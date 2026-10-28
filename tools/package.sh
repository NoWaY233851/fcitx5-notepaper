#!/usr/bin/env bash
# Build the release tarball for a tag: tools/package.sh v1.0.0
# Writes build/fcitx5-notepaper-<version>.tar.gz and its .sha256 next to it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="${1:?usage: tools/package.sh <tag>}"
NAME="fcitx5-notepaper-${TAG#v}"
OUT="$ROOT/build"

git -C "$ROOT" rev-parse -q --verify "refs/tags/$TAG" >/dev/null || { echo "no tag $TAG" >&2; exit 1; }

# The package ships the committed dist/, so make sure it matches the tokens.
python3 -I "$ROOT/tools/build.py" >/dev/null
git -C "$ROOT" diff --quiet "$TAG" -- dist || { echo "dist/ at $TAG is out of date; rebuild and commit it" >&2; exit 1; }

mkdir -p "$OUT"
git -C "$ROOT" archive --format=tar.gz --prefix="$NAME/" -o "$OUT/$NAME.tar.gz" "$TAG" -- \
    install.sh dist tools/sync_theme.py README.md DESIGN.md LICENSE screenshots
(cd "$OUT" && sha256sum "$NAME.tar.gz" >"$NAME.tar.gz.sha256")
echo "$OUT/$NAME.tar.gz"
