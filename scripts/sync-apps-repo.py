#!/usr/bin/env python3
"""Publish the in-tree apps to a checkout of bastille-linux/apps and regenerate index.json.

usage: scripts/sync-apps-repo.py /path/to/apps-checkout
Source of truth: build/config/includes.chroot/usr/local/bin/bastille-<app>.
Keeps each app's existing manifest.json/icon.svg; bumps nothing automatically
(edit the manifest version when you want clients to show a new number — clients
update on checksum change regardless).
"""
import hashlib, json, os, shutil, sys

SRC = os.path.join(os.path.dirname(__file__), "..", "build/config/includes.chroot/usr/local/bin")
APPS = ["browser", "calendar", "documents", "files", "mail", "maps", "messages",
        "music", "notes", "presentations", "settings", "sheets", "terminal", "weather"]

def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def main(dest):
    index = {"version": 1, "apps": {}}
    for app in APPS:
        d = os.path.join(dest, app)
        os.makedirs(d, exist_ok=True)
        shutil.copyfile(os.path.join(SRC, f"bastille-{app}"), os.path.join(d, "main.py"))
        mf = {}
        try:
            mf = json.load(open(os.path.join(d, "manifest.json")))
        except (OSError, ValueError):
            pass
        files = {"main.py": sha(os.path.join(d, "main.py"))}
        if os.path.exists(os.path.join(d, "icon.svg")):
            files["icon.svg"] = sha(os.path.join(d, "icon.svg"))
        index["apps"][app] = {"id": mf.get("id", f"com.bastille.{app}"),
                              "name": mf.get("name", app.title()),
                              "description": mf.get("description", ""),
                              "version": mf.get("version", "0.1.0"),
                              "files": files}
    with open(os.path.join(dest, "index.json"), "w") as f:
        json.dump(index, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"wrote {len(APPS)} apps + index.json to {dest}")

if __name__ == "__main__":
    main(sys.argv[1])
