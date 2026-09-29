---
title: "Flag Emoji Broken on Windows (Segoe UI Emoji)"
category: problem
status: resolved
date: 2026 (Phase 5)
updated: 2026-09-29
tags: [frontend, emoji, windows, fonts, css, unicode-range, i18n]
related_features: [F-008]
---

# Problem: Flag Emoji Not Rendering on Windows

## Symptom
Country/language flag emoji (🇮🇹, 🇫🇷, 🇪🇸, 🇬🇧, 🇪🇺) displayed as blank boxes or letter pairs ("EU") on Windows.
Linux and macOS showed them correctly.

## Root Cause
Windows' default emoji font (Segoe UI Emoji) **does not support regional indicator flag emoji sequences**. A flag
is a pair of regional indicator symbols (U+1F1E6–1F1FF); when no font in the stack draws the pair as a flag, the
system falls back to Segoe UI Emoji, which prints the two letters.

## Solution (since 2026-09-29 — Release 2, K step 12b)
**One global face that only ever draws flags.**

- `frontend/static/lf-flags.css` declares `@font-face 'LF Flags'` with `unicode-range: U+1F1E6-1F1FF` and the
  sources `local('Apple Color Emoji')`, `local('AppleColorEmoji')`, `local('Noto Color Emoji')`,
  `local('NotoColorEmoji')`, then `url('/fonts/noto-color-emoji/noto-color-emoji.0.woff2')`. It is linked by
  `src/app.html` and by `static/offline.html` (the PWA offline page does not load `app.css`). It lives in
  `static/` because `static/fonts/` is the gitignored download cache.
- `'LF Flags'` **leads every font stack**: `html`, Tailwind 4 `@theme --font-sans` and `--font-mono` in `app.css`,
  and every stack of `offline.html`. Because of its unicode-range it draws only regional indicators: digits, `#`,
  `*`, ZWJ/VS16 and every other emoji keep the fonts after it (Inter, the monospace font, the system's emoji).
- Apple devices draw their own flags through `local()`; every other device downloads the Noto flags subset
  (~700 KB) — and only when a flag is actually on the page.
- `.emoji-flag` is now `'LF Flags', Inter, system-ui, sans-serif`. It is only needed where an element brings its
  own stack (a monospace cell): the global stacks cover everything else. The old per-container rule missed places
  — the dashboard currencies printed "EU" on Windows.
- `scripts/update_js_cache.py` caches **only** the flags subset of Noto (`keep_unicode_ranges:
  ['U+1f1e6-1f1ff']`), always as file 0 whatever position Google serves it in, deletes the stale subsets, and
  treats a changed kept-ranges fingerprint as "not up to date". The full Noto stylesheet is no longer linked.

## Why the previous rule changed
- "Apply `.emoji-flag` only to flag containers, not globally" was about the **weight** of the whole Google Fonts
  CSS. With a unicode-range face only the flags subset can load, and only where a flag is displayed.
- The old `.emoji-flag` stack put emoji families **before** the text font. Apple Color Emoji (and Noto's subset 2)
  draw digits, `#` and `*` — measured with CDP: inside `.emoji-flag` the digits came from Apple Color Emoji.
- `9ab32912c` (2026-05-27) put Apple first for iOS; a later local rule in `TransactionsTable.svelte` put Noto first
  again (downloading Noto on Apple devices too). Removed.

## Prevention
- **Never name an emoji family in a font stack.** The only place those names appear is the `local()` list of
  `lf-flags.css`. Gate: `frontend/src/flagFont.gate.test.ts` (also checks that cache file 0 is the flags range).
- A component with its own `font-family` that can show a flag: start the stack with `'LF Flags'`, or wrap the
  flag in `.emoji-flag`.
- **Known limit:** ECharts bypasses the global stacks — its canvas draws with its own `fontFamily` (default
  `sans-serif`), and its HTML tooltips carry an inline `font: … sans-serif`. Flags there (signal legends, the
  geography map, allocation history) are not covered yet (backlog, chart owners); a tooltip flag wrapped in
  `.emoji-flag` is.
- **Verifying without Windows:** `frontend/e2e/fx/fx-flag-font.spec.ts` reads the font that actually draws each
  node through CDP `CSS.getPlatformFontsForNode`; a probe face whose `local()` source cannot resolve exercises the
  Noto (Windows) path on any OS. Real-device checks (iPhone, Mac, Windows) remain manual.

## History
Phase 5 loaded `Noto Color Emoji` from Google Fonts and applied it through `.emoji-flag` to flag containers only,
with Noto first; `9ab32912c` reordered it Apple-first for iOS. Both are superseded by the solution above.

## Source
`LibreFolio_developer_journal/knowledge_base/05_project_conventions.md` — "Emoji Bandiera (Windows Fix)" section;
`LibreFolio_developer_journal/Release_2/Phase_0/25_taxonomySelect/plan-phase00TaxonomySelectStep12ReviewFollowups.prompt.md`.

## Source files

| Role | Path |
|------|------|
| Flag face (`'LF Flags'`) | `frontend/static/lf-flags.css` |
| Global stacks and `.emoji-flag` | `frontend/src/app.css` |
| App shell (links `lf-flags.css`) | `frontend/src/app.html` |
| PWA offline page | `frontend/static/offline.html` |
| Noto cache (flags subset only) | `scripts/update_js_cache.py` |
| Static gate | `frontend/src/flagFont.gate.test.ts` |
| CDP end-to-end check | `frontend/e2e/fx/fx-flag-font.spec.ts` |
| Language selector (flag emoji) | `frontend/src/lib/components/layout/LanguageSelector.svelte` |
