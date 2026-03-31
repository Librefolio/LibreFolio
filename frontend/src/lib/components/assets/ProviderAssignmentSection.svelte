<!--
  ProviderAssignmentSection — Reusable provider config + test + URLs.

  Features:
  - Provider select, identifier, identifier type, dynamic params
  - Test Configuration button → POST /assets/provider/probe
  - User URL (editable) + Provider URL (readonly) with links
  - "No Provider" checkbox
  - Results inline with execution_time_ms
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {SimpleSelect} from '$lib/components/ui/select';
    import type {SelectOption} from '$lib/components/ui/select';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import {
        AlertCircle,
        CheckCircle2,
        Circle,
        ExternalLink,
        Loader2,
        Play,
    } from 'lucide-svelte';
    import {IDENTIFIER_TYPES} from '$lib/utils/assetTypes';

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
    }

    interface ProviderInfo {
        code: string;
        name: string;
        supports_search: boolean;
        params_schema: ParamField[];
        icon_url?: string | null;
    }

    type TestStatus = 'not_tested' | 'testing' | 'passed' | 'failed';

    interface TestResult {
        success: boolean;
        label: string;
        detail?: string;
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
        userUrl?: string;
        providerUrl?: string | null;
        noProvider?: boolean;
        disabled?: boolean;
        readonly?: boolean;
        onchange?: (data: {
            providerCode: string;
            identifier: string;
            identifierType: string;
            providerParams: Record<string, any> | null;
            userUrl: string;
            noProvider: boolean;
            testStatus: TestStatus;
        }) => void;
    }

    let {
        providerCode = $bindable(''),
        identifier = $bindable(''),
        identifierType = $bindable('TICKER'),
        providerParams = $bindable(null),
        userUrl = $bindable(''),
        providerUrl = $bindable(null),
        noProvider = $bindable(false),
        disabled = false,
        readonly = false,
        onchange,
    }: Props = $props();

    // =========================================================================
    // Constants — IDENTIFIER_TYPES imported from $lib/utils/assetTypes
    // =========================================================================


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

    /** Provider options for SimpleSelect (excluding mockprov) */
    let providerOptions = $derived<SelectOption[]>([
        {value: '', label: '—'},
        ...providers
            .filter(p => p.code !== 'mockprov')
            .map(p => ({
                value: p.code,
                label: p.name,
                icon: p.icon_url ?? undefined,
            })),
    ]);

    /** Identifier type options for SimpleSelect */
    let idTypeOptions = $derived<SelectOption[]>(
        IDENTIFIER_TYPES.map(t => ({value: t, label: t}))
    );

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
        const computedParams = paramsSchema.length > 0 ? {...paramsValues} : null;
        onchange?.({
            providerCode,
            identifier,
            identifierType,
            providerParams: computedParams,
            userUrl,
            noProvider,
            testStatus,
        });
    }

    function handleProviderChange(code: string) {
        providerCode = code;
        paramsValues = {};
        testStatus = 'not_tested';
        testResults = [];
        emitChange();
    }

    function handleParamChange(key: string, value: any) {
        paramsValues = {...paramsValues, [key]: value};
        providerParams = {...paramsValues};
        emitChange();
    }

    function handleNoProviderToggle() {
        noProvider = !noProvider;
        if (noProvider) {
            testStatus = 'not_tested';
            testResults = [];
        }
        emitChange();
    }

    // =========================================================================
    // Test Configuration
    // =========================================================================

    async function testConfiguration() {
        if (!providerCode || !identifier) return;
        testStatus = 'testing';
        testResults = [];
        totalExecutionMs = 0;

        try {
            const computedParams = paramsSchema.length > 0 ? {...paramsValues} : null;
            const response = await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post({
                provider_code: providerCode,
                identifier,
                identifier_type: identifierType as any,
                provider_params: computedParams,
                operations: ['current_price', 'history'],
            }) as any;

            const items: TestResult[] = [];

            // Current price
            if (response.current_price) {
                const cp = response.current_price;
                const detail = cp.success
                    ? `${cp.value} ${cp.currency ?? ''}${cp.as_of_date ? ` (${cp.as_of_date})` : ''}`
                    : cp.error;
                items.push({
                    success: cp.success,
                    label: $t('assets.probe.currentPrice'),
                    detail,
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
                    label: $t('assets.probe.history'),
                    detail,
                    execution_time_ms: h.execution_time_ms,
                    samplePrices: h.success && h.sample_prices ? h.sample_prices : undefined,
                });
            }

            testResults = items;
            totalExecutionMs = response.total_execution_time_ms ?? 0;
            testStatus = items.every(r => r.success) ? 'passed' : 'failed';

            // Update providerUrl from probe response
            if (response.provider_url) {
                providerUrl = response.provider_url;
            }
        } catch (e: any) {
            testResults = [{
                success: false,
                label: 'Error',
                detail: e?.message || 'Test failed',
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
            html += `<td style="${tdRight}">${result.priceValue} ${result.priceCurrency ?? ''}</td></tr>`;
            html += '</table>';
            return html;
        }

        // History tooltip — multi-row table with sample prices
        if (result.samplePrices && result.samplePrices.length > 0) {
            let html = '<table style="font-size:12px;border-collapse:collapse;">';
            html += `<tr><th style="${thStyle}">📅 ${$t('common.date')}</th><th style="${thStyle}">💰 Close</th></tr>`;
            for (const p of result.samplePrices) {
                html += `<tr><td style="${tdStyle}">${p.date}</td><td style="${tdRight}">${p.close}</td></tr>`;
            }
            html += '</table>';
            return html;
        }

        return result.detail ?? '—';
    }
</script>

<div class="space-y-3">

    {#if !noProvider}
        <!-- Provider select -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
                <span class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    {$t('assets.provider.selectProvider')}
                </span>
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

            <!-- Identifier Type -->
            <div>
                <span class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    {$t('assets.provider.identifierType')}
                </span>
                <SimpleSelect
                        bind:value={identifierType}
                        options={idTypeOptions}
                        disabled={disabled || readonly}
                        dropdownPosition="auto"
                        onchange={() => emitChange()}
                />
            </div>
        </div>

        <!-- Identifier -->
        <div>
            <label for="provider-identifier" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {$t('assets.provider.identifier')}
            </label>
            <input
                    id="provider-identifier"
                    type="text"
                    bind:value={identifier}
                    oninput={() => { testStatus = 'not_tested'; emitChange(); }}
                    disabled={disabled || readonly}
                    placeholder="AAPL, IE00B4L5Y983, https://..."
                    class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                           bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                           placeholder-gray-400 dark:placeholder-gray-500
                           focus:outline-none focus:ring-2 focus:ring-libre-green/50 focus:border-libre-green
                           disabled:opacity-50"
            />
        </div>

        <!-- Dynamic params from params_schema -->
        {#if paramsSchema.length > 0}
            <div class="space-y-2 pl-3 border-l-2 border-gray-200 dark:border-slate-600">
                {#each paramsSchema as field, idx}
                    <div>
                        <label for="param-{field.key}" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                            {field.description || field.key}
                            {#if field.required}<span class="text-red-500">*</span>{/if}
                        </label>
                        {#if field.type === 'select' && field.options}
                            <select
                                    id="param-{field.key}"
                                    value={paramsValues[field.key] ?? field.default ?? ''}
                                    onchange={(e) => handleParamChange(field.key, (e.target as HTMLSelectElement).value)}
                                    disabled={disabled || readonly}
                                    class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                           bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                           focus:outline-none focus:ring-2 focus:ring-libre-green/50
                                           disabled:opacity-50"
                            >
                                {#each field.options as opt}
                                    <option value={opt}>{opt}</option>
                                {/each}
                            </select>
                        {:else if field.type === 'number'}
                            <input
                                    type="number"
                                    value={paramsValues[field.key] ?? field.default ?? ''}
                                    oninput={(e) => handleParamChange(field.key, Number((e.target as HTMLInputElement).value))}
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
                                    oninput={(e) => handleParamChange(field.key, (e.target as HTMLInputElement).value)}
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

        <!-- User URL + Provider URL -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
                <label for="provider-user-url" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    {$t('assets.provider.userUrl')}
                </label>
                <div class="flex gap-1.5">
                    <input
                            id="provider-user-url"
                            type="text"
                            bind:value={userUrl}
                            oninput={() => emitChange()}
                            disabled={disabled || readonly}
                            placeholder="https://..."
                            class="flex-1 px-3 py-2 text-sm border border-gray-200 dark:border-slate-600 rounded-lg
                                   bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100
                                   placeholder-gray-400 dark:placeholder-gray-500
                                   focus:outline-none focus:ring-2 focus:ring-libre-green/50
                                   disabled:opacity-50"
                    />
                    {#if userUrl}
                        <a href={userUrl} target="_blank" rel="noopener noreferrer"
                           class="shrink-0 flex items-center px-2 py-2 text-gray-400 hover:text-libre-green transition-colors">
                            <ExternalLink size={14}/>
                        </a>
                    {/if}
                </div>
            </div>
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
        </div>

        <!-- Test Configuration button -->
        {#if !readonly}
            <div class="flex items-center gap-3">
                <button
                        type="button"
                        onclick={testConfiguration}
                        disabled={!providerCode || !identifier || testStatus === 'testing' || disabled}
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
            <div class="space-y-1.5 pl-3 border-l-2 {testStatus === 'passed' ? 'border-green-400' : testStatus === 'failed' ? 'border-red-400' : 'border-gray-300 dark:border-slate-600'}">
                {#each testResults as result}
                    <Tooltip html={buildTooltipHtml(result)} position="top">
                        <div class="flex items-center gap-2 text-sm">
                            {#if result.success}
                                <CheckCircle2 size={14} class="text-green-500 shrink-0"/>
                            {:else}
                                <AlertCircle size={14} class="text-red-500 shrink-0"/>
                            {/if}
                            <span class="text-gray-600 dark:text-gray-300">{result.label}:</span>
                            <span class="{result.success ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'} truncate">
                                {result.detail ?? '—'}
                            </span>
                            <span class="text-xs text-gray-400 shrink-0">
                                ({(result.execution_time_ms / 1000).toFixed(2)}s)
                            </span>
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
</div>

