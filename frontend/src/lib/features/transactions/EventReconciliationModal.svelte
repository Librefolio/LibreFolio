<!--
  EventReconciliationModal.svelte — «Relink events» (lot X5-3: N68; FB-19; plan 77 SEL-C, the A4 design).

  Lists the transactions that could link an asset event and have none (a currency change deletes an asset's events, so the
  transactions linked to them lose the link; a dividend booked before its event was synced has none either), with what the
  server found for each (`GET /transactions/event-reconciliation`, read by `eventReconciliation.ts`). One `DataTable` per
  status, each under its own header with its «all» action:
    - `unique` («With one event»): exactly one event of the same asset the SAME DAY, of the corresponding type → «Link»
      (one row, the selection, or «Link all» of the rows the group's filters leave);
    - `none` («Without an event»): no event that day → «Create event» (one row, the selection, or «Create all»): the dialog
      `EventReconciliationCreateModal.svelte` creates what they miss, and the rows then have an event to link;
    - `several` («Several events»): more than one event that day → never guessed: «Choose event» opens
      `EventReconciliationChooseModal.svelte`, where the user picks one. These rows take no checkbox.
  One selection covers the two selectable tables: its bar sits at the top of the window and comes down into the dock when
  the top scrolls out of view (`SelectionPanel`); each action says how many rows it takes and acts on those only. Each row's
  action is in the column pinned on the right and in the table's right-click menu.
  Nothing is linked on its own. A link is the commit the app already uses (`updates: [{id, asset_event_id}]`, atomic: any
  refusal links nothing and the rows stay).

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {CalendarCheck, CalendarPlus, CalendarSearch, CalendarSync, CalendarX, Link2, ListChecks, X} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import SelectionPanel from '$lib/components/table/SelectionPanel.svelte';
    import {selectionToolbarActions} from '$lib/components/table/selectionActions';
    import type {BulkAction, ColumnDef, RowAction} from '$lib/components/table/types';
    import {getAssetInfo, assetStoreVersion} from '$lib/stores/reference/assetStore';
    import {getBrokerInfo, brokerStoreVersion} from '$lib/stores/reference/brokerStore';
    import {currencyStoreVersion} from '$lib/stores/reference/currencyStore';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {formatExactDecimal} from '$lib/utils/core/formatFixed';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
    import {ensureTypesLoaded, getEventTypeEmoji, getTransactionTypeIconUrl, typesVersion} from '$lib/features/transactions/transactionTypeStore';
    import EventReconciliationCreateModal from './EventReconciliationCreateModal.svelte';
    import EventReconciliationChooseModal from './EventReconciliationChooseModal.svelte';
    import EventReconciliationRowButton from './EventReconciliationRowButton.svelte';
    import {eventTypesOfRow, eventTypeToShow, eventValueHtml, linkReconciliation, loadEventReconciliation, uniqueRows, type ReconciliationFilters, type ReconciliationRow, type ReconciliationStatus} from './eventReconciliation';

    interface Props {
        open: boolean;
        /** Only the transactions of this broker / asset (none: everything the user may link). */
        filters?: ReconciliationFilters;
        zIndex?: number;
        onclose?: () => void;
        /** Called after rows were linked, so the page can reload its transactions. */
        onlinked?: () => void;
    }

    let {open = $bindable(), filters, zIndex = 50, onclose, onlinked}: Props = $props();

    const STATUSES: readonly ReconciliationStatus[] = ['unique', 'none', 'several'];

    let rows = $state<ReconciliationRow[]>([]);
    /** The rows as the list was read: the filters' options come from them, not from the rows that are left, so that a filter set on an
     * asset whose rows were all linked can still be taken off. */
    let optionRows = $state<ReconciliationRow[]>([]);
    let loading = $state(false);
    let loadFailed = $state(false);
    let linkFailed = $state(false);
    /** A link is on its way: no second commit meanwhile (row button, menu, bar, «all»). */
    let linking = $state(false);
    /** Bumped on every load, so an answer that arrives after a close or a newer load is ignored. */
    let generation = 0;

    /** Each group's rows, as read (a group with none is not drawn; one its filter empties stays, to take the filter off). */
    let byStatus = $derived(Object.fromEntries(STATUSES.map((status) => [status, rows.filter((row) => row.status === status)])) as Record<ReconciliationStatus, ReconciliationRow[]>);
    /** The rows each table's column filters leave, in display order (`null` before the table reports): its «all» acts on them. */
    let displayedIds = $state<Record<ReconciliationStatus, string[] | null>>({unique: null, none: null, several: null});
    function displayedOf(status: ReconciliationStatus): ReconciliationRow[] {
        const ids = displayedIds[status];
        return ids === null ? byStatus[status] : byStatus[status].filter((row) => ids.includes(String(row.transactionId)));
    }
    let linkAllRows = $derived(uniqueRows(displayedOf('unique')));
    let createAllRows = $derived(displayedOf('none'));

    /** The selection: one per selectable table, read together; the rows are the live ones, so a linked row leaves it. */
    /** Below 640 px the row's button shows only its icon, so its column can be narrower. */
    let phone = $state(false);
    $effect(() => {
        if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
        const query = window.matchMedia('(max-width: 639px)');
        phone = query.matches;
        const follow = (event: MediaQueryListEvent) => (phone = event.matches);
        query.addEventListener('change', follow);
        return () => query.removeEventListener('change', follow);
    });

    let selectedIds = $state<Record<'unique' | 'none', string[]>>({unique: [], none: []});
    let tables = $state<Partial<Record<ReconciliationStatus, DataTable<ReconciliationRow>>>>({});
    let selectedRows = $derived(rows.filter((row) => (row.status === 'unique' || row.status === 'none') && selectedIds[row.status].includes(String(row.transactionId))));

    /** The rows the creation dialog is open for (none: closed), and the row «Choose event» is open for. */
    let creating = $state<ReconciliationRow[] | null>(null);
    let choosing = $state<ReconciliationRow | null>(null);

    /** Read the list. `quiet` keeps the tables on screen (and their selection) while it is read again; it answers the rows read, `null` when the
     * read failed or a close or a newer read overtook it. */
    async function load(quiet = false): Promise<ReconciliationRow[] | null> {
        const mine = ++generation;
        if (!quiet) loading = true;
        loadFailed = false;
        linkFailed = false;
        try {
            const loaded = await loadEventReconciliation(filters);
            if (mine !== generation) return null;
            rows = loaded;
            optionRows = loaded;
            return loaded;
        } catch (error) {
            if (mine !== generation) return null;
            console.error('[event-reconciliation] could not read the transactions without an event', error);
            rows = [];
            loadFailed = true;
            return null;
        } finally {
            if (mine === generation) loading = false;
        }
    }

    // Open → read the list; closed → forget it (a reopening starts from the server's answer).
    $effect(() => {
        if (open) {
            // The events' emojis come from the types the server lists: asked here too, for a page that has not
            ensureTypesLoaded().catch((error) => console.warn('[event-reconciliation] the event types could not be read: the emoji stay generic', error));
            void load();
        } else {
            generation++;
            rows = [];
            optionRows = [];
            loading = false;
            loadFailed = false;
            linkFailed = false;
            displayedIds = {unique: null, none: null, several: null};
            selectedIds = {unique: [], none: []};
            creating = null;
            choosing = null;
        }
    });

    /** The rows leave the list and the selection; the other selected rows stay selected, ready for the next step (77
     *  SEL-C, the designer's (b): after «Link 1» the bar keeps «Create event 2»). */
    function removeRows(done: ReadonlySet<number>) {
        for (const status of ['unique', 'none'] as const) {
            for (const id of selectedIds[status]) if (done.has(Number(id))) tables[status]?.toggleRowSelectionById(id);
        }
        rows = rows.filter((row) => !done.has(row.transactionId));
    }

    /** Link `toLink` in one commit; on success they leave the list. */
    async function link(toLink: ReconciliationRow[]) {
        const linkable = uniqueRows(toLink);
        if (linking || linkable.length === 0) return;
        linking = true;
        linkFailed = false;
        try {
            const outcome = await linkReconciliation(linkable);
            if (!outcome.linked) {
                linkFailed = true;
                return;
            }
            removeRows(new Set(linkable.map((row) => row.transactionId)));
            onlinked?.();
        } finally {
            linking = false;
        }
    }

    function close() {
        open = false;
        onclose?.();
    }

    /** The asset's name when the shared cache has it, else its id. */
    function assetName(assetId: number): string {
        void $assetStoreVersion;
        return getAssetInfo(assetId)?.display_name ?? `#${assetId}`;
    }

    /** The broker's name when the shared cache has it, else its id. */
    function brokerName(brokerId: number): string {
        void $brokerStoreVersion;
        return getBrokerInfo(brokerId)?.name ?? `#${brokerId}`;
    }

    function typeLabel(type: string): string {
        void $typesVersion;
        return `${getEventTypeEmoji(type)} ${$t(`assetDetail.eventType.${type}`) || type}`;
    }

    /** The event a row is about, for the filter: the type the server found, or the one its transaction asks for; an adjustment with no event yet keeps its own type. */
    function eventCode(row: ReconciliationRow): string {
        return eventTypeToShow(row) ?? row.type;
    }

    /** The event types a row's line names: the candidates' (distinct), else the ones its transaction can take. */
    function eventTypesNamed(row: ReconciliationRow): string[] {
        return row.candidates.length > 0 ? [...new Set(row.candidates.map((candidate) => candidate.type))] : [...eventTypesOfRow(row)];
    }

    /** The transaction's movement: its type's icon, then its cash, or its quantity when it has no cash. */
    function movementHtml(row: ReconciliationRow): string {
        void $currencyStoreVersion;
        const icon = `<img src="${escapeHtml(getTransactionTypeIconUrl(row.type))}" alt="" class="w-5 h-5 object-contain shrink-0" />`;
        const cash = Number(row.amount);
        let value: string;
        if (row.currency && cash !== 0) value = formatCurrencyAmountHtml(cash, row.currency, {showSign: true});
        else if (Number(row.quantity) !== 0) {
            const quantity = formatExactDecimal(row.quantity);
            const signed = Number(row.quantity) > 0 ? `+${quantity}` : quantity;
            value = `<span class="currency-amount">${escapeHtml($t('transactions.reconcile.quantityUnits', {values: {n: signed}}))}</span>`;
        } else value = '—';
        return `<span class="inline-flex items-center justify-end gap-1.5 whitespace-nowrap">${icon}${value}</span>`;
    }

    function distinct<T>(values: T[]): T[] {
        return [...new Set(values)];
    }

    const EVENT_HEADER: Record<ReconciliationStatus, string> = {unique: 'transactions.reconcile.colEventFound', none: 'transactions.reconcile.colEventToCreate', several: 'transactions.reconcile.colEventsThatDay'};

    /** The event cell: what it is (emoji and name), and under it its value, what will happen, or how many there are. */
    function eventCell(row: ReconciliationRow): string {
        const types = eventTypesNamed(row);
        const line1 = `<span data-event-type="${escapeHtml(eventCode(row))}">${types.map((type) => escapeHtml(typeLabel(type))).join(` ${escapeHtml($t('transactions.reconcile.or'))} `)}</span>`;
        let line2: string;
        if (row.status === 'unique') line2 = eventValueHtml(row.candidates[0]);
        else if (row.status === 'none') line2 = escapeHtml(types.length > 1 ? $t('transactions.reconcile.toCreateChooseType') : $t('transactions.reconcile.toCreate'));
        else line2 = escapeHtml($t('transactions.reconcile.severalSub', {values: {n: row.candidates.length}}));
        return `<span class="inline-flex flex-col leading-snug"><span class="whitespace-normal">${line1}</span><span class="text-xs text-lf-muted whitespace-nowrap">${line2}</span></span>`;
    }

    /** The row's one action: the pinned button and the right-click menu do the same. */
    function rowActionOf(status: ReconciliationStatus): {icon: typeof Link2; label: () => string; testId: (row: ReconciliationRow) => string; run: (row: ReconciliationRow) => void} {
        if (status === 'unique') return {icon: Link2, label: () => $t('transactions.reconcile.link'), testId: (row) => `event-reconciliation-link-${row.transactionId}`, run: (row) => void link([row])};
        if (status === 'none') return {icon: CalendarPlus, label: () => $t('transactions.reconcile.createOne'), testId: (row) => `event-reconciliation-create-${row.transactionId}`, run: (row) => openCreate([row])};
        return {icon: ListChecks, label: () => $t('transactions.reconcile.choose'), testId: (row) => `event-reconciliation-choose-${row.transactionId}`, run: (row) => (choosing = row)};
    }

    function rowActions(status: ReconciliationStatus): RowAction<ReconciliationRow>[] {
        const action = rowActionOf(status);
        return [{id: `reconcile-${status}`, icon: action.icon, label: action.label, onClick: (row) => action.run(row), blocked: () => (linking ? {hint: () => $t('transactions.reconcile.linkingBusy'), reason: 'linking'} : null)}];
    }

    function columnsFor(status: ReconciliationStatus): ColumnDef<ReconciliationRow>[] {
        const options = optionRows.filter((row) => row.status === status);
        const filterable = status !== 'several';
        const action = rowActionOf(status);
        return [
            {
                id: 'transaction',
                header: () => $t('transactions.reconcile.colTransaction'),
                width: 200,
                minWidth: 120,
                type: 'enum',
                filterable,
                getValue: (row) => String(row.assetId),
                enumOptions: distinct(options.map((row) => row.assetId)).map((id) => ({value: String(id), label: assetName(id)})),
                cell: (row) => ({
                    type: 'html',
                    html: `<span class="inline-flex flex-col leading-snug" data-testid="event-reconciliation-row-${row.transactionId}" data-status="${row.status}" data-candidate-count="${row.candidates.length}"><span class="text-lf-primary">${escapeHtml(assetName(row.assetId))}</span><span class="text-xs text-lf-muted">${escapeHtml(brokerName(row.brokerId))}</span></span>`,
                }),
            },
            {id: 'date', header: () => $t('common.date'), width: 120, minWidth: 96, type: 'date', filterable: false, getValue: (row) => row.date, cell: (row) => formatDay(row.date)},
            {id: 'movement', header: () => $t('transactions.reconcile.colMovement'), width: 150, minWidth: 110, type: 'number', align: 'right', filterable: false, getValue: (row) => Number(row.amount), cell: (row) => ({type: 'html', html: movementHtml(row)})},
            {
                id: 'event',
                header: () => $t(EVENT_HEADER[status]),
                width: 300,
                minWidth: 180,
                type: 'enum',
                filterable,
                getValue: (row) => eventCode(row),
                enumOptions: distinct(options.map((row) => eventCode(row))).map((code) => ({value: code, label: typeLabel(code)})),
                cell: (row) => ({type: 'html', html: eventCell(row)}),
            },
            {
                id: 'action',
                header: '',
                displayName: () => $t('transactions.reconcile.colAction'),
                width: 140,
                // The button keeps its word above 640 px, only its icon below (EventReconciliationRowButton).
                minWidth: phone ? 44 : 128,
                type: 'text',
                sortable: false,
                filterable: false,
                pinned: 'right',
                cell: (row) => ({type: 'custom', component: EventReconciliationRowButton, props: {icon: action.icon, label: action.label(), testId: action.testId(row), disabled: linking, onClick: () => action.run(row)}}),
            },
        ];
    }

    /** Open the creation dialog for the rows that miss their event (the `none` ones). */
    function openCreate(candidates: ReconciliationRow[]) {
        const missing = candidates.filter((row) => row.status === 'none');
        if (missing.length > 0) creating = missing;
    }

    /** The events were created (81 U23): read the list again, where the rows asked for now have their event, and link — in one commit — the
     *  ones that came back with exactly one. A row that came back with several is never guessed (it stays, to be chosen), and the rows
     *  nobody asked to create keep their own «Link». If the link is refused the events stay, the banner tells it, and the rows are
     *  «With one event» now. The created rows leave the selection; the other selected rows stay (77 SEL-C (b)). */
    async function created() {
        const asked = creating ?? [];
        creating = null;
        for (const row of asked) {
            const id = String(row.transactionId);
            if (selectedIds.none.includes(id)) tables.none?.toggleRowSelectionById(id);
        }
        const loaded = await load(true);
        if (loaded === null) return;
        const askedIds = new Set(asked.map((row) => row.transactionId));
        await link(loaded.filter((row) => askedIds.has(row.transactionId)));
    }

    /** The chosen event was linked: the row leaves the list. */
    function chosenLinked(row: ReconciliationRow) {
        choosing = null;
        removeRows(new Set([row.transactionId]));
        onlinked?.();
    }

    function clearSelection() {
        tables.unique?.clearSelection();
        tables.none?.clearSelection();
    }

    /** The selection's actions, by the rule (77): each shows only when a selected row can take it, with its number, and acts on those rows. */
    let selectionActions = $derived<BulkAction<ReconciliationRow>[]>([
        {id: 'link', icon: Link2, label: () => $t('transactions.reconcile.link'), primary: true, appliesTo: (row) => uniqueRows([row]).length === 1, onClick: (picked) => void link(picked)},
        {id: 'create', icon: CalendarPlus, label: () => $t('transactions.reconcile.createOne'), appliesTo: (row) => row.status === 'none', onClick: (picked) => openCreate(picked)},
    ]);
    let panelActions = $derived(selectionToolbarActions(selectionActions, selectedRows));

    const GROUP: Record<ReconciliationStatus, {icon: typeof Link2; tone: string}> = {
        unique: {icon: CalendarCheck, tone: 'bg-lf-success-soft text-lf-success-on-soft border-lf-success-line'},
        none: {icon: CalendarX, tone: 'bg-lf-warning-soft text-lf-warning-on-soft border-lf-warning-line'},
        several: {icon: CalendarSearch, tone: 'bg-lf-info-soft text-lf-info-on-soft border-lf-info-line'},
    };
</script>

{#snippet group(status: ReconciliationStatus)}
    {@const meta = GROUP[status]}
    {@const GroupIcon = meta.icon}
    <section class="space-y-2" data-testid="event-reconciliation-group-{status}" data-count={byStatus[status].length}>
        <div class="flex flex-wrap items-center gap-2">
            <span class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[13px] font-medium {meta.tone}">
                <GroupIcon size={14} />
                {$t(`transactions.reconcile.group.${status}.title`, {values: {n: byStatus[status].length}})}
            </span>
            <span class="flex-1 min-w-40 text-xs text-lf-muted">{$t(`transactions.reconcile.group.${status}.sub`)}</span>
            {#if status === 'unique'}
                <button
                    type="button"
                    class="all-btn inline-flex items-center gap-1.5 rounded-lg border border-lf-input bg-lf-card text-lf-primary hover:bg-lf-hover text-[13px] font-medium whitespace-nowrap transition-colors disabled:opacity-50"
                    disabled={linking || linkAllRows.length === 0}
                    onclick={() => void link(linkAllRows)}
                    data-testid="event-reconciliation-group-unique-all"
                >
                    <Link2 size={15} />
                    <span class="lbl-long">{$t('transactions.reconcile.linkAllGroup')}</span>
                    <span class="lbl-short">{$t('transactions.reconcile.link')}</span>
                    <span class="n" data-testid="event-reconciliation-group-unique-all-count">{linkAllRows.length}</span>
                </button>
            {:else if status === 'none'}
                <button
                    type="button"
                    class="all-btn inline-flex items-center gap-1.5 rounded-lg border border-lf-input bg-lf-card text-lf-primary hover:bg-lf-hover text-[13px] font-medium whitespace-nowrap transition-colors disabled:opacity-50"
                    disabled={linking || createAllRows.length === 0}
                    onclick={() => openCreate(createAllRows)}
                    data-testid="event-reconciliation-group-none-all"
                >
                    <CalendarPlus size={15} />
                    <span class="lbl-long">{$t('transactions.reconcile.createAllGroup')}</span>
                    <span class="lbl-short">{$t('transactions.reconcile.createShort')}</span>
                    <span class="n" data-testid="event-reconciliation-group-none-all-count">{createAllRows.length}</span>
                </button>
            {/if}
        </div>
        <div data-testid="event-reconciliation-table-{status}">
            <DataTable
                bind:this={tables[status]}
                data={byStatus[status]}
                columns={columnsFor(status)}
                getRowId={(row) => String(row.transactionId)}
                storageKey="event-reconciliation-{status}"
                enableSelection={status !== 'several'}
                selectionMode={status !== 'several' ? 'multi' : 'none'}
                onSelectionChange={status === 'several' ? undefined : (ids) => (selectedIds = {...selectedIds, [status]: ids})}
                enableActions={false}
                rowActions={rowActions(status)}
                enableSorting={true}
                enableColumnFilters={status !== 'several'}
                enableColumnResize={false}
                enablePagination={false}
                enableColumnVisibility={false}
                tableLayout="auto"
                onRowOrderChange={(ids) => (displayedIds = {...displayedIds, [status]: ids})}
            />
        </div>
    </section>
{/snippet}

{#if open}
    <ModalBase {open} {zIndex} maxWidth="5xl" onRequestClose={close} testId="event-reconciliation-modal" labelledBy="event-reconciliation-title">
        <div class="flex items-center gap-3 px-5 py-4 border-b border-lf-subtle">
            <CalendarSync class="text-lf-link flex-shrink-0" size={20} />
            <h2 id="event-reconciliation-title" class="text-base font-semibold text-lf-primary">{$t('transactions.reconcile.title')}</h2>
            <button type="button" class="ml-auto p-1 rounded text-lf-muted hover:bg-lf-hover transition-colors" onclick={close} aria-label={$t('transactions.reconcile.close')} data-testid="event-reconciliation-close">
                <X size={18} />
            </button>
        </div>

        <div class="px-5 py-4 space-y-4 text-sm text-lf-primary overflow-y-auto" data-testid="event-reconciliation-body">
            <p class="text-lf-secondary">{$t('transactions.reconcile.introShort')}</p>

            {#if loading}
                <p class="text-lf-muted" data-testid="event-reconciliation-loading">{$t('transactions.reconcile.loading')}</p>
            {:else if loadFailed}
                <p class="text-lf-danger" data-testid="event-reconciliation-error">{$t('transactions.reconcile.loadError')}</p>
            {:else if rows.length === 0}
                <p class="text-lf-muted" data-testid="event-reconciliation-empty">{$t('transactions.reconcile.empty')}</p>
            {:else}
                {#if linkFailed}
                    <p class="text-lf-danger" data-testid="event-reconciliation-error">{$t('transactions.reconcile.linkError')}</p>
                {/if}
                <SelectionPanel actions={panelActions} selectedCount={selectedRows.length} hint={$t('transactions.reconcile.selectionHint')} onClearSelection={clearSelection}>
                    <div class="space-y-5">
                        {#each STATUSES as status (status)}
                            {#if byStatus[status].length > 0}
                                {@render group(status)}
                            {/if}
                        {/each}
                    </div>
                </SelectionPanel>
            {/if}
        </div>

        <div class="flex justify-end gap-2 px-5 py-3 border-t border-lf-subtle bg-lf-panel">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover transition-colors" onclick={close} data-testid="event-reconciliation-done">{$t('transactions.reconcile.close')}</button>
        </div>
    </ModalBase>

    <EventReconciliationCreateModal open={creating !== null} rows={creating ?? []} zIndex={zIndex + 10} onclose={() => (creating = null)} oncreated={created} />
    <EventReconciliationChooseModal
        row={choosing}
        assetName={choosing ? assetName(choosing.assetId) : ''}
        brokerName={choosing ? brokerName(choosing.brokerId) : ''}
        movementHtml={choosing ? movementHtml(choosing) : ''}
        zIndex={zIndex + 10}
        onclose={() => (choosing = null)}
        onlinked={chosenLinked}
    />
{/if}

<style>
    .all-btn {
        height: 30px;
        padding: 0 0.625rem;
    }

    .all-btn .n {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 18px;
        height: 18px;
        padding: 0 5px;
        border-radius: 9999px;
        font-size: 0.6875rem;
        font-weight: 600;
        background: var(--lf-surface-panel);
        color: var(--lf-text-secondary);
    }

    .lbl-short {
        display: none;
    }

    @media (max-width: 639px) {
        .lbl-long {
            display: none;
        }

        .lbl-short {
            display: inline;
        }
    }
</style>
