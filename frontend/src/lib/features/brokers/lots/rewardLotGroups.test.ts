/**
 * rewardLotGroups — the pure logic of the reward lots group in the Lots table (project 79, STK-2c; P-25, Q-5).
 *
 * The contract, one block per export:
 * - `groupRewardLots`: the reward lots of one broker form a group when there are at least two; one alone stays a lot,
 *   none is no group. One group per broker, its lots in opening order (date, then lot id), whatever order they came in.
 * - `arrangeRows`: the rows in display order. A closed group shows its head only; an open one its lots right after the
 *   head. With a comparator the heads and the loose lots are sorted together and each open group's lots are sorted the
 *   same way, but stay under their head: they never interleave with the loose lots.
 * - `lotRowsOf`: the lots behind some rows, each once (a head stands for its lots; head and its lots together count once).
 * - `lotsAfterTableSelection`: the lot selection after a table selection change. A head checked or unchecked takes all its
 *   lots; a lot row only itself; lots no row shows keep their state; ids that are neither a lot nor a known group are
 *   ignored.
 * - `groupSelection`, `tableRowIdsFor`: the selection the table draws from a set of lot ids.
 *
 * Every fixture is built here: rows are plain objects with the four fields the module reads.
 */
import {describe, expect, it} from 'vitest';
import {arrangeRows, groupRewardLots, groupSelection, isRewardGroupId, lotRowsOf, lotsAfterTableSelection, rewardGroupId, tableRowIdsFor, type GroupableRow} from './rewardLotGroups';

interface Row extends GroupableRow {
    reward: boolean;
    pnl: number;
}

function lot(lotId: number, openingDate: string, {broker = 1, reward = true, pnl = 0}: {broker?: number; reward?: boolean; pnl?: number} = {}): Row {
    return {rowId: String(lotId), lotId, openingBrokerId: broker, openingDate, reward, pnl};
}

const isReward = (row: Row) => row.reward;
const ids = (rows: readonly {rowId: string}[]) => rows.map((row) => row.rowId);
const lotIds = (rows: readonly {lotId: number}[]) => rows.map((row) => row.lotId);

/** A head row as the table builds it: its own id, lotId -1, the sum of its lots' P&L. */
function head(groupId: string, members: readonly Row[]): Row {
    return {rowId: groupId, lotId: -1, openingBrokerId: members[0].openingBrokerId, openingDate: members[0].openingDate, reward: true, pnl: members.reduce((sum, row) => sum + row.pnl, 0)};
}

const byPnl =
    (direction: 'asc' | 'desc') =>
    (a: Row, b: Row): number =>
        direction === 'asc' ? a.pnl - b.pnl : b.pnl - a.pnl;

describe('rewardGroupId / isRewardGroupId', () => {
    it('names one group per broker, never a number', () => {
        expect(rewardGroupId(7)).toBe('reward-group:7');
        expect(isRewardGroupId(rewardGroupId(7))).toBe(true);
        expect(isRewardGroupId('7')).toBe(false);
        expect(Number.isInteger(Number(rewardGroupId(7)))).toBe(false);
    });
});

describe('groupRewardLots', () => {
    it('groups two or more reward lots of one broker; the non-reward lots stay out', () => {
        const groups = groupRewardLots([lot(1, '2024-01-10', {reward: false}), lot(2, '2024-02-01'), lot(3, '2024-03-01'), lot(4, '2024-04-01')], isReward);
        expect([...groups.keys()]).toEqual([rewardGroupId(1)]);
        expect(lotIds(groups.get(rewardGroupId(1))!)).toEqual([2, 3, 4]);
    });

    it('leaves a single reward lot alone: no group', () => {
        const groups = groupRewardLots([lot(1, '2024-01-10', {reward: false}), lot(2, '2024-02-01')], isReward);
        expect(groups.size).toBe(0);
    });

    it('makes no group without reward lots', () => {
        expect(groupRewardLots([lot(1, '2024-01-10', {reward: false}), lot(2, '2024-02-01', {reward: false})], isReward).size).toBe(0);
        expect(groupRewardLots([], isReward).size).toBe(0);
    });

    it('makes one group per broker, and none for a broker with one reward lot', () => {
        const rows = [lot(1, '2024-01-01', {broker: 2}), lot(2, '2024-01-02', {broker: 1}), lot(3, '2024-01-03', {broker: 2}), lot(4, '2024-01-04', {broker: 1}), lot(5, '2024-01-05', {broker: 3})];
        const groups = groupRewardLots(rows, isReward);
        expect(new Set(groups.keys())).toEqual(new Set([rewardGroupId(1), rewardGroupId(2)]));
        expect(lotIds(groups.get(rewardGroupId(1))!)).toEqual([2, 4]);
        expect(lotIds(groups.get(rewardGroupId(2))!)).toEqual([1, 3]);
    });

    it('orders a group by opening date, then lot id, whatever order the lots came in', () => {
        const rows = [lot(9, '2024-03-01'), lot(5, '2024-01-15'), lot(7, '2024-03-01'), lot(8, '2024-01-15')];
        const groups = groupRewardLots(rows, isReward);
        expect(lotIds(groups.get(rewardGroupId(1))!)).toEqual([5, 8, 7, 9]);
        // The rows handed in keep their order
        expect(lotIds(rows)).toEqual([9, 5, 7, 8]);
    });
});

describe('arrangeRows', () => {
    // Loose lots 15 and 30; a group of three lots of P&L 10, 20, 40 (head 70). A flat sort would interleave them.
    const loose = [lot(1, '2024-01-01', {reward: false, pnl: 30}), lot(2, '2024-01-02', {reward: false, pnl: 15})];
    const members = [lot(11, '2024-02-01', {pnl: 20}), lot(12, '2024-03-01', {pnl: 40}), lot(13, '2024-04-01', {pnl: 10})];
    const groupId = rewardGroupId(1);
    const groups = new Map([[groupId, members]]);
    const top = [loose[0], head(groupId, members), loose[1]];

    it('closed: the head stands alone, in the order given', () => {
        expect(ids(arrangeRows(top, groups, new Set()))).toEqual(['1', groupId, '2']);
    });

    it('open: the group lots follow their head, in group order', () => {
        expect(ids(arrangeRows(top, groups, new Set([groupId])))).toEqual(['1', groupId, '11', '12', '13', '2']);
    });

    it('ascending: heads and loose lots sorted together, the group lots sorted under their head', () => {
        expect(ids(arrangeRows(top, groups, new Set([groupId]), byPnl('asc')))).toEqual(['2', '1', groupId, '13', '11', '12']);
    });

    it('descending: the same, reversed, the lots still under their head', () => {
        expect(ids(arrangeRows(top, groups, new Set([groupId]), byPnl('desc')))).toEqual([groupId, '12', '11', '13', '1', '2']);
    });

    it('sorted and closed: the head sorts on its own value, its lots stay hidden', () => {
        expect(ids(arrangeRows(top, groups, new Set(), byPnl('desc')))).toEqual([groupId, '1', '2']);
    });

    it('leaves the rows and the group it was given unsorted', () => {
        arrangeRows(top, groups, new Set([groupId]), byPnl('asc'));
        expect(ids(top)).toEqual(['1', groupId, '2']);
        expect(lotIds(members)).toEqual([11, 12, 13]);
    });

    it('opens only the groups asked: two groups, one open', () => {
        const other = rewardGroupId(2);
        const otherMembers = [lot(21, '2024-05-01', {broker: 2, pnl: 1}), lot(22, '2024-06-01', {broker: 2, pnl: 2})];
        const both = new Map([...groups, [other, otherMembers]]);
        expect(ids(arrangeRows([head(groupId, members), head(other, otherMembers)], both, new Set([other])))).toEqual([groupId, other, '21', '22']);
    });
});

describe('lotRowsOf', () => {
    const members = [lot(11, '2024-02-01'), lot(12, '2024-03-01')];
    const groupId = rewardGroupId(1);
    const groups = new Map([[groupId, members]]);
    const loose = lot(1, '2024-01-01', {reward: false});

    it('expands a head to its lots', () => {
        expect(lotIds(lotRowsOf([loose, head(groupId, members)], groups))).toEqual([1, 11, 12]);
    });

    it('counts a lot once when its head and the lot are both there', () => {
        const rows = [head(groupId, members), ...members, loose];
        expect(lotIds(lotRowsOf(rows, groups))).toEqual([11, 12, 1]);
        // A lot listed before its head is not repeated either
        expect(lotIds(lotRowsOf([members[1], loose, head(groupId, members)], groups))).toEqual([12, 1, 11]);
    });

    it('without groups returns the rows as given', () => {
        expect(lotIds(lotRowsOf([loose, ...members], new Map()))).toEqual([1, 11, 12]);
    });
});

describe('lotsAfterTableSelection', () => {
    const members = [lot(11, '2024-02-01'), lot(12, '2024-03-01'), lot(13, '2024-04-01')];
    const groupId = rewardGroupId(1);
    const groups = new Map([[groupId, members]]);

    it('a head checked takes all its lots', () => {
        expect(lotsAfterTableSelection([], [], [groupId], groups)).toEqual([11, 12, 13]);
    });

    it('a head unchecked drops all its lots, and only them', () => {
        expect(lotsAfterTableSelection([1, 11, 12, 13], ['1', groupId], ['1'], groups)).toEqual([1]);
    });

    it('a lot row toggles that lot only', () => {
        expect(lotsAfterTableSelection([], [], ['12'], groups)).toEqual([12]);
        expect(lotsAfterTableSelection([11, 12], ['11', '12'], ['11'], groups)).toEqual([11]);
    });

    it('keeps the lots no row shows: a closed group partly selected, a loose lot checked beside it', () => {
        // Lot 12 was selected inside the group, then the group closed: no row shows it, so its state stays
        expect(lotsAfterTableSelection([12], [], ['1'], groups)).toEqual([1, 12]);
    });

    it('rows unchanged between before and after change nothing', () => {
        expect(lotsAfterTableSelection([1, 12], ['1'], ['1'], groups)).toEqual([1, 12]);
    });

    it('ignores ids that are neither a lot nor a known group', () => {
        expect(lotsAfterTableSelection([5], [], ['abc', '1.5', rewardGroupId(99)], groups)).toEqual([5]);
        expect(lotsAfterTableSelection([5], ['abc', '1.5', rewardGroupId(99)], [], groups)).toEqual([5]);
    });

    it('ignores an empty and a blank row id: neither reads as lot 0', () => {
        // Number('') and Number('  ') are 0: read as a lot, checking them would add lot 0
        expect(lotsAfterTableSelection([5], [], ['', '  '], groups)).toEqual([5]);
        // ...and unchecking them would drop a lot 0 that is selected
        expect(lotsAfterTableSelection([0, 5], ['', '  '], [], groups)).toEqual([0, 5]);
    });

    it('returns the lot ids sorted', () => {
        expect(lotsAfterTableSelection([30, 2], [], [groupId, '7'], groups)).toEqual([2, 7, 11, 12, 13, 30]);
    });
});

describe('groupSelection', () => {
    const members = [lot(11, '2024-02-01'), lot(12, '2024-03-01'), lot(13, '2024-04-01')];

    it('unchecked with none, partial with some, checked with all of its lots', () => {
        expect(groupSelection(members, new Set())).toBe('unchecked');
        expect(groupSelection(members, new Set([1, 99]))).toBe('unchecked');
        expect(groupSelection(members, new Set([12]))).toBe('partial');
        expect(groupSelection(members, new Set([11, 13]))).toBe('partial');
        expect(groupSelection(members, new Set([11, 12, 13, 1]))).toBe('checked');
    });
});

describe('tableRowIdsFor', () => {
    const members = [lot(11, '2024-02-01'), lot(12, '2024-03-01'), lot(13, '2024-04-01')];
    const groupId = rewardGroupId(1);
    const groups = new Map([[groupId, members]]);
    const loose = lot(1, '2024-01-01', {reward: false});

    it('closed group: the head when all its lots are selected, nothing for part of them', () => {
        const shown = [loose, head(groupId, members)];
        expect(tableRowIdsFor([11, 12, 13], shown, groups)).toEqual([groupId]);
        expect(tableRowIdsFor([1, 12], shown, groups)).toEqual(['1']);
    });

    it('open group: every selected lot row shown, and the head when all its lots are', () => {
        const shown = [loose, head(groupId, members), ...members];
        expect(tableRowIdsFor([1, 11, 12, 13], shown, groups)).toEqual(['1', groupId, '11', '12', '13']);
        expect(tableRowIdsFor([12], shown, groups)).toEqual(['12']);
    });

    it('a selected lot no row shows has no row id', () => {
        expect(tableRowIdsFor([1, 42], [loose], groups)).toEqual(['1']);
    });
});
