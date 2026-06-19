# 1-Pokemon_Full_Scraper.py

寶可夢圖鑑完整爬蟲，從台灣官方寶可夢網站擷取 #0001～#1025 的完整資料（**包含所有地區型態與特殊型態**），並自動補充 Pokémon GO 戰鬥基礎數值與各等級最大 CP，最終同時輸出 CSV 與 Parquet 兩種格式。

---

## 輸出檔案

| 檔案 | 格式 | 說明 |
|------|------|------|
| `PVPCSV/a.POKEMON LIST.csv` | UTF-8 BOM CSV | 可直接用 Excel 開啟 |
| `PVPCSV/a.POKEMON LIST.parquet` | Apache Parquet | 供 pandas / Spark 等工具使用 |

### 欄位說明

| 欄位 | 型別 | 說明 | 範例 |
|------|------|------|------|
| 代號 | int | 圖鑑編號 | `6` |
| 名稱 | str | 該型態的名稱 | `噴火龍` |
| 樣貌 | str | 型態關鍵字 | `超級X` |
| 屬性 | str | 屬性，多屬性以 `\|` 分隔 | `火\|龍` |
| 弱點 | str | 弱點，多弱點以 `\|` 分隔 | `地面\|岩石\|龍` |
| ATK | int | GO 基礎攻擊 | `223` |
| DEF | int | GO 基礎防禦 | `173` |
| HP | int | GO 基礎體力 | `186` |
| LV15 (Research) | int | 等級 15 最大 CP（15/15/15 IV）| `1831` |
| LV20 (Raids/Eggs) | int | 等級 20 最大 CP | `2449` |
| LV25 (Weather Boost) | int | 等級 25 最大 CP | `3061` |
| LV40 | int | 等級 40 最大 CP | `4292` |
| LV50 | int | 等級 50 最大 CP | `4851` |

### 資料範例

```
代號,名稱,樣貌,屬性,弱點,ATK,DEF,HP,LV15 (Research),LV20 (Raids/Eggs),LV25 (Weather Boost),LV40,LV50
1,妙蛙種子,一般,草|毒,火|飛行|冰|超能力,118,111,128,477,637,796,1115,1260
3,妙蛙花,超級,草|毒,火|飛行|冰|超能力,198,189,190,1166,1554,1943,2720,3075
6,噴火龍,一般,火|飛行,水|電|岩石,223,173,186,1831,2449,3061,4292,4851
6,噴火龍,超級X,火|龍,地面|岩石|龍,273,213,186,2239,2992,3740,5241,5924
37,六尾,阿羅拉,冰,火|岩石|格鬥|鋼,145,126,146,953,1274,1592,2232,2523
```

---

## 流程架構

```
Phase 1：爬蟲（portal-pokemon.com）
  ├─ 並發爬取 #0001~#1025 所有型態
  ├─ 即時寫入進度暫存（斷點續傳）
  └─ 收集：代號、名稱、樣貌、屬性、弱點

Phase 2：補充基礎數值（pvpoke GitHub）
  ├─ 下載 pvpoke gamemaster pokemon.json
  ├─ 依代號 + 型態匹配 ATK / DEF / HP
  └─ 以 Simplified CP 公式計算 LV15/20/25/40/50 最大 CP

Phase 3：輸出
  ├─ PVPCSV/a.POKEMON LIST.csv   (UTF-8 BOM)
  └─ PVPCSV/a.POKEMON LIST.parquet
```

---

## CP 計算公式

採用與 [db.pokemongohub.net](https://db.pokemongohub.net) 一致的 Simplified 公式（不對體力預先取整）：

$$CP = \left\lfloor \frac{(A + IV) \times \sqrt{D + IV} \times \sqrt{HP + IV} \times CPM^2}{10} \right\rfloor$$

| 變數 | 說明 |
|------|------|
| A / D / HP | 各寶可夢 GO 基礎種族值 |
| IV | 個體值，此處固定為 15（最大值）|
| CPM | 等級係數（Level Scalar），見下表 |

**CPM 關鍵值（來源：pogoapi.net）**

| 等級 | CPM | 用途 |
|------|-----|------|
| 15 | 0.51739395 | Field Research 獎勵 |
| 20 | 0.59740001 | Raid / 蛋孵化 |
| 25 | 0.66793400 | 天氣加成捕獲 |
| 40 | 0.79030001 | 一般最大強化 |
| 50 | 0.84029999 | 傳說強化上限 |

---

## 環境需求

```
Python 3.10+
requests
beautifulsoup4
pandas
pyarrow
```

```bash
pip install requests beautifulsoup4 pandas pyarrow
```

---

## 執行方式

```bash
python "1-Pokemon_Full_Scraper.py"
```

執行後顯示即時進度：

```
待處理代號：1025 個（含所有型態）
預計時間：約 1.5 分鐘

  [   1/1025]   0.1%  #   1 妙蛙種子   [1 型態] 一般
  [   2/1025]   0.2%  #   2 妙蛙草     [1 型態] 一般
  [   3/1025]   0.3%  #   3 妙蛙花     [3 型態] 一般 + 超極巨化 + 超級妙蛙花
  ...

── 補充基礎數值（ATK / DEF / HP / CP）──
  ▸ 從 pvpoke GitHub 取得基礎數值...
  ▸ 載入 1025 個代號的基礎數值

── 輸出檔案 ──
  ▸ CSV  → D:\AI Project\PVPCSV\a.POKEMON LIST.csv
  ▸ Parquet → D:\AI Project\PVPCSV\a.POKEMON LIST.parquet

完成！共 1251 筆（含所有型態）
進度暫存已清除
```

---

## 主要設定參數

位於腳本頂部，可依需求調整：

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `START` / `END` | `1` / `1025` | 抓取的代號範圍 |
| `MAX_WORKERS` | `5` | 並發請求數（勿設過高）|
| `DELAY` | `0.25` 秒 | 每次請求間隔 |
| `MAX_RETRIES` | `3` | 請求失敗最多重試次數 |
| `MAX_FORMS` | `25` | 每個代號最多嘗試幾個 `_N` |
| `OUTPUT_CSV` | `PVPCSV/a.POKEMON LIST.csv` | CSV 輸出路徑 |
| `OUTPUT_PARQUET` | `PVPCSV/a.POKEMON LIST.parquet` | Parquet 輸出路徑 |
| `PVPOKE_URL` | pvpoke GitHub raw URL | 基礎數值來源 |

---

## 斷點續傳

中途中斷不會遺失進度。爬蟲進行中的結果即時存於 `POKELIST_full_progress.csv`（專案根目錄），重新執行時自動偵測並從上次完成的代號繼續。全部完成後暫存檔自動刪除。

> **注意**：斷點續傳只對爬蟲階段有效；基礎數值補充每次都會重新從 pvpoke 拉取（通常不到 5 秒，可接受）。

---

## 型態名稱萃取邏輯

```
URL 無底線 (_)
  └─ 樣貌 = "一般"

URL 有底線 (_N)
  ├─ 頁面有 subname 文字
  │    ├─ 結尾含「的樣子」→ 去除後綴
  │    ├─ 結尾含「形態」  → 去除後綴
  │    └─ 其他           → 直接使用原文
  └─ 頁面無 subname（超級進化等）
       └─ 使用 main-name 作為型態標籤
```

**型態對應範例：**

| URL 格式 | 頁面 subname | 樣貌 | pvpoke suffix |
|----------|-------------|------|--------------|
| `0037` | — | `一般` | `""` |
| `0037_1` | `阿羅拉的樣子` | `阿羅拉` | `alolan` |
| `0003_1` | `超極巨化` | `超極巨化` | `gmax` |
| `0150_1` | — / `超級超夢Ｘ` | `超級X` | `mega_x` |
| `0386_1` | `攻擊形態` | `攻擊` | — |

---

## pandas 分析範例

```python
import pandas as pd

# 讀取 Parquet（推薦，更快）
df = pd.read_parquet("PVPCSV/a.POKEMON LIST.parquet")

# 也可讀 CSV
# df = pd.read_csv("PVPCSV/a.POKEMON LIST.csv", encoding="utf-8-sig")

# 篩選特定型態
df[df["樣貌"] == "阿羅拉"]

# 展開屬性統計
df["屬性"].str.split("|").explode().value_counts()

# 找 LV40 CP 前 10 名（一般型態）
df[df["樣貌"] == "一般"].nlargest(10, "LV40")[["代號","名稱","ATK","DEF","HP","LV40"]]

# 找適合超級聯盟（CP≤1500）的高 CP 寶可夢
df[df["LV25 (Weather Boost)"] <= 1500].nlargest(20, "LV25 (Weather Boost)")

# 找弱點包含火的所有型態
df[df["弱點"].str.contains("火")]
```

---

## 輸出統計（最後一次執行結果）

| 項目 | 數量 |
|------|------|
| 總筆數 | 1,251 |
| 一般型態 | 1,025 |
| 特殊型態 | 226 |
| 有多型態的代號數 | 182 |

---

## 資料來源

| 資料 | 來源 |
|------|------|
| 代號、名稱、屬性、弱點 | [台灣官方寶可夢圖鑑](https://tw.portal-pokemon.com/play/pokedex/) |
| ATK / DEF / HP 種族值 | [pvpoke GitHub](https://github.com/pvpoke/pvpoke)（`src/data/gamemaster/pokemon.json`）|
| CPM 等級係數 | [pogoapi.net](https://pogoapi.net/api/v1/cp_multiplier.json)（L45.5-L50 以 +0.0025 外插）|
