from __future__ import annotations


class PodklajdalError(Exception):
    exit_code = 1

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class InputError(PodklajdalError):
    exit_code = 2


class InvalidUrlError(InputError):
    pass


class UnsupportedUrlError(InputError):
    pass


class PlaylistNotSupportedError(InputError):
    pass


class LiveStreamNotSupportedError(InputError):
    pass


class DurationLimitError(InputError):
    pass


class LocalEnvironmentError(PodklajdalError):
    exit_code = 3


class FFmpegMissingError(LocalEnvironmentError):
    pass


class FFprobeMissingError(LocalEnvironmentError):
    pass


class OutputNotWritableError(LocalEnvironmentError):
    pass


class InsufficientDiskSpaceError(LocalEnvironmentError):
    pass


class DownloadError(PodklajdalError):
    exit_code = 5


class VideoUnavailableError(DownloadError):
    pass


class AuthenticationRequiredError(DownloadError):
    pass


class MediaDownloadError(DownloadError):
    pass


class AudioProcessingError(PodklajdalError):
    exit_code = 6


class ProbeError(AudioProcessingError):
    pass


class PreparationError(AudioProcessingError):
    pass


class EncodeError(AudioProcessingError):
    pass


class SeparationError(PodklajdalError):
    exit_code = 7


class ModelDownloadError(SeparationError):
    pass


class ModelLoadError(SeparationError):
    pass


class InferenceError(SeparationError):
    pass


class OutputConflictError(PodklajdalError):
    exit_code = 4
