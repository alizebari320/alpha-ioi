"""Turn provider configs into live provider objects."""

from __future__ import annotations

import httpx

from alpha_ioi.config import ProviderConfig, SecretStore
from alpha_ioi.providers.anthropic import AnthropicProvider
from alpha_ioi.providers.base import ChatProvider, ProviderError
from alpha_ioi.providers.mock import MockProvider
from alpha_ioi.providers.ollama import OllamaProvider
from alpha_ioi.providers.openai_compat import OpenAICompatibleProvider

__all__ = ["build_provider", "provider_classes", "provider_label"]

_KIND_TO_CLASS: dict[str, type[ChatProvider]] = {
    "mock": MockProvider,
    "openai": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
}


def provider_classes() -> dict[str, type[ChatProvider]]:
    """Known provider kinds, keyed by the ``kind`` string used in config."""
    return dict(_KIND_TO_CLASS)


def provider_label(kind: str) -> str:
    cls = _KIND_TO_CLASS.get(kind)
    return cls.label if cls else kind


def build_provider(
    config: ProviderConfig,
    secrets: SecretStore | None = None,
    *,
    transport: httpx.BaseTransport | None = None,
) -> ChatProvider:
    """Construct a provider from its config.

    ``transport`` lets tests (and the mock-first demo) run with no network.
    """
    cls = _KIND_TO_CLASS.get(config.kind)
    if cls is None:
        raise ProviderError(f"unknown provider kind {config.kind!r}")

    api_key = ""
    if secrets is not None:
        api_key = secrets.get(config.name) or ""

    if cls is MockProvider:
        provider = cls(
            name=config.name,
            model=config.model or _MOCK_DEFAULT_MODEL,
            system_prompt=config.system_prompt,
        )
    else:
        provider = cls(
            name=config.name,
            model=config.model,
            system_prompt=config.system_prompt,
            api_key=api_key,
            base_url=config.base_url,
            transport=transport,
        )
    # A configured title (e.g. "Atria") reads better than the generic class
    # label; describe() and the sidebar both use it.
    if config.title:
        provider.label = config.title
    return provider


_MOCK_DEFAULT_MODEL = "alpha-ioi-demo-1"
