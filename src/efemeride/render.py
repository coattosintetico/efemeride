"""SVG rendering for efemeride."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import drawsvg as dw

from efemeride.core import SkyChart
from efemeride.effects import EffectParams, apply_effects

SVG_CHART_SIZE = 800
SVG_CHART_CENTER = SVG_CHART_SIZE / 2
SVG_CHART_RADIUS = SVG_CHART_SIZE * 0.47

# SVG_POSTER_SIZE = 

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
    px = SVG_CHART_CENTER + x * SVG_CHART_RADIUS
    py = SVG_CHART_CENTER - y * SVG_CHART_RADIUS  # flip Y for SVG
    return px, py


def _star_t(magnitude: float, mag_limit: float) -> float:
    """Return 0.0 for the brightest star, 1.0 for a star at mag_limit."""
    return (magnitude - MAG_BRIGHTEST) / (mag_limit - MAG_BRIGHTEST)


def star_radius(magnitude: float, mag_limit: float) -> float:
    t = _star_t(magnitude, mag_limit)
    return STAR_RADIUS_MAX + t * (STAR_RADIUS_MIN - STAR_RADIUS_MAX)


def star_opacity(magnitude: float, mag_limit: float) -> float:
    t = _star_t(magnitude, mag_limit) ** 2
    return STAR_OPACITY_MAX + t * (STAR_OPACITY_MIN - STAR_OPACITY_MAX)


def _body_style(name: str) -> dict:
    if name == "Sun":
        return SUN_STYLE
    if name == "Moon":
        return MOON_STYLE
    return PLANET_STYLE.get(name, {"color": "#ffffff", "radius": 4})


def render_chart(chart: SkyChart, title: str, grid_style: GridStyle | None = None) -> dw.drawing.Drawing:
    d = dw.Drawing(SVG_CHART_SIZE, SVG_CHART_SIZE)
    d.width = "100%"
    d.height = "100%"

    # Background
    d.append(dw.Rectangle(0, 0, SVG_CHART_SIZE, SVG_CHART_SIZE, fill="#ffffff"))

    # Horizon circle
    d.append(dw.Circle(SVG_CHART_CENTER, SVG_CHART_CENTER, SVG_CHART_RADIUS, fill="none", stroke="#334", stroke_width=1.5))

    # Compass labels
    label_offset = SVG_CHART_RADIUS + 16
    for label, dx, dy in [("N", 0, -1), ("S", 0, 1), ("E", -1, 0), ("W", 1, 0)]:
        lx = SVG_CHART_CENTER + dx * label_offset
        ly = SVG_CHART_CENTER + dy * label_offset
        d.append(
            dw.Text(
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
    # d.append(dw.Text(title, 14, SVG_CENTER, 18, fill="#778", font_family="sans-serif", text_anchor="middle"))

    # Declination grid circles
    if grid_style and chart.grid_circles:
        for circle in chart.grid_circles:
            for arc in circle.arcs:
                if len(arc.points) < 2:
                    continue
                p = dw.Path(
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
            #         dw.Text(
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
            d.append(dw.Line(px1, py1, px2, py2, stroke=CONSTELLATION_STROKE, stroke_width=CONSTELLATION_STROKE_WIDTH))
            all_x.extend([px1, px2])
            all_y.extend([py1, py2])
        # cx = sum(all_x) / len(all_x)
        # cy = sum(all_y) / len(all_y)
        # d.append(
        #     dw.Text(
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
        d.append(dw.Circle(px, py, sr, fill="#000000", fill_opacity=so))

    # Bodies (Sun, Moon, planets)
    for body in chart.bodies:
        px, py = norm_to_px(body.x, body.y)
        style = _body_style(body.name)
        d.append(dw.Circle(px, py, style["radius"], fill=style["color"]))
        # d.append(
        #     dw.Text(
        #         body.name,
        #         10,
        #         px,
        #         py - style["radius"] - 4,
        #         fill=style["color"],
        #         font_family="sans-serif",
        #         text_anchor="middle",
        #     )
        # )

    return d


def render_charts(
    visible: SkyChart,
    nonvisible: SkyChart,
    output_dir: Path,
    timestamp: str,
    effects: EffectParams | None = None,
    grid_style: GridStyle | None = None,
) -> tuple[Path, Path, Path]:
    """Write individual chart SVGs and a merged poster to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    visible_svg = render_chart(visible, "Visible sky", grid_style).as_svg()
    nonvisible_svg = render_chart(nonvisible, "Non-visible sky", grid_style).as_svg()

    visible_path = output_dir / f"{timestamp}_visible.svg"
    nonvisible_path = output_dir / f"{timestamp}_non-visible.svg"
    poster_path = output_dir / f"{timestamp}_poster.svg"

    visible_path.write_text(visible_svg)
    nonvisible_path.write_text(nonvisible_svg)
    poster_path.write_text(merge_poster(visible_svg, nonvisible_svg))

    return visible_path, nonvisible_path, poster_path


# -- Poster merge ----------------------------------------------------------

# A2 portrait dimensions in mm
A2_WIDTH_MM = 420
A2_HEIGHT_MM = 594


def merge_poster(
    visible_svg: str,
    nonvisible_svg: str,
    *,
    margin_mm: float = 20,
    gap_mm: float = 20,
) -> str:
    """Merge two chart SVGs into a single A2 portrait poster SVG."""
    usable_w = A2_WIDTH_MM - 2 * margin_mm
    usable_h = A2_HEIGHT_MM - 2 * margin_mm - gap_mm
    chart_size = min(usable_w, usable_h / 2)

    x = (A2_WIDTH_MM - chart_size) / 2
    y_top = margin_mm
    y_bottom = margin_mm + chart_size + gap_mm

    # Build outer poster SVG with drawsvg (handles namespaces, headers, defs)
    poster = dw.Drawing(A2_WIDTH_MM, A2_HEIGHT_MM)
    poster.width = f"{A2_WIDTH_MM}mm"
    poster.height = f"{A2_HEIGHT_MM}mm"
    poster.append(dw.Rectangle(0, 0, A2_WIDTH_MM, A2_HEIGHT_MM, fill="#ffffff"))

    # Parse the outer SVG and inject charts as nested <svg> elements
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    outer = ET.fromstring(poster.as_svg())

    for svg_str, y in [(visible_svg, y_top), (nonvisible_svg, y_bottom)]:
        root = ET.fromstring(svg_str)
        root.set("x", str(x))
        root.set("y", str(y))
        root.set("width", str(chart_size))
        root.set("height", str(chart_size))
        outer.append(root)

    return ET.tostring(outer, encoding="unicode", xml_declaration=True)
