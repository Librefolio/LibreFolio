// @vitest-environment jsdom
/**
 * BrimNoticeList — the «open an issue» link under a notice (lot N74 · Fineco, safe rows; W-B83). Component test
 * (Vitest + jsdom).
 *
 * A BRIM plugin may ask the user to report a file it could not read whole: Fineco's `fineco_incomplete_rows` notice
 * carries `context.report_issue: true`. The contract (lot N74, F): under a notice whose `context.report_issue === true`,
 * inside that notice's own `brim-notice` item, the list renders one link `brim-notice-report-issue` to
 * `https://github.com/Librefolio/LibreFolio/issues/new`, opened in a new tab (`target="_blank"`, a `rel` holding
 * `noopener` and `noreferrer`), its text the translation of the existing key `importWizard.fixStep.reportIssueLink` —
 * the words of the fix step's own link (`fix-step-report-issue-link`). Without the flag — no context, a null one, no
 * key, `false`, the string `"true"`, the number 1 — no link. The flag decides, not the severity nor the code.
 *
 * Reds: every test that expects a link (today the list renders none). Guards: the notices without the flag, green today
 * and after; each reads the notice it rendered first (its item and its message), so that "no link" cannot pass on a list
 * that rendered nothing.
 *
 * Nothing here asserts translated text: the link's text is compared with `$t(key)` resolved by the same store, after a
 * control that the catalogue has the key. The catalogue is the app's (`$lib/i18n` registers it), booted by the shared
 * harness's `setupI18n`, as the neighbouring component tests do (`GapFixStep`, `ImportWizardModal`, `FixFlaggedStep`):
 * none of them mocks `t`. The notices but one use codes no catalogue will ever name (`probe_*`), so each shows its own
 * `message`, a needle the test locates it by — a real code, translated by a cure, would hide it.
 *
 * Registered in `scripts/test_runner/_frontend_transaction.py`, in the Vitest list of `front_tx_unit` (action
 * `front-transaction tx-unit`), next to `ParseDetailModal.test.ts`, whose modal mounts this list.
 */
import {beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';
import {render, screen, setupI18n, within} from '$test/component';
import {t} from '$lib/i18n';
import type {BrimNotice} from '$lib/types';
import BrimNoticeList from './BrimNoticeList.svelte';

const LINK = 'brim-notice-report-issue';
const NEW_ISSUE_URL = 'https://github.com/Librefolio/LibreFolio/issues/new';
const LINK_KEY = 'importWizard.fixStep.reportIssueLink';

/** A notice as the backend sends it, without evidence; its `message` is `NEEDLE-<code>`. */
function notice(code: string, context: BrimNotice['context'], severity: 'info' | 'warning' = 'info'): BrimNotice {
    return {severity, code, message: `NEEDLE-${code}`, evidence: [], context};
}

/** The `brim-notice` item whose message shows `NEEDLE-<code>`: the presence barrier of a test, and the scope of its link. */
function itemOf(code: string): HTMLElement {
    const needle = `NEEDLE-${code}`;
    const item = screen.getAllByTestId('brim-notice').find((li) => within(li).getByTestId('brim-notice-message').textContent?.includes(needle));
    if (!item) throw new Error(`no brim-notice item shows the message ${needle}`);
    return item;
}

beforeAll(async () => {
    await setupI18n();
});

describe('BrimNoticeList — the «open an issue» link under a notice flagged report_issue (lot N74)', () => {
    // Red today: the list renders no link.
    it('renders it inside the flagged notice: the GitHub new-issue page, in a new tab, worded by the fix step key', () => {
        const label = get(t)(LINK_KEY);
        expect(label, 'control: the catalogue has the key the link reads').not.toBe(LINK_KEY);

        render(BrimNoticeList, {notices: [notice('fineco_incomplete_rows', {count: 2, report_issue: true})]});

        const items = screen.getAllByTestId('brim-notice');
        expect(items, 'presence barrier: the one notice rendered').toHaveLength(1);
        const link = within(items[0]).getByTestId(LINK);
        expect(link.tagName).toBe('A');
        expect(link).toHaveAttribute('href', NEW_ISSUE_URL);
        expect(link).toHaveAttribute('target', '_blank');
        expect((link.getAttribute('rel') ?? '').split(/\s+/)).toEqual(expect.arrayContaining(['noopener', 'noreferrer']));
        expect(link.textContent?.trim()).toBe(label);
    });

    // Red today: no link, whatever the severity.
    it.each(['info', 'warning'] as const)('renders it under a flagged %s notice: the flag decides, not the severity', (severity) => {
        render(BrimNoticeList, {notices: [notice('probe_flagged', {report_issue: true}, severity)]});

        const item = itemOf('probe_flagged');
        expect(item).toHaveAttribute('data-severity', severity);
        expect(within(item).getAllByTestId(LINK)).toHaveLength(1);
    });

    // Red today: no link anywhere.
    it('renders it once, under the flagged notice only, in a list of several', () => {
        render(BrimNoticeList, {
            notices: [notice('probe_plain', {count: 1}), notice('probe_flagged', {count: 2, report_issue: true}), notice('probe_other', null, 'warning')],
        });

        expect(within(itemOf('probe_flagged')).getAllByTestId(LINK)).toHaveLength(1);
        expect(within(itemOf('probe_plain')).queryByTestId(LINK)).toBeNull();
        expect(within(itemOf('probe_other')).queryByTestId(LINK)).toBeNull();
        expect(screen.getAllByTestId(LINK)).toHaveLength(1);
    });

    // Guards: green today and after — only `report_issue === true` asks for the link.
    it.each([
        ['no context', undefined],
        ['a null context', null],
        ['a context without the key', {count: 3}],
        ['report_issue false', {count: 3, report_issue: false}],
        ['report_issue the string "true"', {count: 3, report_issue: 'true'}],
        ['report_issue the number 1', {count: 3, report_issue: 1}],
    ] as [string, BrimNotice['context']][])('guard: %s — no link', (_case, context) => {
        render(BrimNoticeList, {notices: [notice('probe_unflagged', context)]});

        const item = itemOf('probe_unflagged');
        expect(within(item).getByTestId('brim-notice-message')).toHaveTextContent('NEEDLE-probe_unflagged');
        expect(screen.queryByTestId(LINK)).toBeNull();
    });
});
