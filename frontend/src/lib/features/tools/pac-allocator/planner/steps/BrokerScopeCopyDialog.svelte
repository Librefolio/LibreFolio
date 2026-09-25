<script lang="ts">
    import {onDestroy, onMount} from 'svelte';
    import {t, locale} from '$lib/i18n';
    import {applyBrokerCopy, applyLiquidityCopy, domainBrokerKey, newCopyRecord, type CopyOutcome} from '../copies';
    import {compareDecimal} from '../decimal';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatPlannerDate, formatPlannerMoneyPlain, formatPlannerPercent} from '../format';
    import {loadCopyScope, selectableIds, type ScopeBroker} from '../scope';
    import type {PlannerSource, SourceCash} from '../source';
    import {SourceLoad} from '../sourceLoad.svelte';
    import {BADGE, BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, NOTICE} from '../ui';
    import PlannerDialog from '../shared/PlannerDialog.svelte';

    interface Props {
        kind: 'liquidity' | 'brokers';
        draft: PlannerDraft;
        accountGeneration: number;
        onclose: () => void;
        oncopied: (outcome: CopyOutcome, source: PlannerSource) => void;
    }

    let {kind, draft, accountGeneration, onclose, oncopied}: Props = $props();

    const testid = $derived(kind === 'liquidity' ? 'pac-planner-liquidity-copy' : 'pac-planner-broker-copy');
    const load = new SourceLoad();
    let scope = $state<ScopeBroker[] | null>(null);
    let scopeFailed = $state(false);
    let selected = $state<number[]>([]);

    onMount(async () => {
        try {
            scope = await loadCopyScope();
        } catch {
            scopeFailed = true;
            return;
        }
        const owners = selectableIds(scope);
        if (owners.length === 0) return;
        await load.load(
            {
                asOf: draft.data.asOf,
                targetCurrency: draft.data.valuationCurrency,
                sections: kind === 'liquidity' ? ['brokers', 'cash_balances'] : ['brokers'],
                brokerIds: owners,
                assetIds: [],
                fxPairs: [],
            },
            accountGeneration,
        );
    });

    onDestroy(() => load.stop());

    function snapshotBroker(id: number) {
        return load.data?.brokers.find((row) => row.source_broker_id === id) ?? null;
    }

    function cashOf(id: number): SourceCash[] {
        const broker = snapshotBroker(id);
        if (!broker || !load.data) return [];
        return load.data.cash.filter((row) => row.broker_id === broker.broker_id);
    }

    function partial(share: string | null): boolean {
        return share !== null && compareDecimal(share, '1') === -1;
    }

    function toggle(id: number, checked: boolean): void {
        selected = checked ? [...selected, id] : selected.filter((item) => item !== id);
    }

    const rowCount = $derived(kind === 'liquidity' ? selected.reduce((count, id) => count + cashOf(id).length, 0) : selected.length);
    const owners = $derived(scope ? selectableIds(scope) : []);

    function copy(): void {
        const source = load.data;
        if (!source || selected.length === 0) return;
        const record = newCopyRecord(draft, kind, source);
        const outcome = kind === 'liquidity' ? applyLiquidityCopy(draft, source, record, selected) : applyBrokerCopy(draft, source, record, selected);
        oncopied(outcome, source);
        onclose();
    }

    const title = $derived(kind === 'liquidity' ? $t('tools.pacAllocator.planner.liquidityCopy.title', {default: 'Copy liquidity from Brokers'}) : $t('tools.pacAllocator.planner.brokerCopy.title', {default: 'Choose existing Brokers'}));
</script>

<PlannerDialog open {title} {testid} {onclose}>
    <div data-testid="{testid}-body" data-state={load.status} aria-busy={load.status === 'loading'}>
        <p class={HINT}>
            {$t('tools.pacAllocator.planner.copy.sourcePortfolio', {
                default: 'Source: Portfolio API (allocation-source) · as of {date} · only Brokers you own.',
                values: {date: formatPlannerDate(draft.data.asOf, $locale)},
            })}
        </p>

        {#if scopeFailed}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-scope-error">{$t('tools.pacAllocator.planner.copy.scopeError', {default: 'The Broker list could not be loaded. Nothing was copied.'})}</div>
        {:else if scope === null || load.status === 'loading'}
            <p class={HINT} role="status" data-testid="{testid}-loading">{$t('common.loading', {default: 'Loading…'})}</p>
        {:else if owners.length === 0}
            <div class={NOTICE.info} data-testid="{testid}-no-owner">
                {kind === 'liquidity'
                    ? $t('tools.pacAllocator.planner.liquidityCopy.noOwner', {default: 'You own no Broker to copy from. Add a manual account instead: the Tool works without any Broker in the database.'})
                    : $t('tools.pacAllocator.planner.brokerCopy.noOwner', {default: 'You own no Broker to copy. Add a manual Broker instead.'})}
            </div>
        {:else if load.status === 'error' && load.error}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-error">{$t(load.error.key, {default: load.error.fallback})}</div>
        {/if}

        {#if scope && scope.length > 0 && load.status !== 'loading'}
            <ul class="mt-3 space-y-2" data-testid="{testid}-list">
                {#each scope as broker (broker.id)}
                    {@const snapshot = snapshotBroker(broker.id)}
                    <li class="rounded-lg border border-gray-200 p-3 dark:border-gray-700" data-testid="{testid}-broker" data-broker-id={broker.id} data-selectable={broker.selectable ? 'true' : 'false'}>
                        {#if broker.selectable}
                            <label class="flex flex-wrap items-center gap-2">
                                <input type="checkbox" class="rounded border-gray-300 text-libre-green focus:ring-libre-green" checked={selected.includes(broker.id)} disabled={!snapshot} data-testid="{testid}-check" onchange={(event) => toggle(broker.id, event.currentTarget.checked)} />
                                <span class="font-medium">{broker.name}</span>
                                {#if partial(broker.share)}
                                    <span class={HINT}>· {$t('tools.pacAllocator.planner.scope.share', {default: 'share {share}', values: {share: formatPlannerPercent(broker.share)}})}</span>
                                {/if}
                                {#if !broker.active}<span class={BADGE.warning}>{$t('tools.pacAllocator.planner.scope.inactive', {default: 'Inactive'})}</span>{/if}
                                {#if draft.broker(domainBrokerKey(broker.id))}<span class={BADGE.info}>{$t('tools.pacAllocator.planner.copy.alreadyInDraft', {default: 'Already in the draft: copying again updates it'})}</span>{/if}
                            </label>
                            {#if kind === 'liquidity' && snapshot}
                                {@const rows = cashOf(broker.id)}
                                <ul class="mt-2 space-y-1 pl-6 text-sm" data-testid="{testid}-cash">
                                    {#each rows as row (row.cash_id)}
                                        <li class="flex flex-wrap gap-x-2 tabular-nums" data-currency={row.currency}>
                                            <span class="font-medium">{row.currency}</span>
                                            <span>{$t('tools.pacAllocator.planner.liquidityCopy.custody', {default: 'custody {amount}', values: {amount: formatPlannerMoneyPlain(row.custody_amount, row.currency)}})}</span>
                                            {#if partial(row.ownership_share)}
                                                <span>· {$t('tools.pacAllocator.planner.liquidityCopy.yourShare', {default: 'your share {amount}', values: {amount: formatPlannerMoneyPlain(row.economic_amount, row.currency)}})}</span>
                                            {:else}
                                                <span>· {$t('tools.pacAllocator.planner.liquidityCopy.allYours', {default: '100% yours'})}</span>
                                            {/if}
                                        </li>
                                    {:else}
                                        <li class={HINT}>{$t('tools.pacAllocator.planner.liquidityCopy.noCash', {default: 'No cash balance on this date.'})}</li>
                                    {/each}
                                </ul>
                            {:else if kind === 'brokers' && snapshot}
                                <p class="mt-1 pl-6 {HINT}">
                                    {snapshot.observed_currencies.length > 0
                                        ? $t('tools.pacAllocator.planner.brokerCopy.currencies', {default: 'Currencies seen: {currencies}', values: {currencies: snapshot.observed_currencies.join(', ')}})
                                        : $t('tools.pacAllocator.planner.brokerCopy.noCurrencies', {default: 'No currency seen yet: one mode in the valuation currency is proposed.'})}
                                </p>
                            {/if}
                        {:else}
                            <p class="flex flex-wrap items-center gap-2 text-gray-500 dark:text-gray-400">
                                <input type="checkbox" class="rounded border-gray-300" disabled aria-hidden="true" tabindex="-1" />
                                <span>{broker.name}</span>
                                <span class={HINT} data-testid="{testid}-blocked">{$t('tools.pacAllocator.planner.scope.notSelectable', {default: 'Not selectable: {role} access, not read', values: {role: broker.role ?? '—'}})}</span>
                            </p>
                        {/if}
                    </li>
                {/each}
            </ul>
        {/if}

        <p class="mt-3 {HINT}">
            {kind === 'liquidity'
                ? $t('tools.pacAllocator.planner.liquidityCopy.rule', {default: "Every Broker × currency becomes one row. 'Amount to use' stays empty: you write it. A 403/404 from the API shows here in plain words; no Broker is dropped in silence."})
                : $t('tools.pacAllocator.planner.brokerCopy.rule', {default: 'Only the Broker identity is copied. Order modes, fees and funding are scenario data you set here; the Broker itself is not changed.'})}
        </p>
    </div>

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="{testid}-cancel" onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_PRIMARY} disabled={load.status !== 'ready' || selected.length === 0} data-testid="{testid}-apply" onclick={copy}>
            {kind === 'liquidity'
                ? $t('tools.pacAllocator.planner.liquidityCopy.apply', {default: '{count, plural, one {Copy # row} other {Copy # rows}}', values: {count: rowCount}})
                : $t('tools.pacAllocator.planner.brokerCopy.apply', {default: '{count, plural, one {Copy # Broker} other {Copy # Brokers}}', values: {count: rowCount}})}
        </button>
    {/snippet}
</PlannerDialog>
