/**
 * AI Export v2 bump (wave 6, AIX): the three components whose version moves 1 → 2 for T-U9 and MF-C2.
 *
 * WHAT IS UNDER TEST. `portfolio.allocations_cash`, `broker.concentration_context` and
 * `broker.concentration_comparison` keep their schema-1 payload shape; v2 only makes a slice percent `null` when the
 * slices sum to zero or less (MF-C2), moves the shares through `percent_of` and splits the `reason_code` of an
 * unavailable comparison (T-U9). A version the compact renderer does not list silently falls back to YAML, so the
 * list in `snapshotDataRenderer.ts` must carry the new number: this file pins that, without freezing any prompt wording.
 */
import {describe, expect, it} from 'vitest';

import {renderSnapshotDataText} from '../templates/snapshotDataRenderer';

const FALLBACK = 'PAYLOAD YAML FALLBACK';

const directory = {assets: [], brokers: [{broker_id: 5, display_name: 'Named Broker'}], fx_pairs: []};

function section(componentId: string, componentVersion: number, payload: Record<string, unknown>) {
    return {component_id: componentId, component_version: componentVersion, schema_id: componentId, schema_version: 1, payload};
}

function render(componentId: string, componentVersion: number, payload: Record<string, unknown>) {
    const target = componentId.startsWith('broker.') ? {kind: 'broker', broker_id: 5} : {kind: 'portfolio'};
    return renderSnapshotDataText([section(componentId, componentVersion, payload)], target, directory).content;
}

const EUR = (amount: string) => ({code: 'EUR', amount});

const V2_SECTIONS: ReadonlyArray<[string, Record<string, unknown>]> = [
    ['portfolio.allocations_cash', {by_type: [{name: 'ETF', percent: null, amount: EUR('100'), emoji: null}], by_sector: [], by_geography: []}],
    [
        'broker.concentration_context',
        {
            broker_id: 5,
            as_of: '2024-12-31',
            target_currency: 'EUR',
            position_count: 1,
            allocation_by_type: [{name: 'ETF', percent: null, amount: EUR('100'), emoji: null}],
            allocation_by_sector: [],
            allocation_by_geography: [],
            allocation_by_currency: [],
        },
    ],
    ['broker.concentration_comparison', {status: 'unavailable', reason_code: 'broker_has_no_positions', message: 'placeholder', broker_id: 5, target_currency: 'EUR'}],
];

describe('AI Export v2 bump — T-U9 and MF-C2', () => {
    it.each(V2_SECTIONS)('%s v2 renders compactly, not as YAML', (componentId, payload) => {
        expect(render(componentId, 2, payload)).not.toContain(FALLBACK);
    });

    it.each(V2_SECTIONS)('%s v3 is unknown to the renderer and falls back to YAML', (componentId, payload) => {
        expect(render(componentId, 3, payload)).toContain(FALLBACK);
    });

    it('keeps a null slice percent as the literal null, never 0', () => {
        const [, payload] = V2_SECTIONS[0];
        const content = render('portfolio.allocations_cash', 2, payload);
        expect(content).toContain('null');
    });
});
