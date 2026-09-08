import pytest
from titip_makan.services.session_service import SessionService
from titip_makan.services.order_service import OrderService
from titip_makan.schemas.session import SessionCreate
from titip_makan.schemas.order import OrderCreate, OrderUpdate

@pytest.mark.asyncio
async def test_order_payment_lifecycle(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(title="Sesi Bayar", coordinator_name="Irzi")
    )

    # 1. Create order: initially UNPAID and is_paid=False
    order = await order_service.create_order(
        session.id,
        OrderCreate(user_name="Amal", vendor="Babun", item_name="Babun Nasi Telor Dobel", price=13000)
    )
    assert order.is_paid is False
    assert order.payment_status == "UNPAID"

    # 2. User claims they have paid -> PENDING_CONFIRMATION
    claimed = await order_service.claim_order_payment(order.id)
    assert claimed.payment_status == "PENDING_CONFIRMATION"
    assert claimed.is_paid is False

    # 3. Coordinator confirms payment -> PAID and is_paid=True
    confirmed = await order_service.update_payment_status(order.id, is_paid=True)
    assert confirmed.payment_status == "PAID"
    assert confirmed.is_paid is True

    # 4. Coordinator marks back to unpaid -> UNPAID and is_paid=False
    unpaid = await order_service.update_payment_status(order.id, is_paid=False)
    assert unpaid.payment_status == "UNPAID"
    assert unpaid.is_paid is False

@pytest.mark.asyncio
async def test_order_edit_allowed_when_unpaid(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(title="Sesi Edit", coordinator_name="Irzi")
    )

    order = await order_service.create_order(
        session.id,
        OrderCreate(user_name="Bilal", vendor="Mie Ayam", item_name="Mie Ayam Polos", notes="original", price=15000)
    )

    # Edit menu, notes, and price while UNPAID
    updated = await order_service.update_order(
        order.id,
        OrderUpdate(vendor="Mie Ayam", item_name="Mie Ayam Bakso", notes="kuah pisah", price=18000)
    )
    assert updated.item_name == "Mie Ayam Bakso"
    assert updated.notes == "kuah pisah"
    assert updated.price == 18000

@pytest.mark.asyncio
async def test_order_edit_rejected_when_paid_or_pending(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(title="Sesi Edit Protected", coordinator_name="Irzi")
    )

    order = await order_service.create_order(
        session.id,
        OrderCreate(user_name="Shazi", vendor="Babun", item_name="Babun Nasi Ayam Bakar", price=22000)
    )

    # Claim paid
    await order_service.claim_order_payment(order.id)

    # Trying to edit should raise ValueError
    with pytest.raises(ValueError, match="Pesanan sudah ditandai bayar atau lunas"):
        await order_service.update_order(
            order.id,
            OrderUpdate(item_name="Babun Nasi Ayam Kremes")
        )

@pytest.mark.asyncio
async def test_session_summary_includes_unpaid_users_and_tenant_grouping(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(title="Sesi Summary", coordinator_name="Irzi")
    )

    # Order 1: Amal (Paid)
    o1 = await order_service.create_order(
        session.id,
        OrderCreate(user_name="Amal", vendor="Babun", item_name="Nasi Telor", price=13000)
    )
    await order_service.update_payment_status(o1.id, is_paid=True)

    # Order 2: Bilal (Pending)
    o2 = await order_service.create_order(
        session.id,
        OrderCreate(user_name="Bilal", vendor="Mie Ayam", item_name="Mie Ayam Bakso", price=18000)
    )
    await order_service.claim_order_payment(o2.id)

    # Order 3: Shazi (Unpaid)
    await order_service.create_order(
        session.id,
        OrderCreate(user_name="Shazi", vendor="Babun", item_name="Ayam Bakar", price=22000)
    )

    summary = await order_service.get_session_summary(session.id)
    assert summary.total_orders == 3
    assert summary.total_paid_count == 1
    assert summary.total_unpaid_count == 2

    # Check unpaid users list
    unpaid_names = [u.user_name for u in summary.unpaid_orders_users]
    assert "Bilal" in unpaid_names
    assert "Shazi" in unpaid_names
    assert "Amal" not in unpaid_names

    # Check WhatsApp recap grouped per tenant
    assert "[Babun]" in summary.whatsapp_recap_text.replace(" ", "")
    assert "[Mie Ayam]" in summary.whatsapp_recap_text
