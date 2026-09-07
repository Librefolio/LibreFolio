/**
 * @vitest-environment node
 *
 * Branch-exhaustive unit tests for the pure helpers extracted from
 * LotDataQualityBanner.svelte: lot-id resolution, overall severity, and the
 * grouping/dedup/disambiguation pipeline. i18n is injected as a plain
 * `labelForDate` echo so labels are asserted deterministically, no runtime.
 */
import {describe, it, expect} from 'vitest';
import {resolveLotId, groupedSeverity, buildIssueGroups, type IssueSeverity} from './lotDataQualityHelpers';

interface RawIssue {
    code: string;
    severity: IssueSeverity;
    message_i18n_key: string;
    message_params?: Record<string, string | number | boolean | null | undefined>;
}

/** Build an issue; pass `lotId === undefined` with `withParams=false` to omit message_params entirely. */
function issue(code: string, severity: IssueSeverity, lotId?: number, opts: {key?: string; withParams?: boolean; extra?: Record<string, string | number>} = {}): RawIssue {
    const {key = 'msg.' + code, withParams = true, extra = {}} = opts;
    if (!withParams) return {code, severity, message_i18n_key: key};
    return {code, severity, message_i18n_key: key, message_params: {...(lotId === undefined ? {} : {lot_id: lotId}), ...extra}};
}

/** Echo the ISO back so chip labels are deterministic and locale-free. */
const echo = (iso: string) => iso;

describe('resolveLotId', () => {
    it('passes a number through (outer ternary true)', () => {
        expect(resolveLotId(42)).toBe(42);
    });

    it('parses a numeric string (outer false, inner true)', () => {
        expect(resolveLotId('17')).toBe(17);
    });

    it('yields NaN for a non-numeric string (inner true, Number → NaN)', () => {
        expect(resolveLotId('abc')).toBeNaN();
    });

    it('yields NaN for a non-number/non-string (both ternaries false)', () => {
        expect(resolveLotId(undefined)).toBeNaN();
        expect(resolveLotId(null)).toBeNaN();
        expect(resolveLotId(true)).toBeNaN();
        expect(resolveLotId({})).toBeNaN();
    });
});

describe('groupedSeverity', () => {
    it('is error when any error group exists (first if true)', () => {
        expect(groupedSeverity(2, 5)).toBe('error');
    });

    it('is warning when there are no errors but some warnings (first false, second true)', () => {
        expect(groupedSeverity(0, 3)).toBe('warning');
    });

    it('is info when there are neither errors nor warnings (both if false)', () => {
        expect(groupedSeverity(0, 0)).toBe('info');
    });
});

describe('buildIssueGroups', () => {
    it('returns an empty array for no issues', () => {
        expect(buildIssueGroups([], new Map(), echo)).toEqual([]);
    });

    it('builds one group with one labelled chip for a resolvable in-range lot', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', 10)], new Map([[10, '2024-03-15']]), echo);
        expect(groups).toHaveLength(1);
        expect(groups[0]).toMatchObject({code: 'REF', severity: 'warning', messageKey: 'msg.REF'});
        expect(groups[0].lots).toEqual([{lotId: 10, label: '2024-03-15'}]);
    });

    it('preserves message params and key on the group', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', 10, {extra: {foo: 'bar'}})], new Map([[10, 'd']]), echo);
        expect(groups[0].messageParams).toEqual({lot_id: 10, foo: 'bar'});
    });

    it('defaults messageParams to {} when the issue has none (?? {} right arm)', () => {
        const groups = buildIssueGroups([issue('REF', 'info', undefined, {withParams: false})], new Map(), echo);
        expect(groups[0].messageParams).toEqual({});
        expect(groups[0].lots).toEqual([]);
    });

    it('dedups repeated per-lot issues of the same code into one group (existing-group branch)', () => {
        const groups = buildIssueGroups(
            [issue('REF', 'warning', 10), issue('REF', 'warning', 11)],
            new Map([
                [10, '2024-01-02'],
                [11, '2024-01-01'],
            ]),
            echo,
        );
        expect(groups).toHaveLength(1);
        // Ordered by opening date ascending → lot 11 (Jan 1) before lot 10 (Jan 2), distinct dates ⇒ no #index.
        expect(groups[0].lots).toEqual([
            {lotId: 11, label: '2024-01-01'},
            {lotId: 10, label: '2024-01-02'},
        ]);
    });

    it('skips a lot_id that is not in the visible-date map (has() false branch), keeping the group', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', 999)], new Map([[10, 'd']]), echo);
        expect(groups[0].lots).toEqual([]);
    });

    it('skips a NaN lot_id (isFinite false branch)', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', undefined, {extra: {lot_id: 'not-a-number'}})], new Map([[10, 'd']]), echo);
        expect(groups[0].lots).toEqual([]);
    });

    it('does not add the same lot twice within a group (includes true branch)', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', 10), issue('REF', 'warning', 10)], new Map([[10, 'd']]), echo);
        expect(groups[0].lots).toEqual([{lotId: 10, label: 'd'}]);
    });

    it('suffixes lots sharing an opening day with #index in id order (total > 1 branch + id tie-break)', () => {
        const groups = buildIssueGroups(
            [issue('REF', 'warning', 11), issue('REF', 'warning', 10)],
            new Map([
                [10, '2024-05-01'],
                [11, '2024-05-01'],
            ]),
            echo,
        );
        // Same date ⇒ sorted by id (10 then 11), each gets a #index.
        expect(groups[0].lots).toEqual([
            {lotId: 10, label: '2024-05-01 #1'},
            {lotId: 11, label: '2024-05-01 #2'},
        ]);
    });

    it('orders groups by severity: error, then warning, then info', () => {
        const groups = buildIssueGroups([issue('I', 'info'), issue('E', 'error'), issue('W', 'warning')], new Map(), echo);
        expect(groups.map((g) => g.code)).toEqual(['E', 'W', 'I']);
    });
});
