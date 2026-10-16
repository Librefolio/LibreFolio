/**
 * Colours of the ECharts charts, by meaning — the one home for them.
 *
 * ECharts draws from an options object built in TypeScript, so every chart colour is a value picked for the active
 * theme. Each chart used to write its own pairs inline; they now live here with the values they had, so moving them
 * changed no pixel.
 *
 * **Divergences stay, with a name.** Where two charts draw the same thing in two colours, both values are kept side by
 * side — the emerald of the tooltip Δ and the green of the lines, the red of the price charts and the portfolio's — so
 * the designer can see them and decide. A value with two meanings gets two names. Nothing here was unified.
 *
 * A `{light, dark}` pair is read with `themed(pair, dark)` (`./themePair`); a plain string is the same colour in both
 * themes.
 *
 * **The neutrals are roles (B4, DV, 16/10/2026).** Axes, grids, labels, tooltip boxes and pointers left these tables for
 * {@link chartNeutrals}, which reads the roles of tokens.css at each draw: there, two names of one meaning may now read
 * one role (the shared tooltip box and the candlestick's own). The tables keep the series, the categories, the states
 * and the signs, with their legacy values, for the designer.
 *
 * @module lib/theme/chartTheme
 */

import {toRgba} from './colorAlpha';
import {chartRoles} from './roleColors';

/** The price family: line chart, full price chart, candlestick chart, and the compact chart of the cards. */
export const PRICE_SERIES = {
    /** The price line when it is not coloured against the baseline. */
    line: {light: '#1a4031', dark: '#4ade80'},
    /** Points with unsaved edits, the same in both themes. */
    pendingEditPoint: '#f59e0b',
    /** Event markers of a comparison overlay that carries no colour of its own, the same in both themes. */
    comparisonMarkerFallback: '#6b7280',
} as const;

/** Gain and loss in the charts. */
export const CHART_GAIN_LOSS = {
    /** The price charts, above and below the baseline: the price line, candles and their volume, indicator histograms. */
    price: {
        gain: {light: '#16a34a', dark: '#4ade80'},
        loss: {light: '#ef4444', dark: '#f87171'},
    },
    /** The portfolio charts: Growth and Performance, the treemap, the lot charts. A darker red than the price charts'. */
    portfolio: {
        gain: {light: '#16a34a', dark: '#4ade80'},
        loss: {light: '#dc2626', dark: '#f87171'},
    },
    /** The "(Δ …)" suffix of the price tooltips: an emerald and a red, the same in both themes. */
    tooltipDelta: {
        gain: '#10b981',
        loss: '#ef4444',
    },
} as const;

/**
 * The neutrals of the charts, on the roles of tokens.css (B4, DV, 16/10/2026): axes, grid lines and rules, labels,
 * tooltip boxes, axis pointers, and the gaps and rings drawn in the card's colour — the roles the interface gives the
 * same things. Read through `chartRoles` on the chart's own element, `scope` (`<html>` when there is none), so a theme
 * switch or a Designer Lab edit shows at the next draw: take them once per draw. The groups keep the names of the
 * tables they left.
 *
 * - **Text,** by its legacy shade, as the interface's classes were migrated: `primary`, `secondary`, `muted`.
 * - **A tooltip box is a popover:** the card, the raised border (N3), the primary and the muted text. The stale-data
 *   warning in it is the warning state, the one state among the neutrals: its amber was 2.1:1 on the light card.
 * - **A line** takes the role nearest to the contrast it had: the structure (axes, grids, separators, frames)
 *   `subtle`; reference lines, pointers and leader lines `input`.
 * - **Gaps and rings in the card's colour,** `card`; halos and label backgrounds, the card at the alpha they had; the
 *   hover band and the pointer's shadow, the muted text at the alpha they had (ECharts draws the pointer over the bars).
 *
 * The mapping is the nearest role, «da rivedere» with the designer (D-T27): DV's plan, section «B4».
 */
export function chartNeutrals(dark: boolean, scope?: Element | null) {
    const roles = chartRoles(dark, scope);
    const primary = roles.color('--lf-text-primary');
    const secondary = roles.color('--lf-text-secondary');
    const muted = roles.color('--lf-text-muted');
    const subtle = roles.color('--lf-border-subtle');
    const raised = roles.color('--lf-border-raised');
    const input = roles.color('--lf-border-input');
    const card = roles.color('--lf-surface-card');
    /** A value that was translucent, at the alpha it had in each theme. */
    const translucent = (color: string, light: number, darkAlpha: number = light) => toRgba(color, dark ? darkAlpha : light);
    return {
        /** Axes of the price charts (`getChartColors`, and the line, full price and candlestick charts). */
        priceAxis: {line: subtle, label: muted, gridLine: subtle},
        /** Axis and legend text, and split lines, of the dashboard charts (`buildGridColors`, allocation, maps). */
        dashboard: {text: muted, gridLine: subtle},
        /** The greyed arrow of a paged legend that cannot go further: the muted text, dimmed as a disabled control is. */
        legendPageIconInactive: translucent(muted, 0.4),
        /** A secondary axis with no signal colour to borrow. */
        secondaryAxisFallback: muted,
        /** Labels of an indicator's dashed reference levels (RSI 30 and 70, for instance). */
        referenceLevelLabel: muted,
        /** The pointer where a chart named none and ECharts drew its own: its line, and its shadow over the bars. */
        axisPointer: {line: input, shadow: translucent(muted, 0.2)},
        /** Tooltip boxes and the text inside them. */
        tooltip: {
            /** The shared box (`buildTooltipTheme`, the line and full price charts), and where ECharts drew its own. */
            box: {background: card, border: raised, text: primary, muted},
            /** The candlestick chart's box: the same roles under its own names, and its crosshair. */
            candlestickBox: {border: raised, text: primary, heading: primary, muted, crosshair: input},
            /** Asides of the price tooltips — axis notes, the day a value is from, band bounds. */
            aside: muted,
            /** The stale-data warning line. */
            staleWarning: roles.color('--lf-warning'),
        },
        /** The price charts: the dashed line that baseline colouring compares against, the ring around unsaved-edit points. */
        price: {baseline: input, pendingEditPointRing: card},
        /** The risk-return scatter chart: its axes and the capital market line. Its points: `RISK_RETURN_COLORS`. */
        riskReturn: {axis: subtle, axisText: secondary, capitalMarketLine: input},
        /** The allocation charts: the gap between slices and rings, the captions outside the outer ring, the labels on the history's areas and their halo. */
        allocation: {sliceBorder: card, caption: secondary, historyAreaLabel: primary, historyAreaLabelShadow: card},
        /**
         * The ownership semi-donut. Its owners take the first asset types in order (`CATEGORY_SEQUENCE` in
         * `./chartCategories`); the initial on an avatar takes the text that reads best on its disc (`readableText`).
         * The slice of what is still available is a track.
         */
        semiDonut: {label: primary, labelShadow: translucent(card, 0.8, 0.6), labelLine: input, avatarBorder: card, sliceGap: card, available: roles.color('--lf-surface-neutral')},
        /** World maps: the borders between countries, the labels and their background. The land and the highlight: `GEO_MAP_COLORS`. */
        geoMap: {border: card, label: primary, labelBackground: translucent(card, 0.72, 0.55)},
        /**
         * The correlation heatmap and its tooltip. Its scale is three roles, danger, panel and info (GR5.3, read in
         * `CorrelationHeatmap.svelte` through `./roleColors`); the value in a cell takes the text that reads best on it.
         * The hovered cell: a border in the opposite shade of the theme, a halo in the card's.
         */
        correlation: {
            cellGap: card,
            emphasisBorder: primary,
            emphasisHalo: translucent(card, 0.95),
            axisLabel: secondary,
            /** Exposure badges in the tooltip, and the rule above them. */
            tooltipBadge: {background: roles.color('--lf-surface-panel'), text: secondary},
            tooltipDivider: subtle,
        },
        /**
         * The Growth chart's strokes other than its series: the dashed zero line of the P&L mode, and the separators
         * between ladder buckets, stronger than the grid lines. Its broker lines: `growthBrokerColor` in `./chartPalettes`.
         */
        growth: {pnlReference: input, bucketSeparator: input},
        /**
         * The Performance chart: the value of a row that is exactly zero; the rows of the y axis (asset name, its second
         * line, section headings); the zero line of the first series; the rule under a section heading; the band behind
         * the hovered row (mobile) and the axis shadow (desktop).
         */
        performance: {
            zeroValue: primary,
            axisName: primary,
            axisSecondary: muted,
            axisSection: secondary,
            zeroLine: muted,
            sectionSeparator: subtle,
            rowHighlight: translucent(muted, 0.16, 0.14),
            axisPointerShadow: translucent(muted, 0.14, 0.12),
        },
        /** The exposure treemap: the header of a group (a broker) and its background, the borders of groups and tiles. */
        treemap: {groupLabel: secondary, groupLabelBackground: translucent(card, 0.8), groupBorder: subtle, tileBorder: subtle},
        /** The lot charts. */
        lots: {
            /** The ring that lifts a marker off what lies under it, and the same ring on a hovered marker. */
            markerRing: card,
            markerEmphasisRing: primary,
            /** The Gantt: the border of a selected segment, the elbow to the lot it came from, the label on a segment, the text of a selected state button. */
            gantt: {selectedSegmentBorder: primary, lineageConnector: translucent(primary, 0.45, 0.48), segmentLabel: primary, stateChipText: roles.color('--lf-on-status')},
            /** The zero line of the WAC chart's P&L axis. */
            wacZeroLine: input,
        },
    };
}

/** What the tooltips draw that is not a neutral. Their boxes and text: `chartNeutrals().tooltip`. */
export const CHART_TOOLTIP_COLORS = {
    candlestickBox: {
        /** An overlay series that reports no colour, the same in both themes. */
        seriesFallback: '#888',
    },
} as const;

/** The risk-return scatter chart: its points. Its axes and the capital market line: `chartNeutrals().riskReturn`. */
export const RISK_RETURN_COLORS = {
    portfolio: {light: '#0284c7', dark: '#38bdf8'},
    benchmark: {light: '#d97706', dark: '#fbbf24'},
    /** Every other asset. */
    other: {light: '#64748b', dark: '#94a3b8'},
    /** The selected point: the hue of a selected table row, apart from every role colour. */
    selected: {light: '#22c55e', dark: '#4ade80'},
} as const;

/** The allocation charts: pie and donut, allocation history. Their category colours: `./chartCategories`; their neutrals: `chartNeutrals().allocation`. */
export const ALLOCATION_CHART_COLORS = {
    /** The bubble behind a family's icon on its slice, the same in both themes. */
    iconBubble: 'rgba(255, 255, 255, 0.75)',
} as const;

/** World maps: the portfolio's geography and the PAC planner's exposure maps. Their scale: `GEO_CHOROPLETH_SCALE`. */
export const GEO_MAP_COLORS = {
    /**
     * Countries with no weight: the zero of the scale, so not a role (B4) — on `--lf-surface-neutral` it would sit at
     * ΔE00 4.1 (light) and 3.7 (dark) from the scale's first step. For the designer, with the scale (GR5.1).
     */
    land: {light: '#e2e8f0', dark: '#334155'},
    /** A hovered or selected country. */
    highlight: {light: '#f59e0b', dark: '#fbbf24'},
} as const;

/** Chart signals, the same in both themes. Default line colours: `SIGNAL_DEFAULT_PALETTE` in `./chartPalettes`. */
export const SIGNAL_COLORS = {
    /** Parts of backend indicators by role (MACD, Bollinger bands…); the `primary` part keeps the user's colour. */
    roles: {secondary: '#f59e0b', positive: '#16a34a', negative: '#dc2626', neutral: '#64748b', accent: '#8b5cf6'},
    /** The legend's preview of a sign-coloured histogram, before the user customises it. */
    legendBarPreview: {up: '#16a34a', down: '#dc2626'},
    /** The measure tool's line. */
    measure: '#f97316',
} as const;

/** Income events, shared by the Growth chart's income bars and the lot comparison chart. */
export const INCOME_EVENT_COLORS = {
    /** Dividends: a gold kept apart from the deposit teal and the reinvested emerald, at 3:1 on the card (Tailwind's #ca8a04 was 2.94:1). */
    dividend: {light: '#b08d00', dark: '#facc15'},
    /** Interest in the lot comparison chart: a darker violet in the light theme than the Growth chart's (`GROWTH_SERIES.interest`). */
    lotInterest: {light: '#6d28d9', dark: '#a78bfa'},
} as const;

/** The Growth chart's series, read as `cc(key)` in `GrowthChart.svelte`. */
export const GROWTH_SERIES = {
    /** NAV — the prominent line. */
    nav: {light: '#1a4031', dark: '#4ade80'},
    /** Assets at cost — blue area. */
    bookAssetLike: {light: '#3b82f6', dark: '#60a5fa'},
    /** Capital cash — subdued green area. */
    cashContributed: {light: '#9caf9c', dark: '#6b8e6b'},
    /** Returns cash — bright emerald area. */
    cashGenerated: {light: '#10b981', dark: '#34d399'},
    /** Capital baseline — grey dashed. */
    capitalBaseline: {light: '#6b7280', dark: '#9ca3af'},
    /** TWRR (% mode). */
    invested: {light: '#2563eb', dark: '#60a5fa'},
    /** ROI (% mode). */
    pctCash: {light: '#9caf9c', dark: '#94a3b8'},
    /** P&L mode — the total line, as prominent as NAV. */
    totalPnl: {light: '#1a4031', dark: '#4ade80'},
    /** P&L income submode — dividend stacked bar: the same gold as the lot comparison chart's dividends. */
    dividend: INCOME_EVENT_COLORS.dividend,
    /** P&L income submode — interest stacked bar. */
    interest: {light: '#7c3aed', dark: '#a78bfa'},
    /** P&L income submode — costs (fees and taxes): orange here, red in the Performance chart. */
    costs: {light: '#ea580c', dark: '#fb923c'},
    /** P&L income submode — deposit-size bar. */
    deposit: {light: '#0d9488', dark: '#2dd4bf'},
} as const;

/** The Performance chart's series and badges (`palette()` in `PerformanceChart.svelte`). Its rows and rules: `chartNeutrals().performance`. */
export const PERFORMANCE_COLORS = {
    unrealized: {light: '#2563eb', dark: '#60a5fa'},
    /** Realized P&L: the gain green, under its own name. */
    realized: {light: '#16a34a', dark: '#4ade80'},
    income: {light: '#d97706', dark: '#fbbf24'},
    /** Costs: red here, orange in the Growth chart. */
    costs: {light: '#dc2626', dark: '#f87171'},
    other: {light: '#7c3aed', dark: '#a78bfa'},
    neutral: {light: '#64748b', dark: '#cbd5e1'},
    /** Badges of an open or a fully sold position, on the axis and in the tooltip, and their text in both themes. */
    openBadge: {light: '#16a34a', dark: '#166534'},
    closedBadge: {light: '#64748b', dark: '#475569'},
    badgeText: '#ffffff',
} as const;

/** The exposure treemap. Tiles with a P&L take `treemapPnlColor` (`./chartColorScales`); its headers and borders: `chartNeutrals().treemap`. */
export const TREEMAP_COLORS = {
    /** A tile with no P&L, the same in both themes. */
    noPnl: '#6b7280',
    /** The name on a tile, and its shadow, the same in both themes. */
    tileLabel: '#fff',
    tileLabelShadow: 'rgba(0,0,0,0.5)',
} as const;

/** Lines the risk panels add to a price chart, the same in both themes. */
export const RISK_OVERLAY_COLORS = {
    /** The comparison asset's cumulative return. */
    comparisonAsset: '#f59e0b',
    /** The median of the simulated band. */
    simulation: '#2563eb',
} as const;

/** The state of a lot: fill of its markers and of the Gantt filter buttons. */
export const LOT_STATE_COLORS = {
    open: {light: '#0284c7', dark: '#38bdf8'},
    partial: {light: '#d97706', dark: '#fbbf24'},
    closed: {light: '#64748b', dark: '#94a3b8'},
} as const;

/** The lots Gantt chart. Broker segments take the broker's colour (`getBrokerColor`); its neutrals: `chartNeutrals().lots`. */
export const LOT_GANTT_COLORS = {
    /** A segment in transit between two brokers. */
    inTransit: {light: '#7c3aed', dark: '#c084fc'},
    /** A segment with no broker. */
    noBroker: {light: '#2563eb', dark: '#60a5fa'},
    /** The tooltip's estimated current value, and its costs. */
    estimatedValue: {light: '#d97706', dark: '#fbbf24'},
    cost: {light: '#dc2626', dark: '#f87171'},
    /** The band behind the selected lot, and the pulsing one after a jump to it. */
    highlightBand: {
        fill: {light: 'rgba(59, 130, 246, 0.08)', dark: 'rgba(96, 165, 250, 0.10)'},
        stroke: {light: '#2563eb', dark: '#60a5fa'},
    },
    pulseBand: {
        fill: {light: 'rgba(147, 51, 234, 0.12)', dark: 'rgba(168, 85, 247, 0.16)'},
        stroke: {light: '#7c3aed', dark: '#c084fc'},
        glow: 'rgba(168, 85, 247, 0.35)',
    },
    /** Event symbols on the segments. */
    events: {
        sell: {light: '#dc2626', dark: '#f87171'},
        transfer: {light: '#7c3aed', dark: '#c084fc'},
        split: {light: '#ca8a04', dark: '#facc15'},
        buy: {light: '#059669', dark: '#34d399'},
    },
} as const;

/** The lots WAC/price chart. */
export const LOT_WAC_COLORS = {
    /** The combined line, and a line with no broker. */
    combinedSeries: {light: '#475569', dark: '#94a3b8'},
    /** Event markers, by kind; income has a marker of its own. */
    markers: {
        buy: {light: '#16a34a', dark: '#86efac'},
        sell: {light: '#dc2626', dark: '#fca5a5'},
        transfer: {light: '#1d4ed8', dark: '#93c5fd'},
        adjustment: {light: '#d97706', dark: '#fcd34d'},
        split: {light: '#7c3aed', dark: '#c4b5fd'},
    },
    incomeMarker: {light: '#7c3aed', dark: '#c4b5fd'},
    /** The bubble of a lot with no broker, and of a lot whose P&L is zero. */
    noBrokerBubble: {light: '#475569', dark: '#94a3b8'},
    bubbleZero: {light: '#64748b', dark: '#94a3b8'},
    /** The market price line. */
    marketLine: {light: '#16a34a', dark: '#4ade80'},
} as const;

/** The lots comparison chart. Its lot lines are generated by id (`lotColor`). */
export const LOT_COMPARISON_COLORS = {
    /** The value line of lots estimated at cost, and a return that cannot be computed. */
    estimatedValue: {light: '#64748b', dark: '#94a3b8'},
    undefinedReturn: {light: '#64748b', dark: '#94a3b8'},
    aggregateReturn: {light: '#d97706', dark: '#fbbf24'},
    residual: {light: '#2563eb', dark: '#60a5fa'},
    proceeds: {light: '#059669', dark: '#34d399'},
    income: {light: '#7c3aed', dark: '#a78bfa'},
    originalCost: {light: '#475569', dark: '#cbd5e1'},
    aggregateTotal: {light: '#0f172a', dark: '#e2e8f0'},
} as const;
