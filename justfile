# Show available tasks
default:
    @just --list

# Sync runtime dependencies only into .venv
sync:
    uv sync --no-dev

# Sync all dependencies including dev tools (ruff, etc.) into .venv
sync-dev:
    uv sync

# Install the CLI globally in editable mode for day-to-day use
install-cli:
    uv tool install -e .

# Format all files in place
format:
    uv run ruff check --fix
    uv run ruff format

# Check formatting and linting without modifying files
lint:
    uv run ruff check
    uv run ruff format --check

# Run tests
test:
    uv run pytest

# Run the chart command with defaults and open output in brave-browser
run *args:
    uv run efemeride --open {{args}}

# Open the last two generated SVGs in Brave
open:
    brave-browser $(ls -t output/*.svg | head -2 | tac) &

# Clean build artifacts
clean:
    rm -rf dist/ build/ *.egg-info .ruff_cache .pytest_cache
    find . -type d -name __pycache__ -exec rm -rf {} +
