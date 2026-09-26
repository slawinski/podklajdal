from pathlib import Path

import pytest

from podklajdal.domain.errors import OutputConflictError
from podklajdal.domain.job import JobPaths
from podklajdal.domain.metadata import VideoMetadata
from podklajdal.infrastructure.filesystem import check_output_conflicts, safe_slug


def metadata(title: str, artist: str | None = None) -> VideoMetadata:
    return VideoMetadata(
        id="abc123",
        title=title,
        webpage_url="https://youtu.be/abc123",
        duration_seconds=180,
        artist=artist,
    )


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("AC/DC \\ Live", "AC-DC-Live"),
        ("  ...hello...  ", "hello"),
        ("../../escape", "escape"),
        ("Zażółć gęślą jaźń 🎤", "Zażółć-gęślą-jaźń"),
    ],
)
def test_safe_slug(title: str, expected: str) -> None:
    assert safe_slug(metadata(title)) == expected


def test_slug_is_capped() -> None:
    assert len(safe_slug(metadata("x" * 300))) == 120


def test_output_conflict(tmp_path: Path) -> None:
    final_dir = tmp_path / "song"
    final_dir.mkdir()
    vocals = final_dir / "song-vocals.mp3"
    vocals.write_bytes(b"existing")
    paths = JobPaths(
        workspace=tmp_path / "job",
        source_template=tmp_path / "job" / "source.%(ext)s",
        prepared_audio=tmp_path / "job" / "prepared.wav",
        stems_dir=tmp_path / "job" / "stems",
        final_dir=final_dir,
        vocals_temp=tmp_path / "job" / "vocals.part",
        instrumental_temp=tmp_path / "job" / "instrumental.part",
        vocals_final=vocals,
        instrumental_final=final_dir / "song-instrumental.mp3",
    )
    with pytest.raises(OutputConflictError):
        check_output_conflicts(paths, overwrite=False)
    assert check_output_conflicts(paths, overwrite=True) == [vocals]


def test_overwrite_rolls_back_if_second_move_fails(tmp_path: Path, monkeypatch) -> None:
    from podklajdal.infrastructure import filesystem

    workspace = tmp_path / "job"
    workspace.mkdir()
    final_dir = tmp_path / "song"
    final_dir.mkdir()
    vocals_final = final_dir / "song-vocals.mp3"
    instrumental_final = final_dir / "song-instrumental.mp3"
    vocals_final.write_bytes(b"old-vocals")
    instrumental_final.write_bytes(b"old-instrumental")
    vocals_temp = workspace / "vocals.part"
    instrumental_temp = workspace / "instrumental.part"
    vocals_temp.write_bytes(b"new-vocals")
    instrumental_temp.write_bytes(b"new-instrumental")
    paths = JobPaths(
        workspace=workspace,
        source_template=workspace / "source.%(ext)s",
        prepared_audio=workspace / "prepared.wav",
        stems_dir=workspace / "stems",
        final_dir=final_dir,
        vocals_temp=vocals_temp,
        instrumental_temp=instrumental_temp,
        vocals_final=vocals_final,
        instrumental_final=instrumental_final,
    )

    real_replace = filesystem.os.replace
    calls = 0

    def flaky_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second move failure")
        return real_replace(source, destination)

    monkeypatch.setattr(filesystem.os, "replace", flaky_replace)
    with pytest.raises(OSError):
        filesystem.finalize_outputs(paths, overwrite=True)

    assert vocals_final.read_bytes() == b"old-vocals"
    assert instrumental_final.read_bytes() == b"old-instrumental"
