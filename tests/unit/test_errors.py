from podklajdal.domain.errors import (
    AudioProcessingError,
    DownloadError,
    InputError,
    LocalEnvironmentError,
    OutputConflictError,
    PodklajdalError,
    SeparationError,
)


def test_exit_code_contract() -> None:
    assert PodklajdalError("x").exit_code == 1
    assert InputError("x").exit_code == 2
    assert LocalEnvironmentError("x").exit_code == 3
    assert OutputConflictError("x").exit_code == 4
    assert DownloadError("x").exit_code == 5
    assert AudioProcessingError("x").exit_code == 6
    assert SeparationError("x").exit_code == 7
