import pytest
from datetime import timezone, timedelta
from titip_makan.services.session_service import SessionService
from titip_makan.services.order_service import OrderService
from titip_makan.services.analytics_service import AnalyticsService
from titip_makan.schemas.session import SessionCreate
from titip_makan.schemas.order import OrderCreate

WIB = timezone(timedelta(hours=7))

@pytest.mark.asyncio
async def test_analytics_and_leaderboard_empty(db_session):
    analytics_service = AnalyticsService(db_session)
    overview = await analytics_service.get_overview()
    assert overview.total_sessions == 0
    assert overview.total_orders == 0
    assert overview.total_spend == 0
    assert overview.unique_users == 0

    leaderboard = await analytics_service.get_leaderboard()
    assert len(leaderboard.rankings) == 0
    assert len(leaderboard.badges_summary) == 6
    for b in leaderboard.badges_summary:
        assert b.holder is None

@pytest.mark.asyncio
async def test_analytics_and_leaderboard_with_data(db_session):
    session_service = SessionService(db_session)
    order_service = OrderService(db_session)
    analytics_service = AnalyticsService(db_session)

    # Create session
    session = await session_service.create_session(
        SessionCreate(title="Sesi Analytics", coordinator_name="Irzi", cutoff_minutes=60)
    )

    # User A: 3 orders, 60,000 total, 2 with custom notes, 2 unique menus
    await order_service.create_order(session.id, OrderCreate(
        user_name="Alice", vendor="Kantin", item_name="Nasi Goreng", price=20000, notes="Pedas level 5"
    ))
    await order_service.create_order(session.id, OrderCreate(
        user_name="Alice", vendor="Kantin", item_name="Nasi Goreng", price=20000, notes="Gak pake acar"
    ))
    await order_service.create_order(session.id, OrderCreate(
        user_name="Alice", vendor="Mie Ayam", item_name="Mie Ayam Bakso", price=20000, notes=""
    ))

    # User B: 1 order, 85,000 total, 0 notes, 1 unique menu
    await order_service.create_order(session.id, OrderCreate(
        user_name="Bob", vendor="Steakhouse", item_name="Sirloin Steak", price=85000, notes=""
    ))

    # User C: 4 orders, 40,000 total, 0 notes, 1 unique menu (all Es Teh)
    for _ in range(4):
        await order_service.create_order(session.id, OrderCreate(
            user_name="Charlie", vendor="Kantin", item_name="Es Teh Manis", price=10000, notes=""
        ))

    # 1. Test Overview
    overview = await analytics_service.get_overview()
    assert overview.total_sessions == 1
    assert overview.total_orders == 8  # 3 + 1 + 4
    assert overview.total_spend == 185000  # 60000 + 85000 + 40000
    assert overview.unique_users == 3
    assert abs(overview.average_order_price - (185000 / 8)) < 1

    # Top menus
    assert overview.top_menus[0].name == "Es Teh Manis"
    assert overview.top_menus[0].count == 4

    # Top vendors
    assert overview.top_vendors[0].name == "Kantin"

    # 2. Test Leaderboard & Badges
    lb = await analytics_service.get_leaderboard()
    assert len(lb.rankings) == 3

    # Ranking by total_spend: Bob (85k), Alice (60k), Charlie (40k)
    assert lb.rankings[0].user_name == "Bob"
    assert lb.rankings[0].total_spend == 85000
    assert lb.rankings[1].user_name == "Alice"
    assert lb.rankings[1].total_spend == 60000
    assert lb.rankings[2].user_name == "Charlie"
    assert lb.rankings[2].total_spend == 40000

    # Badges check
    badges_map = {b.code: b.holder for b in lb.badges_summary}
    # Sultan Titip Makan: Bob (85,000)
    assert badges_map["sultan"] == "Bob"
    # Si Paling Rajin Titip: Charlie (4 orders)
    assert badges_map["rajin"] == "Charlie"
    # Raja Catatan / Si Paling Custom: Alice (2 notes)
    assert badges_map["catatan"] == "Alice"
    # Ninja Lapar: Bob (1 order)
    assert badges_map["ninja"] == "Bob"
    # Penganut Setia: Charlie (1 unique menu out of 4 orders)
    assert badges_map["setia"] == "Charlie"
    # Eksplorator Kuliner: Alice (2 unique menus)
    assert badges_map["eksplorator"] == "Alice"

    # Check badges list on rankings
    bob_entry = next(r for r in lb.rankings if r.user_name == "Bob")
    assert any("Sultan" in badge for badge in bob_entry.badges)
