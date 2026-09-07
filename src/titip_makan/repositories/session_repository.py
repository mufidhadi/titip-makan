import json
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.models.session import PoolSession

class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        title: str,
        coordinator_name: str,
        vendor_options: List[str],
        payment_info: Optional[str] = None,
        cutoff_at: Optional[datetime] = None
    ) -> PoolSession:
        # Auto-close any previous open sessions
        await self.db.execute(
            update(PoolSession)
            .where(PoolSession.status == "OPEN")
            .values(status="CLOSED", closed_at=datetime.now(timezone.utc))
        )

        session = PoolSession(
            title=title,
            coordinator_name=coordinator_name,
            vendor_options=json.dumps(vendor_options),
            payment_info=payment_info,
            status="OPEN",
            cutoff_at=cutoff_at,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: int) -> Optional[PoolSession]:
        result = await self.db.execute(select(PoolSession).where(PoolSession.id == session_id))
        return result.scalars().first()

    async def get_latest(self) -> Optional[PoolSession]:
        result = await self.db.execute(
            select(PoolSession).order_by(PoolSession.id.desc())
        )
        return result.scalars().first()

    async def get_active(self) -> Optional[PoolSession]:
        result = await self.db.execute(
            select(PoolSession)
            .where(PoolSession.status == "OPEN")
            .order_by(PoolSession.id.desc())
        )
        return result.scalars().first()

    async def close(self, session_id: int) -> Optional[PoolSession]:
        session = await self.get_by_id(session_id)
        if session:
            session.status = "CLOSED"
            session.closed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(session)
        return session
