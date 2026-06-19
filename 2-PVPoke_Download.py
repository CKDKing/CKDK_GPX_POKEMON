import asyncio
import csv
import os
import sys
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PwTimeoutError

sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_DIR = r"d:\AI Project\PVPCSV"
BASE_URL    = "https://pvpoketw.com/rankings/"

# ── Suffix classification sets ─────────────────────────────────────────────────
REGION_SET    = {'洗翠', '伽勒爾', '阿羅拉', '伽勒爾普通', '呼拉呼拉'}
FORM_TYPE_SET = {'化身', '靈獸', '起源', '覺悟', '完全體', '解放'}
SHADOW_SET    = {'暗影'}
MEGA_SET      = {'Mega', 'Mega X', 'Mega Y', '原始'}
GENDER_SET    = {'雌', '雄'}
SIZE_SET      = {'大尺寸', '特大尺寸', '小尺寸', '普通尺寸'}
WEATHER_SET   = {'晴', '雨', '雪', '結冰'}
OTHER_SET     = {
    '百戰勇者', '天空', '水瀾', '陸上', '一擊流', '連擊流', '火熾', '速度', '防禦',
    '草木', '盛開', '花苞', '砂土', '鬥戰', '拂曉之翼', '歌聲', '切割', '闇黑',
    '輕盈輕盈', '熱辣熱辣', '平常', '焰白', '盾之王', '劍之王', '閃電', '黃昏之鬃',
    '裝甲', '火焰', '水流', '別種', '平挺', '啪滋啪滋', '清洗', '一般', '上弓',
    '下垂', '加熱', '冰凍', '黑夜', '盾牌', '白晝', '黃昏', '旋轉', '普通',
    '滿腹花紋', '垃圾', '50%', '10%',
}

# Final column order
OUTPUT_COLUMNS = [
    '評分', '圖鑑編號', '寶可夢', '第一屬性', '第二屬性',
    '地區', '型態別', '暗影', 'Mega進化', '其他形態', '性別', '尺寸', '天氣',
    'CP', '攻擊力', '防禦力', 'HP', '等級',
    '一般招式', '特殊招式1', '特殊招式2', '幾下可用特招1', '幾下可用特招2',
    '夥伴行走距離', '開第二招星塵花費', 'Stat Product',
]

# ── CP 欄位修正 ────────────────────────────────────────────────────────────────
# 【已知來源問題】網站匯出的 CSV 第 K 欄標頭錯置：
#   原始標頭共 17 欄，但資料列實際有 18 欄。
#   原因是「等級」之後應有「CP」欄，網站漏寫該標頭，
#   導致 K 欄標頭顯示為「一般招式」（實際資料為 CP 數值），
#   後續 L～R 欄標頭全部錯位一格。
#
# 【修正方式】fix_cp_header() 偵測到舊標頭時，自動在「等級」後插入「CP」欄標頭。
#
# 【注意】若未來來源網站已修正欄位對齊（標頭與資料列欄數一致），
#         則 fix_cp_header() 的條件判斷不會觸發，無需移除此段邏輯。
RAW_HEADER = (
    "名稱,評分,圖鑑編號,第一屬性,第二屬性,攻擊力,防禦力,HP,Stat Product,"
    "等級,一般招式,特殊招式1,特殊招式2,幾下可用特招1,幾下可用特招2,夥伴行走距離,開第二招星塵花費"
)
FIXED_HEADER = (
    "名稱,評分,圖鑑編號,第一屬性,第二屬性,攻擊力,防禦力,HP,Stat Product,"
    "等級,CP,一般招式,特殊招式1,特殊招式2,幾下可用特招1,幾下可用特招2,夥伴行走距離,開第二招星塵花費"
)


# ── Helper functions ──────────────────────────────────────────────────────────

def parse_pokemon_name(full_name: str) -> dict:
    """Split 名稱 into structured columns."""
    parts = full_name.strip().split(' ')

    # Merge "Mega X" / "Mega Y" into a single token
    merged, i = [], 0
    while i < len(parts):
        if parts[i] == 'Mega' and i + 1 < len(parts) and parts[i + 1] in ('X', 'Y'):
            merged.append(f'Mega {parts[i + 1]}')
            i += 2
        else:
            merged.append(parts[i])
            i += 1

    result = {
        '寶可夢':  merged[0],
        '地區':    '-', '型態別':  '-', '暗影':    '-', 'Mega進化': '-',
        '其他形態': '-', '性別':    '-', '尺寸':    '-', '天氣':    '-',
    }
    for token in merged[1:]:
        if   token in SHADOW_SET:    result['暗影']    = token
        elif token in REGION_SET:    result['地區']    = token
        elif token in FORM_TYPE_SET: result['型態別']  = token
        elif token in MEGA_SET:      result['Mega進化'] = token
        elif token in GENDER_SET:    result['性別']    = token
        elif token in SIZE_SET:      result['尺寸']    = token
        elif token in WEATHER_SET:   result['天氣']    = token
        elif token in OTHER_SET:     result['其他形態'] = token
        else:
            print(f"  WARNING: unknown suffix '{token}' in '{full_name}'")
    return result


def fix_cp_header(path: str) -> None:
    """Insert missing CP column header if the raw (un-fixed) header is detected."""
    with open(path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    if lines[0].strip() == RAW_HEADER:
        lines[0] = FIXED_HEADER + '\n'
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            f.writelines(lines)


def process_csv(path: str) -> None:
    """Expand 名稱 into structured columns and reorder to OUTPUT_COLUMNS."""
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))

    new_rows = []
    for row in rows:
        parsed  = parse_pokemon_name(row['名稱'])
        merged  = {**row, **parsed}
        new_rows.append({col: merged.get(col, '-') for col in OUTPUT_COLUMNS})

    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        w.writeheader()
        w.writerows(new_rows)


def to_parquet(csv_path: str) -> None:
    """Convert a processed CSV to Parquet alongside the original file."""
    parquet_path = csv_path[:-4] + ".parquet"
    df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str)
    df.to_parquet(parquet_path, index=False)


def safe_filename(name: str) -> str:
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, '_')
    return name.strip()


# ── Download automation ────────────────────────────────────────────────────────

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context(accept_downloads=True)
        page    = await context.new_page()

        print("Opening rankings page…")
        await page.goto(BASE_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        fmt_sel  = page.locator(".format-select")
        options  = fmt_sel.locator("option")
        count    = await options.count()

        format_options = [(await options.nth(i).inner_text()).strip() for i in range(count)]

        print(f"Found {len(format_options)} format options:")
        for i, t in enumerate(format_options):
            print(f"  [{i}] {t}")

        for idx, fmt_text in enumerate(format_options):
            print(f"\n{'='*60}")
            print(f"[{idx+1}/{len(format_options)}] {fmt_text}")

            try:
                await page.goto(BASE_URL, wait_until="networkidle")
                await page.wait_for_timeout(1500)

                fmt_sel = page.locator(".format-select")
                try:
                    async with page.expect_navigation(wait_until="networkidle", timeout=8000):
                        await fmt_sel.select_option(index=idx)
                except PwTimeoutError:
                    await page.wait_for_timeout(3000)

                print(f"  URL: {page.url}")

                # Ensure category = overall
                cat_sel = page.locator(".category-select")
                try:
                    if await cat_sel.input_value() != "overall":
                        try:
                            async with page.expect_navigation(wait_until="networkidle", timeout=8000):
                                await cat_sel.select_option(value="overall")
                        except PwTimeoutError:
                            await page.wait_for_timeout(2000)
                except Exception as e:
                    print(f"  Warning (category): {e}")

                await page.wait_for_timeout(2000)

                dl_btn = page.locator(".download-csv")
                if await dl_btn.count() == 0 or not await dl_btn.is_visible():
                    print("  No download button – skipping")
                    continue

                async with page.expect_download(timeout=15000) as dl_info:
                    await dl_btn.click()

                download     = await dl_info.value
                original_name = download.suggested_filename or "rankings.csv"
                # Extract CP number from filename (e.g. "cp1500_all_..." → "1500")
                import re
                m = re.search(r'cp(\d+)_', original_name)
                cp_num   = m.group(1) if m else original_name
                new_name = safe_filename(f"{fmt_text} CP{cp_num}.csv")
                dest     = os.path.join(OUTPUT_DIR, new_name)
                await download.save_as(dest)

                # UTF-8 with BOM
                with open(dest, 'r', encoding='utf-8') as f:
                    content = f.read()
                with open(dest, 'w', encoding='utf-8-sig', newline='') as f:
                    f.write(content)

                fix_cp_header(dest)   # insert CP column if missing
                process_csv(dest)     # expand 名稱 + reorder columns
                to_parquet(dest)      # export .parquet alongside CSV

                print(f"  Saved → {new_name} + .parquet")

            except Exception as e:
                import traceback
                print(f"  ERROR: {e}")
                traceback.print_exc()

        print(f"\n{'='*60}")
        print(f"Finished! Files saved to: {OUTPUT_DIR}")
        await browser.close()


asyncio.run(main())
