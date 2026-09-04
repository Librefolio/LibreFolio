<!--
  BrokerSharingPanel - Pure content for managing broker access sharing

  Extracted from BrokerSharingModal so the SAME UI (ownership donut chart,
  add/edit/remove users, batch save) can be used both inside a modal
  (BrokerSharingModal wraps this in <ModalBase>) AND embedded directly in a
  page (e.g. the broker detail "Info" tab) — no modal chrome of its own.

  Features:
  - Half-donut ECharts pie chart showing OWNER share distribution
  - Add/edit/remove users with role and share percentage
  - Batch save: all changes local until "Save" is clicked
  - Warning banner when total ownership exceeds 100%
  - Search users with debounce + exclude already-added
  - Dark mode support

  `onCancel`, if provided, renders a Cancel/Close button next to Save (for the
  modal use case) and is also invoked right after a successful save (mirrors
  the modal's previous auto-close-on-save behavior). Omit it entirely when
  embedding the panel directly in a page — no Cancel button will render.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {tick} from 'svelte';
    import {goto} from '$app/navigation';
    import {zodiosApi} from '$lib/api';
    import {auth} from '$lib/stores/app/auth';
    import {trySave} from '$lib/utils/trySave';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {Check, ChevronDown, Crown, Eye, Loader2, Pencil, Plus, RotateCcw, Save, Trash2, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import {getRoleIcon as _getRoleIcon, getRoleIconColor as _getRoleIconColor, getRoleShortLabel as _getRoleShortLabel} from '$lib/utils/broker/brokerRoleHelpers';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import LazyImage from '$lib/components/ui/media/LazyImage.svelte';
    import {UserSearchSelect} from '$lib/components/ui/select';
    import SemiDonutChart from '$lib/components/charts/SemiDonutChart.svelte';

    import {numericArrows} from '$lib/actions/numericArrows';
    // =========================================================================
    // Props
    // =========================================================================
    export let brokerId: number;
    export let readOnly: boolean = false;
    export let onChanged: (() => void) | undefined = undefined;
    /** If provided, shows a Cancel/Close button next to Save and is also called
     *  right after a successful save (modal auto-close use case). Omit for embedding. */
    export let onCancel: (() => void) | undefined = undefined;
    /** Bindable — lets a modal wrapper check for unsaved changes before closing. */
    export let hasChanges: boolean = false;

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
    let errorKey: string | null = null;
    let accessLoadState: 'loading' | 'ready' | 'error' = 'loading';

    // Add user state
    let showAddModal = false; // Add User as overlay modal
    let availableUsers: SearchUser[] = [];
    let loadingUsers = false;
    let selectedUserId: number | null = null;
    let newRole: 'OWNER' | 'EDITOR' | 'VIEWER' = 'VIEWER';
    let newSharePercent: number = 0;
    let showRoleDropdown = false;

    // Edit state
    let showEditModal = false;
    let editingUserId: number | null = null;
    let editRole: 'OWNER' | 'EDITOR' | 'VIEWER' = 'VIEWER';
    let editSharePercent: number = 0;
    let showEditRoleDropdown = false;
    let editError: string | null = null;
    let editErrorKey: string | null = null;

    // Confirm dialogs
    let confirmRemoveOpen = false;
    let confirmRemoveUsername = '';
    let confirmRemoveUserId: number | null = null;

    // Self-service state (F4): leave broker / self-demote
    let confirmLeaveOpen = false;
    let confirmDemoteOpen = false;
    let selfActionBusy = false;

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
    // Users still addable: exclude anyone already granted access locally.
    $: selectableUsers = availableUsers.filter((u) => !existingUserIds.has(u.id));
    $: selectedUser = selectableUsers.find((u) => u.id === selectedUserId) ?? null;

    // =========================================================================
    // Self-service (F4): the current user can always leave; an EDITOR can also
    // demote themselves to VIEWER. The last OWNER leaving cascade-deletes the
    // broker (confirmed semantics) — the UI presents that as a danger action.
    // =========================================================================
    $: currentUserId = $auth.user?.id ?? null;
    $: selfEntry = currentUserId != null ? (accesses.find((a) => a.user_id === currentUserId) ?? null) : null;
    $: selfIsLastOwner = selfEntry?.role === 'OWNER' && owners.length <= 1;

    async function handleSelfDemote() {
        if (selfActionBusy) return;
        selfActionBusy = true;
        try {
            await zodiosApi.update_own_broker_role_api_v1_brokers__broker_id__access_me_patch({role: 'VIEWER'}, {params: {broker_id: brokerId}});
            confirmDemoteOpen = false;
            toasts.success($_('brokers.sharing.selfDemoteDone'));
            await loadAccesses();
            onChanged?.();
        } catch {
            toasts.error($_('brokers.sharing.saveFailed'));
        } finally {
            selfActionBusy = false;
        }
    }

    async function handleSelfLeave() {
        if (selfActionBusy) return;
        selfActionBusy = true;
        try {
            const res = await zodiosApi.leave_broker_access_api_v1_brokers__broker_id__access_me_delete(undefined, {params: {broker_id: brokerId}});
            confirmLeaveOpen = false;
            // Navigate FIRST: on broker detail, onChanged reloads the very broker
            // that was just cascade-deleted and can throw, which used to skip the
            // goto entirely — the modal stayed open over the stale page (round 3).
            if (res.broker_deleted) {
                toasts.success($_('brokers.sharing.leaveDeletedBroker'));
                goto('/brokers');
                onChanged?.();
            } else {
                toasts.success($_('brokers.sharing.leaveDone'));
                // Access lost — back to the broker list
                goto('/brokers');
                onChanged?.();
            }
            // Close the host modal (round 5): onCancel is handleRequestClose when
            // embedded in BrokerSharingModal, a no-op when embedded in a page tab.
            onCancel?.();
        } catch {
            toasts.error($_('brokers.sharing.saveFailed'));
        } finally {
            selfActionBusy = false;
        }
    }
    $: canEditAccess = !readOnly && accessLoadState === 'ready';

    // For add form: max share available
    $: maxNewShare = newRole === 'OWNER' ? Math.max(0, Math.round((1 - totalAllocated) * 10000) / 100) : 0;

    // =========================================================================
    // Lifecycle — (re)load whenever brokerId is set/changes. Also covers the
    // modal use case: ModalBase destroys/recreates children on open/close, so
    // this naturally re-fires on every fresh mount (i.e. every time reopened).
    // =========================================================================
    $: if (brokerId) {
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
        accessLoadState = 'loading';
        error = null;
        errorKey = null;
        editError = null;
        editErrorKey = null;
        showAddModal = false;
        editingUserId = null;
        showEditModal = false;
        accesses = [];
        originalAccesses = [];

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
            accessLoadState = 'ready';
        } catch {
            errorKey = 'brokers.sharing.loadFailedBlocking';
            error = $_(errorKey);
            accessLoadState = 'error';
        } finally {
            loading = false;
        }
    }

    // =========================================================================
    // User list (loaded up-front so the picker shows every candidate on open)
    // =========================================================================
    async function loadSelectableUsers() {
        loadingUsers = true;
        try {
            const response = await zodiosApi.search_users_endpoint_api_v1_users_search_get({
                queries: {q: '', exclude_broker_id: brokerId},
            });
            const items = (response as any).items || [];
            availableUsers = items.map((u: any) => ({
                id: u.id,
                username: u.username,
                avatar_url: typeof u.avatar_url === 'string' ? u.avatar_url : null,
            }));
        } catch {
            availableUsers = [];
        } finally {
            loadingUsers = false;
        }
    }

    // =========================================================================
    // Add User (local)
    // =========================================================================
    function handleAddUser() {
        if (!canEditAccess || !selectedUser) return;

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
        selectedUserId = null;
        newRole = 'VIEWER';
        newSharePercent = 0;
        showAddModal = false;
    }

    // =========================================================================
    // Edit User (local)
    // =========================================================================
    function startEdit(entry: AccessEntry) {
        if (!canEditAccess) return;
        editingUserId = entry.user_id;
        editRole = entry.role;
        editSharePercent = Math.round(entry.share_percentage * 10000) / 100;
        showEditRoleDropdown = false;
        editError = null;
        editErrorKey = null;
        showEditModal = true;
    }

    function saveEdit() {
        if (!canEditAccess || editingUserId === null) return;

        const entry = accesses.find((a) => a.user_id === editingUserId);
        if (entry?.role === 'OWNER' && editRole !== 'OWNER' && owners.length <= 1) {
            editErrorKey = 'brokers.sharing.lastOwnerDemotionWarning';
            editError = $_(editErrorKey);
            return;
        }

        accesses = accesses.map((a) => {
            if (a.user_id !== editingUserId) return a;
            const share = editRole === 'OWNER' ? editSharePercent / 100 : 0;
            return {...a, role: editRole, share_percentage: share};
        });
        editingUserId = null;
        editError = null;
        editErrorKey = null;
        showEditModal = false;
    }

    function cancelEdit() {
        editingUserId = null;
        editError = null;
        editErrorKey = null;
        showEditModal = false;
    }

    // =========================================================================
    // Remove User (local with confirm)
    // =========================================================================
    function requestRemove(entry: AccessEntry) {
        if (!canEditAccess) return;
        // Check: cannot remove last OWNER
        if (entry.role === 'OWNER' && owners.length <= 1) {
            errorKey = 'brokers.sharing.lastOwnerRemovalWarning';
            error = $_(errorKey);
            return;
        }
        confirmRemoveUserId = entry.user_id;
        confirmRemoveUsername = entry.username;
        confirmRemoveOpen = true;
    }

    function confirmRemove() {
        if (!canEditAccess || confirmRemoveUserId === null) return;
        accesses = accesses.filter((a) => a.user_id !== confirmRemoveUserId);
        confirmRemoveOpen = false;
        confirmRemoveUserId = null;
    }

    // =========================================================================
    // Save (batch PUT)
    // =========================================================================
    async function handleSave() {
        if (readOnly) return;
        if (accessLoadState !== 'ready') {
            errorKey = 'brokers.sharing.saveRequiresLoadedAccess';
            error = $_(errorKey);
            return;
        }
        saving = true;
        error = null;
        errorKey = null;

        const body = accesses.map((a) => ({
            user_id: a.user_id,
            role: a.role,
            share_percentage: a.share_percentage,
        }));

        const result = await trySave(() => zodiosApi.bulk_update_broker_access_api_v1_brokers__broker_id__access_put(body, {params: {broker_id: brokerId}}), {toast: false, fallback: $_('brokers.sharing.saveFailed')});

        if (result.status === 'success') {
            originalAccesses = JSON.parse(JSON.stringify(accesses));
            onChanged?.();
            toasts.success($_('brokers.sharing.saved'));
            saving = false;
            // Mirrors the modal's previous auto-close-on-save behavior. No-op when embedded
            // (onCancel undefined). `hasChanges` recomputes only on the next flush, so without
            // `await tick()` a bound modal wrapper would still see it as true and pop the
            // unsaved-changes confirmation right after a successful save (beta feedback F3).
            await tick();
            onCancel?.();
            return;
        }
        error = result.message;
        errorKey = null;
        saving = false;
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

<div class="space-y-4" data-testid="broker-sharing-panel" data-access-state={accessLoadState} data-error-key={errorKey ?? undefined} aria-busy={loading ? 'true' : 'false'} aria-invalid={accessLoadState === 'error' ? 'true' : undefined}>
    <!-- Utility row: Reset (only when there are unsaved changes) -->
    {#if !readOnly && hasChanges}
        <div class="flex justify-end">
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
        </div>
    {/if}

    <!-- Warning Banner -->
    {#if exceedsLimit}
        <InfoBanner variant="warning">
            <span class="text-sm">{$_('brokers.sharing.percentageWarning')}</span>
        </InfoBanner>
    {/if}

    <!-- Error / Success banners -->
    <InfoBanner
        dismissible
        message={error}
        ondismiss={() => {
            error = null;
            errorKey = null;
        }}
        variant="error"
    />

    {#if accessLoadState === 'error'}
        <div class="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-3 dark:border-red-900/50 dark:bg-red-900/20" data-testid="sharing-load-error-state">
            <span class="text-sm text-red-700 dark:text-red-200">{$_('brokers.sharing.loadFailedBlocking')}</span>
            <button
                type="button"
                class="inline-flex items-center gap-1.5 rounded-lg border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-100 dark:border-red-800 dark:text-red-200 dark:hover:bg-red-900/40"
                data-testid="sharing-retry-load-btn"
                on:click={loadAccesses}
            >
                <RotateCcw size={14} />
                {$_('common.retry')}
            </button>
        </div>
    {/if}

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
                    {#if canEditAccess}
                        <button
                            type="button"
                            class="mt-1 pointer-events-auto inline-flex items-center justify-center w-7 h-7 rounded-full bg-libre-green text-white hover:bg-libre-green/90 transition-colors shadow-sm"
                            on:click={() => {
                                showAddModal = true;
                                selectedUserId = null;
                                newRole = 'VIEWER';
                                newSharePercent = 0;
                                loadSelectableUsers();
                            }}
                            title={$_('brokers.sharing.addUser')}
                            data-testid="sharing-add-user-btn"
                        >
                            <Plus size={16} />
                        </button>
                    {/if}
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
                            class="flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm transition-colors w-fit {readOnly ? 'cursor-default' : 'cursor-pointer hover:bg-amber-100 dark:hover:bg-amber-900/30'}"
                            data-testid="access-entry-{entry.user_id}"
                            disabled={!canEditAccess}
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
                            <div class="min-w-0">
                                <div class="text-amber-800 dark:text-amber-200 font-medium truncate">{entry.username}</div>
                                <div class="text-[10px] text-amber-600 dark:text-amber-400">
                                    {getRoleShortLabel(entry.role)} · {(Math.round(entry.share_percentage * 10000) / 100).toFixed(1)}%
                                </div>
                            </div>
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
                            class="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl text-sm transition-colors w-fit {readOnly ? 'cursor-default' : 'cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/30'}"
                            data-testid="access-entry-{entry.user_id}"
                            disabled={!canEditAccess}
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
                            <div class="min-w-0">
                                <div class="text-blue-800 dark:text-blue-200 font-medium truncate">{entry.username}</div>
                                <div class="text-[10px] text-blue-600 dark:text-blue-400">
                                    {getRoleShortLabel(entry.role)} · {(Math.round(entry.share_percentage * 10000) / 100).toFixed(1)}%
                                </div>
                            </div>
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
                            class="flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded-xl text-sm transition-colors w-fit {readOnly ? 'cursor-default' : 'cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700'}"
                            data-testid="access-entry-{entry.user_id}"
                            disabled={!canEditAccess}
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
                            <div class="min-w-0">
                                <div class="text-gray-700 dark:text-gray-300 font-medium truncate">{entry.username}</div>
                                <div class="text-[10px] text-gray-500 dark:text-gray-400">
                                    {getRoleShortLabel(entry.role)} · {(Math.round(entry.share_percentage * 10000) / 100).toFixed(1)}%
                                </div>
                            </div>
                        </button>
                    {/each}
                </div>
            </div>
        </div>

        <!-- Self-service (F4): leave / self-demote — always available, even readOnly -->
        {#if selfEntry}
            <div class="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/40 px-3 py-2" data-testid="sharing-self-service">
                <span class="text-xs text-gray-500 dark:text-gray-400">
                    {$_('brokers.sharing.yourAccess')}: <span class="font-medium text-gray-700 dark:text-gray-200">{getRoleShortLabel(selfEntry.role)}</span>
                </span>
                <div class="flex items-center gap-2">
                    {#if selfEntry.role === 'EDITOR'}
                        <button
                            type="button"
                            class="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg border border-gray-300 dark:border-slate-500 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
                            disabled={selfActionBusy}
                            on:click={() => (confirmDemoteOpen = true)}
                            data-testid="sharing-self-demote-btn"
                        >
                            <Eye size={13} />
                            {$_('brokers.sharing.demoteToViewer')}
                        </button>
                    {/if}
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors disabled:opacity-50 {selfIsLastOwner
                            ? 'border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20'
                            : 'border-gray-300 dark:border-slate-500 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-600'}"
                        disabled={selfActionBusy}
                        on:click={() => (confirmLeaveOpen = true)}
                        data-testid="sharing-self-leave-btn"
                    >
                        <Trash2 size={13} />
                        {selfIsLastOwner ? $_('brokers.sharing.leaveAndDelete') : $_('brokers.sharing.leaveBroker')}
                    </button>
                </div>
            </div>
        {/if}

        <!-- Action row: [Cancel/Close if provided] [Save Configuration] -->
        {#if !readOnly}
            <div class="flex items-center justify-end gap-3 pt-2 border-t border-gray-100 dark:border-slate-700">
                {#if onCancel}
                    <button class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors" on:click={onCancel} type="button">
                        {$_('common.cancel')}
                    </button>
                {/if}
                <button
                    class="flex items-center gap-2 px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    data-testid="sharing-save-btn"
                    disabled={!hasChanges || saving || accessLoadState !== 'ready'}
                    on:click={handleSave}
                    type="button"
                >
                    {#if saving}
                        <Loader2 size={16} class="animate-spin" />
                    {:else}
                        <Save size={16} />
                    {/if}
                    {$_('common.saveConfiguration')}
                </button>
            </div>
        {/if}
    {/if}
</div>

{#if !readOnly}
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

    <!-- Add User Overlay Modal -->
    <ModalBase
        allowOverflow={true}
        maxWidth="md"
        onRequestClose={() => {
            showAddModal = false;
            selectedUserId = null;
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
                        selectedUserId = null;
                    }}
                    type="button"
                >
                    <X size={18} />
                </button>
            </div>

            <!-- Body -->
            <div class="p-4 space-y-4" data-testid="sharing-add-form">
                <!-- User picker: opens showing every candidate, narrows down as you type -->
                <div>
                    <span class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        {$_('brokers.sharing.searchPlaceholder')}
                    </span>
                    <UserSearchSelect bind:value={selectedUserId} dropdownPosition="bottom" loading={loadingUsers} maxVisibleItems={6} testId="sharing-user-select" users={selectableUsers} />
                    {#if !loadingUsers && selectableUsers.length === 0}
                        <p class="mt-1 text-xs text-gray-400" data-testid="sharing-no-other-users">{$_('brokers.sharing.noOtherUsers')}</p>
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
                                    use:numericArrows={{step: 0.1}}
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
                        selectedUserId = null;
                    }}
                    type="button"
                >
                    {$_('common.cancel')}
                </button>
                <button
                    class="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    data-testid="sharing-confirm-add"
                    disabled={!selectedUser}
                    on:click={handleAddUser}
                    type="button"
                >
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
                <div class="p-4 space-y-3" data-edit-error-key={editErrorKey ?? undefined}>
                    <InfoBanner message={editError} variant="error" />
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
                                                editError = null;
                                                editErrorKey = null;
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
                                    use:numericArrows={{step: 0.1}}
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
{/if}

<!-- Self-service confirms (F4) — outside the readOnly guard: they must work
     for VIEWER/EDITOR embeddings too -->
<ConfirmModal danger={false} message={$_('brokers.sharing.demoteConfirm')} onCancel={() => (confirmDemoteOpen = false)} onConfirm={handleSelfDemote} open={confirmDemoteOpen} title={$_('brokers.sharing.demoteToViewer')} zIndex={70} />

<ConfirmModal
    danger={selfIsLastOwner}
    message={selfIsLastOwner ? $_('brokers.sharing.leaveLastOwnerWarning') : $_('brokers.sharing.leaveConfirm')}
    description={selfIsLastOwner ? $_('brokers.sharing.leaveLastOwnerHint') : ''}
    descriptionItalic={selfIsLastOwner}
    onCancel={() => (confirmLeaveOpen = false)}
    onConfirm={handleSelfLeave}
    open={confirmLeaveOpen}
    title={selfIsLastOwner ? $_('brokers.sharing.leaveAndDelete') : $_('brokers.sharing.leaveBroker')}
    zIndex={70}
/>
