<script lang="ts">
    import {attachOverflowMarqueeToDescendants} from '$lib/actions/scrollOnOverflow';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {assetStoreVersion, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';

    import {formatReplayShare, type TornadoRow} from './scenarioHelpers';

    /**
     * What each row did over the scenario, in a table with the bar beside the numbers (D376).
     *
     * The name is historical: this used to be bars alone. The bars stay — the one question
     * a scenario answers is *which holding hurts most*, and a bar gives that away before
     * the number is read — but the reader also asked for the numbers in columns: the
     * holding's weight, its own return, what it did to the whole, the amount, and the bar
     * in a column they can widen. The file and its props are unchanged so the shock block
     * (`L4Shock`, A's) mounts it as before.
     *
     * The bars share one scale, taken from the largest magnitude present, so two
     * rows are comparable to each other. A per-row scale would make every
     * scenario look equally severe, which is precisely the reassurance L4 must
     * not give.
     *
     * A column no row has a value for is not drawn at all: a selection of assets has no
     * weights, no contribution and no money, and a column of dashes would say the opposite
     * — that something could have been there.
     *
     * `DataTable` puts no attribute on its rows, so the row's testid and key live on the
     * asset cell. Cells are HTML strings, as in `ContributionTable`: the long names scroll
     * through the wrapper's marquee scan rather than through an action on each cell.
     */
    interface Props {
        rows: TornadoRow[];
        /** Row label, resolved by the caller: only it knows asset names. */
        label: (row: TornadoRow) => string;
        /** Money for a row, or '' when the payload carried no amount. */
        amount?: (row: TornadoRow) => string;
        testId: string;
    }

    let {rows, label, amount, testId}: Props = $props();

    let wrapper: HTMLDivElement | undefined = $state(undefined);

    // The wrapper exists only while there are rows, and rows can arrive after the mount.
    $effect(() => {
        if (!wrapper) return;
        return attachOverflowMarqueeToDescendants(wrapper);
    });

    let scale = $derived(Math.max(...rows.map((row) => Math.abs(row.value)), Number.EPSILON));
    let hasWeight = $derived(rows.some((row) => row.weight !== null));
    let hasReturn = $derived(rows.some((row) => row.ownReturn !== null));
    let hasContribution = $derived(rows.some((row) => row.contribution !== null));
    let hasImpact = $derived(amount !== undefined && rows.some((row) => amount(row) !== ''));

    function signedPercent(value: number, language: string): string {
        return new Intl.NumberFormat(language, {style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: 'exceptZero'}).format(value);
    }

    function numberCell(testSuffix: string, text: string): {type: 'html'; html: string} {
        return {type: 'html', html: text === '' ? '' : `<span class="tabular-nums" data-testid="${escapeHtml(`${testId}-${testSuffix}`)}">${escapeHtml(text)}</span>`};
    }

    /**
     * The asset's own icon when the cache knows one, else its type's, else the generic one: always a
     * picture, so every asset row reads the same. The cache is read, never loaded: the page that mounts
     * the block owns loading it. A bucket is not an asset and has none.
     */
    function iconHtml(row: TornadoRow): string {
        if (row.assetId === undefined) return '';
        const info = getAssetInfo(row.assetId);
        const src = info?.icon_url || getAssetTypeIconUrl(info?.asset_type ?? null);
        return `<img src="${escapeHtml(src)}" alt="" class="h-4 w-4 shrink-0 rounded-full object-cover" onerror="this.style.visibility='hidden'" />`;
    }

    function barHtml(row: TornadoRow): string {
        const magnitude = (Math.abs(row.value) / scale) * 100;
        const loss = row.value < 0;
        // The zero line is drawn, not implied: without it a reader cannot tell a small
        // gain from a small loss at a glance.
        return (
            `<span class="relative block h-3 w-full rounded bg-gray-100 dark:bg-slate-700">` +
            `<span class="absolute top-0 h-3 rounded ${loss ? 'bg-red-500/80 right-1/2' : 'bg-emerald-500/80 left-1/2'}" style="width: ${(magnitude / 2).toFixed(2)}%" data-testid="${escapeHtml(`${testId}-bar`)}" data-sign="${loss ? 'loss' : 'gain'}"></span>` +
            `<span class="absolute left-1/2 top-0 h-3 w-px bg-gray-300 dark:bg-slate-500"></span>` +
            `</span>`
        );
    }

    let columns = $derived.by((): ColumnDef<TornadoRow>[] => {
        void $assetStoreVersion;
        const language = $currentLanguage;
        const list: ColumnDef<TornadoRow>[] = [
            {
                id: 'asset',
                header: () => $t('risk.levels.l4.table.asset'),
                type: 'text',
                width: 200,
                minWidth: 140,
                filterable: false,
                getValue: (row) => label(row),
                cell: (row) => ({
                    type: 'html',
                    html: `<div class="flex min-w-0 items-center gap-1.5" data-testid="${escapeHtml(`${testId}-row`)}" data-row-key="${escapeHtml(row.key)}">${iconHtml(row)}<span class="min-w-0 flex-1 ${overflowScrollTextClass}">${escapeHtml(label(row))}</span></div>`,
                }),
            },
        ];
        if (hasWeight) {
            list.push({id: 'weight', header: () => $t('risk.levels.l4.table.weight'), type: 'number', width: 80, minWidth: 64, align: 'right', filterable: false, getValue: (row) => row.weight, cell: (row) => numberCell('weight', row.weight === null ? '' : formatReplayShare(row.weight, language))});
        }
        if (hasReturn) {
            list.push({
                id: 'return',
                header: () => $t('risk.levels.l4.table.return'),
                type: 'number',
                width: 96,
                minWidth: 72,
                align: 'right',
                filterable: false,
                getValue: (row) => row.ownReturn,
                cell: (row) => numberCell('return', row.ownReturn === null ? '' : signedPercent(row.ownReturn, language)),
            });
        }
        if (hasContribution) {
            list.push({
                id: 'contribution',
                header: () => $t('risk.levels.l4.table.contribution'),
                type: 'number',
                width: 104,
                minWidth: 80,
                align: 'right',
                filterable: false,
                getValue: (row) => row.contribution,
                cell: (row) => numberCell('contribution', row.contribution === null ? '' : signedPercent(row.contribution, language)),
            });
        }
        if (hasImpact && amount) {
            list.push({id: 'impact', header: () => $t('risk.levels.l4.table.impact'), type: 'number', width: 112, minWidth: 80, align: 'right', filterable: false, getValue: (row) => row.amount, cell: (row) => numberCell('impact', amount(row))});
        }
        list.push({id: 'bar', header: () => $t('risk.levels.l4.table.bar'), type: 'number', width: 200, minWidth: 96, filterable: false, getValue: (row) => row.value, cell: (row) => ({type: 'html', html: barHtml(row)})});
        return list;
    });
</script>

{#if rows.length > 0}
    <div bind:this={wrapper} data-testid={testId}>
        <DataTable
            data={rows}
            {columns}
            getRowId={(row) => row.key}
            storageKey={testId}
            enableSelection={false}
            selectionMode="none"
            enableActions={false}
            enableColumnFilters={false}
            enablePagination={false}
            enableColumnVisibility={false}
            enableContextMenu={false}
            enableColumnResize
            enableSorting
        />
    </div>
{/if}
