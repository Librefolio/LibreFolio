<!--
  The warning banner of «Save to the broker profile» (P3 of project 67, N4): before anything is written it lists, for each
  currency of the scenario, whether the broker's profile gets it new or updated, and the conversion mode when it changes.
  «Cancel» closes it and writes nothing; «Confirm» asks the caller to write. It also says the other outcomes: reading,
  nothing to save, a read that failed, a refused or incomplete write, a save done. It writes nothing itself.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import type {ProfileSaveChange, ProfileSavePhase} from '../brokerProfileSave';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY} from '../ui';
    import {getPlannerProfile, testId} from '../profile';

    interface Props {
        phase: ProfileSavePhase;
        brokerName: string;
        changes?: readonly ProfileSaveChange[];
        /** The broker's own words for a refusal, when it gave some. */
        refusal?: string | null;
        onconfirm: () => void;
        oncancel: () => void;
    }

    let {phase, brokerName, changes = [], refusal = null, onconfirm, oncancel}: Props = $props();

    /** Read once, while the component is created: the Tool's profile, the PAC's when none is set. */
    const profile = getPlannerProfile();
    const asking = $derived(phase === 'confirm' || phase === 'writing');
    const tone = $derived(
        phase === 'saved'
            ? 'border-lf-success-line bg-lf-success-soft text-lf-success-on-soft'
            : phase === 'readFailed' || phase === 'refused' || phase === 'writeFailed'
              ? 'border-lf-danger-line bg-lf-danger-soft text-lf-danger-on-soft'
              : 'border-lf-warning-line bg-lf-warning-soft text-lf-warning-on-soft',
    );

    function changeText(change: ProfileSaveChange): string {
        if (change.kind === 'conversion') return change.mode === 'automatic' ? $t('tools.pacAllocator.planner.brokerEditor.profileSave.conversionAutomatic') : $t('tools.pacAllocator.planner.brokerEditor.profileSave.conversionManual');
        return change.change === 'created' ? $t('tools.pacAllocator.planner.brokerEditor.profileSave.created', {values: {currency: change.currency}}) : $t('tools.pacAllocator.planner.brokerEditor.profileSave.updated', {values: {currency: change.currency}});
    }

    function changeKey(change: ProfileSaveChange): string {
        return change.kind === 'conversion' ? 'conversion' : change.currency;
    }
</script>

<div class="space-y-2 rounded-lg border px-3 py-2.5 text-sm {tone}" role={asking ? 'alertdialog' : 'status'} aria-live="polite" data-testid={testId('profile-save', profile)} data-phase={phase}>
    {#if phase === 'reading'}
        <p>{$t('tools.pacAllocator.planner.brokerEditor.profileSave.reading')}</p>
    {:else if phase === 'readFailed'}
        <p>{$t('tools.pacAllocator.planner.brokerEditor.profileSave.readFailed')}</p>
    {:else if phase === 'refused'}
        <p>{$t('tools.pacAllocator.planner.brokerEditor.profileSave.refused')}</p>
        {#if refusal}<p class="text-xs" data-testid={testId('profile-save-refusal', profile)}>{refusal}</p>{/if}
    {:else if phase === 'writeFailed'}
        <p>{$t('tools.pacAllocator.planner.brokerEditor.profileSave.writeFailed')}</p>
    {:else if phase === 'saved'}
        <p>{$t('tools.pacAllocator.planner.brokerEditor.profileSave.saved')}</p>
    {:else}
        <p class="font-semibold">{$t('tools.pacAllocator.planner.brokerEditor.profileSave.title', {values: {name: brokerName || '—'}})}</p>
        {#if changes.length === 0}
            <p data-testid={testId('profile-save-nothing', profile)}>{$t('tools.pacAllocator.planner.brokerEditor.profileSave.nothing')}</p>
        {:else}
            <p>{$t('tools.pacAllocator.planner.brokerEditor.profileSave.intro')}</p>
            <ul class="flex flex-wrap gap-x-3 gap-y-1 font-medium" data-testid={testId('profile-save-changes', profile)}>
                {#each changes as change (changeKey(change))}
                    <li data-testid={testId('profile-save-change', profile)} data-currency={change.kind === 'currency' ? change.currency : undefined} data-change={change.kind === 'currency' ? change.change : 'conversion'}>{changeText(change)}</li>
                {/each}
            </ul>
        {/if}
    {/if}
    {#if phase !== 'reading'}
        <div class="flex flex-wrap justify-end gap-2 pt-1">
            {#if asking}
                <button type="button" class={BUTTON_SECONDARY} disabled={phase === 'writing'} data-testid={testId('profile-save-cancel', profile)} onclick={oncancel}>{$t('common.cancel', {default: 'Cancel'})}</button>
                {#if changes.length > 0}
                    <button type="button" class={BUTTON_PRIMARY} disabled={phase === 'writing'} data-testid={testId('profile-save-confirm', profile)} onclick={onconfirm}>{$t('tools.pacAllocator.planner.brokerEditor.profileSave.confirm')}</button>
                {/if}
            {:else}
                <button type="button" class={BUTTON_SECONDARY} data-testid={testId('profile-save-close', profile)} onclick={oncancel}>{$t('common.close', {default: 'Close'})}</button>
            {/if}
        </div>
    {/if}
</div>
