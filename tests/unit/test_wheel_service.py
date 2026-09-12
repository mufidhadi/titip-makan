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
    # Sesi dengan cutoff di masa depan harus DIABAIKAN (belum selesai)
    assert result.id != open_future_cutoff.id


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
        SessionCreate(title="Sesi Lewat Cutoff", coordinator_name="Zi", cutoff_minutes=30)
    )
    await order_service.create_order(
        session.id, OrderCreate(user_name="Amal", vendor="Babun", item_name="Item", price=10000)
    )
    # Push cutoff into the past directly via the repository (bypassing order_service's
    # lazy-close-on-write path) so the session stays "OPEN" in the DB with an expired cutoff.
    past_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    await SessionRepository(db_session).update_cutoff(session.id, past_cutoff)

    service = WheelService(db_session)
    result = await service.get_tenant_candidates(avoid_last=True)

    assert result.avoid_last_applied is True
    assert result.excluded_last_tenants == ["Babun"]


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
