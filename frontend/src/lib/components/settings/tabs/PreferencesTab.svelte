<script lang="ts">
    import {_, LANGUAGE_OPTIONS, type SupportedLocale} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {userSettings} from '$lib/stores/settings';
    import {zodiosApi} from '$lib/api';
    import {isAxiosError} from 'axios';
    import {onMount} from 'svelte';
    import {debug} from '$lib/debug';
    import {Coins, Globe, Palette, User} from 'lucide-svelte';
    import type {SelectOption} from '$lib/components/ui/select';
    import SettingsLayout from '$lib/components/settings/SettingsLayout.svelte';
    import SettingSelect from '$lib/components/settings/SettingSelect.svelte';
    import SettingCurrency from '$lib/components/settings/SettingCurrency.svelte';
    import SettingTheme from '$lib/components/settings/SettingTheme.svelte';
    import {ImageEditModal} from '$lib/components/ui/media';

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
        {id: 'profile', icon: User, labelKey: 'settings.categoryProfile'},
        {id: 'display', icon: Globe, labelKey: 'settings.categoryDisplay'},
        {id: 'currency', icon: Coins, labelKey: 'settings.categoryCurrency'},
        {id: 'appearance', icon: Palette, labelKey: 'settings.categoryAppearance'},
    ];

    // Hardcoded fallback defaults (used only if global settings fail to load)
    const FALLBACK_DEFAULTS = {
        language: 'en',
        default_currency: 'EUR',
        theme: 'auto' as 'light' | 'dark' | 'auto',
        avatar_url: null as string | null
    };

    // Global defaults (loaded from server's global settings)
    let globalDefaults = {...FALLBACK_DEFAULTS};

    // Original values (from API - user's current settings)
    let originalValues = {...FALLBACK_DEFAULTS};

    // Edited values
    let editedValues = {...FALLBACK_DEFAULTS};

    let isLoading = true;
    let isSaving = false;
    let error: string | null = null;
    let success: string | null = null;
    let selectedCategory: string = '';

    // Avatar upload modal state
    let showAvatarModal = false;
    let avatarFile: File | null = null;

    // Currency options for FuzzySelect
    let currencyOptions: SelectOption[] = [];
    let currenciesLoading = true;

    // Language options
    const languageOptions: SelectOption[] = LANGUAGE_OPTIONS.map(l => ({
        value: l.code,
        label: l.name,
        icon: l.flag
    }));

    onMount(async () => {
        debug.log('PreferencesTab', 'onMount');
        await Promise.all([loadGlobalDefaults(), loadSettings(), loadCurrencies()]);
    });

    async function loadGlobalDefaults() {
        debug.log('PreferencesTab', 'loadGlobalDefaults');
        try {
            // API returns { settings: [{ key: "default_language", value: "en" }, ...] }
            const response = await zodiosApi.list_global_settings_api_v1_settings_global_get();

            debug.log('PreferencesTab', 'loadGlobalDefaults response', response);

            // Convert array to object for easy access
            const settingsMap: Record<string, string> = {};
            for (const setting of response.settings) {
                settingsMap[setting.key] = setting.value;
            }

            globalDefaults = {
                language: settingsMap['default_language'] || FALLBACK_DEFAULTS.language,
                default_currency: settingsMap['default_currency'] || FALLBACK_DEFAULTS.default_currency,
                theme: (settingsMap['default_theme'] as 'light' | 'dark' | 'auto') || FALLBACK_DEFAULTS.theme,
                avatar_url: null  // No global default for avatar
            };
            debug.log('PreferencesTab', 'globalDefaults set to', globalDefaults);
        } catch (e) {
            debug.error('PreferencesTab', 'loadGlobalDefaults failed, using fallback', e);
            // Keep FALLBACK_DEFAULTS if global settings can't be loaded
        }
    }

    async function loadSettings() {
        debug.log('PreferencesTab', 'loadSettings');
        isLoading = true;
        error = null;
        try {
            const response = await zodiosApi.get_user_settings_endpoint_api_v1_settings_user_get();

            debug.log('PreferencesTab', 'loadSettings response', response);
            // avatar_url can come as string | null | undefined from API
            const avatarUrl = typeof response.avatar_url === 'string' ? response.avatar_url : null;
            originalValues = {
                language: response.language || $currentLanguage,
                default_currency: response.base_currency || 'EUR',
                theme: response.theme || getStoredTheme(),
                avatar_url: avatarUrl
            };
            editedValues = {...originalValues};
        } catch (e) {
            debug.error('PreferencesTab', 'loadSettings failed', e);
        } finally {
            isLoading = false;
        }
    }

    async function loadCurrencies() {
        debug.log('PreferencesTab', 'loadCurrencies');
        currenciesLoading = true;
        try {
            const response = await zodiosApi.list_currencies_api_v1_utilities_currencies_get();
            currencyOptions = response.currencies.map(c => ({
                value: c.code,
                label: c.name,
                icon: c.symbol !== c.code ? c.symbol : undefined
            }));
        } catch (e) {
            debug.error('PreferencesTab', 'loadCurrencies failed', e);
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
    $: avatarModified = editedValues.avatar_url !== originalValues.avatar_url;

    // Check if a field is non-default (compared to global defaults)
    $: languageNonDefault = originalValues.language !== globalDefaults.language;
    $: currencyNonDefault = originalValues.default_currency !== globalDefaults.default_currency;
    $: themeNonDefault = originalValues.theme !== globalDefaults.theme;
    $: avatarNonDefault = originalValues.avatar_url !== null;

    // Check if any field is modified
    $: hasChanges = languageModified || currencyModified || themeModified || avatarModified;

    // Filter settings by category
    function getCategoryFields(categoryId: string): (keyof typeof editedValues)[] {
        switch (categoryId) {
            case 'profile':
                return ['avatar_url'];
            case 'display':
                return ['language'];
            case 'currency':
                return ['default_currency'];
            case 'appearance':
                return ['theme'];
            default:
                return ['avatar_url', 'language', 'default_currency', 'theme'];
        }
    }

    // Get visible fields
    $: visibleFields = selectedCategory === ''
        ? ['avatar_url', 'language', 'default_currency', 'theme'] as const
        : getCategoryFields(selectedCategory) as (keyof typeof editedValues)[];

    // Single field actions
    async function saveField(field: keyof typeof editedValues) {
        isSaving = true;
        error = null;
        success = null;

        try {
            if (field === 'avatar_url') {
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({avatar_url: editedValues.avatar_url});
                // Sync userSettings store
                userSettings.setDirect({
                    language: editedValues.language,
                    base_currency: editedValues.default_currency,
                    theme: editedValues.theme,
                    avatar_url: editedValues.avatar_url
                });
            } else if (field === 'language') {
                currentLanguage.set(editedValues.language as SupportedLocale);
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({language: editedValues.language});
                // Sync userSettings store
                userSettings.setDirect({
                    language: editedValues.language,
                    base_currency: editedValues.default_currency,
                    theme: editedValues.theme,
                    avatar_url: editedValues.avatar_url
                });
            } else if (field === 'default_currency') {
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({base_currency: editedValues.default_currency});
                // Sync userSettings store
                userSettings.setDirect({
                    language: editedValues.language,
                    base_currency: editedValues.default_currency,
                    theme: editedValues.theme,
                    avatar_url: editedValues.avatar_url
                });
            } else if (field === 'theme') {
                localStorage.setItem('librefolio-theme', editedValues.theme === 'auto' ? '' : editedValues.theme);
                document.documentElement.classList.remove('light', 'dark');
                if (editedValues.theme !== 'auto') {
                    document.documentElement.classList.add(editedValues.theme);
                }
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({theme: editedValues.theme});
                // Sync userSettings store
                userSettings.setDirect({
                    language: editedValues.language,
                    base_currency: editedValues.default_currency,
                    theme: editedValues.theme,
                    avatar_url: editedValues.avatar_url
                });
            }

            originalValues = {...originalValues, [field]: editedValues[field]};
            success = $_('settings.savedSuccessfully');
            setTimeout(() => success = null, 3000);
        } catch (e) {
            if (isAxiosError(e)) {
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
        editedValues = {...editedValues, [field]: globalDefaults[field]};
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
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({language: editedValues.language});
                originalValues.language = editedValues.language;
                saved.push($_('settings.language'));
            }

            if (currencyModified) {
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({base_currency: editedValues.default_currency});
                originalValues.default_currency = editedValues.default_currency;
                saved.push($_('settings.defaultCurrency'));
            }

            if (themeModified) {
                localStorage.setItem('librefolio-theme', editedValues.theme === 'auto' ? '' : editedValues.theme);
                document.documentElement.classList.remove('light', 'dark');
                if (editedValues.theme !== 'auto') {
                    document.documentElement.classList.add(editedValues.theme);
                }
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({theme: editedValues.theme});
                originalValues.theme = editedValues.theme;
                saved.push($_('settings.theme'));
            }

            // Save avatar if modified
            if (avatarModified) {
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({avatar_url: editedValues.avatar_url});
                originalValues.avatar_url = editedValues.avatar_url;
                saved.push($_('settings.avatar'));
            }

            // Sync userSettings store after all saves
            if (saved.length > 0) {
                userSettings.setDirect({
                    language: editedValues.language,
                    base_currency: editedValues.default_currency,
                    theme: editedValues.theme,
                    avatar_url: editedValues.avatar_url
                });
                success = `${$_('settings.savedSuccessfully')}: ${saved.join(', ')}`;
            }
            setTimeout(() => success = null, 4000);
        } catch (e) {
            if (isAxiosError(e)) {
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
        editedValues = {...globalDefaults};
    }

    // Avatar handlers
    function handleAvatarFileSelect(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files[0]) {
            avatarFile = input.files[0];
            showAvatarModal = true;
            input.value = '';
        }
    }

    function handleAvatarUploadComplete(event: CustomEvent<{url: string; file: File}>) {
        editedValues.avatar_url = event.detail.url;
        showAvatarModal = false;
        avatarFile = null;
        // Auto-save avatar
        saveField('avatar_url');
    }

    function removeAvatar() {
        editedValues.avatar_url = null;
        saveField('avatar_url');
    }
</script>

<SettingsLayout
        bind:selectedCategory
        {categories}
        {hasChanges}
        hasNonDefaults={false}
        isLocked={false}
        on:resetAll={resetAll}
        on:saveAll={saveAll}
        on:undoAll={undoAll}
        showLock={false}
        title={$_('settings.userPreferences')}
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
        <!-- Avatar Setting -->
        {#if visibleFields.includes('avatar_url')}
            <div data-testid="preference-avatar" class="setting-row p-4 border rounded-lg mb-4 dark:border-slate-700">
                <div class="flex items-center gap-4">
                    <!-- Avatar Preview -->
                    <div class="relative group">
                        {#if editedValues.avatar_url}
                            <img
                                src={editedValues.avatar_url}
                                alt="Avatar"
                                class="w-20 h-20 rounded-full object-cover border-2 border-gray-200 dark:border-slate-600"
                            />
                        {:else}
                            <div class="w-20 h-20 rounded-full bg-gray-200 dark:bg-slate-700 flex items-center justify-center">
                                <User size={32} class="text-gray-400 dark:text-slate-500" />
                            </div>
                        {/if}
                        <!-- Upload overlay -->
                        <label class="absolute inset-0 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center cursor-pointer transition-opacity">
                            <span class="text-white text-xs">{$_('common.change')}</span>
                            <input
                                type="file"
                                accept="image/*"
                                class="hidden"
                                on:change={handleAvatarFileSelect}
                            />
                        </label>
                    </div>
                    <!-- Avatar Info -->
                    <div class="flex-1">
                        <h4 class="font-medium text-gray-900 dark:text-white">{$_('settings.avatar')}</h4>
                        <p class="text-sm text-gray-500 dark:text-gray-400">{$_('settings.avatarHint')}</p>
                        {#if editedValues.avatar_url}
                            <button
                                type="button"
                                class="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
                                on:click={removeAvatar}
                            >
                                {$_('common.remove')}
                            </button>
                        {/if}
                    </div>
                </div>
            </div>
        {/if}

        <!-- Language Setting -->
        {#if visibleFields.includes('language')}
            <div data-testid="preference-language">
                <SettingSelect
                        bind:value={editedValues.language}
                        options={languageOptions}
                        label={$_('settings.language')}
                        hint={$_('settings.languageHint')}
                        isModified={languageModified}
                        isNonDefault={languageNonDefault}
                        isLocked={false}
                        onsave={() => saveField('language')}
                        onundo={() => undoField('language')}
                        onreset={() => resetField('language')}
                />
            </div>
        {/if}

        <!-- Default Currency Setting -->
        {#if visibleFields.includes('default_currency')}
            <div data-testid="preference-currency">
                <SettingCurrency
                        bind:value={editedValues.default_currency}
                        options={currencyOptions}
                        label={$_('settings.defaultCurrency')}
                        hint={$_('settings.defaultCurrencyHint')}
                        isModified={currencyModified}
                        isNonDefault={currencyNonDefault}
                        isLocked={false}
                        loading={currenciesLoading}
                        onsave={() => saveField('default_currency')}
                        onundo={() => undoField('default_currency')}
                        onreset={() => resetField('default_currency')}
                />
            </div>
        {/if}

        <!-- Theme Setting -->
        {#if visibleFields.includes('theme')}
            <div data-testid="preference-theme">
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
            </div>
        {/if}
    {/if}
</SettingsLayout>

<!-- Avatar Edit Modal -->
<ImageEditModal
    open={showAvatarModal}
    file={avatarFile}
    preset="avatar"
    on:complete={handleAvatarUploadComplete}
    on:cancel={() => { showAvatarModal = false; avatarFile = null; }}
    on:error={(e) => { error = e.detail.message; }}
/>
