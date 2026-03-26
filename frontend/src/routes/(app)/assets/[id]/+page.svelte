<script lang="ts">
    /**
     * Asset Detail Page — Placeholder (Step 4)
     *
     * Will be implemented in Phase 06 Step 4 with:
     * - PriceChartFull + technical analysis
     * - AssetDataEditorSection
     * - Provider management
     * - Edit/Delete actions
     */
    import {page} from '$app/stores';
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import {ArrowLeft, Construction} from 'lucide-svelte';

    const assetId = $derived($page.params.id);
</script>

<div class="space-y-6" data-testid="asset-detail-page">
    <!-- Back button -->
    <button
            class="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-libre-green dark:hover:text-emerald-400 transition-colors"
            onclick={() => goto('/assets')}
    >
        <ArrowLeft size={16}/>
        {$t('assets.title')}
    </button>

    <!-- Placeholder content -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-12 text-center">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full mb-4">
            <Construction class="text-amber-600 dark:text-amber-400" size={32}/>
        </div>
        <h2 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-2">
            Asset #{assetId} — {$t('common.comingSoon') ?? 'Coming Soon'}
        </h2>
        <p class="text-gray-500 dark:text-gray-400 text-sm max-w-md mx-auto">
            This page will be implemented in Step 4 with full price chart, technical analysis, data editor, and provider management.
        </p>
    </div>
</div>

