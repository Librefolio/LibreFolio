<!--
  AssetDetailToolbarActions — the actions of the asset detail page's toolbar: AI export, Edit, Sync (or
  Recalculate, crossed out with its reason when it is blocked) and Refresh. Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Pencil, RefreshCw, RotateCw} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import AiExportMenu, {type AiExportMenuLabels} from '$lib/features/ai-export/AiExportMenu.svelte';
    import type {PreparedAiExport} from '$lib/features/ai-export/aiExportClipboard';
    import type {AiExportOptionsSelection} from '$lib/features/ai-export/aiExportOptions';
    import type {AiExportCatalogCompatibilityResult} from '$lib/features/ai-export/catalog/compatibility';
    import {getAiExportErrorMessage} from '$lib/features/ai-export/ui';
    import {toasts} from '$lib/stores/app/toastStore.svelte';

    interface Props {
        /** The toolbar shows the labels of its actions, not only their icons (PageToolbar's layout). */
        showActionLabels: boolean;
        /** The asset the page shows: the AI export remembers its options per asset. */
        assetId: number;
        aiExportCompatibility: AiExportCatalogCompatibilityResult;
        aiExportLabels: AiExportMenuLabels;
        /** The AI export catalogue is loading or failed, or the asset is not loaded yet. */
        aiExportDisabled: boolean;
        onaiexportprepare: (options: AiExportOptionsSelection) => Promise<PreparedAiExport>;
        onaiexportcopied: (result: PreparedAiExport) => void;
        /** The asset or its classification is not loaded yet. */
        editDisabled: boolean;
        onedit: () => void;
        /** No sync for this asset: manual only, or archived. */
        syncBlocked: boolean;
        syncDisabledReason: string;
        syncing: boolean;
        /** A parametric provider: the action recalculates the series. */
        isParametric: boolean;
        providerAssignmentLoaded: boolean;
        onsync: () => void;
        /** The page is loading what the user asked for (`pageBusy.busy`, Y11): the Refresh button waits for it. */
        busy: boolean;
        onrefresh: () => void;
    }

    let {showActionLabels, assetId, aiExportCompatibility, aiExportLabels, aiExportDisabled, onaiexportprepare, onaiexportcopied, editDisabled, onedit, syncBlocked, syncDisabledReason, syncing, isParametric, providerAssignmentLoaded, onsync, busy, onrefresh}: Props = $props();
</script>

<AiExportMenu
    domain="asset"
    compatibility={aiExportCompatibility}
    memoryKey={`asset:${assetId}`}
    defaultSelectionId="asset.market_analysis"
    disabled={aiExportDisabled}
    labels={aiExportLabels}
    showLabel={showActionLabels}
    onprepare={onaiexportprepare}
    oncopied={onaiexportcopied}
    onerror={(error) => toasts.error(getAiExportErrorMessage($t, error))}
/>
<button
    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    data-testid="asset-detail-edit-btn"
    disabled={editDisabled}
    onclick={() => onedit()}
>
    <Pencil size={14} />
    {#if showActionLabels}<span>{$t('common.edit')}</span>{/if}
</button>
{#if syncBlocked}
    <Tooltip text={syncDisabledReason} position="top" maxWidth="320px" interactiveChild>
        <button
            class="w-full flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors opacity-50 cursor-not-allowed"
            data-testid="asset-detail-sync-btn"
            disabled={syncing || syncBlocked}
            onclick={onsync}
        >
            <RotateCw class={syncing ? 'animate-spin' : ''} size={14} />
            {#if showActionLabels}<span class="line-through">{syncing ? $t('common.syncing') : isParametric ? $t('assetDetail.recalculate') : $t('common.sync')}</span>{/if}
        </button>
    </Tooltip>
{:else}
    <button
        class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors"
        data-testid="asset-detail-sync-btn"
        disabled={syncing || syncBlocked || !providerAssignmentLoaded}
        onclick={onsync}
    >
        <RotateCw class={syncing ? 'animate-spin' : ''} size={14} />
        {#if showActionLabels}<span>{syncing ? $t('common.syncing') : isParametric ? $t('assetDetail.recalculate') : $t('common.sync')}</span>{/if}
    </button>
{/if}
<button
    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    data-testid="asset-detail-refresh-btn"
    data-busy={busy ? 'true' : 'false'}
    disabled={busy}
    onclick={() => onrefresh()}
>
    <RefreshCw class={busy ? 'animate-spin' : ''} size={14} />
    {#if showActionLabels}<span>{$t('common.refresh')}</span>{/if}
</button>
