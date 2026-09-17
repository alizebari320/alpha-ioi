"""Chat transcript view: a scrolling column of message bubbles."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gi.repository import Gtk

from alpha_ioi.core.models import Role

__all__ = ["ChatView"]

_MESSAGE_LIMIT = 500


class ChatView:
    """Message list, backed by a simple ``Gtk.Box`` inside a scrolled window.

    A flat box (rather than a ``Gtk.ListView`` + factory) keeps the MVP small;
    it is plenty for hundreds of messages, and swapping in a ListView later
    only touches this file.
    """

    def __init__(self) -> None:
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        self._scrolled = Gtk.ScrolledWindow(
            hexpand=True, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER
        )
        self._scrolled.set_child(self._empty_placeholder())

        self._list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._list.set_margin_start(12)
        self._list.set_margin_end(12)
        self._list.set_margin_top(12)
        self._list.set_margin_bottom(12)

        self._count = 0
        self._streaming_label: Gtk.Label | None = None

    # -- widgets ---------------------------------------------------------------

    @property
    def widget(self) -> Gtk.ScrolledWindow:
        return self._scrolled

    def _empty_placeholder(self):
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
        )
        box.add_css_class("empty-state")
        title = Gtk.Label(label="Start a conversation")
        title.add_css_class("title")
        title.add_css_class("dim-label")
        hint = Gtk.Label(
            label="Type below and press Enter.\nNo provider configured? Demo mode works offline.",
            use_markup=False,
            wrap=True,
            justify=Gtk.Justification.CENTER,
        )
        hint.add_css_class("dim-label")
        box.append(title)
        box.append(hint)
        self._placeholder = box
        return box

    def _show_placeholder(self, show: bool) -> None:
        self._scrolled.set_child(self._placeholder if show else self._list)

    # -- content ---------------------------------------------------------------

    def clear(self) -> None:
        import gi

        gi.require_version("Gtk", "4.0")

        child = self._list.get_first_child()
        while child is not None:
            self._list.remove(child)
            child = self._list.get_first_child()
        self._count = 0
        self._streaming_label = None
        self._show_placeholder(True)

    def add_message(self, role: Role, content: str) -> Gtk.Label:
        """Append a finished message and return its label (for streaming edits)."""
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        self._show_placeholder(False)

        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row.add_css_class("message")
        row.add_css_class(f"message-{role.value}")

        label = Gtk.Label(
            label=content,
            wrap=True,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            xalign=0.0,
            selectable=True,
            hexpand=True,
        )
        row.append(label)

        if role is Role.USER:
            row.set_halign(Gtk.Align.END)
            row.add_css_class("message-user")
        else:
            row.set_halign(Gtk.Align.START)
            row.add_css_class("message-assistant")

        self._list.append(row)
        self._count += 1
        self._trim()
        self._scroll_to_bottom()
        return label

    def start_streaming(self) -> Gtk.Label:
        self._streaming_label = self.add_message(Role.ASSISTANT, "")
        return self._streaming_label

    def append_to_streaming(self, text: str) -> None:
        label = self._streaming_label
        if label is None:
            label = self.start_streaming()
        label.set_text(label.get_text() + text)
        self._scroll_to_bottom()

    def finish_streaming(self) -> None:
        if self._streaming_label is not None:
            text = self._streaming_label.get_text()
            if not text.strip():
                self._streaming_label.set_text("(empty reply)")
        self._streaming_label = None

    def add_error(self, message: str) -> None:
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        self._show_placeholder(False)
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row.add_css_class("message")
        row.add_css_class("message-error")
        row.set_halign(Gtk.Align.START)
        label = Gtk.Label(label=f"⚠ {message}", wrap=True, xalign=0.0, selectable=True)
        row.append(label)
        self._list.append(row)
        self._scroll_to_bottom()

    # -- helpers ---------------------------------------------------------------

    def _trim(self) -> None:
        """Cap the number of rendered bubbles so long chats stay smooth."""
        while self._count > _MESSAGE_LIMIT:
            child = self._list.get_first_child()
            if child is None:
                break
            self._list.remove(child)
            self._count -= 1

    def _scroll_to_bottom(self) -> None:
        from gi.repository import GLib

        def _scroll():
            vadjust = self._scrolled.get_vadjustment()
            vadjust.set_value(vadjust.get_upper() - vadjust.get_page_size())
            return GLib.SOURCE_REMOVE

        GLib.idle_add(_scroll)
