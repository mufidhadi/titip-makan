import pytest
from datetime import datetime, timezone
from titip_makan.services.session_service import SessionService
from titip_makan.services.order_service import OrderService
from titip_makan.schemas.session import SessionCreate
from titip_makan.schemas.order import OrderCreate

@pytest.mark.asyncio
async def test_closed_session_reopen_with_plus_5_minutes(db_session):
    session_service = SessionService(db_session)
    session = await session_service.create_session(
        SessionCreate(title="Sesi Makan Siang", coordinator_name="Irzi", cutoff_minutes=15)
    )
    
    # Close session
    closed = await session_service.close_session(session.id)
    assert closed.status == "CLOSED"
    assert closed.closed_at is not None
    assert await session_service.get_active_session() is None

    # Reopen temporarily with +5 minutes
    reopened = await session_service.update_cutoff(session.id, extend_minutes=5)
    assert reopened.status == "OPEN"
    assert reopened.closed_at is None
    now_utc = datetime.now(timezone.utc)
    diff = (reopened.cutoff_at - now_utc).total_seconds()
    assert 280 <= diff <= 310  # roughly 5 minutes (300 seconds)

    # Now active session should be returned
    active = await session_service.get_active_session()
    assert active is not None
    assert active.id == session.id
    assert active.status == "OPEN"


@pytest.mark.asyncio
async def test_closed_session_reopen_with_plus_10_minutes(db_session):
    session_service = SessionService(db_session)
    session = await session_service.create_session(
        SessionCreate(title="Sesi Makan Siang 10m", coordinator_name="Irzi", cutoff_minutes=15)
    )
    
    # Close session
    closed = await session_service.close_session(session.id)
    assert closed.status == "CLOSED"

    # Reopen temporarily with +10 minutes
    reopened = await session_service.update_cutoff(session.id, extend_minutes=10)
    assert reopened.status == "OPEN"
    assert reopened.closed_at is None
    now_utc = datetime.now(timezone.utc)
    diff = (reopened.cutoff_at - now_utc).total_seconds()
    assert 580 <= diff <= 610  # roughly 10 minutes (600 seconds)


@pytest.mark.asyncio
async def test_order_creation_allowed_after_reopening_closed_session(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(title="Sesi Titip Mie", coordinator_name="Irzi", cutoff_minutes=15)
    )
    
    # Close session
    await session_service.close_session(session.id)

    # Verify orders cannot be submitted while closed
    with pytest.raises(ValueError, match="Session is closed"):
        await order_service.create_order(
            session.id,
            OrderCreate(user_name="Budi", vendor="Mie Ayam", item_name="Mie Komplit", price=20000)
        )

    # Reopen temporarily with +5 minutes
    await session_service.update_cutoff(session.id, extend_minutes=5)

    # Now order submission succeeds!
    order = await order_service.create_order(
        session.id,
        OrderCreate(user_name="Budi", vendor="Mie Ayam", item_name="Mie Komplit", price=20000)
    )
    assert order.id is not None
    assert order.user_name == "Budi"
    assert order.session_id == session.id
