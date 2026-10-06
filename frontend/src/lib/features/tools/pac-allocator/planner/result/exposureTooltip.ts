/**
 * R9.8: the box of an exposure chart, the same on the maps and on the bars: the category, its
 * ideal weight (the target shares), its actual weight (the shares after the plan) and the direction
 * between the two (R11.7: «ideal vs actual»). The direction comes from an exact comparison of the
 * backend weights, never from a subtraction. Public weights only.
 * Every text is escaped: the result is HTML handed to ECharts.
 */
import {buildTooltipRow, type TooltipTheme} from '$lib/components/charts/echartsTooltipHelpers';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {formatExactPercent} from '../format';
import type {PlannerTranslate} from '../modeText';
import {compareExact, UNAVAILABLE_FALLBACKS, type WeightRow} from './model';

const KEY = 'tools.pacAllocator.planner.result';

type UnavailableReason = keyof typeof UNAVAILABLE_FALLBACKS;

export interface ExposureTooltipText {
    target: string;
    final: string;
    above: string;
    below: string;
    equal: string;
    /** R10.8: the two weights read the same at two decimals, but the exact ones differ. */
    hairline: string;
    unavailable: Record<UnavailableReason, string>;
}

export function exposureTooltipText(tr: PlannerTranslate): ExposureTooltipText {
    const reasons = Object.keys(UNAVAILABLE_FALLBACKS) as UnavailableReason[];
    return {
        target: tr(`${KEY}.exposures.ideal`, {default: 'Ideal distribution'}),
        final: tr(`${KEY}.exposures.actual`, {default: 'Actual distribution'}),
        above: tr(`${KEY}.exposures.above`, {default: 'Above the ideal'}),
        below: tr(`${KEY}.exposures.below`, {default: 'Below the ideal'}),
        equal: tr(`${KEY}.exposures.equal`, {default: 'In line with the ideal'}),
        hairline: tr(`${KEY}.exposures.hairline`, {default: 'by less than 0.01 points'}),
        unavailable: Object.fromEntries(reasons.map((reason) => [reason, tr(`${KEY}.unavailable.${reason}`, {default: UNAVAILABLE_FALLBACKS[reason]})])) as Record<UnavailableReason, string>,
    };
}

/** `dots`: the series colours, when the chart draws the two weights in two colours (the bars). */
export function exposureTooltipHtml(row: WeightRow, text: ExposureTooltipText, theme: TooltipTheme, dots?: {target: string; final: string}): string {
    const final = row.final.kind === 'available' ? escapeHtml(formatExactPercent(row.final.value)) : `— <span style="font-weight:400;color:${theme.mutedColor}">${escapeHtml(text.unavailable[row.final.reason])}</span>`;
    const lines = [
        `<div style="font-weight:600;margin-bottom:4px">${escapeHtml(row.label)}</div>`,
        buildTooltipRow(escapeHtml(text.target), escapeHtml(formatExactPercent(row.target)), dots?.target),
        buildTooltipRow(escapeHtml(text.final), final, dots?.final),
    ];
    const direction = row.final.kind === 'available' ? compareExact(row.final.value, row.target) : null;
    if (direction !== null && row.final.kind === 'available') {
        const [arrow, words] = direction > 0 ? ['▲', text.above] : direction < 0 ? ['▼', text.below] : ['=', text.equal];
        const hairline = direction !== 0 && formatExactPercent(row.final.value) === formatExactPercent(row.target);
        lines.push(`<div style="margin-top:4px;color:${theme.mutedColor}">${arrow} ${escapeHtml(hairline ? `${words}, ${text.hairline}` : words)}</div>`);
    }
    return lines.join('');
}
