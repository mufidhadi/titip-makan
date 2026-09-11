import pytest
from datetime import datetime, timedelta, timezone
from titip_makan.repositories.session_repository import SessionRepository
from titip_makan.services.session_service import SessionService
from titip_makan.services.order_service import OrderService
from titip_makan.schemas.session import SessionCreate
from titip_makan.schemas.order import OrderCreate


@pytest.mark.asyncio
async def test_repository_get_latest_finished_picks_correct_session(db_session):
    session_service = SessionService(db_session)
    repo = SessionRepository(db_session)

    # 1. A closed session (oldest)
    closed = await session_service.create_session(
        SessionCreate(title="Sesi Ditutup", coordinator_name="Zi", cutoff_minutes=30)
    )
    await session_service.close_session(closed.id)

    # 2. An OPEN session whose cutoff already passed (should count as finished)
    open_past_cutoff = await session_service.create_session(
        SessionCreate(title="Sesi Lewat Cutoff", coordinator_name="Zi", cutoff_minutes=-5)
    )

    # 3. An OPEN session whose cutoff is still in the future (NOT finished)
    open_future_cutoff = await session_service.create_session(
        SessionCreate(title="Sesi Masih Aktif", coordinator_name="Zi", cutoff_minutes=30)
    )

    now = datetime.now(timezone.utc)
    result = await repo.get_latest_finished(now)

    assert result is not None
    assert result.id == open_past_cutoff.id
