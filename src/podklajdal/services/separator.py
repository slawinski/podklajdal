from __future__ import annotations

import logging
from pathlib import Path

from podklajdal.config import DEFAULT_MODEL
from podklajdal.domain.errors import InferenceError, ModelDownloadError, ModelLoadError
from podklajdal.domain.job import SeparatedStems


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

    def separate(self, source: Path, destination_dir: Path) -> SeparatedStems:
        if self._separator is None or self._output_dir != destination_dir:
            self.ensure_model(destination_dir)
        try:
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
