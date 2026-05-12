<!--
  PromoteMergeModal.svelte — 3-column diff UI for resolving divergent fields
  when promoting two transactions into a paired type.

  For each field where txA[field] !== txB[field], shows:
    Left (readonly): txA value
    Center (editable): resolved value (default: merge)
    Right (readonly): txB value
  With ◀ ⟷ ▸ buttons to auto-populate the center.

  If ALL fields are identical, the parent should skip opening this modal
  and call onConfirm({}) directly.

  Plan D2 Step C5.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import {Link2} from 'lucide-svelte';

    interface Props {
        open: boolean;
        txA?: {label: string; description: string; tags: string[]; date: string; cost_basis_override: string} | null;
        txB?: {label: string; description: string; tags: string[]; date: string; cost_basis_override: string} | null;
        targetTypeLabel: string;
        onConfirm: (resolved: {description?: string; tags?: string[]; date?: string; cost_basis_override?: string}) => void;
        onCancel: () => void;
    }

    let {open, txA, txB, targetTypeLabel, onConfirm, onCancel}: Props = $props();

    // Resolved values (center column)
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

    // Reset resolved values when modal opens
    $effect(() => {
        if (!open || !txA || !txB) return;
        // Default: merge
        resDescription = mergeStrings(txA.description, txB.description);
        resTags = mergeTagSets(txA.tags, txB.tags);
        resDate = txA.date > txB.date ? txA.date : txB.date;
        resCostBasis = txA.cost_basis_override || txB.cost_basis_override || '';
    });

    function mergeStrings(a: string, b: string): string {
        if (!a) return b;
        if (!b) return a;
        if (a === b) return a;
        return `${a} | ${b}`;
    }

    function mergeTagSets(a: string[], b: string[]): string[] {
        return [...new Set([...(a ?? []), ...(b ?? [])])];
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
                {$t('transactions.promote.mergeTitle', {values: {type: targetTypeLabel}}) || 'Resolve divergent fields:'}
            </p>

            <div class="space-y-4">
                <!-- Description -->
                {#if diffDesc}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-description">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.promote.fieldDescription')}</div>
                        <div class="grid grid-cols-3 gap-2 items-start">
                            <!-- Left: txA (readonly) -->
                            <div class="text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 break-words min-h-[2rem]">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txA.label}</span>
                                {txA.description || '—'}
                            </div>
                            <!-- Center: resolved -->
                            <div class="space-y-1">
                                <div class="flex justify-center gap-1">
                                    <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={() => (resDescription = txA?.description ?? '')} title={$t('transactions.promote.useLeft')}>◀</button>
                                    <button
                                        type="button"
                                        class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
                                        onclick={() => (resDescription = mergeStrings(txA?.description ?? '', txB?.description ?? ''))}
                                        title={$t('transactions.promote.useMerge')}>⟷</button
                                    >
                                    <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={() => (resDescription = txB?.description ?? '')} title={$t('transactions.promote.useRight')}>▸</button>
                                </div>
                                <input type="text" class="w-full text-xs px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100" bind:value={resDescription} />
                            </div>
                            <!-- Right: txB (readonly) -->
                            <div class="text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 break-words min-h-[2rem]">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txB.label}</span>
                                {txB.description || '—'}
                            </div>
                        </div>
                    </div>
                {/if}

                <!-- Tags -->
                {#if diffTags}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-tags">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.promote.fieldTags')}</div>
                        <div class="grid grid-cols-3 gap-2 items-start">
                            <div class="text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2rem]">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txA.label}</span>
                                {#if (txA.tags ?? []).length > 0}
                                    <span class="flex flex-wrap gap-1"
                                        >{#each txA.tags as tag}<span class="inline-block px-1.5 py-0.5 text-[10px] rounded bg-gray-200 dark:bg-gray-600">{tag}</span>{/each}</span
                                    >
                                {:else}
                                    —
                                {/if}
                            </div>
                            <div class="space-y-1">
                                <div class="flex justify-center gap-1">
                                    <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={() => (resTags = [...(txA?.tags ?? [])])} title={$t('transactions.promote.useLeft')}>◀</button>
                                    <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={() => (resTags = mergeTagSets(txA?.tags ?? [], txB?.tags ?? []))} title={$t('transactions.promote.useMerge')}>⟷</button>
                                    <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={() => (resTags = [...(txB?.tags ?? [])])} title={$t('transactions.promote.useRight')}>▸</button>
                                </div>
                                <input
                                    type="text"
                                    class="w-full text-xs px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100"
                                    value={resTags.join(', ')}
                                    oninput={(e) => {
                                        resTags = (e.currentTarget as HTMLInputElement).value
                                            .split(',')
                                            .map((s) => s.trim())
                                            .filter(Boolean);
                                    }}
                                />
                            </div>
                            <div class="text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2rem]">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txB.label}</span>
                                {#if (txB.tags ?? []).length > 0}
                                    <span class="flex flex-wrap gap-1"
                                        >{#each txB.tags as tag}<span class="inline-block px-1.5 py-0.5 text-[10px] rounded bg-gray-200 dark:bg-gray-600">{tag}</span>{/each}</span
                                    >
                                {:else}
                                    —
                                {/if}
                            </div>
                        </div>
                    </div>
                {/if}

                <!-- Date -->
                {#if diffDate}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-date">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.promote.fieldDate')}</div>
                        <div class="grid grid-cols-3 gap-2 items-start">
                            <div class="text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2rem]">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txA.label}</span>
                                {txA.date}
                            </div>
                            <div class="space-y-1">
                                <div class="flex justify-center gap-1">
                                    <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={() => (resDate = txA?.date ?? '')} title={$t('transactions.promote.useLeft')}>◀</button>
                                    <button
                                        type="button"
                                        class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
                                        onclick={() => (resDate = (txA?.date ?? '') > (txB?.date ?? '') ? (txA?.date ?? '') : (txB?.date ?? ''))}
                                        title={$t('transactions.promote.useMerge')}>⟷</button
                                    >
                                    <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={() => (resDate = txB?.date ?? '')} title={$t('transactions.promote.useRight')}>▸</button>
                                </div>
                                <input type="date" class="w-full text-xs px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100" bind:value={resDate} />
                            </div>
                            <div class="text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2rem]">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txB.label}</span>
                                {txB.date}
                            </div>
                        </div>
                    </div>
                {/if}

                <!-- Cost Basis -->
                {#if diffCostBasis}
                    <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3" data-testid="promote-merge-field-cost_basis_override">
                        <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.promote.fieldCostBasis')}</div>
                        <div class="grid grid-cols-3 gap-2 items-start">
                            <div class="text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2rem]">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txA.label}</span>
                                {txA.cost_basis_override || '—'}
                            </div>
                            <div class="space-y-1">
                                <div class="flex justify-center gap-1">
                                    <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={() => (resCostBasis = txA?.cost_basis_override ?? '')} title={$t('transactions.promote.useLeft')}>◀</button>
                                    <button
                                        type="button"
                                        class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
                                        onclick={() => (resCostBasis = txA?.cost_basis_override || txB?.cost_basis_override || '')}
                                        title={$t('transactions.promote.useMerge')}>⟷</button
                                    >
                                    <button type="button" class="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" onclick={() => (resCostBasis = txB?.cost_basis_override ?? '')} title={$t('transactions.promote.useRight')}>▸</button>
                                </div>
                                <input type="text" class="w-full text-xs px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100" bind:value={resCostBasis} />
                            </div>
                            <div class="text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded p-2 min-h-[2rem]">
                                <span class="text-[10px] text-gray-400 block mb-0.5">{txB.label}</span>
                                {txB.cost_basis_override || '—'}
                            </div>
                        </div>
                    </div>
                {/if}
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
