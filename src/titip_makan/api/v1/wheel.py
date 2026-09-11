from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from titip_makan.core.database import get_db
from titip_makan.schemas.wheel import WheelCandidates
from titip_makan.services.wheel_service import (
    InvalidTenantError,
    NoActiveSessionError,
    WheelService,
)

router = APIRouter(prefix="/wheel", tags=["wheel"])


@router.get("/candidates", response_model=WheelCandidates)
async def get_wheel_candidates(
    mode: Literal["tenant", "item"] = Query(...),
    avoid_last: bool = Query(False),
    tenant: Optional[str] = Query(None),
    max_price: Optional[int] = Query(None, ge=0),
    main_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    service = WheelService(db)

    if mode == "tenant":
        return await service.get_tenant_candidates(avoid_last=avoid_last)

    tenant_value = tenant.strip() if tenant and tenant.strip() else None
    try:
        return await service.get_item_candidates(
            tenant=tenant_value, max_price=max_price, main_only=main_only
        )
    except NoActiveSessionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except InvalidTenantError as e:
        raise HTTPException(status_code=400, detail=str(e))
