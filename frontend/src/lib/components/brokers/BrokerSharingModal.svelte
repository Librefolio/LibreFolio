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
    import {onMount, tick} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {
        X, Plus, Minus, Save, RotateCcw, Users, Crown, Eye, Pencil,
        AlertTriangle, Search, Check, Loader2, Trash2, ChevronDown
    } from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
    import LazyImage from '$lib/components/ui/media/LazyImage.svelte';
    import * as echarts from 'echarts';

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
    let successMessage: string | null = null;

    // Add user state
    let showAddForm = false;
    let searchQuery = '';
    let searchResults: SearchUser[] = [];
    let searching = false;
    let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
    let selectedUser: SearchUser | null = null;
    let newRole: 'OWNER' | 'EDITOR' | 'VIEWER' = 'VIEWER';
    let newSharePercent: number = 0;
    let showRoleDropdown = false;

    // Edit state
    let editingUserId: number | null = null;
    let editRole: 'OWNER' | 'EDITOR' | 'VIEWER' = 'VIEWER';
    let editSharePercent: number = 0;
    let showEditRoleDropdown = false;

    // Confirm dialogs
    let confirmRemoveOpen = false;
    let confirmRemoveUsername = '';
    let confirmRemoveUserId: number | null = null;
    let confirmCloseOpen = false;

    // Chart
    let chartContainer: HTMLDivElement;
    let chartInstance: echarts.ECharts | null = null;

    // =========================================================================
    // Computed
    // =========================================================================
    $: owners = accesses.filter(a => a.role === 'OWNER');
    $: editors = accesses.filter(a => a.role === 'EDITOR');
    $: viewers = accesses.filter(a => a.role === 'VIEWER');
    $: totalAllocated = owners.reduce((sum, o) => sum + o.share_percentage, 0);
    $: totalAllocatedPercent = Math.round(totalAllocated * 10000) / 100;
    $: availablePercent = Math.round((1 - totalAllocated) * 10000) / 100;
    $: exceedsLimit = totalAllocated > 1.0001; // small epsilon for floating point
    $: hasChanges = JSON.stringify(accesses.map(a => ({
        user_id: a.user_id, role: a.role, share_percentage: a.share_percentage
    }))) !== JSON.stringify(originalAccesses.map(a => ({
        user_id: a.user_id, role: a.role, share_percentage: a.share_percentage
    })));
    $: existingUserIds = new Set(accesses.map(a => a.user_id));

    // For add form: max share available
    $: maxNewShare = newRole === 'OWNER' ? Math.max(0, Math.round((1 - totalAllocated) * 10000) / 100) : 0;

    // =========================================================================
    // Lifecycle
    // =========================================================================
    $: if (open) {
        loadAccesses();
    }

    $: if (open && chartContainer && !loading) {
        tick().then(renderChart);
    }

    $: if (!loading && accesses) {
        tick().then(renderChart);
    }

    onMount(() => {
        return () => {
            if (chartInstance) {
                chartInstance.dispose();
                chartInstance = null;
            }
        };
    });

    // =========================================================================
    // Data Loading
    // =========================================================================
    async function loadAccesses() {
        loading = true;
        error = null;
        successMessage = null;
        showAddForm = false;
        editingUserId = null;

        try {
            const response = await zodiosApi.list_broker_access_api_v1_brokers__broker_id__access_get({
                params: {broker_id: brokerId}
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
    // ECharts - Half Donut
    // =========================================================================
    function renderChart() {
        if (!chartContainer) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
        }

        const isDark = document.documentElement.classList.contains('dark');

        // Build data: one slice per OWNER with share > 0, plus "Available"
        const data: Array<{value: number; name: string; itemStyle?: any}> = [];
        const colors: string[] = [];
        const ownerColors = ['#1a4031', '#2d6a4f', '#40916c', '#52b788', '#74c69d', '#95d5b2'];

        owners.forEach((owner, i) => {
            const pct = Math.round(owner.share_percentage * 10000) / 100;
            if (pct > 0) {
                data.push({
                    value: pct,
                    name: owner.username + ' (' + pct.toFixed(1) + '%)',
                });
                colors.push(ownerColors[i % ownerColors.length]);
            }
        });

        const avail = Math.max(0, Math.round((1 - totalAllocated) * 10000) / 100);
        if (avail > 0.01) {
            data.push({
                value: avail,
                name: $_('brokers.sharing.available') + ' (' + avail.toFixed(1) + '%)',
                itemStyle: {
                    color: isDark ? 'rgba(100,116,139,0.3)' : 'rgba(203,213,225,0.5)',
                },
            });
        }

        // If no data at all (edge case)
        if (data.length === 0) {
            data.push({
                value: 100,
                name: $_('brokers.sharing.available') + ' (100%)',
                itemStyle: {color: isDark ? 'rgba(100,116,139,0.3)' : 'rgba(203,213,225,0.5)'},
            });
        }

        const option: echarts.EChartsOption = {
            color: colors.length > 0 ? colors : ['#cbd5e1'],
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c}%',
                backgroundColor: isDark ? '#1e293b' : '#fff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b'},
            },
            series: [
                {
                    type: 'pie',
                    radius: ['50%', '80%'],
                    center: ['50%', '75%'],
                    startAngle: 180,
                    endAngle: 360,
                    label: {show: false},
                    emphasis: {
                        label: {show: false},
                        scaleSize: 4,
                    },
                    data: data,
                },
            ],
        };

        chartInstance.setOption(option, true);
        chartInstance.resize();
    }

    // =========================================================================
    // User Search (debounced)
    // =========================================================================
    function handleSearchInput() {
        if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
        searchResults = [];

        if (searchQuery.length < 2) {
            searching = false;
            return;
        }

        searching = true;
        searchDebounceTimer = setTimeout(async () => {
            try {
                const response = await zodiosApi.search_users_endpoint_api_v1_users_search_get({
                    queries: {q: searchQuery, exclude_broker_id: brokerId}
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
            } catch {
                searchResults = [];
            } finally {
                searching = false;
            }
        }, 300);
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

        accesses = [...accesses, {
            user_id: selectedUser.id,
            username: selectedUser.username,
            avatar_url: selectedUser.avatar_url,
            role: newRole,
            share_percentage: shareVal,
            isNew: true,
        }];

        // Reset form
        selectedUser = null;
        searchQuery = '';
        newRole = 'VIEWER';
        newSharePercent = 0;
        showAddForm = false;
    }

    // =========================================================================
    // Edit User (local)
    // =========================================================================
    function startEdit(entry: AccessEntry) {
        editingUserId = entry.user_id;
        editRole = entry.role;
        editSharePercent = Math.round(entry.share_percentage * 10000) / 100;
        showEditRoleDropdown = false;
    }

    function saveEdit() {
        if (editingUserId === null) return;

        accesses = accesses.map(a => {
            if (a.user_id !== editingUserId) return a;
            const share = editRole === 'OWNER' ? editSharePercent / 100 : 0;
            return {...a, role: editRole, share_percentage: share};
        });
        editingUserId = null;
    }

    function cancelEdit() {
        editingUserId = null;
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
        accesses = accesses.filter(a => a.user_id !== confirmRemoveUserId);
        confirmRemoveOpen = false;
        confirmRemoveUserId = null;
    }

    // =========================================================================
    // Save (batch PUT)
    // =========================================================================
    async function handleSave() {
        saving = true;
        error = null;
        successMessage = null;

        try {
            const body = accesses.map(a => ({
                user_id: a.user_id,
                role: a.role,
                share_percentage: a.share_percentage,
            }));

            await zodiosApi.bulk_update_broker_access_api_v1_brokers__broker_id__access_put(
                body,
                {params: {broker_id: brokerId}}
            );

            successMessage = $_('brokers.sharing.saved');
            originalAccesses = JSON.parse(JSON.stringify(accesses));
            onChanged?.();

            // Auto-dismiss success after 3s
            setTimeout(() => {
                successMessage = null;
            }, 3000);
        } catch (e: any) {
            const detail = e?.response?.data?.detail || e?.message || 'Unknown error';
            error = $_('brokers.sharing.saveFailed') + ': ' + detail;
        } finally {
            saving = false;
        }
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
        showAddForm = false;
        editingUserId = null;
        if (chartInstance) {
            chartInstance.dispose();
            chartInstance = null;
        }
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
        switch (role) {
            case 'OWNER': return Crown;
            case 'EDITOR': return Pencil;
            case 'VIEWER': return Eye;
            default: return Users;
        }
    }

    function getRoleLabel(role: string): string {
        switch (role) {
            case 'OWNER': return $_('brokers.sharing.roleOwner');
            case 'EDITOR': return $_('brokers.sharing.roleEditor');
            case 'VIEWER': return $_('brokers.sharing.roleViewer');
            default: return role;
        }
    }

    function getRoleBadgeClass(role: string): string {
        switch (role) {
            case 'OWNER': return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
            case 'EDITOR': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
            case 'VIEWER': return 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-300';
            default: return 'bg-gray-100 text-gray-600';
        }
    }

    function getAvatarInitial(username: string): string {
        return username ? username.charAt(0).toUpperCase() : '?';
    }

    const roleOptions: Array<{value: 'OWNER' | 'EDITOR' | 'VIEWER'; label: string}> = [
        {value: 'OWNER', label: ''},
        {value: 'EDITOR', label: ''},
        {value: 'VIEWER', label: ''},
    ];
    // Reactive labels
    $: roleOptions[0].label = $_('brokers.sharing.roleOwner');
    $: roleOptions[1].label = $_('brokers.sharing.roleEditor');
    $: roleOptions[2].label = $_('brokers.sharing.roleViewer');
</script>

<ModalBase
    {open}
    zIndex={50}
    maxWidth="2xl"
    onRequestClose={handleRequestClose}
    testId="broker-sharing-modal"
>
    <div class="bg-white dark:bg-slate-800 rounded-xl w-full flex flex-col max-h-[85vh]">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700 shrink-0">
            <div class="flex items-center gap-2">
                <Users size={20} class="text-libre-green" />
                <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {$_('brokers.sharing.title')} — {brokerName}
                </h2>
            </div>
            <div class="flex items-center gap-2">
                {#if hasChanges}
                    <button
                        type="button"
                        on:click={() => { accesses = JSON.parse(JSON.stringify(originalAccesses)); }}
                        class="p-1.5 text-amber-500 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
                        title="Reset"
                    >
                        <RotateCcw size={18} />
                    </button>
                {/if}
                <button
                    type="button"
                    on:click={handleRequestClose}
                    class="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg transition-colors"
                >
                    <X size={20} />
                </button>
            </div>
        </div>

        <!-- Body (scrollable) -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4">
            <!-- Warning Banner -->
            {#if exceedsLimit}
                <div class="flex items-center gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg text-amber-800 dark:text-amber-300 text-sm">
                    <AlertTriangle size={16} class="shrink-0" />
                    <span>{$_('brokers.sharing.percentageWarning')}</span>
                </div>
            {/if}

            <!-- Error / Success banners -->
            <ErrorBanner message={error} on:dismiss={() => error = null} />
            {#if successMessage}
                <div class="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-green-700 dark:text-green-300 text-sm">
                    <Check size={16} class="shrink-0" />
                    <span>{successMessage}</span>
                </div>
            {/if}

            {#if loading}
                <div class="flex items-center justify-center py-12">
                    <Loader2 size={32} class="animate-spin text-libre-green" />
                </div>
            {:else}
                <!-- Ownership Chart + Center Info -->
                <div class="relative" data-testid="ownership-chart-section">
                    <div bind:this={chartContainer} class="w-full" style="height: 200px;"></div>
                    <!-- Center overlay: Allocated / Available + Add button -->
                    <div class="absolute bottom-2 left-1/2 -translate-x-1/2 text-center pointer-events-none">
                        <div class="text-xs text-gray-500 dark:text-gray-400">
                            {$_('brokers.sharing.allocated')}: <span class="font-semibold text-gray-700 dark:text-gray-200">{totalAllocatedPercent.toFixed(1)}%</span>
                        </div>
                        <div class="text-xs text-gray-500 dark:text-gray-400">
                            {$_('brokers.sharing.available')}: <span class="font-semibold text-gray-700 dark:text-gray-200">{availablePercent.toFixed(1)}%</span>
                        </div>
                        <button
                            type="button"
                            class="mt-1 pointer-events-auto inline-flex items-center justify-center w-7 h-7 rounded-full bg-libre-green text-white hover:bg-libre-green/90 transition-colors shadow-sm"
                            on:click={() => { showAddForm = true; selectedUser = null; searchQuery = ''; newRole = 'VIEWER'; newSharePercent = 0; }}
                            title={$_('brokers.sharing.addUser')}
                            data-testid="sharing-add-user-btn"
                        >
                            <Plus size={16} />
                        </button>
                    </div>
                </div>

                <!-- Owners Section -->
                {#if owners.length > 0}
                    <div>
                        <h3 class="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-1.5">
                            <Crown size={14} class="text-amber-500" />
                            {$_('brokers.sharing.owners')}
                        </h3>
                        <div class="space-y-2">
                            {#each owners as entry (entry.user_id)}
                                {@const isEditing = editingUserId === entry.user_id}
                                <div class="flex items-center gap-3 p-2.5 bg-gray-50 dark:bg-slate-700/50 rounded-lg" data-testid="access-entry-{entry.user_id}">
                                    <!-- Avatar -->
                                    <div class="w-8 h-8 rounded-full overflow-hidden bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center shrink-0">
                                        {#if entry.avatar_url}
                                            <LazyImage
                                                src="{entry.avatar_url}?img_preview=48x48"
                                                alt={entry.username}
                                                circle
                                                
                                            />
                                        {:else}
                                            <span class="text-sm font-semibold text-amber-700 dark:text-amber-300">{getAvatarInitial(entry.username)}</span>
                                        {/if}
                                    </div>

                                    {#if isEditing}
                                        <!-- Edit mode -->
                                        <div class="flex-1 min-w-0 flex flex-col sm:flex-row sm:items-center gap-2">
                                            <span class="font-medium text-sm text-gray-800 dark:text-gray-200 truncate">{entry.username}</span>
                                            <div class="flex items-center gap-2">
                                                <!-- Role selector -->
                                                <div class="relative">
                                                    <button
                                                        type="button"
                                                        class="flex items-center gap-1 px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200"
                                                        on:click={() => showEditRoleDropdown = !showEditRoleDropdown}
                                                    >
                                                        <svelte:component this={getRoleIcon(editRole)} size={12} />
                                                        {editRole}
                                                        <ChevronDown size={12} />
                                                    </button>
                                                    {#if showEditRoleDropdown}
                                                        <div class="absolute z-10 mt-1 w-48 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg py-1">
                                                            {#each roleOptions as opt}
                                                                <button
                                                                    type="button"
                                                                    class="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-100 dark:hover:bg-slate-600 text-gray-700 dark:text-gray-200"
                                                                    on:click={() => { editRole = opt.value; showEditRoleDropdown = false; if (opt.value !== 'OWNER') editSharePercent = 0; }}
                                                                >
                                                                    {opt.label}
                                                                </button>
                                                            {/each}
                                                        </div>
                                                    {/if}
                                                </div>
                                                <!-- Share % input (only for OWNER) -->
                                                {#if editRole === 'OWNER'}
                                                    <div class="flex items-center gap-1">
                                                        <input
                                                            type="number"
                                                            min="0"
                                                            max="100"
                                                            step="0.1"
                                                            bind:value={editSharePercent}
                                                            class="w-16 px-1.5 py-1 text-xs text-center border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200"
                                                        />
                                                        <span class="text-xs text-gray-500">%</span>
                                                    </div>
                                                {/if}
                                            </div>
                                        </div>
                                        <div class="flex items-center gap-1 shrink-0">
                                            <button type="button" on:click={saveEdit} class="p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded" title="Save">
                                                <Check size={16} />
                                            </button>
                                            <button type="button" on:click={cancelEdit} class="p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 rounded" title="Cancel">
                                                <X size={16} />
                                            </button>
                                        </div>
                                    {:else}
                                        <!-- View mode -->
                                        <div class="flex-1 min-w-0">
                                            <span class="font-medium text-sm text-gray-800 dark:text-gray-200 truncate block">{entry.username}</span>
                                            <div class="flex items-center gap-2 mt-0.5">
                                                <span class="text-xs px-1.5 py-0.5 rounded-full {getRoleBadgeClass(entry.role)}">
                                                    {entry.role}
                                                </span>
                                                {#if entry.share_percentage > 0}
                                                    <span class="text-xs text-gray-500 dark:text-gray-400">
                                                        {(Math.round(entry.share_percentage * 10000) / 100).toFixed(1)}%
                                                    </span>
                                                {/if}
                                            </div>
                                        </div>
                                        <div class="flex items-center gap-1 shrink-0">
                                            <button type="button" on:click={() => startEdit(entry)} class="p-1 text-gray-400 hover:text-libre-green hover:bg-libre-green/10 rounded transition-colors" title="Edit">
                                                <Pencil size={14} />
                                            </button>
                                            <button type="button" on:click={() => requestRemove(entry)} class="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors" title="Remove">
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Editors Section -->
                {#if editors.length > 0}
                    <div>
                        <h3 class="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-1.5">
                            <Pencil size={14} class="text-blue-500" />
                            {$_('brokers.sharing.editors')}
                        </h3>
                        <div class="flex flex-wrap gap-2">
                            {#each editors as entry (entry.user_id)}
                                <div class="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-full text-sm" data-testid="access-entry-{entry.user_id}">
                                    <!-- Avatar mini -->
                                    <div class="w-5 h-5 rounded-full overflow-hidden bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                                        {#if entry.avatar_url}
                                            <LazyImage
                                                src="{entry.avatar_url}?img_preview=32x32"
                                                alt={entry.username}
                                                circle
                                                
                                            />
                                        {:else}
                                            <span class="text-[10px] font-semibold text-blue-700 dark:text-blue-300">{getAvatarInitial(entry.username)}</span>
                                        {/if}
                                    </div>
                                    <span class="text-blue-800 dark:text-blue-200 font-medium">{entry.username}</span>
                                    <button type="button" on:click={() => startEdit(entry)} class="p-0.5 text-blue-400 hover:text-blue-600 rounded" title="Edit">
                                        <Pencil size={12} />
                                    </button>
                                    <button type="button" on:click={() => requestRemove(entry)} class="p-0.5 text-blue-400 hover:text-red-500 rounded" title="Remove">
                                        <Minus size={12} />
                                    </button>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Viewers Section -->
                {#if viewers.length > 0}
                    <div>
                        <h3 class="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-1.5">
                            <Eye size={14} class="text-gray-400" />
                            {$_('brokers.sharing.viewers')}
                        </h3>
                        <div class="flex flex-wrap gap-2">
                            {#each viewers as entry (entry.user_id)}
                                <div class="flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded-full text-sm" data-testid="access-entry-{entry.user_id}">
                                    <div class="w-5 h-5 rounded-full overflow-hidden bg-gray-200 dark:bg-slate-600 flex items-center justify-center">
                                        {#if entry.avatar_url}
                                            <LazyImage
                                                src="{entry.avatar_url}?img_preview=32x32"
                                                alt={entry.username}
                                                circle
                                                
                                            />
                                        {:else}
                                            <span class="text-[10px] font-semibold text-gray-500 dark:text-gray-400">{getAvatarInitial(entry.username)}</span>
                                        {/if}
                                    </div>
                                    <span class="text-gray-700 dark:text-gray-300 font-medium">{entry.username}</span>
                                    <button type="button" on:click={() => startEdit(entry)} class="p-0.5 text-gray-400 hover:text-gray-600 rounded" title="Edit">
                                        <Pencil size={12} />
                                    </button>
                                    <button type="button" on:click={() => requestRemove(entry)} class="p-0.5 text-gray-400 hover:text-red-500 rounded" title="Remove">
                                        <Minus size={12} />
                                    </button>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Edit inline panel (for Editor/Viewer editing) -->
                {#if editingUserId !== null && !owners.some(o => o.user_id === editingUserId)}
                    {@const editEntry = accesses.find(a => a.user_id === editingUserId)}
                    {#if editEntry}
                        <div class="p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-200 dark:border-slate-600">
                            <div class="flex items-center justify-between mb-2">
                                <span class="text-sm font-medium text-gray-700 dark:text-gray-200">{$_('common.edit')}: {editEntry.username}</span>
                                <div class="flex gap-1">
                                    <button type="button" on:click={saveEdit} class="p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"><Check size={16} /></button>
                                    <button type="button" on:click={cancelEdit} class="p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 rounded"><X size={16} /></button>
                                </div>
                            </div>
                            <div class="flex items-center gap-3">
                                <span class="text-xs text-gray-500 dark:text-gray-400">{$_('brokers.sharing.role')}:</span>
                                <div class="relative">
                                    <button
                                        type="button"
                                        class="flex items-center gap-1 px-2 py-1 text-xs rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200"
                                        on:click={() => showEditRoleDropdown = !showEditRoleDropdown}
                                    >
                                        <svelte:component this={getRoleIcon(editRole)} size={12} />
                                        {editRole}
                                        <ChevronDown size={12} />
                                    </button>
                                    {#if showEditRoleDropdown}
                                        <div class="absolute z-10 mt-1 w-48 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg py-1">
                                            {#each roleOptions as opt}
                                                <button
                                                    type="button"
                                                    class="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-100 dark:hover:bg-slate-600 text-gray-700 dark:text-gray-200"
                                                    on:click={() => { editRole = opt.value; showEditRoleDropdown = false; if (opt.value !== 'OWNER') editSharePercent = 0; }}
                                                >
                                                    {opt.label}
                                                </button>
                                            {/each}
                                        </div>
                                    {/if}
                                </div>
                                {#if editRole === 'OWNER'}
                                    <span class="text-xs text-gray-500 dark:text-gray-400">{$_('brokers.sharing.sharePercentage')}:</span>
                                    <div class="flex items-center gap-1">
                                        <input type="number" min="0" max="100" step="0.1" bind:value={editSharePercent}
                                               class="w-16 px-1.5 py-1 text-xs text-center border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200" />
                                        <span class="text-xs text-gray-500">%</span>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    {/if}
                {/if}

                <!-- Add User Form -->
                {#if showAddForm}
                    <div class="p-3 bg-libre-green/5 dark:bg-libre-green/10 rounded-lg border border-libre-green/20 dark:border-libre-green/30" data-testid="sharing-add-form">
                        <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">{$_('brokers.sharing.addUser')}</h4>

                        <!-- Search user -->
                        <div class="relative mb-3">
                            <div class="flex items-center gap-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 px-3 py-2">
                                <Search size={16} class="text-gray-400 shrink-0" />
                                <input
                                    type="text"
                                    bind:value={searchQuery}
                                    on:input={handleSearchInput}
                                    placeholder={$_('brokers.sharing.searchPlaceholder')}
                                    class="flex-1 bg-transparent text-sm text-gray-700 dark:text-gray-200 outline-none placeholder-gray-400"
                                    data-testid="sharing-search-input"
                                />
                                {#if searching}
                                    <Loader2 size={14} class="animate-spin text-gray-400" />
                                {/if}
                            </div>

                            <!-- Search results dropdown -->
                            {#if searchResults.length > 0}
                                <div class="absolute z-10 mt-1 w-full max-h-48 overflow-y-auto bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg py-1">
                                    {#each searchResults as user}
                                        <button
                                            type="button"
                                            class="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-slate-600 text-sm"
                                            on:click={() => selectSearchUser(user)}
                                        >
                                            <span class="w-6 h-6 rounded-full overflow-hidden bg-gray-200 dark:bg-slate-600 flex items-center justify-center shrink-0">
                                                {#if user.avatar_url}
                                                    <LazyImage
                                                        src="{user.avatar_url}?img_preview=32x32"
                                                        alt={user.username}
                                                        circle
                                                        
                                                    />
                                                {:else}
                                                    <span class="text-[10px] font-semibold text-gray-500 dark:text-gray-400">{getAvatarInitial(user.username)}</span>
                                                {/if}
                                            </span>
                                            <span class="text-gray-700 dark:text-gray-200">{user.username}</span>
                                        </button>
                                    {/each}
                                </div>
                            {:else if searchQuery.length >= 2 && !searching && !selectedUser}
                                <div class="absolute z-10 mt-1 w-full bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg py-3 text-center text-sm text-gray-400">
                                    {$_('brokers.sharing.noOtherUsers')}
                                </div>
                            {/if}
                        </div>

                        {#if selectedUser}
                            <div class="flex items-center gap-2 mb-3 p-2 bg-white dark:bg-slate-700 rounded-lg border border-gray-200 dark:border-slate-600">
                                <div class="w-6 h-6 rounded-full overflow-hidden bg-gray-200 dark:bg-slate-600 flex items-center justify-center shrink-0">
                                    {#if selectedUser.avatar_url}
                                        <LazyImage
                                            src="{selectedUser.avatar_url}?img_preview=32x32"
                                            alt={selectedUser.username}
                                            circle
                                            
                                        />
                                    {:else}
                                        <span class="text-[10px] font-semibold text-gray-500">{getAvatarInitial(selectedUser.username)}</span>
                                    {/if}
                                </div>
                                <span class="text-sm font-medium text-gray-700 dark:text-gray-200 flex-1">{selectedUser.username}</span>
                                <button type="button" on:click={() => { selectedUser = null; searchQuery = ''; }} class="p-0.5 text-gray-400 hover:text-gray-600">
                                    <X size={14} />
                                </button>
                            </div>
                        {/if}

                        <!-- Role + Share % -->
                        <div class="flex flex-col sm:flex-row sm:items-center gap-3 mb-3">
                            <div class="flex items-center gap-2">
                                <span class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{$_('brokers.sharing.role')}:</span>
                                <div class="relative">
                                    <button
                                        type="button"
                                        class="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-600"
                                        on:click={() => showRoleDropdown = !showRoleDropdown}
                                    >
                                        <svelte:component this={getRoleIcon(newRole)} size={12} />
                                        {newRole}
                                        <ChevronDown size={12} />
                                    </button>
                                    {#if showRoleDropdown}
                                        <div class="absolute z-10 mt-1 w-48 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg py-1">
                                            {#each roleOptions as opt}
                                                <button
                                                    type="button"
                                                    class="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-100 dark:hover:bg-slate-600 text-gray-700 dark:text-gray-200"
                                                    on:click={() => { newRole = opt.value; showRoleDropdown = false; if (opt.value !== 'OWNER') newSharePercent = 0; }}
                                                >
                                                    {opt.label}
                                                </button>
                                            {/each}
                                        </div>
                                    {/if}
                                </div>
                            </div>

                            {#if newRole === 'OWNER'}
                                <div class="flex items-center gap-2">
                                    <span class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{$_('brokers.sharing.sharePercentage')}:</span>
                                    <div class="flex items-center gap-1">
                                        <input
                                            type="number"
                                            min="0"
                                            max={maxNewShare}
                                            step="0.1"
                                            bind:value={newSharePercent}
                                            class="w-16 px-1.5 py-1 text-xs text-center border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200"
                                        />
                                        <span class="text-xs text-gray-500">% (max {maxNewShare.toFixed(1)}%)</span>
                                    </div>
                                </div>
                            {/if}
                        </div>

                        <!-- Actions -->
                        <div class="flex items-center justify-end gap-2">
                            <button
                                type="button"
                                on:click={() => { showAddForm = false; selectedUser = null; searchQuery = ''; }}
                                class="px-3 py-1.5 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg transition-colors"
                            >
                                {$_('common.cancel')}
                            </button>
                            <button
                                type="button"
                                on:click={handleAddUser}
                                disabled={!selectedUser}
                                class="flex items-center gap-1 px-3 py-1.5 text-xs bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                data-testid="sharing-confirm-add"
                            >
                                <Plus size={14} />
                                {$_('brokers.sharing.addUser')}
                            </button>
                        </div>
                    </div>
                {/if}

                <!-- Role Legend -->
                <div class="text-xs text-gray-400 dark:text-gray-500 space-y-0.5 pt-2 border-t border-gray-100 dark:border-slate-700">
                    <div class="flex items-center gap-1.5"><Crown size={11} class="text-amber-500" /> {$_('brokers.sharing.roleOwner')}</div>
                    <div class="flex items-center gap-1.5"><Pencil size={11} class="text-blue-500" /> {$_('brokers.sharing.roleEditor')}</div>
                    <div class="flex items-center gap-1.5"><Eye size={11} class="text-gray-400" /> {$_('brokers.sharing.roleViewer')}</div>
                </div>
            {/if}
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-slate-700 shrink-0">
            <button
                type="button"
                on:click={handleRequestClose}
                class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
                {$_('common.cancel')}
            </button>
            <button
                type="button"
                on:click={handleSave}
                disabled={!hasChanges || saving}
                class="flex items-center gap-2 px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="sharing-save-btn"
            >
                {#if saving}
                    <Loader2 size={16} class="animate-spin" />
                {:else}
                    <Save size={16} />
                {/if}
                {$_('brokers.sharing.save')}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Confirm Remove Dialog -->
<ConfirmModal
    open={confirmRemoveOpen}
    title={$_('brokers.sharing.remove')}
    message={$_('brokers.sharing.removeConfirm').replace('{username}', confirmRemoveUsername)}
    danger={true}
    onConfirm={confirmRemove}
    onCancel={() => { confirmRemoveOpen = false; confirmRemoveUserId = null; }}
    zIndex={60}
/>

<!-- Confirm Discard Changes Dialog -->
<ConfirmModal
    open={confirmCloseOpen}
    title={$_('brokers.discardChanges')}
    message={$_('brokers.unsavedChanges')}
    confirmText={$_('brokers.discardAndClose')}
    danger={false}
    onConfirm={confirmDiscard}
    onCancel={() => confirmCloseOpen = false}
    zIndex={60}
/>

