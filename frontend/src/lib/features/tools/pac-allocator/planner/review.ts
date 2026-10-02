/**
 * Step 9 projections (B16): per-section counts and the list of facts the
 * backend will receive. Counts and labels only; no amount is added,
 * converted or compared here.
 */
import {daysBetween, priceIsCopied, rateIsCopied, samePrice, type FactOrigin, type PlannerDraft} from './draft.svelte';
import type {PlannerStep} from './types';

export interface SectionCounts {
    scenario: {currency: string};
    liquidity: {sources: number; cash: number; contributions: number; currencies: string[]};
    brokers: {operative: number; fundingOnly: number; modes: number; fundingRoutes: number};
    /** `missing` = Assets still without a price. */
    assets: {count: number; priced: number; missing: number; stale: number; withExposures: number};
    routing: {enabled: number; assetsWithRoute: number};
    targets: {count: number};
    /** R9.4: only the pairs the scenario needs; `pairs` of them have a rate (`missing` do not), `conversions` move cash. */
    fx: {needed: number; pairs: number; missing: number; stale: number; conversions: number; spreadPercent: string};
    strategy: {policy: string};
}

export type FactValue =
    | {kind: 'money'; amount: string; currency: string; selected: string | null}
    | {kind: 'price'; amount: string; currency: string; units: string}
    | {kind: 'rate'; rate: string}
    | {kind: 'modes'; currencies: string[]; fundingOnly: boolean};

/** R11.3: the composition for the maps is not a fact of the calculation, so it has no row here. */
export type FactKind = 'broker' | 'cash' | 'contribution' | 'price' | 'fx';

/** R9.7: what the fact is about, so the Review can draw the same icons as the steps. */
export type FactSubject = {type: 'broker'; brokerKey: string} | {type: 'cash'; brokerKey: string; currency: string} | {type: 'contribution'; currency: string} | {type: 'asset'; assetKey: string} | {type: 'pair'; base: string; quote: string};

/** R9.7: `librefolio` = copied and untouched; `modified` = copied, then changed or overridden by the user. */
export type FactOriginState = 'librefolio' | 'manual' | 'modified';

export interface SnapshotFact {
    id: string;
    step: PlannerStep;
    kind: FactKind;
    entity: string;
    subject: FactSubject;
    origin: FactOrigin;
    modified: boolean;
    referenceDate: string | null;
    stale: boolean;
    value: FactValue;
}

export function factOriginState(fact: Pick<SnapshotFact, 'origin' | 'modified'>): FactOriginState {
    if (fact.modified) return 'modified';
    return fact.origin === 'copied' ? 'librefolio' : 'manual';
}

function isStale(referenceDate: string | null, asOf: string): boolean {
    if (!referenceDate) return false;
    const age = daysBetween(referenceDate, asOf);
    return age !== null && age > 0;
}

function hasAmount(text: string): boolean {
    return text.trim() !== '';
}

export function sectionCounts(draft: PlannerDraft): SectionCounts {
    const data = draft.data;
    const selectedCash = data.cash.filter((cash) => hasAmount(cash.selected));
    const contributions = data.contributions.filter((item) => hasAmount(item.amount));
    const currencies = [...new Set([...selectedCash.map((cash) => cash.currency), ...contributions.map((item) => item.currency)])].sort();
    const priced = data.assets.filter((asset) => asset.price !== null);
    const rated = draft.requiredPairs.flatMap((pair) => {
        const fx = draft.fx(pair);
        return fx && fx.rate.trim() !== '' ? [fx] : [];
    });
    const enabledRoutes = Object.values(data.routes).filter((route) => route.enabled && !draft.broker(route.brokerKey)?.fundingOnly);
    return {
        scenario: {currency: data.valuationCurrency},
        liquidity: {sources: selectedCash.length + contributions.length, cash: selectedCash.length, contributions: contributions.length, currencies},
        brokers: {
            operative: draft.operativeBrokers.length,
            fundingOnly: draft.fundingOnlyBrokers.length,
            modes: draft.operativeBrokers.reduce((count, broker) => count + broker.modes.length, 0),
            fundingRoutes: data.brokers.reduce((count, broker) => count + broker.funding.filter((item) => item.enabled).length, 0),
        },
        assets: {
            count: data.assets.length,
            priced: priced.length,
            missing: data.assets.length - priced.length,
            stale: priced.filter((asset) => priceIsCopied(asset) && isStale(asset.price!.referenceDate, data.asOf)).length,
            withExposures: data.assets.filter((asset) => asset.exposures.length > 0).length,
        },
        routing: {enabled: enabledRoutes.length, assetsWithRoute: new Set(enabledRoutes.map((route) => route.assetKey)).size},
        targets: {count: data.assets.filter((asset) => hasAmount(data.targets[asset.key] ?? '')).length},
        fx: {
            needed: draft.requiredPairs.length,
            pairs: rated.length,
            missing: draft.requiredPairs.length - rated.length,
            stale: rated.filter((fx) => rateIsCopied(fx) && isStale(fx.referenceDate, data.asOf)).length,
            conversions: draft.conversionPairs.length,
            spreadPercent: data.fxSpreadPercent,
        },
        strategy: {policy: data.policy},
    };
}

/** Every fact the calculation receives, with its origin and age (B16; R9.7: one filterable table). */
export function snapshotFacts(draft: PlannerDraft): SnapshotFact[] {
    const data = draft.data;
    const facts: SnapshotFact[] = [];
    for (const broker of data.brokers) {
        facts.push({
            id: `broker|${broker.key}`,
            step: 'brokers',
            kind: 'broker',
            entity: broker.name,
            subject: {type: 'broker', brokerKey: broker.key},
            origin: broker.origin,
            modified: false,
            referenceDate: null,
            stale: false,
            value: {kind: 'modes', currencies: [...new Set(broker.modes.map((mode) => mode.currency))], fundingOnly: broker.fundingOnly},
        });
    }
    for (const cash of data.cash) {
        facts.push({
            id: `cash|${cash.key}`,
            step: 'liquidity',
            kind: 'cash',
            entity: draft.broker(cash.brokerKey)?.name ?? cash.brokerKey,
            subject: {type: 'cash', brokerKey: cash.brokerKey, currency: cash.currency},
            origin: cash.origin,
            modified: false,
            referenceDate: null,
            stale: false,
            value: {kind: 'money', amount: cash.available, currency: cash.currency, selected: cash.selected.trim() === '' ? null : cash.selected},
        });
    }
    for (const item of data.contributions) {
        facts.push({
            id: `contribution|${item.key}`,
            step: 'liquidity',
            kind: 'contribution',
            entity: item.label,
            subject: {type: 'contribution', currency: item.currency},
            origin: 'manual',
            modified: false,
            referenceDate: null,
            stale: false,
            value: {kind: 'money', amount: item.amount, currency: item.currency, selected: null},
        });
    }
    for (const asset of data.assets) {
        const label = [asset.ticker, asset.name].filter((part) => part.trim() !== '').join(' ');
        if (asset.price) {
            facts.push({
                id: `price|${asset.key}`,
                step: 'assets',
                kind: 'price',
                entity: label,
                subject: {type: 'asset', assetKey: asset.key},
                origin: asset.priceStamp !== null && !asset.priceManual ? 'copied' : 'manual',
                modified: asset.priceStamp !== null && (asset.priceManual || !samePrice(asset.price, asset.copiedPrice)),
                referenceDate: priceIsCopied(asset) ? asset.price.referenceDate || null : null,
                stale: priceIsCopied(asset) && isStale(asset.price.referenceDate, data.asOf),
                value: {kind: 'price', amount: asset.price.amount, currency: asset.price.currency, units: asset.price.quoteBaseQuantity},
            });
        }
    }
    for (const pair of draft.requiredPairs) {
        const fx = draft.fx(pair);
        if (!fx || fx.rate.trim() === '') continue;
        const [base = '', quote = ''] = fx.pair.split('/');
        facts.push({
            id: `fx|${fx.pair}`,
            step: 'fx',
            kind: 'fx',
            entity: fx.pair,
            subject: {type: 'pair', base, quote},
            origin: fx.stamp !== null && !fx.manual ? 'copied' : 'manual',
            modified: fx.stamp !== null && fx.copiedRate !== null && !rateIsCopied(fx),
            referenceDate: rateIsCopied(fx) ? fx.referenceDate : null,
            stale: rateIsCopied(fx) && isStale(fx.referenceDate, data.asOf),
            value: {kind: 'rate', rate: fx.rate},
        });
    }
    return facts;
}
