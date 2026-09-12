import pytest
from httpx import AsyncClient, ASGITransport
from titip_makan.main import app
from titip_makan.core.database import get_db

@pytest.mark.asyncio
async def test_e2e_full_lifecycle_and_bug_fixes(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Check latest session when empty
        resp = await client.get("/api/v1/sessions/latest")
        assert resp.status_code == 200
        assert resp.json() is None

        # 2. Coordinator creates session with cutoff_minutes=30
        create_payload = {
            "title": "Titip Makan Siang 7/09/2026",
            "coordinator_name": "Zi",
            "vendor_options": ["Mie Ayam", "Babun"],
            "payment_info": "BCA 1234567 a.n. Zi",
            "cutoff_minutes": 30
        }
        resp = await client.post("/api/v1/sessions", json=create_payload)
        assert resp.status_code == 201
        session_data = resp.json()
        session_id = session_data["id"]
        
        # Verify ISO 8601 UTC timestamp ends with Z or has UTC offset
        assert session_data["cutoff_at"].endswith("Z") or "+00:00" in session_data["cutoff_at"]

        # 3. Member submits order
        order_resp = await client.post(
            f"/api/v1/sessions/{session_id}/orders",
            json={
                "user_name": "Amal",
                "vendor": "Mie Ayam",
                "item_name": "Mie Ayam",
                "variant": "Pangsit Rebus",
                "price": 15000
            }
        )
        assert order_resp.status_code == 201
        order_amal = order_resp.json()

        # 4. Another member submits custom tenant and custom variant
        order_resp_2 = await client.post(
            f"/api/v1/sessions/{session_id}/orders",
            json={
                "user_name": "Adrian",
                "vendor": "Kantin Mbok Darmi",
                "item_name": "Nasi Rawon",
                "variant": "Daging Dobel",
                "price": 30000
            }
        )
        assert order_resp_2.status_code == 201
        order_adrian = order_resp_2.json()

        # 5. Member self-cancels order
        del_resp = await client.delete(f"/api/v1/orders/{order_adrian['id']}")
        assert del_resp.status_code == 200

        orders_list = (await client.get(f"/api/v1/sessions/{session_id}/orders")).json()
        assert len(orders_list) == 1
        assert orders_list[0]["id"] == order_amal["id"]

        # 6. Coordinator closes session
        close_resp = await client.post(
            f"/api/v1/sessions/{session_id}/close",
            headers={"X-Coordinator-Pin": "1234"}
        )
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "CLOSED"

        # 7. CRITICAL FIX: After session is CLOSED, latest session MUST still return it!
        latest_resp = await client.get("/api/v1/sessions/latest")
        assert latest_resp.status_code == 200
        assert latest_resp.json() is not None
        assert latest_resp.json()["id"] == session_id
        assert latest_resp.json()["status"] == "CLOSED"

        # 8. Coordinator can still get summary of closed session
        summary_resp = await client.get(f"/api/v1/sessions/{session_id}/summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert summary["total_orders"] == 1
        # Check Indonesian thousand separator formatting
        assert "Rp 15.000" in summary["whatsapp_recap_text"]

        # 9. Coordinator creates a second session -> auto closes old ones
        create_payload_2 = {
            "title": "Titip Makan Sore",
            "coordinator_name": "Zi",
            "vendor_options": ["Dimsum"],
            "cutoff_minutes": 20
        }
        resp2 = await client.post("/api/v1/sessions", json=create_payload_2)
        assert resp2.status_code == 201
        session_2 = resp2.json()

        active_resp = await client.get("/api/v1/sessions/active")
        assert active_resp.json()["id"] == session_2["id"]

    app.dependency_overrides.clear()
