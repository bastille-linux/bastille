"""Shared shell UI primitives: layer-shell windows, animated click-away overlays, dialogs."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell as LS

import icons

ALL_EDGES = {LS.Edge.TOP, LS.Edge.BOTTOM, LS.Edge.LEFT, LS.Edge.RIGHT}
CLOSE_MS = 150


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


def button(child=None, *classes, on_click=None, **kw):
    b = Gtk.Button(**kw)
    for c in classes:
        b.add_css_class(c)
    if child is not None:
        b.set_child(child)
    if on_click:
        b.connect("clicked", lambda *_: on_click())
    return b


def pill(text, *classes, on_click=None):
    b = Gtk.Button(label=text)
    b.add_css_class("pill")
    for c in classes:
        b.add_css_class(c)
    if on_click:
        b.connect("clicked", lambda *_: on_click())
    return b


def bounce(widget, ms=700):
    """Play the dock-style launch bounce once."""
    widget.add_css_class("bounce")
    GLib.timeout_add(ms, lambda: (widget.remove_css_class("bounce"), False)[1])


class Overlay:
    """Full-screen click-away layer with one animated panel.

    The panel and the click-away backdrop are *siblings* in a Gtk.Overlay, so a
    click on the panel can never reach the backdrop — buttons inside the panel
    always work, whatever gestures they or their parents use.
    """

    def __init__(self, app, panel, halign, valign, margins, on_hide=None, dim=False):
        self.win = layer_window(app, ALL_EDGES, layer=LS.Layer.OVERLAY, kb=LS.KeyboardMode.EXCLUSIVE, exclusive=-1)
        self.win.add_css_class("catcher")
        if dim:
            self.win.add_css_class("dim")
        self.on_hide = on_hide
        self.panel = panel
        self._tok = 0
        self._closing = False

        root = Gtk.Overlay()
        backdrop = Gtk.Box(hexpand=True, vexpand=True)
        click = Gtk.GestureClick()
        click.connect("pressed", lambda *_: self.hide())
        backdrop.add_controller(click)
        root.set_child(backdrop)

        panel.set_halign(halign)
        panel.set_valign(valign)
        panel.set_margin_top(margins[0])
        panel.set_margin_end(margins[1])
        panel.set_margin_bottom(margins[2])
        panel.set_margin_start(margins[3])
        root.add_overlay(panel)
        self.win.set_child(root)

        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key)
        self.win.add_controller(keys)

    def _on_key(self, _c, keyval, *_):
        if keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def visible(self):
        return self.win.get_visible() and not self._closing

    def show(self):
        self._tok += 1
        self._closing = False
        self.panel.remove_css_class("closing")
        self.panel.remove_css_class("popin")
        self.win.present()
        self.panel.add_css_class("popin")

    def hide(self):
        if not self.win.get_visible() or self._closing:
            return
        self._closing = True
        self.panel.add_css_class("closing")
        tok = self._tok
        GLib.timeout_add(CLOSE_MS, self._finish, tok)

    def hide_now(self):
        self._tok += 1
        self._finish(self._tok)

    def _finish(self, tok):
        if tok != self._tok:
            return False        # re-opened while the fade-out was running
        self._closing = False
        self.win.set_visible(False)
        self.panel.remove_css_class("closing")
        self.panel.remove_css_class("popin")
        if self.on_hide:
            self.on_hide()
        return False


class Dialog:
    """Centered modal card (confirmations, About, Force Quit). Reuses one Overlay."""

    def __init__(self, app):
        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.card.add_css_class("dialog")
        self.card.set_size_request(380, -1)
        self.overlay = Overlay(app, self.card, Gtk.Align.CENTER, Gtk.Align.CENTER, (0, 0, 0, 0), dim=True)

    def visible(self):
        return self.overlay.visible()

    def hide(self):
        self.overlay.hide()

    def _reset(self, width=380):
        clear_children(self.card)
        self.card.set_size_request(width, -1)

    def _buttons(self, row_items):
        row = Gtk.Box(spacing=8, halign=Gtk.Align.END)
        for it in row_items:
            row.append(it)
        self.card.append(row)

    def confirm(self, title, body, label, action, destructive=False, glyph="power"):
        self._reset()
        head = Gtk.Box(spacing=14)
        head.append(icons.icon(glyph, "#f4f6f5", 30, 1.8))
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        v.append(lab(title, "title", wrap=True))
        v.append(lab(body, "dim", wrap=True, max_width_chars=38))
        head.append(v)
        self.card.append(head)
        self._buttons([
            pill("Cancel", on_click=self.hide),
            pill(label, "danger" if destructive else "pri",
                 on_click=lambda: (self.hide(), GLib.idle_add(lambda: (action(), False)[1]))),
        ])
        self.overlay.show()

    def content(self, widget, buttons=(), width=380):
        self._reset(width)
        self.card.append(widget)
        if buttons:
            self._buttons(buttons)
        self.overlay.show()
