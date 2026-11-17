/**
 * F4a of project 67, step 8: the box of a row of the Rebalancer's exposure bullets. The category, its weight today, after
 * the plan and its target (contract §6.2: today on `F`, the target on the entries' weights, after on `W`), and where
 * «after» stands against the target. The direction comes from an exact comparison of the published weights, never from a
 * subtraction; two weights that read the same at two decimals but differ say how small the gap is. Public weights only.
 * Every text is escaped: the result is HTML handed to ECharts.
 */
import {buildTooltipRow, type TooltipTheme} from '$lib/components/charts/echartsTooltipHelpers';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {formatExactPercent} from '../format';
import type {PlannerTranslate} from '../modeText';
import type {PlannerExactNumber, PlannerNumberAvailability} from '../types';
import {compareExact, UNAVAILABLE_FALLBACKS} from './model';

const KEY = 'tools.portfolioRebalancer.planner.result.exposure';
const SHARED = 'tools.pacAllocator.planner.result';

type UnavailableReason = keyof typeof UNAVAILABLE_FALLBACKS;

/** One row of a bullet chart: a category of the dimension, or the cash (`kind: 'cash'`, always the last). */
export interface BulletRow {
    id: string;
    /** The category's own name, for its colour (`chartCategories`): the type code, the sector or the country, read back
     * from the planner id (`fromPlannerId`); `UNCATEGORISED_CATEGORY_ID` for the undeclared share; `cash` for the cash. */
    key: string;
    label: string;
    kind: 'category' | 'cash';
    before: PlannerNumberAvailability;
    target: PlannerExactNumber;
    final: PlannerNumberAvailability;
}

export interface BulletText {
    now: string;
    after: string;
    target: string;
    below: string;
    above: string;
    on: string;
    /** The two weights read the same at two decimals, but the exact ones differ (the PAC's words, R10.8). */
    hairline: string;
    unavailable: Record<UnavailableReason, string>;
}

export function bulletTooltipText(tr: PlannerTranslate): BulletText {
    const reasons = Object.keys(UNAVAILABLE_FALLBACKS) as UnavailableReason[];
    return {
        now: tr(`${KEY}.now`, {default: 'Today'}),
        after: tr(`${KEY}.after`, {default: 'After the plan'}),
        target: tr(`${KEY}.target`, {default: 'Target'}),
        below: tr(`${KEY}.belowTarget`, {default: 'After the plan: below the target'}),
        above: tr(`${KEY}.aboveTarget`, {default: 'After the plan: above the target'}),
        on: tr(`${KEY}.onTarget`, {default: 'After the plan: in line with the target'}),
        hairline: tr(`${SHARED}.exposures.hairline`, {default: 'by less than 0.01 points'}),
        unavailable: Object.fromEntries(reasons.map((reason) => [reason, tr(`${SHARED}.unavailable.${reason}`, {default: UNAVAILABLE_FALLBACKS[reason]})])) as Record<UnavailableReason, string>,
    };
}

/** Where the weight after the plan stands against the target, from an exact comparison; null when it is not published. */
export function bulletDirection(row: BulletRow): 'below' | 'above' | 'on' | null {
    if (row.final.kind !== 'available') return null;
    const direction = compareExact(row.final.value, row.target);
    if (direction === null) return null;
    return direction < 0 ? 'below' : direction > 0 ? 'above' : 'on';
}

/** `dots`: the colours of the row's three marks (today's grey, the category colour after, the tick of the target). */
export function bulletTooltipHtml(row: BulletRow, text: BulletText, theme: TooltipTheme, dots: {now: string; after: string; target: string}): string {
    const weight = (value: PlannerNumberAvailability) => (value.kind === 'available' ? escapeHtml(formatExactPercent(value.value)) : `— <span style="font-weight:400;color:${theme.mutedColor}">${escapeHtml(text.unavailable[value.reason])}</span>`);
    const lines = [
        `<div style="font-weight:600;margin-bottom:4px">${escapeHtml(row.label)}</div>`,
        buildTooltipRow(escapeHtml(text.now), weight(row.before), dots.now),
        buildTooltipRow(escapeHtml(text.after), weight(row.final), dots.after),
        buildTooltipRow(escapeHtml(text.target), escapeHtml(formatExactPercent(row.target)), dots.target),
    ];
    const direction = bulletDirection(row);
    if (direction !== null && row.final.kind === 'available') {
        const [arrow, words] = direction === 'above' ? ['▲', text.above] : direction === 'below' ? ['▼', text.below] : ['=', text.on];
        const hairline = direction !== 'on' && formatExactPercent(row.final.value) === formatExactPercent(row.target);
        lines.push(`<div style="margin-top:4px;color:${theme.mutedColor}">${arrow} ${escapeHtml(hairline ? `${words}, ${text.hairline}` : words)}</div>`);
    }
    return lines.join('');
}
