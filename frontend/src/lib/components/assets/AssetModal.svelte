<!--
  AssetModal — Create/Edit asset modal.

  Features:
  - Create mode: search + auto-fill + auto-test
  - Edit mode: pre-populated form
  - Identifiers section (collapsible) with Ask Provider
  - Provider Assignment section (collapsible) with test
  - Confirmation modals (save without test, change identifier)
  - ModalBase with allowOverflow
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {ChevronDown, ChevronRight, Info, Loader2, RefreshCw, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import AssetSearchAutocomplete from './AssetSearchAutocomplete.svelte';
    import ProviderAssignmentSection from './ProviderAssignmentSection.svelte';
    import {toasts} from '$lib/stores/toastStore.svelte';

    // =========================================================================
    // Types
    // =========================================================================

    interface AssetData {
        id?: number;
        display_name: string;
        currency: string;
        asset_type: string;
        icon_url?: string | null;
        active?: boolean;
        // Identifiers
        identifier_isin?: string | null;
        identifier_ticker?: string | null;
        identifier_cusip?: string | null;
        identifier_sedol?: string | null;
        identifier_figi?: string | null;
        identifier_uuid?: string | null;
        identifier_other?: string | null;
        // Provider
        provider_code?: string | null;
        provider_identifier?: string;
        provider_identifier_type?: string;
        provider_params?: Record<string, any> | null;
        provider_user_url?: string;
        provider_url?: string | null;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        open?: boolean;
        editMode?: boolean;
        editData?: AssetData | null;
        oncreated?: () => void;
        onupdated?: () => void;
        onclose?: () => void;
    }

    let {
        open = $bindable(false),
        editMode = false,
        editData = null,
        oncreated,
        onupdated,
        onclose,
    }: Props = $props();

    // =========================================================================
    // State — Form fields
    // =========================================================================

    let displayName = $state('');
    let currency = $state('USD');
    let assetType = $state('STOCK');
    let iconUrl = $state<string | null>(null);

    // Identifiers
    let identifierIsin = $state('');
    let identifierTicker = $state('');
    let identifierCusip = $state('');
    let identifierSedol = $state('');
    let identifierFigi = $state('');
    let identifierUuid = $state('');
    let identifierOther = $state('');

    // Provider
    let providerCode = $state('');
    let providerIdentifier = $state('');
    let providerIdentifierType = $state('TICKER');
    let providerParams = $state<Record<string, any> | null>(null);
    let providerUserUrl = $state('');
    let providerUrl = $state<string | null>(null);
    let providerNoProvider = $state(false);
    let providerTestStatus = $state<'not_tested' | 'testing' | 'passed' | 'failed'>('not_tested');

    // UI state
    let identifiersExpanded = $state(false);
    let providerExpanded = $state(false);
    let saving = $state(false);
    let formError = $state<string | null>(null);
    let askingProvider = $state(false);
    let autoFilledFields = $state<Set<string>>(new Set());
    let conflictFields = $state<Map<string, string>>(new Map());

    // Confirmation modals
    let showSaveWithoutTestConfirm = $state(false);
    let showIdentifierChangeConfirm = $state(false);
    let pendingSearchResult = $state<any>(null);

    // Track if search result was selected (for auto-assign banner)
    let searchResultSelected = $state(false);

    // =========================================================================
    // Derived
    // =========================================================================

    let isValid = $derived(displayName.trim().length > 0);
    let hasProvider = $derived(!providerNoProvider && providerCode !== '' && providerIdentifier !== '');
    let title = $derived(editMode ? $t('assets.modal.titleEdit') : $t('assets.modal.title'));

    // =========================================================================
    // Lifecycle — Populate in edit mode
    // =========================================================================

    $effect(() => {
        if (open) {
            if (editMode && editData) {
                populateFromEditData(editData);
            } else {
                resetForm();
            }
        }
    });

    function populateFromEditData(data: AssetData) {
        displayName = data.display_name;
        currency = data.currency;
        assetType = data.asset_type ?? 'STOCK';
        iconUrl = data.icon_url ?? null;
        identifierIsin = data.identifier_isin ?? '';
        identifierTicker = data.identifier_ticker ?? '';
        identifierCusip = data.identifier_cusip ?? '';
        identifierSedol = data.identifier_sedol ?? '';
        identifierFigi = data.identifier_figi ?? '';
        identifierUuid = data.identifier_uuid ?? '';
        identifierOther = data.identifier_other ?? '';
        providerCode = data.provider_code ?? '';
        providerIdentifier = data.provider_identifier ?? '';
        providerIdentifierType = data.provider_identifier_type ?? 'TICKER';
        providerParams = data.provider_params ?? null;
        providerUserUrl = data.provider_user_url ?? '';
        providerUrl = data.provider_url ?? null;
        providerNoProvider = !data.provider_code;
        identifiersExpanded = !!(data.identifier_isin || data.identifier_ticker);
        providerExpanded = !!data.provider_code;
        searchResultSelected = false;
        autoFilledFields = new Set();
        conflictFields = new Map();
        formError = null;
        providerTestStatus = 'not_tested';
    }

    function resetForm() {
        displayName = '';
        currency = 'USD';
        assetType = 'STOCK';
        iconUrl = null;
        identifierIsin = '';
        identifierTicker = '';
        identifierCusip = '';
        identifierSedol = '';
        identifierFigi = '';
        identifierUuid = '';
        identifierOther = '';
        providerCode = '';
        providerIdentifier = '';
        providerIdentifierType = 'TICKER';
        providerParams = null;
        providerUserUrl = '';
        providerUrl = null;
        providerNoProvider = false;
        identifiersExpanded = false;
        providerExpanded = false;
        searchResultSelected = false;
        autoFilledFields = new Set();
        conflictFields = new Map();
        formError = null;
        saving = false;
        providerTestStatus = 'not_tested';
    }

    // =========================================================================
    // Search result selection — auto-fill + auto-test
    // =========================================================================

    function handleSearchSelect(result: any) {
        // If edit mode and identifier differs → show confirm
        if (editMode && providerIdentifier && providerIdentifier !== result.identifier) {
            pendingSearchResult = result;
            showIdentifierChangeConfirm = true;
            return;
        }
        applySearchResult(result);
    }

    function applySearchResult(result: any) {
        // Auto-fill form
        displayName = result.display_name || displayName;
        if (result.asset_type) assetType = result.asset_type.toUpperCase();
        if (result.currency) currency = result.currency;

        // Auto-fill identifier based on identifier_type
        const idType = (result.identifier_type ?? '').toUpperCase();
        if (idType === 'TICKER') identifierTicker = result.identifier;
        else if (idType === 'ISIN') identifierIsin = result.identifier;

        // Auto-fill provider
        providerCode = result.provider_code;
        providerIdentifier = result.identifier;
        providerIdentifierType = result.identifier_type;
        providerUrl = result.provider_url ?? null;
        providerNoProvider = false;
        providerParams = null;

        // Expand sections
        identifiersExpanded = true;
        providerExpanded = true;
        searchResultSelected = true;
        formError = null;

        // Auto-trigger test
        autoTriggerProbe();
    }

    async function autoTriggerProbe() {
        providerTestStatus = 'testing';
        // Let ProviderAssignmentSection handle the actual test
        // We just need to trigger it — the section's testConfiguration method runs
        // via $effect watching testStatus. Instead, call the probe directly.
        try {
            const response = await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post({
                provider_code: providerCode,
                identifier: providerIdentifier,
                identifier_type: providerIdentifierType as any,
                provider_params: providerParams,
                operations: ['current_price', 'history'],
            }) as any;

            const cp = response.current_price;
            const h = response.history;
            const allSuccess = (cp?.success ?? false) && (h?.success !== false);
            providerTestStatus = allSuccess ? 'passed' : 'failed';

            if (response.provider_url) providerUrl = response.provider_url;
        } catch {
            providerTestStatus = 'failed';
        }
    }

    // =========================================================================
    // Ask Provider (metadata) — fill identifiers
    // =========================================================================

    async function handleAskProvider() {
        if (!providerCode || !providerIdentifier) return;
        askingProvider = true;
        autoFilledFields = new Set();
        conflictFields = new Map();

        try {
            const response = await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post({
                provider_code: providerCode,
                identifier: providerIdentifier,
                identifier_type: providerIdentifierType as any,
                provider_params: providerParams,
                operations: ['metadata'],
            }) as any;

            const meta = response.metadata;
            if (meta?.success && meta.patch_data) {
                const pd = meta.patch_data;
                fillIdentifier('identifier_ticker', pd.identifier_ticker);
                fillIdentifier('identifier_isin', pd.identifier_isin);
                fillIdentifier('identifier_cusip', pd.identifier_cusip);
                fillIdentifier('identifier_sedol', pd.identifier_sedol);
                fillIdentifier('identifier_figi', pd.identifier_figi);
                fillIdentifier('identifier_uuid', pd.identifier_uuid);
                fillIdentifier('identifier_other', pd.identifier_other);
            }
        } catch (e: any) {
            console.error('Ask Provider failed:', e);
        } finally {
            askingProvider = false;
        }
    }

    function fillIdentifier(field: string, value: string | null | undefined) {
        if (!value) return;
        const currentVal = getIdentifierValue(field);
        if (!currentVal) {
            setIdentifierValue(field, value);
            autoFilledFields = new Set([...autoFilledFields, field]);
        } else if (currentVal !== value) {
            conflictFields = new Map([...conflictFields, [field, value]]);
        }
    }

    function getIdentifierValue(field: string): string {
        switch (field) {
            case 'identifier_isin': return identifierIsin;
            case 'identifier_ticker': return identifierTicker;
            case 'identifier_cusip': return identifierCusip;
            case 'identifier_sedol': return identifierSedol;
            case 'identifier_figi': return identifierFigi;
            case 'identifier_uuid': return identifierUuid;
            case 'identifier_other': return identifierOther;
            default: return '';
        }
    }

    function setIdentifierValue(field: string, value: string) {
        switch (field) {
            case 'identifier_isin': identifierIsin = value; break;
            case 'identifier_ticker': identifierTicker = value; break;
            case 'identifier_cusip': identifierCusip = value; break;
            case 'identifier_sedol': identifierSedol = value; break;
            case 'identifier_figi': identifierFigi = value; break;
            case 'identifier_uuid': identifierUuid = value; break;
            case 'identifier_other': identifierOther = value; break;
        }
    }

    // =========================================================================
    // Save
    // =========================================================================

    function handleSave() {
        if (!isValid) return;
        // Check if provider configured but not tested
        if (hasProvider && providerTestStatus !== 'passed') {
            showSaveWithoutTestConfirm = true;
            return;
        }
        doSave();
    }

    async function doSave() {
        saving = true;
        formError = null;
        showSaveWithoutTestConfirm = false;

        try {
            if (editMode && editData?.id) {
                await saveEdit(editData.id);
            } else {
                await saveCreate();
            }
        } catch (e: any) {
            if (e?.response?.status === 409) {
                formError = $t('assets.modal.duplicateName');
            } else {
                formError = e?.message || 'Save failed';
            }
        } finally {
            saving = false;
        }
    }

    async function saveCreate() {
        // Step 1: Create asset
        const createPayload = [{
            display_name: displayName.trim(),
            currency: currency,
            asset_type: assetType,
            icon_url: iconUrl || undefined,
            identifier_isin: identifierIsin || undefined,
            identifier_ticker: identifierTicker || undefined,
            identifier_cusip: identifierCusip || undefined,
            identifier_sedol: identifierSedol || undefined,
            identifier_figi: identifierFigi || undefined,
            identifier_uuid: identifierUuid || undefined,
            identifier_other: identifierOther || undefined,
        }];

        const createResp = await zodiosApi.create_assets_bulk_api_v1_assets_post(createPayload as any) as any;
        const result = createResp?.results?.[0];
        if (!result?.success) {
            throw new Error(result?.message || 'Failed to create asset');
        }
        const assetId = result.asset_id;

        // Step 2: Assign provider if configured
        if (hasProvider) {
            const assignPayload = [{
                asset_id: assetId,
                provider_code: providerCode,
                identifier: providerIdentifier,
                identifier_type: providerIdentifierType,
                provider_params: providerParams,
                fetch_interval: 1440,
                user_url: providerUserUrl || undefined,
            }];
            await zodiosApi.assign_providers_bulk_api_v1_assets_provider_post(assignPayload as any);
        }

        toasts.success($t('assets.modal.createSuccess', {values: {name: displayName}}));
        open = false;
        oncreated?.();
    }

    async function saveEdit(assetId: number) {
        // Step 1: Patch asset
        const patchPayload = [{
            asset_id: assetId,
            display_name: displayName.trim(),
            currency: currency,
            asset_type: assetType,
            icon_url: iconUrl,
            identifier_isin: identifierIsin || null,
            identifier_ticker: identifierTicker || null,
            identifier_cusip: identifierCusip || null,
            identifier_sedol: identifierSedol || null,
            identifier_figi: identifierFigi || null,
            identifier_uuid: identifierUuid || null,
            identifier_other: identifierOther || null,
        }];

        await zodiosApi.patch_assets_bulk_api_v1_assets_patch(patchPayload as any);

        // Step 2: Handle provider change
        if (providerNoProvider) {
            // Remove provider
            await zodiosApi.remove_providers_bulk_api_v1_assets_provider_delete(undefined, {
                queries: {asset_ids: [assetId]},
            });
        } else if (hasProvider) {
            const assignPayload = [{
                asset_id: assetId,
                provider_code: providerCode,
                identifier: providerIdentifier,
                identifier_type: providerIdentifierType,
                provider_params: providerParams,
                fetch_interval: 1440,
                user_url: providerUserUrl || undefined,
            }];
            await zodiosApi.assign_providers_bulk_api_v1_assets_provider_post(assignPayload as any);
        }

        toasts.success($t('assets.modal.saveSuccess', {values: {name: displayName}}));
        open = false;
        onupdated?.();
    }

    // =========================================================================
    // Close
    // =========================================================================

    function handleClose() {
        open = false;
        onclose?.();
    }

    // Asset types
    const ASSET_TYPES = ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'HOLD', 'CROWDFUND_LOAN', 'OTHER'];
</script>

<ModalBase
        {open}
        maxWidth="3xl"
        allowOverflow={true}
        onRequestClose={handleClose}
>
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
        <button type="button" onclick={handleClose}
                class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
            <X size={20}/>
        </button>
    </div>

    <!-- Body -->
    <div class="px-6 py-4 space-y-5 max-h-[70vh] overflow-y-auto">
        <!-- Search Online -->
        <AssetSearchAutocomplete onselect={handleSearchSelect}/>

        <!-- Asset Details -->
        <div class="space-y-3">
            <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                {$t('assets.modal.assetDetails')}
            </div>

            <!-- Display Name -->
            <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    {$t('common.name')} *
                </label>
                <input
                        type="text"
                        bind:value={displayName}
                        placeholder="Apple Inc."
                        class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                               bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                               placeholder-gray-400 dark:placeholder-gray-500
                               focus:outline-none focus:ring-2 focus:ring-libre-green/50 focus:border-libre-green"
                />
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <!-- Asset Type -->
                <div>
                    <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        {$t('assets.type')} *
                    </label>
                    <select
                            bind:value={assetType}
                            class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                   bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                   focus:outline-none focus:ring-2 focus:ring-libre-green/50 focus:border-libre-green"
                    >
                        {#each ASSET_TYPES as at}
                            <option value={at}>{$t(`assets.types.${at}`) || at}</option>
                        {/each}
                    </select>
                </div>

                <!-- Currency -->
                <div>
                    <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        {$t('common.currency')} *
                    </label>
                    <CurrencySearchSelect
                            value={currency}
                            onchange={(v) => { if (v) currency = v; }}
                            maxVisibleItems={6}
                    />
                </div>
            </div>
        </div>

        <!-- Identifiers (collapsible) -->
        <div class="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
            <button
                    type="button"
                    class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-slate-800 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                    onclick={() => { identifiersExpanded = !identifiersExpanded; }}
            >
                <div class="flex items-center gap-2">
                    {#if identifiersExpanded}
                        <ChevronDown size={16}/>
                    {:else}
                        <ChevronRight size={16}/>
                    {/if}
                    <span>{$t('assets.modal.identifiers')}</span>
                </div>
                <!-- Ask Provider button -->
                {#if hasProvider}
                    <button
                            type="button"
                            onclick={(e) => { e.stopPropagation(); handleAskProvider(); }}
                            disabled={askingProvider}
                            class="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md
                                   bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600
                                   text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-600
                                   disabled:opacity-50 transition-colors"
                    >
                        {#if askingProvider}
                            <Loader2 size={12} class="animate-spin"/>
                        {:else}
                            <RefreshCw size={12}/>
                        {/if}
                        <span>{$t('assets.identifiers.askProvider')}</span>
                    </button>
                {/if}
            </button>

            {#if identifiersExpanded}
                <div class="px-4 py-3 space-y-2 border-t border-gray-200 dark:border-slate-700">
                    <div class="grid grid-cols-2 gap-3">
                        <!-- ISIN -->
                        <div>
                            <label class="block text-[10px] font-medium text-gray-400 uppercase mb-0.5">ISIN</label>
                            <div class="relative">
                                <input type="text" bind:value={identifierIsin}
                                       class="w-full px-2.5 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-libre-green/50 {autoFilledFields.has('identifier_isin') ? 'border-green-400' : ''} {conflictFields.has('identifier_isin') ? 'border-amber-400' : ''}"/>
                                {#if autoFilledFields.has('identifier_isin')}
                                    <span class="absolute right-2 top-1/2 -translate-y-1/2 text-green-500 text-xs">✔</span>
                                {/if}
                                {#if conflictFields.has('identifier_isin')}
                                    <span class="absolute right-2 top-1/2 -translate-y-1/2 text-amber-500 text-xs" title="Provider suggests: {conflictFields.get('identifier_isin')}">⚠</span>
                                {/if}
                            </div>
                        </div>
                        <!-- Ticker -->
                        <div>
                            <label class="block text-[10px] font-medium text-gray-400 uppercase mb-0.5">Ticker</label>
                            <div class="relative">
                                <input type="text" bind:value={identifierTicker}
                                       class="w-full px-2.5 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-libre-green/50 {autoFilledFields.has('identifier_ticker') ? 'border-green-400' : ''} {conflictFields.has('identifier_ticker') ? 'border-amber-400' : ''}"/>
                                {#if autoFilledFields.has('identifier_ticker')}
                                    <span class="absolute right-2 top-1/2 -translate-y-1/2 text-green-500 text-xs">✔</span>
                                {/if}
                                {#if conflictFields.has('identifier_ticker')}
                                    <span class="absolute right-2 top-1/2 -translate-y-1/2 text-amber-500 text-xs" title="Provider suggests: {conflictFields.get('identifier_ticker')}">⚠</span>
                                {/if}
                            </div>
                        </div>
                        <!-- CUSIP -->
                        <div>
                            <label class="block text-[10px] font-medium text-gray-400 uppercase mb-0.5">CUSIP</label>
                            <input type="text" bind:value={identifierCusip}
                                   class="w-full px-2.5 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-libre-green/50"/>
                        </div>
                        <!-- SEDOL -->
                        <div>
                            <label class="block text-[10px] font-medium text-gray-400 uppercase mb-0.5">SEDOL</label>
                            <input type="text" bind:value={identifierSedol}
                                   class="w-full px-2.5 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-libre-green/50"/>
                        </div>
                        <!-- FIGI -->
                        <div>
                            <label class="block text-[10px] font-medium text-gray-400 uppercase mb-0.5">FIGI</label>
                            <input type="text" bind:value={identifierFigi}
                                   class="w-full px-2.5 py-1.5 text-sm border border-gray-200 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-libre-green/50"/>
                        </div>
                    </div>
                </div>
            {/if}
        </div>

        <!-- Provider Assignment (collapsible) -->
        <div class="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
            <button
                    type="button"
                    class="w-full flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-slate-800 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                    onclick={() => { providerExpanded = !providerExpanded; }}
            >
                {#if providerExpanded}
                    <ChevronDown size={16}/>
                {:else}
                    <ChevronRight size={16}/>
                {/if}
                <span>{$t('assets.provider.assignment')}</span>
                {#if providerTestStatus === 'passed'}
                    <span class="text-green-500 text-xs ml-1">✅</span>
                {:else if providerTestStatus === 'failed'}
                    <span class="text-red-500 text-xs ml-1">❌</span>
                {:else if providerTestStatus === 'testing'}
                    <Loader2 size={12} class="animate-spin text-gray-400 ml-1"/>
                {/if}
            </button>

            {#if providerExpanded}
                <div class="px-4 py-3 border-t border-gray-200 dark:border-slate-700">
                    <ProviderAssignmentSection
                            bind:providerCode
                            bind:identifier={providerIdentifier}
                            bind:identifierType={providerIdentifierType}
                            bind:providerParams
                            bind:userUrl={providerUserUrl}
                            bind:providerUrl
                            bind:noProvider={providerNoProvider}
                            onchange={(data) => {
                                providerTestStatus = data.testStatus;
                            }}
                    />
                </div>
            {/if}
        </div>

        <!-- Auto-assign info banner -->
        {#if searchResultSelected && hasProvider && !editMode}
            <InfoBanner variant="info">
                <Info size={14} class="shrink-0"/>
                <span>{$t('assets.modal.autoAssignInfo', {values: {provider: providerCode}})}</span>
            </InfoBanner>
        {/if}

        <!-- Error -->
        {#if formError}
            <div class="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-4 py-2 rounded-lg">
                {formError}
            </div>
        {/if}
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-slate-700">
        <button
                type="button"
                onclick={handleClose}
                class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
        >
            {$t('common.cancel')}
        </button>
        <button
                type="button"
                onclick={handleSave}
                disabled={!isValid || saving}
                class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-libre-green rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
            {#if saving}
                <Loader2 size={14} class="animate-spin"/>
            {/if}
            <span>{editMode ? $t('assets.modal.saveChanges') : $t('assets.modal.createAsset')}</span>
        </button>
    </div>
</ModalBase>

<!-- Confirmation: Save without test -->
<ConfirmModal
        open={showSaveWithoutTestConfirm}
        title={$t('assets.confirm.saveWithoutTest')}
        message={$t('assets.confirm.saveWithoutTestMessage')}
        confirmText={$t('assets.confirm.saveAnyway')}
        warning={true}
        onConfirm={() => doSave()}
        onCancel={() => { showSaveWithoutTestConfirm = false; }}
        zIndex={70}
/>

<!-- Confirmation: Identifier change in edit mode -->
<ConfirmModal
        open={showIdentifierChangeConfirm}
        title={$t('assets.confirm.identifierChanged')}
        message={$t('assets.confirm.identifierChangedMessage')}
        confirmText={$t('assets.confirm.confirmChange')}
        warning={true}
        onConfirm={() => {
            showIdentifierChangeConfirm = false;
            if (pendingSearchResult) applySearchResult(pendingSearchResult);
            pendingSearchResult = null;
        }}
        onCancel={() => { showIdentifierChangeConfirm = false; pendingSearchResult = null; }}
        zIndex={70}
/>

