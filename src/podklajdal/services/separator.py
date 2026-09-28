from __future__ import annotations

import io
import logging
import re
import sys
from collections.abc import Callable
from contextlib import redirect_stderr
from pathlib import Path

from podklajdal.config import DEFAULT_MODEL
from podklajdal.domain.errors import InferenceError, ModelDownloadError, ModelLoadError
from podklajdal.domain.job import SeparatedStems

ProgressCallback = Callable[[int], None]
_TQDM_PERCENT_RE = re.compile(r"(?<!\d)(\d{1,3})%\|")


class _TqdmProgressStream(io.TextIOBase):
    """Capture tqdm refreshes while preserving unrelated stderr output."""

    def __init__(self, on_progress: ProgressCallback, fallback) -> None:
        self.on_progress = on_progress
        self.fallback = fallback
        self.last_percent: int | None = None

    def write(self, text: str) -> int:
        if not text:
            return 0
        matches = list(_TQDM_PERCENT_RE.finditer(text))
        if matches:
            percent = max(0, min(100, int(matches[-1].group(1))))
            if percent != self.last_percent:
                self.last_percent = percent
                self.on_progress(percent)
            return len(text)
        if not text.strip("\r\n "):
            return len(text)
        return self.fallback.write(text)

    def flush(self) -> None:
        self.fallback.flush()

    def isatty(self) -> bool:
        return bool(getattr(self.fallback, "isatty", lambda: False)())


class SeparationService:
    def __init__(self, model_cache: Path, model_filename: str = DEFAULT_MODEL) -> None:
        self.model_cache = model_cache
        self.model_filename = model_filename
        self._separator = None
        self._output_dir: Path | None = None

    @property
    def model_is_cached(self) -> bool:
        return (self.model_cache / self.model_filename).exists()

    def ensure_model(self, output_dir: Path) -> None:
        self.model_cache.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            from audio_separator.separator import Separator
        except ImportError as exc:
            raise ModelLoadError(
                "audio-separator could not be imported.",
                f"{type(exc).__name__}: {exc}",
            ) from exc

        was_cached = self.model_is_cached
        try:
            separator = Separator(
                log_level=logging.WARNING,
                model_file_dir=str(self.model_cache),
                output_dir=str(output_dir),
                output_format="WAV",
                normalization_threshold=1.0,
            )
            separator.load_model(model_filename=self.model_filename)
        except Exception as exc:
            if not was_cached:
                raise ModelDownloadError(
                    "failed to download or prepare the separation model.", str(exc)
                ) from exc
            raise ModelLoadError("failed to load the separation model.", str(exc)) from exc

        self._separator = separator
        self._output_dir = output_dir

    def separate(
        self,
        source: Path,
        destination_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> SeparatedStems:
        if self._separator is None or self._output_dir != destination_dir:
            self.ensure_model(destination_dir)
        try:
            if on_progress:
                on_progress(0)
                progress_stream = _TqdmProgressStream(on_progress, sys.stderr)
                with redirect_stderr(progress_stream):
                    output_files = self._separator.separate(str(source))
                on_progress(100)
            else:
                output_files = self._separator.separate(str(source))
        except Exception as exc:
            raise InferenceError("vocal/instrumental separation failed.", str(exc)) from exc

        paths = []
        for raw in output_files or []:
            path = Path(raw)
            if not path.is_absolute():
                path = destination_dir / path
            paths.append(path)
        if not paths:
            paths = list(destination_dir.glob("*"))

        vocals = next((p for p in paths if "vocal" in p.name.lower()), None)
        instrumental = next(
            (
                p
                for p in paths
                if any(token in p.name.lower() for token in ("instrument", "no_vocal"))
            ),
            None,
        )
        if not vocals or not instrumental or not vocals.exists() or not instrumental.exists():
            raise InferenceError("separator did not produce both vocals and instrumental stems.")
        return SeparatedStems(vocals=vocals, instrumental=instrumental)
