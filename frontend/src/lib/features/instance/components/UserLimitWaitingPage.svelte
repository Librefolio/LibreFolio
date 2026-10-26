<script lang="ts">
    /**
     * What anyone but an administrator sees while the active accounts outnumber the plan of the instance (A5-7): an
     * administrator has to choose who keeps the access. A clear message and two buttons: check again (the app starts again
     * if the choice was made) and sign out. It reads nothing from the API: the server told this user only the refusal.
     */
    import {Users} from 'lucide-svelte';
    import {_} from '$lib/i18n';

    interface Props {
        onlogout: () => void;
        /** Check again; by default the page reloads and the app starts again if the choice was made. */
        oncheck?: () => void;
    }

    let {
        onlogout,
        oncheck = () => {
            window.location.reload();
        },
    }: Props = $props();
</script>

<div class="flex min-h-screen items-center justify-center bg-lf-page p-4" data-testid="user-limit-waiting">
    <section class="w-full max-w-lg rounded-2xl border border-lf-subtle bg-lf-card p-6 shadow-xl" role="alert">
        <div class="flex items-start gap-3">
            <Users class="mt-0.5 h-6 w-6 shrink-0 text-lf-warning" aria-hidden="true" />
            <div>
                <h1 class="text-xl font-semibold text-lf-primary" data-testid="user-limit-waiting-title">{$_('instance.userLimit.waitingTitle')}</h1>
                <p class="mt-2 text-sm text-lf-secondary" data-testid="user-limit-waiting-description">{$_('instance.userLimit.waitingDescription')}</p>
            </div>
        </div>
        <div class="mt-5 flex flex-wrap items-center justify-end gap-2">
            <button type="button" class="rounded-lg px-4 py-2 text-sm font-medium text-lf-link hover:bg-lf-hover hover:underline" onclick={oncheck} data-testid="user-limit-check-again">
                {$_('instance.userLimit.checkAgain')}
            </button>
            <button type="button" class="rounded-lg px-4 py-2 text-sm text-lf-secondary hover:bg-lf-hover" onclick={onlogout} data-testid="user-limit-logout">
                {$_('auth.logout')}
            </button>
        </div>
    </section>
</div>
