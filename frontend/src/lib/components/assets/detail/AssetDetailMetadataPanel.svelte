<!--
  AssetDetailMetadataPanel — the foldable «Metadata & Classification» panel of the asset detail page:
  description, provider URL, sector and geography charts, identifiers, provider assignment, and the
  link to the edit modal. Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ChevronDown, Info} from 'lucide-svelte';
    import AllocationPieChart from '$lib/components/charts/AllocationPieChart.svelte';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import type {ProviderAssignmentFlat} from '$lib/types';

    interface Props {
        /** The panel is unfolded; kept by the page, so it survives a tab switch and a change of asset. */
        open: boolean;
        shortDescription: string | null;
        providerExternalUrl: string | null;
        classificationLoaded: boolean;
        sectorDistribution: Record<string, number> | null;
        geographicDistribution: Record<string, number> | null;
        identifiersList: [string, string][];
        providerAssignment: ProviderAssignmentFlat | null;
        providerIconUrl: string | null;
        assignmentProviderName: string;
        /** «Edit via modal»: the page opens the asset modal. */
        onedit: () => void;
    }

    let {open = $bindable(), shortDescription, providerExternalUrl, classificationLoaded, sectorDistribution, geographicDistribution, identifiersList, providerAssignment, providerIconUrl, assignmentProviderName, onedit}: Props = $props();
</script>

<div class="bg-lf-card text-lf-primary rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle">
    <button class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-lf-secondary hover:bg-lf-hover transition-colors rounded-xl" data-testid="asset-detail-metadata-toggle" use:guideAnchor={'asset.detail.metadata'} onclick={() => (open = !open)}>
        <span class="flex items-center gap-2">
            <Info class="text-sky-500" size={15} />
            {$t('assetDetail.metadata')}
        </span>
        <ChevronDown class="transition-transform {open ? 'rotate-180' : ''}" size={15} />
    </button>
    {#if open}
        <div data-testid="asset-detail-metadata-panel" class="px-4 pb-4 border-t border-lf-subtle pt-3 space-y-4">
            <!-- Description (from classification_params.short_description) — always first if set -->
            {#if shortDescription}
                <div>
                    <h4 class="text-xs font-semibold text-lf-muted uppercase mb-2">{$t('common.description')}</h4>
                    <p class="text-sm text-lf-secondary whitespace-pre-wrap leading-relaxed">{shortDescription}</p>
                </div>
            {/if}

            <!-- External URLs (provider URL only — user URL is in header) -->
            {#if providerExternalUrl}
                <div>
                    <h4 class="text-xs font-semibold text-lf-muted uppercase mb-2">{$t('assets.provider.providerUrl')}</h4>
                    <a href={providerExternalUrl} target="_blank" rel="noopener noreferrer" class="text-sm text-lf-link hover:underline break-all">{providerExternalUrl}</a>
                </div>
            {/if}

            <!-- Classification Charts -->
            {#if classificationLoaded && (sectorDistribution || geographicDistribution)}
                <div class="space-y-3">
                    <h4 class="text-xs font-semibold text-lf-muted uppercase">{$t('common.classification')}</h4>

                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {#if geographicDistribution && Object.keys(geographicDistribution).length > 0}
                            <div class="bg-lf-panel rounded-lg p-3">
                                <h5 class="text-xs font-medium text-lf-muted mb-2">{$t('common.geoDistribution')}</h5>
                                <GeographyMap data={geographicDistribution} height="280px" language={$currentLanguage} />
                            </div>
                        {/if}

                        {#if sectorDistribution && Object.keys(sectorDistribution).length > 0}
                            <div class="bg-lf-panel rounded-lg p-3">
                                <h5 class="text-xs font-medium text-lf-muted mb-2">{$t('common.sectorDistribution')}</h5>
                                <AllocationPieChart data={Object.entries(sectorDistribution).map(([name, w]) => ({name, value: w * 100, amount: 0}))} height="280px" />
                            </div>
                        {/if}
                    </div>
                </div>
            {:else if !classificationLoaded}
                <div class="text-sm text-lf-muted italic">
                    {$t('common.classification')} — {$t('common.loading')}...
                </div>
            {:else}
                <p class="text-sm text-lf-muted">{$t('assetDetail.noClassification')}</p>
            {/if}

            <!-- Identifiers -->
            {#if identifiersList.length > 0}
                <div>
                    <h4 class="text-xs font-semibold text-lf-muted uppercase mb-2">{$t('common.identifiers')}</h4>
                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {#each identifiersList as [label, value]}
                            <div class="bg-lf-panel rounded-lg px-3 py-2">
                                <span class="text-[10px] uppercase text-lf-muted">{label}</span>
                                <p class="text-sm font-mono text-lf-secondary">{value}</p>
                            </div>
                        {/each}
                    </div>
                </div>
            {:else}
                <p class="text-sm text-lf-muted">{$t('assetDetail.noIdentifiers')}</p>
            {/if}

            {#if providerAssignment}
                <div>
                    <h4 class="text-xs font-semibold text-lf-muted uppercase mb-2">{$t('common.provider')}</h4>
                    <div class="flex items-center gap-3 text-sm flex-wrap">
                        <span class="inline-flex items-center gap-1.5 font-medium text-lf-secondary">
                            {#if providerIconUrl}
                                <img src={providerIconUrl} alt="" class="w-4 h-4 rounded-sm object-contain" />
                            {/if}
                            {assignmentProviderName}
                        </span>
                        <span class="text-lf-muted">→</span>
                        <span class="font-mono text-lf-muted">{providerAssignment.identifier} ({providerAssignment.identifier_type})</span>
                        {#if providerAssignment.last_fetch_at}
                            <span class="text-xs text-lf-muted">
                                {$t('assets.provider.lastFetch')}: {new Date(String(providerAssignment.last_fetch_at)).toLocaleDateString(uiLocale())}
                            </span>
                        {:else}
                            <span class="text-xs text-lf-muted">{$t('assets.provider.neverFetched')}</span>
                        {/if}
                    </div>
                </div>
            {/if}

            <button class="text-xs text-lf-link hover:underline disabled:opacity-50 disabled:cursor-not-allowed" onclick={onedit}>
                {$t('assetDetail.editViaModal')} →
            </button>
        </div>
    {/if}
</div>
