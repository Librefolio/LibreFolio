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
 * Accounts lot A-43 (release 1.3, workstream A — the coordinator's contract of 17/10, 10:36) lets the administrators
 * cancel that account's setup link. `PATCH /users/{id}` with `{is_active: false}` on it — inactive already — revokes its
 * link and leaves it waiting (the answer: its row, `pending_setup: true`); its demotion is refused with 409
 * `PENDING_SETUP` (what the tab does with both: `UsersTab.test.ts`, UTAB-55…60). The contract under test, for an account
 * with `pending_setup: true` that is not one's own:
 *   - opened, the action `users-action-cancel-setup`, enabled, room left or not, which hands the account to
 *     `onAction('cancel-setup', account)`. It wears the classes of the row's other actions: a sameness, so the case names
 *     no class; that those classes are roles, without a palette class or a `dark:`, is the colour gates' —
 *     `UserRow.svelte` has no line in `themeRoles.baseline.tsv`, so it must stay clean;
 *   - «Demote» turned off, `data-disabled-reason="pending-setup"`, and that reason in the panel as the key
 *     `settings.usersTab.reasons.pendingSetup`;
 *   - and so «Delete» on, with no reason, and no `settings.usersTab.reasons.demoteFirst` in the panel: it cannot be
 *     demoted, so it is deleted directly (the coordinator's decision of 17/10, 11:42);
 *   - still neither «Deactivate» nor «Reactivate», and still the hint (UPS-03, UPS-04);
 *   - the new reason and the action's label are sentences in the four catalogues; the label is read from the row, as the
 *     contract names no key for it.
 * The guards, green today: no waiting account offers «Deactivate» or «Reactivate»; an account that waits for nothing
 * offers no cancellation, and an administrator that waits for nothing keeps «Demote» on and «Delete» off with
 * `demote-first`, its reason shown — the positive control of the deletion above.
 *
 * After A-43's review (the coordinator's decision of 17/10): the waiting administrator the hook of lot A7 protects
 * refuses the cancellation — `PATCH {is_active: false}` on it is 409 `ACCOUNT_PROTECTED`, nothing changed (UADM-079) —,
 * so for an account with `pending_setup: true` and `protected: true`, room left or not:
 *   - opened, `users-action-cancel-setup` is still drawn, turned off, `data-disabled-reason="protected"`, and that
 *     reason in the panel as the key `settings.usersTab.reasons.protected`, as for a protected account's «Deactivate»;
 *   - a user's click on it hands nothing to `onAction`. That click is `HTMLElement.click()`, which a disabled control
 *     refuses as a browser does: in jsdom `fireEvent.click` reaches a disabled button, and Svelte 5's delegated handler
 *     fires, which no browser allows (devWiki, `domains/email.md`, «jsdom is not a browser»). The barrier of that
 *     absence: the same click on an action of the panel that is on, «Reset link», does reach `onAction`.
 * Its guards are UPS-12 and UPS-13: the waiting administrator nobody protects keeps the action on, with no reason, and
 * its click hands the account over.
 *
 * Mocks, as `UserRow.verification.test.ts`: the identity translator (a message renders as its key) and `formatDateTime`
 * (the row's date is not the subject). What runs for real: the row. Never a class or a colour, but for the sameness of
 * UPS-14: the badge reuses the tab's neutral style, and the colour gates watch it. A7b's cases click no control but the
 * row's toggle; A-43's click `users-action-cancel-setup`, and read the `onAction` spy `mount` hands back.
 *
 * Red until A7b, every case marked so. The fixtures carry `pending_setup`, which `AdminAccount` (`./types.ts`) gains in
 * A7b — optional, as `holds_place` —: until then this file is red at the type check too. Red until A-43, likewise, every
 * case it adds; and UPS-23, added after its review, until the fix: today the action has no disabled state.
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

/** The waiting administrator, room left and full: only an administrator is offered «Demote». */
const PENDING_ADMIN_BY_ROOM = PENDING_BY_ROOM.filter(({account}) => account.is_superuser);

/** The same administrator, protected by the hook of lot A7: its setup link cannot be cancelled, 409 `ACCOUNT_PROTECTED` (UADM-079). */
const PENDING_PROTECTED = makeAccount(13, 'zq_f02_protected', {is_active: false, is_superuser: true, holds_place: false, pending_setup: true, protected: true});

/** That account with room left and on a full instance: its panel is the same either way. */
const PENDING_PROTECTED_BY_ROOM = [{label: 'the initial administrator the hook protects', account: PENDING_PROTECTED}].flatMap((scene) => [
    {...scene, room: 'room left', full: false},
    {...scene, room: 'a full instance', full: true},
]);

/** Every other row, one's own excepted: one's own panel offers no action at all (`UsersTab.test.ts`, UTAB-21). */
const NOT_PENDING_OTHERS = NOT_PENDING.filter(({isSelf}) => !isSelf);

/** The administrators that wait for nothing, as another administrator sees them. */
const ADMINS_NOT_PENDING = [
    {label: 'another active administrator', account: ACTIVE_ADMIN},
    {label: 'an inactive administrator whose setup link was spent', account: DORMANT_ADMIN},
];

// --- DOM helpers ----------------------------------------------------------

interface Mounted {
    row: HTMLElement;
    toggle: HTMLElement;
    /** The row's `onAction`: the subject of A-43's click only. */
    onAction: ReturnType<typeof vi.fn>;
}

/** Mount one row. A7b's cases click nothing but its toggle; A-43's click one action, and read `onAction`. */
function mount(account: AdminAccount, {full = false, isSelf = false}: {full?: boolean; isSelf?: boolean} = {}): Mounted {
    const onAction = vi.fn();
    render(UserRow, {props: {account, isSelf, isOnlyActiveAdmin: false, full, onAction}});
    const row = screen.getByTestId('users-row');
    return {row, toggle: within(row).getByTestId('users-row-toggle'), onAction};
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

/** On, and carrying no reason to be off. */
function expectEnabled(control: HTMLElement): void {
    expect(control).toBeEnabled();
    expect(control.getAttribute('data-disabled-reason') || null, 'an enabled control carries no reason').toBeNull();
}

/** The classes an element wears, sorted: two controls styled alike wear the same list. Read by UPS-14 only. */
const classesOf = (element: Element): string => [...element.classList].sort().join(' ');

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
describe('UserRow — cancelling the setup link of the waiting administrator (A-43)', () => {
    // red until A-43
    it.each(PENDING_BY_ROOM)('UPS-12: $label, $room — opened, users-action-cancel-setup, enabled', async ({account, full}) => {
        const panel = await openPanel(mount(account, {full}));

        expectEnabled(within(panel).getByTestId('users-action-cancel-setup'));
    });

    // red until A-43
    it.each(PENDING)('UPS-13: $label — clicking it hands the account to onAction as cancel-setup, once', async ({account}) => {
        const mounted = mount(account);
        const panel = await openPanel(mounted);

        await fireEvent.click(within(panel).getByTestId('users-action-cancel-setup'));

        expect(mounted.onAction).toHaveBeenCalledTimes(1);
        expect(mounted.onAction).toHaveBeenCalledWith('cancel-setup', account);
    });

    // red until A-43 — a feature assertion of the contract («styled like the other row actions»): a sameness, never a colour
    it.each(PENDING)('UPS-14: $label — it wears the classes of one of the row’s other actions, and no dark: variant', async ({account}) => {
        const panel = await openPanel(mount(account));
        const cancel = within(panel).getByTestId('users-action-cancel-setup');

        const others = [...actionsIn(panel)].filter((action) => action !== cancel).map(classesOf);
        expect(others.length, 'the other actions of the panel').toBeGreaterThan(0);
        expect(others, 'the classes of an action the row already draws').toContain(classesOf(cancel));
        expect(
            [...cancel.classList].filter((name) => name.split(':').includes('dark')),
            'a dark: variant',
        ).toEqual([]);
    });

    // red until A-43
    it.each(PENDING_ADMIN_BY_ROOM)('UPS-15: $label, $room — «Demote» turned off with the reason pending-setup, shown as settings.usersTab.reasons.pendingSetup', async ({account, full}) => {
        const panel = await openPanel(mount(account, {full}));

        const demote = within(panel).getByTestId('users-action-demote');
        expect(demote).toBeDisabled();
        expect(demote).toHaveAttribute('data-disabled-reason', 'pending-setup');
        expect(within(panel).getByText('settings.usersTab.reasons.pendingSetup')).toBeInTheDocument();
    });

    // guard — as before A-43: the cancellation is an action of its own, not a «Deactivate» drawn for an inactive account
    it.each(PENDING_BY_ROOM)('UPS-16: $label, $room — neither users-action-deactivate nor users-action-reactivate', async ({account, full}) => {
        const panel = await openPanel(mount(account, {full}));

        expect(actionsIn(panel).length, 'the actions the panel still offers').toBeGreaterThan(0);
        expect(within(panel).queryByTestId('users-action-deactivate')).toBeNull();
        expect(within(panel).queryByTestId('users-action-reactivate')).toBeNull();
    });

    // red until A-43's fix after its review (UADM-079): the action has no disabled state today. Its guards are UPS-12 and
    // UPS-13: the waiting administrator nobody protects keeps it on, with no reason, and its click hands the account over.
    it.each(PENDING_PROTECTED_BY_ROOM)('UPS-23: $label, $room — users-action-cancel-setup turned off with the reason protected, shown as settings.usersTab.reasons.protected, and a click hands nothing over', async ({account, full}) => {
        const mounted = mount(account, {full});
        const panel = await openPanel(mounted);

        const cancel = within(panel).getByTestId('users-action-cancel-setup');
        expect(cancel).toBeDisabled();
        expect(cancel).toHaveAttribute('data-disabled-reason', 'protected');
        expect(within(panel).getByText('settings.usersTab.reasons.protected')).toBeInTheDocument();

        // A user's click is `HTMLElement.click()`, which a disabled control refuses as a browser does; never
        // `fireEvent.click` here: in jsdom it reaches a disabled button, and Svelte 5's delegated handler fires.
        // The barrier first: the same click on an action of the panel that is on reaches onAction.
        // (A5-1: a protected account's reset link and sign-out are off too, so the barrier is the restart of its guides)
        within(panel).getByTestId('users-action-restart-guides').click();
        expect(mounted.onAction).toHaveBeenCalledTimes(1);
        expect(mounted.onAction).toHaveBeenCalledWith('restart-guides', account);

        cancel.click();
        expect(mounted.onAction, 'only the barrier’s call: the cancellation handed nothing over').toHaveBeenCalledTimes(1);
        expect(mounted.onAction).not.toHaveBeenCalledWith('cancel-setup', expect.anything());
    });
});

// =========================================================================
describe('UserRow — deleting the waiting administrator directly, without a demotion (A-43)', () => {
    // red until A-43 — it cannot be demoted (UPS-15), so «Delete» no longer waits for a demotion
    it.each(PENDING_ADMIN_BY_ROOM)('UPS-21: $label, $room — users-action-delete enabled, and no demote-first reason', async ({account, full}) => {
        const mounted = mount(account, {full});
        const panel = await openPanel(mounted);

        // The barrier of the two absences below: the panel drew «Delete», and with it its reasons.
        expectEnabled(within(panel).getByTestId('users-action-delete'));
        expect(within(panel).queryByText('settings.usersTab.reasons.demoteFirst'), 'the demote-first reason').toBeNull();
        expect(mounted.row.querySelectorAll('[data-disabled-reason="demote-first"]'), 'a control turned off for demote-first').toHaveLength(0);
    });
});

// =========================================================================
describe('UserRow — every account that waits for nothing, as before A-43', () => {
    // guard
    it.each(NOT_PENDING_OTHERS)('UPS-17: $label — no users-action-cancel-setup', async ({account}) => {
        const panel = await openPanel(mount(account));

        expect(actionsIn(panel).length, 'the actions the panel offers').toBeGreaterThan(0);
        expect(within(panel).queryByTestId('users-action-cancel-setup')).toBeNull();
    });

    // guard
    it.each(ADMINS_NOT_PENDING)('UPS-18: $label — «Demote» on, and no pending-setup reason', async ({account}) => {
        const panel = await openPanel(mount(account));

        expectEnabled(within(panel).getByTestId('users-action-demote'));
        expect(within(panel).queryByText('settings.usersTab.reasons.pendingSetup')).toBeNull();
    });

    // guard — the positive control of UPS-21: an administrator that waits for nothing is demoted before it is deleted
    it.each(ADMINS_NOT_PENDING)('UPS-22: $label — «Delete» turned off with demote-first, and its reason shown, as before', async ({account}) => {
        const panel = await openPanel(mount(account));

        const deletion = within(panel).getByTestId('users-action-delete');
        expect(deletion).toBeDisabled();
        expect(deletion).toHaveAttribute('data-disabled-reason', 'demote-first');
        expect(within(panel).getByText('settings.usersTab.reasons.demoteFirst')).toBeInTheDocument();
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

    describe('the keys A-43 adds', () => {
        // red until A-43
        it('UPS-19: settings.usersTab.reasons.pendingSetup is a sentence in the four catalogues, or the row shows the key', () => {
            expect(missingIn('settings.usersTab.reasons.pendingSetup'), 'the catalogues without it').toEqual([]);
        });

        // red until A-43 — the contract names no key for the label: the one the row asks for, read through the identity translator
        it('UPS-20: the label of users-action-cancel-setup is a sentence in the four catalogues', async () => {
            const panel = await openPanel(mount(PENDING_ADMIN));
            const label = within(panel).getByTestId('users-action-cancel-setup').textContent?.trim() ?? '';

            expect(label, 'the action has a label').not.toBe('');
            expect(missingIn(label), `the catalogues without ${label}`).toEqual([]);
        });
    });
});
