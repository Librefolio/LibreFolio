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
 */
import {existsSync, readFileSync} from 'node:fs';
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

/**
 * Open the changelog from the sidebar's version and read every displayed chapter. The gate is the
 * newest chapter carrying its version: the modal renders its chapters in one pass, and only once
 * the translation of the UI language (if any) has loaded, so from there the list is complete.
 */
async function openChangelog(page: Page): Promise<ShownChapter[]> {
    await page.getByTestId('sidebar-version').click();
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
