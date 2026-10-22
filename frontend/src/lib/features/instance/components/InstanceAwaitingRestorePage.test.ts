// @vitest-environment jsdom
/**
 * InstanceAwaitingRestorePage — what the customer sees while the hosting panel restores the instance on an empty volume
 * (workstream H, lot H-62).
 *
 * In that mode the backend answers `GET /api/v1/system/instance` with `mode: "awaiting_restore"` and refuses every other
 * route with `423 {"detail": {"code": "instance_awaiting_restore"}}`. The root layout's `AwaitingRestoreGate` then shows
 * this page instead of the app or the login.
 *
 * The contract under test:
 *   - the root `instance-awaiting-restore` holds a `role="status"` section (polite: information, not an error; no
 *     `role="alert"` anywhere) with an `h1` reading `instance.awaitingRestore.title` and the paragraph
 *     `instance-awaiting-restore-message` reading `instance.awaitingRestore.message`; the root also holds the note
 *     `instance-awaiting-restore-auto` (`instance.awaitingRestore.autoReload`) and the button
 *     `instance-awaiting-restore-retry` named `instance.awaitingRestore.retry`;
 *   - nothing else to act on: no logout button (the retry is the only button), no link, no form, no field;
 *   - the four keys have a string in all four shipped catalogues (`$lib/i18n/{en,it,fr,es}.json`);
 *   - the background is the login page's own `AnimatedBackground` (`$lib/components/ui/AnimatedBackground.svelte`,
 *     `data-testid="animated-background"`), mounted inside the page and imported from that module, never a copy;
 *   - clicking retry calls `onretry`; by default `onretry` is `window.location.reload()`;
 *   - every `pollMs` (default 30 000) the page calls `fetchMode()`: on `"normal"` it calls `onretry()` once and stops
 *     polling; any other answer, `undefined`, and a failed fetch keep the polling going (a failure is swallowed, never an
 *     unhandled rejection); unmounting stops the polling. By default `fetchMode` reads `GET /system/instance` (through
 *     the generated client) and returns its `mode`.
 *
 * Labels are read in a marker locale (the pattern of `DataEditor.test.ts` / `ToastContainer.test.ts`): a private-use
 * language where every key reads `⟦key⟧`, so a label taken from the catalogue reads its marker and a literal reads as
 * itself. Nothing reads what a language says. Whether the catalogues hold the keys is asked of the JSON files.
 *
 * Polling runs on fake timers (`setTimeout`/`setInterval` and their clears only, so Svelte's microtask scheduling stays
 * real), advanced with `advanceTimersByTimeAsync`, which also drains the promise of each answer: no real wait. A case
 * counts the calls made before it advances, so it holds whether or not the page also asks once at mount.
 *
 * `$lib/api` is a mock whose generated method is the spy of the default `fetchMode`; nothing reaches the network.
 *
 * Red until H-62: the component does not exist (the whole file fails to import), and the catalogues have no
 * `instance.awaitingRestore` keys.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, onTestFinished, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {addMessages} from 'svelte-i18n';
import {readFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import {_ as translate} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import InstanceAwaitingRestorePage from './InstanceAwaitingRestorePage.svelte';

const mocks = vi.hoisted(() => ({
    getInstanceConfig: vi.fn().mockName('zodiosApi.get_instance_config_api_v1_system_instance_get'),
}));

vi.mock('$lib/api', () => ({zodiosApi: {get_instance_config_api_v1_system_instance_get: mocks.getInstanceConfig}}));

const KEYS = {
    title: 'instance.awaitingRestore.title',
    message: 'instance.awaitingRestore.message',
    autoReload: 'instance.awaitingRestore.autoReload',
    retry: 'instance.awaitingRestore.retry',
} as const;

/** The default interval of the contract: 30 s. */
const DEFAULT_POLL_MS = 30_000;
/** A short interval for the injected cases: the arithmetic stays readable. */
const POLL_MS = 1_000;
/** The live regions: the page is a polite status, never an alert. */
const ALERT = '[role="alert"], [aria-live="assertive"]';

// ---------------------------------------------------------------------------
// Marker locale — the pattern of DataEditor.test.ts (W-B8).

/** A private-use language (BCP 47 reserves qaa–qtz): Intl accepts it, and it is none of the app's catalogues. */
const MARKER_LOCALE = 'qaa';
/** The four shipped catalogues, by language. */
const SHIPPED_CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

/** How a label reads in the marker locale: `⟦key⟧`. */
const marked = (key: string): string => `⟦${key}⟧`;

/** The value behind a dotted key of a catalogue, if any. */
const leafOf = (catalogue: unknown, key: string): unknown => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);

/** Every dotted key of a catalogue that holds a string. */
function stringKeysOf(node: unknown, prefix = ''): string[] {
    if (typeof node === 'string') return [prefix];
    if (node === null || typeof node !== 'object') return [];
    return Object.entries(node).flatMap(([part, child]) => stringKeysOf(child, prefix ? `${prefix}.${part}` : part));
}

/** Each of `keys` that some catalogue has no string for, with those catalogues: `{}` when all four have all of them. */
function catalogueGaps(keys: readonly string[]): Record<string, string[]> {
    const gaps = keys.map((key) => [key, Object.entries(SHIPPED_CATALOGUES).flatMap(([lang, catalogue]) => (typeof leafOf(catalogue, key) === 'string' ? [] : [lang]))] as const);
    return Object.fromEntries(gaps.filter(([, langs]) => langs.length > 0));
}

/** Switch svelte-i18n to the marker locale: every key of the English catalogue, and each key of this page, reads as its marker. */
async function useMarkerLocale(): Promise<void> {
    const messages: Record<string, string> = Object.fromEntries(stringKeysOf(en).map((key) => [key, marked(key)]));
    for (const key of Object.values(KEYS)) messages[key] = marked(key);
    addMessages(MARKER_LOCALE, messages);
    await setupI18n(MARKER_LOCALE);
}

function text(element: Element): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** Fake only the timers: Svelte schedules on microtasks, which stay real. */
function useFakeTimers(): void {
    vi.useFakeTimers({toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval']});
}

/** Mount with an injected `fetchMode` and `onretry`, and return them. */
function mountPolling(fetchMode: () => Promise<string | undefined>, pollMs = POLL_MS) {
    const spy = vi.fn(fetchMode).mockName('fetchMode');
    const onretry = vi.fn().mockName('onretry');
    const view = render(InstanceAwaitingRestorePage, {props: {fetchMode: spy, onretry, pollMs}});
    flushSync();
    expect(screen.getByTestId('instance-awaiting-restore'), 'Barrier: the page is mounted').toBeInTheDocument();
    return {fetchMode: spy, onretry, view};
}

beforeAll(async () => {
    await setupI18n('en');
    // Negative assertions below (no further poll, no reload) would pass vacuously where effects never run.
    assertEffectsRun();
});

beforeEach(async () => {
    mocks.getInstanceConfig.mockReset();
    await useMarkerLocale();
});

afterEach(async () => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    await setupI18n('en');
});

describe('InstanceAwaitingRestorePage — the catalogues', () => {
    it('has a string for each of its four keys in all four shipped catalogues', () => {
        expect(catalogueGaps(Object.values(KEYS))).toEqual({});
    });

    it('control: the marker locale is live', () => {
        expect(get(translate)(KEYS.title)).toBe(marked(KEYS.title));
    });
});

describe('InstanceAwaitingRestorePage — what it shows', () => {
    it('reads its title, message, note and retry label from the catalogue', () => {
        mountPolling(() => new Promise(() => {}));
        expect(get(translate)(KEYS.title), 'control: the marker locale is live').toBe(marked(KEYS.title));
        const root = screen.getByTestId('instance-awaiting-restore');

        expect(text(within(root).getByRole('heading', {level: 1}))).toBe(marked(KEYS.title));
        expect(text(within(root).getByTestId('instance-awaiting-restore-message'))).toBe(marked(KEYS.message));
        expect(text(within(root).getByTestId('instance-awaiting-restore-auto'))).toBe(marked(KEYS.autoReload));
        const retry = within(root).getByTestId('instance-awaiting-restore-retry');
        expect(retry.tagName, 'a real button').toBe('BUTTON');
        expect(retry).toHaveAccessibleName(marked(KEYS.retry));
    });

    it('announces the title and the message politely, as a status, never as an alert', () => {
        mountPolling(() => new Promise(() => {}));
        const root = screen.getByTestId('instance-awaiting-restore');

        const status = within(root).getByRole('status');
        expect(within(status).getByRole('heading', {level: 1}), 'the h1 is inside the status').toBeInTheDocument();
        expect(within(status).getByTestId('instance-awaiting-restore-message'), 'the message is inside the status').toBeInTheDocument();
        expect(status.getAttribute('aria-live') ?? 'polite', 'a status is polite').toBe('polite');
        expect(document.body.querySelectorAll(ALERT), 'information, not an error').toHaveLength(0);
    });

    it('offers nothing to act on but the retry: no logout, no link, no form, no field', () => {
        mountPolling(() => new Promise(() => {}));
        const root = screen.getByTestId('instance-awaiting-restore');
        // Presence barrier: the page painted its one control, so the absences below are not "nothing rendered yet".
        expect(within(root).getByTestId('instance-awaiting-restore-retry')).toBeVisible();

        expect(within(root).getAllByRole('button'), 'the retry is the only button').toEqual([within(root).getByTestId('instance-awaiting-restore-retry')]);
        expect(document.body.querySelectorAll('a, form, input, select, textarea'), 'no link, no form, no field').toHaveLength(0);
        expect(screen.queryByTestId('instance-blocked-logout'), 'no logout button').toBeNull();
    });

    it("uses the login page's animated background, mounted inside the page", () => {
        mountPolling(() => new Promise(() => {}));
        const root = screen.getByTestId('instance-awaiting-restore');

        expect(within(root).getByTestId('animated-background')).toBeInTheDocument();
        expect(screen.getAllByTestId('animated-background'), 'one background').toHaveLength(1);
    });

    it('imports that background from the shared component, never a copy', () => {
        const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'InstanceAwaitingRestorePage.svelte'), 'utf8');

        expect(source).toMatch(/import\s+AnimatedBackground\s+from\s+['"]\$lib\/components\/ui\/AnimatedBackground\.svelte['"]/);
        expect(source).toMatch(/<AnimatedBackground\b[^>]*\/?>/);
    });
});

describe('InstanceAwaitingRestorePage — the retry button', () => {
    it('calls onretry when clicked', async () => {
        const {onretry} = mountPolling(() => new Promise(() => {}));

        await fireEvent.click(screen.getByTestId('instance-awaiting-restore-retry'));

        expect(onretry).toHaveBeenCalledTimes(1);
    });

    it('reloads the page by default', async () => {
        const reload = vi.fn().mockName('location.reload');
        vi.stubGlobal('location', {href: 'http://librefolio.test/', pathname: '/', search: '', hash: '', origin: 'http://librefolio.test', reload});
        render(InstanceAwaitingRestorePage, {props: {fetchMode: () => new Promise<string | undefined>(() => {})}});
        flushSync();

        await fireEvent.click(screen.getByTestId('instance-awaiting-restore-retry'));

        expect(reload, 'the app starts again from a clean page').toHaveBeenCalledTimes(1);
    });
});

describe('InstanceAwaitingRestorePage — polling the mode', () => {
    it('asks for the mode once every pollMs while the restore is pending', async () => {
        useFakeTimers();
        const {fetchMode, onretry} = mountPolling(() => Promise.resolve('awaiting_restore'));
        const atMount = fetchMode.mock.calls.length;

        await vi.advanceTimersByTimeAsync(POLL_MS - 1);
        expect(fetchMode, 'not before pollMs has elapsed').toHaveBeenCalledTimes(atMount);
        await vi.advanceTimersByTimeAsync(1);
        expect(fetchMode, 'one call at pollMs').toHaveBeenCalledTimes(atMount + 1);
        await vi.advanceTimersByTimeAsync(POLL_MS * 2);
        expect(fetchMode, 'one more call per interval').toHaveBeenCalledTimes(atMount + 3);
        expect(onretry, 'still awaiting the restore: no reload').not.toHaveBeenCalled();
    });

    it('polls every 30 seconds by default', async () => {
        useFakeTimers();
        const fetchMode = vi.fn(() => Promise.resolve<string | undefined>('awaiting_restore')).mockName('fetchMode');
        render(InstanceAwaitingRestorePage, {props: {fetchMode, onretry: vi.fn()}});
        flushSync();
        const atMount = fetchMode.mock.calls.length;

        await vi.advanceTimersByTimeAsync(DEFAULT_POLL_MS - 1);
        expect(fetchMode).toHaveBeenCalledTimes(atMount);
        await vi.advanceTimersByTimeAsync(1);
        expect(fetchMode).toHaveBeenCalledTimes(atMount + 1);
    });

    it('calls onretry once when the mode turns normal, and stops polling', async () => {
        useFakeTimers();
        const answers = ['awaiting_restore', 'normal'];
        const {fetchMode, onretry} = mountPolling(() => Promise.resolve(answers.shift() ?? 'normal'));
        const atMount = fetchMode.mock.calls.length;
        // A mount-time call (if any) consumes the first answer; advance until "normal" has been answered.
        await vi.advanceTimersByTimeAsync(POLL_MS * (2 - atMount));
        expect(answers, 'Barrier: "normal" has been answered').toEqual([]);

        expect(onretry, 'the restore is done: the app starts again').toHaveBeenCalledTimes(1);
        const afterNormal = fetchMode.mock.calls.length;
        await vi.advanceTimersByTimeAsync(POLL_MS * 5);
        expect(fetchMode, 'no polling after "normal"').toHaveBeenCalledTimes(afterNormal);
        expect(onretry, 'onretry once, not once per interval').toHaveBeenCalledTimes(1);
    });

    it.each([
        ['undefined', undefined],
        ['an unknown mode', 'maintenance'],
    ])('keeps polling, without reloading, when the mode is %s', async (_case, mode) => {
        useFakeTimers();
        const {fetchMode, onretry} = mountPolling(() => Promise.resolve(mode));
        const atMount = fetchMode.mock.calls.length;

        await vi.advanceTimersByTimeAsync(POLL_MS * 3);

        expect(fetchMode).toHaveBeenCalledTimes(atMount + 3);
        expect(onretry).not.toHaveBeenCalled();
    });

    it('ignores a failed fetch and keeps polling until the mode turns normal', async () => {
        useFakeTimers();
        // A failure the page lets escape is an unhandled rejection: Node reports it once the microtasks have drained,
        // so the case listens for it and yields one macrotask (`setImmediate`, not faked, no clock) before reading.
        const unhandled: unknown[] = [];
        const onUnhandled = (reason: unknown) => unhandled.push(reason);
        process.on('unhandledRejection', onUnhandled);
        onTestFinished(() => {
            process.off('unhandledRejection', onUnhandled);
        });
        let call = 0;
        const {fetchMode, onretry} = mountPolling(() => {
            call += 1;
            // Every call before the third fails; the third answers "normal".
            return call < 3 ? Promise.reject(new Error('network down')) : Promise.resolve('normal');
        });

        await vi.advanceTimersByTimeAsync(POLL_MS * 3);
        await new Promise<void>((resolve) => setImmediate(resolve));

        expect(fetchMode.mock.calls.length, 'Barrier: the third call happened').toBeGreaterThanOrEqual(3);
        expect(unhandled, 'a failed fetch is swallowed, never an unhandled rejection').toEqual([]);
        expect(onretry, 'the failures were swallowed, and the "normal" after them still reloads').toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('instance-awaiting-restore'), 'a failure never tears the page down').toBeInTheDocument();
    });

    it('stops polling when unmounted', async () => {
        useFakeTimers();
        const {fetchMode, onretry, view} = mountPolling(() => Promise.resolve('awaiting_restore'));
        const atMount = fetchMode.mock.calls.length;
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(fetchMode, 'Barrier: the page polls while mounted').toHaveBeenCalledTimes(atMount + 1);

        view.unmount();
        await vi.advanceTimersByTimeAsync(POLL_MS * 5);

        expect(fetchMode, 'no call after unmount').toHaveBeenCalledTimes(atMount + 1);
        expect(onretry).not.toHaveBeenCalled();
    });

    it('reads the mode from GET /system/instance through the generated client by default', async () => {
        useFakeTimers();
        mocks.getInstanceConfig.mockResolvedValue({profile: 'managed', accounts: {registration_mode: 'invite', registration_locked: true}, mode: 'normal'});
        const onretry = vi.fn().mockName('onretry');
        render(InstanceAwaitingRestorePage, {props: {onretry, pollMs: POLL_MS}});
        flushSync();

        await vi.advanceTimersByTimeAsync(POLL_MS);
        await tick();

        expect(mocks.getInstanceConfig, 'GET /system/instance').toHaveBeenCalled();
        expect(onretry, 'its "normal" mode ends the wait').toHaveBeenCalledTimes(1);
    });
});
