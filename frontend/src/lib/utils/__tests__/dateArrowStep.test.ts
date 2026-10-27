import {beforeEach, describe, expect, it} from 'vitest';
import {dateArrowStep, resetDateArrowHold, shiftIsoDate} from '$lib/utils/core/dateArrowStep';

describe('shiftIsoDate', () => {
    it('moves whole days across month and year boundaries', () => {
        expect(shiftIsoDate('2024-01-31', 'day', 1)).toBe('2024-02-01');
        expect(shiftIsoDate('2024-01-01', 'day', -1)).toBe('2023-12-31');
        expect(shiftIsoDate('2024-02-28', 'day', 1)).toBe('2024-02-29');
    });

    it('clamps the day to the target month instead of spilling into the next one', () => {
        expect(shiftIsoDate('2024-01-31', 'month', 1)).toBe('2024-02-29');
        expect(shiftIsoDate('2023-01-31', 'month', 1)).toBe('2023-02-28');
        expect(shiftIsoDate('2024-03-31', 'month', -1)).toBe('2024-02-29');
    });

    it('wraps months into years in both directions', () => {
        expect(shiftIsoDate('2024-12-15', 'month', 1)).toBe('2025-01-15');
        expect(shiftIsoDate('2024-01-15', 'month', -1)).toBe('2023-12-15');
        expect(shiftIsoDate('2024-01-15', 'month', -13)).toBe('2022-12-15');
    });

    it('keeps 29 February readable when the target year has none', () => {
        expect(shiftIsoDate('2024-02-29', 'year', 1)).toBe('2025-02-28');
        expect(shiftIsoDate('2024-02-29', 'year', 4)).toBe('2028-02-29');
    });

    it('leaves anything that is not an ISO date alone', () => {
        expect(shiftIsoDate('', 'day', 1)).toBe('');
        expect(shiftIsoDate('15/08/2024', 'day', 1)).toBe('15/08/2024');
    });
});

describe('dateArrowStep hold acceleration', () => {
    const target = {} as EventTarget;
    const TODAY = '2024-08-15';

    function press(iso: string, {repeat, key = 'ArrowUp'}: {repeat: boolean; key?: string}): string {
        const event = {key, repeat, target, ctrlKey: false, metaKey: false, altKey: false, preventDefault: () => {}} as unknown as KeyboardEvent;
        return dateArrowStep(event, iso, TODAY) as string;
    }

    beforeEach(() => resetDateArrowHold());

    it('ignores keys that are not arrows', () => {
        const event = {key: 'a', repeat: false, target, preventDefault: () => {}} as unknown as KeyboardEvent;
        expect(dateArrowStep(event, '2024-08-15', TODAY)).toBeNull();
    });

    it('steps a day at a time while the key is tapped', () => {
        let value = '2024-08-15';
        for (let i = 0; i < 20; i += 1) value = press(value, {repeat: false});
        expect(value).toBe('2024-09-04');
    });

    it('fills an empty field from the fallback date', () => {
        expect(press('', {repeat: false})).toBe('2024-08-16');
        resetDateArrowHold();
        expect(press('', {repeat: false, key: 'ArrowDown'})).toBe('2024-08-14');
    });

    it('climbs day → month → year → decade → century while held', () => {
        // Each rung serves 15 presses, the last of which is already the climb: 15 days
        // (16 Aug … 30 Aug), then the 15th moves a month, and so on.
        let value = press('2024-08-15', {repeat: false});
        for (let i = 0; i < 15; i += 1) value = press(value, {repeat: true});
        expect(value).toBe('2024-09-30');
        for (let i = 0; i < 15; i += 1) value = press(value, {repeat: true});
        expect(value).toBe('2026-11-30');
        for (let i = 0; i < 15; i += 1) value = press(value, {repeat: true});
        expect(value).toBe('2050-11-30');
        for (let i = 0; i < 15; i += 1) value = press(value, {repeat: true});
        expect(value).toBe('2290-11-30');
    });

    it('stops climbing at centuries', () => {
        let value = press('2024-08-15', {repeat: false});
        for (let i = 0; i < 120; i += 1) value = press(value, {repeat: true});
        const last = press(value, {repeat: true});
        expect(Number(last.slice(0, 4)) - Number(value.slice(0, 4))).toBe(100);
    });

    it('keeps the day of the month across a short one', () => {
        // 30 Aug held into February and out again: the 28th is a clamp, not a new home.
        let value = press('2024-08-15', {repeat: false});
        for (let i = 0; i < 15; i += 1) value = press(value, {repeat: true});
        expect(value).toBe('2024-09-30');
        for (let i = 0; i < 5; i += 1) value = press(value, {repeat: true});
        expect(value).toBe('2025-02-28');
        value = press(value, {repeat: true});
        expect(value).toBe('2025-03-30');
    });

    it('drops back to a single day when the direction changes', () => {
        let value = press('2024-08-15', {repeat: false});
        for (let i = 0; i < 40; i += 1) value = press(value, {repeat: true});
        expect(press(value, {repeat: true, key: 'ArrowDown'})).toBe(shiftIsoDate(value, 'day', -1));
    });
});

/**
 * W5-11: Date.UTC reads a year 0..99 as 1900..1999, so stepping a date typed with a short year jumped a century. The
 * calendar is the proleptic Gregorian one, year 1 is the floor (year 0 is not a date): stepping below it stays put.
 */
describe('shiftIsoDate — years below 100 (W5-11)', () => {
    it('moves a day inside year 24, leap February included', () => {
        expect(shiftIsoDate('0024-03-01', 'day', 1)).toBe('0024-03-02');
        expect(shiftIsoDate('0024-03-01', 'day', -1)).toBe('0024-02-29');
    });

    it('crosses from year 99 to year 100', () => {
        expect(shiftIsoDate('0099-12-31', 'day', 1)).toBe('0100-01-01');
        expect(shiftIsoDate('0100-01-01', 'day', -1)).toBe('0099-12-31');
    });

    it('year 100 has no 29 February', () => {
        expect(shiftIsoDate('0100-02-28', 'day', 1)).toBe('0100-03-01');
    });

    it('clamps the day on months and years of a short year', () => {
        expect(shiftIsoDate('0024-02-29', 'year', 1)).toBe('0025-02-28');
        expect(shiftIsoDate('0024-01-31', 'month', 1)).toBe('0024-02-29');
        expect(shiftIsoDate('0099-12-15', 'month', 1)).toBe('0100-01-15');
    });

    it('year 1 is the floor: stepping below it stays on 0001-01-01', () => {
        expect(shiftIsoDate('0001-01-01', 'day', -1)).toBe('0001-01-01');
        expect(shiftIsoDate('0001-01-01', 'month', -1)).toBe('0001-01-01');
        expect(shiftIsoDate('0001-01-01', 'year', -1)).toBe('0001-01-01');
    });

    it('still steps up from the floor', () => {
        expect(shiftIsoDate('0001-01-01', 'day', 1)).toBe('0001-01-02');
        expect(shiftIsoDate('0001-01-01', 'month', 1)).toBe('0001-02-01');
        expect(shiftIsoDate('0001-01-01', 'year', 1)).toBe('0002-01-01');
    });
});

describe('dateArrowStep — years below 100 (W5-11)', () => {
    const target = {} as EventTarget;
    const TODAY = '2024-08-15';
    const press = (iso: string, key: 'ArrowUp' | 'ArrowDown'): string => {
        const event = {key, repeat: false, target, ctrlKey: false, metaKey: false, altKey: false, preventDefault: () => {}} as unknown as KeyboardEvent;
        return dateArrowStep(event, iso, TODAY) as string;
    };

    beforeEach(() => resetDateArrowHold());

    it('a tap moves a day inside year 24, not a century', () => {
        expect(press('0024-03-01', 'ArrowUp')).toBe('0024-03-02');
        resetDateArrowHold();
        expect(press('0024-03-01', 'ArrowDown')).toBe('0024-02-29');
    });

    it('ArrowDown on 0001-01-01 stays there', () => {
        expect(press('0001-01-01', 'ArrowDown')).toBe('0001-01-01');
    });
});
