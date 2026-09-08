from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.models.order import OrderItem

class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        session_id: int,
        user_name: str,
        vendor: str,
        item_name: str,
        variant: str = "",
        notes: str = "",
        price: int = 0
    ) -> OrderItem:
        order = OrderItem(
            session_id=session_id,
            user_name=user_name,
            vendor=vendor,
            item_name=item_name,
            variant=variant,
            notes=notes,
            price=price,
            is_paid=False,
            payment_status="UNPAID",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_by_id(self, order_id: int) -> Optional[OrderItem]:
        result = await self.db.execute(select(OrderItem).where(OrderItem.id == order_id))
        return result.scalars().first()

    async def get_by_session(self, session_id: int) -> List[OrderItem]:
        result = await self.db.execute(
            select(OrderItem)
            .where(OrderItem.session_id == session_id)
            .order_by(OrderItem.id.asc())
        )
        return list(result.scalars().all())

    async def get_all(self) -> List[OrderItem]:
        result = await self.db.execute(select(OrderItem).order_by(OrderItem.created_at.desc()))
        return list(result.scalars().all())

    async def update_payment(self, order_id: int, is_paid: bool, payment_status: Optional[str] = None) -> Optional[OrderItem]:
        order = await self.get_by_id(order_id)
        if order:
            order.is_paid = is_paid
            if payment_status is not None:
                order.payment_status = payment_status
            else:
                order.payment_status = "PAID" if is_paid else "UNPAID"
            await self.db.commit()
            await self.db.refresh(order)
        return order

    async def update_order(
        self,
        order_id: int,
        vendor: Optional[str] = None,
        item_name: Optional[str] = None,
        notes: Optional[str] = None,
        price: Optional[int] = None
    ) -> Optional[OrderItem]:
        order = await self.get_by_id(order_id)
        if order:
            if vendor is not None:
                order.vendor = vendor
            if item_name is not None:
                order.item_name = item_name
            if notes is not None:
                order.notes = notes
            if price is not None:
                order.price = price
            await self.db.commit()
            await self.db.refresh(order)
        return order

    async def update_price(self, order_id: int, price: int) -> Optional[OrderItem]:
        order = await self.get_by_id(order_id)
        if order:
            order.price = price
            await self.db.commit()
            await self.db.refresh(order)
        return order

    async def get_distinct_items(self) -> List[OrderItem]:
        result = await self.db.execute(select(OrderItem.vendor, OrderItem.item_name, OrderItem.variant).distinct())
        return list(result.all())

    async def delete(self, order_id: int) -> bool:
        order = await self.get_by_id(order_id)
        if order:
            await self.db.delete(order)
            await self.db.commit()
            return True
        return False

