<script lang="ts">
    /**
     * Broker Detail Page — the Dashboard's page with the broker filter already set (Y6-7, delivery 3).
     *
     * The body — toolbar, report, Overview, Positions (with the lot detail), Risk, Transactions — is `PortfolioView` with
     * `scope: {kind: 'broker', brokerId}`: the same page the Dashboard mounts, counting this broker whole. What is the broker's
     * own is here and goes in as snippets: its identity (header), the Info tab (details and sharing), the Edit and Share
     * buttons, and what writes — New, Import, the selection's bulk actions, the bulk workspace, the import history — for who
     * owns or edits the broker.
     */
    import {page} from '$app/stores';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {goBack} from '$lib/stores/app/navigationStore';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {ArrowLeft, ArrowRightLeft, Briefcase, Copy, Crown, ExternalLink, Eye, FileText, Pencil, Plus, RefreshCw, Share2, Trash2, Upload, Users} from 'lucide-svelte';
    import BrokerModal from '$lib/features/brokers/BrokerModal.svelte';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import BrokerImportFilesModal from '$lib/features/brokers/BrokerImportFilesModal.svelte';
    import BrokerSharingPanel from '$lib/features/brokers/BrokerSharingPanel.svelte';
    import PortfolioView from '$lib/features/portfolio-view/PortfolioView.svelte';
    import TransactionsTable from '$lib/features/transactions/TransactionsTable.svelte';
    import TransactionBulkModal, {type WorkspaceIntent} from '$lib/features/transactions/bulk/TransactionBulkModal.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import DataTableToolbar from '$lib/components/table/DataTableToolbar.svelte';
    import {txStoreSetAll, txStoreCanEdit} from '$lib/features/transactions/txStore.svelte';
    import {guardEditableRows} from '$lib/features/transactions/bulk/selectionGuards';
    import type {TXReadItem} from '$lib/features/transactions/types';
    import type {FilterValue} from '$lib/components/table/types';
    import {buildTransactionsFiltersUrl, applyTransactionColumnFilters} from '$lib/features/transactions/filterState';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {buildTabUrl} from '$lib/utils/url/tabUrl';
    import {goto} from '$app/navigation';
    import type {Broker} from '$lib/types';
    import {safeString} from '$lib/types';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
    import {uiLocaleStore} from '$lib/stores/app/uiLocale';

    let {data}: {data: {brokerId: number}} = $props();

    let broker = $state<Broker | null>(null);
    let loading = $state(true);
    let error = $state<string | null>(null);

    let view = $state<PortfolioView>();
    let editModalOpen = $state(false);
    let importFilesModalOpen = $state(false);

    /** Bulk workspace (create / import) — same engine as /transactions, pre-populated
     *  with this page's broker (still editable, never skips a step). */
    let bulkOpen = $state(false);
    let bulkIntent = $state<WorkspaceIntent | undefined>(undefined);

    /** The rows ticked in the Transactions tab; the bar below shows only to who can edit this broker. */
    let txSelectedRows = $state<TXReadItem[]>([]);
    let txTable = $state<TransactionsTable | undefined>(undefined);
    let txColumnFilters = $state<Record<string, FilterValue>>({});

    const canEdit = $derived(broker ? ['OWNER', 'EDITOR'].includes(safeString(broker.user_role) || '') : false);

    /** The broker as the panels name it. */
    const panelBroker = $derived<BrokerLike | null>(
        broker
            ? {
                  id: broker.id,
                  name: broker.name,
                  icon_url: safeString(broker.icon_url),
                  portal_url: safeString(broker.portal_url),
                  default_import_plugin: safeString(broker.default_import_plugin),
              }
            : null,
    );

    /** Deep-link to the full Transactions page pre-filtered by this broker, the period on screen (the tab keeps to it) and
     *  whatever header column filters are currently active in the embedded table.
     *  Navigating via a plain link registers on the nav stack, so browser Back
     *  returns to this exact broker view (see navigationStore.goBack). */
    function transactionsPageUrl(period: {start: string | undefined; end: string | undefined}): string {
        if (!broker) return '/transactions';
        return buildTransactionsFiltersUrl({...(applyTransactionColumnFilters({}, txColumnFilters) ?? {}), date_start: period.start, date_end: period.end, broker_id: broker.id});
    }

    async function loadBroker() {
        loading = true;
        error = null;

        try {
            // The broker itself and the caller's role on it: the cash and the positions are the portfolio report's
            broker = (await zodiosApi.get_broker_api_v1_brokers__broker_id__get({params: {broker_id: data.brokerId}})) as Broker;
        } catch (e) {
            console.error('Failed to load broker:', e);
            error = $_('brokers.loadFailed');
        } finally {
            loading = false;
        }
    }

    // The first load (the broker, the report, the two lists) is held by the view; the contextual guide starts after it.
    function handleFirstLoaded() {
        if (broker) onboardingGuide.maybeStartContextual('broker_detail_guide');
    }

    function handleBack() {
        goBack('/brokers');
    }

    function openInfoTab() {
        void goto(buildTabUrl($page.url, 'info'), {replaceState: true, noScroll: true});
    }

    async function handleUpdated() {
        await pageBusy.track('broker-reload', loadBroker);
    }

    // ---- what writes -------------------------------------------------------------------------------------------------

    function openImportTransactions() {
        bulkIntent = {action: 'import'};
        bulkOpen = true;
    }

    function openNewTransaction() {
        bulkIntent = {action: 'create'};
        bulkOpen = true;
    }

    /** The bulk workspace from a selection or a row of the Transactions tab (FB-17), as the Transactions page opens it. */
    function openBulkIntent(intent: WorkspaceIntent) {
        bulkIntent = intent;
        bulkOpen = true;
    }

    /** Empty both selections: the table's own (the checkboxes) and this page's (the bar). */
    function clearTxSelection() {
        txTable?.getTableRef()?.clearSelection();
        txSelectedRows = [];
    }

    /** The selected rows the user can edit, with the reason shown when some or all are left out (`selectionGuards.ts`, shared with the Transactions page). */
    function editableTxSelection(): TXReadItem[] | null {
        return guardEditableRows(txSelectedRows, txStoreCanEdit, toasts, $_);
    }

    function editSelectedTx() {
        if (txSelectedRows.length === 0) return;
        const rows = editableTxSelection();
        if (rows) openBulkIntent({action: 'edit', txIds: rows.map((r) => r.id)});
    }

    function cloneSelectedTx() {
        if (txSelectedRows.length === 0) return;
        openBulkIntent({action: 'clone', txIds: txSelectedRows.map((r) => r.id)});
    }

    function deleteSelectedTx() {
        if (txSelectedRows.length === 0) return;
        const rows = editableTxSelection();
        if (rows) openBulkIntent({action: 'delete', txIds: rows.map((r) => r.id)});
    }

    /** The workspace saved something: the rows the selection pointed at may have changed or gone, and the page asks again. */
    async function handleBulkCommitted() {
        clearTxSelection();
        await view?.refresh();
    }

    const txBulkActions = $derived([
        {id: 'edit', icon: Pencil, label: () => $_('common.edit'), onClick: editSelectedTx},
        {id: 'clone', icon: Copy, label: () => $_('transactions.actions.clone'), onClick: cloneSelectedTx},
        {id: 'delete', icon: Trash2, label: () => $_('common.delete'), variant: 'danger' as const, onClick: deleteSelectedTx},
    ]);

    /** What the Transactions tab needs of a page that writes: the actions of the rows show only to who can edit this broker. */
    const transactionsWriter = $derived({
        hideActions: !canEdit,
        onSelectionChange: (rows: TXReadItem[]) => (txSelectedRows = rows),
        onEditRow: (row: TXReadItem) => openBulkIntent({action: 'edit', txIds: [row.id]}),
        onCloneRow: (row: TXReadItem) => openBulkIntent({action: 'clone', txIds: [row.id]}),
        onDeleteRow: (row: TXReadItem) => openBulkIntent({action: 'delete', txIds: [row.id]}),
        onFiltersChange: (filters: Record<string, FilterValue>) => (txColumnFilters = filters),
        // The bulk workspace reads the originals of a selected row from the store (FB-17), as the Transactions page fills it.
        onLoaded: (mainRows: TXReadItem[], partnerRows: TXReadItem[]) => txStoreSetAll(mainRows, partnerRows),
    });

    // ---- formatting ----------------------------------------------------------------------------------------------------

    // In the interface locale (M-18): the template passes `$uiLocaleStore`, read there so it is tracked.
    function formatDate(dateStr: unknown, locale: string): string {
        const str = safeString(dateStr);
        if (!str) return '-';
        return new Date(str).toLocaleDateString(locale, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    }

    function toNumber(value: number | string | (string | null)[] | null | undefined): number {
        if (Array.isArray(value)) return value[0] ? Number(value[0]) : 0;
        if (typeof value === 'number') return value;
        if (typeof value === 'string') return Number(value);
        return 0;
    }

    function formatSharePercentage(value: number | string | (string | null)[] | null | undefined, locale: string): string {
        return formatPercent(Math.round(toNumber(value) * 10000) / 100, {signed: false, digits: 1, locale});
    }
</script>

<PortfolioView bind:this={view} bind:transactionsTable={txTable} scope={{kind: 'broker', brokerId: data.brokerId}} broker={panelBroker} gated={!broker} extraLoad={loadBroker} onFirstLoaded={handleFirstLoaded} {actionsBefore} {header} {gate} {infoTab} {transactionsBar} {transactionsWriter} />

{#snippet header()}
    <div class="flex items-center space-x-4" use:guideAnchor={'broker.detail.header'} data-testid="broker-detail-header">
        <button class="p-2 text-lf-muted hover:text-lf-link hover:bg-lf-selected rounded-lg transition-colors" data-testid="broker-back-button" onclick={handleBack} title={$_('common.back')}>
            <ArrowLeft size={20} />
        </button>

        {#if broker}
            <BrokerIcon brokerId={broker.id} iconUrl={safeString(broker.icon_url)} portalUrl={safeString(broker.portal_url)} pluginCode={safeString(broker.default_import_plugin)} altText={broker.name} size="lg" />

            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                    {#if safeString(broker.user_role)}
                        {@const role = safeString(broker.user_role)}
                        <!-- colour: closest role, to review: broker role badge (owner amber, editor blue, viewer grey) on warning, info and neutral tints -->
                        <span
                            class="inline-flex items-center gap-1 px-2 py-1 rounded-full flex-shrink-0
                            {role === 'OWNER' ? 'bg-lf-warning-soft text-lf-warning-on-soft' : role === 'EDITOR' ? 'bg-lf-info-soft text-lf-info-on-soft' : 'bg-lf-neutral text-lf-secondary'}"
                            title={$_(role === 'OWNER' ? 'brokers.sharing.roleOwnerShort' : role === 'EDITOR' ? 'brokers.sharing.roleEditorShort' : 'brokers.sharing.roleViewerShort')}
                            data-testid="broker-quota-badge"
                        >
                            {#if broker.user_share_percentage != null}
                                <span class="text-xs font-medium">{formatSharePercentage(broker.user_share_percentage, $uiLocaleStore)}</span>
                            {/if}
                            {#if role === 'OWNER'}<Crown size={13} />{:else if role === 'EDITOR'}<Pencil size={13} />{:else}<Eye size={13} />{/if}
                        </span>
                    {/if}
                    <h1 class="text-2xl font-bold text-lf-primary truncate" data-testid="broker-name">{broker.name}</h1>
                </div>
                {#if broker.description}
                    <p class="text-lf-muted text-sm truncate" data-testid="broker-description">{broker.description}</p>
                {/if}
            </div>

            {#if safeString(broker.portal_url)}
                <a href={safeString(broker.portal_url)} target="_blank" rel="noopener noreferrer" class="flex items-center justify-center p-2 text-lf-muted hover:text-lf-link hover:bg-lf-selected rounded-lg transition-colors flex-shrink-0" title={$_('brokers.openPortal')}>
                    <ExternalLink size={20} />
                </a>
            {/if}
        {:else if !error}
            <div class="flex-1">
                <div class="h-8 w-48 bg-lf-neutral rounded animate-pulse"></div>
            </div>
        {/if}
    </div>
{/snippet}

<!-- What stands in place of the toolbar and the tabs until the broker is loaded: its loading, or its failure. -->
{#snippet gate()}
    {#if error}
        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card p-12 text-center border border-lf-danger-line">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-lf-danger-soft rounded-full mb-4">
                <Briefcase class="text-lf-danger" size={32} />
            </div>
            <h3 class="text-lg font-semibold text-lf-secondary mb-2">{$_('common.error')}</h3>
            <p class="text-lf-muted mb-4">{error}</p>
            <button onclick={() => view?.refresh()} class="px-4 py-2 bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors">
                {$_('common.retry')}
            </button>
        </div>
    {:else}
        <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card p-12 text-center border border-lf-subtle">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-lf-selected rounded-full mb-4">
                <RefreshCw class="text-lf-link animate-spin" size={32} />
            </div>
            <p class="text-lf-muted">{$_('common.loading')}</p>
        </div>
    {/if}
{/snippet}

{#snippet actionsBefore({showActionLabels}: {showActionLabels: boolean})}
    {#if canEdit}
        <button onclick={() => (editModalOpen = true)} class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors" data-testid="broker-edit-button">
            <Pencil size={14} />
            {#if showActionLabels}<span>{$_('common.edit')}</span>{/if}
        </button>
    {/if}
    <button onclick={openInfoTab} class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg hover:bg-lf-hover text-lf-secondary transition-colors" data-testid="broker-share-button" title={$_('brokers.sharing.title')}>
        <Share2 size={14} />
        {#if showActionLabels}<span>{$_('brokers.sharing.title')}</span>{/if}
    </button>
{/snippet}

{#snippet transactionsBar({table, period}: {table: TransactionsTable | undefined; period: {start: string | undefined; end: string | undefined}})}
    <div class="flex flex-wrap items-center justify-between gap-2" data-testid="broker-transactions-actions">
        <div class="flex items-center gap-2">
            <button class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-all" onclick={() => (importFilesModalOpen = true)} data-testid="broker-show-import-history">
                <FileText size={15} />
                <span class="hidden sm:inline">{$_('brokers.showImportHistory')}</span>
            </button>
            <a href={transactionsPageUrl(period)} class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-all" title={$_('brokers.viewInTransactionsHint')} data-testid="broker-view-in-transactions">
                <ArrowRightLeft size={15} />
                <span class="hidden sm:inline">{$_('brokers.viewInTransactions')}</span>
            </a>
        </div>
        <div class="flex items-center gap-2">
            {#if canEdit && txSelectedRows.length > 0}
                <DataTableToolbar selectedCount={txSelectedRows.length} bulkActions={txBulkActions} onClearSelection={clearTxSelection} />
            {/if}
            <ColumnVisibilityToggle tableRef={table?.getTableRef()} />
            {#if canEdit}
                <button class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-all" onclick={openImportTransactions} data-testid="broker-import-transactions">
                    <Upload size={15} />
                    <span class="hidden sm:inline">{$_('common.import')}</span>
                </button>
                <button class="flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-all" onclick={openNewTransaction} data-testid="broker-new-transaction">
                    <Plus size={15} />
                    <span class="hidden sm:inline">{$_('transactions.addTransaction')}</span>
                </button>
            {/if}
        </div>
    </div>
{/snippet}

{#snippet infoTab()}
    {#if broker}
        <div class="grid grid-cols-1 xl:grid-cols-2 gap-4" data-testid="broker-info-tab">
            <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-4" data-testid="broker-metadata">
                <h3 class="font-semibold text-lf-secondary mb-3">{$_('brokers.metadata')}</h3>
                <div class="space-y-2 text-sm">
                    <div class="flex justify-between">
                        <span class="text-lf-muted">{$_('brokers.isActive')}</span>
                        <span class="font-medium {broker.is_active ? 'text-lf-success' : 'text-lf-danger'}">
                            {broker.is_active ? '✓ Active' : '✗ Closed'}
                        </span>
                    </div>
                    {#if safeString(broker.opened_at)}
                        <div class="flex justify-between">
                            <span class="text-lf-muted">{$_('brokers.openedAt')}</span>
                            <span class="text-lf-secondary">{formatDate(broker.opened_at, $uiLocaleStore)}</span>
                        </div>
                    {/if}
                    <div class="flex justify-between">
                        <span class="text-lf-muted">{$_('brokers.allowOverdraft')}</span>
                        <span class="font-medium {broker.allow_cash_overdraft ? 'text-lf-success' : 'text-lf-muted'}">
                            {broker.allow_cash_overdraft ? '✓' : '✗'}
                        </span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-lf-muted">{$_('brokers.allowShorting')}</span>
                        <span class="font-medium {broker.allow_asset_shorting ? 'text-lf-success' : 'text-lf-muted'}">
                            {broker.allow_asset_shorting ? '✓' : '✗'}
                        </span>
                    </div>
                    <div class="flex justify-between border-t border-lf-subtle pt-2 mt-2">
                        <span class="text-lf-muted">{$_('brokers.createdInSystem')}</span>
                        <span class="text-lf-secondary">{formatDate(broker.created_at, $uiLocaleStore)}</span>
                    </div>
                </div>
            </div>

            <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-4" data-testid="broker-sharing-section">
                <h3 class="font-semibold text-lf-secondary mb-3 flex items-center gap-2">
                    <Users size={18} class="text-lf-link" />
                    {$_('brokers.sharing.title')}
                </h3>
                <BrokerSharingPanel brokerId={broker.id} readOnly={safeString(broker.user_role) !== 'OWNER'} onChanged={handleUpdated} />
            </div>
        </div>
    {/if}
{/snippet}

{#if broker}
    <BrokerModal
        isOpen={editModalOpen}
        mode="edit"
        brokerId={broker.id}
        initialData={{
            name: broker.name,
            description: safeString(broker.description),
            portal_url: safeString(broker.portal_url),
            icon_url: safeString(broker.icon_url),
            default_import_plugin: safeString(broker.default_import_plugin),
            allow_cash_overdraft: broker.allow_cash_overdraft,
            allow_asset_shorting: broker.allow_asset_shorting,
            is_active: broker.is_active,
            opened_at: safeString(broker.opened_at),
        }}
        onclose={() => (editModalOpen = false)}
        onupdated={handleUpdated}
    />

    <TransactionBulkModal
        open={bulkOpen}
        intent={bulkIntent}
        defaultBrokerId={broker.id}
        onClose={() => {
            bulkOpen = false;
            bulkIntent = undefined;
        }}
        onCommitted={handleBulkCommitted}
    />

    <BrokerImportFilesModal open={importFilesModalOpen} brokerId={broker.id} brokerName={broker.name} onClose={() => (importFilesModalOpen = false)} />
{/if}
