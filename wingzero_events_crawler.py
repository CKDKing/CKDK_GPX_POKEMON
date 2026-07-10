#!/usr/bin/env python3
"""
Daily crawler: fetches the Pokémon GO events page from pokemon.wingzero.tw
using Playwright (headless Chromium) to bypass bot protection.

GitHub Actions runs this at UTC 16:00 (= Taiwan 00:00) every day.
"""
import asyncio
import sys
from datetime import datetime, timezone

from playwright.async_api import async_playwright

TARGET_URL = "https://pokemon.wingzero.tw/zh-TW/data/pokemon-go-events"
OUTPUT_FILE = "wingzero_events_real.html"
REQUIRED_SELECTOR = ".go-events-shell"
TIMEOUT_MS = 60_000


async def crawl():
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{now_utc}] Launching browser → {TARGET_URL}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="zh-TW",
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()

        try:
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=TIMEOUT_MS)
            await page.wait_for_selector(REQUIRED_SELECTOR, timeout=30_000)
        except Exception as e:
            print(f"ERROR: Page load failed — {e}", file=sys.stderr)
            await browser.close()
            sys.exit(1)

        html = await page.content()
        await browser.close()

    # Validate key elements
    markers = ["go-event-live-card", "go-event-upcoming-card"]
    found = [m for m in markers if m in html]
    if not found:
        print(
            f"ERROR: Expected markers not found in {len(html):,}-byte response",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    live_count = html.count('go-event-live-card"')
    upcoming_count = html.count('go-event-upcoming-card"')
    print(
        f"SUCCESS: {OUTPUT_FILE} updated — "
        f"{len(html):,} bytes | ongoing={live_count} | upcoming={upcoming_count}"
    )


if __name__ == "__main__":
    asyncio.run(crawl())
