"""Provider interface shared by every LLM backend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from alpha_ioi.core.models import ChatDelta, Message

__all__ = ["ChatProvider", "ProviderError"]


class ProviderError(RuntimeError):
    """A provider failed in a way worth showing the user in the chat."""


class ChatProvider(ABC):
    """Base class for all chat providers.

    Providers are synchronous generators: :meth:`stream` blocks and yields
    :class:`~alpha_ioi.core.models.ChatDelta` chunks. The UI runs each stream
    on a worker thread and forwards deltas to the main loop with
    ``GLib.idle_add``, so blocking HTTP calls never freeze the window.
    """

    #: Human-friendly label for the model picker.
    label: str = ""

    def __init__(
        self,
        name: str,
        model: str = "",
        system_prompt: str = "",
        api_key: str = "",
        base_url: str = "",
    ) -> None:
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else ""

    # -- API -------------------------------------------------------------------

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return model ids this provider can serve."""

    @abstractmethod
    def stream(self, messages: list[Message], model: str = "") -> Iterator[ChatDelta]:
        """Yield streamed deltas for ``messages``; always ends with a finished delta."""

    # -- helpers ---------------------------------------------------------------

    def resolve_model(self, model: str = "") -> str:
        return (model or self.model).strip()

    def describe(self) -> str:
        model = self.resolve_model() or "no model set"
        return f"{self.label or self.name} · {model}"
