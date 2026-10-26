/**
 * The line under a dead setup link (A5-6): which message and which support link `/setup` shows.
 *
 * Only an EXPIRED link on a managed instance has its own line, because only that one is sent again by the hosting
 * provider: «This link has expired. If you did not receive a new one by email, contact support.» (the developer's
 * wording, 26/10: generic on purpose, it covers the automatic resend and a manual one). The line is
 * `auth.setup.expiredManagedHint`, the one place to change it; beside it, a link to the instance's support address when
 * it has one.
 *
 * The support link is the instance's `support_url`, checked again as the asset search does (`supportChannel`): a mailto
 * with one address, or an http(s) page; anything else — and a missing value — draws no link, and never a GitHub page
 * (this is not a report of a bug in LibreFolio).
 */
import {describe, expect, it} from 'vitest';
import {setupLinkNotice} from './expiredSetupNotice';

const GENERIC = 'auth.setup.newLinkHint';
const MANAGED_EXPIRED = 'auth.setup.expiredManagedHint';

describe('setupLinkNotice — what changes only for an expired link on a managed instance', () => {
    it.each(['consumed', 'revoked', 'unknown', 'missing', 'checking', 'error'])('keeps the generic line for %s, with no support link even when the instance has one', (status) => {
        expect(setupLinkNotice(status, true, 'mailto:help@example.com')).toEqual({hintKey: GENERIC, supportHref: null});
    });

    it('keeps the generic line for an expired link on an instance that is not a confirmed managed one, with no support link', () => {
        expect(setupLinkNotice('expired', false, 'mailto:help@example.com')).toEqual({hintKey: GENERIC, supportHref: null});
    });
});

describe('setupLinkNotice — an expired link on a managed instance', () => {
    it.each([
        ['a mailto', 'mailto:help@example.com', 'mailto:help@example.com'],
        ['a page', 'https://support.example.com/help', 'https://support.example.com/help'],
        ['a page, normalized', 'https://support.example.com', 'https://support.example.com/'],
    ])('links to the support address when it is %s', (_label, value, href) => {
        expect(setupLinkNotice('expired', true, value)).toEqual({hintKey: MANAGED_EXPIRED, supportHref: href});
    });

    it.each([
        ['unset', null],
        ['undefined', undefined],
        ['empty', ''],
        ['a mailto with a header', 'mailto:help@example.com?subject=x'],
        ['a mailto with two addresses', 'mailto:a@example.com,b@example.com'],
        ['a script', 'javascript:alert(1)'],
        ['a page with user info', 'https://user:secret@support.example.com/'],
        ['something that is not an address', 'help'],
    ])('draws the line without a link when the support address is %s, and never a GitHub page', (_label, value) => {
        expect(setupLinkNotice('expired', true, value)).toEqual({hintKey: MANAGED_EXPIRED, supportHref: null});
    });
});
