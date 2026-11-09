<script lang="ts">
    import {_, type SupportedLocale} from '$lib/i18n';
    import {availableLanguages, currentLanguage} from '$lib/stores/app/language';
    import {userSettings} from '$lib/stores/app/settings';
    import {applyTheme, type ThemePreference} from '$lib/stores/app/themeStore';
    import {effectiveUiPreference, followsGlobalUiPreference, uiPreferenceDefault} from '$lib/stores/app/uiPreferences';
    import type {UserSettings} from '$lib/types';
    import {zodiosApi} from '$lib/api';
    import {isAxiosError} from 'axios';
    import {onMount} from 'svelte';
    import {debug} from '$lib/debug';
    import {Coins, Compass, Globe, Palette} from 'lucide-svelte';
    import type {SelectOption} from '$lib/components/ui/select';
    import SettingsLayout from '$lib/features/settings/SettingsLayout.svelte';
    import SettingSelect from '$lib/features/settings/SettingSelect.svelte';
    import SettingCurrency from '$lib/features/settings/SettingCurrency.svelte';
    import SettingTheme from '$lib/features/settings/SettingTheme.svelte';
    import LineShapePicker from '$lib/components/charts/LineShapePicker.svelte';
    import {clearGlobalLineShape, getGlobalLineShape, lineShapeFollowsGlobal, setGlobalLineShape} from '$lib/stores/chartSettingsStore.svelte';
    import SettingActions from '$lib/features/settings/SettingActions.svelte';
    import PreferenceSourceBadge from '$lib/components/ui/PreferenceSourceBadge.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';
    import OnboardingReplaySection from '$lib/features/onboarding/components/OnboardingReplaySection.svelte';

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
        {id: 'onboarding', icon: Compass, labelKey: 'onboarding.settings.category'},
    ];

    // Hardcoded fallback defaults (used only if global settings fail to load)
    const FALLBACK_DEFAULTS = {
        language: 'en',
        default_currency: 'EUR',
        theme: 'auto' as 'light' | 'dark' | 'auto',
    };

    // Global defaults (loaded from server's global settings)
    let globalDefaults = $state({...FALLBACK_DEFAULTS});

    // Original values (from API - user's current settings)
    let originalValues = $state({...FALLBACK_DEFAULTS});

    // Edited values
    let editedValues = $state({...FALLBACK_DEFAULTS});

    let isLoading = $state(true);
    let isSaving = $state(false);
    let error: string | null = $state(null);
    let selectedCategory: string = $state('');

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
                ...globalDefaults,
                language: settingsMap['default_language'] || FALLBACK_DEFAULTS.language,
                default_currency: settingsMap['default_currency'] || FALLBACK_DEFAULTS.default_currency,
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
            // The theme in force and its default come with the user settings (lot UIP): the user's own, else default_theme.
            globalDefaults = {...globalDefaults, theme: uiPreferenceDefault(response, 'theme')};
            originalValues = {
                language: response.language || $currentLanguage,
                default_currency: response.base_currency || 'EUR',
                theme: effectiveUiPreference(response, 'theme'),
            };
            editedValues = {...originalValues};
            userSettings.setDirect({...userSettings.get(), ...response} as UserSettings);
        } catch (e) {
            debug.error('PreferencesTab', 'loadSettings failed', e);
        } finally {
            isLoading = false;
        }
    }

    // Check if a field has been modified (reactive computed)
    let languageModified = $derived(editedValues.language !== originalValues.language);
    let currencyModified = $derived(editedValues.default_currency !== originalValues.default_currency);
    let themeModified = $derived(editedValues.theme !== originalValues.theme);

    // Check if a field is non-default (compared to global defaults)
    let languageNonDefault = $derived(originalValues.language !== globalDefaults.language);
    let currencyNonDefault = $derived(originalValues.default_currency !== globalDefaults.default_currency);
    // The theme and the line shape are the user's own or follow the administrator's default (lot UIP): «non default» means own.
    let themeFollowsGlobal = $derived(followsGlobalUiPreference($userSettings, 'theme'));
    let themeNonDefault = $derived(!themeFollowsGlobal);
    let lineShapeOwn = $derived(!lineShapeFollowsGlobal());

    // Check if any field is modified
    let hasChanges = $derived(languageModified || currencyModified || themeModified);
    let hasNonDefaults = $derived(languageNonDefault || currencyNonDefault || themeNonDefault || lineShapeOwn);

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
            case 'onboarding':
                return [];
            default:
                return ['language', 'default_currency', 'theme'];
        }
    }

    // Get visible fields (avatar is always visible, handled separately in template)
    let visibleFields = $derived(selectedCategory === '' ? (['language', 'default_currency', 'theme'] as const) : (getCategoryFields(selectedCategory) as (keyof typeof editedValues)[]));
    let showOnboarding = $derived(selectedCategory === '' || selectedCategory === 'onboarding');

    type PreferenceField = keyof typeof editedValues;

    function fieldLabel(field: PreferenceField): string {
        if (field === 'language') return $_('settings.language');
        if (field === 'default_currency') return $_('settings.defaultCurrency');
        return $_('settings.theme');
    }

    function savePayload(field: PreferenceField) {
        if (field === 'language') return {language: editedValues.language};
        if (field === 'default_currency') return {base_currency: editedValues.default_currency};
        return {ui_preferences: {theme: editedValues.theme}};
    }

    function applyPersistedSideEffect(field: PreferenceField) {
        if (field === 'language') {
            currentLanguage.set(editedValues.language as SupportedLocale);
        } else if (field === 'theme') {
            applyTheme(editedValues.theme as ThemePreference);
        }
    }

    function syncPersistedPreferences(values = originalValues, response?: UserSettings | null) {
        // Merge: setDirect replaces the whole value, and the sidebar reads avatar_url from it. The answer of the write, when
        // there is one, carries the interface preferences the server now holds (lot UIP).
        userSettings.setDirect({
            ...userSettings.get(),
            ...(response ?? {}),
            language: values.language,
            base_currency: values.default_currency,
        } as UserSettings);
    }

    /**
     * Forget the user's own theme (lot UIP): it follows the administrator's default_theme again, at once. Not an edit to
     * save: the value is removed on the server, which is what «back to the global default» means for this preference.
     */
    async function clearTheme() {
        isSaving = true;
        error = null;
        const ok = await userSettings.updateUiPreference('theme', null);
        isSaving = false;
        if (!ok) {
            error = $_('settings.preferencesSaveFailed');
            notify({name: 'settings.preferences.save.failed', detail: {field: 'theme', reason: 'clear'}, toast: {variant: 'error', message: $_('settings.preferencesSaveFailed')}});
            return;
        }
        const theme = effectiveUiPreference(userSettings.get(), 'theme');
        globalDefaults = {...globalDefaults, theme};
        originalValues = {...originalValues, theme};
        editedValues = {...editedValues, theme};
        applyTheme(theme);
        notify({name: 'settings.preferences.saved', detail: {fields: 1, field: 'theme', value: null}, toast: {variant: 'success', message: $_('settings.savedSuccessfully')}});
    }

    /** Forget the user's own line shape (lot UIP): every chart without a shape of its own follows the administrator's default. */
    async function clearLineShape() {
        const ok = await clearGlobalLineShape();
        notify(
            ok
                ? {name: 'settings.preferences.saved', detail: {fields: 1, field: 'chart_line_shape', value: null}, toast: {variant: 'success', message: $_('settings.savedSuccessfully')}}
                : {name: 'settings.preferences.save.failed', detail: {field: 'chart_line_shape', reason: 'clear'}, toast: {variant: 'error', message: $_('settings.preferencesSaveFailed')}},
        );
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
            const response = await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put(savePayload(field));
            const nextValues = {...originalValues, [field]: editedValues[field]};
            originalValues = nextValues;
            applyPersistedSideEffect(field);
            syncPersistedPreferences(nextValues, response);
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
        if (field === 'theme') {
            void clearTheme();
            return;
        }
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
        let lastResponse: UserSettings | null = null;

        for (const field of fields) {
            try {
                lastResponse = (await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put(savePayload(field))) ?? lastResponse;
                nextValues = {...nextValues, [field]: editedValues[field]};
                saved.push({field, label: fieldLabel(field)});
                applyPersistedSideEffect(field);
            } catch (e) {
                failed.push({field, label: fieldLabel(field), reason: failureMessage(e)});
            }
        }

        originalValues = nextValues;
        if (saved.length > 0) syncPersistedPreferences(nextValues, lastResponse);

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

    /**
     * Language and currency go back to the defaults as edits to save, as before. The theme and the line shape are interface
     * preferences (lot UIP): the user's own value is removed at once, and they follow the administrator's default again.
     */
    function resetAll() {
        editedValues = {...globalDefaults, theme: themeNonDefault ? globalDefaults.theme : editedValues.theme};
        if (themeNonDefault) void clearTheme();
        if (lineShapeOwn) void clearLineShape();
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
                    followsGlobal={themeFollowsGlobal}
                    showAutoBadge={originalValues.theme === 'auto'}
                    badgeTestIdPrefix="preference-theme"
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

        <!-- Line shape of the charts: applied as it is picked, kept with the user settings (FB-3, lot UIP) -->
        {#if visibleFields.includes('theme')}
            <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 py-4 border-b border-lf-subtle text-lf-primary" data-testid="preference-line-shape">
                <div class="flex-1 min-w-0">
                    <div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-lf-secondary">
                        <span>{$_('chartSettings.lineShape')}</span>
                        {#if !lineShapeOwn}
                            <PreferenceSourceBadge kind="global" testId="preference-line-shape-badge-global" />
                        {/if}
                    </div>
                    <p class="text-xs text-lf-muted mt-1">{$_('settings.lineShapeHint')}</p>
                </div>
                <div class="flex items-center gap-2 self-end sm:self-auto">
                    <SettingActions isNonDefault={lineShapeOwn} {isSaving} onreset={() => void clearLineShape()} />
                    <LineShapePicker value={getGlobalLineShape()} onchange={(shape) => void setGlobalLineShape(shape)} testIdPrefix="preference-line-shape-picker" />
                </div>
            </div>
        {/if}

        {#if showOnboarding}
            <OnboardingReplaySection />
        {/if}
    {/if}
</SettingsLayout>
