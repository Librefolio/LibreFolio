<!--
  R10.9: where the backend time of one item went, as one stacked bar beside the shared «Backend
  timings» box. The segments are the leaf phases of `ToolItemMetrics`, in the order they run;
  `execution_ms` contains startup and the worker phases, so it is not a segment. What the total holds
  beyond the leaves is «not attributed». A phase the backend did not observe (`null`) is left out,
  never drawn as 0. Durations only: no amount is shown here.
  R11.9: pointing at a segment highlights its legend entry, and the other way round (pointer
  events, so a press on a touch screen does it too; focus inside an entry, its «?», counts as well).
  The legend already says everything in text: the highlight only links the two.
-->
<script lang="ts">
    import {ChartBarStacked} from 'lucide-svelte';
    import {locale, t} from '$lib/i18n';
    import type {ToolItemMetrics} from '$lib/features/tools/contracts';
    import HelpTip from '../shared/HelpTip.svelte';
    import {HINT} from '../ui';

    interface Props {
        metrics: ToolItemMetrics;
    }

    let {metrics}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.timing';

    const LEAVES = [
        {key: 'queue_wait_ms', label: 'tools.metrics.queueWait', fallback: 'Queue wait', colour: 'bg-slate-400 dark:bg-slate-500'},
        {key: 'startup_ms', label: 'tools.metrics.startup', fallback: 'Worker startup', colour: 'bg-sky-500 dark:bg-sky-400'},
        {key: 'input_validation_ms', label: 'tools.metrics.inputValidation', fallback: 'Input validation', colour: 'bg-violet-500 dark:bg-violet-400'},
        {key: 'compute_ms', label: 'tools.metrics.compute', fallback: 'Compute', colour: 'bg-emerald-500 dark:bg-emerald-400'},
        {key: 'serialization_ms', label: 'tools.metrics.serialization', fallback: 'Output serialization', colour: 'bg-amber-500 dark:bg-amber-400'},
        {key: 'output_validation_ms', label: 'tools.metrics.outputValidation', fallback: 'Output validation', colour: 'bg-rose-500 dark:bg-rose-400'},
        {key: 'cleanup_ms', label: 'tools.metrics.cleanup', fallback: 'Cleanup', colour: 'bg-teal-500 dark:bg-teal-400'},
    ] as const satisfies readonly {key: keyof ToolItemMetrics; label: string; fallback: string; colour: string}[];

    interface Segment {
        id: string;
        label: string;
        ms: number;
        /** Fraction of the bar: of the total, or of the phase sum when the phases exceed it. */
        share: number;
        colour: string;
        help: string | null;
    }

    function measured(value: unknown): value is number {
        return typeof value === 'number' && Number.isFinite(value) && value > 0;
    }

    const total = $derived(measured(metrics.total_ms) ? metrics.total_ms : null);

    const segments = $derived.by((): Segment[] => {
        if (total === null) return [];
        const leaves = LEAVES.flatMap((leaf) => {
            const ms = metrics[leaf.key];
            return measured(ms) ? [{id: leaf.key, label: $t(leaf.label, {default: leaf.fallback}), ms, colour: leaf.colour, help: null}] : [];
        });
        const sum = leaves.reduce((acc, leaf) => acc + leaf.ms, 0);
        const rest = Math.max(0, total - sum);
        const all =
            rest > 0
                ? [
                      ...leaves,
                      {
                          id: 'unattributed',
                          label: $t(`${KEY}.unattributed`, {default: 'Not attributed'}),
                          ms: rest,
                          colour: 'bg-gray-300 dark:bg-gray-600',
                          help: $t(`${KEY}.unattributedHelp`, {default: 'Time inside the total that no phase measures: loading the tool, preparing it, handing over the result.'}),
                      },
                  ]
                : leaves;
        // Integer milliseconds measured separately can add up to a little more than the total.
        const scale = Math.max(total, sum);
        return all.map((segment) => ({...segment, share: segment.ms / scale}));
    });

    const formats = $derived({
        ms: new Intl.NumberFormat($locale ?? 'en', {maximumFractionDigits: 0}),
        share: new Intl.NumberFormat($locale ?? 'en', {style: 'percent', maximumFractionDigits: 1}),
    });

    let pointed = $state<string | null>(null);
    /** The phase under the pointer, if it is still drawn: a new result may have dropped it. */
    const active = $derived(segments.some((segment) => segment.id === pointed) ? pointed : null);
    const dimmed = (id: string) => active !== null && active !== id;

    function duration(ms: number): string {
        return $t('tools.metrics.milliseconds', {default: '{value} ms', values: {value: formats.ms.format(ms)}});
    }
</script>

{#if total !== null && segments.length > 0}
    <section class="min-w-0 rounded-xl border border-gray-200 bg-white p-4 text-gray-900 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100" aria-labelledby="pac-planner-timing-title" data-testid="pac-planner-timing">
        <h4 id="pac-planner-timing-title" class="flex items-center gap-2 text-sm font-semibold">
            <ChartBarStacked size={16} aria-hidden="true" class="shrink-0" />
            {$t(`${KEY}.title`, {default: 'Where the time went'})}
        </h4>
        <p class="mt-2 {HINT}">
            {$t(`${KEY}.hint`, {
                default: 'One colour per phase, in the order they run, over the item total ({total}). Phases not measured, or under 1 ms, are left out.',
                values: {total: duration(total)},
            })}
        </p>
        <div class="mt-3 flex h-4 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-900" aria-hidden="true" data-testid="pac-planner-timing-bar">
            {#each segments as segment (segment.id)}
                <div
                    class="h-full border-r border-white transition-opacity last:border-r-0 dark:border-gray-800 {segment.colour} {dimmed(segment.id) ? 'opacity-30' : ''}"
                    style="width: {segment.share * 100}%; min-width: 3px;"
                    data-testid="pac-planner-timing-segment"
                    data-phase={segment.id}
                    data-active={active === segment.id ? 'true' : 'false'}
                    onpointerenter={() => (pointed = segment.id)}
                    onpointerleave={() => (pointed = null)}
                ></div>
            {/each}
        </div>
        <ul class="mt-3 grid grid-cols-1 gap-x-3 gap-y-1 sm:grid-cols-2 lg:grid-cols-3" data-testid="pac-planner-timing-legend">
            {#each segments as segment (segment.id)}
                <li
                    class="flex min-w-0 items-center gap-2 rounded-md px-1.5 py-1 text-xs transition-[opacity,background-color] {active === segment.id ? 'bg-gray-100 dark:bg-gray-700' : ''} {dimmed(segment.id) ? 'opacity-50' : ''}"
                    data-testid="pac-planner-timing-item"
                    data-phase={segment.id}
                    data-active={active === segment.id ? 'true' : 'false'}
                    onpointerenter={() => (pointed = segment.id)}
                    onpointerleave={() => (pointed = null)}
                    onfocusin={() => (pointed = segment.id)}
                    onfocusout={() => (pointed = null)}
                >
                    <span class="h-2.5 w-2.5 shrink-0 rounded-sm {segment.colour}" aria-hidden="true"></span>
                    <span class="flex min-w-0 flex-1 items-center gap-1 text-gray-600 dark:text-gray-300">
                        <span class="min-w-0 break-words">{segment.label}</span>
                        {#if segment.help}<HelpTip label={segment.label} help={segment.help} testid="pac-planner-timing-help" />{/if}
                    </span>
                    <span class="shrink-0 tabular-nums text-gray-900 dark:text-gray-100">{duration(segment.ms)} · {formats.share.format(segment.share)}</span>
                </li>
            {/each}
        </ul>
    </section>
{/if}
