import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from titip_makan.services.session_service import SessionService
from titip_makan.schemas.session import SessionCreate
from titip_makan.services.scheduler_service import SchedulerService

WIB = timezone(timedelta(hours=7))

@pytest.mark.asyncio
async def test_session_cutoff_extension_and_close(db_session):
    session_service = SessionService(db_session)
    session = await session_service.create_session(
        SessionCreate(title="Sesi Cutoff Test", coordinator_name="Irzi", cutoff_minutes=15)
    )
    initial_cutoff = session.cutoff_at

    # 1. Extend +5 minutes
    extended_5 = await session_service.update_cutoff(session.id, extend_minutes=5)
    diff_5 = (extended_5.cutoff_at - initial_cutoff).total_seconds()
    assert abs(diff_5 - 300) < 2  # 5 minutes = 300 seconds

    # 2. Extend +10 minutes
    extended_10 = await session_service.update_cutoff(session.id, extend_minutes=10)
    diff_10 = (extended_10.cutoff_at - extended_5.cutoff_at).total_seconds()
    assert abs(diff_10 - 600) < 2  # 10 minutes = 600 seconds

    # 3. Close cutoff now
    closed = await session_service.update_cutoff(session.id, close_now=True)
    now_utc = datetime.now(timezone.utc)
    diff_now = abs((closed.cutoff_at - now_utc).total_seconds())
    assert diff_now < 5  # Cutoff is set to right now

@pytest.mark.asyncio
async def test_scheduler_creates_session_on_weekday_10am(db_session):
    mock_notifier = AsyncMock()
    mock_notifier.broadcast_session_opened.return_value = {"status": "success"}

    scheduler = SchedulerService(db_session_factory=lambda: db_session, notifier=mock_notifier)

    # Tuesday at 10:00:00 WIB (weekday = 1)
    fake_tuesday_10am = datetime(2026, 9, 8, 10, 0, 0, tzinfo=WIB)

    session = await scheduler.check_and_create_daily_session(now_wib=fake_tuesday_10am)
    assert session is not None
    assert "Selasa" in session.title
    assert session.coordinator_name == "Irzi"
    assert session.coordinator_phone == "+62 815-1382-5480"
    assert session.status == "OPEN"
    
    # Cutoff should be approximately 30 minutes (10:30 WIB)
    cutoff_wib = session.cutoff_at.astimezone(WIB)
    assert cutoff_wib.hour == 10
    assert cutoff_wib.minute == 30

@pytest.mark.asyncio
async def test_scheduler_skips_on_weekend(db_session):
    scheduler = SchedulerService(db_session_factory=lambda: db_session)

    # Saturday at 10:00:00 WIB (weekday = 5)
    fake_saturday = datetime(2026, 9, 12, 10, 0, 0, tzinfo=WIB)

    session = await scheduler.check_and_create_daily_session(now_wib=fake_saturday)
    assert session is None

@pytest.mark.asyncio
async def test_scheduler_idempotent_single_session_per_day(db_session):
    mock_notifier = AsyncMock()
    scheduler = SchedulerService(db_session_factory=lambda: db_session, notifier=mock_notifier)

    # Wednesday at 10:00:00 WIB
    fake_wednesday = datetime(2026, 9, 9, 10, 0, 0, tzinfo=WIB)

    # First trigger -> creates session
    s1 = await scheduler.check_and_create_daily_session(now_wib=fake_wednesday)
    assert s1 is not None

    # Second trigger 5 minutes later -> should NOT create duplicate session
    fake_wednesday_later = datetime(2026, 9, 9, 10, 5, 0, tzinfo=WIB)
    s2 = await scheduler.check_and_create_daily_session(now_wib=fake_wednesday_later)
    assert s2 is None

@pytest.mark.asyncio
async def test_create_session_routes_wa_to_personal_in_development(db_session):
    from titip_makan.services.notification_service import NotificationService
    import httpx

    notifier = NotificationService(
        base_url="https://waha.masmuf.cloud",
        api_key="test-api-key",
        default_chat_id="120363409564046383@g.us",
        mufid_chat_id="6285740130359@c.us",
        environment="development",
        enabled=True
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json={"status": "success", "_data": {"id": "test_msg_id"}},
            request=httpx.Request("POST", "https://waha.masmuf.cloud/api/sendText")
        )

        service = SessionService(db_session, notifier=notifier)
        session = await service.create_session(
            SessionCreate(
                title="Sesi Test Lokal Baru",
                coordinator_name="Irzi",
                vendor_options=["Babun"]
            )
        )
        assert session.id is not None

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        # Verify it went to mas mufid's personal WA, and NOT the group
        assert call_kwargs["json"]["chatId"] == "6285740130359@c.us"
        assert call_kwargs["json"]["chatId"] != "120363409564046383@g.us"
        assert "TEST LOKAL" in call_kwargs["json"]["text"]
