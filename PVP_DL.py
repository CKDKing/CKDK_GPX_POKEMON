"""
PVP_DL.py  —  PVPoke 台版資料自動下載器
來源：https://pvpoketw.com/rankings/
輸出：PVPData/  （與本腳本同一目錄，即 repo 根目錄）

用法：
  python PVP_DL.py              掃描；偵測到新版本才下載
  python PVP_DL.py --force      強制重新下載（版本相同也執行）
  python PVP_DL.py --check      只查更新時間，不下載
  python PVP_DL.py --visible    顯示瀏覽器視窗（除錯用）
  python PVP_DL.py --no-git     跳過 git commit（GitHub Actions 使用）

Exit code：
  0   — 無動作（skip / init / check / error）
  10  — 下載成功（GitHub Actions 以此判斷是否需要 commit）

流程：
  [1] 確認時間   — 讀取首頁「中文版最後更新時間」
  [2] 確認 LOG   — 比對上次記錄；決定是否下載
  [3] 下載 + 處理 — 下載所有 Format CSV；修正欄位；展開名稱欄
  [4] 輸出雙格式 — 每個 CSV 同時輸出 .csv（UTF-8 BOM）+ .parquet
  [5] Git commit  — stage PVPData/ 並 commit（本機用；Actions 用 --no-git 跳過）
"""

import asyncio
import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PwTimeout

sys.stdout.reconfigure(encoding="utf-8")

# ── 路徑（相對腳本位置；clone 到任何目錄都能用）──────────────────────────────
REPO_DIR    = Path(__file__).parent
PVPDATA_DIR = REPO_DIR / "PVPData"
LOG_FILE    = PVPDATA_DIR / "pvpoke_log.json"
HOMEPAGE    = "https://pvpoketw.com/"
RANKINGS    = "https://pvpoketw.com/rankings/"

_UPDATE_RE  = re.compile(r'中文版最後更新時間[：:]\s*([^\n\r<]+)')

# ── 形態後綴分類集合 ──────────────────────────────────────────────────────────
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

OUTPUT_COLUMNS = [
    '評分', '圖鑑編號', '寶可夢', '第一屬性', '第二屬性',
    '地區', '型態別', '暗影', 'Mega進化', '其他形態', '性別', '尺寸', '天氣',
    'CP', '攻擊力', '防禦力', 'HP', '等級',
    '一般招式', '特殊招式1', '特殊招式2', '幾下可用特招1', '幾下可用特招2',
    '夥伴行走距離', '開第二招星塵花費', 'Stat Product',
]

# 網站原始標頭（缺 CP 欄）與修正後標頭
_RAW_HEADER = (
    "名稱,評分,圖鑑編號,第一屬性,第二屬性,攻擊力,防禦力,HP,Stat Product,"
    "等級,一般招式,特殊招式1,特殊招式2,幾下可用特招1,幾下可用特招2,夥伴行走距離,開第二招星塵花費"
)
_FIXED_HEADER = (
    "名稱,評分,圖鑑編號,第一屬性,第二屬性,攻擊力,防禦力,HP,Stat Product,"
    "等級,CP,一般招式,特殊招式1,特殊招式2,幾下可用特招1,幾下可用特招2,夥伴行走距離,開第二招星塵花費"
)


# ══════════════════════════════════════════════════════════════════════════════
#  LOG
# ══════════════════════════════════════════════════════════════════════════════

def load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return {"last_known_update": None, "last_download": None, "history": []}


def save_log(data: dict) -> None:
    PVPDATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  LOG → {LOG_FILE}")


def now_str() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — 確認時間：讀取首頁「中文版最後更新時間」
# ══════════════════════════════════════════════════════════════════════════════

async def fetch_update_time() -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page    = await browser.new_page()
        try:
            await page.goto(HOMEPAGE, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            body = await page.inner_text("body")
        finally:
            await browser.close()
    m = _UPDATE_RE.search(body)
    return m.group(1).strip() if m else None


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — 下載 + 資料處理
# ══════════════════════════════════════════════════════════════════════════════

def _safe_filename(name: str) -> str:
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, '_')
    return name.strip()


def _parse_name(full_name: str) -> dict:
    parts = full_name.strip().split(' ')
    merged, i = [], 0
    while i < len(parts):
        if parts[i] == 'Mega' and i + 1 < len(parts) and parts[i + 1] in ('X', 'Y'):
            merged.append(f'Mega {parts[i + 1]}')
            i += 2
        else:
            merged.append(parts[i])
            i += 1

    result = {
        '寶可夢': merged[0],
        '地區': '-', '型態別': '-', '暗影': '-', 'Mega進化': '-',
        '其他形態': '-', '性別': '-', '尺寸': '-', '天氣': '-',
    }
    for token in merged[1:]:
        if   token in SHADOW_SET:    result['暗影']     = token
        elif token in REGION_SET:    result['地區']     = token
        elif token in FORM_TYPE_SET: result['型態別']   = token
        elif token in MEGA_SET:      result['Mega進化'] = token
        elif token in GENDER_SET:    result['性別']     = token
        elif token in SIZE_SET:      result['尺寸']     = token
        elif token in WEATHER_SET:   result['天氣']     = token
        elif token in OTHER_SET:     result['其他形態'] = token
        else:
            print(f"    WARNING: 未知後綴 '{token}' in '{full_name}'")
    return result


def _fix_cp_header(path: Path) -> None:
    lines = path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
    if lines and lines[0].strip() == _RAW_HEADER:
        lines[0] = _FIXED_HEADER + '\n'
        path.write_text(''.join(lines), encoding="utf-8-sig")


def _process_csv(path: Path) -> None:
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    new_rows = []
    for row in rows:
        parsed = _parse_name(row['名稱'])
        merged = {**row, **parsed}
        new_rows.append({col: merged.get(col, '-') for col in OUTPUT_COLUMNS})
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        w.writeheader()
        w.writerows(new_rows)


def _to_parquet(csv_path: Path) -> None:
    df = pd.read_csv(csv_path, encoding='utf-8-sig', dtype=str)
    df.to_parquet(csv_path.with_suffix('.parquet'), index=False)


def _parse_date_str(update_time: str) -> str:
    """'Wed Jun 17 18:55:06 2026 +0800'  →  '20260617'"""
    try:
        dt = datetime.strptime(update_time.strip(), "%a %b %d %H:%M:%S %Y %z")
        return dt.strftime("%Y%m%d")
    except ValueError:
        return ""


def cleanup_old_versions(keep: int = 3) -> None:
    """PVPData/ 內只保留最新 keep 個日期版本，刪除更舊的 CSV + parquet。"""
    date_re = re.compile(r' (\d{8})\.(csv|parquet)$')

    dates: set[str] = set()
    for f in PVPDATA_DIR.iterdir():
        m = date_re.search(f.name)
        if m:
            dates.add(m.group(1))

    if len(dates) <= keep:
        return

    sorted_dates  = sorted(dates, reverse=True)   # 最新在前
    old_dates     = set(sorted_dates[keep:])       # 第 keep+1 之後的全刪

    deleted = []
    for f in PVPDATA_DIR.iterdir():
        m = date_re.search(f.name)
        if m and m.group(1) in old_dates:
            f.unlink()
            deleted.append(f.name)

    if deleted:
        print(f"\n  [汰舊] 刪除 {len(deleted)} 個檔案（版本：{sorted(old_dates)}）")
        for name in sorted(deleted):
            print(f"    - {name}")


async def download_and_process(date_str: str, visible: bool = False) -> bool:
    PVPDATA_DIR.mkdir(parents=True, exist_ok=True)
    all_ok = True

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not visible,
            slow_mo=200 if visible else 0
        )
        context = await browser.new_context(accept_downloads=True)
        page    = await context.new_page()

        await page.goto(RANKINGS, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        options  = page.locator(".format-select option")
        count    = await options.count()
        fmt_list = [(await options.nth(i).inner_text()).strip() for i in range(count)]
        print(f"  找到 {len(fmt_list)} 個 Format")

        for idx, fmt_text in enumerate(fmt_list):
            print(f"\n  [{idx+1}/{len(fmt_list)}] {fmt_text}")
            try:
                await page.goto(RANKINGS, wait_until="networkidle")
                await page.wait_for_timeout(1500)

                fmt_sel = page.locator(".format-select")
                try:
                    async with page.expect_navigation(wait_until="networkidle", timeout=8000):
                        await fmt_sel.select_option(index=idx)
                except PwTimeout:
                    await page.wait_for_timeout(3000)

                cat_sel = page.locator(".category-select")
                try:
                    if await cat_sel.input_value() != "overall":
                        try:
                            async with page.expect_navigation(wait_until="networkidle", timeout=8000):
                                await cat_sel.select_option(value="overall")
                        except PwTimeout:
                            await page.wait_for_timeout(2000)
                except Exception:
                    pass

                await page.wait_for_timeout(2000)

                dl_btn = page.locator(".download-csv")
                if await dl_btn.count() == 0 or not await dl_btn.is_visible():
                    print("    無下載按鈕，略過")
                    continue

                async with page.expect_download(timeout=15000) as dl_info:
                    await dl_btn.click()

                download = await dl_info.value
                orig     = download.suggested_filename or "rankings.csv"
                m        = re.search(r'cp(\d+)_', orig)
                cp_num   = m.group(1) if m else orig
                suffix   = f" {date_str}" if date_str else ""
                fname    = _safe_filename(f"{fmt_text} CP{cp_num}{suffix}.csv")
                dest     = PVPDATA_DIR / fname

                await download.save_as(dest)

                # 轉 UTF-8 BOM（Excel 相容中文）
                dest.write_text(dest.read_text(encoding='utf-8'), encoding='utf-8-sig')

                _fix_cp_header(dest)   # 補齊缺失的 CP 欄標頭
                _process_csv(dest)     # 展開名稱欄 → 9 個分類欄位
                _to_parquet(dest)      # 輸出同名 .parquet

                print(f"    ✓ {fname}")
                print(f"    ✓ {fname[:-4]}.parquet")

            except Exception as e:
                import traceback
                print(f"    ✗ 失敗：{e}")
                traceback.print_exc()
                all_ok = False

        await browser.close()
    return all_ok


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — Git commit（push 由使用者手動執行）
# ══════════════════════════════════════════════════════════════════════════════

def _is_git_repo() -> bool:
    r = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True, cwd=str(REPO_DIR)
    )
    return r.returncode == 0


def git_commit(update_time: str) -> None:
    if not _is_git_repo():
        print(f"  ⚠ {REPO_DIR} 不是 Git repo，跳過 commit。")
        return

    def run(cmd: list[str]) -> tuple[int, str]:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", cwd=str(REPO_DIR))
        return r.returncode, r.stderr.strip()

    rc, err = run(["git", "add", "-A", "--", str(PVPDATA_DIR)])
    if rc != 0:
        print(f"  Git add 失敗：{err}"); return

    rc, err = run(["git", "commit", "-m", f"data: PVPData 中文版更新 {update_time}"])
    if rc != 0:
        print(f"  Git commit 失敗：{err}"); return

    print("  Git commit 完成。")
    print(f'  Push：git -C "{REPO_DIR}" push')


# ══════════════════════════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════════════════════════

async def main() -> int:
    """Returns exit code: 10 = downloaded successfully, 0 = no action."""
    args    = set(sys.argv[1:])
    force   = "--force"   in args
    check   = "--check"   in args
    visible = "--visible" in args
    no_git  = "--no-git"  in args

    log  = load_log()
    scan = now_str()

    print(f"\n{'='*60}")
    print(f"PVP_DL     {scan}")
    print(f"輸出目錄   {PVPDATA_DIR}")
    print(f"{'='*60}")

    # ── [1] 確認時間 ──────────────────────────────────────────────────────────
    print("\n[1] 確認中文版最後更新時間…")
    update_time = await fetch_update_time()

    if update_time is None:
        print("  ✗ 無法取得更新時間。")
        log["history"].append({"scan_time": scan, "website_update": None,
                               "action": "error", "note": "無法解析網站更新時間"})
        save_log(log)
        return 0

    last_known = log.get("last_known_update")
    print(f"  網站 : {update_time}")
    print(f"  LOG  : {last_known or '（無記錄）'}")

    # ── [2] 確認 LOG，決定是否下載 ────────────────────────────────────────────
    print("\n[2] 確認 LOG…")

    if check:
        print("  --check 模式，不執行下載。")
        log["history"].append({"scan_time": scan, "website_update": update_time,
                               "action": "check-only", "note": "--check 模式"})
        save_log(log)
        return 0

    if last_known is None and not force:
        print("  首次記錄，不觸發下載。")
        log["last_known_update"] = update_time
        log["history"].append({"scan_time": scan, "website_update": update_time,
                               "action": "init", "note": "首次記錄"})
        save_log(log)
        return 0

    if update_time == last_known and not force:
        print("  無新更新，結束。")
        log["history"].append({"scan_time": scan, "website_update": update_time,
                               "action": "skip", "note": "無新更新"})
        save_log(log)
        return 0

    reason = "強制下載" if force else f"新版本 {last_known} → {update_time}"
    print(f"  → {reason}")

    # ── [3] 下載 + 資料處理  /  [4] 輸出雙格式 ───────────────────────────────
    print("\n[3/4] 下載 / 處理 / 輸出 CSV + parquet…")
    date_str = _parse_date_str(update_time)
    success  = await download_and_process(date_str=date_str, visible=visible)

    # ── [4.5] 汰舊：只保留最近 3 個版本 ─────────────────────────────────────
    if success:
        cleanup_old_versions(keep=3)

    # ── [5] Git commit（本機用；Actions 以 --no-git 跳過，由 workflow 處理）────
    if success:
        if no_git:
            print("\n[5] --no-git 跳過 commit（由 GitHub Actions 處理）。")
        else:
            print("\n[5] Git commit…")
            git_commit(update_time)
        log["last_known_update"] = update_time
        log["last_download"]     = scan
        log["history"].append({"scan_time": scan, "website_update": update_time,
                               "action": "downloaded", "note": reason})
        print("\n✓ 全部完成。")
        return 10  # signal: downloaded
    else:
        log["history"].append({"scan_time": scan, "website_update": update_time,
                               "action": "download_failed", "note": "部分下載失敗"})
        print("\n✗ 下載失敗。")

    save_log(log)
    return 0


sys.exit(asyncio.run(main()))
