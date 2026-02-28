from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from relay.config import get_settings
from relay.main import app


@pytest.fixture(autouse=True)
def relay_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RELAY_SHARED_TOKEN", "test-token")
    monkeypatch.setenv("UPSTREAM_API_KEY", "test-upstream-key")
    monkeypatch.setenv("UPSTREAM_BASE_URL", "https://example.invalid/v1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_chat_requires_auth() -> None:
    with TestClient(app) as client:
        resp = client.post("/v1/chat/completions", json={})
    assert resp.status_code == 401


def test_chat_rejects_unknown_fields() -> None:
    body = {
        "model": "gcp/google/gemini-3-pro",
        "messages": [{"role": "user", "content": "hello"}],
        "bogus": True,
    }
    with TestClient(app) as client:
        resp = client.post("/v1/chat/completions", headers=_headers(), json=body)
    assert resp.status_code == 400
    assert "Unsupported field" in resp.json()["error"]["message"]


def test_chat_rejects_unknown_model() -> None:
    body = {
        "model": "not/allowed",
        "messages": [{"role": "user", "content": "hello"}],
    }
    with TestClient(app) as client:
        resp = client.post("/v1/chat/completions", headers=_headers(), json=body)
    assert resp.status_code == 400
    assert "Model not allowed" in resp.json()["error"]["message"]


def test_chat_forwards_non_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_post(self, url, headers=None, json=None):  # type: ignore[no-untyped-def]
        assert url.endswith("/chat/completions")
        assert headers["Authorization"] == "Bearer test-upstream-key"
        assert json["model"] == "gcp/google/gemini-3-pro"
        return httpx.Response(
            status_code=200,
            json={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    body = {
        "model": "gcp/google/gemini-3-pro",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }
    with TestClient(app) as client:
        resp = client.post("/v1/chat/completions", headers=_headers(), json=body)
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "ok"

