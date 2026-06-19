# PVPoke_Download_README

## 腳本說明

**檔案：** `pvpoke_download.py`
**來源網站：** https://pvpoketw.com/rankings/

自動開啟瀏覽器，逐一選取排行榜頁面的 **Format 下拉選單**所有項目，
排序條件統一使用 **OVERALL**，匯出 CSV 並完成後處理後存入 `PVPCSV/` 資料夾。

---

## 環境需求

```
Python 3.10+
playwright          # pip install playwright
                    # python -m playwright install chromium
pandas              # pip install pandas
pyarrow             # pip install pyarrow
```

---

## 執行方式

```bash
python pvpoke_download.py
```

執行時會開啟可視瀏覽器視窗，依序自動處理每個 Format 選項。

---

## 輸出檔案

存放位置：`d:\AI Project\PVPCSV\`

檔名格式：`{Format選項名稱} CP{CP上限值}.csv / .parquet`

每個排行榜產生兩個同名檔案：`.csv`（Excel 用）與 `.parquet`（分析用）。

| 檔案名稱（不含副檔名） | 說明 |
|------------------------|------|
| 超級聯盟 CP1500 | 超級聯盟（CP 1500） |
| 高級聯盟 CP2500 | 高級聯盟（CP 2500） |
| 大師聯盟 CP10000 | 大師聯盟（CP 10000） |
| 大師聯盟：超級版 CP10000 | 大師聯盟 Mega 限定（CP 10000） |
| NAIC 2026 Championship Series Cup CP1500 | NAIC 2026 賽事杯（CP 1500） |
| 陽光盃 CP1500 | 陽光盃（CP 1500） |
| Battle Frontier (Bayou Cup) CP1500 | Battle Frontier 沼澤杯（CP 1500） |
| Battle Frontier (Spellcraft Cup) CP1500 | Battle Frontier 魔法杯（CP 1500） |
| Battle Frontier (UL Retro) CP2500 | Battle Frontier 高級復古（CP 2500） |
| Battle Frontier (Master) CP10000 | Battle Frontier 大師（CP 10000） |
| Devon Equinox Cup CP1500 | Devon 春分杯（CP 1500） |
| Devon Bastille Cup CP1500 | Devon 巴士底杯（CP 1500） |

> `自訂排名` 選項因為是使用者自訂頁面，無標準資料，自動略過不下載。

---

## CSV 欄位結構

共 26 欄，順序如下：

| 欄 | 欄位名稱 | 說明 |
|----|----------|------|
| A | 評分 | PvP 綜合評分 |
| B | 圖鑑編號 | 全國圖鑑編號 |
| C | 寶可夢 | 純寶可夢名稱（不含形態後綴） |
| D | 第一屬性 | 主屬性 |
| E | 第二屬性 | 副屬性（無則空白） |
| F | 地區 | 地區形態（洗翠／伽勒爾／阿羅拉 等），無則 `-` |
| G | 型態別 | 靈獸／化身／起源 等形態，無則 `-` |
| H | 暗影 | 暗影形態，無則 `-` |
| I | Mega進化 | Mega／Mega X／Mega Y／原始，無則 `-` |
| J | 其他形態 | 寶可夢專屬形態（一擊流、天空、盛開 等），無則 `-` |
| K | 性別 | 雌／雄差異，無則 `-` |
| L | 尺寸 | 大尺寸／小尺寸 等，無則 `-` |
| M | 天氣 | 晴／雨／雪／結冰，無則 `-` |
| N | CP | 實際 CP 上限值 |
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
| Y | 開第二招星塵花費 | 解鎖第二特殊技能費用（星塵） |
| Z | Stat Product | 攻防HP 綜合能力乘積 |

### 名稱展開說明

原始 CSV 的 `名稱` 欄格式為：`{寶可夢名稱} [{形態後綴1}] [{形態後綴2}]`

腳本將其拆解成 C～M 共 9 個獨立欄位。
無對應後綴的欄位一律填入 `-`。

**複合形態範例（同時具有兩種狀態）：**

| 原始名稱 | 寶可夢 | 地區 | 暗影 |
|----------|--------|------|------|
| 九尾 阿羅拉 暗影 | 九尾 | 阿羅拉 | 暗影 |
| 土地雲 化身 暗影 | 土地雲 | - | 暗影（型態別=化身） |
| 騎拉帝納 別種 暗影 | 騎拉帝納 | - | 暗影（其他形態=別種） |

---

## 已知來源問題與修正

### CP 欄標頭錯置

網站匯出的原始 CSV 標頭共 **17 欄**，但資料列實際有 **18 欄**。
「等級」之後缺少「CP」欄標頭，導致 K 欄起全部錯位一格。

腳本中的 `fix_cp_header()` 會自動偵測並補齊，在「等級」後插入「CP」欄標頭。

> **若未來來源網站已修正欄位對齊**，`fix_cp_header()` 的條件判斷不會觸發，無需調整腳本。

---

## 後處理流程（每個檔案自動執行）

1. 儲存下載檔案
2. 轉換為 **UTF-8 with BOM**（確保 Excel 正確顯示中文）
3. 偵測並修正 CP 欄標頭錯置（如適用）
4. 展開 `名稱` 欄為 9 個分類欄位
5. 依指定欄位順序重新排列輸出
6. 輸出同名 **`.parquet`** 檔案（所有欄位保留字串型態，避免數值推斷錯誤）
