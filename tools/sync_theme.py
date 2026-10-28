#!/usr/bin/env python3
"""Keep classicui.conf's Theme= in step with the system light/dark setting.

fcitx5 follows the system by itself through DarkTheme/UseDarkTheme, but on
COSMIC the candidate windows of GTK and Qt Wayland apps (Firefox, Qt apps) are
drawn inside the app by fcitx5-gtk / fcitx5-qt, which only read Theme=. This
watches the desktop portal's color-scheme, points Theme= at the light or dark
Notepaper theme (those apps reload the file as soon as it changes), and asks
fcitx5 to reload so its own panel reads the same file.

Usage: python3 tools/sync_theme.py [--once]
install.sh runs it as the notepaper-theme-sync systemd user service.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONF = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fcitx5/conf/classicui.conf"
PORTAL_NAME = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SETTINGS_IFACE = "org.freedesktop.portal.Settings"
NAMESPACE, KEY = "org.freedesktop.appearance", "color-scheme"
PREFER_DARK = 1  # 0 = no preference, 1 = prefer dark, 2 = prefer light


def theme_names():
    """(light, dark) theme names, from the settings install.sh merges in."""
    settings = dict(
        line.split("=", 1) for line in (ROOT / "dist/classicui.conf").read_text().splitlines() if "=" in line
    )
    return settings["Theme"], settings["DarkTheme"]


def read_color_scheme(bus):
    try:
        reply = bus.call_sync(PORTAL_NAME, PORTAL_PATH, SETTINGS_IFACE, "ReadOne",
                              GLib.Variant("(ss)", (NAMESPACE, KEY)), None,
                              Gio.DBusCallFlags.NONE, 5000, None)
        return reply.unpack()[0]
    except GLib.Error:
        # Portals older than version 2 only have Read, which wraps the value twice.
        reply = bus.call_sync(PORTAL_NAME, PORTAL_PATH, SETTINGS_IFACE, "Read",
                              GLib.Variant("(ss)", (NAMESPACE, KEY)), None,
                              Gio.DBusCallFlags.NONE, 5000, None)
        value = reply.unpack()[0]
        return value[0] if isinstance(value, tuple) else value


def set_theme(name):
    """Point Theme= at `name`; True if the file changed."""
    lines = CONF.read_text().splitlines() if CONF.exists() else []
    wanted = f"Theme={name}"
    if wanted in lines:
        return False
    if any(line.startswith("Theme=") for line in lines):
        lines = [wanted if line.startswith("Theme=") else line for line in lines]
    else:
        lines.append(wanted)
    text = "\n".join(lines) + "\n"
    CONF.parent.mkdir(parents=True, exist_ok=True)
    # Replace the file in one step so the apps watching it never read half of it.
    fd, tmp = tempfile.mkstemp(dir=CONF.parent, prefix=".classicui.conf.")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    if CONF.exists():
        os.chmod(tmp, CONF.stat().st_mode & 0o777)
    os.replace(tmp, CONF)
    return True


def reload_fcitx5(bus):
    try:
        bus.call_sync("org.fcitx.Fcitx5", "/controller", "org.fcitx.Fcitx.Controller1",
                      "ReloadAddonConfig", GLib.Variant("(s)", ("classicui",)), None,
                      Gio.DBusCallFlags.NONE, 2000, None)
    except GLib.Error:
        pass  # Not running yet; it reads the file when it starts.


def apply(bus, scheme, themes):
    light, dark = themes
    name = dark if scheme == PREFER_DARK else light
    if set_theme(name):
        reload_fcitx5(bus)
        print(f"color-scheme {scheme}: Theme={name}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--once", action="store_true", help="apply the current setting and exit")
    args = parser.parse_args()

    bus = Gio.bus_get_sync(Gio.BusType.SESSION)
    themes = theme_names()
    try:
        apply(bus, read_color_scheme(bus), themes)
    except GLib.Error as error:
        sys.exit(f"cannot read {NAMESPACE} {KEY} from the desktop portal: {error.message}")
    if args.once:
        return

    def on_setting_changed(_bus, _sender, _path, _iface, _signal, params):
        namespace, key, value = params.unpack()
        if (namespace, key) == (NAMESPACE, KEY):
            apply(bus, value, themes)

    bus.signal_subscribe(PORTAL_NAME, SETTINGS_IFACE, "SettingChanged", PORTAL_PATH, NAMESPACE,
                         Gio.DBusSignalFlags.NONE, on_setting_changed)
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
