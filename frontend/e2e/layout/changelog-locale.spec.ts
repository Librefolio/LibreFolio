/**
 * The changelog modal speaks the UI language, chapter by chapter (lot CL, the localized CHANGELOG).
 *
 * Translations ship beside the English file as CHANGELOG.<lang>.md. The modal shows a chapter in
 * the UI language when the translation carries it, and in English otherwise, and says which is
 * which: every chapter is a `<section data-version lang>`, and an English chapter inside a
 * translated UI carries the `changelog-not-translated-{ci}` pill in its toggle, the pill itself
 * marked with the UI language. In the English UI nothing is marked.
 *
 * Content-agnostic on purpose: the translations are written by another workstream and grow release
 * by release, so the language each chapter must have is read at run time from the repository's own
 * CHANGELOG.it.md (absent → nothing translated → every chapter English). No version, no count and
 * no prose is written down here. The parse mirrors the module's — src/lib/features/changelog/changelog.ts,
 * which this spec cannot import, since it reads the files through vite's `?raw` — so per version
 * the first chapter the parser keeps counts, and it is translated when it has a content line (a
 * non-blank line that is not a `###`…`######` heading), because the merge keeps a translated chapter
 * only when it has a section.
 *
 * The files are bundled when the frontend is built: a CHANGELOG.<lang>.md changed after the last
 * build is not what the running app shows until the build is redone.
 *
 * Nothing is written server-side: the header's language selector keeps the choice in this browser
 * context (localStorage), never in the user's settings, and TEST_USER only reads — grandfathered
 * completed on every onboarding flow, read back so no guide overlay competes for the clicks.
 * Desktop only: the subject does not depend on the viewport, and on mobile the version entry point
 * sits in the off-canvas sidebar.
 *
 * One window for every entry point (lot A-CL1, written red-first). The version under the sidebar
 * (`sidebar-version`) and the version under the logo in Settings › About (`about-version`) open one
 * and the same window, the Sidebar's at the app shell, and a translation that finishes loading while
 * that window is closed shows when it opens again. E1, in the Italian UI, holds the Italian
 * translation chunk at the network (the build names chunks by content hash, so it is recognised by
 * its body, through a marker read at run time from CHANGELOG.it.md), opens the window from About
 * («loading»), closes it, releases the chunk, waits until the page has evaluated it and reopens the
 * window from About: the chapters must show, in the languages CHANGELOG.it.md says. E2 marks the
 * element holding the window About opens, closes it and opens the sidebar's: the window must sit in
 * the same element, never inside the About tab. Today About mounts a window of its own inside its
 * tab, and the load a closed window dropped leaves «loading» on screen for good. Preconditions are
 * read back, not assumed: no onboarding due, and no «What's new» pending — its window would cover
 * the page and, in the Italian UI, load the translation before the hold.
 */
import {existsSync, readdirSync, readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {expect, test, type Page} from '../fixtures/playwright';
import {login, setLanguage} from '../fixtures/auth-helpers';
import {readOnboardingProgress} from '../fixtures/onboarding-accounts';
import {TEST_USER} from '../fixtures/test-users';

/** The heading rules of src/lib/features/changelog/changelog.ts, copied: a chapter, a `###` section, a `####`–`######` subsection. */
const CHAPTER_HEADING = /^## \[([^\]]+)\](?:\s*-\s*(.+?))?\s*$/;
const SECTION_HEADING = /^###\s+(.+?)\s*$/;
const SUBSECTION_HEADING = /^#{4,6}\s+(.+?)\s*$/;

/** Opening the modal and rendering the bundled chapters, a translation chunk included. */
const MODAL_TIMEOUT_MS = 10_000;

/** Settings › About from a navigation: the app's auth check and bootstrap, the tab's first render, then its seven requests settled. A deadline. */
const ABOUT_MS = 20_000;

/** A window closing: its fade and scale outros (≈ 200 ms) on a busy lane. A deadline. */
const CLOSE_MS = 5_000;

/**
 * A test of the A-CL1 block: the sign-in (login() alone allows 30 s to arrive on a loaded lane), a language switch
 * (setLanguage, 15 s per wait), Settings › About settled (ABOUT_MS), then the window's own waits — E1's red spends the
 * last MODAL_TIMEOUT_MS in full. A ceiling, never a delay.
 */
const ONE_WINDOW_TEST_MS = 90_000;

/** Every JS file of the build: named by content hash under /_app/immutable/, so a chunk is told by its body, not by its URL. */
const BUILD_CHUNKS = '**/_app/immutable/**/*.js';

/** The attribute E2 writes on the element holding the window About opened: client DOM only, gone with the page. */
const HOST_MARK = 'data-e2e-changelog-host';

test.setTimeout(30_000);

/**
 * The versions CHANGELOG.<lang>.md translates, as the modal's merge sees them. A numbered chapter
 * with a blank body is dropped by the parser, so it cannot shadow a later chapter of its version.
 */
function translatedVersions(lang: string): Set<string> {
    const path = fileURLToPath(new URL(`../../../CHANGELOG.${lang}.md`, import.meta.url));
    if (!existsSync(path)) return new Set();

    const chapters: Array<{version: string; nonBlank: boolean; content: boolean}> = [];
    for (const line of readFileSync(path, 'utf8').split('\n')) {
        const heading = CHAPTER_HEADING.exec(line);
        if (heading) {
            chapters.push({version: heading[1], nonBlank: false, content: false});
            continue;
        }
        const chapter = chapters[chapters.length - 1];
        if (!chapter || line.trim().length === 0) continue; // the preamble, or a blank line
        chapter.nonBlank = true;
        if (!SECTION_HEADING.test(line) && !SUBSECTION_HEADING.test(line)) chapter.content = true;
    }

    const seen = new Set<string>();
    const translated = new Set<string>();
    for (const {version, nonBlank, content} of chapters) {
        if (!nonBlank && version.toLowerCase() !== 'unreleased') continue;
        if (seen.has(version)) continue; // a repeated version: the first chapter wins
        seen.add(version);
        if (content) translated.add(version);
    }
    return translated;
}

/** One displayed chapter, as the page shows it: its version and language, and its not-translated pill. */
interface ShownChapter {
    testId: string;
    version: string;
    lang: string | null;
    /** The pill inside the chapter's toggle: its `lang` and whether it is on screen. */
    pill: {lang: string | null; visible: boolean} | null;
    /** Every not-translated pill anywhere in the chapter: one at most, and only the one in the toggle. */
    pillsInChapter: number;
}

/** What a chapter must look like when its text is in `chapterLang` and the UI speaks `uiLang`. */
function expectedChapter(shown: ShownChapter, chapterLang: string, uiLang: string): ShownChapter {
    const marked = chapterLang !== uiLang;
    return {...shown, lang: chapterLang, pill: marked ? {lang: uiLang, visible: true} : null, pillsInChapter: marked ? 1 : 0};
}

/** Precondition, read back rather than inferred: no onboarding flow is due, so no guide or tour overlay competes for the clicks. */
async function expectNoOnboardingDue(page: Page): Promise<void> {
    const due = (await readOnboardingProgress(page)).filter((item) => item.status === 'pending' || item.version < item.current_version).map((item) => item.flow);
    expect(due, `${TEST_USER.username} must be grandfathered completed on every onboarding flow (populate_mock_data _grandfather_onboarding_for_test_users)`).toEqual([]);
}

/** Open the changelog from the sidebar's version and read every displayed chapter ({@link readOpenChangelog}). */
async function openChangelog(page: Page): Promise<ShownChapter[]> {
    await page.getByTestId('sidebar-version').click();
    return readOpenChangelog(page);
}

/**
 * Read every displayed chapter of the changelog window on screen, whichever entry point opened it.
 * The gate is the newest chapter carrying its version: the modal renders its chapters in one pass,
 * and only once the translation of the UI language (if any) has loaded, so from there the list is
 * complete.
 */
async function readOpenChangelog(page: Page): Promise<ShownChapter[]> {
    const modal = page.getByTestId('changelog-modal');
    await expect(modal).toBeVisible({timeout: MODAL_TIMEOUT_MS});
    await expect(modal.getByTestId('changelog-chapter-0'), 'The newest chapter must carry its version').toHaveAttribute('data-version', /\S/, {timeout: MODAL_TIMEOUT_MS});
    await expect(modal.getByTestId('changelog-loading')).toHaveCount(0);

    return modal.locator('section[data-version]').evaluateAll((sections) =>
        sections.map((section) => {
            const testId = section.getAttribute('data-testid') ?? '';
            const ci = testId.replace(/^changelog-chapter-/, '');
            const pill = section.querySelector(`[data-testid="changelog-chapter-toggle-${ci}"] [data-testid="changelog-not-translated-${ci}"]`);
            return {
                testId,
                version: section.getAttribute('data-version') ?? '',
                lang: section.getAttribute('lang'),
                pill: pill ? {lang: pill.getAttribute('lang'), visible: pill.getClientRects().length > 0} : null,
                pillsInChapter: section.querySelectorAll('[data-testid^="changelog-not-translated-"]').length,
            };
        }),
    );
}

test.describe('Changelog modal — the chapters in the UI language', () => {
    test.beforeEach(async ({page}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', 'Desktop only: the chapter languages do not depend on the viewport, and the mobile entry point is the off-canvas sidebar');
        await login(page, TEST_USER);
        await expectNoOnboardingDue(page);
    });

    test('Italian UI: a chapter CHANGELOG.it.md translates is Italian, every other one English with the Italian not-translated pill', async ({page}) => {
        const translated = translatedVersions('it');
        await setLanguage(page, 'it');

        const shown = await openChangelog(page);

        expect(shown.length, 'The modal must show the bundled chapters').toBeGreaterThan(0);
        expect(shown).toEqual(shown.map((chapter) => expectedChapter(chapter, translated.has(chapter.version) ? 'it' : 'en', 'it')));
    });

    test('English UI: every chapter is English and none carries the not-translated pill', async ({page}) => {
        await setLanguage(page, 'en');

        const shown = await openChangelog(page);

        expect(shown.length, 'The modal must show the bundled chapters').toBeGreaterThan(0);
        expect(shown).toEqual(shown.map((chapter) => expectedChapter(chapter, 'en', 'en')));
        await expect(page.getByTestId('changelog-modal').locator('[data-testid^="changelog-not-translated-"]')).toHaveCount(0);
    });
});

// ── One window for every entry point (A-CL1) ───────────────────────────────────────────────────────────────────────────

/**
 * Precondition, read back from the server: no «What's new» window is pending for TEST_USER. That window would cover
 * the page and, in the Italian UI, load the changelog translation itself, before the hold. The app shows it from
 * `user.whats_new` alone (whatsNewStore), so null — or absent — means nothing to show for as long as this page lives;
 * a look at the screen would only say «not yet». Every test lane answers null: dev.py server --test sets
 * LIBREFOLIO_DISABLE_WHATS_NEW.
 */
async function expectNoWhatsNewPending(page: Page): Promise<void> {
    const response = await page.request.get('/api/v1/auth/me');
    expect(response.ok(), `GET /api/v1/auth/me answers for ${TEST_USER.username} (HTTP ${response.status()})`).toBe(true);
    const {user} = (await response.json()) as {user?: {whats_new?: unknown}};
    expect(user, 'GET /api/v1/auth/me carries the signed-in user').toBeTruthy();
    expect(user?.whats_new ?? null, `${TEST_USER.username} has no «What's new» pending (LIBREFOLIO_DISABLE_WHATS_NEW=1 on test lanes): its window would cover the page and could load the translation first`).toBeNull();
}

/** Settings › About on view and settled: the tab publishes `data-busy="false"` once its seven requests are in. */
async function openAbout(page: Page): Promise<void> {
    await page.goto('/settings?tab=about');
    await expect(page.getByTestId('about-tab'), 'Settings › About settles: its seven requests are in').toHaveAttribute('data-busy', 'false', {timeout: ABOUT_MS});
}

/**
 * The marker that recognises the translation chunk of `CHANGELOG.<lang>.md` by its body, or null when the file is
 * absent or holds none. The chunk is the file as a JS string literal: newlines become `\n`, a quote or a backslash is
 * escaped, the bundler picks the quotes and a minifier renames the variable, while accented letters stay as they are.
 * A run of `[A-Za-z0-9 ,.;:()-]` crosses all of that verbatim, so the marker is the first such run of 40 characters or
 * more (the preamble's sentence, as the file is written today) that no other CHANGELOG*.md carries — neither the English
 * file inlined in the main bundle nor another translation's chunk.
 */
function chunkMarker(lang: string): string | null {
    const root = new URL('../../../', import.meta.url);
    const own = `CHANGELOG.${lang}.md`;
    const names = readdirSync(root).filter((name) => /^CHANGELOG(?:\..+)?\.md$/.test(name));
    if (!names.includes(own)) return null;
    const others = names.filter((name) => name !== own).map((name) => readFileSync(new URL(name, root), 'utf8'));
    const runs = readFileSync(new URL(own, root), 'utf8').match(/[A-Za-z0-9 ,.;:()-]{40,}/g) ?? [];
    return runs.map((run) => run.trim()).find((run) => run.length >= 40 && others.every((text) => !text.includes(run))) ?? null;
}

/** A build chunk held at the network until the test lets it through. */
interface HeldChunk {
    /** The URL of every request whose body carried the marker, in order: the proof the hold happened, and happened once. */
    readonly held: readonly string[];
    /** Let the held request through. Idempotent. */
    release(): void;
    /** Release, then remove the route: in `finally`, so a held request never outlives its test. */
    dispose(): Promise<void>;
}

/**
 * Hold at the network the build chunk whose body carries `marker`; every other chunk passes. Each request is read once
 * through `route.fetch()`, for its body, then continued untouched: the browser fetches it itself, so nothing is
 * re-served — the backend gzips JS from 1 KB up, and a decoded body served back under the original `content-encoding`
 * blanks the page (auth.spec.ts, `holdItalianCatalogue`). The held request waits for `release()`.
 *
 * Install it right before the action whose chunk is to be held, once the page is ready: from then on it reads every
 * chunk the page requests, and the held one must be the first carrying the marker.
 */
async function holdChunkCarrying(page: Page, marker: string): Promise<HeldChunk> {
    const held: string[] = [];
    let release = () => {};
    const released = new Promise<void>((resolve) => {
        release = resolve;
    });
    const handler: Parameters<Page['route']>[1] = async (route, request) => {
        try {
            const body = await (await route.fetch()).text();
            if (body.includes(marker)) {
                held.push(request.url());
                await released;
            }
            await route.continue();
        } catch (error) {
            // Nobody awaits a route callback (default-currency.spec.ts, `routeQuietly`): absorbed, not hidden — the
            // request is left unanswered and the test fails on its own barrier.
            console.warn(`[changelog-locale] left ${request.method()} ${request.url()} unanswered: its route callback failed with ${String(error)}`);
        }
    };
    await page.route(BUILD_CHUNKS, handler);
    return {
        held,
        release: () => release(),
        dispose: async () => {
            release();
            await page.unroute(BUILD_CHUNKS, handler);
        },
    };
}

/**
 * Return once the page has evaluated the module at `url` and the app's own import of it has run to its end: from then
 * on the changelog cache holds the translation.
 *
 * `import(url)` from the page joins the app's request through the module map — one entry per URL, so no second request
 * reaches the network (`held` stays at one) — and resolves once the module is fetched and evaluated. That alone sets no
 * order: the imports that waited on the fetch are answered one task each, in no fixed order, so the app's could still
 * be queued. The second `import(url)` is made once the entry is complete, and Chromium answers a client of a complete
 * entry with a task posted to the same task runner, first in first out: behind the app's. The app's continuation —
 * vite's preload wrapper, `m.default`, the parse and the merge into the cache (changelog.ts, `load`) — is promise
 * reactions only, microtasks run to the end before any later task. So when this returns the cache holds the
 * translation, and the next click, a later task, finds it there. Reopening any earlier could join a request still
 * pending and receive its answer the ordinary way: the defect under test would not show. A deadline on the
 * evaluation, never a delay.
 */
async function expectChunkEvaluated(page: Page, url: string): Promise<void> {
    await expect
        .poll(
            () =>
                page.evaluate(async (chunk) => {
                    await import(chunk);
                    await import(chunk);
                    return 'evaluated';
                }, url),
            {message: `the released chunk ${url} is fetched and evaluated by the page, the app's own import of it included`, timeout: MODAL_TIMEOUT_MS},
        )
        .toBe('evaluated');
}

test.describe('Changelog window — one window for every entry point (A-CL1)', () => {
    test.describe.configure({timeout: ONE_WINDOW_TEST_MS});

    test.beforeEach(async ({page}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', 'Desktop only: the window does not depend on the viewport, and the mobile entry point is the off-canvas sidebar');
        await login(page, TEST_USER);
        await expectNoOnboardingDue(page);
        await expectNoWhatsNewPending(page);
    });

    test('E1: Italian UI, About: the changelog closed while its translation loads opens with the translated chapters once it has loaded', async ({page}) => {
        const translated = translatedVersions('it');
        test.skip(translated.size === 0, 'CHANGELOG.it.md is absent or translates no chapter: there is no Italian translation chunk to hold');
        const marker = chunkMarker('it');
        if (marker === null) throw new Error('CHANGELOG.it.md holds no run of [A-Za-z0-9 ,.;:()-] of 40 characters or more that no other CHANGELOG*.md carries: chunkMarker() cannot recognise its chunk');

        await setLanguage(page, 'it');
        await openAbout(page);
        await expect(page.locator('html'), 'the Italian UI outlives the navigation: the language selector keeps it in localStorage').toHaveAttribute('lang', 'it');

        const modal = page.getByTestId('changelog-modal');
        const loading = modal.getByTestId('changelog-loading');
        const hold = await holdChunkCarrying(page, marker);
        try {
            // First opening, the translation requested and held: the window can only wait for it.
            await page.getByTestId('about-version').click();
            await expect(modal, 'about-version opens the changelog window').toBeVisible({timeout: MODAL_TIMEOUT_MS});
            await expect(loading, 'the window waits for the Italian translation: nothing loaded it before this first opening').toBeVisible();
            await expect.poll(() => hold.held.length, {message: 'this opening requests the Italian translation chunk, and it is held', timeout: MODAL_TIMEOUT_MS}).toBe(1);
            const [heldUrl] = hold.held;

            // Closed while the translation loads: the window drops that load's answer.
            await modal.press('Escape');
            await expect(modal, 'Escape closes the window').toHaveCount(0, {timeout: CLOSE_MS});

            // The translation lands while no window is open: released, evaluated, merged into the cache.
            hold.release();
            await expectChunkEvaluated(page, heldUrl);

            // Reopened from the same entry point: the chapters, in the languages CHANGELOG.it.md says.
            await page.getByTestId('about-version').click();
            await expect(modal, 'about-version opens the changelog window again').toBeVisible({timeout: MODAL_TIMEOUT_MS});
            await expect(loading, 'the reopened window shows the translation that loaded while it was closed, not «loading» (A-CL1)').toHaveCount(0, {timeout: MODAL_TIMEOUT_MS});
            const shown = await readOpenChangelog(page);

            expect(hold.held, 'one request for the Italian translation, the one held: the page evaluated that very module').toEqual([heldUrl]);
            expect(shown.length, 'The modal must show the bundled chapters').toBeGreaterThan(0);
            expect(shown).toEqual(shown.map((chapter) => expectedChapter(chapter, translated.has(chapter.version) ? 'it' : 'en', 'it')));
            expect(
                shown.filter((chapter) => chapter.lang === 'it').map((chapter) => chapter.version),
                `the window shows Italian chapters (CHANGELOG.it.md translates ${[...translated].join(', ')})`,
            ).not.toEqual([]);

            await modal.press('Escape');
            await expect(modal, 'Escape closes the window').toHaveCount(0, {timeout: CLOSE_MS});
        } finally {
            await hold.dispose();
        }
    });

    test("E2: the sidebar's version and About's open the same window", async ({page}) => {
        await setLanguage(page, 'en');
        await openAbout(page);

        const modal = page.getByTestId('changelog-modal');
        const markedHost = page.locator(`[${HOST_MARK}="about-version"]`);

        await page.getByTestId('about-version').click();
        await expect(modal, 'about-version opens the changelog window').toBeVisible({timeout: MODAL_TIMEOUT_MS});
        await expect(page.getByTestId('about-tab').getByTestId('changelog-modal'), "About opens the app's one window, not one of its own inside the About tab (A-CL1)").toHaveCount(0);

        // Identity across the two entry points: the element holding the window About opened, marked from here. The
        // window is created on every opening and gone on every close, the element holding it is not.
        await modal.evaluate((dialog, mark) => dialog.parentElement?.setAttribute(mark, 'about-version'), HOST_MARK);
        await expect(markedHost, 'the window About opened sits in an element, now marked').toHaveCount(1);
        await modal.press('Escape');
        await expect(modal, 'Escape closes the window').toHaveCount(0, {timeout: CLOSE_MS});
        await expect(markedHost, 'the marked element outlives the window it held: the next window can be placed against it').toHaveCount(1);

        await page.getByTestId('sidebar-version').click();
        await expect(modal, 'sidebar-version opens the changelog window').toBeVisible({timeout: MODAL_TIMEOUT_MS});
        await expect(page.locator(`[${HOST_MARK}="about-version"] > [data-testid="changelog-modal"]`), "sidebar-version opens the very window About's version opened: it sits in the same element (A-CL1)").toBeVisible();

        await modal.press('Escape');
        await expect(modal, 'Escape closes the window').toHaveCount(0, {timeout: CLOSE_MS});
    });
});
