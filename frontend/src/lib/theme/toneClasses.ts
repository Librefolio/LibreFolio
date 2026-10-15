/**
 * Tailwind classes that colour signed figures and states — the one home for them.
 *
 * The entries on the colour roles (`text-lf-gain`, `bg-lf-loss`…) follow the theme by themselves, with no `dark:`
 * half. The others are still the exact class lists the components wrote before they moved here, until their wave of
 * the colour migration: their variants differ on purpose or by drift — success in green or emerald, info in sky or
 * blue, badges at 100/700 or 100/800 — and each keeps its own name, so the designer can see them side by side and
 * decide. The thresholds stay with the callers (`>= 0`, `> 0`, three-way with zero): only the colours live here.
 *
 * An entry is either all roles or all palette classes, and the element that takes a role entry carries no palette
 * colour of its own: `app.css` exempts every element with a `-lf-` class from its legacy dark remap, so a mixed element
 * would keep half of its light colours in dark.
 *
 * The strings stay complete literals: Tailwind generates a class only when it finds it written out in a source file,
 * so a class assembled from pieces would silently lose its CSS.
 *
 * @module lib/theme/toneClasses
 */

/**
 * Text colour of a signed figure, by the surface that draws it. Every surface shares the gain and loss roles (TD-2,
 * W3-b); each keeps its name, so one can take a role of its own without touching its consumers.
 */
export const SIGN_TEXT = {
    /** Asset and FX price deltas and live price moves, the measure tool. */
    market: {
        gain: 'text-lf-gain',
        loss: 'text-lf-loss',
        /** No delta to show (asset and FX tables). */
        none: 'text-lf-muted',
    },
    /** Portfolio tables (exposure, contribution, lots, other effects), the lot custody figures and the KPI deltas. */
    portfolio: {
        gain: 'text-lf-gain',
        loss: 'text-lf-loss',
        zero: 'text-lf-muted',
    },
    /** KPI breakdown rows and the KpiCard change badge. */
    kpi: {
        gain: 'text-lf-gain',
        loss: 'text-lf-loss',
    },
    /** The headline value of a KPI or risk metric card. */
    headline: {
        gain: 'text-lf-gain',
        loss: 'text-lf-loss',
        neutral: 'text-lf-primary',
    },
    /** The broker card's gain/loss line. */
    brokerCard: {
        gain: 'text-lf-gain',
        loss: 'text-lf-loss',
    },
} as const;

/** Fill of a signed bar or accent line: the gain and loss roles of the figures they stand beside. */
export const SIGN_BAR = {
    /** KPI magnitude bars. */
    kpi: {
        gain: 'bg-lf-gain',
        loss: 'bg-lf-loss',
    },
    /** The thin accent line on top of KPI and risk metric cards. */
    accent: {
        gain: 'bg-lf-gain',
        loss: 'bg-lf-loss',
    },
    /** Stress-test tornado bars, translucent. */
    tornado: {
        gain: 'bg-lf-gain/80',
        loss: 'bg-lf-loss/80',
    },
} as const;

/** Signed values coloured by polarity rather than by gain or loss. */
export const POLARITY_TONES = {
    /**
     * Correlation pairs: the danger role below zero, the info role above — the heatmap's own polarity, its two ends
     * (GR5.3), not a verdict.
     */
    correlationText: {
        negative: 'text-lf-danger',
        positive: 'text-lf-info',
    },
    correlationTag: {
        negative: 'bg-lf-danger-soft text-lf-danger-on-soft',
        positive: 'bg-lf-info-soft text-lf-info-on-soft',
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
