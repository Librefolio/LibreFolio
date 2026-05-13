<!--
  PromoteMergeModal.svelte — Stacked diff UI for resolving divergent fields
  when promoting two transactions into a paired type.

  F7 redesign: stacked layout (2 readonly boxes + 1 editable merge area below),
  TagInput for tags, textarea for description, global all-left/merge/right buttons.
  Works on both desktop and mobile.

  Plan D2 Step C5 + F7 redesign (2026-05-13).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
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

    // Divergence flags
    let diffDesc = $derived(txA?.description !== txB?.description);
    let diffTags = $derived(JSON.stringify(txA?.tags ?? []) !== JSON.stringify(txB?.tags ?? []));
    let diffDate = $derived(txA?.date !== txB?.date);
    let diffCostBasis = $derived(txA?.cost_basis_override !== txB?.cost_basis_override);
    let hasDifferences = $derived(diffDesc || diffTags || diffDate || diffCostBasis);

    // All available tags for TagInput: union of both sides + availableTags prop
    let allTagSuggestions = $derived([...new Set([...(txA?.tags ?? []), ...(txB?.tags ?? []), ...availableTags])]);

    // Reset resolved values when modal opens
    $effect(() => {
        if (!open || !txA || !txB) return;
        resDescription = mergeStrings(txA.description, txB.description);
        resTags = mergeTagSets(txA.tags, txB.tags);
        resDate = txA.date > txB.date ? txA.date : txB.date;
        resCostBasis = txA.cost_basis_override || txB.cost_basis_override || '';
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
</script>

<ModalBase {open} maxWidth="2xl" onRequestClose={onCancel} testId="promote-merge-modal">
    <div class="p-5 space-y-4" data-testid="promote-merge-modal">
        <!-- Header -->
        <div class="flex items-center gap-2 text-lg font-semibold text-gray-800 dark:text-gray-100">
            <Link2 size={20} class="text-indigo-600 dark:text-indigo-400" />
            <span>{$t('transactions.promote.mergeTitle', {values: {type: targetTypeLabel}})}</span>
        </div>

        {#if hasDifferences && txA && txB}
            <p class="text-sm text-gray-500 dark:text-gray-400">
                {$t('transactions.promote.mergeSubtitle')}
            </p>

            <div class="space-y-4">
                <!-- Description (B10: textarea for newlines) -->
                {#if diffDesc}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-description">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.promote.fieldDescription')}</div>
                        <!-- 2 readonly boxes side by side — clickable to select -->
                        <div class="grid grid-cols-2 gap-2 mb-2">
                            <button type="button" class="text-left text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 break-words min-h-[2.5rem] hover:ring-2 hover:ring-indigo-300 dark:hover:ring-indigo-600 transition-all whitespace-pre-wrap" onclick={() => (resDescription = txA?.description ?? '')} data-testid="promote-merge-desc-left">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txA.label}</span>
                                {txA.description || '—'}
                            </button>
                            <button type="button" class="text-left text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 break-words min-h-[2.5rem] hover:ring-2 hover:ring-indigo-300 dark:hover:ring-indigo-600 transition-all whitespace-pre-wrap" onclick={() => (resDescription = txB?.description ?? '')} data-testid="promote-merge-desc-right">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txB.label}</span>
                                {txB.description || '—'}
                            </button>
                        </div>
                        <!-- Merge action + editable textarea -->
                        <div class="flex items-center gap-1 mb-1">
                            <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/50" onclick={() => (resDescription = mergeStrings(txA?.description ?? '', txB?.description ?? ''))} title={$t('transactions.promote.concat')}>⟷ {$t('transactions.promote.concat')}</button>
                        </div>
                        <textarea rows={3} class="w-full text-xs px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 resize-y" style="white-space: pre-wrap" bind:value={resDescription} data-testid="promote-merge-desc-input"></textarea>
                    </div>
                {/if}

                <!-- Tags (DD-BF5: use TagInput component) -->
                {#if diffTags}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-tags">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.promote.fieldTags')}</div>
                        <!-- 2 readonly tag boxes — clickable to select -->
                        <div class="grid grid-cols-2 gap-2 mb-2">
                            <button type="button" class="text-left text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2.5rem] hover:ring-2 hover:ring-indigo-300 dark:hover:ring-indigo-600 transition-all" onclick={() => (resTags = [...(txA?.tags ?? [])])} data-testid="promote-merge-tags-left">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txA.label}</span>
                                {#if (txA.tags ?? []).length > 0}
                                    <span class="flex flex-wrap gap-1">{#each txA.tags as tag}<span class="inline-block px-1.5 py-0.5 text-[10px] rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}</span>
                                {:else}
                                    —
                                {/if}
                            </button>
                            <button type="button" class="text-left text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2.5rem] hover:ring-2 hover:ring-indigo-300 dark:hover:ring-indigo-600 transition-all" onclick={() => (resTags = [...(txB?.tags ?? [])])} data-testid="promote-merge-tags-right">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txB.label}</span>
                                {#if (txB.tags ?? []).length > 0}
                                    <span class="flex flex-wrap gap-1">{#each txB.tags as tag}<span class="inline-block px-1.5 py-0.5 text-[10px] rounded" style={getStringBadgeStyle(tag)}>{tag}</span>{/each}</span>
                                {:else}
                                    —
                                {/if}
                            </button>
                        </div>
                        <!-- Union action + TagInput -->
                        <div class="flex items-center gap-1 mb-1">
                            <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/50" onclick={() => (resTags = mergeTagSets(txA?.tags ?? [], txB?.tags ?? []))} title={$t('transactions.promote.union')}>⟷ {$t('transactions.promote.union')}</button>
                        </div>
                        <TagInput value={resTags} availableTags={allTagSuggestions} onchange={(v) => (resTags = v)} />
                    </div>
                {/if}

                <!-- Date -->
                {#if diffDate}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-date">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.promote.fieldDate')}</div>
                        <div class="grid grid-cols-2 gap-2 mb-2">
                            <button type="button" class="text-left text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2rem] hover:ring-2 hover:ring-indigo-300 dark:hover:ring-indigo-600 transition-all" onclick={() => (resDate = txA?.date ?? '')} data-testid="promote-merge-date-left">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txA.label}</span>
                                {txA.date}
                            </button>
                            <button type="button" class="text-left text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2rem] hover:ring-2 hover:ring-indigo-300 dark:hover:ring-indigo-600 transition-all" onclick={() => (resDate = txB?.date ?? '')} data-testid="promote-merge-date-right">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txB.label}</span>
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
                            <button type="button" class="text-left text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2rem] hover:ring-2 hover:ring-indigo-300 dark:hover:ring-indigo-600 transition-all" onclick={() => (resCostBasis = txA?.cost_basis_override ?? '')}>
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txA.label}</span>
                                {txA.cost_basis_override || '—'}
                            </button>
                            <button type="button" class="text-left text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2rem] hover:ring-2 hover:ring-indigo-300 dark:hover:ring-indigo-600 transition-all" onclick={() => (resCostBasis = txB?.cost_basis_override ?? '')}>
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txB.label}</span>
                                {txB.cost_basis_override || '—'}
                            </button>
                        </div>
                        <input type="text" class="w-full text-xs px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100" bind:value={resCostBasis} />
                    </div>
                {/if}
            </div>

            <!-- Global actions -->
            <div class="flex justify-center gap-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                <button type="button" class="px-3 py-1.5 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200" onclick={allLeft} data-testid="promote-merge-all-left">
                    ◀ {$t('transactions.promote.allLeft')}
                </button>
                <button type="button" class="px-3 py-1.5 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200" onclick={allMerge} data-testid="promote-merge-all-merge">
                    ⟷ {$t('transactions.promote.allMerge')}
                </button>
                <button type="button" class="px-3 py-1.5 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200" onclick={allRight} data-testid="promote-merge-all-right">
                    {$t('transactions.promote.allRight')} ▸
                </button>
            </div>
        {:else}
            <p class="text-sm text-gray-500">{$t('transactions.promote.mergeConfirm')}</p>
        {/if}

        <!-- Footer -->
        <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={onCancel}>
                {$t('common.cancel')}
            </button>
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 inline-flex items-center gap-1.5" onclick={handleConfirm} data-testid="promote-merge-confirm">
                <Link2 size={14} />
                {$t('transactions.promote.mergeConfirm')}
            </button>
        </div>
    </div>
</ModalBase>
