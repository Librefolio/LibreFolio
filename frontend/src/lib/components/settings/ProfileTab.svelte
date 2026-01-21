<script lang="ts">
    import {_} from '$lib/i18n';
    import {auth, currentUser} from '$lib/stores/auth';
    import {api} from '$lib/api';
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

    // Password change modal state
    let showPasswordModal = false;

    // Delete account modal state
    let showDeleteModal = false;
    let deleteConfirmText = '';
    let deleting = false;

    // Profile editing state
    let saving = false;
    let error: string | null = null;
    let success: string | null = null;

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
            // Ask to discard changes when locking
            undoAll();
        }
        isLocked = !isLocked;
        debug.log('ProfileTab', 'toggleLock', isLocked);
    }

    // Save individual field
    async function saveField(field: 'username' | 'email') {
        debug.log('ProfileTab', 'saveField', field);
        saving = true;
        error = null;
        success = null;

        try {
            const payload = field === 'username'
                ? { username: editedUsername }
                : { email: editedEmail };

            await api.put<{ user: any; message: string }>('/auth/profile', payload);
            await auth.checkAuth();
            success = $_('settings.profileUpdated');
            setTimeout(() => success = null, 3000);
        } catch (e: any) {
            debug.error('ProfileTab', 'saveField failed', e);
            error = e?.data?.detail || e?.message || $_('settings.updateFailed');
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
        success = null;

        try {
            const payload: Record<string, string> = {};
            if (usernameModified) payload.username = editedUsername;
            if (emailModified) payload.email = editedEmail;

            if (Object.keys(payload).length > 0) {
                await api.put<{ user: any; message: string }>('/auth/profile', payload);
                await auth.checkAuth();
                success = $_('settings.profileUpdated');
                setTimeout(() => success = null, 3000);
            }
        } catch (e: any) {
            debug.error('ProfileTab', 'saveAll failed', e);
            error = e?.data?.detail || e?.message || $_('settings.updateFailed');
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
            await api.delete('/auth/users/me');
            await auth.logout();
            goto('/');
        } catch (e: any) {
            debug.error('ProfileTab', 'handleDeleteAccount failed', e);
            error = e?.data?.detail || e?.message || $_('settings.deleteAccountFailed');
            deleting = false;
        }
    }

    function closeDeleteModal() {
        showDeleteModal = false;
        deleteConfirmText = '';
    }
</script>

<div class="space-y-6">
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

    {#if success}
        <div class="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg text-green-700 dark:text-green-300 text-sm">
            <CheckCircle size={18} />
            <span>{success}</span>
        </div>
    {/if}

    <!-- Account Fields -->
    <div class="space-y-1">
        <!-- Username -->
        <div class="flex items-center justify-between py-3 px-4 rounded-lg transition-colors {usernameModified ? 'bg-amber-50 dark:bg-amber-900/20' : 'hover:bg-gray-50 dark:hover:bg-slate-800/50'}">
            <div class="flex items-center gap-3">
                <User size={18} class="text-gray-400" />
                <div>
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$_('auth.username')}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">{$_('settings.usernameHint')}</div>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <input
                    type="text"
                    bind:value={editedUsername}
                    disabled={saving || isLocked}
                    class="w-48 px-3 py-1.5 text-sm text-right border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-libre-green focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                />
                {#if usernameModified && !isLocked}
                    <button
                        on:click={() => saveField('username')}
                        disabled={saving}
                        class="p-1.5 rounded-lg bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50"
                        title={$_('common.save')}
                    >
                        <Save size={14}/>
                    </button>
                    <button
                        on:click={() => undoField('username')}
                        class="p-1.5 rounded-lg bg-gray-200 dark:bg-slate-600 text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-slate-500"
                        title={$_('common.undo')}
                    >
                        <Undo size={14}/>
                    </button>
                {/if}
            </div>
        </div>

        <!-- Email -->
        <div class="flex items-center justify-between py-3 px-4 rounded-lg transition-colors {emailModified ? 'bg-amber-50 dark:bg-amber-900/20' : 'hover:bg-gray-50 dark:hover:bg-slate-800/50'}">
            <div class="flex items-center gap-3">
                <Mail size={18} class="text-gray-400" />
                <div>
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$_('auth.email')}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">{$_('settings.emailHint')}</div>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <input
                    type="email"
                    bind:value={editedEmail}
                    disabled={saving || isLocked}
                    class="w-48 px-3 py-1.5 text-sm text-right border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-libre-green focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                />
                {#if emailModified && !isLocked}
                    <button
                        on:click={() => saveField('email')}
                        disabled={saving}
                        class="p-1.5 rounded-lg bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50"
                        title={$_('common.save')}
                    >
                        <Save size={14}/>
                    </button>
                    <button
                        on:click={() => undoField('email')}
                        class="p-1.5 rounded-lg bg-gray-200 dark:bg-slate-600 text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-slate-500"
                        title={$_('common.undo')}
                    >
                        <Undo size={14}/>
                    </button>
                {/if}
            </div>
        </div>

        <!-- Account Created (readonly) -->
        <div class="flex items-center justify-between py-3 px-4">
            <div class="flex items-center gap-3">
                <Calendar size={18} class="text-gray-400" />
                <div>
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$_('settings.accountCreated')}</div>
                </div>
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-300">
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

        <div class="space-y-1">
            <!-- Change Password -->
            <div class="flex items-center justify-between py-3 px-4 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors">
                <div>
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$_('settings.changePassword')}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">{$_('settings.changePasswordDescription')}</div>
                </div>
                <button
                    on:click={() => showPasswordModal = true}
                    class="px-4 py-2 bg-libre-green text-white text-sm rounded-lg hover:bg-libre-green/90 transition-colors"
                >
                    {$_('settings.changePassword')}
                </button>
            </div>

            <!-- Delete Account -->
            <div class="flex items-center justify-between py-3 px-4 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors">
                <div>
                    <div class="text-sm font-medium text-red-600 dark:text-red-400">{$_('settings.deleteAccount')}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">{$_('settings.deleteAccountDescription')}</div>
                </div>
                <button
                    on:click={() => showDeleteModal = true}
                    class="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors"
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
