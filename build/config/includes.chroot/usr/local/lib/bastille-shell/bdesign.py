"""Bastille app design kit — the flat dark "Settings" look shared by Bastille apps.

Palette and metrics follow the Settings mockup: near-black surfaces, 8px cards,
icon-chip rows, uppercase section titles, status badges, blue accent.

    import bdesign
    bdesign.install()                    # once the Gtk display exists
    bdesign.enable_maximize(window)      # double-click the top bar to fill the screen
"""

import json
import os
import subprocess
import threading

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gdk, GLib, Gtk

try:
    import icons
except ImportError:  # pragma: no cover - icons live beside this module
    icons = None

# tone -> (chip background, glyph colour)
TONES = {
    "gn": ("rgba(0,147,0,0.12)", "#3fb950"),
    "bl": ("rgba(42,120,214,0.14)", "#6aa8f0"),
    "am": ("rgba(250,178,25,0.12)", "#fab219"),
    "rd": ("rgba(208,59,59,0.12)", "#f47070"),
    "pu": ("rgba(147,51,234,0.16)", "#b57bff"),
    "":   ("rgba(255,255,255,0.06)", "#a9a79f"),
}

CSS = """
window.b2, window.b2.background, window.bapp.b2 { background: #0b0b0b; color: #f0efec; }
.b2 label { color: #f0efec; }
.b2 .muted, .b2 .dim, .b2 .dim-label { color: #898781; }
.b2 headerbar { background: #151515; border-bottom: 1px solid rgba(255,255,255,0.10);
                box-shadow: none; min-height: 40px; color: #898781; }
.b2 .b2-titlebar { background: #151515; border-bottom: 1px solid rgba(255,255,255,0.10); min-height: 40px; }
.b2 .b2-title { font-size: 13px; font-weight: 500; color: #898781; }

.b2 windowcontrols { padding: 0; }
.b2 windowcontrols > button, .b2 windowcontrols button.titlebutton {
    min-width: 12px; min-height: 12px; padding: 0; margin: 0 4px; border-radius: 50%;
    background-image: none; border: 1px solid rgba(0,0,0,0.25); box-shadow: none; outline: none; }
.b2 windowcontrols > button > image, .b2 windowcontrols button.titlebutton > image {
    opacity: 0; -gtk-icon-size: 8px; min-width: 0; min-height: 0; margin: 0; padding: 0; }
.b2 windowcontrols > button.close { background: #ff5f57; }
.b2 windowcontrols > button.minimize { background: #febc2e; }
.b2 windowcontrols > button.maximize { background: #28c840; }

.b2-nav { background: #151515; border-right: 1px solid rgba(255,255,255,0.10); padding: 10px 8px; }
.b2-nav scrolledwindow, .b2-nav viewport, .b2-nav list { background: transparent; }
.b2-search { background: #1a1a19; border: 1px solid rgba(255,255,255,0.10); border-radius: 6px;
             min-height: 30px; box-shadow: none; color: #f0efec; }
.b2-navlabel { font-size: 10px; font-weight: 600; letter-spacing: 0.06em; color: #898781;
               padding: 12px 8px 4px 8px; }
.b2-navitem { border-radius: 8px; padding: 0; margin: 1px 0; background: transparent; }
.b2-navitem:hover { background: #1a1a19; }
.b2-navitem:selected, .b2-navitem.active { background: rgba(42,120,214,0.14); }
.b2-navitem label { font-size: 13px; color: #c3c2b7; }
.b2-navitem:selected label { color: #f0efec; }

.b2-panel { background: #0b0b0b; }
.b2-panel-header { padding: 20px 0 16px 0; border-bottom: 1px solid rgba(255,255,255,0.10); }
.b2-panel-title { font-size: 18px; font-weight: 600; color: #f0efec; }
.b2-panel-sub { font-size: 12px; color: #898781; }
.b2-section-title { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; color: #898781; }

.b2-card { background: #151515; border: 1px solid rgba(255,255,255,0.10); border-radius: 8px; }
.b2-row { padding: 11px 14px; border-bottom: 1px solid rgba(255,255,255,0.10); }
.b2-row:last-child { border-bottom: none; }
.b2-row.click:hover { background: #1a1a19; }
.b2-chip { border-radius: 6px; min-width: 28px; min-height: 28px; }
.chip-gn { background: rgba(0,147,0,0.12); } .chip-bl { background: rgba(42,120,214,0.14); }
.chip-am { background: rgba(250,178,25,0.12); } .chip-rd { background: rgba(208,59,59,0.12); }
.chip-pu { background: rgba(147,51,234,0.16); } .chip-n { background: rgba(255,255,255,0.06); }
.b2-label { font-size: 13px; color: #f0efec; }
.b2-desc { font-size: 11px; color: #898781; }
.b2-mono { font-family: monospace; }

.b2-badge { font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 4px; }
.b2-badge.ok   { background: rgba(0,147,0,0.14);    color: #3fb950; border: 1px solid rgba(0,147,0,0.25); }
.b2-badge.warn { background: rgba(250,178,25,0.14); color: #fab219; border: 1px solid rgba(250,178,25,0.25); }
.b2-badge.off  { background: rgba(255,255,255,0.07); color: #898781; border: 1px solid rgba(255,255,255,0.10); }
.b2-badge.crit { background: rgba(208,59,59,0.14);  color: #f47070; border: 1px solid rgba(208,59,59,0.30); }
.b2-badge.run  { background: rgba(42,120,214,0.14); color: #6aa8f0; border: 1px solid rgba(42,120,214,0.30); }

.b2 switch { background: #1e1e1d; border: 1px solid rgba(255,255,255,0.10); border-radius: 11px;
             min-width: 40px; min-height: 22px; box-shadow: none; outline: none; }
.b2 switch:checked { background: #009300; border-color: #009300; }
.b2 switch slider { background: #ffffff; border-radius: 8px; min-width: 16px; min-height: 16px;
                    margin: 2px; border: none; box-shadow: none; }

.b2 button.b2-btn { min-height: 28px; padding: 0 14px; border-radius: 6px; background: #1a1a19;
                    border: 1px solid rgba(255,255,255,0.10); color: #f0efec; font-size: 12px;
                    font-weight: 500; box-shadow: none; background-image: none; }
.b2 button.b2-btn:hover { background: #222221; }
.b2 button.b2-btn.pri { background: #2a78d6; border-color: #2a78d6; color: #ffffff; }
.b2 button.b2-btn.pri:hover { background: #3385e3; }
.b2 button.b2-btn.dng { background: rgba(208,59,59,0.14); border-color: rgba(208,59,59,0.30); color: #f47070; }
.b2 button.b2-btn:disabled { opacity: 0.45; }

.b2 dropdown > button, .b2 dropdown button.toggle { background: #1a1a19; border: 1px solid rgba(255,255,255,0.10);
                                                    border-radius: 6px; min-height: 28px; box-shadow: none;
                                                    background-image: none; color: #f0efec; font-size: 12px; }
.b2 entry, .b2 passwordentry, .b2 spinbutton { background: #1a1a19; color: #f0efec; border-radius: 6px;
                                                border: 1px solid rgba(255,255,255,0.10); box-shadow: none;
                                                min-height: 28px; }
.b2 entry:focus-within { border-color: #2a78d6; }
.b2 scale trough { background: #1e1e1d; border-radius: 4px; min-height: 6px; }
.b2 scale highlight { background: #2a78d6; border-radius: 4px; }
.b2 scale slider { background: #ffffff; min-width: 16px; min-height: 16px; border-radius: 8px; box-shadow: none; }
.b2 progressbar trough { background: #1e1e1d; border-radius: 4px; min-height: 6px; }
.b2 progressbar progress { background: #2a78d6; border-radius: 4px; min-height: 6px; }
.b2 textview, .b2 textview text { background: #1a1a19; color: #f0efec; font-family: monospace; font-size: 12px; }
.b2 scrolledwindow, .b2 viewport { background: transparent; }

/* libadwaita pages that have not been rebuilt yet pick up the same card look */
.b2 list.boxed-list, .b2 .boxed-list, .b2 list.card { background: #151515; border-radius: 8px;
                                                        border: 1px solid rgba(255,255,255,0.10); box-shadow: none; }
.b2 list.boxed-list > row { background: transparent; }
.b2 list.boxed-list > row:not(:last-child) { border-bottom: 1px solid rgba(255,255,255,0.10); }
.b2 preferencesgroup > box > label.heading { font-size: 11px; font-weight: 600; letter-spacing: 0.06em;
                                              color: #898781; }
.b2 row.activatable:hover { background: #1a1a19; }
"""

_installed = False


def install():
    """Load the design kit stylesheet (idempotent) and force the dark scheme."""
    global _installed
    if _installed:
        return
    css = Gtk.CssProvider()
    try:
        css.load_from_string(CSS)
    except AttributeError:
        css.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                              Gtk.STYLE_PROVIDER_PRIORITY_USER + 10)
    _installed = True


# ── widgets ───────────────────────────────────────────────────────────────────

def label(text, *classes, wrap=False, xalign=0.0):
    l = Gtk.Label(label=text, xalign=xalign, wrap=wrap)
    for c in classes:
        l.add_css_class(c)
    return l


def badge(text, kind="off"):
    b = Gtk.Label(label=text)
    b.add_css_class("b2-badge")
    b.add_css_class(kind)
    b.set_valign(Gtk.Align.CENTER)
    return b


def button(text, on_click=None, kind=""):
    b = Gtk.Button(label=text)
    b.add_css_class("b2-btn")
    if kind:
        b.add_css_class(kind)
    b.set_valign(Gtk.Align.CENTER)
    if on_click:
        b.connect("clicked", lambda *_: on_click())
    return b


def toggle(active=False, on_change=None):
    sw = Gtk.Switch()
    sw.set_valign(Gtk.Align.CENTER)
    sw.set_active(bool(active))
    if on_change:
        sw.connect("state-set", lambda s, state: (on_change(state), False)[1])
    return sw


def select(options, active=0, on_change=None):
    dd = Gtk.DropDown.new_from_strings(list(options))
    dd.set_selected(max(0, min(active, len(options) - 1)))
    dd.set_valign(Gtk.Align.CENTER)
    if on_change:
        dd.connect("notify::selected", lambda d, _p: on_change(d.get_selected()))
    return dd


def slider(value, lo=0, hi=100, on_change=None, width=180):
    sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, 1)
    sc.set_value(value)
    sc.set_draw_value(False)
    sc.set_size_request(width, -1)
    sc.set_valign(Gtk.Align.CENTER)
    if on_change:
        sc.connect("value-changed", lambda s: on_change(int(s.get_value())))
    return sc


def chip(glyph, tone=""):
    _, fg = TONES.get(tone, TONES[""])
    box = Gtk.Box()
    box.add_css_class("b2-chip")
    box.add_css_class("chip-" + (tone or "n"))
    box.set_size_request(28, 28)
    box.set_halign(Gtk.Align.CENTER)
    box.set_valign(Gtk.Align.CENTER)
    if icons is not None:
        ic = icons.icon(glyph, fg, 15, 1.9)
        ic.set_hexpand(True)      # a horizontal Box packs at the start; expand so it centres
        ic.set_vexpand(True)
        box.append(ic)
    return box


class Row(Gtk.Box):
    """Icon chip + label/description + any number of suffix widgets."""

    def __init__(self, glyph, tone, title, desc="", *suffix, on_click=None):
        super().__init__(spacing=12)
        self.add_css_class("b2-row")
        self.append(chip(glyph, tone))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        self.title_lbl = label(title, "b2-label", wrap=True)
        text.append(self.title_lbl)
        self.desc_lbl = label(desc, "b2-desc", wrap=True)
        self.desc_lbl.set_visible(bool(desc))
        text.append(self.desc_lbl)
        self.append(text)
        for w in suffix:
            self.append(w)
        if on_click:
            self.add_css_class("click")
            g = Gtk.GestureClick()
            g.connect("released", lambda *_: on_click())
            self.add_controller(g)
            if icons is not None:
                self.append(icons.icon("chev", "#898781", 14))

    def set_desc(self, text):
        self.desc_lbl.set_text(text)
        self.desc_lbl.set_visible(bool(text))


class Card(Gtk.Box):
    def __init__(self, *rows):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("b2-card")
        self.set_overflow(Gtk.Overflow.HIDDEN)
        for r in rows:
            self.append(r)


def section(title, *rows):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    if title:
        box.append(label(title.upper(), "b2-section-title"))
    box.append(Card(*rows) if rows and not isinstance(rows[0], Card) else rows[0])
    return box


class Page(Gtk.ScrolledWindow):
    """Panel: header (title + subtitle) and a vertical stack of sections."""

    def __init__(self, title="", sub=""):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add_css_class("b2-panel")
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.body.set_margin_start(24)
        self.body.set_margin_end(24)
        self.body.set_margin_bottom(24)
        head = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        head.add_css_class("b2-panel-header")
        head.append(label(title, "b2-panel-title"))
        if sub:
            head.append(label(sub, "b2-panel-sub", wrap=True))
        self.body.append(head)
        self.set_child(self.body)

    def add(self, widget):
        self.body.append(widget)
        return widget

    def section(self, title, *rows):
        return self.add(section(title, *rows))


# ── background work ───────────────────────────────────────────────────────────

def sh(cmd, timeout=6):
    """Run a command (list or shell string); returns stdout stripped, '' on any failure."""
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def read(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def bg(work, done=None):
    """Run work() in a thread and deliver its result to done(result) on the main loop."""
    def run():
        try:
            res = work()
        except Exception:  # noqa: BLE001
            res = None
        if done:
            GLib.idle_add(lambda: (done(res), False)[1])
    threading.Thread(target=run, daemon=True).start()


# ── double-click the top bar to maximise (fill the usable screen, not fullscreen) ─

_NO_TOGGLE = (Gtk.Button, Gtk.Editable, Gtk.Switch, Gtk.Scale, Gtk.DropDown, Gtk.TextView,
              Gtk.SpinButton, Gtk.ListBoxRow, Gtk.Popover)


def _sway(*args):
    try:
        r = subprocess.run(["swaymsg", *args], capture_output=True, text=True, timeout=3)
        return r.stdout
    except Exception:  # noqa: BLE001
        return ""


def _find_own(node, pid):
    """Best sway container for this process: the focused one, else the first match."""
    found = []

    def walk(n):
        if n.get("pid") == pid and n.get("type") in ("con", "floating_con") and not n.get("nodes"):
            found.append(n)
        for c in n.get("nodes", []) + n.get("floating_nodes", []):
            walk(c)
    walk(node)
    return next((n for n in found if n.get("focused")), found[0] if found else None)


def toggle_maximize(win):
    try:
        tree = json.loads(_sway("-t", "get_tree", "-r") or "{}")
        node = _find_own(tree, os.getpid())
        if node is None:
            return
        ws = next((w for w in json.loads(_sway("-t", "get_workspaces", "-r") or "[]") if w.get("focused")), None)
        if ws is None:
            return
        area, rect = ws["rect"], node["rect"]
        full = abs(rect["width"] - area["width"]) <= 4 and abs(rect["height"] - area["height"]) <= 4
        sel = f"[con_id={node['id']}]"
        if full:
            x, y, w, h = getattr(win, "_b2_prev", (area["x"] + 60, area["y"] + 40,
                                                      int(area["width"] * 0.7), int(area["height"] * 0.75)))
            _sway(sel, f"floating enable, resize set {w} {h}, move absolute position {x} {y}")
        else:
            win._b2_prev = (rect["x"], rect["y"], rect["width"], rect["height"])
            _sway(sel, f"floating enable, move absolute position {area['x']} {area['y']}, "
                       f"resize set {area['width']} {area['height']}")
    except Exception:  # noqa: BLE001
        pass


def enable_maximize(win, zone=48):
    """Double-clicking empty space in the top `zone` px toggles maximise/restore."""
    g = Gtk.GestureClick()
    g.set_button(1)
    g.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

    def pressed(gesture, n_press, x, y):
        if n_press != 2 or y > zone:
            return
        w = win.pick(x, y, Gtk.PickFlags.DEFAULT)
        while w is not None and w is not win:
            if isinstance(w, _NO_TOGGLE):
                return
            w = w.get_parent()
        GLib.idle_add(lambda: (toggle_maximize(win), False)[1])

    g.connect("pressed", pressed)
    win.add_controller(g)
