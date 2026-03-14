# efemeride

A CLI tool to compute the astronomical ephemeris (precise location of the stars on the sky) at a given time, and generate an SVG of it.

## Requirements

[uv](https://docs.astral.sh/uv/) — install it with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation

Install the CLI globally:

```bash
just install-cli
```

Or without [`just`](https://github.com/casey/just/):

```bash
uv tool install -e .
```

List possible just commands with:

```
just -l
```

## Usage

```bash
efemeride --help
```

You can also run without installing:

```bash
uv run efemeride --help
```

or as a module (this runs the CLI):

```bash
uv run python -m efemeride --help
```

## Development

Set up the development environment:

```bash
just sync-dev
```

# Links

- [drawsvg github](https://github.com/cduck/drawsvg)
- [drawsvg quick reference](https://cduck.github.io/drawsvg)
