#!/usr/bin/env bash
# Fast ISO patcher for Bastille dev iteration (~1-2 min builds)
# Usage: ./patch-iso.sh <source.iso> <output.iso> [patch-script.sh]
set -euo pipefail

SOURCE_ISO="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUTPUT_ISO="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
PATCH_SCRIPT="${3:-}"

# Build the patch commands
if [[ -n "$PATCH_SCRIPT" && -f "$PATCH_SCRIPT" ]]; then
    PATCH_CMDS="$(cat "$PATCH_SCRIPT")"
else
    PATCH_CMDS='
grep -q "^user:" /mnt/etc/passwd || echo "user:x:1000:1000:Bastille Live User:/home/user:/bin/bash" >> /mnt/etc/passwd
grep -q "^user:" /mnt/etc/shadow || echo "user:8Ab05sVQ4LLps:20754:0:99999:7:::" >> /mnt/etc/shadow
grep -q "^user:" /mnt/etc/group  || echo "user:x:1000:" >> /mnt/etc/group
mkdir -p /mnt/home/user && chown 1000:1000 /mnt/home/user
'
fi

echo "==> Building inside Docker (output via docker cp to avoid VirtioFS corruption)..."
OUTFILE="$(basename "$OUTPUT_ISO")"

# Create container (don't start yet) — source ISO bind-mounted read-only (reads OK through VirtioFS)
CID=$(docker create --privileged \
    -v "${SOURCE_ISO}:/source.iso:ro" \
    bastille-patcher bash -c "
set -euo pipefail

echo '--> extracting squashfs...'
xorriso -osirrox on -indev /source.iso -extract_single /live/filesystem.squashfs /work/fs.squashfs 2>/dev/null

echo '--> unsquashfs...'
unsquashfs -d /mnt /work/fs.squashfs >/dev/null

echo '--> patching...'
$PATCH_CMDS

echo '--> mksquashfs (xz)...'
mksquashfs /mnt /work/fs-patched.squashfs -all-root -comp xz -b 1M -processors 1 -noappend -no-progress 2>&1 | grep -v '^$' || true
ls -lh /work/fs-patched.squashfs

echo '--> building ISO...'
xorriso -indev /source.iso \
    -outdev /work/output.iso \
    -boot_image any replay \
    -map /work/fs-patched.squashfs /live/filesystem.squashfs \
    -commit_eject none 2>/dev/null

ls -lh /work/output.iso
echo '--> ready for docker cp'
")

echo "==> Container $CID created. Starting..."
docker start -a "$CID"
echo "==> Build done. Copying ISO out via docker cp (bypasses VirtioFS)..."
docker cp "${CID}:/work/output.iso" "${OUTPUT_ISO}"
docker rm "$CID"
echo "==> Done: $OUTPUT_ISO"
ls -lh "$OUTPUT_ISO"
