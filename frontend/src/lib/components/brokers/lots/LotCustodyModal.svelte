<script lang="ts">
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {assetStoreVersion, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {schemas} from '$lib/api';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {ArrowRightLeft, Info, Minus, Plus, X} from 'lucide-svelte';
    import type {z} from 'zod';

    type LotSummarySchema = z.infer<typeof schemas.LotSummarySchema>;
    type LotTimelineEventSchema = z.infer<typeof schemas.LotTimelineEventSchema>;
    type CustodyGroup = {
        key: string;
        brokerId: number | null;
        custodyType: string;
        broker: BrokerLike | null;
        quantity: number;
    };
    type EventDetailItem = {
        label: string;
        value: string;
        tone?: 'positive' | 'negative';
    };

    interface Props {
        open: boolean;
        lot: LotSummarySchema | null;
        history: ReadonlyArray<LotTimelineEventSchema>;
        brokers: ReadonlyArray<BrokerLike>;
        currency: string;
        onClose: () => void;
        onGotoTransaction?: (transactionId: number) => void;
    }

    type EventMarkerKind = 'open' | 'transfer' | 'close' | 'split';

    let {open, lot, history = [], brokers = [], currency, onClose, onGotoTransaction}: Props = $props();

    let selectedHistoryKey = $state<string | null>(null);

    function unwrapScalar<T>(value: T | T[] | null | undefined): T | null | undefined {
        return Array.isArray(value) ? (value[0] ?? null) : value;
    }

    function getBroker(brokerId: number | (number | null)[] | null | undefined): BrokerLike | null {
        const scalarBrokerId = unwrapScalar<number | null>(brokerId) ?? null;
        if (scalarBrokerId == null) return null;
        return brokers.find((broker) => broker.id === scalarBrokerId) ?? {id: scalarBrokerId, name: `#${scalarBrokerId}`};
    }

    function getBrokerName(brokerId: number | (number | null)[] | null | undefined): string {
        const scalarBrokerId = unwrapScalar<number | null>(brokerId) ?? null;
        if (scalarBrokerId == null) return $_('brokers.lots.modal.inTransit');
        return getBroker(scalarBrokerId)?.name ?? `#${scalarBrokerId}`;
    }

    function parseNumber(value: string | number | (string | number | null)[] | null | undefined): number | null {
        const scalar = Array.isArray(value) ? (value.find((entry) => entry != null) ?? null) : value;
        if (scalar == null) return null;
        const parsed = typeof scalar === 'number' ? scalar : Number.parseFloat(scalar);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function formatDate(value: string, kind: 'long' | 'short' = 'long'): string {
        const match = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        const date = match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString($currentLanguage || undefined, kind === 'short' ? {day: '2-digit', month: '2-digit'} : {year: 'numeric', month: 'long', day: 'numeric'});
    }

    function formatQuantity(value: string | number | null | undefined, opts: {signed?: boolean} = {}): string {
        const parsed = parseNumber(value);
        if (parsed == null) return '—';
        const abs = Math.abs(parsed);
        const sign = opts.signed ? (parsed > 0 ? '+' : parsed < 0 ? '-' : '') : '';
        return `${sign}${formatDecimalForDisplay(abs, {minFrac: 0, maxFrac: 8})}${assetUnitLabel ? ` ${assetUnitLabel}` : ''}`;
    }

    function formatPrice(value: string | number | null | undefined): string {
        const parsed = parseNumber(value);
        return parsed == null ? '—' : formatCurrencyAmountPlain(parsed, currency);
    }

    function formatSignedCurrency(value: string | number | null | undefined): string {
        const parsed = parseNumber(value);
        return parsed == null ? '—' : formatCurrencyAmountPlain(parsed, currency, {showSign: parsed !== 0});
    }

    function formatPercent(value: string | number | null | undefined): string {
        const parsed = parseNumber(value);
        if (parsed == null) return '—';
        const sign = parsed > 0 ? '+' : '';
        return `${sign}${(parsed * 100).toFixed(2)}%`;
    }

    function signedToneClass(value: number | null): string {
        if (value == null) return 'text-slate-900 dark:text-slate-100';
        if (value > 0) return 'text-emerald-600 dark:text-emerald-400';
        if (value < 0) return 'text-red-500 dark:text-red-400';
        return 'text-slate-500 dark:text-slate-300';
    }

    function eventDetailToneClass(tone?: EventDetailItem['tone']): string {
        if (tone === 'positive') return 'text-emerald-600 dark:text-emerald-400';
        if (tone === 'negative') return 'text-red-500 dark:text-red-400';
        return 'text-slate-700 dark:text-slate-100';
    }

    function stateLabel(state: string): string {
        const key = `brokers.lots.modal.state.${state.toLowerCase()}`;
        const translated = $_(key);
        return translated === key ? state.replaceAll('_', ' ') : translated;
    }

    function directionLabel(direction: 'LONG' | 'SHORT' | null | undefined): string {
        if (direction == null) return '—';
        const key = `brokers.lots.modal.direction.${direction.toLowerCase()}`;
        const translated = $_(key);
        return translated === key ? direction : translated;
    }

    function eventKindLabel(kind: LotTimelineEventSchema['kind']): string {
        const key = `brokers.lots.modal.event.${kind}`;
        const translated = $_(key);
        return translated === key ? kind.replaceAll('_', ' ') : translated;
    }

    function historyKey(event: LotTimelineEventSchema): string {
        return `${event.date}:${event.kind}:${event.transaction_id}:${event.related_transaction_id ?? ''}:${event.fragment_id ?? ''}`;
    }

    function eventMarkerKind(event: LotTimelineEventSchema): EventMarkerKind {
        if (event.kind === 'BUY' || event.kind === 'ADJUSTMENT_IN') return 'open';
        if (event.kind === 'TRANSFER_DEPART' || event.kind === 'TRANSFER_ARRIVE') return 'transfer';
        if (event.kind === 'SPLIT') return 'split';
        return 'close';
    }

    function eventQuantityText(event: LotTimelineEventSchema): string {
        if (event.kind === 'BUY' || event.kind === 'ADJUSTMENT_IN') return formatQuantity(event.quantity, {signed: true});
        if (event.kind === 'SELL' || event.kind === 'ADJUSTMENT_OUT') {
            const parsed = parseNumber(event.quantity);
            return formatQuantity(parsed == null ? null : -Math.abs(parsed), {signed: true});
        }
        if (event.kind === 'SPLIT') {
            const ratio = unwrapScalar<string | null>(event.ratio) ?? null;
            if (ratio == null) return '×';
            return `×${formatDecimalForDisplay(ratio, {minFrac: 0, maxFrac: 8})}`;
        }
        return formatQuantity(event.quantity);
    }

    function eventDescription(event: LotTimelineEventSchema): string {
        if (event.kind === 'TRANSFER_DEPART') {
            const fromName = getBrokerName(event.source_broker_id ?? event.broker_id);
            return `${fromName} → ${$_('brokers.lots.modal.inTransit')}`;
        }
        if (event.kind === 'TRANSFER_ARRIVE') {
            const toName = getBrokerName(event.destination_broker_id ?? event.broker_id);
            return `${$_('brokers.lots.modal.inTransit')} → ${toName}`;
        }
        if (event.kind === 'SPLIT') {
            const ratio = unwrapScalar<string | null>(event.ratio) ?? null;
            return ratio != null ? `${eventKindLabel(event.kind)} ×${formatDecimalForDisplay(ratio, {minFrac: 0, maxFrac: 8})}` : eventKindLabel(event.kind);
        }
        const brokerName = getBrokerName(event.broker_id ?? lot?.opening_broker_id);
        return brokerName ? `${eventKindLabel(event.kind)} ${brokerName}` : eventKindLabel(event.kind);
    }

    function eventDetailItems(event: LotTimelineEventSchema): EventDetailItem[] {
        if (event.kind === 'BUY' || event.kind === 'ADJUSTMENT_IN') {
            const openingPrice = parseNumber(event.open_unit_price ?? event.unit_price);
            return openingPrice == null ? [] : [{label: $_('brokers.lots.modal.historyDetail.openPrice'), value: formatPrice(openingPrice)}];
        }

        if (event.kind === 'SELL' || event.kind === 'ADJUSTMENT_OUT') {
            const items: EventDetailItem[] = [];
            const closePrice = parseNumber(event.close_unit_price ?? event.unit_price);
            const proceeds = parseNumber(event.proceeds);
            const realizedPnl = parseNumber(event.realized_pnl);
            if (closePrice != null) {
                items.push({label: $_('brokers.lots.modal.historyDetail.closePrice'), value: formatPrice(closePrice)});
            }
            if (proceeds != null) {
                items.push({label: $_('brokers.lots.modal.historyDetail.proceeds'), value: formatSignedCurrency(proceeds), tone: proceeds >= 0 ? 'positive' : 'negative'});
            }
            if (realizedPnl != null) {
                items.push({label: $_('brokers.lots.modal.historyDetail.realizedPnl'), value: formatSignedCurrency(realizedPnl), tone: realizedPnl >= 0 ? 'positive' : 'negative'});
            }
            return items;
        }

        if (event.kind === 'SPLIT') {
            const ratio = unwrapScalar<string | null>(event.ratio) ?? null;
            return ratio == null ? [] : [{label: $_('brokers.lots.modal.historyDetail.splitRatio'), value: `×${formatDecimalForDisplay(ratio, {minFrac: 0, maxFrac: 8})}`}];
        }

        if (event.kind === 'TRANSFER_DEPART') {
            return [
                {label: $_('brokers.lots.modal.historyDetail.sourceBroker'), value: getBrokerName(event.source_broker_id ?? event.broker_id)},
                {label: $_('brokers.lots.modal.historyDetail.destinationBroker'), value: $_('brokers.lots.modal.inTransit')},
            ];
        }

        if (event.kind === 'TRANSFER_ARRIVE') {
            return [
                {label: $_('brokers.lots.modal.historyDetail.sourceBroker'), value: $_('brokers.lots.modal.inTransit')},
                {label: $_('brokers.lots.modal.historyDetail.destinationBroker'), value: getBrokerName(event.destination_broker_id ?? event.broker_id)},
            ];
        }

        return [];
    }

    let assetInfo = $derived.by(() => {
        void $assetStoreVersion;
        return lot ? getAssetInfo(lot.asset_id) : null;
    });

    let assetName = $derived(assetInfo?.display_name ?? (lot ? `#${lot.asset_id}` : ''));
    let assetUnitLabel = $derived(assetInfo?.identifier_ticker?.trim() || assetInfo?.display_name || '');
    let lotStates = $derived(lot?.states ?? []);
    let currentCustody = $derived(lot?.current_custody ?? []);
    let groupedCustody = $derived.by<CustodyGroup[]>(() => {
        const groups: CustodyGroup[] = [];
        const byKey = new Map<string, CustodyGroup>();
        for (const slice of currentCustody) {
            const brokerId = unwrapScalar<number | null>(slice.broker_id) ?? null;
            const custodyType = slice.custody_type;
            const key = `${custodyType}:${brokerId ?? 'none'}`;
            const quantity = parseNumber(slice.quantity) ?? 0;
            let group = byKey.get(key);
            if (!group) {
                group = {
                    key,
                    brokerId,
                    custodyType,
                    broker: custodyType === 'BROKER' ? getBroker(brokerId) : null,
                    quantity: 0,
                };
                byKey.set(key, group);
                groups.push(group);
            }
            group.quantity += quantity;
        }
        return groups;
    });
    let sortedHistory = $derived.by(() =>
        [...history].sort((left, right) => {
            const dateOrder = left.date.localeCompare(right.date);
            if (dateOrder !== 0) return dateOrder;
            return left.transaction_id - right.transaction_id;
        }),
    );
    let defaultHistoryKey = $derived.by(() => {
        if (!lot) return null;
        const openingEvent = sortedHistory.find((event) => event.transaction_id === lot.opening_transaction_id);
        return openingEvent ? historyKey(openingEvent) : null;
    });
    let activeHistoryKey = $derived(selectedHistoryKey ?? defaultHistoryKey);
    let activeHistoryEvent = $derived.by(() => {
        if (!activeHistoryKey) return null;
        return sortedHistory.find((event) => historyKey(event) === activeHistoryKey) ?? null;
    });
    let activeTransactionId = $derived(activeHistoryEvent?.transaction_id ?? lot?.opening_transaction_id ?? null);
    let canGotoTransaction = $derived(onGotoTransaction != null && activeTransactionId != null);
    let lotOpeningValue = $derived.by(() => {
        if (!lot) return null;
        const quantity = parseNumber(lot.original_quantity);
        const unitPrice = parseNumber(lot.opening_unit_price);
        return quantity != null && unitPrice != null ? quantity * unitPrice : null;
    });
    let lotCurrentValue = $derived.by(() => (lot ? (parseNumber(lot.total_value) ?? parseNumber(lot.open_value)) : null));
    let lotCumulativeProceeds = $derived.by(() => (lot ? parseNumber(lot.cumulative_proceeds) : null));
    let lotPnl = $derived.by(() => (lot ? parseNumber(lot.pnl) : null));
    let lotRelativeReturn = $derived.by(() => (lot ? parseNumber(lot.relative_return) : null));

    $effect(() => {
        void open;
        void lot?.lot_id;
        selectedHistoryKey = null;
    });

    function handleGotoTransaction() {
        if (onGotoTransaction && activeTransactionId != null) {
            onGotoTransaction(activeTransactionId);
        }
    }
</script>

<ModalBase open={open && lot != null} maxWidth="4xl" onRequestClose={onClose} contentClass="bg-white dark:bg-slate-800" testId="lot-custody-modal">
    {#if lot}
        <div class="flex items-center gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-700">
            <AssetIcon iconUrl={assetInfo?.icon_url ?? null} assetType={assetInfo?.asset_type ?? null} altText={assetName} size="md" />
            <div class="min-w-0 flex-1">
                <h2 class="truncate text-lg font-semibold text-slate-900 dark:text-slate-100" data-testid="lot-custody-modal-title">
                    {$_('brokers.lots.modal.title', {values: {asset: assetName, date: formatDate(lot.opening_date)}})}
                </h2>
                <p class="mt-0.5 text-sm text-slate-500 dark:text-slate-400" data-testid="lot-custody-modal-lot-id">
                    #{lot.lot_id}
                </p>
            </div>
            <button type="button" class="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-100" onclick={onClose} aria-label={$_('common.close')} data-testid="lot-custody-modal-close">
                <X size={18} />
            </button>
        </div>

        <div class="max-h-[70vh] space-y-5 overflow-y-auto px-5 py-5">
            <section class="space-y-3" data-testid="lot-custody-modal-summary">
                <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                    {$_('brokers.lots.modal.summary')}
                </h3>
                <dl class="grid gap-3 sm:grid-cols-2">
                    <div class="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
                        <dt class="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{$_('brokers.lots.modal.directionLabel')}</dt>
                        <dd class="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">{directionLabel(lot.direction)}</dd>
                    </div>
                    <div class="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
                        <dt class="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{$_('brokers.lots.modal.originalQuantity')}</dt>
                        <dd class="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">{formatQuantity(lot.original_quantity)}</dd>
                    </div>
                    <div class="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
                        <dt class="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{$_('brokers.lots.modal.openQuantity')}</dt>
                        <dd class="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">{formatQuantity(lot.open_quantity)}</dd>
                    </div>
                    <div class="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
                        <dt class="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{$_('brokers.lots.modal.openingPrice')}</dt>
                        <dd class="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">{formatPrice(lot.opening_unit_price)}</dd>
                    </div>
                    <div class="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
                        <dt class="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{$_('brokers.lots.modal.openingValue')}</dt>
                        <dd class="mt-1 text-sm font-medium tabular-nums text-slate-900 dark:text-slate-100">{formatPrice(lotOpeningValue)}</dd>
                    </div>
                    <div class="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
                        <dt class="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{$_('brokers.lots.modal.currentValue')}</dt>
                        <dd class="mt-1 text-sm font-medium tabular-nums text-slate-900 dark:text-slate-100">{formatPrice(lotCurrentValue)}</dd>
                    </div>
                    <div class="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
                        <dt class="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{$_('brokers.lots.modal.cumulativeProceeds')}</dt>
                        <dd class="mt-1 text-sm font-medium tabular-nums text-slate-900 dark:text-slate-100">{formatPrice(lotCumulativeProceeds)}</dd>
                    </div>
                    <div class="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
                        <dt class="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{$_('brokers.lots.modal.fifoPnl')}</dt>
                        <dd class={`mt-1 text-sm font-medium tabular-nums ${signedToneClass(lotPnl)}`}>{formatSignedCurrency(lotPnl)}</dd>
                    </div>
                    <div class="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70">
                        <dt class="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{$_('brokers.lots.modal.openReturn')}</dt>
                        <dd class={`mt-1 text-sm font-medium tabular-nums ${signedToneClass(lotRelativeReturn)}`}>{formatPercent(lotRelativeReturn)}</dd>
                    </div>
                    <div class="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70 sm:col-span-2">
                        <dt class="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{$_('common.status')}</dt>
                        <dd class="mt-2 flex flex-wrap gap-2" data-testid="lot-custody-modal-states">
                            {#if lotStates.length > 0}
                                {#each lotStates as state}
                                    <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                                        {stateLabel(state)}
                                    </span>
                                {/each}
                            {:else}
                                <span class="text-sm text-slate-500 dark:text-slate-400">
                                    {$_('brokers.lots.modal.emptyStates')}
                                </span>
                            {/if}
                        </dd>
                    </div>
                </dl>
            </section>

            <section class="space-y-3" data-testid="lot-custody-modal-current-custody">
                <div class="flex items-center gap-2">
                    <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                        {$_('brokers.lots.modal.currentCustody')}
                    </h3>
                    <Tooltip text={$_('brokers.lots.modal.absoluteQuantityTooltip')} position="top" maxWidth="280px">
                        <span class="inline-flex text-slate-400 hover:text-libre-green dark:hover:text-emerald-400" data-testid="lot-custody-modal-absolute-quantity-info">
                            <Info size={14} />
                        </span>
                    </Tooltip>
                </div>

                {#if currentCustody.length > 0}
                    <div class="space-y-2">
                        <div class="grid gap-2 sm:grid-cols-2" data-testid="lot-custody-modal-custody-summary">
                            {#each groupedCustody as group, index}
                                <div class="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-900/70" data-testid={`lot-custody-modal-custody-summary-row-${index}`}>
                                    <div class="min-w-0 flex-1">
                                        {#if group.custodyType === 'BROKER' && group.broker}
                                            <BrokerBadge broker={group.broker} {brokers} />
                                        {:else}
                                            <div class="inline-flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                                                <ArrowRightLeft size={16} class="text-blue-500 dark:text-blue-400" />
                                                <span>{$_('brokers.lots.modal.inTransit')}</span>
                                            </div>
                                        {/if}
                                    </div>
                                    <div class="shrink-0 text-right text-sm font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                                        {formatQuantity(group.quantity)}
                                    </div>
                                </div>
                            {/each}
                        </div>

                        <div class="text-xs font-medium uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400" data-testid="lot-custody-modal-custody-fragments-label">
                            {$_('brokers.lots.modal.custodyFragments')}
                        </div>
                        {#each currentCustody as slice, index}
                            <div class="flex items-center justify-between gap-3 rounded-xl border border-slate-200 px-4 py-3 dark:border-slate-700" data-testid={`lot-custody-modal-custody-row-${index}`}>
                                <div class="min-w-0 flex-1">
                                    {#if slice.custody_type === 'BROKER' && getBroker(slice.broker_id)}
                                        <BrokerBadge broker={getBroker(slice.broker_id) ?? {id: -1, name: '—'}} {brokers} />
                                    {:else}
                                        <div class="inline-flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                                            <ArrowRightLeft size={16} class="text-blue-500 dark:text-blue-400" />
                                            <span>{$_('brokers.lots.modal.inTransit')}</span>
                                        </div>
                                    {/if}
                                </div>
                                <div class="shrink-0 text-right text-sm font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                                    {formatQuantity(slice.quantity)}
                                </div>
                            </div>
                        {/each}
                    </div>
                {:else}
                    <div class="rounded-xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400" data-testid="lot-custody-modal-current-custody-empty">
                        {$_('brokers.lots.modal.emptyCustody')}
                    </div>
                {/if}
            </section>

            <section class="space-y-3" data-testid="lot-custody-modal-history">
                <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                    {$_('brokers.lots.modal.history')}
                </h3>

                {#if sortedHistory.length > 0}
                    <div class="space-y-2">
                        {#each sortedHistory as event, index}
                            {@const rowKey = historyKey(event)}
                            {@const markerKind = eventMarkerKind(event)}
                            {@const detailItems = eventDetailItems(event)}
                            <button
                                type="button"
                                class="flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors {activeHistoryKey === rowKey
                                    ? 'border-libre-green bg-emerald-50/60 dark:border-emerald-500 dark:bg-emerald-900/15'
                                    : 'border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700/50'}"
                                onclick={() => (selectedHistoryKey = rowKey)}
                                aria-pressed={activeHistoryKey === rowKey}
                                data-testid={`lot-custody-modal-history-row-${index}`}
                            >
                                <div class="flex w-14 shrink-0 items-center pt-0.5 text-xs font-semibold tabular-nums text-slate-500 dark:text-slate-400">
                                    {formatDate(event.date, 'short')}
                                </div>

                                <div class="flex min-w-0 flex-1 items-start gap-3">
                                    <div
                                        class="mt-0.5 flex h-7 min-w-7 items-center justify-center rounded-full text-xs font-semibold {markerKind === 'open'
                                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                                            : markerKind === 'transfer'
                                              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                                              : markerKind === 'close'
                                                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                                                : 'bg-violet-100 px-2 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300'}"
                                    >
                                        {#if markerKind === 'open'}
                                            <Plus size={14} />
                                        {:else if markerKind === 'transfer'}
                                            <ArrowRightLeft size={14} />
                                        {:else if markerKind === 'close'}
                                            <Minus size={14} />
                                        {:else}
                                            ×
                                        {/if}
                                    </div>
                                    <div class="min-w-0 flex-1">
                                        <div class="truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                                            {eventDescription(event)}
                                        </div>
                                        <div class="mt-1 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                                            {eventKindLabel(event.kind)}
                                        </div>
                                        {#if detailItems.length > 0}
                                            <div class="mt-2 flex flex-wrap gap-2" data-testid={`lot-custody-modal-history-details-${index}`}>
                                                {#each detailItems as item}
                                                    <span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-1 text-[11px] dark:bg-slate-700/70">
                                                        <span class="uppercase tracking-wide text-slate-500 dark:text-slate-400">{item.label}</span>
                                                        <span class={`font-semibold tabular-nums ${eventDetailToneClass(item.tone)}`}>{item.value}</span>
                                                    </span>
                                                {/each}
                                            </div>
                                        {/if}
                                    </div>
                                </div>

                                <div class="shrink-0 pl-2 text-right text-sm font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                                    {eventQuantityText(event)}
                                </div>
                            </button>
                        {/each}
                    </div>
                {:else}
                    <div class="rounded-xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400" data-testid="lot-custody-modal-history-empty">
                        {$_('brokers.lots.modal.emptyHistory')}
                    </div>
                {/if}
            </section>
        </div>

        <div class="flex items-center justify-end gap-3 border-t border-slate-200 px-5 py-4 dark:border-slate-700">
            <button type="button" class="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-100 dark:hover:bg-slate-600" onclick={onClose} data-testid="lot-custody-modal-footer-close">
                {$_('common.close')}
            </button>
            <button
                type="button"
                class="rounded-lg bg-libre-green px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-libre-green/90 disabled:cursor-not-allowed disabled:opacity-50"
                onclick={handleGotoTransaction}
                disabled={!canGotoTransaction}
                data-testid="lot-custody-modal-footer-goto-transaction"
            >
                {$_('brokers.lots.modal.goToTransaction')}
            </button>
        </div>
    {/if}
</ModalBase>
