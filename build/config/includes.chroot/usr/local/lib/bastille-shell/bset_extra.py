"""Richer Settings pages (Updates, Appearance, Power, Notifications, Language & Region,
Accessibility, Keyboard, Mouse & Touchpad, Sound, Display).

Everything here changes real state: sway fragments in ~/.config/bastille/*.sway (loaded by
the sway config's `include ~/.config/bastille/*.sway`), shell preferences in the Bastille
state dir, gsettings, wpctl, swaymsg, or polkit-gated helpers.
"""

import json
import os
import re
import shutil
import subprocess
import threading

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, GLib, Gtk

import bdesign as bd
import system
from bdesign import Page, Row, badge, bg, button, label, read, select, sh, slider, toggle
from bset_pages import CONFIG_DIR, logview, pk, swaymsg, write_sway_input

CFG = os.path.expanduser("~/.config")
UPDATER = "/usr/local/sbin/bastille-update"
APPS = "/usr/local/sbin/bastille-apps"


# ── persisted preferences (small JSON per page) ───────────────────────────────

def prefs_load(name, default=None):
    try:
        with open(os.path.join(CONFIG_DIR, name + ".json")) as f:
            return {**(default or {}), **json.load(f)}
    except (OSError, ValueError):
        return dict(default or {})


def prefs_save(name, data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(os.path.join(CONFIG_DIR, name + ".json"), "w") as f:
        json.dump(data, f)


def gget(schema, key, default=""):
    return sh(["gsettings", "get", schema, key]) or default


def gset(schema, key, val):
    bg(lambda: sh(["gsettings", "set", schema, key, str(val)]))


def choice(row, options, current, on_change):
    """Append a dropdown of (label, value) pairs to a row, preselecting `current`."""
    vals = [v for _l, v in options]
    row.append(select([l for l, _v in options], vals.index(current) if current in vals else 0,
                      lambda i: on_change(vals[i])))
    return row


def switch_row(glyph, tone, title, desc, active, on_change):
    r = Row(glyph, tone, title, desc)
    r.append(toggle(active, on_change))
    return r


# ── Updates: everything from inside Settings, no terminal ─────────────────────

class UpdatesPage(Page):
    def __init__(self):
        super().__init__("Bastille Updates", "Check, download and install new Bastille releases — no terminal needed")
        self.prefs = prefs_load("updates", {"auto_check": True, "update_apps": True})
        self.installed = read("/etc/bastille/version", "unknown")
        codename = read("/etc/bastille/codename", "")
        self.latest = None
        self.busy = False

        self.r_ver = Row("download", "bl", "Installed version", f"{self.installed}" + (f"  “{codename}”" if codename else ""))
        self.status = badge("Not checked", "off")
        self.r_ver.append(self.status)
        self.r_check = Row("refresh", "", "Check for updates", "Compares this system with the newest GitHub release")
        self.b_check = button("Check now", self.check)
        self.r_check.append(self.b_check)
        self.r_install = Row("download", "gn", "Install update", "Downloads, verifies the SHA256 and applies it in place")
        self.b_install = button("Install", self.install, "pri")
        self.b_install.set_sensitive(False)
        self.r_install.append(self.b_install)
        self.section("Bastille OS", self.r_ver, self.r_check, self.r_install)

        # progress area (hidden until something runs)
        self.prog_label = label("", "b2-desc", wrap=True)
        self.prog_bar = Gtk.ProgressBar()
        self.prog_bar.set_visible(False)
        self.log = Gtk.TextView()
        self.log.set_editable(False)
        self.log.set_monospace(True)
        self.log.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_sw = Gtk.ScrolledWindow()
        self.log_sw.set_min_content_height(180)
        self.log_sw.set_child(self.log)
        self.log_sw.add_css_class("b2-card")
        self.log_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.log_box.append(self.prog_label)
        self.log_box.append(self.prog_bar)
        self.log_box.append(self.log_sw)
        self.log_box.set_visible(False)
        self.add(self.log_box)

        self.restart_row = Row("power", "am", "Restart to finish", "The update is installed. Restart so every app uses it.")
        self.restart_row.append(button("Restart now", lambda: pk("/sbin/reboot"), "pri"))
        self.restart_card = bd.section("", self.restart_row)
        self.restart_card.set_visible(False)
        self.add(self.restart_card)

        auto = switch_row("clock", "", "Check automatically", "Look for a new release each time Settings opens",
                          self.prefs["auto_check"], lambda on: self._pref("auto_check", on))
        apps = switch_row("apps", "", "Also update Bastille apps",
                          "Mail, Calendar, Notes… are refreshed from the Bastille apps repository",
                          self.prefs["update_apps"], lambda on: self._pref("update_apps", on))
        self.section("Preferences", auto, apps)
        self.section("How it works",
                     Row("shield", "gn", "Verified downloads", "Every release is checked against its published SHA256 before anything changes"),
                     Row("layers", "bl", "Recovery point", "A snapshot is taken first, so a bad update can be rolled back"))
        if self.prefs["auto_check"]:
            GLib.timeout_add(600, lambda: (self.check(quiet=True), False)[1])

    def _pref(self, key, val):
        self.prefs[key] = val
        prefs_save("updates", self.prefs)

    def _show_log(self, text=None):
        self.log_box.set_visible(True)
        if text is not None:
            self.log.get_buffer().set_text(text)

    def _append(self, line):
        buf = self.log.get_buffer()
        buf.insert(buf.get_end_iter(), line + "\n")
        mark = buf.create_mark(None, buf.get_end_iter(), False)
        self.log.scroll_mark_onscreen(mark)

    def check(self, quiet=False):
        if self.busy:
            return
        self.b_check.set_sensitive(False)
        self.status.set_text("Checking…")

        def work():
            r = subprocess.run(["pkexec", UPDATER, "check"], capture_output=True, text=True, timeout=90)
            return r.returncode, ((r.stdout or "") + (r.stderr or "")).replace("bastille-update: ", "").strip()

        def done(res):
            self.b_check.set_sensitive(True)
            rc, out = res if res else (1, "Could not run the updater")
            m = re.search(r"Latest:\s*(\S+)", out) or re.search(r"(v\d+\.\d+\.\d+)\s*$", out)
            self.latest = m.group(1) if m else None
            for cls in ("ok", "warn", "off", "crit"):
                self.status.remove_css_class(cls)
            if rc == 0:
                self.status.set_text("Up to date")
                self.status.add_css_class("ok")
                self.r_install.set_desc("You already have the newest release")
                self.b_install.set_sensitive(False)
            elif rc == 2:
                self.status.set_text("Update available")
                self.status.add_css_class("warn")
                self.r_install.set_desc(f"{self.installed} → {self.latest or 'newer release'}" if self.latest else out.splitlines()[-1] if out else "")
                self.b_install.set_sensitive(True)
            else:
                self.status.set_text("Check failed")
                self.status.add_css_class("crit")
                if not quiet:
                    self._show_log(out or "No output from the updater.")

        bg(work, done)

    def install(self):
        if self.busy:
            return
        self.busy = True
        self.b_install.set_sensitive(False)
        self.b_check.set_sensitive(False)
        self.restart_card.set_visible(False)
        self._show_log("")
        self.prog_bar.set_visible(True)
        self.prog_label.set_text("Starting…")
        self.prog_bar.pulse()
        pulser = GLib.timeout_add(250, lambda: (self.prog_bar.pulse(), self.busy)[1])
        steps = [[UPDATER, "apply"]]
        if self.prefs.get("update_apps", True) and os.path.exists(APPS):
            steps.append([APPS, "update"])

        def run():
            failed = False
            for cmd in steps:
                GLib.idle_add(self._append, "$ " + " ".join(cmd))
                try:
                    p = subprocess.Popen(["pkexec", *cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    buf = b""
                    while True:
                        chunk = os.read(p.stdout.fileno(), 4096)
                        if not chunk:
                            break
                        buf += chunk
                        parts = re.split(rb"[\r\n]", buf)
                        buf = parts.pop()
                        for raw in parts:
                            self._line(raw.decode("utf-8", "replace").strip())
                    p.wait()
                    if p.returncode != 0:
                        failed = True
                        GLib.idle_add(self._append, f"(exit status {p.returncode})")
                        break
                except Exception as e:  # noqa: BLE001
                    failed = True
                    GLib.idle_add(self._append, f"Could not run: {e}")
                    break
            GLib.idle_add(self._finished, failed)

        threading.Thread(target=run, daemon=True).start()
        return pulser

    def _line(self, text):
        if not text:
            return
        text = text.replace("bastille-update: ", "")
        if "%" in text and ("#" in text or text.endswith("%")):      # curl progress bar
            m = re.search(r"(\d+(?:\.\d+)?)%", text)
            if m:
                GLib.idle_add(self._progress, float(m.group(1)) / 100, "Downloading… " + m.group(1) + "%")
            return
        GLib.idle_add(self._append, text)
        GLib.idle_add(self.prog_label.set_text, text[:120])

    def _progress(self, frac, text):
        self.prog_bar.set_fraction(frac)
        self.prog_label.set_text(text)

    def _finished(self, failed):
        self.busy = False
        self.b_check.set_sensitive(True)
        self.prog_bar.set_visible(False)
        if failed:
            self.prog_label.set_text("The update did not finish. Nothing was lost; you can try again.")
            self.b_install.set_sensitive(True)
        else:
            self.prog_label.set_text("Update installed.")
            self.restart_card.set_visible(True)
            self.status.set_text("Restart needed")
            for cls in ("ok", "warn", "off", "crit"):
                self.status.remove_css_class(cls)
            self.status.add_css_class("run")
            self.installed = read("/etc/bastille/version", self.installed)


# ── Appearance: theme, windows, wallpaper and a built-in config editor ────────

CONFIG_FILES = [
    # label, path, default source, how to apply
    ("Sway (window manager)", "~/.config/sway/config", "/etc/skel/.config/sway/config", "sway"),
    ("Terminal (foot)", "~/.config/foot/foot.ini", None, "none"),
    ("Shell style (CSS)", "~/.config/bastille/user.css", None, "shell"),
    ("Screen lock", "~/.config/swaylock/config", "/etc/skel/.config/swaylock/config", "none"),
]

USER_CSS_HELP = """/* Your own styling for the menu bar, dock and panels. Restart the shell to apply:
   Settings → Appearance → Restart shell. Example:

   .bar { background: rgba(10, 10, 14, 0.80); }
*/
"""

ACCENTS = [("Bastille Blue", "#4f8fd4"), ("Red", "#e5534b"), ("Green", "#3fb950"),
           ("Purple", "#a371f7"), ("Orange", "#f0883e"), ("Pink", "#e56fb2"), ("Graphite", "#8b949e")]


class ConfigEditor(Gtk.Box):
    """Edit a config file in place, validate (sway), save, apply, reset to the shipped default."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.idx = 0
        top = Gtk.Box(spacing=8)
        self.picker = select([c[0] for c in CONFIG_FILES], 0, self._pick)
        top.append(self.picker)
        self.path_lbl = label("", "b2-desc")
        self.path_lbl.set_hexpand(True)
        top.append(self.path_lbl)
        self.append(top)
        self.tv = Gtk.TextView()
        self.tv.set_monospace(True)
        self.tv.set_top_margin(10)
        self.tv.set_bottom_margin(10)
        self.tv.set_left_margin(12)
        self.tv.set_right_margin(12)
        self.tv.set_wrap_mode(Gtk.WrapMode.NONE)
        self.sw = Gtk.ScrolledWindow()
        self.sw.set_min_content_height(360)
        self.sw.set_child(self.tv)
        self.sw.add_css_class("b2-card")
        self.append(self.sw)
        bar = Gtk.Box(spacing=8)
        self.msg = label("", "b2-desc")
        self.msg.set_hexpand(True)
        bar.append(self.msg)
        bar.append(button("Reset to default", self.reset, "dng"))
        bar.append(button("Revert", self.load))
        bar.append(button("Save & apply", self.save, "pri"))
        self.append(bar)
        self.load()

    @property
    def spec(self):
        return CONFIG_FILES[self.idx]

    def _path(self):
        return os.path.expanduser(self.spec[1])

    def _pick(self, i):
        self.idx = i
        self.load()

    def load(self, *_):
        p = self._path()
        self.path_lbl.set_text(self.spec[1])
        try:
            with open(p) as f:
                text = f.read()
        except OSError:
            text = USER_CSS_HELP if self.spec[3] == "shell" else ""
            if self.spec[2] and os.path.exists(self.spec[2]):
                text = read(self.spec[2])
        self.tv.get_buffer().set_text(text)
        self.msg.set_text("")

    def _text(self):
        b = self.tv.get_buffer()
        return b.get_text(b.get_start_iter(), b.get_end_iter(), True)

    def save(self, *_):
        text = self._text()
        p = self._path()
        kind = self.spec[3]
        if kind == "sway":
            tmp = os.path.join(CONFIG_DIR, ".sway-check")
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(tmp, "w") as f:
                f.write(text)
            r = subprocess.run(["sway", "-C", "-c", tmp], capture_output=True, text=True)
            os.remove(tmp)
            if r.returncode != 0:
                self.msg.set_text("Not saved — sway rejects this config: " + ((r.stderr or r.stdout).strip().splitlines() or ["error"])[-1][:160])
                return
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if os.path.exists(p):
            shutil.copy2(p, p + ".bak")
        with open(p, "w") as f:
            f.write(text)
        if kind == "sway":
            swaymsg("reload")
            self.msg.set_text("Saved and reloaded. The previous version is kept as config.bak.")
        elif kind == "shell":
            self.msg.set_text("Saved. Use “Restart shell” above to apply it.")
        else:
            self.msg.set_text("Saved. Takes effect the next time the program starts.")

    def reset(self, *_):
        src = self.spec[2]
        if src and os.path.exists(src):
            self.tv.get_buffer().set_text(read(src))
            self.msg.set_text("Default loaded — press Save & apply to keep it.")
        else:
            self.tv.get_buffer().set_text(USER_CSS_HELP if self.spec[3] == "shell" else "")
            self.msg.set_text("Cleared — press Save & apply to keep it.")


class AppearancePage(Page):
    def __init__(self):
        super().__init__("Appearance", "Colours, windows, wallpaper and your own config files")
        self.p = prefs_load("appearance", {"accent": "#4f8fd4", "gaps_inner": 8, "gaps_outer": 6, "border": 1,
                                            "wallpaper": "", "font": "Inter 10"})

        # Theme
        def scheme(i):
            from gi.repository import Adw
            Adw.StyleManager.get_default().set_color_scheme(
                [Adw.ColorScheme.FORCE_DARK, Adw.ColorScheme.FORCE_LIGHT, Adw.ColorScheme.DEFAULT][i])
            gset("org.gnome.desktop.interface", "color-scheme", ["'prefer-dark'", "'prefer-light'", "'default'"][i])

        r1 = Row("moon", "pu", "Colour scheme", "Dark is the Bastille look; Light and System apply to apps that support them")
        r1.append(select(["Dark", "Light", "System"], 0, scheme))
        r2 = Row("sparkle", "bl", "Accent colour", "Window borders and highlights")
        cur = next((i for i, a in enumerate(ACCENTS) if a[1] == self.p["accent"]), 0)
        r2.append(select([a[0] for a in ACCENTS], cur, self._accent))
        fonts = ["Inter 10", "Inter 11", "IBM Plex Sans 10", "IBM Plex Sans 11", "Noto Sans 10", "DejaVu Sans 10", "Cantarell 11"]
        r3 = Row("edit", "", "Interface font", "Used by window titles and GTK apps")
        r3.append(select(fonts, fonts.index(self.p["font"]) if self.p["font"] in fonts else 0, self._font(fonts)))
        mono = ["Monospace 11", "DejaVu Sans Mono 11", "IBM Plex Mono 11", "Noto Sans Mono 11"]
        r4 = Row("term", "", "Monospace font", "Terminal and code editors")
        r4.append(select(mono, 0, lambda i: gset("org.gnome.desktop.interface", "monospace-font-name", f"'{mono[i]}'")))
        self.section("Theme", r1, r2, r3, r4)

        # Windows
        g1 = Row("layers", "", "Gap between windows", "Pixels", slider(self.p["gaps_inner"], 0, 32, lambda v: self._win("gaps_inner", v)))
        g2 = Row("layers", "", "Gap to screen edge", "Pixels", slider(self.p["gaps_outer"], 0, 32, lambda v: self._win("gaps_outer", v)))
        g3 = Row("display", "", "Border thickness", "Pixels", slider(self.p["border"], 0, 6, lambda v: self._win("border", v)))
        self.section("Windows", g1, g2, g3,
                     switch_row("grid", "", "Hide borders when a window is alone", "Smart borders and gaps",
                                self.p.get("smart", True), lambda on: self._win("smart", on)))

        # Wallpaper
        walls = sorted(set(sum([[os.path.join(d, f) for f in os.listdir(d)
                                 if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
                                for d in ("/usr/share/backgrounds/bastille", os.path.expanduser("~/Pictures"),
                                          os.path.expanduser("~/.local/share/backgrounds")) if os.path.isdir(d)], [])))
        self.walls = walls
        r5 = Row("display", "bl", "Wallpaper", self.p["wallpaper"] or "Bastille default")
        self.wall_row = r5
        if walls:
            names = [os.path.basename(w) for w in walls]
            r5.append(select(names, walls.index(self.p["wallpaper"]) if self.p["wallpaper"] in walls else 0,
                             lambda i: self._wall(walls[i])))
        r5.append(button("Choose file…", self._choose_wall))
        self.section("Wallpaper", r5)

        # Shell
        restart = Row("refresh", "", "Restart shell", "Reloads the menu bar and dock (needed after editing the shell style)")
        restart.append(button("Restart", lambda: bg(lambda: sh("pkill -x bastille-shell; sleep 0.5; setsid bastille-shell >/dev/null 2>&1 &"))))
        self.section("Shell", restart)

        # Config editor
        ed_title = label("CONFIG FILES", "b2-section-title")
        self.add(ed_title)
        self.add(label("Edit your window manager, terminal and shell by hand. Saving checks the sway config first, "
                       "keeps a .bak copy and reloads it live.", "b2-desc", wrap=True))
        self.add(ConfigEditor())

    # apply helpers -----------------------------------------------------------
    def _save_fragment(self):
        p = self.p
        lines = [f"gaps inner {p['gaps_inner']}", f"gaps outer {p['gaps_outer']}",
                 f"default_border pixel {p['border']}", f"default_floating_border pixel {p['border']}",
                 f"smart_gaps {'on' if p.get('smart', True) else 'off'}",
                 f"smart_borders {'on' if p.get('smart', True) else 'off'}",
                 f"font pango:{p['font']}"]
        a = p["accent"]
        lines += [f"client.focused {a} #161b22 #c9d1d9 {a} {a}"]
        if p["wallpaper"]:
            lines.append(f"output * bg \"{p['wallpaper']}\" fill")
        write_sway_input("appearance", lines)
        prefs_save("appearance", p)
        swaymsg("reload")

    def _accent(self, i):
        self.p["accent"] = ACCENTS[i][1]
        self._save_fragment()

    def _font(self, fonts):
        def cb(i):
            self.p["font"] = fonts[i]
            gset("org.gnome.desktop.interface", "font-name", f"'{fonts[i]}'")
            self._save_fragment()
        return cb

    def _win(self, key, val):
        self.p[key] = val
        self._debounce()

    def _debounce(self):
        if getattr(self, "_t", None):
            GLib.source_remove(self._t)
        self._t = GLib.timeout_add(350, lambda: (self._save_fragment(), setattr(self, "_t", None), False)[2])

    def _wall(self, path):
        self.p["wallpaper"] = path
        self.wall_row.set_desc(path)
        self._save_fragment()

    def _choose_wall(self):
        dlg = Gtk.FileDialog()
        f = Gtk.FileFilter()
        f.set_name("Images")
        f.add_mime_type("image/jpeg")
        f.add_mime_type("image/png")
        f.add_mime_type("image/webp")
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(f)
        dlg.set_filters(store)

        def done(d, res):
            try:
                gf = d.open_finish(res)
            except GLib.Error:
                return
            if gf:
                self._wall(gf.get_path())
        dlg.open(self.get_root(), None, done)


# ── Power ─────────────────────────────────────────────────────────────────────

LOCK_OPTS = [("1 minute", 60), ("2 minutes", 120), ("3 minutes", 180), ("5 minutes", 300), ("10 minutes", 600),
             ("15 minutes", 900), ("30 minutes", 1800), ("Never", 0)]
OFF_OPTS = [("2 minutes", 120), ("5 minutes", 300), ("10 minutes", 600), ("15 minutes", 900),
            ("30 minutes", 1800), ("Never", 0)]
LID_OPTS = [("Lock the screen", "lock"), ("Lock and turn the screen off", "off"), ("Do nothing", "none")]


class PowerPage(Page):
    def __init__(self):
        super().__init__("Power", "Battery, sleep, screen lock and performance mode")
        self.p = prefs_load("power", {"lock": 180, "off": 600, "lid": "lock"})
        bat = system.battery()
        rows = []
        if bat:
            state = "Charging" if bat[1] else "On battery"
            rows.append(Row("cpu", "gn" if bat[1] else "am", f"Battery {bat[0]}%", state,
                            badge("Charging" if bat[1] else "Discharging", "ok" if bat[1] else "warn")))
            import glob
            for b in glob.glob("/sys/class/power_supply/BAT0"):
                cycles = read(b + "/cycle_count")
                full = read(b + "/energy_full") or read(b + "/charge_full")
                design = read(b + "/energy_full_design") or read(b + "/charge_full_design")
                if full.isdigit() and design.isdigit() and int(design):
                    rows.append(Row("info", "", "Battery health", f"{100 * int(full) // int(design)}% of design capacity"
                                    + (f" · {cycles} cycles" if cycles else "")))
                tech = read(b + "/technology")
                if tech:
                    rows.append(Row("info", "", "Battery type", tech))
        else:
            rows.append(Row("power", "", "Power source", "AC power — no battery detected"))
        self.section("Battery", *rows)

        disp = []
        br = system.brightness()
        if br is not None:
            disp.append(Row("sparkle", "am", "Brightness", "", slider(br, 1, 100, system.set_brightness)))
        disp.append(choice(Row("clock", "bl", "Lock screen after", "Idle time before the Bastille keyguard locks"),
                           LOCK_OPTS, self.p["lock"], lambda v: self._set("lock", v)))
        disp.append(choice(Row("display", "", "Turn screen off after", "Display power-off while idle"),
                           OFF_OPTS, self.p["off"], lambda v: self._set("off", v)))
        disp.append(choice(Row("power", "bl", "When the lid is closed", ""),
                           LID_OPTS, self.p["lid"], lambda v: self._set("lid", v)))
        self.section("Screen & sleep", *disp)

        if shutil.which("powerprofilesctl"):
            cur = sh(["powerprofilesctl", "get"]) or "balanced"
            profiles = [("Power saver", "power-saver"), ("Balanced", "balanced"), ("Performance", "performance")]
            self.section("Performance mode",
                         choice(Row("cpu", "bl", "Power profile", "Trade speed against battery life"), profiles, cur,
                                lambda v: bg(lambda: sh(["powerprofilesctl", "set", v]))))
        row = Row("power", "rd", "Power off or restart", "")
        row.append(button("Restart", lambda: pk("/sbin/reboot")))
        row.append(button("Power off", lambda: pk("/sbin/poweroff"), "dng"))
        self.section("System", row)

    def _set(self, key, val):
        self.p[key] = val
        prefs_save("power", self.p)
        lock, off = self.p["lock"], self.p["off"]
        parts = ["swayidle", "-w"]
        if lock:
            parts += ["timeout", str(lock), "'/usr/local/sbin/bastille-lock'"]
        if off:
            parts += ["timeout", str(off), "\"swaymsg 'output * power off'\"", "resume", "\"swaymsg 'output * power on'\""]
        parts += ["before-sleep", "'/usr/local/sbin/bastille-lock'"]
        lines = ["exec_always --no-startup-id sh -c \"pkill -x swayidle; exec " + " ".join(parts).replace('"', '\\"') + "\""]
        lid = self.p["lid"]
        if lid == "lock":
            lines.append("bindswitch lid:on exec /usr/local/sbin/bastille-lock")
        elif lid == "off":
            lines.append("bindswitch lid:on exec sh -c \"/usr/local/sbin/bastille-lock; swaymsg 'output * power off'\"")
            lines.append("bindswitch lid:off exec swaymsg 'output * power on'")
        write_sway_input("power", lines)
        swaymsg("reload")


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationsPage(Page):
    def __init__(self):
        super().__init__("Notifications", "Banners, Do Not Disturb and sounds")
        self.n = system.state_load("notify.json", {"duration": 6, "sound": False})
        dnd = system.state_load("dnd.json", {}).get("on", False)
        self.section("Focus", switch_row("bell", "rd", "Do Not Disturb",
                                         "Silences banners; they still collect in the notification centre", dnd,
                                         lambda _on: bg(lambda: sh(["bastille-shell", "--dnd"]))))
        dur = [("3 seconds", 3), ("6 seconds", 6), ("10 seconds", 10), ("20 seconds", 20), ("1 minute", 60)]
        self.section("Banners",
                     choice(Row("bell", "bl", "Show banners for", "How long a notification stays on screen"),
                            dur, int(self.n.get("duration", 6)), lambda v: self._set("duration", v)),
                     switch_row("speaker", "", "Play a sound", "A short chime when a notification arrives",
                                bool(self.n.get("sound")), lambda on: self._set("sound", on)))
        test = Row("bell", "bl", "Send a test notification", "Check how banners look and sound")
        test.append(button("Send", lambda: sh(["bastille-shell", "--notify", "Bastille", "This is a test notification"])))
        clear = Row("trash", "", "Clear notification history", "Removes everything from the notification centre")
        clear.append(button("Clear", lambda: sh(["bastille-shell", "--notifications"]) and None))
        self.section("Try it", test)

    def _set(self, key, val):
        self.n[key] = val
        system.state_save("notify.json", self.n)


# ── Language & Region ─────────────────────────────────────────────────────────

class LanguagePage(Page):
    def __init__(self):
        super().__init__("Language & Region", "Locale, time, clock and calendar format")
        self.c = system.state_load("clock.json", {"h24": True, "seconds": False, "weekday": True, "day_first": True})
        loc = os.environ.get("LANG", "en_US.UTF-8")
        tz = read("/etc/timezone") or os.path.basename(os.path.realpath("/etc/localtime"))
        self.section("Region",
                     Row("globe", "bl", "Language", loc),
                     Row("clock", "bl", "Time zone", tz or "UTC"),
                     Row("clock", "", "Time now", sh("date '+%A %-d %B %Y, %H:%M %Z'")))
        self.section("Menu bar clock",
                     switch_row("clock", "", "24-hour time", "Off shows 1:30 PM style", self.c.get("h24", True),
                                lambda on: self._set("h24", on)),
                     switch_row("clock", "", "Show seconds", "", self.c.get("seconds", False),
                                lambda on: self._set("seconds", on)),
                     switch_row("cal", "", "Show the weekday", "Mon 15 Nov", self.c.get("weekday", True),
                                lambda on: self._set("weekday", on)),
                     switch_row("cal", "", "Day before month", "15 Nov instead of Nov 15", self.c.get("day_first", True),
                                lambda on: self._set("day_first", on)))
        units = [("Metric (km, °C)", "metric"), ("Imperial (mi, °F)", "imperial")]
        wk = [("Monday", "mon"), ("Sunday", "sun"), ("Saturday", "sat")]
        self.section("Formats",
                     choice(Row("globe", "", "Measurement units", "Used by Weather and Maps"), units,
                            self.c.get("units", "metric"), lambda v: self._set("units", v)),
                     choice(Row("cal", "", "Week starts on", "Used by Calendar"), wk,
                            self.c.get("week", "mon"), lambda v: self._set("week", v)))

    def _set(self, key, val):
        self.c[key] = val
        system.state_save("clock.json", self.c)


# ── Accessibility ─────────────────────────────────────────────────────────────

class AccessibilityPage(Page):
    def __init__(self):
        super().__init__("Accessibility", "Vision, pointer and motion")
        self.a = prefs_load("access", {"cursor_theme": "Adwaita", "cursor_size": 24})
        I = "org.gnome.desktop.interface"
        try:
            scale = float(gget(I, "text-scaling-factor", "1"))
        except ValueError:
            scale = 1.0
        vals = [0.9, 1.0, 1.25, 1.5, 2.0]
        sizes = [("Small (0.9×)", 0.9), ("Normal (1.0×)", 1.0), ("Large (1.25×)", 1.25),
                 ("Extra large (1.5×)", 1.5), ("Huge (2×)", 2.0)]
        cur = min(vals, key=lambda v: abs(v - scale))
        vision = [
            choice(Row("access", "bl", "Text size", "Applies to newly opened apps"), sizes, cur,
                   lambda v: gset(I, "text-scaling-factor", v)),
            switch_row("sparkle", "am", "Reduce motion", "Turns off animations", gget(I, "enable-animations", "true") == "false",
                       lambda on: gset(I, "enable-animations", "false" if on else "true")),
            switch_row("display", "", "High contrast", "Stronger borders and text colours",
                       gget("org.gnome.desktop.a11y.interface", "high-contrast", "false") == "true",
                       lambda on: gset("org.gnome.desktop.a11y.interface", "high-contrast", "true" if on else "false")),
            switch_row("info", "", "Underline links and use bold labels", "Easier to spot controls",
                       False, lambda on: gset(I, "toolkit-accessibility", "true" if on else "false")),
        ]
        self.section("Vision", *vision)
        cs = [("Normal (24)", 24), ("Large (32)", 32), ("Larger (48)", 48), ("Huge (64)", 64)]
        themes = ["Adwaita", "default"]
        self.section("Pointer",
                     choice(Row("access", "", "Cursor size", "Applies to the desktop and new apps"), cs,
                            int(self.a.get("cursor_size", 24)), self._cursor),
                     switch_row("access", "", "Locate pointer with a ring", "Shake or press Ctrl to find the pointer (when supported)",
                                False, lambda on: None))
        orca = shutil.which("orca")
        sr = Row("speaker", "pu", "Screen reader (Orca)", "Reads the interface aloud" if orca else "Not installed on this system")
        if orca:
            sr.append(toggle(bool(sh(["pgrep", "-x", "orca"])),
                             lambda on: bg(lambda: sh("orca --replace >/dev/null 2>&1 &" if on else "pkill -x orca"))))
        else:
            sr.append(badge("Unavailable", "off"))
        self.section("Hearing & speech", sr)

    def _cursor(self, v):
        self.a["cursor_size"] = v
        prefs_save("access", self.a)
        gset("org.gnome.desktop.interface", "cursor-size", v)
        write_sway_input("cursor", [f"seat * xcursor_theme {self.a['cursor_theme']} {v}"])
        swaymsg("seat", "*", "xcursor_theme", self.a["cursor_theme"], str(v))


# ── Keyboard ──────────────────────────────────────────────────────────────────

LAYOUTS = [("US English", "us", ""), ("UK English", "gb", ""), ("German", "de", ""), ("French", "fr", ""),
           ("Spanish", "es", ""), ("Italian", "it", ""), ("Lithuanian", "lt", ""), ("Polish", "pl", ""),
           ("Swedish", "se", ""), ("Norwegian", "no", ""), ("Danish", "dk", ""), ("Finnish", "fi", ""),
           ("Czech", "cz", ""), ("Dutch", "nl", ""), ("Portuguese", "pt", ""), ("Russian", "ru", ""),
           ("Ukrainian", "ua", ""), ("US Dvorak", "us", "dvorak"), ("US Colemak", "us", "colemak")]


class KeyboardPage(Page):
    def __init__(self):
        super().__init__("Keyboard", "Layouts, repeat rate and special keys")
        self.k = prefs_load("keyboard", {"l1": 0, "l2": -1, "delay": 300, "rate": 40, "caps": "", "compose": "",
                                          "numlock": "disabled", "switch": "grp:alt_shift_toggle"})
        names = [l[0] for l in LAYOUTS]
        second = ["None"] + names
        self.section("Layouts",
                     choice(Row("keyboard", "bl", "Primary layout", "Applied immediately and kept for next login"),
                            [(n, i) for i, n in enumerate(names)], self.k["l1"], lambda v: self._set("l1", v)),
                     choice(Row("keyboard", "", "Second layout", "Switch between them with the shortcut below"),
                            [(n, i - 1) for i, n in enumerate(second)], self.k["l2"], lambda v: self._set("l2", v)),
                     choice(Row("keyboard", "", "Switch layouts with", ""),
                            [("Alt + Shift", "grp:alt_shift_toggle"), ("Super + Space", "grp:win_space_toggle"),
                             ("Ctrl + Shift", "grp:ctrl_shift_toggle"), ("Caps Lock", "grp:caps_toggle")],
                            self.k["switch"], lambda v: self._set("switch", v)))
        self.section("Typing",
                     Row("clock", "", "Repeat delay", "Milliseconds before a held key repeats",
                         slider(self.k["delay"], 150, 800, lambda v: self._set("delay", v))),
                     Row("keyboard", "", "Repeat rate", "Characters per second",
                         slider(self.k["rate"], 10, 80, lambda v: self._set("rate", v))))
        self.section("Special keys",
                     choice(Row("keyboard", "bl", "Caps Lock key acts as", ""),
                            [("Caps Lock", ""), ("Escape", "caps:escape"), ("Control", "ctrl:nocaps"),
                             ("Disabled", "caps:none")], self.k["caps"], lambda v: self._set("caps", v)),
                     choice(Row("keyboard", "", "Compose key", "Type é ñ ü with a key sequence"),
                            [("None", ""), ("Right Alt", "compose:ralt"), ("Menu key", "compose:menu"),
                             ("Caps Lock", "compose:caps")], self.k["compose"], lambda v: self._set("compose", v)),
                     choice(Row("keyboard", "", "Num Lock at login", "Off is safer on laptops with an embedded keypad"),
                            [("Off", "disabled"), ("On", "enabled")], self.k["numlock"], lambda v: self._set("numlock", v)))

    def _set(self, key, val):
        self.k[key] = val
        if getattr(self, "_t", None):
            GLib.source_remove(self._t)
        self._t = GLib.timeout_add(300, self._apply)

    def _apply(self):
        self._t = None
        k = self.k
        a = LAYOUTS[k["l1"]]
        lays, vars_ = [a[1]], [a[2]]
        if k["l2"] >= 0:
            b = LAYOUTS[k["l2"]]
            lays.append(b[1])
            vars_.append(b[2])
        opts = ",".join(o for o in (k["switch"] if len(lays) > 1 else "", k["caps"], k["compose"]) if o)
        lines = [f"input type:keyboard xkb_layout {','.join(lays)}",
                 f"input type:keyboard xkb_variant \"{','.join(vars_)}\"",
                 f"input type:keyboard xkb_options \"{opts}\"",
                 f"input type:keyboard xkb_numlock {k['numlock']}",
                 f"input type:keyboard repeat_delay {k['delay']}",
                 f"input type:keyboard repeat_rate {k['rate']}"]
        prefs_save("keyboard", k)
        write_sway_input("keyboard", lines)
        for ln in lines:
            swaymsg(*ln.replace('"', "").split())
        swaymsg("input", "type:keyboard", "xkb_variant", ",".join(vars_) if any(vars_) else '""')
        return False


# ── Mouse & Touchpad ──────────────────────────────────────────────────────────

class MousePage(Page):
    def __init__(self):
        super().__init__("Mouse & Touchpad", "Pointer speed, tapping, scrolling and buttons")
        self.s = prefs_load("pointer", {"tap": "enabled", "natural_scroll": "enabled", "dwt": "enabled",
                                         "speed": 0.0, "scroll_factor": 1.0, "accel_profile": "adaptive",
                                         "left_handed": "disabled", "click_method": "clickfinger",
                                         "middle_emulation": "disabled", "tap_button_map": "lrm",
                                         "events": "enabled"})
        S = self.s
        self.section("Touchpad",
                     self._tog("Tap to click", "tap", "Tap with one, two and three fingers"),
                     self._tog("Natural scrolling", "natural_scroll", "Content follows your fingers"),
                     self._tog("Disable while typing", "dwt", "Avoids accidental palm touches"),
                     choice(Row("sliders", "", "Click method", "How the touchpad decides left or right click"),
                            [("By finger count", "clickfinger"), ("Button areas", "button_areas")],
                            S["click_method"], lambda v: self._set("click_method", v, "touchpad")),
                     choice(Row("sliders", "", "Tap buttons", "Which click a 2- and 3-finger tap gives"),
                            [("Left · Right · Middle", "lrm"), ("Left · Middle · Right", "lmr")],
                            S["tap_button_map"], lambda v: self._set("tap_button_map", v, "touchpad")),
                     choice(Row("sliders", "", "Touchpad when a mouse is plugged in", ""),
                            [("Keep on", "enabled"), ("Turn off", "disabled_on_external_mouse")],
                            S["events"], lambda v: self._set("events", v, "touchpad")))
        self.section("Pointer",
                     Row("sliders", "bl", "Pointer speed", "Applies to touchpad and mouse",
                         slider(int((S["speed"] + 1) * 50), 0, 100, self._speed)),
                     Row("sliders", "", "Scroll speed", "1× is normal",
                         slider(int(S["scroll_factor"] * 10), 3, 40, lambda v: self._set("scroll_factor", v / 10))),
                     choice(Row("sliders", "", "Acceleration", "Adaptive speeds up fast movements; Flat keeps them 1:1"),
                            [("Adaptive", "adaptive"), ("Flat", "flat")], S["accel_profile"],
                            lambda v: self._set("accel_profile", v)),
                     self._tog("Left-handed buttons", "left_handed", "Swap the primary and secondary buttons"),
                     self._tog("Emulate a middle click", "middle_emulation", "Press both buttons together"))

    def _tog(self, title, key, desc=""):
        r = Row("sliders", "bl", title, desc)
        r.append(toggle(self.s[key] == "enabled", lambda on, k=key: self._set(k, "enabled" if on else "disabled")))
        return r

    def _speed(self, v):
        self._set("speed", round(v / 50 - 1, 2))

    def _set(self, key, val, only=None):
        self.s[key] = val
        prefs_save("pointer", self.s)
        lines = []
        for t in ("touchpad", "pointer"):
            for k, v in self.s.items():
                if k == "speed":
                    lines.append(f"input type:{t} pointer_accel {v}")
                elif k in ("tap", "dwt", "tap_button_map", "click_method", "events") and t != "touchpad":
                    continue
                else:
                    lines.append(f"input type:{t} {k} {v}")
        write_sway_input("pointer", lines)
        for ln in lines:
            swaymsg(*ln.split())


# ── Sound ─────────────────────────────────────────────────────────────────────

def wp_devices(section):
    """[(id, name, is_default)] for 'Sinks' or 'Sources' from `wpctl status`."""
    grab, res = False, []
    for line in sh(["wpctl", "status"]).splitlines():
        clean = re.sub(r"^[\s\u2502\u251c\u2514\u2500\-|`]+", "", line)
        if clean.rstrip() == section + ":":
            grab = True
            continue
        if not grab:
            continue
        m = re.match(r"^[\s\u2502|]*(\*?)\s*(\d+)\.\s+(.+?)\s*(?:\[vol|$)", line)
        if m:
            res.append((int(m.group(2)), m.group(3).strip(), bool(m.group(1))))
        elif clean.endswith(":"):
            break
    return res


class SoundPage(Page):
    def __init__(self):
        super().__init__("Sound", "Output, input and volume")
        v, muted = system.volume()
        sinks, sources = wp_devices("Sinks"), wp_devices("Sources")
        out = [Row("speaker", "bl", "Output volume", "", slider(v, 0, 100, system.set_volume)),
               switch_row("speaker", "", "Mute output", "Silence the default output", muted, lambda on: system.toggle_mute())]
        if sinks:
            out.insert(0, choice(Row("speaker", "bl", "Output device", "Speakers, headphones, HDMI…"),
                                 [(n, i) for i, n, _d in sinks], next((i for i, _n, d in sinks if d), sinks[0][0]),
                                 lambda i: bg(lambda: sh(["wpctl", "set-default", str(i)]))))
        self.section("Output", *out)
        inp = [Row("camera", "", "Input volume", "",
                   slider(self._vol("@DEFAULT_AUDIO_SOURCE@"), 0, 100,
                          lambda p: bg(lambda: sh(["wpctl", "set-volume", "@DEFAULT_AUDIO_SOURCE@", f"{p / 100:.2f}"])))),
               switch_row("camera", "rd", "Mute microphone", "Mute the default input",
                          "MUTED" in sh(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"]),
                          lambda on: bg(lambda: sh(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "1" if on else "0"])))]
        if sources:
            inp.insert(0, choice(Row("camera", "", "Input device", "Built-in or external microphone"),
                                 [(n, i) for i, n, _d in sources], next((i for i, _n, d in sources if d), sources[0][0]),
                                 lambda i: bg(lambda: sh(["wpctl", "set-default", str(i)]))))
        self.section("Input", *inp)
        test = Row("speaker", "", "Play a test sound", "")
        test.append(button("Play", lambda: bg(lambda: sh("paplay /usr/share/sounds/freedesktop/stereo/bell.oga || speaker-test -t sine -l 1 -c 2"))))
        self.section("Test", test)

    @staticmethod
    def _vol(target):
        m = re.search(r"([\d.]+)", sh(["wpctl", "get-volume", target]))
        return int(float(m.group(1)) * 100) if m else 50


# ── Display ───────────────────────────────────────────────────────────────────

class DisplayPage(Page):
    def __init__(self):
        super().__init__("Display", "Resolution, scale, rotation and night light")
        self.d = prefs_load("display", {})
        try:
            outs = json.loads(sh(["swaymsg", "-t", "get_outputs", "-r"]) or "[]")
        except ValueError:
            outs = []
        if not outs:
            self.section("", Row("display", "am", "No display information", "Settings must run inside the Bastille desktop"))
        for o in outs:
            name = o.get("name", "?")
            cur = o.get("current_mode") or {}
            modes = sorted({(m["width"], m["height"], round(m["refresh"] / 1000)) for m in o.get("modes", [])},
                           key=lambda m: (-m[0] * m[1], -m[2]))[:14]
            labels = [f"{w}×{h} @ {r} Hz" for w, h, r in modes]
            cur_i = next((i for i, m in enumerate(modes) if m[0] == cur.get("width") and m[1] == cur.get("height")
                          and m[2] == round(cur.get("refresh", 0) / 1000)), 0)
            rows = []
            if modes:
                rows.append(choice(Row("display", "bl", "Resolution & refresh rate", f"{o.get('make', '')} {o.get('model', '')}".strip()),
                                   [(l, i) for i, l in enumerate(labels)], cur_i,
                                   lambda i, n=name, ms=modes: self._mode(n, ms[i])))
            scales = [("100%", 1.0), ("125%", 1.25), ("150%", 1.5), ("175%", 1.75), ("200%", 2.0)]
            cs = o.get("scale", 1.0)
            rows.append(choice(Row("display", "", "Scale", "Make everything larger or smaller"), scales,
                               min((s for _l, s in scales), key=lambda s: abs(s - cs)),
                               lambda v, n=name: self._set(n, "scale", v)))
            rows.append(choice(Row("display", "", "Rotation", ""),
                               [("Normal", "normal"), ("90°", "90"), ("180°", "180"), ("270°", "270")],
                               o.get("transform", "normal"), lambda v, n=name: self._set(n, "transform", v)))
            self.section(name, *rows)
        if shutil.which("wlsunset"):
            self.n = prefs_load("night", {"on": False, "temp": 4000})
            self.section("Night light",
                         switch_row("sparkle", "am", "Warmer colours in the evening", "Reduces blue light after sunset",
                                    self.n["on"], lambda on: self._night("on", on)),
                         choice(Row("sparkle", "", "Warmth", ""),
                                [("Slightly warm", 5000), ("Warm", 4000), ("Very warm", 3000)], self.n["temp"],
                                lambda v: self._night("temp", v)))
        else:
            self.section("Night light", Row("sparkle", "am", "Night light", "Available in the next system image (needs wlsunset)",
                                            badge("Soon", "off")))

    def _set(self, name, key, val):
        self.d.setdefault(name, {})[key] = val
        self._save()

    def _mode(self, name, m):
        self.d.setdefault(name, {})["mode"] = f"{m[0]}x{m[1]}@{m[2]}Hz"
        self._save()

    def _save(self):
        lines = []
        for name, v in self.d.items():
            parts = [f"output {name}"]
            if "mode" in v:
                parts.append(f"mode {v['mode']}")
            if "scale" in v:
                parts.append(f"scale {v['scale']}")
            if "transform" in v:
                parts.append(f"transform {v['transform']}")
            lines.append(" ".join(parts))
        prefs_save("display", self.d)
        write_sway_input("display", lines)
        for ln in lines:
            swaymsg(*ln.split())

    def _night(self, key, val):
        self.n[key] = val
        prefs_save("night", self.n)
        sh("pkill -x wlsunset")
        lines = []
        if self.n["on"]:
            cmd = f"wlsunset -t {self.n['temp']} -T 6500 -S 07:00 -s 19:30"
            lines = [f"exec_always --no-startup-id sh -c \"pkill -x wlsunset; exec {cmd}\""]
            bg(lambda: sh(f"setsid {cmd} >/dev/null 2>&1 &"))
        write_sway_input("night", lines or ["# night light off"])
