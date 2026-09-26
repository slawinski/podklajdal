from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    id: str
    title: str
    webpage_url: str
    duration_seconds: int
    uploader: str | None = None
    artist: str | None = None
    track: str | None = None
    album: str | None = None
    release_year: int | None = None
    is_live: bool = False

    @property
    def display_title(self) -> str:
        if self.artist and self.track:
            return f"{self.artist} - {self.track}"
        return self.title
