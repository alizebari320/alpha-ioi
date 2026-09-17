"""Core chat data models.

Provider-agnostic primitives shared by the whole app. Nothing in this module
knows how a reply is produced - that is the providers' job.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

__all__ = [
    "ChatDelta",
    "Conversation",
    "Message",
    "Role",
]


class Role(StrEnum):
    """Chat message role, matching the shape every provider understands."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(slots=True)
class Message:
    """A single chat message."""

    role: Role
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_payload(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content}


@dataclass(slots=True)
class ChatDelta:
    """One streamed chunk of a reply.

    Exactly one of ``text`` / ``error`` is meaningful per delta. ``finished``
    marks the end of a stream in both the success and the failure case.
    """

    text: str = ""
    error: str | None = None
    finished: bool = False

    @classmethod
    def done(cls, error: str | None = None) -> ChatDelta:
        return cls(error=error, finished=True)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class Conversation:
    """A conversation. Persisted as one JSONL file by :mod:`alpha_ioi.core.history`."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "New chat"
    messages: list[Message] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def touch(self) -> None:
        self.updated_at = _now_iso()

    def add(self, role: Role, content: str) -> Message:
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        if role is Role.USER and (not self.title or self.title == "New chat"):
            self.title = content.strip().splitlines()[0][:60] or "New chat"
        self.touch()
        return msg

    def last_user_message(self) -> Message | None:
        for msg in reversed(self.messages):
            if msg.role is Role.USER:
                return msg
        return None

    def to_payloads(self, include_system: bool = True) -> list[dict[str, str]]:
        return [
            m.to_payload() for m in self.messages if include_system or m.role is not Role.SYSTEM
        ]

    def is_empty(self) -> bool:
        return not any(m.role is not Role.SYSTEM for m in self.messages)
