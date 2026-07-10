#!/usr/bin/env python3
"""
Daily crawler: fetches Pokémon GO events + news pages from pokemon.wingzero.tw
using Playwright (headless Chromium) to bypass bot protection.

GitHub Actions runs this at UTC 16:00 (= Taiwan 00:00) every day.
Saves:
  wingzero_events_real.html  — /zh-TW/data/pokemon-go-events
  wingzero_news_real.html    — /zh-TW/news
"""
import asyncio
import sys
from datetime import datetime, timezone

from playwright.async_api import async_playwright

PAGES = [
    {
        "url":        "https://pokemon.wingzero.tw/zh-TW/data/pokemon-go-events",
        "wait_until": "networkidle",
        "selector":   ".go-events-shell",
        "markers":    ["go-event-live-card", "go-event-upcoming-card"],
        "output":     "wingzero_events_real.html",
        "required":   True,   # job fails if this page fails
    },
    {
        "url":        "https://pokemon.wingzero.tw/zh-TW/news",
        "wait_until": "domcontentloaded",   # SPA keeps firing requests → never networkidle
        "wait_extra": 6000,                  # extra ms after DOMContentLoaded for JS render
        "selector":   "main, article, #__nuxt, body",
        "markers":    ["wingzero"],
        "output":     "wingzero_news_real.html",
        "required":   False,  # log warning only; events still commit on news failure
    },
]

TIMEOUT_MS = 60_000


async def crawl_page(page, cfg):
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{now_utc}] Fetching {cfg['url']}")

    try:
        await page.goto(
            cfg["url"],
            wait_until=cfg.get("wait_until", "networkidle"),
            timeout=TIMEOUT_MS,
        )
        await page.wait_for_selector(cfg["selector"], timeout=20_000)
        extra = cfg.get("wait_extra", 0)
        if extra:
            await page.wait_for_timeout(extra)
    except Exception as e:
        print(f"ERROR: Page load failed — {e}", file=sys.stderr)
        return False

    html = await page.content()

    if not any(m in html for m in cfg["markers"]):
        print(
            f"ERROR: None of {cfg['markers']} found in "
            f"{len(html):,}-byte response",
            file=sys.stderr,
        )
        return False

    with open(cfg["output"], "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    print(f"SUCCESS: {cfg['output']} — {len(html):,} bytes")
    return True


async def main():
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

        any_required_failed = False
        for cfg in PAGES:
            ok = await crawl_page(page, cfg)
            if not ok:
                if cfg.get("required", True):
                    any_required_failed = True
                else:
                    print(f"WARNING: {cfg['output']} skipped (non-critical)", file=sys.stderr)

        await browser.close()

    if any_required_failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
