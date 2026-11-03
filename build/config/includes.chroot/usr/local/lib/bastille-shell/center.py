"""Notification Center (+ widgets, Edit Widgets gallery), toasts, Control Center (+ Edit Controls)."""

import math
import time

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell as LS

import icons
import system
from bar import layer_window


def clear_children(box):
    c = box.get_first_child()
    while c:
        box.remove(c)
        c = box.get_first_child()


def lab(text, *classes, xalign=0.0, **kw):
    l = Gtk.Label(label=text, xalign=xalign, **kw)
    for c in classes:
        l.add_css_class(c)
    return l


class Overlay:
    """Full-screen click-catcher with one panel placed by alignment/margins."""

    def __init__(self, app, panel, halign, valign, margins, on_hide=None):
        self.win = layer_window(app, {LS.Edge.TOP, LS.Edge.BOTTOM, LS.Edge.LEFT, LS.Edge.RIGHT},
                                layer=LS.Layer.OVERLAY, kb=LS.KeyboardMode.EXCLUSIVE, exclusive=-1)
        self.win.add_css_class("catcher")
        self.on_hide = on_hide
        click = Gtk.GestureClick()
        click.connect("pressed", lambda *_: self.hide())
        self.win.add_controller(click)
        stop = Gtk.GestureClick()
        stop.connect("pressed", lambda g, *_: g.set_state(Gtk.EventSequenceState.CLAIMED))
        panel.add_controller(stop)
        panel.set_halign(halign)
        panel.set_valign(valign)
        panel.set_margin_top(margins[0])
        panel.set_margin_end(margins[1])
        panel.set_margin_bottom(margins[2])
        panel.set_margin_start(margins[3])
        self.win.set_child(panel)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", lambda _c, k, *_: (self.hide(), True)[1] if k == Gdk.KEY_Escape else False)
        self.win.add_controller(keys)

    def visible(self):
        return self.win.get_visible()

    def show(self):
        self.win.present()

    def hide(self):
        self.win.set_visible(False)
        if self.on_hide:
            self.on_hide()


# ── widgets ───────────────────────────────────────────────────────────────────

WIDGETS = {   # kind -> (title, category, size)
    "clock": ("Clock", "Clock", "s"), "calendar": ("Calendar", "Calendar", "m"),
    "date": ("Date", "Calendar", "s"), "battery": ("Battery", "System", "s"),
    "system": ("System", "System", "s"), "note": ("Quick Note", "Notes", "m"),
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


class NotificationCenter:
    def __init__(self, app, shell):
        self.shell = shell
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

    def show(self):
        self.build()
        self.overlay.show()

    def build(self):
        clear_children(self.panel)
        head = Gtk.Box(spacing=8)
        head.append(lab("Notifications", "sechead", hexpand=True))
        n = self.shell.notifyd.history
        if n:
            clear = Gtk.Button(label="Clear")
            clear.add_css_class("pill")
            clear.connect("clicked", lambda *_: (self.shell.notifyd.clear(), self.build()))
            head.append(clear)
        dnd = Gtk.Button()
        dnd.add_css_class("pill")
        dnd.set_child(icons.icon("moon", "#f4f6f5", 14))
        dnd.set_tooltip_text("Do Not Disturb")
        if self.shell.notifyd.dnd:
            dnd.add_css_class("pri")
        dnd.connect("clicked", lambda *_: (self.shell.toggle_dnd(), self.build()))
        head.append(dnd)
        self.panel.append(head)
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
        self.panel.append(lab("Widgets", "sechead"))
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, column_homogeneous=True)
        col = row = 0
        for kind in self.widgets:
            if kind not in WIDGETS:
                continue
            w = make_widget(kind)
            wide = WIDGETS[kind][2] == "m"
            if wide and col == 1:
                col, row = 0, row + 1
            grid.attach(w, col, row, 2 if wide else 1, 1)
            col += 2 if wide else 1
            if col >= 2:
                col, row = 0, row + 1
        self.panel.append(grid)
        edit = Gtk.Button(label="Edit Widgets")
        edit.add_css_class("pill")
        edit.set_halign(Gtk.Align.CENTER)
        edit.connect("clicked", lambda *_: (self.hide(), self.gallery.show()))
        self.panel.append(edit)

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
        done = Gtk.Button(label="Done")
        done.add_css_class("pill")
        done.add_css_class("pri")
        done.connect("clicked", lambda *_: (self.overlay.hide(), nc.show()))
        head.append(done)
        main.append(head)
        sc = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.flow = Gtk.FlowBox(max_children_per_line=3, min_children_per_line=3, selection_mode=Gtk.SelectionMode.NONE,
                                homogeneous=True, column_spacing=12, row_spacing=12, valign=Gtk.Align.START)
        sc.set_child(self.flow)
        main.append(sc)
        panel.append(main)
        self.overlay = Overlay(app, panel, Gtk.Align.CENTER, Gtk.Align.CENTER, (0, 0, 0, 0))

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
            tile.append(make_widget(kind, preview=True))
            on = kind in self.nc.widgets
            tile.append(lab(title + ("  ✓" if on else ""), "small", xalign=0.5))
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

CONTROLS = {"wifi": "Wi‑Fi", "bluetooth": "Bluetooth", "vpn": "VPN", "dnd": "Do Not Disturb",
            "lock": "Lock Screen", "mute": "Mute"}
DEFAULT_CONTROLS = ["wifi", "bluetooth", "vpn", "dnd"]


class ControlCenter:
    def __init__(self, app, shell):
        self.shell = shell
        self.panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.panel.add_css_class("cc")
        self.panel.set_size_request(350, -1)
        self.overlay = Overlay(app, self.panel, Gtk.Align.END, Gtk.Align.START, (36, 10, 0, 0))
        self.controls = system.state_load("controls.json", {}).get("list", list(DEFAULT_CONTROLS))
        self.editing = False

    def visible(self):
        return self.overlay.visible()

    def hide(self):
        self.overlay.hide()

    def show(self):
        self.editing = False
        self.build()
        self.overlay.show()

    def tile(self, key, glyph, title, sub, on, action, chevron=None):
        b = Gtk.Button()
        b.add_css_class("tile")
        if on:
            b.add_css_class("on")
        row = Gtk.Box(spacing=10)
        row.append(icons.icon(glyph, "#1a1d1b" if on else "#f4f6f5", 22, 1.9))
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        v.append(lab(title, "title", ellipsize=3))
        v.append(lab(sub, "dim", "small", ellipsize=3))
        row.append(v)
        b.set_child(row)
        b.connect("clicked", lambda *_: (action(), GLib.idle_add(self.build)))
        return b

    def slider(self, glyph, value, on_change):
        row = Gtk.Box(spacing=10)
        row.add_css_class("tile")
        row.append(icons.icon(glyph, "#f4f6f5", 20))
        sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        sc.set_hexpand(True)
        sc.set_draw_value(False)
        sc.set_value(value)
        sc.connect("value-changed", lambda s: on_change(s.get_value()))
        row.append(sc)
        return row

    def build(self):
        clear_children(self.panel)
        sh = self.shell
        if self.editing:
            head = Gtk.Box()
            head.append(lab("Edit Controls", "sechead", hexpand=True))
            done = Gtk.Button(label="Done")
            done.add_css_class("pill")
            done.add_css_class("pri")
            done.connect("clicked", lambda *_: (setattr(self, "editing", False), self.build()))
            head.append(done)
            self.panel.append(head)
            for key, title in CONTROLS.items():
                on = key in self.controls
                b = Gtk.Button()
                b.add_css_class("tile")
                if on:
                    b.add_css_class("on")
                row = Gtk.Box(spacing=10)
                row.append(icons.icon("check" if on else "plus", "#1a1d1b" if on else "#f4f6f5", 18))
                row.append(lab(title, "title"))
                b.set_child(row)
                b.connect("clicked", lambda _b, k=key: self.toggle_control(k))
                self.panel.append(b)
            return

        grid = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
        i = 0
        for key in self.controls:
            t = self.make_tile(key)
            if t:
                grid.attach(t, i % 2, i // 2, 1, 1)
                i += 1
        self.panel.append(grid)
        b = system.brightness()
        if b is not None:
            self.panel.append(self.slider("sun", b, system.set_brightness))
        v, muted = system.volume()
        self.panel.append(self.slider("mute" if muted else "volume", v, system.set_volume))
        bat = system.battery()
        if bat:
            self.panel.append(lab(f"Battery  {bat[0]}%" + ("  ·  charging" if bat[1] else ""), "dim"))
        edit = Gtk.Button(label="Edit Controls")
        edit.add_css_class("pill")
        edit.set_halign(Gtk.Align.CENTER)
        edit.connect("clicked", lambda *_: (setattr(self, "editing", True), self.build()))
        self.panel.append(edit)

    def make_tile(self, key):
        sh = self.shell
        if key == "wifi":
            net = system.network()
            on = system.wifi_enabled()
            return self.tile(key, "wifi", "Wi‑Fi", net[1] if net[0] == "wifi" else ("On" if on else "Off"), on,
                             lambda: system.set_wifi(not on))
        if key == "bluetooth":
            return self.tile(key, "bt", "Bluetooth", "Blocked (hardened)", False, lambda: None)
        if key == "vpn":
            on = system.vpn_active()
            return self.tile(key, "vpn", "VPN", "Connected" if on else "Off", on,
                             lambda: system.spawn(["bastille-vpn", "toggle"]))
        if key == "dnd":
            on = sh.notifyd.dnd
            return self.tile(key, "moon", "Do Not Disturb", "On" if on else "Off", on, sh.toggle_dnd)
        if key == "lock":
            return self.tile(key, "lock", "Lock Screen", "", False, lambda: (self.hide(), system.spawn(["bastille-lock"])))
        if key == "mute":
            v, m = system.volume()
            return self.tile(key, "mute", "Mute", "On" if m else "Off", m, system.toggle_mute)
        return None

    def toggle_control(self, key):
        lst = list(self.controls)
        lst.remove(key) if key in lst else lst.append(key)
        self.controls = lst
        system.state_save("controls.json", {"list": lst})
        self.build()
