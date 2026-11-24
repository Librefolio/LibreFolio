import {describe, expect, it} from 'vitest';

import {clampHistoryPeriod, historyAvailable, initialHistoryPeriod} from './simulationHistory';

const AVAILABLE = {start: '2016-05-03', end: '2026-11-24'};
const TODAY = '2026-11-23';

describe('historyAvailable', () => {
    it('reads the window the answer states', () => {
        expect(historyAvailable({history_available_start: AVAILABLE.start, history_available_end: AVAILABLE.end})).toEqual(AVAILABLE);
    });

    it('is null without a whole window', () => {
        expect(historyAvailable(null)).toBeNull();
        expect(historyAvailable({history_available_start: AVAILABLE.start, history_available_end: null})).toBeNull();
        expect(historyAvailable({})).toBeNull();
    });
});

describe('clampHistoryPeriod', () => {
    it('keeps a period inside the window as it is', () => {
        expect(clampHistoryPeriod({start: '2020-02-01', end: '2021-03-31'}, AVAILABLE, TODAY)).toEqual({start: '2020-02-01', end: '2021-03-31'});
    });

    it('never before the common history', () => {
        expect(clampHistoryPeriod({start: '2010-01-01', end: '2018-06-30'}, AVAILABLE, TODAY)).toEqual({start: '2016-05-03', end: '2018-06-30'});
    });

    it('never after today, even when the data ends tomorrow', () => {
        expect(clampHistoryPeriod({start: '2025-01-01', end: '2027-01-01'}, AVAILABLE, TODAY)).toEqual({start: '2025-01-01', end: TODAY});
    });

    it('never after the end of the window when it ends before today', () => {
        expect(clampHistoryPeriod({start: '2025-01-01', end: '2026-12-31'}, {start: AVAILABLE.start, end: '2026-06-30'}, TODAY)).toEqual({start: '2025-01-01', end: '2026-06-30'});
    });

    it('a start after the end becomes the end', () => {
        expect(clampHistoryPeriod({start: '2027-03-01', end: '2027-04-01'}, AVAILABLE, TODAY)).toEqual({start: TODAY, end: TODAY});
    });

    it('before any answer only today bounds it', () => {
        expect(clampHistoryPeriod({start: '1990-01-01', end: '2030-01-01'}, null, TODAY)).toEqual({start: '1990-01-01', end: TODAY});
    });
});

describe('initialHistoryPeriod', () => {
    it('opens on the whole window, up to today', () => {
        expect(initialHistoryPeriod(AVAILABLE, TODAY, '2025-11-23')).toEqual({start: AVAILABLE.start, end: TODAY});
    });

    it('opens on the last year before any answer', () => {
        expect(initialHistoryPeriod(null, TODAY, '2025-11-23')).toEqual({start: '2025-11-23', end: TODAY});
    });
});
