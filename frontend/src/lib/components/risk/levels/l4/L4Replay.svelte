<script lang="ts">
    import {Play} from 'lucide-svelte';

    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import {riskMetadata, riskOutput, singleValue} from '$lib/risk/riskTypes';
    import {buildHistoricalReplayParameters} from '$lib/risk/riskRequest';
    import type {RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';

    import {formatCurrencyAmount} from '../../riskAnalysisHelpers';
    import TornadoChart from './TornadoChart.svelte';
    import {replayBlocker, replayOptions, tornadoRows, type TornadoRow} from './scenarioHelpers';

    /**
     * L4 rung 1 — historical replay: real returns, from a real period.
     *
     * The closest rung to observed data, and the only one of the three that is
     * not an opinion: it takes today's composition through what actually
     * happened. That is still a *backtest* and not a record — the composition is
     * today's, not the one held at the time — which is why the audit below is
     * shown rather than hidden.
     */
    interface Props {
        controller: RiskPanelController;
        assetNames: Record<number, string>;
        currency: string;
        dateStart: string;
        dateEnd: string;
    }

    let {controller, assetNames, currency, dateStart, dateEnd}: Props = $props();

    let presetId = $state('');
    /**
     * The replay window follows the panel's window until someone overrides it.
     *
     * Seeding plain state from the prop would freeze the initial value: the
     * reader could narrow the analysis period in the header and then run a
     * replay over the *old* period, with the form showing the old dates and no
     * hint that they stopped being the panel's. An override that starts null
     * keeps the two bound while leaving the box editable.
     */
    let startOverride = $state<string | null>(null);
    let endOverride = $state<string | null>(null);
    let start = $derived(startOverride ?? dateStart);
    let end = $derived(endOverride ?? dateEnd);
    /**
     * Holdings the reader has chosen to leave out, accumulated across attempts.
     *
     * `stress.py:451` refuses the whole replay at the **first** holding without
     * usable history, so a portfolio with three such holdings needs three
     * answers. Accumulating them here turns that into a visible, reversible
     * list instead of a loop the reader cannot see the end of.
     */
    let excluded = $state<number[]>([]);

    let options = $derived(replayOptions(controller.scenarioCatalog, $currentLanguage));
    let result = $derived(controller.replayResult);
    let output = $derived(riskOutput(result, schemas.RiskStressOutput));
    let audit = $derived(singleValue(riskMetadata(result)?.historical_replay_audit));
    let blocker = $derived(replayBlocker(result));
    let rows = $derived(tornadoRows(output));

    $effect(() => {
        controller.registerLauncher('replay', run);
    });

    async function run(): Promise<void> {
        await controller.runGuarded('replay', () => ({
            code: 'stress',
            mode: 'current_composition',
            parameters: buildHistoricalReplayParameters({
                start,
                end,
                missingHistoryPolicy: 'manual_proxy_or_exclude',
                proxyAssets: [],
                excludedAssetIds: [...excluded].sort((left, right) => left - right),
            }),
        }));
    }

    function applyPreset(id: string): void {
        presetId = id;
        const option = options.find((candidate) => candidate.value === id);
        if (option?.start) startOverride = option.start;
        if (option?.end) endOverride = option.end;
        // A new period is a new question, so the old answer must go rather than
        // sit under a changed form looking like a reply to it.
        excluded = [];
        controller.resetAnalysis('replay');
    }

    function overrideStart(value: string): void {
        startOverride = value;
        controller.resetAnalysis('replay');
    }

    function overrideEnd(value: string): void {
        endOverride = value;
        controller.resetAnalysis('replay');
    }

    function excludeAndRetry(assetId: number): void {
        excluded = [...excluded, assetId];
        void run();
    }

    function restore(assetId: number): void {
        excluded = excluded.filter((candidate) => candidate !== assetId);
        controller.resetAnalysis('replay');
    }

    function name(assetId: number): string {
        return assetNames[assetId] ?? `#${assetId}`;
    }

    function rowLabel(row: TornadoRow): string {
        return row.assetId === undefined ? (row.bucketId ?? '') : name(row.assetId);
    }

    function rowAmount(row: TornadoRow): string {
        return row.amount === null ? '' : formatCurrencyAmount(String(row.amount), currency);
    }
</script>

<div class="space-y-3" data-testid="risk-replay">
    <div class="flex flex-wrap items-end gap-2">
        <div class="flex flex-col gap-1 text-xs text-gray-500 dark:text-gray-400">
            <span>{$t('risk.stress.preset')}</span>
            <SimpleSelect value={presetId} options={options.map((option) => ({value: option.value, label: option.label}))} compact ariaLabel={$t('risk.stress.preset')} onchange={applyPreset} testId="risk-replay-preset" />
        </div>
        <label class="flex flex-col gap-1 text-xs text-gray-500 dark:text-gray-400">
            {$t('common.from')}
            <input type="date" value={start} class="rounded border border-gray-200 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700" data-testid="risk-replay-start" onchange={(event) => overrideStart(event.currentTarget.value)} />
        </label>
        <label class="flex flex-col gap-1 text-xs text-gray-500 dark:text-gray-400">
            {$t('common.to')}
            <input type="date" value={end} class="rounded border border-gray-200 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-700" data-testid="risk-replay-end" onchange={(event) => overrideEnd(event.currentTarget.value)} />
        </label>
        <button type="button" class="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white disabled:opacity-50" onclick={run} disabled={controller.replayLoading} data-testid="risk-replay-run">
            <Play size={14} />
            {$t('risk.actions.runReplay')}
        </button>
    </div>

    {#if excluded.length > 0}
        <!-- The reader's own choices, kept visible and reversible: an exclusion
             silently remembered is an assumption smuggled into the answer. -->
        <div class="flex flex-wrap items-center gap-1.5 text-xs" data-testid="risk-replay-exclusions">
            <span class="text-gray-500 dark:text-gray-400">{$t('risk.levels.l4.replayExcluded')}</span>
            {#each excluded as assetId (assetId)}
                <button type="button" class="rounded-full bg-gray-100 px-2 py-0.5 text-gray-700 hover:bg-gray-200 dark:bg-slate-700 dark:text-gray-200" onclick={() => restore(assetId)} data-testid="risk-replay-exclusion" data-asset-id={assetId}>
                    {name(assetId)} ×
                </button>
            {/each}
        </div>
    {/if}

    {#if blocker}
        <div class="rounded-lg bg-amber-50 p-3 text-xs dark:bg-amber-900/20" data-testid="risk-replay-blocker" data-asset-id={blocker.assetId} data-proxy-at-fault={blocker.proxyAtFault}>
            <p class="text-amber-800 dark:text-amber-200">
                {$t(blocker.proxyAtFault ? 'risk.levels.l4.replayProxyUnusable' : 'risk.levels.l4.replayNeedsChoice', {values: {name: name(blocker.assetId)}})}
            </p>
            {#if !blocker.proxyAtFault}
                <button type="button" class="mt-2 rounded border border-amber-400 px-2 py-1 text-amber-800 dark:text-amber-200" onclick={() => excludeAndRetry(blocker.assetId)} data-testid="risk-replay-exclude">
                    {$t('risk.levels.l4.replayExcludeAndRetry')}
                </button>
            {/if}
        </div>
    {/if}

    {#if output}
        <p class="text-sm text-gray-700 dark:text-gray-200" data-testid="risk-replay-total">
            {$t('risk.levels.l4.replayTotal', {
                values: {
                    percent: output.portfolio_return == null ? '—' : `${output.portfolio_return < 0 ? '−' : '+'}${(Math.abs(output.portfolio_return) * 100).toFixed(2)}%`,
                    amount: output.impact_amount == null ? '' : formatCurrencyAmount(output.impact_amount, currency),
                },
            })}
        </p>
        <TornadoChart {rows} label={rowLabel} amount={rowAmount} testId="risk-replay-tornado" />
        {#if audit}
            <!-- A proxy is a choice, not a fact, and an exclusion changes what the
                 number means. Both are stated where the number is read. -->
            <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-replay-audit" data-proxy-count={audit.proxy_count} data-excluded-count={audit.excluded_count}>
                {$t('risk.levels.l4.replayAudit', {
                    values: {
                        proxies: audit.proxy_count,
                        excluded: audit.excluded_count,
                        weight: `${((audit.excluded_weight_total ?? 0) * 100).toFixed(1)}%`,
                    },
                })}
            </p>
        {/if}
    {/if}
</div>
