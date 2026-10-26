import json

import httpx
import pytest

from h2.llm import LLMClient, LLMConfig, LLMError, config_from_env


def _client(handler, **kw):
    cfg = LLMConfig(base_url="http://fake.local/v1", model="m", api_key="sk-secret-value")
    return LLMClient(cfg, transport=httpx.MockTransport(handler), sleep=lambda s: None, **kw)


def test_request_shape_and_header():
    seen = {}

    def handler(req: httpx.Request):
        seen["auth"] = req.headers.get("authorization")
        seen["body"] = req.read()
        return httpx.Response(200, json={"choices": [{"message": {"content": "Yes"}, "finish_reason": "stop"}],
                                         "usage": {"total_tokens": 3}})

    c = _client(handler)
    r = c([{"role": "user", "content": "q"}], temperature=0.0, seed=0, max_tokens=1)
    assert r.content == "Yes" and r.usage == {"total_tokens": 3}
    assert seen["auth"] == "Bearer sk-secret-value"
    body = json.loads(seen["body"])
    assert (body["max_tokens"], body["seed"], body["temperature"], body["model"]) == (1, 0, 0.0, "m")


def test_retry_then_success_and_persistent_failure():
    n = {"calls": 0}

    def flaky(req):
        n["calls"] += 1
        if n["calls"] < 3:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, json={"choices": [{"message": {"content": "no"}}]})

    assert _client(flaky).__call__([{"role": "user", "content": "q"}], max_tokens=1).content == "no"
    assert n["calls"] == 3

    def down(req):
        raise httpx.ConnectError("refused")

    with pytest.raises(LLMError) as ei:
        _client(down, max_retries=3)([{"role": "user", "content": "q"}])
    assert "3 attempts" in str(ei.value) and "sk-secret" not in str(ei.value)

    def forbidden(req):
        return httpx.Response(401, text="bad key sk-secret-value")

    with pytest.raises(LLMError) as ei:
        _client(forbidden)([{"role": "user", "content": "q"}])
    assert "HTTP 401" in str(ei.value)


def test_config_from_env_and_repr(monkeypatch):
    monkeypatch.delenv("CE_JUDGE_BASE_URL", raising=False)
    with pytest.raises(LLMError):
        config_from_env("judge")
    monkeypatch.setenv("CE_JUDGE_BASE_URL", "http://x/v1/")
    monkeypatch.setenv("CE_JUDGE_MODEL", "judge-model")
    monkeypatch.setenv("CE_JUDGE_API_KEY", "topsecret")
    cfg = config_from_env("judge")
    assert cfg.base_url == "http://x/v1" and cfg.model == "judge-model"
    assert "topsecret" not in repr(cfg) and "topsecret" not in str(cfg)
