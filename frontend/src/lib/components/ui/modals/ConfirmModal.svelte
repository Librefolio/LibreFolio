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
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';

    interface Props {
        /** Whether modal is open */
        open: boolean;
        /** Modal title */
        title: string;
        /** Main message */
        message: string;
        /** Optional description rendered below message (e.g., warning text) */
        description?: string;
        /** Render the description in italics (e.g. an alternative-route hint) */
        descriptionItalic?: boolean;
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
        results?: {
            label: string;
            success: boolean;
            detail?: string;
            action?: {href: string; label: string; testId?: string};
        }[];
        /**
         * Identifies *which* confirmation is on screen. ConfirmModal is generic, so
         * without this every confirm looks alike to a test and the only way to tell
         * them apart is the localized text — which the project forbids as a selector.
         */
        testId?: string;
    }

    let {open, title, message, description = '', descriptionItalic = false, items = [], itemsLabel = '', confirmText = $t('common.confirm'), cancelText = $t('common.cancel'), danger = false, warning = false, onConfirm, onCancel, zIndex = 60, results = [], testId = ''}: Props = $props();

    // Auto-show items if there's only 1 (no need for toggle)
    let showItems = $state(false);

    // Reactive: if items.length === 1, always show
    let shouldShowItems = $derived(items.length === 1 || showItems);
    let hasResults = $derived(results.length > 0);
</script>

<ModalBase maxWidth="max-w-md" onRequestClose={onCancel} {open} {zIndex}>
    <!-- Header -->
    <div class="modal-header" data-testid={testId || undefined}>
        {#if danger}
            <AlertTriangle class="text-lf-danger" size={24} />
        {:else if warning}
            <AlertTriangle class="text-lf-warning" size={24} />
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
                            <Check size={14} class="text-lf-success shrink-0" />
                        {:else}
                            <XCircle size={14} class="text-lf-danger shrink-0" />
                        {/if}
                        <span class="result-label">{r.label}</span>
                        {#if r.detail}
                            <span class="result-detail" data-testid={r.action?.testId ? `${r.action.testId}-detail` : undefined}>— {r.detail}</span>
                        {/if}
                        {#if r.action}
                            <a class="result-action" data-testid={r.action.testId} href={r.action.href}>{r.action.label}</a>
                        {/if}
                    </li>
                {/each}
            </ul>
        {:else}
            <p class="message" data-testid="confirm-modal-message">{message}</p>
            {#if description}
                <p class="description" class:italic={descriptionItalic}>{description}</p>
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
    /* No backdrop styles needed — handled by ModalBase. The colours are the roles of lib/theme/tokens.css, the same
       in both themes by name: no `.dark` rule. */

    .modal-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--lf-border-subtle);
    }

    .modal-title {
        flex: 1;
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--lf-text-primary);
        margin: 0;
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
        color: var(--lf-text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .close-btn:hover {
        background: var(--lf-surface-hover);
        color: var(--lf-text-primary);
    }

    .modal-body {
        padding: 1.25rem;
        overflow-y: auto;
    }

    .message {
        color: var(--lf-text-secondary);
        line-height: 1.6;
        margin: 0;
    }

    .description {
        color: var(--lf-text-muted);
        font-size: 0.8125rem;
        line-height: 1.5;
        margin: 0.5rem 0 0;
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
        color: var(--lf-text-primary);
    }

    .result-label {
        font-weight: 500;
    }

    .result-detail {
        color: var(--lf-text-muted);
        font-size: 0.75rem;
    }

    .result-action {
        margin-left: auto;
        color: var(--lf-link);
        font-size: 0.75rem;
        font-weight: 500;
        white-space: nowrap;
    }

    .items-section {
        margin-top: 1rem;
        border: 1px solid var(--lf-border-subtle);
        border-radius: 8px;
        overflow: hidden;
    }

    .items-toggle {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 0.625rem 0.875rem;
        background: var(--lf-surface-panel);
        border: none;
        color: var(--lf-text-muted);
        font-size: 0.875rem;
        cursor: pointer;
        transition: background 0.15s;
    }

    /* On a panel the hover is `neutral` (open question 3), where the muted text falls under 4.5:1: secondary. */
    .items-toggle:hover {
        background: var(--lf-surface-neutral);
        color: var(--lf-text-secondary);
    }

    .items-list {
        list-style: none;
        margin: 0;
        padding: 0.5rem 0;
        max-height: 200px;
        overflow-y: auto;
        background: var(--lf-surface-field);
    }

    .item {
        padding: 0.375rem 0.875rem;
        font-size: 0.8125rem;
        color: var(--lf-text-secondary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-top: 1px solid var(--lf-border-subtle);
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
        background: var(--lf-surface-panel);
        color: var(--lf-text-secondary);
    }

    .btn-secondary:hover {
        background: var(--lf-surface-neutral);
    }

    .btn-primary {
        background: var(--lf-action);
        color: var(--lf-on-action);
    }

    .btn-primary:hover {
        background: var(--lf-action-hover);
    }

    .btn-danger {
        background: var(--lf-danger-solid);
        color: var(--lf-on-danger-solid);
    }

    .btn-danger:hover {
        background: var(--lf-danger-hover);
    }

    .btn-warning {
        background: var(--lf-warning);
        color: var(--lf-on-status);
    }

    .btn-warning:hover {
        background: var(--lf-warning-hover);
    }
</style>
