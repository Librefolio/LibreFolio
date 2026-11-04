<script lang="ts">
    /**
     * «Updates paused»: the live prices of this page stopped refreshing because nobody used it for two minutes
     * (F26, decision 31). A signal, not a command: moving the mouse or pressing a key resumes them, and the pill goes
     * away by itself. Nothing is drawn while the prices refresh, nor while the tab is hidden, where nobody sees it.
     */
    import {Pause} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {STATUS_TONES} from '$lib/theme/toneClasses';
    import type {ActivePollingState} from './activePolling';

    interface Props {
        state: ActivePollingState;
    }

    let {state}: Props = $props();
</script>

{#if state === 'paused-idle'}
    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium {STATUS_TONES.liveUpdates.paused}" data-testid="live-updates-status" data-state={state} role="status" title={$t('liveUpdates.pausedHint')}>
        <Pause size={12} aria-hidden="true" />
        {$t('liveUpdates.paused')}
    </span>
{/if}
