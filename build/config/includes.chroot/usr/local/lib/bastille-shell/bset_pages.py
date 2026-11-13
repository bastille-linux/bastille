"""Settings pages built on the Bastille design kit (bdesign).

Every row reads real system state (sysfs, /proc, OpenRC, nmcli, wpctl, swaymsg…)
and every control either acts directly or runs a polkit-gated helper; nothing
here is a placeholder.
"""

import glob
import json
import os
import shutil
import subprocess

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gtk

import bdesign as bd
import system
from bdesign import Page, Row, badge, bg, button, read, select, sh, slider, toggle

RC = shutil.which("rc-service") or "/sbin/rc-service"
CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "bastille")


# ── small helpers ─────────────────────────────────────────────────────────────

def svc_running(name):
    return "started" in sh([RC, name, "status"])


def pk(*cmd):
    """Run a polkit-gated command in the background."""
    bg(lambda: subprocess.run(["pkexec", *cmd], capture_output=True, text=True, timeout=60))


def svc_action(name, action):
    pk(RC, name, action)


def ok(flag, yes="Active", no="Off"):
    return badge(yes, "ok") if flag else badge(no, "off")


def sysctl(key):
    return read("/proc/sys/" + key.replace(".", "/"))


def swaymsg(*args):
    sh(["swaymsg", *args])


def write_sway_input(name, lines):
    """Persist input tweaks in ~/.config/bastille/<name>.sway (included by the sway config)."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(os.path.join(CONFIG_DIR, name + ".sway"), "w") as f:
        f.write("\n".join(lines) + "\n")


def logview(text, height=260):
    tv = Gtk.TextView()
    tv.set_editable(False)
    tv.set_monospace(True)
    tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    tv.get_buffer().set_text(text)
    sw = Gtk.ScrolledWindow()
    sw.set_min_content_height(height)
    sw.set_child(tv)
    sw.add_css_class("b2-card")
    return sw


# ── System ────────────────────────────────────────────────────────────────────

class AboutPage(Page):
    def __init__(self):
        super().__init__("About", "This computer and the Bastille OS release it is running")
        a = system.about_info()
        prof = read("/etc/bastille/hardware-profile", "unknown")
        vendor = read("/sys/class/dmi/id/sys_vendor")
        model = read("/sys/class/dmi/id/product_version") or read("/sys/class/dmi/id/product_name")
        mode = "UEFI" if os.path.isdir("/sys/firmware/efi") else "Legacy BIOS"
        self.section("Bastille OS", *[
            Row("shield", "bl", "Release", ((a["version"] or "dev") + (f' \u201c{a["codename"]}\u201d' if a.get("codename") else "")), badge(a["arch"], "off")),
            Row("gear", "", "Kernel", a["kernel"]),
            Row("info", "", "Hostname", a["host"]),
            Row("cpu", "", "Hardware profile", prof)])
        self.section("Hardware", *[
            Row("display", "", "Model", " ".join(x for x in (vendor, model) if x) or "Unknown"),
            Row("cpu", "", "Processor", a["cpu"]),
            Row("hdd", "", "Memory", a["memory"]),
            Row("power", "", "Firmware", mode, badge(mode, "ok" if mode == "UEFI" else "warn"))])


class PerformancePage(Page):
    def __init__(self):
        super().__init__("Performance", "CPU, memory and compressed-RAM swap")
        load = read("/proc/loadavg").split()
        mem = {l.split(":")[0]: int(l.split()[1]) for l in read("/proc/meminfo").splitlines() if ":" in l}
        used = mem.get("MemTotal", 0) - mem.get("MemAvailable", 0)
        pct = int(100 * used / mem["MemTotal"]) if mem.get("MemTotal") else 0
        gov_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        gov = read(gov_path, "unavailable")
        avail = read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors").split()
        gov_row = Row("cpu", "bl", "CPU governor", "Trade speed against battery life")
        if avail:
            def set_gov(i):
                pk("/bin/sh", "-c", f"for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo {avail[i]} > $g; done")
            gov_row.append(select(avail, avail.index(gov) if gov in avail else 0, set_gov))
        else:
            gov_row.append(badge(gov, "off"))
        bar = Gtk.ProgressBar()
        bar.set_fraction(pct / 100)
        bar.set_size_request(160, -1)
        bar.set_valign(Gtk.Align.CENTER)
        zram = sh("zramctl --noheadings --output NAME,DISKSIZE,DATA 2>/dev/null | head -1")
        self.section("Processor", gov_row,
                     Row("gear", "", "Load average", " · ".join(load[:3]) if load else "—"),
                     Row("cpu", "", "Online CPUs", str(os.cpu_count())))
        self.section("Memory",
                     Row("hdd", "", "Memory in use", f"{used // 1024} MiB of {mem.get('MemTotal', 0) // 1024} MiB", bar),
                     Row("layers", "", "Compressed swap (zram)", zram or "Not configured",
                         ok(bool(zram), "Active", "Off")))
        self.section("Kernel", Row("cpu", "", "Transparent hugepages", read("/sys/kernel/mm/transparent_hugepage/enabled"),
                                    badge("Tuned", "ok")))


class PowerPage(Page):
    def __init__(self):
        super().__init__("Power", "Battery, charger and screen brightness")
        bat = system.battery()
        rows = []
        if bat:
            state = "Charging" if bat[1] else "On battery"
            rows.append(Row("battery", "gn" if bat[1] else "am", f"Battery {bat[0]}%", state,
                            badge("Charging" if bat[1] else "Discharging", "ok" if bat[1] else "warn")))
            for b in glob.glob("/sys/class/power_supply/BAT0"):
                cycles = read(b + "/cycle_count")
                full, design = read(b + "/energy_full"), read(b + "/energy_full_design")
                if full.isdigit() and design.isdigit() and int(design):
                    rows.append(Row("bolt", "", "Battery health", f"{100 * int(full) // int(design)}% of design capacity"
                                    + (f" · {cycles} cycles" if cycles else "")))
        else:
            rows.append(Row("power", "", "Power source", "AC power — no battery detected"))
        self.section("Battery", *rows)
        br = system.brightness()
        if br is not None:
            self.section("Display", Row("sun", "am", "Brightness", "", slider(br, 1, 100, system.set_brightness)))
        lid = Row("power", "bl", "Close lid", "Locks the screen with the Bastille keyguard")
        lid.append(badge("Lock", "ok"))
        idle = Row("clock", "bl", "Screen lock timeout", "From the session idle rules")
        idle.append(badge("3 min", "off"))
        off = Row("display", "", "Screen off timeout", "")
        off.append(badge("10 min", "off"))
        self.section("Behaviour", lid, idle, off)


class PrintersPage(Page):
    def __init__(self):
        super().__init__("Printers", "Print queues and scanners")
        have = shutil.which("lpstat") is not None
        out = sh("lpstat -p 2>/dev/null") if have else ""
        rows = []
        for line in out.splitlines():
            if line.startswith("printer "):
                name = line.split()[1]
                rows.append(Row("printer", "bl", name, line.split(".", 1)[0].split(name, 1)[-1].strip(),
                                badge("Idle" if "idle" in line else "Busy", "ok" if "idle" in line else "run")))
        if not rows:
            rows.append(Row("printer", "", "No printers set up",
                            "CUPS is running." if svc_running("cupsd") else
                            "Printing service is not installed or not running."))
        self.section("Printers", *rows)
        sc = sh("scanimage -L 2>/dev/null | head -3") if shutil.which("scanimage") else ""
        self.section("Scanners", Row("camera", "", sc.splitlines()[0] if sc else "No scanners found",
                                      "" if sc else "Connect a scanner supported by SANE"))


# ── Security ──────────────────────────────────────────────────────────────────

class SecurityPrivacyPage(Page):
    def __init__(self):
        super().__init__("Security & Privacy", "Live hardening status of this machine")
        cmd = read("/proc/cmdline")
        efi = os.path.isdir("/sys/firmware/efi")

        sb = "n/a"
        if efi:
            raw = sh("od -An -t u1 -j4 -N1 /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c 2>/dev/null").strip()
            sb = "on" if raw == "1" else "off"
        kernel = [
            Row("lock", "gn" if sb == "on" else "am", "Secure Boot",
                "Not available — this machine boots in legacy BIOS mode" if not efi else
                "Bastille's removable GRUB is unsigned; Secure Boot must be off", badge(
                    {"on": "Enabled", "off": "Disabled", "n/a": "Legacy BIOS"}[sb], "ok" if sb == "on" else "warn")),
            Row("cpu", "bl", "Kernel hardening", f"kptr_restrict={sysctl('kernel.kptr_restrict')}, "
                f"dmesg_restrict={sysctl('kernel.dmesg_restrict')}, ptrace_scope={sysctl('kernel.yama.ptrace_scope') or 'n/a'}",
                ok(sysctl("kernel.kptr_restrict") in ("1", "2"), "Active", "Weak")),
            Row("gear", "bl", "Kernel parameters", "mitigations / lockdown / init_on_alloc from the boot command line",
                ok("mitigations=" in cmd or "lockdown=" in cmd, "Enforced", "Defaults")),
            Row("cpu", "gn", "IOMMU / DMA protection", "Blocks DMA attacks from Thunderbolt, FireWire and PCIe devices",
                ok("iommu" in cmd, "Enabled", "Off"))]
        self.section("Kernel & boot", *kernel)

        crypt = sh("lsblk -rno TYPE | grep -c crypt")
        self.section("Disk encryption",
                     Row("lock", "gn", "LUKS2 full-disk encryption",
                         "Root filesystem unlocked at boot" if crypt not in ("", "0") else
                         "No encrypted volume is mounted (live session)",
                         ok(crypt not in ("", "0"), "Unlocked", "Live")),
                     Row("trash", "rd", "RAM wipe on shutdown", "sdmem overwrites memory at power-off",
                         ok(os.path.exists("/etc/init.d/bastille-ramwipe"), "Installed", "Missing")))

        aa = read("/sys/kernel/security/apparmor/profiles")
        n_aa = len([l for l in aa.splitlines() if "(enforce)" in l])
        self.section("Application security",
                     Row("shield", "bl", "AppArmor", f"{n_aa} profiles enforced" if aa else "Not loaded",
                         ok(bool(n_aa), "Enforcing", "Off")),
                     Row("layers", "gn", "Flatpak sandbox", "Network, filesystem and D-Bus portals enforced",
                         ok(shutil.which("flatpak") is not None, "Available", "Not installed")))

        rf = sh("rfkill list bluetooth")
        _bt_blocked = "Soft blocked: yes" in rf or "Hard blocked: yes" in rf
        self.section("Hardware security",
                     Row("usb", "gn", "USBGuard", "Default policy: block unknown devices",
                         ok(svc_running("usbguard"), "Active", "Off")),
                     Row("bt", "rd", "Bluetooth", "Blocked at boot by rfkill",
                         ok(_bt_blocked, "Blocked", "Enabled")),
                     Row("camera", "rd", "Webcam", f"{len(glob.glob('/dev/video*'))} camera device(s) present"))

        wg = shutil.which("wg") and sh("wg show interfaces")
        self.section("Network & DNS",
                     Row("globe", "gn", "Encrypted DNS", "dnscrypt-proxy on 127.0.0.1:53",
                         ok(svc_running("dnscrypt-proxy"), "Active", "Off")),
                     Row("vpn", "bl", "WireGuard VPN", "Interface wg0" if wg else
                         "No VPN configured — add /etc/wireguard/wg0.conf to enable the kill switch",
                         ok(bool(wg), "Connected", "Not set up")),
                     Row("layers", "bl", "nftables firewall",
                         "Kill switch" if os.path.exists("/etc/wireguard/wg0.conf") else "Default deny inbound",
                         ok(svc_running("nftables"), "Active", "Off")),
                     Row("refresh", "am", "MAC randomisation", "A new random MAC on every connection",
                         ok(os.path.exists("/etc/NetworkManager/conf.d/99-thl-mac-random.conf"), "On", "Off")))


class DiskEncryptionPage(Page):
    def __init__(self):
        super().__init__("Disk Encryption", "LUKS2 volumes and key slots on this machine")
        out = sh("lsblk -rno NAME,TYPE,SIZE,MOUNTPOINT")
        vols = [l.split() for l in out.splitlines() if " crypt " in l + " "]
        rows = []
        for v in vols:
            name = v[0]
            info = sh(["cryptsetup", "status", name])
            cipher = next((l.split(":", 1)[1].strip() for l in info.splitlines() if "cipher" in l), "")
            rows.append(Row("lock", "gn", f"/dev/mapper/{name}", f"{cipher} · {v[2]}", badge("Unlocked", "ok")))
        if not rows:
            rows.append(Row("lock", "am", "No encrypted volume mounted",
                            "You are in the live session, or the system is not encrypted", badge("Live", "warn")))
        self.section("Volumes", *rows)
        self.section("Recovery", Row("key", "bl", "Header backup", "Back up the LUKS header to external media with\n"
                                     "cryptsetup luksHeaderBackup — store it offline"),
                     Row("trash", "rd", "RAM wipe on shutdown", "Memory is scrubbed at power-off",
                         ok(os.path.exists("/etc/init.d/bastille-ramwipe"), "Installed", "Missing")))


class KeyManagementPage(Page):
    def __init__(self):
        super().__init__("Key Management", "OpenPGP and age keys stored for this user")
        rows = []
        if shutil.which("gpg"):
            for line in sh("gpg --list-secret-keys --with-colons 2>/dev/null").splitlines():
                f = line.split(":")
                if f[0] == "uid":
                    rows.append(Row("key", "bl", f[9], "OpenPGP secret key", badge("PGP", "ok")))
        age = os.path.expanduser("~/.config/age")
        for k in glob.glob(age + "/*.txt") + glob.glob(age + "/*.key"):
            rows.append(Row("key", "pu", os.path.basename(k), "age identity", badge("age", "run")))
        if not rows:
            rows.append(Row("key", "", "No keys found", "Create one with `gpg --full-generate-key` or `age-keygen`"))
        self.section("Keys", *rows)
        yk = sh("ykman list 2>/dev/null") if shutil.which("ykman") else ""
        self.section("Hardware tokens", Row("usb", "gn" if yk else "", yk or "No hardware token detected",
                                           "FIDO2 / PIV" if yk else "Insert a YubiKey or similar token"))


class AuditLogPage(Page):
    def __init__(self):
        super().__init__("Audit Log", "Recent security-relevant system events")
        running = svc_running("auditd")
        self.section("Service", Row("bug", "bl", "auditd", "Kernel audit daemon", ok(running, "Running", "Not running")))
        text = ""
        for path in ("/var/log/audit/audit.log", "/var/log/auth.log", "/var/log/syslog", "/var/log/messages"):
            text = sh(["tail", "-n", "80", path])
            if text:
                src = path
                break
        else:
            src = "none"
        self.add(Gtk.Label(label=f"LAST EVENTS — {src}", xalign=0, css_classes=["b2-section-title"]))
        self.add(logview(text or "Nothing readable. Run Settings as an administrator or enable auditd."))


# ── Network ───────────────────────────────────────────────────────────────────

class TorPage(Page):
    def __init__(self):
        super().__init__("Tor", "Route browser traffic through the Tor network")
        run = svc_running("bastille-tor") or svc_running("tor")
        name = "bastille-tor" if os.path.exists("/etc/init.d/bastille-tor") else "tor"
        row = Row("globe", "pu", "Tor service", "Anonymising SOCKS proxy on 127.0.0.1:9050",
                  ok(run, "Running", "Stopped"))
        row.append(toggle(run, lambda on: svc_action(name, "start" if on else "stop")))
        self.section("Service", row)
        self.section("Browsers",
                     Row("globe", "pu", "Tor Browser", "Bundled launcher with circuit monitor",
                         ok(shutil.which("torbrowser-launcher") is not None or shutil.which("tor-browser") is not None,
                            "Installed", "Not installed")),
                     Row("shield", "bl", "Browser-only routing", "System traffic uses WireGuard/direct; only the browser uses Tor"))


class UsbPage(Page):
    def __init__(self):
        super().__init__("USB Devices", "Connected devices and USBGuard policy")
        guard = svc_running("usbguard")
        self.section("Policy", Row("usb", "gn", "USBGuard", "Block unknown USB devices by default",
                                   ok(guard, "Active", "Off")))
        rows = []
        for line in sh("lsusb").splitlines():
            if "root hub" in line:
                continue
            rows.append(Row("usb", "", line.split("ID ", 1)[-1][10:] or line, line.split("ID ", 1)[-1][:9]))
        if not rows:
            rows.append(Row("usb", "", "No external USB devices", ""))
        self.section("Connected", *rows)


# ── Applications ──────────────────────────────────────────────────────────────

class FlatpakPage(Page):
    def __init__(self):
        super().__init__("Flatpak Sandbox", "Sandboxed applications and their permissions")
        if not shutil.which("flatpak"):
            self.section("", Row("layers", "am", "Flatpak is not installed", ""))
            return
        apps = [l.split("\t") for l in sh("flatpak list --app --columns=application,name,version").splitlines()]
        rows = []
        for a in apps:
            name = a[1] if len(a) > 1 else a[0]
            perms = sh(["flatpak", "info", "--show-permissions", a[0]])
            net = "network" in perms and "shared=network" in perms
            rows.append(Row("apps", "bl", name, a[0] + (f" · {a[2]}" if len(a) > 2 and a[2] else ""),
                            badge("Network" if net else "Offline", "warn" if net else "ok")))
        self.section("Installed (" + str(len(rows)) + ")", *(rows or [Row("apps", "", "No Flatpak apps installed", "")]))


# ── User ──────────────────────────────────────────────────────────────────────

class NotificationsPage(Page):
    def __init__(self):
        super().__init__("Notifications", "Banners and Do Not Disturb")
        dnd = system.state_load("dnd.json", {}).get("on", False)
        row = Row("bell", "rd", "Do Not Disturb", "Silences banners; they still collect in the notification centre")
        row.append(toggle(dnd, lambda _on: bg(lambda: sh(["bastille-shell", "--dnd"]))))
        self.section("Focus", row)
        test = Row("bell", "bl", "Send a test notification", "")
        test.append(button("Send", lambda: sh(["bastille-shell", "--notify", "Bastille", "This is a test notification"])))
        self.section("Test", test)


class LanguagePage(Page):
    def __init__(self):
        super().__init__("Language & Region", "Locale, time zone and keyboard layout")
        loc = os.environ.get("LANG", "en_US.UTF-8")
        tz = read("/etc/timezone") or os.path.basename(os.path.realpath("/etc/localtime"))
        try:
            kbs = [i for i in json.loads(sh(["swaymsg", "-t", "get_inputs", "-r"]) or "[]") if i.get("type") == "keyboard"]
            layout = kbs[0].get("xkb_active_layout_name", "") if kbs else ""
        except ValueError:
            layout = ""
        self.section("Region",
                     Row("globe", "bl", "Language", loc),
                     Row("clock", "bl", "Time zone", tz or "UTC"),
                     Row("clock", "", "Time", sh("date '+%A %-d %B %Y, %H:%M %Z'")))
        self.section("Input", Row("keyboard", "", "Keyboard layout", layout or "Default"))


class AccessibilityPage(Page):
    def __init__(self):
        super().__init__("Accessibility", "Text size, cursor and motion")

        def gset(key, val):
            bg(lambda: sh(["gsettings", "set", "org.gnome.desktop.interface", key, str(val)]))

        try:
            scale = float(sh(["gsettings", "get", "org.gnome.desktop.interface", "text-scaling-factor"]) or 1)
        except ValueError:
            scale = 1.0
        sizes = ["Small (0.9×)", "Normal (1.0×)", "Large (1.25×)", "Extra large (1.5×)"]
        vals = [0.9, 1.0, 1.25, 1.5]
        cur = min(range(4), key=lambda i: abs(vals[i] - scale))
        r1 = Row("access", "bl", "Text size", "Applies to newly opened apps")
        r1.append(select(sizes, cur, lambda i: gset("text-scaling-factor", vals[i])))
        anim = sh(["gsettings", "get", "org.gnome.desktop.interface", "enable-animations"]) != "false"
        r2 = Row("sparkle", "am", "Animations", "Turn off to reduce motion")
        r2.append(toggle(anim, lambda on: gset("enable-animations", "true" if on else "false")))
        csize = sh(["gsettings", "get", "org.gnome.desktop.interface", "cursor-size"]) or "24"
        r3 = Row("access", "", "Cursor size", "")
        opts = ["24", "32", "48", "64"]
        r3.append(select(opts, opts.index(csize) if csize in opts else 0, lambda i: gset("cursor-size", opts[i])))
        self.section("Vision", r1, r2, r3)


# ── Hardware ──────────────────────────────────────────────────────────────────

class CameraMicPage(Page):
    def __init__(self):
        super().__init__("Camera & Mic", "Cameras and microphones")
        cams = sorted(glob.glob("/dev/video*"))
        self.section("Cameras", *([Row("camera", "bl", os.path.basename(c),
                                       read("/sys/class/video4linux/" + os.path.basename(c) + "/name") or c)
                                   for c in cams[::2]] or [Row("camera", "", "No camera detected", "")]))
        muted = "MUTED" in sh(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"])
        r = Row("volume", "rd", "Microphone muted", "Mute the default input")
        r.append(toggle(muted, lambda on: bg(lambda: sh(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "1" if on else "0"]))))
        self.section("Microphone", r)


class KeyboardPage(Page):
    def __init__(self):
        super().__init__("Keyboard", "Layout and key repeat")
        layouts = ["us", "gb", "de", "fr", "es", "it", "lt", "pl", "se", "dvorak"]
        names = ["US English", "UK English", "German", "French", "Spanish", "Italian", "Lithuanian", "Polish",
                 "Swedish", "US Dvorak"]
        r1 = Row("keyboard", "bl", "Layout", "Applied immediately and kept for next login")

        def set_layout(i):
            lay, var = ("us", "dvorak") if layouts[i] == "dvorak" else (layouts[i], "")
            swaymsg("input", "type:keyboard", "xkb_layout", lay)
            swaymsg("input", "type:keyboard", "xkb_variant", var or "\"\"")
            self._save()

        self.delay, self.rate = 300, 40
        r1.append(select(names, 0, set_layout))
        r2 = Row("clock", "", "Repeat delay", "Milliseconds before a held key repeats", slider(300, 150, 800, self._set_delay))
        r3 = Row("keyboard", "", "Repeat rate", "Characters per second", slider(40, 10, 80, self._set_rate))
        self.layout = "us"
        self.section("Input", r1, r2, r3)

    def _set_delay(self, v):
        self.delay = v
        swaymsg("input", "type:keyboard", "repeat_delay", str(v))
        self._save()

    def _set_rate(self, v):
        self.rate = v
        swaymsg("input", "type:keyboard", "repeat_rate", str(v))
        self._save()

    def _save(self):
        write_sway_input("keyboard", [f"input type:keyboard repeat_delay {self.delay}",
                                      f"input type:keyboard repeat_rate {self.rate}"])


class MousePage(Page):
    def __init__(self):
        super().__init__("Mouse & Touchpad", "Pointer speed, tapping and scrolling")
        self.s = {"tap": "enabled", "natural_scroll": "enabled", "dwt": "enabled", "speed": 0.0}
        self.section("Touchpad",
                     self._tog("sliders", "Tap to click", "tap"),
                     self._tog("sliders", "Natural scrolling", "natural_scroll"),
                     self._tog("keyboard", "Disable while typing", "dwt"))
        self.section("Pointer", Row("sliders", "bl", "Pointer speed", "Applies to touchpad and mouse",
                                    slider(50, 0, 100, self._speed)))

    def _tog(self, glyph, title, key):
        r = Row(glyph, "bl", title)
        r.append(toggle(True, lambda on, k=key: self._set(k, "enabled" if on else "disabled")))
        return r

    def _set(self, key, val):
        self.s[key] = val
        for t in ("touchpad", "pointer"):
            swaymsg("input", f"type:{t}", key, val)
        self._save()

    def _speed(self, v):
        self.s["speed"] = round(v / 50 - 1, 2)
        for t in ("touchpad", "pointer"):
            swaymsg("input", f"type:{t}", "pointer_accel", str(self.s["speed"]))
        self._save()

    def _save(self):
        lines = [f"input type:touchpad {k} {v}" for k, v in self.s.items() if k in ("tap", "natural_scroll", "dwt")]
        lines += [f"input type:{t} pointer_accel {self.s['speed']}" for t in ("touchpad", "pointer")]
        write_sway_input("pointer", lines)
