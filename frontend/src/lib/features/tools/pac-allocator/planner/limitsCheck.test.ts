/**
 * TL-4 of project 67 (the developer's testlist of 21/11, row 7): the limits check said at once, with the figures.
 *
 *   - an Asset's minimum, an amount, alone above the Tool's base is said by the page, on the last preview's total, until the
 *     preview names the sum of the minimums (`minimumsAboveTotal`); a cash entry is never: the backend deducts its trapped
 *     cash first;
 *   - the sum of the minimums carries the two figures the backend compared, formatted as the preview's total is;
 *   - the Rebalancer says it with its own sentence, wherever it appears (`issueMessageKey`);
 *   - the summary row sums the limits typed, a percentage on the base (`limitSum`), exactly.
 */
import {describe, expect, it} from 'vitest';
import {PlannerDraft, type DraftAsset} from './draft.svelte';
import {formatExactMoneyPlain, formatPlannerMoneyPlain} from './format';
import {issueMessageKey, presentIssues} from './issues';
import {formatLimitSum, limitSum} from './limitSums';
import {REBALANCER_PLANNER_PROFILE, PAC_PLANNER_PROFILE, type PlannerProfile} from './profile';
import {minimumAboveTotal, minimumsAboveTotal, previewLimitProblems, type PreviewLimitProblem} from './request';
import type {PlannerExactMoney, PlannerIssue} from './types';

const SUM_CODE = 'allocation.bounds_min_sum_exceeds_reference';

function asset(key: string, name: string): DraftAsset {
    return {
        key,
        origin: 'manual',
        sourceAssetId: null,
        name,
        ticker: null,
        assetClass: 'etf',
        iconUrl: null,
        active: true,
        price: {amount: '10', currency: 'EUR', quoteBaseQuantity: '1', referenceDate: '2026-11-14'},
        priceManual: false,
        copiedPrice: null,
        priceStamp: null,
        priceSource: null,
        exposures: [],
        copiedExposures: null,
        exposureStamp: null,
        enteredAt: '2026-11-14T10:00:00Z',
    } as unknown as DraftAsset;
}

function scenario(profile: PlannerProfile = REBALANCER_PLANNER_PROFILE) {
    const draft = new PlannerDraft('EUR', 'proportional', profile);
    const broker = draft.addManualBroker('Broker probe');
    draft.addAsset(asset('asset:a', 'Alpha'));
    draft.addAsset(asset('asset:b', 'Beta'));
    draft.data.targets['asset:a'] = '60';
    draft.data.targets['asset:b'] = '40';
    return {draft, brokerKey: broker.key};
}

function money(value: string): PlannerExactMoney {
    return {value: {kind: 'finite_decimal', value}, currency: 'EUR'} as PlannerExactMoney;
}

function sumProblem(entityId: string, minimums: string, reference: string): PreviewLimitProblem {
    return {
        code: SUM_CODE,
        path: {kind: 'field', section: 'targets', entity_kind: 'asset', entity_id: entityId, field: 'minimum'},
        params: [
            {kind: 'money', name: 'minimums', value: {amount: minimums, currency: 'EUR'}},
            {kind: 'money', name: 'reference', value: {amount: reference, currency: 'EUR'}},
        ],
    } as unknown as PreviewLimitProblem;
}

describe('a minimum alone above the base, said at once (TL-4)', () => {
    it('an amount above the total: one line on the Asset, with the base; at the total or below, none', () => {
        const {draft} = scenario();
        draft.setLimit('asset:a', 'minimum', '2500');
        const total = money('2043.98');
        const found = minimumsAboveTotal(draft, total);
        expect(found).toEqual([expect.objectContaining({key: 'limitMinimumAboveTotal', assetKey: 'asset:a', entity: 'Alpha', values: {reference: formatExactMoneyPlain(total)}})]);
        expect(minimumAboveTotal(draft, 'asset:a', total)).toBe(true);

        draft.setLimit('asset:a', 'minimum', '2043.98');
        expect(minimumsAboveTotal(draft, total)).toEqual([]);
        expect(minimumAboveTotal(draft, 'asset:a', total)).toBe(false);
    });

    it('a base that is an exact ratio is compared exactly', () => {
        const {draft} = scenario();
        const third = {value: {kind: 'exact_ratio', numerator: '1000', denominator: '3', display_decimal: '333.333333333333333333', display_scale: 18, display_authority: 'non_authoritative'}, currency: 'EUR'} as unknown as PlannerExactMoney;
        draft.setLimit('asset:a', 'minimum', '333.33');
        expect(minimumAboveTotal(draft, 'asset:a', third)).toBe(false);
        draft.setLimit('asset:a', 'minimum', '333.34');
        expect(minimumAboveTotal(draft, 'asset:a', third)).toBe(true);
    });

    it('no base, a percentage, a cash entry: nothing (a share above 100% is the page’s own line; trapped cash is the backend’s)', () => {
        const {draft, brokerKey} = scenario();
        draft.setLimit('asset:a', 'minimum', '99999');
        expect(minimumsAboveTotal(draft, null)).toEqual([]);
        draft.setLimit('asset:a', 'minimum', '99%');
        expect(minimumsAboveTotal(draft, money('10'))).toEqual([]);
        const cash = draft.addCashEntry(brokerKey, 'EUR');
        draft.setLimit('asset:a', 'minimum', '');
        draft.setLimit(cash.key, 'minimum', '99999');
        expect(minimumsAboveTotal(draft, money('10'))).toEqual([]);
    });

    it('once the preview names the Asset in the sum of the minimums, the sum’s line says it', () => {
        const {draft} = scenario();
        draft.setLimit('asset:a', 'minimum', '2500');
        draft.setLimit('asset:b', 'minimum', '3000');
        const total = money('2043.98');
        expect(minimumsAboveTotal(draft, total, [sumProblem('asset:a', '5500', '2043.98')]).map((problem) => problem.assetKey)).toEqual(['asset:b']);
    });
});

describe('the sum of the minimums with its two figures (TL-4)', () => {
    it('one line naming every entry, with the sum and the base as the preview reads them', () => {
        const {draft} = scenario();
        const found = previewLimitProblems(draft, [sumProblem('asset:a', '5500', '2043.98'), sumProblem('asset:b', '5500', '2043.98')]);
        expect(found).toEqual([expect.objectContaining({key: 'bounds_min_sum_exceeds_reference', entity: 'Alpha, Beta', values: {minimums: formatPlannerMoneyPlain('5500', 'EUR'), reference: formatPlannerMoneyPlain('2043.98', 'EUR')}})]);
    });

    it('a base with more digits than the currency reads as the preview’s total does: rounded, with ≈', () => {
        const {draft} = scenario();
        const [line] = previewLimitProblems(draft, [sumProblem('asset:a', '5500', '333.333333333333333333')]);
        const total = {value: {kind: 'exact_ratio', numerator: '1000', denominator: '3', display_decimal: '333.333333333333333333', display_scale: 18, display_authority: 'non_authoritative'}, currency: 'EUR'} as unknown as PlannerExactMoney;
        expect(line.values.reference).toBe(formatExactMoneyPlain(total));
        expect(line.values.reference.startsWith('≈')).toBe(true);
    });

    it('the Rebalancer says it from its own catalogue, the PAC from the shared one; the other codes stay shared', () => {
        expect(issueMessageKey(SUM_CODE, 'rebalancer')).toBe(`tools.portfolioRebalancer.planner.issues.${SUM_CODE}`);
        expect(issueMessageKey(SUM_CODE, 'pac')).toBe(`tools.pacAllocator.planner.issues.${SUM_CODE}`);
        expect(issueMessageKey(SUM_CODE)).toBe(`tools.pacAllocator.planner.issues.${SUM_CODE}`);
        expect(issueMessageKey('allocation.bound_min_above_max', 'rebalancer')).toBe('tools.pacAllocator.planner.issues.allocation.bound_min_above_max');
    });

    it('a refused plan carries the same figures, under each Tool’s key', () => {
        const {draft} = scenario();
        const issue = {...sumProblem('asset:a', '5500', '2043.98'), severity: 'error', kind: 'invalid', message_key: SUM_CODE} as unknown as PlannerIssue;
        const [rebalancer] = presentIssues([issue], draft, undefined, 'rebalancer');
        expect(rebalancer.messageKey).toBe(`tools.portfolioRebalancer.planner.issues.${SUM_CODE}`);
        expect(rebalancer.values).toMatchObject({minimums: formatPlannerMoneyPlain('5500', 'EUR'), reference: formatPlannerMoneyPlain('2043.98', 'EUR')});
        expect(presentIssues([issue], draft)[0].messageKey).toBe(`tools.pacAllocator.planner.issues.${SUM_CODE}`);
    });
});

describe('the summary row’s sums (TL-4)', () => {
    it('amounts as typed, a percentage on the base, every row (cash entries too), exactly', () => {
        const {draft, brokerKey} = scenario(PAC_PLANNER_PROFILE);
        const cash = draft.addCashEntry(brokerKey, 'EUR');
        draft.setLimit('asset:a', 'minimum', '100.10');
        draft.setLimit('asset:b', 'minimum', '25%');
        draft.setLimit(cash.key, 'minimum', '30');
        draft.setLimit('asset:a', 'maximum', '500');
        const sum = limitSum(draft, 'minimum', money('1000'));
        // 100.10 + 25% × 1000 + 30 = 380.10
        expect(sum.kind === 'sum' && formatLimitSum(sum.value, 'EUR')).toBe(formatPlannerMoneyPlain('380.10', 'EUR'));
        const maximum = limitSum(draft, 'maximum', money('1000'));
        expect(maximum.kind === 'sum' && formatLimitSum(maximum.value, 'EUR')).toBe(formatPlannerMoneyPlain('500', 'EUR'));
    });

    it('none typed: none; a percentage without a base: unknown; an invalid field is left out', () => {
        const {draft} = scenario();
        expect(limitSum(draft, 'minimum', money('1000'))).toEqual({kind: 'none'});
        draft.setLimit('asset:a', 'minimum', '10%');
        expect(limitSum(draft, 'minimum', null)).toEqual({kind: 'unknown'});
        draft.setLimit('asset:a', 'minimum', 'abc');
        expect(limitSum(draft, 'minimum', null)).toEqual({kind: 'none'});
    });

    it('a share of a base that is an exact ratio: ≈ at the minor unit', () => {
        const {draft} = scenario();
        draft.setLimit('asset:a', 'minimum', '50%');
        const third = {value: {kind: 'exact_ratio', numerator: '1000', denominator: '3', display_decimal: '333.333333333333333333', display_scale: 18, display_authority: 'non_authoritative'}, currency: 'EUR'} as unknown as PlannerExactMoney;
        const sum = limitSum(draft, 'minimum', third);
        // 50% of 1000/3 = 500/3 = 166.666…
        expect(sum.kind === 'sum' && formatLimitSum(sum.value, 'EUR')).toBe(formatPlannerMoneyPlain('166.67', 'EUR', {approx: true}));
    });
});
