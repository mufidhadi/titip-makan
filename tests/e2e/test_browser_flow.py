import os
import pytest
from playwright.async_api import async_playwright, expect

BASE_URL = "http://localhost:8080"

@pytest.mark.asyncio
async def test_full_browser_e2e_journey():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
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

        await page.fill("#cs-title", "Sesi Uji Coba Seamless E2E")
        await page.fill("#cs-coordinator", "Zi")
        await page.fill("#cs-phone", "6281234567890")
        await page.fill("#cs-vendors", "Mie Ayam, Babun")
        await page.fill("#cs-cutoff", "45")
        await page.fill("#cs-payment", "BCA 1234567 a.n. Zi")
        await page.click('#create-session-form button[type="submit"]')

        # Wait for session title to update
        await expect(page.locator("#coord-session-title")).to_have_text("Sesi Uji Coba Seamless E2E", timeout=5000)

        # ----------------------------------------------------
        # 2. Member Page: Buka App -> Lihat Tabel -> Tambah Pesanan (Amal)
        # ----------------------------------------------------
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_load_state("networkidle")

        # Step 1: Open modal Tambah Pesanan
        await page.click("#btn-open-order-modal")
        await page.wait_for_timeout(300)
        assert await page.is_visible("#modal-order")

        # Step 2: Fill quick name Amal
        await page.click('button.name-tag:has-text("Amal")')
        assert await page.input_value("#input-username") == "Amal"

        # Step 3: Type tenant and menu (free text / suggestions)
        await page.fill("#input-tenant", "Mie Ayam")
        await page.fill("#input-menu", "Mie Ayam")
        await page.fill("#input-variant", "Pangsit Rebus")
        await page.fill("#input-notes", "jangan pakai sawi")
        await page.fill("#input-price", "15000")

        # Step 4: Simpan Pesanan
        await page.click("#btn-submit-order")
        await page.wait_for_timeout(500)

        # Step 5: Beri Notif ke Koordinator screen appears
        assert await page.is_visible("#modal-step-success")
        wa_btn = page.locator("#btn-wa-notify-coordinator")
        wa_href = await wa_btn.get_attribute("href")
        assert "wa.me" in wa_href
        assert "Amal" in wa_href

        # Step 6: Lihat Tabel Pesanan Terkumpul
        await page.click("#btn-finish-and-view-table")
        await page.wait_for_timeout(300)

        # Modal is closed, order is in table
        assert not await page.is_visible("#modal-order")
        table_text = await page.inner_text("#orders-table-body")
        assert "Amal" in table_text
        assert "Mie Ayam" in table_text
        assert "Pangsit Rebus" in table_text
        assert "jangan pakai sawi" in table_text
        assert "Rp 15.000" in table_text

        # ----------------------------------------------------
        # 3. Member Page: Order with Optional Price (Adrian - Soto Betawi)
        # ----------------------------------------------------
        await page.click("#btn-open-order-modal")
        await page.wait_for_timeout(300)

        await page.fill("#input-username", "Adrian")
        await page.fill("#input-tenant", "Soto Betawi Bang Mamat")
        await page.fill("#input-menu", "Soto Daging Campur")
        await page.fill("#input-variant", "Kuah Santan")
        # Leave price empty (optional price!)
        await page.fill("#input-price", "")

        await page.click("#btn-submit-order")
        await page.wait_for_timeout(500)

        # Close success modal to view table
        await page.click("#btn-finish-and-view-table")
        await page.wait_for_timeout(300)

        table_text = await page.inner_text("#orders-table-body")
        assert "Adrian" in table_text
        assert "Soto Betawi Bang Mamat" in table_text
        assert "Belum di-set" in table_text

        # ----------------------------------------------------
        # 4. Coordinator Page: Coordinator Sets Price & Reconciles
        # ----------------------------------------------------
        await page.goto(f"{BASE_URL}/coordinator")
        await page.wait_for_load_state("networkidle")

        # Find Adrian's row with "Belum di-set" and set price to 35000 via prompt
        adrian_row = page.locator('#coordinator-orders-table tr:has-text("Adrian")')
        await adrian_row.locator('button:has-text("✏️ Set")').click()
        await page.wait_for_timeout(500)

        # Now Adrian's price is updated, total becomes 15.000 + 35.000 = 50.000
        assert "50.000" in await page.inner_text("#metric-amount")
        assert "35.000" in await adrian_row.inner_text()

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
        assert "15.000" in await page.inner_text("#metric-amount")

        # Close session
        await page.click("#btn-close-session")
        await page.wait_for_timeout(500)

        # Verify session view remains visible with CLOSED status
        assert await page.is_visible("#active-session-management")
        status_text = await page.inner_text("#coord-status-badge")
        assert "DITUTUP" in status_text

        # Take screenshot for proof
        os.makedirs("docs/screenshots", exist_ok=True)
        await page.screenshot(path="docs/screenshots/e2e_coordinator_seamless.png")

        # Go to home page to verify closed state
        await page.goto(f"{BASE_URL}/")
        await page.wait_for_load_state("networkidle")
        home_status = await page.inner_text("#session-status-badge")
        assert "DITUTUP" in home_status

        # Add order button should be disabled
        open_modal_btn = page.locator("#btn-open-order-modal")
        assert await open_modal_btn.is_disabled()

        await page.screenshot(path="docs/screenshots/e2e_home_seamless_closed.png")
        await browser.close()
