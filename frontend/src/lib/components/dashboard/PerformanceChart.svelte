<!--
  PerformanceChart — Diverging stacked horizontal bar chart for dashboard Performance view.

  Semantics:
  - One row per asset position.
  - Optional "Other period effects" section below asset rows.
  - Positive components stack to the right of zero.
  - Negative components stack to the left of zero.
  - Net period P&L shown as final label on each row.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {goto} from '$app/navigation';
    import {ExternalLink, Layers} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import ContextMenu, {type ContextMenuItem} from '$lib/components/ui/ContextMenu.svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {buildGridColors, buildTooltipDivider, buildTooltipHeader, buildTooltipRow, buildTooltipTheme, setupTooltipAutoHide, scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    interface AssetPeriodContribution {
        asset_id: number;
        asset_name: string;
        asset_ticker?: string | (string | null)[] | null;
        asset_type: string;
        broker_id: number;
        broker_name: string;
        period_unrealized_delta?: string | (string | null)[] | null;
        period_realized_gain_loss?: string | (string | null)[] | null;
        period_income?: string | (string | null)[] | null;
        period_fees_taxes?: string | (string | null)[] | null;
        period_pnl?: string | (string | null)[] | null;
        period_pnl_percent?: string | (string | null)[] | null;
        start_value?: string | (string | null)[] | null;
        end_value?: string | (string | null)[] | null;
        is_fully_sold?: boolean;
    }

    interface OtherPeriodEffect {
        description: string;
        category: 'Income' | 'Cost' | 'Other' | string;
        period_pnl: string;
        broker_id?: number | (number | null)[] | null;
        broker_name?: string | (string | null)[] | null;
    }

    interface Props {
        positions: ReadonlyArray<AssetPeriodContribution>;
        otherEffects: ReadonlyArray<OtherPeriodEffect>;
        displayCurrency?: string;
        onAnalyze?: (assetId: number) => void;
    }

    let {positions = [], otherEffects = [], displayCurrency = 'EUR', onAnalyze}: Props = $props();

    type ComponentKey = 'unrealized' | 'realized' | 'income' | 'costs';

    interface AssetRow {
        key: string;
        kind: 'asset';
        label: string;
        assetId: number;
        assetTicker: string | null;
        brokerName: string;
        startValue: number;
        endValue: number;
        net: number;
        isFullySold: boolean;
        components: Record<ComponentKey, number>;
    }

    interface OtherRow {
        key: string;
        kind: 'other';
        label: string;
        category: string;
        brokerName: string | null;
        net: number;
    }

    interface SectionRow {
        key: string;
        kind: 'section';
        label: string;
        net: 0;
    }

    type ChartRow = AssetRow | OtherRow | SectionRow;

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let scrollWrapper: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;
    let isDark = $state(false);
    let needsInitialLayoutStabilityPass = false;
    let contextMenu = $state<{x: number; y: number; assetId: number} | null>(null);

    // Narrow layout: label+bar side-by-side leaves almost no room for the bar itself
    // (fixed-width category label + right-side net label eat most of a narrow
    // container). Below this container width we split each logical row into two
    // category axis slots — one showing only the label+status+net P&L, the next
    // only the bar — via `displayRows` below, instead of cramming both onto one
    // thin row. Measured off the CHART CONTAINER's own rendered width (not a
    // viewport media query) since that's what actually determines whether there's
    // room — the container can be narrower than the viewport (dashboard padding/
    // sidebar) or the same, but it's always the real constraint either way.
    const NARROW_CONTAINER_THRESHOLD = 480;
    let isMobile = $state(false);
    let narrowResizeObserver: ResizeObserver | null = null;
    $effect(() => {
        if (!chartContainer) return;
        const el = chartContainer;
        isMobile = el.clientWidth > 0 && el.clientWidth < NARROW_CONTAINER_THRESHOLD;
        narrowResizeObserver?.disconnect();
        narrowResizeObserver = new ResizeObserver((entries) => {
            const width = entries[0]?.contentRect.width ?? el.clientWidth;
            isMobile = width > 0 && width < NARROW_CONTAINER_THRESHOLD;
        });
        narrowResizeObserver.observe(el);
        return () => narrowResizeObserver?.disconnect();
    });

    /** Mobile only: which logical row (matched by `ChartRow.key`, shared across its
     *  label slot AND bar slot) is currently hovered/tapped. Plain variable, not
     *  `$state` — updated imperatively via ECharts events and pushed through a
     *  targeted partial `setOption` (not the reactive rebuild `$effect`), since this
     *  needs to update on every mousemove without the cost of a full chart rebuild.
     *  See ROW_HIGHLIGHT_SERIES_ID / renderChart() for the event wiring. */
    let hoveredRowKey: string | null = null;
    const ROW_HIGHLIGHT_SERIES_ID = 'row-highlight';

    function safeString(value: string | (string | null)[] | null | undefined): string | null {
        if (value == null) return null;
        if (typeof value === 'string') return value;
        return value[0] ?? null;
    }

    function safeNumber(value: string | (string | null)[] | null | undefined): number {
        const raw = safeString(value);
        if (raw == null) return 0;
        const parsed = Number.parseFloat(raw);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function safeInt(value: number | (number | null)[] | null | undefined): number | null {
        if (value == null) return null;
        if (typeof value === 'number') return value;
        return value[0] ?? null;
    }

    function escapeHtml(value: string): string {
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function escapeRichText(value: string): string {
        return value.replace(/[{}]/g, '');
    }

    function tr(key: string, fallback: string): string {
        const translated = $t(key);
        return !translated || translated === key ? fallback : translated;
    }

    function shortMoney(amount: number, currency: string, showSign = true): string {
        const info = getCurrencyInfo(currency);
        const symbol = info.symbol && info.symbol !== currency ? info.symbol : '';
        const abs = Math.abs(amount);
        const compact = abs >= 1000 ? new Intl.NumberFormat(undefined, {notation: 'compact', maximumFractionDigits: 1}).format(abs) : abs.toLocaleString(undefined, {minimumFractionDigits: abs % 1 === 0 ? 0 : 2, maximumFractionDigits: 2});
        const sign = showSign && amount > 0 ? '+' : amount < 0 ? '-' : '';
        return symbol ? `${sign}${symbol}${compact}` : `${sign}${compact} ${currency}`;
    }

    function axisTickAmount(amount: number): string {
        if (amount === 0) return '0';
        const abs = Math.abs(amount);
        const compact = new Intl.NumberFormat(undefined, {notation: 'compact', maximumFractionDigits: abs < 10 ? 2 : abs < 100 ? 1 : 0}).format(abs);
        return `${amount < 0 ? '-' : ''}${compact}`;
    }

    function trimLabel(value: string, max = 31): string {
        if (value.length <= max) return value;
        return `${value.slice(0, Math.max(0, max - 1)).trimEnd()}…`;
    }

    function palette(themeDark: boolean) {
        return {
            unrealized: themeDark ? '#60a5fa' : '#2563eb',
            realized: themeDark ? '#4ade80' : '#16a34a',
            income: themeDark ? '#fbbf24' : '#d97706',
            costs: themeDark ? '#f87171' : '#dc2626',
            other: themeDark ? '#a78bfa' : '#7c3aed',
            positive: themeDark ? '#4ade80' : '#16a34a',
            negative: themeDark ? '#f87171' : '#dc2626',
            neutral: themeDark ? '#cbd5e1' : '#64748b',
        };
    }

    function otherEffectColor(category: string, themeDark: boolean): string {
        const colors = palette(themeDark);
        if (category === 'Income') return colors.income;
        if (category === 'Cost') return colors.costs;
        return colors.other;
    }

    /** Backend sends the raw enum ("Income"/"Cost"/"Other") — translate it for
     *  tooltip display instead of leaking the untranslated value into the UI. */
    function categoryLabel(category: string): string {
        if (category === 'Income') return tr('dashboard.categoryIncome', category);
        if (category === 'Cost') return tr('dashboard.categoryCost', category);
        if (category === 'Other') return tr('dashboard.categoryOther', category);
        return category;
    }

    /** Backend sends fixed English description strings for "other effect" rows
     *  (never localized) — translate the known ones instead of leaking raw English
     *  into other languages. Same mapping as OtherPeriodEffectsTable.svelte. */
    function otherEffectDescriptionLabel(description: string): string {
        if (description === 'Unallocated income') return tr('dashboard.unallocatedIncome', description);
        if (description === 'Unallocated costs') return tr('dashboard.unallocatedCosts', description);
        if (description === 'Other / reconciliation residual') return tr('dashboard.otherReconciliationResidual', description);
        return description;
    }

    function netColor(amount: number, themeDark: boolean): string {
        const colors = palette(themeDark);
        if (amount > 0) return colors.positive;
        if (amount < 0) return colors.negative;
        return colors.neutral;
    }

    let labels = $derived.by(() => ({
        periodPnl: tr('dashboard.periodPnl', 'Period P&L'),
        unrealized: tr('dashboard.unrealizedDelta', 'Unrealized Δ'),
        realized: tr('dashboard.realizedSales', 'Realized Sales'),
        income: tr('dashboard.income', 'Income'),
        costs: tr('dashboard.costs', 'Costs'),
        otherPeriodEffects: tr('dashboard.otherPeriodEffects', 'Other period effects'),
        status: tr('common.status', 'Status'),
        openShort: tr('dashboard.openPositions', 'Open'),
        closedShort: tr('dashboard.closedPositions', 'Closed'),
        openLong: tr('dashboard.openAtPeriodEnd', 'Open at period end'),
        closedLong: tr('dashboard.closedByPeriodEnd', 'Closed by period end'),
        startValue: tr('dashboard.startValue', 'Start Value'),
        endValue: tr('dashboard.endValue', 'End Value'),
        broker: tr('common.broker', 'Broker'),
        category: tr('common.category', 'Category'),
        noPeriodPnl: tr('dashboard.noPeriodPnl', 'No P&L in selected period'),
    }));

    let componentDefs = $derived.by(() => [
        {key: 'unrealized' as const, label: labels.unrealized},
        {key: 'realized' as const, label: labels.realized},
        {key: 'income' as const, label: labels.income},
        {key: 'costs' as const, label: labels.costs},
    ]);

    let chartRows = $derived.by<ChartRow[]>(() => {
        const assetRows: AssetRow[] = positions.map((position, index) => {
            const feesTaxes = safeNumber(position.period_fees_taxes);
            return {
                key: `asset-${position.broker_id}-${position.asset_id}-${index}`,
                kind: 'asset',
                label: position.asset_name,
                assetId: position.asset_id,
                assetTicker: safeString(position.asset_ticker),
                brokerName: position.broker_name,
                startValue: safeNumber(position.start_value),
                endValue: safeNumber(position.end_value),
                net: safeNumber(position.period_pnl),
                isFullySold: position.is_fully_sold ?? false,
                components: {
                    unrealized: safeNumber(position.period_unrealized_delta),
                    realized: safeNumber(position.period_realized_gain_loss),
                    income: safeNumber(position.period_income),
                    costs: feesTaxes === 0 ? 0 : -Math.abs(feesTaxes),
                },
            };
        });

        const effectRows: OtherRow[] = otherEffects.map((effect, index) => ({
            key: `effect-${safeInt(effect.broker_id) ?? 'none'}-${index}`,
            kind: 'other',
            label: effect.description,
            category: effect.category,
            brokerName: safeString(effect.broker_name),
            net: safeNumber(effect.period_pnl),
        }));

        // Sort by impact (largest movers first, gain or loss) — mirrors the same
        // convention already used by the Performance table (abs(period_pnl) desc).
        assetRows.sort((a, b) => Math.abs(b.net) - Math.abs(a.net));
        effectRows.sort((a, b) => Math.abs(b.net) - Math.abs(a.net));

        if (assetRows.length > 0 && effectRows.length > 0) {
            return [
                ...assetRows,
                {
                    key: 'section-other-effects',
                    kind: 'section',
                    label: labels.otherPeriodEffects,
                    net: 0,
                },
                ...effectRows,
            ];
        }

        return [...assetRows, ...effectRows];
    });

    interface DisplaySlot {
        row: ChartRow;
        /** 'full' = desktop, label+bar on the same axis row. On mobile each
         *  chartRow becomes two consecutive axis rows: 'label' (text only,
         *  no bar) then 'bar' (bar only, no text) — giving the bar its own
         *  full-width row instead of squeezing it next to the label. */
        slot: 'full' | 'label' | 'bar';
    }

    let displayRows = $derived.by<DisplaySlot[]>(() => {
        if (!isMobile) return chartRows.map((row) => ({row, slot: 'full' as const}));
        return chartRows.flatMap((row) => [
            {row, slot: 'label' as const},
            {row, slot: 'bar' as const},
        ]);
    });

    let chartHeight = $derived(isMobile ? Math.max(260, chartRows.length * 54 + 32) : Math.max(260, chartRows.length * 40 + 32));
    let enableScroll = $derived(chartRows.length > 14);

    let axisBound = $derived.by(() => {
        let absoluteMax = 0;
        for (const row of chartRows) {
            if (row.kind === 'section') continue;
            if (row.kind === 'asset') {
                const positives = Object.values(row.components).reduce((sum, value) => (value > 0 ? sum + value : sum), 0);
                const negatives = Object.values(row.components).reduce((sum, value) => (value < 0 ? sum + Math.abs(value) : sum), 0);
                absoluteMax = Math.max(absoluteMax, positives, negatives, Math.abs(row.net));
            } else {
                absoluteMax = Math.max(absoluteMax, Math.abs(row.net));
            }
        }
        // 105% of the largest magnitude on either side — no "nice number" rounding
        // (niceAxisBound rounds up to the nearest 1/2/5×10^n, e.g. 2433 → 5000, which
        // was inflating the scale far beyond the data and made every bar look tiny).
        return Math.max(absoluteMax * 1.05, 1);
    });

    let legendItems = $derived.by(() => {
        const colors = palette(isDark);
        return componentDefs.map((component) => ({
            ...component,
            color: colors[component.key],
        }));
    });

    function syncTheme() {
        isDark = document.documentElement.classList.contains('dark');
    }

    function buildAxisRich(themeDark: boolean, desktop = false) {
        return {
            name: {
                color: themeDark ? '#e2e8f0' : '#1f2937',
                fontSize: desktop ? 14 : 11,
                fontWeight: 500,
            },
            secondary: {
                color: themeDark ? '#94a3b8' : '#64748b',
                fontSize: 10,
            },
            section: {
                color: themeDark ? '#cbd5e1' : '#475569',
                fontSize: 10,
                fontWeight: 700,
                padding: [4, 0, 0, 0],
            },
            openBadge: {
                color: '#ffffff',
                backgroundColor: themeDark ? '#166534' : '#16a34a',
                borderRadius: 999,
                padding: [2, 6],
                fontSize: 9,
                fontWeight: 700,
            },
            closedBadge: {
                color: '#ffffff',
                backgroundColor: themeDark ? '#475569' : '#64748b',
                borderRadius: 999,
                padding: [2, 6],
                fontSize: 9,
                fontWeight: 700,
            },
        };
    }

    function axisRowLabel(row: ChartRow): string {
        if (row.kind === 'section') {
            return `{section|${escapeRichText(row.label)}}`;
        }

        if (row.kind === 'asset') {
            const badgeKey = row.isFullySold ? 'closedBadge' : 'openBadge';
            const badgeText = row.isFullySold ? labels.closedShort : labels.openShort;
            return `{name|${escapeRichText(trimLabel(row.label))}} {${badgeKey}|${escapeRichText(badgeText)}}`;
        }

        return `{name|${escapeRichText(trimLabel(otherEffectDescriptionLabel(row.label)))}}`;
    }

    /** Mobile row header renders name, status badge and net P&L as three
     *  independently-positioned elements (name left, badge center-right, net
     *  value far right) instead of one inline rich-text blob — needs the name
     *  and badge split apart, unlike the combined `axisRowLabel` used by the
     *  desktop axisLabel (single narrow gutter, no room to spread them out). */
    function axisRowNameOnly(row: ChartRow): string {
        if (row.kind === 'section') return `{section|${escapeRichText(row.label)}}`;
        // Full-width label row on mobile has much more room than the desktop 220px
        // gutter (axisRowLabel below stays at the default 28 for that narrower case).
        const name = row.kind === 'other' ? otherEffectDescriptionLabel(row.label) : row.label;
        return `{name|${escapeRichText(trimLabel(name, 42))}}`;
    }

    function axisRowBadgeOnly(row: ChartRow): string | null {
        if (row.kind !== 'asset') return null;
        const badgeKey = row.isFullySold ? 'closedBadge' : 'openBadge';
        const badgeText = row.isFullySold ? labels.closedShort : labels.openShort;
        return `{${badgeKey}|${escapeRichText(badgeText)}}`;
    }

    function componentValue(row: ChartRow, componentKey: ComponentKey): number {
        return row.kind === 'asset' ? row.components[componentKey] : 0;
    }

    function buildTooltip(row: ChartRow, themeDark: boolean): string {
        const theme = buildTooltipTheme(themeDark);

        if (row.kind === 'other') {
            const pnlHtml = `<span style="color:${netColor(row.net, themeDark)}">${escapeHtml(formatCurrencyAmountPlain(row.net, displayCurrency, {showSign: true}))}</span>`;
            let html = buildTooltipHeader(escapeHtml(otherEffectDescriptionLabel(row.label)), theme.textColor);
            html += buildTooltipRow(labels.category, escapeHtml(categoryLabel(row.category)));
            html += buildTooltipRow(labels.periodPnl, pnlHtml, otherEffectColor(row.category, themeDark));
            html += buildTooltipRow(labels.broker, escapeHtml(row.brokerName ?? '—'));
            return `<div style="font-size:11px;color:${theme.textColor}">${html}</div>`;
        }

        if (row.kind === 'section') return '';

        const statusText = row.isFullySold ? labels.closedLong : labels.openLong;
        const statusBg = row.isFullySold ? (themeDark ? '#475569' : '#64748b') : themeDark ? '#166534' : '#16a34a';
        const statusHtml = `<span style="display:inline-block;padding:2px 8px;border-radius:999px;background:${statusBg};color:#fff;font-weight:700">${escapeHtml(statusText)}</span>`;
        const title = row.assetTicker ? `${row.label} (${row.assetTicker})` : row.label;
        const colors = palette(themeDark);
        const componentRows: Array<{label: string; value: number; color: string}> = [
            {label: labels.unrealized, value: row.components.unrealized, color: colors.unrealized},
            {label: labels.realized, value: row.components.realized, color: colors.realized},
            {label: labels.income, value: row.components.income, color: colors.income},
            {label: labels.costs, value: row.components.costs, color: colors.costs},
        ];

        let html = buildTooltipHeader(escapeHtml(title), theme.textColor);
        html += buildTooltipRow(labels.status, statusHtml);
        html += buildTooltipRow(labels.periodPnl, `<span style="color:${netColor(row.net, themeDark)}">${escapeHtml(formatCurrencyAmountPlain(row.net, displayCurrency, {showSign: true}))}</span>`);
        html += buildTooltipDivider(theme.border);
        for (const component of componentRows) {
            html += buildTooltipRow(component.label, escapeHtml(formatCurrencyAmountPlain(component.value, displayCurrency, {showSign: true})), component.color);
        }
        html += buildTooltipDivider(theme.border);
        html += buildTooltipRow(labels.startValue, escapeHtml(formatCurrencyAmountPlain(row.startValue, displayCurrency)));
        html += buildTooltipRow(labels.endValue, escapeHtml(formatCurrencyAmountPlain(row.endValue, displayCurrency)));
        html += buildTooltipRow(labels.broker, escapeHtml(row.brokerName || '—'));
        return `<div style="font-size:11px;color:${theme.textColor}">${html}</div>`;
    }

    /** Local variant of the shared `tooltipPositionSide` helper (echartsTooltipHelpers.ts,
     *  used by 5 other chart components — NOT modified there to avoid affecting them).
     *  Horizontal bars ⇒ tooltip is centered ABOVE the tap/click point (not offset to
     *  left/right like a side-positioned tooltip, which made sense for the OTHER charts'
     *  vertical bars/lines but not here) so the finger and the bar itself both stay clear.
     *  For rows near the top of the (possibly scrolled) visible area this can legitimately
     *  push the tooltip above the canvas/container edge entirely — acceptable per explicit
     *  request, prioritized over keeping it fully inside the chart bounds (see
     *  `confine: false` on the tooltip option below, which would otherwise clamp this
     *  back in). Horizontal position is still clamped to the viewport width so it never
     *  runs off the left/right edge. */
    function performanceTooltipPosition(point: [number, number], _params: unknown, _dom: unknown, _rect: unknown, size: {contentSize: [number, number]; viewSize: [number, number]}): [number, number] {
        const tooltipW = size.contentSize[0];
        const tooltipH = size.contentSize[1];
        const viewW = size.viewSize[0];

        let x = point[0] - tooltipW / 2;
        if (x < 8) x = 8;
        if (x + tooltipW > viewW - 8) x = viewW - tooltipW - 8;

        // Always above the tap/click point — clears both the finger and the bar
        // itself so nothing underneath stays hidden. For rows near the top of the
        // (possibly scrolled) visible area this can legitimately push the tooltip
        // above the canvas/container edge entirely — acceptable per explicit
        // request, prioritized over keeping it fully inside the chart bounds
        // (see `confine: false` on the tooltip option below, which would otherwise
        // clamp this back in).
        const gapAboveBar = 16;
        let y = point[1] - tooltipH - gapAboveBar;

        // Only clamp the BOTTOM edge — never pushed back down below the tap point —
        // so it doesn't fall past the visible scrolled window on a tall chart.
        if (scrollWrapper && enableScroll) {
            const visibleBottom = scrollWrapper.scrollTop + scrollWrapper.clientHeight;
            if (y + tooltipH > visibleBottom - 8) y = visibleBottom - tooltipH - 8;
        }

        return [x, y];
    }

    function buildSeries(themeDark: boolean): echarts.SeriesOption[] {
        const colors = palette(themeDark);

        // Mobile only: label slot and bar slot are 2 separate y-axis categories, so
        // ECharts' built-in axisPointer shadow (which highlights one category band at
        // a time) shows two thin, independent strips instead of one shared row
        // highlight when hovering either. This custom series draws ONE rect spanning
        // BOTH slots that share `hoveredRowKey` (see renderChart() for the hover
        // detection wiring via 'updateAxisPointer'/'globalout' events + a targeted
        // partial setOption — NOT the full reactive rebuild, for mousemove performance).
        const rowHighlightSeries: any = {
            id: ROW_HIGHLIGHT_SERIES_ID,
            name: 'row-highlight',
            type: 'custom',
            silent: true,
            clip: false,
            tooltip: {show: false},
            z: 1,
            data: hoveredRowKey ? [[displayRows.findIndex((e) => e.row.key === hoveredRowKey), 0]] : [],
            encode: {y: 0, x: 1},
            renderItem: (params: any, api: any) => {
                if (!hoveredRowKey) return null;
                const indices: number[] = [];
                displayRows.forEach((entry, idx) => {
                    if (entry.row.key === hoveredRowKey) indices.push(idx);
                });
                if (indices.length === 0) return null;
                const minIdx = Math.min(...indices);
                const maxIdx = Math.max(...indices);
                const [, yTop] = api.coord([0, minIdx]);
                const [, yBottom] = api.coord([0, maxIdx]);
                const bandSize = (api.size?.([0, 0]) as number[] | undefined)?.[1] ?? 24;
                const coordSys = params.coordSys as {x: number; width: number};
                return {
                    type: 'rect',
                    silent: true,
                    shape: {
                        x: coordSys.x,
                        y: yTop - bandSize / 2,
                        width: coordSys.width,
                        height: yBottom - yTop + bandSize,
                    },
                    style: {
                        fill: themeDark ? 'rgba(148, 163, 184, 0.14)' : 'rgba(148, 163, 184, 0.16)',
                    },
                };
            },
        };

        // Rounded corners must only appear on the outermost segment of each stack side
        // (the one farthest from zero) — applying a static borderRadius to every series
        // rounds EVERY segment's corners uniformly, which looks broken at the internal
        // joints between stacked components. ECharts series-level itemStyle.borderRadius
        // can't be a per-datapoint callback, so instead each data point carries its own
        // itemStyle override (data items support per-item style in ECharts bar series).
        function lastPositiveKey(row: ChartRow): ComponentKey | null {
            if (row.kind !== 'asset') return null;
            let last: ComponentKey | null = null;
            for (const component of componentDefs) {
                if (row.components[component.key] > 0) last = component.key;
            }
            return last;
        }
        function lastNegativeKey(row: ChartRow): ComponentKey | null {
            if (row.kind !== 'asset') return null;
            let last: ComponentKey | null = null;
            for (const component of componentDefs) {
                if (row.components[component.key] < 0) last = component.key;
            }
            return last;
        }

        const assetSeries = componentDefs.flatMap((component, index) => {
            const positiveSeries: echarts.BarSeriesOption = {
                name: `asset-${component.key}-positive`,
                type: 'bar',
                stack: 'positive',
                // Without this, ECharts treats the 'positive' and 'negative' stack
                // groups as two separate side-by-side bar groups (its default
                // "grouped bar" behavior for series not sharing one stack) — visually
                // offsetting the positive and negative halves of the SAME row onto
                // two different lines instead of one shared centerline. -100% forces
                // full overlap so both halves render on the exact same row.
                barGap: '-100%',
                barMaxWidth: 18,
                emphasis: {focus: 'series'},
                data: displayRows.map(({row, slot}) => {
                    const value = slot === 'label' ? 0 : componentValue(row, component.key);
                    const isOutermost = lastPositiveKey(row) === component.key;
                    return {
                        value: value > 0 ? value : 0,
                        itemStyle: {
                            color: colors[component.key],
                            borderRadius: isOutermost ? [0, 4, 4, 0] : 0,
                        },
                    };
                }),
                itemStyle: {color: colors[component.key]},
            };

            if (index === 0) {
                positiveSeries.markLine = {
                    silent: true,
                    symbol: 'none',
                    label: {show: false},
                    lineStyle: {
                        color: themeDark ? '#94a3b8' : '#64748b',
                        width: 1,
                        opacity: 0.75,
                    },
                    data: [{xAxis: 0}],
                };
            }

            const negativeSeries: echarts.BarSeriesOption = {
                name: `asset-${component.key}-negative`,
                type: 'bar',
                stack: 'negative',
                barGap: '-100%',
                barMaxWidth: 18,
                emphasis: {focus: 'series'},
                data: displayRows.map(({row, slot}) => {
                    const value = slot === 'label' ? 0 : componentValue(row, component.key);
                    const isOutermost = lastNegativeKey(row) === component.key;
                    return {
                        value: value < 0 ? value : 0,
                        itemStyle: {
                            color: colors[component.key],
                            borderRadius: isOutermost ? [4, 0, 0, 4] : 0,
                        },
                    };
                }),
                itemStyle: {color: colors[component.key]},
            };

            return [positiveSeries, negativeSeries];
        });

        const otherPositiveSeries: echarts.BarSeriesOption = {
            name: 'other-effects-positive',
            type: 'bar',
            stack: 'positive',
            barGap: '-100%',
            barMaxWidth: 18,
            emphasis: {focus: 'series'},
            data: displayRows.map(({row, slot}) => (slot !== 'label' && row.kind === 'other' && row.net > 0 ? row.net : 0)),
            itemStyle: {
                color: (params: any) => {
                    const row = displayRows[params.dataIndex]?.row;
                    return row?.kind === 'other' ? otherEffectColor(row.category, themeDark) : colors.other;
                },
                borderRadius: [0, 4, 4, 0],
            },
        };

        const otherNegativeSeries: echarts.BarSeriesOption = {
            name: 'other-effects-negative',
            type: 'bar',
            stack: 'negative',
            barGap: '-100%',
            barMaxWidth: 18,
            emphasis: {focus: 'series'},
            data: displayRows.map(({row, slot}) => (slot !== 'label' && row.kind === 'other' && row.net < 0 ? row.net : 0)),
            itemStyle: {
                color: (params: any) => {
                    const row = displayRows[params.dataIndex]?.row;
                    return row?.kind === 'other' ? otherEffectColor(row.category, themeDark) : colors.other;
                },
                borderRadius: [4, 0, 0, 4],
            },
        };

        const sectionDividerSeries: any = {
            name: 'section-divider',
            type: 'custom',
            silent: true,
            clip: false,
            tooltip: {show: false},
            z: 15,
            data: displayRows.map((_entry, rowIndex) => [rowIndex, 0]),
            encode: {y: 0, x: 1},
            renderItem: (params: any, api: any) => {
                const rowIndex = Number(api.value(0));
                const entry = displayRows[rowIndex];
                if (!entry || entry.row.kind !== 'section' || entry.slot === 'bar') return null;
                const [, y] = api.coord([0, rowIndex]);
                const coordSys = params.coordSys as {x: number; width: number};
                return {
                    type: 'line',
                    silent: true,
                    shape: {
                        x1: coordSys.x,
                        y1: y,
                        x2: coordSys.x + coordSys.width,
                        y2: y,
                    },
                    style: {
                        stroke: themeDark ? '#475569' : '#cbd5e1',
                        lineWidth: 1,
                    },
                };
            },
        };

        const netLabelSeries: any = {
            name: 'net-labels',
            type: 'custom',
            silent: true,
            clip: false,
            tooltip: {show: false},
            z: 20,
            data: displayRows.map((_entry, rowIndex) => [rowIndex, 0]),
            encode: {y: 0, x: 1},
            renderItem: (params: any, api: any) => {
                const rowIndex = Number(api.value(0));
                const entry = displayRows[rowIndex];
                // Desktop only ('full' slot) — on mobile the net value moves onto the
                // label row via mobileRowTextSeries below (bar row has no room for it).
                if (!entry || entry.row.kind === 'section' || entry.slot !== 'full') return null;
                const [, y] = api.coord([0, rowIndex]);
                const coordSys = params.coordSys as {x: number; width: number};
                return {
                    type: 'text',
                    x: coordSys.x + coordSys.width + 8,
                    y,
                    silent: true,
                    style: {
                        text: shortMoney(entry.row.net, displayCurrency, true),
                        fill: netColor(entry.row.net, themeDark),
                        fontSize: 14,
                        fontWeight: 700,
                        textAlign: 'left',
                        textVerticalAlign: 'middle',
                    },
                };
            },
        };

        // Mobile row header: since the label row has no bar, `grid.left` shrinks to
        // almost nothing (the bar row below needs the full width) — too narrow for
        // `yAxis.axisLabel` (a chart-wide, single-width gutter) to fit the asset
        // name/status badge. So on mobile the label row's entire text (name, status
        // badge, net P&L) is drawn here as a full-width custom series instead —
        // `yAxis.axisLabel` is hidden entirely on mobile (see buildOption below).
        const mobileRowTextSeries: any = {
            name: 'mobile-row-text',
            type: 'custom',
            silent: true,
            clip: false,
            tooltip: {show: false},
            z: 25,
            data: displayRows.map((_entry, rowIndex) => [rowIndex, 0]),
            encode: {y: 0, x: 1},
            renderItem: (params: any, api: any) => {
                if (!isMobile) return null;
                const rowIndex = Number(api.value(0));
                const entry = displayRows[rowIndex];
                if (!entry || entry.slot !== 'label') return null;
                const [, y] = api.coord([0, rowIndex]);
                const coordSys = params.coordSys as {x: number; width: number};
                const rich = buildAxisRich(themeDark);

                if (entry.row.kind === 'section') {
                    return {
                        type: 'text',
                        x: coordSys.x,
                        y,
                        silent: true,
                        style: {text: axisRowNameOnly(entry.row), rich, textAlign: 'left', textVerticalAlign: 'middle'},
                    };
                }

                const badge = axisRowBadgeOnly(entry.row);
                const children: any[] = [
                    {
                        type: 'text',
                        x: coordSys.x,
                        y,
                        silent: true,
                        style: {text: axisRowNameOnly(entry.row), rich, textAlign: 'left', textVerticalAlign: 'middle'},
                    },
                    {
                        type: 'text',
                        x: coordSys.x + coordSys.width,
                        y,
                        silent: true,
                        style: {
                            text: shortMoney(entry.row.net, displayCurrency, true),
                            fill: netColor(entry.row.net, themeDark),
                            fontSize: 11,
                            fontWeight: 700,
                            textAlign: 'right',
                            textVerticalAlign: 'middle',
                        },
                    },
                ];
                if (badge) {
                    // Center-right: not glued to the name (which can now be as long as
                    // ~60% of the full row width) nor overlapping the net value at the
                    // far right — a fixed anchor independent of the name's own length.
                    children.push({
                        type: 'text',
                        x: coordSys.x + coordSys.width * 0.72,
                        y,
                        silent: true,
                        style: {text: badge, rich, textAlign: 'left', textVerticalAlign: 'middle'},
                    });
                }

                return {type: 'group', children};
            },
        };

        return [rowHighlightSeries, ...assetSeries, otherPositiveSeries, otherNegativeSeries, sectionDividerSeries, netLabelSeries, mobileRowTextSeries];
    }

    function buildOption(themeDark: boolean): echarts.EChartsOption {
        const theme = buildTooltipTheme(themeDark);
        const gridColors = buildGridColors(themeDark);

        return {
            animationDuration: 250,
            grid: isMobile
                ? {
                      left: 4,
                      right: 4,
                      top: 12,
                      bottom: 24,
                  }
                : {
                      left: 260,
                      right: 90,
                      top: 12,
                      bottom: 24,
                  },
            legend: {show: false},
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    // Mobile: the native per-category shadow would show two separate
                    // thin strips (label slot + bar slot are different categories) —
                    // suppressed in favor of the unified rowHighlightSeries custom rect
                    // (see buildSeries()) spanning both. Desktop has one slot per row,
                    // so the native shadow already covers the whole row correctly.
                    type: isMobile ? 'none' : 'shadow',
                    shadowStyle: {
                        color: themeDark ? 'rgba(148, 163, 184, 0.12)' : 'rgba(148, 163, 184, 0.14)',
                    },
                },
                position: performanceTooltipPosition,
                // Deliberately NOT confined to the chart container — the tooltip must be
                // able to sit above the tap point (and thus above the canvas edge for
                // rows near the top) per explicit request; `confine: true` would clamp
                // it back inside and defeat that.
                confine: false,
                // Without `appendTo`, ECharts appends the tooltip DOM node INSIDE the
                // chart's own container (api.getDom()) — which sits inside `scrollWrapper`
                // (`overflow-y-auto` when `enableScroll`) and, further up, the dashboard
                // card. Either ancestor would clip the tooltip whenever it's positioned
                // outside their bounds, silently defeating `confine: false` above (looks
                // like a stacking/z-index bug from the outside, but it's actual clipping).
                // Appending to `document.body` escapes both — ECharts still translates the
                // chart-local coordinates our position function returns into body's
                // coordinate space automatically (see TooltipHTMLContent's makeStyleCoord).
                appendTo: () => document.body,
                backgroundColor: theme.bg,
                borderColor: theme.border,
                textStyle: {color: theme.textColor},
                formatter: (params: any) => {
                    const list = Array.isArray(params) ? params : [params];
                    const match = list.find((item) => item?.dataIndex != null);
                    const row = match ? displayRows[match.dataIndex]?.row : null;
                    return row ? buildTooltip(row, themeDark) : '';
                },
            },
            xAxis: {
                type: 'value',
                min: -axisBound,
                max: axisBound,
                splitNumber: 4,
                axisLine: {show: false},
                axisTick: {show: false},
                splitLine: {
                    show: true,
                    lineStyle: {
                        color: gridColors.gridColor,
                    },
                },
                axisLabel: {
                    color: gridColors.textColor,
                    formatter: (value: number) => axisTickAmount(Number(value)),
                },
            },
            yAxis: {
                type: 'category',
                inverse: true,
                data: displayRows.map((_entry, rowIndex) => rowIndex),
                axisLine: {show: false},
                axisTick: {show: false},
                splitLine: {show: false},
                axisLabel: {
                    show: !isMobile,
                    width: isMobile ? undefined : 235,
                    margin: 12,
                    color: gridColors.textColor,
                    formatter: (value: string | number) => {
                        if (isMobile) return '';
                        const entry = displayRows[Number(value)];
                        return entry ? axisRowLabel(entry.row) : '';
                    },
                    rich: buildAxisRich(themeDark, true),
                },
            },
            series: buildSeries(themeDark),
        };
    }

    function rowFromChartEvent(params: any): ChartRow | null {
        const dataIndex = params?.dataIndex;
        if (typeof dataIndex !== 'number') return null;
        return displayRows[dataIndex]?.row ?? null;
    }

    function handleChartContextMenu(params: any) {
        const row = rowFromChartEvent(params);
        if (row?.kind === 'asset') {
            const nativeEvent = params?.event?.event as MouseEvent | PointerEvent | undefined;
            nativeEvent?.preventDefault();
            if (nativeEvent?.clientX == null || nativeEvent?.clientY == null) return;
            contextMenu = {x: nativeEvent.clientX, y: nativeEvent.clientY, assetId: row.assetId};
        }
    }

    function setupResizeObserver() {
        if (!chartContainer) return;
        if (resizeObserver) return;
        resizeObserver = new ResizeObserver(() => chartInstance?.resize());
        resizeObserver.observe(chartContainer);
    }

    function renderChart() {
        if (!chartContainer || chartRows.length === 0) return;

        syncTheme();

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            tooltipCleanup?.();
            resizeObserver?.disconnect();
            resizeObserver = null;
            chartInstance.dispose();
            chartInstance = undefined;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            needsInitialLayoutStabilityPass = true;
            setupResizeObserver();
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
            setupRowHighlightEvents(chartInstance);
            chartInstance.on('contextmenu', handleChartContextMenu);
        }

        chartInstance.setOption(buildOption(isDark), true);
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer);
        }
    }

    /** Mobile row-highlight hover wiring (see rowHighlightSeries in buildSeries()).
     *  Uses 'updateAxisPointer' (fires for the hovered category even over "empty"
     *  rows with no bar to hit-test against, e.g. the label slot) + 'globalout' to
     *  clear on mouse leave. Pushes a targeted partial setOption — NOT a full
     *  rebuild — to stay cheap on every mousemove. Listeners are attached once (chart
     *  instance persists across data/option rebuilds), so they never accumulate. */
    function setupRowHighlightEvents(instance: echarts.ECharts) {
        instance.on('updateAxisPointer', (event: any) => {
            if (!isMobile) return;
            const axisInfo = event?.axesInfo?.find((info: any) => info.axisDim === 'y');
            const value = axisInfo?.value;
            const entry = value != null ? displayRows[Number(value)] : undefined;
            const nextKey = entry ? entry.row.key : null;
            if (nextKey === hoveredRowKey) return;
            hoveredRowKey = nextKey;
            const indices: number[] = [];
            if (nextKey) displayRows.forEach((e, idx) => e.row.key === nextKey && indices.push(idx));
            instance.setOption({series: [{id: ROW_HIGHLIGHT_SERIES_ID, data: indices.length ? [[indices[0], 0]] : []}]});
        });
        instance.on('globalout', () => {
            if (!hoveredRowKey) return;
            hoveredRowKey = null;
            instance.setOption({series: [{id: ROW_HIGHLIGHT_SERIES_ID, data: []}]});
        });
    }

    onMount(() => {
        syncTheme();
        darkModeObserver = new MutationObserver(() => {
            syncTheme();
            renderChart();
        });
        darkModeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});

        return () => {
            tooltipCleanup?.();
            darkModeObserver?.disconnect();
            resizeObserver?.disconnect();
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        void positions;
        void otherEffects;
        void displayCurrency;
        void chartRows;
        void displayRows;
        void isMobile;
        void axisBound;
        void labels;
        void $currentLanguage;

        if (!chartContainer) return;

        tick().then(() => {
            renderChart();
        });
    });
</script>

<div class="space-y-3" data-testid="performance-chart">
    {#if chartRows.length === 0}
        <p class="py-6 text-center text-sm text-gray-400 dark:text-gray-500">
            {labels.noPeriodPnl}
        </p>
    {:else}
        <div class="flex flex-wrap gap-x-4 gap-y-2 text-[11px] text-gray-500 dark:text-gray-400">
            {#each legendItems as item (item.key)}
                <div class="flex items-center gap-1.5">
                    <span class="h-2.5 w-2.5 rounded-sm" style="background-color:{item.color}"></span>
                    <span>{item.label}</span>
                </div>
            {/each}
        </div>

        <div class:overflow-y-auto={enableScroll} style:max-height={enableScroll ? '70dvh' : undefined} bind:this={scrollWrapper}>
            <div bind:this={chartContainer} style="width:100%;height:{chartHeight}px"></div>
        </div>
    {/if}

    {#if contextMenu}
        <ContextMenu
            x={contextMenu.x}
            y={contextMenu.y}
            items={[
                {id: 'view-asset', label: $t('brokers.lots.viewAsset') || 'View Asset', icon: ExternalLink as unknown as ContextMenuItem['icon']},
                {id: 'analyze-lots', label: $t('brokers.lots.analyze') || 'Analyze Lots', icon: Layers as unknown as ContextMenuItem['icon']},
            ] satisfies ContextMenuItem[]}
            onAction={(id) => {
                if (!contextMenu) return;
                if (id === 'view-asset') void goto(`/assets/${contextMenu.assetId}`);
                else if (id === 'analyze-lots') onAnalyze?.(contextMenu.assetId);
                contextMenu = null;
            }}
            onClose={() => (contextMenu = null)}
        />
    {/if}
</div>
