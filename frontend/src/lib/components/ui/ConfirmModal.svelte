<!--
  ConfirmModal - Generic confirmation modal for destructive actions

  Features:
  - Customizable title, message, buttons
  - Optional collapsible list of items (e.g., files to delete)
  - Danger variant for destructive actions
  - Dark mode support
  - Uses ModalBase for consistent modal behavior
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import {AlertTriangle, Check, ChevronDown, ChevronUp, X, XCircle} from 'lucide-svelte';
    import {fade} from 'svelte/transition';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';

    interface Props {
        /** Whether modal is open */
        open: boolean;
        /** Modal title */
        title: string;
        /** Main message */
        message: string;
        /** Optional description rendered below message (e.g., warning text) */
        description?: string;
        /** Optional list of items to show (collapsible) */
        items?: string[];
        /** Label for the list section */
        itemsLabel?: string;
        /** Confirm button text */
        confirmText?: string;
        /** Cancel button text */
        cancelText?: string;
        /** Danger mode (red confirm button) */
        danger?: boolean;
        /** Warning mode (amber confirm button — for non-destructive but attention-worthy actions) */
        warning?: boolean;
        /** Called on confirm */
        onConfirm: () => void;
        /** Called on cancel/close */
        onCancel: () => void;
        /** Z-index for stacking (default 60 = above first-level modals) */
        zIndex?: number;
        /** Operation results to display after action completes (replaces message+items when present) */
        results?: {label: string; success: boolean; detail?: string}[];
    }

    let {open, title, message, description = '', items = [], itemsLabel = '', confirmText = $t('common.confirm'), cancelText = $t('common.cancel'), danger = false, warning = false, onConfirm, onCancel, zIndex = 60, results = []}: Props = $props();

    // Auto-show items if there's only 1 (no need for toggle)
    let showItems = $state(false);

    // Reactive: if items.length === 1, always show
    let shouldShowItems = $derived(items.length === 1 || showItems);
    let hasResults = $derived(results.length > 0);
</script>

<ModalBase maxWidth="max-w-md" onRequestClose={onCancel} {open} {zIndex}>
    <!-- Header -->
    <div class="modal-header">
        {#if danger}
            <AlertTriangle class="text-red-500" size={24} />
        {:else if warning}
            <AlertTriangle class="text-amber-500" size={24} />
        {/if}
        <h2 class="modal-title">{title}</h2>
        <button aria-label="Close" class="close-btn" onclick={onCancel} type="button">
            <X size={20} />
        </button>
    </div>

    <!-- Body -->
    <div class="modal-body">
        {#if hasResults}
            <!-- Results mode: show ✅/❌ per-item results -->
            <ul class="results-list">
                {#each results as r}
                    <li class="result-item">
                        {#if r.success}
                            <Check size={14} class="text-emerald-500 shrink-0" />
                        {:else}
                            <XCircle size={14} class="text-red-500 shrink-0" />
                        {/if}
                        <span class="result-label">{r.label}</span>
                        {#if r.detail}
                            <span class="result-detail">— {r.detail}</span>
                        {/if}
                    </li>
                {/each}
            </ul>
        {:else}
            <p class="message">{message}</p>
            {#if description}
                <p class="description">{description}</p>
            {/if}

            {#if items.length > 0}
                <div class="items-section">
                    {#if items.length > 1}
                        <button type="button" class="items-toggle" onclick={() => (showItems = !showItems)}>
                            <span class="items-label">
                                {itemsLabel || `${items.length} items`}
                            </span>
                            {#if shouldShowItems}
                                <ChevronUp size={16} />
                            {:else}
                                <ChevronDown size={16} />
                            {/if}
                        </button>
                    {/if}

                    {#if shouldShowItems}
                        <ul class="items-list" transition:fade={{duration: 100}}>
                            {#each items as item}
                                <li class="item">{item}</li>
                            {/each}
                        </ul>
                    {/if}
                </div>
            {/if}
        {/if}
    </div>

    <!-- Footer -->
    <div class="modal-footer">
        {#if hasResults}
            <button type="button" class="btn btn-primary" onclick={onCancel} data-testid="confirm-modal-close">
                {$t('common.close')}
            </button>
        {:else}
            <button type="button" class="btn btn-secondary" onclick={onCancel} data-testid="confirm-modal-cancel">
                {cancelText}
            </button>
            <button type="button" class="btn {danger ? 'btn-danger' : warning ? 'btn-warning' : 'btn-primary'}" onclick={onConfirm} data-testid="confirm-modal-confirm">
                {confirmText}
            </button>
        {/if}
    </div>
</ModalBase>

<style>
    /* No backdrop styles needed — handled by ModalBase */

    .modal-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid #e2e8f0;
    }

    :global(.dark) .modal-header {
        border-bottom-color: #334155;
    }

    .modal-title {
        flex: 1;
        font-size: 1.125rem;
        font-weight: 600;
        color: #0f172a;
        margin: 0;
    }

    :global(.dark) .modal-title {
        color: #f1f5f9;
    }

    .close-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border: none;
        border-radius: 6px;
        background: transparent;
        color: #64748b;
        cursor: pointer;
        transition: all 0.15s;
    }

    .close-btn:hover {
        background: #f1f5f9;
        color: #0f172a;
    }

    :global(.dark) .close-btn:hover {
        background: #334155;
        color: #f1f5f9;
    }

    .modal-body {
        padding: 1.25rem;
        overflow-y: auto;
    }

    .message {
        color: #475569;
        line-height: 1.6;
        margin: 0;
    }

    :global(.dark) .message {
        color: #94a3b8;
    }

    .description {
        color: #64748b;
        font-size: 0.8125rem;
        line-height: 1.5;
        margin: 0.5rem 0 0;
    }

    :global(.dark) .description {
        color: #94a3b8;
    }

    .results-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .result-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.8125rem;
        color: #334155;
    }

    :global(.dark) .result-item {
        color: #e2e8f0;
    }

    .result-label {
        font-weight: 500;
    }

    .result-detail {
        color: #64748b;
        font-size: 0.75rem;
    }

    :global(.dark) .result-detail {
        color: #94a3b8;
    }

    .items-section {
        margin-top: 1rem;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
    }

    :global(.dark) .items-section {
        border-color: #334155;
    }

    .items-toggle {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 0.625rem 0.875rem;
        background: #f8fafc;
        border: none;
        color: #64748b;
        font-size: 0.875rem;
        cursor: pointer;
        transition: background 0.15s;
    }

    .items-toggle:hover {
        background: #f1f5f9;
    }

    :global(.dark) .items-toggle {
        background: #1e293b;
        color: #94a3b8;
    }

    :global(.dark) .items-toggle:hover {
        background: #334155;
    }

    .items-list {
        list-style: none;
        margin: 0;
        padding: 0.5rem 0;
        max-height: 200px;
        overflow-y: auto;
        background: white;
    }

    :global(.dark) .items-list {
        background: #0f172a;
    }

    .item {
        padding: 0.375rem 0.875rem;
        font-size: 0.8125rem;
        color: #475569;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    :global(.dark) .item {
        color: #94a3b8;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-top: 1px solid #e2e8f0;
    }

    :global(.dark) .modal-footer {
        border-top-color: #334155;
    }

    .btn {
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        border-radius: 6px;
        border: none;
        cursor: pointer;
        transition: all 0.15s;
    }

    .btn-secondary {
        background: #f1f5f9;
        color: #475569;
    }

    .btn-secondary:hover {
        background: #e2e8f0;
    }

    :global(.dark) .btn-secondary {
        background: #334155;
        color: #e2e8f0;
    }

    :global(.dark) .btn-secondary:hover {
        background: #475569;
    }

    .btn-primary {
        background: #1a4031;
        color: white;
    }

    .btn-primary:hover {
        background: #153428;
    }

    .btn-danger {
        background: #dc2626;
        color: white;
    }

    .btn-danger:hover {
        background: #b91c1c;
    }

    .btn-warning {
        background: #f59e0b;
        color: white;
    }

    .btn-warning:hover {
        background: #d97706;
    }
</style>
