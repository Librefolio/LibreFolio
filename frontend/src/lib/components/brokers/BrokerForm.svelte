<script lang="ts">
    /**
     * BrokerForm - Form for creating or editing a broker
     */
    import {createEventDispatcher, onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {api} from '$lib/api';
    import {userSettings} from '$lib/stores/settings';
    import FuzzySelect from '$lib/components/FuzzySelect.svelte';
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

    // Get today's date in YYYY-MM-DD format
    function getTodayDate(): string {
        return new Date().toISOString().split('T')[0];
    }

    // Form state
    let name = initialData.name ?? '';
    let description = initialData.description ?? '';
    let portalUrl = initialData.portal_url ?? '';
    let iconUrl = initialData.icon_url ?? '';
    let defaultImportPlugin = initialData.default_import_plugin ?? '';
    let allowOverdraft = initialData.allow_cash_overdraft ?? false;
    let allowShorting = initialData.allow_asset_shorting ?? false;
    let isActive = initialData.is_active ?? true;
    let openedAt = initialData.opened_at ?? (mode === 'create' ? getTodayDate() : '');

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
            const response = await api.get<{
                plugins: Array<{
                    id: string;
                    name: string;
                    description: string;
                    icon?: string;
                }>;
            }>('/brokers/import/plugins');

            importPlugins = response.plugins || [];
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

    // Get selected plugin info (for icon fallback)
    $: selectedPlugin = importPlugins.find(p => p.id === defaultImportPlugin);

    // Computed icon URL: custom > favicon from portal > plugin icon
    $: effectiveIconUrl = iconUrl ||
        (portalUrl ? getFaviconUrl(portalUrl) : null) ||
        selectedPlugin?.icon ||
        null;

    function getFaviconUrl(url: string): string | null {
        try {
            const parsed = new URL(url);
            return `${parsed.origin}/favicon.ico`;
        } catch {
            return null;
        }
    }

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

        dispatch('submit', {
            name: name.trim(),
            description: description.trim() || undefined,
            portal_url: portalUrl.trim() || undefined,
            icon_url: iconUrl.trim() || undefined,
            default_import_plugin: defaultImportPlugin || undefined,
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
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
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
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors resize-none"
        ></textarea>
    </div>

    <!-- Default Import Plugin (moved up) -->
    <div>
        <label for="broker-plugin" class="block text-sm font-medium text-gray-700 mb-1">
            {$_('brokers.defaultImportPlugin')}
        </label>
        <select
                id="broker-plugin"
                bind:value={defaultImportPlugin}
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
                disabled={loadingPlugins}
        >
            <option value="">{$_('brokers.selectPlugin')}</option>
            {#each importPlugins as plugin}
                <option value={plugin.id}>{plugin.name}</option>
            {/each}
        </select>
        <p class="text-xs text-gray-500 mt-1">{$_('brokers.defaultImportPluginHint')}</p>
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
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
        />
    </div>

    <!-- Icon URL -->
    <div>
        <label for="broker-icon" class="block text-sm font-medium text-gray-700 mb-1">
            {$_('brokers.iconUrl')}
        </label>
        <div class="flex items-center gap-3">
            <input
                    id="broker-icon"
                    type="url"
                    bind:value={iconUrl}
                    placeholder={$_('brokers.iconUrlPlaceholder')}
                    class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
            />
            {#if effectiveIconUrl}
                <img
                    src={effectiveIconUrl}
                    alt=""
                    class="w-10 h-10 rounded-full object-cover bg-gray-100"
                    on:error={(e) => e.currentTarget.style.display = 'none'}
                />
            {/if}
        </div>
        <p class="text-xs text-gray-500 mt-1">{$_('brokers.iconUrlHint')}</p>
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
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
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
    <div class="space-y-3 border rounded-lg p-4 bg-gray-50">
        <h4 class="text-sm font-medium text-gray-700 mb-2">{$_('brokers.tradingOptions')}</h4>

        <!-- Allow Leveraged Buying -->
        <div class="flex items-start gap-3">
            <label class="flex items-center gap-2 cursor-pointer flex-1">
                <input
                        type="checkbox"
                        bind:checked={allowOverdraft}
                        class="w-4 h-4 text-libre-green border-gray-300 rounded focus:ring-libre-green"
                />
                <span class="text-sm text-gray-700">{$_('brokers.allowOverdraft')}</span>
            </label>
            {#if !allowOverdraft}
                <span
                        class="p-1 text-gray-400 hover:text-gray-600 cursor-help"
                        title={$_('brokers.allowOverdraftHint')}
                >
                    <Info size={16}/>
                </span>
            {/if}
        </div>
        {#if allowOverdraft}
            <p class="text-xs text-gray-500 ml-6 -mt-1">{$_('brokers.allowOverdraftHint')}</p>
        {/if}

        <!-- Allow Short Selling -->
        <div class="flex items-start gap-3">
            <label class="flex items-center gap-2 cursor-pointer flex-1">
                <input
                        type="checkbox"
                        bind:checked={allowShorting}
                        class="w-4 h-4 text-libre-green border-gray-300 rounded focus:ring-libre-green"
                />
                <span class="text-sm text-gray-700">{$_('brokers.allowShorting')}</span>
            </label>
            {#if !allowShorting}
                <span
                        class="p-1 text-gray-400 hover:text-gray-600 cursor-help"
                        title={$_('brokers.allowShortingHint')}
                >
                    <Info size={16}/>
                </span>
            {/if}
        </div>
        {#if allowShorting}
            <p class="text-xs text-gray-500 ml-6 -mt-1">{$_('brokers.allowShortingHint')}</p>
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
                            <!-- Amount first (70% width) -->
                            <div class="flex-[7]">
                                <input
                                        type="number"
                                        step="0.01"
                                        min="0"
                                        bind:value={balance.amount}
                                        placeholder={$_('brokers.amount')}
                                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green h-[42px]"
                                />
                            </div>

                            <!-- Currency Select (30% width, dropdown opens upward) -->
                            <div class="flex-[3] min-w-[120px]">
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

    <!-- Actions (sempre visibili) -->
    <div class="flex items-center justify-end space-x-3 pt-4 border-t">
        <button
                type="button"
                on:click={handleCancel}
                disabled={loading}
                class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
        >
            {$_('common.cancel')}
        </button>
        <button
                type="submit"
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
</form>
