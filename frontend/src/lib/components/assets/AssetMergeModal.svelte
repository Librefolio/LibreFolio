<!--
  AssetMergeModal.svelte — Fold a duplicate asset into the one the user wants to keep.

  ## Why this exists

  Stopping the creation of duplicates (inactive assets selectable, alternate ISINs
  searchable, soft-ISIN matching promoted) does nothing for the duplicates already in
  the database. The beta test left several: the same Italian BTP booked twice because
  the placement "CUM" ISIN and the tradeable market ISIN look like two instruments.
  Without a merge, that debt is permanent.

  ## Shape of the interaction

  Two deliberate steps, because the operation is destructive:

  1. **Pick the survivor.** The source is fixed (the asset the user acted on); the
     target is chosen from the whole catalogue, inactive assets included — a matured
     BTP is exactly the kind of thing being merged.
  2. **See what moves, then decide the identity.** A `dry_run` merge returns the real
     counts from the backend (transactions, prices, events, provider assignment) and
     the identifier union. Where both assets carry a value for the same structured
     identifier, `IdentifierPrimaryChooser` asks which one leads; the loser is demoted
     into `identifier_other`, never dropped. For the BTP that is the whole point: the
     quoted ISIN stays primary because it is the only one a provider can index, and the
     CUM ISIN keeps working as a soft match on every future import.

  The confirm button says what it does — the source asset is deleted.

  Svelte 5 runes, `data-testid` throughout for E2E.
-->
<script lang="ts">
    import {AlertTriangle, ArrowRight, Loader2} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import IdentifierPrimaryChooser, {type IdentifierChoice} from '$lib/components/assets/IdentifierPrimaryChooser.svelte';
    import {getAssetInfo, getAllAssets, ensureAssetsLoaded, refreshAllAssets, invalidateAfterMutation, type AssetInfo} from '$lib/stores/reference/assetStore';
    import {toasts} from '$lib/stores/app/toastStore.svelte';

    interface Props {
        /** Whether the modal is visible. */
        open?: boolean;
        /** The asset to fold in and delete. */
        sourceAsset: {id: number; display_name: string} | null;
        /** Stacking level; 60 when opened above another modal. */
        zIndex?: number;
        /** Fired after a successful merge, with the surviving asset id. */
        onmerged?: (targetId: number) => void;
        /** Fired when the modal should close. */
        onclose?: () => void;
    }

    let {open = $bindable(false), sourceAsset, zIndex = 50, onmerged, onclose}: Props = $props();

    /** The structured identifier columns, in the order they are shown. */
    const IDENTIFIER_FIELDS = [
        {field: 'identifier_isin', label: 'ISIN', isIsin: true},
        {field: 'identifier_ticker', label: 'Ticker', isIsin: false},
        {field: 'identifier_cusip', label: 'CUSIP', isIsin: false},
        {field: 'identifier_sedol', label: 'SEDOL', isIsin: false},
        {field: 'identifier_figi', label: 'FIGI', isIsin: false},
        {field: 'identifier_uuid', label: 'UUID', isIsin: false},
    ] as const;

    type MergePreview = {
        transactions?: number;
        prices?: number;
        prices_discarded?: number;
        events?: number;
        events_discarded?: number;
        transactions_relinked?: number;
        provider_assignment_moved?: boolean;
        provider_assignment_dropped?: boolean;
        identifiers_added?: string[];
    };

    let step = $state<1 | 2>(1);
    let targetId = $state<number | null>(null);
    let preview = $state<MergePreview | null>(null);
    let previewLoading = $state(false);
    let merging = $state(false);
    let errorMessage = $state<string | null>(null);
    /** Chosen primary per identifier column; absent = let the backend keep the target's. */
    let primaries = $state<Record<string, string>>({});

    let targetAsset = $derived(targetId != null ? (getAssetInfo(targetId) ?? null) : null);
    let sourceInfo = $derived(sourceAsset ? (getAssetInfo(sourceAsset.id) ?? null) : null);

    // Reset whenever the modal is (re)opened on a different source.
    $effect(() => {
        if (!open) return;
        void sourceAsset?.id;
        step = 1;
        targetId = null;
        preview = null;
        errorMessage = null;
        primaries = {};
        void ensureAssetsLoaded();
    });

    /**
     * Identifier columns where both assets hold a value and the values differ.
     *
     * Only these need a decision: a value present on one side alone simply survives
     * (as primary if the slot is free, as an alternate otherwise), and identical values
     * have nothing to choose between.
     */
    let conflicts = $derived.by(() => {
        const src = sourceInfo;
        const tgt = targetAsset;
        if (!src || !tgt) return [] as Array<{field: string; label: string; isIsin: boolean; choices: IdentifierChoice[]}>;
        const out: Array<{field: string; label: string; isIsin: boolean; choices: IdentifierChoice[]}> = [];
        for (const {field, label, isIsin} of IDENTIFIER_FIELDS) {
            const a = ((src as unknown as Record<string, unknown>)[field] as string | null | undefined)?.trim() ?? '';
            const b = ((tgt as unknown as Record<string, unknown>)[field] as string | null | undefined)?.trim() ?? '';
            if (!a || !b || a.toLowerCase() === b.toLowerCase()) continue;
            out.push({
                field,
                label,
                isIsin,
                choices: [
                    {value: b, origin: 'stored', detail: tgt.display_name},
                    {value: a, origin: 'stored', detail: src.display_name},
                ],
            });
        }
        return out;
    });

    /** Never offer the source itself as the survivor. */
    function targetFilter(a: AssetInfo): boolean {
        return a.id !== sourceAsset?.id;
    }

    /** Ask the backend what the merge would move, without writing anything. */
    async function loadPreview() {
        if (!sourceAsset || targetId == null) return;
        previewLoading = true;
        errorMessage = null;
        try {
            const res = await zodiosApi.merge_assets_api_v1_assets_merge_post({
                source_asset_id: sourceAsset.id,
                target_asset_id: targetId,
                dry_run: true,
            });
            preview = ((res as unknown as {preview?: MergePreview})?.preview ?? {}) as MergePreview;
            // Seed the choosers with the target's value: the default is "the survivor keeps its identity".
            const seeded: Record<string, string> = {};
            for (const c of conflicts) seeded[c.field] = c.choices[0].value;
            primaries = seeded;
            step = 2;
        } catch (e: unknown) {
            errorMessage = extractError(e);
        } finally {
            previewLoading = false;
        }
    }

    /** Run the real merge. */
    async function confirmMerge() {
        if (!sourceAsset || targetId == null) return;
        merging = true;
        errorMessage = null;
        const survivorId = targetId;
        try {
            await zodiosApi.merge_assets_api_v1_assets_merge_post({
                source_asset_id: sourceAsset.id,
                target_asset_id: survivorId,
                identifier_primaries: Object.keys(primaries).length > 0 ? primaries : undefined,
                dry_run: false,
            });
            // The source is gone and the target changed identity: evict both from the
            // shared cache so every other page stops showing the duplicate.
            invalidateAfterMutation(sourceAsset.id);
            invalidateAfterMutation(survivorId);
            await refreshAllAssets();
            toasts.success(
                $t('assets.merge.toastOk', {
                    values: {source: sourceAsset.display_name, target: getAssetInfo(survivorId)?.display_name ?? ''},
                }),
            );
            onmerged?.(survivorId);
            open = false;
            onclose?.();
        } catch (e: unknown) {
            errorMessage = extractError(e);
        } finally {
            merging = false;
        }
    }

    function extractError(e: unknown): string {
        const detail = (e as {response?: {data?: {detail?: unknown}}})?.response?.data?.detail;
        if (typeof detail === 'string') return detail;
        const msg = (e as {message?: string})?.message;
        return msg || $t('assets.merge.errorGeneric');
    }

    function close() {
        open = false;
        onclose?.();
    }

    /** Rows of the "what moves" table, hiding the ones that are zero. */
    let movedRows = $derived.by(() => {
        const p = preview;
        if (!p) return [] as Array<{key: string; label: string; value: string}>;
        const rows: Array<{key: string; label: string; value: string}> = [];
        const push = (key: string, label: string, n: number) => {
            if (n > 0) rows.push({key, label, value: String(n)});
        };
        push('transactions', $t('assets.merge.moved.transactions'), p.transactions ?? 0);
        push('prices', $t('assets.merge.moved.prices'), p.prices ?? 0);
        push('pricesDiscarded', $t('assets.merge.moved.pricesDiscarded'), p.prices_discarded ?? 0);
        push('events', $t('assets.merge.moved.events'), p.events ?? 0);
        push('eventsDiscarded', $t('assets.merge.moved.eventsDiscarded'), p.events_discarded ?? 0);
        push('relinked', $t('assets.merge.moved.relinked'), p.transactions_relinked ?? 0);
        if (p.provider_assignment_moved) rows.push({key: 'providerMoved', label: $t('assets.merge.moved.providerMoved'), value: '✓'});
        if (p.provider_assignment_dropped) rows.push({key: 'providerDropped', label: $t('assets.merge.moved.providerDropped'), value: '✓'});
        return rows;
    });

    /** Alternate identifiers the target will gain — proof that nothing is lost. */
    let identifiersAdded = $derived(preview?.identifiers_added ?? []);

    let hasTargets = $derived(getAllAssets().some(targetFilter));
</script>

<!-- Step 1 needs `allowOverflow` for the target dropdown; step 2 has no dropdown and is
     long enough to need real scrolling, or its footer buttons fall off the viewport. -->
<ModalBase {open} {zIndex} maxWidth="2xl" allowOverflow={step === 1} onRequestClose={close} testId="asset-merge-modal">
    <div class="p-6 space-y-5 {step === 1 ? '' : 'max-h-[85vh] overflow-y-auto'}">
        <div>
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100" data-testid="asset-merge-title">
                {$t('assets.merge.title')}
            </h2>
            <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
                {$t('assets.merge.subtitle')}
            </p>
        </div>

        <!-- The direction of the operation, stated once and always visible. -->
        <div class="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/60 px-4 py-3 text-sm">
            <span class="font-medium text-gray-900 dark:text-gray-100 line-through decoration-red-400" data-testid="asset-merge-source">
                {sourceAsset?.display_name ?? ''}
            </span>
            <ArrowRight class="text-gray-400 shrink-0" size={16} />
            <span class="font-medium text-gray-900 dark:text-gray-100" data-testid="asset-merge-target">
                {targetAsset?.display_name ?? $t('assets.merge.targetPlaceholder')}
            </span>
        </div>

        {#if step === 1}
            <div class="space-y-2">
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {$t('assets.merge.chooseTarget')}
                </span>
                <AssetSelect bind:value={targetId} filter={targetFilter} placeholder={$t('assets.merge.targetPlaceholder')} testid="asset-merge-target-select" />
                {#if !hasTargets}
                    <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="asset-merge-no-targets">
                        {$t('assets.merge.noTargets')}
                    </p>
                {/if}
                <p class="text-xs text-gray-500 dark:text-gray-400">
                    {$t('assets.merge.chooseTargetHint')}
                </p>
            </div>
        {:else}
            <!-- What actually moves, straight from the backend's dry run. -->
            <div class="space-y-2">
                <span class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {$t('assets.merge.whatMoves')}
                </span>
                {#if movedRows.length === 0}
                    <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="asset-merge-moves-nothing">
                        {$t('assets.merge.movesNothing')}
                    </p>
                {:else}
                    <ul class="divide-y divide-gray-100 dark:divide-slate-700 rounded-lg border border-gray-200 dark:border-slate-700" data-testid="asset-merge-preview">
                        {#each movedRows as row (row.key)}
                            <li class="flex items-center justify-between px-4 py-2 text-sm" data-testid="asset-merge-preview-{row.key}">
                                <span class="text-gray-600 dark:text-gray-400">{row.label}</span>
                                <span class="font-medium text-gray-900 dark:text-gray-100">{row.value}</span>
                            </li>
                        {/each}
                    </ul>
                {/if}
            </div>

            {#if conflicts.length > 0}
                <!-- The identity decision: which code leads, for each contested type. -->
                <div class="space-y-3" data-testid="asset-merge-conflicts">
                    {#each conflicts as conflict (conflict.field)}
                        <IdentifierPrimaryChooser assetName={targetAsset?.display_name ?? ''} choices={conflict.choices} isIsin={conflict.isIsin} bind:primary={primaries[conflict.field]} testid="asset-merge-chooser-{conflict.field}" typeLabel={conflict.label} />
                    {/each}
                </div>
            {/if}

            {#if identifiersAdded.length > 0}
                <div class="rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-3" data-testid="asset-merge-identifiers-added">
                    <span class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        {$t('assets.merge.identifiersKept')}
                    </span>
                    <div class="mt-2 flex flex-wrap gap-1.5">
                        {#each identifiersAdded as value (value)}
                            <span class="inline-flex items-center rounded-md bg-gray-100 dark:bg-slate-700 px-2 py-0.5 text-xs font-mono text-gray-700 dark:text-gray-300">
                                {value}
                            </span>
                        {/each}
                    </div>
                    <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
                        {$t('assets.merge.identifiersKeptHint')}
                    </p>
                </div>
            {/if}

            <div class="flex items-start gap-2 rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/30 px-4 py-3" data-testid="asset-merge-warning">
                <AlertTriangle class="text-red-500 shrink-0 mt-0.5" size={16} />
                <p class="text-sm text-red-700 dark:text-red-300">
                    {$t('assets.merge.destructiveWarning', {values: {name: sourceAsset?.display_name ?? ''}})}
                </p>
            </div>
        {/if}

        {#if errorMessage}
            <p class="text-sm text-red-600 dark:text-red-400" data-testid="asset-merge-error">{errorMessage}</p>
        {/if}

        <div class="flex justify-end gap-2 pt-1">
            {#if step === 2}
                <button
                    class="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700"
                    data-testid="asset-merge-back"
                    disabled={merging}
                    onclick={() => {
                        step = 1;
                        errorMessage = null;
                    }}
                    type="button"
                >
                    {$t('common.back')}
                </button>
            {/if}
            <button class="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700" data-testid="asset-merge-cancel" disabled={merging} onclick={close} type="button">
                {$t('common.cancel')}
            </button>
            {#if step === 1}
                <button class="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-libre-green text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed" data-testid="asset-merge-next" disabled={targetId == null || previewLoading} onclick={loadPreview} type="button">
                    {#if previewLoading}<Loader2 class="animate-spin" size={14} />{/if}
                    {$t('common.continue')}
                </button>
            {:else}
                <button class="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed" data-testid="asset-merge-confirm" disabled={merging} onclick={confirmMerge} type="button">
                    {#if merging}<Loader2 class="animate-spin" size={14} />{/if}
                    {$t('assets.merge.confirmButton')}
                </button>
            {/if}
        </div>
    </div>
</ModalBase>
