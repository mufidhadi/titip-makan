import uuid

import pytest
from playwright.async_api import async_playwright, expect


@pytest.mark.asyncio
async def test_user_sets_up_weekday_auto_random_order_on_order_page(live_server):
    user = f"E2E Auto {uuid.uuid4().hex[:6]}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page = await context.new_page()

        await page.goto(live_server)
        await page.click("#auto-order-card summary")
        await page.fill("#auto-order-username", user)

        for tenant, menu in [("Mie Ayam", "Mie Ayam Polos"), ("Kantin", "Gado-gado")]:
            await page.fill("#auto-order-tenant", tenant)
            await page.fill("#auto-order-menu", menu)
            await page.click("#auto-order-add")
        await expect(page.locator("#auto-order-candidates li")).to_have_count(2)

        await page.check("#auto-order-enabled")
        await page.click("#auto-order-save")
        await expect(page.locator("#auto-order-status")).to_contain_text("aktif Senin–Jumat")
        await expect(page.locator("#auto-order-badge")).to_have_text("Aktif")

        # Saved name is remembered, so the setup reloads on its own
        await page.reload()
        await page.click("#auto-order-card summary")
        await expect(page.locator("#auto-order-candidates li")).to_have_count(2)
        await expect(page.locator("#auto-order-candidates")).to_contain_text("Rp 20.000")
        await expect(page.locator("#auto-order-enabled")).to_be_checked()

        scroll_width = await page.evaluate("document.documentElement.scrollWidth")
        assert scroll_width <= 390

        await browser.close()
