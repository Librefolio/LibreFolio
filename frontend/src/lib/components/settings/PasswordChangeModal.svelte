<script lang="ts">
    /**
     * PasswordChangeModal.svelte
     * Modal for changing user password
     */
    import { createEventDispatcher } from 'svelte';
    import { _ } from '$lib/i18n';
    import { zodiosApi } from '$lib/api';
    import { isAxiosError } from 'axios';
    import { X, Check, AlertCircle } from 'lucide-svelte';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
    import PasswordStrength from '$lib/components/ui/input/PasswordStrength.svelte';

    const dispatch = createEventDispatcher<{
        close: void;
        success: void;
    }>();

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

    $: passwordMeetsRules = Object.values(passwordRules).every(check => check(newPassword));
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

        try {
            await zodiosApi.change_password_api_v1_auth_change_password_post({
                current_password: currentPassword,
                new_password: newPassword
            });

            success = $_('settings.passwordChanged');
            setTimeout(() => {
                dispatch('success');
                handleClose();
            }, 1500);
        } catch (e) {
            if (isAxiosError(e)) {
                const detail = (e.response?.data?.detail as string)?.toLowerCase() || '';
                if (detail.includes('incorrect')) {
                    error = $_('settings.currentPasswordIncorrect');
                } else if (detail.includes('different')) {
                    error = $_('settings.passwordMustBeDifferent');
                } else {
                    error = e.message || $_('settings.passwordChangeFailed');
                }
            } else {
                error = $_('settings.passwordChangeFailed');
            }
        } finally {
            isSubmitting = false;
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            handleClose();
        }
    }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <!-- Backdrop -->
    <div
        class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        on:click|self={handleClose}
        role="dialog"
        aria-modal="true"
        tabindex="-1"
    >
        <!-- Modal -->
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-md" data-testid="password-change-modal">
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700">
                <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {$_('settings.changePassword')}
                </h2>
                <button
                    type="button"
                    on:click={handleClose}
                    class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg transition-colors"
                >
                    <X size={20} />
                </button>
            </div>

            <!-- Body -->
            <form on:submit|preventDefault={handleSubmit} class="p-4 space-y-4">
                {#if error}
                    <div class="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
                        <AlertCircle size={16} />
                        <span>{error}</span>
                    </div>
                {/if}

                {#if success}
                    <div class="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg text-green-700 dark:text-green-300 text-sm">
                        <Check size={16} />
                        <span>{success}</span>
                    </div>
                {/if}

                <div class="space-y-2">
                    <label for="currentPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        {$_('settings.currentPassword')}
                    </label>
                    <PasswordInput
                        id="currentPassword"
                        bind:value={currentPassword}
                        placeholder={$_('settings.currentPassword')}
                        autocomplete="current-password"
                        disabled={isSubmitting}
                        testId="password-current"
                    />
                </div>

                <div class="space-y-2">
                    <label for="newPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        {$_('settings.newPassword')}
                    </label>
                    <PasswordInput
                        id="newPassword"
                        bind:value={newPassword}
                        placeholder={$_('settings.newPassword')}
                        autocomplete="new-password"
                        disabled={isSubmitting}
                        testId="password-new"
                    />
                    <PasswordStrength password={newPassword} />
                </div>

                <div class="space-y-2">
                    <label for="confirmPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        {$_('settings.confirmNewPassword')}
                    </label>
                    <PasswordInput
                        id="confirmPassword"
                        bind:value={confirmPassword}
                        placeholder={$_('settings.confirmNewPassword')}
                        autocomplete="new-password"
                        disabled={isSubmitting}
                        testId="password-confirm"
                    />
                    {#if confirmPassword && newPassword !== confirmPassword}
                        <p class="text-xs text-red-500">{$_('settings.passwordsMustMatch')}</p>
                    {/if}
                </div>
            </form>

            <!-- Footer -->
            <div class="flex justify-end gap-3 p-4 border-t border-gray-200 dark:border-slate-700">
                <button
                    type="button"
                    on:click={handleClose}
                    disabled={isSubmitting}
                    class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors disabled:opacity-50"
                    data-testid="password-change-cancel"
                >
                    {$_('common.cancel')}
                </button>
                <button
                    type="button"
                    on:click={handleSubmit}
                    disabled={!canSubmit || isSubmitting}
                    class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="password-change-submit"
                >
                    {#if isSubmitting}
                        {$_('common.loading')}
                    {:else}
                        {$_('common.save')}
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}
