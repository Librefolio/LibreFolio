<script lang="ts">
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {_} from '$lib/i18n';
    import {auth, currentUser} from '$lib/stores/app/auth';
    import {userSettings} from '$lib/stores/app/settings';
    import {zodiosApi} from '$lib/api';
    import {isAxiosError} from 'axios';
    import {goto} from '$app/navigation';
    import {debug} from '$lib/debug';
    import {Calendar, Camera, Key, Mail, Pencil, PencilOff, Save, Undo, User} from 'lucide-svelte';
    import PasswordChangeModal from '$lib/features/settings/PasswordChangeModal.svelte';
    import AccountDeletionDialog from '$lib/features/settings/AccountDeletionDialog.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {ImagePickerWrapper} from '$lib/components/ui/media';
    import {onMount} from 'svelte';
    import {uiLocaleStore} from '$lib/stores/app/uiLocale';
    import {sameEmail} from '$lib/features/auth/emailCase';

    // Format date for display, in the interface locale (M-18). The template passes it: read there, the
    // store is tracked, and the date follows a language change.
    function formatDate(dateStr: string | undefined, locale: string): string {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString(locale, {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
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

    // Avatar state
    let originalAvatarUrl: string | null = null;
    let editedAvatarUrl: string | null = null;
    let showAvatarPicker = false;

    // Load avatar URL from settings on mount
    onMount(async () => {
        try {
            const settings = await zodiosApi.get_user_settings_endpoint_api_v1_settings_user_get();
            // avatar_url comes from API - extract string if present
            const avatarValue = settings.avatar_url;
            originalAvatarUrl = typeof avatarValue === 'string' ? avatarValue : null;
            editedAvatarUrl = originalAvatarUrl;
        } catch (e) {
            debug.error('ProfileTab', 'Failed to load avatar', e);
        }
    });

    // Profile editing state
    let saving = false;
    let error: string | null = null;
    /** The code of a refusal the tab words itself (A6e), published on profile-error as data-error-code. */
    let errorCode: string | null = null;
    /** The current password, asked only while the email is changed (A6e). */
    let emailPassword = '';

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
    // P18: the same address in other A–Z capitals is no change of address — saved as typed, with no password and
    // nobody signed out. Only a real change asks for the current password (A6e).
    $: emailChangesAddress = emailModified && !sameEmail(editedEmail, originalEmail);
    // The password belongs to the change it was typed for: back to the stored address, in any capitals, it is gone.
    $: if (!emailChangesAddress) emailPassword = '';
    $: emailNeedsPassword = emailChangesAddress && emailPassword === '';
    $: avatarModified = editedAvatarUrl !== originalAvatarUrl;
    $: hasAnyChanges = usernameModified || emailModified || avatarModified;

    // Check if delete confirmation matches username

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

    /** Refusals of an email change the tab words itself (A6e); any other code reads as a failed update. */
    const PASSWORD_REFUSALS: Record<string, string> = {
        CURRENT_PASSWORD_INVALID: 'settings.currentPasswordIncorrect',
        CURRENT_PASSWORD_REQUIRED: 'settings.currentPasswordRequired',
        // The server's limit on failed passwords (A8a)
        TOO_MANY_ATTEMPTS: 'settings.tooManyPasswordAttempts',
    };

    /** A refusal as the tab shows it: a known code in words (with the code), the server's sentence, or a generic text. */
    function describeRefusal(e: unknown): {code: string | null; text: string} {
        const detail: unknown = isAxiosError(e) ? e.response?.data?.detail : null;
        if (typeof detail === 'string' && detail) return {code: null, text: detail};
        if (detail && typeof detail === 'object') {
            const code = (detail as {error_code?: unknown}).error_code;
            if (typeof code === 'string' && Object.hasOwn(PASSWORD_REFUSALS, code)) return {code, text: $_(PASSWORD_REFUSALS[code])};
            return {code: null, text: $_('settings.updateFailed')};
        }
        return {code: null, text: e instanceof Error ? e.message : $_('settings.updateFailed')};
    }

    function clearError() {
        error = null;
        errorCode = null;
    }

    /** The body of an email save: the current password only when the address itself changes (A6e, P18). */
    function emailPayload(): {email: string; current_password?: string} {
        return emailChangesAddress ? {email: editedEmail, current_password: emailPassword} : {email: editedEmail};
    }

    // Save individual field
    async function saveField(field: 'username' | 'email') {
        debug.log('ProfileTab', 'saveField', field);
        saving = true;
        error = null;
        errorCode = null;

        try {
            const payload = field === 'username' ? {username: editedUsername} : emailPayload();

            await zodiosApi.update_profile_api_v1_auth_profile_put(payload);
            await auth.checkAuth();

            const fieldName = field === 'username' ? $_('auth.username') : $_('auth.email');
            notify({
                name: 'settings.profile.saved',
                detail: {fields: 1, field: fieldName},
                toast: {variant: 'success', message: `${$_('settings.savedSuccessfully')}:<ul class="mt-1 list-inside list-disc">${[fieldName].map((l) => `<li>${escapeHtml(l)}</li>`).join('')}</ul>`},
            });
        } catch (e: unknown) {
            debug.error('ProfileTab', 'saveField failed', e);
            const refusal = describeRefusal(e);
            error = refusal.text;
            errorCode = refusal.code;
            if (field === 'username') editedUsername = originalUsername;
            // A wrong or missing password keeps the address typed, to try again; the password goes. Too many failures
            // keep both (A8b, C11): the password may be right, and waiting is all there is to do.
            else if (refusal.code && refusal.code !== 'TOO_MANY_ATTEMPTS') emailPassword = '';
            else if (!refusal.code) editedEmail = originalEmail;
            setTimeout(clearError, 5000);
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
        errorCode = null;

        const fields: ('username' | 'email')[] = [];
        if (usernameModified) fields.push('username');
        if (emailModified) fields.push('email');

        const saved: {field: 'username' | 'email'; label: string}[] = [];
        const failed: {field: 'username' | 'email'; label: string; reason: string; code: string | null}[] = [];

        for (const field of fields) {
            try {
                const payload = field === 'username' ? {username: editedUsername} : emailPayload();
                await zodiosApi.update_profile_api_v1_auth_profile_put(payload);
                saved.push({field, label: field === 'username' ? $_('auth.username') : $_('auth.email')});
                if (field === 'username') originalUsername = editedUsername;
                else originalEmail = editedEmail;
            } catch (e: unknown) {
                debug.error('ProfileTab', 'saveAll field failed', e);
                const refusal = describeRefusal(e);
                failed.push({
                    field,
                    label: field === 'username' ? $_('auth.username') : $_('auth.email'),
                    reason: refusal.text,
                    code: refusal.code,
                });
                if (field === 'username') editedUsername = originalUsername;
                else if (refusal.code && refusal.code !== 'TOO_MANY_ATTEMPTS') emailPassword = '';
                else if (!refusal.code) editedEmail = originalEmail;
            }
        }

        if (saved.length > 0) {
            await auth.checkAuth();
        }

        if (failed.length > 0) {
            error = failed.map((f) => `${f.label}: ${f.reason}`).join('\n');
            errorCode = failed.find((f) => f.code)?.code ?? null;
            setTimeout(clearError, 5000);
        }

        if (saved.length > 0 || failed.length > 0) {
            const savedList = saved.map((s) => `<li>${s.label}</li>`).join('');
            const failedList = failed.map((f) => `<li>${f.label}</li>`).join('');
            const message =
                failed.length === 0
                    ? `${$_('settings.savedSuccessfully')}:<ul class="mt-1 list-inside list-disc">${savedList}</ul>`
                    : `${$_(saved.length === 0 ? 'settings.profileSaveFailed' : 'settings.profileSavePartial')}:<div class="mt-1">${$_('settings.savedFields')}</div><ul class="list-inside list-disc">${savedList}</ul><div class="mt-1">${$_('settings.failedFields')}</div><ul class="list-inside list-disc">${failedList}</ul>`;
            notify({
                name: failed.length === 0 ? 'settings.profile.saved' : saved.length === 0 ? 'settings.profile.save.failed' : 'settings.profile.save.partial',
                detail: {
                    fields: saved.length,
                    saved: saved.map((s) => s.field),
                    failed: failed.map((f) => f.field),
                    reasons: Object.fromEntries(failed.map((f) => [f.field, f.reason])),
                },
                toast: {variant: failed.length === 0 ? 'success' : saved.length === 0 ? 'error' : 'warning', message},
            });
        }

        saving = false;
    }

    // Undo all changes
    function undoAll() {
        debug.log('ProfileTab', 'undoAll');
        editedUsername = originalUsername;
        editedEmail = originalEmail;
        editedAvatarUrl = originalAvatarUrl;
    }

    // Avatar change handler (from ImagePickerWrapper)
    async function handleAvatarChange(url: string) {
        showAvatarPicker = false;
        editedAvatarUrl = url;
        await saveAvatarField();
    }

    async function saveAvatarField() {
        saving = true;
        error = null;

        try {
            await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({avatar_url: editedAvatarUrl});
            await auth.checkAuth();
            originalAvatarUrl = editedAvatarUrl;
            // Update userSettings store so Sidebar and other components get the new avatar
            const currentSettings = userSettings.get();
            if (currentSettings) {
                userSettings.setDirect({
                    ...currentSettings,
                    avatar_url: editedAvatarUrl,
                });
            }
            notify({
                name: 'settings.profile.avatar.saved',
                detail: {},
                toast: {variant: 'success', message: `${$_('settings.savedSuccessfully')}:<ul class="mt-1 list-inside list-disc">${[$_('common.avatar')].map((l) => `<li>${l}</li>`).join('')}</ul>`},
            });
        } catch (e: unknown) {
            debug.error('ProfileTab', 'saveAvatarField failed', e);
            const detail = isAxiosError(e) ? e.response?.data?.detail : null;
            error = detail || (e instanceof Error ? e.message : $_('settings.updateFailed'));
            editedAvatarUrl = originalAvatarUrl;
            setTimeout(() => (error = null), 5000);
        } finally {
            saving = false;
        }
    }

    // The dialog deleted the account: its session is gone, back to the start page
    async function handleAccountDeleted() {
        debug.log('ProfileTab', 'account deleted');
        await auth.logout();
        goto('/');
    }

    function closeDeleteModal() {
        showDeleteModal = false;
    }
</script>

<div class="space-y-6 text-lf-primary" data-testid="profile-tab" data-busy={saving ? 'true' : 'false'} aria-busy={saving}>
    <!-- Header with Lock/Unlock + Save/Undo All -->
    <div class="flex items-center justify-between pb-4 border-b border-lf-subtle">
        <div>
            <h3 class="text-lg font-semibold text-lf-primary flex items-center">
                <User class="mr-2" size={20} />
                {$_('settings.profileInfo')}
            </h3>
            <p class="text-sm text-lf-muted">{$_('settings.profileDescription')}</p>
        </div>
        <div class="flex items-center space-x-1">
            {#if !isLocked && hasAnyChanges}
                <button on:click={saveAll} disabled={saving || emailNeedsPassword} class="p-2 rounded-lg transition-all bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50" title={$_('common.saveAll')} data-testid="profile-save-all">
                    <Save size={18} />
                </button>
                <button on:click={undoAll} class="p-2 rounded-lg transition-all bg-lf-panel text-lf-secondary hover:bg-lf-neutral" title={$_('common.undoAll')} data-testid="profile-undo-all">
                    <Undo size={18} />
                </button>
            {/if}
            <!-- Edit toggle button -->
            <button
                class="p-2 rounded-lg transition-all {isLocked ? 'bg-lf-panel text-lf-muted hover:bg-lf-neutral' : 'bg-lf-warning-soft text-lf-warning hover:bg-lf-warning-line'}"
                data-testid="profile-edit-toggle"
                on:click={toggleLock}
                title={isLocked ? $_('settings.enableEditing') : $_('settings.disableEditing')}
            >
                {#if isLocked}
                    <Pencil size={18} />
                {:else}
                    <PencilOff size={18} />
                {/if}
            </button>
        </div>
    </div>

    <!-- Status Messages -->
    {#if error}
        <div data-error-code={errorCode ?? ''} data-testid="profile-error">
            <InfoBanner variant="error">
                <span class="text-sm">{error}</span>
            </InfoBanner>
        </div>
    {/if}

    <!-- Avatar Section -->
    <div class="flex items-center gap-4 pb-4 border-b border-lf-subtle" data-testid="profile-avatar">
        <!-- Avatar Preview -->
        <div class="relative group">
            {#if editedAvatarUrl}
                <img src={editedAvatarUrl} alt="Avatar" class="w-20 h-20 rounded-full object-cover border-2 border-lf-subtle" />
            {:else}
                <div class="w-20 h-20 rounded-full bg-lf-neutral flex items-center justify-center">
                    <User size={32} class="text-lf-muted" />
                </div>
            {/if}
            <!-- Upload overlay (only when not locked) - opens AssetPickerModal -->
            {#if !isLocked}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div class="absolute inset-0 rounded-full bg-lf-overlay opacity-0 group-hover:opacity-100 flex items-center justify-center cursor-pointer transition-opacity" on:click={() => (showAvatarPicker = true)} data-testid="profile-avatar-trigger">
                    <Camera size={20} class="text-lf-on-overlay" />
                </div>
            {/if}
        </div>
        <!-- Avatar Info -->
        <div class="flex-1">
            <h4 class="font-medium text-lf-primary">{$_('common.avatar')}</h4>
            <p class="text-sm text-lf-muted">{$_('settings.avatarHint')}</p>
        </div>
    </div>

    <!-- Account Fields -->
    <div class="space-y-0">
        <!-- Username -->
        <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between py-4 border-b border-lf-subtle gap-3 {usernameModified ? 'bg-lf-warning-soft/50 -mx-4 px-4' : ''}">
            <!-- Left: Label, hint and action buttons on mobile -->
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between min-h-[28px]">
                    <div class="flex items-center text-sm font-medium text-lf-secondary">
                        <User class="mr-2 text-lf-muted" size={16} />
                        {$_('auth.username')}
                    </div>
                    <!-- Action buttons - next to label on mobile, hidden on desktop -->
                    {#if !isLocked && usernameModified}
                        <div class="flex items-center space-x-1 sm:hidden">
                            <button type="button" on:click={() => saveField('username')} disabled={saving} class="p-1.5 bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors disabled:opacity-50" title={$_('common.save')}>
                                <Save size={14} />
                            </button>
                            <button type="button" on:click={() => undoField('username')} class="p-1.5 bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-colors" title={$_('common.undo')}>
                                <Undo size={14} />
                            </button>
                        </div>
                    {/if}
                </div>
                <p class="text-xs text-lf-muted mt-1">{$_('settings.usernameHint')}</p>
            </div>

            <!-- Right: Actions (desktop only) + Input -->
            <div class="flex items-center space-x-3 w-full sm:w-auto">
                <!-- Action buttons - desktop only -->
                {#if !isLocked}
                    <div class="hidden sm:flex items-center space-x-1">
                        {#if usernameModified}
                            <button type="button" on:click={() => saveField('username')} disabled={saving} class="p-1.5 bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors disabled:opacity-50" title={$_('common.save')}>
                                <Save size={14} />
                            </button>
                            <button type="button" on:click={() => undoField('username')} class="p-1.5 bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-colors" title={$_('common.undo')}>
                                <Undo size={14} />
                            </button>
                        {/if}
                    </div>
                {/if}

                <!-- Input -->
                <input
                    bind:value={editedUsername}
                    class="px-3 py-2 border border-lf-input rounded-lg bg-lf-field
                           text-lf-primary hover:border-lf-input-hover text-sm w-full sm:w-auto sm:min-w-[200px] sm:text-right
                           focus:ring-2 focus:ring-lf-focus focus:border-lf-focus transition-all
                           disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="profile-username"
                    disabled={saving || isLocked}
                    type="text"
                />
            </div>
        </div>

        <!-- Email -->
        <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between py-4 border-b border-lf-subtle gap-3 {emailModified ? 'bg-lf-warning-soft/50 -mx-4 px-4' : ''}">
            <!-- Left: Label, hint and action buttons on mobile -->
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between min-h-[28px]">
                    <div class="flex items-center text-sm font-medium text-lf-secondary">
                        <Mail class="mr-2 text-lf-muted" size={16} />
                        {$_('auth.email')}
                    </div>
                    <!-- Action buttons - next to label on mobile, hidden on desktop -->
                    {#if !isLocked && emailModified}
                        <div class="flex items-center space-x-1 sm:hidden">
                            <button type="button" on:click={() => saveField('email')} disabled={saving || emailNeedsPassword} class="p-1.5 bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors disabled:opacity-50" title={$_('common.save')}>
                                <Save size={14} />
                            </button>
                            <button type="button" on:click={() => undoField('email')} class="p-1.5 bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-colors" title={$_('common.undo')}>
                                <Undo size={14} />
                            </button>
                        </div>
                    {/if}
                </div>
                <p class="text-xs text-lf-muted mt-1">{$_('settings.emailHint')}</p>
                {#if !isLocked && emailChangesAddress}
                    <!-- A6e: the current password, for a change of address only (P18: not for other capitals); the change signs the other devices out. -->
                    <div class="mt-3 space-y-1">
                        <label class="sr-only" for="profile-current-password">{$_('settings.currentPassword')}</label>
                        <input
                            bind:value={emailPassword}
                            aria-describedby="profile-email-password-hint"
                            autocomplete="current-password"
                            class="px-3 py-2 border border-lf-input rounded-lg bg-lf-field text-lf-primary placeholder:text-lf-placeholder text-sm w-full sm:max-w-xs focus:ring-2 focus:ring-lf-focus focus:border-lf-focus transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            data-testid="profile-email-password"
                            disabled={saving}
                            id="profile-current-password"
                            name="current-password"
                            placeholder={$_('settings.currentPassword')}
                            type="password"
                        />
                        <p class="text-xs text-lf-muted" data-testid="profile-email-password-hint" id="profile-email-password-hint">{$_('settings.emailPasswordHint')}</p>
                    </div>
                {/if}
            </div>

            <!-- Right: Actions (desktop only) + Input -->
            <div class="flex items-center space-x-3 w-full sm:w-auto">
                <!-- Action buttons - desktop only -->
                {#if !isLocked}
                    <div class="hidden sm:flex items-center space-x-1">
                        {#if emailModified}
                            <button type="button" on:click={() => saveField('email')} disabled={saving || emailNeedsPassword} class="p-1.5 bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors disabled:opacity-50" title={$_('common.save')}>
                                <Save size={14} />
                            </button>
                            <button type="button" on:click={() => undoField('email')} class="p-1.5 bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-colors" title={$_('common.undo')}>
                                <Undo size={14} />
                            </button>
                        {/if}
                    </div>
                {/if}

                <!-- Input -->
                <input
                    bind:value={editedEmail}
                    class="px-3 py-2 border border-lf-input rounded-lg bg-lf-field
                           text-lf-primary hover:border-lf-input-hover text-sm w-full sm:w-auto sm:min-w-[200px] sm:text-right
                           focus:ring-2 focus:ring-lf-focus focus:border-lf-focus transition-all
                           disabled:opacity-50 disabled:cursor-not-allowed"
                    data-testid="profile-email"
                    disabled={saving || isLocked}
                    type="email"
                />
            </div>
        </div>

        <!-- Account Created (readonly) -->
        <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between py-4 gap-2">
            <!-- Left: Label -->
            <div class="flex-1 min-w-0">
                <div class="flex items-center text-sm font-medium text-lf-secondary">
                    <Calendar class="mr-2 text-lf-muted" size={16} />
                    {$_('settings.accountCreated')}
                </div>
            </div>

            <!-- Right: Value -->
            <div class="text-sm text-lf-secondary sm:text-right">
                {formatDate($currentUser?.created_at, $uiLocaleStore)}
            </div>
        </div>
    </div>

    <!-- Security Section -->
    <div class="pt-6 border-t border-lf-subtle">
        <h3 class="text-lg font-semibold text-lf-secondary mb-4 flex items-center">
            <Key class="mr-2" size={20} />
            {$_('settings.security')}
        </h3>

        <div class="space-y-0">
            <!-- Change Password -->
            <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between py-4 border-b border-lf-subtle gap-3">
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-lf-secondary">{$_('settings.changePassword')}</div>
                    <p class="text-xs text-lf-muted mt-1">{$_('settings.changePasswordDescription')}</p>
                </div>
                <button class="px-4 py-2 bg-lf-action text-lf-on-action text-sm rounded-lg hover:bg-lf-action-hover transition-colors w-full sm:w-auto" data-testid="change-password-button" on:click={() => (showPasswordModal = true)}>
                    {$_('settings.changePassword')}
                </button>
            </div>

            <!-- Delete Account -->
            <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between py-4 gap-3">
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-lf-danger">{$_('settings.deleteAccount')}</div>
                    <p class="text-xs text-lf-muted mt-1">{$_('settings.deleteAccountDescription')}</p>
                </div>
                <button class="px-4 py-2 bg-lf-danger-solid text-lf-on-danger-solid text-sm rounded-lg hover:bg-lf-danger-hover transition-colors w-full sm:w-auto" data-testid="delete-account-button" on:click={() => (showDeleteModal = true)}>
                    {$_('settings.deleteAccount')}
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Password Change Modal -->
<PasswordChangeModal bind:isOpen={showPasswordModal} on:close={() => (showPasswordModal = false)} />

<!-- Discard Changes Confirmation -->
{#if showDiscardConfirm}
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_no_noninteractive_element_interactions -->
    <div class="fixed inset-0 bg-lf-overlay z-50 flex items-center justify-center p-4" on:click={cancelDiscard} on:keydown={(e) => e.key === 'Escape' && cancelDiscard()} role="dialog" data-testid="profile-discard-dialog" aria-modal="true" tabindex="-1">
        <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
        <div class="bg-lf-card text-lf-primary border border-lf-raised rounded-2xl shadow-xl shadow-lf-shadow w-full max-w-sm p-6" role="document" on:click|stopPropagation on:keydown|stopPropagation>
            <h2 class="text-lg font-semibold text-lf-primary mb-2">
                {$_('common.discardChanges')}
            </h2>
            <p class="text-lf-secondary text-sm mb-4">
                {$_('settings.discardChangesWarning')}
            </p>
            <div class="flex justify-end gap-3">
                <button on:click={cancelDiscard} class="px-4 py-2 text-lf-secondary hover:bg-lf-hover rounded-lg transition-colors">
                    {$_('common.continueEditing')}
                </button>
                <button on:click={confirmDiscard} class="px-4 py-2 bg-lf-warning text-lf-on-status rounded-lg hover:bg-lf-warning-hover transition-colors">
                    {$_('settings.discardAndLock')}
                </button>
            </div>
        </div>
    </div>
{/if}

<!-- Delete Account: what the deletion would take, then the username typed (AccountDeletionDialog, shared with the Users tab) -->
{#if showDeleteModal && $currentUser}
    <AccountDeletionDialog account={{id: $currentUser.id, username: $currentUser.username, is_active: true}} mode="self" onClose={closeDeleteModal} onDeleted={handleAccountDeleted} open testIdPrefix="profile-delete" />
{/if}

<!-- Avatar Image Picker (AssetPicker + ImageEditModal combined) -->
<ImagePickerWrapper circularPreview={true} filterImages={true} initialUrl={editedAvatarUrl || ''} oncancel={() => (showAvatarPicker = false)} onchange={handleAvatarChange} open={showAvatarPicker} preset="avatar" title={$_('settings.selectAvatar') || 'Select Avatar'} />
