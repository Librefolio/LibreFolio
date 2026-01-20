ni<script lang="ts">
    import {_} from '$lib/i18n';
    import {currentUser} from '$lib/stores/auth';
    import {Calendar, Key, Mail, User} from 'lucide-svelte';
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

    // Password change modal state
    let showPasswordModal = false;
</script>

<div class="space-y-6">
    <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-200">{$_('settings.profileInfo')}</h3>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Username -->
        <div class="space-y-2">
            <label class="flex items-center text-sm font-medium text-gray-600 dark:text-gray-400">
                <User class="mr-2" size={16}/>
                {$_('auth.username')}
            </label>
            <div class="px-4 py-3 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-700 dark:text-gray-200">
                {$currentUser?.username || '-'}
            </div>
        </div>

        <!-- Email -->
        <div class="space-y-2">
            <label class="flex items-center text-sm font-medium text-gray-600 dark:text-gray-400">
                <Mail class="mr-2" size={16}/>
                {$_('auth.email')}
            </label>
            <div class="px-4 py-3 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-700 dark:text-gray-200">
                {$currentUser?.email || '-'}
            </div>
        </div>

        <!-- Account Created -->
        <div class="space-y-2">
            <label class="flex items-center text-sm font-medium text-gray-600 dark:text-gray-400">
                <Calendar class="mr-2" size={16}/>
                {$_('settings.accountCreated')}
            </label>
            <div class="px-4 py-3 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg text-gray-700 dark:text-gray-200">
                {formatDate($currentUser?.created_at)}
            </div>
        </div>
    </div>

    <!-- Security Section -->
    <div class="mt-8 pt-6 border-t border-gray-200 dark:border-slate-700">
        <div class="flex items-center justify-between">
            <div>
                <h4 class="text-md font-medium text-gray-700 dark:text-gray-200 flex items-center">
                    <Key class="mr-2" size={18}/>
                    {$_('settings.security')}
                </h4>
                <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{$_('settings.changePasswordDescription')}</p>
            </div>
            <button
                on:click={() => showPasswordModal = true}
                class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
            >
                {$_('settings.changePassword')}
            </button>
        </div>
    </div>
</div>

<!-- Password Change Modal -->
<PasswordChangeModal
    bind:isOpen={showPasswordModal}
    on:close={() => showPasswordModal = false}
/>
