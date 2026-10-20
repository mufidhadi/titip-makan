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
async def test_menu_catalog_page_e2e(live_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1200, "height": 800})
        page = await ctx.new_page()

        # 1. Buka halaman katalog menu
        await page.goto(f"{live_server}/menu")
        await page.wait_for_load_state("networkidle")

        # 2. Verifikasi Header dan Counter
        title = await page.locator("main h1").inner_text()
        assert "Katalog Tenant & Menu" in title
        assert await page.locator("#stat-total-tenants").is_visible()
        assert await page.locator("#stat-total-menus").is_visible()

        # 3. Verifikasi Keberadaan Tenant Padang, Babun, Mie Ayam, Dapoer Bumbu
        content = await page.content()
        assert "Padang" in content
        assert "Babun" in content
        assert "Mie Ayam" in content
        assert "Dapoer Bumbu" in content
        assert "Nasi Rendang" in content
        assert "Nasi Timbel Komplit" in content

        # 4. Uji Filter Pill Tenant "Dapoer Bumbu"
        dapoer_pill = page.locator('button.tenant-filter-pill[data-tenant="Dapoer Bumbu"]')
        assert await dapoer_pill.is_visible()
        await dapoer_pill.click()
        await page.wait_for_timeout(200)

        # Dapoer Bumbu section harus terlihat, Babun section harus tersembunyi
        assert await page.locator('section[data-tenant-name="Dapoer Bumbu"]').is_visible()
        assert not await page.locator('section[data-tenant-name="Babun"]').is_visible()

        # Uji Filter Pill Tenant "Padang"
        padang_pill = page.locator('button.tenant-filter-pill[data-tenant="Padang"]')
        assert await padang_pill.is_visible()
        await padang_pill.click()
        await page.wait_for_timeout(200)

        # Padang section harus terlihat, Babun section harus tersembunyi
        assert await page.locator('section[data-tenant-name="Padang"]').is_visible()
        assert not await page.locator('section[data-tenant-name="Babun"]').is_visible()

        # Kembalikan ke Semua Tenant
        all_pill = page.locator('button.tenant-filter-pill[data-tenant="all"]')
        await all_pill.click()
        await page.wait_for_timeout(200)
        assert await page.locator('section[data-tenant-name="Babun"]').is_visible()

        # 5. Uji Live Search "Rendang"
        search_input = page.locator("#menu-search-input")
        await search_input.fill("rendang")
        await page.wait_for_timeout(200)

        # Menu rendang harus terlihat
        rendang_cards = page.locator('.menu-item-card:not(.hidden)')
        count = await rendang_cards.count()
        assert count > 0
        first_rendang = await rendang_cards.first.inner_text()
        assert "Rendang" in first_rendang or "rendang" in first_rendang.lower()

        # Uji tombol Clear search
        clear_btn = page.locator("#menu-search-clear")
        assert await clear_btn.is_visible()
        await clear_btn.click()
        await page.wait_for_timeout(200)
        assert await search_input.input_value() == ""

        # 6. Uji Empty State Pencarian
        await search_input.fill("xyznonexistentitem12345")
        await page.wait_for_timeout(200)
        assert await page.locator("#no-search-results").is_visible()
        assert "Menu Tidak Ditemukan" in await page.locator("#no-search-results").inner_text()

        # Klik tombol reset search
        await page.click("#btn-reset-search")
        await page.wait_for_timeout(200)
        assert not await page.locator("#no-search-results").is_visible()

        # 7. Uji Responsivitas Mobile (iPhone size 390x844)
        mobile_ctx = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mobile_page = await mobile_ctx.new_page()
        await mobile_page.goto(f"{live_server}/menu")
        await mobile_page.wait_for_load_state("networkidle")

        # Cek horizontal overflow di mobile
        scroll_w = await mobile_page.evaluate("document.documentElement.scrollWidth")
        client_w = await mobile_page.evaluate("document.documentElement.clientWidth")
        assert scroll_w <= client_w, f"Katalog menu memiliki horizontal overflow pada mobile: {scroll_w} > {client_w}"

        # Cek tombol navigasi mobile menuju menu aktif
        await mobile_page.click("#mobile-menu-btn")
        await mobile_page.wait_for_timeout(200)
        assert await mobile_page.locator('#mobile-menu a[href="/menu"]').is_visible()

        await mobile_ctx.close()
        await ctx.close()
        await browser.close()
