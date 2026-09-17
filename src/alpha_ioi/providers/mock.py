"""Offline mock provider.

Needs no network and no API key, so first-launch works and the test suite is
hermetic. It emits canned, deterministic replies word by word to exercise the
same streaming path as a real provider.
"""

from __future__ import annotations

from collections.abc import Iterator

from alpha_ioi.core.models import ChatDelta, Message
from alpha_ioi.providers.base import ChatProvider

__all__ = ["MockProvider"]

_MOCK_MODELS = ["alpha-ioi-demo-1", "alpha-ioi-demo-2"]

_CANNED = (
    "Hello from Alpha IOI's offline demo mode. I am a stand-in for a real model: "
    "I echo a little context back so you can try the whole interface without "
    "configuring an API key. To talk to a real model, add a provider to "
    "{config_path} and pick it in the sidebar."
)


class MockProvider(ChatProvider):
    label = "Demo (offline)"

    def list_models(self) -> list[str]:
        return list(_MOCK_MODELS)

    def stream(self, messages: list[Message], model: str = "") -> Iterator[ChatDelta]:
        yield from self._tokenize(self._reply(messages))
        yield ChatDelta.done()

    def _reply(self, messages: list[Message]) -> str:
        last = next((m.content for m in reversed(messages) if m.role.value == "user"), "")
        prefix = _CANNED.format(config_path="~/.config/alpha-ioi/config.toml")
        if last:
            preview = last.strip().replace("\n", " ")
            if len(preview) > 160:
                preview = preview[:157] + "..."
            return f"{prefix}\n\nYou said: “{preview}”"
        return prefix

    @staticmethod
    def _tokenize(text: str) -> Iterator[ChatDelta]:
        for word in text.split(" "):
            yield ChatDelta(text=word + " ")
