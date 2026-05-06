<!--
  BrokerSharingModal - Modal for managing broker access sharing

  Features:
  - Half-donut ECharts pie chart showing OWNER share distribution
  - Add/edit/remove users with role and share percentage
  - Batch save: all changes local until "Save" is clicked
  - Warning banner when total ownership exceeds 100%
  - Search users with debounce + exclude already-added
  - Dark mode support
  - Uses ModalBase for consistent modal behavior
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {saveWithRetry} from '$lib/utils/saveWithRetry';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import {Check, ChevronDown, Crown, Eye, Loader2, Pencil, Plus, RotateCcw, Save, Search, Trash2, Users, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import {getRoleIcon as _getRoleIcon, getRoleIconColor as _getRoleIconColor, getRoleShortLabel as _getRoleShortLabel} from '$lib/utils/brokerRoleHelpers';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import LazyImage from '$lib/components/ui/media/LazyImage.svelte';
    import SemiDonutChart from '$lib/components/charts/SemiDonutChart.svelte';

    // =========================================================================
    // Props
    // =========================================================================
    export let open: boolean = false;
    export let brokerId: number;
    export let brokerName: string = '';
    export let onClose: () => void = () => {};
    export let onChanged: (() => void) | undefined = undefined;

    // =========================================================================
    // Types
    // =========================================================================
    interface AccessEntry {
        user_id: number;
        username: string;
        avatar_url: string | null;
        role: 'OWNER' | 'EDITOR' | 'VIEWER';
        share_percentage: number; // 0-1 fraction (display as %)
        isNew?: boolean;
    }

    interface SearchUser {
        id: number;
        username: string;
        avatar_url: string | null;
    }

    // =========================================================================
    // State
    // =========================================================================
    let accesses: AccessEntry[] = [];
    let originalAccesses: AccessEntry[] = [];
    let loading = true;
    let saving = false;
    let error: string | null = null;

    // Add user state
    let showAddModal = false; // Add User as overlay modal
    let searchQuery = '';
    let searchResults: SearchUser[] = [];
    let searching = false;
    let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
    let selectedUser: SearchUser | null = null;
    let newRole: 'OWNER' | 'EDITOR' | 'VIEWER' = 'VIEWER';
    let newSharePercent: number = 0;
    let showRoleDropdown = false;
    let searchHighlightIndex = -1; // Arrow key navigation index

    // Edit state
    let showEditModal = false;
    let editingUserId: number | null = null;
    let editRole: 'OWNER' | 'EDITOR' | 'VIEWER' = 'VIEWER';
    let editSharePercent: number = 0;
    let showEditRoleDropdown = false;

    // Confirm dialogs
    let confirmRemoveOpen = false;
    let confirmRemoveUsername = '';
    let confirmRemoveUserId: number | null = null;
    let confirmCloseOpen = false;

    // =========================================================================
    // Computed
    // =========================================================================
    $: owners = accesses.filter((a) => a.role === 'OWNER');
    $: editors = accesses.filter((a) => a.role === 'EDITOR');
    $: viewers = accesses.filter((a) => a.role === 'VIEWER');
    $: totalAllocated = owners.reduce((sum, o) => sum + o.share_percentage, 0);
    $: totalAllocatedPercent = Math.round(totalAllocated * 10000) / 100;
    $: availablePercent = Math.round((1 - totalAllocated) * 10000) / 100;
    $: exceedsLimit = totalAllocated > 1.0001; // small epsilon for floating point
    $: hasChanges =
        JSON.stringify(
            accesses.map((a) => ({
                user_id: a.user_id,
                role: a.role,
                share_percentage: a.share_percentage,
            })),
        ) !==
        JSON.stringify(
            originalAccesses.map((a) => ({
                user_id: a.user_id,
                role: a.role,
                share_percentage: a.share_percentage,
            })),
        );
    $: existingUserIds = new Set(accesses.map((a) => a.user_id));

    // For add form: max share available
    $: maxNewShare = newRole === 'OWNER' ? Math.max(0, Math.round((1 - totalAllocated) * 10000) / 100) : 0;

    // =========================================================================
    // Lifecycle
    // =========================================================================
    $: if (open) {
        loadAccesses();
    }

    // =========================================================================
    // Derived: chart data for SemiDonutChart
    // =========================================================================
    $: chartSlices = owners
        .filter((o) => Math.round(o.share_percentage * 10000) / 100 > 0)
        .map((o) => ({
            name: o.username,
            percentage: Math.round(o.share_percentage * 10000) / 100,
            avatarUrl: o.avatar_url ? `${o.avatar_url}?img_preview=64x64` : null,
        }));

    // =========================================================================
    // Data Loading
    // =========================================================================
    async function loadAccesses() {
        loading = true;
        error = null;
        showAddModal = false;
        editingUserId = null;

        try {
            const response = await zodiosApi.list_broker_access_api_v1_brokers__broker_id__access_get({
                params: {broker_id: brokerId},
            });
            const items = (response as any).items || [];
            accesses = items.map((item: any) => ({
                user_id: item.user_id,
                username: item.username,
                avatar_url: typeof item.avatar_url === 'string' ? item.avatar_url : null,
                role: item.role as 'OWNER' | 'EDITOR' | 'VIEWER',
                share_percentage: parseFloat(String(item.share_percentage)) || 0,
            }));
            originalAccesses = JSON.parse(JSON.stringify(accesses));
        } catch (e: any) {
            error = e?.message || 'Failed to load access list';
        } finally {
            loading = false;
        }
    }

    // =========================================================================
    // User Search (debounced)
    // =========================================================================
    function handleSearchInput() {
        if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
        searchResults = [];
        searchHighlightIndex = -1;

        if (searchQuery.length < 2) {
            searching = false;
            return;
        }

        searching = true;
        searchDebounceTimer = setTimeout(async () => {
            try {
                const response = await zodiosApi.search_users_endpoint_api_v1_users_search_get({
                    queries: {q: searchQuery, exclude_broker_id: brokerId},
                });
                const items = (response as any).items || [];
                // Also exclude users already in local accesses
                searchResults = items
                    .filter((u: any) => !existingUserIds.has(u.id))
                    .map((u: any) => ({
                        id: u.id,
                        username: u.username,
                        avatar_url: typeof u.avatar_url === 'string' ? u.avatar_url : null,
                    }));
                searchHighlightIndex = -1;
            } catch {
                searchResults = [];
            } finally {
                searching = false;
            }
        }, 300);
    }

    function handleSearchKeydown(e: KeyboardEvent) {
        if (searchResults.length === 0) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            searchHighlightIndex = Math.min(searchHighlightIndex + 1, searchResults.length - 1);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            searchHighlightIndex = Math.max(searchHighlightIndex - 1, 0);
        } else if (e.key === 'Enter' && searchHighlightIndex >= 0) {
            e.preventDefault();
            selectSearchUser(searchResults[searchHighlightIndex]);
        }
    }

    function selectSearchUser(user: SearchUser) {
        selectedUser = user;
        searchQuery = user.username;
        searchResults = [];
    }

    // =========================================================================
    // Add User (local)
    // =========================================================================
    function handleAddUser() {
        if (!selectedUser) return;

        const shareVal = newRole === 'OWNER' ? Math.min(newSharePercent, maxNewShare) / 100 : 0;

        accesses = [
            ...accesses,
            {
                user_id: selectedUser.id,
                username: selectedUser.username,
                avatar_url: selectedUser.avatar_url,
                role: newRole,
                share_percentage: shareVal,
                isNew: true,
            },
        ];

        // Reset form
        selectedUser = null;
        searchQuery = '';
        newRole = 'VIEWER';
        newSharePercent = 0;
        showAddModal = false;
        searchHighlightIndex = -1;
    }

    // =========================================================================
    // Edit User (local)
    // =========================================================================
    function startEdit(entry: AccessEntry) {
        editingUserId = entry.user_id;
        editRole = entry.role;
        editSharePercent = Math.round(entry.share_percentage * 10000) / 100;
        showEditRoleDropdown = false;
        showEditModal = true;
    }

    function saveEdit() {
        if (editingUserId === null) return;

        accesses = accesses.map((a) => {
            if (a.user_id !== editingUserId) return a;
            const share = editRole === 'OWNER' ? editSharePercent / 100 : 0;
            return {...a, role: editRole, share_percentage: share};
        });
        editingUserId = null;
        showEditModal = false;
    }

    function cancelEdit() {
        editingUserId = null;
        showEditModal = false;
    }

    // =========================================================================
    // Remove User (local with confirm)
    // =========================================================================
    function requestRemove(entry: AccessEntry) {
        // Check: cannot remove last OWNER
        if (entry.role === 'OWNER' && owners.length <= 1) {
            error = $_('brokers.sharing.lastOwnerWarning');
            return;
        }
        confirmRemoveUserId = entry.user_id;
        confirmRemoveUsername = entry.username;
        confirmRemoveOpen = true;
    }

    function confirmRemove() {
        if (confirmRemoveUserId === null) return;
        accesses = accesses.filter((a) => a.user_id !== confirmRemoveUserId);
        confirmRemoveOpen = false;
        confirmRemoveUserId = null;
    }

    // =========================================================================
    // Save (batch PUT)
    // =========================================================================
    async function handleSave() {
        saving = true;
        error = null;

        const body = accesses.map((a) => ({
            user_id: a.user_id,
            role: a.role,
            share_percentage: a.share_percentage,
        }));

        // I-bis #22 (Batch 4.d-part2) — unified error extraction.
        // #R6-8 (Batch 4.d-part3) — success now emits a toast and closes the
        // modal (consistent with the evolved app-wide save pattern). Only the
        // error path keeps the inline banner (persistent, dismissible).
        const result = await saveWithRetry(() => zodiosApi.bulk_update_broker_access_api_v1_brokers__broker_id__access_put(body, {params: {broker_id: brokerId}}), {toast: false, fallback: $_('brokers.sharing.saveFailed')});

        if (result.status === 'success') {
            originalAccesses = JSON.parse(JSON.stringify(accesses));
            onChanged?.();
            toasts.success($_('brokers.sharing.saved'));
            saving = false;
            doClose();
            return;
        }
        error = result.message;
        saving = false;
    }

    // =========================================================================
    // Close handling
    // =========================================================================
    function handleRequestClose() {
        if (hasChanges) {
            confirmCloseOpen = true;
        } else {
            doClose();
        }
    }

    function doClose() {
        confirmCloseOpen = false;
        showAddModal = false;
        showEditModal = false;
        editingUserId = null;
        searchHighlightIndex = -1;
        onClose();
    }

    function confirmDiscard() {
        confirmCloseOpen = false;
        doClose();
    }

    // =========================================================================
    // Helpers
    // =========================================================================
    function getRoleIcon(role: string) {
        return _getRoleIcon(role);
    }

    function getRoleShortLabel(role: string): string {
        return _getRoleShortLabel(role, $_);
    }

    function getRoleIconColor(role: string): string {
        return _getRoleIconColor(role);
    }

    function getAvatarInitial(username: string): string {
        return username ? username.charAt(0).toUpperCase() : '?';
    }

    const roleOptions: Array<{value: 'OWNER' | 'EDITOR' | 'VIEWER'; label: string; shortLabel: string}> = [
        {value: 'OWNER', label: '', shortLabel: ''},
        {value: 'EDITOR', label: '', shortLabel: ''},
        {value: 'VIEWER', label: '', shortLabel: ''},
    ];
    // Reactive labels
    $: roleOptions[0].label = $_('brokers.sharing.roleOwner');
    $: roleOptions[1].label = $_('brokers.sharing.roleEditor');
    $: roleOptions[2].label = $_('brokers.sharing.roleViewer');
    $: roleOptions[0].shortLabel = $_('brokers.sharing.roleOwnerShort');
    $: roleOptions[1].shortLabel = $_('brokers.sharing.roleEditorShort');
    $: roleOptions[2].shortLabel = $_('brokers.sharing.roleViewerShort');
</script>

<ModalBase maxWidth="2xl" onRequestClose={handleRequestClose} {open} testId="broker-sharing-modal" zIndex={50}>
    <div class="bg-white dark:bg-slate-800 rounded-xl w-full flex flex-col max-h-[85vh]">
        <!-- Header -->
        <div class="p-4 border-b border-gray-200 dark:border-slate-700 shrink-0">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <Users class="text-libre-green" size={20} />
                    <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {$_('brokers.sharing.title')} — {brokerName}
                    </h2>
                </div>
                <div class="flex items-center gap-2">
                    {#if hasChanges}
                        <button
                            type="button"
                            on:click={() => {
                                accesses = JSON.parse(JSON.stringify(originalAccesses));
                            }}
                            class="p-1.5 text-amber-500 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
                            title="Reset"
                        >
                            <RotateCcw size={18} />
                        </button>
                    {/if}
                    <button class="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg transition-colors" on:click={handleRequestClose} type="button">
                        <X size={20} />
                    </button>
                </div>
            </div>
            <!-- Role descriptions are now under each column title -->
        </div>

        <!-- Body (scrollable) -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4">
            <!-- Warning Banner -->
            {#if exceedsLimit}
                <InfoBanner variant="warning">
                    <span class="text-sm">{$_('brokers.sharing.percentageWarning')}</span>
                </InfoBanner>
            {/if}

            <!-- Error / Success banners -->
            <InfoBanner dismissible message={error} ondismiss={() => (error = null)} variant="error" />

            {#if loading}
                <div class="flex items-center justify-center py-12">
                    <Loader2 size={32} class="animate-spin text-libre-green" />
                </div>
            {:else}
                <!-- Ownership Chart + Center Info -->
                <div class="relative" data-testid="ownership-chart-section">
                    <SemiDonutChart data={chartSlices} availableLabel={$_('brokers.sharing.available')} height="240px" />
                    <!-- Center overlay: Allocated / Available + Add button -->
                    <div class="absolute bottom-2 left-0 right-0 flex justify-center pointer-events-none" style="z-index: 1;">
                        <div class="text-center">
                            <div class="text-xs text-gray-500 dark:text-gray-400">
                                {$_('brokers.sharing.allocated')}: <span class="font-semibold text-gray-700 dark:text-gray-200">{totalAllocatedPercent.toFixed(1)}%</span>
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">
                                {$_('brokers.sharing.available')}: <span class="font-semibold text-gray-700 dark:text-gray-200">{availablePercent.toFixed(1)}%</span>
                            </div>
                            <button
                                type="button"
                                class="mt-1 pointer-events-auto inline-flex items-center justify-center w-7 h-7 rounded-full bg-libre-green text-white hover:bg-libre-green/90 transition-colors shadow-sm"
                                on:click={() => {
                                    showAddModal = true;
                                    selectedUser = null;
                                    searchQuery = '';
                                    newRole = 'VIEWER';
                                    newSharePercent = 0;
                                    searchHighlightIndex = -1;
                                }}
                                title={$_('brokers.sharing.addUser')}
                                data-testid="sharing-add-user-btn"
                            >
                                <Plus size={16} />
                            </button>
                        </div>
                    </div>
                </div>

                <!-- 3-Column Grid: Owners | Editors | Viewers -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <!-- Owners Column -->
                    <div data-testid="sharing-owners-column">
                        <h3 class="text-sm font-semibold text-gray-600 dark:text-gray-400 flex items-center gap-1.5">
                            <Crown size={14} class="text-amber-500" />
                            {$_('brokers.sharing.owners')}
                        </h3>
                        <p class="text-[10px] text-gray-400 dark:text-gray-500 mb-2">{$_('brokers.sharing.ownerDesc')}</p>
                        <div class="flex flex-col gap-2">
                            {#each owners as entry (entry.user_id)}
                                <button
                                    type="button"
                                    class="flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-full text-sm cursor-pointer hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors w-fit"
                                    data-testid="access-entry-{entry.user_id}"
                                    on:click={() => startEdit(entry)}
                                >
                                    <span class="w-6 h-6 rounded-full overflow-hidden shrink-0 inline-block">
                                        {#if entry.avatar_url}
                                            <LazyImage src="{entry.avatar_url}?img_preview=48x48" alt={entry.username} circle placeholder="avatar" />
                                        {:else}
                                            <span class="w-full h-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center rounded-full">
                                                <span class="text-[10px] font-semibold text-amber-700 dark:text-amber-300">{getAvatarInitial(entry.username)}</span>
                                            </span>
                                        {/if}
                                    </span>
                                    <span class="text-amber-800 dark:text-amber-200 font-medium truncate">{entry.username}</span>
                                    {#if entry.share_percentage > 0}
                                        <span class="text-xs text-amber-600 dark:text-amber-400">
                                            {(Math.round(entry.share_percentage * 10000) / 100).toFixed(1)}%
                                        </span>
                                    {/if}
                                </button>
                            {/each}
                        </div>
                    </div>

                    <!-- Editors Column -->
                    <div data-testid="sharing-editors-column">
                        <h3 class="text-sm font-semibold text-gray-600 dark:text-gray-400 flex items-center gap-1.5">
                            <Pencil size={14} class="text-blue-500" />
                            {$_('brokers.sharing.editors')}
                        </h3>
                        <p class="text-[10px] text-gray-400 dark:text-gray-500 mb-2">{$_('brokers.sharing.editorDesc')}</p>
                        <div class="flex flex-col gap-2">
                            {#each editors as entry (entry.user_id)}
                                <button
                                    type="button"
                                    class="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-full text-sm cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors w-fit"
                                    data-testid="access-entry-{entry.user_id}"
                                    on:click={() => startEdit(entry)}
                                >
                                    <span class="w-6 h-6 rounded-full overflow-hidden shrink-0 inline-block">
                                        {#if entry.avatar_url}
                                            <LazyImage src="{entry.avatar_url}?img_preview=48x48" alt={entry.username} circle placeholder="avatar" />
                                        {:else}
                                            <span class="w-full h-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center rounded-full">
                                                <span class="text-[10px] font-semibold text-blue-700 dark:text-blue-300">{getAvatarInitial(entry.username)}</span>
                                            </span>
                                        {/if}
                                    </span>
                                    <span class="text-blue-800 dark:text-blue-200 font-medium truncate">{entry.username}</span>
                                </button>
                            {/each}
                        </div>
                    </div>

                    <!-- Viewers Column -->
                    <div data-testid="sharing-viewers-column">
                        <h3 class="text-sm font-semibold text-gray-600 dark:text-gray-400 flex items-center gap-1.5">
                            <Eye size={14} class="text-gray-400" />
                            {$_('brokers.sharing.viewers')}
                        </h3>
                        <p class="text-[10px] text-gray-400 dark:text-gray-500 mb-2">{$_('brokers.sharing.viewerDesc')}</p>
                        <div class="flex flex-col gap-2">
                            {#each viewers as entry (entry.user_id)}
                                <button
                                    type="button"
                                    class="flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded-full text-sm cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors w-fit"
                                    data-testid="access-entry-{entry.user_id}"
                                    on:click={() => startEdit(entry)}
                                >
                                    <span class="w-6 h-6 rounded-full overflow-hidden shrink-0 inline-block">
                                        {#if entry.avatar_url}
                                            <LazyImage src="{entry.avatar_url}?img_preview=48x48" alt={entry.username} circle placeholder="avatar" />
                                        {:else}
                                            <span class="w-full h-full bg-gray-200 dark:bg-slate-600 flex items-center justify-center rounded-full">
                                                <span class="text-[10px] font-semibold text-gray-500 dark:text-gray-400">{getAvatarInitial(entry.username)}</span>
                                            </span>
                                        {/if}
                                    </span>
                                    <span class="text-gray-700 dark:text-gray-300 font-medium truncate">{entry.username}</span>
                                </button>
                            {/each}
                        </div>
                    </div>
                </div>

                <!-- Edit user is now in a separate overlay modal below -->

                <!-- Add User form moved to separate overlay modal below -->
            {/if}
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-slate-700 shrink-0">
            <button class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors" on:click={handleRequestClose} type="button">
                {$_('common.cancel')}
            </button>
            <button class="flex items-center gap-2 px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors" data-testid="sharing-save-btn" disabled={!hasChanges || saving} on:click={handleSave} type="button">
                {#if saving}
                    <Loader2 size={16} class="animate-spin" />
                {:else}
                    <Save size={16} />
                {/if}
                {$_('common.saveConfiguration')}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Confirm Remove Dialog -->
<ConfirmModal
    danger={true}
    message={$_('brokers.sharing.removeConfirm').replace('{username}', confirmRemoveUsername)}
    onCancel={() => {
        confirmRemoveOpen = false;
        confirmRemoveUserId = null;
    }}
    onConfirm={confirmRemove}
    open={confirmRemoveOpen}
    title={$_('brokers.sharing.remove')}
    zIndex={60}
/>

<!-- Confirm Discard Changes Dialog -->
<ConfirmModal confirmText={$_('common.discardAndClose')} danger={false} message={$_('brokers.unsavedChanges')} onCancel={() => (confirmCloseOpen = false)} onConfirm={confirmDiscard} open={confirmCloseOpen} title={$_('common.discardChanges')} warning={true} zIndex={60} />

<!-- Add User Overlay Modal -->
<ModalBase
    allowOverflow={true}
    maxWidth="md"
    onRequestClose={() => {
        showAddModal = false;
        selectedUser = null;
        searchQuery = '';
        searchHighlightIndex = -1;
    }}
    open={showAddModal}
    testId="sharing-add-user-modal"
    zIndex={60}
>
    <div class="bg-white dark:bg-slate-800 rounded-xl w-full flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700 shrink-0">
            <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                <Plus class="text-libre-green" size={18} />
                {$_('brokers.sharing.addUser')}
            </h3>
            <button
                class="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg transition-colors"
                on:click={() => {
                    showAddModal = false;
                    selectedUser = null;
                    searchQuery = '';
                    searchHighlightIndex = -1;
                }}
                type="button"
            >
                <X size={18} />
            </button>
        </div>

        <!-- Body -->
        <div class="p-4 space-y-4" data-testid="sharing-add-form">
            <!-- Unified Search / Selected user -->
            <div class="relative">
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1" for="sharing-search-input">
                    {$_('brokers.sharing.searchPlaceholder')}
                </label>
                <div class="flex items-center gap-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 px-3 py-2 {selectedUser ? 'border-libre-green/40 dark:border-libre-green/40 bg-libre-green/5 dark:bg-libre-green/10' : ''}">
                    {#if selectedUser}
                        <!-- Show selected user inline with clear button -->
                        <div class="w-6 h-6 rounded-full overflow-hidden shrink-0">
                            {#if selectedUser.avatar_url}
                                <LazyImage src="{selectedUser.avatar_url}?img_preview=48x48" alt={selectedUser.username} circle />
                            {:else}
                                <span class="w-full h-full bg-gray-200 dark:bg-slate-600 flex items-center justify-center rounded-full">
                                    <span class="text-[10px] font-semibold text-gray-500 dark:text-gray-400">{getAvatarInitial(selectedUser.username)}</span>
                                </span>
                            {/if}
                        </div>
                        <span class="flex-1 text-sm font-medium text-gray-700 dark:text-gray-200">{selectedUser.username}</span>
                        <button
                            type="button"
                            on:click={() => {
                                selectedUser = null;
                                searchQuery = '';
                            }}
                            class="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        >
                            <X size={14} />
                        </button>
                    {:else}
                        <!-- Search mode -->
                        <Search size={16} class="text-gray-400 shrink-0" />
                        <input
                            id="sharing-search-input"
                            type="text"
                            bind:value={searchQuery}
                            on:input={handleSearchInput}
                            on:keydown={handleSearchKeydown}
                            placeholder={$_('brokers.sharing.searchPlaceholder')}
                            class="flex-1 bg-transparent text-sm text-gray-700 dark:text-gray-200 outline-none placeholder-gray-400"
                            data-testid="sharing-search-input"
                        />
                        {#if searching}
                            <Loader2 size={14} class="animate-spin text-gray-400" />
                        {/if}
                    {/if}
                </div>

                <!-- Search results dropdown (only when not selected) -->
                {#if !selectedUser && searchResults.length > 0}
                    <div class="absolute z-10 mt-1 w-full max-h-48 overflow-y-auto bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg py-1">
                        {#each searchResults as user, idx}
                            <button
                                type="button"
                                class="w-full flex items-center gap-2 px-3 py-2 text-left text-sm transition-colors {idx === searchHighlightIndex ? 'bg-libre-green/10 dark:bg-libre-green/20' : 'hover:bg-gray-100 dark:hover:bg-slate-600'}"
                                data-testid="user-search-result-{user.id}"
                                on:click={() => selectSearchUser(user)}
                            >
                                <span class="w-6 h-6 rounded-full overflow-hidden shrink-0">
                                    {#if user.avatar_url}
                                        <LazyImage src="{user.avatar_url}?img_preview=48x48" alt={user.username} circle />
                                    {:else}
                                        <span class="w-full h-full bg-gray-200 dark:bg-slate-600 flex items-center justify-center rounded-full">
                                            <span class="text-[10px] font-semibold text-gray-500 dark:text-gray-400">{getAvatarInitial(user.username)}</span>
                                        </span>
                                    {/if}
                                </span>
                                <span class="text-gray-700 dark:text-gray-200">{user.username}</span>
                            </button>
                        {/each}
                    </div>
                {:else if !selectedUser && searchQuery.length >= 2 && !searching}
                    <div class="absolute z-10 mt-1 w-full bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg py-3 text-center text-sm text-gray-400">
                        {$_('brokers.sharing.noOtherUsers')}
                    </div>
                {/if}
            </div>

            <!-- Role selection -->
            <div class="flex flex-col gap-3">
                <div class="flex items-center gap-2">
                    <span class="text-xs font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">{$_('brokers.sharing.role')}:</span>
                    <div class="relative">
                        <button
                            class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-600"
                            on:click={() => (showRoleDropdown = !showRoleDropdown)}
                            type="button"
                        >
                            <span class={getRoleIconColor(newRole)}>
                                <svelte:component this={getRoleIcon(newRole)} size={14} />
                            </span>
                            {getRoleShortLabel(newRole)}
                            <ChevronDown size={12} />
                        </button>
                        {#if showRoleDropdown}
                            <div class="absolute z-10 bottom-full mb-1 left-0 min-w-full w-max bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg py-1">
                                {#each roleOptions as opt}
                                    <button
                                        type="button"
                                        class="w-full flex items-center gap-2 text-left px-3 py-2 text-xs hover:bg-gray-100 dark:hover:bg-slate-600 text-gray-700 dark:text-gray-200 whitespace-nowrap"
                                        on:click={() => {
                                            newRole = opt.value;
                                            showRoleDropdown = false;
                                            if (opt.value !== 'OWNER') newSharePercent = 0;
                                        }}
                                    >
                                        <span class={getRoleIconColor(opt.value)}>
                                            <svelte:component this={getRoleIcon(opt.value)} size={14} />
                                        </span>
                                        {opt.shortLabel}
                                    </button>
                                {/each}
                            </div>
                        {/if}
                    </div>
                </div>

                {#if newRole === 'OWNER'}
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">{$_('brokers.sharing.sharePercentage')}:</span>
                        <div class="flex items-center gap-1">
                            <input
                                type="number"
                                min="0"
                                max={maxNewShare}
                                step="0.1"
                                bind:value={newSharePercent}
                                on:keydown={(e) => {
                                    if (e.key === 'Enter') handleAddUser();
                                }}
                                class="w-20 px-2 py-1.5 text-sm text-center border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200"
                            />
                            <span class="text-xs text-gray-500">% (max {maxNewShare.toFixed(1)}%)</span>
                        </div>
                    </div>
                {/if}
            </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-2 p-4 border-t border-gray-200 dark:border-slate-700 shrink-0">
            <button
                class="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg transition-colors"
                on:click={() => {
                    showAddModal = false;
                    selectedUser = null;
                    searchQuery = '';
                    searchHighlightIndex = -1;
                }}
                type="button"
            >
                {$_('common.cancel')}
            </button>
            <button class="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors" data-testid="sharing-confirm-add" disabled={!selectedUser} on:click={handleAddUser} type="button">
                <Plus size={16} />
                {$_('brokers.sharing.addUser')}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Edit User Overlay Modal -->
<ModalBase allowOverflow={true} maxWidth="md" onRequestClose={cancelEdit} open={showEditModal} testId="sharing-edit-user-modal" zIndex={60}>
    {@const editEntry = accesses.find((a) => a.user_id === editingUserId)}
    {#if editEntry}
        <div class="bg-white dark:bg-slate-800 rounded-xl w-full flex flex-col overflow-visible">
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700 shrink-0">
                <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                    <Pencil size={18} class="text-libre-green" />
                    {$_('common.edit')}: {editEntry.username}
                </h3>
                <button type="button" on:click={cancelEdit} class="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg transition-colors">
                    <X size={18} />
                </button>
            </div>

            <!-- Body — compact inline layout -->
            <div class="p-4 space-y-3">
                <!-- Row 1: Avatar + Username + Role selector + Share % — all inline -->
                <div class="flex items-center gap-3 flex-wrap">
                    <!-- Avatar -->
                    <div class="w-9 h-9 rounded-full overflow-hidden shrink-0">
                        {#if editEntry.avatar_url}
                            <LazyImage src="{editEntry.avatar_url}?img_preview=48x48" alt={editEntry.username} circle placeholder="avatar" />
                        {:else}
                            <div class="w-full h-full bg-gray-200 dark:bg-slate-600 flex items-center justify-center rounded-full">
                                <span class="text-sm font-semibold text-gray-500 dark:text-gray-400">{getAvatarInitial(editEntry.username)}</span>
                            </div>
                        {/if}
                    </div>
                    <!-- Username -->
                    <span class="text-sm font-medium text-gray-800 dark:text-gray-100">{editEntry.username}</span>

                    <!-- Separator -->
                    <span class="text-gray-300 dark:text-slate-600">|</span>

                    <!-- Role selector -->
                    <div class="relative">
                        <button
                            type="button"
                            class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-600"
                            on:click={() => (showEditRoleDropdown = !showEditRoleDropdown)}
                        >
                            <span class={getRoleIconColor(editRole)}>
                                <svelte:component this={getRoleIcon(editRole)} size={14} />
                            </span>
                            {getRoleShortLabel(editRole)}
                            <ChevronDown size={12} />
                        </button>
                        {#if showEditRoleDropdown}
                            <div class="absolute z-10 bottom-full mb-1 left-0 min-w-full w-max bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg py-1">
                                {#each roleOptions as opt}
                                    <button
                                        type="button"
                                        class="w-full flex items-center gap-2 text-left px-3 py-2 text-xs hover:bg-gray-100 dark:hover:bg-slate-600 text-gray-700 dark:text-gray-200 whitespace-nowrap"
                                        on:click={() => {
                                            editRole = opt.value;
                                            showEditRoleDropdown = false;
                                            if (opt.value !== 'OWNER') editSharePercent = 0;
                                        }}
                                    >
                                        <span class={getRoleIconColor(opt.value)}>
                                            <svelte:component this={getRoleIcon(opt.value)} size={14} />
                                        </span>
                                        {opt.shortLabel}
                                    </button>
                                {/each}
                            </div>
                        {/if}
                    </div>

                    <!-- Share % (only for OWNER) -->
                    {#if editRole === 'OWNER'}
                        <div class="flex items-center gap-1">
                            <input
                                type="number"
                                min="0"
                                max="100"
                                step="0.1"
                                bind:value={editSharePercent}
                                on:keydown={(e) => {
                                    if (e.key === 'Enter') saveEdit();
                                }}
                                class="w-16 px-2 py-1.5 text-sm text-center border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200"
                            />
                            <span class="text-xs text-gray-500">%</span>
                        </div>
                    {/if}
                </div>
            </div>

            <!-- Footer -->
            <div class="flex items-center justify-between p-4 border-t border-gray-200 dark:border-slate-700 shrink-0">
                <button
                    type="button"
                    on:click={() => {
                        const entry = editEntry;
                        cancelEdit();
                        if (entry) requestRemove(entry);
                    }}
                    class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                >
                    <Trash2 size={14} />
                    {$_('brokers.sharing.remove')}
                </button>
                <div class="flex items-center gap-2">
                    <button type="button" on:click={cancelEdit} class="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg transition-colors">
                        {$_('common.cancel')}
                    </button>
                    <button type="button" on:click={saveEdit} class="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors" data-testid="sharing-confirm-edit">
                        <Check size={16} />
                        {$_('common.confirm')}
                    </button>
                </div>
            </div>
        </div>
    {/if}
</ModalBase>
