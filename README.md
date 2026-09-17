# Alpha IOI

> A native Linux desktop chat client that talks to **many LLM providers** from
> one window — GTK4 + libadwaita, no Electron, no web view.

Alpha IOI keeps your provider API keys in your **system keyring** (never in a
config file, never in git), stores each conversation as a plain JSONL file you
own, and ships with an **offline demo provider** so the app is useful the moment
it starts, before you configure anything.

<p align="center">
  <img src="assets/icons/alpha-ioi.svg" alt="Alpha IOI temporary A7 icon" width="128">
</p>

> **Naming:** the application is **Alpha IOI**. The Python package is
> `alpha_ioi`, the executable and repository are `alpha-ioi`.
> The logo above is a **temporary placeholder** (the future official logo is
> based on the **A7** mark) — see [Replacing the logo](#replacing-the-logo).

---

## Features

- **One window, many backends.** OpenAI-compatible APIs, Anthropic's Messages
  API and a local Ollama server, selectable from the sidebar.
- **Streaming replies** over SSE/NDJSON, rendered live, with a Stop button.
- **Keys in the keyring.** Paste an `api_key` into the config once and Alpha IOI
  moves it to the Secret Service (or to a mode-`0600` `keys.json` when no
  keyring backend exists) and removes it from disk.
- **Offline demo mode** that needs no network and no key.
- **Local history.** One JSONL file per conversation under
  `~/.local/state/alpha-ioi/history/`.
- **No telemetry.** The only network calls are to the provider you configure.

## Requirements

- Linux with GTK 4 and libadwaita 1.4+
- Python 3.11+
- PyGObject (`python3-gobject`) — a **system** package, not a pip dependency

On Fedora:

```bash
sudo dnf install python3 python3-gobject gtk4 libadwaita
```

## Install

### Fedora (recommended)

```bash
git clone https://github.com/aliarifmuhammed/alpha-ioi
cd alpha-ioi
scripts/install-fedora.sh
```

That installs the GTK stack, creates `.venv` with `--system-site-packages` (so
`import gi` works), installs Alpha IOI, and registers the icon, desktop entry
and AppStream metadata in your XDG data directories.

### Any distro, from a checkout

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e .
```

## Run

Either of these starts the application:

```bash
python -m alpha_ioi     # from an installed package or a checkout
alpha-ioi               # the console script
```

From a git checkout without installing:

```bash
scripts/run.sh          # adds src/ to PYTHONPATH
scripts/run.sh --demo   # force the offline demo provider
scripts/run.sh --version
```

Useful flags:

| Flag | Meaning |
|------|---------|
| `--demo` | force the offline demo provider (no network, no key) |
| `--config PATH` | use a specific `config.toml` |
| `--version` | print the version and exit |

## Configuration

Configuration lives at `~/.config/alpha-ioi/config.toml`. The quickest way to
edit it is **menu → “Edit config file”**. A fully commented example ships in
[`config/alpha-ioi.example.toml`](config/alpha-ioi.example.toml):

```toml
active_provider = "ollama"

[providers.ollama]
kind = "ollama"
base_url = "http://localhost:11434"
model = "qwen3:4b"

[providers.openai]
kind = "openai"
base_url = "https://api.openai.com/v1"
model = "gpt-5"
# api_key = "sk-..."   # moved to your keyring on first load
```

### Provider kinds

| `kind` | Protocol | Notes |
|--------|----------|-------|
| `openai` | `/v1/chat/completions` (SSE) | OpenAI, OpenRouter, AgentRouter, TokenHarbor, LocalAI, vLLM, Ollama `/v1` |
| `anthropic` | `/v1/messages` (SSE) | Anthropic-native |
| `ollama` | `/api/chat` (NDJSON) | local, no API key |
| `mock` | — | offline demo, no network |

API keys are read from the keyring at start-up. To set one from the command
line you can paste it into the config as `api_key = "..."` and restart, or use
your desktop's keyring UI with service `alpha-ioi`.

## Replacing the logo

The current icon is a deliberate, temporary **A7** placeholder.

1. Replace `assets/icons/alpha-ioi.svg` with the final logo, keeping the
   **same filename** and a **square** viewBox.
2. Regenerate the rasterized sizes (the SVG stays the source of truth):

   ```bash
   scripts/build-icons.sh
   ```

3. Re-run `scripts/install-fedora.sh` to refresh the copies in
   `~/.local/share/icons/hicolor/` (an installed copy also picks the icon up
   from the wheel, see `src/alpha_ioi/ui/icons.py`).

Nothing else needs changing: the icon name (`alpha-ioi`), the window icon, the
sidebar mark and the About dialog logo all resolve through that one file. The
`assets/` directory is shipped inside the wheel, so an installed copy finds the
icon without the git checkout.

## Project layout

```
alpha-ioi/
├── assets/
│   ├── applications/          # .desktop entry
│   ├── icons/alpha-ioi.svg    # temporary A7 icon (source of truth)
│   └── metainfo/              # AppStream metadata
├── config/alpha-ioi.example.toml
├── scripts/                   # install / run / icon generation
├── src/alpha_ioi/
│   ├── __main__.py            # `python -m alpha_ioi`
│   ├── app.py                 # Adw.Application, actions, About
│   ├── constants.py           # every name and path lives here
│   ├── config/                # TOML config + Secret Store
│   ├── core/                  # models, history, streaming engine
│   ├── providers/             # openai / anthropic / ollama / mock
│   └── ui/                    # GTK4 + libadwaita widgets
└── tests/
```

The layering is strict: `core` and `providers` import no GTK, so they are fully
unit-testable headlessly; only `ui/` and `app.py` touch GObjectIntrospection.

## Development

```bash
uv venv --system-site-packages
uv pip install -e ".[dev]"
uv run ruff check .
uv run ruff format --check .
xvfb-run -a uv run pytest      # xvfb only needed for the GTK smoke tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
