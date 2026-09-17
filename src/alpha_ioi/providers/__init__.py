"""LLM providers: one interface, several backends."""

from alpha_ioi.providers.anthropic import AnthropicProvider
from alpha_ioi.providers.base import ChatProvider, ProviderError
from alpha_ioi.providers.mock import MockProvider
from alpha_ioi.providers.ollama import OllamaProvider
from alpha_ioi.providers.openai_compat import OpenAICompatibleProvider
from alpha_ioi.providers.registry import build_provider, provider_classes, provider_label

__all__ = [
    "AnthropicProvider",
    "ChatProvider",
    "MockProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "ProviderError",
    "build_provider",
    "provider_classes",
    "provider_label",
]
