<script lang="ts">
    import RiskCardGrid from '$lib/components/ui/display/RiskCardGrid.svelte';
    import RiskMetricCard from '$lib/components/ui/display/RiskMetricCard.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {formatDay, formatDayRange} from '$lib/utils/core/formatAxisDate';
    import {formatFixed} from '$lib/utils/core/formatFixed';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';

    import {amountOnValue, formatCurrencyAmount} from '../riskAnalysisHelpers';
    import {omegaFigure, type MoveColumn, type MoveFigures, type ScopeMoveFigures} from '../moveFigures';
    import {figurePercent, gainPercent, signedAmount} from './l1/l1Helpers';
    import {withRateKey} from '../riskFreeRate';

    /**
     * «How does it move?» (RN-18; Q21 c, Q22 a) — the four green twins of «How much can it hurt?»: the best day, thirty
     * good days, the largest rally, and what the days were like. The same block on the Dashboard, a broker's page and an
     * asset's page, between L1 and the next level.
     *
     * It shows only the positive: volatility, annual return, Sharpe and Sortino live in L3's table on every surface (on
     * one asset since RN-17, the asset's own row) — one figure, one place (Q22, the consultant on 17/11/2026).
     *
     * Every figure is something the sample did, read by `moveFigures.ts` from the answers L1 already reads: the block
     * asks nothing of its own. A blank says why, with the backend's warning; the money, when the page states a value, is
     * that value times the figure, as L1's.
     *
     * Pattern: Svelte 5 Runes, Tailwind CSS 4.
     */
    interface Props {
        /** The figures of the scope, or null when none of the three answers came back. */
        figures: ScopeMoveFigures | null;
        /** The value the amounts are on (your position on one asset, the scope's worth on a portfolio); none without it. */
        scopeValue?: number | null;
        currency: string;
        loading?: boolean;
        /**
         * The block's swing and L3's volatility read two series (`semiDeviationPerimeterDiffers`): the semi-deviation's
         * tooltip then says the perimeter of each (RN-18b); otherwise it is the usual help.
         */
        perimeterDiffers?: boolean;
    }

    let {figures, scopeValue = null, currency, loading = false, perimeterDiffers = false}: Props = $props();

    type Sentiment = 'positive' | 'negative' | 'neutral';

    /** The tone of a figure that can go either way: its own sign, never a fixed green (the best 30 days can be a loss). */
    function sentimentOf(value: number | null): Sentiment {
        return value === null || value === 0 ? 'neutral' : value > 0 ? 'positive' : 'negative';
    }

    /** A figure that can go either way: «+» before a gain, U+2212 before a loss, nothing before a zero (D380). */
    function signedPercent(value: number | null): string {
        return value === null ? '—' : gainPercent(value);
    }

    /** The money of a figure on the value the page states, signed; empty without a value. */
    function money(fraction: number | null): string {
        const amount = fraction === null ? null : amountOnValue(fraction, scopeValue);
        return amount === null ? '' : signedAmount(amount, (value) => formatCurrencyAmount(value, currency));
    }

    /** The caption, never an empty string: `RiskMetricCard` drops an empty one and the card would lose a line (L1's rule). */
    function caption(text: string): string {
        return text === '' ? ' ' : text;
    }

    /** A blank figure's caption is its reason, the backend's own warning; otherwise the given text. */
    function captionOr(column: MoveColumn, value: number | null, text: string): string {
        const reason = value === null ? figures?.reasons[column] : undefined;
        return caption(reason ? $t(reason) : text);
    }

    /** The largest rally's money is the same rise on today's value (C8's twin). */
    function sameRiseToday(amount: string): string {
        return amount === '' ? '' : $t('risk.levels.move.sameRiseToday', {values: {amount}});
    }

    let rally = $derived(figures?.rally ?? null);
    let bestMonth = $derived(figures?.bestMonth ?? null);
    let hasAverageDay = $derived(figures !== null && (figures.meanUp !== null || figures.meanDown !== null || figures.reasons.meanUp !== undefined || figures.reasons.meanDown !== undefined));

    /** The reasons of a row's blank parts, the backend's warnings, once each; empty when every part has its figure. */
    function reasonOf(columns: readonly MoveColumn[]): string {
        if (!figures) return '';
        const keys = [...new Set(columns.filter((column) => figures[column as keyof MoveFigures] === null).map((column) => figures.reasons[column]))].filter((key): key is string => key !== undefined);
        return keys.map((key) => $t(key)).join(' ');
    }

    /**
     * The semi-deviation read against the swing it is part of (Q23 a; the consultant, 17/11/2026): «downward 9.8% · out of
     * a 13.9% swing», both from the same historical KPI — a comparison, not the scope's volatility, which L3 states on its
     * own perimeter. Alone when the volatility did not come back. With a risk-free rate (RN-21) it counts the days below
     * it, and says so; at 0 it is today's sentence.
     */
    function semiDeviationText(down: number, swing: number | null, rate: number | null): string {
        return swing === null ? figurePercent(down) : $t(withRateKey('risk.levels.move.rows.semiDeviationValue', rate), {values: {down: figurePercent(down), swing: figurePercent(swing)}});
    }

    /** The row's help: its perimeter when the two series differ (RN-18b), with the rate's sentence after it (RN-21); otherwise what a semi-deviation is. */
    function semiDeviationHelp(rate: number | null): string {
        if (!perimeterDiffers) return $t(withRateKey('risk.assetSet.levels.move.columnHelp.downsideDeviation', rate));
        const perimeter = $t('risk.levels.move.rows.semiDeviationPerimeter');
        return rate ? `${perimeter} ${$t('risk.levels.move.rows.semiDeviationBelowRate')}` : perimeter;
    }

    /** The semi-deviation is the Sortino's denominator: its page explains it (as the lab's column links it). */
    const SEMI_DEVIATION_DOCS = {docsPath: 'financial-theory/technical-analysis/risk-metrics/sortino-ratio/#downside-deviation'};
</script>

{#snippet measure(label: string, value: string, testId: string, docsPath?: string, period?: {from: string; to: string}, reason?: string, help?: string)}
    <!-- One detail row, the same as L1's (F8): the label on the left, the value on the right; a text that does not fit scrolls. -->
    <div class="flex items-baseline justify-between gap-2 text-xs" data-testid={testId} data-from={period?.from} data-to={period?.to}>
        <span class="flex min-w-0 flex-1 items-center gap-1">
            {#if help}
                <!-- RN-18b: the figure's perimeter, said where it is read (the consultant, 17/11/2026). -->
                <Tooltip text={help} position="top" testId="{testId}-help"><span class="text-lf-muted underline decoration-dotted underline-offset-2">{label}</span></Tooltip>
            {:else}
                <span use:scrollOnOverflow class="{overflowScrollTextClass} text-lf-muted">{label}</span>
            {/if}
            {#if docsPath}
                <a class="shrink-0 text-lf-muted hover:text-lf-link" href="/mkdocs/{docsPath}" target="_blank" rel="noopener noreferrer" aria-label={label} data-testid="{testId}-docs">&#9432;</a>
            {/if}
        </span>
        <span use:scrollOnOverflow class="{overflowScrollTextClass} max-w-[65%] shrink-0 text-right font-medium text-lf-secondary tabular-nums" data-testid="{testId}-value">{value}</span>
    </div>
    {#if reason}
        <!-- Q20: a blank row says why, in a line of its own (a tooltip is not there on a phone). -->
        <p class="text-[10px] text-lf-muted" data-testid="{testId}-reason">{reason}</p>
    {/if}
{/snippet}

<div class="space-y-4" data-testid="risk-move" data-risk-free-rate={figures?.riskFreeRate ?? ''}>
    {#if loading && figures === null}
        <div data-testid="risk-move-loading">
            <RiskCardGrid>
                {#each [0, 1, 2, 3] as placeholder (placeholder)}
                    <RiskMetricCard label={' '} value={'—'} caption={' '} loading testId="risk-move-card-skeleton-{placeholder}" />
                {/each}
            </RiskCardGrid>
        </div>
    {:else if figures === null}
        <p class="text-sm text-lf-muted" data-testid="risk-move-empty">{$t('risk.states.unavailable')}</p>
    {:else}
        <div data-testid="risk-move-cards">
            <RiskCardGrid>
                <RiskMetricCard
                    layout="figure"
                    label={$t('risk.levels.move.cards.bestDay')}
                    technicalName={$t('risk.levels.move.technical.bestDay')}
                    value={signedPercent(figures.bestDay)}
                    caption={captionOr('bestDay', figures.bestDay, money(figures.bestDay))}
                    sentiment={sentimentOf(figures.bestDay)}
                    testId="risk-move-card-bestDay"
                >
                    {#snippet submetrics()}
                        {#if figures.bestDayDate}
                            {@render measure($t('risk.levels.l1.when'), formatDay(figures.bestDayDate), 'risk-move-best-day-date')}
                        {/if}
                        {#if hasAverageDay}
                            {@render measure($t('risk.levels.move.rows.meanUpDown'), $t('risk.levels.move.rows.meanUpDownValue', {values: {up: signedPercent(figures.meanUp), down: signedPercent(figures.meanDown)}}), 'risk-move-mean-up-down', undefined, undefined, reasonOf(['meanUp', 'meanDown']))}
                        {/if}
                    {/snippet}
                </RiskMetricCard>

                <RiskMetricCard
                    layout="figure"
                    label={$t('risk.levels.move.cards.bestMonth')}
                    technicalName={$t('risk.levels.move.technical.bestMonth')}
                    value={signedPercent(bestMonth?.gain ?? null)}
                    caption={caption(money(bestMonth?.gain ?? null))}
                    sentiment={sentimentOf(bestMonth?.gain ?? null)}
                    testId="risk-move-card-bestMonth"
                >
                    {#snippet submetrics()}
                        {#if bestMonth}
                            {@render measure($t('risk.levels.l1.when'), formatDayRange(bestMonth.from, bestMonth.to), 'risk-move-best-month-period', undefined, bestMonth)}
                        {/if}
                    {/snippet}
                </RiskMetricCard>

                <RiskMetricCard
                    layout="figure"
                    label={$t('risk.levels.move.cards.rally')}
                    technicalName={$t('risk.levels.move.technical.rally')}
                    value={signedPercent(rally?.gain ?? null)}
                    caption={caption(sameRiseToday(money(rally?.gain ?? null)))}
                    sentiment={sentimentOf(rally?.gain ?? null)}
                    testId="risk-move-card-rally"
                >
                    {#snippet submetrics()}
                        {#if rally?.from && rally.to}
                            {@render measure($t('risk.levels.l1.when'), formatDayRange(rally.from, rally.to), 'risk-move-rally-period', undefined, {from: rally.from, to: rally.to})}
                        {/if}
                        {#if rally && rally.gain > 0 && rally.days !== null}
                            {@render measure($t('risk.levels.l1.duration'), $t('risk.levels.l1.daysCount', {values: {days: rally.days}}), 'risk-move-rally-duration')}
                        {/if}
                        {#if figures.streak}
                            {@render measure($t('risk.assetSet.levels.move.columns.streak'), `${$t('risk.assetSet.levels.move.days', {values: {days: figures.streak.days}})} · ${formatDayRange(figures.streak.from, figures.streak.to)}`, 'risk-move-streak', undefined, figures.streak)}
                        {:else if figures.reasons.streak}
                            {@render measure($t('risk.assetSet.levels.move.columns.streak'), '\u2014', 'risk-move-streak', undefined, undefined, reasonOf(['streak']))}
                        {/if}
                    {/snippet}
                </RiskMetricCard>

                <RiskMetricCard
                    layout="figure"
                    label={$t('risk.levels.move.cards.days')}
                    technicalName={$t('risk.levels.move.technical.days')}
                    value={figures.omega === null ? '—' : $t('risk.assetSet.levels.move.times', {values: {value: omegaFigure(figures.omega)}})}
                    caption={captionOr('omega', figures.omega, figures.omega === null ? '' : $t('risk.levels.move.omegaCaption', {values: {value: omegaFigure(figures.omega)}}))}
                    testId="risk-move-card-days"
                >
                    {#snippet submetrics()}
                        {#if figures.positiveShare !== null}
                            {@render measure($t('risk.assetSet.levels.move.columns.positiveShare'), figurePercent(figures.positiveShare), 'risk-move-positive-share')}
                        {/if}
                        {#if figures.downsideDeviation !== null}
                            {@render measure($t('risk.levels.move.rows.semiDeviation'), semiDeviationText(figures.downsideDeviation, figures.volatility, figures.riskFreeRate), 'risk-move-semi-deviation', SEMI_DEVIATION_DOCS.docsPath, undefined, undefined, semiDeviationHelp(figures.riskFreeRate))}
                        {/if}
                        {#if figures.averageDrawdown !== null}
                            {@render measure($t('risk.levels.move.rows.averageDrawdown'), figurePercent(figures.averageDrawdown), 'risk-move-average-drawdown')}
                        {/if}
                        {#if figures.extremeDays !== null}
                            {@render measure($t('risk.assetSet.levels.move.columns.extremeDays'), $t('risk.levels.move.rows.extremeDaysValue', {values: {value: formatFixed(figures.extremeDays, 1)}}), 'risk-move-extreme-days')}
                        {:else if figures.reasons.extremeDays}
                            {@render measure($t('risk.assetSet.levels.move.columns.extremeDays'), '\u2014', 'risk-move-extreme-days', undefined, undefined, reasonOf(['extremeDays']))}
                        {/if}
                    {/snippet}
                </RiskMetricCard>
            </RiskCardGrid>
        </div>
    {/if}
</div>
