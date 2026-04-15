<!--
  ProviderAssignmentSection — Reusable provider config + test + URLs.

  Features:
  - Provider select, identifier, identifier type, dynamic params
  - Test Configuration button → POST /assets/provider/probe
  - User URL (editable) + Provider URL (readonly) with links
  - "No Provider" checkbox (in parent panel title, not in dropdown)
  - Results inline with execution_time_ms
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {SimpleSelect} from '$lib/components/ui/select';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import type {SelectOption} from '$lib/components/ui/select';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import {
        AlertCircle,
        AlertTriangle,
        CheckCircle2,
        Circle,
        CircleHelp,
        ClipboardCopy,
        ExternalLink,
        Loader2,
        Play,
    } from 'lucide-svelte';
    import {IDENTIFIER_TYPES} from '$lib/utils/assetTypes';
    import ScheduledInvestmentEditor from './ScheduledInvestmentEditor.svelte';
    import {toasts} from '$lib/stores/toastStore.svelte';

    // =========================================================================
    // Types
    // =========================================================================

    interface ParamField {
        key: string;
        type: string;
        required: boolean;
        description: string;
        options?: string[];
        default?: any;
        placeholder?: string;
        help_url?: string;
    }

    interface ProviderInfo {
        code: string;
        name: string;
        supports_search: boolean;
        params_schema: ParamField[];
        icon_url?: string | null;
        accepted_identifier_types?: string[];
        provider_help_url?: string | null;
    }

    type TestStatus = 'not_tested' | 'testing' | 'passed' | 'failed';

    interface TestResult {
        success: boolean;
        /** Display status: success, error, or warning (not supported) */
        status?: 'success' | 'error' | 'warning';
        label: string;
        detail?: string;
        /** Short human-readable summary for inline display (full detail in tooltip) */
        summary?: string;
        execution_time_ms: number;
        /** Sample price points for history results (tooltip display) */
        samplePrices?: Array<{date: string; close: number}>;
        /** Current price info (tooltip display) */
        priceValue?: number;
        priceCurrency?: string;
        priceDate?: string;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        providerCode?: string;
        identifier?: string;
        identifierType?: string;
        providerParams?: Record<string, any> | null;
        providerUrl?: string | null;
        noProvider?: boolean;
        fetchInterval?: number;
        disabled?: boolean;
        readonly?: boolean;
        onchange?: (data: {
            providerCode: string;
            identifier: string;
            identifierType: string;
            providerParams: Record<string, any> | null;
            noProvider: boolean;
            testStatus: TestStatus;
        }) => void;
    }

    let {
        providerCode = $bindable(''),
        identifier = $bindable(''),
        identifierType = $bindable('TICKER'),
        providerParams = $bindable(null),
        providerUrl = $bindable(null),
        noProvider = $bindable(false),
        fetchInterval = $bindable(1440),
        disabled = false,
        readonly = false,
        onchange,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let providers = $state<ProviderInfo[]>([]);
    let providersLoaded = $state(false);
    let testStatus = $state<TestStatus>('not_tested');
    let testResults = $state<TestResult[]>([]);
    let totalExecutionMs = $state(0);
    let paramsValues = $state<Record<string, any>>({});

    // =========================================================================
    // Derived
    // =========================================================================

    let selectedProvider = $derived(providers.find(p => p.code === providerCode));
    let paramsSchema = $derived(selectedProvider?.params_schema ?? []);

    /** Custom UI component name derived from params_schema meta-field */
    let uiComponent = $derived(
        paramsSchema.find(f => f.key === '_ui_component' && f.type === 'ui_component')?.default as string | undefined
    );
    /** Generic fields for the params form loop (excluding meta-fields like ui_component) */
    let genericFields = $derived(paramsSchema.filter(f => f.type !== 'ui_component'));

    /** Provider options for SimpleSelect (excluding mockprov, no empty option) */
    let providerOptions = $derived<SelectOption[]>(
        providers
            .filter(p => p.code !== 'mockprov')
            .map(p => ({
                value: p.code,
                label: p.name,
                icon: p.icon_url ?? undefined,
            }))
    );

    /** Identifier type options for SimpleSelect — filtered by provider's accepted types */
    let idTypeOptions = $derived.by<SelectOption[]>(() => {
        const accepted = selectedProvider?.accepted_identifier_types;
        const types = (accepted && accepted.length > 0)
            ? IDENTIFIER_TYPES.filter(t => accepted.includes(t))
            : IDENTIFIER_TYPES;
        return types.map(t => ({value: t, label: t}));
    });

    /** True when provider accepts exactly 1 identifier type (auto-set, hide dropdown) */
    let idTypeAutoSet = $derived(
        (selectedProvider?.accepted_identifier_types?.length ?? 0) === 1
    );

    /** True when identifier type is AUTO_GENERATED */
    let isAutoGenerated = $derived(identifierType === 'AUTO_GENERATED');

    /** Dynamic identifier field label based on selected type */
    let identifierLabel = $derived.by(() => {
        if (isAutoGenerated) return null; // hide entire field
        if (!idTypeAutoSet) return $t('assets.provider.identifier');
        switch (identifierType) {
            case 'URL': return 'URL';
            default: return identifierType; // TICKER, ISIN → show as-is
        }
    });

    /** Dynamic identifier placeholder based on selected type */
    let identifierPlaceholder = $derived.by(() => {
        switch (identifierType) {
            case 'URL': return 'https://example.com/price';
            case 'ISIN': return 'IE00B4L5Y983';
            case 'TICKER': return 'AAPL, MSFT…';
            default: return 'AAPL, IE00B4L5Y983, https://...';
        }
    });

    // =========================================================================
    // Lifecycle
    // =========================================================================

    $effect(() => {
        if (!providersLoaded) loadProviders();
    });

    // Sync providerParams → paramsValues
    $effect(() => {
        if (providerParams && typeof providerParams === 'object') {
            paramsValues = {...providerParams};
        }
    });

    // Auto-set identifier type when provider has exactly 1 accepted type
    $effect(() => {
        const accepted = selectedProvider?.accepted_identifier_types;
        if (accepted && accepted.length === 1 && identifierType !== accepted[0]) {
            identifierType = accepted[0];
            emitChange();
        }
    });

    async function loadProviders() {
        try {
            const response = await zodiosApi.list_providers_api_v1_assets_provider_get() as any;
            providers = Array.isArray(response) ? response : [];
            providersLoaded = true;
        } catch (e: any) {
            console.error('Failed to load providers:', e);
        }
    }

    // =========================================================================
    // Handlers
    // =========================================================================

    function emitChange() {
        const computedParams = uiComponent === 'scheduled_investment' ? providerParams : (paramsSchema.length > 0 ? {...paramsValues} : null);
        onchange?.({
            providerCode,
            identifier,
            identifierType,
            providerParams: computedParams,
            noProvider,
            testStatus,
        });
    }

    function handleProviderChange(code: string) {
        providerCode = code;
        paramsValues = {};
        providerParams = null;
        identifier = '';
        testStatus = 'not_tested';
        testResults = [];
        emitChange();
    }

    function handleParamChange(key: string, value: any) {
        paramsValues = {...paramsValues, [key]: value};
        providerParams = {...paramsValues};
        emitChange();
    }

    // =========================================================================
    // Test Configuration
    // =========================================================================

    /** Classify whether a failed test is just a "not supported" warning vs real error */
    function isNotSupportedWarning(detail: string | undefined): boolean {
        if (!detail) return false;
        const lower = detail.toLowerCase();
        return lower.includes('not_implemented') || lower.includes('not supported') || lower.includes('not implemented');
    }

    /** Generate a short human-readable summary from error detail */
    function summarizeError(detail: string | undefined): string {
        if (!detail) return 'Error';
        const lower = detail.toLowerCase();
        if (lower.includes('not_implemented') || lower.includes('not supported') || lower.includes('not implemented')) return 'Not supported';
        if (lower.includes('timeout')) return 'Connection timeout';
        if (lower.includes('not_found') && lower.includes('selector')) return 'Selector not found';
        if (lower.includes('not_found')) return 'Element not found';
        if (lower.includes('http_error') || lower.includes('http error')) return 'HTTP error';
        if (lower.includes('request_error') || lower.includes('request failed')) return 'Connection failed';
        if (lower.includes('parse_error')) return 'Parse error';
        if (lower.includes('missing_params')) return 'Missing parameters';
        return detail.length > 60 ? detail.slice(0, 60) + '…' : detail;
    }

    async function testConfiguration() {
        if (!providerCode || (!identifier && !isAutoGenerated)) return;
        testStatus = 'testing';
        testResults = [];
        totalExecutionMs = 0;

        try {
            const computedParams = uiComponent === 'scheduled_investment' ? providerParams : (paramsSchema.length > 0 ? {...paramsValues} : null);
            const response = await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post({
                provider_code: providerCode,
                identifier: identifier || '__auto__',
                identifier_type: identifierType as any,
                provider_params: computedParams,
                operations: ['current_price', 'history'],
            }) as any;

            const items: TestResult[] = [];

            // Current price
            if (response.current_price) {
                const cp = response.current_price;
                const detail = cp.success
                    ? `${Number(cp.value).toFixed(2)} ${cp.currency ?? ''}${cp.as_of_date ? ` (${cp.as_of_date})` : ''}`
                    : cp.error;
                items.push({
                    success: cp.success,
                    status: cp.success ? 'success' : (isNotSupportedWarning(cp.error) ? 'warning' : 'error'),
                    label: $t('assets.probe.currentPrice'),
                    detail,
                    summary: cp.success ? detail : summarizeError(cp.error),
                    execution_time_ms: cp.execution_time_ms,
                    priceValue: cp.success ? cp.value : undefined,
                    priceCurrency: cp.success ? cp.currency : undefined,
                    priceDate: cp.success ? cp.as_of_date : undefined,
                });
            }

            // History
            if (response.history) {
                const h = response.history;
                const detail = h.success
                    ? `${h.points_count} points${h.date_range ? ` — ${h.date_range}` : ''}`
                    : h.error;
                items.push({
                    success: h.success,
                    status: h.success ? 'success' : (isNotSupportedWarning(h.error) ? 'warning' : 'error'),
                    label: $t('assets.probe.history'),
                    detail,
                    summary: h.success ? detail : summarizeError(h.error),
                    execution_time_ms: h.execution_time_ms,
                    samplePrices: h.success && h.sample_prices ? h.sample_prices : undefined,
                });
            }

            // Propagate currency from current_price to history (for tooltip display)
            const cpCurrency = items.find(r => r.priceCurrency)?.priceCurrency ?? '';
            for (const item of items) {
                if (item.samplePrices && !item.priceCurrency) item.priceCurrency = cpCurrency;
            }

            testResults = items;
            totalExecutionMs = response.total_execution_time_ms ?? 0;
            // passed = all success OR all non-success are just warnings
            const hasRealError = items.some(r => r.status === 'error');
            testStatus = hasRealError ? 'failed' : 'passed';

            // Update providerUrl from probe response
            if (response.provider_url) {
                providerUrl = response.provider_url;
            }
        } catch (e: any) {
            testResults = [{
                success: false,
                status: 'error',
                label: 'Error',
                detail: e?.message || 'Test failed',
                summary: summarizeError(e?.message),
                execution_time_ms: 0,
            }];
            testStatus = 'failed';
        }
        emitChange();
    }

    // =========================================================================
    // Tooltip Helpers
    // =========================================================================

    /** Build rich HTML tooltip for a test result — uses table format for both price types */
    function buildTooltipHtml(result: TestResult): string {
        if (!result.success) return result.detail ?? 'Error';

        const thStyle = 'text-align:left;padding:2px 8px;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.2);';
        const tdStyle = 'padding:2px 8px;';
        const tdRight = 'padding:2px 8px;text-align:right;font-variant-numeric:tabular-nums;';

        // Current Price tooltip — single-row table
        if (result.priceValue !== undefined) {
            let html = '<table style="font-size:12px;border-collapse:collapse;">';
            html += `<tr><th style="${thStyle}">📅 ${$t('common.date')}</th><th style="${thStyle}">💰 ${$t('assets.probe.currentPrice')}</th></tr>`;
            html += `<tr><td style="${tdStyle}">${result.priceDate ?? '—'}</td>`;
            html += `<td style="${tdRight}">${Number(result.priceValue).toFixed(2)} ${result.priceCurrency ?? ''}</td></tr>`;
            html += '</table>';
            return html;
        }

        // History tooltip — multi-row table with sample prices
        if (result.samplePrices && result.samplePrices.length > 0) {
            let html = '<table style="font-size:12px;border-collapse:collapse;">';
            html += `<tr><th style="${thStyle}">📅 ${$t('common.date')}</th><th style="${thStyle}">💰 Close${result.priceCurrency ? ` (${result.priceCurrency})` : ''}</th></tr>`;
            for (const p of result.samplePrices) {
                html += `<tr><td style="${tdStyle}">${p.date}</td><td style="${tdRight}">${Number(p.close).toFixed(2)}</td></tr>`;
            }
            html += '</table>';
            return html;
        }

        return result.detail ?? '—';
    }
</script>

<div class="space-y-3">

    {#if !noProvider}

        <!-- ═══ Row 1: Provider select + Fetch Interval ═══ -->
        <div class="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3">
            <!-- Provider select -->
            <div>
                <span class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    {$t('assets.provider.selectProvider')}
                </span>
                <div class="flex items-center gap-2">
                    <div class="flex-1 min-w-0">
                        <SimpleSelect
                                value={providerCode}
                                options={providerOptions}
                                disabled={disabled || readonly}
                                dropdownPosition="auto"
                                onchange={(v) => handleProviderChange(v)}
                        >
                            {#snippet item(opt)}
                                <div class="flex items-center gap-2">
                                    {#if opt.icon}
                                        <img src={opt.icon} alt="" class="w-4 h-4 rounded-sm object-contain"/>
                                    {/if}
                                    <span>{opt.label}</span>
                                </div>
                            {/snippet}
                            {#snippet selectedItem(opt)}
                                <div class="flex items-center gap-2">
                                    {#if opt.icon}
                                        <img src={opt.icon} alt="" class="w-4 h-4 rounded-sm object-contain"/>
                                    {/if}
                                    <span>{opt.label}</span>
                                </div>
                            {/snippet}
                        </SimpleSelect>
                    </div>
                    {#if selectedProvider?.provider_help_url}
                        <a href={selectedProvider.provider_help_url} target="_blank" rel="noopener noreferrer"
                           class="shrink-0 text-gray-400 hover:text-blue-500 dark:text-gray-500 dark:hover:text-blue-400 transition-colors"
                           title={$t('common.documentation')}
                        >
                            <CircleHelp size={18}/>
                        </a>
                    {/if}
                </div>
            </div>

            <!-- Fetch Interval -->
            <div>
                <span class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    {$t('assets.provider.fetchInterval')} *
                </span>
                <div class="inline-flex items-stretch">
                    <input
                            type="text"
                            value={String(Math.floor(fetchInterval / 60)).padStart(2, '0') + ':' + String(fetchInterval % 60).padStart(2, '0')}
                            placeholder="24:00"
                            onblur={(e) => {
                                const raw = e.currentTarget.value.trim();
                                const match = raw.match(/^(\d{1,3}):(\d{1,2})$/);
                                if (match) {
                                    const h = Math.max(0, Number(match[1]));
                                    const m = Math.min(59, Math.max(0, Number(match[2])));
                                    fetchInterval = h * 60 + m;
                                    e.currentTarget.value = String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
                                } else {
                                    e.currentTarget.value = String(Math.floor(fetchInterval / 60)).padStart(2, '0') + ':' + String(fetchInterval % 60).padStart(2, '0');
                                }
                                emitChange();
                            }}
                            disabled={disabled || readonly}
                            class="w-[4.5rem] px-2 py-2 text-sm text-center font-mono border border-gray-200 dark:border-slate-600 rounded-l-lg
                                   bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                   placeholder-gray-400 dark:placeholder-gray-500
                                   focus:outline-none focus:ring-2 focus:ring-libre-green/50
                                   disabled:opacity-50"
                    />
                    <div class="flex flex-col border border-l-0 border-gray-200 dark:border-slate-600 rounded-r-lg overflow-hidden">
                        <button type="button" tabindex="-1" aria-label="Increase"
                                disabled={disabled || readonly}
                                onclick={() => { fetchInterval = Math.max(1, fetchInterval + 1); emitChange(); }}
                                class="px-1.5 flex-1 flex items-center justify-center text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-gray-200 transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                            <svg viewBox="0 0 10 6" class="w-2.5 h-1.5"><path d="M1 5l4-4 4 4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        </button>
                        <button type="button" tabindex="-1" aria-label="Decrease"
                                disabled={disabled || readonly}
                                onclick={() => { fetchInterval = Math.max(1, fetchInterval - 1); emitChange(); }}
                                class="px-1.5 flex-1 flex items-center justify-center text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-gray-200 transition-colors disabled:opacity-30 disabled:cursor-not-allowed border-t border-gray-200 dark:border-slate-600">
                            <svg viewBox="0 0 10 6" class="w-2.5 h-1.5"><path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        </button>
                    </div>
                </div>
                <p class="mt-1 text-[10px] text-gray-400 dark:text-gray-500">
                    ⓘ 24:00 = daily, 01:00 = hourly, 168:00 = weekly
                </p>
            </div>
        </div>

        <!-- ═══ Row 2: ID Type + Identifier (hidden entirely for AUTO_GENERATED) ═══ -->
        {#if !isAutoGenerated}
            <div class="grid grid-cols-[auto_1fr] gap-3 items-end">
                <!-- Identifier Type -->
                <div class="w-36">
                    <span class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        {$t('assets.provider.identifierType')}
                    </span>
                    {#if idTypeAutoSet}
                        <div class="px-3 py-2 text-sm border border-gray-200 dark:border-slate-700 rounded-lg
                                    bg-gray-50 dark:bg-slate-800 text-gray-500 dark:text-gray-400">
                            {identifierType.replace('_', ' ')}
                        </div>
                    {:else}
                        <SimpleSelect
                                bind:value={identifierType}
                                options={idTypeOptions}
                                disabled={disabled || readonly}
                                dropdownPosition="auto"
                                onchange={() => emitChange()}
                        />
                    {/if}
                </div>

                <!-- Identifier -->
                <div>
                    <label for="provider-identifier" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        {identifierLabel ?? $t('assets.provider.identifier')}
                    </label>
                    <input
                            id="provider-identifier"
                            type="text"
                            bind:value={identifier}
                            oninput={() => { testStatus = 'not_tested'; emitChange(); }}
                            disabled={disabled || readonly}
                            placeholder={identifierPlaceholder}
                            class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                   bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                   placeholder-gray-400 dark:placeholder-gray-500
                                   focus:outline-none focus:ring-2 focus:ring-libre-green/50 focus:border-libre-green
                                   disabled:opacity-50"
                    />
                </div>
            </div>
        {/if}

        <!-- ═══ Dynamic params: custom UI component or generic form loop ═══ -->
        {#if uiComponent === 'scheduled_investment'}
            <ScheduledInvestmentEditor
                value={providerParams ?? {}}
                onchange={(newParams) => { providerParams = newParams; emitChange(); }}
                disabled={disabled}
                readonly={readonly}
            />
        {:else if genericFields.length > 0}
            <div class="space-y-2 pl-3 border-l-2 border-gray-200 dark:border-slate-600">
                {#each genericFields as field}
                    <div>
                        <label for="param-{field.key}" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            {field.description || field.key}
                            {#if field.required}<span class="text-red-500">*</span>{/if}
                        </label>
                        {#if field.type === 'select' && field.options}
                            <SimpleSelect
                                    value={paramsValues[field.key] ?? field.default ?? ''}
                                    options={field.options.map(o => ({value: o, label: o}))}
                                    disabled={disabled || readonly}
                                    dropdownPosition="auto"
                                    onchange={(v) => handleParamChange(field.key, v)}
                            />
                        {:else if field.type === 'currency'}
                            <CurrencySearchSelect
                                    value={paramsValues[field.key] ?? field.default ?? ''}
                                    disabled={disabled || readonly}
                                    dropdownPosition="auto"
                                    placeholder={field.placeholder ?? ''}
                                    onchange={(v) => handleParamChange(field.key, v)}
                            />
                        {:else if field.type === 'number'}
                            <input
                                    type="number"
                                    value={paramsValues[field.key] ?? field.default ?? ''}
                                    placeholder={field.placeholder ?? ''}
                                    oninput={(e) => { const el = e.currentTarget; handleParamChange(field.key, Number(el.value)); }}
                                    disabled={disabled || readonly}
                                    class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                           bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                           focus:outline-none focus:ring-2 focus:ring-libre-green/50
                                           disabled:opacity-50"
                            />
                        {:else}
                            <input
                                    type="text"
                                    value={paramsValues[field.key] ?? field.default ?? ''}
                                    placeholder={field.placeholder ?? ''}
                                    oninput={(e) => { const el = e.currentTarget; handleParamChange(field.key, el.value); }}
                                    disabled={disabled || readonly}
                                    class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                           bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                           focus:outline-none focus:ring-2 focus:ring-libre-green/50
                                           disabled:opacity-50"
                            />
                        {/if}
                    </div>
                {/each}
            </div>
        {/if}

        <!-- ═══ Test Configuration ═══ -->
        {#if !isAutoGenerated || providerCode === 'scheduled_investment'}
            {#if !readonly}
                <div class="flex items-center gap-3">
                    <button
                            type="button"
                            onclick={testConfiguration}
                            disabled={!providerCode || (!identifier && !isAutoGenerated) || testStatus === 'testing' || disabled}
                            class="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border transition-colors
                                   {testStatus === 'testing'
                                       ? 'bg-gray-100 dark:bg-slate-700 text-gray-500 cursor-wait border-gray-200 dark:border-slate-600'
                                       : 'bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-200 border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700'}
                                   disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {#if testStatus === 'testing'}
                            <Loader2 size={14} class="animate-spin"/>
                        {:else}
                            <Play size={14}/>
                        {/if}
                        <span>{$t('assets.provider.testConfig')}</span>
                    </button>
                </div>
            {/if}

            <!-- Test results -->
            {#if testResults.length > 0 || testStatus === 'testing'}
                <div class="flex flex-col gap-1.5 pl-3 border-l-2 {testStatus === 'passed' ? (testResults.some(r => r.status === 'warning') ? 'border-amber-400' : 'border-green-400') : testStatus === 'failed' ? 'border-red-400' : 'border-gray-300 dark:border-slate-600'}">
                    {#each testResults as result}
                        <Tooltip html={buildTooltipHtml(result)} position="top">
                            <div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm">
                                {#if result.status === 'warning'}
                                    <AlertTriangle size={14} class="text-amber-500 shrink-0 self-center"/>
                                {:else if result.success}
                                    <CheckCircle2 size={14} class="text-green-500 shrink-0 self-center"/>
                                {:else}
                                    <AlertCircle size={14} class="text-red-500 shrink-0 self-center"/>
                                {/if}
                                <span class="text-gray-600 dark:text-gray-300">{result.label}:</span>
                                <span class="{result.status === 'warning' ? 'text-amber-600 dark:text-amber-400' : result.success ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
                                    {result.summary ?? result.detail ?? '—'}
                                </span>
                                <span class="text-xs text-gray-400 shrink-0">
                                    ({(result.execution_time_ms / 1000).toFixed(2)}s)
                                </span>
                                {#if result.status === 'error' && result.detail}
                                    <button
                                        type="button"
                                        class="ml-auto shrink-0 p-0.5 text-gray-400 hover:text-blue-500 transition-colors"
                                        title="Copy error detail"
                                        onclick={async (e) => {
                                            e.stopPropagation();
                                            try {
                                                await navigator.clipboard.writeText(result.detail ?? '');
                                                toasts.info('Copied to clipboard');
                                            } catch { /* clipboard not available */ }
                                        }}
                                    >
                                        <ClipboardCopy size={13}/>
                                    </button>
                                {/if}
                            </div>
                        </Tooltip>
                    {/each}
                    {#if testStatus === 'testing'}
                        <div class="flex items-center gap-2 text-sm text-gray-500">
                            <Loader2 size={14} class="animate-spin"/>
                            <span>{$t('assets.provider.testing')}</span>
                        </div>
                    {/if}
                    {#if testResults.length > 0 && testStatus !== 'testing'}
                        <div class="text-xs text-gray-400 dark:text-gray-500 pt-1">
                            {$t('assets.probe.totalTime')}: {(totalExecutionMs / 1000).toFixed(2)}s
                        </div>
                    {/if}
                </div>
            {:else if testStatus === 'not_tested' && providerCode && identifier}
                <div class="flex items-center gap-2 text-xs text-gray-400">
                    <Circle size={12}/>
                    <span>{$t('assets.probe.notTested')}</span>
                </div>
            {/if}
        {/if}

        <!-- ═══ URLs ═══ -->
        <div class="space-y-3">
            <!-- Provider URL (hidden for AUTO_GENERATED) -->
            {#if !isAutoGenerated}
                <div>
                    <label for="provider-url-readonly" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                        {$t('assets.provider.providerUrl')}
                    </label>
                    <div class="flex gap-1.5">
                        <input
                                id="provider-url-readonly"
                                type="text"
                                value={providerUrl ?? ''}
                                disabled
                                class="flex-1 px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                       bg-gray-50 dark:bg-slate-900 text-gray-500 dark:text-gray-400
                                       cursor-not-allowed"
                        />
                        {#if providerUrl}
                            <a href={providerUrl} target="_blank" rel="noopener noreferrer"
                               class="shrink-0 flex items-center px-2 py-2 text-gray-400 hover:text-libre-green transition-colors">
                                <ExternalLink size={14}/>
                            </a>
                        {/if}
                    </div>
                </div>
            {/if}

        </div>

    {/if}
</div>

