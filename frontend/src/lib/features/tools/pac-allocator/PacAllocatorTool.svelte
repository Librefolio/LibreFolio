<script lang="ts">
    import {onDestroy} from 'svelte';
    import {AlertTriangle, CircleStop, CloudDownload, Info, LoaderCircle, PencilLine, Plus, RefreshCw, Trash2} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {userSettings} from '$lib/stores/app/settings';
    import {lookupFxRate} from '$lib/stores/fxStoreRegistry';
    import {currencyStoreVersion, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {runTool} from '$lib/features/tools/client';
    import {ToolClientError, assertToolAccount, type ToolBatchMetrics, type ToolItemMetrics, type ToolOutput} from '$lib/features/tools/contracts';
    import {toolErrorMessage, toolViewError} from '$lib/features/tools/presentation';
    import type {ToolHostPropsV1} from '$lib/features/tools/registry';
    import ToolExecutionMetrics from '$lib/features/tools/components/ToolExecutionMetrics.svelte';
    import OwnedAssetGallery from './OwnedAssetGallery.svelte';
    import PacContextEditor from './PacContextEditor.svelte';
    import PacMoneySection from './PacMoneySection.svelte';
    import PacResultPanel from './PacResultPanel.svelte';
    import {fetchPacAllocationSource, type PacAllocationSource, type PacAllocationSourceAsset, type PacAllocationSourceContext} from './allocationSource';
    import type {PacAssetChoice, PacCashSourceState, PacContributionInput, PacDraft, PacDraftRow, PacEditorRow, PacMoneyInput, PacRateInput, PacRowSource, PacInput} from './editorTypes';

    let {descriptor, accountGeneration}: ToolHostPropsV1<'pac_allocator', '1.0.0'> = $props();

    type PacOutput = ToolOutput<'pac_allocator', '1.0.0'>;

    interface PlatformFailure {
        code: string;
        retryable: boolean;
        issueCount: number;
    }

    interface ForeignCurrencyReason {
        currency: string;
        assetNames: string[];
        existingCash: boolean;
        contribution: boolean;
    }

    type PendingConfirmation = {kind: 'deselect'; assetId: number; items: string[]} | {kind: 'remove-row'; index: number; items: string[]} | {kind: 'refresh'; items: string[]};

    const MAX_ROWS = 32;
    const MAX_CURRENCIES = 4;
    let identitySequence = 0;

    function todayIso(): string {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function nextRowKey(prefix = 'local-row'): string {
        identitySequence += 1;
        return `${prefix}-${identitySequence}`;
    }

    function cloneRowValue(row: PacDraftRow): PacDraftRow {
        return {
            row_key: row.row_key,
            instrument_key: row.instrument_key,
            name: row.name,
            initial_quantity: row.initial_quantity,
            quote: {...row.quote},
            target_percent: row.target_percent,
            buy_grid: {...row.buy_grid},
        };
    }

    function createManualRow(): PacEditorRow {
        const rowKey = nextRowKey();
        return {
            origin: 'manual',
            source: null,
            importedValue: null,
            stale: false,
            value: {
                row_key: rowKey,
                instrument_key: `local-instrument-${identitySequence}`,
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
            },
        };
    }

    function createDraft(): PacDraft {
        return {
            operation: 'analyze',
            report_currency: userSettings.get()?.base_currency ?? 'EUR',
            as_of_date: todayIso(),
            rows: [],
            cash: {
                mode: 'broker_copy',
                selectedBrokerIds: [],
                sourceAsOfDate: null,
                sourceFingerprint: null,
                backendAggregatedBalances: [],
                manualBalances: [],
                sources: [],
                stale: false,
            },
            contributionMode: 'none',
            contributions: [],
            valuationRates: [],
        };
    }

    function createMoney(currency = ''): PacMoneyInput {
        return {currency, amount: ''};
    }

    function createContribution(currency = ''): PacContributionInput {
        return {currency, amount: '', monetary_step: '0.01'};
    }

    function createRate(currency = ''): PacRateInput {
        return {currency, rate_to_report: '', reference_date: ''};
    }

    function sourceRowValue(asset: PacAllocationSourceAsset, context: PacAllocationSourceContext | null, rowKey = context?.contextKey ?? asset.candidateKey): PacDraftRow {
        return {
            row_key: rowKey,
            instrument_key: asset.instrumentKey,
            name: asset.name,
            initial_quantity: context?.custodyQuantity ?? '0',
            quote: {
                raw_price: asset.quote.rawPrice,
                currency: asset.quote.currency,
                quote_base_quantity: asset.quote.quoteBaseQuantity,
                reference_date: asset.quote.referenceDate,
            },
            target_percent: '',
            buy_grid: {
                mode: 'whole',
                quantity_step: '1',
            },
        };
    }

    function sourceMetadata(asset: PacAllocationSourceAsset, context: PacAllocationSourceContext | null, sourceDate: string): PacRowSource {
        return {
            kind: context ? 'portfolio_context' : 'catalog_candidate',
            assetId: asset.assetId,
            candidateKey: asset.candidateKey,
            assetActive: asset.active,
            assetType: asset.assetType,
            assetIconUrl: asset.iconUrl,
            usageScope: asset.usageScope,
            contextKey: context?.contextKey ?? null,
            brokerId: context?.brokerId ?? null,
            brokerName: context?.brokerName ?? null,
            brokerIconUrl: context?.brokerIconUrl ?? null,
            brokerPortalUrl: context?.brokerPortalUrl ?? null,
            brokerDefaultImportPlugin: context?.brokerDefaultImportPlugin ?? null,
            ownershipSharePercent: context?.ownershipSharePercent ?? null,
            sourceAsOfDate: sourceDate,
            quoteSource: asset.quote.source,
            quoteReferenceDate: asset.quote.referenceDate,
        };
    }

    function cashSelectionKey(brokerIds: readonly number[]): string {
        return [...brokerIds].sort((left, right) => left - right).join(',');
    }

    function sameMoneyInputs(left: readonly PacMoneyInput[], right: readonly PacMoneyInput[]): boolean {
        return JSON.stringify(left) === JSON.stringify(right);
    }

    function applyBrokerCashSource(source: PacAllocationSource, selectedBrokerIds: readonly number[]): boolean {
        const balances = source.selectedCashBalances.map((balance) => ({...balance}));
        const changed = !sameMoneyInputs(draft.cash.backendAggregatedBalances, balances);
        draft.cash.backendAggregatedBalances = balances;
        draft.cash.sources = source.cashSources;
        draft.cash.sourceAsOfDate = source.asOfDate;
        draft.cash.sourceFingerprint = `${source.generatedAt}|${source.asOfDate}|${cashSelectionKey(selectedBrokerIds)}`;
        draft.cash.stale = false;
        return changed;
    }

    function markChangedSourceRowsStale(source: PacAllocationSource): void {
        for (const row of draft.rows) {
            if (!row.source || !row.importedValue) continue;
            const asset = source.assets.find((candidate) => candidate.assetId === row.source?.assetId);
            if (!asset) {
                row.stale = true;
                continue;
            }
            const context = row.source.kind === 'portfolio_context' ? asset.contexts.find((candidate) => candidate.contextKey === row.source?.contextKey) : null;
            if ((row.source.kind === 'portfolio_context' && !context) || (row.source.kind === 'catalog_candidate' && asset.contexts.length > 0)) {
                row.stale = true;
                continue;
            }
            const freshValue = sourceRowValue(asset, context ?? null, row.value.row_key);
            const freshSource = sourceMetadata(asset, context ?? null, source.asOfDate);
            if (
                sourceFieldsDiffer(freshValue, row.importedValue) ||
                freshSource.sourceAsOfDate !== row.source.sourceAsOfDate ||
                freshSource.brokerName !== row.source.brokerName ||
                freshSource.ownershipSharePercent !== row.source.ownershipSharePercent ||
                freshSource.quoteSource !== row.source.quoteSource
            ) {
                row.stale = true;
            }
        }
    }

    function samePayload(left: PacDraftRow, right: PacDraftRow): boolean {
        return JSON.stringify(left) === JSON.stringify(right);
    }

    function sourceFieldsDiffer(current: PacDraftRow, baseline: PacDraftRow): boolean {
        return (
            current.instrument_key !== baseline.instrument_key ||
            current.name !== baseline.name ||
            current.initial_quantity !== baseline.initial_quantity ||
            current.quote.raw_price !== baseline.quote.raw_price ||
            current.quote.currency !== baseline.quote.currency ||
            current.quote.quote_base_quantity !== baseline.quote.quote_base_quantity ||
            current.quote.reference_date !== baseline.quote.reference_date
        );
    }

    function rowIsModified(row: PacEditorRow): boolean {
        return row.importedValue !== null && !samePayload(row.value, row.importedValue);
    }

    let draft = $state<PacDraft>(createDraft());
    let revision = $state(0);
    let requestRevision = $state<number | null>(null);
    let resultRevision = $state<number | null>(null);
    let ignoredRevision = $state<number | null>(null);
    let requestSequence = 0;
    let busy = $state(false);
    let result = $state.raw<PacOutput | null>(null);
    let clientError = $state.raw<ToolClientError | null>(null);
    let platformFailure = $state.raw<PlatformFailure | null>(null);
    let itemMetrics = $state.raw<ToolItemMetrics | null>(null);
    let batchMetrics = $state.raw<ToolBatchMetrics | null>(null);
    let activeController: AbortController | null = null;

    let allocationSource = $state.raw<PacAllocationSource | null>(null);
    let sourceLoading = $state(false);
    let sourceFailure = $state.raw<ToolClientError | null>(null);
    let sourceRefreshToken = $state(0);
    let sourceRequestSequence = 0;
    let allocationSourceCashSelectionKey = $state('');
    let sourceController: AbortController | null = null;
    let pendingConfirmation = $state.raw<PendingConfirmation | null>(null);
    let fxCopySequence = 0;
    let fxCopyingCurrency = $state<string | null>(null);
    let fxCopyErrors = $state<Record<string, string>>({});

    const resultIsStale = $derived(result !== null && resultRevision !== revision);
    const clientErrorCopy = $derived(clientError ? toolErrorMessage(clientError) : null);
    const sourceError = $derived.by(() => {
        if (!sourceFailure) return null;
        const copy = toolErrorMessage(sourceFailure);
        return $t(copy.key, {default: copy.fallback});
    });
    const sourceIsCurrent = $derived(allocationSource?.asOfDate === draft.as_of_date);
    const staleSourceRows = $derived(draft.rows.filter((row) => row.source !== null && row.stale));
    const cashSourceBlocked = $derived(draft.cash.mode === 'broker_copy' && (draft.cash.stale || sourceLoading || sourceFailure !== null || draft.cash.sourceAsOfDate !== draft.as_of_date));
    const foreignCurrencyReasons = $derived.by<ForeignCurrencyReason[]>(() => {
        const reasons = new Map<string, ForeignCurrencyReason>();
        const reportCurrency = draft.report_currency.trim().toUpperCase();
        const reasonFor = (currency: string): ForeignCurrencyReason => {
            const current = reasons.get(currency);
            if (current) return current;
            const created = {currency, assetNames: [], existingCash: false, contribution: false};
            reasons.set(currency, created);
            return created;
        };
        for (const row of draft.rows) {
            const currency = row.value.quote.currency?.trim().toUpperCase();
            if (!currency || currency === reportCurrency) continue;
            const reason = reasonFor(currency);
            const name = row.value.name?.trim();
            if (name && !reason.assetNames.includes(name)) reason.assetNames.push(name);
        }
        const activeCash = draft.cash.mode === 'manual' ? draft.cash.manualBalances : draft.cash.mode === 'broker_copy' && !draft.cash.stale ? draft.cash.backendAggregatedBalances : [];
        for (const money of activeCash) {
            const currency = money.currency?.trim().toUpperCase();
            if (currency && currency !== reportCurrency) reasonFor(currency).existingCash = true;
        }
        if (draft.contributionMode === 'custom') {
            for (const money of draft.contributions) {
                const currency = money.currency?.trim().toUpperCase();
                if (currency && currency !== reportCurrency) reasonFor(currency).contribution = true;
            }
        }
        return [...reasons.values()].sort((left, right) => left.currency.localeCompare(right.currency));
    });
    const foreignCurrencies = $derived(foreignCurrencyReasons.map((reason) => reason.currency));
    const fxSectionVisible = $derived(foreignCurrencyReasons.length > 0 || draft.valuationRates.length > 0);
    const assetChoices = $derived.by<PacAssetChoice[]>(() => {
        if (!allocationSource) return [];
        return allocationSource.assets.map((asset) => {
            const linkedRows = draft.rows.filter((row) => row.source?.assetId === asset.assetId);
            const sourceKey = (row: PacEditorRow): string | null => row.source?.contextKey ?? row.source?.candidateKey ?? null;
            return {
                ...asset,
                selected: linkedRows.length > 0,
                selectedSourceKeys: [...new Set(linkedRows.map(sourceKey).filter((key): key is string => Boolean(key)))],
                modifiedSourceKeys: [
                    ...new Set(
                        linkedRows
                            .filter(rowIsModified)
                            .map(sourceKey)
                            .filter((key): key is string => Boolean(key)),
                    ),
                ],
                staleSourceKeys: [
                    ...new Set(
                        linkedRows
                            .filter((row) => row.stale)
                            .map(sourceKey)
                            .filter((key): key is string => Boolean(key)),
                    ),
                ],
            };
        });
    });

    $effect(() => {
        const requestedDate = draft.as_of_date;
        const requestedCashBrokerIds = draft.cash.mode === 'broker_copy' ? [...draft.cash.selectedBrokerIds].sort((left, right) => left - right) : [];
        const requestedCashSelectionKey = cashSelectionKey(requestedCashBrokerIds);
        void sourceRefreshToken;
        if (!requestedDate) {
            allocationSource = null;
            sourceFailure = null;
            sourceLoading = false;
            if (draft.cash.mode === 'broker_copy') draft.cash.stale = true;
            return;
        }

        const sequence = ++sourceRequestSequence;
        const generation = accountGeneration;
        const controller = new AbortController();
        sourceController?.abort();
        sourceController = controller;
        sourceLoading = true;
        sourceFailure = null;

        void fetchPacAllocationSource(requestedDate, generation, {
            selectedCashBrokerIds: requestedCashBrokerIds,
            signal: controller.signal,
        })
            .then((response) => {
                if (sequence !== sourceRequestSequence || requestedDate !== draft.as_of_date || requestedCashSelectionKey !== cashSelectionKey(draft.cash.mode === 'broker_copy' ? draft.cash.selectedBrokerIds : []) || generation !== accountGeneration) return;
                markChangedSourceRowsStale(response);
                allocationSource = response;
                allocationSourceCashSelectionKey = requestedCashSelectionKey;
                draft.cash.sources = response.cashSources;
                if (draft.cash.mode === 'broker_copy' && applyBrokerCashSource(response, requestedCashBrokerIds)) markRevised();
            })
            .catch((caught) => {
                if (sequence !== sourceRequestSequence || requestedDate !== draft.as_of_date || generation !== accountGeneration) return;
                const failure = toolViewError(caught);
                if (failure.code === 'waiting_stopped' || failure.code === 'session_changed') return;
                sourceFailure = failure;
            })
            .finally(() => {
                if (sequence === sourceRequestSequence) {
                    sourceLoading = false;
                    if (sourceController === controller) sourceController = null;
                }
            });

        return () => controller.abort();
    });

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

    function cancelFxCopy(): void {
        fxCopySequence += 1;
        fxCopyingCurrency = null;
    }

    function setReportCurrency(value: string): void {
        if (value === draft.report_currency) return;
        cancelFxCopy();
        draft.report_currency = value;
        markRevised();
    }

    function setAsOfDate(value: string): void {
        if (value === draft.as_of_date) return;
        cancelFxCopy();
        draft.as_of_date = value;
        for (const row of draft.rows) {
            if (row.source) row.stale = row.source.sourceAsOfDate !== value;
        }
        if (draft.cash.mode === 'broker_copy') draft.cash.stale = true;
        markRevised();
    }

    function refreshAllocationSource(): void {
        if (draft.cash.mode === 'broker_copy') draft.cash.stale = true;
        sourceRefreshToken += 1;
    }

    function addManualRow(): void {
        if (draft.rows.length >= MAX_ROWS) {
            notify({name: 'tool.pac-row-limit', toast: {variant: 'warning', message: $t('tools.pacAllocator.rowLimit')}});
            return;
        }
        draft.rows.push(createManualRow());
        markRevised();
    }

    function addOwnedAsset(asset: PacAssetChoice): void {
        if (!allocationSource || !sourceIsCurrent) return;
        const sourceContexts: readonly (PacAllocationSourceContext | null)[] = asset.contexts.length > 0 ? asset.contexts : [null];
        if (draft.rows.length + sourceContexts.length > MAX_ROWS) {
            notify({
                name: 'tool.pac-source-row-limit',
                detail: {assetId: asset.assetId, requested: sourceContexts.length, available: MAX_ROWS - draft.rows.length},
                toast: {variant: 'warning', message: $t('tools.pacAllocator.atomicRowLimit')},
            });
            return;
        }
        const rows = sourceContexts.map((context): PacEditorRow => {
            const value = sourceRowValue(asset, context);
            return {
                origin: context ? 'portfolio_context' : 'catalog_candidate',
                value,
                source: sourceMetadata(asset, context, allocationSource!.asOfDate),
                importedValue: cloneRowValue(value),
                stale: false,
            };
        });
        draft.rows.push(...rows);
        markRevised();
    }

    function removeOwnedAsset(assetId: number): void {
        draft.rows = draft.rows.filter((row) => row.source?.assetId !== assetId);
        markRevised();
    }

    function toggleOwnedAsset(asset: PacAssetChoice): void {
        if (!asset.selected) {
            addOwnedAsset(asset);
            return;
        }
        const linkedRows = draft.rows.filter((row) => row.source?.assetId === asset.assetId);
        const modifiedRows = linkedRows.filter(rowIsModified);
        if (modifiedRows.length > 0) {
            pendingConfirmation = {
                kind: 'deselect',
                assetId: asset.assetId,
                items: modifiedRows.map((row) => `${row.value.name || row.value.instrument_key} · ${row.source?.brokerName ?? row.source?.usageScope ?? row.value.row_key}`),
            };
            return;
        }
        removeOwnedAsset(asset.assetId);
    }

    function duplicateRow(index: number): void {
        if (draft.rows.length >= MAX_ROWS) {
            notify({name: 'tool.pac-row-limit', toast: {variant: 'warning', message: $t('tools.pacAllocator.rowLimit')}});
            return;
        }
        const sourceRow = draft.rows[index];
        if (!sourceRow) return;
        const value = cloneRowValue(sourceRow.value);
        value.row_key = nextRowKey('duplicate-row');
        draft.rows.splice(index + 1, 0, {
            origin: 'manual_duplicate',
            value,
            source: null,
            importedValue: null,
            stale: false,
        });
        markRevised();
    }

    function removeRow(index: number): void {
        draft.rows.splice(index, 1);
        markRevised();
    }

    function requestRowRemoval(index: number): void {
        const row = draft.rows[index];
        if (!row) return;
        if (row.source && rowIsModified(row)) {
            pendingConfirmation = {
                kind: 'remove-row',
                index,
                items: [`${row.value.name || row.value.instrument_key} · ${row.source.brokerName ?? row.source.usageScope}`],
            };
            return;
        }
        removeRow(index);
    }

    function findFreshSource(row: PacEditorRow): {asset: PacAllocationSourceAsset; context: PacAllocationSourceContext | null} | null {
        if (!allocationSource || !row.source) return null;
        const asset = allocationSource.assets.find((candidate) => candidate.assetId === row.source?.assetId);
        if (!asset) return null;
        if (row.source.kind === 'catalog_candidate') {
            return asset.contexts.length === 0 ? {asset, context: null} : null;
        }
        const context = asset?.contexts.find((candidate) => candidate.contextKey === row.source?.contextKey);
        return asset && context ? {asset, context} : null;
    }

    function refreshConflictItems(): string[] {
        const items: string[] = [];
        for (const row of draft.rows) {
            if (!row.source || !row.importedValue) continue;
            const fresh = findFreshSource(row);
            if (!fresh || !sourceFieldsDiffer(row.value, row.importedValue)) continue;
            const fields: string[] = [];
            if (row.value.instrument_key !== row.importedValue.instrument_key) fields.push($t('tools.pacAllocator.instrumentId'));
            if (row.value.name !== row.importedValue.name) fields.push($t('common.name'));
            if (row.value.initial_quantity !== row.importedValue.initial_quantity) fields.push($t('tools.pacAllocator.rows.initialQuantity'));
            if (row.value.quote.raw_price !== row.importedValue.quote.raw_price) fields.push($t('tools.pacAllocator.rows.price'));
            if (row.value.quote.currency !== row.importedValue.quote.currency) fields.push($t('common.currency'));
            if (row.value.quote.quote_base_quantity !== row.importedValue.quote.quote_base_quantity) fields.push($t('tools.pacAllocator.rows.quoteBasis'));
            if (row.value.quote.reference_date !== row.importedValue.quote.reference_date) fields.push($t('tools.pacAllocator.rows.quoteDate'));
            items.push(`${row.value.name || row.value.instrument_key} · ${row.source.brokerName ?? row.source.usageScope}: ${fields.join(', ')}`);
        }
        return items;
    }

    function applyCopiedFactRefresh(overwriteConflicts: boolean): void {
        let changed = false;
        for (const row of draft.rows) {
            if (!row.source) continue;
            const fresh = findFreshSource(row);
            if (!fresh) {
                row.stale = true;
                continue;
            }
            const hasConflicts = row.importedValue !== null && sourceFieldsDiffer(row.value, row.importedValue);
            if (hasConflicts && !overwriteConflicts) {
                row.stale = true;
                continue;
            }

            const freshValue = sourceRowValue(fresh.asset, fresh.context, row.value.row_key);
            const editableTarget = row.value.target_percent;
            const editableGrid = {...row.value.buy_grid};
            const baselineTarget = row.importedValue?.target_percent ?? '';
            const baselineGrid = row.importedValue?.buy_grid ?? {mode: 'whole' as const, quantity_step: '1'};
            freshValue.target_percent = editableTarget;
            freshValue.buy_grid = editableGrid;

            row.value.instrument_key = freshValue.instrument_key;
            row.value.name = freshValue.name;
            row.value.initial_quantity = freshValue.initial_quantity;
            row.value.quote = {...freshValue.quote};
            row.source = sourceMetadata(fresh.asset, fresh.context, allocationSource!.asOfDate);
            row.importedValue = cloneRowValue(freshValue);
            row.importedValue.target_percent = baselineTarget;
            row.importedValue.buy_grid = {...baselineGrid};
            row.stale = false;
            changed = true;
        }
        if (changed) markRevised();
    }

    function refreshCopiedFacts(): void {
        if (!sourceIsCurrent) {
            refreshAllocationSource();
            return;
        }
        const conflicts = refreshConflictItems();
        if (conflicts.length > 0) {
            pendingConfirmation = {kind: 'refresh', items: conflicts};
            return;
        }
        applyCopiedFactRefresh(false);
    }

    function confirmPendingAction(): void {
        if (!pendingConfirmation) return;
        if (pendingConfirmation.kind === 'deselect') {
            removeOwnedAsset(pendingConfirmation.assetId);
        } else if (pendingConfirmation.kind === 'remove-row') {
            removeRow(pendingConfirmation.index);
        } else {
            applyCopiedFactRefresh(true);
        }
        pendingConfirmation = null;
    }

    function setCashMode(mode: PacCashSourceState['mode']): void {
        if (mode === draft.cash.mode) return;
        draft.cash.mode = mode;
        if (mode === 'manual' && draft.cash.manualBalances.length === 0) {
            draft.cash.manualBalances.push(createMoney(draft.report_currency));
        }
        if (mode === 'broker_copy') {
            const selectionKey = cashSelectionKey(draft.cash.selectedBrokerIds);
            if (allocationSource && sourceIsCurrent && allocationSourceCashSelectionKey === selectionKey) {
                applyBrokerCashSource(allocationSource, draft.cash.selectedBrokerIds);
            } else {
                draft.cash.stale = true;
            }
        } else {
            draft.cash.stale = false;
        }
        markRevised();
    }

    function handleCashMode(mode: string): void {
        if (mode === 'broker_copy' || mode === 'manual') setCashMode(mode);
    }

    function toggleCashBroker(brokerId: number): void {
        const selected = new Set(draft.cash.selectedBrokerIds);
        if (selected.has(brokerId)) selected.delete(brokerId);
        else selected.add(brokerId);
        draft.cash.selectedBrokerIds = [...selected].sort((left, right) => left - right);
        draft.cash.stale = true;
        markRevised();
    }

    function addMoney(kind: 'cash' | 'contributions'): void {
        if (kind === 'cash') {
            if (draft.cash.manualBalances.length >= MAX_CURRENCIES) return;
            draft.cash.manualBalances.push(createMoney(draft.report_currency));
        } else {
            if (draft.contributions.length >= MAX_CURRENCIES) return;
            draft.contributionMode = 'custom';
            draft.contributions.push(createContribution(draft.report_currency));
        }
        markRevised();
    }

    function removeMoney(kind: 'cash' | 'contributions', index: number): void {
        if (kind === 'cash') draft.cash.manualBalances.splice(index, 1);
        else {
            draft.contributions.splice(index, 1);
            if (draft.contributions.length === 0) draft.contributionMode = 'none';
        }
        markRevised();
    }

    function addValuationRate(currency = ''): void {
        if (draft.valuationRates.length >= MAX_CURRENCIES) return;
        const configured = new Set(draft.valuationRates.map((rate) => rate.currency));
        const suggestedCurrency = currency || foreignCurrencies.find((candidate) => !configured.has(candidate)) || '';
        draft.valuationRates.push(createRate(suggestedCurrency));
        markRevised();
    }

    function removeValuationRate(index: number): void {
        cancelFxCopy();
        draft.valuationRates.splice(index, 1);
        markRevised();
    }

    function setRateCurrency(rate: PacRateInput, value: string): void {
        cancelFxCopy();
        rate.currency = value;
        fxCopyErrors = {};
        markRevised();
    }

    function setRateValue(rate: PacRateInput, value: string): void {
        cancelFxCopy();
        rate.rate_to_report = value;
        fxCopyErrors = {};
        markRevised();
    }

    function setRateDate(rate: PacRateInput, value: string): void {
        cancelFxCopy();
        rate.reference_date = value;
        fxCopyErrors = {};
        markRevised();
    }

    function currencyFlag(code: string): string {
        void $currencyStoreVersion;
        const flag = getCurrencyInfo(code).flag_emoji;
        return flag === '🏳️' ? '' : flag;
    }

    function hasValuationRate(currency: string): boolean {
        const normalized = currency.trim().toUpperCase();
        return draft.valuationRates.some((rate) => rate.currency?.trim().toUpperCase() === normalized);
    }

    async function copyValuationRate(currency: string): Promise<void> {
        const nativeCurrency = currency.trim().toUpperCase();
        const reportCurrency = draft.report_currency.trim().toUpperCase();
        const asOfDate = draft.as_of_date;
        if (!nativeCurrency || !reportCurrency || !asOfDate || nativeCurrency === reportCurrency) return;

        const sequence = ++fxCopySequence;
        const generation = accountGeneration;
        const existing = draft.valuationRates.find((rate) => rate.currency?.trim().toUpperCase() === nativeCurrency);
        const existingValue = existing?.rate_to_report ?? null;
        const existingDate = existing?.reference_date ?? null;
        fxCopyingCurrency = nativeCurrency;
        const nextErrors = {...fxCopyErrors};
        delete nextErrors[nativeCurrency];
        fxCopyErrors = nextErrors;

        try {
            const point = await lookupFxRate(nativeCurrency, reportCurrency, asOfDate);
            if (sequence !== fxCopySequence || generation !== accountGeneration || draft.report_currency.trim().toUpperCase() !== reportCurrency || draft.as_of_date !== asOfDate) {
                return;
            }
            try {
                assertToolAccount(generation);
            } catch {
                return;
            }

            const current = draft.valuationRates.find((rate) => rate.currency?.trim().toUpperCase() === nativeCurrency);
            const fieldUnchanged = existing ? current === existing && current.rate_to_report === existingValue && current.reference_date === existingDate : current === undefined;
            if (!fieldUnchanged) return;

            if (!point || point.rate === null) {
                fxCopyErrors = {...fxCopyErrors, [nativeCurrency]: 'missing'};
                return;
            }

            const target = existing ?? createRate(nativeCurrency);
            target.rate_to_report = formatDecimalForDisplay(String(point.rate), {maxFrac: 12});
            target.reference_date = point.backwardFillInfo?.actualRateDate ?? point.date;
            if (!existing) draft.valuationRates.push(target);
            markRevised();
        } finally {
            if (sequence === fxCopySequence) fxCopyingCurrency = null;
        }
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

    function buildInput(): PacInput {
        return {
            operation: 'analyze',
            report_currency: draft.report_currency,
            as_of_date: draft.as_of_date,
            rows: draft.rows.map((row) => cloneRowValue(row.value)),
            cash_balances: draft.cash.mode === 'broker_copy' ? draft.cash.backendAggregatedBalances.map((money) => ({...money})) : draft.cash.manualBalances.map((money) => ({...money})),
            contributions: draft.contributionMode === 'none' ? [] : draft.contributions.map((money) => ({...money})),
            valuation_rates: draft.valuationRates.map((rate) => ({...rate})),
        };
    }

    async function analyze(): Promise<void> {
        if (busy || cashSourceBlocked || !descriptorIsCurrent()) return;
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
            const reply = await runTool('pac_allocator', '1.0.0', {
                descriptor,
                correlationId: `pac-${sequence}-${draftRevision}`,
                parameters: buildInput(),
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
                    detail: {code: reply.error.code, retryable: reply.error.retryable, issueCount: reply.error.issue_count},
                    toast: {variant: 'error', message: $t('tools.pacAllocator.platformError')},
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

    onDestroy(() => {
        requestSequence += 1;
        sourceRequestSequence += 1;
        fxCopySequence += 1;
        activeController?.abort();
        sourceController?.abort();
        activeController = null;
        sourceController = null;
    });
</script>

<form
    class="min-w-0 space-y-4"
    data-testid="pac-allocator-tool"
    data-busy={busy ? 'true' : 'false'}
    data-cash-source={cashSourceBlocked ? 'pending' : 'ready'}
    data-revision={revision}
    aria-busy={busy}
    onsubmit={(event) => {
        event.preventDefault();
        void analyze();
    }}
>
    <section class="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid="pac-scenario" data-density="compact">
        <div class="flex items-start gap-2">
            <div class="min-w-0 flex-1">
                <h2 class="text-sm font-semibold text-gray-900 dark:text-white">
                    {$t('tools.pacAllocator.valuationSettings', {default: 'Valuation settings'})}
                </h2>
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {$t('tools.pacAllocator.valuationSettingsHint', {
                        default: 'Reporting currency values assets, cash, and contributions. The date is the inclusive cutoff for saved facts.',
                    })}
                </p>
            </div>
            <Tooltip
                text={$t('tools.pacAllocator.valuationSettingsInfo', {
                    default: 'These settings define one comparison unit and fact cutoff. They do not move cash or execute trades.',
                })}
                position="left"
                maxWidth="320px"
            >
                <button type="button" class="inline-flex shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" aria-label={$t('tools.pacAllocator.valuationSettingsInfo', {default: 'Valuation-setting details'})} data-testid="pac-valuation-settings-info">
                    <Info size={16} />
                </button>
            </Tooltip>
        </div>
        <div class="mt-3 grid gap-3 sm:grid-cols-2">
            <label class="field-label">
                <span>{$t('tools.pacAllocator.reportCurrency')}</span>
                <CurrencySearchSelect value={draft.report_currency} compact testId="pac-report-currency" onchange={setReportCurrency} />
            </label>
            <label class="field-label">
                <span>{$t('tools.pacAllocator.asOfDate')}</span>
                <SingleDatePicker value={draft.as_of_date} label="" inputStyle onchange={setAsOfDate} testid="pac-as-of-date" />
            </label>
        </div>
    </section>

    <section class="space-y-3" data-testid="pac-funding">
        <div>
            <h2 class="text-sm font-semibold text-gray-900 dark:text-white">{$t('tools.pacAllocator.fundsTitle', {default: '1. Available funds'})}</h2>
            <p class="mt-0.5 text-xs leading-5 text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.fundsHint', {default: 'Copy native OWNER broker cash or enter exact amounts manually. New contributions remain separate.'})}</p>
        </div>
        <div class="grid gap-4">
            <PacMoneySection
                kind="cash"
                title={$t('tools.pacAllocator.cash.existing')}
                description={$t('tools.pacAllocator.cash.existingHint')}
                mode={draft.cash.mode}
                values={draft.cash.manualBalances}
                cashSources={draft.cash.sources}
                selectedBrokerIds={draft.cash.selectedBrokerIds}
                aggregatedBalances={draft.cash.backendAggregatedBalances}
                {sourceLoading}
                {sourceError}
                sourceStale={draft.cash.stale}
                onmodechange={handleCashMode}
                onadd={() => addMoney('cash')}
                onremove={(index) => removeMoney('cash', index)}
                onchange={markRevised}
                onbrokertoggle={toggleCashBroker}
                onretry={refreshAllocationSource}
            />
            <PacMoneySection
                kind="contributions"
                title={$t('tools.pacAllocator.cash.contributions')}
                description={$t('tools.pacAllocator.cash.contributionsHint')}
                mode={draft.contributionMode}
                values={draft.contributions}
                onadd={() => addMoney('contributions')}
                onremove={(index) => removeMoney('contributions', index)}
                onchange={markRevised}
            />
        </div>
    </section>

    <section class="space-y-3 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-density="compact">
        <OwnedAssetGallery assets={assetChoices} loading={sourceLoading} error={sourceError} disabled={!sourceIsCurrent || sourceLoading} ontoggle={toggleOwnedAsset} onretry={refreshAllocationSource} onaddmanual={addManualRow} />

        {#if staleSourceRows.length > 0}
            <div class="flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-amber-900/60 dark:bg-amber-950/20" data-testid="pac-stale-source">
                <div class="flex items-start gap-2 text-sm text-amber-900 dark:text-amber-200">
                    <AlertTriangle class="mt-0.5 shrink-0" size={16} />
                    <span>{$t('tools.pacAllocator.staleSourceHint', {values: {count: staleSourceRows.length}})}</span>
                </div>
                <button
                    class="inline-flex min-h-10 shrink-0 items-center justify-center gap-1.5 rounded-md border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-medium text-amber-900 transition hover:bg-amber-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-600/70 disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-8 dark:border-amber-800 dark:bg-gray-900 dark:text-amber-200 dark:hover:bg-amber-950/40"
                    type="button"
                    onclick={refreshCopiedFacts}
                    disabled={sourceLoading || !sourceIsCurrent}
                    data-testid="pac-refresh-copied-facts"
                >
                    <RefreshCw class={sourceLoading ? 'animate-spin' : ''} size={15} />
                    <span>{$t('tools.pacAllocator.refreshCopiedFacts')}</span>
                </button>
            </div>
        {/if}

        <div class="border-t border-gray-200 pt-4 dark:border-gray-700" data-testid="pac-rows">
            <div class="flex items-end justify-between gap-3">
                <div>
                    <h3 class="text-sm font-semibold text-gray-900 dark:text-white">{$t('tools.pacAllocator.selectedContexts')}</h3>
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.selectedContextsHint')}</p>
                </div>
                <div class="flex flex-col items-end gap-1">
                    <div class="flex items-center gap-1.5">
                        <span class="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-200" data-testid="pac-selected-context-count">
                            {$t('tools.pacAllocator.selectedContextCount', {
                                default: `${draft.rows.length} ${draft.rows.length === 1 ? 'context selected' : 'contexts selected'}`,
                                values: {count: draft.rows.length},
                            })}
                        </span>
                        <Tooltip
                            text={$t('tools.pacAllocator.rowLimitHint', {
                                default: `Maximum ${MAX_ROWS} contexts. Adding an Asset with multiple custody contexts is always all-or-nothing.`,
                                values: {count: MAX_ROWS},
                            })}
                            position="top"
                            maxWidth="300px"
                        >
                            <button type="button" class="inline-flex text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" aria-label={$t('tools.pacAllocator.rowLimitHint', {default: `Maximum ${MAX_ROWS} contexts`})} data-testid="pac-row-limit-info">
                                <Info size={14} />
                            </button>
                        </Tooltip>
                    </div>
                    {#if draft.rows.length >= 28}
                        <span class="inline-flex items-center gap-1 text-[11px] font-medium text-amber-700 dark:text-amber-300" data-testid="pac-row-limit-warning">
                            <AlertTriangle size={12} />
                            {$t('tools.pacAllocator.rowLimitWarning', {
                                default: `${MAX_ROWS - draft.rows.length} slots remaining`,
                                values: {count: MAX_ROWS - draft.rows.length},
                            })}
                        </span>
                    {/if}
                </div>
            </div>

            {#if draft.rows.length === 0}
                <div class="mt-3 rounded-xl border border-dashed border-gray-300 px-4 py-8 text-center dark:border-gray-700" data-testid="pac-no-rows">
                    <p class="text-sm font-medium text-gray-700 dark:text-gray-200">{$t('tools.pacAllocator.rows.empty')}</p>
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.emptyRowsHint')}</p>
                </div>
            {:else}
                <div class="mt-3 space-y-3">
                    {#each draft.rows as row, index (row.value.row_key)}
                        <PacContextEditor bind:row={draft.rows[index]} {index} onduplicate={() => duplicateRow(index)} onremove={() => requestRowRemoval(index)} onchange={markRevised} />
                    {/each}
                </div>
            {/if}
        </div>
    </section>

    {#if fxSectionVisible}
        <section class="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid="pac-valuation-rates" data-density="compact">
            <div class="flex items-start gap-2">
                <div class="min-w-0 flex-1">
                    <h2 class="text-sm font-semibold text-gray-900 dark:text-white">
                        {$t('tools.pacAllocator.rates.titleNumbered', {default: '3. Valuation exchange rates'})}
                    </h2>
                    <p class="mt-0.5 text-xs leading-5 text-gray-500 dark:text-gray-400">
                        {$t('tools.pacAllocator.rates.description', {
                            default: 'Compare values in the reporting currency. No cash is exchanged, transferred, or merged.',
                        })}
                    </p>
                </div>
                <Tooltip
                    text={$t('tools.pacAllocator.rates.equationHint', {
                        default: 'Example: 1 USD = 0.90 EUR means one USD is worth 0.90 EUR only for this report.',
                    })}
                    position="left"
                    maxWidth="320px"
                >
                    <button type="button" class="mt-0.5 inline-flex shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" aria-label={$t('tools.pacAllocator.rates.equationHint', {default: 'Valuation-rate details'})} data-testid="pac-rate-info">
                        <Info size={16} />
                    </button>
                </Tooltip>
            </div>

            {#if foreignCurrencyReasons.length > 0}
                <div class="mt-3 space-y-2" data-testid="pac-fx-reasons">
                    {#each foreignCurrencyReasons as reason (reason.currency)}
                        <div class="rounded-lg border border-blue-200 bg-blue-50/70 p-2.5 text-xs text-blue-950 dark:border-blue-900/60 dark:bg-blue-950/20 dark:text-blue-100" data-testid={`pac-fx-reason-${reason.currency}`}>
                            <div class="flex flex-wrap items-start justify-between gap-2">
                                <div class="min-w-0 flex-1 space-y-1">
                                    <p class="font-medium">
                                        {#if currencyFlag(reason.currency)}<span class="emoji-flag" aria-hidden="true">{currencyFlag(reason.currency)}</span>{/if}
                                        {$t('tools.pacAllocator.rates.reason', {
                                            default: `${reason.currency} facts must be valued in ${draft.report_currency}.`,
                                            values: {currency: reason.currency, reportCurrency: draft.report_currency},
                                        })}
                                    </p>
                                    {#if reason.assetNames.length > 0}
                                        <p data-testid={`pac-fx-reason-assets-${reason.currency}`}>
                                            {$t('tools.pacAllocator.rates.reasonAssets', {
                                                default: `Asset prices: ${reason.assetNames.join(', ')}`,
                                                values: {assets: reason.assetNames.join(', ')},
                                            })}
                                        </p>
                                    {/if}
                                    {#if reason.existingCash}
                                        <p data-testid={`pac-fx-reason-cash-${reason.currency}`}>{$t('tools.pacAllocator.rates.reasonCash', {default: 'Selected existing cash uses this currency.'})}</p>
                                    {/if}
                                    {#if reason.contribution}
                                        <p data-testid={`pac-fx-reason-contribution-${reason.currency}`}>{$t('tools.pacAllocator.rates.reasonContribution', {default: 'A new contribution uses this currency.'})}</p>
                                    {/if}
                                </div>
                                <div class="flex shrink-0 flex-wrap gap-1.5">
                                    <button
                                        class="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-md border border-blue-300 bg-white px-2.5 py-1.5 text-xs font-medium text-blue-800 transition hover:bg-blue-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/70 disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-8 dark:border-blue-800 dark:bg-gray-900 dark:text-blue-200 dark:hover:bg-blue-950/50"
                                        type="button"
                                        disabled={fxCopyingCurrency !== null}
                                        onclick={() => void copyValuationRate(reason.currency)}
                                        data-testid={`pac-copy-rate-${reason.currency}`}
                                    >
                                        {#if fxCopyingCurrency === reason.currency}
                                            <LoaderCircle class="animate-spin" size={14} />
                                        {:else}
                                            <CloudDownload size={14} />
                                        {/if}
                                        {$t('tools.pacAllocator.rates.copySaved', {default: 'Copy saved rate'})}
                                    </button>
                                    {#if !hasValuationRate(reason.currency)}
                                        <button
                                            class="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70 disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-8 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
                                            type="button"
                                            onclick={() => addValuationRate(reason.currency)}
                                            disabled={draft.valuationRates.length >= MAX_CURRENCIES}
                                            data-testid={`pac-enter-rate-${reason.currency}`}
                                        >
                                            <PencilLine size={14} />
                                            {$t('tools.pacAllocator.rates.enterManually', {default: 'Enter manually'})}
                                        </button>
                                    {/if}
                                </div>
                            </div>
                            {#if fxCopyErrors[reason.currency]}
                                <p class="mt-2 text-red-700 dark:text-red-300" role="alert" data-testid={`pac-copy-rate-error-${reason.currency}`}>
                                    {$t('tools.pacAllocator.rates.copyUnavailable', {
                                        default: `No saved ${reason.currency} to ${draft.report_currency} rate is available for ${draft.as_of_date}.`,
                                        values: {currency: reason.currency, reportCurrency: draft.report_currency, date: draft.as_of_date},
                                    })}
                                </p>
                            {/if}
                        </div>
                    {/each}
                </div>
            {/if}

            {#if draft.valuationRates.length > 0}
                <div class="mt-3 space-y-2 border-t border-gray-200 pt-3 dark:border-gray-700" data-testid="pac-valuation-rate-rows">
                    {#each draft.valuationRates as rate, index}
                        <div class="grid gap-2 rounded-lg border border-gray-200 p-2.5 sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1.6fr)_minmax(0,1.4fr)_auto] sm:items-end dark:border-gray-700" data-testid="pac-rate-row">
                            <label class="field-label">
                                <span>{$t('tools.pacAllocator.rates.nativeCurrency', {default: 'Native currency'})}</span>
                                <div class="flex items-center gap-2">
                                    <span class="text-sm font-semibold text-gray-500 dark:text-gray-400">1</span>
                                    <div class="min-w-0 flex-1">
                                        <CurrencySearchSelect value={rate.currency ?? ''} compact testId={`pac-rate-currency-${index}`} onchange={(value) => setRateCurrency(rate, value)} />
                                    </div>
                                </div>
                            </label>
                            <label class="field-label">
                                <span>{$t('tools.pacAllocator.rates.value')}</span>
                                <div class="flex items-center gap-2">
                                    <span class="text-sm font-semibold text-gray-500 dark:text-gray-400">=</span>
                                    <div class="min-w-0 flex-1">
                                        <ExactDecimalInput
                                            value={rate.rate_to_report ?? ''}
                                            step="0.0001"
                                            maxIntegerDigits={12}
                                            maxFractionDigits={12}
                                            placeholder={$t('tools.pacAllocator.rates.value')}
                                            ariaLabel={$t('tools.pacAllocator.rates.value')}
                                            testid={`pac-rate-value-${index}`}
                                            className="min-h-10 !px-2 !py-1.5 text-sm sm:min-h-9"
                                            onchange={(value) => setRateValue(rate, value)}
                                        />
                                    </div>
                                    <span class="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-gray-600 dark:text-gray-300">
                                        {#if currencyFlag(draft.report_currency)}<span class="emoji-flag" aria-hidden="true">{currencyFlag(draft.report_currency)}</span>{/if}
                                        {draft.report_currency}
                                    </span>
                                </div>
                            </label>
                            <label class="field-label">
                                <span>{$t('tools.pacAllocator.rates.date')}</span>
                                <SingleDatePicker value={rate.reference_date ?? ''} label="" inputStyle clearable onchange={(value) => setRateDate(rate, value)} testid={`pac-rate-date-${index}`} />
                            </label>
                            <Tooltip text={$t('common.remove')} position="top" interactiveChild wrapperClass="self-end">
                                <button
                                    class="inline-flex h-10 w-10 items-center justify-center rounded-md text-red-600 transition hover:bg-red-50 hover:text-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500/70 sm:h-9 sm:w-9 dark:text-red-400 dark:hover:bg-red-950/30 dark:hover:text-red-300"
                                    type="button"
                                    onclick={() => removeValuationRate(index)}
                                    aria-label={$t('common.remove')}
                                    data-testid={`pac-remove-rate-${index}`}
                                >
                                    <Trash2 size={15} />
                                </button>
                            </Tooltip>
                        </div>
                    {/each}
                </div>
            {/if}
            <button
                class="mt-3 inline-flex min-h-10 items-center justify-center gap-1.5 rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70 disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-8 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
                type="button"
                onclick={() => addValuationRate()}
                disabled={draft.valuationRates.length >= MAX_CURRENCIES}
                data-testid="pac-add-rate"
            >
                <Plus size={14} />
                <span>{$t('tools.pacAllocator.rates.add')}</span>
            </button>
        </section>
    {/if}

    <section class="flex flex-col gap-3 rounded-xl border border-gray-200 bg-gray-50 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-gray-700 dark:bg-gray-900/50" data-testid="pac-actions" data-density="compact">
        <div class="text-xs text-gray-600 dark:text-gray-400">
            <p>{$t('tools.pacAllocator.revision')}: <span class="font-mono" data-testid="pac-draft-revision">{revision}</span></p>
            <p>{$t('tools.pacAllocator.noOrders')}</p>
        </div>
        <div class="flex shrink-0 flex-wrap gap-2">
            {#if busy}
                <button
                    type="button"
                    onclick={stopWaiting}
                    class="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-md border border-amber-300 bg-white px-2.5 py-1.5 text-xs font-medium text-amber-800 transition hover:bg-amber-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-600/70 sm:min-h-9 dark:border-amber-800 dark:bg-gray-900 dark:text-amber-200 dark:hover:bg-amber-950/30"
                    data-testid="pac-stop-waiting"
                >
                    <CircleStop size={16} />
                    {$t('tools.pacAllocator.stopWaiting')}
                </button>
            {/if}
            <button
                type="submit"
                disabled={busy || cashSourceBlocked}
                class="inline-flex min-h-10 items-center justify-center gap-1.5 whitespace-nowrap rounded-md border border-libre-green bg-libre-green px-3 py-1.5 text-sm font-semibold text-white transition hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70 disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-9 dark:text-gray-950"
                data-testid="pac-analyze"
            >
                {#if busy}
                    <LoaderCircle size={16} class="animate-spin motion-reduce:animate-none" />
                    {$t('tools.pacAllocator.analyzing', {values: {revision: requestRevision ?? revision}})}
                {:else}
                    {$t('tools.pacAllocator.analyze')}
                {/if}
            </button>
        </div>
    </section>

    {#if busy && requestRevision !== revision}
        <p class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" role="status" data-testid="pac-request-stale">
            {$t('tools.pacAllocator.stale.pending', {values: {requestRevision, draftRevision: revision}})}
        </p>
    {/if}

    {#if ignoredRevision !== null}
        <p class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" role="status" data-testid="pac-response-ignored">
            {$t('tools.pacAllocator.stale.ignored', {values: {revision: ignoredRevision}})}
        </p>
    {/if}

    {#if clientError && clientErrorCopy}
        <section class="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="pac-client-error" data-error-code={clientError.code}>
            <h2 class="font-semibold">{$t('common.error')}</h2>
            <p class="mt-2 text-sm">{$t(clientErrorCopy.key, {default: clientErrorCopy.fallback})}</p>
            <p class="mt-2 text-xs">{$t('tools.pacAllocator.draftPreserved')}</p>
        </section>
    {/if}

    {#if platformFailure}
        <section class="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="pac-platform-error" data-error-code={platformFailure.code}>
            <h2 class="font-semibold">{$t('tools.pacAllocator.platformErrorTitle')}</h2>
            <p class="mt-2 text-sm">{$t('tools.pacAllocator.platformError')}</p>
            <p class="mt-2 break-all font-mono text-xs">{platformFailure.code}</p>
        </section>
    {/if}

    {#if result}
        <div data-result-revision={resultRevision}>
            <PacResultPanel {result} stale={resultIsStale} />
        </div>
    {/if}

    {#if itemMetrics}
        <ToolExecutionMetrics item={itemMetrics} batch={batchMetrics} />
    {/if}
</form>

{#if pendingConfirmation}
    <ConfirmModal
        open
        title={pendingConfirmation.kind === 'refresh' ? $t('tools.pacAllocator.confirmRefreshTitle') : pendingConfirmation.kind === 'remove-row' ? $t('tools.pacAllocator.confirmRemoveRowTitle') : $t('tools.pacAllocator.confirmDeselectTitle')}
        message={pendingConfirmation.kind === 'refresh' ? $t('tools.pacAllocator.confirmRefreshMessage') : pendingConfirmation.kind === 'remove-row' ? $t('tools.pacAllocator.confirmRemoveRowMessage') : $t('tools.pacAllocator.confirmDeselectMessage')}
        description={pendingConfirmation.kind === 'refresh' ? $t('tools.pacAllocator.confirmRefreshDescription') : ''}
        items={pendingConfirmation.items}
        itemsLabel={$t('tools.pacAllocator.modifiedFields')}
        confirmText={pendingConfirmation.kind === 'refresh' ? $t('tools.pacAllocator.overwriteCopiedFacts') : pendingConfirmation.kind === 'remove-row' ? $t('tools.pacAllocator.removeCopiedRow') : $t('tools.pacAllocator.removeCopiedRows')}
        danger={pendingConfirmation.kind !== 'refresh'}
        warning={pendingConfirmation.kind === 'refresh'}
        testId={pendingConfirmation.kind === 'refresh' ? 'pac-confirm-refresh' : 'pac-confirm-deselect'}
        onConfirm={confirmPendingAction}
        onCancel={() => (pendingConfirmation = null)}
    />
{/if}

<style>
    .field-label {
        display: flex;
        min-width: 0;
        flex-direction: column;
        gap: 0.35rem;
        font-size: 0.75rem;
        font-weight: 500;
        color: rgb(75 85 99);
    }

    :global(.dark) .field-label {
        color: rgb(209 213 219);
    }
</style>
