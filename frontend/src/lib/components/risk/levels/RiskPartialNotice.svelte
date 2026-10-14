<script lang="ts">
    import {AlertTriangle, Info} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';

    import type {ResultHealth, ResultReason} from './levelHelpers';
    import {analyticNameKey} from './partialNotice';

    /**
     * What is partial, and why, said once above the levels (developer's decision of 24/09/2026),
     * cause first and effect after it (developer's decision of 30/09/2026).
     *
     * The levels used to repeat it one by one, so the same carried-over price or excluded asset
     * read as four separate problems. The reasons come first because they are what the reader can
     * act on; the measurements they cost follow, grouped under the question of the level that
     * shows them, so the reader knows where on the page to read them with care. The title names
     * the cause when there is one to name; otherwise it says partial, or — for a note on complete
     * results, still worth reading — notes.
     */
    type Level = 1 | 2 | 3;

    interface Props {
        partial: ResultHealth[];
        reasons: ResultReason[];
        /**
         * The level that renders each measurement, by instance id, built by the panel from the
         * slices the levels render. A measurement with no level is still named, in a group of its
         * own at the end: dropped, it would read as whole.
         */
        levelOf?: Readonly<Record<string, Level>>;
    }

    let {partial, reasons, levelOf = {}}: Props = $props();

    /**
     * Informative only when every reason states the one permanent cause (developer's decision of
     * 29/09/2026): a holding with no price source and no price ever recorded reads the same
     * tomorrow, a standing fact about the portfolio rather than a fault of this answer. Amber for
     * anything else — and `every` over a non-empty list, so a reason stating no cause (a
     * data-quality note, or merged warnings that disagreed and lost theirs) never passes for one.
     */
    let tone = $derived<'info' | 'warning'>(reasons.length > 0 && reasons.every((entry) => entry.reason === 'no_price_source') ? 'info' : 'warning');

    /** Same shade weights in both tones; blue and `Info` as the app's `InfoBanner` pairs them. */
    const TONE_CLASSES = {
        info: 'border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-300',
        warning: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300',
    } as const;
    const CHIP_CLASSES = {
        info: 'border-blue-200 bg-white/70 dark:border-blue-900/60 dark:bg-slate-900/40',
        warning: 'border-amber-200 bg-white/70 dark:border-amber-900/60 dark:bg-slate-900/40',
    } as const;

    let title = $derived(partial.length === 0 ? $t('risk.levels.notice.notesTitle') : tone === 'info' ? $t('risk.levels.notice.noPriceSourceTitle') : $t('risk.levels.notice.partialTitle'));

    /** The partial measurements under the level that shows them, in page order; unplaced ones last. */
    let groups = $derived.by(() => {
        const byLevel = new Map<Level | null, ResultHealth[]>();
        for (const entry of partial) {
            const level = levelOf[entry.instanceId] ?? null;
            byLevel.set(level, [...(byLevel.get(level) ?? []), entry]);
        }
        return ([1, 2, 3, null] as const).filter((level) => byLevel.has(level)).map((level) => ({level, entries: byLevel.get(level) ?? []}));
    });

    /** The level's question, as its frame titles it on the page. One literal key per level. */
    function levelTitle(level: Level): string {
        if (level === 1) return $t('risk.levels.l1.title');
        if (level === 2) return $t('risk.levels.l2.title');
        return $t('risk.levels.l3.title');
    }

    function measurementName(entry: ResultHealth): string {
        return entry.label ? $t(entry.label) : $t(analyticNameKey(entry.code), {default: entry.code});
    }
</script>

{#if partial.length > 0 || reasons.length > 0}
    <div class="rounded-lg border px-3 py-2 text-xs {TONE_CLASSES[tone]}" data-testid="risk-partial-notice" data-partial-count={partial.length} data-tone={tone}>
        <p class="flex items-center gap-1.5 font-medium" data-testid="risk-partial-title">
            {#if tone === 'info'}
                <Info size={14} class="shrink-0" />
            {:else}
                <AlertTriangle size={14} class="shrink-0" />
            {/if}
            {title}
        </p>
        {#if reasons.length > 0}
            <ul class="mt-1 list-disc space-y-0.5 pl-5" data-testid="risk-partial-reasons" data-count={reasons.length}>
                {#each reasons as reason (reason.key)}
                    <li data-testid="risk-partial-reason" data-occurrences={reason.occurrences}>{reason.message}</li>
                {/each}
            </ul>
        {/if}
        {#if partial.length > 0}
            <!-- Per instance, never per analytic code: the two VaR horizons share a code and are told
                 apart by their label. `data-count` publishes how many measurements are partial — one
                 chip each, since a measurement two levels read is placed once, under the first. -->
            <div class="mt-2 space-y-1" data-testid="risk-partial-measurements" data-count={partial.length}>
                <p class="font-medium">{$t('risk.levels.notice.affected')}</p>
                {#each groups as group (group.level ?? 'none')}
                    <div class="flex flex-wrap items-center gap-1.5" data-testid="risk-partial-level" data-level={group.level ?? 'none'}>
                        {#if group.level !== null}
                            <span class="opacity-80">{levelTitle(group.level)}</span>
                        {/if}
                        {#each group.entries as entry (entry.instanceId)}
                            <span class="rounded-full border px-2 py-0.5 {CHIP_CLASSES[tone]}" data-testid="risk-partial-measurement" data-instance={entry.instanceId}>{measurementName(entry)}</span>
                        {/each}
                    </div>
                {/each}
            </div>
        {/if}
    </div>
{/if}
