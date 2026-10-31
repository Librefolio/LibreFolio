/**
 * `snapToDay` — the pointer of a step chart sits on a day, never between two (Y2 FB-2).
 *
 * The time axis hands the pointer back as milliseconds, anywhere between two midnights. The day it stands on is the NEAREST calendar day
 * (noon is the turning point), and the millisecond to draw the pointer line at is that day's local midnight.
 */
import {describe, expect, it} from 'vitest';
import {dayOfAxisValue, snapToDay} from '../stepSeries';

const at = (year: number, month: number, day: number, hours = 0, minutes = 0) => new Date(year, month - 1, day, hours, minutes).getTime();

describe('snapToDay', () => {
    it('leaves a pointer already on a midnight where it is', () => {
        expect(snapToDay(at(2026, 10, 12))).toEqual({day: '2026-10-12', ms: at(2026, 10, 12)});
    });

    it('takes the earlier day before noon and the later one from noon on', () => {
        expect(snapToDay(at(2026, 10, 12, 11, 59)).day).toBe('2026-10-12');
        expect(snapToDay(at(2026, 10, 12, 12, 1)).day).toBe('2026-10-13');
    });

    it('rolls over month and year ends', () => {
        expect(snapToDay(at(2026, 12, 31, 18)).day).toBe('2027-01-01');
        expect(snapToDay(at(2026, 12, 31, 18)).ms).toBe(at(2027, 1, 1));
    });

    it('gives the day dayOfAxisValue gives for its own millisecond', () => {
        const snapped = snapToDay(at(2026, 3, 29, 20));
        expect(dayOfAxisValue(snapped.ms)).toBe(snapped.day);
    });
});
