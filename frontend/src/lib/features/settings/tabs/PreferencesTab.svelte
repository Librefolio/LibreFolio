<script lang="ts">
    import {_, type SupportedLocale} from '$lib/i18n';
    import {availableLanguages, currentLanguage} from '$lib/stores/app/language';
    import {userSettings} from '$lib/stores/app/settings';
    import {applyTheme, type ThemePreference} from '$lib/stores/app/themeStore';
    import {FALLBACK_UI_PREFERENCE_DEFAULTS, ownUiPreference, uiPreferenceDefault} from '$lib/stores/app/uiPreferences';
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
    import type {LineShape} from '$lib/components/charts/lineShape';
    import {applySavedGlobalLineShape} from '$lib/stores/chartSettingsStore.svelte';
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
        theme: FALLBACK_UI_PREFERENCE_DEFAULTS.theme,
        chart_line_shape: FALLBACK_UI_PREFERENCE_DEFAULTS.chart_line_shape,
    };

    /**
     * The values of the tab, saved or being edited. The theme and the line shape are interface preferences (lot UIP): the
     * user's own value, or `null` when they follow the administrator's default. Like the language and the currency, a change
     * to them — «back to the global default» included — stays a draft until Save (UIP-2).
     */
    interface PreferenceValues {
        language: string;
        default_currency: string;
        theme: ThemePreference | null;
        chart_line_shape: LineShape | null;
    }

    type PreferenceField = keyof PreferenceValues;
    type UiPreferenceField = 'theme' | 'chart_line_shape';

    const UI_PREFERENCE_FIELDS: UiPreferenceField[] = ['theme', 'chart_line_shape'];
    const ALL_FIELDS: PreferenceField[] = ['language', 'default_currency', 'theme', 'chart_line_shape'];

    function isUiPreferenceField(field: PreferenceField): field is UiPreferenceField {
        return field === 'theme' || field === 'chart_line_shape';
    }

    // Global defaults (the language and the currency from the global settings, the interface preferences from the user settings)
    let globalDefaults = $state({...FALLBACK_DEFAULTS});

    // Original values (from API - user's current settings)
    let originalValues: PreferenceValues = $state({language: FALLBACK_DEFAULTS.language, default_currency: FALLBACK_DEFAULTS.default_currency, theme: null, chart_line_shape: null});

    // Edited values
    let editedValues: PreferenceValues = $state({language: FALLBACK_DEFAULTS.language, default_currency: FALLBACK_DEFAULTS.default_currency, theme: null, chart_line_shape: null});

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

    /** The administrator's defaults of the interface preferences, as the user settings carry them (lot UIP). */
    function withUiDefaults(settings: UserSettings) {
        globalDefaults = {...globalDefaults, theme: uiPreferenceDefault(settings, 'theme'), chart_line_shape: uiPreferenceDefault(settings, 'chart_line_shape')};
    }

    async function loadSettings() {
        debug.log('PreferencesTab', 'loadSettings');
        isLoading = true;
        error = null;
        try {
            const response = await zodiosApi.get_user_settings_endpoint_api_v1_settings_user_get();

            debug.log('PreferencesTab', 'loadSettings response', response);
            // The interface preferences come with their defaults (lot UIP): the user's own value, or null for the default.
            withUiDefaults(response);
            originalValues = {
                language: response.language || $currentLanguage,
                default_currency: response.base_currency || 'EUR',
                theme: ownUiPreference(response, 'theme') ?? null,
                chart_line_shape: ownUiPreference(response, 'chart_line_shape') ?? null,
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
    let lineShapeModified = $derived(editedValues.chart_line_shape !== originalValues.chart_line_shape);

    // Check if a field is non-default (compared to global defaults)
    let languageNonDefault = $derived(originalValues.language !== globalDefaults.language);
    let currencyNonDefault = $derived(originalValues.default_currency !== globalDefaults.default_currency);
    // The theme and the line shape are the user's own or follow the administrator's default (lot UIP): «non default» means a saved own value.
    let themeNonDefault = $derived(originalValues.theme !== null);
    let lineShapeNonDefault = $derived(originalValues.chart_line_shape !== null);

    // What the rows show and their badges follow the draft (UIP-2): the value being edited, else the global default.
    let themeShown = $derived(editedValues.theme ?? globalDefaults.theme);
    let lineShapeShown = $derived(editedValues.chart_line_shape ?? globalDefaults.chart_line_shape);

    // Check if any field is modified
    let hasChanges = $derived(languageModified || currencyModified || themeModified || lineShapeModified);
    let hasNonDefaults = $derived(languageNonDefault || currencyNonDefault || themeNonDefault || lineShapeNonDefault);

    // Filter settings by category
    // Avatar is always shown at the top, regardless of category selection
    function getCategoryFields(categoryId: string): PreferenceField[] {
        switch (categoryId) {
            case 'display':
                return ['language'];
            case 'currency':
                return ['default_currency'];
            case 'appearance':
                return ['theme', 'chart_line_shape'];
            case 'onboarding':
                return [];
            default:
                return ALL_FIELDS;
        }
    }

    // Get visible fields (avatar is always visible, handled separately in template)
    let visibleFields = $derived(selectedCategory === '' ? ALL_FIELDS : getCategoryFields(selectedCategory));
    let showOnboarding = $derived(selectedCategory === '' || selectedCategory === 'onboarding');

    function isModified(field: PreferenceField): boolean {
        return editedValues[field] !== originalValues[field];
    }

    function fieldLabel(field: PreferenceField): string {
        if (field === 'language') return $_('settings.language');
        if (field === 'default_currency') return $_('settings.defaultCurrency');
        if (field === 'chart_line_shape') return $_('chartSettings.lineShape');
        return $_('settings.theme');
    }

    /** One PUT for `fields`: the interface preferences go together under `ui_preferences`, where `null` removes the key (lot UIP). */
    function savePayload(fields: PreferenceField[]) {
        const payload: {language?: string; base_currency?: string; ui_preferences?: {theme?: ThemePreference | null; chart_line_shape?: LineShape | null}} = {};
        for (const field of fields) {
            if (field === 'language') payload.language = editedValues.language;
            else if (field === 'default_currency') payload.base_currency = editedValues.default_currency;
            else if (field === 'theme') payload.ui_preferences = {...payload.ui_preferences, theme: editedValues.theme};
            else payload.ui_preferences = {...payload.ui_preferences, chart_line_shape: editedValues.chart_line_shape};
        }
        return payload;
    }

    /** What a saved value changes beyond the server, only once the server has it (UIP-2). */
    function applyPersistedSideEffect(field: PreferenceField, saved: PreferenceValues) {
        if (field === 'language') {
            currentLanguage.set(saved.language as SupportedLocale);
        } else if (field === 'theme') {
            applyTheme(saved.theme ?? globalDefaults.theme);
        } else if (field === 'chart_line_shape' && saved.chart_line_shape !== null) {
            // Every chart follows the new shape, the ones that had a shape of their own included (FB-3). Back to the
            // global default leaves them alone: `userSettings` already carries it to the charts that follow the global one.
            applySavedGlobalLineShape();
        }
    }

    function syncPersistedPreferences(values = originalValues, response?: UserSettings | null) {
        // Merge: setDirect replaces the whole value, and the sidebar reads avatar_url from it. The answer of the write, when
        // there is one, carries the interface preferences the server now holds (lot UIP): the chart store follows them.
        userSettings.setDirect({
            ...userSettings.get(),
            ...(response ?? {}),
            language: values.language,
            base_currency: values.default_currency,
        } as UserSettings);
        if (response) withUiDefaults(response);
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
            const response = await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put(savePayload([field]));
            const nextValues = {...originalValues, [field]: editedValues[field]};
            originalValues = nextValues;
            syncPersistedPreferences(nextValues, response);
            applyPersistedSideEffect(field, nextValues);
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

    /** Undo: the draft goes back to the saved value. No call. */
    function undoField(field: PreferenceField) {
        editedValues = {...editedValues, [field]: originalValues[field]};
    }

    /** Back to the default, as a draft to save (UIP-2): the language and currency take it, the interface preferences follow it (`null`). */
    function resetField(field: PreferenceField) {
        editedValues = {...editedValues, [field]: isUiPreferenceField(field) ? null : globalDefaults[field]};
    }

    // Bulk actions
    async function saveAll() {
        isSaving = true;
        error = null;

        // One PUT for the language, one for the currency, as before; one for the interface preferences together.
        const groups: PreferenceField[][] = [];
        if (languageModified) groups.push(['language']);
        if (currencyModified) groups.push(['default_currency']);
        const uiFields = UI_PREFERENCE_FIELDS.filter((field) => isModified(field));
        if (uiFields.length > 0) groups.push(uiFields);

        const saved: {field: PreferenceField; label: string}[] = [];
        const failed: {field: PreferenceField; label: string; reason: string}[] = [];
        let nextValues = {...originalValues};
        let lastResponse: UserSettings | null = null;
        const savedFields: PreferenceField[] = [];

        for (const fields of groups) {
            try {
                lastResponse = (await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put(savePayload(fields))) ?? lastResponse;
                for (const field of fields) {
                    nextValues = {...nextValues, [field]: editedValues[field]};
                    saved.push({field, label: fieldLabel(field)});
                    savedFields.push(field);
                }
            } catch (e) {
                const reason = failureMessage(e);
                for (const field of fields) failed.push({field, label: fieldLabel(field), reason});
            }
        }

        originalValues = nextValues;
        if (saved.length > 0) {
            syncPersistedPreferences(nextValues, lastResponse);
            for (const field of savedFields) applyPersistedSideEffect(field, nextValues);
        }

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
                    chart_line_shape: nextValues.chart_line_shape,
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
     * Every field back to its default, as drafts to save (UIP-2): the language and the currency take the instance defaults,
     * the theme and the line shape follow the administrator's default again (`null`). Nothing reaches the server before Save.
     */
    function resetAll() {
        editedValues = {language: globalDefaults.language, default_currency: globalDefaults.default_currency, theme: null, chart_line_shape: null};
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
                <!-- A draft like the other rows (UIP-2): the value shown is the draft, else the global default; null follows it -->
                <SettingTheme
                    value={themeShown}
                    onchange={(theme) => (editedValues = {...editedValues, theme})}
                    label={$_('settings.theme')}
                    hint={$_('settings.themeHint')}
                    icon={Palette}
                    followsGlobal={editedValues.theme === null}
                    showAutoBadge={themeShown === 'auto'}
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

        <!-- Line shape of the charts: a draft saved with the row's Save or Save All, kept with the user settings (FB-3, lot UIP, UIP-2) -->
        {#if visibleFields.includes('chart_line_shape')}
            <div class="setting-row flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 py-4 border-b border-lf-subtle text-lf-primary" data-testid="preference-line-shape">
                <div class="flex-1 min-w-0">
                    <div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-lf-secondary">
                        <span>{$_('chartSettings.lineShape')}</span>
                        {#if editedValues.chart_line_shape === null}
                            <PreferenceSourceBadge kind="global" testId="preference-line-shape-badge-global" />
                        {/if}
                    </div>
                    <p class="text-xs text-lf-muted mt-1">{$_('settings.lineShapeHint')}</p>
                </div>
                <div class="flex items-center gap-2 self-end sm:self-auto">
                    <SettingActions isModified={lineShapeModified} isNonDefault={lineShapeNonDefault} {isSaving} onsave={() => saveField('chart_line_shape')} onundo={() => undoField('chart_line_shape')} onreset={() => resetField('chart_line_shape')} />
                    <LineShapePicker value={lineShapeShown} onchange={(shape) => (editedValues = {...editedValues, chart_line_shape: shape})} testIdPrefix="preference-line-shape-picker" />
                </div>
            </div>
        {/if}

        {#if showOnboarding}
            <OnboardingReplaySection />
        {/if}
    {/if}
</SettingsLayout>
