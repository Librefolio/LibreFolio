<script lang="ts">
    import KpiCard from '$lib/components/dashboard/KpiCard.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {_ as t} from '$lib/i18n';

    import RiskAnalysisPanel from './RiskAnalysisPanel.svelte';
    import RiskBetaBanner from './RiskBetaBanner.svelte';

    interface Props {
        assetId: number;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        assetClass?: string | null;
        sectorExposure?: Record<string, number> | null;
        geographyExposure?: Record<string, number> | null;
        rollingRiskSignals?: RenderedSignal[];
        refreshVersion?: number;
        onconfigure?: () => void | Promise<void>;
        onsynced?: () => void | Promise<void>;
    }

    let {assetId, dateStart, dateEnd, targetCurrency, assetClass = null, sectorExposure = null, geographyExposure = null, rollingRiskSignals = [], refreshVersion = 0, onconfigure, onsynced}: Props = $props();

    let selectedRollingId = $state('');
    let rollingGroups = $derived.by(() => {
        const groups = new Map<string, {id: string; label: string; unit: RenderedSignal['unit']; signals: RenderedSignal[]}>();
        for (const signal of rollingRiskSignals) {
            const id = signal.id.split(':')[0];
            const current = groups.get(id);
            if (current) current.signals.push(signal);
            else groups.set(id, {id, label: signal.label, unit: signal.unit, signals: [signal]});
        }
        return [...groups.values()];
    });
    let rollingOptions = $derived(rollingGroups.map((group) => ({value: group.id, label: group.label})));
    let selectedRolling = $derived(rollingGroups.find((group) => group.id === selectedRollingId) ?? rollingGroups[0] ?? null);
    let latestRollingPoint = $derived(
        selectedRolling?.signals
            .flatMap((signal) => signal.data)
            .sort((left, right) => left.date.localeCompare(right.date))
            .at(-1) ?? null,
    );

    $effect(() => {
        if (rollingGroups.length === 0) {
            selectedRollingId = '';
            return;
        }
        if (!rollingGroups.some((group) => group.id === selectedRollingId)) selectedRollingId = rollingGroups[0].id;
    });

    function formatRollingValue(value: number | null | undefined, unit: RenderedSignal['unit']): string {
        if (value == null) return '—';
        if (unit === 'percentage') return `${(value * 100).toFixed(2)}%`;
        return value.toFixed(3);
    }
</script>

<div class="space-y-4" data-testid="asset-risk-scenarios-view">
    <RiskBetaBanner />

    <section class="rounded-xl border border-gray-100 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800" data-testid="asset-risk-summary">
        <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">{$t('risk.assetDetail.summaryTitle')}</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400">{$t('risk.assetDetail.summaryDescription')}</p>

        {#if selectedRolling}
            <div class="mt-3 flex flex-wrap items-end gap-3">
                <label class="min-w-52 text-xs text-gray-500 dark:text-gray-400">
                    {$t('risk.assetDetail.rollingMetric')}
                    <div class="mt-1">
                        <SimpleSelect value={selectedRollingId} options={rollingOptions} compact testId="asset-risk-rolling-select" onchange={(value) => (selectedRollingId = value)} />
                    </div>
                </label>
                <div class="min-w-48">
                    <KpiCard label={selectedRolling.label} value={formatRollingValue(latestRollingPoint?.value, selectedRolling.unit)} subLabel={latestRollingPoint?.date} />
                </div>
            </div>
        {:else}
            <p class="mt-3 text-sm text-gray-500 dark:text-gray-400" data-testid="asset-risk-no-rolling">{$t('risk.assetDetail.noRollingMetric')}</p>
        {/if}

        <button type="button" class="mt-3 text-sm font-medium text-libre-green hover:underline" onclick={() => onconfigure?.()} data-testid="asset-risk-configure-signals">
            {$t('risk.assetDetail.configureSignals')}
        </button>
    </section>

    <RiskAnalysisPanel
        scope={{kind: 'asset', asset_id: assetId}}
        {dateStart}
        {dateEnd}
        {targetCurrency}
        assetIds={[assetId]}
        title={$t('risk.assetTitle')}
        subtitle={$t('risk.assetRollingHint')}
        {assetClass}
        {sectorExposure}
        {geographyExposure}
        {refreshVersion}
        showHeaderActions={false}
        showBetaBanner={false}
        {onsynced}
    />
</div>
