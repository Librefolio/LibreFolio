<!--
UsersTab — administrators only: the accounts of the instance and the invitations still open (decision D-A10).

At the top, the places taken against the limit («N / max», «Manage subscription» when the hoster set a billing page,
decision D-A9) and the invitation button, off while registration is closed or the instance is full. Each account opens
its actions (UserRow); the confirmations, the invitation, the reset link and the deletion each have their dialog.
Every action reloads the tab: the backend decides, the tab shows its answer.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {CreditCard, ExternalLink, UserPlus, Users} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {currentUser} from '$lib/stores/app/auth';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import AccountDeletionDialog from '../AccountDeletionDialog.svelte';
    import UserRow from '../users/UserRow.svelte';
    import InvitationsList from '../users/InvitationsList.svelte';
    import InviteDialog from '../users/InviteDialog.svelte';
    import ResetLinkDialog from '../users/ResetLinkDialog.svelte';
    import {accountErrorText, describeAccountError} from '../users/accountErrors';
    import type {AccountsUsage, AdminAccount, OpenInvite, UserAction} from '../users/types';

    type Confirmable = 'deactivate' | 'cancel-setup' | 'promote' | 'demote' | 'sign-out' | 'restart-guides';
    type Pending = {kind: Confirmable; account: AdminAccount} | {kind: 'revoke-invite'; invite: OpenInvite};

    const CONFIRM_KEYS: Record<Pending['kind'], {title: string; message: string; confirm: string; danger: boolean}> = {
        deactivate: {
            title: 'settings.usersTab.confirm.deactivate.title',
            message: 'settings.usersTab.confirm.deactivate.message',
            confirm: 'settings.usersTab.confirm.deactivate.confirm',
            danger: true,
        },
        // The waiting initial administrator's setup link stops working; the account still waits (A-43)
        'cancel-setup': {
            title: 'settings.usersTab.confirm.cancelSetup.title',
            message: 'settings.usersTab.confirm.cancelSetup.message',
            confirm: 'settings.usersTab.confirm.cancelSetup.confirm',
            danger: true,
        },
        promote: {
            title: 'settings.usersTab.confirm.promote.title',
            message: 'settings.usersTab.confirm.promote.message',
            confirm: 'settings.usersTab.confirm.promote.confirm',
            danger: false,
        },
        demote: {
            title: 'settings.usersTab.confirm.demote.title',
            message: 'settings.usersTab.confirm.demote.message',
            confirm: 'settings.usersTab.confirm.demote.confirm',
            danger: true,
        },
        'sign-out': {
            title: 'settings.usersTab.confirm.signOut.title',
            message: 'settings.usersTab.confirm.signOut.message',
            confirm: 'settings.usersTab.confirm.signOut.confirm',
            danger: false,
        },
        'restart-guides': {
            title: 'settings.usersTab.confirm.restartGuides.title',
            message: 'settings.usersTab.confirm.restartGuides.message',
            confirm: 'settings.usersTab.confirm.restartGuides.confirm',
            danger: false,
        },
        'revoke-invite': {
            title: 'settings.usersTab.confirm.revokeInvite.title',
            message: 'settings.usersTab.confirm.revokeInvite.message',
            confirm: 'settings.usersTab.confirm.revokeInvite.confirm',
            danger: true,
        },
    };

    let accounts = $state<AdminAccount[]>([]);
    let usage = $state<AccountsUsage | null>(null);
    let invites = $state<OpenInvite[]>([]);
    let busy = $state(true);
    let loadFailed = $state(false);
    let pending = $state<Pending | null>(null);
    let inviteOpen = $state(false);
    let resetFor = $state<AdminAccount | null>(null);
    let deleteFor = $state<AdminAccount | null>(null);

    const meId = $derived($currentUser?.id ?? null);
    const activeAdmins = $derived(accounts.filter((account) => account.is_superuser && account.is_active));
    const onlyActiveAdminId = $derived(activeAdmins.length === 1 ? activeAdmins[0].id : null);
    const maxUsers = $derived(usage?.max_users ?? null);
    const full = $derived(usage !== null && maxUsers !== null && usage.used >= maxUsers);
    const registrationClosed = $derived(instanceConfig.config.accounts.registration_mode === 'disabled');
    const registrationLocked = $derived(instanceConfig.config.accounts.registration_locked);
    // The backend's order: a closed registration refuses an invitation before the limit is counted
    const inviteBlocked = $derived<'registration-disabled' | 'limit' | null>(registrationClosed ? 'registration-disabled' : full ? 'limit' : null);
    const confirmCopy = $derived.by(() => {
        if (pending === null) {
            return null;
        }
        const keys = CONFIRM_KEYS[pending.kind];
        const values = pending.kind === 'revoke-invite' ? {email: pending.invite.email || $_('settings.usersTab.invites.noEmail')} : {username: pending.account.username};
        return {title: $_(keys.title, {values}), message: $_(keys.message, {values}), confirm: $_(keys.confirm), danger: keys.danger};
    });

    async function load() {
        busy = true;
        try {
            const [list, open] = await Promise.all([zodiosApi.list_accounts_api_v1_users_get(), zodiosApi.list_invites_api_v1_users_invites_get()]);
            accounts = (list.items ?? []) as AdminAccount[];
            usage = list.usage as AccountsUsage;
            invites = (open.items ?? []) as OpenInvite[];
            loadFailed = false;
        } catch (e) {
            loadFailed = true;
            notify({name: 'accounts.action.failed', detail: {action: 'load', code: describeAccountError(e).code}, toast: {variant: 'error', message: $_('settings.usersTab.errors.load')}});
        } finally {
            busy = false;
        }
    }

    onMount(() => {
        void load();
    });

    /** Runs one administrator action, tells what happened (the toast only where the outcome is not on screen), then reloads. */
    async function perform(action: string, detail: Record<string, unknown>, call: () => Promise<unknown>, event: string, toastMessage?: string) {
        try {
            await call();
            notify(toastMessage ? {name: event, detail, toast: {variant: 'success', message: toastMessage}} : {name: event, detail});
        } catch (e) {
            const error = describeAccountError(e);
            notify({name: 'accounts.action.failed', detail: {...detail, action, code: error.code}, toast: {variant: 'error', message: accountErrorText(error, $_)}});
        }
        await load();
    }

    function setStatus(account: AdminAccount, body: {is_active: boolean} | {is_superuser: boolean}, action: string, event: string) {
        return perform(action, {user_id: account.id}, () => zodiosApi.update_account_api_v1_users__user_id__patch(body, {params: {user_id: account.id}}), event);
    }

    function onAction(action: UserAction, account: AdminAccount) {
        if (action === 'reactivate') {
            void setStatus(account, {is_active: true}, 'reactivate', 'accounts.user.reactivated');
        } else if (action === 'reset-link') {
            resetFor = account;
        } else if (action === 'delete') {
            deleteFor = account;
        } else {
            pending = {kind: action, account};
        }
    }

    async function confirmPending() {
        const current = pending;
        pending = null;
        if (current === null) {
            return;
        }
        if (current.kind === 'revoke-invite') {
            const inviteId = current.invite.id;
            await perform('revoke-invite', {invite_id: inviteId}, () => zodiosApi.revoke_invite_api_v1_users_invites__invite_id__delete(undefined, {params: {invite_id: inviteId}}), 'accounts.invite.revoked');
            return;
        }
        const {account} = current;
        const userId = account.id;
        switch (current.kind) {
            case 'deactivate':
                await setStatus(account, {is_active: false}, 'deactivate', 'accounts.user.deactivated');
                break;
            case 'cancel-setup':
                // The row still reads «waiting» afterwards: the toast tells what changed. `cancel_setup` makes it a cancellation
                // and nothing else: an administrator that completed its setup meanwhile answers 409 SETUP_COMPLETED (A-51)
                await perform(
                    'cancel-setup',
                    {user_id: userId},
                    () => zodiosApi.update_account_api_v1_users__user_id__patch({is_active: false, cancel_setup: true}, {params: {user_id: userId}}),
                    'accounts.user.setup-cancelled',
                    $_('settings.usersTab.toasts.setupCancelled', {values: {username: account.username}}),
                );
                break;
            case 'promote':
                await setStatus(account, {is_superuser: true}, 'promote', 'accounts.user.promoted');
                break;
            case 'demote':
                await setStatus(account, {is_superuser: false}, 'demote', 'accounts.user.demoted');
                break;
            case 'sign-out':
                await perform(
                    'sign-out',
                    {user_id: userId},
                    () => zodiosApi.revoke_account_sessions_api_v1_users__user_id__sessions_revoke_post(undefined, {params: {user_id: userId}}),
                    'accounts.user.sessions-revoked',
                    $_('settings.usersTab.toasts.signedOut', {values: {username: account.username}}),
                );
                break;
            case 'restart-guides':
                await perform(
                    'restart-guides',
                    {user_id: userId},
                    () => zodiosApi.reset_account_onboarding_api_v1_users__user_id__onboarding_reset_post(null, {params: {user_id: userId}}),
                    'accounts.user.onboarding-reset',
                    $_('settings.usersTab.toasts.guidesRestarted', {values: {username: account.username}}),
                );
                break;
        }
    }
</script>

<div aria-busy={busy} class="space-y-6 text-lf-primary" data-busy={busy ? 'true' : 'false'} data-testid="users-tab">
    <section class="rounded-lg border border-lf-subtle bg-lf-card p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex flex-wrap items-center gap-2">
                <Users class="h-5 w-5 text-lf-muted" />
                <h2 class="text-lg font-semibold text-lf-primary">{$_('settings.usersTab.title')}</h2>
                {#if usage}
                    <span class="rounded-full border border-lf-subtle bg-lf-panel px-2.5 py-0.5 text-sm text-lf-secondary" data-max={maxUsers ?? ''} data-testid="users-usage" data-used={usage.used}>
                        {maxUsers !== null ? $_('settings.usersTab.usage', {values: {used: usage.used, max: maxUsers}}) : $_('settings.usersTab.usageUnlimited', {values: {used: usage.used}})}
                    </span>
                {/if}
                {#if usage?.billing_url}
                    <a class="inline-flex items-center gap-1 text-sm text-lf-link hover:underline" data-testid="users-billing-link" href={usage.billing_url} rel="noopener noreferrer" target="_blank">
                        <CreditCard class="h-4 w-4" />{$_('settings.usersTab.billing')}<ExternalLink class="h-3 w-3" />
                    </a>
                {/if}
            </div>
            <button
                class="inline-flex items-center gap-1.5 rounded-md bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50"
                data-disabled-reason={inviteBlocked ?? undefined}
                data-testid="users-invite-button"
                disabled={inviteBlocked !== null}
                onclick={() => (inviteOpen = true)}
                type="button"
            >
                <UserPlus class="h-4 w-4" />{$_('settings.usersTab.invite.button')}
            </button>
        </div>
        <p class="mt-1 text-xs text-lf-muted">{$_('settings.usersTab.usageHint')}</p>

        {#if full}
            <div class="mt-3 rounded-md border border-lf-warning-line bg-lf-warning-soft px-3 py-2 text-sm text-lf-warning-on-soft" data-testid="users-limit-banner" role="status">
                {$_('settings.usersTab.limitBanner')}
                {#if usage?.billing_url}
                    <a class="ml-1 font-medium underline" data-testid="users-limit-billing-link" href={usage.billing_url} rel="noopener noreferrer" target="_blank">{$_('settings.usersTab.billing')}</a>
                {/if}
            </div>
        {/if}
        {#if inviteBlocked === 'registration-disabled'}
            <p class="mt-2 text-xs text-lf-muted" data-testid="users-invite-blocked">
                {registrationLocked ? $_('settings.usersTab.invite.blockedLocked', {values: {variable: 'LIBREFOLIO_REGISTRATION'}}) : $_('settings.usersTab.invite.blocked')}
            </p>
        {/if}
    </section>

    <section class="rounded-lg border border-lf-subtle bg-lf-card p-4">
        <h3 class="text-sm font-semibold text-lf-secondary">{$_('settings.usersTab.accounts.title')}</h3>
        {#if loadFailed}
            <p class="mt-2 rounded-md border border-lf-danger-line bg-lf-danger-soft px-3 py-2 text-sm text-lf-danger-on-soft" role="alert">{$_('settings.usersTab.errors.load')}</p>
        {/if}
        <ul class="mt-1 divide-y divide-lf-subtle" data-testid="users-accounts">
            {#each accounts as account (account.id)}
                <UserRow {account} {full} isOnlyActiveAdmin={account.id === onlyActiveAdminId} isSelf={account.id === meId} {onAction} />
            {/each}
        </ul>
    </section>

    <section class="rounded-lg border border-lf-subtle bg-lf-card p-4">
        <h3 class="text-sm font-semibold text-lf-secondary">{$_('settings.usersTab.invites.title')}</h3>
        <div class="mt-2" data-testid="users-invites">
            <InvitationsList {invites} onRevoke={(invite) => (pending = {kind: 'revoke-invite', invite})} />
        </div>
    </section>

    <ConfirmModal confirmText={confirmCopy?.confirm} danger={confirmCopy?.danger ?? false} message={confirmCopy?.message ?? ''} onCancel={() => (pending = null)} onConfirm={confirmPending} open={pending !== null} testId="users-confirm" title={confirmCopy?.title ?? ''} />

    <InviteDialog
        onClose={() => {
            inviteOpen = false;
            void load();
        }}
        open={inviteOpen}
    />

    {#if resetFor}
        {@const target = resetFor}
        <ResetLinkDialog account={{id: target.id, username: target.username}} onClose={() => (resetFor = null)} open />
    {/if}

    {#if deleteFor}
        {@const target = deleteFor}
        <AccountDeletionDialog
            account={{id: target.id, username: target.username, is_active: target.is_active}}
            mode="admin"
            onClose={() => (deleteFor = null)}
            onDeactivate={() => setStatus(target, {is_active: false}, 'deactivate', 'accounts.user.deactivated')}
            onDeleted={() => {
                deleteFor = null;
                void load();
            }}
            open
            testIdPrefix="users-delete"
        />
    {/if}
</div>
