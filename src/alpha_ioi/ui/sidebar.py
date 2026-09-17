"""Sidebar: conversation list, provider and model pickers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from alpha_ioi.constants import APP_NAME

__all__ = ["Sidebar"]


class Sidebar:
    """Left pane of the main window.

    Owns widgets and signals only: every decision is handed back to
    :class:`~alpha_ioi.ui.window.MainWindow` through callbacks, so the window
    stays testable without this pane's GTK internals.
    """

    def __init__(self) -> None:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gtk

        self._on_new_chat: Callable[[], None] | None = None
        self._on_select_conversation: Callable[[int], None] | None = None
        self._on_provider_changed: Callable[[str], None] | None = None
        self._on_model_changed: Callable[[str], None] | None = None
        self._on_refresh_models: Callable[[], list[str]] | None = None

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Brand row (the temporary A7 icon + app name)
        brand = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
            margin_start=12,
            margin_end=12,
            margin_top=12,
            margin_bottom=6,
        )
        icon = Gtk.Image(icon_name="alpha-ioi", pixel_size=32)
        icon.add_css_class("app-icon")
        name = Gtk.Label(label=f"<b>{APP_NAME}</b>", use_markup=True, xalign=0.0, hexpand=True)
        brand.append(icon)
        brand.append(name)
        self._box.append(brand)

        new_chat = Gtk.Button(label="New chat", icon_name="list-add-symbolic", hexpand=True)
        new_chat.add_css_class("suggested-action")
        new_chat.connect("clicked", self._emit_new_chat)
        self._box.append(new_chat)

        # Provider / model pickers
        group = Adw.PreferencesGroup()
        self._provider_row = Adw.ComboRow(title="Provider", subtitle="LLM backend")
        self._model_row = Adw.ComboRow(title="Model", subtitle="Model id")
        group.add(self._provider_row)
        group.add(self._model_row)
        self._provider_row.connect("notify::selected", self._emit_provider_changed)
        self._model_row.connect("notify::selected", self._emit_model_changed)
        self._box.append(group)

        refresh = Gtk.Button(label="Refresh models", icon_name="view-refresh-symbolic")
        refresh.add_css_class("flat")
        refresh.connect("clicked", self._refresh_models)
        self._box.append(refresh)

        # Conversation list
        self._store = Gtk.StringList()
        self._selection = Gtk.SingleSelection(model=self._store, autoselect=False)
        self._invalid_position = Gtk.INVALID_LIST_POSITION
        self._selection.connect("selection-changed", self._emit_select_conversation)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_row)
        factory.connect("bind", self._bind_row)
        self._list = Gtk.ListView(
            model=self._selection, factory=factory, show_separators=True, hexpand=True, vexpand=True
        )
        self._list.add_css_class("navigation-sidebar")

        scrolled = Gtk.ScrolledWindow(child=self._list, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scrolled.add_css_class("sidebar-list")
        self._box.append(scrolled)

    # -- widget ----------------------------------------------------------------

    @property
    def widget(self):
        return self._box

    # -- callbacks -------------------------------------------------------------

    def set_callbacks(
        self,
        *,
        new_chat: Callable[[], None] | None = None,
        select_conversation: Callable[[int], None] | None = None,
        provider_changed: Callable[[str], None] | None = None,
        model_changed: Callable[[str], None] | None = None,
        refresh_models: Callable[[], list[str]] | None = None,
    ) -> None:
        self._on_new_chat = new_chat or self._on_new_chat
        self._on_select_conversation = select_conversation or self._on_select_conversation
        self._on_provider_changed = provider_changed or self._on_provider_changed
        self._on_model_changed = model_changed or self._on_model_changed
        self._on_refresh_models = refresh_models or self._on_refresh_models

    def _emit_new_chat(self, _button) -> None:
        if self._on_new_chat:
            self._on_new_chat()

    def _emit_select_conversation(self, _selection, position: int) -> None:
        if self._on_select_conversation and position != self._invalid_position:
            self._on_select_conversation(position)

    def _refresh_models(self, _button) -> None:
        if self._on_refresh_models:
            models = self._on_refresh_models()
            self.set_models(models)

    def _emit_provider_changed(self, row, _pspec) -> None:
        if self._on_provider_changed:
            item = row.get_selected_item()
            if item is not None:
                self._on_provider_changed(item.get_string())

    def _emit_model_changed(self, row, _pspec) -> None:
        if self._on_model_changed:
            item = row.get_selected_item()
            if item is not None:
                self._on_model_changed(item.get_string())

    # -- content ---------------------------------------------------------------

    def set_providers(self, names: list[str], active: str = "") -> None:
        from gi.repository import Gtk

        self._provider_row.set_model(Gtk.StringList.new(names))
        if active in names:
            self._provider_row.set_selected(names.index(active))

    def set_models(self, models: list[str]) -> None:
        from gi.repository import Gtk

        current = self.selected_model()
        self._model_row.set_model(Gtk.StringList.new(models))
        if current in models:
            self._model_row.set_selected(models.index(current))
        elif models:
            self._model_row.set_selected(0)

    def selected_model(self) -> str:
        item = self._model_row.get_selected_item()
        return item.get_string() if item is not None else ""

    def set_conversations(self, titles: list[str]) -> None:
        self._store.splice(0, self._store.get_n_items(), list(titles))

    def select_conversation(self, index: int) -> None:
        if 0 <= index < self._store.get_n_items():
            self._selection.set_selected(index)

    # -- list rows -------------------------------------------------------------

    def _setup_row(self, _factory, list_item) -> None:
        from gi.repository import Gtk

        row = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            margin_start=10,
            margin_end=10,
            margin_top=8,
            margin_bottom=8,
        )
        title = Gtk.Label(xalign=0.0, ellipsize=Gtk.EllipsizeMode.END)
        title.add_css_class("chat-title")
        row.append(title)
        list_item.set_child(row)

    def _bind_row(self, _factory, list_item) -> None:
        child = list_item.get_child()
        if child is None:
            return
        label = child.get_first_child()
        string_item = list_item.get_item()
        if label is not None and string_item is not None:
            label.set_text(string_item.get_string())
