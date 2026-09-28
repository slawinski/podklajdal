from typer.testing import CliRunner

from podklajdal import __version__
from podklajdal.cli import STARTUP_LOGO, _progress_bar, app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_missing_url_is_input_error() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 2
    assert "expected a single YouTube video URL" in result.output


def test_non_youtube_url_is_input_error() -> None:
    result = runner.invoke(app, ["https://example.com/song"])
    assert result.exit_code == 2
    assert "expected a single YouTube video URL" in result.output
    assert STARTUP_LOGO.splitlines()[0] in result.output


def test_startup_logo_uses_stroked_l_variant() -> None:
    lines = STARTUP_LOGO.splitlines()
    glyph = tuple(line[33:42].rstrip() for line in lines)
    assert glyph == (
        "██╗",
        "██║  ██╗",
        "██║ ██╔╝",
        "███╔╝",
        "███████╗",
        "╚══════╝",
    )


def test_progress_bar_contains_only_hashes_and_spaces() -> None:
    bar = _progress_bar(42, 10)
    assert bar == "####      "
    assert len(bar) == 10
