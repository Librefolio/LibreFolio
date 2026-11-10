/**
 * Which positions closed inside the period the Portfolio table lists as sold out (T1, Y6-7; MF-CB's `closed_by`).
 *
 * A position closed by selling is sold, and stays listed (in italics). A position closed by a *transfer* to a broker that
 * is in the report and still holds the asset has not left the portfolio: it moved, so listing it as sold out beside the
 * destination's full row would say the opposite of what happened — it is not listed. Every other closure stays: a transfer
 * to a broker that is not in the report (the units did leave this view), an orphan transfer, an adjustment, and a closure
 * the engine does not name.
 */
import {describe, expect, it} from 'vitest';
import {closedPositionsToList, type ClosedPositionLike} from './closedPositions';

const closed = (assetId: number, brokerId: number, closedBy: ClosedPositionLike['closed_by'], closedTo: number | null = null): ClosedPositionLike => ({asset_id: assetId, broker_id: brokerId, is_fully_sold: true, closed_by: closedBy, closed_to_broker_id: closedTo});
const open = (assetId: number, brokerId: number): ClosedPositionLike => ({asset_id: assetId, broker_id: brokerId, is_fully_sold: false});
const held = (assetId: number, brokerId: number) => ({asset_id: assetId, broker_id: brokerId});
const ids = (list: ClosedPositionLike[]) => list.map((p) => `${p.asset_id}-${p.broker_id}`);

describe('closedPositionsToList', () => {
    it('lists a sale, whatever the other brokers hold', () => {
        expect(ids(closedPositionsToList([closed(5, 1, 'SELL')], [held(5, 2)]))).toEqual(['5-1']);
    });

    it('does not list a transfer to a broker in the report that holds the asset: it moved, it was not sold', () => {
        expect(closedPositionsToList([closed(5, 1, 'TRANSFER', 2)], [held(5, 2)])).toEqual([]);
    });

    it('lists a transfer to a broker the report does not hold the asset in (not selected, or sold since)', () => {
        expect(ids(closedPositionsToList([closed(5, 1, 'TRANSFER', 2)], [held(6, 2), held(5, 3)]))).toEqual(['5-1']);
        expect(ids(closedPositionsToList([closed(5, 1, 'TRANSFER', 2)], []))).toEqual(['5-1']);
    });

    it('lists a transfer whose destination is unknown (an orphan leg, or a broker the user cannot read)', () => {
        expect(ids(closedPositionsToList([closed(5, 1, 'TRANSFER', null)], [held(5, 2)]))).toEqual(['5-1']);
    });

    it('lists an adjustment, and a closure the engine does not name', () => {
        expect(ids(closedPositionsToList([closed(5, 1, 'ADJUSTMENT'), closed(6, 1, null)], [held(5, 2), held(6, 2)]))).toEqual(['5-1', '6-1']);
    });

    it('keeps the order, and ignores positions that are not closed', () => {
        const positions = [open(1, 1), closed(5, 1, 'SELL'), closed(6, 1, 'TRANSFER', 2), closed(7, 1, 'SELL')];
        expect(ids(closedPositionsToList(positions, [held(6, 2)]))).toEqual(['5-1', '7-1']);
    });

    it('does not mistake the same broker for the destination', () => {
        expect(ids(closedPositionsToList([closed(5, 1, 'TRANSFER', 1)], [held(5, 1)]))).toEqual(['5-1']);
    });
});
