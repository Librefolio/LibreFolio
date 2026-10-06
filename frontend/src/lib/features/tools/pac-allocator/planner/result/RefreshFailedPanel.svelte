<script lang="ts">
    import {CircleAlert} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import type {SourceLoadError} from '../sourceLoad.svelte';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, CARD, NOTICE, SECTION_TITLE} from '../ui';
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

<section class={CARD} aria-labelledby="pac-planner-refresh-failed-title" data-testid="pac-planner-refresh-failed">
    <h2 id="pac-planner-refresh-failed-title" tabindex="-1" class="flex items-center gap-2 {SECTION_TITLE} focus:outline-none">
        <CircleAlert class="h-4 w-4" aria-hidden="true" />
        {$t(`${KEY}.title`, {default: 'The copied data could not be read again'})}
    </h2>
    <p class="mt-3 {NOTICE.danger}" role="alert" data-testid="pac-planner-refresh-failed-reason">{$t(error.key, {default: error.fallback})}</p>
    <p class="mt-3 text-sm">{$t(`${KEY}.body`, {default: 'Nothing was calculated. Try again, or calculate with the values copied earlier.'})}</p>
    <div class="mt-4 flex flex-wrap gap-3">
        <button type="button" class={BUTTON_PRIMARY} data-testid="pac-planner-refresh-retry" onclick={onretry}>{$t(`${KEY}.retry`, {default: 'Try again'})}</button>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-refresh-proceed" onclick={onproceed}>{$t(`${KEY}.proceed`, {default: 'Calculate with the copied data'})}</button>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-refresh-edit" onclick={onedit}>{$t('tools.pacAllocator.planner.actions.editConfiguration', {default: 'Edit configuration'})}</button>
    </div>
</section>
