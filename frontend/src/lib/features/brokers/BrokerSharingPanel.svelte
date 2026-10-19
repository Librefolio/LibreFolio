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
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {tick, untrack} from 'svelte';
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
    interface Props {
        brokerId: number;
        readOnly?: boolean;
        onChanged?: () => void;
        /** If provided, shows a Cancel/Close button next to Save and is also called
         *  right after a successful save (modal auto-close use case). Omit for embedding. */
        onCancel?: () => void;
        /** Bindable — lets a modal wrapper check for unsaved changes before closing. */
        hasChanges?: boolean;
    }

    let {brokerId, readOnly = false, onChanged, onCancel, hasChanges = $bindable(false)}: Props = $props();

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
    let accesses: AccessEntry[] = $state([]);
    let originalAccesses: AccessEntry[] = $state([]);
    let loading = $state(true);
    let saving = $state(false);
    let error: string | null = $state(null);
    let errorKey: string | null = $state(null);
    let accessLoadState = $state<'loading' | 'ready' | 'error'>('loading');

    // Add user state
    let showAddModal = $state(false); // Add User as overlay modal
    let availableUsers: SearchUser[] = $state([]);
    let loadingUsers = $state(false);
    let selectedUserId: number | null = $state(null);
    let newRole = $state<AccessEntry['role']>('VIEWER');
    let newSharePercent: number = $state(0);
    let showRoleDropdown = $state(false);

    // Edit state
    let showEditModal = $state(false);
    let editingUserId: number | null = $state(null);
    let editRole = $state<AccessEntry['role']>('VIEWER');
    let editSharePercent: number = $state(0);
    let showEditRoleDropdown = $state(false);
    let editError: string | null = $state(null);
    let editErrorKey: string | null = $state(null);

    // Confirm dialogs
    let confirmRemoveOpen = $state(false);
    let confirmRemoveUsername = $state('');
    let confirmRemoveUserId: number | null = $state(null);

    // Self-service state (F4): leave broker / self-demote
    let confirmLeaveOpen = $state(false);
    let confirmDemoteOpen = $state(false);
    let selfActionBusy = $state(false);

    // =========================================================================
    // Computed
    // =========================================================================
    let owners = $derived(accesses.filter((a) => a.role === 'OWNER'));
    let editors = $derived(accesses.filter((a) => a.role === 'EDITOR'));
    let viewers = $derived(accesses.filter((a) => a.role === 'VIEWER'));
    let totalAllocated = $derived(owners.reduce((sum, o) => sum + o.share_percentage, 0));
    let totalAllocatedPercent = $derived(Math.round(totalAllocated * 10000) / 100);
    let availablePercent = $derived(Math.round((1 - totalAllocated) * 10000) / 100);
    let exceedsLimit = $derived(totalAllocated > 1.0001); // small epsilon for floating point
    let localHasChanges = $derived(
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
            ),
    );

    $effect(() => {
        hasChanges = localHasChanges;
    });

    let existingUserIds = $derived(new Set(accesses.map((a) => a.user_id)));
    // Users still addable: exclude anyone already granted access locally.
    let selectableUsers = $derived(availableUsers.filter((u) => !existingUserIds.has(u.id)));
    let selectedUser = $derived(selectableUsers.find((u) => u.id === selectedUserId) ?? null);

    // =========================================================================
    // Self-service (F4): the current user can always leave; an EDITOR can also
    // demote themselves to VIEWER. The last OWNER leaving cascade-deletes the
    // broker (confirmed semantics) — the UI presents that as a danger action.
    // =========================================================================
    let currentUserId = $derived($auth.user?.id ?? null);
    let selfEntry = $derived(currentUserId != null ? (accesses.find((a) => a.user_id === currentUserId) ?? null) : null);
    let selfIsLastOwner = $derived(selfEntry?.role === 'OWNER' && owners.length <= 1);

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
    let canEditAccess = $derived(!readOnly && accessLoadState === 'ready');

    // For add form: max share available
    let maxNewShare = $derived(newRole === 'OWNER' ? Math.max(0, Math.round((1 - totalAllocated) * 10000) / 100) : 0);

    // =========================================================================
    // Lifecycle — (re)load whenever brokerId is set/changes. Also covers the
    // modal use case: ModalBase destroys/recreates children on open/close, so
    // this naturally re-fires on every fresh mount (i.e. every time reopened).
    // =========================================================================
    $effect(() => {
        if (brokerId) {
            untrack(loadAccesses);
        }
    });

    // =========================================================================
    // Derived: chart data for SemiDonutChart
    // =========================================================================
    let chartSlices = $derived(
        owners
            .filter((o) => Math.round(o.share_percentage * 10000) / 100 > 0)
            .map((o) => ({
                key: o.user_id,
                name: o.username,
                percentage: Math.round(o.share_percentage * 10000) / 100,
                avatarUrl: o.avatar_url ? `${o.avatar_url}?img_preview=64x64` : null,
            })),
    );

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

    let roleOptions: Array<{value: 'OWNER' | 'EDITOR' | 'VIEWER'; label: string; shortLabel: string}> = $derived([
        {value: 'OWNER', label: $_('brokers.sharing.roleOwner'), shortLabel: $_('brokers.sharing.roleOwnerShort')},
        {value: 'EDITOR', label: $_('brokers.sharing.roleEditor'), shortLabel: $_('brokers.sharing.roleEditorShort')},
        {value: 'VIEWER', label: $_('brokers.sharing.roleViewer'), shortLabel: $_('brokers.sharing.roleViewerShort')},
    ]);

    let NewRoleIcon = $derived(getRoleIcon(newRole));
    let EditRoleIcon = $derived(getRoleIcon(editRole));
</script>

<div class="space-y-4 text-lf-primary" data-testid="broker-sharing-panel" data-access-state={accessLoadState} data-error-key={errorKey ?? undefined} aria-busy={loading ? 'true' : 'false'} aria-invalid={accessLoadState === 'error' ? 'true' : undefined}>
    <!-- Utility row: Reset (only when there are unsaved changes) -->
    {#if !readOnly && hasChanges}
        <div class="flex justify-end">
            <button
                type="button"
                onclick={() => {
                    accesses = JSON.parse(JSON.stringify(originalAccesses));
                }}
                class="p-1.5 text-lf-warning hover:bg-lf-warning-soft rounded-lg transition-colors"
                title="Reset"
                data-testid="sharing-reset-btn"
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
        <div class="flex items-center justify-between gap-3 rounded-xl border border-lf-danger-line bg-lf-danger-soft p-3" data-testid="sharing-load-error-state">
            <span class="text-sm text-lf-danger-on-soft">{$_('brokers.sharing.loadFailedBlocking')}</span>
            <button type="button" class="inline-flex items-center gap-1.5 rounded-lg border border-lf-danger-line px-3 py-1.5 text-sm font-medium text-lf-danger-on-soft transition-colors hover:bg-lf-danger-line" data-testid="sharing-retry-load-btn" onclick={loadAccesses}>
                <RotateCcw size={14} />
                {$_('common.retry')}
            </button>
        </div>
    {/if}

    {#if loading}
        <div class="flex items-center justify-center py-12">
            <Loader2 size={32} class="animate-spin text-lf-link" />
        </div>
    {:else}
        <!-- Ownership Chart + Center Info -->
        <div class="relative" data-testid="ownership-chart-section">
            <SemiDonutChart data={chartSlices} availableLabel={$_('brokers.sharing.available')} height="240px" />
            <!-- Center overlay: Allocated / Available + Add button -->
            <div class="absolute bottom-2 left-0 right-0 flex justify-center pointer-events-none" style="z-index: 1;">
                <div class="text-center">
                    <div class="text-xs text-lf-muted">
                        {$_('brokers.sharing.allocated')}: <span class="font-semibold text-lf-secondary">{formatPercent(totalAllocatedPercent, {signed: false, digits: 1})}</span>
                    </div>
                    <div class="text-xs text-lf-muted">
                        {$_('brokers.sharing.available')}: <span class="font-semibold text-lf-secondary">{formatPercent(availablePercent, {signed: false, digits: 1})}</span>
                    </div>
                    {#if canEditAccess}
                        <button
                            type="button"
                            class="mt-1 pointer-events-auto inline-flex items-center justify-center w-7 h-7 rounded-full bg-lf-action text-lf-on-action hover:bg-lf-action-hover transition-colors shadow-sm"
                            onclick={() => {
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
                <h3 class="text-sm font-semibold text-lf-secondary flex items-center gap-1.5">
                    <Crown size={14} class="text-amber-500" />
                    {$_('brokers.sharing.owners')}
                </h3>
                <p class="text-[10px] text-lf-muted mb-2">{$_('brokers.sharing.ownerDesc')}</p>
                <div class="flex flex-col gap-2">
                    {#each owners as entry (entry.user_id)}
                        <button
                            type="button"
                            class="flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-sm transition-colors w-fit {readOnly ? 'cursor-default' : 'cursor-pointer hover:bg-amber-100 dark:hover:bg-amber-900/30'}"
                            data-testid="access-entry-{entry.user_id}"
                            disabled={!canEditAccess}
                            onclick={() => startEdit(entry)}
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
                                    {getRoleShortLabel(entry.role)} · {formatPercent(Math.round(entry.share_percentage * 10000) / 100, {signed: false, digits: 1})}
                                </div>
                            </div>
                        </button>
                    {/each}
                </div>
            </div>

            <!-- Editors Column -->
            <div data-testid="sharing-editors-column">
                <h3 class="text-sm font-semibold text-lf-secondary flex items-center gap-1.5">
                    <Pencil size={14} class="text-blue-500" />
                    {$_('brokers.sharing.editors')}
                </h3>
                <p class="text-[10px] text-lf-muted mb-2">{$_('brokers.sharing.editorDesc')}</p>
                <div class="flex flex-col gap-2">
                    {#each editors as entry (entry.user_id)}
                        <button
                            type="button"
                            class="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl text-sm transition-colors w-fit {readOnly ? 'cursor-default' : 'cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/30'}"
                            data-testid="access-entry-{entry.user_id}"
                            disabled={!canEditAccess}
                            onclick={() => startEdit(entry)}
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
                                    {getRoleShortLabel(entry.role)} · {formatPercent(Math.round(entry.share_percentage * 10000) / 100, {signed: false, digits: 1})}
                                </div>
                            </div>
                        </button>
                    {/each}
                </div>
            </div>

            <!-- Viewers Column -->
            <div data-testid="sharing-viewers-column">
                <h3 class="text-sm font-semibold text-lf-secondary flex items-center gap-1.5">
                    <Eye size={14} class="text-gray-400" />
                    {$_('brokers.sharing.viewers')}
                </h3>
                <p class="text-[10px] text-lf-muted mb-2">{$_('brokers.sharing.viewerDesc')}</p>
                <div class="flex flex-col gap-2">
                    {#each viewers as entry (entry.user_id)}
                        <button
                            type="button"
                            class="flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded-xl text-sm transition-colors w-fit {readOnly ? 'cursor-default' : 'cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700'}"
                            data-testid="access-entry-{entry.user_id}"
                            disabled={!canEditAccess}
                            onclick={() => startEdit(entry)}
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
                                    {getRoleShortLabel(entry.role)} · {formatPercent(Math.round(entry.share_percentage * 10000) / 100, {signed: false, digits: 1})}
                                </div>
                            </div>
                        </button>
                    {/each}
                </div>
            </div>
        </div>

        <!-- Self-service (F4): leave / self-demote — always available, even readOnly -->
        {#if selfEntry}
            <div class="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-lf-subtle bg-lf-panel px-3 py-2" data-testid="sharing-self-service">
                <span class="text-xs text-lf-muted">
                    {$_('brokers.sharing.yourAccess')}: <span class="font-medium text-lf-secondary">{getRoleShortLabel(selfEntry.role)}</span>
                </span>
                <div class="flex items-center gap-2">
                    {#if selfEntry.role === 'EDITOR'}
                        <button
                            type="button"
                            class="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg border border-lf-input text-lf-secondary hover:bg-lf-neutral transition-colors disabled:opacity-50"
                            disabled={selfActionBusy}
                            onclick={() => (confirmDemoteOpen = true)}
                            data-testid="sharing-self-demote-btn"
                        >
                            <Eye size={13} />
                            {$_('brokers.sharing.demoteToViewer')}
                        </button>
                    {/if}
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors disabled:opacity-50 {selfIsLastOwner ? 'border-lf-danger-line text-lf-danger hover:bg-lf-danger-soft' : 'border-lf-input text-lf-secondary hover:bg-lf-neutral'}"
                        disabled={selfActionBusy}
                        onclick={() => (confirmLeaveOpen = true)}
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
            <div class="flex items-center justify-end gap-3 pt-2 border-t border-lf-subtle">
                {#if onCancel}
                    <button class="px-4 py-2 text-sm text-lf-secondary hover:bg-lf-hover rounded-lg transition-colors" onclick={onCancel} type="button">
                        {$_('common.cancel')}
                    </button>
                {/if}
                <button
                    class="flex items-center gap-2 px-4 py-2 text-sm bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    data-testid="sharing-save-btn"
                    disabled={!hasChanges || saving || accessLoadState !== 'ready'}
                    onclick={handleSave}
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
        <div class="bg-lf-card rounded-xl w-full flex flex-col">
            <!-- Header -->
            <div class="flex items-center justify-between p-4 border-b border-lf-subtle shrink-0">
                <h3 class="text-base font-semibold text-lf-primary flex items-center gap-2">
                    <Plus class="text-lf-link" size={18} />
                    {$_('brokers.sharing.addUser')}
                </h3>
                <button
                    class="p-1.5 text-lf-muted hover:text-lf-secondary rounded-lg transition-colors"
                    onclick={() => {
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
                    <span class="block text-xs font-medium text-lf-muted mb-1">
                        {$_('brokers.sharing.searchPlaceholder')}
                    </span>
                    <UserSearchSelect bind:value={selectedUserId} dropdownPosition="bottom" loading={loadingUsers} maxVisibleItems={6} testId="sharing-user-select" users={selectableUsers} />
                    {#if !loadingUsers && selectableUsers.length === 0}
                        <p class="mt-1 text-xs text-lf-muted" data-testid="sharing-no-other-users">{$_('brokers.sharing.noOtherUsers')}</p>
                    {/if}
                </div>

                <!-- Role selection -->
                <div class="flex flex-col gap-3">
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-medium text-lf-muted whitespace-nowrap">{$_('brokers.sharing.role')}:</span>
                        <div class="relative">
                            <button
                                class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-lf-input hover:border-lf-input-hover bg-lf-field text-lf-primary hover:bg-lf-hover"
                                onclick={() => (showRoleDropdown = !showRoleDropdown)}
                                type="button"
                                data-testid="sharing-add-role-trigger"
                            >
                                <span class={getRoleIconColor(newRole)}>
                                    <NewRoleIcon size={14} />
                                </span>
                                {getRoleShortLabel(newRole)}
                                <ChevronDown size={12} />
                            </button>
                            {#if showRoleDropdown}
                                <div class="absolute z-10 bottom-full mb-1 left-0 min-w-full w-max bg-lf-card border border-lf-raised rounded-lg shadow-lg shadow-lf-shadow py-1">
                                    {#each roleOptions as opt}
                                        {@const OptionIcon = getRoleIcon(opt.value)}
                                        <button
                                            type="button"
                                            class="w-full flex items-center gap-2 text-left px-3 py-2 text-xs hover:bg-lf-hover text-lf-secondary whitespace-nowrap"
                                            data-testid="sharing-add-role-option-{opt.value}"
                                            onclick={() => {
                                                newRole = opt.value;
                                                showRoleDropdown = false;
                                                if (opt.value !== 'OWNER') newSharePercent = 0;
                                            }}
                                        >
                                            <span class={getRoleIconColor(opt.value)}>
                                                <OptionIcon size={14} />
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
                            <span class="text-xs font-medium text-lf-muted whitespace-nowrap">{$_('brokers.sharing.sharePercentage')}:</span>
                            <div class="flex items-center gap-1">
                                <input
                                    type="number"
                                    use:numericArrows={{step: 0.1}}
                                    min="0"
                                    max={maxNewShare}
                                    step="0.1"
                                    bind:value={newSharePercent}
                                    onkeydown={(e) => {
                                        if (e.key === 'Enter') handleAddUser();
                                    }}
                                    class="w-20 px-2 py-1.5 text-sm text-center border border-lf-input hover:border-lf-input-hover rounded-lg bg-lf-field text-lf-primary"
                                />
                                <span class="text-xs text-lf-muted">% (max {formatPercent(maxNewShare, {signed: false, digits: 1})})</span>
                            </div>
                        </div>
                    {/if}
                </div>
            </div>

            <!-- Footer -->
            <div class="flex items-center justify-end gap-2 p-4 border-t border-lf-subtle shrink-0">
                <button
                    class="px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover rounded-lg transition-colors"
                    onclick={() => {
                        showAddModal = false;
                        selectedUserId = null;
                    }}
                    type="button"
                >
                    {$_('common.cancel')}
                </button>
                <button
                    class="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    data-testid="sharing-confirm-add"
                    disabled={!selectedUser}
                    onclick={handleAddUser}
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
            <div class="bg-lf-card rounded-xl w-full flex flex-col overflow-visible">
                <!-- Header -->
                <div class="flex items-center justify-between p-4 border-b border-lf-subtle shrink-0">
                    <h3 class="text-base font-semibold text-lf-primary flex items-center gap-2">
                        <Pencil size={18} class="text-lf-link" />
                        {$_('common.edit')}: {editEntry.username}
                    </h3>
                    <button type="button" onclick={cancelEdit} class="p-1.5 text-lf-muted hover:text-lf-secondary rounded-lg transition-colors">
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
                                <div class="w-full h-full bg-lf-neutral flex items-center justify-center rounded-full">
                                    <span class="text-sm font-semibold text-lf-muted">{getAvatarInitial(editEntry.username)}</span>
                                </div>
                            {/if}
                        </div>
                        <!-- Username -->
                        <span class="text-sm font-medium text-lf-primary">{editEntry.username}</span>

                        <!-- Separator -->
                        <span class="text-lf-muted">|</span>

                        <!-- Role selector -->
                        <div class="relative">
                            <button
                                type="button"
                                class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg border border-lf-input hover:border-lf-input-hover bg-lf-field text-lf-primary hover:bg-lf-hover"
                                onclick={() => (showEditRoleDropdown = !showEditRoleDropdown)}
                                data-testid="sharing-edit-role-trigger"
                            >
                                <span class={getRoleIconColor(editRole)}>
                                    <EditRoleIcon size={14} />
                                </span>
                                {getRoleShortLabel(editRole)}
                                <ChevronDown size={12} />
                            </button>
                            {#if showEditRoleDropdown}
                                <div class="absolute z-10 bottom-full mb-1 left-0 min-w-full w-max bg-lf-card border border-lf-raised rounded-lg shadow-lg shadow-lf-shadow py-1">
                                    {#each roleOptions as opt}
                                        {@const OptionIcon = getRoleIcon(opt.value)}
                                        <button
                                            type="button"
                                            class="w-full flex items-center gap-2 text-left px-3 py-2 text-xs hover:bg-lf-hover text-lf-secondary whitespace-nowrap"
                                            data-testid="sharing-edit-role-option-{opt.value}"
                                            onclick={() => {
                                                editError = null;
                                                editErrorKey = null;
                                                editRole = opt.value;
                                                showEditRoleDropdown = false;
                                                if (opt.value !== 'OWNER') editSharePercent = 0;
                                            }}
                                        >
                                            <span class={getRoleIconColor(opt.value)}>
                                                <OptionIcon size={14} />
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
                                    onkeydown={(e) => {
                                        if (e.key === 'Enter') saveEdit();
                                    }}
                                    class="w-16 px-2 py-1.5 text-sm text-center border border-lf-input hover:border-lf-input-hover rounded-lg bg-lf-field text-lf-primary"
                                />
                                <span class="text-xs text-lf-muted">%</span>
                            </div>
                        {/if}
                    </div>
                </div>

                <!-- Footer -->
                <div class="flex items-center justify-between p-4 border-t border-lf-subtle shrink-0">
                    <button
                        type="button"
                        onclick={() => {
                            const entry = editEntry;
                            cancelEdit();
                            if (entry) requestRemove(entry);
                        }}
                        class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-lf-danger hover:bg-lf-danger-soft rounded-lg transition-colors"
                    >
                        <Trash2 size={14} />
                        {$_('brokers.sharing.remove')}
                    </button>
                    <div class="flex items-center gap-2">
                        <button type="button" onclick={cancelEdit} class="px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover rounded-lg transition-colors">
                            {$_('common.cancel')}
                        </button>
                        <button type="button" onclick={saveEdit} class="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors" data-testid="sharing-confirm-edit">
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
