"""Secret storage for provider API keys.

Keys are kept out of ``config.toml`` and out of git. On a normal desktop the
Secret Service (GNOME Keyring / KWallet) is used via ``keyring``; when no
backend is available (headless boxes, containers, CI) we transparently fall
back to a mode-0600 JSON file so the app is still usable and testable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from alpha_ioi.constants import CLI_NAME, KEYSTORE_FILE

__all__ = ["SecretStore"]


class SecretStore:
    """API key storage with a Secret Service backend and a file fallback."""

    def __init__(self, keystore: Path | None = None) -> None:
        self._keystore = Path(keystore) if keystore is not None else KEYSTORE_FILE
        self._memory: dict[str, str] = {}
        self._file_loaded = False

    # -- backend probing -------------------------------------------------------

    def _keyring_available(self) -> bool:
        try:
            import keyring
        except ImportError:
            return False
        try:
            return keyring.get_keyring() is not None
        except Exception:  # pragma: no cover - depends on the host backend
            return False

    # -- file fallback ---------------------------------------------------------

    def _load_file(self) -> dict[str, str]:
        if self._file_loaded:
            return self._memory
        self._file_loaded = True
        try:
            raw = self._keystore.read_text(encoding="utf-8")
            self._memory = json.loads(raw) if raw.strip() else {}
        except (OSError, ValueError):
            self._memory = {}
        return self._memory

    def _save_file(self) -> None:
        self._keystore.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._keystore.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._memory, ensure_ascii=False), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self._keystore)

    # -- public API ------------------------------------------------------------

    def get(self, account: str) -> str | None:
        """Return the key for ``account`` (usually the provider name)."""
        if self._keyring_available():
            try:
                import keyring

                value = keyring.get_password(CLI_NAME, account)
                if value:
                    return value
            except Exception:  # pragma: no cover - backend specific
                pass
        return self._load_file().get(account)

    def set(self, account: str, key: str) -> None:
        if self._keyring_available():
            try:
                import keyring

                keyring.set_password(CLI_NAME, account, key)
                self._load_file().pop(account, None)
                self._save_file()
                return
            except Exception:  # pragma: no cover - backend specific
                pass
        self._load_file()[account] = key
        self._save_file()

    def delete(self, account: str) -> None:
        if self._keyring_available():
            try:
                import keyring

                keyring.delete_password(CLI_NAME, account)
            except Exception:  # pragma: no cover - backend specific
                pass
        if self._load_file().pop(account, None) is not None:
            self._save_file()
