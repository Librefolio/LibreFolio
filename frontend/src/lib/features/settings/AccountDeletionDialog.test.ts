// @vitest-environment jsdom
/**
 * AccountDeletionDialog — component test (Vitest + jsdom). Accounts lot A6b (plan A6b.1).
 *
 * The dialog both doors to account deletion open: the user's own, from the Profile tab (`mode="self"`,
 * `testIdPrefix="profile-delete"`), and an administrator's, from the Users tab (`mode="admin"`,
 * `testIdPrefix="users-delete"`). On opening it asks the server what the deletion would take — the brokers that go
 * with their transactions, those where only the account's access goes, the transfers left unpaired — and it deletes
 * only once the account's username has been typed back exactly. In admin mode, for an active account, it also offers
 * to deactivate instead, which keeps everything and can be undone.
 *
 * Why a component test. Every branch is decided by a prop or by one answer of the server: the mode, whether the
 * account is active, the preview's lists, a 409 and its `error_code`, a 500 that deleted nothing. Through a browser
 * each of those is an administrator to refuse, a protected account, a deletion made to fail half-way; here each is one
 * `mockResolvedValue` or `mockRejectedValue`. The round trip itself stays with the E2E
 * (`e2e/brokers/account-deletion.spec.ts` for the own account; the admin flow is planned in
 * `e2e/settings/admin-users.spec.ts`, plan A6b.1 E1).
 *
 * Red until A6b lands: `AccountDeletionDialog.svelte` does not exist yet, so this file fails at its import.
 *
 * The prefix `p` is a prop, so every lookup below is `${p}-…` — and always inside `${p}-dialog`: the E2E finds the
 * input and the button through the dialog, so that nesting is part of the contract.
 *
 * What it asserts on: testids and their `data-*`, `disabled`, which zodios alias was called and with which `params`,
 * and the callbacks (`onClose`, `onDeleted`, `onDeactivate`). `$lib/i18n`'s translator is the identity, so whatever
 * the dialog writes renders as its key, and nothing below reads it: the UI ships in four languages. Two exceptions,
 * ADEL-28 and its control ADEL-29: there the translator is svelte-i18n's own over the real catalogues, and the case
 * reads which sentence is shown — compared with the catalogue's message for the key, never with a sentence written in
 * this file.
 *
 * Accounts lot A-16 (release 1.3, workstream A — «A-11 + A-16 + A-40 + A-26 as one lot: GO, reds first», 17/10):
 * `DELETE /auth/users/me` refuses the last active administrator with 400, which until A-16 carried a bare English
 * sentence and no code, and the dialog showed that sentence as it was. Since A-16 the body is
 * `{detail: {error_code: 'LAST_ADMIN', message}}`; `LAST_ADMIN`'s own sentence speaks of a deactivation or a demotion,
 * so on a deletion the dialog shows the key `settings.usersTab.errors.LAST_ADMIN_DELETION` instead
 * (`users/accountErrors.test.ts`, AERR-15…17). ADEL-28, through the Profile tab's door and in each of the four
 * languages: the error (`data-error-code="LAST_ADMIN"`) shows that key's sentence in the UI language — neither the
 * server's English nor `LAST_ADMIN`'s —, the error toast says the same, and the dialog stays open with nothing reported
 * deleted. Red until A-16: the key is in no catalogue, and the dialog shows `LAST_ADMIN`'s sentence. ADEL-29, green
 * today, is the positive control of that reader: the same door refused with a key the catalogues already have (the 500
 * `DELETION_FAILED`) shows its sentence in each language, in the error and in the toast — so a red of ADEL-28 is about
 * `LAST_ADMIN` on a deletion, never about the harness.
 *
 * What it deliberately does NOT assert:
 *   - the events (`accounts.user.deleted`, `accounts.action.failed`) and what `onDeleted(result)` carries: the
 *     contract does not say whether the dialog or the tab around it publishes them. `notify` is mocked so that no
 *     toast store is touched; ADEL-28/29 read only the variant and the text of the toasts they raised.
 *   - the wording behind an error: `data-error-code` is the contract, the wording is the catalogue's (ADEL-28/29 read
 *     which message of the catalogue is shown, not what it says).
 *   - ModalBase's focus trap and scroll lock: ModalBase.test.ts owns them (and `browser` is false under Vitest).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

// --- Mocks --------------------------------------------------------------

/** Which translator the dialog gets: the identity, unless a case reads the catalogues (`readTheCatalogues`, ADEL-28/29). */
const translation = vi.hoisted(() => ({catalogues: false}));

// The identity translator: a label renders as its own key. The rest of `$lib/i18n` is the real module, whatever
// else of it the dialog reads. `translation.catalogues` is read at every call: switched on, the key goes to
// svelte-i18n's own translator instead, over the real catalogues — for ADEL-28/29 only, and off again after every case.
vi.mock('$lib/i18n', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/i18n')>();
    const {derived} = await import('svelte/store');
    const translator = derived(actual._, (format) => (key: string, options?: Parameters<typeof format>[1]) => (translation.catalogues ? format(key, options) : key));
    return {...actual, _: translator, t: translator};
});

// Every zodios alias is a lazily created `vi.fn`, as in ProfileTab.test.ts: the four this file cares about are
// looked up by name below, any other the dialog reaches answers `undefined`.
vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
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
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}, schemas: {}};
});

const notify = vi.fn();
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: (...args: unknown[]) => notify(...args)}));

import AccountDeletionDialog from './AccountDeletionDialog.svelte';
import {zodiosApi} from '$lib/api';
// The real catalogues, read only by ADEL-28/29: every other case renders through the identity translator above.
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

// --- Fixtures -----------------------------------------------------------

type Account = {id: number; username: string; is_active: boolean};

type Preview = {
    user_id: number;
    username: string;
    brokers_deleted: {id: number; name: string; transactions: number}[];
    brokers_left: {id: number; name: string; role: string}[];
    transfers_unpaired: number;
};

/** The props of the contract (plan A6b.1), written out so that a drift in the component shows up here. */
type DialogProps = {
    open: boolean;
    mode: 'self' | 'admin';
    account: Account;
    testIdPrefix: string;
    onClose: () => void;
    onDeleted: (result: unknown) => void;
    onDeactivate?: () => void | Promise<void>;
};

const ownPreview = () => vi.mocked(zodiosApi.preview_own_account_deletion_api_v1_auth_users_me_deletion_preview_get as never) as ReturnType<typeof vi.fn>;
const accountPreview = () => vi.mocked(zodiosApi.preview_account_deletion_api_v1_users__user_id__deletion_preview_get as never) as ReturnType<typeof vi.fn>;
const deleteOwn = () => vi.mocked(zodiosApi.delete_own_account_api_v1_auth_users_me_delete as never) as ReturnType<typeof vi.fn>;
const deleteAccount = () => vi.mocked(zodiosApi.delete_account_api_v1_users__user_id__delete as never) as ReturnType<typeof vi.fn>;

/** One door to the dialog: its mode, the prefix its caller gives, the account, and the two aliases it must use. */
interface Mode {
    mode: 'self' | 'admin';
    prefix: string;
    account: Account;
    /** The preview this mode asks for on opening. */
    preview: () => ReturnType<typeof vi.fn>;
    /** The deletion this mode sends. */
    remove: () => ReturnType<typeof vi.fn>;
}

/** The Profile tab's door: the signed-in user deleting their own account. */
const SELF: Mode = {mode: 'self', prefix: 'profile-delete', account: {id: 5, username: 'alice', is_active: true}, preview: ownPreview, remove: deleteOwn};
/** The Users tab's door: an administrator deleting another, active account. */
const ADMIN: Mode = {mode: 'admin', prefix: 'users-delete', account: {id: 42, username: 'carol', is_active: true}, preview: accountPreview, remove: deleteAccount};
const MODES: Mode[] = [SELF, ADMIN];

/**
 * What a deletion would take, as `GET …/deletion-preview` answers. Three items per list, chosen so that the order
 * received matches no sort of them — by id, by name, by transaction count or by role, ascending or descending —
 * and a dialog that re-sorts renders an order this file does not expect.
 */
function previewOf(account: Account, over: Partial<Preview> = {}): Preview {
    return {
        user_id: account.id,
        username: account.username,
        brokers_deleted: [
            {id: 31, name: 'Zeta Savings', transactions: 3},
            {id: 7, name: 'Alpha Trading', transactions: 40},
            {id: 12, name: 'Mid Broker', transactions: 15},
        ],
        brokers_left: [
            {id: 9, name: 'Zulu Family', role: 'EDITOR'},
            {id: 4, name: 'Alpha Club', role: 'VIEWER'},
            {id: 6, name: 'Mid Fund', role: 'OWNER'},
        ],
        transfers_unpaired: 2,
        ...over,
    };
}

/** The backend's 409 refusals of `DELETE /users/{id}`, `detail` as `backend/app/api/v1/users.py` writes it. */
const REFUSALS = [
    {code: 'SELF_DELETION', detail: {error_code: 'SELF_DELETION', message: 'Delete your own account from your profile'}},
    {code: 'DEMOTE_FIRST', detail: {error_code: 'DEMOTE_FIRST', message: 'An administrator must be demoted before it can be deleted'}},
    {code: 'ACCOUNT_PROTECTED', detail: {error_code: 'ACCOUNT_PROTECTED', message: 'This account cannot be deleted, deactivated or demoted', reason: 'instance-owner'}},
];

/** Both deletion endpoints answer 500 with this when the all-or-nothing deletion rolled back. */
const NOTHING_DELETED = {detail: 'Account deletion failed: nothing was deleted'};

/**
 * `DELETE /auth/users/me` refusing the last active administrator, `detail` as `backend/app/api/v1/auth.py` writes it
 * since A-16: the status stays 400, the detail gains a code (until A-16 it was a bare sentence).
 */
const LAST_ADMIN_REFUSAL = {error_code: 'LAST_ADMIN', message: 'Cannot delete account: you are the last active administrator'};
/** What a deletion refused with `LAST_ADMIN` shows since A-16: a key of its own, made for a deletion. */
const LAST_ADMIN_DELETION_KEY = 'settings.usersTab.errors.LAST_ADMIN_DELETION';
/** `LAST_ADMIN`'s key in the Users tab, for a deactivation or a demotion: not what a deletion says. */
const LAST_ADMIN_KEY = 'settings.usersTab.errors.LAST_ADMIN';

/** The catalogues of the four languages the UI ships, as the build generates them. */
const CATALOGUES = {en, it: itCatalogue, fr, es};
type UiLanguage = keyof typeof CATALOGUES;
const UI_LANGUAGES = Object.keys(CATALOGUES) as UiLanguage[];

// --- Helpers ------------------------------------------------------------

/** An axios-shaped rejection: what the zodios client rejects with, its response body included. */
function httpError(status: number, body: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, response: {status, data: body}});
}

/** A promise this test settles by hand, so "in flight" is a state it controls. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/**
 * Mounts the dialog, open by default, as `m`'s caller would. Callbacks passed in `over` replace the default spies:
 * a test that passes its own asserts on its own references.
 */
function mountDialog(m: Mode, over: Partial<DialogProps> = {}) {
    const onClose = vi.fn();
    const onDeleted = vi.fn();
    const onDeactivate = vi.fn();
    const props: DialogProps = {open: true, mode: m.mode, account: m.account, testIdPrefix: m.prefix, onClose, onDeleted, onDeactivate, ...over};
    const {rerender} = render(AccountDeletionDialog, props);
    const p = props.testIdPrefix;
    const dialog = () => screen.getByTestId(`${p}-dialog`);
    return {
        p,
        onClose,
        onDeleted,
        onDeactivate,
        rerender,
        dialog,
        /** `${p}-<name>`, inside the dialog; throws when it is not there. */
        part: (name: string) => within(dialog()).getByTestId(`${p}-${name}`),
        partOrNull: (name: string) => within(dialog()).queryByTestId(`${p}-${name}`),
        parts: (name: string) => within(dialog()).queryAllByTestId(`${p}-${name}`),
    };
}

type Ui = ReturnType<typeof mountDialog>;

/**
 * Waits until the preview asked on opening has been answered and the dialog says it is no longer busy. Both halves:
 * `data-busy="false"` alone is also what a dialog may show before it has even started loading, and an initial state
 * is not a barrier.
 */
async function settled(ui: Ui, source: ReturnType<typeof vi.fn>): Promise<void> {
    await waitFor(() => {
        expect(source).toHaveBeenCalled();
        expect(source.mock.settledResults.at(-1)?.type).not.toBe('incomplete');
        expect(ui.dialog()).toHaveAttribute('data-busy', 'false');
    });
}

async function typeInto(input: HTMLElement, value: string): Promise<void> {
    await fireEvent.input(input, {target: {value}});
}

/** Types the username back and waits for the confirmation to arm. */
async function arm(ui: Ui, username: string): Promise<void> {
    await typeInto(ui.part('confirm-input'), username);
    await waitFor(() => expect(ui.part('confirm')).toBeEnabled());
}

/** The given attributes of each element, in document order. */
function attrs(elements: HTMLElement[], ...names: string[]): (string | null)[][] {
    return elements.map((element) => names.map((name) => element.getAttribute(name)));
}

/** The failure paths below are provoked on purpose, and the dialog may log them: the noise is muted, not read. */
function muteErrorLog(): void {
    vi.spyOn(console, 'error').mockImplementation(() => {});
}

/** The message at a dotted key of `language`'s catalogue, read from the catalogue itself; `undefined` when it has none. */
function sentenceOf(language: UiLanguage, key: string): string | undefined {
    let node: unknown = CATALOGUES[language];
    for (const part of key.split('.')) node = node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined;
    return typeof node === 'string' ? node : undefined;
}

/**
 * For the case that calls it, the dialog's labels go through svelte-i18n over the real catalogues, in `language`: the
 * UI language of that case. The `afterEach` below switches back to the identity.
 */
async function readTheCatalogues(language: UiLanguage): Promise<void> {
    await setupI18n(language);
    translation.catalogues = true;
}

/** What an element says: its text, without the indentation of the markup around it. */
function textOf(element: HTMLElement): string {
    return (element.textContent ?? '').trim();
}

/** The texts of the toasts of `variant` the dialog raised, in order: `notify` is reset before every case. */
function toastTexts(variant: string): unknown[] {
    return notify.mock.calls
        .map(([notification]) => (notification as {toast?: {variant?: string; message?: unknown}} | undefined)?.toast)
        .filter((toast) => toast?.variant === variant)
        .map((toast) => toast?.message);
}

beforeEach(() => {
    // `reset`, not `clear`: a `mockRejectedValueOnce` left unconsumed must not leak into the next test.
    vi.resetAllMocks();
    ownPreview().mockResolvedValue(previewOf(SELF.account));
    accountPreview().mockResolvedValue(previewOf(ADMIN.account));
    deleteOwn().mockResolvedValue({message: 'Account deleted successfully'});
    // DELETE /users/{id} answers 204: zodios resolves `undefined`.
    deleteAccount().mockResolvedValue(undefined);
});

afterEach(() => {
    vi.restoreAllMocks();
    // Every case starts on the identity translator: ADEL-28/29 switch to the catalogues for themselves only.
    translation.catalogues = false;
});

// =========================================================================
describe('AccountDeletionDialog — opening, and the preview it asks for', () => {
    it('ADEL-01: renders nothing and asks nothing while closed; opening it asks for the preview, once', async () => {
        const ui = mountDialog(SELF, {open: false});

        expect(screen.queryByTestId('profile-delete-dialog')).toBeNull();
        // ProfileTab finds its other confirmation by role: a closed dialog must not leave one in the page.
        expect(screen.queryByRole('dialog')).toBeNull();
        expect(ownPreview()).not.toHaveBeenCalled();
        expect(accountPreview()).not.toHaveBeenCalled();

        await ui.rerender({open: true});

        await settled(ui, ownPreview());
        expect(ownPreview()).toHaveBeenCalledTimes(1);
    });

    it('ADEL-02: in self mode asks for the own preview, never for an account by id', async () => {
        const ui = mountDialog(SELF);

        await settled(ui, ownPreview());

        expect(ownPreview()).toHaveBeenCalledTimes(1);
        expect(accountPreview()).not.toHaveBeenCalled();
    });

    it("ADEL-03: in admin mode asks for that account's preview, by its id", async () => {
        const ui = mountDialog(ADMIN);

        await settled(ui, accountPreview());

        expect(accountPreview()).toHaveBeenCalledTimes(1);
        expect(accountPreview()).toHaveBeenCalledWith(expect.objectContaining({params: {user_id: 42}}));
        expect(ownPreview()).not.toHaveBeenCalled();
    });

    it.each(MODES)('ADEL-04 ($mode): publishes data-busy="true" while the preview is in flight, "false" once it has landed', async (m) => {
        const pending = deferred<Preview>();
        m.preview().mockReturnValue(pending.promise);
        const ui = mountDialog(m);

        await waitFor(() => expect(ui.dialog()).toHaveAttribute('data-busy', 'true'));
        expect(ui.parts('broker-deleted')).toHaveLength(0);

        pending.resolve(previewOf(m.account));

        await waitFor(() => {
            expect(ui.dialog()).toHaveAttribute('data-busy', 'false');
            expect(ui.parts('broker-deleted')).toHaveLength(3);
        });
    });

    // The two prefixes of the contract, and one no caller uses: a dialog that derived its testids from the mode
    // instead of reading the prop would pass the first two and fail the third.
    const PREFIXED: Mode[] = [SELF, ADMIN, {...ADMIN, prefix: 'audit-del'}];
    const PREFIXES = PREFIXED.map((m) => m.prefix);

    it.each(PREFIXED)('ADEL-05 ($mode, $prefix): every part carries the prefix it is given, and no other', async (m) => {
        const ui = mountDialog(m);
        await settled(ui, m.preview());

        for (const name of ['preview', 'unpaired', 'confirm-input', 'confirm', 'cancel']) expect(ui.part(name)).toBeInTheDocument();
        expect(ui.parts('broker-deleted')).toHaveLength(3);
        expect(ui.parts('broker-left')).toHaveLength(3);
        if (m.mode === 'admin') expect(ui.part('deactivate')).toBeInTheDocument();
        // Nothing has failed yet, so there is no error to show.
        expect(ui.partOrNull('error')).toBeNull();

        const foreign = Array.from(document.body.querySelectorAll('[data-testid]'))
            .map((element) => element.getAttribute('data-testid') ?? '')
            .filter((testId) => PREFIXES.some((other) => other !== m.prefix && testId.startsWith(`${other}-`)));
        expect(foreign).toEqual([]);
    });
});

// =========================================================================
describe('AccountDeletionDialog — the preview', () => {
    it.each(MODES)('ADEL-06 ($mode): lists the brokers that go, in the order received, each with its id and its transaction count', async (m) => {
        const ui = mountDialog(m);
        await settled(ui, m.preview());

        const items = within(ui.part('preview')).getAllByTestId(`${ui.p}-broker-deleted`);

        expect(attrs(items, 'data-broker-id', 'data-transactions')).toEqual([
            ['31', '3'],
            ['7', '40'],
            ['12', '15'],
        ]);
    });

    it.each(MODES)('ADEL-07 ($mode): lists the brokers only left, in the order received, each with its id and the role that goes', async (m) => {
        const ui = mountDialog(m);
        await settled(ui, m.preview());

        const items = within(ui.part('preview')).getAllByTestId(`${ui.p}-broker-left`);

        expect(attrs(items, 'data-broker-id', 'data-role')).toEqual([
            ['9', 'EDITOR'],
            ['4', 'VIEWER'],
            ['6', 'OWNER'],
        ]);
    });

    it.each(MODES)('ADEL-08 ($mode): says how many transfers are left unpaired when there are some', async (m) => {
        const ui = mountDialog(m);
        await settled(ui, m.preview());

        expect(within(ui.part('preview')).getByTestId(`${ui.p}-unpaired`)).toHaveAttribute('data-count', '2');
    });

    it.each(MODES)('ADEL-09 ($mode): says nothing about unpaired transfers when there are none', async (m) => {
        m.preview().mockResolvedValue(previewOf(m.account, {transfers_unpaired: 0}));
        const ui = mountDialog(m);
        await settled(ui, m.preview());

        // The preview did render — its lists are there — and only the unpaired line is missing.
        expect(ui.parts('broker-deleted')).toHaveLength(3);
        expect(ui.partOrNull('unpaired')).toBeNull();
    });

    it.each(MODES)('ADEL-10 ($mode): an account with nothing to take lists nothing, and can still be deleted', async (m) => {
        m.preview().mockResolvedValue(previewOf(m.account, {brokers_deleted: [], brokers_left: [], transfers_unpaired: 0}));
        const ui = mountDialog(m);
        await settled(ui, m.preview());

        expect(ui.part('confirm-input')).toBeInTheDocument();
        expect(ui.parts('broker-deleted')).toHaveLength(0);
        expect(ui.parts('broker-left')).toHaveLength(0);
        expect(ui.partOrNull('unpaired')).toBeNull();

        // An empty preview is an answer, not a failure: the typed name still arms the deletion.
        await arm(ui, m.account.username);
    });
});

// =========================================================================
describe('AccountDeletionDialog — deactivate instead', () => {
    it('ADEL-11: in admin mode, for an active account, deactivating needs no typed name, calls onDeactivate then onClose, and deletes nothing', async () => {
        const calls: string[] = [];
        const onDeactivate = vi.fn(() => void calls.push('deactivate'));
        const onClose = vi.fn(() => void calls.push('close'));
        const ui = mountDialog(ADMIN, {onDeactivate, onClose});
        await settled(ui, accountPreview());

        // The way out that keeps everything is not behind the typed confirmation.
        expect(ui.part('confirm')).toBeDisabled();
        expect(ui.part('deactivate')).toBeEnabled();

        await fireEvent.click(ui.part('deactivate'));

        await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
        expect(onDeactivate).toHaveBeenCalledTimes(1);
        expect(calls).toEqual(['deactivate', 'close']);
        expect(deleteAccount()).not.toHaveBeenCalled();
        expect(deleteOwn()).not.toHaveBeenCalled();
        expect(ui.onDeleted).not.toHaveBeenCalled();
    });

    it('ADEL-12: closes only once an asynchronous onDeactivate has finished', async () => {
        const pending = deferred<void>();
        const onDeactivate = vi.fn(() => pending.promise);
        const ui = mountDialog(ADMIN, {onDeactivate});
        await settled(ui, accountPreview());

        await fireEvent.click(ui.part('deactivate'));

        await waitFor(() => expect(onDeactivate).toHaveBeenCalledTimes(1));
        expect(ui.onClose).not.toHaveBeenCalled();

        pending.resolve(undefined);

        await waitFor(() => expect(ui.onClose).toHaveBeenCalledTimes(1));
    });

    it('ADEL-13: never offers it in self mode, even with an onDeactivate at hand', async () => {
        const ui = mountDialog(SELF);
        await settled(ui, ownPreview());

        // The rest of the dialog is there: only the deactivation is missing.
        expect(ui.part('confirm')).toBeInTheDocument();
        expect(ui.part('cancel')).toBeInTheDocument();
        expect(ui.partOrNull('deactivate')).toBeNull();
    });

    it('ADEL-14: never offers it for an account that is already inactive', async () => {
        const ui = mountDialog(ADMIN, {account: {...ADMIN.account, is_active: false}});
        await settled(ui, accountPreview());

        expect(ui.part('confirm')).toBeInTheDocument();
        expect(ui.part('cancel')).toBeInTheDocument();
        expect(ui.partOrNull('deactivate')).toBeNull();
    });
});

// =========================================================================
describe('AccountDeletionDialog — the typed confirmation', () => {
    it.each(MODES)('ADEL-15 ($mode): with nothing typed, the deletion is disabled', async (m) => {
        const ui = mountDialog(m);
        await settled(ui, m.preview());

        expect(ui.part('confirm-input')).toHaveValue('');
        expect(ui.part('confirm')).toBeDisabled();
    });

    // Each case first arms the dialog with the exact name, so "disabled" is a change the dialog made, not the state
    // it started from.
    it.each([' carol', 'carol ', 'CAROL', 'Carol', 'caro', 'carol2'])('ADEL-16: %j is not "carol" — no trimming, no case folding, no prefix: the deletion goes back to disabled', async (typed) => {
        const ui = mountDialog(ADMIN);
        await settled(ui, accountPreview());
        await arm(ui, 'carol');

        await typeInto(ui.part('confirm-input'), typed);

        await waitFor(() => expect(ui.part('confirm')).toBeDisabled());
    });

    it.each(MODES)('ADEL-17 ($mode): the exact username arms the deletion, and arming deletes nothing', async (m) => {
        const ui = mountDialog(m);
        await settled(ui, m.preview());

        await arm(ui, m.account.username);

        expect(m.remove()).not.toHaveBeenCalled();
        expect(ui.onDeleted).not.toHaveBeenCalled();
        // Typing is not opening: the preview was asked once.
        expect(m.preview()).toHaveBeenCalledTimes(1);
    });
});

// =========================================================================
describe('AccountDeletionDialog — confirming', () => {
    it('ADEL-18: in self mode deletes through DELETE /auth/users/me, then reports the deletion', async () => {
        const ui = mountDialog(SELF);
        await settled(ui, ownPreview());
        await arm(ui, 'alice');

        await fireEvent.click(ui.part('confirm'));

        await waitFor(() => expect(ui.onDeleted).toHaveBeenCalledTimes(1));
        expect(deleteOwn()).toHaveBeenCalledTimes(1);
        expect(deleteAccount()).not.toHaveBeenCalled();
    });

    it('ADEL-19: in admin mode deletes through DELETE /users/{id}, with the account id, then reports the deletion', async () => {
        const ui = mountDialog(ADMIN);
        await settled(ui, accountPreview());
        await arm(ui, 'carol');

        await fireEvent.click(ui.part('confirm'));

        await waitFor(() => expect(ui.onDeleted).toHaveBeenCalledTimes(1));
        expect(deleteAccount()).toHaveBeenCalledTimes(1);
        expect(deleteAccount()).toHaveBeenCalledWith(undefined, expect.objectContaining({params: {user_id: 42}}));
        expect(deleteOwn()).not.toHaveBeenCalled();
    });

    it.each(MODES)('ADEL-20 ($mode): while the deletion is in flight the confirmation is disabled, and onDeleted waits for the answer', async (m) => {
        const pending = deferred<unknown>();
        m.remove().mockReturnValue(pending.promise);
        const ui = mountDialog(m);
        await settled(ui, m.preview());
        await arm(ui, m.account.username);

        await fireEvent.click(ui.part('confirm'));

        await waitFor(() => {
            expect(m.remove()).toHaveBeenCalledTimes(1);
            expect(ui.part('confirm')).toBeDisabled();
        });
        expect(ui.onDeleted).not.toHaveBeenCalled();

        pending.resolve(undefined);

        await waitFor(() => expect(ui.onDeleted).toHaveBeenCalledTimes(1));
        expect(m.remove()).toHaveBeenCalledTimes(1);
    });
});

// =========================================================================
describe('AccountDeletionDialog — when the deletion is refused', () => {
    beforeEach(() => {
        muteErrorLog();
    });

    it.each(REFUSALS)('ADEL-21 ($code): a 409 is shown with its code, nothing is reported, and the dialog stays open', async ({code, detail}) => {
        deleteAccount().mockRejectedValue(httpError(409, {detail}));
        const ui = mountDialog(ADMIN);
        await settled(ui, accountPreview());
        await arm(ui, 'carol');

        await fireEvent.click(ui.part('confirm'));

        await waitFor(() => expect(ui.part('error')).toHaveAttribute('data-error-code', code));
        expect(ui.onDeleted).not.toHaveBeenCalled();
        expect(ui.onClose).not.toHaveBeenCalled();
        expect(ui.dialog()).toBeInTheDocument();
    });

    // A5-1 (23/10/2026): the paying administrator of a managed instance may not delete its own account from the profile (409, before the last-administrator rule)
    it('ADEL-21b (self): the 409 ACCOUNT_PROTECTED of the profile deletion is shown with its code, nothing is reported, and the dialog stays open', async () => {
        deleteOwn().mockRejectedValue(httpError(409, {detail: {error_code: 'ACCOUNT_PROTECTED', message: 'This account cannot be deleted from here: ask the host of this instance', reason: 'paying_administrator'}}));
        const ui = mountDialog(SELF);
        await settled(ui, ownPreview());
        await arm(ui, SELF.account.username);

        await fireEvent.click(ui.part('confirm'));

        await waitFor(() => expect(ui.part('error')).toHaveAttribute('data-error-code', 'ACCOUNT_PROTECTED'));
        expect(ui.part('error')).not.toHaveTextContent('ask the host');
        expect(ui.onDeleted).not.toHaveBeenCalled();
        expect(ui.onClose).not.toHaveBeenCalled();
        expect(ui.dialog()).toBeInTheDocument();
    });

    it.each(MODES)('ADEL-22 ($mode): a 500 is DELETION_FAILED — nothing was deleted — and the dialog stays open', async (m) => {
        m.remove().mockRejectedValue(httpError(500, NOTHING_DELETED));
        const ui = mountDialog(m);
        await settled(ui, m.preview());
        await arm(ui, m.account.username);

        await fireEvent.click(ui.part('confirm'));

        await waitFor(() => expect(ui.part('error')).toHaveAttribute('data-error-code', 'DELETION_FAILED'));
        expect(ui.onDeleted).not.toHaveBeenCalled();
        expect(ui.onClose).not.toHaveBeenCalled();
        expect(ui.dialog()).toBeInTheDocument();
    });

    it('ADEL-23: after a refusal the confirmation is still armed, and a retry that succeeds is reported', async () => {
        deleteAccount().mockRejectedValueOnce(httpError(500, NOTHING_DELETED)).mockResolvedValueOnce(undefined);
        const ui = mountDialog(ADMIN);
        await settled(ui, accountPreview());
        await arm(ui, 'carol');
        await fireEvent.click(ui.part('confirm'));
        await waitFor(() => expect(ui.part('error')).toHaveAttribute('data-error-code', 'DELETION_FAILED'));

        // Nothing was deleted, so nothing has to be typed again.
        await waitFor(() => expect(ui.part('confirm')).toBeEnabled());
        expect(ui.part('confirm-input')).toHaveValue('carol');

        await fireEvent.click(ui.part('confirm'));

        await waitFor(() => expect(ui.onDeleted).toHaveBeenCalledTimes(1));
        expect(deleteAccount()).toHaveBeenCalledTimes(2);
    });

    // red until A-16 — the key is in no catalogue yet, and the dialog shows LAST_ADMIN's sentence
    it.each(UI_LANGUAGES)('ADEL-28 (self, %s): refused with the 400 LAST_ADMIN, the error and its toast say settings.usersTab.errors.LAST_ADMIN_DELETION in the UI language — not the server’s sentence, not LAST_ADMIN’s —, and the dialog stays open', async (language) => {
        const expected = sentenceOf(language, LAST_ADMIN_DELETION_KEY);
        expect.soft(expected, `${LAST_ADMIN_DELETION_KEY} is missing from the ${language} catalogue: A-16 adds it to the settings i18n source (src/lib/i18n/settings/${language}.json)`).toEqual(expect.stringMatching(/\S/));
        await readTheCatalogues(language);
        deleteOwn().mockRejectedValue(httpError(400, {detail: LAST_ADMIN_REFUSAL}));
        const ui = mountDialog(SELF);
        await settled(ui, ownPreview());
        await arm(ui, 'alice');

        await fireEvent.click(ui.part('confirm'));

        await waitFor(() => expect(ui.part('error')).toHaveAttribute('data-error-code', 'LAST_ADMIN'));
        const shown = textOf(ui.part('error'));
        expect(shown, 'never the server’s English sentence').not.toContain(LAST_ADMIN_REFUSAL.message);
        expect(shown, `never the ${language} sentence of ${LAST_ADMIN_KEY}, made for a deactivation or a demotion`).not.toBe(sentenceOf(language, LAST_ADMIN_KEY));
        expect(shown, `the ${language} sentence of ${LAST_ADMIN_DELETION_KEY}`).toBe(expected);
        // The error toast says the same, and no success is announced.
        expect(toastTexts('error'), 'the error toast says what the dialog says').toEqual([expected]);
        expect(toastTexts('success')).toEqual([]);
        // Nothing was deleted: the dialog stays open and reports nothing — `onDeleted` is what signs the Profile tab out.
        expect(deleteOwn()).toHaveBeenCalledTimes(1);
        expect(deleteAccount()).not.toHaveBeenCalled();
        expect(ui.onDeleted).not.toHaveBeenCalled();
        expect(ui.onClose).not.toHaveBeenCalled();
        expect(ui.dialog()).toBeInTheDocument();
    });

    // guard — ADEL-28's reader proved on a refusal whose key the catalogues already have: same door, same alias
    it.each(UI_LANGUAGES)('ADEL-29 (self, %s): a refused deletion whose key the catalogues have — the 500 DELETION_FAILED — shows its sentence in the UI language, in the error and in its toast', async (language) => {
        const expected = sentenceOf(language, 'settings.usersTab.errors.DELETION_FAILED');
        expect(expected, `settings.usersTab.errors.DELETION_FAILED is a sentence of the ${language} catalogue`).toEqual(expect.stringMatching(/\S/));
        await readTheCatalogues(language);
        deleteOwn().mockRejectedValue(httpError(500, NOTHING_DELETED));
        const ui = mountDialog(SELF);
        await settled(ui, ownPreview());
        await arm(ui, 'alice');

        await fireEvent.click(ui.part('confirm'));

        await waitFor(() => expect(ui.part('error')).toHaveAttribute('data-error-code', 'DELETION_FAILED'));
        expect(textOf(ui.part('error'))).toBe(expected);
        expect(toastTexts('error')).toEqual([expected]);
    });
});

// =========================================================================
describe('AccountDeletionDialog — when the preview cannot be loaded', () => {
    beforeEach(() => {
        muteErrorLog();
    });

    it.each(MODES)('ADEL-24 ($mode): shows an error, stops being busy, and keeps the deletion disabled even with the exact name typed', async (m) => {
        m.preview().mockRejectedValue(httpError(500, 'Internal Server Error'));
        const ui = mountDialog(m);

        await waitFor(() => expect(ui.part('error')).toBeInTheDocument());
        await waitFor(() => expect(ui.dialog()).toHaveAttribute('data-busy', 'false'));

        // With a preview, this very name arms the deletion (ADEL-17); without one, nobody deletes blind.
        await typeInto(ui.part('confirm-input'), m.account.username);

        expect(ui.part('confirm')).toBeDisabled();
        expect(m.remove()).not.toHaveBeenCalled();
        expect(ui.onDeleted).not.toHaveBeenCalled();
    });
});

// =========================================================================
describe('AccountDeletionDialog — leaving without deleting', () => {
    it.each(MODES)('ADEL-25 ($mode): Cancel closes, even when armed, and deletes nothing', async (m) => {
        const ui = mountDialog(m);
        await settled(ui, m.preview());
        await arm(ui, m.account.username);

        await fireEvent.click(ui.part('cancel'));

        await waitFor(() => expect(ui.onClose).toHaveBeenCalledTimes(1));
        expect(deleteOwn()).not.toHaveBeenCalled();
        expect(deleteAccount()).not.toHaveBeenCalled();
        expect(ui.onDeleted).not.toHaveBeenCalled();
    });

    it.each(MODES)('ADEL-26 ($mode): Escape closes too, and deletes nothing', async (m) => {
        const ui = mountDialog(m);
        await settled(ui, m.preview());
        await arm(ui, m.account.username);

        await fireEvent.keyDown(ui.dialog(), {key: 'Escape'});

        await waitFor(() => expect(ui.onClose).toHaveBeenCalledTimes(1));
        expect(deleteOwn()).not.toHaveBeenCalled();
        expect(deleteAccount()).not.toHaveBeenCalled();
        expect(ui.onDeleted).not.toHaveBeenCalled();
    });

    it("ADEL-27: closed, then opened on another account, it starts over — that account's preview, nothing typed", async () => {
        const dave: Account = {id: 77, username: 'dave', is_active: false};
        const davePreview = previewOf(dave, {brokers_deleted: [{id: 88, name: 'Dave Solo', transactions: 1}], brokers_left: [], transfers_unpaired: 0});
        accountPreview().mockImplementation(async (config?: {params?: {user_id?: number}}) => (config?.params?.user_id === dave.id ? davePreview : previewOf(ADMIN.account)));
        const ui = mountDialog(ADMIN);
        await settled(ui, accountPreview());
        await arm(ui, 'carol');

        await ui.rerender({open: false});
        await waitFor(() => expect(screen.queryByTestId('users-delete-dialog')).toBeNull());
        await ui.rerender({open: true, account: dave});

        await waitFor(() => expect(accountPreview()).toHaveBeenCalledTimes(2));
        expect(accountPreview()).toHaveBeenLastCalledWith(expect.objectContaining({params: {user_id: 77}}));
        await settled(ui, accountPreview());
        // Dave's broker, and none of carol's.
        await waitFor(() => expect(attrs(ui.parts('broker-deleted'), 'data-broker-id')).toEqual([['88']]));
        expect(ui.part('confirm-input')).toHaveValue('');
        expect(ui.part('confirm')).toBeDisabled();
    });
});
