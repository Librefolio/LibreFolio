/**
 * Pure serialization boundary for {@link ScheduledInvestmentEditor}.
 *
 * These functions translate between the persisted `provider_params` shape (the
 * schedule / late-interest / asset-event JSON) and the editor's row model. They
 * are the "function of input, produces output" core of the editor — the many
 * `?? default` fallbacks here are exactly the branches that are worth covering
 * exhaustively, away from the component's rendering and event wiring.
 */
import {generateUUID} from '$lib/utils/core/uuid';
import {addDays} from '$lib/utils/dateOnly';

export interface ScheduleRow {
    id: string;
    start_date: string;
    end_date: string;
    annual_rate: number;
    maturation_frequency: string;
    generate_interest: boolean;
    isLate: boolean;
    grace_period_days: number;
    enabled: boolean;
    /** Interest type for late interest row only (SIMPLE/COMPOUND) */
    lateInterestType: string;
}

export interface AssetEventRow {
    id: string;
    date: string;
    type: 'INTEREST' | 'PRICE_ADJUSTMENT' | 'MATURITY_SETTLEMENT';
    value: number;
    currency: string;
    notes: string;
}

export interface SerializedSchedulePeriod {
    start_date: string;
    end_date: string;
    annual_rate: string;
    maturation_frequency: string;
    generate_interest: boolean;
}

export interface SerializedLateInterest {
    annual_rate: string;
    grace_period_days: number;
    interest_type: string;
    maturation_frequency: string;
    generate_interest: boolean;
}

/**
 * Convert a persisted params object into schedule rows, always appending the
 * (possibly disabled) late-interest row the editor expects to exist.
 */
export function deserializeSchedule(val: Record<string, any> | null | undefined): ScheduleRow[] {
    const result: ScheduleRow[] = [];
    const schedule = val?.schedule ?? [];

    for (const p of schedule) {
        result.push({
            id: generateUUID(),
            start_date: p.start_date,
            end_date: p.end_date,
            annual_rate: Number(p.annual_rate) * 100,
            maturation_frequency: p.maturation_frequency ?? 'MONTHLY',
            generate_interest: p.generate_interest ?? false,
            isLate: false,
            grace_period_days: 0,
            enabled: true,
            lateInterestType: 'COMPOUND',
        });
    }

    // Late interest — always present as the trailing row.
    const li = val?.late_interest;
    result.push({
        id: 'late-interest',
        start_date: result.length > 0 ? addDays(result[result.length - 1].end_date, 1) : '',
        end_date: '',
        annual_rate: li ? Number(li.annual_rate) * 100 : 12,
        maturation_frequency: li?.maturation_frequency ?? 'MONTHLY',
        generate_interest: li?.generate_interest ?? false,
        isLate: true,
        grace_period_days: li?.grace_period_days ?? 0,
        enabled: !!li,
        lateInterestType: li?.interest_type ?? 'COMPOUND',
    });

    return result;
}

/** Convert persisted asset-event points into editable event rows. */
export function deserializeEvents(events: any[], todayISO: string): AssetEventRow[] {
    return events.map((e: any) => ({
        id: generateUUID(),
        date: e.date ?? todayISO,
        type: e.type ?? 'INTEREST',
        value: Number(e.value?.amount ?? e.value ?? 0),
        currency: e.value?.code ?? e.currency ?? '',
        notes: e.notes ?? '',
    }));
}

/**
 * Serialize the schedule + late-interest halves of the payload from the row
 * model. The component wraps this with the state-dependent fields
 * (initial_value, currency, asset_events, …).
 */
export function serializeSchedule(allRows: ScheduleRow[]): {
    schedule: SerializedSchedulePeriod[];
    late_interest: SerializedLateInterest | null;
} {
    const schedule = allRows
        .filter((r) => !r.isLate)
        .map((r) => ({
            start_date: r.start_date,
            end_date: r.end_date,
            annual_rate: (r.annual_rate / 100).toFixed(4),
            maturation_frequency: r.maturation_frequency,
            generate_interest: r.generate_interest,
        }));

    const lr = allRows.find((r) => r.isLate && r.enabled);
    const late_interest = lr
        ? {
              annual_rate: (lr.annual_rate / 100).toFixed(4),
              grace_period_days: lr.grace_period_days,
              interest_type: lr.lateInterestType,
              maturation_frequency: lr.maturation_frequency,
              generate_interest: lr.generate_interest,
          }
        : null;

    return {schedule, late_interest};
}
