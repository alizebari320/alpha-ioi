"""Ollama-native provider (local ``/api/chat`` NDJSON streaming, no API key)."""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from alpha_ioi.core.models import ChatDelta, Message
from alpha_ioi.providers.base import ChatProvider, ProviderError

__all__ = ["OllamaProvider"]


class OllamaProvider(ChatProvider):
    label = "Ollama (local)"

    DEFAULT_BASE_URL = "http://localhost:11434"

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

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(20.0, read=None), transport=self._transport
            )
        return self._client

    def list_models(self) -> list[str]:
        try:
            response = self._http().get(self._endpoint("/api/tags"), timeout=10.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"is Ollama running? {self.name}: {exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover
            raise ProviderError(f"{self.name} returned a malformed model list") from exc
        return [item["name"] for item in payload.get("models", []) if item.get("name")]

    def stream(self, messages: list[Message], model: str = "") -> Iterator[ChatDelta]:
        payload = {
            "model": self.resolve_model(model),
            "messages": self._payload(messages),
            "stream": True,
        }
        try:
            with self._http().stream(
                "POST", self._endpoint("/api/chat"), json=payload, timeout=None
            ) as response:
                response.raise_for_status()
                yield from self._parse_stream(response)
        except httpx.HTTPStatusError as exc:
            yield ChatDelta.done(_http_error(exc))
        except httpx.HTTPError as exc:
            yield ChatDelta.done(f"is Ollama running? {self.name}: {exc}")
        except ProviderError as exc:
            yield ChatDelta.done(str(exc))

    def _payload(self, messages: list[Message]) -> list[dict[str, str]]:
        system = self.system_prompt or ""
        payload = [m.to_payload() for m in messages if m.role.value != "system"]
        if system:
            payload.insert(0, {"role": "system", "content": system})
        return payload

    @staticmethod
    def _parse_stream(response: httpx.Response) -> Iterator[ChatDelta]:
        for raw in response.iter_lines():
            line = raw.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except ValueError:
                continue
            if chunk.get("error"):
                yield ChatDelta.done(str(chunk["error"]))
                return
            text = (chunk.get("message") or {}).get("content") or ""
            if text:
                yield ChatDelta(text=text)
            if chunk.get("done"):
                yield ChatDelta.done()
                return
        yield ChatDelta.done()


def _http_error(exc: httpx.HTTPStatusError) -> str:
    try:
        body = exc.response.json()
        detail = body.get("error") or body
    except Exception:
        detail = exc.response.text[:200]
    return f"{exc.response.status_code} from {exc.request.url.host}: {detail}"
