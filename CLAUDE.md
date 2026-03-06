# efemeride

## Purpose
CLI tool that computes the astronomical ephemeris for a given date/time and observer location,
then generates two SVG star charts: one for the visible sky (above horizon) and one for the
non-visible sky (below horizon), using stereographic projection.

## User background
The user studied physics and has a background in the subject, but is refreshing their astronomy
knowledge. When asked to explain astronomical or mathematical concepts (e.g. what magnitude is,
what coordinate systems are used, how stereographic projection works), Claude should explain
clearly and with appropriate depth — but should NOT proactively explain these things on every
interaction unless asked.

## CLI interface (typer)

```
efemeride chart [OPTIONS]
```

Options:
- `--lat FLOAT`      Observer latitude (default: 42.887368053811635)
- `--lon FLOAT`      Observer longitude (default: -8.5251265216666)
- `--time TEXT`      ISO 8601 datetime string; defaults to current UTC time
- `--mag-limit FLOAT` Maximum (faintest) magnitude to include for stars (default: 6.5)
- `-o / --output PATH` Output directory (default: `./output/`)

Output files:
- `YYYY-MM-DD_HH-MM-SS_visible.svg`
- `YYYY-MM-DD_HH-MM-SS_non-visible.svg`

The timestamp in the filename is the time the ephemeris was computed for (not the current time).

## Objects to plot
- **Stars**: Hipparcos catalog, filtered by magnitude limit
- **Planets**: Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune
- **Sun** and **Moon**

## SVG aesthetics (minimal, first iteration)
- Stars: circle size inversely proportional to magnitude (brighter = larger)
- Sun: distinct color (e.g. yellow)
- Moon: distinct color (e.g. light grey/silver)
- Planets: each has a manually configured color and size
- Minimal labels (object names, maybe magnitude for bright stars)
- Two separate SVG files (visible / non-visible), not combined

## Projection
Stereographic projection from the celestial sphere onto a 2D circle.
- Visible chart: projected from the zenith (north up, east left — standard sky chart convention)
- Non-visible chart: projected from the nadir

## Data downloads (skyfield)
Skyfield downloads ephemeris data on first use and caches it locally:
- `de421.bsp` (~17 MB) — planetary positions
- `hip_main.dat` — Hipparcos star catalog (~7 MB)
Cache directory: default skyfield behavior (project root or `~/.skyfield/`), can be configured.
Network requests are acceptable.

## Coding style and architecture

- **Simple is best.** This is a personal project — no production-grade complexity. Code should be
  readable, clean, and easy to understand.
- **`cli.py` is a thin layer only.** It should contain nothing but typer argument declarations and
  calls to functions defined in submodules. No business logic in the CLI layer.
- **Modularity matters.** Logic lives in its appropriate submodule (`core.py` for astronomy,
  `render.py` for SVG). Functions should be small, well-named, and single-purpose.
- Prefer explicit over clever. Avoid abstractions that aren't justified by the current code.

## Tech stack
- `skyfield` — astronomical calculations
- `typer` — CLI
- `uv` — dependency management (always use `uv add`, never edit pyproject.toml directly)
- `ruff` — linting/formatting
- `pytest` — tests

## Project structure
```
src/efemeride/
  cli.py     — typer app and commands
  core.py    — astronomical computation logic
  render.py  — SVG generation (to be created)
tests/
output/      — default SVG output directory (gitignored)
```
