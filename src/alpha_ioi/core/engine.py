"""Streaming chat engine.

Bridges a :class:`~alpha_ioi.core.models.Conversation` and a
:class:`~alpha_ioi.providers.base.ChatProvider`, yielding
:class:`~alpha_ioi.core.models.ChatDelta` chunks until the stream finishes.
"""

from __future__ import annotations

from collections.abc import Iterator

from alpha_ioi.core.models import ChatDelta, Conversation
from alpha_ioi.providers.base import ChatProvider, ProviderError

__all__ = ["conversation_payload", "stream_reply"]


def stream_reply(
    provider: ChatProvider,
    conversation: Conversation,
    model: str = "",
) -> Iterator[ChatDelta]:
    """Stream a reply to the last user message in ``conversation``.

    Always terminates with a finished delta, including on failure, so callers
    can rely on a single end-of-stream signal to clean up UI state.
    """
    model = (model or conversation.model or provider.model).strip()
    try:
        if not conversation.last_user_message():
            yield ChatDelta.done("nothing to send: the conversation has no user message")
            return
        stream = provider.stream(conversation.messages, model=model)
        finished = False
        for delta in stream:
            yield delta
            if delta.finished:
                finished = True
                return
        if not finished:
            yield ChatDelta.done()
    except ProviderError as exc:
        yield ChatDelta.done(str(exc))
    except Exception as exc:
        yield ChatDelta.done(f"unexpected error from {provider.name}: {exc}")


def conversation_payload(conversation: Conversation) -> list[dict[str, str]]:
    """Message list exactly as it will be sent to the provider."""
    return conversation.to_payloads()
