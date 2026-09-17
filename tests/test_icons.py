"""Tests for icon resolution (no display required)."""

from __future__ import annotations

from alpha_ioi.constants import ICON_NAME
from alpha_ioi.ui.icons import (
    ICON_FILENAME,
    icon_directories,
    resolve_icon_path,
)


def test_icon_filename_matches_app_icon_name():
    assert f"{ICON_NAME}.svg" == ICON_FILENAME
    assert ICON_FILENAME == "alpha-ioi.svg"


def test_repo_icon_is_found():
    icon = resolve_icon_path()
    assert icon is not None, "assets/icons/alpha-ioi.svg should exist in a checkout"
    assert icon.name == "alpha-ioi.svg"
    assert icon.is_file()


def test_repo_icon_is_a_square_a7_mark():
    icon = resolve_icon_path()
    assert icon is not None
    text = icon.read_text(encoding="utf-8")
    assert "A7" in text
    assert 'viewBox="0 0 512 512"' in text


def test_icon_directories_are_all_directories():
    for directory in icon_directories():
        assert directory.is_dir()


def test_register_icon_theme_is_safe_without_display():
    # Must not raise even when there is no display (headless CI, containers).
    from alpha_ioi.ui.icons import register_icon_theme

    assert isinstance(register_icon_theme(), list)
