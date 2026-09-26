import os
from pathlib import Path
import shutil
import subprocess

import pytest

from podklajdal.config import DEFAULT_MODEL
from podklajdal.services.separator import SeparationService

pytestmark = pytest.mark.integration_model


@pytest.mark.skipif(
    os.environ.get("PODKLAJDAL_RUN_MODEL_TEST") != "1",
    reason="set PODKLAJDAL_RUN_MODEL_TEST=1 for the release/model smoke test",
)
def test_real_separator_produces_two_stems(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("FFmpeg not installed")

    source = tmp_path / "source.wav"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-ac",
            "2",
            str(source),
        ],
        check=True,
        capture_output=True,
    )

    service = SeparationService(tmp_path / "models", DEFAULT_MODEL)
    stems_dir = tmp_path / "stems"
    service.ensure_model(stems_dir)
    stems = service.separate(source, stems_dir)

    assert stems.vocals.exists()
    assert stems.instrumental.exists()
    assert stems.vocals.stat().st_size > 0
    assert stems.instrumental.stat().st_size > 0
