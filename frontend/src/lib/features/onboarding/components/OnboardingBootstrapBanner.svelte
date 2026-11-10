<script lang="ts">
    import {_} from '$lib/i18n';
    import {STATUS_TONES} from '$lib/theme/toneClasses';

    interface Props {
        error?: string | null;
        onretry: () => void;
    }

    let {error = null, onretry}: Props = $props();

    /** Retry is a button inside a warning banner: the banner chip of round 3 (proposal a). */
    const RETRY = STATUS_TONES.bannerChip.warning;
</script>

<aside class="mb-4 flex flex-col gap-3 rounded-xl border border-lf-warning-line bg-lf-warning-soft px-4 py-3 text-sm text-lf-warning-on-soft sm:flex-row sm:items-center sm:justify-between" data-testid="onboarding-bootstrap-degraded" role="status">
    <span>{error ?? $_('onboarding.errors.degraded')}</span>
    <button type="button" class="shrink-0 rounded-lg border px-3 py-1.5 font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-lf-focus {RETRY.base} {RETRY.hover}" onclick={onretry} data-testid="onboarding-bootstrap-banner-retry">
        {$_('common.retry')}
    </button>
</aside>
