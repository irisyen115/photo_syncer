from datetime import datetime

import pytest

from service.upload_service import parse_date_range


def test_both_none():
    assert parse_date_range(None, None) == (None, None)


def test_date_only_end_is_inclusive():
    start, end = parse_date_range("2025-01-01", "2025-12-31")
    assert start == datetime(2025, 1, 1)
    assert end == datetime(2025, 12, 31, 23, 59, 59, 999999)


def test_only_start():
    start, end = parse_date_range("2025-06-01", None)
    assert start == datetime(2025, 6, 1)
    assert end is None


def test_datetime_end_kept_as_is():
    _, end = parse_date_range(None, "2025-12-31T12:00:00")
    assert end == datetime(2025, 12, 31, 12, 0, 0)


def test_start_after_end_raises():
    with pytest.raises(ValueError):
        parse_date_range("2025-12-31", "2025-01-01")


def test_bad_format_raises():
    with pytest.raises(ValueError):
        parse_date_range("2025/01/01", None)
