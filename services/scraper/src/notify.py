"""Optional Slack Incoming Webhook alerts for scrape sync failures.

One POST per sync (pipeline / scrape-daily / scrape-all), never per step.
Unset or empty ``SLACK_WEBHOOK_URL`` skips HTTP and never fails the scrape.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TypeVar

import requests

from config import settings

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 8
_MESSAGE_LIMIT = 200
_MAX_FAILURES_IN_MESSAGE = 15

T = TypeVar("T")


@dataclass(frozen=True)
class StepFailure:
    step: str
    error_type: str
    message: str
    season: str | None = None

    @classmethod
    def from_exception(
        cls,
        step: str,
        exc: BaseException,
        *,
        season: str | None = None,
    ) -> StepFailure:
        return cls(
            step=step,
            error_type=type(exc).__name__,
            message=_truncate_error_message(exc),
            season=season,
        )


class SyncFailedError(RuntimeError):
    """One or more scrape steps failed during a sync."""

    def __init__(self, failures: Sequence[StepFailure]) -> None:
        self.failures = list(failures)
        first = self.failures[0]
        super().__init__(
            f"{len(self.failures)} scrape step(s) failed; "
            f"first={first.step}: {first.error_type}: {first.message}"
        )


def _truncate_error_message(exc: BaseException) -> str:
    raw = re.sub(r"<[^>]+>", " ", str(exc))
    raw = re.sub(r"\s+", " ", raw).strip()
    if len(raw) > _MESSAGE_LIMIT:
        return raw[: _MESSAGE_LIMIT - 3] + "..."
    return raw


def _resolve_webhook_url(webhook_url: str | None) -> str | None:
    raw = settings.slack_webhook_url if webhook_url is None else webhook_url
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped or None


def format_sync_failure_text(sync_name: str, failures: Sequence[StepFailure]) -> str:
    lines = [f"NBA scrape failed: {sync_name} ({len(failures)} step(s))"]
    shown = failures[:_MAX_FAILURES_IN_MESSAGE]
    for item in shown:
        where = f"{item.step} ({item.season})" if item.season else item.step
        detail = f"{item.error_type}: {item.message}" if item.message else item.error_type
        lines.append(f"- {where}: {detail}")
    extra = len(failures) - len(shown)
    if extra:
        lines.append(f"- ...and {extra} more")
    return "\n".join(lines)


def notify_sync_failures(
    failures: Sequence[StepFailure],
    *,
    sync_name: str,
    webhook_url: str | None = None,
) -> None:
    """POST one Incoming Webhook summary. No-op when URL is unset or no failures."""
    if not failures:
        return
    url = _resolve_webhook_url(webhook_url)
    if not url:
        return
    text = format_sync_failure_text(sync_name, failures)
    try:
        response = requests.post(
            url,
            json={"text": text},
            timeout=WEBHOOK_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            logger.warning(
                "Slack webhook returned HTTP %s; scrape failures still stand",
                response.status_code,
            )
    except Exception:
        logger.warning(
            "Slack webhook POST failed; scrape failures still stand",
            exc_info=True,
        )


@dataclass
class SyncAlert:
    """Collects step failures during one scrape sync and posts at most once."""

    sync_name: str
    failures: list[StepFailure] = field(default_factory=list)

    def record(
        self,
        step: str,
        exc: BaseException,
        *,
        season: str | None = None,
    ) -> None:
        self.failures.append(StepFailure.from_exception(step, exc, season=season))

    def try_run(
        self,
        step: str,
        fn: Callable[[], T],
        *,
        season: str | None = None,
    ) -> T | None:
        try:
            return fn()
        except Exception as exc:
            where = f"{step} ({season})" if season else step
            logger.exception("Scrape step %s failed", where)
            self.record(step, exc, season=season)
            return None

    def raise_if_failed(self) -> None:
        if self.failures:
            raise SyncFailedError(self.failures)

    def notify(self, *, webhook_url: str | None = None) -> None:
        notify_sync_failures(
            self.failures,
            sync_name=self.sync_name,
            webhook_url=webhook_url,
        )
