from datetime import UTC, datetime

import pytest

from repositories.status import as_utc


@pytest.mark.unit
def test_as_utc_none() -> None:
    assert as_utc(None) is None


@pytest.mark.unit
def test_as_utc_naive_and_aware() -> None:
    naive = datetime(2026, 9, 4, 4, 12)
    aware = datetime(2026, 9, 4, 4, 12, tzinfo=UTC)
    assert as_utc(naive) == datetime(2026, 9, 4, 4, 12, tzinfo=UTC)
    assert as_utc(aware) == aware
