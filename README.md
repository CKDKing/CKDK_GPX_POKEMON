# CKDK POKE

個人 Pokémon GO 全功能輔助工具，單一 HTML 檔案，無需安裝、無需伺服器，直接用瀏覽器開啟即可使用。

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
| 圖片 | Base64 內嵌（無外部檔案依賴，~21MB） |

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

---

## 品牌 / 外觀

- **應用名稱**：CKDK POKE
- **瀏覽器分頁圖示（favicon）**：Pokemon 30th Logo（Base64 內嵌）
- **Header 圖示**：Pokemon GO Logo（w-11 h-11，Base64 內嵌）
- **Header 標題**：漸層文字（brand-primary → white → brand-secondary）

---

## 檔案結構

```
AI Project/
├── index_OK.html          # 主程式（唯一需要的檔案，~21MB）
└── README.md              # 本說明文件
```

> 所有圖片資源皆已 Base64 內嵌於 HTML 中，開啟單一檔案即為完整應用。

---

## 注意事項

- 部分嵌入頁面因 CORS 政策可能無法直接嵌入，會顯示友善提示並提供新分頁連結
- 檔案較大（約 21MB），初次載入請稍候
- 建議使用 Chrome / Edge 最新版本以獲得最佳體驗
- 活動資訊預設開啟，每日自動更新一次
