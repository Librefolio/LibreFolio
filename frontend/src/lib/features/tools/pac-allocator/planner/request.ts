/**
 * Draft → PacPlannerRequest (C2) and the local problems that block sending (D8).
 *
 * Local checks are shape and same-unit checks only; every economic rule
 * (reachability, fees, FX closure, minimums, feasibility) stays in the
 * backend. A missing price or rate is not a local problem: the backend
 * answers `needs_input` and names it.
 *
 * The wire is compact (plan-phase00PacContractCompaction §1-§3): a field that
 * holds its schema default is left out, and the codec fills it back in. The
 * builder returns both forms: `request`, the body that is sent, and
 * `resolved`, the codec's parsed output, which the result views read.
 */
import {toolContractMap} from '$lib/api/tool-contract-map.generated';
import {canonicalInput, compareDecimal, decimalSign, isWholeDecimal, percentToFraction} from './decimal';
import {PLANNER_OPERATION} from './defaults';
import {priceIsCopied, routeKey, sameExposures, selectionExceedsAvailable, type CopyRef, type DraftAsset, type DraftBroker, type DraftMode, type DraftRoute, type PlannerDraft} from './draft.svelte';
import {toPlannerId, toPlannerTimestamp} from './source';
import type {
    PacPlannerRequest,
    PacRequestAsset,
    PacRequestBroker,
    PacRequestCapability,
    PacRequestCash,
    PacRequestExposure,
    PacRequestFeeSchedule,
    PacRequestFundingRoute,
    PacRequestOrderRoute,
    PacRequestProvenance,
    PacResolvedRequest,
    PlannerStep,
} from './types';

export interface LocalProblem {
    id: string;
    step: PlannerStep;
    /** Suffix under `tools.pacAllocator.planner.problems.`. */
    key: string;
    fallback: string;
    values: Record<string, string>;
    /** Entity label shown before the message (a name, never an amount). */
    entity: string | null;
}

/** Wire ids → draft entities, used to route backend issues to steps and labels. */
export interface RequestIdMap {
    routes: Map<string, {assetKey: string; brokerKey: string}>;
    funding: Map<string, {brokerKey: string; fundingKey: string}>;
    capabilities: Map<string, {brokerKey: string; modeKey: string}>;
    provenance: Map<string, {step: PlannerStep; entityKey: string}>;
}

export interface BuiltRequest {
    /** The compact body that is sent. */
    request: PacPlannerRequest;
    /** `request` as the codec resolves it, every default filled in: the result views read this one. */
    resolved: PacResolvedRequest;
    ids: RequestIdMap;
    revision: number;
    fingerprint: string;
    counts: {assets: number; operativeBrokers: number; buyRoutes: number; fxPairs: number};
}

export type BuildOutcome = {ok: true; built: BuiltRequest} | {ok: false; problems: LocalProblem[]};

const SAFE_INTEGER = /^(?:0|[1-9][0-9]*)$/;

export function capabilityId(brokerKey: string, mode: DraftMode): string {
    return `${brokerKey}/mode:${mode.currency}`;
}

export function feeScheduleId(brokerKey: string, mode: DraftMode): string {
    return `${brokerKey}/fee:${mode.currency}:buy`;
}

function copyProvenanceId(stamp: CopyRef): string | null {
    return toPlannerId(`${stamp.copyId}/${stamp.provenanceId}`);
}

function manualProvenanceId(entityKey: string, suffix = ''): string | null {
    return toPlannerId(`manual:${entityKey}${suffix}`);
}

function wireDecimal(text: string): string | null {
    return canonicalInput(text);
}

function wireFraction(percentText: string): string | null {
    const canonical = canonicalInput(percentText);
    return canonical === null ? null : percentToFraction(canonical);
}

function wireInteger(text: string): number | null {
    const trimmed = text.trim();
    if (!SAFE_INTEGER.test(trimmed)) return null;
    const value = Number(trimmed);
    return Number.isSafeInteger(value) ? value : null;
}

/**
 * `{[key]: value}`, or nothing when `value` is null. The compact wire leaves a
 * field out when it holds its schema default: the key is absent, never
 * `undefined`, because the tool client refuses an `undefined` value.
 */
function field<K extends string, V>(key: K, value: V | null): Partial<Record<K, V>> {
    return value === null ? {} : ({[key]: value} as Partial<Record<K, V>>);
}

/** `value`, or null when it is zero: the default of every rate and fee. */
function nonZero(value: string): string | null {
    return decimalSign(value) === 0 ? null : value;
}

/** `items`, or null when the list is empty: the default of every list. */
function nonEmpty<T>(items: T[]): T[] | null {
    return items.length > 0 ? items : null;
}

/**
 * The BUY fee schedule of one mode, without its zero fields (§3), or null when
 * every fee is zero: a route with no schedule is a BUY without fees. A
 * rate-only schedule therefore names no currency.
 */
function feeSchedule(brokerKey: string, mode: DraftMode): PacRequestFeeSchedule | null {
    const money = (text: string) => {
        const amount = nonZero(wireDecimal(text) as string);
        return amount === null ? null : {amount, currency: mode.currency};
    };
    const cap = mode.cap.trim() === '' ? null : (wireDecimal(mode.cap) as string);
    const fees = {
        ...field('fixed_fee', money(mode.fixedFee)),
        ...field('rate', nonZero(wireFraction(mode.ratePercent) as string)),
        ...field('variable_floor', money(mode.floor)),
        ...field('variable_cap', cap === null ? null : {kind: 'amount' as const, amount: {amount: cap, currency: mode.currency}}),
    };
    if (Object.keys(fees).length === 0) return null;
    return {fee_schedule_id: feeScheduleId(brokerKey, mode), capability_id: capabilityId(brokerKey, mode), side: 'buy', ...fees};
}

function exposuresUnchanged(asset: DraftAsset): boolean {
    return asset.exposureStamp !== null && sameExposures(asset.exposures, asset.copiedExposures);
}

class ProblemList {
    readonly items: LocalProblem[] = [];

    add(step: PlannerStep, key: string, fallback: string, entity: string | null = null, values: Record<string, string> = {}): void {
        const id = `${step}|${key}|${entity ?? ''}|${JSON.stringify(values)}`;
        if (!this.items.some((item) => item.id === id)) this.items.push({id, step, key, fallback, values, entity});
    }
}

function cashLabel(draft: PlannerDraft, brokerKey: string, currency: string): string {
    return `${draft.broker(brokerKey)?.name ?? brokerKey} · ${currency}`;
}

/** D8: problems that stop the request before it is sent. */
export function localProblems(draft: PlannerDraft): LocalProblem[] {
    const problems = new ProblemList();
    const data = draft.data;
    if (!/^[A-Z]{3}$/.test(data.valuationCurrency)) problems.add('scenario', 'valuationCurrencyMissing', 'The valuation currency is missing.');

    // Liquidity
    if (data.cash.length === 0 && data.contributions.length === 0) problems.add('liquidity', 'noLiquidity', 'Add at least one cash row or contribution.');
    for (const cash of data.cash) {
        const label = cashLabel(draft, cash.brokerKey, cash.currency);
        if (cash.origin === 'manual' && wireDecimal(cash.available) === null) problems.add('liquidity', 'declaredMissing', "'Declared liquidity' is empty or not a number.", label);
        if (cash.selected.trim() === '') problems.add('liquidity', 'selectedMissing', "'Amount to use' is empty.", label);
        else if (wireDecimal(cash.selected) === null) problems.add('liquidity', 'selectedInvalid', "'Amount to use' is not a number.", label);
        else if (selectionExceedsAvailable(cash)) problems.add('liquidity', 'selectedExceedsAvailable', "'Amount to use' exceeds the available amount in the same currency.", label);
    }
    for (const item of data.contributions) {
        const label = item.label.trim() || item.currency;
        if (item.label.trim() === '') problems.add('liquidity', 'contributionLabelMissing', 'The contribution label is empty.', label);
        if (wireDecimal(item.amount) === null) problems.add('liquidity', 'contributionAmountMissing', 'The contribution amount is empty or not a number.', label);
    }

    // Brokers
    if (draft.operativeBrokers.length === 0) problems.add('brokers', 'noOperativeBroker', 'Add at least one Broker on which orders can be proposed.');
    for (const broker of data.brokers) {
        if (broker.name.trim() === '') problems.add('brokers', 'brokerNameMissing', 'The Broker name is empty.', broker.key);
        if (!broker.fundingOnly && broker.modes.length === 0) problems.add('brokers', 'brokerNoMode', 'The Broker has no order mode.', broker.name);
        const currencies = new Set<string>();
        for (const mode of broker.modes) {
            const label = `${broker.name} · ${mode.currency}`;
            if (currencies.has(mode.currency)) problems.add('brokers', 'modeDuplicateCurrency', 'Two order modes use the same currency.', label);
            currencies.add(mode.currency);
            const step = wireDecimal(mode.step);
            if (step === null) problems.add('brokers', 'modeStepMissing', 'The order step is empty or not a number.', label);
            else if (mode.kind === 'whole_quantity' && !isWholeDecimal(step)) problems.add('brokers', 'modeStepNotWhole', 'Whole-unit mode: the step must be a whole number of units.', label);
            for (const [field, value] of [
                ['fixedFee', mode.fixedFee],
                ['ratePercent', mode.ratePercent],
                ['floor', mode.floor],
            ] as const) {
                if (wireDecimal(value) === null) problems.add('brokers', 'feeFieldMissing', 'A fee field is empty or not a number.', label, {field});
            }
            if (mode.cap.trim() !== '' && wireDecimal(mode.cap) === null) problems.add('brokers', 'feeFieldMissing', 'A fee field is empty or not a number.', label, {field: 'cap'});
        }
        for (const funding of broker.funding) {
            if (!funding.enabled) continue;
            if (wireInteger(funding.priority) === null) problems.add('brokers', 'fundingPriorityInvalid', 'Funding priority must be a whole number from 0.', broker.name);
            if (funding.cap.trim() !== '' && wireDecimal(funding.cap) === null) problems.add('brokers', 'fundingCapInvalid', 'The transfer cap is not a number.', broker.name);
            if (draft.sourceCurrency(funding.source) === null) problems.add('brokers', 'fundingSourceMissing', 'A funding route points to a source that no longer exists.', broker.name);
        }
    }

    // Assets
    if (data.assets.length === 0) problems.add('assets', 'noAssets', 'Add at least one Asset.');
    for (const asset of data.assets) {
        if (asset.name.trim() === '') problems.add('assets', 'assetNameMissing', 'The Asset name is empty.', asset.key);
        if (!/^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$/.test(asset.assetClass) || asset.assetClass.length < 3) problems.add('assets', 'assetClassInvalid', 'The Asset class must be a lowercase code of at least 3 characters.', asset.name);
        if (asset.price) {
            if (wireDecimal(asset.price.amount) === null) problems.add('assets', 'priceInvalid', 'The price is empty or not a number.', asset.name);
            if (wireDecimal(asset.price.quoteBaseQuantity) === null) problems.add('assets', 'quoteBasisInvalid', "'Units per price' is empty or not a number.", asset.name);
            if (!/^[A-Z]{3}$/.test(asset.price.currency)) problems.add('assets', 'priceCurrencyMissing', 'The price currency is missing.', asset.name);
        }
        for (const exposure of asset.exposures) {
            if (exposure.categoryId.trim() === '' || exposure.label.trim() === '' || wireFraction(exposure.weightPercent) === null) {
                problems.add('assets', 'exposureIncomplete', 'An exposure row is incomplete.', asset.name);
            } else if (toPlannerId(exposure.categoryId.trim()) === null) {
                problems.add('assets', 'exposureIdTooLong', 'An exposure category identifier is too long.', asset.name);
            }
        }
    }

    // Routing
    const buyRoutes = Object.values(data.routes).filter((route) => route.enabled);
    if (data.assets.length > 0 && draft.operativeBrokers.length > 0 && buyRoutes.length === 0) problems.add('routing', 'noEnabledRoute', 'No order route is enabled.');
    for (const route of buyRoutes) {
        const asset = draft.asset(route.assetKey);
        const broker = draft.broker(route.brokerKey);
        const label = `${asset?.name ?? route.assetKey} · ${broker?.name ?? route.brokerKey}`;
        const mode = draft.modeFor(route.assetKey, route.brokerKey);
        if (!mode && (broker?.modes.length ?? 0) > 0) {
            problems.add('routing', 'routeNoMode', 'This Broker has no order mode in {currency}, the price currency of this Asset: add it, or exclude the Asset on this Broker.', label, {currency: asset?.price?.currency ?? ''});
        }
        if (wireInteger(route.priority) === null) problems.add('routing', 'routePriorityInvalid', 'Route priority must be a whole number from 0.', label);
        if (route.cap.trim() !== '' && wireDecimal(route.cap) === null) problems.add('routing', 'routeCapInvalid', 'The route cap is not a number.', label);
        for (const value of [route.minimumIfActive, route.requiredMinimum]) {
            if (value.trim() !== '' && wireDecimal(value) === null) problems.add('routing', 'routeMinimumInvalid', 'A route minimum is not a number.', label);
        }
        if (wireFraction(route.marginPercent) === null) problems.add('routing', 'routeMarginInvalid', 'The execution margin is empty or not a number.', label);
    }

    // Targets (control percentages, Q-C0-2)
    for (const asset of data.assets) {
        const value = data.targets[asset.key] ?? '';
        if (value.trim() !== '' && (canonicalInput(value) === null || decimalSign(canonicalInput(value) as string) === -1)) problems.add('targets', 'targetInvalid', 'The target is not a number from 0.', asset.name);
    }
    const total = draft.targetTotal;
    if (data.assets.length > 0 && (total === null || compareDecimal(total, '100') !== 0)) {
        problems.add('targets', 'targetTotalNotHundred', 'The target total is {total}%, it must be 100% (control).', null, {total: total ?? '?'});
    }

    // FX: only the pairs the scenario needs are sent; the spread only matters when cash is converted.
    for (const pair of draft.requiredPairs) {
        const fx = draft.fx(pair);
        if (fx && fx.rate.trim() !== '' && wireDecimal(fx.rate) === null) problems.add('fx', 'fxRateInvalid', 'The rate is not a number.', pair);
    }
    if (draft.conversionPairs.length > 0 && wireFraction(data.fxSpreadPercent) === null) problems.add('fx', 'fxSpreadInvalid', 'The conversion spread is empty or not a number.');

    // Strategy
    if (data.policy === '') problems.add('strategy', 'policyMissing', 'Choose a strategy.');
    return problems.items;
}

/**
 * Builds the exact wire request. Returns local problems instead when any
 * shape is wrong, including a structural rejection by the compiled codec.
 */
export function buildRequest(draft: PlannerDraft, now: Date = new Date()): BuildOutcome {
    const problems = localProblems(draft);
    if (problems.length > 0) return {ok: false, problems};
    const data = draft.data;
    const late = new ProblemList();
    const ids: RequestIdMap = {routes: new Map(), funding: new Map(), capabilities: new Map(), provenance: new Map()};
    const provenance = new Map<string, PacRequestProvenance>();
    let newest = now.toISOString();

    const copied = (stamp: CopyRef, step: PlannerStep, entityKey: string): string => {
        const id = copyProvenanceId(stamp);
        const record = draft.copyRecord(stamp);
        const source = record?.provenance.find((item) => item.provenance_id === stamp.provenanceId);
        const capturedAt = source ? toPlannerTimestamp(source.captured_at) : null;
        const sourceRef = source ? toPlannerId(source.source_ref, 256) : null;
        if (!id || !source || !capturedAt || !sourceRef) {
            late.add(step, 'provenanceUnavailable', 'A copied fact lost its source record: copy it again.', entityKey);
            return 'invalid';
        }
        if (!provenance.has(id)) {
            const label = source.source_label?.trim() ? source.source_label.trim().slice(0, 128) : null;
            provenance.set(id, {kind: 'domain_copy', provenance_id: id, domain: source.domain, source_ref: sourceRef, ...field('source_label', label), captured_at: capturedAt});
            ids.provenance.set(id, {step, entityKey});
            if (capturedAt > newest) newest = capturedAt;
        }
        return id;
    };
    const manual = (entityKey: string, suffix: string, label: string, enteredAt: string, step: PlannerStep): string => {
        const id = manualProvenanceId(entityKey, suffix);
        const entered = toPlannerTimestamp(enteredAt) ?? now.toISOString();
        if (!id) {
            late.add(step, 'identifierTooLong', 'An identifier is too long for the planner.', entityKey);
            return 'invalid';
        }
        if (!provenance.has(id)) {
            provenance.set(id, {kind: 'manual', provenance_id: id, label, entered_at: entered});
            ids.provenance.set(id, {step, entityKey});
        }
        return id;
    };

    // Assets. A copied price keeps its date in the draft, where it drives the staleness
    // warnings (plan §5); the wire carries only the price and where it comes from.
    const assets: PacRequestAsset[] = data.assets.map((asset) => {
        const price = asset.price;
        const quote = price
            ? {
                  amount: wireDecimal(price.amount) as string,
                  currency: price.currency,
                  quote_base_quantity: wireDecimal(price.quoteBaseQuantity) as string,
                  provenance_id: priceIsCopied(asset) ? copied(asset.priceStamp as CopyRef, 'assets', asset.key) : manual(asset.key, '/quote', 'manual price', asset.enteredAt, 'assets'),
              }
            : null;
        const exposureProvenance = (provenanceId: string | null): string =>
            exposuresUnchanged(asset) && provenanceId && asset.exposureStamp ? copied({copyId: asset.exposureStamp.copyId, provenanceId}, 'assets', asset.key) : manual(asset.key, '/exposures', 'manual exposures', asset.enteredAt, 'assets');
        const ticker = asset.ticker.trim() === '' ? null : asset.ticker.trim().slice(0, 128);
        const exposures = asset.exposures.map(
            (exposure): PacRequestExposure => ({
                dimension: exposure.dimension,
                category_id: toPlannerId(exposure.categoryId.trim()) as string,
                label: exposure.label.trim().slice(0, 128),
                weight: wireFraction(exposure.weightPercent) as string,
                provenance_id: exposureProvenance(exposure.provenanceId),
            }),
        );
        return {
            asset_id: asset.key,
            identity:
                asset.sourceAssetId !== null ? {kind: 'domain_asset', source_asset_id: String(asset.sourceAssetId), name: asset.name.trim().slice(0, 128), ticker, asset_class: asset.assetClass} : {kind: 'manual_asset', name: asset.name.trim().slice(0, 128), ticker, asset_class: asset.assetClass},
            quote,
            ...field('exposures', nonEmpty(exposures)),
        };
    });

    // Brokers, capabilities, fee schedules. A mode whose fees are all zero sends no schedule.
    const sentSchedules = new Set<string>();
    const brokers: PacRequestBroker[] = data.brokers.map((broker: DraftBroker) => {
        const provenanceId = broker.origin === 'copied' && broker.stamp ? copied(broker.stamp, 'brokers', broker.key) : manual(broker.key, '', 'manual broker', broker.enteredAt, 'brokers');
        const modes = broker.fundingOnly ? [] : broker.modes;
        for (const mode of modes) ids.capabilities.set(capabilityId(broker.key, mode), {brokerKey: broker.key, modeKey: mode.key});
        const capabilities = modes.map(
            (mode): PacRequestCapability =>
                mode.kind === 'whole_quantity'
                    ? {kind: 'whole_quantity', capability_id: capabilityId(broker.key, mode), quantity_unit: 'asset_unit', quantity_step: wireDecimal(mode.step) as string}
                    : {kind: 'monetary_amount', capability_id: capabilityId(broker.key, mode), order_amount_step: {amount: wireDecimal(mode.step) as string, currency: mode.currency}},
        );
        const feeSchedules = modes.map((mode) => feeSchedule(broker.key, mode)).filter((schedule): schedule is PacRequestFeeSchedule => schedule !== null);
        for (const schedule of feeSchedules) sentSchedules.add(schedule.fee_schedule_id);
        return {
            broker_id: broker.key,
            identity: broker.sourceBrokerId !== null ? {kind: 'domain_broker', source_broker_id: String(broker.sourceBrokerId), name: broker.name.trim().slice(0, 128), active: broker.active} : {kind: 'manual_broker', name: broker.name.trim().slice(0, 128)},
            provenance_id: provenanceId,
            conversion_mode: broker.conversionMode,
            ...field('capabilities', nonEmpty(capabilities)),
            ...field('fee_schedules', nonEmpty(feeSchedules)),
        };
    });

    // Cash and contributions
    const existingCash: PacRequestCash[] = data.cash.map((cash) => ({
        cash_id: cash.key,
        broker_id: cash.brokerKey,
        available: {amount: wireDecimal(cash.available) as string, currency: cash.currency},
        selected: {amount: wireDecimal(cash.selected) as string, currency: cash.currency},
        provenance_id: cash.origin === 'copied' && cash.stamp ? copied(cash.stamp, 'liquidity', cash.key) : manual(cash.key, '', 'manual cash', cash.enteredAt, 'liquidity'),
    }));
    const contributions = data.contributions.map((item) => ({
        contribution_id: item.key,
        label: item.label.trim().slice(0, 128),
        amount: {amount: wireDecimal(item.amount) as string, currency: item.currency},
        provenance_id: manual(item.key, '', 'contribution', item.enteredAt, 'liquidity'),
    }));

    // Funding routes: every source is allowed to every operative Broker until the user excludes it (syncFunding).
    // An empty transfer cap is left out: the backend then moves the whole selected amount of the source.
    const fundingRoutes: PacRequestFundingRoute[] = [];
    for (const broker of data.brokers) {
        for (const funding of broker.funding) {
            if (!funding.enabled) continue;
            const currency = draft.sourceCurrency(funding.source) as string;
            const cap = funding.cap.trim() === '' ? null : (wireDecimal(funding.cap) as string);
            const priority = wireInteger(funding.priority) as number;
            const wireId = toPlannerId(`funding:${broker.key}/${funding.key}`) as string;
            ids.funding.set(wireId, {brokerKey: broker.key, fundingKey: funding.key});
            fundingRoutes.push({
                funding_route_id: wireId,
                source: funding.source.kind === 'cash' ? {kind: 'existing_cash', cash_id: funding.source.cashKey} : {kind: 'contribution', contribution_id: funding.source.contributionKey},
                broker_id: broker.key,
                currency,
                ...field('priority', priority === 0 ? null : priority),
                ...field('transfer_cap', cap === null ? null : {amount: cap, currency}),
                provenance_id: manual(funding.key, '', 'funding route', funding.enteredAt, 'brokers'),
            });
        }
    }

    // Order routes (BUY only; a disabled route is simply not sent)
    const orderRoutes: PacRequestOrderRoute[] = [];
    for (const asset of data.assets) {
        for (const broker of draft.operativeBrokers) {
            const route: DraftRoute | undefined = data.routes[routeKey(asset.key, broker.key)];
            if (!route?.enabled) continue;
            const mode = draft.modeFor(asset.key, broker.key) as DraftMode;
            const minimum = (value: string): NonNullable<PacRequestOrderRoute['required_minimum']> | null =>
                value.trim() === ''
                    ? null
                    : mode.kind === 'whole_quantity'
                      ? {kind: 'whole_quantity', quantity: wireDecimal(value) as string, unit: 'asset_unit'}
                      : {kind: 'monetary_amount', amount: {amount: wireDecimal(value) as string, currency: mode.currency}};
            const cap: NonNullable<PacRequestOrderRoute['cap']> | null =
                route.cap.trim() === ''
                    ? null
                    : mode.kind === 'whole_quantity'
                      ? {kind: 'quantity', quantity: wireDecimal(route.cap) as string, unit: 'asset_unit'}
                      : {kind: 'notional', amount: {amount: wireDecimal(route.cap) as string, currency: mode.currency}};
            const priority = wireInteger(route.priority) as number;
            const scheduleId = feeScheduleId(broker.key, mode);
            ids.routes.set(route.wireId, {assetKey: asset.key, brokerKey: broker.key});
            orderRoutes.push({
                route_id: route.wireId,
                asset_id: asset.key,
                broker_id: broker.key,
                capability_id: capabilityId(broker.key, mode),
                side: 'buy',
                ...field('priority', priority === 0 ? null : priority),
                ...field('minimum_if_active', minimum(route.minimumIfActive)),
                ...field('required_minimum', minimum(route.requiredMinimum)),
                ...field('cap', cap),
                ...field('execution_margin_rate', nonZero(wireFraction(route.marginPercent) as string)),
                ...field('fee_schedule_id', sentSchedules.has(scheduleId) ? scheduleId : null),
                provenance_id: manual(route.wireId, '', 'order route', route.enteredAt, 'routing'),
            });
        }
    }

    const fxRates: Record<string, string> = {};
    for (const pair of draft.requiredPairs) {
        const fx = draft.fx(pair);
        const rate = fx ? wireDecimal(fx.rate) : null;
        if (rate !== null) fxRates[pair] = rate;
    }

    if (late.items.length > 0) return {ok: false, problems: late.items};

    const fxSpread = wireFraction(data.fxSpreadPercent) ?? '0';
    const request = {
        operation: PLANNER_OPERATION,
        snapshot: {snapshot_id: `draft:${draft.revision}`, draft_revision: draft.revision, captured_at: newest},
        as_of: data.asOf,
        valuation_currency: data.valuationCurrency,
        provenance: [...provenance.values()],
        ...field('fx_rates', Object.keys(fxRates).length > 0 ? fxRates : null),
        ...field('fx_spread_rate', nonZero(fxSpread)),
        assets,
        brokers,
        ...field('existing_cash', nonEmpty(existingCash)),
        ...field('contributions', nonEmpty(contributions)),
        ...field('funding_routes', nonEmpty(fundingRoutes)),
        target_weights: data.assets.map((asset) => ({asset_id: asset.key, weight: wireFraction(data.targets[asset.key]?.trim() ? data.targets[asset.key] : '0') as string})),
        order_routes: orderRoutes,
        policy: data.policy,
    } as PacPlannerRequest;

    const parsed = toolContractMap.pac_allocator['1.0.0'].input.safeParse(request);
    if (!parsed.success) {
        const structural = new ProblemList();
        for (const issue of parsed.error.issues.slice(0, 20)) {
            structural.add(stepOfWirePath(issue.path), 'structureInvalid', 'A field does not match the planner contract: {path}.', null, {path: issue.path.join('.')});
        }
        return {ok: false, problems: structural.items};
    }
    return {
        ok: true,
        built: {
            request,
            resolved: parsed.data,
            ids,
            revision: draft.revision,
            fingerprint: draft.fingerprint,
            counts: {assets: assets.length, operativeBrokers: draft.operativeBrokers.length, buyRoutes: orderRoutes.length, fxPairs: Object.keys(fxRates).length},
        },
    };
}

/** The first segment of a wire path names the step that owns it. */
export function stepOfWirePath(path: readonly (string | number)[]): PlannerStep {
    switch (path[0]) {
        case 'assets':
            return 'assets';
        case 'brokers':
        case 'funding_routes':
            return 'brokers';
        case 'existing_cash':
        case 'contributions':
            return 'liquidity';
        case 'order_routes':
            return 'routing';
        case 'target_weights':
            return 'targets';
        case 'fx_rates':
        case 'fx_spread_rate':
            return 'fx';
        case 'policy':
            return 'strategy';
        default:
            return 'scenario';
    }
}
