"""Conversation persistence (one JSONL file per conversation)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from alpha_ioi.constants import HISTORY_DIR
from alpha_ioi.core.models import Conversation, Message, Role

__all__ = ["HistoryStore"]


class HistoryStore:
    """Append-only JSONL store, one file per conversation.

    Each line is ``{"role": ..., "content": ..., "created_at": ...}``. The
    conversation header (id/title/provider/model) is written to a sibling
    ``.meta.json`` file so loading the list of chats is cheap.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else HISTORY_DIR
        self.root.mkdir(parents=True, exist_ok=True)

    # -- paths ----------------------------------------------------------------

    def _meta_path(self, conversation_id: str) -> Path:
        return self.root / f"{conversation_id}.meta.json"

    def _log_path(self, conversation_id: str) -> Path:
        return self.root / f"{conversation_id}.jsonl"

    # -- writes ---------------------------------------------------------------

    def save_header(self, conversation: Conversation) -> None:
        payload = {
            "id": conversation.id,
            "title": conversation.title,
            "provider": conversation.provider,
            "model": conversation.model,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }
        tmp = self._meta_path(conversation.id).with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._meta_path(conversation.id))

    def append_message(self, conversation: Conversation, message: Message) -> None:
        line = json.dumps(
            message.to_payload() | {"created_at": message.created_at.isoformat()},
            ensure_ascii=False,
        )
        with self._log_path(conversation.id).open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def record(self, conversation: Conversation, message: Message) -> Message:
        """Persist a message then refresh (and store) the conversation header."""
        self.append_message(conversation, message)
        self.save_header(conversation)
        return message

    def delete(self, conversation_id: str) -> None:
        for path in (self._log_path(conversation_id), self._meta_path(conversation_id)):
            path.unlink(missing_ok=True)

    def clear(self) -> None:
        for path in self.root.glob("*.jsonl"):
            path.unlink(missing_ok=True)
        for path in self.root.glob("*.meta.json"):
            path.unlink(missing_ok=True)

    # -- reads ----------------------------------------------------------------

    def list_conversations(self) -> list[Conversation]:
        metas = []
        for meta_path in sorted(
            self.root.glob("*.meta.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            metas.append(
                Conversation(
                    id=data["id"],
                    title=data.get("title") or "New chat",
                    provider=data.get("provider", ""),
                    model=data.get("model", ""),
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                )
            )
        return metas

    def load_conversation(self, conversation_id: str) -> Conversation | None:
        meta_path = self._meta_path(conversation_id)
        if not meta_path.exists():
            return None
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        conversation = Conversation(
            id=data["id"],
            title=data.get("title") or "New chat",
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
        log_path = self._log_path(conversation_id)
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                role = Role(item.get("role", "user"))
                content = item.get("content", "")
                created_at = item.get("created_at")
                conversation.messages.append(
                    Message(
                        role=role,
                        content=content,
                        created_at=_parse_dt(created_at),
                    )
                )
        return conversation


def _parse_dt(value: str | None) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.now(UTC)
