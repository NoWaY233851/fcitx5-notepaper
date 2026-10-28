#!/usr/bin/env python3
"""Pop up the fcitx5 candidate panel and save a picture of it.

Creates a throwaway input context over DBus the way an X11 app would, types a
pinyin string into it, then copies the pixels of fcitx5's own panel window
(nothing else on screen) and lays them on a plain page color so the shadow
shows. Text it would commit goes to the throwaway context, never to a real
window. Needs XWayland, since the panel is captured as an X11 window.

fcitx5-rime shares one RIME session with your other windows by default, so
RIME has to be in Chinese mode and --keys has to suit the active schema
(pinyin: nihao, bopomofo: 5k4g4 for 這是).

Usage: python3 tools/snapshot.py [--keys nihao] [--inline-preedit] [--page "#E9E7E1"]
                                 [--zoom 2] [-o screenshots/panel.png]
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

os.environ["GDK_BACKEND"] = "x11"

import gi  # noqa: E402

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GdkX11", "3.0")
from gi.repository import Gdk, GdkPixbuf, GdkX11, Gio, GLib  # noqa: E402

BUS_NAME = "org.fcitx.Fcitx5"
IM_PATH = "/org/freedesktop/portal/inputmethod"
IM_IFACE = "org.fcitx.Fcitx.InputMethod1"
IC_IFACE = "org.fcitx.Fcitx.InputContext1"
CONTROLLER_IFACE = "org.fcitx.Fcitx.Controller1"
# fcitx::CapabilityFlag
CAP_PREEDIT = 1 << 1
CAP_FORMATTED_PREEDIT = 1 << 4
# Where the fake text cursor sits, in X11 root coordinates.
CURSOR = (240, 240, 1, 20)
WINDOW_NAME = "Fcitx5 Input Window"
PAGE_MARGIN = 16


class Fcitx:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION)

    def call(self, path, iface, method, args=None, reply=None):
        return self.bus.call_sync(
            BUS_NAME, path, iface, method, args,
            GLib.VariantType(reply) if reply else None,
            Gio.DBusCallFlags.NONE, 2000, None,
        )

    def create_ic(self, display):
        args = GLib.Variant("(a(ss))", ([("program", "notepaper-snapshot"), ("display", display)],))
        path, _uuid = self.call(IM_PATH, IM_IFACE, "CreateInputContext", args, "(oay)").unpack()
        return path

    def key(self, ic, keysym):
        """Press and release a key; True if the input method took the press."""
        handled = False
        for release in (False, True):
            args = GLib.Variant("(uuubu)", (keysym, 0, 0, release, int(time.monotonic() * 1000) & 0xFFFFFFFF))
            (took,) = self.call(ic, IC_IFACE, "ProcessKeyEvent", args, "(b)").unpack()
            handled = handled or (took and not release)
            time.sleep(0.03)
        return handled


def find_panel_window():
    tree = subprocess.run(["xwininfo", "-root", "-tree"], capture_output=True, text=True, check=True).stdout
    match = re.search(r"(0x[0-9a-f]+) \"" + WINDOW_NAME + r"\".*?(\d+)x(\d+)[+-]-?\d+[+-]-?\d+\s+\+(-?\d+)\+(-?\d+)", tree)
    if not match:
        sys.exit(f"no '{WINDOW_NAME}' window; is fcitx5 running with the classic UI?")
    xid, w, h, x, y = match.groups()
    return int(xid, 16), int(w), int(h), int(x), int(y)


def capture(xid, w, h):
    Gdk.init([])
    window = GdkX11.X11Window.foreign_new_for_display(Gdk.Display.get_default(), xid)
    pixbuf = Gdk.pixbuf_get_from_window(window, 0, 0, w, h)
    if pixbuf is None:
        sys.exit("could not read the panel window")
    return pixbuf


def on_page(panel, color, zoom):
    rgba = Gdk.RGBA()
    rgba.parse(color)
    pixel = (round(rgba.red * 255) << 24) | (round(rgba.green * 255) << 16) | (round(rgba.blue * 255) << 8) | 0xFF
    w, h = panel.get_width() + 2 * PAGE_MARGIN, panel.get_height() + 2 * PAGE_MARGIN
    page = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, w, h)
    page.fill(pixel)
    panel.composite(page, PAGE_MARGIN, PAGE_MARGIN, panel.get_width(), panel.get_height(),
                    PAGE_MARGIN, PAGE_MARGIN, 1, 1, GdkPixbuf.InterpType.NEAREST, 255)
    if zoom > 1:
        page = page.scale_simple(w * zoom, h * zoom, GdkPixbuf.InterpType.NEAREST)
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keys", default="nihao", help="what to type (ASCII letters)")
    parser.add_argument("--inline-preedit", action="store_true",
                        help="claim the app shows the preedit, so the panel only shows candidates")
    parser.add_argument("--page", default="#E9E7E1", help="background color under the panel")
    parser.add_argument("--zoom", type=int, default=1, help="enlarge with nearest-neighbor scaling")
    parser.add_argument("-o", "--output", default="screenshots/panel.png")
    args = parser.parse_args()

    fcitx = Fcitx()
    ic = fcitx.create_ic("x11:" + os.environ.get("DISPLAY", ":0"))
    try:
        cap = CAP_PREEDIT | CAP_FORMATTED_PREEDIT if args.inline_preedit else 0
        fcitx.call(ic, IC_IFACE, "SetCapability", GLib.Variant("(t)", (cap,)))
        fcitx.call(ic, IC_IFACE, "SetCursorRect", GLib.Variant("(iiii)", CURSOR))
        fcitx.call(ic, IC_IFACE, "FocusIn")
        fcitx.call("/controller", CONTROLLER_IFACE, "Activate")
        time.sleep(0.2)
        # Not any(...): every key has to be sent.
        if not [fcitx.key(ic, ord(char)) for char in args.keys].count(True):
            sys.exit("RIME ignored every key: it shares one state with your other windows (InputState=All), "
                     "so switch it to Chinese mode, and pass --keys for the active schema")
        time.sleep(0.6)
        xid, w, h, x, y = find_panel_window()
        panel = capture(xid, w, h)
    finally:
        fcitx.call(ic, IC_IFACE, "FocusOut")
        fcitx.call(ic, IC_IFACE, "DestroyIC")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    on_page(panel, args.page, args.zoom).savev(str(out), "png", [], [])
    # Where the window's top-left sits relative to the bottom-left of the text cursor;
    # with a shadow this should be minus the theme's ShadowMargin left/top.
    dx, dy = x - CURSOR[0], y - (CURSOR[1] + CURSOR[3])
    print(f"{out} ({w}x{h}, alpha={panel.get_has_alpha()}, window offset from cursor {dx:+d},{dy:+d})")


if __name__ == "__main__":
    main()
