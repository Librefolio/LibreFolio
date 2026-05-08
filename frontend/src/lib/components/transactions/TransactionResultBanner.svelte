<!--
  TransactionResultBanner — Unified banner for transaction validation/commit results.

  Covers: validate success (green), validate issues (amber), commit failures (red).
  Used by: TransactionDeleteModal, TransactionBulkModal, TransactionFormModal.

  Svelte 5 runes, dark mode.
-->
<script lang="ts">
    interface Props {
        /** 'success' = green, 'warning' = amber, 'error' = red */
        variant: 'success' | 'warning' | 'error';
        /** Bold title at the top (can include emoji like ⛔, ⚠️, ✓) */
        title: string;
        /** Optional subtitle under the title (smaller text) */
        subtitle?: string;
        /** HTML messages to render (from resolveIssueMessage — may contain <img>, <strong>, etc.) */
        messages?: string[];
        testId?: string;
    }

    let {variant, title, subtitle = '', messages = [], testId = 'tx-result-banner'}: Props = $props();

    const variantStyles = {
        success: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20',
        warning: 'text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20',
        error: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20',
    };
</script>

<div class="flex flex-col gap-1 text-sm {variantStyles[variant]} rounded p-3" data-testid={testId}>
    <div class="flex items-center gap-2 font-semibold">
        <span>{title}</span>
    </div>
    {#if subtitle}
        <p class="text-xs opacity-80 ml-6">{subtitle}</p>
    {/if}
    {#if messages.length > 0}
        <div class="ml-6">
            {#each messages as msg}
                <p>{@html msg}</p>
            {/each}
        </div>
    {/if}
</div>

