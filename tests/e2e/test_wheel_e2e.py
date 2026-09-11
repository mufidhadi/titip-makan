import socket
import threading
import time
import pytest
from playwright.async_api import async_playwright, expect
from titip_makan.main import app


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    import uvicorn

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


async def _new_page(browser):
    context = await browser.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
        reduced_motion="reduce",
    )
    page = await context.new_page()
    return context, page


@pytest.mark.asyncio
async def test_coordinator_wheel_tenant_flow_fills_cs_vendors(live_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context, page = await _new_page(browser)

        await page.goto(f"{live_server}/coordinator")
        await page.wait_for_load_state("networkidle")

        create_card = page.locator("#create-session-card")
        if not await create_card.is_visible():
            await page.click("#btn-new-session-toggle")
            await page.wait_for_timeout(200)

        await page.click('[data-testid="wheel-open-tenant"]')
        await expect(page.locator('[data-testid="wheel-modal"]')).to_be_visible()

        await page.click('[data-testid="wheel-spin"]')
        await expect(page.locator('[data-testid="wheel-result"]')).to_be_visible(timeout=3000)

        winner_label = await page.inner_text("#wheel-result-label")
        assert winner_label.strip() != ""

        await page.click('[data-testid="wheel-apply"]')
        await expect(page.locator('[data-testid="wheel-modal"]')).to_be_hidden()

        cs_vendors_value = await page.input_value("#cs-vendors")
        assert cs_vendors_value.strip() == winner_label.strip()

        await context.close()
        await browser.close()


@pytest.mark.asyncio
async def test_index_wheel_item_flow_fills_order_form(live_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Create an active session first via the coordinator page
        setup_context, setup_page = await _new_page(browser)
        await setup_page.goto(f"{live_server}/coordinator")
        await setup_page.wait_for_load_state("networkidle")

        create_card = setup_page.locator("#create-session-card")
        if not await create_card.is_visible():
            await setup_page.click("#btn-new-session-toggle")
            await setup_page.wait_for_timeout(200)

        await setup_page.fill("#cs-title", "Sesi Wheel E2E")
        await setup_page.fill("#cs-coordinator", "Zi")
        await setup_page.fill("#cs-vendors", "Babun, Mie Ayam")
        await setup_page.fill("#cs-cutoff", "45")
        await setup_page.click('#create-session-form button[type="submit"]')
        await expect(setup_page.locator("#coord-session-title")).to_have_text("Sesi Wheel E2E", timeout=5000)
        await setup_context.close()

        # Now drive the member order form
        context, page = await _new_page(browser)
        await page.goto(f"{live_server}/")
        await page.wait_for_load_state("networkidle")

        await page.locator("#btn-mobile-open-order-modal").dispatch_event("click")
        await page.wait_for_timeout(200)

        await page.click('[data-testid="wheel-open-item"]')
        await expect(page.locator('[data-testid="wheel-modal"]')).to_be_visible()

        await page.click('[data-testid="wheel-spin"]')
        await expect(page.locator('[data-testid="wheel-result"]')).to_be_visible(timeout=3000)

        winner_label = (await page.inner_text("#wheel-result-label")).strip()

        await page.click('[data-testid="wheel-apply"]')
        await expect(page.locator('[data-testid="wheel-modal"]')).to_be_hidden()

        menu_value = await page.input_value("#input-menu")
        tenant_value = await page.input_value("#input-tenant")
        price_value = await page.input_value("#input-price")

        assert menu_value.strip() == winner_label
        assert tenant_value.strip() in ("Babun", "Mie Ayam")
        assert price_value.strip() != ""

        await context.close()
        await browser.close()


@pytest.mark.asyncio
async def test_wheel_exclude_manual_disables_spin_below_two_candidates(live_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context, page = await _new_page(browser)

        await page.goto(f"{live_server}/coordinator")
        await page.wait_for_load_state("networkidle")

        create_card = page.locator("#create-session-card")
        if not await create_card.is_visible():
            await page.click("#btn-new-session-toggle")
            await page.wait_for_timeout(200)

        await page.click('[data-testid="wheel-open-tenant"]')
        await expect(page.locator('[data-testid="wheel-modal"]')).to_be_visible()

        checkboxes = page.locator('[data-testid="wheel-candidate"]')
        await expect(checkboxes.first).to_be_visible(timeout=3000)
        count = await checkboxes.count()
        assert count >= 3, "expected the real catalog to have at least 3 tenants"

        # Uncheck all but one, leaving exactly 1 active candidate
        for i in range(count - 1):
            await checkboxes.nth(i).uncheck()

        spin_btn = page.locator('[data-testid="wheel-spin"]')
        await expect(spin_btn).to_be_disabled()

        await context.close()
        await browser.close()
