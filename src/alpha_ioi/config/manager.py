"""Configuration management.

Configuration lives at ``$XDG_CONFIG_HOME/alpha-ioi/config.toml`` (see
:mod:`alpha_ioi.constants`). Structure::

    active_provider = "ollama"

    [providers.ollama]
    kind = "ollama"
    base_url = "http://localhost:11434"
    model = "qwen3:4b"

    [providers.openai]
    kind = "openai"
    base_url = "https://api.openai.com/v1"
    model = "gpt-5"

API keys are never written here - they go to the Secret Store
(:mod:`alpha_ioi.config.secrets`) or the ``provider.api_key`` convenience
field, which is moved out of the file on save.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w

from alpha_ioi.config.secrets import SecretStore
from alpha_ioi.constants import CONFIG_DIR, CONFIG_FILE, EXAMPLE_CONFIG_FILENAME

__all__ = ["AppConfig", "ConfigManager", "ProviderConfig", "load_example_config"]

#: Provider kinds the registry knows how to build.
KNOWN_PROVIDER_KINDS = ("mock", "openai", "anthropic", "ollama")

#: Kind that needs no network and no key - selected on first launch.
DEFAULT_PROVIDER_KIND = "mock"


@dataclass(slots=True)
class ProviderConfig:
    """One configured LLM provider."""

    name: str
    kind: str
    base_url: str = ""
    model: str = ""
    system_prompt: str = ""
    api_key: str = ""
    title: str = ""

    def to_toml(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": self.kind}
        if self.base_url:
            payload["base_url"] = self.base_url
        if self.model:
            payload["model"] = self.model
        if self.system_prompt:
            payload["system_prompt"] = self.system_prompt
        if self.title:
            payload["title"] = self.title
        return payload


@dataclass(slots=True)
class AppConfig:
    """Whole application configuration."""

    active_provider: str = DEFAULT_PROVIDER_KIND
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    send_on_enter: bool = True
    window_width: int = 1100
    window_height: int = 720

    def provider(self, name: str | None = None) -> ProviderConfig:
        """Return the active (or named) provider config, always something usable."""
        if name and name in self.providers:
            return self.providers[name]
        if self.active_provider in self.providers:
            return self.providers[self.active_provider]
        if self.providers:
            return next(iter(self.providers.values()))
        return _demo_provider()

    def provider_names(self) -> list[str]:
        return list(self.providers)


def _demo_provider() -> ProviderConfig:
    """Zero-config provider used on first launch and in demo mode."""
    return ProviderConfig(
        name="mock",
        kind=DEFAULT_PROVIDER_KIND,
        title="Demo (offline)",
        system_prompt="You are Alpha IOI, a helpful assistant.",
    )


def _default_config() -> AppConfig:
    demo = _demo_provider()
    return AppConfig(active_provider=demo.name, providers={demo.name: demo})


class ConfigManager:
    """Load, hold and persist :class:`AppConfig`."""

    def __init__(
        self,
        path: Path | None = None,
        secrets: SecretStore | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else CONFIG_FILE
        self.secrets = secrets if secrets is not None else SecretStore()
        self.config = _default_config()

    # -- IO --------------------------------------------------------------------

    def load(self) -> AppConfig:
        if not self.path.exists():
            self.config = _default_config()
            return self.config

        with self.path.open("rb") as fh:
            raw = tomllib.load(fh)

        providers: dict[str, ProviderConfig] = {}
        for name, body in (raw.get("providers") or {}).items():
            kind = str(body.get("kind", "")).strip().lower()
            if kind not in KNOWN_PROVIDER_KINDS:
                continue
            providers[name] = ProviderConfig(
                name=name,
                kind=kind,
                base_url=str(body.get("base_url", "")).strip(),
                model=str(body.get("model", "")).strip(),
                system_prompt=str(body.get("system_prompt", "")).strip(),
                title=str(body.get("title", "")).strip(),
                api_key=str(body.get("api_key", "")).strip(),
            )

        self.config = AppConfig(
            active_provider=str(raw.get("active_provider") or DEFAULT_PROVIDER_KIND),
            providers=providers,
            send_on_enter=bool(raw.get("send_on_enter", True)),
            window_width=int(raw.get("window_width", 1100)),
            window_height=int(raw.get("window_height", 720)),
        )

        # Pull keys out of the file (if the user pasted one there) into the
        # Secret Store and drop them from disk.
        self._migrate_api_keys()
        return self.config

    def _migrate_api_keys(self) -> None:
        moved = False
        for provider in self.config.providers.values():
            if provider.api_key:
                self.secrets.set(provider.name, provider.api_key)
                provider.api_key = ""
                moved = True
        if moved:
            self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "active_provider": self.config.active_provider,
            "send_on_enter": self.config.send_on_enter,
            "window_width": self.config.window_width,
            "window_height": self.config.window_height,
            "providers": {
                name: provider.to_toml() for name, provider in self.config.providers.items()
            },
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(tomli_w.dumps(payload), encoding="utf-8")
        tmp.replace(self.path)

    # -- helpers ---------------------------------------------------------------

    def provider(self, name: str | None = None) -> ProviderConfig:
        """The active (or named) provider - delegates to :class:`AppConfig`."""
        return self.config.provider(name)

    def ensure_provider(
        self, name: str, kind: str, base_url: str = "", model: str = "", api_key: str = ""
    ) -> ProviderConfig:
        """Create or update a provider, storing the key safely when given."""
        provider = self.config.providers.get(name)
        if provider is None:
            provider = ProviderConfig(name=name, kind=kind)
            self.config.providers[name] = provider
        provider.kind = kind
        if base_url:
            provider.base_url = base_url
        if model:
            provider.model = model
        if api_key:
            self.secrets.set(name, api_key)
            provider.api_key = ""
        self.save()
        return provider

    def set_active(self, name: str) -> None:
        if name not in self.config.providers:
            raise KeyError(f"unknown provider {name!r}")
        self.config.active_provider = name
        self.save()


def load_example_config() -> str:
    """Return the bundled example TOML so the UI can show users what to write."""
    candidates = [
        Path(__file__).resolve().parents[3] / "config" / EXAMPLE_CONFIG_FILENAME,
        Path(__file__).resolve().parents[4] / "config" / EXAMPLE_CONFIG_FILENAME,
        Path.cwd() / "config" / EXAMPLE_CONFIG_FILENAME,
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return f"# example config not found next to the package; see {CONFIG_DIR}\n"


def default_config_dir() -> Path:
    return CONFIG_DIR
