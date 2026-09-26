from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from podklajdal.domain.metadata import VideoMetadata


class JobState(StrEnum):
    CREATED = "created"
    INSPECTING = "inspecting"
    DOWNLOADING = "downloading"
    PREPARING = "preparing"
    MODEL_READY = "model_ready"
    SEPARATING = "separating"
    ENCODING = "encoding"
    VALIDATING = "validating"
    FINALIZING = "finalizing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class JobRequest:
    url: str
    output_root: Path
    overwrite: bool = False
    allow_long: bool = False
    keep_temp: bool = False


@dataclass(frozen=True, slots=True)
class JobPaths:
    workspace: Path
    source_template: Path
    prepared_audio: Path
    stems_dir: Path
    final_dir: Path
    vocals_temp: Path
    instrumental_temp: Path
    vocals_final: Path
    instrumental_final: Path


@dataclass(frozen=True, slots=True)
class JobResult:
    metadata: VideoMetadata
    vocals_path: Path
    instrumental_path: Path
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class AudioInfo:
    codec_name: str
    duration_seconds: float
    sample_rate: int | None
    channels: int | None


@dataclass(frozen=True, slots=True)
class SeparatedStems:
    vocals: Path
    instrumental: Path
