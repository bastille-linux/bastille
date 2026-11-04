"""Notification Center (+ widgets, Edit Widgets), toasts, Control Center (+ Wi-Fi, Bluetooth, Edit Controls)."""

import math
import shutil
import threading
import time

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import GLib, Gtk, Gtk4LayerShell as LS

import icons
import system
from ui import Overlay, button, clear_children, lab, layer_window, pill


# ── widgets ───────────────────────────────────────────────────────────────────

WIDGETS = {   # kind -> (title, category, size)
    "clock": ("Clock", "Clock", "s"), "calendar": ("Calendar", "Calendar", "m"),
    "date": ("Date", "Calendar", "s"), "battery": ("Battery", "System", "s"),
    "system": ("System", "System", "s"), "storage": ("Storage", "System", "s"),
    "network": ("Network", "System", "s"), "note": ("Quick Note", "Notes", "m"),
}
CATEGORIES = ["Suggestions", "Clock", "Calendar", "System", "Notes"]
DEFAULT_WIDGETS = ["calendar", "clock", "system"]


def analog_clock(size=110):
    area = Gtk.DrawingArea()
    area.set_content_width(size)
    area.set_content_height(size)

    def draw(_a, cr, w, h):
        cx, cy, r = w / 2, h / 2, min(w, h) / 2 - 4
        cr.set_source_rgba(0.12, 0.14, 0.13, 0.92)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgba(1, 1, 1, 0.25)
        cr.set_line_width(1)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.stroke()
        cr.set_source_rgba(1, 1, 1, 0.85)
        for i in range(12):
            a = i * math.pi / 6
            r1 = r - (7 if i % 3 == 0 else 4)
            cr.set_line_width(2 if i % 3 == 0 else 1)
            cr.move_to(cx + r1 * math.sin(a), cy - r1 * math.cos(a))
            cr.line_to(cx + (r - 2) * math.sin(a), cy - (r - 2) * math.cos(a))
            cr.stroke()
        t = time.localtime()
        for ang, ln, wd, col in (((t.tm_hour % 12 + t.tm_min / 60) * math.pi / 6, 0.5, 3.5, (1, 1, 1)),
                                 ((t.tm_min + t.tm_sec / 60) * math.pi / 30, 0.78, 2.5, (1, 1, 1)),
                                 (t.tm_sec * math.pi / 30, 0.85, 1.2, (1, 0.6, 0.2))):
            cr.set_source_rgb(*col)
            cr.set_line_width(wd)
            cr.move_to(cx, cy)
            cr.line_to(cx + r * ln * math.sin(ang), cy - r * ln * math.cos(ang))
            cr.stroke()
        cr.set_source_rgb(1, 0.6, 0.2)
        cr.arc(cx, cy, 3, 0, 2 * math.pi)
        cr.fill()
    area.set_draw_func(draw)
    GLib.timeout_add_seconds(1, lambda: (area.queue_draw(), area.get_mapped())[1])
    return area


def make_widget(kind, preview=False):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.add_css_class("widget")
    box.set_hexpand(True)
    if preview:
        box.set_size_request(210, 150)
        box.set_overflow(Gtk.Overflow.HIDDEN)
        box.set_halign(Gtk.Align.CENTER)
    if kind == "clock":
        box.set_halign(Gtk.Align.CENTER)
        box.append(analog_clock(100 if preview else 118))
    elif kind == "calendar":
        now = time.localtime()
        box.append(lab(time.strftime("%A").upper(), "dim", "small"))
        box.append(lab(str(now.tm_mday), "big"))
        if preview:
            box.append(lab(time.strftime("%B %Y"), "dim"))
        else:
            box.append(Gtk.Calendar())
    elif kind == "date":
        now = time.localtime()
        box.append(lab(time.strftime("%A").upper(), "dim", "small"))
        box.append(lab(str(now.tm_mday), "big"))
        box.append(lab(time.strftime("%B %Y"), "dim"))
    elif kind == "battery":
        b = system.battery()
        box.append(icons.icon("battery", "#f4f6f5", 28))
        box.append(lab(f"{b[0]}%", "big") if b else lab("AC power", "title"))
        box.append(lab("Charging" if b and b[1] else ("Battery" if b else "No battery"), "dim"))
    elif kind == "system":
        try:
            mem = {k: int(v.split()[0]) for k, v in (l.split(":", 1) for l in open("/proc/meminfo"))}
            used = 100 - int(100 * mem["MemAvailable"] / mem["MemTotal"])
            load = open("/proc/loadavg").read().split()[0]
        except Exception:  # noqa: BLE001
            used, load = 0, "0"
        box.append(icons.icon("cpu", "#f4f6f5", 28))
        box.append(lab(f"{used}% memory", "title"))
        box.append(lab(f"Load {load}", "dim"))
    elif kind == "storage":
        try:
            du = shutil.disk_usage("/")
            pct, free = int(100 * du.used / du.total), du.free / 1e9
        except Exception:  # noqa: BLE001
            pct, free = 0, 0.0
        box.append(icons.icon("hdd", "#f4f6f5", 28))
        box.append(lab(f"{pct}% used", "title"))
        box.append(lab(f"{free:.1f} GB free", "dim"))
    elif kind == "network":
        net = system.network()
        box.append(icons.icon("wifi" if net[0] != "eth" else "eth", "#f4f6f5", 28))
        box.append(lab(net[1] if net[0] != "none" else "Offline", "title", ellipsize=3))
        box.append(lab("VPN on" if system.vpn_active() else "VPN off", "dim"))
    elif kind == "note":
        tv = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        tv.set_size_request(-1, 90)
        buf = tv.get_buffer()
        buf.set_text(system.state_load("quicknote.json", {}).get("text", "") if not preview else "Write a note…")
        if not preview:
            buf.connect("changed", lambda b: system.state_save(
                "quicknote.json", {"text": b.get_text(b.get_start_iter(), b.get_end_iter(), False)}))
        box.append(lab("Quick Note", "dim", "small"))
        box.append(tv)
    return box


def badge_btn(glyph, cls, on_click, halign, valign, tip=""):
    b = Gtk.Button()
    b.add_css_class("badge")
    b.add_css_class(cls)
    b.set_child(icons.icon(glyph, "#ffffff", 12, 2.6))
    b.set_halign(halign)
    b.set_valign(valign)
    if tip:
        b.set_tooltip_text(tip)
    b.connect("clicked", lambda *_: on_click())
    return b


def edit_wrap(child, remove, move_back=None, move_fwd=None, plus=False):
    """Wiggling edit-mode frame: remove/add badge top-left, reorder arrows top-right."""
    ov = Gtk.Overlay()
    ov.set_child(child)
    ov.add_css_class("wiggle")
    ov.add_overlay(badge_btn("plus" if plus else "minus", "plus" if plus else "minus", remove,
                             Gtk.Align.START, Gtk.Align.START, "Add" if plus else "Remove"))
    if not plus:
        mv = Gtk.Box(spacing=2, halign=Gtk.Align.END, valign=Gtk.Align.START, margin_top=2, margin_end=2)
        if move_back:
            mv.append(badge_btn("back", "mv", move_back, Gtk.Align.CENTER, Gtk.Align.CENTER, "Move earlier"))
        if move_fwd:
            mv.append(badge_btn("chev", "mv", move_fwd, Gtk.Align.CENTER, Gtk.Align.CENTER, "Move later"))
        ov.add_overlay(mv)
    return ov


def moved(lst, i, d):
    lst = list(lst)
    j = i + d
    if 0 <= j < len(lst):
        lst[i], lst[j] = lst[j], lst[i]
    return lst


class NotificationCenter:
    def __init__(self, app, shell):
        self.shell = shell
        self.editing = False
        self.panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.panel.add_css_class("nc")
        self.panel.set_size_request(400, -1)
        sc = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, propagate_natural_height=True,
                                max_content_height=720)
        sc.set_child(self.panel)
        shell_box = Gtk.Box()
        shell_box.append(sc)
        self.overlay = Overlay(app, shell_box, Gtk.Align.END, Gtk.Align.START, (36, 10, 0, 0))
        self.widgets = system.state_load("widgets.json", {}).get("list", list(DEFAULT_WIDGETS))
        self.gallery = Gallery(app, self)

    def visible(self):
        return self.overlay.visible()

    def hide(self):
        self.overlay.hide()

    def show(self, editing=False):
        self.editing = editing
        self.build()
        self.overlay.show()

    def build(self):
        clear_children(self.panel)
        if self.editing:
            head = Gtk.Box(spacing=8)
            head.append(lab("Edit Widgets", "sechead", hexpand=True))
            head.append(pill("Done", "pri", on_click=lambda: self.set_editing(False)))
            self.panel.append(head)
            self.panel.append(lab("Tap − to remove a widget, use the arrows to reorder, or add new ones.",
                                  "dim", "small", wrap=True))
        else:
            self.build_header()
            self.build_notifications()
            self.panel.append(lab("Widgets", "sechead"))
        self.build_widgets()
        if self.editing:
            add = button(Gtk.Box(spacing=8, halign=Gtk.Align.CENTER), "addtile", on_click=self.open_gallery)
            row = add.get_child()
            row.append(icons.icon("plus", "#f4f6f5", 18, 2.2))
            row.append(lab("Add Widget", "title"))
            self.panel.append(add)
        else:
            self.panel.append(pill("Edit Widgets", on_click=lambda: self.set_editing(True)))
            self.panel.get_last_child().set_halign(Gtk.Align.CENTER)

    def build_header(self):
        head = Gtk.Box(spacing=8)
        head.append(lab("Notifications", "sechead", hexpand=True))
        if self.shell.notifyd.history:
            head.append(pill("Clear", on_click=lambda: (self.shell.notifyd.clear(), self.build())))
        dnd = Gtk.Button()
        dnd.add_css_class("pill")
        dnd.set_child(icons.icon("moon", "#f4f6f5", 14))
        dnd.set_tooltip_text("Do Not Disturb")
        if self.shell.notifyd.dnd:
            dnd.add_css_class("pri")
        dnd.connect("clicked", lambda *_: (self.shell.toggle_dnd(), self.build()))
        head.append(dnd)
        self.panel.append(head)

    def build_notifications(self):
        n = self.shell.notifyd.history
        if not n:
            empty = lab("No Notifications", "dim", xalign=0.5)
            empty.set_margin_top(18)
            empty.set_margin_bottom(18)
            self.panel.append(empty)
        for item in n[:6]:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            card.add_css_class("ncard")
            top = Gtk.Box()
            top.append(lab(item["app"], "dim", "small", hexpand=True))
            top.append(lab(time.strftime("%H:%M", time.localtime(item["time"])), "dim", "small"))
            card.append(top)
            card.append(lab(item["summary"], "title", wrap=True))
            if item["body"]:
                card.append(lab(item["body"], wrap=True))
            self.panel.append(card)

    def build_widgets(self):
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, column_homogeneous=True)
        col = row = 0
        kinds = [k for k in self.widgets if k in WIDGETS]
        for i, kind in enumerate(kinds):
            w = make_widget(kind)
            if self.editing:
                w = edit_wrap(w, lambda k=kind: self.remove(k),
                              (lambda i=i: self.move(i, -1)) if i > 0 else None,
                              (lambda i=i: self.move(i, 1)) if i < len(kinds) - 1 else None)
            wide = WIDGETS[kind][2] == "m"
            if wide and col == 1:
                col, row = 0, row + 1
            grid.attach(w, col, row, 2 if wide else 1, 1)
            col += 2 if wide else 1
            if col >= 2:
                col, row = 0, row + 1
        self.panel.append(grid)

    # ── edit mode ─────────────────────────────────────────────────────────────
    def set_editing(self, on):
        self.editing = on
        self.build()

    def open_gallery(self):
        self.overlay.hide_now()
        self.gallery.show()

    def remove(self, kind):
        self.set_widgets([k for k in self.widgets if k != kind])
        self.build()

    def move(self, i, d):
        kinds = [k for k in self.widgets if k in WIDGETS]
        self.set_widgets(moved(kinds, i, d))
        self.build()

    def set_widgets(self, lst):
        self.widgets = lst
        system.state_save("widgets.json", {"list": lst})


class Gallery:
    def __init__(self, app, nc):
        self.nc = nc
        self.cat = "Suggestions"
        self.query = ""
        panel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        panel.add_css_class("gallery")
        panel.set_size_request(820, 540)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        side.set_size_request(210, -1)
        side.set_margin_top(18)
        side.set_margin_start(14)
        side.set_margin_end(10)
        self.search = Gtk.SearchEntry(placeholder_text="Search Widgets")
        self.search.add_css_class("search")
        self.search.connect("search-changed", lambda e: (setattr(self, "query", e.get_text()), self.fill()))
        side.append(self.search)
        self.cat_btns = {}
        for c in CATEGORIES:
            b = Gtk.Button()
            b.add_css_class("sidebtn")
            b.set_child(lab(c))
            b.connect("clicked", lambda _b, c=c: self.pick(c))
            self.cat_btns[c] = b
            side.append(b)
        panel.append(side)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, hexpand=True)
        main.set_margin_top(18)
        main.set_margin_end(18)
        main.set_margin_bottom(16)
        head = Gtk.Box()
        self.title = lab("Suggestions", "sechead", hexpand=True)
        head.append(self.title)
        head.append(pill("Done", "pri", on_click=self.done))
        main.append(head)
        sc = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.flow = Gtk.FlowBox(max_children_per_line=3, min_children_per_line=3, selection_mode=Gtk.SelectionMode.NONE,
                                homogeneous=True, column_spacing=12, row_spacing=12, valign=Gtk.Align.START)
        sc.set_child(self.flow)
        main.append(sc)
        panel.append(main)
        self.overlay = Overlay(app, panel, Gtk.Align.CENTER, Gtk.Align.CENTER, (0, 0, 0, 0), dim=True)

    def done(self):
        self.overlay.hide_now()
        self.nc.show(editing=True)

    def show(self):
        self.search.set_text("")
        self.query = ""
        self.pick("Suggestions")
        self.overlay.show()

    def pick(self, cat):
        self.cat = cat
        self.title.set_text(cat)
        for c, b in self.cat_btns.items():
            (b.add_css_class if c == cat else b.remove_css_class)("sel")
        self.fill()

    def fill(self):
        clear_children(self.flow)
        for kind, (title, cat, _size) in WIDGETS.items():
            if self.query and self.query.lower() not in title.lower():
                continue
            if not self.query and self.cat != "Suggestions" and cat != self.cat:
                continue
            tile = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            on = kind in self.nc.widgets
            prev = Gtk.Overlay()
            prev.set_child(make_widget(kind, preview=True))
            mark = Gtk.Box(halign=Gtk.Align.END, valign=Gtk.Align.START, margin_end=6, margin_top=6)
            mark.add_css_class("badge")
            mark.add_css_class("minus" if on else "plus")
            mark.set_can_target(False)
            mark.append(icons.icon("check" if on else "plus", "#ffffff", 12, 2.6))
            prev.add_overlay(mark)
            tile.append(prev)
            tile.append(lab(title + ("  ·  Added" if on else ""), "small", xalign=0.5))
            btn = Gtk.Button()
            btn.add_css_class("gridbtn")
            btn.set_child(tile)
            btn.connect("clicked", lambda _b, k=kind: self.toggle(k))
            self.flow.append(btn)

    def toggle(self, kind):
        lst = list(self.nc.widgets)
        lst.remove(kind) if kind in lst else lst.append(kind)
        self.nc.set_widgets(lst)
        self.fill()


# ── toasts ────────────────────────────────────────────────────────────────────

class Toasts:
    def __init__(self, app):
        self.win = layer_window(app, {LS.Edge.TOP, LS.Edge.RIGHT}, layer=LS.Layer.OVERLAY,
                                margins={LS.Edge.TOP: 36, LS.Edge.RIGHT: 10})
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.box.set_size_request(340, -1)
        self.win.set_child(self.box)

    def push(self, item):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.add_css_class("toast")
        card.append(lab(item["app"], "dim", "small"))
        card.append(lab(item["summary"], "title", wrap=True))
        if item["body"]:
            card.append(lab(item["body"], wrap=True))
        click = Gtk.GestureClick()
        click.connect("pressed", lambda *_: self.drop(card))
        card.add_controller(click)
        self.box.append(card)
        self.win.present()
        GLib.timeout_add_seconds(6, lambda: (self.drop(card), False)[1])

    def drop(self, card):
        if card.get_parent() is self.box:
            self.box.remove(card)
        if not self.box.get_first_child():
            self.win.set_visible(False)


# ── control centre ────────────────────────────────────────────────────────────

CONTROLS = {   # key -> (title, glyph)
    "wifi": ("Wi‑Fi", "wifi"), "bluetooth": ("Bluetooth", "bt"), "vpn": ("VPN", "vpn"),
    "dnd": ("Do Not Disturb", "moon"), "lock": ("Lock Screen", "lock"), "mute": ("Mute", "mute"),
    "airplane": ("Airplane Mode", "airplane"), "screenshot": ("Screenshot", "camera"),
    "awake": ("Keep Awake", "coffee"),
}
DEFAULT_CONTROLS = ["wifi", "bluetooth", "vpn", "dnd"]
PAGES = ("main", "wifi", "bt", "edit")


class ControlCenter:
    def __init__(self, app, shell):
        self.shell = shell
        self.page = "main"
        self.bt = "blocked"        # cached, refreshed off the main thread
        self._tok = 0
        self.panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.panel.add_css_class("cc")
        self.panel.set_size_request(350, -1)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.NONE, transition_duration=240,
                               interpolate_size=True, hhomogeneous=True, vhomogeneous=False)
        self.boxes = {}
        for name in PAGES:
            b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.stack.add_named(b, name)
            self.boxes[name] = b
        self.panel.append(self.stack)
        self.overlay = Overlay(app, self.panel, Gtk.Align.END, Gtk.Align.START, (36, 10, 0, 0))
        self.controls = system.state_load("controls.json", {}).get("list", list(DEFAULT_CONTROLS))

    # ── visibility ────────────────────────────────────────────────────────────
    def visible(self):
        return self.overlay.visible()

    def hide(self):
        self.overlay.hide()

    def show(self, page="main"):
        self._tok += 1
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.page = page
        self.fill(page)
        self.stack.set_visible_child_name(page)
        self.refresh_bt()
        self.overlay.show()

    def go(self, name):
        if name == self.page:
            return
        forward = PAGES.index(name) > PAGES.index(self.page) if self.page == "main" else False
        self._tok += 1
        self.fill(name)
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT if forward
                                       else Gtk.StackTransitionType.SLIDE_RIGHT)
        self.stack.set_visible_child_name(name)
        self.page = name

    def fill(self, name):
        box = self.boxes[name]
        clear_children(box)
        {"main": self.page_main, "wifi": self.page_wifi, "bt": self.page_bt, "edit": self.page_edit}[name](box)

    def rebuild(self):
        if self.visible():
            self.fill(self.page)

    # ── tiles ─────────────────────────────────────────────────────────────────
    def mk_tile(self, glyph, title, sub, on, toggle, expand=None):
        t = Gtk.Box(spacing=4)
        t.add_css_class("tile")
        if on:
            t.add_css_class("on")
        t.append(button(icons.icon(glyph, "#f4f6f5", 20, 1.9), "tilecircle", on_click=lambda: self.act(toggle),
                        valign=Gtk.Align.CENTER))
        inner = Gtk.Box(spacing=4)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        v.append(lab(title, "title", ellipsize=3))
        v.append(lab(sub, "dim", "small", ellipsize=3))
        inner.append(v)
        if expand:
            inner.append(icons.icon("chev", "#f4f6f5", 12, 2.2))
        body = button(inner, "tilebody", hexpand=True, valign=Gtk.Align.CENTER,
                      on_click=(lambda: self.go(expand)) if expand else (lambda: self.act(toggle)))
        t.append(body)
        return t

    def act(self, fn):
        fn()
        GLib.idle_add(lambda: (self.rebuild(), False)[1])

    def slider(self, glyph, value, on_change):
        row = Gtk.Box(spacing=10)
        row.add_css_class("slidebox")
        row.append(icons.icon(glyph, "#f4f6f5", 20))
        sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        sc.set_hexpand(True)
        sc.set_draw_value(False)
        sc.set_value(value)
        sc.connect("value-changed", lambda s: on_change(s.get_value()))
        row.append(sc)
        return row

    def spec(self, key):
        """(glyph, title, subtitle, on, toggle, expand_page) for one control."""
        sh = self.shell
        title, glyph = CONTROLS[key]
        if key == "wifi":
            net, on = system.network(), system.wifi_enabled()
            return glyph, title, net[1] if net[0] == "wifi" else ("On" if on else "Off"), on, \
                (lambda: system.set_wifi(not on)), "wifi"
        if key == "bluetooth":
            sub = {"on": "On", "off": "Off", "blocked": "Blocked", "none": "Unavailable"}[self.bt]
            return glyph, title, sub, self.bt == "on", self.toggle_bt, "bt"
        if key == "vpn":
            on = system.vpn_active()
            return glyph, title, "Connected" if on else "Off", on, \
                (lambda: (system.spawn(["pkexec", "/usr/local/sbin/bastille-set-wg", "down" if on else "up"]),
                          GLib.timeout_add(2500, lambda: (self.rebuild(), False)[1]))), None
        if key == "dnd":
            on = sh.notifyd.dnd
            return glyph, title, "On" if on else "Off", on, sh.toggle_dnd, None
        if key == "lock":
            return glyph, title, "", False, lambda: (self.hide(), system.spawn(["bastille-lock"])), None
        if key == "mute":
            _v, m = system.volume()
            return glyph, title, "On" if m else "Off", m, system.toggle_mute, None
        if key == "airplane":
            on = not system.wifi_enabled() and self.bt != "on"
            return glyph, title, "On" if on else "Off", on, self.toggle_airplane, None
        if key == "screenshot":
            return glyph, title, "Select area", False, lambda: (
                self.hide(), GLib.timeout_add(250, lambda: (system.spawn(
                    ["sh", "-c", 'grim -g "$(slurp)" - | wl-copy']), False)[1])), None
        if key == "awake":
            on = system.run(["ps", "-o", "stat=", "-C", "swayidle"]).startswith("T")
            return glyph, title, "On" if on else "Off", on, \
                (lambda: system.run(["pkill", "-CONT" if on else "-STOP", "swayidle"])), None
        return None

    # ── actions that touch hardware ──────────────────────────────────────────
    def refresh_bt(self):
        def work():
            st = system.bt_state()
            GLib.idle_add(self._set_bt, st)
        threading.Thread(target=work, daemon=True).start()

    def _set_bt(self, st):
        changed = st != self.bt
        self.bt = st
        if changed:
            self.rebuild()
        return False

    def toggle_bt(self):
        want = self.bt != "on"
        self.bt = "on" if want else "off"      # optimistic; the thread corrects it

        def work():
            system.set_bluetooth(want)
            GLib.idle_add(self._set_bt, system.bt_state())
        threading.Thread(target=work, daemon=True).start()

    def toggle_airplane(self):
        on = not system.wifi_enabled() and self.bt != "on"
        system.set_wifi(on)
        if not on:
            self.bt = "blocked"
            threading.Thread(target=lambda: system.set_bluetooth(False), daemon=True).start()

    # ── main page ─────────────────────────────────────────────────────────────
    def page_main(self, box):
        grid = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
        i = 0
        for key in self.controls:
            sp = self.spec(key) if key in CONTROLS else None
            if sp:
                grid.attach(self.mk_tile(*sp), i % 2, i // 2, 1, 1)
                i += 1
        box.append(grid)
        b = system.brightness()
        if b is not None:
            box.append(self.slider("sun", b, system.set_brightness))
        v, muted = system.volume()
        box.append(self.slider("mute" if muted else "volume", v, system.set_volume))
        bat = system.battery()
        if bat:
            box.append(lab(f"Battery  {bat[0]}%" + ("  ·  charging" if bat[1] else ""), "dim"))
        edit = pill("Edit Controls", on_click=lambda: self.go("edit"))
        edit.set_halign(Gtk.Align.CENTER)
        box.append(edit)

    # ── detail pages ──────────────────────────────────────────────────────────
    def head(self, box, title, switch=None, switch_cb=None):
        row = Gtk.Box(spacing=8)
        row.append(button(icons.icon("back", "#f4f6f5", 16, 2.2), "barbtn", on_click=lambda: self.go("main"),
                          tooltip_text="Back"))
        row.append(lab(title, "sechead", hexpand=True))
        if switch is not None:
            sw = Gtk.Switch(valign=Gtk.Align.CENTER)
            sw.set_active(switch)
            sw.connect("notify::active", lambda s, _p: switch_cb(s.get_active()))
            row.append(sw)
        box.append(row)

    def message(self, box, text):
        box.append(lab(text, "dim", wrap=True, max_width_chars=36, margin_top=8, margin_bottom=8,
                       margin_start=6, margin_end=6))

    # Wi-Fi
    def page_wifi(self, box):
        on = system.wifi_enabled()
        self.head(box, "Wi‑Fi", on, self.wifi_switch)
        self.wifi_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.append(self.wifi_list)
        if on:
            sp = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
            sp.append(Gtk.Spinner(spinning=True))
            sp.append(lab("Looking for networks…", "dim"))
            self.wifi_list.append(sp)
            self.scan_wifi()
        else:
            self.message(self.wifi_list, "Wi‑Fi is turned off.")
        link = pill("Wi‑Fi Settings…", on_click=lambda: (self.hide(), system.spawn(["foot", "nmtui"])))
        link.set_halign(Gtk.Align.CENTER)
        box.append(link)

    def wifi_switch(self, on):
        def work():
            system.set_wifi(on)
            time.sleep(0.6)
            GLib.idle_add(lambda: (self.fill("wifi") if self.page == "wifi" else None, False)[1])
        threading.Thread(target=work, daemon=True).start()

    def scan_wifi(self):
        tok = self._tok

        def work():
            known = system.wifi_known()
            GLib.idle_add(self.show_networks, tok, system.wifi_networks("no", 5), known)
            GLib.idle_add(self.show_networks, tok, system.wifi_networks("yes", 15), known)
        threading.Thread(target=work, daemon=True).start()

    def show_networks(self, tok, nets, known):
        if tok != self._tok or self.page != "wifi":
            return False
        # keep a half-typed password alive across the second (rescanned) update
        if getattr(self, "_pw_open", None) and self._pw_open.get_reveal_child():
            return False
        clear_children(self.wifi_list)
        if not nets:
            self.message(self.wifi_list, "No networks found.")
            return False
        cur = [n for n in nets if n[2]]
        others = [n for n in nets if not n[2]]
        if cur:
            self.wifi_list.append(lab("Known Network", "dim", "small", margin_start=8, margin_top=2))
            self.wifi_list.append(self.net_row(cur[0], known))
        if others:
            self.wifi_list.append(lab("Other Networks", "dim", "small", margin_start=8, margin_top=8))
            grp = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            for n in others[:8]:
                grp.append(self.net_row(n, known))
            self.wifi_list.append(grp)
        return False

    def net_row(self, net, known):
        ssid, sig, in_use, secured = net
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        status = lab("", "dim", "small", margin_start=46)
        status.set_visible(False)
        rev = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN, transition_duration=180)
        pw_row = Gtk.Box(spacing=6, margin_start=46, margin_end=6, margin_top=2, margin_bottom=6)
        entry = Gtk.Entry(visibility=False, placeholder_text=f"Password for {ssid}", hexpand=True)
        entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        pw_row.append(entry)
        join = pill("Join", "pri")
        pw_row.append(join)
        rev.set_child(pw_row)

        def do_connect(pw=None):
            status.set_text("Connecting…")
            status.set_visible(True)

            def work():
                ok, msg = system.wifi_connect(ssid, pw)
                GLib.idle_add(done, ok, msg)
            threading.Thread(target=work, daemon=True).start()

        def done(ok, msg):
            status.set_text("" if ok else (msg or "Could not connect"))
            status.set_visible(not ok)
            self._pw_open = None
            if ok and self.page == "wifi":
                self.fill("wifi")
            return False

        def clicked():
            if in_use:
                return
            if secured and ssid not in known:
                rev.set_reveal_child(not rev.get_reveal_child())
                self._pw_open = rev if rev.get_reveal_child() else None
                if rev.get_reveal_child():
                    entry.grab_focus()
            else:
                do_connect()
        join.connect("clicked", lambda *_: entry.get_text() and do_connect(entry.get_text()))
        entry.connect("activate", lambda *_: entry.get_text() and do_connect(entry.get_text()))

        row = Gtk.Box(spacing=10)
        circle = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        circle.add_css_class("netcircle")
        if in_use:
            circle.add_css_class("on")
        circle.set_size_request(30, 30)
        circle.append(icons.icon("check" if in_use else "wifi", "#f4f6f5", 16, 2.0))
        row.append(circle)
        row.append(lab(ssid, hexpand=True, ellipsize=3, max_width_chars=22))
        if secured:
            row.append(icons.icon("lock", "#f4f6f5", 13, 2.0))
        row.append(icons.icon("signal", "#f4f6f5" if sig > 50 else "#9aa09d", 14, 2.0))
        if in_use:
            row.append(pill("Disconnect", on_click=lambda: threading.Thread(
                target=lambda: (system.wifi_disconnect(), GLib.idle_add(lambda: (self.fill("wifi"), False)[1])),
                daemon=True).start()))
        if in_use:
            row.add_css_class("netrow")
            col.append(row)
        else:
            col.append(button(row, "netrow", on_click=clicked))
        col.append(rev)
        col.append(status)
        return col

    # Bluetooth
    def page_bt(self, box):
        st = self.bt
        self.head(box, "Bluetooth", st == "on", self.bt_switch)
        self.bt_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.append(self.bt_list)
        if st == "on":
            sp = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
            sp.append(Gtk.Spinner(spinning=True))
            sp.append(lab("Loading devices…", "dim"))
            self.bt_list.append(sp)
            tok = self._tok
            threading.Thread(target=lambda: GLib.idle_add(self.show_devices, tok, system.bt_devices()),
                             daemon=True).start()
        elif st == "none":
            self.message(self.bt_list, "No Bluetooth adapter was found, or Bluetooth support isn’t installed. "
                                       "Bastille ships with the Bluetooth stack disabled for security.")
        else:
            self.message(self.bt_list, "Bluetooth is off. Bastille blocks it at boot — turn it on only while "
                                       "you need to pair a device.")

    def bt_switch(self, on):
        self.bt = "on" if on else "off"

        def work():
            system.set_bluetooth(on)
            st = system.bt_state()
            GLib.idle_add(lambda: (self._set_bt_page(st), False)[1])
        threading.Thread(target=work, daemon=True).start()

    def _set_bt_page(self, st):
        self.bt = st
        if self.page == "bt":
            self.fill("bt")

    def show_devices(self, tok, devs):
        if tok != self._tok or self.page != "bt":
            return False
        clear_children(self.bt_list)
        if not devs:
            self.message(self.bt_list, "No devices yet. Pair one with bluetoothctl, then it will show up here.")
            return False
        self.bt_list.append(lab("My Devices", "dim", "small", margin_start=8, margin_top=2))
        for d in devs:
            row = Gtk.Box(spacing=10)
            circle = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
            circle.add_css_class("netcircle")
            if d["connected"]:
                circle.add_css_class("on")
            circle.set_size_request(30, 30)
            circle.append(icons.icon("bt", "#f4f6f5", 16, 2.0))
            row.append(circle)
            row.append(lab(d["name"], hexpand=True, ellipsize=3, max_width_chars=22))
            if d["battery"] is not None:
                row.append(lab(f"{d['battery']}%", "dim", "small"))
            row.append(lab("Connected" if d["connected"] else "Not Connected", "dim", "small"))

            def toggle(d=d):
                threading.Thread(target=lambda: (system.bt_connect(d["mac"], not d["connected"]),
                                                 GLib.idle_add(lambda: (self.fill("bt") if self.page == "bt"
                                                                        else None, False)[1])),
                                 daemon=True).start()
            self.bt_list.append(button(row, "netrow", on_click=toggle))
        return False

    # ── edit controls ─────────────────────────────────────────────────────────
    def page_edit(self, box):
        row = Gtk.Box(spacing=8)
        row.append(lab("Edit Controls", "sechead", hexpand=True))
        row.append(pill("Done", "pri", on_click=lambda: self.go("main")))
        box.append(row)
        box.append(lab("Tap − to remove a control, use the arrows to reorder, or add more below.", "dim", "small",
                       wrap=True))
        inc = [k for k in self.controls if k in CONTROLS]
        grid = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
        for i, key in enumerate(inc):
            grid.attach(edit_wrap(self.edit_tile(key), lambda k=key: self.toggle_control(k),
                                  (lambda i=i: self.move_control(i, -1)) if i > 0 else None,
                                  (lambda i=i: self.move_control(i, 1)) if i < len(inc) - 1 else None),
                        i % 2, i // 2, 1, 1)
        box.append(grid)
        more = [k for k in CONTROLS if k not in inc]
        if more:
            box.append(lab("More Controls", "sechead", margin_top=4))
            g2 = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
            for i, key in enumerate(more):
                g2.attach(edit_wrap(self.edit_tile(key), lambda k=key: self.toggle_control(k), plus=True),
                          i % 2, i // 2, 1, 1)
            box.append(g2)

    def edit_tile(self, key):
        title, glyph = CONTROLS[key]
        t = Gtk.Box(spacing=8)
        t.add_css_class("tile")
        c = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, margin_start=12)
        c.add_css_class("netcircle")
        c.set_size_request(38, 38)
        c.append(icons.icon(glyph, "#f4f6f5", 20, 1.9))
        t.append(c)
        t.append(lab(title, "title", ellipsize=3, max_width_chars=9, valign=Gtk.Align.CENTER, hexpand=True))
        return t

    def toggle_control(self, key):
        lst = list(self.controls)
        lst.remove(key) if key in lst else lst.append(key)
        self.save_controls(lst)

    def move_control(self, i, d):
        self.save_controls(moved([k for k in self.controls if k in CONTROLS], i, d))

    def save_controls(self, lst):
        self.controls = lst
        system.state_save("controls.json", {"list": lst})
        self.fill("edit")
