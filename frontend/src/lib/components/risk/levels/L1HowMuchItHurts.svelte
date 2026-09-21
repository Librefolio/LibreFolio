<script lang="ts">
    import RiskCardGrid from '$lib/components/ui/display/RiskCardGrid.svelte';
    import RiskMetricCard from '$lib/components/ui/display/RiskMetricCard.svelte';
    import {_ as t} from '$lib/i18n';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
    import {formatPercent} from '$lib/utils/core/formatPercent';

    import {formatCurrencyAmount} from '../riskAnalysisHelpers';
    import {buildCurrentDrawdown, buildHurtRows} from './levelHelpers';
    import {buildReturnHistogram, buildTailMeasures, buildUnderwater} from './l1/l1Helpers';
    import ReturnHistogram from './l1/ReturnHistogram.svelte';
    import UnderwaterChart from './l1/UnderwaterChart.svelte';

    /**
     * L1 — "how much can it hurt?"
     *
     * The old panel's defect was never that it showed a VaR. It was that it put a
     * one-day loss next to a multi-year drawdown without ever declaring the
     * change of scale, so the reader summed them in their head. The cure is a
     * single section with one explicit, increasing scale.
     *
     * Nothing in here is estimated: every figure is something the sample did.
     *
     * WHY CARDS AND NOT THE OLD LIST. The list pushed label and number to
     * opposite edges of the page, so three figures occupied a full-width band
     * with a void down the middle and the eye had to travel to pair them. The
     * grid packs each pair into one object, and - the part the list could not do
     * at all - gives every figure somewhere to put its second row.
     *
     * WHY THE ACQUIRED MEASURES ARE SECOND ROWS AND NEVER NEW CARDS.
     * `worst_realization`, `drawdown_at_risk` and `conditional_drawdown_at_risk`
     * are not three more risks: they are refinements of two that are already
     * here. The worst day *actually seen* only means something beside the worst
     * day the tail predicts; a drawdown-at-risk only means something beside the
     * drawdown that happened. Promoting them to cards of their own would restate
     * the very defect this section exists to cure - an undeclared change of scale.
     *
     * The fourth, `ulcer_index`, is the caption of the underwater chart rather
     * than a row anywhere: alone it is a dimensionless number nobody can read,
     * and the curve above it is literally the shape it measures.
     *
     * Pattern: Svelte 5 Runes, Tailwind CSS 4.
     */
    interface Props {
        historicalResults: RiskAnalyticResult[];
        /**
         * Scope value, used to put money next to every percentage.
         *
         * Optional, and when absent the money line simply does not appear. No
         * risk analytic carries an amount, so a figure here would have to be
         * invented, and an invented euro reads exactly like a measured one.
         */
        scopeValue?: number | null;
        currency: string;
        loading?: boolean;
    }

    let {historicalResults, scopeValue = null, currency, loading = false}: Props = $props();

    let rows = $derived(buildHurtRows(historicalResults));
    let current = $derived(buildCurrentDrawdown(historicalResults));
    let tails = $derived(buildTailMeasures(historicalResults));
    let underwater = $derived(buildUnderwater(historicalResults));
    let histogram = $derived(buildReturnHistogram(historicalResults));
    let showMoney = $derived(typeof scopeValue === 'number' && Number.isFinite(scopeValue) && scopeValue > 0);

    /**
     * A loss magnitude rendered as a fall.
     *
     * The minus is prefixed here, as U+2212 MINUS SIGN, rather than left to the
     * formatter: `formatPercent` emits an ASCII hyphen, and this panel's E2E net
     * asserts the typographic minus. Both characters draw as a short horizontal
     * stroke, so a mismatch is invisible on screen and surfaces only as a failing
     * string comparison.
     */
    function lossPercent(fraction: number): string {
        return `\u2212${formatPercent(fraction, {scale: 100, signed: false, digits: 1})}`;
    }

    /** A gain magnitude rendered as a rise, with the matching plus. */
    function gainPercent(fraction: number): string {
        return `+${formatPercent(fraction, {scale: 100, signed: false, digits: 1})}`;
    }

    /** The money a loss fraction costs at the current scope value. */
    function lossMoney(fraction: number): string {
        if (!showMoney || scopeValue == null) return '';
        return `\u2212${formatCurrencyAmount(String(scopeValue * fraction), currency)}`;
    }

    /**
     * The card caption, never an empty string.
     *
     * `RiskMetricCard` renders the caption behind an `{#if}`, so an empty string
     * removes the element and the card loses a line of height the moment money
     * becomes available. A non-breaking space keeps the line reserved and
     * invisible. This is the caller's half of the card's no-shift guarantee: the
     * card can only promise not to resize the value line.
     */
    function caption(text: string): string {
        return text === '' ? '\u00A0' : text;
    }

    /** The confidence the backend actually used, never the 95% one might assume. */
    let confidenceLabel = $derived(tails.drawdownConfidence === null ? '\u2014' : formatPercent(tails.drawdownConfidence, {scale: 100, signed: false, digits: 0}));

    /**
     * Documentation is per card, never one generic link for the section.
     *
     * These are MkDocs directory URLs, and every one was verified to exist as a
     * page and to be reachable from the nav. The three they replace pointed at
     * `user/analysis/risk.md#...`, where no such page exists: `check-links` never
     * saw them because the old markup passed `path={expression}` and the gate
     * only reads literals.
     */
    const DOCS = 'financial-theory/technical-analysis/risk-metrics';
    const DOC_PATHS: Record<string, string> = {
        day: `${DOCS}/conditional-value-at-risk/`,
        month: `${DOCS}/conditional-value-at-risk/`,
        worst: `${DOCS}/max-drawdown/`,
    };
</script>

{#snippet measure(label: string, value: string, testId: string, docsPath?: string)}
    <div class="flex items-baseline justify-between gap-2 text-xs" data-testid={testId}>
        <span class="flex min-w-0 items-center gap-1">
            <span class="truncate text-gray-500 dark:text-gray-400">{label}</span>
            {#if docsPath}
                <a class="shrink-0 text-gray-400 hover:text-blue-500 dark:text-gray-500" href="/mkdocs/{docsPath}" target="_blank" rel="noopener noreferrer" aria-label={label} data-testid="{testId}-docs">&#9432;</a>
            {/if}
        </span>
        <span class="shrink-0 font-medium text-gray-700 tabular-nums dark:text-gray-300">{value}</span>
    </div>
{/snippet}

<div class="space-y-4" data-testid="risk-l1">
    {#if loading && rows.length === 0}
        <div data-testid="risk-l1-loading">
            <RiskCardGrid>
                {#each [0, 1, 2, 3] as placeholder (placeholder)}
                    <RiskMetricCard label={'\u00A0'} value={'\u2014'} caption={'\u00A0'} loading testId="risk-l1-card-skeleton-{placeholder}" />
                {/each}
            </RiskCardGrid>
        </div>
    {:else if rows.length === 0}
        <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="risk-l1-empty">{$t('risk.states.unavailable')}</p>
    {:else}
        <div data-testid="risk-l1-cards">
            <RiskCardGrid>
                {#each rows as row (row.id)}
                    <RiskMetricCard label={$t(`risk.levels.l1.rows.${row.id}`)} technicalName={$t(`risk.levels.l1.technical.${row.id}`)} value={lossPercent(row.loss)} caption={caption(lossMoney(row.loss))} sentiment="negative" docsPath={DOC_PATHS[row.id]} testId="risk-l1-card-{row.id}">
                        {#snippet submetrics()}
                            {#if row.durationDays != null}
                                {@render measure($t('risk.levels.l1.durationDays', {values: {days: row.durationDays}}), '', `risk-l1-duration-${row.id}`)}
                            {/if}
                            {#if row.requiredRecovery != null}
                                <!-- The number that teaches the asymmetry: a 50% fall
                                     needs a +100% rise, not a +50% one. -->
                                {@render measure($t('risk.levels.l1.requiredRecovery', {values: {percent: ''}}), gainPercent(row.requiredRecovery), `risk-l1-recovery-${row.id}`)}
                            {/if}

                            <!-- The acquired measures, each attached to the figure it
                                 refines instead of standing on its own. -->
                            {#if row.id === 'day' && tails.worstRealization !== null}
                                {@render measure($t('risk.levels.l1.tails.worstRealization'), lossPercent(tails.worstRealization), 'risk-l1-worst-realization', `${DOCS}/worst-realization/`)}
                                {#if tails.worstRealizationDate}
                                    <p class="text-right text-[10px] text-gray-400 dark:text-gray-500" data-testid="risk-l1-worst-realization-date">{$t('risk.levels.l1.tails.worstRealizationOn', {values: {date: tails.worstRealizationDate}})}</p>
                                {/if}
                            {/if}
                            {#if row.id === 'worst' && tails.drawdownAtRisk !== null}
                                {@render measure($t('risk.levels.l1.tails.drawdownAtRisk', {values: {confidence: confidenceLabel}}), lossPercent(tails.drawdownAtRisk), 'risk-l1-drawdown-at-risk', `${DOCS}/drawdown-at-risk/`)}
                            {/if}
                            {#if row.id === 'worst' && tails.conditionalDrawdownAtRisk !== null}
                                {@render measure($t('risk.levels.l1.tails.conditionalDrawdownAtRisk'), lossPercent(tails.conditionalDrawdownAtRisk), 'risk-l1-conditional-drawdown-at-risk', `${DOCS}/conditional-drawdown-at-risk/`)}
                            {/if}
                        {/snippet}
                    </RiskMetricCard>
                {/each}

                {#if current}
                    <RiskMetricCard label={$t('risk.levels.l1.currentDrawdown')} technicalName={$t('risk.levels.l1.technical.current')} value={lossPercent(current.loss)} caption={caption(lossMoney(current.loss))} sentiment="negative" docsPath="{DOCS}/current-drawdown/" testId="risk-l1-card-current">
                        {#snippet submetrics()}
                            {#if current.peakDate}
                                {@render measure($t('risk.levels.l1.sincePeak', {values: {date: current.peakDate}}), '', 'risk-l1-current-since')}
                            {/if}
                            {#if current.requiredRecovery != null}
                                {@render measure($t('risk.levels.l1.requiredRecovery', {values: {percent: ''}}), gainPercent(current.requiredRecovery), 'risk-l1-current-recovery')}
                            {/if}
                        {/snippet}
                    </RiskMetricCard>
                {/if}
            </RiskCardGrid>
        </div>

        <UnderwaterChart points={underwater} ulcerIndex={tails.ulcerIndex} />

        <ReturnHistogram {histogram} />
    {/if}
</div>
