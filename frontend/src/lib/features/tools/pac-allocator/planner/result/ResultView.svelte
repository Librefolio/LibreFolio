<script lang="ts">
    import {untrack} from 'svelte';
    import {SvelteSet} from 'svelte/reactivity';
    import {t} from '$lib/i18n';
    import IssueList from '../shared/IssueList.svelte';
    import type {PlannerDraft} from '../draft.svelte';
    import {catalogCurrencyDigits} from '../format';
    import {presentIssues} from '../issues';
    import {listIssue} from '../labels';
    import type {RunOutcome} from '../run.svelte';
    import type {PacOrderRow, PlannerStep} from '../types';
    import {BUTTON_LINK, CARD, HINT, SECTION_TITLE} from '../ui';
    import AssetTable from './AssetTable.svelte';
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
    import WeightBars from './WeightBars.svelte';
    import {isReady, planLookup, resultNames, type WeightRow} from './model';

    interface Props {
        outcome: RunOutcome;
        draft: PlannerDraft;
        apiVersion: string;
        /** Wide layout: every section open, with Collapse all. Narrow: one section at a time. */
        wide: boolean;
        busy: boolean;
        ongoto: (step: PlannerStep) => void;
        onedit: () => void;
        oncalculate: () => void;
        onretry: () => void;
        ondiscard: () => void;
    }

    let {outcome, draft, apiVersion, wide, busy, ongoto, onedit, oncalculate, onretry, ondiscard}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result';
    const stale = $derived(outcome.built.fingerprint !== draft.fingerprint);
    const ready = $derived(outcome.kind === 'result' && isReady(outcome.result) ? outcome.result : null);
    const failure = $derived(outcome.kind === 'result' && !isReady(outcome.result) ? outcome.result : null);
    const solution = $derived(ready && 'primary_solution' in ready ? ready.primary_solution : null);
    const digits = $derived(catalogCurrencyDigits(ready ? ready.catalogs.currencies : []));
    const names = $derived(ready ? resultNames(ready) : null);
    const lookup = $derived(ready && names ? planLookup(ready, outcome.built.request, names) : null);
    const notes = $derived(ready ? presentIssues(ready.issues, draft, outcome.built.ids).map(listIssue) : []);
    const orderCount = $derived(solution ? solution.order_rows.length : 0);
    const hasPlan = $derived(solution !== null && orderCount + solution.funding_actions.length + solution.fx_actions.length > 0);
    const weights = $derived<WeightRow[]>(solution && names ? solution.asset_rows.map((row) => ({id: row.asset_id, label: [names.ticker(row.asset_id), names.asset(row.asset_id)].filter((part) => part).join(' '), target: row.target_weight, final: row.final_weight})) : []);
    const sections = $derived(solution ? ['allocation', 'exposures', 'assets', ...(hasPlan ? ['plan'] : []), 'ledger', 'proof'] : ['proof']);
    const resultState = $derived(outcome.kind === 'result' ? outcome.result.result_state : outcome.kind);

    const open = new SvelteSet<string>();
    let selectedOrder = $state<PacOrderRow | null>(null);

    // A new result or a layout change starts from the layout default: all open when wide, the first one when narrow.
    $effect(() => {
        const ids = sections;
        const all = wide;
        untrack(() => {
            open.clear();
            for (const id of all ? ids : ids.slice(0, 1)) open.add(id);
        });
    });

    function toggle(id: string): void {
        if (open.has(id)) {
            open.delete(id);
            return;
        }
        if (!wide) open.clear();
        open.add(id);
    }

    function toggleAll(): void {
        const collapse = open.size > 0;
        open.clear();
        if (!collapse) for (const id of sections) open.add(id);
    }

    const title = (id: string, fallback: string) => $t(`${KEY}.sections.${id}`, {default: fallback});
</script>

<div class="space-y-4" data-testid="pac-planner-result" data-state={resultState} data-stale={stale ? 'true' : 'false'}>
    {#if stale}
        <StaleBanner resultRevision={outcome.built.revision} draftRevision={draft.revision} onreview={() => ongoto('review')} {ondiscard} />
    {/if}

    {#if outcome.kind !== 'result'}
        <h2 id="pac-planner-result-title" tabindex="-1" class="text-lg font-semibold text-gray-900 focus:outline-none dark:text-gray-100">{$t(`${KEY}.title`, {default: 'Calculation result'})}</h2>
        <ToolErrorPanel {outcome} disabled={busy} {onretry} {onedit} />
    {:else if failure}
        <h2 id="pac-planner-result-title" tabindex="-1" class="text-lg font-semibold text-gray-900 focus:outline-none dark:text-gray-100">{$t(`${KEY}.title`, {default: 'Calculation result'})}</h2>
        <FailurePanel result={failure} {draft} ids={outcome.built.ids} {ongoto} {onedit} />
    {:else if ready && names && lookup && outcome.kind === 'result'}
        <OutcomeHeader result={ready} revision={outcome.built.revision} {apiVersion} {digits} disabled={busy} {onedit} {oncalculate} />
        <StateNotice result={ready} request={outcome.built.request} {names} {digits} {ongoto} {onedit} />

        {#if notes.length > 0}
            <section class="{CARD} space-y-2" aria-labelledby="pac-planner-notes-title" data-testid="pac-planner-notes">
                <h3 id="pac-planner-notes-title" class={SECTION_TITLE}>{$t(`${KEY}.notes`, {default: 'Notes from the backend'})}</h3>
                <IssueList items={notes} {ongoto} testid="pac-planner-notes-list" />
            </section>
        {/if}

        {#if solution}
            <KpiCards {solution} {digits} />
        {/if}

        {#if wide && sections.length > 1}
            <div class="flex justify-end">
                <button type="button" class={BUTTON_LINK} data-testid="pac-planner-result-toggle-all" onclick={toggleAll}>
                    {open.size > 0 ? $t(`${KEY}.collapseAll`, {default: 'Collapse all'}) : $t(`${KEY}.expandAll`, {default: 'Expand all'})}
                </button>
            </div>
        {/if}

        {#if solution}
            <ResultSection id="allocation" title={title('allocation', 'Allocation per Asset · % of the invested value')} open={open.has('allocation')} ontoggle={toggle}>
                <WeightBars rows={weights} testid="pac-planner-asset-weights" />
                <p class="mt-3 {HINT}">{$t(`${KEY}.allocationHint`, {default: "Backend weights only (target and after). No 'before': in a pure PAC it is 0 by construction."})}</p>
            </ResultSection>
            <ResultSection id="exposures" title={title('exposures', 'Exposures · public weights')} open={open.has('exposures')} ontoggle={toggle}>
                <ExposureSection rows={solution.exposure_rows} />
            </ResultSection>
            <ResultSection id="assets" title={title('assets', 'Assets · values in the valuation currency')} open={open.has('assets')} ontoggle={toggle}>
                <AssetTable rows={solution.asset_rows} accounting={solution.accounting} {names} {digits} />
            </ResultSection>
            {#if hasPlan}
                <ResultSection id="plan" title={title('plan', 'Operational plan · in the backend sequence order')} count={orderCount} open={open.has('plan')} ontoggle={toggle}>
                    <OperationalPlan {solution} {names} {lookup} {digits} onorder={(order) => (selectedOrder = order)} />
                </ResultSection>
            {/if}
            <ResultSection id="ledger" title={title('ledger', 'Balances per Broker and currency')} open={open.has('ledger')} ontoggle={toggle}>
                <LedgerTable rows={solution.ledger_rows} accounting={solution.accounting} {names} {digits} />
            </ResultSection>
        {/if}
        <ResultSection id="proof" title={title('proof', 'Proof and solver')} open={open.has('proof')} ontoggle={toggle}>
            <ProofPanel result={ready} metrics={outcome.metrics} batch={outcome.batch} {digits} />
        </ResultSection>

        {#if solution}
            <OrderDetail order={selectedOrder} fxActions={solution.fx_actions} {names} {lookup} {digits} onclose={() => (selectedOrder = null)} />
        {/if}
    {/if}
</div>
