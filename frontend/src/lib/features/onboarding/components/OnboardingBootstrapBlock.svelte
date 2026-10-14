<script lang="ts">
    import {_} from '$lib/i18n';

    interface Props {
        error?: string | null;
        onretry: () => void;
        onlogout: () => void;
    }

    let {error = null, onretry, onlogout}: Props = $props();
</script>

<div class="flex min-h-screen items-center justify-center bg-libre-beige p-4 dark:bg-slate-950" data-testid="onboarding-bootstrap-blocked">
    <section class="w-full max-w-lg rounded-2xl border border-red-200 bg-white p-6 shadow-xl dark:border-red-900 dark:bg-slate-900" role="alert">
        <h1 class="text-xl font-semibold text-gray-900 dark:text-white">
            {$_('onboarding.errors.loadTitle')}
        </h1>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-300">
            {error ?? $_('onboarding.errors.loadDescription')}
        </p>
        <div class="mt-5 flex justify-end gap-2">
            <button type="button" class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-800" onclick={onlogout} data-testid="onboarding-bootstrap-logout">
                {$_('onboarding.welcome.logout')}
            </button>
            <button type="button" class="rounded-lg bg-libre-green px-4 py-2 text-sm font-medium text-white" onclick={onretry} data-testid="onboarding-bootstrap-retry">
                {$_('common.retry')}
            </button>
        </div>
    </section>
</div>
