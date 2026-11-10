<!--
  One stacked bar and its legend, linked: pointing at a segment highlights its legend entry, and the other way round.

  Shared by the Files page's space bar (`StorageBar`) and the planner's «Where the time went» bar
  (`BackendTimingBar`), which drew the same thing twice. The parts the two differ in are props: the segments (a share of
  the bar and a fill class, plus any `data-*` the caller wants on the segment), the look of the bar and of the legend, the
  test ids, and the content of a legend row (a snippet: the dot comes from here).

  Pointer events, so a press on a touch screen does it too; focus inside a legend row counts as well. The legend already
  says everything in text: the highlight only links the two.

  Published state: `data-active` (`true|false`) on every segment and every legend row; `data-segment` is the segment's id.
-->
<script lang="ts" generics="S extends LinkedSegment">
    import type {Snippet} from 'svelte';
    import type {LinkedBarMarker, LinkedSegment, LinkedStackedBarTestIds} from './linkedStackedBar';

    interface Props {
        segments: S[];
        /** The bar's own classes (height, rounding, border, background, separators). */
        barClass: string;
        /** When given the bar is an image with this label; otherwise it is decoration (the legend says it all). */
        barLabel?: string;
        /** The legend list's classes. */
        legendClass: string;
        /** The classes of every legend row, before the highlight. */
        itemClass?: string;
        /** The dot before the content of a row. */
        dotClass?: string;
        /** The background of the row under the pointer. */
        activeItemClass?: string;
        /** A segment never narrower than this many pixels (a thin phase stays visible). */
        minSegmentPx?: number;
        testIds: LinkedStackedBarTestIds;
        /** What follows the dot in a legend row. */
        row: Snippet<[S]>;
        /** Drawn between the bar and the legend (a summary line). */
        between?: Snippet;
        /**
         * A tick on the bar at `percent`, named by `label` under it, and the part of the bar after it in red stripes: what is
         * past a limit (the space bar over its limit, C9-4). Without it the bar is drawn as it always was.
         */
        marker?: LinkedBarMarker | null;
    }

    let {segments, barClass, barLabel, legendClass, itemClass = '', dotClass = 'h-2.5 w-2.5 rounded-full border border-lf-subtle', activeItemClass = 'bg-lf-hover', minSegmentPx = 0, testIds, row, between, marker = null}: Props = $props();

    let pointed = $state<string | null>(null);
    /** The segment under the pointer, if it is still drawn: a new read may have dropped it. */
    const active = $derived(segments.some((segment) => segment.id === pointed) ? pointed : null);
    const dimmed = (id: string) => active !== null && active !== id;
</script>

{#snippet bar()}
    <div class="{barClass}{marker ? ' relative' : ''}" role={barLabel === undefined ? undefined : 'img'} aria-label={barLabel} aria-hidden={barLabel === undefined ? 'true' : undefined} data-testid={testIds.bar}>
        {#each segments as segment (segment.id)}
            <div
                class="h-full transition-opacity {segment.fill} {dimmed(segment.id) ? 'opacity-30' : ''}"
                style="width: {segment.percent}%;{minSegmentPx > 0 ? ` min-width: ${minSegmentPx}px;` : ''}"
                data-testid={testIds.segment(segment.id)}
                data-segment={segment.id}
                data-active={active === segment.id ? 'true' : 'false'}
                {...segment.attrs}
                onpointerenter={() => (pointed = segment.id)}
                onpointerleave={() => (pointed = null)}
            ></div>
        {/each}
        {#if marker}
            <div class="lf-past-marker pointer-events-none absolute inset-y-0 right-0" style="left: {marker.percent}%;" data-testid="{testIds.bar}-past" aria-hidden="true"></div>
        {/if}
    </div>
{/snippet}

{#if marker}
    <!-- The tick and its label sit outside the bar, which clips what overflows it. -->
    <div class="relative pb-5" data-testid="{testIds.bar}-marked">
        {@render bar()}
        <div class="pointer-events-none absolute -top-1 bottom-4 w-0.5 -translate-x-1/2 rounded bg-lf-danger" style="left: {marker.percent}%;" data-testid="{testIds.bar}-marker" aria-hidden="true"></div>
        <span class="pointer-events-none absolute bottom-0 whitespace-nowrap text-xs font-medium text-lf-danger {marker.percent > 80 ? '-translate-x-full' : marker.percent < 20 ? '' : '-translate-x-1/2'}" style="left: {marker.percent}%;" data-testid="{testIds.bar}-marker-label">{marker.label}</span>
    </div>
{:else}
    {@render bar()}
{/if}

{@render between?.()}

<ul class={legendClass} data-testid={testIds.legend}>
    {#each segments as segment (segment.id)}
        <li
            class="flex items-center gap-2 transition-[opacity,background-color] {itemClass} {active === segment.id ? activeItemClass : ''} {dimmed(segment.id) ? 'opacity-50' : ''}"
            data-testid={testIds.item(segment.id)}
            data-segment={segment.id}
            data-active={active === segment.id ? 'true' : 'false'}
            onpointerenter={() => (pointed = segment.id)}
            onpointerleave={() => (pointed = null)}
            onfocusin={() => (pointed = segment.id)}
            onfocusout={() => (pointed = null)}
        >
            <span class="inline-block shrink-0 {dotClass} {segment.fill}" aria-hidden="true"></span>
            {@render row(segment)}
        </li>
    {/each}
</ul>

<style>
    /* What is past the marker: red stripes over the segments, in the danger role of the theme. */
    .lf-past-marker {
        background-image: repeating-linear-gradient(135deg, var(--lf-danger) 0 4px, transparent 4px 8px);
        opacity: 0.85;
    }
</style>
