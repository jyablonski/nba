"""Shared NLP provider contract for /api/v1/query."""

from __future__ import annotations

from typing import Protocol

from schemas.game import QueryResponse


class NlpProvider(Protocol):
    """Interchangeable backends for POST /api/v1/query."""

    def answer(self, question: str, season: str | None = None) -> QueryResponse:
        """Return a user-facing answer plus optional data / SQL reference."""

    def classify(self, question: str) -> str:
        """Return a family label for eval / routing (rules) or 'llm' / 'refuse'."""
