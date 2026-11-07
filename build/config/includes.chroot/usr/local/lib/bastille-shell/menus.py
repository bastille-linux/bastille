"""The shield menu (Apple-menu equivalent) plus its dialogs: About, Force Quit, power confirmations."""

import os

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gtk

import icons
import system
from ui import Dialog, Overlay, clear_children, lab, pill


def sep():
    s = Gtk.Box()
    s.add_css_class("menusep")
    return s


class AppleMenu:
    def __init__(self, app, shell):
        self.shell = shell
        self.dialog = Dialog(app)
        self.panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.panel.add_css_class("menu")
        self.panel.set_size_request(270, -1)
        self.overlay = Overlay(app, self.panel, Gtk.Align.START, Gtk.Align.START, (30, 0, 0, 8))
        self.recent_open = False

    def visible(self):
        return self.overlay.visible() or self.dialog.visible()

    def hide(self):
        self.overlay.hide()
        self.dialog.hide()

    def show(self):
        self.recent_open = False
        self.build()
        self.overlay.show()

    # ── building ──────────────────────────────────────────────────────────────
    def item(self, text, action, hint="", close=True, icon=None):
        b = Gtk.Button()
        b.add_css_class("menuitem")
        row = Gtk.Box(spacing=8)
        if icon:
            row.append(icons.icon(icon, "#f4f6f5", 14, 1.9))
        row.append(lab(text, hexpand=True))
        if hint:
            row.append(lab(hint, "hint"))

        def go(*_):
            if close:
                self.overlay.hide()
            GLib.idle_add(lambda: (action(), False)[1])
        b.set_child(row)
        b.connect("clicked", go)
        return b

    def build(self):
        clear_children(self.panel)
        sh = self.shell
        user = GLib.get_real_name()
        if not user or user == "Unknown":
            user = GLib.get_user_name()
        add = self.panel.append
        add(self.item("About This Bastille", self.about))
        add(sep())
        add(self.item("System Settings…", lambda: system.spawn(["bastille-settings"]), icon="gear"))
        add(self.item("App Store…", lambda: system.spawn(["bastille-store"]), icon="store"))
        add(sep())
        add(self.recent_row())
        add(self.recent_list())
        add(sep())
        add(self.item("Force Quit…", self.force_quit, "Super+Alt+Esc"))
        add(sep())
        add(self.item("Sleep", self.sleep))
        add(self.item("Restart…", lambda: self.dialog.confirm(
            "Restart now?", "Open apps will be closed and anything unsaved will be lost.", "Restart",
            lambda: system.spawn(["reboot"]), destructive=True, glyph="restart"), close=True))
        add(self.item("Shut Down…", lambda: self.dialog.confirm(
            "Shut down now?", "Open apps will be closed and anything unsaved will be lost.", "Shut Down",
            lambda: system.spawn(["poweroff"]), destructive=True, glyph="power")))
        add(sep())
        add(self.item("Lock Screen", lambda: system.spawn(["bastille-lock"]), "Super+Esc"))
        add(self.item(f"Log Out {user}…", lambda: self.dialog.confirm(
            f"Log out {user}?", "Open apps will be closed and anything unsaved will be lost.", "Log Out",
            lambda: system.sway_msg("exit"), destructive=True, glyph="x")))

    def recent_row(self):
        b = Gtk.Button()
        b.add_css_class("menuitem")
        row = Gtk.Box(spacing=8)
        row.append(lab("Recent Items", hexpand=True))
        self.chev = icons.icon("chev", "#f4f6f5", 12, 2.2)
        self.chev.add_css_class("chev")
        row.append(self.chev)
        b.set_child(row)
        b.connect("clicked", lambda *_: self.toggle_recent())
        return b

    def recent_list(self):
        self.rev = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN, transition_duration=180)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        col.add_css_class("submenu")
        apps = system.recent_apps(5)
        for a in apps:
            col.append(self.item(a.get_display_name(), lambda a=a: system.launch(a)))
        files = self.recent_files(5)
        if apps and files:
            col.append(sep())
        for name, uri in files:
            col.append(self.item(name, lambda u=uri: system.spawn(["xdg-open", u])))
        if not apps and not files:
            col.append(lab("No recent items", "dim", margin_start=12, margin_top=4, margin_bottom=4))
        self.rev.set_child(col)
        return self.rev

    @staticmethod
    def recent_files(n):
        try:
            items = Gtk.RecentManager.get_default().get_items()
            items.sort(key=lambda i: i.get_modified().to_unix() if i.get_modified() else 0, reverse=True)
            return [(i.get_display_name(), i.get_uri()) for i in items[:n]]
        except Exception:  # noqa: BLE001
            return []

    def toggle_recent(self):
        self.recent_open = not self.recent_open
        self.rev.set_reveal_child(self.recent_open)
        (self.chev.add_css_class if self.recent_open else self.chev.remove_css_class)("open")

    # ── actions ───────────────────────────────────────────────────────────────
    def sleep(self):
        system.spawn(["swaylock", "-f"])

    def about(self):
        d = system.about_info()
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.CENTER)
        col.append(icons.badge("shield", "#4f8fd4", "#1f4f93", 72, 24))
        col.append(lab("Bastille OS", "title", xalign=0.5))
        col.append(lab(f"Version {d['version']}", "dim", xalign=0.5))
        grid = Gtk.Grid(column_spacing=18, row_spacing=6, halign=Gtk.Align.CENTER)
        grid.set_margin_top(10)
        grid.add_css_class("kv")
        for i, (k, v) in enumerate((("Processor", d["cpu"]), ("Memory", d["memory"]), ("Kernel", d["kernel"]),
                                    ("Hostname", d["host"]), ("Architecture", d["arch"]))):
            grid.attach(lab(k, "dim", xalign=1.0), 0, i, 1, 1)
            grid.attach(lab(v, xalign=0.0, max_width_chars=30, ellipsize=3), 1, i, 1, 1)
        col.append(grid)
        self.dialog.content(col, [pill("More Info…", on_click=lambda: (self.dialog.hide(),
                                                                       system.spawn(["bastille-settings"]))),
                                  pill("Close", "pri", on_click=self.dialog.hide)], width=400)

    def force_quit(self):
        wins = [w for w in system.sway_windows_full() if w["pid"] != os.getpid()]
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        col.append(lab("Force Quit Applications", "title"))
        col.append(lab("If an app isn’t responding, select it and choose Force Quit.", "dim", wrap=True,
                       max_width_chars=44))
        self._fq_sel = None
        rows = []
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        list_box.add_css_class("group")
        if not wins:
            list_box.append(lab("No applications are open.", "dim", margin_top=14, margin_bottom=14,
                                xalign=0.5))
        for w in wins:
            b = Gtk.Button()
            b.add_css_class("fqrow")
            name = system.app_name_for(w["app"]) or w["app"]
            row = Gtk.Box(spacing=10)
            row.append(icons.tile("generic", 24))
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            v.append(lab(name, ellipsize=3, max_width_chars=34))
            if w["title"] and w["title"] != name:
                v.append(lab(w["title"], "dim", "small", ellipsize=3, max_width_chars=44))
            row.append(v)
            b.set_child(row)

            def pick(_b, w=w, b=b):
                self._fq_sel = w
                for r in rows:
                    r.remove_css_class("sel")
                b.add_css_class("sel")
            b.connect("clicked", pick)
            rows.append(b)
            list_box.append(b)
        sc = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, propagate_natural_height=True,
                                max_content_height=260)
        sc.set_child(list_box)
        col.append(sc)

        def kill():
            if self._fq_sel:
                system.force_quit(self._fq_sel["pid"])
            self.dialog.hide()
        self.dialog.content(col, [pill("Cancel", on_click=self.dialog.hide),
                                  pill("Force Quit", "danger", on_click=kill)], width=430)
