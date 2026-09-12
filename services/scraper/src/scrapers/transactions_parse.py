"""Parse the Basketball-Reference season transactions log. No HTTP, no DB.

Page shape, verified against the 2025-26 page:

    <ul class='page_index'>
      <li>
        <span>July 1, 2025</span>
        <p>The <a data-attr-to="CLE" href="/teams/CLE/2026.html">Cleveland
           Cavaliers</a> signed <a href="/players/t/travelu01.html">Luke
           Travers</a> to a two-way contract.</p>
        <p>...another transaction on the same date...</p>
      </li>
    </ul>

One ``li`` per date, one ``p`` per transaction. The date carries an explicit
four-digit year, so nothing here has to infer one from the season.

The page's final ``li`` is not closed — it runs straight into ``</ul>`` — so
items are split on the opening tag rather than matched between a pair. A
``<li>(.*?)</li>`` regex silently drops the last date group on every run.

Only hyperlinked entities become participants. Draft picks are plain prose
("a 2031 2nd round draft pick") and are intentionally dropped; where a pick
clause names the player later selected, that player *is* linked and is kept.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from html import unescape
from typing import Any

BREF_TRANSACTIONS_PATH = "/leagues/NBA_{year}_transactions.html"

# The transactions list is the only ul.page_index on the page.
_LIST_RE = re.compile(r"<ul class=['\"]page_index['\"]>(.*?)</ul>", re.S)
_DATE_RE = re.compile(r"<span>(.*?)</span>", re.S)
_ENTRY_RE = re.compile(r"<p>(.*?)</p>", re.S)
_ANCHOR_RE = re.compile(r"<a\s+([^>]*)>(.*?)</a>", re.S)
_HREF_RE = re.compile(r'href="([^"]+)"')
_DIRECTION_RE = re.compile(r'data-attr-(to|from)="([A-Z]{3})"')
_PLAYER_HREF_RE = re.compile(r"^/players/\w/(\w+)\.html$")
_TEAM_HREF_RE = re.compile(r"^/teams/([A-Z]{3})/\d{4}\.html$")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def transactions_url(season_end_year: int, base_url: str) -> str:
    """BRef names the page for the season's *ending* year: 2025-26 -> 2026."""
    return f"{base_url}{BREF_TRANSACTIONS_PATH.format(year=season_end_year)}"


def transaction_key(transaction_date: date, description: str) -> str:
    """Stable grain for a transaction.

    A unique index on (transaction_date, description) directly is not possible:
    description is free prose and a btree entry over ~2704 bytes errors on
    insert. Hashing gives a fixed-width key with the same meaning.
    """
    payload = f"{transaction_date.isoformat()}|{description}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _clean_text(fragment: str) -> str:
    return _WS_RE.sub(" ", unescape(_TAG_RE.sub("", fragment))).strip()


def parse_transaction_date(value: str) -> date | None:
    """ "July 1, 2025" -> date(2025, 7, 1). The year is always explicit."""
    try:
        return datetime.strptime(_clean_text(value), "%B %d, %Y").date()
    except ValueError:
        return None


def parse_participants(entry_html: str) -> list[dict[str, Any]]:
    """Linked players and teams in one transaction, in document order.

    A team can appear twice in one trade, once sending and once receiving, so
    dedupe is on (type, slug, direction) rather than slug alone.
    """
    participants: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for attrs, label in _ANCHOR_RE.findall(entry_html):
        href_match = _HREF_RE.search(attrs)
        if not href_match:
            continue
        href = href_match.group(1)
        name = _clean_text(label)
        if not name:
            continue

        player_match = _PLAYER_HREF_RE.match(href)
        team_match = _TEAM_HREF_RE.match(href)
        if player_match:
            participant_type, slug, direction = "player", player_match.group(1), "none"
        elif team_match:
            participant_type, slug = "team", team_match.group(1)
            direction_match = _DIRECTION_RE.search(attrs)
            direction = direction_match.group(1) if direction_match else "none"
        else:
            # Anything else linked in the prose (a season page, a coach) is not
            # a participant we can resolve to a canonical id.
            continue

        identity = (participant_type, slug, direction)
        if identity in seen:
            continue
        seen.add(identity)
        participants.append(
            {
                "participant_type": participant_type,
                "direction": direction,
                "bref_slug": slug,
                "display_name": name[:200],
            }
        )
    return participants


def parse_transactions_html(
    html: str,
    *,
    season: str,
    source_url: str,
) -> list[dict[str, Any]]:
    """Return one dict per transaction, each carrying its participants."""
    list_match = _LIST_RE.search(html)
    if not list_match:
        return []

    rows: list[dict[str, Any]] = []
    for chunk in list_match.group(1).split("<li>")[1:]:
        item = chunk.split("</li>")[0]
        date_match = _DATE_RE.search(item)
        if not date_match:
            continue
        transaction_date = parse_transaction_date(date_match.group(1))
        if transaction_date is None:
            continue

        for entry in _ENTRY_RE.findall(item):
            description = _clean_text(entry)
            if not description:
                continue
            rows.append(
                {
                    "transaction_key": transaction_key(transaction_date, description),
                    "transaction_date": transaction_date,
                    "season": season,
                    "description": description,
                    "source_url": source_url,
                    "participants": parse_participants(entry),
                }
            )
    return rows
