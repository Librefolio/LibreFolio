/**
 * commitRefusal.test.ts — W-B39: the words of a refused Split pair or Promote pair.
 *
 * The Transactions page commits a Split pair and a Promote pair on its own, through `commitTransactions`, which
 * shows no toast. A refusal used to reach only the console; `commitRefusalMessage` composes the error toast
 * instead. Its contract:
 *   - the action's title first, escaped: it is text, never markup;
 *   - then one line `• <reason>` per distinct reason, in order. A reason is an issue resolved by
 *     `resolveIssueMessage` with the context the caller passes; a text repeated by several issues is written
 *     once, where it first appears; the resolver's own markup is kept as it is (it escapes its inputs itself);
 *   - with no issue, the network error is the one reason, escaped — unless it is the title itself, the fallback
 *     the page hands `commitTransactions`, which would only repeat it; with issues, the network error adds nothing
 *     (a 422 carries both, and its issues are the reasons);
 *   - with neither, the title alone.
 *
 * `t` stands in for svelte-i18n's `$t` as in resolveValidationMessage.test.ts: a missing key resolves to the key
 * itself, a known one interpolates its `{placeholder}` tokens from `opts.values`.
 *
 * Until the cure lands this file fails at its import: `commitRefusal.ts` is new code (W-B39).
 */

import {describe, expect, it} from 'vitest';
import {commitRefusalMessage} from './commitRefusal';
import type {ResolverContext} from './resolveValidationMessage';
import type {TxValidationIssue} from './txCommitApi';

/** A missing key resolves to the key itself; a known one interpolates `{placeholder}` from `opts.values`. */
function makeT(known: Record<string, string> = {}) {
    return (key: string, opts?: {values?: Record<string, unknown>}): string => {
        const tpl = known[key];
        if (tpl === undefined) return key;
        const values = opts?.values ?? {};
        return tpl.replace(/\{(\w+)\}/g, (_m, k) => (values[k] !== undefined ? String(values[k]) : `{${k}}`));
    };
}

const TITLE = 'Promote failed';
const t = makeT({
    'transactions.errors.alreadyPaired': 'Already linked to another transaction',
    'transactions.errors.noPromoteRule': 'No promotion rule matches these two types',
    'transactions.errors.accessDenied': 'Editor role required for {brokerName}',
});

/** An issue as `commitTransactions` hands it over: the server's own, `operation` included. */
function issue(code: string, extra: Partial<TxValidationIssue> = {}): TxValidationIssue {
    return {operation: 'promote', index: 0, ref_id: null, error: `raw ${code}`, code, ...extra};
}

describe('commitRefusalMessage — the title, then one line per reason (W-B39)', () => {
    it('writes the title, then one bullet line per reason, in order', () => {
        const msg = commitRefusalMessage({issues: [issue('alreadyPaired'), issue('noPromoteRule')]}, TITLE, t);
        expect(msg).toBe('Promote failed\n• Already linked to another transaction\n• No promotion rule matches these two types');
    });

    it('writes a repeated reason once, where it first appears — the same code in other words stays two reasons', () => {
        const issues = [issue('noPromoteRule'), issue('alreadyPaired', {ref_id: 11}), issue('accessDenied', {params: {brokerId: 7}}), issue('alreadyPaired', {ref_id: 12}), issue('accessDenied', {params: {brokerId: 8}}), issue('noPromoteRule')];
        const expected = ['Promote failed', '• No promotion rule matches these two types', '• Already linked to another transaction', '• Editor role required for Broker #7', '• Editor role required for Broker #8'];
        expect(commitRefusalMessage({issues}, TITLE, t)).toBe(expected.join('\n'));
    });

    it('resolves the reasons with the context it is given', () => {
        const ctx: ResolverContext = {brokers: [{id: 7, name: 'Fineco'}]};
        expect(commitRefusalMessage({issues: [issue('accessDenied', {params: {brokerId: 7}})]}, TITLE, t, ctx)).toBe('Promote failed\n• Editor role required for Fineco');
    });

    it('hands the issue over whole: a split refused for a missing exchange rate reads the split text, its pairs filled in', () => {
        const tSplit = makeT({
            'transactions.errors.wacFxUnavailableSplit': 'Average cost of the units that leave needs the {pairs} rate',
            'transactions.errors.wacFxUnavailable': 'WAC calculation failed.',
        });
        const missingRate: TxValidationIssue = {
            operation: 'split',
            index: 0,
            ref_id: 41,
            error: 'WAC calculation failed: missing FX pairs USD/EUR',
            code: 'wacFxUnavailable',
            params: {pairs: ['USD/EUR'], pair_details: [{pair: 'USD/EUR', dates: ['2026-10-01']}]},
        };
        const [head, ...lines] = commitRefusalMessage({issues: [missingRate]}, 'Split failed', tSplit).split('\n');
        expect(head).toBe('Split failed');
        expect(lines).toHaveLength(1);
        expect(lines[0].startsWith('• Average cost of the units that leave needs the ')).toBe(true);
        expect(lines[0]).toContain('USD');
        expect(lines[0]).toContain('EUR');
        expect(lines[0]).not.toContain('{pairs}');
    });
});

describe('commitRefusalMessage — a network error, and nothing at all (W-B39)', () => {
    it('with no issue, the network error is the one reason, escaped', () => {
        expect(commitRefusalMessage({issues: [], networkError: 'Network Error'}, TITLE, t)).toBe('Promote failed\n• Network Error');
        expect(commitRefusalMessage({issues: [], networkError: 'Bad <b>gateway</b> & co'}, TITLE, t)).toBe('Promote failed\n• Bad &lt;b&gt;gateway&lt;/b&gt; &amp; co');
    });

    it('with no issue, a network error that is the title itself adds nothing: the title alone, no bullet line', () => {
        // An error with no message of its own reaches the page as trySave's fallback, which the page sets to the title.
        expect(commitRefusalMessage({issues: [], networkError: TITLE}, TITLE, t)).toBe('Promote failed');
    });

    it('with issues, the network error adds nothing: a 422 carries both, and its issues are the reasons', () => {
        const msg = commitRefusalMessage({issues: [issue('alreadyPaired')], networkError: 'Request failed with status code 422'}, TITLE, t);
        expect(msg).toBe('Promote failed\n• Already linked to another transaction');
    });

    it('with neither, the title alone', () => {
        expect(commitRefusalMessage({issues: []}, TITLE, t)).toBe('Promote failed');
    });
});

describe('commitRefusalMessage — what reaches {@html} (W-B39)', () => {
    it('escapes the title: a tag in it is text, never markup', () => {
        expect(commitRefusalMessage({issues: [issue('alreadyPaired')]}, 'Split <b>failed</b>', t)).toBe('Split &lt;b&gt;failed&lt;/b&gt;\n• Already linked to another transaction');
        const alone = commitRefusalMessage({issues: []}, 'Split <b>failed</b>', t);
        expect(alone).toBe('Split &lt;b&gt;failed&lt;/b&gt;');
        expect(alone).not.toContain('<b>');
    });

    it('keeps the markup a reason is written with, and escapes what the user wrote once, not twice', () => {
        const tMarkup = makeT({'transactions.errors.accessDenied': 'Editor role required for <strong>{brokerName}</strong>'});
        const ctx: ResolverContext = {brokers: [{id: 7, name: 'Fineco & <Co>'}]};
        const msg = commitRefusalMessage({issues: [issue('accessDenied', {params: {brokerId: 7}})]}, TITLE, tMarkup, ctx);
        expect(msg).toBe('Promote failed\n• Editor role required for <strong>Fineco &amp; &lt;Co&gt;</strong>');
    });
});
