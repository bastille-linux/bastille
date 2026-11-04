"""Top menu bar and bottom dock."""

import threading
import time

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import GLib, Gtk, Gtk4LayerShell as LS

import icons
import system
from ui import bounce, layer_window  # noqa: F401  (layer_window re-exported for older imports)

DOCK = [("files", "bastille-files"), ("browser", "bastille-browser"), ("terminal", "bastille-terminal"),
        ("mail", "bastille-mail"), ("messages", "bastille-messages"), ("notes", "bastille-notes"),
        ("calendar", "bastille-calendar"), ("music", "bastille-music"), ("weather", "bastille-weather"),
        ("store", "bastille-store"), ("settings", "bastille-settings")]


def pretty_app(app_id):
    if not app_id:
        return "Desktop"
    known = system.app_name_for(app_id)
    if known:
        return known
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
        logo.set_tooltip_text("Bastille")
        logo.connect("clicked", lambda *_: shell.toggle("apple"))
        box.append(logo)

        self.app_label = Gtk.Label(label="Desktop")
        self.app_label.add_css_class("app")
        self.app_label.set_margin_start(6)
        self.app_label.set_margin_end(10)
        box.append(self.app_label)
        # Keep these compact and functional.  They used to be labels that looked
        # like menu items but swallowed clicks without doing anything.
        for name, action in ((
                ("File", lambda: shell.show_launcher("files")),
                ("Edit", lambda: shell.show_launcher("actions")),
                ("View", lambda: shell.toggle("center")),
                ("Window", lambda: shell.toggle("control")))):
            menu = Gtk.Button(label=name)
            menu.add_css_class("barbtn")
            menu.add_css_class("dim")
            menu.set_margin_start(2)
            menu.set_margin_end(2)
            menu.connect("clicked", lambda _button, action=action: action())
            box.append(menu)

        spacer = Gtk.Box(hexpand=True)
        box.append(spacer)

        self.vpn = icons.icon("vpn", "#f4f6f5", 15)
        self.vpn.set_margin_start(6)
        self.vpn.set_margin_end(6)
        box.append(self.vpn)
        self.vpn.set_visible(False)
        # status items open the matching page of the control centre
        self.bt = self.status_button(box, "bt")
        self.net = self.status_button(box, "wifi")
        self.vol = self.status_button(box, "main")
        self.bat = self.status_button(box, "main", spacing=4)
        self.bt.btn.set_visible(False)
        self.bat.btn.set_visible(False)

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

    def status_button(self, box, page, spacing=0):
        """Flat bar button that opens control-centre `page`; returns the inner Box to fill with an icon."""
        inner = Gtk.Box(spacing=spacing)
        b = Gtk.Button()
        b.add_css_class("barbtn")
        b.set_child(inner)
        b.connect("clicked", lambda *_: self.shell.show_control(page))
        box.append(b)
        inner.btn = b
        return inner

    def tick(self):
        self.clock_lbl.set_text(time.strftime("%a %-d %b  %H:%M"))
        return True

    def set_focused(self, app_id):
        self.app_label.set_text(pretty_app(app_id) if app_id else "Desktop")

    def refresh_status(self):
        def work():
            net = system.network()
            vol = system.volume()
            bat = system.battery()
            vpn = system.vpn_active()
            bt = system.bt_state()
            GLib.idle_add(self.apply, net, vol, bat, vpn, bt)
        threading.Thread(target=work, daemon=True).start()
        return True

    def apply(self, net, vol, bat, vpn, bt="blocked"):
        def put(box, widget):
            c = box.get_first_child()
            while c:
                box.remove(c)
                c = box.get_first_child()
            box.append(widget)
        put(self.net, icons.icon({"wifi": "wifi", "eth": "eth"}.get(net[0], "wifi"),
                                 "#f4f6f5" if net[0] != "none" else "#8a8f8c", 15))
        put(self.vol, icons.icon("mute" if vol[1] else "volume", "#f4f6f5", 15))
        put(self.bt, icons.icon("bt", "#f4f6f5", 15))
        self.bt.btn.set_visible(bt == "on")
        self.vpn.set_visible(vpn)
        if bat:
            row = Gtk.Box(spacing=4)
            lbl = Gtk.Label(label=f"{bat[0]}%")
            row.append(lbl)
            row.append(icons.icon("battery", "#f4f6f5", 17))
            put(self.bat, row)
            self.bat.btn.set_visible(True)
        else:
            self.bat.btn.set_visible(False)
        return False


class Dock:
    def __init__(self, app, shell):
        self.shell = shell
        self.win = layer_window(app, {LS.Edge.BOTTOM}, exclusive=80, margins={LS.Edge.BOTTOM: 6})
        self.box = Gtk.Box(spacing=6)
        self.box.add_css_class("dock")
        self.box.set_margin_top(18)       # headroom so hover-zoom and the launch bounce are not clipped
        self.box.set_valign(Gtk.Align.END)
        self.items = []     # (kind, desktop_id, dot widget)
        for kind, did in DOCK:
            info = system.app_by_id(did + ".desktop")
            if info is None:
                continue
            self._add(kind, did, info.get_display_name(), lambda i=info: system.launch(i))
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
        btn.connect("clicked", lambda b, *_: self.click(did, action, track, b))
        self.box.append(btn)
        if track:
            self.items.append((did, dot))

    def click(self, did, action, track, btn=None):
        if track:
            wins = [w for w in system.sway_windows() if self.match(w[0], did)]
            if wins:
                system.sway_msg(f'[con_id={wins[0][3]}]', "focus")
                return
            if btn is not None:
                bounce(btn)
        action()

    @staticmethod
    def match(win_app, did):
        w = (win_app or "").lower()
        base = did.replace("bastille-", "")
        return w == did or w.endswith("." + base) or w == base or w == "bastille-" + base

    def refresh(self, windows):
        for did, dot in self.items:
            dot.set_opacity(1 if any(self.match(w[0], did) for w in windows) else 0)
