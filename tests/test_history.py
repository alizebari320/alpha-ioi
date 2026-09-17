"""Tests for conversation persistence."""

from __future__ import annotations

from alpha_ioi.core.models import Conversation, Role


def test_record_then_load_roundtrip(history_store):
    conversation = Conversation(provider="ollama", model="qwen3:4b")
    history_store.record(conversation, conversation.add(Role.USER, "hello"))
    history_store.record(conversation, conversation.add(Role.ASSISTANT, "hi there"))

    loaded = history_store.load_conversation(conversation.id)
    assert loaded is not None
    assert loaded.title == "hello"
    assert loaded.provider == "ollama"
    assert loaded.model == "qwen3:4b"
    assert [(m.role, m.content) for m in loaded.messages] == [
        (Role.USER, "hello"),
        (Role.ASSISTANT, "hi there"),
    ]


def test_list_conversations_newest_first(history_store):
    first = Conversation(title="first")
    second = Conversation(title="second")
    history_store.save_header(first)
    history_store.save_header(second)

    titles = [c.title for c in history_store.list_conversations()]
    assert set(titles) == {"first", "second"}


def test_delete_removes_files(history_store):
    conversation = Conversation()
    history_store.record(conversation, conversation.add(Role.USER, "x"))
    history_store.delete(conversation.id)
    assert history_store.load_conversation(conversation.id) is None
    assert list(history_store.root.glob("*.jsonl")) == []


def test_clear_removes_everything(history_store):
    for i in range(3):
        conversation = Conversation(title=f"c{i}")
        history_store.record(conversation, conversation.add(Role.USER, f"m{i}"))
    history_store.clear()
    assert history_store.list_conversations() == []


def test_load_missing_returns_none(history_store):
    assert history_store.load_conversation("does-not-exist") is None


def test_corrupt_meta_is_skipped(history_store):
    (history_store.root / "broken.meta.json").write_text("{not json", encoding="utf-8")
    assert history_store.list_conversations() == []


def test_corrupt_log_line_is_skipped(history_store):
    conversation = Conversation()
    history_store.record(conversation, conversation.add(Role.USER, "good"))
    with (history_store.root / f"{conversation.id}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{also not json\n")
    loaded = history_store.load_conversation(conversation.id)
    assert loaded is not None
    assert [m.content for m in loaded.messages] == ["good"]
