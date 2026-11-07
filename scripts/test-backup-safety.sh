#!/usr/bin/env bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKUP="$ROOT/build/config/includes.chroot/usr/local/bin/bastille-backup"
bash -n "$BACKUP"
grep -q -- '--encrypt --passphrase' "$BACKUP"
grep -q 'refusing to overwrite existing archive' "$BACKUP"
grep -q -- '--into-home' "$BACKUP"
grep -q -- 'no-same-owner' "$BACKUP"
echo "Backup safety checks passed."
