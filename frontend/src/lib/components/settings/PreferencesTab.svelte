<script lang="ts">
    import {_, LANGUAGE_OPTIONS, type SupportedLocale} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {api, ApiError} from '$lib/api';
    import {onMount} from 'svelte';
    import {ChevronRight, Coins, Globe, Palette, RotateCcw, Save, Undo} from 'lucide-svelte';
    import FuzzySelect, {type SelectOption} from '$lib/components/FuzzySelect.svelte';

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

    // Original values (from API)
    let originalValues = {
        language: 'en',
        default_currency: 'EUR',
        theme: 'auto' as 'light' | 'dark' | 'auto'
    };

    // Edited values
    let editedValues = {...originalValues};

    let isLoading = true;
    let isSaving = false;
    let error: string | null = null;
    let success: string | null = null;
    let selectedCategory: string = 'all';

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
                user_id: number;
                default_currency: string | null;
                default_language: string | null;
            }>('/settings/user');

            originalValues = {
                language: response.default_language || $currentLanguage,
                default_currency: response.default_currency || 'EUR',
                theme: getStoredTheme()
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

    // Check if a field has been modified
    function isModified(field: keyof typeof editedValues): boolean {
        return editedValues[field] !== originalValues[field];
    }

    // Check if any field is modified
    $: hasChanges = Object.keys(editedValues).some(k => isModified(k as keyof typeof editedValues));

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
    $: visibleFields = selectedCategory === 'all'
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
                await api.patch('/settings/user', {default_language: editedValues.language});
            } else if (field === 'default_currency') {
                await api.patch('/settings/user', {default_currency: editedValues.default_currency});
            } else if (field === 'theme') {
                // Theme is stored locally
                localStorage.setItem('librefolio-theme', editedValues.theme === 'auto' ? '' : editedValues.theme);
                document.documentElement.classList.remove('light', 'dark');
                if (editedValues.theme !== 'auto') {
                    document.documentElement.classList.add(editedValues.theme);
                }
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
        const defaults = {
            language: 'en',
            default_currency: 'EUR',
            theme: 'auto' as const
        };
        editedValues = {...editedValues, [field]: defaults[field]};
    }

    // Bulk actions
    async function saveAll() {
        isSaving = true;
        error = null;
        success = null;

        const saved: string[] = [];

        try {
            // Save language
            if (isModified('language')) {
                currentLanguage.set(editedValues.language as SupportedLocale);
                await api.patch('/settings/user', {default_language: editedValues.language});
                originalValues.language = editedValues.language;
                saved.push($_('settings.language'));
            }

            // Save currency
            if (isModified('default_currency')) {
                await api.patch('/settings/user', {default_currency: editedValues.default_currency});
                originalValues.default_currency = editedValues.default_currency;
                saved.push($_('settings.defaultCurrency'));
            }

            // Save theme
            if (isModified('theme')) {
                localStorage.setItem('librefolio-theme', editedValues.theme === 'auto' ? '' : editedValues.theme);
                document.documentElement.classList.remove('light', 'dark');
                if (editedValues.theme !== 'auto') {
                    document.documentElement.classList.add(editedValues.theme);
                }
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
        editedValues = {
            language: 'en',
            default_currency: 'EUR',
            theme: 'auto'
        };
    }
</script>

<div class="flex flex-col lg:flex-row gap-6">
    <!-- Left Sidebar: Categories -->
    <div class="lg:w-48 shrink-0">
        <nav class="space-y-1">
            <!-- All -->
            <button
                on:click={() => selectedCategory = 'all'}
                class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors
                       {selectedCategory === 'all' ? 'bg-libre-green text-white' : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-700'}"
            >
                <span>{$_('settings.categoryAll')}</span>
                <ChevronRight size={16} class="opacity-50" />
            </button>

            <!-- Categories -->
            {#each categories as category (category.id)}
                <button
                    on:click={() => selectedCategory = category.id}
                    class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors
                           {selectedCategory === category.id ? 'bg-libre-green text-white' : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-700'}"
                >
                    <div class="flex items-center gap-2">
                        <svelte:component this={category.icon} size={16} />
                        <span>{$_(category.labelKey)}</span>
                    </div>
                    <ChevronRight size={16} class="opacity-50" />
                </button>
            {/each}
        </nav>
    </div>

    <!-- Right Content: Settings -->
    <div class="flex-1 min-w-0">
        <!-- Top Actions Bar -->
        <div class="flex items-center justify-end gap-2 mb-4 pb-4 border-b border-gray-200 dark:border-slate-700">
            {#if hasChanges}
                <button
                    on:click={undoAll}
                    disabled={isSaving}
                    class="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                    title={$_('common.undoAll')}
                >
                    <Undo size={18} />
                </button>
                <button
                    on:click={saveAll}
                    disabled={isSaving}
                    class="p-2 text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors disabled:opacity-50"
                    title={$_('common.saveAll')}
                >
                    <Save size={18} />
                </button>
            {/if}
            <button
                on:click={resetAll}
                disabled={isSaving}
                class="p-2 text-gray-500 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-colors disabled:opacity-50"
                title={$_('common.resetAll')}
            >
                <RotateCcw size={18} />
            </button>
        </div>

        <!-- Success/Error Messages -->
        {#if success}
            <div class="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
                {success}
            </div>
        {/if}
        {#if error}
            <div class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
            </div>
        {/if}

        <!-- Settings List -->
        {#if isLoading}
            <div class="text-center py-8 text-gray-500">{$_('common.loading')}</div>
        {:else}
            <div class="space-y-6">
                <!-- Language -->
                {#if visibleFields.includes('language')}
                    <div class="p-4 border border-gray-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800">
                        <div class="flex items-start justify-between gap-4">
                            <div class="flex-1 min-w-0">
                                <label class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-200">
                                    <Globe class="mr-2 text-libre-green" size={18}/>
                                    {$_('settings.language')}
                                </label>
                                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{$_('settings.languageHint')}</p>
                            </div>
                            <!-- Actions -->
                            {#if isModified('language')}
                                <div class="flex items-center gap-1">
                                    <button on:click={() => undoField('language')} class="p-1.5 text-gray-400 hover:text-gray-600" title={$_('common.undo')}>
                                        <Undo size={14} />
                                    </button>
                                    <button on:click={() => saveField('language')} disabled={isSaving} class="p-1.5 text-libre-green hover:bg-libre-green/10 rounded" title={$_('common.save')}>
                                        <Save size={14} />
                                    </button>
                                </div>
                            {:else}
                                <button on:click={() => resetField('language')} class="p-1.5 text-gray-400 hover:text-amber-600" title={$_('common.reset')}>
                                    <RotateCcw size={14} />
                                </button>
                            {/if}
                        </div>
                        <div class="mt-3">
                            <select
                                bind:value={editedValues.language}
                                class="w-full max-w-xs px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100
                                       focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-all"
                            >
                                {#each languageOptions as lang}
                                    <option value={lang.code}>{lang.icon} {lang.label}</option>
                                {/each}
                            </select>
                        </div>
                    </div>
                {/if}

                <!-- Default Currency -->
                {#if visibleFields.includes('default_currency')}
                    <div class="p-4 bg-gray-50 dark:bg-slate-800/50 rounded-lg">
                        <div class="flex items-start justify-between gap-4">
                            <div class="flex-1 min-w-0">
                                <label class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-200">
                                    <Coins class="mr-2 text-libre-green" size={18}/>
                                    {$_('settings.defaultCurrency')}
                                </label>
                                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{$_('settings.defaultCurrencyHint')}</p>
                            </div>
                            <!-- Actions -->
                            {#if isModified('default_currency')}
                                <div class="flex items-center gap-1">
                                    <button on:click={() => undoField('default_currency')} class="p-1.5 text-gray-400 hover:text-gray-600" title={$_('common.undo')}>
                                        <Undo size={14} />
                                    </button>
                                    <button on:click={() => saveField('default_currency')} disabled={isSaving} class="p-1.5 text-libre-green hover:bg-libre-green/10 rounded" title={$_('common.save')}>
                                        <Save size={14} />
                                    </button>
                                </div>
                            {:else}
                                <button on:click={() => resetField('default_currency')} class="p-1.5 text-gray-400 hover:text-amber-600" title={$_('common.reset')}>
                                    <RotateCcw size={14} />
                                </button>
                            {/if}
                        </div>
                        <div class="mt-3 max-w-sm">
                            <FuzzySelect
                                bind:value={editedValues.default_currency}
                                options={currencyOptions}
                                placeholder={$_('settings.selectCurrency')}
                                loading={currenciesLoading}
                            />
                        </div>
                    </div>
                {/if}

                <!-- Theme -->
                {#if visibleFields.includes('theme')}
                    <div class="p-4 bg-gray-50 dark:bg-slate-800/50 rounded-lg">
                        <div class="flex items-start justify-between gap-4">
                            <div class="flex-1 min-w-0">
                                <label class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-200">
                                    <Palette class="mr-2 text-libre-green" size={18}/>
                                    {$_('settings.theme')}
                                </label>
                                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{$_('settings.themeHint')}</p>
                            </div>
                            <!-- Actions -->
                            {#if isModified('theme')}
                                <div class="flex items-center gap-1">
                                    <button on:click={() => undoField('theme')} class="p-1.5 text-gray-400 hover:text-gray-600" title={$_('common.undo')}>
                                        <Undo size={14} />
                                    </button>
                                    <button on:click={() => saveField('theme')} disabled={isSaving} class="p-1.5 text-libre-green hover:bg-libre-green/10 rounded" title={$_('common.save')}>
                                        <Save size={14} />
                                    </button>
                                </div>
                            {:else}
                                <button on:click={() => resetField('theme')} class="p-1.5 text-gray-400 hover:text-amber-600" title={$_('common.reset')}>
                                    <RotateCcw size={14} />
                                </button>
                            {/if}
                        </div>
                        <div class="mt-3 flex flex-wrap gap-3">
                            {#each ['light', 'dark', 'auto'] as themeOption}
                                <label
                                    class="flex items-center gap-2 px-4 py-2 border rounded-lg cursor-pointer transition-all
                                           {editedValues.theme === themeOption
                                             ? 'border-libre-green bg-libre-green/10 text-libre-green'
                                             : 'border-gray-300 dark:border-slate-600 text-gray-600 dark:text-gray-300 hover:border-gray-400'}"
                                >
                                    <input
                                        type="radio"
                                        name="theme"
                                        value={themeOption}
                                        bind:group={editedValues.theme}
                                        class="sr-only"
                                    />
                                    <span>{$_(`settings.theme${themeOption.charAt(0).toUpperCase() + themeOption.slice(1)}`)}</span>
                                </label>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>
        {/if}
    </div>
</div>

