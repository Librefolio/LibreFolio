<script lang="ts">
    /**
     * BrokerForm - Form for creating or editing a broker
     */
    import {createEventDispatcher, onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {userSettings} from '$lib/stores/settings';
    import {CurrencySearchSelect, ImportPluginSelect} from '$lib/components/ui/select';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import {ImagePickerWrapper} from '$lib/components/ui/media';
    import SingleDatePicker from '$lib/components/ui/SingleDatePicker.svelte';
    import {Info, Plus, Trash2, Upload} from 'lucide-svelte';

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
            initial_balances?: Array<{code: string; amount: number}>;
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
        log('Form fields set to:', {name, description, portalUrl, iconUrl, defaultImportPlugin, allowOverdraft, allowShorting, isActive, openedAt});
    }

    // Initial balances (only for create mode)
    let initialBalances: Array<{code: string; amount: number}> = [];

    // Load user settings on mount
    onMount(async () => {
        // Bug 2 fix: Load user settings if not already available
        // This ensures base_currency is available for the initial balance selector
        if (!$userSettings) {
            await userSettings.load();
        }
    });

    // Validation
    $: isValid = name.trim().length >= 1 && name.trim().length <= 100;

    // Check for duplicate currencies in initial balances
    $: hasDuplicateCurrencies = new Set(initialBalances.map((b) => b.code)).size !== initialBalances.length;

    // Get user's default currency
    $: defaultCurrency = $userSettings?.base_currency ?? 'EUR';

    // Image picker state (uses ImagePickerWrapper)
    let showImagePicker = false;

    function handleImagePickerChange(url: string) {
        iconUrl = url;
        showImagePicker = false;
    }

    function addBalance() {
        // First balance uses user's default currency, subsequent ones find unused
        const usedCodes = new Set(initialBalances.map((b) => b.code));
        let newCode = defaultCurrency;

        if (usedCodes.has(defaultCurrency)) {
            // Find a common currency not already used
            const commonCurrencies = ['EUR', 'USD', 'GBP', 'CHF', 'JPY', 'CAD', 'AUD', 'CNY'];
            const available = commonCurrencies.find((c) => !usedCodes.has(c));
            newCode = available ?? 'EUR';
        }

        initialBalances = [
            ...initialBalances,
            {
                code: newCode,
                amount: 0,
            },
        ];
    }

    function removeBalance(index: number) {
        initialBalances = initialBalances.filter((_, i) => i !== index);
    }

    function handleSubmit() {
        if (!isValid || loading) return;

        // Filter out zero/negative amounts
        const validBalances = initialBalances.filter((b) => b.amount > 0);

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
            description: mode === 'edit' ? trimmedDescription || '' : trimmedDescription || undefined,
            portal_url: mode === 'edit' ? trimmedPortalUrl || '' : trimmedPortalUrl || undefined,
            icon_url: mode === 'edit' ? trimmedIconUrl || '' : trimmedIconUrl || undefined,
            default_import_plugin: mode === 'edit' ? trimmedPlugin || '' : trimmedPlugin || undefined,
            allow_cash_overdraft: allowOverdraft,
            allow_asset_shorting: allowShorting,
            is_active: isActive,
            opened_at: openedAt || undefined,
            initial_balances: mode === 'create' && validBalances.length > 0 ? validBalances : undefined,
        });
    }

    function handleCancel() {
        dispatch('cancel');
    }
</script>

<form class="space-y-5" on:submit|preventDefault={handleSubmit}>
    <!-- Name -->
    <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="broker-name">
            {$_('common.name')} *
        </label>
        <input
            bind:value={name}
            class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors"
            class:border-red-300={name.length > 0 && name.trim().length === 0}
            data-testid="broker-name-input"
            id="broker-name"
            maxlength="100"
            minlength="1"
            placeholder={$_('brokers.namePlaceholder')}
            required
            type="text"
        />
    </div>

    <!-- Description -->
    <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="broker-description">
            {$_('brokers.description')}
        </label>
        <textarea bind:value={description} class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors resize-none" id="broker-description" maxlength="500" placeholder={$_('brokers.descriptionPlaceholder')} rows="3"></textarea>
    </div>

    <!-- Default Import Plugin (moved up) -->
    <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" for="broker-plugin">
            {$_('brokers.defaultImportPlugin')}
        </label>
        <ImportPluginSelect bind:value={defaultImportPlugin} placeholder={$_('brokers.selectPlugin')} />
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{$_('brokers.defaultImportPluginHint')}</p>
    </div>

    <!-- Portal URL -->
    <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="broker-portal">
            {$_('brokers.portalUrl')}
        </label>
        <input bind:value={portalUrl} class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-colors" id="broker-portal" placeholder={$_('brokers.portalUrlPlaceholder')} type="url" />
    </div>

    <!-- Icon -->
    <div>
        <span class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {$_('brokers.iconUrl')}
        </span>
        <div class="flex items-center gap-3">
            <!-- Clickable Icon Preview - opens AssetPickerModal -->
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="icon-picker-trigger group relative cursor-pointer" data-testid="broker-icon-trigger" on:click={() => (showImagePicker = true)} title={$_('uploads.selectIcon') || 'Select Icon'}>
                <BrokerIcon altText="Icon" {iconUrl} pluginCode={defaultImportPlugin} {portalUrl} size="lg" />
                <div class="absolute inset-0 rounded-full bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                    <Upload class="text-white" size={16} />
                </div>
            </div>
            <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-500 dark:text-gray-400">{$_('brokers.iconUrlHint')}</p>
                {#if iconUrl}
                    <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5 truncate" title={iconUrl}>{iconUrl}</p>
                {/if}
            </div>
        </div>
    </div>

    <!-- Account Status: Opened At + Is Active Toggle (same row) -->
    <div class="flex flex-col sm:flex-row sm:items-end gap-4">
        <!-- Opened At -->
        <div class="flex-1">
            <SingleDatePicker
                value={openedAt}
                onchange={(d) => {
                    openedAt = d;
                }}
                label={$_('brokers.openedAt')}
                allowFuture={false}
            />
        </div>

        <!-- Is Active Toggle -->
        <div class="flex items-center gap-3 pb-2">
            <span class="text-sm text-gray-700">{$_('brokers.isActive')}</span>
            <button
                aria-checked={isActive}
                aria-label={$_('brokers.isActive')}
                class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-libre-green focus:ring-offset-2"
                class:bg-gray-300={!isActive}
                class:bg-libre-green={isActive}
                on:click={() => (isActive = !isActive)}
                role="switch"
                type="button"
            >
                <span class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out" class:translate-x-0={!isActive} class:translate-x-5={isActive}></span>
            </button>
        </div>
    </div>

    <!-- Trading Flags (vertical layout with instant tooltips) -->
    <div class="space-y-3 border rounded-lg p-4 bg-gray-50 dark:bg-slate-800 dark:border-slate-700">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">{$_('brokers.tradingOptions')}</h4>

        <!-- Allow Leveraged Buying -->
        <div class="flex items-start gap-3">
            <label class="flex items-center gap-2 cursor-pointer flex-1">
                <input bind:checked={allowOverdraft} class="w-4 h-4 text-libre-green rounded focus:ring-libre-green" type="checkbox" />
                <span class="text-sm text-gray-700 dark:text-gray-300">{$_('brokers.allowOverdraft')}</span>
            </label>
            {#if !allowOverdraft}
                <Tooltip text={$_('brokers.allowOverdraftHint')} position="left" maxWidth="320px">
                    <span class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help">
                        <Info size={16} />
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
                <input bind:checked={allowShorting} class="w-4 h-4 text-libre-green rounded focus:ring-libre-green" type="checkbox" />
                <span class="text-sm text-gray-700 dark:text-gray-300">{$_('brokers.allowShorting')}</span>
            </label>
            {#if !allowShorting}
                <Tooltip text={$_('brokers.allowShortingHint')} position="left" maxWidth="320px">
                    <span class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help">
                        <Info size={16} />
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
                <button type="button" on:click={addBalance} class="flex items-center space-x-1 px-3 py-1.5 text-sm bg-libre-green/10 text-libre-green rounded-lg hover:bg-libre-green/20 transition-colors disabled:opacity-50">
                    <Plus size={16} />
                    <span>{$_('brokers.addCurrency')}</span>
                </button>
            </div>

            {#if initialBalances.length > 0}
                <div class="space-y-3">
                    {#each initialBalances as balance, i (i)}
                        <div class="flex items-center gap-2">
                            <!-- Amount first (60% width) -->
                            <div class="flex-[6]">
                                <input type="number" step="0.01" min="0" bind:value={balance.amount} placeholder={$_('brokers.amount')} class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-libre-green focus:border-libre-green h-[42px]" />
                            </div>

                            <!-- Currency Select (40% width, dropdown opens upward) -->
                            <div class="flex-[4] min-w-[120px]">
                                <CurrencySearchSelect bind:value={balance.code} placeholder={$_('settings.selectCurrency')} dropdownPosition="top" />
                            </div>

                            <!-- Remove -->
                            <button type="button" on:click={() => removeBalance(i)} class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors shrink-0">
                                <Trash2 size={18} />
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

<!-- Image Picker (AssetPicker + ImageEditModal combined) -->
<ImagePickerWrapper circularPreview={true} filterImages={true} initialUrl={iconUrl} oncancel={() => (showImagePicker = false)} onchange={handleImagePickerChange} open={showImagePicker} preset="broker-icon" title={$_('uploads.selectIcon') || 'Select Icon'} />

<!-- Actions (sempre visibili - fuori dal form scrollabile) -->
<div class="flex items-center justify-end space-x-3 pt-4 mt-4 border-t border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 sticky bottom-0 pb-4 px-4 -mx-4 -mb-4 rounded-b-2xl">
    <button class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors" disabled={loading} on:click={handleCancel} type="button">
        {$_('common.cancel')}
    </button>
    <button class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed" data-testid="broker-form-submit" disabled={!isValid || loading || hasDuplicateCurrencies} on:click={handleSubmit} type="button">
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
