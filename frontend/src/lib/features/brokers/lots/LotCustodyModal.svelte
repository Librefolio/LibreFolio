<script lang="ts">
    import {_} from '$lib/i18n';
    import {assetStoreVersion, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {schemas} from '$lib/api';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {formatExactDecimal, priceFractionDigits} from '$lib/utils/core/formatFixed';
    import {maskableQuantity} from '$lib/utils/privacy/maskable';
    import {SIGN_TEXT} from '$lib/theme/toneClasses';
    import {safeDecimal} from '$lib/types';
    import {ArrowRightLeft, Info, Minus, Plus, X} from 'lucide-svelte';
    import type {z} from 'zod';
    import {formatPercent as sharedFormatPercent} from '$lib/utils/core/formatPercent';
    import {closureValueLabelKey, compareHistoryEvents, eventMarkerKind, getBroker as sharedGetBroker, groupCustodySlices, historyKey, unwrapScalar, type EventMarkerKind} from './lotCustodyModalHelpers';
    import {eventLabelKind, isUnknownOrNonZero} from './lotChartShared';
    import {formatLotQuantity} from './unifiedLotsTableHelpers';
    import {uiLocale} from '$lib/stores/app/uiLocale';

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

    let {open, lot, history = [], brokers = [], currency, onClose, onGotoTransaction}: Props = $props();

    let selectedHistoryKey = $state<string | null>(null);

    const getBroker = (brokerId: number | (number | null)[] | null | undefined): BrokerLike | null => sharedGetBroker(brokerId, brokers);

    function getBrokerName(brokerId: number | (number | null)[] | null | undefined): string {
        const scalarBrokerId = unwrapScalar<number | null>(brokerId) ?? null;
        if (scalarBrokerId == null) return $_('brokers.lots.modal.inTransit');
        return getBroker(scalarBrokerId)?.name ?? `#${scalarBrokerId}`;
    }

    /** Local name for this chart's numeric unwrap. Delegates to the shared
     *  `safeDecimal`: the body used to be copied five times, and two of those
     *  copies went through `safeString`, which answers `null` for a value that
     *  is already a number. */
    const parseNumber = (value: unknown): number | null => safeDecimal(value);

    function formatDate(value: string, kind: 'long' | 'short' = 'long'): string {
        const match = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        const date = match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString(uiLocale(), kind === 'short' ? {day: '2-digit', month: '2-digit'} : {year: 'numeric', month: 'long', day: 'numeric'});
    }

    /** A lot quantity; masked under privacy (D5′), with the sign and the unit left outside. */
    function formatQuantity(value: string | number | null | undefined, opts: {signed?: boolean} = {}): string {
        const parsed = parseNumber(value);
        if (parsed == null) return '—';
        const abs = Math.abs(parsed);
        const sign = opts.signed ? (parsed > 0 ? '+' : parsed < 0 ? '-' : '') : '';
        // C-97c: the lots' shared formatter, up to 10 decimals and never `1e-7` (formatExactDecimal wrote a number through String())
        return `${sign}${maskableQuantity(formatLotQuantity(abs))}${assetUnitLabel ? ` ${assetUnitLabel}` : ''}`;
    }

    function formatPrice(value: string | number | null | undefined): string {
        const parsed = parseNumber(value);
        return parsed == null ? '—' : formatCurrencyAmountPlain(parsed, currency);
    }

    /**
     * A price per unit — opening, closing. Public: a price is not patrimony and a purchase
     * price is admissible (product owner, 2026-09-22), and with the quantity masked (D5′)
     * price × quantity rebuilds nothing. Totals keep `formatPrice`, which masks.
     */
    function formatUnitPrice(value: unknown): string {
        const parsed = parseNumber(value);
        if (parsed == null) return '—';
        // C-97c: a price under a cent keeps 4 significant digits instead of reading 0.00.
        const {min, max} = priceFractionDigits(parsed);
        return formatCurrencyAmountPlain(parsed, currency, {minFraction: min, maxFraction: max, sensitivity: 'public'});
    }

    function formatSignedCurrency(value: string | number | null | undefined): string {
        const parsed = parseNumber(value);
        return parsed == null ? '—' : formatCurrencyAmountPlain(parsed, currency, {showSign: parsed !== 0});
    }

    /** These come from the API as fractions, hence scale 100. */
    const formatPercent = (value: unknown): string => sharedFormatPercent(parseNumber(value), {scale: 100});

    function signedToneClass(value: number | null): string {
        if (value == null) return 'text-lf-primary';
        if (value > 0) return SIGN_TEXT.portfolio.gain;
        if (value < 0) return SIGN_TEXT.portfolio.loss;
        return SIGN_TEXT.portfolio.zero;
    }

    function eventDetailToneClass(tone?: EventDetailItem['tone']): string {
        if (tone === 'positive') return SIGN_TEXT.portfolio.gain;
        if (tone === 'negative') return SIGN_TEXT.portfolio.loss;
        return 'text-lf-primary';
    }

    /* colour: closest role, to review: open/transfer/close markers on success/info/warning tints; "other" stays categorical violet until the categorical roles exist */
    function markerClass(kind: string): string {
        if (kind === 'open') return 'bg-lf-success-soft text-lf-success-on-soft';
        if (kind === 'transfer') return 'bg-lf-info-soft text-lf-info-on-soft';
        if (kind === 'close') return 'bg-lf-warning-soft text-lf-warning-on-soft';
        return 'bg-violet-100 px-2 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300';
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

    /** The label of an event's kind; a transfer leg read at the scope's edge gets its transfer label (J-48). */
    function eventKindLabel(kind: LotTimelineEventSchema['kind'] | 'TRANSFER_IN' | 'TRANSFER_OUT'): string {
        const key = `brokers.lots.modal.event.${kind}`;
        const translated = $_(key);
        return translated === key ? kind.replaceAll('_', ' ') : translated;
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
            return `×${formatExactDecimal(ratio, {minFrac: 0, maxFrac: 8})}`;
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
            return ratio != null ? `${eventKindLabel(event.kind)} ×${formatExactDecimal(ratio, {minFrac: 0, maxFrac: 8})}` : eventKindLabel(event.kind);
        }
        const brokerName = getBrokerName(event.broker_id ?? lot?.opening_broker_id);
        const label = eventKindLabel(eventLabelKind(event));
        return brokerName ? `${label} ${brokerName}` : label;
    }

    function eventDetailItems(event: LotTimelineEventSchema): EventDetailItem[] {
        if (event.kind === 'BUY' || event.kind === 'ADJUSTMENT_IN') {
            const openingPrice = parseNumber(event.open_unit_price ?? event.unit_price);
            return openingPrice == null ? [] : [{label: $_('brokers.lots.modal.historyDetail.openPrice'), value: formatUnitPrice(openingPrice)}];
        }

        if (event.kind === 'SELL' || event.kind === 'ADJUSTMENT_OUT') {
            const items: EventDetailItem[] = [];
            const closePrice = parseNumber(event.close_unit_price ?? event.unit_price);
            const proceeds = parseNumber(event.proceeds);
            const realizedPnl = parseNumber(event.realized_pnl);
            if (closePrice != null) {
                items.push({label: $_('brokers.lots.modal.historyDetail.closePrice'), value: formatUnitPrice(closePrice)});
            }
            if (proceeds != null) {
                items.push({label: $_(closureValueLabelKey(event.kind)), value: formatSignedCurrency(proceeds), tone: proceeds >= 0 ? 'positive' : 'negative'});
            }
            if (realizedPnl != null) {
                items.push({label: $_('brokers.lots.modal.historyDetail.realizedPnl'), value: formatSignedCurrency(realizedPnl), tone: realizedPnl >= 0 ? 'positive' : 'negative'});
            }
            return items;
        }

        if (event.kind === 'SPLIT') {
            const ratio = unwrapScalar<string | null>(event.ratio) ?? null;
            return ratio == null ? [] : [{label: $_('brokers.lots.modal.historyDetail.splitRatio'), value: `×${formatExactDecimal(ratio, {minFrac: 0, maxFrac: 8})}`}];
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
    let groupedCustody = $derived.by<CustodyGroup[]>(() => groupCustodySlices(currentCustody, brokers));
    let sortedHistory = $derived.by(() => [...history].sort(compareHistoryEvents));
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
    // The backend's cost of the lot at opening (U8): null without the opening-date rate, never rebuilt as quantity × price.
    let lotOpeningValue = $derived.by(() => (lot ? parseNumber(lot.original_cost) : null));
    let lotCurrentValue = $derived.by(() => (lot ? (parseNumber(lot.total_value) ?? parseNumber(lot.open_value)) : null));
    let lotCumulativeProceeds = $derived.by(() => (lot ? parseNumber(lot.cumulative_proceeds) : null));
    let lotPnl = $derived.by(() => (lot ? parseNumber(lot.pnl) : null));
    let lotRelativeReturn = $derived.by(() => (lot ? parseNumber(lot.relative_return) : null));
    let lotAssetIncome = $derived.by(() => (lot ? parseNumber(lot.asset_income) : null));
    let lotMarketPnl = $derived.by(() => (lot ? parseNumber(lot.market_pnl) : null));
    let lotTotalPnl = $derived.by(() => (lot ? parseNumber(lot.total_pnl) : null));
    let lotCashYield = $derived.by(() => (lot ? parseNumber(lot.cash_yield) : null));
    let lotTotalReturn = $derived.by(() => (lot ? parseNumber(lot.total_return) : null));
    let lotAllocatedFees = $derived.by(() => (lot ? parseNumber(lot.allocated_fees) : null));
    let lotAllocatedTaxes = $derived.by(() => (lot ? parseNumber(lot.allocated_taxes) : null));
    let lotNetTotalPnl = $derived.by(() => (lot ? parseNumber(lot.net_total_pnl) : null));
    let lotNetTotalReturn = $derived.by(() => (lot ? parseNumber(lot.net_total_return) : null));
    let lotNetMetricsStatus = $derived.by(() => (lot ? (unwrapScalar<string | null>(lot.net_metrics_status) ?? 'AVAILABLE') : 'AVAILABLE'));
    // An amount the API could not value (null) keeps its row, shown as «—», never hidden as if it were zero.
    let lotHasNetCosts = $derived(lot != null && (isUnknownOrNonZero(lotAllocatedFees) || isUnknownOrNonZero(lotAllocatedTaxes)));
    let lotNetAvailable = $derived(lotNetMetricsStatus !== 'UNAVAILABLE');
    let lotValueSource = $derived.by(() => (lot ? (unwrapScalar<string | null>(lot.value_source) ?? null) : null));
    let lotIsEstimated = $derived(lotValueSource === 'ESTIMATED_AT_COST');
    let lotHasIncome = $derived(lot != null && isUnknownOrNonZero(lotAssetIncome));

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

<ModalBase open={open && lot != null} maxWidth="4xl" onRequestClose={onClose} testId="lot-custody-modal">
    {#if lot}
        <div class="flex items-center gap-3 border-b border-lf-subtle px-5 py-4">
            <AssetIcon iconUrl={assetInfo?.icon_url ?? null} assetType={assetInfo?.asset_type ?? null} altText={assetName} size="md" />
            <div class="min-w-0 flex-1">
                <h2 class="truncate text-lg font-semibold text-lf-primary" data-testid="lot-custody-modal-title">
                    {$_('brokers.lots.modal.title', {values: {asset: assetName, date: formatDate(lot.opening_date)}})}
                </h2>
                <p class="mt-0.5 text-sm text-lf-muted" data-testid="lot-custody-modal-lot-id">
                    #{lot.lot_id}
                </p>
            </div>
            <button type="button" class="rounded-lg p-2 text-lf-muted transition-colors hover:bg-lf-hover hover:text-lf-secondary" onclick={onClose} aria-label={$_('common.close')} data-testid="lot-custody-modal-close">
                <X size={18} />
            </button>
        </div>

        <div class="max-h-[70vh] space-y-5 overflow-y-auto px-5 py-5">
            <section class="space-y-3" data-testid="lot-custody-modal-summary">
                <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-lf-muted">
                    {$_('brokers.lots.modal.summary')}
                </h3>
                <dl class="grid gap-3 sm:grid-cols-2">
                    <div class="rounded-xl bg-lf-panel px-4 py-3">
                        <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.modal.directionLabel')}</dt>
                        <dd class="mt-1 text-sm font-medium text-lf-primary">{directionLabel(lot.direction)}</dd>
                    </div>
                    <div class="rounded-xl bg-lf-panel px-4 py-3">
                        <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.originalQuantity')}</dt>
                        <dd class="mt-1 text-sm font-medium text-lf-primary">{formatQuantity(lot.original_quantity)}</dd>
                    </div>
                    <div class="rounded-xl bg-lf-panel px-4 py-3">
                        <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.openQuantity')}</dt>
                        <dd class="mt-1 text-sm font-medium text-lf-primary">{formatQuantity(lot.open_quantity)}</dd>
                    </div>
                    <div class="rounded-xl bg-lf-panel px-4 py-3">
                        <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.modal.openingPrice')}</dt>
                        <dd class="mt-1 text-sm font-medium text-lf-primary">{formatUnitPrice(lot.opening_unit_price)}</dd>
                    </div>
                    <div class="rounded-xl bg-lf-panel px-4 py-3">
                        <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.modal.openingValue')}</dt>
                        <dd class="mt-1 text-sm font-medium tabular-nums text-lf-primary" data-testid="lot-custody-modal-opening-value">{formatPrice(lotOpeningValue)}</dd>
                    </div>
                    <div class="rounded-xl bg-lf-panel px-4 py-3">
                        <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.currentValue')}</dt>
                        <dd class="mt-1 text-sm font-medium tabular-nums text-lf-primary">{formatPrice(lotCurrentValue)}</dd>
                        {#if lotIsEstimated}
                            <p class="mt-1 inline-flex items-center gap-1 text-xs font-medium text-lf-warning" data-testid="lot-custody-modal-value-source">
                                <Info size={12} />
                                {$_('brokers.lots.modal.estimatedAtCost')}
                            </p>
                        {/if}
                    </div>
                    <div class="rounded-xl bg-lf-panel px-4 py-3">
                        <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.modal.cumulativeProceeds')}</dt>
                        <dd class="mt-1 text-sm font-medium tabular-nums text-lf-primary">{formatPrice(lotCumulativeProceeds)}</dd>
                    </div>
                    {#if lotHasIncome}
                        <div class="rounded-xl bg-lf-panel px-4 py-3">
                            <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.modal.assetIncome')}</dt>
                            <dd class={`mt-1 text-sm font-medium tabular-nums ${signedToneClass(lotAssetIncome)}`} data-testid="lot-custody-modal-asset-income">{formatSignedCurrency(lotAssetIncome)}</dd>
                        </div>
                    {/if}
                    {#if lotMarketPnl != null}
                        <div class="rounded-xl bg-lf-panel px-4 py-3">
                            <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.modal.marketPnl')}</dt>
                            <dd class={`mt-1 text-sm font-medium tabular-nums ${signedToneClass(lotMarketPnl)}`} data-testid="lot-custody-modal-market-pnl">{formatSignedCurrency(lotMarketPnl)}</dd>
                        </div>
                    {/if}
                    <div class="rounded-xl bg-lf-panel px-4 py-3">
                        <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.fifoPnl')}</dt>
                        <dd class={`mt-1 text-sm font-medium tabular-nums ${signedToneClass(lotPnl)}`}>{formatSignedCurrency(lotPnl)}</dd>
                    </div>
                    {#if lotTotalPnl != null}
                        <div class="rounded-xl bg-lf-panel px-4 py-3">
                            <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.totalPnl')}</dt>
                            <dd class={`mt-1 text-sm font-medium tabular-nums ${signedToneClass(lotTotalPnl)}`} data-testid="lot-custody-modal-total-pnl">{formatSignedCurrency(lotTotalPnl)}</dd>
                        </div>
                    {/if}
                    <div class="rounded-xl bg-lf-panel px-4 py-3">
                        <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.openReturn')}</dt>
                        <dd class={`mt-1 text-sm font-medium tabular-nums ${signedToneClass(lotRelativeReturn)}`}>{formatPercent(lotRelativeReturn)}</dd>
                    </div>
                    {#if lotTotalReturn != null}
                        <div class="rounded-xl bg-lf-panel px-4 py-3">
                            <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.modal.totalReturn')}</dt>
                            <dd class={`mt-1 text-sm font-medium tabular-nums ${signedToneClass(lotTotalReturn)}`} data-testid="lot-custody-modal-total-return">{formatPercent(lotTotalReturn)}</dd>
                        </div>
                    {/if}
                    {#if lotHasNetCosts}
                        <div class="rounded-xl bg-lf-panel px-4 py-3 sm:col-span-2" data-testid="lot-custody-modal-net-breakdown">
                            <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.modal.netBreakdown')}</dt>
                            <dd class="mt-2 space-y-1 text-sm tabular-nums text-lf-primary">
                                <div class="flex items-center justify-between gap-4">
                                    <span class="text-lf-muted">{$_('brokers.lots.modal.grossTotalPnl')}</span>
                                    <span class={`font-medium ${signedToneClass(lotTotalPnl)}`}>{formatSignedCurrency(lotTotalPnl)}</span>
                                </div>
                                <div class="flex items-center justify-between gap-4">
                                    <span class="text-lf-muted">− {$_('brokers.lots.modal.fees')}</span>
                                    <span class="font-medium {SIGN_TEXT.portfolio.loss}" data-testid="lot-custody-modal-allocated-fees">{formatPrice(lotAllocatedFees)}</span>
                                </div>
                                <div class="flex items-center justify-between gap-4">
                                    <span class="text-lf-muted">− {$_('brokers.lots.modal.taxes')}</span>
                                    <span class="font-medium {SIGN_TEXT.portfolio.loss}" data-testid="lot-custody-modal-allocated-taxes">{formatPrice(lotAllocatedTaxes)}</span>
                                </div>
                                <div class="flex items-center justify-between gap-4 border-t border-lf-subtle pt-1">
                                    <span class="font-medium text-lf-secondary">{$_('brokers.lots.modal.netTotalPnl')}</span>
                                    {#if lotNetAvailable}
                                        <span class={`font-semibold ${signedToneClass(lotNetTotalPnl)}`} data-testid="lot-custody-modal-net-total-pnl">{formatSignedCurrency(lotNetTotalPnl)}</span>
                                    {:else}
                                        <span class="font-semibold text-lf-muted" title={$_('brokers.lots.netMetricsUnavailable')} data-testid="lot-custody-modal-net-total-pnl">—</span>
                                    {/if}
                                </div>
                                {#if lotNetTotalReturn != null || !lotNetAvailable}
                                    <div class="flex items-center justify-between gap-4">
                                        <span class="text-lf-muted">{$_('brokers.lots.modal.netTotalReturn')}</span>
                                        {#if lotNetAvailable}
                                            <span class={`font-medium ${signedToneClass(lotNetTotalReturn)}`} data-testid="lot-custody-modal-net-total-return">{formatPercent(lotNetTotalReturn)}</span>
                                        {:else}
                                            <span class="font-medium text-lf-muted" title={$_('brokers.lots.netMetricsUnavailable')} data-testid="lot-custody-modal-net-total-return">—</span>
                                        {/if}
                                    </div>
                                {/if}
                            </dd>
                        </div>
                    {/if}
                    {#if lotHasIncome && lotCashYield != null}
                        <div class="rounded-xl bg-lf-panel px-4 py-3">
                            <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('brokers.lots.modal.cashYield')}</dt>
                            <dd class={`mt-1 text-sm font-medium tabular-nums ${signedToneClass(lotCashYield)}`} data-testid="lot-custody-modal-cash-yield">{formatPercent(lotCashYield)}</dd>
                        </div>
                    {/if}
                    <div class="rounded-xl bg-lf-panel px-4 py-3 sm:col-span-2">
                        <dt class="text-xs font-medium uppercase tracking-wide text-lf-muted">{$_('common.status')}</dt>
                        <dd class="mt-2 flex flex-wrap gap-2" data-testid="lot-custody-modal-states">
                            {#if lotStates.length > 0}
                                {#each lotStates as state}
                                    <span class="rounded-full bg-lf-success-soft px-2.5 py-1 text-xs font-medium text-lf-success-on-soft">
                                        {stateLabel(state)}
                                    </span>
                                {/each}
                            {:else}
                                <span class="text-sm text-lf-muted">
                                    {$_('brokers.lots.modal.emptyStates')}
                                </span>
                            {/if}
                        </dd>
                    </div>
                </dl>
            </section>

            <section class="space-y-3" data-testid="lot-custody-modal-current-custody">
                <div class="flex items-center gap-2">
                    <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-lf-muted">
                        {$_('brokers.lots.modal.currentCustody')}
                    </h3>
                    <Tooltip text={$_('brokers.lots.modal.absoluteQuantityTooltip')} position="top" maxWidth="280px">
                        <span class="inline-flex text-lf-muted hover:text-lf-link" data-testid="lot-custody-modal-absolute-quantity-info">
                            <Info size={14} />
                        </span>
                    </Tooltip>
                </div>

                {#if currentCustody.length > 0}
                    <div class="space-y-2">
                        <div class="grid gap-2 sm:grid-cols-2" data-testid="lot-custody-modal-custody-summary">
                            {#each groupedCustody as group, index}
                                <div class="flex items-center justify-between gap-3 rounded-xl bg-lf-panel px-4 py-3" data-testid={`lot-custody-modal-custody-summary-row-${index}`}>
                                    <div class="min-w-0 flex-1">
                                        {#if group.custodyType === 'BROKER' && group.broker}
                                            <BrokerBadge broker={group.broker} {brokers} />
                                        {:else}
                                            <div class="inline-flex items-center gap-2 text-sm font-medium text-lf-secondary">
                                                <ArrowRightLeft size={16} class="text-lf-info" />
                                                <!-- colour: closest role, to review: in-transit blue icon on info; same blue as the transfer marker -->
                                                <span>{$_('brokers.lots.modal.inTransit')}</span>
                                            </div>
                                        {/if}
                                    </div>
                                    <div class="shrink-0 text-right text-sm font-semibold tabular-nums text-lf-primary">
                                        {formatQuantity(group.quantity)}
                                    </div>
                                </div>
                            {/each}
                        </div>

                        <div class="text-xs font-medium uppercase tracking-[0.16em] text-lf-muted" data-testid="lot-custody-modal-custody-fragments-label">
                            {$_('brokers.lots.modal.custodyFragments')}
                        </div>
                        {#each currentCustody as slice, index}
                            <div class="flex items-center justify-between gap-3 rounded-xl border border-lf-subtle px-4 py-3" data-testid={`lot-custody-modal-custody-row-${index}`}>
                                <div class="min-w-0 flex-1">
                                    {#if slice.custody_type === 'BROKER' && getBroker(slice.broker_id)}
                                        <BrokerBadge broker={getBroker(slice.broker_id) ?? {id: -1, name: '—'}} {brokers} />
                                    {:else}
                                        <div class="inline-flex items-center gap-2 text-sm font-medium text-lf-secondary">
                                            <ArrowRightLeft size={16} class="text-lf-info" />
                                            <!-- colour: closest role, to review: in-transit blue icon on info; same blue as the transfer marker -->
                                            <span>{$_('brokers.lots.modal.inTransit')}</span>
                                        </div>
                                    {/if}
                                </div>
                                <div class="shrink-0 text-right text-sm font-semibold tabular-nums text-lf-primary">
                                    {formatQuantity(slice.quantity)}
                                </div>
                            </div>
                        {/each}
                    </div>
                {:else}
                    <div class="rounded-xl border border-dashed border-lf-subtle px-4 py-6 text-sm text-lf-muted" data-testid="lot-custody-modal-current-custody-empty">
                        {$_('brokers.lots.modal.emptyCustody')}
                    </div>
                {/if}
            </section>

            <section class="space-y-3" data-testid="lot-custody-modal-history">
                <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-lf-muted">
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
                                class="flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors {activeHistoryKey === rowKey ? 'border-lf-checked bg-lf-selected' : 'border-lf-subtle bg-lf-card hover:bg-lf-hover'}"
                                onclick={() => (selectedHistoryKey = rowKey)}
                                aria-pressed={activeHistoryKey === rowKey}
                                data-testid={`lot-custody-modal-history-row-${index}`}
                            >
                                <div class="flex w-14 shrink-0 items-center pt-0.5 text-xs font-semibold tabular-nums text-lf-muted">
                                    {formatDate(event.date, 'short')}
                                </div>

                                <div class="flex min-w-0 flex-1 items-start gap-3">
                                    <div class="mt-0.5 flex h-7 min-w-7 items-center justify-center rounded-full text-xs font-semibold {markerClass(markerKind)}">
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
                                        <div class="truncate text-sm font-medium text-lf-primary">
                                            {eventDescription(event)}
                                        </div>
                                        <div class="mt-1 text-xs uppercase tracking-wide text-lf-muted">
                                            {eventKindLabel(eventLabelKind(event))}
                                        </div>
                                        {#if detailItems.length > 0}
                                            <div class="mt-2 flex flex-wrap gap-2" data-testid={`lot-custody-modal-history-details-${index}`}>
                                                {#each detailItems as item}
                                                    <span class="inline-flex items-center gap-1 rounded-full bg-lf-panel px-2 py-1 text-[11px]">
                                                        <span class="uppercase tracking-wide text-lf-muted">{item.label}</span>
                                                        <span class={`font-semibold tabular-nums ${eventDetailToneClass(item.tone)}`}>{item.value}</span>
                                                    </span>
                                                {/each}
                                            </div>
                                        {/if}
                                    </div>
                                </div>

                                <div class="shrink-0 pl-2 text-right text-sm font-semibold tabular-nums text-lf-primary">
                                    {eventQuantityText(event)}
                                </div>
                            </button>
                        {/each}
                    </div>
                {:else}
                    <div class="rounded-xl border border-dashed border-lf-subtle px-4 py-6 text-sm text-lf-muted" data-testid="lot-custody-modal-history-empty">
                        {$_('brokers.lots.modal.emptyHistory')}
                    </div>
                {/if}
            </section>
        </div>

        <div class="flex items-center justify-end gap-3 border-t border-lf-subtle px-5 py-4">
            <button type="button" class="rounded-lg bg-lf-panel px-4 py-2 text-sm font-medium text-lf-secondary transition-colors hover:bg-lf-neutral" onclick={onClose} data-testid="lot-custody-modal-footer-close">
                {$_('common.close')}
            </button>
            <button
                type="button"
                class="rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action transition-colors hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50"
                onclick={handleGotoTransaction}
                disabled={!canGotoTransaction}
                data-testid="lot-custody-modal-footer-goto-transaction"
            >
                {$_('brokers.lots.modal.goToTransaction')}
            </button>
        </div>
    {/if}
</ModalBase>
