#!/usr/bin/env bash
# End-to-end encrypted backup/restore test. It is designed for the Debian CI
# builder, where age is installed by the workflow.
set -euo pipefail

if ! command -v age >/dev/null 2>&1; then
    echo "Backup round-trip test skipped: age is not installed."
    exit 0
fi

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKUP="$ROOT/build/config/includes.chroot/usr/local/bin/bastille-backup"
TMP=$(mktemp -d)
TEST_USER=""
cleanup() {
    if [ -n "$TEST_USER" ]; then userdel -r "$TEST_USER" 2>/dev/null || true; fi
    rm -rf -- "$TMP"
}
trap cleanup EXIT

if [ "$(id -u)" -eq 0 ]; then
    TEST_USER="bastille-backup-test"
    useradd --create-home --home-dir "$TMP/home" --shell /bin/bash "$TEST_USER"
    chown "$TEST_USER:$TEST_USER" "$TMP"
    RUN=(runuser -u "$TEST_USER" -- env HOME="$TMP/home")
else
    RUN=(env HOME="$HOME")
    mkdir -p "$HOME"
fi

printf '%s\n' 'daily-driver backup test' > "$TMP/home/important.txt"
run_with_tty() {
    local command_line
    printf -v command_line '%q ' "$@"
    printf 'test-passphrase\ntest-passphrase\n' \
        | script -qec "$command_line" /dev/null >/dev/null
}
run_with_tty "${RUN[@]}" bash "$BACKUP" create "$TMP/backup.age"
run_with_tty "${RUN[@]}" bash "$BACKUP" restore "$TMP/backup.age" "$TMP/restored"
cmp -s "$TMP/home/important.txt" "$TMP/restored/important.txt"
echo "Backup round-trip test passed."
