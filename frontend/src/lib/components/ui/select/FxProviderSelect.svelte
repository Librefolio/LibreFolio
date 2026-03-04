<!--
  FxProviderSelect.svelte - Svelte 5

  Reusable FX provider selection dropdown using SearchSelect.
  Loads available providers from /fx/providers API and filters by currency compatibility.

  Features:
  - Loads providers from the FX providers API
  - Filters by base/quote currency compatibility (direct pair support)
  - Shows provider icon (from icon_url or fallback initial), name, code, description
  - Excludes already-added provider codes
  - Disabled state when currencies are not yet selected
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';

    // =========================================================================
    // Types
    // =========================================================================

    export interface FxProviderInfo {
        code: string;
        name: string;
        base_currency: string;
        base_currencies: string[];
        target_currencies: string[];
        description: string;
        icon_url: string | null;
    }

    interface Props {
        /** Selected provider code (bindable) */
        value?: string;
        /** Base currency code — used to filter compatible providers */
        baseCurrency?: string;
        /** Quote currency code — used to filter compatible providers */
        quoteCurrency?: string;
        /** Provider codes to exclude (already added) */
        excludeCodes?: string[];
        /** Disable the select */
        disabled?: boolean;
        /** Custom placeholder */
        placeholder?: string;
        /** Dropdown position */
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        /** Change callback */
        onchange?: (value: string) => void;
        /** Expose loaded providers for parent access */
        onProvidersLoaded?: (providers: FxProviderInfo[]) => void;
    }

    let {
        value = $bindable(''),
        baseCurrency = '',
        quoteCurrency = '',
        excludeCodes = [],
        disabled = false,
        placeholder = '',
        dropdownPosition = 'auto',
        onchange,
        onProvidersLoaded,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let allProviders = $state<FxProviderInfo[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);

    // =========================================================================
    // Derived: compatibility check
    // =========================================================================

    /**
     * A provider is compatible if:
     * (base in base_currencies AND quote in target_currencies)
     * OR
     * (quote in base_currencies AND base in target_currencies)
     */
    function isCompatible(provider: FxProviderInfo, base: string, quote: string): boolean {
        if (!base || !quote) return false;
        const bUpper = base.toUpperCase();
        const qUpper = quote.toUpperCase();
        return (
            (provider.base_currencies.includes(bUpper) && provider.target_currencies.includes(qUpper)) ||
            (provider.base_currencies.includes(qUpper) && provider.target_currencies.includes(bUpper))
        );
    }

    let providerOptions = $derived.by<SelectOption[]>(() => {
        const hasCurrencies = !!baseCurrency && !!quoteCurrency;
        const excludeSet = new Set(excludeCodes);

        return allProviders
            .filter(p => !excludeSet.has(p.code))
            .map(p => {
                const compatible = hasCurrencies ? isCompatible(p, baseCurrency, quoteCurrency) : false;
                return {
                    value: p.code,
                    label: `${p.name} (${p.code})`,
                    searchText: `${p.code} ${p.name} ${p.description}`,
                    disabled: !compatible,
                    icon: p.icon_url || undefined,
                    data: {
                        description: p.description,
                        compatible,
                        icon_url: p.icon_url,
                    },
                } satisfies SelectOption;
            });
    });

    let isDisabled = $derived(disabled || (!baseCurrency || !quoteCurrency));

    // =========================================================================
    // Load providers
    // =========================================================================

    $effect(() => {
        loadProviders();
    });

    async function loadProviders() {
        loading = true;
        error = null;
        try {
            const response = await zodiosApi.list_providers_api_v1_fx_providers_get();
            allProviders = (response as any[]).map((p: any) => ({
                code: p.code,
                name: p.name,
                base_currency: p.base_currency,
                base_currencies: p.base_currencies ?? [p.base_currency],
                target_currencies: p.target_currencies ?? [],
                description: p.description ?? '',
                icon_url: p.icon_url ?? null,
            }));
            onProvidersLoaded?.(allProviders);
        } catch (e) {
            console.error('Failed to load FX providers:', e);
            error = 'Failed to load providers';
        } finally {
            loading = false;
        }
    }

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleChange(newValue: string) {
        value = newValue;
        onchange?.(newValue);
    }

    /** Get provider initials for fallback icon */
    function getInitials(code: string): string {
        return code.slice(0, 2).toUpperCase();
    }

    /** Extract provider data from option */
    function getProvData(option: {data?: unknown}): {description: string; compatible: boolean; icon_url: string | null} | undefined {
        return option.data as {description: string; compatible: boolean; icon_url: string | null} | undefined;
    }
</script>

<SearchSelect
    bind:value
    disabled={isDisabled}
    {dropdownPosition}
    inlineSearch={true}
    {loading}
    maxVisibleItems={6}
    onchange={handleChange}
    options={providerOptions}
    placeholder={placeholder || $_('fx.addPair.addProvider')}
>
    {#snippet item(option)}
        <div class="flex items-center space-x-2 min-w-0 {option.disabled ? 'opacity-40' : ''}">
            <!-- Provider icon -->
            {#if getProvData(option)?.icon_url}
                <img
                    src={getProvData(option)?.icon_url ?? ''}
                    alt={option.value}
                    class="w-6 h-6 rounded-md object-contain bg-gray-50 dark:bg-slate-700 p-0.5 flex-shrink-0"
                />
            {:else}
                <span class="w-6 h-6 flex items-center justify-center rounded-md bg-libre-green/15 text-libre-green text-[10px] font-bold flex-shrink-0">
                    {getInitials(option.value)}
                </span>
            {/if}
            <div class="min-w-0 flex-1">
                <div class="font-medium text-xs text-gray-900 dark:text-gray-100 truncate">
                    {option.label}
                </div>
                {#if getProvData(option)?.description}
                    <div class="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {getProvData(option)?.description}
                    </div>
                {/if}
                {#if option.disabled}
                    <div class="text-[10px] text-amber-500 dark:text-amber-400 mt-0.5">
                        {$_('fx.addPair.providerIncompatible')}
                    </div>
                {/if}
            </div>
        </div>
    {/snippet}
    {#snippet selectedItem(option)}
        <div class="flex items-center space-x-2 min-w-0">
            {#if getProvData(option)?.icon_url}
                <img
                    src={getProvData(option)?.icon_url ?? ''}
                    alt={option.value}
                    class="w-6 h-6 rounded-md object-contain bg-gray-50 dark:bg-slate-700 p-0.5 flex-shrink-0"
                />
            {:else}
                <span class="w-6 h-6 flex items-center justify-center rounded-md bg-libre-green/15 text-libre-green text-[10px] font-bold flex-shrink-0">
                    {getInitials(option.value)}
                </span>
            {/if}
            <div class="min-w-0">
                <div class="font-medium text-xs text-gray-900 dark:text-gray-100">{option.label}</div>
            </div>
        </div>
    {/snippet}
</SearchSelect>

