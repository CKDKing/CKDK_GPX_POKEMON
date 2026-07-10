#!/usr/bin/env python3
"""
Daily crawler — two independent jobs in one script:

1. Events  (wingzero.tw)   — Playwright headless Chromium (SSR page, CF allows it)
   → wingzero_events_real.html

2. News    (pokemongo.com) — plain requests + BeautifulSoup (no CF issues)
   → pgo_news.json          [{title, image, link}, ...]

GitHub Actions runs this at UTC 16:00 (= Taiwan 00:00) every day.
"""
import asyncio
import json
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

EVENT_TIMEOUT_MS = 90_000


# ── News: pokemongo.com (requests, no Playwright) ────────────────────────────

NEWS_URL  = "https://pokemongo.com/zh-Hant/news"
NEWS_BASE = "https://pokemongo.com"
NEWS_OUT  = "pgo_news.json"


def crawl_news():
    print(f"[news]  fetching {NEWS_URL}")
    try:
        resp = requests.get(
            NEWS_URL,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-TW,zh;q=0.9",
            },
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"WARNING: news fetch failed — {e}", file=sys.stderr)
        return False

    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    seen  = set()

    # All anchor tags pointing to an individual article
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/news/" not in href:
            continue
        # Skip the listing page itself
        if href.rstrip("/").endswith("/news"):
            continue

        full_link = href if href.startswith("http") else NEWS_BASE + href
        if full_link in seen:
            continue
        seen.add(full_link)

        # Image
        img    = a.find("img")
        image  = ""
        if img:
            image = img.get("src") or img.get("data-src") or ""
            if image.startswith("//"):
                image = "https:" + image
            elif image.startswith("/"):
                image = NEWS_BASE + image

        # Title: text directly in the anchor (excluding nested noise)
        title = a.get_text(separator=" ", strip=True)
        title = " ".join(title.split())[:150]

        if title or image:
            items.append({"title": title, "image": image, "link": full_link})

    if not items:
        print("WARNING: 0 news items parsed from pokemongo.com", file=sys.stderr)
        return False

    with open(NEWS_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(items[:30], f, ensure_ascii=False, indent=2)

    print(f"[news]  ✓ {min(len(items),30)} items → {NEWS_OUT}")
    return True


# ── Events: wingzero.tw (Playwright) ─────────────────────────────────────────

async def crawl_events():
    url = "https://pokemon.wingzero.tw/zh-TW/data/pokemon-go-events"
    print(f"[events] fetching {url}")

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
            await page.goto(url, wait_until="networkidle", timeout=EVENT_TIMEOUT_MS)
        except Exception as e:
            print(f"ERROR: events page load failed — {e}", file=sys.stderr)
            await browser.close()
            return False

        # Extract only the event card elements (not the full page with ads)
        html = await page.evaluate("""() => {
            const selectors = [
                '.go-event-live-card',
                '.go-event-upcoming-card',
                '.go-event-ended-card',
                '.go-event-upcoming-raid-card',
                '.go-event-live-raid-card',
                '.go-event-timeline'
            ];
            const parts = [];
            selectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => parts.push(el.outerHTML));
            });
            return '<html><body>' + parts.join('\\n') + '</body></html>';
        }""")
        await browser.close()

    markers = ["go-event-live-card", "go-event-upcoming-card"]
    if not any(m in html for m in markers):
        print(f"ERROR: events markers not found ({len(html):,} bytes)", file=sys.stderr)
        return False

    with open("wingzero_events_real.html", "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"[events] ✓ {len(html):,} bytes → wingzero_events_real.html")
    return True


# ── main ─────────────────────────────────────────────────────────────────────

async def main():
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"=== WingZero crawler started {now_utc} ===")

    # News: synchronous, no browser needed
    news_ok = crawl_news()

    # Events: async Playwright
    events_ok = await crawl_events()

    if not news_ok:
        print("WARNING: news crawl incomplete (non-critical)", file=sys.stderr)
    if not events_ok:
        print("FATAL: events crawl failed", file=sys.stderr)
        sys.exit(1)

    print("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
