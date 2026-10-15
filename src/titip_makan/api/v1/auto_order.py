from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.core.database import get_db
from titip_makan.schemas.auto_order import AutoOrderPreferenceIn, AutoOrderPreferenceOut
from titip_makan.services.auto_order_service import AutoOrderService

router = APIRouter(prefix="/auto-order", tags=["auto-order"])

@router.get("", response_model=AutoOrderPreferenceOut)
async def get_auto_order(
    user_name: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
):
    return await AutoOrderService(db).get_preference(user_name)

@router.put("", response_model=AutoOrderPreferenceOut)
async def save_auto_order(data: AutoOrderPreferenceIn, db: AsyncSession = Depends(get_db)):
    return await AutoOrderService(db).save_preference(data)
