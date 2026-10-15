import json
import random
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.core.catalog import MASTER_CATALOG
from titip_makan.models.auto_order import AutoOrderPreference
from titip_makan.repositories.order_repository import OrderRepository
from titip_makan.repositories.session_repository import SessionRepository
from titip_makan.schemas.auto_order import AutoOrderPreferenceIn, AutoOrderPreferenceOut
from titip_makan.schemas.order import OrderCreate, OrderOut
from titip_makan.services.order_service import OrderService

AUTO_ORDER_NOTE = "🎲 auto random"

class AutoOrderService:
    def __init__(self, db: AsyncSession, rng: random.Random = random):
        self.db = db
        self.rng = rng

    async def _find(self, user_name: str) -> Optional[AutoOrderPreference]:
        result = await self.db.execute(
            select(AutoOrderPreference).where(func.lower(AutoOrderPreference.user_name) == user_name.strip().lower())
        )
        return result.scalars().first()

    def _to_schema(self, pref: AutoOrderPreference) -> AutoOrderPreferenceOut:
        return AutoOrderPreferenceOut(
            user_name=pref.user_name, enabled=pref.enabled, candidates=json.loads(pref.candidates or "[]")
        )

    async def get_preference(self, user_name: str) -> AutoOrderPreferenceOut:
        pref = await self._find(user_name)
        if not pref:
            return AutoOrderPreferenceOut(user_name=user_name.strip(), enabled=False, candidates=[])
        return self._to_schema(pref)

    async def save_preference(self, data: AutoOrderPreferenceIn) -> AutoOrderPreferenceOut:
        pref = await self._find(data.user_name)
        if not pref:
            pref = AutoOrderPreference(user_name=data.user_name)
            self.db.add(pref)
        pref.enabled = data.enabled
        pref.candidates = json.dumps([c.model_dump() for c in data.candidates])
        pref.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(pref)
        return self._to_schema(pref)

    async def place_orders_for_active_session(self) -> List[OrderOut]:
        """Order one random candidate for every enabled user not yet handled in the open session."""
        session = await SessionRepository(self.db).get_active()
        if not session:
            return []

        result = await self.db.execute(
            select(AutoOrderPreference).where(
                AutoOrderPreference.enabled.is_(True),
                (AutoOrderPreference.last_session_id.is_(None)) | (AutoOrderPreference.last_session_id != session.id),
            )
        )
        prefs = list(result.scalars().all())
        if not prefs:
            return []

        existing = await OrderRepository(self.db).get_by_session(session.id)
        ordered_users = {o.user_name.lower() for o in existing}
        order_service = OrderService(self.db)
        placed: List[OrderOut] = []

        for pref in prefs:
            candidates = json.loads(pref.candidates or "[]")
            if candidates and pref.user_name.lower() not in ordered_users:
                pick = self.rng.choice(candidates)
                catalog_price = MASTER_CATALOG.get(pick["vendor"], {}).get(pick["item_name"])
                try:
                    placed.append(await order_service.create_order(session.id, OrderCreate(
                        user_name=pref.user_name,
                        vendor=pick["vendor"],
                        item_name=pick["item_name"],
                        notes=AUTO_ORDER_NOTE,
                        price=catalog_price if catalog_price is not None else pick.get("price", 0),
                    )))
                except ValueError:
                    # Session closed or cutoff passed while iterating; nothing more can be ordered.
                    break
            pref.last_session_id = session.id
            await self.db.commit()

        return placed
