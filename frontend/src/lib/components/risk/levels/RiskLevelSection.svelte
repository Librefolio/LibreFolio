<script lang="ts">
    import type {Snippet} from 'svelte';
    import {ChevronDown} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';

    import type {ResultHealth, ResultReason} from './levelHelpers';

    /**
     * The frame around one of the four levels.
     *
     * A level is a *question*, not an analytic: it may aggregate several backend
     * outputs, or none yet. That is why this frame knows nothing about results —
     * it carries the question, the sentence the data answers it with, and the
     * disclosure state, and leaves the answering to its children.
     */
    interface Props {
        /** The question this level asks, in the reader's language. */
        title: string;
        /**
         * The one-line answer, generated from the data.
         *
         * Empty when the data says nothing worth a headline: an invented lead is
         * worse than none, because the reader cannot tell the two apart.
         */
        lead?: string;
        /** Ordinal shown before the question, so the scale is legible at a glance. */
        level: 1 | 2 | 3 | 4;
        /** Collapsible levels start closed; the rest are always open. */
        collapsible?: boolean;
        testId: string;
        /**
         * Measurements behind this level that did not come back whole.
         *
         * Rendered rather than swallowed: a level that silently drops the rung it
         * could not compute shows a shorter list, and a shorter list looks exactly
         * like a portfolio with less to say. Only one of the two is worth retrying.
         */
        health?: ResultHealth[];
        /**
         * Why those measurements fell short, in the backend's own words.
         *
         * The companion to `health`, and deliberately separate: the status says a
         * number is incomplete, the reason says what to do about it. Shown
         * verbatim — these are backend strings, and routing them through i18n
         * keys built at runtime is how an unseen value ends up printing its own
         * key on screen.
         */
        reasons?: ResultReason[];
        children?: Snippet;
        /**
         * Fired the first time the level is opened, and only then.
         *
         * Opening a drawer is a request for data; opening it *again* is not. The
         * distinction lives here so no level has to remember it.
         */
        onfirstopen?: () => void;
    }

    let {title, lead = '', level, collapsible = false, testId, health = [], reasons = [], children, onfirstopen}: Props = $props();

    /** `historical_var` is `historicalVar` in the catalogue; unknown codes stay raw. */
    function analyticName(code: string): string {
        const camel = code.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
        return $t(`risk.analytics.${camel}.name`, {default: code});
    }

    let manuallyOpen = $state(false);
    let hasOpened = $state(false);
    // Derived rather than seeded from `collapsible`: a `$state` initialiser reads
    // the prop once and then stops listening, so a section that later became
    // collapsible would stay stuck in whatever state it was born in.
    let open = $derived(!collapsible || manuallyOpen);

    function toggle(): void {
        manuallyOpen = !manuallyOpen;
        if (manuallyOpen && !hasOpened) {
            hasOpened = true;
            onfirstopen?.();
        }
    }
</script>

<section class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm" data-testid={testId} data-level={level} data-open={open}>
    {#if collapsible}
        <button type="button" class="w-full flex items-start justify-between gap-3 p-4 text-left" onclick={toggle} data-testid="{testId}-toggle" aria-expanded={open}>
            {@render header()}
            <ChevronDown size={18} class="shrink-0 text-gray-400 transition-transform {open ? 'rotate-180' : ''}" />
        </button>
    {:else}
        <div class="p-4 pb-0">
            {@render header()}
        </div>
    {/if}

    {#if open}
        <div class="p-4 {collapsible ? 'pt-0' : ''}" data-testid="{testId}-body">
            {#if health.length > 0}
                <!-- `data-count` is the disclosure's own arity, published for the
                     same reason `risk-replay-audit` publishes its proxy and
                     exclusion counts: the entries are rendered as one sentence,
                     so *how many* measurements fell short is otherwise legible
                     only by reading a translated string. It is not decoration —
                     L1 asks `historical_var` twice and the two horizons share an
                     analytic code, so a disclosure that deduped by code would
                     show one entry, look entirely plausible, and hide exactly
                     the case the row exists for. -->
                <p class="mb-3 text-xs text-amber-700 dark:text-amber-300" data-testid="{testId}-health" data-count={health.length}>
                    {#each health as entry, index (entry.instanceId)}{index > 0 ? ' · ' : ''}{entry.label ? $t(entry.label) : analyticName(entry.code)}: {$t(`risk.states.${entry.status}`)}{/each}
                </p>
            {/if}
            {#if reasons.length > 0}
                <!-- `data-count` is the number of *distinct* sentences, while each
                     entry publishes how many results carried it: identical text
                     repeated would read as a rendering fault rather than as two
                     affected assets, so the arity is published instead of drawn. -->
                <ul class="mb-3 space-y-1 text-xs text-amber-700 dark:text-amber-300" data-testid="{testId}-reasons" data-count={reasons.length}>
                    {#each reasons as reason (reason.key)}
                        <li data-testid="{testId}-reason" data-occurrences={reason.occurrences}>{reason.message}</li>
                    {/each}
                </ul>
            {/if}
            {@render children?.()}
        </div>
    {/if}
</section>

{#snippet header()}
    <div class="min-w-0">
        <h3 class="text-base font-semibold text-gray-800 dark:text-gray-100" data-testid="{testId}-title">{title}</h3>
        {#if lead}
            <!-- The sentence precedes the chart: the chart then demonstrates it,
                 instead of leaving the reader to infer the question from a shape. -->
            <p class="mt-1 text-sm text-gray-600 dark:text-gray-300" data-testid="{testId}-lead">{lead}</p>
        {/if}
    </div>
{/snippet}
