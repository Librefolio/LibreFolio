/**
 * Contract tests for the signal helpers the chart detail pages share (FE5c, piece 2).
 *
 * The three bodies moved out of the asset detail page verbatim; these tests pin what the page
 * relies on, so the move is proven and later edits are guarded:
 * - the backend signal results are parsed all or nothing, by the real signal result schema;
 * - the data fingerprint follows what the signal data depends on (id, type, params) and nothing
 *   else: not the order, not the style, not the runtime params a comparison load writes back;
 * - the comparison peers are the distinct valid asset ids of the asset-comparison configs.
 */
import {describe, expect, it} from 'vitest';
import type {SignalConfig} from '$lib/charts/signals';
import {backendSignalSchemas} from '$lib/charts/signals/backendTypes';
import {comparisonAssetIds, parseBackendSignalResults, signalDataContextFingerprint} from '../chartPageSignals';
import {COMPARISON_ASSET_RUNTIME_PARAM_KEYS} from '../loadComparisonData';

function signalConfig(id: string, signalType: string, params: Record<string, unknown> = {}, style: Record<string, unknown> = {}): SignalConfig {
    return {id, signalType, params, style} as unknown as SignalConfig;
}

function comparisonConfig(id: string, assetId: unknown, params: Record<string, unknown> = {}): SignalConfig {
    return signalConfig(id, 'asset-comparison', {assetId, ...params});
}

/** A minimal result the signal result schema accepts. */
function signalResult(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {instance_id: 'sma-20', signal_code: 'SMA', status: 'ok', ...overrides};
}

/** Every runtime param a comparison load writes back into its config, each with a value. */
function comparisonRuntimeParams(): Record<string, unknown> {
    return Object.fromEntries(COMPARISON_ASSET_RUNTIME_PARAM_KEYS.map((key) => [key, `runtime value of ${key}`]));
}

describe('parseBackendSignalResults: a non-array is no result; each item is parsed by the signal result schema, and one invalid item throws', () => {
    it.each([
        {label: 'undefined', value: undefined},
        {label: 'null', value: null},
        {label: 'a string', value: 'signals'},
        {label: 'a number', value: 3},
        {label: 'a single result object', value: signalResult()},
    ])('gives no results for $label', ({value}) => {
        expect(parseBackendSignalResults(value)).toEqual([]);
    });

    it('gives no results for an empty array', () => {
        expect(parseBackendSignalResults([])).toEqual([]);
    });

    it('returns each item as the schema parses it, in order', () => {
        const items = [signalResult({instance_id: 'sma-20', note_from_backend: 'a key the schema does not know'}), signalResult({instance_id: 'cci-14', signal_code: 'CCI', status: 'failed', error: {code: 'compute_error', message: 'CCI computation failed'}})];

        const results = parseBackendSignalResults(items);

        expect(results.map((result) => result.instance_id)).toEqual(['sma-20', 'cci-14']);
        expect(results).toEqual(items.map((item) => backendSignalSchemas.result.parse(item)));
        // The schema's output, not the raw item: an unknown key is dropped, a default is filled in.
        expect(results.find((result) => result.instance_id === 'sma-20')).not.toHaveProperty('note_from_backend');
        expect(results.find((result) => result.instance_id === 'cci-14')?.error).toEqual({code: 'compute_error', message: 'CCI computation failed', retryable: false});
    });

    it('throws when one item is invalid, even after valid ones', () => {
        const valid = signalResult();

        expect(parseBackendSignalResults([valid])).toHaveLength(1);
        expect(() => parseBackendSignalResults([valid, signalResult({status: 'not-a-status'})])).toThrow();
        expect(() => parseBackendSignalResults([valid, {signal_code: 'SMA', status: 'ok'}])).toThrow();
        expect(() => parseBackendSignalResults([valid, null])).toThrow();
    });
});

describe('signalDataContextFingerprint: the id, type and params of each config, blind to config order, params order, style and comparison runtime params', () => {
    it('is the JSON of each config id, type and params, sorted by id', () => {
        const fingerprint = signalDataContextFingerprint([signalConfig('sig-b', 'ema', {period: 12, source: 'close'}, {color: '#ff0000'}), comparisonConfig('sig-a', 7)]);

        expect(JSON.parse(fingerprint)).toEqual([
            {id: 'sig-a', signalType: 'asset-comparison', params: {assetId: 7}},
            {id: 'sig-b', signalType: 'ema', params: {period: 12, source: 'close'}},
        ]);
    });

    it('ignores the order of the configs and of their params, and leaves the given configs in their order', () => {
        const configs = [signalConfig('sig-b', 'ema', {period: 12, source: 'close'}), signalConfig('sig-a', 'sma', {source: 'open', period: 20})];
        const reordered = [signalConfig('sig-a', 'sma', {period: 20, source: 'open'}), signalConfig('sig-b', 'ema', {source: 'close', period: 12})];

        expect(signalDataContextFingerprint(configs)).toBe(signalDataContextFingerprint(reordered));
        expect(configs.map((config) => config.id)).toEqual(['sig-b', 'sig-a']);
    });

    it('ignores the style of a config', () => {
        const styled = signalConfig('sig-a', 'sma', {period: 20}, {color: '#ff0000', lineWidth: 1});
        const restyled = signalConfig('sig-a', 'sma', {period: 20}, {color: '#00ff00', lineWidth: 3});

        expect(signalDataContextFingerprint([restyled])).toBe(signalDataContextFingerprint([styled]));
    });

    it('ignores every runtime param a comparison load writes back', () => {
        const bare = comparisonConfig('sig-a', 7, {mode: 'percent'});
        const loaded = comparisonConfig('sig-a', 7, {mode: 'percent', ...comparisonRuntimeParams()});

        expect(signalDataContextFingerprint([loaded])).toBe(signalDataContextFingerprint([bare]));
    });

    it.each([
        {label: 'a param value', base: signalConfig('sig-a', 'sma', {period: 20}), changed: signalConfig('sig-a', 'sma', {period: 21})},
        {label: 'an added param', base: signalConfig('sig-a', 'sma', {period: 20}), changed: signalConfig('sig-a', 'sma', {period: 20, source: 'close'})},
        {label: 'the signal type', base: signalConfig('sig-a', 'sma', {period: 20}), changed: signalConfig('sig-a', 'ema', {period: 20})},
        {label: 'the id', base: signalConfig('sig-a', 'sma', {period: 20}), changed: signalConfig('sig-b', 'sma', {period: 20})},
        {label: 'the comparison peer', base: comparisonConfig('sig-a', 7), changed: comparisonConfig('sig-a', 8)},
    ])('changes with $label', ({base, changed}) => {
        expect(signalDataContextFingerprint([changed])).not.toBe(signalDataContextFingerprint([base]));
    });
});

describe('comparisonAssetIds: the distinct positive safe-integer peers of the asset-comparison configs, ascending, without the excluded asset', () => {
    it('reads only asset-comparison configs', () => {
        const configs = [comparisonConfig('cmp-7', 7), signalConfig('fx-1', 'fx-pair', {assetId: 5}), signalConfig('sma-1', 'sma', {assetId: 6, period: 20})];

        expect(comparisonAssetIds(configs)).toEqual([7]);
    });

    it('returns each peer once, in ascending numeric order', () => {
        const configs = [comparisonConfig('cmp-a', 10), comparisonConfig('cmp-b', 9), comparisonConfig('cmp-c', 2), comparisonConfig('cmp-d', 9)];

        expect(comparisonAssetIds(configs)).toEqual([2, 9, 10]);
    });

    it.each([
        {label: 'zero', assetId: 0},
        {label: 'a negative id', assetId: -4},
        {label: 'a fractional id', assetId: 2.5},
        {label: 'NaN', assetId: Number.NaN},
        {label: 'an infinite id', assetId: Number.POSITIVE_INFINITY},
        {label: 'an id beyond the safe integers', assetId: Number.MAX_SAFE_INTEGER + 1},
        {label: 'a string that is not a number', assetId: 'seven'},
        {label: 'null', assetId: null},
        {label: 'a missing id', assetId: undefined},
    ])('drops $label', ({assetId}) => {
        expect(comparisonAssetIds([comparisonConfig('cmp-bad', assetId), comparisonConfig('cmp-ok', 4)])).toEqual([4]);
    });

    it('reads a numeric string as its number, and keeps the largest safe integer', () => {
        const configs = [comparisonConfig('cmp-a', '7'), comparisonConfig('cmp-b', 7), comparisonConfig('cmp-c', Number.MAX_SAFE_INTEGER)];

        expect(comparisonAssetIds(configs)).toEqual([7, Number.MAX_SAFE_INTEGER]);
    });

    it('leaves out the excluded asset, and only it', () => {
        const configs = [comparisonConfig('cmp-a', 3), comparisonConfig('cmp-b', '7'), comparisonConfig('cmp-c', 8)];

        expect(comparisonAssetIds(configs, 7)).toEqual([3, 8]);
        expect(comparisonAssetIds(configs, 99)).toEqual([3, 7, 8]);
        expect(comparisonAssetIds(configs)).toEqual([3, 7, 8]);
    });

    it('gives no peers without configs', () => {
        expect(comparisonAssetIds([])).toEqual([]);
    });
});
