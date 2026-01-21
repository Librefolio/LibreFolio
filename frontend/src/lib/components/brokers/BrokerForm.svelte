<script lang="ts">
    /**
     * BrokerForm - Form for creating or editing a broker
     */
    import {createEventDispatcher, onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {api} from '$lib/api';
    import {userSettings} from '$lib/stores/settings';
    import FuzzySelect from '$lib/components/FuzzySelect.svelte';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import type {SelectOption} from '$lib/components/FuzzySelect.svelte';
    import {Plus, Trash2, Info} from 'lucide-svelte';

    const dispatch = createEventDispatcher<{
        submit: {
            name: string;
            description?: string;
            portal_url?: string;
            icon_url?: string;
            default_import_plugin?: string;
            allow_cash_overdraft: boolean;
            allow_asset_shorting: boolean;
            is_active: boolean;
            opened_at?: string;
            initial_balances?: Array<{ code: string; amount: number }>;
        };
        cancel: void;
    }>();

    // Props
    export let mode: 'create' | 'edit' = 'create';
    export let initialData: {
        name?: string;
        description?: string | null;
        portal_url?: string | null;
        icon_url?: string | null;
        default_import_plugin?: string | null;
        allow_cash_overdraft?: boolean;
        allow_asset_shorting?: boolean;
        is_active?: boolean;
        opened_at?: string | null;
    } = {};
    export let loading = false;

    // Debug flag - set to false in production
    const DEBUG = false;
    function log(...args: any[]) {
        if (DEBUG) console.log('[BrokerForm]', ...args);
    }

    // Get today's date in YYYY-MM-DD format
    function getTodayDate(): string {
        return new Date().toISOString().split('T')[0];
    }

    // Parse date from backend (may be ISO datetime) to YYYY-MM-DD
    function parseDate(dateStr: string | null | undefined): string {
        if (!dateStr) return '';
        // Try to parse as date
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return '';
            return d.toISOString().split('T')[0];
        } catch {
            return '';
        }
    }

    // Form state - use reactive statements to sync with initialData
    let name = '';
    let description = '';
    let portalUrl = '';
    let iconUrl = '';
    let defaultImportPlugin = '';
    let allowOverdraft = false;
    let allowShorting = false;
    let isActive = true;
    let openedAt = '';

    // Track initialData key to detect when it changes
    $: initialDataKey = JSON.stringify(initialData);
    let prevInitialDataKey = '';

    // Reset form when initialData changes
    $: if (initialDataKey !== prevInitialDataKey) {
        log('initialDataKey changed:', prevInitialDataKey.slice(0, 50), '->', initialDataKey.slice(0, 50));
        prevInitialDataKey = initialDataKey;
        resetForm();
    }

    function resetForm() {
        log('resetForm called with initialData:', initialData);
        name = initialData.name ?? '';
        description = initialData.description ?? '';
        portalUrl = initialData.portal_url ?? '';
        iconUrl = initialData.icon_url ?? '';
        defaultImportPlugin = initialData.default_import_plugin ?? '';
        allowOverdraft = initialData.allow_cash_overdraft ?? false;
        allowShorting = initialData.allow_asset_shorting ?? false;
        isActive = initialData.is_active ?? true;
        openedAt = parseDate(initialData.opened_at) || (mode === 'create' ? getTodayDate() : '');
        log('Form fields set to:', { name, description, portalUrl, iconUrl, defaultImportPlugin, allowOverdraft, allowShorting, isActive, openedAt });
    }

    // Initial balances (only for create mode)
    let initialBalances: Array<{ code: string; amount: number }> = [];

    // Currency options for FuzzySelect
    let currencyOptions: SelectOption[] = [];
    let loadingCurrencies = true;

    // Import plugins for select
    let importPlugins: Array<{ id: string; name: string; description: string; icon?: string }> = [];
    let loadingPlugins = true;

    // Load currencies and plugins on mount
    onMount(async () => {
        // Load currencies
        try {
            const response = await api.get<{
                currencies: Array<{
                    code: string;
                    name: string;
                    symbol?: string;
                }>;
                count: number;
            }>('/utilities/currencies');

            currencyOptions = response.currencies.map(c => ({
                code: c.code,
                label: c.name,
                icon: c.symbol && c.symbol !== c.code ? c.symbol : undefined
            }));
        } catch (e) {
            console.error('Failed to load currencies:', e);
        } finally {
            loadingCurrencies = false;
        }

        // Load import plugins
        try {
            const response = await api.get<Array<{
                code: string;
                name: string;
                description: string;
                supported_extensions: string[];
                icon_url?: string;
            }>>('/brokers/import/plugins');

            // Backend returns array directly, not {plugins: [...]}
            // Sort: broker_generic_csv first with "(default)" suffix, rest alphabetically
            const plugins = (response || []).map(p => ({
                id: p.code,
                name: p.code === 'broker_generic_csv' ? `${p.name} (default)` : p.name,
                description: p.description,
                icon: p.icon_url
            }));

            importPlugins = plugins.sort((a, b) => {
                if (a.id === 'broker_generic_csv') return -1;
                if (b.id === 'broker_generic_csv') return 1;
                return a.name.localeCompare(b.name);
            });
        } catch (e) {
            console.error('Failed to load import plugins:', e);
        } finally {
            loadingPlugins = false;
        }
    });

    // Validation
    $: isValid = name.trim().length >= 1 && name.trim().length <= 100;

    // Check for duplicate currencies in initial balances
    $: hasDuplicateCurrencies = new Set(initialBalances.map(b => b.code)).size !== initialBalances.length;

    // Get user's default currency
    $: defaultCurrency = $userSettings?.default_currency ?? 'EUR';

    // Get selected plugin info (for tooltip/description)
    $: selectedPlugin = importPlugins.find(p => p.id === defaultImportPlugin);


    function addBalance() {
        // First balance uses user's default currency, subsequent ones find unused
        const usedCodes = new Set(initialBalances.map(b => b.code));
        let newCode = defaultCurrency;

        if (usedCodes.has(defaultCurrency)) {
            // Find a currency not already used
            const available = currencyOptions.find(c => !usedCodes.has(c.code));
            newCode = available?.code ?? 'EUR';
        }

        initialBalances = [...initialBalances, {
            code: newCode,
            amount: 0
        }];
    }

    function removeBalance(index: number) {
        initialBalances = initialBalances.filter((_, i) => i !== index);
    }

    function handleSubmit() {
        if (!isValid || loading) return;

        // Filter out zero/negative amounts
        const validBalances = initialBalances.filter(b => b.amount > 0);

        // For edit mode: send empty string "" to clear fields, undefined to skip update
        // For create mode: undefined means "don't include field"
        const trimmedDescription = description.trim();
        const trimmedPortalUrl = portalUrl.trim();
        const trimmedIconUrl = iconUrl.trim();
        const trimmedPlugin = defaultImportPlugin?.trim() || '';

        dispatch('submit', {
            name: name.trim(),
            // In edit mode, empty string means "clear field"
            // In create mode, undefined means "don't include"
            description: mode === 'edit'
                ? (trimmedDescription || "")
                : (trimmedDescription || undefined),
            portal_url: mode === 'edit'
                ? (trimmedPortalUrl || "")
                : (trimmedPortalUrl || undefined),
            icon_url: mode === 'edit'
                ? (trimmedIconUrl || "")
                : (trimmedIconUrl || undefined),
            default_import_plugin: mode === 'edit'
                ? (trimmedPlugin || "")
                : (trimmedPlugin || undefined),
            allow_cash_overdraft: allowOverdraft,
            allow_asset_shorting: allowShorting,
            is_active: isActive,
            opened_at: openedAt || undefined,
            initial_balances: mode === 'create' && validBalances.length > 0 ? validBalances : undefined
        });
    }

    function handleCancel() {
        dispatch('cancel');
    }
</script>

<form on:submit|preventDefault={handleSubmit} class="space-y-5">
    <!-- Name -->
    <div>
        <label for="broker-name" class="block text-sm font-medium text-gray-700 mb-1">
            {$_('brokers.name')} *
        </label>
        <input
                id="broker-name"
                type="text"
                bind:value={name}
                placeholder={$_('brokers.namePlaceholder')}
                required
                minlength="1"
                maxlength="100"
                class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
                class:border-red-300={name.length > 0 && name.trim().length === 0}
        />
    </div>

    <!-- Description -->
    <div>
        <label for="broker-description" class="block text-sm font-medium text-gray-700 mb-1">
            {$_('brokers.description')}
        </label>
        <textarea
                id="broker-description"
                bind:value={description}
                placeholder={$_('brokers.descriptionPlaceholder')}
                rows="3"
                maxlength="500"
                class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors resize-none"
        ></textarea>
    </div>

    <!-- Default Import Plugin (moved up) -->
    <div>
        <label for="broker-plugin" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {$_('brokers.defaultImportPlugin')}
        </label>
        <div class="flex items-center gap-2">
            {#if selectedPlugin?.icon}
                <img
                    src={selectedPlugin.icon}
                    alt=""
                    class="w-6 h-6 rounded object-cover"
                    on:error={(e) => {
                        const target = e.currentTarget;
                        if (target instanceof HTMLImageElement) target.style.display = 'none';
                    }}
                />
            {/if}
            <select
                    id="broker-plugin"
                    bind:value={defaultImportPlugin}
                    class="flex-1 px-3 py-2 border dark:border-slate-600 dark:bg-slate-700 dark:text-white rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
                    disabled={loadingPlugins}
            >
                <option value="">{loadingPlugins ? $_('common.loading') : $_('brokers.selectPlugin')}</option>
                {#each importPlugins as plugin}
                    <option value={plugin.id}>{plugin.name}</option>
                {/each}
            </select>
            {#if selectedPlugin?.description}
                <Tooltip text={selectedPlugin.description} position="left" maxWidth="350px">
                    <span class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help">
                        <Info size={16}/>
                    </span>
                </Tooltip>
            {/if}
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{$_('brokers.defaultImportPluginHint')}</p>
    </div>

    <!-- Portal URL -->
    <div>
        <label for="broker-portal" class="block text-sm font-medium text-gray-700 mb-1">
            {$_('brokers.portalUrl')}
        </label>
        <input
                id="broker-portal"
                type="url"
                bind:value={portalUrl}
                placeholder={$_('brokers.portalUrlPlaceholder')}
                class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
        />
    </div>

    <!-- Icon URL -->
    <div>
        <label for="broker-icon" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {$_('brokers.iconUrl')}
        </label>
        <div class="flex items-center gap-3">
            <input
                    id="broker-icon"
                    type="url"
                    bind:value={iconUrl}
                    placeholder={$_('brokers.iconUrlPlaceholder')}
                    class="flex-1 px-3 py-2 border dark:border-slate-600 dark:bg-slate-700 dark:text-white rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
            />
            <!-- Icon preview using BrokerIcon component -->
            <BrokerIcon
                iconUrl={iconUrl}
                portalUrl={portalUrl}
                pluginCode={defaultImportPlugin}
                altText="Preview"
                size="md"
            />
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{$_('brokers.iconUrlHint')}</p>
    </div>

    <!-- Account Status: Opened At + Is Active Toggle (same row) -->
    <div class="flex flex-col sm:flex-row sm:items-end gap-4">
        <!-- Opened At -->
        <div class="flex-1">
            <label for="broker-opened" class="block text-sm font-medium text-gray-700 mb-1">
                {$_('brokers.openedAt')}
            </label>
            <input
                    id="broker-opened"
                    type="date"
                    bind:value={openedAt}
                    class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
            />
        </div>

        <!-- Is Active Toggle -->
        <div class="flex items-center gap-3 pb-2">
            <span class="text-sm text-gray-700">{$_('brokers.isActive')}</span>
            <button
                    type="button"
                    role="switch"
                    aria-checked={isActive}
                    aria-label={$_('brokers.isActive')}
                    on:click={() => isActive = !isActive}
                    class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-libre-green focus:ring-offset-2"
                    class:bg-libre-green={isActive}
                    class:bg-gray-300={!isActive}
            >
                <span
                        class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                        class:translate-x-5={isActive}
                        class:translate-x-0={!isActive}
                ></span>
            </button>
        </div>
    </div>

    <!-- Trading Flags (vertical layout with instant tooltips) -->
    <div class="space-y-3 border rounded-lg p-4 bg-gray-50 dark:bg-slate-800 dark:border-slate-700">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">{$_('brokers.tradingOptions')}</h4>

        <!-- Allow Leveraged Buying -->
        <div class="flex items-start gap-3">
            <label class="flex items-center gap-2 cursor-pointer flex-1">
                <input
                        type="checkbox"
                        bind:checked={allowOverdraft}
                        class="w-4 h-4 text-libre-green rounded focus:ring-libre-green"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">{$_('brokers.allowOverdraft')}</span>
            </label>
            {#if !allowOverdraft}
                <Tooltip text={$_('brokers.allowOverdraftHint')} position="left" maxWidth="320px">
                    <span class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help">
                        <Info size={16}/>
                    </span>
                </Tooltip>
            {/if}
        </div>
        {#if allowOverdraft}
            <p class="text-xs text-gray-500 dark:text-gray-400 ml-6 -mt-1">{$_('brokers.allowOverdraftHint')}</p>
        {/if}

        <!-- Allow Short Selling -->
        <div class="flex items-start gap-3">
            <label class="flex items-center gap-2 cursor-pointer flex-1">
                <input
                        type="checkbox"
                        bind:checked={allowShorting}
                        class="w-4 h-4 text-libre-green rounded focus:ring-libre-green"
                />
                <span class="text-sm text-gray-700 dark:text-gray-300">{$_('brokers.allowShorting')}</span>
            </label>
            {#if !allowShorting}
                <Tooltip text={$_('brokers.allowShortingHint')} position="left" maxWidth="320px">
                    <span class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help">
                        <Info size={16}/>
                    </span>
                </Tooltip>
            {/if}
        </div>
        {#if allowShorting}
            <p class="text-xs text-gray-500 dark:text-gray-400 ml-6 -mt-1">{$_('brokers.allowShortingHint')}</p>
        {/if}
    </div>

    <!-- Initial Balances (only for create mode) -->
    {#if mode === 'create'}
        <div class="border-t pt-5">
            <div class="flex items-center justify-between mb-3">
                <div>
                    <h4 class="text-sm font-medium text-gray-700">{$_('brokers.initialBalances')}</h4>
                    <p class="text-xs text-gray-500 mt-0.5">{$_('brokers.initialBalancesHint')}</p>
                </div>
                <button
                        type="button"
                        on:click={addBalance}
                        disabled={loadingCurrencies}
                        class="flex items-center space-x-1 px-3 py-1.5 text-sm bg-libre-green/10 text-libre-green rounded-lg hover:bg-libre-green/20 transition-colors disabled:opacity-50"
                >
                    <Plus size={16}/>
                    <span>{$_('brokers.addCurrency')}</span>
                </button>
            </div>

            {#if initialBalances.length > 0}
                <div class="space-y-3">
                    {#each initialBalances as balance, i (i)}
                        <div class="flex items-center gap-2">
                            <!-- Amount first (60% width) -->
                            <div class="flex-[6]">
                                <input
                                        type="number"
                                        step="0.01"
                                        min="0"
                                        bind:value={balance.amount}
                                        placeholder={$_('brokers.amount')}
                                        class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green h-[42px]"
                                />
                            </div>

                            <!-- Currency Select (40% width, dropdown opens upward) -->
                            <div class="flex-[4] min-w-[120px]">
                                <FuzzySelect
                                        bind:value={balance.code}
                                        options={currencyOptions}
                                        placeholder={$_('settings.selectCurrency')}
                                        loading={loadingCurrencies}
                                        dropdownPosition="top"
                                />
                            </div>

                            <!-- Remove -->
                            <button
                                    type="button"
                                    on:click={() => removeBalance(i)}
                                    class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors shrink-0"
                            >
                                <Trash2 size={18}/>
                            </button>
                        </div>
                    {/each}
                </div>

                {#if hasDuplicateCurrencies}
                    <p class="text-sm text-amber-600 mt-2">⚠️ {$_('brokers.duplicateCurrencies')}</p>
                {/if}
            {/if}
        </div>
    {/if}
</form>

<!-- Actions (sempre visibili - fuori dal form scrollabile) -->
<div class="flex items-center justify-end space-x-3 pt-4 mt-4 border-t border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 sticky bottom-0 pb-4 px-4 -mx-4 -mb-4 rounded-b-2xl">
    <button
            type="button"
            on:click={handleCancel}
            disabled={loading}
            class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
    >
        {$_('common.cancel')}
    </button>
    <button
            type="button"
            on:click={handleSubmit}
            disabled={!isValid || loading || hasDuplicateCurrencies}
            class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    >
        {#if loading}
            <span class="inline-flex items-center space-x-2">
                <span class="animate-spin">⏳</span>
                <span>{$_('common.loading')}</span>
            </span>
        {:else}
            {mode === 'create' ? $_('common.create') : $_('common.save')}
        {/if}
    </button>
</div>
