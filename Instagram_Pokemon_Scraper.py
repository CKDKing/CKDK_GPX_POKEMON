# -*- coding: utf-8 -*-
"""
Instagram Pokemon Image Scraper（instaloader 版）
不需要瀏覽器，直接走 IG 行動 API，session 持久化存檔。

用法:
  從 Chrome/Edge 提取 session: python Instagram_Pokemon_Scraper.py --from-chrome
  從 Playwright profile 提取:   python Instagram_Pokemon_Scraper.py --from-browser
  帳號密碼登入（備用）:         python Instagram_Pokemon_Scraper.py --setup
  日常自動執行:                  python Instagram_Pokemon_Scraper.py
"""

import re
import sys
import json
import getpass
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import instaloader

warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# ── 設定 ────────────────────────────────────────────────────
TARGET_USERNAME = "dennyli666666"
REQUIRED_TAGS   = ["#PokemonGO", "#寶可夢", "#神奇寶貝"]
EXCLUDE_KEYWORDS = ["寶可夢中心", "Pokemon Center", "Pokémon Center"]
DAYS_BACK       = 8

ROOT_DIR      = Path(__file__).parent   # = D:\AI Project\Scraper\ (git root)
IMAGES_DIR    = ROOT_DIR / "images_ig"
SESSION_FILE  = ROOT_DIR / "ig_session"
USERNAME_FILE = ROOT_DIR / "ig_username.txt"
LOG_FILE      = ROOT_DIR / "Instagram_Pokemon_Scraper_log.json"
PROFILE_DIR   = ROOT_DIR / "ig_profile"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ── 工具函式 ────────────────────────────────────────────────

def ensure_dirs():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def load_log() -> dict:
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"downloaded_posts": [], "last_run": None}

def save_log(log: dict):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def make_filename(tw_dt: datetime, img_index: int) -> str:
    return f"DENNY_POKEINFO_{tw_dt.strftime('%Y%m%d%H%M%S')}_{img_index}.JPG"

def has_required_tag(text: str) -> bool:
    for tag in REQUIRED_TAGS:
        pattern = (
            r'(?<![A-Za-z0-9一-鿿#])'
            + re.escape(tag)
            + r'(?![A-Za-z0-9一-鿿])'
        )
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def download_image(url: str, save_path: Path) -> bool:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        if resp.status_code != 200:
            return False
        data = resp.content
        if len(data) < 80 * 1024:   # 小於 80 KB 視為縮圖
            return False
        save_path.write_bytes(data)
        return True
    except Exception as e:
        print(f"    下載異常: {e}")
        return False

def clean_small_images():
    removed = 0
    for f in IMAGES_DIR.glob("*.JPG"):
        if f.stat().st_size < 80 * 1024:
            f.unlink()
            removed += 1
    if removed:
        print(f"  刪除 {removed} 張小圖")

def clean_old_images(days: int = 25):
    """刪除檔名日期超過 days 天的圖片"""
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    for f in IMAGES_DIR.glob("DENNY_POKEINFO_*.JPG"):
        try:
            date_str = f.stem.split("_")[2]          # yyyymmddHHMMSS
            file_dt  = datetime.strptime(date_str, "%Y%m%d%H%M%S")
            if file_dt < cutoff:
                f.unlink()
                removed += 1
                print(f"  刪除過期: {f.name}")
        except Exception:
            pass
    if removed:
        print(f"  共刪除 {removed} 張過期圖片（>{days} 天）")

# ── Setup：手動登入瀏覽器後自動提取 cookies ─────────────────

def setup_from_browser():
    """
    開啟 Playwright 瀏覽器，等待用戶手動登入 Instagram，
    登入完成後自動提取 cookies 並儲存 instaloader session。
    手動登入不觸發 IG 機器人驗證。
    """
    import shutil
    from playwright.sync_api import sync_playwright

    # 清除舊 profile（可能有過期或 redirect-cached 狀態）
    if PROFILE_DIR.exists():
        try:
            shutil.rmtree(PROFILE_DIR)
        except Exception as e:
            print(f"⚠  無法清除舊 profile，繼續使用: {e}")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("手動登入模式")
    print("=" * 60)
    print()
    print("即將開啟瀏覽器視窗，請在視窗中：")
    print("  1. 輸入 Instagram 帳號密碼")
    print("  2. 完成任何雙重驗證")
    print("  3. 等到 IG 主頁顯示（看到貼文動態）")
    print()
    print("登入完成後程式自動偵測並關閉瀏覽器（最多等 5 分鐘）")
    print("⚠  不要自己關閉瀏覽器視窗")
    print()
    input("準備好後按 Enter 開啟瀏覽器...")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="zh-TW",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        # 隱藏 webdriver 標記
        page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )

        page.goto(
            "https://www.instagram.com/accounts/login/",
            timeout=30_000,
            wait_until="domcontentloaded",
        )

        # 等待用戶登入：偵測 URL 離開 /accounts/ 頁面
        print("\n等待登入中（最多 5 分鐘）...\n")
        try:
            page.wait_for_function(
                """() => {
                    const url = window.location.href;
                    return url.includes('instagram.com') &&
                           !url.includes('/accounts/login') &&
                           !url.includes('/accounts/emailsignup') &&
                           !url.includes('/challenge/') &&
                           !url.includes('/auth_platform/');
                }""",
                timeout=300_000,
                polling=2_000,
            )
        except Exception:
            print("✗ 等待超時（5 分鐘），請重試。")
            ctx.close()
            return

        print("✓ 偵測到登入成功！等待 session cookies 寫入...")
        page.wait_for_timeout(4_000)

        raw_cookies = ctx.cookies()

        # 嘗試從頁面 JS 取帳號名稱
        username = ""
        try:
            username = page.evaluate("""
                () => {
                    try {
                        const d = JSON.parse(
                            document.getElementById('__NEXT_DATA__')?.textContent || '{}'
                        );
                        return d?.props?.pageProps?.viewer?.username || '';
                    } catch(e) { return ''; }
                }
            """) or ""
        except Exception:
            pass

        ctx.close()

    ig_cookies = {
        c["name"]: c["value"]
        for c in raw_cookies
        if "instagram.com" in c.get("domain", "")
    }

    print(f"  取得 {len(ig_cookies)} 個 IG cookies: {', '.join(ig_cookies.keys())}")

    if "sessionid" not in ig_cookies:
        print("\n✗ 未取到 sessionid，登入可能未完成。")
        print("  請重試並確認登入後看到 IG 主頁（有貼文動態）")
        return

    # 注入 cookies 到 instaloader 並儲存 session
    L = instaloader.Instaloader(quiet=True)
    for name, value in ig_cookies.items():
        L.context._session.cookies.set(name, value, domain=".instagram.com")

    # test_login() 驗證 session 是否有效，同時回傳帳號
    if not username:
        try:
            username = L.test_login() or ""
        except Exception as e:
            print(f"  API 驗證失敗: {e}")

    if not username:
        username = input("請輸入你的 IG 帳號名稱: ").strip()

    # instaloader 的 save_session_to_file 需要 context.username 不為空
    L.context.username = username
    L.save_session_to_file(str(SESSION_FILE))
    USERNAME_FILE.write_text(username, encoding="utf-8")

    print(f"\n✓ Session 已儲存！帳號: {username}")
    print(f"  之後直接執行（背景，無需瀏覽器）：")
    print(f"  python Instagram_Pokemon_Scraper.py")


# ── Setup：從真實 Chrome/Edge 提取 IG cookies ────────────────

def setup_from_chrome():
    """
    從用戶電腦的 Chrome 或 Edge 瀏覽器提取 IG session cookies，
    不需要重新登入，也不觸發機器人驗證。
    執行前請先關閉 Chrome / Edge（否則 cookie 資料庫可能被鎖住）。
    """
    try:
        import rookiepy
    except ImportError:
        print("✗ 請先安裝: pip install rookiepy")
        return

    print("從瀏覽器提取 Instagram cookies...")
    print("（若 Chrome/Edge 正在執行，可能需要先關閉才能讀取）\n")

    ig_cookies = {}

    # 依序嘗試 Chrome → Edge → Brave → Firefox
    browsers = [
        ("Chrome",  lambda: rookiepy.chrome(["instagram.com"])),
        ("Edge",    lambda: rookiepy.edge(["instagram.com"])),
        ("Brave",   lambda: rookiepy.brave(["instagram.com"])),
        ("Firefox", lambda: rookiepy.firefox(["instagram.com"])),
    ]

    for browser_name, fn in browsers:
        try:
            cookies_list = fn()
            if cookies_list:
                ig_cookies = {c["name"]: c["value"] for c in cookies_list
                              if c.get("value")}
                if "sessionid" in ig_cookies:
                    print(f"✓ 從 {browser_name} 取得 sessionid")
                    break
                else:
                    print(f"  {browser_name}：有 cookies 但無 sessionid（可能未登入）")
            else:
                print(f"  {browser_name}：無 IG cookies")
        except Exception as e:
            print(f"  {browser_name}：{e}")

    if "sessionid" not in ig_cookies:
        print("\n✗ 所有瀏覽器都找不到 IG sessionid。")
        print("  請確認你在 Chrome 或 Edge 有登入 Instagram，")
        print("  或改用 --setup 以帳號密碼方式登入。")
        return

    # 注入 cookies 到 instaloader
    L = instaloader.Instaloader(quiet=True)
    for name, value in ig_cookies.items():
        L.context._session.cookies.set(name, value, domain=".instagram.com")

    # 確認 session 有效並取得帳號
    username = ""
    try:
        username = L.test_login() or ""
        if username:
            print(f"✓ Session 驗證成功，帳號: {username}")
    except Exception as e:
        print(f"⚠  API 驗證失敗: {e}")

    if not username:
        username = input("請輸入你的 IG 帳號: ").strip()

    L.context.username = username
    L.save_session_to_file(str(SESSION_FILE))
    USERNAME_FILE.write_text(username, encoding="utf-8")

    print(f"\n✓ Session 已儲存！")
    print(f"  帳號: {username}")
    print(f"  之後直接執行: python Instagram_Pokemon_Scraper.py")


# ── Setup：帳號密碼登入（備用）───────────────────────────────

def setup_login():
    print("=" * 60)
    print("Setup 模式：登入 Instagram（只需執行一次）")
    print("=" * 60)
    print("\nSession 儲存後，日常執行完全不需要登入。\n")

    username = input("Instagram 帳號: ").strip()
    password = getpass.getpass("Instagram 密碼（輸入不顯示）: ")

    L = instaloader.Instaloader(quiet=True)
    try:
        L.login(username, password)
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        code = input("請輸入雙重驗證碼: ").strip()
        L.two_factor_login(code)
    except Exception as e:
        print(f"\n✗ 登入失敗: {e}")
        return

    L.save_session_to_file(str(SESSION_FILE))
    USERNAME_FILE.write_text(username, encoding="utf-8")

    print(f"\n✓ 登入成功！")
    print(f"  Session 儲存至: {SESSION_FILE}")
    print(f"\n之後直接執行撈圖（無需瀏覽器，背景自動完成）：")
    print(f"  python Instagram_Pokemon_Scraper.py")

# ── 主程式 ───────────────────────────────────────────────────

def scrape():
    if not SESSION_FILE.exists() or not USERNAME_FILE.exists():
        print("找不到 session，請先執行 --setup：")
        print("  python Instagram_Pokemon_Scraper.py --setup")
        sys.exit(1)

    username = USERNAME_FILE.read_text(encoding="utf-8").strip()

    ensure_dirs()
    print("清理舊小圖及過期圖片...")
    clean_small_images()
    clean_old_images(10)

    log = load_log()
    already_done = set(log.get("downloaded_posts", []))
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)

    print("=" * 60)
    print(f"目標  : https://www.instagram.com/{TARGET_USERNAME}/")
    print(f"範圍  : 最近 {DAYS_BACK} 天（{cutoff_dt.strftime('%Y-%m-%d')} 後）")
    print(f"標籤  : {' / '.join(REQUIRED_TAGS)}")
    print(f"儲存至: {IMAGES_DIR}")
    print("=" * 60)

    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    try:
        L.load_session_from_file(username, str(SESSION_FILE))
    except Exception as e:
        print(f"✗ 載入 session 失敗: {e}")
        print("請重新執行 --from-browser。")
        sys.exit(1)

    # IG web GraphQL API (doc_id 模式) 必須帶 x-ig-app-id，否則 400
    csrftoken = L.context._session.cookies.get("csrftoken", "")
    L.context._session.headers.update({
        "x-ig-app-id": "936619743392459",
        "x-csrftoken": csrftoken,
        "x-ig-www-claim": "0",
        "Referer": "https://www.instagram.com/",
    })

    try:
        profile = instaloader.Profile.from_username(L.context, TARGET_USERNAME)
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"✗ 找不到帳號: {TARGET_USERNAME}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 載入個人頁失敗（可能 session 過期）: {e}")
        print("請重新執行 --from-browser。")
        sys.exit(1)

    # instaloader 4.15 的 _obtain_metadata (doc_id 25980296051578533) 使用
    # 過期的 __relay_internal__pv__ 變數導致 400；logged_in 模式下
    # get_posts() 的 NodeIterator 不依賴這份 metadata，直接跳過。
    profile._has_full_metadata = True

    saved_count    = 0
    new_done_posts: list[str] = []

    print(f"\n開始掃描 {TARGET_USERNAME} 的貼文...\n")

    for post in profile.get_posts():
        # 時間（UTC → 台灣 +8）
        post_dt_utc = post.date_utc.replace(tzinfo=timezone.utc)
        if post_dt_utc < cutoff_dt:
            print(f"  貼文時間超出 {DAYS_BACK} 天範圍，停止。")
            break

        shortcode = post.shortcode

        if shortcode in already_done:
            print(f"  {shortcode} — 已處理，跳過")
            continue

        tw_dt = post_dt_utc + timedelta(hours=8)
        print(f"  [{shortcode}] {tw_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        # 標籤檢查
        caption = post.caption or ""
        if not has_required_tag(caption):
            print(f"         ✗ 無符合標籤，跳過")
            new_done_posts.append(shortcode)
            continue

        # 排除關鍵字檢查
        excluded = next((kw for kw in EXCLUDE_KEYWORDS if kw.lower() in caption.lower()), None)
        if excluded:
            print(f"         ✗ 含排除關鍵字「{excluded}」，跳過")
            new_done_posts.append(shortcode)
            continue

        hit = [t for t in REQUIRED_TAGS if re.search(
            r'(?<![A-Za-z0-9一-鿿#])' + re.escape(t) + r'(?![A-Za-z0-9一-鿿])',
            caption, re.IGNORECASE
        )]

        # 取得圖片 URL（輪播或單張）
        if post.typename == "GraphSidecar":
            img_urls = [node.display_url for node in post.get_sidecar_nodes()]
        else:
            img_urls = [post.url]

        print(f"         ✓ {' '.join(hit)} | {len(img_urls)} 張")

        for img_i, img_url in enumerate(img_urls, 1):
            filename  = make_filename(tw_dt, img_i)
            save_path = IMAGES_DIR / filename
            if save_path.exists():
                print(f"         [{img_i:02d}] 已存在: {filename}")
                continue
            ok = download_image(img_url, save_path)
            if ok:
                kb = save_path.stat().st_size // 1024
                print(f"         [{img_i:02d}] ✓ {filename} ({kb} KB)")
                saved_count += 1
            else:
                print(f"         [{img_i:02d}] ✗ 下載失敗")

        new_done_posts.append(shortcode)

    log["downloaded_posts"] = list(set(already_done) | set(new_done_posts))
    log["last_run"] = datetime.now().isoformat()
    save_log(log)

    print(f"\n{'='*60}")
    print(f"完成！本次儲存 {saved_count} 張圖片至：")
    print(f"  {IMAGES_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    if "--from-chrome" in sys.argv:
        setup_from_chrome()
    elif "--from-browser" in sys.argv:
        setup_from_browser()
    elif "--setup" in sys.argv:
        setup_login()
    else:
        scrape()
