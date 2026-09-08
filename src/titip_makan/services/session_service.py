import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.repositories.session_repository import SessionRepository
from titip_makan.schemas.session import SessionCreate, SessionOut
from titip_makan.models.session import PoolSession

import logging
from titip_makan.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class SessionService:
    def __init__(self, db: AsyncSession, notifier: Optional[NotificationService] = None):
        self.repo = SessionRepository(db)
        self.notifier = notifier if notifier is not None else NotificationService()

    def _to_schema(self, session: PoolSession) -> SessionOut:
        try:
            vendors = json.loads(session.vendor_options) if session.vendor_options else []
        except Exception:
            vendors = [v.strip() for v in session.vendor_options.split(",") if v.strip()]

        return SessionOut(
            id=session.id,
            title=session.title,
            coordinator_name=session.coordinator_name,
            coordinator_phone=getattr(session, "coordinator_phone", None),
            vendor_options=vendors,
            payment_info=session.payment_info,
            status=session.status,
            cutoff_at=session.cutoff_at,
            created_at=session.created_at,
            closed_at=session.closed_at
        )

    async def create_session(self, data: SessionCreate) -> SessionOut:
        cutoff_at = None
        if data.cutoff_minutes is not None:
            cutoff_at = datetime.now(timezone.utc) + timedelta(minutes=data.cutoff_minutes)

        session = await self.repo.create(
            title=data.title,
            coordinator_name=data.coordinator_name,
            vendor_options=data.vendor_options,
            payment_info=data.payment_info,
            cutoff_at=cutoff_at,
            coordinator_phone=data.coordinator_phone
        )
        session_out = self._to_schema(session)

        # Automatically broadcast announcement to WhatsApp group
        if self.notifier:
            try:
                await self.notifier.broadcast_session_opened(session_out)
            except Exception as e:
                logger.error(f"Failed to broadcast session opened to WhatsApp: {e}")

        return session_out

    async def broadcast_session(self, session_id: int, chat_id: Optional[str] = None):
        session_out = await self.get_session_by_id(session_id)
        if not session_out:
            raise ValueError(f"Session with ID {session_id} not found")
        if self.notifier:
            return await self.notifier.broadcast_session_opened(session_out, chat_id)
        return {"status": "skipped", "reason": "no_notifier"}

    async def get_latest_session(self) -> Optional[SessionOut]:
        session = await self.repo.get_latest()
        if not session:
            return None
        return self._to_schema(session)

    async def get_active_session(self) -> Optional[SessionOut]:
        session = await self.repo.get_active()
        if not session:
            return None
        
        # Check if cutoff has passed and should auto-close
        if session.cutoff_at:
            now = datetime.now(timezone.utc)
            cutoff = session.cutoff_at if session.cutoff_at.tzinfo else session.cutoff_at.replace(tzinfo=timezone.utc)
            if now > cutoff:
                session = await self.repo.close(session.id)
                return None

        return self._to_schema(session)

    async def get_session_by_id(self, session_id: int) -> Optional[SessionOut]:
        session = await self.repo.get_by_id(session_id)
        if not session:
            return None
        return self._to_schema(session)

    async def close_session(self, session_id: int) -> SessionOut:
        session = await self.repo.close(session_id)
        if not session:
            raise ValueError(f"Session with ID {session_id} not found")
        return self._to_schema(session)
