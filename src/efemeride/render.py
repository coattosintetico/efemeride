"""SVG rendering for efemeride."""

from dataclasses import dataclass
from pathlib import Path

import drawsvg as draw

from efemeride.core import SkyChart
from efemeride.effects import EffectParams, apply_effects

SVG_SIZE = 800
SVG_CENTER = SVG_SIZE / 2
SVG_RADIUS = SVG_SIZE * 0.47

PLANET_STYLE: dict[str, dict] = {
    "Mercury": {"color": "#b0b0b0", "radius": 4},
    "Venus": {"color": "#fffacd", "radius": 5},
    "Mars": {"color": "#ff4500", "radius": 5},
    "Jupiter": {"color": "#f5deb3", "radius": 7},
    "Saturn": {"color": "#d2b48c", "radius": 6},
    "Uranus": {"color": "#7fffd4", "radius": 4},
    "Neptune": {"color": "#4169e1", "radius": 4},
}
SUN_STYLE = {"color": "#ffe033", "radius": 12}
MOON_STYLE = {"color": "#d0d0d0", "radius": 10}

# Brightest magnitude we expect (Sirius is -1.46)
MAG_BRIGHTEST = -1.5
# Rendered radius range (in SVG viewBox units)
STAR_RADIUS_MAX = 3.5
STAR_RADIUS_MIN = 0.3
# Opacity range
STAR_OPACITY_MAX = 1.0
STAR_OPACITY_MIN = 0.15

CONSTELLATION_STROKE = "#1a3a5c"
CONSTELLATION_STROKE_WIDTH = 0.6
CONSTELLATION_LABEL_COLOR = "rgba(255,255,255,0.3)"


@dataclass
class GridStyle:
    """Visual style for declination grid circles."""

    stroke_color: str = "#335"
    stroke_width: float = 0.5
    stroke_opacity: float = 0.3
    dash_array: str = "4,4"
    label_color: str = "rgba(255,255,255,0.25)"
    label_size: int = 9
    show_labels: bool = True


def norm_to_px(x: float, y: float) -> tuple[float, float]:
    """Convert normalised chart coordinates to SVG pixel coordinates."""
    px = SVG_CENTER + x * SVG_RADIUS
    py = SVG_CENTER - y * SVG_RADIUS  # flip Y for SVG
    return px, py


def _star_t(magnitude: float, mag_limit: float) -> float:
    """Return 0.0 for the brightest star, 1.0 for a star at mag_limit."""
    return (magnitude - MAG_BRIGHTEST) / (mag_limit - MAG_BRIGHTEST)


def star_radius(magnitude: float, mag_limit: float) -> float:
    t = _star_t(magnitude, mag_limit)
    return STAR_RADIUS_MAX + t * (STAR_RADIUS_MIN - STAR_RADIUS_MAX)


def star_opacity(magnitude: float, mag_limit: float) -> float:
    t = _star_t(magnitude, mag_limit)**2
    return STAR_OPACITY_MAX + t * (STAR_OPACITY_MIN - STAR_OPACITY_MAX)


def _body_style(name: str) -> dict:
    if name == "Sun":
        return SUN_STYLE
    if name == "Moon":
        return MOON_STYLE
    return PLANET_STYLE.get(name, {"color": "#ffffff", "radius": 4})


def render_chart(chart: SkyChart, title: str, grid_style: GridStyle | None = None) -> str:
    d = draw.Drawing(SVG_SIZE, SVG_SIZE)
    d.width = "100%"
    d.height = "100%"

    # Background
    d.append(draw.Rectangle(0, 0, SVG_SIZE, SVG_SIZE, fill="#ffffff"))

    # Horizon circle
    d.append(draw.Circle(SVG_CENTER, SVG_CENTER, SVG_RADIUS, fill="none", stroke="#334", stroke_width=1.5))

    # Compass labels
    label_offset = SVG_RADIUS + 16
    for label, dx, dy in [("N", 0, -1), ("S", 0, 1), ("E", -1, 0), ("W", 1, 0)]:
        lx = SVG_CENTER + dx * label_offset
        ly = SVG_CENTER + dy * label_offset
        d.append(
            draw.Text(
                label,
                13,
                lx,
                ly,
                fill="#556",
                font_family="sans-serif",
                text_anchor="middle",
                dominant_baseline="middle",
            )
        )

    # Title
    # d.append(draw.Text(title, 14, SVG_CENTER, 18, fill="#778", font_family="sans-serif", text_anchor="middle"))

    # Declination grid circles
    if grid_style and chart.grid_circles:
        for circle in chart.grid_circles:
            for arc in circle.arcs:
                if len(arc.points) < 2:
                    continue
                p = draw.Path(
                    fill="none",
                    stroke=grid_style.stroke_color,
                    stroke_width=grid_style.stroke_width,
                    stroke_opacity=grid_style.stroke_opacity,
                    stroke_dasharray=grid_style.dash_array,
                )
                px0, py0 = norm_to_px(*arc.points[0])
                p.M(px0, py0)
                for x, y in arc.points[1:]:
                    px, py = norm_to_px(x, y)
                    p.L(px, py)
                d.append(p)

            # Label at midpoint of longest arc
            # if grid_style.show_labels and circle.arcs:
            #     longest = max(circle.arcs, key=lambda a: len(a.points))
            #     mid = longest.points[len(longest.points) // 2]
            #     lx, ly = norm_to_px(mid[0], mid[1])
            #     d.append(
            #         draw.Text(
            #             circle.label,
            #             grid_style.label_size,
            #             lx,
            #             ly,
            #             fill=grid_style.label_color,
            #             font_family="sans-serif",
            #             text_anchor="middle",
            #             dominant_baseline="middle",
            #         )
            #     )

    # Constellation lines and labels
    for constellation in chart.constellations:
        if not constellation.segments:
            continue
        all_x: list[float] = []
        all_y: list[float] = []
        for seg in constellation.segments:
            px1, py1 = norm_to_px(seg.x1, seg.y1)
            px2, py2 = norm_to_px(seg.x2, seg.y2)
            d.append(
                draw.Line(px1, py1, px2, py2, stroke=CONSTELLATION_STROKE, stroke_width=CONSTELLATION_STROKE_WIDTH)
            )
            all_x.extend([px1, px2])
            all_y.extend([py1, py2])
        # cx = sum(all_x) / len(all_x)
        # cy = sum(all_y) / len(all_y)
        # d.append(
        #     draw.Text(
        #         constellation.abbr,
        #         9,
        #         cx,
        #         cy,
        #         fill=CONSTELLATION_LABEL_COLOR,
        #         font_family="sans-serif",
        #         text_anchor="middle",
        #         dominant_baseline="middle",
        #     )
        # )

    # Stars
    for star in chart.stars:
        px, py = norm_to_px(star.x, star.y)
        sr = star_radius(star.magnitude, chart.mag_limit)
        so = star_opacity(star.magnitude, chart.mag_limit)
        d.append(draw.Circle(px, py, sr, fill="#000000", fill_opacity=so))

    # Bodies (Sun, Moon, planets)
    for body in chart.bodies:
        px, py = norm_to_px(body.x, body.y)
        style = _body_style(body.name)
        d.append(draw.Circle(px, py, style["radius"], fill=style["color"]))
        # d.append(
        #     draw.Text(
        #         body.name,
        #         10,
        #         px,
        #         py - style["radius"] - 4,
        #         fill=style["color"],
        #         font_family="sans-serif",
        #         text_anchor="middle",
        #     )
        # )

    return d.as_svg()


def render_charts(
    visible: SkyChart,
    nonvisible: SkyChart,
    output_dir: Path,
    timestamp: str,
    effects: EffectParams | None = None,
    grid_style: GridStyle | None = None,
) -> tuple[Path, Path]:
    """Write both SVG charts to output_dir and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)

    visible_path = output_dir / f"{timestamp}_visible.svg"
    nonvisible_path = output_dir / f"{timestamp}_non-visible.svg"

    # visible_path.write_text(apply_effects(render_chart(visible, "Visible sky", grid_style), effects))
    # nonvisible_path.write_text(apply_effects(render_chart(nonvisible, "Non-visible sky", grid_style), effects))
    visible_path.write_text(render_chart(visible, "Visible sky", grid_style))
    nonvisible_path.write_text(render_chart(nonvisible, "Non-visible sky", grid_style))

    return visible_path, nonvisible_path
