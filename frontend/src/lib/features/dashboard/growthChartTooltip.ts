/**
 * GrowthChart's tooltip — the HTML ECharts shows on hover (FE6a, release 1.3).
 *
 * The formatter the component hands to ECharts builds a `GrowthTooltipView` on every hover and calls
 * `buildGrowthTooltip`. What the tooltip reads — the entry on screen, the view, the labels, the translator, the
 * currency — is read at that moment, as when the formatter's body lived in the component; the theme is the one the
 * option was built with.
 */
import {utcMs} from '$lib/utils/dateOnly';
import {indexHoldingDay} from '$lib/utils/stepSeries';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {formatDay} from '$lib/utils/core/formatAxisDate';
import {formatPercent} from '$lib/utils/core/formatPercent';
import {maskFormattedNumber} from '$lib/utils/privacy/maskable';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {themed} from '$lib/theme/themePair';
import {CHART_GAIN_LOSS, GROWTH_SERIES} from '$lib/theme/chartTheme';
import {buildTooltipDivider, buildTooltipHeader, buildTooltipRow, type TooltipTheme} from '$lib/components/charts/echartsTooltipHelpers';
import {bucketSpanUpTo} from '$lib/components/charts/priceChartHelpers';
import type {AggregatedResolutionData, BucketInfo, PctSeriesKey} from './growthChartData';
import {brokerColor, type EurLabels, type GrowthMode, type PnlLabels, type PnlSubmode} from './growthChartSeries';

/** The translator: `$_` of svelte-i18n. */
export type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

/** What the tooltip reads, built by the component on every hover. */
export interface GrowthTooltipView {
    /** The aggregation on screen: the hovered index is one of its buckets. */
    entry: AggregatedResolutionData | null;
    viewMode: GrowthMode;
    pnlSubmode: PnlSubmode;
    /** True while the ladder draws the chart (P&L candles and Income). */
    ladderActive: boolean;
    /** The caption of the rung on screen (`1M`), read only by a ladder bucket's header. */
    candleWidthCaption: () => string;
    eurLabels: EurLabels;
    pnlLabels: PnlLabels;
    baseCurrency: string;
    t: Translate;
    /** The theme the option was built with. */
    isDark: boolean;
    theme: TooltipTheme;
    /**
     * The day the pointer is on, while the entry is the steps themselves (the daily resolution, not the ladder). ECharts hands
     * a time axis the drawn point NEAREST to the pointer, so in the right half of a step it would list the next step's
     * values: the tooltip finds the step holding this day instead. Absent: the hovered index is read as it always was.
     */
    pointedDay?: string | null;
    /** The % series in drawing order, so a stepped tooltip lists them from the entry, not from what ECharts hands over. */
    pctRows?: ReadonlyArray<{key: PctSeriesKey; name: string; colorKey: keyof typeof COLORS}>;
    /** The true MWRR point nearest to a day, with its own date (`nearestPoint` over the report's `mwrr_line`). */
    mwrrAt?: (day: string) => {date: string; value: number} | null;
}

// Color palettes
const COLORS = GROWTH_SERIES;

export function formatTooltipMonth(date: string): string {
    const activeLocale = uiLocale();
    const [year, month, day] = date.split('-').map(Number);
    return new Intl.DateTimeFormat(activeLocale, {
        month: 'long',
        year: 'numeric',
        timeZone: 'UTC',
    }).format(new Date(utcMs(year, month - 1, day)));
}

/**
 * The line under a ladder bucket's header that says how much of its period it holds:
 * "Partial: 26 of 31 days" on a period that is over and that the series covers in part,
 * "In progress: 6 of 31 days" on the one that has not ended yet; empty on a whole period.
 * The translation is data inside tooltip HTML, so it is escaped and reads as written. Two
 * literal calls, never a key chosen at runtime: the project's i18n sweep only sees literals.
 */
export function buildPartialBucketLine(bucket: BucketInfo, theme: TooltipTheme, t: Translate): string {
    let text: string;
    if (bucket.partial) text = t('chart.tooltip.partialBucket', {values: {days: bucket.partial.days, total: bucket.partial.total}});
    else if (bucket.current) text = t('chart.tooltip.currentBucket', {values: {days: bucket.current.days, total: bucket.current.total}});
    else return '';
    return `<div style="font-size:10px;color:${theme.mutedColor};margin-bottom:4px">${escapeHtml(text)}</div>`;
}

/** Every day of the header is written in the interface language, never as raw ISO (plan 52, C2). */
export function buildTooltipBucketHeader(bucket: BucketInfo, theme: TooltipTheme, view: Pick<GrowthTooltipView, 'ladderActive' | 'pnlSubmode' | 'candleWidthCaption' | 't'>): string {
    const {ladderActive, pnlSubmode, t} = view;
    const partialHtml = buildPartialBucketLine(bucket, theme, t);
    // A one-day bucket has nothing to span, so it keeps the plain date. A ladder bucket is
    // judged by its period: a week the series covers for one day still prints its week.
    const span = bucket.period ?? {start: bucket.bucketStart, end: bucket.bucketEnd};
    if (span.start === span.end) {
        return `${buildTooltipHeader(formatDay(bucket.bucketEnd), theme.textColor)}${partialHtml}`;
    }

    if (ladderActive) {
        // "1M - Oct 1, 2026 → Oct 31, 2026": the calendar period the bucket stands for. The
        // old form said "Week" for every bucket wider than a day, which was simply false
        // on a three-day or fourteen-day rung.
        const headerHtml = `${buildTooltipHeader(`${view.candleWidthCaption()} - ${formatDay(span.start)} → ${formatDay(span.end)}`, theme.textColor)}${partialHtml}`;
        // "Value at <date>" is true of a closing level and false of a sum, so the
        // Income submode — whose bars are sums over the bucket — does not claim it. The
        // date is the last day with data, never a day of the period still to come.
        if (pnlSubmode === 'income') return headerHtml;
        return `${headerHtml}<div style="font-size:10px;color:${theme.mutedColor};margin-bottom:4px">${t('chart.tooltip.valueAt', {values: {date: formatDay(bucket.bucketEnd)}})}</div>`;
    }

    // The point stands for its bucket up to its own day, the last one with data: the
    // period still running ends there.
    const upTo = bucketSpanUpTo(bucket.date, bucket);
    const contextLine = `<div style="font-size:10px;color:${theme.mutedColor};margin-bottom:4px">${t('chart.tooltip.valueAt', {values: {date: formatDay(upTo.bucketEnd)}})}</div>`;

    if (bucket.resolution === 'weekly') {
        return `${buildTooltipHeader(t('chart.tooltip.weekRange', {values: {start: formatDay(upTo.bucketStart), end: formatDay(upTo.bucketEnd)}}), theme.textColor)}${contextLine}`;
    }

    return `${buildTooltipHeader(t('chart.tooltip.monthLabel', {values: {month: formatTooltipMonth(upTo.bucketEnd)}}), theme.textColor)}${contextLine}`;
}

/**
 * Colour for a signed amount: green up, red down, **neutral at zero**.
 *
 * `v >= 0` painted every zero green, which reads as a gain that did not happen —
 * and in the Income submode most buckets are legitimately zero, so the tooltip was
 * mostly green for weeks in which nothing was earned.
 *
 * Zero is what the row prints as zero, as for the sign (D23b): `fmtCurrency` keeps two
 * decimals, so under half a cent it prints `0.00` with no sign. A bucket sum can land
 * there without being 0 (0.1 + 0.2 − 0.3 is 5.55e-17), and tested on the raw value it
 * would print `EUR 0.00` in green.
 */
export function signedValueColor(v: number, dark: boolean, neutral: string): string {
    return Math.abs(v) < 0.005 ? neutral : v > 0 ? themed(CHART_GAIN_LOSS.portfolio.gain, dark) : themed(CHART_GAIN_LOSS.portfolio.loss, dark);
}

/** The tooltip of the hovered point: its bucket's header, then the rows of the view on screen. */
export function buildGrowthTooltip(params: any, view: GrowthTooltipView): string {
    const {viewMode, pnlSubmode, eurLabels, pnlLabels, isDark, t} = view;
    const activeChartData = view.entry;
    const {bg: tooltipBg, border: tooltipBorder, textColor, mutedColor} = view.theme;

    /**
     * Format a number as currency: `EUR 1,234.56`, and with `signed` `EUR +5.00` or
     * `EUR -12.00`, the one form of every signed tooltip row (D23b).
     *
     * The sign comes from the same `toLocaleString` call as the digits, in the interface locale
     * (`uiLocale()`, D23): `-` in the four UI languages and their regions. `signed`
     * adds `+` to a gain and no sign to an amount that rounds to zero. As in
     * `formatCurrencyAmountPlain`, only the digits are masked; the currency and the sign stay
     * readable (D8).
     */
    const fmtCurrency = (v: number | null | undefined, signed = false) => {
        if (v == null) return '—';
        // `-0 === 0`, so a negative zero becomes +0: `signDisplay: 'auto'` would print it `-0.00`.
        const formatted = (v === 0 ? 0 : v).toLocaleString(uiLocale(), {minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: signed ? 'exceptZero' : 'auto'});
        return `${view.baseCurrency} ${maskFormattedNumber(formatted)}`;
    };

    const items = Array.isArray(params) ? params : [params];
    // The steps themselves: the step holding the pointed day, written under the day itself.
    const pointedDay = activeChartData && !view.ladderActive && activeChartData.resolution === 'daily' ? (view.pointedDay ?? null) : null;
    const idx = pointedDay !== null && activeChartData ? indexHoldingDay(activeChartData.buckets, pointedDay) : (items[0]?.dataIndex ?? 0);
    const bucket = activeChartData?.buckets[idx];
    if (!bucket) return '';
    const shownBucket = pointedDay !== null ? {...bucket, date: pointedDay, bucketStart: pointedDay, bucketEnd: pointedDay} : bucket;
    let html = buildTooltipBucketHeader(shownBucket, {bg: tooltipBg, border: tooltipBorder, textColor, mutedColor}, view);

    if (viewMode === 'eur') {
        const assetCostVal = activeChartData?.eur.bookAssetLike.values[idx];
        const cashGenVal = activeChartData?.eur.cashGenerated.values[idx];
        const cashContribVal = activeChartData?.eur.cashContributed.values[idx];
        const navVal = activeChartData?.eur.nav.values[idx];
        const baselineVal = activeChartData?.eur.capitalBaseline.values[idx];
        const totalPnlVal = activeChartData?.eur.totalPnl.values[idx];

        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
        const fmtOrDash = (v: number | null | undefined) => (v != null && v !== 0 ? fmtCurrency(v) : '—');

        html += buildTooltipRow(`<b>${eurLabels.nav}</b>`, fmtCurrency(navVal), cc('nav'));
        html += buildTooltipRow(eurLabels.capitalBaselineTooltip, fmtCurrency(baselineVal), cc('capitalBaseline'));
        if (totalPnlVal != null) {
            const pnlColor = signedValueColor(totalPnlVal, isDark, textColor);
            html += `<div style="display:flex;justify-content:space-between;gap:16px;color:${pnlColor}"><span><b>${t('dashboard.totalPnl')}</b></span><b>${fmtCurrency(totalPnlVal, true)}</b></div>`;
        }
        html += `<div style="font-size:10px;color:${textColor};opacity:0.7">${t('dashboard.pnlFormulaHint')}</div>`;
        html += buildTooltipDivider(tooltipBorder);
        html += buildTooltipRow(eurLabels.bookAssetLikeTooltip, fmtOrDash(assetCostVal), cc('bookAssetLike'));
        html += buildTooltipRow(eurLabels.cashGenerated, fmtOrDash(cashGenVal), cc('cashGenerated'));
        html += buildTooltipRow(eurLabels.cashContributed, fmtOrDash(cashContribVal), cc('cashContributed'));
        return html;
    }

    if (viewMode === 'pnl' && pnlSubmode === 'line') {
        const totalVal = activeChartData?.pnl.total.values[idx];
        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
        const pnlRow = (label: string, v: number | null | undefined, color: string) => {
            if (v == null) return buildTooltipRow(label, '—', color);
            const signColor = signedValueColor(v, isDark, textColor);
            return `<div style="display:flex;justify-content:space-between;gap:16px;color:${color}"><span>${label}</span><b style="color:${signColor}">${fmtCurrency(v, true)}</b></div>`;
        };
        html += pnlRow(`<b>${pnlLabels.total}</b>`, totalVal, cc('totalPnl'));
        activeChartData?.pnl.brokers.forEach((broker, index) => {
            html += pnlRow(escapeHtml(broker.brokerName), broker.metric.values[idx], brokerColor(index, isDark));
        });
        return html;
    }

    if (viewMode === 'pnl' && pnlSubmode === 'candles') {
        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
        const candle = activeChartData?.pnl.candle.points[idx];
        const ohlcRow = (label: string, v: number | null | undefined) => `<div style="display:flex;justify-content:space-between;gap:16px;color:${textColor}"><span>${label}</span><b>${v != null ? fmtCurrency(v) : '—'}</b></div>`;
        if (candle && candle.close != null) {
            html += ohlcRow(t('dataEditor.col.open'), candle.open);
            html += ohlcRow(t('dataEditor.col.close'), candle.close);
            html += ohlcRow(t('dataEditor.col.high'), candle.high);
            html += ohlcRow(t('dataEditor.col.low'), candle.low);
        } else {
            html += `<div style="color:${mutedColor}">${t('common.noData')}</div>`;
        }
        // No synthetic-candle footnote in the tooltip: the caption under the
        // chart is the single disclosure.
        activeChartData?.pnl.brokers.forEach((broker, index) => {
            const v = broker.metric.values[idx];
            if (v == null) return;
            const signColor = signedValueColor(v, isDark, textColor);
            html += `<div style="display:flex;justify-content:space-between;gap:16px;color:${brokerColor(index, isDark)}"><span>${escapeHtml(broker.brokerName)}</span><b style="color:${signColor}">${fmtCurrency(v, true)}</b></div>`;
        });
        return html;
    }

    if (viewMode === 'pnl' && pnlSubmode === 'income') {
        const cc = (key: keyof typeof COLORS) => COLORS[key][isDark ? 'dark' : 'light'];
        const divVal = activeChartData?.pnl.income.dividend.values[idx] ?? 0;
        const intVal = activeChartData?.pnl.income.interest.values[idx] ?? 0;
        const costVal = activeChartData?.pnl.costs.values[idx] ?? 0;
        const depositVal = activeChartData?.pnl.deposits.values[idx] ?? 0;
        const acqNewVal = activeChartData?.pnl.acquisition.fromNewCapital.values[idx] ?? 0;
        const acqReinvestedVal = activeChartData?.pnl.acquisition.fromReinvested.values[idx] ?? 0;
        const signedRow = (label: string, v: number, color: string) => {
            const signColor = signedValueColor(v, isDark, textColor);
            return `<div style="display:flex;justify-content:space-between;gap:16px;color:${color}"><span>${label}</span><b style="color:${signColor}">${fmtCurrency(v, true)}</b></div>`;
        };
        html += signedRow(pnlLabels.dividend, divVal, cc('dividend'));
        html += signedRow(pnlLabels.interest, intVal, cc('interest'));
        html += buildTooltipDivider(tooltipBorder);
        html += signedRow(`<b>${t('assets.distribution.total')}</b>`, divVal + intVal, textColor);
        // Batch 2 dimensions: costs/deposit/acquisition are distinct economic
        // concepts from personal income, so each gets its own row rather than
        // folding into the income total above.
        if (costVal !== 0 || depositVal !== 0 || acqNewVal !== 0 || acqReinvestedVal !== 0) {
            html += buildTooltipDivider(tooltipBorder);
            if (costVal !== 0) html += signedRow(pnlLabels.costs, costVal, cc('costs'));
            if (depositVal !== 0) html += signedRow(pnlLabels.deposit, depositVal, cc('deposit'));
            if (acqNewVal !== 0 || acqReinvestedVal !== 0) {
                // R11: the purchase value in bold, like the income total, then
                // its two halves under it, each in its zone's colour (D26).
                html += signedRow(`<b>${pnlLabels.bookValue}</b>`, acqNewVal + acqReinvestedVal, textColor);
                html += signedRow(`↳ ${pnlLabels.acqNewCapital}`, acqNewVal, cc('bookAssetLike'));
                html += signedRow(`↳ ${pnlLabels.acqReinvested}`, acqReinvestedVal, cc('cashGenerated'));
            }
        }
        return html;
    }

    // See buildGrowthUpdateSeries's matching guard.
    if (viewMode === 'pnl') return html;

    if (pointedDay !== null && activeChartData && view.pctRows) {
        // TWRR and ROI are steps: the one holding the day. The MWRR is a line of true points: the nearest, with its date
        // when that is not the day itself.
        for (const row of view.pctRows) {
            const color = COLORS[row.colorKey][isDark ? 'dark' : 'light'];
            let label = escapeHtml(row.name);
            let value: number | null | undefined;
            if (row.key === 'mwrrCum') {
                const nearest: {date: string; value: number} | null = view.mwrrAt?.(pointedDay) ?? null;
                value = nearest?.value;
                if (nearest && nearest.date !== pointedDay) label += ` <span style="font-size:10px;color:${mutedColor}">${escapeHtml(t('chart.tooltip.valueAt', {values: {date: formatDay(nearest.date)}}))}</span>`;
            } else {
                value = activeChartData.pct[row.key].values[idx];
            }
            if (value == null) continue;
            html += buildTooltipRow(label, formatPercent(Number(value), {signed: false}), color);
        }
        return html;
    }

    html += items
        .filter((p: any) => p.value != null)
        .map((p: any) => {
            const rawVal = Array.isArray(p.value) ? p.value[1] : p.value;
            const val = formatPercent(Number(rawVal), {signed: false});
            return buildTooltipRow(escapeHtml(String(p.seriesName ?? '')), val, p.color);
        })
        .join('');
    return html;
}
