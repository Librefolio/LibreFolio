<script lang="ts">
    /**
     * L4Rates — the rates scenario of one asset (RN-25), a tool of its «What if…?».
     *
     * The backend computes it (`rate_shock`: −modified duration × the move, first order) for every step at once, in
     * the current-composition wave, from the duration of the asset's profile; this box says which duration it used
     * (source, day, years), lets the reader choose rates up or down by half a point, one point or two (the consultant,
     * 18/11/2026), and reads the figure of that move from the answer: the page computes nothing. The money is the
     * figure on the position the page states (`amountOnValue`, as the shock's), absent when it states none. A «now»
     * duration the source has not confirmed for more than 30 days (plan 68 D1d, `duration_stale`) is said not up to date,
     * with the day of its last confirmation, in the warning role, as the Profile says it (D1c).
     */
    import {onMount} from 'svelte';

    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {riskOutput} from '$lib/features/risk/riskTypes';
    import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';
    import {formatExactDecimal} from '$lib/utils/core/formatFixed';
    import {formatPercent} from '$lib/utils/core/formatPercent';

    import {dayFormatter} from '../../eligibility';
    import {amountOnValue, formatCurrencyAmount, RATE_SHOCK_STEPS} from '../../riskAnalysisHelpers';
    import {durationSourceName, enricherNamesVersion, ensureEnricherNames} from './durationSource';

    interface Props {
        result: RiskAnalyticResult | null;
        currency: string;
        /** The value of the position the page states, or null: percentages only. */
        scopeValue?: number | null;
        testId?: string;
    }

    let {result, currency, scopeValue = null, testId = 'risk-rates'}: Props = $props();

    /** The steps the backend is asked for, up and down (`RATE_SHOCK_STEPS`): the sizes the reader picks from. */
    const STEPS = RATE_SHOCK_STEPS.filter((move) => move > 0);
    const MINUS = '−';

    let direction = $state<'up' | 'down'>('up');
    let step = $state<number>(0.01);

    let output = $derived(riskOutput(result, schemas.RiskRateShockOutput));
    let move = $derived(direction === 'up' ? step : -step);
    let scenario = $derived(output?.scenarios.find((item) => item.yield_change === move) ?? null);

    let sourceLine = $derived.by(() => {
        void $enricherNamesVersion;
        if (!output) return '';
        return $t('risk.levels.l4.ratesSource', {
            values: {source: durationSourceName(output.duration_source, (key) => $t(key)), date: dayFormatter()(String(output.duration_read_on)), years: formatExactDecimal(output.modified_duration, {maxFrac: 2})},
        });
    });

    let staleLine = $derived(output?.duration_stale && output.duration_confirmed_on ? $t('risk.levels.l4.ratesStale', {values: {date: dayFormatter()(String(output.duration_confirmed_on))}}) : '');

    let percent = $derived(scenario === null ? '—' : `${scenario.price_change < 0 ? MINUS : '+'}${formatPercent(Math.abs(scenario.price_change), {scale: 100, signed: false, trim: true})}`);
    let amount = $derived.by(() => {
        const value = scenario === null ? null : amountOnValue(scenario.price_change, scopeValue);
        if (value === null) return null;
        return `${value < 0 ? MINUS : '+'}${formatCurrencyAmount(String(Math.abs(value)), currency)}`;
    });

    onMount(() => {
        void ensureEnricherNames();
    });
</script>

{#if output}
    <div class="space-y-2" data-testid={testId} data-direction={direction} data-step={step} data-source={output.duration_source} data-duration={output.modified_duration} data-stale={staleLine ? 'true' : 'false'}>
        <p class="text-xs text-lf-muted" data-testid="{testId}-source">{sourceLine}</p>
        {#if staleLine}
            <p class="text-xs text-lf-warning" data-testid="{testId}-stale">{staleLine}</p>
        {/if}
        <div class="flex flex-wrap items-center gap-2 text-sm text-lf-secondary">
            <div class="inline-flex overflow-hidden rounded-lg border border-lf-input" role="group">
                <button type="button" class="px-2.5 py-1 text-xs {direction === 'up' ? 'bg-lf-checked text-lf-on-checked' : 'text-lf-secondary hover:bg-lf-hover'}" aria-pressed={direction === 'up'} onclick={() => (direction = 'up')} data-testid="{testId}-up">
                    {$t('risk.levels.l4.ratesUp')}
                </button>
                <button type="button" class="border-l border-lf-input px-2.5 py-1 text-xs {direction === 'down' ? 'bg-lf-checked text-lf-on-checked' : 'text-lf-secondary hover:bg-lf-hover'}" aria-pressed={direction === 'down'} onclick={() => (direction = 'down')} data-testid="{testId}-down">
                    {$t('risk.levels.l4.ratesDown')}
                </button>
            </div>
            <span class="text-xs text-lf-muted">{$t('risk.levels.l4.ratesBy')}</span>
            <div class="inline-flex overflow-hidden rounded-lg border border-lf-input" role="group">
                {#each STEPS as candidate, index (candidate)}
                    <button
                        type="button"
                        class="px-2.5 py-1 text-xs {index > 0 ? 'border-l border-lf-input' : ''} {step === candidate ? 'bg-lf-checked text-lf-on-checked' : 'text-lf-secondary hover:bg-lf-hover'}"
                        aria-pressed={step === candidate}
                        onclick={() => (step = candidate)}
                        data-testid="{testId}-step-{candidate}"
                    >
                        {formatExactDecimal(candidate * 100, {maxFrac: 1})}
                    </button>
                {/each}
            </div>
            <span class="text-xs text-lf-muted">{$t('risk.levels.l4.ratesPointsUnit')}</span>
        </div>
        <p class="text-sm text-lf-primary" data-testid="{testId}-result" data-price-change={scenario?.price_change ?? ''}>
            {$t(scenario !== null && scenario.price_change > 0 ? 'risk.levels.l4.ratesRise' : 'risk.levels.l4.ratesFall', {values: {percent, amount: ''}}).replace(/\.$/, '')}{#if amount !== null}<span data-testid="{testId}-amount"> · {amount}</span>{/if}.
        </p>
        <p class="text-xs text-lf-muted" data-testid="{testId}-caveat">{$t('risk.levels.l4.ratesCaveat')}</p>
    </div>
{/if}
