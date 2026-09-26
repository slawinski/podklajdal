from __future__ import annotations

from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

from podklajdal.domain.errors import (
    AuthenticationRequiredError,
    InvalidUrlError,
    LiveStreamNotSupportedError,
    MediaDownloadError,
    PlaylistNotSupportedError,
    UnsupportedUrlError,
    VideoUnavailableError,
)
from podklajdal.domain.metadata import VideoMetadata

ProgressCallback = Callable[[dict], None] | None

_SUPPORTED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}


def validate_youtube_url(url: str) -> None:
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise InvalidUrlError("expected a single YouTube video URL.") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InvalidUrlError("expected a single YouTube video URL.", f"Received: {url}")
    host = parsed.hostname.lower() if parsed.hostname else ""
    if host not in _SUPPORTED_HOSTS:
        raise UnsupportedUrlError("expected a single YouTube video URL.", f"Received: {url}")

    if host == "youtu.be":
        if not parsed.path.strip("/"):
            raise InvalidUrlError("expected a single YouTube video URL.", f"Received: {url}")
        return

    path = parsed.path.rstrip("/") or "/"
    query = parse_qs(parsed.query)
    if path == "/playlist":
        raise PlaylistNotSupportedError("playlist-only URLs are not supported in the MVP.")
    if path == "/watch":
        if not query.get("v"):
            raise InvalidUrlError("expected a single YouTube video URL.", f"Received: {url}")
        return
    if path.startswith("/shorts/") and len(path.split("/")) >= 3:
        return
    raise UnsupportedUrlError("expected a single YouTube video URL.", f"Received: {url}")


def _translate_download_error(exc: Exception) -> Exception:
    message = str(exc)
    lower = message.lower()
    if any(token in lower for token in ("sign in", "private video", "login", "cookies")):
        return AuthenticationRequiredError(
            "this video cannot be downloaded without authentication.",
            "podkłajdal MVP supports public videos that do not require cookies or login.",
        )
    if any(token in lower for token in ("video unavailable", "removed", "not available")):
        return VideoUnavailableError("the YouTube video is unavailable.")
    return MediaDownloadError("failed to retrieve media from YouTube.", message)


def _release_year(info: dict) -> int | None:
    value = info.get("release_year") or info.get("release_date")
    if value is None:
        return None
    text = str(value)
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    return None


class YouTubeService:
    def inspect(self, url: str) -> VideoMetadata:
        validate_youtube_url(url)
        try:
            from yt_dlp import YoutubeDL
            from yt_dlp.utils import DownloadError as YtDlpDownloadError
        except ImportError as exc:
            raise MediaDownloadError("yt-dlp is not installed correctly.") from exc

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
        except YtDlpDownloadError as exc:
            raise _translate_download_error(exc) from exc

        if not isinstance(info, dict) or info.get("_type") == "playlist":
            raise PlaylistNotSupportedError("expected one YouTube video, not a playlist.")
        is_live = bool(info.get("is_live")) or info.get("live_status") == "is_live"
        if is_live:
            raise LiveStreamNotSupportedError(
                "live streams currently in progress are not supported."
            )
        duration = info.get("duration")
        if not duration or float(duration) <= 0:
            raise VideoUnavailableError("video duration could not be determined.")
        return VideoMetadata(
            id=str(info.get("id") or ""),
            title=str(info.get("title") or "untitled"),
            webpage_url=str(info.get("webpage_url") or url),
            duration_seconds=int(float(duration)),
            uploader=info.get("uploader") or info.get("channel"),
            artist=info.get("artist"),
            track=info.get("track"),
            album=info.get("album"),
            release_year=_release_year(info),
            is_live=is_live,
        )

    def download_audio(
        self,
        metadata: VideoMetadata,
        destination_template: Path,
        on_progress: ProgressCallback = None,
    ) -> Path:
        try:
            from yt_dlp import YoutubeDL
            from yt_dlp.utils import DownloadError as YtDlpDownloadError
        except ImportError as exc:
            raise MediaDownloadError("yt-dlp is not installed correctly.") from exc

        hooks = [on_progress] if on_progress else []
        options = {
            "format": "bestaudio/best",
            "outtmpl": str(destination_template),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": hooks,
        }
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(metadata.webpage_url, download=True)
                requested = info.get("requested_downloads") or []
                for item in requested:
                    filepath = item.get("filepath")
                    if filepath and Path(filepath).exists():
                        return Path(filepath)
                filename = ydl.prepare_filename(info)
                if Path(filename).exists():
                    return Path(filename)
        except YtDlpDownloadError as exc:
            raise _translate_download_error(exc) from exc

        candidates = [
            path
            for path in destination_template.parent.glob("source.*")
            if path.is_file() and not path.name.endswith((".part", ".ytdl"))
        ]
        if len(candidates) == 1:
            return candidates[0]
        raise MediaDownloadError(
            "yt-dlp finished but the downloaded audio file could not be located."
        )
