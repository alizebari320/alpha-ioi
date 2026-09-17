"""Application-wide constants for Alpha.

Every user-visible name and every technical name lives here so the rest of the
codebase never hard-codes them. Identity rules:

    user-visible name .. "Alpha"
    Python package ..... ``alpha_ioi``
    executable / repo .. ``alpha``
"""

from __future__ import annotations

import os
from importlib import metadata
from pathlib import Path

__all__ = [
    "APP_AUTHOR",
    "APP_DESCRIPTION",
    "APP_ID",
    "APP_NAME",
    "CLI_NAME",
    "CONFIG_DIR",
    "CONFIG_FILE",
    "DEVELOPER_EMAIL",
    "HELP_URL",
    "HISTORY_DIR",
    "ICON_NAME",
    "ISSUES_URL",
    "PACKAGE_NAME",
    "STATE_DIR",
    "VERSION",
]

# --- Identity -----------------------------------------------------------------

#: User-visible application name. Used in the window title, header, README,
#: docs and About dialog.
APP_NAME = "Alpha"

#: Importable Python package name.
PACKAGE_NAME = "alpha_ioi"

#: Console script / repository / distribution name (kebab-case).
CLI_NAME = "alpha"

#: GApplication / Wayland app id. Drives the app id shown by the compositor.
APP_ID = "io.github.aliarifmuhammed.Alpha"

#: Icon name registered against the icon theme. Matches the filename of
#: ``assets/icons/alpha.svg``.
ICON_NAME = "alpha"

APP_AUTHOR = "Ali Arif Muhammed"
DEVELOPER_EMAIL = "aliarifmuhammed@users.noreply.github.com"
APP_DESCRIPTION = (
    "A native Linux desktop chat client that talks to many LLM providers from one window."
)
WEBSITE_URL = "https://github.com/aliarifmuhammed/alpha"
ISSUES_URL = f"{WEBSITE_URL}/issues"
HELP_URL = f"{WEBSITE_URL}#configuration"

#: Release version. Falls back to a sentinel when the package is run straight
#: from a checkout (e.g. ``python -m alpha_ioi`` in a source tree) before it is
#: installed.
_VERSION_FALLBACK = "0.0.0+unknown"


def _resolve_version() -> str:
    try:
        return metadata.version(CLI_NAME)
    except metadata.PackageNotFoundError:
        return _VERSION_FALLBACK


VERSION = os.environ.get("ALPHA_VERSION") or _resolve_version()

# --- Paths --------------------------------------------------------------------


def _xdg(env_var: str, fallback: str) -> Path:
    return Path(os.environ.get(env_var) or (Path.home() / fallback))


CONFIG_DIR = _xdg("XDG_CONFIG_HOME", ".config") / CLI_NAME
CONFIG_FILE = CONFIG_DIR / "config.toml"

STATE_DIR = _xdg("XDG_STATE_HOME", ".local/state") / CLI_NAME
HISTORY_DIR = STATE_DIR / "history"

#: Where the fallback key store lives when no Secret Service backend exists.
KEYSTORE_FILE = CONFIG_DIR / "keys.json"

#: Filename of the bundled example configuration (repo-root ``config/``).
EXAMPLE_CONFIG_FILENAME = f"{CLI_NAME}.example.toml"
