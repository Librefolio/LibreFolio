// @vitest-environment jsdom
/**
 * UserRow and the initial administrator waiting for its setup link (accounts lot A7b, contract C5 — plan-phase01Accounts
 * «A7b — Analisi e contratto», its «Scelte di dettaglio» and the coordinator's decisions of 21:10).
 *
 * F02 (lot A7a) creates the administrator of LIBREFOLIO_ADMIN_EMAIL at the first start: a row of `users`, inactive, an
 * administrator, its password a secret nobody knows, waiting for its setup link (`/setup#token=…`). Until A7b the Users
 * tab draws it as any deactivated account — the «inactive» badge, and «Reactivate» in its panel —, and reactivating it
 * would leave an active account whose password nobody knows, and whose setup link `POST /auth/setup` then refuses. The
 * backend of A7b names that account, `AdminUserRead.pending_setup` (inactive, with an `admin_setup` token and none of
 * them consumed — live, expired or revoked alike, an administrator or not: `pending_admin_filter()`), and refuses
 * `PATCH {is_active: true}` on it with 409 `PENDING_SETUP` (UADM-060…065, `test_users_admin_api.py`; how the tab words
 * that refusal is pinned in `accountErrors.test.ts`).
 *
 * The contract under test, for an account with `pending_setup: true`:
 *   - in the list, the badge `users-badge-pending-setup` (key `settings.usersTab.badges.pendingSetup`) in place of the
 *     inactive one (`settings.usersTab.badges.inactive`, which has no test id: asserted absent by its key);
 *   - the row publishes `data-pending-setup="true"`, and every other row `"false"` — `pending_setup` absent (an older
 *     server) included;
 *   - opened: no `users-action-reactivate`, and in its place the hint `users-pending-setup-hint` (key
 *     `settings.usersTab.pendingSetupHint`: the account is activated by its setup link). The other actions are those
 *     of any inactive account; which ones is not this file's subject — only that some remain, the barrier that keeps
 *     the absence of «Reactivate» from passing on an empty panel;
 *   - on a full instance its reasons do not carry the `limit` one: there is nothing to reactivate;
 *   - the two new keys are sentences in the four catalogues (C6): the identity translator below renders a missing key
 *     as itself, so without that block a forgotten translation would pass here.
 * Two such accounts: the one the bootstrap leaves (an administrator, `holds_place` false — its place is counted by
 * another rule), and the same account demoted while it waits — a change this tab itself offers, after which it still
 * waits (UADM-062) and the backend still refuses to activate it (UADM-065, «an administrator or not»).
 *
 * The guards, green today: an inactive account that waits for nothing — `pending_setup` false or absent, an
 * administrator whose setup link was spent among them (UADM-063, 066) — keeps the inactive badge, «Reactivate» and, on a
 * full instance, the `limit` reason (the positive control of the absence above); an active account, one's own
 * included, shows neither the badge nor the hint.
 *
 * Mocks, as `UserRow.verification.test.ts`: the identity translator (a message renders as its key) and `formatDateTime`
 * (the row's date is not the subject). What runs for real: the row. Never a class or a colour: the badge reuses the
 * tab's neutral style, and the colour gates watch it. No control is clicked, only the row's toggle.
 *
 * Red until A7b, every case marked so. The fixtures carry `pending_setup`, which `AdminAccount` (`./types.ts`) gains in
 * A7b — optional, as `holds_place` —: until then this file is red at the type check too.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/utils/core/formatDateTime', () => ({formatDateTime: () => '2026-10-16'}));

import UserRow from './UserRow.svelte';
import type {AdminAccount} from './types';
// The real catalogues, read only by the last block: the rows render through the identity translator above.
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

// --- Fixtures -------------------------------------------------------------

/** An account as `GET /users` lists it. `pending_setup` only when given: without it, the answer of an older server. */
function makeAccount(id: number, username: string, flags: Partial<AdminAccount>): AdminAccount {
    return {id, username, email: `${username}@example.com`, is_active: true, is_superuser: false, created_at: '2026-10-16T00:00:00Z', protected: false, ...flags};
}

/** The administrator of LIBREFOLIO_ADMIN_EMAIL as the bootstrap leaves it: inactive, an administrator, its place counted by another rule. */
const PENDING_ADMIN = makeAccount(11, 'zq_f02_admin', {is_active: false, is_superuser: true, holds_place: false, pending_setup: true});
/** The same account demoted while it waits: it still waits (UADM-062), and the backend still refuses to activate it. */
const PENDING_DEMOTED = makeAccount(12, 'zq_f02_demoted', {is_active: false, is_superuser: false, holds_place: false, pending_setup: true});

const PENDING = [
    {label: 'the initial administrator, as the bootstrap leaves it', account: PENDING_ADMIN},
    {label: 'the same account, demoted while it waits', account: PENDING_DEMOTED},
];

/** Each waiting account with room left and on a full instance: its panel is the same either way. */
const PENDING_BY_ROOM = PENDING.flatMap((scene) => [
    {...scene, room: 'room left', full: false},
    {...scene, room: 'a full instance', full: true},
]);

/** An administrator deactivated after its setup: its setup link was spent, its password is known — it waits for nothing. */
const DORMANT_ADMIN = makeAccount(23, 'zq_dormant_admin', {is_active: false, is_superuser: true, pending_setup: false});

const INACTIVE_NOT_PENDING = [
    {label: 'an inactive member, pending_setup false', account: makeAccount(21, 'zq_dormant', {is_active: false, pending_setup: false})},
    {label: 'an inactive member, pending_setup absent (an older server)', account: makeAccount(22, 'zq_dormant_old', {is_active: false})},
    {label: 'an inactive administrator whose setup link was spent', account: DORMANT_ADMIN},
];

const ACTIVE_ADMIN = makeAccount(33, 'zq_admin', {is_superuser: true, pending_setup: false});

const ACTIVE = [
    {label: 'an active member, pending_setup false', account: makeAccount(31, 'zq_member', {pending_setup: false}), isSelf: false},
    {label: 'an active member, pending_setup absent (an older server)', account: makeAccount(32, 'zq_member_old', {}), isSelf: false},
    {label: 'another active administrator', account: ACTIVE_ADMIN, isSelf: false},
    {label: 'one’s own account', account: ACTIVE_ADMIN, isSelf: true},
];

/** Every row but a waiting account's. */
const NOT_PENDING = [...INACTIVE_NOT_PENDING.map((scene) => ({...scene, isSelf: false})), ...ACTIVE];

// --- DOM helpers ----------------------------------------------------------

interface Mounted {
    row: HTMLElement;
    toggle: HTMLElement;
}

/** Mount one row. Nothing here is clicked but its toggle, so `onAction` is never the subject. */
function mount(account: AdminAccount, {full = false, isSelf = false}: {full?: boolean; isSelf?: boolean} = {}): Mounted {
    render(UserRow, {props: {account, isSelf, isOnlyActiveAdmin: false, full, onAction: vi.fn()}});
    const row = screen.getByTestId('users-row');
    return {row, toggle: within(row).getByTestId('users-row-toggle')};
}

/** Open the row's panel and hand it back. Rule 14: ask for the state first; the panel is the element the toggle controls. */
async function openPanel({toggle}: Mounted): Promise<HTMLElement> {
    if (toggle.getAttribute('aria-expanded') !== 'true') await fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const panelId = toggle.getAttribute('aria-controls');
    const panel = panelId === null ? null : document.getElementById(panelId);
    if (panel === null) throw new Error(`users-row-toggle controls #${panelId}, which is not in the document: the panel did not open`);
    return panel;
}

/** The actions a panel offers, whichever they are. */
const actionsIn = (panel: HTMLElement) => panel.querySelectorAll('[data-testid^="users-action-"]');

afterEach(() => {
    cleanup();
});

// =========================================================================
describe('UserRow — the initial administrator waiting for its setup link (A7b, C5)', () => {
    // red until A7b
    it.each(PENDING)('UPS-01: $label — in the list, the badge users-badge-pending-setup in place of the inactive one', ({account}) => {
        const {row, toggle} = mount(account);

        // Seen in the list, without opening the row: where «Deactivated» stood.
        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        expect(within(row).getByTestId('users-badge-pending-setup')).toHaveTextContent('settings.usersTab.badges.pendingSetup');
        expect(row, 'the inactive badge').not.toHaveTextContent('settings.usersTab.badges.inactive');
    });

    // red until A7b
    it.each(PENDING)('UPS-02: $label — the row publishes data-pending-setup="true"', ({account}) => {
        const {row} = mount(account);

        expect(row).toHaveAttribute('data-pending-setup', 'true');
    });

    // red until A7b
    it.each(PENDING_BY_ROOM)('UPS-03: $label, $room — opened, no users-action-reactivate', async ({account, full}) => {
        const mounted = mount(account, {full});
        const panel = await openPanel(mounted);

        // The barrier: the panel drew its other actions — those of any inactive account, not this file's subject.
        expect(actionsIn(panel).length, 'the actions the panel still offers').toBeGreaterThan(0);
        expect(within(mounted.row).queryByTestId('users-action-reactivate')).toBeNull();
    });

    // red until A7b
    it.each(PENDING_BY_ROOM)('UPS-04: $label, $room — opened, the hint users-pending-setup-hint in its place', async ({account, full}) => {
        const panel = await openPanel(mount(account, {full}));

        expect(within(panel).getByTestId('users-pending-setup-hint')).toHaveTextContent('settings.usersTab.pendingSetupHint');
    });

    // red until A7b
    it.each(PENDING)('UPS-05: $label on a full instance — no limit reason: there is nothing to reactivate', async ({account}) => {
        const mounted = mount(account, {full: true});
        const panel = await openPanel(mounted);

        expect(actionsIn(panel).length, 'the actions the panel still offers').toBeGreaterThan(0);
        expect(mounted.row, 'the limit reason').not.toHaveTextContent('settings.usersTab.reasons.limit');
        expect(mounted.row.querySelectorAll('[data-disabled-reason="limit"]'), 'a control turned off for the limit').toHaveLength(0);
    });
});

// =========================================================================
describe('UserRow — data-pending-setup on every other row (A7b, C5)', () => {
    // red until A7b
    it.each(NOT_PENDING)('UPS-06: $label — data-pending-setup="false"', ({account, isSelf}) => {
        const {row} = mount(account, {isSelf});

        expect(row).toHaveAttribute('data-pending-setup', 'false');
    });
});

// =========================================================================
describe('UserRow — every other account, as before A7b', () => {
    // guard
    it.each(INACTIVE_NOT_PENDING)('UPS-07: $label — the inactive badge and «Reactivate», neither the badge nor the hint of a pending setup', async ({account}) => {
        const mounted = mount(account);

        expect(within(mounted.row).getByText('settings.usersTab.badges.inactive')).toBeInTheDocument();
        expect(within(mounted.row).queryByTestId('users-badge-pending-setup')).toBeNull();

        const panel = await openPanel(mounted);
        expect(within(panel).getByTestId('users-action-reactivate')).toBeInTheDocument();
        expect(within(mounted.row).queryByTestId('users-pending-setup-hint')).toBeNull();
    });

    // guard — the positive control of UPS-05: on the same full instance, an account that waits for nothing has its limit reason
    it.each(INACTIVE_NOT_PENDING)('UPS-08: $label on a full instance — «Reactivate» turned off with the limit reason, as before', async ({account}) => {
        const panel = await openPanel(mount(account, {full: true}));

        const reactivate = within(panel).getByTestId('users-action-reactivate');
        expect(reactivate).toBeDisabled();
        expect(reactivate).toHaveAttribute('data-disabled-reason', 'limit');
        expect(within(panel).getByText('settings.usersTab.reasons.limit')).toBeInTheDocument();
    });

    // guard
    it.each(ACTIVE)('UPS-09: $label — neither the badge nor the hint of a pending setup, closed or opened', async ({account, isSelf}) => {
        const mounted = mount(account, {isSelf});

        expect(mounted.row, 'the row drew this account').toHaveAttribute('data-username', account.username);
        expect(within(mounted.row).queryByTestId('users-badge-pending-setup')).toBeNull();
        expect(mounted.row, 'the inactive badge').not.toHaveTextContent('settings.usersTab.badges.inactive');

        await openPanel(mounted);
        expect(within(mounted.row).queryByTestId('users-pending-setup-hint')).toBeNull();
        expect(within(mounted.row).queryByTestId('users-badge-pending-setup')).toBeNull();
    });
});

// =========================================================================
describe('UserRow — its keys are sentences in the four catalogues (A7b, C6)', () => {
    const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

    /** The leaf at a dotted key, read from the catalogue itself. */
    function leafOf(catalogue: unknown, key: string): unknown {
        let node = catalogue;
        for (const part of key.split('.')) node = node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined;
        return node;
    }

    /** The languages whose catalogue has no sentence at `key`. */
    function missingIn(key: string): string[] {
        return Object.keys(CATALOGUES).filter((language) => {
            const message = leafOf(CATALOGUES[language], key);
            return typeof message !== 'string' || message.trim() === '';
        });
    }

    // guard — the reader's positive control: keys the row renders today are found in all four
    it.each(['settings.usersTab.badges.inactive', 'settings.usersTab.reasons.limit'])('UPS-10: %s, rendered today, is a sentence in the four catalogues', (key) => {
        expect(missingIn(key), 'the catalogues without it').toEqual([]);
    });

    // red until A7b
    it.each(['settings.usersTab.badges.pendingSetup', 'settings.usersTab.pendingSetupHint'])('UPS-11: %s is a sentence in the four catalogues, or the row shows the key', (key) => {
        expect(missingIn(key), 'the catalogues without it').toEqual([]);
    });
});
