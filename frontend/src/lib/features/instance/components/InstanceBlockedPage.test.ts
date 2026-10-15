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
 *   - when the answer says the instance is no longer blocked, the flag is cleared and the page reloads;
 *   - when the answer fails, the page stays, without a date, and the flag stays on;
 *   - the logout button (`instance-blocked-logout`) calls `onlogout`.
 *
 * Answers are deferreds the test settles by hand: the component awaits the promise first, so its continuation has run
 * when the test's own `await` of the same promise resumes, and `tick()` then lets the page paint it. No clock. Texts are
 * compared only with what the catalogue answers for the key (`translate`), never with a literal, and the date with the
 * interface locale of the same module the component reads. `$lib/stores/app/auth` is a writable the test sets, and
 * `window.location` is stubbed only where a reload is expected.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import {_} from '$lib/i18n';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {instanceBlock} from '../instanceBlock.svelte';
import InstanceBlockedPage from './InstanceBlockedPage.svelte';

type BlockAnswer = {blocked: boolean; deletion_date?: string | null; billing_url?: string | null};

const mocks = await vi.hoisted(async () => {
    const {writable} = await import('svelte/store');
    return {
        auth: writable<{user: {is_superuser?: boolean} | null}>({user: null}),
        getInstanceBlock: vi.fn().mockName('zodiosApi.get_instance_block_api_v1_system_block_get'),
    };
});

vi.mock('$lib/stores/app/auth', () => ({auth: mocks.auth}));
vi.mock('$lib/api', () => ({zodiosApi: {get_instance_block_api_v1_system_block_get: mocks.getInstanceBlock}}));

const DELETION_DAY = '2026-11-14';
/** Where the subscription is managed, as `GET /system/block` gives it to an administrator. */
const BILLING_URL = 'https://billing.example.test/acme';
/** A placeholder of an address that is not http(s): nothing here follows it, and the page must never make it a link. */
const SCRIPT_ADDRESS = 'javascript:void(0)';

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
