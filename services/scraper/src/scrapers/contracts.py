"""Scrape remaining NBA player contracts from Basketball-Reference.

stats.nba.com has no first-class salary/contract endpoint. Current source is
team payroll HTML at ``https://www.basketball-reference.com/contracts/{TEAM}.html``
(remaining multi-year salaries, not a historical paid-salary ledger).

Be polite: BRef rate-limits aggressively. Included on season-active daily
(``pipeline`` / ``scrape-daily``) and ``scrape-all``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from db import get_session, upsert_rows
from models import PlayerContract, TeamPayroll
from scrapers.contracts_parse import (
    BREF_TEAM_ABBREVIATIONS,
    parse_contracts_html,
    parse_team_list,
)

logger = logging.getLogger(__name__)

BREF_BASE_URL = "https://www.basketball-reference.com"
BREF_REQUEST_TIMEOUT = 60
BREF_REQUEST_DELAY_SECONDS = 3.0
BREF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.basketball-reference.com/contracts/",
}

_last_bref_request_at = 0.0


class BrefHTTPError(RuntimeError):
    def __init__(self, status: int, url: str) -> None:
        self.status = int(status)
        self.url = url
        super().__init__(f"Basketball-Reference HTTP {status} for {url}")


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (KeyboardInterrupt, SystemExit, ValueError)):
        return False
    # 4xx other than 429 is a permanent client error; retrying cannot fix it.
    return not (isinstance(exc, BrefHTTPError) and 400 <= exc.status < 500 and exc.status != 429)


def bref_rate_limit() -> None:
    global _last_bref_request_at
    elapsed = time.monotonic() - _last_bref_request_at
    if elapsed < BREF_REQUEST_DELAY_SECONDS:
        time.sleep(BREF_REQUEST_DELAY_SECONDS - elapsed)
    _last_bref_request_at = time.monotonic()


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def bref_get(url: str, *, get: Callable[..., Any] | None = None) -> str:
    """Rate-limit and GET a Basketball-Reference URL with exponential backoff."""
    bref_rate_limit()
    http_get = get or requests.get
    response = http_get(url, headers=BREF_HEADERS, timeout=BREF_REQUEST_TIMEOUT)
    status = getattr(response, "status_code", None)
    if status is not None and int(status) >= 400:
        raise BrefHTTPError(int(status), url)
    return str(response.text)


def team_contracts_url(bref_team_abbreviation: str) -> str:
    return f"{BREF_BASE_URL}/contracts/{bref_team_abbreviation.upper()}.html"


def scrape_contracts(
    teams: str | None = None,
    *,
    fetch_html: Callable[[str], str] | None = None,
) -> tuple[int, int]:
    """Upsert remaining contracts for one or more teams.

    Returns ``(player_contract_rows, team_payroll_rows)``.
    """
    team_list = parse_team_list(teams)
    fetch = fetch_html or bref_get
    scraped_at = datetime.now()
    player_rows: list[dict] = []
    payroll_rows: list[dict] = []

    for bref_abbr in team_list:
        url = team_contracts_url(bref_abbr)
        html = fetch(url)
        parsed_players, parsed_payroll = parse_contracts_html(
            html,
            bref_team_abbreviation=bref_abbr,
            source_url=url,
        )
        for row in parsed_players:
            row["scraped_at"] = scraped_at
        for row in parsed_payroll:
            row["scraped_at"] = scraped_at
        player_rows.extend(parsed_players)
        payroll_rows.extend(parsed_payroll)
        logger.info(
            "Parsed %s player-season rows and %s payroll rows from %s",
            len(parsed_players),
            len(parsed_payroll),
            url,
        )

    with get_session() as session:
        n_players = upsert_rows(
            session,
            PlayerContract,
            player_rows,
            ["bref_player_slug", "bref_team_abbreviation", "season"],
        )
        n_payroll = upsert_rows(
            session,
            TeamPayroll,
            payroll_rows,
            ["bref_team_abbreviation", "season"],
        )
    logger.info(
        "Upserted %s player contracts and %s team payroll rows (teams=%s)",
        n_players,
        n_payroll,
        ",".join(team_list),
    )
    return n_players, n_payroll


__all__ = [
    "BREF_TEAM_ABBREVIATIONS",
    "BrefHTTPError",
    "bref_get",
    "bref_rate_limit",
    "scrape_contracts",
    "team_contracts_url",
]
