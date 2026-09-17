#!/usr/bin/env bash
# Alpha IOI - regenerate the rasterized icon sizes from the canonical SVG.
#
# Run this after replacing assets/icons/alpha-ioi.svg with the final logo.
# The SVG stays the source of truth; the PNGs are a convenience for desktop
# environments and the icon theme.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec python3 "${repo_root}/scripts/build_icons.py" \
  --svg "${repo_root}/assets/icons/alpha-ioi.svg" \
  --outdir "${repo_root}/assets/icons" "$@"
