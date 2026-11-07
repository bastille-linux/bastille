#!/bin/bash
# THL Modern — top-level build script
# Requires: live-build, debootstrap, squashfs-tools, xorriso
# Run as root inside the build/ directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

echo "=== Tinfoil Hat Linux Modern — Build ==="
echo "Build dir: $BUILD_DIR"
echo

# Sanity checks
if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: live-build must run as root (or under sudo)." >&2
  exit 1
fi

command -v lb >/dev/null 2>&1 || {
  echo "ERROR: live-build not found. Install with: apt install live-build" >&2
  exit 1
}

# live-build keeps bootstrap/chroot state across invocations.  Reusing a
# Bookworm cache after switching the project to Trixie produces a deceptively
# successful `lb config` followed by a Bookworm image.  Invalidate only the
# generated build state when the cache proves it belongs to the old suite.
if find "$BUILD_DIR/cache/packages.bootstrap" -maxdepth 1 -type f -name '*deb12*' -print -quit 2>/dev/null | grep -q .; then
  echo "--- Removing stale Bookworm live-build state ---"
  (cd "$BUILD_DIR" && lb clean --cache --chroot --binary --stage)
fi

# Older live-build runs also leave generated config files behind.  `lb config`
# preserves those files, so remove only the generated suite/architecture files
# when they advertise Bookworm; the checked-in package lists and hooks remain.
if [ -f "$BUILD_DIR/config/bootstrap" ] &&
   grep -qE 'LB_DISTRIBUTION="bookworm"|LB_DISTRIBUTION_CHROOT="bookworm"|LB_DISTRIBUTION_BINARY="bookworm"' "$BUILD_DIR/config/bootstrap"; then
  echo "--- Removing stale Bookworm generated configuration ---"
  rm -f "$BUILD_DIR/config/bootstrap" "$BUILD_DIR/config/binary" \
        "$BUILD_DIR/config/chroot" "$BUILD_DIR/config/common" \
        "$BUILD_DIR/config/source"
fi

# Make auto/* scripts executable
chmod +x "$BUILD_DIR"/auto/*
chmod +x "$BUILD_DIR"/config/hooks/live/*.hook.chroot 2>/dev/null || true

cd "$BUILD_DIR"

echo "--- Configuring live-build ---"
lb config "${@}"

echo "--- Building ISO ---"
lb build

ISO=$(ls -1t "$BUILD_DIR"/live-image-*.hybrid.iso 2>/dev/null | head -1)
if [ -n "$ISO" ]; then
  echo
  echo "=== Build complete ==="
  echo "ISO: $ISO"
  sha512sum "$ISO"
else
  echo "ERROR: ISO not found after build — check build.log" >&2
  exit 1
fi
