<script lang="ts">
    import {_} from '$lib/i18n';
    import {currentUser} from '$lib/stores/auth';
    import {api, ApiError} from '$lib/api';
    import {Calendar, Check, Key, Mail, User, X} from 'lucide-svelte';
    import PasswordInput from '$lib/components/ui/PasswordInput.svelte';

    // Format date for display
    function formatDate(dateStr: string | undefined): string {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    // Password change state
    let showPasswordForm = false;
    let currentPassword = '';
    let newPassword = '';
    let confirmPassword = '';
    let passwordError = '';
    let passwordSuccess = '';
    let isChangingPassword = false;

    function togglePasswordForm() {
        showPasswordForm = !showPasswordForm;
        if (!showPasswordForm) {
            resetPasswordForm();
        }
    }

    function resetPasswordForm() {
        currentPassword = '';
        newPassword = '';
        confirmPassword = '';
        passwordError = '';
        passwordSuccess = '';
    }

    async function handlePasswordChange() {
        passwordError = '';
        passwordSuccess = '';

        // Validation
        if (newPassword.length < 8) {
            passwordError = $_('settings.passwordTooShort');
            return;
        }

        if (newPassword !== confirmPassword) {
            passwordError = $_('settings.passwordsMustMatch');
            return;
        }

        isChangingPassword = true;

        try {
            await api.post('/auth/change-password', {
                current_password: currentPassword,
                new_password: newPassword
            });

            passwordSuccess = $_('settings.passwordChanged');
            setTimeout(() => {
                showPasswordForm = false;
                resetPasswordForm();
            }, 2000);
        } catch (e) {
            if (e instanceof ApiError) {
                const detail = (e.data as { detail?: string })?.detail?.toLowerCase() || '';
                if (detail.includes('incorrect')) {
                    passwordError = $_('settings.currentPasswordIncorrect');
                } else if (detail.includes('different')) {
                    passwordError = $_('settings.passwordMustBeDifferent');
                } else {
                    passwordError = e.message || $_('settings.passwordChangeFailed');
                }
            } else {
                passwordError = $_('settings.passwordChangeFailed');
            }
        } finally {
            isChangingPassword = false;
        }
    }
</script>

<div class="space-y-6">
    <h3 class="text-lg font-semibold text-gray-700">{$_('settings.profileInfo')}</h3>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Username -->
        <div class="space-y-2">
            <label class="flex items-center text-sm font-medium text-gray-600">
                <User class="mr-2" size={16}/>
                {$_('auth.username')}
            </label>
            <div class="px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-700">
                {$currentUser?.username || '-'}
            </div>
        </div>

        <!-- Email -->
        <div class="space-y-2">
            <label class="flex items-center text-sm font-medium text-gray-600">
                <Mail class="mr-2" size={16}/>
                {$_('auth.email')}
            </label>
            <div class="px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-700">
                {$currentUser?.email || '-'}
            </div>
        </div>

        <!-- Account Created -->
        <div class="space-y-2">
            <label class="flex items-center text-sm font-medium text-gray-600">
                <Calendar class="mr-2" size={16}/>
                {$_('settings.accountCreated')}
            </label>
            <div class="px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-700">
                {formatDate($currentUser?.created_at)}
            </div>
        </div>
    </div>

    <!-- Change Password Section -->
    <div class="mt-8 pt-6 border-t border-gray-200">
        <div class="flex items-center justify-between mb-4">
            <div>
                <h4 class="text-md font-medium text-gray-700 flex items-center">
                    <Key class="mr-2" size={18}/>
                    {$_('settings.security')}
                </h4>
                <p class="text-sm text-gray-500 mt-1">{$_('settings.changePasswordDescription')}</p>
            </div>
            {#if !showPasswordForm}
                <button
                        on:click={togglePasswordForm}
                        class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                >
                    {$_('settings.changePassword')}
                </button>
            {/if}
        </div>

        {#if showPasswordForm}
            <form on:submit|preventDefault={handlePasswordChange} class="bg-gray-50 rounded-lg p-6 space-y-4">
                {#if passwordError}
                    <div class="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                        <X size={16}/>
                        <span>{passwordError}</span>
                    </div>
                {/if}

                {#if passwordSuccess}
                    <div class="flex items-center space-x-2 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
                        <Check size={16}/>
                        <span>{passwordSuccess}</span>
                    </div>
                {/if}

                <div class="space-y-2">
                    <label for="currentPassword" class="block text-sm font-medium text-gray-700">
                        {$_('settings.currentPassword')}
                    </label>
                    <PasswordInput
                            id="currentPassword"
                            bind:value={currentPassword}
                            placeholder={$_('settings.currentPassword')}
                            autocomplete="current-password"
                            disabled={isChangingPassword}
                    />
                </div>

                <div class="space-y-2">
                    <label for="newPassword" class="block text-sm font-medium text-gray-700">
                        {$_('settings.newPassword')}
                    </label>
                    <PasswordInput
                            id="newPassword"
                            bind:value={newPassword}
                            placeholder={$_('settings.newPassword')}
                            autocomplete="new-password"
                            disabled={isChangingPassword}
                    />
                </div>

                <div class="space-y-2">
                    <label for="confirmPassword" class="block text-sm font-medium text-gray-700">
                        {$_('settings.confirmNewPassword')}
                    </label>
                    <PasswordInput
                            id="confirmPassword"
                            bind:value={confirmPassword}
                            placeholder={$_('settings.confirmNewPassword')}
                            autocomplete="new-password"
                            disabled={isChangingPassword}
                    />
                </div>

                <div class="flex justify-end space-x-3 pt-2">
                    <button
                            type="button"
                            on:click={togglePasswordForm}
                            class="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                            disabled={isChangingPassword}
                    >
                        {$_('common.cancel')}
                    </button>
                    <button
                            type="submit"
                            class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                            disabled={isChangingPassword || !currentPassword || !newPassword || !confirmPassword}
                    >
                        {#if isChangingPassword}
                            {$_('common.loading')}
                        {:else}
                            {$_('common.save')}
                        {/if}
                    </button>
                </div>
            </form>
        {/if}
    </div>
</div>

