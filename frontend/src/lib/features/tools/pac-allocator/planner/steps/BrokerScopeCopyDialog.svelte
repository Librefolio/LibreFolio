<script lang="ts">
    import {onDestroy, onMount} from 'svelte';
    import {t} from '$lib/i18n';
    import {applyBrokerCopy, applyLiquidityCopy, domainBrokerKey, domainCashKey, newCopyRecord, type CopyOutcome} from '../copies';
    import {compareDecimal} from '../decimal';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatPlannerMoneyPlain} from '../format';
    import {loadCopyScope, selectableIds, type ScopeBroker} from '../scope';
    import type {PlannerSource, SourceCash} from '../source';
    import {SourceLoad} from '../sourceLoad.svelte';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, NOTICE} from '../ui';
    import BrokerTile from '../shared/BrokerTile.svelte';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
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
        // «Add Broker» has nothing to read for a Broker the plan already has.
        const pending = kind === 'brokers' ? owners.filter((id) => !draft.broker(domainBrokerKey(id))) : owners;
        if (pending.length === 0) return;
        draft.refreshAsOf();
        await load.load(
            {
                asOf: draft.data.asOf,
                targetCurrency: draft.data.valuationCurrency,
                sections: kind === 'liquidity' ? ['brokers', 'cash_balances'] : ['brokers'],
                brokerIds: pending,
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

    /** The cash rows of a Broker that the plan does not have yet: the dialog offers and copies only these. */
    function newCash(id: number): SourceCash[] {
        return cashOf(id).filter((row) => !draft.cashRow(domainCashKey(id, row.currency)));
    }

    /** Already in the plan: the Broker itself for «Add Broker», the Broker with all its cash for «Copy liquidity». */
    function inPlan(id: number): boolean {
        if (!draft.broker(domainBrokerKey(id))) return false;
        if (kind === 'brokers') return true;
        // Without its snapshot the cash of a Broker is unknown, so it is not called complete.
        return snapshotBroker(id) !== null && newCash(id).length === 0;
    }

    function partial(share: string | null): boolean {
        return share !== null && compareDecimal(share, '1') === -1;
    }

    function toggle(id: number, pressed: boolean): void {
        selected = pressed ? [...selected, id] : selected.filter((item) => item !== id);
    }

    const rowCount = $derived(kind === 'liquidity' ? selected.reduce((count, id) => count + newCash(id).length, 0) : selected.length);
    const owners = $derived(scope ? selectableIds(scope) : []);
    const visible = $derived(scope ? scope.filter((broker) => !inPlan(broker.id)) : []);
    const allInPlan = $derived(owners.length > 0 && !visible.some((broker) => broker.selectable));

    function copy(): void {
        const loaded = load.data;
        if (!loaded || selected.length === 0) return;
        // The dialog only adds: a cash row already in the plan is left as it is, and «Calculate» re-reads it.
        const sourceIds = new Map(loaded.brokers.map((row) => [row.broker_id, row.source_broker_id]));
        const source: PlannerSource =
            kind === 'liquidity'
                ? {
                      ...loaded,
                      cash: loaded.cash.filter((row) => {
                          const id = sourceIds.get(row.broker_id);
                          return id === undefined || !draft.cashRow(domainCashKey(id, row.currency));
                      }),
                  }
                : loaded;
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
            {$t('tools.pacAllocator.planner.copy.sourcePortfolio', {default: 'You can copy only from Brokers you own.'})}
        </p>

        {#if scopeFailed}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-scope-error">{$t('tools.pacAllocator.planner.copy.scopeError', {default: 'The Broker list could not be loaded. Nothing was copied.'})}</div>
        {:else if scope === null || load.status === 'loading'}
            <p class={HINT} role="status" data-testid="{testid}-loading">{$t('common.loading', {default: 'Loading…'})}</p>
        {:else if owners.length === 0}
            <div class={NOTICE.info} data-testid="{testid}-no-owner">
                {kind === 'liquidity'
                    ? $t('tools.pacAllocator.planner.liquidityCopy.noOwner', {default: 'You own no Broker to copy from. Use an external account or a new contribution instead: the Tool works without any registered Broker.'})
                    : $t('tools.pacAllocator.planner.brokerCopy.noOwner', {default: 'You own no Broker to copy. Add a manual Broker instead.'})}
            </div>
        {:else if load.status === 'error' && load.error}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-error">{$t(load.error.key, {default: load.error.fallback})}</div>
        {/if}

        {#if scope !== null && load.status !== 'loading' && allInPlan}
            <div class="mt-3 {NOTICE.info}" data-testid="{testid}-all-in-plan">
                {$t('tools.pacAllocator.planner.copy.allInPlan', {
                    default: '{kind, select, liquidity {The liquidity of every Broker you can copy is already in the plan.} other {Every Broker you can copy is already in the plan.}}',
                    values: {kind},
                })}
            </div>
        {/if}

        {#if visible.length > 0 && load.status !== 'loading'}
            <ul class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3" data-testid="{testid}-list">
                {#each visible as broker (broker.id)}
                    {@const snapshot = snapshotBroker(broker.id)}
                    {@const checked = selected.includes(broker.id)}
                    <li data-testid="{testid}-broker" data-broker-id={broker.id} data-selectable={broker.selectable ? 'true' : 'false'} data-selected={checked ? 'true' : 'false'}>
                        <BrokerTile {broker} pressed={checked} disabled={!snapshot} {testid} ontoggle={(next) => toggle(broker.id, next)}>
                            {#snippet detail()}
                                {#if kind === 'liquidity' && snapshot}
                                    {@const rows = newCash(broker.id)}
                                    <span class="block w-max min-w-full space-y-0.5 text-xs" data-testid="{testid}-cash">
                                        {#each rows as row (row.cash_id)}
                                            <span class="flex w-max min-w-full items-center justify-center gap-x-2 whitespace-nowrap tabular-nums" data-currency={row.currency}>
                                                <CurrencyCode code={row.currency} />
                                                <span>{$t('tools.pacAllocator.planner.liquidityCopy.custody', {default: 'custody {amount}', values: {amount: formatPlannerMoneyPlain(row.custody_amount, row.currency)}})}</span>
                                                {#if partial(row.ownership_share)}
                                                    <span>· {$t('tools.pacAllocator.planner.liquidityCopy.yourShare', {default: 'your share {amount}', values: {amount: formatPlannerMoneyPlain(row.economic_amount, row.currency, {minorUnit: true})}})}</span>
                                                {:else}
                                                    <span>· {$t('tools.pacAllocator.planner.liquidityCopy.allYours', {default: '100% yours'})}</span>
                                                {/if}
                                            </span>
                                        {:else}
                                            <span class="block {HINT}">{$t('tools.pacAllocator.planner.liquidityCopy.noCash', {default: 'No cash balance on this date.'})}</span>
                                        {/each}
                                    </span>
                                {:else if kind === 'brokers' && snapshot}
                                    <span class="flex w-max min-w-full items-center justify-center gap-x-2 whitespace-nowrap {HINT}">
                                        {#if snapshot.observed_currencies.length > 0}
                                            <span>{$t('tools.pacAllocator.planner.brokerCopy.currenciesSeen', {default: 'Currencies seen:'})}</span>
                                            {#each snapshot.observed_currencies as currency (currency)}<CurrencyCode code={currency} />{/each}
                                        {:else}
                                            {$t('tools.pacAllocator.planner.brokerCopy.noCurrencies', {default: 'No currency seen yet: one mode in the valuation currency is proposed.'})}
                                        {/if}
                                    </span>
                                {/if}
                            {/snippet}
                        </BrokerTile>
                    </li>
                {/each}
            </ul>
        {/if}

        <p class="mt-3 {HINT}">
            {kind === 'liquidity'
                ? $t('tools.pacAllocator.planner.liquidityCopy.rule', {default: 'Each currency of a Broker becomes one liquidity row. The amount to use starts from the whole available amount: you can lower it after the copy.'})
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
