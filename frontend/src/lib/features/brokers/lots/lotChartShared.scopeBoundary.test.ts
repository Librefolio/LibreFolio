/**
 * @vitest-environment node
 *
 * J-48 (workstream J): a TRANSFER leg that crosses the analysis scope is shown as a transfer.
 *
 * The backend reads a TRANSFER leg whose partner sits at a broker outside the lots' scope as an ADJUSTMENT row (J-10,
 * `financial_math/lots/scope_boundary.py`): ADJUSTMENT_IN, at its own cost basis, when it enters the scope;
 * ADJUSTMENT_OUT, at the market value of its day, when it leaves. The figures are right, but the custody modal, the
 * Gantt and the WAC price chart label such a row «Adjustment In/Out». J-48 gives each lot timeline event an optional
 * `scope_boundary`, 'IN' | 'OUT' | null, which the generated client may type scalar-or-array like every optional field
 * of the event (`unwrapScalar`, lotCustodyModalHelpers.ts). The views show a boundary row as a TRANSFER — its label and
 * its marker only: every economic computation keeps reading `kind`.
 *
 * This file pins the two readers lotChartShared gains for the three views:
 * - `scopeBoundaryOf(event)`: 'IN' or 'OUT' as sent, the array shape unwrapped (['IN'] → 'IN'); anything else is no
 *   boundary, `null` — the field null, absent or undefined, an empty array, another case ('in'), another word, a number;
 * - `eventLabelKind(event)`: the kind a view labels an event by — 'TRANSFER_IN' across an IN boundary, 'TRANSFER_OUT'
 *   across an OUT one, the event's own kind otherwise (BUY, SELL, an ADJUSTMENT_IN without a boundary, TRANSFER_DEPART…).
 * The type `ScopeBoundary`, 'IN' | 'OUT', is pinned with `expectTypeOf`: svelte-check reads it, Vitest asserts nothing.
 *
 * Red, before the cure: every case but the control fails with «scopeBoundaryOf is not a function» or «eventLabelKind is
 * not a function». Neither export exists yet, and Vitest reads a missing named export as `undefined`, so the reds stay
 * in this file — which is why the two readers have a file of their own. The case named «control» holds today and after.
 *
 * Fixtures are events as the client receives them (`LotTimelineEventSchema`), carrying the new field; the kinds are the
 * generated client's copy of the backend's enum, read apart from the code under test.
 */
import {describe, expect, expectTypeOf, it} from 'vitest';

import {schemas} from '$lib/api';

import {eventLabelKind, scopeBoundaryOf, type ScopeBoundary} from './lotChartShared';

/** A lot timeline event as the client receives it (`LotTimelineEventSchema`): the fields these cases set, and J-48's. */
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

/** The oracle of «every kind»: the generated client's copy of the backend's LotTimelineEventKind. */
const EVENT_KINDS: readonly string[] = schemas.LotTimelineEventKind.options;

/** Every shape of «no boundary»: the field null, absent or undefined, the array shape empty or holding null, and values the backend never sends. */
const NO_BOUNDARY: ReadonlyArray<{name: string; field: {scope_boundary?: unknown}}> = [
    {name: 'null', field: {scope_boundary: null}},
    {name: 'absent', field: {}},
    {name: 'undefined', field: {scope_boundary: undefined}},
    {name: 'an empty array', field: {scope_boundary: []}},
    {name: '[null]', field: {scope_boundary: [null]}},
    {name: 'in (lower case)', field: {scope_boundary: 'in'}},
    {name: 'X', field: {scope_boundary: 'X'}},
    {name: 'the number 1', field: {scope_boundary: 1}},
];

describe('J-48 — scope boundary', () => {
    describe('scopeBoundaryOf — the boundary an event crosses, or null', () => {
        // RED until J-48's cure: scopeBoundaryOf is not a function.
        it('reads IN off a leg entering the scope and OUT off a leg leaving it', () => {
            expect(scopeBoundaryOf(timelineEvent('ADJUSTMENT_IN', {scope_boundary: 'IN'})), 'J-48: a leg entering the scope').toBe('IN');
            expect(scopeBoundaryOf(timelineEvent('ADJUSTMENT_OUT', {scope_boundary: 'OUT'})), 'J-48: a leg leaving the scope').toBe('OUT');
            // Read by svelte-check, not by Vitest (at run time expectTypeOf asserts nothing): a boundary is IN or OUT and
            // nothing else, and the reader answers one of them or null.
            expectTypeOf<ScopeBoundary>().toEqualTypeOf<'IN' | 'OUT'>();
            expectTypeOf(scopeBoundaryOf).returns.toEqualTypeOf<ScopeBoundary | null>();
        });

        // RED until J-48's cure: scopeBoundaryOf is not a function.
        it('unwraps the scalar-or-array shape of the generated client: [IN] is IN, [OUT] is OUT', () => {
            expect(scopeBoundaryOf(timelineEvent('ADJUSTMENT_IN', {scope_boundary: ['IN']}))).toBe('IN');
            expect(scopeBoundaryOf(timelineEvent('ADJUSTMENT_OUT', {scope_boundary: ['OUT']}))).toBe('OUT');
        });

        // RED until J-48's cure: scopeBoundaryOf is not a function. The no-boundary case beside the two above.
        it.each(NO_BOUNDARY)('reads no boundary, null, when the field is $name', ({field}) => {
            expect(scopeBoundaryOf(timelineEvent('ADJUSTMENT_IN', field))).toBeNull();
        });
    });

    describe('eventLabelKind — the kind a view labels an event by', () => {
        // RED until J-48's cure: eventLabelKind is not a function.
        it('labels a leg entering the scope TRANSFER_IN and a leg leaving it TRANSFER_OUT, no longer as an adjustment', () => {
            expect(eventLabelKind(timelineEvent('ADJUSTMENT_IN', {scope_boundary: 'IN'})), 'J-48: a leg entering the scope').toBe('TRANSFER_IN');
            expect(eventLabelKind(timelineEvent('ADJUSTMENT_OUT', {scope_boundary: 'OUT'})), 'J-48: a leg leaving the scope').toBe('TRANSFER_OUT');
        });

        // RED until J-48's cure: eventLabelKind is not a function.
        it('reads the array shape too: [IN] is TRANSFER_IN, [OUT] is TRANSFER_OUT', () => {
            expect(eventLabelKind(timelineEvent('ADJUSTMENT_IN', {scope_boundary: ['IN']}))).toBe('TRANSFER_IN');
            expect(eventLabelKind(timelineEvent('ADJUSTMENT_OUT', {scope_boundary: ['OUT']}))).toBe('TRANSFER_OUT');
        });

        // RED until J-48's cure: eventLabelKind is not a function. The no-boundary case beside the two above: a real
        // adjustment stays an adjustment, and no other kind moves, whatever shape «no boundary» takes.
        it('labels every kind without a boundary by itself', () => {
            for (const {name, field} of NO_BOUNDARY) {
                expect(
                    EVENT_KINDS.map((kind) => eventLabelKind(timelineEvent(kind, field))),
                    `the field ${name}`,
                ).toEqual(EVENT_KINDS);
            }
        });

        // Control, green before and after the cure: the oracle holds the kinds this file is about, so the sweep above
        // cannot pass on an empty or renamed enum.
        it('control: the client’s LotTimelineEventKind holds the adjustment and transfer kinds, and BUY, SELL, SPLIT', () => {
            expect(EVENT_KINDS).toEqual(expect.arrayContaining(['ADJUSTMENT_IN', 'ADJUSTMENT_OUT', 'TRANSFER_DEPART', 'TRANSFER_ARRIVE', 'BUY', 'SELL', 'SPLIT']));
        });
    });
});
