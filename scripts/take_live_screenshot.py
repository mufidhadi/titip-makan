import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Desktop screenshot
        desktop_ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await desktop_ctx.new_page()
        await page.goto("https://titip-irzi.masmuf.cloud/menu", wait_until="networkidle")
        
        # Click Dapoer Bumbu filter pill to highlight it
        dapoer_pill = page.locator('button.tenant-filter-pill[data-tenant="Dapoer Bumbu"]')
        if await dapoer_pill.is_visible():
            await dapoer_pill.click()
            await page.wait_for_timeout(500)
            
        await page.screenshot(path="docs/screenshots/live_vps_dapoer_bumbu_dedup_desktop.png", full_page=True)
        print("Desktop screenshot saved.")
        
        # Mobile screenshot
        mobile_ctx = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mobile_page = await mobile_ctx.new_page()
        await mobile_page.goto("https://titip-irzi.masmuf.cloud/menu", wait_until="networkidle")
        mobile_pill = mobile_page.locator('button.tenant-filter-pill[data-tenant="Dapoer Bumbu"]')
        if await mobile_pill.is_visible():
            await mobile_pill.click()
            await mobile_page.wait_for_timeout(500)
            
        await mobile_page.screenshot(path="docs/screenshots/live_vps_dapoer_bumbu_dedup_mobile.png", full_page=True)
        print("Mobile screenshot saved.")

        # Babun filter pill screenshot
        await dapoer_pill.click() # unfilter / toggle or click Babun
        babun_pill = page.locator('button.tenant-filter-pill[data-tenant="Babun"]')
        if await babun_pill.is_visible():
            await babun_pill.click()
            await page.wait_for_timeout(500)
        await page.screenshot(path="docs/screenshots/live_vps_babun_dedup_desktop.png", full_page=True)
        print("Babun screenshot saved.")
        
        await desktop_ctx.close()
        await mobile_ctx.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
