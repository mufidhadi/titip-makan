import os
import pytest
from playwright.async_api import async_playwright, expect

BASE_URL = "http://localhost:8080"

@pytest.mark.asyncio
async def test_full_browser_e2e_journey():
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = await context.new_page()

        # Handle dialogs (confirm / alert / prompt) automatically
        async def handle_dialog(dialog):
            if dialog.type == "prompt":
                await dialog.accept("1234")  # Coordinator PIN
            else:
                await dialog.accept()

        page.on("dialog", handle_dialog)

        # ----------------------------------------------------
        # 1. Coordinator Page: Create a fresh session
        # ----------------------------------------------------
        await page.goto(f"{BASE_URL}/coordinator")
        await page.wait_for_load_state("networkidle")

        # Check if create session card is visible, if not click new session button
        create_card = page.locator("#create-session-card")
        if not await create_card.is_visible():
            await page.click("#btn-new-session-toggle")
            await page.wait_for_timeout(300)

        await page.fill("#cs-title", "Sesi Uji Coba E2E Browser")
        await page.fill("#cs-coordinator", "Zi")
        await page.fill("#cs-vendors", "Mie Ayam, Babun")
        await page.fill("#cs-cutoff", "45")
        await page.fill("#cs-payment", "BCA 1234567 a.n. Zi")
        await page.click('#create-session-form button[type="submit"]')

        # Wait for session title to update
        await expect(page.locator("#coord-session-title")).to_have_text("Sesi Uji Coba E2E Browser", timeout=5000)

        # ----------------------------------------------------
        # 2. Member Page: Standard Order (Amal - Mie Ayam)
        # ----------------------------------------------------
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_load_state("networkidle")

        # Click quick name 'Amal'
        await page.click('button.name-tag:has-text("Amal")')
        assert await page.input_value("#input-username") == "Amal"

        # Select vendor
        await page.select_option("#select-vendor", "Mie Ayam")
        await page.wait_for_timeout(200)

        # Select menu
        await page.select_option("#select-menu", "Mie Ayam")
        await page.wait_for_timeout(200)

        # Select variant
        await page.check('input[name="order-variant"][value="Pangsit Rebus"]')
        await page.fill("#input-notes", "jangan pakai sawi")

        # Verify price display
        assert "Rp 15.000" in await page.inner_text("#price-display")

        # Submit order
        await page.click("#btn-submit-order")
        await page.wait_for_timeout(500)

        # Verify order in live list
        order_list_text = await page.inner_text("#orders-list")
        assert "Amal" in order_list_text
        assert "Mie Ayam" in order_list_text
        assert "Pangsit Rebus" in order_list_text
        assert "jangan pakai sawi" in order_list_text

        # ----------------------------------------------------
        # 3. Member Page: Custom Vendor & Custom Variant Order
        # ----------------------------------------------------
        await page.fill("#input-username", "Adrian")
        await page.select_option("#select-vendor", "__custom__")
        await page.wait_for_timeout(200)

        # Custom vendor input should be visible
        assert await page.is_visible("#custom-vendor-wrapper")
        await page.fill("#input-custom-vendor", "Soto Betawi Bang Mamat")
        await page.fill("#input-custom-menu", "Soto Daging Campur")
        await page.fill("#input-custom-price", "35000")
        await page.fill("#input-custom-variant", "Kuah Santan Susu")
        await page.fill("#input-notes", "sambal dipisah")

        assert "Rp 35.000" in await page.inner_text("#price-display")

        await page.click("#btn-submit-order")
        await page.wait_for_timeout(500)

        order_list_text = await page.inner_text("#orders-list")
        assert "Adrian" in order_list_text
        assert "Soto Betawi Bang Mamat" in order_list_text
        assert "Soto Daging Campur" in order_list_text
        assert "Kuah Santan Susu" in order_list_text

        # ----------------------------------------------------
        # 4. Coordinator Page: Reconcile, Toggle Payment & Close
        # ----------------------------------------------------
        await page.goto(f"{BASE_URL}/coordinator")
        await page.wait_for_load_state("networkidle")

        # Verify 2 orders and total amount (15000 + 35000 = 50000)
        assert await page.inner_text("#metric-orders") == "2 porsi"
        assert "50.000" in await page.inner_text("#metric-amount")

        # Toggle payment for Amal
        amal_row = page.locator('#coordinator-orders-table tr:has-text("Amal")')
        await amal_row.locator('button:has-text("Set Lunas")').click()
        await page.wait_for_timeout(500)

        # Verify paid metric increases
        assert await page.inner_text("#metric-paid") == "1"

        # Delete Adrian's order (simulate deleting test order)
        adrian_row = page.locator('#coordinator-orders-table tr:has-text("Adrian")')
        await adrian_row.locator("button:has-text('🗑️')").click()
        await page.wait_for_timeout(500)

        # Now only 1 order remains
        assert await page.inner_text("#metric-orders") == "1 porsi"
        assert "15.000" in await page.inner_text("#metric-amount")

        # Close session
        await page.click("#btn-close-session")
        await page.wait_for_timeout(500)

        # Verify after closing, session view remains visible with CLOSED status
        assert await page.is_visible("#active-session-management")
        status_text = await page.inner_text("#coord-status-badge")
        assert "DITUTUP" in status_text

        # Take screenshot for proof
        os.makedirs("docs/screenshots", exist_ok=True)
        await page.screenshot(path="docs/screenshots/e2e_coordinator_verified.png")

        # Go to home page to verify closed banner
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_load_state("networkidle")
        home_status = await page.inner_text("#session-status-badge")
        assert "DITUTUP" in home_status

        # Order button should be disabled
        submit_btn = page.locator("#btn-submit-order")
        assert await submit_btn.is_disabled()

        await page.screenshot(path="docs/screenshots/e2e_home_closed_verified.png")

        await browser.close()
