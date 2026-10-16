<script lang="ts">
    import {_} from '$lib/i18n';

    interface Props {
        error?: string | null;
        onretry: () => void;
    }

    let {error = null, onretry}: Props = $props();
</script>

<aside class="mb-4 flex flex-col gap-3 rounded-xl border border-lf-warning-line bg-lf-warning-soft px-4 py-3 text-sm text-lf-warning-on-soft sm:flex-row sm:items-center sm:justify-between" data-testid="onboarding-bootstrap-degraded" role="status">
    <span>{error ?? $_('onboarding.errors.degraded')}</span>
    <button type="button" class="shrink-0 rounded-lg border border-lf-warning-line px-3 py-1.5 font-medium hover:bg-lf-warning-line/50" onclick={onretry} data-testid="onboarding-bootstrap-banner-retry">
        {$_('common.retry')}
    </button>
</aside>
