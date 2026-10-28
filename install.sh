#!/usr/bin/env bash
# Install the Notepaper themes for fcitx5 classicui (README.md).
#   ./install.sh               link the themes, switch classicui to them, and start
#                              the service that keeps Theme= in step with light/dark
#   ./install.sh --uninstall   undo all of that and restore classicui.conf
#
# Run from a git checkout, everything links back to the checkout, so rebuilt
# themes apply at once. Run from anything else (a release download), it first
# copies itself to $INSTALL_DIR and installs from there, so the download can go.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fcitx5-notepaper"
THEMES_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fcitx5/themes"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}/fcitx5/conf/classicui.conf"
BACKUP="$CONF.before-notepaper"
FONTCONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/fontconfig/conf.d/60-notepaper.conf"
SERVICE=notepaper-theme-sync.service
SERVICE_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/$SERVICE"
THEMES=(notepaper notepaper-dark)

is_copy_install() { [[ ! -e "$ROOT/.git" && "$ROOT" != "$INSTALL_DIR" ]]; }

# Everything the installed themes and the sync service need at run time.
copy_to_install_dir() {
    rm -rf "${INSTALL_DIR:?}"
    mkdir -p "$INSTALL_DIR/tools"
    # No --preserve: a fresh mtime on the font alias is what tells reload_fcitx5 to restart.
    cp -r "$ROOT/install.sh" "$ROOT/dist" "$ROOT/LICENSE" "$INSTALL_DIR/"
    cp "$ROOT/tools/sync_theme.py" "$INSTALL_DIR/tools/"
    echo "copied to $INSTALL_DIR"
}

fcitx5_call() {
    gdbus call --session --dest org.fcitx.Fcitx5 --object-path /controller \
        --method "org.fcitx.Fcitx.Controller1.$1" "${@:2}" >/dev/null 2>&1
}

reload_fcitx5() {
    local pid started
    pid="$(pgrep -x fcitx5 | head -n1 || true)"
    if [[ -z "$pid" ]]; then
        echo "fcitx5 is not running; the themes apply on its next start"
        return
    fi
    started="$(stat -c %Y "/proc/$pid")"
    # fcitx5 reads fontconfig once at startup, so it must restart when the alias link
    # was (re)pointed or the file it points to changed since then.
    if [[ -L "$FONTCONFIG" ]] &&
        (($(stat -c %Y "$FONTCONFIG") > started || $(stat -L -c %Y "$FONTCONFIG") > started)); then
        fcitx5_call Restart && echo "restarted fcitx5 to load the font alias"
    # `fcitx5-remote -r` does not reload the classic UI, so ask for it by name.
    else
        fcitx5_call ReloadAddonConfig classicui && echo "reloaded fcitx5 classicui"
    fi
}

# Point $2 at $1, leaving an existing correct link alone so its mtime stays meaningful.
link() {
    [[ "$(readlink "$2" || true)" == "$1" ]] && return
    ln -sfn "$1" "$2"
    echo "linked $2"
}

# GTK and Qt Wayland apps draw their own candidate window from Theme= alone,
# so tools/sync_theme.py rewrites Theme= whenever the system switches light/dark.
install_service() {
    # Once now, so the fcitx5 reload that follows already reads the right theme.
    python3 -I "$ROOT/tools/sync_theme.py" --once || echo "could not read the system light/dark setting" >&2
    if ! systemctl --user show-environment >/dev/null 2>&1; then
        echo "no systemd user session; GTK and Qt apps will keep the light theme" >&2
        return
    fi
    mkdir -p "$(dirname "$SERVICE_FILE")"
    cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=Notepaper: follow the system light/dark setting in GTK and Qt candidate windows
PartOf=graphical-session.target
After=graphical-session.target

[Service]
ExecStart=$(command -v python3) -I "$ROOT/tools/sync_theme.py"
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical-session.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE" >/dev/null 2>&1
    systemctl --user restart "$SERVICE"
    echo "started $SERVICE"
}

uninstall_service() {
    if [[ -f "$SERVICE_FILE" ]]; then
        systemctl --user disable --now "$SERVICE" >/dev/null 2>&1 || true
        rm "$SERVICE_FILE"
        systemctl --user daemon-reload || true
        echo "removed $SERVICE"
    fi
}

# Set key=value in a flat fcitx5 config file, replacing an existing line for the same key.
set_key() {
    local line="$1" key="${1%%=*}"
    awk -v key="$key" -v line="$line" '
        index($0, key "=") == 1 { print line; done = 1; next }
        { print }
        END { if (!done) print line }
    ' "$CONF" >"$CONF.tmp"
    mv "$CONF.tmp" "$CONF"
}

install() {
    for file in "${THEMES[@]/%//theme.conf}" fontconfig/60-notepaper.conf classicui.conf; do
        [[ -f "$ROOT/dist/$file" ]] || { echo "dist/$file is missing; run: python3 tools/build.py" >&2; exit 1; }
    done

    mkdir -p "$THEMES_DIR" "$(dirname "$CONF")" "$(dirname "$FONTCONFIG")"
    for theme in "${THEMES[@]}"; do
        local target="$THEMES_DIR/$theme"
        if [[ -e "$target" && ! -L "$target" ]]; then
            echo "$target exists and is not a link; leaving it alone" >&2
            exit 1
        fi
        link "$ROOT/dist/$theme" "$target"
    done
    link "$ROOT/dist/fontconfig/60-notepaper.conf" "$FONTCONFIG"

    # Keep the user's original config once; an empty backup means there was none.
    if [[ ! -e "$BACKUP" ]]; then
        if [[ -f "$CONF" ]]; then cp "$CONF" "$BACKUP"; else : >"$BACKUP"; fi
    fi
    touch "$CONF"
    while IFS= read -r setting; do
        [[ -n "$setting" ]] && set_key "$setting"
    done <"$ROOT/dist/classicui.conf"
    echo "updated $CONF"
    install_service
    reload_fcitx5
}

uninstall() {
    # Stop the service first so it cannot rewrite Theme= after the restore.
    uninstall_service
    for theme in "${THEMES[@]}"; do
        if [[ -L "$THEMES_DIR/$theme" ]]; then
            rm "$THEMES_DIR/$theme"
            echo "removed $THEMES_DIR/$theme"
        fi
    done
    if [[ -L "$FONTCONFIG" ]]; then
        rm "$FONTCONFIG"
        echo "removed $FONTCONFIG"
    fi
    if [[ -e "$BACKUP" ]]; then
        if [[ -s "$BACKUP" ]]; then mv "$BACKUP" "$CONF"; else rm -f "$CONF" "$BACKUP"; fi
        echo "restored $CONF"
    fi
    reload_fcitx5
    # Last, since this script may be running from inside it.
    if [[ "$ROOT" == "$INSTALL_DIR" ]]; then
        rm -rf "${INSTALL_DIR:?}"
        echo "removed $INSTALL_DIR"
    fi
}

case "${1:-}" in
    "")
        if is_copy_install; then
            copy_to_install_dir
            exec "$INSTALL_DIR/install.sh"
        fi
        install
        ;;
    --uninstall)
        if is_copy_install && [[ -x "$INSTALL_DIR/install.sh" ]]; then
            exec "$INSTALL_DIR/install.sh" --uninstall
        fi
        uninstall
        ;;
    *) echo "usage: $0 [--uninstall]" >&2; exit 2 ;;
esac
