"""Unit tests for app/core/logging_utils.py."""

import pytest

from app.core.logging_utils import mask_email


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("alice@example.com", "a***@example.com"),
        ("a@b.co", "a***@b.co"),
        ("bob.smith@sub.domain.org", "b***@sub.domain.org"),
        ("no-at-sign", "***"),
        ("", "***"),
        ("@example.com", "***"),
        ("alice@", "***"),
    ],
)
def test_mask_email(value: str, expected: str) -> None:
    assert mask_email(value) == expected
