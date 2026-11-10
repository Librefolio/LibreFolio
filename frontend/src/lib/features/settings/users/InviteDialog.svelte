<!--
InviteDialog — an administrator creates an invitation (optional e-mail, administrator or not), then shares its
single-use link through LinkShare. Refusals of the instance (registration closed, no free place) stay on the form.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {notify} from '$lib/stores/app/notify.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import LinkShare from './LinkShare.svelte';
    import {accountErrorText, describeAccountError, type AccountError} from './accountErrors';

    interface InviteCreated {
        invite: {id: number; grants_admin: boolean; email?: string | null; expires_at: string};
        token: string;
        path: string;
        url?: string | null;
    }

    interface Props {
        open: boolean;
        onClose: () => void;
        onCreated?: (response: InviteCreated) => void;
    }

    let {open, onClose, onCreated}: Props = $props();

    const uid = $props.id();
    let email = $state('');
    let grantsAdmin = $state(false);
    let creating = $state(false);
    let error = $state<AccountError | null>(null);
    let created = $state<InviteCreated | null>(null);

    // Every opening starts from an empty form
    $effect(() => {
        if (open) {
            untrack(() => {
                email = '';
                grantsAdmin = false;
                creating = false;
                error = null;
                created = null;
            });
        }
    });

    async function create(event: SubmitEvent) {
        event.preventDefault();
        if (creating) {
            return;
        }
        creating = true;
        error = null;
        const body: {grants_admin: boolean; email?: string} = {grants_admin: grantsAdmin};
        const address = email.trim();
        if (address) {
            body.email = address;
        }
        try {
            created = (await zodiosApi.create_invite_api_v1_users_invites_post(body)) as InviteCreated;
            notify({name: 'accounts.invite.created', detail: {invite_id: created.invite.id, grants_admin: created.invite.grants_admin}});
        } catch (e) {
            error = describeAccountError(e);
            notify({name: 'accounts.action.failed', detail: {action: 'invite', code: error.code}, toast: {variant: 'error', message: accountErrorText(error, $_)}});
        } finally {
            creating = false;
        }
    }

    function done() {
        const response = created;
        onClose();
        if (response) {
            onCreated?.(response);
        }
    }
</script>

<ModalBase labelledBy="{uid}-title" maxWidth="lg" onRequestClose={onClose} {open} testId="users-invite-dialog" trapFocus>
    <div class="space-y-4 p-5 text-lf-primary">
        <h2 class="text-lg font-semibold" id="{uid}-title">{$_('settings.usersTab.invite.title')}</h2>

        {#if created === null}
            <form class="space-y-4" onsubmit={create}>
                <div>
                    <label class="mb-1 block text-sm font-medium text-lf-secondary" for="{uid}-email">{$_('settings.usersTab.invite.emailLabel')}</label>
                    <input
                        autocomplete="off"
                        bind:value={email}
                        class="w-full rounded-md border border-lf-input bg-lf-field px-3 py-2 text-sm text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:ring-2 focus:ring-lf-focus"
                        data-testid="users-invite-email"
                        id="{uid}-email"
                        type="email"
                    />
                    <p class="mt-1 text-xs text-lf-muted">{$_('settings.usersTab.invite.emailHint')}</p>
                </div>

                <label class="flex items-start gap-3">
                    <input bind:checked={grantsAdmin} class="mt-0.5 h-4 w-4 rounded border border-lf-input" data-testid="users-invite-admin" type="checkbox" />
                    <span>
                        <span class="block text-sm font-medium text-lf-primary">{$_('settings.usersTab.invite.adminLabel')}</span>
                        <span class="block text-xs text-lf-muted">{$_('settings.usersTab.invite.adminHint')}</span>
                    </span>
                </label>

                {#if error}
                    <p class="rounded-md border border-lf-danger-line bg-lf-danger-soft px-3 py-2 text-sm text-lf-danger-on-soft" data-error-code={error.code ?? ''} data-testid="users-invite-error" role="alert">
                        {accountErrorText(error, $_)}
                    </p>
                {/if}

                <div class="flex justify-end gap-2">
                    <button class="rounded-md border border-lf-input bg-lf-card px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover" data-testid="users-invite-cancel" onclick={onClose} type="button">
                        {$_('common.cancel')}
                    </button>
                    <button class="rounded-md bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50" data-testid="users-invite-create" disabled={creating} type="submit">
                        {$_('settings.usersTab.invite.create')}
                    </button>
                </div>
            </form>
        {:else}
            <p class="text-sm text-lf-secondary">{$_('settings.usersTab.invite.ready')}</p>
            <LinkShare context={{email: created.invite.email ?? null}} expiresAt={created.invite.expires_at} path={created.path} purpose="invite" url={created.url ?? null} />
            <div class="flex justify-end">
                <button class="rounded-md bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover" data-testid="users-invite-done" onclick={done} type="button">
                    {$_('settings.usersTab.done')}
                </button>
            </div>
        {/if}
    </div>
</ModalBase>
