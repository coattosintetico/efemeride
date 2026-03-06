from typer.testing import CliRunner

from efemeride.cli import app

runner = CliRunner()


def test_chart_help() -> None:
    result = runner.invoke(app, ["chart", "--help"])
    assert result.exit_code == 0
    assert "--lat" in result.output
