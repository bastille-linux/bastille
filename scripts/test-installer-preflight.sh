#!/usr/bin/env bash
# Regression test for the installer's non-destructive validation entry point.
# This is intentionally runnable on a normal development host: the fake disk
# must be rejected before the installer asks for any partitioning tool.
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKEND="$ROOT/build/config/includes.chroot/usr/local/sbin/bastille-install-backend"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

set +e
printf '%s\n' '{"disk":"/dev/bastille-test-does-not-exist","confirm":"/dev/bastille-test-does-not-exist","passphrase":"long-enough-passphrase","username":"alice","password":"test","hostname":"bastille"}' \
    | python3 "$BACKEND" --preflight >"$TMP" 2>&1
status=$?
set -e

[ "$status" -ne 0 ] || { echo "preflight unexpectedly accepted a nonexistent disk" >&2; exit 1; }
# On an ordinary workstation the root guard is the first safe rejection. In
# the privileged CI/container job the disk guard is reached instead.
grep -Eq 'must run as root|not a block device' "$TMP" || { cat "$TMP" >&2; exit 1; }
! grep -q 'Partitioning' "$TMP" || { echo "preflight reached partitioning" >&2; exit 1; }

python3 - "$BACKEND" <<'PY'
import importlib.machinery
import importlib.util
import builtins
import io
import pathlib
import sys
import tempfile
from unittest import mock

loader = importlib.machinery.SourceFileLoader("bastille_install_backend", sys.argv[1])
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)

with mock.patch.object(module.os, "listdir", return_value=["SecureBoot-1234"]), \
     mock.patch.object(module.os.path, "isfile", return_value=True), \
     mock.patch.object(builtins, "open", return_value=io.BytesIO(b"\0" * 4 + b"\1")):
    assert module.secure_boot_enabled()

with mock.patch.object(module.os, "listdir", return_value=["SecureBoot-1234"]), \
     mock.patch.object(module.os.path, "isfile", return_value=True), \
     mock.patch.object(builtins, "open", return_value=io.BytesIO(b"\0" * 5)):
    assert not module.secure_boot_enabled()
PY

echo "Installer preflight safety test passed."
