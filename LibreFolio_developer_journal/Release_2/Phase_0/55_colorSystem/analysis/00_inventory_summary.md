# Frontend color inventory — quantitative snapshot

Source: `frontend/src` (generated API files excluded). Files scanned: 1047. Test files excluded from the stats below (kept in CSVs with `is_test`).

## Totals (production code)

- Tailwind palette + white/black/transparent color classes: **10682** (with `dark:`: 4801)
- Custom-token Tailwind classes (libre-*/theme-*/primary/accent): **795**
- Arbitrary-value color classes (`bg-[#...]`, `text-[var(--...)]`): **12**
- Hex literals: **1610** (166 distinct)
- rgb()/rgba()/hsl()/oklch()/color-mix(): **211** (162 distinct)
- `var(--…)` usages: **84** across 40 distinct properties
- CSS custom property definitions: **86**

## Tailwind color families (prod)

| Family | Uses | Top shades |
|---|---:|---|
| gray | 5462 | 400×1183, 500×848, 200×753, 100×669, 700×542, 300×489, 600×403, 50×268, 900×175 |
| slate | 1788 | 700×747, 600×416, 800×265, 900×85, 500×84, 400×53, 100×44, 200×38, 300×30 |
| amber | 831 | 900×123, 400×115, 200×89, 500×88, 600×87, 800×71, 50×66, 700×65, 100×57 |
| red | 684 | 400×135, 500×113, 600×81, 900×70, 50×55, 200×54, 700×53, 300×41, 800×40 |
| white | 645 |  |
| emerald | 334 | 400×75, 600×52, 900×42, 300×32, 700×27, 100×24, 500×21, 50×20, 200×18 |
| blue | 266 | 900×43, 400×32, 500×30, 700×30, 300×27, 100×25, 600×22, 50×19, 200×19 |
| green | 220 | 400×91, 600×35, 500×24, 900×15, 700×14, 300×10, 100×9, 800×9, 50×8 |
| sky | 98 | 900×16, 200×15, 800×12, 700×10, 100×9, 50×8, 400×8, 300×7, 600×5 |
| violet | 70 | 900×12, 400×11, 100×9, 600×9, 700×7, 300×7, 50×5, 200×3, 500×3 |
| indigo | 49 | 900×13, 100×8, 400×7, 700×5, 50×4, 200×3, 600×3, 800×2, 500×2 |
| orange | 49 | 900×10, 100×7, 700×6, 400×5, 200×5, 500×4, 600×4, 300×4, 800×3 |
| purple | 36 | 400×7, 600×7, 700×6, 300×5, 900×4, 500×3, 100×3, 50×1 |
| transparent | 28 |  |
| yellow | 27 | 900×5, 500×4, 600×3, 400×3, 100×3, 700×3, 300×2, 800×2, 50×1 |
| black | 24 |  |
| pink | 22 | 900×4, 200×3, 800×3, 300×3, 50×2, 600×2, 100×2, 700×2, 400×1 |
| rose | 17 | 200×4, 900×3, 50×2, 950×2, 500×2, 700×1, 800×1, 300×1, 400×1 |
| teal | 15 | 400×4, 100×3, 900×3, 700×3, 500×2 |
| current | 8 |  |
| cyan | 5 | 600×1, 100×1, 900×1, 700×1, 400×1 |
| lime | 4 | 500×2, 200×1, 600×1 |

## Prefix × family (prod, top 70)

| Prefix | Family | Uses |
|---|---|---:|
| text | gray | 3886 |
| bg | slate | 988 |
| border | gray | 794 |
| bg | gray | 744 |
| border | slate | 567 |
| text | amber | 421 |
| bg | white | 397 |
| text | red | 365 |
| bg | amber | 279 |
| text | white | 229 |
| text | slate | 218 |
| bg | red | 203 |
| text | emerald | 181 |
| text | green | 135 |
| text | blue | 126 |
| border | amber | 121 |
| bg | emerald | 110 |
| border | red | 107 |
| bg | blue | 100 |
| bg | green | 63 |
| bg | sky | 40 |
| text | sky | 38 |
| border | emerald | 35 |
| border | blue | 32 |
| text | violet | 30 |
| bg | violet | 28 |
| bg | indigo | 28 |
| bg | orange | 22 |
| text | purple | 22 |
| text | indigo | 21 |
| text | orange | 21 |
| bg | transparent | 20 |
| border | sky | 20 |
| placeholder | gray | 19 |
| bg | black | 18 |
| border | white | 18 |
| bg | yellow | 13 |
| bg | purple | 12 |
| divide | gray | 11 |
| text | yellow | 11 |
| border | green | 10 |
| bg | pink | 10 |
| outline | green | 10 |
| border | transparent | 8 |
| border | violet | 8 |
| ring | blue | 8 |
| ring | emerald | 8 |
| bg | teal | 8 |
| text | teal | 7 |
| border | current | 7 |
| border | black | 6 |
| border | rose | 6 |
| bg | rose | 6 |
| ring | amber | 6 |
| ring | orange | 6 |
| ring | red | 5 |
| text | rose | 5 |
| ring | slate | 4 |
| ring-offset | slate | 4 |
| border | pink | 4 |
| ring | pink | 4 |
| text | pink | 4 |
| ring | violet | 4 |
| divide | slate | 3 |
| text | cyan | 3 |
| fill | amber | 3 |
| outline | red | 3 |
| text | lime | 2 |
| border | purple | 2 |
| ring | yellow | 2 |

## Variants on color classes (prod)

`dark`×4801, `hover`×1158, `class`×35, `focus-visible`×19, `disabled`×12, `focus`×12, `even`×2, `odd`×2, `placeholder`×2

## Opacity modifiers (prod)

`/30`×184, `/20`×118, `/50`×108, `/40`×100, `/70`×82, `/60`×55, `/10`×52, `/80`×45, `/90`×21, `/5`×7, `/45`×5, `/15`×4, `/95`×3, `/25`×1

## Most frequent exact color classes (prod, top 100)

| Class | Uses |
|---|---:|
| `dark:text-gray-400` | 642 |
| `text-gray-500` | 629 |
| `text-gray-400` | 515 |
| `text-gray-700` | 376 |
| `border-gray-200` | 352 |
| `bg-white` | 318 |
| `dark:text-gray-300` | 298 |
| `text-gray-600` | 284 |
| `dark:border-slate-600` | 268 |
| `dark:text-gray-200` | 263 |
| `dark:border-slate-700` | 234 |
| `dark:hover:bg-slate-700` | 216 |
| `dark:text-gray-100` | 209 |
| `dark:bg-slate-700` | 206 |
| `dark:bg-slate-800` | 205 |
| `dark:text-gray-500` | 202 |
| `text-white` | 200 |
| `border-gray-100` | 186 |
| `hover:bg-gray-50` | 154 |
| `text-gray-900` | 151 |
| `hover:bg-gray-100` | 137 |
| `bg-gray-100` | 128 |
| `bg-gray-50` | 105 |
| `text-gray-800` | 99 |
| `dark:text-amber-400` | 94 |
| `dark:text-red-400` | 92 |
| `border-gray-300` | 92 |
| `dark:hover:bg-slate-600` | 87 |
| `dark:border-gray-700` | 86 |
| `text-red-500` | 75 |
| `text-amber-600` | 69 |
| `dark:text-green-400` | 64 |
| `text-red-600` | 62 |
| `text-amber-500` | 57 |
| `dark:text-emerald-400` | 56 |
| `bg-amber-50` | 55 |
| `hover:text-gray-600` | 54 |
| `text-emerald-600` | 46 |
| `text-amber-700` | 45 |
| `text-slate-500` | 44 |
| `border-amber-200` | 43 |
| `dark:hover:text-gray-300` | 43 |
| `dark:text-slate-400` | 43 |
| `text-red-700` | 42 |
| `bg-gray-200` | 42 |
| `bg-red-50` | 41 |
| `bg-amber-100` | 40 |
| `hover:bg-gray-200` | 40 |
| `text-amber-800` | 38 |
| `dark:bg-slate-600` | 37 |
| `dark:text-amber-300` | 35 |
| `dark:hover:text-gray-200` | 35 |
| `border-red-200` | 34 |
| `dark:text-amber-200` | 33 |
| `text-green-600` | 32 |
| `dark:text-red-300` | 31 |
| `dark:bg-amber-900/20` | 31 |
| `dark:border-gray-600` | 31 |
| `hover:text-gray-700` | 30 |
| `dark:bg-slate-900` | 29 |
| `dark:bg-amber-900/30` | 28 |
| `dark:bg-gray-700` | 28 |
| `dark:text-slate-100` | 27 |
| `text-slate-700` | 24 |
| `dark:text-emerald-300` | 24 |
| `dark:bg-gray-800` | 24 |
| `dark:bg-red-900/20` | 23 |
| `dark:bg-slate-700/50` | 23 |
| `bg-emerald-100` | 22 |
| `dark:border-red-800` | 21 |
| `dark:text-blue-300` | 21 |
| `bg-blue-100` | 21 |
| `text-blue-700` | 21 |
| `dark:border-amber-800` | 20 |
| `dark:text-gray-600` | 20 |
| `bg-slate-50` | 20 |
| `text-emerald-700` | 20 |
| `dark:text-blue-400` | 20 |
| `bg-gray-300` | 19 |
| `dark:bg-slate-900/70` | 19 |
| `text-gray-300` | 18 |
| `dark:text-slate-200` | 18 |
| `dark:bg-emerald-900/30` | 18 |
| `dark:bg-blue-900/30` | 18 |
| `bg-transparent` | 18 |
| `text-amber-900` | 18 |
| `bg-blue-50` | 17 |
| `dark:text-red-200` | 17 |
| `dark:bg-amber-950/30` | 15 |
| `dark:text-slate-300` | 15 |
| `text-blue-500` | 15 |
| `text-blue-600` | 14 |
| `dark:hover:bg-gray-700` | 14 |
| `bg-red-100` | 14 |
| `text-slate-900` | 14 |
| `text-red-800` | 14 |
| `dark:text-white` | 14 |
| `bg-amber-500` | 13 |
| `border-blue-200` | 13 |
| `bg-emerald-50` | 13 |

## Custom-token classes (prod)

| Class | Uses |
|---|---:|
| `bg-libre-green` | 175 |
| `text-libre-green` | 146 |
| `hover:bg-libre-green/90` | 65 |
| `bg-libre-green/10` | 46 |
| `hover:text-libre-green` | 39 |
| `focus:ring-libre-green` | 36 |
| `border-libre-green` | 32 |
| `focus:border-libre-green` | 30 |
| `focus-visible:outline-libre-green` | 27 |
| `bg-libre-beige` | 24 |
| `dark:bg-libre-green/20` | 24 |
| `focus:ring-libre-green/50` | 16 |
| `text-libre-dark` | 13 |
| `ring-libre-green` | 10 |
| `hover:bg-libre-green/10` | 10 |
| `hover:border-libre-green` | 10 |
| `bg-libre-green/5` | 8 |
| `hover:bg-libre-green/5` | 4 |
| `hover:text-libre-green/80` | 4 |
| `hover:bg-libre-green/20` | 4 |
| `focus:ring-libre-green/40` | 4 |
| `focus:ring-libre-green/30` | 4 |
| `hover:border-libre-green/30` | 3 |
| `dark:bg-libre-green/25` | 3 |
| `border-libre-green/40` | 3 |
| `focus-visible:ring-libre-green/70` | 3 |
| `dark:bg-libre-green/10` | 3 |
| `class:focus:border-libre-green` | 3 |
| `class:focus:ring-libre-green` | 3 |
| `dark:hover:bg-libre-green/20` | 3 |
| `dark:hover:text-libre-green` | 3 |
| `ring-libre-green/30` | 3 |
| `bg-libre-green/20` | 3 |
| `hover:border-libre-green/50` | 3 |
| `bg-libre-green/15` | 2 |
| `hover:bg-libre-green-dark` | 2 |
| `class:bg-libre-green` | 2 |
| `bg-libre-green/70` | 2 |
| `hover:bg-libre-green` | 2 |
| `dark:hover:bg-libre-green/30` | 2 |
| `bg-libre-green/30` | 2 |
| `dark:bg-libre-green` | 2 |
| `ring-libre-beige` | 1 |
| `focus:ring-libre-green/20` | 1 |
| `focus-visible:ring-libre-green/20` | 1 |
| `hover:bg-libre-green/15` | 1 |
| `hover:border-libre-green/20` | 1 |
| `dark:border-libre-green/30` | 1 |
| `bg-libre-green/50` | 1 |
| `dark:border-libre-green` | 1 |
| `text-libre-green/80` | 1 |
| `bg-libre-beige/95` | 1 |
| `border-libre-green/60` | 1 |
| `dark:hover:bg-libre-green/10` | 1 |

## Arbitrary-value color classes (prod)

| Class | Uses |
|---|---:|
| `bg-[#ff4500]` | 1 |
| `hover:bg-[#e03d00]` | 1 |
| `focus-visible:ring-[#ff4500]` | 1 |
| `bg-[#0866ff]` | 1 |
| `hover:bg-[#0758db]` | 1 |
| `focus-visible:ring-[#0866ff]` | 1 |
| `from-[#c13584]` | 1 |
| `via-[#833ab4]` | 1 |
| `to-[#405de6]` | 1 |
| `focus-visible:ring-[#c13584]` | 1 |
| `focus-visible:ring-[#25f4ee]` | 1 |
| `shadow-[0_0_0_5px_rgba(52,211,153,0.4),0_0_28px_rgba(52,211,153,0.95)]` | 1 |

## Hex literals (prod) — distinct values by frequency

| Hex | Uses | Files | Example files |
|---|---:|---:|---|
| `#e2e8f0` | 111 | 28 | lib/components/auth/UpdateAvailableModal.svelte<br>lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/charts/AllocationPieChart.svelte … |
| `#334155` | 88 | 26 | app.css<br>lib/components/auth/UpdateAvailableModal.svelte<br>lib/components/charts/AllocationPieChart.svelte<br>lib/components/charts/CandlestickChart.svelte … |
| `#94a3b8` | 79 | 25 | app.css<br>lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/brokers/lots/lotStateVisual.ts … |
| `#1a4031` | 76 | 28 | app.css<br>lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/charts/AllocationPieChart.svelte<br>lib/components/charts/PriceChartCompact.svelte … |
| `#0f172a` | 72 | 14 | app.css<br>lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/LotWacPriceChart.svelte … |
| `#374151` | 68 | 9 | lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/charts/AllocationPieChart.svelte<br>lib/components/files/FileGrid.svelte<br>lib/components/ui/feedback/LoadingSpinner.svelte … |
| `#64748b` | 60 | 24 | app.css<br>lib/charts/signals/signalVisualStyle.ts<br>lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/lotStateVisual.ts … |
| `#1e293b` | 57 | 22 | app.css<br>lib/components/charts/AllocationPieChart.svelte<br>lib/components/charts/CandlestickChart.svelte<br>lib/components/charts/GeographyMap.svelte … |
| `#475569` | 54 | 20 | lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/charts/CandlestickChart.svelte<br>lib/components/charts/LineChart.svelte … |
| `#9ca3af` | 50 | 14 | app.css<br>lib/components/charts/CandlestickChart.svelte<br>lib/components/charts/LineChart.svelte<br>lib/components/charts/PriceChartFull.svelte … |
| `#4ade80` | 47 | 22 | app.css<br>lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/brokers/lots/lotGanttChartHelpers.ts … |
| `#f1f5f9` | 43 | 13 | lib/components/charts/echartsTooltipHelpers.ts<br>lib/components/dashboard/AllocationHistoryChart.svelte<br>lib/components/dashboard/GrowthChart.svelte<br>lib/components/files/FilePreviewModal.svelte … |
| `#e5e7eb` | 41 | 11 | app.css<br>lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/charts/CandlestickChart.svelte<br>lib/components/files/FileGrid.svelte … |
| `#f3f4f6` | 39 | 7 | app.css<br>lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/files/FileGrid.svelte<br>lib/components/ui/media/AssetPickerModal.svelte … |
| `#6b7280` | 38 | 17 | app.css<br>lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/charts/CandlestickChart.svelte<br>lib/components/charts/LineChart.svelte … |
| `#cbd5e1` | 34 | 18 | app.css<br>lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/charts/AllocationPieChart.svelte<br>lib/components/charts/GeographyMap.svelte … |
| `#d1d5db` | 32 | 11 | lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/charts/CandlestickChart.svelte<br>lib/components/charts/LineChart.svelte<br>lib/components/charts/PriceChartFull.svelte … |
| `#4b5563` | 31 | 9 | app.css<br>lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/charts/LineChart.svelte<br>lib/components/charts/chartCoreHelpers.ts … |
| `#dc2626` | 30 | 24 | lib/charts/signals/signalVisualStyle.ts<br>lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/LotWacPriceChart.svelte … |
| `#ffffff` | 28 | 14 | app.css<br>lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/LotWacPriceChart.svelte … |
| `#10b981` | 22 | 8 | lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/charts/priceChartHelpers.ts<br>lib/components/dashboard/GrowthChart.svelte<br>lib/components/files/FileGrid.svelte … |
| `#f8fafc` | 21 | 11 | app.css<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/files/FilePreviewModal.svelte<br>lib/components/risk/CorrelationHeatmap.svelte … |
| `#16a34a` | 21 | 14 | app.css<br>lib/charts/signals/signalVisualStyle.ts<br>lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotWacPriceChart.svelte … |
| `#1f2937` | 20 | 7 | lib/components/charts/CandlestickChart.svelte<br>lib/components/dashboard/PerformanceChart.svelte<br>lib/components/files/FileGrid.svelte<br>lib/components/ui/feedback/Tooltip.svelte … |
| `#f59e0b` | 18 | 13 | lib/charts/signals/ChartSignal.ts<br>lib/charts/signals/signalVisualStyle.ts<br>lib/components/charts/CandlestickChart.svelte<br>lib/components/charts/GeographyMap.svelte … |
| `#d97706` | 18 | 13 | lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/brokers/lots/lotStateVisual.ts … |
| `#f87171` | 18 | 14 | lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/lotGanttChartHelpers.ts<br>lib/components/brokers/lots/lotWacPriceChartHelpers.ts … |
| `#fbbf24` | 16 | 14 | lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/lotStateVisual.ts<br>lib/components/charts/AllocationPieChart.svelte … |
| `#60a5fa` | 16 | 10 | lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/lotGanttChartHelpers.ts<br>lib/components/charts/AllocationPieChart.svelte … |
| `#2563eb` | 14 | 12 | lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/lotGanttChartHelpers.ts<br>lib/components/charts/AllocationPieChart.svelte … |
| `#fff` | 12 | 11 | lib/components/auth/DonationPopupModal.svelte<br>lib/components/auth/ForgotPasswordCard.svelte<br>lib/components/auth/LoginCard.svelte<br>lib/components/auth/RegisterCard.svelte … |
| `#7c3aed` | 12 | 8 | lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/brokers/lots/lotGanttChartHelpers.ts … |
| `#fecaca` | 11 | 8 | lib/components/files/FileGrid.svelte<br>lib/components/table/DataTable.svelte<br>lib/components/table/DataTableColumnFilter.svelte<br>lib/components/table/DataTableToolbar.svelte … |
| `#111827` | 10 | 6 | app.css<br>lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/charts/CandlestickChart.svelte<br>lib/components/files/FilePreviewModal.svelte … |
| `#b91c1c` | 9 | 8 | lib/components/files/FilePreviewModal.svelte<br>lib/components/risk/CorrelationHeatmap.svelte<br>lib/components/risk/CorrelationPairsList.svelte<br>lib/components/table/DataTableColumnFilter.svelte … |
| `#fef2f2` | 8 | 7 | lib/components/files/FileGrid.svelte<br>lib/components/table/DataTableToolbar.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte<br>lib/components/ui/ContextMenu.svelte … |
| `#f9fafb` | 7 | 6 | app.css<br>lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/ui/media/AssetPickerModal.svelte<br>lib/components/ui/media/FileEditModal.svelte … |
| `#3b82f6` | 7 | 5 | lib/charts/signals/ChartSignal.ts<br>lib/charts/signals/registry.ts<br>lib/components/dashboard/AllocationHistoryChart.svelte<br>lib/components/dashboard/GrowthChart.svelte … |
| `#059669` | 7 | 7 | lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/charts/AllocationPieChart.svelte<br>lib/components/ui/media/AssetPickerModal.svelte … |
| `#a78bfa` | 7 | 6 | lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/lotComparisonChartHelpers.ts<br>lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/AllocationHistoryChart.svelte … |
| `#f0fdf4` | 7 | 6 | lib/components/charts/GeographyMap.svelte<br>lib/components/files/FileGrid.svelte<br>lib/components/table/DataTable.svelte<br>lib/components/table/DataTablePagination.svelte … |
| `#7f1d1d` | 7 | 5 | lib/components/table/DataTable.svelte<br>lib/components/table/DataTableColumnFilter.svelte<br>lib/components/table/DataTableToolbar.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte … |
| `#c084fc` | 6 | 4 | lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/lotGanttChartHelpers.ts<br>lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/AllocationHistoryChart.svelte |
| `#22c55e` | 5 | 5 | app.css<br>lib/components/charts/GeographyMap.svelte<br>lib/components/charts/scatterChartHelpers.ts<br>lib/components/ui/media/FileUploader.svelte … |
| `#166534` | 5 | 4 | app.css<br>lib/components/dashboard/PerformanceChart.svelte<br>lib/components/table/DataTable.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte |
| `#143326` | 5 | 5 | lib/components/brokers/BrokerImportFilesModal.svelte<br>lib/components/ui/media/AssetPickerModal.svelte<br>lib/components/ui/media/FileEditModal.svelte<br>lib/components/ui/media/ImageEditModal.svelte … |
| `#86efac` | 5 | 5 | lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/charts/GeographyMap.svelte<br>lib/components/table/DataTable.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte … |
| `#fca5a5` | 5 | 3 | lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/files/FileGrid.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte |
| `#1d4ed8` | 5 | 4 | lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/files/FilePreviewModal.svelte<br>lib/components/risk/CorrelationHeatmap.svelte<br>lib/components/risk/CorrelationPairsList.svelte |
| `#ef4444` | 5 | 4 | lib/components/charts/lineChartHelpers.ts<br>lib/components/charts/priceChartHelpers.ts<br>lib/components/dashboard/AllocationHistoryChart.svelte<br>lib/components/table/DataTable.svelte |
| `#9caf9c` | 4 | 3 | app.css<br>lib/components/dashboard/GrowthChart.svelte<br>lib/components/ui/AnimatedBackground.svelte |
| `#34d399` | 4 | 4 | lib/components/brokers/lots/LotComparisonChart.svelte<br>lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/GrowthChart.svelte |
| `#facc15` | 4 | 4 | lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/brokers/lots/lotComparisonChartHelpers.ts<br>lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/GrowthChart.svelte |
| `#0f0f18` | 4 | 2 | lib/components/brokers/lots/UnifiedLotsTable.svelte<br>lib/components/transactions/TransactionsTable.svelte |
| `#f3e8ff` | 4 | 2 | lib/components/brokers/lots/UnifiedLotsTable.svelte<br>lib/components/table/DataTable.svelte |
| `#fee2e2` | 4 | 4 | lib/components/table/DataTable.svelte<br>lib/components/table/DataTableColumnFilter.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte<br>lib/components/ui/media/FileUploader.svelte |
| `#f5f4ef` | 3 | 2 | app.css<br>lib/components/ui/AnimatedBackground.svelte |
| `#8b5cf6` | 3 | 3 | lib/charts/signals/ChartSignal.ts<br>lib/charts/signals/signalVisualStyle.ts<br>lib/components/dashboard/AllocationHistoryChart.svelte |
| `#fef3c7` | 3 | 3 | lib/components/assets/AssetTable.svelte<br>lib/components/table/DataTable.svelte<br>lib/components/ui/media/FileUploader.svelte |
| `#e9d5ff` | 3 | 2 | lib/components/brokers/lots/UnifiedLotsTable.svelte<br>lib/components/table/DataTable.svelte |
| `#0d9488` | 3 | 3 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/charts/SemiDonutChart.svelte<br>lib/components/dashboard/GrowthChart.svelte |
| `#6366f1` | 3 | 3 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/charts/allocationHierarchy.ts<br>lib/components/dashboard/AllocationHistoryChart.svelte |
| `#2dd4bf` | 3 | 3 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/AllocationHistoryChart.svelte<br>lib/components/dashboard/GrowthChart.svelte |
| `#f472b6` | 3 | 3 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/AllocationHistoryChart.svelte<br>lib/components/dashboard/GrowthChart.svelte |
| `#fb923c` | 3 | 3 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/AllocationHistoryChart.svelte<br>lib/components/dashboard/GrowthChart.svelte |
| `#22d3ee` | 3 | 3 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/AllocationHistoryChart.svelte<br>lib/components/dashboard/GrowthChart.svelte |
| `#1e3a5f` | 3 | 2 | lib/components/table/DataTable.svelte<br>lib/components/ui/media/FileUploader.svelte |
| `#dcfce7` | 3 | 2 | lib/components/table/DataTable.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte |
| `#173a2c` | 2 | 1 | app.css |
| `#00d681` | 2 | 2 | app.css<br>lib/features/tools/pac-allocator/planner/result/ExposureBars.svelte |
| `#ec4899` | 2 | 2 | lib/charts/signals/ChartSignal.ts<br>lib/components/dashboard/AllocationHistoryChart.svelte |
| `#06b6d4` | 2 | 2 | lib/charts/signals/ChartSignal.ts<br>lib/components/dashboard/AllocationHistoryChart.svelte |
| `#84cc16` | 2 | 2 | lib/charts/signals/ChartSignal.ts<br>lib/components/dashboard/AllocationHistoryChart.svelte |
| `#f97316` | 2 | 2 | lib/charts/signals/MeasureSignal.ts<br>lib/components/dashboard/AllocationHistoryChart.svelte |
| `#a855f7` | 2 | 2 | lib/components/assets/AssetDataEditorSection.svelte<br>lib/components/fx/FxDataEditorSection.svelte |
| `#fffbeb` | 2 | 2 | lib/components/assets/AssetTable.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte |
| `#ca8a04` | 2 | 2 | lib/components/brokers/lots/LotGanttChart.svelte<br>lib/components/charts/AllocationPieChart.svelte |
| `#93c5fd` | 2 | 2 | lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/ui/feedback/Tooltip.svelte |
| `#fcd34d` | 2 | 2 | lib/components/brokers/lots/LotWacPriceChart.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte |
| `#c4b5fd` | 2 | 1 | lib/components/brokers/lots/LotWacPriceChart.svelte |
| `#b08d00` | 2 | 2 | lib/components/brokers/lots/lotComparisonChartHelpers.ts<br>lib/components/dashboard/GrowthChart.svelte |
| `#38bdf8` | 2 | 2 | lib/components/brokers/lots/lotStateVisual.ts<br>lib/components/charts/scatterChartHelpers.ts |
| `#0284c7` | 2 | 2 | lib/components/brokers/lots/lotStateVisual.ts<br>lib/components/charts/scatterChartHelpers.ts |
| `#be185d` | 2 | 2 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/charts/SemiDonutChart.svelte |
| `#4f46e5` | 2 | 2 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/charts/SemiDonutChart.svelte |
| `#ea580c` | 2 | 2 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/GrowthChart.svelte |
| `#0891b2` | 2 | 2 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/GrowthChart.svelte |
| `#818cf8` | 2 | 2 | lib/components/charts/AllocationPieChart.svelte<br>lib/components/dashboard/AllocationHistoryChart.svelte |
| `#293548` | 2 | 1 | lib/components/charts/AllocationPieChart.svelte |
| `#000` | 2 | 2 | lib/components/charts/ChartSettingsModal.svelte<br>lib/components/dashboard/AllocationHistoryChart.svelte |
| `#1e3a2f` | 2 | 2 | lib/components/charts/GeographyMap.svelte<br>lib/features/tools/pac-allocator/planner/result/ExposureMaps.svelte |
| `#22543d` | 2 | 2 | lib/components/charts/GeographyMap.svelte<br>lib/features/tools/pac-allocator/planner/result/ExposureMaps.svelte |
| `#276749` | 2 | 2 | lib/components/charts/GeographyMap.svelte<br>lib/features/tools/pac-allocator/planner/result/ExposureMaps.svelte |
| `#2f855a` | 2 | 2 | lib/components/charts/GeographyMap.svelte<br>lib/features/tools/pac-allocator/planner/result/ExposureMaps.svelte |
| `#38a169` | 2 | 2 | lib/components/charts/GeographyMap.svelte<br>lib/features/tools/pac-allocator/planner/result/ExposureMaps.svelte |
| `#48bb78` | 2 | 2 | lib/components/charts/GeographyMap.svelte<br>lib/features/tools/pac-allocator/planner/result/ExposureMaps.svelte |
| `#bbf7d0` | 2 | 2 | lib/components/charts/GeographyMap.svelte<br>lib/features/tools/pac-allocator/planner/result/ExposureMaps.svelte |
| `#7e22ce` | 2 | 2 | lib/components/dashboard/AllocationHistoryChart.svelte<br>lib/components/table/DataTable.svelte |
| `#a3e635` | 2 | 2 | lib/components/dashboard/AllocationHistoryChart.svelte<br>lib/components/dashboard/GrowthChart.svelte |
| `#b45309` | 2 | 1 | lib/components/files/FilePreviewModal.svelte |
| `#ff4500` | 2 | 1 | lib/components/support/supportLinks.ts |
| `#0866ff` | 2 | 1 | lib/components/support/supportLinks.ts |
| `#c13584` | 2 | 1 | lib/components/support/supportLinks.ts |
| `#eff6ff` | 2 | 2 | lib/components/table/DataTable.svelte<br>lib/components/ui/media/FileUploader.svelte |
| `#14532d` | 2 | 1 | lib/components/table/DataTable.svelte |
| `#92400e` | 2 | 2 | lib/components/table/DataTable.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte |
| `#991b1b` | 2 | 2 | lib/components/table/DataTable.svelte<br>lib/components/transactions/modals/ImportBrokerMismatchModal.svelte |
| `#dbeafe` | 2 | 2 | lib/components/table/DataTable.svelte<br>lib/components/ui/media/FileUploader.svelte |
| `#1a403140` | 2 | 1 | lib/components/table/DataTable.svelte |
| `#4ade8040` | 2 | 1 | lib/components/table/DataTable.svelte |
| `#153428` | 2 | 2 | lib/components/transactions/modals/ImportBrokerMismatchModal.svelte<br>lib/components/ui/modals/ConfirmModal.svelte |
| `#450a0a` | 2 | 2 | lib/components/ui/ContextMenu.svelte<br>lib/components/ui/media/FileUploader.svelte |
| `#1a2332` | 2 | 2 | lib/components/ui/media/AssetPickerModal.svelte<br>lib/components/ui/media/ImageEditModal.svelte |
| `#111111` | 1 | 1 | app.css |
| `#e8f0ed` | 1 | 1 | app.css |
| `#c5d9d0` | 1 | 1 | app.css |
| `#9fc0b2` | 1 | 1 | app.css |
| `#78a793` | 1 | 1 | app.css |
| `#5a947c` | 1 | 1 | app.css |
| `#133125` | 1 | 1 | app.css |
| `#0f281e` | 1 | 1 | app.css |
| `#0a1c14` | 1 | 1 | app.css |
| `#fdfcfa` | 1 | 1 | app.css |
| `#edeae2` | 1 | 1 | app.css |
| `#e0dcd0` | 1 | 1 | app.css |
| `#d3cec0` | 1 | 1 | app.css |
| `#c5c0b0` | 1 | 1 | app.css |
| `#00834f` | 1 | 1 | app.css |
| `#546175` | 1 | 1 | app.css |
| `#39af50` | 1 | 1 | app.css |
| `#e0f2fe` | 1 | 1 | lib/components/brokers/lots/LotGanttChart.svelte |
| `#6d28d9` | 1 | 1 | lib/components/brokers/lots/lotComparisonChartHelpers.ts |
| `#9333ea` | 1 | 1 | lib/components/charts/AllocationPieChart.svelte |
| `#a5b4fc` | 1 | 1 | lib/components/charts/AllocationPieChart.svelte |
| `#888` | 1 | 1 | lib/components/charts/CandlestickChart.svelte |
| `#14b8a6` | 1 | 1 | lib/components/dashboard/AllocationHistoryChart.svelte |
| `#a3a3a3` | 1 | 1 | lib/components/dashboard/AllocationHistoryChart.svelte |
| `#a21caf` | 1 | 1 | lib/components/dashboard/AllocationHistoryChart.svelte |
| `#d4d4d4` | 1 | 1 | lib/components/dashboard/AllocationHistoryChart.svelte |
| `#e879f9` | 1 | 1 | lib/components/dashboard/AllocationHistoryChart.svelte |
| `#000000` | 1 | 1 | lib/components/dashboard/AllocationHistoryChart.svelte |
| `#6b8e6b` | 1 | 1 | lib/components/dashboard/GrowthChart.svelte |
| `#db2777` | 1 | 1 | lib/components/dashboard/GrowthChart.svelte |
| `#65a30d` | 1 | 1 | lib/components/dashboard/GrowthChart.svelte |
| `#fef08a` | 1 | 1 | lib/components/layout/ChangelogModal.svelte |
| `#e03d00` | 1 | 1 | lib/components/support/supportLinks.ts |
| `#0758db` | 1 | 1 | lib/components/support/supportLinks.ts |
| `#833ab4` | 1 | 1 | lib/components/support/supportLinks.ts |
| `#405de6` | 1 | 1 | lib/components/support/supportLinks.ts |
| `#25f4ee` | 1 | 1 | lib/components/support/supportLinks.ts |
| `#1a2e35` | 1 | 1 | lib/components/table/DataTable.svelte |
| `#ecfdf5` | 1 | 1 | lib/components/table/DataTable.svelte |
| `#d1fae5` | 1 | 1 | lib/components/table/DataTable.svelte |
| `#1e40af` | 1 | 1 | lib/components/table/DataTable.svelte |
| `#78350f` | 1 | 1 | lib/components/table/DataTable.svelte |
| `#fde68a` | 1 | 1 | lib/components/table/DataTable.svelte |
| `#1e3a8a` | 1 | 1 | lib/components/table/DataTable.svelte |
| `#bfdbfe` | 1 | 1 | lib/components/table/DataTable.svelte |
| `#11151c` | 1 | 1 | lib/components/ui/AnimatedBackground.svelte |
| `#00ff9a` | 1 | 1 | lib/components/ui/AnimatedBackground.svelte |
| `#61666f` | 1 | 1 | lib/components/ui/feedback/Tooltip.svelte |
| `#451a03` | 1 | 1 | lib/components/ui/media/FileUploader.svelte |
| `#143426` | 1 | 1 | lib/components/ui/media/FileUploader.svelte |
| `#1a1a1a` | 1 | 1 | lib/components/ui/media/ImageCropper.svelte |
| `#156534` | 1 | 1 | lib/stores/app/themeStore.ts |
| `#a7f3d0` | 1 | 1 | routes/(app)/files/+page.svelte |

## rgb/rgba/hsl/color-mix (prod) — distinct expressions (top 80)

| Expression | Uses |
|---|---:|
| `rgba(0,0,0,0.5)` | 7 |
| `rgba(255,255,255,0.9)` | 5 |
| `rgba(0,0,0,0.3)` | 4 |
| `rgba(147,51,234,0.25)` | 4 |
| `rgb(000/0.1)` | 4 |
| `rgba(26,64,49,0.1)` | 3 |
| `rgba(0,0,0,0.4)` | 3 |
| `rgba(220,38,38,0.3)` | 3 |
| `rgba(0,0,0,0.1)` | 3 |
| `rgba(0,0,0,0.08)` | 2 |
| `rgba(0,0,0,0.12)` | 2 |
| `rgb(7185105)` | 2 |
| `rgba(147,51,234,0.4)` | 2 |
| `color-mix(insrgb,var(--broker-vivid,transparent)22%,#0f0f18)` | 2 |
| `rgba(255,255,255,0.75)` | 2 |
| `rgba(100,116,139,0.3)` | 2 |
| `rgba(203,213,225,0.5)` | 2 |
| `rgb(304159)` | 2 |
| `rgba(148,163,184,0.14)` | 2 |
| `rgba(220,38,38,0.2)` | 2 |
| `rgba(0,0,0,0.2)` | 2 |
| `rgb(255255255/0.08)` | 2 |
| `rgba(26,64,49,0.2)` | 2 |
| `rgba(74,222,128,0.2)` | 2 |
| `rgb(000/0.05)` | 2 |
| `rgb(99102241/0)` | 2 |
| `rgb(156163175)` | 2 |
| `rgba(245,158,11,0.1)` | 2 |
| `rgba(245,158,11,0.2)` | 2 |
| `rgba(220,38,38,0.1)` | 2 |
| `rgba(0,0,0,0.7)` | 2 |
| `rgba(34,197,94,0.15)` | 1 |
| `rgba(30,41,59,0.95)` | 1 |
| `rgb(1205315/0.24)` | 1 |
| `rgb(1205315/0.36)` | 1 |
| `rgb(209213219)` | 1 |
| `rgba(255,255,255,0.2)` | 1 |
| `rgba(168,85,247,0.16)` | 1 |
| `rgba(147,51,234,0.12)` | 1 |
| `rgba(96,165,250,0.10)` | 1 |
| `rgba(59,130,246,0.08)` | 1 |
| `rgba(168,85,247,0.35)` | 1 |
| `rgba(226,232,240,0.48)` | 1 |
| `rgba(71,85,105,0.45)` | 1 |
| `rgba(148,163,184,0.75)` | 1 |
| `rgba(71,85,105,0.6)` | 1 |
| `color-mix(insrgb,var(--broker-vivid-light,transparent)26%,white)` | 1 |
| `color-mix(insrgb,var(--broker-vivid,transparent)14%,#0f0f18)` | 1 |
| `color-mix(insrgb,var(--broker-vivid-light,transparent)68%,white)` | 1 |
| `hsl(...)` | 1 |
| `hsla(...,alpha)` | 1 |
| `hsla(${hslmatch[1]},${alpha})` | 1 |
| `hsl(${hue}78%68%)` | 1 |
| `hsl(${hue}68%44%)` | 1 |
| `rgba(15,23,42,0.55)` | 1 |
| `rgba(255,255,255,0.72)` | 1 |
| `rgba(0,0,0,0.6)` | 1 |
| `rgba(255,255,255,0.8)` | 1 |
| `rgba(${r},${g},${b},${alpha})` | 1 |
| `rgb(${34+intensity*40},${197+intensity*40},${94+intensity*40})` | 1 |
| `rgb(${22-intensity*10},${163-intensity*30},${74+intensity*20})` | 1 |
| `rgb(${248},${113-intensity*40},${113-intensity*40})` | 1 |
| `rgb(${220+intensity*20},${38+intensity*20},${38+intensity*20})` | 1 |
| `rgba(30,41,59,0.8)` | 1 |
| `rgba(248,250,252,0.8)` | 1 |
| `rgba(22,163,74,${alpha})` | 1 |
| `rgba(220,38,38,${alpha})` | 1 |
| `rgb(255255255/0.5)` | 1 |
| `rgb(304159/0.4)` | 1 |
| `rgb(229231235/0.7)` | 1 |
| `rgba(148,163,184,0.16)` | 1 |
| `rgba(148,163,184,0.12)` | 1 |
| `rgb(000/0.3)` | 1 |
| `rgba(16,185,129,0.1)` | 1 |
| `rgba(220,38,38,0.4)` | 1 |
| `rgba(251,191,36,0.35)` | 1 |
| `rgba(37,99,235,0.38)` | 1 |
| `rgba(0,0,0,0.05)` | 1 |
| `rgba(255,255,255,0.08)` | 1 |
| `rgba(234,179,8,0.35)` | 1 |

## CSS custom properties — definitions

| Property | Value | Defined at | var() uses |
|---|---|---|---:|
| `--font-sans` | `'LF Flags', Inter, system-ui, sans-serif` | src/app.css:11 | 0 |
| `--font-mono` | `'LF Flags', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Li` | src/app.css:12 | 0 |
| `--color-libre-green` | `#1a4031` | src/app.css:15 | 1 |
| `--color-libre-banner` | `#1a4031` | src/app.css:16 | 0 |
| `--color-libre-beige` | `#f5f4ef` | src/app.css:17 | 0 |
| `--color-libre-sage` | `#9caf9c` | src/app.css:18 | 0 |
| `--color-libre-dark` | `#111111` | src/app.css:19 | 0 |
| `--color-primary-50` | `#e8f0ed` | src/app.css:22 | 0 |
| `--color-primary-100` | `#c5d9d0` | src/app.css:23 | 0 |
| `--color-primary-200` | `#9fc0b2` | src/app.css:24 | 0 |
| `--color-primary-300` | `#78a793` | src/app.css:25 | 0 |
| `--color-primary-400` | `#5a947c` | src/app.css:26 | 0 |
| `--color-primary-500` | `#1a4031` | src/app.css:27 | 0 |
| `--color-primary-600` | `#173a2c` | src/app.css:28 | 0 |
| `--color-primary-700` | `#133125` | src/app.css:29 | 0 |
| `--color-primary-800` | `#0f281e` | src/app.css:30 | 0 |
| `--color-primary-900` | `#0a1c14` | src/app.css:31 | 0 |
| `--color-surface-50` | `#fdfcfa` | src/app.css:34 | 0 |
| `--color-surface-100` | `#f5f4ef` | src/app.css:35 | 0 |
| `--color-surface-200` | `#edeae2` | src/app.css:36 | 0 |
| `--color-surface-300` | `#e0dcd0` | src/app.css:37 | 0 |
| `--color-surface-400` | `#d3cec0` | src/app.css:38 | 0 |
| `--color-surface-500` | `#c5c0b0` | src/app.css:39 | 0 |
| `--shadow-card` | `0 4px 20px rgba(0, 0, 0, 0.08)` | src/app.css:42 | 0 |
| `--shadow-card-hover` | `0 8px 30px rgba(0, 0, 0, 0.12)` | src/app.css:43 | 0 |
| `--radius-xl` | `1rem` | src/app.css:46 | 0 |
| `--radius-2xl` | `1.5rem` | src/app.css:47 | 0 |
| `--theme-bg-primary` | `#ffffff` | src/app.css:127 | 2 |
| `--theme-bg-secondary` | `#f9fafb` | src/app.css:128 | 3 |
| `--theme-bg-tertiary` | `#f3f4f6` | src/app.css:129 | 1 |
| `--theme-bg-card` | `#ffffff` | src/app.css:130 | 1 |
| `--theme-bg-hover` | `#f3f4f6` | src/app.css:131 | 2 |
| `--theme-text-primary` | `#111827` | src/app.css:132 | 5 |
| `--theme-text-secondary` | `#4b5563` | src/app.css:134 | 1 |
| `--theme-text-tertiary` | `#9ca3af` | src/app.css:135 | 1 |
| `--theme-text-muted` | `#6b7280` | src/app.css:136 | 1 |
| `--theme-border-primary` | `#e5e7eb` | src/app.css:137 | 2 |
| `--theme-border-secondary` | `#f3f4f6` | src/app.css:139 | 0 |
| `--theme-accent` | `#1a4031` | src/app.css:140 | 0 |
| `--theme-accent-hover` | `#173a2c` | src/app.css:142 | 0 |
| `--theme-accent-bg` | `rgba(26, 64, 49, 0.1)` | src/app.css:143 | 0 |
| `--theme-shadow` | `0 4px 20px rgba(0, 0, 0, 0.08)` | src/app.css:144 | 1 |
| `--theme-shadow-hover` | `0 8px 30px rgba(0, 0, 0, 0.12)` | src/app.css:146 | 0 |
| `--color-libre-green` | `#00d681` | src/app.css:151 | 1 |
| `--color-libre-banner` | `#00834f` | src/app.css:152 | 0 |
| `--theme-bg-primary` | `#0f172a` | src/app.css:153 | 2 |
| `--theme-bg-secondary` | `#1e293b` | src/app.css:154 | 3 |
| `--theme-bg-tertiary` | `#334155` | src/app.css:155 | 1 |
| `--theme-bg-card` | `#1e293b` | src/app.css:156 | 1 |
| `--theme-bg-hover` | `#334155` | src/app.css:157 | 2 |
| `--theme-text-primary` | `#f8fafc` | src/app.css:158 | 5 |
| `--theme-text-secondary` | `#cbd5e1` | src/app.css:160 | 1 |
| `--theme-text-tertiary` | `#64748b` | src/app.css:161 | 1 |
| `--theme-text-muted` | `#94a3b8` | src/app.css:162 | 1 |
| `--theme-border-primary` | `#334155` | src/app.css:163 | 2 |
| `--theme-border-secondary` | `#1e293b` | src/app.css:165 | 0 |
| `--theme-accent` | `#22c55e` | src/app.css:166 | 0 |
| `--theme-accent-hover` | `#16a34a` | src/app.css:168 | 0 |
| `--theme-accent-bg` | `rgba(34, 197, 94, 0.15)` | src/app.css:169 | 0 |
| `--theme-shadow` | `0 4px 20px rgba(0, 0, 0, 0.3)` | src/app.css:170 | 1 |
| `--theme-shadow-hover` | `0 8px 30px rgba(0, 0, 0, 0.4)` | src/app.css:172 | 0 |
| `--tw-shadow` | `var(--theme-shadow)` | src/app.css:217 | 0 |
| `--tw-ring-color` | `#4ade80` | src/app.css:274 | 0 |
| `--tw-shadow` | `0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -4px rgba(0, 0, 0, 0.3)` | src/app.css:285 | 0 |
| `--tw-shadow` | `0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3` | src/app.css:289 | 0 |
| `--lf-price-flash-rest` | `var(--color-gray-700)` | src/app.css:327 | 1 |
| `--lf-price-flash-peak` | `var(--color-emerald-600)` | src/app.css:331 | 2 |
| `--lf-price-flash-peak` | `var(--color-red-500)` | src/app.css:335 | 2 |
| `--lf-price-flash-rest` | `var(--color-gray-200)` | src/app.css:340 | 1 |
| `--lf-price-flash-peak` | `var(--color-emerald-400)` | src/app.css:344 | 2 |
| `--lf-price-flash-peak` | `var(--color-red-400)` | src/app.css:348 | 2 |
| `--lot-highlight-base` | `#f3e8ff` | src/lib/components/brokers/lots/UnifiedLotsTable.svelte:793 | 3 |
| `--lot-highlight-peak` | `#e9d5ff` | src/lib/components/brokers/lots/UnifiedLotsTable.svelte:794 | 1 |
| `--lot-highlight-base` | `rgba(147, 51, 234, 0.25)` | src/lib/components/brokers/lots/UnifiedLotsTable.svelte:799 | 3 |
| `--lot-highlight-peak` | `rgba(147, 51, 234, 0.4)` | src/lib/components/brokers/lots/UnifiedLotsTable.svelte:800 | 1 |
| `--highlight-base` | `#f3e8ff` | src/lib/components/table/DataTable.svelte:1885 | 1 |
| `--highlight-peak` | `#e9d5ff` | src/lib/components/table/DataTable.svelte:1886 | 1 |
| `--highlight-base` | `rgba(147, 51, 234, 0.25)` | src/lib/components/table/DataTable.svelte:1896 | 1 |
| `--highlight-peak` | `rgba(147, 51, 234, 0.4)` | src/lib/components/table/DataTable.svelte:1897 | 1 |
| `--theme-color` | `rgba(0, 0, 0, 0.5)` | src/lib/components/ui/media/ImageCropper.svelte:901 | 0 |
| `--cropper-backdrop-color` | `rgba(0, 0, 0, 0.3)` | src/lib/components/ui/media/ImageCropper.svelte:902 | 0 |
| `--cropper-selection-outline-width` | `2px` | src/lib/components/ui/media/ImageCropper.svelte:925 | 0 |
| `--cropper-selection-outline-color` | `rgba(255, 255, 255, 0.9)` | src/lib/components/ui/media/ImageCropper.svelte:926 | 0 |
| `--theme-color` | `rgba(0, 0, 0, 0.7)` | src/lib/components/ui/media/ImageCropper.svelte:1009 | 0 |
| `--cropper-backdrop-color` | `rgba(0, 0, 0, 0.8)` | src/lib/components/ui/media/ImageCropper.svelte:1010 | 0 |
| `--cropper-selection-outline-color` | `rgba(255, 255, 255, 0.9)` | src/lib/components/ui/media/ImageCropper.svelte:1014 | 0 |

## var() references with no definition in frontend/src

- `--badge-text` ×7 — e.g. src/lib/components/auth/UpdateAvailableModal.svelte
- `--badge-dark-text` ×7 — e.g. src/lib/components/auth/UpdateAvailableModal.svelte
- `--badge-bg` ×6 — e.g. src/lib/components/auth/UpdateAvailableModal.svelte
- `--badge-dark-bg` ×6 — e.g. src/lib/components/auth/UpdateAvailableModal.svelte
- `--broker-vivid-light` ×4 — e.g. src/lib/components/brokers/lots/UnifiedLotsTable.svelte
- `--broker-vivid` ×4 — e.g. src/lib/components/brokers/lots/UnifiedLotsTable.svelte
- `--prov-bg` ×3 — e.g. src/lib/components/ui/select/FxProviderSelect.svelte
- `--stale-opacity` ×2 — e.g. src/lib/components/table/DataTable.svelte
- `--prov-border` ×2 — e.g. src/lib/components/ui/select/FxProviderSelect.svelte
- `--color-gray-700` ×1 — e.g. src/app.css
- `--color-emerald-600` ×1 — e.g. src/app.css
- `--color-red-500` ×1 — e.g. src/app.css
- `--color-gray-200` ×1 — e.g. src/app.css
- `--color-emerald-400` ×1 — e.g. src/app.css
- `--color-red-400` ×1 — e.g. src/app.css
- `--chart-1` ×1 — e.g. src/lib/components/charts/__tests__/allocationHierarchy.test.ts
- `--broker-bg` ×1 — e.g. src/lib/components/table/DataTable.svelte
- `--broker-text` ×1 — e.g. src/lib/components/table/DataTable.svelte
- `--broker-dark-bg` ×1 — e.g. src/lib/components/table/DataTable.svelte
- `--broker-dark-text` ×1 — e.g. src/lib/components/table/DataTable.svelte
- `--priority-w` ×1 — e.g. src/lib/components/transactions/modals/ImportWizardModal.svelte
- `--prov-dark-bg` ×1 — e.g. src/lib/components/ui/select/FxProviderSelect.svelte

## Hotspot files (prod)

| File | TW palette | of which dark: | custom tokens | arbitrary | hex | rgb/hsl | var() |
|---|---:|---:|---:|---:|---:|---:|---:|
| src/lib/components/transactions/modals/ImportWizardModal.svelte | 527 | 242 | 40 | 0 | 1 | 0 | 1 |
| src/routes/(app)/assets/[id]/+page.svelte | 273 | 138 | 17 | 0 | 0 | 0 | 0 |
| src/lib/components/brokers/lots/LotCustodyModal.svelte | 212 | 107 | 4 | 0 | 0 | 0 | 0 |
| src/lib/components/transactions/modals/TransactionFormModal.svelte | 197 | 90 | 16 | 0 | 0 | 0 | 0 |
| src/lib/components/brokers/BrokerSharingPanel.svelte | 200 | 99 | 11 | 0 | 0 | 0 | 0 |
| src/routes/(app)/assets/+page.svelte | 191 | 104 | 17 | 0 | 0 | 0 | 0 |
| src/lib/components/assets/AssetModal.svelte | 179 | 84 | 20 | 0 | 0 | 0 | 0 |
| src/lib/components/transactions/import/FixFlaggedStep.svelte | 188 | 98 | 2 | 0 | 0 | 0 | 0 |
| src/lib/components/transactions/modals/TransactionBulkModal.svelte | 180 | 75 | 6 | 0 | 0 | 0 | 0 |
| src/lib/components/risk/RiskAnalysisPanel.svelte | 169 | 90 | 5 | 0 | 2 | 0 | 0 |
| src/lib/components/settings/tabs/ProfileTab.svelte | 145 | 71 | 16 | 0 | 0 | 0 | 0 |
| src/lib/components/table/DataTable.svelte | 3 | 1 | 0 | 0 | 129 | 18 | 8 |
| src/lib/components/ui/select/FxProviderSelect.svelte | 138 | 62 | 7 | 0 | 1 | 0 | 10 |
| src/routes/(app)/fx/[pair]/+page.svelte | 153 | 77 | 3 | 0 | 0 | 0 | 0 |
| src/lib/features/tools/pac-allocator/planner/ui.ts | 133 | 68 | 21 | 0 | 0 | 0 | 0 |
| src/lib/components/settings/tabs/AboutTab.svelte | 147 | 4 | 5 | 0 | 1 | 0 | 0 |
| src/lib/components/transactions/modals/TransactionActionModal.svelte | 145 | 69 | 0 | 0 | 4 | 0 | 4 |
| src/lib/components/transactions/modals/ParseDetailModal.svelte | 135 | 60 | 2 | 0 | 0 | 0 | 0 |
| src/routes/(app)/brokers/[id]/+page.svelte | 117 | 54 | 13 | 0 | 0 | 0 | 0 |
| src/lib/components/dashboard/GrowthChart.svelte | 64 | 36 | 7 | 0 | 57 | 0 | 0 |
| src/lib/components/table/DataTableColumnFilter.svelte | 0 | 0 | 0 | 0 | 120 | 6 | 0 |
| src/lib/components/transactions/import/AssetGroupStep.svelte | 121 | 53 | 0 | 0 | 0 | 0 | 0 |
| src/app.css | 12 | 0 | 5 | 0 | 56 | 13 | 29 |
| src/lib/components/brokers/lots/UnifiedLotsTable.svelte | 96 | 48 | 0 | 0 | 4 | 6 | 8 |
| src/lib/components/settings/SchedulerLogModal.svelte | 113 | 45 | 0 | 0 | 0 | 0 | 0 |
| src/lib/components/ui/media/ImageEditModal.svelte | 0 | 0 | 0 | 0 | 96 | 10 | 1 |
| src/lib/components/transactions/modals/PromoteMergeModal.svelte | 98 | 46 | 0 | 0 | 4 | 0 | 4 |
| src/lib/components/settings/tabs/GlobalSettingsTab.svelte | 90 | 41 | 15 | 0 | 0 | 0 | 0 |
| src/lib/components/dashboard/KpiSection.svelte | 101 | 52 | 0 | 0 | 0 | 2 | 0 |
| src/lib/components/assets/ScheduledInvestmentEditor.svelte | 94 | 46 | 6 | 0 | 0 | 2 | 0 |
| src/lib/components/settings/SchedulerConfigModal.svelte | 88 | 46 | 14 | 0 | 0 | 0 | 0 |
| src/lib/components/brokers/lots/LotComparisonChart.svelte | 71 | 40 | 8 | 0 | 22 | 0 | 0 |
| src/lib/components/ui/select/AssetPickerPanel.svelte | 88 | 45 | 13 | 0 | 0 | 0 | 0 |
| src/lib/components/transactions/wac/WacPreviewSection.svelte | 87 | 38 | 9 | 0 | 0 | 0 | 0 |
| src/lib/components/transactions/import/GapFixStep.svelte | 85 | 41 | 10 | 0 | 0 | 0 | 0 |
| src/lib/components/layout/ChangelogModal.svelte | 82 | 40 | 4 | 0 | 5 | 3 | 0 |
| src/lib/components/charts/ChartSignalsSection.svelte | 86 | 33 | 7 | 0 | 0 | 0 | 0 |
| src/lib/components/transactions/import/ReportSetCard.svelte | 83 | 36 | 10 | 0 | 0 | 0 | 0 |
| src/lib/components/assets/ProviderAssignmentSection.svelte | 86 | 38 | 5 | 0 | 0 | 0 | 0 |
| src/routes/(app)/fx/+page.svelte | 74 | 40 | 11 | 0 | 0 | 0 | 0 |
| src/lib/components/assets/AssetCard.svelte | 75 | 34 | 8 | 0 | 0 | 0 | 0 |
| src/lib/components/files/FilePreviewModal.svelte | 0 | 0 | 0 | 0 | 80 | 2 | 0 |
| src/lib/utils/assetTypes.ts | 80 | 40 | 0 | 0 | 0 | 0 | 0 |
| src/lib/features/tools/ToolsHub.svelte | 73 | 42 | 6 | 0 | 0 | 0 | 0 |
| src/lib/components/transactions/modals/TransactionCompareModal.svelte | 76 | 37 | 2 | 0 | 0 | 0 | 0 |
| src/lib/features/tools/ToolDiagnosticsPanel.svelte | 76 | 39 | 2 | 0 | 0 | 0 | 0 |
| src/lib/components/assets/AssetCurrencyChangeModal.svelte | 74 | 37 | 0 | 0 | 0 | 0 | 0 |
| src/lib/components/ui/media/AssetPickerModal.svelte | 0 | 0 | 0 | 0 | 70 | 2 | 0 |
| src/routes/(app)/dashboard/+page.svelte | 69 | 37 | 2 | 0 | 0 | 0 | 0 |
| src/lib/components/brokers/lots/LotWacPriceChart.svelte | 36 | 20 | 4 | 0 | 28 | 2 | 0 |
| src/lib/components/charts/ChartAestheticsSection.svelte | 63 | 33 | 7 | 0 | 0 | 0 | 0 |
| src/lib/components/transactions/events/AssetEventPicker.svelte | 60 | 29 | 9 | 0 | 0 | 0 | 0 |
| src/lib/features/ai-export/AiExportOptionsPanel.svelte | 68 | 33 | 0 | 0 | 0 | 0 | 0 |
| src/routes/(app)/files/+page.svelte | 0 | 0 | 0 | 0 | 66 | 2 | 0 |
| src/lib/components/brokers/BrokerCard.svelte | 60 | 28 | 7 | 0 | 0 | 0 | 0 |
| src/lib/components/brokers/BrokerForm.svelte | 48 | 18 | 19 | 0 | 0 | 0 | 0 |
| src/lib/components/brokers/lots/LotGanttChart.svelte | 32 | 18 | 0 | 0 | 28 | 7 | 0 |
| src/lib/components/risk/AssetSetRiskPanel.svelte | 64 | 34 | 3 | 0 | 0 | 0 | 0 |
| src/lib/components/ui/data-editor/CsvEditor.svelte | 67 | 31 | 0 | 0 | 0 | 0 | 0 |
| src/lib/components/assets/AssetMergeModal.svelte | 65 | 30 | 1 | 0 | 0 | 0 | 0 |
| src/lib/components/fx/FxCard.svelte | 59 | 27 | 7 | 0 | 0 | 0 | 0 |
| src/lib/components/ui/date/DateRangePicker.svelte | 57 | 30 | 9 | 0 | 0 | 0 | 0 |
| src/lib/components/ui/modals/SyncModalBase.svelte | 60 | 28 | 4 | 0 | 0 | 0 | 0 |
| src/lib/features/onboarding/components/OnboardingReplaySection.svelte | 62 | 32 | 2 | 0 | 0 | 0 | 0 |
| src/lib/components/ui/data-editor/DataEditor.svelte | 60 | 33 | 3 | 0 | 0 | 0 | 0 |
| src/lib/components/ui/media/FileUploader.svelte | 0 | 0 | 0 | 0 | 58 | 1 | 0 |
| src/lib/components/ui/select/SearchSelect.svelte | 42 | 20 | 17 | 0 | 0 | 0 | 0 |
| src/lib/components/assets/ProviderComparisonModal.svelte | 50 | 23 | 8 | 0 | 0 | 0 | 0 |
| src/lib/components/settings/SettingsLayout.svelte | 48 | 24 | 9 | 0 | 0 | 0 | 0 |
| src/lib/components/transactions/modals/ImportBrokerMismatchModal.svelte | 1 | 0 | 0 | 0 | 49 | 7 | 0 |
| src/lib/components/ui/media/FileEditModal.svelte | 0 | 0 | 0 | 0 | 53 | 4 | 0 |
| src/lib/features/tools/ToolAboutPanel.svelte | 54 | 29 | 3 | 0 | 0 | 0 | 0 |
| src/lib/components/charts/AllocationPieChart.svelte | 0 | 0 | 0 | 0 | 54 | 2 | 0 |
| src/lib/components/assets/AssetSearchAutocomplete.svelte | 48 | 24 | 7 | 0 | 0 | 0 | 0 |
| src/lib/features/tools/ToolHost.svelte | 51 | 28 | 3 | 0 | 0 | 0 | 0 |
| src/lib/components/files/FileGrid.svelte | 1 | 0 | 0 | 0 | 46 | 6 | 0 |
| src/lib/components/charts/PriceChartFull.svelte | 24 | 14 | 4 | 0 | 23 | 0 | 0 |
| src/lib/components/ui/data-editor/DataImportModal.svelte | 47 | 21 | 4 | 0 | 0 | 0 | 0 |
| src/lib/components/table/DataTablePagination.svelte | 0 | 0 | 0 | 0 | 46 | 4 | 0 |
| src/lib/components/risk/CorrelationHeatmap.svelte | 28 | 15 | 1 | 0 | 17 | 3 | 0 |

## Light-only candidates: ≥3 palette classes, zero `dark:`, zero var()

- src/lib/components/ui/modals/ConfirmModal.svelte (4 palette classes)
- src/lib/components/auth/RegisterCard.svelte (15 palette classes)
- src/lib/components/ui/input/PasswordStrength.svelte (24 palette classes)
- src/lib/components/auth/LoginCard.svelte (9 palette classes)
- src/lib/components/auth/ForgotPasswordCard.svelte (11 palette classes)
- src/lib/components/ui/input/PasswordInput.svelte (7 palette classes)
- src/lib/components/layout/ConnectionSecurityIndicator.svelte (6 palette classes)
- src/lib/utils/currency/fxConversionHelper.ts (6 palette classes)
- src/lib/components/layout/Sidebar.svelte (3 palette classes)
- src/lib/components/ui/feedback/ToastContainer.svelte (4 palette classes)
- src/lib/components/ui/select/ImportPluginSelect.svelte (4 palette classes)
- src/lib/utils/broker/brokerRoleHelpers.ts (4 palette classes)
- src/lib/utils/sync/syncHelpers.ts (4 palette classes)
