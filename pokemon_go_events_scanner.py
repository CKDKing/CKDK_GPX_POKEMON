#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pokémon GO Regional Events Scanner
掃描 16 個地區 Pokémon GO 官網，找出地區限定活動（排除全球性活動）
輸出：pokemon_go_events.json  &  pokemon_go_events.md
Log ：pokemon_go_events_scanner_log.txt（每次執行追加，日期記錄在內）
"""

import io
import json
import logging
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

# Windows 終端 UTF-8 相容
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ──────────────────────────────────────────────────────────────────────────────
# 設定常數
# ──────────────────────────────────────────────────────────────────────────────

BASE_URL        = "https://pokemongo.com"
REQUEST_DELAY   = 2.0   # 兩次請求間隔秒數（避免被封）
REQUEST_TIMEOUT = 20    # 連線逾時
MAX_RETRIES     = 3     # 失敗重試次數

# 若文章出現在 < REGIONAL_THRESHOLD 個地區 → 視為地區限定
# 全球活動通常出現在全部 16 個地區
REGIONAL_THRESHOLD = 4

REGIONS: List[Dict] = [
    {"code": "zh_hant", "name": "台灣",     "flag": "🇹🇼", "lang": "zh-TW"},
    {"code": "ja",      "name": "日本",     "flag": "🇯🇵", "lang": "ja"},
    {"code": "ko",      "name": "韓國",     "flag": "🇰🇷", "lang": "ko"},
    {"code": "th",      "name": "泰國",     "flag": "🇹🇭", "lang": "th"},
    {"code": "id",      "name": "印尼",     "flag": "🇮🇩", "lang": "id"},
    {"code": "hi",      "name": "印度",     "flag": "🇮🇳", "lang": "hi"},
    {"code": "pt_br",   "name": "巴西",     "flag": "🇧🇷", "lang": "pt"},
    {"code": "es_mx",   "name": "拉丁美洲", "flag": "🌎",  "lang": "es"},
    {"code": "en",      "name": "英文",     "flag": "🇺🇸", "lang": "en"},
    {"code": "fr",      "name": "法國",     "flag": "🇫🇷", "lang": "fr"},
    {"code": "de",      "name": "德國",     "flag": "🇩🇪", "lang": "de"},
    {"code": "it",      "name": "義大利",   "flag": "🇮🇹", "lang": "it"},
    {"code": "es",      "name": "西班牙",   "flag": "🇪🇸", "lang": "es"},
    {"code": "pl",      "name": "波蘭",     "flag": "🇵🇱", "lang": "pl"},
    {"code": "ru",      "name": "俄羅斯",   "flag": "🇷🇺", "lang": "ru"},
    {"code": "tr",      "name": "土耳其",   "flag": "🇹🇷", "lang": "tr"},
]

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

# ──────────────────────────────────────────────────────────────────────────────
# 路徑
# ──────────────────────────────────────────────────────────────────────────────

ROOT        = Path(__file__).parent
TODAY_STR   = datetime.now().strftime("%Y-%m-%d")
LOG_FILE    = ROOT / "pokemon_go_events_scanner_log.txt"
JSON_OUTPUT = ROOT / "pokemon_go_events.json"
MD_OUTPUT   = ROOT / "pokemon_go_events.md"

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    logger = logging.getLogger("pogo_scanner")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Append 模式：每次執行追加，日期自動記錄在 log 內
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    # 每次執行寫入分隔線，方便在 log 中區分不同日期的掃描
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'─'*65}\n")
        f.write(f"  掃描開始：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'─'*65}\n")

    return logger

# ──────────────────────────────────────────────────────────────────────────────
# HTTP
# ──────────────────────────────────────────────────────────────────────────────

def fetch_html(url: str, log: logging.Logger) -> Optional[str]:
    """抓取 HTML，失敗自動重試。"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                log.debug(f"    OK {len(resp.text):,} chars : {url}")
                return resp.text
            log.warning(f"    HTTP {resp.status_code} [{attempt}/{MAX_RETRIES}] : {url}")
        except requests.RequestException as exc:
            log.warning(f"    Error [{attempt}/{MAX_RETRIES}] {exc} : {url}")
        if attempt < MAX_RETRIES:
            time.sleep(2 * attempt)
    log.error(f"    給予放棄 : {url}")
    return None

# ──────────────────────────────────────────────────────────────────────────────
# Slug 擷取
# ──────────────────────────────────────────────────────────────────────────────

_SLUG_RE = re.compile(r"/news/([a-z0-9][a-z0-9_\-]{2,80})(?:[/?#]|$)", re.IGNORECASE)

def extract_slugs(html: str) -> Dict[str, str]:
    """從新聞列表頁擷取 {slug: title}。"""
    soup = BeautifulSoup(html, "lxml")
    slugs: Dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        m = _SLUG_RE.search(a["href"])
        if m:
            slug = m.group(1).lower()
            if slug not in slugs:
                title = a.get_text(" ", strip=True)
                slugs[slug] = title[:200] if title else slug
    return slugs

# ──────────────────────────────────────────────────────────────────────────────
# 日期解析（多語言）
# ──────────────────────────────────────────────────────────────────────────────

# 日文・繁中：2026年6月23日
_CJK = re.compile(r"(202[6-9])年\s*(\d{1,2})月\s*(\d{1,2})日")
# 韓文：2026년 7월 11일
_KO  = re.compile(r"(202[6-9])년\s*(\d{1,2})월\s*(\d{1,2})일")
# ISO / 斜線：2026-06-23 or 2026/06/23
_ISO = re.compile(r"\b(202[6-9])[\/\-](\d{1,2})[\/\-](\d{1,2})\b")
# 英文月份：June 23, 2026 / 23 June 2026
_MONTHS_EN = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,
    "sep":9,"oct":10,"nov":11,"dec":12,
}
_EN_DATE1 = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2}),?\s+(202[6-9])\b",
    re.IGNORECASE,
)
_EN_DATE2 = re.compile(
    r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(202[6-9])\b",
    re.IGNORECASE,
)


def _regex_dates(text: str) -> List[date]:
    found: List[date] = []

    for y, m, d in _CJK.findall(text) + _KO.findall(text) + _ISO.findall(text):
        try:
            found.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass

    for mo_str, day, year in _EN_DATE1.findall(text):
        mo = _MONTHS_EN.get(mo_str.lower())
        if mo:
            try:
                found.append(date(int(year), mo, int(day)))
            except ValueError:
                pass

    for day, mo_str, year in _EN_DATE2.findall(text):
        mo = _MONTHS_EN.get(mo_str.lower())
        if mo:
            try:
                found.append(date(int(year), mo, int(day)))
            except ValueError:
                pass

    return found


def _dateparser_dates(text: str, lang: str) -> List[date]:
    """使用 dateparser 作為補充（若已安裝）。"""
    try:
        from dateparser.search import search_dates
        lang_code = lang.split("-")[0]
        results = search_dates(
            text[:6000],
            languages=[lang_code, "en"],
            settings={
                "STRICT_PARSING": True,
                "REQUIRE_PARTS": ["day", "month", "year"],
                "PREFER_DATES_FROM": "future",
            },
        ) or []
        return [dt.date() for _, dt in results if 2026 <= dt.year <= 2027]
    except Exception:
        return []


def extract_dates(
    html: str, lang: str, log: logging.Logger
) -> Tuple[Optional[date], Optional[date]]:
    """
    從文章 HTML 擷取 (start_date, end_date)。
    優先用正則，再試 dateparser，找不到回傳 (None, None)。
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)

    dates = sorted(set(_regex_dates(text)))
    method = "regex"

    if not dates:
        dates = sorted(set(_dateparser_dates(text, lang)))
        method = "dateparser"

    if not dates:
        log.debug("    ❌ 找不到日期")
        return None, None

    start = dates[0]
    end   = dates[-1] if len(dates) > 1 else None
    log.debug(f"    📅 [{method}] {start} → {end}  (共 {len(dates)} 個日期)")
    return start, end

# ──────────────────────────────────────────────────────────────────────────────
# 狀態判斷
# ──────────────────────────────────────────────────────────────────────────────

def event_status(start: Optional[date], end: Optional[date]) -> str:
    today = date.today()
    if start is None:
        return "unknown"
    if end and today > end:
        return "ended"
    if today >= start:
        return "active"
    return "upcoming"

# ──────────────────────────────────────────────────────────────────────────────
# 主掃描流程
# ──────────────────────────────────────────────────────────────────────────────

def scan(log: logging.Logger) -> List[Dict]:

    # ── Phase 1：蒐集各地區 news 頁的文章 slug ────────────────────
    log.info("=" * 65)
    log.info(f"  Pokémon GO Regional Events Scanner  |  {TODAY_STR}")
    log.info(f"  掃描 {len(REGIONS)} 個地區  |  REGIONAL_THRESHOLD = {REGIONAL_THRESHOLD}")
    log.info("=" * 65)
    log.info("【Phase 1】蒐集各地區新聞頁文章 slug")

    slug_regions: Dict[str, set]  = defaultdict(set)   # slug → {region_codes}
    slug_title:   Dict[str, str]  = {}                  # slug → title (首次出現)

    for region in REGIONS:
        code = region["code"]
        url  = f"{BASE_URL}/{code}/news"
        log.info(f"  {region['flag']} {region['name']:<8}  →  {url}")
        html = fetch_html(url, log)
        time.sleep(REQUEST_DELAY)

        if html:
            slugs = extract_slugs(html)
            log.info(f"    找到 {len(slugs)} 篇文章")
            for slug, title in slugs.items():
                slug_regions[slug].add(code)
                if slug not in slug_title:
                    slug_title[slug] = title
        else:
            log.warning(f"    無法取得內容，跳過")

    log.info(f"\n  不重複 slug 總計：{len(slug_regions)}")

    # ── Phase 2：篩選地區限定 ─────────────────────────────────────
    log.info(f"\n【Phase 2】篩選地區限定 slug（出現 < {REGIONAL_THRESHOLD} 個地區）")

    regional_slugs: Dict[str, Dict] = {}
    global_count = 0

    for slug, regions in slug_regions.items():
        if len(regions) < REGIONAL_THRESHOLD:
            regional_slugs[slug] = {
                "title":   slug_title.get(slug, slug),
                "regions": sorted(regions),
                "count":   len(regions),
            }
            log.debug(f"  ✓ [{len(regions):2d}地區] {slug}")
        else:
            global_count += 1
            log.debug(f"  ✗ [{len(regions):2d}地區] {slug}  ← 全球性，略過")

    log.info(f"  地區限定：{len(regional_slugs)} 篇  |  全球性：{global_count} 篇")

    # ── Phase 3：逐篇抓取，解析標題與日期 ────────────────────────
    log.info(f"\n【Phase 3】抓取地區限定文章，解析日期")

    events: List[Dict] = []

    for slug, info in regional_slugs.items():
        for region_code in info["regions"]:
            region = next(r for r in REGIONS if r["code"] == region_code)
            url    = f"{BASE_URL}/{region_code}/news/{slug}"

            log.info(f"\n  {region['flag']} {region['name']}  /  {slug}")
            html = fetch_html(url, log)
            time.sleep(REQUEST_DELAY)

            title      = info["title"]
            start_date = None
            end_date   = None

            if html:
                soup = BeautifulSoup(html, "lxml")
                h1 = soup.find("h1")
                if h1:
                    t = h1.get_text(" ", strip=True)
                    if t:
                        title = t
                start_date, end_date = extract_dates(html, region["lang"], log)

            status = event_status(start_date, end_date)
            log.info(f"    標題  : {title[:60]}")
            log.info(f"    日期  : {start_date} → {end_date}  |  狀態：{status}")

            if status == "ended":
                log.info("    ⏭  已結束，跳過")
                continue

            events.append({
                "region":            f"{region['flag']} {region['name']}",
                "region_code":       region_code,
                "event_name":        title,
                "start_date":        start_date.isoformat() if start_date else None,
                "end_date":          end_date.isoformat()   if end_date   else None,
                "status":            status,
                "url":               url,
                "article_slug":      slug,
                "found_in_regions":  info["regions"],
            })

    # 排序：進行中 → 即將開始 → 未知；同層再按起始日
    ORDER = {"active": 0, "upcoming": 1, "unknown": 2}
    events.sort(key=lambda e: (
        ORDER.get(e["status"], 3),
        e["start_date"] or "9999-99-99",
    ))

    log.info(f"\n  最終有效地區限定活動：{len(events)} 筆")
    return events

# ──────────────────────────────────────────────────────────────────────────────
# 輸出 JSON
# ──────────────────────────────────────────────────────────────────────────────

def write_json(events: List[Dict], log: logging.Logger):
    payload = {
        "scan_timestamp": datetime.now().isoformat(),
        "scan_date":      TODAY_STR,
        "total":          len(events),
        "events":         events,
    }
    JSON_OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(f"  JSON  → {JSON_OUTPUT.name}")

# ──────────────────────────────────────────────────────────────────────────────
# 輸出 Markdown
# ──────────────────────────────────────────────────────────────────────────────

_STATUS_LABEL = {
    "active":   "✅ 進行中",
    "upcoming": "🔜 即將開始",
    "unknown":  "❓ 日期未知",
}


def write_markdown(events: List[Dict], log: logging.Logger):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if events:
        rows = []
        for e in events:
            label = _STATUS_LABEL.get(e["status"], e["status"])
            start = e["start_date"] or "—"
            end   = e["end_date"]   or "—"
            name  = e["event_name"][:65]
            link  = f"[🔗]({e['url']})"
            rows.append(
                f"| {e['region']} | {name} | {start} | {end} | {label} | {link} |"
            )
        table_body = "\n".join(rows)
    else:
        table_body = "| — | 目前無地區限定活動 | — | — | — | — |"

    md = f"""\
# 🗺️ Pokémon GO 地區限定活動

> 掃描時間：**{now}**（台灣時間）
> 僅顯示地區限定活動，已結束的不列入
> 全球性共同活動不列入

| 地區 | 活動名稱 | 起點 | 終點 | 狀態 | 網頁 |
| ---- | -------- | :--: | :--: | :--: | :--: |
{table_body}

---
*每日 05:00 台灣時間自動掃描 · 原始資料：[pogo_events.json](pogo_events.json)*
"""
    MD_OUTPUT.write_text(md, encoding="utf-8")
    log.info(f"  MD    → {MD_OUTPUT.name}")

# ──────────────────────────────────────────────────────────────────────────────
# Console 摘要表
# ──────────────────────────────────────────────────────────────────────────────

def print_summary(events: List[Dict]):
    W = 90
    print(f"\n{'═'*W}")
    print(f"  {'地區':<14} {'狀態':<10} {'起點':<12} {'終點':<12} 活動名稱")
    print(f"{'─'*W}")
    for e in events:
        print(
            f"  {e['region']:<14} "
            f"{e['status']:<10} "
            f"{(e['start_date'] or '—'):<12} "
            f"{(e['end_date']   or '—'):<12} "
            f"{e['event_name'][:32]}"
        )
    print(f"{'═'*W}")
    print(f"  共 {len(events)} 筆地區限定活動\n")

# ──────────────────────────────────────────────────────────────────────────────
# 進入點
# ──────────────────────────────────────────────────────────────────────────────

def main():
    log = setup_logging()
    log.info("Pokémon GO Events Scanner 啟動")

    try:
        events = scan(log)
        log.info("\n【輸出結果】")
        write_json(events, log)
        write_markdown(events, log)
        print_summary(events)
        log.info("✅ 掃描完成")
        sys.exit(0)
    except KeyboardInterrupt:
        log.warning("使用者中斷")
        sys.exit(1)
    except Exception as exc:
        log.exception(f"Fatal error: {exc}")
        sys.exit(2)


if __name__ == "__main__":
    main()
