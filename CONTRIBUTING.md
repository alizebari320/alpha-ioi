# Contributing to Alpha IOI

Thanks for helping! This project is a native GTK4 / libadwaita chat client for
many LLM providers.

## Ground rules

- Use the official names: **Alpha IOI** (user-visible), `alpha_ioi` (Python
  package), `alpha-ioi` (executable, repository, distribution).
- Never commit a real API key, token or `.env`. Keys belong in the keyring.
- Keep the layering: `core/` and `providers/` must not import GTK, so that they
  stay unit-testable on a headless machine. Only `ui/` and `app.py` touch
  GObjectIntrospection.

## Development setup

PyGObject is a **system** dependency; install it with your package manager.

Fedora:

```bash
sudo dnf install python3-gobject gtk4 libadwaita
uv venv --system-site-packages
uv pip install -e ".[dev]"
```

Debian/Ubuntu:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libgtk-4-1 libadwaita-1-0
uv venv --system-site-packages
uv pip install -e ".[dev]"
```

The `--system-site-packages` flag is required: it is what lets `import gi`
resolve to the distribution's PyGObject inside the virtualenv.

## Checks

```bash
uv run ruff check .            # lint
uv run ruff format --check .   # formatting
xvfb-run -a uv run pytest      # tests (xvfb is only for the GTK smoke tests)
```

On a desktop session you can drop `xvfb-run`; the GTK tests skip themselves
automatically when no display is available.

Please run `scripts/run.sh` and actually use the app before opening a pull
request that changes the UI — code review does not catch a broken layout.

## Adding a provider

1. Add a class in `src/alpha_ioi/providers/` deriving from `ChatProvider`
   (see `openai_compat.py` for an SSE example and `ollama.py` for NDJSON).
   `stream()` must yield `ChatDelta` chunks and always end with a finished one.
   Prefer turning HTTP failures into `ChatDelta.done(error)`, not exceptions.
2. Register it in `src/alpha_ioi/providers/registry.py` (`_KIND_TO_CLASS`).
3. Add the kind to `KNOWN_PROVIDER_KINDS` in `src/alpha_ioi/config/manager.py`
   and document it in `config/alpha-ioi.example.toml` and the README table.
4. Add tests using `httpx.MockTransport` — no real network in the suite.

## Changing the icon

`assets/icons/alpha-ioi.svg` is the single source of truth. Replace it, run
`scripts/build-icons.sh`, and re-run `scripts/install-fedora.sh`. See the
“Replacing the logo” section of the README.

## Commit style

Conventional Commits, e.g.:

```
feat: create initial Alpha IOI MVP
fix: keep streamed text when a provider ends without a finish frame
```

## License

By contributing you agree your work is licensed under Apache-2.0.
