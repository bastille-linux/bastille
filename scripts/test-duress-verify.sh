#!/usr/bin/env bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERIFY="$ROOT/build/config/includes.chroot/usr/local/sbin/bastille-duress-verify"
bash -n "$VERIFY"
grep -q 'recovery resistance' "$VERIFY"
grep -q 'cryptographic wipe contract' "$VERIFY"
echo "Duress verification checks passed."
