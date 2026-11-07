#!/usr/bin/env bash
# Static validation for the reproducible image-build inputs.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CHECK_APT=0
[ "${1:-}" = "--check-apt" ] && CHECK_APT=1

if [ "$CHECK_APT" -eq 1 ] && ! command -v apt-cache >/dev/null 2>&1; then
    echo "ERROR: --check-apt requires apt-cache (available in the Debian CI builder)." >&2
    exit 2
fi

failures=0
fail() { echo "ERROR: $*" >&2; failures=$((failures + 1)); }

echo "Checking hook names and permissions"
last=-1
for hook in "$ROOT"/build/config/hooks/live/*.hook.chroot; do
    name=${hook##*/}
    number=${name%%-*}
    case "$number" in ''|*[!0-9]*) fail "invalid hook prefix: $name"; continue ;; esac
    [ "$number" -ge "$last" ] || fail "hooks are not ordered near $name"
    last=$number
    if [ -L "$hook" ]; then
        target=$(readlink "$hook")
        case "$target" in /usr/share/live/build/*) : ;; *) fail "unexpected hook symlink: $name -> $target" ;; esac
    elif [ ! -x "$hook" ]; then
        fail "hook is not executable: $name"
    fi
done

echo "Checking shell syntax"
while IFS= read -r -d '' file; do
    first=$(LC_ALL=C head -c 256 "$file" | LC_ALL=C tr -d '\000' | sed -n '1p')
    case "$first" in
        '#!/bin/bash'*) bash -n "$file" || fail "bash syntax: ${file#$ROOT/}" ;;
        '#!/bin/sh'*) sh -n "$file" || fail "sh syntax: ${file#$ROOT/}" ;;
    esac
done < <(find "$ROOT"/build "$ROOT"/src "$ROOT" -maxdepth 8 -type f \
    \( -name '*.sh' -o -name '*.hook.chroot' -o -name 'build' -o -name 'config' \) \
    -print0)

echo "Checking Python syntax"
while IFS= read -r -d '' file; do
    python3 - "$file" <<'PY'
import ast
import pathlib
import sys
ast.parse(pathlib.Path(sys.argv[1]).read_text(), filename=sys.argv[1])
PY
done < <(find "$ROOT/build" -type f -name '*.py' -print0)

echo "Checking package references"
while IFS= read -r -d '' list; do
    while IFS= read -r line || [ -n "$line" ]; do
        package=$(printf '%s\n' "$line" | sed 's/[[:space:]]*#.*$//' | awk '{$1=$1; print}')
        [ -n "$package" ] || continue
        case "$package" in
            *[!A-Za-z0-9+._:-]*) fail "invalid package token '$package' in ${list#$ROOT/}"; continue ;;
        esac
        package=${package%-}
        [ "$package" = "swaybar" ] && fail "stale package reference: swaybar"
        [ "$package" = "greetd-tuigreet" ] && fail "stale package reference: greetd-tuigreet"
        if [ "$CHECK_APT" -eq 1 ]; then
            apt-cache show "$package" 2>/dev/null | grep -q '^Package:' || fail "package not found in apt metadata: $package"
        fi
    done < "$list"
done < <(find "$ROOT/build/config/package-lists" -type f -name '*.list.chroot' -print0)

echo "Checking architecture handling"
grep -q 'grub-efi-amd64-bin' "$ROOT/build/config/hooks/live/0005-bastille-architecture-packages.hook.chroot" || fail "amd64 GRUB package missing from architecture hook"
grep -q 'grub-efi-arm64-bin' "$ROOT/build/config/hooks/live/0005-bastille-architecture-packages.hook.chroot" || fail "arm64 GRUB package missing from architecture hook"
if grep -qE '^grub-efi-(amd64|arm64)-bin$' "$ROOT/build/config/package-lists/bastille-base.list.chroot"; then
    fail "architecture-specific GRUB package leaked into common package list"
fi

echo "Checking OpenRC service graph"
grep -q 'command="/usr/sbin/NetworkManager"' "$ROOT/build/config/includes.chroot/etc/init.d/networkmanager" || fail "NetworkManager OpenRC wrapper missing"
grep -q 'need nftables' "$ROOT/build/config/hooks/live/0090-bastille-new-features.hook.chroot" || fail "network guard does not require nftables"
if rg -n 'thl-dns-lock' "$ROOT/build/config/includes.chroot/etc/init.d" "$ROOT/build/config/hooks/live" >/dev/null; then
    fail "stale OpenRC dependency name: thl-dns-lock"
fi
if rg -n 'need localmount' "$ROOT/build/config/includes.chroot/etc/init.d" >/dev/null; then
    fail "OpenRC service graph references nonexistent localmount"
fi
grep -q 'curl -fsSI' "$ROOT/build/config/includes.chroot/etc/init.d/bastille-tlsdate" || fail "HTTPS time-sync implementation missing"

echo "Checking source/build mirrors"
for source in "$ROOT"/src/*/*; do
    [ -f "$source" ] || continue
    relative=${source#"$ROOT/src/"}
    mirror="$ROOT/build/config/includes.chroot/usr/local/src/$relative"
    [ -e "$mirror" ] || continue
    cmp -s "$source" "$mirror" || fail "source/build drift: ${relative}"
done

if [ "$failures" -ne 0 ]; then
    echo "Build validation failed with $failures error(s)." >&2
    exit 1
fi
echo "Build validation passed."
