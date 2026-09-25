/**
 * Step 9 projections (B16): per-section counts and the list of facts the
 * backend will receive. Counts and labels only; no amount is added,
 * converted or compared here.
 */
import {compareDecimal} from './decimal';
import {daysBetween, sameExposures, samePrice, type FactOrigin, type PlannerDraft} from './draft.svelte';
import type {PlannerStep} from './types';

export interface SectionCounts {
    scenario: {asOf: string; currency: string};
    liquidity: {sources: number; cash: number; contributions: number; currencies: string[]};
    brokers: {operative: number; fundingOnly: number; modes: number; fundingRoutes: number};
    assets: {count: number; priced: number; stale: number; withExposures: number};
    routing: {enabled: number; assetsWithRoute: number};
    targets: {count: number};
    fx: {pairs: number; stale: number; spreadPercent: string};
    strategy: {policy: string};
}

export type FactValue = {kind: 'money'; amount: string; currency: string; selected: string | null} | {kind: 'price'; amount: string; currency: string; units: string} | {kind: 'rate'; rate: string} | {kind: 'rows'; count: number} | {kind: 'none'};

export interface SnapshotFact {
    id: string;
    step: PlannerStep;
    kind: 'broker' | 'cash' | 'contribution' | 'price' | 'exposures' | 'fx';
    entity: string;
    origin: FactOrigin;
    modified: boolean;
    referenceDate: string | null;
    stale: boolean;
    value: FactValue;
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
    const rated = data.fxRates.filter((fx) => fx.rate.trim() !== '');
    const enabledRoutes = Object.values(data.routes).filter((route) => route.enabled && !draft.broker(route.brokerKey)?.fundingOnly);
    return {
        scenario: {asOf: data.asOf, currency: data.valuationCurrency},
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
            stale: priced.filter((asset) => isStale(asset.price!.referenceDate, data.asOf)).length,
            withExposures: data.assets.filter((asset) => asset.exposures.length > 0).length,
        },
        routing: {enabled: enabledRoutes.length, assetsWithRoute: new Set(enabledRoutes.map((route) => route.assetKey)).size},
        targets: {count: data.assets.filter((asset) => hasAmount(data.targets[asset.key] ?? '')).length},
        fx: {pairs: rated.length, stale: rated.filter((fx) => isStale(fx.referenceDate, data.asOf)).length, spreadPercent: data.fxSpreadPercent},
        strategy: {policy: data.policy},
    };
}

/** Every fact of the snapshot with its origin and age (B16 [Full snapshot]). */
export function snapshotFacts(draft: PlannerDraft): SnapshotFact[] {
    const data = draft.data;
    const facts: SnapshotFact[] = [];
    for (const broker of data.brokers) {
        facts.push({id: `broker|${broker.key}`, step: 'brokers', kind: 'broker', entity: broker.name, origin: broker.origin, modified: false, referenceDate: null, stale: false, value: {kind: 'none'}});
    }
    for (const cash of data.cash) {
        facts.push({
            id: `cash|${cash.key}`,
            step: 'liquidity',
            kind: 'cash',
            entity: [draft.broker(cash.brokerKey)?.name ?? cash.brokerKey, cash.currency].join(' · '),
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
                origin: asset.priceStamp ? 'copied' : 'manual',
                modified: asset.priceStamp !== null && !samePrice(asset.price, asset.copiedPrice),
                referenceDate: asset.price.referenceDate || null,
                stale: isStale(asset.price.referenceDate, data.asOf),
                value: {kind: 'price', amount: asset.price.amount, currency: asset.price.currency, units: asset.price.quoteBaseQuantity},
            });
        }
        if (asset.exposures.length > 0) {
            facts.push({
                id: `exposures|${asset.key}`,
                step: 'assets',
                kind: 'exposures',
                entity: label,
                origin: asset.exposureStamp ? 'copied' : 'manual',
                modified: asset.exposureStamp !== null && !sameExposures(asset.exposures, asset.copiedExposures),
                referenceDate: null,
                stale: false,
                value: {kind: 'rows', count: asset.exposures.length},
            });
        }
    }
    for (const fx of data.fxRates) {
        if (fx.rate.trim() === '') continue;
        facts.push({
            id: `fx|${fx.pair}`,
            step: 'fx',
            kind: 'fx',
            entity: fx.pair,
            origin: fx.stamp ? 'copied' : 'manual',
            modified: fx.stamp !== null && fx.copiedRate !== null && compareDecimal(fx.rate, fx.copiedRate) !== 0,
            referenceDate: fx.referenceDate,
            stale: isStale(fx.referenceDate, data.asOf),
            value: {kind: 'rate', rate: fx.rate},
        });
    }
    return facts;
}
