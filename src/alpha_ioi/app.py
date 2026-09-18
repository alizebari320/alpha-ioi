"""Application entry point.

Both ``python -m alpha_ioi`` and the ``alpha-ioi`` console script land here, so
the two commands behave identically by construction.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import TYPE_CHECKING

from alpha_ioi.constants import (
    APP_AUTHOR,
    APP_DESCRIPTION,
    APP_ID,
    APP_NAME,
    CLI_NAME,
    CONFIG_FILE,
    DEVELOPER_EMAIL,
    HELP_URL,
    ISSUES_URL,
    VERSION,
    WEBSITE_URL,
)

if TYPE_CHECKING:
    from alpha_ioi.config import ConfigManager
    from alpha_ioi.core.history import HistoryStore
    from alpha_ioi.ui.window import MainWindow

__all__ = ["AlphaIOIApplication", "main"]


class AlphaIOIApplication:
    """Thin wrapper around ``Adw.Application``.

    Wrapped (rather than subclassed) so the non-GUI parts of the codebase can
    import this module without paying for GObjectIntrospection.
    """

    def __init__(
        self, config: ConfigManager, history: HistoryStore, force_demo: bool = False
    ) -> None:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gio

        self._config = config
        self._history = history
        self._force_demo = force_demo

        self._app = Adw.Application(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

        # The window is built lazily in _ensure_window(): GTK refuses to
        # register an application window before GApplication::startup, and an
        # unregistered window does not keep the application alive.
        self._window: MainWindow | None = None

        actions = {
            "quit": (lambda _a, _p: self.quit(), ("<Control>q",)),
            "new-chat": (lambda _a, _p: self._ensure_window().new_chat(), ("<Control>n",)),
            "edit-config": (lambda _a, _p: self.edit_config(), None),
            "about": (lambda _a, _p: self.show_about(), None),
        }
        for name, (handler, accels) in actions.items():
            action = Gio.SimpleAction(name=name)
            action.connect("activate", handler)
            self._app.add_action(action)
            if accels:
                self._app.set_accels_for_action(f"app.{name}", list(accels))

        self._app.connect("activate", self._on_activate)

    # -- application -----------------------------------------------------------

    def _ensure_window(self) -> MainWindow:
        """Build the main window on first use, after ``GApplication::startup``.

        A ``Gtk.ApplicationWindow`` created too early is never registered with
        the application, and an application with no registered windows exits as
        soon as the main loop starts - which looks like "the app won't launch".
        """
        if self._window is None:
            from alpha_ioi.ui.window import MainWindow

            self._window = MainWindow(self._app, self._config, self._history)
        return self._window

    def _on_activate(self, _app) -> None:
        self.load_stylesheet()
        if self._force_demo:
            self._config.config.active_provider = "mock"
        window = self._ensure_window()
        window.refresh_all()
        window.present()

    def load_stylesheet(self) -> None:
        from importlib import resources

        from gi.repository import Gdk, Gtk

        provider = Gtk.CssProvider()
        try:
            css = resources.files("alpha_ioi.ui").joinpath("styles.css").read_bytes()
            provider.load_from_data(css)
        except (OSError, FileNotFoundError):  # pragma: no cover
            return
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # -- actions ---------------------------------------------------------------

    def quit(self) -> None:
        self._app.quit()

    def edit_config(self) -> None:
        """Open the config file in the user's editor, creating it if missing."""
        if not CONFIG_FILE.exists():
            self._config.save()
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "xdg-open"
        try:
            subprocess.Popen([editor, str(CONFIG_FILE)])  # noqa: S603
        except FileNotFoundError:
            self._ensure_window().show_error(f"editor {editor!r} not found; edit {CONFIG_FILE}")

    def show_about(self) -> None:
        from gi.repository import Adw

        from alpha_ioi.ui.icons import app_icon_texture

        about = Adw.AboutWindow(
            transient_for=self._ensure_window().widget,
            application_name=APP_NAME,
            application_icon="alpha-ioi",
            version=VERSION,
            developer_name=APP_AUTHOR,
            developers=[f"{APP_AUTHOR} <{DEVELOPER_EMAIL}>"],
            copyright=f"Copyright © 2026 {APP_AUTHOR}",
            website=WEBSITE_URL,
            issue_url=ISSUES_URL,
            support_url=HELP_URL,
            comments=APP_DESCRIPTION,
        )
        about.set_license_type(_license_type())
        logo = app_icon_texture(256)
        if logo is not None:
            about.set_logo(logo)
        about.present()

    # -- run -------------------------------------------------------------------

    def run(self, argv: list[str] | None = None) -> int:
        return self._app.run(argv if argv is not None else [])


def _license_type():
    from gi.repository import Gtk

    return Gtk.License.APACHE_2_0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=CLI_NAME,
        description=f"{APP_NAME} - {APP_DESCRIPTION}",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="force the offline demo provider (no network, no API key)",
    )
    parser.add_argument("--config", metavar="PATH", help="path to config.toml")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    from alpha_ioi.config import ConfigManager, SecretStore
    from alpha_ioi.core.history import HistoryStore

    config = ConfigManager(path=args.config, secrets=SecretStore())
    config.load()
    history = HistoryStore()

    application = AlphaIOIApplication(config, history, force_demo=args.demo)
    # ``Adw.Application.run`` wants a full argv whose first element is the
    # program name; passing our own flags would make GTK try to parse them.
    return application.run([sys.argv[0]])


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
