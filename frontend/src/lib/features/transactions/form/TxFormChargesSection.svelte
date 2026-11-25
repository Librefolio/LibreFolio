<!--
  TxFormChargesSection — the linked charges of a parent in the transaction form (project 66, issue #25).

  The FEE and TAX rows that belong to this transaction: the saved ones and the ones added here, each with its amount,
  its currency and its note, and under them the read-only total («Total charged» or «Net received», one amount per
  currency). Every voice is only itself: the parent's amount never holds its charges. The model is `txCharges.ts`; the
  form owns the rows and the Bulk saves them (lot F7). Editable only in the form the Bulk hosts; read-only elsewhere.
-->
<script lang="ts">
    import {Eye, Link2Off, Trash2} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {REAL_SIGNIFICANT_DIGITS} from '$lib/utils/core/parseDecimalInput';
    import CompactCashCell from './CompactCashCell.svelte';
    import {chargesTotal, linkedCharges, newCharge, type ChargeCash, type ChargeDraft, type ChargeType} from './txCharges';
    import type {CashDirection} from './txTradeAmount';

    interface Props {
        /** Every draft, all states: the section shows the linked ones. */
        charges: ChargeDraft[];
        /** Add, change, unlink and delete rows. */
        editable: boolean;
        /** Show «+ Fee» / «+ Tax»: editable and the parent is not a leg of a pair (rule 8). */
        canAdd: boolean;
        /** The parent's cash as the form shows it (a magnitude), for the total and the new rows' currency. */
        parentCash: ChargeCash | null;
        /** Which way the parent's cash goes; `null` hides the total. */
        direction: CashDirection | null;
        /** The rows' load: `ready` when there is nothing to load. */
        loadState: 'loading' | 'ready' | 'error';
        /** Keys of the rows without an amount (a local error of the form). */
        missingKeys: readonly string[];
        /** Open a saved charge in the same window (F3); `null` hides «Open». */
        onOpen?: ((id: number) => void) | null;
        /** The charge the user came from, highlighted (F3). */
        highlightId?: number | null;
        /** «Link an existing charge…» (F4): the form opens the picker; `null` hides it. */
        onLinkExisting?: (() => void) | null;
    }

    let {charges = $bindable(), editable, canAdd, parentCash, direction, loadState, missingKeys, onOpen = null, highlightId = null, onLinkExisting = null}: Props = $props();

    let seq = 0;
    const shown = $derived(linkedCharges(charges));
    const totals = $derived(chargesTotal(direction, parentCash, charges));

    function update(key: string, patch: Partial<ChargeDraft>) {
        charges = charges.map((charge) => (charge.key === key ? {...charge, ...patch} : charge));
    }

    function add(type: ChargeType) {
        seq += 1;
        while (charges.some((charge) => charge.key === `new-${seq}`)) seq += 1;
        charges = [...charges, newCharge(type, parentCash?.code ?? null, seq)];
    }

    function drop(key: string) {
        charges = charges.filter((other) => other.key !== key);
    }

    /** A charge picked in this form (F4) was never linked: unlinking it only takes it back out of the section. */
    function unlink(charge: ChargeDraft) {
        if (charge.linkNew) drop(charge.key);
        else update(charge.key, {state: 'unlink'});
    }

    /** A new row, or a charge picked in this form, leaves the section; a saved linked charge is deleted on save. */
    function remove(charge: ChargeDraft) {
        if (charge.id === null || charge.linkNew) drop(charge.key);
        else update(charge.key, {state: 'delete'});
    }

    function totalText(amount: string, code: string): string {
        return formatCurrencyAmountPlain(Number(amount), code, {maxFraction: 6, sensitivity: 'personal'});
    }
</script>

<section class="border border-lf-subtle rounded-lg px-4 py-3 text-sm text-lf-primary" data-testid="tx-form-charges" data-state={loadState}>
    <h3 class="text-xs font-semibold uppercase tracking-wide text-lf-muted">{$t('transactions.form.charges.title')}</h3>

    {#if loadState === 'loading'}
        <p class="mt-2 text-xs text-lf-muted" data-testid="tx-form-charges-loading">{$t('transactions.form.charges.loading')}</p>
    {:else if loadState === 'error'}
        <p class="mt-2 text-xs text-lf-danger" data-testid="tx-form-charges-error" data-state="error">{$t('transactions.form.charges.loadError')}</p>
    {/if}

    {#each shown as charge, index (charge.key)}
        {@const missing = missingKeys.includes(charge.key)}
        {@const highlighted = highlightId != null && charge.id === highlightId}
        <div
            class="py-2 flex flex-col gap-1.5 {index > 0 ? 'border-t border-lf-subtle' : ''} {highlighted ? 'bg-lf-selected -mx-2 px-2 rounded' : ''}"
            data-testid="tx-form-charge-row"
            data-charge-key={charge.key}
            data-charge-id={charge.id ?? ''}
            data-charge-type={charge.type}
            data-missing={missing ? 'true' : 'false'}
            data-highlighted={highlighted ? 'true' : 'false'}
        >
            <!-- P-18 (66 TL-1d): below `sm` the title and the icons share the first line (the icons right), the amount takes
                 the next; from `sm` up the three sit on one line, as before. -->
            <div class="flex flex-wrap items-center gap-2">
                <span class="min-w-0 flex items-center gap-2 grow order-1">
                    <span class="font-medium" data-testid="tx-form-charge-title">{$t(`transactions.types.${charge.type}`)}</span>
                    {#if charge.id !== null}
                        <span class="text-xs {highlighted ? 'text-lf-secondary' : 'text-lf-muted'}">#{charge.id}</span>
                    {:else}
                        <span class="text-[10px] px-1.5 py-px rounded-full bg-lf-info-soft text-lf-info-on-soft">{$t('transactions.form.charges.new')}</span>
                    {/if}
                </span>
                <span class="w-full sm:w-64 min-w-0 order-3 sm:order-2">
                    <CompactCashCell value={charge.cash} onChange={(next) => update(charge.key, {cash: next})} signHint="negative" defaultCode={parentCash?.code} disabled={!editable} testid={`tx-form-charge-cash-${charge.key}`} maxSignificantDigits={REAL_SIGNIFICANT_DIGITS} />
                </span>
                {#if (onOpen && charge.id !== null) || editable}
                    <span class="inline-flex gap-1.5 shrink-0 order-2 sm:order-3">
                        {#if onOpen && charge.id !== null}
                            <button
                                type="button"
                                class="p-1.5 rounded-lg border border-lf-input text-lf-link bg-lf-card hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus"
                                aria-label={$t('transactions.form.charges.open')}
                                title={$t('transactions.form.charges.open')}
                                data-testid={`tx-form-charge-open-${charge.key}`}
                                onclick={() => charge.id !== null && onOpen?.(charge.id)}><Eye size={14} /></button
                            >
                        {/if}
                        {#if editable && charge.id !== null}
                            <button
                                type="button"
                                class="p-1.5 rounded-lg border border-lf-input text-lf-link bg-lf-card hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus"
                                aria-label={$t('transactions.form.charges.unlink')}
                                title={$t('transactions.form.charges.unlink')}
                                data-testid={`tx-form-charge-unlink-${charge.key}`}
                                onclick={() => unlink(charge)}><Link2Off size={14} /></button
                            >
                        {/if}
                        {#if editable}
                            <button
                                type="button"
                                class="p-1.5 rounded-lg border border-lf-input text-lf-danger bg-lf-card hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus"
                                aria-label={$t('transactions.form.charges.remove')}
                                title={$t('transactions.form.charges.remove')}
                                data-testid={`tx-form-charge-remove-${charge.key}`}
                                onclick={() => remove(charge)}><Trash2 size={14} /></button
                            >
                        {/if}
                    </span>
                {/if}
            </div>
            {#if editable}
                <input
                    type="text"
                    maxlength="500"
                    class="w-full px-3 py-1.5 text-sm bg-lf-field text-lf-primary placeholder:text-lf-placeholder border border-lf-input hover:border-lf-input-hover rounded-lg focus:outline-none focus:ring-2 focus:ring-lf-focus/30"
                    placeholder={$t('transactions.form.charges.notePlaceholder')}
                    aria-label={$t('common.description')}
                    value={charge.description}
                    oninput={(event) => update(charge.key, {description: (event.currentTarget as HTMLInputElement).value})}
                    data-testid={`tx-form-charge-note-${charge.key}`}
                />
            {:else if charge.description}
                <p class="text-xs text-lf-secondary" data-testid={`tx-form-charge-note-${charge.key}`}>{charge.description}</p>
            {/if}
            {#if missing && editable}
                <p class="text-xs text-lf-danger">{$t('transactions.form.charges.missingAmount')}</p>
            {/if}
        </div>
    {/each}

    {#if editable && canAdd}
        <div class="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
            {#each ['FEE', 'TAX'] as const as type (type)}
                <button
                    type="button"
                    class="flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-lf-input bg-lf-field text-lf-secondary hover:border-lf-input-hover focus-visible:outline-2 focus-visible:outline-lf-focus"
                    data-testid={`tx-form-charges-add-${type}`}
                    onclick={() => add(type)}>{$t('transactions.form.charges.addCharge', {values: {type: $t(`transactions.types.${type}`)}})}</button
                >
            {/each}
        </div>
        {#if onLinkExisting}
            <button
                type="button"
                class="mt-2 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-lf-input bg-lf-field text-lf-link hover:border-lf-input-hover focus-visible:outline-2 focus-visible:outline-lf-focus"
                data-testid="tx-form-charges-link-existing"
                onclick={() => onLinkExisting?.()}>{$t('transactions.form.charges.linkExisting')}</button
            >
        {/if}
    {/if}

    {#if totals}
        <div class="mt-3 pt-2 border-t border-lf-subtle flex flex-wrap items-baseline justify-between gap-2" data-testid="tx-form-charges-total" data-direction={direction}>
            <span class="text-lf-secondary">{$t(direction === 'out' ? 'transactions.form.charges.totalOut' : 'transactions.form.charges.totalIn')}</span>
            <span class="flex flex-wrap gap-x-3 font-semibold">
                {#each totals as total (total.currency)}
                    <span data-testid={`tx-form-charges-total-${total.currency}`}>{totalText(total.amount, total.currency)}</span>
                {/each}
            </span>
        </div>
    {/if}
</section>
