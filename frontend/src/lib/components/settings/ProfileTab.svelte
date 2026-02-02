<script lang="ts">
    import {_} from '$lib/i18n';
    import {auth, currentUser} from '$lib/stores/auth';
    import {zodiosApi} from '$lib/api';
    import {isAxiosError} from 'axios';
    import {goto} from '$app/navigation';
    import {debug} from '$lib/debug';
    import {Calendar, Key, Mail, User, AlertCircle, CheckCircle, Trash2, Save, Undo, Pencil, PencilOff} from 'lucide-svelte';
    import PasswordChangeModal from '$lib/components/settings/PasswordChangeModal.svelte';

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

    // Edit lock state
    let isLocked = true;

    // Confirm discard dialog
    let showDiscardConfirm = false;

    // Password change modal state
    let showPasswordModal = false;

    // Delete account modal state
    let showDeleteModal = false;
    let deleteConfirmText = '';
    let deleting = false;

    // Profile editing state
    let saving = false;
    let error: string | null = null;
    let successItems: string[] = [];  // Array of saved field names for bullet list

    // Original values (from server)
    let originalUsername = $currentUser?.username ?? '';
    let originalEmail = $currentUser?.email ?? '';

    // Edited values (local state)
    let editedUsername = $currentUser?.username ?? '';
    let editedEmail = $currentUser?.email ?? '';

    // Sync original values when currentUser changes (separate from edited to avoid cycles)
    $: {
        const user = $currentUser;
        if (user) {
            debug.log('ProfileTab', 'User data updated', user.username);
            originalUsername = user.username;
            originalEmail = user.email;
        }
    }

    // Track modifications (separate reactive statements)
    $: usernameModified = editedUsername !== originalUsername;
    $: emailModified = editedEmail !== originalEmail;
    $: hasAnyChanges = usernameModified || emailModified;

    // Check if delete confirmation matches username
    $: canDelete = deleteConfirmText === $currentUser?.username;

    function toggleLock() {
        if (!isLocked && hasAnyChanges) {
            // Show confirmation dialog
            showDiscardConfirm = true;
            return;
        }
        isLocked = !isLocked;
        debug.log('ProfileTab', 'toggleLock', isLocked);
    }

    function confirmDiscard() {
        undoAll();
        isLocked = true;
        showDiscardConfirm = false;
        debug.log('ProfileTab', 'Changes discarded');
    }

    function cancelDiscard() {
        showDiscardConfirm = false;
    }

    // Save individual field
    async function saveField(field: 'username' | 'email') {
        debug.log('ProfileTab', 'saveField', field);
        saving = true;
        error = null;
        successItems = [];

        try {
            const payload = field === 'username'
                ? { username: editedUsername }
                : { email: editedEmail };

            await zodiosApi.update_profile_api_v1_auth_profile_put(payload);
            await auth.checkAuth();

            const fieldName = field === 'username' ? $_('auth.username') : $_('auth.email');
            successItems = [fieldName];
            setTimeout(() => successItems = [], 3000);
        } catch (e: unknown) {
            debug.error('ProfileTab', 'saveField failed', e);
            const detail = isAxiosError(e) ? e.response?.data?.detail : null;
            error = detail || (e instanceof Error ? e.message : $_('settings.updateFailed'));
            if (field === 'username') editedUsername = originalUsername;
            else editedEmail = originalEmail;
            setTimeout(() => error = null, 5000);
        } finally {
            saving = false;
        }
    }

    // Undo individual field
    function undoField(field: 'username' | 'email') {
        debug.log('ProfileTab', 'undoField', field);
        if (field === 'username') editedUsername = originalUsername;
        else editedEmail = originalEmail;
    }

    // Save all changes
    async function saveAll() {
        debug.log('ProfileTab', 'saveAll');
        saving = true;
        error = null;
        successItems = [];

        const saved: string[] = [];

        try {
            if (usernameModified) {
                await zodiosApi.update_profile_api_v1_auth_profile_put({ username: editedUsername });
                saved.push($_('auth.username'));
            }
            if (emailModified) {
                await zodiosApi.update_profile_api_v1_auth_profile_put({ email: editedEmail });
                saved.push($_('auth.email'));
            }

            if (saved.length > 0) {
                await auth.checkAuth();
                successItems = saved;
                setTimeout(() => successItems = [], 4000);
            }
        } catch (e: unknown) {
            debug.error('ProfileTab', 'saveAll failed', e);
            const detail = isAxiosError(e) ? e.response?.data?.detail : null;
            error = detail || (e instanceof Error ? e.message : $_('settings.updateFailed'));
            setTimeout(() => error = null, 5000);
        } finally {
            saving = false;
        }
    }

    // Undo all changes
    function undoAll() {
        debug.log('ProfileTab', 'undoAll');
        editedUsername = originalUsername;
        editedEmail = originalEmail;
    }

    async function handleDeleteAccount() {
        if (!canDelete) return;
        debug.log('ProfileTab', 'handleDeleteAccount');

        deleting = true;
        error = null;

        try {
            await zodiosApi.delete_own_account_api_v1_auth_users_me_delete(undefined, {});
            await auth.logout();
            goto('/');
        } catch (e: unknown) {
            debug.error('ProfileTab', 'handleDeleteAccount failed', e);
            const detail = isAxiosError(e) ? e.response?.data?.detail : null;
            error = detail || (e instanceof Error ? e.message : $_('settings.deleteAccountFailed'));
            deleting = false;
        }
    }

    function closeDeleteModal() {
        showDeleteModal = false;
        deleteConfirmText = '';
    }
</script>

<div class="space-y-6" data-testid="profile-tab">
    <!-- Header with Lock/Unlock + Save/Undo All -->
    <div class="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-slate-700">
        <div>
            <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center">
                <User class="mr-2" size={20}/>
                {$_('settings.profileInfo')}
            </h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">{$_('settings.profileDescription')}</p>
        </div>
        <div class="flex items-center space-x-1">
            {#if !isLocked && hasAnyChanges}
                <button
                    on:click={saveAll}
                    disabled={saving}
                    class="p-2 rounded-lg transition-all bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50"
                    title={$_('common.saveAll')}
                >
                    <Save size={18}/>
                </button>
                <button
                    on:click={undoAll}
                    class="p-2 rounded-lg transition-all bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600"
                    title={$_('common.undoAll')}
                >
                    <Undo size={18}/>
                </button>
            {/if}
            <!-- Edit toggle button -->
            <button
                on:click={toggleLock}
                class="p-2 rounded-lg transition-all {isLocked
                    ? 'bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-slate-600'
                    : 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 hover:bg-amber-200 dark:hover:bg-amber-900/50'}"
                title={isLocked ? $_('settings.enableEditing') : $_('settings.disableEditing')}
            >
                {#if isLocked}
                    <Pencil size={18}/>
                {:else}
                    <PencilOff size={18}/>
                {/if}
            </button>
        </div>
    </div>

    <!-- Status Messages -->
    {#if error}
        <div class="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
            <AlertCircle size={18} />
            <span>{error}</span>
        </div>
    {/if}

    {#if successItems.length > 0}
        <div class="p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg text-green-700 dark:text-green-300 text-sm">
            <div class="flex items-center gap-2 mb-2">
                <CheckCircle size={18} />
                <span class="font-medium">{$_('settings.savedSuccessfully')}:</span>
            </div>
            <ul class="list-disc list-inside ml-6 space-y-0.5">
                {#each successItems as item}
                    <li>{item}</li>
                {/each}
            </ul>
        </div>
    {/if}

    <!-- Account Fields -->
    <div class="space-y-0">
        <!-- Username -->
        <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between py-4 border-b border-gray-100 dark:border-slate-700 gap-3 {usernameModified ? 'bg-amber-50/50 dark:bg-amber-900/10 -mx-4 px-4' : ''}">
            <!-- Left: Label and hint -->
            <div class="flex-1 min-w-0">
                <div class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-200">
                    <User size={16} class="mr-2 text-gray-500 dark:text-gray-400"/>
                    {$_('auth.username')}
                </div>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{$_('settings.usernameHint')}</p>
            </div>

            <!-- Right: Actions + Input -->
            <div class="flex items-center space-x-3 w-full sm:w-auto">
                <!-- Action buttons -->
                {#if !isLocked}
                    <div class="flex items-center space-x-1">
                        {#if usernameModified}
                            <button
                                type="button"
                                on:click={() => saveField('username')}
                                disabled={saving}
                                class="p-1.5 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                                title={$_('common.save')}
                            >
                                <Save size={14}/>
                            </button>
                            <button
                                type="button"
                                on:click={() => undoField('username')}
                                class="p-1.5 bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                                title={$_('common.undo')}
                            >
                                <Undo size={14}/>
                            </button>
                        {/if}
                    </div>
                {/if}

                <!-- Input -->
                <input
                    type="text"
                    bind:value={editedUsername}
                    disabled={saving || isLocked}
                    data-testid="profile-username"
                    class="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700
                           text-gray-900 dark:text-gray-100 text-sm w-full sm:w-auto sm:min-w-[200px] sm:text-right
                           focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-all
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
            </div>
        </div>

        <!-- Email -->
        <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between py-4 border-b border-gray-100 dark:border-slate-700 gap-3 {emailModified ? 'bg-amber-50/50 dark:bg-amber-900/10 -mx-4 px-4' : ''}">
            <!-- Left: Label and hint -->
            <div class="flex-1 min-w-0">
                <div class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-200">
                    <Mail size={16} class="mr-2 text-gray-500 dark:text-gray-400"/>
                    {$_('auth.email')}
                </div>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{$_('settings.emailHint')}</p>
            </div>

            <!-- Right: Actions + Input -->
            <div class="flex items-center space-x-3 w-full sm:w-auto">
                <!-- Action buttons -->
                {#if !isLocked}
                    <div class="flex items-center space-x-1">
                        {#if emailModified}
                            <button
                                type="button"
                                on:click={() => saveField('email')}
                                disabled={saving}
                                class="p-1.5 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                                title={$_('common.save')}
                            >
                                <Save size={14}/>
                            </button>
                            <button
                                type="button"
                                on:click={() => undoField('email')}
                                class="p-1.5 bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
                                title={$_('common.undo')}
                            >
                                <Undo size={14}/>
                            </button>
                        {/if}
                    </div>
                {/if}

                <!-- Input -->
                <input
                    type="email"
                    bind:value={editedEmail}
                    disabled={saving || isLocked}
                    data-testid="profile-email"
                    class="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700
                           text-gray-900 dark:text-gray-100 text-sm w-full sm:w-auto sm:min-w-[200px] sm:text-right
                           focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-all
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
            </div>
        </div>

        <!-- Account Created (readonly) -->
        <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between py-4 gap-2">
            <!-- Left: Label -->
            <div class="flex-1 min-w-0">
                <div class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-200">
                    <Calendar size={16} class="mr-2 text-gray-500 dark:text-gray-400"/>
                    {$_('settings.accountCreated')}
                </div>
            </div>

            <!-- Right: Value -->
            <div class="text-sm text-gray-600 dark:text-gray-300 sm:text-right">
                {formatDate($currentUser?.created_at)}
            </div>
        </div>
    </div>

    <!-- Security Section -->
    <div class="pt-6 border-t border-gray-200 dark:border-slate-700">
        <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-4 flex items-center">
            <Key class="mr-2" size={20}/>
            {$_('settings.security')}
        </h3>

        <div class="space-y-0">
            <!-- Change Password -->
            <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between py-4 border-b border-gray-100 dark:border-slate-700 gap-3">
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$_('settings.changePassword')}</div>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{$_('settings.changePasswordDescription')}</p>
                </div>
                <button
                    on:click={() => showPasswordModal = true}
                    data-testid="change-password-button"
                    class="px-4 py-2 bg-libre-green text-white text-sm rounded-lg hover:bg-libre-green/90 transition-colors w-full sm:w-auto"
                >
                    {$_('settings.changePassword')}
                </button>
            </div>

            <!-- Delete Account -->
            <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between py-4 gap-3">
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-red-600 dark:text-red-400">{$_('settings.deleteAccount')}</div>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{$_('settings.deleteAccountDescription')}</p>
                </div>
                <button
                    on:click={() => showDeleteModal = true}
                    data-testid="delete-account-button"
                    class="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors w-full sm:w-auto"
                >
                    {$_('settings.deleteAccount')}
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Password Change Modal -->
<PasswordChangeModal
    bind:isOpen={showPasswordModal}
    on:close={() => showPasswordModal = false}
/>

<!-- Discard Changes Confirmation -->
{#if showDiscardConfirm}
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_no_noninteractive_element_interactions -->
    <div
        class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        on:click={cancelDiscard}
        on:keydown={(e) => e.key === 'Escape' && cancelDiscard()}
        role="dialog"
        aria-modal="true"
        tabindex="-1"
    >
        <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
        <div
            class="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-sm p-6"
            role="document"
            on:click|stopPropagation
            on:keydown|stopPropagation
        >
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
                {$_('settings.discardChanges')}
            </h2>
            <p class="text-gray-600 dark:text-gray-300 text-sm mb-4">
                {$_('settings.discardChangesWarning')}
            </p>
            <div class="flex justify-end gap-3">
                <button
                    on:click={cancelDiscard}
                    class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                    {$_('settings.continueEditing')}
                </button>
                <button
                    on:click={confirmDiscard}
                    class="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors"
                >
                    {$_('settings.discardAndLock')}
                </button>
            </div>
        </div>
    </div>
{/if}

<!-- Delete Account Confirmation Modal -->
{#if showDeleteModal}
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_label_has_associated_control a11y_no_noninteractive_element_interactions -->
    <div
        class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        on:click={closeDeleteModal}
        on:keydown={(e) => e.key === 'Escape' && closeDeleteModal()}
        role="dialog"
        aria-modal="true"
        tabindex="-1"
    >
        <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
        <div
            class="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-md p-6"
            role="document"
            on:click|stopPropagation
            on:keydown|stopPropagation
        >
            <div class="flex items-center gap-3 mb-4">
                <div class="p-2 bg-red-100 dark:bg-red-900/30 rounded-full">
                    <Trash2 size={24} class="text-red-600 dark:text-red-400" />
                </div>
                <h2 class="text-xl font-semibold text-gray-800 dark:text-gray-100">
                    {$_('settings.deleteAccountConfirm')}
                </h2>
            </div>

            <p class="text-gray-600 dark:text-gray-300 mb-4">
                {$_('settings.deleteAccountWarning')}
            </p>

            <div class="mb-4">
                <label for="delete-confirm-input" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {$_('settings.typeUsernameToConfirm').replace('{username}', $currentUser?.username || '')}
                </label>
                <input
                    id="delete-confirm-input"
                    type="text"
                    bind:value={deleteConfirmText}
                    class="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    placeholder={$currentUser?.username}
                />
            </div>

            <div class="flex justify-end gap-3">
                <button
                    on:click={closeDeleteModal}
                    class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                    {$_('common.cancel')}
                </button>
                <button
                    on:click={handleDeleteAccount}
                    disabled={!canDelete || deleting}
                    class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {#if deleting}
                        {$_('common.deleting')}
                    {:else}
                        {$_('settings.deleteAccountPermanently')}
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}
