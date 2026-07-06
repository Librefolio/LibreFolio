/**
 * Technical Export Builder — orchestrates signal computation for the AI export.
 *
 * For each eligible asset:
 * 1. Loads price data from assetPriceStoreRegistry
 * 2. Computes EMA20/50/200, RSI14, MACD via existing ChartSignal classes
 * 3. Samples the 3M window (last 7 daily + preceding weekly)
 * 4. Computes normalized return from 3M base price
 * 5. Detects technical events (crosses)
 * 6. Builds AiTechnicalAsset output
 */

import {ensureAssetPriceRangeLoaded} from '$lib/stores/assetPriceStoreRegistry';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {EmaSignal} from '$lib/charts/signals/EmaSignal';
import {RsiSignal} from '$lib/charts/signals/RsiSignal';
import {MacdSignal} from '$lib/charts/signals/MacdSignal';
import {sampleTimeSeries} from './technicalSampling';
import {detectTechnicalEvents} from './technicalEvents';
import type {TimeSeriesPoint} from './signalCrossDetection';
import type {AiTechnicalAsset, AiTechnicalSeriesPoint, AiTechnicalUnavailable} from '../types';

// ─── Configuration ───────────────────────────────────────────────────────────

/** Technical window in months for normalized return base */
const TECHNICAL_WINDOW_MONTHS = 3;

/** Extra months to load for EMA warm-up */
const WARMUP_MONTHS = 13;

// ─── Types ───────────────────────────────────────────────────────────────────

export interface TechnicalExportInput {
    assetId: number;
    assetName: string;
    assetTicker?: string;
    currency: string;
    /** End date for the technical window (YYYY-MM-DD) */
    endDate: string;
    /** Target currency for price conversion */
    targetCurrency: string;
}

export interface TechnicalExportResult {
    assets: AiTechnicalAsset[];
    unavailable: AiTechnicalUnavailable[];
}

// ─── Main Builder ────────────────────────────────────────────────────────────

/**
 * Builds technical context for all eligible assets.
 * Loads price data in parallel, computes signals, samples, and detects events.
 */
export async function buildTechnicalContext(inputs: TechnicalExportInput[]): Promise<TechnicalExportResult> {
    const results = await Promise.allSettled(inputs.map((input) => buildSingleAsset(input)));

    const assets: AiTechnicalAsset[] = [];
    const unavailable: AiTechnicalUnavailable[] = [];

    for (let i = 0; i < results.length; i++) {
        const result = results[i];
        const input = inputs[i];
        if (result.status === 'fulfilled') {
            if (result.value) {
                assets.push(result.value);
            } else {
                unavailable.push({
                    asset: input.assetName,
                    reason: 'No price history available for technical analysis.',
                });
            }
        } else {
            unavailable.push({
                asset: input.assetName,
                reason: `Error loading price data: ${result.reason}`,
            });
        }
    }

    // Limit total events to 30 (most recent across all assets)
    const MAX_TOTAL_EVENTS = 30;
    const allEvents = assets.flatMap((a) => a.events);
    if (allEvents.length > MAX_TOTAL_EVENTS) {
        const eventsByDate = allEvents.sort((a, b) => b.date.localeCompare(a.date));
        const keepDates = new Set(eventsByDate.slice(0, MAX_TOTAL_EVENTS).map((e) => `${e.asset}|${e.date}|${e.event}`));
        for (const asset of assets) {
            asset.events = asset.events.filter((e) => keepDates.has(`${e.asset}|${e.date}|${e.event}`));
        }
    }

    return {assets, unavailable};
}

// ─── Single Asset Builder ────────────────────────────────────────────────────

async function buildSingleAsset(input: TechnicalExportInput): Promise<AiTechnicalAsset | null> {
    const endDate = input.endDate;
    const windowStart = subtractMonths(endDate, TECHNICAL_WINDOW_MONTHS);
    const loadStart = subtractMonths(endDate, WARMUP_MONTHS);

    // Load price data with warm-up period
    const prices = await ensureAssetPriceRangeLoaded(input.assetId, input.currency, loadStart, endDate, {
        targetCurrency: input.targetCurrency,
    });

    if (prices.length < 5) return null;

    // Filter out backward-filled (non-trading day) prices for cleaner signal data
    const tradingPrices = prices.filter((p) => !p.backwardFillInfo || p.backwardFillInfo.daysBack === 0);
    const effectivePrices = tradingPrices.length >= 5 ? tradingPrices : prices;

    // Convert to LineDataPoint
    const priceData: LineDataPoint[] = effectivePrices.map((p) => ({date: p.date, value: p.close}));

    // Compute signals using the full data range (includes warm-up)
    const defaultStyle = {color: '#000', lineWidth: 1, lineType: 'solid' as const, markerStart: null, markerEnd: null};
    const ema20 = new EmaSignal('ema20', defaultStyle, {period: 20}).computePoints(priceData);
    const ema50 = new EmaSignal('ema50', defaultStyle, {period: 50}).computePoints(priceData);
    const ema200 = new EmaSignal('ema200', defaultStyle, {period: 200}).computePoints(priceData);
    const rsi14 = new RsiSignal('rsi14', defaultStyle, {period: 14}).computePoints(priceData);
    const macdSignal = new MacdSignal('macd', defaultStyle, {fastPeriod: 12, slowPeriod: 26, signalPeriod: 9});
    const macdAll = (macdSignal as any)._computeAll(priceData) as {histogram: LineDataPoint[]};
    const macdHistogram: LineDataPoint[] = macdAll.histogram;

    // Build date-indexed maps for quick lookup
    const ema20Map = indexByDate(ema20);
    const ema50Map = indexByDate(ema50);
    const ema200Map = indexByDate(ema200);
    const rsi14Map = indexByDate(rsi14);
    const macdHistMap = indexByDate(macdHistogram);

    // Filter to technical window for sampling
    const windowData = priceData.filter((p) => p.date >= windowStart);
    if (windowData.length === 0) return null;

    // Find base price for normalized return
    const baseInfo = findBasePrice(priceData, windowStart);
    if (!baseInfo) return null;

    // Sample the window: last 7 daily + preceding weekly
    const sampled = sampleTimeSeries(
        windowData.map((p) => ({date: p.date, value: p.value})),
        {windowStart, recentDays: 7},
    );

    // Build series points
    const series: AiTechnicalSeriesPoint[] = sampled.map((p) => ({
        date: p.date,
        close: round2(p.value),
        return_from_base_pct: round2(((p.value - baseInfo.price) / baseInfo.price) * 100),
        rsi14: rsi14Map.get(p.date) != null ? round2(rsi14Map.get(p.date)!) : undefined,
        macd_hist: macdHistMap.get(p.date) != null ? round2(macdHistMap.get(p.date)!) : undefined,
        ema20: ema20Map.get(p.date) != null ? round2(ema20Map.get(p.date)!) : undefined,
        ema50: ema50Map.get(p.date) != null ? round2(ema50Map.get(p.date)!) : undefined,
        ema200: ema200Map.get(p.date) != null ? round2(ema200Map.get(p.date)!) : undefined,
    }));

    // Detect events within the window
    const windowClose: TimeSeriesPoint[] = windowData.map((p) => ({date: p.date, value: p.value}));
    const windowEma20: TimeSeriesPoint[] = filterToWindow(ema20, windowStart);
    const windowEma50: TimeSeriesPoint[] = filterToWindow(ema50, windowStart);
    const windowEma200: TimeSeriesPoint[] = filterToWindow(ema200, windowStart);
    const windowRsi14: TimeSeriesPoint[] = filterToWindow(rsi14, windowStart);
    const windowMacdHist: TimeSeriesPoint[] = filterToWindow(macdHistogram, windowStart);

    const rawEvents = detectTechnicalEvents({
        close: windowClose,
        ema20: windowEma20.length > 0 ? windowEma20 : undefined,
        ema50: windowEma50.length > 0 ? windowEma50 : undefined,
        ema200: windowEma200.length > 0 ? windowEma200 : undefined,
        rsi14: windowRsi14.length > 0 ? windowRsi14 : undefined,
        macdHistogram: windowMacdHist.length > 0 ? windowMacdHist : undefined,
    });

    const events = rawEvents.map((e) => ({
        asset: input.assetTicker ?? input.assetName,
        date: e.date,
        event: e.event,
        details: e.details,
    }));

    // Build metadata
    const windowComplete = priceData.some((p) => p.date <= windowStart);
    const metadata = {
        asset: input.assetName,
        symbol: input.assetTicker,
        technical_window: `${TECHNICAL_WINDOW_MONTHS}M`,
        technical_window_start: windowStart,
        normalized_return_base_date: baseInfo.date,
        normalized_return_base_price: round2(baseInfo.price),
        technical_window_complete: windowComplete && baseInfo.date <= windowStart,
        ...(baseInfo.date > windowStart
            ? {
                  normalized_return_base_reason: 'first_available_price_after_window_start',
                  comparability_note: 'Return series starts later than other assets; compare with caution.',
              }
            : {}),
    };

    return {metadata, series, events};
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function indexByDate(series: LineDataPoint[]): Map<string, number> {
    const map = new Map<string, number>();
    for (const p of series) map.set(p.date, p.value);
    return map;
}

function filterToWindow(series: LineDataPoint[], windowStart: string): TimeSeriesPoint[] {
    return series.filter((p) => p.date >= windowStart).map((p) => ({date: p.date, value: p.value}));
}

function findBasePrice(priceData: LineDataPoint[], windowStart: string): {date: string; price: number} | null {
    // Find the last price on or before windowStart, or the first after
    let lastBefore: LineDataPoint | null = null;
    let firstAfter: LineDataPoint | null = null;

    for (const p of priceData) {
        if (p.date <= windowStart) {
            lastBefore = p;
        } else if (!firstAfter) {
            firstAfter = p;
        }
    }

    if (lastBefore && lastBefore.value > 0) {
        return {date: lastBefore.date, price: lastBefore.value};
    }
    if (firstAfter && firstAfter.value > 0) {
        return {date: firstAfter.date, price: firstAfter.value};
    }
    return null;
}

function subtractMonths(dateStr: string, months: number): string {
    const d = new Date(dateStr + 'T12:00:00Z');
    d.setUTCMonth(d.getUTCMonth() - months);
    return d.toISOString().slice(0, 10);
}

function round2(n: number): number {
    return Math.round(n * 100) / 100;
}
