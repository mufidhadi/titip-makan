# Wheel of Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "spin the wheel" modal to `/coordinator` (pick a tenant) and `/` (pick a menu item), backed by a read-only candidates API, that prefills existing form fields without persisting anything.

**Architecture:** Backend adds a `WheelService` that derives candidate lists from `MASTER_CATALOG` plus session/order history, exposed via one `GET /api/v1/wheel/candidates` endpoint. Frontend adds a shared `window.MenuWheel` vanilla-JS module and one Jinja partial (`wheel_modal.html`) reused by both pages; each page wires a 🎡 button that calls `MenuWheel.open({mode, onApply})`.

**Tech Stack:** FastAPI + SQLAlchemy async + Pydantic v2 (backend, matches existing `services`/`repositories`/`schemas`/`api/v1` layering), vanilla JS + Tailwind CDN + Jinja2 (frontend, matches existing `app.js`/`coordinator.js`/`base.html` conventions), pytest + pytest-asyncio + httpx (unit/integration), Python Playwright (E2E).

**Spec:** `docs/superpowers/specs/2026-09-11-wheel-of-menu-design.md`

## Global Constraints

- All vendor-name matching is case/whitespace-insensitive: `value.strip().casefold()` (Python) / equivalent trimming (JS never does vendor matching — that's server-side only).
- Wheel results are never persisted to the DB. `MenuWheel.open`'s `onApply` callback only fills existing form fields.
- No new page or nav entry — the wheel is a modal on the existing `/` and `/coordinator` pages.
- Endpoint is read-only, no `X-Coordinator-PIN` required.
- `data-testid` values are fixed by the spec: `wheel-open-tenant`, `wheel-open-item`, `wheel-modal`, `wheel-close`, `wheel-svg`, `wheel-spin`, `wheel-result`, `wheel-apply`, `wheel-respin`, `wheel-avoid-last`, `wheel-main-only`, `wheel-max-price`, `wheel-tenant-filter`, `wheel-candidate`, `wheel-error`.
- `MAIN_DISH_MIN_PRICE = 10000` is inclusive (a 10000-priced item counts as a "makanan berat").
- Randomness for picking the wheel's winner must use `crypto.getRandomValues` (never `Math.random`), uniform over active (non-excluded) candidates.
- Frontend has no JS unit-test framework in this repo (no jest/vitest configured) — frontend correctness is verified through Playwright E2E tests only, per existing repo convention (`tests/e2e/*.py`).
- Run `uv run pytest -v` before every commit that touches Python; the suite must stay green (per `CONTRIBUTING.md`).

---

## File Structure

Backend (new):
- `src/titip_makan/schemas/wheel.py` — `WheelCandidate`, `WheelCandidates`
- `src/titip_makan/services/wheel_service.py` — `WheelService`, `NoActiveSessionError`, `InvalidTenantError`
- `src/titip_makan/api/v1/wheel.py` — `GET /api/v1/wheel/candidates`

Backend (modified):
- `src/titip_makan/core/catalog.py` — add `MAIN_DISH_MIN_PRICE`
- `src/titip_makan/repositories/session_repository.py` — add `get_latest_finished`
- `src/titip_makan/main.py` — register wheel router

Frontend (new):
- `src/titip_makan/templates/partials/wheel_modal.html` — shared modal markup
- `src/titip_makan/static/js/wheel.js` — `window.MenuWheel` module

Frontend (modified):
- `src/titip_makan/templates/coordinator.html` — 🎡 button + partial include + script tag
- `src/titip_makan/static/js/coordinator.js` — wire tenant-mode wheel
- `src/titip_makan/templates/index.html` — 🎡 button (session-gated) + partial include + script tag
- `src/titip_makan/static/js/app.js` — wire item-mode wheel

Tests (new):
- `tests/unit/test_wheel_service.py`
- `tests/integration/test_wheel_api.py`
- `tests/e2e/test_wheel_e2e.py`

---

### Task 1: Catalog constant + `SessionRepository.get_latest_finished`

**Files:**
- Modify: `src/titip_makan/core/catalog.py`
- Modify: `src/titip_makan/repositories/session_repository.py`
- Test: `tests/unit/test_wheel_service.py` (new file — repository test lives here per spec §5)

**Interfaces:**
- Produces: `MAIN_DISH_MIN_PRICE: int = 10000` (module constant in `titip_makan.core.catalog`)
- Produces: `SessionRepository.get_latest_finished(now: datetime) -> Optional[PoolSession]` — newest session (by `created_at` desc) where `status == "CLOSED"` OR (`cutoff_at` is set and `cutoff_at <= now`, comparing timezone-aware). Iterates in Python (like `session_service.get_active_session` already does) rather than filtering in SQL, to avoid SQLite naive/aware datetime comparison pitfalls that the rest of the codebase already works around.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_wheel_service.py` with just this first test:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_wheel_service.py::test_repository_get_latest_finished_picks_correct_session -v`
Expected: FAIL with `AttributeError: 'SessionRepository' object has no attribute 'get_latest_finished'`

- [ ] **Step 3: Add the catalog constant**

In `src/titip_makan/core/catalog.py`, add near the top (after the module docstring, before `MASTER_CATALOG`):

```python
MAIN_DISH_MIN_PRICE = 10000  # inclusive threshold for "makanan berat" (heuristic, price-based)
```

- [ ] **Step 4: Implement `get_latest_finished`**

In `src/titip_makan/repositories/session_repository.py`, add `timezone` to the existing `datetime` import (`from datetime import datetime, timezone`) and add this method to `SessionRepository` (after `get_active`):

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_wheel_service.py -v`
Expected: PASS (1 test)

- [ ] **Step 6: Commit**

```bash
git add src/titip_makan/core/catalog.py src/titip_makan/repositories/session_repository.py tests/unit/test_wheel_service.py
git commit -m "feat: add MAIN_DISH_MIN_PRICE constant and get_latest_finished repository query"
```

---

### Task 2: Wheel schemas

**Files:**
- Create: `src/titip_makan/schemas/wheel.py`

**Interfaces:**
- Produces:
  ```python
  class WheelCandidate(BaseModel):
      label: str
      vendor: str
      price: Optional[int] = None

  class WheelCandidates(BaseModel):
      mode: Literal["tenant", "item"]
      candidates: List[WheelCandidate] = Field(default_factory=list)
      vendors: List[str] = Field(default_factory=list)
      excluded_last_tenants: List[str] = Field(default_factory=list)
      avoid_last_applied: bool = False
  ```
- Consumed by `WheelService` (Task 3/4) and `api/v1/wheel.py` (Task 5).

No standalone test — this is a plain data schema exercised indirectly by every `WheelService` test in Tasks 3–4. Writing an isolated schema test would just re-assert Pydantic's own behavior (No Placeholders rule notwithstanding, this is the one exception the writing-plans skill allows: schemas with no independent behavior are verified through their consumers).

- [ ] **Step 1: Create the schema file**

```python
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class WheelCandidate(BaseModel):
    label: str
    vendor: str
    price: Optional[int] = None


class WheelCandidates(BaseModel):
    mode: Literal["tenant", "item"]
    candidates: List[WheelCandidate] = Field(default_factory=list)
    vendors: List[str] = Field(default_factory=list)
    excluded_last_tenants: List[str] = Field(default_factory=list)
    avoid_last_applied: bool = False
```

- [ ] **Step 2: Sanity-check import**

Run: `uv run python -c "from titip_makan.schemas.wheel import WheelCandidate, WheelCandidates; print(WheelCandidates(mode='tenant'))"`
Expected: prints `mode='tenant' candidates=[] vendors=[] excluded_last_tenants=[] avoid_last_applied=False`

- [ ] **Step 3: Commit**

```bash
git add src/titip_makan/schemas/wheel.py
git commit -m "feat: add WheelCandidate/WheelCandidates schemas"
```

---

### Task 3: `WheelService.get_tenant_candidates`

**Files:**
- Create: `src/titip_makan/services/wheel_service.py`
- Test: `tests/unit/test_wheel_service.py` (append)

**Interfaces:**
- Consumes: `SessionRepository.get_latest_finished` (Task 1), `OrderRepository.get_by_session` (existing), `MASTER_CATALOG` (existing), `WheelCandidate`/`WheelCandidates` (Task 2).
- Produces:
  ```python
  class NoActiveSessionError(ValueError): ...
  class InvalidTenantError(ValueError): ...

  class WheelService:
      def __init__(self, db: AsyncSession): ...
      async def get_tenant_candidates(self, avoid_last: bool = False) -> WheelCandidates: ...
  ```
  (`get_item_candidates` is added in Task 4 — this task's implementation only needs `get_tenant_candidates` to exist and work.)

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_wheel_service.py`:

```python
from titip_makan.services.wheel_service import WheelService
from titip_makan.core.catalog import MASTER_CATALOG


@pytest.mark.asyncio
async def test_tenant_candidates_are_catalog_keys_sorted_alphabetically(db_session):
    service = WheelService(db_session)
    result = await service.get_tenant_candidates()

    assert result.mode == "tenant"
    assert [c.label for c in result.candidates] == sorted(MASTER_CATALOG.keys())
    assert all(c.vendor == c.label for c in result.candidates)
    assert all(c.price is None for c in result.candidates)
    assert result.avoid_last_applied is False
    assert result.excluded_last_tenants == []


@pytest.mark.asyncio
async def test_tenant_avoid_last_no_history_has_no_effect(db_session):
    service = WheelService(db_session)
    result = await service.get_tenant_candidates(avoid_last=True)

    assert [c.label for c in result.candidates] == sorted(MASTER_CATALOG.keys())
    assert result.avoid_last_applied is False
    assert result.excluded_last_tenants == []


async def _finish_session_with_orders(db_session, vendor_counts: dict) -> int:
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(title="Sesi Kemarin", coordinator_name="Zi", cutoff_minutes=30)
    )
    n = 0
    for vendor, count in vendor_counts.items():
        for _ in range(count):
            n += 1
            await order_service.create_order(
                session.id,
                OrderCreate(user_name=f"User{n}", vendor=vendor, item_name="Item", price=10000)
            )
    await session_service.close_session(session.id)
    return session.id


@pytest.mark.asyncio
async def test_tenant_avoid_last_excludes_top_vendor(db_session):
    await _finish_session_with_orders(db_session, {"Babun": 2, "Mie Ayam": 1})

    service = WheelService(db_session)
    result = await service.get_tenant_candidates(avoid_last=True)

    assert result.avoid_last_applied is True
    assert result.excluded_last_tenants == ["Babun"]
    assert "Babun" not in [c.label for c in result.candidates]
    assert "Mie Ayam" in [c.label for c in result.candidates]


@pytest.mark.asyncio
async def test_tenant_avoid_last_tie_excludes_all_tied_vendors(db_session):
    await _finish_session_with_orders(db_session, {"Babun": 2, "Mie Ayam": 2, "Buah Potong": 1})

    service = WheelService(db_session)
    result = await service.get_tenant_candidates(avoid_last=True)

    assert result.avoid_last_applied is True
    assert set(result.excluded_last_tenants) == {"Babun", "Mie Ayam"}
    remaining = [c.label for c in result.candidates]
    assert "Babun" not in remaining
    assert "Mie Ayam" not in remaining
    assert "Buah Potong" in remaining
    assert "Kantin" in remaining


@pytest.mark.asyncio
async def test_tenant_avoid_last_case_insensitive_vendor_match(db_session):
    await _finish_session_with_orders(db_session, {"  babun  ": 3, "Mie Ayam": 1})

    service = WheelService(db_session)
    result = await service.get_tenant_candidates(avoid_last=True)

    assert result.excluded_last_tenants == ["Babun"]
    assert "Babun" not in [c.label for c in result.candidates]


@pytest.mark.asyncio
async def test_tenant_avoid_last_fallback_when_all_excluded(db_session):
    # One order per catalog vendor -> 4-way tie -> excluding all would empty the list -> fallback
    await _finish_session_with_orders(
        db_session, {vendor: 1 for vendor in MASTER_CATALOG.keys()}
    )

    service = WheelService(db_session)
    result = await service.get_tenant_candidates(avoid_last=True)

    assert result.avoid_last_applied is False
    assert result.excluded_last_tenants == []
    assert [c.label for c in result.candidates] == sorted(MASTER_CATALOG.keys())


@pytest.mark.asyncio
async def test_tenant_avoid_last_treats_open_session_past_cutoff_as_finished(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(title="Sesi Lewat Cutoff", coordinator_name="Zi", cutoff_minutes=-5)
    )
    await order_service.create_order(
        session.id, OrderCreate(user_name="Amal", vendor="Babun", item_name="Item", price=10000)
    )
    # Note: session status is still "OPEN" in the DB (nobody called close_session/get_active_session)

    service = WheelService(db_session)
    result = await service.get_tenant_candidates(avoid_last=True)

    assert result.avoid_last_applied is True
    assert result.excluded_last_tenants == ["Babun"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_wheel_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'titip_makan.services.wheel_service'`

- [ ] **Step 3: Implement `WheelService.get_tenant_candidates`**

Create `src/titip_makan/services/wheel_service.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_wheel_service.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add src/titip_makan/services/wheel_service.py tests/unit/test_wheel_service.py
git commit -m "feat: add WheelService.get_tenant_candidates with avoid_last rule"
```

---

### Task 4: `WheelService.get_item_candidates`

**Files:**
- Modify: `src/titip_makan/services/wheel_service.py`
- Test: `tests/unit/test_wheel_service.py` (append)

**Interfaces:**
- Consumes: `SessionService.get_active_session()` (existing, returns `Optional[SessionOut]` with `.vendor_options: List[str]`), `MASTER_CATALOG` (existing).
- Produces: `WheelService.get_item_candidates(tenant: Optional[str] = None, max_price: Optional[int] = None, main_only: bool = True) -> WheelCandidates`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_wheel_service.py`:

```python
from titip_makan.services.wheel_service import NoActiveSessionError, InvalidTenantError


@pytest.mark.asyncio
async def test_item_candidates_without_active_session_raises(db_session):
    service = WheelService(db_session)
    with pytest.raises(NoActiveSessionError):
        await service.get_item_candidates()


async def _open_session_with_vendors(db_session, vendor_options):
    session_service = SessionService(db_session)
    return await session_service.create_session(
        SessionCreate(
            title="Sesi Aktif",
            coordinator_name="Zi",
            vendor_options=vendor_options,
            cutoff_minutes=30,
        )
    )


@pytest.mark.asyncio
async def test_item_candidates_vendors_is_intersection_with_catalog(db_session):
    await _open_session_with_vendors(
        db_session, ["Mie Ayam", "Babun", "Nasi Goreng", "Dimsum"]
    )

    service = WheelService(db_session)
    result = await service.get_item_candidates(main_only=False)

    assert result.mode == "item"
    assert result.vendors == ["Mie Ayam", "Babun"]
    assert all(c.vendor in ("Mie Ayam", "Babun") for c in result.candidates)


@pytest.mark.asyncio
async def test_item_candidates_tenant_filter_valid(db_session):
    await _open_session_with_vendors(db_session, ["Mie Ayam", "Babun"])

    service = WheelService(db_session)
    result = await service.get_item_candidates(tenant="babun", main_only=False)

    assert result.vendors == ["Mie Ayam", "Babun"]
    assert len(result.candidates) == len(MASTER_CATALOG["Babun"])
    assert all(c.vendor == "Babun" for c in result.candidates)


@pytest.mark.asyncio
async def test_item_candidates_tenant_filter_invalid_raises(db_session):
    await _open_session_with_vendors(db_session, ["Mie Ayam", "Babun", "Dimsum"])

    service = WheelService(db_session)
    with pytest.raises(InvalidTenantError):
        await service.get_item_candidates(tenant="Dimsum")


@pytest.mark.asyncio
async def test_item_candidates_max_price_inclusive(db_session):
    await _open_session_with_vendors(db_session, ["Babun"])

    service = WheelService(db_session)
    result = await service.get_item_candidates(tenant="Babun", main_only=False, max_price=10000)

    labels = [c.label for c in result.candidates]
    assert "Babun Omelette" in labels  # exactly 10000, inclusive boundary
    assert all(c.price <= 10000 for c in result.candidates)
    assert "Babun Nasi Telor Dobel" not in labels  # 13000, over the limit


@pytest.mark.asyncio
async def test_item_candidates_main_only_excludes_below_threshold_keeps_exact_threshold(db_session):
    await _open_session_with_vendors(db_session, ["Babun"])

    service = WheelService(db_session)
    result = await service.get_item_candidates(tenant="Babun", main_only=True)

    labels = [c.label for c in result.candidates]
    assert "Babun Omelette" in labels  # exactly MAIN_DISH_MIN_PRICE, kept
    assert "Babun Es Teh Manis" not in labels  # 5000, excluded
    assert all(c.price >= 10000 for c in result.candidates)


@pytest.mark.asyncio
async def test_item_candidates_main_only_false_keeps_all(db_session):
    await _open_session_with_vendors(db_session, ["Babun"])

    service = WheelService(db_session)
    result = await service.get_item_candidates(tenant="Babun", main_only=False)

    assert len(result.candidates) == len(MASTER_CATALOG["Babun"])


@pytest.mark.asyncio
async def test_item_candidates_empty_when_no_matching_items(db_session):
    await _open_session_with_vendors(db_session, ["Buah Potong"])

    service = WheelService(db_session)
    result = await service.get_item_candidates(tenant="Buah Potong", main_only=True)

    assert result.candidates == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_wheel_service.py -v`
Expected: FAIL with `AttributeError: 'WheelService' object has no attribute 'get_item_candidates'`

- [ ] **Step 3: Implement `get_item_candidates`**

Add to `src/titip_makan/services/wheel_service.py`, inside the `WheelService` class (after `get_tenant_candidates`):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_wheel_service.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add src/titip_makan/services/wheel_service.py tests/unit/test_wheel_service.py
git commit -m "feat: add WheelService.get_item_candidates with tenant/price/main_only filters"
```

---

### Task 5: `GET /api/v1/wheel/candidates` endpoint

**Files:**
- Create: `src/titip_makan/api/v1/wheel.py`
- Modify: `src/titip_makan/main.py`
- Test: `tests/integration/test_wheel_api.py`

**Interfaces:**
- Consumes: `WheelService` (Task 3/4), `get_db` (existing, `titip_makan.core.database`).
- Produces: `router: APIRouter` importable as `titip_makan.api.v1.wheel.router`, registered in `main.py` with `prefix="/api/v1"` like the other v1 routers.

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_wheel_api.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from titip_makan.main import app
from titip_makan.core.database import get_db


async def _client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_wheel_candidates_tenant_mode_200(db_session):
    async with await _client(db_session) as client:
        resp = await client.get("/api/v1/wheel/candidates", params={"mode": "tenant"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "tenant"
        assert len(body["candidates"]) > 0
        assert body["candidates"][0]["price"] is None


@pytest.mark.asyncio
async def test_wheel_candidates_item_mode_200(db_session):
    async with await _client(db_session) as client:
        await client.post("/api/v1/sessions", json={
            "title": "Sesi Aktif",
            "coordinator_name": "Zi",
            "vendor_options": ["Mie Ayam", "Babun"],
            "cutoff_minutes": 30,
        })

        resp = await client.get("/api/v1/wheel/candidates", params={"mode": "item"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "item"
        assert body["vendors"] == ["Mie Ayam", "Babun"]
        assert all(c["price"] is not None for c in body["candidates"])


@pytest.mark.asyncio
async def test_wheel_candidates_item_mode_409_without_active_session(db_session):
    async with await _client(db_session) as client:
        resp = await client.get("/api/v1/wheel/candidates", params={"mode": "item"})
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Tidak ada sesi aktif"


@pytest.mark.asyncio
async def test_wheel_candidates_item_mode_400_invalid_tenant(db_session):
    async with await _client(db_session) as client:
        await client.post("/api/v1/sessions", json={
            "title": "Sesi Aktif",
            "coordinator_name": "Zi",
            "vendor_options": ["Babun"],
            "cutoff_minutes": 30,
        })

        resp = await client.get(
            "/api/v1/wheel/candidates", params={"mode": "item", "tenant": "Nonexistent"}
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_wheel_candidates_422_invalid_mode(db_session):
    async with await _client(db_session) as client:
        resp = await client.get("/api/v1/wheel/candidates", params={"mode": "bogus"})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_wheel_candidates_422_negative_max_price(db_session):
    async with await _client(db_session) as client:
        resp = await client.get(
            "/api/v1/wheel/candidates", params={"mode": "item", "max_price": -1}
        )
        assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_wheel_api.py -v`
Expected: FAIL with 404 (route doesn't exist yet)

- [ ] **Step 3: Implement the router**

Create `src/titip_makan/api/v1/wheel.py`:

```python
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from titip_makan.core.database import get_db
from titip_makan.schemas.wheel import WheelCandidates
from titip_makan.services.wheel_service import (
    InvalidTenantError,
    NoActiveSessionError,
    WheelService,
)

router = APIRouter(prefix="/wheel", tags=["wheel"])


@router.get("/candidates", response_model=WheelCandidates)
async def get_wheel_candidates(
    mode: Literal["tenant", "item"] = Query(...),
    avoid_last: bool = Query(False),
    tenant: Optional[str] = Query(None),
    max_price: Optional[int] = Query(None, ge=0),
    main_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    service = WheelService(db)

    if mode == "tenant":
        return await service.get_tenant_candidates(avoid_last=avoid_last)

    tenant_value = tenant.strip() if tenant and tenant.strip() else None
    try:
        return await service.get_item_candidates(
            tenant=tenant_value, max_price=max_price, main_only=main_only
        )
    except NoActiveSessionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except InvalidTenantError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 4: Register the router**

In `src/titip_makan/main.py`, add the import next to the other `api.v1` imports:

```python
from titip_makan.api.v1.wheel import router as wheel_router
```

And add next to the other `app.include_router(..., prefix="/api/v1")` calls:

```python
app.include_router(wheel_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_wheel_api.py -v`
Expected: PASS (all tests)

- [ ] **Step 6: Run the full backend suite**

Run: `uv run pytest tests/unit tests/integration -v`
Expected: PASS (no regressions)

- [ ] **Step 7: Commit**

```bash
git add src/titip_makan/api/v1/wheel.py src/titip_makan/main.py tests/integration/test_wheel_api.py
git commit -m "feat: add GET /api/v1/wheel/candidates endpoint"
```

---

### Task 6: Wheel modal partial + `wheel.js` module

**Files:**
- Create: `src/titip_makan/templates/partials/wheel_modal.html`
- Create: `src/titip_makan/static/js/wheel.js`

**Interfaces:**
- Produces: `window.MenuWheel.open({ mode: "tenant" | "item", onApply: (candidate) => void })`, where `candidate` is `{ label, vendor, price }` matching the API's `WheelCandidate` shape.
- Consumes: `GET /api/v1/wheel/candidates` (Task 5).
- No automated test in this task — this is pure markup/JS with no test runner in the repo for it. It is exercised end-to-end by Task 9's Playwright tests, after Tasks 7–8 wire it into both pages. Treat this task's own verification as "loads without console errors" (checked manually via the `run` workflow before Task 9, see note at end of Task 8).

- [ ] **Step 1: Create the modal partial**

Create `src/titip_makan/templates/partials/wheel_modal.html`:

```html
<div id="wheel-modal" data-testid="wheel-modal" class="fixed inset-0 z-[60] hidden items-end sm:items-center justify-center p-0 sm:p-4 bg-slate-900/60 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="wheel-modal-title">
    <div class="bg-white rounded-t-3xl sm:rounded-2xl shadow-2xl max-w-lg w-full max-h-[92vh] overflow-y-auto border border-slate-200 p-5 sm:p-6">
        <div class="w-12 h-1.5 bg-slate-200 rounded-full mx-auto mb-3 sm:hidden"></div>

        <div class="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <h3 id="wheel-modal-title" class="text-base font-bold text-slate-800 flex items-center gap-2">
                <span>🎡</span> <span id="wheel-modal-heading">Roda Pilihan</span>
            </h3>
            <button type="button" id="wheel-close" data-testid="wheel-close" aria-label="Tutup" class="text-slate-400 hover:text-slate-600 p-1.5 text-xl leading-none">✕</button>
        </div>

        <div id="wheel-filters" class="space-y-3 mb-4">
            <label id="wheel-avoid-last-wrap" class="hidden items-center justify-between gap-2 p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700">
                <span>Hindari tenant kemarin</span>
                <input type="checkbox" id="wheel-avoid-last" data-testid="wheel-avoid-last" class="w-4 h-4">
            </label>

            <div id="wheel-tenant-filter-wrap" class="hidden">
                <label class="block text-xs font-semibold text-slate-700 mb-1">Tenant</label>
                <select id="wheel-tenant-filter" data-testid="wheel-tenant-filter" class="w-full px-3 py-2 text-sm rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                    <option value="">Semua</option>
                </select>
            </div>

            <div id="wheel-max-price-wrap" class="hidden">
                <label class="block text-xs font-semibold text-slate-700 mb-1">Harga Maksimum (Opsional)</label>
                <input type="number" id="wheel-max-price" data-testid="wheel-max-price" min="0" step="1000" placeholder="Tanpa batas" class="w-full px-3 py-2 text-sm rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none">
            </div>

            <label id="wheel-main-only-wrap" class="hidden items-center justify-between gap-2 p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700">
                <span>Makanan berat saja</span>
                <input type="checkbox" id="wheel-main-only" data-testid="wheel-main-only" class="w-4 h-4" checked>
            </label>

            <p id="wheel-avoid-last-info" class="hidden text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-2.5 py-2"></p>
        </div>

        <div id="wheel-error" data-testid="wheel-error" class="hidden text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl px-3 py-2 mb-3"></div>

        <div id="wheel-canvas-wrap" class="relative flex items-center justify-center py-2">
            <div class="absolute -top-1 left-1/2 -translate-x-1/2 z-10 text-2xl leading-none">🔻</div>
            <svg id="wheel-svg" data-testid="wheel-svg" viewBox="0 0 300 300" class="w-64 h-64 sm:w-72 sm:h-72"></svg>
        </div>

        <div id="wheel-candidate-list" class="mt-3 max-h-36 overflow-y-auto space-y-1 border border-slate-100 rounded-xl p-2"></div>

        <button type="button" id="wheel-spin" data-testid="wheel-spin" class="w-full mt-4 py-3 bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] text-white font-bold rounded-xl text-sm transition shadow-md disabled:bg-slate-300 disabled:cursor-not-allowed disabled:active:scale-100">
            🎯 Putar!
        </button>
        <p id="wheel-spin-hint" class="hidden text-[11px] text-rose-600 mt-1.5 text-center"></p>

        <div id="wheel-result" data-testid="wheel-result" class="hidden mt-4 p-4 bg-indigo-50 border border-indigo-200 rounded-2xl text-center" role="region" aria-live="polite">
            <p class="text-[11px] font-bold text-indigo-600 uppercase tracking-wider">Pemenang</p>
            <p id="wheel-result-label" class="text-lg font-extrabold text-slate-800 mt-0.5"></p>
            <p id="wheel-result-detail" class="text-xs text-slate-500 mt-0.5"></p>
            <div class="flex gap-2 mt-3">
                <button type="button" id="wheel-respin" data-testid="wheel-respin" class="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition">🔁 Putar Lagi</button>
                <button type="button" id="wheel-apply" data-testid="wheel-apply" class="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl transition">✅ Pakai Hasil Ini</button>
            </div>
        </div>
    </div>
</div>
```

- [ ] **Step 2: Create the `wheel.js` module**

Create `src/titip_makan/static/js/wheel.js`:

```js
(function () {
    const PALETTE = ["#4f46e5", "#7c3aed", "#059669", "#d97706", "#e11d48", "#0284c7"];
    const MAX_LABELED_SLICES = 16;
    const SPIN_DURATION_MS = 4000;

    let state = null;

    function qs(id) {
        return document.getElementById(id);
    }

    function secureRandomInt(maxExclusive) {
        if (maxExclusive <= 0) return 0;
        const range = 0x100000000;
        const limit = range - (range % maxExclusive);
        const buf = new Uint32Array(1);
        let x;
        do {
            crypto.getRandomValues(buf);
            x = buf[0];
        } while (x >= limit);
        return x % maxExclusive;
    }

    function normalizeMod360(deg) {
        return ((deg % 360) + 360) % 360;
    }

    function computeTargetRotation(currentRotationDeg, winnerIndex, sliceCount) {
        const sliceAngle = 360 / sliceCount;
        const sliceCenter = winnerIndex * sliceAngle + sliceAngle / 2;
        const currentModNorm = normalizeMod360(currentRotationDeg);
        const desiredMod = normalizeMod360(360 - sliceCenter);
        let delta = desiredMod - currentModNorm;
        if (delta < 0) delta += 360;
        return currentRotationDeg + 5 * 360 + delta;
    }

    function prefersReducedMotion() {
        return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    function debounce(fn, delay) {
        let timer = null;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function resetState(mode, onApply, triggerEl) {
        state = {
            mode,
            onApply,
            triggerEl,
            allCandidates: [],
            vendors: [],
            excludedLabels: new Set(),
            rotationDeg: 0,
            spinning: false,
            winner: null,
            fetchController: null,
        };
    }

    function activeCandidates() {
        if (!state) return [];
        return state.allCandidates.filter((c) => !state.excludedLabels.has(c.label));
    }

    function setError(message) {
        const el = qs("wheel-error");
        if (!message) {
            el.classList.add("hidden");
            el.innerText = "";
            return;
        }
        el.innerText = message;
        el.classList.remove("hidden");
    }

    function showWheelUi(visible) {
        qs("wheel-canvas-wrap").classList.toggle("hidden", !visible);
        qs("wheel-candidate-list").classList.toggle("hidden", !visible);
        qs("wheel-spin").classList.toggle("hidden", !visible);
    }

    function updateSpinButtonState() {
        const btn = qs("wheel-spin");
        const hint = qs("wheel-spin-hint");
        const count = activeCandidates().length;
        const disabled = state.spinning || count < 2;
        btn.disabled = disabled;
        if (count < 2 && !state.spinning) {
            hint.innerText = "Minimal 2 pilihan untuk diputar";
            hint.classList.remove("hidden");
        } else {
            hint.classList.add("hidden");
        }
    }

    function renderCandidateList() {
        const container = qs("wheel-candidate-list");
        container.innerHTML = "";
        state.allCandidates.forEach((candidate) => {
            const row = document.createElement("label");
            row.className = "flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-50 text-xs text-slate-700 cursor-pointer";

            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "w-3.5 h-3.5";
            checkbox.setAttribute("data-testid", "wheel-candidate");
            checkbox.checked = !state.excludedLabels.has(candidate.label);
            checkbox.addEventListener("change", () => {
                if (checkbox.checked) {
                    state.excludedLabels.delete(candidate.label);
                } else {
                    state.excludedLabels.add(candidate.label);
                }
                renderWheel();
                updateSpinButtonState();
            });

            const text = document.createElement("span");
            let label = candidate.label;
            if (state.mode === "item") {
                const priceText = candidate.price != null ? `Rp ${candidate.price.toLocaleString("id-ID")}` : "";
                label = `${candidate.label} — ${candidate.vendor}${priceText ? " (" + priceText + ")" : ""}`;
            }
            text.innerText = label;

            row.appendChild(checkbox);
            row.appendChild(text);
            container.appendChild(row);
        });
    }

    function polarPoint(cx, cy, r, angleDeg) {
        const rad = (angleDeg * Math.PI) / 180;
        return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
    }

    function renderWheel() {
        const svg = qs("wheel-svg");
        const candidates = activeCandidates();
        svg.innerHTML = "";
        if (candidates.length === 0) return;

        const cx = 150, cy = 150, r = 140;
        const n = candidates.length;
        const sliceAngle = 360 / n;
        const showLabels = n <= MAX_LABELED_SLICES;

        candidates.forEach((candidate, i) => {
            const startDeg = -90 + i * sliceAngle;
            const endDeg = -90 + (i + 1) * sliceAngle;
            const p1 = polarPoint(cx, cy, r, startDeg);
            const p2 = polarPoint(cx, cy, r, endDeg);
            const largeArc = sliceAngle > 180 ? 1 : 0;

            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", `M ${cx},${cy} L ${p1.x},${p1.y} A ${r},${r} 0 ${largeArc} 1 ${p2.x},${p2.y} Z`);
            path.setAttribute("fill", PALETTE[i % PALETTE.length]);
            path.setAttribute("stroke", "#ffffff");
            path.setAttribute("stroke-width", "1.5");
            svg.appendChild(path);

            if (showLabels) {
                const midDeg = startDeg + sliceAngle / 2;
                const labelPoint = polarPoint(cx, cy, r * 0.62, midDeg);
                const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
                text.setAttribute("x", labelPoint.x);
                text.setAttribute("y", labelPoint.y);
                text.setAttribute("fill", "#ffffff");
                text.setAttribute("font-size", n > 8 ? "7" : "9");
                text.setAttribute("font-weight", "700");
                text.setAttribute("text-anchor", "middle");
                text.setAttribute("dominant-baseline", "middle");
                text.setAttribute("transform", `rotate(${midDeg + 90}, ${labelPoint.x}, ${labelPoint.y})`);
                text.textContent = candidate.label.length > 14 ? candidate.label.slice(0, 13) + "…" : candidate.label;
                svg.appendChild(text);
            }
        });
    }

    function applyFilterVisibility() {
        const isTenant = state.mode === "tenant";
        qs("wheel-avoid-last-wrap").classList.toggle("hidden", !isTenant);
        qs("wheel-avoid-last-wrap").classList.toggle("flex", isTenant);
        qs("wheel-tenant-filter-wrap").classList.toggle("hidden", isTenant);
        qs("wheel-max-price-wrap").classList.toggle("hidden", isTenant);
        qs("wheel-main-only-wrap").classList.toggle("hidden", isTenant);
        qs("wheel-main-only-wrap").classList.toggle("flex", !isTenant);
        qs("wheel-modal-heading").innerText = isTenant ? "Roda Pilihan Tenant" : "Roda Pilihan Menu";
    }

    function buildQuery() {
        const params = new URLSearchParams();
        params.set("mode", state.mode);
        if (state.mode === "tenant") {
            params.set("avoid_last", qs("wheel-avoid-last").checked ? "true" : "false");
        } else {
            const tenant = qs("wheel-tenant-filter").value;
            if (tenant) params.set("tenant", tenant);
            const maxPrice = qs("wheel-max-price").value.trim();
            if (maxPrice !== "") params.set("max_price", maxPrice);
            params.set("main_only", qs("wheel-main-only").checked ? "true" : "false");
        }
        return params.toString();
    }

    function renderTenantFilterOptions(vendors) {
        const select = qs("wheel-tenant-filter");
        const current = select.value;
        select.innerHTML = '<option value="">Semua</option>';
        vendors.forEach((v) => {
            const opt = document.createElement("option");
            opt.value = v;
            opt.innerText = v;
            select.appendChild(opt);
        });
        if (vendors.includes(current)) {
            select.value = current;
        }
    }

    function hideResult() {
        qs("wheel-result").classList.add("hidden");
        state.winner = null;
    }

    async function fetchCandidates() {
        if (!state) return;
        setError(null);
        hideResult();
        qs("wheel-avoid-last-info").classList.add("hidden");

        if (state.fetchController) {
            state.fetchController.abort();
        }
        const controller = new AbortController();
        state.fetchController = controller;

        try {
            const resp = await fetch(`/api/v1/wheel/candidates?${buildQuery()}`, { signal: controller.signal });
            if (!resp.ok) {
                let detail = "Gagal memuat pilihan.";
                try {
                    const body = await resp.json();
                    if (body && body.detail) detail = body.detail;
                } catch (e) { /* ignore body parse errors */ }

                if (resp.status === 409) {
                    detail = "Belum ada sesi aktif";
                    showWheelUi(false);
                } else {
                    showWheelUi(true);
                }
                setError(detail);
                state.allCandidates = [];
                renderCandidateList();
                updateSpinButtonState();
                return;
            }

            const data = await resp.json();
            showWheelUi(true);
            state.allCandidates = data.candidates || [];
            state.vendors = data.vendors || [];

            if (state.mode === "item") {
                renderTenantFilterOptions(state.vendors);
            }

            if (state.mode === "tenant" && data.avoid_last_applied && data.excluded_last_tenants && data.excluded_last_tenants.length > 0) {
                const info = qs("wheel-avoid-last-info");
                info.innerText = `Tidak termasuk: ${data.excluded_last_tenants.join(", ")}`;
                info.classList.remove("hidden");
            }

            renderCandidateList();
            renderWheel();
            updateSpinButtonState();
        } catch (err) {
            if (err.name === "AbortError") return;
            console.error("Gagal memuat kandidat wheel:", err);
            setError("Gagal memuat pilihan. Coba lagi.");
            showWheelUi(true);
        }
    }

    const debouncedFetch = debounce(fetchCandidates, 300);

    function showResult(winner) {
        state.winner = winner;
        qs("wheel-result-label").innerText = winner.label;
        if (state.mode === "item") {
            const priceText = winner.price != null ? `Rp ${winner.price.toLocaleString("id-ID")}` : "Harga belum ditentukan";
            qs("wheel-result-detail").innerText = `${winner.vendor} • ${priceText}`;
        } else {
            qs("wheel-result-detail").innerText = "";
        }
        qs("wheel-result").classList.remove("hidden");
    }

    function spin() {
        if (!state || state.spinning) return;
        const candidates = activeCandidates();
        if (candidates.length < 2) return;

        state.spinning = true;
        hideResult();
        updateSpinButtonState();

        const winnerIndex = secureRandomInt(candidates.length);
        const winner = candidates[winnerIndex];
        const target = computeTargetRotation(state.rotationDeg, winnerIndex, candidates.length);

        const svg = qs("wheel-svg");

        function finishSpin() {
            state.rotationDeg = target;
            state.spinning = false;
            updateSpinButtonState();
            showResult(winner);
        }

        if (prefersReducedMotion()) {
            svg.style.transition = "none";
            svg.style.transform = `rotate(${target}deg)`;
            finishSpin();
            return;
        }

        svg.style.transition = `transform ${SPIN_DURATION_MS}ms cubic-bezier(0.12, 0.67, 0.1, 1)`;
        void svg.getBoundingClientRect(); // force reflow so the transition applies
        svg.style.transform = `rotate(${target}deg)`;

        let settled = false;
        const onEnd = () => {
            if (settled) return;
            settled = true;
            svg.removeEventListener("transitionend", onEnd);
            finishSpin();
        };
        svg.addEventListener("transitionend", onEnd);
        setTimeout(onEnd, SPIN_DURATION_MS + 300);
    }

    function closeModal() {
        qs("wheel-modal").classList.add("hidden");
        qs("wheel-modal").classList.remove("flex");
        if (state && state.fetchController) state.fetchController.abort();
        if (state && state.triggerEl && typeof state.triggerEl.focus === "function") {
            state.triggerEl.focus();
        }
    }

    function handleKeydown(e) {
        if (e.key === "Escape" && !qs("wheel-modal").classList.contains("hidden")) {
            closeModal();
        }
    }

    function setupOnce() {
        if (window.__menuWheelSetup) return;
        window.__menuWheelSetup = true;

        qs("wheel-close").addEventListener("click", closeModal);
        qs("wheel-modal").addEventListener("click", (e) => {
            if (e.target.id === "wheel-modal") closeModal();
        });
        document.addEventListener("keydown", handleKeydown);

        qs("wheel-spin").addEventListener("click", spin);
        qs("wheel-respin").addEventListener("click", () => {
            hideResult();
            spin();
        });
        qs("wheel-apply").addEventListener("click", () => {
            if (!state || !state.winner) return;
            const winner = state.winner;
            const callback = state.onApply;
            closeModal();
            if (typeof callback === "function") callback(winner);
        });

        qs("wheel-avoid-last").addEventListener("change", fetchCandidates);
        qs("wheel-tenant-filter").addEventListener("change", fetchCandidates);
        qs("wheel-main-only").addEventListener("change", fetchCandidates);
        qs("wheel-max-price").addEventListener("input", debouncedFetch);
    }

    function open(options) {
        setupOnce();
        const mode = options && options.mode === "item" ? "item" : "tenant";
        const onApply = options && options.onApply;
        const triggerEl = document.activeElement;

        resetState(mode, onApply, triggerEl);

        qs("wheel-avoid-last").checked = false;
        qs("wheel-main-only").checked = true;
        qs("wheel-max-price").value = "";
        qs("wheel-tenant-filter").innerHTML = '<option value="">Semua</option>';
        qs("wheel-avoid-last-info").classList.add("hidden");
        hideResult();
        setError(null);
        showWheelUi(true);

        const svg = qs("wheel-svg");
        svg.style.transition = "none";
        svg.style.transform = "rotate(0deg)";

        applyFilterVisibility();

        const modal = qs("wheel-modal");
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        qs("wheel-close").focus();

        fetchCandidates();
    }

    window.MenuWheel = { open };
})();
```

- [ ] **Step 3: Commit**

```bash
git add src/titip_makan/templates/partials/wheel_modal.html src/titip_makan/static/js/wheel.js
git commit -m "feat: add wheel modal partial and MenuWheel JS module"
```

---

### Task 7: Coordinator page integration (tenant mode)

**Files:**
- Modify: `src/titip_makan/templates/coordinator.html`
- Modify: `src/titip_makan/static/js/coordinator.js`

**Interfaces:**
- Consumes: `window.MenuWheel.open` (Task 6).
- Produces: clicking `#wheel-open-tenant` opens the wheel in tenant mode; applying a result sets `#cs-vendors`.

- [ ] **Step 1: Add the 🎡 button next to `#cs-vendors`**

In `src/titip_makan/templates/coordinator.html`, replace:

```html
                <div>
                    <label class="block text-xs font-semibold text-slate-700 mb-1">Pilihan Vendor / Tenant (Pisahkan koma)</label>
                    <input type="text" id="cs-vendors" value="Mie Ayam, Babun, Nasi Goreng, Dimsum"
                        class="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                </div>
```

with:

```html
                <div>
                    <label class="block text-xs font-semibold text-slate-700 mb-1">Pilihan Vendor / Tenant (Pisahkan koma)</label>
                    <div class="flex items-center gap-2">
                        <input type="text" id="cs-vendors" value="Mie Ayam, Babun, Nasi Goreng, Dimsum"
                            class="flex-1 min-w-0 px-3.5 py-2 text-sm rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                        <button type="button" id="wheel-open-tenant" data-testid="wheel-open-tenant" title="Putar roda tenant"
                            class="flex-none w-9 h-9 flex items-center justify-center bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-xl text-base transition">
                            🎡
                        </button>
                    </div>
                </div>
```

- [ ] **Step 2: Include the modal partial and load `wheel.js` before `coordinator.js`**

In `src/titip_makan/templates/coordinator.html`, add the include right before `{% endblock %}` that closes `{% block content %}` (i.e. immediately after the last `</div>` of the page content, before the `{% endblock %}` on its own line):

```html
{% include "partials/wheel_modal.html" %}
{% endblock %}
```

Then change the scripts block from:

```html
{% block scripts %}
<script src="/static/js/coordinator.js"></script>
{% endblock %}
```

to:

```html
{% block scripts %}
<script src="/static/js/wheel.js"></script>
<script src="/static/js/coordinator.js"></script>
{% endblock %}
```

- [ ] **Step 3: Wire the button in `coordinator.js`**

In `src/titip_makan/static/js/coordinator.js`, inside `setupEventListeners()`, right after the `newSessionBtn` block (after its closing `}` around line 313, before the `// Create session form` comment), add:

```js
    const wheelOpenTenantBtn = document.getElementById("wheel-open-tenant");
    if (wheelOpenTenantBtn) {
        wheelOpenTenantBtn.addEventListener("click", () => {
            window.MenuWheel.open({
                mode: "tenant",
                onApply: (candidate) => {
                    document.getElementById("cs-vendors").value = candidate.label;
                }
            });
        });
    }
```

- [ ] **Step 4: Manual smoke check**

Run: `uv run uvicorn titip_makan.main:app --host 127.0.0.1 --port 8099 &` then `curl -s http://127.0.0.1:8099/coordinator | grep -c 'wheel-open-tenant'` — expect `1` (button rendered). Then `curl -s http://127.0.0.1:8099/static/js/wheel.js | head -c 50` — expect the start of the JS file (confirms static mount serves it). Stop the server afterward (`kill %1` or note the PID to kill).

Expected: both checks succeed, no 404s.

- [ ] **Step 5: Commit**

```bash
git add src/titip_makan/templates/coordinator.html src/titip_makan/static/js/coordinator.js
git commit -m "feat: wire wheel-of-tenant into coordinator page"
```

---

### Task 8: Index page integration (item mode)

**Files:**
- Modify: `src/titip_makan/templates/index.html`
- Modify: `src/titip_makan/static/js/app.js`

**Interfaces:**
- Consumes: `window.MenuWheel.open` (Task 6).
- Produces: `#wheel-open-item` (rendered only when `session` is truthy in the Jinja context — set by `web.py`'s `home_view`, which already passes `session=active_session`) opens the wheel in item mode; applying a result fills `#input-tenant`, `#input-menu`, `#input-price` and dispatches `input`/`change` events on each.

- [ ] **Step 1: Add the session-gated 🎡 button next to `#input-tenant`**

In `src/titip_makan/templates/index.html`, replace:

```html
                    <input type="text" id="input-tenant" list="datalist-tenants" required autocomplete="off"
                        placeholder="Ketik tenant (misal: Mie Ayam, Babun)..."
                        class="w-full px-3.5 py-2.5 text-base sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    <datalist id="datalist-tenants"></datalist>
```

with:

```html
                    <div class="flex items-center gap-2">
                        <input type="text" id="input-tenant" list="datalist-tenants" required autocomplete="off"
                            placeholder="Ketik tenant (misal: Mie Ayam, Babun)..."
                            class="flex-1 min-w-0 px-3.5 py-2.5 text-base sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                        {% if session %}
                        <button type="button" id="wheel-open-item" data-testid="wheel-open-item" title="Putar roda menu"
                            class="flex-none w-11 h-11 sm:w-10 sm:h-10 flex items-center justify-center bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-xl text-lg transition">
                            🎡
                        </button>
                        {% endif %}
                    </div>
                    <datalist id="datalist-tenants"></datalist>
```

- [ ] **Step 2: Include the modal partial and load `wheel.js` before `app.js`**

In `src/titip_makan/templates/index.html`, add the include right before the `{% endblock %}` that closes `{% block content %}` (immediately after the closing `</div>` of `#modal-order`):

```html
{% include "partials/wheel_modal.html" %}
{% endblock %}
```

Then change the scripts block from:

```html
{% block scripts %}
<script src="/static/js/app.js"></script>
{% endblock %}
```

to:

```html
{% block scripts %}
<script src="/static/js/wheel.js"></script>
<script src="/static/js/app.js"></script>
{% endblock %}
```

- [ ] **Step 3: Wire the button in `app.js`**

In `src/titip_makan/static/js/app.js`, inside `setupFormEventListeners()`, right after the `menuInput` listeners (after line 550, before `const form = document.getElementById("order-form");`), add:

```js
    const wheelOpenItemBtn = document.getElementById("wheel-open-item");
    if (wheelOpenItemBtn) {
        wheelOpenItemBtn.addEventListener("click", () => {
            window.MenuWheel.open({
                mode: "item",
                onApply: (candidate) => {
                    const targetTenant = document.getElementById("input-tenant");
                    const targetMenu = document.getElementById("input-menu");
                    const targetPrice = document.getElementById("input-price");

                    targetTenant.value = candidate.vendor;
                    targetMenu.value = candidate.label;
                    targetPrice.value = candidate.price != null ? candidate.price : "";

                    [targetTenant, targetMenu, targetPrice].forEach((el) => {
                        el.dispatchEvent(new Event("input", { bubbles: true }));
                        el.dispatchEvent(new Event("change", { bubbles: true }));
                    });
                }
            });
        });
    }
```

- [ ] **Step 4: Manual smoke check (both pages, both modes)**

Run: `uv run uvicorn titip_makan.main:app --host 127.0.0.1 --port 8099 &`

1. `curl -s http://127.0.0.1:8099/` — since there is no active session by default, confirm `wheel-open-item` is **absent**: `curl -s http://127.0.0.1:8099/ | grep -c 'wheel-open-item'` expect `0`.
2. Create a session: `curl -s -X POST http://127.0.0.1:8099/api/v1/sessions -H 'Content-Type: application/json' -d '{"title":"Smoke Test","coordinator_name":"Zi","vendor_options":["Babun","Mie Ayam"],"cutoff_minutes":30}'`
3. `curl -s http://127.0.0.1:8099/ | grep -c 'wheel-open-item'` — now expect `1`.
4. `curl -s "http://127.0.0.1:8099/api/v1/wheel/candidates?mode=item" | head -c 200` — expect a JSON body with `"mode":"item"` and non-empty `candidates`.

Stop the server afterward.

Expected: all four checks match, confirming the Jinja conditional and the live endpoint work together.

- [ ] **Step 5: Commit**

```bash
git add src/titip_makan/templates/index.html src/titip_makan/static/js/app.js
git commit -m "feat: wire wheel-of-item into index order form"
```

---

### Task 9: E2E tests

**Files:**
- Create: `tests/e2e/test_wheel_e2e.py`

**Interfaces:**
- Consumes: the full stack (Tasks 1–8) through a real, in-process `uvicorn` server (same `live_server` pattern as `tests/e2e/test_responsive_navigation_e2e.py`), driven with Python Playwright.

- [ ] **Step 1: Write the E2E test file**

Create `tests/e2e/test_wheel_e2e.py`:

```python
import socket
import threading
import time
import pytest
from playwright.async_api import async_playwright, expect
from titip_makan.main import app


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    import uvicorn

    port = get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=2)


async def _new_page(browser):
    context = await browser.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
        reduced_motion="reduce",
    )
    page = await context.new_page()
    return context, page


@pytest.mark.asyncio
async def test_coordinator_wheel_tenant_flow_fills_cs_vendors(live_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context, page = await _new_page(browser)

        await page.goto(f"{live_server}/coordinator")
        await page.wait_for_load_state("networkidle")

        create_card = page.locator("#create-session-card")
        if not await create_card.is_visible():
            await page.click("#btn-new-session-toggle")
            await page.wait_for_timeout(200)

        await page.click('[data-testid="wheel-open-tenant"]')
        await expect(page.locator('[data-testid="wheel-modal"]')).to_be_visible()

        await page.click('[data-testid="wheel-spin"]')
        await expect(page.locator('[data-testid="wheel-result"]')).to_be_visible(timeout=3000)

        winner_label = await page.inner_text("#wheel-result-label")
        assert winner_label.strip() != ""

        await page.click('[data-testid="wheel-apply"]')
        await expect(page.locator('[data-testid="wheel-modal"]')).to_be_hidden()

        cs_vendors_value = await page.input_value("#cs-vendors")
        assert cs_vendors_value.strip() == winner_label.strip()

        await context.close()
        await browser.close()


@pytest.mark.asyncio
async def test_index_wheel_item_flow_fills_order_form(live_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Create an active session first via the coordinator page
        setup_context, setup_page = await _new_page(browser)
        await setup_page.goto(f"{live_server}/coordinator")
        await setup_page.wait_for_load_state("networkidle")

        create_card = setup_page.locator("#create-session-card")
        if not await create_card.is_visible():
            await setup_page.click("#btn-new-session-toggle")
            await setup_page.wait_for_timeout(200)

        await setup_page.fill("#cs-title", "Sesi Wheel E2E")
        await setup_page.fill("#cs-coordinator", "Zi")
        await setup_page.fill("#cs-vendors", "Babun, Mie Ayam")
        await setup_page.fill("#cs-cutoff", "45")
        await setup_page.click('#create-session-form button[type="submit"]')
        await expect(setup_page.locator("#coord-session-title")).to_have_text("Sesi Wheel E2E", timeout=5000)
        await setup_context.close()

        # Now drive the member order form
        context, page = await _new_page(browser)
        await page.goto(f"{live_server}/")
        await page.wait_for_load_state("networkidle")

        await page.locator("#btn-mobile-open-order-modal").dispatch_event("click")
        await page.wait_for_timeout(200)

        await page.click('[data-testid="wheel-open-item"]')
        await expect(page.locator('[data-testid="wheel-modal"]')).to_be_visible()

        await page.click('[data-testid="wheel-spin"]')
        await expect(page.locator('[data-testid="wheel-result"]')).to_be_visible(timeout=3000)

        winner_label = (await page.inner_text("#wheel-result-label")).strip()

        await page.click('[data-testid="wheel-apply"]')
        await expect(page.locator('[data-testid="wheel-modal"]')).to_be_hidden()

        menu_value = await page.input_value("#input-menu")
        tenant_value = await page.input_value("#input-tenant")
        price_value = await page.input_value("#input-price")

        assert menu_value.strip() == winner_label
        assert tenant_value.strip() in ("Babun", "Mie Ayam")
        assert price_value.strip() != ""

        await context.close()
        await browser.close()


@pytest.mark.asyncio
async def test_wheel_exclude_manual_disables_spin_below_two_candidates(live_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context, page = await _new_page(browser)

        await page.goto(f"{live_server}/coordinator")
        await page.wait_for_load_state("networkidle")

        create_card = page.locator("#create-session-card")
        if not await create_card.is_visible():
            await page.click("#btn-new-session-toggle")
            await page.wait_for_timeout(200)

        await page.click('[data-testid="wheel-open-tenant"]')
        await expect(page.locator('[data-testid="wheel-modal"]')).to_be_visible()

        checkboxes = page.locator('[data-testid="wheel-candidate"]')
        await expect(checkboxes.first).to_be_visible(timeout=3000)
        count = await checkboxes.count()
        assert count >= 3, "expected the real catalog to have at least 3 tenants"

        # Uncheck all but one, leaving exactly 1 active candidate
        for i in range(count - 1):
            await checkboxes.nth(i).uncheck()

        spin_btn = page.locator('[data-testid="wheel-spin"]')
        await expect(spin_btn).to_be_disabled()

        await context.close()
        await browser.close()
```

- [ ] **Step 2: Run the E2E tests**

Run: `uv run pytest tests/e2e/test_wheel_e2e.py -v`
Expected: PASS (3 tests). If a selector or timing assumption is wrong, fix `wheel.js`/the templates (not the test) unless the test itself contradicts the spec — then fix the test.

- [ ] **Step 3: Run the entire test suite**

Run: `uv run pytest -v`
Expected: PASS, including all pre-existing tests (no regressions) and all new wheel tests.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_wheel_e2e.py
git commit -m "test: add E2E coverage for wheel of menu on coordinator and index pages"
```

---

## Self-Review Notes (for the executor)

- **Spec coverage:** §3.1 → Task 1. §3.2 → Task 1. §3.3 → Tasks 3–4. §3.4 → Task 2. §3.5 → Task 5. §4.1–4.3 → Task 6. §4.4 (coordinator) → Task 7. §4.4 (index) → Task 8. §4.5 (a11y: dialog roles, Esc/backdrop close, focus return, aria-live, keyboard access) → baked into Task 6's markup/JS. §4.6 (`data-testid`s) → all present in Task 6's partial and Tasks 7–8's buttons. §5 (tests) → Tasks 1, 3, 4, 5, 9. §6 (out of scope) → nothing in this plan touches persistence, weighting, new pages/nav, or catalog categories. §7 (risks) → no mitigation code needed beyond the toggles already specced.
- If any step's exact line numbers have drifted (e.g. another commit touched `app.js`/`coordinator.js` first), locate the anchor text quoted in that step rather than trusting the line number.
