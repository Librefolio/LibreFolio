/**
 * syncHelpers — the question a page asks before its sync dialog warns (C-66, F-094).
 *
 * A sync writes every date the data provider returns and replaces what is stored,
 * manual edits included: the provider wins. So the dialog says so before Start
 * when the range it is about to sync already holds stored rows, and only the page
 * knows that, from the points it shows. `hasStoredPointInRange` is that question
 * for one item: is there a point inside [start, end], both bounds included, that
 * is a stored row?
 *
 * A point filled backward from an earlier date is not one: it stands for a row
 * that lies before its own date. The rule is `extractDaysBack` in
 * assetPriceDerived.ts, its one home — `days_back` (the snake_case API shape) or
 * `daysBack` (the camelCase cache shape) above 0 — so both shapes are exercised
 * here. A `'min'` start is the MAX range: no lower bound.
 *
 * Dates are ISO `YYYY-MM-DD` strings throughout, as the pages hold them.
 *
 * (`formatElapsed` and `formatTime`, also in syncHelpers, are covered in
 * syncToastHelpers.test.ts.)
 *
 * Red today: `hasStoredPointInRange` does not exist.
 */
import {describe, expect, it} from 'vitest';
import {hasStoredPointInRange} from '../syncHelpers';

const START = '2024-03-01';
const END = '2024-03-31';

describe('hasStoredPointInRange', () => {
    it('is false for an item with no points', () => {
        expect(hasStoredPointInRange([], START, END)).toBe(false);
    });

    it.each([
        {where: 'inside the range', date: '2024-03-15', expected: true},
        {where: 'on its first day', date: START, expected: true},
        {where: 'on its last day', date: END, expected: true},
        {where: 'the day before it', date: '2024-02-29', expected: false},
        {where: 'the day after it', date: '2024-04-01', expected: false},
    ])('answers $expected for a stored point $where', ({date, expected}) => {
        expect(hasStoredPointInRange([{date}], START, END)).toBe(expected);
    });

    it("reads a 'min' start as no lower bound, and still honours the end", () => {
        expect(hasStoredPointInRange([{date: '1990-01-02'}], 'min', END)).toBe(true);
        expect(hasStoredPointInRange([{date: '2024-04-01'}], 'min', END)).toBe(false);
    });

    it.each([
        {shape: 'snake_case days_back', point: {date: '2024-03-15', backward_fill_info: {days_back: 3}}},
        {shape: 'camelCase daysBack', point: {date: '2024-03-15', backwardFillInfo: {daysBack: 3}}},
    ])('never counts a point filled backward ($shape = 3), even inside the range', ({point}) => {
        expect(hasStoredPointInRange([point], START, END)).toBe(false);
    });

    it.each([
        {shape: 'snake_case days_back = 0', point: {date: '2024-03-15', backward_fill_info: {days_back: 0}}},
        {shape: 'camelCase daysBack = 0', point: {date: '2024-03-15', backwardFillInfo: {daysBack: 0}}},
        {shape: 'both shapes null', point: {date: '2024-03-15', backward_fill_info: null, backwardFillInfo: null}},
    ])('counts a point filled from no earlier date: $shape', ({point}) => {
        expect(hasStoredPointInRange([point], START, END)).toBe(true);
    });

    it('needs one point that is both stored and in the range', () => {
        const filledInside = {date: '2024-03-15', backward_fill_info: {days_back: 2}};
        const storedOutside = {date: '2024-04-02'};

        // Each half of the condition is met, by a different point: no stored row lies in the range.
        expect(hasStoredPointInRange([filledInside, storedOutside], START, END)).toBe(false);
        // One point that meets both is enough, wherever it sits in the list.
        expect(hasStoredPointInRange([filledInside, storedOutside, {date: '2024-03-20'}], START, END)).toBe(true);
    });
});
