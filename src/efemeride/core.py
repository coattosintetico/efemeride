"""Core logic for efemeride."""

import math
from datetime import datetime

import numpy as np
from pydantic import BaseModel
from skyfield.api import Loader, Star, wgs84
from skyfield.data import hipparcos


class StarPoint(BaseModel):
    x: float
    y: float
    magnitude: float


class BodyPoint(BaseModel):
    name: str
    x: float
    y: float


class SkyChart(BaseModel):
    stars: list[StarPoint] = []
    bodies: list[BodyPoint] = []


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
    stars = Star.from_dataframe(df)
    astrometric = location.at(t).observe(stars)
    ra, dec, _ = astrometric.radec()

    # Manual alt/az to avoid .apparent() triggering buggy deflection on large arrays
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

    for alt_deg, az_deg, mag in zip(alts_deg, azs_deg, df["magnitude"]):
        if alt_deg >= 0:
            x, y = stereographic_project_visible(alt_deg, az_deg)
            visible.stars.append(StarPoint(x=x, y=y, magnitude=mag))
        else:
            x, y = stereographic_project_nonvisible(alt_deg, az_deg)
            nonvisible.stars.append(StarPoint(x=x, y=y, magnitude=mag))

    return visible, nonvisible
