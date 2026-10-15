/**
 * Tailwind classes that colour signed figures and states — the one home for them.
 *
 * Every string below is the exact class list a component wrote before it moved here, so moving changed no pixel.
 * The variants differ on purpose or by drift — emerald or green for a gain, red-500 or red-600 for a loss, bars whose
 * dark shades run the other way — and each keeps its own name, so the designer can see them side by side and decide.
 * The thresholds stay with the callers (`>= 0`, `> 0`, three-way with zero): only the colours live here.
 *
 * The strings stay complete literals: Tailwind generates a class only when it finds it written out in a source file,
 * so a class assembled from pieces would silently lose its CSS.
 *
 * @module lib/theme/toneClasses
 */

/** Text colour of a signed figure, by the surface that draws it. */
export const SIGN_TEXT = {
    /** Asset and FX price deltas, the measure tool. */
    market: {
        gain: 'text-emerald-600 dark:text-emerald-400',
        loss: 'text-red-500 dark:text-red-400',
        /** No delta to show (asset and FX tables). */
        none: 'text-gray-400 dark:text-gray-500',
    },
    /** Portfolio tables (exposure, contribution, lots, other effects) and the KPI deltas. */
    portfolio: {
        gain: 'text-green-600 dark:text-green-400',
        loss: 'text-red-500 dark:text-red-400',
        zero: 'text-gray-500 dark:text-gray-400',
    },
    /** KPI breakdown rows and the KpiCard change badge: green, with a darker red. */
    kpi: {
        gain: 'text-green-600 dark:text-green-400',
        loss: 'text-red-600 dark:text-red-400',
    },
    /** The headline value of a KPI or risk metric card. */
    headline: {
        gain: 'text-green-700 dark:text-green-400',
        loss: 'text-red-700 dark:text-red-400',
        neutral: 'text-gray-800 dark:text-gray-100',
    },
    /** The broker card's gain/loss line: emerald, with the darker red. */
    brokerCard: {
        gain: 'text-emerald-600 dark:text-emerald-400',
        loss: 'text-red-600 dark:text-red-400',
    },
} as const;

/** Fill of a signed bar or accent line. */
export const SIGN_BAR = {
    /** KPI magnitude bars: the loss shades run the other way round (red-400 in light, red-500 in dark). */
    kpi: {
        gain: 'bg-green-500 dark:bg-green-400',
        loss: 'bg-red-400 dark:bg-red-500',
    },
    /** The thin accent line on top of KPI and risk metric cards. */
    accent: {
        gain: 'bg-green-500 dark:bg-green-400',
        loss: 'bg-red-500 dark:bg-red-400',
    },
    /** Stress-test tornado bars, translucent, the same in both themes. */
    tornado: {
        gain: 'bg-emerald-500/80',
        loss: 'bg-red-500/80',
    },
} as const;

/** Signed values coloured by polarity rather than by gain or loss. */
export const POLARITY_TONES = {
    /** Correlation pairs: red below zero, blue above — the heatmap's polarity, not a verdict. */
    correlationText: {
        negative: 'text-red-700 dark:text-red-300',
        positive: 'text-blue-700 dark:text-blue-300',
    },
    correlationTag: {
        negative: 'bg-red-50 text-red-800 dark:bg-red-900/40 dark:text-red-200',
        positive: 'bg-blue-50 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
    },
    /** Risk contribution bars: a negative contribution red, the rest blue, the same in both themes. */
    riskContributionBar: {
        negative: 'bg-red-500',
        positive: 'bg-blue-500',
    },
    /** Diversification divergence, where higher is worse: positive red, the rest emerald. */
    divergenceText: {
        positive: 'text-red-600 dark:text-red-400',
        negative: 'text-emerald-600 dark:text-emerald-400',
    },
    divergenceBar: {
        positive: 'bg-red-500 dark:bg-red-400',
        negative: 'bg-emerald-500 dark:bg-emerald-400',
    },
} as const;

/**
 * Colours of states — badges, notices, chips, toasts — one table per surface.
 *
 * The same kinds of state are drawn in several patterns today: badges at 100/700 or 100/800 with a dark 900/30 or
 * 900/40, success in green or emerald, info in sky or blue, and the data-quality banner draws errors in amber like
 * warnings (only its icon tells them apart). Layout classes stay with the components; only colours live here.
 */
export const STATUS_TONES = {
    /** Sync result icons: no dark variant. */
    syncIcon: {
        ok: 'text-emerald-500',
        partial: 'text-amber-500',
        failed: 'text-red-500',
        skipped: 'text-gray-400',
        /** A status the table does not know. */
        unknown: 'text-gray-400',
    },
    /** PAC planner badges (`BADGE` in the planner's `ui.ts` adds the layout). */
    pacBadge: {
        neutral: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200',
        success: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
        info: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200',
        warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
        danger: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
    },
    /** PAC planner notices (`NOTICE` in the planner's `ui.ts` adds the layout). */
    pacNotice: {
        info: 'border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900 dark:bg-sky-950/30 dark:text-sky-100',
        warning: 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100',
        danger: 'border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950/30 dark:text-red-100',
        success: 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-100',
    },
    /** PAC asset distribution editor, bar fill by total: brand green at 100 %, red above, amber below. */
    pacTargetBar: {
        balanced: 'bg-libre-green',
        excess: 'bg-red-400',
        missing: 'bg-amber-400',
        unknown: 'bg-gray-300 dark:bg-gray-600',
    },
    /** PAC asset distribution editor, total figure: only balanced and unknown have a dark variant. */
    pacTargetTotal: {
        balanced: 'text-green-600 dark:text-green-400',
        excess: 'text-red-500',
        missing: 'text-amber-500',
        unknown: 'text-gray-500 dark:text-gray-400',
    },
    /** Toasts: solid fills, the same in both themes. */
    toast: {
        success: 'bg-emerald-600 text-white',
        error: 'bg-red-600 text-white',
        warning: 'bg-amber-500 text-white',
        info: 'bg-blue-500 text-white',
    },
    /** Import wizard, status of a report set: success in green, the error text at 700. */
    reportSet: {
        loading: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-300',
        complete: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
        incomplete: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
        error: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    },
    /** File-set badges in the files area. */
    fileSet: {
        combined: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200',
        stale: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200',
        usedInCombined: 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-gray-200',
        set: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200',
        incomplete: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
    },
    /** Asset chips of the risk panels (`AssetChip` adds the border widths and style). */
    riskAssetChip: {
        default: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-300',
        warning: 'border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-600 dark:bg-amber-900/20 dark:text-amber-300',
        excluded: 'border-gray-300 text-gray-400 dark:border-slate-600 dark:text-gray-500',
    },
    /** Data-quality banner: errors and warnings share the amber tone; info is sky. */
    dataQuality: {
        attention: {
            container: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400',
            button: 'bg-amber-100 dark:bg-amber-800/40 hover:bg-amber-200 dark:hover:bg-amber-700/40',
        },
        info: {
            container: 'bg-sky-50 dark:bg-sky-900/20 border-sky-200 dark:border-sky-800 text-sky-700 dark:text-sky-400',
            button: 'bg-sky-100 dark:bg-sky-800/40 hover:bg-sky-200 dark:hover:bg-sky-700/40',
        },
    },
    /** The «Updates paused» pill of the live prices: a neutral chip on the roles, which follow the theme by themselves. */
    liveUpdates: {
        paused: 'bg-lf-neutral text-lf-secondary',
    },
} as const;

/** Badges that tell kinds apart rather than states: one hue per kind. */
export const KIND_TONES = {
    /** Import wizard, identifier badges: ISIN sky, symbol violet, name slate. */
    identifier: {
        isin: 'border-sky-300 bg-sky-100 text-sky-900 dark:border-sky-700 dark:bg-sky-900/40 dark:text-sky-100',
        symbol: 'border-violet-300 bg-violet-100 text-violet-900 dark:border-violet-700 dark:bg-violet-900/40 dark:text-violet-100',
        name: 'border-slate-300 bg-slate-100 text-slate-800 dark:border-slate-600 dark:bg-slate-700/60 dark:text-slate-100',
    },
} as const;
