"""GTK smoke tests.

These need a display; they are skipped automatically when none is available
(run them under ``xvfb-run`` on headless CI - see .github/workflows/ci.yml).
"""

from __future__ import annotations

import pytest

from alpha_ioi.constants import APP_NAME, ICON_NAME


def _gtk_or_skip():
    gi = pytest.importorskip("gi")
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gdk, Gtk

    if Gdk.Display.get_default() is None:
        pytest.skip("no display available for GTK")
    Adw.init()
    return Gtk, Adw


def test_main_window_title_and_icon(config_manager, history_store):
    _Gtk, _Adw = _gtk_or_skip()

    from alpha_ioi.ui.window import MainWindow

    config_manager.load()
    window = MainWindow(None, config_manager, history_store)

    assert window.widget.get_title() == APP_NAME
    assert window.widget.get_icon_name() == ICON_NAME
    window.widget.destroy()


def test_window_renders_a_conversation(config_manager, history_store):
    _Gtk, _Adw = _gtk_or_skip()

    from alpha_ioi.core.models import Role
    from alpha_ioi.ui.window import MainWindow

    config_manager.load()
    window = MainWindow(None, config_manager, history_store)

    window._conversation.add(Role.USER, "hello from the test")
    window._render_conversation()
    # Two children after render: user + (later) assistant; at least the user row.
    first = window._chat._list.get_first_child()
    assert first is not None
    window.widget.destroy()


def test_new_chat_resets_transcript(config_manager, history_store):
    _Gtk, _Adw = _gtk_or_skip()

    from alpha_ioi.core.models import Role
    from alpha_ioi.ui.window import MainWindow

    config_manager.load()
    window = MainWindow(None, config_manager, history_store)
    window._conversation.add(Role.USER, "hi")
    window._render_conversation()
    window.new_chat()
    assert window._chat._list.get_first_child() is None
    window.widget.destroy()
