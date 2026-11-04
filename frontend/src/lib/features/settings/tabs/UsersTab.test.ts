// @vitest-environment jsdom
/**
 * UsersTab — component test (Vitest + jsdom). Accounts lot A6b (plan-phase01Accounts «A6b.1»), cases UTAB-01…UTAB-54.
 *
 * The administrators' «Users» tab of Settings: every account of the instance with the actions an administrator may
 * take on it, the live invitations, and the places taken against the limit of the instance. It takes no props; what
 * decides its behaviour is the answer of `GET /users` and `GET /users/invites`, the registration mode of
 * `GET /system/instance` (`instanceConfig`) and who is signed in (`currentUser`) — all controllable from here.
 *
 * RED TODAY, by construction: `./UsersTab.svelte` does not exist yet, so the import below fails and the whole file
 * fails to collect. Every case is written against the A6b.1 contract, not against an implementation.
 *
 * Why a component test and not an E2E. Most of what this tab decides is a *rule*, and the rules live in states a live
 * instance cannot reach on cue: a protected account exists only on a managed instance; a full instance needs
 * LIBREFOLIO_MAX_USERS; the «last active administrator» guard never shows on a real session, because whoever reads
 * the tab is an active administrator too (the `last-admin` cases explain their fixture); and a 409 or a 404 needs a
 * server that refuses at the right moment. Here each one is a fixture line. `e2e/settings/admin-users.spec.ts` walks
 * the real flows on disposable accounts.
 *
 * The mocked server. `GET /users` and `GET /users/invites` answer from `server`, and the writes change it the way the
 * backend would: a PATCH merges its body, a DELETE removes, a call about an account that is gone answers 404 with the
 * backend's own body. So «the tab reloads after an action» is asserted twice: the list is asked again (a delta on its
 * calls, sampled before acting — rule 16), *and* the new answer is what the screen shows.
 *
 * Selectors are the contract's test ids and data attributes, never a translated string and never a class:
 * `$lib/i18n` is an identity translator. Events are read from the `notify` mock by `name` and `detail`; the toast is
 * asserted as the `toast` field of that same call — its variant, never its message (one notification, two halves).
 * The confirmation is the real `ConfirmModal` (`testId="users-confirm"` sits on its header; its buttons are
 * `confirm-modal-confirm` / `confirm-modal-cancel`).
 *
 * What it deliberately does NOT assert:
 *   - the dialogs' insides. `InviteDialog`, `ResetLinkDialog`, `LinkShare` and `AccountDeletionDialog` have their own
 *     lanes; here they are opened only far enough to prove the tab wires them — open, for the right account, closed
 *     and reloaded after.
 *   - what the tab does with «Deactivate instead» (`users-delete-deactivate`), and who emits `accounts.user.deleted`
 *     (the tab or the dialog): the contract pins neither.
 *   - wording: the «N / max» text, the hint naming LIBREFOLIO_REGISTRATION, the dates.
 *   - colours: the `lf-*` roles have gates of their own.
 *
 * Accounts lot A-43 (release 1.3, workstream A — the coordinator's contract of 17/10, 10:36, and its decisions of 11:42),
 * cases UTAB-55…UTAB-60: cancelling the setup link of the administrator waiting for it (F02, `pending_setup: true`; its
 * row: `UserRow.pendingSetup.test.ts`). `users-action-cancel-setup` asks first, with the keys
 * `settings.usersTab.confirm.cancelSetup.title|message|confirm`, as a danger: the link handed over stops working.
 * Confirmed, one `PATCH /users/{id}` `{is_active: false}` — on a waiting administrator the backend revokes its link and
 * keeps it waiting — and no other write; the row is the answer, still waiting; the event is
 * `accounts.user.setup-cancelled`, with a success toast — the link stops working out of sight —, the key
 * `settings.usersTab.toasts.setupCancelled` given the username. Cancelled, nothing. The backend refuses to demote it with
 * 409 `PENDING_SETUP`: a row drawn before the server said it waits still offers «Demote», and the toast takes the wording
 * `accountErrors.ts` gives that code since A7b (UTAB-58, a guard: green today). The keys of the confirmation and of the
 * toast are sentences in the four catalogues, naming no value but the username. Four things the rest of this file leaves
 * alone are read there, each the subject of its case: the confirmation's danger, as `btn-danger` (ConfirmModal publishes
 * its variant only as that class, and `GlobalSettingsTab.test.ts` reads its amber one so); a toast's message, which
 * through the identity translator is the key the tab chose; the values that key was given, from the translator's own
 * calls (the identity translator is a spy for this alone); and the real catalogues. Red until A-43, every case marked
 * so; the two guards (UTAB-58, UTAB-59, the catalogue reader's positive control) are green today.
 *
 * Accounts lot A-51 (release 1.3, workstream A — the coordinator's OK of 17/10, 14:52), cases UTAB-61…UTAB-62. The
 * cancellation sent the body of a deactivation, `{is_active: false}`, so the backend could not tell one from the other:
 * when the waiting administrator completed its setup while the tab still drew it waiting, a click minutes later
 * deactivated the new administrator, and the toast said its link was cancelled. Since A-51 the request carries its
 * intent: confirmed, the cancellation sends exactly `{is_active: false, cancel_setup: true}` to that account (UTAB-61;
 * UTAB-56 keeps the rest of that flow and, since A-51, pins only `is_active: false`). A setup completed meanwhile
 * answers 409 `SETUP_COMPLETED`, and the tab says so with the wording `accountErrors.ts` gives that code — the key
 * `settings.usersTab.errors.SETUP_COMPLETED`, a sentence in the four catalogues (`accountErrors.test.ts`) —, announces
 * no success, and reloads onto the account as the server has it: active, waiting for nothing (UTAB-62). A deactivation
 * keeps its plain body: UTAB-32 pins `{is_active: false}` with `toEqual`, which a defined `cancel_setup` turns red — the
 * guard, green today. The mocked server stores no `cancel_setup`: it says why `is_active: false` is asked, it is not a
 * column. Red until A-51, both cases.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {get, readable, writable} from 'svelte/store';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

// --- Mocks --------------------------------------------------------------

vi.mock('$lib/i18n', () => {
    // An identity translator: a label renders as its own key, so nothing below can lean on a phrase. The object form
    // (`$_({id, values})`) answers its id, so no call shape can turn a label into a crash. A spy since A-43, its answers
    // unchanged: the values a message was given, which the identity drops, are read from its calls (`translator()`).
    const identity = readable(vi.fn((input: unknown) => (typeof input === 'string' ? input : String((input as {id?: unknown} | null)?.id ?? ''))));
    return {
        _: identity,
        t: identity,
        locale: writable('en'),
        date: readable((v: unknown) => String(v)),
        time: readable((v: unknown) => String(v)),
        number: readable((v: unknown) => String(v)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

// Replaced whole, every export: the dates of the rows go through `uiLocaleStore`, derived from `currentLanguage`.
vi.mock('$lib/stores/app/language', () => ({
    currentLanguage: writable('en'),
    currentLanguageName: readable('English'),
    currentLanguageFlag: readable('EN'),
    availableLanguages: [{code: 'en', name: 'English', flag: 'EN'}],
}));

vi.mock('$lib/api', () => {
    const cache = new Map<string, unknown>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

const notify = vi.fn();
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: (...args: unknown[]) => notify(...args)}));

/**
 * Who is signed in, with the real store's shape: `auth` is a store of `{user, isLoading, error, isInitialized}` and
 * `currentUser` derives the user. Built in `vi.hoisted` because the factory hands the stores out as they are.
 */
const session = await vi.hoisted(async () => {
    const store = await import('svelte/store');
    type SessionUser = {id: number; username: string; email: string; is_active: boolean; is_superuser: boolean; created_at: string};
    const state = store.writable<{user: SessionUser | null; isLoading: boolean; error: null; isInitialized: boolean}>({user: null, isLoading: false, error: null, isInitialized: true});
    return {
        state,
        currentUser: store.derived(state, (now) => now.user),
        isAuthenticated: store.derived(state, (now) => now.user !== null),
        isAuthLoading: store.derived(state, (now) => now.isLoading),
        authError: store.derived(state, (now) => now.error),
        isAuthInitialized: store.derived(state, (now) => now.isInitialized),
        snapshot: () => store.get(state),
        signIn: (user: SessionUser) => state.set({user, isLoading: false, error: null, isInitialized: true}),
    };
});
vi.mock('$lib/stores/app/auth', () => ({
    auth: {subscribe: session.state.subscribe, login: vi.fn(async () => true), logout: vi.fn(async () => undefined), checkAuth: vi.fn(async () => 'authenticated'), clearError: vi.fn(), reset: vi.fn()},
    currentUser: session.currentUser,
    isAuthenticated: session.isAuthenticated,
    isAuthLoading: session.isAuthLoading,
    authError: session.authError,
    isAuthInitialized: session.isAuthInitialized,
    getAuthState: () => session.snapshot(),
    isSignOutRequested: () => false,
}));

/**
 * The public configuration of the instance (`GET /system/instance`), held by the test: the accounts part says which
 * registration mode is in force and whether LIBREFOLIO_REGISTRATION pins it. Getters over `$state`, as in the real
 * store, so the tab re-reads them; `load` is a spy. Open and unpinned before every test.
 */
const instance = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const OPEN: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
    return {
        OPEN,
        box: reactiveBox<{config: InstanceConfig}>({config: OPEN}),
        load: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
    };
});
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: instance.OPEN,
    fetchInstanceConfigFromApi: async () => instance.box.config,
    instanceConfig: {
        get config() {
            return instance.box.config;
        },
        get loaded() {
            return true;
        },
        get failed() {
            return false;
        },
        load: instance.load,
    },
}));

import UsersTab from './UsersTab.svelte';
import {zodiosApi} from '$lib/api';
import {_ as translatorStore} from '$lib/i18n';
// The real catalogues, read only by the last block of A-43: the tab renders through the identity translator above.
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

// --- Fixtures -------------------------------------------------------------

/** `pending_setup` as `GET /users` lists it since A7b: only A-43's fixtures carry it. */
type Account = {id: number; username: string; email: string; is_active: boolean; is_superuser: boolean; created_at: string; protected: boolean; pending_setup?: boolean};
type Invite = {id: number; grants_admin: boolean; email: string | null; created_at: string; expires_at: string; created_by_user_id: number | null};
type Usage = {used: number; max_users?: number | null; billing_url?: string | null};

const CREATED = '2025-03-04T09:30:00Z';
const EXPIRES = '2026-10-22T09:30:00Z';

const makeAccount = (id: number, username: string, flags: Partial<Account> = {}): Account => ({id, username, email: `${username}@example.test`, is_active: true, is_superuser: false, created_at: CREATED, protected: false, ...flags});

/** The signed-in administrator: their own row offers no action at all. */
const ME = makeAccount(1, 'root_admin', {is_superuser: true});
/** Another active administrator: beside ME, never the last one. */
const OTHER_ADMIN = makeAccount(2, 'second_admin', {is_superuser: true});
const REGULAR = makeAccount(3, 'plain_user');
const INACTIVE = makeAccount(4, 'dormant_user', {is_active: false});
/** The paying administrator of a managed instance: nobody deactivates, demotes or deletes it. */
const PROTECTED = makeAccount(5, 'billing_owner', {is_superuser: true, protected: true});
const ACCOUNTS: readonly Account[] = [ME, OTHER_ADMIN, REGULAR, INACTIVE, PROTECTED];

const INVITE_FOR_FRIEND: Invite = {id: 31, grants_admin: false, email: 'friend@example.test', created_at: CREATED, expires_at: EXPIRES, created_by_user_id: ME.id};
const INVITE_ADMIN_NO_EMAIL: Invite = {id: 32, grants_admin: true, email: null, created_at: CREATED, expires_at: EXPIRES, created_by_user_id: null};
const INVITES: readonly Invite[] = [INVITE_FOR_FRIEND, INVITE_ADMIN_NO_EMAIL];

/** Four active accounts plus two live invitations, against a limit of ten: room left. */
const ROOM: Usage = {used: 6, max_users: 10, billing_url: null};
/** Four active accounts plus two live invitations, against a limit of six. */
const FULL: Usage = {used: 6, max_users: 6, billing_url: null};
const BILLING = 'https://billing.example.test/librefolio/subscription';

const sessionUser = (a: Account) => ({id: a.id, username: a.username, email: a.email, is_active: a.is_active, is_superuser: a.is_superuser, created_at: a.created_at});

// --- The mocked server ----------------------------------------------------

/** What the server holds: the two lists answer from it, and the writes change it. Seeded fresh by every test. */
const server = {accounts: [] as Account[], invites: [] as Invite[], usage: {...ROOM} as Usage, nextInviteId: 100};

interface Scene {
    accounts?: readonly Account[];
    invites?: readonly Invite[];
    usage?: Usage;
}

function seed(scene: Scene = {}): void {
    server.accounts = (scene.accounts ?? ACCOUNTS).map((a) => ({...a}));
    server.invites = (scene.invites ?? INVITES).map((i) => ({...i}));
    server.usage = {...(scene.usage ?? ROOM)};
    server.nextInviteId = 100;
}

const usersAnswer = () => ({items: server.accounts.map((a) => ({...a})), usage: {...server.usage}});
const invitesAnswer = () => ({items: server.invites.map((i) => ({...i})), usage: {...server.usage}});

/** An axios-shaped refusal, with the body the backend sends: an object `detail` for a 409, a sentence for a 404. */
function refusal(status: number, detail: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, response: {status, data: {detail}}});
}
const conflict = (error_code: string, extra: Record<string, unknown> = {}) => refusal(409, {error_code, message: 'An English sentence nobody should read', ...extra});
const notFound = () => refusal(404, 'User not found');

const userIdOf = (config: unknown): unknown => (config as {params?: {user_id?: unknown}} | undefined)?.params?.user_id;

/** The account a per-account route is about; a 404, as the backend answers, when it is not (or no longer) there. */
function onServer(userId: unknown): Account {
    const found = server.accounts.find((a) => a.id === userId);
    if (!found) throw notFound();
    return found;
}

const previewOf = (a: Account) => ({user_id: a.id, username: a.username, brokers_deleted: [{id: 900 + a.id, name: `${a.username} broker`, transactions: 3}], brokers_left: [], transfers_unpaired: 0});

// --- API handles ----------------------------------------------------------

type Mocked = ReturnType<typeof vi.fn>;
const handle = (fn: unknown): Mocked => fn as Mocked;

const listUsers = () => handle(zodiosApi.list_accounts_api_v1_users_get);
const listInvites = () => handle(zodiosApi.list_invites_api_v1_users_invites_get);
const patchUser = () => handle(zodiosApi.update_account_api_v1_users__user_id__patch);
const revokeSessions = () => handle(zodiosApi.revoke_account_sessions_api_v1_users__user_id__sessions_revoke_post);
const resetGuides = () => handle(zodiosApi.reset_account_onboarding_api_v1_users__user_id__onboarding_reset_post);
const createResetLink = () => handle(zodiosApi.create_password_reset_link_api_v1_users__user_id__password_reset_link_post);
const previewDeletion = () => handle(zodiosApi.preview_account_deletion_api_v1_users__user_id__deletion_preview_get);
const previewOwnDeletion = () => handle(zodiosApi.preview_own_account_deletion_api_v1_auth_users_me_deletion_preview_get);
const deleteUser = () => handle(zodiosApi.delete_account_api_v1_users__user_id__delete);
const deleteOwn = () => handle(zodiosApi.delete_own_account_api_v1_auth_users_me_delete);
const createInvite = () => handle(zodiosApi.create_invite_api_v1_users_invites_post);
const revokeInvite = () => handle(zodiosApi.revoke_invite_api_v1_users_invites__invite_id__delete);
const issueProbe = () => handle(zodiosApi.issue_address_probe_api_v1_users_address_probe_post);
/** `PATCH /settings/global/bulk`, the registration mode's write: the mock client hands `axios` out as a bare spy, so its `patch` is given here (N69c). */
const bulkPatch = (): Mocked => {
    const axios = zodiosApi.axios as unknown as {patch?: Mocked};
    axios.patch ??= vi.fn();
    return axios.patch;
};

/** The identity translator of the `$lib/i18n` mock, a spy: the values a message was given, which it drops (A-43's toast). */
const translator = () => handle(get(translatorStore));

/** Every route that changes something on the server, by the name a failure should print. */
const WRITES: Record<string, () => Mocked> = {
    'PATCH /users/{id}': patchUser,
    'POST /users/{id}/sessions/revoke': revokeSessions,
    'POST /users/{id}/onboarding/reset': resetGuides,
    'POST /users/{id}/password-reset-link': createResetLink,
    'DELETE /users/{id}': deleteUser,
    'DELETE /auth/users/me': deleteOwn,
    'POST /users/invites': createInvite,
    'DELETE /users/invites/{id}': revokeInvite,
    'PATCH /settings/global/bulk': bulkPatch,
};

function expectNothingWritten(): void {
    for (const [route, call] of Object.entries(WRITES)) expect(call(), `${route} was not asked`).not.toHaveBeenCalled();
}

// --- DOM helpers ----------------------------------------------------------

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

const tab = () => screen.getByTestId('users-tab');

async function settled(): Promise<void> {
    await waitFor(() => expect(tab()).toHaveAttribute('data-busy', 'false'));
}

/** Seed the server, mount, and wait for both answers to be on screen — the rows, not merely the container. */
async function mount(scene: Scene = {}) {
    seed(scene);
    const utils = render(UsersTab);
    await waitFor(() => {
        expect(listUsers()).toHaveBeenCalled();
        expect(listInvites()).toHaveBeenCalled();
    });
    await settled();
    await waitFor(() => expect(screen.getAllByTestId('users-row')).toHaveLength(server.accounts.length));
    if (server.invites.length > 0) await waitFor(() => expect(screen.getAllByTestId('users-invite-row')).toHaveLength(server.invites.length));
    return utils;
}

const rowsOf = (userId: number) => screen.queryAllByTestId('users-row').filter((el) => el.getAttribute('data-user-id') === String(userId));

/** The row of one account, found by what it publishes — never by its position in the list. */
function rowOf(userId: number): HTMLElement {
    const found = rowsOf(userId);
    if (found.length !== 1) throw new Error(`expected one users-row with data-user-id="${userId}", found ${found.length}`);
    return found[0];
}

const toggleOf = (userId: number) => within(rowOf(userId)).getByTestId('users-row-toggle');

/** Open a row's actions panel. Rule 14: ask for the state first, never click a toggle blind. */
async function openPanel(userId: number): Promise<HTMLElement> {
    if (toggleOf(userId).getAttribute('aria-expanded') !== 'true') await fireEvent.click(toggleOf(userId));
    await waitFor(() => expect(toggleOf(userId)).toHaveAttribute('aria-expanded', 'true'));
    return rowOf(userId);
}

type Action = 'deactivate' | 'reactivate' | 'promote' | 'demote' | 'reset-link' | 'sign-out' | 'restart-guides' | 'delete' | 'cancel-setup';

const actionIn = (row: HTMLElement, action: Action) => within(row).getByTestId(`users-action-${action}`);
const offered = (row: HTMLElement, action: Action) => within(row).queryByTestId(`users-action-${action}`);

function expectDisabled(control: HTMLElement, reason: string): void {
    expect(control).toBeDisabled();
    expect(control).toHaveAttribute('data-disabled-reason', reason);
}

function expectEnabled(control: HTMLElement): void {
    expect(control).toBeEnabled();
    expect(control.getAttribute('data-disabled-reason') || null, 'an enabled control carries no reason').toBeNull();
}

/** The open confirmation. `ConfirmModal` puts its `testId` on its header, so the dialog is the header's ancestor. */
async function confirmation(): Promise<HTMLElement> {
    const header = await screen.findByTestId('users-confirm');
    const dialog = header.closest<HTMLElement>('[role="dialog"]');
    if (!dialog) throw new Error('users-confirm is not inside a role="dialog"');
    return dialog;
}

async function acceptConfirmation(): Promise<void> {
    await fireEvent.click(within(await confirmation()).getByTestId('confirm-modal-confirm'));
}

/** Cancel, and end on what the helper promises (rule 19): the confirmation is gone. */
async function declineConfirmation(): Promise<void> {
    await fireEvent.click(within(await confirmation()).getByTestId('confirm-modal-cancel'));
    await waitFor(() => expect(screen.queryByTestId('users-confirm')).not.toBeInTheDocument());
}

type Note = {name: string; detail?: Record<string, unknown>; toast?: {variant: string; message: string}};

/** The notifications sent under one name, in order. */
const notes = (name: string): Note[] => notify.mock.calls.map(([note]) => note as Note).filter((note) => note.name === name);

/** Exactly one notification of that name — one action, one event — once it has been sent. */
async function oneNote(name: string): Promise<Note> {
    await waitFor(() => expect(notes(name)).toHaveLength(1));
    return notes(name)[0];
}

const inviteRowsOf = (inviteId: number) => screen.queryAllByTestId('users-invite-row').filter((el) => el.getAttribute('data-invite-id') === String(inviteId));

function inviteRowOf(inviteId: number): HTMLElement {
    const found = inviteRowsOf(inviteId);
    if (found.length !== 1) throw new Error(`expected one users-invite-row with data-invite-id="${inviteId}", found ${found.length}`);
    return found[0];
}

// --- Lifecycle --------------------------------------------------------------

beforeAll(async () => {
    // The rules below are reactive: fail loudly if this file ever loses its jsdom docblock.
    assertEffectsRun();
    // The mocked `$lib/i18n` covers `$_`; this initialises svelte-i18n itself, should a formatter reach it directly.
    await setupI18n();
});

beforeEach(() => {
    vi.clearAllMocks();
    // `clearAllMocks` keeps implementations and queued `…Once` values: every alias this file drives is reset, then
    // given the behaviour of the mocked server.
    for (const fn of [listUsers(), listInvites(), patchUser(), revokeSessions(), resetGuides(), createResetLink(), previewDeletion(), previewOwnDeletion(), deleteUser(), deleteOwn(), createInvite(), revokeInvite(), issueProbe()]) fn.mockReset();
    seed();
    session.signIn(sessionUser(ME));
    instance.box.config = instance.OPEN;
    instance.load.mockResolvedValue(undefined);
    bulkPatch().mockReset().mockResolvedValue({data: null});

    listUsers().mockImplementation(async () => usersAnswer());
    listInvites().mockImplementation(async () => invitesAnswer());
    patchUser().mockImplementation(async (body: Partial<Account> | undefined, config: unknown) => {
        const target = onServer(userIdOf(config));
        // `cancel_setup` (A-51) says why `is_active: false` is asked; it is not a column, and the backend stores nothing under it
        for (const [key, value] of Object.entries(body ?? {})) if (key !== 'cancel_setup' && value !== undefined && value !== null) Object.assign(target, {[key]: value});
        return {...target};
    });
    revokeSessions().mockImplementation(async (_body: unknown, config: unknown) => void onServer(userIdOf(config)));
    resetGuides().mockImplementation(async (_body: unknown, config: unknown) => void onServer(userIdOf(config)));
    createResetLink().mockImplementation(async (_body: unknown, config: unknown) => {
        onServer(userIdOf(config));
        return {token: 'reset-token', path: '/reset-password#reset-token', url: null, expires_at: EXPIRES};
    });
    previewDeletion().mockImplementation(async (config: unknown) => previewOf(onServer(userIdOf(config))));
    previewOwnDeletion().mockImplementation(async () => previewOf(onServer(ME.id)));
    deleteUser().mockImplementation(async (_body: unknown, config: unknown) => {
        const gone = onServer(userIdOf(config));
        server.accounts = server.accounts.filter((a) => a.id !== gone.id);
    });
    createInvite().mockImplementation(async (body?: {grants_admin?: boolean | null; email?: string | null}) => {
        const invite: Invite = {id: server.nextInviteId++, grants_admin: body?.grants_admin ?? false, email: body?.email || null, created_at: CREATED, expires_at: EXPIRES, created_by_user_id: ME.id};
        server.invites.push(invite);
        return {invite: {...invite}, token: 'invite-token', path: '/invite#invite-token', url: null};
    });
    revokeInvite().mockImplementation(async (_body: unknown, config: unknown) => {
        const inviteId = (config as {params?: {invite_id?: unknown}} | undefined)?.params?.invite_id;
        const before = server.invites.length;
        server.invites = server.invites.filter((i) => i.id !== inviteId);
        if (server.invites.length === before) throw refusal(404, 'Invitation not found');
    });
    issueProbe().mockImplementation(async () => ({nonce: 'probe-nonce', expires_at: EXPIRES}));
});

// =========================================================================
describe('UsersTab — loading both lists (UTAB-01…02)', () => {
    it.each([
        {id: 'UTAB-01', first: 'users'},
        {id: 'UTAB-02', first: 'invitations'},
    ] as const)('$id: busy while either list is pending, both asked at once — the $first answer first', async ({first}) => {
        seed();
        const users = deferred<unknown>();
        const invitations = deferred<unknown>();
        listUsers().mockImplementation(() => users.promise);
        listInvites().mockImplementation(() => invitations.promise);

        render(UsersTab);

        // In parallel, not one after the other: both are asked before either has answered.
        await waitFor(() => {
            expect(listUsers()).toHaveBeenCalledTimes(1);
            expect(listInvites()).toHaveBeenCalledTimes(1);
        });
        expect(tab()).toHaveAttribute('data-busy', 'true');
        expect(tab()).toHaveAttribute('aria-busy', 'true');

        const answer = {users: () => users.resolve(usersAnswer()), invitations: () => invitations.resolve(invitesAnswer())};
        const second = first === 'users' ? 'invitations' : 'users';
        answer[first]();
        // Not a clock wait: a few microtask turns for the tab to handle that answer (its continuation on the promise was
        // registered before ours), then Svelte's flush. A tab that drops its busy flag on the first answer shows it by
        // now; a correct one stays busy whatever the timing, so this negative can only ever err towards green.
        await (first === 'users' ? users.promise : invitations.promise);
        await tick();
        await tick();
        expect(tab(), `the ${second} are still pending`).toHaveAttribute('data-busy', 'true');
        expect(tab()).toHaveAttribute('aria-busy', 'true');

        answer[second]();

        await settled();
        expect(tab()).toHaveAttribute('aria-busy', 'false');
        await waitFor(() => expect(screen.getAllByTestId('users-row')).toHaveLength(ACCOUNTS.length));
        expect(screen.getAllByTestId('users-invite-row')).toHaveLength(INVITES.length);
    });
});

// =========================================================================
describe('UsersTab — the usage of the instance (UTAB-03…08)', () => {
    it('UTAB-03: publishes the places taken and the limit', async () => {
        await mount({usage: {used: 6, max_users: 10, billing_url: null}});

        expect(screen.getByTestId('users-usage')).toHaveAttribute('data-used', '6');
        expect(screen.getByTestId('users-usage')).toHaveAttribute('data-max', '10');
    });

    it.each([
        {id: 'UTAB-04', how: 'null', usage: {used: 6, max_users: null} as Usage},
        {id: 'UTAB-05', how: 'absent', usage: {used: 6} as Usage},
    ])('$id: publishes an empty data-max when there is no limit (max_users $how)', async ({usage}) => {
        await mount({usage});

        expect(screen.getByTestId('users-usage')).toHaveAttribute('data-used', '6');
        expect(screen.getByTestId('users-usage')).toHaveAttribute('data-max', '');
    });

    it('UTAB-06: links the subscription, outside the app, when the instance has a billing address', async () => {
        await mount({usage: {...ROOM, billing_url: BILLING}});

        const links = screen.getAllByTestId('users-billing-link');
        for (const link of links) {
            expect(link).toHaveAttribute('href', BILLING);
            expect(link).toHaveAttribute('target', '_blank');
            expect((link.getAttribute('rel') ?? '').split(/\s+/), 'rel="noopener noreferrer"').toEqual(expect.arrayContaining(['noopener', 'noreferrer']));
        }
    });

    it.each([
        {id: 'UTAB-07', how: 'null', usage: {...ROOM, billing_url: null} as Usage},
        {id: 'UTAB-08', how: 'absent', usage: {used: 6, max_users: 10} as Usage},
    ])('$id: no billing link without a billing address (billing_url $how)', async ({usage}) => {
        await mount({usage});

        expect(screen.getByTestId('users-usage'), 'barrier: the usage is drawn').toBeInTheDocument();
        expect(screen.queryAllByTestId('users-billing-link')).toHaveLength(0);
    });
});

// =========================================================================
describe('UsersTab — a full instance (UTAB-09…14)', () => {
    it.each([
        {id: 'UTAB-09', used: 6, max: 6},
        {id: 'UTAB-10', used: 7, max: 6},
    ])('$id: full at $used of $max — the banner, and no invitation', async ({used, max}) => {
        await mount({usage: {used, max_users: max, billing_url: null}});

        expect(screen.getByTestId('users-limit-banner')).toBeInTheDocument();
        expectDisabled(screen.getByTestId('users-invite-button'), 'limit');
    });

    it('UTAB-11: the banner of a full instance carries the subscription link when there is one', async () => {
        await mount({usage: {...FULL, billing_url: BILLING}});

        const banner = screen.getByTestId('users-limit-banner');
        const hrefs = within(banner)
            .getAllByRole('link')
            .map((a) => a.getAttribute('href'));
        expect(hrefs).toContain(BILLING);
    });

    it.each([
        {id: 'UTAB-12', how: 'one place left', usage: {used: 5, max_users: 6, billing_url: null} as Usage},
        {id: 'UTAB-13', how: 'no limit', usage: {used: 50, max_users: null, billing_url: null} as Usage},
    ])('$id: not full ($how) — no banner, invitations open', async ({usage}) => {
        await mount({usage});

        expectEnabled(screen.getByTestId('users-invite-button'));
        expect(screen.queryByTestId('users-limit-banner')).not.toBeInTheDocument();
    });

    it('UTAB-14: a full instance cannot take a reactivated account back', async () => {
        await mount({usage: FULL});

        const row = await openPanel(INACTIVE.id);

        expectDisabled(actionIn(row, 'reactivate'), 'limit');
    });
});

// =========================================================================
describe('UsersTab — whether registration is open (UTAB-15…19)', () => {
    const registration = (mode: 'open' | 'invite' | 'disabled', locked = false): void => {
        instance.box.config = {profile: 'selfhosted', accounts: {registration_mode: mode, registration_locked: locked}};
    };

    it.each([
        {id: 'UTAB-15', how: 'by the global setting', locked: false},
        {id: 'UTAB-16', how: 'by LIBREFOLIO_REGISTRATION', locked: true},
    ])('$id: registration closed $how — no invitation, and the hint says why', async ({locked}) => {
        registration('disabled', locked);
        await mount();

        expectDisabled(screen.getByTestId('users-invite-button'), 'registration-disabled');
        expect(screen.getByTestId('users-invite-blocked')).toBeInTheDocument();
    });

    it.each([
        {id: 'UTAB-17', mode: 'open'},
        {id: 'UTAB-18', mode: 'invite'},
    ] as const)('$id: registration $mode — invitations open, no hint', async ({mode}) => {
        registration(mode);
        await mount();

        expectEnabled(screen.getByTestId('users-invite-button'));
        expect(screen.queryByTestId('users-invite-blocked')).not.toBeInTheDocument();
    });

    it('UTAB-19: follows the instance configuration while on screen', async () => {
        await mount();
        expectEnabled(screen.getByTestId('users-invite-button'));

        registration('disabled');

        await waitFor(() => expectDisabled(screen.getByTestId('users-invite-button'), 'registration-disabled'));
        expect(screen.getByTestId('users-invite-blocked')).toBeInTheDocument();

        registration('invite');

        await waitFor(() => expectEnabled(screen.getByTestId('users-invite-button')));
        expect(screen.queryByTestId('users-invite-blocked')).not.toBeInTheDocument();
    });
});

// =========================================================================
describe('UsersTab — the account rows (UTAB-20…22)', () => {
    it('UTAB-20: one users-row per account, in users-accounts, publishing who it is', async () => {
        await mount();

        const list = screen.getByTestId('users-accounts');
        expect(within(list).getAllByTestId('users-row')).toHaveLength(ACCOUNTS.length);
        for (const a of ACCOUNTS) {
            const row = rowOf(a.id);
            expect(list).toContainElement(row);
            expect(row).toHaveAttribute('data-username', a.username);
            expect(row).toHaveAttribute('data-active', String(a.is_active));
            expect(row).toHaveAttribute('data-admin', String(a.is_superuser));
            expect(row).toHaveAttribute('data-protected', String(a.protected));
            expect(row, `data-self of ${a.username}`).toHaveAttribute('data-self', String(a.id === ME.id));
        }
    });

    it('UTAB-21: the own row opens on a hint to the profile, and offers no action at all', async () => {
        await mount();
        expect(toggleOf(ME.id)).toHaveAttribute('aria-expanded', 'false');

        await fireEvent.click(toggleOf(ME.id));

        await waitFor(() => expect(toggleOf(ME.id)).toHaveAttribute('aria-expanded', 'true'));
        const own = rowOf(ME.id);
        // The presence barrier for the absence below: the panel is open, and it is the hint that fills it.
        expect(within(own).getByTestId('users-self-hint')).toBeInTheDocument();
        expect(own.querySelectorAll('[data-testid^="users-action-"]'), 'not one action on your own account').toHaveLength(0);
        const hrefs = within(own)
            .getAllByRole('link')
            .map((a) => a.getAttribute('href') ?? '');
        expect(
            hrefs.some((href) => /[?&]tab=profile(?:[&#]|$)/.test(href)),
            `a link to ?tab=profile among ${JSON.stringify(hrefs)}`,
        ).toBe(true);

        await fireEvent.click(toggleOf(ME.id));

        await waitFor(() => expect(toggleOf(ME.id)).toHaveAttribute('aria-expanded', 'false'));
    });

    it("UTAB-22: another account's toggle opens its actions panel, and closes it again", async () => {
        await mount();
        expect(toggleOf(REGULAR.id)).toHaveAttribute('aria-expanded', 'false');

        await fireEvent.click(toggleOf(REGULAR.id));

        await waitFor(() => expect(toggleOf(REGULAR.id)).toHaveAttribute('aria-expanded', 'true'));
        expect(actionIn(rowOf(REGULAR.id), 'reset-link')).toBeInTheDocument();
        expect(toggleOf(OTHER_ADMIN.id), 'only that row opened').toHaveAttribute('aria-expanded', 'false');

        await fireEvent.click(toggleOf(REGULAR.id));

        await waitFor(() => expect(toggleOf(REGULAR.id)).toHaveAttribute('aria-expanded', 'false'));
    });
});

// =========================================================================
describe('UsersTab — which actions a row offers, and why one is off (UTAB-23…31)', () => {
    it('UTAB-23: a protected account cannot be deactivated, demoted or deleted', async () => {
        await mount();

        const row = await openPanel(PROTECTED.id);

        for (const action of ['deactivate', 'demote', 'delete'] as const) expectDisabled(actionIn(row, action), 'protected');
        // since A5-1 (23/10/2026) nobody else resets its password or signs it out either: the server answers 409, the row says why first
        for (const action of ['reset-link', 'sign-out'] as const) expectDisabled(actionIn(row, action), 'protected');
        expectEnabled(actionIn(row, 'restart-guides'));
        expect(offered(row, 'promote'), 'an administrator is not promoted').toBeNull();
        expect(offered(row, 'reactivate'), 'an active account is not reactivated').toBeNull();
    });

    it('UTAB-24: another active administrator — deactivate and demote on, delete waits for a demotion', async () => {
        await mount();

        const row = await openPanel(OTHER_ADMIN.id);

        expectEnabled(actionIn(row, 'deactivate'));
        expectEnabled(actionIn(row, 'demote'));
        expectDisabled(actionIn(row, 'delete'), 'demote-first');
        expect(offered(row, 'promote'), 'an administrator is not promoted').toBeNull();
        expect(offered(row, 'reactivate'), 'an active account is not reactivated').toBeNull();
    });

    it('UTAB-25: a regular active account — deactivate, promote and delete on', async () => {
        await mount();

        const row = await openPanel(REGULAR.id);

        for (const action of ['deactivate', 'promote', 'delete'] as const) expectEnabled(actionIn(row, action));
        expect(offered(row, 'demote'), 'a regular account is not demoted').toBeNull();
        expect(offered(row, 'reactivate'), 'an active account is not reactivated').toBeNull();
    });

    it('UTAB-26: an inactive regular account, with room left — reactivate and delete on, no deactivate', async () => {
        await mount();

        const row = await openPanel(INACTIVE.id);

        expectEnabled(actionIn(row, 'reactivate'));
        expectEnabled(actionIn(row, 'delete'));
        expect(offered(row, 'deactivate'), 'an inactive account is not deactivated again').toBeNull();
    });

    it('UTAB-27: every other account offers a reset link, a sign-out and a restart of the guides — the protected one only the restart (A5-1)', async () => {
        await mount();

        for (const a of ACCOUNTS.filter((candidate) => candidate.id !== ME.id && !candidate.protected)) {
            const row = await openPanel(a.id);
            for (const action of ['reset-link', 'sign-out', 'restart-guides'] as const) expectEnabled(actionIn(row, action));
        }
    });

    /*
     * `last-admin` is computed from the list alone: the row is the only active administrator *of the list* (plan A6b.1:
     * «l'unico admin attivo della lista»; the backend stays the authority with its 409 LAST_ADMIN). On a real session it
     * never shows on another row — whoever reads this tab is an active administrator, so no other row is ever the only
     * one. These fixtures therefore list the signed-in account as a regular one (the list is newer than the session),
     * so that another row can be the last active administrator. The session's own flags play no part in the rule.
     */
    const ME_LISTED_REGULAR = makeAccount(ME.id, ME.username, {is_superuser: false});
    const THIRD_ADMIN = makeAccount(6, 'third_admin', {is_superuser: true});
    const DORMANT_ADMIN = makeAccount(7, 'dormant_admin', {is_superuser: true, is_active: false});

    it.each([
        {id: 'UTAB-28', how: 'the only administrator of the list', accounts: [ME_LISTED_REGULAR, OTHER_ADMIN, REGULAR]},
        {id: 'UTAB-29', how: 'beside an inactive administrator, who does not count', accounts: [ME_LISTED_REGULAR, OTHER_ADMIN, DORMANT_ADMIN, REGULAR]},
    ])('$id: the last active administrator ($how) cannot be deactivated or demoted', async ({accounts}) => {
        await mount({accounts});

        const row = await openPanel(OTHER_ADMIN.id);

        expectDisabled(actionIn(row, 'deactivate'), 'last-admin');
        expectDisabled(actionIn(row, 'demote'), 'last-admin');
        expectDisabled(actionIn(row, 'delete'), 'demote-first');
    });

    it('UTAB-30: with a second active administrator, neither is the last', async () => {
        await mount({accounts: [ME_LISTED_REGULAR, OTHER_ADMIN, THIRD_ADMIN, REGULAR]});

        for (const id of [OTHER_ADMIN.id, THIRD_ADMIN.id]) {
            const row = await openPanel(id);
            expectEnabled(actionIn(row, 'deactivate'));
            expectEnabled(actionIn(row, 'demote'));
        }
    });

    it('UTAB-31: protected outranks last-admin, as the reasons are ordered', async () => {
        await mount({accounts: [ME_LISTED_REGULAR, PROTECTED, REGULAR]});

        const row = await openPanel(PROTECTED.id);

        for (const action of ['deactivate', 'demote', 'delete'] as const) expectDisabled(actionIn(row, action), 'protected');
    });
});

// =========================================================================
describe('UsersTab — an action reaches the server, then the tab reloads (UTAB-32…42)', () => {
    /** The body is not the subject: the route takes none, and only the options' position is pinned. */
    const ANY_BODY = Symbol('any body');

    type Flow = {
        id: string;
        action: Action;
        target: Account;
        confirm: boolean;
        call: () => Mocked;
        body: unknown;
        event: string;
        toast: boolean;
        /** What the reloaded answer changes on the row: the server applied the write. */
        after?: [attribute: string, value: string];
    };

    const FLOWS: Flow[] = [
        {id: 'UTAB-32', action: 'deactivate', target: REGULAR, confirm: true, call: patchUser, body: {is_active: false}, event: 'accounts.user.deactivated', toast: false, after: ['data-active', 'false']},
        {id: 'UTAB-33', action: 'reactivate', target: INACTIVE, confirm: false, call: patchUser, body: {is_active: true}, event: 'accounts.user.reactivated', toast: false, after: ['data-active', 'true']},
        {id: 'UTAB-34', action: 'promote', target: REGULAR, confirm: true, call: patchUser, body: {is_superuser: true}, event: 'accounts.user.promoted', toast: false, after: ['data-admin', 'true']},
        {id: 'UTAB-35', action: 'demote', target: OTHER_ADMIN, confirm: true, call: patchUser, body: {is_superuser: false}, event: 'accounts.user.demoted', toast: false, after: ['data-admin', 'false']},
        {id: 'UTAB-36', action: 'sign-out', target: REGULAR, confirm: true, call: revokeSessions, body: ANY_BODY, event: 'accounts.user.sessions-revoked', toast: true},
        {id: 'UTAB-37', action: 'restart-guides', target: REGULAR, confirm: true, call: resetGuides, body: null, event: 'accounts.user.onboarding-reset', toast: true},
    ];

    it.each(FLOWS)('$id: $action → the request for that account, a reload, and $event', async (flow) => {
        await mount();
        const row = await openPanel(flow.target.id);
        const listsBefore = listUsers().mock.calls.length;

        await fireEvent.click(actionIn(row, flow.action));
        if (flow.confirm) {
            await confirmation();
            expect(flow.call(), 'nothing is sent before the confirmation').not.toHaveBeenCalled();
            await acceptConfirmation();
        }

        await waitFor(() => expect(flow.call()).toHaveBeenCalledTimes(1));
        const [body, options] = flow.call().mock.calls[0];
        if (flow.body !== ANY_BODY) expect(body, 'the body is the subject').toEqual(flow.body);
        expect(options, 'the options come second: (body, {params})').toEqual(expect.objectContaining({params: {user_id: flow.target.id}}));
        if (!flow.confirm) expect(screen.queryByTestId('users-confirm'), 'this action asks for no confirmation').not.toBeInTheDocument();
        await waitFor(() => expect(screen.queryByTestId('users-confirm')).not.toBeInTheDocument());

        await waitFor(() => expect(listUsers().mock.calls.length, 'the tab reloads after the action').toBeGreaterThan(listsBefore));
        if (flow.after) {
            const [attribute, value] = flow.after;
            await waitFor(() => expect(rowOf(flow.target.id), 'the reloaded answer is what the row shows').toHaveAttribute(attribute, value));
        }

        const note = await oneNote(flow.event);
        expect(note.detail).toEqual(expect.objectContaining({user_id: flow.target.id}));
        if (flow.toast) expect(note.toast).toEqual(expect.objectContaining({variant: 'success'}));
        else expect(note.toast, 'the row already shows the change: no toast').toBeUndefined();
        expect(notes('accounts.action.failed')).toHaveLength(0);
        await settled();
    });

    it.each([
        {id: 'UTAB-38', action: 'deactivate', target: REGULAR},
        {id: 'UTAB-39', action: 'promote', target: REGULAR},
        {id: 'UTAB-40', action: 'demote', target: OTHER_ADMIN},
        {id: 'UTAB-41', action: 'sign-out', target: REGULAR},
        {id: 'UTAB-42', action: 'restart-guides', target: REGULAR},
    ] as const)('$id: cancelling the $action confirmation sends nothing and reloads nothing', async ({action, target}) => {
        await mount();
        const row = await openPanel(target.id);
        const listsBefore = listUsers().mock.calls.length;
        const notesBefore = notify.mock.calls.length;

        await fireEvent.click(actionIn(row, action));
        await declineConfirmation();

        expectNothingWritten();
        expect(listUsers().mock.calls.length, 'no reload').toBe(listsBefore);
        expect(notify.mock.calls.length, 'no event').toBe(notesBefore);
    });
});

// =========================================================================
describe('UsersTab — when the server refuses (UTAB-43…46)', () => {
    it.each([
        {id: 'UTAB-43', code: 'LAST_ADMIN', action: 'demote', target: OTHER_ADMIN, refused: () => conflict('LAST_ADMIN'), success: 'accounts.user.demoted'},
        {id: 'UTAB-44', code: 'ACCOUNT_PROTECTED', action: 'deactivate', target: REGULAR, refused: () => conflict('ACCOUNT_PROTECTED', {reason: 'managed instance'}), success: 'accounts.user.deactivated'},
    ] as const)('$id: a 409 $code → accounts.action.failed with that code, and an error toast', async ({code, action, target, refused, success}) => {
        // The backend stays the authority: it may refuse what the list allowed (another administrator acted meanwhile).
        patchUser().mockRejectedValue(refused());
        await mount();
        const row = await openPanel(target.id);

        await fireEvent.click(actionIn(row, action));
        await acceptConfirmation();

        const failure = await oneNote('accounts.action.failed');
        expect(failure.detail).toEqual(expect.objectContaining({code, user_id: target.id, action: expect.any(String)}));
        expect(failure.toast, 'one notification, two halves: the toast is a field of the same call').toEqual(expect.objectContaining({variant: 'error'}));
        expect(notes(success), 'a refusal is not announced as done').toHaveLength(0);
    });

    it.each([
        {id: 'UTAB-45', action: 'reactivate', target: INACTIVE, confirm: false, call: patchUser},
        {id: 'UTAB-46', action: 'sign-out', target: REGULAR, confirm: true, call: revokeSessions},
    ] as const)('$id: a 404 on $action — the account is gone: NOT_FOUND, and the list reloads without it', async ({action, target, confirm, call}) => {
        await mount();
        const row = await openPanel(target.id);
        // Another administrator deleted it after this list was drawn: the server answers 404 for it from now on.
        server.accounts = server.accounts.filter((a) => a.id !== target.id);
        const listsBefore = listUsers().mock.calls.length;

        await fireEvent.click(actionIn(row, action));
        if (confirm) await acceptConfirmation();

        await waitFor(() => expect(call()).toHaveBeenCalledTimes(1));
        const failure = await oneNote('accounts.action.failed');
        expect(failure.detail).toEqual(expect.objectContaining({code: 'NOT_FOUND', user_id: target.id}));
        expect(failure.toast).toEqual(expect.objectContaining({variant: 'error'}));
        await waitFor(() => expect(listUsers().mock.calls.length, 'a 404 reloads the list').toBeGreaterThan(listsBefore));
        await waitFor(() => expect(rowsOf(target.id), 'the reloaded list no longer has it').toHaveLength(0));
    });
});

// =========================================================================
describe('UsersTab — the dialogs it opens, and what it does when they finish (UTAB-47…51)', () => {
    it('UTAB-47: reset link opens users-reset-dialog for that account, and creates nothing until asked', async () => {
        await mount();
        const row = await openPanel(REGULAR.id);

        await fireEvent.click(actionIn(row, 'reset-link'));

        expect(await screen.findByTestId('users-reset-dialog')).toBeInTheDocument();
        expect(createResetLink(), 'the dialog confirms first: the links issued before stop working').not.toHaveBeenCalled();
        // One step into the dialog, only to prove which account the tab handed it.
        await fireEvent.click(screen.getByTestId('users-reset-create'));
        await waitFor(() => expect(createResetLink()).toHaveBeenCalledTimes(1));
        expect(createResetLink().mock.calls[0][1]).toEqual(expect.objectContaining({params: {user_id: REGULAR.id}}));
    });

    it('UTAB-48: invite opens users-invite-dialog, and its cancel closes it', async () => {
        await mount();

        await fireEvent.click(screen.getByTestId('users-invite-button'));

        expect(await screen.findByTestId('users-invite-dialog')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('users-invite-cancel'));
        await waitFor(() => expect(screen.queryByTestId('users-invite-dialog')).not.toBeInTheDocument());
        expect(createInvite()).not.toHaveBeenCalled();
    });

    it('UTAB-49: once an invitation is made and the dialog done, it closes and the new invitation is listed', async () => {
        await mount();
        await fireEvent.click(screen.getByTestId('users-invite-button'));
        await screen.findByTestId('users-invite-dialog');
        const invitesBefore = listInvites().mock.calls.length;

        await fireEvent.click(screen.getByTestId('users-invite-create'));
        await waitFor(() => expect(createInvite()).toHaveBeenCalledTimes(1));
        const {invite} = (await createInvite().mock.results[0].value) as {invite: Invite};
        await fireEvent.click(await screen.findByTestId('users-invite-done'));

        await waitFor(() => expect(screen.queryByTestId('users-invite-dialog')).not.toBeInTheDocument());
        await waitFor(() => expect(listInvites().mock.calls.length, 'the invitations are asked again').toBeGreaterThan(invitesBefore));
        await waitFor(() => expect(inviteRowsOf(invite.id), 'the reloaded answer is on screen').toHaveLength(1));
    });

    it('UTAB-50: delete on a regular row opens users-delete-dialog on the admin preview of that account', async () => {
        await mount();
        const row = await openPanel(REGULAR.id);

        await fireEvent.click(actionIn(row, 'delete'));

        expect(await screen.findByTestId('users-delete-dialog')).toBeInTheDocument();
        await waitFor(() => expect(previewDeletion()).toHaveBeenCalled());
        for (const [options] of previewDeletion().mock.calls) expect(options).toEqual(expect.objectContaining({params: {user_id: REGULAR.id}}));
        expect(previewOwnDeletion(), 'the admin mode, not the deletion of your own account').not.toHaveBeenCalled();

        await waitFor(() => expect(screen.getByTestId('users-delete-dialog')).toHaveAttribute('data-busy', 'false'));
        await fireEvent.click(screen.getByTestId('users-delete-cancel'));
        await waitFor(() => expect(screen.queryByTestId('users-delete-dialog')).not.toBeInTheDocument());
        expect(deleteUser()).not.toHaveBeenCalled();
    });

    it('UTAB-51: a deletion confirmed in the dialog closes it, and the list reloads without the account', async () => {
        await mount();
        // An inactive account: the dialog offers no «deactivate instead» before the deletion.
        const row = await openPanel(INACTIVE.id);
        await fireEvent.click(actionIn(row, 'delete'));
        await screen.findByTestId('users-delete-dialog');
        await waitFor(() => expect(screen.getByTestId('users-delete-dialog')).toHaveAttribute('data-busy', 'false'));
        const listsBefore = listUsers().mock.calls.length;

        await fireEvent.input(screen.getByTestId('users-delete-confirm-input'), {target: {value: INACTIVE.username}});
        await waitFor(() => expect(screen.getByTestId('users-delete-confirm')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('users-delete-confirm'));

        await waitFor(() => expect(deleteUser()).toHaveBeenCalledTimes(1));
        expect(deleteUser().mock.calls[0][1]).toEqual(expect.objectContaining({params: {user_id: INACTIVE.id}}));
        await waitFor(() => expect(screen.queryByTestId('users-delete-dialog')).not.toBeInTheDocument());
        await waitFor(() => expect(listUsers().mock.calls.length, 'the tab reloads after a deletion').toBeGreaterThan(listsBefore));
        await waitFor(() => expect(rowsOf(INACTIVE.id), 'the reloaded list no longer has it').toHaveLength(0));
    });
});

// =========================================================================
describe('UsersTab — the live invitations (UTAB-52…54)', () => {
    it('UTAB-52: one users-invite-row per invitation, in users-invites, publishing what it grants', async () => {
        await mount();

        const list = screen.getByTestId('users-invites');
        expect(within(list).getAllByTestId('users-invite-row')).toHaveLength(INVITES.length);
        for (const invite of INVITES) {
            const row = inviteRowOf(invite.id);
            expect(list).toContainElement(row);
            expect(row, 'an empty data-email when the invitation names nobody').toHaveAttribute('data-email', invite.email ?? '');
            expect(row).toHaveAttribute('data-admin', String(invite.grants_admin));
        }
    });

    it('UTAB-53: revoke asks first, deletes that invitation, reloads, and says so without a toast', async () => {
        await mount();
        const invitesBefore = listInvites().mock.calls.length;

        await fireEvent.click(within(inviteRowOf(INVITE_FOR_FRIEND.id)).getByTestId('users-invite-revoke'));
        await confirmation();
        expect(revokeInvite(), 'nothing is sent before the confirmation').not.toHaveBeenCalled();
        await acceptConfirmation();

        await waitFor(() => expect(revokeInvite()).toHaveBeenCalledTimes(1));
        expect(revokeInvite().mock.calls[0][1], 'the options come second: (body, {params})').toEqual(expect.objectContaining({params: {invite_id: INVITE_FOR_FRIEND.id}}));
        await waitFor(() => expect(listInvites().mock.calls.length, 'the invitations are asked again').toBeGreaterThan(invitesBefore));
        await waitFor(() => expect(inviteRowsOf(INVITE_FOR_FRIEND.id), 'the reloaded list no longer has it').toHaveLength(0));
        expect(inviteRowsOf(INVITE_ADMIN_NO_EMAIL.id), 'the other one stays').toHaveLength(1);
        const note = await oneNote('accounts.invite.revoked');
        expect(note.detail).toEqual(expect.objectContaining({invite_id: INVITE_FOR_FRIEND.id}));
        expect(note.toast, 'the list already shows it: no toast').toBeUndefined();
    });

    it('UTAB-54: cancelling the revocation sends nothing and keeps the invitation', async () => {
        await mount();
        const invitesBefore = listInvites().mock.calls.length;
        const notesBefore = notify.mock.calls.length;

        await fireEvent.click(within(inviteRowOf(INVITE_FOR_FRIEND.id)).getByTestId('users-invite-revoke'));
        await declineConfirmation();

        expectNothingWritten();
        expect(listInvites().mock.calls.length, 'no reload').toBe(invitesBefore);
        expect(notify.mock.calls.length, 'no event').toBe(notesBefore);
        expect(inviteRowsOf(INVITE_FOR_FRIEND.id)).toHaveLength(1);
    });
});

// =========================================================================
describe('UsersTab — cancelling the setup link of the waiting administrator (UTAB-55…60, A-43)', () => {
    /** The administrator of LIBREFOLIO_ADMIN_EMAIL as the bootstrap leaves it (F02): inactive, an administrator, waiting for its setup link. */
    const WAITING_ADMIN = makeAccount(8, 'f02_admin', {is_active: false, is_superuser: true, pending_setup: true});
    /** The same account in a list older than the server's answer, drawn before the server said it waits: «Demote» is on. */
    const STALE_WAITING_ADMIN = makeAccount(WAITING_ADMIN.id, WAITING_ADMIN.username, {is_active: false, is_superuser: true});
    const WITH_WAITING_ADMIN: Scene = {accounts: [...ACCOUNTS, WAITING_ADMIN]};

    const CANCEL_SETUP = {title: 'settings.usersTab.confirm.cancelSetup.title', message: 'settings.usersTab.confirm.cancelSetup.message', confirm: 'settings.usersTab.confirm.cancelSetup.confirm'};
    const SETUP_CANCELLED_TOAST = 'settings.usersTab.toasts.setupCancelled';

    // red until A-43
    it('UTAB-55: cancel setup asks first, in a danger confirmation worded by the cancelSetup keys', async () => {
        await mount(WITH_WAITING_ADMIN);
        const row = await openPanel(WAITING_ADMIN.id);

        await fireEvent.click(actionIn(row, 'cancel-setup'));

        const dialog = await confirmation();
        // These are keys from this file's identity translator, not catalogue text.
        expect(screen.getByTestId('users-confirm')).toHaveTextContent(CANCEL_SETUP.title);
        expect(within(dialog).getByTestId('confirm-modal-message')).toHaveTextContent(CANCEL_SETUP.message);
        const confirm = within(dialog).getByTestId('confirm-modal-confirm');
        expect(confirm).toHaveTextContent(CANCEL_SETUP.confirm);
        // A feature assertion of the contract, selection by test id: the danger is the subject, and ConfirmModal publishes it only so.
        expect(confirm).toHaveClass('btn-danger');
        expectNothingWritten();
    });

    // red until A-43
    it('UTAB-56: confirmed — one PATCH {is_active: false} for that account and no other write; the row is the answer, still waiting; accounts.user.setup-cancelled, with a success toast naming the account', async () => {
        await mount(WITH_WAITING_ADMIN);
        const row = await openPanel(WAITING_ADMIN.id);

        await fireEvent.click(actionIn(row, 'cancel-setup'));
        await confirmation();
        expect(patchUser(), 'nothing is sent before the confirmation').not.toHaveBeenCalled();
        await acceptConfirmation();

        await waitFor(() => expect(patchUser()).toHaveBeenCalledTimes(1));
        const [body, options] = patchUser().mock.calls[0];
        // Since A-51 the body also says it cancels (`cancel_setup: true`): its exact shape is UTAB-61's subject.
        expect(body, 'a deactivation is how a waiting administrator’s link is revoked').toEqual(expect.objectContaining({is_active: false}));
        expect(options, 'the options come second: (body, {params})').toEqual(expect.objectContaining({params: {user_id: WAITING_ADMIN.id}}));
        const note = await oneNote('accounts.user.setup-cancelled');
        expect(note.detail).toEqual(expect.objectContaining({user_id: WAITING_ADMIN.id}));
        // The link stops working out of sight, so a toast is owed: a field of the same call. Its message is the key (the
        // identity translator); the values that key was given are read from the translator's own calls.
        expect(note.toast, 'one notification, two halves').toEqual(expect.objectContaining({variant: 'success', message: SETUP_CANCELLED_TOAST}));
        expect(translator(), 'the toast names the account').toHaveBeenCalledWith(SETUP_CANCELLED_TOAST, expect.objectContaining({values: {username: WAITING_ADMIN.username}}));
        await waitFor(() => expect(screen.queryByTestId('users-confirm')).not.toBeInTheDocument());
        await settled();

        // The answer keeps it waiting — its link is revoked, not its setup —, whether the tab reloaded or took the answer.
        const after = rowOf(WAITING_ADMIN.id);
        expect(after).toHaveAttribute('data-pending-setup', 'true');
        expect(after).toHaveAttribute('data-active', 'false');
        expect(within(after).getByTestId('users-badge-pending-setup')).toBeInTheDocument();
        expect(patchUser(), 'one PATCH').toHaveBeenCalledTimes(1);
        for (const [route, call] of Object.entries(WRITES)) if (route !== 'PATCH /users/{id}') expect(call(), `${route} was not asked`).not.toHaveBeenCalled();
        expect(notes('accounts.user.deactivated'), 'a cancellation, not announced as a deactivation').toHaveLength(0);
        expect(notes('accounts.action.failed')).toHaveLength(0);
    });

    // red until A-43
    it('UTAB-57: cancelling the confirmation sends nothing, reloads nothing, and the account still waits', async () => {
        await mount(WITH_WAITING_ADMIN);
        const row = await openPanel(WAITING_ADMIN.id);
        const listsBefore = listUsers().mock.calls.length;
        const notesBefore = notify.mock.calls.length;

        await fireEvent.click(actionIn(row, 'cancel-setup'));
        await declineConfirmation();

        expectNothingWritten();
        expect(listUsers().mock.calls.length, 'no reload').toBe(listsBefore);
        expect(notify.mock.calls.length, 'no event').toBe(notesBefore);
        expect(rowOf(WAITING_ADMIN.id)).toHaveAttribute('data-pending-setup', 'true');
    });

    // guard — green today: accountErrors.ts maps PENDING_SETUP since A7b, and a demotion goes through that mapping
    it('UTAB-58: a demotion refused with 409 PENDING_SETUP (a stale row) → that code, the toast worded settings.usersTab.errors.PENDING_SETUP, and the row redrawn as the server has it', async () => {
        patchUser().mockRejectedValue(conflict('PENDING_SETUP'));
        await mount({accounts: [...ACCOUNTS, STALE_WAITING_ADMIN]});
        const row = await openPanel(STALE_WAITING_ADMIN.id);
        // The server knows the account waits; the list on screen predates it.
        Object.assign(onServer(STALE_WAITING_ADMIN.id), {pending_setup: true});
        const listsBefore = listUsers().mock.calls.length;

        await fireEvent.click(actionIn(row, 'demote'));
        await acceptConfirmation();

        const failure = await oneNote('accounts.action.failed');
        expect(failure.detail).toEqual(expect.objectContaining({code: 'PENDING_SETUP', user_id: STALE_WAITING_ADMIN.id, action: expect.any(String)}));
        // The wording is the subject here; through the identity translator it is a key, not a phrase.
        expect(failure.toast).toEqual(expect.objectContaining({variant: 'error', message: 'settings.usersTab.errors.PENDING_SETUP'}));
        expect(notes('accounts.user.demoted'), 'a refusal is not announced as done').toHaveLength(0);
        await waitFor(() => expect(listUsers().mock.calls.length, 'the tab reloads after a refusal too').toBeGreaterThan(listsBefore));
        await waitFor(() => expect(rowOf(STALE_WAITING_ADMIN.id), 'the reloaded row waits').toHaveAttribute('data-pending-setup', 'true'));
    });

    describe('its keys are sentences in the four catalogues', () => {
        const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

        /** The leaf at a dotted key, read from the catalogue itself. */
        function leafOf(catalogue: unknown, key: string): unknown {
            let node = catalogue;
            for (const part of key.split('.')) node = node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined;
            return node;
        }

        /** The ICU arguments a message names, read as `accountErrors.test.ts` reads them: `username` for «Deactivate {username}?». */
        function placeholdersOf(message: string): string[] {
            return [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();
        }

        /** The values `confirmCopy` hands an account's confirmation: the username to its title and message, nothing to its button. */
        const confirmationOf = (name: string): Record<string, string[]> => ({
            [`settings.usersTab.confirm.${name}.title`]: ['username'],
            [`settings.usersTab.confirm.${name}.message`]: ['username'],
            [`settings.usersTab.confirm.${name}.confirm`]: [],
        });

        /** What keeps each key from reaching the user as a sentence: a language without it, or a value the tab does not fill. */
        function defectsOf(keys: Record<string, string[]>): string[] {
            return Object.entries(keys).flatMap(([key, filled]) =>
                Object.entries(CATALOGUES).flatMap(([language, catalogue]) => {
                    const message = leafOf(catalogue, key);
                    if (typeof message !== 'string' || message.trim() === '') return [`${language}: no sentence at ${key}`];
                    return placeholdersOf(message)
                        .filter((name) => !filled.includes(name))
                        .map((name) => `${language}: ${key} names {${name}}, which the tab does not fill`);
                }),
            );
        }

        // guard — the reader's positive control: the keys of the deactivation, and the toast of the sign-out, drawn today
        it('UTAB-59: the keys of the deactivation confirmation and of the sign-out toast are sentences in the four catalogues, naming no value but the username', () => {
            expect(defectsOf({...confirmationOf('deactivate'), 'settings.usersTab.toasts.signedOut': ['username']})).toEqual([]);
        });

        // red until A-43
        it('UTAB-60: the keys of the cancelSetup confirmation and of its toast are sentences in the four catalogues, naming no value but the username', () => {
            expect(defectsOf({...confirmationOf('cancelSetup'), [SETUP_CANCELLED_TOAST]: ['username']})).toEqual([]);
        });
    });

    describe('a cancellation the backend can tell from a deactivation (UTAB-61…62, A-51)', () => {
        const SETUP_COMPLETED_ERROR = 'settings.usersTab.errors.SETUP_COMPLETED';

        // red until A-51
        it('UTAB-61: confirmed — the PATCH says it cancels: exactly {is_active: false, cancel_setup: true}, for that account', async () => {
            await mount(WITH_WAITING_ADMIN);
            const row = await openPanel(WAITING_ADMIN.id);
            const listsBefore = listUsers().mock.calls.length;

            await fireEvent.click(actionIn(row, 'cancel-setup'));
            await acceptConfirmation();

            await waitFor(() => expect(patchUser()).toHaveBeenCalledTimes(1));
            const [body, options] = patchUser().mock.calls[0];
            // The flag is the intent: without it the backend reads a deactivation, and deactivates an administrator whose setup is done.
            expect(body, 'the body is the subject: a deactivation that says it cancels the setup link').toEqual({is_active: false, cancel_setup: true});
            expect(options, 'the options come second: (body, {params})').toEqual(expect.objectContaining({params: {user_id: WAITING_ADMIN.id}}));
            // Rule 19: end on the flow's own end, the tab idle after its reload.
            await waitFor(() => expect(listUsers().mock.calls.length, 'the tab reloads after the action').toBeGreaterThan(listsBefore));
            await settled();
        });

        // red until A-51
        it('UTAB-62: a cancellation refused with 409 SETUP_COMPLETED (the setup was completed meanwhile) → that code, the toast worded settings.usersTab.errors.SETUP_COMPLETED, no success, and the row redrawn as the server has it', async () => {
            patchUser().mockRejectedValue(conflict('SETUP_COMPLETED'));
            await mount(WITH_WAITING_ADMIN);
            const row = await openPanel(WAITING_ADMIN.id);
            // The administrator completed its setup after this list was drawn: the server has it active, waiting for nothing.
            Object.assign(onServer(WAITING_ADMIN.id), {is_active: true, pending_setup: false});
            const listsBefore = listUsers().mock.calls.length;

            await fireEvent.click(actionIn(row, 'cancel-setup'));
            await acceptConfirmation();

            await waitFor(() => expect(patchUser(), 'the PATCH is what was refused').toHaveBeenCalledTimes(1));
            const failure = await oneNote('accounts.action.failed');
            expect(failure.detail).toEqual(expect.objectContaining({code: 'SETUP_COMPLETED', user_id: WAITING_ADMIN.id, action: expect.any(String)}));
            // The wording is the subject here; through the identity translator it is a key, not a phrase.
            expect(failure.toast).toEqual(expect.objectContaining({variant: 'error', message: SETUP_COMPLETED_ERROR}));
            expect(notes('accounts.user.setup-cancelled'), 'a refusal is not announced as done').toHaveLength(0);
            // The failure above is the barrier: one action ends in success or in failure, never both.
            expect(
                notify.mock.calls.map(([note]) => (note as Note).toast?.variant),
                'no success toast',
            ).not.toContain('success');
            await waitFor(() => expect(listUsers().mock.calls.length, 'the tab reloads after a refusal too').toBeGreaterThan(listsBefore));
            await waitFor(() => expect(rowOf(WAITING_ADMIN.id), 'the reloaded row waits no more').toHaveAttribute('data-pending-setup', 'false'));
            expect(rowOf(WAITING_ADMIN.id), 'it is active, as the server has it').toHaveAttribute('data-active', 'true');
            await settled();
        });
    });
});

// =========================================================================
// N69c (release 1.3, workstream A — decision D5 b of 19/10/2026, D6 only the mode, D7 beside «Invite»): who can sign up,
// from the Users tab. The mode is the global setting `registration_mode`; this control and the Global settings one are the
// same source (`registrationMode.ts`, `registrationMode.test.ts`). The control sits in the first section, next to the
// invitation button, and saves at the choice — no «Save» button —, asking first only for `open`: it lets in anyone who
// reaches the login page. Published on `users-registration`: `data-mode` (the mode in force, from the public configuration),
// `data-shown` (what the select shows), `data-locked` (`LIBREFOLIO_REGISTRATION` pins it), `data-saving`. The select is
// `users-registration-mode` (its trigger `…-button`, its options `users-registration-option-<mode>`), the confirmation
// `users-confirm`, the tab's own (buttons `confirm-modal-confirm` / `confirm-modal-cancel`), the line naming the variable
// `users-registration-locked`. Red until N69c, every case below.
describe('UsersTab — who can sign up, from here (UTAB-63…72, N69c)', () => {
    const registration = (mode: 'open' | 'invite' | 'disabled', locked = false): void => {
        instance.box.config = {profile: 'selfhosted', accounts: {registration_mode: mode, registration_locked: locked}};
    };
    const control = () => screen.getByTestId('users-registration');

    /** Opens the select and picks a mode, as a person does. */
    async function choose(mode: 'open' | 'invite' | 'disabled'): Promise<void> {
        await fireEvent.click(screen.getByTestId('users-registration-mode-button'));
        await fireEvent.click(await screen.findByTestId(`users-registration-option-${mode}`));
    }

    const bulkBody = (mode: string) => ({items: [{key: 'registration_mode', value: mode}]});

    it('UTAB-63: shows the mode in force, in the first section beside «Invite», and follows the configuration while on screen', async () => {
        registration('invite');
        await mount();

        expect(control()).toHaveAttribute('data-mode', 'invite');
        expect(control()).toHaveAttribute('data-shown', 'invite');
        expect(control()).toHaveAttribute('data-locked', 'false');
        expect(control().closest('section')).toBe(screen.getByTestId('users-invite-button').closest('section'));
        expect(screen.queryByTestId('users-registration-locked')).not.toBeInTheDocument();

        registration('disabled');

        await waitFor(() => expect(control()).toHaveAttribute('data-mode', 'disabled'));
        expect(control()).toHaveAttribute('data-shown', 'disabled');
    });

    it.each([
        {id: 'UTAB-64', from: 'invite', to: 'disabled'},
        {id: 'UTAB-65', from: 'open', to: 'invite'},
        {id: 'UTAB-66', from: 'disabled', to: 'invite'},
    ] as const)('$id: $from → $to saves at the choice — one bulk PATCH, the configuration read again, no confirmation, an event and no toast', async ({from, to}) => {
        registration(from);
        await mount();
        const loads = instance.load.mock.calls.length;

        await choose(to);

        await waitFor(() => expect(bulkPatch()).toHaveBeenCalledTimes(1));
        expect(bulkPatch()).toHaveBeenCalledWith('/api/v1/settings/global/bulk', bulkBody(to));
        await waitFor(() => expect(instance.load.mock.calls.length).toBeGreaterThan(loads));
        expect(instance.load).toHaveBeenLastCalledWith({force: true});
        expect(screen.queryByTestId('users-confirm')).not.toBeInTheDocument();
        const note = await oneNote('settings.global.saved');
        expect(note.detail).toEqual({keys: ['registration_mode'], count: 1});
        expect(note.toast, 'the select already shows the new mode: no toast').toBeUndefined();
    });

    it('UTAB-67: «open» asks first — a confirmation, nothing sent — and confirmed saves it', async () => {
        registration('invite');
        await mount();

        await choose('open');

        await confirmation();
        expect(bulkPatch()).not.toHaveBeenCalled();
        expect(control()).toHaveAttribute('data-mode', 'invite');

        await acceptConfirmation();

        await waitFor(() => expect(bulkPatch()).toHaveBeenCalledWith('/api/v1/settings/global/bulk', bulkBody('open')));
        expect(bulkPatch()).toHaveBeenCalledTimes(1);
        await waitFor(() => expect(screen.queryByTestId('users-confirm')).not.toBeInTheDocument());
        await oneNote('settings.global.saved');
    });

    it('UTAB-68: the confirmation of «open» is not a danger one, and cancelling it sends nothing and puts the select back on the mode in force', async () => {
        registration('disabled');
        await mount();

        await choose('open');

        const dialog = await confirmation();
        expect(within(dialog).getByTestId('confirm-modal-confirm').className).not.toContain('btn-danger');
        expect(control()).toHaveAttribute('data-shown', 'open');

        await declineConfirmation();

        expect(bulkPatch()).not.toHaveBeenCalled();
        expect(notes('settings.global.saved')).toHaveLength(0);
        await waitFor(() => expect(control()).toHaveAttribute('data-shown', 'disabled'));
        expect(control()).toHaveAttribute('data-mode', 'disabled');
    });

    it('UTAB-69: pinned by LIBREFOLIO_REGISTRATION — the select is off, shows the mode in force, and the line names the variable', async () => {
        registration('invite', true);
        await mount();

        expect(control()).toHaveAttribute('data-locked', 'true');
        expect(control()).toHaveAttribute('data-shown', 'invite');
        expect(screen.getByTestId('users-registration-mode-button')).toBeDisabled();
        expect(screen.getByTestId('users-registration-locked')).toBeInTheDocument();
        const asked = translator().mock.calls.filter(([key]) => key === 'settings.lockedByEnv');
        expect(asked.at(-1)?.[1], 'the line is given the variable').toEqual({values: {variable: 'LIBREFOLIO_REGISTRATION'}});
        expect(bulkPatch()).not.toHaveBeenCalled();
    });

    it('UTAB-70: a save the server refuses with 409 SETTING_LOCKED_BY_ENV (a configuration read before the pin) — the variable named in an error toast, the select back on the mode in force, the configuration read again', async () => {
        registration('invite');
        await mount();
        bulkPatch().mockRejectedValue(conflict('SETTING_LOCKED_BY_ENV', {variable: 'LIBREFOLIO_REGISTRATION'}));
        const loads = instance.load.mock.calls.length;

        await choose('disabled');

        const note = await oneNote('accounts.registration.failed');
        expect(note.toast?.variant).toBe('error');
        expect(note.detail).toMatchObject({code: 'SETTING_LOCKED_BY_ENV'});
        expect(notes('settings.global.saved')).toHaveLength(0);
        await waitFor(() => expect(control()).toHaveAttribute('data-shown', 'invite'));
        expect(instance.load.mock.calls.length, 'the pin is learnt from the server').toBeGreaterThan(loads);
        const asked = translator().mock.calls.filter(([key]) => key === 'settings.lockedByEnv');
        expect(asked.at(-1)?.[1]).toEqual({values: {variable: 'LIBREFOLIO_REGISTRATION'}});
    });

    it('UTAB-71: any other refusal — an error toast worded by settings.usersTab.registration.saveFailed, the select back on the mode in force, nothing announced as saved', async () => {
        registration('invite');
        await mount();
        bulkPatch().mockRejectedValue(refusal(500, 'boom'));

        await choose('disabled');

        const note = await oneNote('accounts.registration.failed');
        expect(note.toast).toEqual({variant: 'error', message: 'settings.usersTab.registration.saveFailed'});
        expect(notes('settings.global.saved')).toHaveLength(0);
        await waitFor(() => expect(control()).toHaveAttribute('data-shown', 'invite'));
        expect(control()).toHaveAttribute('data-mode', 'invite');
    });

    it('UTAB-72: while the save runs the select is off and the control says so; once done, it is usable again', async () => {
        registration('invite');
        await mount();
        const pending = deferred<{data: null}>();
        bulkPatch().mockReturnValue(pending.promise);

        await choose('disabled');

        await waitFor(() => expect(control()).toHaveAttribute('data-saving', 'true'));
        expect(screen.getByTestId('users-registration-mode-button')).toBeDisabled();

        pending.resolve({data: null});

        await waitFor(() => expect(control()).toHaveAttribute('data-saving', 'false'));
        expect(screen.getByTestId('users-registration-mode-button')).toBeEnabled();
    });

    describe('its keys are sentences in the four catalogues', () => {
        const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};
        /** Each key, and the values the tab fills into it. */
        const KEYS: Record<string, string[]> = {
            'settings.usersTab.registration.label': [],
            'settings.usersTab.registration.confirm.title': [],
            'settings.usersTab.registration.confirm.message': [],
            'settings.usersTab.registration.confirm.confirm': [],
            'settings.usersTab.registration.saveFailed': [],
        };

        const leafOf = (catalogue: unknown, key: string): unknown => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);

        it('UTAB-73: every key is a non-empty sentence in en, it, fr and es, naming no value the tab does not fill', () => {
            const defects = Object.entries(KEYS).flatMap(([key, filled]) =>
                Object.entries(CATALOGUES).flatMap(([language, catalogue]) => {
                    const message = leafOf(catalogue, key);
                    if (typeof message !== 'string' || message.trim() === '') return [`${language}: no sentence at ${key}`];
                    return [...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)]
                        .map((match) => match[1])
                        .filter((name) => !filled.includes(name))
                        .map((name) => `${language}: ${key} names {${name}}`);
                }),
            );
            expect(defects).toEqual([]);
        });
    });
});
