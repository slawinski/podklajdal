from __future__ import annotations

import subprocess
from pathlib import Path

from podklajdal.domain.errors import EncodeError, PreparationError, ProbeError
from podklajdal.domain.job import AudioInfo
from podklajdal.domain.metadata import VideoMetadata
from podklajdal.infrastructure.ffmpeg import probe_json, require_ffmpeg, run_process


class AudioService:
    def probe(self, path: Path) -> AudioInfo:
        try:
            payload = probe_json(path)
        except Exception as exc:
            raise ProbeError(f"could not decode audio file: {path}") from exc

        streams = [s for s in payload.get("streams", []) if s.get("codec_type") == "audio"]
        if not streams:
            raise ProbeError(f"audio file contains no audio stream: {path}")
        stream = streams[0]
        raw_duration = stream.get("duration") or payload.get("format", {}).get("duration")
        try:
            duration = float(raw_duration)
        except (TypeError, ValueError) as exc:
            raise ProbeError(f"audio duration is invalid: {path}") from exc
        if duration <= 0:
            raise ProbeError(f"audio duration is invalid: {path}")
        sample_rate = stream.get("sample_rate")
        return AudioInfo(
            codec_name=str(stream.get("codec_name") or "unknown"),
            duration_seconds=duration,
            sample_rate=int(sample_rate) if sample_rate else None,
            channels=int(stream["channels"]) if stream.get("channels") else None,
        )

    def source_video_id(self, path: Path) -> str | None:
        try:
            payload = probe_json(path)
        except Exception:
            return None
        tags = payload.get("format", {}).get("tags", {})
        comment = next(
            (value for key, value in tags.items() if key.lower() == "comment"),
            None,
        )
        prefix = "Generated locally by podkłajdal from YouTube video "
        if isinstance(comment, str) and comment.startswith(prefix):
            video_id = comment[len(prefix) :].strip()
            return video_id or None
        return None

    def prepare(self, source: Path, destination: Path) -> Path:
        ffmpeg = require_ffmpeg()
        try:
            run_process(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(source),
                    "-vn",
                    "-ac",
                    "2",
                    "-ar",
                    "44100",
                    "-c:a",
                    "pcm_s16le",
                    str(destination),
                ]
            )
        except subprocess.CalledProcessError as exc:
            hint = (
                "Free disk space and try again."
                if "No space left" in (exc.stderr or "")
                else None
            )
            raise PreparationError("failed to prepare canonical WAV audio.", hint) from exc
        self.probe(destination)
        return destination

    def encode_mp3(
        self,
        source: Path,
        destination: Path,
        metadata: VideoMetadata,
    ) -> Path:
        ffmpeg = require_ffmpeg()
        args = [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-vn",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-metadata",
            f"title={metadata.track or metadata.title}",
        ]
        if metadata.artist:
            args.extend(["-metadata", f"artist={metadata.artist}"])
        args.extend(
            [
                "-metadata",
                f"comment=Generated locally by podkłajdal from YouTube video {metadata.id}",
                "-f",
                "mp3",
                str(destination),
            ]
        )
        try:
            run_process(args)
        except subprocess.CalledProcessError as exc:
            hint = (
                "Free disk space and try again."
                if "No space left" in (exc.stderr or "")
                else None
            )
            raise EncodeError(f"failed to encode MP3: {destination.name}", hint) from exc
        return destination

    def validate_duration(self, path: Path, expected_seconds: float, tolerance: float) -> AudioInfo:
        info = self.probe(path)
        if abs(info.duration_seconds - expected_seconds) > tolerance:
            raise ProbeError(
                f"audio duration mismatch for {path.name}: "
                f"expected about {expected_seconds:.1f}s, got {info.duration_seconds:.1f}s"
            )
        return info

    def validate_final_mp3(self, path: Path, expected_seconds: float) -> AudioInfo:
        if not path.exists() or path.stat().st_size <= 0:
            raise EncodeError(f"encoded output is empty: {path}")
        info = self.validate_duration(path, expected_seconds, tolerance=1.0)
        if info.codec_name != "mp3":
            raise EncodeError(f"encoded output is not MP3: {path}")
        if info.sample_rate != 44100:
            raise EncodeError(f"encoded output is not 44.1 kHz: {path}")
        if info.channels != 2:
            raise EncodeError(f"encoded output is not stereo: {path}")
        return info
