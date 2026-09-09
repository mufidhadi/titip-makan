import socket
import threading
import time
import pytest
import uvicorn
from playwright.async_api import async_playwright
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
async def test_responsive_navigation_desktop_and_mobile(live_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ----------------------------------------------------
        # 1. Desktop Viewport (1200 x 800)
        # ----------------------------------------------------
        desktop_ctx = await browser.new_context(viewport={"width": 1200, "height": 800})
        desktop_page = await desktop_ctx.new_page()
        await desktop_page.goto(live_server)
        await desktop_page.wait_for_load_state("networkidle")

        # Desktop nav should be visible, mobile menu button should not be visible
        assert await desktop_page.locator("#nav-pesan").is_visible()
        assert await desktop_page.locator("#nav-history").is_visible()
        assert await desktop_page.locator("#nav-leaderboard").is_visible()
        assert await desktop_page.locator("#nav-coordinator").is_visible()
        assert not await desktop_page.locator("#mobile-menu-btn").is_visible()
        assert not await desktop_page.locator("#mobile-menu").is_visible()

        # Check no horizontal overflow on desktop
        scroll_w = await desktop_page.evaluate("document.documentElement.scrollWidth")
        client_w = await desktop_page.evaluate("document.documentElement.clientWidth")
        assert scroll_w <= client_w

        await desktop_ctx.close()

        # ----------------------------------------------------
        # 2. Mobile Viewport (390 x 844 - iPhone / Android size)
        # ----------------------------------------------------
        mobile_ctx = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mobile_page = await mobile_ctx.new_page()
        await mobile_page.goto(live_server)
        await mobile_page.wait_for_load_state("networkidle")

        # Mobile menu button should be visible, desktop nav should NOT be visible
        assert await mobile_page.locator("#mobile-menu-btn").is_visible()
        assert not await mobile_page.locator("#nav-pesan").is_visible()
        assert not await mobile_page.locator("#mobile-menu").is_visible()

        # Verify NO horizontal overflow on mobile!
        scroll_w_m = await mobile_page.evaluate("document.documentElement.scrollWidth")
        client_w_m = await mobile_page.evaluate("document.documentElement.clientWidth")
        assert scroll_w_m <= client_w_m, f"Mobile page has horizontal overflow: scrollWidth {scroll_w_m} > clientWidth {client_w_m}"

        # Click hamburger button -> mobile menu opens
        await mobile_page.click("#mobile-menu-btn")
        await mobile_page.wait_for_timeout(200)
        assert await mobile_page.locator("#mobile-menu").is_visible()
        assert await mobile_page.locator("#menu-icon-close").is_visible()
        assert not await mobile_page.locator("#menu-icon-bars").is_visible()
        assert await mobile_page.get_attribute("#mobile-menu-btn", "aria-expanded") == "true"

        # Click again -> mobile menu closes
        await mobile_page.click("#mobile-menu-btn")
        await mobile_page.wait_for_timeout(200)
        assert not await mobile_page.locator("#mobile-menu").is_visible()
        assert await mobile_page.get_attribute("#mobile-menu-btn", "aria-expanded") == "false"

        # Reopen and test navigation to Leaderboard
        await mobile_page.click("#mobile-menu-btn")
        await mobile_page.wait_for_timeout(200)
        await mobile_page.click('#mobile-menu a[href="/leaderboard"]')
        await mobile_page.wait_for_load_state("networkidle")
        assert "/leaderboard" in mobile_page.url

        # Check Leaderboard page mobile layout has no overflow
        scroll_w_lb = await mobile_page.evaluate("document.documentElement.scrollWidth")
        client_w_lb = await mobile_page.evaluate("document.documentElement.clientWidth")
        assert scroll_w_lb <= client_w_lb, f"Leaderboard page has horizontal overflow: {scroll_w_lb} > {client_w_lb}"

        await mobile_ctx.close()
        await browser.close()
