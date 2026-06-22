<!--
  BrokerSearchSelect.svelte - Svelte 5

  Broker selection dropdown using SearchSelect with inline search.
  Replaces the old BrokerSelect component.
-->
<script lang="ts">
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import {getRoleIcon, getRoleIconColor} from '$lib/utils/broker/brokerRoleHelpers';
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
        user_role?: string | null;
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
        /** W43/W44: "Create new" footer label. When set, shows a sticky footer. */
        createLabel?: string;
        /** W43/W44: Callback when "Create new" footer is clicked. */
        onCreateNew?: () => void;
        onchange?: (brokerId: number | null) => void;
    }

    let {brokers, value = $bindable(null), placeholder = '', disabled = false, disabledIds = new Set(), dropdownPosition = 'auto', maxVisibleItems = 6, createLabel = '', onCreateNew, onchange}: Props = $props();

    // Convert brokers to SelectOption format
    let brokerOptions: SelectOption[] = $derived(
        brokers.map((b) => ({
            value: String(b.id),
            label: b.name,
            searchText: b.name,
            data: b,
            disabled: disabledIds.has(b.id),
        })),
    );

    // Convert numeric value to string for SearchSelect
    let stringValue = $derived(value != null ? String(value) : '');

    /** Helper to safely cast option.data to BrokerSelectItem. */
    function asBroker(data: unknown): BrokerSelectItem {
        return data as BrokerSelectItem;
    }

    function handleChange(newValue: string) {
        const numericValue = newValue ? parseInt(newValue, 10) : null;
        value = numericValue;
        onchange?.(numericValue);
    }
</script>

<SearchSelect {disabled} {dropdownPosition} inlineSearch={true} {maxVisibleItems} onchange={handleChange} options={brokerOptions} placeholder={placeholder || $_('uploads.selectBroker')} value={stringValue} {createLabel} {onCreateNew}>
    {#snippet item(option)}
        {@const broker = asBroker(option.data)}
        {@const RoleIcon = broker.user_role ? getRoleIcon(broker.user_role) : null}
        <div class="flex items-center gap-2">
            <BrokerIcon iconUrl={broker.icon_url} portalUrl={broker.portal_url} pluginCode={broker.default_import_plugin} altText={broker.name} size="sm" />
            <span class="truncate">{broker.name}</span>
            {#if RoleIcon}
                <RoleIcon size={14} class={getRoleIconColor(broker.user_role)} />
            {/if}
        </div>
    {/snippet}
    {#snippet selectedItem(option)}
        {@const broker = asBroker(option.data)}
        {@const RoleIcon = broker.user_role ? getRoleIcon(broker.user_role) : null}
        <div class="flex items-center gap-2">
            <BrokerIcon iconUrl={broker.icon_url} portalUrl={broker.portal_url} pluginCode={broker.default_import_plugin} altText={broker.name} size="sm" />
            <span class="truncate">{broker.name}</span>
            {#if RoleIcon}
                <RoleIcon size={14} class={getRoleIconColor(broker.user_role)} />
            {/if}
        </div>
    {/snippet}
</SearchSelect>
