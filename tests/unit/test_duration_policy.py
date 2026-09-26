import pytest

from podklajdal.application import validate_duration_policy
from podklajdal.domain.errors import DurationLimitError


def test_14_59_is_normal() -> None:
    assert validate_duration_policy(14 * 60 + 59, False) is False


def test_15_01_warns() -> None:
    assert validate_duration_policy(15 * 60 + 1, False) is True


def test_59_59_is_allowed_with_warning() -> None:
    assert validate_duration_policy(59 * 60 + 59, False) is True


def test_60_01_is_rejected_by_default() -> None:
    with pytest.raises(DurationLimitError):
        validate_duration_policy(60 * 60 + 1, False)


def test_60_01_is_allowed_explicitly() -> None:
    assert validate_duration_policy(60 * 60 + 1, True) is True
