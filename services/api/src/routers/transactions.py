from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from dependencies import get_transactions_repository
from repositories.transactions import TransactionsRepository
from schemas import (
    ItemResponse,
    PaginatedResponse,
    PaginationMeta,
    SeasonListResponse,
    Transaction,
    TransactionDetail,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[Transaction])
def list_transactions(
    season: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    team_abbreviation: Annotated[str | None, Query()] = None,
    player_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    repo: TransactionsRepository = Depends(get_transactions_repository),
) -> PaginatedResponse[Transaction]:
    total, rows = repo.list_transactions(
        season=season,
        search=search.strip() if search and search.strip() else None,
        team_abbreviation=team_abbreviation.strip().upper() if team_abbreviation else None,
        player_id=player_id,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(
        data=[Transaction.model_validate(row) for row in rows],
        meta=PaginationMeta(total=total, limit=limit, offset=offset),
    )


@router.get("/seasons", response_model=SeasonListResponse)
def list_transaction_seasons(
    repo: TransactionsRepository = Depends(get_transactions_repository),
) -> SeasonListResponse:
    seasons = repo.list_seasons()
    return SeasonListResponse(
        data=seasons,
        meta=PaginationMeta(total=len(seasons), limit=len(seasons), offset=0),
    )


# After /seasons on purpose: a literal path segment must not be shadowed by the
# key route, which would match "seasons" as a transaction_key and 404.
@router.get("/{transaction_key}", response_model=ItemResponse[TransactionDetail])
def get_transaction(
    transaction_key: str,
    repo: TransactionsRepository = Depends(get_transactions_repository),
) -> ItemResponse[TransactionDetail]:
    transaction = repo.get_transaction(transaction_key)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return ItemResponse(data=TransactionDetail.model_validate(transaction))
