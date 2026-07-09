"""Gateway reverse-proxy routes for the AI Service."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["ai-proxy"])


@router.post("/leetcode/analyze")
async def leetcode_analyze(request: Request):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path="/leetcode/analyze",
        stream=should_stream(request),
    )


@router.post("/leetcode/follow-up")
async def leetcode_follow_up(request: Request):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path="/leetcode/follow-up",
        stream=should_stream(request),
    )


@router.get("/leetcode/history")
async def leetcode_history(request: Request):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path="/leetcode/history",
    )


@router.get("/leetcode/history/{session_id}")
async def leetcode_history_session(request: Request, session_id: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path=f"/leetcode/history/{session_id}",
    )


@router.patch("/leetcode/history/{session_id}")
async def leetcode_update_session(request: Request, session_id: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path=f"/leetcode/history/{session_id}",
    )


@router.delete("/leetcode/history/{session_id}")
async def leetcode_delete_session(request: Request, session_id: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path=f"/leetcode/history/{session_id}",
    )


@router.get("/leetcode/progress")
async def leetcode_progress(request: Request):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path="/leetcode/progress",
    )


@router.get("/leetcode/modes")
async def leetcode_modes(request: Request):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path="/leetcode/modes",
    )


@router.get("/leetcode/examples")
async def leetcode_examples(request: Request):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path="/leetcode/examples",
    )


@router.get("/ai/models")
async def ai_models(request: Request):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path="/ai/models",
    )


# Future-proofing: allow new AI endpoints without adding gateway code.
@router.api_route("/ai/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def ai_catchall(request: Request, path: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path=f"/ai/{path}",
        stream=should_stream(request),
    )

