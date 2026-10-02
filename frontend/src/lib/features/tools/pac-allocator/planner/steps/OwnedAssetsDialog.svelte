<!--
  «Your Assets»: the Assets with an open position today in the Brokers you own, added to the
  plan in one go. Only their identity is added here: no quantity is read or shown; the step
  reads their stored prices right after (`onadded`).
-->
<script lang="ts">
    import {onDestroy, onMount} from 'svelte';
    import {CheckCheck, Square} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import {applyOwnedAssets, domainAssetKey, domainBrokerKey, ownedAssets} from '../copies';
    import type {PlannerDraft} from '../draft.svelte';
    import {loadCopyScope, selectableIds, type ScopeBroker} from '../scope';
    import {compareDecimal} from '../decimal';
    import {formatPlannerPercent} from '../format';
    import {SourceLoad} from '../sourceLoad.svelte';
    import {BADGE, BUTTON_PILL, BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, LABEL_ROW, NOTICE} from '../ui';
    import HelpTip from '../shared/HelpTip.svelte';
    import PlannerDialog from '../shared/PlannerDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
        /** The source ids of the Assets just added. */
        onadded: (assetIds: number[]) => void;
        onclose: () => void;
    }

    let {draft, accountGeneration, onadded, onclose}: Props = $props();

    const testid = 'pac-planner-owned-assets';
    const load = new SourceLoad();
    let scope = $state<ScopeBroker[] | null>(null);
    let scopeFailed = $state(false);
    /** One owned Broker id, or `''` for all of them. */
    let brokerFilter = $state('');
    /** The Assets the user unticked: every other one in view is ticked. */
    let excluded = $state<number[]>([]);

    onMount(async () => {
        try {
            scope = await loadCopyScope();
        } catch {
            scopeFailed = true;
            return;
        }
        const owners = selectableIds(scope);
        if (owners.length === 0) return;
        const planBrokers = owners.filter((id) => draft.broker(domainBrokerKey(id)) !== undefined);
        brokerFilter = planBrokers.length === 1 ? String(planBrokers[0]) : '';
        draft.refreshAsOf();
        await load.load(
            {
                asOf: draft.data.asOf,
                targetCurrency: draft.data.valuationCurrency,
                sections: ['assets', 'brokers', 'holdings'],
                brokerIds: owners,
                assetIds: null,
                fxPairs: [],
            },
            accountGeneration,
        );
    });

    onDestroy(() => load.stop());

    const owners = $derived(scope ? selectableIds(scope) : []);
    const scopeById = $derived(new Map((scope ?? []).map((broker) => [broker.id, broker])));
    const owned = $derived(load.data ? ownedAssets(load.data) : {rows: [], unresolved: 0});
    /** Brokers with a lower role stay listed, disabled, never dropped in silence (N18). */
    const brokerOptions = $derived<SelectOption[]>([
        {value: '', label: $t('tools.pacAllocator.planner.ownedAssets.allBrokers', {default: 'All Brokers'})},
        ...(scope ?? []).map((broker) => ({value: String(broker.id), label: broker.name, disabled: !broker.selectable})),
    ]);
    const visible = $derived(brokerFilter === '' ? owned.rows : owned.rows.filter((row) => row.brokerIds.includes(Number(brokerFilter))));
    const pickable = $derived(visible.filter((row) => !inPlan(row.asset.source_asset_id)));
    const picked = $derived(pickable.filter((row) => !excluded.includes(row.asset.source_asset_id)));

    function inPlan(assetId: number): boolean {
        return draft.asset(domainAssetKey(assetId)) !== undefined;
    }

    function toggle(assetId: number, checked: boolean): void {
        excluded = checked ? excluded.filter((id) => id !== assetId) : [...excluded, assetId];
    }

    function selectAll(): void {
        const ids = new Set(pickable.map((row) => row.asset.source_asset_id));
        excluded = excluded.filter((id) => !ids.has(id));
    }

    function selectNone(): void {
        excluded = [...new Set([...excluded, ...pickable.map((row) => row.asset.source_asset_id)])];
    }

    function partial(share: string | null): boolean {
        return share !== null && compareDecimal(share, '1') === -1;
    }

    function add(): void {
        const assets = picked.map((row) => row.asset);
        applyOwnedAssets(draft, assets);
        onadded(assets.map((asset) => asset.source_asset_id));
        onclose();
    }
</script>

{#snippet brokerOption(option: SelectOption)}
    {@const broker = scopeById.get(Number(option.value))}
    {#if broker}
        <span class="flex min-w-0 items-center gap-2">
            <span class="inline-flex shrink-0 {broker.selectable ? '' : 'opacity-60'}"><BrokerIcon brokerId={broker.id} iconUrl={broker.iconUrl} portalUrl={broker.portalUrl} pluginCode={broker.pluginCode} altText="" size={16} /></span>
            <span class="min-w-0">
                <span class="flex flex-wrap items-center gap-x-2">
                    <span class="truncate">{broker.name}</span>
                    {#if broker.selectable && partial(broker.share)}<span class={HINT}>· {$t('tools.pacAllocator.planner.scope.share', {default: 'share {share}', values: {share: formatPlannerPercent(broker.share)}})}</span>{/if}
                    {#if !broker.active}<span class={BADGE.warning}>{$t('tools.pacAllocator.planner.scope.inactive', {default: 'Inactive'})}</span>{/if}
                </span>
                {#if !broker.selectable}
                    <span class="block text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.planner.scope.notSelectable', {default: 'Not selectable: {role} access, not read', values: {role: broker.role ?? '—'}})}</span>
                {/if}
            </span>
        </span>
    {:else}
        <span class="truncate">{option.label}</span>
    {/if}
{/snippet}

{#snippet brokerSelected(option: SelectOption)}
    {@const broker = scopeById.get(Number(option.value))}
    <span class="flex min-w-0 items-center gap-2">
        {#if broker}<BrokerIcon brokerId={broker.id} iconUrl={broker.iconUrl} portalUrl={broker.portalUrl} pluginCode={broker.pluginCode} altText="" size={16} />{/if}
        <span class="truncate">{option.label}</span>
    </span>
{/snippet}

<PlannerDialog open title={$t('tools.pacAllocator.planner.ownedAssets.title', {default: 'Add the Assets you hold'})} {testid} {onclose}>
    <div class="space-y-3" data-testid="{testid}-body" data-state={load.status} aria-busy={load.status === 'loading'}>
        {#if scopeFailed}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-scope-error">{$t('tools.pacAllocator.planner.copy.scopeError', {default: 'The Broker list could not be loaded. Nothing was copied.'})}</div>
        {:else if scope === null || load.status === 'loading'}
            <p class={HINT} role="status" data-testid="{testid}-loading">{$t('common.loading', {default: 'Loading…'})}</p>
        {:else if owners.length === 0}
            <div class={NOTICE.info} data-testid="{testid}-no-owner">{$t('tools.pacAllocator.planner.ownedAssets.noOwner', {default: 'You own no Broker to read positions from. Search the Assets or add manual ones: the Tool works without any registered Broker.'})}</div>
        {:else if load.status === 'error' && load.error}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-error">{$t(load.error.key, {default: load.error.fallback})}</div>
        {:else if load.data}
            <div>
                <p class={LABEL_ROW}>
                    {$t('tools.pacAllocator.planner.ownedAssets.brokers', {default: 'Broker'})}
                    <HelpTip label={$t('tools.pacAllocator.planner.ownedAssets.brokers', {default: 'Broker'})} help={$t('tools.pacAllocator.planner.ownedAssets.brokersHelp', {default: 'The list shows the Assets with an open position today in the chosen Broker, or in all your Brokers. It starts on the Broker of the plan when the plan has exactly one.'})} />
                </p>
                <div class="w-full sm:w-72">
                    <SimpleSelect
                        value={brokerFilter}
                        options={brokerOptions}
                        compact
                        ariaLabel={$t('tools.pacAllocator.planner.ownedAssets.brokers', {default: 'Broker'})}
                        testId="{testid}-brokers"
                        optionTestId={(option) => `${testid}-broker-option-${option.value || 'all'}`}
                        item={brokerOption}
                        selectedItem={brokerSelected}
                        onchange={(value) => (brokerFilter = value)}
                    />
                </div>
            </div>

            {#if owned.unresolved > 0}
                <div class={NOTICE.warning} data-testid="{testid}-unresolved">
                    {$t('tools.pacAllocator.planner.ownedAssets.unresolved', {default: '{count, plural, one {# position could not be matched to its Asset or Broker and is not listed.} other {# positions could not be matched to their Asset or Broker and are not listed.}}', values: {count: owned.unresolved}})}
                </div>
            {/if}

            <div class="flex flex-wrap items-center gap-2" data-testid="{testid}-bulk">
                <button type="button" class={BUTTON_PILL} disabled={pickable.length === 0} data-testid="{testid}-all" onclick={selectAll}>
                    <CheckCheck size={13} aria-hidden="true" />{$t('tools.pacAllocator.planner.ownedAssets.selectAll', {default: 'Select all'})}
                </button>
                <button type="button" class={BUTTON_PILL} disabled={pickable.length === 0} data-testid="{testid}-none" onclick={selectNone}>
                    <Square size={13} aria-hidden="true" />{$t('tools.pacAllocator.planner.ownedAssets.selectNone', {default: 'Deselect all'})}
                </button>
                <span class="ml-auto {HINT}" data-testid="{testid}-count" data-selected={picked.length} data-total={pickable.length}>
                    {$t('tools.pacAllocator.planner.ownedAssets.count', {default: '{selected} of {total} selected', values: {selected: picked.length, total: pickable.length}})}
                </span>
            </div>

            <ul class="space-y-2" data-testid="{testid}-list">
                {#each visible as row (row.asset.asset_id)}
                    {@const assetId = row.asset.source_asset_id}
                    {@const already = inPlan(assetId)}
                    {@const checked = !already && !excluded.includes(assetId)}
                    <li data-testid="{testid}-asset" data-asset-id={assetId} data-in-plan={already ? 'true' : 'false'} data-selected={checked ? 'true' : 'false'}>
                        <label class="flex items-center gap-3 rounded-lg border p-3 transition-colors {checked ? 'border-libre-green bg-libre-green/10 dark:bg-libre-green/20' : 'border-gray-200 dark:border-gray-700'} {already ? 'cursor-not-allowed opacity-60' : 'cursor-pointer hover:border-libre-green'}">
                            <input type="checkbox" class="rounded border-gray-300 text-libre-green focus:ring-libre-green" {checked} disabled={already} data-testid="{testid}-check" onchange={(event) => toggle(assetId, event.currentTarget.checked)} />
                            <AssetIcon iconUrl={row.asset.icon_url} assetType={row.asset.asset_class} altText="" size="sm" />
                            <span class="min-w-0 flex-1">
                                <span class="flex flex-wrap items-center gap-2">
                                    <span class="font-medium text-gray-900 dark:text-gray-100">{row.asset.name}</span>
                                    {#if row.asset.ticker}<span class={HINT}>{row.asset.ticker}</span>{/if}
                                    {#if !row.asset.active}<span class={BADGE.warning}>{$t('tools.pacAllocator.planner.scope.inactive', {default: 'Inactive'})}</span>{/if}
                                    {#if already}<span class={BADGE.info} data-testid="{testid}-in-plan">{$t('tools.pacAllocator.planner.ownedAssets.inPlan', {default: 'Already in the plan'})}</span>{/if}
                                </span>
                                <span class="mt-1 flex flex-wrap gap-x-3 gap-y-1" data-testid="{testid}-holders">
                                    {#each row.brokerIds as brokerId (brokerId)}
                                        {@const broker = scopeById.get(brokerId)}
                                        {#if broker}
                                            <span class="inline-flex items-center gap-1 text-xs text-gray-600 dark:text-gray-300">
                                                <BrokerIcon brokerId={broker.id} iconUrl={broker.iconUrl} portalUrl={broker.portalUrl} pluginCode={broker.pluginCode} altText="" size={16} />{broker.name}
                                            </span>
                                        {/if}
                                    {/each}
                                </span>
                            </span>
                        </label>
                    </li>
                {:else}
                    <li class={HINT} data-testid="{testid}-empty">
                        {#if owned.rows.length === 0}
                            {$t('tools.pacAllocator.planner.ownedAssets.noHoldings', {default: 'No open position in your Brokers today.'})}
                        {:else}
                            {$t('tools.pacAllocator.planner.ownedAssets.noneInBrokers', {default: 'No open position in this Broker today.'})}
                        {/if}
                    </li>
                {/each}
            </ul>
        {/if}
    </div>

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="{testid}-cancel" onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_PRIMARY} disabled={load.status !== 'ready' || picked.length === 0} data-testid="{testid}-apply" onclick={add}>
            {$t('tools.pacAllocator.planner.ownedAssets.apply', {default: '{count, plural, one {Add # Asset} other {Add # Assets}}', values: {count: picked.length}})}
        </button>
    {/snippet}
</PlannerDialog>
