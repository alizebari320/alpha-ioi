"""Anthropic-native provider (Messages API with SSE streaming)."""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from alpha_ioi.core.models import ChatDelta, Message
from alpha_ioi.providers.base import ChatProvider, ProviderError

__all__ = ["AnthropicProvider"]

_API_VERSION = "2023-06-01"


class AnthropicProvider(ChatProvider):
    label = "Anthropic"

    DEFAULT_BASE_URL = "https://api.anthropic.com"

    def __init__(
        self,
        *args,
        client: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._transport = transport
        self._client = client

    def _endpoint(self, path: str) -> str:
        base = self.base_url or self.DEFAULT_BASE_URL
        return base.rstrip("/") + path

    def _headers(self) -> dict[str, str]:
        headers = {
            "content-type": "application/json",
            "accept": "text/event-stream",
            "anthropic-version": _API_VERSION,
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(20.0, read=None), transport=self._transport
            )
        return self._client

    def list_models(self) -> list[str]:
        try:
            response = self._http().get(
                self._endpoint("/v1/models"), headers=self._headers(), timeout=20.0
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"could not list models for {self.name}: {exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover
            raise ProviderError(f"{self.name} returned a malformed model list") from exc
        return sorted(item["id"] for item in payload.get("data", []) if item.get("id")) or (
            [self.model] if self.model else []
        )

    def stream(self, messages: list[Message], model: str = "") -> Iterator[ChatDelta]:
        system, payload = self._payload(messages)
        body: dict[str, object] = {
            "model": self.resolve_model(model),
            "messages": payload,
            "max_tokens": 4096,
            "stream": True,
        }
        if system:
            body["system"] = system
        try:
            with self._http().stream(
                "POST", self._endpoint("/v1/messages"), json=body, headers=self._headers()
            ) as response:
                response.raise_for_status()
                yield from self._parse_stream(response)
        except httpx.HTTPStatusError as exc:
            yield ChatDelta.done(_http_error(exc))
        except httpx.HTTPError as exc:
            yield ChatDelta.done(f"network error talking to {self.name}: {exc}")
        except ProviderError as exc:
            yield ChatDelta.done(str(exc))

    def _payload(self, messages: list[Message]) -> tuple[str, list[dict[str, str]]]:
        system = self.system_prompt or ""
        payload = [m.to_payload() for m in messages if m.role.value != "system"]
        if not system:
            for msg in messages:
                if msg.role.value == "system":
                    system = msg.content
                    break
        return system, payload

    @staticmethod
    def _parse_stream(response: httpx.Response) -> Iterator[ChatDelta]:
        event_type = ""
        for raw in response.iter_lines():
            line = raw.strip()
            if not line:
                event_type = ""
                continue
            if line.startswith("event:"):
                event_type = line[len("event:") :].strip()
                continue
            if not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            try:
                chunk = json.loads(data)
            except ValueError:
                continue
            if event_type == "content_block_delta":
                delta = chunk.get("delta", {})
                text = delta.get("text") or ""
                if text:
                    yield ChatDelta(text=text)
            elif event_type in {"message_stop", "error"}:
                if event_type == "error":
                    yield ChatDelta.done(chunk.get("error", {}).get("message", "stream error"))
                    return
                yield ChatDelta.done()
                return
        yield ChatDelta.done()


def _http_error(exc: httpx.HTTPStatusError) -> str:
    try:
        body = exc.response.json()
        detail = body.get("error", {}).get("message") or body
    except Exception:
        detail = exc.response.text[:200]
    return f"{exc.response.status_code} from {exc.request.url.host}: {detail}"
