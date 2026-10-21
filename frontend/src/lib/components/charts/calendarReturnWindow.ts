import {daysBetween} from '$lib/utils/dateOnly';

export const CALENDAR_RETURN_PRESETS = [
    {key: '1w', count: 1, unit: 'weeks', windowDays: 7},
    {key: '1m', count: 1, unit: 'months', windowDays: 30},
    {key: '3m', count: 3, unit: 'months', windowDays: 90},
    {key: '1y', count: 1, unit: 'years', windowDays: 365},
] as const;

export type CalendarReturnPresetKey = (typeof CALENDAR_RETURN_PRESETS)[number]['key'];
export type CalendarReturnWindowUnit = 'weeks' | 'months' | 'years';

/** Catalog keys of a preset's label, `{n}` + the reader's unit letter: the date picker's presets use the same ones. */
export const CALENDAR_RETURN_UNIT_LABEL_KEYS: Record<CalendarReturnWindowUnit, string> = {
    weeks: 'datePicker.presets.weeks',
    months: 'datePicker.presets.months',
    years: 'datePicker.presets.years',
};

export interface CalendarReturnWindowSelection {
    kind: 'preset' | 'custom';
    preset: CalendarReturnPresetKey;
    customAmount: number;
    customUnit: CalendarReturnWindowUnit;
}

export const DEFAULT_CALENDAR_RETURN_WINDOW: CalendarReturnWindowSelection = {
    kind: 'preset',
    preset: '1m',
    customAmount: 3,
    customUnit: 'years',
};

const UNIT_MULTIPLIERS: Record<CalendarReturnWindowUnit, number> = {
    weeks: 7,
    months: 30,
    years: 365,
};

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isPositiveSafeInteger(value: unknown): value is number {
    return typeof value === 'number' && Number.isSafeInteger(value) && value > 0;
}

export function calendarReturnWindowDays(selection: CalendarReturnWindowSelection): number | null {
    if (selection.kind === 'preset') {
        return CALENDAR_RETURN_PRESETS.find((preset) => preset.key === selection.preset)?.windowDays ?? null;
    }
    const multiplier = UNIT_MULTIPLIERS[selection.customUnit];
    const windowDays = selection.customAmount * multiplier;
    return isPositiveSafeInteger(windowDays) ? windowDays : null;
}

/** The largest preset whose window fits `rangeDays` on screen; the smallest when none does. */
export function largestCalendarReturnPresetFor(rangeDays: number): CalendarReturnPresetKey {
    let chosen: CalendarReturnPresetKey = CALENDAR_RETURN_PRESETS[0].key;
    for (const preset of CALENDAR_RETURN_PRESETS) {
        if (preset.windowDays <= rangeDays) chosen = preset.key;
    }
    return chosen;
}

export function calendarReturnRangeDays(start: string, end: string): number {
    return Math.max(0, daysBetween(start, end));
}

export function sanitizeCalendarReturnWindow(value: unknown): CalendarReturnWindowSelection {
    if (!isRecord(value)) return {...DEFAULT_CALENDAR_RETURN_WINDOW};

    const preset = CALENDAR_RETURN_PRESETS.some((candidate) => candidate.key === value.preset) ? (value.preset as CalendarReturnPresetKey) : DEFAULT_CALENDAR_RETURN_WINDOW.preset;
    const customUnit = value.customUnit === 'weeks' || value.customUnit === 'months' || value.customUnit === 'years' ? value.customUnit : DEFAULT_CALENDAR_RETURN_WINDOW.customUnit;
    const customAmount = isPositiveSafeInteger(value.customAmount) ? value.customAmount : DEFAULT_CALENDAR_RETURN_WINDOW.customAmount;
    const kind = value.kind === 'custom' ? 'custom' : 'preset';
    const selection: CalendarReturnWindowSelection = {
        kind,
        preset,
        customAmount,
        customUnit,
    };

    return calendarReturnWindowDays(selection) === null ? {...DEFAULT_CALENDAR_RETURN_WINDOW} : selection;
}
