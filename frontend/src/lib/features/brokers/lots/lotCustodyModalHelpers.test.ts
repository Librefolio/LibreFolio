/**
 * @vitest-environment node
 *
 * Branch-exhaustive unit tests for the pure helpers extracted from
 * LotCustodyModal.svelte. Every `??`, `||`, `if`, and `switch`-like arm below
 * is exercised in both directions; ECharts/DOM never enter because none of
 * these functions touch them.
 */
import {describe, it, expect} from 'vitest';
import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {unwrapScalar, getBroker, historyKey, eventMarkerKind, closureValueLabelKey, groupCustodySlices, compareHistoryEvents, type CustodyGroup} from './lotCustodyModalHelpers';

const brokers: BrokerLike[] = [
    {id: 1, name: 'Fineco'},
    {id: 2, name: 'Directa'},
    {id: 3, name: 'Degiro'},
];

describe('unwrapScalar', () => {
    it('returns the value itself for a plain scalar (not-array branch)', () => {
        expect(unwrapScalar<number>(42)).toBe(42);
    });

    it('returns the first element for a non-empty array (array branch, ?? left)', () => {
        expect(unwrapScalar<number>([7, 8, 9])).toBe(7);
    });

    it('returns null for an empty array (array branch, ?? right)', () => {
        expect(unwrapScalar<number>([])).toBeNull();
    });

    it('returns null when the first element is null (array branch, ?? right)', () => {
        expect(unwrapScalar<number>([null as unknown as number])).toBeNull();
    });

    it('passes null through unchanged (not-array branch)', () => {
        expect(unwrapScalar<number>(null)).toBeNull();
    });

    it('passes undefined through unchanged (not-array branch)', () => {
        expect(unwrapScalar<number>(undefined)).toBeUndefined();
    });
});

describe('getBroker', () => {
    it('returns null when the id is null (no-id branch)', () => {
        expect(getBroker(null, brokers)).toBeNull();
    });

    it('returns null when the id is undefined (no-id branch)', () => {
        expect(getBroker(undefined, brokers)).toBeNull();
    });

    it('returns null when the array unwraps to null (no-id branch after unwrap)', () => {
        expect(getBroker([null], brokers)).toBeNull();
    });

    it('returns the matching broker for a scalar id (?? left branch)', () => {
        expect(getBroker(2, brokers)).toEqual({id: 2, name: 'Directa'});
    });

    it('unwraps an array id then matches (array + ?? left branch)', () => {
        expect(getBroker([3], brokers)).toEqual({id: 3, name: 'Degiro'});
    });

    it('returns a synthetic #id placeholder on a miss (?? right branch)', () => {
        expect(getBroker(99, brokers)).toEqual({id: 99, name: '#99'});
    });

    it('returns a synthetic placeholder against an empty broker list', () => {
        expect(getBroker(5, [])).toEqual({id: 5, name: '#5'});
    });
});

describe('historyKey', () => {
    it('joins all five parts when both optional ids are present (?? left, ?? left)', () => {
        expect(
            historyKey({
                date: '2024-03-15',
                kind: 'BUY',
                transaction_id: 10,
                related_transaction_id: 20,
                fragment_id: 'frag-a',
            }),
        ).toBe('2024-03-15:BUY:10:20:frag-a');
    });

    it('leaves the related/fragment parts empty when both are null (?? right, ?? right)', () => {
        expect(
            historyKey({
                date: '2024-03-15',
                kind: 'SELL',
                transaction_id: 11,
                related_transaction_id: null,
                fragment_id: null,
            }),
        ).toBe('2024-03-15:SELL:11::');
    });

    it('leaves the related/fragment parts empty when both are undefined (?? right, ?? right)', () => {
        expect(historyKey({date: '2024-01-01', kind: 'SPLIT', transaction_id: 12})).toBe('2024-01-01:SPLIT:12::');
    });

    it('fills only related when fragment is absent (?? left, ?? right)', () => {
        expect(historyKey({date: '2024-02-02', kind: 'TRANSFER_DEPART', transaction_id: 13, related_transaction_id: 40})).toBe('2024-02-02:TRANSFER_DEPART:13:40:');
    });
});

describe('eventMarkerKind', () => {
    it.each([
        ['BUY', 'open'],
        ['ADJUSTMENT_IN', 'open'],
        ['TRANSFER_DEPART', 'transfer'],
        ['TRANSFER_ARRIVE', 'transfer'],
        ['SPLIT', 'split'],
        ['SELL', 'close'],
        ['ADJUSTMENT_OUT', 'close'],
        ['ANYTHING_ELSE', 'close'],
    ])('classifies %s as %s', (kind, expected) => {
        expect(eventMarkerKind({kind})).toBe(expected);
    });
});

describe('groupCustodySlices', () => {
    it('returns an empty array for no slices', () => {
        expect(groupCustodySlices([], brokers)).toEqual([]);
    });

    it('merges slices sharing (type, broker) and sums their quantities (existing-group branch)', () => {
        const groups = groupCustodySlices(
            [
                {broker_id: 1, custody_type: 'BROKER', quantity: '10'},
                {broker_id: 1, custody_type: 'BROKER', quantity: '2.5'},
            ],
            brokers,
        );
        expect(groups).toHaveLength(1);
        expect(groups[0]).toMatchObject({key: 'BROKER:1', brokerId: 1, custodyType: 'BROKER', quantity: 12.5});
        expect(groups[0].broker).toEqual({id: 1, name: 'Fineco'});
    });

    it('resolves a synthetic broker for a BROKER slice with an unknown id (BROKER + miss)', () => {
        const groups = groupCustodySlices([{broker_id: 77, custody_type: 'BROKER', quantity: '1'}], brokers);
        expect(groups[0].broker).toEqual({id: 77, name: '#77'});
    });

    it('keeps broker null for IN_TRANSIT even when a broker_id is present (non-BROKER branch)', () => {
        const groups = groupCustodySlices([{broker_id: 1, custody_type: 'IN_TRANSIT', quantity: '4'}], brokers);
        expect(groups[0]).toMatchObject({key: 'IN_TRANSIT:1', custodyType: 'IN_TRANSIT', broker: null});
    });

    it('uses the "none" key when a broker id is absent (?? none branch)', () => {
        const groups = groupCustodySlices([{broker_id: null, custody_type: 'IN_TRANSIT', quantity: '3'}], brokers);
        expect(groups[0]).toMatchObject({key: 'IN_TRANSIT:none', brokerId: null, broker: null});
    });

    it('treats an unparseable quantity as 0 (safeDecimal ?? 0 branch)', () => {
        const groups = groupCustodySlices(
            [
                {broker_id: 2, custody_type: 'BROKER', quantity: 'not-a-number'},
                {broker_id: 2, custody_type: 'BROKER', quantity: '5'},
            ],
            brokers,
        );
        expect(groups[0].quantity).toBe(5);
    });

    it('unwraps an array broker_id before grouping', () => {
        const groups = groupCustodySlices([{broker_id: [3], custody_type: 'BROKER', quantity: '1'}], brokers);
        expect(groups[0]).toMatchObject({brokerId: 3, key: 'BROKER:3'});
    });

    it('preserves first-seen order across distinct groups (new-group branch, multiple)', () => {
        const groups: CustodyGroup[] = groupCustodySlices(
            [
                {broker_id: 2, custody_type: 'BROKER', quantity: '1'},
                {broker_id: null, custody_type: 'IN_TRANSIT', quantity: '1'},
                {broker_id: 1, custody_type: 'BROKER', quantity: '1'},
            ],
            brokers,
        );
        expect(groups.map((g) => g.key)).toEqual(['BROKER:2', 'IN_TRANSIT:none', 'BROKER:1']);
    });
});

describe('compareHistoryEvents', () => {
    it('orders by ISO date ascending (date-differs branch, negative)', () => {
        expect(compareHistoryEvents({date: '2024-01-01', transaction_id: 5}, {date: '2024-02-01', transaction_id: 1})).toBeLessThan(0);
    });

    it('orders by ISO date ascending (date-differs branch, positive)', () => {
        expect(compareHistoryEvents({date: '2024-03-01', transaction_id: 1}, {date: '2024-02-01', transaction_id: 9})).toBeGreaterThan(0);
    });

    it('breaks ties by transaction id when dates match (tie-break branch, negative)', () => {
        expect(compareHistoryEvents({date: '2024-01-01', transaction_id: 3}, {date: '2024-01-01', transaction_id: 8})).toBeLessThan(0);
    });

    it('breaks ties by transaction id when dates match (tie-break branch, positive)', () => {
        expect(compareHistoryEvents({date: '2024-01-01', transaction_id: 8}, {date: '2024-01-01', transaction_id: 3})).toBeGreaterThan(0);
    });

    it('returns 0 for identical date and transaction id', () => {
        expect(compareHistoryEvents({date: '2024-01-01', transaction_id: 3}, {date: '2024-01-01', transaction_id: 3})).toBe(0);
    });

    it('sorts a list into (date, id) order', () => {
        const sorted = [
            {date: '2024-02-01', transaction_id: 2},
            {date: '2024-01-01', transaction_id: 9},
            {date: '2024-01-01', transaction_id: 4},
        ].sort(compareHistoryEvents);
        expect(sorted.map((e) => e.transaction_id)).toEqual([4, 9, 2]);
    });
});

/*
 * J-48 (workstream J) — a TRANSFER leg crossing the analysis scope is a transfer on the modal's timeline.
 *
 * The contract. The backend reads a TRANSFER leg whose partner sits at a broker outside the lots' scope as an
 * ADJUSTMENT_IN (entering) or an ADJUSTMENT_OUT (leaving) row (J-10), so the timeline draws it as an opening or as a
 * closure. J-48 gives each lot timeline event an optional `scope_boundary`, 'IN' | 'OUT' | null, which the generated
 * client may type scalar-or-array (`unwrapScalar`), and the modal shows a boundary row as a transfer — its marker and its
 * label only:
 * - `eventMarkerKind(event)` answers 'transfer' for an ADJUSTMENT_IN or an ADJUSTMENT_OUT carrying a boundary, and
 *   classifies it by its kind as before without one: 'open', 'close';
 * - the value row keeps reading `kind`: a leg leaving the scope still hands its units over, at the market value of its
 *   day (J-10), so `closureValueLabelKey` keeps the handed-over key, never the proceeds one.
 *
 * Red, before the cure: the boundary cases of `eventMarkerKind`, on their assertion — today it reads the kind alone. The
 * cases named «control» hold today and after the cure. Events are built as the modal receives them and passed as
 * variables, so this block type-checks before the cure and after it; keys are asserted, never their translations.
 */

/** A lot timeline event as the modal receives it (`LotTimelineEventSchema`): the fields these cases set, and J-48's. */
interface WireLotEvent {
    lot_id: number;
    date: string;
    kind: string;
    transaction_id: number;
    quantity: string;
    scope_boundary?: unknown;
}

/** An event of `kind` on lot 7, with `field` spread in: the boundary as sent, or nothing at all. */
function timelineEvent(kind: string, field: {scope_boundary?: unknown} = {}): WireLotEvent {
    return {lot_id: 7, date: '2024-03-15', kind, transaction_id: 4201, quantity: '10', ...field};
}

describe('J-48 — scope boundary', () => {
    /** «No boundary» as the modal may receive it: the field absent or null, or the array shape empty or holding null. */
    const NO_BOUNDARY: ReadonlyArray<{name: string; field: {scope_boundary?: unknown}}> = [
        {name: 'absent', field: {}},
        {name: 'null', field: {scope_boundary: null}},
        {name: 'an empty array', field: {scope_boundary: []}},
        {name: '[null]', field: {scope_boundary: [null]}},
    ];

    // RED until J-48's cure: today the marker reads the kind alone — 'open' for ADJUSTMENT_IN, 'close' for ADJUSTMENT_OUT.
    it.each([
        {name: 'ADJUSTMENT_IN across IN', kind: 'ADJUSTMENT_IN', boundary: 'IN'},
        {name: 'ADJUSTMENT_OUT across OUT', kind: 'ADJUSTMENT_OUT', boundary: 'OUT'},
        {name: 'ADJUSTMENT_IN across [IN], the array shape', kind: 'ADJUSTMENT_IN', boundary: ['IN']},
        {name: 'ADJUSTMENT_OUT across [OUT], the array shape', kind: 'ADJUSTMENT_OUT', boundary: ['OUT']},
    ] as ReadonlyArray<{name: string; kind: string; boundary: unknown}>)('eventMarkerKind: $name is a transfer', ({kind, boundary}) => {
        expect(eventMarkerKind(timelineEvent(kind, {scope_boundary: boundary})), 'J-48: a leg crossing the scope is a transfer on the timeline').toBe('transfer');
    });

    // Control, green before and after the cure: the no-boundary case beside each red.
    it.each([
        {kind: 'ADJUSTMENT_IN', marker: 'open'},
        {kind: 'ADJUSTMENT_OUT', marker: 'close'},
    ])('control: eventMarkerKind — $kind without a boundary is still $marker', ({kind, marker}) => {
        for (const {name, field} of NO_BOUNDARY) {
            expect(eventMarkerKind(timelineEvent(kind, field)), `the field ${name}`).toBe(marker);
        }
    });

    // Control, green before and after the cure: a null boundary moves no other kind.
    it('control: eventMarkerKind — every other kind keeps its marker under a null boundary', () => {
        const kinds = ['BUY', 'SELL', 'SPLIT', 'TRANSFER_DEPART', 'TRANSFER_ARRIVE'];
        expect(kinds.map((kind) => eventMarkerKind(timelineEvent(kind, {scope_boundary: null})))).toEqual(['open', 'close', 'split', 'transfer', 'transfer']);
    });

    // Control, green before and after the cure: the value row reads the kind, whatever label the row gets.
    it('control: closureValueLabelKey — a leg leaving the scope still hands its units over: its ADJUSTMENT_OUT reads handedOver, not proceeds', () => {
        const leaving = timelineEvent('ADJUSTMENT_OUT', {scope_boundary: 'OUT'});
        expect(closureValueLabelKey(leaving.kind)).toBe('brokers.lots.modal.historyDetail.handedOver');
    });
});
