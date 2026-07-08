"""Reverse-proxy utilities for routing Gateway → AI Service."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
import httpx
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse

from shared.middleware.request_id import REQUEST_ID_HEADER

from app.proxy.constants import HOP_BY_HOP_HEADERS

logger = logging.getLogger("gateway.proxy")


def _filtered_request_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS or lk in {"host", "content-length"}:
            continue
        headers[k] = v
    return headers


def _filtered_response_headers(upstream: httpx.Response) -> dict[str, str]:
    headers: dict[str, str] = {}
    for k, v in upstream.headers.items():
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS or lk in {"content-length"}:
            continue
        headers[k] = v
    return headers


def _request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    if isinstance(rid, str) and rid:
        return rid
    header_val = request.headers.get(REQUEST_ID_HEADER)
    return header_val or ""


def _auth_header_present(request: Request) -> bool:
    auth = request.headers.get("authorization")
    return bool(auth and auth.strip())


def _json_error(status_code: int, detail: str, request: Request) -> JSONResponse:
    headers: dict[str, str] = {}
    rid = _request_id(request)
    if rid:
        headers[REQUEST_ID_HEADER] = rid
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


TransientExc = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
    httpx.WriteError,
)


def _is_transient_status(code: int) -> bool:
    return code in {
        status.HTTP_502_BAD_GATEWAY,
        status.HTTP_503_SERVICE_UNAVAILABLE,
        status.HTTP_504_GATEWAY_TIMEOUT,
    }


async def _retry(
    fn: Callable[[], httpx.Response],
    *,
    max_attempts: int = 3,
    base_delay_s: float = 0.2,
) -> httpx.Response:
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = await fn()
            if _is_transient_status(resp.status_code) and attempt < max_attempts:
                await resp.aclose()
                await asyncio.sleep(base_delay_s * (2 ** (attempt - 1)))
                continue
            return resp
        except TransientExc as exc:
            last_exc = exc
            if attempt >= max_attempts:
                raise
            await asyncio.sleep(base_delay_s * (2 ** (attempt - 1)))
    raise RuntimeError("unreachable") from last_exc


async def proxy_to_upstream(
    request: Request,
    *,
    upstream_client: httpx.AsyncClient,
    upstream_path: str,
    require_auth: bool = True,
    stream: bool = False,
) -> Response:
    if require_auth and not _auth_header_present(request):
        return _json_error(status.HTTP_401_UNAUTHORIZED, "Missing Authorization header.", request)

    request_id = _request_id(request)
    start = time.perf_counter()

    method = request.method.upper()
    params = dict(request.query_params)
    body = await request.body()
    headers = _filtered_request_headers(request)
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id

    async def do_request() -> httpx.Response:
        req = upstream_client.build_request(
            method,
            upstream_path,
            params=params,
            content=body,
            headers=headers,
        )
        return await upstream_client.send(req, stream=stream)

    try:
        upstream = await _retry(do_request)
    except httpx.ReadTimeout:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.warning(
            "proxy timeout method=%s path=%s upstream=%s status=%s latency_ms=%s request_id=%s",
            method,
            request.url.path,
            str(upstream_client.base_url.join(upstream_path)),
            504,
            latency_ms,
            request_id,
        )
        return _json_error(status.HTTP_504_GATEWAY_TIMEOUT, "Upstream timeout.", request)
    except TransientExc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.warning(
            "proxy unavailable method=%s path=%s upstream=%s status=%s latency_ms=%s request_id=%s",
            method,
            request.url.path,
            str(upstream_client.base_url.join(upstream_path)),
            502,
            latency_ms,
            request_id,
        )
        return _json_error(status.HTTP_502_BAD_GATEWAY, "Upstream unavailable.", request)

    latency_ms = int((time.perf_counter() - start) * 1000)

    if stream:
        async def gen() -> AsyncIterator[bytes]:
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            finally:
                await upstream.aclose()

        resp = StreamingResponse(
            gen(),
            status_code=upstream.status_code,
            headers=_filtered_response_headers(upstream),
            media_type=upstream.headers.get("content-type"),
        )
    else:
        content = upstream.content
        resp = Response(
            content=content,
            status_code=upstream.status_code,
            headers=_filtered_response_headers(upstream),
            media_type=upstream.headers.get("content-type"),
        )
        await upstream.aclose()

    # Ensure request-id is always echoed from the gateway as well.
    if request_id:
        resp.headers[REQUEST_ID_HEADER] = request_id

    logger.info(
        "proxy method=%s path=%s upstream=%s status=%s latency_ms=%s request_id=%s",
        method,
        request.url.path,
        str(upstream_client.base_url.join(upstream_path)),
        upstream.status_code,
        latency_ms,
        request_id,
    )

    return resp

