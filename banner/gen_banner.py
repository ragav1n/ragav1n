"""Generate the profile banner SVGs, one per GitHub theme.

GitHub serves README images through an <img> tag, which cannot fetch web fonts.
Live <text> would fall back to a different face on every OS, so every glyph here
is outlined to a path.

The artwork is a topographic contour field: a seeded sum of Gaussian bumps,
traced at fixed heights with marching squares. Everything is deterministic, so
re-running this produces byte-identical output.

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

TAGLINE = "security · systems · detection"

COLS, ROWS = 340, 84
BUMPS = 15
# Every third contour is drawn heavier, the way an index contour is on a real
# topographic map.
LEVELS = [round(-0.96 + i * 0.12, 3) for i in range(17)]
INDEX_EVERY = 3

THEMES = {
    "light": {"ink": "#0b0d10", "muted": "#5b6570", "line": "#4a5560", "accent": "#0f7d8f"},
    "dark": {"ink": "#e8eef4", "muted": "#8b949e", "line": "#9fb0bd", "accent": "#4cc3d9"},
}


def load(name, axes=None):
    font = TTFont(FONTS / name)
    if axes:
        instantiateVariableFont(font, axes, inplace=True)
    return font


def outline(font, text, size, origin, tracking=0.0, fill="#000"):
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
    # Fonts draw y-up, SVG draws y-down, so the group flips the axis.
    group = (
        f'<g transform="translate({origin[0]} {origin[1]}) scale({scale:.6f} {-scale:.6f})"'
        f' fill="{fill}">{"".join(parts)}</g>'
    )
    return group, width


def build_grid(rng):
    """Sample a sum of Gaussian bumps over the canvas.

    Distances are measured in units of the canvas height so the contours come
    out round rather than smeared across the 4.9:1 canvas.
    """
    aspect = W / H
    # Weighted to the right, since the mask hides everything under the wordmark.
    bumps = [
        (
            rng.uniform(1.05, aspect + 0.40),
            rng.uniform(-0.30, 1.30),
            rng.uniform(0.17, 0.46),
            rng.choice((-1, 1)) * rng.uniform(0.65, 1.15),
        )
        for _ in range(BUMPS)
    ]

    grid = []
    for j in range(ROWS + 1):
        y = j / ROWS
        row = []
        for i in range(COLS + 1):
            x = (i / COLS) * aspect
            total = 0.0
            for cx, cy, radius, amp in bumps:
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                total += amp * math.exp(-d2 / (2 * radius * radius))
            row.append(total)
        grid.append(row)
    return grid


def _interp(p1, v1, p2, v2, level):
    if abs(v2 - v1) < 1e-12:
        t = 0.5
    else:
        t = (level - v1) / (v2 - v1)
    return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)


def march(grid, level):
    """Marching squares. Returns unordered segments at the given height."""
    segments = []
    for j in range(ROWS):
        for i in range(COLS):
            x0, x1 = i / COLS * W, (i + 1) / COLS * W
            y0, y1 = j / ROWS * H, (j + 1) / ROWS * H
            v00, v10 = grid[j][i], grid[j][i + 1]
            v11, v01 = grid[j + 1][i + 1], grid[j + 1][i]

            case = (
                (1 if v00 >= level else 0)
                | (2 if v10 >= level else 0)
                | (4 if v11 >= level else 0)
                | (8 if v01 >= level else 0)
            )
            if case in (0, 15):
                continue

            top = _interp((x0, y0), v00, (x1, y0), v10, level)
            right = _interp((x1, y0), v10, (x1, y1), v11, level)
            bottom = _interp((x0, y1), v01, (x1, y1), v11, level)
            left = _interp((x0, y0), v00, (x0, y1), v01, level)

            if case in (1, 14):
                segments.append((left, top))
            elif case in (2, 13):
                segments.append((top, right))
            elif case in (3, 12):
                segments.append((left, right))
            elif case in (4, 11):
                segments.append((right, bottom))
            elif case in (6, 9):
                segments.append((top, bottom))
            elif case in (7, 8):
                segments.append((left, bottom))
            elif case == 5:
                segments.append((left, top))
                segments.append((right, bottom))
            elif case == 10:
                segments.append((top, right))
                segments.append((left, bottom))
    return segments


def chain(segments):
    """Join loose segments into polylines so each contour is one path."""
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    ends = {}
    for idx, (a, b) in enumerate(segments):
        ends.setdefault(key(a), []).append(idx)
        ends.setdefault(key(b), []).append(idx)

    used = [False] * len(segments)
    paths = []

    for start in range(len(segments)):
        if used[start]:
            continue
        used[start] = True
        a, b = segments[start]
        line = [a, b]

        # Walk forward from the tail, then backward from the head.
        for direction in (0, 1):
            while True:
                tip = line[-1] if direction == 0 else line[0]
                nxt = None
                for idx in ends.get(key(tip), ()):
                    if used[idx]:
                        continue
                    p, q = segments[idx]
                    if key(p) == key(tip):
                        nxt, point = idx, q
                        break
                    if key(q) == key(tip):
                        nxt, point = idx, p
                        break
                if nxt is None:
                    break
                used[nxt] = True
                if direction == 0:
                    line.append(point)
                else:
                    line.insert(0, point)

        if len(line) > 3:
            paths.append(line)
    return paths


def to_d(points):
    """Emit a path, dropping points too close together to see."""
    out = [f"M{points[0][0]:.1f} {points[0][1]:.1f}"]
    lx, ly = points[0]
    for x, y in points[1:]:
        if abs(x - lx) < 1.4 and abs(y - ly) < 1.4:
            continue
        out.append(f"L{x:.1f} {y:.1f}")
        lx, ly = x, y
    return "".join(out)


def render(theme_name):
    c = THEMES[theme_name]
    rng = random.Random(SEED)
    grid = build_grid(rng)

    grotesk = load("SpaceGroteskVF.ttf", {"wght": 500})
    mono = load("JetBrainsMono.ttf")

    # The contours run under the whole canvas and a gradient mask dissolves them
    # before they reach the wordmark or the right crop. A second, narrower mask
    # sweeps a band of accent colour across the same paths, which is the only
    # moving part of the banner.
    defs = (
        "<defs>"
        '<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset="0.30" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset="0.56" stop-color="#fff" stop-opacity="1"/>'
        '<stop offset="0.88" stop-color="#fff" stop-opacity="1"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        "</linearGradient>"
        f'<mask id="fadeout"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>'
        '<linearGradient id="band" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset="0.5" stop-color="#fff" stop-opacity="1"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        "</linearGradient>"
        # SMIL rather than a CSS keyframe: an SVG loaded through <img> renders in
        # a restricted mode, and SMIL is the animation that reliably plays there.
        f'<mask id="sweep"><rect class="band" x="-320" y="0" width="300" height="{H}" '
        'fill="url(#band)">'
        f'<animate attributeName="x" dur="9s" repeatCount="indefinite" '
        f'calcMode="linear" keyTimes="0;0.58;1" values="-320;{W + 40};{W + 40}"/>'
        "</rect></mask>"
        "</defs>"
        # CSS cannot stop SMIL, but hiding the band empties the mask, which
        # leaves the contours static for anyone who asked for less motion.
        "<style>@media (prefers-reduced-motion:reduce){.band{display:none}}</style>"
    )

    heavy, light = [], []
    for n, level in enumerate(LEVELS):
        target = heavy if n % INDEX_EVERY == 0 else light
        for line in chain(march(grid, level)):
            target.append(f'<path d="{to_d(line)}"/>')

    contours = heavy + light
    # Each contour is defined once and drawn twice by reference: dim underneath,
    # accent inside the sweep band. Repeating the path data would double the file.
    shapes = (
        f'<g id="ridge" stroke-width="1.15">{"".join(heavy)}</g>'
        f'<g id="minor" stroke-width="0.75">{"".join(light)}</g>'
    )

    def draw(stroke, a, b):
        return (
            f'<use href="#ridge" xlink:href="#ridge" stroke="{stroke}" opacity="{a}"/>'
            f'<use href="#minor" xlink:href="#minor" stroke="{stroke}" opacity="{b}"/>'
        )

    body = [
        defs.replace("</defs>", shapes + "</defs>"),
        f'<g fill="none" mask="url(#fadeout)">{draw(c["line"], 0.5, 0.3)}'
        f'<g mask="url(#sweep)">{draw(c["accent"], 0.95, 0.8)}</g></g>',
    ]

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

    # GitHub renders a profile README in a 666px column, so this 1280-wide
    # canvas lands at roughly half scale. The tagline is sized for that.
    tagline, _ = outline(
        mono, TAGLINE, size=20, origin=(left + 2, 222), tracking=0.14, fill=c["muted"]
    )
    body.append(tagline)

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="Ragav. Security, systems, detection.">'
        f"{''.join(body)}</svg>"
    )

    OUT.mkdir(exist_ok=True)
    path = OUT / f"banner-{theme_name}.svg"
    path.write_text(svg, encoding="utf-8")
    print(f"{path.relative_to(HERE.parent)}  {len(svg) / 1024:.1f} KB  "
          f"{len(contours)} contour paths  wordmark {mark_w:.0f}px")


if __name__ == "__main__":
    for name in THEMES:
        render(name)
