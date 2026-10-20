import {describe, expect, it} from 'vitest';

// E-AI503: `PRICE_SERIES_GAP_MEANINGS` is read by name through the namespace, so while it is missing only the tests reading it fail.
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
 * - Without a gap a v2 section renders byte for byte as its v1. v3 still falls back to YAML, and so do the FX series,
 *   which this lot leaves at v1.
 *
 * No meaning sentence is frozen here: the developer approves their wording later, so every test reads them from the
 * renderer's own map. Titles, headers and keys are format and are asserted; cells are read by column header, rows found
 * by what they hold.
 *
 * Today (base `70ad4cec1`) the map does not exist and `COMPACT_COMPONENT_VERSIONS` lists none of the three components, so
 * their v2 renders as `PAYLOAD YAML FALLBACK`: PSG-01 to PSG-08 are red. PSG-09 is a guard, green today and after.
 */
describe('assets without a price series (E-AI503)', () => {
    /** The backend's `PriceSeriesGapReason`: the codes the renderer gives a meaning. */
    type PriceSeriesGapCode = 'no_stored_price' | 'mixed_price_currencies';
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
    /** A line that gives a code its meaning, `<code>=…`, for every code these tests use, known or not. */
    const MEANING_LINE = /^(?:no_stored_price|mixed_price_currencies|some_future_reason)=/;

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
        const empty = {first: null, minimum: null, maximum: null, last: null, observation_count: 0, minimum_date: null, maximum_date: null, return_start_date: null, simple_return: null};
        return [
            {start_date: '2026/03/01', end_date: '2026/03/15', calendar_days: 15, ...empty},
            {start_date: '2026/03/16', end_date: '2026/03/31', calendar_days: 16, ...empty},
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

    /** `fx.rate_ohlc` / `fx.returns_volatility`: the FX series this lot leaves alone, each with its own payload shape. */
    function fxSection(componentId: 'fx.rate_ohlc' | 'fx.returns_volatility', componentVersion: number) {
        if (componentId === 'fx.rate_ohlc') {
            return section(componentId, componentVersion, {base_currency: 'USD', quote_currency: 'EUR', buckets: [priceBucket({first: {rate: 0.91}, minimum: {rate: 0.9}, maximum: {rate: 0.93}, last: {rate: 0.92}})], latest_rate: 0.92, latest_date: '2026/03/31'});
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
        return section(componentId, componentVersion, {base_currency: 'USD', quote_currency: 'EUR', buckets: [returnBucket]});
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

    /** The renderer's meanings, read by name through the namespace: while the export is missing, only the tests reading it fail. */
    function gapMeanings(): Readonly<Record<PriceSeriesGapCode, string>> {
        const meanings = renderer.PRICE_SERIES_GAP_MEANINGS;
        expect(typeof meanings === 'object' && meanings !== null, 'snapshotDataRenderer.ts exports PRICE_SERIES_GAP_MEANINGS, one meaning per reason_code').toBe(true);
        return meanings;
    }

    /** The line that gives `code` its meaning, built from the renderer's own map: the developer approves the sentences later. */
    function meaningLine(code: PriceSeriesGapCode): string {
        const meaning = gapMeanings()[code];
        expect(typeof meaning, `a meaning for ${code}`).toBe('string');
        return `${code}=${meaning}`;
    }

    /** Every line of `content` that gives a code a meaning, known or not, in printed order. */
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

    it('PSG-08: PRICE_SERIES_GAP_MEANINGS gives exactly the two codes one distinct, non-empty, single-line meaning each, safe to print raw', () => {
        const meanings = gapMeanings();

        // An allow-list of the backend's `PriceSeriesGapReason` codes: nothing more, nothing less ...
        expect(Object.keys(meanings).sort()).toEqual(['mixed_price_currencies', 'no_stored_price']);
        for (const [code, meaning] of Object.entries(meanings)) {
            // ... each meaning a sentence: non-empty, on one line, with no `|` a reader could take for a cell border ...
            expect(typeof meaning, code).toBe('string');
            expect(meaning.trim(), code).not.toBe('');
            expect(meaning, code).not.toMatch(/[\r\n|]/);
        }
        // ... and two reasons, two meanings: mixed currencies have a reason of their own.
        expect(new Set(Object.values(meanings)).size).toBe(2);
    });

    it.each([
        ['portfolio.technical_prices v3', gapPricesSection('portfolio.technical_prices', 3)],
        ['broker.technical_prices v3', gapPricesSection('broker.technical_prices', 3)],
        ['asset.ohlc_returns v3', ohlcSection(3, gapOhlcPayload('no_stored_price'))],
        ['portfolio.technical_prices v2 with schema 2', gapPricesSection('portfolio.technical_prices', 2, 2)],
        ['broker.technical_prices v2 with schema 2', gapPricesSection('broker.technical_prices', 2, 2)],
        ['asset.ohlc_returns v2 with schema 2', ohlcSection(2, gapOhlcPayload('no_stored_price'), 2)],
        ['fx.rate_ohlc v2, a version this lot does not add', fxSection('fx.rate_ohlc', 2)],
        ['fx.returns_volatility v2, a version this lot does not add', fxSection('fx.returns_volatility', 2)],
    ] as const)('PSG-09: still falls back to YAML for %s', (_label, yamlSection) => {
        const rendered = renderSnapshotDataText([yamlSection], targetOf(yamlSection.component_id, SECOND_ASSET_ID), directory).content;

        expect(rendered).toContain(`COMPONENT ${yamlSection.component_id}`);
        expect(rendered).toContain('PAYLOAD YAML FALLBACK');
    });
});
