<script lang="ts">
    import {_, type SupportedLocale} from '$lib/i18n';
    import {availableLanguages, currentLanguage} from '$lib/stores/app/language';
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
    import {notify} from '$lib/stores/app/notify.svelte';
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
    let selectedCategory: string = '';

    // Language options
    const languageOptions: SelectOption[] = availableLanguages.map((l) => ({
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
    $: hasNonDefaults = languageNonDefault || currencyNonDefault || themeNonDefault;

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

    type PreferenceField = keyof typeof editedValues;

    function fieldLabel(field: PreferenceField): string {
        if (field === 'language') return $_('settings.language');
        if (field === 'default_currency') return $_('settings.defaultCurrency');
        return $_('settings.theme');
    }

    function savePayload(field: PreferenceField) {
        if (field === 'language') return {language: editedValues.language};
        if (field === 'default_currency') return {base_currency: editedValues.default_currency};
        return {theme: editedValues.theme};
    }

    function applyPersistedSideEffect(field: PreferenceField) {
        if (field === 'language') {
            currentLanguage.set(editedValues.language as SupportedLocale);
        } else if (field === 'theme') {
            applyTheme(editedValues.theme as 'light' | 'dark' | 'auto');
        }
    }

    function syncPersistedPreferences(values = originalValues) {
        userSettings.setDirect({
            language: values.language,
            base_currency: values.default_currency,
            theme: values.theme,
        });
    }

    function failureMessage(e: unknown): string {
        if (isAxiosError(e)) return e.message;
        return $_('settings.saveFailed');
    }

    // Single field actions
    async function saveField(field: PreferenceField) {
        isSaving = true;
        error = null;

        try {
            await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put(savePayload(field));
            const nextValues = {...originalValues, [field]: editedValues[field]};
            originalValues = nextValues;
            applyPersistedSideEffect(field);
            syncPersistedPreferences(nextValues);
            notify({
                name: 'settings.preferences.saved',
                detail: {fields: 1, field, value: editedValues[field]},
                toast: {variant: 'success', message: $_('settings.savedSuccessfully')},
            });
        } catch (e) {
            error = failureMessage(e);
            notify({
                name: 'settings.preferences.save.failed',
                detail: {field, reason: error},
                toast: {variant: 'error', message: $_('settings.preferencesSaveFailed')},
            });
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

        const fields: PreferenceField[] = [];
        if (languageModified) fields.push('language');
        if (currencyModified) fields.push('default_currency');
        if (themeModified) fields.push('theme');

        const saved: {field: PreferenceField; label: string}[] = [];
        const failed: {field: PreferenceField; label: string; reason: string}[] = [];
        let nextValues = {...originalValues};

        for (const field of fields) {
            try {
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put(savePayload(field));
                nextValues = {...nextValues, [field]: editedValues[field]};
                saved.push({field, label: fieldLabel(field)});
                applyPersistedSideEffect(field);
            } catch (e) {
                failed.push({field, label: fieldLabel(field), reason: failureMessage(e)});
            }
        }

        originalValues = nextValues;
        if (saved.length > 0) syncPersistedPreferences(nextValues);

        if (failed.length > 0) {
            error = failed.map((f) => `${f.label}: ${f.reason}`).join('\n');
        }

        if (saved.length > 0 || failed.length > 0) {
            const savedList = saved.map((s) => `<li>${s.label}</li>`).join('');
            const failedList = failed.map((f) => `<li>${f.label}</li>`).join('');
            const message =
                failed.length === 0
                    ? `${$_('settings.savedSuccessfully')}:<ul class="mt-1 list-inside list-disc">${savedList}</ul>`
                    : `${$_(saved.length === 0 ? 'settings.preferencesSaveFailed' : 'settings.preferencesSavePartial')}:<div class="mt-1">${$_('settings.savedFields')}</div><ul class="list-inside list-disc">${savedList}</ul><div class="mt-1">${$_('settings.failedFields')}</div><ul class="list-inside list-disc">${failedList}</ul>`;
            notify({
                name: failed.length === 0 ? 'settings.preferences.saved' : saved.length === 0 ? 'settings.preferences.save.failed' : 'settings.preferences.save.partial',
                detail: {
                    fields: saved.length,
                    saved: saved.map((s) => s.field),
                    failed: failed.map((f) => f.field),
                    reasons: Object.fromEntries(failed.map((f) => [f.field, f.reason])),
                    language: nextValues.language,
                    currency: nextValues.default_currency,
                    theme: nextValues.theme,
                },
                toast: {variant: failed.length === 0 ? 'success' : saved.length === 0 ? 'error' : 'warning', message},
            });
        }

        isSaving = false;
    }

    function undoAll() {
        editedValues = {...originalValues};
    }

    function resetAll() {
        editedValues = {...globalDefaults};
    }
</script>

<SettingsLayout bind:selectedCategory {categories} {hasChanges} {hasNonDefaults} isBusy={isLoading || isSaving} {isSaving} isLocked={false} onresetAll={resetAll} onsaveAll={saveAll} onundoAll={undoAll} showLock={false} title={$_('settings.userPreferences')}>
    <!-- Error message (success is a toast: see notify() above) -->
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
                    {isSaving}
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
                    {isSaving}
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
                    {isSaving}
                    onsave={() => saveField('theme')}
                    onundo={() => undoField('theme')}
                    onreset={() => resetField('theme')}
                />
            </div>
        {/if}
    {/if}
</SettingsLayout>
