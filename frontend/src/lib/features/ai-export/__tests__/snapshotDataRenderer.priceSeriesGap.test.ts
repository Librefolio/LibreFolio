import {describe, expect, it} from 'vitest';

// E-AI503, E-23: the meaning maps are read by name through the namespace (`Reflect.get`), so while one is missing or lacks a key only the tests reading it fail, and the file type-checks before the cure and after it.
import * as renderer from '../templates/snapshotDataRenderer';
import {renderSnapshotDataText} from '../templates/snapshotDataRenderer';

/**
 * E-AI503 (developer's decisions, 19/10): an eligible held asset with no technical price series — no price stored up to
 * the period end, or stored prices in more than one currency — failed the whole AI Export with a 503. The backend now
 * reports it, and the prompt says why, asset by asset. The criterion is the price points the database returns, never the
 * asset type: the renderer never sees a type here, so the fixtures carry none.
 *
 * - `portfolio.technical_prices` / `broker.technical_prices` v2 (schema 1) carry `uncovered_assets`, one row per eligible
 *   asset without a series (`asset_id`, `portfolio_weight_ratio`, `reason_code`), never in `assets`. Right after the
 *   SERIES table the renderer prints the title `ASSETS WITHOUT PRICE SERIES`, a table of those assets by prompt ref, then
 *   one `<code>=<meaning>` line per distinct code, sorted by code; then BUCKETS.
 * - `asset.ohlc_returns` v2 (schema 1) may carry a null `currency` and a `reason_code`, every bucket then empty: SUMMARY
 *   gains a `reason_code` row right after `price_basis`, the `<code>=<meaning>` line follows the SUMMARY table, and the
 *   null currency is named on the `omitted_null_columns=` line after SERIES (T-B7).
 * - The meanings live in a local allow-list, `PRICE_SERIES_GAP_MEANINGS`: the frontend never takes presentation text from
 *   the backend. An unknown code, or an `uncovered_assets` that is not an array of records, sends the section to the
 *   generic renderer, with no sentence invented for it.
 * - Without a gap a v2 section renders byte for byte as its v1. v3 still falls back to YAML, and so do the FX series at
 *   v2, which E-AI503 leaves at v1 (E-23 then adds `fx.rate_ohlc` v2, below).
 *
 * E-23 (developer's decisions, 20/10; contract E-23.2, items 3 and 6): a run of whole buckets with no observed price while
 * markets were open is a gap, which the backend merges into one record: `start_date`, `end_date`, `calendar_days`, and
 * `last_value` with `last_value_date`, the last value stored before the gap, both null when the history begins inside the
 * period. The records are in `price_gaps` of each `assets` row of `*.technical_prices` v2 and of `asset.ohlc_returns` v2
 * (no new version: both v2s are unreleased), and in `rate_gaps` of `fx.rate_ohlc` v2, a version E-23 makes compact. An
 * absent or empty list is no gap.
 * - After the BUCKETS table, only when there is a gap: the title `PRICE GAPS` (`RATE GAPS` for an FX pair), one row per gap
 *   (`entity|from|to|days|last_price|last_price_date`, `last_rate|last_rate_date` for a pair; entities in series order, an
 *   entity's gaps in payload order, which the backend keeps by date), then ONE `price_gap=` (`rate_gap=`) meaning line from
 *   a new local map, `SERIES_GAP_MEANINGS`. BUCKETS keeps only the buckets with an observation.
 * - A gap with no value stored before it has empty last-value cells, never `null`: the renderer passes them as `undefined`,
 *   so when no gap has one the two columns go silently, with no `omitted_null_columns=` line.
 * - A third reason code, `no_price_in_period` (prices stored, none observed inside the period), joins
 *   `PRICE_SERIES_GAP_MEANINGS`. `ASSETS WITHOUT PRICE SERIES` gains `currency|last_price|last_price_date`, filled only on
 *   the rows of that code (from the backend's `currency`, `last_close`, `last_close_date`) and `undefined` on the others:
 *   with the two E-AI503 codes alone the table is the E-AI503 one, byte for byte, whatever nulls the backend writes there.
 * - A gap list or record the renderer does not know sends the section to the generic renderer, as an unknown code does.
 *
 * No meaning sentence is frozen here: the developer approves their wording later, so every test reads them from the
 * renderer's own maps. Titles, headers and keys are format and are asserted; cells are read by column header, rows found
 * by what they hold.
 *
 * Today (base `1ef19d8dc`, E-AI503 merged) PSG-01 to PSG-07 and PSG-09 are green, and so are PSG-18 and the three price
 * rows of PSG-19: they guard that a payload without a gap, or with the E-AI503 codes only, renders as before, and must stay
 * green. PSG-08, PSG-10 to PSG-17, PSG-20 and the `fx.rate_ohlc` row of PSG-19 are red until E-23: the map has two codes,
 * `SERIES_GAP_MEANINGS` does not exist, `no_price_in_period` is an unknown code, gap lists are ignored, and `fx.rate_ohlc`
 * v2 falls back to YAML.
 */
describe('price series gaps (E-AI503, E-23)', () => {
    /** The backend's `PriceSeriesGapReason`: the codes the renderer gives a meaning. */
    type PriceSeriesGapCode = 'no_stored_price' | 'mixed_price_currencies' | 'no_price_in_period';
    /** The keys of `SERIES_GAP_MEANINGS` (E-23): the meaning of a gap in a price series, and in a rate series. */
    type SeriesGapKind = 'price_gap' | 'rate_gap';
    /** The components whose price series carry `price_gaps` (E-23). */
    type PriceComponentId = 'portfolio.technical_prices' | 'broker.technical_prices' | 'asset.ohlc_returns';
    type Rendered = ReturnType<typeof renderSnapshotDataText>;

    // Database ids no rendered cell may carry: distinctive, so a leak cannot hide among the figures.
    const FIRST_ASSET_ID = 5031;
    const SECOND_ASSET_ID = 5032;
    const THIRD_ASSET_ID = 5033;
    const BROKER_ID = 5034;
    const directory = {
        assets: [
            {asset_id: FIRST_ASSET_ID, display_name: 'First Asset'},
            {asset_id: SECOND_ASSET_ID, display_name: 'Second Asset'},
            {asset_id: THIRD_ASSET_ID, display_name: 'Third Asset'},
        ],
        brokers: [{broker_id: BROKER_ID, display_name: 'Named Broker'}],
        fx_pairs: [],
    };
    const UNCOVERED_TITLE = 'ASSETS WITHOUT PRICE SERIES';
    /** T-B7: the key of the line that names, right after a table, the columns left out because they were null in every row. */
    const NULL_COLUMNS_DECLARATION = 'omitted_null_columns=';
    /** A code this renderer does not know: a reason the backend could add after it. */
    const UNKNOWN_CODE = 'some_future_reason';
    /** A line that gives a code or a kind of gap its meaning, `<key>=…`, for every key these tests use, known or not. */
    const MEANING_LINE = /^(?:no_stored_price|mixed_price_currencies|no_price_in_period|price_gap|rate_gap|some_future_reason)=/;
    /** E-23: the titles and headers of the gap tables that follow BUCKETS, and of ASSETS WITHOUT PRICE SERIES with a last price. */
    const PRICE_GAPS_TITLE = 'PRICE GAPS';
    const RATE_GAPS_TITLE = 'RATE GAPS';
    const PRICE_GAPS_HEADER = '|entity|from|to|days|last_price|last_price_date|';
    const RATE_GAPS_HEADER = '|entity|from|to|days|last_rate|last_rate_date|';
    const UNCOVERED_HEADER_WITH_LAST_PRICE = '|entity|portfolio_weight_percent|reason_code|currency|last_price|last_price_date|';
    /** The values of a bucket with no observation, as the backend builds it: no value, no date, no return. */
    const EMPTY_BUCKET_VALUES = {first: null, minimum: null, maximum: null, last: null, observation_count: 0, minimum_date: null, maximum_date: null, return_start_date: null, simple_return: null};
    /**
     * E-23: the bucket plan of the gap fixtures, March 2026 in four spans. A series on it has one value per span, null for a
     * bucket with no observation; a gap reads the value of the span before it, on that span's last day.
     */
    const GAP_PLAN = [
        {start_date: '2026/03/01', end_date: '2026/03/08', calendar_days: 8},
        {start_date: '2026/03/09', end_date: '2026/03/15', calendar_days: 7},
        {start_date: '2026/03/16', end_date: '2026/03/23', calendar_days: 8},
        {start_date: '2026/03/24', end_date: '2026/03/31', calendar_days: 8},
    ] as const;

    function section(componentId: string, componentVersion: number, payload: Record<string, unknown>, schemaVersion = 1) {
        return {component_id: componentId, component_version: componentVersion, schema_id: componentId, schema_version: schemaVersion, payload};
    }

    /** A populated price bucket: every field the BUCKETS table reads has a value, unless `overrides` says otherwise. */
    function priceBucket(overrides: Record<string, unknown> = {}) {
        return {
            start_date: '2026/03/01',
            end_date: '2026/03/15',
            calendar_days: 15,
            first: {close: 100},
            minimum: {close: 98},
            maximum: {close: 102},
            last: {close: 101},
            observation_count: 10,
            minimum_date: '2026/03/04',
            maximum_date: '2026/03/09',
            return_start_date: '2026/02/27',
            simple_return: 0.01,
            ...overrides,
        };
    }

    /** The buckets of an asset without a series: all empty, as the backend builds them (no observation, no value). */
    function emptyPriceBuckets() {
        return [
            {start_date: '2026/03/01', end_date: '2026/03/15', calendar_days: 15, ...EMPTY_BUCKET_VALUES},
            {start_date: '2026/03/16', end_date: '2026/03/31', calendar_days: 16, ...EMPTY_BUCKET_VALUES},
        ];
    }

    /** One row of `assets`: an eligible asset with its series, keys in the backend's order. */
    function coveredAsset(assetId: number, weight: number) {
        return {asset_id: assetId, portfolio_weight_ratio: weight, currency: 'EUR', buckets: [priceBucket()], latest_close: 101, latest_date: '2026/03/31'};
    }

    /** One row of `uncovered_assets`: an eligible asset without a series, and why. */
    function uncoveredAsset(assetId: number, weight: number, reasonCode: string) {
        return {asset_id: assetId, portfolio_weight_ratio: weight, reason_code: reasonCode};
    }

    /** E-23: one row of `uncovered_assets` for an asset whose stored prices all predate the period: its currency, and its last price with the date. */
    function uncoveredBeforePeriod(assetId: number, weight: number, currency: string, lastClose: number, lastCloseDate: string) {
        return {...uncoveredAsset(assetId, weight, 'no_price_in_period'), currency, last_close: lastClose, last_close_date: lastCloseDate};
    }

    /** E-23: `row` with the three new fields as the backend writes them on a `no_stored_price` or `mixed_price_currencies` row: null. */
    function withNullLastPrice(row: Record<string, unknown>) {
        return {...row, currency: null, last_close: null, last_close_date: null};
    }

    /**
     * A `portfolio.technical_prices` / `broker.technical_prices` section. Without `uncovered` the payload has the v1 shape,
     * with no `uncovered_assets` key; the counts keep the v2 invariants: covered = `assets`, eligible = `assets` + uncovered.
     */
    function pricesSection(componentId: string, componentVersion: number, assets: readonly Record<string, unknown>[], uncovered?: readonly unknown[], schemaVersion = 1) {
        const eligible = assets.length + (uncovered?.length ?? 0);
        const payload = {
            price_basis: 'observed_close',
            assets,
            eligible_asset_count: eligible,
            period_position_leg_count: eligible,
            period_contributor_asset_count: eligible,
            covered_asset_count: assets.length,
            ...(uncovered === undefined ? {} : {uncovered_assets: uncovered}),
        };
        return section(componentId, componentVersion, payload, schemaVersion);
    }

    /** The PSG-02 book: the first asset with its series, the second with no stored price, the third with prices in two currencies. */
    function gapPricesSection(componentId: string, componentVersion: number, schemaVersion = 1) {
        return pricesSection(componentId, componentVersion, [coveredAsset(FIRST_ASSET_ID, 0.5)], [uncoveredAsset(SECOND_ASSET_ID, 0.3, 'no_stored_price'), uncoveredAsset(THIRD_ASSET_ID, 0.2, 'mixed_price_currencies')], schemaVersion);
    }

    function ohlcSection(componentVersion: number, payload: Record<string, unknown>, schemaVersion = 1) {
        return section('asset.ohlc_returns', componentVersion, payload, schemaVersion);
    }

    /** `asset.ohlc_returns` of the first asset, which has its series: the v1 payload, keys in the backend's order. */
    function pricedOhlcPayload() {
        return {asset_id: FIRST_ASSET_ID, currency: 'EUR', price_basis: 'observed_close', buckets: [priceBucket()], latest_close: 101, latest_date: '2026/03/31'};
    }

    /** `asset.ohlc_returns` of the second asset, which has no series: no currency, every bucket empty, no latest close, and why. */
    function gapOhlcPayload(reasonCode: string) {
        return {asset_id: SECOND_ASSET_ID, currency: null, price_basis: 'observed_close', buckets: emptyPriceBuckets(), latest_close: null, latest_date: null, reason_code: reasonCode};
    }

    /** A section in which every eligible asset has its series: at v1 the payload has no key for a gap, at v2 it says there is none. */
    function noGapSection(componentId: string, componentVersion: number) {
        if (componentId === 'asset.ohlc_returns') return ohlcSection(componentVersion, componentVersion === 1 ? pricedOhlcPayload() : {...pricedOhlcPayload(), reason_code: null});
        return pricesSection(componentId, componentVersion, [coveredAsset(FIRST_ASSET_ID, 1)], componentVersion === 1 ? undefined : []);
    }

    /** `fx.rate_ohlc` / `fx.returns_volatility`: the FX series, each with its own payload shape; E-23 gives `fx.rate_ohlc` a v2, `fx.returns_volatility` stays at v1. */
    function fxSection(componentId: 'fx.rate_ohlc' | 'fx.returns_volatility', componentVersion: number, schemaVersion = 1) {
        if (componentId === 'fx.rate_ohlc') {
            return section(componentId, componentVersion, {base_currency: 'USD', quote_currency: 'EUR', buckets: [priceBucket({first: {rate: 0.91}, minimum: {rate: 0.9}, maximum: {rate: 0.93}, last: {rate: 0.92}})], latest_rate: 0.92, latest_date: '2026/03/31'}, schemaVersion);
        }
        const returnBucket = {
            start_date: '2026/03/01',
            end_date: '2026/03/15',
            calendar_days: 15,
            first: {return: 0.001},
            minimum: {return: -0.002},
            maximum: {return: 0.003},
            last: {return: 0.001},
            observation_count: 10,
            volatility: 0.004,
        };
        return section(componentId, componentVersion, {base_currency: 'USD', quote_currency: 'EUR', buckets: [returnBucket]}, schemaVersion);
    }

    /** E-23: a series on GAP_PLAN, one value per span (null: a bucket with no observation): its buckets, flat at each value, and its latest value with its span's last day. */
    function plannedSeries(values: readonly (number | null)[], key: 'close' | 'rate') {
        if (values.length !== GAP_PLAN.length) throw new Error(`one value per span of GAP_PLAN, not ${values.length}`);
        const buckets = GAP_PLAN.map((span, index) => {
            const value = values[index];
            if (value === null) return {...span, ...EMPTY_BUCKET_VALUES};
            const cell = {[key]: value};
            return priceBucket({...span, first: cell, minimum: cell, maximum: cell, last: cell, minimum_date: span.start_date, maximum_date: span.end_date});
        });
        const latestIndex = values.reduce<number>((latest, value, index) => (value === null ? latest : index), -1);
        return {buckets, latest: latestIndex < 0 ? null : values[latestIndex], latestDate: latestIndex < 0 ? null : GAP_PLAN[latestIndex].end_date};
    }

    /** E-23: one gap as the backend's `SeriesGap` serializes it: a merged run of empty buckets, and the last value stored before it (null, with its date: none). */
    function seriesGap(startDate: string, endDate: string, calendarDays: number, lastValue: number | null, lastValueDate: string | null) {
        return {start_date: startDate, end_date: endDate, calendar_days: calendarDays, last_value: lastValue, last_value_date: lastValueDate};
    }

    /** E-23: one row of `assets` with its series on GAP_PLAN, `closes` per span, and its `price_gaps`, keys in the backend's order. */
    function gappedAsset(assetId: number, weight: number, closes: readonly (number | null)[], priceGaps: unknown) {
        const {buckets, latest, latestDate} = plannedSeries(closes, 'close');
        return {asset_id: assetId, portfolio_weight_ratio: weight, currency: 'EUR', buckets, latest_close: latest, latest_date: latestDate, price_gaps: priceGaps};
    }

    /** E-23: a v2 section of `componentId` in which First Asset, the only one, has its series on GAP_PLAN and `priceGaps`: a row of `assets`, or the whole `asset.ohlc_returns` payload. */
    function gappedSection(componentId: PriceComponentId, closes: readonly (number | null)[], priceGaps: unknown) {
        if (componentId !== 'asset.ohlc_returns') return pricesSection(componentId, 2, [gappedAsset(FIRST_ASSET_ID, 1, closes, priceGaps)], []);
        const {buckets, latest, latestDate} = plannedSeries(closes, 'close');
        return ohlcSection(2, {asset_id: FIRST_ASSET_ID, currency: 'EUR', reason_code: null, price_basis: 'observed_close', buckets, latest_close: latest, latest_date: latestDate, price_gaps: priceGaps});
    }

    /** E-23: `fx.rate_ohlc` v2 on GAP_PLAN: the pair's `rates` per span, and its `rate_gaps`. */
    function gappedFxSection(rates: readonly (number | null)[], rateGaps: unknown) {
        const {buckets, latest, latestDate} = plannedSeries(rates, 'rate');
        return section('fx.rate_ohlc', 2, {base_currency: 'USD', quote_currency: 'EUR', buckets, latest_rate: latest, latest_date: latestDate, rate_gaps: rateGaps});
    }

    /** E-23: a v2 section that says it has no gap (an empty `price_gaps` or `rate_gaps`, as the backend writes one), beside the v1 of the same series. */
    function emptyGapListSections(componentId: PriceComponentId | 'fx.rate_ohlc') {
        if (componentId === 'fx.rate_ohlc') {
            const v2 = fxSection(componentId, 2);
            return {v1: fxSection(componentId, 1), v2: {...v2, payload: {...v2.payload, rate_gaps: []}}};
        }
        if (componentId === 'asset.ohlc_returns') return {v1: noGapSection(componentId, 1), v2: ohlcSection(2, {...pricedOhlcPayload(), reason_code: null, price_gaps: []})};
        return {v1: noGapSection(componentId, 1), v2: pricesSection(componentId, 2, [{...coveredAsset(FIRST_ASSET_ID, 1), price_gaps: []}], [])};
    }

    /** The target of a section of `componentId`: the portfolio, the broker, the asset `assetId`, or the FX pair. */
    function targetOf(componentId: string, assetId = FIRST_ASSET_ID) {
        if (componentId.startsWith('broker.')) return {kind: 'broker', broker_id: BROKER_ID};
        if (componentId.startsWith('asset.')) return {kind: 'asset', asset_id: assetId};
        if (componentId.startsWith('fx.')) return {kind: 'fx_pair', base_currency: 'USD', quote_currency: 'EUR'};
        return {kind: 'portfolio'};
    }

    /** The rendered block of `componentId`: tables are looked up inside it, where no other component repeats a title. */
    function blockOf(rendered: Rendered, componentId: string): string {
        const block = rendered.blocks.find((candidate) => candidate.id === componentId);
        if (block === undefined) throw new Error(`no block for ${componentId}`);
        return block.content;
    }

    /** The index of the title line `marker`, which must be there. */
    function titleIndex(lines: readonly string[], marker: string): number {
        const index = lines.indexOf(marker);
        expect(index, `a "${marker}" line`).toBeGreaterThanOrEqual(0);
        return index;
    }

    /** The pipe lines right after the title line `marker`, header first: the table as a reader of `|…|` lines sees it. */
    function pipeLinesAfter(content: string, marker: string): string[] {
        const lines = content.split('\n');
        const table: string[] = [];
        for (const line of lines.slice(titleIndex(lines, marker) + 1)) {
            if (!line.startsWith('|')) break;
            table.push(line);
        }
        return table;
    }

    /** The pipe table on the lines right after `marker`: its header, and one header-keyed map per data row. */
    function pipeTableAfter(content: string, marker: string): {readonly header: readonly string[]; readonly rows: Map<string, string>[]} {
        const [header = [], ...rows] = pipeLinesAfter(content, marker).map((line) => line.slice(1, -1).split(/(?<!\\)\|/));
        return {header, rows: rows.map((cells) => new Map(header.map((column, index): [string, string] => [column, cells[index]])))};
    }

    /** The values of `column` in the table titled `marker`, row by row. */
    function columnOf(content: string, marker: string, column: string): (string | undefined)[] {
        return pipeTableAfter(content, marker).rows.map((row) => row.get(column));
    }

    /** The line right after the last pipe row of the table titled `marker`; undefined when the text ends there. */
    function lineAfterTable(content: string, marker: string): string | undefined {
        const lines = content.split('\n');
        let end = titleIndex(lines, marker) + 1;
        while (end < lines.length && lines[end].startsWith('|')) end += 1;
        return lines[end];
    }

    /** The lines after the last pipe row of the table titled `marker`, up to the title line `next`, which must follow. */
    function linesBetween(content: string, marker: string, next: string): string[] {
        const lines = content.split('\n');
        let end = titleIndex(lines, marker) + 1;
        while (end < lines.length && lines[end].startsWith('|')) end += 1;
        const stop = lines.indexOf(next, end);
        expect(stop, `a "${next}" line after the "${marker}" table`).toBeGreaterThanOrEqual(end);
        return lines.slice(end, stop);
    }

    /** The column names declared on the line right after the table titled `marker`; [] when it declares none (T-B7). */
    function declaredAfter(content: string, marker: string): string[] {
        const line = lineAfterTable(content, marker);
        return line?.startsWith(NULL_COLUMNS_DECLARATION) ? line.slice(NULL_COLUMNS_DECLARATION.length).split(',') : [];
    }

    /** The one row whose `column` reads `value`: rows are found by what they hold, never by position. */
    function rowWhere(rows: readonly Map<string, string>[], column: string, value: string): Map<string, string> {
        const matches = rows.filter((row) => row.get(column) === value);
        expect(matches, `rows whose ${column} is ${value}`).toHaveLength(1);
        return matches[0];
    }

    /** An asset's prompt ref, resolved through the ENTITY DIRECTORY as a reader of the prompt would. */
    function assetRef(rendered: Rendered, displayName: string): string {
        const ref = rowWhere(pipeTableAfter(rendered.entityDirectory, 'ASSETS').rows, 'display_name', displayName).get('ref');
        if (ref === undefined) throw new Error(`the ENTITY DIRECTORY has no ref for ${displayName}`);
        return ref;
    }

    /** The FX pair's prompt ref, resolved through the ENTITY DIRECTORY as a reader of the prompt would. */
    function fxPairRef(rendered: Rendered): string {
        const ref = rowWhere(pipeTableAfter(rendered.entityDirectory, 'FX PAIRS').rows, 'display_name', 'USD/EUR').get('ref');
        if (ref === undefined) throw new Error('the ENTITY DIRECTORY has no ref for USD/EUR');
        return ref;
    }

    /** The lines from the title line `marker`, which must be there, to the end of `content`: how a block closes, as a reader sees it. */
    function linesFrom(content: string, marker: string): string[] {
        const lines = content.split('\n');
        return lines.slice(titleIndex(lines, marker));
    }

    /** `<entity> <start>` for each row of the BUCKETS table, in printed order: which buckets the table kept, and whose. */
    function bucketStarts(content: string): string[] {
        return pipeTableAfter(content, 'BUCKETS').rows.map((row) => `${row.get('entity')} ${row.get('start')}`);
    }

    /** Every line of `content` that names the columns a table left out because they were null in every row (T-B7). */
    function nullColumnDeclarations(content: string): string[] {
        return content.split('\n').filter((line) => line.startsWith(NULL_COLUMNS_DECLARATION));
    }

    /**
     * A map of meanings the renderer exports, read by name through the namespace: while it is missing or lacks a key, only the
     * tests reading it fail, and the file type-checks before the cure and after it. Every value must be a string.
     */
    function exportedMeanings(name: 'PRICE_SERIES_GAP_MEANINGS' | 'SERIES_GAP_MEANINGS', purpose: string): Readonly<Record<string, string>> {
        const value: unknown = Reflect.get(renderer, name);
        const entries = typeof value === 'object' && value !== null && !Array.isArray(value) ? Object.entries(value) : undefined;
        expect(entries !== undefined && entries.every(([, meaning]) => typeof meaning === 'string'), `snapshotDataRenderer.ts exports ${name}, ${purpose}`).toBe(true);
        return Object.fromEntries(entries ?? []);
    }

    /** The renderer's meanings of the reason codes (E-AI503, E-23). */
    function gapMeanings(): Readonly<Record<string, string>> {
        return exportedMeanings('PRICE_SERIES_GAP_MEANINGS', 'one meaning per reason_code');
    }

    /** The renderer's meanings of the gaps inside a series (E-23). */
    function seriesGapMeanings(): Readonly<Record<string, string>> {
        return exportedMeanings('SERIES_GAP_MEANINGS', 'one meaning for a gap in a price series and one for a gap in a rate series');
    }

    /** The line that gives `code` its meaning, built from the renderer's own map: the developer approves the sentences later. */
    function meaningLine(code: PriceSeriesGapCode): string {
        const meaning = gapMeanings()[code];
        expect(typeof meaning, `a meaning for ${code}`).toBe('string');
        return `${code}=${meaning}`;
    }

    /** E-23: the one line that gives the rows of a gap table their meaning, built from the renderer's own map. */
    function gapMeaningLine(kind: SeriesGapKind): string {
        const meaning = seriesGapMeanings()[kind];
        expect(typeof meaning, `a meaning for ${kind}`).toBe('string');
        return `${kind}=${meaning}`;
    }

    /** Every line of `content` that gives a code or a kind of gap its meaning, known or not, in printed order. */
    function meaningLines(content: string): string[] {
        return content.split('\n').filter((line) => MEANING_LINE.test(line));
    }

    it.each(['portfolio.technical_prices', 'broker.technical_prices', 'asset.ohlc_returns'] as const)('PSG-01: renders %s v2 without a gap compactly, byte for byte as its v1', (componentId) => {
        const v1 = renderSnapshotDataText([noGapSection(componentId, 1)], targetOf(componentId), directory).content;
        const v2 = renderSnapshotDataText([noGapSection(componentId, 2)], targetOf(componentId), directory).content;

        // Control: v1 is today's compact continuous-series rendering, with nothing to report.
        expect(v1).toContain(`COMPONENT ${componentId}`);
        expect(v1).not.toContain('PAYLOAD YAML FALLBACK');
        expect(v1.split('\n')).toContain('SERIES');
        expect(v1).not.toContain(UNCOVERED_TITLE);
        // Subject: v2 says it has no gap (`uncovered_assets: []`, `reason_code: null`), and its text is v1's, line for line.
        expect(v2).not.toContain('PAYLOAD YAML FALLBACK');
        expect(v2).toBe(v1);
    });

    it.each([
        ['PSG-02', 'portfolio.technical_prices'],
        ['PSG-03', 'broker.technical_prices'],
    ] as const)('%s: renders %s v2 with its uncovered assets right after SERIES, by ref, weight and code, each code once with its meaning, none in a SERIES or BUCKETS row', (_id, componentId) => {
        const rendered = renderSnapshotDataText([gapPricesSection(componentId, 2)], targetOf(componentId), directory);
        const block = blockOf(rendered, componentId);
        const first = assetRef(rendered, 'First Asset');
        const second = assetRef(rendered, 'Second Asset');
        const third = assetRef(rendered, 'Third Asset');

        // Presence barrier: the compact series rendering, with the covered asset in SERIES and in BUCKETS — and only it: the
        // two uncovered assets are not in `assets`, so neither has a row in either table.
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(columnOf(block, 'SERIES', 'entity')).toEqual([first]);
        expect(columnOf(block, 'BUCKETS', 'entity')).toEqual([first]);
        // Subject: right after the SERIES table, the title, then one row per uncovered asset by prompt ref, its weight as
        // SERIES prints one, and its code — in payload order, not sorted by code ...
        expect(lineAfterTable(block, 'SERIES')).toBe(UNCOVERED_TITLE);
        expect(pipeLinesAfter(block, UNCOVERED_TITLE)).toEqual(['|entity|portfolio_weight_percent|reason_code|', `|${second}|30%|no_stored_price|`, `|${third}|20%|mixed_price_currencies|`]);
        // ... then the meaning of each code present, sorted by code, and BUCKETS ...
        expect(linesBetween(block, UNCOVERED_TITLE, 'BUCKETS')).toEqual([meaningLine('mixed_price_currencies'), meaningLine('no_stored_price')]);
        // ... each meaning said once in the whole prompt.
        expect(meaningLines(rendered.content)).toEqual([meaningLine('mixed_price_currencies'), meaningLine('no_stored_price')]);
        // The uncovered assets are their prompt refs, never their database ids.
        expect(block).not.toContain(String(SECOND_ASSET_ID));
        expect(block).not.toContain(String(THIRD_ASSET_ID));
    });

    it.each(['portfolio.technical_prices', 'broker.technical_prices'] as const)('PSG-04: renders %s v2 with every eligible asset uncovered: all of them listed, a meaning for the one code present only', (componentId) => {
        const uncovered = [uncoveredAsset(SECOND_ASSET_ID, 0.6, 'no_stored_price'), uncoveredAsset(THIRD_ASSET_ID, 0.4, 'no_stored_price')];
        const rendered = renderSnapshotDataText([pricesSection(componentId, 2, [], uncovered)], targetOf(componentId), directory);
        const block = blockOf(rendered, componentId);
        const second = assetRef(rendered, 'Second Asset');
        const third = assetRef(rendered, 'Third Asset');

        // Presence barrier: the compact series rendering, with no series at all: SERIES and BUCKETS keep their header, no row.
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(pipeTableAfter(block, 'SERIES').rows).toEqual([]);
        expect(pipeTableAfter(block, 'BUCKETS').rows).toEqual([]);
        // Subject: every eligible asset is listed, in payload order, both with the same code ...
        expect(lineAfterTable(block, 'SERIES')).toBe(UNCOVERED_TITLE);
        expect(pipeLinesAfter(block, UNCOVERED_TITLE)).toEqual(['|entity|portfolio_weight_percent|reason_code|', `|${second}|60%|no_stored_price|`, `|${third}|40%|no_stored_price|`]);
        // ... which gets its meaning once, between the table and BUCKETS; the code no asset has gets none.
        expect(linesBetween(block, UNCOVERED_TITLE, 'BUCKETS')).toEqual([meaningLine('no_stored_price')]);
        expect(meaningLines(rendered.content)).toEqual([meaningLine('no_stored_price')]);
    });

    it.each([
        ['PSG-05', 'no_stored_price'],
        ['PSG-06', 'mixed_price_currencies'],
    ] as const)('%s: renders asset.ohlc_returns v2 without a series (%s): the code in SUMMARY right after price_basis, its meaning right below the table, the null currency named after SERIES', (_id, code) => {
        const rendered = renderSnapshotDataText([ohlcSection(2, gapOhlcPayload(code))], targetOf('asset.ohlc_returns', SECOND_ASSET_ID), directory);
        const block = blockOf(rendered, 'asset.ohlc_returns');

        // Presence barrier: the compact series rendering; the asset keeps its SERIES row, and BUCKETS has no row, every
        // bucket being empty.
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(columnOf(block, 'SERIES', 'entity')).toEqual([assetRef(rendered, 'Second Asset')]);
        expect(pipeTableAfter(block, 'BUCKETS').rows).toEqual([]);
        // Subject: SUMMARY gains the code, on the row right after price_basis ...
        expect(pipeLinesAfter(block, 'SUMMARY')).toEqual(['|field|value|', '|price_basis|observed_close|', `|reason_code|${code}|`]);
        // ... the line right after the SUMMARY table gives its meaning, the only meaning line of the prompt ...
        expect(lineAfterTable(block, 'SUMMARY')).toBe(meaningLine(code));
        expect(meaningLines(rendered.content)).toEqual([meaningLine(code)]);
        // ... and the null currency leaves the SERIES table and is named on the line right after it (T-B7).
        expect(pipeTableAfter(block, 'SERIES').header).not.toContain('currency');
        expect(declaredAfter(block, 'SERIES')).toContain('currency');
    });

    it.each([
        ['an unknown code in uncovered_assets', pricesSection('portfolio.technical_prices', 2, [coveredAsset(FIRST_ASSET_ID, 0.5)], [uncoveredAsset(SECOND_ASSET_ID, 0.5, UNKNOWN_CODE)]), UNKNOWN_CODE],
        ['an unknown code beside a known one', pricesSection('broker.technical_prices', 2, [coveredAsset(FIRST_ASSET_ID, 0.5)], [uncoveredAsset(SECOND_ASSET_ID, 0.3, 'no_stored_price'), uncoveredAsset(THIRD_ASSET_ID, 0.2, UNKNOWN_CODE)]), UNKNOWN_CODE],
        ['an uncovered_assets that is not an array of records', pricesSection('portfolio.technical_prices', 2, [coveredAsset(FIRST_ASSET_ID, 0.5)], [uncoveredAsset(SECOND_ASSET_ID, 0.5, 'no_stored_price'), 'no_stored_price']), 'no_stored_price'],
        ['an unknown code in asset.ohlc_returns', ohlcSection(2, gapOhlcPayload(UNKNOWN_CODE)), UNKNOWN_CODE],
    ] as const)('PSG-07: sends %s to the generic renderer: no throw, no title, no meaning line, the raw value kept', (_label, declined, rawText) => {
        const componentId = declined.component_id;
        const render = () => renderSnapshotDataText([declined], targetOf(componentId, SECOND_ASSET_ID), directory);

        // A code the renderer cannot explain is data, not an error.
        expect(render).not.toThrow();
        const rendered = render();
        const block = blockOf(rendered, componentId);
        // v2 is a version the renderer knows, so the declined section is printed by the generic renderer: not as YAML, and
        // not by the continuous-series renderer either, whose SERIES title is missing ...
        expect(block).toContain(`COMPONENT ${componentId}`);
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(block.split('\n')).not.toContain('SERIES');
        // ... with no uncovered-assets title and no meaning line for any code, known or not: none is invented ...
        expect(block).not.toContain(UNCOVERED_TITLE);
        expect(meaningLines(rendered.content)).toEqual([]);
        // ... while the raw value still reaches the prompt.
        expect(block).toContain(rawText);
    });

    it('PSG-08: PRICE_SERIES_GAP_MEANINGS gives exactly the three codes one distinct, non-empty, single-line meaning each, safe to print raw', () => {
        const meanings = gapMeanings();

        // An allow-list of the backend's `PriceSeriesGapReason` codes, E-23's `no_price_in_period` included: nothing more, nothing less ...
        expect(Object.keys(meanings).sort()).toEqual(['mixed_price_currencies', 'no_price_in_period', 'no_stored_price']);
        for (const [code, meaning] of Object.entries(meanings)) {
            // ... each meaning a sentence: non-empty, on one line, with no `|` a reader could take for a cell border ...
            expect(typeof meaning, code).toBe('string');
            expect(meaning.trim(), code).not.toBe('');
            expect(meaning, code).not.toMatch(/[\r\n|]/);
        }
        // ... and three reasons, three meanings: mixed currencies, and prices that all predate the period, have a reason of their own.
        expect(new Set(Object.values(meanings)).size).toBe(3);
    });

    it.each([
        ['portfolio.technical_prices v3', gapPricesSection('portfolio.technical_prices', 3)],
        ['broker.technical_prices v3', gapPricesSection('broker.technical_prices', 3)],
        ['asset.ohlc_returns v3', ohlcSection(3, gapOhlcPayload('no_stored_price'))],
        ['portfolio.technical_prices v2 with schema 2', gapPricesSection('portfolio.technical_prices', 2, 2)],
        ['broker.technical_prices v2 with schema 2', gapPricesSection('broker.technical_prices', 2, 2)],
        ['asset.ohlc_returns v2 with schema 2', ohlcSection(2, gapOhlcPayload('no_stored_price'), 2)],
        ['fx.rate_ohlc v3, a version this lot does not add', fxSection('fx.rate_ohlc', 3)],
        ['fx.rate_ohlc v2 with schema 2', fxSection('fx.rate_ohlc', 2, 2)],
        ['fx.returns_volatility v2, a version this lot does not add', fxSection('fx.returns_volatility', 2)],
    ] as const)('PSG-09: still falls back to YAML for %s', (_label, yamlSection) => {
        const rendered = renderSnapshotDataText([yamlSection], targetOf(yamlSection.component_id, SECOND_ASSET_ID), directory).content;

        expect(rendered).toContain(`COMPONENT ${yamlSection.component_id}`);
        expect(rendered).toContain('PAYLOAD YAML FALLBACK');
    });

    it('PSG-10: SERIES_GAP_MEANINGS gives exactly price_gap and rate_gap one distinct, non-empty, single-line meaning each, safe to print raw', () => {
        const meanings = seriesGapMeanings();

        // One meaning per kind of gap, keyed as its meaning line begins: nothing more, nothing less ...
        expect(Object.keys(meanings).sort()).toEqual(['price_gap', 'rate_gap']);
        for (const [kind, meaning] of Object.entries(meanings)) {
            // ... each meaning a sentence: non-empty, on one line, with no `|` a reader could take for a cell border ...
            expect(typeof meaning, kind).toBe('string');
            expect(meaning.trim(), kind).not.toBe('');
            expect(meaning, kind).not.toMatch(/[\r\n|]/);
        }
        // ... and two kinds, two meanings: a gap in a rate series speaks of rates, not of prices.
        expect(new Set(Object.values(meanings)).size).toBe(2);
    });

    it.each(['portfolio.technical_prices', 'broker.technical_prices'] as const)('PSG-11: renders %s v2 with an asset that has two gaps beside one that has none: PRICE GAPS right after BUCKETS, its rows only, in date order, then the price_gap meaning once, closing the block', (componentId) => {
        const gapped = gappedAsset(FIRST_ASSET_ID, 0.6, [101, null, 103, null], [seriesGap('2026/03/09', '2026/03/15', 7, 101, '2026/03/08'), seriesGap('2026/03/24', '2026/03/31', 8, 103, '2026/03/23')]);
        const whole = gappedAsset(SECOND_ASSET_ID, 0.4, [101, 102, 103, 104], []);
        const rendered = renderSnapshotDataText([pricesSection(componentId, 2, [gapped, whole], [])], targetOf(componentId), directory);
        const block = blockOf(rendered, componentId);
        const first = assetRef(rendered, 'First Asset');
        const second = assetRef(rendered, 'Second Asset');

        // Presence barrier: the compact series rendering, both assets in SERIES, no uncovered asset; BUCKETS keeps only the
        // buckets with an observation, as before E-23: the first asset's two empty buckets are no row of it.
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(columnOf(block, 'SERIES', 'entity')).toEqual([first, second]);
        expect(block).not.toContain(UNCOVERED_TITLE);
        expect(bucketStarts(block)).toEqual([`${first} 2026/03/01`, `${first} 2026/03/16`, `${second} 2026/03/01`, `${second} 2026/03/09`, `${second} 2026/03/16`, `${second} 2026/03/24`]);
        // Subject: right after the BUCKETS table, the title, one row per gap of the first asset — the one in the middle, then
        // the one at the end, each with the last price stored before it — and the meaning line, once; the block ends there.
        expect(lineAfterTable(block, 'BUCKETS')).toBe(PRICE_GAPS_TITLE);
        expect(linesFrom(block, PRICE_GAPS_TITLE)).toEqual([PRICE_GAPS_TITLE, PRICE_GAPS_HEADER, `|${first}|2026/03/09|2026/03/15|7|101|2026/03/08|`, `|${first}|2026/03/24|2026/03/31|8|103|2026/03/23|`, gapMeaningLine('price_gap')]);
        // The asset without a gap has no row, and the whole prompt says one meaning: no code line, no rate gap.
        expect(meaningLines(rendered.content)).toEqual([gapMeaningLine('price_gap')]);
    });

    it.each(['portfolio.technical_prices', 'broker.technical_prices'] as const)('PSG-12: lists the gaps of %s v2 in series order, not by ref nor by date, a run of empty buckets merged by the backend as one row', (componentId) => {
        // The payload puts the third asset first; its one gap is the run of its two last buckets, merged.
        const thirdAsset = gappedAsset(THIRD_ASSET_ID, 0.5, [101, 102, null, null], [seriesGap('2026/03/16', '2026/03/31', 16, 102, '2026/03/15')]);
        const firstAsset = gappedAsset(FIRST_ASSET_ID, 0.5, [101, null, 103, 104], [seriesGap('2026/03/09', '2026/03/15', 7, 101, '2026/03/08')]);
        const rendered = renderSnapshotDataText([pricesSection(componentId, 2, [thirdAsset, firstAsset], [])], targetOf(componentId), directory);
        const block = blockOf(rendered, componentId);
        const first = assetRef(rendered, 'First Asset');
        const third = assetRef(rendered, 'Third Asset');

        // Control: SERIES keeps the payload's order, the third asset before the first.
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(columnOf(block, 'SERIES', 'entity')).toEqual([third, first]);
        // Subject: PRICE GAPS follows SERIES — the third asset's gap first, although it is the later one and its ref sorts
        // after — and its two empty buckets are one row, as the backend merged them; the meaning line follows the table.
        expect(pipeLinesAfter(block, PRICE_GAPS_TITLE)).toEqual([PRICE_GAPS_HEADER, `|${third}|2026/03/16|2026/03/31|16|102|2026/03/15|`, `|${first}|2026/03/09|2026/03/15|7|101|2026/03/08|`]);
        expect(lineAfterTable(block, PRICE_GAPS_TITLE)).toBe(gapMeaningLine('price_gap'));
    });

    it.each(['portfolio.technical_prices', 'broker.technical_prices', 'asset.ohlc_returns'] as const)('PSG-13: renders %s v2 with a gap that has no price stored before it beside one that has: its last-price cells empty, never null, both columns kept', (componentId) => {
        // The history begins inside the period: the gap at its head has no last price, the later gap has one.
        const gaps = [seriesGap('2026/03/01', '2026/03/08', 8, null, null), seriesGap('2026/03/16', '2026/03/23', 8, 102, '2026/03/15')];
        const rendered = renderSnapshotDataText([gappedSection(componentId, [null, 102, null, 104], gaps)], targetOf(componentId), directory);
        const block = blockOf(rendered, componentId);
        const first = assetRef(rendered, 'First Asset');

        // Presence barrier: the compact series rendering, with a gap table right after BUCKETS.
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(lineAfterTable(block, 'BUCKETS')).toBe(PRICE_GAPS_TITLE);
        // Subject: both gaps, both last-price columns, and the head gap's last price and date empty — none stored before it,
        // not an unavailable value — so no cell reads null ...
        expect(pipeLinesAfter(block, PRICE_GAPS_TITLE)).toEqual([PRICE_GAPS_HEADER, `|${first}|2026/03/01|2026/03/08|8|||`, `|${first}|2026/03/16|2026/03/23|8|102|2026/03/15|`]);
        expect(pipeLinesAfter(block, PRICE_GAPS_TITLE).join('\n')).not.toContain('null');
        // ... and the meaning line follows the table directly: no column was dropped, so none is named.
        expect(lineAfterTable(block, PRICE_GAPS_TITLE)).toBe(gapMeaningLine('price_gap'));
    });

    it.each(['portfolio.technical_prices', 'broker.technical_prices', 'asset.ohlc_returns'] as const)('PSG-14: renders %s v2 whose only gap has no price stored before it: the two last-price columns gone silently, no omitted_null_columns line', (componentId) => {
        const rendered = renderSnapshotDataText([gappedSection(componentId, [null, 102, 103, 104], [seriesGap('2026/03/01', '2026/03/08', 8, null, null)])], targetOf(componentId), directory);
        const block = blockOf(rendered, componentId);

        // Presence barrier: the compact series rendering, with a gap table right after BUCKETS.
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(lineAfterTable(block, 'BUCKETS')).toBe(PRICE_GAPS_TITLE);
        // Subject: the gap's row without the two columns no gap fills: not applicable here, not unavailable ...
        expect(pipeLinesAfter(block, PRICE_GAPS_TITLE)).toEqual(['|entity|from|to|days|', `|${assetRef(rendered, 'First Asset')}|2026/03/01|2026/03/08|8|`]);
        // ... so no line names them: the meaning line follows the table, and the block declares no null column at all.
        expect(lineAfterTable(block, PRICE_GAPS_TITLE)).toBe(gapMeaningLine('price_gap'));
        expect(nullColumnDeclarations(block)).toEqual([]);
    });

    it('PSG-15: renders asset.ohlc_returns v2 with prices stored only before the period (no_price_in_period): the code and its meaning after SUMMARY, the currency kept, the whole period one gap with the last price', () => {
        const payload = {...gapOhlcPayload('no_price_in_period'), currency: 'USD', price_gaps: [seriesGap('2026/03/01', '2026/03/31', 31, 95.5, '2026/02/20')]};
        const rendered = renderSnapshotDataText([ohlcSection(2, payload)], targetOf('asset.ohlc_returns', SECOND_ASSET_ID), directory);
        const block = blockOf(rendered, 'asset.ohlc_returns');
        const second = assetRef(rendered, 'Second Asset');

        // Presence barrier: the compact series rendering; the asset keeps its SERIES row and, unlike with the two E-AI503
        // codes, its currency, in which its last price reads; BUCKETS has no row, every bucket being empty.
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(columnOf(block, 'SERIES', 'entity')).toEqual([second]);
        expect(columnOf(block, 'SERIES', 'currency')).toEqual(['USD']);
        expect(pipeTableAfter(block, 'BUCKETS').rows).toEqual([]);
        // Subject: SUMMARY gains the code on the row right after price_basis, its meaning on the line right below the table ...
        expect(pipeLinesAfter(block, 'SUMMARY')).toEqual(['|field|value|', '|price_basis|observed_close|', '|reason_code|no_price_in_period|']);
        expect(lineAfterTable(block, 'SUMMARY')).toBe(meaningLine('no_price_in_period'));
        // ... and the whole period is one gap, right after BUCKETS, with the last price stored before the period and its date.
        expect(lineAfterTable(block, 'BUCKETS')).toBe(PRICE_GAPS_TITLE);
        expect(linesFrom(block, PRICE_GAPS_TITLE)).toEqual([PRICE_GAPS_TITLE, PRICE_GAPS_HEADER, `|${second}|2026/03/01|2026/03/31|31|95.5|2026/02/20|`, gapMeaningLine('price_gap')]);
        // Each meaning once in the whole prompt: the code's, then the gap's.
        expect(meaningLines(rendered.content)).toEqual([meaningLine('no_price_in_period'), gapMeaningLine('price_gap')]);
    });

    it('PSG-16: renders fx.rate_ohlc v2 compactly, its gap in RATE GAPS right after BUCKETS with the last rate, then the rate_gap meaning once', () => {
        const rendered = renderSnapshotDataText([gappedFxSection([0.91, null, 0.93, 0.94], [seriesGap('2026/03/09', '2026/03/15', 7, 0.91, '2026/03/08')])], targetOf('fx.rate_ohlc'), directory);
        const block = blockOf(rendered, 'fx.rate_ohlc');
        const pair = fxPairRef(rendered);

        // Presence barrier: v2 is a compact version now, rendered as v1 is: SERIES, and BUCKETS with only the buckets that
        // have a rate.
        expect(block).toContain('COMPONENT fx.rate_ohlc');
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(columnOf(block, 'SERIES', 'entity')).toEqual([pair]);
        expect(bucketStarts(block)).toEqual([`${pair} 2026/03/01`, `${pair} 2026/03/16`, `${pair} 2026/03/24`]);
        // Subject: the gap in a table of rates, not of prices, with the last rate stored before it, then its meaning line;
        // the block ends there ...
        expect(lineAfterTable(block, 'BUCKETS')).toBe(RATE_GAPS_TITLE);
        expect(linesFrom(block, RATE_GAPS_TITLE)).toEqual([RATE_GAPS_TITLE, RATE_GAPS_HEADER, `|${pair}|2026/03/09|2026/03/15|7|0.91|2026/03/08|`, gapMeaningLine('rate_gap')]);
        // ... with no price-gap title, and one meaning in the whole prompt.
        expect(block.split('\n')).not.toContain(PRICE_GAPS_TITLE);
        expect(meaningLines(rendered.content)).toEqual([gapMeaningLine('rate_gap')]);
    });

    it.each(['portfolio.technical_prices', 'broker.technical_prices'] as const)('PSG-17: renders %s v2 with a no_price_in_period asset beside a no_stored_price one: three more columns, filled on its row only, empty on the other, and both meanings', (componentId) => {
        const uncovered = [withNullLastPrice(uncoveredAsset(SECOND_ASSET_ID, 0.3, 'no_stored_price')), uncoveredBeforePeriod(THIRD_ASSET_ID, 0.2, 'USD', 95.5, '2026/02/20')];
        const rendered = renderSnapshotDataText([pricesSection(componentId, 2, [coveredAsset(FIRST_ASSET_ID, 0.5)], uncovered)], targetOf(componentId), directory);
        const block = blockOf(rendered, componentId);
        const first = assetRef(rendered, 'First Asset');
        const second = assetRef(rendered, 'Second Asset');
        const third = assetRef(rendered, 'Third Asset');

        // Presence barrier: the compact series rendering, with the covered asset alone in SERIES and in BUCKETS.
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(columnOf(block, 'SERIES', 'entity')).toEqual([first]);
        expect(columnOf(block, 'BUCKETS', 'entity')).toEqual([first]);
        // Subject: right after SERIES, the table gains currency, last_price and last_price_date, filled on the
        // no_price_in_period row from its currency, last close and its date; on the no_stored_price row they do not apply:
        // empty, never the backend's null. Rows in payload order ...
        expect(lineAfterTable(block, 'SERIES')).toBe(UNCOVERED_TITLE);
        expect(pipeLinesAfter(block, UNCOVERED_TITLE)).toEqual([UNCOVERED_HEADER_WITH_LAST_PRICE, `|${second}|30%|no_stored_price||||`, `|${third}|20%|no_price_in_period|USD|95.5|2026/02/20|`]);
        // ... then the meaning of each code present, sorted by code, and BUCKETS: no line names a column ...
        expect(linesBetween(block, UNCOVERED_TITLE, 'BUCKETS')).toEqual([meaningLine('no_price_in_period'), meaningLine('no_stored_price')]);
        // ... each meaning said once in the whole prompt, and no gap meaning: no series has a gap.
        expect(meaningLines(rendered.content)).toEqual([meaningLine('no_price_in_period'), meaningLine('no_stored_price')]);
    });

    it.each(['portfolio.technical_prices', 'broker.technical_prices'] as const)('PSG-18: renders %s v2 whose uncovered rows carry the nulls E-23 adds to no_stored_price and mixed_price_currencies byte for byte as without them: the new columns never appear', (componentId) => {
        const withNulls = pricesSection(componentId, 2, [coveredAsset(FIRST_ASSET_ID, 0.5)], [withNullLastPrice(uncoveredAsset(SECOND_ASSET_ID, 0.3, 'no_stored_price')), withNullLastPrice(uncoveredAsset(THIRD_ASSET_ID, 0.2, 'mixed_price_currencies'))]);
        const rendered = renderSnapshotDataText([withNulls], targetOf(componentId), directory);
        const block = blockOf(rendered, componentId);

        // Control: the E-AI503 table of PSG-02, three columns, the meanings right below it, nothing named in between ...
        expect(pipeLinesAfter(block, UNCOVERED_TITLE)).toEqual(['|entity|portfolio_weight_percent|reason_code|', `|${assetRef(rendered, 'Second Asset')}|30%|no_stored_price|`, `|${assetRef(rendered, 'Third Asset')}|20%|mixed_price_currencies|`]);
        expect(lineAfterTable(block, UNCOVERED_TITLE)).toBe(meaningLine('mixed_price_currencies'));
        // ... and the subject: the nulls change nothing — not a column, not an omitted_null_columns line, not a byte.
        expect(rendered.content).toBe(renderSnapshotDataText([gapPricesSection(componentId, 2)], targetOf(componentId), directory).content);
    });

    it.each(['portfolio.technical_prices', 'broker.technical_prices', 'asset.ohlc_returns', 'fx.rate_ohlc'] as const)('PSG-19: renders %s v2 with an empty gap list compactly, byte for byte as its v1', (componentId) => {
        const {v1, v2} = emptyGapListSections(componentId);
        const v1Text = renderSnapshotDataText([v1], targetOf(componentId), directory).content;
        const v2Text = renderSnapshotDataText([v2], targetOf(componentId), directory).content;

        // Control: v1 is today's compact continuous-series rendering, with nothing to report.
        expect(v1Text).toContain(`COMPONENT ${componentId}`);
        expect(v1Text).not.toContain('PAYLOAD YAML FALLBACK');
        expect(v1Text.split('\n')).toContain('SERIES');
        // Subject: v2 says it has no gap (`price_gaps: []`, `rate_gaps: []`): no gap title, no meaning line, v1's text line for line.
        expect(v2Text).not.toContain('PAYLOAD YAML FALLBACK');
        expect(v2Text.split('\n')).not.toContain(PRICE_GAPS_TITLE);
        expect(v2Text.split('\n')).not.toContain(RATE_GAPS_TITLE);
        expect(v2Text).toBe(v1Text);
    });

    it.each([
        ['a price_gaps that is not a list', pricesSection('portfolio.technical_prices', 2, [gappedAsset(FIRST_ASSET_ID, 1, [101, null, 103, 104], 'not_a_gap_list')], []), 'not_a_gap_list'],
        ['a price_gaps that is not a list of records', pricesSection('broker.technical_prices', 2, [gappedAsset(FIRST_ASSET_ID, 1, [101, null, 103, 104], [seriesGap('2026/03/09', '2026/03/15', 7, 101, '2026/03/08'), 'not_a_gap'])], []), 'not_a_gap'],
        ['a gap without its end_date', gappedSection('asset.ohlc_returns', [101, null, 103, 104], [{start_date: '2026/03/09', calendar_days: 7, last_value: 101, last_value_date: '2026/03/08'}]), '2026/03/09'],
        ['a rate gap whose last value is not a number', gappedFxSection([0.91, null, 0.93, 0.94], [{...seriesGap('2026/03/09', '2026/03/15', 7, 0.91, '2026/03/08'), last_value: {rate: 0.8765}}]), '0.8765'],
    ] as const)('PSG-20: sends %s to the generic renderer, as an unknown code: no throw, no gap title, no meaning line, the raw value kept', (_label, declined, rawText) => {
        const componentId = declined.component_id;
        const render = () => renderSnapshotDataText([declined], targetOf(componentId), directory);

        // A gap the renderer cannot read is data, not an error.
        expect(render).not.toThrow();
        const rendered = render();
        const block = blockOf(rendered, componentId);
        const lines = block.split('\n');
        // v2 is a version the renderer knows, so the declined section is printed by the generic renderer: not as YAML, and
        // not by the continuous-series renderer either, whose SERIES title is missing ...
        expect(block).toContain(`COMPONENT ${componentId}`);
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(lines).not.toContain('SERIES');
        // ... with no gap table and no meaning line, for the gap or for anything else: none is invented ...
        expect(lines).not.toContain(PRICE_GAPS_TITLE);
        expect(lines).not.toContain(RATE_GAPS_TITLE);
        expect(meaningLines(rendered.content)).toEqual([]);
        // ... while the raw value still reaches the prompt.
        expect(block).toContain(rawText);
    });
});
