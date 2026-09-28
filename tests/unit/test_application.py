from pathlib import Path

from podklajdal.application import PodklajdalApplication
from podklajdal.config import Settings
from podklajdal.domain.job import AudioInfo, JobRequest, JobState, SeparatedStems
from podklajdal.domain.metadata import VideoMetadata


class FakeYouTube:
    def inspect(self, url: str) -> VideoMetadata:
        return VideoMetadata(
            id="abc123",
            title="Test Song",
            webpage_url=url,
            duration_seconds=180,
            artist="Test Artist",
            track="Test Song",
        )

    def download_audio(self, metadata, destination_template: Path, on_progress=None) -> Path:
        path = destination_template.parent / "source.webm"
        path.write_bytes(b"source")
        return path


class FakeAudio:
    def source_video_id(self, path: Path) -> str | None:
        return None

    def probe(self, path: Path) -> AudioInfo:
        return AudioInfo("pcm_s16le", 180.0, 44100, 2)

    def prepare(self, source: Path, destination: Path) -> Path:
        destination.write_bytes(b"wav")
        return destination

    def validate_duration(self, path: Path, expected_seconds: float, tolerance: float) -> AudioInfo:
        return self.probe(path)

    def encode_mp3(self, source: Path, destination: Path, metadata) -> Path:
        destination.write_bytes(b"mp3")
        return destination

    def validate_final_mp3(self, path: Path, expected_seconds: float) -> AudioInfo:
        return AudioInfo("mp3", 180.0, 44100, 2)


class FakeSeparator:
    model_is_cached = True

    def ensure_model(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

    def separate(self, source: Path, destination_dir: Path, on_progress=None) -> SeparatedStems:
        if on_progress:
            on_progress(0)
            on_progress(50)
            on_progress(100)
        vocals = destination_dir / "vocals.wav"
        instrumental = destination_dir / "instrumental.wav"
        vocals.write_bytes(b"vocals")
        instrumental.write_bytes(b"instrumental")
        return SeparatedStems(vocals, instrumental)


def test_happy_path_and_states(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("podklajdal.application.require_ffmpeg", lambda: "/usr/bin/ffmpeg")
    monkeypatch.setattr("podklajdal.application.require_ffprobe", lambda: "/usr/bin/ffprobe")
    settings = Settings(
        output_root=tmp_path / "out",
        jobs_root=tmp_path / "cache" / "jobs",
        model_cache=tmp_path / "cache" / "models",
    )
    app = PodklajdalApplication(
        settings=settings,
        youtube=FakeYouTube(),
        audio=FakeAudio(),
        separator=FakeSeparator(),
    )
    states: list[JobState] = []
    separation_progress: list[int] = []
    result = app.process_youtube_video(
        JobRequest("https://youtu.be/abc123", settings.output_root),
        on_stage=lambda state, detail: (
            states.append(state) if not states or states[-1] != state else None
        ),
        on_separation_progress=separation_progress.append,
    )

    assert result.vocals_path.read_bytes() == b"mp3"
    assert result.instrumental_path.read_bytes() == b"mp3"
    assert separation_progress == [0, 50, 100]
    assert states == [
        JobState.INSPECTING,
        JobState.DOWNLOADING,
        JobState.PREPARING,
        JobState.MODEL_READY,
        JobState.SEPARATING,
        JobState.ENCODING,
        JobState.VALIDATING,
        JobState.FINALIZING,
        JobState.SUCCEEDED,
    ]
    assert not any(settings.jobs_root.iterdir())


def test_different_video_with_same_slug_uses_video_id_suffix(tmp_path: Path) -> None:
    from podklajdal.infrastructure.filesystem import create_job_paths

    settings = Settings(
        output_root=tmp_path / "out",
        jobs_root=tmp_path / "cache" / "jobs",
        model_cache=tmp_path / "cache" / "models",
    )

    class CollisionAudio(FakeAudio):
        def source_video_id(self, path: Path) -> str | None:
            return "different-video"

    app = PodklajdalApplication(
        settings=settings,
        youtube=FakeYouTube(),
        audio=CollisionAudio(),
        separator=FakeSeparator(),
    )
    metadata = FakeYouTube().inspect("https://youtu.be/abc123")
    paths = create_job_paths(metadata, settings.output_root, settings.jobs_root)
    paths.final_dir.mkdir(parents=True)
    paths.vocals_final.write_bytes(b"old")
    paths.instrumental_final.write_bytes(b"old")

    resolved = app._resolve_output_collision(
        paths,
        metadata,
        JobRequest("https://youtu.be/abc123", settings.output_root),
    )
    assert resolved.final_dir.name.endswith("-abc123")
