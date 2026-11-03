"""org.freedesktop.Notifications server (in-process) with history and Do Not Disturb."""

import time

from gi.repository import Gio, GLib

XML = """
<node><interface name="org.freedesktop.Notifications">
 <method name="Notify"><arg type="s" direction="in"/><arg type="u" direction="in"/><arg type="s" direction="in"/>
  <arg type="s" direction="in"/><arg type="s" direction="in"/><arg type="as" direction="in"/>
  <arg type="a{sv}" direction="in"/><arg type="i" direction="in"/><arg type="u" direction="out"/></method>
 <method name="CloseNotification"><arg type="u" direction="in"/></method>
 <method name="GetCapabilities"><arg type="as" direction="out"/></method>
 <method name="GetServerInformation"><arg type="s" direction="out"/><arg type="s" direction="out"/>
  <arg type="s" direction="out"/><arg type="s" direction="out"/></method>
 <signal name="NotificationClosed"><arg type="u"/><arg type="u"/></signal>
 <signal name="ActionInvoked"><arg type="u"/><arg type="s"/></signal>
</interface></node>"""


class Notifyd:
    def __init__(self, on_new):
        self.on_new = on_new        # callback(item, show_toast)
        self.history = []           # newest first: dict(id, app, summary, body, time)
        self.dnd = False
        self._next = 1
        self.on_change = lambda: None
        self.conn = None
        Gio.bus_own_name(Gio.BusType.SESSION, "org.freedesktop.Notifications",
                         Gio.BusNameOwnerFlags.REPLACE | Gio.BusNameOwnerFlags.ALLOW_REPLACEMENT,
                         self._bus_acquired, None, lambda *a: None)

    def _bus_acquired(self, conn, _name):
        self.conn = conn
        info = Gio.DBusNodeInfo.new_for_xml(XML)
        conn.register_object("/org/freedesktop/Notifications", info.interfaces[0], self._call, None, None)

    def _call(self, _c, _s, _p, _i, method, params, inv):
        if method == "Notify":
            app, rid, _icon, summary, body, _actions, _hints, _timeout = params.unpack()
            nid = rid or self._next
            if not rid:
                self._next += 1
            self.add(app, summary, body, nid)
            inv.return_value(GLib.Variant("(u)", (nid,)))
        elif method == "GetCapabilities":
            inv.return_value(GLib.Variant("(as)", (["body", "persistence"],)))
        elif method == "GetServerInformation":
            inv.return_value(GLib.Variant("(ssss)", ("Bastille Shell", "Bastille OS", "1.0", "1.2")))
        else:
            inv.return_value(None)

    def add(self, app, summary, body, nid=None):
        nid = nid or self._next
        self._next = max(self._next, nid + 1)
        self.history = [h for h in self.history if h["id"] != nid]
        item = {"id": nid, "app": app or "System", "summary": summary, "body": body, "time": time.time()}
        self.history.insert(0, item)
        del self.history[50:]
        self.on_new(item, not self.dnd)
        self.on_change()

    def clear(self):
        self.history = []
        self.on_change()
