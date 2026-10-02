<script lang="ts">
    import {Clock} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import type {CopyKind} from '../draft.svelte';
    import type {PlannerDraft} from '../draft.svelte';
    import type {CopyOutcome} from '../copies';
    import {formatCopyStamp} from '../format';
    import {presentSourceIssues, sourceEntityLabel} from '../issues';
    import {listIssue} from '../labels';
    import type {PlannerSource} from '../source';
    import {BADGE, BUTTON_LINK, NOTICE} from '../ui';
    import IssueList from './IssueList.svelte';

    interface Props {
        outcome: CopyOutcome;
        draft: PlannerDraft;
        source: PlannerSource | null;
        testid: string;
        /** The step shows the copied rows at once: a copy that went well says nothing, and the fees note is left to the Broker card. */
        quiet?: boolean;
        ondismiss: () => void;
    }

    let {outcome, draft, source, testid, quiet = false, ondismiss}: Props = $props();

    const MISSING_FALLBACKS: Partial<Record<CopyKind, string>> = {
        prices: 'No price published for: {names}. They stay in the draft; the calculation will ask for them.',
        classifications: 'No complete classification for: {names}.',
        fx: 'No rate published for: {names}.',
        liquidity: 'Nothing copied for: {names}.',
        brokers: 'Nothing copied for: {names}.',
    };

    /** Structural, one per Broker: LibreFolio stores no fees or order modes, the Broker step collects them. Said once, as information. */
    const PROFILE_CODE = 'allocation.broker_execution_profile_unsupported';

    const profileBrokers = $derived(
        quiet
            ? []
            : [
                  ...new Set(
                      outcome.issues
                          .filter((issue) => issue.code === PROFILE_CODE)
                          .map((issue) => sourceEntityLabel(draft, source, 'entity_id' in issue.path ? {kind: issue.path.entity_kind, id: issue.path.entity_id} : null))
                          .filter((name): name is string => name !== null),
                  ),
              ],
    );
    const issues = $derived(
        presentSourceIssues(
            outcome.issues.filter((issue) => issue.code !== PROFILE_CODE),
            draft,
            source,
        ).map(listIssue),
    );
    const warn = $derived(outcome.missing.length > 0 || outcome.conflicts.length > 0 || issues.some((item) => item.severity !== 'info'));
    const shown = $derived(!quiet || warn || issues.length > 0);
    /** Prices, FX rates and cash balances left unchanged are read again before «Calcola»: their copy time says nothing. */
    const showStamp = $derived(outcome.kind !== 'prices' && outcome.kind !== 'fx' && outcome.kind !== 'liquidity');
    const stamp = $derived(formatCopyStamp(outcome.copy.asOf, outcome.copy.capturedAt, $locale));
    const stampHint = $derived(
        $t('tools.pacAllocator.planner.copyNotice.stamp', {
            default: '{kind, select, refreshed {Copied: {when}. Values you have not changed are read again just before the calculation.} other {Copied: {when}.}}',
            values: {when: stamp, kind: 'other'},
        }),
    );
</script>

{#if shown}
    <div class={warn ? NOTICE.warning : NOTICE.success} role="status" data-testid={testid} data-kind={outcome.kind} data-applied={outcome.applied} data-unchanged={outcome.unchanged} data-missing={outcome.missing.length} data-conflicts={outcome.conflicts.length}>
        <div class="flex flex-wrap items-start justify-between gap-2">
            <div class="min-w-0 space-y-1">
                <p class="flex flex-wrap items-center gap-x-2 gap-y-1 font-medium">
                    <span>
                        {$t('tools.pacAllocator.planner.copyNotice.summary', {
                            default: 'Copy done: {applied, plural, =0 {nothing added or updated} one {# item added or updated} other {# items added or updated}}{unchanged, plural, =0 {} one {, # unchanged} other {, # unchanged}}.',
                            values: {applied: outcome.applied, unchanged: outcome.unchanged},
                        })}
                    </span>
                    {#if showStamp}
                        <span class={BADGE.neutral} title={stampHint} data-testid="{testid}-stamp">
                            <Clock size={12} aria-hidden="true" />{stamp}
                        </span>
                    {/if}
                </p>
                {#if profileBrokers.length > 0}
                    <p class="text-xs" data-testid="{testid}-profile">
                        {$t('tools.pacAllocator.planner.copyNotice.executionProfile', {
                            default: 'Fees and order modes of {names} are not recorded in LibreFolio: {kind, select, brokers {you set them below.} other {you set them in the Broker step.}}',
                            values: {names: profileBrokers.join(', '), kind: outcome.kind === 'brokers' ? 'brokers' : 'other'},
                        })}
                    </p>
                {/if}
                {#if outcome.missing.length > 0}
                    <p data-testid="{testid}-missing">
                        {$t(`tools.pacAllocator.planner.copyNotice.missing.${outcome.kind}`, {default: MISSING_FALLBACKS[outcome.kind] ?? '{names}', values: {names: outcome.missing.join(', ')}})}
                    </p>
                {/if}
                {#if outcome.conflicts.length > 0}
                    <p data-testid="{testid}-conflicts">
                        {$t('tools.pacAllocator.planner.copyNotice.conflicts', {
                            default: '{count, plural, one {# fact changed since the previous copy: you decide in the dialog.} other {# facts changed since the previous copy: you decide in the dialog.}}',
                            values: {count: outcome.conflicts.length},
                        })}
                    </p>
                {/if}
            </div>
            <button type="button" class={BUTTON_LINK} data-testid="{testid}-dismiss" onclick={ondismiss}>{$t('common.close', {default: 'Close'})}</button>
        </div>
        {#if issues.length > 0}
            <div class="mt-2">
                <IssueList items={issues} testid="{testid}-issues" />
            </div>
        {/if}
    </div>
{/if}
