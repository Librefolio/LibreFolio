<!--
  PromoteAllModal - merge every suggested pair of the bulk editor at once.

  A simplified PromoteMergeModal: one answer for all the pairs, used where the two rows of a pair
  carry a different description or different tags — keep the left row's (the first one the banner
  lists), keep the right row's, or combine both, as PromoteMergeModal proposes by default.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Link2} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';

    export type PromoteAllStrategy = 'left' | 'merge' | 'right';

    interface Props {
        open: boolean;
        /** How many suggested pairs will be merged. */
        count: number;
        onConfirm: (strategy: PromoteAllStrategy) => void;
        onCancel: () => void;
        zIndex?: number;
    }

    let {open, count, onConfirm, onCancel, zIndex = 70}: Props = $props();

    let strategy = $state<PromoteAllStrategy>('merge');

    // Every opening starts from the default answer, the one PromoteMergeModal proposes.
    $effect(() => {
        if (open) strategy = 'merge';
    });

    let choices = $derived<{value: PromoteAllStrategy; label: string; hint: string}[]>([
        {value: 'left', label: $t('transactions.promote.allLeft'), hint: $t('transactions.promoteSuggest.mergeAllLeftHint')},
        {value: 'merge', label: $t('transactions.promoteSuggest.mergeAllCombine'), hint: $t('transactions.promoteSuggest.mergeAllCombineHint')},
        {value: 'right', label: $t('transactions.promote.allRight'), hint: $t('transactions.promoteSuggest.mergeAllRightHint')},
    ]);
</script>

<ModalBase maxWidth="max-w-md" onRequestClose={onCancel} {open} {zIndex} testId="promote-all-modal">
    <div class="flex items-center gap-3 px-5 py-4 border-b border-gray-200 dark:border-slate-700">
        <Link2 class="text-libre-green dark:text-green-400 shrink-0" size={20} />
        <h2 class="flex-1 text-lg font-semibold text-gray-900 dark:text-gray-100">{$t('transactions.promoteSuggest.mergeAllTitle')}</h2>
    </div>

    <div class="px-5 py-4 space-y-3">
        <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{$t('transactions.promoteSuggest.mergeAllIntro', {values: {n: count}})}</p>
        <div class="space-y-2" role="radiogroup" data-testid="promote-all-choices">
            {#each choices as choice (choice.value)}
                <label
                    class="flex items-start gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-colors
                           {strategy === choice.value ? 'border-libre-green bg-green-50 dark:border-green-400 dark:bg-green-900/20' : 'border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/40'}"
                    data-testid="promote-all-choice-{choice.value}"
                >
                    <input type="radio" class="mt-1 accent-libre-green" name="promote-all-strategy" value={choice.value} checked={strategy === choice.value} onchange={() => (strategy = choice.value)} />
                    <span class="min-w-0">
                        <span class="block text-sm font-medium text-gray-900 dark:text-gray-100">{choice.label}</span>
                        <span class="block text-xs text-gray-500 dark:text-gray-400">{choice.hint}</span>
                    </span>
                </label>
            {/each}
        </div>
    </div>

    <div class="flex items-center justify-end gap-3 px-5 py-4 border-t border-gray-200 dark:border-slate-700">
        <button type="button" class="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-slate-700 dark:text-gray-200 dark:hover:bg-slate-600" onclick={onCancel} data-testid="promote-all-cancel">
            {$t('common.cancel')}
        </button>
        <button type="button" class="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-libre-green text-white hover:bg-libre-green/90" onclick={() => onConfirm(strategy)} data-testid="promote-all-confirm">
            <Link2 size={14} />
            {$t('transactions.promoteSuggest.mergeAllConfirm', {values: {n: count}})}
        </button>
    </div>
</ModalBase>
