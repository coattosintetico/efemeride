"""Post-processing SVG visual effects for efemeride.

This module operates on raw SVG strings produced by render.py,
injecting SVG filter definitions and attributes to enhance aesthetics.
It is fully independent from the rendering logic.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


@dataclass
class EffectParams:
    """Tweakable parameters for all available effects.

    Set any value to 0 (or False) to disable that effect.
    """

    # Star glow: gaussian blur behind each star circle.
    # Value is the blur stdDeviation (0 = off, try 2-6).
    star_glow: float = 0.0

    # Body glow: gaussian blur behind sun/moon/planet circles.
    body_glow: float = 0.0

    # Background radial gradient: darkens edges to give depth.
    # Value is the opacity of the dark vignette ring (0 = off, 0.3-0.7 typical).
    vignette: float = 0.0

    # Star radial gradient fill: replace flat white with a center-bright
    # radial gradient that fades to transparent at the edge.
    # Value is the edge opacity (0 = off / keep flat fill, 0.0-0.3 typical).
    star_soft_edge: float = 0.0

    # Global bloom: a full-scene gaussian blur composited on top with 'screen'.
    # Value is the blur stdDeviation (0 = off, try 1-3).
    scene_bloom: float = 0.0

    # Constellation line opacity multiplier (1.0 = unchanged, 0.3 = subtle).
    constellation_opacity: float = 1.0


# ---------------------------------------------------------------------------
# Internal SVG manipulation helpers
# ---------------------------------------------------------------------------

_NS = {"svg": "http://www.w3.org/2000/svg"}


def _register_namespaces() -> None:
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def _parse(svg_text: str) -> ET.Element:
    _register_namespaces()
    return ET.fromstring(svg_text)


def _serialize(root: ET.Element) -> str:
    return ET.tostring(root, encoding="unicode")


def _get_or_create_defs(root: ET.Element) -> ET.Element:
    defs = root.find("svg:defs", _NS)
    if defs is None:
        defs = ET.SubElement(root, "defs")
        root.insert(0, defs)
    return defs


# ---------------------------------------------------------------------------
# Individual effect applicators
# ---------------------------------------------------------------------------

def _apply_star_glow(root: ET.Element, defs: ET.Element, std_dev: float) -> None:
    """Add a glow filter and apply it to star circles (small white circles)."""
    filt = ET.SubElement(defs, "filter", id="starGlow", x="-50%", y="-50%",
                         width="200%", height="200%")
    ET.SubElement(filt, "feGaussianBlur", attrib={
        "in": "SourceGraphic", "stdDeviation": str(std_dev), "result": "blur",
    })
    merge = ET.SubElement(filt, "feMerge")
    ET.SubElement(merge, "feMergeNode", attrib={"in": "blur"})
    ET.SubElement(merge, "feMergeNode", attrib={"in": "SourceGraphic"})

    for circle in root.iter("{http://www.w3.org/2000/svg}circle"):
        fill = circle.get("fill", "")
        r = float(circle.get("r", "0"))
        if fill == "#ffffff" and r < 10:
            circle.set("filter", "url(#starGlow)")


def _apply_body_glow(root: ET.Element, defs: ET.Element, std_dev: float) -> None:
    """Add a glow filter for solar-system bodies."""
    filt = ET.SubElement(defs, "filter", id="bodyGlow", x="-50%", y="-50%",
                         width="200%", height="200%")
    ET.SubElement(filt, "feGaussianBlur", attrib={
        "in": "SourceGraphic", "stdDeviation": str(std_dev), "result": "blur",
    })
    merge = ET.SubElement(filt, "feMerge")
    ET.SubElement(merge, "feMergeNode", attrib={"in": "blur"})
    ET.SubElement(merge, "feMergeNode", attrib={"in": "SourceGraphic"})

    for circle in root.iter("{http://www.w3.org/2000/svg}circle"):
        fill = circle.get("fill", "")
        r = float(circle.get("r", "0"))
        # Bodies have colored fills and r >= 4; exclude horizon circle (fill=none)
        # and stars (fill=#ffffff).
        if fill not in ("#ffffff", "none", "") and r >= 4:
            circle.set("filter", "url(#bodyGlow)")


def _apply_vignette(root: ET.Element, defs: ET.Element, opacity: float) -> None:
    """Overlay a radial gradient that darkens the edges of the chart."""
    grad = ET.SubElement(defs, "radialGradient", id="vignette")
    ET.SubElement(grad, "stop", offset="60%", attrib={
        "stop-color": "transparent",
    })
    ET.SubElement(grad, "stop", offset="100%", attrib={
        "stop-color": f"rgba(0,0,0,{opacity})",
    })

    # Find the first rectangle (background) to get dimensions.
    rect = root.find(".//{http://www.w3.org/2000/svg}rect")
    if rect is not None:
        w = rect.get("width", "800")
        h = rect.get("height", "800")
        vignette_rect = ET.SubElement(root, "rect", x="0", y="0",
                                       width=w, height=h,
                                       fill="url(#vignette)")
        # Insert right after background rect.
        root.remove(vignette_rect)
        idx = list(root).index(rect)
        root.insert(idx + 1, vignette_rect)


def _apply_star_soft_edge(root: ET.Element, defs: ET.Element, edge_opacity: float) -> None:
    """Replace flat star fills with a radial gradient (bright center, fading edge)."""
    grad = ET.SubElement(defs, "radialGradient", id="starSoft")
    ET.SubElement(grad, "stop", offset="0%", attrib={
        "stop-color": "#ffffff", "stop-opacity": "1",
    })
    ET.SubElement(grad, "stop", offset="100%", attrib={
        "stop-color": "#ffffff", "stop-opacity": str(edge_opacity),
    })

    for circle in root.iter("{http://www.w3.org/2000/svg}circle"):
        if circle.get("fill") == "#ffffff" and float(circle.get("r", "0")) < 10:
            circle.set("fill", "url(#starSoft)")


def _apply_scene_bloom(root: ET.Element, defs: ET.Element, std_dev: float) -> None:
    """Apply a subtle full-scene bloom (blur + screen composite)."""
    filt = ET.SubElement(defs, "filter", id="sceneBloom", x="0", y="0",
                         width="100%", height="100%")
    ET.SubElement(filt, "feGaussianBlur", attrib={
        "in": "SourceGraphic", "stdDeviation": str(std_dev), "result": "bloom",
    })
    ET.SubElement(filt, "feBlend", attrib={
        "in": "SourceGraphic", "in2": "bloom", "mode": "screen",
    })

    # Wrap all existing children in a <g> with the filter.
    g = ET.Element("g", filter="url(#sceneBloom)")
    children = list(root)
    defs_elem = root.find("svg:defs", _NS) or root.find("defs")
    for child in children:
        if child.tag.endswith("defs") or child is defs_elem:
            continue
        root.remove(child)
        g.append(child)
    root.append(g)


def _apply_constellation_opacity(root: ET.Element, opacity: float) -> None:
    """Scale opacity of constellation lines."""
    for line in root.iter("{http://www.w3.org/2000/svg}line"):
        stroke = line.get("stroke", "")
        if stroke == "#1a3a5c":
            line.set("opacity", str(opacity))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_effects(svg_text: str, params: EffectParams | None = None) -> str:
    """Apply visual effects to an SVG string and return the modified SVG.

    If params is None or all values are at their defaults (off), the SVG
    is returned unchanged.
    """
    if params is None:
        return svg_text

    root = _parse(svg_text)
    defs = _get_or_create_defs(root)

    if params.star_soft_edge > 0:
        _apply_star_soft_edge(root, defs, params.star_soft_edge)

    if params.star_glow > 0:
        _apply_star_glow(root, defs, params.star_glow)

    if params.body_glow > 0:
        _apply_body_glow(root, defs, params.body_glow)

    if params.vignette > 0:
        _apply_vignette(root, defs, params.vignette)

    if params.constellation_opacity != 1.0:
        _apply_constellation_opacity(root, params.constellation_opacity)

    # Scene bloom goes last — it wraps everything.
    if params.scene_bloom > 0:
        _apply_scene_bloom(root, defs, params.scene_bloom)

    return _serialize(root)
