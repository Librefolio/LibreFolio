<script lang="ts">
    /**
     * What an administrator sees instead of the app while the active accounts outnumber the plan of the instance (A5-7):
     * who keeps the access. The others are deactivated, never deleted; the full backup is offered first, on the same page.
     *
     * The server decides every rule (who must stay, how many, that an administrator remains): the page only helps to
     * respect them, and shows the server's refusal when a rule is still broken. `fetchChoice` and `resolve` are injectable
     * for tests; by default they are `GET /users/over-limit` and `POST /users/over-limit/resolve`.
     */
    import {onMount} from 'svelte';
    import {Users} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import BackupDownloadCard from '$lib/features/backup/BackupDownloadCard.svelte';
    import ToastContainer from '$lib/components/ui/feedback/ToastContainer.svelte';
    import {userLimit} from '../userLimit.svelte';

    type Row = {id: number; username: string; email: string; is_superuser: boolean; protected?: 'owner' | 'you' | ('owner' | 'you' | null)[] | null; owned_brokers_alone: number};
    type Choice = {over_limit: boolean; active: number; max_users?: number | (number | null)[] | null; live_invites: number; waiting_accounts: number; max_keep: number; users: Row[]};

    interface Props {
        onlogout: () => void;
        fetchChoice?: () => Promise<Choice>;
        resolve?: (keepUserIds: number[]) => Promise<unknown>;
        /** The choice is made (here or by another administrator): by default the flag is cleared and the page reloads. */
        onresolved?: () => void;
    }

    let {
        onlogout,
        fetchChoice = () => zodiosApi.list_over_limit_api_v1_users_over_limit_get(),
        resolve = (keepUserIds: number[]) => zodiosApi.resolve_over_limit_api_v1_users_over_limit_resolve_post({keep_user_ids: keepUserIds}),
        onresolved = () => {
            userLimit.clear();
            window.location.reload();
        },
    }: Props = $props();

    /** The line of each refusal the server codes; any other failure has the generic one. */
    const ERROR_KEYS: Record<string, string> = {
        UNKNOWN_USER: 'instance.userLimit.error.UNKNOWN_USER',
        TOO_MANY_KEPT: 'instance.userLimit.error.TOO_MANY_KEPT',
        PROTECTED_MISSING: 'instance.userLimit.error.PROTECTED_MISSING',
        NO_ADMIN_KEPT: 'instance.userLimit.error.NO_ADMIN_KEPT',
    };

    let choice = $state<Choice | null>(null);
    let kept = $state<number[]>([]);
    let busy = $state(false);
    let errorKey = $state<string | null>(null);

    const chosen = $derived(kept.length);
    const maxKeep = $derived(choice?.max_keep ?? 0);
    // The generated client types a nullable number with a default as a number or an array: only a number is a plan size
    const planSize = $derived(typeof choice?.max_users === 'number' ? choice.max_users : maxKeep);
    const overPlan = $derived(chosen > maxKeep);
    const hasAdmin = $derived(choice?.users.some((user) => user.is_superuser && kept.includes(user.id)) ?? false);
    // The invitations that would not fit once these accounts stay: the server revokes them, newest first
    const invitesToCancel = $derived(choice ? Math.min(choice.live_invites, Math.max(0, chosen + choice.live_invites - planSize)) : 0);
    const canConfirm = $derived(choice !== null && !busy && chosen > 0 && !overPlan && hasAdmin);

    function errorCode(error: unknown): {status: number | undefined; code: string | undefined} {
        const response = (error as {response?: {status?: number; data?: {detail?: {error_code?: string}}}} | null)?.response;
        return {status: response?.status, code: response?.data?.detail?.error_code};
    }

    async function load(): Promise<void> {
        errorKey = null;
        try {
            const answer = await fetchChoice();
            if (!answer.over_limit) {
                // Chosen meanwhile (or the plan grew): nothing to choose
                onresolved();
                return;
            }
            choice = answer;
            kept = answer.users.filter((user) => user.protected).map((user) => user.id);
        } catch {
            errorKey = 'instance.userLimit.error.load';
        }
    }

    function toggle(id: number): void {
        kept = kept.includes(id) ? kept.filter((other) => other !== id) : [...kept, id];
    }

    async function confirm(): Promise<void> {
        if (!canConfirm) return;
        busy = true;
        errorKey = null;
        try {
            await resolve([...kept]);
            onresolved();
        } catch (error) {
            const {status, code} = errorCode(error);
            if (status === 409 && code === 'NOT_OVER_LIMIT') {
                onresolved();
                return;
            }
            errorKey = (code && ERROR_KEYS[code]) || 'instance.userLimit.error.generic';
        } finally {
            busy = false;
        }
    }

    onMount(() => {
        void load();
    });
</script>

<div class="flex min-h-screen items-center justify-center bg-lf-page p-4" data-testid="user-limit-choice">
    <div class="w-full max-w-2xl space-y-4">
        <section class="rounded-2xl border border-lf-subtle bg-lf-card p-6 shadow-xl" role="alert">
            <div class="flex items-start gap-3">
                <Users class="mt-0.5 h-6 w-6 shrink-0 text-lf-warning" aria-hidden="true" />
                <div class="min-w-0 flex-1">
                    <h1 class="text-xl font-semibold text-lf-primary" data-testid="user-limit-title">{$_('instance.userLimit.title')}</h1>
                    {#if choice}
                        <p class="mt-2 text-sm text-lf-secondary" data-testid="user-limit-description">
                            {$_('instance.userLimit.description', {values: {active: choice.active, max: planSize}})}
                        </p>
                    {/if}
                </div>
            </div>

            {#if choice}
                <ul class="mt-4 divide-y divide-lf-subtle rounded-lg border border-lf-subtle" data-testid="user-limit-list">
                    {#each choice.users as user (user.id)}
                        <li class="flex items-center gap-3 px-3 py-2" data-testid={`user-limit-row-${user.id}`}>
                            <input type="checkbox" class="h-4 w-4 shrink-0" checked={kept.includes(user.id)} disabled={Boolean(user.protected)} onchange={() => toggle(user.id)} aria-label={user.username} data-testid={`user-limit-keep-${user.id}`} />
                            <div class="min-w-0 flex-1">
                                <p class="truncate text-sm font-medium text-lf-primary">{user.username}</p>
                                <p class="truncate text-xs text-lf-muted">{user.email}</p>
                                {#if user.owned_brokers_alone > 0}
                                    <p class="text-xs text-lf-warning-on-soft" data-testid={`user-limit-alone-${user.id}`}>
                                        {$_('instance.userLimit.brokersAlone', {values: {count: user.owned_brokers_alone}})}
                                    </p>
                                {/if}
                            </div>
                            <div class="flex shrink-0 flex-col items-end gap-1 text-xs">
                                {#if user.is_superuser}
                                    <span class="text-lf-secondary">{$_('instance.userLimit.administrator')}</span>
                                {/if}
                                {#if user.protected}
                                    <span class="text-lf-success">{user.protected === 'owner' ? $_('instance.userLimit.protectedOwner') : $_('instance.userLimit.protectedYou')}</span>
                                {/if}
                            </div>
                        </li>
                    {/each}
                </ul>

                <p class="mt-3 text-sm {overPlan ? 'text-lf-danger' : 'text-lf-secondary'}" data-testid="user-limit-counter" data-state={overPlan ? 'over' : 'ok'}>
                    {$_('instance.userLimit.counter', {values: {chosen, max: maxKeep}})}
                </p>
                {#if !hasAdmin && chosen > 0}
                    <p class="mt-1 text-xs text-lf-warning-on-soft" data-testid="user-limit-no-admin">{$_('instance.userLimit.noAdministrator')}</p>
                {/if}
                {#if invitesToCancel > 0}
                    <p class="mt-1 rounded-lg border border-lf-warning-line bg-lf-warning-soft px-3 py-2 text-sm text-lf-warning-on-soft" data-testid="user-limit-invites">
                        {$_('instance.userLimit.invitesCancelled', {values: {count: invitesToCancel}})}
                    </p>
                {/if}
            {/if}

            {#if errorKey}
                <p class="mt-3 rounded-lg border border-lf-danger-line bg-lf-danger-soft px-3 py-2 text-sm text-lf-danger-on-soft" data-testid="user-limit-error">{$_(errorKey)}</p>
            {/if}

            <div class="mt-5 flex flex-wrap items-center justify-end gap-2">
                {#if !choice && errorKey}
                    <button type="button" class="rounded-lg px-4 py-2 text-sm font-medium text-lf-link hover:bg-lf-hover hover:underline" onclick={() => void load()} data-testid="user-limit-retry">
                        {$_('common.retry')}
                    </button>
                {/if}
                <button type="button" class="rounded-lg px-4 py-2 text-sm text-lf-secondary hover:bg-lf-hover" onclick={onlogout} data-testid="user-limit-logout">
                    {$_('auth.logout')}
                </button>
                {#if choice}
                    <button type="button" class="rounded-lg bg-lf-action px-4 py-2 text-sm font-bold text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50" disabled={!canConfirm} onclick={() => void confirm()} data-testid="user-limit-confirm">
                        {$_('instance.userLimit.confirm')}
                    </button>
                {/if}
            </div>
        </section>
        <!-- Outside the alert: a screen reader announces the choice, not the backup card and its progress -->
        <section class="rounded-2xl border border-lf-subtle bg-lf-card p-4 shadow-xl sm:p-6" aria-labelledby="user-limit-backup-title" data-testid="user-limit-backup">
            <h2 id="user-limit-backup-title" class="mb-3 text-base font-semibold text-lf-primary">{$_('instance.userLimit.backupTitle')}</h2>
            <BackupDownloadCard />
        </section>
    </div>
    <!-- The (app) layout mounts its toasts around the app only, and this page replaces the app -->
    <ToastContainer />
</div>
