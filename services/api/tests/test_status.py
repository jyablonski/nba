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


@pytest.mark.unit
def test_status_reports_next_scrape(client, session, mapping_row, query_result) -> None:
    session.queue = [
        query_result(
            [
                mapping_row(
                    {
                        "last_scraped_at": datetime(2026, 9, 11, 6, 0),
                        "next_scrape_at": datetime(2026, 9, 12, 6, 0),
                        "player_count": 747,
                        "game_count": 1230,
                        "season_count": 2,
                        "first_season": "2024-25",
                        "last_season": "2025-26",
                    }
                )
            ]
        )
    ]
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["data"]["next_scrape_at"] == "2026-09-12T06:00:00Z"


@pytest.mark.unit
def test_status_next_scrape_is_null_when_no_schedule_recorded(
    client, session, mapping_row, query_result
) -> None:
    """An unset daily_refresh_utc must stay null rather than become a guess."""
    session.queue = [
        query_result(
            [
                mapping_row(
                    {
                        "last_scraped_at": None,
                        "next_scrape_at": None,
                        "player_count": 0,
                        "game_count": 0,
                        "season_count": 0,
                        "first_season": None,
                        "last_season": None,
                    }
                )
            ]
        )
    ]
    assert client.get("/api/v1/status").json()["data"]["next_scrape_at"] is None


@pytest.mark.unit
def test_status_sql_rolls_the_daily_time_forward() -> None:
    from queries.status import WAREHOUSE_STATUS

    sql = str(WAREHOUSE_STATUS)
    assert "daily_refresh_utc" in sql
    # Past today's time means the next run is tomorrow, not a stamp in the past.
    assert "(now() AT TIME ZONE 'utc')::date + 1 + pipeline_stamp.daily_refresh_utc" in sql
