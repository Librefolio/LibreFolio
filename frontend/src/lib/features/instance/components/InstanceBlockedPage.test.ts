// @vitest-environment jsdom
/**
 * InstanceBlockedPage — the page the `(app)` layout shows instead of the app on a blocked instance (workstream H, CP6).
 *
 * The contract under test:
 *   - the page (`instance-blocked`) explains the block: `instance.block.adminDescription` to an administrator
 *     (`$auth.user.is_superuser === true`), `instance.block.userDescription` to anyone else;
 *   - at mount it reads the block through `fetchBlock` (by default the generated client's
 *     `get_instance_block_api_v1_system_block_get`), and shows `instance.block.deletionDate` only when a deletion date
 *     is given: the ISO day written in the interface locale at UTC, so that no time zone moves it to the day before or
 *     after;
 *   - an administrator whose answer carries `billing_url` gets a link to the subscription (`instance-blocked-billing`):
 *     `instance.block.manageSubscription`, opened in a new tab without opener or referrer, its icon hidden from
 *     assistive technology. Only an http(s) address becomes a link, whatever the backend sends (a `javascript:` one
 *     never does); nobody else gets it, and the logout button stays in every case;
 *   - the backup card of workstream B (`BackupDownloadCard`, decision 12) follows the answer's `backup_available`, never
 *     the client's role: told `true`, the page shows it in `instance-blocked-backup`, below the `role="alert"` section
 *     and outside it (and outside any other live region), so that a screen reader announces the block and not the card;
 *     told `false`, told nothing, while the answer is pending, after a failed request and when the block was lifted
 *     meanwhile, the card is not mounted at all. An administrator told `false` gets none, a user told `true` gets it.
 *     The backup section is a region named by the level-2 heading it holds before the card (`aria-labelledby`), the only
 *     level-2 heading of the page, after its h1: headings go h1, h2, then the card's own h3;
 *   - the page has a toast container of its own, with or without the card: the `(app)` layout mounts its toasts around
 *     the app only, and this page replaces the app. A toast pushed while the page is mounted shows on it, outside the
 *     alert (a change inside the alert would have the whole block read out again) and outside the backup section;
 *   - when the answer says the instance is no longer blocked, the flag is cleared and the page reloads;
 *   - when the answer fails, the page stays, without a date, and the flag stays on;
 *   - the logout button (`instance-blocked-logout`) calls `onlogout`.
 *
 * Answers are deferreds the test settles by hand: the component awaits the promise first, so its continuation has run
 * when the test's own `await` of the same promise resumes, and `tick()` then lets the page paint it. No clock. Texts are
 * compared only with what the catalogue answers for the key (`translate`), never with a literal, and the date with the
 * interface locale of the same module the component reads. `$lib/stores/app/auth` is a writable the test sets, and
 * `window.location` is stubbed only where a reload is expected.
 *
 * The card is `BackupDownloadCardStub`, one element with a testid of its own (`backup-download-card-stub`): what the card
 * does is `BackupDownloadCard.test.ts`, and the real one would read the backup API at mount. A case that asserts there is
 * no card first mounts the same page, for the same user, told `backup_available: true`, and sees the card there (a
 * control), then unmounts it: an absence alone would also hold on a page that never shows the card at all.
 *
 * The toast store is the real one (`$lib/stores/app/toastStore.svelte`), the module the page's container reads. A case
 * that pushes a toast gives it no duration, so no timer is set, and dismisses it by id when the test finishes
 * (`onTestFinished`, after `cleanup()`, even when an assertion failed): no toast is left for the next test.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, onTestFinished, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import {_} from '$lib/i18n';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {instanceBlock} from '../instanceBlock.svelte';
import InstanceBlockedPage from './InstanceBlockedPage.svelte';

type BlockAnswer = {blocked: boolean; deletion_date?: string | null; billing_url?: string | null; backup_available?: boolean};

const mocks = await vi.hoisted(async () => {
    const {writable} = await import('svelte/store');
    return {
        auth: writable<{user: {is_superuser?: boolean} | null}>({user: null}),
        getInstanceBlock: vi.fn().mockName('zodiosApi.get_instance_block_api_v1_system_block_get'),
    };
});

vi.mock('$lib/stores/app/auth', () => ({auth: mocks.auth}));
vi.mock('$lib/api', () => ({zodiosApi: {get_instance_block_api_v1_system_block_get: mocks.getInstanceBlock}}));
// B's backup card is not the subject here (`BackupDownloadCard.test.ts` is): a stub with a testid of its own, so the page
// spec sees where the card is mounted and whether it is, and the real card never reads the backup API from this file.
vi.mock('$lib/features/backup/BackupDownloadCard.svelte', async () => ({default: (await import('$test/harness/BackupDownloadCardStub.svelte')).default}));

const DELETION_DAY = '2026-11-14';
/** Where the subscription is managed, as `GET /system/block` gives it to an administrator. */
const BILLING_URL = 'https://billing.example.test/acme';
/** A placeholder of an address that is not http(s): nothing here follows it, and the page must never make it a link. */
const SCRIPT_ADDRESS = 'javascript:void(0)';
/** `GET /system/block` for a user the server lets download a backup (decision 12: an administrator, in practice). */
const BACKUP_AVAILABLE: BlockAnswer = {blocked: true, deletion_date: DELETION_DAY, backup_available: true};
/** The live regions: what a screen reader reads out by itself when it changes. The backup card belongs in none of them. */
const LIVE_REGION = '[role="alert"], [role="status"], [role="log"], [aria-live]';
/** The message of the toast a case pushes: markup with a testid of its own (kept by the sanitiser), so the case finds its own toast. */
const TOAST_PROBE = '<span data-testid="instance-blocked-toast-probe">probe</span>';

function translate(key: string, values?: Record<string, string>): string {
    return get(_)(key, values ? {values} : undefined);
}

function text(element: Element): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** A promise the test settles by hand. */
function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (error: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** Mount the page with a `fetchBlock` the test answers; the request has started once this returns. */
function mountPage() {
    const answer = deferred<BlockAnswer>();
    const fetchBlock = vi.fn(() => answer.promise);
    const onlogout = vi.fn();
    render(InstanceBlockedPage, {props: {onlogout, fetchBlock}});
    flushSync();
    expect(fetchBlock, 'Barrier: the page reads the block at mount').toHaveBeenCalledTimes(1);
    return {answer, fetchBlock, onlogout};
}

/** Settle the request and let the page paint what it received. */
async function answerWith(answer: ReturnType<typeof deferred<BlockAnswer>>, value: BlockAnswer): Promise<void> {
    answer.resolve(value);
    await answer.promise;
    await tick();
    flushSync();
}

async function failWith(answer: ReturnType<typeof deferred<BlockAnswer>>, error: unknown): Promise<void> {
    answer.reject(error);
    await answer.promise.catch(() => undefined);
    await tick();
    flushSync();
}

/** The container of the backup card on the page, and the card in it; throws when either is missing. */
function backupCard(): {container: HTMLElement; card: HTMLElement} {
    const container = screen.getByTestId('instance-blocked-backup');
    return {container, card: within(container).getByTestId('backup-download-card-stub')};
}

/** No backup card: no container, and the card mounted nowhere else either (mounted, the real one reads the backup API). */
function expectNoBackupCard(why: string): void {
    expect(screen.queryByTestId('instance-blocked-backup'), why).toBeNull();
    expect(screen.queryByTestId('backup-download-card-stub'), 'nor mounted anywhere else: mounted, the real card reads the backup API').toBeNull();
}

/**
 * The control of an absence: the same page, for the user the case signed in, told `backup_available: true`, shows the
 * card. Without it an absence would also hold on a page that never shows the card. The control page is unmounted before
 * this returns, so that the case's own page is alone on the screen.
 */
async function expectCardWhenAvailable(): Promise<void> {
    const {answer} = mountPage();
    await answerWith(answer, BACKUP_AVAILABLE);
    expect(screen.queryByTestId('instance-blocked-backup'), 'Control: told that a backup is available, the same page shows the card').not.toBeNull();
    expect(backupCard().card, 'Control: the card is in its container').toBeInTheDocument();
    cleanup();
}

beforeAll(async () => {
    await setupI18n();
    // Negative assertions below would pass vacuously in an environment where effects never run.
    assertEffectsRun();
});

beforeEach(() => {
    mocks.auth.set({user: {is_superuser: false}});
    mocks.getInstanceBlock.mockReset();
    instanceBlock.markBlocked();
});

afterEach(() => {
    cleanup();
    instanceBlock.clear();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
});

describe('InstanceBlockedPage — the explanation', () => {
    it.each([
        ['an administrator', {is_superuser: true}, 'instance.block.adminDescription'],
        ['a regular user', {is_superuser: false}, 'instance.block.userDescription'],
        ['a user without the flag', {}, 'instance.block.userDescription'],
    ])('tells %s what the block means for them', async (_case, user, key) => {
        mocks.auth.set({user});
        mountPage();

        expect(screen.getByTestId('instance-blocked')).toBeInTheDocument();
        expect(text(screen.getByTestId('instance-blocked-description'))).toBe(translate(key));
    });

    it('tells a page without a signed-in user what it tells a regular user', () => {
        mocks.auth.set({user: null});
        mountPage();

        expect(text(screen.getByTestId('instance-blocked-description'))).toBe(translate('instance.block.userDescription'));
    });

    it('reads the block through the generated client by default', async () => {
        mocks.getInstanceBlock.mockResolvedValue({blocked: true, deletion_date: DELETION_DAY});
        render(InstanceBlockedPage, {props: {onlogout: vi.fn()}});
        flushSync();

        expect(mocks.getInstanceBlock, 'GET /system/block, once at mount').toHaveBeenCalledTimes(1);
        await mocks.getInstanceBlock.mock.results[0].value;
        await tick();
        flushSync();
        expect(screen.getByTestId('instance-blocked-deletion-date')).toBeInTheDocument();
    });
});

describe('InstanceBlockedPage — the deletion date', () => {
    it.each([
        ['America/Los_Angeles', 13],
        ['Pacific/Kiritimati', 14],
        ['UTC', 14],
    ])('shows the ISO day as the same day in the interface locale, in the time zone %s', async (zone, localDayOfUtcMidnight) => {
        vi.stubEnv('TZ', zone);
        // Barrier: the time zone is in force, so a day read or written in local time would show here.
        expect(new Date(`${DELETION_DAY}T00:00:00Z`).getDate(), `local day of midnight UTC in ${zone}`).toBe(localDayOfUtcMidnight);
        const {answer} = mountPage();

        await answerWith(answer, {blocked: true, deletion_date: DELETION_DAY});

        const day = new Intl.DateTimeFormat(uiLocale(), {dateStyle: 'long', timeZone: 'UTC'}).format(Date.UTC(2026, 10, 14));
        expect(day, 'Barrier: the expected day names the 14th').toMatch(/14/);
        expect(text(screen.getByTestId('instance-blocked-deletion-date'))).toBe(translate('instance.block.deletionDate', {date: day}));
    });

    it.each([
        ['null', null],
        ['absent', undefined],
        ['empty', ''],
    ])('shows no date when the deletion date is %s', async (_case, deletionDate) => {
        const {answer} = mountPage();

        await answerWith(answer, {blocked: true, deletion_date: deletionDate});

        expect(screen.getByTestId('instance-blocked'), 'the page stays').toBeInTheDocument();
        expect(screen.queryByTestId('instance-blocked-deletion-date')).toBeNull();
        expect(instanceBlock.blocked, 'still blocked').toBe(true);
    });
});

describe('InstanceBlockedPage — the subscription link', () => {
    it.each([
        ['an https address', BILLING_URL],
        ['a scheme in capitals, which the backend accepts too', 'HTTPS://billing.example.test/acme'],
    ])('gives an administrator a link to the subscription, for %s', async (_case, address) => {
        mocks.auth.set({user: {is_superuser: true}});
        const {answer} = mountPage();

        await answerWith(answer, {blocked: true, deletion_date: DELETION_DAY, billing_url: address});

        const link = screen.getByTestId('instance-blocked-billing');
        expect(link.tagName, 'a link').toBe('A');
        expect(link.getAttribute('href')).toBe(address);
        expect(link.getAttribute('target'), 'opened in a new tab').toBe('_blank');
        expect(link.getAttribute('rel')?.split(/\s+/), 'without opener or referrer').toEqual(expect.arrayContaining(['noopener', 'noreferrer']));
        expect(text(link)).toBe(translate('instance.block.manageSubscription'));
        const icon = link.querySelector('svg');
        expect(icon, 'Barrier: the external-link icon is in the link').not.toBeNull();
        expect(icon?.getAttribute('aria-hidden'), 'the icon is hidden from assistive technology').toBe('true');
        expect(screen.getByRole('link', {name: translate('instance.block.manageSubscription')}), 'the accessible name is the text alone').toBe(link);
        expect(screen.getByTestId('instance-blocked-logout'), 'the logout button stays').toBeInTheDocument();
    });

    it.each([
        ['a regular user', {is_superuser: false}],
        ['a user without the flag', {}],
        ['a page without a signed-in user', null],
    ])('gives %s no link, even when the answer carries an address', async (_case, user) => {
        mocks.auth.set({user});
        const {answer} = mountPage();

        await answerWith(answer, {blocked: true, deletion_date: DELETION_DAY, billing_url: BILLING_URL});

        expect(screen.getByTestId('instance-blocked-deletion-date'), 'Barrier: the page painted the answer').toBeInTheDocument();
        expect(screen.queryByTestId('instance-blocked-billing')).toBeNull();
        expect(screen.getByTestId('instance-blocked-logout'), 'the logout button stays').toBeInTheDocument();
    });

    it.each<[string, BlockAnswer]>([
        ['null', {blocked: true, deletion_date: DELETION_DAY, billing_url: null}],
        ['absent', {blocked: true, deletion_date: DELETION_DAY}],
    ])('gives an administrator no link when the address is %s', async (_case, value) => {
        mocks.auth.set({user: {is_superuser: true}});
        const {answer} = mountPage();

        await answerWith(answer, value);

        expect(screen.getByTestId('instance-blocked-deletion-date'), 'Barrier: the page painted the answer').toBeInTheDocument();
        expect(screen.queryByTestId('instance-blocked-billing')).toBeNull();
        expect(screen.getByTestId('instance-blocked-logout'), 'the logout button stays').toBeInTheDocument();
    });

    it('never makes a link of an address that is not http(s), even for an administrator', async () => {
        mocks.auth.set({user: {is_superuser: true}});
        const {answer} = mountPage();

        await answerWith(answer, {blocked: true, deletion_date: DELETION_DAY, billing_url: SCRIPT_ADDRESS});

        expect(screen.getByTestId('instance-blocked-deletion-date'), 'Barrier: the page painted the answer').toBeInTheDocument();
        expect(screen.queryByTestId('instance-blocked-billing')).toBeNull();
        expect(document.querySelector(`[href="${SCRIPT_ADDRESS}"]`), 'the address is in no link of the page').toBeNull();
        expect(screen.getByTestId('instance-blocked-logout'), 'the logout button stays').toBeInTheDocument();
    });
});

describe('InstanceBlockedPage — the answer of the server', () => {
    it('clears the flag and reloads the page when the instance is no longer blocked', async () => {
        const reload = vi.fn().mockName('location.reload');
        vi.stubGlobal('location', {href: 'http://librefolio.test/dashboard', pathname: '/dashboard', search: '', hash: '', origin: 'http://librefolio.test', reload});
        const {answer} = mountPage();

        await answerWith(answer, {blocked: false, deletion_date: null});

        expect(instanceBlock.blocked, 'the block was lifted meanwhile: the flag is cleared').toBe(false);
        expect(reload, 'the app starts again from a clean page').toHaveBeenCalledTimes(1);
    });

    it('stays, without a date and still blocked, when the request fails', async () => {
        const reload = vi.fn().mockName('location.reload');
        vi.stubGlobal('location', {href: 'http://librefolio.test/dashboard', pathname: '/dashboard', search: '', hash: '', origin: 'http://librefolio.test', reload});
        const {answer} = mountPage();

        await failWith(answer, new Error('the server does not answer'));

        expect(screen.getByTestId('instance-blocked'), 'the refusal that showed the page is enough').toBeInTheDocument();
        expect(screen.getByTestId('instance-blocked-description')).toBeInTheDocument();
        expect(screen.queryByTestId('instance-blocked-deletion-date')).toBeNull();
        expect(instanceBlock.blocked).toBe(true);
        expect(reload).not.toHaveBeenCalled();
    });
});

describe('InstanceBlockedPage — signing out', () => {
    it('calls onlogout from the logout button', async () => {
        const {answer, onlogout} = mountPage();
        await answerWith(answer, {blocked: true, deletion_date: null});

        await fireEvent.click(screen.getByTestId('instance-blocked-logout'));

        expect(onlogout).toHaveBeenCalledTimes(1);
    });
});

describe('InstanceBlockedPage — the backup card (decision 12)', () => {
    it('shows the backup card below the alert and outside it when the server says a backup is available', async () => {
        mocks.auth.set({user: {is_superuser: true}});
        const {answer} = mountPage();

        await answerWith(answer, BACKUP_AVAILABLE);

        expect(screen.getByTestId('instance-blocked-deletion-date'), 'Barrier: the page painted the answer').toBeInTheDocument();
        const {container} = backupCard();
        expect(screen.getAllByTestId('backup-download-card-stub'), 'one card, the one in the container').toHaveLength(1);
        expect(screen.getByTestId('instance-blocked').contains(container), 'on the block page').toBe(true);
        const alert = screen.getByRole('alert');
        expect(within(alert).getByTestId('instance-blocked-description'), 'the alert still explains the block').toBeInTheDocument();
        expect(within(alert).getByTestId('instance-blocked-logout'), 'and still holds the logout button').toBeInTheDocument();
        expect(alert.contains(container), 'the card is outside the alert: a screen reader announces the block, not the card').toBe(false);
        expect(container.closest(LIVE_REGION), 'nor in any other live region').toBeNull();
        expect(alert.compareDocumentPosition(container), 'below the alert: read after the block').toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    });

    it('names the backup section by the level-2 heading it holds before the card: the only one of the page, after the page title', async () => {
        mocks.auth.set({user: {is_superuser: true}});
        const {answer} = mountPage();

        await answerWith(answer, BACKUP_AVAILABLE);

        expect(screen.getByTestId('instance-blocked-deletion-date'), 'Barrier: the page painted the answer').toBeInTheDocument();
        const headings = screen.getAllByRole('heading', {level: 2});
        expect(headings, 'one level-2 heading on the page').toHaveLength(1);
        const [heading] = headings;
        const {container, card} = backupCard();
        expect(container.contains(heading), 'held by the backup section').toBe(true);
        expect(heading.id, 'Barrier: the heading has an id to be named by').not.toBe('');
        expect(container.getAttribute('aria-labelledby'), 'the section is labelled by its heading').toBe(heading.id);
        expect(document.getElementById(heading.id), 'and the reference resolves to that heading, not to another element with its id').toBe(heading);
        expect(text(heading), 'the heading is not empty: the section has a name').not.toBe('');
        expect(screen.getByRole('region', {name: text(heading)}), 'assistive technology reads a region named by its heading').toBe(container);
        expect(heading.compareDocumentPosition(card), 'the heading comes before the card, and its h3').toBe(Node.DOCUMENT_POSITION_FOLLOWING);
        const title = screen.getByRole('heading', {level: 1});
        expect(title.compareDocumentPosition(heading), 'the page title comes first: h1, then h2').toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    });

    it.each<[string, {is_superuser?: boolean} | null]>([
        ['a regular user', {is_superuser: false}],
        ['a user without the flag', {}],
        ['a page without a signed-in user', null],
    ])('shows the card for %s when the server says a backup is available: the server decides, not the role', async (_case, user) => {
        mocks.auth.set({user});
        const {answer} = mountPage();

        await answerWith(answer, BACKUP_AVAILABLE);

        expect(screen.getByTestId('instance-blocked-deletion-date'), 'Barrier: the page painted the answer').toBeInTheDocument();
        expect(text(screen.getByTestId('instance-blocked-description')), 'Barrier: the page sees no administrator').toBe(translate('instance.block.userDescription'));
        const {container} = backupCard();
        expect(screen.getByRole('alert').contains(container), 'outside the alert').toBe(false);
    });

    it.each<[string, {is_superuser?: boolean}]>([
        ['an administrator', {is_superuser: true}],
        ['a regular user', {is_superuser: false}],
    ])('gives %s no card when the server says no backup is available', async (_case, user) => {
        mocks.auth.set({user});
        await expectCardWhenAvailable();
        const {answer} = mountPage();

        await answerWith(answer, {...BACKUP_AVAILABLE, backup_available: false});

        expect(screen.getByTestId('instance-blocked-deletion-date'), 'Barrier: the page painted the answer').toBeInTheDocument();
        expectNoBackupCard('told `backup_available: false`, no card, whatever the role');
        expect(screen.getByTestId('instance-blocked-logout'), 'the logout button stays').toBeInTheDocument();
    });

    it.each<[string, {is_superuser?: boolean}]>([
        ['an administrator', {is_superuser: true}],
        ['a regular user', {is_superuser: false}],
    ])('gives %s no card when the answer does not say whether a backup is available', async (_case, user) => {
        mocks.auth.set({user});
        await expectCardWhenAvailable();
        const {answer} = mountPage();

        await answerWith(answer, {blocked: true, deletion_date: DELETION_DAY});

        expect(screen.getByTestId('instance-blocked-deletion-date'), 'Barrier: the page painted the answer').toBeInTheDocument();
        expectNoBackupCard('without `backup_available`, no card: the page does not guess it from the role');
    });

    it('shows no card while the answer is pending, even to an administrator, and the card once it says a backup is available', async () => {
        mocks.auth.set({user: {is_superuser: true}});
        const {answer} = mountPage();
        // Let the page paint all that does not wait for the answer: a flush, not a clock.
        await tick();
        flushSync();

        expect(screen.getByTestId('instance-blocked'), 'Barrier: the page stands while the request is out').toBeInTheDocument();
        expect(screen.getByTestId('instance-blocked-logout')).toBeInTheDocument();
        expectNoBackupCard('no card before the server said so, not even for an administrator');

        await answerWith(answer, BACKUP_AVAILABLE);

        const {container} = backupCard();
        expect(screen.getByRole('alert').contains(container), 'outside the alert').toBe(false);
    });

    it('gives an administrator no card when the request fails, and the page stands', async () => {
        mocks.auth.set({user: {is_superuser: true}});
        await expectCardWhenAvailable();
        const {answer} = mountPage();

        await failWith(answer, new Error('the server does not answer'));

        expect(screen.getByTestId('instance-blocked'), 'the page stands').toBeInTheDocument();
        expect(screen.getByRole('heading', {level: 1, name: translate('instance.block.title')}), 'with its title').toBeInTheDocument();
        expect(screen.getByTestId('instance-blocked-logout'), 'and its logout button').toBeInTheDocument();
        expectNoBackupCard('no answer, no card: the page does not guess it from the role');
        expect(instanceBlock.blocked, 'still blocked').toBe(true);
    });

    it('shows no card when the instance is no longer blocked, even with a backup available: the page reloads', async () => {
        const reload = vi.fn().mockName('location.reload');
        vi.stubGlobal('location', {href: 'http://librefolio.test/dashboard', pathname: '/dashboard', search: '', hash: '', origin: 'http://librefolio.test', reload});
        mocks.auth.set({user: {is_superuser: true}});
        await expectCardWhenAvailable();
        const {answer} = mountPage();

        await answerWith(answer, {...BACKUP_AVAILABLE, blocked: false, deletion_date: null});

        expect(instanceBlock.blocked, 'Barrier: the page read the answer, and the block was lifted meanwhile: the flag is cleared').toBe(false);
        expect(reload, 'the app starts again from a clean page').toHaveBeenCalledTimes(1);
        expectNoBackupCard('no card on a page that starts again');
    });
});

describe('InstanceBlockedPage — toasts', () => {
    it.each<[string, {is_superuser?: boolean}, boolean]>([
        ['an administrator, with the backup card', {is_superuser: true}, true],
        ['a regular user, without it', {is_superuser: false}, false],
    ])('shows %s a toast pushed while the page is mounted: the page has a toast container of its own', async (_case, user, backupAvailable) => {
        mocks.auth.set({user});
        const {answer} = mountPage();
        await answerWith(answer, {blocked: true, deletion_date: DELETION_DAY, backup_available: backupAvailable});
        expect(screen.getByTestId('instance-blocked-deletion-date'), 'Barrier: the page painted the answer').toBeInTheDocument();
        expect(screen.queryByTestId('toast-warning'), 'Barrier: no toast on the page before the push (none left by another test)').toBeNull();

        const id = toasts.warning(TOAST_PROBE, 0);
        onTestFinished(() => toasts.dismiss(id));
        flushSync();

        // Only the page is mounted here: a toast in the document is the page's own container at work.
        const toast = screen.getByTestId('toast-warning');
        expect(toast, 'the toast shows on the block page').toBeVisible();
        expect(within(toast).getByTestId('instance-blocked-toast-probe'), 'and it is the one this case pushed').toBeInTheDocument();
        const backup = screen.queryByTestId('instance-blocked-backup');
        expect(backup !== null, `the case: ${backupAvailable ? 'the backup card is on the page' : 'no backup card on the page'}`).toBe(backupAvailable);
        expect(screen.getByRole('alert').contains(toast), 'outside the alert: a toast does not have the block read out again').toBe(false);
        expect(backup?.contains(toast) ?? false, 'outside the backup section: the toasts do not depend on the card').toBe(false);
    });
});
