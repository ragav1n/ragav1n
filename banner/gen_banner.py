"""Generate the profile banner SVGs, one per GitHub theme.

GitHub serves README images through an <img> tag, which cannot fetch web fonts.
Live <text> would fall back to a different face on every OS, so every glyph here
is outlined to a path. The constellation is seeded, so re-running this produces
byte-identical output.

    python3 gen_banner.py

Writes ../assets/banner-light.svg and ../assets/banner-dark.svg.
"""

import math
import random
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen

HERE = Path(__file__).parent
FONTS = HERE / "fonts"
OUT = HERE.parent / "assets"

W, H = 1280, 260
SEED = 20260810

# The constellation echoes the knowledge graph inside threat-intel. It runs off
# the top and bottom crop so it reads as a field the banner cuts into, rather
# than a blob floating in the middle of the page.
FIELD_X0, FIELD_X1 = 452, W + 40
FIELD_Y0, FIELD_Y1 = -34, H + 34
NODE_COUNT = 52
MIN_GAP = 38
NEIGHBOURS = 2
MAX_LINK = 132

THEMES = {
    "light": {"ink": "#0b0d10", "muted": "#5b6570", "accent": "#0f7d8f", "edge": "#7d8b96"},
    "dark": {"ink": "#e8eef4", "muted": "#8b949e", "accent": "#4cc3d9", "edge": "#5f7280"},
}


def load(name, axes=None):
    font = TTFont(FONTS / name)
    if axes:
        instantiateVariableFont(font, axes, inplace=True)
    return font


def outline(font, text, size, origin, tracking=0.0, fill="#000", opacity=None):
    """Lay out text as outlined paths, letterspaced by `tracking` em."""
    upem = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    glyphs = font.getGlyphSet()
    hmtx = font["hmtx"]

    missing = [c for c in text if ord(c) not in cmap]
    if missing:
        raise SystemExit(f"font is missing {missing!r}, pick another character")

    scale = size / upem
    step = tracking * upem
    parts, pen_x = [], 0.0

    for char in text:
        name = cmap[ord(char)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        d = pen.getCommands()
        if d:
            parts.append(f'<path transform="translate({pen_x:.0f} 0)" d="{d}"/>')
        pen_x += hmtx[name][0] + step

    width = (pen_x - step) * scale
    attrs = f' fill="{fill}"'
    if opacity is not None:
        attrs += f' opacity="{opacity}"'
    # Fonts draw y-up, SVG draws y-down, so the group flips the axis.
    group = (
        f'<g transform="translate({origin[0]} {origin[1]}) scale({scale:.6f} {-scale:.6f})"'
        f'{attrs}>{"".join(parts)}</g>'
    )
    return group, width


def smoothstep(a, b, x):
    if a == b:
        return 0.0 if x < a else 1.0
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def falloff(x, y):
    """Thin the field out to nothing before the right crop.

    Only the last few pixels of the top and bottom soften, so nodes run off
    those edges instead of curving into an oval.
    """
    fx = smoothstep(FIELD_X0, FIELD_X0 + 300, x) * (1 - smoothstep(W - 178, W + 8, x))
    fy = smoothstep(-30, 16, y) * (1 - smoothstep(H - 16, H + 30, y))
    return fx * fy


def build_field(rng):
    nodes = []
    attempts = 0
    while len(nodes) < NODE_COUNT and attempts < NODE_COUNT * 400:
        attempts += 1
        x = rng.uniform(FIELD_X0, FIELD_X1)
        y = rng.uniform(FIELD_Y0, FIELD_Y1)
        if falloff(x, y) < 0.05:
            continue
        if any((x - nx) ** 2 + (y - ny) ** 2 < MIN_GAP**2 for nx, ny, _ in nodes):
            continue
        nodes.append((x, y, rng.random()))

    # Linking each node to its nearest few neighbours draws a graph. Linking
    # everything inside a radius draws a mesh, which reads as noise.
    seen, edges = set(), []
    for i, (x1, y1, _) in enumerate(nodes):
        near = sorted(
            ((math.hypot(x2 - x1, y2 - y1), j) for j, (x2, y2, _) in enumerate(nodes) if j != i)
        )[:NEIGHBOURS]
        for dist, j in near:
            if dist > MAX_LINK:
                continue
            key = (min(i, j), max(i, j))
            if key in seen:
                continue
            seen.add(key)
            edges.append((x1, y1, nodes[j][0], nodes[j][1], dist))

    hubs = sorted(nodes, key=lambda n: -falloff(n[0], n[1]))[:2]
    return nodes, edges, hubs


def render(theme_name):
    c = THEMES[theme_name]
    rng = random.Random(SEED)
    nodes, edges, hubs = build_field(rng)

    grotesk = load("SpaceGroteskVF.ttf", {"wght": 500})
    mono = load("JetBrainsMono.ttf")

    body = []

    # The banner scales to the width of the README column, so the wordmark sits
    # near x=0 to share a left edge with the body text underneath it.
    left = 6
    wordmark, mark_w = outline(
        grotesk, "RAGAV", size=96, origin=(left, 152), tracking=0.15, fill=c["ink"]
    )
    body.append(wordmark)

    body.append(
        f'<rect x="{left + 2}" y="186" width="{mark_w - 4:.0f}" height="1" '
        f'fill="{c["ink"]}" opacity="0.22"/>'
    )

    tagline, _ = outline(
        mono,
        "security · systems · local-first",
        size=15,
        origin=(left + 2, 218),
        tracking=0.16,
        fill=c["muted"],
    )
    body.append(tagline)

    for x1, y1, x2, y2, dist in edges:
        a = min(falloff(x1, y1), falloff(x2, y2))
        a *= 1 - (dist / MAX_LINK) * 0.5
        a *= 0.42
        if a < 0.015:
            continue
        body.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{c["edge"]}" stroke-width="0.85" opacity="{a:.3f}"/>'
        )

    for x, y, jitter in nodes:
        a = falloff(x, y)
        if a < 0.03:
            continue
        r = 1.5 + jitter * 1.7
        warm = jitter > 0.72
        body.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" '
            f'fill="{c["accent"] if warm else c["ink"]}" '
            f'opacity="{a * (0.9 if warm else 0.55):.3f}"/>'
        )

    for x, y, _ in hubs:
        a = falloff(x, y)
        body.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9.5" fill="none" '
            f'stroke="{c["accent"]}" stroke-width="1" opacity="{a * 0.5:.3f}"/>'
        )
        body.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.1" '
            f'fill="{c["accent"]}" opacity="{a * 0.95:.3f}"/>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="Ragav. Security, systems, local-first.">'
        f"{''.join(body)}</svg>"
    )

    OUT.mkdir(exist_ok=True)
    path = OUT / f"banner-{theme_name}.svg"
    path.write_text(svg, encoding="utf-8")
    print(f"{path.relative_to(HERE.parent)}  {len(svg) / 1024:.1f} KB  "
          f"{len(nodes)} nodes  {len(edges)} edges  wordmark {mark_w:.0f}px")


if __name__ == "__main__":
    for name in THEMES:
        render(name)
