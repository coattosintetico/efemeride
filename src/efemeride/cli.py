"""CLI interface for efemeride."""

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from efemeride.core import compute_charts
from efemeride.effects import EffectParams, apply_effects
from efemeride.render import SVG_CHART_SIZE, GridStyle, render_charts

app = typer.Typer(
    name="efemeride",
    help="Compute astronomical ephemeris and generate SVG star charts.",
    no_args_is_help=True,
)

DEFAULT_LAT = 42.887368053811635
DEFAULT_LON = -8.5251265216666


@app.command()
def chart(
    lat: float = typer.Option(DEFAULT_LAT, help="Observer latitude"),
    lon: float = typer.Option(DEFAULT_LON, help="Observer longitude"),
    time: Optional[str] = typer.Option(None, help="ISO 8601 datetime string (default: now UTC)"),
    mag_limit: float = typer.Option(6.5, help="Maximum (faintest) magnitude to include for stars"),
    output: Path = typer.Option(Path("./output/"), "-o", help="Output directory"),
    open: bool = typer.Option(True, "--open", help="Open output files with xdg-open after generation"),
    # Visual effects
    star_glow: float = typer.Option(3.0, help="Star glow blur radius (0=off, try 2-6)"),
    body_glow: float = typer.Option(5.0, help="Body glow blur radius (0=off, try 3-8)"),
    vignette: float = typer.Option(0.4, help="Edge vignette opacity (0=off, 0.3-0.7 typical)"),
    star_soft_edge: float = typer.Option(0.15, help="Star radial fade edge opacity (0=off, 0.0-0.3 typical)"),
    scene_bloom: float = typer.Option(0.0, help="Full-scene bloom blur (0=off, try 1-3)"),
    constellation_opacity: float = typer.Option(0.5, help="Constellation line opacity (1.0=unchanged, 0.3=subtle)"),
    # Declination grid
    grid: bool = typer.Option(True, "--grid/--no-grid", help="Draw declination grid circles"),
    grid_step: float = typer.Option(30.0, help="Declination grid step in degrees"),
    grid_opacity: float = typer.Option(0.3, help="Declination grid line opacity"),
) -> None:
    """Generate SVG star charts for a given time and observer location."""
    dt = datetime.fromisoformat(time) if time else datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")
    declinations = None
    if grid:
        step = int(grid_step)
        declinations = [float(d) for d in range(-60, 91, step) if -90 <= d <= 90]
    visible, nonvisible = compute_charts(lat=lat, lon=lon, dt=dt, mag_limit=mag_limit, declinations=declinations)
    grid_style = GridStyle(stroke_opacity=grid_opacity) if grid else None
    effects = EffectParams(
        star_glow=star_glow,
        body_glow=body_glow,
        vignette=vignette,
        star_soft_edge=star_soft_edge,
        scene_bloom=scene_bloom,
        constellation_opacity=constellation_opacity,
    )
    p1, p2, poster = render_charts(visible, nonvisible, output, timestamp, effects, grid_style)
    typer.echo(f"Wrote {p1}")
    typer.echo(f"Wrote {p2}")
    typer.echo(f"Wrote {poster}")
    if open:
        subprocess.Popen(["xdg-open", poster.resolve().as_uri()])


def main() -> None:
    app()


if __name__ == "__main__":
    main()
