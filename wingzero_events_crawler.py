#!/usr/bin/env python3
"""
Daily crawler: fetches the Pokémon GO events page from pokemon.wingzero.tw
and saves it as wingzero_events_real.html for the GitHub Pages deployment.

GitHub Actions runs this at UTC 16:00 (= Taiwan 00:00) every day.
"""
import requests
import sys
from datetime import datetime, timezone

TARGET_URL = "https://pokemon.wingzero.tw/zh-TW/data/pokemon-go-events"
OUTPUT_FILE = "wingzero_events_real.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": "https://pokemon.wingzero.tw/",
}

REQUIRED_MARKERS = ["go-events-shell", "go-event-live-card", "go-event-upcoming-card"]

def main():
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{now_utc}] Fetching {TARGET_URL}")

    try:
        resp = requests.get(TARGET_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: Request failed — {e}", file=sys.stderr)
        sys.exit(1)

    html = resp.text

    # Validate that the response contains expected event elements
    found = [m for m in REQUIRED_MARKERS if m in html]
    if not found:
        print(
            f"ERROR: Response ({len(html)} bytes) missing all expected markers: {REQUIRED_MARKERS}",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    # Quick stats
    live_count = html.count('class="go-event-live-card"')
    upcoming_count = html.count('class="go-event-upcoming-card"')
    print(
        f"SUCCESS: {OUTPUT_FILE} updated — "
        f"{len(html):,} bytes | "
        f"ongoing={live_count} | upcoming={upcoming_count}"
    )

if __name__ == "__main__":
    main()
