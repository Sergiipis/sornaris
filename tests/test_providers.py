import json
import urllib.error
import urllib.request

import pytest
from sornaris.providers import (
    AnthropicProvider,
    BaseProvider,
    FakeProvider,
    OpenAIProvider,
    ProviderError,
    ScriptedProvider,
    build_provider,
)


def test_base_provider_cannot_instantiate():
    with pytest.raises(TypeError):
        BaseProvider()


def test_fake_provider_deterministic():
    p = FakeProvider()
    out1 = p.generate("what is 2+2?", "gpt-4")
    out2 = p.generate("what is 2+2?", "gpt-4")
    assert out1 == out2


def test_fake_provider_changes_with_prompt():
    p = FakeProvider()
    out1 = p.generate("A", "m")
    out2 = p.generate("B", "m")
    assert out1 != out2


def test_fake_provider_changes_with_model():
    p = FakeProvider()
    out1 = p.generate("same", "m1")
    out2 = p.generate("same", "m2")
    assert out1 != out2


def test_fake_provider_prefix_appears():
    p = FakeProvider(prefix="MOCK")
    out = p.generate("x", "m")
    assert out.startswith("MOCK:m:")


def test_scripted_first_match_wins():
    p = ScriptedProvider(
        scripts=[
            ("hello", "m1", "response_a"),
            ("hello", "m1", "response_b"),
        ]
    )
    assert p.generate("hello world", "m1") == "response_a"


def test_scripted_model_id_must_match():
    p = ScriptedProvider(scripts=[("hi", "m1", "r1")], default="fallback")
    assert p.generate("hi there", "m2") == "fallback"


def test_scripted_no_match_raises_without_default():
    p = ScriptedProvider(scripts=[("foo", "m1", "r")])
    with pytest.raises(KeyError):
        p.generate("bar", "m1")


def test_scripted_no_match_returns_default_when_set():
    p = ScriptedProvider(scripts=[("foo", "m1", "r")], default="X")
    assert p.generate("bar", "m2") == "X"


def test_scripted_empty_substring_matches_anything():
    p = ScriptedProvider(scripts=[("", "m1", "always")])
    assert p.generate("whatever", "m1") == "always"


def test_scripted_substring_partial():
    p = ScriptedProvider(scripts=[("error", "m1", "oops")])
    assert p.generate("an error occurred", "m1") == "oops"


# --- real HTTP providers (mocked transport) ------------------------------


class _FakeResp:
    def __init__(self, payload):
        self._data = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_urlopen(monkeypatch, payload, capture=None):
    def fake_urlopen(req, timeout=None):
        if capture is not None:
            capture["req"] = req
        return _FakeResp(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


def test_build_provider_fake():
    assert isinstance(build_provider("fake"), FakeProvider)


def test_build_provider_unknown_raises():
    with pytest.raises(ProviderError):
        build_provider("nope")


def test_openai_missing_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ProviderError):
        OpenAIProvider(model_id="gpt-4o-mini")


def test_openai_generate_parses_and_sends(monkeypatch):
    cap = {}
    _patch_urlopen(monkeypatch, {"choices": [{"message": {"content": "hello"}}]}, cap)
    p = OpenAIProvider(model_id="gpt-4o-mini", api_key="sk-test")
    out = p.generate("ping", "gpt-4o-mini")
    assert out == "hello"
    body = json.loads(cap["req"].data)
    assert body["model"] == "gpt-4o-mini"
    assert body["messages"][0]["content"] == "ping"
    assert cap["req"].get_header("Authorization") == "Bearer sk-test"
    assert cap["req"].full_url.endswith("/chat/completions")


def test_openai_bad_shape_raises(monkeypatch):
    _patch_urlopen(monkeypatch, {"unexpected": True})
    p = OpenAIProvider(model_id="m", api_key="k")
    with pytest.raises(ProviderError):
        p.generate("x", "m")


def test_openai_http_error_becomes_provider_error(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    p = OpenAIProvider(model_id="m", api_key="bad")
    with pytest.raises(ProviderError):
        p.generate("x", "m")


def test_anthropic_generate_parses_and_sends(monkeypatch):
    cap = {}
    _patch_urlopen(monkeypatch, {"content": [{"type": "text", "text": "hi there"}]}, cap)
    p = AnthropicProvider(model_id="claude-x", api_key="ak-test")
    out = p.generate("ping", "claude-x")
    assert out == "hi there"
    assert cap["req"].get_header("X-api-key") == "ak-test"
    assert cap["req"].full_url.endswith("/v1/messages")


def test_build_provider_openai_forwards_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    p = build_provider("openai", model_id="gpt-4o")
    assert isinstance(p, OpenAIProvider)
    assert p.default_model == "gpt-4o"
