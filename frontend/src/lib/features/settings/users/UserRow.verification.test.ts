// @vitest-environment jsdom
/**
 * UserRow and email verification (lot E5b, developer decision 44): «Reactivate» for an inactive account on a full
 * instance.
 *
 * The contract under test: an account waiting for its email verification with a live link (`holds_place: true`, from
 * `GET /users`) already holds its place, so «Reactivate» stays usable on a full instance — no `limit` reason —, and a
 * click asks for it; an inactive account without it (`holds_place` false or absent: an older server) is turned off on a
 * full instance with the `limit` reason, as before; with a free place «Reactivate» is usable either way. A control
 * turned off is asserted disabled with its reason and never clicked: jsdom dispatches a click to a disabled button,
 * and Svelte's delegated handler runs, where a browser sends nothing.
 *
 * Lot E-7 (the developer's decision of 21/10/2026): an account waiting for its email verification shows the badge
 * «Waiting for verification» in place of «Deactivated» — even after its link expired (`holds_place` false) —, with a
 * hint on hover and in its panel. The contract under test, for `AdminAccount.pending_verification` (from `GET /users`,
 * optional: absent on an older server):
 *   - the row is «waiting for verification» when `pending_verification === true && !is_active && !pending_setup`.
 *     `holds_place` takes no part in it: the badge is the same for a live link and for an expired one;
 *   - then the list shows the badge `users-badge-pending-verification` (key `settings.usersTab.badges.pendingVerification`),
 *     whose `title` — the hover hint — is the key `settings.usersTab.pendingVerificationHint`, and not the «Deactivated»
 *     badge, which gains the test id `users-badge-inactive` (asserted by it and by its key, `settings.usersTab.badges.inactive`);
 *     every other inactive row — the flag absent or false — keeps that badge, and shows no verification one;
 *   - the row publishes `data-pending-verification="true"`, else `"false"` — an active account, the flag absent, and the
 *     account whose setup link it waits for (`pending_setup`) included: the attribute is the derived state above, not the
 *     raw flag;
 *   - opened, the panel shows the hint `users-pending-verification-hint` (same key as the badge's title); the actions are
 *     those of any inactive account, «Reactivate» among them, which on a full instance follows `holds_place` exactly as
 *     UVR-01 and UVR-02 pin — usable with a live link, off with the `limit` reason once it expired. The hint is the barrier
 *     of those cases: it proves the row they read is drawn as waiting, not as a plain inactive one;
 *   - precedence: `pending_setup: true` wins. The setup badge `users-badge-pending-setup` and the setup hint
 *     `users-pending-setup-hint` are drawn, with neither the verification badge nor its hint, nor «Deactivated», even when
 *     `pending_verification` is also true — and then `data-pending-verification` is `"false"`: the derived state is
 *     `pending_verification && !is_active && !pending_setup`;
 *   - an active account with `pending_verification: true` (a server never sends it, but the row must not lie): no
 *     verification badge, no inactive badge, no hint, `data-pending-verification="false"`.
 * The badge, the hint and the two test ids are keys and attributes read through the identity translator below; never a
 * translation, never a class.
 *
 * Mocks: the identity translator (a message renders as its key) and `formatDateTime` (the row's date is not the
 * subject). What runs for real: the row. Red until E5b is applied (`AdminAccount.holds_place`); UVR-04…11 red until
 * E-7 (`AdminAccount.pending_verification`, the badge and the hint, `users-badge-inactive`, `data-pending-verification`).
 * Their fixtures carry the flag through `Flags` below, so the file compiles before and after `types.ts` gains it.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/utils/core/formatDateTime', () => ({formatDateTime: () => '2026-10-16'}));

import UserRow from './UserRow.svelte';
import type {AdminAccount} from './types';

function waiting(holdsPlace: boolean | undefined): AdminAccount {
    const account: AdminAccount = {id: 7, username: 'zq_vera', email: 'zq_vera@example.com', is_active: false, is_superuser: false, created_at: '2026-10-16T00:00:00Z', protected: false};
    return holdsPlace === undefined ? account : {...account, holds_place: holdsPlace};
}

async function opened(account: AdminAccount, full: boolean): Promise<{onAction: ReturnType<typeof vi.fn>; reactivate: HTMLElement}> {
    const onAction = vi.fn();
    render(UserRow, {props: {account, isSelf: false, isOnlyActiveAdmin: false, full, onAction}});
    await fireEvent.click(screen.getByTestId('users-row-toggle'));
    return {onAction, reactivate: screen.getByTestId('users-action-reactivate')};
}

// --- E-7 fixtures and helpers ---------------------------------------------

/** The fields a case sets beyond the base account. `pending_verification` is declared here, not read from `AdminAccount`: it exists there only once E-7 is applied. */
interface Flags {
    is_active?: boolean;
    holds_place?: boolean;
    pending_setup?: boolean;
    pending_verification?: boolean;
}

/** An account as `GET /users` lists it: active, a member, unflagged. A flag only when given — absent is the answer of an older server. */
function makeAccount(flags: Flags = {}): AdminAccount {
    return {id: 8, username: 'zq_wanda', email: 'zq_wanda@example.com', is_active: true, is_superuser: false, created_at: '2026-10-21T00:00:00Z', protected: false, ...flags} as AdminAccount;
}

const BADGE_PENDING_VERIFICATION = 'settings.usersTab.badges.pendingVerification';
const BADGE_INACTIVE = 'settings.usersTab.badges.inactive';
const BADGE_PENDING_SETUP = 'settings.usersTab.badges.pendingSetup';
const HINT_PENDING_VERIFICATION = 'settings.usersTab.pendingVerificationHint';
const HINT_PENDING_SETUP = 'settings.usersTab.pendingSetupHint';

/** Waiting for its email verification, whatever `holds_place` says: a live link holds its place, an expired one does not, an older server sends nothing. */
const WAITING = [
    {label: 'a live link (holds_place true)', account: makeAccount({is_active: false, pending_verification: true, holds_place: true})},
    {label: 'an expired link (holds_place false)', account: makeAccount({is_active: false, pending_verification: true, holds_place: false})},
    {label: 'holds_place absent', account: makeAccount({is_active: false, pending_verification: true})},
];

/** An inactive account that waits for no verification: the flag false or absent, `holds_place` aside. */
const PLAIN_INACTIVE = [
    {label: 'the flag absent (an older server)', account: makeAccount({is_active: false})},
    {label: 'the flag false', account: makeAccount({is_active: false, pending_verification: false})},
    {label: 'the flag false, holds_place true', account: makeAccount({is_active: false, pending_verification: false, holds_place: true})},
    {label: 'the flag absent, holds_place true', account: makeAccount({is_active: false, holds_place: true})},
];

/** Mount one row, its panel closed. */
function mountRow(account: AdminAccount, full = false): {row: HTMLElement; onAction: ReturnType<typeof vi.fn>} {
    const onAction = vi.fn();
    render(UserRow, {props: {account, isSelf: false, isOnlyActiveAdmin: false, full, onAction}});
    return {row: screen.getByTestId('users-row'), onAction};
}

/** Mount one row and open its panel: the panel is what the toggle controls. */
async function openRow(account: AdminAccount, full = false): Promise<{row: HTMLElement; panel: HTMLElement; onAction: ReturnType<typeof vi.fn>}> {
    const {row, onAction} = mountRow(account, full);
    const toggle = within(row).getByTestId('users-row-toggle');
    await fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const panelId = toggle.getAttribute('aria-controls');
    const panel = panelId === null ? null : document.getElementById(panelId);
    if (panel === null) throw new Error(`users-row-toggle controls #${panelId}, which is not in the document: the panel did not open`);
    return {row, panel, onAction};
}

/** No «Deactivated» badge, by its test id and by its key. */
function expectNoInactiveBadge(row: HTMLElement): void {
    expect(within(row).queryByTestId('users-badge-inactive'), 'the inactive badge, by test id').toBeNull();
    expect(within(row).queryByText(BADGE_INACTIVE), 'the inactive badge, by key').toBeNull();
}

/** No «Waiting for verification» badge, by its test id and by its key. */
function expectNoVerificationBadge(row: HTMLElement): void {
    expect(within(row).queryByTestId('users-badge-pending-verification'), 'the verification badge, by test id').toBeNull();
    expect(within(row).queryByText(BADGE_PENDING_VERIFICATION), 'the verification badge, by key').toBeNull();
}

afterEach(() => {
    cleanup();
});

describe('UserRow — «Reactivate» on a full instance', () => {
    it('UVR-01: a waiting account whose live link holds its place: usable, no limit reason, and the click asks for it', async () => {
        const account = waiting(true);
        const {onAction, reactivate} = await opened(account, true);

        expect(reactivate).toBeEnabled();
        expect(reactivate).not.toHaveAttribute('data-disabled-reason');
        expect(screen.queryByText('settings.usersTab.reasons.limit')).toBeNull();
        await fireEvent.click(reactivate);
        expect(onAction).toHaveBeenCalledWith('reactivate', account);
    });

    it.each([
        ['holds_place false', false],
        ['holds_place absent (an older server)', undefined],
    ])('UVR-02: an inactive account with %s: turned off with the limit reason', async (_label, holdsPlace) => {
        const {reactivate} = await opened(waiting(holdsPlace), true);

        expect(reactivate).toBeDisabled();
        expect(reactivate).toHaveAttribute('data-disabled-reason', 'limit');
        expect(screen.getByText('settings.usersTab.reasons.limit')).toBeInTheDocument();
    });

    it.each([true, false])('UVR-03: with a free place, «Reactivate» is usable whatever holds_place says (%s)', async (holdsPlace) => {
        const {reactivate} = await opened(waiting(holdsPlace), false);

        expect(reactivate).toBeEnabled();
        expect(reactivate).not.toHaveAttribute('data-disabled-reason');
    });
});

// =========================================================================
describe('UserRow — an account waiting for its email verification (E-7)', () => {
    // red until E-7
    it.each(WAITING)('UVR-04: $label — the badge «Waiting for verification» with its hover hint, not «Deactivated»', ({account}) => {
        const {row} = mountRow(account);

        // Seen in the list, without opening the row: where «Deactivated» stood.
        const badge = within(row).getByTestId('users-badge-pending-verification');
        expect(badge.textContent?.trim()).toBe(BADGE_PENDING_VERIFICATION);
        expect(badge).toHaveAttribute('title', HINT_PENDING_VERIFICATION);
        expectNoInactiveBadge(row);
        expect(within(row).queryByTestId('users-badge-pending-setup'), 'the setup badge').toBeNull();
    });

    // red until E-7
    it.each([
        ...WAITING.map((scene) => ({...scene, label: `${scene.label}, waiting`, expected: 'true'})),
        {label: 'inactive, the flag absent', account: makeAccount({is_active: false}), expected: 'false'},
        {label: 'inactive, the flag false', account: makeAccount({is_active: false, pending_verification: false}), expected: 'false'},
        {label: 'active, the flag absent', account: makeAccount(), expected: 'false'},
        {label: 'active, the flag false', account: makeAccount({pending_verification: false}), expected: 'false'},
    ])('UVR-05: $label — the row publishes data-pending-verification as derived', ({account, expected}) => {
        const {row} = mountRow(account);

        expect(row).toHaveAttribute('data-pending-verification', expected);
    });

    // red until E-7: «Deactivated» has no test id today
    it.each(PLAIN_INACTIVE)('UVR-06: an inactive account, $label — keeps «Deactivated», no verification badge, no hint in its panel', async ({account}) => {
        const {row, panel} = await openRow(account);

        expect(within(row).getByTestId('users-badge-inactive').textContent?.trim()).toBe(BADGE_INACTIVE);
        expectNoVerificationBadge(row);
        expect(within(row).getByTestId('users-badge-inactive'), 'no hover hint on «Deactivated»').not.toHaveAttribute('title', HINT_PENDING_VERIFICATION);
        // The barrier of the absence: the panel is open, and offers «Reactivate».
        expect(within(panel).getByTestId('users-action-reactivate')).toBeInTheDocument();
        expect(within(panel).queryByTestId('users-pending-verification-hint'), 'the verification hint').toBeNull();
        expect(within(panel).queryByText(HINT_PENDING_VERIFICATION)).toBeNull();
    });

    // red until E-7
    it.each(WAITING)('UVR-07: $label — opened, the panel shows the hint, and still offers «Reactivate»', async ({account}) => {
        const {panel} = await openRow(account);

        expect(within(panel).getByTestId('users-pending-verification-hint').textContent?.trim()).toBe(HINT_PENDING_VERIFICATION);
        expect(within(panel).getByTestId('users-action-reactivate')).toBeInTheDocument();
        expect(within(panel).queryByTestId('users-pending-setup-hint'), 'the setup hint').toBeNull();
    });

    // red until E-7: the hint is the barrier that proves the row is drawn as waiting
    it.each([
        ['a live link on a full instance', makeAccount({is_active: false, pending_verification: true, holds_place: true}), true],
        ['a live link with room left', makeAccount({is_active: false, pending_verification: true, holds_place: true}), false],
        ['an expired link with room left', makeAccount({is_active: false, pending_verification: true, holds_place: false}), false],
    ])('UVR-08: waiting with %s — «Reactivate» is usable, no limit reason, and the click asks for it', async (_label, account, full) => {
        const {panel, onAction} = await openRow(account, full);

        expect(within(panel).getByTestId('users-pending-verification-hint')).toBeInTheDocument();
        const reactivate = within(panel).getByTestId('users-action-reactivate');
        expect(reactivate).toBeEnabled();
        expect(reactivate).not.toHaveAttribute('data-disabled-reason');
        expect(within(panel).queryByText('settings.usersTab.reasons.limit')).toBeNull();
        await fireEvent.click(reactivate);
        expect(onAction).toHaveBeenCalledWith('reactivate', account);
    });

    // red until E-7: the hint is the barrier that proves the row is drawn as waiting
    it('UVR-09: waiting with an expired link on a full instance — «Reactivate» is turned off with the limit reason', async () => {
        const {panel} = await openRow(makeAccount({is_active: false, pending_verification: true, holds_place: false}), true);

        expect(within(panel).getByTestId('users-pending-verification-hint')).toBeInTheDocument();
        const reactivate = within(panel).getByTestId('users-action-reactivate');
        expect(reactivate).toBeDisabled();
        expect(reactivate).toHaveAttribute('data-disabled-reason', 'limit');
        expect(within(panel).getByText('settings.usersTab.reasons.limit')).toBeInTheDocument();
    });

    // red until E-7: data-pending-verification is the derived state, so it reads "false" when the setup wins
    it('UVR-10: pending_setup wins — the setup badge and hint, no verification badge or hint, no «Deactivated», data-pending-verification="false"', async () => {
        const account = makeAccount({is_active: false, pending_setup: true, pending_verification: true});
        const {row, panel} = await openRow(account);

        expect(within(row).getByTestId('users-badge-pending-setup').textContent?.trim()).toBe(BADGE_PENDING_SETUP);
        expect(within(panel).getByTestId('users-pending-setup-hint').textContent?.trim()).toBe(HINT_PENDING_SETUP);
        expectNoVerificationBadge(row);
        expectNoInactiveBadge(row);
        expect(within(panel).queryByTestId('users-pending-verification-hint'), 'the verification hint').toBeNull();
        expect(within(panel).queryByText(HINT_PENDING_VERIFICATION)).toBeNull();
        expect(row).toHaveAttribute('data-pending-setup', 'true');
        expect(row).toHaveAttribute('data-pending-verification', 'false');
    });

    // red until E-7
    it('UVR-11: an active account with pending_verification true — the row does not lie: no badge, no hint, "false"', async () => {
        const {row, panel} = await openRow(makeAccount({is_active: true, pending_verification: true}));

        expectNoVerificationBadge(row);
        expectNoInactiveBadge(row);
        expect(row).toHaveAttribute('data-pending-verification', 'false');
        // The barrier of the absence: the panel is open, and offers «Deactivate».
        expect(within(panel).getByTestId('users-action-deactivate')).toBeInTheDocument();
        expect(within(panel).queryByTestId('users-pending-verification-hint'), 'the verification hint').toBeNull();
        expect(within(panel).queryByText(HINT_PENDING_VERIFICATION)).toBeNull();
    });
});
