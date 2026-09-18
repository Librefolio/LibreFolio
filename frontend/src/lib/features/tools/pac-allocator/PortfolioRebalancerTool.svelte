<script lang="ts">
    import {onDestroy} from 'svelte';
    import {CircleStop, LoaderCircle} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {userSettings} from '$lib/stores/app/settings';
    import {runTool} from '$lib/features/tools/client';
    import {ToolClientError, assertToolAccount, type ToolBatchMetrics, type ToolItemMetrics, type ToolOutput} from '$lib/features/tools/contracts';
    import {toolErrorMessage, toolViewError} from '$lib/features/tools/presentation';
    import type {ToolHostPropsV1} from '$lib/features/tools/registry';
    import ToolExecutionMetrics from '$lib/features/tools/components/ToolExecutionMetrics.svelte';
    import AllocationFundingSummary from './AllocationFundingSummary.svelte';
    import AllocationFxSection from './AllocationFxSection.svelte';
    import AllocationTargetEditor from './AllocationTargetEditor.svelte';
    import OwnedAssetGallery from './OwnedAssetGallery.svelte';
    import PacMoneySection from './PacMoneySection.svelte';
    import RebalanceHoldingEditor from './RebalanceHoldingEditor.svelte';
    import RebalancerResultPanel from './RebalancerResultPanel.svelte';
    import {fetchPacAllocationSource, type PacAllocationSource} from './allocationSource';
    import {cloneDraft, closePercentDistribution, createManualRebalanceHolding, createRebalanceHoldings, syncTargets} from './draftFactories';
    import type {AllocationTargetDraft, PacAssetChoice, PacCashSourceState, PacContributionInput, PacContributionMode, PacMoneyInput, PacRateInput, RebalanceEditorHolding, RebalancerInput} from './editorTypes';

    let {descriptor, accountGeneration}: ToolHostPropsV1<'portfolio_rebalancer', '1.0.0'> = $props();
    type RebalancerOutput = ToolOutput<'portfolio_rebalancer', '1.0.0'>;

    interface PlatformFailure {
        code: string;
        retryable: boolean;
    }

    interface PendingRemoval {
        sourceAssetId: number | null;
        holdingIndex: number | null;
        items: string[];
    }

    const MAX_HOLDINGS = 32;
    const MAX_CURRENCIES = 4;
    const MAX_CONTRIBUTIONS = 32;

    function todayIso(): string {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    }

    function createMoney(currency = ''): PacMoneyInput {
        return {currency, amount: ''};
    }

    function createContribution(currency = ''): PacContributionInput {
        return {currency, amount: '', monetary_step: '0.01'};
    }

    function sameValue(left: unknown, right: unknown): boolean {
        return JSON.stringify(left) === JSON.stringify(right);
    }

    function isModified(holding: RebalanceEditorHolding): boolean {
        return holding.importedValue !== null && !sameValue(holding.value, holding.importedValue);
    }

    let reportCurrency = $state(userSettings.get()?.base_currency ?? 'EUR');
    let asOfDate = $state(todayIso());
    let holdings = $state<RebalanceEditorHolding[]>([]);
    let targets = $state<AllocationTargetDraft[]>([]);
    let cashMode = $state<PacCashSourceState['mode']>('broker_copy');
    let selectedCashBrokerIds = $state<number[]>([]);
    let sourceCash = $state<PacMoneyInput[]>([]);
    let manualCash = $state<PacMoneyInput[]>([]);
    let contributionMode = $state<PacContributionMode>('none');
    let contributions = $state<PacContributionInput[]>([]);
    let valuationRates = $state<PacRateInput[]>([]);

    let allocationSource = $state.raw<PacAllocationSource | null>(null);
    let sourceGeneration = $state<number | null>(null);
    let sourceCashSelectionKey = $state<string | null>(null);
    let sourceLoading = $state(false);
    let sourceFailure = $state.raw<ToolClientError | null>(null);
    let sourceSequence = 0;
    let sourceRefresh = $state(0);
    let sourceController: AbortController | null = null;

    let revision = $state(0);
    let resultRevision = $state<number | null>(null);
    let requestSequence = 0;
    let busy = $state(false);
    let result = $state.raw<RebalancerOutput | null>(null);
    let clientError = $state.raw<ToolClientError | null>(null);
    let platformFailure = $state.raw<PlatformFailure | null>(null);
    let itemMetrics = $state.raw<ToolItemMetrics | null>(null);
    let batchMetrics = $state.raw<ToolBatchMetrics | null>(null);
    let activeController: AbortController | null = null;
    let pendingRemoval = $state.raw<PendingRemoval | null>(null);

    let resultStale = $derived(result !== null && resultRevision !== revision);
    let sourceError = $derived.by(() => {
        if (!sourceFailure) return null;
        const copy = toolErrorMessage(sourceFailure);
        return $t(copy.key, {default: copy.fallback});
    });
    let currentCashSelectionKey = $derived([...selectedCashBrokerIds].sort((a, b) => a - b).join(','));
    let sourceCurrent = $derived(allocationSource?.asOfDate === asOfDate && sourceGeneration === accountGeneration);
    let brokerCashReady = $derived(selectedCashBrokerIds.length === 0 || (sourceCurrent && sourceCashSelectionKey === currentCashSelectionKey));
    let activeCash = $derived(cashMode === 'broker_copy' ? (selectedCashBrokerIds.length > 0 && brokerCashReady ? sourceCash : []) : manualCash);
    let authoritativePools = $derived(result?.cash_pools.availability === 'available' ? result.cash_pools.value : null);
    let canCopyCurrent = $derived(!resultStale && targets.length > 0 && targets.every((target) => result?.instruments.some((instrument) => instrument.instrument_key === target.instrument_key && instrument.current_weight_percent.availability === 'available')));
    let requiredCurrencies = $derived.by(() => {
        const currencies = new Set<string>();
        for (const holding of holdings) {
            const currency = holding.value.quote.currency;
            if (currency && currency !== reportCurrency) currencies.add(currency);
        }
        for (const row of activeCash) if (row.currency && row.currency !== reportCurrency) currencies.add(row.currency);
        for (const row of contributions) if (row.currency && row.currency !== reportCurrency) currencies.add(row.currency);
        return [...currencies].sort();
    });
    let assetChoices = $derived.by<PacAssetChoice[]>(() => {
        if (!allocationSource) return [];
        return allocationSource.assets.map((source) => {
            const linked = holdings.filter((holding) => holding.source?.assetId === source.assetId);
            return {
                ...source,
                selected: linked.length > 0,
                selectedSourceKeys: linked.map((holding) => holding.source?.contextKey ?? source.candidateKey),
                modifiedSourceKeys: linked.filter(isModified).map((holding) => holding.source?.contextKey ?? source.candidateKey),
                staleSourceKeys: linked.filter((holding) => holding.stale).map((holding) => holding.source?.contextKey ?? source.candidateKey),
            };
        });
    });

    function markRevised(): void {
        revision += 1;
        clientError = null;
        platformFailure = null;
    }

    function applySource(response: PacAllocationSource, selectionKey: string, generation: number): boolean {
        const previousCash = JSON.stringify(sourceCash);
        const previousHoldings = JSON.stringify(holdings.map((holding) => ({value: holding.value, stale: holding.stale})));
        allocationSource = response;
        sourceGeneration = generation;
        sourceCashSelectionKey = selectionKey;
        sourceCash = response.selectedCashBalances.map((balance) => ({...balance}));

        const manual = holdings.filter((holding) => holding.source === null);
        const selectedSourceIds = [...new Set(holdings.flatMap((holding) => (holding.source ? [holding.source.assetId] : [])))];
        const refreshed: RebalanceEditorHolding[] = [];
        for (const assetId of selectedSourceIds) {
            const current = holdings.filter((holding) => holding.source?.assetId === assetId);
            const fresh = response.assets.find((asset) => asset.assetId === assetId);
            if (!fresh) {
                current.forEach((holding) => {
                    holding.stale = true;
                    refreshed.push(holding);
                });
                continue;
            }
            const freshHoldings = createRebalanceHoldings(fresh, response.asOfDate);
            const existingContextKeys = new Set(current.map((holding) => holding.source?.contextKey));
            current.forEach((holding) => {
                const matching = freshHoldings.find((candidate) => candidate.source?.contextKey === holding.source?.contextKey);
                if (!matching) {
                    holding.stale = true;
                    refreshed.push(holding);
                } else if (isModified(holding)) {
                    holding.stale = !sameValue(holding.importedValue, matching.value);
                    if (matching.source) holding.source = matching.source;
                    refreshed.push(holding);
                } else {
                    refreshed.push(matching);
                }
            });
            refreshed.push(...freshHoldings.filter((holding) => !existingContextKeys.has(holding.source?.contextKey)));
        }
        holdings = [...refreshed, ...manual];
        targets = syncTargets(
            holdings.map((holding) => holding.value),
            targets,
        );
        return previousCash !== JSON.stringify(sourceCash) || previousHoldings !== JSON.stringify(holdings.map((holding) => ({value: holding.value, stale: holding.stale})));
    }

    $effect(() => {
        const requestedDate = asOfDate;
        const brokerIds = cashMode === 'broker_copy' ? [...selectedCashBrokerIds].sort((a, b) => a - b) : [];
        const selectionKey = brokerIds.join(',');
        void sourceRefresh;
        if (!requestedDate) {
            sourceController?.abort();
            sourceController = null;
            sourceLoading = false;
            sourceFailure = null;
            return;
        }

        const sequence = ++sourceSequence;
        const generation = accountGeneration;
        const controller = new AbortController();
        sourceController?.abort();
        sourceController = controller;
        sourceLoading = true;
        sourceFailure = null;
        void fetchPacAllocationSource(requestedDate, generation, {
            selectedCashBrokerIds: brokerIds,
            signal: controller.signal,
        })
            .then((response) => {
                if (sequence !== sourceSequence || generation !== accountGeneration || requestedDate !== asOfDate || selectionKey !== (cashMode === 'broker_copy' ? [...selectedCashBrokerIds].sort((a, b) => a - b).join(',') : '')) return;
                if (applySource(response, selectionKey, generation)) markRevised();
            })
            .catch((caught) => {
                if (sequence !== sourceSequence || generation !== accountGeneration || requestedDate !== asOfDate) return;
                const failure = toolViewError(caught);
                if (failure.code !== 'waiting_stopped' && failure.code !== 'session_changed') sourceFailure = failure;
            })
            .finally(() => {
                if (sequence === sourceSequence) {
                    sourceLoading = false;
                    if (sourceController === controller) sourceController = null;
                }
            });
        return () => controller.abort();
    });

    function refreshSource(): void {
        sourceFailure = null;
        sourceLoading = true;
        sourceRefresh += 1;
    }

    function setReportCurrency(value: string): void {
        if (value === reportCurrency) return;
        reportCurrency = value;
        markRevised();
    }

    function setAsOfDate(value: string): void {
        if (value === asOfDate) return;
        sourceFailure = null;
        sourceLoading = Boolean(value);
        asOfDate = value;
        for (const holding of holdings) if (holding.source) holding.stale = true;
        markRevised();
    }

    function setCashMode(mode: string): void {
        if (mode !== 'broker_copy' && mode !== 'manual') return;
        if (mode === cashMode) return;
        sourceFailure = null;
        sourceLoading = true;
        cashMode = mode;
        if (mode === 'manual' && manualCash.length === 0) manualCash.push(createMoney(reportCurrency));
        markRevised();
    }

    function toggleCashBroker(brokerId: number): void {
        sourceFailure = null;
        sourceLoading = true;
        const selected = new Set(selectedCashBrokerIds);
        if (selected.has(brokerId)) selected.delete(brokerId);
        else selected.add(brokerId);
        selectedCashBrokerIds = [...selected].sort((a, b) => a - b);
        markRevised();
    }

    function addMoney(kind: 'cash' | 'contributions'): void {
        if (kind === 'cash') {
            if (manualCash.length >= MAX_CURRENCIES) return;
            manualCash.push(createMoney(reportCurrency));
        } else {
            if (contributions.length >= MAX_CONTRIBUTIONS) return;
            contributionMode = 'custom';
            contributions.push(createContribution(reportCurrency));
        }
        markRevised();
    }

    function removeMoney(kind: 'cash' | 'contributions', index: number): void {
        if (kind === 'cash') manualCash.splice(index, 1);
        else {
            contributions.splice(index, 1);
            if (contributions.length === 0) contributionMode = 'none';
        }
        markRevised();
    }

    function addSourceAsset(choice: PacAssetChoice): void {
        if (!allocationSource || !sourceCurrent) return;
        const created = createRebalanceHoldings(choice, allocationSource.asOfDate);
        if (holdings.length + created.length > MAX_HOLDINGS) return;
        holdings.push(...created);
        targets = syncTargets(
            holdings.map((holding) => holding.value),
            targets,
        );
        markRevised();
    }

    function removeSourceAsset(assetId: number): void {
        holdings = holdings.filter((holding) => holding.source?.assetId !== assetId);
        targets = syncTargets(
            holdings.map((holding) => holding.value),
            targets,
        );
        markRevised();
    }

    function toggleSourceAsset(choice: PacAssetChoice): void {
        if (!choice.selected) {
            addSourceAsset(choice);
            return;
        }
        const linked = holdings.filter((holding) => holding.source?.assetId === choice.assetId);
        const target = linked[0] && targets.find((item) => item.instrument_key === linked[0]?.value.instrument_key);
        if (linked.some(isModified) || Boolean(target?.target_percent)) {
            pendingRemoval = {
                sourceAssetId: choice.assetId,
                holdingIndex: null,
                items: linked.map((holding) => `${holding.value.name} · ${holding.source?.brokerName ?? $t('tools.portfolioRebalancer.uncustodied', {default: 'No custody'})}`),
            };
            return;
        }
        removeSourceAsset(choice.assetId);
    }

    function addManualHolding(): void {
        if (holdings.length >= MAX_HOLDINGS) return;
        const holding = createManualRebalanceHolding(holdings.length);
        holding.value.name = $t('tools.pacAllocator.newManualAsset', {default: 'Manual Asset'});
        holding.importedValue = cloneDraft(holding.value);
        holdings.push(holding);
        targets = syncTargets(
            holdings.map((holding) => holding.value),
            targets,
        );
        markRevised();
    }

    function duplicateHolding(index: number): void {
        if (holdings.length >= MAX_HOLDINGS) return;
        const source = holdings[index];
        if (!source) return;
        const value = cloneDraft($state.snapshot(source.value));
        value.row_key = `manual:holding:${crypto.randomUUID()}`;
        holdings.splice(index + 1, 0, {
            value,
            source: null,
            importedValue: cloneDraft(value),
            stale: false,
        });
        targets = syncTargets(
            holdings.map((holding) => holding.value),
            targets,
        );
        markRevised();
    }

    function requestHoldingRemoval(index: number): void {
        const holding = holdings[index];
        if (!holding) return;
        const linkedCount = holdings.filter((candidate) => candidate.value.instrument_key === holding.value.instrument_key).length;
        const target = targets.find((candidate) => candidate.instrument_key === holding.value.instrument_key);
        if (isModified(holding) || (linkedCount === 1 && Boolean(target?.target_percent))) {
            pendingRemoval = {
                sourceAssetId: null,
                holdingIndex: index,
                items: [`${holding.value.name} · ${holding.source?.brokerName ?? $t('tools.portfolioRebalancer.uncustodied', {default: 'No custody'})}`],
            };
            return;
        }
        removeHolding(index);
    }

    function removeHolding(index: number): void {
        holdings.splice(index, 1);
        targets = syncTargets(
            holdings.map((holding) => holding.value),
            targets,
        );
        markRevised();
    }

    function confirmRemoval(): void {
        if (!pendingRemoval) return;
        if (pendingRemoval.sourceAssetId !== null) removeSourceAsset(pendingRemoval.sourceAssetId);
        else if (pendingRemoval.holdingIndex !== null) removeHolding(pendingRemoval.holdingIndex);
        pendingRemoval = null;
    }

    function holdingChanged(): void {
        targets = syncTargets(
            holdings.map((holding) => holding.value),
            targets,
        );
        markRevised();
    }

    function copyCurrentDistribution(): void {
        if (!result || resultStale) return;
        const currentByInstrument = new Map(result.instruments.filter((instrument) => instrument.current_weight_percent.availability === 'available').map((instrument) => [instrument.instrument_key, instrument.current_weight_percent.value?.approximation ?? '']));
        const current = targets.map((target) => currentByInstrument.get(target.instrument_key) ?? '');
        if (current.some((value) => value === '')) return;
        const closed = closePercentDistribution(current);
        targets.forEach((target, index) => {
            target.target_percent = closed[index] ?? '';
        });
        markRevised();
    }

    function buildInput(): RebalancerInput {
        return {
            operation: 'analyze',
            report_currency: reportCurrency,
            as_of_date: asOfDate || null,
            holdings: holdings.map((holding) => cloneDraft($state.snapshot(holding.value))),
            targets: targets.map(({instrument_key, target_percent}) => ({instrument_key, target_percent})),
            cash_balances: activeCash.map((money) => ({...money})),
            contributions: contributionMode === 'none' ? [] : contributions.map((money) => ({...money})),
            valuation_rates: valuationRates.map((rate) => ({...rate})),
        };
    }

    function requestIsCurrent(sequence: number, requestedRevision: number, generation: number): boolean {
        if (sequence !== requestSequence || requestedRevision !== revision || generation !== accountGeneration) return false;
        try {
            assertToolAccount(generation);
            return true;
        } catch {
            return false;
        }
    }

    async function analyze(): Promise<void> {
        if (busy || (cashMode === 'broker_copy' && (sourceLoading || !brokerCashReady))) return;
        const requestedRevision = revision;
        const generation = accountGeneration;
        const sequence = ++requestSequence;
        const controller = new AbortController();
        activeController = controller;
        busy = true;
        clientError = null;
        platformFailure = null;
        try {
            const reply = await runTool('portfolio_rebalancer', '1.0.0', {
                descriptor,
                correlationId: `rebalancer-${sequence}-${requestedRevision}`,
                parameters: buildInput(),
                signal: controller.signal,
            });
            if (!requestIsCurrent(sequence, requestedRevision, generation)) return;
            itemMetrics = reply.metrics;
            batchMetrics = reply.batch.metrics;
            if (reply.status === 'success') {
                result = reply.result;
                resultRevision = requestedRevision;
            } else {
                result = null;
                resultRevision = null;
                platformFailure = {code: reply.error.code, retryable: reply.error.retryable};
            }
        } catch (caught) {
            if (!requestIsCurrent(sequence, requestedRevision, generation)) return;
            const failure = toolViewError(caught);
            if (failure.code === 'waiting_stopped' || failure.code === 'session_changed') return;
            clientError = failure;
            const copy = toolErrorMessage(failure);
            notify({
                name: 'tool.rebalancer-analyze.failed',
                detail: {kind: failure.kind, code: failure.code},
                toast: {variant: 'error', message: $t(copy.key, {default: copy.fallback})},
            });
        } finally {
            if (sequence === requestSequence) {
                busy = false;
                activeController = null;
            }
        }
    }

    onDestroy(() => {
        requestSequence += 1;
        sourceSequence += 1;
        activeController?.abort();
        sourceController?.abort();
    });
</script>

<form
    class="min-w-0 space-y-4"
    data-testid="portfolio-rebalancer-tool"
    data-busy={busy}
    aria-busy={busy}
    onsubmit={(event) => {
        event.preventDefault();
        void analyze();
    }}
>
    <section class="rounded-xl border border-blue-200 bg-blue-50/70 p-3 text-xs leading-5 text-blue-950 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-100">
        <strong>{$t('tools.portfolioRebalancer.p1.title', {default: 'Portfolio Rebalancer P1'})}</strong>
        <span class="ml-1">{$t('tools.portfolioRebalancer.p1.description', {default: 'Compares current invested allocation with a final target. It does not recommend or generate trades.'})}</span>
    </section>

    <section class="grid gap-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60 sm:grid-cols-2">
        <label class="space-y-1 text-xs font-medium text-gray-600 dark:text-gray-300">
            <span>{$t('tools.pacAllocator.reportCurrency')}</span>
            <CurrencySearchSelect value={reportCurrency} compact testId="rebalancer-report-currency" disabled={busy} onchange={setReportCurrency} />
        </label>
        <SingleDatePicker value={asOfDate} label={$t('tools.pacAllocator.asOfDate')} inputStyle clearable disabled={busy} onchange={setAsOfDate} testid="rebalancer-analysis-date" />
    </section>

    <section class="space-y-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid="rebalancer-holdings-step">
        <OwnedAssetGallery
            assets={assetChoices}
            loading={sourceLoading}
            error={sourceError}
            title={$t('tools.portfolioRebalancer.holdings.title', {default: '1. Portfolio holdings'})}
            description={$t('tools.portfolioRebalancer.holdings.hint', {default: 'Select Assets to copy all their custody contexts, or add a manual holding.'})}
            disabled={!sourceCurrent || sourceLoading || busy}
            manualDisabled={busy || holdings.length >= MAX_HOLDINGS}
            ontoggle={toggleSourceAsset}
            onretry={refreshSource}
            onaddmanual={addManualHolding}
        />
        {#if holdings.length > 0}
            <div class="space-y-2" data-testid="rebalancer-holdings">
                {#each holdings as holding, index (holding.value.row_key)}
                    <RebalanceHoldingEditor bind:holding={holdings[index]} {index} disabled={busy} onduplicate={() => duplicateHolding(index)} onremove={() => requestHoldingRemoval(index)} onchange={holdingChanged} />
                {/each}
            </div>
        {/if}
    </section>

    <AllocationTargetEditor {targets} service="rebalancer" disabled={busy} {canCopyCurrent} oncopycurrent={copyCurrentDistribution} onchange={markRevised} />

    <details class="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid="rebalancer-funding-context">
        <summary class="cursor-pointer text-sm font-semibold text-gray-900 dark:text-white">
            {$t('tools.portfolioRebalancer.funding.title', {default: 'Optional liquidity context'})}
        </summary>
        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {$t('tools.portfolioRebalancer.funding.hint', {default: 'Cash and contributions are reported separately. P1 does not use them to infer executable trades.'})}
        </p>
        <div class="mt-3 space-y-3">
            <PacMoneySection
                kind="cash"
                title={$t('tools.pacAllocator.cash.existing')}
                description={$t('tools.pacAllocator.cash.existingHint')}
                mode={cashMode}
                values={manualCash}
                cashSources={allocationSource?.cashSources ?? []}
                selectedBrokerIds={selectedCashBrokerIds}
                {sourceLoading}
                {sourceError}
                sourceStale={sourceLoading}
                disabled={busy}
                onmodechange={setCashMode}
                onadd={() => addMoney('cash')}
                onremove={(index) => removeMoney('cash', index)}
                onchange={markRevised}
                onbrokertoggle={toggleCashBroker}
                onretry={refreshSource}
            />
            <PacMoneySection
                kind="contributions"
                title={$t('tools.pacAllocator.cash.contributions')}
                description={$t('tools.pacAllocator.cash.contributionsHint')}
                mode={contributionMode}
                values={contributions}
                maxEntries={MAX_CONTRIBUTIONS}
                disabled={busy}
                onadd={() => addMoney('contributions')}
                onremove={(index) => removeMoney('contributions', index)}
                onchange={markRevised}
            />
            <AllocationFundingSummary existing={activeCash} {contributions} {authoritativePools} pending={busy || (cashMode === 'broker_copy' && sourceLoading)} stale={resultStale} />
        </div>
    </details>

    <AllocationFxSection rates={valuationRates} {requiredCurrencies} {reportCurrency} {asOfDate} {accountGeneration} disabled={busy} onchange={markRevised} />

    {#if clientError}
        {@const copy = toolErrorMessage(clientError)}
        <section class="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="rebalancer-client-error">
            {$t(copy.key, {default: copy.fallback})}
        </section>
    {:else if platformFailure}
        <section class="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="rebalancer-platform-error">
            {$t('tools.pacAllocator.platformError')} <span class="font-mono text-xs">{platformFailure.code}</span>
        </section>
    {/if}

    <div class="flex justify-end gap-2">
        {#if busy}
            <button
                class="inline-flex min-h-9 items-center gap-1.5 rounded-md border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 dark:border-amber-800 dark:bg-gray-900 dark:text-amber-200"
                type="button"
                onclick={() => activeController?.abort()}
                data-testid="rebalancer-stop-waiting"
            >
                <CircleStop size={15} />
                {$t('tools.pacAllocator.stopWaiting')}
            </button>
        {/if}
        <button
            class="inline-flex min-h-9 items-center gap-1.5 rounded-md bg-libre-green px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50 dark:text-gray-950"
            type="submit"
            disabled={busy || (cashMode === 'broker_copy' && (sourceLoading || !brokerCashReady))}
            data-testid="rebalancer-analyze"
        >
            {#if busy}<LoaderCircle class="animate-spin" size={15} />{/if}
            {$t('tools.portfolioRebalancer.analyze', {default: 'Analyze target gaps'})}
        </button>
    </div>

    <RebalancerResultPanel output={result} stale={resultStale} />

    {#if itemMetrics}
        <ToolExecutionMetrics item={itemMetrics} batch={batchMetrics} />
    {/if}
</form>

{#if pendingRemoval}
    <ConfirmModal
        open
        title={$t('tools.portfolioRebalancer.customizedRemovalTitle', {default: 'Remove customized holding?'})}
        message={$t('tools.portfolioRebalancer.customizedRemovalMessage', {default: 'Removing this holding will discard its scenario settings.'})}
        items={pendingRemoval.items}
        itemsLabel={$t('tools.pacAllocator.customizedRemovalItems', {default: 'Settings that will be lost'})}
        confirmText={$t('common.remove')}
        warning
        onConfirm={confirmRemoval}
        onCancel={() => (pendingRemoval = null)}
        testId="rebalancer-customized-removal-confirm"
    />
{/if}
