from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.repositories.order_repository import OrderRepository
from titip_makan.repositories.session_repository import SessionRepository
from titip_makan.schemas.order import OrderCreate, OrderOut, AggregatedItem, SessionSummary
from titip_makan.models.order import OrderItem

class OrderService:
    def __init__(self, db: AsyncSession):
        self.order_repo = OrderRepository(db)
        self.session_repo = SessionRepository(db)

    def _to_schema(self, order: OrderItem) -> OrderOut:
        return OrderOut(
            id=order.id,
            session_id=order.session_id,
            user_name=order.user_name,
            vendor=order.vendor,
            item_name=order.item_name,
            variant=order.variant or "",
            notes=order.notes or "",
            price=order.price or 0,
            is_paid=order.is_paid,
            created_at=order.created_at
        )

    async def create_order(self, session_id: int, data: OrderCreate) -> OrderOut:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session with ID {session_id} not found")
        
        if session.status != "OPEN":
            raise ValueError("Session is closed. No new orders can be submitted.")

        if session.cutoff_at:
            now = datetime.now(timezone.utc)
            cutoff = session.cutoff_at if session.cutoff_at.tzinfo else session.cutoff_at.replace(tzinfo=timezone.utc)
            if now > cutoff:
                await self.session_repo.close(session_id)
                raise ValueError("Session order deadline has passed.")

        order = await self.order_repo.create(
            session_id=session_id,
            user_name=data.user_name.strip(),
            vendor=data.vendor.strip(),
            item_name=data.item_name.strip(),
            variant=data.variant.strip() if data.variant else "",
            notes=data.notes.strip() if data.notes else "",
            price=data.price or 0
        )
        return self._to_schema(order)

    async def get_orders_by_session(self, session_id: int) -> List[OrderOut]:
        orders = await self.order_repo.get_by_session(session_id)
        return [self._to_schema(o) for o in orders]

    async def toggle_payment(self, order_id: int, is_paid: bool) -> OrderOut:
        order = await self.order_repo.update_payment(order_id, is_paid)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        return self._to_schema(order)

    async def delete_order(self, order_id: int) -> bool:
        return await self.order_repo.delete(order_id)

    async def get_session_summary(self, session_id: int) -> SessionSummary:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session with ID {session_id} not found")

        orders = await self.order_repo.get_by_session(session_id)
        order_schemas = [self._to_schema(o) for o in orders]

        # Aggregate items by (vendor, item_name, variant)
        item_groups: Dict[tuple, Dict] = defaultdict(lambda: {
            "quantity": 0,
            "subtotal": 0,
            "notes": []
        })

        total_amount = 0
        paid_count = 0
        unpaid_count = 0

        for o in order_schemas:
            key = (o.vendor, o.item_name, o.variant)
            item_groups[key]["quantity"] += 1
            item_groups[key]["subtotal"] += o.price
            if o.notes:
                item_groups[key]["notes"].append(f"{o.user_name}: {o.notes}")

            total_amount += o.price
            if o.is_paid:
                paid_count += 1
            else:
                unpaid_count += 1

        aggregated_list: List[AggregatedItem] = []
        for (vendor, item_name, variant), stats in item_groups.items():
            aggregated_list.append(
                AggregatedItem(
                    vendor=vendor,
                    item_name=item_name,
                    variant=variant,
                    quantity=stats["quantity"],
                    subtotal=stats["subtotal"],
                    notes_list=stats["notes"]
                )
            )

        # Sort aggregated items by vendor then quantity descending
        aggregated_list.sort(key=lambda x: (x.vendor, -x.quantity))

        # Generate WhatsApp recap message
        wa_lines = [
            f"📋 *Rekap Titip Makan: {session.title}*",
            f"👤 Koordinator: {session.coordinator_name}",
            f"📊 Total Pesanan: {len(order_schemas)} porsi",
            f"💰 Total Biaya: Rp {total_amount:,} (Lunas: {paid_count}, Belum: {unpaid_count})",
            "",
            "🛒 *Ringkasan Belanjaan:*"
        ]

        for item in aggregated_list:
            variant_str = f" ({item.variant})" if item.variant else ""
            price_str = f" - Rp {item.subtotal:,}" if item.subtotal > 0 else ""
            wa_lines.append(f"• {item.quantity}x {item.item_name}{variant_str}{price_str}")
            if item.notes_list:
                for note in item.notes_list:
                    wa_lines.append(f"   ↳ {note}")

        wa_lines.append("")
        wa_lines.append("📝 *Daftar Pemesan:*")
        for idx, o in enumerate(order_schemas, 1):
            variant_str = f" ({o.variant})" if o.variant else ""
            status_icon = "✅ Lunas" if o.is_paid else "⏳ Belum"
            price_str = f" - Rp {o.price:,}" if o.price > 0 else ""
            note_str = f" [Catatan: {o.notes}]" if o.notes else ""
            wa_lines.append(f"{idx}. {o.user_name} - {o.item_name}{variant_str}{price_str}{note_str} ({status_icon})")

        if session.payment_info:
            wa_lines.append("")
            wa_lines.append(f"💳 *Info Pembayaran:*\n{session.payment_info}")

        whatsapp_recap = "\n".join(wa_lines)

        return SessionSummary(
            session_id=session.id,
            title=session.title,
            status=session.status,
            total_orders=len(order_schemas),
            total_amount=total_amount,
            total_paid_count=paid_count,
            total_unpaid_count=unpaid_count,
            aggregated_items=aggregated_list,
            orders=order_schemas,
            whatsapp_recap_text=whatsapp_recap
        )
