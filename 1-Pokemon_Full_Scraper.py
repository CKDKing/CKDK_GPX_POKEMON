"""
寶可夢圖鑑完整爬蟲（含所有型態）0001~1025
每個代號自動嘗試 base、_1、_2、_3... 直到 404 為止
輸出：POKELIST.csv（欄位：代號, 名稱, 樣貌, 屬性, 弱點）
"""

import csv
import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 設定 ──────────────────────────────────────────────
BASE_URL   = "https://tw.portal-pokemon.com/play/pokedex/{}{}"
OUTPUT_FILE = "POKELIST.csv"
TEMP_FILE   = "POKELIST_full_progress.csv"
START, END  = 1, 1025
MAX_WORKERS = 5
DELAY       = 0.25   # 每次請求間隔（秒）
MAX_RETRIES = 3
MAX_FORMS   = 25     # 每個代號最多嘗試幾個 _N（超過此數視為無更多型態）
# ──────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9",
}
FIELDNAMES = ["代號", "名稱", "樣貌", "屬性", "弱點"]
print_lock = Lock()


def extract_form_keyword(subname: str, main_name: str) -> str:
    """從型態名稱中萃取關鍵字"""
    if subname:
        result = subname
        for suffix in ["的樣子", "形態", "樣子"]:
            if result.endswith(suffix):
                result = result[: -len(suffix)]
                break
        return result or subname
    # 沒有 subname → 直接以 main-name 為型態標籤（如「超級烈空坐」）
    return main_name


def fetch_one_url(url: str) -> requests.Response | None:
    """帶重試的 GET，回傳 Response 或 None（404/失敗）"""
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
    """從 Response 解析寶可夢資料"""
    soup = BeautifulSoup(r.text, "html.parser")

    # 代號
    no_el = soup.find("p", class_="pokemon-slider__main-no")
    if not no_el:
        return None
    poke_number = int(no_el.get_text(strip=True))

    # 名稱
    name_el = soup.find("p", class_="pokemon-slider__main-name")
    name = name_el.get_text(strip=True) if name_el else ""

    # 樣貌
    if not suffix:
        form = "一般"
    else:
        subname_el = soup.find("p", class_="pokemon-slider__main-subname")
        subname = subname_el.get_text(strip=True) if subname_el else ""
        form = extract_form_keyword(subname, name)

    # 屬性
    type_container = soup.find("div", class_="pokemon-type")
    types = []
    if type_container:
        for span in type_container.find_all("span"):
            t = span.get_text(strip=True)
            if t:
                types.append(t)

    # 弱點
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
    """爬取一個代號的所有型態（base + _1, _2, ...）"""
    poke_id = str(number).zfill(4)
    results = []

    # Base form
    url = BASE_URL.format(poke_id, "")
    r = fetch_one_url(url)
    if r:
        data = parse_pokemon_page(r, "")
        if data:
            results.append(data)

    # Alternate forms
    for idx in range(1, MAX_FORMS + 1):
        suffix = f"_{idx}"
        url = BASE_URL.format(poke_id, suffix)
        r = fetch_one_url(url)
        if r is None:
            break   # 404 → 此代號沒有更多型態
        data = parse_pokemon_page(r, suffix)
        if data:
            results.append(data)

    return results


def load_done_numbers(path: str) -> set[int]:
    """讀取已完成的代號（斷點續傳）"""
    done = set()
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
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows


def main():
    done_ids = load_done_numbers(TEMP_FILE)
    if done_ids:
        print(f"偵測到進度檔案，已完成 {len(done_ids)} 個代號，繼續上次進度...")

    todo = [n for n in range(START, END + 1) if n not in done_ids]
    total = len(todo)
    est_min = total * DELAY * 1.5 / MAX_WORKERS / 60
    print(f"待處理代號：{total} 個（含所有型態）")
    print(f"預計時間：約 {est_min:.1f} 分鐘\n")

    completed = 0
    failed = []

    progress_f = open(TEMP_FILE, "a", encoding="utf-8-sig", newline="")
    writer = csv.DictWriter(progress_f, fieldnames=FIELDNAMES)
    if not done_ids:
        writer.writeheader()

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
                    writer.writerow(row)
                progress_f.flush()
                with print_lock:
                    pct = completed / total * 100
                    forms_str = " + ".join(
                        f"{r['樣貌']}" for r in rows
                    )
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

    # 合併排序後輸出最終 CSV
    all_rows = load_all_rows(TEMP_FILE)
    all_rows.sort(key=lambda x: (int(x["代號"]), x["樣貌"] != "一般", x["樣貌"]))

    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n完成！共 {len(all_rows)} 筆（含所有型態）")
    print(f"輸出：{OUTPUT_FILE}")

    if failed:
        print(f"失敗代號（可重跑）：{failed}")
    elif len(done_ids) + total == END - START + 1:
        try:
            os.remove(TEMP_FILE)
            print("進度暫存已清除")
        except OSError:
            pass


if __name__ == "__main__":
    main()
