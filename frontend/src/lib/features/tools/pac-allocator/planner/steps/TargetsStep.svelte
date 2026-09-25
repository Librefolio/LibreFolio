<script lang="ts">
    import {t} from '$lib/i18n';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import {canonicalInput, decimalSign} from '../decimal';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatPlannerPercentUnits} from '../format';
    import {BUTTON_SECONDARY, HINT, INPUT, NOTICE, TABLE, TD, TH} from '../ui';
    import DistributionDialog from './DistributionDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
    }

    let {draft, accountGeneration}: Props = $props();

    const ids = $props.id();
    let copying = $state(false);

    const copyDisabled = $derived(!/^[A-Z]{3}$/.test(draft.data.valuationCurrency) || !draft.data.assets.some((asset) => asset.sourceAssetId !== null));
    const total = $derived(draft.targetTotal);
    const remaining = $derived(draft.targetRemaining);
    const balanced = $derived(remaining !== null && decimalSign(remaining) === 0);

    /** Bar width of a control percentage: a picture of the target, not a preview of the plan. */
    function barWidth(value: string | undefined): string {
        const canonical = canonicalInput(value ?? '');
        const number = canonical === null ? 0 : Number(canonical);
        return [Math.min(100, Math.max(0, Number.isFinite(number) ? number : 0)), '%'].join('');
    }
</script>

<div class="space-y-4" data-testid="pac-planner-targets">
    <p class="text-sm text-gray-700 dark:text-gray-300">{$t('tools.pacAllocator.planner.targets.intro', {default: 'How to distribute the liquidity. Not a preview of the plan.'})}</p>
    <button type="button" class={BUTTON_SECONDARY} disabled={copyDisabled} data-testid="pac-planner-distribution-open" onclick={() => (copying = true)}>
        {$t('tools.pacAllocator.planner.targets.copyDistribution', {default: 'Copy current distribution'})}
    </button>

    {#if draft.data.assets.length === 0}
        <p class={NOTICE.info} data-testid="pac-planner-targets-empty">{$t('tools.pacAllocator.planner.problems.noAssets', {default: 'Add at least one Asset.'})}</p>
    {:else}
        <div class="overflow-x-auto">
            <table class={TABLE} data-testid="pac-planner-targets-table">
                <thead>
                    <tr>
                        <th scope="col" class={TH}>{$t('tools.pacAllocator.planner.routing.asset', {default: 'Asset'})}</th>
                        <th scope="col" class="{TH} w-32">{$t('tools.pacAllocator.planner.targets.target', {default: 'Target %'})}</th>
                        <th scope="col" class="{TH} w-1/2">{$t('tools.pacAllocator.planner.targets.shape', {default: 'Distribution'})}</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100 dark:divide-gray-800">
                    {#each draft.data.assets as asset (asset.key)}
                        <tr data-testid="pac-planner-target" data-asset-key={asset.key}>
                            <td class={TD}><label for="{ids}-{asset.key}">{[asset.ticker, asset.name].filter((part) => part.trim() !== '').join(' ')}</label></td>
                            <td class={TD}>
                                <ExactDecimalInput id="{ids}-{asset.key}" value={draft.data.targets[asset.key] ?? ''} step="1" max="100" className={INPUT} testid="pac-planner-target-input" onchange={(value) => (draft.data.targets[asset.key] = value)} />
                            </td>
                            <td class={TD}>
                                <div class="h-3 w-full rounded bg-gray-100 dark:bg-gray-700" aria-hidden="true">
                                    <div class="h-3 rounded bg-libre-green" style:width={barWidth(draft.data.targets[asset.key])}></div>
                                </div>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
        <p class="flex flex-wrap gap-4 text-sm" data-testid="pac-planner-targets-control" data-balanced={balanced ? 'true' : 'false'}>
            <span>{$t('tools.pacAllocator.planner.targets.total', {default: 'Total {value}', values: {value: total === null ? '—' : formatPlannerPercentUnits(total)}})}</span>
            <span class={balanced ? '' : 'font-medium text-amber-700 dark:text-amber-300'}>
                {$t('tools.pacAllocator.planner.targets.remaining', {default: 'Remaining {value}', values: {value: remaining === null ? '—' : formatPlannerPercentUnits(remaining)}})}
            </span>
            <span class={HINT}>{$t('tools.pacAllocator.planner.targets.control', {default: '(informative control)'})}</span>
        </p>
        <p class={HINT}>{$t('tools.pacAllocator.planner.targets.wire', {default: 'Weights in percent; they go to the backend as decimals.'})}</p>
    {/if}
</div>

{#if copying}
    <DistributionDialog {draft} {accountGeneration} onclose={() => (copying = false)} />
{/if}
