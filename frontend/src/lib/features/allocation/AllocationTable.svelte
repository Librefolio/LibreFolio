<!--
  AllocationTable — the slices of the base as a table (lane 80, F3): the slice, its amount, its share of the selection, its share
  of the portfolio and how many assets make it up. What is excluded stays at the bottom, struck, with no share.

  A click on a slice opens it in place: the assets that make it up, each with its amount and its share of the slice (no modal).
  Everything is the backend's; a share it did not send (base at or below zero) shows as «—». Amounts are personal money:
  masked with the privacy toggle (the columns are built again when it flips, so the cells follow it), the percentages stay.

  Built on `DataTable` with the table's own helpers switched off (no sorting, filters, paging or selection): the order is the
  backend's, largest first, and a detail row sits under its slice.

  Test ids: `{testId}` (root, with `data-dimension`) and `{testId}-hint`; the rows are `DataTable`'s `tr[data-row-id]`, whose id says what
  they are: `slice:<bucket>`, `detail:<bucket>:<asset id>`, `excluded:bucket:<bucket>`, `excluded:asset:<id>`, `excluded:fixed:<reason>`.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {CellContent, ColumnDef} from '$lib/components/table/types';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {isPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
    import {ensureCountriesLoaded, getCountryInfo} from '$lib/stores/reference/countryStore';
    import {ensureSectorsLoaded, getSectorEmoji, sectorEmojiVersion} from '$lib/stores/reference/sectorStore';
    import type {AllocationResponse} from './allocationQuery';
    import {assetNamesOf, tableRows, type AllocationRow} from './allocationView';
    import {assetLabel, COMPACT_MONEY, sliceLabel, type RowLabel, type Translate} from './allocationLabels';

    interface Props {
        view: AllocationResponse;
        testId: string;
    }

    let {view, testId}: Props = $props();

    let expanded = $state<ReadonlySet<string>>(new Set());

    // The country and sector names arrive from the stores: ask for them, and read their version so the labels are drawn again.
    $effect(() => {
        void ensureCountriesLoaded();
        void ensureSectorsLoaded();
    });
    const sectorVersion = $derived(sectorEmojiVersion());

    const rows = $derived(tableRows(view, expanded));
    const names = $derived(assetNamesOf(view));
    const t = (key: string, options?: Parameters<Translate>[1]) => $_(key, options as never);

    function toggle(row: AllocationRow): void {
        if (row.kind !== 'slice' || !row.expandable) return;
        const next = new Set(expanded);
        if (next.has(row.key)) next.delete(row.key);
        else next.add(row.key);
        expanded = next;
    }

    const percent = (value: string | null | undefined) => (value == null ? '—' : formatPercent(parseFloat(value), {digits: 1, signed: false}));

    function labelOf(row: AllocationRow): RowLabel {
        const deps = {t, assetNames: names, country: getCountryInfo, sectorEmoji: getSectorEmoji};
        if (row.kind === 'detail') return assetLabel(deps, row.assetId as number);
        if (row.kind === 'excluded') {
            if (row.excluded === 'asset') return assetLabel(deps, row.assetId as number);
            if (row.excluded === 'unattributable') return {text: t(`allocation.unattributable.${row.key}`)};
            return sliceLabel(deps, view.dimension === 'asset' ? 'sector' : view.dimension, row.key);
        }
        return sliceLabel(deps, view.dimension, row.key, row.assetId);
    }

    function labelHtml(row: AllocationRow): string {
        const label = labelOf(row);
        const lead = label.iconUrl ? `<img src="${escapeHtml(label.iconUrl)}" alt="" class="inline-block h-4 w-4 object-contain align-text-bottom" /> ` : label.glyph ? `<span class="emoji-flag">${escapeHtml(label.glyph)}</span> ` : '';
        const caret = row.kind === 'slice' && row.expandable ? `<span aria-hidden="true" class="text-lf-muted">${row.expanded ? '▾' : '▸'}</span> ` : row.kind === 'detail' ? '<span aria-hidden="true" class="text-lf-muted">↳</span> ' : '';
        const suffix = row.kind === 'excluded' ? ` <span class="text-lf-muted">${escapeHtml(t('allocation.table.excluded'))}</span>` : '';
        return `${caret}${lead}${escapeHtml(label.text)}${suffix}`;
    }

    const html = (value: string): CellContent => ({type: 'html', html: value});
    /** The amount, through the one formatter (escaped, masked under privacy). */
    const amountHtml = (row: AllocationRow): string => formatCurrencyAmountHtml(row.amount, view.currency, {sensitivity: 'personal'});
    /** An excluded row is struck: on the content of each cell, where a decoration always reaches. */
    const strike = (row: AllocationRow): string => (row.kind === 'excluded' ? 'line-through text-lf-muted' : '');

    // Built again when the privacy flag flips (and when the sector names arrive), so that every cell follows both.
    const columns = $derived.by<ColumnDef<AllocationRow>[]>(() => {
        void isPrivacyEnabled();
        void sectorVersion;
        const base = {sortable: false, filterable: false, resizable: false} as const;
        return [
            {...base, id: 'label', minWidth: 170, header: () => $_(`allocation.dimension.${view.dimension}`), type: 'text', cell: (row) => html(`<span class="${strike(row)}">${labelHtml(row)}</span>`)},
            {...base, id: 'amount', header: () => $_('allocation.table.amount'), type: 'text', cell: (row) => html(`<span class="block whitespace-nowrap text-right ${COMPACT_MONEY} ${strike(row)}">${amountHtml(row)}</span>`)},
            {
                ...base,
                id: 'shareOfSelection',
                header: () => $_('allocation.table.shareOfSelection'),
                type: 'text',
                cell: (row) =>
                    html(
                        `<span class="block text-right ${row.kind === 'slice' ? 'font-semibold' : ''} ${strike(row)}">${row.kind === 'detail' ? escapeHtml(t('allocation.table.ofSlice', {values: {share: percent(row.shareOfSlice)}})) : row.kind === 'excluded' ? '—' : escapeHtml(percent(row.shareOfSelection))}</span>`,
                    ),
            },
            {...base, id: 'shareOfPortfolio', header: () => $_('allocation.table.shareOfPortfolio'), type: 'text', cell: (row) => html(`<span class="block text-right ${strike(row)}">${row.kind === 'slice' ? escapeHtml(percent(row.shareOfPortfolio)) : row.kind === 'excluded' ? '—' : ''}</span>`)},
            {...base, id: 'assets', header: () => $_('allocation.table.assets'), type: 'text', cell: (row) => html(`<span class="block text-right ${strike(row)}">${row.assetCount === null ? '' : row.assetCount}</span>`)},
        ];
    });

    const rowClass = (row: AllocationRow): string => (row.kind === 'excluded' ? 'text-lf-muted' : row.kind === 'detail' ? 'bg-lf-panel text-lf-secondary' : row.expandable ? 'cursor-pointer' : '');
    const hint = $derived(view.base_share_of_portfolio == null ? $_('allocation.table.hintNoShare') : $_('allocation.table.hint', {values: {share: percent(view.base_share_of_portfolio)}}));
</script>

<div data-testid={testId} data-dimension={view.dimension} aria-label={$_('allocation.table.label')}>
    <DataTable
        data={rows}
        {columns}
        getRowId={(row) => row.id}
        storageKey="allocation-table"
        enableSelection={false}
        enableActions={false}
        enableSorting={false}
        enableColumnFilters={false}
        enableColumnResize={false}
        enablePagination={false}
        enableColumnVisibility={false}
        enableContextMenu={false}
        stickyHeader={false}
        tableLayout="auto"
        emptyMessage={$_('allocation.table.empty')}
        getRowClass={rowClass}
        onRowClick={toggle}
    />
    <p class="mt-2 text-center text-xs italic text-lf-muted" data-testid="{testId}-hint">{hint}</p>
</div>
