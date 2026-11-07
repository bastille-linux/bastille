"""Spotlight-style launcher: search, apps (Super+1), files (Super+2), clipboard, actions."""

import os
import re
import subprocess

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gdk, Gio, GLib, Gtk, Gtk4LayerShell as LS

import icons
import system
from ui import Overlay

HOME = os.path.expanduser("~")
MODES = [("search", "search", "Search"), ("apps", "apps", "Applications"), ("files", "folder", "Files"),
         ("clipboard", "copy", "Clipboard"), ("actions", "power", "Actions")]


def kind_for(info):
    did = (info.get_id() or "").replace(".desktop", "")
    base = did.replace("bastille-", "")
    return base if did.startswith("bastille-") and base in icons.TILES else None


def app_icon(info, size=34):
    k = kind_for(info)
    if k:
        return icons.tile(k, size)
    gi_ = info.get_icon()
    if gi_ is not None:
        # only use the themed icon if the theme actually has it, otherwise we would show a blank/broken image
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        names = gi_.get_names() if isinstance(gi_, Gio.ThemedIcon) else None
        if names is None or any(theme.has_icon(n) for n in names):
            img = Gtk.Image.new_from_gicon(gi_)
            img.set_pixel_size(size)
            return img
    return icons.tile("generic", size)


def calc(q):
    if not re.fullmatch(r"[0-9+\-*/().%^ ]+", q) or not re.search(r"[+\-*/%^]", q):
        return None
    try:
        v = eval(q.replace("^", "**"), {"__builtins__": {}}, {})  # noqa: S307 (charset-restricted)
        return str(round(v, 10)).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)
    except Exception:  # noqa: BLE001
        return None


class Launcher:
    def __init__(self, app, shell):
        self.shell = shell
        self.mode = "search"
        self.rows = []
        self.sel = 0
        self.apps = []
        self._deb = 0

        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)

        top = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        pill = Gtk.Box(spacing=12, valign=Gtk.Align.CENTER)
        pill.add_css_class("spot")
        pill.set_size_request(560, 64)
        pill.append(icons.icon("search", "#f4f6f5", 24, 2.0))
        self.entry = Gtk.Entry(hexpand=True, placeholder_text="Spotlight Search", has_frame=False)
        self.entry.connect("changed", lambda *_: self.refresh_soon())
        self.entry.connect("activate", lambda *_: self.activate())
        pill.append(self.entry)
        top.append(pill)
        self.mode_btns = {}
        for key, glyph, tip in MODES[1:]:
            b = Gtk.Button()
            b.add_css_class("circlebtn")
            b.set_child(icons.icon(glyph, "#f4f6f5", 24, 1.9))
            b.set_tooltip_text(tip)
            b.set_valign(Gtk.Align.CENTER)
            b.connect("clicked", lambda _b, k=key: self.set_mode(k))
            self.mode_btns[key] = b
            top.append(b)
        col.append(top)

        self.results_wrap = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, propagate_natural_height=True,
                                               max_content_height=470)
        self.results_wrap.add_css_class("results")
        self.results_wrap.set_size_request(560, -1)
        self.results_wrap.set_halign(Gtk.Align.CENTER)
        self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.results_wrap.set_child(self.results)
        col.append(self.results_wrap)

        self.ov = Overlay(app, col, Gtk.Align.CENTER, Gtk.Align.START, (150, 0, 0, 0))
        self.win = self.ov.win
        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self.on_key)
        self.win.add_controller(keys)

    # ── show / hide ───────────────────────────────────────────────────────────
    def visible(self):
        return self.ov.visible()

    def show(self, mode="search"):
        self.entry.set_text("")
        self.apps = system.all_apps()
        self.ov.show()
        self.set_mode(mode)
        self.entry.grab_focus()

    def hide(self):
        self.ov.hide()

    def set_mode(self, mode):
        self.mode = mode
        for k, b in self.mode_btns.items():
            (b.add_css_class if k == mode else b.remove_css_class)("sel")
        self.entry.set_placeholder_text({"search": "Spotlight Search", "apps": "Search applications",
                                         "files": "Search files", "clipboard": "Search clipboard",
                                         "actions": "Actions"}[mode])
        self.refresh()
        self.entry.grab_focus()

    def refresh_soon(self):
        """Debounce typing: the file search shells out to find."""
        if self._deb:
            GLib.source_remove(self._deb)
        self._deb = GLib.timeout_add(90, self._refresh_now)

    def _refresh_now(self):
        self._deb = 0
        self.refresh()
        return False

    # ── keys ─────────────────────────────────────────────────────────────────
    def on_key(self, _c, keyval, _code, state):
        if keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        if self._deb and keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            GLib.source_remove(self._deb)
            self._refresh_now()
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Tab) or (ctrl and keyval == Gdk.KEY_n):
            self.move(1)
            return True
        if keyval in (Gdk.KEY_Up, Gdk.KEY_ISO_Left_Tab) or (ctrl and keyval == Gdk.KEY_p):
            self.move(-1)
            return True
        return False

    def move(self, d):
        if not self.rows:
            return
        self.sel = (self.sel + d) % len(self.rows)
        self.mark()

    def mark(self):
        for i, (w, _a) in enumerate(self.rows):
            (w.add_css_class if i == self.sel else w.remove_css_class)("sel")

    def activate(self):
        if self.rows:
            self.rows[self.sel][1]()

    # ── results ──────────────────────────────────────────────────────────────
    def clear(self):
        c = self.results.get_first_child()
        while c:
            self.results.remove(c)
            c = self.results.get_first_child()
        self.rows = []
        self.sel = 0

    def row(self, img, title, sub, action, close=True):
        b = Gtk.Button()
        b.add_css_class("resrow")
        h = Gtk.Box(spacing=12)
        h.append(img)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        t = Gtk.Label(label=title, xalign=0, ellipsize=3)
        v.append(t)
        if sub:
            s = Gtk.Label(label=sub, xalign=0, ellipsize=3)
            s.add_css_class("dim")
            s.add_css_class("small")
            v.append(s)
        h.append(v)
        b.set_child(h)

        def go(*_):
            if close:
                self.hide()
            action()
        b.connect("clicked", go)
        self.results.append(b)
        self.rows.append((b, go))

    def section(self, text):
        l = Gtk.Label(label=text, xalign=0)
        l.add_css_class("dim")
        l.add_css_class("small")
        l.set_margin_start(12)
        l.set_margin_top(6)
        self.results.append(l)

    def refresh(self):
        q = self.entry.get_text().strip()
        self.clear()
        self.results_wrap.set_size_request(560, -1)
        {"search": self.r_search, "apps": self.r_apps, "files": self.r_files,
         "clipboard": self.r_clip, "actions": self.r_actions}[self.mode](q)
        self.results_wrap.set_visible(bool(self.rows) or self.mode == "apps")
        self.mark()

    def match_apps(self, q):
        ql = q.lower()
        out = []
        for a in self.apps:
            name = a.get_display_name().lower()
            if name.startswith(ql):
                out.append((0, a))
            elif ql in name or ql in (a.get_generic_name() or "").lower() or ql in (a.get_keywords() and " ".join(a.get_keywords()).lower() or ""):
                out.append((1, a))
        out.sort(key=lambda x: (x[0], x[1].get_display_name().lower()))
        return [a for _s, a in out]

    def add_app_rows(self, apps):
        for a in apps:
            self.row(app_icon(a), a.get_display_name(), a.get_description() or "Application",
                     lambda a=a: system.launch(a))

    def r_search(self, q):
        if not q:
            return
        c = calc(q)
        if c is not None:
            self.row(icons.icon("grid", "#f4f6f5", 30), c, f"{q} =", lambda: self.copy(c))
        apps = self.match_apps(q)[:6]
        if apps:
            self.section("Applications")
            self.add_app_rows(apps)
        files = self.find_files(q, 5)
        if files:
            self.section("Files")
            self.add_file_rows(files)
        acts = [a for a in self.action_list() if q.lower() in a[0].lower()]
        if acts:
            self.section("Actions")
            for name, glyph, fn in acts:
                self.row(icons.icon(glyph, "#f4f6f5", 28), name, "", fn)

    def r_apps(self, q):
        apps = self.match_apps(q) if q else self.apps
        grid = Gtk.FlowBox(max_children_per_line=6, min_children_per_line=6, selection_mode=Gtk.SelectionMode.NONE,
                           homogeneous=True, column_spacing=2, row_spacing=2)
        for a in apps:
            b = Gtk.Button()
            b.add_css_class("gridbtn")
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.CENTER)
            v.append(app_icon(a, 54))
            l = Gtk.Label(label=a.get_display_name(), ellipsize=3, max_width_chars=11)
            l.add_css_class("small")
            v.append(l)
            b.set_child(v)
            b.connect("clicked", lambda _b, a=a: (self.hide(), system.launch(a)))
            grid.append(b)
            self.rows.append((b, lambda a=a: (self.hide(), system.launch(a))))
        self.results.append(grid)
        self.results_wrap.set_size_request(640, 440)

    def find_files(self, q, n):
        try:
            out = subprocess.run(["find", HOME, "-maxdepth", "4", "-not", "-path", "*/.*", "-iname", f"*{q}*"],
                                 capture_output=True, text=True, timeout=1.0).stdout.splitlines()
        except Exception:  # noqa: BLE001
            out = []
        return out[:n]

    def add_file_rows(self, paths):
        for p in paths:
            isdir = os.path.isdir(p)
            self.row(icons.icon("folder" if isdir else "doc", "#9ec5ff" if isdir else "#f4f6f5", 28),
                     os.path.basename(p), os.path.dirname(p).replace(HOME, "~"),
                     lambda p=p: system.open_path(p))

    def r_files(self, q):
        if q:
            self.add_file_rows(self.find_files(q, 12))
            return
        self.section("Home")
        try:
            entries = sorted(e for e in os.listdir(HOME) if not e.startswith("."))
        except Exception:  # noqa: BLE001
            entries = []
        self.add_file_rows([os.path.join(HOME, e) for e in entries[:14]])

    def r_clip(self, q):
        out = system.run(["cliphist", "list"], timeout=2)
        lines = [l for l in out.splitlines() if l.strip()]
        if q:
            lines = [l for l in lines if q.lower() in l.lower()]
        if not lines:
            self.section("Clipboard history is empty")
        for l in lines[:14]:
            cid, _, text = l.partition("\t")
            self.row(icons.icon("copy", "#f4f6f5", 26), text[:80], "", lambda cid=cid: self.paste(cid))

    def paste(self, cid):
        try:
            data = subprocess.run(["cliphist", "decode", cid], capture_output=True, timeout=2).stdout
            subprocess.run(["wl-copy"], input=data, timeout=2)
        except Exception:  # noqa: BLE001
            pass

    def copy(self, text):
        try:
            subprocess.run(["wl-copy"], input=text.encode(), timeout=2)
        except Exception:  # noqa: BLE001
            pass

    def action_list(self):
        s = self.shell
        return [("Lock Screen", "lock", lambda: system.spawn(["bastille-lock"])),
                ("Do Not Disturb", "moon", lambda: s.toggle_dnd()),
                ("Control Center", "sliders", lambda: s.toggle("control")),
                ("Settings", "gear", lambda: system.spawn(["bastille-settings"])),
                ("App Store", "store", lambda: system.spawn(["bastille-store"])),
                ("Force Quit…", "x", lambda: s.show_force_quit()),
                ("Log Out", "x", lambda: system.sway_msg("exit")),
                ("Restart", "restart", lambda: system.spawn(["reboot"])),
                ("Power Off", "power", lambda: system.spawn(["poweroff"]))]

    def r_actions(self, q):
        for name, glyph, fn in self.action_list():
            if q.lower() in name.lower():
                self.row(icons.icon(glyph, "#f4f6f5", 28), name, "", fn)
