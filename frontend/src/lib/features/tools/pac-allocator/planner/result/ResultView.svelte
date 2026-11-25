<script lang="ts">
    import {tick, untrack} from 'svelte';
    import {SvelteSet} from 'svelte/reactivity';
    import {t} from '$lib/i18n';
    import IssueList from '../shared/IssueList.svelte';
    import type {PlannerDraft} from '../draft.svelte';
    import {catalogCurrencyDigits} from '../format';
    import {presentIssues} from '../issues';
    import {listIssue} from '../labels';
    import type {RunOutcome} from '../run.svelte';
    import type {PlannerOrderRow, PlannerStep, RebalancerSolution} from '../types';
    import {BUTTON_LINK, CARD, SECTION_TITLE} from '../ui';
    import AssetTable from './AssetTable.svelte';
    import RebalancerAllocationTable from './RebalancerAllocationTable.svelte';
    import ExposureSection from './ExposureSection.svelte';
    import FailurePanel from './FailurePanel.svelte';
    import KpiCards from './KpiCards.svelte';
    import LedgerTable from './LedgerTable.svelte';
    import OperationalPlan from './OperationalPlan.svelte';
    import OrderDetail from './OrderDetail.svelte';
    import OutcomeHeader from './OutcomeHeader.svelte';
    import ProofPanel from './ProofPanel.svelte';
    import ResultSection from './ResultSection.svelte';
    import StaleBanner from './StaleBanner.svelte';
    import StateNotice from './StateNotice.svelte';
    import ToolErrorPanel from './ToolErrorPanel.svelte';
    import {hasPlanSteps, isReady, limitedEntries, notesBesideLimitsBanner, planLookup, planStepCount, resultNames} from './model';
    import {getPlannerProfile, domId, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    interface Props {
        outcome: RunOutcome;
        draft: PlannerDraft;
        apiVersion: string;
        busy: boolean;
        ongoto: (step: PlannerStep) => void;
        onedit: () => void;
        oncalculate: () => void;
        onretry: () => void;
        ondiscard: () => void;
    }

    let {outcome, draft, apiVersion, busy, ongoto, onedit, oncalculate, onretry, ondiscard}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result';
    const stale = $derived(outcome.built.fingerprint !== draft.fingerprint);
    const ready = $derived(outcome.kind === 'result' && isReady(outcome.result) ? outcome.result : null);
    const failure = $derived(outcome.kind === 'result' && !isReady(outcome.result) ? outcome.result : null);
    const solution = $derived(ready && 'primary_solution' in ready ? ready.primary_solution : null);
    const digits = $derived(catalogCurrencyDigits(ready ? ready.catalogs.currencies : []));
    const names = $derived(ready ? resultNames(ready) : null);
    const lookup = $derived(ready && names ? planLookup(ready, outcome.built.resolved, names) : null);
    /** The entries with a limit (F2, M20): the banner of a `ready_infeasible` result lists them. */
    const limits = $derived(limitedEntries(outcome.built.resolved));
    const notes = $derived(ready ? presentIssues(notesBesideLimitsBanner(ready, limits), draft, outcome.built.ids, profile.text).map(listIssue) : []);
    // A plan of transfers only, or conversions only, is still a plan (contract §6.3).
    const hasPlan = $derived(solution !== null && hasPlanSteps(solution));
    // Every numbered step and every order, in both Tools (TL-8 of project 67): `planStepCount`.
    const planCount = $derived(solution ? planStepCount(solution) : 0);
    const sections = $derived(solution ? ['allocation', ...(hasPlan ? ['plan'] : []), 'exposures', 'ledger', 'proof'] : ['proof']);
    /** R9.8: the allocation and the operational plan open, the rest on request. */
    const OPEN_BY_DEFAULT = new Set(['allocation', 'plan']);
    const resultState = $derived(outcome.kind === 'result' ? outcome.result.result_state : outcome.kind);

    const open = new SvelteSet<string>();
    let selectedOrder = $state<PlannerOrderRow | null>(null);

    // A new result starts from the default sections; without a solution the proof is the only one, and it opens.
    $effect(() => {
        const ids = sections;
        untrack(() => {
            open.clear();
            const defaults = ids.filter((id) => OPEN_BY_DEFAULT.has(id));
            for (const id of defaults.length > 0 ? defaults : ids.slice(0, 1)) open.add(id);
        });
    });

    const allOpen = $derived(sections.every((id) => open.has(id)));

    function toggle(id: string): void {
        if (open.has(id)) open.delete(id);
        else open.add(id);
    }

    function toggleAll(): void {
        const collapse = allOpen;
        open.clear();
        if (!collapse) for (const id of sections) open.add(id);
    }

    const title = (id: string, fallback: string) => $t(`${KEY}.sections.${id}`, {default: fallback});

    let root = $state<HTMLDivElement>();

    /** R10.7: opens «Proof and solver» and brings it into view; focus goes to its toggle, so the keyboard lands there too. */
    async function gotoProof(): Promise<void> {
        open.add('proof');
        await tick();
        const section = root?.querySelector<HTMLElement>('[data-section="proof"]');
        if (!section) return;
        const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        section.scrollIntoView({behavior: reduced ? 'auto' : 'smooth', block: 'start'});
        section.querySelector<HTMLElement>(`[data-testid="${testId('result-section-toggle', profile)}"]`)?.focus({preventScroll: true});
    }
</script>

<div bind:this={root} class="space-y-4" data-testid={testId('result', profile)} data-state={resultState} data-stale={stale ? 'true' : 'false'}>
    {#if stale}
        <StaleBanner resultRevision={outcome.built.revision} draftRevision={draft.revision} onreview={() => ongoto('review')} {ondiscard} />
    {/if}

    {#if outcome.kind !== 'result'}
        <h2 id={domId('result-title', profile)} tabindex="-1" class="text-lg font-semibold text-lf-primary focus:outline-none">{$t(`${KEY}.title`, {default: 'Calculation result'})}</h2>
        <ToolErrorPanel {outcome} disabled={busy} {onretry} {onedit} />
    {:else if failure}
        <h2 id={domId('result-title', profile)} tabindex="-1" class="text-lg font-semibold text-lf-primary focus:outline-none">{$t(`${KEY}.title`, {default: 'Calculation result'})}</h2>
        <FailurePanel result={failure} {draft} ids={outcome.built.ids} {ongoto} {onedit} />
    {:else if ready && names && lookup && outcome.kind === 'result'}
        <OutcomeHeader result={ready} revision={outcome.built.revision} {apiVersion} {digits} disabled={busy} {onedit} {oncalculate} ongotoproof={gotoProof} />
        <StateNotice result={ready} {names} {digits} {limits} {ongoto} {onedit} />

        {#if notes.length > 0}
            <section class="{CARD} space-y-2" aria-labelledby={domId('notes-title', profile)} data-testid={testId('notes', profile)}>
                <h3 id={domId('notes-title', profile)} class={SECTION_TITLE}>{$t(`${KEY}.notes`, {default: 'Notes on the calculation'})}</h3>
                <IssueList items={notes} {ongoto} testid={testId('notes-list', profile)} />
            </section>
        {/if}

        <KpiCards {solution} result={ready} metrics={outcome.metrics} {digits} />

        {#if sections.length > 1}
            <div class="flex justify-end">
                <button type="button" class={BUTTON_LINK} data-testid={testId('result-toggle-all', profile)} onclick={toggleAll}>
                    {allOpen ? $t(`${KEY}.collapseAll`, {default: 'Collapse all'}) : $t(`${KEY}.expandAll`, {default: 'Expand all'})}
                </button>
            </div>
        {/if}

        {#if solution}
            <ResultSection id="allocation" title={profile.text === 'rebalancer' ? $t('tools.portfolioRebalancer.planner.result.allocation.title') : title('allocation', 'Allocation per Asset')} open={open.has('allocation')} ontoggle={toggle}>
                <!-- F4a step 3: the Rebalancer's before / target / after with its cash entries and the uninvested row; the PAC keeps its table. -->
                {#if profile.text === 'rebalancer'}
                    <RebalancerAllocationTable solution={solution as unknown as RebalancerSolution} {names} {digits} {draft} />
                {:else}
                    <AssetTable rows={solution.asset_rows} accounting={solution.accounting} {names} {digits} {draft} />
                {/if}
            </ResultSection>
            {#if hasPlan}
                <ResultSection id="plan" title={title('plan', 'Operational plan')} count={planCount} open={open.has('plan')} ontoggle={toggle}>
                    <OperationalPlan {solution} {names} {lookup} {digits} {draft} onorder={(order) => (selectedOrder = order)} />
                </ResultSection>
            {/if}
            <ResultSection
                id="exposures"
                title={profile.text === 'rebalancer' ? $t('tools.portfolioRebalancer.planner.result.exposure.title') : title('exposures', 'Exposures – ideal vs actual')}
                help={profile.text === 'rebalancer'
                    ? $t('tools.portfolioRebalancer.planner.result.exposure.help')
                    : $t(`${KEY}.exposures.help`, {
                          default: 'How the Assets spread by country, type and sector, according to their declared exposures: the ideal distribution follows your target shares, the actual one the shares at the end of the plan. The charts do not change the plan.',
                      })}
                open={open.has('exposures')}
                ontoggle={toggle}
            >
                <!-- The Rebalancer's «Cash» rows are the last row of each bullet chart (F4a step 8); the PAC has none. -->
                <ExposureSection rows={solution.exposure_rows} />
            </ResultSection>
            <ResultSection id="ledger" title={title('ledger', 'Balances per Broker and currency')} open={open.has('ledger')} ontoggle={toggle}>
                <LedgerTable rows={solution.ledger_rows} accounting={solution.accounting} {names} {digits} {draft} />
            </ResultSection>
        {/if}
        <ResultSection id="proof" title={title('proof', 'Proof and solver')} open={open.has('proof')} ontoggle={toggle}>
            <ProofPanel result={ready} metrics={outcome.metrics} batch={outcome.batch} {digits} />
        </ResultSection>

        {#if solution}
            <OrderDetail order={selectedOrder} conversions={solution.conversions} {names} {lookup} {digits} onclose={() => (selectedOrder = null)} />
        {/if}
    {/if}
</div>
