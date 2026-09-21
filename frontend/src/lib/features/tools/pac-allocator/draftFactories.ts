import type {AllocationTargetDraft, PacEditorAsset, RebalanceEditorHolding} from './editorTypes';
import type {PacAllocationSourceAsset, PacAllocationSourceContext} from './allocationSource';

function defaultGrid(): {mode: 'whole'; quantity_step: string} {
    return {mode: 'whole', quantity_step: '1'};
}

function manualKey(kind: 'asset' | 'holding'): string {
    return `manual:${kind}:${crypto.randomUUID()}`;
}

export function createPacAsset(source: PacAllocationSourceAsset): PacEditorAsset {
    const value = {
        instrument_key: source.instrumentKey,
        name: source.name,
        buy_grid: defaultGrid(),
    };
    return {
        source,
        value,
        importedValue: cloneDraft(value),
        stale: false,
    };
}

export function createManualPacAsset(index: number): PacEditorAsset {
    const value = {
        instrument_key: manualKey('asset'),
        name: `Manual Asset ${index + 1}`,
        buy_grid: defaultGrid(),
    };
    return {
        source: null,
        importedValue: cloneDraft(value),
        stale: false,
        value,
    };
}

function holdingSource(asset: PacAllocationSourceAsset, context: PacAllocationSourceContext | null, sourceDate: string): RebalanceEditorHolding['source'] {
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

export function createRebalanceHoldings(source: PacAllocationSourceAsset, sourceDate = ''): RebalanceEditorHolding[] {
    const contexts: readonly (PacAllocationSourceContext | null)[] = source.contexts.length > 0 ? source.contexts : [null];

    return contexts.map((context, index) => {
        const value = {
            row_key: `${context?.contextKey ?? source.candidateKey}:${index}`,
            instrument_key: source.instrumentKey,
            name: source.name,
            quantity: context?.custodyQuantity ?? '0',
            quote: {
                raw_price: source.quote.rawPrice,
                currency: source.quote.currency,
                quote_base_quantity: source.quote.quoteBaseQuantity,
                reference_date: source.quote.referenceDate,
            },
            buy_grid: defaultGrid(),
        };
        return {
            source: holdingSource(source, context, sourceDate),
            importedValue: cloneDraft(value),
            stale: false,
            value,
        };
    });
}

export function createManualRebalanceHolding(index: number): RebalanceEditorHolding {
    const instrumentKey = manualKey('asset');
    const value = {
        row_key: manualKey('holding'),
        instrument_key: instrumentKey,
        name: `Manual Asset ${index + 1}`,
        quantity: '',
        quote: {
            raw_price: null,
            currency: null,
            quote_base_quantity: 1,
            reference_date: null,
        },
        buy_grid: defaultGrid(),
    };
    return {
        source: null,
        importedValue: cloneDraft(value),
        stale: false,
        value,
    };
}

export function syncTargets(instruments: readonly {instrument_key: string; name: string}[], current: readonly AllocationTargetDraft[]): AllocationTargetDraft[] {
    const existing = new Map(current.map((target) => [target.instrument_key, target]));
    const seen = new Set<string>();
    const next: AllocationTargetDraft[] = [];
    for (const instrument of instruments) {
        if (seen.has(instrument.instrument_key)) continue;
        seen.add(instrument.instrument_key);
        const prior = existing.get(instrument.instrument_key);
        next.push({
            instrument_key: instrument.instrument_key,
            name: instrument.name,
            target_percent: prior?.target_percent ?? '',
        });
    }
    return next;
}

export function cloneDraft<T>(value: T): T {
    return structuredClone(value);
}

export function closePercentDistribution(values: readonly string[]): string[] {
    if (values.length === 0) return [];
    const parts = values.map((value) => {
        if (!/^\d+(?:\.\d+)?$/.test(value)) return null;
        const [whole = '0', fraction = ''] = value.split('.');
        return {digits: BigInt(`${whole}${fraction}`), places: fraction.length};
    });
    if (parts.some((value) => value === null)) return [...values];
    const parsed = parts.filter((value): value is {digits: bigint; places: number} => value !== null);
    const places = Math.max(0, ...parsed.map((value) => value.places));
    const scale = 10n ** BigInt(places);
    const used = parsed.slice(0, -1).reduce((sum, value) => sum + value.digits * 10n ** BigInt(places - value.places), 0n);
    const remainder = 100n * scale - used;
    if (remainder < 0n) return [...values];
    const digits = remainder.toString().padStart(places + 1, '0');
    const whole = places === 0 ? digits : digits.slice(0, -places);
    const fraction = places === 0 ? '' : digits.slice(-places).replace(/0+$/, '');
    return [...values.slice(0, -1), `${whole}${fraction ? `.${fraction}` : ''}`];
}
