<!--
  PromoteMergeModal.svelte — Stacked diff UI for resolving divergent fields
  when promoting two transactions into a paired type.

  F7 redesign: stacked layout (2 readonly boxes + 1 editable merge area below),
  TagInput for tags, textarea for description, global all-left/merge/right buttons.
  Works on both desktop and mobile.

  Plan D2 Step C5 + F7 redesign (2026-05-13).
  Plan D2 Bugfix 2 Step 6 — blue/pink sides, dirty guard (2026-05-13).
  Plan D2 Bugfix 3 Step 5 — removed green bg, top global buttons, no clickToSelect, textarea resize-none (2026-05-14).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import TagInput from '$lib/components/ui/TagInput.svelte';
    import {Link2} from 'lucide-svelte';
    import {getStringBadgeStyle} from '$lib/utils/colors';

    interface Props {
        open: boolean;
        txA?: {label: string; description: string; tags: string[]; date: string; cost_basis_override: string} | null;
        txB?: {label: string; description: string; tags: string[]; date: string; cost_basis_override: string} | null;
        targetTypeLabel: string;
        availableTags?: string[];
        onConfirm: (resolved: {description?: string; tags?: string[]; date?: string; cost_basis_override?: string}) => void;
        onCancel: () => void;
    }

    let {open, txA, txB, targetTypeLabel, availableTags = [], onConfirm, onCancel}: Props = $props();

    // Resolved values (editable merge area)
    let resDescription = $state('');
    let resTags = $state<string[]>([]);
    let resDate = $state('');
    let resCostBasis = $state('');

    // Dirty guard
    let showDiscardConfirm = $state(false);
    let initialSnapshot = $state('');

    // Divergence flags
    let diffDesc = $derived(txA?.description !== txB?.description);
    let diffTags = $derived(JSON.stringify(txA?.tags ?? []) !== JSON.stringify(txB?.tags ?? []));
    let diffDate = $derived(txA?.date !== txB?.date);
    let diffCostBasis = $derived(txA?.cost_basis_override !== txB?.cost_basis_override);
    let hasDifferences = $derived(diffDesc || diffTags || diffDate || diffCostBasis);

    // All available tags for TagInput: union of both sides + availableTags prop
    let allTagSuggestions = $derived([...new Set([...(txA?.tags ?? []), ...(txB?.tags ?? []), ...availableTags])]);

    function currentSnapshot(): string {
        return JSON.stringify({resDescription, resTags, resDate, resCostBasis});
    }

    let dirty = $derived(initialSnapshot !== '' && currentSnapshot() !== initialSnapshot);

    // Reset resolved values when modal opens
    $effect(() => {
        if (!open || !txA || !txB) return;
        resDescription = mergeStrings(txA.description, txB.description);
        resTags = mergeTagSets(txA.tags, txB.tags);
        resDate = txA.date > txB.date ? txA.date : txB.date;
        resCostBasis = txA.cost_basis_override || txB.cost_basis_override || '';
        // Capture initial snapshot after values are set (next tick)
        setTimeout(() => {
            initialSnapshot = currentSnapshot();
        }, 0);
    });

    function mergeStrings(a: string, b: string): string {
        if (!a) return b;
        if (!b) return a;
        if (a === b) return a;
        return `${a}\n${b}`;
    }

    function mergeTagSets(a: string[], b: string[]): string[] {
        return [...new Set([...(a ?? []), ...(b ?? [])])];
    }

    // Global actions
    function allLeft() {
        if (diffDesc) resDescription = txA?.description ?? '';
        if (diffTags) resTags = [...(txA?.tags ?? [])];
        if (diffDate) resDate = txA?.date ?? '';
        if (diffCostBasis) resCostBasis = txA?.cost_basis_override ?? '';
    }
    function allMerge() {
        if (diffDesc) resDescription = mergeStrings(txA?.description ?? '', txB?.description ?? '');
        if (diffTags) resTags = mergeTagSets(txA?.tags ?? [], txB?.tags ?? []);
        if (diffDate) resDate = (txA?.date ?? '') > (txB?.date ?? '') ? (txA?.date ?? '') : (txB?.date ?? '');
        if (diffCostBasis) resCostBasis = txA?.cost_basis_override || txB?.cost_basis_override || '';
    }
    function allRight() {
        if (diffDesc) resDescription = txB?.description ?? '';
        if (diffTags) resTags = [...(txB?.tags ?? [])];
        if (diffDate) resDate = txB?.date ?? '';
        if (diffCostBasis) resCostBasis = txB?.cost_basis_override ?? '';
    }

    function handleConfirm() {
        const resolved: Record<string, unknown> = {};
        if (diffDesc) resolved.description = resDescription;
        if (diffTags) resolved.tags = resTags;
        if (diffDate) resolved.date = resDate;
        if (diffCostBasis) resolved.cost_basis_override = resCostBasis;
        onConfirm(resolved as {description?: string; tags?: string[]; date?: string; cost_basis_override?: string});
    }

    function handleCancel() {
        if (dirty) {
            showDiscardConfirm = true;
            return;
        }
        onCancel();
    }
</script>

<ModalBase {open} maxWidth="2xl" onRequestClose={handleCancel} testId="promote-merge-modal">
    <div class="p-5 space-y-4 rounded-lg" data-testid="promote-merge-modal">
        <!-- Header -->
        <div class="flex items-center gap-2 text-lg font-semibold text-gray-800 dark:text-gray-100">
            <Link2 size={20} class="text-green-600 dark:text-green-400" />
            <span>{$t('transactions.promote.mergeTitle', {values: {type: targetTypeLabel}})}</span>
        </div>

        {#if hasDifferences && txA && txB}
            <p class="text-sm text-gray-500 dark:text-gray-400">
                {$t('transactions.promote.mergeSubtitle')}
            </p>

            <!-- Global actions — colored buttons -->
            <div class="flex justify-center gap-2">
                <Tooltip text={$t('transactions.promote.allLeft')}>
                    <button type="button" class="px-3 py-1.5 text-xs rounded-lg bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800/40" onclick={allLeft} data-testid="promote-merge-all-left">
                        {$t('transactions.promote.allLeft')} ▶
                    </button>
                </Tooltip>
                <Tooltip text={$t('transactions.promote.allMerge')}>
                    <button type="button" class="px-3 py-1.5 text-xs rounded-lg bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-800/40" onclick={allMerge} data-testid="promote-merge-all-merge">
                        ⟷
                    </button>
                </Tooltip>
                <Tooltip text={$t('transactions.promote.allRight')}>
                    <button type="button" class="px-3 py-1.5 text-xs rounded-lg bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300 hover:bg-pink-200 dark:hover:bg-pink-800/40" onclick={allRight} data-testid="promote-merge-all-right">
                        ◀ {$t('transactions.promote.allRight')}
                    </button>
                </Tooltip>
            </div>

            <div class="space-y-4">
                <!-- Description (B10: textarea for newlines) -->
                {#if diffDesc}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-description">
                        <div class="flex items-center justify-between mb-2">
                            <div class="text-xs font-semibold text-gray-500 dark:text-gray-400">{$t('transactions.promote.fieldDescription')}</div>
                            <Tooltip text={$t('transactions.promote.concat')}>
                                <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/50" onclick={() => (resDescription = mergeStrings(txA?.description ?? '', txB?.description ?? ''))}>⟷ {$t('transactions.promote.concat')}</button>
                            </Tooltip>
                        </div>
                        <!-- 2 readonly boxes side by side — clickable to select -->
                        <div class="grid grid-cols-2 gap-2 mb-2">
                            <button type="button" class="w-full text-left text-xs text-gray-600 dark:text-gray-300 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-2 break-words min-h-[2.5rem] hover:ring-2 hover:ring-blue-300 dark:hover:ring-blue-600 transition-all whitespace-pre-wrap" onclick={() => (resDescription = txA?.description ?? '')} data-testid="promote-merge-desc-left">
                                <span class="text-[10px] text-gray-400 block mb-0.5">Transaction {txA.label}</span>
                                {txA.description || '—'}
                            </button>
                            <button type="button" class="w-full text-left text-xs text-gray-600 dark:text-gray-300 bg-pink-50 dark:bg-pink-900/20 border border-pink-200 dark:border-pink-800 rounded p-2 break-words min-h-[2.5rem] hover:ring-2 hover:ring-pink-300 dark:hover:ring-pink-600 transition-all whitespace-pre-wrap" onclick={() => (resDescription = txB?.description ?? '')} data-testid="promote-merge-desc-right">
                                <span class="text-[10px] text-gray-400 block mb-0.5">Transaction {txB.label}</span>
                                {txB.description || '—'}
                            </button>
                        </div>
                        <textarea rows={2} class="w-full text-xs px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 resize-none overflow-y-auto" style="field-sizing: content; max-height: 8rem; white-space: pre-wrap" bind:value={resDescription} data-testid="promote-merge-desc-input"></textarea>
                    </div>
                {/if}

                <!-- Tags (DD-BF5: use TagInput component) -->
                {#if diffTags}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-tags">
                        <div class="flex items-center justify-between mb-2">
                            <div class="text-xs font-semibold text-gray-500 dark:text-gray-400">{$t('transactions.promote.fieldTags')}</div>
                            <Tooltip text={$t('transactions.promote.union')}>
                                <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/50" onclick={() => (resTags = mergeTagSets(txA?.tags ?? [], txB?.tags ?? []))}>⟷ {$t('transactions.promote.union')}</button>
                            </Tooltip>
                        </div>
                        <!-- 2 readonly tag boxes — clickable to select -->
                        <div class="grid grid-cols-2 gap-2 mb-2">
                            <button type="button" class="w-full text-left text-xs text-gray-600 dark:text-gray-300 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-2 min-h-[2.5rem] hover:ring-2 hover:ring-blue-300 dark:hover:ring-blue-600 transition-all" onclick={() => (resTags = [...(txA?.tags ?? [])])} data-testid="promote-merge-tags-left">
                                <span class="text-[10px] text-gray-400 block mb-0.5">Transaction {txA.label}</span>
                                {#if (txA.tags ?? []).length > 0}
                                    <span class="flex flex-wrap gap-1">{#each txA.tags as tag}<span class="inline-block px-1.5 py-0.5 text-[10px] rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}</span>
                                {:else}
                                    —
                                {/if}
                            </button>
                            <button type="button" class="w-full text-left text-xs text-gray-600 dark:text-gray-300 bg-pink-50 dark:bg-pink-900/20 border border-pink-200 dark:border-pink-800 rounded p-2 min-h-[2.5rem] hover:ring-2 hover:ring-pink-300 dark:hover:ring-pink-600 transition-all" onclick={() => (resTags = [...(txB?.tags ?? [])])} data-testid="promote-merge-tags-right">
                                <span class="text-[10px] text-gray-400 block mb-0.5">Transaction {txB.label}</span>
                                {#if (txB.tags ?? []).length > 0}
                                    <span class="flex flex-wrap gap-1">{#each txB.tags as tag}<span class="inline-block px-1.5 py-0.5 text-[10px] rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}</span>
                                {:else}
                                    —
                                {/if}
                            </button>
                        </div>
                        <TagInput value={resTags} availableTags={allTagSuggestions} onchange={(v) => (resTags = v)} />
                    </div>
                {/if}

                <!-- Date -->
                {#if diffDate}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-date">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.promote.fieldDate')}</div>
                        <div class="grid grid-cols-2 gap-2 mb-2">
                            <button type="button" class="w-full text-left text-xs text-gray-600 dark:text-gray-300 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-2 min-h-[2rem] hover:ring-2 hover:ring-blue-300 dark:hover:ring-blue-600 transition-all" onclick={() => (resDate = txA?.date ?? '')} data-testid="promote-merge-date-left">
                                <span class="text-[10px] text-gray-400 block mb-0.5">Transaction {txA.label}</span>
                                {txA.date}
                            </button>
                            <button type="button" class="w-full text-left text-xs text-gray-600 dark:text-gray-300 bg-pink-50 dark:bg-pink-900/20 border border-pink-200 dark:border-pink-800 rounded p-2 min-h-[2rem] hover:ring-2 hover:ring-pink-300 dark:hover:ring-pink-600 transition-all" onclick={() => (resDate = txB?.date ?? '')} data-testid="promote-merge-date-right">
                                <span class="text-[10px] text-gray-400 block mb-0.5">Transaction {txB.label}</span>
                                {txB.date}
                            </button>
                        </div>
                        <input type="date" class="w-full text-xs px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100" bind:value={resDate} data-testid="promote-merge-date-input" />
                    </div>
                {/if}

                <!-- Cost Basis -->
                {#if diffCostBasis}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-cost_basis_override">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.promote.fieldCostBasis')}</div>
                        <div class="grid grid-cols-2 gap-2 mb-2">
                            <button type="button" class="w-full text-left text-xs text-gray-600 dark:text-gray-300 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-2 min-h-[2rem] hover:ring-2 hover:ring-blue-300 dark:hover:ring-blue-600 transition-all" onclick={() => (resCostBasis = txA?.cost_basis_override ?? '')}>
                                <span class="text-[10px] text-gray-400 block mb-0.5">Transaction {txA.label}</span>
                                {txA.cost_basis_override || '—'}
                            </button>
                            <button type="button" class="w-full text-left text-xs text-gray-600 dark:text-gray-300 bg-pink-50 dark:bg-pink-900/20 border border-pink-200 dark:border-pink-800 rounded p-2 min-h-[2rem] hover:ring-2 hover:ring-pink-300 dark:hover:ring-pink-600 transition-all" onclick={() => (resCostBasis = txB?.cost_basis_override ?? '')}>
                                <span class="text-[10px] text-gray-400 block mb-0.5">Transaction {txB.label}</span>
                                {txB.cost_basis_override || '—'}
                            </button>
                        </div>
                        <input type="text" class="w-full text-xs px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100" bind:value={resCostBasis} />
                    </div>
                {/if}
            </div>
        {:else}
            <p class="text-sm text-gray-500">{$t('transactions.promote.mergeConfirm')}</p>
        {/if}

        <!-- Footer -->
        <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={handleCancel}>
                {$t('common.cancel')}
            </button>
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-white bg-green-600 hover:bg-green-700 inline-flex items-center gap-1.5" onclick={handleConfirm} data-testid="promote-merge-confirm">
                <Link2 size={14} />
                {$t('transactions.promote.mergeConfirm')}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Dirty guard discard confirm -->
<ConfirmModal
    open={showDiscardConfirm}
    title={$t('common.discardChanges')}
    message={$t('common.discardChangesMessage')}
    confirmText={$t('common.discard') || 'Discard'}
    warning={true}
    onConfirm={() => { showDiscardConfirm = false; onCancel(); }}
    onCancel={() => { showDiscardConfirm = false; }}
/>
