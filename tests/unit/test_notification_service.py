import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from titip_makan.schemas.session import SessionOut
from titip_makan.services.notification_service import NotificationService, format_session_announcement

def test_format_session_announcement():
    session = SessionOut(
        id=1,
        title="Titip Makan Siang MTN CORE",
        status="OPEN",
        coordinator_name="Irzi",
        coordinator_phone="+62 815-1382-5480",
        vendor_options=["Babun", "Mie Ayam"],
        payment_info="gopay ke +62 815-1382-5480",
        cutoff_at=datetime(2026, 9, 8, 4, 30, tzinfo=timezone.utc), # 11:30 WIB
        created_at=datetime(2026, 9, 8, 3, 30, tzinfo=timezone.utc),
        orders=[]
    )
    
    msg = format_session_announcement(session, public_url="https://titip-irzi.masmuf.cloud")
    
    # Must contain assistant perspective as required by user rules
    assert "asisten mas mufid" in msg.lower()
    assert "Titip Makan Siang MTN CORE" in msg
    assert "Irzi" in msg
    assert "+62 815-1382-5480" in msg
    assert "Babun, Mie Ayam" in msg
    assert "11:30 WIB" in msg
    assert "https://titip-irzi.masmuf.cloud" in msg
    assert "gopay ke +62 815-1382-5480" in msg

@pytest.mark.asyncio
async def test_notification_service_send_success():
    service = NotificationService(
        base_url="https://waha.masmuf.cloud",
        api_key="fake-key",
        default_chat_id="120363409564046383@g.us",
        enabled=True
    )
    
    import httpx
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = httpx.Response(
            200,
            json={"status": "success", "_data": {"id": "true_120363409564046383@g.us_3EB0"}},
            request=httpx.Request("POST", "https://waha.masmuf.cloud/api/sendText")
        )
        
        session = SessionOut(
            id=1,
            title="Sesi Makan Siang",
            status="OPEN",
            coordinator_name="Irzi",
            coordinator_phone="+62 815-1382-5480",
            vendor_options=["Babun"],
            payment_info="gopay",
            cutoff_at=None,
            created_at=datetime.now(timezone.utc),
            orders=[]
        )
        
        res = await service.broadcast_session_opened(session)
        assert res["status"] == "success"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["chatId"] == "120363409564046383@g.us"
        assert "asisten mas mufid" in call_kwargs["json"]["text"].lower()

@pytest.mark.asyncio
async def test_notification_service_disabled_skips():
    service = NotificationService(
        base_url="https://waha.masmuf.cloud",
        api_key="fake-key",
        default_chat_id="120363409564046383@g.us",
        enabled=False
    )
    session = SessionOut(
        id=1,
        title="Sesi Makan Siang",
        status="OPEN",
        coordinator_name="Irzi",
        coordinator_phone=None,
        vendor_options=[],
        payment_info=None,
        cutoff_at=None,
        created_at=datetime.now(timezone.utc),
        orders=[]
    )
    res = await service.broadcast_session_opened(session)
    assert res["status"] == "skipped"

@pytest.mark.asyncio
async def test_session_service_create_triggers_broadcast(db_session):
    from titip_makan.services.session_service import SessionService
    from titip_makan.schemas.session import SessionCreate
    
    mock_notifier = AsyncMock(spec=NotificationService)
    mock_notifier.broadcast_session_opened.return_value = {"status": "success"}
    
    service = SessionService(db_session, notifier=mock_notifier)
    session_data = SessionCreate(
        title="Sesi dengan Notifikasi WA",
        coordinator_name="Irzi",
        vendor_options=["Babun"]
    )
    session = await service.create_session(session_data)
    assert session.id is not None
    mock_notifier.broadcast_session_opened.assert_called_once()

@pytest.mark.asyncio
async def test_session_service_create_tolerates_broadcast_failure(db_session):
    from titip_makan.services.session_service import SessionService
    from titip_makan.schemas.session import SessionCreate
    
    mock_notifier = AsyncMock(spec=NotificationService)
    mock_notifier.broadcast_session_opened.side_effect = Exception("WAHA API timeout")
    
    service = SessionService(db_session, notifier=mock_notifier)
    session_data = SessionCreate(
        title="Sesi WAHA Timeout",
        coordinator_name="Irzi",
        vendor_options=["Babun"]
    )
    # Must not raise error
    session = await service.create_session(session_data)
    assert session.id is not None
    assert session.status == "OPEN"
