"""Stroke icons (24-grid) and macOS-style gradient app tiles, rendered with librsvg."""

import gi
gi.require_version('Gdk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gdk, GdkPixbuf, Gtk

PATHS = {
    "search": "M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-4.5-4.5",
    "wifi": "M5 12.5a10 10 0 0114 0M8 16a6 6 0 018 0M12 19.5h.01",
    "eth": "M4 5h16v8H4zM8 13v3M12 13v3M16 13v3M6 19h12",
    "volume": "M4 9v6h4l5 4V5L8 9zM16.5 8.5a5 5 0 010 7",
    "mute": "M4 9v6h4l5 4V5L8 9zM17 9l4 6M21 9l-4 6",
    "battery": "M3 8h15v8H3zM21 11v2M6 11v2",
    "bolt": "M13 3L6 14h5l-1 7 7-11h-5z",
    "bell": "M6 16v-5a6 6 0 1112 0v5l2 2H4zM10 20a2 2 0 004 0",
    "sliders": "M4 7h10M18 7h2M4 17h2M10 17h10M14 5v4M8 15v4",
    "sun": "M12 8a4 4 0 100 8 4 4 0 000-8zM12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5",
    "moon": "M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z",
    "bt": "M7 7l10 10-5 4V3l5 4L7 17",
    "power": "M12 3v9M6.4 6.4a8 8 0 1011.2 0",
    "restart": "M20 12a8 8 0 11-2.3-5.7M20 4v5h-5",
    "lock": "M6 11h12v9H6zM9 11V8a3 3 0 016 0v3",
    "shield": "M12 3l8 3v6c0 4.5-3.2 7.8-8 9-4.8-1.2-8-4.5-8-9V6z",
    "check": "M5 12l5 5 9-10",
    "copy": "M8 8h11v12H8zM5 16V4h11",
    "layers": "M12 3l9 5-9 5-9-5zM3 13l9 5 9-5",
    "folder": "M3 7h6l2 2h10v10H3z",
    "term": "M4 5h16v14H4zM8 10l3 2-3 2M13 15h3",
    "globe": "M12 3a9 9 0 100 18 9 9 0 000-18zM3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18",
    "gear": "M12 9a3 3 0 100 6 3 3 0 000-6zM12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1",
    "mail": "M4 6h16v12H4zM4 7l8 6 8-6",
    "msg": "M4 5h16v11H9l-5 4z",
    "notes": "M6 4h12v16H6zM9 9h6M9 13h6",
    "cal": "M5 6h14v14H5zM5 10h14M9 3v4M15 3v4",
    "music": "M9 18V6l10-2v12M9 18a3 3 0 11-6 0 3 3 0 016 0zM19 16a3 3 0 11-6 0 3 3 0 016 0z",
    "cloud": "M7 18a4 4 0 010-8 5 5 0 019.5 1A3.5 3.5 0 0117 18z",
    "map": "M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2zM9 4v14M15 6v14",
    "doc": "M7 3h8l4 4v14H7zM15 3v4h4M10 13h6M10 17h6",
    "table": "M4 5h16v14H4zM4 10h16M10 5v14",
    "slides": "M4 4h16v11H4zM12 15v5M8 20h8",
    "download": "M12 4v11M7 11l5 5 5-5M5 20h14",
    "apps": "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    "chev": "M9 6l6 6-6 6",
    "x": "M6 6l12 12M18 6L6 18",
    "plus": "M12 5v14M5 12h14",
    "clock": "M12 3a9 9 0 100 18 9 9 0 000-18zM12 7v5l3 2",
    "cpu": "M7 7h10v10H7zM9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4",
    "vpn": "M12 3l8 3v6c0 4.5-3.2 7.8-8 9-4.8-1.2-8-4.5-8-9V6zM9 12l2 2 4-4",
    "trash": "M5 7h14M9 7V4h6v3M7 7l1 13h8l1-13",
    "grid": "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
    "store": "M5 8h14l-1 12H6zM9 8V6a3 3 0 016 0v2",
    "minus": "M5 12h14",
    "back": "M15 6l-6 6 6 6",
    "info": "M12 3a9 9 0 100 18 9 9 0 000-18zM12 11v5M12 8h.01",
    "airplane": "M3 13l8-2-3-7h2l6 6 5-1.5a1.5 1.5 0 010 3L16 13l-6 6H8l2-6z",
    "coffee": "M5 9h11v6a4 4 0 01-4 4H9a4 4 0 01-4-4zM16 10h2a2 2 0 010 4h-2M8 3v3M12 3v3",
    "camera": "M4 8h4l2-3h4l2 3h4v11H4zM12 11a3 3 0 100 6 3 3 0 000-6z",
    "key": "M14 10a4 4 0 11-8 0 4 4 0 018 0zM12.8 12.8L20 20M17 17l2-2",
    "display": "M3 5h18v11H3zM8 20h8M12 16v4",
    "speaker": "M7 3h10v18H7zM12 8a1 1 0 100 .01M12 17a3 3 0 100-6 3 3 0 000 6z",
    "keyboard": "M3 7h18v10H3zM7 11h.01M11 11h.01M15 11h.01M8 14h8",
    "user": "M12 12a4 4 0 100-8 4 4 0 000 8zM4 20a8 8 0 0116 0",
    "hdd": "M3 14h18v6H3zM5 14l2-9h10l2 9M17 17h.01",
    "printer": "M7 9V4h10v5M7 17H4v-7h16v7h-3M7 14h10v6H7z",
    "access": "M12 4a1.5 1.5 0 100 .01M5 8l7 1 7-1M12 9v5M9 20l3-6 3 6",
    "usb": "M12 3v14M12 17a2 2 0 100 4 2 2 0 000-4zM12 9l4-2v3M12 12l-4-2V8",
    "bug": "M9 8a3 3 0 016 0v9a3 3 0 01-6 0zM5 10h4M15 10h4M5 15h4M15 15h4",
    "face": "M12 3a9 9 0 100 18 9 9 0 000-18zM9 10h.01M15 10h.01M9 15h6",
    "refresh": "M20 12a8 8 0 11-2.3-5.7M20 4v5h-5",
    "signal": "M5 19v-3M10 19v-7M15 19V8M20 19V4",
    "sparkle": "M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z",
    "chat": "M4 5h16v11H9l-5 4z",
    "edit": "M4 20h4L19 9l-4-4L4 16zM13 7l4 4",
}

# app tile gradients (top, bottom)
TILES = {
    "files": ("#58b4ff", "#1f6fe0"), "browser": ("#46dba5", "#0f8f6c"), "terminal": ("#4a4d52", "#1d1f22"),
    "settings": ("#a8aab0", "#5e6066"), "mail": ("#58b4ff", "#2368e0"), "messages": ("#52dd78", "#14a53c"),
    "notes": ("#ffd84a", "#e8a900"), "calendar": ("#fafafa", "#d6d6d8"), "music": ("#ff6a82", "#d01f45"),
    "weather": ("#62ccfa", "#2a7be4"), "maps": ("#74dc74", "#2a9a4a"), "documents": ("#58a6ff", "#1c5fd6"),
    "sheets": ("#46dc86", "#128a47"), "presentations": ("#ffa94d", "#e0670f"), "install": ("#8a70ff", "#4a35d6"),
    "launcher": ("#6a6e74", "#34373b"), "generic": ("#7b8088", "#4a4e55"),
    "store": ("#5ac8fa", "#2563e8"), "update": ("#8d8bff", "#4a43d8"), "setup": ("#a8aab0", "#5e6066"),
}
TILE_GLYPH = {"files": "folder", "browser": "globe", "terminal": "term", "settings": "gear", "mail": "mail",
              "messages": "msg", "notes": "notes", "calendar": "cal", "music": "music", "weather": "cloud",
              "maps": "map", "documents": "doc", "sheets": "table", "presentations": "slides",
              "install": "download", "launcher": "apps", "generic": "apps", "store": "store",
              "update": "download", "setup": "gear"}

_cache = {}


def _texture(svg):
    key = svg
    tex = _cache.get(key)
    if tex is None:
        loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
        loader.write(svg.encode())
        loader.close()
        tex = Gdk.Texture.new_for_pixbuf(loader.get_pixbuf())
        _cache[key] = tex
    return tex


def icon(name, color="#f4f6f5", size=16, stroke=1.8):
    px = size * 3
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{px}" height="{px}" fill="none" '
           f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">'
           f'<path d="{PATHS.get(name, PATHS["grid"])}"/></svg>')
    img = Gtk.Image.new_from_paintable(_texture(svg))
    img.set_pixel_size(size)
    img.set_halign(Gtk.Align.CENTER)
    img.set_valign(Gtk.Align.CENTER)
    return img


def tile(kind, size=52):
    """macOS-style rounded gradient tile with a white glyph."""
    c1, c2 = TILES.get(kind, TILES["generic"])
    glyph = PATHS[TILE_GLYPH.get(kind, "apps")]
    stroke = "#2a2d31" if kind == "calendar" else "#ffffff"
    px = size * 3
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" viewBox="0 0 96 96">'
           f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c1}"/>'
           f'<stop offset="1" stop-color="{c2}"/></linearGradient></defs>'
           f'<rect x="2" y="2" width="92" height="92" rx="22" fill="url(#g)"/>'
           f'<rect x="2.5" y="2.5" width="91" height="91" rx="21.5" fill="none" stroke="#ffffff" stroke-opacity="0.28"/>'
           f'<g transform="translate(24 24) scale(2)" fill="none" stroke="{stroke}" stroke-width="1.7" '
           f'stroke-linecap="round" stroke-linejoin="round"><path d="{glyph}"/></g></svg>')
    img = Gtk.Image.new_from_paintable(_texture(svg))
    img.set_pixel_size(size)
    img.set_halign(Gtk.Align.CENTER)
    img.set_valign(Gtk.Align.CENTER)
    return img


def badge(glyph, c1, c2, size=26, radius=None):
    """Small gradient rounded-square badge with a white glyph (Settings sidebar, store categories)."""
    px = size * 3
    r = radius if radius is not None else 22
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" viewBox="0 0 96 96">'
           f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c1}"/>'
           f'<stop offset="1" stop-color="{c2}"/></linearGradient></defs>'
           f'<rect x="2" y="2" width="92" height="92" rx="{r}" fill="url(#g)"/>'
           f'<rect x="2.5" y="2.5" width="91" height="91" rx="{r - 0.5}" fill="none" stroke="#ffffff" stroke-opacity="0.25"/>'
           f'<g transform="translate(22 22) scale(2.2)" fill="none" stroke="#ffffff" stroke-width="1.7" '
           f'stroke-linecap="round" stroke-linejoin="round"><path d="{PATHS.get(glyph, PATHS["grid"])}"/></g></svg>')
    img = Gtk.Image.new_from_paintable(_texture(svg))
    img.set_pixel_size(size)
    img.set_halign(Gtk.Align.CENTER)
    img.set_valign(Gtk.Align.CENTER)
    return img
