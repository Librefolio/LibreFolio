/**
 * The period the simulation draws its days from (RSK-SIM1, P-7, the developer, 23/11/2026).
 *
 * By default the simulation draws from all the history its holdings have in common, as it always has. In turbulent
 * times that mixes the crashes with the rebounds, so the reader may choose a period inside that history instead. The
 * backend owns the rule — it moves a start before the common history to it, and says so — and it states the window
 * the reader may choose in (`history_available_start` / `_end`). This module only keeps the picker inside it: never
 * before the common history, never after today, the start never after the end. ISO days compare as strings.
 */

export interface HistoryWindow {
    start: string;
    end: string;
}

/** The window a period may be chosen in, from the last answer that stated it; null before any. */
export function historyAvailable(output: {history_available_start?: string | null; history_available_end?: string | null} | null | undefined): HistoryWindow | null {
    const start = output?.history_available_start;
    const end = output?.history_available_end;
    return typeof start === 'string' && typeof end === 'string' ? {start, end} : null;
}

/** A period the picker may hold: inside the available window when it is known, never after today, start ≤ end. */
export function clampHistoryPeriod(period: HistoryWindow, available: HistoryWindow | null, today: string): HistoryWindow {
    const ceiling = available && available.end < today ? available.end : today;
    let start = available && period.start < available.start ? available.start : period.start;
    const end = period.end > ceiling ? ceiling : period.end;
    if (start > end) start = end;
    return {start, end};
}

/** The period the picker opens on: the whole available window, or, before any answer stated it, the last year. */
export function initialHistoryPeriod(available: HistoryWindow | null, today: string, yearBefore: string): HistoryWindow {
    return clampHistoryPeriod(available ?? {start: yearBefore, end: today}, available, today);
}
