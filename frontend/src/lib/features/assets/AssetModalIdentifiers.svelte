<!--
  AssetModalIdentifiers — the identifiers of the asset in AssetModal: the single-valued types in an editable table (add,
  edit, remove, bulk delete) and the OTHER (soft) identifiers as removable tags. The rows and the table selection are
  bound to the modal; every edit reports the identifier field it touched, and the modal confirms the bulk delete.
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Info, Loader2, Plus, RefreshCw, Trash2, X} from 'lucide-svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import type {ColumnDef as DTColumnDef, RowAction as DTRowAction} from '$lib/components/table/types';
    import TagInput from '$lib/components/ui/input/TagInput.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {IDENTIFIER_TYPES} from '$lib/utils/assetTypes';
    import {generateUUID} from '$lib/utils/core/uuid';
    import {nextAvailableIdentifierType, type IdentifierRow} from './assetIdentifiers';

    interface Props {
        /** The identifier rows of the asset: single-valued types and OTHER. */
        rows: IdentifierRow[];
        /** Ids of the rows selected in the table, for the bulk delete. */
        selectedIds: string[];
        hasProvider: boolean;
        askingProvider: boolean;
        /** An identifier field the user edited by hand (`identifier_<type>`). */
        onmanualedit: (field: string) => void;
        onaskprovider: () => void;
        /** Bulk delete of `selectedIds`, which the modal confirms. */
        onbulkdelete: () => void;
    }

    let {rows = $bindable(), selectedIds = $bindable(), hasProvider, askingProvider, onmanualedit, onaskprovider, onbulkdelete}: Props = $props();

    function addIdentifierRow() {
        // OTHER (soft identifiers) is managed via the tag/badge input below, so the table
        // only adds fixed single-valued types. If all are already used, do nothing.
        const availableType = nextAvailableIdentifierType(rows);
        if (!availableType) return;
        onmanualedit(`identifier_${availableType.toLowerCase()}`);
        rows = [...rows, {id: generateUUID(), type: availableType, value: ''}];
    }

    function updateIdentifierRow(id: string, field: 'type' | 'value', val: string) {
        const current = rows.find((row) => row.id === id);
        if (current) onmanualedit(`identifier_${current.type.toLowerCase()}`);
        if (field === 'type') onmanualedit(`identifier_${val.toLowerCase()}`);
        rows = rows.map((r) => (r.id === id ? {...r, [field]: val} : r));
    }

    function removeIdentifierRow(id: string) {
        const current = rows.find((row) => row.id === id);
        if (current) onmanualedit(`identifier_${current.type.toLowerCase()}`);
        rows = rows.filter((r) => r.id !== id);
    }

    let idTypeOptions = $derived(IDENTIFIER_TYPES.filter((t) => t !== 'OTHER').map((t) => ({value: t, label: t})));

    // OTHER (soft identifiers) are rendered as tag badges, not table rows.
    let rowsFixed = $derived(rows.filter((r) => r.type !== 'OTHER'));
    let otherIdentifiers = $derived(
        rows
            .filter((r) => r.type === 'OTHER')
            .map((r) => (typeof r.value === 'string' ? r.value : String(r.value ?? '')))
            .filter((v) => v.trim().length > 0),
    );

    /** Replace all OTHER rows from the tag/badge input (fixed-type rows untouched). */
    function setOtherIdentifiers(vals: string[]) {
        onmanualedit('identifier_other');
        const fixed = rows.filter((r) => r.type !== 'OTHER');
        const others = vals.map((v) => ({id: generateUUID(), type: 'OTHER', value: v}));
        rows = [...fixed, ...others];
    }

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

    let identifierRowActions: DTRowAction<IdentifierRow>[] = $derived([
        {
            id: 'delete',
            icon: X,
            label: () => $t('common.remove'),
            variant: 'danger',
            onClick: (row) => removeIdentifierRow(row.id),
        },
    ]);
</script>

<!-- Sub-section: Identifiers -->
<div class="space-y-2">
    <div class="flex items-center justify-between">
        <div class="text-[10px] font-semibold text-lf-muted uppercase tracking-wider">
            {$t('common.identifiers')}
        </div>
        <div class="flex items-center gap-1.5">
            {#if selectedIds.length > 0}
                <DataTableToolbar
                    selectedCount={selectedIds.length}
                    bulkActions={[
                        {
                            id: 'delete',
                            icon: Trash2,
                            label: () => $t('assets.identifiers.deleteSelected'),
                            variant: 'danger',
                            onClick: onbulkdelete,
                        },
                    ]}
                    onClearSelection={() => {
                        selectedIds = [];
                    }}
                />
            {/if}
            <button type="button" onclick={addIdentifierRow} data-testid="asset-modal-add-identifier" class="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded text-lf-muted hover:text-lf-secondary transition-colors" title={$t('assets.identifiers.addIdentifier')}>
                <Plus size={10} /> <span class="hidden sm:inline">{$t('assets.identifiers.addIdentifier')}</span>
            </button>
            <button
                type="button"
                onclick={onaskprovider}
                disabled={!hasProvider || askingProvider}
                class="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded text-lf-muted hover:text-lf-secondary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title={$t('assets.identifiers.askProvider')}
            >
                {#if askingProvider}<Loader2 size={10} class="animate-spin" />{:else}<RefreshCw size={10} />{/if}
                <span class="hidden sm:inline">{$t('assets.identifiers.askProvider')}</span>
            </button>
        </div>
    </div>
    {#if rowsFixed.length > 0}
        <DataTable
            data={rowsFixed}
            columns={identifierColumns}
            getRowId={(r) => r.id}
            storageKey="asset-modal-identifiers"
            enableSelection={true}
            onSelectionChange={(ids) => {
                selectedIds = ids;
            }}
            enablePagination={false}
            enableColumnFilters={false}
            enableSorting={false}
            enableColumnResize={false}
            enableColumnVisibility={false}
            enableActions={true}
            actionsColumnWidth="64px"
            rowActions={identifierRowActions}
            tableLayout="auto"
        />
    {:else}
        <div class="text-xs text-lf-muted italic py-1">{$t('assets.identifiers.askProviderHint')}</div>
    {/if}

    <!-- OTHER / soft identifiers as removable tag badges -->
    <div class="space-y-1 pt-1">
        <div class="flex items-center gap-1">
            <div class="text-[10px] font-medium text-lf-muted">{$t('assets.identifiers.otherLabel')}</div>
            <Tooltip text={$t('assets.identifiers.otherSeparatorsHint')} position="top" maxWidth="320px">
                <Info size={12} class="text-lf-muted cursor-help" />
            </Tooltip>
        </div>
        <TagInput value={otherIdentifiers} onchange={setOtherIdentifiers} placeholder={$t('assets.identifiers.otherPlaceholder')} />
    </div>
</div>
