"""Shared helpers for building and finalizing single-LLM invocations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.coaching.registry import get_mode_registry
from app.core.config import feature_max_tokens_map, get_ai_settings
from app.core.feature_tokens import resolve_feature_max_tokens
from app.prompts.builder import PromptBuilder
from app.schemas.ai import PlannerOutput
from app.schemas.workflow import AIWorkflowState
from app.utils.section_tokens import resolve_prior_payload
from shared.config import get_settings


@dataclass(frozen=True)
class OpenRouterInvocation:
    """Prepared prompts and parameters for a single OpenRouter call."""

    system_prompt: str
    user_prompt: str
    model: str | None
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    planner: PlannerOutput
    requested_sections: list[str] | None
    prior_payload: dict[str, Any] | None
    cache_key: str | None
    prompt_version: str
    mode_id: str | None


def build_openrouter_invocation(
    *,
    state: AIWorkflowState,
    prompt_builder: PromptBuilder,
    cache_manager: Any,
) -> OpenRouterInvocation:
    """Build prompts and generation parameters from workflow state."""
    planner = PlannerOutput.model_validate(state.get("planner_output") or {})
    mode_registry = get_mode_registry()
    mode_cfg = mode_registry.resolve(state.get("mode_id"))
    requested_sections = state.get("requested_sections")
    built = prompt_builder.build(
        planner=planner,
        message=state.get("message", ""),
        context=state.get("context") if isinstance(state.get("context"), dict) else None,
        memory_context=state.get("memory_context") if isinstance(state.get("memory_context"), dict) else None,
        title=state.get("title"),
        mode_id=state.get("mode_id"),
        requested_sections=requested_sections,
    )
    shared_settings = get_settings()
    ai_settings = get_ai_settings()
    model_name = state.get("model") or shared_settings.openrouter_model
    prompt_version = ai_settings.prompt_default_version
    max_tokens = resolve_feature_max_tokens(
        planner.feature.value,
        override=state.get("max_tokens"),
        requested_sections=requested_sections,
        limits=feature_max_tokens_map(ai_settings),
    )
    cache_key = cache_manager.build_key(
        feature=planner.feature.value,
        model=str(model_name),
        prompt_version=prompt_version,
        context=state.get("context") if isinstance(state.get("context"), dict) else None,
        metadata=planner.metadata if isinstance(planner.metadata, dict) else None,
        message=state.get("message", ""),
    )
    prior_payload = resolve_prior_payload(
        context=state.get("context") if isinstance(state.get("context"), dict) else None,
        memory_context=state.get("memory_context") if isinstance(state.get("memory_context"), dict) else None,
    )
    return OpenRouterInvocation(
        system_prompt=built.system_prompt,
        user_prompt=built.user_prompt,
        model=state.get("model"),
        temperature=float(state.get("temperature", mode_cfg.generation.temperature)),
        max_tokens=max_tokens,
        top_p=mode_cfg.generation.top_p,
        frequency_penalty=mode_cfg.generation.frequency_penalty,
        presence_penalty=mode_cfg.generation.presence_penalty,
        planner=planner,
        requested_sections=requested_sections,
        prior_payload=prior_payload,
        cache_key=cache_key,
        prompt_version=prompt_version,
        mode_id=state.get("mode_id"),
    )
