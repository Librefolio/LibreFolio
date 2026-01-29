<script lang="ts">
    import {_, LANGUAGE_OPTIONS} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {isAxiosError} from 'axios';
    import {onMount} from 'svelte';
    import {debug} from '$lib/debug';
    import {AlertCircle, ChevronRight, Clock, FileUp, Lock, RotateCcw, Save, Shield, ShieldOff, Undo, Unlock, Users} from 'lucide-svelte';
    import FuzzySelect, {type SelectOption} from '$lib/components/FuzzySelect.svelte';
    import type {GlobalSetting} from '$lib/types';

    // Props
    export let canEdit: boolean = false;


    interface CurrencyInfo {
        code: string;
        name: string;
        symbol: string;
    }

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

    // Currency options for FuzzySelect
    let currencyOptions: SelectOption[] = [];
    let currenciesLoading = true;

    // Language options for dropdown
    const languageOptions = LANGUAGE_OPTIONS.map(l => ({
        code: l.code,
        label: l.name,
        icon: l.flag
    }));

    onMount(async () => {
        debug.log('GlobalSettingsTab', 'onMount');
        await Promise.all([
            loadSettings(),
            loadCurrencies()
        ]);
    });

    async function loadCurrencies() {
        debug.log('GlobalSettingsTab', 'loadCurrencies');
        currenciesLoading = true;
        try {
            const response = await zodiosApi.list_currencies_api_v1_utilities_currencies_get();
            currencyOptions = response.currencies.map(c => ({
                code: c.code,
                label: c.name,
                icon: c.symbol
            }));
        } catch (e) {
            debug.error('GlobalSettingsTab', 'loadCurrencies failed', e);
        } finally {
            currenciesLoading = false;
        }
    }

    async function loadSettings() {
        debug.log('GlobalSettingsTab', 'loadSettings');
        isLoading = true;
        error = null;
        try {
            const response = await zodiosApi.list_global_settings_api_v1_settings_global_get();
            debug.log('GlobalSettingsTab', 'loadSettings response', response.settings.length);
            settings = response.settings as GlobalSetting[];
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

    function getSettingLabel(key: string): string {
        // Try to get localized name, fallback to key
        const localizedKey = `settings.globalSettingNames.${key}`;
        const localized = $_(localizedKey);
        return localized !== localizedKey ? localized : key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    function getSettingUnit(key: string): string {
        const localizedKey = `settings.globalSettingUnits.${key}`;
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
</script>

<div class="flex gap-6 min-h-[400px]">
    <!-- Left sidebar: Category navigation -->
    <div class="w-48 flex-shrink-0">
        <nav class="space-y-1">
            <button
                    on:click={() => selectedCategory = 'all'}
                    class="w-full flex items-center px-3 py-2 text-sm rounded-lg transition-colors
                    {selectedCategory === 'all'
                        ? 'bg-libre-green text-white'
                        : 'text-gray-700 hover:bg-gray-100'}"
            >
                <span class="flex-1 text-left">{$_('settings.globalSettingCategories.all')}</span>
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
                            : 'text-gray-700 hover:bg-gray-100'}"
                >
                    <svelte:component this={cat.icon} size={16} class="mr-2"/>
                    <span class="flex-1 text-left">{$_(`settings.globalSettingCategories.${cat.id}`)}</span>
                    {#if selectedCategory === cat.id}
                        <ChevronRight size={16}/>
                    {/if}
                </button>
            {/each}
        </nav>
    </div>

    <!-- Right side: Settings content -->
    <div class="flex-1 space-y-4">
        <!-- Header with lock/unlock -->
        <div class="flex items-center justify-between pb-4 border-b border-gray-200">
            <div>
                <h3 class="text-lg font-semibold text-gray-900">{$_('settings.globalSettings')}</h3>
                <p class="text-sm text-gray-500">{$_('settings.globalSettingsDescription')}</p>
            </div>
            <div class="flex items-center space-x-1">
                {#if canEdit}
                    {#if !isLocked}
                        <!-- Bulk action buttons when unlocked - only visible when actionable -->
                        {#if hasAnyChanges}
                            <button
                                    on:click={saveAll}
                                    disabled={isSaving}
                                    class="p-2 rounded-lg transition-all bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50"
                                    title={$_('settings.saveAll')}
                            >
                                <Save size={18}/>
                            </button>
                            <button
                                    on:click={undoAll}
                                    class="p-2 rounded-lg transition-all bg-gray-100 text-gray-600 hover:bg-gray-200"
                                    title={$_('settings.undoAll')}
                            >
                                <Undo size={18}/>
                            </button>
                        {/if}
                        {#if hasAnyNonDefault}
                            <button
                                    on:click={resetAllToDefaults}
                                    class="p-2 rounded-lg transition-all bg-orange-100 text-orange-700 hover:bg-orange-200"
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
                                ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                : 'bg-amber-100 text-amber-700 hover:bg-amber-200'}"
                            title={isLocked ? $_('settings.clickToEdit') : $_('settings.clickToLock')}
                    >
                        {#if isLocked}
                            <Lock size={18}/>
                        {:else}
                            <Unlock size={18}/>
                        {/if}
                    </button>
                {:else}
                    <div class="flex items-center space-x-2 px-3 py-2 bg-gray-50 text-gray-500 rounded-lg" title={$_('settings.readOnlyMode')}>
                        <ShieldOff size={18}/>
                    </div>
                {/if}
            </div>
        </div>

        {#if error}
            <div class="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                <AlertCircle size={18}/>
                <span>{error}</span>
            </div>
        {/if}

        {#if success}
            <div class="p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 whitespace-pre-line">
                {success}
            </div>
        {/if}

        {#if isLoading}
            <div class="text-center py-8 text-gray-500">
                {$_('common.loading')}
            </div>
        {:else if settings.length === 0}
            <div class="text-center py-8 text-gray-500">
                {$_('settings.noGlobalSettings')}
            </div>
        {:else}
            <div class="space-y-4">
                {#each filteredSettings as setting (setting.key)}
                    {@const category = getCategoryForSetting(setting.key)}
                    <div class="bg-gray-50 rounded-lg p-4">
                        <div class="flex items-center justify-between">
                            <div class="flex-1">
                                <label for={setting.key} class="flex items-center text-sm font-medium text-gray-700">
                                    {#if category}
                                        <svelte:component this={category.icon} size={16} class="mr-2 text-gray-500"/>
                                    {/if}
                                    {$_(`settings.globalSettingNames.${setting.key}`) !== `settings.globalSettingNames.${setting.key}`
                                        ? $_(`settings.globalSettingNames.${setting.key}`)
                                        : setting.key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                </label>
                                <p class="text-xs text-gray-500 mt-1">
                                    {$_(`settings.globalSettingDescriptions.${setting.key}`) !== `settings.globalSettingDescriptions.${setting.key}`
                                        ? $_(`settings.globalSettingDescriptions.${setting.key}`)
                                        : ''}
                                </p>
                            </div>
                            <div class="flex items-center space-x-3">
                                {#if setting.value_type === 'bool'}
                                    <!-- Action buttons BEFORE the field -->
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
                                                        title={$_('settings.undo')}
                                                >
                                                    <Undo size={14}/>
                                                </button>
                                            {/if}
                                            {#if nonDefaultKeys.includes(setting.key)}
                                                <button
                                                        on:click={() => resetSettingToDefault(setting.key)}
                                                        class="p-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 transition-colors"
                                                        title={$_('settings.resetToDefault')}
                                                >
                                                    <RotateCcw size={14}/>
                                                </button>
                                            {/if}
                                        </div>
                                    {/if}
                                    <!-- Toggle Switch for boolean -->
                                    <button
                                            type="button"
                                            disabled={isLocked}
                                            aria-label="Toggle {setting.key}"
                                            on:click={() => {
                                                if (!isLocked) {
                                                    editedValues[setting.key] = editedValues[setting.key] === 'true' ? 'false' : 'true';
                                                    editedValues = {...editedValues};
                                                }
                                            }}
                                            class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                                            {editedValues[setting.key] === 'true' ? 'bg-libre-green' : 'bg-gray-300'}
                                            {isLocked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}"
                                    >
                                        <span
                                                class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                                                {editedValues[setting.key] === 'true' ? 'translate-x-6' : 'translate-x-1'}"
                                        ></span>
                                    </button>
                                    <span class="text-sm text-gray-600 w-10">
                                        {editedValues[setting.key] === 'true' ? 'ON' : 'OFF'}
                                    </span>
                                {:else if setting.value_type === 'int' || setting.value_type === 'float'}
                                    <!-- Action buttons BEFORE the field -->
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
                                                        title={$_('settings.undo')}
                                                >
                                                    <Undo size={14}/>
                                                </button>
                                            {/if}
                                            {#if nonDefaultKeys.includes(setting.key)}
                                                <button
                                                        on:click={() => resetSettingToDefault(setting.key)}
                                                        class="p-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 transition-colors"
                                                        title={$_('settings.resetToDefault')}
                                                >
                                                    <RotateCcw size={14}/>
                                                </button>
                                            {/if}
                                        </div>
                                    {/if}
                                    <!-- Number input with unit -->
                                    <div class="flex items-center space-x-2">
                                        <input
                                                id={setting.key}
                                                type="number"
                                                step={setting.value_type === 'float' ? '0.01' : '1'}
                                                min="0"
                                                value={editedValues[setting.key]}
                                                on:input={(e) => {
                                                    editedValues[setting.key] = e.currentTarget.value;
                                                    editedValues = {...editedValues};
                                                }}
                                                disabled={isLocked}
                                                class="w-20 px-3 py-2 border rounded-lg text-sm text-right
                                                {isLocked
                                                    ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                                                    : 'bg-white text-gray-900 focus:ring-2 focus:ring-libre-green focus:border-libre-green'}"
                                        />
                                        {#if getSettingUnit(setting.key)}
                                            <span class="text-sm text-gray-500">{getSettingUnit(setting.key)}</span>
                                        {/if}
                                    </div>
                                {:else if setting.key === 'default_language'}
                                    <!-- Action buttons BEFORE the field -->
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
                                                        title={$_('settings.undo')}
                                                >
                                                    <Undo size={14}/>
                                                </button>
                                            {/if}
                                            {#if nonDefaultKeys.includes(setting.key)}
                                                <button
                                                        on:click={() => resetSettingToDefault(setting.key)}
                                                        class="p-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 transition-colors"
                                                        title={$_('settings.resetToDefault')}
                                                >
                                                    <RotateCcw size={14}/>
                                                </button>
                                            {/if}
                                        </div>
                                    {/if}
                                    <!-- Language dropdown -->
                                    <select
                                            id={setting.key}
                                            value={editedValues[setting.key]}
                                            on:change={(e) => {
                                                editedValues[setting.key] = e.currentTarget.value;
                                                editedValues = {...editedValues};
                                            }}
                                            disabled={isLocked}
                                            class="w-40 px-3 py-2 border rounded-lg text-sm
                                            {isLocked
                                                ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                                                : 'bg-white text-gray-900 focus:ring-2 focus:ring-libre-green focus:border-libre-green'}"
                                    >
                                        {#each languageOptions as lang}
                                            <option value={lang.code}>
                                                {lang.icon} {lang.label}
                                            </option>
                                        {/each}
                                    </select>
                                {:else if setting.key === 'default_currency'}
                                    <!-- Action buttons BEFORE the field -->
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
                                                        title={$_('settings.undo')}
                                                >
                                                    <Undo size={14}/>
                                                </button>
                                            {/if}
                                            {#if nonDefaultKeys.includes(setting.key)}
                                                <button
                                                        on:click={() => resetSettingToDefault(setting.key)}
                                                        class="p-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 transition-colors"
                                                        title={$_('settings.resetToDefault')}
                                                >
                                                    <RotateCcw size={14}/>
                                                </button>
                                            {/if}
                                        </div>
                                    {/if}
                                    <!-- Currency FuzzySelect -->
                                    <div class="w-72">
                                        <FuzzySelect
                                                bind:value={editedValues[setting.key]}
                                                options={currencyOptions}
                                                placeholder={$_('settings.selectCurrency')}
                                                disabled={isLocked}
                                                loading={currenciesLoading}
                                                on:change={() => { editedValues = {...editedValues}; }}
                                        />
                                    </div>
                                {:else}
                                    <!-- Action buttons BEFORE the field -->
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
                                                        title={$_('settings.undo')}
                                                >
                                                    <Undo size={14}/>
                                                </button>
                                            {/if}
                                            {#if nonDefaultKeys.includes(setting.key)}
                                                <button
                                                        on:click={() => resetSettingToDefault(setting.key)}
                                                        class="p-1.5 bg-orange-100 text-orange-600 rounded-lg hover:bg-orange-200 transition-colors"
                                                        title={$_('settings.resetToDefault')}
                                                >
                                                    <RotateCcw size={14}/>
                                                </button>
                                            {/if}
                                        </div>
                                    {/if}
                                    <!-- Text input for string -->
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
                {/each}
            </div>
        {/if}

        {#if !isLocked}
            <div class="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <p class="text-sm text-amber-700">
                    <strong>⚠️ {$_('settings.warning')}:</strong> {$_('settings.globalSettingsWarning')}
                </p>
            </div>
        {/if}
    </div>
</div>

