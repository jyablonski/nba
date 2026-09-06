from fastapi import APIRouter, Depends

from dependencies import get_status_repository
from repositories.status import StatusRepository
from schemas import ItemResponse, WarehouseStatus

router = APIRouter()


@router.get("", response_model=ItemResponse[WarehouseStatus])
def get_status(
    repo: StatusRepository = Depends(get_status_repository),
) -> ItemResponse[WarehouseStatus]:
    return ItemResponse(data=WarehouseStatus.model_validate(repo.get_status()))
