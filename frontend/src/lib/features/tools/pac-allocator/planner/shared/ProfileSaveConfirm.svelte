<!--
  «Save to the broker profile» (P3 of project 67, N4), before and after the write. Before anything is written, the project's
  confirmation modal (R1-C of project 67: the developer asked for «la classica modale nostra di conferma» in place of a
  yellow banner) lists, for each currency of the scenario, whether the broker's profile gets it new or updated, and the
  conversion mode when it changes. «Cancel» closes it and writes nothing; «Confirm» asks the caller to write. The other
  phases are a line in the window: reading, nothing to save, writing, a read that failed, a refused or incomplete write, a
  save done. The line carries `data-phase` in every phase, hidden while the modal asks. It writes nothing itself.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import type {ProfileSaveChange, ProfileSavePhase} from '../brokerProfileSave';
    import {BUTTON_SECONDARY} from '../ui';
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
    const P = 'tools.pacAllocator.planner.brokerEditor.profileSave';
    /** The modal asks only when there is something to write; «nothing to save» is a line. */
    const asking = $derived(phase === 'confirm' && changes.length > 0);
    const tone = $derived(
        phase === 'saved' ? 'border-lf-success-line bg-lf-success-soft text-lf-success-on-soft' : phase === 'readFailed' || phase === 'refused' || phase === 'writeFailed' ? 'border-lf-danger-line bg-lf-danger-soft text-lf-danger-on-soft' : 'border-lf-subtle bg-lf-panel text-lf-secondary',
    );

    function changeText(change: ProfileSaveChange): string {
        if (change.kind === 'conversion') return change.mode === 'automatic' ? $t(`${P}.conversionAutomatic`) : $t(`${P}.conversionManual`);
        return change.change === 'created' ? $t(`${P}.created`, {values: {currency: change.currency}}) : $t(`${P}.updated`, {values: {currency: change.currency}});
    }

    function changeKey(change: ProfileSaveChange): string {
        return change.kind === 'conversion' ? 'conversion' : change.currency;
    }
</script>

<ConfirmModal open={asking} title={$t(`${P}.title`, {values: {name: brokerName || '—'}})} message={$t(`${P}.intro`)} confirmText={$t(`${P}.confirm`)} warning testId={testId('profile-save-modal', profile)} onConfirm={onconfirm} onCancel={oncancel}>
    {#snippet details()}
        <ul class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-sm font-medium text-lf-primary" data-testid={testId('profile-save-changes', profile)}>
            {#each changes as change (changeKey(change))}
                <li data-testid={testId('profile-save-change', profile)} data-currency={change.kind === 'currency' ? change.currency : undefined} data-change={change.kind === 'currency' ? change.change : 'conversion'}>{changeText(change)}</li>
            {/each}
        </ul>
    {/snippet}
</ConfirmModal>

<div class="space-y-2 rounded-lg border px-3 py-2.5 text-sm {tone}" role="status" aria-live="polite" hidden={asking} data-testid={testId('profile-save', profile)} data-phase={phase}>
    {#if phase === 'reading'}
        <p>{$t(`${P}.reading`)}</p>
    {:else if phase === 'writing'}
        <p>{$t(`${P}.writing`, {default: 'Saving to the broker…'})}</p>
    {:else if phase === 'readFailed'}
        <p>{$t(`${P}.readFailed`)}</p>
    {:else if phase === 'refused'}
        <p>{$t(`${P}.refused`)}</p>
        {#if refusal}<p class="text-xs" data-testid={testId('profile-save-refusal', profile)}>{refusal}</p>{/if}
    {:else if phase === 'writeFailed'}
        <p>{$t(`${P}.writeFailed`)}</p>
    {:else if phase === 'saved'}
        <p>{$t(`${P}.saved`)}</p>
    {:else if changes.length === 0}
        <p data-testid={testId('profile-save-nothing', profile)}>{$t(`${P}.nothing`)}</p>
    {/if}
    {#if phase !== 'reading' && phase !== 'writing' && !asking}
        <div class="flex flex-wrap justify-end gap-2 pt-1">
            <button type="button" class={BUTTON_SECONDARY} data-testid={testId('profile-save-close', profile)} onclick={oncancel}>{$t('common.close', {default: 'Close'})}</button>
        </div>
    {/if}
</div>
