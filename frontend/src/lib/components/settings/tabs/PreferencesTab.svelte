<script lang="ts">
    import {_, LANGUAGE_OPTIONS, type SupportedLocale} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {userSettings} from '$lib/stores/app/settings';
    import {applyTheme, getStoredThemePreference} from '$lib/stores/app/themeStore';
    import {zodiosApi} from '$lib/api';
    import {isAxiosError} from 'axios';
    import {onMount} from 'svelte';
    import {debug} from '$lib/debug';
    import {Coins, Globe, Palette} from 'lucide-svelte';
    import type {SelectOption} from '$lib/components/ui/select';
    import SettingsLayout from '$lib/components/settings/SettingsLayout.svelte';
    import SettingSelect from '$lib/components/settings/SettingSelect.svelte';
    import SettingCurrency from '$lib/components/settings/SettingCurrency.svelte';
    import SettingTheme from '$lib/components/settings/SettingTheme.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';

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

    // Hardcoded fallback defaults (used only if global settings fail to load)
    const FALLBACK_DEFAULTS = {
        language: 'en',
        default_currency: 'EUR',
        theme: 'auto' as 'light' | 'dark' | 'auto',
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

    // Language options
    const languageOptions: SelectOption[] = LANGUAGE_OPTIONS.map((l) => ({
        value: l.code,
        label: l.name,
        icon: l.flag,
    }));

    onMount(async () => {
        debug.log('PreferencesTab', 'onMount');
        await Promise.all([loadGlobalDefaults(), loadSettings()]);
    });

    async function loadGlobalDefaults() {
        debug.log('PreferencesTab', 'loadGlobalDefaults');
        try {
            // API returns { settings: [{ key: "default_language", value: "en" }, ...] }
            const response = await zodiosApi.list_global_settings_api_v1_settings_global_get();

            debug.log('PreferencesTab', 'loadGlobalDefaults response', response);

            // Convert array to object for easy access
            const settingsMap: Record<string, string> = {};
            for (const setting of response.items ?? []) {
                settingsMap[setting.key] = setting.value;
            }

            globalDefaults = {
                language: settingsMap['default_language'] || FALLBACK_DEFAULTS.language,
                default_currency: settingsMap['default_currency'] || FALLBACK_DEFAULTS.default_currency,
                theme: (settingsMap['default_theme'] as 'light' | 'dark' | 'auto') || FALLBACK_DEFAULTS.theme,
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
            originalValues = {
                language: response.language || $currentLanguage,
                default_currency: response.base_currency || 'EUR',
                theme: response.theme || getStoredThemePreference(),
            };
            editedValues = {...originalValues};
        } catch (e) {
            debug.error('PreferencesTab', 'loadSettings failed', e);
        } finally {
            isLoading = false;
        }
    }

    // Check if a field has been modified (reactive computed)
    $: languageModified = editedValues.language !== originalValues.language;
    $: currencyModified = editedValues.default_currency !== originalValues.default_currency;
    $: themeModified = editedValues.theme !== originalValues.theme;

    // Check if a field is non-default (compared to global defaults)
    $: languageNonDefault = originalValues.language !== globalDefaults.language;
    $: currencyNonDefault = originalValues.default_currency !== globalDefaults.default_currency;
    $: themeNonDefault = originalValues.theme !== globalDefaults.theme;

    // Check if any field is modified
    $: hasChanges = languageModified || currencyModified || themeModified;

    // Filter settings by category
    // Avatar is always shown at the top, regardless of category selection
    function getCategoryFields(categoryId: string): (keyof typeof editedValues)[] {
        switch (categoryId) {
            case 'display':
                return ['language'];
            case 'currency':
                return ['default_currency'];
            case 'appearance':
                return ['theme'];
            default:
                return ['language', 'default_currency', 'theme'];
        }
    }

    // Get visible fields (avatar is always visible, handled separately in template)
    $: visibleFields = selectedCategory === '' ? (['language', 'default_currency', 'theme'] as const) : (getCategoryFields(selectedCategory) as (keyof typeof editedValues)[]);

    // Single field actions
    async function saveField(field: keyof typeof editedValues) {
        isSaving = true;
        error = null;
        success = null;

        try {
            if (field === 'language') {
                currentLanguage.set(editedValues.language as SupportedLocale);
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({language: editedValues.language});
                // Sync userSettings store
                userSettings.setDirect({
                    language: editedValues.language,
                    base_currency: editedValues.default_currency,
                    theme: editedValues.theme,
                });
            } else if (field === 'default_currency') {
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({base_currency: editedValues.default_currency});
                // Sync userSettings store
                userSettings.setDirect({
                    language: editedValues.language,
                    base_currency: editedValues.default_currency,
                    theme: editedValues.theme,
                });
            } else if (field === 'theme') {
                applyTheme(editedValues.theme as 'light' | 'dark' | 'auto');
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({theme: editedValues.theme});
                // Sync userSettings store
                userSettings.setDirect({
                    language: editedValues.language,
                    base_currency: editedValues.default_currency,
                    theme: editedValues.theme,
                });
            }

            originalValues = {...originalValues, [field]: editedValues[field]};
            success = $_('settings.savedSuccessfully');
            setTimeout(() => (success = null), 3000);
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
                applyTheme(editedValues.theme as 'light' | 'dark' | 'auto');
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({theme: editedValues.theme});
                originalValues.theme = editedValues.theme;
                saved.push($_('settings.theme'));
            }

            // Sync userSettings store after all saves
            if (saved.length > 0) {
                userSettings.setDirect({
                    language: editedValues.language,
                    base_currency: editedValues.default_currency,
                    theme: editedValues.theme,
                });
                success = `${$_('settings.savedSuccessfully')}: ${saved.join(', ')}`;
            }
            setTimeout(() => (success = null), 4000);
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
</script>

<SettingsLayout bind:selectedCategory {categories} {hasChanges} hasNonDefaults={false} isLocked={false} on:resetAll={resetAll} on:saveAll={saveAll} on:undoAll={undoAll} showLock={false} title={$_('settings.userPreferences')}>
    <!-- Success/Error Messages -->
    {#if success}
        <div class="mb-4 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg text-green-700 dark:text-green-300 text-sm">
            {success}
        </div>
    {/if}
    <InfoBanner class="mb-4" dismissible message={error} ondismiss={() => (error = '')} variant="error" />

    <!-- Settings Fields -->
    {#if isLoading}
        <LoadingSpinner />
    {:else}
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
                    label={$_('settings.defaultCurrency')}
                    hint={$_('settings.defaultCurrencyHint')}
                    isModified={currencyModified}
                    isNonDefault={currencyNonDefault}
                    isLocked={false}
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
