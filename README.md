# CKDK POKE

個人 Pokémon GO 全功能輔助工具，單一 HTML 檔案，無需安裝、無需伺服器，直接用瀏覽器開啟即可使用。  
共 **14 個功能模組**，含地圖、PVP 榜單、IV 查詢、活動時程等。

---

## 快速開始

```
直接用瀏覽器開啟 index_OK.html
```

無需 Node.js、無需後端、無網路亦可使用大部分功能（部分功能需連線爬取資料）。  
開啟後預設直接進入「活動資訊」頁籤。

---

## 功能模組

| 頁籤 | 功能說明 |
|------|----------|
| **活動資訊** | 自動爬取 WingZero 活動頁面，顯示正在進行 / 即將開始的活動，並以 Gantt 時間軸呈現所有活動期間。每日快取一次，切換頁籤不重複爬取。 |
| **PVP 對戰** | PVP 輔助中心，包含「PVP 榜單查詢」與「CP 計算機」兩個子功能（見下方詳述）。 |
| **iToolsBT 最愛位置** | 管理 iToolsBT 常用座標，支援分類、新增、刪除、地圖顯示，可匯出 JSON 供 iToolsBT 使用。 |
| **iToolsBT 路徑編輯** | 匯入 / 編輯 / 匯出 iToolsBT 路徑 GPX 檔案，支援點位拖曳、順序調整。 |
| **IV100 狙擊** | 快速查詢與標記 IV100 寶可夢座標。 |
| **粉蝶蟲位置** | 顯示全球各地區粉蝶蟲花紋對應座標，輔助收集。 |
| **字串產生器** | 產生 Pokémon GO 搜尋用字串（例如 IV 篩選、名稱篩選）。 |
| **Android 飛人寶可夢** | 管理 Android 模擬位置的目標寶可夢清單，地圖顯示座標。 |
| **寶可夢查詢** | 透過 52poke wiki 查詢寶可夢詳細資料，右側預設隨機顯示 5 張歡迎圖（填滿）。 |
| **抓寶查詢** | 整合 LeekDuck、GoHub、SnackNap 等抓寶資訊，右側預設隨機顯示 4 張歡迎圖（填滿）。 |
| **屬性攻擊調查** | 進入時自動載入 DialgaDex 屬性強者，快速查看各屬性最佳攻擊手。 |
| **相關資訊** | 整合 9db.jp、PokéBase、Leek Duck、Serebii.net 等相關連結，右側預設隨機顯示 3 張歡迎圖（填滿）。 |
| **交換列表** | 管理個人交換需求清單。 |
| **Pokémon Champions** | Pokémon Champions 賽事資訊、賽制說明與選手追蹤。 |

---

## PVP 對戰詳細說明

### PVP 榜單查詢

賽博龐克霓虹紫主題的 PVP 排行資料庫。12 個聯盟的 CSV 資料完整嵌入 HTML，無需網路即可查閱。

**支援聯盟（共 12 個）：**

| 分類 | 聯盟名稱 |
|------|---------|
| 大師聯盟 CP10000 | 大師聯盟：超級版、大師聯盟、Battle Frontier (Master) |
| 高級聯盟 CP2500 | 高級聯盟、Battle Frontier (UL Retro) |
| 超級聯盟 CP1500 | 超級聯盟、Battle Frontier (Bayou Cup)、Battle Frontier (Spellcraft Cup)、NAIC 2026 Championship Series Cup、Devon Bastille Cup、Devon Equinox Cup、陽光盃 |

**三種查詢模式：**

| 聯盟 | 寶可夢 | 結果 |
|------|--------|------|
| 未選 | 已選 | 全部 12 聯盟掃描，帶出此寶可夢所有出現行（含暗影、Mega、各型態），表格加入「聯盟」欄 |
| 已選 | 已選 | 指定聯盟篩選此寶可夢 |
| 已選 | 未選 | 顯示指定聯盟完整排行 |

**表格欄位（共 25 欄，排除 Stat Product）：**

> 名次 / 評分 / 圖鑑編號 / 寶可夢 / 第一屬性 / 第二屬性 / 地區 / 型態別 / 暗影 / Mega進化 / 其他形態 / 性別 / 尺寸 / 天氣 / CP / 攻擊力 / 防禦力 / HP / 等級 / 一般招式 / 特殊招式1 / 特殊招式2 / 幾下可用特招1 / 幾下可用特招2 / 夥伴行走距離 / 開第二招星塵花費

**視覺特色：**
- 「名次」欄固定於左側（sticky），橫向捲動不消失
- 評分依分數區間顯示霓虹紫色調（≥ 95 最亮紫 → 60 以下灰）
- 屬性欄位顯示彩色徽章（18 種屬性各有配色）
- 前三名：🥇 金 / 🥈 銀 / 🥉 銅 左邊框高亮

**招式符號說明：**

| 符號 | 顏色樣式 | 意義 |
|------|---------|------|
| `*` | 琥珀色粗體大字 | 精選技能（Elite TM 習得）|
| `†` | 琥珀色粗體大字 | 舊有限定技能（已停止更新但持有者仍保留）|
| `‡` | 霓虹紫 | 特殊活動限定技能 |

**搜尋功能：**
- **寶可夢搜尋欄**（側邊欄）：輸入圖鑑編號或名稱，即時顯示下拉候選清單，選定後作為查詢條件
- **資料表格搜尋**（工具列）：資料載入後可即時篩選名稱、圖鑑編號、屬性、招式

### CP 計算機

根據目標 CP 上限，計算各等級、各 IV 組合的 CP 值，協助選擇對戰最佳個體。

---

## 技術架構

| 項目 | 內容 |
|------|------|
| 架構 | 單一 HTML 檔案（All-in-One） |
| 樣式 | Tailwind CSS（CDN） |
| 地圖 | Leaflet.js 1.9.4 |
| 圖示 | Lucide Icons |
| 字型 | Inter / Outfit / JetBrains Mono（Google Fonts） |
| 資料爬取 | CORS Proxy 鏈（allorigins → corsproxy.io → 本地 fallback） |
| 快取 | localStorage（`ckdk_pgo_events_v1`，每日一次） |
| 圖片 | Base64 內嵌（無外部檔案依賴，~23MB）|
| PVP 資料 | 12 個聯盟 CSV 嵌入為 JS 字串（約 700 KB） |

---

## 活動資訊爬蟲說明

- 資料來源：[pokemon.wingzero.tw](https://pokemon.wingzero.tw/zh-TW/data/pokemon-go-events)
- 每日首次開啟時自動爬取，結果存入 `localStorage`
- 同一天內切換頁籤或重開應用不重複爬取（`window.wingZeroEventsLoaded` flag）
- 網路不通時使用內建 fallback 資料
- 強制刷新：清除瀏覽器 localStorage 中的 `ckdk_pgo_events_v1`

### Gantt 時間軸說明

| 狀態 | 顏色 | 下方資訊 |
|------|------|----------|
| 進行中 | 綠色漸層 + 閃亮綠點 | `→ MM/dd` + 離結束 N 天 |
| 已結束 | 灰色漸層 + 白色「已結束」標籤 | `MM/dd 已結束` |
| 尚未開始 | 淡黃色漸層（黑字） | 離開始 N 天 + 活動天數 N 天 |
| 單日活動 | 依類型顏色 | `MM/dd 當天` |

活動類型色系：RAID 紅、MEGA 橙、PvP 藍、RES 紫、EVT 青綠  
TODAY 進度插線：霓虹琥珀色（`rgba(251,191,36,0.9)`）  
TODAY 軸標記：X 軸日期欄 + 閃亮光圈，Y 軸垂直琥珀色進度線

### 活動資訊側邊欄

| 順序 | 連結 |
|------|------|
| 1 | Leek Duck 團戰頭目 |
| 2 | Leek Duck 活動時程 |
| 3 | GoHub 目前團戰頭目 |
| 4 | SnackNap 團戰資訊 |

側邊欄底部配置裝飾圖片及標題圖。

---

## 各模組歡迎頁面圖片集

| 模組 | 圖片數 | 呈現方式 |
|------|--------|----------|
| 寶可夢查詢 | 5 張隨機 | object-cover 填滿 |
| 抓寶查詢 | 4 張隨機 | object-cover 填滿 |
| 相關資訊 | 3 張隨機 | object-cover 填滿 |
| 屬性攻擊調查 | — | 自動載入 DialgaDex |

所有圖片皆以 Base64 內嵌，無需外部檔案。

---

## 相關資訊側邊欄連結

| 位置 | 網站 | 嵌入方式 |
|------|------|----------|
| 1 | ポケモンGO攻略 (9db.jp) | 可嵌入 |
| 2 | Go Raid Finder (9db.jp) | 可嵌入 |
| 3 | PokéBase | 可嵌入 |
| 4 | Leek Duck | 可嵌入 |
| 5 | PokemonGoHub | 可嵌入 |
| 6 | Serebii.net | 可嵌入 |
| 7 | ★Snacknap | 可嵌入 |
| 8 | ★DialgaDex | 可嵌入 |
| 9 | 遊々亭 | 可嵌入 |
| 10 | PokeData PTCG | 可嵌入 |

---

## 響應式設計

| 裝置 | 斷點 | 說明 |
|------|------|------|
| 手機版 | ≤ 767px | 側邊欄轉為抽屜式滑入，觸控按鈕 min-h 36px，字體最小 10px 保護 |
| 平板版 | 768–1024px | 側邊欄縮窄至 300px |
| 桌機版 | > 1024px | 完整雙欄布局，側邊欄 450px |

Gantt 時間軸支援 `-webkit-overflow-scrolling:touch` 手機橫滑順暢捲動。

### PVP 榜單查詢 響應式設計

| 裝置 | 說明 |
|------|------|
| 桌機 | 工具列單排：圖示 / 標題 / 筆數 / 搜尋欄；表格橫向捲動，名次欄固定左側 |
| 手機 | 左上 ☰ 開啟側邊欄 Overlay；工具列搜尋欄自動折行為第二排（100% 寬）；表格支援觸控橫滑（`-webkit-overflow-scrolling:touch`）；歡迎畫面顯示手機操作提示 |

---

## 品牌 / 外觀

- **應用名稱**：CKDK POKE
- **瀏覽器分頁圖示（favicon）**：Pokemon 30th Logo（Base64 內嵌）
- **Header 圖示**：Pokemon GO Logo（w-11 h-11，Base64 內嵌）
- **Header 標題**：漸層文字（brand-primary → white → brand-secondary）

---

## 檔案結構

```
D:\AI Project\
├── index_OK.html          # 主程式（唯一需要的檔案，~23MB）
├── README.md              # 本說明文件
└── PVPCSV\                # PVP 榜單原始 CSV（已嵌入 HTML，此資料夾供日後更新用）
    ├── 大師聯盟：超級版 CP10000.csv
    ├── 大師聯盟 CP10000.csv
    ├── Battle Frontier (Master) CP10000.csv
    ├── 高級聯盟 CP2500.csv
    ├── Battle Frontier (UL Retro) CP2500.csv
    ├── 超級聯盟 CP1500.csv
    ├── Battle Frontier (Bayou Cup) CP1500.csv
    ├── Battle Frontier (Spellcraft Cup) CP1500.csv
    ├── NAIC 2026 Championship Series Cup CP1500.csv
    ├── Devon Bastille Cup CP1500.csv
    ├── Devon Equinox Cup CP1500.csv
    └── 陽光盃 CP1500.csv
```

> 所有圖片資源皆已 Base64 內嵌，PVP 榜單資料以 JS 字串嵌入，開啟單一 HTML 檔案即為完整應用。

### 更新 PVP 榜單資料

若日後聯盟排行有新資料，更新步驟：

1. 替換 `PVPCSV\` 中對應的 CSV 檔案
2. 以 PowerShell 或腳本讀取 CSV 內容，替換 `index_OK.html` 中 `const PVP_LB_DATA` 物件對應的 key 值
3. 確保 CSV 內容不含反引號（`` ` ``）與 `${`（這兩者會破壞 JS 樣板字串）

---

## 注意事項

- 部分嵌入頁面因 CORS 政策可能無法直接嵌入，會顯示友善提示並提供新分頁連結
- 檔案較大（約 23 MB），初次載入請稍候數秒
- 建議使用 Chrome / Edge 最新版本以獲得最佳體驗
- 活動資訊預設開啟，每日自動更新一次
- PVP 榜單資料完整內嵌，無網路環境下仍可正常查詢
- 手機使用 PVP 榜單時，建議橫屏瀏覽以獲得更好的表格閱讀體驗
