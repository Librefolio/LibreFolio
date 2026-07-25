<script lang="ts">
    import {Info} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import type {SignalParamDescriptor} from '$lib/charts/signals';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';

    interface Props {
        descriptor: SignalParamDescriptor;
        value: unknown;
        affectsLabel?: string;
        onchange: (value: unknown) => void;
    }

    let {descriptor, value, affectsLabel = '', onchange}: Props = $props();

    function translatedLabel(): string {
        const direct = $t(descriptor.label);
        if (direct !== descriptor.label) return direct;

        const conventionalKey = `chartSettings.params.${descriptor.key}`;
        const conventional = $t(conventionalKey);
        return conventional !== conventionalKey ? conventional : descriptor.label;
    }

    function numberValue(): number {
        if (typeof value === 'number' && Number.isFinite(value)) return value;
        const fallback = Number(descriptor.default ?? 0);
        return Number.isFinite(fallback) ? fallback : 0;
    }

    function stringValue(): string {
        return typeof value === 'string' ? value : String(descriptor.default ?? '');
    }

    function translatedSuffix(): string {
        if (!descriptor.suffix) return '';
        const key = `signals.units.${descriptor.suffix}`;
        const translated = $t(key);
        return translated === key ? descriptor.suffix : translated;
    }

    function handleNumberInput(rawValue: string) {
        const parsed = Number(rawValue);
        if (!Number.isFinite(parsed)) return;
        onchange(descriptor.integer ? Math.round(parsed) : parsed);
    }
</script>

<div class="flex flex-wrap items-center gap-1.5" data-testid="signal-param-{descriptor.key}">
    <span class="text-[10px] text-gray-500 dark:text-gray-400 uppercase">
        {translatedLabel()}
    </span>
    {#if descriptor.tooltip}
        <Tooltip text={$t(descriptor.tooltip)} math position="top">
            <Info size={12} class="text-gray-400 hover:text-libre-green cursor-help transition-colors" />
        </Tooltip>
    {/if}
    {#if affectsLabel}
        <span class="rounded bg-gray-100 px-1.5 py-0.5 text-[9px] normal-case text-gray-500 dark:bg-slate-700 dark:text-gray-400">
            {$t('signals.visual.affects')}: {affectsLabel}
        </span>
    {/if}

    {#if descriptor.type === 'number'}
        <div class="flex items-center gap-1">
            <input
                type="number"
                value={numberValue()}
                min={descriptor.min}
                max={descriptor.max}
                step={descriptor.step}
                class="w-16 px-1.5 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green"
                oninput={(event) => handleNumberInput(event.currentTarget.value)}
            />
            {#if descriptor.suffix}
                <span class="text-[10px] text-gray-400">{translatedSuffix()}</span>
            {/if}
        </div>
    {:else if descriptor.type === 'boolean'}
        <input type="checkbox" checked={value === true} class="h-4 w-4 accent-libre-green" onchange={(event) => onchange(event.currentTarget.checked)} />
    {:else if descriptor.type === 'select'}
        <div class="w-36">
            <SimpleSelect value={stringValue()} options={descriptor.options ?? []} dropdownPosition="auto" onchange={(selected) => onchange(selected)} />
        </div>
    {:else}
        <input type="text" value={stringValue()} class="w-24 px-1.5 py-0.5 text-xs border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:ring-1 focus:ring-libre-green" oninput={(event) => onchange(event.currentTarget.value)} />
    {/if}
</div>
