"""Provider tests using httpx's in-process MockTransport (no real network)."""

from __future__ import annotations

import httpx
import pytest

from alpha_ioi.config import ProviderConfig
from alpha_ioi.core.models import Message, Role
from alpha_ioi.providers import (
    AnthropicProvider,
    MockProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    build_provider,
    provider_classes,
)
from alpha_ioi.providers.base import ChatProvider, ProviderError


def _user(text: str = "hi") -> Message:
    return Message(role=Role.USER, content=text)


def _collect(provider, messages=None) -> tuple[str, str | None, bool]:
    text, error, finished = "", None, False
    for delta in provider.stream(messages or [_user()]):
        text += delta.text
        error = delta.error or error
        finished = finished or delta.finished
    return text, error, finished


# --- mock --------------------------------------------------------------------


def test_mock_provider_streams_and_finishes():
    text, error, finished = _collect(MockProvider(name="mock"))
    assert finished and error is None
    assert "Alpha IOI" in text


def test_mock_provider_echoes_the_user_text():
    text, _, _ = _collect(MockProvider(name="mock"), [_user("ping pong")])
    assert "ping pong" in text


def test_mock_provider_lists_models():
    assert MockProvider(name="mock").list_models()


# --- openai compatible -------------------------------------------------------


def _openai_provider(handler, **kwargs) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name="openai",
        base_url="https://api.example.com/v1",
        model="gpt-5",
        api_key="sk-test",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def test_openai_stream_parses_sse():
    body = (
        'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer sk-test"
        return httpx.Response(
            200, content=body.encode(), headers={"content-type": "text/event-stream"}
        )

    text, error, finished = _collect(_openai_provider(handler))
    assert (text, error, finished) == ("Hello", None, True)


def test_openai_stream_honours_finish_reason():
    body = 'data: {"choices":[{"delta":{"content":"Hi"},"finish_reason":"stop"}]}\n\n'
    handler = lambda request: httpx.Response(200, content=body.encode())  # noqa: E731
    text, error, finished = _collect(_openai_provider(handler))
    assert (text, error, finished) == ("Hi", None, True)


def test_openai_stream_reports_http_errors():
    handler = lambda request: httpx.Response(  # noqa: E731
        401, json={"error": {"message": "bad key"}}
    )
    text, error, finished = _collect(_openai_provider(handler))
    assert finished and text == ""
    assert "401" in error and "bad key" in error


def test_openai_stream_reports_network_errors():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    _, error, finished = _collect(_openai_provider(handler))
    assert finished and "network error" in error


def test_openai_list_models_sorted():
    handler = lambda request: httpx.Response(  # noqa: E731
        200, json={"data": [{"id": "b"}, {"id": "a"}]}
    )
    assert _openai_provider(handler).list_models() == ["a", "b"]


def test_openai_base_url_without_v1_gets_it_appended():
    provider = OpenAICompatibleProvider(name="x", base_url="https://api.example.com")
    assert provider._endpoint("/models") == "https://api.example.com/v1/models"


def test_openai_system_prompt_is_prepended():
    import json

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, content=b"data: [DONE]\n\n")

    provider = _openai_provider(handler, system_prompt="be brief")
    list(provider.stream([_user("hi")]))
    assert captured["payload"]["messages"][0] == {"role": "system", "content": "be brief"}


# --- anthropic ---------------------------------------------------------------


def test_anthropic_stream_parses_events():
    body = (
        "event: content_block_delta\n"
        'data: {"delta":{"type":"text_delta","text":"Hel"}}\n\n'
        "event: content_block_delta\n"
        'data: {"delta":{"type":"text_delta","text":"lo"}}\n\n'
        "event: message_stop\n"
        'data: {"type":"message_stop"}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/messages"
        assert request.headers["x-api-key"] == "sk-ant"
        return httpx.Response(200, content=body.encode())

    provider = AnthropicProvider(
        name="anthropic",
        base_url="https://api.anthropic.com",
        model="claude",
        api_key="sk-ant",
        transport=httpx.MockTransport(handler),
    )
    text, error, finished = _collect(provider)
    assert (text, error, finished) == ("Hello", None, True)


def test_anthropic_error_event():
    body = 'event: error\ndata: {"type":"error","error":{"message":"overloaded"}}\n\n'

    def handler(request):
        return httpx.Response(200, content=body.encode())

    provider = AnthropicProvider(
        name="anthropic", model="claude", api_key="k", transport=httpx.MockTransport(handler)
    )
    _, error, finished = _collect(provider)
    assert finished and "overloaded" in error


# --- ollama ------------------------------------------------------------------


def test_ollama_stream_parses_ndjson():
    body = (
        '{"message":{"content":"Hel"},"done":false}\n'
        '{"message":{"content":"lo"},"done":false}\n'
        '{"message":{"content":""},"done":true}\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(200, content=body.encode())

    provider = OllamaProvider(
        name="ollama",
        base_url="http://localhost:11434",
        model="qwen3:4b",
        transport=httpx.MockTransport(handler),
    )
    text, error, finished = _collect(provider)
    assert (text, error, finished) == ("Hello", None, True)


def test_ollama_list_models():
    handler = lambda request: httpx.Response(  # noqa: E731
        200, json={"models": [{"name": "qwen3:4b"}, {"name": "llama3"}]}
    )
    provider = OllamaProvider(
        name="ollama", base_url="http://localhost:11434", transport=httpx.MockTransport(handler)
    )
    assert provider.list_models() == ["qwen3:4b", "llama3"]


def test_ollama_unreachable_is_reported():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    provider = OllamaProvider(
        name="ollama", base_url="http://localhost:11434", transport=httpx.MockTransport(handler)
    )
    _, error, finished = _collect(provider)
    assert finished and "Ollama" in error


# --- registry ----------------------------------------------------------------


def test_registry_knows_all_kinds():
    assert set(provider_classes()) == {"mock", "openai", "anthropic", "ollama"}


def test_build_provider_mock_has_default_model(secret_store):
    provider = build_provider(ProviderConfig(name="demo", kind="mock"), secret_store)
    assert isinstance(provider, MockProvider)
    assert provider.model


def test_build_provider_pulls_key_from_secret_store(secret_store):
    secret_store.set("openai", "sk-from-keyring")
    provider = build_provider(
        ProviderConfig(
            name="openai", kind="openai", base_url="https://api.openai.com/v1", model="gpt-5"
        ),
        secret_store,
    )
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.api_key == "sk-from-keyring"


def test_build_provider_rejects_unknown_kind(secret_store):
    with pytest.raises(ProviderError):
        build_provider(ProviderConfig(name="x", kind="wat"), secret_store)


def test_provider_describe():
    provider = OpenAICompatibleProvider(name="openai", model="gpt-5")
    assert provider.describe() == "OpenAI-compatible · gpt-5"


def test_base_provider_is_abstract():
    with pytest.raises(TypeError):
        ChatProvider(name="x")  # type: ignore[abstract]


def test_secret_store_none_builds_without_key():
    provider = build_provider(ProviderConfig(name="demo", kind="mock"), None)
    assert provider.name == "demo"


def test_ollama_sends_no_authorization_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        return httpx.Response(200, content=b'{"message":{"content":"x"},"done":true}\n')

    provider = OllamaProvider(
        name="ollama", base_url="http://x", transport=httpx.MockTransport(handler)
    )
    text, _, _ = _collect(provider)
    assert text == "x"
    assert "authorization" not in seen["headers"]
