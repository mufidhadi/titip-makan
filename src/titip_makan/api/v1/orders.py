from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.core.database import get_db
from titip_makan.schemas.order import OrderOut, OrderPaymentUpdate
from titip_makan.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])

@router.patch("/{order_id}/payment", response_model=OrderOut)
async def update_payment(order_id: int, data: OrderPaymentUpdate, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    try:
        return await service.toggle_payment(order_id, data.is_paid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{order_id}")
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    success = await service.delete_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": "success", "message": f"Order {order_id} deleted"}
