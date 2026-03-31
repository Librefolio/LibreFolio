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
    import {ChevronDown, ChevronRight, Loader2, Minus, Plus, RefreshCw, Trash2, Upload, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {CurrencySearchSelect, SimpleSelect} from '$lib/components/ui/select';
    import AssetSearchAutocomplete from './AssetSearchAutocomplete.svelte';
    import AssetIcon from './AssetIcon.svelte';
    import ProviderAssignmentSection from './ProviderAssignmentSection.svelte';
    import ProviderComparisonModal from './ProviderComparisonModal.svelte';
    import type {DiffItem} from './ProviderComparisonModal.svelte';
    import DistributionEditor from '$lib/components/ui/input/DistributionEditor.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import type {ColumnDef as DTColumnDef, RowAction as DTRowAction} from '$lib/components/table/types';
    import ImagePickerWrapper from '$lib/components/ui/media/ImagePickerWrapper.svelte';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import {ASSET_TYPES, IDENTIFIER_TYPES, buildAssetTypeOptions, getAssetTypeIconUrl} from '$lib/utils/assetTypes';

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
            sector_area?: { distribution: Record<string, number> } | null;
            geographic_area?: { distribution: Record<string, number> } | null;
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


    // =========================================================================
    // Derived
    // =========================================================================

    let isValid = $derived(displayName.trim().length > 0);
    let hasProvider = $derived(!providerNoProvider && providerCode !== '' && providerIdentifier !== '');
    let title = $derived(editMode ? $t('assets.modal.titleEdit') : $t('assets.modal.title'));

    /** Asset type options for SimpleSelect (with PNG icons) */
    let assetTypeOptions = $derived(buildAssetTypeOptions($t));

    /** Current form fingerprint for dirty detection */
    let currentSnapshot = $derived(
        JSON.stringify([displayName, currency, assetType, JSON.stringify(identifierRows.map(r => [r.type, r.value])), providerCode, providerIdentifier, providerIdentifierType, providerNoProvider])
    );
    let isDirty = $derived(initialSnapshot !== '' && currentSnapshot !== initialSnapshot);

    // =========================================================================
    // Helpers — Identifier rows ↔ DB columns conversion
    // =========================================================================

    function columnsToIdentifierRows(data: AssetData): IdentifierRow[] {
        const rows: IdentifierRow[] = [];
        for (const idType of IDENTIFIER_TYPES) {
            const key = `identifier_${idType.toLowerCase()}` as keyof AssetData;
            const value = (data[key] as string) ?? '';
            if (value) rows.push({id: crypto.randomUUID(), type: idType, value});
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
        const usedTypes = new Set(identifierRows.map(r => r.type));
        const availableType = IDENTIFIER_TYPES.find(t => !usedTypes.has(t)) ?? 'TICKER';
        identifierRows = [...identifierRows, {id: crypto.randomUUID(), type: availableType, value: ''}];
    }

    function updateIdentifierRow(id: string, field: 'type' | 'value', val: string) {
        identifierRows = identifierRows.map(r => r.id === id ? {...r, [field]: val} : r);
    }

    function removeIdentifierRow(id: string) {
        identifierRows = identifierRows.filter(r => r.id !== id);
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
        identifierRows = identifierRows.filter(r => !deleteSet.has(r.id));
        identifierSelectedIds = [];
        pendingIdentifierDeleteIds = [];
        showIdentifierDeleteConfirm = false;
    }

    /** Get identifier value by type from rows */
    function getIdentifierByType(type: string): string {
        return identifierRows.find(r => r.type === type)?.value ?? '';
    }

    // =========================================================================
    // Identifier DataTable columns
    // =========================================================================

    let idTypeOptions = $derived(IDENTIFIER_TYPES.map(t => ({value: t, label: t})));

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
        moreInfoExpanded = identifierRows.length > 0;
        providerExpanded = !!data.provider_code;
        searchResultSelected = false;
        autoFilledFields = new Set();
        conflictFields = new Map();
        formError = null;
        providerTestStatus = 'not_tested';
        showComparisonModal = false;
        comparisonDifferences = [];
        setTimeout(() => {
            initialSnapshot = JSON.stringify([displayName, currency, assetType, JSON.stringify(identifierRows.map(r => [r.type, r.value])), providerCode, providerIdentifier, providerIdentifierType, providerNoProvider, shortDescription]);
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
        setTimeout(() => {
            initialSnapshot = JSON.stringify([displayName, currency, assetType, JSON.stringify(identifierRows.map(r => [r.type, r.value])), providerCode, providerIdentifier, providerIdentifierType, providerNoProvider, shortDescription]);
        }, 0);
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
        if (result.asset_type) assetType = (ASSET_TYPES as readonly string[]).includes(result.asset_type.toUpperCase()) ? result.asset_type.toUpperCase() : 'OTHER';
        if (result.currency) currency = result.currency;

        // Auto-fill identifier based on identifier_type
        const idType = (result.identifier_type ?? '').toUpperCase();
        if (idType && result.identifier) {
            // Add or update the identifier row
            const existing = identifierRows.find(r => r.type === idType);
            if (existing) {
                identifierRows = identifierRows.map(r => r.type === idType ? {...r, value: result.identifier} : r);
            } else {
                identifierRows = [...identifierRows, {id: crypto.randomUUID(), type: idType, value: result.identifier}];
            }
        }

        // Auto-fill provider
        providerCode = result.provider_code;
        providerIdentifier = result.identifier;
        providerIdentifierType = result.identifier_type;
        providerUrl = result.provider_url ?? null;
        providerNoProvider = false;
        providerParams = null;

        // Expand sections
        moreInfoExpanded = true;
        providerExpanded = true;
        searchResultSelected = true;
        formError = null;

        // Auto-trigger test + metadata fetch
        autoTriggerProbe();
        autoFetchMetadata();
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

    /**
     * Silent metadata fetch after search selection.
     * Populates all empty fields (identifiers, description, distributions)
     * without showing comparison modal — only fills blank fields.
     */
    async function autoFetchMetadata() {
        if (!providerCode || !providerIdentifier) return;
        try {
            const response = await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post({
                provider_code: providerCode,
                identifier: providerIdentifier,
                identifier_type: providerIdentifierType as any,
                provider_params: providerParams,
                operations: ['metadata'],
            }) as any;

            const meta = response.metadata;
            if (!meta?.success || !meta.patch_data) return;
            const pd = meta.patch_data;

            // Auto-fill only empty fields (no comparison modal)
            for (const idType of IDENTIFIER_TYPES) {
                const dbKey = `identifier_${idType.toLowerCase()}`;
                const provVal = pd[dbKey];
                if (provVal && !getIdentifierByType(idType)) {
                    setIdentifierByType(idType, provVal);
                    autoFilledFields = new Set([...autoFilledFields, dbKey]);
                }
            }
            if (pd.display_name && !displayName) {
                displayName = pd.display_name;
                autoFilledFields = new Set([...autoFilledFields, 'display_name']);
            }
            if (pd.asset_type && assetType === 'STOCK') {
                const at = pd.asset_type.toUpperCase();
                if ((ASSET_TYPES as readonly string[]).includes(at)) {
                    assetType = at;
                    autoFilledFields = new Set([...autoFilledFields, 'asset_type']);
                }
            }
            if (pd.currency && !currency) {
                currency = pd.currency;
                autoFilledFields = new Set([...autoFilledFields, 'currency']);
            }

            const cpData = pd.classification_params;
            if (cpData?.short_description && !shortDescription) {
                shortDescription = cpData.short_description;
                autoFilledFields = new Set([...autoFilledFields, 'short_description']);
            }
            if (cpData?.sector_area) {
                const provDist = cpData.sector_area.distribution ?? cpData.sector_area;
                if (Object.keys(sectorDistribution).length === 0) {
                    sectorDistribution = provDist;
                    autoFilledFields = new Set([...autoFilledFields, 'sector_area']);
                }
            }
            if (cpData?.geographic_area) {
                const provDist = cpData.geographic_area.distribution ?? cpData.geographic_area;
                if (Object.keys(geographicDistribution).length === 0) {
                    geographicDistribution = provDist;
                    autoFilledFields = new Set([...autoFilledFields, 'geographic_area']);
                }
            }
        } catch (e) {
            // Silent — metadata is best-effort on search selection
            console.debug('Auto-fetch metadata failed (non-blocking):', e);
        }
    }

    // =========================================================================
    // Ask Provider (metadata) — fill all fields + comparison modal
    // =========================================================================

    /** Helper: field name like 'identifier_ticker' → type 'TICKER' */
    function fieldToIdType(field: string): string {
        return field.replace('identifier_', '').toUpperCase();
    }

    /** Set or update an identifier row by type */
    function setIdentifierByType(type: string, val: string) {
        const existing = identifierRows.find(r => r.type === type);
        if (existing) {
            identifierRows = identifierRows.map(r => r.type === type ? {...r, value: val, autoFilled: true} : r);
        } else {
            identifierRows = [...identifierRows, {id: crypto.randomUUID(), type, value: val, autoFilled: true}];
        }
    }

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
                const differences: DiffItem[] = [];

                // String fields comparison helper
                function compareField(field: string, label: string, currentVal: string, providerVal: string | null | undefined) {
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

                // Compare identifier fields
                for (const idType of IDENTIFIER_TYPES) {
                    const dbKey = `identifier_${idType.toLowerCase()}`;
                    const provVal = pd[dbKey];
                    if (provVal) {
                        const currentVal = getIdentifierByType(idType);
                        compareField(dbKey, idType, currentVal, provVal);
                    }
                }

                // Compare display_name, asset_type and currency
                if (pd.display_name) compareField('display_name', $t('common.name'), displayName, pd.display_name);
                if (pd.asset_type) compareField('asset_type', $t('assets.type'), assetType, pd.asset_type);
                if (pd.currency) compareField('currency', $t('common.currency'), currency, pd.currency);

                // Compare short_description
                const cpData = pd.classification_params;
                if (cpData?.short_description) {
                    compareField('short_description', 'Description', shortDescription, cpData.short_description);
                }

                // Compare distributions (block accept/reject)
                const missingDistributions: string[] = [];
                if (cpData?.sector_area) {
                    const provDist = cpData.sector_area.distribution ?? cpData.sector_area;
                    const hasCurrent = Object.keys(sectorDistribution).length > 0;
                    if (!hasCurrent) {
                        sectorDistribution = provDist;
                        autoFilledFields = new Set([...autoFilledFields, 'sector_area']);
                    } else if (JSON.stringify(sectorDistribution) !== JSON.stringify(provDist)) {
                        differences.push({field: 'sector_area', label: $t('assets.modal.sectorDistribution'), type: 'distribution', currentValue: sectorDistribution, providerValue: provDist, selected: true});
                    } else {
                        autoFilledFields = new Set([...autoFilledFields, 'sector_area']);
                    }
                } else {
                    missingDistributions.push($t('assets.modal.sectorDistribution'));
                }

                if (cpData?.geographic_area) {
                    const provDist = cpData.geographic_area.distribution ?? cpData.geographic_area;
                    const hasCurrent = Object.keys(geographicDistribution).length > 0;
                    if (!hasCurrent) {
                        geographicDistribution = provDist;
                        autoFilledFields = new Set([...autoFilledFields, 'geographic_area']);
                    } else if (JSON.stringify(geographicDistribution) !== JSON.stringify(provDist)) {
                        differences.push({field: 'geographic_area', label: $t('assets.modal.geographicDistribution'), type: 'distribution', currentValue: geographicDistribution, providerValue: provDist, selected: true});
                    } else {
                        autoFilledFields = new Set([...autoFilledFields, 'geographic_area']);
                    }
                } else {
                    missingDistributions.push($t('assets.modal.geographicDistribution'));
                }

                // Notify about missing distributions
                if (missingDistributions.length > 0) {
                    toasts.info($t('assets.comparison.noDistributionData', {values: {fields: missingDistributions.join(', ')}}));
                }

                if (differences.length > 0) {
                    comparisonDifferences = differences;
                    showComparisonModal = true;
                } else {
                    toasts.success($t('assets.comparison.allMatch'));
                }
            }
        } catch (e: any) {
            console.error('Ask Provider failed:', e);
        } finally {
            askingProvider = false;
        }
    }

    /** Per-section Ask Provider — calls same probe, shows diff modal for section-specific fields */
    async function handleAskProviderSection(section: 'identifiers' | 'sector' | 'geographic') {
        if (!providerCode || !providerIdentifier) return;
        askingProvider = true;

        try {
            const response = await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post({
                provider_code: providerCode,
                identifier: providerIdentifier,
                identifier_type: providerIdentifierType as any,
                provider_params: providerParams,
                operations: ['metadata'],
            }) as any;

            const meta = response.metadata;
            if (!meta?.success || !meta.patch_data) {
                toasts.info($t('assets.identifiers.askProviderHint') + ' — no data from provider');
                return;
            }
            const pd = meta.patch_data;
            const differences: DiffItem[] = [];

            if (section === 'identifiers') {
                for (const idType of IDENTIFIER_TYPES) {
                    const dbKey = `identifier_${idType.toLowerCase()}`;
                    const provVal = pd[dbKey];
                    if (provVal) {
                        const currentVal = getIdentifierByType(idType);
                        if (!currentVal) {
                            setFieldValue(dbKey, provVal);
                            autoFilledFields = new Set([...autoFilledFields, dbKey]);
                        } else if (currentVal !== provVal) {
                            differences.push({field: dbKey, label: idType, type: 'string', currentValue: currentVal, providerValue: provVal, selected: true});
                        } else {
                            autoFilledFields = new Set([...autoFilledFields, dbKey]);
                        }
                    }
                }
            } else if (section === 'sector') {
                const cpData = pd.classification_params;
                if (cpData?.sector_area) {
                    const provDist = cpData.sector_area.distribution ?? cpData.sector_area;
                    const hasCurrent = Object.keys(sectorDistribution).length > 0;
                    if (!hasCurrent) {
                        sectorDistribution = provDist;
                        autoFilledFields = new Set([...autoFilledFields, 'sector_area']);
                    } else if (JSON.stringify(sectorDistribution) !== JSON.stringify(provDist)) {
                        differences.push({field: 'sector_area', label: $t('assets.modal.sectorDistribution'), type: 'distribution', currentValue: sectorDistribution, providerValue: provDist, selected: true});
                    } else {
                        autoFilledFields = new Set([...autoFilledFields, 'sector_area']);
                    }
                } else {
                    toasts.info($t('assets.modal.sectorDistribution') + ' — no data from provider');
                }
            } else if (section === 'geographic') {
                const cpData = pd.classification_params;
                if (cpData?.geographic_area) {
                    const provDist = cpData.geographic_area.distribution ?? cpData.geographic_area;
                    const hasCurrent = Object.keys(geographicDistribution).length > 0;
                    if (!hasCurrent) {
                        geographicDistribution = provDist;
                        autoFilledFields = new Set([...autoFilledFields, 'geographic_area']);
                    } else if (JSON.stringify(geographicDistribution) !== JSON.stringify(provDist)) {
                        differences.push({field: 'geographic_area', label: $t('assets.modal.geographicDistribution'), type: 'distribution', currentValue: geographicDistribution, providerValue: provDist, selected: true});
                    } else {
                        autoFilledFields = new Set([...autoFilledFields, 'geographic_area']);
                    }
                } else {
                    toasts.info($t('assets.modal.geographicDistribution') + ' — no data from provider');
                }
            }

            // Show diff modal if conflicts exist, otherwise show success toast
            if (differences.length > 0) {
                comparisonDifferences = differences;
                showComparisonModal = true;
            } else {
                toasts.success($t('assets.comparison.allMatch'));
            }
        } catch (e: any) {
            console.error(`Ask Provider (${section}) failed:`, e);
        } finally {
            askingProvider = false;
        }
    }

    /** Generic setter used by comparison logic */
    function setFieldValue(field: string, value: string) {
        if (field.startsWith('identifier_')) {
            const idType = fieldToIdType(field);
            setIdentifierByType(idType, value);
        } else {
            switch (field) {
                case 'display_name': displayName = value; break;
                case 'asset_type': assetType = value; break;
                case 'currency': currency = value; break;
                case 'short_description': shortDescription = value; break;
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
            console.error('Save failed:', e);
            if (e?.response?.status === 409) {
                formError = $t('assets.modal.duplicateName');
            } else {
                formError = e?.message || 'Save failed';
            }
            // Scroll error into view
            setTimeout(() => {
                document.querySelector('[data-form-error]')?.scrollIntoView({behavior: 'smooth', block: 'center'});
            }, 50);
        } finally {
            saving = false;
        }
    }

    async function saveCreate() {
        // Build classification_params if any fields are set
        const classificationParams: any = {};
        if (shortDescription) classificationParams.short_description = shortDescription;
        if (Object.keys(sectorDistribution).length > 0) classificationParams.sector_area = {distribution: sectorDistribution};
        if (Object.keys(geographicDistribution).length > 0) classificationParams.geographic_area = {distribution: geographicDistribution};

        // Step 1: Create asset
        const createPayload = [{
            display_name: displayName.trim(),
            currency: currency,
            asset_type: assetType,
            icon_url: iconUrl || undefined,
            classification_params: Object.keys(classificationParams).length > 0 ? classificationParams : undefined,
            ...identifierRowsToColumns(identifierRows),
        }];

        const createResp = await zodiosApi.create_assets_bulk_api_v1_assets_post(createPayload as any) as any;
        const result = createResp?.results?.[0];
        if (!result?.success) {
            throw new Error(result?.message || 'Failed to create asset');
        }
        const assetId = result.asset_id;

        // Step 2: Assign provider (separate try/catch — asset already created)
        if (hasProvider) {
            try {
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
            } catch (assignErr: any) {
                console.error('Provider assignment failed after asset creation:', assignErr);
                toasts.warning($t('assets.modal.createSuccessProviderFailed', {values: {name: displayName}}));
                open = false;
                oncreated?.();
                return;
            }
        }

        toasts.success($t('assets.modal.createSuccess', {values: {name: displayName}}));
        open = false;
        oncreated?.();
    }

    async function saveEdit(assetId: number) {
        // Build classification_params
        const classificationParams: any = {};
        if (shortDescription) classificationParams.short_description = shortDescription;
        if (Object.keys(sectorDistribution).length > 0) classificationParams.sector_area = {distribution: sectorDistribution};
        if (Object.keys(geographicDistribution).length > 0) classificationParams.geographic_area = {distribution: geographicDistribution};

        // Step 1: Patch asset
        const idCols = identifierRowsToColumns(identifierRows);
        const patchPayload = [{
            asset_id: assetId,
            display_name: displayName.trim(),
            currency: currency,
            asset_type: assetType,
            icon_url: iconUrl,
            classification_params: Object.keys(classificationParams).length > 0 ? classificationParams : null,
            identifier_isin: idCols.identifier_isin || null,
            identifier_ticker: idCols.identifier_ticker || null,
            identifier_cusip: idCols.identifier_cusip || null,
            identifier_sedol: idCols.identifier_sedol || null,
            identifier_figi: idCols.identifier_figi || null,
            identifier_uuid: idCols.identifier_uuid || null,
            identifier_other: idCols.identifier_other || null,
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
                        <Loader2 size={12} class="animate-spin"/>
                    {:else}
                        <RefreshCw size={12}/>
                    {/if}
                    <span class="hidden sm:inline">{$t('assets.identifiers.askProvider')}</span>
                </button>
            </div>

            <!-- Grid: Icon on left, form fields on right -->
            <div class="grid grid-cols-[auto_1fr] gap-4 items-start">
                <!-- Left: Icon (clickable) -->
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div class="group relative cursor-pointer"
                     onclick={() => showImagePicker = true}
                     title={$t('uploads.selectIcon')}>
                    <AssetIcon iconUrl={iconUrl} assetType={assetType} size="lg" />
                    <div class="absolute inset-0 rounded-full bg-black/40 opacity-0 group-hover:opacity-100
                                flex items-center justify-center transition-opacity">
                        <Upload class="text-white" size={16}/>
                    </div>
                </div>

                <!-- Right: Name, Type+Currency -->
                <div class="space-y-3">
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
                                class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                       bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                       placeholder-gray-400 dark:placeholder-gray-500
                                       focus:outline-none focus:ring-2 focus:ring-libre-green/50 focus:border-libre-green"
                        />
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <!-- Asset Type -->
                        <div>
                            <span class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                {$t('assets.type')} *
                            </span>
                            <SimpleSelect
                                    bind:value={assetType}
                                    options={assetTypeOptions}
                                    dropdownPosition="auto"
                            >
                                {#snippet item(opt)}
                                    <div class="flex items-center gap-2">
                                        <img src={opt.icon} alt="" class="w-4 h-4 object-contain"/>
                                        <span>{opt.label}</span>
                                    </div>
                                {/snippet}
                                {#snippet selectedItem(opt)}
                                    <div class="flex items-center gap-2">
                                        <img src={opt.icon} alt="" class="w-4 h-4 object-contain"/>
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
                                    onchange={(v) => { if (v) currency = v; }}
                                    maxVisibleItems={6}
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
                    onclick={() => { moreInfoExpanded = !moreInfoExpanded; }}
                    onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); moreInfoExpanded = !moreInfoExpanded; } }}
            >
                <div class="flex items-center gap-2">
                    {#if moreInfoExpanded}
                        <ChevronDown size={16}/>
                    {:else}
                        <ChevronRight size={16}/>
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
                                {$t('assets.modal.identifiers')}
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
                                        onClearSelection={() => { identifierSelectedIds = []; }}
                                    />
                                {/if}
                                <button type="button" onclick={addIdentifierRow}
                                        class="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                                        title={$t('assets.identifiers.addIdentifier')}>
                                    <Plus size={10}/> <span class="hidden sm:inline">{$t('assets.identifiers.addIdentifier')}</span>
                                </button>
                                <button type="button" onclick={() => handleAskProviderSection('identifiers')}
                                        disabled={!hasProvider || askingProvider}
                                        class="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                        title={$t('assets.identifiers.askProvider')}>
                                    {#if askingProvider}<Loader2 size={10} class="animate-spin"/>{:else}<RefreshCw size={10}/>{/if}
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
                                    onSelectionChange={(ids) => { identifierSelectedIds = ids; }}
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
                            {$t('assets.modal.classification')}
                        </div>

                        <!-- Sector Distribution -->
                        <DistributionEditor
                                kind="sector"
                                bind:value={sectorDistribution}
                                {hasProvider}
                                {askingProvider}
                                onAskProvider={() => handleAskProviderSection('sector')}
                        />

                        <!-- Geographic Distribution -->
                        <DistributionEditor
                                kind="geographic"
                                bind:value={geographicDistribution}
                                {hasProvider}
                                {askingProvider}
                                onAskProvider={() => handleAskProviderSection('geographic')}
                        />
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
                    onclick={() => { if (!providerNoProvider) providerExpanded = !providerExpanded; }}
                    onkeydown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && !providerNoProvider) { e.preventDefault(); providerExpanded = !providerExpanded; } }}
            >
                <div class="flex items-center gap-2">
                    {#if !providerNoProvider}
                        {#if providerExpanded}
                            <ChevronDown size={16}/>
                        {:else}
                            <ChevronRight size={16}/>
                        {/if}
                    {:else}
                        <Minus size={16} class="text-gray-400"/>
                    {/if}
                    <span>{$t('assets.provider.assignment')}</span>
                    {#if providerTestStatus === 'passed'}
                        <span class="text-green-500 text-xs ml-1">✅</span>
                    {:else if providerTestStatus === 'failed'}
                        <span class="text-red-500 text-xs ml-1">❌</span>
                    {:else if providerTestStatus === 'testing'}
                        <Loader2 size={12} class="animate-spin text-gray-400 ml-1"/>
                    {/if}
                </div>
                <!-- No Provider checkbox in header -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                        class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 cursor-pointer"
                        onclick={(e) => e.stopPropagation()}
                        onkeydown={(e) => e.stopPropagation()}
                >
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

<!-- Confirmation: Discard unsaved changes -->
<ConfirmModal
        open={showDiscardConfirm}
        title={$t('common.discardChanges')}
        message={$t('common.discardChangesMessage')}
        confirmText={$t('common.discardAndClose')}
        cancelText={$t('common.continueEditing')}
        warning={true}
        onConfirm={() => doClose()}
        onCancel={() => { showDiscardConfirm = false; }}
        zIndex={70}
/>

<!-- Provider Comparison Modal -->
<ProviderComparisonModal
        bind:open={showComparisonModal}
        differences={comparisonDifferences}
        onapply={handleComparisonApply}
        oncancel={() => { showComparisonModal = false; }}
/>

<!-- Image Picker for asset icon -->
<ImagePickerWrapper
    open={showImagePicker}
    preset="asset-icon"
    title={$t('uploads.selectIcon')}
    initialUrl={iconUrl ?? ''}
    circularPreview={false}
    filterImages={true}
    onchange={handleImagePickerChange}
    oncancel={() => showImagePicker = false}
/>

<!-- Confirmation: Bulk delete identifiers -->
<ConfirmModal
    open={showIdentifierDeleteConfirm}
    title={$t('assets.identifiers.deleteSelected')}
    message={$t('assets.identifiers.deleteConfirmMessage', {values: {count: pendingIdentifierDeleteIds.length}})}
    confirmText={$t('common.delete')}
    warning={true}
    onConfirm={confirmIdentifierBulkDelete}
    onCancel={() => { showIdentifierDeleteConfirm = false; pendingIdentifierDeleteIds = []; }}
    zIndex={80}
/>

