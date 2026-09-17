"""Tests for the command-line surface."""

from __future__ import annotations

import pytest

from alpha_ioi.app import _build_parser
from alpha_ioi.constants import APP_NAME


def test_version_flag_prints_app_name(capsys):
    with pytest.raises(SystemExit) as exc:
        _build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert APP_NAME in out


def test_demo_flag():
    args = _build_parser().parse_args(["--demo"])
    assert args.demo is True


def test_config_flag():
    args = _build_parser().parse_args(["--config", "custom.toml"])
    assert args.config == "custom.toml"


def test_defaults():
    args = _build_parser().parse_args([])
    assert args.demo is False
    assert args.config is None


def test_program_name_is_the_console_script():
    assert _build_parser().prog == "alpha-ioi"
