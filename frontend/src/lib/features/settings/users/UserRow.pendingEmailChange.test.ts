// @vitest-environment jsdom
/**
 * UserRow and a change of address waiting for its link (release 1.4, project 71, step 2.10; decision D5.5 U1).
 *
 * An account that asked for a new address from its Profile waits for the link sent to it: the address the account has is
 * still the old one. `AdminUserRead.pending_email_change` (step 2.6) says so, and the row wears a badge, beside the
 * others, so the administrator sees it without opening the account. The contract under test:
 *   - `pending_email_change: true`: the badge `users-badge-pending-email-change` (key
 *     `settings.usersTab.badges.pendingEmailChange`) and the row's `data-pending-email-change="true"`;
 *   - false, or absent (an older server): no badge, `data-pending-email-change="false"`;
 *   - it is a sign beside the account's state, never in place of it: an active account keeps no inactive badge, an
 *     inactive one keeps its own, an administrator keeps «Admin», and the protected one keeps «Protected» — the badge
 *     is added to them;
 *   - the row's address is still the account's, and the panel offers the same actions as without the flag;
 *   - the key is a sentence in the four catalogues.
 *
 * Mocks, as `UserRow.pendingSetup.test.ts`: the identity translator (a message renders as its key) and `formatDateTime`.
 * What runs for real: the row. Never a class or a colour: the colour gates watch the file.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/utils/core/formatDateTime', () => ({formatDateTime: () => '2026-11-12'}));

import UserRow from './UserRow.svelte';
import type {AdminAccount} from './types';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

const BADGE = 'users-badge-pending-email-change';
const KEY = 'settings.usersTab.badges.pendingEmailChange';

function makeAccount(flags: Partial<AdminAccount>): AdminAccount {
    return {id: 5, username: 'zq_anna', email: 'zq_anna@example.com', is_active: true, is_superuser: false, created_at: '2026-11-01T00:00:00Z', protected: false, ...flags};
}

function mountRow(account: AdminAccount) {
    const onAction = vi.fn();
    render(UserRow, {props: {account, isSelf: false, isOnlyActiveAdmin: false, full: false, onAction}});
    return {row: screen.getByTestId('users-row'), onAction};
}

afterEach(cleanup);

describe('UserRow — a change of address waiting for its link', () => {
    it('UPE-01 an account that waits wears the badge, and the row says so', () => {
        const {row} = mountRow(makeAccount({pending_email_change: true}));

        expect(within(row).getByTestId(BADGE)).toHaveTextContent(KEY);
        expect(row.getAttribute('data-pending-email-change')).toBe('true');
    });

    it.each([
        ['false', {pending_email_change: false}],
        ['absent (an older server)', {}],
    ])('UPE-02 pending_email_change %s: no badge, the row says false', (_label, flags) => {
        const {row} = mountRow(makeAccount(flags));

        expect(within(row).queryByTestId(BADGE)).toBeNull();
        expect(row.getAttribute('data-pending-email-change')).toBe('false');
    });

    it("UPE-03 the badge is a sign beside the account's state: an administrator keeps «Admin», a protected one «Protected»", () => {
        const {row} = mountRow(makeAccount({pending_email_change: true, is_superuser: true, protected: true}));

        expect(within(row).getByTestId(BADGE)).toBeInTheDocument();
        expect(row.textContent).toContain('settings.usersTab.badges.admin');
        expect(row.textContent).toContain('settings.usersTab.badges.protected');
        expect(row.textContent).not.toContain('settings.usersTab.badges.inactive');
    });

    it('UPE-04 an inactive account keeps its own state badge, with this one added', () => {
        const {row} = mountRow(makeAccount({pending_email_change: true, is_active: false}));

        expect(within(row).getByTestId(BADGE)).toBeInTheDocument();
        expect(within(row).getByTestId('users-badge-inactive')).toBeInTheDocument();
    });

    it("UPE-05 the address shown is still the account's own, and the panel offers the same actions as without the flag", async () => {
        const waiting = mountRow(makeAccount({pending_email_change: true}));
        expect(waiting.row.textContent).toContain('zq_anna@example.com');
        await fireEvent.click(within(waiting.row).getByTestId('users-row-toggle'));
        const withFlag = [...waiting.row.querySelectorAll('[data-testid^="users-action-"]')].map((node) => node.getAttribute('data-testid'));
        cleanup();

        const plain = mountRow(makeAccount({pending_email_change: false}));
        await fireEvent.click(within(plain.row).getByTestId('users-row-toggle'));
        const without = [...plain.row.querySelectorAll('[data-testid^="users-action-"]')].map((node) => node.getAttribute('data-testid'));

        expect(withFlag.length).toBeGreaterThan(0);
        expect(withFlag).toEqual(without);
    });

    it('UPE-06 the key is a sentence in the four catalogues', () => {
        for (const catalogue of [en, itCatalogue, fr, es]) {
            const badges = (catalogue as {settings: {usersTab: {badges: Record<string, string>}}}).settings.usersTab.badges;
            expect(typeof badges.pendingEmailChange === 'string' && badges.pendingEmailChange.trim().length > 0).toBe(true);
        }
    });
});
