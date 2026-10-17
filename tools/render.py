import asyncio, os, sys
from playwright.async_api import async_playwright

src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(device_scale_factor=2)
        for f in sorted(os.listdir(src)):
            if not f.endswith(".svg"):
                continue
            svg = open(os.path.join(src, f), encoding="utf-8").read()
            await pg.set_content(f"<html><body style='margin:0'>{svg}</body></html>")
            el = await pg.query_selector("svg")
            await el.screenshot(path=os.path.join(dst, f[:-4] + ".png"))
        await b.close()

asyncio.run(main())
print("rendered")
