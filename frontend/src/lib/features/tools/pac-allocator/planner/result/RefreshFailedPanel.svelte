<script lang="ts">
    import {CircleAlert} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import type {SourceLoadError} from '../sourceLoad.svelte';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, CARD, NOTICE, SECTION_TITLE} from '../ui';
    import {getPlannerProfile, domId, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();
    const KEY = 'tools.pacAllocator.planner.refresh.failed';

    interface Props {
        error: SourceLoadError;
        onretry: () => void;
        /** Calculates with the values copied earlier, without reading them again. */
        onproceed: () => void;
        onedit: () => void;
    }

    let {error, onretry, onproceed, onedit}: Props = $props();
</script>

<section class={CARD} aria-labelledby={domId('refresh-failed-title', profile)} data-testid={testId('refresh-failed', profile)}>
    <h2 id={domId('refresh-failed-title', profile)} tabindex="-1" class="flex items-center gap-2 {SECTION_TITLE} focus:outline-none">
        <CircleAlert class="h-4 w-4" aria-hidden="true" />
        {$t(`${KEY}.title`, {default: 'The copied data could not be read again'})}
    </h2>
    <p class="mt-3 {NOTICE.danger}" role="alert" data-testid={testId('refresh-failed-reason', profile)}>{$t(error.key, {default: error.fallback})}</p>
    <p class="mt-3 text-sm">{$t(`${KEY}.body`, {default: 'Nothing was calculated. Try again, or calculate with the values copied earlier.'})}</p>
    <div class="mt-4 flex flex-wrap gap-3">
        <button type="button" class={BUTTON_PRIMARY} data-testid={testId('refresh-retry', profile)} onclick={onretry}>{$t(`${KEY}.retry`, {default: 'Try again'})}</button>
        <button type="button" class={BUTTON_SECONDARY} data-testid={testId('refresh-proceed', profile)} onclick={onproceed}>{$t(`${KEY}.proceed`, {default: 'Calculate with the copied data'})}</button>
        <button type="button" class={BUTTON_SECONDARY} data-testid={testId('refresh-edit', profile)} onclick={onedit}>{$t('tools.pacAllocator.planner.actions.editConfiguration', {default: 'Edit configuration'})}</button>
    </div>
</section>
