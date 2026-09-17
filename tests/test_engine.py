"""Tests for the streaming chat engine."""

from __future__ import annotations

from alpha_ioi.core.engine import conversation_payload, stream_reply
from alpha_ioi.core.models import ChatDelta, Conversation, Role
from alpha_ioi.providers.base import ChatProvider, ProviderError
from alpha_ioi.providers.mock import MockProvider


def _drain(provider, conversation, model="") -> tuple[str, str | None, bool]:
    text, error, finished = "", None, False
    for delta in stream_reply(provider, conversation, model=model):
        text += delta.text
        error = delta.error or error
        finished = finished or delta.finished
    return text, error, finished


def test_stream_reply_uses_mock_provider():
    conversation = Conversation()
    conversation.add(Role.USER, "hello world")
    text, error, finished = _drain(MockProvider(name="mock"), conversation)
    assert finished and error is None
    assert "hello world" in text


def test_stream_reply_requires_a_user_message():
    conversation = Conversation()
    _, error, finished = _drain(MockProvider(name="mock"), conversation)
    assert finished and "no user message" in error


class _BoomProvider(ChatProvider):
    label = "boom"

    def list_models(self):
        return []

    def stream(self, messages, model=""):
        raise ProviderError("kaboom")
        yield  # pragma: no cover


def test_stream_reply_turns_provider_error_into_finished_delta():
    conversation = Conversation()
    conversation.add(Role.USER, "hi")
    _, error, finished = _drain(_BoomProvider(name="boom"), conversation)
    assert finished and error == "kaboom"


class _UnexpectedProvider(ChatProvider):
    label = "unexpected"

    def list_models(self):
        return []

    def stream(self, messages, model=""):
        raise RuntimeError("surprise")
        yield  # pragma: no cover


def test_stream_reply_never_raises_on_unexpected_errors():
    conversation = Conversation()
    conversation.add(Role.USER, "hi")
    _, error, finished = _drain(_UnexpectedProvider(name="x"), conversation)
    assert finished and "unexpected error" in error


class _SilentProvider(ChatProvider):
    label = "silent"

    def list_models(self):
        return []

    def stream(self, messages, model=""):
        return iter(())


def test_stream_reply_adds_finished_when_provider_forgets():
    conversation = Conversation()
    conversation.add(Role.USER, "hi")
    text, error, finished = _drain(_SilentProvider(name="silent"), conversation)
    assert (text, error, finished) == ("", None, True)


def test_conversation_payload_shape():
    conversation = Conversation()
    conversation.add(Role.USER, "hi")
    assert conversation_payload(conversation) == [{"role": "user", "content": "hi"}]


def test_chat_delta_default_construction():
    delta = ChatDelta(text="x")
    assert delta.text == "x" and delta.error is None and delta.finished is False
