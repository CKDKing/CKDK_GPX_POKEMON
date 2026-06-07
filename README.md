# CKDK GPX APP — 寶可夢 GO 工具整合平台

單一 HTML 檔案，免安裝、免後端。整合地圖編輯、路徑管理、寶可夢查詢、PK 對戰分析與常用工具連結。

---

## 功能模組

### iToolsBT 最愛位置
- 匯入 iToolsBT 匯出的 `FavoriteLists.json`
- 手風琴式多層分類清單，支援展開 / 收合
- 地圖點選快速定位，拖曳標記同步更新座標

### iToolsBT 路徑編輯
- 視覺化編輯 GPX 路徑節點
- 每個節點可拖曳微調，左側卡片即時同步
- 調整速度、間距等基本參數，匯出飛人格式 GPX

### Android 飛人寶可夢
- 匯入 `.gpx` / `.json` 軌跡檔
- 地標（Waypoints）與路線（Routes）分頁管理
- 地標排序、批次複製、刪除、去重偵測
- 路線內軌跡點細節編輯（右鍵座標選單）
- 儲存為標準 XML GPX

### 字串產生器
產生 Pokémon GO 搜尋字串，點擊按鈕自動組合條件並插入游標位置。

| 條件類型 | 說明 | 分隔符 |
|---|---|---|
| 寶可夢選擇 | 輸入編號或中文名稱篩選，點擊插入；支援 +進化體系 | `,` |
| CP / HP 比較 | `>`、`<`、`=` 運算符 + 預設值快捷鈕 | `&` |
| 自定義 CP | 輸入數值產生 CP- 或 CP- 範圍字串 | `&` |
| 星級 | 0★ ~ 4★（完美），含複合快捷鈕 | `&` |
| 分類 | 色違、傳說、幻、極巨化等，支援 要 / 不要 | `&` |
| 時間 | 今日、近 7 日、近 30 日 | `&` |
| 尺寸 | XXS / XS / XL / XXL，支援 要 / 不要 | `&` |
| 體質 | 迷你、鉅大，支援 要 / 不要 | `&` |
| 地區 | 關都→帕底亞（全 9 世代），支援 要 / 不要 | `,` |
| 屬性 | 18 種屬性；單屬性多選用 `,`，多屬性連集用 `&` | `,` / `&` |
| 登錄 / 道具進化 | 新進化、道具、進化&未登錄 | `&` |
| 特別條件 | 影子、淨化、幸運、穿梭等，支援 要 / 不要 | `&` |

**自動插入規則**
- 去除空格；自動補連接符；重複 `&&` → `&`、`,,` → `,`；開頭 `&` / `,` 自動清除

#### PK 對戰分析
選擇對手的 1 ~ 2 種屬性，點擊「分析最佳攻擊屬性」後顯示兩欄結果：

| 欄位 | 內容 |
|---|---|
| 雙屬性 TOP 10 | 153 種雙屬性組合，依最高攻擊倍率排序，顯示主攻屬性備註 |
| 單屬性 TOP 10 | 18 種單一攻擊屬性，依效率排序 |

點擊任意列，直接將屬性組合插入字串框。

#### 屬性克制圖
底部橫向輪播列（7 張參考圖），左右箭頭切換，點擊放大查閱。

### 寶可夢查詢
- 內建全世代寶可夢清單（含編號、中 / 日 / 英文名稱）
- 輸入關鍵字即時篩選，點擊任一隻嵌入顯示 52Poke Wiki 詳細資料
- 資料來源：[wiki.52poke.com](https://wiki.52poke.com/wiki/)

### 抓寶查詢

| 工具 | 網址 | 顯示方式 |
|---|---|---|
| IV100 | [moonani.com/PokeList/index.php](https://moonani.com/PokeList/index.php) | 嵌入 |
| 報寶貝 | [twpkinfo.com/ipoke.aspx](https://twpkinfo.com/ipoke.aspx) | 另開分頁 |
| PVP寶可夢戰力資訊 | [pvpoketw.com](https://pvpoketw.com/) | 嵌入 |
| IV → CP | [jie-bao.online/pkg/iv2cp/](https://jie-bao.online/pkg/iv2cp/) | 嵌入 |
| CP → IV | [jie-bao.online/pkg/](https://jie-bao.online/pkg/) | 嵌入 |
| IV計算機 | [pokemon.gameinfo.io/zh-tw/tools/iv-calculator](https://pokemon.gameinfo.io/zh-tw/tools/iv-calculator) | 另開分頁 |

### 相關資訊

#### 可嵌入顯示

| 網站 | 網址 |
|---|---|
| ポケモンGO攻略 | [9db.jp/pokemongo/](https://9db.jp/pokemongo/) |
| Go Raid Finder | [9db.jp/pokego/data/62](https://9db.jp/pokego/data/62) |
| PokéBase | [pokebase.app/pokemon-go](https://pokebase.app/pokemon-go) |

#### 另開新分頁

| 網站 | 網址 |
|---|---|
| PokemonGO 官網（繁中） | [pokemongo.com/zh_hant](https://pokemongo.com/zh_hant) |
| PokemonGO 官網（多國語系） | pokemongo.com/{ja/en/ko/pt-BR/es/fr/de/th/hi/id/it/pl/ru/tr} |
| Pokémon GO Wiki | [pokemongo.fandom.com](https://pokemongo.fandom.com/wiki/Pok%C3%A9mon_GO_Wiki) |
| ポケモンGO攻略速報 | [pokemongo.gamewith.jp](https://pokemongo.gamewith.jp/) |
| Pokémon GO Database | [db.pokemongohub.net](https://db.pokemongohub.net/) |
| Pokémon Database | [pokemondb.net](https://pokemondb.net/) |
| Pocket Monsters | [pocketmonsters.net](https://www.pocketmonsters.net/) |
| Pokemon-Zone | [pokemon-zone.com](https://www.pokemon-zone.com/) |
| 寶可夢集換式卡牌（台灣） | [asia.pokemon-card.com/tw](https://asia.pokemon-card.com/tw/) |
| The Official Pokémon Website | [pokemon.com/us](https://www.pokemon.com/us) |
| 台灣寶可夢官方網站 | [tw.portal-pokemon.com](https://tw.portal-pokemon.com/) |
| PokemonGO 資訊網 | [pokemon.wingzero.tw](https://pokemon.wingzero.tw/zh-TW) |
| PokoGuide | [pokemongo.gishan.net](https://pokemongo.gishan.net/) |
| Bulbagarden | [bulbagarden.net](https://bulbagarden.net/home/) |
| PokemonGO Info | [pokemon.gameinfo.io](https://pokemon.gameinfo.io/zh-tw) |
| J-Channel Facebook | [facebook.com/J-Channel](https://www.facebook.com/p/J-Channel-100064760946461/) |
| J-Channel X | [x.com/junochannel](https://x.com/junochannel) |
| PokemonGo X (Twitter) | [x.com/pokemon](https://x.com/pokemon?lang=zh-Hant) |
| PokemonGo Facebook 社群 | [facebook.com/groups/pokemongo](https://www.facebook.com/groups/932304146879607/) |
| PokemonGo Reddit | [reddit.com/r/pokemongo](https://www.reddit.com/r/pokemongo/) |

---

## 地圖

- 底圖：CartoDB Dark（預設）、CartoDB Light、OpenStreetMap、Google 道路、Google 衛星、Google 混合
- 即時滑鼠座標顯示
- 右鍵選單 → 複製座標 / 插入地標
- 搜尋地址定位

---

## 技術架構

| 項目 | 說明 |
|---|---|
| 主程式 | 純 HTML + Vanilla JS，單檔無依賴 |
| 樣式 | Tailwind CSS CDN |
| 地圖 | Leaflet.js 1.9.4 |
| 圖示 | Lucide Icons |
| 字型 | Inter、Outfit、JetBrains Mono（Google Fonts） |
| PK 模型 | 18×18 完整屬性克制 JS 物件（Pokémon GO 倍率規則） |
| 圖片 | 7 張屬性克制圖以 Base64 內嵌，單檔可離線使用 |

---

## 檔案結構

```
AI Project/
├── CKDK_GPX_POKEMON.html        主程式（單一自含檔案，約 3.4 MB）
├── FIGHT/                       屬性克制圖原始檔（已內嵌至 HTML）
│   ├── sshot-1.png ~ sshot-7.png
├── *.gpx                        範例路徑（可直接匯入）
└── FavoriteLists_iTools_*.json  iToolsBT 最愛位置匯出檔
```

---

## 使用方式

1. 以瀏覽器直接開啟 `CKDK_GPX_POKEMON.html`（建議 Chrome / Edge）
2. 頂部導覽列切換功能模組
3. **字串產生器**：左側點擊條件 → 右側文字框即時組合 → 複製貼入遊戲搜尋欄
4. **Android 飛人**：匯入 GPX 或 JSON → 編輯節點 → 儲存標準 GPX
5. **PK 對戰**：選擇對手屬性 → 分析 → 點擊結果列插入字串

> 所有操作皆在本機執行，無任何資料上傳。圖片已內嵌，部署單一 HTML 檔案即可完整運作。
