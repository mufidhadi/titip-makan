import random
from datetime import datetime, timedelta, timezone

import pytest

from titip_makan.schemas.auto_order import AutoOrderPreferenceIn
from titip_makan.schemas.order import OrderCreate
from titip_makan.schemas.session import SessionCreate
from titip_makan.services.auto_order_service import AutoOrderService
from titip_makan.services.order_service import OrderService
from titip_makan.services.scheduler_service import SchedulerService
from titip_makan.services.session_service import SessionService

WIB = timezone(timedelta(hours=7))
MIE = {"vendor": "Mie Ayam", "item_name": "Mie Ayam Polos", "price": 1}
GADO = {"vendor": "Kantin", "item_name": "Gado-gado", "price": 1}


async def _open_session(db):
    return await SessionService(db, notifier=None).create_session(
        SessionCreate(title="Sesi Hari Ini", coordinator_name="Irzi", cutoff_minutes=30)
    )


async def test_preference_defaults_then_upsert_case_insensitive(db_session):
    service = AutoOrderService(db_session)

    empty = await service.get_preference("Amal")
    assert empty.enabled is False and empty.candidates == []

    await service.save_preference(AutoOrderPreferenceIn(user_name="Amal", enabled=True, candidates=[MIE]))
    saved = await service.save_preference(
        AutoOrderPreferenceIn(user_name=" amal ", enabled=True, candidates=[MIE, GADO])
    )

    assert saved.user_name == "Amal"
    assert [c.item_name for c in saved.candidates] == ["Mie Ayam Polos", "Gado-gado"]
    assert (await service.get_preference("AMAL")).candidates == saved.candidates


def test_enabled_without_candidates_is_rejected():
    with pytest.raises(ValueError):
        AutoOrderPreferenceIn(user_name="Amal", enabled=True, candidates=[])


async def test_places_one_random_order_per_enabled_user_once_per_session(db_session):
    session = await _open_session(db_session)
    service = AutoOrderService(db_session, rng=random.Random(1))
    await service.save_preference(AutoOrderPreferenceIn(user_name="Amal", enabled=True, candidates=[MIE, GADO]))
    await service.save_preference(AutoOrderPreferenceIn(user_name="Shazi", enabled=False, candidates=[MIE]))

    placed = await service.place_orders_for_active_session()
    again = await service.place_orders_for_active_session()

    assert [o.user_name for o in placed] == ["Amal"]
    assert again == []
    order = placed[0]
    assert order.session_id == session.id
    assert order.item_name in {"Mie Ayam Polos", "Gado-gado"}
    # Price comes from the master catalog, not the stale client-sent value
    assert order.price in {15000, 20000}
    assert "auto random" in order.notes


async def test_skips_user_who_already_ordered_and_does_not_readd_after_cancel(db_session):
    session = await _open_session(db_session)
    await OrderService(db_session).create_order(
        session.id, OrderCreate(user_name="amal", vendor="Babun", item_name="Babun Urap")
    )
    service = AutoOrderService(db_session)
    await service.save_preference(AutoOrderPreferenceIn(user_name="Amal", enabled=True, candidates=[MIE]))

    assert await service.place_orders_for_active_session() == []

    orders = await OrderService(db_session).get_orders_by_session(session.id)
    await OrderService(db_session).delete_order(orders[0].id)
    assert await service.place_orders_for_active_session() == []


async def test_no_active_session_places_nothing(db_session):
    service = AutoOrderService(db_session)
    await service.save_preference(AutoOrderPreferenceIn(user_name="Amal", enabled=True, candidates=[MIE]))
    assert await service.place_orders_for_active_session() == []


async def test_scheduler_places_auto_orders_only_on_weekdays(db_session):
    await _open_session(db_session)
    await AutoOrderService(db_session).save_preference(
        AutoOrderPreferenceIn(user_name="Amal", enabled=True, candidates=[MIE])
    )
    scheduler = SchedulerService(db_session_factory=lambda: db_session)

    saturday = datetime(2026, 9, 12, 10, 5, tzinfo=WIB)
    assert await scheduler.check_and_place_auto_orders(now_wib=saturday) == []

    friday = datetime(2026, 9, 11, 10, 5, tzinfo=WIB)
    placed = await scheduler.check_and_place_auto_orders(now_wib=friday)
    assert [o.user_name for o in placed] == ["Amal"]
