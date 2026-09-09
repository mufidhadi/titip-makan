import pytest
from httpx import AsyncClient, ASGITransport
from titip_makan.main import app
from titip_makan.core.database import get_db

@pytest.mark.asyncio
async def test_responsive_navigation_elements_in_all_routes(db_session):
    """
    TDD Test: Verify that all rendered HTML pages include:
    1. A responsive mobile hamburger toggle button (#mobile-menu-btn).
    2. A collapsible mobile navigation container (#mobile-menu) hidden on md screens.
    3. Desktop navigation hidden on mobile (hidden md:flex).
    4. Links to all core sections: /, /history, /leaderboard, /coordinator.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        routes_to_test = ["/", "/history", "/leaderboard", "/coordinator"]

        for route in routes_to_test:
            resp = await client.get(route)
            assert resp.status_code == 200, f"Failed loading {route}"
            html = resp.text

            # Mobile hamburger button assertions
            assert 'id="mobile-menu-btn"' in html, f"Missing #mobile-menu-btn on {route}"
            assert 'id="mobile-menu"' in html, f"Missing #mobile-menu on {route}"
            assert 'id="menu-icon-bars"' in html, f"Missing #menu-icon-bars on {route}"
            assert 'id="menu-icon-close"' in html, f"Missing #menu-icon-close on {route}"

            # Desktop navigation container assertions
            assert 'hidden md:flex' in html, f"Desktop nav should be hidden on mobile (hidden md:flex) on {route}"

            # Navigation links assertions
            assert 'href="/"' in html, f"Missing home link on {route}"
            assert 'href="/history"' in html, f"Missing history link on {route}"
            assert 'href="/leaderboard"' in html, f"Missing leaderboard link on {route}"
            assert 'href="/coordinator"' in html, f"Missing coordinator link on {route}"

    app.dependency_overrides.clear()
