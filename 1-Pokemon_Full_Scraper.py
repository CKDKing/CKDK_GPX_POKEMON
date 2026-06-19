"""
寶可夢圖鑑完整爬蟲 + 基礎數值補充（含所有型態）#0001~#1025

流程：
  1. 從台灣官方圖鑑爬取：代號、名稱、樣貌、屬性、弱點
  2. 從 pvpoke GitHub 取得各寶可夢 GO 基礎數值（ATK / DEF / HP）
  3. 用正確 CPM 表計算各等級最大 CP（LV15/20/25/40/50，15/15/15 IV）
  4. 輸出 PVPCSV/a.POKEMON LIST.csv（UTF-8 BOM）
  5. 同步輸出 PVPCSV/a.POKEMON LIST.parquet

CP 公式（simplified，與 db.pokemongohub.net 一致）：
  CP = floor((A+IV) × sqrt(D+IV) × sqrt(HP+IV) × CPM² / 10)
"""

import csv
import json
import math
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import requests
from bs4 import BeautifulSoup

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 路徑設定 ────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PVPCSV_DIR   = os.path.join(SCRIPT_DIR, "PVPCSV")
OUTPUT_CSV    = os.path.join(PVPCSV_DIR, "a.POKEMON LIST.csv")
OUTPUT_PARQUET= os.path.join(PVPCSV_DIR, "a.POKEMON LIST.parquet")
TEMP_FILE     = os.path.join(SCRIPT_DIR, "POKELIST_full_progress.csv")

# ── 爬蟲設定 ────────────────────────────────────────────
BASE_URL    = "https://tw.portal-pokemon.com/play/pokedex/{}{}"
START, END  = 1, 1025
MAX_WORKERS = 5
DELAY       = 0.25
MAX_RETRIES = 3
MAX_FORMS   = 25

# ── pvpoke 資料來源 ─────────────────────────────────────
PVPOKE_URL = (
    "https://raw.githubusercontent.com/pvpoke/pvpoke"
    "/master/src/data/gamemaster/pokemon.json"
)

# ── Pokémon GO CPM 表（L1~L50，步距 0.5，共 99 值）──────
# 來源：pogoapi.net/api/v1/cp_multiplier.json（L1-L45）
#        L45.5-L50 以 +0.0025/半等級外插（與官方一致）
CPM = [
    0.09399999678, 0.13513743,    0.16639787,    0.19265091,
    0.21573247,    0.23657265,    0.25572005,    0.27353038,
    0.29024988,    0.30605738,    0.32108760,    0.33544503,
    0.34921268,    0.36245774,    0.37523559,    0.38759241,
    0.39956728,    0.41119355,    0.42250001,    0.43292641,
    0.44310755,    0.45305995,    0.46279839,    0.47233608,
    0.48168495,    0.49085581,    0.49985844,    0.50870176,
    0.51739395,    0.52594251,    0.53435433,    0.54263576,
    0.55079269,    0.55883060,    0.56675452,    0.57456915,
    0.58227891,    0.58988791,    0.59740001,    0.60482366,
    0.61215729,    0.61940411,    0.62656713,    0.63364918,
    0.64065295,    0.64758097,    0.65443563,    0.66121927,
    0.66793400,    0.67458190,    0.68116492,    0.68768491,
    0.69414365,    0.70054290,    0.70688421,    0.71316910,
    0.71939909,    0.72557561,    0.73170000,    0.73474102,
    0.73776948,    0.74078558,    0.74378943,    0.74678122,
    0.74976104,    0.75272910,    0.75568551,    0.75863037,
    0.76156384,    0.76448607,    0.76739717,    0.77029727,
    0.77318650,    0.77606495,    0.77893275,    0.78179006,
    0.78463697,    0.78747358,    0.79030001,    0.79280001,
    0.79530001,    0.79780001,    0.80030000,    0.80280000,
    0.80530000,    0.80780000,    0.81029999,    0.81279999,
    0.81529999,    0.81779999,    0.82029999,    0.82279999,
    0.82529999,    0.82779999,    0.83029999,    0.83279999,
    0.83529999,    0.83779999,    0.84029999,
]  # index 0 = Lv1，每增 1 index = +0.5 等級

LV_IDX = {15: 28, 20: 38, 25: 48, 40: 78, 50: 98}

# 輸出欄位
BASE_FIELDS  = ["代號", "名稱", "樣貌", "屬性", "弱點"]
STAT_FIELDS  = ["ATK", "DEF", "HP",
                "LV15 (Research)", "LV20 (Raids/Eggs)",
                "LV25 (Weather Boost)", "LV40", "LV50"]
ALL_FIELDS   = BASE_FIELDS + STAT_FIELDS

# ── 中文型態 → pvpoke suffix 關鍵字映射 ─────────────────
FORM_KEYWORDS: dict[str, list[str]] = {
    "一般":  [],
    "超級":  ["mega"],
    "超級X": ["mega_x"],
    "超級Y": ["mega_y"],
    "阿羅拉":["alolan"],
    "伽勒爾":["galarian"],
    "帕底亞":["paldean"],
    "悠閒":  ["zen"],
    "原始":  ["primal", "origin"],
    "巨大":  ["gmax"],
}

print_lock = Lock()

# ══════════════════════════════════════════════════════════
# § 1  爬蟲（portal-pokemon.com）
# ══════════════════════════════════════════════════════════

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9",
}


def extract_form_keyword(subname: str, main_name: str) -> str:
    if subname:
        result = subname
        for suffix in ["的樣子", "形態", "樣子"]:
            if result.endswith(suffix):
                result = result[: -len(suffix)]
                break
        return result or subname
    return main_name


def fetch_one_url(url: str) -> requests.Response | None:
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(DELAY)
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r
        except requests.HTTPError:
            return None
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                with print_lock:
                    print(f"  [!] 請求失敗 {url}: {e}")
                return None
    return None


def parse_pokemon_page(r: requests.Response, suffix: str) -> dict | None:
    soup = BeautifulSoup(r.text, "html.parser")

    no_el = soup.find("p", class_="pokemon-slider__main-no")
    if not no_el:
        return None
    poke_number = int(no_el.get_text(strip=True))

    name_el = soup.find("p", class_="pokemon-slider__main-name")
    name = name_el.get_text(strip=True) if name_el else ""

    if not suffix:
        form = "一般"
    else:
        subname_el = soup.find("p", class_="pokemon-slider__main-subname")
        subname = subname_el.get_text(strip=True) if subname_el else ""
        form = extract_form_keyword(subname, name)

    type_container = soup.find("div", class_="pokemon-type")
    types = []
    if type_container:
        for span in type_container.find_all("span"):
            t = span.get_text(strip=True)
            if t:
                types.append(t)

    weak_container = soup.find("div", class_="pokemon-weakness__items")
    weaknesses = []
    if weak_container:
        for btn in weak_container.find_all("div", class_="pokemon-weakness__btn"):
            span = btn.find("span")
            if span:
                w = span.get_text(strip=True)
                if w:
                    weaknesses.append(w)

    return {
        "代號": poke_number,
        "名稱": name,
        "樣貌": form,
        "屬性": "|".join(types),
        "弱點": "|".join(weaknesses),
    }


def scrape_all_forms(number: int) -> list[dict]:
    poke_id = str(number).zfill(4)
    results = []

    url = BASE_URL.format(poke_id, "")
    r = fetch_one_url(url)
    if r:
        data = parse_pokemon_page(r, "")
        if data:
            results.append(data)

    for idx in range(1, MAX_FORMS + 1):
        suffix = f"_{idx}"
        url = BASE_URL.format(poke_id, suffix)
        r = fetch_one_url(url)
        if r is None:
            break
        data = parse_pokemon_page(r, suffix)
        if data:
            results.append(data)

    return results


def load_done_numbers(path: str) -> set[int]:
    done: set[int] = set()
    if not os.path.exists(path):
        return done
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                done.add(int(row["代號"]))
            except (KeyError, ValueError):
                pass
    return done


def load_all_rows(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ══════════════════════════════════════════════════════════
# § 2  基礎數值補充（pvpoke → ATK/DEF/HP + CP）
# ══════════════════════════════════════════════════════════

def calc_cp(atk: int, def_: int, hp: int, cpm: float, iv: int = 15) -> int:
    """Simplified formula (matches db.pokemongohub.net Max CP display)."""
    a = (atk + iv) * cpm
    d = (def_ + iv) * cpm
    h = (hp  + iv) * cpm
    return max(10, math.floor(a * math.sqrt(d) * math.sqrt(h) / 10))


def fetch_pvpoke_lookup() -> dict[int, list[dict]]:
    """
    回傳 {dex: [{suffix, atk, def, hp, id}, ...]}
    suffix 為 speciesId 去掉首個 '_' 前的部分（e.g. "mega", "alolan", ""）
    """
    print("  ▸ 從 pvpoke GitHub 取得基礎數值...")
    with urllib.request.urlopen(PVPOKE_URL, timeout=30) as resp:
        data = json.load(resp)

    lookup: dict[int, list[dict]] = {}
    for pk in data:
        dex = pk.get("dex")
        if not dex:
            continue
        bs  = pk.get("baseStats", {})
        sid = pk.get("speciesId", "")
        sfx = sid.split("_", 1)[1] if "_" in sid else ""
        lookup.setdefault(dex, []).append({
            "suffix": sfx,
            "atk": bs.get("atk", 0),
            "def": bs.get("def", 0),
            "hp":  bs.get("hp",  0),
            "id":  sid,
        })

    print(f"  ▸ 載入 {len(lookup)} 個代號的基礎數值")
    return lookup


def get_base_stats(
    lookup: dict[int, list[dict]],
    dex: int,
    form_zh: str,
) -> tuple[int, int, int] | tuple[None, None, None]:
    entries = lookup.get(dex, [])
    if not entries:
        return None, None, None

    pool = [e for e in entries if "shadow" not in e["suffix"]] or entries
    keywords = FORM_KEYWORDS.get(form_zh, [])

    if keywords:
        for kw in keywords:
            for e in pool:
                if kw in e["suffix"]:
                    return e["atk"], e["def"], e["hp"]

    # 預設：回傳基礎型態（suffix 為空的第一筆）
    for e in pool:
        if e["suffix"] == "":
            return e["atk"], e["def"], e["hp"]
    return pool[0]["atk"], pool[0]["def"], pool[0]["hp"]


def enrich_rows(rows: list[dict]) -> list[dict]:
    """在爬蟲資料列上補充 ATK/DEF/HP 及各等級最大 CP。"""
    try:
        lookup = fetch_pvpoke_lookup()
    except Exception as e:
        print(f"  [!] 無法取得 pvpoke 資料，基礎數值欄位留空：{e}")
        for row in rows:
            for f in STAT_FIELDS:
                row[f] = ""
        return rows

    missing = 0
    for row in rows:
        dex  = int(row["代號"])
        form = row["樣貌"]
        atk, def_, hp = get_base_stats(lookup, dex, form)

        if atk is None:
            missing += 1
            for f in STAT_FIELDS:
                row[f] = ""
            continue

        row["ATK"] = atk
        row["DEF"] = def_
        row["HP"]  = hp
        row["LV15 (Research)"]    = calc_cp(atk, def_, hp, CPM[LV_IDX[15]])
        row["LV20 (Raids/Eggs)"]  = calc_cp(atk, def_, hp, CPM[LV_IDX[20]])
        row["LV25 (Weather Boost)"]= calc_cp(atk, def_, hp, CPM[LV_IDX[25]])
        row["LV40"]               = calc_cp(atk, def_, hp, CPM[LV_IDX[40]])
        row["LV50"]               = calc_cp(atk, def_, hp, CPM[LV_IDX[50]])

    if missing:
        print(f"  [!] {missing} 筆找不到基礎數值（已留空）")
    return rows


# ══════════════════════════════════════════════════════════
# § 3  輸出（CSV + Parquet）
# ══════════════════════════════════════════════════════════

def save_csv(rows: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ▸ CSV  → {path}")


def save_parquet(csv_path: str, parquet_path: str) -> None:
    if not HAS_PANDAS:
        print("  [!] 未安裝 pandas/pyarrow，略過 Parquet 輸出")
        return
    import pandas as pd
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    int_cols = ["ATK","DEF","HP",
                "LV15 (Research)","LV20 (Raids/Eggs)",
                "LV25 (Weather Boost)","LV40","LV50"]
    for c in int_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    df.to_parquet(parquet_path, index=False, engine="pyarrow")
    print(f"  ▸ Parquet → {parquet_path}")


# ══════════════════════════════════════════════════════════
# § 4  主程式
# ══════════════════════════════════════════════════════════

def main() -> None:
    os.makedirs(PVPCSV_DIR, exist_ok=True)

    # ── Phase 1：爬蟲 ──────────────────────────────────────
    done_ids = load_done_numbers(TEMP_FILE)
    if done_ids:
        print(f"偵測到進度檔案，已完成 {len(done_ids)} 個代號，繼續上次進度...")

    todo = [n for n in range(START, END + 1) if n not in done_ids]
    total = len(todo)
    est_min = total * DELAY * 1.5 / MAX_WORKERS / 60
    print(f"待處理代號：{total} 個（含所有型態）")
    print(f"預計時間：約 {est_min:.1f} 分鐘\n")

    completed = 0
    failed: list[int] = []

    progress_f = open(TEMP_FILE, "a", encoding="utf-8-sig", newline="")
    progress_writer = csv.DictWriter(progress_f, fieldnames=BASE_FIELDS)
    if not done_ids:
        progress_writer.writeheader()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scrape_all_forms, n): n for n in todo}

        for future in as_completed(futures):
            n = futures[future]
            completed += 1
            try:
                rows = future.result()
            except Exception as e:
                with print_lock:
                    print(f"  [X] #{n} 發生例外: {e}")
                failed.append(n)
                continue

            if rows:
                for row in rows:
                    progress_writer.writerow(row)
                progress_f.flush()
                with print_lock:
                    pct = completed / total * 100
                    forms_str = " + ".join(r["樣貌"] for r in rows)
                    print(
                        f"  [{completed:4d}/{total}] {pct:5.1f}%"
                        f"  #{n:4d} {rows[0]['名稱']:8s}"
                        f"  [{len(rows)} 型態] {forms_str}"
                    )
            else:
                with print_lock:
                    print(f"  [!] #{n} 無資料")
                failed.append(n)

    progress_f.close()

    # ── Phase 2：排序 + 補充基礎數值 ───────────────────────
    print("\n── 補充基礎數值（ATK / DEF / HP / CP）──")
    all_rows = load_all_rows(TEMP_FILE)
    all_rows.sort(key=lambda x: (int(x["代號"]), x["樣貌"] != "一般", x["樣貌"]))
    all_rows = enrich_rows(all_rows)

    # ── Phase 3：輸出 ───────────────────────────────────────
    print("\n── 輸出檔案 ──")
    save_csv(all_rows, OUTPUT_CSV)
    save_parquet(OUTPUT_CSV, OUTPUT_PARQUET)

    total_rows = len(all_rows)
    print(f"\n完成！共 {total_rows} 筆（含所有型態）")

    if failed:
        print(f"失敗代號（可重跑）：{failed}")
    elif len(done_ids) + len(todo) == END - START + 1:
        try:
            os.remove(TEMP_FILE)
            print("進度暫存已清除")
        except OSError:
            pass


if __name__ == "__main__":
    main()
