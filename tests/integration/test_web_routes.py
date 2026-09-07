import pytest
from httpx import AsyncClient, ASGITransport
from titip_makan.main import app
from titip_makan.core.database import get_db

@pytest.mark.asyncio
async def test_web_routes(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test home view
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Titip Makan" in resp.text

        # 2. Test coordinator view
        resp = await client.get("/coordinator")
        assert resp.status_code == 200
        assert "Dashboard Koordinator" in resp.text

        # 3. Test health check endpoint
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    app.dependency_overrides.clear()
