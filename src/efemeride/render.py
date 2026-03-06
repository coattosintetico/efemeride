"""SVG rendering for efemeride."""

from pathlib import Path

import drawsvg as draw

from efemeride.core import BodyPoint, SkyChart, StarPoint

SVG_SIZE = 800
SVG_CENTER = SVG_SIZE / 2
SVG_RADIUS = SVG_SIZE * 0.47

PLANET_STYLE: dict[str, dict] = {
    "Mercury": {"color": "#b0b0b0", "radius": 4},
    "Venus":   {"color": "#fffacd", "radius": 5},
    "Mars":    {"color": "#ff4500", "radius": 5},
    "Jupiter": {"color": "#f5deb3", "radius": 7},
    "Saturn":  {"color": "#d2b48c", "radius": 6},
    "Uranus":  {"color": "#7fffd4", "radius": 4},
    "Neptune": {"color": "#4169e1", "radius": 4},
}
SUN_STYLE  = {"color": "#ffe033", "radius": 12}
MOON_STYLE = {"color": "#d0d0d0", "radius": 10}

MAG_BASE = 4.0
MAG_OFFSET = 2.0


def norm_to_px(x: float, y: float) -> tuple[float, float]:
    """Convert normalised chart coordinates to SVG pixel coordinates."""
    px = SVG_CENTER + x * SVG_RADIUS
    py = SVG_CENTER - y * SVG_RADIUS  # flip Y for SVG
    return px, py


def star_radius(magnitude: float) -> float:
    return max(0.5, MAG_BASE / (magnitude + MAG_OFFSET))


def _body_style(name: str) -> dict:
    if name == "Sun":
        return SUN_STYLE
    if name == "Moon":
        return MOON_STYLE
    return PLANET_STYLE.get(name, {"color": "#ffffff", "radius": 4})


def render_chart(chart: SkyChart, title: str) -> str:
    d = draw.Drawing(SVG_SIZE, SVG_SIZE)

    # Background
    d.append(draw.Rectangle(0, 0, SVG_SIZE, SVG_SIZE, fill="#0a0a1a"))

    # Horizon circle
    d.append(draw.Circle(SVG_CENTER, SVG_CENTER, SVG_RADIUS,
                         fill="none", stroke="#334", stroke_width=1.5))

    # Compass labels
    label_offset = SVG_RADIUS + 16
    for label, dx, dy in [("N", 0, -1), ("S", 0, 1), ("E", -1, 0), ("W", 1, 0)]:
        lx = SVG_CENTER + dx * label_offset
        ly = SVG_CENTER + dy * label_offset
        d.append(draw.Text(label, 13, lx, ly,
                           fill="#556", font_family="sans-serif",
                           text_anchor="middle", dominant_baseline="middle"))

    # Title
    d.append(draw.Text(title, 14, SVG_CENTER, 18,
                       fill="#778", font_family="sans-serif",
                       text_anchor="middle"))

    # Stars
    for star in chart.stars:
        px, py = norm_to_px(star.x, star.y)
        sr = star_radius(star.magnitude)
        d.append(draw.Circle(px, py, sr, fill="#ffffff"))

    # Bodies (Sun, Moon, planets)
    for body in chart.bodies:
        px, py = norm_to_px(body.x, body.y)
        style = _body_style(body.name)
        d.append(draw.Circle(px, py, style["radius"], fill=style["color"]))
        d.append(draw.Text(body.name, 10, px, py - style["radius"] - 4,
                           fill=style["color"], font_family="sans-serif",
                           text_anchor="middle"))

    return d.as_svg()


def render_charts(
    visible: SkyChart,
    nonvisible: SkyChart,
    output_dir: Path,
    timestamp: str,
) -> tuple[Path, Path]:
    """Write both SVG charts to output_dir and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)

    visible_path = output_dir / f"{timestamp}_visible.svg"
    nonvisible_path = output_dir / f"{timestamp}_non-visible.svg"

    visible_path.write_text(render_chart(visible, "Visible sky"))
    nonvisible_path.write_text(render_chart(nonvisible, "Non-visible sky"))

    return visible_path, nonvisible_path
