#!/usr/bin/env node
/**
 * sync-assets.ts — v3 (Manifest-driven)
 * ──────────────────────────────────────────────────────────────────────────────
 * Syncs gallery screenshots using the galleryManifest.ts definition.
 */

import fs from "node:fs";
import path from "node:path";
const VIDEO_PROMO = process.cwd();
const MKDOCS_SRC  = path.resolve(VIDEO_PROMO, "../..");
const GALLERY     = path.resolve(MKDOCS_SRC, "docs/gallery");
const STATIC      = path.resolve(MKDOCS_SRC, "docs/static");
const AI_DIR      = path.resolve(VIDEO_PROMO, "public/ai");
const ASSETS_OUT  = path.resolve(VIDEO_PROMO, "public/assets");

// Hardcode manifest temporarily since TS execution in node without a loader can be tricky
// We will sync exactly what's needed for the 7 scenes.
const promoGallery = {
  dashboard: ["main.png", "allocation-charts.png"],
  transactions: ["list.png", "form-modal.png", "picker-modal.png"],
  brokers: ["list.png"],
  assets: ["list.png", "detail-chart.png", "detail-signals.png", "detail-measures.png", "detail-classification.png", "detail-editor.png"],
  fx: ["list.png", "detail-chart.png", "detail-signals.png", "detail-measures.png"],
  settings: ["scheduler-config.png", "scheduler-log.png"],
  files: ["preview-modal.png"],
};

const promoGalleryMobile = {
  dashboard: ["main.png"],
  assets: ["list.png", "detail-chart.png"],
};

const LOCALES = ["en", "it", "es", "fr"] as const;
const THEMES  = ["dark", "light"] as const;

const SHARED_ASSETS = [
  { src: path.join(STATIC, "logo.png"),    dest: "shared/logo.png",    desc: "LibreFolio logo" },
  { src: path.join(STATIC, "favicon.png"), dest: "shared/favicon.png", desc: "Favicon" },
];

const AI_ASSETS = [
  "chaos_bg_v2.png",
  "data_stream_bg.png",
  "import_pipeline_bg.png",
  "device_sync_bg.png",
  "open_network_bg.png",
  "cta_particles_bg.png",
  "audio_track_main_54s_fade.mp3",
  "sfx_transition_whoosh_cut_a.mp3",
  "sfx_logo_sting_cut_a.mp3",
];

function getMtime(p: string): number {
  try { return fs.statSync(p).mtimeMs; }
  catch { return -1; }
}

function ensureDir(dir: string): void {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

interface SyncStats { copied: number; upToDate: number; missing: number; ignored: number; }
const stats: SyncStats = { copied: 0, upToDate: 0, missing: 0, ignored: 0 };

function syncFile(src: string, destRel: string, desc: string): void {
  const dest = path.join(ASSETS_OUT, destRel);
  const srcMtime = getMtime(src);

  if (srcMtime === -1) {
    console.warn(`  ⚠️  MISSING   ${destRel}  (${desc})`);
    stats.missing++;
    return;
  }

  const destMtime = getMtime(dest);
  if (destMtime >= srcMtime) {
    stats.upToDate++;
    return;
  }

  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
  console.log(`  📦  ${destMtime === -1 ? "COPIED  " : "UPDATED "}  ${destRel}`);
  stats.copied++;
}

console.log("🔄  sync-assets v3 — Manifest-driven\n");

// 1. Shared
console.log("── Shared assets ─────────────────────────");
for (const { src, dest, desc } of SHARED_ASSETS) {
  syncFile(src, dest, desc);
}

// 2. AI Assets
console.log("\n── AI-generated assets (public/ai/) ────────");
for (const name of AI_ASSETS) {
  if (getMtime(path.join(AI_DIR, name)) === -1) {
    console.warn(`  ⚠️  MISSING   ai/${name}`);
    stats.missing++;
  } else {
    stats.upToDate++;
  }
}

// 3. Gallery Desktop
for (const locale of LOCALES) {
  console.log(`\n── Gallery ${locale.toUpperCase()} ────────────────────────────`);
  for (const theme of THEMES) {
    // Desktop
    for (const [category, files] of Object.entries(promoGallery)) {
      for (const file of files) {
        const relPath = `${category}/${file}`;
        syncFile(
          path.join(GALLERY, "desktop", locale, theme, relPath),
          `${locale}/${theme}/desktop/${relPath}`,
          `desktop ${locale}/${theme}/${relPath}`
        );
      }
    }
    // Mobile
    for (const [category, files] of Object.entries(promoGalleryMobile)) {
      for (const file of files) {
        const relPath = `${category}/${file}`;
        syncFile(
          path.join(GALLERY, "mobile", locale, theme, relPath),
          `${locale}/${theme}/mobile/${relPath}`,
          `mobile ${locale}/${theme}/${relPath}`
        );
      }
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
