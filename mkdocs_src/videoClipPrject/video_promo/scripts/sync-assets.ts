#!/usr/bin/env node
/**
 * sync-assets.ts — v2
 * ──────────────────────────────────────────────────────────────────────────────
 * Syncs gallery screenshots AND manually-placed AI assets into public/assets/.
 *
 * Output structure in public/assets/:
 *   shared/                  ← logo, favicon (lingua-indipendenti)
 *   ai/                      ← asset generati manualmente (chaos_bg, opensource)
 *   en/dark/desktop/         ← screenshot desktop dark EN
 *   en/dark/mobile/          ← screenshot mobile dark EN
 *   en/light/desktop/        ← screenshot desktop light EN
 *   en/light/mobile/         ← screenshot mobile light EN
 *   (idem per it / es / fr)
 *
 * Source di verità:
 *   - gallery → mkdocs_src/docs/gallery/{desktop,mobile}/{locale}/{dark,light}/
 *   - AI assets → mkdocs_src/videoClipPrject/external_src/ai/   (piazzati a mano)
 *   - shared → mkdocs_src/docs/static/
 *
 * Usage:
 *   npm run sync
 *   (auto-eseguito da prebuild:* hooks)
 * ──────────────────────────────────────────────────────────────────────────────
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const VIDEO_PROMO = path.resolve(__dirname, "..");           // …/video_promo
const MKDOCS_SRC  = path.resolve(VIDEO_PROMO, "../..");       // …/mkdocs_src
const GALLERY     = path.resolve(MKDOCS_SRC, "docs/gallery");
const STATIC      = path.resolve(MKDOCS_SRC, "docs/static");
const AI_DIR      = path.resolve(VIDEO_PROMO, "public/ai");   // AI assets: permanent home
const ASSETS_OUT  = path.resolve(VIDEO_PROMO, "public/assets");

// ──────────────────────────────────────────────────────────────────────────────
// Locales & themes to sync
// ──────────────────────────────────────────────────────────────────────────────
const LOCALES = ["en", "it", "es", "fr"] as const;
const THEMES  = ["dark", "light"] as const;

// ──────────────────────────────────────────────────────────────────────────────
// Per-scene asset mappings (relative to gallery/{desktop|mobile}/{locale}/{theme}/)
// key   = logical name used in scenes
// value = source path relative to the theme folder
// ──────────────────────────────────────────────────────────────────────────────
const DESKTOP_ASSETS: Record<string, string> = {
  "dashboard_main.png":       "dashboard/main.png",
  "dashboard_allocation.png": "dashboard/allocation-charts.png",
  "echarts_view.png":         "assets/detail-chart.png",
  "datatable_view.png":       "assets/list.png",
  "signals_view.png":         "assets/detail-signals.png",
  "fx_chart.png":             "fx/detail-chart.png",
};

const MOBILE_ASSETS: Record<string, string> = {
  "dashboard_main.png":   "dashboard/main.png",
  "assets_chart.png":     "assets/detail-chart.png",
  "assets_list.png":      "assets/list.png",
};

// Shared assets (logo, favicon) — copied once, no locale variation
const SHARED_ASSETS: Array<{ src: string; dest: string; desc: string }> = [
  { src: path.join(STATIC, "logo.png"),    dest: "shared/logo.png",    desc: "LibreFolio logo" },
  { src: path.join(STATIC, "favicon.png"), dest: "shared/favicon.png", desc: "Favicon" },
];

// AI-generated assets — permanently in public/ai/
// No copy needed: just verify they exist so the build warning is informative.
const AI_ASSETS = [
  "chaos_bg.png",
  "opensource_infographic.png",
  "audio_track.mp3",
];

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────
function getMtime(p: string): number {
  try { return fs.statSync(p).mtimeMs; }
  catch { return -1; }
}

function ensureDir(dir: string): void {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function syncFile(src: string, destRel: string, desc: string, stats: SyncStats): void {
  const dest = path.join(ASSETS_OUT, destRel);
  const srcMtime = getMtime(src);

  if (srcMtime === -1) {
    console.warn(`  ⚠️  MISSING   ${destRel}  (${desc})`);
    stats.missing++;
    return;
  }

  const destMtime = getMtime(dest);
  if (destMtime >= srcMtime) {
    // console.log(`  ✅  OK        ${destRel}`);   // uncomment for verbose
    stats.upToDate++;
    return;
  }

  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
  const action = destMtime === -1 ? "COPIED  " : "UPDATED ";
  console.log(`  📦  ${action}  ${destRel}`);
  stats.copied++;
}

interface SyncStats { copied: number; upToDate: number; missing: number; }

// ──────────────────────────────────────────────────────────────────────────────
// Main
// ──────────────────────────────────────────────────────────────────────────────
console.log("🔄  sync-assets v2 — LibreFolio video_promo\n");
const stats: SyncStats = { copied: 0, upToDate: 0, missing: 0 };

// 1. Shared (logo, favicon)
console.log("── Shared assets ─────────────────────────");
for (const { src, dest, desc } of SHARED_ASSETS) {
  syncFile(src, dest, desc, stats);
}

// 2. AI-generated assets — check presence in public/ai/ (no copy needed)
console.log("\n── AI-generated assets (public/ai/) ────────");
for (const name of AI_ASSETS) {
  const fullPath = path.join(AI_DIR, name);
  if (getMtime(fullPath) === -1) {
    console.warn(`  ⚠️  MISSING   ai/${name}  → see PROMPT_*.md in public/ai/`);
    stats.missing++;
  } else {
    console.log(`  ✅  PRESENT   ai/${name}`);
    stats.upToDate++;
  }
}

// 3. Gallery → per locale × theme × device
for (const locale of LOCALES) {
  console.log(`\n── Gallery ${locale.toUpperCase()} ────────────────────────────`);
  for (const theme of THEMES) {
    // Desktop
    const desktopSrc = path.join(GALLERY, "desktop", locale, theme);
    for (const [logicalName, relPath] of Object.entries(DESKTOP_ASSETS)) {
      syncFile(
        path.join(desktopSrc, relPath),
        `${locale}/${theme}/desktop/${logicalName}`,
        `desktop ${locale}/${theme}/${logicalName}`,
        stats
      );
    }
    // Mobile
    const mobileSrc = path.join(GALLERY, "mobile", locale, theme);
    for (const [logicalName, relPath] of Object.entries(MOBILE_ASSETS)) {
      syncFile(
        path.join(mobileSrc, relPath),
        `${locale}/${theme}/mobile/${logicalName}`,
        `mobile ${locale}/${theme}/${logicalName}`,
        stats
      );
    }
  }
}

console.log(`
────────────────────────────────────────────────────────
  📦  Copied / Updated : ${stats.copied}
  ✅  Already up-to-date: ${stats.upToDate}
  ⚠️   Missing sources  : ${stats.missing}
────────────────────────────────────────────────────────
`);

if (stats.missing > 0) {
  console.warn(
    "⚠️  Missing assets will render as placeholders in the video.\n" +
    "   AI assets go in: mkdocs_src/videoClipPrject/external_src/ai/\n"
  );
}
