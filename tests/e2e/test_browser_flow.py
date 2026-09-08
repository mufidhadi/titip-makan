import os
import pytest
from playwright.async_api import async_playwright, expect

BASE_URL = "http://localhost:8080"

@pytest.mark.asyncio
async def test_full_browser_e2e_journey():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Mobile viewport emulation (iPhone 13/14 size: 390 x 844)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = await context.new_page()

        # Handle dialogs (confirm / alert / prompt)
        async def handle_dialog(dialog):
            if dialog.type == "prompt":
                if "PIN" in dialog.message:
                    await dialog.accept("1234")  # Coordinator PIN
                elif "harga" in dialog.message.lower():
                    await dialog.accept("35000")  # Set price 35000
                else:
                    await dialog.accept("1234")
            else:
                await dialog.accept()

        page.on("dialog", handle_dialog)

        # ----------------------------------------------------
        # 1. Coordinator Page: Create a fresh session
        # ----------------------------------------------------
        await page.goto(f"{BASE_URL}/coordinator")
        await page.wait_for_load_state("networkidle")

        create_card = page.locator("#create-session-card")
        if not await create_card.is_visible():
            await page.click("#btn-new-session-toggle")
            await page.wait_for_timeout(300)

        await page.fill("#cs-title", "Sesi Mobile First MTN")
        await page.fill("#cs-coordinator", "Zi")
        await page.fill("#cs-phone", "6281234567890")
        await page.fill("#cs-vendors", "Mie Ayam, Babun")
        await page.fill("#cs-cutoff", "45")
        await page.fill("#cs-payment", "BCA 1234567 a.n. Zi")
        await page.click('#create-session-form button[type="submit"]')

        # Wait for session title to update
        await expect(page.locator("#coord-session-title")).to_have_text("Sesi Mobile First MTN", timeout=5000)
        assert await page.is_visible("#btn-broadcast-wa")

        # Test broadcast WA button
        await page.click("#btn-broadcast-wa")
        await page.wait_for_timeout(300)

        # ----------------------------------------------------
        # 2. Member Page (Mobile View): Buka App -> Lihat Antrean -> Tambah Pesanan (Amal)
        # ----------------------------------------------------
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_load_state("networkidle")

        # Verify Mobile Bottom Action Bar is visible
        assert await page.is_visible("#mobile-bottom-bar")

        # Step 1: Open modal via Mobile Sticky FAB Button
        await page.click("#btn-mobile-open-order-modal")
        await page.wait_for_timeout(300)
        assert await page.is_visible("#modal-order")

        # Step 2: Fill quick name Amal
        await page.click('button.name-tag:has-text("Amal")')
        assert await page.input_value("#input-username") == "Amal"

        # Step 3: Type tenant and menu (NO VARIANT FIELD!) and verify auto-fill
        assert not await page.locator("#input-variant").is_visible()

        # Test catalog auto-complete & price auto-fill
        await page.fill("#input-menu", "Babun Nasi Telor Dobel")
        await page.dispatch_event("#input-menu", "input")
        assert await page.input_value("#input-price") == "13000"
        assert await page.input_value("#input-tenant") == "Babun"

        # Now fill for actual Amal order
        await page.fill("#input-tenant", "Mie Ayam")
        await page.fill("#input-menu", "Mie Ayam Bakso")
        await page.fill("#input-notes", "jangan pakai sawi")
        await page.fill("#input-price", "18000")

        # Step 4: Simpan Pesanan
        await page.click("#btn-submit-order")
        await page.wait_for_timeout(500)

        # Step 5: Beri Notif ke Koordinator screen appears
        assert await page.is_visible("#modal-step-success")
        wa_btn = page.locator("#btn-wa-notify-coordinator")
        wa_href = await wa_btn.get_attribute("href")
        assert "wa.me" in wa_href
        assert "Amal" in wa_href
        assert "Mie%20Ayam%20Bakso" in wa_href

        # Step 6: Lihat Tabel / Kartu Antrean
        await page.click("#btn-finish-and-view-table")
        await page.wait_for_timeout(300)

        # Modal is closed, mobile order card is in the list
        assert not await page.is_visible("#modal-order")
        mobile_cards_text = await page.inner_text("#orders-cards-container")
        assert "Amal" in mobile_cards_text
        assert "Mie Ayam" in mobile_cards_text
        assert "Mie Ayam Bakso" in mobile_cards_text
        assert "jangan pakai sawi" in mobile_cards_text
        assert "Rp 18.000" in mobile_cards_text

        # ----------------------------------------------------
        # 3. Member Page: Second Order (Adrian) with Optional Price
        # ----------------------------------------------------
        await page.click("#btn-mobile-open-order-modal")
        await page.wait_for_timeout(300)

        await page.fill("#input-username", "Adrian")
        await page.fill("#input-tenant", "Soto Betawi Bang Mamat")
        await page.fill("#input-menu", "Soto Daging Campur")
        # Leave price empty (optional price!)
        await page.fill("#input-price", "")

        await page.click("#btn-submit-order")
        await page.wait_for_timeout(500)

        # Close success modal to view mobile cards
        await page.click("#btn-finish-and-view-table")
        await page.wait_for_timeout(300)

        mobile_cards_text = await page.inner_text("#orders-cards-container")
        assert "Adrian" in mobile_cards_text
        assert "Soto Betawi Bang Mamat".upper() in mobile_cards_text.upper()
        assert "Soto Daging Campur" in mobile_cards_text
        assert "Belum di-set" in mobile_cards_text

        # Take screenshot of mobile orders list
        os.makedirs("docs/screenshots", exist_ok=True)
        await page.screenshot(path="docs/screenshots/mobile_orders_view.png")

        # ----------------------------------------------------
        # 4. Coordinator Page: Sets Price & Closes
        # ----------------------------------------------------
        await page.goto(f"{BASE_URL}/coordinator")
        await page.wait_for_load_state("networkidle")

        # Find Adrian's row with "Belum di-set" and set price to 35000 via prompt
        adrian_row = page.locator('#coordinator-orders-table tr:has-text("Adrian")')
        await adrian_row.locator('button:has-text("✏️ Set")').click()
        await page.wait_for_timeout(500)

        # Total becomes 18.000 + 35.000 = 53.000
        assert "53.000" in await page.inner_text("#metric-amount")

        # Toggle payment for Amal
        amal_row = page.locator('#coordinator-orders-table tr:has-text("Amal")')
        await amal_row.locator('button:has-text("Set Lunas")').click()
        await page.wait_for_timeout(500)
        assert await page.inner_text("#metric-paid") == "1"

        # Delete Adrian's order
        adrian_row = page.locator('#coordinator-orders-table tr:has-text("Adrian")')
        await adrian_row.locator("button:has-text('🗑️')").click()
        await page.wait_for_timeout(500)

        # Now only Amal's order remains
        assert await page.inner_text("#metric-orders") == "1 porsi"
        assert "18.000" in await page.inner_text("#metric-amount")

        # Close session
        await page.click("#btn-close-session")
        await page.wait_for_timeout(500)

        # Verify session view remains visible with CLOSED status
        status_text = await page.inner_text("#coord-status-badge")
        assert "DITUTUP" in status_text

        await page.screenshot(path="docs/screenshots/mobile_coordinator_view.png")

        # Go to home page to verify closed state on mobile
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_load_state("networkidle")
        home_status = await page.inner_text("#session-status-badge")
        assert "DITUTUP" in home_status

        # Mobile button should be disabled
        mobile_btn = page.locator("#btn-mobile-open-order-modal")
        assert await mobile_btn.is_disabled()

        await page.screenshot(path="docs/screenshots/mobile_home_closed.png")
        await browser.close()
