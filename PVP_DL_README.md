# PVP_DL

自動偵測並下載 [pvpoketw.com](https://pvpoketw.com/rankings/) 排行榜 CSV 資料，處理後輸出雙格式，並透過 GitHub Actions 每日定時執行。

---

## 檔案結構

```
repo 根目錄/
├── PVP_DL.py                        主腳本
├── .github/workflows/pvp_update.yml  排程設定
└── PVPData/
    ├── pvpoke_log.json               下載歷史 LOG
    ├── 超級聯盟 CP1500 20260617.csv
    ├── 超級聯盟 CP1500 20260617.parquet
    └── ...（各 Format 檔案）
```

---

## 執行流程

```
[1] 確認時間   讀取首頁「中文版最後更新時間」
[2] 確認 LOG   比對上次記錄版本
     ├─ 相同    → 結束（不下載）
     └─ 不同    → 繼續
[3] 下載       逐一選取所有 Format，點擊下載按鈕
[4] 處理輸出   修正欄位 → 展開名稱 → 輸出 .csv + .parquet
[4.5] 汰舊     只保留最近 3 個日期版本，刪除更舊的檔案
[5] Git commit  stage PVPData/ 並 commit
```

---

## 輸出檔名格式

```
{Format名稱} CP{上限} {YYYYMMDD}.csv
{Format名稱} CP{上限} {YYYYMMDD}.parquet
```

日期取自網站「中文版最後更新時間」，例如：

```
超級聯盟 CP1500 20260617.csv
大師聯盟 CP10000 20260617.parquet
```

---

## CSV 欄位結構（共 26 欄）

| 欄 | 欄位名稱 | 說明 |
|----|----------|------|
| A | 評分 | PvP 綜合評分 |
| B | 圖鑑編號 | 全國圖鑑編號 |
| C | 寶可夢 | 純名稱（不含形態後綴） |
| D | 第一屬性 | 主屬性 |
| E | 第二屬性 | 副屬性 |
| F | 地區 | 洗翠 / 伽勒爾 / 阿羅拉 等，無則 `-` |
| G | 型態別 | 靈獸 / 化身 / 起源 等，無則 `-` |
| H | 暗影 | 暗影形態，無則 `-` |
| I | Mega進化 | Mega / Mega X / Mega Y / 原始，無則 `-` |
| J | 其他形態 | 專屬形態，無則 `-` |
| K | 性別 | 雌 / 雄差異，無則 `-` |
| L | 尺寸 | 大尺寸 / 小尺寸 等，無則 `-` |
| M | 天氣 | 晴 / 雨 / 雪 / 結冰，無則 `-` |
| N | CP | CP 上限值 |
| O | 攻擊力 | 攻擊數值 |
| P | 防禦力 | 防禦數值 |
| Q | HP | HP 數值 |
| R | 等級 | 等級 |
| S | 一般招式 | 一般技能 |
| T | 特殊招式1 | 主要特殊技能 |
| U | 特殊招式2 | 次要特殊技能 |
| V | 幾下可用特招1 | 累積特招1所需一般招式次數 |
| W | 幾下可用特招2 | 累積特招2所需一般招式次數 |
| X | 夥伴行走距離 | 夥伴獲得糖果所需公里數 |
| Y | 開第二招星塵花費 | 解鎖第二技能費用（星塵） |
| Z | Stat Product | 攻防HP 綜合能力乘積 |

---

## LOG 格式（pvpoke_log.json）

```json
{
  "last_known_update": "Wed Jun 17 18:55:06 2026 +0800",
  "last_download": "2026-06-22T10:30:00+08:00",
  "history": [
    {
      "scan_time": "2026-06-22T10:30:00+08:00",
      "website_update": "Wed Jun 17 18:55:06 2026 +0800",
      "action": "downloaded",
      "note": "新版本 ..."
    }
  ]
}
```

| 欄位 | 說明 |
|------|------|
| `last_known_update` | 上次成功下載時的網站版本時間 |
| `last_download` | 上次成功下載的執行時間 |
| `history` | 每次執行的完整記錄 |

**history action 值：**

| action | 說明 |
|--------|------|
| `downloaded` | 偵測到新版本，成功下載 |
| `skip` | 版本相同，跳過 |
| `init` | 首次記錄，未下載 |
| `check-only` | `--check` 模式，未下載 |
| `download_failed` | 下載過程發生錯誤 |
| `error` | 無法取得網站更新時間 |

---

## 版本保留規則

每次下載後自動汰舊，**只保留最近 3 個日期版本**：

```
20260622  ✓ 保留（最新）
20260601  ✓ 保留
20260510  ✓ 保留
20260425  ✗ 刪除
```

被刪除的版本仍可從 Git 歷史記錄中還原。

---

## 指令參數

```bash
python PVP_DL.py              # 正常執行（有新版本才下載）
python PVP_DL.py --force      # 強制重新下載
python PVP_DL.py --check      # 只查詢更新時間，不下載
python PVP_DL.py --visible    # 顯示瀏覽器視窗（除錯用）
python PVP_DL.py --no-git     # 跳過 git commit（GitHub Actions 使用）
```

---

## GitHub Actions 排程

**檔案：** `.github/workflows/pvp_update.yml`

- 每日 **09:00 台灣時間**（UTC 01:00）自動執行
- 可在 GitHub → Actions 頁面手動觸發，並選擇是否強制下載

**手動觸發流程：**
1. GitHub → Actions → PVPoke Daily Update → Run workflow
2. 勾選「強制重新下載」（初始化或手動補跑時使用）
3. Run workflow

**Exit code 說明（workflow 判斷用）：**

| Code | 意義 |
|------|------|
| `0` | 無動作（skip / init / check） |
| `10` | 下載成功 → workflow 執行 git commit + push |

---

## 環境需求

```
Python 3.10+
playwright    pip install playwright && playwright install chromium
pandas        pip install pandas
pyarrow       pip install pyarrow
```

---

## 已知問題與修正

**網站 CSV 標頭缺少 CP 欄**

原始匯出的 CSV 標頭共 17 欄，但資料列實際有 18 欄，「等級」之後漏寫「CP」欄標頭，導致後續欄位全部錯位。腳本自動偵測並補齊，若未來網站修正則不影響運作。
