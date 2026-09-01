// @vitest-environment jsdom
/**
 * BrokerSharingPanel — component test (Vitest + jsdom).
 *
 * The panel decides who may see and who may change a broker. It is the UI half of
 * one endpoint whose contract is unusually sharp: the bulk PUT is documented as
 * *"sends the COMPLETE desired access list"* and the server diffs it against what
 * exists, so whatever this panel holds in `accesses` at the moment Save is pressed
 * becomes the whole truth for that broker. Everything below is written with that
 * in mind — most tests end on the body handed to the API, not on what the screen
 * says, because the body is the thing that changes permissions.
 *
 * Why a component test when `e2e/brokers/broker-sharing.spec.ts` already exists:
 * that spec drives the happy path against a live server, and the happy path is not
 * where this file's risk lives. The risk is in the three API calls failing, in the
 * arithmetic of shares, and in the guards — and reaching those through Playwright
 * means a server that refuses on demand, which is not a thing that exists here.
 * With `$lib/api` mocked, a rejected load, a rejected save, a save still in flight
 * and a user search that dies are each one line.
 *
 * The chart is stubbed (`$test/harness/SemiDonutChartStub.svelte`) for two reasons
 * spelled out in that file: ECharts cannot paint in jsdom, and stubbing it turns
 * `chartSlices` — a derivation whose only production consumer is a canvas — into
 * something readable. The E2E already proves a real canvas with a non-zero bitmap.
 *
 * What it deliberately does NOT assert:
 *   - translated text. Role labels, column titles, the confirm sentence and both
 *     button captions come from the four-language catalogue. Rows are addressed by
 *     `access-entry-{user_id}`, state by `data-testid`, and the one error message
 *     asserted verbatim is a string this test itself injected as the API's
 *     `response.data.detail`.
 *   - CSS classes. The colour of a role badge is not a contract; membership of a
 *     column is, and that is read from `sharing-{owners,editors,viewers}-column`.
 *   - the donut's pixels. `data-slices` is the *input* to the chart, nothing more.
 *
 * Two selectors here are weaker than they should be, and both are noted in the
 * report as requests rather than worked around silently: the role dropdown (its
 * trigger and its three options carry no `data-*`, so they are reached by index
 * into `roleOptions`, a constant declared in the source — never data — and every
 * use is immediately verified by its consequence) and the Reset control (reached
 * by `title="Reset"`, which is hard-coded English in the markup, not a catalogue
 * key — that this lookup works at all is itself an i18n gap).
 *
 * Left uncovered on purpose: `$: if (brokerId)` skipping a falsy id (broker ids
 * come from a route and are never 0), and the `readOnly` early-returns inside
 * `handleAddUser` / `startEdit` / `confirmRemove` / `handleSave` — when `readOnly`
 * is set the entire `{#if !readOnly}` block that hosts those controls is never
 * rendered, so the guards have no caller. What *is* asserted is the surface: that
 * a read-only panel offers no way in. The load-failed guards are asserted through
 * their public state (`data-access-state`) and by synthetic save dispatch, because
 * the real button is disabled.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

// --- Mocks --------------------------------------------------------------
// zodiosApi: a Proxy minting a cached spy per method, so `api[NAME]` in a test and
// the call inside the component are the same fn (pattern from AssetModal.test.ts).
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
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));

// $app/navigation: goto is the R3-F4 subject (leave flow navigates on success).
vi.mock('$app/navigation', () => ({goto: vi.fn()}));

// auth: a minimal controllable readable store. Default `user: null` keeps every
// pre-existing test on its current path (no self-service block); the leave
// tests set a user whose id is present in the mounted access list.
const authStore = vi.hoisted(() => {
    type AuthState = {user: {id: number; username: string} | null};
    let value: AuthState = {user: null};
    const subs = new Set<(v: AuthState) => void>();
    return {
        subscribe(fn: (v: AuthState) => void) {
            subs.add(fn);
            fn(value);
            return () => subs.delete(fn);
        },
        set(v: AuthState) {
            value = v;
            for (const fn of subs) fn(value);
        },
    };
});
vi.mock('$lib/stores/app/auth', () => ({auth: authStore}));
vi.mock('$lib/components/charts/SemiDonutChart.svelte', async () => ({
    default: (await import('$test/harness/SemiDonutChartStub.svelte')).default,
}));

import BrokerSharingPanel from './BrokerSharingPanel.svelte';
import BrokerSharingPanelHarness from '$test/harness/BrokerSharingPanelHarness.svelte';
import {zodiosApi} from '$lib/api';
import {goto} from '$app/navigation';
import {toasts} from '$lib/stores/app/toastStore.svelte';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const api = zodiosApi as any;
const gotoMock = vi.mocked(goto);
const LIST = 'list_broker_access_api_v1_brokers__broker_id__access_get';
const SEARCH = 'search_users_endpoint_api_v1_users_search_get';
const PUT = 'bulk_update_broker_access_api_v1_brokers__broker_id__access_put';
const DELETE_ME = 'leave_broker_access_api_v1_brokers__broker_id__access_me_delete';

type Role = 'OWNER' | 'EDITOR' | 'VIEWER';

// =========================================================================
// Fixtures
// =========================================================================

/** One row of the access list, as the API returns it (share is a string there). */
function access(user_id: number, username: string, role: Role, share = 0, avatar_url: string | null = null) {
    return {user_id, username, avatar_url, role, share_percentage: String(share)};
}

/** A promise the test decides when — and whether — to settle. */
function deferred<T>() {
    let resolve!: (v: T) => void;
    let reject!: (e: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** An axios-shaped rejection, which is what `trySave` knows how to read. */
function httpError(detail: string, status = 400) {
    return {response: {data: {detail}, status, statusText: 'Bad Request'}};
}

interface MountOptions {
    accesses?: ReturnType<typeof access>[];
    users?: {id: number; username: string; avatar_url: string | null}[];
    props?: Record<string, unknown>;
}

/**
 * Render the panel with both read calls programmed, and wait until the access list
 * is known-good. Failed reads are a different state, not an empty-good list.
 */
async function mountPanel({accesses = [], users = [], props = {}}: MountOptions = {}) {
    api[LIST].mockResolvedValue({items: accesses});
    api[SEARCH].mockResolvedValue({items: users});
    const utils = render(BrokerSharingPanel, {brokerId: 7, ...props});
    await settled();
    return utils;
}

async function settled() {
    await waitFor(() => expect(panel()).toHaveAttribute('data-access-state', 'ready'));
}

async function loadFailed() {
    await waitFor(() => expect(panel()).toHaveAttribute('data-access-state', 'error'));
}

function panel(): HTMLElement {
    return screen.getByTestId('broker-sharing-panel');
}

function panelErrorKey(): string | null {
    return panel().getAttribute('data-error-key');
}

function editErrorKey(): string | null {
    return screen.getByTestId('sharing-edit-user-modal').querySelector('[data-edit-error-key]')?.getAttribute('data-edit-error-key') ?? null;
}

// =========================================================================
// Readers — everything addressed by user id or by testid, never by position
// =========================================================================

function entry(userId: number): HTMLElement {
    return screen.getByTestId(`access-entry-${userId}`);
}

/** Which of the three role columns holds this user, or null when absent. */
function columnOf(userId: number): Role | null {
    const table: Record<string, Role> = {'sharing-owners-column': 'OWNER', 'sharing-editors-column': 'EDITOR', 'sharing-viewers-column': 'VIEWER'};
    for (const [testid, role] of Object.entries(table)) {
        if (within(screen.getByTestId(testid)).queryByTestId(`access-entry-${userId}`)) return role;
    }
    return null;
}

/** The ids currently rendered in one column, in DOM order. */
function idsIn(column: string): number[] {
    return [...screen.getByTestId(column).querySelectorAll('[data-testid^="access-entry-"]')].map((el) => Number(el.getAttribute('data-testid')!.replace('access-entry-', '')));
}

function saveBtn(): HTMLButtonElement {
    return screen.getByTestId('sharing-save-btn') as HTMLButtonElement;
}

function errorText(): string | null {
    return screen.queryByTestId('info-banner-error')?.textContent?.trim() ?? null;
}

/** The `data` array handed to SemiDonutChart, via the stub. */
function slices(): {name: string; percentage: number; avatarUrl: string | null}[] {
    return JSON.parse(screen.getByTestId('semi-donut-stub').getAttribute('data-slices') ?? '[]');
}

/** Body of the last bulk PUT — the whole point of the panel. */
function lastPutBody(): {user_id: number; role: Role; share_percentage: number}[] | undefined {
    return api[PUT].mock.calls.at(-1)?.[0];
}

// =========================================================================
// Drivers
// =========================================================================

/**
 * The buttons in a scope that carry no `data-testid`. Used only for the role
 * dropdown and the edit dialog's footer, which publish no handles of their own;
 * every call asserts the expected length first, so a markup change fails here
 * with a readable count instead of silently clicking the wrong control.
 */
function plainButtons(scope: HTMLElement): HTMLButtonElement[] {
    return within(scope)
        .getAllByRole('button')
        .filter((b) => !b.hasAttribute('data-testid')) as HTMLButtonElement[];
}

/**
 * Choose a role in the dropdown of `scope` (the add form or the edit dialog).
 *
 * `roleOptions` is a constant declared in the component in the fixed order
 * OWNER, EDITOR, VIEWER — a source-order enum, not data — so the index is stable
 * by construction. It is still verified rather than trusted: picking OWNER must
 * reveal the share input, and picking anything else must remove it, which is the
 * `{#if newRole === 'OWNER'}` / `{#if editRole === 'OWNER'}` arm. If the index
 * were wrong the assertion below fails immediately.
 */
async function pickRole(scope: HTMLElement, role: Role, opts: {triggerIndex?: number} = {}) {
    const triggerIndex = opts.triggerIndex ?? 0;
    const closed = plainButtons(scope);
    await fireEvent.click(closed[triggerIndex]);

    const open = plainButtons(scope);
    expect(open).toHaveLength(closed.length + 3); // trigger + the three options
    const optionIndex = triggerIndex + 1 + ['OWNER', 'EDITOR', 'VIEWER'].indexOf(role);
    await fireEvent.click(open[optionIndex]);

    if (role === 'OWNER') {
        await waitFor(() => expect(within(scope).getAllByRole('spinbutton')).toHaveLength(1));
    } else {
        await waitFor(() => expect(within(scope).queryAllByRole('spinbutton')).toHaveLength(0));
    }
}

/** The share field of a scope. Only rendered while the chosen role is OWNER. */
function shareInput(scope: HTMLElement): HTMLInputElement {
    return within(scope).getByRole('spinbutton') as HTMLInputElement;
}

/** Type into a `bind:value` number field; ends on the value it promises. */
async function typeShare(scope: HTMLElement, value: string) {
    const input = shareInput(scope);
    await fireEvent.input(input, {target: {value}});
    await waitFor(() => expect(input).toHaveValue(Number(value)));
}

/** Open the add dialog; ends when the form is on screen. */
async function openAdd(): Promise<HTMLElement> {
    await fireEvent.click(screen.getByTestId('sharing-add-user-btn'));
    await waitFor(() => expect(screen.getByTestId('sharing-add-form')).toBeInTheDocument());
    return screen.getByTestId('sharing-add-form');
}

/** Pick a candidate in the UserSearchSelect; ends when Add becomes usable. */
async function pickUser(userId: number) {
    await fireEvent.click(screen.getByTestId('sharing-user-select-trigger'));
    const option = await waitFor(() => {
        const el = document.querySelector(`[data-testid="search-select-option-${userId}"]`);
        expect(el).toBeTruthy();
        return el!;
    });
    await fireEvent.click(option);
    await waitFor(() => expect(screen.getByTestId('sharing-confirm-add')).toBeEnabled());
}

/** Open the edit dialog on a row; ends when the dialog is on screen. */
async function openEdit(userId: number): Promise<HTMLElement> {
    await fireEvent.click(entry(userId));
    await waitFor(() => expect(screen.getByTestId('sharing-edit-user-modal')).toBeInTheDocument());
    return screen.getByTestId('sharing-edit-user-modal');
}

/**
 * The edit dialog's footer buttons, by source order: close (×), role trigger,
 * Remove, Cancel. Asserted, not assumed — and each caller checks the effect.
 */
function editRemoveButton(dialog: HTMLElement): HTMLButtonElement {
    const buttons = plainButtons(dialog);
    expect(buttons).toHaveLength(4);
    return buttons[2];
}

beforeEach(() => {
    for (const name of [LIST, SEARCH, PUT, DELETE_ME]) api[name].mockReset();
    api[PUT].mockResolvedValue({results: [], success_count: 0});
    vi.mocked(toasts.success).mockClear();
    vi.mocked(toasts.error).mockClear();
    gotoMock.mockClear();
    authStore.set({user: null});
});

// =========================================================================
// Loading
// =========================================================================

describe('BrokerSharingPanel — loading', () => {
    it('publishes loading before the access read settles, then ready after it succeeds', async () => {
        await setupI18n();
        const flight = deferred<{items: ReturnType<typeof access>[]}>();
        api[LIST].mockReturnValue(flight.promise);

        render(BrokerSharingPanel, {brokerId: 7});

        expect(panel()).toHaveAttribute('data-access-state', 'loading');
        expect(panel()).toHaveAttribute('aria-busy', 'true');

        flight.resolve({items: [access(1, 'alice', 'OWNER', 1)]});

        await settled();
        expect(panel()).toHaveAttribute('aria-busy', 'false');
        expect(columnOf(1)).toBe('OWNER');
    });

    it('asks for the broker it was given and files each grant under its role', async () => {
        await setupI18n();
        await mountPanel({
            accesses: [access(1, 'alice', 'OWNER', 0.6), access(2, 'bob', 'EDITOR'), access(3, 'carol', 'VIEWER'), access(4, 'dave', 'OWNER', 0.4)],
        });

        expect(api[LIST]).toHaveBeenCalledWith({params: {broker_id: 7}});
        expect(idsIn('sharing-owners-column')).toEqual([1, 4]);
        expect(idsIn('sharing-editors-column')).toEqual([2]);
        expect(idsIn('sharing-viewers-column')).toEqual([3]);
        expect(errorText()).toBeNull();
    });

    it('normalises what the API sends: a string share becomes a number, an unusable one becomes zero', async () => {
        await setupI18n();
        // `share_percentage` arrives as a string from the JSON payload, and
        // `avatar_url` is typed loosely enough that a non-string can arrive.
        await mountPanel({
            accesses: [
                {user_id: 1, username: 'alice', avatar_url: 'http://img/a.png', role: 'OWNER', share_percentage: '0.25'},
                {user_id: 2, username: 'bob', avatar_url: 42, role: 'OWNER', share_percentage: 'not-a-number'},
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ] as any,
        });

        // Only alice reaches the chart: bob's unreadable share became 0, and the
        // chart drops zero-share owners. Her avatar is passed with the preview
        // suffix; bob's non-string avatar was coerced to null, so no initial-only
        // slice carries a bogus URL.
        expect(slices()).toEqual([{name: 'alice', percentage: 25, avatarUrl: 'http://img/a.png?img_preview=64x64'}]);
        expect(columnOf(2)).toBe('OWNER');
    });

    it('falls back to the initial of the name when a user has no picture, in every column', async () => {
        await setupI18n();
        await mountPanel({
            accesses: [access(1, 'alice', 'OWNER', 1, 'http://img/a.png'), access(2, 'bob', 'EDITOR'), access(3, 'carol', 'VIEWER')],
        });

        // alice has an avatar: an image carries her name, and no initial is drawn.
        // (`LazyImage` renders a placeholder and the real file, hence "at least".)
        expect(within(entry(1)).getAllByRole('img', {name: 'alice'}).length).toBeGreaterThan(0);
        expect(within(entry(1)).queryByText('A')).not.toBeInTheDocument();
        // bob and carol do not, in two differently-styled columns.
        expect(within(entry(2)).getByText('B')).toBeInTheDocument();
        expect(within(entry(3)).getByText('C')).toBeInTheDocument();
        expect(within(entry(2)).queryAllByRole('img')).toHaveLength(0);

        // …and the edit dialog makes the same choice for the same user.
        const dialog = await openEdit(2);
        expect(within(dialog).getByText('B')).toBeInTheDocument();
    });

    it('treats a response without an items list as an empty access list', async () => {
        await setupI18n();
        api[LIST].mockResolvedValue({});
        render(BrokerSharingPanel, {brokerId: 7});
        await settled();

        expect(idsIn('sharing-owners-column')).toEqual([]);
        expect(slices()).toEqual([]);
        expect(errorText()).toBeNull();
        expect(saveBtn()).toBeDisabled();
    });

    it('renders a failed load as a blocked, retryable state instead of an editable empty list', async () => {
        await setupI18n();
        api[LIST].mockRejectedValue(new Error('NEEDLE-LOAD-FAILED'));
        render(BrokerSharingPanel, {brokerId: 7});
        await loadFailed();

        // The failed GET is not collapsed into "empty, therefore safe to edit".
        expect(panelErrorKey()).toBe('brokers.sharing.loadFailedBlocking');
        expect(screen.getByTestId('sharing-load-error-state')).toBeInTheDocument();
        expect(screen.getByTestId('sharing-retry-load-btn')).toBeVisible();
        expect(panel()).toHaveAttribute('aria-invalid', 'true');
        expect(screen.queryByTestId('sharing-add-user-btn')).not.toBeInTheDocument();
        expect(idsIn('sharing-owners-column')).toEqual([]);
        expect(saveBtn()).toBeDisabled();
    });

    it('returns to a normal editable state after a failed load is retried successfully', async () => {
        await setupI18n();
        api[LIST].mockRejectedValueOnce(new Error('NEEDLE-FIRST-LOAD-FAILED')).mockResolvedValueOnce({items: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});
        render(BrokerSharingPanel, {brokerId: 7});
        await loadFailed();

        await fireEvent.click(screen.getByTestId('sharing-retry-load-btn'));

        await settled();
        expect(panel()).not.toHaveAttribute('aria-invalid');
        expect(errorText()).toBeNull();
        expect(columnOf(1)).toBe('OWNER');
        expect(screen.getByTestId('sharing-add-user-btn')).toBeVisible();
        expect(saveBtn()).toBeDisabled();
        expect(api[LIST]).toHaveBeenCalledTimes(2);

        const dialog = await openEdit(2);
        await pickRole(dialog, 'EDITOR', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));
        await waitFor(() => expect(saveBtn()).toBeEnabled());

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(api[PUT]).toHaveBeenCalledTimes(1));
        expect(lastPutBody()).toEqual([
            {user_id: 1, role: 'OWNER', share_percentage: 1},
            {user_id: 2, role: 'EDITOR', share_percentage: 0},
        ]);
    });

    it('reloads when the broker changes, and drops the previous broker rows', async () => {
        await setupI18n();
        const {rerender} = await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1)]});
        expect(columnOf(1)).toBe('OWNER');

        api[LIST].mockResolvedValue({items: [access(5, 'carol', 'VIEWER')]});
        await rerender({brokerId: 8});

        await waitFor(() => expect(columnOf(5)).toBe('VIEWER'));
        expect(api[LIST].mock.calls.map((c: [{params: {broker_id: number}}]) => c[0].params.broker_id)).toEqual([7, 8]);
        expect(screen.queryByTestId('access-entry-1')).not.toBeInTheDocument();
    });

    it('dismissing the error banner clears it', async () => {
        await setupI18n();
        api[LIST].mockRejectedValue(new Error('NEEDLE-DISMISS-ME'));
        render(BrokerSharingPanel, {brokerId: 7});
        await loadFailed();
        expect(panelErrorKey()).toBe('brokers.sharing.loadFailedBlocking');

        await fireEvent.click(within(screen.getByTestId('info-banner-error')).getByRole('button', {name: 'Dismiss'}));

        await waitFor(() => expect(screen.queryByTestId('info-banner-error')).not.toBeInTheDocument());
        expect(panelErrorKey()).toBeNull();
    });
});

// =========================================================================
// Save
// =========================================================================

describe('BrokerSharingPanel — save', () => {
    it('sends the complete desired list, then reports success and stops offering to save', async () => {
        await setupI18n();
        const onChanged = vi.fn();
        const onCancel = vi.fn();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')], props: {onChanged, onCancel}});

        // A single local change: bob becomes an EDITOR.
        const dialog = await openEdit(2);
        await pickRole(dialog, 'EDITOR', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));
        await waitFor(() => expect(columnOf(2)).toBe('EDITOR'));
        expect(saveBtn()).toBeEnabled();

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(api[PUT]).toHaveBeenCalledTimes(1));
        // Every grant travels, not just the edited one — the endpoint replaces.
        expect(lastPutBody()).toEqual([
            {user_id: 1, role: 'OWNER', share_percentage: 1},
            {user_id: 2, role: 'EDITOR', share_percentage: 0},
        ]);
        expect(api[PUT].mock.calls[0][1]).toEqual({params: {broker_id: 7}});
        expect(onChanged).toHaveBeenCalledTimes(1);
        expect(onCancel).toHaveBeenCalledTimes(1); // the modal wrapper's auto-close
        expect(toasts.success).toHaveBeenCalledTimes(1);
        // The saved state became the new baseline: nothing left to save.
        await waitFor(() => expect(saveBtn()).toBeDisabled());
        expect(errorText()).toBeNull();
    });

    it('F3 — after a successful save the bound hasChanges is already false when onCancel fires', async () => {
        await setupI18n();
        // The bug: the modal wrapper binds `hasChanges` and pops the unsaved-changes
        // confirm whenever it is true at close time. handleSave used to call
        // `onCancel` in the same flush that cleared the dirty state, so the binding
        // still read true and every successful save was followed by a "discard
        // changes?" dialog. The fix is `await tick()` before `onCancel?.()`.
        //
        // The harness binds hasChanges like the modal does and probes the value at
        // the exact moment onCancel fires; the mirror span proves the binding is
        // live before the save, so `false` afterwards is an observation, not a
        // constant.
        const onChanged = vi.fn();
        const onCancelProbe = vi.fn();
        api[LIST].mockResolvedValue({items: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});
        api[SEARCH].mockResolvedValue({items: []});
        render(BrokerSharingPanelHarness, {brokerId: 7, onChanged, onCancelProbe});
        await settled();

        const harnessFlag = () => screen.getByTestId('harness-has-changes').getAttribute('data-value');
        expect(harnessFlag()).toBe('false'); // clean baseline

        // Dirty the draft: bob becomes an EDITOR. The binding must go live —
        // without this, the probe's `false` below could never have read `true`.
        const dialog = await openEdit(2);
        await pickRole(dialog, 'EDITOR', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));
        await waitFor(() => expect(saveBtn()).toBeEnabled());
        await waitFor(() => expect(harnessFlag()).toBe('true'));

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(onCancelProbe).toHaveBeenCalledTimes(1));
        // F3: by the time the modal wrapper is asked to close, the bound value
        // has already recomputed to false — no unsaved-changes confirm.
        expect(onCancelProbe).toHaveBeenCalledWith(false);
        await waitFor(() => expect(harnessFlag()).toBe('false'));
    });

    it('embedded — no onCancel — saves without one and stays put', async () => {
        await setupI18n();
        const onChanged = vi.fn();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')], props: {onChanged}});

        const dialog = await openEdit(2);
        await pickRole(dialog, 'EDITOR', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));
        await waitFor(() => expect(saveBtn()).toBeEnabled());

        await fireEvent.click(saveBtn());

        await waitFor(() => expect(saveBtn()).toBeDisabled());
        expect(onChanged).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('broker-sharing-panel')).toBeInTheDocument();
    });

    it('renders a refused save inline, keeps the draft, and fires no toast', async () => {
        await setupI18n();
        const onChanged = vi.fn();
        const onCancel = vi.fn();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')], props: {onChanged, onCancel}});
        // The server's own words — injected here, so asserting them verbatim is
        // asserting a value this test provided, not a translation.
        api[PUT].mockRejectedValue(httpError('NEEDLE-SERVER-REFUSED', 400));

        const dialog = await openEdit(2);
        await pickRole(dialog, 'EDITOR', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));
        await waitFor(() => expect(saveBtn()).toBeEnabled());
        await fireEvent.click(saveBtn());

        await waitFor(() => expect(errorText()).toBe('NEEDLE-SERVER-REFUSED'));
        // `trySave` is called with `toast: false`, so the banner is the whole
        // report — a toast as well would be the same news twice.
        expect(toasts.error).not.toHaveBeenCalled();
        expect(toasts.success).not.toHaveBeenCalled();
        expect(onChanged).not.toHaveBeenCalled();
        expect(onCancel).not.toHaveBeenCalled();
        // The draft survives, and can be saved again.
        expect(columnOf(2)).toBe('EDITOR');
        expect(saveBtn()).toBeEnabled();
    });

    it('falls back to its own sentence when the failure carries no readable message', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});
        // An error whose only text is its class name: `trySave` calls that
        // uninformative and reaches for the caller's `fallback` instead.
        api[PUT].mockRejectedValue(new Error(''));

        const dialog = await openEdit(2);
        await pickRole(dialog, 'EDITOR', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));
        await waitFor(() => expect(saveBtn()).toBeEnabled());
        await fireEvent.click(saveBtn());

        // The sentence itself is a translation, so what is asserted is that the
        // banner appeared with something other than the empty message.
        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toBeInTheDocument());
        expect(errorText()).not.toBe('');
        expect(errorText()).not.toBe('Error');
    });

    it('is not offered while a save is in flight, and becomes available again if it fails', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});
        const flight = deferred<unknown>();
        api[PUT].mockReturnValue(flight.promise);

        const dialog = await openEdit(2);
        await pickRole(dialog, 'EDITOR', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));
        await waitFor(() => expect(saveBtn()).toBeEnabled());

        await fireEvent.click(saveBtn());
        await waitFor(() => expect(saveBtn()).toBeDisabled());

        flight.reject(httpError('NEEDLE-LATE-REFUSAL'));
        await waitFor(() => expect(errorText()).toBe('NEEDLE-LATE-REFUSAL'));
        expect(saveBtn()).toBeEnabled();
    });

    it('has no re-entrancy guard of its own: a second dispatch in flight starts a second write', async () => {
        // Pinning a property of the component, not a claim about the browser.
        // `disabled={!hasChanges || saving}` is the only thing between the user
        // and two concurrent writes of the access list; `handleSave` itself never
        // looks at `saving`. jsdom's synthetic dispatch reaches the handler of a
        // disabled button where a real click would be swallowed, which is what
        // makes the absence observable here — and also why this is a latent risk
        // rather than a live bug: every present-day caller goes through that
        // button. The day a guard is added, or a second caller appears, this test
        // is the one that says so.
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});
        const flight = deferred<unknown>();
        api[PUT].mockReturnValue(flight.promise);

        const dialog = await openEdit(2);
        await pickRole(dialog, 'EDITOR', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));
        await waitFor(() => expect(saveBtn()).toBeEnabled());

        await fireEvent.click(saveBtn());
        await waitFor(() => expect(saveBtn()).toBeDisabled());
        await fireEvent.click(saveBtn());

        expect(api[PUT]).toHaveBeenCalledTimes(2);
        flight.resolve({results: [], success_count: 0});
        await waitFor(() => expect(saveBtn()).toBeDisabled());
    });

    it('Reset puts the loaded configuration back and withdraws the offer to save', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});
        // No Reset control until something is actually different.
        expect(screen.queryByTitle('Reset')).not.toBeInTheDocument();

        const dialog = await openEdit(2);
        await pickRole(dialog, 'EDITOR', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));
        await waitFor(() => expect(columnOf(2)).toBe('EDITOR'));

        // Reached by its hard-coded `title` — the one control in this panel whose
        // label never went through the catalogue. See the report.
        await fireEvent.click(screen.getByTitle('Reset'));

        await waitFor(() => expect(columnOf(2)).toBe('VIEWER'));
        expect(saveBtn()).toBeDisabled();
        expect(screen.queryByTitle('Reset')).not.toBeInTheDocument();
        expect(api[PUT]).not.toHaveBeenCalled();
    });
});

// =========================================================================
// Add user
// =========================================================================

describe('BrokerSharingPanel — add user', () => {
    it('opens on the full candidate list, minus everyone already granted access', async () => {
        await setupI18n();
        await mountPanel({
            accesses: [access(1, 'alice', 'OWNER', 1)],
            users: [
                {id: 1, username: 'alice', avatar_url: null},
                {id: 9, username: 'zoe', avatar_url: null},
            ],
        });

        await openAdd();
        await waitFor(() => expect(api[SEARCH]).toHaveBeenCalledWith({queries: {q: '', exclude_broker_id: 7}}));
        await fireEvent.click(screen.getByTestId('sharing-user-select-trigger'));

        // alice is already an owner, so she is filtered out client-side even
        // though the search answered with her.
        await waitFor(() => expect(document.querySelector('[data-testid="search-select-option-9"]')).toBeTruthy());
        expect(document.querySelector('[data-testid="search-select-option-1"]')).toBeNull();
        // One candidate left, so the "nobody to add" hint stays away.
        expect(screen.queryByTestId('sharing-no-other-users')).not.toBeInTheDocument();
    });

    it('does not call an unfinished search empty', async () => {
        // The hint is gated on `!loadingUsers` as well as on the list being empty,
        // which is the difference between "nobody to add" and "not answered yet".
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1)]});
        const flight = deferred<{items: {id: number; username: string; avatar_url: string | null}[]}>();
        api[SEARCH].mockReturnValue(flight.promise);

        await openAdd();
        expect(screen.queryByTestId('sharing-no-other-users')).not.toBeInTheDocument();

        flight.resolve({items: []});

        await waitFor(() => expect(screen.getByTestId('sharing-no-other-users')).toBeInTheDocument());
    });

    it('reports a dead user search as "no candidates" — the same picture as an empty list', async () => {
        // Pinning current behaviour, not endorsing it: `loadSelectableUsers`
        // swallows the rejection into `availableUsers = []`, so a broken search
        // and a broker everyone already belongs to look identical to the user.
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1)]});
        api[SEARCH].mockRejectedValue(new Error('NEEDLE-SEARCH-DOWN'));

        await openAdd();

        await waitFor(() => expect(screen.getByTestId('sharing-no-other-users')).toBeInTheDocument());
        expect(screen.queryByTestId('info-banner-error')).not.toBeInTheDocument();
        expect(screen.getByTestId('sharing-confirm-add')).toBeDisabled();
    });

    it('adds a viewer with no share, and leaves the chart alone', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1)], users: [{id: 9, username: 'zoe', avatar_url: null}]});

        await openAdd();
        await pickUser(9);
        await fireEvent.click(screen.getByTestId('sharing-confirm-add'));

        await waitFor(() => expect(columnOf(9)).toBe('VIEWER'));
        expect(screen.queryByTestId('sharing-add-form')).not.toBeInTheDocument();
        expect(slices().map((s) => s.name)).toEqual(['alice']);
        expect(saveBtn()).toBeEnabled();
    });

    it('clamps a new owner share to what is still unallocated', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 0.4)], users: [{id: 9, username: 'zoe', avatar_url: null}]});

        const form = await openAdd();
        await pickRole(form, 'OWNER');
        expect(shareInput(form)).toHaveAttribute('max', '60'); // 100 − alice's 40
        await pickUser(9);
        await typeShare(screen.getByTestId('sharing-add-form'), '90');
        await fireEvent.click(screen.getByTestId('sharing-confirm-add'));

        await waitFor(() => expect(columnOf(9)).toBe('OWNER'));
        // 90 asked, 60 granted — `Math.min(newSharePercent, maxNewShare)`.
        expect(slices()).toEqual([
            {name: 'alice', percentage: 40, avatarUrl: null},
            {name: 'zoe', percentage: 60, avatarUrl: null},
        ]);
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(api[PUT]).toHaveBeenCalled());
        expect(lastPutBody()).toEqual([
            {user_id: 1, role: 'OWNER', share_percentage: 0.4},
            {user_id: 9, role: 'OWNER', share_percentage: 0.6},
        ]);
    });

    it('does not clamp the other end: a negative share is added as written', async () => {
        // The `min="0"` on the field is markup only — `handleAddUser` bounds the
        // value from above (`Math.min(…, maxNewShare)`) and never from below, so
        // a typed negative reaches the body as a negative fraction of ownership.
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 0.4)], users: [{id: 9, username: 'zoe', avatar_url: null}]});

        const form = await openAdd();
        await pickRole(form, 'OWNER');
        await pickUser(9);
        await typeShare(screen.getByTestId('sharing-add-form'), '-40');
        await fireEvent.click(screen.getByTestId('sharing-confirm-add'));

        await waitFor(() => expect(columnOf(9)).toBe('OWNER'));
        // Below zero, so the chart drops the slice: on screen this owner simply
        // has no wedge, while the number travels to the server intact.
        expect(slices().map((s) => s.name)).toEqual(['alice']);
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(api[PUT]).toHaveBeenCalled());
        expect(lastPutBody()).toContainEqual({user_id: 9, role: 'OWNER', share_percentage: -0.4});
    });

    it('drops a typed share when the role moves away from owner', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 0.2)], users: [{id: 9, username: 'zoe', avatar_url: null}]});

        const form = await openAdd();
        await pickRole(form, 'OWNER');
        await typeShare(form, '50');
        await pickRole(form, 'EDITOR'); // hides the field *and* zeroes the value
        await pickUser(9);
        await fireEvent.click(screen.getByTestId('sharing-confirm-add'));

        await waitFor(() => expect(columnOf(9)).toBe('EDITOR'));
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(api[PUT]).toHaveBeenCalled());
        expect(lastPutBody()).toContainEqual({user_id: 9, role: 'EDITOR', share_percentage: 0});
    });

    it('refuses to add nobody, from the button and from the keyboard alike', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 0.5)], users: [{id: 9, username: 'zoe', avatar_url: null}]});

        const form = await openAdd();
        expect(screen.getByTestId('sharing-confirm-add')).toBeDisabled();

        // Enter in the share field calls `handleAddUser` directly, bypassing the
        // disabled button — which is why the function needs its own `!selectedUser`
        // guard, and has one.
        await pickRole(form, 'OWNER');
        await typeShare(form, '30');
        await fireEvent.keyDown(shareInput(form), {key: 'Enter'});

        expect(screen.getByTestId('sharing-add-form')).toBeInTheDocument();
        expect(idsIn('sharing-owners-column')).toEqual([1]);
        expect(saveBtn()).toBeDisabled();
    });

    it('closing the add dialog forgets the selection', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1)], users: [{id: 9, username: 'zoe', avatar_url: null}]});

        await openAdd();
        await pickUser(9);
        const closed = plainButtons(screen.getByTestId('sharing-add-user-modal'));
        expect(closed).toHaveLength(3); // header ×, role trigger, footer Cancel
        await fireEvent.click(closed[2]);
        await waitFor(() => expect(screen.queryByTestId('sharing-add-form')).not.toBeInTheDocument());

        await openAdd();
        expect(screen.getByTestId('sharing-confirm-add')).toBeDisabled();
        expect(idsIn('sharing-viewers-column')).toEqual([]);
    });
});

// =========================================================================
// Edit and remove
// =========================================================================

describe('BrokerSharingPanel — edit and remove', () => {
    it('opens on the row it was asked about, with that row values', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 0.35), access(2, 'bob', 'VIEWER')]});

        const dialog = await openEdit(1);

        // Pre-filled from the entry, not from the previous dialog: the share field
        // is present (so the role read OWNER) and carries alice's own 35%.
        expect(shareInput(dialog)).toHaveValue(35);
        expect(within(dialog).getByText('alice')).toBeInTheDocument();
    });

    it('moves a user between columns and zeroes the share the role no longer allows', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 0.7), access(2, 'bob', 'OWNER', 0.3)]});

        const dialog = await openEdit(2);
        await pickRole(dialog, 'VIEWER', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));

        await waitFor(() => expect(columnOf(2)).toBe('VIEWER'));
        expect(screen.queryByTestId('sharing-edit-user-modal')).not.toBeInTheDocument();
        expect(slices()).toEqual([{name: 'alice', percentage: 70, avatarUrl: null}]);
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(api[PUT]).toHaveBeenCalled());
        expect(lastPutBody()).toContainEqual({user_id: 2, role: 'VIEWER', share_percentage: 0});
    });

    it('cancelling an edit changes nothing', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});

        const dialog = await openEdit(2);
        await pickRole(dialog, 'OWNER', {triggerIndex: 1});
        await typeShare(dialog, '10');
        const buttons = plainButtons(dialog);
        expect(buttons).toHaveLength(4); // ×, role trigger, Remove, Cancel
        await fireEvent.click(buttons[3]);

        await waitFor(() => expect(screen.queryByTestId('sharing-edit-user-modal')).not.toBeInTheDocument());
        expect(columnOf(2)).toBe('VIEWER');
        expect(saveBtn()).toBeDisabled();
    });

    it('removing a user asks first, and the answer decides', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});

        // Say no.
        await fireEvent.click(editRemoveButton(await openEdit(2)));
        await waitFor(() => expect(screen.getByTestId('confirm-modal-cancel')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-cancel')).not.toBeInTheDocument());
        expect(columnOf(2)).toBe('VIEWER');
        expect(saveBtn()).toBeDisabled();

        // Say yes.
        await fireEvent.click(editRemoveButton(await openEdit(2)));
        await waitFor(() => expect(screen.getByTestId('confirm-modal-confirm')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));

        await waitFor(() => expect(screen.queryByTestId('access-entry-2')).not.toBeInTheDocument());
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(api[PUT]).toHaveBeenCalled());
        expect(lastPutBody()).toEqual([{user_id: 1, role: 'OWNER', share_percentage: 1}]);
    });

    it('refuses to remove the only owner, and says so without opening the dialog', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});

        await fireEvent.click(editRemoveButton(await openEdit(1)));

        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toBeInTheDocument());
        expect(panelErrorKey()).toBe('brokers.sharing.lastOwnerRemovalWarning');
        expect(screen.queryByTestId('confirm-modal-confirm')).not.toBeInTheDocument();
        expect(columnOf(1)).toBe('OWNER');
        expect(saveBtn()).toBeDisabled();
    });

    it('allows removing an owner once a second one exists', async () => {
        // The guard counts owners, so the same click is refused above and allowed
        // here — the precondition is the count, not the role.
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 0.5), access(4, 'dave', 'OWNER', 0.5)]});

        await fireEvent.click(editRemoveButton(await openEdit(1)));

        await waitFor(() => expect(screen.getByTestId('confirm-modal-confirm')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(screen.queryByTestId('access-entry-1')).not.toBeInTheDocument());
        expect(idsIn('sharing-owners-column')).toEqual([4]);
    });
});

// =========================================================================
// Read-only
// =========================================================================

describe('BrokerSharingPanel — read-only', () => {
    it('shows who has access and offers no way to change it', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')], props: {readOnly: true}});

        expect(columnOf(1)).toBe('OWNER');
        expect(columnOf(2)).toBe('VIEWER');
        // Not "hidden": absent. There is no add button, no save row, and the
        // rows themselves are inert, so `startEdit`'s own guard is never reached.
        expect(screen.queryByTestId('sharing-add-user-btn')).not.toBeInTheDocument();
        expect(screen.queryByTestId('sharing-save-btn')).not.toBeInTheDocument();
        expect(entry(1)).toBeDisabled();
        expect(entry(2)).toBeDisabled();

        await fireEvent.click(entry(1));
        expect(screen.queryByTestId('sharing-edit-user-modal')).not.toBeInTheDocument();
    });

    it('offers no reset either, whatever the data says', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1)], props: {readOnly: true}});

        expect(screen.queryByTitle('Reset')).not.toBeInTheDocument();
        expect(screen.queryByTestId('sharing-add-user-modal')).not.toBeInTheDocument();
    });
});

// =========================================================================
// States the panel offers and the server refuses
//
// Each of these describes something a user can build here and press Save on. The
// endpoint rejects all three (400/422), so they are not holes in the permission
// model — they are configurations the panel lets someone assemble and only the
// round-trip refuses. Written as descriptions of today's behaviour: whichever way
// the decision goes, these are the tests that will say it changed.
// =========================================================================

describe('BrokerSharingPanel — states the panel offers', () => {
    it('lets total ownership pass 100%: it warns, and keeps Save available', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});
        expect(screen.queryByTestId('info-banner-warning')).not.toBeInTheDocument();

        // The edit dialog's share field bounds nothing: `saveEdit` divides by 100
        // and stores the result, and `max="100"` is markup only.
        const dialog = await openEdit(2);
        await pickRole(dialog, 'OWNER', {triggerIndex: 1});
        await typeShare(dialog, '250');
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));

        await waitFor(() => expect(screen.getByTestId('info-banner-warning')).toBeInTheDocument());
        expect(saveBtn()).toBeEnabled();
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(api[PUT]).toHaveBeenCalled());
        expect(lastPutBody()).toContainEqual({user_id: 2, role: 'OWNER', share_percentage: 2.5});
    });

    it('refuses to demote the last owner to viewer or editor, and tells them to promote another owner first', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1), access(2, 'bob', 'VIEWER')]});

        const dialog = await openEdit(1);
        await pickRole(dialog, 'VIEWER', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));

        await waitFor(() => expect(editErrorKey()).toBe('brokers.sharing.lastOwnerDemotionWarning'));
        expect(columnOf(1)).toBe('OWNER');
        expect(screen.getByTestId('sharing-edit-user-modal')).toBeInTheDocument();
        expect(saveBtn()).toBeDisabled();
        expect(api[PUT]).not.toHaveBeenCalled();

        await pickRole(dialog, 'EDITOR', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));

        await waitFor(() => expect(editErrorKey()).toBe('brokers.sharing.lastOwnerDemotionWarning'));
        expect(columnOf(1)).toBe('OWNER');
        expect(saveBtn()).toBeDisabled();
    });

    it('keeps the last owner invariant intact after a refused demotion, so the old empty-list save path stays closed', async () => {
        await setupI18n();
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1)]});

        const dialog = await openEdit(1);
        await pickRole(dialog, 'VIEWER', {triggerIndex: 1});
        await fireEvent.click(screen.getByTestId('sharing-confirm-edit'));
        await waitFor(() => expect(editErrorKey()).toBe('brokers.sharing.lastOwnerDemotionWarning'));
        expect(columnOf(1)).toBe('OWNER');

        await fireEvent.click(editRemoveButton(screen.getByTestId('sharing-edit-user-modal')));

        await waitFor(() => expect(panelErrorKey()).toBe('brokers.sharing.lastOwnerRemovalWarning'));
        expect(screen.queryByTestId('confirm-modal-confirm')).not.toBeInTheDocument();
        expect(columnOf(1)).toBe('OWNER');
        expect(saveBtn()).toBeDisabled();
        expect(api[PUT]).not.toHaveBeenCalled();
    });

    it('after a failed load, save refuses to write the unknown access list', async () => {
        await setupI18n();
        api[LIST].mockRejectedValue(new Error('NEEDLE-LOAD-FAILED'));
        api[SEARCH].mockResolvedValue({items: [{id: 9, username: 'zoe', avatar_url: null}]});
        render(BrokerSharingPanel, {brokerId: 7});
        await loadFailed();

        expect(screen.queryByTestId('sharing-add-user-btn')).not.toBeInTheDocument();
        expect(saveBtn()).toBeDisabled();
        await fireEvent.click(saveBtn());

        expect(api[PUT]).not.toHaveBeenCalled();
        expect(lastPutBody()).toBeUndefined();
        expect(panel()).toHaveAttribute('data-access-state', 'error');
    });
});

// =========================================================================
// Self-service leave (F4) — navigation ordering (R3-F4)
// =========================================================================

describe('BrokerSharingPanel — self-service leave (F4, R3-F4, R5-F4)', () => {
    /**
     * R3-F4: on a successful leave the panel must navigate to /brokers BEFORE
     * calling onChanged — on the broker detail page, onChanged reloads the very
     * broker that was just cascade-deleted, and when that reload threw, the
     * earlier order (onChanged first) skipped the goto entirely: the modal
     * stayed open over a stale page. The assertions therefore check not only
     * THAT both fire, but their invocation order.
     *
     * R5-F4: a successful leave ends with `onCancel?.()` so the host modal
     * (BrokerSharingModal's handleRequestClose) closes too, instead of staying
     * open over the /brokers page the goto just navigated to. The locked order
     * is therefore goto → onChanged → onCancel; a failed leave fires NONE of
     * the three (error toast only — the panel must stay open with its data).
     *
     * Both response branches are covered: broker_deleted true (last owner,
     * cascade) and false (access lost, broker survives) — both navigate.
     */

    /** Mount with alice (id 1) as the signed-in user and an OWNER of the broker. */
    async function mountAsAlice() {
        authStore.set({user: {id: 1, username: 'alice'}});
        const onChanged = vi.fn();
        const onCancel = vi.fn();
        await mountPanel({
            accesses: [access(1, 'alice', 'OWNER', 0.5), access(2, 'bob', 'OWNER', 0.5)],
            props: {onChanged, onCancel},
        });
        return {onChanged, onCancel};
    }

    /** Open the leave confirm and accept it; ends when the DELETE has fired. */
    async function confirmLeave() {
        await fireEvent.click(screen.getByTestId('sharing-self-leave-btn'));
        await waitFor(() => expect(screen.getByTestId('confirm-modal-confirm')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(api[DELETE_ME]).toHaveBeenCalledTimes(1));
    }

    it('leave with broker surviving: navigates to /brokers BEFORE onChanged, then closes the host modal', async () => {
        await setupI18n();
        const {onChanged, onCancel} = await mountAsAlice();
        api[DELETE_ME].mockResolvedValue({success: true, message: 'Access removed', broker_deleted: false});

        await confirmLeave();
        // The confirm is spent — the modal closed.
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).not.toBeInTheDocument());

        await waitFor(() => expect(gotoMock).toHaveBeenCalledWith('/brokers'));
        await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
        // R5-F4: the host modal is closed after a successful leave.
        await waitFor(() => expect(onCancel).toHaveBeenCalledTimes(1));
        // R3-F4 + R5-F4: the ordering IS the fix — goto → onChanged → onCancel.
        expect(gotoMock.mock.invocationCallOrder[0]).toBeLessThan(onChanged.mock.invocationCallOrder[0]);
        expect(onChanged.mock.invocationCallOrder[0]).toBeLessThan(onCancel.mock.invocationCallOrder[0]);
        // The call carried the broker this panel is mounted for.
        expect(api[DELETE_ME].mock.calls[0][1]).toEqual({params: {broker_id: 7}});
        expect(toasts.success).toHaveBeenCalledTimes(1);
    });

    it('leave with broker cascade-deleted (last owner): same navigation, same order, same close', async () => {
        await setupI18n();
        const {onChanged, onCancel} = await mountAsAlice();
        api[DELETE_ME].mockResolvedValue({success: true, message: 'Broker deleted: the last owner left', broker_deleted: true});

        await confirmLeave();
        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).not.toBeInTheDocument());

        await waitFor(() => expect(gotoMock).toHaveBeenCalledWith('/brokers'));
        await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
        await waitFor(() => expect(onCancel).toHaveBeenCalledTimes(1));
        expect(gotoMock.mock.invocationCallOrder[0]).toBeLessThan(onChanged.mock.invocationCallOrder[0]);
        expect(onChanged.mock.invocationCallOrder[0]).toBeLessThan(onCancel.mock.invocationCallOrder[0]);
    });

    it('a failed leave neither navigates nor reports a change nor closes the modal', async () => {
        await setupI18n();
        const {onChanged, onCancel} = await mountAsAlice();
        api[DELETE_ME].mockRejectedValue(new Error('NEEDLE-LEAVE-FAILED'));

        await confirmLeave();

        await waitFor(() => expect(toasts.error).toHaveBeenCalledTimes(1));
        expect(gotoMock).not.toHaveBeenCalled();
        expect(onChanged).not.toHaveBeenCalled();
        // R5-F4: the failure path must not close the host modal either.
        expect(onCancel).not.toHaveBeenCalled();
    });

    // R4-F4 — the leave confirm carries the "what to do instead" hint ONLY for
    // the last owner (whose leaving cascade-deletes the broker), rendered in
    // italics (ConfirmModal.descriptionItalic). ConfirmModal's description <p>
    // has no data-testid; it is located structurally as the sibling of
    // `confirm-modal-message`, and the asserted class (`italic`) IS the feature
    // — the same deliberate exception as the F15 badge palette.
    function leaveDescription(): HTMLElement | null {
        return screen.getByTestId('confirm-modal-message').parentElement?.querySelector('p.description') ?? null;
    }

    it('last-owner leave confirm shows the italic guidance hint', async () => {
        await setupI18n();
        // Alice is the ONLY owner → selfIsLastOwner.
        authStore.set({user: {id: 1, username: 'alice'}});
        await mountPanel({accesses: [access(1, 'alice', 'OWNER', 1)]});

        await fireEvent.click(screen.getByTestId('sharing-self-leave-btn'));
        await waitFor(() => expect(screen.getByTestId('confirm-modal-message')).toBeInTheDocument());

        const desc = leaveDescription();
        expect(desc, 'last-owner leave must carry the guidance hint paragraph').not.toBeNull();
        expect(desc!.classList.contains('italic')).toBe(true);
        expect(desc!.textContent?.trim().length).toBeGreaterThan(0);
    });

    it('non-last-owner leave confirm shows no hint paragraph at all', async () => {
        await setupI18n();
        await mountAsAlice(); // alice + bob both OWNER → not the last one

        await fireEvent.click(screen.getByTestId('sharing-self-leave-btn'));
        await waitFor(() => expect(screen.getByTestId('confirm-modal-message')).toBeInTheDocument());

        expect(leaveDescription()).toBeNull();
    });
});
