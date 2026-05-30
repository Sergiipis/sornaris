"""Provider abstraction + offline (fake/scripted) and real HTTP LLM providers.

The real providers (``OpenAIProvider``, ``AnthropicProvider``) use only the
Python standard library (``urllib``) — no third-party SDK dependency — and read
the API key from the environment. This keeps ``sornaris`` dependency-free
while letting you bisect a *real* agent, not just the offline ``FakeProvider``.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Optional


class BaseProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, model_id: str) -> str: ...


class FakeProvider(BaseProvider):
    def __init__(self, prefix: str = "FAKE") -> None:
        self.prefix = prefix

    def generate(self, prompt: str, model_id: str) -> str:
        digest = hashlib.sha256((prompt + "|" + model_id).encode("utf-8")).hexdigest()[:16]
        return f"{self.prefix}:{model_id}:{digest}"


class ScriptedProvider(BaseProvider):
    def __init__(
        self,
        scripts: list,
        default: Optional[str] = None,
    ) -> None:
        self._scripts = list(scripts)
        self._default = default

    def generate(self, prompt: str, model_id: str) -> str:
        for substr, mid, response in self._scripts:
            if substr in prompt and mid == model_id:
                return response
        if self._default is not None:
            return self._default
        raise KeyError(f"no script matched for model={model_id}")


class ProviderError(RuntimeError):
    """Raised when a real provider is misconfigured or its HTTP call fails."""


def _http_post_json(url: str, headers: dict, payload: dict, timeout: float) -> dict:
    """POST ``payload`` as JSON to ``url`` and return the parsed JSON response.

    Uses only the standard library. Raises ``ProviderError`` with a readable
    message on any HTTP/transport/parse failure so the bisect loop can surface
    a clear error instead of an opaque traceback.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # 4xx/5xx
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise ProviderError(f"HTTP {exc.code} from {url}: {body}") from exc
    except urllib.error.URLError as exc:  # network/DNS/timeout
        raise ProviderError(f"request to {url} failed: {exc.reason}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"non-JSON response from {url}: {raw[:200]}") from exc


class OpenAIProvider(BaseProvider):
    """Chat-completions provider for OpenAI-compatible APIs (stdlib only).

    Works with any endpoint that speaks the OpenAI ``/chat/completions`` shape
    (OpenAI, Azure-compatible gateways, vLLM, Ollama's OpenAI mode, etc.) via
    ``base_url``. The API key is read from ``api_key_env`` if not passed.
    """

    def __init__(
        self,
        model_id: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        temperature: float = 0.0,
        api_key_env: str = "OPENAI_API_KEY",
    ) -> None:
        self.default_model = model_id
        self.api_key = api_key or os.environ.get(api_key_env)
        self.base_url = (
            base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        if not self.api_key:
            raise ProviderError(f"missing OpenAI API key: set ${api_key_env} or pass api_key=")

    def generate(self, prompt: str, model_id: str) -> str:
        model = model_id or self.default_model
        if not model:
            raise ProviderError("no model_id given to OpenAIProvider.generate")
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = _http_post_json(f"{self.base_url}/chat/completions", headers, payload, self.timeout)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"unexpected OpenAI response shape: {data}") from exc


class AnthropicProvider(BaseProvider):
    """Messages-API provider for Anthropic (stdlib only)."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_tokens: int = 1024,
        anthropic_version: str = "2023-06-01",
        api_key_env: str = "ANTHROPIC_API_KEY",
    ) -> None:
        self.default_model = model_id
        self.api_key = api_key or os.environ.get(api_key_env)
        self.base_url = (
            base_url or os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"
        ).rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.anthropic_version = anthropic_version
        if not self.api_key:
            raise ProviderError(f"missing Anthropic API key: set ${api_key_env} or pass api_key=")

    def generate(self, prompt: str, model_id: str) -> str:
        model = model_id or self.default_model
        if not model:
            raise ProviderError("no model_id given to AnthropicProvider.generate")
        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "content-type": "application/json",
        }
        data = _http_post_json(f"{self.base_url}/v1/messages", headers, payload, self.timeout)
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"unexpected Anthropic response shape: {data}") from exc


_PROVIDERS = {
    "fake": FakeProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def build_provider(name: str, model_id: Optional[str] = None, **kwargs) -> BaseProvider:
    """Construct a provider by name (``fake`` / ``openai`` / ``anthropic``).

    ``fake`` ignores ``model_id``/kwargs; the real providers forward them.
    Raises ``ProviderError`` on an unknown name.
    """
    key = (name or "fake").lower()
    if key == "fake":
        return FakeProvider()
    cls = _PROVIDERS.get(key)
    if cls is None:
        known = ", ".join(sorted(_PROVIDERS))
        raise ProviderError(f"unknown provider {name!r}; known: {known}")
    return cls(model_id=model_id, **kwargs)
