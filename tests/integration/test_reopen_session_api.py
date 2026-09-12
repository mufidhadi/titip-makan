import pytest
from httpx import AsyncClient, ASGITransport
from titip_makan.main import app
from titip_makan.core.database import get_db

@pytest.mark.asyncio
async def test_api_reopen_closed_session_via_cutoff_endpoint(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a session
        create_payload = {
            "title": "Sesi Makan Siang Reopen Test",
            "coordinator_name": "Irzi",
            "vendor_options": ["Mie Ayam", "Babun"],
            "cutoff_minutes": 15
        }
        res_create = await client.post("/api/v1/sessions", json=create_payload)
        assert res_create.status_code == 201
        session_id = res_create.json()["id"]

        # 2. Close the session
        res_close = await client.post(
            f"/api/v1/sessions/{session_id}/close",
            headers={"X-Coordinator-Pin": "1234"}
        )
        assert res_close.status_code == 200
        assert res_close.json()["status"] == "CLOSED"

        # Check active session is None
        res_active = await client.get("/api/v1/sessions/active")
        assert res_active.json() is None

        # 3. Reopen temporarily with +5 minutes via cutoff endpoint
        res_cutoff = await client.patch(
            f"/api/v1/sessions/{session_id}/cutoff",
            headers={"X-Coordinator-Pin": "1234"},
            json={"extend_minutes": 5}
        )
        assert res_cutoff.status_code == 200
        data_cutoff = res_cutoff.json()
        assert data_cutoff["status"] == "OPEN"
        assert data_cutoff["closed_at"] is None

        # Check active session is active again
        res_active_again = await client.get("/api/v1/sessions/active")
        assert res_active_again.json()["id"] == session_id
        assert res_active_again.json()["status"] == "OPEN"

        # 4. An order can now be placed
        order_payload = {
            "user_name": "Doni",
            "vendor": "Mie Ayam",
            "item_name": "Mie Pangsit",
            "price": 18000
        }
        res_order = await client.post(f"/api/v1/sessions/{session_id}/orders", json=order_payload)
        assert res_order.status_code == 201
        assert res_order.json()["user_name"] == "Doni"

        # 5. Close again and test dedicated POST /{id}/reopen endpoint with +10 minutes
        await client.post(f"/api/v1/sessions/{session_id}/close", headers={"X-Coordinator-Pin": "1234"})
        res_reopen = await client.post(
            f"/api/v1/sessions/{session_id}/reopen?minutes=10",
            headers={"X-Coordinator-Pin": "1234"}
        )
        assert res_reopen.status_code == 200
        assert res_reopen.json()["status"] == "OPEN"
        assert res_reopen.json()["closed_at"] is None

