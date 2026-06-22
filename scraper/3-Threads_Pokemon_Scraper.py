# -*- coding: utf-8 -*-
"""
Threads Pokemon Infographic Image Scraper
爬取 threads.net/@jchannelzz 帳號最近一個月內的寶可夢資訊圖片，
直接上傳至 GitHub Repo 的 images/ 資料夾。
crawl_log.json 也儲存在 repo 中以持久化紀錄。
"""

import os
import re
import sys
import json
import base64
import tempfile
import warnings
from datetime import datetime, timedelta
import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# --- 爬蟲設定 ---
TARGET_URL  = "https://www.threads.net/@jchannelzz?hl=zh-tw"
USER_AGENT  = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# --- GitHub 設定（填入你的 Personal Access Token）---
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")   # 建議用環境變數，或直接填字串
GITHUB_REPO       = "CKDKing/CKDK_GPX_POKEMON"
GITHUB_BRANCH     = "main"
GITHUB_IMAGES_DIR = "images"
GITHUB_LOG_PATH   = "crawl_log.json"
GITHUB_API_BASE   = "https://api.github.com"

# --- GitHub API 工具函式 ---

def _gh_headers() -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def github_get_file(path: str) -> tuple[str | None, str | None]:
    """取得 repo 中指定檔案的內容（base64解碼後）與 SHA。若不存在回傳 (None, None)。"""
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    resp = requests.get(url, headers=_gh_headers(), timeout=15)
    if resp.status_code == 404:
        return None, None
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]

def github_put_file(path: str, content_bytes: bytes, commit_msg: str, sha: str | None = None) -> bool:
    """在 repo 中新增或更新檔案。sha 為更新時必填（既有檔案的 SHA）。"""
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": commit_msg,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    resp = requests.put(url, headers=_gh_headers(), json=payload, timeout=30)
    if resp.status_code in (200, 201):
        return True
    print(f"  GitHub 上傳失敗 ({path}): {resp.status_code} {resp.text[:200]}")
    return False

# --- crawl_log.json 讀寫（儲存於 GitHub repo）---

def load_crawl_log() -> tuple[dict, str | None]:
    """從 GitHub repo 讀取 crawl_log.json，回傳 (log_data, sha)。"""
    try:
        content, sha = github_get_file(GITHUB_LOG_PATH)
        if content:
            return json.loads(content), sha
    except Exception as e:
        print(f"讀取 GitHub 日誌失敗，將重新建立: {e}")
    return {"last_crawled_time": None, "crawled_post_ids": []}, None

def save_crawl_log(log_data: dict, sha: str | None) -> str | None:
    """將 crawl_log.json 寫回 GitHub repo，回傳新 SHA。"""
    content_bytes = json.dumps(log_data, ensure_ascii=False, indent=4).encode("utf-8")
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/{GITHUB_LOG_PATH}"
    payload = {
        "message": "chore: update crawl_log",
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    resp = requests.put(url, headers=_gh_headers(), json=payload, timeout=30)
    if resp.status_code in (200, 201):
        return resp.json()["content"]["sha"]
    print(f"保存日誌失敗: {resp.status_code} {resp.text[:200]}")
    return sha

# --- 圖片下載與上傳 ---

def download_and_check_image(url: str) -> bytes | None:
    """下載圖片並驗證解析度，符合規格才回傳 bytes，否則回傳 None。"""
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            print(f"  圖片下載失敗，HTTP {resp.status_code}")
            return None
        image_bytes = resp.content
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        try:
            from PIL import Image
            with Image.open(tmp_path) as img:
                w, h = img.size
            if (w == 1920 and h == 1080) or (w == 2160 and h == 1234):
                return image_bytes
            print(f"  解析度 {w}x{h} 不符合規格，略過")
            return None
        except Exception as e:
            print(f"  解析度檢查失敗: {e}")
            return None
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception as e:
        print(f"  圖片下載異常: {e}")
        return None

def upload_image_to_github(filename: str, image_bytes: bytes) -> bool:
    """將圖片上傳至 GitHub repo 的 images/ 資料夾。"""
    path = f"{GITHUB_IMAGES_DIR}/{filename}"
    # 先查是否已存在（避免重複 commit 衝突）
    _, existing_sha = github_get_file(path)
    commit_msg = f"feat: add {filename}"
    return github_put_file(path, image_bytes, commit_msg, existing_sha)

# --- 頁面解析 ---

def parse_utc_time(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

def get_taiwan_time(utc_dt: datetime) -> datetime:
    return utc_dt + timedelta(hours=8)

def extract_json_block(text: str, start_pattern: str) -> str | None:
    match = re.search(start_pattern, text)
    if not match:
        return None
    start_idx = match.start()
    brace_count = 0
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[start_idx:i + 1]
    return None

def find_key_recursive(data, target_key):
    if isinstance(data, dict):
        if target_key in data:
            return data[target_key]
        for value in data.values():
            res = find_key_recursive(value, target_key)
            if res:
                return res
    elif isinstance(data, list):
        for item in data:
            res = find_key_recursive(item, target_key)
            if res:
                return res
    return None

def extract_main_post_images(soup: BeautifulSoup) -> tuple[str, list]:
    for script in soup.find_all("script"):
        text = script.get_text()
        if not text or "adp_BarcelonaPermalinkMobilePostColumnPageQueryRelayPreloader" not in text:
            continue
        json_str = extract_json_block(text, r'\{"__bbox"')
        if not json_str:
            continue
        try:
            data = json.loads(json_str)
            media = find_key_recursive(data, "media")
            if not media:
                continue
            caption = media.get("caption", {}).get("text", "")
            image_urls = []
            carousel = media.get("carousel_media")
            if carousel:
                for item in carousel:
                    candidates = item.get("image_versions2", {}).get("candidates", [])
                    matched = next(
                        (c["url"] for c in candidates if (c.get("width"), c.get("height")) in [(1920, 1080), (2160, 1234)]),
                        None
                    )
                    image_urls.append(matched)
            else:
                candidates = media.get("image_versions2", {}).get("candidates", [])
                matched = next(
                    (c["url"] for c in candidates if (c.get("width"), c.get("height")) in [(1920, 1080), (2160, 1234)]),
                    None
                )
                image_urls.append(matched)
            return caption, image_urls
        except Exception:
            pass

    print("  無法由 JSON 提取，改用備用 DOM 方案...")
    post_images = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if not src:
            continue
        is_avatar = "2885-19" in src or "82787-19" in src or "大頭貼照" in alt
        if "fbcdn.net" in src and not is_avatar and "external" not in src:
            if src not in post_images:
                post_images.append(src)
    meta = soup.find("meta", attrs={"name": "description"})
    return (meta.get("content") if meta else ""), post_images

# --- 主程式 ---

def check_github_token():
    if not GITHUB_TOKEN:
        print("錯誤：未設定 GITHUB_TOKEN。")
        print("請設定環境變數：set GITHUB_TOKEN=ghp_你的token")
        print("或直接在腳本頂端的 GITHUB_TOKEN 變數填入 token 字串。")
        sys.exit(1)

def scrape_threads() -> None:
    check_github_token()

    print(f"從 GitHub repo 讀取爬蟲日誌 ({GITHUB_REPO}/{GITHUB_LOG_PATH})...")
    log_data, log_sha = load_crawl_log()

    now = datetime.now()
    if log_data["last_crawled_time"]:
        cutoff_dt = parse_utc_time(log_data["last_crawled_time"])
        print(f"增量爬取，起始時間: {get_taiwan_time(cutoff_dt).strftime('%Y-%m-%d %H:%M:%S')} (台灣時間)")
    else:
        cutoff_dt = parse_utc_time((now - timedelta(days=30)).isoformat() + "Z")
        print(f"首次爬取，範圍: 最近 30 天 (起始 {get_taiwan_time(cutoff_dt).strftime('%Y-%m-%d %H:%M:%S')})")

    newest_post_time = None
    crawled_ids = set(log_data.get("crawled_post_ids", []))

    with sync_playwright() as p:
        print("啟動無頭瀏覽器...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="zh-TW")
        page = context.new_page()

        print(f"導航至主頁: {TARGET_URL}")
        page.goto(TARGET_URL)
        page.wait_for_timeout(5000)

        print("滾動頁面加載歷史貼文...")
        last_height = page.evaluate("document.body.scrollHeight")
        for _ in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        soup = BeautifulSoup(page.content(), "html.parser")
        post_links = []
        for a in soup.find_all("a", href=True):
            match = re.search(r"/@jchannelzz/post/([^/]+)", a["href"])
            if match:
                post_url = f"https://www.threads.net/@jchannelzz/post/{match.group(1)}"
                if post_url not in post_links:
                    post_links.append(post_url)

        print(f"發現 {len(post_links)} 篇貼文，開始篩選與下載...")

        downloaded_count = 0
        new_crawled_ids = []

        for idx, post_url in enumerate(post_links):
            post_id = post_url.split("/")[-1]
            if post_id in crawled_ids:
                continue

            print(f"\n[{idx+1}/{len(post_links)}] 解析: {post_url}")
            try:
                page.goto(post_url)
                page.wait_for_timeout(4000)

                post_soup = BeautifulSoup(page.content(), "html.parser")
                time_el = post_soup.find("time")
                if not time_el or not time_el.get("datetime"):
                    print("  無法取得發布時間，跳過")
                    continue

                pub_dt = parse_utc_time(time_el["datetime"])
                local_dt = get_taiwan_time(pub_dt)

                if pub_dt <= cutoff_dt:
                    print(f"  貼文時間 {local_dt.strftime('%Y-%m-%d %H:%M:%S')} 超出範圍，跳過")
                    continue

                if newest_post_time is None or pub_dt > newest_post_time:
                    newest_post_time = pub_dt

                _, post_images = extract_main_post_images(post_soup)
                valid_images = [u for u in post_images if u is not None]
                print(f"  發布時間: {local_dt.strftime('%Y-%m-%d %H:%M:%S')} | 候選圖片: {len(valid_images)} 張")

                if not valid_images:
                    print("  無符合規格的圖片，跳過")
                    new_crawled_ids.append(post_id)
                    continue

                date_str = local_dt.strftime("%Y%m%d")
                time_str = local_dt.strftime("%H%M%S")

                for img_idx, img_url in enumerate(valid_images):
                    filename = f"Pokeinfo_{date_str}_{time_str}_{img_idx+1}.png"
                    print(f"  下載並驗證: {filename}")
                    image_bytes = download_and_check_image(img_url)
                    if image_bytes:
                        print(f"  上傳至 GitHub: {GITHUB_IMAGES_DIR}/{filename}")
                        if upload_image_to_github(filename, image_bytes):
                            print(f"  ✓ 上傳成功")
                            downloaded_count += 1
                        else:
                            print(f"  ✗ 上傳失敗")

                new_crawled_ids.append(post_id)

            except Exception as e:
                print(f"  解析貼文時發生異常: {e}")

        browser.close()

    # 更新日誌寫回 GitHub
    if newest_post_time:
        log_data["last_crawled_time"] = newest_post_time.isoformat().replace("+00:00", "Z")
    log_data["crawled_post_ids"] = list(crawled_ids.union(new_crawled_ids))
    print(f"\n更新爬蟲日誌至 GitHub...")
    save_crawl_log(log_data, log_sha)

    print(f"\n完成！本次成功上傳 {downloaded_count} 張圖片至 {GITHUB_REPO}/{GITHUB_IMAGES_DIR}/")

if __name__ == "__main__":
    scrape_threads()
