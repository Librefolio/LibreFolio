// @vitest-environment jsdom
/**
 * WhatsNewModal — «What's new since your last version» (component test, Vitest + jsdom; workstream A, lot C-54).
 *
 * The contract under test (approved by the coordinator, 17/10):
 *   - no props: it reads the store `whatsNew` (whatsNewStore.svelte.ts). A `ModalBase` with `testId="whats-new-modal"`,
 *     open while `whatsNew.shouldShow` (WNM-05);
 *   - its heading worded by `changelog.whatsNew.title`; its intro by `changelog.whatsNew.intro` when the payload has a
 *     `since`, by `changelog.whatsNew.introRelease` with `{version}` — the release — when `since` is null (WNM-01, 02);
 *   - one block per chapter to show, `whats-new-chapter` with `data-version`, newest first (WNM-01, 02), its body
 *     rendered as ChangelogModal renders one: Markdown, through sanitizeHtml (WNM-04);
 *   - `whats-new-close`, a button named by `changelog.whatsNew.close`, and `whats-new-full-changelog`, a link to
 *     `CHANGELOG_REMOTE_URL` whose `rel` holds `noopener` and `noreferrer`, named by `changelog.whatsNew.fullChangelog`
 *     (WNM-03);
 *   - the button, Escape and the backdrop close it, each calling `whatsNew.dismiss()` once, and the dialog goes at once,
 *     before the server answers the POST (WNM-06);
 *   - each chapter in the interface language through `localizedChangelog`: English in an English UI, with no pill
 *     (WNM-07); in a translated UI, a translated chapter in that language and an untranslated one in English, with the
 *     pill `whats-new-not-translated` worded by `changelog.notTranslated` inside its block (WNM-08); English while the
 *     translation loads, then the translation (WNM-09); English, each with the pill, when it fails to load (WNM-10).
 *
 * The REAL stores: the modal reads the real `whatsNew`, which reads the real auth store, signed in through its own seam
 * — `checkAuth()` against a programmed `GET /auth/me` whose user carries `whats_new` — so the case does not care where
 * the modal finds `since` and `release`, the store or the user. Each case signs in an account of its own and the hooks
 * sign it out, a new client session each time. `whatsNew.dismiss()` is observed through a pass-through spy, and the POST
 * of `/api/v1/auth/whats-new/seen` through `$lib/api`, matched by its URL (FastAPI names the operation
 * `<function>_api_v1_auth_whats_new_seen_post`); any other operation is an inert spy, pending forever.
 *
 * The changelog module is a fixture, as in ChangelogModal.test.ts — the real one imports the repository's CHANGELOG.md
 * through `?raw`, which the jsdom pipeline refuses — with a faithful fake of `localizedChangelog` that each case
 * programs (English for `en` or a language without a file, a cache filled by a successful load only, a failed chunk
 * resolving to English). The chapters are this file's own words (kiwi, walrus, fenicottero): asserting them is
 * asserting the fixture, never a catalogue. Every catalogue key is read through `_`, which renders `[key]` or
 * `[key|name=value…]`; the UI language is the real svelte-i18n `locale`, put back to English after each case.
 *
 * Written red-first, before `WhatsNewModal.svelte` and its store exist: both are loaded through `import.meta.glob` in
 * `beforeAll`, so every case fails on its own and names what is missing.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Component} from 'svelte';
import type {ChangelogChapter} from './changelog';
import type {AuthUser} from '$lib/types';

/** A chapter as the modal displays it: the module's chapter plus the language its text is in. */
type ShownChapter = ChangelogChapter & {lang: string};

// The English fixture, shared by the module stub and the cases: newest first, the upcoming chapter on top. `chapters`
// is the very array the stub exports as `changelogChapters`; a case may swap a chapter in place (WNM-04), and
// `restore()` puts the fixture back before every case.
const changelogFixture = vi.hoisted(() => {
    const chapter = (version: string, date: string, intro: string, title: string, bullet: string): ChangelogChapter => ({
        version,
        date,
        body: `${intro}\n\n### ${title}\n- ${bullet}\n`,
        sections: [
            {title: null, body: `${intro}\n`, subsections: []},
            {title, body: `- ${bullet}\n`, subsections: []},
        ],
    });
    const chapters: ChangelogChapter[] = [
        chapter('Unreleased', '', 'The **narwhal** is coming.', 'Added', 'narwhal previews'),
        chapter('1.2.1', '2026-10-15', 'The **kiwi** release keeps imports steady.', 'Fixed', 'the kiwi wizard keeps its place'),
        chapter('1.2.0', '2026-10-14', 'The **walrus** release adds reports.', 'Added', 'walrus reports'),
        chapter('1.1.0', '2026-09-07', 'The **otter** release draws charts.', 'Added', 'otter charts'),
        chapter('1.0.0', '2026-07-20', 'The **heron** release.', 'Added', 'heron basics'),
    ];
    const pristine = [...chapters];
    return {
        chapters,
        restore() {
            chapters.splice(0, chapters.length, ...pristine);
        },
    };
});

// A faithful fake of `localizedChangelog` (the one of ChangelogModal.test.ts), driven by what each case programs:
//  - `cached.set(lang, chapters)`: that language already loaded — `peek` answers at once;
//  - `files.set(lang, () => promise)`: its translation file, not loaded yet — `peek` answers undefined and `load` waits
//    for it; a success is cached, a rejection is a failed chunk, which resolves to English and is not cached;
//  - neither: a language without a file — English at once, as for `en`.
// The cache is a `SvelteMap`, as the module's since A-CL1: a window reading `peek` sees a load that fills it.
const localizedFake = await vi.hoisted(async () => {
    const {SvelteMap} = await import('svelte/reactivity');
    const baseLanguage = (locale: string | null | undefined): string => (locale ?? '').trim().toLowerCase().split(/[-_]/)[0] || 'en';
    let memo: {from: ChangelogChapter[]; shown: ShownChapter[]} | null = null;
    const english = (): ShownChapter[] => {
        const chapters = changelogFixture.chapters;
        if (!memo || memo.from.length !== chapters.length || memo.from.some((chapter, i) => chapter !== chapters[i])) {
            memo = {from: [...chapters], shown: chapters.map((chapter) => ({...chapter, lang: 'en'}))};
        }
        return memo.shown;
    };
    const cached = new SvelteMap<string, ShownChapter[]>();
    const files = new Map<string, () => Promise<ShownChapter[]>>();
    const ready = (lang: string): ShownChapter[] | undefined => cached.get(lang) ?? (files.has(lang) ? undefined : english());
    const peek = vi.fn((locale: string | null | undefined): ShownChapter[] | undefined => ready(baseLanguage(locale)));
    const load = vi.fn(async (locale: string | null | undefined): Promise<ShownChapter[]> => {
        const lang = baseLanguage(locale);
        const file = cached.has(lang) ? undefined : files.get(lang);
        if (!file) return ready(lang) ?? english();
        try {
            const shown = await file();
            cached.set(lang, shown);
            return shown;
        } catch {
            return english();
        }
    });
    return {
        baseLanguage,
        english,
        cached,
        files,
        peek,
        load,
        reset() {
            cached.clear();
            files.clear();
            peek.mockClear();
            load.mockClear();
        },
    };
});

vi.mock('$lib/features/changelog/changelog', () => ({
    changelogChapters: changelogFixture.chapters,
    localizedChangelog: {peek: localizedFake.peek, load: localizedFake.load},
    baseLanguage: localizedFake.baseLanguage,
    CHANGELOG_REMOTE_URL: 'https://github.com/Librefolio/LibreFolio/blob/main/CHANGELOG.md',
}));

const api = vi.hoisted(() => ({
    me: vi.fn(),
    logout: vi.fn(),
    /** `POST /api/v1/auth/whats-new/seen`, whatever the generated client calls it. */
    seen: vi.fn(),
}));

// `$lib/api`: the auth store's seam, the POST of this lot matched by its URL — the generated alias
// (`…_api_v1_auth_whats_new_seen_post`) or a bare `post(url)` —, and an inert spy for any other operation, pending
// forever so that nothing it starts can settle behind the assertions or reach the network.
vi.mock('$lib/api', () => {
    const SEEN_ALIAS = /_api_v1_auth_whats_new_seen_post$/;
    const SEEN_URL = /\/api\/v1\/auth\/whats-new\/seen\/?$/;
    const programmed: Record<string, unknown> = {
        get_me_api_v1_auth_me_get: api.me,
        logout_api_v1_auth_logout_post: api.logout,
    };
    const inert = new Map<string, unknown>();
    const pending = () => new Promise(() => {});
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, operation) {
                if (typeof operation !== 'string' || operation === 'then') return undefined;
                if (operation in programmed) return programmed[operation];
                if (SEEN_ALIAS.test(operation)) return api.seen;
                if (operation === 'post') return (url: unknown, ...rest: unknown[]) => (typeof url === 'string' && SEEN_URL.test(url) ? api.seen(...rest) : pending());
                if (!inert.has(operation)) inert.set(operation, vi.fn(pending));
                return inert.get(operation);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

// Keep the real i18n (its `locale` is the UI language), but render every key as a test-owned token.
const translateMock = vi.hoisted(() => vi.fn());
vi.mock('$lib/i18n', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/i18n')>();
    const {readable} = await import('svelte/store');
    return {...actual, _: readable(translateMock)};
});

import {get} from 'svelte/store';
import {tick} from 'svelte';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {auth, getAuthState} from '$lib/stores/app/auth';
import {locale} from '$lib/i18n';
import {CHANGELOG_REMOTE_URL} from './changelog';

// ---------------------------------------------------------------------------
// The translator: keys, never sentences
// ---------------------------------------------------------------------------

/** How `_` renders a key: `[key]`, or `[key|name=value|…]` with its values sorted by name. */
function token(key: unknown, options?: {values?: Record<string, unknown>}): string {
    const descriptor = typeof key === 'object' && key !== null ? (key as {id?: unknown; values?: Record<string, unknown>}) : null;
    const id = String(descriptor ? descriptor.id : key);
    const values = (descriptor ? descriptor.values : options?.values) ?? {};
    const parts = Object.keys(values)
        .sort()
        .map((name) => `${name}=${String(values[name])}`);
    return `[${[id, ...parts].join('|')}]`;
}

function escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** The text of `key`, with or without values — never the text of a longer key that starts with it. */
function keyed(key: string): RegExp {
    return new RegExp(`\\[${escapeRegExp(key)}[|\\]]`);
}

/** The text of `key` with the value `name=value` among its values. */
function keyedWith(key: string, name: string, value: string): RegExp {
    return new RegExp(`\\[${escapeRegExp(key)}(?:\\|[^\\]]*)?\\|${escapeRegExp(name)}=${escapeRegExp(value)}(?:\\|[^\\]]*)?\\]`);
}

// ---------------------------------------------------------------------------
// The component and its store
// ---------------------------------------------------------------------------

interface WhatsNewStore {
    readonly shouldShow: boolean;
    readonly chapters: readonly ChangelogChapter[];
    dismiss(): unknown;
}

const MODAL_MODULES = import.meta.glob<{default: Component<Record<string, never>>}>('./WhatsNewModal.svelte');
const STORE_MODULES = import.meta.glob<{whatsNew?: unknown}>('./whatsNewStore.svelte.ts');

let loaded: {modal: Component<Record<string, never>>; store: WhatsNewStore} | {error: unknown} | undefined;

beforeAll(async () => {
    await setupI18n();
    try {
        const loadModal = MODAL_MODULES['./WhatsNewModal.svelte'];
        if (!loadModal) throw new Error("src/lib/features/changelog/WhatsNewModal.svelte does not exist yet: «What's new since your last version» has no modal (C-54)");
        const modal = (await loadModal()).default;
        const loadStore = STORE_MODULES['./whatsNewStore.svelte.ts'];
        if (!loadStore) throw new Error('src/lib/features/changelog/whatsNewStore.svelte.ts does not exist yet: the modal has no store to read (C-54)');
        const {whatsNew} = await loadStore();
        if (typeof whatsNew !== 'object' || whatsNew === null || typeof (whatsNew as {dismiss?: unknown}).dismiss !== 'function') throw new Error('whatsNewStore.svelte.ts does not export `whatsNew` with dismiss()');
        loaded = {modal, store: whatsNew as WhatsNewStore};
    } catch (error) {
        loaded = {error};
    }
}, 60_000);

function subject(): {modal: Component<Record<string, never>>; store: WhatsNewStore} {
    if (loaded === undefined) throw new Error('WhatsNewModal was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded;
}

// ---------------------------------------------------------------------------
// Accounts, fixtures and helpers
// ---------------------------------------------------------------------------

/** What the backend sends in the user payload: `null` when there is nothing to show. */
interface WhatsNewInfo {
    since: string | null;
    release: string;
}

/** The user of `/auth/me`, with this lot's field. */
type Account = AuthUser & {whats_new: WhatsNewInfo | null};

/** A range the fixture has chapters for: 1.2.1 and 1.2.0. */
const RANGE: WhatsNewInfo = {since: '1.1.0', release: '1.2.1'};

let nextId = 5400;

/** Signs a new account in through `checkAuth()` against a programmed `GET /auth/me`: a new client session. */
async function signIn(whatsNew: WhatsNewInfo | null): Promise<Account> {
    const id = nextId++;
    const user: Account = {id, username: `whats-new-${id}`, email: `whats-new-${id}@example.com`, is_active: true, is_superuser: false, created_at: '2026-10-17T00:00:00Z', whats_new: whatsNew};
    api.me.mockResolvedValueOnce({user});
    expect(await auth.checkAuth(), 'premise: the auth store signed the account in').toBe('authenticated');
    expect(getAuthState().user, 'premise: the account of this case is the one signed in, its payload untouched').toEqual(user);
    return user;
}

/** Signs an account in whose payload has something to show, then mounts the modal: it opens by itself. */
async function openModal(whatsNew: WhatsNewInfo) {
    const {modal, store} = subject();
    await signIn(whatsNew);
    expect(store.shouldShow, 'premise: the store has something to show for this account').toBe(true);
    const dismiss = vi.spyOn(store, 'dismiss');
    render(modal);
    const dialog = await screen.findByTestId('whats-new-modal');
    return {dialog, dismiss};
}

function blocks(dialog: HTMLElement): HTMLElement[] {
    return within(dialog).queryAllByTestId('whats-new-chapter');
}

function blockVersions(dialog: HTMLElement): Array<string | null> {
    return blocks(dialog).map((block) => block.getAttribute('data-version'));
}

/** The one block of `version`. */
function block(dialog: HTMLElement, version: string): HTMLElement {
    const found = blocks(dialog).filter((candidate) => candidate.getAttribute('data-version') === version);
    expect(found, `one block for v${version}`).toHaveLength(1);
    return found[0];
}

/** Switch the UI language; ends once the store holds it (svelte-i18n loads a new dictionary first). */
async function setUiLocale(next: string): Promise<void> {
    await locale.set(next);
    await waitFor(() => expect(get(locale)).toBe(next));
}

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((resolvePromise, rejectPromise) => {
        resolve = resolvePromise;
        reject = rejectPromise;
    });
    return {promise, resolve, reject};
}

/** v1.2.1 in Italian: "fenicottero" is a word only the translation has, and the English "kiwi" is gone. */
const ITALIAN_121: ShownChapter = {
    version: '1.2.1',
    date: '2026-10-15',
    lang: 'it',
    body: 'La versione **fenicottero** rende stabili le importazioni.\n\n### Corretto\n- la procedura fenicottero ricorda il punto\n',
    sections: [
        {title: null, body: 'La versione **fenicottero** rende stabili le importazioni.\n', subsections: []},
        {title: 'Corretto', body: '- la procedura fenicottero ricorda il punto\n', subsections: []},
    ],
};

/** The Italian UI's chapters: 1.2.1 translated, every other one still English. */
function shownInItalian(): ShownChapter[] {
    return localizedFake.english().map((chapter) => (chapter.version === '1.2.1' ? ITALIAN_121 : chapter));
}

/** Markup a changelog body must never run: an inline handler and a script. The image itself is harmless. */
const HOSTILE_MARKUP = '<img src="x" onerror="alert(1)">\n\n<script>void 0</script>\n';

/** v1.2.1 carrying the hostile markup in its intro and in a section. */
const HOSTILE_121: ChangelogChapter = {
    version: '1.2.1',
    date: '2026-10-15',
    body: `Probe intro text.\n\n${HOSTILE_MARKUP}\n### Fixed\nProbe section text.\n\n${HOSTILE_MARKUP}`,
    sections: [
        {title: null, body: `Probe intro text.\n\n${HOSTILE_MARKUP}`, subsections: []},
        {title: 'Fixed', body: `Probe section text.\n\n${HOSTILE_MARKUP}`, subsections: []},
    ],
};

beforeEach(() => {
    changelogFixture.restore();
    localizedFake.reset();
    api.me.mockReset();
    api.logout.mockReset().mockResolvedValue(undefined);
    api.seen.mockReset().mockResolvedValue(undefined);
    translateMock.mockReset();
    translateMock.mockImplementation(token);
    auth.reset();
});

afterEach(async () => {
    vi.restoreAllMocks();
    auth.reset();
    await setUiLocale('en');
});

// ---------------------------------------------------------------------------
// The cases
// ---------------------------------------------------------------------------

describe('WhatsNewModal — what it shows', () => {
    it('WNM-01: since set — the dialog, its title, the intro of an update, and one block per chapter released since, newest first', async () => {
        const {dialog} = await openModal({since: '1.1.0', release: '1.2.1'});

        expect(within(dialog).getByRole('heading', {name: keyed('changelog.whatsNew.title')})).toBeInTheDocument();
        expect(dialog).toHaveTextContent(keyed('changelog.whatsNew.intro'));
        expect(dialog, 'not the intro of an account from before the feature').not.toHaveTextContent(keyed('changelog.whatsNew.introRelease'));
        expect(blockVersions(dialog), 'since excluded, release included, never Unreleased').toEqual(['1.2.1', '1.2.0']);
    });

    it('WNM-02: since null (an account from before the feature) — the release chapter alone, and the intro that names the release', async () => {
        const {dialog} = await openModal({since: null, release: '1.2.1'});

        expect(within(dialog).getByRole('heading', {name: keyed('changelog.whatsNew.title')})).toBeInTheDocument();
        expect(dialog).toHaveTextContent(keyedWith('changelog.whatsNew.introRelease', 'version', '1.2.1'));
        expect(dialog, 'not the intro of an update').not.toHaveTextContent(keyed('changelog.whatsNew.intro'));
        expect(blockVersions(dialog)).toEqual(['1.2.1']);
    });

    it('WNM-03: the full changelog link — CHANGELOG_REMOTE_URL, rel noopener noreferrer — and the close button, each named by its key', async () => {
        const {dialog} = await openModal(RANGE);

        const link = within(dialog).getByTestId('whats-new-full-changelog');
        expect(link.tagName, 'a link').toBe('A');
        expect(link).toHaveAttribute('href', CHANGELOG_REMOTE_URL);
        expect((link.getAttribute('rel') ?? '').split(/\s+/), 'no window.opener, no referrer').toEqual(expect.arrayContaining(['noopener', 'noreferrer']));
        expect(link).toHaveAccessibleName(keyed('changelog.whatsNew.fullChangelog'));

        const close = within(dialog).getByTestId('whats-new-close');
        expect(close.tagName, 'a button').toBe('BUTTON');
        expect(close).toHaveAccessibleName(keyed('changelog.whatsNew.close'));
    });

    it('WNM-04: bodies are Markdown, rendered through sanitizeHtml — text, emphasis, lists and image stay; the handler and the script go', async () => {
        // Swapped in place: this array is both `changelogChapters` and the source of the fake's English list.
        changelogFixture.chapters[1] = HOSTILE_121;
        const {dialog} = await openModal(RANGE);

        const hostile = block(dialog, '1.2.1');
        expect(hostile).toHaveTextContent('Probe intro text.');
        expect(hostile).toHaveTextContent('Probe section text.');
        expect(hostile.querySelector('img'), 'the image itself is harmless, and kept: the body is HTML, not escaped text').not.toBeNull();
        expect(dialog.querySelector('[onerror]'), 'no event-handler attribute survives').toBeNull();
        expect(dialog.querySelector('script'), 'no script element survives').toBeNull();

        const plain = block(dialog, '1.2.0');
        expect(plain.querySelector('strong'), 'Markdown emphasis, rendered').toHaveTextContent('walrus');
        expect(plain.querySelector('li'), 'a Markdown list item, rendered').toHaveTextContent('walrus reports');
    });

    it('WNM-05: closed while the store has nothing to show; the same mount opens as soon as it has', async () => {
        const {modal, store} = subject();
        await signIn(null);
        expect(store.shouldShow, 'premise: whats_new null, nothing to show').toBe(false);

        render(modal);
        await tick();
        expect(screen.queryByTestId('whats-new-modal')).toBeNull();

        // Positive control: another account, with something new — the same mount opens, so the absence above was the store's.
        auth.reset();
        await signIn(RANGE);
        expect(store.shouldShow, 'premise: the next account has something to show').toBe(true);
        const dialog = await screen.findByTestId('whats-new-modal');
        expect(blockVersions(dialog)).toEqual(['1.2.1', '1.2.0']);
    });
});

describe('WhatsNewModal — closing it', () => {
    const CLOSES: Array<[string, (dialog: HTMLElement) => Promise<unknown>]> = [
        ['the close button', (dialog) => fireEvent.click(within(dialog).getByTestId('whats-new-close'))],
        ['Escape', (dialog) => fireEvent.keyDown(dialog, {key: 'Escape'})],
        [
            'a click on the backdrop',
            async (dialog) => {
                await fireEvent.mouseDown(dialog);
                await fireEvent.click(dialog);
            },
        ],
    ];

    it.each(CLOSES)('WNM-06: %s calls whatsNew.dismiss() once, and the dialog goes at once — before the server answers', async (_label, close) => {
        const answer = deferred<unknown>();
        api.seen.mockImplementation(() => answer.promise);
        const {dialog, dismiss} = await openModal(RANGE);
        expect(dismiss, 'premise: nothing dismissed it yet').not.toHaveBeenCalled();

        await close(dialog);

        expect(dismiss, 'one close, one dismiss').toHaveBeenCalledTimes(1);
        await waitFor(() => expect(screen.queryByTestId('whats-new-modal')).toBeNull());
        await waitFor(() => expect(api.seen, 'the POST is on its way, and the dialog did not wait for its answer').toHaveBeenCalledTimes(1));

        answer.resolve(undefined);
        await answer.promise;
        await tick();
        expect(dismiss, 'nothing dismissed it a second time').toHaveBeenCalledTimes(1);
        expect(api.seen, 'one POST').toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('whats-new-modal'), 'still closed once the server answered').toBeNull();
    });
});

describe('WhatsNewModal — the chapters in the interface language', () => {
    it('WNM-07: English UI — every block in English, with no pill', async () => {
        const {dialog} = await openModal(RANGE);

        expect(blockVersions(dialog)).toEqual(['1.2.1', '1.2.0']);
        expect(block(dialog, '1.2.1')).toHaveTextContent('kiwi');
        expect(block(dialog, '1.2.0')).toHaveTextContent('walrus');
        expect(within(dialog).queryAllByTestId('whats-new-not-translated'), 'an English chapter in an English UI carries no pill').toHaveLength(0);
    });

    it('WNM-08: Italian UI, translation loaded — the translated chapter in Italian with no pill, the untranslated one in English with the pill', async () => {
        await setUiLocale('it');
        localizedFake.cached.set('it', shownInItalian());

        const {dialog} = await openModal(RANGE);

        expect(blockVersions(dialog)).toEqual(['1.2.1', '1.2.0']);
        const translated = block(dialog, '1.2.1');
        expect(translated).toHaveTextContent('fenicottero');
        expect(translated, 'the translation replaces the English text').not.toHaveTextContent('kiwi');
        expect(within(translated).queryByTestId('whats-new-not-translated'), 'a translated chapter carries no pill').toBeNull();
        const english = block(dialog, '1.2.0');
        expect(english).toHaveTextContent('walrus');
        expect(within(english).getByTestId('whats-new-not-translated')).toHaveTextContent(keyed('changelog.notTranslated'));
        expect(within(dialog).getAllByTestId('whats-new-not-translated'), "one pill: the untranslated chapter's").toHaveLength(1);
    });

    it('WNM-09: Italian UI, translation still loading — English at once, then the translation', async () => {
        await setUiLocale('it');
        const file = deferred<ShownChapter[]>();
        localizedFake.files.set('it', () => file.promise);

        const {dialog} = await openModal(RANGE);

        await waitFor(() => expect(blockVersions(dialog), 'the blocks, while the Italian chapters load').toEqual(['1.2.1', '1.2.0']));
        expect(block(dialog, '1.2.1'), 'in English meanwhile').toHaveTextContent('kiwi');
        await waitFor(() => expect(localizedFake.load).toHaveBeenCalled());
        expect(
            localizedFake.load.mock.calls.map(([value]) => localizedFake.baseLanguage(value)),
            'the translation of the UI language is asked for',
        ).toContain('it');

        file.resolve(shownInItalian());

        await waitFor(() => expect(block(dialog, '1.2.1')).toHaveTextContent('fenicottero'));
        expect(within(block(dialog, '1.2.1')).queryByTestId('whats-new-not-translated')).toBeNull();
        expect(within(block(dialog, '1.2.0')).getByTestId('whats-new-not-translated')).toHaveTextContent(keyed('changelog.notTranslated'));
    });

    it('WNM-10: Italian UI, translation fails to load — every block in English, each with the pill', async () => {
        await setUiLocale('it');
        localizedFake.files.set('it', () => Promise.reject(new Error('translation chunk failed (WhatsNewModal.test)')));

        const {dialog} = await openModal(RANGE);

        await waitFor(() => expect(localizedFake.load).toHaveBeenCalled());
        await waitFor(() => expect(within(dialog).queryAllByTestId('whats-new-not-translated')).toHaveLength(2));
        expect(block(dialog, '1.2.1')).toHaveTextContent('kiwi');
        expect(block(dialog, '1.2.0')).toHaveTextContent('walrus');
        for (const version of ['1.2.1', '1.2.0']) {
            expect(within(block(dialog, version)).getByTestId('whats-new-not-translated'), `v${version}`).toHaveTextContent(keyed('changelog.notTranslated'));
        }
    });
});
