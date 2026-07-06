<!--
  OtherPeriodEffectsTable — Compact secondary table for period P&L rows that are
  not tied to a specific asset position.

  Mounted separately from main Performance table. Hidden entirely when there are
  no effects.

  Pattern: Svelte 5 runes, DataTable, data-testid, dark mode.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import type {PositionsContribution} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    type OtherPeriodEffect = NonNullable<PositionsContribution['other_effects']>[number];

    interface Props {
        effects: OtherPeriodEffect[];
        displayCurrency: string;
    }

    interface DisplayRow {
        key: string;
        description: string;
        category: string;
        periodPnl: number | null;
        brokerId: number | null;
        brokerName: string | null;
    }

    let {effects = [], displayCurrency = 'EUR'}: Props = $props();

    let tableShell: HTMLDivElement | null = $state(null);

    function safeNum(v: string | (string | null)[] | null | undefined): number | null {
        const s = Array.isArray(v) ? (v[0] ?? null) : v;
        if (s == null) return null;
        const n = parseFloat(s);
        return Number.isNaN(n) ? null : n;
    }

    function safeInt(v: number | (number | null)[] | null | undefined): number | null {
        if (v == null) return null;
        return Array.isArray(v) ? (v[0] ?? null) : v;
    }

    function safeStr(v: string | (string | null)[] | null | undefined): string | null {
        if (v == null) return null;
        return Array.isArray(v) ? (v[0] ?? null) : v;
    }

    function label(key: string, fallback: string): string {
        const translated = $_(key);
        return !translated || translated === key ? fallback : translated;
    }

    let rows = $derived.by<DisplayRow[]>(() =>
        (effects ?? []).map((effect, index) => ({
            key: `effect-${index}-${effect.category}-${safeInt(effect.broker_id) ?? 'global'}`,
            description: effect.description,
            category: effect.category,
            periodPnl: safeNum(effect.period_pnl),
            brokerId: safeInt(effect.broker_id),
            brokerName: safeStr(effect.broker_name),
        })),
    );

    function escapeHtml(value: string): string {
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function categoryBadgeClass(category: string): string {
        switch (category) {
            case 'Income':
                return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
            case 'Cost':
                return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
            default:
                return 'bg-slate-100 text-slate-700 dark:bg-slate-700/50 dark:text-slate-300';
        }
    }

    function categoryLabel(category: string): string {
        if (category === 'Income') return label('dashboard.categoryIncome', category);
        if (category === 'Cost') return label('dashboard.categoryCost', category);
        if (category === 'Other') return label('dashboard.categoryOther', category);
        return category;
    }

    /** Backend sends fixed English description strings (never localized) — translate
     *  the known ones instead of leaking raw English into other languages. */
    function descriptionLabel(description: string): string {
        if (description === 'Unallocated income') return label('dashboard.unallocatedIncome', description);
        if (description === 'Unallocated costs') return label('dashboard.unallocatedCosts', description);
        if (description === 'Other / reconciliation residual') return label('dashboard.otherReconciliationResidual', description);
        return description;
    }

    /** Broker shown inline in the description right away (not only in the separate
     *  Broker column) — per-broker rows should read e.g. "Unallocated income — Directa"
     *  at a glance. Global rows (no broker, e.g. the reconciliation residual) are
     *  unaffected. */
    function descriptionWithBroker(row: DisplayRow): string {
        const base = descriptionLabel(row.description);
        return row.brokerName ? `${base} — ${row.brokerName}` : base;
    }

    function amountColorClass(value: number | null): string {
        if (value == null || value === 0) return 'text-gray-500 dark:text-gray-400';
        return value > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400';
    }

    function formatAmount(value: number | null): string {
        if (value == null) return '—';
        return formatCurrencyAmountPlain(value, displayCurrency, {showSign: value !== 0});
    }

    let columns = $derived.by<ColumnDef<DisplayRow>[]>(() => [
        {
            id: 'description',
            header: () => label('common.description', 'Description'),
            type: 'text',
            width: 320,
            minWidth: 240,
            maxWidth: 480,
            sortable: true,
            filterable: false,
            resizable: true,
            getValue: (row) => descriptionWithBroker(row),
            cell: (row) => ({
                type: 'html' as const,
                html: `<div class="block max-w-[18rem] truncate text-gray-700 dark:text-gray-200" title="${escapeHtml(descriptionWithBroker(row))}">${escapeHtml(descriptionWithBroker(row))}</div>`,
            }),
        },
        {
            id: 'category',
            header: () => label('common.category', 'Category'),
            type: 'text',
            width: 120,
            minWidth: 110,
            maxWidth: 160,
            sortable: true,
            filterable: false,
            resizable: true,
            getValue: (row) => categoryLabel(row.category),
            cell: (row) => ({
                type: 'html' as const,
                html: `<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium ${categoryBadgeClass(row.category)}" data-testid="other-period-effects-category-${escapeHtml(row.key)}">${escapeHtml(categoryLabel(row.category))}</span>`,
            }),
        },
        {
            id: 'period-pnl',
            header: () => label('dashboard.periodPnl', 'Period P&L'),
            type: 'number',
            width: 150,
            minWidth: 140,
            maxWidth: 190,
            sortable: true,
            filterable: false,
            resizable: true,
            align: 'right',
            getValue: (row) => row.periodPnl ?? 0,
            cell: (row) => ({
                type: 'html' as const,
                html: `<span class="font-medium tabular-nums ${amountColorClass(row.periodPnl)}">${escapeHtml(formatAmount(row.periodPnl))}</span>`,
            }),
        },
        {
            id: 'broker',
            header: () => label('common.broker', 'Broker'),
            type: 'text',
            width: 190,
            minWidth: 150,
            maxWidth: 240,
            sortable: true,
            filterable: false,
            resizable: true,
            getValue: (row) => row.brokerName ?? '',
            cell: (row) => {
                if (row.brokerId != null && row.brokerName) {
                    return {
                        type: 'custom' as const,
                        component: BrokerBadge,
                        props: {
                            broker: {id: row.brokerId, name: row.brokerName},
                            size: 14,
                            showName: true,
                            tooltip: row.brokerName,
                            nameClass: 'text-xs',
                        },
                    };
                }

                if (row.brokerName) {
                    return {
                        type: 'html' as const,
                        html: `<span class="block truncate text-gray-600 dark:text-gray-300">${escapeHtml(row.brokerName)}</span>`,
                    };
                }

                return {
                    type: 'html' as const,
                    html: '<span class="text-gray-400 dark:text-gray-500">—</span>',
                };
            },
        },
    ]);

    function syncRowTestIds() {
        if (!tableShell) return;

        for (const row of rows) {
            const rowElement = tableShell.querySelector<HTMLTableRowElement>(`tr[data-row-id="${row.key}"]`);
            if (!rowElement) continue;

            rowElement.setAttribute('data-testid', `other-period-effects-row-${row.key}`);

            const cells = rowElement.querySelectorAll('td');
            cells[2]?.setAttribute('data-testid', `other-period-effects-pnl-${row.key}`);
        }
    }

    $effect(() => {
        if (!tableShell) return;
        rows;

        const observer = new MutationObserver(() => {
            syncRowTestIds();
        });

        observer.observe(tableShell, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ['data-row-id'],
        });

        syncRowTestIds();

        return () => {
            observer.disconnect();
        };
    });
</script>

{#if rows.length > 0}
    <section class="mt-3 rounded-lg border border-gray-200/80 bg-gray-50/80 dark:border-slate-700 dark:bg-slate-900/30" data-testid="other-period-effects-table">
        <div class="border-b border-gray-200/80 px-3 py-2 dark:border-slate-700" data-testid="other-period-effects-header">
            <h3 class="text-[11px] font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-200">
                {label('dashboard.otherPeriodEffects', 'Other Period Effects')}
            </h3>
            <p class="mt-0.5 text-[11px] text-gray-500 dark:text-gray-400">
                {label('dashboard.otherPeriodEffectsSubtitle', 'Effects that contribute to period P&L but are not linked to a specific asset')}
            </p>
        </div>

        <div bind:this={tableShell} class="other-period-effects-datatable">
            <DataTable
                data={rows}
                {columns}
                getRowId={(row) => row.key}
                storageKey="dashboard-other-period-effects"
                enableSelection={false}
                selectionMode="none"
                enableActions={false}
                enablePagination={false}
                enableColumnVisibility={false}
                enableColumnFilters={false}
                enableSorting={false}
                enableColumnResize={true}
                enableContextMenu={false}
                tableLayout="fixed"
            />
        </div>
    </section>
{/if}

<style>
    .other-period-effects-datatable :global(.table-wrapper) {
        border: none;
        border-radius: 0;
        background: transparent;
    }

    :global(.dark) .other-period-effects-datatable :global(.table-wrapper) {
        background: transparent;
    }

    .other-period-effects-datatable :global(.datatable) {
        background: transparent;
    }

    :global(.dark) .other-period-effects-datatable :global(.datatable) {
        background: transparent;
    }

    .other-period-effects-datatable :global(.datatable thead) {
        background: rgb(255 255 255 / 0.5);
    }

    :global(.dark) .other-period-effects-datatable :global(.datatable thead) {
        background: rgb(30 41 59 / 0.4);
    }

    .other-period-effects-datatable :global(.datatable th) {
        padding: 0.5rem 0.75rem;
        font-size: 0.6875rem;
    }

    .other-period-effects-datatable :global(.datatable td) {
        padding: 0.5rem 0.75rem;
        font-size: 0.75rem;
        border-bottom-color: rgb(229 231 235 / 0.7);
        background: transparent;
    }

    :global(.dark) .other-period-effects-datatable :global(.datatable td) {
        border-bottom-color: rgb(30 41 59);
        background: transparent;
    }

    .other-period-effects-datatable :global(.datatable tbody tr) {
        background: transparent;
    }

    .other-period-effects-datatable :global(.datatable tbody tr:hover) {
        background: transparent;
    }

    :global(.dark) .other-period-effects-datatable :global(.datatable tbody tr) {
        background: transparent;
    }

    :global(.dark) .other-period-effects-datatable :global(.datatable tbody tr:hover) {
        background: transparent;
    }

    .other-period-effects-datatable :global(.datatable tbody tr:last-child td) {
        border-bottom: none;
    }
</style>
