"""OpenAI-compatible team inference relay."""
from __future__ import annotations

import json
import logging
import sys
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response, StreamingResponse

from relay.config import RelaySettings, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

SUPPORTED_CHAT_FIELDS = {
    "model",
    "messages",
    "temperature",
    "max_tokens",
    "stream",
    "top_p",
    "stop",
    "presence_penalty",
    "frequency_penalty",
    "n",
    "response_format",
    "seed",
    "tools",
    "tool_choice",
    "user",
    "logit_bias",
}


@dataclass
class RelayMetrics:
    total_requests: int = 0
    stream_requests: int = 0
    non_stream_requests: int = 0
    auth_failures: int = 0
    bad_requests: int = 0
    model_blocked: int = 0
    upstream_4xx: int = 0
    upstream_5xx: int = 0
    upstream_timeout: int = 0
    upstream_network_error: int = 0
    success_by_model: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "stream_requests": self.stream_requests,
            "non_stream_requests": self.non_stream_requests,
            "auth_failures": self.auth_failures,
            "bad_requests": self.bad_requests,
            "model_blocked": self.model_blocked,
            "upstream_4xx": self.upstream_4xx,
            "upstream_5xx": self.upstream_5xx,
            "upstream_timeout": self.upstream_timeout,
            "upstream_network_error": self.upstream_network_error,
            "success_by_model": dict(self.success_by_model),
        }


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def _request_ip(req: Request) -> str:
    xff = req.headers.get("x-forwarded-for", "").strip()
    if xff:
        return xff.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


def _upstream_url(path: str, settings: RelaySettings) -> str:
    return f"{settings.upstream_base_url.rstrip('/')}/{path.lstrip('/')}"


def _json_error(code: str, message: str, request_id: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}, "request_id": request_id},
        headers={"x-relay-request-id": request_id},
    )


async def _require_auth(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    settings: RelaySettings = request.app.state.settings
    token = _bearer_token(authorization)
    if not token or token != settings.relay_shared_token:
        request.app.state.metrics.auth_failures += 1
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def _validate_payload(payload: dict[str, Any], settings: RelaySettings) -> tuple[str, bool]:
    unknown = sorted(k for k in payload.keys() if k not in SUPPORTED_CHAT_FIELDS)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported field(s): {', '.join(unknown)}",
        )

    model = payload.get("model")
    if not isinstance(model, str) or not model.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Field 'model' is required")
    model = model.strip()
    if model not in settings.model_allowlist:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Model not allowed: {model}")

    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Field 'messages' must be a non-empty list")

    return model, bool(payload.get("stream", False))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if not settings.relay_shared_token:
        raise RuntimeError("RELAY_SHARED_TOKEN must be set before starting the relay")
    if not settings.upstream_api_key:
        raise RuntimeError("UPSTREAM_API_KEY (or NVIDIA_API_KEY) must be set before starting the relay")

    app.state.settings = settings
    app.state.metrics = RelayMetrics()
    app.state.http = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=settings.connect_timeout_s,
            read=settings.request_timeout_s,
            write=settings.request_timeout_s,
            pool=settings.connect_timeout_s,
        ),
    )
    logger.info(
        "Relay starting on %s with %d allowed model(s)",
        settings.relay_bind,
        len(settings.model_allowlist),
    )
    yield
    await app.state.http.aclose()
    logger.info("Relay stopped")


app = FastAPI(title="Open-Stitch Team Relay", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health(request: Request) -> dict[str, Any]:
    settings: RelaySettings = request.app.state.settings
    client: httpx.AsyncClient = request.app.state.http

    upstream_ok = False
    upstream_status: int | None = None
    error: str | None = None

    try:
        resp = await client.get(
            _upstream_url("/models", settings),
            headers={"Authorization": f"Bearer {settings.upstream_api_key}"},
            timeout=settings.health_probe_timeout_s,
        )
        upstream_status = resp.status_code
        upstream_ok = resp.status_code < 500
    except httpx.HTTPError as exc:
        error = str(exc)

    return {
        "status": "ok",
        "relay": {"allowed_models": sorted(settings.model_allowlist)},
        "upstream": {
            "base_url": settings.upstream_base_url,
            "reachable": upstream_ok,
            "status_code": upstream_status,
            "error": error,
        },
    }


@app.get("/metrics", dependencies=[Depends(_require_auth)])
async def metrics(request: Request) -> dict[str, Any]:
    return request.app.state.metrics.as_dict()


@app.get("/v1/models", dependencies=[Depends(_require_auth)])
async def list_models(request: Request) -> dict[str, Any]:
    settings: RelaySettings = request.app.state.settings
    return {
        "object": "list",
        "data": [
            {"id": model, "object": "model", "owned_by": "team-relay"}
            for model in sorted(settings.model_allowlist)
        ],
    }


@app.post("/v1/chat/completions", dependencies=[Depends(_require_auth)])
async def chat_completions(request: Request) -> Response:
    settings: RelaySettings = request.app.state.settings
    client: httpx.AsyncClient = request.app.state.http
    metrics: RelayMetrics = request.app.state.metrics
    request_id = uuid.uuid4().hex
    caller_ip = _request_ip(request)

    metrics.total_requests += 1

    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        metrics.bad_requests += 1
        return _json_error("invalid_json", "Body must be valid JSON", request_id, 400)

    if not isinstance(payload, dict):
        metrics.bad_requests += 1
        return _json_error("invalid_payload", "Body must be a JSON object", request_id, 400)

    try:
        model, stream = _validate_payload(payload, settings)
    except HTTPException as exc:
        if "Model not allowed" in str(exc.detail):
            metrics.model_blocked += 1
        else:
            metrics.bad_requests += 1
        return _json_error(
            "bad_request",
            str(exc.detail),
            request_id,
            exc.status_code,
        )

    logger.info(
        "relay_request id=%s ip=%s model=%s stream=%s messages=%d",
        request_id,
        caller_ip,
        model,
        stream,
        len(payload.get("messages", [])),
    )

    upstream_headers = {
        "Authorization": f"Bearer {settings.upstream_api_key}",
        "Content-Type": "application/json",
    }
    url = _upstream_url("/chat/completions", settings)

    if not stream:
        metrics.non_stream_requests += 1
        try:
            resp = await client.post(url, headers=upstream_headers, json=payload)
        except httpx.TimeoutException:
            metrics.upstream_timeout += 1
            return _json_error("upstream_timeout", "Upstream timed out", request_id, 504)
        except httpx.HTTPError as exc:
            metrics.upstream_network_error += 1
            return _json_error("upstream_network_error", str(exc), request_id, 502)

        if 400 <= resp.status_code < 500:
            metrics.upstream_4xx += 1
        if resp.status_code >= 500:
            metrics.upstream_5xx += 1
        if resp.status_code < 400:
            metrics.success_by_model[model] += 1

        content_type = resp.headers.get("content-type", "application/json")
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=content_type.split(";")[0],
            headers={"x-relay-request-id": request_id},
        )

    metrics.stream_requests += 1
    req = client.build_request("POST", url, headers=upstream_headers, json=payload)
    try:
        upstream_resp = await client.send(req, stream=True)
    except httpx.TimeoutException:
        metrics.upstream_timeout += 1
        return _json_error("upstream_timeout", "Upstream timed out", request_id, 504)
    except httpx.HTTPError as exc:
        metrics.upstream_network_error += 1
        return _json_error("upstream_network_error", str(exc), request_id, 502)

    if 400 <= upstream_resp.status_code < 500:
        metrics.upstream_4xx += 1
    if upstream_resp.status_code >= 500:
        metrics.upstream_5xx += 1

    if upstream_resp.status_code >= 400:
        body = await upstream_resp.aread()
        await upstream_resp.aclose()
        return Response(
            content=body,
            status_code=upstream_resp.status_code,
            media_type=upstream_resp.headers.get("content-type", "application/json").split(";")[0],
            headers={"x-relay-request-id": request_id},
        )

    metrics.success_by_model[model] += 1

    async def _event_stream() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream_resp.aiter_bytes():
                yield chunk
        finally:
            await upstream_resp.aclose()

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "x-relay-request-id": request_id,
        },
    )


def main() -> None:
    import uvicorn

    settings = get_settings()
    host, _, port = settings.relay_bind.partition(":")
    if not host or not port.isdigit():
        raise RuntimeError("RELAY_BIND must be in host:port format, e.g. 127.0.0.1:8090")

    uvicorn.run("relay.main:app", host=host, port=int(port), log_level="info", reload=False)


if __name__ == "__main__":
    main()
