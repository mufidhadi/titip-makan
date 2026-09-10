from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.core.database import get_db
from titip_makan.schemas.order import OrderOut, OrderPaymentUpdate, OrderPriceUpdate, OrderUpdate
from titip_makan.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/{order_id}/claim-paid", response_model=OrderOut)
async def claim_paid(order_id: int, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    try:
        return await service.claim_order_payment(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{order_id}", response_model=OrderOut)
@router.patch("/{order_id}", response_model=OrderOut)
async def update_order(order_id: int, data: OrderUpdate, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    try:
        return await service.update_order(order_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{order_id}/payment", response_model=OrderOut)
async def update_payment(order_id: int, data: OrderPaymentUpdate, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    try:
        return await service.update_payment_status(order_id, is_paid=data.is_paid, payment_status=data.payment_status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{order_id}/price", response_model=OrderOut)
async def update_price(order_id: int, data: OrderPriceUpdate, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    try:
        return await service.update_order_price(order_id, data.price)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{order_id}")
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    success = await service.delete_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": "success", "message": f"Order {order_id} deleted"}
