"""CLI interface for efemeride."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from efemeride.core import compute_charts
from efemeride.render import render_charts

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
) -> None:
    """Generate SVG star charts for a given time and observer location."""
    dt = datetime.fromisoformat(time) if time else datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")
    visible, nonvisible = compute_charts(lat=lat, lon=lon, dt=dt, mag_limit=mag_limit)
    p1, p2 = render_charts(visible, nonvisible, output, timestamp)
    typer.echo(f"Wrote {p1}")
    typer.echo(f"Wrote {p2}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
