<!--
  BrokerSearchSelect.svelte - Svelte 5

  Broker selection dropdown using SearchSelect with inline search.
  Replaces the old BrokerSelect component.
-->
<script lang="ts">
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import {_} from '$lib/i18n';

    /**
     * Minimum broker info needed for the select component.
     */
    interface BrokerSelectItem {
        id: number;
        name: string;
        icon_url?: string | null;
        portal_url?: string | null;
        default_import_plugin?: string | null;
    }

    interface Props {
        brokers: BrokerSelectItem[];
        value: number | null;
        placeholder?: string;
        disabled?: boolean;
        /** Broker IDs that should appear greyed-out / non-selectable */
        disabledIds?: Set<number>;
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        maxVisibleItems?: number;
        onchange?: (brokerId: number | null) => void;
    }

    let {
        brokers,
        value = $bindable(null),
        placeholder = '',
        disabled = false,
        disabledIds = new Set(),
        dropdownPosition = 'auto',
        maxVisibleItems = 6,
        onchange
    }: Props = $props();

    // Convert brokers to SelectOption format
    let brokerOptions = $derived<SelectOption[]>(
        brokers.map(b => ({
            value: String(b.id),
            label: b.name,
            searchText: b.name,
            data: b,
            disabled: disabledIds.has(b.id),
        }))
    );

    // Convert numeric value to string for SearchSelect
    let stringValue = $derived(value != null ? String(value) : '');

    // Get selected broker for display
    let selectedBroker = $derived(
        value != null ? brokers.find(b => b.id === value) : null
    );

    function handleChange(newValue: string) {
        const numericValue = newValue ? parseInt(newValue, 10) : null;
        value = numericValue;
        onchange?.(numericValue);
    }
</script>

<SearchSelect
        {disabled}
        {dropdownPosition}
        inlineSearch={true}
        {maxVisibleItems}
        onchange={handleChange}
        options={brokerOptions}
        placeholder={placeholder || $_('uploads.selectBroker')}
        value={stringValue}
>
    {#snippet item(option)}
        {@const broker = option.data as BrokerSelectItem}
        <div class="flex items-center gap-2">
            <BrokerIcon
                    iconUrl={broker.icon_url}
                    portalUrl={broker.portal_url}
                    pluginCode={broker.default_import_plugin}
                    altText={broker.name}
                    size="sm"
            />
            <span class="truncate">{broker.name}</span>
        </div>
    {/snippet}
    {#snippet selectedItem(option)}
        {@const broker = option.data as BrokerSelectItem}
        <div class="flex items-center gap-2">
            <BrokerIcon
                    iconUrl={broker.icon_url}
                    portalUrl={broker.portal_url}
                    pluginCode={broker.default_import_plugin}
                    altText={broker.name}
                    size="sm"
            />
            <span class="truncate">{broker.name}</span>
        </div>
    {/snippet}
</SearchSelect>
