<script lang="ts">
    import type {TornadoRow} from './scenarioHelpers';

    /**
     * Horizontal bars, worst first.
     *
     * Replaces two HTML tables. The point of the shape is not decoration: a table
     * of signed percentages makes the reader rank the rows themselves, and the
     * one question a scenario answers is *which holding hurts most*. A bar gives
     * that away before the number is read.
     *
     * The bars share one scale, taken from the largest magnitude present, so two
     * rows are comparable to each other. A per-row scale would make every
     * scenario look equally severe, which is precisely the reassurance L4 must
     * not give.
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

    let scale = $derived(Math.max(...rows.map((row) => Math.abs(row.value)), Number.EPSILON));

    function percent(value: number): string {
        return `${value < 0 ? '−' : '+'}${(Math.abs(value) * 100).toFixed(2)}%`;
    }
</script>

{#if rows.length > 0}
    <ul class="space-y-1.5" data-testid={testId}>
        {#each rows as row (row.key)}
            {@const magnitude = (Math.abs(row.value) / scale) * 100}
            <li class="grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-2 text-xs" data-testid="{testId}-row" data-row-key={row.key}>
                <span class="truncate text-gray-600 dark:text-gray-300" title={label(row)}>{label(row)}</span>
                <span class="relative h-3 rounded bg-gray-100 dark:bg-slate-700">
                    <span class="absolute top-0 h-3 rounded {row.value < 0 ? 'bg-red-500/80 right-1/2' : 'bg-emerald-500/80 left-1/2'}" style="width: {(magnitude / 2).toFixed(2)}%" data-testid="{testId}-bar" data-sign={row.value < 0 ? 'loss' : 'gain'}></span>
                    <!-- The zero line is drawn, not implied: without it a reader
                         cannot tell a small gain from a small loss at a glance. -->
                    <span class="absolute left-1/2 top-0 h-3 w-px bg-gray-300 dark:bg-slate-500"></span>
                </span>
                <span class="tabular-nums text-right text-gray-700 dark:text-gray-200" data-testid="{testId}-value">
                    {percent(row.value)}{#if amount && amount(row)}<span class="ml-1 text-gray-500 dark:text-gray-400">{amount(row)}</span>{/if}
                </span>
            </li>
        {/each}
    </ul>
{/if}
