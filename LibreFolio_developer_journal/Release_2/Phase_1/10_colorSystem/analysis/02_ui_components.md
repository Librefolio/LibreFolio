# 02 — UI components & pages: color patterns

> Snapshot: `dev_release2` @ `6d0b1266c` (v1.2), 2026-10-14. Read-only. Paths relative to `frontend/src/`.
> Method: grep counts (tests excluded); individual components were not all opened, so "likely" items are inferences. Exact regex counts per class are in `00_inventory_summary.md` (CSVs: regenerate with `scripts/visual_review/color_inventory.py`).
> ⚠️ Dark-mode values written as `dark:` classes may not render: see report 01 §6.0 (global `app.css` overrides win the cascade).

Totals: ~4.8k `dark:` prefixes; **0** `var(--theme-*)` in markup.

## 1. Tailwind color families by purpose

| Purpose | Families in use | Main shades | Problem |
|---|---|---|---|
| Neutral, light | **gray** (dominant) | text-gray-400 ~1.16k, -500 ~830, -700 ~410, -600 ~360; border-gray-200 ~370, -100 ~185; bg-gray-50/100 ~265 each | — |
| Neutral, dark | **slate** (main) + gray | bg-slate-700 ~475, -800 ~255, -600 ~125, -900 ~65; border-slate-600 ~275, -700 ~240; also border-gray-700 ~88, bg-gray-700 ~42, bg-gray-800 ~27 | gray and slate mixed for dark surfaces; non-existent `slate-750` (2×) |
| Primary / brand | `libre-green` (bg ~364, text ~192, border ~88, ring ~80, outline ~27) | `/90` hover ~59, `/10` ~49, `/20` ~21, `/5` ~8 | competing focus color `focus-visible:outline-green-400` (9) vs `outline-libre-green` (22) |
| Success / positive | green **and** emerald | text-green-400 65 / -600 32; text-emerald-400 59 / -600 46; bg-emerald-900 37; + lime (3), teal (~10) | two families for one meaning |
| Danger | red (+ rose ~15) | text-red-400 101, -500 86, -600 69; bg-red-50 55, bg-red-900 53 | three competing text shades |
| Warning | amber (+ yellow ~25, orange ~45) | text-amber-400 98, bg-amber-900 91, bg-amber-50 65 | three families |
| Info | blue (+ sky ~70, indigo ~40, cyan ~6) | bg-blue-900 41, bg-blue-100 25 | blue vs sky |
| Categories / tags | violet, purple, pink, indigo, teal | low counts | badge-type palettes (see report 03) |

## 2. Opacity modifiers
`/30` 169, `/20` 104, `/50` 98, `/40` 96, `/70` 71, `/60` 52, `/10` 31, `/80` 30, `/90` 10, plus `/95`, `/15`, `/25` → **12 different steps**, mostly dark tints like `dark:bg-red-900/30`.
Backdrops alone: `bg-black/5` 1, `/10` 2, `/30` 2, `/40` 2, `/45` 5, `/50` 5 → six values.

## 3. Patterns: de-facto standard vs outliers

| Pattern | Most common variant | Outliers |
|---|---|---|
| Primary button | `bg-libre-green hover:bg-libre-green/90` (~59) | `hover:bg-libre-green-dark` (2, **undefined token → no hover**); in dark, resting `#166534` vs hover `#00d681`@90 (report 01 §6.0) |
| Soft/ghost, selected item | `bg-libre-green/10` (~49) | `/20` (27), `/5` (8) |
| Card / panel | `bg-white dark:bg-slate-800` (~122) | `dark:bg-slate-700` (75), `dark:bg-slate-700/50` (5), `dark:bg-slate-900` (2), `dark:bg-gray-800/700` (2+2) — **but in dark every `bg-white` renders `#1e293b` regardless** (app.css `!important`) |
| Row / menu hover | light `hover:bg-gray-50` (152) vs `hover:bg-gray-100` (137); dark `dark:hover:bg-slate-700` (216) | `hover:bg-gray-200` 40, dark `hover:bg-slate-600` 86, `hover:bg-gray-700` 13, `hover:bg-slate-700/50` 8 |
| Focus | `focus:outline-none` + `focus:ring-libre-green` (37) or `focus:border-libre-green` (31) | ring opacities /50 16, /40 4, /30 4; `focus-visible:outline-libre-green` 22 vs `outline-green-400` 9. In dark, `focus:border-*` on inputs is overridden by `html.dark input` |
| Placeholder | `placeholder-gray-500` (11) | `placeholder-gray-400` (8) |
| Error alert | `bg-red-50 border-red-200` / `dark:bg-red-900/… dark:border-red-800` | `bg-red-950` (17), `border-red-900` (15), rose variants |
| Warning alert | `bg-amber-50 border-amber-200` / `dark:bg-amber-900/… border-amber-800` | `bg-amber-950` (21), `border-amber-900` (14), yellow/orange variants |
| Dividers | `divide-gray-100` 6 | `divide-gray-700` 4, `divide-slate-700` 3, `divide-gray-200` 1 |

Not inventoried one by one: sidebar, tabs, tooltips, skeletons, onboarding highlight (suggested follow-up, see 00 §6).

## 4. Hardcoded hex / rgb — a parallel CSS color system

Matching lines per file (mostly `<style>` blocks with `:global(.dark)` overrides):

| File | Lines |
|---|---|
| `lib/components/table/DataTable.svelte` | 143 |
| `lib/components/table/DataTableColumnFilter.svelte` | 126 |
| `lib/components/ui/media/ImageEditModal.svelte` | 106 |
| `lib/components/files/FilePreviewModal.svelte` | 81 |
| `lib/components/ui/media/AssetPickerModal.svelte` | 72 |
| `routes/(app)/files/+page.svelte` | 68 |
| `lib/components/ui/media/FileUploader.svelte` | 59 |
| `lib/components/ui/media/FileEditModal.svelte` | 57 |
| `lib/components/transactions/modals/ImportBrokerMismatchModal.svelte` | 56 |
| `lib/components/files/FileGrid.svelte` | 52 |
| `lib/components/table/DataTablePagination.svelte` | 50 |
| `lib/components/ui/modals/ConfirmModal.svelte` | 44 |
| `lib/components/brokers/BrokerImportFilesModal.svelte` | 26 |
| `lib/components/table/DataTableToolbar.svelte` | 22 |
| `lib/components/ui/ContextMenu.svelte` | 17 |
| `lib/components/ui/media/ImageCropper.svelte` | 18 |
| `lib/components/ui/display/CompactCashCell.svelte` | 13 |

→ Tables, file/media modals and `ConfirmModal` use their own CSS color system instead of Tailwind classes (likely the most visible source of "different-looking" surfaces).

Inline `style=`:
- White logo tile `style="background:#fff"` in both themes: `auth/LoginCard.svelte:44`, `auth/RegisterCard.svelte:152`, `auth/ForgotPasswordCard.svelte:16`, `auth/DonationPopupModal.svelte:53`, `settings/tabs/AboutTab.svelte:258`.
- `ui/media/AssetPickerModal.svelte:265` `color:#dc2626` (no dark).
- `ui/select/FxProviderSelect.svelte:466` `#fbbf24` in an HTML tooltip string.
- `brokers/lots/LotComparisonChart.svelte:855` tooltip `#4ade80/#16a34a/#f87171/#dc2626`.

## 5. Light-only candidates (verified: 0 `dark:`, 0 `:global(.dark)`)

- `lib/components/layout/Sidebar.svelte`
- `lib/components/ui/feedback/ToastContainer.svelte` (has a `<style>` block, no dark rule)
- `lib/components/ui/input/PasswordStrength.svelte`
- `lib/components/layout/ConnectionSecurityIndicator.svelte`
- `routes/(app)/settings/+page.svelte`

They may still look acceptable in dark thanks to the global `app.css` remap of gray/white classes — or may be intentionally fixed (e.g. Sidebar on brand green). Visual check required. Full scripted list: `00_inventory_summary.md` → "Light-only candidates".

## 6. Hotspots (most color expressions per file)

Top by Tailwind palette classes: `transactions/modals/ImportWizardModal.svelte` (527), `routes/(app)/assets/[id]/+page.svelte` (273), `brokers/lots/LotCustodyModal.svelte` (212), `brokers/BrokerSharingPanel.svelte` (200), `transactions/modals/TransactionFormModal.svelte` (197), `routes/(app)/assets/+page.svelte` (191), `transactions/import/FixFlaggedStep.svelte` (188), `transactions/modals/TransactionBulkModal.svelte` (180), `assets/AssetModal.svelte` (179), `risk/RiskAnalysisPanel.svelte` (169). `settings/tabs/AboutTab.svelte` has 147 palette classes but only 4 `dark:` (relies on the global remap). Full table: inventory.

## 7. Open questions for the designer

1. Dark neutrals: slate only (drop gray-700/800 and `slate-750`)? One ladder for page / card / raised / hover?
2. Card surface: slate-800 or slate-700?
3. Success: green or emerald, and distinct from brand `libre-green`?
4. One shade each for danger text; warning amber only; info blue or sky?
5. One focus treatment (ring vs border vs outline, single opacity)?
6. One backdrop value; a reduced opacity scale (e.g. 10/20/50)?
7. Move `<style>`-block colors in `DataTable*`, media/file modals, `ConfirmModal` to tokens?
8. White logo tile on auth pages in dark mode: intentional?
