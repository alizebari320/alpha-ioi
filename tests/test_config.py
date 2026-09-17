"""Tests for configuration and secret storage."""

from __future__ import annotations

import stat

import pytest

from alpha_ioi.config import ConfigManager
from alpha_ioi.config.manager import DEFAULT_PROVIDER_KIND, load_example_config

# --- secrets -----------------------------------------------------------------


def test_secret_roundtrip_file_fallback(secret_store, tmp_path):
    secret_store.set("openai", "sk-test")
    assert secret_store.get("openai") == "sk-test"
    secret_store.delete("openai")
    assert secret_store.get("openai") is None


def test_secret_file_is_private(secret_store):
    secret_store.set("openai", "sk-test")
    mode = stat.S_IMODE(secret_store._keystore.stat().st_mode)
    assert mode == 0o600


def test_secret_missing_returns_none(secret_store):
    assert secret_store.get("nope") is None


# --- config ------------------------------------------------------------------


def test_default_config_is_usable_offline(config_manager):
    config = config_manager.load()
    assert config.active_provider == DEFAULT_PROVIDER_KIND
    assert DEFAULT_PROVIDER_KIND in config.providers
    assert config.provider().kind == "mock"


def test_save_then_load_roundtrip(config_manager):
    config_manager.load()
    config_manager.ensure_provider(
        "ollama", "ollama", base_url="http://localhost:11434", model="qwen3:4b"
    )
    config_manager.set_active("ollama")

    fresh = ConfigManager(path=config_manager.path, secrets=config_manager.secrets)
    config = fresh.load()
    assert config.active_provider == "ollama"
    assert config.providers["ollama"].kind == "ollama"
    assert config.providers["ollama"].base_url == "http://localhost:11434"
    assert config.providers["ollama"].model == "qwen3:4b"


def test_api_key_is_moved_out_of_the_file(config_manager, secret_store):
    config_manager.path.parent.mkdir(parents=True, exist_ok=True)
    config_manager.path.write_text(
        'active_provider = "openai"\n'
        "[providers.openai]\n"
        'kind = "openai"\n'
        'base_url = "https://api.openai.com/v1"\n'
        'model = "gpt-5"\n'
        'api_key = "sk-secret"\n',
        encoding="utf-8",
    )

    config = config_manager.load()
    assert secret_store.get("openai") == "sk-secret"
    assert "sk-secret" not in config_manager.path.read_text(encoding="utf-8")
    assert config.providers["openai"].api_key == ""


def test_unknown_provider_kind_is_ignored(config_manager):
    config_manager.path.parent.mkdir(parents=True, exist_ok=True)
    config_manager.path.write_text(
        'active_provider = "weird"\n[providers.weird]\nkind = "not-a-real-kind"\n',
        encoding="utf-8",
    )
    config = config_manager.load()
    assert "weird" not in config.providers


def test_set_active_rejects_unknown(config_manager):
    config_manager.load()
    with pytest.raises(KeyError):
        config_manager.set_active("ghost")


def test_ensure_provider_stores_key_out_of_band(config_manager, secret_store):
    config_manager.load()
    config_manager.ensure_provider(
        "anthropic",
        "anthropic",
        base_url="https://api.anthropic.com",
        model="claude-sonnet-4-5",
        api_key="sk-ant-xyz",
    )
    assert secret_store.get("anthropic") == "sk-ant-xyz"
    assert "sk-ant-xyz" not in config_manager.path.read_text(encoding="utf-8")


def test_provider_falls_back_when_active_is_unknown(config_manager):
    config_manager.load()
    config_manager.config.active_provider = "missing"
    assert config_manager.config.provider().kind == "mock"


def test_window_size_persisted(config_manager):
    config_manager.load()
    config_manager.config.window_width = 999
    config_manager.config.window_height = 555
    config_manager.save()

    fresh = ConfigManager(path=config_manager.path, secrets=config_manager.secrets)
    config = fresh.load()
    assert config.window_width == 999
    assert config.window_height == 555


def test_example_config_is_discoverable_and_valid_toml():
    import tomllib

    text = load_example_config()
    parsed = tomllib.loads(text)
    assert parsed["active_provider"] == "demo"
    assert "demo" in parsed["providers"]
