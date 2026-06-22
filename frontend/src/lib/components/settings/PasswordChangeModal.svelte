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

    // Password rules for validation
    const passwordRules = {
        minLength: (pwd: string) => pwd.length >= 8,
        hasUppercase: (pwd: string) => /[A-Z]/.test(pwd),
        hasLowercase: (pwd: string) => /[a-z]/.test(pwd),
        hasNumber: (pwd: string) => /\d/.test(pwd),
        hasSpecial: (pwd: string) => /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~;']/.test(pwd),
    };

    $: passwordMeetsRules = Object.values(passwordRules).every((check) => check(newPassword));
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
                    const detail = ((err as any)?.response?.data?.detail as string)?.toLowerCase() || '';
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
    <div class="bg-white dark:bg-slate-800 rounded-xl w-full">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {$_('settings.changePassword')}
            </h2>
            <button class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg transition-colors" on:click={handleClose} type="button">
                <X size={20} />
            </button>
        </div>

        <!-- Body -->
        <form class="p-4 space-y-4" on:submit|preventDefault={handleSubmit}>
            <InfoBanner dismissible message={error} ondismiss={() => (error = '')} variant="error" />

            {#if success}
                <div class="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg text-green-700 dark:text-green-300 text-sm">
                    <Check size={16} />
                    <span>{success}</span>
                </div>
            {/if}

            <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300" for="currentPassword">
                    {$_('settings.currentPassword')}
                </label>
                <PasswordInput autocomplete="current-password" bind:value={currentPassword} disabled={isSubmitting} id="currentPassword" placeholder={$_('settings.currentPassword')} testId="password-current" />
            </div>

            <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300" for="newPassword">
                    {$_('settings.newPassword')}
                </label>
                <PasswordInput autocomplete="new-password" bind:value={newPassword} disabled={isSubmitting} id="newPassword" placeholder={$_('settings.newPassword')} testId="password-new" />
                <PasswordStrength password={newPassword} />
            </div>

            <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300" for="confirmPassword">
                    {$_('settings.confirmNewPassword')}
                </label>
                <PasswordInput autocomplete="new-password" bind:value={confirmPassword} disabled={isSubmitting} id="confirmPassword" placeholder={$_('settings.confirmNewPassword')} testId="password-confirm" />
                {#if confirmPassword && newPassword !== confirmPassword}
                    <p class="text-xs text-red-500">{$_('settings.passwordsMustMatch')}</p>
                {/if}
            </div>
        </form>

        <!-- Footer -->
        <div class="flex justify-end gap-3 p-4 border-t border-gray-200 dark:border-slate-700">
            <button class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors disabled:opacity-50" data-testid="password-change-cancel" disabled={isSubmitting} on:click={handleClose} type="button">
                {$_('common.cancel')}
            </button>
            <button class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed" data-testid="password-change-submit" disabled={!canSubmit || isSubmitting} on:click={handleSubmit} type="button">
                {#if isSubmitting}
                    {$_('common.loading')}
                {:else}
                    {$_('common.save')}
                {/if}
            </button>
        </div>
    </div>
</ModalBase>
