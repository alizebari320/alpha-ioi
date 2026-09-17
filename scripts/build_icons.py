#!/usr/bin/env python3
"""Rasterize ``assets/icons/alpha-ioi.svg`` into the PNG sizes the icon theme
wants.

Uses GTK's own SVG loader (gdk-pixbuf's librsvg loader), so no separate
``rsvg-convert``/``inkscape`` install is required. This is the only reason the
project needs PyGObject at *build* time, and it degrades gracefully: if the
loader is missing the script exits non-zero and callers keep the SVG.

Usage::

    scripts/build_icons.py                     # into assets/icons/
    scripts/build_icons.py --outdir <hicolor>  # <hicolor>/<N>x<N>/apps/alpha-ioi.png
    scripts/build_icons.py --sizes 16,32,256
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SIZES = (16, 24, 32, 48, 64, 128, 256, 512)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SVG = REPO_ROOT / "assets" / "icons" / "alpha-ioi.svg"
DEFAULT_OUT = REPO_ROOT / "assets" / "icons"


def _require_gi():
    try:
        import gi

        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf
    except (ImportError, ValueError) as exc:  # pragma: no cover - host dependent
        print(f"error: PyGObject/GdkPixbuf unavailable: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    return GdkPixbuf


def rasterize(
    svg: Path, sizes: tuple[int, ...], outdir: Path, hicolor: bool, quiet: bool
) -> list[Path]:
    GdkPixbuf = _require_gi()
    written: list[Path] = []
    for size in sizes:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(str(svg), size, size)
        except Exception as exc:
            print(f"error: could not rasterize {svg} at {size}px: {exc}", file=sys.stderr)
            raise SystemExit(3) from exc

        target_dir = outdir / f"{size}x{size}" / "apps" if hicolor else outdir
        target_dir.mkdir(parents=True, exist_ok=True)

        name = "alpha-ioi.png" if hicolor else f"alpha-ioi-{size}.png"
        target = target_dir / name
        pixbuf.savev(str(target), "png", [], [])
        written.append(target)
        if not quiet:
            print(f"wrote {target}")
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--svg", type=Path, default=DEFAULT_SVG)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--sizes", default=",".join(str(s) for s in SIZES))
    parser.add_argument(
        "--hicolor", action="store_true", help="write <outdir>/<N>x<N>/apps/alpha-ioi.png layout"
    )
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.svg.is_file():
        print(f"error: no such SVG: {args.svg}", file=sys.stderr)
        return 1
    sizes = tuple(int(s) for s in args.sizes.split(",") if s.strip())
    rasterize(args.svg, sizes, args.outdir, args.hicolor, args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
