/**
 * Tailwind classes that colour signed figures and states — the one home for them.
 *
 * Every entry is on the colour roles (`text-lf-gain`, `bg-lf-success-soft`…), which follow the theme by themselves, with
 * no `dark:` half; the kinds told apart by hue alone (`KIND_TONES`, the combined file set) take the nearest category's
 * roles since D-T28. Several entries now hold the same classes: each keeps its own name, so one
 * surface can take a role of its own without touching its consumers. The thresholds stay with the callers (`>= 0`,
 * `> 0`, three-way with zero): only the colours live here.
 *
 * An entry is all roles, and the element that takes a role entry carries no palette
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
    /** The risk tables (DV, W6-a). */
    riskTable: {
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
    /** The bars of the returns histogram (DV, W6-a), translucent like the tornado. */
    histogram: {
        gain: 'bg-lf-gain/80',
        loss: 'bg-lf-loss/80',
    },
} as const;

/**
 * A sign on a tint: a badge or a chip that says gain or loss, not a state — the income and cost effects of the dashboard
 * (`OtherPeriodEffectsTable`). The gain and loss tints, not the success and danger ones, so the designer can part them
 * (rule 7 of the design-system skill).
 */
export const SIGN_BADGE = {
    gain: 'bg-lf-gain-soft text-lf-gain-on-soft',
    loss: 'bg-lf-loss-soft text-lf-loss-on-soft',
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
    /** Risk contribution bars: a negative contribution in the danger role, the rest in info — the correlation's poles. */
    riskContributionBar: {
        negative: 'bg-lf-danger',
        positive: 'bg-lf-info',
    },
    /** Diversification divergence, where higher is worse: positive in the danger role, the rest in success. */
    divergenceText: {
        positive: 'text-lf-danger',
        negative: 'text-lf-success',
    },
    divergenceBar: {
        positive: 'bg-lf-danger',
        negative: 'bg-lf-success',
    },
} as const;

/**
 * Colours of states — badges, notices, chips, toasts — one table per surface, on the state roles (W3-c), with X one of
 * `success`, `warning`, `danger`, `info`: a tint is `bg-lf-X-soft text-lf-X-on-soft`, with `border-lf-X-line` when it
 * has an edge; a solid fill is `bg-lf-X text-lf-on-status`; a neutral chip is `bg-lf-neutral text-lf-secondary`. Since
 * the designer's round 3 (17/10) the toasts are tints as well, a chip or a button inside a banner stands on the card
 * (`bannerChip`), and the data-quality banners draw each severity in its own state. Layout classes stay with the
 * components; only colours live here.
 */
export const STATUS_TONES = {
    /** Sync result icons. */
    syncIcon: {
        ok: 'text-lf-success',
        partial: 'text-lf-warning',
        failed: 'text-lf-danger',
        skipped: 'text-lf-muted',
        /** A status the table does not know. */
        unknown: 'text-lf-muted',
    },
    /** PAC planner badges (`BADGE` in the planner's `ui.ts` adds the layout). */
    pacBadge: {
        neutral: 'bg-lf-neutral text-lf-secondary',
        success: 'bg-lf-success-soft text-lf-success-on-soft',
        info: 'bg-lf-info-soft text-lf-info-on-soft',
        warning: 'bg-lf-warning-soft text-lf-warning-on-soft',
        danger: 'bg-lf-danger-soft text-lf-danger-on-soft',
    },
    /** PAC planner notices (`NOTICE` in the planner's `ui.ts` adds the layout and the `border`). */
    pacNotice: {
        info: 'border-lf-info-line bg-lf-info-soft text-lf-info-on-soft',
        warning: 'border-lf-warning-line bg-lf-warning-soft text-lf-warning-on-soft',
        danger: 'border-lf-danger-line bg-lf-danger-soft text-lf-danger-on-soft',
        success: 'border-lf-success-line bg-lf-success-soft text-lf-success-on-soft',
    },
    /**
     * PAC asset distribution editor, bar fill by total: success at 100 %, danger above, warning below. `unknown`, a
     * total that cannot be read, takes the colour the target already has in the result (`ResultCell`, the legend of
     * `AssetTable`): `secondary`, 5.8:1 on the `neutral` track of `TargetsStep`, the fill the track must stand apart
     * from (W6-e, 16/10: provisional, for the designer's review).
     */
    pacTargetBar: {
        balanced: 'bg-lf-success',
        excess: 'bg-lf-danger',
        missing: 'bg-lf-warning',
        unknown: 'bg-lf-secondary',
    },
    /** PAC asset distribution editor, total figure. */
    pacTargetTotal: {
        balanced: 'text-lf-success',
        excess: 'text-lf-danger',
        missing: 'text-lf-warning',
        unknown: 'text-lf-muted',
    },
    /**
     * Toasts: tints, like the banners (designer, round 3): the `X-soft` fill and its `X-line` edge (`ToastContainer`
     * adds the border width), the text in `X-on-soft`, the icon in `X`; the dismiss button and the countdown in the
     * same `X-on-soft`, the button's hover a step down the family, on `X-line`.
     */
    toast: {
        success: {
            container: 'bg-lf-success-soft border-lf-success-line text-lf-success-on-soft',
            icon: 'text-lf-success',
            dismiss: 'hover:bg-lf-success-line',
            track: 'bg-lf-success-on-soft/15',
            bar: 'bg-lf-success-on-soft/40',
        },
        error: {
            container: 'bg-lf-danger-soft border-lf-danger-line text-lf-danger-on-soft',
            icon: 'text-lf-danger',
            dismiss: 'hover:bg-lf-danger-line',
            track: 'bg-lf-danger-on-soft/15',
            bar: 'bg-lf-danger-on-soft/40',
        },
        warning: {
            container: 'bg-lf-warning-soft border-lf-warning-line text-lf-warning-on-soft',
            icon: 'text-lf-warning',
            dismiss: 'hover:bg-lf-warning-line',
            track: 'bg-lf-warning-on-soft/15',
            bar: 'bg-lf-warning-on-soft/40',
        },
        info: {
            container: 'bg-lf-info-soft border-lf-info-line text-lf-info-on-soft',
            icon: 'text-lf-info',
            dismiss: 'hover:bg-lf-info-line',
            track: 'bg-lf-info-on-soft/15',
            bar: 'bg-lf-info-on-soft/40',
        },
    },
    /** Import wizard, status of a report set. */
    reportSet: {
        loading: 'bg-lf-neutral text-lf-secondary',
        complete: 'bg-lf-success-soft text-lf-success-on-soft',
        incomplete: 'bg-lf-warning-soft text-lf-warning-on-soft',
        error: 'bg-lf-danger-soft text-lf-danger-on-soft',
    },
    /**
     * File-set badges in the files area. `combined` names a kind, not a state: the indigo of the fund category's roles
     * (D-T28, «da rivedere» with the designer).
     */
    fileSet: {
        combined: 'bg-lf-cat-fund-soft text-lf-cat-fund-on-soft',
        stale: 'bg-lf-warning-soft text-lf-warning-on-soft',
        usedInCombined: 'bg-lf-neutral text-lf-secondary',
        set: 'bg-lf-success-soft text-lf-success-on-soft',
        incomplete: 'bg-lf-danger-soft text-lf-danger-on-soft',
    },
    /** Asset chips of the risk panels (`AssetChip` adds the border widths and style). */
    riskAssetChip: {
        default: 'bg-lf-neutral text-lf-secondary',
        warning: 'border-lf-warning-line bg-lf-warning-soft text-lf-warning-on-soft',
        excluded: 'border-lf-subtle text-lf-muted',
    },
    /**
     * A chip or a button inside a banner (designer, round 3, proposal a): it stands on the card, out of the tint, with
     * its text in `X-on-soft`, 6.8–12.4:1 there, and its edge in `X`, 4.6–9.6:1 on the card and on the tint: the
     * developer and the designer chose it on 17/10 (T3-b) over the `X-line` of her proposal, 1.1–1.6:1, under the
     * 3:1 of a control's border. `hover` is a step into the family, the `X-soft` fill: a button takes it, a pill
     * that is no control does not. The component adds the border width.
     */
    bannerChip: {
        success: {base: 'border-lf-success bg-lf-card text-lf-success-on-soft', hover: 'hover:bg-lf-success-soft'},
        warning: {base: 'border-lf-warning bg-lf-card text-lf-warning-on-soft', hover: 'hover:bg-lf-warning-soft'},
        danger: {base: 'border-lf-danger bg-lf-card text-lf-danger-on-soft', hover: 'hover:bg-lf-danger-soft'},
        info: {base: 'border-lf-info bg-lf-card text-lf-info-on-soft', hover: 'hover:bg-lf-info-soft'},
    },
    /**
     * Data-quality banners (`DataQualityBanner`, `LotDataQualityBanner`): each severity in its own state since round
     * 3, through `DATA_QUALITY_TONE` — before, errors shared the warning tone. A grouped banner takes the tone of its
     * worst issue and each row the tone of its own; their chips and buttons are `bannerChip`. The rule for any banner
     * (the developer, 17/10): red for a real error, one that stops a calculation or makes it wrong; amber for missing
     * data, which once supplied lets the work go on; blue for information and notes; green for a success.
     */
    dataQuality: {
        danger: {container: 'bg-lf-danger-soft border-lf-danger-line text-lf-danger-on-soft', icon: 'text-lf-danger', divider: 'border-lf-danger-line'},
        warning: {container: 'bg-lf-warning-soft border-lf-warning-line text-lf-warning-on-soft', icon: 'text-lf-warning', divider: 'border-lf-warning-line'},
        info: {container: 'bg-lf-info-soft border-lf-info-line text-lf-info-on-soft', icon: 'text-lf-info', divider: 'border-lf-info-line'},
    },
    /** The «Updates paused» pill of the live prices: a neutral chip. */
    liveUpdates: {
        paused: 'bg-lf-neutral text-lf-secondary',
    },
} as const;

/**
 * The state a data-quality severity is drawn in (designer, round 3): an error in danger, a warning in warning, an info
 * in info. Which conditions are errors is the backend's call, condition by condition (17/10: the portfolio's missing
 * price and the four codes that fail the lots' replay are errors; the risk lab's missing price is a warning).
 */
export const DATA_QUALITY_TONE = {error: 'danger', warning: 'warning', info: 'info'} as const;

/**
 * Badges that tell kinds apart rather than states: one hue per kind, on the nearest category's roles (D-T28, «da
 * rivedere» with the designer): the edge is the category colour at 40 %.
 */
export const KIND_TONES = {
    /** Import wizard, identifier badges: ISIN blue (the ETF's), symbol violet (the stock's), name slate (the hold's). */
    identifier: {
        isin: 'border-lf-cat-etf/40 bg-lf-cat-etf-soft text-lf-cat-etf-on-soft',
        symbol: 'border-lf-cat-stock/40 bg-lf-cat-stock-soft text-lf-cat-stock-on-soft',
        name: 'border-lf-cat-hold/40 bg-lf-cat-hold-soft text-lf-cat-hold-on-soft',
    },
} as const;
