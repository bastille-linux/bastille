"""Bastille app look — shared by Settings, App Store and Files so every window matches the shell.

Dark glass surfaces, rounded grouped cards, macOS-style traffic lights on the left, no stock GNOME chrome.
Usage:  appstyle.install()  once the Gtk display exists (Application.do_startup / activate).
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gdk, Gtk

CSS = """
@define-color window_bg_color #111513;
@define-color window_fg_color #f4f6f5;
@define-color view_bg_color transparent;
@define-color view_fg_color #f4f6f5;
@define-color headerbar_bg_color transparent;
@define-color headerbar_fg_color #f4f6f5;
@define-color card_bg_color rgba(255,255,255,0.07);
@define-color card_fg_color #f4f6f5;
@define-color popover_bg_color #1d2421;
@define-color dialog_bg_color #1d2421;
@define-color accent_bg_color #2a78d6;
@define-color accent_fg_color #ffffff;
@define-color accent_color #6fb0ff;
:root { --accent-bg-color: #2a78d6; --accent-color: #6fb0ff; --window-bg-color: #111513;
        --card-bg-color: rgba(255,255,255,0.07); --view-bg-color: transparent; }

window.bapp, window.bapp.background {
    background: linear-gradient(165deg, #1b2320 0%, #0f1311 100%); color: #f4f6f5; }
.bapp label { color: #f4f6f5; }
.bapp .dim, .bapp .dim-label, .bapp .subtitle { color: rgba(244,246,245,0.58); }

/* sidebar */
.bsidebar { background: rgba(255,255,255,0.045); border-right: 1px solid rgba(255,255,255,0.07); }
.bsidebar list, .bsidebar listview { background: transparent; }
.bsidebar row { border-radius: 9px; margin: 1px 8px; padding: 0; min-height: 0; background: transparent;
                transition: background 120ms ease; }
.bapp .bsidebar row.activatable:hover { background: rgba(255,255,255,0.07); }
.bapp .bsidebar row.activatable:selected, .bapp .bsidebar row.activatable:selected:hover,
.bapp .bsidebar row:selected { background: #2a78d6; }
.bapp .bsidebar row:selected label { color: #ffffff; }
.bsection { font-size: 11px; font-weight: 700; letter-spacing: 0.6px; color: rgba(244,246,245,0.45);
            margin: 14px 18px 4px 18px; }
.bsidebar searchentry, .bsidebar entry { background: rgba(255,255,255,0.09); border-radius: 9px; border: none;
                                          box-shadow: none; color: #f4f6f5; min-height: 30px; }
.usercard { padding: 10px 14px 6px 14px; }
.pagetitle { font-size: 22px; font-weight: 700; }
.bcontent { background: transparent; }

/* traffic lights */
.bapp windowcontrols { padding: 0; }
.bapp windowcontrols > button, .bapp windowcontrols button.titlebutton {
    min-width: 12px; min-height: 12px; padding: 0; margin: 0 4px; border-radius: 50%;
    background-image: none; border: 1px solid rgba(0,0,0,0.25); box-shadow: none; outline: none; }
.bapp windowcontrols > button > image, .bapp windowcontrols button.titlebutton > image {
    opacity: 0; -gtk-icon-size: 8px; min-width: 0; min-height: 0; margin: 0; padding: 0; }
.bapp windowcontrols > button.close { background: #ff5f57; }
.bapp windowcontrols > button.minimize { background: #febc2e; }
.bapp windowcontrols > button.maximize { background: #28c840; }
.bapp windowcontrols:hover > button > image { opacity: 0.55; }

/* grouped cards (libadwaita preferences groups, boxed lists) */
.bapp list.boxed-list, .bapp .boxed-list, .bapp list.card {
    background: rgba(255,255,255,0.065); border: 1px solid rgba(255,255,255,0.09); border-radius: 14px;
    box-shadow: none; }
.bapp list.boxed-list > row, .bapp .boxed-list > row { background: transparent; }
.bapp list.boxed-list > row:not(:last-child) { border-bottom: 1px solid rgba(255,255,255,0.07); }
.bapp row.activatable:hover { background: rgba(255,255,255,0.06); }
.bapp preferencesgroup > box > label.heading, .bapp .title-4 { font-weight: 700; }
.bapp scrolledwindow, .bapp viewport { background: transparent; }
.bapp stack, .bapp scrolledwindow > viewport { background: transparent; }
.bapp textview, .bapp textview text { background: rgba(0,0,0,0.25); color: #f4f6f5; border-radius: 10px; }
.bapp entry, .bapp spinbutton, .bapp row entry { background: rgba(255,255,255,0.09); color: #f4f6f5;
                                                  border-radius: 9px; border: 1px solid rgba(255,255,255,0.10);
                                                  box-shadow: none; }
.bapp button { border-radius: 9px; background-image: none; box-shadow: none; transition: background 120ms ease; }
.bapp button.pill { border-radius: 16px; padding: 4px 16px; background: rgba(255,255,255,0.12);
                    border: 1px solid rgba(255,255,255,0.12); }
.bapp button.pill:hover { background: rgba(255,255,255,0.2); }
.bapp button.suggested-action, .bapp button.pill.suggested-action { background: #2a78d6; color: #fff;
                                                                    border-color: #2a78d6; }
.bapp button.suggested-action:hover { background: #3a88e6; }
.bapp button.destructive-action { background: #d8453c; color: #fff; border-color: #d8453c; }
.bapp button.flat { background: transparent; border: none; }
.bapp button.flat:hover { background: rgba(255,255,255,0.10); }
.bapp switch { background: rgba(255,255,255,0.22); border-radius: 16px; min-width: 44px; min-height: 26px;
               border: none; box-shadow: none; outline: none; }
.bapp switch:checked { background: #2a78d6; }
.bapp switch slider { background: #fff; border-radius: 13px; min-width: 22px; min-height: 22px; margin: 2px;
                      border: none; box-shadow: 0 1px 3px rgba(0,0,0,0.4); }
.bapp stackswitcher button { padding: 3px 16px; }
.bapp stackswitcher button:checked { background: rgba(255,255,255,0.18); }
.bapp progressbar trough { background: rgba(255,255,255,0.14); border-radius: 4px; min-height: 6px; }
.bapp progressbar progress { background: #2a78d6; border-radius: 4px; min-height: 6px; }

/* store */
.appcard { background: rgba(255,255,255,0.065); border: 1px solid rgba(255,255,255,0.09); border-radius: 18px;
           padding: 12px; transition: background 140ms ease, transform 140ms ease; }
.appcard:hover { background: rgba(255,255,255,0.11); transform: translateY(-2px); }
.getbtn { background: rgba(42,120,214,0.22); color: #6fb0ff; border-radius: 15px; padding: 2px 16px;
          font-weight: 700; border: none; min-height: 26px; }
.getbtn:hover { background: rgba(42,120,214,0.4); }
.getbtn.open { background: rgba(255,255,255,0.12); color: #f4f6f5; }
.hero { border-radius: 22px; padding: 22px; }
.hero .getbtn { background: rgba(255,255,255,0.92); color: #123a78; }
.hero .getbtn:hover { background: #ffffff; }
.hero .getbtn.open { background: rgba(0,0,0,0.25); color: #ffffff; }
.hero label { color: #ffffff; }
.chip { background: rgba(255,255,255,0.09); border-radius: 12px; padding: 2px 10px; font-size: 11px; }
.fade-in { animation-name: fadein; animation-duration: 220ms; animation-fill-mode: both; }
@keyframes fadein { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
"""

_installed = False


def install():
    """Load the stylesheet for the whole display (safe to call more than once)."""
    global _installed
    if _installed:
        return
    css = Gtk.CssProvider()
    try:
        css.load_from_string(CSS)
    except AttributeError:
        css.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    s = Gtk.Settings.get_default()
    if s is not None:
        s.set_property("gtk-decoration-layout", "close,minimize,maximize:")
    _installed = True


def traffic_lights():
    """Window controls on the left, macOS style."""
    wc = Gtk.WindowControls(side=Gtk.PackType.START)
    wc.set_decoration_layout("close,minimize,maximize:")
    # Without this the buttons are stretched to the full height of the title bar.
    wc.set_valign(Gtk.Align.CENTER)
    wc.set_halign(Gtk.Align.START)
    return wc
