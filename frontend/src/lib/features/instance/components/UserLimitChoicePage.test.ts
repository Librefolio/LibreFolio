// @vitest-environment jsdom
/**
 * UserLimitChoicePage — what an administrator sees instead of the app while the active accounts outnumber the plan
 * (workstream A, lot A5-7; analysis `ondata5/A-5-7-analisi-oltre-il-limite.md`).
 *
 * The contract under test:
 *   - at mount the page reads the choice through `fetchChoice` (by default `GET /users/over-limit`) and lists the active
 *     accounts, each in `user-limit-row-<id>` with a checkbox `user-limit-keep-<id>`;
 *   - an account the server marks `protected` (the owner of a managed instance; the administrator who chooses, when there is
 *     no owner) is checked and cannot be unchecked; the others start unchecked;
 *   - `user-limit-counter` says how many are chosen against `max_keep`, with `data-state` `ok` or `over`; the confirm
 *     button `user-limit-confirm` is disabled while more than `max_keep` are chosen, while none is, and while no administrator
 *     is among them (the server refuses it too);
 *   - when the chosen accounts and the live invitations exceed the plan, `user-limit-invites` says how many invitations will
 *     be cancelled (never more than the live ones); otherwise it is not there;
 *   - an account that owns brokers alone says so (`user-limit-alone-<id>`), the others do not;
 *   - the confirm button sends exactly the chosen ids through `resolve`; on success `onresolved` runs (by default: the flag
 *     is cleared and the page reloads); a 409 `NOT_OVER_LIMIT` is a success too (another administrator chose first); a
 *     refusal with a code shows its own line in `user-limit-error` and keeps the page; any other failure shows the generic line;
 *   - when the answer says the instance is no longer over the plan, `onresolved` runs without a click;
 *   - when the list cannot be read, `user-limit-error` says so and `user-limit-retry` asks again;
 *   - the backup card follows the page whatever the list holds: it is in `user-limit-backup`, outside the alert;
 *   - the logout button (`user-limit-logout`) calls `onlogout`.
 *
 * Texts are never compared: `$lib/i18n` keeps its real exports with the identity as translator, so a line renders as its
 * key, the values of an interpolated one written out after it. The backup card is a stub (its own spec is
 * `BackupDownloadCard.test.ts`). No clock: every wait is a `waitFor` on a state.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const identity = readable((key: string, options?: {values?: Record<string, unknown>}) => (options?.values ? `${key} ${Object.values(options.values).join(' ')}` : key));
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: identity, t: identity};
});
vi.mock('$lib/api', () => ({zodiosApi: {}}));
vi.mock('$lib/features/backup/BackupDownloadCard.svelte', async () => ({default: (await import('$test/harness/BackupDownloadCardStub.svelte')).default}));
vi.mock('$lib/components/ui/feedback/ToastContainer.svelte', () => ({default: () => {}}));

import UserLimitChoicePage from './UserLimitChoicePage.svelte';

type Row = {id: number; username: string; email: string; is_superuser: boolean; protected: 'owner' | 'you' | null; owned_brokers_alone: number};
type Choice = {over_limit: boolean; active: number; max_users: number | null; live_invites: number; waiting_accounts: number; max_keep: number; users: Row[]};

const row = (id: number, username: string, extra: Partial<Row> = {}): Row => ({id, username, email: `${username}@example.test`, is_superuser: false, protected: null, owned_brokers_alone: 0, ...extra});

/** The example of the analysis: five accounts, a plan of three; Anna chooses. */
function example(extra: Partial<Choice> = {}): Choice {
    return {
        over_limit: true,
        active: 5,
        max_users: 3,
        live_invites: 0,
        waiting_accounts: 0,
        max_keep: 3,
        users: [row(1, 'anna', {is_superuser: true, protected: 'you'}), row(2, 'bruno', {is_superuser: true}), row(3, 'carla'), row(4, 'dario', {owned_brokers_alone: 2}), row(5, 'elena')],
        ...extra,
    };
}

function mount(choice: Choice | Error, resolve: (ids: number[]) => Promise<unknown> = async () => ({kept: 3, deactivated: 2, revoked_invites: 0})) {
    const fetchChoice = vi.fn(async () => {
        if (choice instanceof Error) throw choice;
        return choice;
    });
    const onresolved = vi.fn();
    const onlogout = vi.fn();
    const resolver = vi.fn(resolve);
    render(UserLimitChoicePage, {props: {fetchChoice, resolve: resolver, onresolved, onlogout}});
    return {fetchChoice, onresolved, onlogout, resolver};
}

const keep = (id: number) => screen.getByTestId(`user-limit-keep-${id}`) as HTMLInputElement;
const confirm = () => screen.getByTestId('user-limit-confirm') as HTMLButtonElement;
const counter = () => screen.getByTestId('user-limit-counter');
async function listed() {
    await waitFor(() => expect(screen.getByTestId('user-limit-row-1')).toBeInTheDocument());
}

/** An axios-shaped refusal. */
function refusal(status: number, detail: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, response: {status, data: {detail}}});
}

afterEach(cleanup);

describe('UserLimitChoicePage — the list', () => {
    it('lists every active account with a checkbox, the protected one checked and fixed, the others unchecked', async () => {
        mount(example());
        await listed();

        expect([1, 2, 3, 4, 5].map((id) => keep(id).checked)).toEqual([true, false, false, false, false]);
        expect(keep(1).disabled, 'the protected account cannot be unchecked').toBe(true);
        expect([2, 3, 4, 5].map((id) => keep(id).disabled)).toEqual([false, false, false, false]);
        expect(within(screen.getByTestId('user-limit-row-2')).getByText('bruno')).toBeInTheDocument();
    });

    it('says which accounts own brokers alone, and only them', async () => {
        mount(example());
        await listed();

        expect(screen.getByTestId('user-limit-alone-4').textContent).toContain('2');
        expect(screen.queryByTestId('user-limit-alone-3')).toBeNull();
        expect(screen.queryByTestId('user-limit-alone-1')).toBeNull();
    });

    it('shows the numbers of the plan in the description', async () => {
        mount(example());
        await listed();

        const description = screen.getByTestId('user-limit-description').textContent ?? '';
        expect(description).toContain('5');
        expect(description).toContain('3');
    });
});

describe('UserLimitChoicePage — the choice', () => {
    it('counts the chosen accounts against the plan, and confirms only within it', async () => {
        mount(example());
        await listed();
        expect(counter()).toHaveAttribute('data-state', 'ok');
        expect(confirm().disabled, 'only the protected account: one of three').toBe(false);

        await fireEvent.click(keep(2));
        await fireEvent.click(keep(3));
        expect(counter(), 'three of three').toHaveAttribute('data-state', 'ok');
        expect(confirm().disabled).toBe(false);

        await fireEvent.click(keep(4));
        expect(counter(), 'four of three').toHaveAttribute('data-state', 'over');
        expect(confirm().disabled).toBe(true);

        await fireEvent.click(keep(4));
        expect(counter()).toHaveAttribute('data-state', 'ok');
        expect(confirm().disabled).toBe(false);
    });

    it('does not confirm a choice without an administrator', async () => {
        const choice = example({users: [row(1, 'anna', {is_superuser: true}), row(2, 'bruno'), row(3, 'carla')], max_keep: 2});
        mount(choice);
        await listed();

        await fireEvent.click(keep(2));
        expect(confirm().disabled, 'bruno is not an administrator').toBe(true);
        await fireEvent.click(keep(1));
        expect(confirm().disabled, 'anna is').toBe(false);
    });

    it('says how many invitations will be cancelled to make room, never more than the live ones, and nothing when they fit', async () => {
        mount(example({live_invites: 2}));
        await listed();
        expect(screen.queryByTestId('user-limit-invites'), 'one chosen of three, two invitations: all fit').toBeNull();

        await fireEvent.click(keep(2));
        expect(screen.getByTestId('user-limit-invites').textContent, 'two chosen and two invitations: one place short').toContain('1');
        await fireEvent.click(keep(3));
        expect(screen.getByTestId('user-limit-invites').textContent, 'three chosen: both invitations go').toContain('2');
    });

    it('leaves an unprotected account out when it is unchecked again', async () => {
        const {resolver} = mount(example());
        await listed();

        await fireEvent.click(keep(2));
        await fireEvent.click(keep(5));
        await fireEvent.click(keep(5));
        await fireEvent.click(confirm());

        await waitFor(() => expect(resolver).toHaveBeenCalledTimes(1));
        expect(resolver.mock.calls[0][0].sort()).toEqual([1, 2]);
    });
});

describe('UserLimitChoicePage — the confirmation', () => {
    it('sends exactly the chosen ids, then runs onresolved', async () => {
        const {resolver, onresolved} = mount(example());
        await listed();

        await fireEvent.click(keep(2));
        await fireEvent.click(keep(3));
        await fireEvent.click(confirm());

        await waitFor(() => expect(onresolved).toHaveBeenCalledTimes(1));
        expect(resolver.mock.calls[0][0].sort()).toEqual([1, 2, 3]);
    });

    it('treats NOT_OVER_LIMIT as done: another administrator chose first', async () => {
        const {onresolved} = mount(example(), async () => {
            throw refusal(409, {error_code: 'NOT_OVER_LIMIT', message: 'x'});
        });
        await listed();

        await fireEvent.click(confirm());

        await waitFor(() => expect(onresolved).toHaveBeenCalledTimes(1));
    });

    it.each(['UNKNOWN_USER', 'TOO_MANY_KEPT', 'PROTECTED_MISSING', 'NO_ADMIN_KEPT'])('shows the line of %s and keeps the page', async (code) => {
        const {onresolved} = mount(example(), async () => {
            throw refusal(422, {error_code: code, message: 'x'});
        });
        await listed();

        await fireEvent.click(confirm());

        await waitFor(() => expect(screen.getByTestId('user-limit-error')).toBeInTheDocument());
        expect(screen.getByTestId('user-limit-error').textContent).toContain(code);
        expect(onresolved).not.toHaveBeenCalled();
        expect(confirm().disabled, 'the administrator may choose again').toBe(false);
    });

    it('shows a generic line for any other failure', async () => {
        mount(example(), async () => {
            throw new Error('network');
        });
        await listed();

        await fireEvent.click(confirm());

        await waitFor(() => expect(screen.getByTestId('user-limit-error').textContent).toContain('generic'));
    });
});

describe('UserLimitChoicePage — the other states', () => {
    it('runs onresolved at once when the instance is no longer over the plan', async () => {
        const {onresolved} = mount(example({over_limit: false, users: []}));

        await waitFor(() => expect(onresolved).toHaveBeenCalledTimes(1));
    });

    it('says the list could not be read, and asks again on retry', async () => {
        const {fetchChoice} = mount(new Error('network'));

        await waitFor(() => expect(screen.getByTestId('user-limit-error')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('user-limit-retry'));

        await waitFor(() => expect(fetchChoice).toHaveBeenCalledTimes(2));
    });

    it('offers the backup outside the alert, and logout', async () => {
        const {onlogout} = mount(example());
        await listed();

        const backup = screen.getByTestId('user-limit-backup');
        expect(within(backup).getByTestId('backup-download-card-stub')).toBeInTheDocument();
        expect(backup.closest('[role="alert"]'), 'the backup is not part of the alert').toBeNull();

        await fireEvent.click(screen.getByTestId('user-limit-logout'));
        expect(onlogout).toHaveBeenCalledTimes(1);
    });
});
