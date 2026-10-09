<!--
  GapFixStep.svelte — "Align with the bank", the import wizard's step after the review for report sets.

  Per broker and plugin (one gap-fix request): a summary card for each truth point, in date order —
  a checkpoint with the cash LibreFolio lacks and the positions that differ, a verification with
  whether it holds. A card is the group's active point: it opens that point's full comparison (what
  LibreFolio will have next to what the bank states, and where the difference comes from), and a
  checkpoint also narrows the table to its own corrections; a second click clears it. Below, one
  table of the group's corrections, selected by default (D-S14), with the review's commands. The
  verifications are only compared, never corrected. A controlled component: the wizard owns the
  selection, and the step only asks to flip a key, or to set several at once.

  Plain Svelte text, no {@html}. Money goes through CurrencyAmount (privacy). A position's quantity
  sits next to the bank's figures and is masked (D5′); a correction's quantity is a transaction's,
  and stays visible.

  Design: LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/design-phase00BrimReportSets.md, §4.6;
  layout U4-B of the developer's review (plan, F2.0).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {AlertTriangle, CheckCircle, CheckSquare, Info, ListChecks, Square, XCircle} from 'lucide-svelte';
    import CurrencyAmount from '$lib/components/ui/display/CurrencyAmount.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import GapFixToggle from '$lib/components/transactions/import/GapFixToggle.svelte';
    import {maskableQuantity} from '$lib/utils/privacy/maskable';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {formatIsoDay} from '$lib/utils/transactions/importReportSets';
    import {getTransactionTypeIconUrl} from '$lib/stores/transactions/transactionTypeStore';
    import {gapFixProposalCount, gapFixSelectedCount, type GapFixAmount, type GapFixCashRow, type GapFixCheckpoint, type GapFixGroup, type GapFixNote, type GapFixProposal, type GapFixVerification, type GapFixView} from '$lib/utils/transactions/gapFixModel';

    interface Props {
        view: GapFixView;
        selected: ReadonlySet<string>;
        onToggle: (key: string) => void;
        /** Keep or drop several corrections at once: select all, select visible, deselect all. */
        onSetSelected: (keys: string[], selected: boolean) => void;
        assetName: (assetId: number) => string;
        brokerName: (brokerId: number) => string;
    }

    let {view, selected, onToggle, onSetSelected, assetName, brokerName}: Props = $props();

    let proposalCount = $derived(gapFixProposalCount(view));
    let selectedCount = $derived(gapFixSelectedCount(view, selected));

    const P = 'importWizard.reportSet.gapFix.';

    /** A truth point of a group, as its summary card shows it. */
    type Point = {kind: 'checkpoint'; key: string; asOf: string; checkpoint: GapFixCheckpoint} | {kind: 'verification'; key: string; asOf: string; verification: GapFixVerification};

    /** One correction, as its table row shows it. */
    interface ProposalRow {
        key: string;
        pointKey: string;
        pointKind: string;
        type: string;
        date: string;
        assetId: number | null;
        quantity: string | null;
        cash: {code: string; amount: number} | null;
        needsCost: boolean;
        selected: boolean;
    }

    /** The active point of each group, by group key. */
    let activeByGroup = $state<Record<string, string | null>>({});
    let tables = $state<Record<string, DataTable<ProposalRow> | undefined>>({});

    function quantity(value: string): string {
        return formatDecimalForDisplay(value, {minFrac: 0, maxFrac: 8});
    }

    function signedQuantity(value: string): string {
        const formatted = quantity(value);
        return Number(value) > 0 ? `+${formatted}` : formatted;
    }

    function nonZero(list: GapFixAmount[]): GapFixAmount[] {
        return list.filter((item) => Number(item.amount) !== 0);
    }

    function differences(rows: GapFixCashRow[]): GapFixCashRow[] {
        return rows.filter((row) => Number(row.difference) !== 0);
    }

    function noteText(note: GapFixNote): string {
        const key = `${P}note.${note.code}`;
        const translated = $t(key);
        return translated === key ? note.message : translated;
    }

    function typeLabel(type: string): string {
        const key = `transactions.types.${type}`;
        const translated = $t(key);
        return translated === key ? type : translated;
    }

    function pointLabel(kind: string): string {
        if (kind === 'opening') return $t(`${P}pointOpening`);
        if (kind === 'gap') return $t(`${P}pointGap`);
        return kind;
    }

    function checkpointTitle(checkpoint: GapFixCheckpoint): string {
        return $t(checkpoint.kind === 'opening' ? `${P}checkpointOpening` : `${P}checkpointGap`, {values: {date: formatIsoDay(checkpoint.asOf)}});
    }

    function proposalFacts(proposal: GapFixProposal) {
        const tx = proposal.tx;
        const cash = typeof tx.cash === 'object' && tx.cash !== null && !Array.isArray(tx.cash) ? (tx.cash as {code?: unknown; amount?: unknown}) : null;
        return {
            type: String(tx.type ?? ''),
            date: String(tx.date ?? '').slice(0, 10),
            assetId: typeof tx.asset_id === 'number' ? tx.asset_id : null,
            quantity: tx.quantity !== null && tx.quantity !== undefined && Number(tx.quantity) !== 0 ? String(tx.quantity) : null,
            cash: cash && typeof cash.code === 'string' ? {code: cash.code, amount: Number(cash.amount)} : null,
        };
    }

    /** The truth points of a group in date order; on a shared date the checkpoint comes first. */
    function pointsOf(group: GapFixGroup): Point[] {
        const points: Point[] = [
            ...group.checkpoints.map((checkpoint): Point => ({kind: 'checkpoint', key: checkpoint.key, asOf: checkpoint.asOf, checkpoint})),
            ...group.verifications.map((verification): Point => ({kind: 'verification', key: verification.key, asOf: verification.asOf, verification})),
        ];
        return points.sort((a, b) => {
            if (a.asOf !== b.asOf) return a.asOf < b.asOf ? -1 : 1;
            if (a.kind === b.kind) return 0;
            return a.kind === 'checkpoint' ? -1 : 1;
        });
    }

    function activePointOf(group: GapFixGroup): Point | null {
        const key = activeByGroup[group.key] ?? null;
        return key === null ? null : (pointsOf(group).find((point) => point.key === key) ?? null);
    }

    function toggleActive(group: GapFixGroup, key: string) {
        activeByGroup = {...activeByGroup, [group.key]: activeByGroup[group.key] === key ? null : key};
    }

    function changedPositions(checkpoint: GapFixCheckpoint): number {
        return checkpoint.positions.filter((position) => Number(position.difference) !== 0).length;
    }

    /** The group's corrections; a checkpoint, when active, keeps only its own (a verification corrects nothing). */
    function rowsOf(group: GapFixGroup, active: Point | null): ProposalRow[] {
        const only = active?.kind === 'checkpoint' ? active.key : null;
        return group.checkpoints
            .filter((checkpoint) => only === null || checkpoint.key === only)
            .flatMap((checkpoint) =>
                checkpoint.proposals.map((proposal) => ({
                    ...proposalFacts(proposal),
                    key: proposal.key,
                    pointKey: checkpoint.key,
                    pointKind: checkpoint.kind,
                    needsCost: proposal.needsCost,
                    selected: selected.has(proposal.key),
                })),
            );
    }

    function groupKeys(group: GapFixGroup): string[] {
        return group.checkpoints.flatMap((checkpoint) => checkpoint.proposals.map((proposal) => proposal.key));
    }

    function groupSelectedCount(group: GapFixGroup): number {
        return groupKeys(group).filter((key) => selected.has(key)).length;
    }

    /** The rows of the table's current page, filter and sort included, as the review's command does. */
    function selectVisible(group: GapFixGroup) {
        const keys = tables[group.key]?.getPageRowIds() ?? [];
        if (keys.length > 0) onSetSelected(keys, true);
    }

    let columns = $derived<ColumnDef<ProposalRow>[]>([
        {
            id: 'selected',
            header: '',
            type: 'custom',
            sortable: false,
            filterable: false,
            width: 52,
            minWidth: 52,
            cell: (row) => ({type: 'custom', component: GapFixToggle, props: {pressed: row.selected, label: $t(`${P}toggle`), proposalKey: row.key, type: row.type, date: row.date, point: row.pointKey, onToggle: () => onToggle(row.key)}}),
        },
        {id: 'point', header: () => $t(`${P}column.point`), type: 'text', sortable: true, filterable: false, width: 140, minWidth: 110, getValue: (row) => `${row.date}:${row.pointKind}`, cell: (row) => pointLabel(row.pointKind)},
        {id: 'date', header: () => $t('common.date'), type: 'date', sortable: true, filterable: false, width: 110, minWidth: 100, getValue: (row) => row.date, cell: (row) => ({type: 'date', value: row.date, format: 'date'})},
        {id: 'type', header: () => $t('common.type'), type: 'text', sortable: true, filterable: false, minWidth: 140, getValue: (row) => typeLabel(row.type), cell: (row) => ({type: 'image', src: getTransactionTypeIconUrl(row.type), alt: '', text: typeLabel(row.type), size: 20})},
        {id: 'asset', header: () => $t('common.asset'), type: 'text', sortable: true, filterable: false, minWidth: 140, getValue: (row) => (row.assetId !== null ? assetName(row.assetId) : ''), cell: (row) => (row.assetId !== null ? assetName(row.assetId) : '—')},
        {id: 'quantity', header: () => $t('common.quantity'), type: 'number', sortable: false, filterable: false, width: 110, minWidth: 90, cell: (row) => (row.quantity !== null ? signedQuantity(row.quantity) : '—')},
        {
            id: 'cash',
            header: () => $t('common.cash'),
            type: 'custom',
            sortable: false,
            filterable: false,
            minWidth: 140,
            cell: (row) => (row.cash !== null ? {type: 'custom', component: CurrencyAmount, props: {amount: row.cash.amount, code: row.cash.code, options: {showSign: true}}} : '—'),
        },
        {
            id: 'tag',
            header: () => $t('common.tags'),
            type: 'text',
            sortable: false,
            filterable: false,
            width: 140,
            minWidth: 110,
            cell: (row) => (row.needsCost ? {type: 'badge', text: $t(`${P}costToEnter`), variant: 'warning'} : {type: 'badge', text: 'gap_fix', variant: 'default'}),
        },
    ]);
</script>

{#snippet amountList(list: GapFixAmount[])}
    {#each list as item, index (index)}
        <span class="whitespace-nowrap font-mono"
            >{#if index > 0}·{/if}
            <CurrencyAmount amount={Number(item.amount)} code={item.currency} /></span
        >
    {/each}
{/snippet}

{#snippet checkpointDetails(checkpoint: GapFixCheckpoint)}
    {@const explanation = checkpoint.explanation}
    {@const openingCash = nonZero(explanation.openingCash)}
    <div data-testid="gapfix-checkpoint" data-as-of={checkpoint.asOf} data-kind={checkpoint.kind}>
        <h4 class="border-b border-gray-100 px-3 py-2 text-sm font-medium text-gray-800 dark:border-slate-700 dark:text-gray-100">{checkpointTitle(checkpoint)}</h4>

        {#if checkpoint.cash.length > 0 || checkpoint.positions.length > 0}
            <div class="overflow-x-auto px-3 py-2">
                <table class="w-full text-sm">
                    <thead>
                        <tr class="text-xs text-gray-500 dark:text-gray-400">
                            <th class="py-1 text-left font-normal"></th>
                            <th class="py-1 text-right font-normal">LibreFolio</th>
                            <th class="py-1 text-right font-normal">{$t(`${P}bank`)}</th>
                            <th class="py-1 text-right font-normal">{$t(`${P}difference`)}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each checkpoint.cash as row, index (index)}
                            <tr data-testid="gapfix-cash-row" data-currency={row.currency} data-difference={row.difference}>
                                <td class="py-1 pr-3 text-gray-700 dark:text-gray-200">{$t(`${P}cashLabel`, {values: {currency: row.currency}})}</td>
                                <td class="py-1 text-right font-mono"><CurrencyAmount amount={Number(row.librefolio)} code={row.currency} /></td>
                                <td class="py-1 text-right font-mono"><CurrencyAmount amount={Number(row.bank)} code={row.currency} /></td>
                                <td class="py-1 text-right font-mono"><CurrencyAmount amount={Number(row.difference)} code={row.currency} options={{showSign: true}} /></td>
                            </tr>
                        {/each}
                        {#each checkpoint.positions as position, index (index)}
                            <tr data-testid="gapfix-position-row" data-asset-id={position.assetId} data-exactness={position.exactness}>
                                <td class="py-1 pr-3 text-gray-700 dark:text-gray-200">{assetName(position.assetId)}</td>
                                <td class="py-1 text-right font-mono">{maskableQuantity(quantity(position.librefolio))}</td>
                                <td class="py-1 text-right font-mono">
                                    {#if position.exactness === 'at_least'}
                                        {$t(`${P}atLeast`, {values: {quantity: maskableQuantity(quantity(position.bank))}})}
                                    {:else}
                                        {maskableQuantity(quantity(position.bank))}
                                    {/if}
                                </td>
                                <td class="py-1 text-right font-mono">{maskableQuantity(signedQuantity(position.difference))}</td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}

        {#if explanation.absorbedCount > 0 || openingCash.length > 0 || explanation.unexplainedCash.length > 0 || explanation.notes.length > 0}
            <div class="space-y-1 border-t border-gray-100 px-3 py-2 text-xs text-gray-600 dark:border-slate-700 dark:text-gray-300" data-testid="gapfix-explanation">
                {#if explanation.absorbedCount > 0}
                    <p>
                        {$t(`${P}absorbed`, {values: {n: explanation.absorbedCount}})}
                        {#if explanation.absorbedMissingCount > 0}
                            {$t(`${P}absorbedMissing`, {values: {n: explanation.absorbedMissingCount}})}
                            {@render amountList(explanation.absorbedMissingCash)}
                        {/if}
                    </p>
                {/if}
                {#if openingCash.length > 0}
                    <p>{$t(`${P}openingCash`)} {@render amountList(openingCash)}</p>
                {/if}
                {#if explanation.unexplainedCash.length > 0}
                    <p>{$t(`${P}unexplained`)} {@render amountList(explanation.unexplainedCash)}</p>
                {/if}
                {#each explanation.notes as note, index (index)}
                    <p class="flex items-start gap-1.5 text-amber-700 dark:text-amber-300" data-testid="gapfix-note" data-code={note.code}><AlertTriangle size={12} class="mt-0.5 shrink-0" /> {noteText(note)}</p>
                {/each}
            </div>
        {/if}
    </div>
{/snippet}

{#snippet verificationDetails(verification: GapFixVerification)}
    <div class="px-3 py-2 text-sm" data-testid="gapfix-verification" data-as-of={verification.asOf} data-ok={String(verification.ok)}>
        <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="text-gray-800 dark:text-gray-100">{$t(`${P}verificationTitle`, {values: {date: formatIsoDay(verification.asOf)}})}</span>
            {#if verification.ok}
                <span class="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300"><CheckCircle size={14} /> {$t(`${P}verificationOk`)}</span>
            {:else}
                <span class="inline-flex items-center gap-1 text-xs font-semibold text-red-700 dark:text-red-300"><XCircle size={14} /> {$t(`${P}verificationKo`)}</span>
            {/if}
        </div>
        {#if !verification.ok}
            <table class="mt-2 w-full text-sm">
                <tbody>
                    {#each verification.cash as row, index (index)}
                        <tr data-testid="gapfix-verification-cash-row" data-currency={row.currency} data-difference={row.difference}>
                            <td class="py-1 pr-3 text-gray-700 dark:text-gray-200">{$t(`${P}cashLabel`, {values: {currency: row.currency}})}</td>
                            <td class="py-1 text-right font-mono">LibreFolio <CurrencyAmount amount={Number(row.librefolio)} code={row.currency} /></td>
                            <td class="py-1 text-right font-mono">{$t(`${P}bank`)} <CurrencyAmount amount={Number(row.bank)} code={row.currency} /></td>
                            <td class="py-1 text-right font-mono"><CurrencyAmount amount={Number(row.difference)} code={row.currency} options={{showSign: true}} /></td>
                        </tr>
                    {/each}
                </tbody>
            </table>
            <p class="mt-1 text-xs text-gray-600 dark:text-gray-300">{$t(`${P}verificationKoHint`)}</p>
        {/if}
    </div>
{/snippet}

<div class="space-y-4" data-testid="import-wizard-gapfix" data-proposal-count={proposalCount} data-selected-count={selectedCount}>
    <p class="text-sm text-gray-600 dark:text-gray-300">{$t(`${P}intro`)}</p>

    {#each view.groups as group (group.key)}
        {@const points = pointsOf(group)}
        {@const active = activePointOf(group)}
        {@const rows = rowsOf(group, active)}
        <section class="rounded-lg border border-gray-200 dark:border-slate-700" data-testid="gapfix-group" data-broker-id={group.brokerId} data-plugin-code={group.pluginCode}>
            <header class="border-b border-gray-200 bg-gray-50 px-4 py-2 text-sm font-semibold text-gray-800 dark:border-slate-700 dark:bg-slate-800/60 dark:text-gray-100">{brokerName(group.brokerId)}</header>

            {#if group.error !== null}
                <div role="alert" class="m-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300" data-testid="gapfix-error">
                    <p class="flex items-center gap-1.5 font-medium"><AlertTriangle size={14} /> {$t(`${P}error`)}</p>
                    <p class="mt-1 break-words font-mono text-xs">{group.error}</p>
                    <p class="mt-1 text-xs">{$t(`${P}errorContinue`)}</p>
                </div>
            {:else}
                <div class="space-y-3 p-4">
                    {#if points.length > 0}
                        <p class="text-xs text-gray-500 dark:text-gray-400">{$t(`${P}filterHint`)}</p>
                        <div class="flex flex-wrap gap-2">
                            {#each points as point (point.key)}
                                {@const isActive = active?.key === point.key}
                                {#if point.kind === 'checkpoint'}
                                    {@const checkpoint = point.checkpoint}
                                    {@const positions = changedPositions(checkpoint)}
                                    <button
                                        type="button"
                                        class="min-w-44 rounded-lg border px-3 py-2 text-left text-sm transition-colors {isActive ? 'border-libre-green bg-libre-green/5 ring-1 ring-libre-green' : 'border-gray-200 hover:border-gray-400 dark:border-slate-700 dark:hover:border-slate-500'}"
                                        aria-pressed={isActive ? 'true' : 'false'}
                                        onclick={() => toggleActive(group, point.key)}
                                        data-testid="gapfix-summary"
                                        data-key={point.key}
                                        data-kind={checkpoint.kind}
                                        data-as-of={checkpoint.asOf}
                                        data-proposals={checkpoint.proposals.length}
                                        data-positions={positions}
                                        data-notes={checkpoint.explanation.notes.length}
                                    >
                                        <span class="block text-xs font-semibold text-gray-800 dark:text-gray-100">{checkpointTitle(checkpoint)}</span>
                                        {#each differences(checkpoint.cash) as row, index (index)}
                                            <span class="block font-mono text-xs text-gray-700 dark:text-gray-200">{$t(`${P}cashLabel`, {values: {currency: row.currency}})} <CurrencyAmount amount={Number(row.difference)} code={row.currency} options={{showSign: true}} /></span>
                                        {/each}
                                        <span class="mt-0.5 flex flex-wrap gap-x-2 text-[11px] text-gray-500 dark:text-gray-400">
                                            {#if positions > 0}<span>{$t(`${P}positions`, {values: {n: positions}})}</span>{/if}
                                            <span>{$t(`${P}corrections`, {values: {n: checkpoint.proposals.length}})}</span>
                                            {#if checkpoint.explanation.notes.length > 0}<span class="text-amber-700 dark:text-amber-300">⚠ {$t(`${P}notesCount`, {values: {n: checkpoint.explanation.notes.length}})}</span>{/if}
                                        </span>
                                    </button>
                                {:else}
                                    {@const verification = point.verification}
                                    <button
                                        type="button"
                                        class="min-w-44 rounded-lg border px-3 py-2 text-left text-sm transition-colors {isActive
                                            ? 'border-libre-green bg-libre-green/5 ring-1 ring-libre-green'
                                            : verification.ok
                                              ? 'border-emerald-200 hover:border-emerald-400 dark:border-emerald-900/60'
                                              : 'border-red-200 hover:border-red-400 dark:border-red-900/60'}"
                                        aria-pressed={isActive ? 'true' : 'false'}
                                        onclick={() => toggleActive(group, point.key)}
                                        data-testid="gapfix-summary"
                                        data-key={point.key}
                                        data-kind="verification"
                                        data-as-of={verification.asOf}
                                        data-ok={String(verification.ok)}
                                    >
                                        <span class="block text-xs font-semibold text-gray-800 dark:text-gray-100">{$t(`${P}verificationTitle`, {values: {date: formatIsoDay(verification.asOf)}})}</span>
                                        {#if verification.ok}
                                            <span class="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300"><CheckCircle size={12} /> {$t(`${P}verificationOk`)}</span>
                                        {:else}
                                            <span class="inline-flex items-center gap-1 text-xs font-semibold text-red-700 dark:text-red-300"><XCircle size={12} /> {$t(`${P}verificationKo`)}</span>
                                            {#each differences(verification.cash) as row, index (index)}
                                                <span class="block font-mono text-xs text-gray-700 dark:text-gray-200"><CurrencyAmount amount={Number(row.difference)} code={row.currency} options={{showSign: true}} /></span>
                                            {/each}
                                        {/if}
                                    </button>
                                {/if}
                            {/each}
                        </div>
                    {/if}

                    {#if active}
                        <div class="rounded-lg border border-libre-green/40 dark:border-libre-green/30" data-testid="gapfix-point-details" data-key={active.key}>
                            {#if active.kind === 'checkpoint'}
                                {@render checkpointDetails(active.checkpoint)}
                            {:else}
                                {@render verificationDetails(active.verification)}
                            {/if}
                        </div>
                    {/if}

                    {#if groupKeys(group).length > 0}
                        <div class="overflow-hidden rounded-lg border border-gray-200 dark:border-slate-700" data-testid="gapfix-table">
                            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 bg-gray-50 px-3 py-1.5 dark:border-slate-700 dark:bg-slate-800/60">
                                <span class="text-xs text-gray-600 dark:text-gray-300">{$t(`${P}selectedCount`, {values: {n: groupSelectedCount(group)}})}</span>
                                <div class="flex items-center gap-2">
                                    <button type="button" class="flex items-center gap-1 text-xs text-libre-green hover:underline" onclick={() => onSetSelected(groupKeys(group), true)} data-testid="gapfix-select-all">
                                        <CheckSquare size={12} /><span class="hidden sm:inline">{$t('common.selectAll')}</span>
                                    </button>
                                    <span class="text-gray-300 dark:text-gray-600">|</span>
                                    <button type="button" class="flex items-center gap-1 text-xs text-libre-green hover:underline" onclick={() => selectVisible(group)} data-testid="gapfix-select-visible" title={$t('importWizard.selectVisibleTip')}>
                                        <ListChecks size={12} /><span class="hidden sm:inline">{$t('importWizard.selectVisible')}</span>
                                    </button>
                                    <span class="text-gray-300 dark:text-gray-600">|</span>
                                    <button type="button" class="flex items-center gap-1 text-xs text-gray-500 hover:underline" onclick={() => onSetSelected(groupKeys(group), false)} data-testid="gapfix-deselect-all">
                                        <Square size={12} /><span class="hidden sm:inline">{$t('common.deselectAll')}</span>
                                    </button>
                                </div>
                            </div>
                            <DataTable
                                bind:this={tables[group.key]}
                                data={rows}
                                {columns}
                                getRowId={(row) => row.key}
                                storageKey="import-wizard-gapfix"
                                enableSelection={false}
                                enableActions={false}
                                enablePagination={true}
                                defaultPageSize={10}
                                pageSizeOptions={[10, 25, 50, 0]}
                                enableSorting={true}
                                enableColumnFilters={false}
                                enableColumnResize={true}
                                enableColumnVisibility={false}
                                tableLayout="auto"
                                getRowClass={(row) => (row.selected ? '' : 'opacity-50')}
                                emptyMessage={$t(`${P}noProposals`)}
                            />
                        </div>
                    {/if}
                </div>
            {/if}
        </section>
    {/each}

    <p class="flex items-start gap-1.5 text-xs text-gray-500 dark:text-gray-400" data-testid="gapfix-info-hidden-titles"><Info size={14} class="mt-0.5 shrink-0" /> {$t(`${P}hiddenTitles`)}</p>
</div>
