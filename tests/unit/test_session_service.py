import pytest
from datetime import datetime, timedelta, timezone
from titip_makan.services.session_service import SessionService
from titip_makan.schemas.session import SessionCreate

@pytest.mark.asyncio
async def test_create_session(db_session):
    service = SessionService(db_session)
    session_data = SessionCreate(
        title="Titip Makan 7/09/2026",
        coordinator_name="Zi",
        vendor_options=["Mie Ayam", "Babun"],
        payment_info="BCA 1234567 a.n. Zi",
        cutoff_minutes=30
    )
    session = await service.create_session(session_data)
    assert session.id is not None
    assert session.title == "Titip Makan 7/09/2026"
    assert session.status == "OPEN"
    assert session.coordinator_name == "Zi"
    assert session.cutoff_at is not None

@pytest.mark.asyncio
async def test_get_active_session(db_session):
    service = SessionService(db_session)
    session_data = SessionCreate(
        title="Titip Makan Siang",
        coordinator_name="Zi",
        vendor_options=["Mie Ayam"],
        payment_info="BCA 1234567 a.n. Zi",
        cutoff_minutes=15
    )
    created = await service.create_session(session_data)
    active = await service.get_active_session()
    assert active is not None
    assert active.id == created.id

@pytest.mark.asyncio
async def test_close_session(db_session):
    service = SessionService(db_session)
    session_data = SessionCreate(
        title="Titip Makan Siang",
        coordinator_name="Zi",
        vendor_options=["Mie Ayam"],
        payment_info="BCA 1234567 a.n. Zi"
    )
    session = await service.create_session(session_data)
    closed = await service.close_session(session.id)
    assert closed.status == "CLOSED"
    assert closed.closed_at is not None

    active = await service.get_active_session()
    assert active is None

@pytest.mark.asyncio
async def test_create_session_with_defaults(db_session):
    service = SessionService(db_session)
    session_data = SessionCreate(
        title="Titip Makan Siang"
    )
    session = await service.create_session(session_data)
    assert session.coordinator_name == "Irzi"
    assert session.coordinator_phone == "+62 815-1382-5480"

@pytest.mark.asyncio
async def test_get_history_includes_order_details(db_session):
    from titip_makan.services.order_service import OrderService
    from titip_makan.schemas.order import OrderCreate

    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(title="Sesi Riwayat Lengkap", coordinator_name="Irzi")
    )
    await order_service.create_order(
        session.id,
        OrderCreate(user_name="Amal", vendor="Babun", item_name="Nasi Telor", price=13000)
    )
    await order_service.create_order(
        session.id,
        OrderCreate(user_name="Shazi", vendor="Mie Ayam", item_name="Mie Bakso", price=18000)
    )

    history = await session_service.get_history()
    target = next((s for s in history if s.id == session.id), None)
    assert target is not None
    assert len(target.orders) == 2
    assert target.orders[0].user_name in ["Amal", "Shazi"]
    assert target.orders[1].user_name in ["Amal", "Shazi"]

