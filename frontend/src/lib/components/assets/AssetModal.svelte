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
    import {untrack} from 'svelte';
    import {zodiosApi} from '$lib/api';
    import {ChevronDown, ChevronRight, ExternalLink, Loader2, Minus, Plus, RefreshCw, Trash2, Upload, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {CurrencySearchSelect, SimpleSelect} from '$lib/components/ui/select';
    import AssetSearchAutocomplete from './AssetSearchAutocomplete.svelte';
    import AssetIcon from './AssetIcon.svelte';
    import ProviderAssignmentSection from './ProviderAssignmentSection.svelte';
    import ProviderComparisonModal from './ProviderComparisonModal.svelte';
    import type {DiffItem} from './ProviderComparisonModal.svelte';
    import AssetCurrencyChangeModal from './AssetCurrencyChangeModal.svelte';
    import DistributionEditor from '$lib/components/ui/input/DistributionEditor.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import type {ColumnDef as DTColumnDef, RowAction as DTRowAction} from '$lib/components/table/types';
    import ImagePickerWrapper from '$lib/components/ui/media/ImagePickerWrapper.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import {trySave} from '$lib/utils/trySave';
    import {ASSET_TYPES, IDENTIFIER_TYPES, buildAssetTypeOptions} from '$lib/utils/assetTypes';
    import {generateUUID} from '$lib/utils/uuid';
    import {ensureAssetProvidersCached, isParametricProvider} from '$lib/utils/providerHelpers';
    import {mergeAssets, invalidateAfterMutation} from '$lib/stores/assetStore';

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
        classification_params?: {
            short_description?: string | null;
            sector_area?: {distribution: Record<string, number>} | null;
            geographic_area?: {distribution: Record<string, number>} | null;
        } | null;
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
        /** Z-index override for stacked modal contexts. */
        zIndex?: number;
        oncreated?: (assetId: number) => void;
        onupdated?: () => void;
        onclose?: () => void;
    }

    let {open = $bindable(false), editMode = false, editData = null, zIndex = 50, oncreated, onupdated, onclose}: Props = $props();

    // =========================================================================
    // Constants
    // =========================================================================

    // Asset types and icon mapping are imported from $lib/utils/assetTypes

    // =========================================================================
    // State — Form fields
    // =========================================================================

    let displayName = $state('');
    let currency = $state('USD');
    let assetType = $state('STOCK');
    let iconUrl = $state<string | null>(null);

    // Identifiers — dynamic rows instead of fixed fields
    interface IdentifierRow {
        id: string;
        type: string;
        value: string;
        autoFilled?: boolean;
    }
    let identifierRows = $state<IdentifierRow[]>([]);

    // Classification
    let shortDescription = $state('');
    let sectorDistribution = $state<Record<string, number>>({});
    let geographicDistribution = $state<Record<string, number>>({});

    // Provider
    let providerCode = $state('');
    let providerIdentifier = $state('');
    let providerIdentifierType = $state('TICKER');
    let providerParams = $state<Record<string, any> | null>(null);
    let providerUserUrl = $state('');
    let providerUrl = $state<string | null>(null);
    let providerNoProvider = $state(false);
    let providerTestStatus = $state<'not_tested' | 'testing' | 'passed' | 'failed'>('not_tested');
    let fetchInterval = $state(1440);

    // UI state
    let moreInfoExpanded = $state(false);
    let providerExpanded = $state(false);
    let saving = $state(false);
    let formError = $state<string | null>(null);
    let askingProvider = $state(false);
    let autoFilledFields = $state<Set<string>>(new Set());
    let conflictFields = $state<Map<string, string>>(new Map());

    // Confirmation modals
    let showSaveWithoutTestConfirm = $state(false);
    let showIdentifierChangeConfirm = $state(false);
    let showDiscardConfirm = $state(false);

    // #R3-4 — scheduled_investment regenerate confirm. Shown when the user edits an
    // existing scheduled_investment asset and changes its provider_params (schedule /
    // maturation_frequency / …). Confirming wipes the old prices server-side and
    // triggers an immediate re-sync so the chart reflects the new schedule.
    let showScheduledRegenConfirm = $state(false);
    let pendingSaveAssetId = $state<number | null>(null);
    let initialProviderParamsJson = $state<string>('');

    // I-bis #2 — snapshot of the provider config as loaded from the DB.
    // Used by the ``providerDirty`` derived below to gate the
    // "Save Without Testing?" modal: it must fire **only** when one of
    // these four fields changed vs what was loaded. Non-provider edits
    // (name, description, classification, etc.) skip the modal entirely.
    let initialProviderCode = $state<string>('');
    let initialProviderIdentifier = $state<string>('');
    let initialProviderIdentifierType = $state<string>('TICKER');

    // I.6 — destructive currency-change modal state.
    let currencyChangeModalOpen = $state(false);
    let currencyChangeBlocker = $state<{
        assetId: number;
        prices: number;
        eventsManual: number;
        eventsProvider: number;
        linkedTx: number;
        oldest: string;
        newest: string;
        from: string;
        to: string;
    } | null>(null);
    let currencyChangePatchPayload = $state<Record<string, unknown> | null>(null);
    let currencyChangeProviderAssigned = $state(false);
    let pendingSearchResult = $state<any>(null);

    // Provider comparison modal
    let showComparisonModal = $state(false);
    let comparisonDifferences = $state<DiffItem[]>([]);

    // Image picker
    let showImagePicker = $state(false);

    // Identifier selection + bulk delete
    let identifierSelectedIds = $state<string[]>([]);
    let showIdentifierDeleteConfirm = $state(false);
    let pendingIdentifierDeleteIds = $state<string[]>([]);

    // Track if search result was selected (for auto-assign banner)
    let searchResultSelected = $state(false);

    // Dirty tracking — snapshot of initial form to detect unsaved changes
    let initialSnapshot = $state('');

    // Duplicate name detection
    let duplicateAssetName = $state<string | null>(null);

    // =========================================================================
    // Derived
    // =========================================================================

    let isValid = $derived(displayName.trim().length > 0);
    let hasProvider = $derived(!providerNoProvider && providerCode !== '' && (providerIdentifier !== '' || providerIdentifierType === 'AUTO_GENERATED'));

    // I-bis #2 — dirty detection for the provider block.
    //
    // Previous behaviour: the "Save Without Testing?" modal fired on every
    // save whenever a provider was configured, even if the user only
    // touched a non-provider field (name, description, classification…).
    //
    // New behaviour: the modal fires only when any of the four provider
    // fields (code / identifier / identifier_type / params) changed
    // compared to the snapshot taken at load time. In **create mode**
    // (editMode === false) there is no snapshot, so any provider
    // configured means "dirty" by definition.
    let providerDirty = $derived(!editMode ? hasProvider : providerCode !== initialProviderCode || providerIdentifier !== initialProviderIdentifier || providerIdentifierType !== initialProviderIdentifierType || JSON.stringify(providerParams ?? null) !== (initialProviderParamsJson || 'null'));
    let title = $derived(editMode ? $t('assets.modal.titleEdit') : $t('assets.modal.title'));

    /** Asset type options for SimpleSelect (with PNG icons) */
    let assetTypeOptions = $derived(buildAssetTypeOptions($t));

    /** Build form snapshot for dirty tracking — single source of truth */
    function buildFormSnapshot(): string {
        return JSON.stringify([
            displayName,
            currency,
            assetType,
            iconUrl,
            JSON.stringify(identifierRows.map((r) => [r.type, r.value])),
            shortDescription,
            JSON.stringify(sectorDistribution),
            JSON.stringify(geographicDistribution),
            providerCode,
            providerIdentifier,
            providerIdentifierType,
            providerNoProvider,
            fetchInterval,
        ]);
    }

    /** Current form fingerprint for dirty detection */
    let currentSnapshot = $derived(buildFormSnapshot());
    let isDirty = $derived(initialSnapshot !== '' && currentSnapshot !== initialSnapshot);

    // =========================================================================
    // Helpers — Identifier rows ↔ DB columns conversion
    // =========================================================================

    function columnsToIdentifierRows(data: AssetData): IdentifierRow[] {
        const rows: IdentifierRow[] = [];
        for (const idType of IDENTIFIER_TYPES) {
            const key = `identifier_${idType.toLowerCase()}` as keyof AssetData;
            const value = (data[key] as string) ?? '';
            if (value) rows.push({id: generateUUID(), type: idType, value});
        }
        return rows;
    }

    function identifierRowsToColumns(rows: IdentifierRow[]): Record<string, string | undefined> {
        const result: Record<string, string | undefined> = {};
        for (const idType of IDENTIFIER_TYPES) {
            result[`identifier_${idType.toLowerCase()}`] = undefined;
        }
        for (const row of rows) {
            if (!row.value.trim()) continue;
            result[`identifier_${row.type.toLowerCase()}`] = row.value.trim();
        }
        return result;
    }

    function addIdentifierRow() {
        // Find first unused type
        const usedTypes = new Set(identifierRows.map((r) => r.type));
        const availableType = IDENTIFIER_TYPES.find((t) => !usedTypes.has(t)) ?? 'TICKER';
        identifierRows = [...identifierRows, {id: generateUUID(), type: availableType, value: ''}];
    }

    function updateIdentifierRow(id: string, field: 'type' | 'value', val: string) {
        identifierRows = identifierRows.map((r) => (r.id === id ? {...r, [field]: val} : r));
    }

    function removeIdentifierRow(id: string) {
        identifierRows = identifierRows.filter((r) => r.id !== id);
    }

    /** Handle image picker change — empty string means remove */
    function handleImagePickerChange(url: string) {
        iconUrl = url || null;
        showImagePicker = false;
    }

    /** Bulk delete identifiers with confirmation */
    function handleIdentifierBulkDelete() {
        pendingIdentifierDeleteIds = [...identifierSelectedIds];
        showIdentifierDeleteConfirm = true;
    }

    function confirmIdentifierBulkDelete() {
        const deleteSet = new Set(pendingIdentifierDeleteIds);
        identifierRows = identifierRows.filter((r) => !deleteSet.has(r.id));
        identifierSelectedIds = [];
        pendingIdentifierDeleteIds = [];
        showIdentifierDeleteConfirm = false;
    }

    /** Get identifier value by type from rows */
    function getIdentifierByType(type: string): string {
        return identifierRows.find((r) => r.type === type)?.value ?? '';
    }

    // =========================================================================
    // Identifier DataTable columns
    // =========================================================================

    let idTypeOptions = $derived(IDENTIFIER_TYPES.map((t) => ({value: t, label: t})));

    let identifierColumns = $derived.by<DTColumnDef<IdentifierRow>[]>(() => [
        {
            id: 'type',
            header: () => $t('assets.provider.identifierType'),
            type: 'custom' as const,
            cell: (row: IdentifierRow) => ({
                type: 'editable-select' as const,
                value: row.type,
                options: idTypeOptions,
                onchange: (newVal: string) => updateIdentifierRow(row.id, 'type', newVal),
            }),
            sortable: false,
            filterable: false,
            width: 110,
        },
        {
            id: 'value',
            header: () => $t('assets.provider.identifier'),
            type: 'custom' as const,
            cell: (row: IdentifierRow) => ({
                type: 'editable-text' as const,
                value: row.value,
                placeholder: 'US0378331005, AAPL, ...',
                onchange: (newVal: string) => updateIdentifierRow(row.id, 'value', newVal),
            }),
            sortable: false,
            filterable: false,
            width: 250,
        },
    ]);

    let identifierRowActions = $derived<DTRowAction<IdentifierRow>[]>([
        {
            id: 'delete',
            icon: X,
            label: 'Remove',
            variant: 'danger',
            onClick: (row) => removeIdentifierRow(row.id),
        },
    ]);

    // =========================================================================
    // Lifecycle — Populate in edit mode
    // =========================================================================

    $effect(() => {
        if (open) {
            // untrack: only `open` should trigger this effect.
            // populateFromEditData reads $state vars it just wrote (e.g. identifierRows.length)
            // which would create a dependency loop → effect_update_depth_exceeded.
            untrack(() => {
                if (editMode && editData) {
                    populateFromEditData(editData);
                } else {
                    resetForm();
                }
            });
        }
    });

    function populateFromEditData(data: AssetData) {
        displayName = data.display_name;
        currency = data.currency;
        assetType = data.asset_type ?? 'STOCK';
        iconUrl = data.icon_url ?? null;
        identifierRows = columnsToIdentifierRows(data);
        // Classification
        const cp = data.classification_params;
        shortDescription = cp?.short_description ?? '';
        sectorDistribution = cp?.sector_area?.distribution ?? {};
        geographicDistribution = cp?.geographic_area?.distribution ?? {};
        // Provider
        providerCode = data.provider_code ?? '';
        providerIdentifier = data.provider_identifier ?? '';
        providerIdentifierType = data.provider_identifier_type ?? 'TICKER';
        providerParams = data.provider_params ?? null;
        providerUserUrl = data.provider_user_url ?? '';
        providerUrl = data.provider_url ?? null;
        providerNoProvider = !data.provider_code;
        fetchInterval = (data as any).fetch_interval ?? 1440;
        // #R3-4 — snapshot initial params to detect scheduled_investment changes at save.
        initialProviderParamsJson = providerParams ? JSON.stringify(providerParams) : '';
        // I-bis #2 — snapshot the other three provider fields too so
        // ``providerDirty`` can detect any user edit and gate the
        // "Save Without Testing?" modal accordingly.
        initialProviderCode = providerCode;
        initialProviderIdentifier = providerIdentifier;
        initialProviderIdentifierType = providerIdentifierType;
        moreInfoExpanded = identifierRows.length > 0;
        providerExpanded = !!data.provider_code;
        searchResultSelected = false;
        autoFilledFields = new Set();
        conflictFields = new Map();
        formError = null;
        providerTestStatus = 'not_tested';
        showComparisonModal = false;
        comparisonDifferences = [];
        duplicateAssetName = null;
        setTimeout(() => {
            initialSnapshot = buildFormSnapshot();
        }, 0);
    }

    function resetForm() {
        displayName = '';
        currency = 'USD';
        assetType = 'STOCK';
        iconUrl = null;
        identifierRows = [];
        shortDescription = '';
        sectorDistribution = {};
        geographicDistribution = {};
        providerCode = '';
        providerIdentifier = '';
        providerIdentifierType = 'TICKER';
        providerParams = null;
        providerUserUrl = '';
        providerUrl = null;
        providerNoProvider = false;
        fetchInterval = 1440;
        moreInfoExpanded = false;
        providerExpanded = false;
        searchResultSelected = false;
        autoFilledFields = new Set();
        conflictFields = new Map();
        formError = null;
        saving = false;
        providerTestStatus = 'not_tested';
        showComparisonModal = false;
        comparisonDifferences = [];
        duplicateAssetName = null;
        setTimeout(() => {
            initialSnapshot = buildFormSnapshot();
        }, 0);
    }

    // =========================================================================
    // Duplicate name detection (debounced)
    // =========================================================================

    $effect(() => {
        const name = displayName.trim();
        if (name.length < 2) {
            duplicateAssetName = null;
            return;
        }
        const timer = setTimeout(async () => {
            try {
                const response = await zodiosApi.list_assets_api_v1_assets_query_get({
                    queries: {},
                });
                const items = response as any[];
                const match = items.find((a: any) => {
                    if (editMode && editData?.id === a.id) return false;
                    return a.display_name.toLowerCase() === name.toLowerCase();
                });
                duplicateAssetName = match ? match.display_name : null;
            } catch {
                duplicateAssetName = null;
            }
        }, 400);
        return () => clearTimeout(timer);
    });

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
        if (result.asset_type) assetType = (ASSET_TYPES as readonly string[]).includes(result.asset_type.toUpperCase()) ? result.asset_type.toUpperCase() : 'OTHER';
        if (result.currency) currency = result.currency;

        // Auto-fill identifier based on identifier_type
        const idType = (result.identifier_type ?? '').toUpperCase();
        if (idType && result.identifier) {
            // Add or update the identifier row
            const existing = identifierRows.find((r) => r.type === idType);
            if (existing) {
                identifierRows = identifierRows.map((r) => (r.type === idType ? {...r, value: result.identifier} : r));
            } else {
                identifierRows = [...identifierRows, {id: generateUUID(), type: idType, value: result.identifier}];
            }
        }

        // Auto-fill provider
        providerCode = result.provider_code;
        providerIdentifier = result.identifier;
        providerIdentifierType = result.identifier_type;
        providerUrl = result.provider_url ?? null;
        providerNoProvider = false;
        // Carry over provider_params from search result (e.g. language, currency).
        // Provider-supplied params take priority; currency is added as fallback
        // only when the provider didn't already include it.
        const searchParams: Record<string, any> = {...(result.provider_params ?? {})};
        if (result.currency && !('currency' in searchParams)) {
            searchParams.currency = result.currency;
        }
        providerParams = Object.keys(searchParams).length > 0 ? searchParams : null;

        // Expand sections
        moreInfoExpanded = true;
        providerExpanded = true;
        searchResultSelected = true;
        formError = null;

        // Auto-trigger test + metadata fetch (global ask provider)
        autoTriggerProbe();
        handleAskProvider();
    }

    async function autoTriggerProbe() {
        providerTestStatus = 'testing';
        // Let ProviderAssignmentSection handle the actual test
        // We just need to trigger it — the section's testConfiguration method runs
        // via $effect watching testStatus. Instead, call the probe directly.
        try {
            const response = (await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post({
                provider_code: providerCode,
                identifier: providerIdentifier,
                identifier_type: providerIdentifierType as any,
                provider_params: providerParams,
                operations: ['current_price', 'history'],
            })) as any;

            const cp = response.current_price;
            const h = response.history;
            const allSuccess = (cp?.success ?? false) && h?.success !== false;
            providerTestStatus = allSuccess ? 'passed' : 'failed';

            if (response.provider_url) providerUrl = response.provider_url;
        } catch {
            providerTestStatus = 'failed';
        }
    }

    // =========================================================================
    // Ask Provider (metadata) — unified fetch + compare logic (C1+C2 refactoring)
    // =========================================================================

    /** Helper: field name like 'identifier_ticker' → type 'TICKER' */
    function fieldToIdType(field: string): string {
        return field.replace('identifier_', '').toUpperCase();
    }

    /** Set or update an identifier row by type */
    function setIdentifierByType(type: string, val: string) {
        const existing = identifierRows.find((r) => r.type === type);
        if (existing) {
            identifierRows = identifierRows.map((r) => (r.type === type ? {...r, value: val, autoFilled: true} : r));
        } else {
            identifierRows = [...identifierRows, {id: generateUUID(), type, value: val, autoFilled: true}];
        }
    }

    /**
     * Unified metadata fetch + comparison logic.
     * Used by: handleAskProvider() [global], handleAskProviderSection() [per-section],
     *          and applySearchResult() [auto after search].
     *
     * @param scope Which fields to compare. 'all' = everything, others = section-specific.
     */
    async function fetchAndCompareMetadata(scope: 'all' | 'identifiers' | 'sector' | 'geographic') {
        if (!providerCode || !providerIdentifier) return;
        askingProvider = true;
        autoFilledFields = new Set();

        try {
            const response = (await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post({
                provider_code: providerCode,
                identifier: providerIdentifier,
                identifier_type: providerIdentifierType as any,
                provider_params: providerParams,
                operations: ['metadata'],
            })) as any;

            const meta = response.metadata;
            if (!meta?.success || !meta.patch_data) {
                toasts.info($t('assets.identifiers.askProviderHint') + ' — no data from provider');
                return;
            }
            const pd = meta.patch_data;
            const differences: DiffItem[] = [];
            const missingFields: string[] = [];

            // --- Helper: compare a string field — auto-fill if empty, diff if different ---
            function compareStringField(field: string, label: string, currentVal: string, providerVal: string | null | undefined) {
                if (!providerVal) return;
                if (!currentVal) {
                    setFieldValue(field, providerVal);
                    autoFilledFields = new Set([...autoFilledFields, field]);
                } else if (currentVal === providerVal) {
                    autoFilledFields = new Set([...autoFilledFields, field]);
                } else {
                    differences.push({field, label, type: 'string', currentValue: currentVal, providerValue: providerVal, selected: true});
                }
            }

            // --- Helper: compare a distribution — auto-fill if empty, diff if different ---
            function compareDistribution(field: string, label: string, currentDist: Record<string, number>, providerDist: Record<string, number>) {
                const hasCurrent = Object.keys(currentDist).length > 0;
                if (!hasCurrent) {
                    if (field === 'sector_area') sectorDistribution = providerDist;
                    else geographicDistribution = providerDist;
                    autoFilledFields = new Set([...autoFilledFields, field]);
                } else if (JSON.stringify(currentDist) !== JSON.stringify(providerDist)) {
                    differences.push({field, label, type: 'distribution', currentValue: currentDist, providerValue: providerDist, selected: true});
                } else {
                    autoFilledFields = new Set([...autoFilledFields, field]);
                }
            }

            // --- IDENTIFIERS (scope 'all' or 'identifiers') ---
            if (scope === 'all' || scope === 'identifiers') {
                for (const idType of IDENTIFIER_TYPES) {
                    const dbKey = `identifier_${idType.toLowerCase()}`;
                    const provVal = pd[dbKey];
                    if (provVal) {
                        const currentVal = getIdentifierByType(idType);
                        compareStringField(dbKey, idType, currentVal, provVal);
                    }
                }
            }

            // --- ASSET DETAILS (scope 'all' only) ---
            if (scope === 'all') {
                compareStringField('display_name', $t('common.name'), displayName, pd.display_name);
                compareStringField('asset_type', $t('assets.type'), assetType, pd.asset_type);
                compareStringField('currency', $t('common.currency'), currency, pd.currency);
            }

            // --- CLASSIFICATION: description, sector, geographic ---
            const cpData = pd.classification_params;

            if (scope === 'all') {
                if (cpData?.short_description) {
                    compareStringField('short_description', 'Description', shortDescription, cpData.short_description);
                }
            }

            if (scope === 'all' || scope === 'sector') {
                if (cpData?.sector_area) {
                    const provDist = cpData.sector_area.distribution ?? cpData.sector_area;
                    compareDistribution('sector_area', $t('common.sectorDistribution'), sectorDistribution, provDist);
                } else {
                    missingFields.push($t('common.sectorDistribution'));
                }
            }

            if (scope === 'all' || scope === 'geographic') {
                if (cpData?.geographic_area) {
                    const provDist = cpData.geographic_area.distribution ?? cpData.geographic_area;
                    compareDistribution('geographic_area', $t('common.geoDistribution'), geographicDistribution, provDist);
                } else {
                    missingFields.push($t('common.geoDistribution'));
                }
            }

            // --- RESULTS: consistent toast logic (Fix 3) ---
            if (missingFields.length > 0) {
                toasts.info($t('assets.comparison.noDistributionData', {values: {fields: missingFields.join(', ')}}));
            }

            if (differences.length > 0) {
                comparisonDifferences = differences;
                showComparisonModal = true;
            } else if (missingFields.length === 0) {
                // Only show success if nothing was missing — never both info + success
                toasts.success($t('assets.comparison.allMatch'));
            }
        } catch (e: any) {
            console.error(`Ask Provider (${scope}) failed:`, e);
        } finally {
            askingProvider = false;
        }
    }

    /** Global "Ask Provider" — compares all fields */
    function handleAskProvider() {
        fetchAndCompareMetadata('all');
    }

    /** Per-section "Ask Provider" — compares only the given section */
    function handleAskProviderSection(section: 'identifiers' | 'sector' | 'geographic') {
        fetchAndCompareMetadata(section);
    }

    /** Generic setter used by comparison logic */
    function setFieldValue(field: string, value: string) {
        if (field.startsWith('identifier_')) {
            const idType = fieldToIdType(field);
            setIdentifierByType(idType, value);
        } else {
            switch (field) {
                case 'display_name':
                    displayName = value;
                    break;
                case 'asset_type':
                    assetType = value;
                    break;
                case 'currency':
                    currency = value;
                    break;
                case 'short_description':
                    shortDescription = value;
                    break;
            }
        }
    }

    /** Apply selected fields from ProviderComparisonModal */
    function handleComparisonApply(selectedFields: string[]) {
        for (const diff of comparisonDifferences) {
            if (selectedFields.includes(diff.field)) {
                if (diff.type === 'string') {
                    setFieldValue(diff.field, diff.providerValue);
                } else if (diff.type === 'distribution') {
                    if (diff.field === 'sector_area') {
                        sectorDistribution = diff.providerValue?.distribution ?? diff.providerValue;
                    } else if (diff.field === 'geographic_area') {
                        geographicDistribution = diff.providerValue?.distribution ?? diff.providerValue;
                    }
                }
                autoFilledFields = new Set([...autoFilledFields, diff.field]);
            }
        }
        showComparisonModal = false;
    }

    // =========================================================================
    // Save
    // =========================================================================

    function handleSave() {
        if (!isValid) return;
        // I-bis #2 — retest 1.3 follow-up: when the user changes the provider
        // dropdown, ``ProviderAssignmentSection.handleProviderChange`` clears
        // the identifier on purpose (different providers use different ID
        // formats). As a result ``hasProvider`` becomes ``false`` →
        // (a) the "Save Without Testing?" gate below would NOT fire, and
        // (b) ``saveEdit``'s provider step would silently skip both the
        //     remove and the assign branch, so the provider change would
        //     be thrown away without any feedback.
        // Surface an explicit form error so the user completes the provider
        // block (or ticks "No provider") before saving.
        if (editMode && providerDirty && !providerNoProvider && providerCode !== '' && !hasProvider) {
            formError = $t('assets.modal.providerIncomplete');
            setTimeout(() => {
                document.querySelector('[data-form-error]')?.scrollIntoView({behavior: 'smooth', block: 'center'});
            }, 50);
            return;
        }
        // I-bis #2 — only gate on the "Save Without Testing?" modal when
        // the provider block has actually been touched. Before, the modal
        // fired on every save with a configured provider, even if the
        // user only edited non-provider metadata (name, description,
        // classification…).
        if (hasProvider && providerDirty && providerTestStatus !== 'passed') {
            showSaveWithoutTestConfirm = true;
            return;
        }
        doSave();
    }

    async function doSave() {
        saving = true;
        formError = null;
        showSaveWithoutTestConfirm = false;

        // I-bis #22 (Batch 4.d-part2) — route the orchestrator through
        // ``trySave`` for uniform error extraction. Two custom
        // semantics are preserved:
        //   (a) **409 currency-change** is NOT handled here: it's intercepted
        //       deeper in ``saveEdit`` (see the patch_assets_bulk try/catch
        //       around the PATCH call) which rewrites the ``patchResp`` from
        //       ``detail.results[]`` and opens the destructive
        //       ``AssetCurrencyChangeModal``. That path never throws to us.
        //   (b) **409 duplicate-name** (create path) still maps to the
        //       dedicated ``duplicateName`` i18n key via the ``onError``
        //       hook below.
        // ``toast: false`` because the error is rendered inline via the
        // ``data-form-error`` banner (the existing UX).
        const result = await trySave(() => (editMode && editData?.id ? saveEdit(editData.id) : saveCreate()), {
            toast: false,
            fallback: $t('assets.modal.saveFailed'),
            onError: (err: any) => {
                if (err?.response?.status === 409) {
                    formError = $t('assets.modal.duplicateName');
                    return true;
                }
                return false;
            },
        });

        if (result.status === 'error' && !formError) {
            formError = result.message;
        }
        if (result.status === 'error') {
            // Scroll error into view (same behavior as the previous try/catch)
            setTimeout(() => {
                document.querySelector('[data-form-error]')?.scrollIntoView({behavior: 'smooth', block: 'center'});
            }, 50);
        }
        saving = false;
    }

    async function saveCreate() {
        // Build classification_params if any fields are set
        const classificationParams: any = {};
        if (shortDescription) classificationParams.short_description = shortDescription;
        if (Object.keys(sectorDistribution).length > 0) classificationParams.sector_area = {distribution: sectorDistribution};
        if (Object.keys(geographicDistribution).length > 0) classificationParams.geographic_area = {distribution: geographicDistribution};

        // Step 1: Create asset
        const createPayload = [
            {
                display_name: displayName.trim(),
                currency: currency,
                asset_type: assetType,
                icon_url: iconUrl || undefined,
                classification_params: Object.keys(classificationParams).length > 0 ? classificationParams : undefined,
                ...identifierRowsToColumns(identifierRows),
            },
        ];

        const createResp = (await zodiosApi.create_assets_bulk_api_v1_assets_post(createPayload as any)) as any;
        const result = createResp?.results?.[0];
        if (!result?.success) {
            throw new Error(result?.message || 'Failed to create asset');
        }
        const assetId = result.asset_id;

        // Upsert the new asset into the shared cache so other pages
        // (transactions cell, AssetCard, LiveTicker, …) reflect the entry
        // immediately. The BE response only carries `asset_id`; we merge the
        // fields the FE just submitted (no extra round-trip).
        mergeAssets([{id: assetId, ...(createPayload[0] as Record<string, unknown>)}]);

        // Step 2: Assign provider (separate try/catch — asset already created)
        // Skip assignment for scheduled_investment if no schedule is configured yet
        const skipProviderAssignment = providerCode === 'scheduled_investment' && (!providerParams || !providerParams.schedule?.length);
        if (hasProvider && !skipProviderAssignment) {
            try {
                const assignPayload = [
                    {
                        asset_id: assetId,
                        provider_code: providerCode,
                        identifier: providerIdentifier,
                        identifier_type: providerIdentifierType,
                        provider_params: providerParams,
                        fetch_interval: fetchInterval,
                    },
                ];
                await zodiosApi.assign_providers_bulk_api_v1_assets_provider_post(assignPayload as any);
            } catch (assignErr: any) {
                console.error('Provider assignment failed after asset creation:', assignErr);
                toasts.warning($t('assets.modal.createSuccessProviderFailed', {values: {name: displayName}}));
                open = false;
                oncreated?.(assetId);
                return;
            }
        }

        toasts.success($t('assets.modal.createSuccess', {values: {name: displayName}}));
        open = false;
        oncreated?.(assetId);
    }

    async function saveEdit(assetId: number) {
        // #R3-4 — for PARAMETRIC_GENERATION providers (e.g. scheduled_investment), if the
        // user changed `provider_params` intercept the save flow to show an explicit
        // regenerate confirmation. Confirming will: (1) PATCH/assign through the normal
        // path, (2) BE wipes old prices + invalidates caches atomically, (3) we trigger
        // an immediate re-sync so the chart reflects the new schedule without requiring
        // a manual click. Gating on `isParametricProvider()` (kind-based) instead of
        // hardcoding 'scheduled_investment' so future parametric providers inherit the
        // flow for free.
        await ensureAssetProvidersCached();
        if (isParametricProvider(providerCode) && !providerNoProvider && initialProviderParamsJson && JSON.stringify(providerParams ?? null) !== initialProviderParamsJson && !pendingSaveAssetId) {
            pendingSaveAssetId = assetId;
            showScheduledRegenConfirm = true;
            return; // wait for confirm; the modal will re-invoke saveEdit()
        }

        // Build classification_params
        const classificationParams: any = {};
        if (shortDescription) classificationParams.short_description = shortDescription;
        if (Object.keys(sectorDistribution).length > 0) classificationParams.sector_area = {distribution: sectorDistribution};
        if (Object.keys(geographicDistribution).length > 0) classificationParams.geographic_area = {distribution: geographicDistribution};

        // Step 1: Patch asset
        const idCols = identifierRowsToColumns(identifierRows);
        const patchItem = {
            asset_id: assetId,
            display_name: displayName.trim(),
            currency: currency,
            asset_type: assetType,
            icon_url: iconUrl,
            user_url: providerUserUrl || null,
            classification_params: Object.keys(classificationParams).length > 0 ? classificationParams : null,
            identifier_isin: idCols.identifier_isin || null,
            identifier_ticker: idCols.identifier_ticker || null,
            identifier_cusip: idCols.identifier_cusip || null,
            identifier_sedol: idCols.identifier_sedol || null,
            identifier_figi: idCols.identifier_figi || null,
            identifier_uuid: idCols.identifier_uuid || null,
            identifier_other: idCols.identifier_other || null,
        };
        const patchPayload = [patchItem];

        // I.3 + R3-3 Policy D — PATCH returns a per-item failure with the structured
        // blocker token when the user changed the currency on an asset that still has
        // *any* market data (prices, events or linked transactions). Token format:
        //   CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|prices=N|events_manual=M|
        //     events_provider=K|linked_tx=L|oldest=...|newest=...|from=X|to=Y
        // The modal turns this into the destructive-confirm dialog.
        //
        // I-bis #7 — the backend now also returns HTTP 409 when *every* item in
        // the batch is blocked by market data (single-asset edits always fall in
        // this case). Axios throws on non-2xx; we catch below and re-extract the
        // ``results[]`` from the response body so the UX is identical.
        let patchResp: any;
        try {
            patchResp = await zodiosApi.patch_assets_bulk_api_v1_assets_patch(patchPayload as any);
        } catch (err: any) {
            const status = err?.response?.status;
            const detail = err?.response?.data?.detail;
            if (status === 409 && detail && typeof detail === 'object' && Array.isArray(detail.results)) {
                patchResp = {results: detail.results, success_count: 0};
            } else {
                throw err;
            }
        }
        const resultItem = patchResp?.results?.[0];
        if (resultItem && resultItem.success === false && typeof resultItem.message === 'string' && resultItem.message.startsWith('CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|')) {
            const parsed: Record<string, string> = {};
            for (const chunk of resultItem.message.split('|').slice(1)) {
                const [k, v] = chunk.split('=');
                if (k && v !== undefined) parsed[k] = v;
            }
            currencyChangeBlocker = {
                assetId,
                prices: parseInt(parsed.prices || '0', 10),
                eventsManual: parseInt(parsed.events_manual || '0', 10),
                eventsProvider: parseInt(parsed.events_provider || '0', 10),
                linkedTx: parseInt(parsed.linked_tx || '0', 10),
                oldest: parsed.oldest || '',
                newest: parsed.newest || '',
                from: parsed.from || '',
                to: parsed.to || '',
            };
            currencyChangePatchPayload = patchItem;
            currencyChangeProviderAssigned = hasProvider && !providerNoProvider;
            currencyChangeModalOpen = true;
            return; // abort save — the modal will either finish the flow or the user cancels
        }

        // PATCH succeeded — sync the patched fields into the shared cache so
        // every consumer (transactions cell, AssetCard, LiveTicker, …) sees
        // the new icon/name/etc. without a manual reload. The BE response
        // only carries `{success, asset_id, message}`; we merge the fields
        // the FE just submitted.
        mergeAssets([{id: assetId, ...(patchItem as unknown as Record<string, unknown>)}]);

        // Step 2: Handle provider change
        if (providerNoProvider) {
            // Remove provider
            await zodiosApi.remove_providers_bulk_api_v1_assets_provider_delete(undefined, {
                queries: {asset_ids: [assetId]},
            });
        } else if (hasProvider) {
            const assignPayload = [
                {
                    asset_id: assetId,
                    provider_code: providerCode,
                    identifier: providerIdentifier,
                    identifier_type: providerIdentifierType,
                    provider_params: providerParams,
                    fetch_interval: fetchInterval,
                },
            ];
            await zodiosApi.assign_providers_bulk_api_v1_assets_provider_post(assignPayload as any);
        }

        // #R3-4 — after a confirmed scheduled_investment regenerate, trigger an
        // immediate sync so the prices are regenerated with the new params and
        // the chart refreshes on close.
        //
        // #R6-5 (2026-04-24, retest Batch 4) — extended to cover non-parametric
        // provider changes too. Scenario 1.3: user changes provider Yahoo →
        // JustETF with a valid identifier. Without this auto-sync, the page
        // reloads after save but the chart keeps showing the OLD prices (from
        // Yahoo) because nothing regenerated the series. The user perceived
        // this as "no reload happened" and had to F5 manually. Now, any
        // change to ``providerCode``, ``providerIdentifier`` or
        // ``providerIdentifierType`` triggers an opportunistic sync so the
        // new provider fetches fresh data on close. ``providerDirty`` already
        // covers all four fields including ``providerParams``.
        const didRegenerate = pendingSaveAssetId === assetId;
        pendingSaveAssetId = null;
        const providerChanged = providerDirty && !providerNoProvider && hasProvider;
        const shouldAutoSync = (didRegenerate && isParametricProvider(providerCode)) || providerChanged;
        if (shouldAutoSync && !providerNoProvider) {
            try {
                const today = new Date();
                const end = today.toISOString().slice(0, 10);
                const startD = new Date(today);
                startD.setFullYear(startD.getFullYear() - 5);
                const start = startD.toISOString().slice(0, 10);
                await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([{asset_id: assetId, date_range: {start, end}} as any]);
            } catch (syncErr) {
                console.warn('Post-save auto-sync failed (non-blocking):', syncErr);
                // Non-blocking: the user can manually re-sync if needed.
            }
        }

        toasts.success($t('assets.modal.saveSuccess', {values: {name: displayName}}));
        open = false;
        onupdated?.();
    }

    /**
     * Currency-change wipe-confirm flow: triggered when the user accepts the
     * destructive currency change. Sync the patched fields into the shared
     * cache, then evict so any consumer refetches fresh data on next access.
     */
    function handleCurrencyChangeConfirmed(): void {
        const payload = currencyChangePatchPayload;
        if (payload && typeof payload.asset_id === 'number') {
            const id = payload.asset_id;
            mergeAssets([{id, ...payload}]);
            invalidateAfterMutation(id);
        }
        open = false;
        onupdated?.();
    }

    // =========================================================================
    // Close
    // =========================================================================

    function handleClose() {
        if (isDirty) {
            showDiscardConfirm = true;
            return;
        }
        doClose();
    }

    function doClose() {
        showDiscardConfirm = false;
        open = false;
        onclose?.();
    }
</script>

<ModalBase {open} maxWidth="4xl" allowOverflow={true} onRequestClose={handleClose} {zIndex}>
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
        <button type="button" onclick={handleClose} class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
            <X size={20} />
        </button>
    </div>

    <!-- Body -->
    <div class="px-6 py-4 space-y-5 max-h-[70vh] overflow-y-auto" data-testid="asset-modal-form">
        <!-- Search Online -->
        <AssetSearchAutocomplete onselect={handleSearchSelect} />

        <!-- Asset Details -->
        <div class="space-y-3">
            <div class="flex items-center justify-between">
                <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {$t('assets.modal.assetDetails')}
                </div>
                <!-- Ask Provider global button -->
                <button
                    type="button"
                    onclick={handleAskProvider}
                    disabled={!hasProvider || askingProvider}
                    class="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md
                               bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600
                               text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-600
                               disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    title={!hasProvider ? $t('assets.identifiers.askProviderHint') : ''}
                >
                    {#if askingProvider}
                        <Loader2 size={12} class="animate-spin" />
                    {:else}
                        <RefreshCw size={12} />
                    {/if}
                    <span class="hidden sm:inline">{$t('assets.identifiers.askProvider')}</span>
                </button>
            </div>

            <!-- Grid: Icon on left, form fields on right -->
            <div class="grid grid-cols-[auto_1fr] gap-4 items-center">
                <!-- Left: Icon (clickable) -->
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div class="group relative cursor-pointer" onclick={() => (showImagePicker = true)} title={$t('uploads.selectIcon')}>
                    <AssetIcon {iconUrl} {assetType} size="lg" />
                    <div
                        class="absolute inset-0 rounded-full bg-black/40 opacity-0 group-hover:opacity-100
                                flex items-center justify-center transition-opacity"
                    >
                        <Upload class="text-white" size={16} />
                    </div>
                </div>

                <!-- Right: Name+URL row, Type+Currency row (2×2 on desktop, column on mobile) -->
                <div class="space-y-3">
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <!-- Display Name -->
                        <div>
                            <label for="asset-display-name" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                {$t('common.name')} *
                            </label>
                            <input
                                id="asset-display-name"
                                type="text"
                                bind:value={displayName}
                                placeholder="Apple Inc."
                                data-testid="asset-modal-display-name"
                                class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                           bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                           placeholder-gray-400 dark:placeholder-gray-500
                                           focus:outline-none focus:ring-2 focus:ring-libre-green/50 focus:border-libre-green"
                            />
                            {#if duplicateAssetName}
                                <Tooltip text={$t('assets.modal.duplicateNameTooltip', {values: {name: duplicateAssetName}})} position="bottom" maxWidth="300px">
                                    <span class="inline-flex items-center gap-1 mt-1 text-xs text-amber-600 dark:text-amber-400">
                                        ⚠️ {$t('assets.modal.duplicateNameWarning', {values: {name: duplicateAssetName}})}
                                    </span>
                                </Tooltip>
                            {/if}
                        </div>

                        <!-- User URL (custom link for this asset) -->
                        <div>
                            <label for="asset-user-url" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                {$t('assets.provider.userUrl')}
                            </label>
                            <div class="flex gap-1.5">
                                <input
                                    id="asset-user-url"
                                    type="text"
                                    bind:value={providerUserUrl}
                                    placeholder="https://..."
                                    class="flex-1 px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                               bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                               placeholder-gray-400 dark:placeholder-gray-500
                                               focus:outline-none focus:ring-2 focus:ring-libre-green/50 focus:border-libre-green"
                                />
                                {#if providerUserUrl}
                                    <a href={providerUserUrl} target="_blank" rel="noopener noreferrer" class="shrink-0 flex items-center px-2 py-2 text-gray-400 hover:text-libre-green transition-colors">
                                        <ExternalLink size={14} />
                                    </a>
                                {/if}
                            </div>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <!-- Asset Type -->
                        <div>
                            <span class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                {$t('assets.type')} *
                            </span>
                            <SimpleSelect bind:value={assetType} options={assetTypeOptions} dropdownPosition="auto">
                                {#snippet item(opt)}
                                    <div class="flex items-center gap-2">
                                        <img src={opt.icon} alt="" class="w-4 h-4 object-contain" />
                                        <span>{opt.label}</span>
                                    </div>
                                {/snippet}
                                {#snippet selectedItem(opt)}
                                    <div class="flex items-center gap-2">
                                        <img src={opt.icon} alt="" class="w-4 h-4 object-contain" />
                                        <span>{opt.label}</span>
                                    </div>
                                {/snippet}
                            </SimpleSelect>
                        </div>

                        <!-- Currency -->
                        <div>
                            <span class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                {$t('common.currency')} *
                            </span>
                            <CurrencySearchSelect
                                value={currency}
                                onchange={(v) => {
                                    if (v) currency = v;
                                }}
                                maxVisibleItems={6}
                                compact={true}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Description (short, always visible) -->
        <div>
            <label for="asset-description" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {$t('brokers.description')}
            </label>
            <textarea
                id="asset-description"
                data-testid="asset-modal-description"
                bind:value={shortDescription}
                rows={2}
                placeholder="Brief description of the asset…"
                class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                           bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                           placeholder-gray-400 dark:placeholder-gray-500
                           focus:outline-none focus:ring-2 focus:ring-libre-green/50 focus:border-libre-green resize-none"
            ></textarea>
        </div>

        <!-- More Info (collapsible — Identifiers + Classification) -->
        <div class="border border-gray-200 dark:border-slate-700 rounded-lg">
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
                class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-slate-800 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors cursor-pointer select-none"
                role="button"
                tabindex="0"
                data-testid="asset-modal-more-info"
                onclick={() => {
                    moreInfoExpanded = !moreInfoExpanded;
                }}
                onkeydown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        moreInfoExpanded = !moreInfoExpanded;
                    }
                }}
            >
                <div class="flex items-center gap-2">
                    {#if moreInfoExpanded}
                        <ChevronDown size={16} />
                    {:else}
                        <ChevronRight size={16} />
                    {/if}
                    <span>{$t('assets.modal.moreInfo')}</span>
                </div>
            </div>

            {#if moreInfoExpanded}
                <div class="px-4 py-3 space-y-4 border-t border-gray-200 dark:border-slate-700">
                    <!-- Sub-section: Identifiers -->
                    <div class="space-y-2">
                        <div class="flex items-center justify-between">
                            <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                                {$t('common.identifiers')}
                            </div>
                            <div class="flex items-center gap-1.5">
                                {#if identifierSelectedIds.length > 0}
                                    <DataTableToolbar
                                        selectedCount={identifierSelectedIds.length}
                                        bulkActions={[
                                            {
                                                id: 'delete',
                                                icon: Trash2,
                                                label: () => $t('assets.identifiers.deleteSelected'),
                                                variant: 'danger',
                                                onClick: handleIdentifierBulkDelete,
                                            },
                                        ]}
                                        onClearSelection={() => {
                                            identifierSelectedIds = [];
                                        }}
                                    />
                                {/if}
                                <button
                                    type="button"
                                    onclick={addIdentifierRow}
                                    class="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                                    title={$t('assets.identifiers.addIdentifier')}
                                >
                                    <Plus size={10} /> <span class="hidden sm:inline">{$t('assets.identifiers.addIdentifier')}</span>
                                </button>
                                <button
                                    type="button"
                                    onclick={() => handleAskProviderSection('identifiers')}
                                    disabled={!hasProvider || askingProvider}
                                    class="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                    title={$t('assets.identifiers.askProvider')}
                                >
                                    {#if askingProvider}<Loader2 size={10} class="animate-spin" />{:else}<RefreshCw size={10} />{/if}
                                    <span class="hidden sm:inline">{$t('assets.identifiers.askProvider')}</span>
                                </button>
                            </div>
                        </div>
                        {#if identifierRows.length > 0}
                            <DataTable
                                data={identifierRows}
                                columns={identifierColumns}
                                getRowId={(r) => r.id}
                                storageKey="asset-modal-identifiers"
                                enableSelection={true}
                                onSelectionChange={(ids) => {
                                    identifierSelectedIds = ids;
                                }}
                                enablePagination={false}
                                enableColumnFilters={false}
                                enableSorting={false}
                                enableColumnResize={false}
                                enableColumnVisibility={false}
                                enableActions={true}
                                actionsColumnWidth="40px"
                                rowActions={identifierRowActions}
                                tableLayout="auto"
                            />
                        {:else}
                            <div class="text-xs text-gray-400 italic py-1">{$t('assets.identifiers.askProviderHint')}</div>
                        {/if}
                    </div>

                    <!-- Sub-section: Classification -->
                    <div class="space-y-3">
                        <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                            {$t('common.classification')}
                        </div>

                        <!-- Sector Distribution -->
                        <DistributionEditor kind="sector" bind:value={sectorDistribution} {hasProvider} {askingProvider} onAskProvider={() => handleAskProviderSection('sector')} />

                        <!-- Geographic Distribution -->
                        <DistributionEditor kind="geographic" bind:value={geographicDistribution} {hasProvider} {askingProvider} onAskProvider={() => handleAskProviderSection('geographic')} />
                    </div>
                </div>
            {/if}
        </div>

        <!-- Provider Assignment (collapsible) -->
        <div class="border border-gray-200 dark:border-slate-700 rounded-lg">
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
                class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-50 dark:bg-slate-800 transition-colors select-none {providerNoProvider ? '' : 'hover:bg-gray-100 dark:hover:bg-slate-700 cursor-pointer'}"
                role="button"
                tabindex="0"
                onclick={() => {
                    if (!providerNoProvider) providerExpanded = !providerExpanded;
                }}
                onkeydown={(e) => {
                    if ((e.key === 'Enter' || e.key === ' ') && !providerNoProvider) {
                        e.preventDefault();
                        providerExpanded = !providerExpanded;
                    }
                }}
            >
                <div class="flex items-center gap-2">
                    {#if !providerNoProvider}
                        {#if providerExpanded}
                            <ChevronDown size={16} />
                        {:else}
                            <ChevronRight size={16} />
                        {/if}
                    {:else}
                        <Minus size={16} class="text-gray-400" />
                    {/if}
                    <span>{$t('assets.provider.assignment')}</span>
                    {#if providerTestStatus === 'passed'}
                        <span class="text-green-500 text-xs ml-1">✅</span>
                    {:else if providerTestStatus === 'failed'}
                        <span class="text-red-500 text-xs ml-1">❌</span>
                    {:else if providerTestStatus === 'testing'}
                        <Loader2 size={12} class="animate-spin text-gray-400 ml-1" />
                    {/if}
                </div>
                <!-- No Provider checkbox in header -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 cursor-pointer" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>
                    <input
                        type="checkbox"
                        id="no-provider-checkbox"
                        checked={providerNoProvider}
                        onchange={() => {
                            providerNoProvider = !providerNoProvider;
                            if (providerNoProvider) {
                                providerExpanded = false;
                                providerTestStatus = 'not_tested';
                            }
                        }}
                        class="rounded border-gray-300 dark:border-slate-600 text-libre-green focus:ring-libre-green/50"
                    />
                    <label for="no-provider-checkbox">{$t('assets.provider.noProvider')}</label>
                </div>
            </div>

            {#if providerExpanded && !providerNoProvider}
                <div class="px-4 py-3 border-t border-gray-200 dark:border-slate-700">
                    <ProviderAssignmentSection
                        bind:providerCode
                        bind:identifier={providerIdentifier}
                        bind:identifierType={providerIdentifierType}
                        bind:providerParams
                        bind:providerUrl
                        bind:noProvider={providerNoProvider}
                        bind:fetchInterval
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
                <span>{$t('assets.modal.autoAssignInfo', {values: {provider: providerCode}})}</span>
            </InfoBanner>
        {/if}

        <!-- Error -->
        {#if formError}
            <div data-form-error class="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-4 py-2 rounded-lg">
                {formError}
            </div>
        {/if}
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-slate-700">
        <button type="button" onclick={handleClose} data-testid="asset-modal-cancel" class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors">
            {$t('common.cancel')}
        </button>
        <button
            type="button"
            onclick={handleSave}
            disabled={!isValid || saving}
            data-testid="asset-modal-save"
            class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-libre-green rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
            {#if saving}
                <Loader2 size={14} class="animate-spin" />
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
    onCancel={() => {
        showSaveWithoutTestConfirm = false;
    }}
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
    onCancel={() => {
        showIdentifierChangeConfirm = false;
        pendingSearchResult = null;
    }}
    zIndex={70}
/>

<!-- Confirmation: Discard unsaved changes -->
<ConfirmModal
    open={showDiscardConfirm}
    title={$t('common.discardChanges')}
    message={$t('common.discardChangesMessage')}
    confirmText={$t('common.discardAndClose')}
    cancelText={$t('common.continueEditing')}
    warning={true}
    onConfirm={() => doClose()}
    onCancel={() => {
        showDiscardConfirm = false;
    }}
    zIndex={70}
/>

<!-- #R3-4 — Confirmation: regenerate scheduled_investment prices on params change -->
<ConfirmModal
    open={showScheduledRegenConfirm}
    title={$t('assets.modal.scheduledRegenTitle')}
    message={$t('assets.modal.scheduledRegenMessage')}
    confirmText={$t('assets.modal.scheduledRegenConfirm')}
    cancelText={$t('common.cancel')}
    danger={true}
    onConfirm={() => {
        showScheduledRegenConfirm = false;
        const aid = pendingSaveAssetId;
        // pendingSaveAssetId is kept non-null so the guard in saveEdit() skips
        // re-showing this modal and proceeds to PATCH+assign+sync.
        if (aid !== null) {
            saveEdit(aid).catch((err) => {
                console.error('saveEdit after regenerate confirm failed:', err);
                toasts.error($t('common.errorOccurred'));
                pendingSaveAssetId = null;
            });
        }
    }}
    onCancel={() => {
        showScheduledRegenConfirm = false;
        pendingSaveAssetId = null;
    }}
    zIndex={70}
/>

<!-- Provider Comparison Modal -->
<ProviderComparisonModal
    bind:open={showComparisonModal}
    differences={comparisonDifferences}
    onapply={handleComparisonApply}
    oncancel={() => {
        showComparisonModal = false;
    }}
/>

<!-- I.6 + R3-3 Policy D — Destructive currency-change modal. Triggered by the CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA marker. -->
<AssetCurrencyChangeModal
    bind:open={currencyChangeModalOpen}
    blocker={currencyChangeBlocker}
    patchPayload={currencyChangePatchPayload}
    providerAssigned={currencyChangeProviderAssigned}
    onconfirmed={() => {
        // The flow completed: the child modal already emitted the final
        // `currencyChange.done` toast. I-bis #12 — suppress the generic
        // "updated successfully" toast here to avoid duplicate notifications.
        // Cache eviction + merge handled by `handleCurrencyChangeConfirmed`.
        handleCurrencyChangeConfirmed();
    }}
    oncanceled={() => {
        currencyChangeBlocker = null;
        currencyChangePatchPayload = null;
    }}
/>

<!-- Image Picker for asset icon -->
<ImagePickerWrapper open={showImagePicker} preset="asset-icon" title={$t('uploads.selectIcon')} initialUrl={iconUrl ?? ''} circularPreview={false} filterImages={true} onchange={handleImagePickerChange} oncancel={() => (showImagePicker = false)} />

<!-- Confirmation: Bulk delete identifiers -->
<ConfirmModal
    open={showIdentifierDeleteConfirm}
    title={$t('assets.identifiers.deleteSelected')}
    message={$t('assets.identifiers.deleteConfirmMessage', {values: {count: pendingIdentifierDeleteIds.length}})}
    confirmText={$t('common.delete')}
    warning={true}
    onConfirm={confirmIdentifierBulkDelete}
    onCancel={() => {
        showIdentifierDeleteConfirm = false;
        pendingIdentifierDeleteIds = [];
    }}
    zIndex={80}
/>
