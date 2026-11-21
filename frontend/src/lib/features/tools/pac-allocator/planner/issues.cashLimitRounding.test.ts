// @vitest-environment jsdom
/**
 * Lot ZB of project 67 (specification §16.16): `allocation.cash_limit_exceeded_by_rounding`, the warning a plan of the
 * wide model carries when its rounding ends a cash entry beyond its limit by a few cents (at most one per rounded
 * posting). Its one parameter, `exceeded_by`, is money in the limit's currency. The note names the cash entry and leads
 * to Targets, where the limit is set; its message carries the amount. Nothing reads translated text: the message must
 * resolve (not fall back to its key) and carry the amount as the planner formats it, with no placeholder left.
 */
import {get} from 'svelte/store';
import {locale, t, waitLocale} from 'svelte-i18n';
import {beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {setupI18n} from '$test/component';
import {PlannerDraft} from './draft.svelte';
import {formatPlannerMoneyPlain} from './format';
import {issueMessageKey, presentIssue} from './issues';
import {defaultPolicy} from './policies';
import {REBALANCER_PLANNER_PROFILE} from './profile';
import type {PlannerIssue} from './types';

const CODE = 'allocation.cash_limit_exceeded_by_rounding';

beforeAll(async () => {
    await setupI18n('en');
    locale.set('en');
    await waitLocale('en');
});

function overshoot(): {draft: PlannerDraft; issue: PlannerIssue} {
    const draft = new PlannerDraft('EUR', defaultPolicy(REBALANCER_PLANNER_PROFILE), REBALANCER_PLANNER_PROFILE);
    const broker = draft.addManualBroker('Broker probe');
    draft.addCashEntry(broker.key, 'EUR');
    const issue = {
        code: CODE,
        severity: 'warning',
        kind: 'constraint',
        path: {kind: 'entity', section: 'targets', entity_kind: 'cash', entity_id: `${broker.key}:EUR`},
        message_key: CODE,
        params: [{kind: 'money', name: 'exceeded_by', value: {amount: '0.01', currency: 'EUR'}}],
    } as unknown as PlannerIssue;
    return {draft, issue};
}

describe('the note of a cash limit exceeded by rounding', () => {
    it('names the cash entry, leads to Targets and carries the amount it is exceeded by', () => {
        const {draft, issue} = overshoot();
        const presented = presentIssue(issue, draft);
        expect([presented.step, presented.entity, presented.severity]).toEqual(['targets', 'Broker probe · EUR', 'warning']);
        expect(presented.values.exceeded_by).toBe(formatPlannerMoneyPlain('0.01', 'EUR'));
    });

    it('has its message, with the amount in it', () => {
        const {draft, issue} = overshoot();
        const presented = presentIssue(issue, draft);
        const message = get(t)(issueMessageKey(CODE), {values: presented.values});
        expect(message).not.toBe(issueMessageKey(CODE));
        expect(message).toContain(presented.values.exceeded_by);
        expect(message).not.toContain('{exceeded_by}');
    });
});
