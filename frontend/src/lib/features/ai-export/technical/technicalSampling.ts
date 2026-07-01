/**
 * Technical series sampling — reduces a daily series to a compact representation
 * suitable for AI prompt export.
 *
 * Strategy: keep the last N daily points as-is, then sample preceding points
 * weekly (last trading day of each ISO week) within the technical window.
 */

export interface SampledPoint {
	date: string;
	value: number;
}

export interface SamplingOptions {
	/** Number of most recent daily points to keep verbatim (default: 7) */
	recentDays?: number;
	/** Start of the sampling window (ISO date string) */
	windowStart: string;
}

/**
 * Samples a time series: last `recentDays` daily + preceding weekly.
 *
 * Expects `series` sorted ascending by date, with no null values.
 * Returns sampled points in ascending date order.
 */
export function sampleTimeSeries(series: SampledPoint[], options: SamplingOptions): SampledPoint[] {
	const recentDays = options.recentDays ?? 7;
	const windowStart = options.windowStart;

	// Filter to window
	const inWindow = series.filter((p) => p.date >= windowStart);
	if (inWindow.length === 0) return [];

	if (inWindow.length <= recentDays) return inWindow;

	// Split: recent daily tail + preceding for weekly sampling
	const recentStart = inWindow.length - recentDays;
	const recent = inWindow.slice(recentStart);
	const preceding = inWindow.slice(0, recentStart);

	// Weekly sampling: keep last point of each ISO week
	const weeklyMap = new Map<string, SampledPoint>();
	for (const p of preceding) {
		const weekKey = isoWeekKey(p.date);
		weeklyMap.set(weekKey, p); // last point wins
	}

	const weeklySampled = Array.from(weeklyMap.values()).sort((a, b) => a.date.localeCompare(b.date));

	return [...weeklySampled, ...recent];
}

/** Returns an ISO week key like "2026-W27" for grouping. */
function isoWeekKey(dateStr: string): string {
	const d = new Date(dateStr + 'T12:00:00Z');
	const dayOfWeek = d.getUTCDay() || 7; // Mon=1 .. Sun=7
	// ISO week: Thursday determines the week number
	d.setUTCDate(d.getUTCDate() + 4 - dayOfWeek);
	const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
	const weekNo = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
	return `${d.getUTCFullYear()}-W${String(weekNo).padStart(2, '0')}`;
}
