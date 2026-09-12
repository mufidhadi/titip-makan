import pytest
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


@pytest.mark.asyncio
async def test_get_paginated_history(db_session):
    session_service = SessionService(db_session)

    # Create 5 distinct sessions
    created_ids = []
    for i in range(5):
        s = await session_service.create_session(
            SessionCreate(title=f"Sesi Halaman {i+1}", coordinator_name=f"Koord {i+1}")
        )
        created_ids.append(s.id)

    # Test page 1 with limit 2
    p1 = await session_service.get_paginated_history(page=1, limit=2)
    assert p1.total >= 5
    assert len(p1.items) == 2
    assert p1.page == 1
    assert p1.limit == 2
    assert p1.total_pages == (p1.total + 2 - 1) // 2

    # Test page 2 with limit 2
    p2 = await session_service.get_paginated_history(page=2, limit=2)
    assert len(p2.items) == 2
    assert p2.page == 2
    # Ensure items on page 2 are different from page 1
    p1_ids = [item.id for item in p1.items]
    p2_ids = [item.id for item in p2.items]
    assert not set(p1_ids).intersection(set(p2_ids))

    # Test page out of range
    p_out = await session_service.get_paginated_history(page=999, limit=10)
    assert len(p_out.items) == 0
    assert p_out.page == 999


