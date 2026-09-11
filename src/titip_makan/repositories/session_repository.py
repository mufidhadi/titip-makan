import json
from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
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
        cutoff_at: Optional[datetime] = None,
        coordinator_phone: Optional[str] = None
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
            coordinator_phone=coordinator_phone,
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
        result = await self.db.execute(
            select(PoolSession)
            .options(selectinload(PoolSession.orders))
            .where(PoolSession.id == session_id)
        )
        return result.scalars().first()

    async def get_latest(self) -> Optional[PoolSession]:
        result = await self.db.execute(
            select(PoolSession)
            .options(selectinload(PoolSession.orders))
            .order_by(PoolSession.id.desc())
        )
        return result.scalars().first()

    async def get_active(self) -> Optional[PoolSession]:
        result = await self.db.execute(
            select(PoolSession)
            .where(PoolSession.status == "OPEN")
            .order_by(PoolSession.id.desc())
        )
        return result.scalars().first()

    async def get_latest_finished(self, now: datetime) -> Optional[PoolSession]:
        result = await self.db.execute(
            select(PoolSession).order_by(PoolSession.created_at.desc())
        )
        for session in result.scalars().all():
            if session.status == "CLOSED":
                return session
            if session.cutoff_at:
                cutoff = session.cutoff_at if session.cutoff_at.tzinfo else session.cutoff_at.replace(tzinfo=timezone.utc)
                if cutoff <= now:
                    return session
        return None

    async def close(self, session_id: int) -> Optional[PoolSession]:
        session = await self.get_by_id(session_id)
        if session:
            session.status = "CLOSED"
            session.closed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(session)
        return session

    async def update_cutoff(self, session_id: int, cutoff_at: Optional[datetime]) -> Optional[PoolSession]:
        session = await self.get_by_id(session_id)
        if session:
            session.cutoff_at = cutoff_at
            await self.db.commit()
            await self.db.refresh(session)
        return session

    async def get_all_history(self) -> List[PoolSession]:
        result = await self.db.execute(
            select(PoolSession)
            .options(selectinload(PoolSession.orders))
            .order_by(PoolSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_all_history(self) -> int:
        result = await self.db.execute(
            select(func.count(PoolSession.id))
        )
        return result.scalar() or 0

    async def get_paginated_history(self, limit: int, offset: int) -> List[PoolSession]:
        result = await self.db.execute(
            select(PoolSession)
            .options(selectinload(PoolSession.orders))
            .order_by(PoolSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

