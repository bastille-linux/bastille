"""Bastille shell — system helpers (sway IPC, status, apps). All calls are best-effort."""

import glob
import json
import os
import subprocess

from gi.repository import Gio, GLib


def run(cmd, timeout=3):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def spawn(cmd):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception:  # noqa: BLE001
        pass


# ── sway ──────────────────────────────────────────────────────────────────────

def sway_tree():
    try:
        return json.loads(run(["swaymsg", "-t", "get_tree", "-r"]))
    except Exception:  # noqa: BLE001
        return {}


def sway_windows():
    """[(app_id, title, focused, con_id)] for every view."""
    out = []

    def walk(n):
        if n.get("pid") and (n.get("app_id") or n.get("window_properties")):
            app = n.get("app_id") or (n.get("window_properties") or {}).get("class") or ""
            out.append((app, n.get("name") or "", bool(n.get("focused")), n.get("id")))
        for c in n.get("nodes", []) + n.get("floating_nodes", []):
            walk(c)
    walk(sway_tree())
    return out


def focused_app():
    for app, title, foc, _ in sway_windows():
        if foc:
            return app, title
    return "", ""


def sway_msg(*args):
    spawn(["swaymsg", *args])


def sway_subscribe(callback):
    """Call callback() on window/workspace events (debounced by the caller)."""
    try:
        p = subprocess.Popen(["swaymsg", "-t", "subscribe", "-m", '["window","workspace"]'],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except Exception:  # noqa: BLE001
        return
    ch = GLib.IOChannel.unix_new(p.stdout.fileno())

    def on_io(_ch, _cond):
        try:
            p.stdout.readline()
        except Exception:  # noqa: BLE001
            return False
        callback()
        return True
    GLib.io_add_watch(ch, GLib.PRIORITY_DEFAULT, GLib.IOCondition.IN | GLib.IOCondition.HUP, on_io)
    sway_subscribe.proc = p


# ── applications ──────────────────────────────────────────────────────────────

def all_apps():
    """Gio.AppInfo list (visible, sorted by name)."""
    apps = [a for a in Gio.AppInfo.get_all() if a.should_show()]
    apps.sort(key=lambda a: a.get_display_name().lower())
    return apps


def app_by_id(desktop_id):
    try:
        return Gio.DesktopAppInfo.new(desktop_id)
    except TypeError:
        return None


# ── network / battery / audio / brightness ────────────────────────────────────

def network():
    """('wifi'|'eth'|'none', ssid_or_iface)"""
    out = run(["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device"])
    for line in out.splitlines():
        t, s, c = (line.split(":") + ["", "", ""])[:3]
        if s == "connected":
            return ("wifi" if t == "wifi" else "eth"), c
    return "none", ""


def wifi_enabled():
    return run(["nmcli", "radio", "wifi"]) == "enabled"


def set_wifi(on):
    spawn(["nmcli", "radio", "wifi", "on" if on else "off"])


def wifi_networks():
    out = run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list"], timeout=6)
    nets, seen = [], set()
    for line in out.splitlines():
        parts = line.replace("\\:", "\x00").split(":")
        if len(parts) < 4 or not parts[1] or parts[1] in seen:
            continue
        seen.add(parts[1])
        nets.append((parts[1].replace("\x00", ":"), int(parts[2] or 0), parts[0] == "*", bool(parts[3])))
    return nets


def battery():
    """(percent, charging) or None when there is no battery."""
    for d in glob.glob("/sys/class/power_supply/BAT*"):
        try:
            pct = int(open(d + "/capacity").read())
            st = open(d + "/status").read().strip()
            return pct, st in ("Charging", "Full")
        except Exception:  # noqa: BLE001
            continue
    return None


def volume():
    """(0..100, muted)"""
    out = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    if out.startswith("Volume:"):
        try:
            return int(float(out.split()[1]) * 100), "MUTED" in out
        except Exception:  # noqa: BLE001
            pass
    return 50, False


def set_volume(pct):
    spawn(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{max(0, min(100, int(pct)))}%"])


def toggle_mute():
    spawn(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])


def brightness():
    out = run(["brightnessctl", "-m"])
    try:
        return int(out.split(",")[3].rstrip("%"))
    except Exception:  # noqa: BLE001
        return None


def set_brightness(pct):
    spawn(["brightnessctl", "set", f"{max(1, min(100, int(pct)))}%"])


def vpn_active():
    return "wg" in run(["ip", "-o", "link", "show", "type", "wireguard"]) or \
        "tun" in run(["ip", "-o", "link", "show", "type", "tun"])


def bluetooth_blocked():
    return True    # Bastille ships Bluetooth hard-blocked (see rfkill hook)


# ── DND (shared with the notification daemon) ─────────────────────────────────

STATE_DIR = os.path.join(GLib.get_user_config_dir(), "bastille")


def state_load(name, default):
    try:
        with open(os.path.join(STATE_DIR, name)) as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def state_save(name, data):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(os.path.join(STATE_DIR, name), "w") as f:
            json.dump(data, f)
    except Exception:  # noqa: BLE001
        pass
