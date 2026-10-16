<script lang="ts">
    import {SlidersHorizontal} from 'lucide-svelte';
    import {untrack} from 'svelte';

    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {ensureCountriesLoaded, getCountryInfo} from '$lib/stores/reference/countryStore';
    import {ensureSectorsLoaded, getSectorEmoji} from '$lib/stores/reference/sectorStore';
    import {riskMetadata, riskOutput, singleValue} from '$lib/features/risk/riskTypes';
    import {buildHypotheticalShockParameters, type RiskScenarioDimension} from '$lib/features/risk/riskRequest';
    import type {RiskPanelController} from '$lib/features/risk/riskPanelController.svelte';

    import {formatCurrencyAmount, stressImpactDimension} from '../../riskAnalysisHelpers';
    import {stressBucketLabel} from '../../stressBucketLabel';
    import TornadoChart from './TornadoChart.svelte';
    import {shockOptions, shockScenario, tornadoRows, type TornadoRow} from './scenarioHelpers';
    import {formatPercent} from '$lib/utils/core/formatPercent';

    /**
     * L4 rung 2 — hypothetical shock: deterministic, on an assumption stated.
     *
     * The old panel asked the reader to fill in a shock per bucket before
     * anything would run, and **nobody was ever going to do that** (D4). The
     * order is inverted here: a named scenario is one click, and the buckets it
     * implies become visible only when someone asks to see them.
     *
     * That is not merely convenience. A form nobody fills in produces no
     * answers at all, so the level it belongs to is effectively absent — and an
     * absent level reads exactly like a portfolio with nothing to worry about.
     */
    interface Props {
        controller: RiskPanelController;
        assetNames: Record<number, string>;
        currency: string;
        /**
         * Whether this surface may state amounts in money — `undefined` means
         * "decide from the answer".
         *
         * Two separate questions hide here, and conflating them produced two
         * wrong designs in a row. **How it is known**: reading the scope off
         * `metadata` is fail-closed, because a caller cannot forget it; a prop
         * alone is fail-open, so a future mount on `asset_set` that omits it
         * brings the euros back. **What is returned**: `''` makes the amount
         * absent, which is right everywhere, whereas the `—` of
         * `formatScopedCurrencyAmount` is right inside a card and wrong inside a
         * sentence — "would have ended the period at −12.30% —" reads as a
         * number that failed to load, not as one that does not apply.
         *
         * So the default is derived from the payload and the prop is an explicit
         * override. The condition is the one `formatScopedCurrencyAmount`
         * already uses, reused rather than restated, so the guards across the
         * subsystem converge on the same predicate even where the string differs.
         */
        showMoney?: boolean;
    }

    let {controller, assetNames, currency, showMoney: showMoneyOverride}: Props = $props();

    let presetId = $state('');
    let dimension = $state<RiskScenarioDimension>('asset_class');
    let bucketShocks = $state<Record<string, number>>({});
    let showDetail = $state(false);

    let options = $derived(shockOptions(controller.scenarioCatalog, $currentLanguage));
    let result = $derived(controller.stressResult);
    let output = $derived(riskOutput(result, schemas.RiskStressOutput));
    let scopeKind = $derived(singleValue(riskMetadata(result)?.scope) ?? '');
    let showMoney = $derived(showMoneyOverride ?? scopeKind === 'portfolio');
    let rows = $derived(tornadoRows(output));
    let buckets = $derived(Object.keys(bucketShocks).sort((left, right) => left.localeCompare(right)));

    /** Bumped once the country and sector names of the current language have arrived. */
    let referenceVersion = $state(0);
    /** The dimension the answer stressed, which names the table's rows and its first column. */
    let answeredDimension = $derived(stressImpactDimension(output?.dimension, dimension));
    /** A bucket as the reader names it, rebuilt on a language switch and when the reference data lands. */
    let bucketName = $derived.by(() => {
        void referenceVersion;
        const words = {translate: $t, sectorEmoji: getSectorEmoji, country: getCountryInfo};
        return (bucket: string, bucketDimension: RiskScenarioDimension) => stressBucketLabel(bucket, bucketDimension, words);
    });
    let rowLabel = $derived.by(() => {
        const name = bucketName;
        const stressed = answeredDimension;
        const names = assetNames;
        return (row: TornadoRow): string => (row.bucketId !== undefined ? name(row.bucketId, stressed) : (names[row.assetId ?? 0] ?? `#${row.assetId}`));
    });
    let nameHeader = $derived($t(`risk.stress.dimensions.${answeredDimension}`));

    $effect(() => {
        const language = $currentLanguage;
        untrack(() => {
            Promise.all([ensureCountriesLoaded(language), ensureSectorsLoaded()])
                .then(() => {
                    referenceVersion += 1;
                })
                .catch(() => {
                    // The codes stay readable as they are; the next language change tries again.
                });
        });
    });

    $effect(() => {
        controller.registerLauncher('stress', run);
    });

    async function run(): Promise<void> {
        if (Object.keys(bucketShocks).length === 0) return;
        await controller.runGuarded('stress', () => ({
            code: 'stress',
            mode: 'current_composition',
            parameters: buildHypotheticalShockParameters({dimension, bucketShocks}),
        }));
    }

    /** One click: adopt the scenario's assumption *and* ask the question. */
    async function choose(id: string): Promise<void> {
        const scenario = shockScenario(controller.scenarioCatalog, id);
        if (!scenario) return;
        presetId = id;
        dimension = scenario.dimension as RiskScenarioDimension;
        bucketShocks = {...scenario.bucketShocks};
        await run();
    }

    function editBucket(bucket: string, percent: number): void {
        bucketShocks = {...bucketShocks, [bucket]: percent / 100};
        // The preset no longer describes what is on screen, so it stops claiming
        // to: a named scenario that has been edited is no longer that scenario.
        presetId = '';
        controller.resetAnalysis('stress');
    }

    function rowAmount(row: TornadoRow): string {
        return !showMoney || row.amount === null ? '' : formatCurrencyAmount(String(row.amount), currency);
    }
</script>

<div class="space-y-3" data-testid="risk-shock">
    <div class="flex flex-wrap gap-2" data-testid="risk-shock-presets">
        {#each options as option (option.value)}
            <button
                type="button"
                class="rounded-full border px-3 py-1 text-xs {presetId === option.value ? 'border-lf-checked bg-lf-checked text-lf-on-checked' : 'border-lf-input text-lf-secondary'}"
                onclick={() => choose(option.value)}
                disabled={controller.stressLoading}
                data-testid="risk-shock-preset"
                data-preset-id={option.value}
                data-selected={presetId === option.value}
            >
                {option.label}
            </button>
        {/each}
    </div>

    {#if buckets.length > 0}
        <button type="button" class="flex items-center gap-1.5 text-xs text-lf-muted hover:text-lf-secondary" onclick={() => (showDetail = !showDetail)} data-testid="risk-shock-detail-toggle" aria-expanded={showDetail}>
            <SlidersHorizontal size={13} />
            {$t(showDetail ? 'risk.levels.l4.shockHideDetail' : 'risk.levels.l4.shockShowDetail')}
        </button>
    {/if}

    {#if showDetail}
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3" data-testid="risk-shock-buckets">
            {#each buckets as bucket (bucket)}
                {@const name = bucketName(bucket, dimension)}
                <div class="flex items-center gap-1.5 text-xs">
                    <span class="min-w-0 flex-1 truncate text-lf-secondary" title={name}>{name}</span>
                    <input
                        type="number"
                        step="1"
                        value={(bucketShocks[bucket] * 100).toFixed(0)}
                        class="w-16 rounded border border-lf-input bg-lf-field px-1 py-0.5 text-right text-lf-primary hover:border-lf-input-hover focus:border-lf-focus focus:ring-1 focus:ring-lf-focus"
                        onchange={(event) => editBucket(bucket, Number(event.currentTarget.value))}
                        aria-label={name}
                        data-testid="risk-shock-bucket"
                        data-bucket-id={bucket}
                    />
                    <span class="text-lf-muted">%</span>
                </div>
            {/each}
            <button type="button" class="col-span-full justify-self-start rounded-lg bg-lf-action px-3 py-1.5 text-sm text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50" onclick={run} disabled={controller.stressLoading} data-testid="risk-shock-run">
                {$t('risk.actions.runScenario')}
            </button>
        </div>
    {/if}

    {#if output}
        <p class="text-sm text-lf-secondary" data-testid="risk-shock-total">
            {$t('risk.levels.l4.shockTotal', {
                values: {
                    percent: output.portfolio_return == null ? '—' : `${output.portfolio_return < 0 ? '−' : '+'}${formatPercent(Math.abs(output.portfolio_return), {scale: 100, signed: false})}`,
                    amount: !showMoney || output.impact_amount == null ? '' : formatCurrencyAmount(output.impact_amount, currency),
                },
            })}
        </p>
        <TornadoChart {rows} label={rowLabel} {nameHeader} amount={rowAmount} testId="risk-shock-tornado" />
        {#if output.classification_coverage != null && output.classification_coverage < 1}
            <!-- Coverage below one means some holdings had no bucket to fall in.
                 Unstated, the total would silently speak for less than the whole
                 portfolio while looking as if it spoke for all of it. -->
            <p class="text-xs text-lf-warning" data-testid="risk-shock-coverage">
                {$t('risk.levels.l4.shockCoverage', {values: {percent: formatPercent(output.classification_coverage, {scale: 100, signed: false, digits: 0})}})}
            </p>
        {/if}
    {/if}
</div>
