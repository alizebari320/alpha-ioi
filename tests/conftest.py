"""Shared pytest fixtures.

Every test gets its own config/state/keystore under ``tmp_path`` so nothing
touches the developer's real ``~/.config/alpha-ioi``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from alpha_ioi.config import ConfigManager, SecretStore  # noqa: E402
from alpha_ioi.core.history import HistoryStore  # noqa: E402


@pytest.fixture
def secret_store(tmp_path, monkeypatch) -> SecretStore:
    """A SecretStore pinned to a temp file, with the keyring backend disabled."""
    store = SecretStore(keystore=tmp_path / "keys.json")
    monkeypatch.setattr(store, "_keyring_available", lambda: False)
    return store


@pytest.fixture
def config_manager(tmp_path, secret_store) -> ConfigManager:
    return ConfigManager(path=tmp_path / "config.toml", secrets=secret_store)


@pytest.fixture
def history_store(tmp_path) -> HistoryStore:
    return HistoryStore(root=tmp_path / "history")
