"""Format Usage Service export payloads as CSV / Excel / PDF bytes."""

from __future__ import annotations

import csv
import io
import zipfile
from typing import Any
from xml.sax.saxutils import escape


def build_export_file(
    *,
    report: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    fmt: str,
) -> tuple[bytes, str, str]:
    """Return (content, media_type, filename)."""
    fmt_key = fmt.strip().lower()
    safe_report = report.replace(" ", "_").lower()
    if fmt_key == "csv":
        return (
            _to_csv(columns, rows),
            "text/csv; charset=utf-8",
            f"{safe_report}.csv",
        )
    if fmt_key in {"excel", "xlsx"}:
        return (
            _to_xlsx(columns, rows, sheet_name=safe_report[:31] or "Report"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"{safe_report}.xlsx",
        )
    if fmt_key == "pdf":
        return (
            _to_pdf(title=safe_report, columns=columns, rows=rows),
            "application/pdf",
            f"{safe_report}.pdf",
        )
    raise ValueError(f"Unsupported export format: {fmt}")


def _to_csv(columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    return buf.getvalue().encode("utf-8")


def _to_xlsx(columns: list[str], rows: list[dict[str, Any]], *, sheet_name: str) -> bytes:
    """Minimal XLSX writer (no third-party dependency)."""
    sheet_xml = _sheet_xml(columns, rows)
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        f'<sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/>'
        "</sheets></workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


def _col_name(index: int) -> str:
    """1-based column index → Excel column letters."""
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def _sheet_xml(columns: list[str], rows: list[dict[str, Any]]) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
    ]
    header_cells = []
    for i, col in enumerate(columns, start=1):
        ref = f"{_col_name(i)}1"
        header_cells.append(
            f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(col))}</t></is></c>'
        )
    header_joined = "".join(header_cells)
    parts.append(f'<row r="1">{header_joined}</row>')

    for r_idx, row in enumerate(rows, start=2):
        cells = []
        for c_idx, col in enumerate(columns, start=1):
            ref = f"{_col_name(c_idx)}{r_idx}"
            val = row.get(col, "")
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                cells.append(f'<c r="{ref}"><v>{val}</v></c>')
            else:
                cells.append(
                    f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(val))}</t></is></c>'
                )
        row_joined = "".join(cells)
        parts.append(f'<row r="{r_idx}">{row_joined}</row>')
    parts.extend(["</sheetData>", "</worksheet>"])
    return "".join(parts)


def _to_pdf(
    *,
    title: str,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> bytes:
    """Minimal single-page-ish text PDF (no third-party dependency)."""
    lines = [title.replace("_", " ").title(), ""]
    lines.append(" | ".join(columns))
    lines.append("-" * min(100, max(20, len(lines[-1]))))
    for row in rows[:200]:
        lines.append(" | ".join(str(row.get(c, "")) for c in columns))
    if len(rows) > 200:
        lines.append(f"... ({len(rows) - 200} more rows)")

    content_lines = []
    y = 750
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"BT /F1 9 Tf 40 {y} Td ({safe[:120]}) Tj ET")
        y -= 12
        if y < 40:
            break
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode()
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(out.tell())
        out.write(obj)
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(
        f"trailer<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode()
    )
    return out.getvalue()
