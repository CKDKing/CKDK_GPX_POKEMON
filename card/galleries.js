/**
 * Pokémon TCG 官方圖庫 — 卡片圖片連結資料集
 *
 * ════════════════════════════════════════════════════════
 *  URL 結構
 * ════════════════════════════════════════════════════════
 *  圖庫頁面  https://tcg.pokemon.com/en-us/galleries/{slug}/
 *  卡片圖片  https://dz3we2x72f7ol.cloudfront.net/expansions/{slug}/en-us/{prefix}_EN_{n}.png
 *
 *  規則：
 *  - slug（圖庫網址路徑）與 CDN 路徑完全一致
 *  - 卡片 ID 格式固定為 {prefix}_EN_{n}，n 從 1 開始連號
 *  - 篩選 tab 由前端 JS 控制，不反映在 URL 上
 *  - CDN 需帶 Referer: https://tcg.pokemon.com/ 才會回傳 200，否則 403
 *
 * ════════════════════════════════════════════════════════
 *  Prefix 命名規則（實測歸納）
 * ════════════════════════════════════════════════════════
 *
 *  【Scarlet & Violet 系列】
 *  主系列   → SV01, SV02, SV03, SV04, SV05, SV06, SV07, SV08, SV09, SV10
 *  中間彈   → SV{n}pt5（如 SV3pt5=151、SV4pt5=Paldean Fates、SV6pt5=Shrouded Fable、SV8pt5=Prismatic Evolutions）
 *  特例     → Black Bolt & White Flare 為 SV10pt5_ZSV（加了 _ZSV 後綴，
 *             原因：gallery slug 為 "black-white"，與舊世代 Black & White 同名，
 *             CDN 以後綴區分，避免路徑衝突）
 *
 *  【Mega Evolution 系列】
 *  無統一規則，每個系列採用獨立短碼：
 *  Chaos Rising      → SN54
 *  Perfect Order     → P614
 *  Ascended Heroes   → M7XJ
 *  Phantasmal Flames → 8BXG
 *  Mega Evolution    → JL2G
 *  推測為官方內部隨機碼，無法由系列名稱推算，需逐一確認。
 *
 * ════════════════════════════════════════════════════════
 *  ★ = HEAD request 實際確認存在
 * ════════════════════════════════════════════════════════
 */

const GALLERY_BASE = "https://tcg.pokemon.com/en-us/galleries/";
const CDN_BASE     = "https://dz3we2x72f7ol.cloudfront.net/expansions/";

// 單張卡片的完整 CDN URL
function cardImageUrl(slug, cardId) {
  return `${CDN_BASE}${slug}/en-us/${cardId}.png`;
}

// 圖庫頁面 URL
function galleryUrl(slug) {
  return `${GALLERY_BASE}${slug}/`;
}

// 由 prefix + count 產生卡片 ID 陣列（連號系列用）
function generateCardIds(prefix, count) {
  return Array.from({ length: count }, (_, i) => `${prefix}_EN_${i + 1}`);
}

// 回傳某系列所有卡片的完整 CDN URL 陣列
function getAllCardUrls(set) {
  if (!set.cardPrefix || !set.cardCount) return [];
  return generateCardIds(set.cardPrefix, set.cardCount)
    .map(id => cardImageUrl(set.slug, id));
}

// ═══════════════════════════════════════════════════════════
//  系列一：MEGA EVOLUTION
// ═══════════════════════════════════════════════════════════

const MEGA_EVOLUTION = {
  era: "Mega Evolution",

  sets: [
    {
      name: "Chaos Rising",
      slug: "chaos-rising",
      galleryUrl: galleryUrl("chaos-rising"),
      cdnBase:    `${CDN_BASE}chaos-rising/en-us/`,
      cardPrefix: "SN54",  // ★ 已確認
      cardCount:  122,     // ★ SN54_EN_1 ~ SN54_EN_122
      filters: ["See All", "Mega Evolution Pokémon", "Special Art"],
    },
    {
      name: "Perfect Order",
      slug: "perfect-order",
      galleryUrl: galleryUrl("perfect-order"),
      cdnBase:    `${CDN_BASE}perfect-order/en-us/`,
      cardPrefix: "P614",  // ★ 已確認
      cardCount:  124,     // ★ P614_EN_1 ~ P614_EN_124
      filters: ["See All", "Mega Evolution Pokémon", "Special Art"],
    },
    {
      name: "Ascended Heroes",
      slug: "ascended-heroes",
      galleryUrl: galleryUrl("ascended-heroes"),
      cdnBase:    `${CDN_BASE}ascended-heroes/en-us/`,
      cardPrefix: "M7XJ",  // ★ 已確認
      cardCount:  295,     // ★ M7XJ_EN_1 ~ M7XJ_EN_295
      filters: ["See All", "Mega Evolution Pokémon", "Trainer's Pokémon", "Special Art", "Pokémon ex"],
    },
    {
      name: "Phantasmal Flames",
      slug: "phantasmal-flames",
      galleryUrl: galleryUrl("phantasmal-flames"),
      cdnBase:    `${CDN_BASE}phantasmal-flames/en-us/`,
      cardPrefix: "8BXG",  // ★ 已確認
      cardCount:  130,     // ★ 8BXG_EN_1 ~ 8BXG_EN_130
      filters: ["See All", "Mega Evolution Pokémon", "Special Art"],
    },
    {
      name: "Mega Evolution",
      slug: "mega-evolution",
      galleryUrl: galleryUrl("mega-evolution"),
      cdnBase:    `${CDN_BASE}mega-evolution/en-us/`,
      cardPrefix: "JL2G",  // ★ 已確認
      cardCount:  188,     // ★ JL2G_EN_1 ~ JL2G_EN_188
      filters: ["See All", "Mega Evolution Pokémon", "Special Art"],
    },
  ],
};

// ═══════════════════════════════════════════════════════════
//  系列二：SCARLET & VIOLET（新 → 舊）
// ═══════════════════════════════════════════════════════════

const SCARLET_VIOLET = {
  era: "Scarlet & Violet",

  sets: [
    {
      name: "Black Bolt and White Flare",
      slug: "black-white",
      galleryUrl: galleryUrl("black-white"),
      cdnBase:    `${CDN_BASE}black-white/en-us/`,
      cardPrefix: "SV10pt5_ZSV", // ★ 已確認
      cardCount:  172,            // ★ SV10pt5_ZSV_EN_1 ~ SV10pt5_ZSV_EN_172
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art"],
    },
    {
      name: "Destined Rivals",
      slug: "destined-rivals",
      galleryUrl: galleryUrl("destined-rivals"),
      cdnBase:    `${CDN_BASE}destined-rivals/en-us/`,
      cardPrefix: "SV10",  // ★ 已確認
      cardCount:  244,     // ★ SV10_EN_1 ~ SV10_EN_244
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art"],
    },
    {
      name: "Journey Together",
      slug: "journey-together",
      galleryUrl: galleryUrl("journey-together"),
      cdnBase:    `${CDN_BASE}journey-together/en-us/`,
      cardPrefix: "SV09",  // ★ 已確認
      cardCount:  190,     // ★ SV09_EN_1 ~ SV09_EN_190
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art"],
    },
    {
      name: "Prismatic Evolutions",
      slug: "prismatic-evolutions",
      galleryUrl: galleryUrl("prismatic-evolutions"),
      cdnBase:    `${CDN_BASE}prismatic-evolutions/en-us/`,
      cardPrefix: "SV8pt5", // ★ 已確認
      cardCount:  180,      // ★ SV8pt5_EN_1 ~ SV8pt5_EN_180
      filters: ["See All", "Pokémon ex", "Special Art"],
    },
    {
      name: "Surging Sparks",
      slug: "surging-sparks",
      galleryUrl: galleryUrl("surging-sparks"),
      cdnBase:    `${CDN_BASE}surging-sparks/en-us/`,
      cardPrefix: "SV08",  // ★ 已確認
      cardCount:  252,     // ★ SV08_EN_1 ~ SV08_EN_252
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art"],
    },
    {
      name: "Stellar Crown",
      slug: "stellar-crown",
      galleryUrl: galleryUrl("stellar-crown"),
      cdnBase:    `${CDN_BASE}stellar-crown/en-us/`,
      cardPrefix: "SV07",  // ★ 已確認
      cardCount:  175,     // ★ SV07_EN_1 ~ SV07_EN_175
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art"],
    },
    {
      name: "Shrouded Fable",
      slug: "shrouded-fable",
      galleryUrl: galleryUrl("shrouded-fable"),
      cdnBase:    `${CDN_BASE}shrouded-fable/en-us/`,
      cardPrefix: "SV6pt5", // ★ 已確認
      cardCount:  99,       // ★ SV6pt5_EN_1 ~ SV6pt5_EN_99
      filters: ["See All", "Pokémon ex", "Special Art"],
    },
    {
      name: "Twilight Masquerade",
      slug: "twilight-masquerade",
      galleryUrl: galleryUrl("twilight-masquerade"),
      cdnBase:    `${CDN_BASE}twilight-masquerade/en-us/`,
      cardPrefix: "SV06",  // ★ 已確認
      cardCount:  226,     // ★ SV06_EN_1 ~ SV06_EN_226
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art"],
    },
    {
      name: "Temporal Forces",
      slug: "temporal-forces",
      galleryUrl: galleryUrl("temporal-forces"),
      cdnBase:    `${CDN_BASE}temporal-forces/en-us/`,
      cardPrefix: "SV05",  // ★ 已確認
      cardCount:  218,     // ★ SV05_EN_1 ~ SV05_EN_218
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art"],
    },
    {
      name: "Paldean Fates",
      slug: "paldean-fates",
      galleryUrl: galleryUrl("paldean-fates"),
      cdnBase:    `${CDN_BASE}paldean-fates/en-us/`,
      cardPrefix: "SV4pt5", // ★ 已確認
      cardCount:  245,      // ★ SV4pt5_EN_1 ~ SV4pt5_EN_245
      filters: ["See All", "Shiny Pokémon ex", "Shiny Pokémon", "Special Art"],
    },
    {
      name: "Paradox Rift",
      slug: "paradox-rift",
      galleryUrl: galleryUrl("paradox-rift"),
      cdnBase:    `${CDN_BASE}paradox-rift/en-us/`,
      cardPrefix: "SV04",  // ★ 已確認
      cardCount:  266,     // ★ SV04_EN_1 ~ SV04_EN_266
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art"],
    },
    {
      name: "151",
      slug: "151",
      galleryUrl: galleryUrl("151"),
      cdnBase:    `${CDN_BASE}151/en-us/`,
      cardPrefix: "SV3pt5", // ★ 已確認
      cardCount:  207,      // ★ SV3pt5_EN_1 ~ SV3pt5_EN_207
      filters: ["See All", "Pokémon ex", "Special Art"],
    },
    {
      name: "Obsidian Flames",
      slug: "obsidian-flames",
      galleryUrl: galleryUrl("obsidian-flames"),
      cdnBase:    `${CDN_BASE}obsidian-flames/en-us/`,
      cardPrefix: "SV03",  // ★ 已確認
      cardCount:  230,     // ★ SV03_EN_1 ~ SV03_EN_230
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art"],
    },
    {
      name: "Paldea Evolved",
      slug: "paldea-evolved",
      galleryUrl: galleryUrl("paldea-evolved"),
      cdnBase:    `${CDN_BASE}paldea-evolved/en-us/`,
      cardPrefix: "SV02",  // ★ 已確認
      cardCount:  279,     // ★ SV02_EN_1 ~ SV02_EN_279
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art"],
    },
    {
      name: "Scarlet & Violet",
      slug: "scarlet-violet",
      galleryUrl: galleryUrl("scarlet-violet"),
      cdnBase:    `${CDN_BASE}scarlet-violet/en-us/`,
      cardPrefix: "SV01",  // ★ 已確認
      cardCount:  258,     // ★ SV01_EN_1 ~ SV01_EN_258
      filters: ["See All", "Pokémon ex", "Tera Pokémon ex", "Special Art", "New Pokémon"],
    },
  ],
};

// ═══════════════════════════════════════════════════════════
//  匯出
// ═══════════════════════════════════════════════════════════

const ALL_GALLERIES = [MEGA_EVOLUTION, SCARLET_VIOLET];

const GALLERY_BY_SLUG = Object.fromEntries(
  ALL_GALLERIES.flatMap(era => era.sets).map(set => [set.slug, set])
);

// exposed as globals for classic script usage
