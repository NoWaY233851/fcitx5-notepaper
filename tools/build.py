#!/usr/bin/env python3
"""Build the fcitx5 classicui themes in dist/ from tokens.toml and templates/.

Usage: python3 tools/build.py
"""

import shutil
import sys
import tomllib
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
DIST = ROOT / "dist"

# Room for the pixels between the 9-slice corners; any small value works.
SLICE_CENTER = 4
# Padding around the chevrons, which also widens their click area.
ARROW_PAD = 4


def fmt(value):
    """Write numbers the way a hand-written SVG would: 8, 0.5, 0.07."""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def render(template, out, **values):
    text = Template((TEMPLATES / template).read_text()).substitute(
        {k: fmt(v) for k, v in values.items()}
    )
    # Leave unchanged files alone: install.sh restarts fcitx5 only when the
    # fontconfig alias is newer than the running process.
    if not out.exists() or out.read_text() != text:
        out.write_text(text)


def note_values(theme, *, spread, offset_y, blur, opacity, radius, border):
    """Geometry for a rounded note with a soft shadow, sliced for fcitx5."""
    shadow = {
        "l": spread,
        "r": spread,
        "t": spread - offset_y,
        "b": spread + offset_y,
    }
    slice_ = {side: shadow[side] + radius + border for side in shadow}
    w = slice_["l"] + slice_["r"] + SLICE_CENTER
    h = slice_["t"] + slice_["b"] + SLICE_CENTER
    body_w = w - shadow["l"] - shadow["r"]
    body_h = h - shadow["t"] - shadow["b"]
    svg = dict(
        w=w,
        h=h,
        blur=blur,
        radius=radius,
        body_x=shadow["l"],
        shadow_y=shadow["t"] + offset_y,
        body_w=body_w,
        body_h=body_h,
        shadow=theme["shadow"],
        shadow_opacity=opacity,
        stroke_x=shadow["l"] + border / 2,
        stroke_y=shadow["t"] + border / 2,
        stroke_w=body_w - border,
        stroke_h=body_h - border,
        stroke_r=radius - border / 2,
        paper=theme["paper"],
        border=theme["border"],
        border_width=border,
    )
    return shadow, slice_, svg


def chevron_points(size, pointing):
    aw, ah = size["arrow_width"], size["arrow_height"]
    near, far = ARROW_PAD, ARROW_PAD + aw
    if pointing == "right":
        near, far = far, near
    return f"{fmt(far)},{ARROW_PAD} {fmt(near)},{fmt(ARROW_PAD + ah / 2)} {fmt(far)},{ARROW_PAD + ah}"


def check_tokens(size):
    problems = []
    if size["cell_padding_x"] < size["hl_radius"] or size["cell_padding_y"] < size["hl_radius"]:
        problems.append("cell_padding_x/y must be >= hl_radius, or the highlight corners get stretched")
    if size["shadow_offset_y"] > size["shadow_spread"]:
        problems.append("shadow_offset_y must be <= shadow_spread")
    if size["panel_radius"] - size["panel_inset"] != size["hl_radius"]:
        print("warning: panel_radius - panel_inset != hl_radius, corners will not be concentric", file=sys.stderr)
    if problems:
        sys.exit("tokens.toml: " + "; ".join(problems))


def build_theme(meta, size, theme):
    out = DIST / theme["dir"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    border = size["panel_border"]
    inset = size["panel_inset"]
    shadow, panel_slice, panel_svg = note_values(
        theme,
        spread=size["shadow_spread"],
        offset_y=size["shadow_offset_y"],
        blur=size["shadow_blur"],
        opacity=theme["shadow_opacity"],
        radius=size["panel_radius"],
        border=border,
    )
    _, menu_slice, menu_svg = note_values(
        theme, spread=0, offset_y=0, blur=0, opacity=0, radius=size["panel_radius"], border=border
    )
    render("note.svg", out / "panel.svg", **panel_svg)
    render("note.svg", out / "menu.svg", **menu_svg)

    px, py, hl_r = size["cell_padding_x"], size["cell_padding_y"], size["hl_radius"]
    render("pill.svg", out / "highlight.svg", w=2 * px + 2, h=2 * py + 2, r=hl_r, fill=theme["hl"])
    mx, my = size["menu_padding_x"], size["menu_padding_y"]
    render("pill.svg", out / "menu-highlight.svg", w=2 * mx + 2, h=2 * my + 2, r=hl_r, fill=theme["hl"])
    mark_h = size["mark_height"]
    render("pill.svg", out / "mark.svg", w=size["mark_width"], h=mark_h, r=mark_h / 2, fill=theme["accent"])

    chevron = dict(
        w=size["arrow_width"] + 2 * ARROW_PAD,
        h=size["arrow_height"] + 2 * ARROW_PAD,
        stroke=theme["muted"],
        stroke_width=size["arrow_stroke"],
    )
    render("chevron.svg", out / "prev.svg", points=chevron_points(size, "left"), **chevron)
    # fcitx5 puts the next button flush against the content edge; pad its right side
    # like a candidate cell so the right margin matches the left one.
    render("chevron.svg", out / "next.svg", points=chevron_points(size, "right"),
           **{**chevron, "w": size["arrow_width"] + ARROW_PAD + px})
    render("chevron.svg", out / "arrow.svg", points=chevron_points(size, "right"), **chevron)
    render("check.svg", out / "check.svg", stroke=theme["ink"])
    render("separator.svg", out / "separator.svg", fill=theme["border"])

    render(
        "theme.conf",
        out / "theme.conf",
        name=theme["name"],
        name_zh_tw=theme["name_zh_tw"],
        version=meta["version"],
        author=meta["author"],
        description=theme["description"],
        ink=theme["ink"],
        hl=theme["hl"],
        paper=theme["paper"],
        border=theme["border"],
        panel_slice_l=panel_slice["l"],
        panel_slice_r=panel_slice["r"],
        panel_slice_t=panel_slice["t"],
        panel_slice_b=panel_slice["b"],
        shadow_l=shadow["l"],
        shadow_r=shadow["r"],
        shadow_t=shadow["t"],
        shadow_b=shadow["b"],
        content_l=shadow["l"] + border + inset,
        content_r=shadow["r"] + border + inset,
        content_t=shadow["t"] + border + inset,
        content_b=shadow["b"] + border + inset,
        cell_padding_x=px,
        cell_padding_y=py,
        mark_x=px + size["mark_nudge_x"],
        mark_offset_y=size["mark_offset_y"],
        menu_slice=menu_slice["l"],
        menu_content=border + inset,
        menu_padding_x=mx,
        menu_padding_y=my,
    )
    return out


def build_settings(font, themes):
    """The fontconfig alias and the classicui.conf lines install.sh merges in."""
    (DIST / "fontconfig").mkdir(parents=True, exist_ok=True)
    render("fontconfig.conf", DIST / "fontconfig" / "60-notepaper.conf",
           family=font["family"], latin=font["latin"], cjk=font["cjk"])
    render("classicui.conf", DIST / "classicui.conf",
           font=f'{font["family"]} {font["size"]}', menu_font=font["menu"],
           light=themes["light"]["dir"], dark=themes["dark"]["dir"])


def main():
    tokens = tomllib.loads((ROOT / "tokens.toml").read_text())
    size = tokens["size"]
    check_tokens(size)
    for theme in tokens["themes"].values():
        out = build_theme(tokens["meta"], size, theme)
        print(f"built {out.relative_to(ROOT)}")
    build_settings(tokens["font"], tokens["themes"])
    print("built dist/fontconfig/60-notepaper.conf, dist/classicui.conf")


if __name__ == "__main__":
    main()
