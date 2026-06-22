# Threads Pokemon Scraper

自動爬取 [threads.net/@jchannelzz](https://www.threads.net/@jchannelzz) 的寶可夢資訊圖片，篩選符合規格後直接上傳至 GitHub Repo 的 `images/` 資料夾。

---

## 檔案結構

```
repo 根目錄/
├── Threads_Pokemon_Scraper.py           主腳本
├── .github/workflows/scraper.yml        排程設定
├── crawl_log.json                       爬蟲歷史 LOG（自動產生於 repo 根目錄）
└── images/
    ├── Pokeinfo_20260617_103000_1.png
    ├── Pokeinfo_20260617_103000_2.png
    └── ...
```

---

## 執行流程

```
[1] 讀取 LOG    從 GitHub repo 讀取 crawl_log.json（取得上次爬取時間）
[2] 開啟瀏覽器  Playwright 無頭模式導航至帳號主頁
[3] 收集貼文    滾動頁面，收集所有貼文連結
[4] 逐篇篩選    跳過已爬取的 post_id；跳過超出時間範圍的貼文
[5] 圖片驗證    下載圖片，確認解析度符合規格（1920×1080 或 2160×1234）
[6] 上傳 GitHub 通過驗證的圖片直接 PUT 至 images/ 資料夾
[7] 更新 LOG    將最新爬取時間與 post_id 清單寫回 crawl_log.json
```

---

## 圖片規格

只保留符合以下解析度的圖片（排除大頭貼、廣告等非資訊圖）：

| 解析度 | 說明 |
|--------|------|
| 1920 × 1080 | 橫式資訊圖 |
| 2160 × 1234 | 寬幅資訊圖 |

---

## 輸出檔名格式

```
Pokeinfo_{YYYYMMDD}_{HHMMSS}_{圖片序號}.png
```

範例：
```
Pokeinfo_20260617_103000_1.png   ← 2026/06/17 10:30:00 的第 1 張
Pokeinfo_20260617_103000_2.png   ← 同一貼文第 2 張（輪播）
```

---

## LOG 格式（crawl_log.json）

```json
{
    "last_crawled_time": "2026-06-17T02:30:00Z",
    "crawled_post_ids": [
        "ABC123",
        "DEF456"
    ]
}
```

| 欄位 | 說明 |
|------|------|
| `last_crawled_time` | 上次成功爬取的最新貼文時間（UTC） |
| `crawled_post_ids` | 已處理過的 post ID 清單（避免重複下載） |

首次執行時無 LOG，自動爬取**最近 30 天**的貼文；之後為增量爬取。

---

## GitHub Actions 排程

**檔案：** `.github/workflows/scraper.yml`

- 每日 **09:00 台灣時間**（UTC 01:00）自動執行
- 可在 GitHub → Actions 頁面手動觸發

**必要設定：** `GITHUB_TOKEN` 透過 Actions 自動注入，不需額外設定 Secret。

---

## 環境需求

```
Python 3.11+
requests          pip install requests
playwright        pip install playwright && playwright install chromium
pillow            pip install pillow
beautifulsoup4    pip install beautifulsoup4
```

---

## 腳本內常數說明

| 常數 | 預設值 | 說明 |
|------|--------|------|
| `TARGET_URL` | `threads.net/@jchannelzz` | 爬取目標帳號 |
| `GITHUB_REPO` | `CKDKing/CKDK_GPX_POKEMON` | 目標 repo |
| `GITHUB_BRANCH` | `main` | 目標分支 |
| `GITHUB_IMAGES_DIR` | `images` | 圖片存放資料夾 |
| `GITHUB_LOG_PATH` | `crawl_log.json` | LOG 在 repo 中的路徑 |
