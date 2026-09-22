<script lang="ts">
    import {schemas} from '$lib/api';
    import RiskCardGrid from '$lib/components/ui/display/RiskCardGrid.svelte';
    import RiskMetricCard from '$lib/components/ui/display/RiskMetricCard.svelte';
    import KpiDivergingFlowBar from '$lib/components/ui/display/KpiDivergingFlowBar.svelte';
    import {_ as t} from '$lib/i18n';
    import {riskOutput} from '$lib/risk/riskTypes';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
    import {formatPercent} from '$lib/utils/core/formatPercent';

    import CorrelationHeatmap from '../CorrelationHeatmap.svelte';
    import {buildLookup, NEAR_IDENTICAL, topPairs} from '../correlationHelpers';
    import {buildConcentration, buildDivergenceRows, uncoveredWeight} from './levelHelpers';

    /**
     * L2 — "am I diversified like I think I am?"
     *
     * The cheapest valuable picture in the whole subsystem: `weight` and
     * `percentage_contribution` both already travel in the payload, and `weight`
     * is currently thrown away. Risk contribution on its own does not answer the
     * question — the answer is the *gap* between what a holding weighs and how
     * much risk it produces.
     *
     * The bar is two-sided because that gap has two directions, and the second
     * one is the half that gets forgotten. On the seeded portfolio one holding
     * weighs a small fraction of the book and produces most of its risk, while
     * the LARGEST holding produces almost none. The first says "I am
     * concentrated where I did not think I was"; the second says "and I am
     * absent where I thought I was exposed". Neither a pie nor a treemap can
     * draw the second, which is why neither is allowed here.
     *
     * The measured figures are deliberately NOT written here. A weight and a
     * risk share both integrate over the query window, and the window is a
     * choice of the page rather than a property of the data: two readers of the
     * same screen on the same day, over different intervals, see different
     * numbers, and neither is wrong. A figure pinned in a comment would go on
     * reading as a fact long after it stopped being one. They live, dated and
     * with the command that produced them, in
     * `implementation_2/progress/S2-esecuzione.md`.
     *
     * Three cards sit above the list because the list cannot answer a
     * portfolio-level question. `buildConcentration` and `uncoveredWeight` were
     * both written and unit-tested and then rendered by nobody; this is the
     * first surface that reads them.
     */
    interface Props {
        /**
         * Risk contribution over the scope.
         *
         * PORTFOLIO-only by contract (`risk_contribution.py:46`), and measured:
         * an `asset_set` asking for it is answered `unavailable` /
         * `incompatible_scope`. Everything derived from it — the three cards and
         * every row — is therefore absent on that scope rather than empty, which
         * is why none of them gates the matrix below.
         */
        contributionResult: RiskAnalyticResult | null;
        /**
         * The correlation matrix over the same scope.
         *
         * Already travels in the historical wave the panel requests — it is
         * `add('correlation')` in `buildBaseAnalytics` — and until now no level
         * rendered it, so the answer was fetched and thrown away. Taking it as a
         * prop therefore costs nothing on the wire.
         *
         * `null` is a legitimate state and not a fault: a scope that does not
         * advertise the capability simply shows no matrix.
         */
        correlationResult?: RiskAnalyticResult | null;
        /** Display names by asset id; an id with no name falls back to `#id`. */
        assetNames?: Record<number, string>;
        loading?: boolean;
        /** Rows shown before the "show all" control; the rest stay one click away. */
        visibleRows?: number;
    }

    let {contributionResult, correlationResult = null, assetNames = {}, loading = false, visibleRows = 8}: Props = $props();

    let rows = $derived(buildDivergenceRows(contributionResult));
    /**
     * The share of NAV these rows do not describe.
     *
     * Read with `!== null`, never `?? 0`: the field carries a schema default, so
     * the generated type offers `undefined` even though the server always sends
     * it, and the fallback that type invites — zero — reads as "nothing
     * uncovered". That is precisely the reassurance this line exists to withhold.
     */
    let uncovered = $derived(uncoveredWeight(contributionResult));
    let concentration = $derived(buildConcentration(contributionResult));
    let expanded = $state(false);
    let shown = $derived(expanded ? rows : rows.slice(0, visibleRows));

    /** The widest gap on show, so every row is drawn against one scale. */
    let scale = $derived(Math.max(0.01, ...rows.map((row) => Math.abs(row.divergence))));

    let correlation = $derived(riskOutput(correlationResult, schemas.RiskCorrelationOutput));
    /** The heatmap takes a Map; the panel hands every level a Record. */
    let assetLabels = $derived(new Map(Object.entries(assetNames).map(([assetId, label]) => [Number(assetId), label])));

    /**
     * Whether any pair in this scope reaches the redundancy threshold.
     *
     * Rendered as a *declaration* rather than left as an absence, because a
     * matrix with nothing in it and a matrix that failed to compute look
     * identical to a reader. On the seeded data nothing reaches it — every mock
     * asset is generated with independent noise, so the fake market has no
     * common factor. An empty answer that says it is empty is an answer; an
     * empty answer that says nothing is a suspicion.
     *
     * Deliberately a boolean and not the strongest coefficient: a figure quoted
     * here would move with the query window and read as a fact that does not hold.
     */
    let hasRedundantPair = $derived.by(() => {
        if (!correlation) return true;
        const {correlated} = topPairs(correlation.asset_ids, buildLookup(correlation.cells), 1);
        return (correlated[0]?.value ?? 0) >= NEAR_IDENTICAL;
    });

    function name(assetId: number): string {
        return assetNames[assetId] ?? `#${assetId}`;
    }

    /**
     * How to read `N_eff` against the number of positions on screen.
     *
     * The figure is not a count and routinely exceeds the holdings — measured
     * here at 14.97 over 7 — and that is the documented convention, not a
     * defect: weights are position value over TOTAL NAV, so cash dilutes every
     * weight without contributing a square of its own
     * (`concentration.en.md#where-cash-sits`). Adding cash scales the count by
     * `1/s²`, and with `s` near a half that is roughly a fourfold inflation.
     *
     * Putting the two numbers side by side makes the gap visible, which is only
     * half the job: the gap means opposite things in its two directions, and the
     * same page states which (`#interpretation`). ABOVE the count, the excess is
     * cash and says nothing about how the weights are spread. BELOW it, the
     * weights are lopsided and a few positions carry the portfolio. A caption
     * that shows the comparison without its rule leaves the reader to guess the
     * direction, and the wrong guess reads as "the software is broken".
     *
     * Equality is neither case — even weights and no cash — so it gets its own
     * sentence rather than being folded into a branch it would falsify.
     *
     * The comparison is against the positions THIS LEVEL MEASURED, which is what
     * the reader can count underneath. A holding excluded for want of a usable
     * price series is not among them; it is in the uncovered card instead.
     */
    let effectiveAssetsReading = $derived.by(() => {
        if (!concentration) return '';
        const positions = rows.length;
        const effective = concentration.effectiveNumberOfAssets;
        const key = effective > positions ? 'aboveCount' : effective < positions ? 'belowCount' : 'evenCount';
        return $t(`risk.levels.l2.effectiveAssets.${key}`, {values: {positions}});
    });

    /** A share of the portfolio: one decimal, never signed — a weight has no direction. */
    function share(fraction: number): string {
        return formatPercent(fraction, {scale: 100, signed: false, digits: 1});
    }

    /**
     * A gap between two shares, in percentage POINTS.
     *
     * The unit is the whole point: a 20% weight against an 80% share of risk
     * differ by 60 *points*, and writing that as `+60%` states a different
     * quantity. The illustration is round and invented on purpose — a measured
     * pair would integrate over the query window, and a comment cannot carry a
     * figure that moves.
     *
     * The sign is composed here instead of being left to `formatPercent` because
     * the negative case must print U+2212, the typographic minus this column has
     * always shown. A hyphen is narrower than the plus it sits under, so the
     * column stops aligning the moment one is substituted for the other.
     */
    function points(fraction: number): string {
        const sign = fraction >= 0 ? '+' : '−';
        return `${sign}${formatPercent(Math.abs(fraction), {scale: 100, signed: false, digits: 1, suffix: 'pp'})}`;
    }

    /** The diverging bar wants -100..100; the shared scale keeps rows comparable. */
    function barPercent(divergence: number): number {
        return (divergence / scale) * 100;
    }

    /**
     * Two decimals for an index that is not a percentage.
     *
     * Goes through `formatPercent` with the unit switched off rather than
     * `toLocaleString`, and the reason is a defect this file briefly had.
     *
     * `toLocaleString(undefined, …)` formats in the BROWSER's locale, so on an
     * Italian browser it writes `14,97` while every percentage beside it —
     * `formatPercent`, which ends in `toFixed` — writes `49.3%`. The two sat in
     * the same row of cards, three centimetres apart, under an Italian
     * interface: one comma, two dots.
     *
     * The app-locale-versus-browser-locale split is a known debt and it is not
     * this surface's to pay. What this surface must not do is DOUBLE it: a
     * second, parallel formatting path turns one debt in one place into two
     * conventions disagreeing on one screen, which is harder to fix and worse to
     * read. One convention, one owner, one repair.
     */
    function index(value: number): string {
        return formatPercent(value, {signed: false, digits: 2, suffix: ''});
    }
</script>

<div class="space-y-4" data-testid="risk-l2">
    {#if loading && rows.length === 0 && !correlation}
        <div class="space-y-2" data-testid="risk-l2-loading">
            {#each [0, 1, 2] as placeholder (placeholder)}
                <div class="h-8 animate-pulse rounded bg-gray-100 dark:bg-slate-700"></div>
            {/each}
        </div>
    {:else}
        <!-- Every block below stands on its own measurement, and that is the
             whole structure of this file.
             `risk_contribution` is PORTFOLIO-only — measured: an asset_set asked
             for it comes back `unavailable` / `incompatible_scope` — while
             `correlation` serves both scopes. Gating the level on the
             contribution, as it used to be, would hide the matrix precisely on
             the scope where the matrix is the only thing there is to show.
             A card whose metric does not exist in this scope therefore does not
             render: not as zero, and not as a dash. What is missing and why is
             already disclosed by RiskLevelSection, which reads the same result. -->
        {#if concentration || uncovered !== null}
            <!-- `caption` is supplied during `loading` too — empty, but present —
                 because the card only guarantees the VALUE line does not move; a
                 caption that arrives late makes the card grow under the reader. -->
            <RiskCardGrid testId="risk-l2-metrics" minWidth="17rem">
                {#if concentration}
                    <RiskMetricCard
                        label={$t('risk.levels.l2.effectiveAssets.label')}
                        technicalName="N_eff"
                        numericValue={concentration?.effectiveNumberOfAssets}
                        formatValue={index}
                        caption={loading ? '' : effectiveAssetsReading}
                        docsPath="financial-theory/technical-analysis/risk-metrics/concentration/"
                        {loading}
                        testId="risk-l2-card-effective-assets"
                    />
                    <RiskMetricCard
                        label={$t('risk.levels.l2.diversificationRatio.label')}
                        technicalName="DR"
                        numericValue={concentration?.diversificationRatio}
                        formatValue={index}
                        caption={loading ? '' : $t('risk.levels.l2.diversificationRatio.caption')}
                        docsPath="financial-theory/technical-analysis/risk-metrics/concentration/"
                        {loading}
                        testId="risk-l2-card-diversification-ratio"
                    />
                {/if}
                {#if uncovered !== null}
                    <!-- Promoted from a footnote to a card. The figure was already
                         on screen, in 12px grey under the legend, while it decides
                         how much of the reader's money the rest of this level is
                         even about. -->
                    <RiskMetricCard
                        label={$t('risk.levels.l2.uncovered.label')}
                        technicalName={$t('risk.metrics.cashWeight')}
                        numericValue={uncovered ?? undefined}
                        formatValue={share}
                        caption={loading ? '' : $t('risk.levels.l2.uncovered.caption')}
                        docsPath="financial-theory/technical-analysis/risk-metrics/risk-contribution/"
                        {loading}
                        testId="risk-l2-card-uncovered"
                    />
                {/if}
            </RiskCardGrid>
        {/if}

        {#if uncovered !== null}
            <!-- Kept as well as promoted: `data-uncovered` publishes the raw
                 fraction, which is what a test reads instead of going through a
                 formatted, translated string. -->
            <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l2-uncovered" data-uncovered={uncovered}>
                {$t('risk.levels.l2.uncovered.residual', {values: {share: share(uncovered)}})}
            </p>
        {/if}

        {#if rows.length > 0}
            <div class="space-y-2">
                <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l2-rows-caption">{$t('risk.levels.l2.rowsCaption')}</p>
                <ul class="space-y-3" data-testid="risk-l2-rows">
                    {#each shown as row (row.assetId)}
                        <li class="space-y-1" data-testid="risk-l2-row-{row.assetId}">
                            <!-- One bar, two directions, one shared scale. The gap
                                 IS the answer, so the gap is what gets drawn;
                                 weight and contribution stay underneath as the two
                                 numbers it was computed from. -->
                            <KpiDivergingFlowBar
                                layout="inline"
                                label={name(row.assetId)}
                                value={points(row.divergence)}
                                valueTestId="risk-l2-divergence-{row.assetId}"
                                signedPct={barPercent(row.divergence)}
                                positiveColor="bg-red-500 dark:bg-red-400"
                                negativeColor="bg-emerald-500 dark:bg-emerald-400"
                                valueColor={row.divergence > 0 ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}
                                valueClass="tabular-nums font-semibold"
                                testId="risk-l2-divergence-bar-{row.assetId}"
                            />
                            <div class="flex justify-end gap-4 text-xs text-gray-500 dark:text-gray-400">
                                <span>
                                    {$t('risk.levels.l2.weight')}
                                    <span class="tabular-nums text-gray-700 dark:text-gray-200" data-testid="risk-l2-weight-{row.assetId}">{share(row.weight)}</span>
                                </span>
                                <span>
                                    {$t('risk.levels.l2.contribution')}
                                    <span class="tabular-nums text-gray-700 dark:text-gray-200" data-testid="risk-l2-contribution-{row.assetId}">{share(row.contribution)}</span>
                                </span>
                            </div>
                        </li>
                    {/each}
                </ul>
            </div>

            {#if rows.length > visibleRows}
                <button type="button" class="text-xs text-libre-green hover:underline" onclick={() => (expanded = !expanded)} data-testid="risk-l2-toggle-all">
                    {expanded ? $t('risk.levels.l2.showLess') : $t('risk.levels.l2.showAll')}
                </button>
            {/if}
        {:else}
            <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="risk-l2-empty">{$t('risk.states.unavailable')}</p>
        {/if}

        {#if correlation}
            <!-- The second half of the level, which the design always assigned to
                 it and which had never been mounted anywhere but the legacy panel:
                 the list above says how much each holding contributes, this says
                 which holdings are the same bet. -->
            <div class="space-y-2 border-t border-gray-100 pt-4 dark:border-slate-700" data-testid="risk-l2-correlation">
                <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200">{$t('risk.levels.l2.correlation.title')}</h4>
                <p class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l2.correlation.basis')}</p>
                {#if !hasRedundantPair}
                    <!-- An empty matrix and a broken one look alike, so the empty
                         one says so. The claim is about the SHAPE of the answer
                         and never about a coefficient. -->
                    <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l2-correlation-no-redundancy">
                        {$t('risk.levels.l2.correlation.noRedundancy')}
                    </p>
                {/if}
                <CorrelationHeatmap output={correlation} {assetLabels} height="360px" />
            </div>
        {/if}
    {/if}
</div>
