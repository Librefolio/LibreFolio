/**
 * The box of a row of the Rebalancer's exposure bullets (F4a of project 67, step 8): the category, its weight today,
 * after the plan and its target, and the direction of «after» against the target. The direction comes from an exact
 * comparison of the published weights, never from a subtraction; two weights that read the same at two decimals but
 * differ say so («by less than 0.01 points», the PAC's own words). Every text is escaped.
 *
 * The words are passed in (invented here): nothing translated is read. Environment: node, no DOM.
 */
import {describe, expect, it} from 'vitest';
import type {TooltipTheme} from '$lib/components/charts/echartsTooltipHelpers';
import {formatExactPercent} from '../format';
import type {PlannerExactNumber, PlannerNumberAvailability} from '../types';
import {bulletDirection, bulletTooltipHtml, type BulletRow, type BulletText} from './rebalancerExposureTooltip';

const exact = (value: string): PlannerExactNumber => ({kind: 'finite_decimal', value});
const available = (value: string): PlannerNumberAvailability => ({kind: 'available', value: exact(value)});
const UNPUBLISHED: PlannerNumberAvailability = {kind: 'unavailable', reason: 'dependency_unavailable'};

const TEXT: BulletText = {
    now: 'NOW-word',
    after: 'AFTER-word',
    target: 'TARGET-word',
    below: 'BELOW-word',
    above: 'ABOVE-word',
    on: 'ON-word',
    hairline: 'HAIRLINE-word',
    unavailable: {zero_current_invested: 'ZERO-NOW-word', zero_final_invested: 'ZERO-AFTER-word', not_applicable: 'NA-word', dependency_unavailable: 'UNAVAILABLE-word'},
};
const THEME = {bg: '#000001', border: '#000002', textColor: '#000003', mutedColor: '#000004'} as unknown as TooltipTheme;
const DOTS = {now: '#100000', after: '#200000', target: '#300000'};

function row(before: PlannerNumberAvailability, target: string, final: PlannerNumberAvailability, label = 'Row <b>'): BulletRow {
    return {id: 'row', key: 'STOCK', label, kind: 'category', before, target: exact(target), final};
}

describe('the Rebalancer exposure tooltip (F4a step 8)', () => {
    it('tooltip says today, after and target, and the direction from an exact comparison', () => {
        const below = row(available('0.12'), '0.20', available('0.185'));
        const html = bulletTooltipHtml(below, TEXT, THEME, DOTS);
        expect(html).toContain('Row &lt;b&gt;');
        for (const [word, value] of [
            ['NOW-word', '0.12'],
            ['AFTER-word', '0.185'],
            ['TARGET-word', '0.20'],
        ])
            expect(html).toMatch(new RegExp(`${word}[\\s\\S]*${formatExactPercent(exact(value)).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`));
        expect(html).toContain('BELOW-word');
        expect(bulletDirection(below)).toBe('below');
        expect(bulletDirection(row(available('0.3'), '0.20', available('0.21')))).toBe('above');
        expect(bulletDirection(row(available('0.3'), '0.20', available('0.2')))).toBe('on');
    });

    it('two weights equal at two decimals but not exactly: the direction, and how small the gap is', () => {
        const hair = row(available('0.1'), '0.2', available('0.200001'));
        expect(formatExactPercent(exact('0.200001')), 'PREMISE: they read the same').toBe(formatExactPercent(exact('0.2')));
        const html = bulletTooltipHtml(hair, TEXT, THEME, DOTS);
        expect(html).toContain('ABOVE-word');
        expect(html).toContain('HAIRLINE-word');
    });

    it('a weight not published reads its reason, and no direction is given', () => {
        const unpublished = row(UNPUBLISHED, '0.2', UNPUBLISHED);
        expect(bulletDirection(unpublished)).toBeNull();
        const html = bulletTooltipHtml(unpublished, TEXT, THEME, DOTS);
        expect(html).toContain('UNAVAILABLE-word');
        expect(html).not.toContain('BELOW-word');
        expect(html).not.toContain('ABOVE-word');
        expect(html).not.toContain('ON-word');
    });

    it('each line carries the dot of its own mark', () => {
        const html = bulletTooltipHtml(row(available('0.12'), '0.20', available('0.185')), TEXT, THEME, DOTS);
        for (const colour of Object.values(DOTS)) expect(html).toContain(colour);
    });
});
