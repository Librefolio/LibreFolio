<script lang="ts">
    import {_, LANGUAGE_OPTIONS, type SupportedLocale} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {api, ApiError} from '$lib/api';
    import {onMount} from 'svelte';
    import {Coins, Globe, Palette} from 'lucide-svelte';
    import type {SelectOption} from '$lib/components/FuzzySelect.svelte';
    import SettingsLayout from '$lib/components/settings/SettingsLayout.svelte';
    import SettingSelect from '$lib/components/settings/SettingSelect.svelte';
    import SettingCurrency from '$lib/components/settings/SettingCurrency.svelte';
    import SettingTheme from '$lib/components/settings/SettingTheme.svelte';

    interface CurrencyInfo {
        code: string;
        name: string;
        symbol: string;
    }

    // Category definitions
    interface Category {
        id: string;
        icon: any;
        labelKey: string;
    }

    const categories: Category[] = [
        {id: 'display', icon: Globe, labelKey: 'settings.categoryDisplay'},
        {id: 'currency', icon: Coins, labelKey: 'settings.categoryCurrency'},
        {id: 'appearance', icon: Palette, labelKey: 'settings.categoryAppearance'},
    ];

    // Default values
    const DEFAULTS = {
        language: 'en',
        default_currency: 'EUR',
        theme: 'auto' as 'light' | 'dark' | 'auto'
    };

    // Original values (from API)
    let originalValues = {...DEFAULTS};

    // Edited values
    let editedValues = {...DEFAULTS};

    let isLoading = true;
    let isSaving = false;
    let error: string | null = null;
    let success: string | null = null;
    let selectedCategory: string = '';

    // Currency options for FuzzySelect
    let currencyOptions: SelectOption[] = [];
    let currenciesLoading = true;

    // Language options
    const languageOptions = LANGUAGE_OPTIONS.map(l => ({
        code: l.code,
        label: l.name,
        icon: l.flag
    }));

    onMount(async () => {
        await Promise.all([loadSettings(), loadCurrencies()]);
    });

    async function loadSettings() {
        isLoading = true;
        error = null;
        try {
            const response = await api.get<{
                language: string;
                base_currency: string;
                theme: 'light' | 'dark' | 'auto';
            }>('/settings/user');

            originalValues = {
                language: response.language || $currentLanguage,
                default_currency: response.base_currency || 'EUR',
                theme: response.theme || getStoredTheme()
            };
            editedValues = {...originalValues};
        } catch (e) {
            console.error('Failed to load user settings', e);
        } finally {
            isLoading = false;
        }
    }

    async function loadCurrencies() {
        currenciesLoading = true;
        try {
            const response = await api.get<{ currencies: CurrencyInfo[] }>('/utilities/currencies');
            currencyOptions = response.currencies.map(c => ({
                code: c.code,
                label: c.name,
                icon: c.symbol !== c.code ? c.symbol : undefined
            }));
        } catch (e) {
            console.error('Failed to load currencies', e);
        } finally {
            currenciesLoading = false;
        }
    }

    function getStoredTheme(): 'light' | 'dark' | 'auto' {
        if (typeof localStorage === 'undefined') return 'auto';
        const saved = localStorage.getItem('librefolio-theme');
        if (saved === 'light' || saved === 'dark') return saved;
        return 'auto';
    }

    // Check if a field has been modified (reactive computed)
    $: languageModified = editedValues.language !== originalValues.language;
    $: currencyModified = editedValues.default_currency !== originalValues.default_currency;
    $: themeModified = editedValues.theme !== originalValues.theme;

    // Check if a field is non-default (reactive computed)
    $: languageNonDefault = originalValues.language !== DEFAULTS.language;
    $: currencyNonDefault = originalValues.default_currency !== DEFAULTS.default_currency;
    $: themeNonDefault = originalValues.theme !== DEFAULTS.theme;

    // Check if any field is modified
    $: hasChanges = languageModified || currencyModified || themeModified;

    // Filter settings by category
    function getCategoryFields(categoryId: string): (keyof typeof editedValues)[] {
        switch (categoryId) {
            case 'display': return ['language'];
            case 'currency': return ['default_currency'];
            case 'appearance': return ['theme'];
            default: return ['language', 'default_currency', 'theme'];
        }
    }

    // Get visible fields
    $: visibleFields = selectedCategory === ''
        ? ['language', 'default_currency', 'theme'] as const
        : getCategoryFields(selectedCategory) as (keyof typeof editedValues)[];

    // Single field actions
    async function saveField(field: keyof typeof editedValues) {
        isSaving = true;
        error = null;
        success = null;

        try {
            if (field === 'language') {
                currentLanguage.set(editedValues.language as SupportedLocale);
                await api.put('/settings/user', {language: editedValues.language});
            } else if (field === 'default_currency') {
                await api.put('/settings/user', {base_currency: editedValues.default_currency});
            } else if (field === 'theme') {
                localStorage.setItem('librefolio-theme', editedValues.theme === 'auto' ? '' : editedValues.theme);
                document.documentElement.classList.remove('light', 'dark');
                if (editedValues.theme !== 'auto') {
                    document.documentElement.classList.add(editedValues.theme);
                }
                await api.put('/settings/user', {theme: editedValues.theme});
            }

            originalValues = {...originalValues, [field]: editedValues[field]};
            success = $_('settings.savedSuccessfully');
            setTimeout(() => success = null, 3000);
        } catch (e) {
            if (e instanceof ApiError) {
                error = e.message;
            } else {
                error = $_('settings.saveFailed');
            }
        } finally {
            isSaving = false;
        }
    }

    function undoField(field: keyof typeof editedValues) {
        editedValues = {...editedValues, [field]: originalValues[field]};
    }

    function resetField(field: keyof typeof editedValues) {
        editedValues = {...editedValues, [field]: DEFAULTS[field]};
    }

    // Bulk actions
    async function saveAll() {
        isSaving = true;
        error = null;
        success = null;

        const saved: string[] = [];

        try {
            if (languageModified) {
                currentLanguage.set(editedValues.language as SupportedLocale);
                await api.put('/settings/user', {language: editedValues.language});
                originalValues.language = editedValues.language;
                saved.push($_('settings.language'));
            }

            if (currencyModified) {
                await api.put('/settings/user', {base_currency: editedValues.default_currency});
                originalValues.default_currency = editedValues.default_currency;
                saved.push($_('settings.defaultCurrency'));
            }

            if (themeModified) {
                localStorage.setItem('librefolio-theme', editedValues.theme === 'auto' ? '' : editedValues.theme);
                document.documentElement.classList.remove('light', 'dark');
                if (editedValues.theme !== 'auto') {
                    document.documentElement.classList.add(editedValues.theme);
                }
                await api.put('/settings/user', {theme: editedValues.theme});
                originalValues.theme = editedValues.theme;
                saved.push($_('settings.theme'));
            }

            if (saved.length > 0) {
                success = `${$_('settings.savedSuccessfully')}: ${saved.join(', ')}`;
            }
            setTimeout(() => success = null, 4000);
        } catch (e) {
            if (e instanceof ApiError) {
                error = e.message;
            } else {
                error = $_('settings.saveFailed');
            }
        } finally {
            isSaving = false;
        }
    }

    function undoAll() {
        editedValues = {...originalValues};
    }

    function resetAll() {
        editedValues = {...DEFAULTS};
    }
</script>

<SettingsLayout
    {categories}
    bind:selectedCategory
    {hasChanges}
    hasNonDefaults={false}
    isLocked={false}
    showLock={false}
    title={$_('settings.userPreferences')}
    on:saveAll={saveAll}
    on:undoAll={undoAll}
    on:resetAll={resetAll}
>
    <!-- Success/Error Messages -->
    {#if success}
        <div class="mb-4 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg text-green-700 dark:text-green-300 text-sm">
            {success}
        </div>
    {/if}
    {#if error}
        <div class="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
            {error}
        </div>
    {/if}

    <!-- Settings Fields -->
    {#if isLoading}
        <div class="text-center py-8 text-gray-500 dark:text-gray-400">{$_('common.loading')}</div>
    {:else}
        <!-- Language Setting -->
        {#if visibleFields.includes('language')}
            <SettingSelect
                bind:value={editedValues.language}
                options={languageOptions}
                label={$_('settings.language')}
                hint={$_('settings.languageHint')}
                icon={Globe}
                isModified={languageModified}
                isNonDefault={languageNonDefault}
                isLocked={false}
                on:save={() => saveField('language')}
                on:undo={() => undoField('language')}
                on:reset={() => resetField('language')}
            />
        {/if}

        <!-- Default Currency Setting -->
        {#if visibleFields.includes('default_currency')}
            <SettingCurrency
                bind:value={editedValues.default_currency}
                options={currencyOptions}
                label={$_('settings.defaultCurrency')}
                hint={$_('settings.defaultCurrencyHint')}
                icon={Coins}
                isModified={currencyModified}
                isNonDefault={currencyNonDefault}
                isLocked={false}
                loading={currenciesLoading}
                on:save={() => saveField('default_currency')}
                on:undo={() => undoField('default_currency')}
                on:reset={() => resetField('default_currency')}
            />
        {/if}

        <!-- Theme Setting -->
        {#if visibleFields.includes('theme')}
            <SettingTheme
                bind:value={editedValues.theme}
                label={$_('settings.theme')}
                hint={$_('settings.themeHint')}
                icon={Palette}
                isModified={themeModified}
                isNonDefault={themeNonDefault}
                isLocked={false}
                on:save={() => saveField('theme')}
                on:undo={() => undoField('theme')}
                on:reset={() => resetField('theme')}
            />
        {/if}
    {/if}
</SettingsLayout>

