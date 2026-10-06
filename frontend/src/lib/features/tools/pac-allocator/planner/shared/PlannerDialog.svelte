<script lang="ts">
    import type {Snippet} from 'svelte';
    import {X} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';

    interface Props {
        open: boolean;
        title: string;
        testid: string;
        onclose: () => void;
        maxWidth?: string;
        /** Stacking above another planner dialog (the conflict dialog after a copy). */
        zIndex?: number;
        children: Snippet;
        footer?: Snippet;
    }

    let {open, title, testid, onclose, maxWidth = '2xl', zIndex = 50, children, footer}: Props = $props();

    const titleId = $props.id();
</script>

<!-- A backdrop click never closes: a dialog can hold typed values (manual account, editors). -->
<ModalBase {open} {maxWidth} {zIndex} closeOnBackdropClick={false} onRequestClose={onclose} labelledBy={titleId} trapFocus restoreFocus testId={testid}>
    <div class="flex min-h-0 flex-1 flex-col" data-testid="{testid}-panel">
        <header class="flex shrink-0 items-start justify-between gap-3 border-b border-gray-200 px-5 py-4 dark:border-gray-700">
            <h2 id={titleId} class="min-w-0 break-words text-base font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
            <button
                type="button"
                class="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-800 focus-visible:outline-2 focus-visible:outline-libre-green dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-100"
                aria-label={$t('common.close', {default: 'Close'})}
                data-testid="{testid}-close"
                onclick={onclose}
            >
                <X size={18} aria-hidden="true" />
            </button>
        </header>
        <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4 text-sm text-gray-800 dark:text-gray-200">
            {@render children()}
        </div>
        {#if footer}
            <footer class="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-gray-200 px-5 py-3 dark:border-gray-700">
                {@render footer()}
            </footer>
        {/if}
    </div>
</ModalBase>
