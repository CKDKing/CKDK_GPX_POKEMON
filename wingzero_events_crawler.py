#!/usr/bin/env python3
"""
Daily crawler: fetches Pokémon GO events + news from pokemon.wingzero.tw
using Playwright (headless Chromium) to bypass Cloudflare bot protection.

GitHub Actions runs this at UTC 16:00 (= Taiwan 00:00) every day.
Outputs:
  wingzero_events_real.html  — raw HTML for event Gantt parsing
  wingzero_news.json         — structured [{title, image, link, tag, date}, ...]
"""
import asyncio
import json
import sys
from datetime import datetime, timezone

from playwright.async_api import async_playwright

TIMEOUT_MS  = 90_000   # generous: CF challenge can take ~10-30 s

# Cloudflare "hold on" title patterns
CF_TITLES = ["請稍候", "Just a moment", "Checking your browser", "Please wait"]


# ── helpers ──────────────────────────────────────────────────────────────────

async def wait_for_cf(page, max_ms=35_000):
    """Block until the Cloudflare challenge title disappears."""
    try:
        await page.wait_for_function(
            """() => {
                const t = document.title;
                return !['請稍候','Just a moment','Checking your browser','Please wait']
                       .some(s => t.includes(s));
            }""",
            timeout=max_ms,
            polling=1000,
        )
        print("  CF challenge resolved")
        await page.wait_for_timeout(1500)   # brief pause after redirect
    except Exception:
        title = await page.title()
        print(f"WARNING: CF challenge not resolved (title: '{title}')", file=sys.stderr)


# ── individual crawlers ───────────────────────────────────────────────────────

async def crawl_events(page):
    """Fetch events page → save wingzero_events_real.html.  Returns True on success."""
    url = "https://pokemon.wingzero.tw/zh-TW/data/pokemon-go-events"
    print(f"  events  → {url}")
    try:
        await page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
    except Exception as e:
        print(f"ERROR: events page load failed — {e}", file=sys.stderr)
        return False

    html = await page.content()
    markers = ["go-event-live-card", "go-event-upcoming-card"]
    if not any(m in html for m in markers):
        print(f"ERROR: events markers not found in {len(html):,}-byte response", file=sys.stderr)
        return False

    with open("wingzero_events_real.html", "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"  events  ✓ {len(html):,} bytes → wingzero_events_real.html")
    return True


async def crawl_news(page):
    """
    Fetch news page → extract structured JSON → save wingzero_news.json.
    Returns True on success (even partial results count).
    Runs in the same browser session as crawl_events(), so the CF session
    cookie from the events page should already be set.
    """
    url = "https://pokemon.wingzero.tw/zh-TW/news"
    print(f"  news    → {url}")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
    except Exception as e:
        print(f"WARNING: news goto timed out, trying content grab — {e}", file=sys.stderr)

    # Handle Cloudflare challenge if it appeared
    title = await page.title()
    if any(cf in title for cf in CF_TITLES):
        print(f"  CF challenge detected (title: '{title}'), waiting…")
        await wait_for_cf(page)

    # Wait for actual article links to appear in DOM (up to 30 s)
    try:
        await page.wait_for_selector("a[href*='/zh-TW/news/']", timeout=30_000)
        print("  article links found in DOM")
    except Exception:
        print("WARNING: article links not found within 30 s", file=sys.stderr)

    await page.wait_for_timeout(1500)   # let lazy images register src attributes

    # Extract structured data directly from the live DOM
    items = await page.evaluate("""() => {
        const BASE = 'https://pokemon.wingzero.tw';
        const fixUrl = (u) => {
            if (!u || u.startsWith('data:')) return '';
            if (u.startsWith('//')) return 'https:' + u;
            if (u.startsWith('/'))  return BASE + u;
            return u;
        };

        const seen  = new Set();
        const items = [];

        // Collect all anchors pointing to an individual news article
        const links = [...document.querySelectorAll('a[href]')].filter(a => {
            const h = a.getAttribute('href') || '';
            return /\/zh-TW\/news\/[^?#\s]+/.test(h);
        });

        for (const link of links) {
            const href     = link.getAttribute('href');
            const fullLink = href.startsWith('http') ? href : BASE + href;
            if (seen.has(fullLink)) continue;
            seen.add(fullLink);

            // Image — check inside the anchor first, then its parent wrapper
            const imgEl = link.querySelector('img')
                       || link.parentElement?.querySelector('img');
            const imgSrc = imgEl
                ? (imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || '')
                : '';
            const image = fixUrl(imgSrc);

            // Title — prefer semantic heading / named class, else all text
            const titleEl = link.querySelector(
                'h1, h2, h3, h4, [class*="title"], [class*="name"], p'
            );
            let title = titleEl ? titleEl.textContent.trim() : '';
            if (!title) {
                // strip decorative child nodes, grab remaining text
                const clone = link.cloneNode(true);
                clone.querySelectorAll('img, svg, [class*="tag"], [class*="badge"], time')
                     .forEach(el => el.remove());
                title = clone.textContent.trim().replace(/\\s+/g, ' ');
            }
            title = title.slice(0, 120);

            // Tag / category badge
            const tagEl = link.querySelector(
                '[class*="tag"], [class*="badge"], [class*="cat"], [class*="type"], [class*="label"]'
            );
            const tag = tagEl ? tagEl.textContent.trim() : 'Pokémon GO';

            // Date
            const dateEl = link.querySelector('time, [class*="date"], [class*="time"]');
            const date   = dateEl
                ? (dateEl.getAttribute('datetime') || dateEl.textContent.trim())
                : '';

            if (title || image) {
                items.push({ title, image, link: fullLink, tag, date });
            }
        }

        return items.slice(0, 30);
    }""")

    if not items:
        print("WARNING: no news items extracted", file=sys.stderr)
        return False

    with open("wingzero_news.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"  news    ✓ {len(items)} items → wingzero_news.json")
    return True


# ── main ─────────────────────────────────────────────────────────────────────

async def main():
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{now_utc}] Starting WingZero crawler")

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

        # Events first → establishes CF session cookie for the domain
        events_ok = await crawl_events(page)

        # News second → same session, CF cookie already present
        news_ok = await crawl_news(page)

        await browser.close()

    if not news_ok:
        print("WARNING: news crawl incomplete (non-critical)", file=sys.stderr)
    if not events_ok:
        print("FATAL: events crawl failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
