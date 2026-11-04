<!--
AccountDeletionDialog — deleting an account, one's own (Profile) or another's (Users tab, administrators).

It first shows what the deletion would take, from the backend's preview, computed by the very rule of the deletion: the
brokers the account is the last owner of go with their transactions and files; on the others only its access goes; the
transfers with those brokers lose their other half (backlog V-3). An administrator is offered to deactivate the account
first, which keeps everything and can be undone. The deletion itself needs the username typed.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {notify} from '$lib/stores/app/notify.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {accountErrorText, describeAccountError, type AccountError} from './users/accountErrors';

    interface DeletionPreview {
        user_id: number;
        username: string;
        brokers_deleted: {id: number; name: string; transactions: number}[];
        brokers_left: {id: number; name: string; role: string}[];
        transfers_unpaired: number;
    }

    interface AccountDeletionResult {
        user_id: number;
        brokers_deleted: number;
    }

    interface Props {
        open: boolean;
        mode: 'self' | 'admin';
        account: {id: number; username: string; is_active: boolean};
        /** Prefix of every data-testid: `profile-delete` in the Profile tab, `users-delete` in the Users tab. */
        testIdPrefix: string;
        onClose: () => void;
        onDeleted: (result: AccountDeletionResult) => void;
        /** Administrators only: deactivate the account instead, offered first. */
        onDeactivate?: () => void | Promise<void>;
    }

    let {open, mode, account, testIdPrefix, onClose, onDeleted, onDeactivate}: Props = $props();

    const ROLE_KEY: Record<string, string> = {
        OWNER: 'settings.accountDeletion.roles.OWNER',
        EDITOR: 'settings.accountDeletion.roles.EDITOR',
        VIEWER: 'settings.accountDeletion.roles.VIEWER',
    };

    const uid = $props.id();
    let preview = $state<DeletionPreview | null>(null);
    let busy = $state(false);
    let deleting = $state(false);
    let deactivating = $state(false);
    let error = $state<AccountError | null>(null);
    let confirmText = $state('');

    const canDelete = $derived(preview !== null && !busy && !deleting && confirmText === account.username);
    const offerDeactivation = $derived(mode === 'admin' && account.is_active && onDeactivate !== undefined);

    async function loadPreview() {
        busy = true;
        preview = null;
        error = null;
        confirmText = '';
        try {
            preview = (mode === 'self' ? await zodiosApi.preview_own_account_deletion_api_v1_auth_users_me_deletion_preview_get() : await zodiosApi.preview_account_deletion_api_v1_users__user_id__deletion_preview_get({params: {user_id: account.id}})) as DeletionPreview;
        } catch (e) {
            error = describeAccountError(e);
        } finally {
            busy = false;
        }
    }

    $effect(() => {
        if (open) {
            untrack(() => void loadPreview());
        }
    });

    async function deactivateInstead() {
        deactivating = true;
        try {
            await onDeactivate?.();
        } finally {
            deactivating = false;
        }
        onClose();
    }

    async function confirmDeletion() {
        if (!canDelete || preview === null) {
            return;
        }
        deleting = true;
        error = null;
        const brokersDeleted = preview.brokers_deleted.length;
        try {
            if (mode === 'self') {
                await zodiosApi.delete_own_account_api_v1_auth_users_me_delete(undefined, {});
            } else {
                await zodiosApi.delete_account_api_v1_users__user_id__delete(undefined, {params: {user_id: account.id}});
            }
        } catch (e) {
            error = describeAccountError(e, 'delete');
            notify({name: 'accounts.action.failed', detail: {action: 'delete', code: error.code, user_id: account.id}, toast: {variant: 'error', message: accountErrorText(error, $_)}});
            deleting = false;
            return;
        }
        deleting = false;
        const message = mode === 'self' ? $_('settings.accountDeletion.deletedSelf') : $_('settings.accountDeletion.deletedAdmin', {values: {username: account.username, count: brokersDeleted}});
        notify({name: 'accounts.user.deleted', detail: {user_id: account.id, brokers_deleted: brokersDeleted, mode}, toast: {variant: 'success', message}});
        onDeleted({user_id: account.id, brokers_deleted: brokersDeleted});
    }
</script>

<ModalBase labelledBy="{uid}-title" maxWidth="lg" onRequestClose={onClose} {open} trapFocus>
    <div aria-busy={busy} class="space-y-4 p-5 text-lf-primary" data-busy={busy ? 'true' : 'false'} data-testid="{testIdPrefix}-dialog">
        <div>
            <h2 class="text-lg font-semibold text-lf-danger" id="{uid}-title">
                {mode === 'self' ? $_('settings.deleteAccountConfirm') : $_('settings.accountDeletion.titleAdmin', {values: {username: account.username}})}
            </h2>
            <p class="mt-1 text-sm text-lf-secondary">
                {mode === 'self' ? $_('settings.deleteAccountWarning') : $_('settings.accountDeletion.warningAdmin')}
            </p>
        </div>

        {#if offerDeactivation}
            <div class="rounded-md border border-lf-subtle bg-lf-panel p-3">
                <p class="text-sm font-medium text-lf-primary">{$_('settings.accountDeletion.deactivateTitle')}</p>
                <p class="mt-1 text-xs text-lf-muted">{$_('settings.accountDeletion.deactivateText')}</p>
                <button
                    class="mt-2 rounded-md bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50"
                    data-testid="{testIdPrefix}-deactivate"
                    disabled={deactivating || deleting}
                    onclick={deactivateInstead}
                    type="button"
                >
                    {$_('settings.accountDeletion.deactivateAction')}
                </button>
            </div>
        {/if}

        {#if busy}
            <p class="text-sm text-lf-muted">{$_('settings.accountDeletion.loading')}</p>
        {:else if preview}
            <div class="space-y-3" data-testid="{testIdPrefix}-preview">
                {#if preview.brokers_deleted.length > 0}
                    <div>
                        <p class="text-sm font-medium text-lf-primary">{$_('settings.accountDeletion.brokersDeleted')}</p>
                        <ul class="mt-1 divide-y divide-lf-subtle rounded-md border border-lf-subtle">
                            {#each preview.brokers_deleted as broker (broker.id)}
                                <li class="flex items-center justify-between gap-3 px-3 py-1.5 text-sm" data-broker-id={broker.id} data-testid="{testIdPrefix}-broker-deleted" data-transactions={broker.transactions}>
                                    <span class="truncate">{broker.name}</span>
                                    <span class="shrink-0 text-xs text-lf-muted">{$_('settings.accountDeletion.transactions', {values: {count: broker.transactions}})}</span>
                                </li>
                            {/each}
                        </ul>
                    </div>
                {:else}
                    <p class="text-sm text-lf-muted">{$_('settings.accountDeletion.noBrokersDeleted')}</p>
                {/if}

                {#if preview.brokers_left.length > 0}
                    <div>
                        <p class="text-sm font-medium text-lf-primary">{$_('settings.accountDeletion.brokersLeft')}</p>
                        <ul class="mt-1 divide-y divide-lf-subtle rounded-md border border-lf-subtle">
                            {#each preview.brokers_left as broker (broker.id)}
                                <li class="flex items-center justify-between gap-3 px-3 py-1.5 text-sm" data-broker-id={broker.id} data-role={broker.role} data-testid="{testIdPrefix}-broker-left">
                                    <span class="truncate">{broker.name}</span>
                                    <span class="shrink-0 text-xs text-lf-muted">{ROLE_KEY[broker.role] ? $_(ROLE_KEY[broker.role]) : broker.role}</span>
                                </li>
                            {/each}
                        </ul>
                    </div>
                {/if}

                {#if preview.transfers_unpaired > 0}
                    <p class="rounded-md border border-lf-warning-line bg-lf-warning-soft px-3 py-2 text-sm text-lf-warning-on-soft" data-count={preview.transfers_unpaired} data-testid="{testIdPrefix}-unpaired">
                        {$_('settings.accountDeletion.unpaired', {values: {count: preview.transfers_unpaired}})}
                    </p>
                {/if}
            </div>
        {/if}

        {#if error}
            <p class="rounded-md border border-lf-danger-line bg-lf-danger-soft px-3 py-2 text-sm text-lf-danger-on-soft" data-error-code={error.code ?? ''} data-testid="{testIdPrefix}-error" role="alert">
                {busy || preview !== null ? accountErrorText(error, $_) : $_('settings.accountDeletion.previewFailed')}
            </p>
        {/if}

        <div>
            <label class="mb-1 block text-sm text-lf-secondary" for="{uid}-confirm">
                {$_('settings.typeUsernameToConfirm', {values: {username: account.username}})}
            </label>
            <input
                autocomplete="off"
                bind:value={confirmText}
                class="w-full rounded-md border border-lf-input bg-lf-field px-3 py-2 text-sm text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:ring-2 focus:ring-lf-focus"
                data-testid="{testIdPrefix}-confirm-input"
                disabled={preview === null || deleting}
                id="{uid}-confirm"
                placeholder={account.username}
                spellcheck="false"
                type="text"
            />
            <p class="mt-1 text-xs text-lf-muted">{$_('settings.accountDeletion.irreversible')}</p>
        </div>

        <div class="flex justify-end gap-2">
            <button class="rounded-md border border-lf-input bg-lf-card px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover" data-testid="{testIdPrefix}-cancel" onclick={onClose} type="button">
                {$_('common.cancel')}
            </button>
            <button class="rounded-md bg-lf-danger px-3 py-1.5 text-sm font-medium text-lf-on-status disabled:cursor-not-allowed disabled:opacity-50" data-testid="{testIdPrefix}-confirm" disabled={!canDelete} onclick={confirmDeletion} type="button">
                {deleting ? $_('common.deleting') : $_('settings.deleteAccountPermanently')}
            </button>
        </div>
    </div>
</ModalBase>
