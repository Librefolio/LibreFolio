// @vitest-environment jsdom
/**
 * currentLanguage — the language store follows svelte-i18n until the user picks a language (backlog TC-6, A-8).
 *
 * The bug: a first visit with the browser in `it-IT`, nothing in `localStorage`. The page renders in Italian, the
 * language selector says English. `initI18n()` asks svelte-i18n for `it`, but svelte-i18n moves its `locale` store to
 * `it` only once the Italian dictionary has loaded; `currentLanguage.init()`, called at mount with no stored
 * preference, read `locale` once — still the default, `en` — and unsubscribed, so the store stayed `en` for good.
 *
 * The contract of the fix (narrow on purpose):
 *   - `init()` with no stored preference makes the store follow `locale` — supported values only (en, it, fr, es),
 *     anything else ignored — until a language is picked through the store (`currentLanguage.set(…)` or `cycle()`, by
 *     the user or by the app on their behalf): from then on `locale` no longer moves it;
 *   - `init()` with a stored preference sets the store and `locale` to it, and does not follow;
 *   - a second `init()` adds no second follower;
 *   - on the server (`browser` false) `init()` does nothing: not pinned here, this file runs as a browser.
 *
 * The harness. svelte-i18n's `locale` is a real writable, a fresh one for every test, behind the one object the module
 * imports (an earlier test's follower stays subscribed to its own writable, which nothing feeds again); its `subscribe`
 * is a spy that also counts the subscriptions still open: the followers. `$app/environment` says browser. The store is
 * created at import, from `localStorage`, so every test clears the storage and takes a freshly imported module
 * (`vi.resetModules()` + `import()`). The storage is a Map this file owns, as in `HeaderToggles.i18n.test.ts`: Node 26
 * ships a global `localStorage` that hides jsdom's and is unavailable without `--localstorage-file`. Every change is
 * synchronous and read back with `get`: no clock anywhere.
 *
 * Red today: every case that needs the store to follow `locale` — the first, the barrier of the second, the premise of
 * the third, and the last (no follower is kept at all). Green today, a guard the fix must keep: a stored preference.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {get, type Writable} from 'svelte/store';

/** What svelte-i18n's `locale` can hold: a supported code, any other tag, or nothing yet. */
type Locale = string | null | undefined;
type LanguageModule = typeof import('./language');
type CurrentLanguage = LanguageModule['currentLanguage'];

/** The `locale` writable of one test, and how many subscriptions to it are open. */
interface LocaleTarget {
    store: Writable<Locale>;
    open: number;
}

const mocks = await vi.hoisted(async () => {
    const {writable} = await import('svelte/store');
    const current: {target: LocaleTarget} = {target: {store: writable<Locale>('en'), open: 0}};
    return {
        /** svelte-i18n's `locale`, as the module imports it: one object, on the writable of the running test. */
        locale: {
            /** A spy that also counts the subscriptions it hands out until each is closed: the followers. */
            subscribe: vi.fn((run: (value: Locale) => void, invalidate?: () => void) => {
                const target = current.target;
                const unsubscribe = target.store.subscribe(run, invalidate);
                target.open += 1;
                let closed = false;
                return () => {
                    if (!closed) {
                        closed = true;
                        target.open -= 1;
                    }
                    unsubscribe();
                };
            }),
            set: (value: Locale) => current.target.store.set(value),
            update: (updater: (value: Locale) => Locale) => current.target.store.update(updater),
        },
        /** Starts the running test on a fresh `locale` holding `value`, with no subscription open. */
        resetLocale(value: Locale): void {
            current.target = {store: writable<Locale>(value), open: 0};
        },
        /** How many subscriptions to the running test's `locale` are open now. */
        openSubscriptions: (): number => current.target.open,
    };
});

vi.mock('svelte-i18n', async (importOriginal) => ({...(await importOriginal<typeof import('svelte-i18n')>()), locale: mocks.locale}));
// The shared mock says server, where the store does nothing at all.
vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

// The storage the store reads at import and `saveLocalePreference` writes. Stubbed so the file owns it: Node 26 ships a
// global `localStorage` that is unavailable without --localstorage-file, and it hides jsdom's. Installed before any test
// imports the module, which only `freshPageLoad` does.
const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
    clear: () => storage.clear(),
});

/** The language store of a page load that has just begun: created at import, from what `localStorage` holds now. */
async function freshPageLoad(): Promise<LanguageModule> {
    vi.resetModules();
    return import('./language');
}

beforeEach(() => {
    // A first visit: nothing stored, and svelte-i18n still on its default.
    localStorage.clear();
    mocks.resetLocale('en');
    mocks.locale.subscribe.mockClear();
});

describe('currentLanguage.init() — no stored preference: the store follows svelte-i18n', () => {
    it('follows locale when svelte-i18n moves it after the dictionary has loaded: the first visit of an Italian browser', async () => {
        const {currentLanguage} = await freshPageLoad();
        currentLanguage.init();
        expect(get(currentLanguage), 'premise: at mount svelte-i18n still holds the default').toBe('en');

        // The Italian dictionary has loaded: only now does svelte-i18n move `locale`.
        mocks.locale.set('it');

        expect(get(currentLanguage), 'the selector shows the language the page is drawn in').toBe('it');
    });

    it.each(['de', null])('ignores %j from locale, and keeps following the supported values', async (unsupported) => {
        const {currentLanguage} = await freshPageLoad();
        currentLanguage.init();

        mocks.locale.set(unsupported);
        expect(get(currentLanguage), 'an unsupported value leaves the store where it was').toBe('en');

        // The barrier: the store does follow, so the value above was refused, not missed.
        mocks.locale.set('it');
        expect(get(currentLanguage), 'the barrier: a supported value is followed').toBe('it');
        mocks.locale.set(unsupported);
        expect(get(currentLanguage), 'refused again once the store follows another language').toBe('it');
    });

    it.each([
        ['set(es)', (store: CurrentLanguage) => store.set('es'), 'es'],
        ['cycle(), from it to fr', (store: CurrentLanguage) => store.cycle(), 'fr'],
    ])('stops following once a language is picked through the store: %s', async (_label, pick, picked) => {
        const {currentLanguage} = await freshPageLoad();
        currentLanguage.init();
        mocks.locale.set('it');
        expect(get(currentLanguage), 'premise: the store follows locale until the pick').toBe('it');

        pick(currentLanguage);
        expect(get(currentLanguage), 'the pick').toBe(picked);

        mocks.locale.set('it');

        expect(get(currentLanguage), 'a later move of locale leaves the pick alone').toBe(picked);
    });

    it('keeps one follower however many times init() runs', async () => {
        const {currentLanguage} = await freshPageLoad();

        currentLanguage.init();
        currentLanguage.init();

        expect(mocks.locale.subscribe, 'init() subscribes to locale').toHaveBeenCalled();
        expect(mocks.openSubscriptions(), 'one subscription kept open: not one per init(), and not none').toBe(1);
        mocks.locale.set('it');
        expect(get(currentLanguage), 'and that one follows').toBe('it');
    });
});

describe('currentLanguage.init() — a stored preference', () => {
    it('takes it, hands it to locale, and does not follow locale', async () => {
        localStorage.setItem('librefolio-locale', 'fr');
        const {currentLanguage} = await freshPageLoad();

        currentLanguage.init();

        expect(get(currentLanguage)).toBe('fr');
        expect(get(mocks.locale), 'svelte-i18n is told the stored language').toBe('fr');

        mocks.locale.set('it');

        expect(get(currentLanguage), 'the stored preference is the user’s: locale does not move it').toBe('fr');
    });
});
