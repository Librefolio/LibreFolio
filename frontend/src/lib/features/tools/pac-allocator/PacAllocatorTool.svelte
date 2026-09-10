<script lang="ts">
    import {onDestroy} from 'svelte';
    import {AlertTriangle, CircleStop, LoaderCircle, Plus, Trash2} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {runTool} from '$lib/features/tools/client';
    import {ToolClientError, assertToolAccount, type ToolBatchMetrics, type ToolInput, type ToolItemMetrics, type ToolOutput} from '$lib/features/tools/contracts';
    import {toolErrorMessage, toolViewError} from '$lib/features/tools/presentation';
    import type {ToolHostPropsV1} from '$lib/features/tools/registry';
    import ToolExecutionMetrics from '$lib/features/tools/components/ToolExecutionMetrics.svelte';

    let {descriptor, accountGeneration}: ToolHostPropsV1<'pac_allocator', '1.0.0'> = $props();

    type PacInput = ToolInput<'pac_allocator', '1.0.0'>;
    type PacOutput = ToolOutput<'pac_allocator', '1.0.0'>;
    type PacInputRow = NonNullable<PacInput['rows']>[number];
    type PacDraftRow = PacInputRow & {
        quote: NonNullable<PacInputRow['quote']>;
        buy_grid: NonNullable<PacInputRow['buy_grid']>;
    };
    type PacMoney = NonNullable<PacInput['cash_balances']>[number];
    type PacRate = NonNullable<PacInput['valuation_rates']>[number];
    type PacDraft = PacInput & {
        operation: 'analyze';
        rows: PacDraftRow[];
        cash_balances: PacMoney[] | null;
        contributions: PacMoney[] | null;
        valuation_rates: PacRate[];
    };
    type ReportingFact = PacOutput['totals']['initial_invested_reporting'];
    type RowRatioFact = PacOutput['rows'][number]['current_weight_percent'] | PacOutput['rows'][number]['deviation_pp'];
    type TotalRatioFact = PacOutput['totals']['max_abs_gap_pp'] | PacOutput['totals']['squared_gap_pp2'];
    type RatioFact = RowRatioFact | TotalRatioFact;

    interface PlatformFailure {
        code: string;
        retryable: boolean;
        issueCount: number;
    }

    let identitySequence = 0;

    function createRow(instrumentKey?: string): PacDraftRow {
        identitySequence += 1;
        return {
            row_key: `local-row-${identitySequence}`,
            instrument_key: instrumentKey ?? `local-instrument-${identitySequence}`,
            name: '',
            initial_quantity: '',
            quote: {
                raw_price: '',
                currency: '',
                quote_base_quantity: 1,
                reference_date: '',
            },
            target_percent: '',
            buy_grid: {
                mode: 'whole',
                quantity_step: '1',
            },
        };
    }

    function createDraft(): PacDraft {
        return {
            operation: 'analyze',
            report_currency: '',
            as_of_date: '',
            rows: [createRow()],
            cash_balances: null,
            contributions: null,
            valuation_rates: [],
        };
    }

    function createMoney(): PacMoney {
        return {currency: '', amount: ''};
    }

    function createRate(): PacRate {
        return {currency: '', rate_to_report: '', reference_date: ''};
    }

    let draft = $state<PacDraft>(createDraft());
    let revision = $state(0);
    let requestRevision = $state<number | null>(null);
    let resultRevision = $state<number | null>(null);
    let ignoredRevision = $state<number | null>(null);
    let requestSequence = 0;
    let busy = $state(false);
    let exactView = $state(true);
    let result = $state.raw<PacOutput | null>(null);
    let clientError = $state.raw<ToolClientError | null>(null);
    let platformFailure = $state.raw<PlatformFailure | null>(null);
    let itemMetrics = $state.raw<ToolItemMetrics | null>(null);
    let batchMetrics = $state.raw<ToolBatchMetrics | null>(null);
    let activeController: AbortController | null = null;

    const resultIsStale = $derived(result !== null && resultRevision !== revision);
    const clientErrorCopy = $derived(clientError ? toolErrorMessage(clientError) : null);

    function markRevised(): void {
        revision += 1;
        ignoredRevision = null;
        clientError = null;
        platformFailure = null;
        if (result === null) {
            itemMetrics = null;
            batchMetrics = null;
        }
    }

    function onDraftInput(): void {
        markRevised();
    }

    function addRow(source?: PacDraftRow): void {
        if (draft.rows.length >= 32) return;
        const row = createRow(source?.instrument_key);
        if (source) {
            row.name = source.name;
            row.quote = {...source.quote};
            row.buy_grid = {...source.buy_grid};
            row.initial_quantity = '0';
        }
        draft.rows.push(row);
        markRevised();
    }

    function removeRow(index: number): void {
        draft.rows.splice(index, 1);
        markRevised();
    }

    function addCashBalance(): void {
        if ((draft.cash_balances?.length ?? 0) >= 4) return;
        if (draft.cash_balances === null) draft.cash_balances = [];
        draft.cash_balances.push(createMoney());
        markRevised();
    }

    function addContribution(): void {
        if ((draft.contributions?.length ?? 0) >= 4) return;
        if (draft.contributions === null) draft.contributions = [];
        draft.contributions.push(createMoney());
        markRevised();
    }

    function removeCashBalance(index: number): void {
        draft.cash_balances?.splice(index, 1);
        markRevised();
    }

    function removeContribution(index: number): void {
        draft.contributions?.splice(index, 1);
        markRevised();
    }

    function markNoCash(): void {
        draft.cash_balances = [];
        markRevised();
    }

    function markNoContributions(): void {
        draft.contributions = [];
        markRevised();
    }

    function markCashNotSupplied(): void {
        draft.cash_balances = null;
        markRevised();
    }

    function markContributionsNotSupplied(): void {
        draft.contributions = null;
        markRevised();
    }

    function addValuationRate(): void {
        if (draft.valuation_rates.length >= 4) return;
        draft.valuation_rates.push(createRate());
        markRevised();
    }

    function removeValuationRate(index: number): void {
        draft.valuation_rates.splice(index, 1);
        markRevised();
    }

    function descriptorIsCurrent(): boolean {
        return descriptor.tool_code === 'pac_allocator' && descriptor.contract_version === '1.0.0' && descriptor.ui.kind === 'custom' && descriptor.ui.component_key === 'pac-allocator' && descriptor.ui.ui_contract_version === 1;
    }

    function requestIsCurrent(sequence: number, draftRevision: number, generation: number): boolean {
        if (sequence !== requestSequence || revision !== draftRevision || generation !== accountGeneration || !descriptorIsCurrent()) return false;
        try {
            assertToolAccount(generation);
            return true;
        } catch {
            return false;
        }
    }

    function reportClientFailure(failure: ToolClientError): void {
        if (failure.code === 'waiting_stopped' || failure.code === 'session_changed') return;
        const copy = toolErrorMessage(failure);
        notify({
            name: 'tool.pac-analyze.failed',
            detail: {kind: failure.kind, code: failure.code, issueCount: failure.issueCount},
            toast: {variant: 'error', message: $t(copy.key, {default: copy.fallback})},
        });
    }

    async function analyze(): Promise<void> {
        if (busy || !descriptorIsCurrent()) return;
        const draftRevision = revision;
        const generation = accountGeneration;
        const sequence = ++requestSequence;
        const controller = new AbortController();
        activeController = controller;
        requestRevision = draftRevision;
        ignoredRevision = null;
        clientError = null;
        platformFailure = null;
        busy = true;

        try {
            const parameters: PacInput = $state.snapshot(draft);
            const reply = await runTool('pac_allocator', '1.0.0', {
                descriptor,
                correlationId: `pac-${sequence}-${draftRevision}`,
                parameters,
                signal: controller.signal,
            });
            if (!requestIsCurrent(sequence, draftRevision, generation)) {
                if (sequence === requestSequence && generation === accountGeneration) ignoredRevision = draftRevision;
                return;
            }
            itemMetrics = reply.metrics;
            batchMetrics = reply.batch.metrics;
            if (reply.status === 'success') {
                result = reply.result;
                resultRevision = draftRevision;
                platformFailure = null;
            } else {
                result = null;
                resultRevision = null;
                platformFailure = {
                    code: reply.error.code,
                    retryable: reply.error.retryable,
                    issueCount: reply.error.issue_count,
                };
                notify({
                    name: 'tool.pac-analyze.platform-failed',
                    detail: {
                        code: reply.error.code,
                        retryable: reply.error.retryable,
                        issueCount: reply.error.issue_count,
                    },
                    toast: {
                        variant: 'error',
                        message: $t('tools.pacAllocator.platformError', {
                            default: 'The backend could not complete this analysis. Your draft was preserved.',
                        }),
                    },
                });
            }
        } catch (caught) {
            if (!requestIsCurrent(sequence, draftRevision, generation)) {
                if (sequence === requestSequence && generation === accountGeneration) ignoredRevision = draftRevision;
                return;
            }
            const failure = toolViewError(caught);
            clientError = failure;
            result = null;
            resultRevision = null;
            itemMetrics = null;
            batchMetrics = null;
            reportClientFailure(failure);
        } finally {
            if (sequence === requestSequence) {
                busy = false;
                activeController = null;
            }
        }
    }

    function stopWaiting(): void {
        activeController?.abort();
    }

    function displayDecimal(value: string, maxFrac = 8): string {
        return exactView ? value : formatDecimalForDisplay(value, {maxFrac});
    }

    function displayReportingFact(fact: ReportingFact): string {
        if (fact.availability === 'unavailable') return `— (${fact.reason_codes.join(', ')})`;
        return `${displayDecimal(fact.value.amount)} ${fact.value.currency}`;
    }

    function displayRatioFact(fact: RatioFact): string {
        if (fact.availability === 'unavailable') return `— (${fact.reason_codes.join(', ')})`;
        return exactView ? `${fact.value.numerator} / ${fact.value.denominator}` : displayDecimal(fact.value.approximation, 6);
    }

    onDestroy(() => {
        requestSequence += 1;
        activeController?.abort();
        activeController = null;
    });
</script>

<form
    class="min-w-0 space-y-6"
    data-testid="pac-allocator-tool"
    data-busy={busy ? 'true' : 'false'}
    data-revision={revision}
    aria-busy={busy}
    onsubmit={(event) => {
        event.preventDefault();
        void analyze();
    }}
    oninput={onDraftInput}
>
    <aside class="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-100" data-testid="pac-pilot-notice">
        {$t('tools.pacAllocator.pilotNotice', {
            default: 'Manual initial-state analysis only. No portfolio data is read, no orders are proposed, and nothing is saved.',
        })}
    </aside>

    <section class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800" data-testid="pac-scenario">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {$t('tools.pacAllocator.scenario', {default: 'Scenario'})}
        </h2>
        <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300">
                <span class="mb-1 block font-medium">{$t('tools.pacAllocator.reportCurrency', {default: 'Reporting currency'})}</span>
                <input
                    type="text"
                    maxlength="8"
                    autocomplete="off"
                    placeholder="EUR"
                    bind:value={draft.report_currency}
                    class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 uppercase text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                    data-testid="pac-report-currency"
                />
            </label>
            <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300">
                <span class="mb-1 block font-medium">{$t('tools.pacAllocator.asOfDate', {default: 'As-of date (optional)'})}</span>
                <input
                    type="text"
                    maxlength="10"
                    autocomplete="off"
                    placeholder="YYYY-MM-DD"
                    bind:value={draft.as_of_date}
                    class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                    data-testid="pac-as-of-date"
                />
            </label>
        </div>
    </section>

    <section class="space-y-4" data-testid="pac-rows">
        <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
                <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {$t('tools.pacAllocator.rows.title', {default: 'Assets and custody contexts'})}
                </h2>
                <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    {$t('tools.pacAllocator.rows.description', {
                        default: 'Each row is one asset in one context. Use “same asset, another context” to preserve instrument identity.',
                    })}
                </p>
            </div>
            <button
                type="button"
                onclick={() => addRow()}
                disabled={draft.rows.length >= 32}
                class="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                data-testid="pac-add-row"
            >
                <Plus size={16} aria-hidden="true" />
                {$t('tools.pacAllocator.rows.addAsset', {default: 'New local asset'})}
            </button>
        </div>

        {#if draft.rows.length === 0}
            <p class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" data-testid="pac-no-rows">
                {$t('tools.pacAllocator.rows.empty', {default: 'Add at least one row. The backend will report missing rows until then.'})}
            </p>
        {/if}

        {#each draft.rows as row, index (row.row_key)}
            <article class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800" data-testid="pac-row" data-row-index={index}>
                <header class="flex flex-wrap items-start justify-between gap-3">
                    <div class="min-w-0">
                        <h3 class="font-semibold text-gray-900 dark:text-gray-100">
                            {$t('tools.pacAllocator.rows.rowNumber', {
                                default: 'Row {number}',
                                values: {number: index + 1},
                            })}
                        </h3>
                        <p class="mt-1 break-all text-xs text-gray-500 dark:text-gray-400">
                            {$t('tools.pacAllocator.rows.identity', {default: 'Local instrument identity'})}: {row.instrument_key}
                        </p>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onclick={() => addRow(row)}
                            disabled={draft.rows.length >= 32}
                            class="rounded-lg border border-gray-300 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
                            data-testid="pac-add-same-instrument"
                        >
                            {$t('tools.pacAllocator.rows.sameAsset', {default: 'Same asset, another context'})}
                        </button>
                        <button
                            type="button"
                            onclick={() => removeRow(index)}
                            class="inline-flex items-center gap-1 rounded-lg border border-red-300 px-3 py-2 text-xs font-medium text-red-700 hover:bg-red-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-950/30"
                            aria-label={$t('common.remove')}
                            data-testid="pac-remove-row"
                        >
                            <Trash2 size={14} aria-hidden="true" />
                            {$t('common.remove')}
                        </button>
                    </div>
                </header>

                <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300">
                        <span class="mb-1 block font-medium">{$t('common.name')}</span>
                        <input
                            type="text"
                            maxlength="128"
                            autocomplete="off"
                            bind:value={row.name}
                            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-row-name"
                        />
                    </label>
                    <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300">
                        <span class="mb-1 block font-medium">{$t('tools.pacAllocator.rows.initialQuantity', {default: 'Initial quantity'})}</span>
                        <input
                            type="text"
                            inputmode="decimal"
                            maxlength="64"
                            autocomplete="off"
                            bind:value={row.initial_quantity}
                            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-initial-quantity"
                        />
                    </label>
                    <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300">
                        <span class="mb-1 block font-medium">{$t('tools.pacAllocator.rows.price', {default: 'Native price'})}</span>
                        <input
                            type="text"
                            inputmode="decimal"
                            maxlength="64"
                            autocomplete="off"
                            bind:value={row.quote.raw_price}
                            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-price"
                        />
                    </label>
                    <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300">
                        <span class="mb-1 block font-medium">{$t('common.currency')}</span>
                        <input
                            type="text"
                            maxlength="8"
                            autocomplete="off"
                            placeholder="EUR"
                            bind:value={row.quote.currency}
                            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 uppercase text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-price-currency"
                        />
                    </label>
                    <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300">
                        <span class="mb-1 block font-medium">{$t('tools.pacAllocator.rows.quoteBasis', {default: 'Quote base quantity'})}</span>
                        <input
                            type="number"
                            step="1"
                            bind:value={row.quote.quote_base_quantity}
                            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-quote-basis"
                        />
                    </label>
                    <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300">
                        <span class="mb-1 block font-medium">{$t('tools.pacAllocator.rows.target', {default: 'Target (%)'})}</span>
                        <input
                            type="text"
                            inputmode="decimal"
                            maxlength="64"
                            autocomplete="off"
                            bind:value={row.target_percent}
                            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-target-percent"
                        />
                    </label>
                    <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300">
                        <span class="mb-1 block font-medium">{$t('tools.pacAllocator.rows.gridMode', {default: 'Purchase grid'})}</span>
                        <select bind:value={row.buy_grid.mode} class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" data-testid="pac-grid-mode">
                            <option value="whole">{$t('tools.pacAllocator.rows.whole', {default: 'Whole quantities'})}</option>
                            <option value="fractional">{$t('tools.pacAllocator.rows.fractional', {default: 'Fractional quantities'})}</option>
                        </select>
                    </label>
                    <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300">
                        <span class="mb-1 block font-medium">{$t('tools.pacAllocator.rows.quantityStep', {default: 'Purchase quantity step'})}</span>
                        <input
                            type="text"
                            inputmode="decimal"
                            maxlength="64"
                            autocomplete="off"
                            bind:value={row.buy_grid.quantity_step}
                            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-quantity-step"
                        />
                    </label>
                    <label class="min-w-0 text-sm text-gray-700 dark:text-gray-300 sm:col-span-2">
                        <span class="mb-1 block font-medium">{$t('tools.pacAllocator.rows.quoteDate', {default: 'Quote date (optional)'})}</span>
                        <input
                            type="text"
                            maxlength="10"
                            autocomplete="off"
                            placeholder="YYYY-MM-DD"
                            bind:value={row.quote.reference_date}
                            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-libre-green focus:outline-none dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-quote-date"
                        />
                    </label>
                </div>
            </article>
        {/each}
    </section>

    <section class="grid grid-cols-1 gap-4 lg:grid-cols-2" data-testid="pac-cash-vectors">
        <article class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800" data-testid="pac-existing-cash">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {$t('tools.pacAllocator.cash.existing', {default: 'Existing cash'})}
            </h2>
            {#if draft.cash_balances === null}
                <p class="mt-3 text-sm text-amber-700 dark:text-amber-300" data-testid="pac-existing-cash-not-supplied">
                    {$t('tools.pacAllocator.cash.notSupplied', {default: 'Not supplied'})}
                </p>
            {:else if draft.cash_balances.length === 0}
                <p class="mt-3 text-sm text-gray-600 dark:text-gray-400" data-testid="pac-existing-cash-none">
                    {$t('tools.pacAllocator.cash.noneExisting', {default: 'Explicitly no existing cash'})}
                </p>
            {/if}
            <div class="mt-3 space-y-3">
                {#each draft.cash_balances ?? [] as money, index}
                    <div class="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto] gap-2" data-testid="pac-existing-cash-row">
                        <input
                            type="text"
                            maxlength="8"
                            autocomplete="off"
                            placeholder="EUR"
                            aria-label={$t('common.currency')}
                            bind:value={money.currency}
                            class="min-w-0 rounded-lg border border-gray-300 bg-white px-3 py-2 uppercase text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-cash-currency"
                        />
                        <input
                            type="text"
                            inputmode="decimal"
                            maxlength="64"
                            autocomplete="off"
                            aria-label={$t('tools.pacAllocator.cash.amount', {default: 'Amount'})}
                            bind:value={money.amount}
                            class="min-w-0 rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-cash-amount"
                        />
                        <button type="button" onclick={() => removeCashBalance(index)} aria-label={$t('common.remove')} class="rounded-lg border border-red-300 p-2 text-red-700 dark:border-red-800 dark:text-red-300" data-testid="pac-remove-cash">
                            <Trash2 size={16} aria-hidden="true" />
                        </button>
                    </div>
                {/each}
            </div>
            <div class="mt-4 flex flex-wrap gap-2">
                <button
                    type="button"
                    onclick={addCashBalance}
                    disabled={(draft.cash_balances?.length ?? 0) >= 4}
                    class="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600"
                    data-testid="pac-add-cash"
                >
                    <Plus size={14} aria-hidden="true" />
                    {$t('tools.pacAllocator.cash.addCurrency', {default: 'Add currency'})}
                </button>
                <button type="button" onclick={markNoCash} class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600" data-testid="pac-mark-no-cash">
                    {$t('tools.pacAllocator.cash.markNoneExisting', {default: 'No existing cash'})}
                </button>
                {#if draft.cash_balances !== null}
                    <button type="button" onclick={markCashNotSupplied} class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600" data-testid="pac-unset-cash">
                        {$t('tools.pacAllocator.cash.markNotSupplied', {default: 'Mark as not supplied'})}
                    </button>
                {/if}
            </div>
        </article>

        <article class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800" data-testid="pac-contributions">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {$t('tools.pacAllocator.cash.contributions', {default: 'New contributions'})}
            </h2>
            {#if draft.contributions === null}
                <p class="mt-3 text-sm text-amber-700 dark:text-amber-300" data-testid="pac-contributions-not-supplied">
                    {$t('tools.pacAllocator.cash.notSupplied', {default: 'Not supplied'})}
                </p>
            {:else if draft.contributions.length === 0}
                <p class="mt-3 text-sm text-gray-600 dark:text-gray-400" data-testid="pac-contributions-none">
                    {$t('tools.pacAllocator.cash.noneContributions', {default: 'Explicitly no new contributions'})}
                </p>
            {/if}
            <div class="mt-3 space-y-3">
                {#each draft.contributions ?? [] as money, index}
                    <div class="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto] gap-2" data-testid="pac-contribution-row">
                        <input
                            type="text"
                            maxlength="8"
                            autocomplete="off"
                            placeholder="EUR"
                            aria-label={$t('common.currency')}
                            bind:value={money.currency}
                            class="min-w-0 rounded-lg border border-gray-300 bg-white px-3 py-2 uppercase text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-contribution-currency"
                        />
                        <input
                            type="text"
                            inputmode="decimal"
                            maxlength="64"
                            autocomplete="off"
                            aria-label={$t('tools.pacAllocator.cash.amount', {default: 'Amount'})}
                            bind:value={money.amount}
                            class="min-w-0 rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                            data-testid="pac-contribution-amount"
                        />
                        <button type="button" onclick={() => removeContribution(index)} aria-label={$t('common.remove')} class="rounded-lg border border-red-300 p-2 text-red-700 dark:border-red-800 dark:text-red-300" data-testid="pac-remove-contribution">
                            <Trash2 size={16} aria-hidden="true" />
                        </button>
                    </div>
                {/each}
            </div>
            <div class="mt-4 flex flex-wrap gap-2">
                <button
                    type="button"
                    onclick={addContribution}
                    disabled={(draft.contributions?.length ?? 0) >= 4}
                    class="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600"
                    data-testid="pac-add-contribution"
                >
                    <Plus size={14} aria-hidden="true" />
                    {$t('tools.pacAllocator.cash.addCurrency', {default: 'Add currency'})}
                </button>
                <button type="button" onclick={markNoContributions} class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600" data-testid="pac-mark-no-contributions">
                    {$t('tools.pacAllocator.cash.markNoneContributions', {default: 'No new contributions'})}
                </button>
                {#if draft.contributions !== null}
                    <button type="button" onclick={markContributionsNotSupplied} class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600" data-testid="pac-unset-contributions">
                        {$t('tools.pacAllocator.cash.markNotSupplied', {default: 'Mark as not supplied'})}
                    </button>
                {/if}
            </div>
        </article>
    </section>

    <section class="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800" data-testid="pac-valuation-rates">
        <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
                <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {$t('tools.pacAllocator.rates.title', {default: 'Valuation exchange rates'})}
                </h2>
                <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    {$t('tools.pacAllocator.rates.description', {
                        default: 'Reporting value of one native currency unit. These rates do not convert or move cash.',
                    })}
                </p>
            </div>
            <button type="button" onclick={addValuationRate} disabled={draft.valuation_rates.length >= 4} class="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600" data-testid="pac-add-rate">
                <Plus size={14} aria-hidden="true" />
                {$t('tools.pacAllocator.rates.add', {default: 'Add rate'})}
            </button>
        </div>
        <div class="mt-4 space-y-3">
            {#each draft.valuation_rates as rate, index}
                <div class="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_minmax(0,2fr)_auto]" data-testid="pac-rate-row">
                    <input
                        type="text"
                        maxlength="8"
                        autocomplete="off"
                        placeholder="USD"
                        aria-label={$t('common.currency')}
                        bind:value={rate.currency}
                        class="min-w-0 rounded-lg border border-gray-300 bg-white px-3 py-2 uppercase text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                        data-testid="pac-rate-currency"
                    />
                    <input
                        type="text"
                        inputmode="decimal"
                        maxlength="64"
                        autocomplete="off"
                        aria-label={$t('tools.pacAllocator.rates.value', {default: 'Rate to reporting currency'})}
                        bind:value={rate.rate_to_report}
                        class="min-w-0 rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                        data-testid="pac-rate-value"
                    />
                    <input
                        type="text"
                        maxlength="10"
                        autocomplete="off"
                        placeholder="YYYY-MM-DD"
                        aria-label={$t('tools.pacAllocator.rates.date', {default: 'Rate date (optional)'})}
                        bind:value={rate.reference_date}
                        class="min-w-0 rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                        data-testid="pac-rate-date"
                    />
                    <button type="button" onclick={() => removeValuationRate(index)} aria-label={$t('common.remove')} class="rounded-lg border border-red-300 p-2 text-red-700 dark:border-red-800 dark:text-red-300" data-testid="pac-remove-rate">
                        <Trash2 size={16} aria-hidden="true" />
                    </button>
                </div>
            {/each}
        </div>
    </section>

    <section class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/50" data-testid="pac-actions">
        <div class="text-sm text-gray-600 dark:text-gray-400">
            <p>
                {$t('tools.pacAllocator.revision', {default: 'Draft revision'})}: <span class="font-mono" data-testid="pac-draft-revision">{revision}</span>
            </p>
            <p>{$t('tools.pacAllocator.noOrders', {default: 'Orders, feasibility, and optimization are not included in this pilot.'})}</p>
        </div>
        <div class="flex flex-wrap gap-2">
            {#if busy}
                <button type="button" onclick={stopWaiting} class="inline-flex items-center gap-2 rounded-lg border border-amber-400 px-4 py-2 text-sm font-medium text-amber-800 dark:text-amber-200" data-testid="pac-stop-waiting">
                    <CircleStop size={16} aria-hidden="true" />
                    {$t('tools.pacAllocator.stopWaiting', {default: 'Stop waiting'})}
                </button>
            {/if}
            <button type="submit" disabled={busy} class="inline-flex items-center gap-2 rounded-lg bg-libre-green px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50" data-testid="pac-analyze">
                {#if busy}
                    <LoaderCircle size={16} class="animate-spin motion-reduce:animate-none" aria-hidden="true" />
                    {$t('tools.pacAllocator.analyzing', {default: 'Analyzing revision {revision}…', values: {revision: requestRevision ?? revision}})}
                {:else}
                    {$t('tools.pacAllocator.analyze', {default: 'Check initial state'})}
                {/if}
            </button>
        </div>
    </section>

    {#if busy && requestRevision !== revision}
        <p class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" role="status" data-testid="pac-request-stale">
            {$t('tools.pacAllocator.stale.pending', {
                default: 'Request revision {requestRevision} is still running, but the draft is now revision {draftRevision}. Its response will be ignored.',
                values: {requestRevision, draftRevision: revision},
            })}
        </p>
    {/if}

    {#if ignoredRevision !== null}
        <p class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" role="status" data-testid="pac-response-ignored">
            {$t('tools.pacAllocator.stale.ignored', {
                default: 'Response for revision {revision} was ignored because the draft or account changed.',
                values: {revision: ignoredRevision},
            })}
        </p>
    {/if}

    {#if clientError && clientErrorCopy}
        <section class="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="pac-client-error" data-error-code={clientError.code}>
            <h2 class="font-semibold">{$t('common.error')}</h2>
            <p class="mt-2 text-sm">{$t(clientErrorCopy.key, {default: clientErrorCopy.fallback})}</p>
            <p class="mt-2 text-xs">{$t('tools.pacAllocator.draftPreserved', {default: 'Your draft was preserved.'})}</p>
        </section>
    {/if}

    {#if platformFailure}
        <section class="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="pac-platform-error" data-error-code={platformFailure.code}>
            <h2 class="font-semibold">{$t('tools.pacAllocator.platformErrorTitle', {default: 'Analysis not completed'})}</h2>
            <p class="mt-2 text-sm">{$t('tools.pacAllocator.platformError', {default: 'The backend could not complete this analysis. Your draft was preserved.'})}</p>
            <p class="mt-2 break-all font-mono text-xs">{platformFailure.code}</p>
        </section>
    {/if}

    {#if result}
        <section class="space-y-5 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800" data-testid="pac-result" data-state={result.availability} data-stale={resultIsStale ? 'true' : 'false'} data-result-revision={resultRevision}>
            <header class="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {#if result.availability === 'ready'}
                            {$t('tools.pacAllocator.state.ready', {default: 'Ready · initial state is evaluable'})}
                        {:else if result.availability === 'needs_input'}
                            {$t('tools.pacAllocator.state.needsInput', {default: 'Needs input'})}
                        {:else if result.availability === 'invalid'}
                            {$t('tools.pacAllocator.state.invalid', {default: 'Invalid scenario'})}
                        {:else}
                            {$t('tools.pacAllocator.state.unsupported', {default: 'Outside the P1 domain'})}
                        {/if}
                    </h2>
                    <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
                        {$t('tools.pacAllocator.resultMeaning', {
                            default: 'This is an initial-state analysis. It does not certify trade feasibility, target attainment, or optimality.',
                        })}
                    </p>
                    {#if resultIsStale}
                        <p class="mt-2 text-sm font-medium text-amber-700 dark:text-amber-300" data-testid="pac-result-stale">
                            {$t('tools.pacAllocator.stale.result', {default: 'This result belongs to an older draft revision.'})}
                        </p>
                    {/if}
                </div>
                <div class="inline-flex rounded-lg border border-gray-300 p-1 dark:border-gray-600" data-testid="pac-display-mode">
                    <button type="button" onclick={() => (exactView = true)} aria-pressed={exactView} class="rounded px-3 py-1.5 text-sm font-medium aria-pressed:bg-libre-green aria-pressed:text-white" data-testid="pac-view-exact">
                        {$t('tools.pacAllocator.exactView', {default: 'Exact'})}
                    </button>
                    <button type="button" onclick={() => (exactView = false)} aria-pressed={!exactView} class="rounded px-3 py-1.5 text-sm font-medium aria-pressed:bg-libre-green aria-pressed:text-white" data-testid="pac-view-formatted">
                        {$t('tools.pacAllocator.formattedView', {default: 'Formatted'})}
                    </button>
                </div>
            </header>

            <dl class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4" data-testid="pac-totals">
                <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
                    <dt class="text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.totals.invested', {default: 'Initial invested value'})}</dt>
                    <dd class="mt-1 break-words font-mono text-sm text-gray-900 dark:text-gray-100" data-testid="pac-total-invested">
                        {displayReportingFact(result.totals.initial_invested_reporting)}
                    </dd>
                </div>
                <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
                    <dt class="text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.totals.existingCash', {default: 'Existing cash'})}</dt>
                    <dd class="mt-1 break-words font-mono text-sm text-gray-900 dark:text-gray-100" data-testid="pac-total-existing-cash">
                        {displayReportingFact(result.totals.existing_cash_reporting)}
                    </dd>
                </div>
                <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
                    <dt class="text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.totals.contributions', {default: 'New contributions'})}</dt>
                    <dd class="mt-1 break-words font-mono text-sm text-gray-900 dark:text-gray-100" data-testid="pac-total-contributions">
                        {displayReportingFact(result.totals.contributions_reporting)}
                    </dd>
                </div>
                <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
                    <dt class="text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.totals.combinedCash', {default: 'Cash plus contributions'})}</dt>
                    <dd class="mt-1 break-words font-mono text-sm text-gray-900 dark:text-gray-100" data-testid="pac-total-combined-cash">
                        {displayReportingFact(result.totals.cash_plus_contributions_reporting)}
                    </dd>
                </div>
            </dl>

            <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
                <table class="min-w-full divide-y divide-gray-200 text-left text-sm dark:divide-gray-700" data-testid="pac-result-rows">
                    <thead class="bg-gray-50 text-xs text-gray-600 dark:bg-gray-900/50 dark:text-gray-400">
                        <tr>
                            <th class="px-3 py-2 font-medium">{$t('tools.pacAllocator.result.row', {default: 'Row'})}</th>
                            <th class="px-3 py-2 font-medium">{$t('tools.pacAllocator.rows.initialQuantity', {default: 'Initial quantity'})}</th>
                            <th class="px-3 py-2 font-medium">{$t('tools.pacAllocator.result.value', {default: 'Reporting value'})}</th>
                            <th class="px-3 py-2 font-medium">{$t('tools.pacAllocator.result.weight', {default: 'Current weight'})}</th>
                            <th class="px-3 py-2 font-medium">{$t('tools.pacAllocator.result.target', {default: 'Target'})}</th>
                            <th class="px-3 py-2 font-medium">{$t('tools.pacAllocator.result.gap', {default: 'Gap (pp)'})}</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200 text-gray-800 dark:divide-gray-700 dark:text-gray-200">
                        {#each result.rows as row}
                            <tr data-testid="pac-result-row">
                                <td class="max-w-48 break-words px-3 py-2">{row.name || row.row_key}</td>
                                <td class="whitespace-nowrap px-3 py-2 font-mono">
                                    {row.quantity.availability === 'available' ? displayDecimal(row.quantity.value) : '—'}
                                </td>
                                <td class="whitespace-nowrap px-3 py-2 font-mono">
                                    {row.initial_value_reporting.availability === 'available' ? `${displayDecimal(row.initial_value_reporting.value.amount)} ${row.initial_value_reporting.value.currency}` : '—'}
                                </td>
                                <td class="whitespace-nowrap px-3 py-2 font-mono">
                                    {displayRatioFact(row.current_weight_percent)}
                                </td>
                                <td class="whitespace-nowrap px-3 py-2 font-mono">
                                    {row.target_percent.availability === 'available' ? `${displayDecimal(row.target_percent.value)}%` : '—'}
                                </td>
                                <td class="whitespace-nowrap px-3 py-2 font-mono">
                                    {displayRatioFact(row.deviation_pp)}
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>

            <dl class="grid grid-cols-1 gap-3 sm:grid-cols-2" data-testid="pac-distance-summary">
                <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
                    <dt class="text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.totals.maxGap', {default: 'Maximum absolute gap (pp)'})}</dt>
                    <dd class="mt-1 break-words font-mono text-sm" data-testid="pac-max-gap">{displayRatioFact(result.totals.max_abs_gap_pp)}</dd>
                </div>
                <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
                    <dt class="text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.totals.squaredGap', {default: 'Squared gap (pp²)'})}</dt>
                    <dd class="mt-1 break-words font-mono text-sm" data-testid="pac-squared-gap">{displayRatioFact(result.totals.squared_gap_pp2)}</dd>
                </div>
            </dl>

            <section data-testid="pac-cash-pools">
                <h3 class="font-semibold text-gray-900 dark:text-gray-100">
                    {$t('tools.pacAllocator.cashPools', {default: 'Native cash pools'})}
                </h3>
                {#if result.cash_pools.availability === 'available'}
                    <ul class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                        {#each result.cash_pools.value as pool}
                            <li class="rounded-lg bg-gray-50 p-3 text-sm dark:bg-gray-900/50" data-testid="pac-cash-pool">
                                <p class="font-semibold">{pool.currency}</p>
                                <p class="mt-1 font-mono">
                                    {$t('tools.pacAllocator.totals.existingCash', {default: 'Existing cash'})}: {displayDecimal(pool.existing_amount)}
                                </p>
                                <p class="font-mono">
                                    {$t('tools.pacAllocator.totals.contributions', {default: 'New contributions'})}: {displayDecimal(pool.contribution_amount)}
                                </p>
                                <p class="font-mono">
                                    {$t('tools.pacAllocator.totals.combinedCash', {default: 'Cash plus contributions'})}: {displayDecimal(pool.combined_amount)}
                                </p>
                            </li>
                        {/each}
                    </ul>
                {:else}
                    <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
                        — ({result.cash_pools.reason_codes.join(', ')})
                    </p>
                {/if}
            </section>

            {#if result.issues.length > 0}
                <section data-testid="pac-issues">
                    <h3 class="font-semibold text-gray-900 dark:text-gray-100">
                        {$t('tools.pacAllocator.issues', {default: 'Backend findings'})}
                    </h3>
                    <ul class="mt-3 space-y-2">
                        {#each result.issues as issue}
                            <li class="rounded-lg border border-gray-200 p-3 text-sm dark:border-gray-700" data-testid="pac-issue" data-kind={issue.kind}>
                                <p class="font-medium"><span class="font-mono">{issue.code}</span> · {issue.kind}</p>
                                <p class="mt-1 break-words font-mono text-xs text-gray-600 dark:text-gray-400">{issue.path.join(' · ')}</p>
                            </li>
                        {/each}
                    </ul>
                </section>
            {/if}

            {#if result.availability === 'ready'}
                <details class="rounded-lg border border-gray-200 p-3 dark:border-gray-700" data-testid="pac-normalized-details">
                    <summary class="cursor-pointer font-medium">{$t('tools.pacAllocator.normalizedInput', {default: 'Normalized input and units'})}</summary>
                    <pre class="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs">{JSON.stringify(result.normalized, null, 2)}</pre>
                </details>
            {/if}
        </section>
    {/if}

    {#if itemMetrics}
        <ToolExecutionMetrics item={itemMetrics} batch={batchMetrics} />
    {/if}
</form>
