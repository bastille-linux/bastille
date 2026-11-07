#!/usr/bin/env bash
# Exercise the live-image rollback transaction without touching a real disk.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Update rollback test skipped: root is required for the live-media guard."
    exit 0
fi

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
UPDATER="$ROOT/build/config/includes.chroot/usr/local/sbin/bastille-update"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/live"
printf '%s\n' new >"$TMP/live/filesystem.squashfs"
printf '%s\n' old >"$TMP/live/filesystem.squashfs.previous"
printf '%s\n' new-version >"$TMP/live/bastille-version"
printf '%s\n' old-version >"$TMP/live/bastille-version.previous"

BASTILLE_BOOT_MEDIUM="$TMP" \
BASTILLE_VERSION_FILE="$TMP/running-version" \
BASTILLE_NOTIFY_USER=root \
    bash "$UPDATER" rollback >/dev/null

[ "$(cat "$TMP/live/filesystem.squashfs")" = old ]
[ "$(cat "$TMP/live/bastille-version")" = old-version ]
[ "$(cat "$TMP/live/filesystem.squashfs.failed")" = new ]
[ ! -e "$TMP/live/filesystem.squashfs.previous" ]
echo "Update rollback transaction test passed."
