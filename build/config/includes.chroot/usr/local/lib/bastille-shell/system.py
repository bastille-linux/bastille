"""Bastille shell — system helpers (sway IPC, status, apps). All calls are best-effort."""

import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import time

from gi.repository import Gio, GLib

LOG = os.path.join(GLib.get_user_cache_dir(), "bastille-shell.log")


def log(msg):
    """Append a line to ~/.cache/bastille-shell.log (the shell has no visible stderr)."""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(time.strftime("%H:%M:%S ") + str(msg) + "\n")
    except Exception:  # noqa: BLE001
        pass


def clean_env():
    """Environment for child processes: the shell preloads gtk4-layer-shell, apps must not inherit that."""
    env = dict(os.environ)
    env.pop("LD_PRELOAD", None)
    return env


def run(cmd, timeout=3):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def spawn(cmd):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
                         env=clean_env())
        return True
    except Exception as e:  # noqa: BLE001
        log(f"spawn {cmd!r} failed: {e}")
        return False


# ── sway ──────────────────────────────────────────────────────────────────────

def sway_tree():
    try:
        return json.loads(run(["swaymsg", "-t", "get_tree", "-r"]))
    except Exception:  # noqa: BLE001
        return {}


def sway_windows_full():
    """[dict(app, title, focused, id, pid)] for every view."""
    out = []

    def walk(n):
        if n.get("pid") and (n.get("app_id") or n.get("window_properties")):
            app = n.get("app_id") or (n.get("window_properties") or {}).get("class") or ""
            out.append({"app": app, "title": n.get("name") or "", "focused": bool(n.get("focused")),
                        "id": n.get("id"), "pid": n.get("pid")})
        for c in n.get("nodes", []) + n.get("floating_nodes", []):
            walk(c)
    walk(sway_tree())
    return out


def sway_windows():
    """[(app_id, title, focused, con_id)] for every view."""
    return [(w["app"], w["title"], w["focused"], w["id"]) for w in sway_windows_full()]


def force_quit(pid):
    try:
        os.kill(int(pid), 9)
    except Exception as e:  # noqa: BLE001
        log(f"force quit {pid}: {e}")


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

def is_live():
    try:
        return os.path.isdir("/run/live/medium") or "boot=live" in open("/proc/cmdline").read()
    except Exception:  # noqa: BLE001
        return False


def desktop_base(info):
    did = info.get_id() or ""
    return did[:-8] if did.endswith(".desktop") else did


def all_apps():
    """Apps the user actually has: Bastille's own apps plus anything installed from the App Store
    (Flatpak) or into ~/.local. Distro leftovers (foot, htop, vim, firefox-esr ...) are hidden."""
    out = []
    for a in Gio.AppInfo.get_all():
        if not a.should_show():
            continue
        base = desktop_base(a)
        path = getattr(a, "get_filename", lambda: "")() or ""
        if base.startswith("bastille-"):
            if base == "bastille-setup" or (base == "bastille-install" and not is_live()):
                continue
            out.append(a)
        elif "/flatpak/exports/" in path or "/.local/share/applications/" in path:
            out.append(a)
    out.sort(key=lambda a: a.get_display_name().lower())
    return out


def app_by_id(desktop_id):
    try:
        return Gio.DesktopAppInfo.new(desktop_id)
    except TypeError:
        return None


_names = {}


def app_name_for(app_id):
    """Human name for a sway app_id (org.bastilleos.Files -> Files), or '' when unknown."""
    if not app_id:
        return ""
    key = app_id.lower()
    if key in _names:
        return _names[key]
    tail = key.split(".")[-1]
    name = ""
    for a in Gio.AppInfo.get_all():
        base = desktop_base(a).lower()
        wm = (getattr(a, "get_startup_wm_class", lambda: "")() or "").lower()
        if key in (base, wm) or base in ("bastille-" + tail, tail):
            name = a.get_display_name()
            break
    _names[key] = name
    return name


def _strip_codes(cmd):
    return re.sub(r"\s%[a-zA-Z]", "", cmd).replace("%%", "%").strip()


def launch(info):
    """Start an application reliably (clean environment, terminal apps in foot). True if started."""
    base = desktop_base(info)
    try:
        recent = state_load("recent.json", {}).get("apps", [])
        recent = [base] + [r for r in recent if r != base]
        state_save("recent.json", {"apps": recent[:10]})
    except Exception:  # noqa: BLE001
        pass
    try:
        cmdline = _strip_codes(info.get_commandline() or "")
        if getattr(info, "get_boolean", lambda k: False)("Terminal") and cmdline:
            return spawn(["foot", "-e", *shlex.split(cmdline)])
        ctx = Gio.AppLaunchContext()
        ctx.unsetenv("LD_PRELOAD")
        if info.launch([], ctx):
            return True
        log(f"Gio launch of {base} returned False, falling back to Exec")
    except Exception as e:  # noqa: BLE001
        log(f"Gio launch of {base} failed: {e}")
    try:
        return spawn(shlex.split(_strip_codes(info.get_commandline() or "")))
    except Exception as e:  # noqa: BLE001
        log(f"fallback launch of {base} failed: {e}")
        return False


def open_path(path):
    """Folders open in Files, everything else through the default handler."""
    if os.path.isdir(path):
        return spawn(["bastille-files", path])
    return spawn(["xdg-open", path])


def recent_apps(n=5):
    out = []
    for did in state_load("recent.json", {}).get("apps", []):
        info = app_by_id(did + ".desktop")
        if info is not None and info.should_show():
            out.append(info)
        if len(out) >= n:
            break
    return out


def about_info():
    d = {"version": read_text("/etc/bastille/version", "dev"), "kernel": os.uname().release,
         "host": os.uname().nodename, "arch": os.uname().machine}
    cpu = ""
    try:
        for line in open("/proc/cpuinfo"):
            k, _, v = line.partition(":")
            if k.strip() in ("model name", "Hardware", "Model", "Processor") and v.strip():
                cpu = v.strip()
                break
    except Exception:  # noqa: BLE001
        pass
    d["cpu"] = cpu or os.uname().machine
    try:
        kb = int(next(l for l in open("/proc/meminfo") if l.startswith("MemTotal")).split()[1])
        d["memory"] = f"{kb / 1048576:.1f} GB"
    except Exception:  # noqa: BLE001
        d["memory"] = "—"
    return d


def read_text(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:  # noqa: BLE001
        return default


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
    run(["nmcli", "radio", "wifi", "on" if on else "off"], timeout=5)


def wifi_networks(rescan="auto", timeout=8):
    """[(ssid, signal, in_use, secured)], strongest first, one row per SSID."""
    out = run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", rescan],
              timeout=timeout)
    nets = {}
    for line in out.splitlines():
        parts = line.replace("\\:", "\x00").split(":")
        if len(parts) < 4 or not parts[1]:
            continue
        ssid = parts[1].replace("\x00", ":")
        try:
            sig = int(parts[2] or 0)
        except ValueError:
            sig = 0
        row = (ssid, sig, parts[0] == "*", bool(parts[3].strip()))
        if ssid not in nets or row[2] or (not nets[ssid][2] and sig > nets[ssid][1]):
            nets[ssid] = row
    return sorted(nets.values(), key=lambda n: (not n[2], -n[1], n[0].lower()))


def wifi_known():
    out = run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
    known = set()
    for line in out.splitlines():
        name, _, typ = line.rpartition(":")
        if typ in ("802-11-wireless", "wifi"):
            known.add(name.replace("\\:", ":"))
    return known


def wifi_connect(ssid, password=None):
    """(ok, message). Known networks reuse their saved profile."""
    try:
        if password is None and ssid in wifi_known():
            r = subprocess.run(["nmcli", "connection", "up", "id", ssid], capture_output=True, text=True, timeout=30)
        else:
            cmd = ["nmcli", "device", "wifi", "connect", ssid] + (["password", password] if password else [])
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.returncode == 0, (r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else ""
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def wifi_disconnect():
    for line in run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"]).splitlines():
        dev, typ, state = (line.split(":") + ["", "", ""])[:3]
        if typ == "wifi" and state == "connected":
            run(["nmcli", "device", "disconnect", dev], timeout=10)


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
    return bt_state() in ("blocked", "none")


def bt_tools():
    return shutil.which("bluetoothctl") is not None


def bt_state():
    """'none' (no adapter / no bluez), 'blocked' (rfkill, Bastille's default), 'off', 'on'."""
    rf = run(["rfkill", "list", "bluetooth"])
    if not rf:
        return "none"
    if re.search(r"(Soft|Hard) blocked: yes", rf):
        return "blocked"
    if not bt_tools():
        return "none"
    return "on" if "Powered: yes" in run(["bluetoothctl", "show"], timeout=4) else "off"


def set_bluetooth(on):
    if on:
        run(["rfkill", "unblock", "bluetooth"], timeout=5)
        if bt_tools():
            run(["bluetoothctl", "power", "on"], timeout=6)
    else:
        if bt_tools():
            run(["bluetoothctl", "power", "off"], timeout=6)
        run(["rfkill", "block", "bluetooth"], timeout=5)


def bt_devices():
    """[dict(mac, name, connected, paired, battery, kind)] for known devices."""
    if not bt_tools():
        return []
    devs = []
    for line in run(["bluetoothctl", "devices"], timeout=5).splitlines():
        parts = line.split(" ", 2)
        if len(parts) < 3 or parts[0] != "Device":
            continue
        mac, name = parts[1], parts[2]
        info = run(["bluetoothctl", "info", mac], timeout=4)
        bat = re.search(r"Battery Percentage: 0x[0-9a-fA-F]+ \((\d+)\)", info)
        kind = re.search(r"Icon: (\S+)", info)
        devs.append({"mac": mac, "name": name, "connected": "Connected: yes" in info,
                     "paired": "Paired: yes" in info, "battery": int(bat.group(1)) if bat else None,
                     "kind": kind.group(1) if kind else ""})
    devs.sort(key=lambda d: (not d["connected"], not d["paired"], d["name"].lower()))
    return devs


def bt_connect(mac, on=True):
    out = run(["bluetoothctl", "connect" if on else "disconnect", mac], timeout=15)
    return ("successful" in out.lower()) if on else True


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
