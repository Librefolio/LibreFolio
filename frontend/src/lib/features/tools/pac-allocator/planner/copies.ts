/**
 * Explicit copies from the domain APIs into the draft (B2, B4, Q-C0-6).
 *
 * Each copy is one user action on one immutable source snapshot. A copied
 * fact keeps its value and stamp; a re-copy updates silently only what the
 * user has not changed and lists the rest as conflicts. Nothing here is live,
 * nothing prices an Asset (`/assets/prices/current` is never called).
 */
import {canonicalInput, compareDecimal, fractionToPercent} from './decimal';
import {PlannerDraft, nowTimestamp, sameExposures, samePrice, type CopyKind, type CopyRecord, type CopyRef, type DraftAsset, type DraftBroker, type DraftCash, type DraftExposure, type DraftPrice} from './draft.svelte';
import type {PlannerSource, SourceBroker, SourceCurrentWeight, SourceIssue} from './source';

export type CopyConflict =
    | {id: string; kind: 'cash'; cashKey: string; label: string; currency: string; previous: string; previousStamp: CopyRef | null; incoming: string; incomingStamp: CopyRef; ownershipShare: string; economicAmount: string; selected: string}
    | {id: string; kind: 'price'; assetKey: string; label: string; previous: DraftPrice | null; previousStamp: CopyRef | null; current: DraftPrice | null; incoming: DraftPrice; incomingStamp: CopyRef; source: string | null}
    | {id: string; kind: 'exposures'; assetKey: string; label: string; previousStamp: CopyRef | null; incoming: DraftExposure[]; incomingStamp: CopyRef}
    | {id: string; kind: 'fx'; pair: string; label: string; previous: string | null; previousStamp: CopyRef | null; current: string; incoming: string; incomingStamp: CopyRef; source: string | null; referenceDate: string | null};

export interface CopyOutcome {
    kind: CopyKind;
    /** The copy this outcome belongs to; a resolved conflict re-registers it (see `resolveConflicts`). */
    copy: CopyRecord;
    applied: number;
    unchanged: number;
    missing: string[];
    conflicts: CopyConflict[];
    issues: SourceIssue[];
}

function outcome(kind: CopyKind, source: PlannerSource, copy: CopyRecord): CopyOutcome {
    return {kind, copy, applied: 0, unchanged: 0, missing: [], conflicts: [], issues: source.issues};
}

/** A copy record enters the draft only once a fact references it. */
function stampOf(draft: PlannerDraft, copy: CopyRecord, provenanceId: string): CopyRef {
    if (!draft.data.copies[copy.copyId]) draft.data.copies[copy.copyId] = copy;
    return {copyId: copy.copyId, provenanceId};
}

/** Drops copy records no fact references any more (a refreshed stamp replaces the old one). */
export function pruneCopies(draft: PlannerDraft): void {
    const used = new Set<string>();
    const mark = (stamp: CopyRef | null) => {
        if (stamp) used.add(stamp.copyId);
    };
    for (const broker of draft.data.brokers) mark(broker.stamp);
    for (const cash of draft.data.cash) mark(cash.stamp);
    for (const asset of draft.data.assets) {
        mark(asset.priceStamp);
        mark(asset.exposureStamp);
    }
    for (const fx of draft.data.fxRates) mark(fx.stamp);
    for (const id of Object.keys(draft.data.copies)) if (!used.has(id)) delete draft.data.copies[id];
}

export function newCopyRecord(draft: PlannerDraft, kind: CopyKind, source: PlannerSource): CopyRecord {
    return {copyId: draft.nextId('copy'), kind, asOf: source.asOf, capturedAt: source.generatedAt, provenance: source.provenance};
}

export function domainBrokerKey(sourceBrokerId: number): string {
    return `broker:${sourceBrokerId}`;
}

export function domainCashKey(sourceBrokerId: number, currency: string): string {
    return `cash:${domainBrokerKey(sourceBrokerId)}:${currency}`;
}

export function domainAssetKey(sourceAssetId: number): string {
    return `asset:${sourceAssetId}`;
}

/**
 * Domain Asset types are the `AssetType` enum (`ETF`, `REAL_ESTATE`); the planner
 * takes a lowercase code. Same identifier, different spelling: nothing is inferred.
 */
export function plannerAssetClass(raw: string | null | undefined): string {
    return (raw ?? '').trim().toLowerCase();
}

/** Identity of a DB Asset from the Asset API; price and exposures arrive by explicit copy. */
export function draftAssetFromInfo(info: {id: number; display_name: string; identifier_ticker?: string | null; asset_type?: string | null; icon_url?: string | null; active: boolean}): DraftAsset {
    return {
        key: domainAssetKey(info.id),
        origin: 'copied',
        sourceAssetId: info.id,
        manualId: null,
        name: info.display_name,
        ticker: info.identifier_ticker ?? '',
        assetClass: plannerAssetClass(info.asset_type),
        iconUrl: info.icon_url ?? null,
        active: info.active,
        price: null,
        copiedPrice: null,
        priceStamp: null,
        priceSource: null,
        exposures: [],
        copiedExposures: null,
        exposureStamp: null,
        enteredAt: nowTimestamp(),
    };
}

// -- Brokers ----------------------------------------------------------------

function upsertBroker(draft: PlannerDraft, row: SourceBroker, copy: CopyRecord): DraftBroker {
    const key = domainBrokerKey(row.source_broker_id);
    const stamp = stampOf(draft, copy, row.provenance_id);
    const existing = draft.broker(key);
    if (existing) {
        // Identity facts follow the source; modes and funding are the user's configuration.
        existing.name = row.name;
        existing.iconUrl = row.icon_url;
        existing.active = row.active;
        existing.accessRole = row.access_role;
        existing.ownershipShare = row.ownership_share;
        existing.observedCurrencies = [...row.observed_currencies];
        existing.stamp = stamp;
        return existing;
    }
    const broker: DraftBroker = {
        key,
        origin: 'copied',
        sourceBrokerId: row.source_broker_id,
        name: row.name,
        iconUrl: row.icon_url,
        fundingOnly: false,
        active: row.active,
        accessRole: row.access_role,
        ownershipShare: row.ownership_share,
        observedCurrencies: [...row.observed_currencies],
        stamp,
        enteredAt: nowTimestamp(),
        modes: draft.defaultModes(row.observed_currencies),
        funding: [],
    };
    draft.data.brokers.push(broker);
    return draft.data.brokers[draft.data.brokers.length - 1];
}

export function applyBrokerCopy(draft: PlannerDraft, source: PlannerSource, copy: CopyRecord, brokerIds: readonly number[]): CopyOutcome {
    const result = outcome('brokers', source, copy);
    for (const row of source.brokers) {
        if (!brokerIds.includes(row.source_broker_id)) continue;
        const existed = draft.broker(domainBrokerKey(row.source_broker_id)) !== undefined;
        upsertBroker(draft, row, copy);
        if (existed) result.unchanged += 1;
        else result.applied += 1;
    }
    draft.syncRoutes();
    pruneCopies(draft);
    return result;
}

// -- Liquidity (B2) -----------------------------------------------------------

/** Every selected Broker × currency becomes a cash row; `selected` always starts empty. */
export function applyLiquidityCopy(draft: PlannerDraft, source: PlannerSource, copy: CopyRecord, brokerIds: readonly number[]): CopyOutcome {
    const result = outcome('liquidity', source, copy);
    const byKey = new Map(source.brokers.map((row) => [row.broker_id, row]));
    for (const row of source.brokers) if (brokerIds.includes(row.source_broker_id)) upsertBroker(draft, row, copy);
    for (const row of source.cash) {
        const broker = byKey.get(row.broker_id);
        if (!broker || !brokerIds.includes(broker.source_broker_id)) continue;
        const key = domainCashKey(broker.source_broker_id, row.currency);
        const incomingStamp = stampOf(draft, copy, row.provenance_id);
        const existing = draft.cashRow(key);
        if (!existing) {
            const cash: DraftCash = {
                key,
                origin: 'copied',
                brokerKey: domainBrokerKey(broker.source_broker_id),
                currency: row.currency,
                available: row.custody_amount,
                ownershipShare: row.ownership_share,
                economicAmount: row.economic_amount,
                stamp: incomingStamp,
                selected: '',
                enteredAt: nowTimestamp(),
            };
            draft.data.cash.push(cash);
            result.applied += 1;
            continue;
        }
        if (compareDecimal(existing.available, row.custody_amount) === 0) {
            existing.stamp = incomingStamp;
            existing.ownershipShare = row.ownership_share;
            existing.economicAmount = row.economic_amount;
            result.unchanged += 1;
        } else if (existing.selected.trim() === '') {
            existing.available = row.custody_amount;
            existing.stamp = incomingStamp;
            existing.ownershipShare = row.ownership_share;
            existing.economicAmount = row.economic_amount;
            result.applied += 1;
        } else {
            result.conflicts.push({
                id: `cash|${key}`,
                kind: 'cash',
                cashKey: key,
                label: broker.name,
                currency: row.currency,
                previous: existing.available,
                previousStamp: existing.stamp,
                incoming: row.custody_amount,
                incomingStamp,
                ownershipShare: row.ownership_share,
                economicAmount: row.economic_amount,
                selected: existing.selected,
            });
        }
    }
    draft.syncRoutes();
    pruneCopies(draft);
    return result;
}

// -- Prices ---------------------------------------------------------------------

function sourceAssetKeys(source: PlannerSource): Map<number, string> {
    return new Map(source.assets.map((row) => [row.source_asset_id, row.asset_id]));
}

function clonePrice(price: DraftPrice): DraftPrice {
    return {...price};
}

export function applyPriceCopy(draft: PlannerDraft, source: PlannerSource, copy: CopyRecord): CopyOutcome {
    const result = outcome('prices', source, copy);
    const keys = sourceAssetKeys(source);
    for (const asset of draft.data.assets) {
        if (asset.sourceAssetId === null) continue;
        const sourceKey = keys.get(asset.sourceAssetId);
        const row = sourceKey ? source.prices.find((item) => item.asset_id === sourceKey) : undefined;
        if (!row || row.amount === null || row.currency === null || row.quote_base_quantity === null || row.reference_date === null) {
            result.missing.push(asset.name);
            continue;
        }
        const incoming: DraftPrice = {amount: row.amount, currency: row.currency, quoteBaseQuantity: row.quote_base_quantity, referenceDate: row.reference_date};
        const incomingStamp = stampOf(draft, copy, row.provenance_id);
        if (asset.price === null) {
            asset.price = clonePrice(incoming);
            asset.copiedPrice = clonePrice(incoming);
            asset.priceStamp = incomingStamp;
            asset.priceSource = row.source;
            result.applied += 1;
        } else if (asset.copiedPrice && samePrice(asset.copiedPrice, incoming)) {
            asset.priceStamp = incomingStamp;
            asset.priceSource = row.source;
            result.unchanged += 1;
        } else if (asset.priceStamp && samePrice(asset.price, asset.copiedPrice)) {
            asset.price = clonePrice(incoming);
            asset.copiedPrice = clonePrice(incoming);
            asset.priceStamp = incomingStamp;
            asset.priceSource = row.source;
            result.applied += 1;
        } else {
            result.conflicts.push({
                id: `price|${asset.key}`,
                kind: 'price',
                assetKey: asset.key,
                label: asset.name,
                previous: asset.copiedPrice,
                previousStamp: asset.priceStamp,
                current: asset.price,
                incoming,
                incomingStamp,
                source: row.source,
            });
        }
    }
    pruneCopies(draft);
    return result;
}

// -- Classifications -----------------------------------------------------------

function cloneExposures(draft: PlannerDraft, rows: readonly DraftExposure[]): DraftExposure[] {
    return rows.map((row) => ({...row, key: draft.nextId('exposure')}));
}

export function applyClassificationCopy(draft: PlannerDraft, source: PlannerSource, copy: CopyRecord): CopyOutcome {
    const result = outcome('classifications', source, copy);
    const keys = sourceAssetKeys(source);
    for (const asset of draft.data.assets) {
        if (asset.sourceAssetId === null) continue;
        const sourceKey = keys.get(asset.sourceAssetId);
        const rows = sourceKey ? source.classifications.filter((item) => item.asset_id === sourceKey) : [];
        const complete = rows.filter((row) => row.category_id !== null && row.label !== null && row.weight !== null);
        if (complete.length < rows.length || rows.length === 0) result.missing.push(asset.name);
        if (complete.length === 0) continue;
        const incoming: DraftExposure[] = complete.map((row) => ({
            key: draft.nextId('exposure'),
            dimension: row.dimension,
            categoryId: row.category_id as string,
            label: row.label as string,
            weightPercent: fractionToPercent(row.weight as string) ?? '',
            provenanceId: row.provenance_id,
        }));
        const incomingStamp = stampOf(draft, copy, complete[0].provenance_id);
        if (asset.exposures.length === 0 && asset.exposureStamp === null) {
            asset.exposures = incoming;
            asset.copiedExposures = cloneExposures(draft, incoming);
            asset.exposureStamp = incomingStamp;
            result.applied += 1;
        } else if (asset.copiedExposures && sameExposures(asset.copiedExposures, incoming)) {
            asset.exposureStamp = incomingStamp;
            result.unchanged += 1;
        } else if (asset.exposureStamp && sameExposures(asset.exposures, asset.copiedExposures)) {
            asset.exposures = incoming;
            asset.copiedExposures = cloneExposures(draft, incoming);
            asset.exposureStamp = incomingStamp;
            result.applied += 1;
        } else {
            result.conflicts.push({id: `exposures|${asset.key}`, kind: 'exposures', assetKey: asset.key, label: asset.name, previousStamp: asset.exposureStamp, incoming, incomingStamp});
        }
    }
    pruneCopies(draft);
    return result;
}

// -- FX --------------------------------------------------------------------------

export function applyFxCopy(draft: PlannerDraft, source: PlannerSource, copy: CopyRecord): CopyOutcome {
    const result = outcome('fx', source, copy);
    for (const row of source.fxQuotes) {
        if (row.rate === null) {
            result.missing.push(row.pair);
            continue;
        }
        const incomingStamp = stampOf(draft, copy, row.provenance_id);
        const fx = draft.ensureFx(row.pair);
        const fresh = () => {
            fx.rate = row.rate as string;
            fx.copiedRate = row.rate;
            fx.stamp = incomingStamp;
            fx.source = row.source;
            fx.referenceDate = row.reference_date;
        };
        if (fx.rate.trim() === '') {
            fresh();
            result.applied += 1;
        } else if (fx.copiedRate !== null && compareDecimal(fx.copiedRate, row.rate) === 0) {
            fx.stamp = incomingStamp;
            fx.source = row.source;
            fx.referenceDate = row.reference_date;
            result.unchanged += 1;
        } else if (fx.copiedRate !== null && fx.stamp && compareDecimal(canonicalInput(fx.rate) ?? fx.rate, fx.copiedRate) === 0) {
            fresh();
            result.applied += 1;
        } else {
            result.conflicts.push({
                id: `fx|${row.pair}`,
                kind: 'fx',
                pair: row.pair,
                label: row.pair,
                previous: fx.copiedRate,
                previousStamp: fx.stamp,
                current: fx.rate,
                incoming: row.rate,
                incomingStamp,
                source: row.source,
                referenceDate: row.reference_date,
            });
        }
    }
    for (const pair of draft.fxPairs) {
        if (!source.fxQuotes.some((row) => row.pair === pair) && !result.missing.includes(pair)) result.missing.push(pair);
    }
    pruneCopies(draft);
    return result;
}

// -- Conflict resolution (B4) -----------------------------------------------------

/**
 * "Aggiorna fatto copiato" moves only the copied baseline and its date; the
 * user's own fields never change. "Mantieni copia precedente" changes nothing.
 *
 * A copy whose every row conflicted was pruned when it was applied (no fact
 * referenced it yet), so an update registers it again before stamping.
 */
export function resolveConflicts(draft: PlannerDraft, copy: CopyRecord, conflicts: readonly CopyConflict[], choice: 'keep' | 'update'): void {
    if (choice === 'update' && conflicts.length > 0) {
        if (!draft.data.copies[copy.copyId]) draft.data.copies[copy.copyId] = copy;
        for (const conflict of conflicts) {
            if (conflict.kind === 'cash') {
                const cash = draft.cashRow(conflict.cashKey);
                if (!cash) continue;
                cash.available = conflict.incoming;
                cash.stamp = conflict.incomingStamp;
                cash.ownershipShare = conflict.ownershipShare;
                cash.economicAmount = conflict.economicAmount;
            } else if (conflict.kind === 'price') {
                const asset = draft.asset(conflict.assetKey);
                if (!asset) continue;
                asset.copiedPrice = clonePrice(conflict.incoming);
                asset.priceStamp = conflict.incomingStamp;
                asset.priceSource = conflict.source;
            } else if (conflict.kind === 'exposures') {
                const asset = draft.asset(conflict.assetKey);
                if (!asset) continue;
                asset.copiedExposures = cloneExposures(draft, conflict.incoming);
                asset.exposureStamp = conflict.incomingStamp;
            } else {
                const fx = draft.fx(conflict.pair);
                if (!fx) continue;
                fx.copiedRate = conflict.incoming;
                fx.stamp = conflict.incomingStamp;
                fx.source = conflict.source;
                fx.referenceDate = conflict.referenceDate;
            }
        }
    }
    pruneCopies(draft);
}

// -- Restore ----------------------------------------------------------------------

export function restoreCopiedPrice(asset: DraftAsset): void {
    if (asset.copiedPrice) asset.price = clonePrice(asset.copiedPrice);
}

export function restoreCopiedExposures(draft: PlannerDraft, asset: DraftAsset): void {
    if (asset.copiedExposures) asset.exposures = cloneExposures(draft, asset.copiedExposures);
}

export function restoreCopiedRate(draft: PlannerDraft, pair: string): void {
    const fx = draft.fx(pair);
    if (fx?.copiedRate) fx.rate = fx.copiedRate;
}

// -- Current distribution (Q-C0-6) ---------------------------------------------

export interface DistributionRow {
    assetKey: string;
    label: string;
    manual: boolean;
    /** Percentage text from the backend weight; `null` = no weight published. */
    weightPercent: string | null;
    held: boolean;
    valuation: SourceCurrentWeight['valuation_source'];
    referenceDate: string | null;
    daysBefore: number | null;
    stale: boolean;
}

export interface DistributionProposal {
    status: 'complete' | 'incomplete' | 'no_holdings';
    asOf: string;
    quantumPercent: string | null;
    rows: DistributionRow[];
    /** Targets that would change, with the value they have now. */
    changes: {assetKey: string; label: string; from: string; to: string}[];
    issues: SourceIssue[];
}

/** Weights come from the portfolio engine; the UI only turns fractions into percentages. */
export function distributionProposal(draft: PlannerDraft, source: PlannerSource): DistributionProposal | null {
    const distribution = source.currentDistribution;
    if (!distribution) return null;
    const keys = sourceAssetKeys(source);
    const rows: DistributionRow[] = draft.data.assets.map((asset) => {
        const sourceKey = asset.sourceAssetId === null ? undefined : keys.get(asset.sourceAssetId);
        const row = sourceKey ? distribution.rows.find((item) => item.asset_id === sourceKey) : undefined;
        if (!row) {
            return {assetKey: asset.key, label: asset.name, manual: asset.sourceAssetId === null, weightPercent: asset.sourceAssetId === null ? '0' : null, held: false, valuation: null, referenceDate: null, daysBefore: null, stale: false};
        }
        return {
            assetKey: asset.key,
            label: asset.name,
            manual: false,
            weightPercent: row.weight === null ? null : fractionToPercent(row.weight),
            held: row.held,
            valuation: row.valuation_source,
            referenceDate: row.valuation_reference_date,
            daysBefore: row.valuation_days_before_requested,
            stale: row.valuation_stale,
        };
    });
    const changes =
        distribution.status === 'complete'
            ? rows.flatMap((row) => {
                  const to = row.weightPercent ?? '0';
                  const current = draft.data.targets[row.assetKey] ?? '';
                  const from = canonicalInput(current);
                  if (from === null || compareDecimal(from, to) === 0) return [];
                  return [{assetKey: row.assetKey, label: row.label, from: current, to}];
              })
            : [];
    return {status: distribution.status, asOf: distribution.as_of, quantumPercent: fractionToPercent(distribution.weight_quantum), rows, changes, issues: source.issues};
}

/** Applied only after an explicit "Usa come target" (and a confirmation when targets change). */
export function applyDistribution(draft: PlannerDraft, proposal: DistributionProposal): void {
    if (proposal.status !== 'complete') return;
    for (const row of proposal.rows) draft.data.targets[row.assetKey] = row.weightPercent ?? '0';
}
