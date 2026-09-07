import pytest
from datetime import datetime, timedelta, timezone
from titip_makan.services.session_service import SessionService
from titip_makan.services.order_service import OrderService
from titip_makan.schemas.session import SessionCreate
from titip_makan.schemas.order import OrderCreate

@pytest.mark.asyncio
async def test_create_order_atomic(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(
            title="Titip Makan 7/09/2026",
            coordinator_name="Zi",
            vendor_options=["Mie Ayam", "Babun"],
            payment_info="BCA 1234567 a.n. Zi",
            cutoff_minutes=60
        )
    )

    # Amal orders Mie Ayam Pangsit Rebus
    order1 = await order_service.create_order(
        session.id,
        OrderCreate(
            user_name="Amal",
            vendor="Mie Ayam",
            item_name="Mie Ayam",
            variant="Pangsit Rebus",
            notes="tanpa daun bawang",
            price=15000
        )
    )

    # Shazi orders Babun Nasi Ayam Lada Hitam
    order2 = await order_service.create_order(
        session.id,
        OrderCreate(
            user_name="Shazi",
            vendor="Babun",
            item_name="Babun Nasi Ayam",
            variant="Lada Hitam",
            notes="pedas manis",
            price=20000
        )
    )

    orders = await order_service.get_orders_by_session(session.id)
    assert len(orders) == 2
    assert orders[0].user_name == "Amal"
    assert orders[1].user_name == "Shazi"

@pytest.mark.asyncio
async def test_order_aggregation_summary(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(
            title="Titip Makan 7/09/2026",
            coordinator_name="Zi",
            vendor_options=["Mie Ayam", "Babun"],
            payment_info="BCA 1234567 a.n. Zi",
            cutoff_minutes=60
        )
    )

    # Add multiple orders
    await order_service.create_order(
        session.id,
        OrderCreate(user_name="Amal", vendor="Mie Ayam", item_name="Mie Ayam", variant="Pangsit Rebus", price=15000)
    )
    await order_service.create_order(
        session.id,
        OrderCreate(user_name="Mufid", vendor="Mie Ayam", item_name="Mie Ayam", variant="Pangsit Rebus", price=15000)
    )
    await order_service.create_order(
        session.id,
        OrderCreate(user_name="Jordan", vendor="Mie Ayam", item_name="Mie Ayam", variant="Pangsit Goreng", price=15000)
    )
    await order_service.create_order(
        session.id,
        OrderCreate(user_name="Shazi", vendor="Babun", item_name="Babun Nasi Ayam", variant="Lada Hitam", price=22000)
    )

    summary = await order_service.get_session_summary(session.id)
    assert summary.total_orders == 4
    assert summary.total_amount == 67000
    
    # Check item aggregation: "Mie Ayam" should be 3 total
    mie_ayam_item = next(i for i in summary.aggregated_items if i.item_name == "Mie Ayam")
    assert mie_ayam_item.quantity == 3

    # Check WA formatted text recap generation
    assert "Rekap Titip Makan" in summary.whatsapp_recap_text
    assert "Mie Ayam" in summary.whatsapp_recap_text

@pytest.mark.asyncio
async def test_order_cutoff_expiration(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(
            title="Titip Makan Cepat",
            coordinator_name="Zi",
            vendor_options=["Mie Ayam"],
            payment_info="BCA 1234567 a.n. Zi",
            cutoff_minutes=-1  # In the past
        )
    )

    with pytest.raises(ValueError, match="order deadline has passed"):
        await order_service.create_order(
            session.id,
            OrderCreate(user_name="Bilal", vendor="Mie Ayam", item_name="Mie Ayam", variant="Polos")
        )

@pytest.mark.asyncio
async def test_delete_order(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(
            title="Titip Makan Siang",
            coordinator_name="Zi",
            vendor_options=["Mie Ayam"]
        )
    )

    order = await order_service.create_order(
        session.id,
        OrderCreate(user_name="Bilal", vendor="Mie Ayam", item_name="Mie Ayam")
    )

    deleted = await order_service.delete_order(order.id)
    assert deleted is True

    orders = await order_service.get_orders_by_session(session.id)
    assert len(orders) == 0

@pytest.mark.asyncio
async def test_custom_tenant_and_variant_order(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(
            title="Titip Makan Fleksibel",
            coordinator_name="Zi",
            vendor_options=["Mie Ayam", "Babun"],
            cutoff_minutes=60
        )
    )

    # Order with custom tenant not in vendor_options, and custom variant
    order = await order_service.create_order(
        session.id,
        OrderCreate(
            user_name="Mufid",
            vendor="Sate Khas Senayan",  # Custom vendor
            item_name="Sate Kambing Campur",  # Custom item
            variant="Bumbu Kacang + Lontong",  # Custom variant
            notes="bawang goreng banyakin",
            price=45000
        )
    )

    assert order.vendor == "Sate Khas Senayan"
    assert order.variant == "Bumbu Kacang + Lontong"

    summary = await order_service.get_session_summary(session.id)
    assert summary.total_orders == 1
    assert summary.total_amount == 45000
    assert any(i.vendor == "Sate Khas Senayan" and i.item_name == "Sate Kambing Campur" for i in summary.aggregated_items)
    assert "Sate Khas Senayan" in summary.whatsapp_recap_text
    assert "bawang goreng banyakin" in summary.whatsapp_recap_text

@pytest.mark.asyncio
async def test_optional_order_price_and_coordinator_update(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(
            title="Titip Makan Santai",
            coordinator_name="Zi",
            vendor_options=["Mie Ayam"],
            cutoff_minutes=60
        )
    )

    # Member orders without specifying price (default 0)
    order = await order_service.create_order(
        session.id,
        OrderCreate(
            user_name="Amal",
            vendor="Mie Ayam",
            item_name="Mie Ayam Spesial",
            price=0
        )
    )
    assert order.price == 0

    # Coordinator fills/updates the price
    updated = await order_service.update_order_price(order.id, 18000)
    assert updated.price == 18000

    summary = await order_service.get_session_summary(session.id)
    assert summary.total_amount == 18000

@pytest.mark.asyncio
async def test_get_suggestions_includes_newly_ordered_tenants_and_menus(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(
            title="Titip Makan Fleksibel",
            coordinator_name="Zi",
            vendor_options=["Mie Ayam"],
            cutoff_minutes=60
        )
    )

    # Order from brand new tenant
    await order_service.create_order(
        session.id,
        OrderCreate(
            user_name="Adrian",
            vendor="Kue Balok Kang Ismet",
            item_name="Kue Balok Coklat Lumer",
            variant="Setengah Matang",
            price=25000
        )
    )

    suggestions = await order_service.get_suggestions(session.id)
    assert "Kue Balok Kang Ismet" in suggestions["tenants"]
    assert "Kue Balok Coklat Lumer" in suggestions["menus"]["Kue Balok Kang Ismet"]

@pytest.mark.asyncio
async def test_order_without_variant_and_clean_aggregation(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)

    session = await session_service.create_session(
        SessionCreate(
            title="Titip Makan Siang",
            coordinator_name="Zi",
            vendor_options=["Mie Ayam"],
            cutoff_minutes=60
        )
    )

    # Order without any variant
    await order_service.create_order(
        session.id,
        OrderCreate(
            user_name="Amal",
            vendor="Mie Ayam",
            item_name="Mie Ayam Spesial",
            notes="tanpa sawi",
            price=18000
        )
    )
    await order_service.create_order(
        session.id,
        OrderCreate(
            user_name="Mufid",
            vendor="Mie Ayam",
            item_name="Mie Ayam Spesial",
            notes="kuah banyak",
            price=18000
        )
    )

    summary = await order_service.get_session_summary(session.id)
    assert summary.total_orders == 2
    assert summary.total_amount == 36000
    item = next(i for i in summary.aggregated_items if i.item_name == "Mie Ayam Spesial")
    assert item.quantity == 2
    assert "2x [Mie Ayam] Mie Ayam Spesial - Rp 36.000" in summary.whatsapp_recap_text




