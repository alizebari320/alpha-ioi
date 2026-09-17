#!/usr/bin/env bash
# Alpha IOI - Fedora installer.
#
# Installs the system GTK stack, creates a virtualenv that can see the system
# PyGObject bindings, installs Alpha IOI itself, and registers the icon, the
# desktop entry and the AppStream metadata with the user's XDG data dirs.
#
#     scripts/install-fedora.sh            # install
#     scripts/install-fedora.sh --uninstall
#
# NOTE: PyGObject is intentionally a *system* dependency (dnf), not a pip one.
# pip cannot reliably build it without gobject-introspection headers.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
venv="${repo_root}/.venv"

uninstall=0
[[ "${1:-}" == "--uninstall" ]] && uninstall=1

say() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }

if [[ $uninstall -eq 1 ]]; then
  say "Removing user data files"
  rm -f "${data_home}/applications/alpha-ioi.desktop"
  rm -f "${data_home}/metainfo/io.github.aliarifmuhammed.AlphaIOI.metainfo.xml"
  rm -f "${data_home}/icons/hicolor/scalable/apps/alpha-ioi.svg"
  rm -f "${data_home}/icons/hicolor/scalable/apps/io.github.aliarifmuhammed.AlphaIOI.svg"
  for size in 16 32 48 64 128 256 512; do
    rm -f "${data_home}/icons/hicolor/${size}x${size}/apps/alpha-ioi.png"
  done
  command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t "${data_home}/icons/hicolor" 2>/dev/null || true
  command -v update-desktop-database >/dev/null && update-desktop-database "${data_home}/applications" 2>/dev/null || true
  say "Done. (The virtualenv at ${venv} was left in place; remove it manually if you want.)"
  exit 0
fi

# --- system packages --------------------------------------------------------
if command -v dnf >/dev/null 2>&1; then
  say "Installing system packages with dnf (needs sudo)"
  sudo dnf install -y \
    python3 python3-pip python3-gobject gtk4 libadwaita \
    gdk-pixbuf2-modules desktop-file-utils
else
  warn "dnf not found - install python3-gobject, gtk4 and libadwaita manually."
fi

# --- virtualenv that can see system PyGObject -------------------------------
say "Creating virtualenv at ${venv} (--system-site-packages for gi)"
python3 -m venv --system-site-packages "${venv}"
"${venv}/bin/python" -m pip install --upgrade pip >/dev/null
say "Installing Alpha IOI"
"${venv}/bin/python" -m pip install -e "${repo_root}"

# --- icon, desktop entry, metainfo ------------------------------------------
say "Registering icon, desktop entry and metadata in ${data_home}"
mkdir -p "${data_home}/applications" \
         "${data_home}/metainfo" \
         "${data_home}/icons/hicolor/scalable/apps"

# Scalable SVG under the app id as well, so Wayland compositors resolve the
# window icon from the app id (io.github...AlphaIOI -> dashed icon name).
install -m 0644 "${repo_root}/assets/icons/alpha-ioi.svg" \
  "${data_home}/icons/hicolor/scalable/apps/alpha-ioi.svg"
install -m 0644 "${repo_root}/assets/icons/alpha-ioi.svg" \
  "${data_home}/icons/hicolor/scalable/apps/io.github.aliarifmuhammed.AlphaIOI.svg"

# Rasterized sizes, if the generator is available.
if python3 "${repo_root}/scripts/build_icons.py" --outdir "${data_home}/icons/hicolor" --quiet; then
  :
else
  warn "could not rasterize PNG icon sizes; the scalable SVG is still installed."
fi

install -m 0644 "${repo_root}/assets/applications/alpha-ioi.desktop" \
  "${data_home}/applications/alpha-ioi.desktop"
install -m 0644 "${repo_root}/assets/metainfo/io.github.aliarifmuhammed.AlphaIOI.metainfo.xml" \
  "${data_home}/metainfo/io.github.aliarifmuhammed.AlphaIOI.metainfo.xml"

command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t "${data_home}/icons/hicolor" 2>/dev/null || true
command -v update-desktop-database >/dev/null && update-desktop-database "${data_home}/applications" 2>/dev/null || true

say "Installed."
echo
echo "  Run the app:      ${venv}/bin/alpha-ioi"
echo "  Or via module:    ${venv}/bin/python -m alpha_ioi"
echo "  Or from source:   scripts/run.sh"
echo
echo "  From a login shell with ${venv}/bin on PATH you can just type:  alpha-ioi"
