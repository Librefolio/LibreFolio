<script lang="ts">
    import type {Snippet} from 'svelte';
    import {AlertTriangle, ChevronDown} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';

    import type {ResultHealth, ResultReason} from './levelHelpers';
    import type {LevelMetadataRow} from './levelHelpers';
    import {translateErrorCode, translateOrRaw} from './levelHelpers';
    import {analyticNameKey} from './partialNotice';

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
         * Why those measurements fell short, as finished sentences.
         *
         * The companion to `health`, and deliberately separate: the status says a
         * number is incomplete, the reason says what to do about it. Each one is
         * worded by the caller (`resultReasons` with a translator): the backend's
         * own key and values, or its English sentence when those do not resolve —
         * never an i18n key built here from a code, which is how an unseen value
         * ends up printing its own key on screen.
         */
        reasons?: ResultReason[];
        /**
         * The codes of measurements that did not come back **at all**.
         *
         * Distinct from `reasons` in both content and provenance: `reasons` are
         * finished sentences, worded by the caller; these are identifiers, worded
         * here. Keeping them apart is what keeps each list's contract readable —
         * one the section shows as it is, one it always words.
         *
         * An empty level renders the same shape whether the analytic is out of
         * scope, short of history, or still in flight, and its single sentence
         * blames the user's data for a limit of the analytic. This is where the
         * difference gets back on screen.
         */
        errorCodes?: string[];
        /**
         * What the level's figures were computed over.
         *
         * `RiskResultFrame` publishes this and is used only by the legacy panel,
         * so on the day the four levels replace it the observation count would
         * leave the product. A window is half the meaning of a number: the same
         * asset pair correlates 0.96 over one month and 0.67 over one year.
         *
         * Optional, and absent renders nothing, so a level that passes no
         * provenance is unchanged rather than broken.
         */
        metadata?: LevelMetadataRow[];
        children?: Snippet;
        /**
         * Fired the first time the level is opened, and only then.
         *
         * Opening a drawer is a request for data; opening it *again* is not. The
         * distinction lives here so no level has to remember it.
         */
        onfirstopen?: () => void;
        /**
         * The manual page for this question, relative to `/mkdocs/`, shown as a book
         * icon on the right edge of the header — beside the toggle when the level is
         * collapsible, never inside it. Named `docsPath` so the cross-boundary link
         * check (`dev.py mkdocs check-links`) finds the literal a caller writes and
         * validates it. Optional and without default: a caller that passes nothing
         * renders exactly as before (agreed with Risk, F-3b V7).
         */
        docsPath?: string;
        /**
         * The icon's tooltip and accessible name. Defaults to the level's title. A caller
         * may pass a short explanation of the card instead — the correlation panel does,
         * at the developer's request (F-3b V7).
         */
        docsLabel?: string;
        /**
         * Actions drawn in the header, just before the manual's icon and in the same
         * row — beside the toggle when the level is collapsible, never inside it, so a
         * click on an action neither opens nor folds the level. Optional: a caller that
         * passes nothing renders exactly as before. Added for the column toggle of Asset
         * Global's loss table (the developer's review of L1°, 30/09; lent by Risk).
         */
        actions?: Snippet;
    }

    let {title, lead = '', level, collapsible = false, testId, health = [], reasons = [], errorCodes = [], metadata = [], children, onfirstopen, docsPath, docsLabel, actions}: Props = $props();

    /**
     * The failure sentences, recomputed on every locale change.
     *
     * `$t` is read *inside* the `$derived`, which is what makes switching
     * language re-word these. Translating in the helper module instead would
     * freeze the text at derivation time: correct on load, stale after a switch,
     * and stale in a way nothing turns red.
     */
    let errorSentences = $derived(errorCodes.map((code) => ({code, text: translateErrorCode(code, $t, 'risk.errors.unknown')})));

    /** `historical_var` is `historicalVar` in the catalogue; unknown codes stay raw. */
    function analyticName(code: string): string {
        return $t(analyticNameKey(code), {default: code});
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
        <!-- The toggle and the manual's icon side by side, never nested: a link inside a
             `<button>` is invalid HTML, and a click on the icon must open the manual, not fold
             the level. Tab order follows the reading order: the toggle first, then the icon. -->
        <div class="flex items-start gap-2 p-4">
            <button type="button" class="flex min-w-0 flex-1 items-start justify-between gap-3 text-left" onclick={toggle} data-testid="{testId}-toggle" aria-expanded={open}>
                {@render header()}
                <ChevronDown size={18} class="shrink-0 text-gray-400 transition-transform {open ? 'rotate-180' : ''}" />
            </button>
            {#if actions}
                {@render actions()}
            {/if}
            {#if docsPath}
                <DocsLink path={docsPath} label={docsLabel ?? title} icon="book" size={16} testId="{testId}-docs" />
            {/if}
        </div>
    {:else}
        <div class="p-4 pb-0">
            {@render header()}
        </div>
    {/if}

    {#if open}
        <div class="p-4 {collapsible ? 'pt-0' : ''}" data-testid="{testId}-body">
            {#if health.length > 0 || errorSentences.length > 0 || reasons.length > 0}
                <!-- One banner around what the level could not give, on every page that draws a
                     level (developer's review of D378, 06/10/2026: «migliorerei con un banner il
                     warning», «ovunque»). Loose amber lines read as a footnote, not as the reason
                     the level below is empty. Same tone, border and icon as the notice above the
                     levels (`RiskPartialNotice`), so the two read as one family. The icon sits
                     outside the three blocks: their testids, counts and text are unchanged. -->
                <div class="mb-3 flex items-start gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300" data-testid="{testId}-alert">
                    <AlertTriangle size={14} class="mt-px shrink-0" />
                    <div class="min-w-0 flex-1 space-y-1">
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
                            <p class="font-medium" data-testid="{testId}-health" data-count={health.length}>
                                {#each health as entry, index (entry.instanceId)}{index > 0 ? ' · ' : ''}{entry.label ? $t(entry.label) : analyticName(entry.code)}: {$t(`risk.states.${entry.status}`)}{/each}
                            </p>
                        {/if}
                        {#if errorSentences.length > 0}
                            <!-- Above `reasons` on purpose: a measurement that never ran
                                 explains the gap, while a warning only qualifies a number
                                 that is present. `data-code` carries the backend identifier
                                 for support without putting jargon in front of the reader. -->
                            <ul class="space-y-0.5" data-testid="{testId}-errors" data-count={errorSentences.length}>
                                {#each errorSentences as entry (entry.code)}
                                    <li data-testid="{testId}-error" data-code={entry.code}>{entry.text}</li>
                                {/each}
                            </ul>
                        {/if}
                        {#if reasons.length > 0}
                            <!-- `data-count` is the number of *distinct* sentences, while each
                                 entry publishes how many results carried it: identical text
                                 repeated would read as a rendering fault rather than as two
                                 affected assets, so the arity is published instead of drawn. -->
                            <ul class="space-y-0.5" data-testid="{testId}-reasons" data-count={reasons.length}>
                                {#each reasons as reason (reason.key)}
                                    <li data-testid="{testId}-reason" data-occurrences={reason.occurrences}>{reason.message}</li>
                                {/each}
                            </ul>
                        {/if}
                    </div>
                </div>
            {/if}
            {@render children?.()}
            {#if metadata.length > 0}
                <!-- Last, and closed: provenance qualifies the numbers above it,
                     so it follows them, and it is the answer to a question the
                     reader only sometimes asks. `data-rows` publishes how many
                     distinct sets of figures the level's analytics reported —
                     one is the ordinary case, two means they disagree about the
                     window, which is the case worth seeing. -->
                <details class="mt-3 border-t border-gray-100 pt-2 text-xs text-gray-500 dark:border-slate-700 dark:text-gray-400" data-testid="{testId}-metadata" data-rows={metadata.length}>
                    <summary class="flex cursor-pointer list-none items-center gap-1 font-medium">
                        <ChevronDown size={13} />
                        {$t('risk.metadata.title')}
                    </summary>
                    {#each metadata as row (row.key)}
                        <div class="mt-2" data-testid="{testId}-metadata-row" data-codes={row.codes.join(' ')}>
                            {#if metadata.length > 1}
                                <p class="mb-1 font-medium text-gray-600 dark:text-gray-300">{row.codes.map((code) => analyticName(code)).join(' · ')}</p>
                            {/if}
                            <dl class="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-4">
                                {#if row.observations !== null}
                                    <div>
                                        <dt>{$t('risk.metadata.observations')}</dt>
                                        <dd class="font-mono text-gray-700 dark:text-gray-200" data-testid="{testId}-metadata-observations">{row.observations}</dd>
                                    </div>
                                {/if}
                                {#if row.coverage !== null}
                                    <div>
                                        <dt>{$t('risk.metadata.coverage')}</dt>
                                        <dd class="font-mono text-gray-700 dark:text-gray-200">{(row.coverage * 100).toFixed(1)}%</dd>
                                    </div>
                                {/if}
                                {#if row.annualizationFactor !== null}
                                    <div>
                                        <dt>{$t('risk.metadata.annualization')}</dt>
                                        <dd class="font-mono text-gray-700 dark:text-gray-200">{row.annualizationFactor.toFixed(2)}</dd>
                                    </div>
                                {/if}
                                {#if row.returnBasis !== null}
                                    <div>
                                        <dt>{$t('risk.metadata.returnBasis')}</dt>
                                        <!-- Guarded, unlike `RiskResultFrame:108`, which builds this
                                             same key with no fallback: a basis the catalogue has not
                                             seen prints `risk.returnBasis.<value>` there. Here it
                                             degrades to the backend token, which is information. -->
                                        <dd class="font-mono text-gray-700 dark:text-gray-200" data-testid="{testId}-metadata-basis" data-basis={row.returnBasis}>{translateOrRaw('risk.returnBasis', row.returnBasis, $t)}</dd>
                                    </div>
                                {/if}
                            </dl>
                        </div>
                    {/each}
                </details>
            {/if}
        </div>
    {/if}
</section>

{#snippet header()}
    <div class="min-w-0">
        <!-- The title on the left, the manual's icon alone on the right edge of the card (the developer). -->
        <div class="flex items-start justify-between gap-2">
            <h3 class="text-base font-semibold text-gray-800 dark:text-gray-100" data-testid="{testId}-title">{title}</h3>
            {#if actions && !collapsible}
                <!-- The actions and the manual's icon share the right edge; the wrapper exists
                     only when there are actions, so a level without them is unchanged. -->
                <div class="flex shrink-0 items-start gap-2">
                    {@render actions()}
                    {#if docsPath}
                        <DocsLink path={docsPath} label={docsLabel ?? title} icon="book" size={16} testId="{testId}-docs" />
                    {/if}
                </div>
            {:else if docsPath && !collapsible}
                <!-- A collapsible level shows the icon beside its toggle instead (see the
                     section's head): inside the toggle it would be a link inside a `<button>`. -->
                <DocsLink path={docsPath} label={docsLabel ?? title} icon="book" size={16} testId="{testId}-docs" />
            {/if}
        </div>
        {#if lead}
            <!-- The sentence precedes the chart: the chart then demonstrates it,
                 instead of leaving the reader to infer the question from a shape. -->
            <p class="mt-1 text-sm text-gray-600 dark:text-gray-300" data-testid="{testId}-lead">{lead}</p>
        {/if}
    </div>
{/snippet}
