"""Core logic for efemeride."""

import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
from pydantic import BaseModel
from skyfield.api import Loader, Star, wgs84
from skyfield.data import hipparcos

CONSTELLATIONS_DIR = Path(__file__).parent / "data" / "constellations"
DEFAULT_SKYCULTURE = "modern_st"


class StarPoint(BaseModel):
    x: float
    y: float
    magnitude: float


class BodyPoint(BaseModel):
    name: str
    x: float
    y: float


class ConstellationSegment(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class Constellation(BaseModel):
    abbr: str
    segments: list[ConstellationSegment] = []


class SkyChart(BaseModel):
    stars: list[StarPoint] = []
    bodies: list[BodyPoint] = []
    constellations: list[Constellation] = []


PLANETS = {
    "Mercury": "mercury",
    "Venus": "venus",
    "Mars": "mars",
    "Jupiter": "jupiter barycenter",
    "Saturn": "saturn barycenter",
    "Uranus": "uranus barycenter",
    "Neptune": "neptune barycenter",
}


def get_loader() -> Loader:
    return Loader("data")


def load_ephemeris(loader: Loader):
    return loader("de421.bsp")


def load_hipparcos(loader: Loader):
    with loader.open(hipparcos.URL) as f:
        return hipparcos.load_dataframe(f)


def stereographic_project_visible(alt_deg: float, az_deg: float) -> tuple[float, float]:
    """Project alt/az to 2D for the visible (above-horizon) chart.

    Zenith → r=0, horizon → r=1. North up, east left (standard sky chart).
    """
    theta = math.radians(90.0 - alt_deg)
    r = math.tan(theta / 2.0)
    az = math.radians(az_deg)
    x = -r * math.sin(az)
    y = r * math.cos(az)
    return x, y


def stereographic_project_nonvisible(alt_deg: float, az_deg: float) -> tuple[float, float]:
    """Project alt/az to 2D for the non-visible (below-horizon) chart.

    Nadir → r=0, horizon → r=1.
    """
    theta = math.radians(90.0 + alt_deg)  # alt < 0, so this > 90
    r = math.tan(theta / 2.0)
    az = math.radians(az_deg)
    x = -r * math.sin(az)
    y = r * math.cos(az)
    return x, y


def load_constellations(
    skyculture: str = DEFAULT_SKYCULTURE,
) -> dict[str, list[tuple[int, int]]]:
    """Parse a Stellarium skyculture JSON → dict mapping abbreviation to HIP ID pairs."""
    path = CONSTELLATIONS_DIR / f"{skyculture}.json"
    data = json.loads(path.read_text())
    constellations: dict[str, list[tuple[int, int]]] = {}
    for entry in data["constellations"]:
        abbr = entry["id"].split()[-1]
        pairs: list[tuple[int, int]] = []
        for chain in entry.get("lines", []):
            for i in range(len(chain) - 1):
                pairs.append((chain[i], chain[i + 1]))
        if pairs:
            constellations[abbr] = pairs
    return constellations


def _compute_alt_az(
    df, location, t, lat: float, lon: float
) -> tuple[np.ndarray, np.ndarray]:
    """Compute alt/az arrays for a DataFrame of Hipparcos stars."""
    stars = Star.from_dataframe(df)
    astrometric = location.at(t).observe(stars)
    ra, dec, _ = astrometric.radec()

    lst_deg = (t.gast * 15.0 + lon) % 360.0
    ha = np.radians((lst_deg - ra.degrees) % 360.0)
    d = np.radians(dec.degrees)
    phi = math.radians(lat)

    sin_alt = np.sin(phi) * np.sin(d) + np.cos(phi) * np.cos(d) * np.cos(ha)
    alts_deg = np.degrees(np.arcsin(np.clip(sin_alt, -1.0, 1.0)))
    azs_deg = np.degrees(
        np.arctan2(
            -np.cos(d) * np.sin(ha),
            np.sin(d) * np.cos(phi) - np.cos(d) * np.cos(ha) * np.sin(phi),
        )
    ) % 360.0

    return alts_deg, azs_deg


def _compute_constellation_segments(
    constellation_data: dict[str, list[tuple[int, int]]],
    hip_df,
    location,
    t,
    lat: float,
    lon: float,
) -> tuple[list[Constellation], list[Constellation]]:
    """Compute constellation segments for visible and non-visible charts."""
    # Collect all unique HIP IDs needed
    all_hip_ids: set[int] = set()
    for pairs in constellation_data.values():
        for a, b in pairs:
            all_hip_ids.add(a)
            all_hip_ids.add(b)

    # Filter hip_df to only constellation stars (index is HIP ID)
    available_ids = hip_df.index.intersection(list(all_hip_ids))
    const_df = hip_df.loc[available_ids]

    if const_df.empty:
        return [], []

    # Compute positions
    alts_deg, azs_deg = _compute_alt_az(const_df, location, t, lat, lon)

    # Build lookup: HIP ID → (x_vis, y_vis, x_nonvis, y_nonvis, is_visible)
    lookup: dict[int, tuple[float, float, float, float, bool]] = {}
    for hip_id, alt_deg, az_deg in zip(const_df.index, alts_deg, azs_deg):
        is_visible = alt_deg >= 0
        if is_visible:
            x, y = stereographic_project_visible(alt_deg, az_deg)
            lookup[hip_id] = (x, y, 0.0, 0.0, True)
        else:
            x, y = stereographic_project_nonvisible(alt_deg, az_deg)
            lookup[hip_id] = (0.0, 0.0, x, y, False)

    visible_constellations: list[Constellation] = []
    nonvisible_constellations: list[Constellation] = []

    for abbr, pairs in constellation_data.items():
        vis_segments: list[ConstellationSegment] = []
        nonvis_segments: list[ConstellationSegment] = []

        for hip_a, hip_b in pairs:
            if hip_a not in lookup or hip_b not in lookup:
                continue
            a = lookup[hip_a]
            b = lookup[hip_b]
            # Skip horizon-crossing segments
            if a[4] != b[4]:
                continue
            if a[4]:  # both visible
                vis_segments.append(
                    ConstellationSegment(x1=a[0], y1=a[1], x2=b[0], y2=b[1])
                )
            else:  # both non-visible
                nonvis_segments.append(
                    ConstellationSegment(x1=a[2], y1=a[3], x2=b[2], y2=b[3])
                )

        if vis_segments:
            visible_constellations.append(
                Constellation(abbr=abbr, segments=vis_segments)
            )
        if nonvis_segments:
            nonvisible_constellations.append(
                Constellation(abbr=abbr, segments=nonvis_segments)
            )

    return visible_constellations, nonvisible_constellations


def compute_charts(
    lat: float, lon: float, dt: datetime, mag_limit: float
) -> tuple[SkyChart, SkyChart]:
    """Compute visible and non-visible sky charts for the given observer and time."""
    loader = get_loader()
    eph = load_ephemeris(loader)
    hip_df = load_hipparcos(loader)

    ts = loader.timescale()
    t = ts.from_datetime(dt)
    observer = wgs84.latlon(lat, lon)
    earth = eph["earth"]
    location = earth + observer

    visible = SkyChart()
    nonvisible = SkyChart()

    # Sun and Moon
    for name, target_name in [("Sun", "sun"), ("Moon", "moon")]:
        target = eph[target_name]
        astrometric = location.at(t).observe(target).apparent()
        alt, az, _ = astrometric.altaz()
        alt_deg = alt.degrees
        az_deg = az.degrees
        if alt_deg >= 0:
            x, y = stereographic_project_visible(alt_deg, az_deg)
            visible.bodies.append(BodyPoint(name=name, x=x, y=y))
        else:
            x, y = stereographic_project_nonvisible(alt_deg, az_deg)
            nonvisible.bodies.append(BodyPoint(name=name, x=x, y=y))

    # Planets
    for name, target_name in PLANETS.items():
        target = eph[target_name]
        astrometric = location.at(t).observe(target).apparent()
        alt, az, _ = astrometric.altaz()
        alt_deg = alt.degrees
        az_deg = az.degrees
        if alt_deg >= 0:
            x, y = stereographic_project_visible(alt_deg, az_deg)
            visible.bodies.append(BodyPoint(name=name, x=x, y=y))
        else:
            x, y = stereographic_project_nonvisible(alt_deg, az_deg)
            nonvisible.bodies.append(BodyPoint(name=name, x=x, y=y))

    # Stars from Hipparcos
    df = hip_df.dropna(subset=["magnitude"])
    df = df[df["magnitude"] <= mag_limit]
    alts_deg, azs_deg = _compute_alt_az(df, location, t, lat, lon)

    for alt_deg, az_deg, mag in zip(alts_deg, azs_deg, df["magnitude"]):
        if alt_deg >= 0:
            x, y = stereographic_project_visible(alt_deg, az_deg)
            visible.stars.append(StarPoint(x=x, y=y, magnitude=mag))
        else:
            x, y = stereographic_project_nonvisible(alt_deg, az_deg)
            nonvisible.stars.append(StarPoint(x=x, y=y, magnitude=mag))

    # Constellations
    constellation_data = load_constellations()
    vis_const, nonvis_const = _compute_constellation_segments(
        constellation_data, hip_df, location, t, lat, lon
    )
    visible.constellations = vis_const
    nonvisible.constellations = nonvis_const

    return visible, nonvisible
