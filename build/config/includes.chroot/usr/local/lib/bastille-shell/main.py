"""bastille-shell — menu bar, dock, launcher, notification centre and control centre for Sway."""

import os
import sys

# The wrapper preloads gtk4-layer-shell for *this* process only; apps we start must not inherit it.
os.environ.pop("LD_PRELOAD", None)


def _extend_data_dirs():
    """Make Flatpak-installed apps (and their icons) visible to Gio/GTK before either reads XDG_DATA_DIRS."""
    parts = (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    for extra in ("/var/lib/flatpak/exports/share", os.path.expanduser("~/.local/share/flatpak/exports/share")):
        if extra not in parts:
            parts.append(extra)
    os.environ["XDG_DATA_DIRS"] = ":".join(parts)


_extend_data_dirs()

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gdk, Gio, GLib, Gtk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import system  # noqa: E402
from bar import Bar, Dock  # noqa: E402
from center import ControlCenter, NotificationCenter, Toasts  # noqa: E402
from launcher import Launcher  # noqa: E402
from menus import AppleMenu  # noqa: E402
from notifyd import Notifyd  # noqa: E402
from theme import CSS  # noqa: E402

APP_ID = "org.bastilleos.Shell"

try:    # the shell has no visible stderr: keep tracebacks in ~/.cache/bastille-shell.log
    sys.stderr = open(system.LOG, "a", buffering=1)
except Exception:  # noqa: BLE001
    pass


class Shell(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.ready = False
        self._pending = GLib.SOURCE_REMOVE

    def do_startup(self):
        Gtk.Application.do_startup(self)
        css = Gtk.CssProvider()
        css.load_from_string(CSS) if hasattr(css, "load_from_string") else css.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.hold()
        self.toasts = Toasts(self)
        self.notifyd = Notifyd(lambda item, show: self.toasts.push(item) if show else None)
        self.notifyd.dnd = system.state_load("dnd.json", {}).get("on", False)
        self.bar = Bar(self, self)
        self.dock = Dock(self, self)
        self.launcher = Launcher(self, self)
        self.nc = NotificationCenter(self, self)
        self.cc = ControlCenter(self, self)
        self.apple = AppleMenu(self, self)
        self.bar.win.present()
        self.dock.win.present()
        self.ready = True
        self.sync()
        system.sway_subscribe(self.queue_sync)

    def do_command_line(self, cl):
        try:
            self.run_command(cl.get_arguments()[1:])
        except Exception:  # noqa: BLE001  never leave the caller hanging; the traceback goes to the log
            import traceback
            traceback.print_exc()
        return 0

    def run_command(self, args):
        if not self.ready:
            self.activate()
        a = args[0] if args else ""
        if a == "--launcher":
            self.show_launcher(args[1] if len(args) > 1 else "search", args[2] if len(args) > 2 else "")
        elif a == "--notifications":
            self.toggle("center")
        elif a == "--control":
            self.show_control(args[1] if len(args) > 1 else "main")
        elif a == "--wifi":
            self.show_control("wifi")
        elif a == "--bluetooth":
            self.show_control("bt")
        elif a == "--apple-menu":
            self.toggle("apple")
        elif a == "--about":
            self.close_panels()
            self.apple.about()
        elif a == "--force-quit":
            self.show_force_quit()
        elif a == "--gallery":
            self.close_panels()
            self.nc.gallery.show()
        elif a == "--edit-controls":
            self.close_panels()
            self.cc.show("edit")
        elif a == "--edit-widgets":
            self.close_panels()
            self.nc.show(editing=True)
        elif a == "--dnd":
            self.toggle_dnd()
        elif a == "--notify":
            self.notifyd.add(args[1] if len(args) > 1 else "Bastille", args[2] if len(args) > 2 else "Test",
                             args[3] if len(args) > 3 else "")
        elif a == "--close":
            self.close_panels()

    def do_activate(self):
        pass

    # ── sway state ────────────────────────────────────────────────────────────
    def queue_sync(self):
        if self._pending == GLib.SOURCE_REMOVE:
            self._pending = GLib.timeout_add(120, self._sync_once)

    def _sync_once(self):
        self._pending = GLib.SOURCE_REMOVE
        self.sync()
        return False

    def sync(self):
        wins = system.sway_windows()
        self.dock.refresh(wins)
        foc = next((w for w in wins if w[2]), None)
        self.bar.set_focused(foc[0] if foc else "")

    # ── panels ───────────────────────────────────────────────────────────────
    def close_panels(self):
        for p in (self.launcher, self.nc, self.cc, self.apple):
            if p.visible():
                p.hide()
        self.nc.gallery.overlay.hide()

    def show_launcher(self, mode="search", query=""):
        if self.launcher.visible() and self.launcher.mode == mode:
            self.launcher.hide()
            return
        self.close_panels()
        self.launcher.show(mode)
        if query:
            self.launcher.entry.set_text(query)

    def toggle(self, which):
        panel = {"center": self.nc, "control": self.cc, "apple": self.apple}[which]
        was = panel.visible()
        self.close_panels()
        if not was:
            panel.show()

    def show_control(self, page="main"):
        was = self.cc.visible() and self.cc.page == page
        self.close_panels()
        if not was:
            self.cc.show(page)

    def show_force_quit(self):
        self.close_panels()
        self.apple.force_quit()

    def toggle_dnd(self):
        self.notifyd.dnd = not self.notifyd.dnd
        system.state_save("dnd.json", {"on": self.notifyd.dnd})


if __name__ == "__main__":
    sys.exit(Shell().run(sys.argv))
