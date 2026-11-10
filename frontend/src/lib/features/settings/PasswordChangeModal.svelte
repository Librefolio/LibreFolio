<script lang="ts">
    /**
     * PasswordChangeModal.svelte
     * Modal for changing user password
     */
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {trySave} from '$lib/utils/trySave';
    import {Check, X} from 'lucide-svelte';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
    import PasswordStrength from '$lib/components/ui/input/PasswordStrength.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {currentUser} from '$lib/stores/app/auth';

    type _DispatchEvents = {
        close: void;
        success: void;
    };
    const dispatch = createEventDispatcher();

    // Props
    export let isOpen: boolean = false;

    // State
    let currentPassword = '';
    let newPassword = '';
    let confirmPassword = '';
    let error = '';
    let success = '';
    let isSubmitting = false;

    // The rules are the app's own, read from PasswordStrength (`bind:valid`, decision 37): this modal keeps no copy of them.
    let passwordMeetsRules = false;
    $: canSubmit = currentPassword && newPassword && confirmPassword && passwordMeetsRules && newPassword === confirmPassword;

    function reset() {
        currentPassword = '';
        newPassword = '';
        confirmPassword = '';
        error = '';
        success = '';
    }

    function handleClose() {
        reset();
        dispatch('close');
    }

    async function handleSubmit() {
        if (isSubmitting || success) return;

        error = '';
        success = '';

        if (!passwordMeetsRules) {
            error = $_('auth.validation.passwordTooWeak');
            return;
        }

        if (newPassword !== confirmPassword) {
            error = $_('settings.passwordsMustMatch');
            return;
        }

        isSubmitting = true;

        // I-bis #22 (Batch 4.d-part2) — route through ``trySave`` for uniform
        // error extraction. ``toast: false`` because we already render the error
        // inline via ``InfoBanner``; a toast would duplicate the message.
        // ``onError`` preserves the two semantic mappings (incorrect / different
        // password) that existed before — the extractor alone would surface the
        // raw FastAPI detail, which is less friendly.
        const result = await trySave(
            () =>
                zodiosApi.change_password_api_v1_auth_change_password_post({
                    current_password: currentPassword,
                    new_password: newPassword,
                }),
            {
                toast: false,
                fallback: $_('settings.passwordChangeFailed'),
                onError: (err: unknown) => {
                    const raw: unknown = (err as any)?.response?.data?.detail;
                    // The server's limit on failed passwords (A8a): wait, in the user's language
                    if ((err as any)?.response?.status === 429 && raw && typeof raw === 'object' && (raw as {error_code?: unknown}).error_code === 'TOO_MANY_ATTEMPTS') {
                        error = $_('settings.tooManyPasswordAttempts');
                        return true;
                    }
                    if (raw && typeof raw === 'object' && (raw as {error_code?: unknown}).error_code === 'PASSWORD_TOO_WEAK') {
                        error = $_('auth.validation.passwordTooWeak');
                        return true;
                    }
                    const detail = typeof raw === 'string' ? raw.toLowerCase() : '';
                    if (detail.includes('incorrect')) {
                        error = $_('settings.currentPasswordIncorrect');
                        return true;
                    }
                    if (detail.includes('different')) {
                        error = $_('settings.passwordMustBeDifferent');
                        return true;
                    }
                    return false;
                },
            },
        );

        if (result.status === 'success') {
            success = $_('settings.passwordChanged');
            currentPassword = '';
            newPassword = '';
            confirmPassword = '';
            setTimeout(() => {
                dispatch('success');
                handleClose();
            }, 1500);
        } else if (!error) {
            error = result.message;
        }
        isSubmitting = false;
    }
</script>

<ModalBase maxWidth="md" onRequestClose={handleClose} open={isOpen} testId="password-change-modal" zIndex={50}>
    <div class="bg-lf-card rounded-xl w-full">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-lf-subtle">
            <h2 class="text-lg font-semibold text-lf-primary">
                {$_('settings.changePassword')}
            </h2>
            <button class="p-1 text-lf-muted hover:text-lf-secondary rounded-lg transition-colors" on:click={handleClose} type="button">
                <X size={20} />
            </button>
        </div>

        <!-- Body -->
        <form class="p-4 space-y-4" on:submit|preventDefault={handleSubmit}>
            <!-- Tells the browser's password manager which saved account the new password belongs to. -->
            <input autocomplete="username" hidden name="username" readonly type="text" value={$currentUser?.username ?? ''} />
            <InfoBanner dismissible message={error} ondismiss={() => (error = '')} variant="error" />

            {#if success}
                <div class="flex items-center gap-2 p-3 bg-lf-success-soft border border-lf-success-line rounded-lg text-lf-success-on-soft text-sm">
                    <Check size={16} />
                    <span>{success}</span>
                </div>
            {/if}

            <div class="space-y-2">
                <label class="block text-sm font-medium text-lf-secondary" for="currentPassword">
                    {$_('settings.currentPassword')}
                </label>
                <PasswordInput autocomplete="current-password" bind:value={currentPassword} disabled={isSubmitting || !!success} id="currentPassword" name="current-password" placeholder={$_('settings.currentPassword')} testId="password-current" />
            </div>

            <div class="space-y-2">
                <label class="block text-sm font-medium text-lf-secondary" for="newPassword">
                    {$_('settings.newPassword')}
                </label>
                <PasswordInput autocomplete="new-password" bind:value={newPassword} disabled={isSubmitting || !!success} id="newPassword" name="new-password" placeholder={$_('settings.newPassword')} testId="password-new" />
                <PasswordStrength bind:valid={passwordMeetsRules} password={newPassword} />
            </div>

            <div class="space-y-2">
                <label class="block text-sm font-medium text-lf-secondary" for="confirmPassword">
                    {$_('settings.confirmNewPassword')}
                </label>
                <PasswordInput autocomplete="new-password" bind:value={confirmPassword} disabled={isSubmitting || !!success} id="confirmPassword" name="confirm-password" placeholder={$_('settings.confirmNewPassword')} testId="password-confirm" />
                {#if confirmPassword && newPassword !== confirmPassword}
                    <p class="text-xs text-lf-danger">{$_('settings.passwordsMustMatch')}</p>
                {/if}
            </div>
        </form>

        <!-- Footer -->
        <div class="flex justify-end gap-3 p-4 border-t border-lf-subtle">
            <button class="px-4 py-2 text-lf-secondary hover:text-lf-primary transition-colors disabled:opacity-50" data-testid="password-change-cancel" disabled={isSubmitting} on:click={handleClose} type="button">
                {$_('common.cancel')}
            </button>
            <button class="px-4 py-2 bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed" data-testid="password-change-submit" disabled={!canSubmit || isSubmitting || !!success} on:click={handleSubmit} type="button">
                {#if isSubmitting}
                    {$_('common.loading')}
                {:else}
                    {$_('common.save')}
                {/if}
            </button>
        </div>
    </div>
</ModalBase>
