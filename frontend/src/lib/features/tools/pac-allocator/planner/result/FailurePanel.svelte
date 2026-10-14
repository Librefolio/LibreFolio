<script lang="ts">
    import {CircleHelp, CircleMinus, CircleX} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import IssueList from '../shared/IssueList.svelte';
    import type {PlannerDraft} from '../draft.svelte';
    import {presentIssues} from '../issues';
    import {listIssue} from '../labels';
    import type {RequestIdMap} from '../request';
    import type {PacFailureResult, PlannerStep} from '../types';
    import {BUTTON_LINK, BUTTON_SECONDARY, CARD, HINT} from '../ui';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        result: PacFailureResult;
        draft: PlannerDraft;
        ids: RequestIdMap;
        ongoto: (step: PlannerStep) => void;
        onedit: () => void;
    }

    let {result, draft, ids, ongoto, onedit}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.failure';
    const HEADINGS = {needs_input: 'More data needed', invalid: 'Input not valid', unsupported: 'Scenario not supported'} as const;
    const NOTES = {
        needs_input: 'Draft intact. No Asset was removed silently: add the missing fact or remove the Asset yourself.',
        invalid: 'Messages translated by the interface; amounts masked when privacy is on. The backend code is under Details.',
        unsupported: 'Not an error in your data: this version of the Tool does not handle the case. No calculation was run.',
    } as const;

    let showCodes = $state(false);
    const items = $derived(presentIssues(result.issues, draft, ids).map(listIssue));
</script>

<section class="{CARD} space-y-3" aria-labelledby="pac-planner-failure-title" data-testid="pac-planner-failure" data-state={result.result_state}>
    <h3 id="pac-planner-failure-title" class="flex flex-wrap items-center gap-2 text-base font-semibold text-gray-900 dark:text-gray-100">
        {#if result.result_state === 'needs_input'}
            <CircleHelp size={18} class="text-amber-600 dark:text-amber-400" aria-hidden="true" />
        {:else if result.result_state === 'invalid'}
            <CircleX size={18} class="text-red-600 dark:text-red-400" aria-hidden="true" />
        {:else}
            <CircleMinus size={18} class="text-gray-500 dark:text-gray-400" aria-hidden="true" />
        {/if}
        <span>{$t(`${KEY}.titles.${result.result_state}`, {default: HEADINGS[result.result_state]})}</span>
        <span class="text-sm font-normal text-gray-500 dark:text-gray-400">· {$t(`${KEY}.nothingCalculated`, {default: 'the backend calculated nothing'})}</span>
    </h3>
    <IssueList {items} {ongoto} {showCodes} testid="pac-planner-failure-issues" />
    <p class={HINT}>{$t(`${KEY}.notes.${result.result_state}`, {default: NOTES[result.result_state]})}</p>
    <div class="flex flex-wrap items-center gap-3">
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-failure-edit" onclick={onedit}>{$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}</button>
        <button type="button" class={BUTTON_LINK} aria-pressed={showCodes} data-testid="pac-planner-failure-details" onclick={() => (showCodes = !showCodes)}>
            {showCodes ? $t(`${KEY}.hideDetails`, {default: 'Hide details'}) : $t(`${KEY}.showDetails`, {default: 'Details'})}
        </button>
    </div>
</section>
