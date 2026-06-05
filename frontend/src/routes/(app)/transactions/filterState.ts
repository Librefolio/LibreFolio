import type {FilterValue} from '$lib/components/table/types';

export type TransactionFilterMap = {
    broker_id?: number;
    broker_ids?: number[];
    asset_id?: number;
    asset_ids?: number[];
    types?: string[];
    date_start?: string;
    date_end?: string;
    tags?: string[];
    currency?: string;
    cash?: Array<{code: string; min?: number; max?: number}>;
    id_min?: number;
    id_max?: number;
    qty_min?: number;
    qty_max?: number;
    page?: number;
    page_size?: number;
};

export function parseTransactionFilters(searchParams: URLSearchParams): TransactionFilterMap {
    const out: TransactionFilterMap = {};
    const num = (k: string) => {
        const v = searchParams.get(k);
        if (v == null || v === '') return undefined;
        const n = Number(v);
        return Number.isFinite(n) ? n : undefined;
    };
    const csv = (k: string) => {
        const v = searchParams.get(k);
        return v ? v.split(',').filter(Boolean) : undefined;
    };

    out.broker_id = num('broker_id');
    out.asset_id = num('asset_id');

    const brokerIdsRaw = csv('broker_ids');
    if (brokerIdsRaw) out.broker_ids = brokerIdsRaw.map(Number).filter(Number.isFinite);

    const assetIdsRaw = csv('asset_ids');
    if (assetIdsRaw) out.asset_ids = assetIdsRaw.map(Number).filter(Number.isFinite);

    out.types = csv('types');
    out.date_start = searchParams.get('date_start') || undefined;
    out.date_end = searchParams.get('date_end') || undefined;
    out.tags = csv('tags');
    out.currency = searchParams.get('currency') || undefined;
    out.id_min = num('id_min');
    out.id_max = num('id_max');
    out.qty_min = num('qty_min');
    out.qty_max = num('qty_max');

    const cashRaw = searchParams.get('cash');
    if (cashRaw) {
        const items: Array<{code: string; min?: number; max?: number}> = [];
        for (const s of cashRaw
            .split(',')
            .map((x) => x.trim())
            .filter(Boolean)) {
            const [code, minS, maxS] = s.split(':');
            if (!code) continue;
            const min = minS != null && minS !== '' ? Number(minS) : undefined;
            const max = maxS != null && maxS !== '' ? Number(maxS) : undefined;
            const it: {code: string; min?: number; max?: number} = {code: code.toUpperCase()};
            if (Number.isFinite(min as number)) it.min = min as number;
            if (Number.isFinite(max as number)) it.max = max as number;
            items.push(it);
        }
        if (items.length > 0) out.cash = items;
    }

    out.page = num('page');
    out.page_size = num('page_size');
    return out;
}

export function buildTransactionsFiltersUrl(filters: TransactionFilterMap): string {
    const params = new URLSearchParams();
    if (filters.broker_id != null) params.set('broker_id', String(filters.broker_id));
    if (filters.broker_ids?.length) params.set('broker_ids', filters.broker_ids.join(','));
    if (filters.asset_id != null) params.set('asset_id', String(filters.asset_id));
    if (filters.asset_ids?.length) params.set('asset_ids', filters.asset_ids.join(','));
    if (filters.types?.length) params.set('types', filters.types.join(','));
    if (filters.date_start) params.set('date_start', filters.date_start);
    if (filters.date_end) params.set('date_end', filters.date_end);
    if (filters.tags?.length) params.set('tags', filters.tags.join(','));
    if (filters.currency) params.set('currency', filters.currency);
    if (filters.id_min != null) params.set('id_min', String(filters.id_min));
    if (filters.id_max != null) params.set('id_max', String(filters.id_max));
    if (filters.qty_min != null) params.set('qty_min', String(filters.qty_min));
    if (filters.qty_max != null) params.set('qty_max', String(filters.qty_max));
    if (filters.cash?.length) {
        params.set('cash', filters.cash.map((it) => `${it.code}:${it.min ?? ''}:${it.max ?? ''}`).join(','));
    }
    if (filters.page != null && filters.page !== 1) params.set('page', String(filters.page));
    if (filters.page_size != null && filters.page_size !== 50) params.set('page_size', String(filters.page_size));
    const qs = params.toString();
    return qs ? `/transactions?${qs}` : '/transactions';
}

export function toTransactionColumnFilters(filters: TransactionFilterMap): Record<string, FilterValue> {
    const out: Record<string, FilterValue> = {};
    if (filters.types?.length) out.types = {type: 'enum', selected: filters.types};
    if (filters.tags?.length) out.tags = {type: 'multi-enum', selected: filters.tags};
    if (filters.broker_id != null) out.broker_id = {type: 'enum', selected: [String(filters.broker_id)]};
    else if (filters.broker_ids?.length) out.broker_id = {type: 'enum', selected: filters.broker_ids.map(String)};
    if (filters.asset_id != null) out.asset_id = {type: 'enum', selected: [String(filters.asset_id)]};
    else if (filters.asset_ids?.length) out.asset_id = {type: 'enum', selected: filters.asset_ids.map(String)};
    if (filters.date_start || filters.date_end) out.date = {type: 'date', from: filters.date_start, to: filters.date_end};
    if (filters.cash?.length) out.cash = {type: 'currency-stack', items: filters.cash.map((i) => ({...i}))};
    if (filters.id_min != null || filters.id_max != null) out.id = {type: 'number', min: filters.id_min, max: filters.id_max};
    if (filters.qty_min != null || filters.qty_max != null) out.qty = {type: 'number', min: filters.qty_min, max: filters.qty_max};
    return out;
}

export function applyTransactionColumnFilters(filters: TransactionFilterMap, record: Record<string, FilterValue>): TransactionFilterMap | null {
    const next: TransactionFilterMap = {...filters};

    next.types = undefined;
    next.tags = undefined;
    next.broker_id = undefined;
    next.broker_ids = undefined;
    next.asset_id = undefined;
    next.asset_ids = undefined;
    next.date_start = undefined;
    next.date_end = undefined;
    next.cash = undefined;
    next.id_min = undefined;
    next.id_max = undefined;
    next.qty_min = undefined;
    next.qty_max = undefined;

    for (const [k, v] of Object.entries(record)) {
        if (!v) continue;
        if (k === 'types' && v.type === 'enum') next.types = v.selected.length > 0 ? v.selected : undefined;
        else if (k === 'tags' && v.type === 'multi-enum') next.tags = v.selected.length > 0 ? v.selected : undefined;
        else if (k === 'broker_id' && v.type === 'enum') {
            if (v.selected.length === 1) {
                next.broker_id = Number(v.selected[0]);
                next.broker_ids = undefined;
            } else if (v.selected.length > 1) {
                next.broker_id = undefined;
                next.broker_ids = v.selected.map(Number);
            }
        } else if (k === 'asset_id' && v.type === 'enum') {
            if (v.selected.length === 1) {
                next.asset_id = Number(v.selected[0]);
                next.asset_ids = undefined;
            } else if (v.selected.length > 1) {
                next.asset_id = undefined;
                next.asset_ids = v.selected.map(Number);
            }
        } else if (k === 'date' && v.type === 'date') {
            next.date_start = v.from || undefined;
            next.date_end = v.to || undefined;
        } else if (k === 'cash' && v.type === 'currency-stack') next.cash = v.items.length > 0 ? v.items.map((i) => ({...i})) : undefined;
        else if (k === 'id' && v.type === 'number') {
            next.id_min = v.min;
            next.id_max = v.max;
        } else if (k === 'qty' && v.type === 'number') {
            next.qty_min = v.min;
            next.qty_max = v.max;
        }
    }

    const sameTypes = JSON.stringify(filters.types ?? null) === JSON.stringify(next.types ?? null);
    const sameTags = JSON.stringify(filters.tags ?? null) === JSON.stringify(next.tags ?? null);
    const sameBroker = (filters.broker_id ?? null) === (next.broker_id ?? null) && JSON.stringify(filters.broker_ids ?? null) === JSON.stringify(next.broker_ids ?? null);
    const sameAsset = (filters.asset_id ?? null) === (next.asset_id ?? null) && JSON.stringify(filters.asset_ids ?? null) === JSON.stringify(next.asset_ids ?? null);
    const sameDate = (filters.date_start ?? null) === (next.date_start ?? null) && (filters.date_end ?? null) === (next.date_end ?? null);
    const sameCash = JSON.stringify(filters.cash ?? null) === JSON.stringify(next.cash ?? null);
    const sameId = (filters.id_min ?? null) === (next.id_min ?? null) && (filters.id_max ?? null) === (next.id_max ?? null);
    const sameQty = (filters.qty_min ?? null) === (next.qty_min ?? null) && (filters.qty_max ?? null) === (next.qty_max ?? null);
    if (sameTypes && sameTags && sameBroker && sameAsset && sameDate && sameCash && sameId && sameQty) return null;

    next.page = 1;
    return next;
}

