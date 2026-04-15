<script lang="ts">
    import {_, LANGUAGE_OPTIONS} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {isAxiosError} from 'axios';
    import {onDestroy, onMount} from 'svelte';
    import {debug} from '$lib/debug';
    import {ChevronDown, ChevronRight, Clock, FileUp, Lock, RotateCcw, Save, Shield, ShieldOff, Undo, Unlock, Users} from 'lucide-svelte';
    import {CurrencySearchSelect, type SelectOption, SimpleSelect} from '$lib/components/ui/select';
    import type {GlobalSetting} from '$lib/types';
    import {globalSettings} from '$lib/stores/globalSettings';
    import LoadingSpinner from '$lib/components/ui/LoadingSpinner.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import SettingToggle from '$lib/components/settings/SettingToggle.svelte';
    import SettingNumber from '$lib/components/settings/SettingNumber.svelte';

    // Props
    export let canEdit: boolean = false;


    // Default values for global settings
    const SETTING_DEFAULTS: Record<string, string> = {
        session_ttl_hours: '24',
        enable_registration: 'true',
        require_email_verification: 'false',
        max_file_upload_mb: '10',
        auto_sync_fx_rates: 'true',
        auto_sync_prices: 'true',
        price_sync_interval_hours: '6',
        default_currency: 'EUR',
        default_language: 'en',
    };

    // Category definitions with icons
    interface Category {
        id: string;
        icon: any;
        keys: string[];
    }

    const categories: Category[] = [
        {id: 'session', icon: Clock, keys: ['session_ttl_hours']},
        {id: 'security', icon: Shield, keys: ['enable_registration', 'require_email_verification']},
        {id: 'sync', icon: FileUp, keys: ['auto_sync_fx_rates', 'auto_sync_prices', 'price_sync_interval_hours', 'max_file_upload_mb']},
        {id: 'defaults', icon: Users, keys: ['default_currency', 'default_language']},
    ];

    let settings: GlobalSetting[] = [];
    let editedValues: Record<string, string> = {};
    let isLocked = true;
    let isLoading = true;
    let isSaving = false;
    let error: string | null = null;
    let success: string | null = null;
    let selectedCategory: string = 'all';


    // Language options for dropdown
    const languageOptions: SelectOption[] = LANGUAGE_OPTIONS.map(l => ({
        value: l.code,
        label: l.name,
        icon: l.flag
    }));

    onMount(async () => {
        debug.log('GlobalSettingsTab', 'onMount');
        await loadSettings();
    });

    async function loadSettings() {
        debug.log('GlobalSettingsTab', 'loadSettings');
        isLoading = true;
        error = null;
        try {
            const response = await zodiosApi.list_global_settings_api_v1_settings_global_get();
            debug.log('GlobalSettingsTab', 'loadSettings response', (response.items || []).length);
            settings = (response.items || []) as GlobalSetting[];
            // Initialize edited values
            editedValues = {};
            for (const setting of settings) {
                editedValues[setting.key] = setting.value;
            }
        } catch (e) {
            if (isAxiosError(e)) {
                error = e.message;
            } else {
                error = 'Failed to load settings';
            }
        } finally {
            isLoading = false;
        }
    }

    // Single setting actions
    async function saveSetting(key: string) {
        isSaving = true;
        error = null;
        success = null;
        try {
            await zodiosApi.update_global_setting_endpoint_api_v1_settings_global__key__put({value: editedValues[key]}, {params: {key}});
            // Update local state
            const setting = settings.find(s => s.key === key);
            if (setting) {
                setting.value = editedValues[key];
            }
            // Trigger reactivity
            settings = [...settings];

            // Sync globalSettings store
            syncGlobalSettingsStore();

            const label = getSettingLabel(key);
            success = `"${label}" ${$_('settings.savedSuccessfully')}`;
            setTimeout(() => success = null, 3000);
        } catch (e) {
            if (isAxiosError(e)) {
                if (e.response?.status === 403) {
                    error = $_('settings.adminRequired');
                } else {
                    error = e.message;
                }
            } else {
                error = $_('settings.saveFailed');
            }
        } finally {
            isSaving = false;
        }
    }

    function undoSetting(key: string) {
        const setting = settings.find(s => s.key === key);
        if (setting) {
            editedValues[key] = setting.value;
            editedValues = {...editedValues}; // Trigger reactivity
        }
    }

    function resetSettingToDefault(key: string) {
        if (SETTING_DEFAULTS[key] !== undefined) {
            editedValues[key] = SETTING_DEFAULTS[key];
            editedValues = {...editedValues}; // Trigger reactivity
        }
    }

    // Bulk actions
    async function saveAll() {
        const keysToSave = settings.filter(s => changedKeys.includes(s.key)).map(s => s.key);
        const savedLabels: string[] = [];

        for (const key of keysToSave) {
            isSaving = true;
            error = null;
            try {
                await zodiosApi.update_global_setting_endpoint_api_v1_settings_global__key__put({value: editedValues[key]}, {params: {key}});
                // Update local state
                const setting = settings.find(s => s.key === key);
                if (setting) {
                    setting.value = editedValues[key];
                }
                savedLabels.push(getSettingLabel(key));
            } catch (e) {
                if (isAxiosError(e)) {
                    if (e.response?.status === 403) {
                        error = $_('settings.adminRequired');
                    } else {
                        error = e.message;
                    }
                } else {
                    error = $_('settings.saveFailed');
                }
                break; // Stop on first error
            }
        }

        // Trigger reactivity
        settings = [...settings];
        isSaving = false;

        if (savedLabels.length > 0 && !error) {
            // Sync globalSettings store
            syncGlobalSettingsStore();

            success = `${$_('settings.savedSuccessfully')}:\n• ${savedLabels.join('\n• ')}`;
            setTimeout(() => success = null, 4000);
        }
    }

    function undoAll() {
        for (const setting of settings) {
            editedValues[setting.key] = setting.value;
        }
        editedValues = {...editedValues}; // Trigger reactivity
    }

    function resetAllToDefaults() {
        for (const key of Object.keys(editedValues)) {
            if (SETTING_DEFAULTS[key] !== undefined) {
                editedValues[key] = SETTING_DEFAULTS[key];
            }
        }
        editedValues = {...editedValues}; // Trigger reactivity
    }

    /**
     * Sync current editedValues to the globalSettings store
     * This ensures other components see the updated values immediately
     */
    function syncGlobalSettingsStore() {
        globalSettings.setDirect({
            default_language: editedValues['default_language'] || 'en',
            default_currency: editedValues['default_currency'] || 'EUR',
            default_theme: editedValues['default_theme'] || 'auto',
            session_ttl_hours: parseInt(editedValues['session_ttl_hours'] || '24', 10),
            auto_sync_fx_rates: editedValues['auto_sync_fx_rates'] === 'true',
            auto_sync_prices: editedValues['auto_sync_prices'] === 'true',
            price_sync_interval_hours: parseInt(editedValues['price_sync_interval_hours'] || '24', 10),
            max_file_upload_mb: parseInt(editedValues['max_file_upload_mb'] || '10', 10)
        });
    }

    // Override map: backend setting keys whose label already exists under settings.*
    const SETTING_LABEL_OVERRIDES: Record<string, string> = {
        default_currency: 'settings.defaultCurrency',
    };

    // Override map: category ids whose label already exists under settings.*
    const CATEGORY_LABEL_OVERRIDES: Record<string, string> = {
        security: 'settings.security',
        all: 'settings.all',
    };

    function getSettingLabel(key: string): string {
        // Check override first (collapsed duplicates)
        if (SETTING_LABEL_OVERRIDES[key]) {
            return $_(SETTING_LABEL_OVERRIDES[key]);
        }
        // Try to get localized name, fallback to key
        const localizedKey = `settings.globalSettingNames.${key}`;
        const localized = $_(localizedKey);
        return localized !== localizedKey ? localized : key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    function getCategoryLabel(id: string): string {
        if (CATEGORY_LABEL_OVERRIDES[id]) {
            return $_(CATEGORY_LABEL_OVERRIDES[id]);
        }
        const key = `settings.globalSettingCategories.${id}`;
        const localized = $_(key);
        return localized !== key ? localized : id.replace(/\b\w/g, l => l.toUpperCase());
    }

    function getSettingUnit(key: string): string {
        const localizedKey = `settings.globalSettingUnits.${key}`;
        const localized = $_(localizedKey);
        return localized !== localizedKey ? localized : '';
    }

    function getSettingHint(key: string): string {
        const localizedKey = `settings.globalSettingDescriptions.${key}`;
        const localized = $_(localizedKey);
        return localized !== localizedKey ? localized : '';
    }

    function getCategoryForSetting(key: string): Category | undefined {
        return categories.find(c => c.keys.includes(key));
    }

    // Reactive: compute changed keys based on editedValues
    $: changedKeys = settings
        .filter(s => s.value !== editedValues[s.key])
        .map(s => s.key);

    // Reactive: check if any setting has changes
    $: hasAnyChanges = changedKeys.length > 0;

    // Reactive: compute non-default keys
    $: nonDefaultKeys = Object.keys(editedValues)
        .filter(key => SETTING_DEFAULTS[key] !== undefined && editedValues[key] !== SETTING_DEFAULTS[key]);

    // Reactive: check if any setting differs from default
    $: hasAnyNonDefault = nonDefaultKeys.length > 0;

    // Toggle lock with confirmation if there are pending changes
    function toggleLock() {
        if (!isLocked) {
            // Trying to lock - check for pending changes
            if (hasAnyChanges) {
                const confirmed = confirm($_('settings.discardChangesConfirm'));
                if (!confirmed) return;
            }
            undoAll();
        }
        isLocked = !isLocked;
    }

    // Reactive: filter settings based on selected category
    $: filteredSettings = selectedCategory === 'all'
        ? settings
        : settings.filter(s => {
            const category = categories.find(c => c.id === selectedCategory);
            return category ? category.keys.includes(s.key) : true;
        });

    // Mobile dropdown state
    let showDropdown = false;
    let dropdownRef: HTMLDivElement | null = null;

    // Get selected category label for mobile display
    $: selectedCategoryLabel = getCategoryLabel(selectedCategory);

    // Get selected category icon
    $: selectedCategoryIcon = selectedCategory === 'all'
        ? null
        : categories.find(c => c.id === selectedCategory)?.icon || null;

    function toggleDropdown() {
        showDropdown = !showDropdown;
    }

    function selectCategoryMobile(id: string) {
        selectedCategory = id;
        showDropdown = false;
    }

    // Close dropdown on click outside
    function handleClickOutside(event: MouseEvent) {
        if (dropdownRef && !dropdownRef.contains(event.target as Node)) {
            showDropdown = false;
        }
    }

    onMount(() => {
        document.addEventListener('click', handleClickOutside);
    });

    onDestroy(() => {
        document.removeEventListener('click', handleClickOutside);
    });
</script>

<!-- Mobile: Custom dropdown category selector -->
<div bind:this={dropdownRef} class="sm:hidden mb-4">
    <span class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        {$_('settings.category')}
    </span>
    <div class="relative">
        <button
                class="w-full flex items-center justify-between px-4 py-3 border border-gray-300 dark:border-slate-600
                   rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 text-sm
                   focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-all"
                on:click={toggleDropdown}
                type="button"
        >
            <span class="flex items-center gap-2">
                {#if selectedCategoryIcon}
                    <svelte:component this={selectedCategoryIcon} size={16} class="text-gray-500 dark:text-gray-400"/>
                {/if}
                {selectedCategoryLabel}
            </span>
            <ChevronDown class="text-gray-400 transition-transform {showDropdown ? 'rotate-180' : ''}" size={18}/>
        </button>

        {#if showDropdown}
            <div class="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-slate-800 border border-gray-200
                        dark:border-slate-600 rounded-lg shadow-lg overflow-hidden z-50">
                <!-- All Settings option -->
                <button
                        type="button"
                        on:click={() => selectCategoryMobile('all')}
                        class="w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors
                           {selectedCategory === 'all'
                               ? 'bg-libre-green/10 text-libre-green font-medium'
                               : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                >
                    <span class="flex-1">{getCategoryLabel('all')}</span>
                    {#if selectedCategory === 'all'}
                        <ChevronRight size={16}/>
                    {/if}
                </button>

                <!-- Category options -->
                {#each categories as cat (cat.id)}
                    <button
                            type="button"
                            on:click={() => selectCategoryMobile(cat.id)}
                            class="w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors
                               {selectedCategory === cat.id
                                   ? 'bg-libre-green/10 text-libre-green font-medium'
                                   : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    >
                        <svelte:component this={cat.icon} size={16} class="{selectedCategory === cat.id ? 'text-libre-green' : 'text-gray-400'}"/>
                        <span class="flex-1">{getCategoryLabel(cat.id)}</span>
                        {#if selectedCategory === cat.id}
                            <ChevronRight size={16}/>
                        {/if}
                    </button>
                {/each}
            </div>
        {/if}
    </div>
</div>

<div class="flex flex-col sm:flex-row gap-4 sm:gap-6 min-h-[300px] sm:min-h-[400px]" data-testid="global-settings-tab">
    <!-- Left sidebar: Category navigation (hidden on mobile) -->
    <div class="hidden sm:block w-48 flex-shrink-0">
        <nav class="space-y-1">
            <button
                    class="w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors
                    {selectedCategory === 'all'
                        ? 'bg-libre-green text-white'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700'}"
                    on:click={() => selectedCategory = 'all'}
            >
                <span class="flex-1 text-left">{getCategoryLabel('all')}</span>
                {#if selectedCategory === 'all'}
                    <ChevronRight size={16}/>
                {/if}
            </button>

            {#each categories as cat}
                <button
                        on:click={() => selectedCategory = cat.id}
                        class="w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors
                        {selectedCategory === cat.id
                            ? 'bg-libre-green text-white'
                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700'}"
                >
                    <svelte:component this={cat.icon} size={16} class="mr-2"/>
                    <span class="flex-1 text-left">{getCategoryLabel(cat.id)}</span>
                    {#if selectedCategory === cat.id}
                        <ChevronRight size={16}/>
                    {/if}
                </button>
            {/each}
        </nav>
    </div>

    <!-- Right side: Settings content -->
    <div class="flex-1 space-y-4">
        <!-- Header with lock/unlock - Title and icons on same row, description below -->
        <div class="pb-4 border-b border-gray-200 dark:border-slate-700">
            <div class="flex items-center justify-between gap-2 mb-1 min-h-[36px]">
                <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{$_('settings.globalSettings')}</h3>
                <div class="flex items-center gap-1 flex-shrink-0">
                    {#if canEdit}
                        {#if !isLocked}
                            {#if hasAnyChanges}
                                <button
                                        on:click={saveAll}
                                        disabled={isSaving}
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
                            {#if hasAnyNonDefault}
                                <button
                                        on:click={resetAllToDefaults}
                                        class="p-2 rounded-lg transition-all bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 hover:bg-orange-200 dark:hover:bg-orange-900/50"
                                        title={$_('settings.resetAllToDefault')}
                                >
                                    <RotateCcw size={18}/>
                                </button>
                            {/if}
                        {/if}
                        <button
                                on:click={toggleLock}
                                class="p-2 rounded-lg transition-all
                                {isLocked
                                    ? 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'
                                    : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 hover:bg-amber-200 dark:hover:bg-amber-900/50'}"
                                title={isLocked ? $_('settings.clickToEdit') : $_('settings.clickToLock')}
                        >
                            {#if isLocked}
                                <Lock size={18}/>
                            {:else}
                                <Unlock size={18}/>
                            {/if}
                        </button>
                    {:else}
                        <div class="flex items-center space-x-2 px-3 py-2 bg-gray-50 dark:bg-slate-700 text-gray-500 dark:text-gray-400 rounded-lg"
                             title={$_('settings.readOnlyMode')}>
                            <ShieldOff size={18}/>
                        </div>
                    {/if}
                </div>
            </div>
            <p class="text-sm text-gray-500 dark:text-gray-400">{$_('settings.globalSettingsDescription')}</p>
        </div>

        {#if error}
            <InfoBanner variant="error">
                <span>{error}</span>
            </InfoBanner>
        {/if}

        {#if success}
            <InfoBanner variant="success">
                <span class="whitespace-pre-line">{success}</span>
            </InfoBanner>
        {/if}

        {#if isLoading}
            <LoadingSpinner/>
        {:else if settings.length === 0}
            <div class="text-center py-8 text-gray-500">
                {$_('settings.noGlobalSettings')}
            </div>
        {:else}
            <div class="space-y-4">
                {#each filteredSettings as setting (setting.key)}
                    {@const category = getCategoryForSetting(setting.key)}
                    {#if setting.value_type === 'bool'}
                        <!-- Boolean toggle (self-contained component) -->
                        <div class="bg-gray-50 dark:bg-slate-800 rounded-lg px-4">
                            <SettingToggle
                                    value={editedValues[setting.key] === 'true'}
                                    label={getSettingLabel(setting.key)}
                                    hint={getSettingHint(setting.key)}
                                    icon={category?.icon ?? null}
                                    isModified={changedKeys.includes(setting.key)}
                                    isNonDefault={nonDefaultKeys.includes(setting.key)}
                                    {isLocked}
                                    {isSaving}
                                    onsave={() => saveSetting(setting.key)}
                                    onundo={() => undoSetting(setting.key)}
                                    onreset={() => resetSettingToDefault(setting.key)}
                                    onchange={(val) => {
                                        editedValues[setting.key] = val ? 'true' : 'false';
                                        editedValues = {...editedValues};
                                    }}
                            />
                        </div>
                    {:else if setting.value_type === 'int' || setting.value_type === 'float'}
                        <!-- Numeric input (self-contained component) -->
                        <div class="bg-gray-50 dark:bg-slate-800 rounded-lg px-4">
                            <SettingNumber
                                    value={editedValues[setting.key]}
                                    label={getSettingLabel(setting.key)}
                                    hint={getSettingHint(setting.key)}
                                    icon={category?.icon ?? null}
                                    type={setting.value_type === 'float' ? 'float' : 'int'}
                                    unit={getSettingUnit(setting.key)}
                                    isModified={changedKeys.includes(setting.key)}
                                    isNonDefault={nonDefaultKeys.includes(setting.key)}
                                    {isLocked}
                                    {isSaving}
                                    onsave={() => saveSetting(setting.key)}
                                    onundo={() => undoSetting(setting.key)}
                                    onreset={() => resetSettingToDefault(setting.key)}
                                    onchange={(val) => {
                                        editedValues[setting.key] = val;
                                        editedValues = {...editedValues};
                                    }}
                            />
                        </div>
                    {:else}
                        <!-- Language / Currency / Text (inline) -->
                        <div class="bg-gray-50 dark:bg-slate-800 rounded-lg p-4">
                            <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                                <div class="flex-1 min-w-0">
                                    <label for={setting.key} class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-200">
                                        {#if category}
                                            <svelte:component this={category.icon} size={16} class="mr-2 text-gray-500 dark:text-gray-400"/>
                                        {/if}
                                        {getSettingLabel(setting.key)}
                                    </label>
                                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                        {getSettingHint(setting.key)}
                                    </p>
                                </div>
                                <div class="flex items-center gap-2 sm:space-x-3 self-end sm:self-auto min-h-[32px]">
                                    {#if setting.key === 'default_language'}
                                        {#if !isLocked}
                                            <div class="flex items-center space-x-1">
                                                {#if changedKeys.includes(setting.key)}
                                                    <button
                                                            on:click={() => saveSetting(setting.key)}
                                                            disabled={isSaving}
                                                            class="p-1.5 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                                                            title={$_('common.save')}
                                                    >
                                                        <Save size={14}/>
                                                    </button>
                                                    <button
                                                            on:click={() => undoSetting(setting.key)}
                                                            class="p-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
                                                            title={$_('common.undo')}
                                                    >
                                                        <Undo size={14}/>
                                                    </button>
                                                {/if}
                                                {#if nonDefaultKeys.includes(setting.key)}
                                                    <button
                                                            on:click={() => resetSettingToDefault(setting.key)}
                                                            class="p-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 transition-colors"
                                                            title={$_('common.reset')}
                                                    >
                                                        <RotateCcw size={14}/>
                                                    </button>
                                                {/if}
                                            </div>
                                        {/if}
                                        <div class="w-40 sm:w-48">
                                            <SimpleSelect
                                                    bind:value={editedValues[setting.key]}
                                                    options={languageOptions}
                                                    placeholder={$_('settings.selectLanguage')}
                                                    disabled={isLocked}
                                                    onchange={() => { editedValues = {...editedValues}; }}
                                            />
                                        </div>
                                    {:else if setting.key === 'default_currency'}
                                        {#if !isLocked}
                                            <div class="flex items-center space-x-1">
                                                {#if changedKeys.includes(setting.key)}
                                                    <button
                                                            on:click={() => saveSetting(setting.key)}
                                                            disabled={isSaving}
                                                            class="p-1.5 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                                                            title={$_('common.save')}
                                                    >
                                                        <Save size={14}/>
                                                    </button>
                                                    <button
                                                            on:click={() => undoSetting(setting.key)}
                                                            class="p-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
                                                            title={$_('common.undo')}
                                                    >
                                                        <Undo size={14}/>
                                                    </button>
                                                {/if}
                                                {#if nonDefaultKeys.includes(setting.key)}
                                                    <button
                                                            on:click={() => resetSettingToDefault(setting.key)}
                                                            class="p-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 transition-colors"
                                                            title={$_('common.reset')}
                                                    >
                                                        <RotateCcw size={14}/>
                                                    </button>
                                                {/if}
                                            </div>
                                        {/if}
                                        <div class="w-48 sm:w-64">
                                            <CurrencySearchSelect
                                                    bind:value={editedValues[setting.key]}
                                                    placeholder={$_('settings.selectCurrency')}
                                                    disabled={isLocked}
                                                    onchange={() => { editedValues = {...editedValues}; }}
                                            />
                                        </div>
                                    {:else}
                                        {#if !isLocked}
                                            <div class="flex items-center space-x-1">
                                                {#if changedKeys.includes(setting.key)}
                                                    <button
                                                            on:click={() => saveSetting(setting.key)}
                                                            disabled={isSaving}
                                                            class="p-1.5 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50"
                                                            title={$_('common.save')}
                                                    >
                                                        <Save size={14}/>
                                                    </button>
                                                    <button
                                                            on:click={() => undoSetting(setting.key)}
                                                            class="p-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
                                                            title={$_('common.undo')}
                                                    >
                                                        <Undo size={14}/>
                                                    </button>
                                                {/if}
                                                {#if nonDefaultKeys.includes(setting.key)}
                                                    <button
                                                            on:click={() => resetSettingToDefault(setting.key)}
                                                            class="p-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 transition-colors"
                                                            title={$_('common.reset')}
                                                    >
                                                        <RotateCcw size={14}/>
                                                    </button>
                                                {/if}
                                            </div>
                                        {/if}
                                        <input
                                                id={setting.key}
                                                type="text"
                                                value={editedValues[setting.key]}
                                                on:input={(e) => {
                                                    editedValues[setting.key] = e.currentTarget.value;
                                                    editedValues = {...editedValues};
                                                }}
                                                disabled={isLocked}
                                                class="w-32 px-3 py-2 border rounded-lg text-sm
                                                {isLocked
                                                    ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                                                    : 'bg-white text-gray-900 focus:ring-2 focus:ring-libre-green focus:border-libre-green'}"
                                        />
                                    {/if}
                                </div>
                            </div>
                            {#if setting.updated_at && typeof setting.updated_at === 'string'}
                                <p class="text-xs text-gray-400 mt-2">
                                    Last updated: {new Date(setting.updated_at).toLocaleString()}
                                </p>
                            {/if}
                        </div>
                    {/if}
                {/each}
            </div>
        {/if}

        {#if !isLocked}
            <InfoBanner variant="warning">
                <p class="text-sm">
                    <strong>⚠️ {$_('settings.warning')}:</strong> {$_('settings.globalSettingsWarning')}
                </p>
            </InfoBanner>
        {/if}
    </div>
</div>

