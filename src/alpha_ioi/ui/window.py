"""Main application window."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from alpha_ioi.constants import APP_NAME, ICON_NAME
from alpha_ioi.core.engine import stream_reply
from alpha_ioi.core.models import ChatDelta, Conversation, Role
from alpha_ioi.providers.base import ChatProvider, ProviderError
from alpha_ioi.providers.registry import build_provider

if TYPE_CHECKING:
    from gi.repository import Adw, Gtk

    from alpha_ioi.config import ConfigManager
    from alpha_ioi.core.history import HistoryStore

__all__ = ["MainWindow"]


class MainWindow:
    """Controller for the Alpha IOI main window.

    Owns one :class:`~alpha_ioi.core.models.Conversation` at a time, runs each
    provider stream on a worker thread, and forwards deltas to GTK on the main
    loop with ``GLib.idle_add`` so blocking HTTP never freezes the UI.
    """

    def __init__(
        self,
        app: Adw.Application,
        config: ConfigManager,
        history: HistoryStore,
    ) -> None:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gtk

        from alpha_ioi.ui.chat_view import ChatView
        from alpha_ioi.ui.icons import register_icon_theme
        from alpha_ioi.ui.sidebar import Sidebar

        self._config = config
        self._history = history
        self._provider: ChatProvider | None = None
        self._conversation = Conversation(
            provider=config.config.active_provider, model=config.provider().model
        )
        self._generating = False
        self._stop = threading.Event()

        register_icon_theme()

        self._window = Adw.ApplicationWindow(application=app)
        self._window.set_title(APP_NAME)
        self._window.set_icon_name(ICON_NAME)
        self._window.set_default_size(config.config.window_width, config.config.window_height)

        self._chat = ChatView()
        self._sidebar = Sidebar()
        self._sidebar.set_callbacks(
            new_chat=self.new_chat,
            select_conversation=self.open_conversation,
            provider_changed=self.select_provider,
            model_changed=self.select_model,
            refresh_models=self.refresh_models,
        )

        self._title = Adw.WindowTitle(title=APP_NAME, subtitle="")

        self._split = Adw.OverlaySplitView(collapsed=False, show_sidebar=True)
        self._split.set_sidebar(self._sidebar.widget)
        self._split.set_content(self._build_content(Gtk, Adw))
        self._window.set_content(self._split)

        self._window.connect("close-request", self._on_close_request)
        self._window.connect("notify::default-width", self._persist_window_size)
        self._window.connect("notify::default-height", self._persist_window_size)

        self.refresh_all()

    # -- layout ----------------------------------------------------------------

    def _build_content(self, Gtk: type, Adw: type) -> Gtk.Widget:
        from gi.repository import Gio, GLib

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        header.add_css_class("flat")
        header.set_title_widget(self._title)

        menu = Gio.Menu()
        menu.append("New chat", "app.new-chat")
        menu.append("Edit config file", "app.edit-config")
        menu.append(f"About {APP_NAME}", "app.about")
        menu.append("Quit", "app.quit")
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))

        stop_button = Gtk.Button(
            icon_name="media-playback-stop-symbolic", tooltip_text="Stop generating"
        )
        stop_button.add_css_class("error")
        stop_button.connect("clicked", self._on_stop)
        stop_button.set_visible(False)
        self._stop_button = stop_button
        header.pack_end(stop_button)

        box.append(header)
        box.append(self._chat.widget)

        entry_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_start=10,
            margin_end=10,
            margin_top=6,
            margin_bottom=10,
        )
        self._entry = Gtk.TextView(
            wrap_mode=Gtk.WrapMode.WORD_CHAR, pixels_below_lines=4, height_request=64
        )
        self._entry.add_css_class("entry")
        scrolled = Gtk.ScrolledWindow(
            child=self._entry,
            min_content_height=64,
            max_content_height=220,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        scrolled.add_css_class("entry-scroll")
        entry_box.append(scrolled)

        send = Gtk.Button(label="Send", icon_name="go-next-symbolic", tooltip_text="Send (Enter)")
        send.add_css_class("suggested-action")
        send.set_halign(Gtk.Align.END)
        send.connect("clicked", self._on_send)
        self._send_button = send
        entry_box.append(send)

        box.append(entry_box)

        controller = Gtk.EventControllerKey()
        self._entry.add_controller(controller)
        controller.connect("key-pressed", self._on_key_pressed)

        _ = GLib  # imported for the main-loop callbacks used elsewhere
        return box

    # -- public actions --------------------------------------------------------

    @property
    def widget(self) -> Adw.ApplicationWindow:
        return self._window

    def present(self) -> None:
        self._window.present()

    def refresh_all(self) -> None:
        """Rebuild sidebar state and (re)apply the active provider."""
        cfg = self._config.config
        self._sidebar.set_providers(cfg.provider_names(), cfg.active_provider)
        self._sidebar.set_conversations([c.title for c in self._history.list_conversations()])
        self._apply_provider()
        self._render_conversation()

    def show_error(self, message: str) -> None:
        """Surface a non-fatal error in the transcript."""
        self._chat.add_error(message)

    def new_chat(self) -> None:
        self._conversation = Conversation(
            provider=self._config.config.active_provider, model=self._sidebar.selected_model()
        )
        self._chat.clear()

    def open_conversation(self, index: int) -> None:
        conversations = self._history.list_conversations()
        if not 0 <= index < len(conversations):
            return
        loaded = self._history.load_conversation(conversations[index].id)
        if loaded is None:
            return
        self._conversation = loaded
        self._render_conversation()

    def select_provider(self, name: str) -> None:
        try:
            self._config.set_active(name)
        except KeyError:
            return
        self._apply_provider()

    def select_model(self, model: str) -> None:
        self._config.provider().model = model
        self._conversation.model = model
        self._config.save()
        self._update_subtitle()

    def refresh_models(self) -> list[str]:
        if self._provider is None:
            return []
        try:
            models = self._provider.list_models()
        except ProviderError as exc:
            self._chat.add_error(str(exc))
            return []
        self._sidebar.set_models(models)
        return models

    # -- internals -------------------------------------------------------------

    def _apply_provider(self) -> None:
        cfg = self._config.provider()
        self._provider = build_provider(cfg, self._config.secrets)
        # build_provider() may substitute a provider-side default when the config
        # names no model (the demo provider does), so read it back from the
        # provider instead of trusting the raw config value.
        model = self._provider.resolve_model()
        self._conversation.provider = cfg.name
        self._conversation.model = model
        self._sidebar.set_models([model] if model else [])
        self._update_subtitle()

    def _update_subtitle(self) -> None:
        self._title.set_subtitle(self._provider.describe() if self._provider else "")

    def _render_conversation(self) -> None:
        self._chat.clear()
        for message in self._conversation.messages:
            self._chat.add_message(message.role, message.content)

    # -- sending ---------------------------------------------------------------

    def _on_key_pressed(self, _controller, keyval, _keycode, state) -> bool:
        from gi.repository import Gdk

        if keyval not in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            return False
        if bool(state & Gdk.ModifierType.SHIFT_MASK) or not self._config.config.send_on_enter:
            return False
        self._on_send()
        return True

    def _on_send(self, *_args) -> None:
        if self._generating:
            return
        buffer = self._entry.get_buffer()
        text = buffer.get_text(*buffer.get_bounds(), include_hidden_chars=False).strip()
        if not text:
            return
        self._history.record(self._conversation, self._conversation.add(Role.USER, text))
        self._chat.add_message(Role.USER, text)
        buffer.set_text("")
        self._refresh_history_list()
        self._start_generation()

    def _on_stop(self, *_args) -> None:
        self._stop.set()

    def _start_generation(self) -> None:
        if self._provider is None:
            self._chat.add_error("no provider configured")
            return
        self._generating = True
        self._stop.clear()
        self._send_button.set_sensitive(False)
        self._stop_button.set_visible(True)
        self._chat.start_streaming()
        threading.Thread(target=self._generate, daemon=True).start()

    def _generate(self) -> None:
        from gi.repository import GLib

        provider = self._provider
        assert provider is not None
        model = self._sidebar.selected_model() or self._conversation.model
        chunks: list[str] = []

        def flush(delta: ChatDelta) -> bool:
            if delta.text:
                chunks.append(delta.text)
                self._chat.append_to_streaming(delta.text)
            if delta.error:
                self._chat.add_error(delta.error)
            if delta.finished:
                self._chat.finish_streaming()
                reply = "".join(chunks).strip()
                if reply:
                    self._history.record(
                        self._conversation, self._conversation.add(Role.ASSISTANT, reply)
                    )
                self._finish_generation()
            return GLib.SOURCE_REMOVE

        for delta in stream_reply(provider, self._conversation, model=model):
            stopped = self._stop.is_set()
            if stopped and not delta.finished:
                GLib.idle_add(flush, ChatDelta.done("stopped by user"))
                return
            GLib.idle_add(flush, delta)
            if stopped:
                return

    def _finish_generation(self) -> None:
        self._generating = False
        self._send_button.set_sensitive(True)
        self._stop_button.set_visible(False)
        self._refresh_history_list()

    def _refresh_history_list(self) -> None:
        self._sidebar.set_conversations([c.title for c in self._history.list_conversations()])

    # -- lifecycle -------------------------------------------------------------

    def _on_close_request(self, _window) -> bool:
        self._stop.set()
        self._persist_window_size()
        return False

    def _persist_window_size(self, *_args) -> None:
        width, height = self._window.get_default_width(), self._window.get_default_height()
        if (width, height) != (self._config.config.window_width, self._config.config.window_height):
            self._config.config.window_width = width
            self._config.config.window_height = height
            self._config.save()
