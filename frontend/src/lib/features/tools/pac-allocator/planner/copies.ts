/**
 * Explicit copies from the domain APIs into the draft (B2, B4, Q-C0-6).
 *
 * Each copy is one user action on one immutable source snapshot. A copied
 * fact keeps its value and stamp; a re-copy updates silently only what the
 * user has not changed and lists the rest as conflicts. Nothing here is live,
 * nothing prices an Asset (`/assets/prices/current` is never called).
 */
import {canonicalInput, compareDecimal, decimalSign, fractionToPercent} from './decimal';
import {EXPOSURE_DIMENSIONS, PlannerDraft, nowTimestamp, priceIsCopied, rateIsCopied, sameExposures, samePrice, type CopyKind, type CopyRecord, type CopyRef, type DraftAsset, type DraftBroker, type DraftCash, type DraftExposure, type DraftFx, type DraftPrice, type ExposureDimension} from './draft.svelte';
import type {PlannerSource, SourceAsset, SourceBroker, SourceCurrentWeight, SourceIssue, SourceQuery, SourceSection} from './source';

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

/** The snapshot reads every owned Broker; a Broker copy reports only the issues of the Brokers the user picked. */
function selectedBrokerIssues(source: PlannerSource, brokerIds: readonly number[]): SourceIssue[] {
    const picked = new Set(brokerIds.map(domainBrokerKey));
    return source.issues.filter((issue) => {
        if (!('entity_id' in issue.path)) return true;
        const brokerKey = /(?:^|:)(broker:\d+)(?::|$)/.exec(issue.path.entity_id)?.[1];
        return brokerKey === undefined || picked.has(brokerKey);
    });
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
        name: info.display_name,
        ticker: info.identifier_ticker ?? '',
        assetClass: plannerAssetClass(info.asset_type),
        iconUrl: info.icon_url ?? null,
        active: info.active,
        price: null,
        priceManual: false,
        copiedPrice: null,
        priceStamp: null,
        priceSource: null,
        exposures: [],
        copiedExposures: null,
        exposureStamp: null,
        enteredAt: nowTimestamp(),
    };
}

/** The same identity, read from a snapshot row instead of the Asset API. */
export function draftAssetFromSource(row: SourceAsset): DraftAsset {
    return draftAssetFromInfo({id: row.source_asset_id, display_name: row.name, identifier_ticker: row.ticker, asset_type: row.asset_class, icon_url: row.icon_url, active: row.active});
}

// -- Owned Assets ---------------------------------------------------------------

export interface OwnedAsset {
    asset: SourceAsset;
    /** The Brokers (database ids) where the snapshot sees a position. */
    brokerIds: number[];
}

export interface OwnedAssets {
    rows: OwnedAsset[];
    /** Holdings whose Asset or Broker the snapshot did not resolve: shown, never dropped in silence. */
    unresolved: number;
}

/**
 * The Assets the user holds, joined through the snapshot's own keys: a holding
 * names its Asset and its Broker, the `assets` and `brokers` sections resolve
 * them. No quantity is read.
 */
export function ownedAssets(source: PlannerSource): OwnedAssets {
    const assets = new Map(source.assets.map((row) => [row.asset_id, row]));
    const brokers = new Map(source.brokers.map((row) => [row.broker_id, row.source_broker_id]));
    const byAsset = new Map<string, OwnedAsset>();
    let unresolved = 0;
    for (const holding of source.holdings) {
        const asset = assets.get(holding.asset_id);
        const brokerId = brokers.get(holding.broker_id);
        if (!asset || brokerId === undefined) {
            unresolved += 1;
            continue;
        }
        const entry = byAsset.get(asset.asset_id) ?? {asset, brokerIds: []};
        if (!entry.brokerIds.includes(brokerId)) entry.brokerIds.push(brokerId);
        byAsset.set(asset.asset_id, entry);
    }
    return {rows: [...byAsset.values()].sort((left, right) => left.asset.name.localeCompare(right.asset.name)), unresolved};
}

/** Adds the identity of the picked Assets; one already in the draft stays as it is. */
export function applyOwnedAssets(draft: PlannerDraft, picked: readonly SourceAsset[]): number {
    let added = 0;
    for (const row of picked) {
        if (draft.asset(domainAssetKey(row.source_asset_id))) continue;
        draft.addAsset(draftAssetFromSource(row));
        added += 1;
    }
    return added;
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
        conversionMode: 'manual',
        funding: [],
    };
    draft.data.brokers.push(broker);
    return draft.data.brokers[draft.data.brokers.length - 1];
}

export function applyBrokerCopy(draft: PlannerDraft, source: PlannerSource, copy: CopyRecord, brokerIds: readonly number[]): CopyOutcome {
    const result = outcome('brokers', source, copy);
    result.issues = selectedBrokerIssues(source, brokerIds);
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

/** The whole available amount, canonical («all», zero included), or empty when the balance is negative. */
function wholeAvailable(amount: string): string {
    const canonical = canonicalInput(amount);
    return canonical !== null && decimalSign(canonical) !== -1 ? canonical : '';
}

/** An amount to use equal to the whole available amount means «all»: it follows the source when the balance changes. */
function usesAllAvailable(cash: DraftCash): boolean {
    return cash.selected.trim() !== '' && compareDecimal(cash.selected, cash.available) === 0;
}

/** Every selected Broker × currency becomes a cash row; the amount to use starts from the whole available amount. */
export function applyLiquidityCopy(draft: PlannerDraft, source: PlannerSource, copy: CopyRecord, brokerIds: readonly number[]): CopyOutcome {
    const result = outcome('liquidity', source, copy);
    result.issues = selectedBrokerIssues(source, brokerIds);
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
                selected: wholeAvailable(row.custody_amount),
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
        } else if (existing.selected.trim() === '' || usesAllAvailable(existing)) {
            if (usesAllAvailable(existing)) existing.selected = wholeAvailable(row.custody_amount);
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
        if (asset.priceManual) {
            // The user's price stays; only the value «Auto» would restore moves.
            asset.copiedPrice = clonePrice(incoming);
            asset.priceStamp = incomingStamp;
            asset.priceSource = row.source;
            result.unchanged += 1;
        } else if (asset.price === null) {
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

/** A price never copied and never typed: the automatic read may fill it. A cleared copied price or a manual one is never read. */
export function priceAwaitsRead(asset: DraftAsset): boolean {
    return asset.sourceAssetId !== null && !asset.priceManual && asset.price === null && asset.priceStamp === null;
}

/**
 * R9.1: the price of a LibreFolio Asset is LibreFolio's («Auto», read again before
 * «Calcola») or the user's («Manual», never read again). Manual starts from the price on
 * screen, or from an empty amount in `currency`; Auto puts the copied price back, or
 * leaves the price empty for the next read when LibreFolio had none.
 */
export function setPriceManual(draft: PlannerDraft, assetKey: string, manual: boolean, currency: string): void {
    const asset = draft.asset(assetKey);
    if (!asset || asset.sourceAssetId === null || asset.priceManual === manual) return;
    asset.priceManual = manual;
    if (manual) asset.price = asset.price ? clonePrice(asset.price) : {amount: '', currency, quoteBaseQuantity: '1', referenceDate: draft.data.asOf};
    else asset.price = asset.copiedPrice ? clonePrice(asset.copiedPrice) : null;
}

/** A rate never copied and never typed: the automatic read may fill it (same rule as `priceAwaitsRead`). */
export function rateAwaitsRead(fx: DraftFx): boolean {
    return !fx.manual && fx.rate.trim() === '' && fx.stamp === null;
}

/**
 * R9.4: an FX rate is LibreFolio's («Auto», read again before «Calcola») or the
 * user's («Manual», never read again). Manual starts from the rate on screen;
 * Auto puts the copied rate back, or leaves it empty for the next read.
 */
export function setRateManual(draft: PlannerDraft, pair: string, manual: boolean): void {
    const fx = draft.ensureFx(pair);
    if (fx.manual === manual) return;
    fx.manual = manual;
    if (!manual) fx.rate = fx.copiedRate ?? '';
}

/** A composition never copied and never typed: the automatic read may fill it. An emptied copied one stays empty. */
export function exposuresAwaitRead(asset: DraftAsset): boolean {
    return asset.sourceAssetId !== null && asset.exposures.length === 0 && asset.exposureStamp === null;
}

/**
 * The price read right after an Asset is added from the database (R5.5). It
 * fills only the listed Assets whose price is still empty and was never
 * copied: a value typed while the read was running, an Asset already priced,
 * or a copied price the user cleared is never touched, so this copy has no
 * conflicts.
 */
export function applyAddedAssetPrices(draft: PlannerDraft, source: PlannerSource, copy: CopyRecord, assetIds: readonly number[]): CopyOutcome {
    const result = outcome('prices', source, copy);
    const keys = sourceAssetKeys(source);
    const wanted = new Set(assetIds);
    for (const asset of draft.data.assets) {
        if (asset.sourceAssetId === null || !wanted.has(asset.sourceAssetId) || !priceAwaitsRead(asset)) continue;
        const sourceKey = keys.get(asset.sourceAssetId);
        const row = sourceKey ? source.prices.find((item) => item.asset_id === sourceKey) : undefined;
        if (!row || row.amount === null || row.currency === null || row.quote_base_quantity === null || row.reference_date === null) {
            result.missing.push(asset.name);
            continue;
        }
        const incoming: DraftPrice = {amount: row.amount, currency: row.currency, quoteBaseQuantity: row.quote_base_quantity, referenceDate: row.reference_date};
        asset.price = clonePrice(incoming);
        asset.copiedPrice = clonePrice(incoming);
        asset.priceStamp = stampOf(draft, copy, row.provenance_id);
        asset.priceSource = row.source;
        result.applied += 1;
    }
    pruneCopies(draft);
    return result;
}

// -- Classifications -----------------------------------------------------------

function cloneExposures(draft: PlannerDraft, rows: readonly DraftExposure[]): DraftExposure[] {
    return rows.map((row) => ({...row, key: draft.nextId('exposure')}));
}

/** The complete rows of one Asset: a dimension LibreFolio lacks arrives as a row of nulls. */
function completeClassifications(source: PlannerSource, sourceKey: string | undefined) {
    const rows = sourceKey ? source.classifications.filter((item) => item.asset_id === sourceKey) : [];
    return rows.filter((row) => row.category_id !== null && row.label !== null && row.weight !== null);
}

/**
 * The composition read together with the price of an added Asset (R6.2). Like
 * `applyAddedAssetPrices`, it fills only the listed Assets whose composition
 * is empty and was never copied, so it has no conflicts. A partial one is
 * taken as it is: what LibreFolio lacks counts as uncategorised.
 */
export function applyAddedAssetClassifications(draft: PlannerDraft, source: PlannerSource, copy: CopyRecord, assetIds: readonly number[]): CopyOutcome {
    const result = outcome('classifications', source, copy);
    const keys = sourceAssetKeys(source);
    const wanted = new Set(assetIds);
    for (const asset of draft.data.assets) {
        if (asset.sourceAssetId === null || !wanted.has(asset.sourceAssetId) || !exposuresAwaitRead(asset)) continue;
        const complete = completeClassifications(source, keys.get(asset.sourceAssetId));
        if (complete.length === 0) {
            result.missing.push(asset.name);
            continue;
        }
        const incoming: DraftExposure[] = complete.map((row) => ({
            key: draft.nextId('exposure'),
            dimension: row.dimension,
            categoryId: row.category_id as string,
            label: row.label as string,
            weightPercent: fractionToPercent(row.weight as string) ?? '',
            provenanceId: row.provenance_id,
        }));
        asset.exposures = incoming;
        asset.copiedExposures = cloneExposures(draft, incoming);
        asset.exposureStamp = stampOf(draft, copy, complete[0].provenance_id);
        result.applied += 1;
    }
    pruneCopies(draft);
    return result;
}

/** For each listed Asset (database id), the dimensions LibreFolio holds no classification for. */
export function lackingDimensions(source: PlannerSource, assetIds: readonly number[]): Map<number, ExposureDimension[]> {
    const keys = sourceAssetKeys(source);
    const lacking = new Map<number, ExposureDimension[]>();
    for (const id of assetIds) {
        const complete = completeClassifications(source, keys.get(id));
        lacking.set(
            id,
            EXPOSURE_DIMENSIONS.filter((dimension) => !complete.some((row) => row.dimension === dimension)),
        );
    }
    return lacking;
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

/**
 * The automatic read of the FX step (R9.4). It fills only the listed pairs
 * still waiting for their first rate: a manual pair, or a rate typed or copied
 * while the read was running, is never touched, so this copy has no conflicts.
 */
export function applyAwaitingFxRates(draft: PlannerDraft, source: PlannerSource, copy: CopyRecord, pairs: readonly string[]): CopyOutcome {
    const result = outcome('fx', source, copy);
    for (const pair of pairs) {
        const current = draft.fx(pair);
        if (current && !rateAwaitsRead(current)) continue;
        const row = source.fxQuotes.find((item) => item.pair === pair);
        if (!row || row.rate === null) {
            result.missing.push(pair);
            continue;
        }
        const fx = current ?? draft.ensureFx(pair);
        fx.rate = row.rate;
        fx.copiedRate = row.rate;
        fx.stamp = stampOf(draft, copy, row.provenance_id);
        fx.source = row.source;
        fx.referenceDate = row.reference_date;
        result.applied += 1;
    }
    pruneCopies(draft);
    return result;
}

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

// -- Re-read before «Calcola» ----------------------------------------------------

/** The copied facts the user has not changed: they are read again right before the calculation. */
export interface RefreshPlan {
    assetIds: number[];
    cashBrokerIds: number[];
    fxPairs: string[];
}

export interface RefreshSummary {
    readAt: string;
    /** Facts whose value changed, per kind. */
    prices: number;
    fx: number;
    cash: number;
    unchanged: number;
    /** Labels of facts the source no longer publishes: they keep the copied value. */
    missing: string[];
}

const ascending = (a: number, b: number) => a - b;

/**
 * `null` when nothing copied is left unchanged: the calculation then reads nothing.
 * A LibreFolio Asset still waiting for its first price is read too (R8.3): its price
 * cannot be typed, so the calculation is the last chance to find one.
 */
export function refreshPlan(draft: PlannerDraft): RefreshPlan | null {
    const assetIds = [...new Set(draft.data.assets.flatMap((asset) => (asset.sourceAssetId !== null && (priceIsCopied(asset) || priceAwaitsRead(asset)) ? [asset.sourceAssetId] : [])))].sort(ascending);
    const cashBrokerIds = [
        ...new Set(
            draft.data.cash.flatMap((cash) => {
                const id = cash.origin === 'copied' ? draft.broker(cash.brokerKey)?.sourceBrokerId : null;
                return id === null || id === undefined ? [] : [id];
            }),
        ),
    ].sort(ascending);
    const fxPairs = draft.requiredPairs.filter((pair) => {
        const fx = draft.fx(pair);
        return !fx || rateIsCopied(fx) || rateAwaitsRead(fx);
    });
    if (assetIds.length === 0 && cashBrokerIds.length === 0 && fxPairs.length === 0) return null;
    return {assetIds, cashBrokerIds, fxPairs};
}

/**
 * The plan without the first reads (R9.4): with no owned Broker nothing can be
 * read, and a price or rate never copied must not block the calculation, which
 * then reports it as missing. A copied fact still needs its read.
 */
export function copiedOnly(draft: PlannerDraft, plan: RefreshPlan): RefreshPlan | null {
    const assetIds = plan.assetIds.filter((id) => draft.data.assets.some((asset) => asset.sourceAssetId === id && priceIsCopied(asset)));
    const fxPairs = plan.fxPairs.filter((pair) => {
        const fx = draft.fx(pair);
        return fx !== undefined && rateIsCopied(fx);
    });
    if (assetIds.length === 0 && plan.cashBrokerIds.length === 0 && fxPairs.length === 0) return null;
    return {assetIds, cashBrokerIds: plan.cashBrokerIds, fxPairs};
}

/**
 * One read for every kind. The Portfolio API needs Brokers the user owns: the
 * owned ones plus those the cash came from, so a Broker no longer owned is
 * refused (403) instead of being dropped in silence.
 */
export function refreshQuery(draft: PlannerDraft, plan: RefreshPlan, owners: readonly number[]): SourceQuery {
    const sections: SourceSection[] = [];
    if (plan.assetIds.length > 0) sections.push('assets', 'prices');
    if (plan.cashBrokerIds.length > 0) sections.push('brokers', 'cash_balances');
    if (plan.fxPairs.length > 0) sections.push('fx_quotes');
    return {
        asOf: draft.data.asOf,
        targetCurrency: draft.data.valuationCurrency,
        sections,
        brokerIds: [...new Set([...owners, ...plan.cashBrokerIds])].sort(ascending),
        assetIds: plan.assetIds,
        fxPairs: plan.fxPairs,
    };
}

function sameQuote(left: DraftPrice, right: DraftPrice): boolean {
    return samePrice({...left, referenceDate: ''}, {...right, referenceDate: ''});
}

/**
 * Applies the read to the facts that are still unchanged copies; the check is
 * repeated here so an edit made while the read was running is never overwritten.
 * The amount to use of a cash row is the user's: only «all» (equal to the whole
 * available amount) follows the new balance, any other amount is never touched.
 */
export function refreshCopiedFacts(draft: PlannerDraft, source: PlannerSource, plan: RefreshPlan): RefreshSummary {
    const summary: RefreshSummary = {readAt: source.generatedAt, prices: 0, fx: 0, cash: 0, unchanged: 0, missing: []};
    const records = new Map<CopyKind, CopyRecord>();
    const record = (kind: CopyKind): CopyRecord => {
        let copy = records.get(kind);
        if (!copy) {
            copy = newCopyRecord(draft, kind, source);
            records.set(kind, copy);
        }
        return copy;
    };

    const keys = sourceAssetKeys(source);
    for (const asset of draft.data.assets) {
        if (asset.sourceAssetId === null || !plan.assetIds.includes(asset.sourceAssetId)) continue;
        const awaiting = priceAwaitsRead(asset);
        const previous = asset.copiedPrice;
        if (!awaiting && (!priceIsCopied(asset) || previous === null)) continue;
        const sourceKey = keys.get(asset.sourceAssetId);
        const row = sourceKey ? source.prices.find((item) => item.asset_id === sourceKey) : undefined;
        if (!row || row.amount === null || row.currency === null || row.quote_base_quantity === null || row.reference_date === null) {
            // Still no price for an awaiting Asset: nothing copied stays, the calculation reports it.
            if (!awaiting) summary.missing.push(asset.name);
            continue;
        }
        const incoming: DraftPrice = {amount: row.amount, currency: row.currency, quoteBaseQuantity: row.quote_base_quantity, referenceDate: row.reference_date};
        if (previous !== null && sameQuote(previous, incoming)) summary.unchanged += 1;
        else summary.prices += 1;
        asset.price = clonePrice(incoming);
        asset.copiedPrice = clonePrice(incoming);
        asset.priceStamp = stampOf(draft, record('prices'), row.provenance_id);
        asset.priceSource = row.source;
    }

    for (const pair of plan.fxPairs) {
        const current = draft.fx(pair);
        const awaiting = !current || rateAwaitsRead(current);
        if (!awaiting && (!current || !rateIsCopied(current) || current.copiedRate === null)) continue;
        const row = source.fxQuotes.find((item) => item.pair === pair);
        if (!row || row.rate === null) {
            // Still no rate for an awaiting pair: the calculation reports it.
            if (!awaiting) summary.missing.push(pair);
            continue;
        }
        const fx = current ?? draft.ensureFx(pair);
        if (fx.copiedRate !== null && compareDecimal(fx.copiedRate, row.rate) === 0) summary.unchanged += 1;
        else summary.fx += 1;
        fx.rate = row.rate;
        fx.copiedRate = row.rate;
        fx.stamp = stampOf(draft, record('fx'), row.provenance_id);
        fx.source = row.source;
        fx.referenceDate = row.reference_date;
    }

    const sourceBrokers = new Map(source.brokers.map((row) => [row.broker_id, row.source_broker_id]));
    for (const cash of draft.data.cash) {
        if (cash.origin !== 'copied') continue;
        const broker = draft.broker(cash.brokerKey);
        if (!broker || broker.sourceBrokerId === null || !plan.cashBrokerIds.includes(broker.sourceBrokerId)) continue;
        const row = source.cash.find((item) => sourceBrokers.get(item.broker_id) === broker.sourceBrokerId && item.currency === cash.currency);
        if (!row) {
            summary.missing.push(`${broker.name} · ${cash.currency}`);
            continue;
        }
        const sameShare = cash.ownershipShare !== null && compareDecimal(cash.ownershipShare, row.ownership_share) === 0;
        if (compareDecimal(cash.available, row.custody_amount) === 0 && sameShare) summary.unchanged += 1;
        else summary.cash += 1;
        if (usesAllAvailable(cash)) cash.selected = wholeAvailable(row.custody_amount);
        cash.available = row.custody_amount;
        cash.ownershipShare = row.ownership_share;
        cash.economicAmount = row.economic_amount;
        cash.stamp = stampOf(draft, record('liquidity'), row.provenance_id);
    }

    pruneCopies(draft);
    return summary;
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
}

export interface DistributionProposal {
    status: 'complete' | 'incomplete' | 'no_holdings';
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
            return {assetKey: asset.key, label: asset.name, manual: asset.sourceAssetId === null, weightPercent: asset.sourceAssetId === null ? '0' : null, held: false, valuation: null, referenceDate: null};
        }
        return {
            assetKey: asset.key,
            label: asset.name,
            manual: false,
            weightPercent: row.weight === null ? null : fractionToPercent(row.weight),
            held: row.held,
            valuation: row.valuation_source,
            referenceDate: row.valuation_reference_date,
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
    return {status: distribution.status, quantumPercent: fractionToPercent(distribution.weight_quantum), rows, changes, issues: source.issues};
}

/** Applied only after an explicit "Usa come target" (and a confirmation when targets change). */
export function applyDistribution(draft: PlannerDraft, proposal: DistributionProposal): void {
    if (proposal.status !== 'complete') return;
    for (const row of proposal.rows) draft.data.targets[row.assetKey] = row.weightPercent ?? '0';
}
