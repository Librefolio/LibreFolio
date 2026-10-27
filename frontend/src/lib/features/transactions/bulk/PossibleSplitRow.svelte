<!--
  PossibleSplitRow — one row of the «may be a stock split» banner of the bulk editor.

  The importer turned a broker's split row into an incoming adjustment at no cost and flagged it (todo
  `possible_split`). Linking a SPLIT asset event is what makes the cost follow the old shares, so the row offers
  the two ways to get there: create the event (the mini modal, with the ratio the file implies) or pick one that exists.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import AssetEventPicker from '$lib/features/transactions/events/AssetEventPicker.svelte';
    import type {PossibleSplitEntry} from './bulkTodos';

    interface Props {
        entry: PossibleSplitEntry;
        onCreate: (entry: PossibleSplitEntry) => void;
        onLink: (eventId: number) => void;
        onGoto: (rowId: string) => void;
    }

    let {entry, onCreate, onLink, onGoto}: Props = $props();

    let pickerOpen = $state(false);
    /** An asset not yet resolved (a fake id, or none) has no events to create or link. */
    let resolved = $derived(typeof entry.assetId === 'number' && entry.assetId > 0);

    const buttonClass = 'px-2 py-0.5 rounded border border-lf-input bg-lf-field text-lf-primary hover:bg-lf-hover text-xs';
</script>

<div class="mt-2 border-t border-lf-warning-line pt-2 text-xs" data-testid="possible-split-row" data-row-id={entry.rowId}>
    <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span class="font-mono opacity-70">#{entry.rowNumber}</span>
        <span class="font-medium">{entry.ticker}</span>
        <span>{$t('transactions.bulk.possibleSplit.quantityAdded', {values: {quantity: entry.addedQuantity}})}</span>
        <span class="font-mono opacity-70">{entry.date}</span>
        {#if entry.ratio}
            <span data-testid="possible-split-ratio">{$t('transactions.bulk.possibleSplit.ratio', {values: {ratio: entry.ratio, held: entry.heldBefore ?? ''}})}</span>
        {/if}
        <button type="button" class="ml-auto underline hover:no-underline" onclick={() => onGoto(entry.rowId)} data-testid="possible-split-goto">{$t('transactions.bulk.possibleSplit.goto')}</button>
    </div>
    {#if entry.roundingDelta !== null}
        <p class="mt-1" data-testid="possible-split-rounding">{$t('transactions.bulk.possibleSplit.rounding', {values: {ratio: entry.suggestedRatio ?? entry.ratio ?? '', delta: entry.roundingDelta}})}</p>
    {/if}
    {#if resolved}
        <div class="mt-1.5 flex flex-wrap items-center gap-2">
            <button type="button" class={buttonClass} onclick={() => onCreate(entry)} data-testid="possible-split-create">{$t('transactions.bulk.possibleSplit.create')}</button>
            <button type="button" class={buttonClass} onclick={() => (pickerOpen = !pickerOpen)} aria-expanded={pickerOpen} data-testid="possible-split-link">{$t('transactions.bulk.possibleSplit.link')}</button>
        </div>
        {#if pickerOpen}
            <div class="mt-1.5 max-w-sm">
                <AssetEventPicker
                    assetId={entry.assetId as number}
                    txDate={entry.date}
                    value={null}
                    onChange={(id) => {
                        if (id !== null) onLink(id);
                    }}
                />
            </div>
        {/if}
    {:else}
        <p class="mt-1.5 opacity-80" data-testid="possible-split-asset-needed">{$t('transactions.bulk.possibleSplit.assetNeeded')}</p>
    {/if}
</div>
