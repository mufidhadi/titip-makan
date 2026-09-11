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
