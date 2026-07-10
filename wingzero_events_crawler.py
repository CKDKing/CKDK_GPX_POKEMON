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
from playwright_stealth import stealth_async

EVENT_TIMEOUT_MS = 90_000
NEWS_TIMEOUT_MS  = 120_000  # longer: news page has many images

CF_TITLES = ["請稍候", "Just a moment", "Checking your browser", "Please wait"]


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
        await page.wait_for_timeout(1500)
        return True
    except Exception:
        return False


async def crawl_events(page):
    url = "https://pokemon.wingzero.tw/zh-TW/data/pokemon-go-events"
    print(f"[events] fetching {url}")
    try:
        await page.goto(url, wait_until="networkidle", timeout=EVENT_TIMEOUT_MS)
    except Exception as e:
        print(f"ERROR: events page load failed — {e}", file=sys.stderr)
        return False

    html = await page.content()
    markers = ["go-event-live-card", "go-event-upcoming-card"]
    if not any(m in html for m in markers):
        print(f"ERROR: events markers not found ({len(html):,} bytes)", file=sys.stderr)
        return False

    with open("wingzero_events_real.html", "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"[events] ✓ {len(html):,} bytes saved")
    return True


async def crawl_news(page):
    url = "https://pokemon.wingzero.tw/zh-TW/news"
    print(f"[news]   fetching {url}")

    try:
        # networkidle: wait until page + images fully loaded
        # CF session cookie from events page should prevent new challenge
        await page.goto(url, wait_until="networkidle", timeout=NEWS_TIMEOUT_MS)
    except Exception as e:
        print(f"WARNING: news goto timed out, trying content grab anyway — {e}", file=sys.stderr)

    # Diagnostic: report what we actually loaded
    title      = await page.title()
    current_url = page.url
    print(f"[news]   url={current_url}")
    print(f"[news]   title={title!r}")

    # Handle CF challenge if still active
    if any(cf in title for cf in CF_TITLES):
        print(f"[news]   CF challenge detected — waiting up to 35 s…")
        resolved = await wait_for_cf(page)
        title = await page.title()
        print(f"[news]   after CF wait: resolved={resolved} title={title!r}")

    # Scroll to bottom to trigger lazy-loaded images / infinite scroll
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(2000)

    # Diagnostic: count relevant strings in raw HTML
    html = await page.content()
    n_news_links = html.count("/zh-TW/news/")
    n_img_tags   = html.count("<img")
    print(f"[news]   html={len(html):,} bytes | /zh-TW/news/ refs={n_news_links} | <img={n_img_tags}")

    if n_news_links == 0:
        print("WARNING: no news links found in page source — CF may still be blocking", file=sys.stderr)
        return False

    # Extract structured data from the live DOM
    items = await page.evaluate("""() => {
        const BASE  = 'https://pokemon.wingzero.tw';
        const fixUrl = u => {
            if (!u || u.startsWith('data:')) return '';
            if (u.startsWith('//')) return 'https:' + u;
            if (u.startsWith('/'))  return BASE + u;
            return u;
        };

        const seen  = new Set();
        const items = [];

        // All anchors pointing to an individual article
        const links = [...document.querySelectorAll('a[href]')].filter(a => {
            const h = a.getAttribute('href') || '';
            // match /zh-TW/news/<slug>  (not the listing page itself)
            return /\\/zh-TW\\/news\\/[^?#\\s]+/.test(h);
        });

        console.log('[eval] matched links:', links.length);

        for (const link of links) {
            const href     = link.getAttribute('href');
            const fullLink = href.startsWith('http') ? href : BASE + href;
            if (seen.has(fullLink)) continue;
            seen.add(fullLink);

            // Image: inside the anchor or its direct parent wrapper
            const imgEl = link.querySelector('img')
                       || link.parentElement?.querySelector('img');
            const imgSrc = imgEl
                ? (imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || '')
                : '';
            const image = fixUrl(imgSrc);

            // Title
            const titleEl = link.querySelector(
                'h1, h2, h3, h4, [class*="title"], [class*="name"], p'
            );
            let title = titleEl ? titleEl.textContent.trim() : '';
            if (!title) {
                const clone = link.cloneNode(true);
                clone.querySelectorAll('img, svg, [class*="tag"], [class*="badge"], time')
                     .forEach(el => el.remove());
                title = clone.textContent.trim().replace(/\\s+/g, ' ');
            }
            title = title.slice(0, 120);

            // Tag
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

    print(f"[news]   extracted {len(items)} items")

    if not items:
        print("WARNING: page loaded but 0 news items extracted", file=sys.stderr)
        return False

    with open("wingzero_news.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[news]   ✓ {len(items)} items → wingzero_news.json")
    return True


async def main():
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"=== WingZero crawler started {now_utc} ===")

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
        await stealth_async(page)   # patch headless fingerprints to bypass CF bot detection

        # Events first — establishes CF session cookie for the domain
        events_ok = await crawl_events(page)

        # News second — same session, CF cookie already present
        news_ok = await crawl_news(page)

        await browser.close()

    if not news_ok:
        print("WARNING: news crawl incomplete (non-critical)", file=sys.stderr)
    if not events_ok:
        print("FATAL: events crawl failed", file=sys.stderr)
        sys.exit(1)

    print("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
