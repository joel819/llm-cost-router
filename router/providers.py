"""OpenAI-compatible providers (Groq, NVIDIA, OpenRouter, ...) behind one small interface."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI

from .config import Config, Tier
from .cost import Usage
from .errors import ProviderError


@dataclass(frozen=True)
class Reply:
    text: str
    usage: Usage


class ChatProvider(Protocol):
    def chat(self, tier: Tier, system: str, user: str, max_tokens: int) -> Reply: ...


class OpenAICompatProvider:
    def __init__(self, cfg: Config, timeout: float = 60.0, max_retries: int = 5):
        self.cfg, self.timeout, self.max_retries = cfg, timeout, max_retries
        self._clients: dict[str, OpenAI] = {}
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def _client(self, provider: str) -> OpenAI:
        if provider not in self._clients:
            p = self.cfg.providers[provider]
            if not p.api_key:
                raise ProviderError(f"{p.api_key_env} is not set (needed for provider {provider!r})")
            self._clients[provider] = OpenAI(api_key=p.api_key, base_url=p.base_url, timeout=self.timeout,
                                             max_retries=self.max_retries)   # SDK backs off on 429/5xx
        return self._clients[provider]

    def _throttle(self, provider: str) -> None:
        gap = self.cfg.min_interval
        if gap <= 0:
            return
        with self._lock:
            wait = self._last.get(provider, 0) + gap - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last[provider] = time.monotonic()

    def chat(self, tier: Tier, system: str, user: str, max_tokens: int) -> Reply:
        client = self._client(tier.provider)
        self._throttle(tier.provider)
        try:
            r = client.chat.completions.create(
                model=tier.model, temperature=0, max_tokens=max_tokens,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                **({"extra_body": tier.params} if tier.params else {}))
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"{tier.provider}/{tier.model}: {type(exc).__name__}: {exc}") from exc
        u = r.usage
        usage = Usage(getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0) if u else Usage()
        return Reply((r.choices[0].message.content or "").strip(), usage)

    def list_models(self, provider: str) -> list[str]:
        try:
            return sorted(m.id for m in self._client(provider).models.list())
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"{provider}: {type(exc).__name__}: {exc}") from exc
