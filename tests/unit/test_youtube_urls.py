import pytest

from podklajdal.domain.errors import (
    InvalidUrlError,
    PlaylistNotSupportedError,
    UnsupportedUrlError,
)
from podklajdal.services.youtube import validate_youtube_url


@pytest.mark.parametrize(
    "url",
    [
        "https://youtube.com/watch?v=abc123",
        "https://www.youtube.com/watch?v=abc123&list=PL123",
        "https://m.youtube.com/watch?v=abc123",
        "https://music.youtube.com/watch?v=abc123",
        "https://youtu.be/abc123",
        "https://youtube.com/shorts/abc123",
    ],
)
def test_supported_urls(url: str) -> None:
    validate_youtube_url(url)


def test_malformed_url() -> None:
    with pytest.raises(InvalidUrlError):
        validate_youtube_url("not-a-url")


def test_non_youtube_url() -> None:
    with pytest.raises(UnsupportedUrlError):
        validate_youtube_url("https://example.com/song")


def test_playlist_only_url() -> None:
    with pytest.raises(PlaylistNotSupportedError):
        validate_youtube_url("https://youtube.com/playlist?list=PL123")
