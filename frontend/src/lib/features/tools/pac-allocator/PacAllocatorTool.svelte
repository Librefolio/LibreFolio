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
    import PacAssetEditor from './PacAssetEditor.svelte';
    import PacMoneySection from './PacMoneySection.svelte';
    import PacResultPanel from './PacResultPanel.svelte';
    import {fetchPacAllocationSource, type PacAllocationSource} from './allocationSource';
    import {cloneDraft, createManualPacAsset, createPacAsset, syncTargets} from './draftFactories';
    import type {AllocationTargetDraft, PacAssetChoice, PacCashSourceState, PacContributionInput, PacContributionMode, PacEditorAsset, PacInput, PacMoneyInput, PacRateInput} from './editorTypes';

    let {descriptor, accountGeneration}: ToolHostPropsV1<'pac_allocator', '1.0.0'> = $props();
    type PacOutput = ToolOutput<'pac_allocator', '1.0.0'>;

    interface PlatformFailure {
        code: string;
        retryable: boolean;
    }

    interface PendingRemoval {
        sourceAssetId: number | null;
        editorIndex: number | null;
        items: string[];
    }

    const MAX_ASSETS = 32;
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

    function isModified(asset: PacEditorAsset): boolean {
        return asset.importedValue !== null && !sameValue(asset.value, asset.importedValue);
    }

    let reportCurrency = $state(userSettings.get()?.base_currency ?? 'EUR');
    let asOfDate = $state(todayIso());
    let assets = $state<PacEditorAsset[]>([]);
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
    let result = $state.raw<PacOutput | null>(null);
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
    let requiredCurrencies = $derived.by(() => {
        const currencies = new Set<string>();
        for (const row of activeCash) if (row.currency && row.currency !== reportCurrency) currencies.add(row.currency);
        for (const row of contributions) if (row.currency && row.currency !== reportCurrency) currencies.add(row.currency);
        return [...currencies].sort();
    });
    let assetChoices = $derived.by<PacAssetChoice[]>(() => {
        if (!allocationSource) return [];
        return allocationSource.assets.map((source) => {
            const editor = assets.find((asset) => asset.source?.assetId === source.assetId);
            return {
                ...source,
                selected: Boolean(editor),
                selectedSourceKeys: editor ? [source.candidateKey] : [],
                modifiedSourceKeys: editor && isModified(editor) ? [source.candidateKey] : [],
                staleSourceKeys: editor?.stale ? [source.candidateKey] : [],
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
        const previousAssets = JSON.stringify(assets.map((asset) => ({value: asset.value, stale: asset.stale})));
        allocationSource = response;
        sourceGeneration = generation;
        sourceCashSelectionKey = selectionKey;
        sourceCash = response.selectedCashBalances.map((balance) => ({...balance}));
        for (let index = 0; index < assets.length; index += 1) {
            const editor = assets[index];
            if (!editor?.source) continue;
            const fresh = response.assets.find((candidate) => candidate.assetId === editor.source?.assetId);
            if (!fresh) {
                editor.stale = true;
                continue;
            }
            const replacement = createPacAsset(fresh);
            if (isModified(editor)) {
                editor.source = fresh;
                editor.stale = !sameValue(editor.importedValue, replacement.value);
                continue;
            }
            assets[index] = replacement;
        }
        targets = syncTargets(
            assets.map((asset) => asset.value),
            targets,
        );
        return previousCash !== JSON.stringify(sourceCash) || previousAssets !== JSON.stringify(assets.map((asset) => ({value: asset.value, stale: asset.stale})));
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
        for (const asset of assets) if (asset.source) asset.stale = true;
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
        if (!allocationSource || !sourceCurrent || assets.length >= MAX_ASSETS) return;
        assets.push(createPacAsset(choice));
        targets = syncTargets(
            assets.map((asset) => asset.value),
            targets,
        );
        markRevised();
    }

    function removeSourceAsset(assetId: number): void {
        assets = assets.filter((asset) => asset.source?.assetId !== assetId);
        targets = syncTargets(
            assets.map((asset) => asset.value),
            targets,
        );
        markRevised();
    }

    function toggleSourceAsset(choice: PacAssetChoice): void {
        if (!choice.selected) {
            addSourceAsset(choice);
            return;
        }
        const editor = assets.find((asset) => asset.source?.assetId === choice.assetId);
        const target = editor && targets.find((item) => item.instrument_key === editor.value.instrument_key);
        if (editor && (isModified(editor) || Boolean(target?.target_percent))) {
            pendingRemoval = {sourceAssetId: choice.assetId, editorIndex: null, items: [editor.value.name]};
            return;
        }
        removeSourceAsset(choice.assetId);
    }

    function addManualAsset(): void {
        if (assets.length >= MAX_ASSETS) return;
        const asset = createManualPacAsset(assets.length);
        asset.value.name = $t('tools.pacAllocator.newManualAsset', {default: 'Manual Asset'});
        asset.importedValue = cloneDraft(asset.value);
        assets.push(asset);
        targets = syncTargets(
            assets.map((asset) => asset.value),
            targets,
        );
        markRevised();
    }

    function requestAssetRemoval(index: number): void {
        const asset = assets[index];
        if (!asset) return;
        if (asset.source) {
            toggleSourceAsset(
                assetChoices.find((choice) => choice.assetId === asset.source?.assetId) ?? {
                    ...asset.source,
                    selected: true,
                    selectedSourceKeys: [],
                    modifiedSourceKeys: [],
                    staleSourceKeys: [],
                },
            );
            return;
        }
        if (isModified(asset) || targets.find((target) => target.instrument_key === asset.value.instrument_key)?.target_percent) {
            pendingRemoval = {sourceAssetId: null, editorIndex: index, items: [asset.value.name]};
            return;
        }
        assets.splice(index, 1);
        targets = syncTargets(
            assets.map((item) => item.value),
            targets,
        );
        markRevised();
    }

    function confirmRemoval(): void {
        if (!pendingRemoval) return;
        if (pendingRemoval.sourceAssetId !== null) removeSourceAsset(pendingRemoval.sourceAssetId);
        else if (pendingRemoval.editorIndex !== null) {
            assets.splice(pendingRemoval.editorIndex, 1);
            targets = syncTargets(
                assets.map((asset) => asset.value),
                targets,
            );
            markRevised();
        }
        pendingRemoval = null;
    }

    function assetChanged(index: number): void {
        const asset = assets[index];
        if (!asset) return;
        targets = syncTargets(
            assets.map((item) => item.value),
            targets,
        );
        markRevised();
    }

    function buildInput(): PacInput {
        return {
            operation: 'analyze',
            report_currency: reportCurrency,
            as_of_date: asOfDate || null,
            assets: assets.map((asset) => cloneDraft($state.snapshot(asset.value))),
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
            const reply = await runTool('pac_allocator', '1.0.0', {
                descriptor,
                correlationId: `pac-${sequence}-${requestedRevision}`,
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
                name: 'tool.pac-analyze.failed',
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
    data-testid="pac-allocator-tool"
    data-busy={busy}
    aria-busy={busy}
    onsubmit={(event) => {
        event.preventDefault();
        void analyze();
    }}
>
    <section class="rounded-xl border border-blue-200 bg-blue-50/70 p-3 text-xs leading-5 text-blue-950 dark:border-blue-900 dark:bg-blue-950/20 dark:text-blue-100">
        <strong>{$t('tools.pacAllocator.p1.title', {default: 'PAC Allocator P1'})}</strong>
        <span class="ml-1">{$t('tools.pacAllocator.p1.description', {default: 'Distributes available liquidity by target percentage. It does not inspect the current portfolio or generate orders.'})}</span>
    </section>

    <section class="grid gap-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60 sm:grid-cols-2">
        <label class="space-y-1 text-xs font-medium text-gray-600 dark:text-gray-300">
            <span>{$t('tools.pacAllocator.reportCurrency')}</span>
            <CurrencySearchSelect value={reportCurrency} compact testId="pac-report-currency" disabled={busy} onchange={setReportCurrency} />
        </label>
        <SingleDatePicker value={asOfDate} label={$t('tools.pacAllocator.asOfDate')} inputStyle clearable disabled={busy} onchange={setAsOfDate} testid="pac-analysis-date" />
    </section>

    <section class="space-y-3" data-testid="pac-funding">
        <div>
            <h2 class="text-sm font-semibold text-gray-900 dark:text-white">{$t('tools.pacAllocator.fundsTitle', {default: '1. Available funds'})}</h2>
            <p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.fundsHint', {default: 'Copy native OWNER Broker cash or enter exact amounts. New contributions remain separate.'})}</p>
        </div>
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
    </section>

    <section class="space-y-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60">
        <OwnedAssetGallery
            assets={assetChoices}
            loading={sourceLoading}
            error={sourceError}
            title={$t('tools.pacAllocator.assets.title', {default: '2. Assets to fund'})}
            description={$t('tools.pacAllocator.assets.hint', {default: 'Choose canonical Assets. Current prices are source context only and do not affect the P1 split.'})}
            disabled={!sourceCurrent || sourceLoading || busy}
            manualDisabled={busy || assets.length >= MAX_ASSETS}
            ontoggle={toggleSourceAsset}
            onretry={refreshSource}
            onaddmanual={addManualAsset}
        />
        {#if assets.length > 0}
            <div class="grid gap-2 lg:grid-cols-2" data-testid="pac-assets">
                {#each assets as asset, index (asset.value.instrument_key)}
                    <PacAssetEditor bind:asset={assets[index]} {index} disabled={busy} onremove={() => requestAssetRemoval(index)} onchange={() => assetChanged(index)} />
                {/each}
            </div>
        {/if}
    </section>

    <AllocationTargetEditor {targets} service="pac" disabled={busy} onchange={markRevised} />

    <AllocationFxSection rates={valuationRates} {requiredCurrencies} {reportCurrency} {asOfDate} {accountGeneration} disabled={busy} onchange={markRevised} />

    {#if clientError}
        {@const copy = toolErrorMessage(clientError)}
        <section class="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="pac-client-error">
            {$t(copy.key, {default: copy.fallback})}
        </section>
    {:else if platformFailure}
        <section class="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="pac-platform-error">
            {$t('tools.pacAllocator.platformError')} <span class="font-mono text-xs">{platformFailure.code}</span>
        </section>
    {/if}

    <div class="flex justify-end gap-2">
        {#if busy}
            <button
                class="inline-flex min-h-9 items-center gap-1.5 rounded-md border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 dark:border-amber-800 dark:bg-gray-900 dark:text-amber-200"
                type="button"
                onclick={() => activeController?.abort()}
                data-testid="pac-stop-waiting"
            >
                <CircleStop size={15} />
                {$t('tools.pacAllocator.stopWaiting')}
            </button>
        {/if}
        <button
            class="inline-flex min-h-9 items-center gap-1.5 rounded-md bg-libre-green px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-50 dark:text-gray-950"
            type="submit"
            disabled={busy || (cashMode === 'broker_copy' && (sourceLoading || !brokerCashReady))}
            data-testid="pac-analyze"
        >
            {#if busy}<LoaderCircle class="animate-spin" size={15} />{/if}
            {$t('tools.pacAllocator.analyze', {default: 'Analyze PAC allocation'})}
        </button>
    </div>

    <PacResultPanel output={result} stale={resultStale} />

    {#if itemMetrics}
        <ToolExecutionMetrics item={itemMetrics} batch={batchMetrics} />
    {/if}
</form>

{#if pendingRemoval}
    <ConfirmModal
        open
        title={$t('tools.pacAllocator.customizedRemovalTitle', {default: 'Remove customized Asset?'})}
        message={$t('tools.pacAllocator.customizedRemovalMessage', {default: 'Removing this Asset will discard its target and custom settings.'})}
        items={pendingRemoval.items}
        itemsLabel={$t('tools.pacAllocator.customizedRemovalItems', {default: 'Settings that will be lost'})}
        confirmText={$t('common.remove')}
        warning
        onConfirm={confirmRemoval}
        onCancel={() => (pendingRemoval = null)}
        testId="pac-customized-removal-confirm"
    />
{/if}
