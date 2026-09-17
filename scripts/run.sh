#!/usr/bin/env bash
# Alpha IOI - development launcher.
#
# Runs the app straight from this checkout, no install required:
#
#     scripts/run.sh
#     scripts/run.sh --demo          # offline demo provider
#     scripts/run.sh --version
#
# PYTHONPATH points at src/ so `python -m alpha_ioi` finds the package.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" 2>/dev/null; then
  echo "Alpha IOI needs GTK4, libadwaita and PyGObject." >&2
  echo "On Fedora run:  sudo dnf install python3-gobject gtk4 libadwaita" >&2
  exit 1
fi

export PYTHONPATH="${repo_root}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 -m alpha_ioi "$@"
