"""OpenAI-compatible provider.

One class covers everything that speaks the OpenAI Chat Completions API:
OpenAI itself, OpenRouter, AgentRouter, TokenHarbor, LocalAI, vLLM, and
Ollama's ``/v1`` endpoint. Streaming uses server-sent events.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from alpha_ioi.core.models import ChatDelta, Message
from alpha_ioi.providers.base import ChatProvider, ProviderError

__all__ = ["OpenAICompatibleProvider"]

_SSE_DONE = "[DONE]"


class OpenAICompatibleProvider(ChatProvider):
    label = "OpenAI-compatible"

    #: Default endpoint when config gives no base_url.
    DEFAULT_BASE_URL = "https://api.openai.com"

    def __init__(
        self,
        *args,
        client: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        #: Optional injected transport - tests use it to fake the network.
        self._transport = transport
        self._client = client

    # -- plumbing --------------------------------------------------------------

    def _endpoint(self, path: str) -> str:
        base = self.base_url or self.DEFAULT_BASE_URL
        if not base.rstrip("/").endswith("/v1"):
            base = base.rstrip("/") + "/v1"
        return base + path

    def _headers(self) -> dict[str, str]:
        headers = {"content-type": "application/json", "accept": "text/event-stream"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        return headers

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(20.0, read=None), transport=self._transport
            )
        return self._client

    # -- API -------------------------------------------------------------------

    def list_models(self) -> list[str]:
        try:
            response = self._http().get(
                self._endpoint("/models"), headers=self._headers(), timeout=20.0
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"could not list models for {self.name}: {exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - malformed upstream reply
            raise ProviderError(f"{self.name} returned a malformed model list") from exc
        return sorted(item["id"] for item in payload.get("data", []) if item.get("id")) or (
            [self.model] if self.model else []
        )

    def stream(self, messages: list[Message], model: str = "") -> Iterator[ChatDelta]:
        payload = {
            "model": self.resolve_model(model),
            "messages": self._payload(messages),
            "stream": True,
        }
        try:
            with self._http().stream(
                "POST",
                self._endpoint("/chat/completions"),
                json=payload,
                headers=self._headers(),
            ) as response:
                response.raise_for_status()
                yield from self._parse_stream(response)
        except httpx.HTTPStatusError as exc:
            yield ChatDelta.done(_http_error(exc))
        except httpx.HTTPError as exc:
            yield ChatDelta.done(f"network error talking to {self.name}: {exc}")
        except ProviderError as exc:
            yield ChatDelta.done(str(exc))

    # -- helpers ---------------------------------------------------------------

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
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if data == _SSE_DONE:
                yield ChatDelta.done()
                return
            try:
                chunk = json.loads(data)
            except ValueError:
                continue
            for choice in chunk.get("choices", []):
                delta = choice.get("delta", {})
                text = delta.get("content") or ""
                if text:
                    yield ChatDelta(text=text)
                if choice.get("finish_reason"):
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
