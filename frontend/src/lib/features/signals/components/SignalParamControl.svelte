<script lang="ts">
    import {Info} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import type {SignalParamDescriptor} from '$lib/features/signals';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import SignalAssetParamControl from './SignalAssetParamControl.svelte';
    import {answeredParam} from '$lib/features/signals/answeredParams.svelte';
    import {formatPercent} from '$lib/utils/core/formatPercent';

    import {numericArrows} from '$lib/actions/numericArrows';
    interface Props {
        descriptor: SignalParamDescriptor;
        value: unknown;
        affectsLabel?: string;
        onchange: (value: unknown) => void;
        /** The asset the chart shows, ruled out of a comparison-asset parameter (RN-12b). */
        mainAssetId?: number | null;
        /** The signal instance this parameter belongs to: a value the backend chose is read from its last answer. */
        instanceId?: string;
    }

    let {descriptor, value, affectsLabel = '', onchange, mainAssetId = null, instanceId = ''}: Props = $props();

    /** The rate the chart's answer was computed with, in percent, or null before an answer (RN-21, B). */
    let answeredRatePercent = $derived.by((): number | null => {
        if (descriptor.control !== 'risk_free_rate' || !instanceId) return null;
        const answered = answeredParam(instanceId, descriptor.key);
        return typeof answered === 'number' && Number.isFinite(answered) ? Number((answered * 100).toFixed(6)) : null;
    });

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
    <span class="text-[10px] text-lf-muted uppercase">
        {translatedLabel()}
    </span>
    {#if descriptor.tooltip}
        <Tooltip text={$t(descriptor.tooltip)} math position="top">
            <Info size={12} class="text-lf-muted hover:text-lf-link cursor-help transition-colors" />
        </Tooltip>
    {/if}
    {#if affectsLabel}
        <span class="rounded bg-lf-panel px-1.5 py-0.5 text-[9px] normal-case text-lf-muted">
            {$t('signals.visual.affects')}: {affectsLabel}
        </span>
    {/if}

    {#if descriptor.control === 'comparison_asset'}
        <SignalAssetParamControl {value} {mainAssetId} onchange={(assetId) => onchange(assetId)} />
    {:else if descriptor.control === 'risk_free_rate'}
        <!-- RN-21: the reader's one risk-free rate, shared with the risk pages; the request takes it from the same store
             (`requestBuilder`), so no field here can say another figure. The line says the rate of the answer the chart
             draws, never the field's: «0 %» while the series is still at 0 % is true (the consultant, B); before an
             answer, no figure. -->
        <Tooltip text={$t('signals.riskFreeRate.where')} position="top">
            <span class="text-xs text-lf-secondary" data-testid="signal-param-risk-free-rate" data-percent={answeredRatePercent ?? ''}>
                {$t('signals.riskFreeRate.uses', {values: {rate: answeredRatePercent === null ? '—' : formatPercent(answeredRatePercent, {signed: false, trim: true, digits: 4})}})}
            </span>
        </Tooltip>
    {:else if descriptor.type === 'number'}
        <div class="flex items-center gap-1">
            <input
                type="number"
                use:numericArrows
                value={numberValue()}
                min={descriptor.min}
                max={descriptor.max}
                step={descriptor.step}
                class="w-16 px-1.5 py-0.5 text-xs border border-lf-input rounded bg-lf-field text-lf-primary hover:border-lf-input-hover focus:ring-1 focus:ring-lf-focus"
                oninput={(event) => handleNumberInput(event.currentTarget.value)}
            />
            {#if descriptor.suffix}
                <span class="text-[10px] text-lf-muted">{translatedSuffix()}</span>
            {/if}
        </div>
    {:else if descriptor.type === 'boolean'}
        <input type="checkbox" checked={value === true} class="h-4 w-4 accent-lf-checked" onchange={(event) => onchange(event.currentTarget.checked)} />
    {:else if descriptor.type === 'select'}
        <div class="w-36">
            <SimpleSelect value={stringValue()} options={descriptor.options ?? []} dropdownPosition="auto" onchange={(selected) => onchange(selected)} />
        </div>
    {:else}
        <input type="text" value={stringValue()} class="w-24 px-1.5 py-0.5 text-xs border border-lf-input rounded bg-lf-field text-lf-primary hover:border-lf-input-hover focus:ring-1 focus:ring-lf-focus" oninput={(event) => onchange(event.currentTarget.value)} />
    {/if}
</div>
