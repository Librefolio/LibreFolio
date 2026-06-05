<!--
  TransactionResultBanner — Unified banner for transaction validation/commit results.

  Covers: validate success (green), validate issues (amber), commit failures (red).
  Used by: TransactionDeleteModal, TransactionBulkModal, TransactionFormModal.

  Features:
  - Emoji-only icons (no SVG lucide) — consistent with the design system
  - Left-aligned text with proper bullet spacing
  - Optional dismiss button
  - Supports both simple messages and grouped clickable issue lists (via children slot)

  Svelte 5 runes, dark mode.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';

    interface Props {
        /** 'success' = green, 'warning' = amber, 'error' = red */
        variant: 'success' | 'warning' | 'error';
        /** Bold title at the top (should include emoji like ⛔, ⚠️, ✅) */
        title: string;
        /** Optional subtitle under the title (smaller text) */
        subtitle?: string;
        /** Simple HTML messages to render (from resolveIssueMessage — may contain <img>, <strong>, etc.) */
        messages?: string[];
        /** Show dismiss (X) button */
        dismissible?: boolean;
        /** Called when dismiss button is clicked */
        ondismiss?: () => void;
        /** Slot for complex content (grouped issue lists with clickable buttons) */
        children?: Snippet;
        /** Optional action rendered inline with the title (right-aligned) */
        titleAction?: Snippet;
        testId?: string;
    }

    let {variant, title, subtitle = '', messages = [], dismissible = false, ondismiss, children, titleAction, testId = 'tx-result-banner'}: Props = $props();

    const variantStyles = {
        success: 'text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800/40',
        warning: 'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800/40',
        error: 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800/40',
    };
</script>

<div class="flex items-start gap-2 text-sm {variantStyles[variant]} rounded-lg border p-3 text-left" data-testid={testId}>
    <div class="flex-1 min-w-0">
        <div class="flex items-center justify-between gap-2">
            <p class="font-semibold">{title}</p>
            {#if titleAction}
                {@render titleAction()}
            {/if}
        </div>
        {#if subtitle}
            <p class="text-xs opacity-80 mt-0.5">{subtitle}</p>
        {/if}
        {#if messages.length > 0}
            <ul class="list-disc pl-4 space-y-0.5 text-sm mt-1.5 text-left">
                {#each messages as msg}
                    <li>{@html msg}</li>
                {/each}
            </ul>
        {/if}
        {#if children}
            <div class="mt-1.5">
                {@render children()}
            </div>
        {/if}
    </div>
    {#if dismissible && ondismiss}
        <button type="button" class="shrink-0 p-0.5 rounded opacity-60 hover:opacity-100 transition-opacity" onclick={ondismiss} aria-label="Dismiss"> ✕ </button>
    {/if}
</div>
