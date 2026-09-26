from pathlib import Path
import shutil
import subprocess

import pytest

from podklajdal.domain.metadata import VideoMetadata
from podklajdal.services.audio import AudioService

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg not installed",
)
def test_prepare_and_encode_mp3(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    subprocess.run(
        [
            shutil.which("ffmpeg"),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-ac",
            "2",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    service = AudioService()
    prepared = service.prepare(source, tmp_path / "prepared.wav")
    encoded = service.encode_mp3(
        prepared,
        tmp_path / "final.mp3.part",
        VideoMetadata("id", "Tone", "https://youtu.be/id", 1, artist="Test"),
    )
    info = service.validate_final_mp3(encoded, expected_seconds=1.0)
    assert info.codec_name == "mp3"
    assert encoded.stat().st_size > 0
