"""Coder processing module — formats code solutions, no additional LLM calls."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.enums import MessageRole, ModuleName
from app.repositories.ai_message_repository import AIMessageRepository
from app.schemas.ai import ModuleResponse

_SUPPORTED_LANGUAGES = frozenset(
    {"python", "java", "cpp", "c++", "javascript", "go", "rust", "typescript"},
)

_LANG_ALIASES = {
    "c++": "cpp",
    "js": "javascript",
    "ts": "typescript",
}


class CoderModule:
    """Read coder JSON, format code, store solutions."""

    def process(
        self,
        *,
        session_id: UUID,
        payload: dict[str, Any],
        message_repo: AIMessageRepository | None = None,
    ) -> ModuleResponse:
        parts: list[str] = ["## Solutions"]
        solution_count = 0

        structured_solutions = self._extract_structured_solutions(payload)
        if structured_solutions:
            for label, solution in structured_solutions:
                solution_count += 1
                parts.extend(self._format_solution_block(label, solution))
        else:
            language = self._normalize_language(str(payload.get("language", "python")))
            solutions = payload.get("solutions") or []
            parts[0] = f"## Solutions ({language})"
            for index, solution in enumerate(solutions, start=1):
                solution_count += 1
                approach = solution.get("approach", f"Approach {index}")
                code = solution.get("code", "")
                complexity = solution.get("complexity", "")
                explanation = solution.get("explanation", "")
                parts.append(f"\n### {approach}")
                if complexity:
                    parts.append(f"**Complexity:** {complexity}")
                if explanation:
                    parts.append(explanation)
                if code:
                    parts.append(f"```{language}\n{code}\n```")

        content = "\n".join(parts).strip() or "No coder output available."
        primary_language = self._detect_primary_language(payload)

        if message_repo is not None:
            message_repo.create_message(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=content,
                module_name=ModuleName.CODER,
                content_metadata={
                    "structured": payload,
                    "language": primary_language,
                    "solution_count": solution_count,
                },
            )

        return ModuleResponse(
            module=ModuleName.CODER,
            content=content,
            structured=payload,
            metadata={"language": primary_language, "solution_count": solution_count},
        )

    def _extract_structured_solutions(
        self,
        payload: dict[str, Any],
    ) -> list[tuple[str, dict[str, Any]]]:
        labels = (
            ("Brute Force", "brute_force"),
            ("Better Solution", "better_solution"),
            ("Optimal Solution", "optimal_solution"),
        )
        alias_keys = {
            "better_solution": "better",
            "optimal_solution": "optimal",
        }
        results: list[tuple[str, dict[str, Any]]] = []
        for label, key in labels:
            raw = payload.get(key)
            if not isinstance(raw, dict) or not raw.get("code"):
                alias = alias_keys.get(key)
                if alias:
                    raw = payload.get(alias)
            if isinstance(raw, dict) and raw.get("code"):
                results.append((label, raw))
        return results

    def _format_solution_block(self, label: str, solution: dict[str, Any]) -> list[str]:
        language = self._normalize_language(str(solution.get("language", "python")))
        code = str(solution.get("code", ""))
        complexity = str(solution.get("complexity", ""))
        explanation = str(solution.get("explanation", ""))
        block = [f"\n### {label}"]
        if complexity:
            block.append(f"**Complexity:** {complexity}")
        if explanation:
            block.append(explanation)
        if code:
            block.append(f"```{language}\n{code}\n```")
        return block

    def _normalize_language(self, language: str) -> str:
        normalized = language.strip().lower()
        normalized = _LANG_ALIASES.get(normalized, normalized)
        if normalized not in _SUPPORTED_LANGUAGES:
            return "python"
        return normalized

    def _detect_primary_language(self, payload: dict[str, Any]) -> str:
        for key in ("optimal_solution", "better_solution", "brute_force"):
            raw = payload.get(key)
            if isinstance(raw, dict) and raw.get("language"):
                return self._normalize_language(str(raw["language"]))
        return self._normalize_language(str(payload.get("language", "python")))
