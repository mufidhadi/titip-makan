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
async def test_auto_order_preference_roundtrip(db_session):
    async with await _client(db_session) as client:
        resp = await client.get("/api/v1/auto-order", params={"user_name": "Rayhan"})
        assert resp.status_code == 200
        assert resp.json() == {"user_name": "Rayhan", "enabled": False, "candidates": []}

        payload = {
            "user_name": "Rayhan",
            "enabled": True,
            "candidates": [{"vendor": "Mie Ayam", "item_name": "Mie Ayam Polos", "price": 15000}],
        }
        resp = await client.put("/api/v1/auto-order", json=payload)
        assert resp.status_code == 200
        assert resp.json() == payload

        resp = await client.get("/api/v1/auto-order", params={"user_name": "rayhan"})
        assert resp.json() == payload


@pytest.mark.asyncio
async def test_auto_order_rejects_enabled_without_candidates(db_session):
    async with await _client(db_session) as client:
        resp = await client.put(
            "/api/v1/auto-order", json={"user_name": "Rayhan", "enabled": True, "candidates": []}
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_auto_order_rejects_blank_user_name(db_session):
    async with await _client(db_session) as client:
        resp = await client.put("/api/v1/auto-order", json={"user_name": "   ", "enabled": False})
        assert resp.status_code == 422
