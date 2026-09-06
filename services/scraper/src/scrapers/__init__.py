"""NBA Stats API scrapers with shared rate-limiting and retry helpers."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

REQUEST_DELAY_SECONDS = 0.6
NBA_REQUEST_TIMEOUT = 60

HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://stats.nba.com/",
    "Origin": "https://stats.nba.com",
    "Connection": "keep-alive",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

GAME_SEASON_TYPES = ("Regular Season", "Playoffs", "PlayIn")
LOG_SEASON_TYPES = ("Regular Season", "Playoffs", "PlayIn")

_last_request_at = 0.0
_headers_applied = False


def ensure_headers() -> None:
    """nba_api sets headers by default; re-apply if a 403-style failure is likely."""
    global _headers_applied
    if _headers_applied:
        return
    try:
        from nba_api.stats.library.http import NBAStatsHTTP

        # Current nba_api uses `.headers`; older builds used `.nba_headers`.
        for attr in ("headers", "nba_headers"):
            current = getattr(NBAStatsHTTP, attr, None)
            if isinstance(current, dict):
                current.update(HEADERS)
            else:
                setattr(NBAStatsHTTP, attr, dict(HEADERS))
    except Exception:
        pass
    _headers_applied = True


def rate_limit() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < REQUEST_DELAY_SECONDS:
        time.sleep(REQUEST_DELAY_SECONDS - elapsed)
    _last_request_at = time.monotonic()


def _is_retryable(exc: BaseException) -> bool:
    return not isinstance(exc, (KeyboardInterrupt, SystemExit))


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def nba_call[T](fn: Callable[[], T]) -> T:
    """Rate-limit, then invoke an NBA API request with exponential backoff."""
    ensure_headers()
    rate_limit()
    return fn()


def current_season(today: date | None = None) -> str:
    """NBA season string for `today`. October starts a new season."""
    today = today or date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return season_from_start_year(start_year)


def season_from_start_year(year: int | str) -> str:
    year = int(year)
    return f"{year}-{str(year + 1)[-2:]}"


def season_start_year(season: str) -> int:
    return int(season.split("-")[0])


def generate_seasons(start: str, end: str) -> list[str]:
    first = season_start_year(start)
    last = season_start_year(end)
    if last < first:
        raise ValueError(f"Season range is reversed: {start} -> {end}")
    return [season_from_start_year(year) for year in range(first, last + 1)]


def parse_seasons(value: str | None) -> list[str]:
    """Parse a comma-separated season list. Empty/None -> current season only."""
    if value is None or not value.strip():
        return [current_season()]
    seasons = [part.strip() for part in value.split(",") if part.strip()]
    if not seasons:
        return [current_season()]
    return seasons


def parse_game_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized game date: {value!r}")


def parse_minutes(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if ":" in text:
        minutes, _, seconds = text.partition(":")
        try:
            return int(minutes) + int(seconds) / 60.0
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except TypeError, ValueError:
        return None


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def to_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def row_get(row: dict[str, Any], *names: str) -> Any:
    lookup = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def dataset_rows(payload: dict[str, Any], *preferred: str) -> list[dict[str, Any]]:
    for name in preferred:
        rows = payload.get(name)
        if isinstance(rows, list):
            return rows
    for rows in payload.values():
        if isinstance(rows, list):
            return rows
    return []


def matchup_is_home(matchup: str) -> bool:
    lowered = matchup.lower()
    return " vs." in lowered or " vs " in lowered


def matchup_team_abbr(matchup: str) -> str | None:
    token = matchup.strip().split()[0] if matchup and matchup.strip() else ""
    return token.upper() or None


def parse_matchup_sides(matchup: str) -> tuple[str | None, str | None]:
    """Return (home_abbr, away_abbr) from ``DAL @ DET`` or ``DET vs. DAL``.

    LeagueGameFinder sometimes repeats the ``@`` string on both team rows
    (NBA Cup knockout / restaged dates). Callers must not assume the current
    row is home just because the matchup lacks ``vs``.
    """
    text = (matchup or "").strip()
    if not text:
        return None, None
    lowered = text.lower()
    if " @ " in lowered:
        left, right = text.split("@", 1)
        away = left.strip().split()[0].upper() if left.strip() else None
        home = right.strip().split()[0].upper() if right.strip() else None
        return home, away
    if " vs." in lowered or " vs " in lowered:
        marker = " vs." if " vs." in lowered else " vs "
        idx = lowered.find(marker)
        left, right = text[:idx], text[idx + len(marker) :]
        home = left.strip().split()[0].upper() if left.strip() else None
        away = right.strip().split()[0].upper() if right.strip() else None
        return home, away
    return None, None


def matchup_row_is_home(matchup: str, team_abbr: str | None) -> bool:
    """Whether this team's finder row is the home side."""
    home_abbr, away_abbr = parse_matchup_sides(matchup)
    key = (team_abbr or "").strip().upper()
    if key and home_abbr and key == home_abbr:
        return True
    if key and away_abbr and key == away_abbr:
        return False
    return matchup_is_home(matchup)


def nba_date(value: date) -> str:
    """NBA Stats date filter format (YYYY-MM-DD per nba_api LeagueGameFinder)."""
    return value.strftime("%Y-%m-%d")
