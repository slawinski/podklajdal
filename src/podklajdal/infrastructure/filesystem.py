from __future__ import annotations

import os
import re
import shutil
import time
import unicodedata
import uuid
from pathlib import Path

from podklajdal.config import STALE_JOB_AGE_SECONDS
from podklajdal.domain.errors import (
    InsufficientDiskSpaceError,
    OutputConflictError,
    OutputNotWritableError,
)
from podklajdal.domain.job import JobPaths
from podklajdal.domain.metadata import VideoMetadata

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SEPARATOR_RE = re.compile(r"[\\/]+")
_PUNCT_RE = re.compile(r"[^\w\-. ]+", re.UNICODE)
_SPACING_RE = re.compile(r"[\s._-]+")


def safe_slug(metadata: VideoMetadata, max_length: int = 120) -> str:
    source = (
        f"{metadata.artist} - {metadata.track or metadata.title}"
        if metadata.artist
        else metadata.title
    )
    value = unicodedata.normalize("NFKC", source)
    value = _CONTROL_RE.sub("", value)
    value = _SEPARATOR_RE.sub("-", value)
    value = _PUNCT_RE.sub("", value)
    value = _SPACING_RE.sub("-", value).strip(" .-_")
    value = value[:max_length].rstrip(" .-_")
    return value or metadata.id[:12] or "track"


def create_job_paths(
    metadata: VideoMetadata,
    output_root: Path,
    jobs_root: Path,
) -> JobPaths:
    slug = safe_slug(metadata)
    workspace = jobs_root / str(uuid.uuid4())
    final_dir = output_root.expanduser().resolve() / slug
    workspace.mkdir(parents=True, exist_ok=False)
    stems_dir = workspace / "stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    return JobPaths(
        workspace=workspace,
        source_template=workspace / "source.%(ext)s",
        prepared_audio=workspace / "prepared.wav",
        stems_dir=stems_dir,
        final_dir=final_dir,
        vocals_temp=workspace / "final-vocals.mp3.part",
        instrumental_temp=workspace / "final-instrumental.mp3.part",
        vocals_final=final_dir / f"{slug}-vocals.mp3",
        instrumental_final=final_dir / f"{slug}-instrumental.mp3",
    )


def retarget_final_slug(paths: JobPaths, output_root: Path, slug: str) -> JobPaths:
    final_dir = output_root.expanduser().resolve() / slug
    return JobPaths(
        workspace=paths.workspace,
        source_template=paths.source_template,
        prepared_audio=paths.prepared_audio,
        stems_dir=paths.stems_dir,
        final_dir=final_dir,
        vocals_temp=paths.vocals_temp,
        instrumental_temp=paths.instrumental_temp,
        vocals_final=final_dir / f"{slug}-vocals.mp3",
        instrumental_final=final_dir / f"{slug}-instrumental.mp3",
    )


def find_output_conflicts(paths: JobPaths) -> list[Path]:
    return [p for p in (paths.vocals_final, paths.instrumental_final) if p.exists()]


def ensure_writable_directory(path: Path) -> None:
    path = path.expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / f".podklajdal-write-test-{uuid.uuid4().hex}"
        test_file.write_bytes(b"")
        test_file.unlink()
    except OSError as exc:
        raise OutputNotWritableError(
            f"output directory is not writable: {path}",
            "Choose another path with --output.",
        ) from exc


def ensure_free_space(path: Path, required_bytes: int) -> None:
    try:
        free = shutil.disk_usage(path).free
    except OSError as exc:
        raise OutputNotWritableError(f"cannot inspect free space for: {path}") from exc
    if free < required_bytes:
        gib = required_bytes / 1024**3
        raise InsufficientDiskSpaceError(
            f"not enough free space in temporary storage (need at least {gib:.0f} GB)",
            "Free disk space and try again.",
        )


def check_output_conflicts(paths: JobPaths, overwrite: bool) -> list[Path]:
    conflicts = find_output_conflicts(paths)
    if conflicts and not overwrite:
        rendered = "\n".join(f"  {p}" for p in conflicts)
        raise OutputConflictError(
            f"output files already exist:\n{rendered}",
            "Use --overwrite to replace them.",
        )
    return conflicts


def finalize_outputs(paths: JobPaths, overwrite: bool) -> None:
    paths.final_dir.mkdir(parents=True, exist_ok=True)
    pairs = (
        (paths.vocals_temp, paths.vocals_final),
        (paths.instrumental_temp, paths.instrumental_final),
    )
    backups: dict[Path, Path] = {}
    moved: list[Path] = []

    for _, destination in pairs:
        if destination.exists() and not overwrite:
            raise OutputConflictError(
                f"output file already exists: {destination}",
                "Use --overwrite to replace it.",
            )
        if destination.exists():
            backup = paths.workspace / f"backup-{destination.name}"
            shutil.copy2(destination, backup)
            backups[destination] = backup

    try:
        for source, destination in pairs:
            os.replace(source, destination)
            moved.append(destination)
    except Exception:
        for destination in moved:
            try:
                if destination in backups:
                    os.replace(backups[destination], destination)
                else:
                    destination.unlink(missing_ok=True)
            except OSError:
                pass
        for destination, backup in backups.items():
            if destination not in moved and backup.exists():
                backup.unlink(missing_ok=True)
        raise
    finally:
        for backup in backups.values():
            backup.unlink(missing_ok=True)


def cleanup_workspace(workspace: Path) -> None:
    shutil.rmtree(workspace, ignore_errors=True)


def cleanup_stale_jobs(jobs_root: Path, now: float | None = None) -> None:
    if not jobs_root.exists():
        return
    cutoff = (now if now is not None else time.time()) - STALE_JOB_AGE_SECONDS
    for child in jobs_root.iterdir():
        if not child.is_dir():
            continue
        try:
            if child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            continue
