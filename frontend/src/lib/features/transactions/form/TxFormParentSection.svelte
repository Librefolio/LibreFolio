<!--
  TxFormParentSection — «Linked to»: the transaction a charge belongs to, in the charge's form (project 66, issue #25).

  One line for the parent (its type, its id, its date and its amount) with «Open», which shows it in the same window,
  and «Unlink» where the charges can be edited. The form owns the state; this component draws it.
-->
<script lang="ts">
    import {Eye, Link2Off} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import type {TXReadItem} from '../types';

    interface Props {
        parentId: number;
        /** The parent as the API returns it, once loaded. */
        parent: TXReadItem | null;
        loadState: 'loading' | 'ready' | 'error';
        /** The user unlinked the charge in this form (it will be saved by the host). */
        unlinked: boolean;
        /** Open the parent in the same window; `null` hides «Open». */
        onOpen: ((id: number) => void) | null;
        /** Unlink the charge; `null` hides «Unlink». */
        onUnlink: (() => void) | null;
    }

    let {parentId, parent, loadState, unlinked, onOpen, onUnlink}: Props = $props();

    const state = $derived(unlinked ? 'unlinked' : loadState);
</script>

<section class="border border-lf-subtle rounded-lg px-4 py-3 text-sm text-lf-primary" data-testid="tx-form-parent" data-parent-id={parentId} data-state={state}>
    <h3 class="text-xs font-semibold uppercase tracking-wide text-lf-muted">{$t('transactions.form.parent.title')}</h3>
    {#if unlinked}
        <p class="mt-2 text-xs text-lf-secondary" data-testid="tx-form-parent-unlinked">{$t('transactions.form.parent.unlinked')}</p>
    {:else if loadState === 'loading'}
        <p class="mt-2 text-xs text-lf-muted">{$t('transactions.form.parent.loading')}</p>
    {:else if loadState === 'error' || !parent}
        <p class="mt-2 text-xs text-lf-danger" data-testid="tx-form-parent-error">{$t('transactions.form.parent.loadError')}</p>
    {:else}
        <div class="mt-2 flex flex-wrap items-center gap-2">
            <span class="grow min-w-0" data-testid="tx-form-parent-summary">
                <span class="font-medium">{$t(`transactions.types.${parent.type}`)}</span>
                <span class="text-lf-muted">#{parent.id}</span>
                <span class="text-lf-secondary">· {parent.date}</span>
                {#if parent.cash}
                    <span class="text-lf-secondary">· {formatCurrencyAmountPlain(Number(parent.cash.amount), parent.cash.code, {sensitivity: 'personal'})}</span>
                {/if}
            </span>
            <span class="inline-flex gap-1.5">
                {#if onOpen}
                    <button
                        type="button"
                        class="p-1.5 rounded-lg border border-lf-input text-lf-link bg-lf-card hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus"
                        aria-label={$t('transactions.form.charges.open')}
                        title={$t('transactions.form.charges.open')}
                        data-testid="tx-form-parent-open"
                        onclick={() => onOpen?.(parentId)}><Eye size={14} /></button
                    >
                {/if}
                {#if onUnlink}
                    <button
                        type="button"
                        class="p-1.5 rounded-lg border border-lf-input text-lf-link bg-lf-card hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus"
                        aria-label={$t('transactions.form.parent.unlink')}
                        title={$t('transactions.form.parent.unlink')}
                        data-testid="tx-form-parent-unlink"
                        onclick={() => onUnlink?.()}><Link2Off size={14} /></button
                    >
                {/if}
            </span>
        </div>
    {/if}
</section>
