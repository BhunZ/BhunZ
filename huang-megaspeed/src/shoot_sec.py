"""Real screenshots of SEC EDGAR pages (Playwright, deviceScaleFactor 2).
SEC fair-access policy requires a declared User-Agent with contact email (approved by the owner)."""
import sys, asyncio
from playwright.async_api import async_playwright
UA = "BhunZ news-explainer research baohung.clone@gmail.com"
PAGES = {
 "sec_8k": "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000082/nvda-20261111.htm",
 "sec_ex991": "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000082/nvidiaannouncesceotransiti.htm",
}
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx = await b.new_context(user_agent=UA, viewport={"width": 900, "height": 1400}, device_scale_factor=2,
                                  extra_http_headers={"From": "baohung.clone@gmail.com"})
        pg = await ctx.new_page()
        for k, u in PAGES.items():
            r = await pg.goto(u, wait_until="networkidle", timeout=60000)
            print(k, r.status)
            await pg.screenshot(path=f"assets2/docs/{k}_full.png", full_page=True)
            open(f"assets2/docs/{k}.txt", "w").write(await pg.inner_text("body"))
            await asyncio.sleep(1.0)
        await b.close()
asyncio.run(main())
