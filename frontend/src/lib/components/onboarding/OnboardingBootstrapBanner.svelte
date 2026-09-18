<script lang="ts">
    import {_} from '$lib/i18n';

    interface Props {
        error?: string | null;
        onretry: () => void;
    }

    let {error = null, onretry}: Props = $props();
</script>

<aside class="mb-4 flex flex-col gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100 sm:flex-row sm:items-center sm:justify-between" data-testid="onboarding-bootstrap-degraded" role="status">
    <span>{error ?? $_('onboarding.errors.degraded')}</span>
    <button type="button" class="shrink-0 rounded-lg border border-amber-400 px-3 py-1.5 font-medium hover:bg-amber-100 dark:border-amber-700 dark:hover:bg-amber-900/40" onclick={onretry} data-testid="onboarding-bootstrap-banner-retry">
        {$_('common.retry')}
    </button>
</aside>
