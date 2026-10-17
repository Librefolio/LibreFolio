<script lang="ts">
    import {_} from '$lib/i18n';

    interface Props {
        error?: string | null;
        onretry: () => void;
        onlogout: () => void;
    }

    let {error = null, onretry, onlogout}: Props = $props();
</script>

<div class="flex min-h-screen items-center justify-center bg-lf-page p-4 text-lf-primary" data-testid="onboarding-bootstrap-blocked">
    <section class="w-full max-w-lg rounded-2xl border border-lf-danger-line bg-lf-card p-6 shadow-xl shadow-lf-shadow" role="alert">
        <h1 class="text-xl font-semibold text-lf-primary">
            {$_('onboarding.errors.loadTitle')}
        </h1>
        <p class="mt-2 text-sm text-lf-secondary">
            {error ?? $_('onboarding.errors.loadDescription')}
        </p>
        <div class="mt-5 flex justify-end gap-2">
            <button type="button" class="rounded-lg px-4 py-2 text-sm text-lf-secondary hover:bg-lf-hover" onclick={onlogout} data-testid="onboarding-bootstrap-logout">
                {$_('onboarding.welcome.logout')}
            </button>
            <button type="button" class="rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover" onclick={onretry} data-testid="onboarding-bootstrap-retry">
                {$_('common.retry')}
            </button>
        </div>
    </section>
</div>
