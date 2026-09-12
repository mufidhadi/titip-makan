from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from titip_makan.core.catalog import MASTER_CATALOG, MAIN_DISH_MIN_PRICE
from titip_makan.repositories.order_repository import OrderRepository
from titip_makan.repositories.session_repository import SessionRepository
from titip_makan.schemas.wheel import WheelCandidate, WheelCandidates
from titip_makan.services.session_service import SessionService


class NoActiveSessionError(ValueError):
    pass


class InvalidTenantError(ValueError):
    pass


def _normalize(value: str) -> str:
    return value.strip().casefold()


class WheelService:
    def __init__(self, db: AsyncSession):
        self.session_repo = SessionRepository(db)
        self.order_repo = OrderRepository(db)
        self.session_service = SessionService(db)

    async def get_tenant_candidates(self, avoid_last: bool = False) -> WheelCandidates:
        # avoid_last semantics on a tie: if multiple vendors share the top order
        # count in the last finished session, ALL of them are excluded (not just
        # one). This is intentional per spec section 3.3 ("Kalau seri, semua
        # vendor yang seri ikut") — see test_tenant_avoid_last_tie_excludes_all_tied_vendors.
        vendor_names = sorted(MASTER_CATALOG.keys())
        candidates = [
            WheelCandidate(label=name, vendor=name, price=None) for name in vendor_names
        ]

        if not avoid_last:
            return WheelCandidates(mode="tenant", candidates=candidates)

        now = datetime.now(timezone.utc)
        last_session = await self.session_repo.get_latest_finished(now)
        if not last_session:
            return WheelCandidates(mode="tenant", candidates=candidates)

        orders = await self.order_repo.get_by_session(last_session.id)
        if not orders:
            return WheelCandidates(mode="tenant", candidates=candidates)

        counts: Dict[str, int] = {}
        for order in orders:
            key = _normalize(order.vendor)
            counts[key] = counts.get(key, 0) + 1

        max_count = max(counts.values())
        top_vendors = {key for key, count in counts.items() if count == max_count}

        filtered = [c for c in candidates if _normalize(c.vendor) not in top_vendors]
        excluded = [c.vendor for c in candidates if _normalize(c.vendor) in top_vendors]

        if not filtered:
            return WheelCandidates(mode="tenant", candidates=candidates)

        return WheelCandidates(
            mode="tenant",
            candidates=filtered,
            excluded_last_tenants=excluded,
            avoid_last_applied=True,
        )

    async def get_item_candidates(
        self,
        tenant: Optional[str] = None,
        max_price: Optional[int] = None,
        main_only: bool = True,
    ) -> WheelCandidates:
        active_session = await self.session_service.get_active_session()
        if not active_session:
            raise NoActiveSessionError("Tidak ada sesi aktif")

        catalog_by_key = {_normalize(name): name for name in MASTER_CATALOG.keys()}

        eligible_vendors: List[str] = []
        seen = set()
        for vendor in active_session.vendor_options:
            key = _normalize(vendor)
            if key in catalog_by_key and key not in seen:
                seen.add(key)
                eligible_vendors.append(catalog_by_key[key])

        target_vendors = eligible_vendors
        if tenant is not None:
            tenant_key = _normalize(tenant)
            matched = next((v for v in eligible_vendors if _normalize(v) == tenant_key), None)
            if matched is None:
                raise InvalidTenantError(f"Tenant '{tenant}' tidak tersedia pada sesi ini")
            target_vendors = [matched]

        candidates: List[WheelCandidate] = []
        for vendor in target_vendors:
            for item_name, price in MASTER_CATALOG[vendor].items():
                if main_only and price < MAIN_DISH_MIN_PRICE:
                    continue
                if max_price is not None and price > max_price:
                    continue
                candidates.append(WheelCandidate(label=item_name, vendor=vendor, price=price))

        return WheelCandidates(mode="item", candidates=candidates, vendors=eligible_vendors)
