import {describe, it, expect} from 'vitest';
import {deserializeSchedule, deserializeEvents, serializeSchedule, type ScheduleRow} from './scheduleSerialization';

// A minimal helper to make a normal (non-late) schedule row.
function normalRow(over: Partial<ScheduleRow> = {}): ScheduleRow {
    return {
        id: 'r1',
        start_date: '2024-01-01',
        end_date: '2024-06-30',
        annual_rate: 5,
        maturation_frequency: 'MONTHLY',
        generate_interest: true,
        isLate: false,
        grace_period_days: 0,
        enabled: true,
        lateInterestType: 'COMPOUND',
        ...over,
    };
}

describe('deserializeSchedule', () => {
    it('returns only the late-interest row for empty/absent input, with sane defaults', () => {
        for (const val of [undefined, null, {}, {schedule: []}]) {
            const rows = deserializeSchedule(val as never);
            expect(rows).toHaveLength(1);
            const late = rows[0];
            expect(late.isLate).toBe(true);
            expect(late.id).toBe('late-interest');
            // No preceding period → start_date collapses to ''.
            expect(late.start_date).toBe('');
            // No stored late_interest → default 12% and disabled.
            expect(late.annual_rate).toBe(12);
            expect(late.enabled).toBe(false);
            expect(late.maturation_frequency).toBe('MONTHLY');
            expect(late.generate_interest).toBe(false);
            expect(late.grace_period_days).toBe(0);
            expect(late.lateInterestType).toBe('COMPOUND');
        }
    });

    it('maps stored periods and applies per-period fallbacks when fields are missing', () => {
        const rows = deserializeSchedule({
            schedule: [{start_date: '2024-01-01', end_date: '2024-03-31', annual_rate: 0.05}],
        });
        // one period + the always-present late row
        expect(rows).toHaveLength(2);
        const p = rows[0];
        expect(p.isLate).toBe(false);
        expect(p.start_date).toBe('2024-01-01');
        // annual_rate is stored as a fraction and surfaced as a percentage.
        expect(p.annual_rate).toBeCloseTo(5);
        // Missing optional fields fall back.
        expect(p.maturation_frequency).toBe('MONTHLY');
        expect(p.generate_interest).toBe(false);
        // The late row's start_date is the day after the last period's end.
        expect(rows[1].start_date).toBe('2024-04-01');
    });

    it('honours per-period values when present (truthy side of the fallbacks)', () => {
        const rows = deserializeSchedule({
            schedule: [
                {
                    start_date: '2024-01-01',
                    end_date: '2024-03-31',
                    annual_rate: 0.1,
                    maturation_frequency: 'QUARTERLY',
                    generate_interest: true,
                },
            ],
        });
        const p = rows[0];
        expect(p.maturation_frequency).toBe('QUARTERLY');
        expect(p.generate_interest).toBe(true);
        expect(p.annual_rate).toBeCloseTo(10);
    });

    it('reads a stored late_interest block (truthy side of every late fallback)', () => {
        const rows = deserializeSchedule({
            schedule: [{start_date: '2024-01-01', end_date: '2024-03-31', annual_rate: 0.05}],
            late_interest: {
                annual_rate: 0.2,
                grace_period_days: 15,
                interest_type: 'SIMPLE',
                maturation_frequency: 'ANNUAL',
                generate_interest: true,
            },
        });
        const late = rows[rows.length - 1];
        expect(late.enabled).toBe(true);
        expect(late.annual_rate).toBeCloseTo(20);
        expect(late.grace_period_days).toBe(15);
        expect(late.lateInterestType).toBe('SIMPLE');
        expect(late.maturation_frequency).toBe('ANNUAL');
        expect(late.generate_interest).toBe(true);
    });

    it('applies late-row fallbacks when late_interest exists but omits sub-fields', () => {
        const rows = deserializeSchedule({late_interest: {annual_rate: 0.03}});
        const late = rows[rows.length - 1];
        expect(late.enabled).toBe(true); // present → enabled
        expect(late.annual_rate).toBeCloseTo(3); // truthy → not the 12 default
        expect(late.grace_period_days).toBe(0);
        expect(late.maturation_frequency).toBe('MONTHLY');
        expect(late.generate_interest).toBe(false);
        expect(late.lateInterestType).toBe('COMPOUND');
    });
});

describe('deserializeEvents', () => {
    const TODAY = '2024-09-01';

    it('returns [] for an empty list', () => {
        expect(deserializeEvents([], TODAY)).toEqual([]);
    });

    it('reads the structured {value:{amount,code}} shape', () => {
        const [ev] = deserializeEvents([{date: '2024-02-01', type: 'PRICE_ADJUSTMENT', value: {amount: '12.5', code: 'USD'}, notes: 'x'}], TODAY);
        expect(ev.date).toBe('2024-02-01');
        expect(ev.type).toBe('PRICE_ADJUSTMENT');
        expect(ev.value).toBe(12.5);
        expect(ev.currency).toBe('USD');
        expect(ev.notes).toBe('x');
    });

    it('reads the flat {value:number, currency} shape', () => {
        const [ev] = deserializeEvents([{date: '2024-02-01', value: 7, currency: 'EUR'}], TODAY);
        expect(ev.value).toBe(7);
        expect(ev.currency).toBe('EUR');
        // type/notes fall back
        expect(ev.type).toBe('INTEREST');
        expect(ev.notes).toBe('');
    });

    it('falls back on every field for a bare event object', () => {
        const [ev] = deserializeEvents([{}], TODAY);
        expect(ev.date).toBe(TODAY);
        expect(ev.type).toBe('INTEREST');
        expect(ev.value).toBe(0);
        expect(ev.currency).toBe('');
        expect(ev.notes).toBe('');
    });

    it('treats an explicit zero amount as 0, not as a fallback', () => {
        const [ev] = deserializeEvents([{value: {amount: 0, code: 'USD'}}], TODAY);
        expect(ev.value).toBe(0);
        expect(ev.currency).toBe('USD');
    });
});

describe('serializeSchedule', () => {
    it('serializes normal periods and an enabled late row', () => {
        const out = serializeSchedule([
            normalRow({annual_rate: 5}),
            {
                id: 'late-interest',
                start_date: '2024-07-01',
                end_date: '',
                annual_rate: 20,
                maturation_frequency: 'MONTHLY',
                generate_interest: false,
                isLate: true,
                grace_period_days: 10,
                enabled: true,
                lateInterestType: 'SIMPLE',
            },
        ]);
        expect(out.schedule).toHaveLength(1);
        expect(out.schedule[0].annual_rate).toBe('0.0500'); // percent → fraction, 4dp
        expect(out.late_interest).not.toBeNull();
        expect(out.late_interest?.annual_rate).toBe('0.2000');
        expect(out.late_interest?.grace_period_days).toBe(10);
        expect(out.late_interest?.interest_type).toBe('SIMPLE');
    });

    it('emits late_interest = null when the late row is disabled', () => {
        const out = serializeSchedule([normalRow(), {...normalRow(), id: 'late-interest', isLate: true, enabled: false}]);
        expect(out.schedule).toHaveLength(1);
        expect(out.late_interest).toBeNull();
    });

    it('emits late_interest = null when there is no late row at all', () => {
        const out = serializeSchedule([normalRow()]);
        expect(out.late_interest).toBeNull();
    });
});
