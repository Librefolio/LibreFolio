/**
 * Contract tests for the reading of the FX convert answer on the FX detail page (X-R16, FX part):
 * `parseFxConvertWithSignalIsolation`, the twin of the asset page's `parseAssetPriceQueryWithSignalIsolation`
 * (`components/assets/detail/assetDetailPriceQuery.ts`).
 *
 * Why it is needed. With a backend signal configured, `loadChartData` in `routes/(app)/fx/[pair]/+page.svelte` asks for
 * the rates and the signal results in one `POST /api/v1/fx/currencies/convert`, through the Zodios client, which
 * validates every answer (`validate: 'response'`, `lib/api/zodios-client.ts`) against the generated
 * `FXConvertResponse`. One signal result that schema rejects therefore rejects the WHOLE answer, rates included: the
 * page lands in its catch, merges no rate into its store and, with nothing cached, draws no chart at all. The guard at
 * the end of this file pins that fact on the generated schema.
 *
 * The contract pinned here:
 * - the answer is validated as `FXConvertResponse` with, in each signal group, only its valid signal results
 *   (`backendSignalSchemas.result`);
 * - it comes back as parsed (`results`, `success_count`), each group with its RAW `signals`, so the page can still
 *   report the invalid ones; a missing `signal_results` gives `[]`, a group without `signals` gives `signals: []`;
 * - it throws an `Error` when the answer is not an object, when `results` is malformed (a broken rate is a real error,
 *   never isolated), when `signal_results` is not an array, when a group is not an object, when a group's `signals` is
 *   present but not an array, and wherever else the schema rejects the answer outside its signal results.
 *
 * RED TODAY, by construction: `./fxDetailConvertQuery` does not exist yet, so the static import below fails and the
 * whole file fails at import, with no test run («Error: Cannot find module './fxDetailConvertQuery' imported from
 * …/fxDetailConvertQuery.test.ts», Vitest 4.1). That is the expected red; the cure adds the module. The guard holds
 * before the cure and after it, but runs only once the import resolves.
 *
 * Real schemas throughout: the fixtures are valid, or deliberately invalid, against the generated `FXConversionResult`,
 * `FXSignalQueryResult` and `SignalResult`. A refusal is asserted as an `Error`, never by its message: the wording
 * belongs to the cure.
 */
import {describe, expect, it} from 'vitest';
import {schemas} from '$lib/api';
import {backendSignalSchemas} from '$lib/charts/signals/backendTypes';
import {parseFxConvertWithSignalIsolation} from './fxDetailConvertQuery';

/** One day of 1 EUR in USD, as `FXConversionResult` accepts it. */
function rateOn(date: string, rate: string, overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {from_amount: {code: 'EUR', amount: '1'}, to_amount: {code: 'USD', amount: rate}, conversion_date: date, rate, ...overrides};
}

/** Thursday to Saturday of EUR/USD: the Saturday back-filled from the Friday, as the backend answers a weekend. */
function rates(): Record<string, unknown>[] {
    return [rateOn('2026-02-05', '1.0812'), rateOn('2026-02-06', '1.0834'), rateOn('2026-02-07', '1.0834', {backward_fill_info: {actual_rate_date: '2026-02-06', days_back: 1}})];
}

/** A signal result `SignalResult` accepts. */
function signalResult(instanceId: string, overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {instance_id: instanceId, signal_code: 'SMA', status: 'ok', ...overrides};
}

/** A signal result `SignalResult` rejects for its status alone. */
function invalidSignal(): Record<string, unknown> {
    return signalResult('cci-14', {signal_code: 'CCI', status: 'not-a-status'});
}

/**
 * Valid, invalid, valid, and each differs from what the schema would return: the first has a key the schema drops,
 * the second fails the schema, the third lacks a field the schema defaults (`error.retryable`).
 */
function mixedSignals(): unknown[] {
    return [signalResult('sma-20', {note_from_backend: 'a key the schema does not know'}), invalidSignal(), signalResult('rsi-14', {signal_code: 'RSI', status: 'failed', error: {code: 'compute_error', message: 'RSI computation failed'}})];
}

/** The signal group of conversion request `requestIndex`, as `FXSignalQueryResult` accepts it; without `signals` unless given. */
function signalGroup(requestIndex: number, signals?: unknown, overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {request_index: requestIndex, from_currency: 'EUR', to_currency: 'USD', date_range: {start: '2026-02-05', end: '2026-02-07'}, ...(signals === undefined ? {} : {signals}), ...overrides};
}

/** An answer of `POST /fx/currencies/convert`: the three rates, their count, and the given keys on top (`signal_results`, …). */
function convertAnswer(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {results: rates(), success_count: 3, ...overrides};
}

// RED until the cure (the file fails at import). Pins what the page reads from a valid answer: the rates and their count
// as the schema parses them, each group with the signal results it carried.
describe('parseFxConvertWithSignalIsolation: the answer is validated with the valid signal results of each group, and returned with the raw ones', () => {
    it('returns a valid answer as received: the rates, their count, and each group with its signal results', () => {
        const answer = () => convertAnswer({signal_results: [signalGroup(0, [signalResult('sma-20'), signalResult('rsi-14', {signal_code: 'RSI'})])]});

        const parsed = parseFxConvertWithSignalIsolation(answer());

        expect(parsed).toEqual(answer());
        expect(parsed).toEqual(schemas.FXConvertResponse.parse(answer()));
    });

    it('returns the signal results each group carried, not the schema output of them', () => {
        const signals = () => [signalResult('sma-20', {note_from_backend: 'a key the schema does not know'}), signalResult('rsi-14', {signal_code: 'RSI', status: 'failed', error: {code: 'compute_error', message: 'RSI computation failed'}})];
        // Both are valid, and the schema returns each differently: it drops the unknown key, and defaults `retryable`.
        expect(signals().map((signal) => backendSignalSchemas.result.parse(signal))).not.toEqual(signals());

        const parsed = parseFxConvertWithSignalIsolation(convertAnswer({signal_results: [signalGroup(0, signals())]}));

        expect(parsed).toEqual(convertAnswer({signal_results: [signalGroup(0, signals())]}));
    });

    it('returns the rates as the schema parses them', () => {
        // `Currency_Output` drops a key it does not know: the rates come back parsed, not as received.
        const answer = () => convertAnswer({results: [rateOn('2026-02-05', '1.0812'), rateOn('2026-02-06', '1.0834', {to_amount: {code: 'USD', amount: '1.0834', note_from_backend: 'a key the schema does not know'}})], success_count: 2, signal_results: [signalGroup(0, [signalResult('sma-20')])]});
        const schemaOutput = schemas.FXConvertResponse.parse(answer());
        expect(schemaOutput.results).not.toEqual(answer().results);

        expect(parseFxConvertWithSignalIsolation(answer())).toEqual(schemaOutput);
    });
});

// RED until the cure (the file fails at import). Pins the isolation itself, the point of X-R16: an invalid signal result
// does not throw, costs the answer neither its rates nor its group, and stays in the group's raw list for the page to report.
describe('parseFxConvertWithSignalIsolation: an invalid signal result costs the answer nothing but itself', () => {
    it('keeps the rates of an answer whose signal results include an invalid one, and returns the group with all of them', () => {
        const parsed = parseFxConvertWithSignalIsolation(convertAnswer({signal_results: [signalGroup(0, mixedSignals())]}));

        // The three rates, the back-filled Saturday included, their count, and the group with its three results as received.
        expect(parsed).toEqual(convertAnswer({signal_results: [signalGroup(0, mixedSignals())]}));
    });

    it.each([
        {label: 'one without instance id, its status outside the enum', signal: {signal_code: 'SMA', status: 'not-a-status'}},
        {label: 'one with an empty instance id', signal: signalResult('')},
        {label: 'one whose series is not a list', signal: signalResult('macd-12', {signal_code: 'MACD', series: 'not-a-list'})},
        {label: 'one whose error code is unknown', signal: signalResult('rsi-14', {signal_code: 'RSI', status: 'failed', error: {code: 'not-a-code', message: 'RSI computation failed'}})},
        {label: 'null', signal: null},
        {label: 'a string', signal: 'SMA'},
    ])('isolates an invalid signal result: $label', ({signal}) => {
        expect(backendSignalSchemas.result.safeParse(signal).success).toBe(false);

        const parsed = parseFxConvertWithSignalIsolation(convertAnswer({signal_results: [signalGroup(0, [signalResult('sma-20'), signal])]}));

        expect(parsed).toEqual(convertAnswer({signal_results: [signalGroup(0, [signalResult('sma-20'), signal])]}));
    });

    it('isolates group by group, keeping every group in the order of the answer', () => {
        // The first group is clean, the second mixes a valid and an invalid result, the third holds an invalid one alone.
        const groups = () => [signalGroup(0, [signalResult('sma-20')]), signalGroup(1, [signalResult('sma-20'), invalidSignal()], {from_currency: 'USD', to_currency: 'EUR'}), signalGroup(2, [invalidSignal()])];

        const parsed = parseFxConvertWithSignalIsolation(convertAnswer({signal_results: groups()}));

        expect(parsed).toEqual(convertAnswer({signal_results: groups()}));
    });
});

// RED until the cure (the file fails at import). Pins the empty shapes the page can rely on: always a list of groups,
// always a list of signal results in a group.
describe('parseFxConvertWithSignalIsolation: an answer without signal results, a group without signals', () => {
    it('gives an answer without signal results an empty list, its rates intact', () => {
        expect(parseFxConvertWithSignalIsolation(convertAnswer())).toEqual(convertAnswer({signal_results: []}));
        expect(parseFxConvertWithSignalIsolation(convertAnswer({signal_results: undefined}))).toEqual(convertAnswer({signal_results: []}));
        expect(parseFxConvertWithSignalIsolation(convertAnswer({signal_results: []}))).toEqual(convertAnswer({signal_results: []}));
    });

    it('gives an answer with no rate an empty rate list, not an error', () => {
        expect(parseFxConvertWithSignalIsolation({results: [], success_count: 0})).toEqual({results: [], success_count: 0, signal_results: []});
    });

    it('gives a group without signals an empty signal list', () => {
        expect(parseFxConvertWithSignalIsolation(convertAnswer({signal_results: [signalGroup(0)]}))).toEqual(convertAnswer({signal_results: [signalGroup(0, [])]}));
        expect(parseFxConvertWithSignalIsolation(convertAnswer({signal_results: [signalGroup(0, [])]}))).toEqual(convertAnswer({signal_results: [signalGroup(0, [])]}));
    });
});

// RED until the cure (the file fails at import). Pins the refusals: the isolation covers one signal result at a time and
// nothing else — a malformed answer, rate, group list, group or signal collection is a real error.
describe('parseFxConvertWithSignalIsolation: a malformed answer, rate list, rate, group list, group or signal collection throws', () => {
    it.each([
        {label: 'null', data: null},
        {label: 'undefined', data: undefined},
        {label: 'an array', data: [convertAnswer()]},
        {label: 'a string', data: 'results'},
        {label: 'a number', data: 3},
    ])('rejects $label as the answer', ({data}) => {
        expect(() => parseFxConvertWithSignalIsolation(data)).toThrow(Error);
    });

    it.each([
        {label: 'missing', results: undefined},
        {label: 'null', results: null},
        {label: 'an object', results: {0: rateOn('2026-02-05', '1.0812')}},
        {label: 'a string', results: 'results'},
    ])('rejects rates that are $label', ({results}) => {
        expect(() => parseFxConvertWithSignalIsolation(convertAnswer({results, signal_results: [signalGroup(0, [signalResult('sma-20')])]}))).toThrow(Error);
    });

    it.each([
        {label: 'a numeric rate', rate: rateOn('2026-02-06', '1.0834', {rate: 1.0834})},
        {label: 'no converted amount', rate: rateOn('2026-02-06', '1.0834', {to_amount: undefined})},
        {label: 'a back-fill without the day it reads', rate: rateOn('2026-02-06', '1.0834', {backward_fill_info: {days_back: 1}})},
        {label: 'null', rate: null},
    ])('rejects a broken rate ($label) whatever the signal results: a rate is never isolated', ({rate}) => {
        expect(schemas.FXConversionResult.safeParse(rate).success).toBe(false);
        // The three rates, the Friday broken.
        const results = () => rates().map((day, index) => (index === 1 ? rate : day));

        expect(() => parseFxConvertWithSignalIsolation(convertAnswer({results: results()}))).toThrow(Error);
        expect(() => parseFxConvertWithSignalIsolation(convertAnswer({results: results(), signal_results: [signalGroup(0, [signalResult('sma-20')])]}))).toThrow(Error);
        expect(() => parseFxConvertWithSignalIsolation(convertAnswer({results: results(), signal_results: [signalGroup(0, mixedSignals())]}))).toThrow(Error);
    });

    it.each([
        {label: 'null', signalResults: null},
        {label: 'an object', signalResults: {0: signalGroup(0, [signalResult('sma-20')])}},
        {label: 'a single group', signalResults: signalGroup(0, [signalResult('sma-20')])},
        {label: 'a string', signalResults: 'signal_results'},
    ])('rejects signal results that are $label', ({signalResults}) => {
        expect(() => parseFxConvertWithSignalIsolation(convertAnswer({signal_results: signalResults}))).toThrow(Error);
    });

    it.each([
        {label: 'null', group: null},
        {label: 'an array', group: [signalGroup(1, [signalResult('sma-20')])]},
        {label: 'a string', group: 'group'},
    ])('rejects a group that is $label, beside a valid one', ({group}) => {
        expect(() => parseFxConvertWithSignalIsolation(convertAnswer({signal_results: [signalGroup(0, [signalResult('sma-20')]), group]}))).toThrow(Error);
    });

    it.each([
        {label: 'null', signals: null},
        {label: 'an object', signals: {0: signalResult('sma-20')}},
        {label: 'a single result', signals: signalResult('sma-20')},
        {label: 'a string', signals: 'signals'},
    ])('rejects a group whose signal results are $label, beside a valid group', ({signals}) => {
        expect(() => parseFxConvertWithSignalIsolation(convertAnswer({signal_results: [signalGroup(0, [signalResult('sma-20')]), signalGroup(1, signals)]}))).toThrow(Error);
    });

    // What the schema rejects outside the signal results: the isolation drops invalid results, never an invalid group or count.
    it.each([
        {label: 'no success count', answer: convertAnswer({success_count: undefined})},
        {label: 'a negative success count', answer: convertAnswer({success_count: -1})},
        {label: 'operation errors that are not a list', answer: convertAnswer({errors: 'No FX rate found'})},
        {label: 'a group with a negative request index', answer: convertAnswer({signal_results: [signalGroup(-1, [signalResult('sma-20')])]})},
        {label: 'a group with a four-letter currency', answer: convertAnswer({signal_results: [signalGroup(0, [signalResult('sma-20')], {from_currency: 'EURO'})]})},
        {label: 'a group without its date range', answer: convertAnswer({signal_results: [signalGroup(0, [signalResult('sma-20')], {date_range: undefined})]})},
    ])('rejects an answer the schema rejects outside its signal results: $label', ({answer}) => {
        expect(schemas.FXConvertResponse.safeParse(answer).success).toBe(false);

        expect(() => parseFxConvertWithSignalIsolation(answer)).toThrow(Error);
    });
});

// GUARD, green before the cure and after it (it runs once the import resolves). Pins WHY the page needs the isolation:
// the generated schema the Zodios client validates the answer against refuses all of it for one invalid signal result.
describe('guard: the generated FXConvertResponse rejects the whole answer, rates included, for one invalid signal result', () => {
    it('accepts the answers whose signal results are all valid: the fixtures above are sound', () => {
        expect(schemas.FXConvertResponse.safeParse(convertAnswer()).success).toBe(true);
        expect(schemas.FXConvertResponse.safeParse(convertAnswer({signal_results: [signalGroup(0, [signalResult('sma-20'), signalResult('rsi-14', {signal_code: 'RSI'})])]})).success).toBe(true);
        expect(schemas.FXConvertResponse.safeParse(convertAnswer({signal_results: [signalGroup(0, [mixedSignals()[0], mixedSignals()[2]])]})).success).toBe(true);
    });

    it('rejects the answer of the isolation case as a whole, for its invalid signal result alone', () => {
        const parsed = schemas.FXConvertResponse.safeParse(convertAnswer({signal_results: [signalGroup(0, mixedSignals())]}));

        expect(parsed.success).toBe(false);
        // Nothing of the answer survives the refusal: the rates are lost with the signal result.
        expect(parsed.data).toBeUndefined();
        // And every issue lies inside that one result (group 0, result 1): the rates and the group are valid.
        const paths = parsed.error?.issues.map((issue) => issue.path.slice(0, 4)) ?? [];
        expect(paths.length).toBeGreaterThan(0);
        expect(paths).toEqual(paths.map(() => ['signal_results', 0, 'signals', 1]));
    });
});
