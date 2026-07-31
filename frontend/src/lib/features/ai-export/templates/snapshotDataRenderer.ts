import {escapeMarkdownTableCell, normalizeJsonSafeValue, serializeYaml} from '../serialization';

type JsonRecord = Record<string, unknown>;

export interface SnapshotDataTextBlock {
    readonly id: string;
    readonly content: string;
}

export interface RenderedSnapshotDataText {
    readonly content: string;
    readonly blocks: readonly SnapshotDataTextBlock[];
    readonly wrapper: string;
    readonly formatPreamble: string;
    readonly entityDirectory: string;
    readonly signalMetrics: readonly SnapshotSignalMetric[];
    readonly formatDiagnostics: SnapshotFormatDiagnostics;
}

export interface SnapshotFormatDiagnostics {
    readonly numeric_values_compacted: number;
    readonly floating_point_noise_normalized: number;
    readonly bounded_values_snapped: number;
    readonly event_differences_zeroed: number;
    readonly monetary_residuals_zeroed: number;
    readonly normalized_ratio_percent_values: number;
    readonly already_scaled_percent_values: number;
    readonly empty_columns_removed: number;
    readonly empty_parent_columns_removed: number;
    readonly semantic_duplicate_columns_detected: number;
    readonly empty_temporal_rows_omitted: number;
}

export interface SnapshotSignalMetric {
    readonly component_id: string;
    readonly kind: 'indicator' | 'event';
    readonly signal_code: string;
    readonly instance_count: number;
    readonly history_row_count: number;
    readonly history_chars: number;
    readonly event_count: number;
    readonly event_chars: number;
    readonly definition_chars: number;
    readonly summary_chars: number;
}

const COMPONENT_SEPARATOR = '\n\n';
const BASE_FORMAT_PREAMBLE_LINES = [
    'SNAPSHOT DATA FORMAT',
    'technical_components=compact_pipe_tables_v1',
    'other_components=generic_pipe_tables_v1',
    'unknown_versions=yaml_fallback_v1',
    'entity_refs=resolve through ENTITY DIRECTORY',
    'user_facing_rule=never use refs or numeric IDs as names; use display names or clear shortened names',
    'numeric_display=remove trailing zeros, round fractional precision to 4 significant digits after leading zeros, and suppress only semantically identified floating-point noise; backend calculations remain full precision',
    'normalized_weights=shown directly as percentages; no user or model conversion required',
    'null=explicitly unavailable',
    'dated_scalar=value@date',
    'range=f:first;l:last;n:min;x:max;c:observation_count',
    'table delimiters use | and embedded delimiters are escaped',
] as const;
const MISSING_PRICE_POLICY = 'missing_price_policy=When a price is needed for a date without an observation, use the latest available observation on or before that date. Never use a future price.';
const BOUNDED_DISPLAY_EPSILON = 1e-10;
const EVENT_DIFFERENCE_EPSILON = 1e-10;

interface MutableSnapshotFormatDiagnostics {
    numeric_values_compacted: number;
    floating_point_noise_normalized: number;
    bounded_values_snapped: number;
    event_differences_zeroed: number;
    monetary_residuals_zeroed: number;
    normalized_ratio_percent_values: number;
    already_scaled_percent_values: number;
    empty_columns_removed: number;
    empty_parent_columns_removed: number;
    semantic_duplicate_columns_detected: number;
    empty_temporal_rows_omitted: number;
}

export interface PromptNumberSemantics {
    readonly minimum?: number;
    readonly maximum?: number;
    readonly zeroEpsilon?: number;
    readonly monetaryResidualCurrency?: string;
}

function createFormatDiagnostics(): MutableSnapshotFormatDiagnostics {
    return {
        numeric_values_compacted: 0,
        floating_point_noise_normalized: 0,
        bounded_values_snapped: 0,
        event_differences_zeroed: 0,
        monetary_residuals_zeroed: 0,
        normalized_ratio_percent_values: 0,
        already_scaled_percent_values: 0,
        empty_columns_removed: 0,
        empty_parent_columns_removed: 0,
        semantic_duplicate_columns_detected: 0,
        empty_temporal_rows_omitted: 0,
    };
}

function formatPreamble(sections: readonly JsonRecord[]): string {
    const appliesMissingPricePolicy = sections.some((section) => {
        const componentId = String(section.component_id ?? '');
        return ['price', 'position', 'performance', 'ohlc', 'rate', 'valuation', 'fifo'].some((token) => componentId.includes(token));
    });
    return [...BASE_FORMAT_PREAMBLE_LINES, ...(appliesMissingPricePolicy ? [MISSING_PRICE_POLICY] : []), ''].join('\n');
}

interface AssetDirectoryEntry {
    readonly assetId: string;
    displayName?: unknown;
    ticker?: unknown;
    isin?: unknown;
    cusip?: unknown;
    sedol?: unknown;
    figi?: unknown;
    other?: unknown;
    currency?: unknown;
    assetType?: unknown;
    quoteBaseQuantity?: unknown;
}

interface BrokerDirectoryEntry {
    readonly brokerId: string;
    name?: unknown;
}

interface EntityDirectory {
    readonly assetRefById: ReadonlyMap<string, string>;
    readonly brokerRefById: ReadonlyMap<string, string>;
    readonly fxRef?: string;
    readonly content: string;
}

interface IndicatorSampling {
    readonly temporalClass?: unknown;
    readonly bucketCount?: unknown;
}

function isRecord(value: unknown): value is JsonRecord {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function records(value: unknown): JsonRecord[] | undefined {
    return Array.isArray(value) && value.every(isRecord) ? value : undefined;
}

function plainDecimal(value: number): string {
    const raw = String(value);
    if (!/[eE]/.test(raw)) return raw;
    const [coefficient, exponentText] = raw.toLowerCase().split('e');
    const exponent = Number(exponentText);
    const negative = coefficient.startsWith('-');
    const unsigned = negative ? coefficient.slice(1) : coefficient;
    const [integer, fraction = ''] = unsigned.split('.');
    const digits = `${integer}${fraction}`;
    const decimalIndex = integer.length + exponent;
    const expanded = decimalIndex <= 0 ? `0.${'0'.repeat(-decimalIndex)}${digits}` : decimalIndex >= digits.length ? `${digits}${'0'.repeat(decimalIndex - digits.length)}` : `${digits.slice(0, decimalIndex)}.${digits.slice(decimalIndex)}`;
    return negative ? `-${expanded}` : expanded;
}

function roundedFraction(integer: string, fraction: string, significantDigits: number): {readonly integer: string; readonly fraction: string} {
    const firstNonZero = fraction.search(/[1-9]/);
    if (firstNonZero < 0) return {integer, fraction: ''};
    const keepLength = firstNonZero + significantDigits;
    if (fraction.length <= keepLength) return {integer, fraction: fraction.replace(/0+$/, '')};
    const kept = fraction.slice(0, keepLength);
    const shouldRound = Number(fraction[keepLength]) >= 5;
    if (!shouldRound) return {integer, fraction: kept.replace(/0+$/, '')};
    const combined = BigInt(`${integer}${kept}` || '0') + 1n;
    const padded = combined.toString().padStart(integer.length + keepLength, '0');
    const integerLength = padded.length - keepLength;
    return {
        integer: padded.slice(0, integerLength) || '0',
        fraction: padded.slice(integerLength).replace(/0+$/, ''),
    };
}

function currencyMinorUnit(currencyCode: string): number {
    try {
        return 10 ** -(new Intl.NumberFormat('en', {style: 'currency', currency: currencyCode}).resolvedOptions().maximumFractionDigits ?? 2);
    } catch {
        return 0.01;
    }
}

function formatPromptNumberWithDiagnostics(value: number | string, semantics: PromptNumberSemantics = {}, diagnostics?: MutableSnapshotFormatDiagnostics): string {
    const raw = typeof value === 'number' ? plainDecimal(value) : value;
    if (!/^-?\d+(?:\.\d+)?$/.test(raw)) return raw;
    const parsed = Number(raw);
    let normalizedRaw = raw;
    let noiseKind: 'bounded' | 'difference' | 'monetary' | undefined;
    if (Number.isFinite(parsed)) {
        const bounds = [
            ['minimum', semantics.minimum],
            ['maximum', semantics.maximum],
        ] as const;
        for (const [, bound] of bounds) {
            if (bound === undefined) continue;
            const epsilon = BOUNDED_DISPLAY_EPSILON * Math.max(1, Math.abs(bound));
            if (parsed !== bound && Math.abs(parsed - bound) <= epsilon) {
                normalizedRaw = plainDecimal(bound);
                noiseKind = 'bounded';
                break;
            }
        }
        if (!noiseKind && parsed !== 0 && semantics.zeroEpsilon !== undefined && Math.abs(parsed) <= semantics.zeroEpsilon) {
            normalizedRaw = '0';
            noiseKind = 'difference';
        }
        if (!noiseKind && parsed !== 0 && semantics.monetaryResidualCurrency && Math.abs(parsed) < currencyMinorUnit(semantics.monetaryResidualCurrency)) {
            normalizedRaw = '0';
            noiseKind = 'monetary';
        }
    }
    const negative = normalizedRaw.startsWith('-');
    const unsigned = negative ? normalizedRaw.slice(1) : normalizedRaw;
    const [integerRaw, fraction = ''] = unsigned.split('.');
    const integer = integerRaw.replace(/^0+(?=\d)/, '') || '0';
    const rounded = roundedFraction(integer, fraction, 4);
    const sign = negative && (rounded.integer !== '0' || rounded.fraction !== '') ? '-' : '';
    const formatted = `${sign}${rounded.integer}${rounded.fraction ? `.${rounded.fraction}` : ''}`;
    if (diagnostics && formatted !== raw) diagnostics.numeric_values_compacted += 1;
    if (diagnostics && noiseKind) {
        diagnostics.floating_point_noise_normalized += 1;
        if (noiseKind === 'bounded') diagnostics.bounded_values_snapped += 1;
        if (noiseKind === 'difference') diagnostics.event_differences_zeroed += 1;
        if (noiseKind === 'monetary') diagnostics.monetary_residuals_zeroed += 1;
    }
    return formatted;
}

export function formatPromptNumber(value: number | string, semantics: PromptNumberSemantics = {}): string {
    return formatPromptNumberWithDiagnostics(value, semantics);
}

function formattedStructuredValue(value: unknown): unknown {
    if (typeof value === 'number' && Number.isFinite(value)) return formatPromptNumber(value);
    if (Array.isArray(value)) return value.map(formattedStructuredValue);
    if (isRecord(value)) return Object.fromEntries(Object.entries(value).map(([key, nested]) => [key, formattedStructuredValue(nested)]));
    return value;
}

function scalar(value: unknown): string {
    if (value === undefined) return '';
    if (value === null) return 'null';
    if (typeof value === 'string') return value;
    if (typeof value === 'number') return Number.isFinite(value) ? formatPromptNumber(value) : String(value);
    if (typeof value === 'boolean') return String(value);
    return JSON.stringify(normalizeJsonSafeValue(formattedStructuredValue(value)));
}

function tableCell(value: unknown): string {
    return escapeMarkdownTableCell(scalar(value));
}

function pipeRow(values: readonly unknown[]): string {
    return `|${values.map(tableCell).join('|')}|`;
}

function isEmptyPublicValue(value: unknown): boolean {
    return value === undefined || value === null || value === '' || value === 'null';
}

function pipeTable(headers: readonly string[], rows: readonly (readonly unknown[])[], diagnostics?: MutableSnapshotFormatDiagnostics): string {
    if (rows.some((row) => row.length !== headers.length)) {
        throw new TypeError('AI Export compact table row width must match its header');
    }
    const includedIndexes = rows.length === 0 ? headers.map((_header, index) => index) : headers.map((_header, index) => index).filter((index) => rows.some((row) => !isEmptyPublicValue(row[index])));
    if (diagnostics) diagnostics.empty_columns_removed += headers.length - includedIndexes.length;
    const includedHeaders = includedIndexes.map((index) => headers[index]);
    const includedRows = rows.map((row) => includedIndexes.map((index) => row[index]));
    return [pipeRow(includedHeaders), ...includedRows.map(pipeRow)].join('\n');
}

function valueMap(value: unknown, boundsByKey?: JsonRecord, diagnostics?: MutableSnapshotFormatDiagnostics): string {
    if (value === null || value === undefined) return 'null';
    if (!isRecord(value)) return scalar(value);
    return Object.keys(value)
        .sort()
        .map((key) => {
            const bounds = isRecord(boundsByKey?.[key]) ? boundsByKey[key] : undefined;
            const semantics: PromptNumberSemantics = {
                minimum: typeof bounds?.minimum === 'number' ? bounds.minimum : undefined,
                maximum: typeof bounds?.maximum === 'number' ? bounds.maximum : undefined,
                zeroEpsilon: key === 'difference' ? EVENT_DIFFERENCE_EPSILON : undefined,
            };
            const nested = value[key];
            const rendered =
                typeof nested === 'number' && Number.isFinite(nested) ? formatPromptNumberWithDiagnostics(nested, semantics, diagnostics) : typeof nested === 'string' && /^-?\d+(?:\.\d+)?$/.test(nested) ? formatPromptNumberWithDiagnostics(nested, semantics, diagnostics) : scalar(nested);
            return `${key}=${rendered}`;
        })
        .join(',');
}

function datedValue(value: unknown, semantics: PromptNumberSemantics = {}, diagnostics?: MutableSnapshotFormatDiagnostics): string {
    if (!isRecord(value)) return 'null';
    const renderedValue =
        typeof value.value === 'number' && Number.isFinite(value.value)
            ? formatPromptNumberWithDiagnostics(value.value, semantics, diagnostics)
            : typeof value.value === 'string' && /^-?\d+(?:\.\d+)?$/.test(value.value)
              ? formatPromptNumberWithDiagnostics(value.value, semantics, diagnostics)
              : scalar(value.value);
    return `${renderedValue}@${scalar(value.date)}`;
}

function indicatorCell(value: unknown, semantics: PromptNumberSemantics = {}, diagnostics?: MutableSnapshotFormatDiagnostics): string {
    if (value === null || value === undefined) return 'null';
    if (!isRecord(value)) return scalar(value);
    if (value.kind === 'single') return datedValue(value, semantics, diagnostics);
    if (value.kind !== 'range') return scalar(value);
    return [`f:${datedValue(value.first, semantics, diagnostics)}`, `l:${datedValue(value.last, semantics, diagnostics)}`, `n:${datedValue(value.min, semantics, diagnostics)}`, `x:${datedValue(value.max, semantics, diagnostics)}`, `c:${scalar(value.observation_count)}`].join(';');
}

function mergeAssetEntry(entries: Map<string, AssetDirectoryEntry>, assetIdValue: unknown, values: Partial<AssetDirectoryEntry>): void {
    if (assetIdValue === undefined || assetIdValue === null) return;
    const assetId = scalar(assetIdValue);
    const current = entries.get(assetId) ?? {assetId};
    entries.set(assetId, {
        ...current,
        ...Object.fromEntries(Object.entries(values).filter(([, value]) => value !== undefined && value !== null && value !== '')),
        assetId,
    });
}

function mergeBrokerEntry(entries: Map<string, BrokerDirectoryEntry>, brokerIdValue: unknown, name: unknown): void {
    if (brokerIdValue === undefined || brokerIdValue === null) return;
    const brokerId = scalar(brokerIdValue);
    const current = entries.get(brokerId) ?? {brokerId};
    entries.set(brokerId, {
        ...current,
        ...(name !== undefined && name !== null && name !== '' ? {name} : {}),
        brokerId,
    });
}

function collectDirectories(sections: readonly JsonRecord[], target: unknown, providedDirectory: unknown): EntityDirectory {
    const assets = new Map<string, AssetDirectoryEntry>();
    const brokers = new Map<string, BrokerDirectoryEntry>();
    if (isRecord(providedDirectory)) {
        for (const asset of records(providedDirectory.assets) ?? []) {
            mergeAssetEntry(assets, asset.asset_id, {
                displayName: asset.display_name,
                ticker: asset.ticker,
                isin: asset.isin,
                cusip: asset.cusip,
                sedol: asset.sedol,
                figi: asset.figi,
                other: asset.other_identifiers,
                currency: asset.currency,
                assetType: asset.asset_type,
                quoteBaseQuantity: asset.quote_base_quantity,
            });
        }
        for (const broker of records(providedDirectory.brokers) ?? []) {
            mergeBrokerEntry(brokers, broker.broker_id, broker.display_name);
        }
    }
    for (const section of sections) {
        const componentId = scalar(section.component_id);
        const payload = isRecord(section.payload) ? section.payload : undefined;
        if (!payload) continue;
        if (componentId === 'asset.identity') {
            const identifiers = isRecord(payload.identifiers) ? payload.identifiers : {};
            mergeAssetEntry(assets, payload.asset_id, {
                displayName: payload.display_name,
                ticker: identifiers.ticker,
                isin: identifiers.isin,
                cusip: identifiers.cusip,
                sedol: identifiers.sedol,
                figi: identifiers.figi,
                other: identifiers.other,
                currency: payload.currency,
                assetType: payload.asset_type,
                quoteBaseQuantity: payload.quote_base_quantity,
            });
        }
        const visit = (value: unknown): void => {
            if (Array.isArray(value)) {
                for (const nested of value) visit(nested);
                return;
            }
            if (!isRecord(value)) return;
            if (value.asset_id !== undefined) {
                mergeAssetEntry(assets, value.asset_id, {
                    displayName: value.asset_name ?? value.display_name,
                    ticker: value.asset_ticker,
                    isin: value.asset_isin,
                    cusip: value.asset_cusip,
                    sedol: value.asset_sedol,
                    figi: value.asset_figi,
                    other: value.asset_other,
                    currency: value.asset_currency ?? value.currency,
                    assetType: value.asset_type,
                    quoteBaseQuantity: value.quote_base_quantity,
                });
            }
            if (value.broker_id !== undefined) mergeBrokerEntry(brokers, value.broker_id, value.broker_name ?? value.display_name);
            for (const nested of Object.values(value)) visit(nested);
        };
        visit(payload);
        const positions = records(payload.positions);
        if (positions) {
            for (const position of positions) {
                mergeAssetEntry(assets, position.asset_id, {
                    displayName: position.asset_name,
                    ticker: position.asset_ticker,
                    isin: position.asset_isin,
                    cusip: position.asset_cusip,
                    sedol: position.asset_sedol,
                    figi: position.asset_figi,
                    other: position.asset_other,
                    assetType: position.asset_type,
                });
                mergeBrokerEntry(brokers, position.broker_id, position.broker_name);
            }
        }
        const technicalAssets = records(payload.assets);
        if (technicalAssets) {
            for (const asset of technicalAssets) mergeAssetEntry(assets, asset.asset_id, {});
        }
        mergeAssetEntry(assets, payload.asset_id, {});
    }
    if (isRecord(target) && target.kind === 'asset') mergeAssetEntry(assets, target.asset_id, {});
    if (isRecord(target) && target.kind === 'broker') mergeBrokerEntry(brokers, target.broker_id, undefined);

    const sortedAssets = [...assets.values()].sort((left, right) => left.assetId.localeCompare(right.assetId, undefined, {numeric: true}));
    const sortedBrokers = [...brokers.values()].sort((left, right) => left.brokerId.localeCompare(right.brokerId, undefined, {numeric: true}));
    const assetRefById = new Map(sortedAssets.map((asset, index) => [asset.assetId, `A${index + 1}`]));
    const brokerRefById = new Map(sortedBrokers.map((broker, index) => [broker.brokerId, `B${index + 1}`]));
    const providedFxPairs = isRecord(providedDirectory) ? records(providedDirectory.fx_pairs) : undefined;
    const fxPair = providedFxPairs?.[0] ?? (isRecord(target) && target.kind === 'fx_pair' ? target : undefined);
    const fxRef = fxPair ? 'FX1' : undefined;
    const blocks = ['ENTITY DIRECTORY', 'Use refs only to join tables. In user-facing prose use display_name, a clear shortened name, broker name, or FX pair label.'];
    if (sortedAssets.length) {
        const optionalColumns = [
            ['ticker', (asset: AssetDirectoryEntry) => asset.ticker],
            ['isin', (asset: AssetDirectoryEntry) => asset.isin],
            ['cusip', (asset: AssetDirectoryEntry) => asset.cusip],
            ['sedol', (asset: AssetDirectoryEntry) => asset.sedol],
            ['figi', (asset: AssetDirectoryEntry) => asset.figi],
            ['other', (asset: AssetDirectoryEntry) => asset.other],
            ['currency', (asset: AssetDirectoryEntry) => asset.currency],
            ['asset_type', (asset: AssetDirectoryEntry) => asset.assetType],
            ['quote_base_quantity', (asset: AssetDirectoryEntry) => asset.quoteBaseQuantity],
        ] as const;
        const includedColumns = optionalColumns.filter(([, getter]) =>
            sortedAssets.some((asset) => {
                const value = getter(asset);
                return value !== undefined && value !== null && value !== '' && (!Array.isArray(value) || value.length > 0);
            }),
        );
        blocks.push(
            'ASSETS',
            pipeTable(
                ['ref', 'display_name', ...includedColumns.map(([name]) => name)],
                sortedAssets.map((asset) => [assetRefById.get(asset.assetId), asset.displayName ?? 'unavailable', ...includedColumns.map(([, getter]) => getter(asset))]),
            ),
        );
        if (sortedAssets.some((asset) => Number(asset.quoteBaseQuantity) > 1)) {
            blocks.push('PRICE NORMALIZATION', 'Market quotes may be published per N units. Position unit prices are normalized to one unit.');
        }
    }
    if (sortedBrokers.length) {
        blocks.push(
            'BROKERS',
            pipeTable(
                ['ref', 'display_name'],
                sortedBrokers.map((broker) => [brokerRefById.get(broker.brokerId), broker.name ?? 'unavailable']),
            ),
        );
    }
    if (fxRef && fxPair) {
        blocks.push('FX PAIRS', pipeTable(['ref', 'display_name', 'base_currency', 'quote_currency'], [[fxRef, `${scalar(fxPair.base_currency)}/${scalar(fxPair.quote_currency)}`, fxPair.base_currency, fxPair.quote_currency]]));
    }
    blocks.push('');
    return {
        assetRefById,
        brokerRefById,
        fxRef,
        content: blocks.join('\n'),
    };
}

function assetRef(assetId: unknown, directory: EntityDirectory): string {
    if (assetId === undefined) return '';
    if (assetId === null) return 'null';
    const key = scalar(assetId);
    return directory.assetRefById.get(key) ?? `asset_unmapped:${key}`;
}

function brokerRef(brokerId: unknown, directory: EntityDirectory): string {
    if (brokerId === undefined) return '';
    if (brokerId === null) return 'null';
    const key = scalar(brokerId);
    return directory.brokerRefById.get(key) ?? `broker_unmapped:${key}`;
}

function eventEntityRef(entityId: unknown, assetId: unknown, directory: EntityDirectory): string {
    if (assetId !== undefined && assetId !== null) return assetRef(assetId, directory);
    const value = scalar(entityId);
    const assetMatch = /^asset:(.+)$/.exec(value);
    if (assetMatch) return assetRef(assetMatch[1], directory);
    if (value.startsWith('fx:') && directory.fxRef) return directory.fxRef;
    return value;
}

function componentHeader(section: JsonRecord): string {
    return `COMPONENT ${scalar(section.component_id)}`;
}

function targetEntity(target: unknown, directory: EntityDirectory): string {
    if (!isRecord(target)) return 'target';
    if (target.kind === 'asset') return assetRef(target.asset_id, directory);
    if (target.kind === 'fx_pair') return directory.fxRef ?? `${scalar(target.base_currency)}/${scalar(target.quote_currency)}`;
    if (target.kind === 'broker') return brokerRef(target.broker_id, directory);
    return scalar(target.kind) || 'target';
}

function technicalSeries(payload: JsonRecord, directory: EntityDirectory): {readonly entity: string; readonly portfolioWeightRatio: unknown; readonly values: JsonRecord}[] | undefined {
    const assets = records(payload.assets);
    if (assets) {
        return assets.map((asset) => ({
            entity: assetRef(asset.asset_id, directory),
            portfolioWeightRatio: asset.portfolio_weight_ratio,
            values: asset,
        }));
    }
    if (records(payload.buckets)) {
        const entity = payload.asset_id !== undefined ? assetRef(payload.asset_id, directory) : payload.base_currency !== undefined ? (directory.fxRef ?? `${scalar(payload.base_currency)}/${scalar(payload.quote_currency)}`) : 'target';
        return [{entity, portfolioWeightRatio: undefined, values: payload}];
    }
    return undefined;
}

function renderContinuousSeries(payload: JsonRecord, directory: EntityDirectory, diagnostics: MutableSnapshotFormatDiagnostics): string | undefined {
    const series = technicalSeries(payload, directory);
    if (!series) return undefined;
    const summaryRows = series.map(({entity, portfolioWeightRatio, values}) => [entity, normalizedRatioPercent(portfolioWeightRatio, diagnostics), values.currency ?? values.quote_currency, values.latest_close ?? values.latest_rate, values.latest_date]);
    const bucketRows: unknown[][] = [];
    for (const {entity, values} of series) {
        const buckets = records(values.buckets);
        if (!buckets) return undefined;
        for (const bucket of buckets) {
            if (Number(bucket.observation_count) === 0) {
                diagnostics.empty_temporal_rows_omitted += 1;
                continue;
            }
            bucketRows.push([
                entity,
                bucket.start_date,
                bucket.end_date,
                bucket.calendar_days,
                bucket.observation_count,
                valueMap(bucket.first, undefined, diagnostics),
                valueMap(bucket.last, undefined, diagnostics),
                valueMap(bucket.minimum, undefined, diagnostics),
                bucket.minimum_date,
                valueMap(bucket.maximum, undefined, diagnostics),
                bucket.maximum_date,
                bucket.return_start_date,
                bucket.simple_return,
                bucket.volatility,
            ]);
        }
    }
    const globalRows = [
        ['considered_asset_count', payload.considered_asset_count],
        ['eligible_asset_count', payload.eligible_asset_count],
        ['base_currency', payload.base_currency],
        ['quote_currency', payload.quote_currency],
    ].filter((row) => row[1] !== undefined);
    return [
        ...(globalRows.length ? ['SUMMARY', pipeTable(['field', 'value'], globalRows, diagnostics)] : []),
        'SERIES',
        pipeTable(['entity', 'portfolio_weight_percent', 'currency', 'latest_value', 'latest_date'], summaryRows, diagnostics),
        'BUCKETS',
        pipeTable(['entity', 'start', 'end', 'days', 'obs', 'first', 'last', 'min', 'min_date', 'max', 'max_date', 'return_from', 'simple_return', 'volatility'], bucketRows, diagnostics),
    ].join('\n');
}

interface IndicatorEntity {
    readonly entity: string;
    readonly indicators: readonly JsonRecord[];
}

function indicatorEntities(payload: JsonRecord, target: unknown, directory: EntityDirectory): IndicatorEntity[] | undefined {
    const assets = records(payload.assets);
    if (assets) {
        const entities: IndicatorEntity[] = [];
        for (const asset of assets) {
            const indicators = records(asset.indicators);
            if (!indicators) return undefined;
            entities.push({
                entity: assetRef(asset.asset_id, directory),
                indicators,
            });
        }
        return entities;
    }
    const indicators = records(payload.indicators);
    return indicators
        ? [
              {
                  entity: targetEntity(target, directory),
                  indicators,
              },
          ]
        : undefined;
}

function signalDefinition(indicator: JsonRecord): JsonRecord {
    return {
        signal_code: indicator.signal_code,
        semantic_id: indicator.semantic_id,
        semantic_description: indicator.semantic_description,
        category: indicator.category,
    };
}

function indicatorInstanceDefinition(indicator: JsonRecord): unknown {
    const columns = records(indicator.columns);
    if (!columns) return undefined;
    return {
        instance_id: indicator.instance_id,
        temporal_class: indicator.temporal_class,
        columns: columns.map(({latest: _latest, ...column}) => column),
    };
}

function outputNumberSemantics(column: JsonRecord): PromptNumberSemantics {
    return {
        minimum: typeof column.minimum === 'number' ? column.minimum : undefined,
        maximum: typeof column.maximum === 'number' ? column.maximum : undefined,
    };
}

function renderIndicators(componentId: string, payload: JsonRecord, target: unknown, directory: EntityDirectory, samplingByInstance: ReadonlyMap<string, IndicatorSampling>, signalMetrics: SnapshotSignalMetric[], diagnostics: MutableSnapshotFormatDiagnostics): string | undefined {
    const entities = indicatorEntities(payload, target, directory);
    if (!entities) return undefined;
    const bySignal = new Map<
        string,
        {
            readonly definition: JsonRecord;
            readonly signature: string;
            readonly instances: Map<
                string,
                {
                    readonly definition: JsonRecord;
                    readonly signature: string;
                    readonly entities: {
                        readonly entity: string;
                        readonly portfolioWeightRatio: unknown;
                        readonly technicalNormalizedWeightRatio: unknown;
                        readonly indicator: JsonRecord;
                    }[];
                }
            >;
        }
    >();
    for (const entity of entities) {
        for (const indicator of entity.indicators) {
            const signalCode = scalar(indicator.signal_code);
            const instanceId = scalar(indicator.instance_id);
            const definition = signalDefinition(indicator);
            const signature = JSON.stringify(normalizeJsonSafeValue(definition));
            let signal = bySignal.get(signalCode);
            if (signal && signal.signature !== signature) return undefined;
            if (!signal) {
                signal = {
                    definition,
                    signature,
                    instances: new Map(),
                };
                bySignal.set(signalCode, signal);
            }
            const instanceDefinition = indicatorInstanceDefinition(indicator);
            if (!isRecord(instanceDefinition)) return undefined;
            const instanceSignature = JSON.stringify(normalizeJsonSafeValue(instanceDefinition));
            const existingInstance = signal.instances.get(instanceId);
            if (existingInstance && existingInstance.signature !== instanceSignature) return undefined;
            if (existingInstance)
                existingInstance.entities.push({
                    entity: entity.entity,
                    portfolioWeightRatio: indicator.portfolio_weight_ratio,
                    technicalNormalizedWeightRatio: indicator.technical_normalized_weight_ratio,
                    indicator,
                });
            else {
                signal.instances.set(instanceId, {
                    definition: instanceDefinition,
                    signature: instanceSignature,
                    entities: [
                        {
                            entity: entity.entity,
                            portfolioWeightRatio: indicator.portfolio_weight_ratio,
                            technicalNormalizedWeightRatio: indicator.technical_normalized_weight_ratio,
                            indicator,
                        },
                    ],
                });
            }
        }
    }

    const instanceCount = [...bySignal.values()].reduce((total, signal) => total + signal.instances.size, 0);
    const globalRows = [
        ['considered_asset_count', payload.considered_asset_count],
        ['eligible_asset_count', payload.eligible_asset_count],
        ['covered_asset_count', payload.covered_asset_count],
        ['eligible_portfolio_weight_percent', normalizedRatioPercent(payload.eligible_portfolio_weight_ratio, diagnostics)],
        ['covered_portfolio_weight_percent', normalizedRatioPercent(payload.covered_portfolio_weight_ratio, diagnostics)],
        ['covered_weight_ratio_percent', normalizedRatioPercent(payload.covered_weight_ratio, diagnostics)],
        ['entity_count', entities.length > 1 ? entities.length : undefined],
        ['signal_count', bySignal.size],
        ['signal_instance_count', instanceCount],
    ].filter((row) => row[1] !== undefined);
    const blocks: string[] = [];
    if (globalRows.length) blocks.push('SUMMARY', pipeTable(['field', 'value'], globalRows, diagnostics));
    if (payload.covered_asset_count !== undefined) {
        blocks.push('WEIGHT SEMANTICS', "portfolio_weight_percent and *_portfolio_weight_percent use gross absolute open-position market value. technical_normalized_weight_percent sums to 100% across each signal instance's covered technical universe.");
    }

    let signalIndex = 0;
    for (const signal of bySignal.values()) {
        signalIndex += 1;
        const definition = signal.definition;
        const outputDefinitions = new Map<string, {readonly column: JsonRecord; readonly instances: string[]}>();
        for (const [instanceId, instance] of signal.instances) {
            const columns = records(instance.definition.columns);
            if (!columns) return undefined;
            for (const column of columns) {
                const outputSignature = JSON.stringify(normalizeJsonSafeValue(column));
                const existing = outputDefinitions.get(outputSignature);
                if (existing) existing.instances.push(instanceId);
                else outputDefinitions.set(outputSignature, {column, instances: [instanceId]});
            }
        }
        const instanceEntries = [...signal.instances.entries()];
        const includeEntityCount = instanceEntries.some(([, instance]) => instance.entities.length > 1);
        const definitionBlock = [
            `SIGNAL ${signalIndex}`,
            pipeTable(['signal_code', 'category', 'semantic_id', 'semantic_description', 'instance_count'], [[definition.signal_code, definition.category, definition.semantic_id, definition.semantic_description, signal.instances.size]], diagnostics),
            'INSTANCES',
            pipeTable(
                ['instance_id', 'temporal_class', 'bucket_count', ...(includeEntityCount ? ['entity_count'] : [])],
                instanceEntries.map(([instanceId, instance]) => {
                    const sampling = samplingByInstance.get(instanceId);
                    return [instanceId, sampling?.temporalClass ?? instance.definition.temporal_class, sampling?.bucketCount, ...(includeEntityCount ? [instance.entities.length] : [])];
                }),
                diagnostics,
            ),
            'OUTPUT DEFINITIONS',
            (() => {
                const includeBounds = [...outputDefinitions.values()].some(({column}) => column.minimum !== undefined || column.maximum !== undefined);
                return pipeTable(
                    ['instances', 'column_key', 'output_key', 'component', 'unit', 'kind', 'aggregation_profile', ...(includeBounds ? ['minimum', 'maximum'] : []), 'semantic_id', 'semantic_description'],
                    [...outputDefinitions.values()].map(({column, instances}) => [
                        instances.join(','),
                        column.column_key,
                        column.output_key,
                        column.component,
                        column.unit,
                        column.kind,
                        column.aggregation_profile,
                        ...(includeBounds ? [column.minimum, column.maximum] : []),
                        column.semantic_id,
                        column.semantic_description,
                    ]),
                    diagnostics,
                );
            })(),
        ].join('\n');
        blocks.push(definitionBlock);
        let summaryChars = 0;
        let historyChars = 0;
        let historyRowCount = 0;
        for (const [instanceId, instance] of signal.instances) {
            const columns = records(instance.definition.columns);
            if (!columns) return undefined;
            const columnKeys = columns.map((column) => scalar(column.column_key));
            const summaryRows: unknown[][] = [];
            const historyRows: unknown[][] = [];
            for (const entity of instance.entities) {
                const indicatorColumns = records(entity.indicator.columns);
                const periodSummary = isRecord(entity.indicator.period_summary) ? entity.indicator.period_summary : undefined;
                const rows = records(entity.indicator.rows);
                if (!indicatorColumns || !periodSummary || !rows) return undefined;
                const latestByColumn = new Map(indicatorColumns.map((column) => [scalar(column.column_key), column.latest]));
                const columnByKey = new Map(indicatorColumns.map((column) => [scalar(column.column_key), column]));
                for (const columnKey of columnKeys) {
                    const semantics = outputNumberSemantics(columnByKey.get(columnKey) ?? {});
                    summaryRows.push([
                        entity.entity,
                        normalizedRatioPercent(entity.portfolioWeightRatio, diagnostics),
                        normalizedRatioPercent(entity.technicalNormalizedWeightRatio, diagnostics),
                        columnKey,
                        datedValue(latestByColumn.get(columnKey), semantics, diagnostics),
                        indicatorCell(periodSummary[columnKey], semantics, diagnostics),
                    ]);
                }
                for (const row of rows) {
                    if (Number(row.observation_count) === 0) {
                        diagnostics.empty_temporal_rows_omitted += 1;
                        continue;
                    }
                    const cells = isRecord(row.cells) ? row.cells : undefined;
                    if (!cells) return undefined;
                    historyRows.push([entity.entity, row.start_date, row.end_date, row.calendar_days, row.observation_count, ...columnKeys.map((columnKey) => indicatorCell(cells[columnKey], outputNumberSemantics(columnByKey.get(columnKey) ?? {}), diagnostics))]);
                }
            }
            const summaryBlock = [`INSTANCE ${instanceId}`, 'PERIOD SUMMARY', pipeTable(['entity', 'portfolio_weight_percent', 'technical_normalized_weight_percent', 'column_key', 'latest', 'period_summary'], summaryRows, diagnostics)].join('\n');
            const historyBlock = ['HISTORY', pipeTable(['entity', 'start', 'end', 'days', 'obs', ...columnKeys], historyRows, diagnostics)].join('\n');
            summaryChars += summaryBlock.length;
            historyChars += historyBlock.length;
            historyRowCount += historyRows.length;
            blocks.push(summaryBlock, historyBlock);
        }
        signalMetrics.push({
            component_id: componentId,
            kind: 'indicator',
            signal_code: scalar(definition.signal_code),
            instance_count: signal.instances.size,
            history_row_count: historyRowCount,
            history_chars: historyChars,
            event_count: 0,
            event_chars: 0,
            definition_chars: definitionBlock.length,
            summary_chars: summaryChars,
        });
    }
    return blocks.join('\n');
}

function renderEvents(componentId: string, payload: JsonRecord, directory: EntityDirectory, signalMetrics: SnapshotSignalMetric[], diagnostics: MutableSnapshotFormatDiagnostics): string | undefined {
    const buckets = records(payload.buckets);
    const summaries = records(payload.selection_summaries);
    if (!buckets || !summaries) return undefined;
    const bucketRows: unknown[][] = [];
    const signalGroups = new Map<
        string,
        {
            readonly definitions: Map<string, {readonly id: string; readonly event: JsonRecord}>;
            readonly events: unknown[][];
            readonly annotationKeys: Set<string>;
        }
    >();
    const signalByAnnotation = new Map<string, string>();
    let definitionIndex = 0;
    for (const [bucketIndex, bucket] of buckets.entries()) {
        const events = records(bucket.events);
        if (!events) return undefined;
        const bucketId = bucketIndex + 1;
        if (Number(bucket.event_count) > 0) bucketRows.push([bucketId, bucket.start_date, bucket.end_date, bucket.calendar_days, bucket.event_count]);
        for (const event of events) {
            const signalCode = scalar(event.signal_code);
            const annotationKey = scalar(event.key);
            const definitionSignature = JSON.stringify(
                normalizeJsonSafeValue({
                    annotation_key: event.key,
                    annotation_type: event.annotation_type,
                    semantic_description: event.semantic_description,
                }),
            );
            let group = signalGroups.get(signalCode);
            if (!group) {
                group = {definitions: new Map(), events: [], annotationKeys: new Set()};
                signalGroups.set(signalCode, group);
            }
            let definition = group.definitions.get(definitionSignature);
            if (!definition) {
                definitionIndex += 1;
                definition = {id: `event_definition_${definitionIndex}`, event};
                group.definitions.set(definitionSignature, definition);
            }
            group.annotationKeys.add(annotationKey);
            signalByAnnotation.set(annotationKey, signalCode);
            group.events.push([bucketId, definition.id, eventEntityRef(event.entity_id, event.asset_id, directory), event.date, event.key, event.direction, valueMap(event.values, isRecord(event.value_bounds) ? event.value_bounds : undefined, diagnostics)]);
        }
    }
    for (const summary of summaries) {
        const annotationKey = scalar(summary.annotation_key);
        if (!signalByAnnotation.has(annotationKey)) signalByAnnotation.set(annotationKey, 'UNKNOWN');
    }
    const summaryRows = [
        ['detected_event_count', payload.detected_event_count],
        ['exported_event_count', payload.exported_event_count],
        ['bucket_count', buckets.length],
        ['signal_count', signalGroups.size],
    ];
    const blocks = ['SUMMARY', pipeTable(['field', 'value'], summaryRows, diagnostics), 'BUCKETS', pipeTable(['bucket_id', 'start', 'end', 'days', 'event_count'], bucketRows, diagnostics)];
    let signalIndex = 0;
    for (const [signalCode, group] of signalGroups) {
        signalIndex += 1;
        const signalSummaries = summaries.filter((summary) => signalByAnnotation.get(scalar(summary.annotation_key)) === signalCode);
        const definitionBlock = [
            `SIGNAL EVENTS ${signalIndex}`,
            pipeTable(['signal_code'], [[signalCode]], diagnostics),
            'ANNOTATION DEFINITIONS',
            pipeTable(
                ['definition_id', 'annotation_key', 'annotation_type', 'semantic_description'],
                [...group.definitions.values()].map(({id, event}) => [id, event.key, event.annotation_type, event.semantic_description]),
                diagnostics,
            ),
        ].join('\n');
        const eventsBlock = ['EVENTS', pipeTable(['bucket_id', 'definition_id', 'entity_ref', 'date', 'annotation_key', 'direction', 'values'], group.events, diagnostics)].join('\n');
        const selectionBlock = [
            'SELECTION',
            pipeTable(
                ['entity', 'annotation_key', 'detected', 'recent_30d', 'exported', 'selection_applied', 'detected_from', 'detected_to', 'exported_from', 'exported_to', 'up', 'down'],
                signalSummaries.map((summary) => [
                    eventEntityRef(summary.entity_id, undefined, directory),
                    summary.annotation_key,
                    summary.detected_count,
                    summary.recent_30d_count,
                    summary.exported_count,
                    summary.selection_applied,
                    summary.oldest_detected_event_date,
                    summary.newest_detected_event_date,
                    summary.oldest_exported_event_date,
                    summary.newest_exported_event_date,
                    summary.upward_count,
                    summary.downward_count,
                ]),
                diagnostics,
            ),
        ].join('\n');
        blocks.push(definitionBlock, eventsBlock, selectionBlock);
        signalMetrics.push({
            component_id: componentId,
            kind: 'event',
            signal_code: signalCode,
            instance_count: 0,
            history_row_count: 0,
            history_chars: 0,
            event_count: group.events.length,
            event_chars: eventsBlock.length,
            definition_chars: definitionBlock.length,
            summary_chars: selectionBlock.length,
        });
    }
    return blocks.join('\n');
}

function renderBreadth(payload: JsonRecord, diagnostics: MutableSnapshotFormatDiagnostics): string | undefined {
    const states = records(payload.states);
    if (!states) return undefined;
    return [
        'SUMMARY',
        pipeTable(
            ['considered_asset_count', 'eligible_asset_count', 'covered_asset_count', 'eligible_portfolio_weight_percent', 'covered_portfolio_weight_percent', 'covered_weight_ratio_percent'],
            [
                [
                    payload.considered_asset_count,
                    payload.eligible_asset_count,
                    payload.covered_asset_count,
                    normalizedRatioPercent(payload.eligible_portfolio_weight_ratio, diagnostics),
                    normalizedRatioPercent(payload.covered_portfolio_weight_ratio, diagnostics),
                    normalizedRatioPercent(payload.covered_weight_ratio, diagnostics),
                ],
            ],
            diagnostics,
        ),
        'WEIGHT SEMANTICS',
        'portfolio_weight_percent and *_portfolio_weight_percent use gross absolute open-position market value. technical_normalized_weight_percent sums to 100% across each covered signal/output universe.',
        'STATES',
        pipeTable(
            ['signal_code', 'output_key', 'state', 'covered_asset_count', 'covered_portfolio_weight_percent', 'unweighted_count', 'unweighted_ratio_percent', 'technical_normalized_weight_percent'],
            states.map((state) => [
                state.signal_code,
                state.output_key,
                state.state,
                state.covered_asset_count,
                normalizedRatioPercent(state.covered_portfolio_weight_ratio, diagnostics),
                state.unweighted_count,
                normalizedRatioPercent(state.unweighted_ratio, diagnostics),
                normalizedRatioPercent(state.technical_normalized_weight_ratio, diagnostics),
            ]),
            diagnostics,
        ),
    ].join('\n');
}

const DIRECTORY_IDENTITY_FIELDS = new Set(['asset_name', 'asset_ticker', 'asset_isin', 'asset_cusip', 'asset_sedol', 'asset_figi', 'asset_other', 'asset_type', 'broker_name', 'opening_broker_name']);
const ALREADY_SCALED_PERCENT_FIELDS = new Set(['allocation_percent', 'nav_weight_percent', 'largest_position_weight_percent', 'percent']);
const NORMALIZED_RATIO_FIELDS = new Set(['weight']);
const MONETARY_RESIDUAL_FIELDS = new Set(['period_other_result', 'reconciliation_diff', 'residual']);

function finalPathKey(path: string): string {
    return path.slice(path.lastIndexOf('.') + 1);
}

function decimalTimesOneHundred(value: number | string): string {
    const raw = typeof value === 'number' ? plainDecimal(value) : value;
    if (!/^-?\d+(?:\.\d+)?$/.test(raw)) return raw;
    const negative = raw.startsWith('-');
    const unsigned = negative ? raw.slice(1) : raw;
    const [integer, fraction = ''] = unsigned.split('.');
    const digits = `${integer}${fraction}`;
    const decimalIndex = integer.length + 2;
    const expanded = decimalIndex >= digits.length ? `${digits}${'0'.repeat(decimalIndex - digits.length)}` : decimalIndex <= 0 ? `0.${'0'.repeat(-decimalIndex)}${digits}` : `${digits.slice(0, decimalIndex)}.${digits.slice(decimalIndex)}`;
    return `${negative ? '-' : ''}${expanded}`;
}

function normalizedRatioPercent(value: unknown, diagnostics: MutableSnapshotFormatDiagnostics): string | undefined {
    if (value === undefined) return undefined;
    if (value === null) return 'null';
    if (typeof value !== 'number' && (typeof value !== 'string' || !/^-?\d+(?:\.\d+)?$/.test(value))) return scalar(value);
    diagnostics.normalized_ratio_percent_values += 1;
    return `${formatPromptNumberWithDiagnostics(decimalTimesOneHundred(value), {}, diagnostics)}%`;
}

function percentageValue(path: string, value: unknown, diagnostics: MutableSnapshotFormatDiagnostics): string | undefined {
    const key = finalPathKey(path);
    const normalizedRatio = NORMALIZED_RATIO_FIELDS.has(key);
    if (!normalizedRatio && key !== 'percent' && !key.endsWith('_percent')) return undefined;
    if (value === null || value === undefined) return scalar(value);
    if (typeof value !== 'number' && (typeof value !== 'string' || !/^-?\d+(?:\.\d+)?$/.test(value))) return scalar(value);
    const alreadyScaled = ALREADY_SCALED_PERCENT_FIELDS.has(key);
    if (alreadyScaled) diagnostics.already_scaled_percent_values += 1;
    else diagnostics.normalized_ratio_percent_values += 1;
    const percent = alreadyScaled ? value : decimalTimesOneHundred(value);
    return `${formatPromptNumberWithDiagnostics(percent, {}, diagnostics)}%`;
}

function genericFieldName(path: string): string {
    const key = finalPathKey(path);
    if (key === 'asset_id' || key.endsWith('_asset_id')) return `${path.slice(0, -2)}ref`;
    if (key === 'broker_id' || key.endsWith('_broker_id')) return `${path.slice(0, -2)}ref`;
    if (path === 'entity_id' || path.endsWith('.entity_id')) return `${path.slice(0, -2)}ref`;
    if (key === 'weight') return `${path.slice(0, -key.length)}weight_percent`;
    return path;
}

function isMonetaryResidualPath(path: string): boolean {
    const segments = path.split('.');
    return segments.some((segment) => MONETARY_RESIDUAL_FIELDS.has(segment));
}

function genericLeaf(path: string, value: unknown, directory: EntityDirectory, diagnostics: MutableSnapshotFormatDiagnostics, semantics: PromptNumberSemantics = {}): string {
    const key = finalPathKey(path);
    if (key === 'asset_id' || key.endsWith('_asset_id')) return assetRef(value, directory);
    if (key === 'broker_id' || key.endsWith('_broker_id')) return brokerRef(value, directory);
    if (path === 'entity_id' || path.endsWith('.entity_id')) return eventEntityRef(value, undefined, directory);
    const percentage = percentageValue(path, value, diagnostics);
    if (percentage !== undefined) return percentage;
    if (typeof value === 'number' && Number.isFinite(value)) return formatPromptNumberWithDiagnostics(value, semantics, diagnostics);
    if (typeof value === 'string' && /^-?\d+(?:\.\d+)?$/.test(value)) return formatPromptNumberWithDiagnostics(value, semantics, diagnostics);
    return scalar(value);
}

function publicStructuredValue(value: unknown, path: string, directory: EntityDirectory, diagnostics: MutableSnapshotFormatDiagnostics): unknown {
    if (Array.isArray(value)) {
        if (path.endsWith('broker_ids') || path.endsWith('broker_scope')) return value.map((item) => brokerRef(item, directory));
        if (path.endsWith('asset_ids')) return value.map((item) => assetRef(item, directory));
        return value.map((item) => publicStructuredValue(item, path, directory, diagnostics));
    }
    if (isRecord(value)) {
        const currencyCode = typeof value.code === 'string' ? value.code : undefined;
        return Object.fromEntries(
            Object.entries(value).map(([key, nested]) => {
                const nestedPath = path ? `${path}.${key}` : key;
                const semantics = key === 'amount' && currencyCode && isMonetaryResidualPath(path) ? {monetaryResidualCurrency: currencyCode} : {};
                const rendered = Array.isArray(nested) || isRecord(nested) ? publicStructuredValue(nested, nestedPath, directory, diagnostics) : genericLeaf(nestedPath, nested, directory, diagnostics, semantics);
                return [genericFieldName(nestedPath).slice(path ? path.length + 1 : 0), rendered];
            }),
        );
    }
    return genericLeaf(path, value, directory, diagnostics);
}

function flattenGenericRow(value: JsonRecord, directory: EntityDirectory, diagnostics: MutableSnapshotFormatDiagnostics): Map<string, string> {
    const flattened = new Map<string, string>();
    const visit = (record: JsonRecord, prefix: string): void => {
        const currencyCode = typeof record.code === 'string' ? record.code : undefined;
        for (const [key, nested] of Object.entries(record)) {
            if (DIRECTORY_IDENTITY_FIELDS.has(key)) continue;
            const path = prefix ? `${prefix}.${key}` : key;
            if (isRecord(nested)) visit(nested, path);
            else {
                const semantics = key === 'amount' && currencyCode && isMonetaryResidualPath(prefix) ? {monetaryResidualCurrency: currencyCode} : {};
                flattened.set(genericFieldName(path), Array.isArray(nested) ? JSON.stringify(normalizeJsonSafeValue(publicStructuredValue(nested, path, directory, diagnostics))) : genericLeaf(path, nested, directory, diagnostics, semantics));
            }
        }
    };
    visit(value, '');
    return flattened;
}

interface GenericArrayTable {
    readonly path: string;
    readonly values: readonly unknown[];
}

function isEmptyPublicCell(value: string | undefined): boolean {
    return value === undefined || value === '' || value === 'null';
}

function renderGenericPayload(payload: JsonRecord, directory: EntityDirectory, diagnostics: MutableSnapshotFormatDiagnostics): string {
    const summaryRows: unknown[][] = [];
    const arrays: GenericArrayTable[] = [];
    const visit = (record: JsonRecord, prefix: string): void => {
        const currencyCode = typeof record.code === 'string' ? record.code : undefined;
        for (const [key, nested] of Object.entries(record)) {
            if (DIRECTORY_IDENTITY_FIELDS.has(key)) continue;
            const path = prefix ? `${prefix}.${key}` : key;
            if (Array.isArray(nested)) {
                if (nested.length === 0) summaryRows.push([genericFieldName(path), '[]']);
                else arrays.push({path, values: nested});
            } else if (isRecord(nested)) visit(nested, path);
            else {
                const semantics = key === 'amount' && currencyCode && isMonetaryResidualPath(prefix) ? {monetaryResidualCurrency: currencyCode} : {};
                summaryRows.push([genericFieldName(path), genericLeaf(path, nested, directory, diagnostics, semantics)]);
            }
        }
    };
    visit(payload, '');

    const blocks: string[] = [];
    if (summaryRows.length) blocks.push('SUMMARY', pipeTable(['field', 'value'], summaryRows, diagnostics));
    for (const array of arrays) {
        const rowRecords = records(array.values);
        if (!rowRecords) {
            blocks.push(
                `TABLE ${array.path}`,
                pipeTable(
                    ['row', 'value'],
                    array.values.map((value, index) => [index + 1, Array.isArray(value) || isRecord(value) ? JSON.stringify(normalizeJsonSafeValue(publicStructuredValue(value, array.path, directory, diagnostics))) : genericLeaf(array.path, value, directory, diagnostics)]),
                    diagnostics,
                ),
            );
            continue;
        }
        const flattenedRows = rowRecords.map((row) => flattenGenericRow(row, directory, diagnostics));
        const discoveredColumns: string[] = [];
        const seen = new Set<string>();
        for (const row of flattenedRows) {
            for (const column of row.keys()) {
                if (seen.has(column)) continue;
                seen.add(column);
                discoveredColumns.push(column);
            }
        }
        const columns = discoveredColumns.filter((column) => flattenedRows.some((row) => !isEmptyPublicCell(row.get(column))));
        const removedColumns = discoveredColumns.filter((column) => !columns.includes(column));
        diagnostics.empty_columns_removed += removedColumns.length;
        diagnostics.empty_parent_columns_removed += removedColumns.filter((column) => discoveredColumns.some((candidate) => candidate.startsWith(`${column}.`))).length;
        blocks.push(
            `TABLE ${array.path}`,
            pipeTable(
                ['row', ...columns],
                flattenedRows.map((row, index) => [index + 1, ...columns.map((column) => row.get(column) ?? 'null')]),
                diagnostics,
            ),
        );
    }
    return blocks.length ? blocks.join('\n') : 'SUMMARY\n|field|value|\n|payload|{}|';
}

function technicalPayload(
    componentId: string,
    payload: JsonRecord,
    target: unknown,
    directory: EntityDirectory,
    samplingByInstance: ReadonlyMap<string, IndicatorSampling>,
    signalMetrics: SnapshotSignalMetric[],
    diagnostics: MutableSnapshotFormatDiagnostics,
): {readonly format: string; readonly content: string} | undefined {
    if (componentId.endsWith('.indicators') || componentId.includes('technical_indicators')) {
        const content = renderIndicators(componentId, payload, target, directory, samplingByInstance, signalMetrics, diagnostics);
        return content ? {format: 'signal_tables_v1', content} : undefined;
    }
    if (componentId.includes('technical_events') || componentId.endsWith('.states_events')) {
        const content = renderEvents(componentId, payload, directory, signalMetrics, diagnostics);
        return content ? {format: 'signal_event_tables_v1', content} : undefined;
    }
    if (componentId.includes('technical_breadth')) {
        const content = renderBreadth(payload, diagnostics);
        return content ? {format: 'breadth_tables_v1', content} : undefined;
    }
    if (componentId.includes('technical_prices') || componentId.endsWith('.ohlc_returns') || componentId.endsWith('.rate_ohlc') || componentId.endsWith('.returns_volatility')) {
        const content = renderContinuousSeries(payload, directory, diagnostics);
        return content ? {format: 'time_series_tables_v1', content} : undefined;
    }
    return undefined;
}

function renderComponent(section: JsonRecord, target: unknown, directory: EntityDirectory, samplingByInstance: ReadonlyMap<string, IndicatorSampling>, signalMetrics: SnapshotSignalMetric[], diagnostics: MutableSnapshotFormatDiagnostics): string {
    const componentId = scalar(section.component_id);
    const payload = isRecord(section.payload) ? section.payload : undefined;
    const compactVersion = section.component_version === 1 && section.schema_version === 1;
    const technical = compactVersion && payload ? technicalPayload(componentId, payload, target, directory, samplingByInstance, signalMetrics, diagnostics) : undefined;
    if (technical) return `${componentHeader(section)}\n${technical.content}`;
    if (compactVersion && payload) return `${componentHeader(section)}\n${renderGenericPayload(payload, directory, diagnostics)}`;
    return `${componentHeader(section)}\nPAYLOAD YAML FALLBACK\n${serializeYaml({payload: section.payload})}`;
}

export function renderSnapshotDataText(sectionsValue: unknown, target: unknown, entityDirectory?: unknown, technicalSampling?: unknown): RenderedSnapshotDataText {
    const sections = records(sectionsValue);
    if (!sections) throw new TypeError('AI Export snapshot sections must be an array of objects');
    const directory = collectDirectories(sections, target, entityDirectory);
    const signalMetrics: SnapshotSignalMetric[] = [];
    const formatDiagnostics = createFormatDiagnostics();
    const samplingByInstance = new Map<string, IndicatorSampling>();
    if (isRecord(technicalSampling)) {
        for (const policy of records(technicalSampling.indicator_policies) ?? []) {
            samplingByInstance.set(scalar(policy.signal_instance_id), {
                temporalClass: policy.temporal_class,
                bucketCount: policy.bucket_count,
            });
        }
    }
    const preamble = formatPreamble(sections);
    const wrapper = `${preamble}${directory.content}`;
    const blocks = sections.map((section, index) => ({
        id: scalar(section.component_id),
        content: `${renderComponent(section, target, directory, samplingByInstance, signalMetrics, formatDiagnostics)}${index < sections.length - 1 ? COMPONENT_SEPARATOR : ''}`,
    }));
    return {
        content: `${wrapper}${blocks.map((block) => block.content).join('')}`,
        blocks,
        wrapper,
        formatPreamble: preamble,
        entityDirectory: directory.content,
        signalMetrics,
        formatDiagnostics,
    };
}
