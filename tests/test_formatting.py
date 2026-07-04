"""Юнит-тесты утилит отображения."""

import pytest

from ctos.utils.formatting import format_speed_kbps


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0, "0 KB/s"),
        (99.19999999999999, "99.2 KB/s"),
        (100.0, "100 KB/s"),
        (42, "42 KB/s"),
    ],
)
def test_format_speed_kbps(raw, expected):
    assert format_speed_kbps(raw) == expected
