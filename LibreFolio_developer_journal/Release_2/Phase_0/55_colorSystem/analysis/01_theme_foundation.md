# 01 — Color foundation: tokens, theme, dark mode

> Snapshot: branch `dev_release2` @ `6d0b1266c` (v1.2), 2026-10-14. Read-only analysis.
> Paths relative to `frontend/`. Counts are grep estimates (see `00_inventory_summary.md` for the scripted, exact-regex numbers).

## TL;DR

- `app.css` defines 16 semantic `--theme-*` variables, but **no component reads them** (0 `var(--theme-*)` in `.svelte`). They are only used *inside* `app.css` by a global "dark remap" layer.
- In practice colors come from ~10.7k raw Tailwind palette classes, ~4.8k `dark:` variants, the `libre-green` brand token (~800 uses), ~1.6k hex literals and ~210 rgb()/hsl() expressions.
- **Cascade trap (verified on compiled CSS):** the dark-mode rules of `app.css` are *unlayered*; Tailwind v4 utilities live in `@layer utilities`. Unlayered rules beat layered ones regardless of specificity, and several also carry `!important`. Result: in dark mode, a large number of explicit `dark:` classes written in components **never render** (see §6.0). The designer must evaluate dark mode **in the browser**, not by reading classes.

---

## 1. Token inventory

### 1a. Tailwind `@theme` tokens (`src/app.css:7-48`)

| Token | Light | Dark | Defined | Uses | Notes |
|---|---|---|---|---|---|
| `--color-libre-green` | `#1a4031` | `#00d681` (`app.css:151`) | `app.css:15` | ~800 | Main brand color. In dark, `.bg-libre-green` and `.text-libre-green` are separately forced to other greens (§6.4). |
| `--color-libre-banner` | `#1a4031` | `#00834f` (`app.css:152`) | `app.css:16` | 0 | Dark override exists, nobody uses it. |
| `--color-libre-beige` | `#f5f4ef` | — (`.bg-libre-beige` forced to `--theme-bg-primary`, `app.css:238`) | `app.css:17` | ~25 | = `surface-100`, manifest `background_color`, splash background. |
| `--color-libre-sage` | `#9caf9c` | — | `app.css:18` | 0 | Only used as `--accent-light` in `static/offline.html`. |
| `--color-libre-dark` | `#111111` | — (`.text-libre-dark` forced to text-primary, `app.css:247`) | `app.css:19` | ~13 | Almost identical to text-primary `#111827`. |
| `--color-primary-50…900` | `#e8f0ed` … `#0a1c14` | — | `app.css:22-31` | 5 (all `bg-primary-600`) | `primary-500` = `#1a4031` = libre-green. 9/10 steps unused. |
| `--color-surface-50…500` | `#fdfcfa` … `#c5c0b0` | — (`.bg-surface-100` override at `app.css:242`) | `app.css:34-39` | 0 | Whole scale unused. |
| `--shadow-card` / `-hover` | rgba .08 / .12 | — | `app.css:42-43` | n/c | Duplicates `--theme-shadow*`. |

### 1b. Semantic theme variables (`:root, html.light` `app.css:125-147`; `html.dark` `app.css:150-175`)

| Token | Light | Dark | `var()` uses outside app.css | Used inside app.css for |
|---|---|---|---|---|
| `--theme-bg-primary` | `#ffffff` | `#0f172a` (slate-900) | 0 | dark body bg, `.bg-libre-beige` |
| `--theme-bg-secondary` | `#f9fafb` (gray-50) | `#1e293b` (slate-800) | 0 | `.bg-gray-50`, `.bg-surface-100`, `option` |
| `--theme-bg-tertiary` | `#f3f4f6` (gray-100) | `#334155` (slate-700) | 0 | `.bg-gray-100` |
| `--theme-bg-card` | `#ffffff` | `#1e293b` | 0 | `.bg-white` (= bg-primary light, = bg-secondary dark) |
| `--theme-bg-hover` | `#f3f4f6` | `#334155` | 0 | = bg-tertiary in both themes |
| `--theme-text-primary` | `#111827` | `#f8fafc` | 0 | body, gray-800/900, inputs |
| `--theme-text-secondary` | `#4b5563` | `#cbd5e1` | 0 | gray-600/700 |
| `--theme-text-tertiary` | `#9ca3af` | `#64748b` | 0 | placeholder only (`app.css:234`) |
| `--theme-text-muted` | `#6b7280` | `#94a3b8` | 0 | gray-400/500 |
| `--theme-border-primary` | `#e5e7eb` | `#334155` | 0 | gray-100/200 borders, `.rounded-xl/.rounded-2xl` |
| `--theme-border-secondary` | `#f3f4f6` | `#1e293b` | 0 | **unused** |
| `--theme-accent` | `#1a4031` | `#22c55e` | 0 | **unused** |
| `--theme-accent-hover` | `#173a2c` | `#16a34a` | 0 | **unused** |
| `--theme-accent-bg` | rgba(26,64,49,.1) | rgba(34,197,94,.15) | 0 | **unused** |
| `--theme-shadow` / `-hover` | .08 / .12 | .3 / .4 | 0 | `.shadow`, `.shadow-sm` |

- The **order of tertiary vs muted flips between themes**: light tertiary `#9ca3af` is lighter than muted `#6b7280`; dark tertiary `#64748b` is dimmer than muted `#94a3b8`.

### 1c. Other custom properties

- `--lf-price-flash-peak/rest` (`app.css:324-349`): emerald-600 / red-500 / gray-700 light; emerald-400 / red-400 / gray-200 dark. One of the few places that uses Tailwind palette vars correctly with a dark override.
- `static/offline.html:12-46` has its own token set (`--bg`, `--text`, `--accent`, `--btn-bg`, `--card-bg`, `--dropdown-*`). Dark bg `#11151c` ≠ app `#0f172a`; dark accent `#4ade80`; dark `--accent-light` `#00ff9a`.

## 2. Brand palette

- **Green `#1a4031`**: libre-green = libre-banner = primary-500 = theme-accent; meta `theme-color` (`src/app.html:11`, `static/offline.html:6`, `static/manifest.json:9`); splash spinner; **~76–112 hardcoded hex copies** in components/charts (most frequent brand hex).
- **Beige `#f5f4ef`**: libre-beige = surface-100 = manifest `background_color` = splash bg = offline `--bg`.
- **Sage `#9caf9c`**: unused in app.
- **Dark `#111111`**: `text-libre-dark` (~13).
- **Dark-mode greens — at least 8 distinct values:**

| Value | Where |
|---|---|
| `#00d681` | `--color-libre-green` dark, `app.css:151` → all opacity/border/ring/outline variants |
| `#00834f` | `--color-libre-banner` dark, `app.css:152` (unused) |
| `#22c55e` / `#16a34a` | `--theme-accent(-hover)` dark (unused) |
| `#39af50` | `.text-libre-green` forced, `app.css:252` |
| `#4ade80` | `focus:ring-libre-green` forced (`app.css:274`), offline accent, ~47 hex hits in components/charts |
| `#166534` | `.bg-libre-green` forced, `app.css:294` |
| `#156534` | meta theme-color dark, `app.html:26`, `themeStore.ts:59` (1-digit typo of `#166534`?) |
| `#86efac` | splash spinner dark (`app.html`) |

## 3. Dark-mode mechanism

- `@custom-variant dark (&:where(.dark, .dark *))` (`src/app.css:4`) → `dark:` follows `html.dark` class.
- Anti-FOUC inline script `src/app.html:16-26`: reads `localStorage['librefolio-theme']` (`'light'|'dark'|''`, empty = auto via `prefers-color-scheme`), sets the class and meta theme-color.
- Store `src/lib/stores/app/themeStore.ts`: key `librefolio-theme` (l.11), `applyTheme()` (l.50-62), `initThemeListener()` follows OS only in auto (l.72-85).
- Toggles: `src/lib/components/ui/ThemeToggle.svelte:15-40` flips light/dark only (saves an explicit choice → stops following OS; registers a duplicate media listener l.28-35). `settings/tabs/PreferencesTab.svelte:335+` offers light/dark/auto and saves server-side.
- `color-scheme: dark` set only in dark (`app.css:174`); no `color-scheme: light`.

## 4. Global hardcoded colors

| file:line | Value | Purpose |
|---|---|---|
| `src/app.css:228` | `#546175` | dark input/select/textarea border (not a token) |
| `src/app.css:252` | `#39af50 !important` | dark `.text-libre-green` |
| `src/app.css:258` | `rgba(30,41,59,.95) !important` | dark `.bg-white/90`, `/95` |
| `src/app.css:274` | `#4ade80` | dark `focus:ring-libre-green` |
| `src/app.css:285,289` | rgba shadows | dark `shadow-lg/xl` |
| `src/app.css:294` | `#166534 !important` | dark `.bg-libre-green` |
| `src/app.css:299` | `#0f172a → #1e293b` gradient | dark `.animated-bg-gradient` (login) |
| `src/app.html:11,26` + style block ~38-95 | `#1a4031`/`#156534`; splash `#f5f4ef`, `#ffffff`, `#1a4031`; dark `#0f172a`, `#86efac` | meta + splash |
| `src/lib/stores/app/themeStore.ts:59` | `#156534` / `#1a4031` | duplicate of app.html |
| `static/manifest.json:9-10` | `#1a4031` / `#f5f4ef` | PWA (no dark) |
| `static/offline.html:12-46` | separate palette | offline page |

No global `::selection`, scrollbar-color or `:focus-visible` color rules.

## 5. Competing consumption patterns

| Approach | Approx. count | Notes |
|---|---|---|
| Raw Tailwind palette classes | ~10.7k | `text-gray-*` ~3.9k, `bg-slate-*` ~1k, `border-gray-*` ~0.8k… |
| `dark:` variants | ~4.8k in ~250/347 `.svelte` | usually gray (light) → slate (dark) |
| Implicit dark remap in `app.css:183-295` | — | repaints gray/white/libre classes with unlayered `!important` rules |
| Brand tokens | libre-* ~800; primary-* 5; surface-* 0 | |
| Hex literals | ~1.6k (166 distinct) | mostly slate/gray copies in `<style>` blocks and chart configs |
| rgb()/rgba()/hsl() | ~210 | |
| `:global(.dark …)` rules in components | 31 files | top: `table/DataTable.svelte` 56, `table/DataTableColumnFilter.svelte` 36, `ui/media/ImageEditModal.svelte` 32, `files/FilePreviewModal.svelte` 24, `ui/media/AssetPickerModal.svelte` 23, `routes/(app)/files/+page.svelte` 21 |
| `var(--theme-*)` in components | **0** | |

Two neutral scales: **gray** is the light basis, **slate** the dark basis — but slate is also used heavily as a light class (`bg-slate-*` ~1k).

## 6. Findings

### 6.0 ⚠️ Dark-mode cascade: written `dark:` classes that never render (coordinator-verified)

Verified on the compiled bundle `frontend/build/_app/immutable/assets/0.*.css`: Tailwind utilities (e.g. `.dark\:text-gray-400`, `.focus\:border-libre-green`) are inside `@layer utilities{…}`; `html.dark input`, `html.dark .rounded-xl`, `html.dark .bg-white`, `html.dark .bg-libre-green` are **unlayered**. Per CSS Cascade 5, unlayered normal declarations beat layered normal declarations, and `!important` beats both. Hence in dark mode:

| app.css rule | Effect | Elements affected (class attribute co-occurrence, `.svelte`) |
|---|---|---|
| `html.dark .text-gray-{400..900} { color: … !important }` (`:198-211`) | every `dark:text-*` on the same element is ignored; actual color = theme var | **~1,541** elements with `text-gray-N` + `dark:text-*` |
| `html.dark .bg-white { … !important }` (`:183`) | `dark:bg-*` ignored → always `#1e293b` | **~223** (e.g. `bg-white … dark:bg-slate-900` renders slate-800) |
| `html.dark .bg-gray-50/100 { … !important }` | `dark:bg-*` ignored | ~72 / ~85 |
| `html.dark .hover\:bg-gray-50/100:hover` | `dark:hover:bg-*` ignored | ~266 |
| `html.dark .rounded-xl, .rounded-2xl { border-color }` (`:262`, unlayered, no `!important`) | **border color depends on corner radius**: any `dark:border-*` on a rounded-xl/2xl element is ignored (e.g. red/amber alert borders become `#334155`) | ~100 |
| `html.dark input, select, textarea { border-color:#546175; color }` (`:226`) | `dark:border-*` **and `focus:border-libre-green`** on inputs are ignored in dark → no visible focus border change | ~52 inputs with `dark:border-*`, ~22 with `focus:border-*` |
| `html.dark .bg-libre-green { #166534 !important }` vs `hover:bg-libre-green/90` → var `#00d681` | resting dark button `#166534`, hover jumps to bright `#00d681` @90% | every primary button with that hover (~65) |

Examples: `routes/(app)/brokers/+page.svelte:382`, `routes/(app)/fx/+page.svelte:1082-1127`, `routes/(app)/assets/+page.svelte:1327`, `settings/SchedulerConfigModal.svelte:198`.

Counts come from a co-occurrence probe on `class="…"` attributes (dynamic `class={…}` and `class:` directives are not counted, so real numbers are higher). Visual confirmation in DevTools is recommended (inspect computed color → rule origin `app.css`).

### 6.1 Semantic layer is dead for components
All 16 `--theme-*` vars: 0 direct uses; 4 unused even in app.css.

### 6.2 Unused tokens
`libre-banner`, `libre-sage`, `surface-*`, 9/10 `primary-*`, `shadow-card*` (duplicates).

### 6.3 Duplicate values
`#1a4031` ×4 tokens; `#f5f4ef` ×2; bg-card = bg-primary (light) = bg-secondary (dark); bg-hover = bg-tertiary; libre-dark ≈ text-primary.

### 6.4 Inconsistent dark brand green
Solid `#166534`, text `#39af50`, all other variants `#00d681`, focus ring `#4ade80` (only without opacity modifier). 8 distinct dark greens overall.

### 6.5 Typo candidate
Meta theme-color dark `#156534` vs CSS `#166534`.

### 6.6 Missing dark versions
`libre-beige` (only `.bg-` covered), `primary-*`, `libre-sage`, manifest; offline dark bg differs.

### 6.7 Non-existent classes (no-op)
- `dark:hover:bg-slate-750` — `transactions/modals/ImportWizardModal.svelte:4657`, `routes/(app)/assets/[id]/+page.svelte:3361` (slate-750 is not in the Tailwind scale; absent from the compiled CSS).
- `hover:bg-libre-green-dark` — `assets/BoundaryDateModal.svelte:234`, `assets/ScheduledInvestmentEditor.svelte:1172` (token not defined; absent from compiled CSS).

### 6.8 Approximate WCAG contrast (AA: 4.5 text, 3.0 large text/UI)

| Pair | Ratio |
|---|---|
| Light text-tertiary `#9ca3af` on `#f9fafb` / white | **2.43 / 2.54** ✗ (`text-gray-400` is the most used text class: ~1.2k) |
| Light text-muted `#6b7280` on white / on `#f3f4f6` | 4.83 / **4.39** (borderline) |
| Light text-secondary on white | 7.56 |
| `#1a4031` on beige / white on `#1a4031` | 10.5 / 11.5 |
| Dark text-tertiary `#64748b` on `#1e293b` / `#0f172a` | **3.07 / 3.75** ✗ (placeholder) |
| Dark text-muted `#94a3b8` on `#1e293b` / `#334155` | 5.71 / **4.04** |
| Dark `#39af50` on `#1e293b` | 5.17 |
| White on dark button `#166534` | 7.13 |
| White on `#00d681` (un-overridden libre-green surfaces, e.g. hover) | **1.92** ✗ |
| Dark input border `#546175` on `#1e293b` | **2.33** ✗ (< 3:1 for UI) |
| Light border `#e5e7eb` on white | 1.24 (decorative) |

### 6.9 Two versions of the "same" color: Tailwind v4 OKLCH vs hand-written sRGB hex (coordinator-verified)

Tailwind is v4.1.18: its default palette is defined in **OKLCH** (compiled CSS: `--color-red-500: oklch(63.7% .237 25.331)`). The hex copies in charts, `<style>` blocks and TS helpers are the **v3 sRGB** values (`#ef4444`). Same lightness and hue, but v4 chroma is ~12–15% higher and most saturated v4 colors fall **outside sRGB** (wide-gamut, P3):

| Tailwind name | v4 class (OKLCH) | in sRGB? | ≈ sRGB clip | v3 hex used in charts/TS | v3 as OKLCH | ΔChroma |
|---|---|---|---|---|---|---:|
| red-500 | `oklch(63.7% .237 25)` | yes (edge) | `#fb2c36` | `#ef4444` | `oklch(63.7% .208 25)` | +0.029 |
| red-600 | `oklch(57.7% .245 27)` | no | `#e7000b` | `#dc2626` | `oklch(57.7% .215 27)` | +0.030 |
| green-600 | `oklch(62.7% .194 149)` | no | `#00a63e` | `#16a34a` | `oklch(62.7% .170 149)` | +0.024 |
| emerald-600 | `oklch(59.6% .145 163)` | no | `#009966` | `#059669` | `oklch(59.6% .127 163)` | +0.018 |
| emerald-400 | `oklch(76.5% .177 163)` | no | `#00d492` | `#34d399` | `oklch(77.3% .153 163)` | +0.024 |
| amber-500 | `oklch(76.9% .188 70)` | no | `#fe9a00` | `#f59e0b` | `oklch(76.9% .165 70)` | +0.023 |
| blue-500 | `oklch(62.3% .214 260)` | no | `#2b7fff` | `#3b82f6` | `oklch(62.3% .188 260)` | +0.026 |
| slate-800 | `oklch(27.9% .041 260)` | yes | `#1d293d` | `#1e293b` | `oklch(27.9% .037 260)` | +0.004 |

Consequences:
- UI text/badges (classes) and charts (hex) do **not** match even when they "use the same color" (e.g. `text-red-500` vs chart `#ef4444`).
- On wide-gamut displays (recent Macs) class colors render more saturated than on sRGB displays; the gallery PNGs (headless Chromium, sRGB) show the clipped version — the live app can look more vivid than the screenshots.
- `app.css` dark overrides are hex (sRGB), so in dark mode the same element mixes sRGB surfaces with OKLCH accents.
- Token decision needed: color space of the future tokens (sRGB hex everywhere, or OKLCH everywhere incl. charts — ECharts accepts any CSS color string, but helpers like `hexToRgba` and `+ '88'` alpha concatenation only accept `#rrggbb`).

## 7. Open questions for the designer

1. Single source of truth: `--theme-*` semantic vars or Tailwind `@theme` tokens? Expose semantic utilities (`bg-surface`, `text-muted`…)?
2. Gray or slate as the neutral scale, same family in light and dark?
3. One dark brand green (8 today) for solid/text/focus/opacity variants?
4. Keep/remove `libre-sage`, `libre-banner`, `surface-*`, `primary-*`?
5. Beige as light app background, or white/gray-50?
6. Semantic status colors (success, warning, error, info, gain, loss): emerald or green for positive?
7. Merge/clarify text-tertiary vs muted (order flips; tertiary fails AA in both themes).
8. Should offline page, splash and manifest share app tokens incl. dark?
9. Contrast target: AA for body text, 3:1 for input borders?
10. Keep the global `!important` dark remap as safety net, or move to explicit tokens (it currently silently overrides thousands of `dark:` classes — §6.0)?
