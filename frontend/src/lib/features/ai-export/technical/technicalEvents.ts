/**
 * Technical events — maps generic cross detections to semantic event names.
 *
 * Runs detectCrosses for standard indicator pairs and produces human-readable
 * event labels for the AI export.
 */

import {detectCrosses, type TimeSeriesPoint} from './signalCrossDetection';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface TechnicalEvent {
	date: string;
	event: string;
	details: Record<string, number | string>;
}

interface SignalSeries {
	close: TimeSeriesPoint[];
	ema20?: TimeSeriesPoint[];
	ema50?: TimeSeriesPoint[];
	ema200?: TimeSeriesPoint[];
	rsi14?: TimeSeriesPoint[];
	macdHistogram?: TimeSeriesPoint[];
}

// ─── Event Detection ─────────────────────────────────────────────────────────

/**
 * Detects all standard technical events for an asset.
 *
 * Events detected:
 * - PRICE_CROSSED_ABOVE/BELOW_EMA20/50/200
 * - EMA20_CROSSED_ABOVE/BELOW_EMA50
 * - MACD_HISTOGRAM_TURNED_POSITIVE/NEGATIVE
 * - RSI_ENTERED_OVERBOUGHT (crossed above 70)
 * - RSI_LEFT_OVERBOUGHT (crossed below 70)
 * - RSI_ENTERED_OVERSOLD (crossed below 30)
 * - RSI_LEFT_OVERSOLD (crossed above 30)
 */
export function detectTechnicalEvents(signals: SignalSeries): TechnicalEvent[] {
	const events: TechnicalEvent[] = [];

	const crossPairs: Array<{
		a: TimeSeriesPoint[] | undefined;
		b: TimeSeriesPoint[] | number | undefined;
		labelA: string;
		labelB: string;
		aboveEvent: string;
		belowEvent: string;
	}> = [
		{
			a: signals.close,
			b: signals.ema20,
			labelA: 'close',
			labelB: 'EMA20',
			aboveEvent: 'PRICE_CROSSED_ABOVE_EMA20',
			belowEvent: 'PRICE_CROSSED_BELOW_EMA20',
		},
		{
			a: signals.close,
			b: signals.ema50,
			labelA: 'close',
			labelB: 'EMA50',
			aboveEvent: 'PRICE_CROSSED_ABOVE_EMA50',
			belowEvent: 'PRICE_CROSSED_BELOW_EMA50',
		},
		{
			a: signals.close,
			b: signals.ema200,
			labelA: 'close',
			labelB: 'EMA200',
			aboveEvent: 'PRICE_CROSSED_ABOVE_EMA200',
			belowEvent: 'PRICE_CROSSED_BELOW_EMA200',
		},
		{
			a: signals.ema20,
			b: signals.ema50,
			labelA: 'EMA20',
			labelB: 'EMA50',
			aboveEvent: 'EMA20_CROSSED_ABOVE_EMA50',
			belowEvent: 'EMA20_CROSSED_BELOW_EMA50',
		},
		{
			a: signals.macdHistogram,
			b: 0,
			labelA: 'MACD_histogram',
			labelB: '0',
			aboveEvent: 'MACD_HISTOGRAM_TURNED_POSITIVE',
			belowEvent: 'MACD_HISTOGRAM_TURNED_NEGATIVE',
		},
	];

	for (const pair of crossPairs) {
		if (!pair.a || pair.b === undefined) continue;
		const crosses = detectCrosses(pair.a, pair.b, {
			labelA: pair.labelA,
			labelB: pair.labelB,
		});
		for (const c of crosses) {
			events.push({
				date: c.date,
				event: c.event === 'CROSSED_ABOVE' ? pair.aboveEvent : pair.belowEvent,
				details: {
					[pair.labelA]: c.currentA,
					[pair.labelB]: typeof pair.b === 'number' ? pair.b : c.currentB,
				},
			});
		}
	}

	// RSI zone transitions
	if (signals.rsi14) {
		const rsiAbove70 = detectCrosses(signals.rsi14, 70, {labelA: 'RSI14', labelB: '70'});
		for (const c of rsiAbove70) {
			events.push({
				date: c.date,
				event: c.event === 'CROSSED_ABOVE' ? 'RSI_ENTERED_OVERBOUGHT' : 'RSI_LEFT_OVERBOUGHT',
				details: {RSI14: c.currentA},
			});
		}

		const rsiBelow30 = detectCrosses(signals.rsi14, 30, {labelA: 'RSI14', labelB: '30'});
		for (const c of rsiBelow30) {
			events.push({
				date: c.date,
				event: c.event === 'CROSSED_BELOW' ? 'RSI_ENTERED_OVERSOLD' : 'RSI_LEFT_OVERSOLD',
				details: {RSI14: c.currentA},
			});
		}
	}

	// Sort by date ascending
	events.sort((a, b) => a.date.localeCompare(b.date));

	return events;
}
