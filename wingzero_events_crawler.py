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

TIMEOUT_MS = 60_000

PAGES = [
    {
        "url":        "https://pokemon.wingzero.tw/zh-TW/data/pokemon-go-events",
        "wait_until": "networkidle",
        "selector":   ".go-events-shell",
        "markers":    ["go-event-live-card", "go-event-upcoming-card"],
        "output":     "wingzero_events_real.html",
        "required":   True,
    },
    {
        "url":        "https://pokemon.wingzero.tw/zh-TW/news",
        "wait_until": "domcontentloaded",   # news page has many images → networkidle never fires
        # After DOMContentLoaded, wait until actual article links appear in the DOM.
        # a[href*="/zh-TW/news/"] matches individual articles (not the listing nav link).
        "content_selector": "a[href*='/zh-TW/news/']",
        "content_timeout":  25_000,          # up to 25 s for JS to render articles
        "wait_extra":       2000,            # small buffer after articles appear
        "selector":         "body",          # just confirms page loaded
        "markers":          ["wingzero"],
        "output":           "wingzero_news_real.html",
        "required":         False,           # log warning only on failure
    },
]


async def crawl_page(page, cfg):
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{now_utc}] Fetching {cfg['url']}")

    # Navigate
    try:
        await page.goto(
            cfg["url"],
            wait_until=cfg.get("wait_until", "networkidle"),
            timeout=TIMEOUT_MS,
        )
    except Exception as e:
        if cfg.get("required", True):
            print(f"ERROR: Page load failed — {e}", file=sys.stderr)
            return False
        print(f"WARNING: goto timed out, still attempting content grab — {e}", file=sys.stderr)

    # Wait for initial page selector (e.g. body)
    try:
        await page.wait_for_selector(cfg["selector"], timeout=10_000)
    except Exception:
        pass

    # For news: wait until article links actually appear in the DOM
    if "content_selector" in cfg:
        try:
            await page.wait_for_selector(
                cfg["content_selector"],
                timeout=cfg.get("content_timeout", 20_000),
            )
            print(f"  Article links detected in DOM")
        except Exception:
            print(f"WARNING: content selector '{cfg['content_selector']}' not found within timeout", file=sys.stderr)

    extra = cfg.get("wait_extra", 0)
    if extra:
        await page.wait_for_timeout(extra)

    html = await page.content()

    if not any(m in html for m in cfg["markers"]):
        print(
            f"ERROR: None of {cfg['markers']} found in {len(html):,}-byte response",
            file=sys.stderr,
        )
        return False

    with open(cfg["output"], "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    # Debug stats for news
    if "content_selector" in cfg:
        import re
        art_count  = len(re.findall(r'/zh-TW/news/', html))
        print(f"SUCCESS: {cfg['output']} — {len(html):,} bytes | news-links≈{art_count}")
    else:
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
