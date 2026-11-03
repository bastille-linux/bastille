"""Top menu bar and bottom dock."""

import threading
import time

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import GLib, Gtk, Gtk4LayerShell as LS

import icons
import system

DOCK = [("files", "bastille-files"), ("browser", "bastille-browser"), ("terminal", "bastille-terminal"),
        ("mail", "bastille-mail"), ("messages", "bastille-messages"), ("notes", "bastille-notes"),
        ("calendar", "bastille-calendar"), ("music", "bastille-music"), ("weather", "bastille-weather"),
        ("settings", "bastille-settings")]


def layer_window(app, edge_anchors, layer=LS.Layer.TOP, exclusive=0, kb=LS.KeyboardMode.NONE, margins=None):
    win = Gtk.Window(application=app)
    win.add_css_class("shell")
    win.set_decorated(False)
    LS.init_for_window(win)
    LS.set_layer(win, layer)
    for edge in (LS.Edge.TOP, LS.Edge.BOTTOM, LS.Edge.LEFT, LS.Edge.RIGHT):
        LS.set_anchor(win, edge, edge in edge_anchors)
    for edge, m in (margins or {}).items():
        LS.set_margin(win, edge, m)
    if exclusive:
        LS.set_exclusive_zone(win, exclusive)
    LS.set_keyboard_mode(win, kb)
    return win


def pretty_app(app_id):
    if not app_id:
        return "Bastille"
    name = app_id.split(".")[-1]
    name = name.replace("bastille-", "").replace("-", " ")
    return name[:1].upper() + name[1:]


class Bar:
    def __init__(self, app, shell):
        self.shell = shell
        self.win = layer_window(app, {LS.Edge.TOP, LS.Edge.LEFT, LS.Edge.RIGHT}, exclusive=28)
        box = Gtk.Box(spacing=2)
        box.add_css_class("bar")

        logo = Gtk.Button()
        logo.add_css_class("barbtn")
        logo.set_child(icons.icon("shield", "#f4f6f5", 15, 2.0))
        logo.connect("clicked", lambda *_: shell.show_launcher("apps"))
        box.append(logo)

        self.app_label = Gtk.Label(label="Finder")
        self.app_label.add_css_class("app")
        self.app_label.set_margin_start(6)
        self.app_label.set_margin_end(10)
        box.append(self.app_label)
        for name, cb in (("File", None), ("Edit", None), ("View", None), ("Window", None)):
            lab = Gtk.Label(label=name)
            lab.add_css_class("dim")
            lab.set_margin_start(8)
            lab.set_margin_end(8)
            box.append(lab)

        spacer = Gtk.Box(hexpand=True)
        box.append(spacer)

        self.vpn = icons.icon("vpn", "#f4f6f5", 15)
        self.net = Gtk.Box()
        self.vol = Gtk.Box()
        self.bat = Gtk.Box(spacing=4)
        self.bat_lbl = Gtk.Label(label="")
        for w in (self.vpn, self.net, self.vol, self.bat):
            w.set_margin_start(6)
            w.set_margin_end(6)
            box.append(w)
        self.vpn.set_visible(False)

        cc = Gtk.Button()
        cc.add_css_class("barbtn")
        cc.set_child(icons.icon("sliders", "#f4f6f5", 15))
        cc.connect("clicked", lambda *_: shell.toggle("control"))
        box.append(cc)

        self.clock = Gtk.Button()
        self.clock.add_css_class("barbtn")
        self.clock_lbl = Gtk.Label(label="")
        self.clock.set_child(self.clock_lbl)
        self.clock.connect("clicked", lambda *_: shell.toggle("center"))
        box.append(self.clock)

        self.win.set_child(box)
        self.tick()
        GLib.timeout_add_seconds(1, self.tick)
        self.refresh_status()
        GLib.timeout_add_seconds(15, self.refresh_status)

    def tick(self):
        self.clock_lbl.set_text(time.strftime("%a %-d %b  %H:%M"))
        return True

    def set_focused(self, app_id):
        self.app_label.set_text(pretty_app(app_id) if app_id else "Finder")

    def refresh_status(self):
        def work():
            net = system.network()
            vol = system.volume()
            bat = system.battery()
            vpn = system.vpn_active()
            GLib.idle_add(self.apply, net, vol, bat, vpn)
        threading.Thread(target=work, daemon=True).start()
        return True

    def apply(self, net, vol, bat, vpn):
        def put(box, widget):
            c = box.get_first_child()
            while c:
                box.remove(c)
                c = box.get_first_child()
            box.append(widget)
        put(self.net, icons.icon({"wifi": "wifi", "eth": "eth"}.get(net[0], "wifi"),
                                 "#f4f6f5" if net[0] != "none" else "#8a8f8c", 15))
        put(self.vol, icons.icon("mute" if vol[1] else "volume", "#f4f6f5", 15))
        self.vpn.set_visible(vpn)
        if bat:
            row = Gtk.Box(spacing=4)
            lbl = Gtk.Label(label=f"{bat[0]}%")
            row.append(lbl)
            row.append(icons.icon("battery", "#f4f6f5", 17))
            put(self.bat, row)
            self.bat.set_visible(True)
        else:
            self.bat.set_visible(False)
        return False


class Dock:
    def __init__(self, app, shell):
        self.shell = shell
        self.win = layer_window(app, {LS.Edge.BOTTOM}, exclusive=88, margins={LS.Edge.BOTTOM: 8})
        self.box = Gtk.Box(spacing=6)
        self.box.add_css_class("dock")
        self.items = []     # (kind, desktop_id, dot widget)
        for kind, did in DOCK:
            info = system.app_by_id(did + ".desktop")
            if info is None:
                continue
            self._add(kind, did, info.get_display_name(), lambda i=info: i.launch([], None))
        sep = Gtk.Box()
        sep.add_css_class("dock-sep")
        self.box.append(sep)
        self._add("launcher", "", "Apps", lambda: shell.show_launcher("apps"), track=False)
        self.win.set_child(self.box)

    def _add(self, kind, did, name, action, track=True):
        btn = Gtk.Button()
        btn.add_css_class("dockbtn")
        btn.set_tooltip_text(name)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, halign=Gtk.Align.CENTER)
        col.append(icons.tile(kind, 50))
        dot = Gtk.Box(halign=Gtk.Align.CENTER)
        dot.add_css_class("dot")
        dot.set_opacity(0)
        col.append(dot)
        btn.set_child(col)
        btn.connect("clicked", lambda *_: self.click(did, action, track))
        self.box.append(btn)
        if track:
            self.items.append((did, dot))

    def click(self, did, action, track):
        if track:
            app_id = did if did else ""
            wins = [w for w in system.sway_windows() if self.match(w[0], did)]
            if wins:
                system.sway_msg(f'[con_id={wins[0][3]}]', "focus")
                return
        action()

    @staticmethod
    def match(win_app, did):
        w = (win_app or "").lower()
        base = did.replace("bastille-", "")
        return w == did or w.endswith("." + base) or w == base or w == "bastille-" + base

    def refresh(self, windows):
        for did, dot in self.items:
            dot.set_opacity(1 if any(self.match(w[0], did) for w in windows) else 0)
