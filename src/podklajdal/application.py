from __future__ import annotations

import importlib.util
import time
from collections.abc import Callable
from pathlib import Path

from podklajdal.config import (
    MAX_DEFAULT_DURATION_SECONDS,
    MAX_NORMAL_DURATION_SECONDS,
    MIN_FREE_BYTES_LONG,
    MIN_FREE_BYTES_NORMAL,
    Settings,
)
from podklajdal.domain.errors import DurationLimitError, LocalEnvironmentError, PodklajdalError
from podklajdal.domain.job import AudioInfo, JobRequest, JobResult, JobState
from podklajdal.domain.metadata import VideoMetadata
from podklajdal.infrastructure.ffmpeg import require_ffmpeg, require_ffprobe
from podklajdal.infrastructure.filesystem import (
    check_output_conflicts,
    cleanup_stale_jobs,
    cleanup_workspace,
    create_job_paths,
    ensure_free_space,
    ensure_writable_directory,
    finalize_outputs,
    find_output_conflicts,
    retarget_final_slug,
    safe_slug,
)
from podklajdal.services.audio import AudioService
from podklajdal.services.separator import SeparationService
from podklajdal.services.youtube import YouTubeService, validate_youtube_url

StageCallback = Callable[[JobState, str | None], None]
NoticeCallback = Callable[[str], None]
DebugCallback = Callable[[str], None]
DownloadCallback = Callable[[dict], None]


def validate_duration_policy(duration_seconds: int, allow_long: bool) -> bool:
    """Validate duration and return True when the user should receive a long-track warning."""
    if duration_seconds > MAX_DEFAULT_DURATION_SECONDS and not allow_long:
        hours, remainder = divmod(duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        rendered = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        raise DurationLimitError(
            f"video duration is {rendered}. Tracks longer than 60 minutes are blocked by default.",
            "Re-run with --allow-long if this is intentional.",
        )
    return duration_seconds > MAX_NORMAL_DURATION_SECONDS


class PodklajdalApplication:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        youtube: YouTubeService | None = None,
        audio: AudioService | None = None,
        separator: SeparationService | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.youtube = youtube or YouTubeService()
        self.audio = audio or AudioService()
        self.separator = separator or SeparationService(
            self.settings.model_cache,
            self.settings.model_filename,
        )

    def process_youtube_video(
        self,
        request: JobRequest,
        *,
        on_stage: StageCallback | None = None,
        on_notice: NoticeCallback | None = None,
        on_debug: DebugCallback | None = None,
        on_download: DownloadCallback | None = None,
    ) -> JobResult:
        started = time.monotonic()
        paths = None
        state = JobState.CREATED

        def stage(next_state: JobState, detail: str | None = None) -> None:
            nonlocal state
            state = next_state
            if on_stage:
                on_stage(next_state, detail)

        def debug(message: str) -> None:
            if on_debug:
                on_debug(message)

        try:
            validate_youtube_url(request.url)
            self._preflight(request.output_root)
            cleanup_stale_jobs(self.settings.jobs_root)

            stage(JobState.INSPECTING)
            metadata = self.youtube.inspect(request.url)
            stage(JobState.INSPECTING, metadata.display_title)
            is_long = validate_duration_policy(metadata.duration_seconds, request.allow_long)
            if is_long and on_notice:
                on_notice(
                    f"This video is {self._format_duration(metadata.duration_seconds)}. "
                    "Long tracks use more memory and take longer to separate. Continuing…"
                )

            paths = create_job_paths(metadata, request.output_root, self.settings.jobs_root)
            debug(f"workspace: {paths.workspace}")
            debug(f"model: {self.settings.model_filename}")
            paths = self._resolve_output_collision(paths, metadata, request)
            check_output_conflicts(paths, request.overwrite)
            ensure_free_space(
                paths.workspace,
                MIN_FREE_BYTES_LONG if is_long else MIN_FREE_BYTES_NORMAL,
            )

            stage(JobState.DOWNLOADING)
            source = self.youtube.download_audio(metadata, paths.source_template, on_download)
            source_info = self.audio.probe(source)
            debug(
                f"source: {source.name}; codec={source_info.codec_name}; "
                f"duration={source_info.duration_seconds:.2f}s"
            )
            if abs(source_info.duration_seconds - metadata.duration_seconds) > 5:
                debug(
                    "source duration differs from YouTube metadata by more than 5 seconds; "
                    "using probed duration for media validation"
                )

            stage(JobState.PREPARING)
            self.audio.prepare(source, paths.prepared_audio)
            prepared_info = self.audio.probe(paths.prepared_audio)

            stage(JobState.MODEL_READY, "Preparing separation model")
            self.separator.ensure_model(paths.stems_dir)

            stage(JobState.SEPARATING)
            stems = self.separator.separate(paths.prepared_audio, paths.stems_dir)
            self.audio.validate_duration(
                stems.vocals, prepared_info.duration_seconds, tolerance=1.0
            )
            self.audio.validate_duration(
                stems.instrumental, prepared_info.duration_seconds, tolerance=1.0
            )

            stage(JobState.ENCODING)
            self.audio.encode_mp3(stems.vocals, paths.vocals_temp, metadata)
            self.audio.encode_mp3(stems.instrumental, paths.instrumental_temp, metadata)

            stage(JobState.VALIDATING)
            self.audio.validate_final_mp3(paths.vocals_temp, prepared_info.duration_seconds)
            self.audio.validate_final_mp3(paths.instrumental_temp, prepared_info.duration_seconds)

            stage(JobState.FINALIZING)
            finalize_outputs(paths, request.overwrite)

            if not request.keep_temp:
                cleanup_workspace(paths.workspace)
            stage(JobState.SUCCEEDED)
            return JobResult(
                metadata=metadata,
                vocals_path=paths.vocals_final,
                instrumental_path=paths.instrumental_final,
                elapsed_seconds=time.monotonic() - started,
            )
        except KeyboardInterrupt:
            if paths is not None and not request.keep_temp:
                cleanup_workspace(paths.workspace)
            raise
        except PodklajdalError:
            if paths is not None and not request.keep_temp:
                cleanup_workspace(paths.workspace)
            raise
        except Exception:
            if paths is not None and not request.keep_temp:
                cleanup_workspace(paths.workspace)
            raise

    def _resolve_output_collision(
        self,
        paths,
        metadata: VideoMetadata,
        request: JobRequest,
    ):
        conflicts = find_output_conflicts(paths)
        if not conflicts or request.overwrite:
            return paths
        source_ids = [self.audio.source_video_id(path) for path in conflicts]
        if source_ids and all(source_id and source_id != metadata.id for source_id in source_ids):
            short_id = metadata.id[:8] or "video"
            alternate_slug = f"{safe_slug(metadata)}-{short_id}"
            return retarget_final_slug(paths, request.output_root, alternate_slug)
        return paths

    def _preflight(self, output_root: Path) -> None:
        require_ffmpeg()
        require_ffprobe()
        if isinstance(self.youtube, YouTubeService) and importlib.util.find_spec("yt_dlp") is None:
            raise LocalEnvironmentError(
                "yt-dlp is required but the Python package is not installed."
            )
        if (
            isinstance(self.separator, SeparationService)
            and importlib.util.find_spec("audio_separator") is None
        ):
            raise LocalEnvironmentError(
                "audio-separator is required but the Python package is not installed."
            )
        ensure_writable_directory(output_root)
        for path in (self.settings.jobs_root, self.settings.model_cache):
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise LocalEnvironmentError(
                    f"cannot create application cache directory: {path}"
                ) from exc

    @staticmethod
    def _format_duration(seconds: int) -> str:
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"
