/**
 * Colours of the ECharts charts, by meaning — the one home for them.
 *
 * ECharts draws from an options object built in TypeScript, so every chart colour is a value picked for the active
 * theme. Each chart used to write its own pairs inline; they now live here with the values they had, so moving them
 * changed no pixel.
 *
 * **Divergences stay, with a name.** Where two charts draw the same thing in two colours, both values are kept side by
 * side — the shared tooltip box and the candlestick's own, the emerald of the tooltip Δ and the green of the lines — so
 * the designer can see them and decide. A value with two meanings gets two names. Nothing here was unified.
 *
 * A `{light, dark}` pair is read with `themed(pair, dark)` (`./themePair`); a plain string is the same colour in both
 * themes.
 *
 * @module lib/theme/chartTheme
 */

/** The price family: line chart, full price chart, candlestick chart, and the compact chart of the cards. */
export const PRICE_SERIES = {
    /** The price line when it is not coloured against the baseline. */
    line: {light: '#1a4031', dark: '#4ade80'},
    /** The dashed line that baseline colouring compares against. */
    baseline: {light: '#9ca3af', dark: '#64748b'},
    /** Points with unsaved edits, the same in both themes. */
    pendingEditPoint: '#f59e0b',
    /** The ring around unsaved-edit points: the card's background. */
    pendingEditPointRing: {light: '#ffffff', dark: '#1e293b'},
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

/** Axes, grid lines and other neutral strokes. */
export const CHART_NEUTRALS = {
    /** Axes of the price charts (`getChartColors`, and the line, full price and candlestick charts). */
    priceAxis: {
        line: {light: '#d1d5db', dark: '#475569'},
        label: {light: '#6b7280', dark: '#94a3b8'},
        gridLine: {light: '#d1d5db', dark: '#4b5563'},
    },
    /** Axis and legend text, and split lines, of the dashboard charts (`buildGridColors`, allocation, maps). */
    dashboard: {
        text: {light: '#64748b', dark: '#94a3b8'},
        gridLine: {light: '#f1f5f9', dark: '#1e293b'},
    },
    /** The greyed arrow of a paged legend that cannot go further. */
    legendPageIconInactive: {light: '#cbd5e1', dark: '#334155'},
    /** A secondary axis with no signal colour to borrow. */
    secondaryAxisFallback: {light: '#9ca3af', dark: '#64748b'},
    /** Labels of an indicator's dashed reference levels (RSI 30 and 70, for instance). */
    referenceLevelLabel: {light: '#64748b', dark: '#cbd5e1'},
} as const;

/** Tooltip boxes and the text inside them. */
export const CHART_TOOLTIP_COLORS = {
    /** The shared tooltip box (`buildTooltipTheme`, the line and full price charts). */
    box: {
        background: {light: '#ffffff', dark: '#1e293b'},
        border: {light: '#e2e8f0', dark: '#334155'},
        text: {light: '#1e293b', dark: '#e2e8f0'},
        muted: {light: '#64748b', dark: '#94a3b8'},
    },
    /** The candlestick chart's own box: its border and text differ in the light theme. Its background is `box`'s. */
    candlestickBox: {
        border: {light: '#e5e7eb', dark: '#334155'},
        text: {light: '#111827', dark: '#e2e8f0'},
        heading: {light: '#1f2937', dark: '#e2e8f0'},
        muted: {light: '#6b7280', dark: '#94a3b8'},
        crosshair: {light: '#9ca3af', dark: '#475569'},
        /** An overlay series that reports no colour, the same in both themes. */
        seriesFallback: '#888',
    },
    /** Asides of the price tooltips — axis notes, the day a value is from, band bounds — one gray in both themes. */
    aside: '#94a3b8',
    /** The stale-data warning line, amber in both themes. */
    staleWarning: '#f59e0b',
} as const;

/** The risk-return scatter chart. */
export const RISK_RETURN_COLORS = {
    portfolio: {light: '#0284c7', dark: '#38bdf8'},
    benchmark: {light: '#d97706', dark: '#fbbf24'},
    /** Every other asset. */
    other: {light: '#64748b', dark: '#94a3b8'},
    /** The selected point: the hue of a selected table row, apart from every role colour. */
    selected: {light: '#22c55e', dark: '#4ade80'},
    axis: {light: '#cbd5e1', dark: '#475569'},
    axisText: {light: '#475569', dark: '#cbd5e1'},
    capitalMarketLine: {light: '#94a3b8', dark: '#64748b'},
} as const;

/** The allocation charts: pie and donut, allocation history. Their category colours: `./chartCategories`. */
export const ALLOCATION_CHART_COLORS = {
    /** The gap between pie slices and rings: white on the light card, a slate a step above the dark card. */
    sliceBorder: {light: '#ffffff', dark: '#293548'},
    /** Captions outside the outer ring. */
    caption: {light: '#374151', dark: '#cbd5e1'},
    /** The bubble behind a family's icon on its slice, the same in both themes. */
    iconBubble: 'rgba(255, 255, 255, 0.75)',
    /** Labels on the areas of the allocation history, and their halo. */
    historyAreaLabel: {light: '#000000', dark: '#ffffff'},
    historyAreaLabelShadow: {light: '#fff', dark: '#000'},
} as const;

/**
 * The ownership semi-donut. Its owners take the first asset types in order (`CATEGORY_SEQUENCE` in
 * `./chartCategories`); the initial on an avatar takes the text that reads best on its disc (`readableText`).
 */
export const SEMI_DONUT_COLORS = {
    label: {light: '#1e293b', dark: '#e2e8f0'},
    labelShadow: {light: 'rgba(255,255,255,0.8)', dark: 'rgba(0,0,0,0.6)'},
    labelLine: {light: '#94a3b8', dark: '#475569'},
    /** The ring around an owner's avatar, picture or initial. */
    avatarBorder: {light: '#ffffff', dark: '#334155'},
    /** The gap between slices: the card's background. */
    sliceGap: {light: '#ffffff', dark: '#1e293b'},
    /** The slice of what is still available. */
    available: {light: 'rgba(203,213,225,0.5)', dark: 'rgba(100,116,139,0.3)'},
} as const;

/** World maps: the portfolio's geography and the PAC planner's exposure maps. Their scale: `GEO_CHOROPLETH_SCALE`. */
export const GEO_MAP_COLORS = {
    /** Countries with no weight. */
    land: {light: '#e2e8f0', dark: '#334155'},
    border: {light: '#cbd5e1', dark: '#1e293b'},
    /** A hovered or selected country. */
    highlight: {light: '#f59e0b', dark: '#fbbf24'},
    label: {light: '#1e293b', dark: '#e2e8f0'},
    labelBackground: {light: 'rgba(255,255,255,0.72)', dark: 'rgba(15, 23, 42, 0.55)'},
} as const;

/**
 * The correlation heatmap and its tooltip. Its scale is three roles, danger, panel and info (GR5.3, read in
 * `CorrelationHeatmap.svelte` through `./roleColors`); the value in a cell takes the text that reads best on it.
 */
export const CORRELATION_COLORS = {
    /** The gap between cells: the card's background. */
    cellGap: {light: '#ffffff', dark: '#1e293b'},
    /** Border and halo of the hovered cell: no hue, the opposite shade of the theme. */
    emphasisBorder: {light: '#0f172a', dark: '#ffffff'},
    emphasisHalo: {light: 'rgba(255, 255, 255, 0.95)', dark: 'rgba(2, 6, 23, 0.95)'},
    axisLabel: {light: '#475569', dark: '#cbd5e1'},
    /** Exposure badges in the tooltip, and the rule above them: the same in both themes. */
    tooltipBadge: {background: '#f1f5f9', text: '#334155'},
    tooltipDivider: 'rgba(148,163,184,0.35)',
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

/** The Growth chart's strokes other than its series. Its broker lines: `growthBrokerColor` in `./chartPalettes`. */
export const GROWTH_CHART_COLORS = {
    /** The dashed zero line of the P&L mode. */
    pnlReference: {light: '#9ca3af', dark: '#64748b'},
    /** Vertical separators between ladder buckets: stronger than the grid lines, which vanished at the same tint. */
    bucketSeparator: {light: '#cbd5e1', dark: '#64748b'},
} as const;

/** The Performance chart (`palette()` and the axis rows in `PerformanceChart.svelte`). */
export const PERFORMANCE_COLORS = {
    unrealized: {light: '#2563eb', dark: '#60a5fa'},
    /** Realized P&L: the gain green, under its own name. */
    realized: {light: '#16a34a', dark: '#4ade80'},
    income: {light: '#d97706', dark: '#fbbf24'},
    /** Costs: red here, orange in the Growth chart. */
    costs: {light: '#dc2626', dark: '#f87171'},
    other: {light: '#7c3aed', dark: '#a78bfa'},
    neutral: {light: '#64748b', dark: '#cbd5e1'},
    /** The value of a row that is exactly zero. */
    zeroValue: {light: '#0f172a', dark: '#e2e8f0'},
    /** The rows of the y axis: asset name, its second line, section headings. */
    axisName: {light: '#1f2937', dark: '#e2e8f0'},
    axisSecondary: {light: '#64748b', dark: '#94a3b8'},
    axisSection: {light: '#475569', dark: '#cbd5e1'},
    /** Badges of an open or a fully sold position, on the axis and in the tooltip, and their text in both themes. */
    openBadge: {light: '#16a34a', dark: '#166534'},
    closedBadge: {light: '#64748b', dark: '#475569'},
    badgeText: '#ffffff',
    /** The zero line of the first series. */
    zeroLine: {light: '#64748b', dark: '#94a3b8'},
    /** The rule under a section heading. */
    sectionSeparator: {light: '#cbd5e1', dark: '#475569'},
    /** The band behind the hovered row (mobile: one custom rect over label and bar), and the axis shadow on desktop. */
    rowHighlight: {light: 'rgba(148, 163, 184, 0.16)', dark: 'rgba(148, 163, 184, 0.14)'},
    axisPointerShadow: {light: 'rgba(148, 163, 184, 0.14)', dark: 'rgba(148, 163, 184, 0.12)'},
} as const;

/** The exposure treemap. Tiles with a P&L take `treemapPnlColor` (`./chartColorScales`). */
export const TREEMAP_COLORS = {
    /** A tile with no P&L, the same in both themes. */
    noPnl: '#6b7280',
    /** The header of a group (a broker). */
    groupLabel: {light: '#334155', dark: '#e2e8f0'},
    groupLabelBackground: {light: 'rgba(248,250,252,0.8)', dark: 'rgba(30,41,59,0.8)'},
    /** The name on a tile, and its shadow, the same in both themes. */
    tileLabel: '#fff',
    tileLabelShadow: 'rgba(0,0,0,0.5)',
    /** Borders of the first two levels: groups, then tiles. */
    groupBorder: {light: '#e2e8f0', dark: '#334155'},
    tileBorder: {light: '#cbd5e1', dark: '#475569'},
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

/** Shared by the three lot charts. */
export const LOT_CHART_COLORS = {
    /** The ring that lifts a marker off what lies under it. */
    markerRing: {light: '#ffffff', dark: '#0f172a'},
    /** The same ring on a hovered marker. */
    markerEmphasisRing: {light: '#0f172a', dark: '#e2e8f0'},
} as const;

/** The lots Gantt chart. Broker segments take the broker's colour (`getBrokerColor`). */
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
    /** The border of a selected segment. */
    selectedSegmentBorder: {light: '#0f172a', dark: '#e0f2fe'},
    /** The elbow from a lot to the lot it came from. */
    lineageConnector: {light: 'rgba(71,85,105,0.45)', dark: 'rgba(226,232,240,0.48)'},
    /** The label on a segment. */
    segmentLabel: {light: '#0f172a', dark: '#f8fafc'},
    /** Event symbols on the segments. */
    events: {
        sell: {light: '#dc2626', dark: '#f87171'},
        transfer: {light: '#7c3aed', dark: '#c084fc'},
        split: {light: '#ca8a04', dark: '#facc15'},
        buy: {light: '#059669', dark: '#34d399'},
    },
    /** The text of a selected state filter button. */
    stateChipText: {light: '#ffffff', dark: '#0f172a'},
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
    /** The zero line of the P&L axis. */
    zeroLine: {light: 'rgba(71,85,105,0.6)', dark: 'rgba(148,163,184,0.75)'},
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
