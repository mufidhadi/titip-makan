import pytest
from httpx import AsyncClient, ASGITransport
from titip_makan.main import app
from titip_makan.core.database import get_db

@pytest.mark.asyncio
async def test_full_titip_makan_api_lifecycle(db_session):
    # Override get_db dependency to use the isolated test database
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Initially, no active session
        resp = await client.get("/api/v1/sessions/active")
        assert resp.status_code == 200
        assert resp.json() is None

        # 2. Coordinator creates a session
        create_payload = {
            "title": "Titip Makan Siang 7/09/2026",
            "coordinator_name": "Zi",
            "vendor_options": ["Mie Ayam", "Babun"],
            "payment_info": "BCA 1234567 a.n. Zi",
            "cutoff_minutes": 45
        }
        resp = await client.post("/api/v1/sessions", json=create_payload)
        assert resp.status_code == 201
        session_data = resp.json()
        session_id = session_data["id"]
        assert session_data["status"] == "OPEN"

        # 3. User submits an order (atomic)
        order_payload_1 = {
            "user_name": "Amal",
            "vendor": "Mie Ayam",
            "item_name": "Mie Ayam",
            "variant": "Pangsit Rebus",
            "notes": "jangan pedas",
            "price": 15000
        }
        resp = await client.post(f"/api/v1/sessions/{session_id}/orders", json=order_payload_1)
        assert resp.status_code == 201
        order_1 = resp.json()
        assert order_1["user_name"] == "Amal"
        assert order_1["is_paid"] is False

        # 4. Another user submits an order
        order_payload_2 = {
            "user_name": "Shazi",
            "vendor": "Babun",
            "item_name": "Babun Nasi Ayam",
            "variant": "Lada Hitam",
            "notes": "nasi dikit",
            "price": 22000
        }
        resp = await client.post(f"/api/v1/sessions/{session_id}/orders", json=order_payload_2)
        assert resp.status_code == 201

        # 5. Toggle payment for order 1
        resp = await client.patch(f"/api/v1/orders/{order_1['id']}/payment", json={"is_paid": True})
        assert resp.status_code == 200
        assert resp.json()["is_paid"] is True

        # 6. Fetch summary
        resp = await client.get(f"/api/v1/sessions/{session_id}/summary")
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["total_orders"] == 2
        assert summary["total_amount"] == 37000
        assert summary["total_paid_count"] == 1
        assert summary["total_unpaid_count"] == 1
        assert "Rekap Titip Makan" in summary["whatsapp_recap_text"]

        # 6b. Test broadcast endpoint with PIN validation
        bad_broadcast = await client.post(f"/api/v1/sessions/{session_id}/broadcast", headers={"X-Coordinator-Pin": "wrong"})
        assert bad_broadcast.status_code == 403

        good_broadcast = await client.post(f"/api/v1/sessions/{session_id}/broadcast", headers={"X-Coordinator-Pin": "1234"})
        assert good_broadcast.status_code == 200
        assert good_broadcast.json()["status"] in ["skipped", "success"]

        # 7. Close session (requires coordinator pin)
        resp = await client.post(f"/api/v1/sessions/{session_id}/close", headers={"X-Coordinator-Pin": "1234"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "CLOSED"

        # 8. Attempting to order on closed session should fail (HTTP 400)
        resp = await client.post(f"/api/v1/sessions/{session_id}/orders", json=order_payload_1)
        assert resp.status_code == 400

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_order_price_update_and_suggestions_api(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session with coordinator_phone
        create_resp = await client.post("/api/v1/sessions", json={
            "title": "Titip Makan Siang",
            "coordinator_name": "Zi",
            "coordinator_phone": "6281234567890",
            "vendor_options": ["Mie Ayam"]
        })
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]
        assert create_resp.json()["coordinator_phone"] == "6281234567890"

        # Member adds order with price=0 (optional)
        order_resp = await client.post(f"/api/v1/sessions/{session_id}/orders", json={
            "user_name": "Amal",
            "vendor": "Bebek Kaleyo",
            "item_name": "Bebek Goreng Kremes",
            "variant": "Sambal Ijo",
            "price": 0
        })
        assert order_resp.status_code == 201
        order_id = order_resp.json()["id"]
        assert order_resp.json()["price"] == 0

        # Coordinator updates price via PATCH /orders/{order_id}/price
        price_resp = await client.patch(
            f"/api/v1/orders/{order_id}/price",
            json={"price": 38000}
        )
        assert price_resp.status_code == 200
        assert price_resp.json()["price"] == 38000

        # Verify suggestions endpoint includes Bebek Kaleyo
        sugg_resp = await client.get(f"/api/v1/sessions/{session_id}/suggestions")
        assert sugg_resp.status_code == 200
        data = sugg_resp.json()
        assert "Bebek Kaleyo" in data["tenants"]
        assert "Bebek Goreng Kremes" in data["menus"]["Bebek Kaleyo"]

        # Verify paginated history endpoint
        hist_resp = await client.get("/api/v1/sessions/history?page=1&limit=10")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert "items" in hist_data
        assert hist_data["total"] >= 1
        assert hist_data["page"] == 1
        assert hist_data["limit"] == 10
        assert hist_data["total_pages"] >= 1
        target_hist = next((s for s in hist_data["items"] if s["id"] == session_id), None)
        assert target_hist is not None
        assert len(target_hist["orders"]) == 1
        assert target_hist["orders"][0]["user_name"] == "Amal"
        assert target_hist["orders"][0]["vendor"] == "Bebek Kaleyo"

        # Verify unpaginated history when all=true
        hist_all = await client.get("/api/v1/sessions/history?all=true")
        assert hist_all.status_code == 200
        assert isinstance(hist_all.json(), list)
        assert len(hist_all.json()) >= 1

    app.dependency_overrides.clear()

