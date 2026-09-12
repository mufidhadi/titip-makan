import socket
import threading
import time
import pytest
import uvicorn
from playwright.async_api import async_playwright, expect
from titip_makan.main import app

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

@pytest.fixture(scope="module")
def live_server():
    port = get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=2)

@pytest.mark.asyncio
async def test_reopen_closed_session_flow_e2e(live_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = await context.new_page()

        # Handle all dialogs automatically
        async def handle_dialog(dialog):
            if dialog.type == "prompt":
                await dialog.accept("1234")
            else:
                await dialog.accept()

        page.on("dialog", handle_dialog)

        # ----------------------------------------------------
        # 1. Open Coordinator page & Create Session
        # ----------------------------------------------------
        await page.goto(f"{live_server}/coordinator")
        await page.wait_for_load_state("networkidle")

        create_card = page.locator("#create-session-card")
        if not await create_card.is_visible():
            await page.click("#btn-new-session-toggle")
            await page.wait_for_timeout(300)

        await page.fill("#cs-title", "Sesi Uji Coba Buka Sementara")
        await page.fill("#cs-coordinator", "Irzi")
        await page.fill("#cs-phone", "+62 815-1382-5480")
        await page.fill("#cs-vendors", "Mie Ayam, Babun")
        await page.fill("#cs-cutoff", "15")
        await page.fill("#cs-payment", "BCA 1234567 a.n. Irzi")
        await page.click('#create-session-form button[type="submit"]')

        # Verify active session banner
        await expect(page.locator("#coord-session-title")).to_have_text("Sesi Uji Coba Buka Sementara", timeout=5000)
        await expect(page.locator("#coord-status-badge")).to_contain_text("SESI SEDANG BERLANGSUNG")

        # ----------------------------------------------------
        # 2. Close Session
        # ----------------------------------------------------
        await page.click("#btn-close-session")
        await page.wait_for_timeout(500)

        # Status should now be CLOSED
        await expect(page.locator("#coord-status-badge")).to_contain_text("SESI SUDAH DITUTUP")
        # Notice banner should be visible
        await expect(page.locator("#coord-closed-notice")).to_be_visible()
        # Close cutoff button should be hidden
        await expect(page.locator("#btn-close-cutoff-now")).not_to_be_visible()

        # Save screenshot of closed session in coordinator
        await page.screenshot(path="docs/screenshots/e2e_session_closed_coordinator.png")

        # ----------------------------------------------------
        # 3. Check Home Page (Index) when Session is CLOSED
        # ----------------------------------------------------
        home_page = await context.new_page()
        home_page.on("dialog", handle_dialog)
        await home_page.goto(live_server)
        await home_page.wait_for_load_state("networkidle")

        await expect(home_page.locator("#session-status-badge")).to_contain_text("SESI DITUTUP")
        await expect(home_page.locator("#reopen-quick-card")).to_be_visible()
        assert await home_page.locator("#btn-open-order-modal").is_disabled()

        # Save screenshot of closed session on home page
        await home_page.screenshot(path="docs/screenshots/e2e_session_closed_home.png")

        # ----------------------------------------------------
        # 4. Reopen Session via +5m button on Coordinator page
        # ----------------------------------------------------
        await page.click("#btn-extend-5")
        await page.wait_for_timeout(600)

        # Coordinator badge should immediately become active again
        await expect(page.locator("#coord-status-badge")).to_contain_text("SESI SEDANG BERLANGSUNG")
        await expect(page.locator("#coord-closed-notice")).not_to_be_visible()
        await expect(page.locator("#btn-close-session")).to_be_visible()

        # Save screenshot of reopened session in coordinator
        await page.screenshot(path="docs/screenshots/e2e_session_reopened_coordinator.png")

        # ----------------------------------------------------
        # 5. Verify Home Page automatically reflects OPEN status & Place Order
        # ----------------------------------------------------
        await home_page.reload()
        await home_page.wait_for_load_state("networkidle")

        await expect(home_page.locator("#session-status-badge")).to_contain_text("MEMBUAT PESANAN")
        await expect(home_page.locator("#reopen-quick-card")).not_to_be_visible()
        assert not await home_page.locator("#btn-open-order-modal").is_disabled()

        # Place an order in the reopened session
        await home_page.click("#btn-open-order-modal")
        await home_page.wait_for_timeout(300)
        await home_page.fill("#input-username", "Rian Susulan")
        await home_page.fill("#input-tenant", "Mie Ayam")
        await home_page.fill("#input-menu", "Mie Ayam Bakso")
        await home_page.fill("#input-price", "18000")
        await home_page.click("#btn-submit-order", force=True)
        await home_page.wait_for_timeout(500)

        assert await home_page.is_visible("#modal-step-success")
        await home_page.locator("#btn-finish-and-view-table").dispatch_event("click")
        await home_page.wait_for_timeout(500)

        # Verify order exists in desktop table
        table_text = await home_page.inner_text("#orders-table-card")
        assert "Rian Susulan" in table_text

        # ----------------------------------------------------
        # 6. Test Reopening via +10m on Home Page
        # ----------------------------------------------------
        # Close again from coordinator
        await page.click("#btn-close-session")
        await page.wait_for_timeout(500)
        await expect(page.locator("#coord-status-badge")).to_contain_text("SESI SUDAH DITUTUP")

        # Reload home page -> shows CLOSED with quick reopen card
        await home_page.reload()
        await home_page.wait_for_load_state("networkidle")
        await expect(home_page.locator("#reopen-quick-card")).to_be_visible()

        # Click +10m on home page
        await home_page.click("#btn-quick-reopen-10")
        await home_page.wait_for_timeout(600)

        # Status badge should now be MEMBUAT PESANAN again
        await expect(home_page.locator("#session-status-badge")).to_contain_text("MEMBUAT PESANAN")
        await expect(home_page.locator("#reopen-quick-card")).not_to_be_visible()

        # Save screenshot of reopened session on home page
        await home_page.screenshot(path="docs/screenshots/e2e_session_reopened_home.png")

        await context.close()
        await browser.close()
