/**
 * The PAC planner draft (C2).
 *
 * One in-memory scenario, edited step by step and never persisted. Every
 * value is decimal text in the unit shown next to its field; the draft
 * validates shapes, never computes an economic result. Copied facts keep the
 * value and the stamp of their copy, so an explicit re-copy can tell "the
 * source changed" from "the user changed it" (B4) instead of overwriting.
 */
import {compareDecimal, sumControlPercentages, remainingControlPercentage, canonicalInput} from './decimal';
import {DEFAULT_EXECUTION_MARGIN_PERCENT, DEFAULT_FEE, DEFAULT_FUNDING_PRIORITY, DEFAULT_FX_SPREAD_PERCENT, DEFAULT_QUANTITY_STEP, DEFAULT_ROUTE_PRIORITY, defaultAsOf} from './defaults';
import {canonicalPair, type ExposureDimension, type SourceProvenance} from './source';
import {PLANNER_STEPS, type PlannerStep} from './types';

export type {ExposureDimension};

export type FactOrigin = 'copied' | 'manual';
export type CopyKind = 'liquidity' | 'brokers' | 'prices' | 'classifications' | 'fx' | 'distribution';
export type ModeKind = 'whole_quantity' | 'monetary_amount';

export const EXPOSURE_DIMENSIONS: readonly ExposureDimension[] = ['asset_type', 'sector', 'geography'];

/** Where a copied fact came from: one copy, one source provenance record. */
export interface CopyRef {
    copyId: string;
    provenanceId: string;
}

export interface CopyRecord {
    copyId: string;
    kind: CopyKind;
    asOf: string;
    capturedAt: string;
    provenance: SourceProvenance[];
}

export interface DraftMode {
    key: string;
    currency: string;
    kind: ModeKind;
    /** Whole quantity: units per step. Monetary amount: amount step in `currency`. */
    step: string;
    fixedFee: string;
    ratePercent: string;
    floor: string;
    /** Empty = no variable cap. */
    cap: string;
}

export type FundingSourceRef = {kind: 'cash'; cashKey: string} | {kind: 'contribution'; contributionKey: string};

export interface DraftFunding {
    key: string;
    wireId: string;
    source: FundingSourceRef;
    enabled: boolean;
    priority: string;
    /** Empty = the whole amount of the source. */
    cap: string;
    enteredAt: string;
}

/** R4.9: who converts currency for this Broker's orders. The calculation is the same; only the plan's presentation changes. */
export type ConversionMode = 'manual' | 'automatic';

export interface DraftBroker {
    key: string;
    origin: FactOrigin;
    sourceBrokerId: number | null;
    name: string;
    iconUrl: string | null;
    fundingOnly: boolean;
    active: boolean;
    accessRole: string | null;
    ownershipShare: string | null;
    observedCurrencies: string[];
    stamp: CopyRef | null;
    enteredAt: string;
    modes: DraftMode[];
    conversionMode: ConversionMode;
    funding: DraftFunding[];
}

export interface DraftCash {
    key: string;
    origin: FactOrigin;
    brokerKey: string;
    currency: string;
    /** Custody amount (copied, read-only) or declared amount (manual); a limit, not a proposal. */
    available: string;
    ownershipShare: string | null;
    economicAmount: string | null;
    stamp: CopyRef | null;
    /** What the user decides to use. Always starts empty. */
    selected: string;
    enteredAt: string;
}

export interface DraftContribution {
    key: string;
    label: string;
    amount: string;
    currency: string;
    enteredAt: string;
}

export interface DraftPrice {
    amount: string;
    currency: string;
    quoteBaseQuantity: string;
    referenceDate: string;
}

export interface DraftExposure {
    key: string;
    dimension: ExposureDimension;
    categoryId: string;
    label: string;
    weightPercent: string;
    /** Source provenance of a copied row; `null` when typed by the user. */
    provenanceId: string | null;
}

export interface DraftAsset {
    key: string;
    origin: FactOrigin;
    sourceAssetId: number | null;
    name: string;
    ticker: string;
    assetClass: string;
    iconUrl: string | null;
    active: boolean;
    price: DraftPrice | null;
    /**
     * A LibreFolio Asset whose price the user took over (R9.1): it is never read again and
     * goes out as a manual price, even when equal to the copy. A manual Asset never sets it.
     */
    priceManual: boolean;
    copiedPrice: DraftPrice | null;
    priceStamp: CopyRef | null;
    priceSource: string | null;
    exposures: DraftExposure[];
    copiedExposures: DraftExposure[] | null;
    exposureStamp: CopyRef | null;
    enteredAt: string;
}

export interface DraftRoute {
    wireId: string;
    assetKey: string;
    brokerKey: string;
    enabled: boolean;
    priority: string;
    /** Empty = no minimum; the unit follows the Broker mode. */
    minimumIfActive: string;
    requiredMinimum: string;
    /** Empty = no cap of its own: the order stays bounded by the money that can reach it. */
    cap: string;
    marginPercent: string;
    enteredAt: string;
}

export interface DraftFx {
    pair: string;
    /** Units of the second currency for one unit of the first. */
    rate: string;
    copiedRate: string | null;
    stamp: CopyRef | null;
    source: string | null;
    referenceDate: string | null;
    /** The user's own rate: used as typed, never read again from LibreFolio. */
    manual: boolean;
    enteredAt: string;
}

/** Why the backend needs a pair: to value the portfolio, to convert cash at a buy, or both. */
export type FxPurpose = 'valuation' | 'conversion' | 'both';

export interface DraftData {
    asOf: string;
    valuationCurrency: string;
    fxSpreadPercent: string;
    policy: string;
    brokers: DraftBroker[];
    cash: DraftCash[];
    contributions: DraftContribution[];
    assets: DraftAsset[];
    routes: Record<string, DraftRoute>;
    targets: Record<string, string>;
    fxRates: DraftFx[];
    copies: Record<string, CopyRecord>;
}

/** A structural consequence listed before a removal is confirmed (A9). */
export interface RemovalImpact {
    routes: DraftRoute[];
    cash: DraftCash[];
    funding: {broker: DraftBroker; funding: DraftFunding}[];
    target: boolean;
}

export function routeKey(assetKey: string, brokerKey: string): string {
    return `${assetKey}|${brokerKey}`;
}

/** One card of the Liquidity step: existing cash or a new contribution. */
export type LiquidityEntry = {kind: 'cash'; key: string; enteredAt: string; cash: DraftCash} | {kind: 'contribution'; key: string; enteredAt: string; contribution: DraftContribution};

export function liquidityEntryKey(kind: LiquidityEntry['kind'], key: string): string {
    return `${kind}|${key}`;
}

export function nowTimestamp(): string {
    return new Date().toISOString();
}

/** Whole days between two ISO dates (`later` − `earlier`); date arithmetic, not money. */
export function daysBetween(earlier: string, later: string): number | null {
    const a = Date.parse(`${earlier}T00:00:00Z`);
    const b = Date.parse(`${later}T00:00:00Z`);
    if (Number.isNaN(a) || Number.isNaN(b)) return null;
    return Math.round((b - a) / 86_400_000);
}

function sameDecimalText(left: string, right: string): boolean {
    const a = canonicalInput(left) ?? left.trim();
    const b = canonicalInput(right) ?? right.trim();
    return a === b || compareDecimal(a, b) === 0;
}

export function samePrice(left: DraftPrice | null, right: DraftPrice | null): boolean {
    if (left === null || right === null) return left === right;
    return left.currency === right.currency && left.referenceDate === right.referenceDate && sameDecimalText(left.amount, right.amount) && sameDecimalText(left.quoteBaseQuantity, right.quoteBaseQuantity);
}

/**
 * A price still equal to its copy: it keeps the source date and is re-read before
 * «Calcola». A typed price, or one switched to manual, is the user's and carries the calculation date.
 */
export function priceIsCopied(asset: DraftAsset): boolean {
    return !asset.priceManual && asset.priceStamp !== null && asset.copiedPrice !== null && samePrice(asset.price, asset.copiedPrice);
}

/** A rate still equal to its copy (same rule as `priceIsCopied`). */
export function rateIsCopied(fx: DraftFx): boolean {
    if (fx.manual || fx.stamp === null || fx.copiedRate === null) return false;
    const current = canonicalInput(fx.rate);
    return current !== null && compareDecimal(current, fx.copiedRate) === 0;
}

function exposureSignature(rows: readonly DraftExposure[]): string {
    return rows
        .map((row) => [row.dimension, row.categoryId, canonicalInput(row.weightPercent) ?? row.weightPercent].join('\u0000'))
        .sort()
        .join('\u0001');
}

export function sameExposures(left: readonly DraftExposure[] | null, right: readonly DraftExposure[] | null): boolean {
    if (left === null || right === null) return left === right;
    return exposureSignature(left) === exposureSignature(right);
}

function emptyData(valuationCurrency: string): DraftData {
    return {
        asOf: defaultAsOf(),
        valuationCurrency,
        fxSpreadPercent: DEFAULT_FX_SPREAD_PERCENT,
        policy: '',
        brokers: [],
        cash: [],
        contributions: [],
        assets: [],
        routes: {},
        targets: {},
        fxRates: [],
        copies: {},
    };
}

export function defaultMode(key: string, currency: string): DraftMode {
    return {
        key,
        currency,
        kind: 'whole_quantity',
        step: DEFAULT_QUANTITY_STEP,
        fixedFee: DEFAULT_FEE.fixed,
        ratePercent: DEFAULT_FEE.ratePercent,
        floor: DEFAULT_FEE.floor,
        cap: DEFAULT_FEE.cap,
    };
}

export class PlannerDraft {
    data = $state<DraftData>(emptyData(''));

    /** Every editable fact; a result computed on another fingerprint is stale. */
    readonly fingerprint = $derived(JSON.stringify(this.data));

    #counter = 0;
    #lastFingerprint = '';
    #revision = 0;

    /** Monotonic: a new number for every distinct draft state observed. */
    readonly revision = $derived.by(() => {
        const current = this.fingerprint;
        if (current !== this.#lastFingerprint) {
            this.#lastFingerprint = current;
            this.#revision += 1;
        }
        return this.#revision;
    });

    /** True once the user has entered anything worth a leave confirmation (A8). */
    readonly dirty = $derived(this.data.brokers.length > 0 || this.data.cash.length > 0 || this.data.contributions.length > 0 || this.data.assets.length > 0 || this.data.fxRates.length > 0 || Object.keys(this.data.targets).length > 0);

    /**
     * The user's order of the Liquidity cards (`liquidityEntryKey`), set by drag and drop.
     * Presentation only, kept outside `data`: reordering changes no fingerprint, so it never makes a result stale.
     */
    liquidityOrder = $state<string[]>([]);

    /** Liquidity cards: the user's order first, then the rest in the order they were added. */
    readonly liquidityEntries = $derived.by((): LiquidityEntry[] => {
        const entries: LiquidityEntry[] = [
            ...this.data.cash.map((cash): LiquidityEntry => ({kind: 'cash', key: liquidityEntryKey('cash', cash.key), enteredAt: cash.enteredAt, cash})),
            ...this.data.contributions.map((contribution): LiquidityEntry => ({kind: 'contribution', key: liquidityEntryKey('contribution', contribution.key), enteredAt: contribution.enteredAt, contribution})),
        ];
        const rank = new Map(this.liquidityOrder.map((key, index) => [key, index]));
        const position = (entry: LiquidityEntry): number => rank.get(entry.key) ?? rank.size;
        return entries.sort((a, b) => position(a) - position(b) || (a.enteredAt < b.enteredAt ? -1 : a.enteredAt > b.enteredAt ? 1 : 0));
    });

    /**
     * The user's order of the Asset cards (Asset keys), set by drag and drop in the Assets step.
     * Presentation only, like `liquidityOrder`: the engine orders Assets by id, so no fingerprint changes.
     */
    assetOrder = $state<string[]>([]);

    /** Assets as the steps list them: the user's order first, then the rest in the order they were added. */
    readonly orderedAssets = $derived.by((): DraftAsset[] => {
        const rank = new Map(this.assetOrder.map((key, index) => [key, index]));
        return this.data.assets
            .map((asset, index) => ({asset, index}))
            .sort((a, b) => (rank.get(a.asset.key) ?? rank.size) - (rank.get(b.asset.key) ?? rank.size) || a.index - b.index)
            .map((entry) => entry.asset);
    });

    constructor(valuationCurrency = '', policy = '') {
        this.data = emptyData(valuationCurrency);
        this.data.policy = policy;
    }

    nextId(prefix: string): string {
        this.#counter += 1;
        return `${prefix}:${this.#counter}`;
    }

    reset(valuationCurrency: string, policy: string): void {
        this.data = emptyData(valuationCurrency);
        this.data.policy = policy;
        this.liquidityOrder = [];
        this.assetOrder = [];
    }

    /** The scenario date is always today: set before every copy read and every calculation. */
    refreshAsOf(now: Date = new Date()): void {
        const today = defaultAsOf(now);
        if (this.data.asOf !== today) this.data.asOf = today;
    }

    // -- lookups -----------------------------------------------------------

    broker(key: string): DraftBroker | undefined {
        return this.data.brokers.find((item) => item.key === key);
    }

    cashRow(key: string): DraftCash | undefined {
        return this.data.cash.find((item) => item.key === key);
    }

    contribution(key: string): DraftContribution | undefined {
        return this.data.contributions.find((item) => item.key === key);
    }

    asset(key: string): DraftAsset | undefined {
        return this.data.assets.find((item) => item.key === key);
    }

    fx(pair: string): DraftFx | undefined {
        return this.data.fxRates.find((item) => item.pair === pair);
    }

    readonly operativeBrokers = $derived(this.data.brokers.filter((item) => !item.fundingOnly));
    readonly fundingOnlyBrokers = $derived(this.data.brokers.filter((item) => item.fundingOnly));

    /** The Broker mode an order route uses: the one in the price currency (N10). */
    modeFor(assetKey: string, brokerKey: string): DraftMode | null {
        const broker = this.broker(brokerKey);
        const asset = this.asset(assetKey);
        if (!broker || broker.fundingOnly || broker.modes.length === 0) return null;
        const currency = asset?.price?.currency;
        if (currency) return broker.modes.find((mode) => mode.currency === currency) ?? null;
        // Without a price the backend answers needs_input; any mode keeps the route well-formed.
        return broker.modes.find((mode) => mode.currency === this.data.valuationCurrency) ?? broker.modes[0] ?? null;
    }

    // -- liquidity ---------------------------------------------------------

    addContribution(currency: string, label: string): DraftContribution {
        const item: DraftContribution = {key: this.nextId('contribution'), label, amount: '', currency, enteredAt: nowTimestamp()};
        this.data.contributions.push(item);
        this.syncFunding();
        return item;
    }

    removeContribution(key: string): void {
        this.data.contributions = this.data.contributions.filter((item) => item.key !== key);
        this.dropFundingFrom({kind: 'contribution', contributionKey: key});
        this.forgetLiquidityEntry(liquidityEntryKey('contribution', key));
    }

    /** B3: a manual account is manual cash on a manual, funding-only Broker. */
    addManualAccount(input: {name: string; currency: string; available: string; selected: string}): DraftCash {
        const enteredAt = nowTimestamp();
        const broker: DraftBroker = {
            key: this.nextId('manual-broker'),
            origin: 'manual',
            sourceBrokerId: null,
            name: input.name,
            iconUrl: null,
            fundingOnly: true,
            active: true,
            accessRole: null,
            ownershipShare: null,
            observedCurrencies: [input.currency],
            stamp: null,
            enteredAt,
            modes: [],
            conversionMode: 'manual',
            funding: [],
        };
        const cash: DraftCash = {
            key: this.nextId('manual-cash'),
            origin: 'manual',
            brokerKey: broker.key,
            currency: input.currency,
            available: input.available,
            ownershipShare: null,
            economicAmount: null,
            stamp: null,
            selected: input.selected,
            enteredAt,
        };
        this.data.brokers.push(broker);
        this.data.cash.push(cash);
        this.syncFunding();
        return cash;
    }

    removeCash(key: string): void {
        this.data.cash = this.data.cash.filter((item) => item.key !== key);
        this.dropFundingFrom({kind: 'cash', cashKey: key});
        this.forgetLiquidityEntry(liquidityEntryKey('cash', key));
    }

    reorderLiquidity(keys: readonly string[]): void {
        this.liquidityOrder = [...keys];
    }

    /** A removed card loses its place: added again, it goes to the end like any new one. */
    private forgetLiquidityEntry(entryKey: string): void {
        if (this.liquidityOrder.includes(entryKey)) this.liquidityOrder = this.liquidityOrder.filter((key) => key !== entryKey);
    }

    private dropFundingFrom(source: FundingSourceRef): void {
        for (const broker of this.data.brokers) {
            broker.funding = broker.funding.filter((item) => !sameSource(item.source, source));
        }
    }

    /** Funding sources that need a route to reach `brokerKey`: its own cash is already local. */
    fundingCandidates(brokerKey: string): FundingSourceRef[] {
        const cash = this.data.cash.filter((item) => item.brokerKey !== brokerKey).map((item) => ({kind: 'cash', cashKey: item.key}) as const);
        const contributions = this.data.contributions.map((item) => ({kind: 'contribution', contributionKey: item.key}) as const);
        return [...cash, ...contributions];
    }

    fundingFor(broker: DraftBroker, source: FundingSourceRef): DraftFunding | undefined {
        return broker.funding.find((item) => sameSource(item.source, source));
    }

    /**
     * Every operative Broker may use every liquidity source unless the user says otherwise: a source
     * without an entry gets one, enabled. An entry the user switched off stays off.
     */
    syncFunding(): void {
        for (const broker of this.data.brokers) {
            if (broker.fundingOnly) continue;
            for (const source of this.fundingCandidates(broker.key)) {
                if (!this.fundingFor(broker, source)) broker.funding.push({...this.newFunding(source), enabled: true});
            }
        }
    }

    newFunding(source: FundingSourceRef): DraftFunding {
        return {key: this.nextId('funding'), wireId: '', source, enabled: false, priority: DEFAULT_FUNDING_PRIORITY, cap: '', enteredAt: nowTimestamp()};
    }

    sourceCurrency(source: FundingSourceRef): string | null {
        if (source.kind === 'cash') return this.cashRow(source.cashKey)?.currency ?? null;
        return this.contribution(source.contributionKey)?.currency ?? null;
    }

    // -- brokers -----------------------------------------------------------

    defaultModes(currencies: readonly string[]): DraftMode[] {
        const list = currencies.length > 0 ? [...new Set(currencies)].sort() : [this.data.valuationCurrency].filter(Boolean);
        return list.map((currency) => defaultMode(this.nextId('mode'), currency));
    }

    addManualBroker(name: string): DraftBroker {
        const broker: DraftBroker = {
            key: this.nextId('manual-broker'),
            origin: 'manual',
            sourceBrokerId: null,
            name,
            iconUrl: null,
            fundingOnly: false,
            active: true,
            accessRole: null,
            ownershipShare: null,
            observedCurrencies: [],
            stamp: null,
            enteredAt: nowTimestamp(),
            modes: this.defaultModes([]),
            conversionMode: 'manual',
            funding: [],
        };
        this.data.brokers.push(broker);
        this.syncRoutes();
        return broker;
    }

    replaceBroker(next: DraftBroker): void {
        const index = this.data.brokers.findIndex((item) => item.key === next.key);
        if (index < 0) return;
        this.data.brokers[index] = next;
        this.syncRoutes();
    }

    brokerRemovalImpact(key: string): RemovalImpact {
        const cash = this.data.cash.filter((item) => item.brokerKey === key);
        const cashKeys = new Set(cash.map((item) => item.key));
        const funding = this.data.brokers.flatMap((broker) => (broker.key === key ? [] : broker.funding.filter((item) => item.source.kind === 'cash' && cashKeys.has(item.source.cashKey)).map((item) => ({broker, funding: item}))));
        return {routes: Object.values(this.data.routes).filter((route) => route.brokerKey === key), cash, funding, target: false};
    }

    removeBroker(key: string): void {
        const impact = this.brokerRemovalImpact(key);
        for (const cash of impact.cash) this.removeCash(cash.key);
        this.data.brokers = this.data.brokers.filter((item) => item.key !== key);
        this.syncRoutes();
    }

    // -- assets ------------------------------------------------------------

    addAsset(asset: DraftAsset): void {
        if (this.asset(asset.key)) return;
        this.data.assets.push(asset);
        this.syncRoutes();
    }

    replaceAsset(next: DraftAsset): void {
        const index = this.data.assets.findIndex((item) => item.key === next.key);
        if (index < 0) return;
        this.data.assets[index] = next;
    }

    assetRemovalImpact(key: string): RemovalImpact {
        return {routes: Object.values(this.data.routes).filter((route) => route.assetKey === key), cash: [], funding: [], target: key in this.data.targets};
    }

    removeAsset(key: string): void {
        this.data.assets = this.data.assets.filter((item) => item.key !== key);
        delete this.data.targets[key];
        if (this.assetOrder.includes(key)) this.assetOrder = this.assetOrder.filter((item) => item !== key);
        this.syncRoutes();
    }

    reorderAssets(keys: readonly string[]): void {
        this.assetOrder = [...keys];
    }

    // -- routes ------------------------------------------------------------

    /** One route per Asset × operative Broker; new pairs start enabled with the defaults (§8.2). */
    syncRoutes(): void {
        const wanted = new Set<string>();
        for (const asset of this.data.assets) {
            for (const broker of this.data.brokers) {
                if (broker.fundingOnly) continue;
                const key = routeKey(asset.key, broker.key);
                wanted.add(key);
                if (!this.data.routes[key]) {
                    this.data.routes[key] = {
                        wireId: this.nextId('route'),
                        assetKey: asset.key,
                        brokerKey: broker.key,
                        enabled: true,
                        priority: DEFAULT_ROUTE_PRIORITY,
                        minimumIfActive: '',
                        requiredMinimum: '',
                        cap: '',
                        marginPercent: DEFAULT_EXECUTION_MARGIN_PERCENT,
                        enteredAt: nowTimestamp(),
                    };
                }
            }
        }
        for (const key of Object.keys(this.data.routes)) {
            if (!wanted.has(key)) delete this.data.routes[key];
        }
        this.syncFunding();
    }

    /** The routes of one operative Broker, in the user's Asset order (Routing step). */
    routesOfBroker(brokerKey: string): DraftRoute[] {
        return this.orderedAssets.flatMap((asset) => this.data.routes[routeKey(asset.key, brokerKey)] ?? []);
    }

    // -- targets (control percentages only, Q-C0-2) --------------------------

    readonly targetTotal = $derived.by(() => {
        const values = this.data.assets.map((asset) => canonicalInput(this.data.targets[asset.key] ?? '') ?? '0');
        return sumControlPercentages(values);
    });

    readonly targetRemaining = $derived(this.targetTotal === null ? null : remainingControlPercentage(this.targetTotal));

    // -- FX ------------------------------------------------------------------

    /**
     * Pairs the backend will ask for, mirroring its closure (normalize.py
     * `validate_fx_pair_closure`): every referenced currency against the
     * valuation currency (`valuationPairs`), plus every cash pool of a Broker
     * against the price currency of each Asset it can buy (`conversionPairs`).
     * Only these are sent: a stale extra pair would reference a currency the
     * scenario no longer has, and the backend would ask for more rates.
     */
    readonly #fxClosure = $derived.by(() => {
        const valuation = this.data.valuationCurrency;
        const referenced = new Set<string>();
        const pools = new Map<string, Set<string>>();
        const addPool = (brokerKey: string, currency: string) => {
            if (!pools.has(brokerKey)) pools.set(brokerKey, new Set());
            pools.get(brokerKey)!.add(currency);
        };
        for (const cash of this.data.cash) {
            referenced.add(cash.currency);
            addPool(cash.brokerKey, cash.currency);
        }
        for (const item of this.data.contributions) referenced.add(item.currency);
        for (const broker of this.data.brokers) {
            for (const mode of broker.modes) if (!broker.fundingOnly) referenced.add(mode.currency);
            for (const funding of broker.funding) {
                if (!funding.enabled) continue;
                const currency = this.sourceCurrency(funding.source);
                if (currency) {
                    referenced.add(currency);
                    addPool(broker.key, currency);
                }
            }
        }
        for (const asset of this.data.assets) if (asset.price?.currency) referenced.add(asset.price.currency);
        const valuationPairs = new Set<string>();
        for (const currency of referenced) if (valuation && currency && currency !== valuation) valuationPairs.add(canonicalPair(currency, valuation));
        const conversionPairs = new Set<string>();
        for (const route of Object.values(this.data.routes)) {
            if (!route.enabled) continue;
            const quote = this.asset(route.assetKey)?.price?.currency;
            if (!quote) continue;
            for (const pool of pools.get(route.brokerKey) ?? []) if (pool !== quote) conversionPairs.add(canonicalPair(pool, quote));
        }
        return {valuation: [...valuationPairs].sort(), conversion: [...conversionPairs].sort()};
    });

    readonly valuationPairs = $derived(this.#fxClosure.valuation);
    readonly conversionPairs = $derived(this.#fxClosure.conversion);
    readonly requiredPairs = $derived([...new Set([...this.valuationPairs, ...this.conversionPairs])].sort());
    /** No pair needed: the FX step has nothing to ask and leaves the wizard. */
    readonly fxNeeded = $derived(this.requiredPairs.length > 0);

    fxPurpose(pair: string): FxPurpose {
        const valuation = this.valuationPairs.includes(pair);
        const conversion = this.conversionPairs.includes(pair);
        return valuation && conversion ? 'both' : conversion ? 'conversion' : 'valuation';
    }

    /** The wizard steps on screen: FX only when a rate is needed. */
    readonly visibleSteps: readonly PlannerStep[] = $derived(PLANNER_STEPS.filter((step) => step !== 'fx' || this.fxNeeded));

    ensureFx(pair: string): DraftFx {
        const existing = this.fx(pair);
        if (existing) return existing;
        const item: DraftFx = {pair, rate: '', copiedRate: null, stamp: null, source: null, referenceDate: null, manual: false, enteredAt: nowTimestamp()};
        this.data.fxRates.push(item);
        return this.data.fxRates[this.data.fxRates.length - 1];
    }

    // -- copies --------------------------------------------------------------

    registerCopy(kind: CopyKind, asOf: string, capturedAt: string, provenance: SourceProvenance[]): CopyRecord {
        const record: CopyRecord = {copyId: this.nextId('copy'), kind, asOf, capturedAt, provenance};
        this.data.copies[record.copyId] = record;
        return record;
    }

    copyRecord(stamp: CopyRef | null): CopyRecord | null {
        return stamp ? (this.data.copies[stamp.copyId] ?? null) : null;
    }

    // -- review counts (counts, never sums) ----------------------------------

    readonly factCounts = $derived.by(() => {
        let copied = 0;
        let manual = 0;
        let modified = 0;
        let stale = 0;
        for (const broker of this.data.brokers) {
            if (broker.origin === 'copied') copied += 1;
            else manual += 1;
        }
        for (const cash of this.data.cash) {
            if (cash.origin === 'copied') copied += 1;
            else manual += 1;
        }
        manual += this.data.contributions.length;
        for (const asset of this.data.assets) {
            if (asset.price) {
                if (priceIsCopied(asset)) {
                    copied += 1;
                    const age = daysBetween(asset.price.referenceDate, this.data.asOf);
                    if (age !== null && age > 0) stale += 1;
                } else if (asset.priceStamp) modified += 1;
                else manual += 1;
            }
            if (asset.exposures.length > 0) {
                if (asset.exposureStamp && sameExposures(asset.exposures, asset.copiedExposures)) copied += 1;
                else if (asset.exposureStamp) modified += 1;
                else manual += 1;
            }
        }
        for (const pair of this.requiredPairs) {
            const fx = this.fx(pair);
            if (!fx || !fx.rate) continue;
            if (rateIsCopied(fx)) {
                copied += 1;
                const age = fx.referenceDate ? daysBetween(fx.referenceDate, this.data.asOf) : null;
                if (age !== null && age > 0) stale += 1;
            } else if (fx.stamp) modified += 1;
            else manual += 1;
        }
        return {copied, manual, modified, stale};
    });
}

export function sameSource(left: FundingSourceRef, right: FundingSourceRef): boolean {
    if (left.kind === 'cash' && right.kind === 'cash') return left.cashKey === right.cashKey;
    if (left.kind === 'contribution' && right.kind === 'contribution') return left.contributionKey === right.contributionKey;
    return false;
}

/** Cash `selected` ≤ `available`, both in the row currency (Q-C0-2: same unit only). */
export function selectionExceedsAvailable(cash: DraftCash): boolean {
    const selected = canonicalInput(cash.selected);
    const available = canonicalInput(cash.available);
    if (selected === null || available === null) return false;
    return compareDecimal(selected, available) === 1;
}
