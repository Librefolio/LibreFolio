<script lang="ts" module>
    import type {OnDemandAnalysis} from '$lib/stores/risk/riskPanelController.svelte';

    export type L4Tool = 'replay' | 'shock' | 'simulation';

    /** The one order the tools ever appear in: observed → assumed → modelled, whatever the order they were added in. */
    export const L4_TOOLS: readonly L4Tool[] = ['replay', 'shock', 'simulation'];

    /** The on-demand analysis each tool asks for: closing the tool drops that answer (D377). */
    export const L4_TOOL_ANALYSIS = {replay: 'replay', shock: 'stress', simulation: 'simulation'} as const satisfies Record<L4Tool, OnDemandAnalysis>;

    /** Per user, in this browser: the same set for the Dashboard and for a broker's page (D376). */
    export const L4_TOOLS_STORAGE_KEY = 'risk.l4.openTools';
</script>

<script lang="ts">
    import {AlertTriangle, Plus, X} from 'lucide-svelte';
    import {untrack, type Snippet} from 'svelte';

    import {_ as t} from '$lib/i18n';
    import {getUserStorage, setUserStorage} from '$lib/utils/storage';

    import RiskBetaBanner from '../RiskBetaBanner.svelte';

    /**
     * L4 — "what if…?", closed by default.
     *
     * L4 is the only level that is not homogeneous: it holds three things at
     * increasing distance from observed data, and the internal order has to make
     * that visible rather than leave the reader to guess.
     *
     *   historical replay → real returns from a real period
     *   hypothetical shock → deterministic, on an assumption the user states
     *   simulation         → a probabilistic model, on the model's assumptions
     *
     * THE READER PICKS THE TOOLS (D376, D377). Where a surface supplies more than one,
     * a selector adds them one at a time, each in a box of its own, always in the order
     * above. Nothing is open on a first visit; after that the tools left open last time
     * come back, remembered per user in this browser. The × of a box removes the tool
     * *and its answer*: the reader said they no longer want it, so the section's status
     * line must stop speaking of it too. Collapsing the whole section is another gesture
     * and keeps everything, as before. A surface with a single tool — Asset Global mounts
     * the replay alone — shows it at once, with no selector and no ×.
     *
     * Only the last rung is a model. That is the one and only place a beta
     * warning belongs: putting it on the section would tar the replay, which is
     * simply what happened, and a warning that is everywhere is read nowhere.
     *
     * WHY THE BETA BANNER LIVES HERE, AND ONLY HERE. It used to sit above every
     * risk surface, which said the whole subsystem was provisional. It is not
     * any more — L1, L2 and L3 rest on observed facts and have left beta. This
     * rung has not, and the reason is recorded rather than general: the
     * simulation answers the *window* rather than the portfolio, because the
     * bootstrap resamples each observation `horizon / observations` times, so a
     * short window under a long horizon extrapolates a single quarter across a
     * year. Asking for more history can silently return the same history, so the
     * denominator of any ratio guard is inflated and saturable — which is why no
     * threshold is shipped yet and the rung is still declared beta instead.
     *
     * Two notices, not one, and they are not redundant: the banner is about
     * *maturity* and is the one that gets deleted the day the defect is fixed;
     * the amber warning below it is about *epistemics* and is permanent, because
     * a model stays a model. Merging them would turn that future deletion into a
     * rewrite of prose.
     *
     * The banner is drawn inside the simulation's box only, and a box exists only for
     * a supplied tool: a surface that supplies no simulation snippet cannot inherit the
     * banner by accident. The scope of the claim is structural.
     */
    interface Props {
        /** The three rungs, supplied by the container. */
        replay?: Snippet;
        shock?: Snippet;
        simulation?: Snippet;
        /** Drops the answer of a tool the reader closes (D377). A surface with one tool has no ×, and needs none. */
        controller?: {resetAnalysis: (analysis: OnDemandAnalysis) => void};
    }

    let {replay, shock, simulation, controller}: Props = $props();

    const TITLE_KEYS: Record<L4Tool, string> = {replay: 'risk.levels.l4.replay', shock: 'risk.levels.l4.shock', simulation: 'risk.levels.l4.simulation'};
    const HINT_KEYS: Record<L4Tool, string> = {replay: 'risk.levels.l4.replayHint', shock: 'risk.levels.l4.shockHint', simulation: 'risk.levels.l4.simulationHint'};
    const DISTANCE: Record<L4Tool, string> = {replay: 'observed', shock: 'assumed', simulation: 'modelled'};

    let snippets = $derived<Record<L4Tool, Snippet | undefined>>({replay, shock, simulation});
    let supplied = $derived(L4_TOOLS.filter((tool) => snippets[tool] !== undefined));
    /** Only a surface with a choice has a selector, and only it remembers one. */
    let selectable = $derived(supplied.length > 1);

    function storedTools(available: readonly L4Tool[]): L4Tool[] {
        try {
            const parsed: unknown = JSON.parse(getUserStorage(L4_TOOLS_STORAGE_KEY, '[]'));
            return Array.isArray(parsed) ? L4_TOOLS.filter((tool) => available.includes(tool) && parsed.includes(tool)) : [];
        } catch {
            return [];
        }
    }

    // Read once, when the section mounts: collapsing L4 unmounts it, so reopening reads the set again.
    let openTools = $state<L4Tool[]>(untrack(() => (selectable ? storedTools(supplied) : [])));
    let shown = $derived(selectable ? openTools : supplied);
    let addable = $derived(selectable ? supplied.filter((tool) => !openTools.includes(tool)) : []);

    function remember(next: L4Tool[]): void {
        openTools = next;
        setUserStorage(L4_TOOLS_STORAGE_KEY, JSON.stringify(next));
    }

    function add(tool: L4Tool): void {
        remember(L4_TOOLS.filter((candidate) => candidate === tool || openTools.includes(candidate)));
    }

    function close(tool: L4Tool): void {
        remember(openTools.filter((candidate) => candidate !== tool));
        controller?.resetAnalysis(L4_TOOL_ANALYSIS[tool]);
    }
</script>

<div class="space-y-3" data-testid="risk-l4">
    {#if addable.length > 0}
        <div class="space-y-2" data-testid="risk-l4-tools">
            {#if openTools.length === 0}
                <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-l4-empty">{$t('risk.levels.l4.tools.empty')}</p>
            {/if}
            <div class="flex flex-wrap items-center gap-2">
                <span class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l4.tools.add')}</span>
                {#each addable as tool (tool)}
                    <button type="button" class="inline-flex items-center gap-1 rounded-full border border-gray-300 px-2.5 py-1 text-xs text-gray-700 hover:border-libre-green hover:text-libre-green dark:border-slate-600 dark:text-gray-200" data-testid="risk-l4-add-{tool}" onclick={() => add(tool)}>
                        <Plus size={12} />
                        {$t(TITLE_KEYS[tool])}
                    </button>
                {/each}
            </div>
        </div>
    {/if}

    {#each shown as tool (tool)}
        <div class={selectable ? 'rounded-lg border border-gray-200 p-3 dark:border-slate-700' : ''} data-testid="risk-l4-{tool}" data-distance={DISTANCE[tool]}>
            <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                    <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200">{$t(TITLE_KEYS[tool])}</h4>
                    <p class="mb-2 text-xs text-gray-500 dark:text-gray-400">{$t(HINT_KEYS[tool])}</p>
                </div>
                {#if selectable}
                    <button
                        type="button"
                        class="shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-slate-700 dark:hover:text-gray-200"
                        aria-label={$t('risk.levels.l4.tools.close', {values: {tool: $t(TITLE_KEYS[tool])}})}
                        data-testid="risk-l4-{tool}-close"
                        onclick={() => close(tool)}
                    >
                        <X size={14} />
                    </button>
                {/if}
            </div>
            {#if tool === 'simulation'}
                <div class="mb-2">
                    <RiskBetaBanner scope="simulation" />
                </div>
                <div class="mb-2 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-900/20" data-testid="risk-l4-model-warning">
                    <AlertTriangle size={14} class="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                    <p class="text-xs text-amber-800 dark:text-amber-200">{$t('risk.levels.l4.modelWarning')}</p>
                </div>
            {/if}
            {@render snippets[tool]?.()}
        </div>
    {/each}
</div>
