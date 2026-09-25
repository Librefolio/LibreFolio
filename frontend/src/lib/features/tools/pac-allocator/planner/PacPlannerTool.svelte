<script lang="ts">
    /**
     * PAC allocator 2.0.0 renderer (C0 delta §3–§6, UiTarget §13–§16).
     *
     * The Tool Host owns the h1, the back link, the docs link, Refresh and the
     * version line; this shell owns the nine-step wizard and the result view.
     * Every figure comes from the backend: the wizard only edits the draft.
     */
    import {onDestroy, onMount, tick} from 'svelte';
    import {MediaQuery, SvelteSet} from 'svelte/reactivity';
    import {afterNavigate, beforeNavigate, goto} from '$app/navigation';
    import {ArrowLeft, ArrowRight, ChevronDown, ChevronUp, CircleStop} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import {userSettings} from '$lib/stores/app/settings';
    import {assertToolAccount, type CompatibleToolDescriptor} from '../../contracts';
    import {PLANNER_CONTRACT_VERSION, PLANNER_TOOL_CODE} from './defaults';
    import {PlannerDraft} from './draft.svelte';
    import {STEP_FALLBACKS, listLocalProblem, stepKey, type ListedIssue} from './labels';
    import {defaultPolicy} from './policies';
    import {buildRequest, localProblems} from './request';
    import {PlannerRun} from './run.svelte';
    import {PLANNER_STEPS, type PlannerStep} from './types';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, CARD, NOTICE, SECTION_TITLE} from './ui';
    import IssueList from './shared/IssueList.svelte';
    import StepNav from './shell/StepNav.svelte';
    import SummaryPanel from './shell/SummaryPanel.svelte';
    import ScenarioStep from './steps/ScenarioStep.svelte';
    import LiquidityStep from './steps/LiquidityStep.svelte';
    import BrokersStep from './steps/BrokersStep.svelte';
    import AssetsStep from './steps/AssetsStep.svelte';
    import RoutingStep from './steps/RoutingStep.svelte';
    import TargetsStep from './steps/TargetsStep.svelte';
    import FxStep from './steps/FxStep.svelte';
    import StrategyStep from './steps/StrategyStep.svelte';
    import ReviewStep from './steps/ReviewStep.svelte';
    import BusyPanel from './result/BusyPanel.svelte';
    import ResultView from './result/ResultView.svelte';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        descriptor: CompatibleToolDescriptor<typeof PLANNER_TOOL_CODE, typeof PLANNER_CONTRACT_VERSION>;
        accountGeneration: number;
    }

    let {descriptor, accountGeneration}: Props = $props();

    const STEP_TITLE_ID = 'pac-planner-step-title';
    const STEP_ALERT_ID = 'pac-planner-step-alert';
    const BUSY_TITLE_ID = 'pac-planner-busy-title';
    const RESULT_TITLE_ID = 'pac-planner-result-title';
    const STOPPED_TITLE_ID = 'pac-planner-stopped-title';
    const SUMMARY_ID = 'pac-planner-summary-disclosure';

    // Props are fixed for the life of a mount: an account change unmounts the renderer.
    const draft = new PlannerDraft(userSettings.get()?.base_currency ?? '', defaultPolicy());
    const run = new PlannerRun(() => descriptor);

    const desktop = new MediaQuery('min-width: 1200px');
    const tablet = new MediaQuery('min-width: 900px');

    let view = $state<'wizard' | 'result'>('wizard');
    let step = $state<PlannerStep>('scenario');
    const visited = new SvelteSet<PlannerStep>(['scenario']);
    /** The step whose Continue found problems; the alert lists them until they are fixed. */
    let alertStep = $state<PlannerStep | null>(null);
    let summaryOpen = $state(false);
    /** Problems found while building the request, valid only for the draft they describe. */
    let buildFailure = $state.raw<{fingerprint: string; problems: ListedIssue[]} | null>(null);
    let leaveTarget = $state.raw<{url: URL; delta: number | null; external: boolean} | null>(null);
    let allowLeave = false;
    let destroyed = false;

    const apiVersion = $derived(descriptor.contract_version);
    const uiVersion = $derived(descriptor.ui.version);
    const index = $derived(PLANNER_STEPS.indexOf(step));
    const problems = $derived(localProblems(draft).map(listLocalProblem));
    const reviewProblems = $derived.by(() => {
        if (problems.length > 0) return problems;
        return buildFailure !== null && buildFailure.fingerprint === draft.fingerprint ? buildFailure.problems : [];
    });
    const problemSteps = $derived(new Set(reviewProblems.flatMap((item) => (item.step ? [item.step] : []))));
    const alertItems = $derived(alertStep === step ? problems.filter((item) => item.step === step) : []);
    const runState = $derived.by(() => {
        if (run.busy) return 'busy';
        const outcome = run.outcome;
        if (!outcome) return run.stopped ? 'stopped' : 'idle';
        return outcome.kind === 'result' ? outcome.result.result_state : outcome.kind;
    });
    const navVariant = $derived(desktop.current ? 'vertical' : tablet.current ? 'horizontal' : 'compact');
    const leaveCounts = $derived({assets: draft.data.assets.length, sources: draft.data.cash.length + draft.data.contributions.length});

    async function focusFirst(...ids: string[]): Promise<void> {
        await tick();
        if (destroyed) return;
        for (const id of ids) {
            const element = document.getElementById(id);
            if (element) {
                element.focus();
                return;
            }
        }
    }

    function go(target: PlannerStep): void {
        step = target;
        visited.add(target);
        alertStep = null;
        void focusFirst(STEP_TITLE_ID);
    }

    function next(): void {
        if (problems.some((item) => item.step === step)) {
            alertStep = step;
            void focusFirst(STEP_ALERT_ID);
            return;
        }
        if (index < PLANNER_STEPS.length - 1) go(PLANNER_STEPS[index + 1]);
    }

    function back(): void {
        if (index > 0) go(PLANNER_STEPS[index - 1]);
    }

    function editStep(target: PlannerStep): void {
        view = 'wizard';
        go(target);
    }

    function showResult(): void {
        view = 'result';
        void focusFirst(RESULT_TITLE_ID, BUSY_TITLE_ID, STOPPED_TITLE_ID);
    }

    async function calculate(): Promise<void> {
        if (run.running) return;
        const outcome = buildRequest(draft);
        if (!outcome.ok) {
            buildFailure = {fingerprint: draft.fingerprint, problems: outcome.problems.map(listLocalProblem)};
            editStep('review');
            return;
        }
        buildFailure = null;
        await launch(outcome.built);
    }

    async function launch(built: Parameters<PlannerRun['start']>[0]): Promise<void> {
        view = 'result';
        const running = run.start(built, accountGeneration);
        void focusFirst(BUSY_TITLE_ID);
        await running;
        if (!destroyed && view === 'result' && !run.running) void focusFirst(RESULT_TITLE_ID, STOPPED_TITLE_ID);
    }

    function retry(): void {
        const outcome = run.outcome;
        if (outcome && !run.running) void launch(outcome.built);
    }

    function discard(): void {
        run.discard();
        editStep('review');
    }

    // A8: a dirty draft is never dropped without a confirmation. A session change
    // is not asked about: the registry unmounts the renderer and the draft goes.
    beforeNavigate((navigation) => {
        if (allowLeave || !draft.dirty) return;
        try {
            assertToolAccount(accountGeneration);
        } catch {
            return;
        }
        if (navigation.type === 'leave') {
            navigation.cancel();
            return;
        }
        const to = navigation.to?.url;
        if (!to) return;
        navigation.cancel();
        leaveTarget = {url: to, delta: navigation.type === 'popstate' ? (navigation.delta ?? null) : null, external: navigation.willUnload};
    });

    afterNavigate(() => {
        allowLeave = false;
    });

    async function confirmLeave(): Promise<void> {
        const target = leaveTarget;
        leaveTarget = null;
        if (!target) return;
        allowLeave = true;
        if (target.delta !== null) history.go(target.delta);
        else if (target.external) window.location.assign(target.url.href);
        else await goto(target.url);
    }

    onMount(() => {
        if (draft.data.valuationCurrency !== '') return;
        void userSettings.load().then(() => {
            if (destroyed || draft.data.valuationCurrency !== '') return;
            draft.data.valuationCurrency = userSettings.get()?.base_currency ?? 'EUR';
        });
    });

    onDestroy(() => {
        destroyed = true;
        run.dispose();
    });
</script>

<div class="min-w-0 space-y-4" data-testid="pac-planner" data-view={view} data-step={step} data-state={runState} data-busy={run.running ? 'true' : 'false'} aria-busy={run.running}>
    {#if view === 'result'}
        {#if run.busy}
            <BusyPanel built={run.busy} onstop={() => run.stop()} />
        {:else if run.outcome}
            {#if run.stopped}
                <p class={NOTICE.info} role="status" data-testid="pac-planner-stopped-previous">
                    {$t(`${PLANNER_KEY}.stopped.previous`, {default: 'You stopped waiting: the plan below is the previous one.'})}
                </p>
            {/if}
            <ResultView outcome={run.outcome} {draft} {apiVersion} wide={tablet.current} busy={run.running} ongoto={editStep} onedit={() => editStep('review')} oncalculate={() => void calculate()} onretry={retry} ondiscard={discard} />
        {:else}
            <section class={CARD} aria-labelledby={STOPPED_TITLE_ID} data-testid="pac-planner-stopped">
                <h2 id={STOPPED_TITLE_ID} tabindex="-1" class="flex items-center gap-2 {SECTION_TITLE} focus:outline-none">
                    <CircleStop class="h-4 w-4" aria-hidden="true" />
                    {$t(`${PLANNER_KEY}.stopped.title`, {default: 'Calculation stopped'})}
                </h2>
                <p class="mt-3 text-sm">{$t(`${PLANNER_KEY}.stopped.body`, {default: 'You stopped waiting. If the server finishes, its answer is discarded. The configuration is intact.'})}</p>
                <div class="mt-4 flex flex-wrap gap-3">
                    <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-stopped-edit" onclick={() => editStep('review')}>
                        {$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}
                    </button>
                    <button type="button" class={BUTTON_PRIMARY} data-testid="pac-planner-stopped-calculate" onclick={() => void calculate()}>
                        {$t(`${PLANNER_KEY}.review.calculate`, {default: 'Calculate plan'})}
                    </button>
                </div>
            </section>
        {/if}
    {:else}
        <div class={desktop.current ? 'grid grid-cols-[minmax(10rem,12rem)_minmax(0,1fr)_minmax(13rem,15rem)] items-start gap-4' : 'space-y-3'}>
            {#if desktop.current}
                <div class="sticky top-4">
                    <StepNav current={step} {visited} {problemSteps} variant="vertical" onselect={go} />
                </div>
            {:else}
                <div class="space-y-2 {CARD}">
                    <StepNav current={step} {visited} {problemSteps} variant={navVariant} onselect={go} />
                    <button type="button" class="inline-flex items-center gap-1 text-sm font-medium text-gray-700 dark:text-gray-200" aria-expanded={summaryOpen} aria-controls={SUMMARY_ID} data-testid="pac-planner-summary-toggle" onclick={() => (summaryOpen = !summaryOpen)}>
                        {$t(`${PLANNER_KEY}.summary.toggle`, {default: 'Summary'})}
                        {#if summaryOpen}<ChevronUp class="h-4 w-4" aria-hidden="true" />{:else}<ChevronDown class="h-4 w-4" aria-hidden="true" />{/if}
                    </button>
                    {#if summaryOpen}
                        <div id={SUMMARY_ID} class="border-t border-gray-200 pt-3 dark:border-gray-700">
                            <SummaryPanel {draft} {step} {apiVersion} {uiVersion} />
                        </div>
                    {/if}
                </div>
            {/if}

            <section class="min-w-0 {CARD}" aria-labelledby={STEP_TITLE_ID} data-testid="pac-planner-step" data-step={step}>
                <h2 id={STEP_TITLE_ID} tabindex="-1" class="mb-4 {SECTION_TITLE} focus:outline-none">{$t(stepKey(step), {default: STEP_FALLBACKS[step]})}</h2>

                {#if alertItems.length > 0}
                    <div id={STEP_ALERT_ID} tabindex="-1" class="mb-4 {NOTICE.danger} focus:outline-none" role="alert" data-testid="pac-planner-step-alert">
                        <p class="mb-2 font-medium">
                            {$t(`${PLANNER_KEY}.continueBlocked`, {default: '{count, plural, one {# problem to fix before continuing:} other {# problems to fix before continuing:}}', values: {count: alertItems.length}})}
                        </p>
                        <IssueList items={alertItems} testid="pac-planner-step-problem" />
                    </div>
                {/if}

                {#if step === 'scenario'}
                    <ScenarioStep {draft} />
                {:else if step === 'liquidity'}
                    <LiquidityStep {draft} {accountGeneration} />
                {:else if step === 'brokers'}
                    <BrokersStep {draft} {accountGeneration} />
                {:else if step === 'assets'}
                    <AssetsStep {draft} {accountGeneration} />
                {:else if step === 'routing'}
                    <RoutingStep {draft} />
                {:else if step === 'targets'}
                    <TargetsStep {draft} {accountGeneration} />
                {:else if step === 'fx'}
                    <FxStep {draft} {accountGeneration} />
                {:else if step === 'strategy'}
                    <StrategyStep {draft} />
                {:else}
                    <ReviewStep {draft} problems={reviewProblems} busy={run.running} hasResult={run.outcome !== null} ongoto={go} oncalculate={() => void calculate()} onshowresult={showResult} />
                {/if}

                <div class="sticky bottom-0 z-10 -mx-4 mt-6 flex items-center justify-between gap-3 border-t border-gray-200 bg-white/95 px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur dark:border-gray-700 dark:bg-gray-800/95" data-testid="pac-planner-footer">
                    {#if index > 0}
                        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-back" onclick={back}>
                            <ArrowLeft class="h-4 w-4" aria-hidden="true" />
                            <span class={tablet.current ? '' : 'sr-only'}>{$t('common.back', {default: 'Back'})}</span>
                        </button>
                    {:else}
                        <span></span>
                    {/if}
                    {#if step !== 'review'}
                        <button type="button" class={BUTTON_PRIMARY} data-testid="pac-planner-continue" onclick={next}>
                            {$t('common.continue', {default: 'Continue'})}
                            <ArrowRight class="h-4 w-4" aria-hidden="true" />
                        </button>
                    {/if}
                </div>
            </section>

            {#if desktop.current}
                <div class="sticky top-4 {CARD}">
                    <SummaryPanel {draft} {step} {apiVersion} {uiVersion} />
                </div>
            {/if}
        </div>
    {/if}
</div>

<ConfirmModal
    open={leaveTarget !== null}
    title={$t(`${PLANNER_KEY}.leave.title`, {default: 'Leave the PAC allocator?'})}
    message={$t(`${PLANNER_KEY}.leave.message`, {
        default: 'The current configuration is not saved. Leaving, you will lose {assets, plural, one {# Asset} other {# Assets}} and {sources, plural, one {# liquidity source} other {# liquidity sources}}.',
        values: leaveCounts,
    })}
    confirmText={$t(`${PLANNER_KEY}.leave.confirm`, {default: 'Leave and discard'})}
    cancelText={$t('common.continueEditing')}
    warning
    onConfirm={() => void confirmLeave()}
    onCancel={() => (leaveTarget = null)}
    testId="pac-planner-leave-confirm"
/>
