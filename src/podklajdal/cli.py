from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.status import Status

from podklajdal import __version__
from podklajdal.application import PodklajdalApplication
from podklajdal.config import DEFAULT_OUTPUT_ROOT, MODEL_CACHE, PRODUCT_NAME
from podklajdal.domain.errors import PodklajdalError
from podklajdal.domain.job import JobRequest, JobState
from podklajdal.services.diagnostics import DiagnosticsService

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    pretty_exceptions_enable=False,
    help=(
        f"{PRODUCT_NAME}: zamienia jeden film z YouTube na pliki MP3 "
        "z wokalem i podkładem instrumentalnym."
    ),
)

STARTUP_LOGO = """\
██████╗  ██████╗ ██████╗ ██╗  ██╗██╗      █████╗      ██╗██████╗  █████╗ ██╗
██╔══██╗██╔═══██╗██╔══██╗██║ ██╔╝██║ ██╗ ██╔══██╗     ██║██╔══██╗██╔══██╗██║
██████╔╝██║   ██║██║  ██║█████╔╝ ██║██╔╝ ███████║     ██║██║  ██║███████║██║
██╔═══╝ ██║   ██║██║  ██║██╔═██╗ ███╔╝   ██╔══██║██   ██║██║  ██║██╔══██║██║
██║     ╚██████╔╝██████╔╝██║  ██╗███████╗██║  ██║╚█████╔╝██████╔╝██║  ██║███████╗
╚═╝      ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝"""

_STAGE_LABELS = {
    JobState.INSPECTING: "Sprawdzanie adresu URL",
    JobState.DOWNLOADING: "Pobieranie audio",
    JobState.PREPARING: "Przygotowywanie audio",
    JobState.MODEL_READY: "Przygotowywanie modelu separacji",
    JobState.SEPARATING: "Rozdzielanie wokalu i podkładu",
    JobState.ENCODING: "Kodowanie MP3",
    JobState.VALIDATING: "Sprawdzanie plików wynikowych",
    JobState.FINALIZING: "Zapisywanie plików",
    JobState.SUCCEEDED: "Gotowe",
}

_DIAGNOSTIC_STATUS_LABELS = {
    "PASS": "OK",
    "WARN": "OSTRZEŻENIE",
    "FAIL": "BŁĄD",
}


def _progress_bar(percent: int, width: int) -> str:
    percent = max(0, min(100, percent))
    filled = int(width * percent / 100)
    if percent > 0 and filled == 0:
        filled = 1
    return "#" * filled + " " * (width - filled)


class StageReporter:
    def __init__(self, console: Console) -> None:
        self.console = console
        self.status: Status | None = None
        self.current_state: JobState | None = None
        self.current_detail: str | None = None

    def stage(self, state: JobState, detail: str | None = None) -> None:
        if state == JobState.SUCCEEDED:
            self.finish_current()
            return
        if state == self.current_state:
            self.current_detail = detail or self.current_detail
            if self.status:
                self.status.update(self._message(state, self.current_detail))
            return
        self.finish_current()
        self.current_state = state
        self.current_detail = detail
        self.status = self.console.status(self._message(state, detail), spinner="dots")
        self.status.start()

    def download(self, progress: dict) -> None:
        if self.current_state != JobState.DOWNLOADING or not self.status:
            return
        if progress.get("status") != "downloading":
            return
        downloaded = progress.get("downloaded_bytes")
        total = progress.get("total_bytes") or progress.get("total_bytes_estimate")
        if downloaded and total:
            self.status.update(
                f"{_STAGE_LABELS[JobState.DOWNLOADING]}  "
                f"{_human_bytes(downloaded)} / {_human_bytes(total)}"
            )

    def separation(self, percent: int) -> None:
        if self.current_state != JobState.SEPARATING or not self.status:
            return
        label = _STAGE_LABELS[JobState.SEPARATING]
        width = max(12, min(60, self.console.width - len(label) - 12))
        bar = _progress_bar(percent, width)
        self.status.update(f"{label}  |{bar}|  {percent:3d}%")

    def finish_current(self) -> None:
        if not self.current_state:
            return
        if self.status:
            self.status.stop()
        label = _STAGE_LABELS.get(self.current_state, self.current_state.value)
        show_detail = self.current_detail and self.current_detail != label
        suffix = f"\n  {self.current_detail}" if show_detail else ""
        self.console.print(f"[green]✓[/green] {label}{suffix}")
        self.status = None
        self.current_state = None
        self.current_detail = None

    def cancel(self) -> None:
        if self.status:
            self.status.stop()
        self.status = None
        self.current_state = None

    @staticmethod
    def _message(state: JobState, detail: str | None) -> str:
        label = _STAGE_LABELS.get(state, state.value)
        return f"{label}…" if not detail else f"{label}…  {detail}"


def _human_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} GB"


def _console(no_color: bool, *, stderr: bool = False) -> Console:
    disable = no_color or bool(os.environ.get("NO_COLOR"))
    return Console(stderr=stderr, color_system=None if disable else "auto")


def _render_error(console: Console, error: PodklajdalError, verbose: bool) -> None:
    console.print(f"[bold red]Błąd:[/bold red] {error.message}")
    if error.hint:
        console.print(error.hint)
    if verbose and error.__cause__:
        console.print(f"\n[dim]Szczegóły: {error.__cause__!r}[/dim]")


def _run_doctor(no_color: bool, output_root: Path) -> None:
    console = _console(no_color)
    report = DiagnosticsService().run(MODEL_CACHE, output_root)
    console.print(f"[bold]{PRODUCT_NAME} — diagnostyka[/bold]\n")
    for item in report.items:
        icons = {
            "PASS": "[green]✓[/green]",
            "WARN": "[yellow]![/yellow]",
            "FAIL": "[red]✗[/red]",
        }
        icon = icons[item.status]
        console.print(f"  {icon} {item.name:<20} {item.detail}")
    console.print()
    if report.ready and report.cpu_fallback:
        console.print("Wynik: [yellow]gotowy — używany będzie procesor CPU[/yellow]")
    elif report.ready:
        console.print("Wynik: [green]gotowy[/green]")
    else:
        console.print("Wynik: [red]niegotowy[/red]")
        raise typer.Exit(3)


@app.command()
def run(
    youtube_url: Annotated[
        str | None, typer.Argument(help="Adres URL jednego publicznego filmu z YouTube")
    ] = None,
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Katalog główny plików wynikowych")
    ] = DEFAULT_OUTPUT_ROOT,
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Bezpiecznie zastąp istniejące pliki wynikowe")
    ] = False,
    allow_long: Annotated[
        bool, typer.Option("--allow-long", help="Zezwól na filmy dłuższe niż 60 minut")
    ] = False,
    no_color: Annotated[
        bool, typer.Option("--no-color", help="Wyłącz kolory ANSI")
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Pokaż diagnostykę techniczną na standardowym wyjściu błędów",
        ),
    ] = False,
    doctor: Annotated[
        bool, typer.Option("--doctor", help="Sprawdź lokalne zależności i zakończ")
    ] = False,
    version: Annotated[
        bool, typer.Option("--version", help="Wyświetl wersję i zakończ")
    ] = False,
    keep_temp: Annotated[bool, typer.Option("--keep-temp", hidden=True)] = False,
) -> None:
    console = _console(no_color)
    err_console = _console(no_color, stderr=True)

    if version:
        console.print(f"{PRODUCT_NAME} {__version__}")
        return
    if doctor:
        _run_doctor(no_color, output)
        return
    if not youtube_url:
        err_console.print("[bold red]Błąd:[/bold red] podaj adres URL jednego filmu z YouTube.")
        err_console.print("Użyj 'podklajdal --help', aby wyświetlić pomoc.")
        raise typer.Exit(2)

    console.print(STARTUP_LOGO, style="bold cyan", highlight=False, soft_wrap=True)
    console.print()
    reporter = StageReporter(console)
    app_service = PodklajdalApplication()

    def debug(message: str) -> None:
        if verbose:
            err_console.print(f"[dim]{message}[/dim]")

    if verbose:
        diagnostic_report = DiagnosticsService().run(MODEL_CACHE, output)
        for item in diagnostic_report.items:
            status = _DIAGNOSTIC_STATUS_LABELS.get(item.status, item.status)
            debug(f"{item.name}: {status} {item.detail}")

    try:
        result = app_service.process_youtube_video(
            JobRequest(
                url=youtube_url,
                output_root=output.expanduser(),
                overwrite=overwrite,
                allow_long=allow_long,
                keep_temp=keep_temp,
            ),
            on_stage=reporter.stage,
            on_notice=lambda message: console.print(f"[yellow]![/yellow] {message}"),
            on_debug=debug,
            on_download=reporter.download,
            on_separation_progress=reporter.separation,
        )
        reporter.finish_current()
        console.print("\n[bold green]Gotowe[/bold green]")
        console.print(f"  Wokal:   {result.vocals_path}")
        console.print(f"  Podkład: {result.instrumental_path}")
    except KeyboardInterrupt:
        reporter.cancel()
        err_console.print("\nAnulowano. Czyszczenie plików tymczasowych…")
        raise typer.Exit(130) from None
    except PodklajdalError as exc:
        reporter.cancel()
        _render_error(err_console, exc, verbose)
        raise typer.Exit(exc.exit_code) from None
    except Exception as exc:
        reporter.cancel()
        err_console.print("[bold red]Błąd:[/bold red] nieoczekiwany błąd wewnętrzny.")
        if verbose:
            traceback.print_exception(exc, file=sys.stderr)
        raise typer.Exit(1) from None


def main() -> None:
    app()


if __name__ == "__main__":
    main()
