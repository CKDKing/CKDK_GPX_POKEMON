"""
PVP_DL_ENG.py  —  PVPoke (English) rankings downloader
Source:  https://pvpoke.com/rankings/
Output:  PVPDataENG/  (same directory as this script)

Usage:
  python PVP_DL_ENG.py              Scan; download only if version changed
  python PVP_DL_ENG.py --force      Force re-download
  python PVP_DL_ENG.py --check      Check version only, no download
  python PVP_DL_ENG.py --visible    Show browser window (debug)
  python PVP_DL_ENG.py --no-git     Skip git commit (for GitHub Actions)

Exit code:
  0   — no action (skip / init / check / error)
  10  — download successful

Flow:
  [1] Check version   — read site version number from homepage
  [2] Check LOG       — compare with last known; decide whether to download
  [3] Download + process — get all format CSVs; expand name column
  [4] Output CSV      — UTF-8 BOM (Excel compatible)
  [5] Git commit      — stage PVPDataENG/ and commit (skip with --no-git)
"""

import asyncio
import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PwTimeout

sys.stdout.reconfigure(encoding="utf-8")

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_DIR    = Path(__file__).parent
PVPDATA_DIR = REPO_DIR / "PVPDataENG"
LOG_FILE    = PVPDATA_DIR / "pvpoke_eng_log.json"
HOMEPAGE    = "https://pvpoke.com/"
RANKINGS    = "https://pvpoke.com/rankings/"

_VERSION_RE = re.compile(r'(?:[Vv]ersion|VERSION)[:\s]+([\d]+\.[\d.]+)')

# ── Form token classification sets ────────────────────────────────────────────
# Tokens are extracted from parentheses: "Charizard (Mega X) (Shadow)" → ["Mega X", "Shadow"]
SHADOW_SET    = {'Shadow'}
REGION_SET    = {'Alolan', 'Galarian', 'Hisuian', 'Paldean', 'Kantonian'}
FORM_TYPE_SET = {
    'Therian', 'Incarnate', 'Origin', 'Altered', 'Complete', 'Resolute',
    'Zen', 'Pirouette', 'Aria', 'Dawn', 'Dusk', 'Midnight', 'Midday',
    'Dusk-Mane', 'Dawn-Wings', 'Dusk Mane', 'Dawn Wings',  # Necrozma
    'Confined', 'Unbound', 'Ordinary',
    'Natural', 'Crowned', 'Crowned Sword', 'Crowned Shield',  # Zacian/Zamazenta
    'Eternamax', 'Black', 'White',
    'Shield', 'Blade',          # Aegislash
    'Land', 'Sky',              # Shaymin
    'Standard', 'Armored',      # Darmanitan / Mewtwo Armored
    'Normal', 'Attack', 'Defense', 'Speed',  # Deoxys
    'Ice', 'Rider', 'Shadow Rider',          # Calyrex
    'Hero',                     # Zacian / Zamazenta base
    '50% Forme', '10% Forme', 'Complete Forme',  # Zygarde
}
MEGA_SET      = {'Mega', 'Mega X', 'Mega Y', 'Primal'}
GENDER_SET    = {'Female', 'Male'}
SIZE_SET      = {'XL', 'XS', 'Small', 'Average', 'Large', 'Super'}  # Gourgeist sizes
WEATHER_SET   = {'Sunny', 'Rainy', 'Snowy', 'Foggy', 'Cloudy', 'Windy'}
OTHER_SET     = {
    'Yellow', 'Red', 'Blue', 'Orange', 'Indigo', 'Violet', 'Sandy', 'Trash',
    "Pom-Pom", "Pa'u", 'Baile', 'Sensu',       # Oricorio
    'Heat', 'Wash', 'Frost', 'Fan', 'Mow',      # Rotom
    'Curly', 'Droopy', 'Stretchy',              # Tatsugiri
    'Full Belly', 'Hangry',                     # Morpeko
    'Flower', 'Plant', 'Overcast', 'Sunshine',
    'Shock', 'Burn', 'Chill', 'Drown',
    'Single Strike', 'Rapid Strike',
    'Meteor', 'Sword', 'Spiky',
    'Aqua', 'Blaze', 'Combat',                  # Tauros Paldean forms
    'Douse', 'Shock',                            # Genesect drives
    '50%', '10%',
    'A', 'B', 'C', 'D', 'E', 'F',
}

OUTPUT_COLUMNS = [
    'Score', 'Dex', 'Pokemon', 'Type 1', 'Type 2',
    'Region', 'Form Type', 'Shadow', 'Mega', 'Alt Form', 'Gender', 'Size', 'Weather',
    'CP', 'ATK', 'DEF', 'HP', 'Level',
    'Fast Move', 'Charge Move 1', 'Charge Move 2', 'Fast Turns', 'Charge 1 Turns',
    'Buddy Distance', 'Second Move Cost', 'Stat Product',
]

# ── Flexible column detection (handles various pvpoke CSV header styles) ──────
_COL_CANDIDATES = {
    'name_col':   ['name', 'Name', 'pokemon', 'Pokemon', '名稱'],
    'score_col':  ['score', 'Score', '評分'],
    'dex_col':    ['number', 'Number', 'dex', 'Dex', '圖鑑編號'],
    'type1_col':  ['type1', 'type 1', 'Type 1', 'Type1', '第一屬性'],
    'type2_col':  ['type2', 'type 2', 'Type 2', 'Type2', '第二屬性'],
    'atk_col':    ['attack', 'Attack', 'atk', 'ATK', '攻擊力'],
    'def_col':    ['defense', 'Defense', 'def', 'DEF', '防禦力'],
    'hp_col':     ['hp', 'HP', 'stamina', 'Stamina'],
    'sp_col':     ['statProduct', 'stat_product', 'stat product', 'Stat Product'],
    'level_col':  ['level', 'Level', '等級'],
    'cp_col':     ['cp', 'CP'],
    'fast_col':   ['fastMove', 'fast_move', 'fast move', 'Fast Move', '一般招式'],
    'chg1_col':   ['chargedMove1', 'charged_move_1', 'charged move 1', 'Charge Move 1', '特殊招式1'],
    'chg2_col':   ['chargedMove2', 'charged_move_2', 'charged move 2', 'Charge Move 2', '特殊招式2'],
    'ft_col':     ['fastMoveCount', 'fast_turns', 'fast turns', 'Fast Turns', '幾下可用特招1'],
    'ct1_col':    ['chargedMove1Count', 'charge_1_turns', 'charge 1 turns', 'Charge 1 Turns', '幾下可用特招2'],
    'buddy_col':  ['buddyDistance', 'buddy_distance', 'buddy distance', 'Buddy Distance', '夥伴行走距離'],
    'cost_col':   ['thirdMoveCost', 'second_move_cost', 'second move cost', 'Second Move Cost', '開第二招星塵花費'],
}


def _detect_col(headers: list[str], candidates: list[str]) -> str | None:
    """Return first matching header (exact match first, then case-insensitive)."""
    header_set = set(headers)
    for c in candidates:
        if c in header_set:
            return c
    lower_map = {h.lower(): h for h in headers}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def _build_col_map(headers: list[str]) -> dict[str, str | None]:
    return {key: _detect_col(headers, cands) for key, cands in _COL_CANDIDATES.items()}


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
#  STEP 1 — Check site version number
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
    m = _VERSION_RE.search(body)
    return m.group(1).strip() if m else None


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — Download + process
# ══════════════════════════════════════════════════════════════════════════════

_PAREN_RE = re.compile(r'\(([^)]*)\)')


def _safe_filename(name: str) -> str:
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, '_')
    return name.strip()


def _parse_name(full_name: str) -> dict:
    """Split 'Charizard (Mega X) (Shadow)' into base name + form columns."""
    base_name = _PAREN_RE.sub('', full_name).strip()
    tokens    = [m.group(1).strip() for m in _PAREN_RE.finditer(full_name)]

    result = {
        'Pokemon':    base_name,
        'Region':    '-', 'Form Type': '-', 'Shadow':  '-',
        'Mega':      '-', 'Alt Form':  '-', 'Gender':  '-',
        'Size':      '-', 'Weather':   '-',
    }
    for token in tokens:
        if not token:
            continue
        if   token in SHADOW_SET:    result['Shadow']    = token
        elif token in REGION_SET:    result['Region']    = token
        elif token in FORM_TYPE_SET: result['Form Type'] = token
        elif token in MEGA_SET:      result['Mega']      = token
        elif token in GENDER_SET:    result['Gender']    = token
        elif token in SIZE_SET:      result['Size']      = token
        elif token in WEATHER_SET:   result['Weather']   = token
        elif token in OTHER_SET:     result['Alt Form']  = token
        else:
            print(f"    WARNING: unknown suffix '({token})' in '{full_name}'")
    return result


def _process_csv(path: Path) -> None:
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        raw_rows = list(csv.DictReader(f))

    if not raw_rows:
        print(f"    ⚠ Empty file: {path.name}")
        return

    headers  = list(raw_rows[0].keys())
    col_map  = _build_col_map(headers)
    name_col = col_map['name_col']

    if name_col is None:
        print(f"    ⚠ Cannot detect name column. Headers: {headers[:8]}…")
        print(f"      Saving raw CSV without processing.")
        return

    print(f"    Detected name column: '{name_col}' | total columns: {len(headers)}")

    new_rows = []
    for row in raw_rows:
        full_name = row.get(name_col, '').strip()
        if not full_name:
            continue
        parsed = _parse_name(full_name)

        def _get(key: str) -> str:
            col = col_map.get(key)
            return row.get(col, '-') if col else '-'

        out = {
            'Score':          _get('score_col'),
            'Dex':            _get('dex_col'),
            'Pokemon':        parsed['Pokemon'],
            'Type 1':         _get('type1_col'),
            'Type 2':         _get('type2_col'),
            'Region':         parsed['Region'],
            'Form Type':      parsed['Form Type'],
            'Shadow':         parsed['Shadow'],
            'Mega':           parsed['Mega'],
            'Alt Form':       parsed['Alt Form'],
            'Gender':         parsed['Gender'],
            'Size':           parsed['Size'],
            'Weather':        parsed['Weather'],
            'CP':             _get('cp_col'),
            'ATK':            _get('atk_col'),
            'DEF':            _get('def_col'),
            'HP':             _get('hp_col'),
            'Level':          _get('level_col'),
            'Fast Move':      _get('fast_col'),
            'Charge Move 1':  _get('chg1_col'),
            'Charge Move 2':  _get('chg2_col'),
            'Fast Turns':     _get('ft_col'),
            'Charge 1 Turns': _get('ct1_col'),
            'Buddy Distance': _get('buddy_col'),
            'Second Move Cost': _get('cost_col'),
            'Stat Product':   _get('sp_col'),
        }
        new_rows.append(out)

    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        w.writeheader()
        w.writerows(new_rows)

    print(f"    Processed {len(new_rows)} rows")


def cleanup_old_versions(keep: int = 2) -> None:
    """Keep only the newest `keep` version tags; delete older CSVs."""
    ver_re = re.compile(r' ([\d.]+_\d{8})\.csv$')

    versions: set[str] = set()
    for f in PVPDATA_DIR.iterdir():
        m = ver_re.search(f.name)
        if m:
            versions.add(m.group(1))

    if len(versions) <= keep:
        return

    sorted_ver  = sorted(versions, reverse=True)
    old_ver     = set(sorted_ver[keep:])

    deleted = []
    for f in PVPDATA_DIR.iterdir():
        m = ver_re.search(f.name)
        if m and m.group(1) in old_ver:
            f.unlink()
            deleted.append(f.name)

    if deleted:
        print(f"\n  [cleanup] Deleted {len(deleted)} files (versions: {sorted(old_ver)})")
        for name in sorted(deleted):
            print(f"    - {name}")


async def download_and_process(version: str, visible: bool = False) -> bool:
    PVPDATA_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime('%Y%m%d')
    ver_tag  = f"{version}_{date_str}" if version else date_str
    all_ok   = True

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not visible,
            slow_mo=200 if visible else 0,
        )
        context = await browser.new_context(accept_downloads=True)
        page    = await context.new_page()

        await page.goto(RANKINGS, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        options  = page.locator(".format-select option")
        count    = await options.count()
        fmt_list = [(await options.nth(i).inner_text()).strip() for i in range(count)]
        print(f"  Found {len(fmt_list)} formats")

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

                # Reset category to "overall" if selector exists
                cat_sel = page.locator(".category-select")
                try:
                    if await cat_sel.count() > 0 and await cat_sel.input_value() != "overall":
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
                    print("    No download button, skipping")
                    continue

                async with page.expect_download(timeout=15000) as dl_info:
                    await dl_btn.click()

                download = await dl_info.value
                orig   = download.suggested_filename or "rankings.csv"
                m      = re.search(r'cp(\d+)_', orig)
                cp_num = m.group(1) if m else orig
                fname  = _safe_filename(f"{fmt_text} CP{cp_num} {ver_tag}.csv")
                dest     = PVPDATA_DIR / fname

                await download.save_as(dest)
                dest.write_text(dest.read_text(encoding='utf-8'), encoding='utf-8-sig')

                _process_csv(dest)
                print(f"    ✓ {fname}")

            except Exception as e:
                import traceback
                print(f"    ✗ Failed: {e}")
                traceback.print_exc()
                all_ok = False

        await browser.close()
    return all_ok


# ══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — Git commit
# ══════════════════════════════════════════════════════════════════════════════

def _is_git_repo() -> bool:
    r = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True, cwd=str(REPO_DIR),
    )
    return r.returncode == 0


def git_commit(version: str) -> None:
    if not _is_git_repo():
        print(f"  ⚠ {REPO_DIR} is not a Git repo, skipping commit.")
        return

    def run(cmd: list[str]) -> tuple[int, str]:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", cwd=str(REPO_DIR))
        return r.returncode, r.stderr.strip()

    rc, err = run(["git", "add", "-A", "--", str(PVPDATA_DIR)])
    if rc != 0:
        print(f"  Git add failed: {err}"); return

    rc, err = run(["git", "commit", "-m", f"data: PVPDataENG updated to version {version}"])
    if rc != 0:
        print(f"  Git commit failed: {err}"); return

    print("  Git commit done.")
    print(f'  Push:  git -C "{REPO_DIR}" push')


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

async def main() -> int:
    args    = set(sys.argv[1:])
    force   = "--force"   in args
    check   = "--check"   in args
    visible = "--visible" in args
    no_git  = "--no-git"  in args

    log  = load_log()
    scan = now_str()

    print(f"\n{'='*60}")
    print(f"PVP_DL (EN)   {scan}")
    print(f"Output dir    {PVPDATA_DIR}")
    print(f"{'='*60}")

    # ── [1] Fetch version ─────────────────────────────────────────────────────
    print("\n[1] Checking site version…")
    version = await fetch_update_time()

    if version is None:
        print("  ✗ Could not detect version number.")
        log["history"].append({"scan_time": scan, "website_update": None,
                               "action": "error", "note": "version not found"})
        save_log(log)
        return 0

    last_known = log.get("last_known_update")
    print(f"  Site    : {version}")
    print(f"  LOG     : {last_known or '(none)'}")

    # ── [2] Compare LOG ───────────────────────────────────────────────────────
    print("\n[2] Checking LOG…")

    if check:
        print("  --check mode, no download.")
        log["history"].append({"scan_time": scan, "website_update": version,
                               "action": "check-only", "note": "--check mode"})
        save_log(log)
        return 0

    if last_known is None and not force:
        print("  First run — recording version, not downloading.")
        log["last_known_update"] = version
        log["history"].append({"scan_time": scan, "website_update": version,
                               "action": "init", "note": "first run"})
        save_log(log)
        return 0

    if version == last_known and not force:
        print("  No new version, exiting.")
        log["history"].append({"scan_time": scan, "website_update": version,
                               "action": "skip", "note": "no new version"})
        save_log(log)
        return 0

    reason = "forced" if force else f"new version {last_known} → {version}"
    print(f"  → {reason}")

    # ── [3/4] Download + process ──────────────────────────────────────────────
    print("\n[3/4] Downloading / processing / writing CSV…")
    success = await download_and_process(version=version, visible=visible)

    if success:
        cleanup_old_versions(keep=2)

    # ── [5] Git commit ────────────────────────────────────────────────────────
    if success:
        if no_git:
            print("\n[5] --no-git: skipping commit (for GitHub Actions).")
        else:
            print("\n[5] Git commit…")
            git_commit(version)
        log["last_known_update"] = version
        log["last_download"]     = scan
        log["history"].append({"scan_time": scan, "website_update": version,
                               "action": "downloaded", "note": reason})
        print("\n✓ Done.")
        save_log(log)
        return 10
    else:
        log["history"].append({"scan_time": scan, "website_update": version,
                               "action": "download_failed", "note": "some downloads failed"})
        print("\n✗ Download failed.")

    save_log(log)
    return 0


sys.exit(asyncio.run(main()))
