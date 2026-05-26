from typer.testing import CliRunner

from chatgpt_haber.cli import app


runner = CliRunner()


def test_build_help():
    result = runner.invoke(app, ["build", "--help"])
    assert result.exit_code == 0
    assert "paper-size" in result.stdout
