"""Tests for the core data models."""

from __future__ import annotations

from alpha_ioi.core.models import ChatDelta, Conversation, Message, Role


def test_message_payload():
    message = Message(role=Role.USER, content="hi")
    assert message.to_payload() == {"role": "user", "content": "hi"}


def test_conversation_title_from_first_user_message():
    conversation = Conversation()
    conversation.add(Role.USER, "Explain quantum tunnelling please")
    assert conversation.title == "Explain quantum tunnelling please"


def test_conversation_title_uses_first_line_only():
    conversation = Conversation()
    conversation.add(Role.USER, "First line\nSecond line")
    assert conversation.title == "First line"


def test_conversation_title_is_truncated():
    conversation = Conversation()
    conversation.add(Role.USER, "x" * 200)
    assert len(conversation.title) == 60


def test_conversation_title_stays_new_chat_for_assistant_only():
    conversation = Conversation()
    conversation.add(Role.ASSISTANT, "hello there")
    assert conversation.title == "New chat"


def test_last_user_message_skips_assistant():
    conversation = Conversation()
    conversation.add(Role.USER, "one")
    conversation.add(Role.ASSISTANT, "two")
    conversation.add(Role.USER, "three")
    assert conversation.last_user_message().content == "three"


def test_to_payloads_can_exclude_system():
    conversation = Conversation()
    conversation.add(Role.SYSTEM, "be nice")
    conversation.add(Role.USER, "hi")
    assert conversation.to_payloads(include_system=False) == [{"role": "user", "content": "hi"}]


def test_is_empty():
    conversation = Conversation()
    assert conversation.is_empty()
    conversation.add(Role.USER, "hi")
    assert not conversation.is_empty()


def test_add_updates_updated_at():
    conversation = Conversation()
    before = conversation.updated_at
    conversation.add(Role.USER, "hi")
    assert conversation.updated_at >= before


def test_chat_delta_done():
    delta = ChatDelta.done("boom")
    assert delta.finished is True
    assert delta.error == "boom"
    assert delta.text == ""
