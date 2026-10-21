/**
 * Colours of the ECharts charts, by meaning — the one home for them.
 *
 * ECharts draws from an options object built in TypeScript, so every chart colour is a value picked for the active
 * theme. Each chart used to write its own pairs inline; they now live here.
 *
 * **Divergences keep their names.** Where two charts drew the same thing in two colours, both names stay — the Δ of the
 * tooltip and the lines, the price charts' red and the portfolio's — and since D-T28 they read the same role, so the
 * designer can part them again with one edit. A value with two meanings gets two names.
 *
 * A `{light, dark}` pair is read with `themed(pair, dark)` (`./themePair`); a plain string is the same colour in both
 * themes.
 *
 * **The neutrals are roles (B4, DV, 16/10/2026).** Axes, grids, labels, tooltip boxes and pointers left these tables for
 * {@link chartNeutrals}, which reads the roles of tokens.css at each draw: there, two names of one meaning may now read
 * one role (the shared tooltip box and the candlestick's own). The tables keep the series, the states and the signs.
 *
 * **The series are roles too (DV-10, C2, D-T28 of 21/10/2026).** Each pair is the nearest role of tokens.css
 * (`rolePair('--lf-…')`, `./seriesRoles`), «da rivedere» with the designer; the names and the shapes did not change. A
 * plain string the same in both themes is a getter that reads the active theme's role at each access. Two values are
 * not roles: the map's land and the PAC's ideal weight are the designer's own (round 3).
 *
 * @module lib/theme/chartTheme
 */

import {toRgba} from './colorAlpha';
import {chartRoles} from './roleColors';
import {pairNow, rolePair, rolePairAlpha, rolePairSplit, roleNow, roleNowAlpha} from './seriesRoles';

/** The price family: line chart, full price chart, candlestick chart, and the compact chart of the cards. */
export const PRICE_SERIES = {
    /** The price line when it is not coloured against the baseline: the app's green (was a dark forest in light, a bright green in dark). */
    line: rolePair('--lf-focus'),
    /** Points with unsaved edits, the same in both themes: the warning, read at each access. */
    get pendingEditPoint() {
        return roleNow('--lf-warning');
    },
    /** Event markers of a comparison overlay that carries no colour of its own, the same in both themes: the grey of «other». */
    get comparisonMarkerFallback() {
        return roleNow('--lf-cat-other');
    },
};

/** Gain and loss in the charts. */
export const CHART_GAIN_LOSS = {
    /** The price charts, above and below the baseline: the price line, candles and their volume, indicator histograms. */
    price: {
        gain: rolePair('--lf-gain'),
        loss: rolePair('--lf-loss'),
    },
    /** The portfolio charts: Growth and Performance, the treemap, the lot charts. Since D-T28 the same red as the price charts': both are `--lf-loss`. */
    portfolio: {
        gain: rolePair('--lf-gain'),
        loss: rolePair('--lf-loss'),
    },
    /** The "(Δ …)" suffix of the price tooltips, the same in both themes: gain and loss, read at each access. */
    tooltipDelta: {
        get gain() {
            return roleNow('--lf-gain');
        },
        get loss() {
            return roleNow('--lf-loss');
        },
    },
};

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
         * The ownership semi-donut. Its owners take the first asset types (`CATEGORY_SEQUENCE` in `./chartCategories`)
         * by their key, never by the order of the data; the initial on an avatar takes the text that reads best on its
         * disc (`readableText`). The slice of what is still available is a track.
         */
        semiDonut: {label: primary, labelShadow: translucent(card, 0.8, 0.6), labelLine: input, avatarBorder: card, sliceGap: card, available: roles.color('--lf-surface-neutral')},
        /** World maps: the borders between countries, the labels and their background. The land and the highlight: `GEO_MAP_COLORS`. */
        geoMap: {border: card, label: primary, labelBackground: translucent(card, 0.72, 0.55)},
        /**
         * The correlation heatmap and its tooltip. Its scale and the value in a cell are the designer's own
         * (`CORRELATION_SCALE` and `CORRELATION_CELL_TEXT` in `./chartPalettes`, round 3, §1.6).
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
        get seriesFallback() {
            return roleNow('--lf-text-muted');
        },
    },
};

/** The risk-return scatter chart: its points. Its axes and the capital market line: `chartNeutrals().riskReturn`. */
export const RISK_RETURN_COLORS = {
    portfolio: rolePair('--lf-info'),
    benchmark: rolePair('--lf-warning'),
    /** Every other asset. */
    other: rolePair('--lf-cat-other'),
    /** The selected point: the green of a selected control. */
    selected: rolePair('--lf-checked'),
} as const;

/** The allocation charts: pie and donut, allocation history. Their category colours: `./chartCategories`; their neutrals: `chartNeutrals().allocation`. */
export const ALLOCATION_CHART_COLORS = {
    /** The bubble behind a family's icon on its slice, the same in both themes: the white of the text on a scrim, at 75 %. */
    get iconBubble() {
        return roleNowAlpha('--lf-on-overlay', 0.75);
    },
};

/** World maps: the portfolio's geography and the PAC planner's exposure maps. Their scale: `GEO_CHOROPLETH_SCALE`. */
export const GEO_MAP_COLORS = {
    /**
     * Countries with no data: the designer's neutral grey (round 3, §1.6), chosen with the scale, so not a role. Darker
     * than the scale's first step on purpose, at ΔE00 4.9 (light) and 6.1 (dark).
     */
    land: {light: '#D5D9E0', dark: '#343B46'},
    /** A hovered or selected country. */
    highlight: rolePair('--lf-warning'),
} as const;

/** The PAC planner's exposure bars, «ideal vs actual» (TD-1): the actual weight takes its row's category colour. */
export const PAC_EXPOSURE_COLORS = {
    /**
     * The ideal weight: the designer's neutral grey (round 3, §1.7; P1-a′ and P2-c, 17/10/2026), 3.0:1 and 4.8:1 on the
     * card. At least ΔE00 10 from every colour a row can draw, the shades of the ETF subtypes included, but in light
     * «Non classificato» (8.0) and «Other» (8.7).
     */
    ideal: {light: '#8C929E', dark: '#868594'},
} as const;

/** Chart signals, the same in both themes (read at each access). Default line colours: `SIGNAL_DEFAULT_PALETTE` in `./chartPalettes`. */
export const SIGNAL_COLORS = {
    /** Parts of backend indicators by role (MACD, Bollinger bands…); the `primary` part keeps the user's colour. */
    roles: {
        get secondary() {
            return roleNow('--lf-warning');
        },
        get positive() {
            return roleNow('--lf-gain');
        },
        get negative() {
            return roleNow('--lf-loss');
        },
        get neutral() {
            return roleNow('--lf-cat-other');
        },
        /** The violet of a part: the Stock type's, not the AI accent (the AI violet is no series). */
        get accent() {
            return roleNow('--lf-cat-stock');
        },
    },
    /** The legend's preview of a sign-coloured histogram, before the user customises it. */
    legendBarPreview: {
        get up() {
            return roleNow('--lf-gain');
        },
        get down() {
            return roleNow('--lf-loss');
        },
    },
    /** The measure tool's line: an orange, the commodity's. */
    get measure() {
        return roleNow('--lf-cat-commodity');
    },
};

/** Income events, shared by the Growth chart's income bars and the lot comparison chart. */
export const INCOME_EVENT_COLORS = {
    /** Dividends: the gold of the crypto type (was a gold at 3:1 on the card), kept apart from the deposit and the returns cash. */
    dividend: rolePair('--lf-cat-crypto'),
    /** Interest in the lot comparison chart: since D-T28 the same violet as the Growth chart's (`GROWTH_SERIES.interest`). */
    lotInterest: rolePair('--lf-cat-stock'),
} as const;

/** The Growth chart's series, read as `cc(key)` in `GrowthChart.svelte`. */
export const GROWTH_SERIES = {
    /** NAV — the prominent line. */
    nav: rolePair('--lf-focus'),
    /** Assets at cost — blue area. */
    bookAssetLike: rolePair('--lf-info'),
    /** Capital cash — subdued green area. */
    cashContributed: rolePair('--lf-border-input'),
    /** Returns cash — bright emerald area. */
    cashGenerated: rolePair('--lf-gain'),
    /** Capital baseline — grey dashed. */
    capitalBaseline: rolePair('--lf-cat-other'),
    /** TWRR (% mode). */
    invested: rolePair('--lf-info'),
    /** ROI (% mode). */
    pctCash: rolePair('--lf-border-input'),
    /** P&L mode — the total line, as prominent as NAV. */
    totalPnl: rolePair('--lf-focus'),
    /** P&L income submode — dividend stacked bar: the same gold as the lot comparison chart's dividends. */
    dividend: INCOME_EVENT_COLORS.dividend,
    /** P&L income submode — interest stacked bar. */
    interest: rolePair('--lf-cat-stock'),
    /** P&L income submode — costs (fees and taxes): orange here, red in the Performance chart. */
    costs: rolePair('--lf-cat-commodity'),
    /** P&L income submode — deposit-size bar. */
    deposit: rolePair('--lf-cat-liquidity'),
} as const;

/** The Performance chart's series and badges (`palette()` in `PerformanceChart.svelte`). Its rows and rules: `chartNeutrals().performance`. */
export const PERFORMANCE_COLORS = {
    unrealized: rolePair('--lf-info'),
    /** Realized P&L: the gain green, under its own name. */
    realized: rolePair('--lf-gain'),
    income: rolePair('--lf-warning'),
    /** Costs: red here, orange in the Growth chart. */
    costs: rolePair('--lf-loss'),
    other: rolePair('--lf-cat-stock'),
    neutral: rolePair('--lf-cat-hold'),
    /**
     * Badges of an open or a fully sold position, on the axis and in the tooltip, and their text in both themes. The text
     * is white, so the fill must be dark in both: the primary button's green for open; for closed a slate (light) and
     * the input border's grey-green (dark), which no single role gives.
     */
    openBadge: rolePair('--lf-action'),
    closedBadge: rolePairSplit('--lf-cat-hold-on-soft', '--lf-border-input'),
    get badgeText() {
        return roleNow('--lf-on-overlay');
    },
};

/** The exposure treemap. Tiles with a P&L take `treemapPnlColor` (`./chartColorScales`); its headers and borders: `chartNeutrals().treemap`. */
export const TREEMAP_COLORS = {
    /** A tile with no P&L, the same in both themes. */
    get noPnl() {
        return pairNow(rolePairSplit('--lf-cat-hold-on-soft', '--lf-border-input'));
    },
    /** The name on a tile, and its shadow, the same in both themes: the white of the text on a scrim, and the scrim. */
    get tileLabel() {
        return roleNow('--lf-on-overlay');
    },
    get tileLabelShadow() {
        return roleNow('--lf-surface-overlay');
    },
};

/** Lines the risk panels add to a price chart, the same in both themes. */
export const RISK_OVERLAY_COLORS = {
    /** The comparison asset's cumulative return. */
    get comparisonAsset() {
        return roleNow('--lf-warning');
    },
    /** The median of the simulated band. */
    get simulation() {
        return roleNow('--lf-info');
    },
};

/** The state of a lot: fill of its markers and of the Gantt filter buttons. */
export const LOT_STATE_COLORS = {
    open: rolePair('--lf-info'),
    partial: rolePair('--lf-warning'),
    closed: rolePair('--lf-cat-other'),
} as const;

/** The lots Gantt chart. Broker segments take the broker's colour (`getBrokerColor`); its neutrals: `chartNeutrals().lots`. */
export const LOT_GANTT_COLORS = {
    /** A segment in transit between two brokers. */
    inTransit: rolePair('--lf-cat-stock'),
    /** A segment with no broker. */
    noBroker: rolePair('--lf-info'),
    /** The tooltip's estimated current value, and its costs. */
    estimatedValue: rolePair('--lf-warning'),
    cost: rolePair('--lf-loss'),
    /** The band behind the selected lot, and the pulsing one after a jump to it. */
    highlightBand: {
        fill: rolePairAlpha('--lf-info', 0.08, 0.1),
        stroke: rolePair('--lf-info'),
    },
    pulseBand: {
        fill: rolePairAlpha('--lf-cat-stock', 0.12, 0.16),
        stroke: rolePair('--lf-cat-stock'),
        get glow() {
            return roleNowAlpha('--lf-cat-stock', 0.35);
        },
    },
    /** Event symbols on the segments. */
    events: {
        sell: rolePair('--lf-loss'),
        transfer: rolePair('--lf-cat-stock'),
        split: rolePair('--lf-cat-crypto'),
        buy: rolePair('--lf-gain'),
    },
};

/** The lots WAC/price chart. */
export const LOT_WAC_COLORS = {
    /** The combined line, and a line with no broker. */
    combinedSeries: rolePair('--lf-text-secondary'),
    /** Event markers, by kind; income has a marker of its own. */
    markers: {
        buy: rolePair('--lf-gain'),
        sell: rolePair('--lf-loss'),
        transfer: rolePair('--lf-info-on-soft'),
        adjustment: rolePair('--lf-warning'),
        split: rolePair('--lf-cat-stock'),
    },
    incomeMarker: rolePair('--lf-cat-stock'),
    /** The bubble of a lot with no broker, and of a lot whose P&L is zero. */
    noBrokerBubble: rolePair('--lf-text-secondary'),
    bubbleZero: rolePair('--lf-cat-other'),
    /** The market price line. */
    marketLine: rolePair('--lf-gain'),
} as const;

/** The lots comparison chart. Its lot lines are generated by id (`lotColor`). */
export const LOT_COMPARISON_COLORS = {
    /** The value line of lots estimated at cost, and a return that cannot be computed. */
    estimatedValue: rolePair('--lf-cat-other'),
    undefinedReturn: rolePair('--lf-cat-other'),
    aggregateReturn: rolePair('--lf-warning'),
    residual: rolePair('--lf-info'),
    proceeds: rolePair('--lf-gain'),
    income: rolePair('--lf-cat-stock'),
    originalCost: rolePair('--lf-text-secondary'),
    aggregateTotal: rolePair('--lf-text-primary'),
} as const;
