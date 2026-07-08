"""Convert LeetCode problem HTML into LeetCode-style Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

from bs4 import BeautifulSoup, NavigableString, Tag


@dataclass(frozen=True)
class ParsedExample:
    """Parsed example test case from LeetCode HTML."""

    input: str
    output: str
    explanation: str | None = None

_EXAMPLE_HEADER_RE = re.compile(r"^example\s*\d*\s*:?\s*$", re.IGNORECASE)
_CONSTRAINTS_HEADER_RE = re.compile(r"^constraints?\s*:?\s*$", re.IGNORECASE)
_FOLLOW_UP_HEADER_RE = re.compile(r"^follow[\s-]?up\s*:?\s*$", re.IGNORECASE)
_INPUT_RE = re.compile(r"^input\s*:\s*(.*)$", re.IGNORECASE | re.DOTALL)
_OUTPUT_RE = re.compile(r"^output\s*:\s*(.*)$", re.IGNORECASE | re.DOTALL)
_EXPLANATION_RE = re.compile(r"^explanation\s*:\s*(.*)$", re.IGNORECASE | re.DOTALL)


def _normalize_superscripts(root: Tag | BeautifulSoup) -> None:
    for sup in root.find_all("sup"):
        sup.replace_with(f"^{sup.get_text()}")


def _inline_markdown(node: Tag | NavigableString) -> str:
    if isinstance(node, NavigableString):
        return unescape(str(node))
    if not isinstance(node, Tag):
        return ""
    if node.name == "sup":
        return f"^{node.get_text()}"
    if node.name == "sub":
        return f"_{node.get_text()}_"
    if node.name == "code":
        return f"`{node.get_text()}`"
    if node.name in {"strong", "b"}:
        inner = "".join(_inline_markdown(child) for child in node.children)
        return f"**{inner}**" if inner.strip() else ""
    if node.name in {"em", "i"}:
        inner = "".join(_inline_markdown(child) for child in node.children)
        return f"*{inner}*" if inner.strip() else ""
    if node.name == "br":
        return "\n"
    return "".join(_inline_markdown(child) for child in node.children)


def _paragraph_text(element: Tag) -> str:
    text = _inline_markdown(element).strip()
    return re.sub(r"\s+", " ", text).strip()


def _pre_text(element: Tag) -> str:
    return unescape(element.get_text("\n", strip=False)).strip()


def _parse_pre_example(pre_text: str) -> tuple[str, str, str | None]:
    input_val = ""
    output_val = ""
    explanation_val: str | None = None

    current: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal input_val, output_val, explanation_val, current, buffer
        if not current or not buffer:
            buffer = []
            current = None
            return
        joined = "\n".join(buffer).strip()
        if current == "input":
            input_val = joined
        elif current == "output":
            output_val = joined
        elif current == "explanation":
            explanation_val = joined
        buffer = []
        current = None

    for line in pre_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        input_match = _INPUT_RE.match(stripped)
        if input_match:
            flush()
            current = "input"
            rest = input_match.group(1).strip()
            if rest:
                buffer = [rest]
            continue
        output_match = _OUTPUT_RE.match(stripped)
        if output_match:
            flush()
            current = "output"
            rest = output_match.group(1).strip()
            if rest:
                buffer = [rest]
            continue
        explanation_match = _EXPLANATION_RE.match(stripped)
        if explanation_match:
            flush()
            current = "explanation"
            rest = explanation_match.group(1).strip()
            if rest:
                buffer = [rest]
            continue
        buffer.append(stripped)

    flush()
    return input_val, output_val, explanation_val


def _format_example_markdown(index: int, pre_text: str) -> tuple[str, ParsedExample]:
    input_val, output_val, explanation_val = _parse_pre_example(pre_text)
    lines = [f"### Example {index}"]

    if input_val:
        lines.append("")
        lines.append("**Input:**")
        lines.append("")
        lines.append("```")
        lines.append(input_val)
        lines.append("```")
    if output_val:
        lines.append("")
        lines.append("**Output:**")
        lines.append("")
        lines.append("```")
        lines.append(output_val)
        lines.append("```")
    if explanation_val:
        lines.append("")
        lines.append(f"**Explanation:** {explanation_val}")

    example = ParsedExample(
        input=input_val,
        output=output_val,
        explanation=explanation_val,
    )
    return "\n".join(lines), example


def _format_constraints_markdown(items: list[str]) -> str:
    if not items:
        return ""
    lines = ["### Constraints", ""]
    lines.extend(f"- `{item}`" for item in items)
    return "\n".join(lines)


def _list_item_plain_text(li: Tag) -> str:
    _normalize_superscripts(li)
    text = unescape(li.get_text(strip=False)).strip()
    return re.sub(r"\s+", " ", text).strip()


def _extract_list_items(ul: Tag) -> list[str]:
    items: list[str] = []
    for li in ul.find_all("li", recursive=False):
        text = _list_item_plain_text(li)
        if text:
            items.append(text)
    return items


def parse_leetcode_html(html: str) -> tuple[str, list[ParsedExample], list[str]]:
    """Return markdown, examples, and constraints from LeetCode HTML content."""
    if not html.strip():
        return "", [], []

    soup = BeautifulSoup(html, "html.parser")
    _normalize_superscripts(soup)

    intro_parts: list[str] = []
    example_sections: list[str] = []
    examples: list[ParsedExample] = []
    constraints: list[str] = []
    follow_up_parts: list[str] = []

    elements = [el for el in soup.children if isinstance(el, Tag)]
    i = 0
    example_index = 0
    section: str = "intro"

    while i < len(elements):
        el = elements[i]
        if el.name == "strong":
            header_text = el.get_text(strip=True)
            header_lower = header_text.lower()
            if _FOLLOW_UP_HEADER_RE.match(header_lower):
                section = "follow_up"
                remainder = _inline_markdown(el.next_sibling).strip() if el.next_sibling else ""
                text = f"**Follow-up:** {remainder}".strip()
                if text:
                    follow_up_parts.append(text)
                i += 1
                continue
            i += 1
            continue

        if el.name == "p":
            strong = el.find("strong")
            header_text = strong.get_text(strip=True) if strong else ""
            header_lower = header_text.lower()

            if _EXAMPLE_HEADER_RE.match(header_lower) or (
                "example" in header_lower and ":" in header_text
            ):
                section = "example"
                example_index += 1
                i += 1
                if i < len(elements) and elements[i].name == "pre":
                    md, example = _format_example_markdown(example_index, _pre_text(elements[i]))
                    example_sections.append(md)
                    examples.append(example)
                    i += 1
                continue

            if _CONSTRAINTS_HEADER_RE.match(header_lower):
                section = "constraints"
                i += 1
                if i < len(elements) and elements[i].name == "ul":
                    constraints = _extract_list_items(elements[i])
                    i += 1
                continue

            if _FOLLOW_UP_HEADER_RE.match(header_lower):
                section = "follow_up"
                text = _paragraph_text(el)
                if text:
                    follow_up_parts.append(text.replace(header_text, "").strip(": ").strip())
                i += 1
                continue

            text = _paragraph_text(el)
            if text and section == "intro":
                intro_parts.append(text)
            elif text and section == "follow_up":
                follow_up_parts.append(text)
            i += 1
            continue

        if el.name == "pre" and section == "intro":
            # Standalone pre in intro (rare)
            intro_parts.append(f"```\n{_pre_text(el)}\n```")
            i += 1
            continue

        if el.name == "ul" and section == "constraints" and not constraints:
            constraints = _extract_list_items(el)
            i += 1
            continue

        i += 1

    markdown_parts: list[str] = []
    if intro_parts:
        markdown_parts.append("\n\n".join(intro_parts))
    if example_sections:
        markdown_parts.append("\n\n".join(example_sections))
    if constraints:
        markdown_parts.append(_format_constraints_markdown(constraints))
    if follow_up_parts:
        markdown_parts.append("### Follow-up\n\n" + "\n\n".join(follow_up_parts))

    markdown = "\n\n".join(part for part in markdown_parts if part.strip())
    return markdown.strip(), examples, constraints


def plain_text_to_markdown(text: str) -> str:
    """Best-effort markdown for manually pasted problem statements."""
    return text.strip()
