from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.repositories.order_repository import OrderRepository
from titip_makan.repositories.session_repository import SessionRepository
from titip_makan.schemas.order import OrderCreate, OrderOut, AggregatedItem, SessionSummary, UnpaidUserItem, OrderUpdate
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
            payment_status=getattr(order, "payment_status", "PAID" if order.is_paid else "UNPAID") or ("PAID" if order.is_paid else "UNPAID"),
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

    async def claim_order_payment(self, order_id: int) -> OrderOut:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        updated = await self.order_repo.update_payment(order_id, is_paid=False, payment_status="PENDING_CONFIRMATION")
        return self._to_schema(updated)

    async def update_payment_status(self, order_id: int, is_paid: Optional[bool] = None, payment_status: Optional[str] = None) -> OrderOut:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        if is_paid is not None:
            paid = is_paid
            status = "PAID" if paid else "UNPAID"
        elif payment_status is not None:
            status = payment_status
            paid = (status == "PAID")
        else:
            paid = not order.is_paid
            status = "PAID" if paid else "UNPAID"

        updated = await self.order_repo.update_payment(order_id, is_paid=paid, payment_status=status)
        return self._to_schema(updated)

    async def toggle_payment(self, order_id: int, is_paid: bool) -> OrderOut:
        return await self.update_payment_status(order_id, is_paid=is_paid)

    async def update_order(self, order_id: int, data: OrderUpdate) -> OrderOut:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        session = await self.session_repo.get_by_id(order.session_id)
        if not session or session.status != "OPEN":
            raise ValueError("Sesi pemesanan sudah ditutup.")

        curr_status = getattr(order, "payment_status", "PAID" if order.is_paid else "UNPAID")
        if order.is_paid or curr_status != "UNPAID":
            raise ValueError("Pesanan sudah ditandai bayar atau lunas, tidak dapat diubah lagi.")

        updated = await self.order_repo.update_order(
            order_id=order_id,
            vendor=data.vendor.strip() if data.vendor else None,
            item_name=data.item_name.strip() if data.item_name else None,
            notes=data.notes.strip() if data.notes is not None else None,
            price=data.price
        )
        return self._to_schema(updated)

    async def update_order_price(self, order_id: int, price: int) -> OrderOut:
        if price < 0:
            raise ValueError("Price cannot be negative")
        order = await self.order_repo.update_price(order_id, price)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        return self._to_schema(order)

    async def get_suggestions(self, session_id: Optional[int] = None) -> Dict:
        import json
        from titip_makan.core.catalog import MASTER_CATALOG

        tenants_set = set(MASTER_CATALOG.keys())
        menus_dict = defaultdict(set)
        prices_dict = {}

        # Seed from master catalog
        for vendor, items in MASTER_CATALOG.items():
            for item, price in items.items():
                menus_dict[vendor].add(item)
                prices_dict[item] = price

        if session_id:
            session = await self.session_repo.get_by_id(session_id)
            if session and session.vendor_options:
                try:
                    opts = json.loads(session.vendor_options)
                except Exception:
                    opts = [v.strip() for v in session.vendor_options.split(",") if v.strip()]
                for opt in opts:
                    tenants_set.add(opt)

        distinct_items = await self.order_repo.get_distinct_items()
        for vendor, item_name, _ in distinct_items:
            if vendor:
                tenants_set.add(vendor)
                if item_name:
                    menus_dict[vendor].add(item_name)

        return {
            "tenants": sorted(list(tenants_set)),
            "menus": {k: sorted(list(v)) for k, v in menus_dict.items()},
            "prices": prices_dict
        }

    async def delete_order(self, order_id: int) -> bool:
        return await self.order_repo.delete(order_id)

    async def get_session_summary(self, session_id: int) -> SessionSummary:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session with ID {session_id} not found")

        orders = await self.order_repo.get_by_session(session_id)
        order_schemas = [self._to_schema(o) for o in orders]

        # Aggregate items by (vendor, item_name)
        item_groups: Dict[tuple, Dict] = defaultdict(lambda: {
            "quantity": 0,
            "subtotal": 0,
            "notes": []
        })

        total_amount = 0
        paid_count = 0
        unpaid_count = 0

        for o in order_schemas:
            key = (o.vendor, o.item_name)
            item_groups[key]["quantity"] += 1
            item_groups[key]["subtotal"] += o.price
            notes_parts = []
            if o.notes:
                notes_parts.append(o.notes)
            elif o.variant:
                notes_parts.append(o.variant)
            if notes_parts:
                item_groups[key]["notes"].append(f"{o.user_name}: {', '.join(notes_parts)}")

            total_amount += o.price
            if o.is_paid:
                paid_count += 1
            else:
                unpaid_count += 1

        aggregated_list: List[AggregatedItem] = []
        for (vendor, item_name), stats in item_groups.items():
            aggregated_list.append(
                AggregatedItem(
                    vendor=vendor,
                    item_name=item_name,
                    variant="",
                    quantity=stats["quantity"],
                    subtotal=stats["subtotal"],
                    notes_list=stats["notes"]
                )
            )

        # Sort aggregated items by vendor then quantity descending
        aggregated_list.sort(key=lambda x: (x.vendor, -x.quantity))

        def format_idr(val: int) -> str:
            return f"{val:,}".replace(",", ".")

        # Unpaid users list for hover / quick inspect
        unpaid_users: List[UnpaidUserItem] = [
            UnpaidUserItem(
                order_id=o.id,
                user_name=o.user_name,
                item_name=o.item_name,
                vendor=o.vendor,
                price=o.price,
                payment_status=getattr(o, "payment_status", "UNPAID")
            )
            for o in order_schemas if not o.is_paid
        ]

        # Group aggregated items by vendor for WhatsApp recap
        vendor_groups = defaultdict(list)
        for item in aggregated_list:
            vendor_groups[item.vendor or "Lain-lain"].append(item)

        # Generate WhatsApp recap message grouped per tenant
        wa_lines = [
            f"📋 *Rekap Titip Makan: {session.title}*",
            f"👤 Koordinator: {session.coordinator_name}",
            f"📊 Total Pesanan: {len(order_schemas)} porsi",
            f"💰 Total Biaya: Rp {format_idr(total_amount)} (Lunas: {paid_count}, Belum: {unpaid_count})",
            "",
            "🏪 *Ringkasan Belanjaan per Tenant:*"
        ]

        for v_name, items in sorted(vendor_groups.items(), key=lambda x: x[0]):
            v_subtotal = sum(it.subtotal for it in items)
            v_subtotal_str = f" (Subtotal: Rp {format_idr(v_subtotal)})" if v_subtotal > 0 else ""
            wa_lines.append(f"\n[{v_name}]{v_subtotal_str}")
            for item in items:
                price_str = f" - Rp {format_idr(item.subtotal)}" if item.subtotal > 0 else ""
                wa_lines.append(f"• {item.quantity}x {item.item_name}{price_str}")
                if item.notes_list:
                    for note in item.notes_list:
                        wa_lines.append(f"   ↳ {note}")

        wa_lines.append("")
        wa_lines.append("📝 *Daftar Pemesan:*")
        for idx, o in enumerate(order_schemas, 1):
            if o.is_paid:
                status_icon = "✅ Lunas"
            elif getattr(o, "payment_status", "UNPAID") == "PENDING_CONFIRMATION":
                status_icon = "⏳ Menunggu Konfirmasi"
            else:
                status_icon = "❌ Belum Bayar"

            price_str = f" - Rp {format_idr(o.price)}" if o.price > 0 else " - (Belum di-set)"
            note_str = f" [Catatan: {o.notes}]" if o.notes else ""
            vendor_str = f"[{o.vendor}] " if o.vendor else ""
            wa_lines.append(f"{idx}. {o.user_name} - {vendor_str}{o.item_name}{price_str}{note_str} ({status_icon})")

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
            unpaid_orders_users=unpaid_users,
            whatsapp_recap_text=whatsapp_recap
        )
