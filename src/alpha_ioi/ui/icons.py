"""Application icon loading.

GTK 4.22 dropped ``Gtk.Window.set_icon``/``Gtk.Application.set_default_icon_name``;
the supported route is to register a search path with the icon theme and then
call ``Gtk.Window.set_icon_name("alpha-ioi")``. That is what this module does.

The canonical icon is ``assets/icons/alpha-ioi.svg`` in the source tree; the
wheel also ships a copy inside the package (see ``pyproject.toml``) so an
installed copy can find it without the repo. See README "Replacing the logo".
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from alpha_ioi.constants import ICON_NAME

__all__ = [
    "ICON_FILENAME",
    "app_icon_paintable",
    "app_icon_texture",
    "icon_directories",
    "register_icon_theme",
    "resolve_icon_path",
]

ICON_FILENAME = f"{ICON_NAME}.svg"


def icon_directories() -> list[Path]:
    """Every directory that may contain ``alpha-ioi.svg``, most specific first."""
    here = Path(__file__).resolve()
    candidates = [
        # 1. source checkout: src/alpha_ioi/ui/icons.py -> <repo>/assets/icons
        here.parents[3] / "assets" / "icons",
        # 2. installed package data (mapped by the wheel build)
        Path(str(resources.files("alpha_ioi"))) / "data" / "icons",
        # 3. system/user hicolor theme, used when scripts/install-fedora.sh ran
        Path.home() / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps",
        Path("/usr/share/icons/hicolor/scalable/apps"),
        Path("/usr/local/share/icons/hicolor/scalable/apps"),
    ]
    return [path for path in candidates if path.is_dir()]


def resolve_icon_path() -> Path | None:
    """Return the first on-disk copy of the icon, or ``None`` if none exists."""
    for directory in icon_directories():
        icon = directory / ICON_FILENAME
        if icon.is_file():
            return icon
    return None


def register_icon_theme(display=None) -> list[Path]:
    """Make ``alpha-ioi`` resolvable by the icon theme. Returns dirs registered."""
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk, Gtk
    except (ImportError, ValueError):  # pragma: no cover - non-GTK environment
        return []

    if display is None:
        display = Gdk.Display.get_default()
    if display is None:  # pragma: no cover - headless
        return []

    theme = Gtk.IconTheme.get_for_display(display)
    registered: list[Path] = []
    for directory in icon_directories():
        theme.add_search_path(str(directory))
        registered.append(directory)
    return registered


def app_icon_paintable(display=None, size: int = 32):
    """Icon as a :class:`Gtk.IconPaintable` (header bars, buttons)."""
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, Gtk

    if display is None:
        display = Gdk.Display.get_default()
    if display is None:  # pragma: no cover - headless
        return None
    theme = Gtk.IconTheme.get_for_display(display)
    return theme.lookup_icon(
        ICON_NAME,
        None,
        size,
        1,
        Gtk.TextDirection.NONE,
        Gtk.IconLookupFlags.PRELOAD,
    )


def app_icon_texture(size: int = 256):
    """Icon as a :class:`Gdk.Texture` (About window logo). Falls back to None."""
    import gi

    gi.require_version("Gdk", "4.0")
    gi.require_version("GLib", "2.0")
    from gi.repository import Gdk, GLib

    path = resolve_icon_path()
    if path is None:
        return None
    try:
        bytes_ = GLib.Bytes(path.read_bytes())
        texture = Gdk.Texture.new_from_bytes(bytes_)
    except Exception:
        return None
    # The texture is the vector at its natural size; callers scale via paintable.
    _ = size
    return texture
