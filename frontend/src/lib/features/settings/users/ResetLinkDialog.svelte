<!--
ResetLinkDialog — an administrator creates a single-use password-reset link for an account (the links created before
for it stop working), then shares it through LinkShare.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {notify} from '$lib/stores/app/notify.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import LinkShare from './LinkShare.svelte';
    import {accountErrorText, describeAccountError, type AccountError} from './accountErrors';

    interface ResetLink {
        token: string;
        path: string;
        url?: string | null;
        expires_at: string;
    }

    interface Props {
        open: boolean;
        account: {id: number; username: string};
        onClose: () => void;
    }

    let {open, account, onClose}: Props = $props();

    const uid = $props.id();
    let creating = $state(false);
    let error = $state<AccountError | null>(null);
    let created = $state<ResetLink | null>(null);

    $effect(() => {
        if (open) {
            untrack(() => {
                creating = false;
                error = null;
                created = null;
            });
        }
    });

    async function create() {
        if (creating) {
            return;
        }
        creating = true;
        error = null;
        try {
            created = (await zodiosApi.create_password_reset_link_api_v1_users__user_id__password_reset_link_post(undefined, {params: {user_id: account.id}})) as ResetLink;
            notify({
                name: 'accounts.reset-link.created',
                detail: {user_id: account.id},
                toast: {variant: 'success', message: $_('settings.usersTab.toasts.resetLinkCreated', {values: {username: account.username}})},
            });
        } catch (e) {
            error = describeAccountError(e);
            notify({name: 'accounts.action.failed', detail: {action: 'reset-link', code: error.code, user_id: account.id}, toast: {variant: 'error', message: accountErrorText(error, $_)}});
        } finally {
            creating = false;
        }
    }
</script>

<ModalBase labelledBy="{uid}-title" maxWidth="lg" onRequestClose={onClose} {open} testId="users-reset-dialog" trapFocus>
    <div class="space-y-4 p-5 text-lf-primary">
        <h2 class="text-lg font-semibold" id="{uid}-title">{$_('settings.usersTab.reset.title', {values: {username: account.username}})}</h2>

        {#if created === null}
            <p class="text-sm text-lf-secondary">{$_('settings.usersTab.reset.message')}</p>
            {#if error}
                <p class="rounded-md border border-lf-danger-line bg-lf-danger-soft px-3 py-2 text-sm text-lf-danger-on-soft" data-error-code={error.code ?? ''} data-testid="users-reset-error" role="alert">
                    {accountErrorText(error, $_)}
                </p>
            {/if}
            <div class="flex justify-end gap-2">
                <button class="rounded-md border border-lf-input bg-lf-card px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover" data-testid="users-reset-cancel" onclick={onClose} type="button">
                    {$_('common.cancel')}
                </button>
                <button class="rounded-md bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50" data-testid="users-reset-create" disabled={creating} onclick={create} type="button">
                    {$_('settings.usersTab.reset.create')}
                </button>
            </div>
        {:else}
            <p class="text-sm text-lf-secondary">{$_('settings.usersTab.reset.ready', {values: {username: account.username}})}</p>
            <LinkShare context={{username: account.username, userId: account.id}} expiresAt={created.expires_at} path={created.path} purpose="password_reset" url={created.url ?? null} />
            <div class="flex justify-end">
                <button class="rounded-md bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover" data-testid="users-reset-close" onclick={onClose} type="button">
                    {$_('settings.usersTab.done')}
                </button>
            </div>
        {/if}
    </div>
</ModalBase>
