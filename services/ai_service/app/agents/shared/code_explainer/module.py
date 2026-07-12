"""Code Explainer processing module — derives explanations from shared JSON, no LLM calls."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.models.enums import MessageRole, ModuleName
from app.repositories.ai_message_repository import AIMessageRepository
from app.schemas.ai import ModuleResponse

_SUPPORTED_LANGS = frozenset({"python", "java", "cpp", "c++", "javascript", "go", "rust", "c#", "sql"})
_LANG_ALIASES = {
    "py": "python",
    "c++": "cpp",
    "js": "javascript",
    "golang": "go",
    "csharp": "c#",
}


@dataclass(frozen=True)
class _ExplainedLine:
    line_no: int
    code: str
    explanation: str


class CodeExplainerModule:
    """Explain code line-by-line for beginner/intermediate/interview audiences."""

    def process(
        self,
        *,
        session_id: UUID,
        payload: dict[str, Any],
        message_repo: AIMessageRepository | None = None,
    ) -> ModuleResponse:
        llm_raw = payload.get("llm_raw") or {}
        coder_payload = payload.get("coder_output") or llm_raw.get("coder") or {}
        evaluator_payload = payload.get("evaluator_output") or llm_raw.get("evaluator") or {}

        solutions = self._extract_solutions(coder_payload)
        explained = []
        for label, sol in solutions:
            language = self._normalize_language(str(sol.get("language") or coder_payload.get("language") or "python"))
            code = str(sol.get("code") or "").strip("\n")
            if not code.strip():
                continue
            explained.append(
                {
                    "label": label,
                    "language": language,
                    "beginner": self._explain(code, language=language, level="beginner"),
                    "intermediate": self._explain(code, language=language, level="intermediate"),
                    "interview": self._explain(code, language=language, level="interview"),
                    "time_complexity": str(evaluator_payload.get("time_complexity") or "Unknown"),
                    "space_complexity": str(evaluator_payload.get("space_complexity") or "Unknown"),
                },
            )

        structured = {
            "solutions": explained,
            "languages_supported": sorted(_SUPPORTED_LANGS),
        }
        content = self._format_markdown(structured)

        if message_repo is not None:
            message_repo.create_message(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=content,
                module_name=ModuleName.CODE_EXPLAINER,
                content_metadata={"structured": structured, "markdown": content},
            )

        return ModuleResponse(
            module=ModuleName.CODE_EXPLAINER,
            content=content,
            structured=structured,
            metadata={"solution_count": len(explained)},
        )

    def _extract_solutions(self, coder_payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        labels = (
            ("Brute Force", "brute_force"),
            ("Better Solution", "better_solution"),
            ("Optimal Solution", "optimal_solution"),
        )
        results: list[tuple[str, dict[str, Any]]] = []
        for label, key in labels:
            raw = coder_payload.get(key)
            if isinstance(raw, dict) and str(raw.get("code") or "").strip():
                results.append((label, raw))
        if results:
            return results
        # fallback: legacy solutions[]
        solutions = coder_payload.get("solutions") or []
        if isinstance(solutions, list):
            for idx, raw in enumerate(solutions[:3], start=1):
                if isinstance(raw, dict) and str(raw.get("code") or "").strip():
                    results.append((str(raw.get("approach") or f"Approach {idx}"), raw))
        return results

    def _normalize_language(self, language: str) -> str:
        normalized = language.strip().lower()
        normalized = _LANG_ALIASES.get(normalized, normalized)
        if normalized not in _SUPPORTED_LANGS:
            return "python"
        return normalized

    def _explain(self, code: str, *, language: str, level: str) -> dict[str, Any]:
        # Returns structured JSON suitable for "Explain line 15" follow-ups.
        lines = code.splitlines()
        if language == "python":
            return self._explain_python(lines, level=level)
        if language == "sql":
            return self._explain_sql(lines, level=level)
        return self._explain_generic(lines, language=language, level=level)

    def _explain_python(self, lines: list[str], *, level: str) -> dict[str, Any]:
        code = "\n".join(lines)
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return self._explain_generic(lines, language="python", level=level)

        line_notes: dict[int, list[str]] = {}

        def add(lineno: int, msg: str) -> None:
            if lineno <= 0:
                return
            line_notes.setdefault(lineno, []).append(msg)

        for node in ast.walk(tree):
            lineno = getattr(node, "lineno", 0) or 0
            if isinstance(node, ast.FunctionDef):
                add(lineno, f"Defines a function `{node.name}`.")
            elif isinstance(node, ast.Return):
                add(lineno, "Returns a value to the caller.")
            elif isinstance(node, ast.For):
                add(lineno, "Starts a loop that iterates over a sequence.")
            elif isinstance(node, ast.While):
                add(lineno, "Starts a loop that repeats while the condition is true.")
            elif isinstance(node, ast.If):
                add(lineno, "Checks a condition and chooses which block to execute.")
            elif isinstance(node, ast.Assign):
                targets = []
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        targets.append(t.id)
                if targets:
                    add(lineno, f"Assigns a value to {', '.join(targets)}.")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    add(lineno, f"Calls the function `{node.func.id}()`.")
                elif isinstance(node.func, ast.Attribute):
                    add(lineno, f"Calls `{ast.unparse(node.func)}`.")

        explained_lines: list[_ExplainedLine] = []
        for i, raw in enumerate(lines, start=1):
            stripped = raw.rstrip("\n")
            if not stripped.strip():
                continue
            notes = line_notes.get(i) or []
            if not notes:
                notes = [self._default_note_for_line(stripped, language="python")]
            explained_lines.append(_ExplainedLine(i, stripped, self._tone(notes, level=level)))

        return self._package_explanation(explained_lines, language="python", level=level)

    def _explain_sql(self, lines: list[str], *, level: str) -> dict[str, Any]:
        explained: list[_ExplainedLine] = []
        for i, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if upper.startswith("SELECT"):
                msg = "Selects the output columns."
            elif upper.startswith("FROM"):
                msg = "Chooses the table (or subquery) to read from."
            elif upper.startswith("WHERE"):
                msg = "Filters rows by the given condition."
            elif upper.startswith("JOIN"):
                msg = "Combines rows from two sources based on a match condition."
            elif upper.startswith("GROUP BY"):
                msg = "Groups rows so aggregates (COUNT/SUM/etc.) are computed per group."
            elif upper.startswith("HAVING"):
                msg = "Filters groups after aggregation."
            elif upper.startswith("ORDER BY"):
                msg = "Sorts the final result."
            else:
                msg = "Continues the SQL query."
            explained.append(_ExplainedLine(i, raw.rstrip("\n"), self._tone([msg], level=level)))
        return self._package_explanation(explained, language="sql", level=level)

    def _explain_generic(self, lines: list[str], *, language: str, level: str) -> dict[str, Any]:
        explained: list[_ExplainedLine] = []
        for i, raw in enumerate(lines, start=1):
            stripped = raw.rstrip("\n")
            if not stripped.strip():
                continue
            note = self._default_note_for_line(stripped, language=language)
            explained.append(_ExplainedLine(i, stripped, self._tone([note], level=level)))
        return self._package_explanation(explained, language=language, level=level)

    @staticmethod
    def _default_note_for_line(line: str, *, language: str) -> str:
        lowered = line.strip().lower()
        if any(tok in lowered for tok in ("for ", "while ", "foreach", "loop")):
            return "This line starts/continues a loop."
        if any(tok in lowered for tok in ("if ", "else", "elif", "switch", "case")):
            return "This line makes a decision based on a condition."
        if any(tok in lowered for tok in ("return",)):
            return "This line returns a result."
        if language in {"java", "cpp", "c#", "go", "rust"} and ("{" in lowered or "}" in lowered):
            return "This line opens/closes a code block."
        if re.search(r"\bdef\b|\bfunction\b", lowered):
            return "This line declares a function."
        if "=" in line and "==" not in line:
            return "This line assigns a value to a variable."
        return "This line performs part of the solution logic."

    @staticmethod
    def _tone(notes: list[str], *, level: str) -> str:
        merged = " ".join(notes).strip()
        if level == "beginner":
            return merged
        if level == "intermediate":
            return merged.replace("This line", "This statement")
        if level == "interview":
            return merged + " (Focus on invariants and edge cases.)"
        return merged

    @staticmethod
    def _package_explanation(lines: list[_ExplainedLine], *, language: str, level: str) -> dict[str, Any]:
        return {
            "language": language,
            "level": level,
            "lines": [
                {"line_no": item.line_no, "code": item.code, "explanation": item.explanation}
                for item in lines
            ],
        }

    @staticmethod
    def _format_markdown(structured: dict[str, Any]) -> str:
        parts: list[str] = ["## Code Explanation"]
        solutions = structured.get("solutions") or []
        if not solutions:
            return "## Code Explanation\n\nNo code available to explain."
        for sol in solutions:
            label = sol.get("label") or "Solution"
            language = sol.get("language") or "python"
            parts.append(f"\n### {label} ({language})")
            for section in ("beginner", "intermediate", "interview"):
                payload = sol.get(section) or {}
                parts.append(f"\n#### {section.title()} explanation")
                for item in payload.get("lines") or []:
                    parts.append(f"- **Line {item['line_no']}**: `{item['code'].strip()}`")
                    parts.append(f"  - {item['explanation']}")
            parts.append(
                f"\n**Time Complexity:** {sol.get('time_complexity','Unknown')}\n\n"
                f"**Space Complexity:** {sol.get('space_complexity','Unknown')}"
            )
        return "\n".join(parts).strip()

