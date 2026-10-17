/**
 * Gallery Screenshot Generator
 *
 * Generates consistent screenshots for mkdocs documentation.
 * NOT included in normal test runs - run separately with:
 *   ./dev.py mkdocs gallery
 *
 * Screenshots saved to: mkdocs_src/docs/gallery/{desktop|mobile}/{lang}/{theme}/...
 *
 * Prerequisites:
 *   - Run `./dev.py db populate --force` before generating gallery
 *   - This ensures brokers with icons exist for realistic screenshots
 */
import {type APIRequestContext, expect, type Locator, type Page, test} from './fixtures/playwright';
import {login, navigateTo, openMobileMenu, setLanguage} from './fixtures/auth-helpers';
import {validateRuns, waitForChart, waitForParseVerdict, waitForSettled} from './fixtures/app-events';
import {
    attachPageSnapshotOnFailure,
    badgeKinds,
    brimFilesListed,
    brimFilesOn,
    cleanupGalleryAccount,
    closeEditorWithoutSaving,
    closeSuccessToasts,
    combineSet,
    createGalleryBroker,
    currentStep,
    DANSKE,
    DANSKE_SAMPLES,
    editorAfterHandoff,
    expectGalleryOffline,
    expectFaviconImagesLoading,
    expectNoToast,
    expectOfflinePricesDrawn,
    expectUncovered,
    GAP_POINTS,
    type GalleryAccount,
    galleryOfflineGuard,
    GENERIC,
    guardGalleryOffline,
    hideGalleryTempData,
    injectTodosIntoParses,
    keepFaviconImagesLoading,
    keepOnlyCashRows,
    keepTempDataHiddenUnder,
    leaveGalleryPage,
    onboardGalleryAccount,
    openBrokerPanel,
    openWizardOnSelectFiles,
    parseSelection,
    previewSet,
    registerGalleryAccount,
    reportSetCard,
    roleRow,
    SAVINGS_ROWS,
    SAVINGS_TODOS,
    scrollToTop,
    tickWholeSet,
    unfoldCard,
    uploadFile,
    uploadSet,
    waitForStillness,
    walkToReview,
    writeSavingsStatement,
} from './fixtures/galleryReportSets';
import {continueToReview, type ParseResponse, parseSelectedFile, selectBrokerFile} from './fixtures/import-wizard';
import {canEdit, listBrokers, readTransactions, seededRow, type TxRow} from './fixtures/owned-pair';
import {appears, optionsClosed} from './fixtures/probe';
import {
    chooseLabYear,
    currentUserId,
    expectLabClean,
    fitViewportToBlock,
    forgetWhatIfTools,
    frameBlock,
    frameFromTop,
    guardReadOnly,
    idSet,
    imagesSettled,
    injectReplayLeftOut,
    injectStalePrice,
    LAB_ASSET_NAMES,
    labSelection,
    openLab,
    pairTestId,
    parkPointer,
    resolveLabIds,
    revealListSection,
    scrollBackToHeader,
    seedLabStorage,
} from './fixtures/galleryRiskLab';
import {assetIdNamed, canvasStill, chooseReplayPreset, CRISIS_PRESET_ID, DASHBOARD_BENCHMARK_NAME, forgetDashboardRiskMemory, framedParts, historicalReplayPreset, injectCrisisReplay, seedDashboardBenchmark, textStill} from './fixtures/galleryRiskDashboard';
import {
    chartsDrawn,
    chooseOnboardingCategory,
    CORE_TOUR_FX_STEP,
    expectGuideStep,
    expectLanguageAndTheme,
    expectOnboardingCategory,
    frameOnboardingCategory,
    frameWelcome,
    FX_PAGE_FILTERS_STEP,
    FX_PAGE_OVERVIEW_STEP,
    holdPanelAtFullStrength,
    seedLanguageAndTheme,
    setAccountLanguage,
    walkCoreTourToFx,
} from './fixtures/galleryOnboarding';
import {
    buildPacDraft,
    calculatePacPlan,
    closePacBrokerEditor,
    closePacExposures,
    fitScreenToPacProof,
    framePacAssets,
    framePacBrokerEditor,
    framePacExposures,
    framePacLiquidity,
    framePacPlan,
    framePacProof,
    framePacResult,
    framePacReview,
    framePacRouting,
    framePacTargets,
    leavePacTargetsIncomplete,
    openPacPlanner,
    resolvePacIds,
    restorePacScreen,
    settlePacShot,
} from './fixtures/galleryPac';
import {closeProviderCompare, fitScreenToCompareDialog, mockProviderCompare, openProviderCompare, restoreCompareScreen, settleProviderCompareShot} from './fixtures/galleryProviderCompare';
import {expectGalleryEmailStatus, serveGalleryEmailStatus} from './fixtures/galleryEmail';
import {expectGalleryBackupReady, serveGalleryBackupJob} from './fixtures/galleryBackup';
import {extendScreenToBlock, fitScreenToDialog, PAGE_BLOCK, restoreTallScreen} from './fixtures/galleryTallShots';
import {boxStill, bringIntoViewFromTop, captureShot, COLUMN_FILTER_GAP, DROPDOWN_GAP, expectDropdownAt, frameTarget, logApiOnFailure, scrollStill, settledToOpen, settleShot, type ShotOptions, trackApiRequests} from './fixtures/galleryShot';
import {brimFileId, chooseTheme, closePreview, FILES_SAMPLES, filesTableReady, fontsLoaded, gridPreviewReady, imagePreviewReady, imagesInViewLoaded, languageMenuClosed, markdownPreviewReady, openPreview, pdfPreviewReady, staticFileId, textPreviewReady} from './fixtures/galleryFiles';
import {expectDrawnUnder, setBrowserLocale, stampDocumentLocale} from './fixtures/galleryLocale';
import {completeWelcome, prepareOnboardingAccount} from './fixtures/onboarding-accounts';
import {openSettingsTab} from './fixtures/settings-tabs';
import {type Language, SUPPORTED_LANGUAGES, TEST_ADMIN, TEST_EMPTY, TEST_USER} from './fixtures/test-users';
import {goToFxDetailPage, goToFxPage, openAddPairModal} from './fx/fx-helpers';
import {goToAssetsPage} from './assets/assets-helpers';
import {schemas} from '../src/lib/api/generated';
import * as path from 'path';
import * as fs from 'fs';
import {fileURLToPath} from 'url';

// ES module compatibility for __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GALLERY_ROOT = path.join(__dirname, '../../mkdocs_src/docs/gallery');
const THEMES = ['light', 'dark'] as const;
type Theme = (typeof THEMES)[number];

async function clickRowAction(page: Page, scope: Page | Locator, actionId: string, index = 0): Promise<void> {
    const actionsButton = scope.getByTestId(/^row-actions-/).nth(index);
    await expect(actionsButton).toBeVisible({timeout: 5_000});
    await actionsButton.scrollIntoViewIfNeeded();
    await actionsButton.click();
    await page.getByTestId(`context-menu-action-${actionId}`).click();
}

/**
 * The indicator menu at one instant, read in one pass through the combobox's own contract — the trigger's `aria-expanded` and
 * `aria-activedescendant`, the rows' test ids and ids — never through a position or a label, so that its parts agree.
 */
interface IndicatorTreeState {
    /** The trigger says the menu is open. */
    open: boolean;
    /** The open menu's rows by test id, in screen order: the family rows, and the options of the families that are open. */
    rows: string[];
    /** The row the trigger names in `aria-activedescendant` — the one Enter acts on — by test id; '' when it names none. */
    active: string;
    /** What the pointer is over: the nearest test id, else the tag, else `nothing`. */
    pointer: string;
}

/** How many of the walk's last keys a failure quotes: the ones where it went wrong. */
const TREE_KEYS_QUOTED = 8;

/** Read the indicator menu of `picker` (`signals-indicator-select`): TreeSelect renders the open menu inside its own root. */
async function readIndicatorTree(picker: Locator): Promise<IndicatorTreeState> {
    return picker.evaluate((root): IndicatorTreeState => {
        const trigger = root.querySelector('[data-testid="signals-indicator-select-button"]');
        const rows = Array.from(root.querySelectorAll('[data-testid^="signal-tree-group-"], [data-testid^="signal-tree-option-"]'));
        const testIdOf = (element: Element): string => element.getAttribute('data-testid') ?? '';
        const activeId = trigger?.getAttribute('aria-activedescendant') ?? '';
        const activeRow = rows.find((row) => row.id === activeId);
        const hovers = document.querySelectorAll(':hover');
        const under = hovers.length > 0 ? hovers[hovers.length - 1] : null;
        return {
            open: trigger?.getAttribute('aria-expanded') === 'true',
            rows: rows.map(testIdOf),
            // An id that names no row is quoted as it stands, so that a failure shows it.
            active: activeId === '' ? '' : activeRow ? testIdOf(activeRow) : `#${activeId}`,
            pointer: under === null ? 'nothing' : (under.closest('[data-testid]')?.getAttribute('data-testid') ?? under.tagName.toLowerCase()),
        };
    });
}

/** A state as a failure quotes it: open or closed, the highlighted row and the wanted one with their place among the rows, the pointer, the rows. */
function describeIndicatorTree(state: IndicatorTreeState, target: string): string {
    if (!state.open) return `closed · pointer on ${state.pointer}`;
    const place = (row: string): string => {
        const index = state.rows.indexOf(row);
        return index < 0 ? `${row || 'none'}, not a row` : `${row} (${index + 1}/${state.rows.length})`;
    };
    return `open · highlight on ${place(state.active)} · wanted ${place(target)} · pointer on ${state.pointer}\n  rows: ${state.rows.join(' · ')}`;
}

/**
 * Walk the open indicator menu's highlight onto the row `target` (a test id): one key at a time from the search box — ↓ or ↑,
 * whichever brings it nearer from wherever it stands — reading the menu again after each key. The keys walk the rows in
 * screen order, family rows included (TreeSelect.test.ts pins it). From any row the target is fewer keys away than the menu
 * has rows, so the walk stops after their count and two more, and fails with the last state read and the last keys pressed.
 */
async function walkIndicatorTreeTo(picker: Locator, search: Locator, target: string, shot: string): Promise<void> {
    let state = await readIndicatorTree(picker);
    const bound = state.rows.length + 2;
    const keys: string[] = [];
    while (state.active !== target) {
        const to = state.rows.indexOf(target);
        if (!state.open || to < 0 || keys.length >= bound) {
            const why = !state.open ? 'the menu closed' : to < 0 ? 'the wanted row is not in the menu' : `${keys.length} keys did not get there`;
            const quoted = keys.length > TREE_KEYS_QUOTED ? [`… ${keys.length - TREE_KEYS_QUOTED} earlier`, ...keys.slice(-TREE_KEYS_QUOTED)] : keys;
            throw new Error(`${shot}: the indicator menu's highlight never reached ${target}: ${why}\n  last state: ${describeIndicatorTree(state, target)}\n  keys, oldest first: ${quoted.join(' · ') || 'none'}`);
        }
        const key = state.rows.indexOf(state.active) > to ? 'ArrowUp' : 'ArrowDown';
        await search.press(key);
        state = await readIndicatorTree(picker);
        keys.push(`${key === 'ArrowUp' ? '↑' : '↓'} ${state.active || 'none'}`);
    }
}

/**
 * Choose `optionValue` in the signals panel's indicator picker for the shot `shot` (`viewport/lang/theme/category/name`), and
 * end on the indicator added: the menu closed, and a card of that type in the panel. The picker is a TreeSelect of families
 * (`groupKey`) whose options are rendered only while their family is open; the first family opens by itself.
 *
 * It used to click the trigger, the family and the option, and check nothing after. In the L candidate run of 15/10 (6
 * workers), `mobile/it/light/assets/detail-signals-macd` was shot with the menu open and no MACD, 1 variant of 16, the test
 * green: its line (🔎) had the focus on the MACD row and a page 342 px shorter. A mousedown had reached MACD, no click had
 * chosen it, and the highlight stood on CCI, the row above. TreeSelect ends its opening on later tasks — one highlights the
 * first row and focuses the search box, and has the next scroll the highlighted row into view — and a loaded browser runs
 * input before timers: landed between the mousedown and the mouseup, they moved the list, the mouseup fell on CCI, and a
 * press and a release on two rows click neither. The likeliest reading, not an observed one (plan 56, G-9).
 *
 * So no pointer goes near the menu, and the choice is checked. The pointer is parked first, where the menu never reaches — a
 * row takes the highlight on `mouseenter` (galleryRiskDashboard.ts, `chooseReplayPreset`, H1) — and the page is settled for
 * the picker ({@link settledToOpen}). ↓ on the trigger opens the menu, and the search box holding the focus says the opening
 * has run. Then the keyboard, through the combobox's contract: ↓ and ↑ from the search box walk the highlight to the family's
 * row, → opens the family when it is closed, the walk goes on to the option ({@link walkIndicatorTreeTo}), and Enter chooses
 * the row `aria-activedescendant` names, wherever the list stands. A card's `data-signal-type` is the option's value: both
 * are the catalogue's signal type (ChartSignalsSection, `addSignal`).
 */
async function selectIndicatorFromTree(page: Page, groupKey: string, optionValue: string, shot: string): Promise<void> {
    const panel = page.getByTestId('asset-detail-signals-panel');
    const picker = panel.getByTestId('signals-indicator-select');
    const trigger = picker.getByTestId('signals-indicator-select-button');
    // Assert-loud on purpose: the picker appears only once the backend signal catalogue has loaded, so a missing one is a
    // real failure, not a skip.
    await expect(trigger).toBeVisible({timeout: 15_000});
    await expect(trigger, `${shot}: the indicator menu is open before the choice`).toHaveAttribute('aria-expanded', 'false');
    await parkPointer(page);
    await trigger.scrollIntoViewIfNeeded();
    await settledToOpen(page, picker, shot, 'the indicator picker');

    await trigger.press('ArrowDown');
    await expect(trigger, `${shot}: ↓ did not open the indicator menu`).toHaveAttribute('aria-expanded', 'true');
    // The search box is the open trigger's one input (TreeSelect gives it no test id). Its focus is the opening's last step,
    // after the first row's highlight: from here on, with the pointer parked, only the keys below move the highlight.
    const search = trigger.locator('input');
    await expect(search, `${shot}: the indicator menu has not finished opening`).toBeFocused();
    await expect(trigger, `${shot}: the open indicator menu highlights no row`).toHaveAttribute('aria-activedescendant', /.+/);

    // The family's options are rendered only while it is open: opened here only when it is closed.
    const familyRow = `signal-tree-group-${groupKey}`;
    const family = picker.getByTestId(familyRow);
    await expect(family, `${shot}: the indicator menu has no ${groupKey} family`).toBeVisible();
    if ((await family.getAttribute('aria-expanded')) !== 'true') {
        await walkIndicatorTreeTo(picker, search, familyRow, shot);
        await search.press('ArrowRight');
    }
    await expect(family, `${shot}: the ${groupKey} family did not open`).toHaveAttribute('aria-expanded', 'true');

    const optionRow = `signal-tree-option-${optionValue}`;
    const option = picker.getByTestId(optionRow);
    await expect(option, `${shot}: the ${groupKey} family holds no ${optionValue}`).toBeVisible();
    const optionId = await option.getAttribute('id');
    if (!optionId) throw new Error(`${shot}: the ${optionValue} row has no id for aria-activedescendant to name`);
    await walkIndicatorTreeTo(picker, search, optionRow, shot);
    await expect(search, `${shot}: Enter would act on another row than ${optionValue}`).toHaveAttribute('aria-activedescendant', optionId);
    await search.press('Enter');

    // The choice, proved: the menu closed, and the indicator added — its card is in the panel.
    await expect(trigger, `${shot}: the indicator menu stayed open after Enter on ${optionValue}`).toHaveAttribute('aria-expanded', 'false');
    await expect(panel.locator(`[data-testid^="signal-card-"][data-signal-type="${optionValue}"]`), `${shot}: no ${optionValue} card in the signals panel, the indicator was not added`).not.toHaveCount(0);
}

/**
 * Wait until every configured signal card has finished its backend computation. A card first: with none in the panel there is
 * no `signal-loading` either, and the wait passed on an empty panel — the MACD shot of 15/10 went out without its indicator
 * that way (plan 56, G-9). A new card comes with its spinner: adding a signal sets the panel loading in the same update
 * (assets/[id]/+page.svelte, `handleSignalsChange` → `loadChartData`).
 */
async function waitForSignalCardsSettled(page: Page, timeout = 30_000): Promise<void> {
    const panel = page.getByTestId('asset-detail-signals-panel');
    await expect(panel.locator('[data-testid^="signal-card-"]'), 'the signals panel holds no signal card: no computation to wait for').not.toHaveCount(0);
    await expect(panel.getByTestId('signal-loading')).toHaveCount(0, {timeout});
}

/**
 * Forget persisted chart settings (signal configs live in user-scoped localStorage).
 * Call at the START of a combo, before navigation: the next full page load re-hydrates
 * an empty store, so each lang/theme iteration starts with no signals configured and
 * cards never accumulate across combos.
 */
async function resetChartSettings(page: Page): Promise<void> {
    await page.evaluate(() => {
        for (const key of Object.keys(localStorage)) {
            if (key.endsWith('_chartSettingsStore')) localStorage.removeItem(key);
        }
    });
}

/**
 * Nothing is still moving in `scope`: no Web Animation is running on it or inside it.
 *
 * A modal opens with Svelte's `transition:` (fade + scale), which runs through the Web Animations
 * API — the CSS of freezeAnimations() cannot pause it — so a modal can be visible and still be
 * half-faded. This reads what the browser is animating instead of betting on a duration. The CSS
 * animations freezeAnimations() pauses are not running, so they never hold it up.
 */
async function waitForMotionSettled(scope: Locator, what: string): Promise<void> {
    await expect.poll(() => scope.evaluate((root) => root.getAnimations({subtree: true}).filter((animation) => animation.playState === 'running').length), {message: `${what} is still animating`, timeout: 5_000}).toBe(0);
}

function ensureDir(dir: string) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, {recursive: true});
    }
}

function getGalleryPath(viewport: 'desktop' | 'mobile', lang: Language, theme: Theme, category: string): string {
    return path.join(GALLERY_ROOT, viewport, lang, theme, category);
}

/**
 * Pause every CSS animation and turn CSS transitions off, for the shots of the page as it stands (a new document drops the
 * style tag: call it again after a load). Only paused: each animation keeps its designed delay — the login background's
 * lines start 0, 4 and 8 s apart — and the phase it stopped at is not the shot's. Right before the picture the shot's settle
 * (galleryShot.ts) pins every looping animation at the same moment of its own run, delay included (`pinLoopingAnimations`,
 * `GALLERY_ANIMATION_TIME_MS`), and finishes every animation that ends, which then shows its end state.
 */
async function freezeAnimations(page: Page) {
    await page.addStyleTag({
        content: `
            *, *::before, *::after {
                animation-play-state: paused !important;
                transition-duration: 0s !important;
            }
        `,
    });
}

/**
 * Set the application theme (light/dark)
 */
async function setTheme(page: Page, theme: Theme) {
    const currentTheme = await page.evaluate(() => {
        return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    });

    if (currentTheme !== theme) {
        await page.getByTestId('theme-toggle').click();
        await page.waitForTimeout(100); // Let theme transition complete
    }
}

/**
 * Wait until all pending network requests to the backend API have settled.
 * Uses networkidle + a small buffer to handle late-arriving responses.
 * Beware: in this single-page app `networkidle` is reached once per document, so after the first load this is a 200 ms
 * pause. A shot does not rely on it: screenshot() waits for the page's /api/ requests itself (galleryShot.ts, `apiQuiet`).
 */
async function waitForNetworkSettled(page: Page) {
    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
    await page.waitForTimeout(200);
}

/**
 * Wait until the app splash screen (logo + spinner) has been removed.
 * The splash lives in app.html as #app-splash and is removed once i18n loads.
 */
async function waitForSplashGone(page: Page) {
    await page.waitForFunction(() => !document.getElementById('app-splash'), {timeout: 10_000}).catch(() => {});
}

/**
 * Take the shot `category/name` of this combination, once the page has settled for it (galleryShot.ts, `settleShot`): the
 * pointer parked, every `/api/` request answered, no loader on screen, the animations that end ended, the images in, the
 * charts, the text and the frame still, no toast, the looping animations pinned. `options` opts a shot out of a step — a
 * shot that hovers on purpose keeps its pointer, one of a tooltip a click pinned declares it — or names its subject.
 */
async function screenshot(page: Page, viewport: 'desktop' | 'mobile', lang: Language, theme: Theme, category: string, name: string, options: ShotOptions = {}) {
    const shot = `${viewport}/${lang}/${theme}/${category}/${name}`;
    await waitForSplashGone(page);
    await settleShot(page, shot, options);
    // The page began under this language's browser locale: a forgotten switch point fails here, not as an en-US number in
    // another language's shot (galleryLocale.ts).
    await expectDrawnUnder(page, lang);
    const dir = getGalleryPath(viewport, lang, theme, category);
    ensureDir(dir);
    await captureShot(page, path.join(dir, `${name}.png`), shot);
    console.log(`  📸 ${shot}.png`);
}

// Helper to run for all languages and themes
async function forEachLanguageAndTheme(page: Page, callback: (lang: Language, theme: Theme) => Promise<void>) {
    for (const lang of SUPPORTED_LANGUAGES) {
        await setBrowserLocale(page, lang);
        await setLanguage(page, lang);
        for (const theme of THEMES) {
            await setTheme(page, theme);
            await callback(lang, theme);
        }
    }
}

/**
 * For a test whose page is set up first and then photographed in several combinations. forEachLanguageAndTheme switches on
 * the page as it stands, and what a page has drawn keeps the browser locale it was drawn under (galleryLocale.ts): `draw`
 * sets the page up again at the first combination of each language — after the header's switch, so the page it loads is
 * drawn under that language's locale, in the language and theme just stored — and what it returns serves the language's
 * two themes.
 */
function perLanguage<T>(draw: (lang: Language) => Promise<T>): (lang: Language) => Promise<T> {
    let drawn: {lang: Language; value: T} | null = null;
    return async (lang) => {
        if (drawn?.lang !== lang) drawn = {lang, value: await draw(lang)};
        return drawn.value;
    };
}

// Determine viewport from project name
function getViewport(testInfo: any): 'desktop' | 'mobile' {
    return testInfo.project.name === 'mobile' ? 'mobile' : 'desktop';
}

/**
 * The name the Security shot opens the app under: one the browser classifies as a local network (plan 36). Chromium maps it
 * onto the loopback, where the lane's backend listens, with the baseURL's protocol and port — as
 * layout/connection-security.spec.ts does.
 */
const GALLERY_LAN_NAME = 'lf-e2e.lan';

// `launchOptions` is worker-scoped: Playwright refuses it inside a describe ("forces a new worker"), so the Security shot's
// resolver rule is set here, for the whole file, as layout/connection-security.spec.ts sets its own. It maps that one name
// and nothing else, so every other shot — the baseURL, the sites the favicons come from — resolves as before; the config's
// own launch options are kept.
test.use({
    launchOptions: async ({launchOptions}, use) => {
        await use({...launchOptions, args: [...(launchOptions.args ?? []), `--host-resolver-rules=MAP ${GALLERY_LAN_NAME} 127.0.0.1`]});
    },
});

test.describe('Gallery Screenshots', () => {
    // Gallery tests iterate over 4 languages × 2 themes = 8 screenshots per test
    // Some tests also navigate (broker detail, import modal) so need extra time
    // Bumped from 180s: CI runs on a 4-vCPU public runner with --workers matched
    // to CPU count, but transient contention (backend workers, mkdocs build,
    // node overhead) still warrants a bit more default headroom.
    test.setTimeout(240_000); // 4 minutes per test (default; heavy tests override above)

    // Each gallery test is independent (logs in fresh, navigates, screenshots).
    // Run in parallel across workers for faster generation.
    test.describe.configure({mode: 'parallel'});
    // A hung action must fail in seconds, naming the real step, not at the test timeout; explicit per-call timeouts keep their value.
    test.use({actionTimeout: 20_000});
    // Reduced motion, on the context: every page of a test has it from its first document. A text too long for its box —
    // a broker or asset name on a card, a table cell, the Synthetic caption under the P&L candles — scrolls itself as a
    // marquee (scrollOnOverflow.ts) from 2 s after it mounts: a JS loop freezeAnimations() cannot stop, so shots caught
    // names mid-scroll. Under reduced motion the marquee never starts and the text rests on its beginning. The other
    // readers of the preference show the same content, standing still (coordinator's audit): the coachmark's pulse ring
    // and pointer, spinners, the price flash, a highlighted table row, Tailwind `motion-*`; the coachmark and the PAC
    // result scroll to their target at once. svelte/motion's `tweened` ignores it, so the 1 s waits for the KPI count-up
    // stay. A nested `test.use({contextOptions})` would replace this object: spread it there.
    test.use({contextOptions: {reducedMotion: 'reduce'}});
    // No locale on the context: @playwright/test would give it 'en-US', and Chromium would then refuse the locale each
    // language sets at runtime (galleryLocale.ts). `locale: undefined` keeps that default; a fixture yielding undefined does not.
    test.use({locale: async ({}, use) => use(undefined)});

    // Tests running in parallel create temporary brokers and files (group 3: disposable accounts, brokers
    // named `‹label› · ‹TOKEN›`). A session that cannot reach them still hears of them: every session caches
    // every broker's name, and a superuser's Files page lists every file. Registered before any sign-in, so
    // every page of every test is filtered; seeded data carries no mark and is never touched.
    // The gallery is offline and deterministic as well: no page reaches a real price or exchange-rate provider, or
    // writes a price. The live-price poll and the provider catalogue are answered from fixtures, a provider search as
    // offline, and a sync, a metadata refresh or a provider probe is aborted (galleryReportSets.ts, guardGalleryOffline).
    // With any route installed Playwright aborts every image whose URL ends in /favicon.ico — the brokers' logos, most
    // import plugins' icons, FED's and SNB's — so the pages write those URLs with a query that keeps them loading: an
    // init script, in force from the next document, so before the first navigation (keepFaviconImagesLoading).
    test.beforeEach(async ({page}) => {
        // First, before any request: the shots wait for the page's /api/ requests, and a failed test lists those still in
        // flight (galleryShot.ts). A request that left before this line would never be seen.
        trackApiRequests(page);
        // Before any load: every document stamps the locale it began under, and the first begins under en-US (galleryLocale.ts).
        await stampDocumentLocale(page);
        await setBrowserLocale(page, 'en');
        await hideGalleryTempData(page);
        await guardGalleryOffline(page);
        await keepFaviconImagesLoading(page);
    });

    // A failed test first says what its page was still waiting for — the /api/ requests in flight and the slowest that came
    // back (galleryShot.ts) — before anything below touches the page, and attaches the page itself: Playwright snapshots it
    // for error-context.md only after the hooks, and these leave it (attachPageSnapshotOnFailure).
    // Then the favicon fix was in force on the page the test ended on: read there, before the page goes.
    // Then the page leaves for about:blank, and only then are the routes dropped, what they were still doing ignored
    // (leaveGalleryPage): the offline guard must outlive the app. Dropped first, they left the app polling unguarded until
    // the page closed, and a live-price poll answered by the backend asks the provider and writes today's candle — on 14/10
    // one tick rewrote Apple's from Yahoo, and every Apple-dependent shot of that run after it. A page that cannot leave
    // keeps its routes until it closes.
    // Then the offline guard's record: a sync attempted, or a call it could not answer as designed, fails the test. A failed
    // favicon check fails it too, once the rest has run; when both fail, the record leads and the favicon check is its cause.
    test.afterEach(async ({page}, testInfo) => {
        logApiOnFailure(page, testInfo);
        await attachPageSnapshotOnFailure(page, testInfo);
        const favicons = await expectFaviconImagesLoading(page).then(
            () => null,
            (error: unknown) => ({error}),
        );
        await leaveGalleryPage(page, `${testInfo.project.name} › ${testInfo.title}`);
        try {
            expectGalleryOffline(page);
        } catch (offline) {
            if (!favicons) throw offline;
            throw new Error(offline instanceof Error ? offline.message : String(offline), {cause: favicons.error});
        }
        if (favicons) throw favicons.error;
    });

    test.describe('Auth Pages', () => {
        /**
         * The login page as a new document, its animations frozen again: the style tag goes with the old one. Given `lang`,
         * it is the page of that language's shots (perLanguage): it must open in the language the header just stored.
         */
        async function openLoginPage(page: Page, lang?: Language): Promise<void> {
            await page.goto('/');
            // The app's first load (the splash, then the catalogue) took more than 3 s on a loaded machine's phone.
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 30_000});
            if (lang) await expect(page.locator('html'), 'the language survived the load').toHaveAttribute('lang', lang);
            await freezeAnimations(page);
        }

        test('login page - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // The page the first switch is made on; each language then loads its own.
            await openLoginPage(page);
            const loginPageIn = perLanguage((lang) => openLoginPage(page, lang));

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await loginPageIn(lang);
                await page.waitForTimeout(100);
                await screenshot(page, viewport, lang, theme, 'auth', '01-login');
            });
        });

        test('register modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // The page the first switch is made on; each language then loads its own.
            await openLoginPage(page);
            const loginPageIn = perLanguage((lang) => openLoginPage(page, lang));

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await loginPageIn(lang);
                await expect(page.getByTestId('login-modal')).toBeVisible({timeout: 3000});
                await page.getByTestId('goto-register').click();
                await expect(page.getByTestId('register-modal')).toBeVisible({timeout: 3000});
                await page.waitForTimeout(200);
                await screenshot(page, viewport, lang, theme, 'auth', '02-register-empty');

                // Go back to login for next iteration
                await page.getByTestId('goto-login').click();
                await expect(page.getByTestId('login-modal')).toBeVisible({timeout: 3000});
            });
        });

        test('register with password strength - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // The page the first switch is made on; each language then loads its own.
            await openLoginPage(page);
            const loginPageIn = perLanguage((lang) => openLoginPage(page, lang));

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await loginPageIn(lang);
                await expect(page.getByTestId('login-modal')).toBeVisible({timeout: 3000});
                await page.getByTestId('goto-register').click();
                await expect(page.getByTestId('register-modal')).toBeVisible({timeout: 3000});

                // Fill form with sample data to show password strength
                await page.getByTestId('register-username').fill('demo_user');
                await page.getByTestId('register-email').fill('demo@example.com');
                // Find password input within register modal
                await page.getByTestId('register-modal').locator('input[type="password"]').first().fill('MyStr0ng!Pass');
                await page.waitForTimeout(500); // Let password strength meter update

                await screenshot(page, viewport, lang, theme, 'auth', '03-register-filled');

                // Go back to login for next iteration
                await page.getByTestId('goto-login').click();
                await expect(page.getByTestId('login-modal')).toBeVisible({timeout: 3000});
            });
        });

        test('update available modal (mocked release) - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            // Deterministic mock: seed the 1h-throttled update-check cache with a fake
            // newer release BEFORE the app boots. The admin layout probe
            // (checkForNewerRelease) then reads the fresh cache instead of fetching GitHub,
            // and prompts. addInitScript re-runs on every full page load, so each reload
            // re-seeds a fresh cache and the modal reappears. The shape is the one
            // updateCheck.ts writes today (tag + probeStatus), which readCache() accepts.
            await page.addInitScript(() => {
                localStorage.setItem(
                    'librefolio-update-check',
                    JSON.stringify({
                        checkedAt: Date.now(),
                        latest: {
                            version: '99.9.0',
                            tag: 'v99.9.0',
                            url: 'https://github.com/Librefolio/LibreFolio/releases/tag/v99.9.0',
                            name: 'v99.9.0',
                        },
                        probeStatus: 'success',
                    }),
                );
            });
            // The prompt is double-gated: the GitHub release (mocked via the seeded cache
            // above) AND the container image of its tag. The image gate is the same-origin
            // backend GET /api/v1/system/container-image-status?tag=99.9.0 (updateCheck.ts
            // probeImageWithApi), which answers `pending` for the fake tag and silences the
            // prompt — the gate working as designed. Answer `published` instead
            // (ContainerImageStatusResponse: `reason` is set only when status is `error`).
            let imageStatusHits = 0;
            await page.route('**/api/v1/system/container-image-status**', (route) => {
                imageStatusHits += 1;
                return route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({status: 'published', reason: null})});
            });

            await login(page, TEST_ADMIN);
            // The login load runs the probe once too: let it reach the gate first, so each reload
            // below is measured against a counter that nothing else is still moving.
            await expect.poll(() => imageStatusHits, {message: 'the admin update probe never asked the (mocked) container-image-status gate after login', timeout: 20_000}).toBeGreaterThan(0);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    // The modal backdrop blocks the header selectors, so language/theme are
                    // seeded into localStorage (read by i18n + theme boot) instead of clicked.
                    await page.evaluate(
                        ([l, t]) => {
                            localStorage.setItem('librefolio-locale', l);
                            localStorage.setItem('librefolio-theme', t);
                        },
                        [lang, theme] as [string, string],
                    );
                    // Full reload → layout auth check → cached probe → image gate → prompt (once per load)
                    const imageStatusHitsBefore = imageStatusHits;
                    await page.reload();
                    // The attribute, not visibility: with the update modal open the body is scroll-locked
                    // (position: fixed), <html> lays out with no height, and Playwright calls it hidden.
                    await expect(page.locator('html')).toHaveAttribute('data-i18n-ready', 'true', {timeout: 15_000});
                    // Two halves, so a red names the one that failed: the probe reached the image gate
                    // (the seeded release was accepted as newer), then the prompt was shown.
                    await expect.poll(() => imageStatusHits, {message: 'the admin update probe never asked the (mocked) container-image-status gate', timeout: 20_000}).toBeGreaterThan(imageStatusHitsBefore);
                    const modal = page.getByTestId('update-available-modal');
                    await expect(modal).toBeVisible({timeout: 20_000});
                    await expect(page.locator('html')).toHaveAttribute('lang', lang);
                    await expect(page.locator('html')).toHaveClass(new RegExp(`\\b${theme}\\b`));
                    await freezeAnimations(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'auth', 'update-available-modal');
                }
            }
        });
    });

    /**
     * Inventory group 5: onboarding — the first-run Welcome page, a step of the Core tour, and a contextual guide on the
     * FX page (the Onboarding category of Preferences is under Settings). Helpers and the reasons behind them:
     * fixtures/galleryOnboarding.ts.
     *
     * The canonical users have completed every flow, so each test signs up its own account, and afterEach deletes it
     * with everything it owns, failure or not. One account per test, so the variants of a shot show the same account:
     * the language and the theme are written into the browser before every full load (the Welcome page has no theme
     * toggle, and a guide's overlay lies over the header's controls), and the Welcome form, pre-filled from the
     * account's settings, gets the account's language first. A guide is walked once to its step and resumes there after
     * each load — its position is kept per account in the browser — which every combination asserts. Nothing reaches a
     * provider: the gallery-wide offline guard answers the FX page's catalogue read from its fixture and aborts any sync.
     */
    test.describe('Onboarding', () => {
        let account: GalleryAccount | undefined;

        test.beforeEach(() => {
            account = undefined;
        });

        // afterEach, not `finally`: a cleanup that throws from `finally` would replace the error it follows. A failed test
        // first logs what its page was still waiting for and attaches the page: the cleanup leaves it, its requests are
        // forgotten with it, and Playwright snapshots it only after the hooks.
        test.afterEach(async ({page, request}, testInfo) => {
            logApiOnFailure(page, testInfo);
            await attachPageSnapshotOnFailure(page, testInfo);
            if (account) await cleanupGalleryAccount(page, request, account);
        });

        test('welcome setup - all languages and themes', async ({page, request}, testInfo) => {
            // Account and sign-in ~5 s; per combination the account's language, one full load of the page and one shot,
            // ~4 s, twice that under parallel load: 8 × 8 s + 30 s.
            test.setTimeout(180_000);
            const viewport = getViewport(testInfo);
            account = await registerGalleryAccount(request);
            await login(page, account.user);
            await expect(page, 'a new account signs in to the Welcome page').toHaveURL(/\/welcome(?:[/?#]|$)/, {timeout: 15_000});

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    // Pre-filled from the account's settings: its language is the combination's, its currency its own.
                    const defaults = await setAccountLanguage(page.request, lang);
                    await seedLanguageAndTheme(page, lang, theme);
                    await navigateTo(page, '/welcome');
                    await expectLanguageAndTheme(page, lang, theme);
                    const welcome = page.getByTestId('welcome-page');
                    await expect(welcome, 'Welcome is still due: never confirmed, never skipped').toHaveAttribute('data-outcome', 'pending', {timeout: 15_000});
                    const form = welcome.getByTestId('welcome-form');
                    await expect(form).toHaveAttribute('data-busy', 'false');
                    await expect(form.getByTestId('welcome-language')).toBeVisible();
                    // The currency select draws its value once the currency list is in; until then it shows its placeholder.
                    await expect(form.getByTestId('welcome-currency').getByRole('combobox'), 'the default currency is pre-filled').toContainText(defaults.base_currency, {timeout: 15_000});
                    await expect(form.getByTestId('welcome-avatar-preview')).toBeVisible();
                    await expect(form.getByTestId('welcome-avatar-clear'), 'no picture: the initials stand in').toHaveCount(0);
                    await expect(form.getByTestId('welcome-avatar-choose')).toBeEnabled();
                    await expect(form.getByTestId('welcome-skip')).toBeEnabled();
                    await expect(form.getByTestId('welcome-continue')).toBeEnabled();
                    await expect(form.getByTestId('welcome-error')).toHaveCount(0);
                    await frameWelcome(page);
                    await parkPointer(page);
                    await freezeAnimations(page);
                    await waitForMotionSettled(welcome, 'the Welcome page');
                    await expectNoToast(page);
                    await screenshot(page, viewport, lang, theme, 'onboarding', 'welcome-setup');
                }
            }
        });

        test('core tour step - all languages and themes', async ({page, request}, testInfo) => {
            // Account, Welcome and the walk to the step ~15 s; per combination one full load of the dashboard, the tour
            // resumed on its step, the panel's 3 s fade and one shot, ~8 s, twice that under parallel load: 8 × 16 s + 40 s.
            test.setTimeout(300_000);
            const viewport = getViewport(testInfo);
            account = await registerGalleryAccount(request);
            await login(page, account.user);
            // Welcome confirmed as it comes — the account's own language and currency — hands over to the intro; the tour
            // is walked once, Next by Next, to the Exchange rates destination in the sidebar.
            await completeWelcome(page);
            await walkCoreTourToFx(page);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await seedLanguageAndTheme(page, lang, theme);
                    await navigateTo(page, '/dashboard');
                    await expectLanguageAndTheme(page, lang, theme);
                    // The dashboard lies dimmed under the tour: settled all the same.
                    await waitForSettled(page.getByTestId('dashboard-page'), 20_000);
                    // After a full load the tour resumes on its step: its position is kept per account in the browser.
                    await expectGuideStep(page, CORE_TOUR_FX_STEP, 20_000);
                    if (viewport === 'mobile') await expect(page.getByTestId('app-header'), 'on a phone the step opens the menu its destination is in').toHaveAttribute('data-sidebar-open', 'true');
                    await freezeAnimations(page);
                    const panel = await holdPanelAtFullStrength(page);
                    await waitForMotionSettled(page.getByTestId('onboarding-coachmark'), 'the Core tour');
                    await waitForStillness(panel, 'the message panel');
                    // One last reading before the shot: still on its step, anchored on a still target.
                    await expectGuideStep(page, CORE_TOUR_FX_STEP);
                    await expect(page.getByTestId('deferred-app-popups'), 'a popup waits for the tour to end, never over it').toHaveAttribute('data-active-popup', 'none');
                    await expectNoToast(page);
                    // The pointer stays on the panel: it is what holds it at full strength (holdPanelAtFullStrength).
                    await screenshot(page, viewport, lang, theme, 'onboarding', 'core-tour-step', {keepPointer: true});
                }
            }
        });

        test('contextual guide on the FX page - all languages and themes', async ({page, request}, testInfo) => {
            // Account, Welcome, the skips and the walk to the step ~20 s; per combination one full load of the FX page — its
            // two waves and its charts — the guide resumed on its step, the panel's 3 s fade and one shot, ~10 s, twice
            // that under parallel load: 8 × 20 s + 50 s.
            test.setTimeout(300_000);
            const viewport = getViewport(testInfo);
            account = await registerGalleryAccount(request);
            // Welcome confirmed as it comes, the intro closed, every guide skipped but the FX page's: no other guide competes
            // for the overlay. It opens on the page's title; Next takes it to the currency filters, real controls it pulses.
            await prepareOnboardingAccount(page, account.user, ['fx_page_guide']);
            await navigateTo(page, '/fx');
            await expectGuideStep(page, FX_PAGE_OVERVIEW_STEP, 30_000);
            await page.getByTestId('onboarding-coachmark-next').click();
            await expectGuideStep(page, FX_PAGE_FILTERS_STEP);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await seedLanguageAndTheme(page, lang, theme);
                    await navigateTo(page, '/fx');
                    await expectLanguageAndTheme(page, lang, theme);
                    // Two waves — the pairs, then each pair's rates — then the cards' charts.
                    const fx = page.getByTestId('fx-page');
                    await waitForSettled(fx, 30_000);
                    await chartsDrawn(fx, 'the FX cards');
                    // After a full load the guide resumes on its step: its position is kept per account in the browser.
                    await expectGuideStep(page, FX_PAGE_FILTERS_STEP, 30_000);
                    await freezeAnimations(page);
                    const panel = await holdPanelAtFullStrength(page);
                    await waitForMotionSettled(page.getByTestId('onboarding-coachmark'), 'the FX page guide');
                    await waitForStillness(panel, 'the message panel');
                    // One last reading before the shot: still on its step, anchored on a still target.
                    await expectGuideStep(page, FX_PAGE_FILTERS_STEP);
                    await expect(page.getByTestId('deferred-app-popups'), 'a popup waits for the guide to end, never over it').toHaveAttribute('data-active-popup', 'none');
                    await expectNoToast(page);
                    // The pointer stays on the panel: it is what holds it at full strength (holdPanelAtFullStrength).
                    await screenshot(page, viewport, lang, theme, 'onboarding', 'contextual-guide', {keepPointer: true});
                }
            }
            // Positive control: the FX page reads the provider catalogue on every load, and the gallery-wide offline guard
            // answered it — a guard on the wrong path would let the backend ask ECB and SNB unseen.
            expect(galleryOfflineGuard(page).catalogueReads, 'the FX page read no provider catalogue: the offline guard no longer matches what the page asks for').toBeGreaterThan(0);
        });
    });

    function parseLocalDateString(s: string): Date {
        const [year, month, day] = s.split('-').map(Number);
        return new Date(year, month - 1, day);
    }

    function getLocalDateString(d: Date): string {
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function shiftDatesToToday(obj: any): any {
        const datePattern = /^\d{4}-\d{2}-\d{2}$/;
        let maxDateStr: string | null = null;

        function findMaxDate(val: any) {
            if (typeof val === 'string' && datePattern.test(val)) {
                if (!maxDateStr || val > maxDateStr) {
                    maxDateStr = val;
                }
            } else if (Array.isArray(val)) {
                for (const item of val) findMaxDate(item);
            } else if (val && typeof val === 'object') {
                for (const key of Object.keys(val)) findMaxDate(val[key]);
            }
        }
        findMaxDate(obj);

        if (!maxDateStr) return obj;

        const today = new Date();
        const maxDate = parseLocalDateString(maxDateStr);

        today.setHours(0, 0, 0, 0);
        maxDate.setHours(0, 0, 0, 0);

        const diffTime = today.getTime() - maxDate.getTime();
        const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
        if (diffDays === 0) return obj;

        function shift(val: any): any {
            if (typeof val === 'string' && datePattern.test(val)) {
                const d = parseLocalDateString(val);
                d.setDate(d.getDate() + diffDays);
                return getLocalDateString(d);
            } else if (Array.isArray(val)) {
                return val.map(shift);
            } else if (val && typeof val === 'object') {
                const newObj: any = {};
                for (const key of Object.keys(val)) {
                    newObj[key] = shift(val[key]);
                }
                return newObj;
            }
            return val;
        }

        return shift(obj);
    }

    /**
     * The captured dashboard-report.json is a REAL user snapshot. If it stops validating
     * against the current report schema (zodios rejects the whole response and the
     * dashboard renders zeroed KPIs), do NOT patch or delete blocks to make it pass —
     * the snapshot must be RE-CAPTURED from a real backend by the user (see the comment
     * in the docs/testing guides). A loud failure beats a silently wrong screenshot;
     * src/lib/api/dashboardReportFixture.test.ts says it in seconds.
     *
     * One snapshot answers EVERY POST /api/v1/portfolio/report the dashboard makes (main
     * report, positions contribution, P&L candles): it carries all of those sections, so no
     * answer is merged with live data. Matched by URL only — the snapshot was captured with
     * other broker ids than the gallery DB's, so a request body is never a reason to fall
     * through to the backend. `adjust` edits the date-shifted copy, never the file.
     */
    async function setupDashboardMockReport(page: Page, adjust?: (report: {summary: {data_quality: Record<string, unknown>}}) => void): Promise<void> {
        const report = shiftDatesToToday(JSON.parse(fs.readFileSync(path.join(__dirname, 'dashboard-report.json'), 'utf8')));
        adjust?.(report);
        const body = JSON.stringify(report);
        await page.route('**/api/v1/portfolio/report', (route) => route.fulfill({status: 200, contentType: 'application/json', body}));
    }

    /**
     * The 1-year range, strictly, for the dashboard shots: selectOneYearDateRange() (below), plus a reload. The range persists
     * in the session. When the click changed it, the page is reloaded, so every chart draws once on the new range instead of
     * being redrawn, by the report the click asked for, while a shot is taken.
     */
    async function selectOneYearPreset(page: Page): Promise<void> {
        const oneYear = page.getByTestId('date-preset-1y');
        await expect(oneYear).toBeVisible({timeout: 10_000});
        if ((await oneYear.getAttribute('data-active')) === 'true') return;
        await oneYear.click();
        await expect(oneYear).toHaveAttribute('data-active', 'true');
        await page.reload();
        await expect(page.getByTestId('date-preset-1y')).toHaveAttribute('data-active', 'true', {timeout: 15_000});
    }

    /**
     * The served snapshot reached the page — asserted before every dashboard shot. From 09-11 the
     * mocked report failed Zod, the dashboard drew nothing, and these shots stayed green. Settled
     * alone proves nothing (a rejected report settles too); the % toggle does: GrowthChart enables
     * it only when the history carries performance data. Overview tab only — it holds the chart.
     */
    async function expectDashboardReportLoaded(page: Page): Promise<void> {
        await waitForSettled(page.getByTestId('dashboard-page'), 20_000);
        await expect(page.getByTestId('growth-chart')).toBeVisible();
        await expect(page.getByTestId('growth-toggle-pct'), 'no performance history on the dashboard — was the served dashboard-report.json rejected by Zod?').toBeEnabled({timeout: 10_000});
        await expect(page.getByTestId('kpi-period-pnl').getByTestId('kpi-value')).toBeVisible();
        await expect(page.getByTestId('kpi-net-worth').getByTestId('kpi-value')).toBeVisible();
    }

    /**
     * Switch the growth chart to `mode` and return once it has drawn it. The chart counts its
     * finished render passes in data-chart-renders (attachChartReady): read before the click and
     * awaited after, so the shot follows a pass of the new mode, not a guessed animation length.
     * The mode must really change — a click on the active one draws nothing.
     */
    async function switchGrowthMode(page: Page, mode: 'eur' | 'pct' | 'pnl'): Promise<void> {
        const growthChart = page.getByTestId('growth-chart');
        const toggle = growthChart.getByTestId(`growth-toggle-${mode}`);
        const drawing = growthChart.locator('[data-chart-renders]');
        const renders = async () => Number((await drawing.getAttribute('data-chart-renders', {timeout: 2_000}).catch(() => null)) ?? '0');
        await expect(toggle).toBeEnabled();
        await expect(toggle, `the growth chart is already in ${mode}: no render pass would follow the click`).not.toHaveAttribute('aria-pressed', 'true');
        const before = await renders();
        await toggle.click();
        await expect(toggle).toHaveAttribute('aria-pressed', 'true');
        await expect.poll(renders, {message: `the growth chart never redrew in ${mode}`, timeout: 10_000}).toBeGreaterThan(before);
    }

    /**
     * Switch the growth chart's P&L view to `submode` and return once it has drawn it: switchGrowthMode's contract, one
     * level down. The render count is read before the click and awaited after, so the submode must really change — a
     * click on the active one draws nothing.
     */
    async function switchPnlSubmode(page: Page, submode: 'line' | 'candles' | 'income'): Promise<void> {
        const toggle = page.getByTestId('growth-chart').getByTestId(`growth-pnl-submode-${submode}`);
        await expect(toggle).toBeVisible();
        await expect(toggle, `the P&L view is already ${submode}: no render pass would follow the click`).not.toHaveAttribute('aria-pressed', 'true');
        const before = await growthChartRenders(page);
        await toggle.click();
        await expect(toggle).toHaveAttribute('aria-pressed', 'true');
        await expect.poll(() => growthChartRenders(page), {message: `the growth chart never redrew in ${submode}`, timeout: 10_000}).toBeGreaterThan(before);
    }

    /** Where the growth chart draws: the element that counts its finished render passes (attachChartReady) and holds its ECharts instance (`__lfChart`). */
    function growthDrawing(page: Page): Locator {
        return page.getByTestId('growth-chart').locator('[data-chart-renders]');
    }

    /** The growth chart's finished render passes: read before an action, awaited after it. */
    async function growthChartRenders(page: Page): Promise<number> {
        const drawing = growthDrawing(page);
        return Number((await drawing.getAttribute('data-chart-renders', {timeout: 2_000}).catch(() => null)) ?? '0');
    }

    /**
     * The items of the growth chart's `type` series that carry a value — a candle rather than the `'-'` gap, a bar or a
     * point that is not zero — in the option the chart handed ECharts, read through its test hook (`__lfChart`) as
     * dashboard.spec.ts reads it: the canvas has no DOM to ask.
     */
    async function growthItems(page: Page, type: 'line' | 'candlestick' | 'bar'): Promise<number> {
        return growthDrawing(page).evaluate((node, seriesType) => {
            const series: any[] = ((node as any).__lfChart?.getOption?.()?.series ?? []).filter((entry: any) => entry?.type === seriesType);
            const amountOf = (item: any) => {
                const value = item !== null && typeof item === 'object' && !Array.isArray(item) ? item.value : item;
                return Array.isArray(value) ? value[value.length - 1] : value;
            };
            return series.flatMap((entry) => (Array.isArray(entry.data) ? entry.data : [])).filter((item) => typeof amountOf(item) === 'number' && amountOf(item) !== 0).length;
        }, type);
    }

    /**
     * How many x-axis labels the growth chart painted: canvas text, read off the zrender scene through the same hook —
     * dashboard.spec.ts's `ladderSnapshot`, reduced to a count. A label the overlap pass hid, or a blank one, does not count.
     */
    async function paintedAxisLabels(page: Page): Promise<number> {
        return growthDrawing(page).evaluate((node) => {
            const chart = (node as any).__lfChart;
            const axis = chart?.getModel?.()?.getComponent?.('xAxis', 0);
            const view = axis ? chart.getViewOfComponentModel?.(axis) : null;
            let painted = 0;
            view?.group?.traverse((el: any) => {
                if (el.type !== 'text' || !String(el.anid ?? '').startsWith('label_') || el.ignore || el.invisible) return;
                const spans: any[] = el.childrenRef?.() ?? el._children ?? [];
                if (spans.some((span) => typeof span?.style?.text === 'string' && span.style.text.trim() !== '')) painted += 1;
            });
            return painted;
        });
    }

    /** What the growth chart's own y-axis formatter prints for `values`, read fresh from `getOption()`: dashboard.spec.ts's `axisLabels`. */
    async function growthAxisLabels(page: Page, values: number[]): Promise<string[]> {
        return growthDrawing(page).evaluate((node, amounts) => {
            const formatter = (node as any).__lfChart?.getOption?.()?.yAxis?.[0]?.axisLabel?.formatter;
            return typeof formatter === 'function' ? amounts.map((amount) => String(formatter(amount))) : [];
        }, values);
    }

    /**
     * Frame the growth chart as `main` frames it — from the top of the page, scrolled into view by the browser: on the
     * desktop the end of the page, on a phone the card centred — and return the card's top. Called once per combination,
     * with the card at its height in `main` (nothing under the chart), and every P&L view is shot from there: those shots
     * join `main`'s carousel, where a card that moved between two items would jump. The Candles caption only adds height
     * below. The pointer rests off the chart first, so the scroll slides no chart under it and no tooltip opens.
     */
    async function frameGrowthChart(page: Page): Promise<number> {
        const growthChart = page.getByTestId('growth-chart');
        await parkPointer(page);
        await scrollBackToHeader(page);
        await growthChart.scrollIntoViewIfNeeded();
        await expect(growthChart, 'the whole card is in the frame').toBeInViewport({ratio: 1});
        await expect(page.getByTestId('app-header'), 'the header has slid away, as in main').toHaveAttribute('data-scroll-state', 'hidden');
        const box = await growthChart.boundingBox();
        if (!box) throw new Error('the growth chart has no box');
        return box.y;
    }

    /** The card is still where frameGrowthChart() put it: switching views moves nothing above its bottom edge. */
    async function expectGrowthChartAt(page: Page, top: number): Promise<void> {
        await expect.poll(async () => (await page.getByTestId('growth-chart').boundingBox())?.y ?? Number.NaN, {message: 'the growth chart moved since it was framed'}).toBeCloseTo(top, 0);
    }

    /**
     * `PRIVACY_PLACEHOLDER` of src/lib/utils/privacy/maskable.ts, copied rather than imported, as privacy-masking.spec.ts
     * does: that module imports the runes privacy store, which Playwright's loader cannot compile.
     */
    const PRIVACY_PLACEHOLDER = '•••';

    /**
     * Hide or show amounts from the header's eye button, the state asserted on both sides: privacy-masking.spec.ts's
     * flipPrivacy, with the mouse alone, as a user does. The header is on screen first, and the button with it. No focus
     * is given: keyboard focus would pin the header, but it lights the button's focus-visible ring, which the click does
     * not clear — a ring in every privacy shot. A mouse click leaves none, and does not pin the header (T-7): the scene
     * brings the header back by scrolling instead.
     */
    async function setPrivacyFromHeader(page: Page, on: boolean): Promise<void> {
        const toggle = page.getByTestId('privacy-toggle');
        await expect(toggle, `privacy must start ${on ? 'off' : 'on'}`).toHaveAttribute('aria-pressed', String(!on));
        await expect(page.getByTestId('app-header'), 'the header is on screen, not slid away').toHaveAttribute('data-scroll-state', 'visible');
        await expect(toggle, 'and so is the eye button').toBeInViewport({ratio: 1});
        await toggle.click();
        await expect(toggle).toHaveAttribute('aria-pressed', String(on));
    }

    /**
     * Show one allocation tab in one view and return once its chart has drawn. Both buttons are
     * toggles whose end state (aria-pressed) is asserted. Now: the pie or the map is mounted for
     * the tab, so the first pass its container reports (data-chart-ready) is the data pass.
     * History: that chart stays mounted but draws only while visible, so turning the view on
     * causes a pass — its data-chart-renders count is read before the clicks and awaited after.
     */
    async function showAllocation(page: Page, tab: 'type' | 'sector' | 'geo', view: 'now' | 'history'): Promise<void> {
        const panel = page.getByTestId('allocation-panel');
        const tabButton = panel.getByTestId(`allocation-tab-${tab}`);
        const viewButton = panel.getByTestId(`allocation-view-${view}`);
        const historyChart = panel.getByTestId('allocation-history-chart');
        const historyRenders = async () => Number((await historyChart.getAttribute('data-chart-renders', {timeout: 2_000}).catch(() => null)) ?? '0');
        const historyTurnsOn = view === 'history' && (await viewButton.getAttribute('aria-pressed')) !== 'true';
        const historyRendersBefore = await historyRenders();
        await tabButton.click();
        await expect(tabButton).toHaveAttribute('aria-pressed', 'true');
        await viewButton.click();
        await expect(viewButton).toHaveAttribute('aria-pressed', 'true');
        if (view === 'now') {
            await expect(panel.locator('[data-chart-ready]:not([data-testid="allocation-history-chart"])')).toHaveAttribute('data-chart-ready', 'true', {timeout: 10_000});
            return;
        }
        await expect(historyChart).toBeVisible({timeout: 10_000});
        if (historyTurnsOn) await expect.poll(historyRenders, {message: `the allocation history never drew ${tab}`, timeout: 10_000}).toBeGreaterThan(historyRendersBefore);
        await expect(historyChart).toHaveAttribute('data-chart-ready', 'true');
    }

    /**
     * Choose the date preset `key` (DateRangePicker: `date-preset-{key}`, `data-active`), strictly: the button is waited for,
     * clicked only when it is not the active one already — the range persists in the session — and its active state asserted.
     * These helpers used to give the bar half a second (`appears(button, 500)`) and, on a bar not painted by then, click
     * nothing: under load the window stayed at the 3-month default, in silence (plan 56, class C).
     */
    async function selectDatePreset(page: Page, key: '1y' | 'max'): Promise<void> {
        const preset = page.getByTestId(`date-preset-${key}`);
        await expect(preset, `the date preset ${key} is on the page`).toBeVisible({timeout: 15_000});
        if ((await preset.getAttribute('data-active')) !== 'true') await preset.click();
        await expect(preset, `the date preset ${key} is the active one`).toHaveAttribute('data-active', 'true');
    }

    // FIFO screenshots: the whole history («All»), so the engine centres on the lots' full lifecycle. Both pages that call it,
    // the dashboard and a broker's page, offer it (only the replay's picker leaves it out, L4Replay.svelte): no 2-year fallback.
    async function selectMaxDateRange(page: Page) {
        await selectDatePreset(page, 'max');
    }

    // Non-FIFO screenshots use a fixed 1-year window (deterministic, not the ambient
    // 3-month sessionStorage default) — FIFO screenshots use selectMaxDateRange() instead
    // so the engine auto-centers on the lots' full lifecycle.
    async function selectOneYearDateRange(page: Page) {
        await selectDatePreset(page, '1y');
    }

    const POSITIONS_SCREENSHOT_VARIANTS = [
        {
            semantic: 'holdings',
            visual: 'table',
            name: 'positions-holdings-table',
        },
        {
            semantic: 'holdings',
            visual: 'map',
            name: 'positions-holdings-map',
        },
        {
            semantic: 'performance',
            visual: 'table',
            name: 'positions-performance-table',
        },
        {
            semantic: 'performance',
            visual: 'map',
            name: 'positions-performance-map',
        },
    ] as const;

    /**
     * Open the page of the broker named `brokerName` (seeded data, not a translation) from the broker list: once the list has
     * its brokers in (`brokers-page`, `data-busy`), by its card — never the first card, which is whatever the list sorts first
     * (Charles Schwab today) — and end on the broker's page.
     */
    async function openBrokerCardByName(page: Page, brokerName: string) {
        await waitForSettled(page.getByTestId('brokers-page'), 20_000);
        const brokerCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: brokerName}).first();
        await expect(brokerCard, `the broker list shows ${brokerName}`).toBeVisible({timeout: 5_000});
        await brokerCard.scrollIntoViewIfNeeded();
        await brokerCard.click();
        await expect(page.getByTestId('broker-detail-page'), `${brokerName}'s page is open`).toBeVisible({timeout: 20_000});
    }

    async function setPositionsView(page: Page, semantic: 'holdings' | 'performance', visual: 'table' | 'map') {
        const semanticButton = page.getByTestId(`positions-toggle-${semantic}`);
        await expect(semanticButton).toBeVisible({timeout: 5_000});
        await semanticButton.scrollIntoViewIfNeeded();
        await semanticButton.click({timeout: 5_000});

        const visualButton = page.getByTestId(`positions-toggle-${visual}`);
        await expect(visualButton).toBeVisible({timeout: 5_000});
        await visualButton.scrollIntoViewIfNeeded();
        await visualButton.click({timeout: 5_000}).catch(async () => {
            await visualButton.click({timeout: 5_000, force: true});
        });

        // Wait for the ACTUAL content root, not networkidle+fixed-sleep. PositionsPanel
        // shows an animate-pulse skeleton while `loading`/`contributionLoading` is true
        // and only swaps to real content once data has arrived — that swap is the true
        // "loaded" signal. The previous networkidle+700ms wasn't always enough for the
        // on-demand `performance` contribution fetch (bug: mobile positions-performance-table
        // gallery screenshot captured the loading skeleton instead of real rows).
        // The charts' redraw (treemap, performance chart) is the shot's settle's to wait for.
        const contentTestId = semantic === 'holdings' ? (visual === 'table' ? 'exposure-table' : 'exposure-treemap') : visual === 'table' ? 'contribution-table' : 'performance-chart';
        await expect(page.getByTestId(contentTestId)).toBeVisible({timeout: 15_000});
    }

    /**
     * The four views of the positions panel, each framed the same way in every run. The panel used to be scrolled into view
     * once, before the first view, racing its load: still a short skeleton, it was in view already and nothing scrolled;
     * loaded, it was not and the page scrolled — the same shot from two frames (b5_c4_2). Now each view is framed once its
     * content is on screen: on a phone, and on the desktop for the views not in `tall`, from the top of the page with the panel
     * 8 px under the screen's edge (frameTarget) — or as near as the page allows: a broker with few positions ends first, the
     * scroll stops short and the header stays, the same in every run; on the desktop, the views in `tall` keep their frame —
     * the top of the page, on a screen grown to the panel's end (galleryTallShots.ts).
     */
    async function screenshotPositionsVariants(page: Page, viewport: 'desktop' | 'mobile', lang: Language, theme: Theme, category: string, tall: readonly string[] = []) {
        const positionsPanel = page.getByTestId('positions-panel');
        await expect(positionsPanel).toBeVisible({timeout: 5_000});

        for (const variant of POSITIONS_SCREENSHOT_VARIANTS) {
            await setPositionsView(page, variant.semantic, variant.visual);
            if (viewport === 'desktop' && tall.includes(variant.name)) {
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the frame from the top of the page and a
                // screen as tall as the panel — the holdings map and the performance chart grow with the screen, so it is
                // measured again after each resize — and the project's screen again right after the shot.
                await scrollBackToHeader(page);
                await extendScreenToBlock(page, positionsPanel, `desktop/${lang}/${theme}/${category}/${variant.name}`);
            } else {
                await frameTarget(page, positionsPanel, `${viewport}/${lang}/${theme}/${category}/${variant.name}`);
            }
            await screenshot(page, viewport, lang, theme, category, variant.name);
            await restoreTallScreen(page);
        }
    }

    const LOTS_SCREENSHOT_VARIANTS = [
        {testId: 'lot-wac-price-chart', name: 'fifo-lots-wac-chart'},
        {testId: 'lot-gantt-chart', name: 'fifo-lots-gantt-chart'},
        {testId: 'unified-lots-table', name: 'fifo-lots-table'},
        {testId: 'lot-comparison-chart', name: 'fifo-lots-comparison-chart'},
    ] as const;

    /**
     * The FIFO lots panel's shots, from the panel as the test opened it. Loaded first, strictly: the panel's skeleton gone, the
     * WAC and Gantt charts drawn. LotsAnalysisPanel slides open (200 ms) and, once its box stands still, scrolls itself to the
     * top of the screen, smoothly (`scrollPanelIntoViewWhenStable`); the spec used to scroll at once and wait 800 ms, so the
     * frame landed 35–70 px apart from run to run, the panel's title cut in one (plan 56, class B). Now the panel's own scroll
     * is let end — the page standing still — and the frame is taken again from the top of the page, the panel 8 px under the
     * screen's edge, or as near as the page's end allows (frameTarget).
     */
    async function captureLotsAnalysisScreenshots(page: Page, viewport: 'desktop' | 'mobile', lang: Language, theme: Theme, category: string) {
        const shot = (name: string) => `${viewport}/${lang}/${theme}/${category}/${name}`;
        const panel = page.getByTestId('lots-analysis-panel');
        await expect(panel).toBeVisible({timeout: 5_000});
        await expect(panel.getByTestId('lots-analysis-panel-loading'), 'the lots analysis has loaded').toBeHidden({timeout: 30_000});
        // Drawn, both: chartsDrawn polls the whole budget, where waitForChart gives a chart two seconds to exist.
        await chartsDrawn(panel.getByTestId('lot-wac-price-chart'), 'the WAC chart of the lots analysis');
        await chartsDrawn(panel.getByTestId('lot-gantt-chart'), 'the Gantt chart of the lots analysis');
        await scrollStill(page, shot('fifo-lots-panel'));
        await frameTarget(page, panel, shot('fifo-lots-panel'));
        await screenshot(page, viewport, lang, theme, category, 'fifo-lots-panel');

        for (const variant of LOTS_SCREENSHOT_VARIANTS) {
            const block = page.getByTestId(variant.testId);
            await expect(block).toBeVisible({timeout: 10_000});
            await block.scrollIntoViewIfNeeded();
            await screenshot(page, viewport, lang, theme, category, variant.name);
        }

        // The comparison's Return mode: its toggle is drawn with the chart (LotComparisonChart), which opens in Value — so the
        // click is a change, and the chart's next drawing (its render counter, read before the click) is the new mode's.
        const comparisonReturnToggle = page.getByTestId('lot-comparison-mode-return');
        const comparisonDrawing = page.getByTestId('lot-comparison-echart');
        const comparisonRenders = async () => Number((await comparisonDrawing.getAttribute('data-chart-renders')) ?? '0');
        await expect(comparisonReturnToggle).toBeVisible({timeout: 10_000});
        await expect(comparisonReturnToggle, 'the comparison opens in Value').toHaveAttribute('aria-pressed', 'false');
        const rendersBefore = await comparisonRenders();
        await comparisonReturnToggle.click();
        await expect(comparisonReturnToggle).toHaveAttribute('aria-pressed', 'true');
        await expect.poll(comparisonRenders, {message: 'the comparison chart never redrew in Return', timeout: 10_000}).toBeGreaterThan(rendersBefore);
        await screenshot(page, viewport, lang, theme, category, 'fifo-lots-comparison-chart-return');

        const table = page.getByTestId('unified-lots-table');
        await clickRowAction(page, table, 'lot-view-details-action');
        await expect(page.getByTestId('lot-custody-modal')).toBeVisible({timeout: 5_000});
        await screenshot(page, viewport, lang, theme, category, 'fifo-lots-custody-modal');
        await page.getByTestId('lot-custody-modal-close').click();
        await expect(page.getByTestId('lot-custody-modal')).toBeHidden({timeout: 5_000});
    }

    /** The wizard shots' sample report: its UNETF row is step 4's unresolved asset, its AAPL rows the likely duplicates. */
    const WIZARD_SAMPLE = 'generic_simple.csv';

    /**
     * Select the wizard shots' sample in step 2 and analyse it; returns the parse response. The sample is the seeded file
     * (populate_mock_data.py, on Interactive Brokers), found by its name in the admin's own listing — the oldest of that name,
     * should a copy exist — and selected in its broker's panel by its id, on whichever page of the panel it is
     * (import-wizard.ts, selectBrokerFile). Three probes used to look for «the first row named so» on the panels as drawn and,
     * missing it, skip the analysis and its shots in silence (M-15). Parse is clicked with that one file selected and its
     * response captured (parseSelectedFile): it says whether leaving the analysis asks to confirm its notices (continueToReview),
     * which a three-second probe used to guess (plan 56, class C).
     */
    async function analyseWizardSample(page: Page): Promise<ParseResponse> {
        const sample = (await brimFilesListed(page.request)).filter((file) => file.filename === WIZARD_SAMPLE && file.target_broker_id !== null).sort((a, b) => a.uploaded_at.localeCompare(b.uploaded_at))[0];
        if (!sample) throw new Error(`No ${WIZARD_SAMPLE} on any broker the admin reaches — check populate_mock_data.py`);
        const fileId = await selectBrokerFile(page, {brokerId: sample.target_broker_id as number, fileId: sample.file_id});
        return parseSelectedFile(page, fileId);
    }

    test.describe('Dashboard', () => {
        test.beforeEach(async ({page}) => {
            // Use TEST_ADMIN since db populate assigns brokers to admin
            await login(page, TEST_ADMIN);
        });

        test('main dashboard - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await setupDashboardMockReport(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await selectOneYearPreset(page);
                await freezeAnimations(page);
                await expectDashboardReportLoaded(page);

                // Top-of-dashboard screenshot (scroll=0): KPI cards with the snapshot's figures.
                // The svelte/motion `tweened()` count-up (TweenedValue, 900 ms, JS-driven — not a
                // CSS animation, so freezeAnimations() cannot stop it) publishes no settled state,
                // so this wait stays until the component exposes one.
                await page.waitForTimeout(1_000);
                await page.evaluate(() => window.scrollTo(0, 0));
                await screenshot(page, viewport, lang, theme, 'dashboard', 'kpi-top');

                // Scroll to the growth chart so it is visible and positioned nicely
                await page.getByTestId('growth-chart').scrollIntoViewIfNeeded();

                // Abs for 'main', % for 'main-pct', each shot right after a render pass of its own
                // mode. The chart remembers its last mode per user and this loop leaves it in %, so
                // Abs is normally a switch; when it is already Abs (first combo), go through % first,
                // or there would be no fresh pass to wait for.
                if ((await page.getByTestId('growth-toggle-eur').getAttribute('aria-pressed')) === 'true') await switchGrowthMode(page, 'pct');
                await switchGrowthMode(page, 'eur');
                await screenshot(page, viewport, lang, theme, 'dashboard', 'main');

                await switchGrowthMode(page, 'pct');
                await screenshot(page, viewport, lang, theme, 'dashboard', 'main-pct');
            });
        });

        test('dashboard growth P&L submodes - all languages and themes', async ({page}, testInfo) => {
            // Per combination one full load, the 1 s count-up and three views, each with its render pass and its shot, ~11 s,
            // twice that under parallel load: 8 × 22 s + 60 s.
            test.setTimeout(240_000);
            const viewport = getViewport(testInfo);
            await setupDashboardMockReport(page);
            const candleOpenings = new Set<string>();

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await selectOneYearPreset(page);
                await freezeAnimations(page);
                await expectDashboardReportLoaded(page);
                // On the desktop the last rows of the KPI cards are in these frames, above the chart.
                // The svelte/motion `tweened()` count-up (TweenedValue, 900 ms, JS-driven — not a
                // CSS animation, so freezeAnimations() cannot stop it) publishes no settled state,
                // so this wait stays until the component exposes one.
                await page.waitForTimeout(1_000);

                const growthChart = page.getByTestId('growth-chart');
                const candleWidths = growthChart.getByTestId('growth-candle-width');
                const pressedWidth = candleWidths.locator('[aria-pressed="true"]');

                // P&L on Line before the first shot. A fresh browser opens the chart in Abs, and P&L on Line; from the second
                // combination on, the chart opens where the previous one left it: P&L on Line. Never on Income — entering
                // Income, by a click or on mounting, opens it on 1M, and Candles would then keep 1M: their own opening applies
                // only on the first entry into the width ladder after a load.
                if ((await growthChart.getByTestId('growth-toggle-pnl').getAttribute('aria-pressed')) !== 'true') await switchGrowthMode(page, 'pnl');
                await expect(growthChart.getByTestId('growth-pnl-submode-line'), 'P&L opens on Line: Candles will be the first view on the width ladder since this load').toHaveAttribute('aria-pressed', 'true');
                const top = await frameGrowthChart(page);

                // Candles, on the width their opening picks: the finest this plot can draw. Recorded, not asserted — on a
                // phone the plot is a few pixels from the 3D/1W edge, where the host's scrollbar gutter decides.
                await switchPnlSubmode(page, 'candles');
                await expect(pressedWidth, 'one candle width is pressed: the one the opening picked').toHaveCount(1);
                await expect.poll(() => growthItems(page, 'candlestick'), {message: "the snapshot's pnl_candles reached the chart"}).toBeGreaterThan(0);
                await expect.poll(() => paintedAxisLabels(page), {message: 'the axis names the periods under the candles'}).toBeGreaterThanOrEqual(2);
                await parkPointer(page);
                await expectGrowthChartAt(page, top);
                await expect(growthDrawing(page), 'the candles and their axis are in the shot').toBeInViewport({ratio: 1});
                await expect(candleWidths, 'and so is the width picker').toBeInViewport({ratio: 1});
                await expect(growthChart.getByTestId('growth-pnl-candles-hypothetical-label'), 'and the Synthetic caption').toBeInViewport({ratio: 1});
                const opening = ((await pressedWidth.getAttribute('data-testid')) ?? '').replace('growth-candle-width-', '').toUpperCase();
                candleOpenings.add(opening);
                console.log(`  🕯️ ${viewport}/${lang}/${theme}: Candles opened on ${opening}`);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'growth-pnl-candles');

                // Income opens on 1M on every entry: monthly groups of bars, and under them the axis naming each month.
                await switchPnlSubmode(page, 'income');
                await expect(growthChart.getByTestId('growth-candle-width-1m'), 'Income opens on 1M').toHaveAttribute('aria-pressed', 'true');
                await expect(pressedWidth).toHaveCount(1);
                await expect.poll(() => growthItems(page, 'bar'), {message: "the snapshot's income, costs, deposits and purchases reached the chart"}).toBeGreaterThan(0);
                await expect.poll(() => paintedAxisLabels(page), {message: 'the axis names the months under the bars'}).toBeGreaterThanOrEqual(2);
                await parkPointer(page);
                await expectGrowthChartAt(page, top);
                await expect(growthChart, 'the whole card is in the shot').toBeInViewport({ratio: 1});
                await screenshot(page, viewport, lang, theme, 'dashboard', 'growth-pnl-income');

                // Line last: it leaves the chart on P&L Line for the next combination.
                await switchPnlSubmode(page, 'line');
                await expect.poll(() => growthItems(page, 'line'), {message: 'the P&L line reached the chart'}).toBeGreaterThan(0);
                await parkPointer(page);
                await expectGrowthChartAt(page, top);
                await expect(growthChart, 'the whole card is in the shot').toBeInViewport({ratio: 1});
                await screenshot(page, viewport, lang, theme, 'dashboard', 'growth-pnl-line');
            });

            // The width Candles opened on, per viewport, for the run's report.
            testInfo.annotations.push({type: 'candles-opening-width', description: `${viewport}: ${[...candleOpenings].join(', ')}`});
        });

        test('dashboard privacy mode - all languages and themes', async ({page}, testInfo) => {
            // Per combination one full load, the 1 s count-up, the eye button both ways with the chart's redraw and one shot,
            // ~7 s, twice that under parallel load: 8 × 14 s + 50 s.
            test.setTimeout(180_000);
            const viewport = getViewport(testInfo);
            await setupDashboardMockReport(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await selectOneYearPreset(page);
                await freezeAnimations(page);
                await expectDashboardReportLoaded(page);
                await expect(page.getByTestId('growth-toggle-eur'), 'the growth chart is in Abs: a fresh browser opens it there, and this test never leaves it').toHaveAttribute('aria-pressed', 'true');
                // The KPI cards are the subject of this shot.
                // The svelte/motion `tweened()` count-up (TweenedValue, 900 ms, JS-driven — not a
                // CSS animation, so freezeAnimations() cannot stop it) publishes no settled state,
                // so this wait stays until the component exposes one.
                await page.waitForTimeout(1_000);

                // Hide amounts, from the eye button at the top of the page. The growth chart's axis labels are canvas text
                // that ECharts caches, so masking them redraws the whole chart: its count is read before, awaited after.
                await scrollBackToHeader(page);
                const rendersBefore = await growthChartRenders(page);
                await setPrivacyFromHeader(page, true);
                await expect.poll(() => growthChartRenders(page), {message: 'the growth chart never redrew under privacy', timeout: 10_000}).toBeGreaterThan(rendersBefore);

                // Masked. The chart, through its own y-axis formatter (`__lfChart`): the magnitude and its k/M suffix become
                // the placeholder, the sign stays outside it (D8).
                await expect.poll(() => growthAxisLabels(page, [20_000, -5_000, 0]), {message: "the growth chart's amount axis is masked, the sign kept"}).toEqual([expect.stringMatching(/^•••$/), expect.stringMatching(/^[-\u2212]•••$/), expect.stringMatching(/^•••$/)]);
                // The KPI amounts have no hook of their own: maskable() swaps the digits for the placeholder before the string
                // exists, so the placeholder and the missing digits are what there is to read — data, not translation. ROI is
                // a percentage, no amount, and stays readable (D5′, D6): the negative control.
                for (const card of ['kpi-period-pnl', 'kpi-net-worth']) {
                    const amount = page.getByTestId(card).getByTestId('kpi-value');
                    await expect(amount, `${card}: the amount is masked`).toContainText(PRIVACY_PLACEHOLDER);
                    await expect(amount, `${card}: no digit is left`).not.toHaveText(/\d/);
                }
                await expect(page.getByTestId('kpi-return-roi-value'), 'ROI stays readable').toHaveText(/\d/);

                // The frame: the KPI row right under the header. The date-range toolbar above the cards scrolls away, and the
                // room it leaves goes to the growth chart below them: on the desktop its header and the top of its masked
                // axis, on a phone none of it, the cards being stacked there.
                await page.getByTestId('kpi-row').evaluate((row) => {
                    const header = document.querySelector('[data-testid="app-header"]')?.getBoundingClientRect().height ?? 0;
                    // 16 px: the dashboard's gap between its blocks (space-y-4).
                    window.scrollTo({top: Math.max(0, row.getBoundingClientRect().top + window.scrollY - header - 16), behavior: 'instant'});
                });
                // No focus holds the header (its keyboard ring would show in the shot): the header's own scroll rule brings it
                // back (Header.svelte, the distance accumulated per direction). 8 px further down, HIDE_SCROLL_THRESHOLD, slide
                // it away; 8 px back up, past SHOW_SCROLL_THRESHOLD (4), to the very frame above, bring it back. The header
                // reads a scroll in the animation frame its listener schedules: each step waits for its `scroll` event and two
                // frames, so the state read next is the header's verdict on that step, not on the two at once.
                const framedTop = await page.evaluate(() => window.scrollY);
                const scrollSeen = (top: number) =>
                    page.evaluate(async (y) => {
                        const from = window.scrollY;
                        const scrolled = new Promise<void>((resolve) => window.addEventListener('scroll', () => resolve(), {once: true}));
                        window.scrollTo({top: y, behavior: 'instant'});
                        if (window.scrollY !== from) await scrolled;
                        await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
                        return window.scrollY;
                    }, top);
                expect(await scrollSeen(framedTop + 8), 'the page has room to scroll 8 px further down').toBeGreaterThan(framedTop);
                await expect(page.getByTestId('app-header'), '8 px further down, HIDE_SCROLL_THRESHOLD, the header slides away').toHaveAttribute('data-scroll-state', 'hidden');
                expect(await scrollSeen(framedTop), 'back up, the frame is exactly the framing one again').toBeCloseTo(framedTop, 0);
                await expect(page.getByTestId('app-header'), 'the header is back after an upward scroll past SHOW_SCROLL_THRESHOLD, not pinned by focus').toHaveAttribute('data-scroll-state', 'visible');
                await expect(page.getByTestId('privacy-toggle'), 'the eye button is in the shot').toBeInViewport({ratio: 1});
                await expect(page.getByTestId('kpi-period-pnl').getByTestId('kpi-value'), 'and so is the first masked amount').toBeInViewport({ratio: 1});
                await parkPointer(page);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'privacy-masked');

                // Off again, from the same button, and the amounts come back in place: the next combination loads in the clear.
                await setPrivacyFromHeader(page, false);
                await expect(page.getByTestId('kpi-net-worth').getByTestId('kpi-value'), 'the amounts are back').toHaveText(/\d/);
            });
        });

        test('mobile menu open', async ({page}, testInfo) => {
            if (testInfo.project.name !== 'mobile') {
                test.skip();
                return;
            }
            await setupDashboardMockReport(page);

            const menuToggle = page.getByTestId('mobile-menu-toggle');

            // Take screenshot for each language and theme
            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    // Navigate fresh to dashboard for each combo (ensures clean state)
                    await page.goto('/dashboard');
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await selectOneYearPreset(page);
                    await freezeAnimations(page);
                    // The dashboard behind the drawer is part of the shot
                    await expectDashboardReportLoaded(page);

                    // Set language and theme while menu is closed
                    await setLanguage(page, lang);
                    await setTheme(page, theme);

                    // Open the menu for the shot. The drawer is open once its contents are wholly
                    // on screen (transitions are frozen, so it does not slide).
                    await menuToggle.click();
                    await expect(page.getByTestId('logout-button')).toBeInViewport({ratio: 1});

                    await screenshot(page, 'mobile', lang, theme, 'dashboard', 'menu-open');
                    // No need to close - we navigate away next iteration
                }
            }
        });

        test('dashboard allocation charts - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await setupDashboardMockReport(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await selectOneYearPreset(page);
                await freezeAnimations(page);
                await expectDashboardReportLoaded(page);

                // Scroll to the allocation panel
                const allocPanel = page.getByTestId('allocation-panel');
                await expect(allocPanel).toBeVisible();
                await allocPanel.scrollIntoViewIfNeeded();

                // Now then History for each dimension — the same six shots, in the same order.
                // Tab and view persist per user, so every step states both and waits for its chart.
                for (const [tab, shot] of [
                    ['type', 'allocation-type'],
                    ['sector', 'allocation-sector'],
                    ['geo', 'allocation-geo'],
                ] as const) {
                    await showAllocation(page, tab, 'now');
                    await screenshot(page, viewport, lang, theme, 'dashboard', `${shot}-now`);
                    await showAllocation(page, tab, 'history');
                    await screenshot(page, viewport, lang, theme, 'dashboard', `${shot}-history`);
                }

                // Scroll back to top so next iteration starts clean
                await page.evaluate(() => window.scrollTo(0, 0));
            });
        });

        test('dashboard positions tab - all languages and themes', async ({page}, testInfo) => {
            // Four variants a combination; on the desktop each on a screen as tall as the panel (the map and the chart need a
            // few resizes, they grow with the screen) and back: above the 4-minute default.
            test.setTimeout(420_000);
            const viewport = getViewport(testInfo);
            await setupDashboardMockReport(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await selectOneYearPreset(page);
                await freezeAnimations(page);
                // Asserted on the overview, which holds the chart and the KPIs, before leaving it
                await expectDashboardReportLoaded(page);

                await page.getByTestId('dashboard-tab-posizioni').click();
                await expect(page.getByTestId('dashboard-positions-tab')).toBeVisible({timeout: 5_000});
                // Each variant is shot once setPositionsView() has its content root on screen: the
                // holdings table or treemap, the contribution table or the performance chart.
                await screenshotPositionsVariants(page, viewport, lang, theme, 'dashboard', ['positions-holdings-table', 'positions-holdings-map', 'positions-performance-table', 'positions-performance-map']);
            });
        });

        test('dashboard fifo lots panel - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // Deliberately NOT using setupDashboardMockReport here: that fixture is a static,
            // pre-captured snapshot whose holdings[].asset_id values don't reliably correspond
            // to real FIFO lots in a freshly-populated test DB. The other dashboard tests only
            // show aggregate data (growth/allocation), so the mock's staleness doesn't matter
            // there — but "analyze lots" drills into one specific real asset, so we need the
            // live (unmocked) report, exactly like the broker detail equivalent test does.

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                // One pass, and a second one only when the app sent the page to the login screen while the analysis loaded —
                // once seen during a capture. Where the pass ended is read with a retrying poll on «the analysis has drawn,
                // or the login page is up, or the analysis failed»; instant probes used to decide it (`isVisible({timeout})`
                // answers about this instant), so a slow load read as absent and spent the retry in silence.
                for (let attempt = 1; ; attempt++) {
                    await page.goto('/dashboard');
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await selectMaxDateRange(page);
                    await freezeAnimations(page);

                    await page.getByTestId('dashboard-tab-posizioni').click();
                    await expect(page.getByTestId('dashboard-positions-tab')).toBeVisible({timeout: 5_000});
                    await setPositionsView(page, 'holdings', 'table');

                    // Target "Apple Inc." specifically instead of `.first()` (highest
                    // current value). Holdings sort by value desc (ExposureTable.svelte),
                    // which currently puts "RE Loan Milano" first — but that asset has
                    // exactly ONE PriceHistory row ever (see populate_mock_data.py
                    // populate_price_history() loan_price_points), so its WAC/Market
                    // chart renders empty. Apple has the richest lot history in the mock
                    // dataset (buys across 3 brokers/currencies + a partial sell +
                    // dividend + 3-year price history) — a proper FIFO/WAC demo.
                    const positionsPanel = page.getByTestId('positions-panel');
                    const appleRow = positionsPanel.locator('tr[data-row-id]').filter({hasText: 'Apple'}).first();
                    await clickRowAction(page, appleRow, 'analyze-lots');

                    const panel = page.getByTestId('lots-analysis-panel');
                    let outcome = 'loading';
                    await expect
                        .poll(
                            async () => {
                                if (await page.getByTestId('login-page').isVisible()) return (outcome = 'login');
                                if (await panel.getByTestId('lots-analysis-panel-error').isVisible()) return (outcome = 'error');
                                const drawn = (await panel.isVisible()) && !(await panel.getByTestId('lots-analysis-panel-loading').isVisible()) && (await panel.getByTestId('lot-wac-price-chart').isVisible()) && (await panel.getByTestId('lot-gantt-chart').isVisible());
                                return (outcome = drawn ? 'panel' : 'loading');
                            },
                            {message: 'the lots analysis of Apple neither drew nor ended on the login page', timeout: 45_000},
                        )
                        .not.toBe('loading');
                    if (outcome === 'error') throw new Error(`Dashboard FIFO lots panel: the analysis failed — ${await panel.getByTestId('lots-analysis-panel-error').innerText()}`);
                    if (outcome === 'login') {
                        if (attempt === 2) throw new Error('Dashboard FIFO lots panel redirected to login page during capture.');
                        await login(page, TEST_ADMIN);
                        continue;
                    }

                    await captureLotsAnalysisScreenshots(page, viewport, lang, theme, 'dashboard');

                    await page.getByTestId('lots-analysis-panel-close').click();
                    await expect(panel).toBeHidden({timeout: 5_000});
                    break;
                }
            });
        });
        test('dashboard transactions tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await setupDashboardMockReport(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await selectOneYearPreset(page);
                await freezeAnimations(page);
                // Asserted on the overview, which holds the chart and the KPIs, before leaving it
                await expectDashboardReportLoaded(page);

                await page.getByTestId('dashboard-tab-transazioni').click();
                const transactionsTab = page.getByTestId('dashboard-transactions-tab');
                await expect(transactionsTab).toBeVisible({timeout: 5_000});
                // This tab lists the gallery DB's own transactions (live, not the snapshot)
                await expect(transactionsTab.getByTestId('tx-table').locator('tbody tr[data-row-id]'), 'TEST_ADMIN has no transaction in the last year — check populate_mock_data.py').not.toHaveCount(0, {timeout: 15_000});
                // Linked-pair partners and event tooltips load after the rows and publish no state
                // of their own (the tab's txLoading is not exposed), so this wait stays for now.
                await page.waitForTimeout(500);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'transactions-tab');
            });
        });

        test('dashboard empty state - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // Switch from TEST_ADMIN (beforeEach) to the empty user without the UI logout: on
            // mobile its button sits in the off-canvas drawer, and openMobileMenu() opens it only
            // when the burger is already visible — right after login() it often is not yet.
            // page.request shares this context's cookie jar, so the server logout plus the cookie
            // purge leave no session behind; login() then starts from a full page load, where the
            // in-memory auth store re-asks /auth/me and keeps nothing of the admin.
            const logoutResponse = await page.request.post('/api/v1/auth/logout');
            expect(logoutResponse.ok()).toBeTruthy();
            await page.context().clearCookies();
            expect((await page.request.get('/api/v1/auth/me')).status(), 'a session survived the logout').toBe(401);
            await login(page, TEST_EMPTY);
            const meResponse = await page.request.get('/api/v1/auth/me');
            expect(meResponse.ok()).toBeTruthy();
            expect(((await meResponse.json()) as {user?: {username?: string}}).user?.username, 'the dashboard below must be the empty user').toBe(TEST_EMPTY.username);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                // Prove the empty dashboard is the one on screen. The empty user owns no broker,
                // so the page asks for no report and settles with no history — and with no history
                // GrowthChart disables its % toggle, which the admin's populated dashboard does not.
                await waitForSettled(page.getByTestId('dashboard-page'));
                await expect(page.getByTestId('growth-toggle-pct')).toBeDisabled({timeout: 5_000});
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'empty-state');
            });
        });

        test('dashboard data-quality banner (mocked issues) - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            // The populated DB produces no data-quality issues deterministically, so inject
            // two synthetic ones into the served snapshot (same helper as the other dashboard
            // shots): one warning with CTA + one info row. Only `issues` is written —
            // data_quality_status stays the snapshot's own: the backend derives it from the
            // other fields (a computed field it rejects as input), never from the issues.
            await setupDashboardMockReport(page, (report) => {
                report.summary.data_quality = {
                    ...report.summary.data_quality,
                    issues: [
                        {
                            domain: 'portfolio',
                            code: 'STALE_PRICE',
                            severity: 'warning',
                            message_i18n_key: 'dataQuality.stalePrice',
                            message_params: {count: 2},
                            count: 2,
                            affected_asset_ids: [1, 2],
                            affected_asset_names: ['Apple Inc.', 'Microsoft Corp.'],
                            cta_action: 'navigate_asset',
                            cta_target: '1',
                            group_key: 'stale_price',
                        },
                        {
                            domain: 'portfolio',
                            code: 'MISSING_FX_MARKET',
                            severity: 'info',
                            message_i18n_key: 'dataQuality.missingFx',
                            message_params: {count: 1},
                            count: 1,
                            affected_fx_pairs: ['USD-CHF'],
                            cta_action: 'add_fx_pair',
                            cta_target: 'USD-CHF',
                            group_key: 'missing_fx_market',
                        },
                    ],
                };
            });

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);
                await expectDashboardReportLoaded(page);

                // Collapsed on every load. A toggle: open it only when closed, then assert the end
                // state and the two injected issues the shot is for.
                const bannerToggle = page.getByTestId('data-quality-toggle');
                await expect(bannerToggle).toBeVisible({timeout: 10_000});
                if ((await bannerToggle.getAttribute('aria-expanded')) !== 'true') await bannerToggle.click();
                await expect(bannerToggle).toHaveAttribute('aria-expanded', 'true');
                await expect(page.getByTestId('data-quality-issue-STALE_PRICE')).toBeVisible();
                await expect(page.getByTestId('data-quality-issue-MISSING_FX_MARKET')).toBeVisible();
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'data-quality-banner');
            });
        });

        test('dashboard data-quality banner missing exchange rates (mocked issue) - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // Shown, never pressed: Sync rates asks the exchange-rate provider and writes the rates. The guard makes a
            // stray press fail closed, and the end of the test proves none happened.
            const guard = await guardReadOnly(page);

            // The populated DB holds every rate the dashboard asks for, so the backend never reports one missing: the
            // issue is written into the served snapshot, with the helper and the flow of the shot above, whose content
            // stays as it is. Its shape is the one portfolio_engine.py builds for configured pairs that have a provider:
            // the pairs in its sorted order, the first one the target of Sync rates, and the dates they lack — three
            // days inside the default range, before the pairs' first stored rate (a date is missing only when no rate
            // exists on or before it). Only `issues` is written, as above.
            const daysAgo = (days: number) => getLocalDateString(new Date(Date.now() - days * 24 * 60 * 60 * 1000));
            await setupDashboardMockReport(page, (report) => {
                report.summary.data_quality = {
                    ...report.summary.data_quality,
                    issues: [
                        {
                            domain: 'portfolio',
                            code: 'MISSING_FX_RATES',
                            severity: 'warning',
                            message_i18n_key: 'dataQuality.missingFxRates',
                            message_params: {count: 2, date_from: daysAgo(88), date_to: daysAgo(86), dates_count: 3},
                            count: 2,
                            affected_fx_pairs: ['EUR-GBP', 'EUR-USD'],
                            cta_action: 'sync_fx_pair',
                            cta_target: 'EUR-GBP',
                            group_key: 'missing_fx_rates',
                        },
                    ],
                };
            });

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);
                await expectDashboardReportLoaded(page);

                // Collapsed on every load. A toggle: open it only when closed, then assert the end state, the issue the
                // shot is for and its Sync rates button.
                const bannerToggle = page.getByTestId('data-quality-toggle');
                await expect(bannerToggle).toBeVisible({timeout: 10_000});
                if ((await bannerToggle.getAttribute('aria-expanded')) !== 'true') await bannerToggle.click();
                await expect(bannerToggle).toHaveAttribute('aria-expanded', 'true');
                const issue = page.getByTestId('data-quality-issue-MISSING_FX_RATES');
                await expect(issue).toBeVisible();
                await expect(issue).toHaveAttribute('data-severity', 'warning');
                const syncRates = issue.getByTestId('data-quality-cta-MISSING_FX_RATES');
                await expect(syncRates).toBeVisible();
                await expect(syncRates).toBeEnabled();
                await freezeAnimations(page);
                await parkPointer(page);
                await expectNoToast(page);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'data-quality-sync-rates');
            });
            expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started').toEqual([]);
        });
    });

    /**
     * The sidebar's connection-security line (plan 36), open on «Connection: local network» with its reason and the How to
     * connect securely link: security/connection-indicator, on user/connection-security.md.
     *
     * A local-network verdict needs a host the browser classifies as one, so the page is opened under GALLERY_LAN_NAME,
     * which this file's launch options map onto the loopback. Cookies are per host, so the gallery's admin signs in twice:
     * on the baseURL first, with the gallery's own login() — where the reads the gallery's routes make in Node go — then
     * through the login form served under the LAN name: the session the page runs on. The Dashboard behind is the
     * gallery's: the snapshot report on its 1Y range, settled as the Dashboard shots settle it.
     *
     * Offline as every shot: the outer beforeEach's routes match paths and third-party hosts, never the baseURL's origin,
     * so they hold under the LAN name; the two listings hideGalleryTempData filters in Node are read through the baseURL
     * (keepTempDataHiddenUnder), and the outer afterEach gives the verdict (expectGalleryOffline).
     */
    test.describe('Security', () => {
        /** The runner's baseURL origin: the lane serves plain HTTP, and the shot is that of an http: page. */
        function laneOrigin(baseURL: string | undefined): string {
            if (!baseURL) throw new Error('the Security shot needs the runner-provided baseURL');
            const url = new URL(baseURL);
            expect(url.protocol, 'precondition: the lane serves plain HTTP — over HTTPS the line would read secure').toBe('http:');
            return url.origin;
        }

        /** The lane's origin under another name: the baseURL's protocol and port. */
        function originUnder(origin: string, hostname: string): string {
            const url = new URL(origin);
            url.hostname = hostname;
            return url.origin;
        }

        /** The user page the details link, at its root, in the language of the UI (connectionSecurityDocsUrl). */
        function connectionDocsHref(lang: Language): string {
            return `/mkdocs/${lang === 'en' ? '' : `${lang}/`}user/connection-security/`;
        }

        /**
         * Sign `user` in through the login form served under `origin`, which has no session of its own yet: login() would
         * start over on the baseURL, whose cookie belongs to another host. Ends on the app shell, still under `origin`.
         */
        async function signInThroughFormUnder(page: Page, origin: string, user: {username: string; password: string}): Promise<void> {
            await page.goto(`${origin}/`);
            await expect(page.getByTestId('login-page'), `${origin} has no session of its own yet: its login form shows`).toBeVisible({timeout: 30_000});
            await expect(page.getByTestId('login-form')).toBeVisible();
            await page.getByTestId('login-username').fill(user.username);
            await page.getByTestId('login-password').fill(user.password);
            await page.getByTestId('login-submit').click();
            await expect(page.getByTestId('login-page'), 'the sign-in went through').toBeHidden({timeout: 30_000});
            await expect(page.getByTestId('app-shell'), 'the app shell is up after the post-login routing').toBeVisible({timeout: 30_000});
            expect(new URL(page.url()).origin, `precondition: the app stayed under ${origin}`).toBe(origin);
        }

        /**
         * Positive control: the outer beforeEach's offline guard matches paths, not the baseURL's origin, so it holds under the
         * page's own name — a provider catalogue read made from the page is answered from the guard's fixture, never by the
         * backend, which would ask ECB and SNB.
         */
        async function expectGuardHoldsOnPage(page: Page): Promise<void> {
            const guard = galleryOfflineGuard(page);
            const reads = guard.catalogueReads;
            const status = await page.evaluate(async () => (await fetch('/api/v1/fx/providers')).status);
            expect(status, 'the provider catalogue read was answered').toBe(200);
            expect(guard.catalogueReads, `the offline guard did not answer a provider catalogue read made under ${new URL(page.url()).origin}`).toBeGreaterThan(reads);
        }

        /**
         * Rest the pointer on the open details' own right padding: on the indicator, whose pointer holds the details' 30 s
         * countdown (ConnectionSecurityIndicator, plan 48 C3), and on nothing that reacts to it — the toggle has a hover
         * background, the link a hover colour, the reason a title. parkPointer's right edge would leave the indicator and
         * start the countdown before the shot. Ends on the spot being the details themselves, and on no tooltip shown.
         */
        async function restPointerOnDetails(page: Page, details: Locator): Promise<void> {
            const box = await details.boundingBox();
            if (!box) throw new Error('the details are not on screen');
            const spot = {x: Math.floor(box.x + box.width) - 4, y: Math.round(box.y + box.height / 2)};
            await page.mouse.move(spot.x, spot.y);
            const onDetails = await details.evaluate((element, {x, y}) => document.elementFromPoint(x, y) === element, spot);
            expect(onDetails, 'the pointer rests on the details themselves, not on the reason, the link or anything over them').toBe(true);
            await expect(page.getByTestId('tooltip-content'), 'a tooltip lies over the shot').toHaveCount(0);
        }

        test('connection indicator on a local network - all languages and themes', async ({page, baseURL}, testInfo) => {
            const viewport = getViewport(testInfo);
            const lane = laneOrigin(baseURL);
            const lan = originUnder(lane, GALLERY_LAN_NAME);
            const header = page.getByTestId('app-header');
            const line = page.getByTestId('connection-security');
            const toggle = line.getByTestId('connection-security-toggle');
            const details = line.getByTestId('connection-security-details');
            const link = details.getByTestId('connection-security-docs-link');

            await setupDashboardMockReport(page);
            await login(page, TEST_ADMIN);
            await keepTempDataHiddenUnder(page, lan, lane);
            await signInThroughFormUnder(page, lan, TEST_ADMIN);
            await expectGuardHoldsOnPage(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                // One full load per combination, in its language and theme: the line asks the server once per load, and
                // every chart behind draws once.
                await page.goto(`${lan}/dashboard`);
                await selectOneYearPreset(page);
                await freezeAnimations(page);
                await expectDashboardReportLoaded(page);
                await expect(page.locator('html'), 'the language survived the load').toHaveAttribute('lang', lang);
                await expect(page.locator('html')).toHaveAttribute('data-i18n-ready', 'true');
                await expect(page.locator('html'), 'the theme survived the load').toHaveClass(new RegExp(`\\b${theme}\\b`));

                // The verdict, once the server has answered: a LAN name, and a client the server does not see as public.
                await expect(line, 'the server answered the line (GET /api/v1/system/connection)').toHaveAttribute('data-server-checked', 'true', {timeout: 15_000});
                await expect(line).toHaveAttribute('data-level', 'local');
                await expect(line).toHaveAttribute('data-reason', 'lan');

                // On a phone the sidebar is the drawer: the burger opens it.
                if (viewport === 'mobile') {
                    await expect(header, 'the drawer is closed after the load').toHaveAttribute('data-sidebar-open', 'false');
                    await page.getByTestId('mobile-menu-toggle').click();
                    await expect(header, 'the burger opened the drawer').toHaveAttribute('data-sidebar-open', 'true');
                }
                await expect(page.getByTestId('sidebar-user-avatar'), "the page runs on the gallery's admin").toContainText(TEST_ADMIN.username);
                // Only an expanded sidebar draws the label: a collapsed one shows the shield alone.
                await expect(line.getByTestId('connection-security-label'), 'the sidebar is expanded').toBeVisible();

                // The details: closed on every load, opened by a click.
                await expect(toggle, 'the details start closed').toHaveAttribute('aria-expanded', 'false');
                await toggle.click();
                await expect(toggle).toHaveAttribute('aria-expanded', 'true');
                await expect(details.getByTestId('connection-security-reason')).toBeVisible();
                await expect(link, 'the link opens the user page in the language of the UI').toHaveAttribute('href', connectionDocsHref(lang));
                await expect(details.getByTestId('connection-security-admin-warning'), 'no cookie line: the page is plain HTTP').toHaveCount(0);

                // Settled, then in frame: the KPI cards' count-up and the growth chart behind, every image, nothing moving.
                await textStill(page.getByTestId('kpi-row'), 'the KPI cards');
                await waitForChart(page.getByTestId('growth-chart'));
                await canvasStill(page.getByTestId('growth-chart'), 'the growth chart');
                await imagesSettled(page.getByTestId('app-shell'));
                await waitForMotionSettled(page.getByTestId('app-shell'), 'the page');
                // The pointer stays on the indicator, so the details' countdown never starts before the shot.
                await restPointerOnDetails(page, details);
                await expectNoToast(page);
                await expect(line, 'the whole line is on screen: the level, the reason and the link').toBeInViewport({ratio: 1});
                await expectUncovered(link, 'the How to connect securely link');
                // The pointer stays on the details (restPointerOnDetails): parked anywhere else, it would start their countdown.
                await screenshot(page, viewport, lang, theme, 'security', 'connection-indicator', {keepPointer: true});
                // Nothing reopens the details without a click: open now, so open in the picture.
                await expect(toggle, 'the details stayed open through the shot').toHaveAttribute('aria-expanded', 'true');

                // The next combination's language and theme are set from the header, which the open drawer covers: it closes
                // as a user closes it, by picking the page it shows.
                if (viewport === 'mobile') {
                    await page.getByTestId('nav-dashboard').click();
                    await expect(header, 'the drawer closed').toHaveAttribute('data-sidebar-open', 'false');
                }
            });
        });
    });

    test.describe('Settings', () => {
        /**
         * Open the admin tab of Settings and return it loaded: the tab selected (`aria-selected`) and its settings in — the tab
         * says so with `data-busy` (GlobalSettingsTab: loading or saving). Global Settings is a member of «Administration»
         * (decision P13 b): `openSettingsTab` opens the group, then the tab in its second bar, an administrator's — every
         * caller signs TEST_ADMIN in. The tests used to wait for its spinner to leave and swallow the timeout
         * (`.catch(() => {})`), then 200 ms (`waitForNetworkSettled`) and 500 ms more.
         */
        async function openGlobalSettings(page: Page): Promise<Locator> {
            await openSettingsTab(page, 'admin');
            const tab = page.getByTestId('settings-tab-admin');
            await expect(tab).toHaveAttribute('aria-selected', 'true');
            const globalSettings = page.getByTestId('global-settings-tab');
            await expect(globalSettings).toBeVisible({timeout: 10_000});
            await waitForSettled(globalSettings, 15_000);
            return globalSettings;
        }

        /**
         * Unlock the admin settings: every load opens them locked (GlobalSettingsTab, `isLocked`), and the lock toggle is drawn
         * for the admin. The toggle publishes no state of its own; the scheduler's Configure button, disabled while they are
         * locked, does — on All, where every load opens. Clicked only when locked, the end state asserted. A miss used to leave
         * the toggle unclicked in silence, and the scheduler shot clicking a disabled button (plan 56, class C).
         */
        async function unlockGlobalSettings(page: Page): Promise<void> {
            const lockToggle = page.getByTestId('settings-lock-toggle');
            const schedulerConfigure = page.getByTestId('scheduler-config-btn');
            await expect(lockToggle, 'the admin may edit the global settings').toBeVisible({timeout: 10_000});
            await expect(schedulerConfigure).toBeVisible({timeout: 10_000});
            if (await schedulerConfigure.isDisabled()) await lockToggle.click();
            await expect(schedulerConfigure, 'the global settings are unlocked').toBeEnabled();
        }

        /**
         * Narrow the admin settings to the Memory category through the control each layout offers (GlobalSettingsTab): the
         * sidebar on a desktop, the category dropdown on a phone — chooseOnboardingCategory's pattern (galleryOnboarding.ts). A
         * one-second probe used to decide: the sidebar on a desktop when it was drawn in time, nothing on a phone. Neither control
         * publishes the choice, so the end state is read on what the category shows: the cache panel (Memory and All) on, and the
         * scheduler's rows (Sync and All) gone.
         */
        async function chooseMemoryCategory(page: Page, viewport: 'desktop' | 'mobile'): Promise<void> {
            if (viewport === 'mobile') {
                const menu = page.getByTestId('global-settings-mobile-category-menu');
                await page.getByTestId('global-settings-mobile-category-trigger').click();
                await expect(menu).toBeVisible();
                await menu.getByTestId('global-settings-mobile-category-memory').click();
                await expect(menu, 'the dropdown closes on the choice').toHaveCount(0);
            } else {
                const memory = page.getByTestId('global-settings-category-memory');
                await expect(memory).toBeVisible();
                await memory.click();
            }
            await expect(page.getByTestId('cache-panel'), 'the Memory category shows the cache panel').toBeVisible({timeout: 10_000});
            await expect(page.getByTestId('scheduler-config-row'), 'the Memory category hides the scheduler').toHaveCount(0);
        }

        test('user preferences - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                // Straight to the tab: the page honours ?tab= (settings/+page.svelte), as the onboarding replay below opens it. It
                // used to open on Profile and click Preferences only when an instant probe found the tab already drawn — under
                // load it did not, and the shot was Profile's, or Preferences still loading.
                await navigateTo(page, '/settings?tab=preferences');
                await expect(page.getByTestId('settings-tab-preferences')).toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
                // The preferences arrive after the tab is drawn: the layout says when they are in (data-busy).
                await waitForSettled(page.getByTestId('settings-layout'), 15_000);
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'settings', 'user-preferences');
            });
        });

        test('global settings (admin) - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                await freezeAnimations(page);
                await openGlobalSettings(page);
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole page, on a screen as tall as it.
                if (viewport === 'desktop') await extendScreenToBlock(page, page.locator(PAGE_BLOCK), `desktop/${lang}/${theme}/settings/global-settings`);
                await screenshot(page, viewport, lang, theme, 'settings', 'global-settings');
                await restoreTallScreen(page);
            });
        });

        test('email (admin) - all languages and themes', async ({page}, testInfo) => {
            // The administrators' Email tab where email works: the lane has no SMTP server, so the status read is answered,
            // before any navigation, by galleryEmail.ts — ready, 47 of 50 emails left, no notice. The test email is never pressed.
            const viewport = getViewport(testInfo);
            await serveGalleryEmailStatus(page);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                // Straight to the tab, as the preferences shots open theirs: the page honours ?tab= (settings/+page.svelte).
                await navigateTo(page, '/settings?tab=email');
                await expect(page.getByTestId('settings-tab-email')).toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
                // The status arrives after the tab is drawn: the panel says when it is in (data-busy).
                await waitForSettled(page.getByTestId('email-tab'), 15_000);
                await expectGalleryEmailStatus(page);
                await freezeAnimations(page);
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole card, as the profile shot frames it.
                if (viewport === 'desktop') await extendScreenToBlock(page, page.getByTestId('settings-page'), `desktop/${lang}/${theme}/settings/email`);
                await screenshot(page, viewport, lang, theme, 'settings', 'email');
                await restoreTallScreen(page);
            });
        });

        test('plugins - all languages and themes', async ({page}, testInfo) => {
            // Settings › Plugins (workstream X, CP11; G's conditions, 2026-10-16): the settings the installed plugins ask for —
            // justETF's and Borsa Italiana's personal search preferences, on their default «All». Nothing is mocked: the lane's
            // own catalogue. A member's view (TEST_USER), the one the user manual describes: the tab bar without the
            // administrators' tabs.
            const viewport = getViewport(testInfo);
            await login(page, TEST_USER);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                // Straight to the tab, as the email shots open theirs: the page honours ?tab= (settings/+page.svelte).
                await navigateTo(page, '/settings?tab=plugins');
                await expect(page.getByTestId('settings-tab-plugins')).toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
                // The catalogue arrives after the tab is drawn: the tab says when it is in (data-busy).
                await waitForSettled(page.getByTestId('plugin-settings-tab'), 15_000);
                await expect(page.getByTestId('plugin-settings-load-error')).toHaveCount(0);
                await expect(page.getByTestId('plugin-settings-empty')).toHaveCount(0);
                await expect(page.getByTestId('plugin-settings-family').first()).toBeVisible();
                // No secret saved, or set by a variable of the server: a leftover of the E2E, or a variable of the shell, would
                // give a shot CI cannot reproduce.
                await expect(page.locator('[data-testid="plugin-setting-secret-state"][data-state="set"], [data-testid="plugin-setting-secret-state"][data-state="env"]')).toHaveCount(0);
                await freezeAnimations(page);
                if (viewport === 'desktop') {
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole card, as the email shot
                    // frames it; past ~2500 px (many plugins), the first family only.
                    const settingsPage = page.getByTestId('settings-page');
                    const bottom = await settingsPage.evaluate((element) => element.getBoundingClientRect().bottom);
                    const block = bottom > 2500 ? page.getByTestId('plugin-settings-family').first() : settingsPage;
                    await extendScreenToBlock(page, block, `desktop/${lang}/${theme}/settings/plugins`);
                }
                // MOBILE — the first screen, as the email shot.
                await screenshot(page, viewport, lang, theme, 'settings', 'plugins');
                await restoreTallScreen(page);
            });
        });

        test('backup ready (admin) - all languages and themes', async ({page}, testInfo) => {
            // The administrators' Backup tab with a finished backup on offer: the lane never runs a real backup, so the job the
            // card follows is stored and answered, before any navigation, by galleryBackup.ts — done, 46.0 MB, no warning.
            // Neither the download nor the delete is ever pressed.
            const viewport = getViewport(testInfo);
            await serveGalleryBackupJob(page);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                // Straight to the tab, as the email shots open theirs: the page honours ?tab= (settings/+page.svelte).
                await navigateTo(page, '/settings?tab=backup');
                await expect(page.getByTestId('settings-tab-backup')).toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
                // The job is read after the card is drawn: the card says when it is in (data-busy).
                await waitForSettled(page.getByTestId('backup-download-card'), 15_000);
                await expectGalleryBackupReady(page);
                await freezeAnimations(page);
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole card, as the email shot frames it.
                if (viewport === 'desktop') await extendScreenToBlock(page, page.getByTestId('settings-page'), `desktop/${lang}/${theme}/settings/backup-ready`);
                await screenshot(page, viewport, lang, theme, 'settings', 'backup-ready');
                await restoreTallScreen(page);
            });
        });

        test('about tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await waitForNetworkSettled(page);
                await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                await freezeAnimations(page);
                await page.getByTestId('settings-tab-about').click();
                // Wait for about tab to render and system info to load
                await page.getByTestId('about-tab').waitFor({state: 'visible', timeout: 10_000});
                await page
                    .locator('[data-testid="about-tab"] [role="status"]')
                    .waitFor({state: 'hidden', timeout: 15_000})
                    .catch(() => {});
                // Also wait for version string to replace placeholder "..."
                await page.getByTestId('about-version').filter({hasNotText: '...'}).waitFor({state: 'visible', timeout: 10_000});
                await waitForNetworkSettled(page);
                await page.waitForTimeout(500);
                await screenshot(page, viewport, lang, theme, 'settings', 'about');
            });
        });

        test('password change modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                await freezeAnimations(page);
                // Click change password button
                await page.getByTestId('change-password-button').click();
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, theme, 'settings', 'password-modal');
                // Close modal
                await page.keyboard.press('Escape');
                await page.waitForTimeout(100);
            });
        });

        test('profile tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                await freezeAnimations(page);
                // By its test id, on both viewports. The tab's label is translated, and on a phone the TabBar shows its icon only
                // (hideLabelOnMobile): the old filter on the English word found the tab on the English desktop alone, and every
                // other combination skipped the shot in silence — no phone and no it/fr/es desktop image was ever made.
                const profileTab = page.getByTestId('settings-tab-profile');
                await expect(profileTab).toBeVisible({timeout: 10_000});
                await profileTab.click();
                await expect(profileTab).toHaveAttribute('aria-selected', 'true');
                const profile = page.getByTestId('profile-tab');
                await expect(profile).toBeVisible();
                await expect(profile).toHaveAttribute('data-busy', 'false');
                // The avatar comes with the user's settings, after the tab is drawn (ProfileTab's onMount): the gallery's admin
                // has one — the sidebar shows it — so its picture, loaded, is what says the tab is complete.
                const avatar = profile.getByTestId('profile-avatar').locator('img');
                await expect(avatar, "the admin's avatar is not on the Profile tab").toBeVisible({timeout: 10_000});
                await expect.poll(() => avatar.evaluate((img) => (img as HTMLImageElement).complete && (img as HTMLImageElement).naturalWidth > 0), {message: "the admin's avatar never loaded", timeout: 10_000}).toBe(true);
                await parkPointer(page);
                await waitForMotionSettled(profile, 'the Profile tab');
                await expectNoToast(page);
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole card, its tab bar and the
                // profile down to its rounded bottom edge — `profile-tab` alone stops inside the card's padding.
                if (viewport === 'desktop') await extendScreenToBlock(page, page.getByTestId('settings-page'), `desktop/${lang}/${theme}/settings/profile`);
                await screenshot(page, viewport, lang, theme, 'settings', 'profile');
                await restoreTallScreen(page);
            });
        });

        // The Users tab (lot A6b, administrators only), one account's actions open. Both lists are fixed bodies, answered on
        // this page only: the lane's accounts and invitations change with every test that registers its own (the gallery's
        // too, registerGalleryAccount in galleryReportSets.ts), so the real lists would draw another picture on every run.
        // The admin's row keeps the admin's real account, read from
        // /auth/me: the tab tells the signed-in account's row («You», no actions) by its id. Another account is open, so the
        // picture shows what an administrator can do to it. Every date is drawn absolute (formatDateTime): no clock is set.
        test('users - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            // A read, nothing written: the signed-in admin, through the page's own session (its cookies, the config's baseURL).
            const admin = schemas.AuthMeResponse.parse(await (await page.request.get('/api/v1/auth/me')).json()).user;
            // 5 places taken: the 3 active accounts and the 2 open invitations. `/billing` is a path of the app, never opened:
            // it draws the «Manage subscription» link.
            const usage = {used: 5, max_users: 10, billing_url: '/billing'};
            const accountRows = [
                {id: admin.id, username: admin.username, email: admin.email, is_active: true, is_superuser: true, created_at: '2026-01-12T09:30:00Z', protected: false},
                {id: 9101, username: 'anna.rossi', email: 'anna.rossi@example.com', is_active: true, is_superuser: true, created_at: '2026-02-03T18:05:00Z', protected: false},
                {id: 9102, username: 'marco', email: 'marco@example.com', is_active: true, is_superuser: false, created_at: '2026-03-21T07:45:00Z', protected: false},
                {id: 9103, username: 'giulia.b', email: 'giulia.b@example.com', is_active: false, is_superuser: false, created_at: '2026-04-09T12:00:00Z', protected: false},
            ];
            const inviteRows = [
                {id: 7201, grants_admin: false, email: 'luca@example.com', created_at: '2026-10-10T08:15:00Z', expires_at: '2026-10-17T08:15:00Z', created_by_user_id: admin.id},
                {id: 7202, grants_admin: true, email: null, created_at: '2026-10-12T16:40:00Z', expires_at: '2026-10-19T16:40:00Z', created_by_user_id: admin.id},
            ];
            // Checked here against the generated schemas the client validates with: a body Zodios refuses leaves the tab empty,
            // without an error — this fails now, with Zod's message.
            const accounts = schemas.AdminUserListResponse.parse({items: accountRows, usage});
            const invites = schemas.InviteListResponse.parse({items: inviteRows, usage});
            // Before the tab's first load (the sign-in lands on the dashboard, which asks neither path). Each answers its own
            // path for GET only; anything else falls back — to the gallery's guard and filters, then the backend.
            await page.route(
                (url) => url.pathname === '/api/v1/users',
                (route) => (route.request().method() === 'GET' ? route.fulfill({json: accounts}) : route.fallback()),
            );
            await page.route(
                (url) => url.pathname === '/api/v1/users/invites',
                (route) => (route.request().method() === 'GET' ? route.fulfill({json: invites}) : route.fallback()),
            );

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                // Straight to the tab, as for Preferences: the page applies ?tab=users once the admin's tab is drawn.
                await navigateTo(page, '/settings?tab=users');
                await expect(page.getByTestId('settings-tab-users')).toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
                // Both lists are in: the tab says so with data-busy (UsersTab, `load`).
                const usersTab = page.getByTestId('users-tab');
                await waitForSettled(usersTab, 15_000);
                // The fixed lists, not the lane's: a route that missed would leave the real ones on screen, and the shot green.
                await expect(usersTab.getByTestId('users-row'), 'the Users tab does not show the fixed accounts').toHaveCount(accountRows.length, {timeout: 5_000});
                await expect(usersTab.getByTestId('users-invite-row'), 'the Users tab does not show the fixed invitations').toHaveCount(inviteRows.length, {timeout: 5_000});
                await freezeAnimations(page);
                // One account open, so the picture shows its actions. Every load draws the rows closed (UserRow, `expanded`).
                const marcoRow = usersTab.locator('[data-testid="users-row"][data-username="marco"]');
                const toggle = marcoRow.getByTestId('users-row-toggle');
                await expect(toggle, "marco's row starts closed").toHaveAttribute('aria-expanded', 'false', {timeout: 5_000});
                await toggle.click();
                await expect(toggle, "marco's actions are open").toHaveAttribute('aria-expanded', 'true', {timeout: 5_000});
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole card, as for the Profile tab.
                // PHONE — marco's row framed from its top (frameTarget), so the actions it opened are whole on the screen (G-15).
                if (viewport === 'desktop') await extendScreenToBlock(page, page.getByTestId('settings-page'), `desktop/${lang}/${theme}/settings/users`);
                else await frameTarget(page, marcoRow, `${viewport}/${lang}/${theme}/settings/users`);
                await screenshot(page, viewport, lang, theme, 'settings', 'users');
                await restoreTallScreen(page);
            });
        });

        test('scheduler config modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/settings');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    await openGlobalSettings(page);
                    // Settings start locked by default — unlock before interacting with scheduler-config-btn (disabled while locked)
                    await unlockGlobalSettings(page);

                    // Click the configure button to open SchedulerConfigModal: drawn on All, where every load opens
                    const configBtn = page.getByTestId('scheduler-config-btn');
                    // The dialog freezes the page behind it where the button's scroll left it. A bare scroll into view, on a page
                    // not settled yet and from wherever the clicks above had left it, centred the button in one run and not in the
                    // other: the page 59 px apart behind the same dialog (plan 56). From the top of the settled page instead.
                    await bringIntoViewFromTop(page, configBtn, `${viewport}/${lang}/${theme}/settings/scheduler-config`);
                    await configBtn.click();
                    const configModal = page.getByTestId('scheduler-config-modal');
                    await expect(configModal).toBeVisible({timeout: 5_000});
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'settings', 'scheduler-config');
                    // The next combination starts from a new load
                    await page.keyboard.press('Escape');
                }
            }
        });

        test('scheduler log modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/settings');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    await openGlobalSettings(page);

                    // Click the scheduler status row to open SchedulerLogModal: drawn on All, where every load opens
                    const statusRow = page.getByTestId('scheduler-status-row');
                    await expect(statusRow).toBeVisible({timeout: 10_000});
                    // The dialog freezes the page behind it where the row's scroll left it: brought into view from the top of the
                    // settled page, as the configure button is — a bare scroll into view jumped the same way (plan 56).
                    await bringIntoViewFromTop(page, statusRow, `${viewport}/${lang}/${theme}/settings/scheduler-log`);
                    await statusRow.click();
                    const logModal = page.getByTestId('scheduler-log-modal');
                    await expect(logModal).toBeVisible({timeout: 5_000});
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'settings', 'scheduler-log');
                    // The next combination starts from a new load
                    await page.keyboard.press('Escape');
                }
            }
        });

        // Must stay language-neutral: the modal searches the chapters in the UI's language, so the term is a proper name present in every translated chapter set (CHANGELOG.md, .it, .fr, .es) — an English word like 'Added' finds nothing in it/fr/es.
        const CHANGELOG_SEARCH_TERM = 'Docker';

        test('changelog modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            const isMobile = testInfo.project.name === 'mobile';
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/dashboard');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Sidebar version chip opens the bundled changelog (mobile: inside the burger menu)
                    if (isMobile) {
                        await openMobileMenu(page);
                    }
                    await page.getByTestId('sidebar-version').click();
                    const modal = page.getByTestId('changelog-modal');
                    await expect(modal).toBeVisible({timeout: 8_000});
                    // Chapters render from the bundled CHANGELOG — wait for one to exist
                    await expect(page.locator('[data-testid^="changelog-chapter-"]').first()).toBeVisible({timeout: 8_000});
                    await freezeAnimations(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'settings', 'changelog-modal');

                    // Second shot: search narrows the index, one fold opened by a hit
                    await page.getByTestId('changelog-search').fill(CHANGELOG_SEARCH_TERM);
                    const hits = page.getByTestId('changelog-search-results');
                    await expect(hits).toBeVisible({timeout: 5_000});
                    await hits.locator('[data-testid^="changelog-hit-"]').first().click();
                    await page.waitForTimeout(400); // scroll-into-view after the fold opens
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'settings', 'changelog-modal-search');

                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('cache panel - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/settings');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                    await openGlobalSettings(page);

                    // Unlock as admin so the Clear actions are rendered too
                    await unlockGlobalSettings(page);
                    // Narrowed to the Memory category on both viewports: the cache panel under the upload limit
                    await chooseMemoryCategory(page, viewport);

                    const cachePanel = page.getByTestId('cache-panel');
                    // The cache status is in: Refresh stays disabled while it loads (CachePanel, `loading`). Its sizes are content.
                    await expect(cachePanel.getByTestId('cache-refresh'), 'the cache status has loaded').toBeEnabled({timeout: 15_000});
                    await cachePanel.scrollIntoViewIfNeeded();
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'settings', 'cache-panel');
                    // No re-lock needed: the next combo re-navigates and the tab remounts locked.
                }
            }
        });

        test('about plugin diagnostics - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/settings');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                    await page.getByTestId('settings-tab-about').click();
                    await page.getByTestId('about-tab').waitFor({state: 'visible', timeout: 10_000});
                    await page
                        .locator('[data-testid="about-tab"] [role="status"]')
                        .waitFor({state: 'hidden', timeout: 15_000})
                        .catch(() => {});

                    // Expand the Plugin diagnostics collapsible (4 registries: asset/fx/brim/signals)
                    const diagnostics = page.getByTestId('about-plugin-diagnostics');
                    await expect(diagnostics).toBeVisible({timeout: 8_000});
                    if ((await diagnostics.getAttribute('open')) === null) {
                        await diagnostics.locator('summary').click();
                        await expect(diagnostics).toHaveAttribute('open', '', {timeout: 3_000});
                    }
                    // The Tools panel grows the block once its catalogue is in, so the frame is taken after it, on both viewports. A
                    // scroll taken before raced it: 7 desktop frames of b5_c4_5 held the whole block and 1 did not, and on a phone
                    // two runs of 15/10 landed 92 px apart on a page of the same height (plan 56).
                    await expect(diagnostics.getByTestId('tool-about-panel')).toHaveAttribute('data-state', /^(ready|degraded)$/, {timeout: 15_000});
                    await freezeAnimations(page);
                    if (viewport === 'desktop') {
                        // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the block scrolled into view, on a
                        // screen grown to its end.
                        await diagnostics.scrollIntoViewIfNeeded();
                        await extendScreenToBlock(page, diagnostics, `desktop/${lang}/${theme}/settings/about-plugin-diagnostics`);
                    } else {
                        // PHONE — framed from the top of the page, the block 8 px under the screen's edge, or as near as the page's
                        // end allows (frameTarget): a scroll into view moves from wherever the page stands.
                        await frameTarget(page, diagnostics, `${viewport}/${lang}/${theme}/settings/about-plugin-diagnostics`);
                    }
                    await screenshot(page, viewport, lang, theme, 'settings', 'about-plugin-diagnostics');
                    await restoreTallScreen(page);
                }
            }
        });

        test('about tool diagnostics - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/settings');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await expect(page.getByTestId('settings-page')).toBeVisible({timeout: 10_000});
                    await page.getByTestId('settings-tab-about').click();
                    await expect(page.getByTestId('about-tab')).toBeVisible({timeout: 10_000});
                    // System info and the plugin registries arrive in one wave: the report button is enabled
                    // once it is in, and the Plugin diagnostics block renders with it.
                    await expect(page.getByTestId('about-copy-report')).toBeEnabled({timeout: 15_000});

                    // Both collapsibles are toggles: each is opened only when it is closed. Opening Plugin
                    // diagnostics activates its Tools panel, which reads the tool catalogue.
                    const diagnostics = page.getByTestId('about-plugin-diagnostics');
                    await expect(diagnostics).toBeVisible();
                    if ((await diagnostics.getAttribute('open')) === null) await diagnostics.locator(':scope > summary').click();
                    await expect(diagnostics).toHaveAttribute('open', '');
                    const tools = diagnostics.getByTestId('tool-about-panel');
                    // Real state, no mock: ready, or degraded when the server reports it — never still loading.
                    await expect(tools).toHaveAttribute('data-state', /^(ready|degraded)$/, {timeout: 15_000});
                    await expect(tools.getByTestId('tool-about-entry-pac_allocator')).toBeVisible();

                    // Opening Tool diagnostics reads the snapshot of the API process that answers.
                    const toolDiagnostics = tools.getByTestId('tool-about-diagnostics');
                    if ((await toolDiagnostics.getAttribute('open')) === null) await tools.getByTestId('tool-about-diagnostics-toggle').click();
                    await expect(toolDiagnostics).toHaveAttribute('open', '');
                    const snapshot = toolDiagnostics.getByTestId('tool-diagnostics-panel');
                    await expect(snapshot).toHaveAttribute('data-state', /^(ready|degraded)$/, {timeout: 15_000});
                    const loaded = snapshot.getByTestId('tool-diagnostics-loaded');
                    await expect(loaded.getByTestId('tool-diagnostics-loaded-entry').filter({hasText: 'pac_allocator'})).toBeVisible();
                    await expect(tools).toHaveAttribute('data-busy', 'false');

                    // Bottom edge on the loaded tools: the PAC allocator entry and its version are in the frame on
                    // every viewport, with as much of the panel above them as fits.
                    await loaded.evaluate((el) => el.scrollIntoView({block: 'end'}));
                    await freezeAnimations(page);
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole Tools panel.
                    if (viewport === 'desktop') await extendScreenToBlock(page, tools, `desktop/${lang}/${theme}/settings/about-tool-diagnostics`);
                    await screenshot(page, viewport, lang, theme, 'settings', 'about-tool-diagnostics');
                    await restoreTallScreen(page);
                }
            }
        });

        test('onboarding replay - all languages and themes', async ({page}, testInfo) => {
            // As the admin, read-only: the category is a view of Preferences, and neither Replay nor Replay all is pressed —
            // each arms a replay. The admin's browser asks GitHub for the latest release on load: the gallery-wide offline
            // guard aborts it, so no update prompt depends on the day. Per combination one full load and one shot.
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings?tab=preferences');
                await expectLanguageAndTheme(page, lang, theme);
                await expect(page.getByTestId('settings-tab-preferences')).toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
                await waitForSettled(page.getByTestId('settings-layout'), 15_000);
                // Every load opens on All; the Onboarding category is chosen in the sidebar, or in the dropdown on a phone.
                await chooseOnboardingCategory(page, viewport);
                // As every load opens it: Setup and Core tour open on their flow, the other four areas folded, nothing armed.
                const section = await expectOnboardingCategory(page);
                // On a phone the card's own header is brought to the top of the screen, so the Core tour's area is on show too.
                await frameOnboardingCategory(page, viewport);
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts).
                if (viewport === 'desktop') await extendScreenToBlock(page, section, `desktop/${lang}/${theme}/settings/onboarding-replay`);
                await parkPointer(page);
                await freezeAnimations(page);
                await waitForMotionSettled(section, 'the Onboarding category');
                await expect(page.getByTestId('deferred-app-popups'), 'a popup lies over the shot').toHaveAttribute('data-active-popup', 'none');
                await expectNoToast(page);
                await screenshot(page, viewport, lang, theme, 'settings', 'onboarding-replay');
                await restoreTallScreen(page);
                // The next combination starts in the header: on a phone it slid away with the scroll down.
                if (viewport === 'mobile') await scrollBackToHeader(page);
            });
        });
    });

    test.describe('Tools', () => {
        test('tools hub - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/tools');
                // Two waves: the catalogue, then each tool's interface. data-state says the catalogue came back
                // healthy — a degraded hub would shoot its warning aside and toast — and data-busy that the
                // interfaces are in as well, which is when a card becomes the link that opens its tool.
                const hub = page.getByTestId('tools-hub');
                await expect(hub, 'the Tools catalogue did not load healthy').toHaveAttribute('data-state', 'ready', {timeout: 20_000});
                await expect(hub).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
                const pac = hub.getByTestId('tools-catalog-cards').getByTestId('tool-card-pac_allocator');
                await expect(pac).toHaveAttribute('data-interface-state', 'ready');
                await expect(pac.getByTestId('tool-compatibility-versions')).toBeVisible();
                await expect(pac.getByTestId('tool-docs-pac_allocator')).toBeVisible();
                await expect(hub.getByTestId('tools-hub-refresh')).toBeEnabled();
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'tools', 'hub');
            });
        });

        // PAC allocator — user/tools/pac-allocator/index.en.md: one placeholder per wizard step, three for the result; the result
        // has a fourth shot, the Exposures (pac-result-exposures), with no placeholder there yet.
        // The planner's draft lives in the open page only: it survives a language or theme picked from the header, not a
        // load. What a page has drawn keeps the browser locale it was drawn under (galleryLocale.ts), so each language opens
        // the planner again after its switch and builds the same draft there, at its first combination (perLanguage); its
        // two themes photograph that draft. The planner only reads the database and the calculation runs in the local
        // solver (galleryPac.ts says what the draft holds, and why). Two tests, so the wizard and the result run side by side.
        test('PAC allocator steps - all languages and themes', async ({page}, testInfo) => {
            // A draft per language (about forty interactions and a few database reads each) and 48 shots. With a single draft
            // the test took about 4 minutes on a quiet lane; the budget keeps room for three more.
            test.setTimeout(600_000);
            const viewport = getViewport(testInfo);
            const shoot = async (region: Locator, what: string, lang: Language, theme: Theme, name: string, tall?: Locator) => {
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): `tall`, the part of the step the screen
                // cuts, gets a screen as tall as it, with room under it for the wizard's sticky footer; the project's screen
                // again right after the shot.
                if (viewport === 'desktop' && tall) await extendScreenToBlock(page, tall, `desktop/${lang}/${theme}/tools/${name}`, {footer: page.getByTestId('pac-planner-footer')});
                await settlePacShot(page, region, what, waitForMotionSettled);
                await screenshot(page, viewport, lang, theme, 'tools', name);
                await restoreTallScreen(page);
            };
            await login(page, TEST_ADMIN);
            const ids = await resolvePacIds(page);
            const draftIn = perLanguage(async (lang) => {
                await openPacPlanner(page);
                await expect(page.locator('html'), 'the language survived the load').toHaveAttribute('lang', lang);
                await freezeAnimations(page);
                const draft = await buildPacDraft(page, ids);
                await scrollBackToHeader(page);
                return draft;
            });

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                const draft = await draftIn(lang);
                await shoot(await framePacLiquidity(page, draft), 'the Liquidity step', lang, theme, 'pac-step-liquidity', page.locator('[data-testid="pac-planner-cash"][data-origin="manual"]'));
                // The editor works on a copy of the Broker: cancelled after the shot, the draft keeps what buildPacDraft applied.
                await shoot(await framePacBrokerEditor(page, draft, waitForMotionSettled), 'the Broker editor', lang, theme, 'pac-step-brokers');
                await closePacBrokerEditor(page);
                await shoot(await framePacAssets(page, draft), 'the Assets step', lang, theme, 'pac-step-assets');
                await shoot(await framePacRouting(page, draft), 'the Routing step', lang, theme, 'pac-step-routing');
                // The Review is shot with one field still to complete (the target total at 90%); the Targets shot completes it.
                await leavePacTargetsIncomplete(page, draft);
                await shoot(await framePacReview(page), 'the Review step', lang, theme, 'pac-step-review');
                await shoot(await framePacTargets(page, draft), 'the Targets step', lang, theme, 'pac-step-targets');
                // The next language and theme are picked from the header, which the framing scrolled away.
                await scrollBackToHeader(page);
            });
        });

        test('PAC allocator result - all languages and themes', async ({page}, testInfo) => {
            // A draft and its calculation per language (the local solver: milliseconds for this draft) and 32 shots; on the
            // desktop the proof shot also resizes the screen and back, every combination. With a single draft the test took
            // about 2 minutes on a quiet lane; the budget keeps room for three more.
            test.setTimeout(360_000);
            const viewport = getViewport(testInfo);
            const shoot = async (region: Locator, what: string, lang: Language, theme: Theme, name: string, tall?: Locator) => {
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): `tall`, the section the screen cuts, gets
                // a screen as tall as it; the project's screen again right after the shot. The proof shot has its own fit below.
                if (viewport === 'desktop' && tall) await extendScreenToBlock(page, tall, `desktop/${lang}/${theme}/tools/${name}`);
                await settlePacShot(page, region, what, waitForMotionSettled);
                await screenshot(page, viewport, lang, theme, 'tools', name);
                await restoreTallScreen(page);
            };
            await login(page, TEST_ADMIN);
            const ids = await resolvePacIds(page);
            const draftIn = perLanguage(async (lang) => {
                await openPacPlanner(page);
                await expect(page.locator('html'), 'the language survived the load').toHaveAttribute('lang', lang);
                await freezeAnimations(page);
                const draft = await buildPacDraft(page, ids);
                await calculatePacPlan(page);
                await scrollBackToHeader(page);
                return draft;
            });

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                const draft = await draftIn(lang);
                await shoot(await framePacResult(page), 'the PAC result', lang, theme, 'pac-result', page.locator('[data-testid="pac-planner-result-section"][data-section="allocation"]'));
                await shoot(await framePacPlan(page, draft), 'the Operational plan', lang, theme, 'pac-result-plan', page.locator('[data-testid="pac-planner-result-section"][data-section="plan"]'));
                // «Exposures – ideal vs actual» starts closed: opened for its shot, and closed right after it, so the next
                // combination's result and plan shots find the page under them as before (galleryPac.ts, framePacExposures).
                await shoot(await framePacExposures(page, viewport), 'the Exposures', lang, theme, 'pac-result-exposures', page.locator('[data-testid="pac-planner-result-section"][data-section="exposures"]'));
                await closePacExposures(page);
                // «Proof and timings» opens the section on a language's first combination; it stays open for the second.
                const proof = await framePacProof(page);
                // DESKTOP — coordinator's decision, provisional: the simulation shot's rule (see 'risk what-if simulation on the
                // dashboard' and «Screens taller than the desktop's» in galleryRiskLab.ts). The page wants the whole Proof and
                // solver section in one image — badges, objective values, solver stages, backend timings — far taller than 720 px:
                // the shot gets a screen as tall as the section plus the frame's margins, width (1280) and scale unchanged,
                // measured and logged (📐) every combination. The mobile project keeps its phone: the section from its title.
                // Reverting the decision is deleting this line.
                if (viewport === 'desktop') await fitScreenToPacProof(page, proof, `desktop/${lang}/${theme}/tools/pac-result-proof`, waitForMotionSettled);
                await shoot(proof, 'Proof and solver', lang, theme, 'pac-result-proof');
                // The project's screen again, before anything else: the next combination's result and plan are 720 px shots.
                await restorePacScreen(page);
                await scrollBackToHeader(page);
            });
        });
    });

    test.describe('Support', () => {
        // The five share buttons, in the order SupportActions draws them (SOCIAL_SHARE_ORDER).
        const SHARE_PLATFORMS = ['x', 'reddit', 'facebook', 'instagram', 'tiktok'] as const;
        // Duplicated on purpose, as in support-copy-and-go.spec.ts: SHARE_HASHTAGS in
        // src/lib/features/support/supportLinks.ts, the same line in every language.
        const SHARE_HASHTAG_LINE = '#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance';

        test('donation popup after sign-in - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            // The popup is a sign-in signal: AuthLoginResponse.show_donation_popup, which the real backend raises
            // only after weeks of use. Every combo signs in again, and its real login response comes back with
            // the signal on — no disposable user, nothing written beyond what any sign-in writes. The same response
            // carries the user's saved language and theme, which the app applies at sign-in over the ones seeded
            // below (auth.ts), so they are set to the combo's too: the sign-in a user with these preferences gets.
            let combo: {lang: Language; theme: Theme} = {lang: 'en', theme: 'light'};
            let signalledLogins = 0;
            await page.route('**/api/v1/auth/login', async (route) => {
                const response = await route.fetch();
                if (!response.ok()) {
                    await route.fulfill({response});
                    return;
                }
                const body = (await response.json()) as {show_donation_popup?: boolean; user_settings?: Record<string, unknown> | null};
                body.show_donation_popup = true;
                if (body.user_settings) body.user_settings = {...body.user_settings, language: combo.lang, theme: combo.theme};
                signalledLogins += 1;
                await route.fulfill({response, json: body});
            });

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    combo = {lang, theme};
                    // Signed out without the UI (the previous popup's backdrop sat over the header): without its
                    // cookie the next full load starts at the login page. Language and theme are seeded into
                    // localStorage before that load, as for the update modal, since the backdrop blocks the
                    // header selectors.
                    await page.context().clearCookies();
                    await page.goto('/');
                    await page.evaluate(
                        ([l, t]) => {
                            localStorage.setItem('librefolio-locale', l);
                            localStorage.setItem('librefolio-theme', t);
                        },
                        [lang, theme] as [string, string],
                    );
                    const signalledBefore = signalledLogins;
                    await login(page, TEST_ADMIN);
                    expect(signalledLogins, 'the sign-in did not go through the intercepted login response').toBeGreaterThan(signalledBefore);

                    // The attributes, not visibility: with the popup open the body is scroll-locked and <html>
                    // lays out with no height, so Playwright calls it hidden.
                    const html = page.locator('html');
                    await expect(html).toHaveAttribute('data-i18n-ready', 'true', {timeout: 15_000});
                    await expect(html).toHaveAttribute('lang', lang, {timeout: 10_000});
                    await expect(html).toHaveClass(new RegExp(`\\b${theme}\\b`));
                    const popups = page.getByTestId('deferred-app-popups');
                    await expect(popups, 'the donation popup was not offered after sign-in').toHaveAttribute('data-active-popup', 'donation', {timeout: 20_000});
                    // The dashboard behind the backdrop has settled, so the dimmed page is the same on every run.
                    await waitForSettled(page.getByTestId('dashboard-page'), 30_000);

                    const popup = page.getByTestId('donation-popup-modal');
                    await expect(popup).toBeVisible();
                    const support = popup.getByTestId('donation-popup-support-card');
                    await expect(support.getByTestId('donation-popup-donate')).toBeVisible();
                    for (const platform of SHARE_PLATFORMS) await expect(support.getByTestId(`support-share-${platform}`)).toBeVisible();
                    const later = popup.getByTestId('donation-popup-later');
                    await expect(later).toBeVisible();
                    await freezeAnimations(page);
                    await waitForMotionSettled(popup, 'the donation popup');
                    await screenshot(page, viewport, lang, theme, 'support', 'donation-popup');

                    // Maybe later is one of the popup's only two ways out (no close button, no Escape, no backdrop).
                    await later.click();
                    await expect(popup).toBeHidden();
                    await expect(popups).not.toHaveAttribute('data-active-popup', 'donation');
                }
            }
        });

        test('social share modal Reddit - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/settings');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await expect(page.getByTestId('settings-page')).toBeVisible({timeout: 10_000});
                    await page.getByTestId('settings-tab-about').click();
                    await expect(page.getByTestId('about-tab')).toBeVisible({timeout: 10_000});
                    // The About tab behind the dialog has loaded, so the dimmed page is the same on every run.
                    await expect(page.getByTestId('about-copy-report')).toBeEnabled({timeout: 15_000});

                    await page.getByTestId('about-support-card').getByTestId('support-share-reddit').click();
                    const modal = page.getByTestId('support-social-share-modal');
                    await expect(modal).toBeVisible();
                    // Reddit, explicitly: the one network whose dialog has a Suggested title.
                    const copyAndGo = modal.getByTestId('support-social-share-copy');
                    await expect(copyAndGo).toHaveAttribute('data-social-platform', 'reddit');
                    await expect(copyAndGo).toHaveAttribute('data-copy-state', 'idle');
                    await expect(modal.getByTestId('support-social-share-post-title')).toBeVisible();
                    await expect(modal.getByTestId('support-social-share-close')).toBeVisible();
                    const message = modal.getByTestId('support-social-share-message');
                    await expect(message).toHaveValue(new RegExp(`\\n\\n${SHARE_HASHTAG_LINE}$`));
                    // The message box is seven rows tall and every message is longer, so it is brought to its end:
                    // the hashtag line the shot is about is then in the frame, as a reader scrolling it would see.
                    await message.evaluate((el) => {
                        el.scrollTop = el.scrollHeight;
                    });
                    await expect.poll(() => message.evaluate((el) => el.scrollHeight - el.clientHeight - el.scrollTop), {message: 'the suggested message did not scroll to its end'}).toBeLessThanOrEqual(1);
                    await freezeAnimations(page);
                    await waitForMotionSettled(modal, 'the share dialog');
                    await screenshot(page, viewport, lang, theme, 'support', 'social-share-modal');

                    // Close, never Copy and go: that one opens a new tab.
                    await modal.getByTestId('support-social-share-close').click();
                    await expect(modal).toBeHidden();
                }
            }
        });
    });

    test.describe('Files', () => {
        test.beforeEach(async ({page}) => {
            // Use TEST_ADMIN since db populate assigns brokers to admin
            await login(page, TEST_ADMIN);
        });

        // One page load per language (after the one the first switch is made on), its two themes switched in place, every
        // shot waiting for its own subject: what the page publishes (galleryFiles.ts), never the network going idle or a
        // fixed wait. CI triage b5: the preview test loaded the page 32 times with 2.4 s of fixed waits each and ran out of
        // its 240 s on every attempt.

        /** Load the Files page at `url` — before the first switch, then once per language — with the gallery's CSS animations frozen. */
        async function openFilesPage(page: Page, url: string): Promise<void> {
            await navigateTo(page, url);
            await expect.poll(() => page.evaluate(() => document.getElementById('app-splash') === null), {message: 'the splash screen never went away'}).toBe(true);
            await freezeAnimations(page);
        }

        /**
         * The eight combinations. The language is switched through the header, its menu closed again, then the page at `url`
         * is loaded again: what a page has drawn keeps the browser locale it was drawn under (galleryLocale.ts), the tables'
         * dates among it, so each language gets a page drawn under its own, in the language just stored — settled before its
         * themes are switched on it in place, read back (chooseTheme) instead of waited for.
         */
        async function eachLanguageAndTheme(page: Page, url: string, callback: (lang: Language, theme: Theme) => Promise<void>): Promise<void> {
            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                await setLanguage(page, lang);
                await languageMenuClosed(page);
                await openFilesPage(page, url);
                await expect(page.locator('html'), 'the language survived the load').toHaveAttribute('lang', lang);
                await waitForSettled(page.getByTestId('files-page'), 20_000);
                for (const theme of THEMES) {
                    await chooseTheme(page, theme);
                    await callback(lang, theme);
                }
            }
        }

        /**
         * The shot, once `subject` has settled: the pointer parked where nothing reacts to it and no tooltip, the fonts in,
         * nothing animating, the subject still, no toast. The spec's screenshot() without its wait for the network to go
         * idle and its 200 ms: each test here has already waited for its own subject.
         */
        async function shootFiles(page: Page, viewport: 'desktop' | 'mobile', lang: Language, theme: Theme, name: string, subject: Locator): Promise<void> {
            const shot = `${viewport}/${lang}/${theme}/files/${name}`;
            await parkPointer(page);
            await fontsLoaded(page);
            await waitForMotionSettled(page.locator('body'), shot);
            await waitForStillness(subject, shot);
            await expectNoToast(page);
            await expectDrawnUnder(page, lang);
            const dir = getGalleryPath(viewport, lang, theme, 'files');
            ensureDir(dir);
            await captureShot(page, path.join(dir, `${name}.png`), shot);
            console.log(`  📸 ${shot}.png`);
        }

        /**
         * The preview of one seeded static resource in every combination: the page loaded once per language, filtered to the
         * file by its name, and the file opened from its own row; `ready` waits for what that kind of preview draws.
         */
        async function shootStaticPreview(page: Page, viewport: 'desktop' | 'mobile', kind: 'image' | 'pdf' | 'markdown' | 'text', ready: (modal: Locator, shot: string) => Promise<Locator>): Promise<void> {
            const name = FILES_SAMPLES[kind];
            const fileId = await staticFileId(page, name);
            const url = `/files?tab=static&filename=${encodeURIComponent(name)}`;
            await openFilesPage(page, url);
            const table = page.getByTestId('files-table-static');

            await eachLanguageAndTheme(page, url, async (lang, theme) => {
                const shot = `${viewport}/${lang}/${theme}/files/preview-modal-${kind}`;
                await filesTableReady(page, table, shot);
                const modal = await openPreview(page, table, fileId, shot);
                const stage = await ready(modal, shot);
                await shootFiles(page, viewport, lang, theme, `preview-modal-${kind}`, stage);
                await closePreview(modal, shot);
            });
        }

        test('static resources tab - all languages and themes', async ({page}, testInfo) => {
            // One load per language, then its two combinations, the desktop's on a screen grown to the table: 10–11 s (desktop),
            // 4 s (mobile) on a quiet lane with a single load (b6); the rest is room for a loaded CI runner.
            test.setTimeout(90_000);
            const viewport = getViewport(testInfo);
            const url = '/files?tab=static';
            await openFilesPage(page, url);
            const table = page.getByTestId('files-table-static');

            await eachLanguageAndTheme(page, url, async (lang, theme) => {
                await filesTableReady(page, table, `${viewport}/${lang}/${theme}/files/static-tab`);
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts).
                if (viewport === 'desktop') await extendScreenToBlock(page, table, `desktop/${lang}/${theme}/files/static-tab`);
                await shootFiles(page, viewport, lang, theme, 'static-tab', table);
                await restoreTallScreen(page);
            });
        });

        test('broker reports tab - all languages and themes', async ({page}, testInfo) => {
            // One load per language, then its two combinations: 7–12 s (desktop), 5 s (mobile) on a quiet lane with a single load
            // (b6), the brokers' logos included.
            test.setTimeout(90_000);
            const viewport = getViewport(testInfo);
            const url = '/files?tab=brim';
            await openFilesPage(page, url);
            const table = page.getByTestId('files-table-brim');

            await eachLanguageAndTheme(page, url, async (lang, theme) => {
                await filesTableReady(page, table, `${viewport}/${lang}/${theme}/files/brim-tab`);
                await shootFiles(page, viewport, lang, theme, 'brim-tab', table);
            });
        });

        test('static resources grid view - all languages and themes', async ({page}, testInfo) => {
            // One load per language, then its two combinations, each entering the grid again (its thumbnails cached after the
            // first): 4–6 s on a quiet lane with a single load (b6), both projects.
            test.setTimeout(90_000);
            const viewport = getViewport(testInfo);
            const url = '/files?tab=static';
            await openFilesPage(page, url);
            const files = page.getByTestId('files-page');
            // The grid lists every file: the card of a seeded one tells it is drawn.
            const card = page.getByTestId(`file-grid-preview-${await staticFileId(page, FILES_SAMPLES.image)}`);
            const gridView = page.getByTestId('view-mode-grid');

            await eachLanguageAndTheme(page, url, async (lang, theme) => {
                const shot = `${viewport}/${lang}/${theme}/files/static-grid`;
                await expect(files, `${shot}: the files never finished loading`).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
                // A fresh grid for each combination: a card prints its size once, when it mounts (galleryFiles.ts).
                await expect(gridView, `${shot}: the page offers no grid view`).toBeVisible();
                await gridView.click();
                await expect(card, `${shot}: the grid is not drawn`).toBeVisible();
                await expect(page.getByTestId('files-table-static'), `${shot}: the list is still shown`).toHaveCount(0);
                await imagesInViewLoaded(files, shot);
                await shootFiles(page, viewport, lang, theme, 'static-grid', files);
                // Back to the list: the next combination gets a grid of its own.
                await page.getByTestId('view-mode-list').click();
                await expect(card, `${shot}: the grid stayed on the page`).toHaveCount(0);
            });
        });

        test('file preview modal (BRIM) - all languages and themes', async ({page}, testInfo) => {
            // One load per language, then its two combinations — open the report from its row, wait for the grid's canvas, shoot,
            // close: 7 s (desktop), 6 s (mobile) on a quiet lane with a single load (b6).
            test.setTimeout(90_000);
            const viewport = getViewport(testInfo);
            const fileId = await brimFileId(page, FILES_SAMPLES.csv);
            const url = `/files?tab=brim&filename=${encodeURIComponent(FILES_SAMPLES.csv)}`;
            await openFilesPage(page, url);
            const table = page.getByTestId('files-table-brim');

            await eachLanguageAndTheme(page, url, async (lang, theme) => {
                const shot = `${viewport}/${lang}/${theme}/files/preview-modal-csv`;
                await filesTableReady(page, table, shot);
                const modal = await openPreview(page, table, fileId, shot);
                const grid = await gridPreviewReady(modal, shot);
                await shootFiles(page, viewport, lang, theme, 'preview-modal-csv', grid);
                await closePreview(modal, shot);
            });
        });

        test('file preview modal (image) - all languages and themes', async ({page}, testInfo) => {
            // One load per language, then its two combinations — open the avatar from its row, wait for the picture, shoot, close:
            // 5 s (desktop), 6 s (mobile) on a quiet lane with a single load (b6).
            test.setTimeout(90_000);
            await shootStaticPreview(page, getViewport(testInfo), 'image', (modal, shot) => imagePreviewReady(modal, shot));
        });

        test('file preview modal (pdf) - all languages and themes', async ({page}, testInfo) => {
            // One load per language, then its two combinations, each starting the viewer again (its engine, the tiles of two
            // pages) and waiting out its page controls (4 s, EmbedPDF's timer, no machine shortens it): 52 s (desktop), 49 s
            // (mobile) on a quiet lane with a single load (b6).
            test.setTimeout(180_000);
            await shootStaticPreview(page, getViewport(testInfo), 'pdf', (modal, shot) => pdfPreviewReady(modal, shot));
        });

        test('file preview modal (markdown) - all languages and themes', async ({page}, testInfo) => {
            // One load per language, then its two combinations — open the sample from its row, wait for the rendered markdown and
            // its fonts: 4–5 s on a quiet lane with a single load (b6), both projects.
            test.setTimeout(90_000);
            await shootStaticPreview(page, getViewport(testInfo), 'markdown', (modal, shot) => markdownPreviewReady(page, modal, shot));
        });

        test('file preview modal (text) - all languages and themes', async ({page}, testInfo) => {
            // One load per language, then its two combinations — open the sample from its row, wait for its lines, shoot, close:
            // 4 s on a quiet lane with a single load (b6), both projects.
            test.setTimeout(90_000);
            await shootStaticPreview(page, getViewport(testInfo), 'text', (modal, shot) => textPreviewReady(modal, shot));
        });
    });

    test.describe('Transactions', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        /** The row the picker shot edits: a standalone deposit the seed gives Interactive Brokers (populate_mock_data.py). */
        const PICKER_EDITED_ROW = 'Initial EUR funding from bank';

        /**
         * The pair the promote-merge shot links: the seeded promote candidates (populate_mock_data.py, tag `promote-test`), read
         * through the API and checked as tx-split-promote.spec.ts checks them — the one standalone WITHDRAWAL, and the standalone
         * DEPOSIT that answers it from another broker in its currency and amount, both on brokers the admin edits. Their
         * descriptions differ, so the product asks to merge them: the merge dialog, the shot. The test used to try the first four
         * rows of a page in pairs, by CSS class, and skip the shot in silence when none matched.
         */
        async function promoteMergePair(page: Page): Promise<{withdrawal: TxRow; deposit: TxRow}> {
            const tagged = (await readTransactions(page, {tags: 'promote-test'})).filter((tx) => (tx.tags ?? []).includes('promote-test') && tx.related_transaction_id == null);
            const withdrawals = tagged.filter((tx) => tx.type === 'WITHDRAWAL');
            expect(
                withdrawals.map((tx) => tx.id),
                'premise: one standalone WITHDRAWAL tagged promote-test — check populate_mock_data.py',
            ).toHaveLength(1);
            const [withdrawal] = withdrawals;
            const deposits = tagged.filter((tx) => tx.type === 'DEPOSIT' && tx.broker_id !== withdrawal.broker_id && tx.cash?.code === withdrawal.cash?.code && Number(tx.cash?.amount) === -Number(withdrawal.cash?.amount));
            expect(
                deposits.map((tx) => tx.id),
                `premise: one standalone DEPOSIT tagged promote-test answers withdrawal #${withdrawal.id} from another broker — check populate_mock_data.py`,
            ).toHaveLength(1);
            const [deposit] = deposits;
            const brokers = new Map((await listBrokers(page)).map((broker) => [broker.id, broker]));
            for (const tx of [withdrawal, deposit]) expect(canEdit(brokers.get(tx.broker_id)), `premise: #${tx.id} sits on a broker the admin can edit`).toBe(true);
            expect(withdrawal.description ?? '', 'premise: the two descriptions differ, so the product asks to merge them').not.toBe(deposit.description ?? '');
            return {withdrawal, deposit};
        }

        test('transaction list - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/transactions');
                await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                await waitForNetworkSettled(page);
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'transactions', 'list');
            });
        });

        test('transaction form modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Click the Add transaction button
                    await page.getByTestId('tx-add-button').click();
                    const formModal = page.getByTestId('tx-form-modal');
                    await expect(formModal).toBeVisible({timeout: 8_000});
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'transactions', 'form-modal');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    // Confirm discard if dialog appears
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                }
            }
        });

        const TX_FORM_VARIANT_TYPES: Array<{type: string; name: string}> = [
            {type: 'SELL', name: 'form-modal-sell'},
            {type: 'DIVIDEND', name: 'form-modal-dividend'},
            {type: 'DEPOSIT', name: 'form-modal-deposit'},
            {type: 'ADJUSTMENT', name: 'form-modal-adjustment'},
            {type: 'TRANSFER', name: 'form-modal-transfer'},
            {type: 'FX_CONVERSION', name: 'form-modal-fxconversion'},
            {type: 'CASH_TRANSFER', name: 'form-modal-cash-transfer'},
            {type: 'WITHDRAWAL', name: 'form-modal-withdrawal'},
            {type: 'INTEREST', name: 'form-modal-interest'},
            {type: 'FEE', name: 'form-modal-fee'},
            {type: 'TAX', name: 'form-modal-tax'},
        ];

        /**
         * Select a transaction type in the form's type combobox and wait for the
         * reactive re-render to land — NOT for network. `setType()` only mutates
         * local Svelte state (draft.type) and TransactionTypeSearchSelect issues
         * zero fetch calls, so a type switch never touches the network. The type
         * icon's `src` is keyed by type code, so waiting for it to change from its
         * previous value is a precise, language-agnostic, network-independent
         * completion signal — resolves in ~10-50ms instead of racing a 10s
         * networkidle timeout under parallel CI load.
         */
        async function selectTransactionType(page: Page, type: string) {
            // The Add form always draws its type select, and offers every type (TransactionFormModal: no restriction on create):
            // asserted, where a two-second probe used to return without choosing — the shot then showed the previous type.
            const typeCombobox = page.locator('[data-testid="tx-form-type"] [role="combobox"]');
            await expect(typeCombobox).toBeVisible({timeout: 10_000});
            const icon = typeCombobox.locator('img');
            const prevSrc = await icon.getAttribute('src').catch(() => null);
            await typeCombobox.click();
            const option = page.locator(`[data-testid="search-select-option-${type}"]`);
            await expect(option, `the type select offers ${type}`).toBeVisible({timeout: 5_000});
            await option.click();
            if (prevSrc != null) {
                await expect(icon).not.toHaveAttribute('src', prevSrc, {timeout: 3_000});
            } else {
                await icon.waitFor({state: 'attached', timeout: 3_000}).catch(() => {});
            }
            // The list has closed: every SearchSelect names its options alike (search-select-option-*), so the next type's
            // option must not be looked for while this list is still on its way out.
            await optionsClosed(page);
        }

        /** Close the form modal, then the TransactionBulkModal that hosts it (tx-add-button
         *  opens a bulk modal wrapping the form) — both must be gone before the next
         *  lang/theme switch, since their backdrop covers the header selectors. */
        async function closeTxFormAndBulkModal(page: Page, formModal: ReturnType<Page['getByTestId']>) {
            await page.keyboard.press('Escape');
            await page.waitForTimeout(200);
            const discardBtn = page.getByTestId('confirm-modal-confirm');
            if (await discardBtn.isVisible({timeout: 500}).catch(() => false)) {
                await discardBtn.click();
                await page.waitForTimeout(200);
            }
            await expect(formModal).not.toBeVisible({timeout: 3_000});

            const bulkModal = page.getByTestId('tx-bulk-modal');
            if (await bulkModal.isVisible({timeout: 500}).catch(() => false)) {
                await page.getByTestId('tx-bulk-close').click();
                await page.waitForTimeout(200);
                const bulkDiscardBtn = page.getByTestId('confirm-modal-confirm');
                if (await bulkDiscardBtn.isVisible({timeout: 500}).catch(() => false)) {
                    await bulkDiscardBtn.click();
                    await page.waitForTimeout(200);
                }
                await expect(bulkModal).not.toBeVisible({timeout: 3_000});
            }
        }

        // Generate one test PER (lang, theme) combo instead of looping inside a
        // single test — this is what actually lets Playwright's worker pool run
        // combos in parallel (viewport parallelism already existed via the
        // desktop/mobile `--project` split). Each combo still opens the Add form
        // ONCE and cycles all 7 types inside it (no re-entering per screenshot).
        for (const lang of SUPPORTED_LANGUAGES) {
            for (const theme of THEMES) {
                test(`transaction form modal variants - ${lang} - ${theme}`, async ({page}, testInfo) => {
                    const viewport = getViewport(testInfo);

                    await setBrowserLocale(page, lang);
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    // Open Add form ONCE for this combo
                    await page.getByTestId('tx-add-button').click();
                    const formModal = page.getByTestId('tx-form-modal');
                    await expect(formModal).toBeVisible({timeout: 8_000});
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(200);

                    // Cycle through each type inside the same open modal — no
                    // close/reopen between screenshots.
                    for (const {type, name} of TX_FORM_VARIANT_TYPES) {
                        await selectTransactionType(page, type);
                        await freezeAnimations(page);
                        // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the Transfer form scrolls at
                        // 720 px; the project's screen again before the next type.
                        if (viewport === 'desktop' && name === 'form-modal-transfer') await fitScreenToDialog(page, formModal, `desktop/${lang}/${theme}/transactions/${name}`, {body: page.getByTestId('tx-form-body')});
                        await screenshot(page, viewport, lang, theme, 'transactions', name);
                        await restoreTallScreen(page);
                    }

                    await closeTxFormAndBulkModal(page, formModal);
                });
            }
        }

        test('transaction picker modal - all languages and themes', async ({page}, testInfo) => {
            // Heavier than the default 3-min budget: nested modal navigation × 4 langs × 2 themes.
            test.setTimeout(300_000); // 5 minutes
            const viewport = getViewport(testInfo);
            // The row edited before the picker opens: a seeded standalone deposit, found through the API by its description and
            // checked — linked to nothing, on a broker the admin edits (owned-pair.ts, seededRow). The first row of the whole
            // table used to be taken, whichever it was that day: a linked pair opens the editor on both of its halves.
            const edited = await seededRow(page, PICKER_EDITED_ROW);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    // The table narrowed to that row (the id column's filter, in the URL): no neighbour's row moves it and no
                    // page boundary hides it. The narrowing is the table's alone: the picker lists every row the page loaded.
                    await navigateTo(page, `/transactions?id_min=${edited.id}&id_max=${edited.id}`);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Open BulkModal via the row's own kebab (row actions are kebab-only since 05712844).
                    const row = page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${edited.id}"]`);
                    await expect(row, `"${PICKER_EDITED_ROW}" is in the narrowed table`).toBeVisible({timeout: 10_000});
                    await clickRowAction(page, row, 'edit');
                    // The single-row edit intent: the BulkModal holds this one row, with the FormModal auto-opened on top
                    const bulkModal = page.locator('[data-testid="tx-bulk-modal-root"]');
                    await expect(bulkModal).toBeVisible({timeout: 8_000});
                    // Close the nested FormModal first
                    const formClose = page.getByTestId('tx-form-close');
                    await expect(formClose).toBeVisible({timeout: 5_000});
                    await formClose.click();
                    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});
                    await expect(page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]'), 'the editor holds the one row edited').toHaveCount(1);
                    // Open the TransactionPickerModal: its rows are the shot's settle's to wait for
                    const pickerBtn = page.getByTestId('tx-bulk-picker');
                    await expect(pickerBtn).toBeVisible({timeout: 5_000});
                    await pickerBtn.click();
                    const pickerModal = page.getByTestId('tx-picker-modal');
                    await expect(pickerModal).toBeVisible({timeout: 5_000});
                    await screenshot(page, viewport, lang, theme, 'transactions', 'picker-modal');
                    // Close the picker and the editor; the next combination starts from a new load
                    await page.keyboard.press('Escape');
                    await page.keyboard.press('Escape');
                }
            }
        });

        test('transaction split action modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Find a paired TX row that has a split action. Row actions are kebab-only
                    // since 05712844: open each row's kebab and keep the first offering
                    // `context-menu-action-split` (paired rows only — rule: scan candidates,
                    // don't infer).
                    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
                    const rowCount = await rows.count();
                    let found = false;
                    for (let i = 0; i < Math.min(rowCount, 30) && !found; i++) {
                        const kebab = page
                            .getByTestId('tx-table')
                            .getByTestId(/^row-actions-/)
                            .nth(i);
                        if (!(await appears(kebab, 1_000))) continue;
                        await kebab.scrollIntoViewIfNeeded();
                        await kebab.click();
                        const splitAction = page.getByTestId('context-menu-action-split');
                        if (await appears(splitAction, 500)) {
                            await splitAction.click();
                            const actionModal = page.getByTestId('tx-action-modal');
                            await expect(actionModal).toBeVisible({timeout: 5_000});
                            await page.waitForTimeout(300);
                            // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts).
                            if (viewport === 'desktop') await fitScreenToDialog(page, actionModal, `desktop/${lang}/${theme}/transactions/action-modal`);
                            await screenshot(page, viewport, lang, theme, 'transactions', 'action-modal');
                            await restoreTallScreen(page);
                            await page.getByTestId('tx-action-modal-cancel').click();
                            await page.waitForTimeout(200);
                            found = true;
                        } else {
                            // Not a paired row — close the menu before trying the next one
                            await page.keyboard.press('Escape');
                            await page.waitForTimeout(150);
                        }
                    }
                    if (!found) throw new Error('action-modal: no paired row with a split action found in the first 30 rows');
                }
            }
        });

        test('transaction clone flow - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Clone the first row via its kebab — the BulkModal opens in clone intent
                    // with the duplicated row staged (and the form auto-opened on top).
                    // Deterministic post-populate: admin can edit every broker → clone offered.
                    const txTable = page.getByTestId('tx-table');
                    await expect(txTable.locator('tbody tr[data-row-id]').first()).toBeVisible({timeout: 5_000});
                    await clickRowAction(page, txTable, 'clone');

                    const bulkModal = page.locator('[data-testid="tx-bulk-modal-root"]');
                    await expect(bulkModal).toBeVisible({timeout: 8_000});
                    // The pre-filled form auto-opens only for a single-row clone; cloning a
                    // paired row stages both legs instead (no form). Close it when present.
                    const formClose = page.getByTestId('tx-form-close');
                    if (await appears(formClose, 3_000)) {
                        await formClose.click();
                        await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});
                    }
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'transactions', 'clone-flow');

                    // Close BulkModal (discard the staged clone)
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('transaction promote-merge modal - all languages and themes', async ({page}, testInfo) => {
            // The seeded promote pair (promoteMergePair), ticked by its rows' own checkboxes, opens the PromoteMergeModal. A
            // missing pair or a promote the product does not offer is a red: the shot is documented.
            const viewport = getViewport(testInfo);
            const {withdrawal, deposit} = await promoteMergePair(page);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    // The table narrowed to the pair's ids (the id column's filter, in the URL): no neighbour's row moves them
                    // and no page boundary hides them. Settled, the page has its type rules too (loaded before its rows): what
                    // the product reads to decide that the pair can be promoted.
                    await navigateTo(page, `/transactions?id_min=${Math.min(withdrawal.id, deposit.id)}&id_max=${Math.max(withdrawal.id, deposit.id)}`);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    const txTable = page.getByTestId('tx-table');
                    await txTable.waitFor({state: 'visible', timeout: 10_000});

                    // Tick both rows: a checkbox is a toggle, read before it is clicked, its end state asserted
                    for (const tx of [withdrawal, deposit]) {
                        const checkbox = txTable.getByTestId(`dt-row-checkbox-tx-${tx.id}`);
                        await expect(checkbox, `transaction #${tx.id} is in the narrowed table`).toBeVisible({timeout: 10_000});
                        if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
                        await expect(checkbox).toHaveAttribute('data-state', 'checked');
                    }
                    await expect(page.getByTestId('selection-toolbar'), 'the selection is the pair, and only the pair').toHaveAttribute('data-selected-count', '2');

                    // The product offers the promote for the pair (promoteMatch)
                    const promoteBtn = page.getByTestId('toolbar-action-promote');
                    await expect(promoteBtn, `the product offers no promote for #${withdrawal.id} and #${deposit.id}`).toBeVisible({timeout: 5_000});
                    // The shot has the promote button's tooltip over the dialog's title, as a user has it. The button sits in a
                    // Tooltip, which pins its tooltip on a click (Tooltip.svelte, toggle) and closes a pinned one on a click
                    // outside it — never one inside the dialog: ModalBase stops its clicks — or 30 s after the pointer left.
                    // Real behaviour, so the shot keeps it, declared (pinnedTooltip), instead of faking a click to hide it; it is
                    // on the designer's list. None on screen before the click, one after: the one in the shot is the promote's.
                    const tooltip = page.getByTestId('tooltip-content');
                    await expect(tooltip, 'no tooltip is on screen before the promote is clicked').toHaveCount(0);
                    await promoteBtn.click();
                    // Use role=dialog to target the ModalBase backdrop (not the inner div)
                    // which also has data-testid="promote-merge-modal"
                    const mergeModal = page.locator('[data-testid="promote-merge-modal"][role="dialog"]');
                    await expect(mergeModal, 'the pair diverges, so the product asks to merge it').toBeVisible({timeout: 5_000});
                    await expect(tooltip, "the click pinned the promote button's tooltip, and no other tooltip is on screen").toHaveCount(1);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'transactions', 'promote-merge-modal', {pinnedTooltip: true});
                    // Nothing pins it again without a click: there now, so there in the picture.
                    await expect(tooltip, 'the pinned tooltip has closed: it closes 30 s after the pointer leaves the button, so the shot may have been taken without it').toHaveCount(1);
                    // Nothing is committed: the dialog is cancelled, and the next combination starts from a new load
                    await page.keyboard.press('Escape');
                }
            }
        });

        test('delete linked pair modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // T4: the dedicated delete modal is gone — a single-row delete
                    // opens the bulk workspace with the pair collapsed into one row
                    // pre-marked for deletion, plus the split-hint banner. That IS
                    // the shot; it is richer than the old modal (grid + banner).
                    //
                    // The mock ships a paired "delete-safe" ETH TRANSFER — find it
                    // by its tag (tags are never translated, unlike the type name
                    // the old text scan relied on). Hard assertions, no probe: this
                    // shot is referenced by the docs, so a silent skip is doc rot.
                    const pairRow = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').filter({hasText: 'delete-safe'}).filter({hasText: 'ETH'}).first();
                    await expect(pairRow, 'the delete-safe ETH pair must exist — check populate_mock_data.py').toBeVisible({timeout: 10_000});

                    await pairRow.hover();
                    const kebabBtn = pairRow.getByTestId(/^row-actions-/);
                    await expect(kebabBtn, 'the delete-safe pair must offer row actions (TEST_ADMIN owns both brokers)').toBeVisible({timeout: 3_000});
                    await kebabBtn.click();
                    await page.getByTestId('context-menu-action-delete').click();

                    const bulkModal = page.getByTestId('tx-bulk-modal');
                    await expect(bulkModal).toBeVisible({timeout: 5_000});
                    // The pair is staged as ONE collapsed row, marked for deletion,
                    // and the split hint explains the alternative. Both are the
                    // contract this shot documents.
                    await expect(bulkModal.locator('tbody tr.row-deleted')).toHaveCount(1);
                    await expect(bulkModal.getByTestId('tx-bulk-split-hint')).toBeVisible();
                    await waitForSettled(bulkModal.getByTestId('tx-bulk-modal-root'));
                    await freezeAnimations(page);
                    // The pointer is parked by the shot: the hover above only revealed the row's kebab, on the table behind,
                    // and what it rests on after the menu's click is no part of the editor's picture.
                    await screenshot(page, viewport, lang, theme, 'transactions', 'bulk-delete-pair-modal');

                    // Close WITHOUT committing — the pair is shared mock data and
                    // must survive for the real test suites (tx-delete reads it).
                    await bulkModal.getByTestId('tx-bulk-cancel').click();
                    await expect(bulkModal).not.toBeVisible({timeout: 5_000});
                }
            }
        });
    });

    test.describe('Brokers', () => {
        test.beforeEach(async ({page}) => {
            // Use TEST_ADMIN since db populate assigns brokers to admin
            await login(page, TEST_ADMIN);
        });

        test('broker list - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/brokers');
                await waitForSplashGone(page);
                await freezeAnimations(page);
                // The list says when its brokers are in (data-busy); their logos are the shot's settle's to wait for.
                await waitForSettled(page.getByTestId('brokers-page'), 20_000);
                await expect(page.locator('[data-testid^="broker-card-"]').filter({hasText: 'Charles Schwab'}).first(), 'the broker list shows its brokers').toBeVisible({timeout: 10_000});
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole page, on a screen as tall as it.
                if (viewport === 'desktop') await extendScreenToBlock(page, page.locator(PAGE_BLOCK), `desktop/${lang}/${theme}/brokers/list`);
                await screenshot(page, viewport, lang, theme, 'brokers', 'list');
                await restoreTallScreen(page);
            });
        });

        test('broker detail - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    // Navigate fresh each iteration to ensure clean state
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // By name, not the first card: the list is alphabetical, and its first broker, Charles Schwab, has no
                    // transactions, so the overview was empty (M-31). Interactive Brokers holds cash and stocks across the
                    // default 3-month window (populate_mock_data.py). Its logo and its KPIs are the shot's settle's to wait for.
                    await openBrokerCardByName(page, 'Interactive Brokers');
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts).
                    if (viewport === 'desktop') await extendScreenToBlock(page, page.getByTestId('broker-overview-tab'), `desktop/${lang}/${theme}/brokers/detail`);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'detail');
                    await restoreTallScreen(page);
                }
            }
        });

        test('broker edit modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    // Navigate fresh each iteration to ensure clean state
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // By name: the first card is whatever the list sorts first — Charles Schwab today, named here.
                    await openBrokerCardByName(page, 'Charles Schwab');

                    // Click edit button to open BrokerModal
                    const editBtn = page.getByTestId('broker-edit-button');
                    await expect(editBtn).toBeVisible({timeout: 5000});
                    await editBtn.click();
                    await expect(page.getByTestId('broker-modal')).toBeVisible({timeout: 5000});
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts). The fit measures once the import
                    // plugins are in: their «Loading…» line under the select changed the form's height (galleryTallShots.ts).
                    if (viewport === 'desktop') await fitScreenToDialog(page, page.getByTestId('broker-modal'), `desktop/${lang}/${theme}/brokers/edit-modal`);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'edit-modal');
                    await restoreTallScreen(page);

                    // Close modal; the next combination starts from a new load
                    await page.keyboard.press('Escape');
                }
            }
        });

        test('broker sharing modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSplashGone(page);
                    await freezeAnimations(page);
                    await waitForSettled(page.getByTestId('brokers-page'), 20_000);

                    const coinbaseCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: 'Coinbase'}).first();
                    await expect(coinbaseCard).toBeVisible({timeout: 5_000});

                    const shareButton = coinbaseCard.locator('[data-testid^="broker-share-"]').first();
                    await expect(shareButton).toBeVisible({timeout: 5_000});
                    await shareButton.click();
                    // The sharing donut and the users' avatars are the shot's settle's to wait for.
                    await expect(page.getByTestId('broker-sharing-modal')).toBeVisible({timeout: 5_000});

                    await screenshot(page, viewport, lang, theme, 'brokers', 'sharing-modal');

                    // The next combination starts from a new load
                    await page.keyboard.press('Escape');
                }
            }
        });

        test('broker info tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openBrokerCardByName(page, 'Coinbase');
                    await page.getByTestId('broker-tab-info').click();
                    await expect(page.getByTestId('broker-info-tab')).toBeVisible({timeout: 5_000});
                    await expect(page.getByTestId('broker-metadata')).toBeVisible({timeout: 5_000});
                    // The sharing donut is drawn after the section: the shot's settle waits for it to stand still.
                    await expect(page.getByTestId('broker-sharing-section')).toBeVisible({timeout: 5_000});
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts).
                    if (viewport === 'desktop') await extendScreenToBlock(page, page.getByTestId('broker-info-tab'), `desktop/${lang}/${theme}/brokers/info-tab`);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'info-tab');
                    await restoreTallScreen(page);
                }
            }
        });

        test('broker positions tab - all languages and themes', async ({page}, testInfo) => {
            // Four variants a combination, two of them on the desktop on a screen as tall as the panel (the map needs a few
            // resizes, it grows with the screen) and back: more than the 4-minute default leaves.
            test.setTimeout(360_000);
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openBrokerCardByName(page, 'Coinbase');
                    await selectOneYearDateRange(page);
                    await page.getByTestId('broker-tab-posizioni').click();
                    await expect(page.getByTestId('broker-holdings')).toBeVisible({timeout: 5_000});
                    await screenshotPositionsVariants(page, viewport, lang, theme, 'brokers', ['positions-holdings-map', 'positions-performance-table']);
                }
            }
        });

        test('broker fifo lots panel - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openBrokerCardByName(page, 'Coinbase');
                    await selectMaxDateRange(page);
                    await page.getByTestId('broker-tab-posizioni').click();
                    await expect(page.getByTestId('broker-holdings')).toBeVisible({timeout: 5_000});
                    await setPositionsView(page, 'holdings', 'table');

                    await clickRowAction(page, page, 'analyze-lots');

                    // Loaded and drawn — the skeleton gone, the WAC and Gantt charts drawn — inside the capture, as on the dashboard
                    await captureLotsAnalysisScreenshots(page, viewport, lang, theme, 'brokers');

                    await page.getByTestId('lots-analysis-panel-close').click();
                    await expect(page.getByTestId('lots-analysis-panel')).toBeHidden({timeout: 5_000});
                }
            }
        });

        test('import modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    // Navigate fresh each iteration
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // By name: the first card is whatever the list sorts first — Charles Schwab today, named here.
                    await openBrokerCardByName(page, 'Charles Schwab');

                    // Switch to the Transazioni tab, where the import/new-tx buttons live
                    const transactionsTabButton = page.getByTestId('broker-tab-transazioni');
                    await transactionsTabButton.click();
                    await expect(transactionsTabButton).toHaveAttribute('aria-selected', 'true');
                    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: 5000});
                    await screenshot(page, viewport, lang, theme, 'brokers', 'transactions-tab');

                    // Scroll to and click the import history button
                    const importBtn = page.getByTestId('broker-show-import-history');
                    await expect(importBtn).toBeVisible({timeout: 5_000});
                    await importBtn.scrollIntoViewIfNeeded();
                    await importBtn.click();

                    // The modal's «Loading…» list is the shot's settle's to wait out (its files request)
                    const modal = page.getByTestId('import-files-modal');
                    await expect(modal).toBeVisible({timeout: 3000});
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-modal');
                    // The next combination starts from a new load
                    await page.keyboard.press('Escape');
                }
            }
        });

        test('import wizard step 1 - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Open ImportWizardModal via the Import button on the transactions page
                    await page.getByTestId('tx-import-button').click();
                    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});
                    await page.getByTestId('import-wizard-step1').waitFor({state: 'visible', timeout: 5_000});
                    await waitForSettled(page.getByTestId('import-wizard-step1'));
                    await freezeAnimations(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-step1');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    // Confirm discard if needed
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    // Also close BulkModal if open
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import wizard step 2 - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    // Open ImportWizardModal
                    await page.getByTestId('tx-import-button').click();
                    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});

                    // Skip step 1 (DB already has uploaded files), once step 1 has its brokers: Next before them used to open
                    // step 2 with every broker's panel folded (batch 19, M-16)
                    await waitForSettled(page.getByTestId('import-wizard-step1'));
                    await page.getByTestId('import-wizard-next').click();
                    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 8_000});
                    // Its broker files, plugins and set previews load behind its own data-busy: what the 800 ms stood in for
                    await waitForSettled(page.getByTestId('import-wizard-step2'), 30_000);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-step2');

                    // Close
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import wizard step 4 asset resolution - all languages and themes', async ({page}, testInfo) => {
            // Heavier than the default 3-min budget: real CSV parse via backend × 4 langs × 2 themes.
            test.setTimeout(300_000); // 5 minutes
            // generic_simple.csv contains UNETF (unknown asset → unresolved card in step 4)
            const viewport = getViewport(testInfo);
            const GENERIC_SIMPLE = path.resolve(__dirname, '../../backend/app/services/brim_providers/sample_reports/generic_simple.csv');

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    // Open ImportWizardModal
                    await page.getByTestId('tx-import-button').click();
                    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});

                    // Skip step 1 (go to step 2 which shows files already in DB)
                    await waitForSettled(page.getByTestId('import-wizard-step1'));
                    await page.getByTestId('import-wizard-next').click();
                    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 8_000});
                    await waitForSettled(page.getByTestId('import-wizard-step2'), 30_000);

                    // Select and parse generic_simple.csv (step 3)
                    const parsed = await analyseWizardSample(page);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-step3');

                    // Continue to step 4: its notices confirmed when the parse raised some — the response says, not a probe
                    await continueToReview(page, parsed);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-step4-resolution');

                    // Close
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import wizard duplicate detection - all languages and themes', async ({page}, testInfo) => {
            // generic_simple.csv has AAPL rows that match transactions already in the DB.
            // After parsing, step4 shows the transaction table with "likely duplicate" badges.
            // We scroll to center on the table to make the duplicate status visible.
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    await page.getByTestId('tx-import-button').click();
                    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});

                    // Skip to step 2
                    await waitForSettled(page.getByTestId('import-wizard-step1'));
                    await page.getByTestId('import-wizard-next').click();
                    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 8_000});
                    await waitForSettled(page.getByTestId('import-wizard-step2'), 30_000);

                    // Select generic_simple.csv — has AAPL/MSFT rows + UNETF (unresolved)
                    // The AAPL rows match existing DB transactions → show as "likely duplicate"
                    const parsed = await analyseWizardSample(page);
                    // To step 4: its notices confirmed when the parse raised some — the response says, not a probe
                    const step4 = await continueToReview(page, parsed);

                    // Scroll to the transaction table (below the resolve section) to show duplicate badges
                    const txTable = step4.locator('table').first();
                    if (await appears(txTable, 2_000)) {
                        await txTable.evaluate((el) => el.scrollIntoView({block: 'center'}));
                    }
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-duplicate');

                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import bulk staging - all languages and themes', async ({page}, testInfo) => {
            // Heavier than the default 3-min budget under load: real backend list load × 4 langs × 2 themes.
            test.setTimeout(300_000); // 5 minutes
            // Show the BulkModal (staging grid) — open it in edit mode from the transactions table.
            // The BulkModal staging view is the same whether populated from wizard import or manual edit.
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await waitForNetworkSettled(page);
                    await freezeAnimations(page);

                    // Open BulkModal via the row kebab edit action (kebab-only since 05712844).
                    // Deterministic post-populate: admin owns every row → edit is always offered.
                    const txTable = page.getByTestId('tx-table');
                    await expect(txTable.locator('tbody tr[data-row-id]').first()).toBeVisible({timeout: 5_000});
                    await clickRowAction(page, txTable, 'edit');
                    // BulkModal opens with the FormModal auto-opened on top (single-row edit intent)
                    const bulkModal = page.locator('[data-testid="tx-bulk-modal-root"]');
                    await expect(bulkModal).toBeVisible({timeout: 8_000});
                    // Close the auto-opened FormModal to reveal the staging grid
                    const formClose = page.getByTestId('tx-form-close');
                    await expect(formClose).toBeVisible({timeout: 3_000});
                    await formClose.click();
                    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-bulk-staging');

                    // Close BulkModal
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import wizard conditional steps (assets / fix / duplicates / n-way compare) - all languages and themes', async ({page}, testInfo) => {
            // Heaviest wizard test: two real uploads + backend parse + four step walkthrough × 8 combos.
            test.setTimeout(600_000); // 10 minutes
            const viewport = getViewport(testInfo);
            const TITOLI_CSV = path.join(__dirname, 'assets', 'demo_credit_agricole_titoli.csv');
            const CONTO_CSV = path.join(__dirname, 'assets', 'demo_credit_agricole_conto.csv');

            // Track this test's own uploads via the upload responses, so cleanup deletes
            // exactly those files (never a parallel worker's same-named copies).
            const uploadedFileIds = new Set<string>();
            page.on('response', (response) => {
                if (!response.url().includes('/api/v1/brokers/import/upload')) return;
                if (!response.ok()) return;
                response
                    .json()
                    .then((body) => {
                        const id = (body as {file_id?: string})?.file_id;
                        if (id) uploadedFileIds.add(id);
                    })
                    .catch(() => {});
            });
            const cleanupUploadedFiles = async () => {
                for (const id of uploadedFileIds) {
                    await page.request.delete(`/api/v1/brokers/import/files/${id}`).catch(() => {});
                }
                uploadedFileIds.clear();
            };
            // Parse opens only when every ticked file has a plugin and no report set is ticked in
            // part or left incomplete. When it stays shut, say which of those gates held it.
            const expectParseEnabled = async () => {
                try {
                    await expect(page.getByTestId('import-wizard-parse')).toBeEnabled({timeout: 10_000});
                } catch (error) {
                    const setBlocks = page.getByTestId('import-wizard-set-blocks');
                    const why = (await setBlocks.count()) > 0 ? `a report set blocks the analysis (data-reason="${await setBlocks.getAttribute('data-reason')}")` : 'no report set blocks it, so a ticked file has no plugin or nothing is ticked';
                    throw new Error(`import-wizard-parse stayed disabled: ${why}.\n${(error as Error).message}`);
                }
            };

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    try {
                        // ── Step 1: upload the two Credit Agricole demo files ──
                        await page.getByTestId('tx-import-button').click();
                        await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});
                        const step1 = page.getByTestId('import-wizard-step1');
                        await step1.waitFor({state: 'visible', timeout: 5_000});
                        // A fresh wizard opens with its drop zone expanded (dropZoneExpanded starts true and
                        // resetState() restores it), so there is no "upload more" to click: the input is there.
                        const fileInput = step1.getByTestId('file-input');
                        await expect(fileInput).toBeAttached({timeout: 5_000});
                        await fileInput.setInputFiles([TITOLI_CSV, CONTO_CSV]);
                        // Both pending rows rendered
                        await expect(step1.locator('tbody tr[data-row-id]')).toHaveCount(2, {timeout: 5_000});

                        // Assign the global broker (both files to the same broker — duplicates
                        // arbitration is per-broker): Interactive Brokers, which has an icon and is
                        // seeded for TEST_ADMIN by populate_mock_data.py — required, not a preference.
                        await page.getByTestId('import-wizard-step1-broker-select').locator('[role="combobox"]').click();
                        const listbox = page.locator('[role="listbox"]').first();
                        await expect(listbox).toBeVisible({timeout: 5_000});
                        await expect(listbox).toHaveAttribute('aria-busy', 'false', {timeout: 8_000});
                        const ibOption = listbox.locator('[data-testid^="search-select-option-"]').filter({hasText: 'Interactive Brokers'}).first();
                        await expect(ibOption, 'Interactive Brokers must be offered to TEST_ADMIN — check populate_mock_data.py').toBeVisible({timeout: 5_000});
                        await ibOption.click();

                        // Upload on Next — uploaded files arrive pre-selected in step 2 (T7)
                        await expect(page.getByTestId('import-wizard-next')).toBeEnabled({timeout: 5_000});
                        await page.getByTestId('import-wizard-next').click();
                        const step2 = page.getByTestId('import-wizard-step2');
                        await step2.waitFor({state: 'visible', timeout: 10_000});
                        await expect(step2).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
                        // Both uploads are known by id: the cleanup deletes by these, and step 3 is checked against them.
                        await expect.poll(() => uploadedFileIds.size, {message: 'both demo uploads must be recorded by id', timeout: 5_000}).toBe(2);

                        // ── Step 2 → 3: parse both files (plugin auto-picked: broker_credit_agricole) ──
                        // The demo files are two single files (only report-set plugins group files into
                        // sets), so no set should hold Parse — but if one ever does, the failure says so.
                        await expectParseEnabled();
                        await page.getByTestId('import-wizard-parse').click();
                        const step3 = page.getByTestId('import-wizard-step3');
                        await step3.waitFor({state: 'visible', timeout: 15_000});
                        await waitForParseVerdict(page, 60_000);
                        await expect(step3, 'both demo files must parse: the later steps are built from the two of them').toHaveAttribute('data-parse-state', 'ok');
                        // The analysis lists exactly what step 2 ticked: this combo's two uploads, nothing else.
                        await expect(step3.locator('tbody tr[data-row-id]')).toHaveCount(uploadedFileIds.size);
                        for (const id of uploadedFileIds) await expect(step3.locator(`tbody tr[data-row-id="${id}"]`)).toHaveCount(1);

                        // ── Step 3 → assets: Continue either opens the parse-notices modal (the parse
                        // raised some) or moves straight on. Wait for whichever of the two the click
                        // produced, then act on that one — no guess at how long the modal takes.
                        await page.getByTestId('import-wizard-continue').click();
                        const assetsStep = page.getByTestId('import-wizard-step-assets');
                        const warningConfirm = page.getByTestId('import-wizard-warning-confirm');
                        await expect(warningConfirm.or(assetsStep).first()).toBeVisible({timeout: 15_000});
                        if (await warningConfirm.isVisible()) {
                            await warningConfirm.click();
                            await expect(warningConfirm).toBeHidden({timeout: 5_000});
                        }

                        // ── Assets step: proposed (AMUNDI name-suffix) + confirmed (BTP) groups ──
                        await expect(assetsStep).toBeVisible({timeout: 15_000});
                        await expect(assetsStep.getByTestId('asset-group-step')).toBeVisible({timeout: 10_000});
                        // The shot exists to show an open proposal: insist on one before taking it.
                        const proposedGroups = assetsStep.locator('[data-testid^="asset-group-grp-"][data-state="proposed"]');
                        await expect(proposedGroups.first()).toBeVisible({timeout: 10_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-assets-step');
                        // Continue stays disabled while any proposal is open, so settle them first.
                        // AssetGroupStep offers "confirm all" only from two open proposals up; a lone one
                        // is settled by its own button. The cards render together, so the count is final.
                        if ((await proposedGroups.count()) >= 2) {
                            await assetsStep.getByTestId('asset-group-confirm-all').click();
                        } else {
                            await proposedGroups.getByTestId(/^asset-group-confirm-grp-/).click();
                        }
                        await expect(proposedGroups).toHaveCount(0, {timeout: 5_000});
                        const assetsContinue = page.getByTestId('import-wizard-assets-continue');
                        await expect(assetsContinue).toBeEnabled({timeout: 30_000});
                        await assetsContinue.click();

                        // ── Fix step: bundled-amount warning + unresolved-asset blocker ──
                        const fixStep = page.getByTestId('import-wizard-step-fix');
                        await expect(fixStep).toBeVisible({timeout: 15_000});
                        await expect(fixStep.getByTestId('fix-step-row').first()).toBeVisible({timeout: 10_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-fix-step');
                        // Settle every flagged row (keep the plugin's fallback) to unlock Continue
                        await fixStep.getByTestId('fix-step-accept-all').click();
                        await expect(page.getByTestId('import-wizard-fix-continue')).toBeEnabled({timeout: 10_000});
                        await page.getByTestId('import-wizard-fix-continue').click();

                        // ── Duplicates step: cross-file coupon pair (probable/partial tier) ──
                        const dupStep = page.getByTestId('import-wizard-step-duplicates');
                        await expect(dupStep).toBeVisible({timeout: 20_000});
                        await expect(dupStep.getByTestId('import-wizard-duplicate-resolver')).toBeVisible({timeout: 10_000});
                        // Every duplicate re-check rebuilds the resolver's layout: read it only once the
                        // wizard says no re-check or candidate refresh is running.
                        await expect(page.getByTestId('import-wizard-content')).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
                        // The resolver opens by itself when a group is partial (probable tier) and stays
                        // folded when every overlap is total. A toggle: read its settled state, click only
                        // when folded, then assert the end state.
                        const filePriority = dupStep.getByTestId('import-wizard-file-priority');
                        if (!(await filePriority.isVisible())) await dupStep.getByTestId('import-wizard-duplicate-resolver-toggle').click();
                        await expect(filePriority).toBeVisible({timeout: 3_000});
                        // Open the first tier panel so its groups are listed in the shot
                        const tierToggle = dupStep.locator('[data-testid^="import-wizard-resolver-tier-toggle-"]').first();
                        await expect(tierToggle).toBeVisible({timeout: 5_000});
                        await tierToggle.click();
                        await expect(dupStep.getByTestId('import-wizard-duplicate-group').first()).toBeVisible({timeout: 3_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-duplicates-step');

                        // ── N-way compare modal from a duplicate group ──
                        // The compare action lives inside the expanded group's body
                        await dupStep.getByTestId('import-wizard-duplicate-group').first().locator('button').first().click();
                        const compareBtn = dupStep.locator('[data-testid^="import-wizard-resolver-compare-"]').first();
                        await expect(compareBtn).toBeVisible({timeout: 5_000});
                        await compareBtn.click();
                        const compareModal = page.getByTestId('import-wizard-compare-modal');
                        await expect(compareModal).toBeVisible({timeout: 5_000});
                        await expect(compareModal.getByTestId('import-wizard-compare-table')).toBeVisible({timeout: 5_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, theme, 'brokers', 'import-nway-compare');
                        await page.getByTestId('import-wizard-compare-close').click();
                        await expect(compareModal).not.toBeVisible({timeout: 3_000});
                    } finally {
                        // A page that died (test timeout) cannot be cleaned, and touching it would replace
                        // the real error with "Target page… closed". Nothing here may throw either, for
                        // the same reason: the wizard needs no closing, since the next combo starts from
                        // a full navigation — only this combo's uploads must go.
                        if (!page.isClosed()) await cleanupUploadedFiles();
                    }
                }
            }
        });
    });

    /**
     * Inventory group 3: the Danske Bank report sets, from Select Files to the Files page, and the bulk
     * editor's todo banner. Helpers and the reasons behind them: fixtures/galleryReportSets.ts.
     *
     * Each test signs up its own account — the admin's wizard shots list every file the admin reaches,
     * so these uploads must never be the admin's — which owns its broker and its uploads, and afterEach
     * deletes it with everything it owns. Its broker is named `‹label› · ‹TOKEN›` (galleryBrokerName): the
     * mark the gallery's outer beforeEach hides from every session that cannot reach it (hideGalleryTempData).
     * Nothing is ever committed: the wizard stops on its own steps, and the editor is closed through its
     * discard guard.
     *
     * The data is uploaded once per test, over the API, into one upload batch per set — the same request
     * the wizard sends — and every combination opens the wizard again. Select Files then lists the set as
     * detection reads it (a set analysed earlier keeps the members it was analysed with, which are the
     * same here), unticked and folded, so the test ticks it whole and unfolds it, as it is right after an
     * upload. Language and theme are switched on the page behind the wizard, before it opens.
     */
    test.describe('Import report sets (Danske Bank)', () => {
        let account: GalleryAccount | undefined;

        test.beforeEach(() => {
            account = undefined;
        });

        // afterEach, not `finally`: a cleanup that throws from `finally` would replace the error it follows. A failed test
        // first logs what its page was still waiting for and attaches the page: the cleanup leaves it, its requests are
        // forgotten with it, and Playwright snapshots it only after the hooks.
        test.afterEach(async ({page, request}, testInfo) => {
            logApiOnFailure(page, testInfo);
            await attachPageSnapshotOnFailure(page, testInfo);
            if (account) await cleanupGalleryAccount(page, request, account);
        });

        /** A disposable account through the welcome, with every guide skipped, and its broker, named `‹label› · ‹TOKEN›` (galleryBrokerName). */
        async function startAccount(page: Page, request: APIRequestContext, label: string, extra: Record<string, unknown> = {}): Promise<number> {
            account = await registerGalleryAccount(request);
            await onboardGalleryAccount(page, account);
            return createGalleryBroker(page.request, account, label, extra);
        }

        /** One language and one theme, on the account's Transactions page, settled: the wizard opens from there. */
        async function onTransactions(page: Page, lang: Language, theme: Theme): Promise<void> {
            await navigateTo(page, '/transactions');
            await setLanguage(page, lang);
            await setTheme(page, theme);
            await expect(page.getByTestId('tx-table')).toBeVisible({timeout: 15_000});
            await waitForSettled(page.getByTestId('transactions-page'), 20_000);
        }

        /** The set's card in Select Files: its broker panel open, the set ticked whole and unfolded, settled. */
        async function openSetCard(page: Page, brokerId: number, batchId: string, status: 'complete' | 'incomplete'): Promise<Locator> {
            await openWizardOnSelectFiles(page);
            await openBrokerPanel(page, brokerId);
            const card = reportSetCard(page, brokerId, batchId);
            await expect(card, `the upload is one ${status} set`).toHaveAttribute('data-set-status', status, {timeout: 20_000});
            await tickWholeSet(card);
            await unfoldCard(card);
            await waitForSettled(card, 20_000);
            return card;
        }

        test('report set card and its Read as menu - all languages and themes', async ({page, request}, testInfo) => {
            // Account and upload ~20 s; per combination a full load, the wizard to Select Files and two shots,
            // ~15 s, twice that under parallel load: 8 × 30 s + 60 s.
            test.setTimeout(300_000);
            const viewport = getViewport(testInfo);
            const brokerId = await startAccount(page, request, 'Danske Bank');
            // The bank's two exports, as it exports them, uploaded together: one set.
            const {
                batchId,
                files: [custody, cash],
            } = await uploadSet(page.request, brokerId, [DANSKE_SAMPLES.custody, DANSKE_SAMPLES.cash]);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await onTransactions(page, lang, theme);
                    const card = await openSetCard(page, brokerId, batchId, 'complete');
                    // One table per kind of export, the timeline, the note of a first import — nothing missing.
                    await expect(roleRow(card, 'custody', custody.file_id)).toBeVisible();
                    await expect(roleRow(card, 'cash', cash.file_id)).toBeVisible();
                    await expect(card.getByTestId('report-set-missing')).toHaveCount(0);
                    await expect(card.locator('[data-testid="report-set-history"][data-kind="first"]')).toBeVisible();
                    await expect(page.getByTestId('import-wizard-parse'), 'a complete set, ticked whole, can be analysed').toBeEnabled();
                    const readAs = card.getByTestId('report-set-read-as-button');
                    await expect(readAs, 'Read as sits in the header, closed').toHaveAttribute('aria-expanded', 'false');
                    await scrollToTop(card);
                    await expect(card.getByTestId('report-set-timeline')).toBeInViewport();
                    await freezeAnimations(page);
                    await waitForMotionSettled(page.getByTestId('import-wizard-modal'), 'the import wizard');
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-report-set-card');

                    // Read as, open: the set's plugin, detected and chosen, and reading the files one by one.
                    await readAs.click();
                    const list = card.getByTestId('report-set-read-as-dropdown');
                    await expect(list).toBeVisible();
                    await expect(list.getByTestId(`report-set-read-as-option-${DANSKE}`), 'the set is read with Danske Bank').toHaveAttribute('aria-selected', 'true');
                    await expect(list.getByTestId('report-set-read-as-option-one-by-one')).toHaveAttribute('aria-selected', 'false');
                    await expect(list).toBeInViewport();
                    await waitForMotionSettled(list, 'the Read as list');
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-report-set-read-as');
                    // Escape, never a choice: the set stays as it is. The next combination starts from a full load.
                    await page.keyboard.press('Escape');
                    await expect(list).toHaveCount(0);
                }
            }
        });

        test('report set file menu - all languages and themes', async ({page, request}, testInfo) => {
            // Account and upload ~20 s; per combination a full load, the wizard to Select Files and one shot,
            // ~12 s, twice that under parallel load: 8 × 24 s + 50 s.
            test.setTimeout(240_000);
            const viewport = getViewport(testInfo);
            const brokerId = await startAccount(page, request, 'Danske Bank');
            // The bank's two exports, as it exports them, uploaded together: one set. No single-file plugin reads the bank's
            // own cash statement (decision 1), so its ⋮ menu holds Preview, Remove from the set and Delete, and no «Read alone
            // with…»: the menu of a real export, which the Danske Bank page shows.
            const {
                batchId,
                files: [custody, cash],
            } = await uploadSet(page.request, brokerId, [DANSKE_SAMPLES.custody, DANSKE_SAMPLES.cash]);
            expect(cash.compatible_plugins ?? [], 'premise: Danske Bank reads the bank’s cash statement').toContain(DANSKE);
            expect(cash.compatible_plugins ?? [], 'premise: the generic CSV does not').not.toContain(GENERIC);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await onTransactions(page, lang, theme);
                    const card = await openSetCard(page, brokerId, batchId, 'complete');
                    await expect(roleRow(card, 'custody', custody.file_id)).toBeVisible();
                    const row = roleRow(card, 'cash', cash.file_id);
                    await expect(row, 'the bank’s statement is the cash export of the set').toBeVisible();
                    await scrollToTop(card);
                    await freezeAnimations(page);

                    await row.getByTestId(`row-actions-${cash.file_id}`).click();
                    const menu = page.getByTestId('context-menu');
                    await expect(menu).toBeVisible();
                    // What the menu holds first, then what it must not: the absences would also hold for a menu not drawn yet.
                    for (const action of ['preview', 'remove-from-set', 'delete']) await expect(menu.getByTestId(`context-menu-action-${action}`)).toBeVisible();
                    await expect(menu.getByTestId(`context-menu-action-read-alone-${GENERIC}`), 'no "Read alone with" the generic CSV: it does not read the statement').toHaveCount(0);
                    await expect(menu.locator('[data-testid^="context-menu-action-read-alone-"]'), 'nor with any other plugin').toHaveCount(0);
                    await waitForStillness(menu, 'the file menu');
                    await expect(menu).toBeInViewport();
                    await waitForMotionSettled(menu, 'the file menu');
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-report-set-file-menu');
                    // Escape, never an action: the set stays as it is. The next combination starts from a full load.
                    await page.keyboard.press('Escape');
                    await expect(menu).toHaveCount(0);
                }
            }
        });

        test('report set missing an export - all languages and themes', async ({page, request}, testInfo) => {
            // Account and upload ~20 s; per combination a full load, the wizard to Select Files and one shot,
            // ~12 s, twice that under parallel load: 8 × 24 s + 50 s.
            test.setTimeout(240_000);
            const viewport = getViewport(testInfo);
            const brokerId = await startAccount(page, request, 'Danske Bank');
            // The custody export alone: a set that misses its cash statement.
            const {
                batchId,
                files: [custody],
            } = await uploadSet(page.request, brokerId, [DANSKE_SAMPLES.custody]);
            // Premise, read from the server: the missing statement comes with the period it must cover — the card shows it only then.
            const missingCash = (await previewSet(page.request, brokerId, batchId)).missing.find((item) => item.role === 'cash');
            expect(Boolean(missingCash?.start && missingCash?.end), `premise: the preview names the period the cash statement must cover (${JSON.stringify(missingCash)})`).toBe(true);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await onTransactions(page, lang, theme);
                    const card = await openSetCard(page, brokerId, batchId, 'incomplete');
                    await expect(roleRow(card, 'custody', custody.file_id)).toBeVisible();
                    const missing = card.locator('[data-testid="report-set-missing"][data-role="cash"]');
                    await expect(missing, 'the card names the missing cash statement').toBeVisible();
                    await expect(card.getByTestId('report-set-missing')).toHaveCount(1);
                    await expect(missing.getByTestId('report-set-upload-missing')).toBeEnabled();
                    // Ticked and incomplete, the set holds the analysis back, and the footer says why.
                    await expect(page.getByTestId('import-wizard-set-blocks')).toHaveAttribute('data-reason', 'incomplete');
                    await expect(page.getByTestId('import-wizard-parse')).toBeDisabled();
                    await scrollToTop(card);
                    await expect(missing).toBeInViewport();
                    await freezeAnimations(page);
                    await waitForMotionSettled(page.getByTestId('import-wizard-modal'), 'the import wizard');
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-report-set-missing');
                }
            }
        });

        test('report set pairing and Align with the bank - all languages and themes', async ({page, request}, testInfo) => {
            // Account and upload ~20 s; per combination the wizard to the analysis (combine + parse, ≤60 s), the
            // detail, the walk to the review, the gap-fix request and two shots: ~35 s, more under load. The first
            // combination combines; the next ones reuse the identical combined file. 8 × 60 s + 100 s.
            test.setTimeout(600_000);
            const viewport = getViewport(testInfo);
            const brokerId = await startAccount(page, request, 'Danske Bank');
            // The gap set: two custody exports with a gap between them and one cash statement covering both — the
            // set whose analysis has rows left out (the table of reasons) and a truth point after the gap.
            const {batchId} = await uploadSet(page.request, brokerId, [DANSKE_SAMPLES.gapCustody1, DANSKE_SAMPLES.gapCustody2, DANSKE_SAMPLES.gapCash]);
            const point = (gapFix: Locator, kind: string, asOf: string) => gapFix.locator(`[data-testid="gapfix-summary"][data-kind="${kind}"][data-as-of="${asOf}"]`);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await onTransactions(page, lang, theme);
                    await openWizardOnSelectFiles(page);
                    await openBrokerPanel(page, brokerId);
                    const card = reportSetCard(page, brokerId, batchId);
                    await expect(card, 'the three exports are one complete set').toHaveAttribute('data-set-status', 'complete', {timeout: 20_000});
                    await tickWholeSet(card);
                    const parsed = await parseSelection(page);

                    // The set is one row of the analysis; its detail opens from the row's menu, on desktop and on touch.
                    const setRow = page
                        .getByTestId('import-wizard-step3')
                        .locator('tbody tr[data-row-id]')
                        .filter({has: page.getByTestId('parse-row-set')});
                    await expect(setRow, 'the set is one row of the analysis').toHaveCount(1);
                    await setRow.getByTestId(/^row-actions-/).click();
                    await page.getByTestId('context-menu-action-viewDetail').click();
                    const detail = page.getByTestId('parse-detail-modal');
                    await expect(detail).toBeVisible({timeout: 10_000});
                    const pairing = detail.getByTestId('parse-detail-pairing');
                    await expect(pairing, 'the detail of a set shows how its exports were matched').toBeVisible();
                    await expect(pairing.getByTestId('parse-detail-pairing-outcome'), 'one chip per outcome').toHaveCount(5);
                    await expect(pairing.getByTestId('parse-detail-pairing-reason').first(), 'the rows left out, by reason').toBeVisible();
                    await expect(pairing.getByTestId('parse-detail-pairing-reasons')).toBeInViewport();
                    await freezeAnimations(page);
                    await waitForMotionSettled(detail, 'the analysis detail');
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-report-set-pairing');
                    await detail.getByTestId('parse-detail-close').click();
                    await expect(detail).toHaveCount(0, {timeout: 10_000});

                    // To the review, then only the cash movements: nothing waits for an asset, and Import asks the bank's
                    // comparison (POST /gap-fix, which writes nothing). Its corrections reach no editor: Continue is never clicked.
                    const step4 = await walkToReview(page, parsed);
                    await keepOnlyCashRows(page, step4);
                    await page.getByTestId('import-wizard-import').click();
                    await expect(currentStep(page), 'Import on a report set stops on Align with the bank').toHaveAttribute('data-step-id', 'gapFix', {timeout: 60_000});
                    const gapFix = page.getByTestId('import-wizard-gapfix');
                    await expect(gapFix).toBeVisible();
                    const gapPoint = point(gapFix, 'gap', GAP_POINTS.gap);
                    const verificationPoint = point(gapFix, 'verification', GAP_POINTS.verification);
                    await expect(point(gapFix, 'opening', GAP_POINTS.opening), 'the starting point has its card').toHaveCount(1);
                    await expect(gapPoint, 'the point after the gap has its card').toHaveCount(1);
                    await expect(verificationPoint, 'the end-of-period check has its card').toHaveCount(1);
                    await expect(gapPoint, 'the point after the gap proposes a correction of its own').not.toHaveAttribute('data-proposals', '0');
                    // Every correction selected by default, and none hidden: no card is active, so the table lists them all.
                    await expect(gapFix.getByTestId('gapfix-point-details')).toHaveCount(0);
                    await expect(gapFix).toHaveAttribute('data-selected-count', (await gapFix.getAttribute('data-proposal-count')) ?? '');
                    const corrections = gapFix.locator('[data-testid="gapfix-table"] [data-testid="gapfix-proposal-toggle"]');
                    await expect(page.getByTestId('import-wizard-content')).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
                    // On desktop the three cards share one line under the step's intro, and the step starts the shot. On a
                    // phone they stack one per line and push the table below the fold: the card after the gap starts the
                    // shot instead (as far as the wizard's content scrolls), and the starting point may lie above it.
                    await scrollToTop(viewport === 'mobile' ? gapPoint : gapFix);
                    await expect(gapPoint, 'the point after the gap is in the shot').toBeInViewport();
                    await expect(verificationPoint, 'the end-of-period check is in the shot').toBeInViewport();
                    await expect(corrections.first(), 'the table of corrections is in the shot').toBeInViewport();
                    await waitForMotionSettled(page.getByTestId('import-wizard-modal'), 'the import wizard');
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-gapfix-step');
                }
            }
        });

        test('Files page report-set badges and Uploaded by filter - all languages and themes', async ({page, request}, testInfo) => {
            // Account and nine API calls ~20 s; per combination one page load and one filter, ~10 s, twice that
            // under parallel load: 8 × 20 s + 60 s.
            test.setTimeout(240_000);
            const viewport = getViewport(testInfo);
            const brokerId = await startAccount(page, request, 'Danske Bank');
            const api = page.request;
            // Over the API only, oldest first; the table lists the newest first.
            // B1: both exports, then combined — the combined file, and two originals "Used in a combined file".
            const b1 = await uploadSet(api, brokerId, [DANSKE_SAMPLES.custody, DANSKE_SAMPLES.cash]);
            const combined = await combineSet(api, brokerId, b1.batchId);
            // B2: the custody export alone — a set still missing its statement.
            const b2 = await uploadSet(api, brokerId, [DANSKE_SAMPLES.custody]);
            // B3: the gap set, uploaded last, so its three rows come first. The open filter lies over the top rows
            // of the table: these keep B1 and its combined file — the rows the shot is about — below it.
            const b3 = await uploadSet(api, brokerId, [DANSKE_SAMPLES.gapCustody1, DANSKE_SAMPLES.gapCustody2, DANSKE_SAMPLES.gapCash]);
            const [b1Custody, b1Cash] = b1.files;
            const [b2Custody] = b2.files;
            // The premises the badges stand on, read back (R8 of tx-import-report-set.spec.ts pins the badges themselves).
            const stored = new Map((await brimFilesOn(api, brokerId)).map((file) => [file.file_id, file]));
            for (const original of b1.files) expect(stored.get(original.file_id)?.combined_into ?? [], `${original.filename} of B1 went into the combined file`).toContain(combined.file_id);
            expect(stored.get(b2Custody.file_id)?.combined_into ?? [], 'the custody export of B2 was never combined').toEqual([]);
            const listed = [...[...b3.files].reverse(), b2Custody, combined, ...[...b1.files].reverse()];
            // The table holds what the page's own request returns: exactly these files, newest first — nothing of
            // another account, and no legacy file without a broker (that request lists those too).
            expect(
                (await brimFilesListed(api)).map((file) => file.file_id),
                'the Files page of the account lists exactly its seven files, newest first',
            ).toEqual(listed.map((file) => file.file_id));

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/files?tab=brim');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    const table = page.getByTestId('files-table-brim');
                    await expect(table).toBeVisible({timeout: 15_000});
                    await expect(table, 'the uploaders are named, not numbered').toHaveAttribute('data-users-state', 'ready', {timeout: 15_000});
                    const row = (fileId: string) => table.locator(`tbody tr[data-row-id="${fileId}"]`);
                    for (const file of listed) await expect(row(file.file_id), `${file.filename} is listed`).toHaveCount(1, {timeout: 10_000});
                    // `incomplete` waits for the preview of its set: once B2's is in, the badges have settled.
                    await expect(row(b2Custody.file_id).locator('[data-testid="file-set-badge"][data-kind="incomplete"]'), 'the lone custody export is an incomplete set').toBeVisible({timeout: 20_000});
                    await expect.poll(() => badgeKinds(row(combined.file_id)), {message: 'combined file'}).toEqual(['combined']);
                    for (const original of b1.files) await expect.poll(() => badgeKinds(row(original.file_id)), {message: `${original.filename} of B1`}).toEqual(['usedInCombined', 'set']);
                    for (const member of b3.files) await expect.poll(() => badgeKinds(row(member.file_id)), {message: `${member.filename} of the gap set`}).toEqual(['set']);

                    // Uploaded by, open: one uploader — the account — and nothing filtered yet. DataTableColumnFilter places its
                    // popover from the filter button's box, as it mounts and a frame later, and moves it on a scroll or a resize
                    // only: it is opened on a settled page, and asserted under its button before the shot — 8 px under it, the
                    // 4 px of its position and the 4 px of its margin (COLUMN_FILTER_GAP, galleryShot.ts), in every run.
                    const shot = `${viewport}/${lang}/${theme}/files/brim-report-sets`;
                    const filterButton = table.getByTestId('col-filter-trigger-uploader');
                    await settledToOpen(page, filterButton, shot);
                    await filterButton.click();
                    const filter = table.getByTestId('dt-header-uploader').getByTestId('column-filter');
                    await expect(filter).toBeVisible();
                    const uploader = filter.getByTestId(`filter-enum-option-${account?.user.id}`);
                    await expect(uploader, 'the filter lists the account as uploader').toBeVisible();
                    await expect(uploader).toHaveAttribute('data-checked', 'false');
                    await waitForMotionSettled(filter, 'the Uploaded by filter');
                    // On a phone the Report set column lies right of the screen: the table is scrolled to it, and the
                    // open filter follows its column. On desktop the column is in view and nothing moves.
                    await table.getByTestId('dt-header-reportSet').evaluate((element) => element.scrollIntoView({block: 'nearest', inline: 'nearest'}));
                    await boxStill(filter, `${shot}: the Uploaded by filter`);
                    await expectDropdownAt(filterButton, filter, COLUMN_FILTER_GAP, shot);
                    await expectUncovered(row(combined.file_id).locator('[data-testid="file-set-badge"][data-kind="combined"]'), 'the Combined badge');
                    await expectUncovered(row(b1Cash.file_id).locator('[data-testid="file-set-badge"][data-kind="usedInCombined"]'), 'the Used in a combined file badge');
                    await expectUncovered(row(b1Custody.file_id).locator('[data-testid="file-set-badge"][data-kind="set"]'), 'the Set of ‹date› badge');
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'files', 'brim-report-sets');
                }
            }
        });

        test('bulk editor todo banner leading to its row - all languages and themes', async ({page, request}, testInfo) => {
            // Account and upload ~20 s; per combination the wizard to the review (one parse, ≤60 s), the hand-over and
            // its validation, the banner and one shot: ~25 s, more under load. 8 × 50 s + 80 s.
            test.setTimeout(480_000);
            const viewport = getViewport(testInfo);
            // A broker that imports with the generic CSV, and a statement of cash movements only.
            const brokerId = await startAccount(page, request, 'Demo Bank', {opened_at: '2020-01-01', default_import_plugin: GENERIC});
            const statement = await uploadFile(page.request, brokerId, writeSavingsStatement(testInfo));
            // The generic CSV raises no todo on cash rows: the parse of this statement gains two fields to verify.
            const todos = await injectTodosIntoParses(page, SAVINGS_TODOS);
            const target = SAVINGS_TODOS[SAVINGS_TODOS.length - 1];
            try {
                for (const lang of SUPPORTED_LANGUAGES) {
                    await setBrowserLocale(page, lang);
                    for (const theme of THEMES) {
                        await onTransactions(page, lang, theme);
                        await openWizardOnSelectFiles(page);
                        await selectBrokerFile(page, {brokerId, fileId: statement.file_id});
                        const parsed = await parseSelection(page);
                        expect([...todos.injected].sort(), 'every injected todo found the row it names').toEqual(SAVINGS_TODOS.map((todo) => todo.description).sort());
                        expect(
                            parsed.field_todos?.map((todo) => todo.reason_code),
                            'the page received the injected todos',
                        ).toEqual(expect.arrayContaining(SAVINGS_TODOS.map((todo) => todo.reason_code)));
                        const step4 = await walkToReview(page, parsed);
                        await expect(step4, 'every movement of the statement is selected').toHaveAttribute('data-selected-count', String(SAVINGS_ROWS.length));
                        const importButton = page.getByTestId('import-wizard-import');
                        await expect(importButton).toBeEnabled({timeout: 15_000});

                        // The hand-over runs one validation: read before, awaited after, so the banners are final.
                        const root = page.getByTestId('tx-bulk-modal-root');
                        const runsBefore = await validateRuns(root);
                        await importButton.click();
                        await editorAfterHandoff(page);
                        await expect.poll(() => validateRuns(root), {message: 'the hand-over runs its validation', timeout: 30_000}).toBeGreaterThan(runsBefore);
                        await waitForSettled(root, 30_000);
                        // The hand-over's "N transactions imported to editor" toast lies over the editor's header. It came with
                        // the editor, in the same update: closed now, before the entry is clicked — afterwards nothing may stir.
                        await closeSuccessToasts(page);

                        // The banner of fields to verify folds its list by default, and its toggle publishes no state:
                        // whether the list is open is read from its entries, after the banner is on screen.
                        const banner = root.getByTestId('tx-bulk-todo-warnings');
                        await expect(banner).toBeVisible();
                        const entries = banner.getByTestId('tx-bulk-todo-goto');
                        if (!(await entries.first().isVisible())) await banner.getByTestId('tx-bulk-todo-warnings-toggle').click();
                        await expect(entries, 'one entry per field to verify').toHaveCount(SAVINGS_TODOS.length);
                        // The entry is the plugin's own message — data, not a translation.
                        const entry = entries.filter({hasText: target.message});
                        await expect(entry).toHaveCount(1);
                        const rowId = await entry.getAttribute('data-row-id');
                        const row = root.getByTestId('tx-bulk-body').locator(`tr[data-row-id="${rowId}"]`);
                        await expect(row).toHaveAttribute('data-highlighted', 'false');
                        // Frozen before the click: the highlight's pulse starts paused, on the same frame on every run.
                        await freezeAnimations(page);
                        await entry.click();
                        // From here nothing clicks or types: either clears the highlight (DataTable). The shot's settle only
                        // moves the pointer, off the editor (95% of the screen wide) to its parked spot, which clears nothing.
                        await expect(row, 'the entry leads to its row and highlights it').toHaveAttribute('data-highlighted', 'true');
                        await waitForStillness(row, 'the highlighted row');
                        await expect(row).toBeInViewport();
                        await expect(entry).toBeInViewport();
                        await waitForMotionSettled(page.getByTestId('tx-bulk-modal'), 'the bulk editor');
                        await expectNoToast(page);
                        await screenshot(page, viewport, lang, theme, 'transactions', 'bulk-todo-banner');
                        await closeEditorWithoutSaving(page, root);
                    }
                }
            } finally {
                if (!page.isClosed()) await todos.stop().catch(() => undefined);
            }
        });
    });

    test.describe('Media & Upload', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        test('image edit modal - crop view', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    // Navigate fresh each time to avoid leftover modal state
                    await navigateTo(page, '/files');
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await page.waitForTimeout(300);
                    await setLanguage(page, lang);
                    await page.getByTestId('files-tab-static').click();
                    await page.waitForTimeout(300);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Open upload area
                    await page.getByTestId('upload-button').click();
                    await expect(page.getByTestId('file-uploader')).toBeVisible({timeout: 3000});

                    // Add an image file via the hidden file input
                    const testImagePath = path.resolve(__dirname, '../static/icons/transactions/buy.png');
                    await page.getByTestId('file-input').setInputFiles(testImagePath);

                    // Wait for file to appear in pending list
                    await expect(page.locator('.file-item')).toBeVisible({timeout: 3000});

                    // Click the edit (pencil) button on the image file
                    const editBtn = page.getByTestId('file-edit-btn').first();
                    await expect(editBtn).toBeVisible({timeout: 2000});
                    await editBtn.click();

                    // Wait for ImageEditModal to appear and cropper to initialize
                    await expect(page.getByTestId('image-edit-modal')).toBeVisible({timeout: 5000});
                    const cropperReady = page.locator('[data-cropper-ready="true"]');
                    await cropperReady.waitFor({state: 'attached', timeout: 8000});
                    await page.waitForTimeout(800);

                    await screenshot(page, viewport, lang, theme, 'media', 'image-edit-modal');

                    // Close the modal to ensure clean state for next iteration
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    // If confirmation dialog appears, dismiss it
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                }
            }
        });

        test('asset picker modal - existing files', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    // Navigate fresh each iteration to ensure clean state
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // By name: the first card is whatever the list sorts first — Charles Schwab today, named here. Every step
                    // below is always drawn on this path for the admin: asserted, where a chain of probes used to skip the shot
                    // in silence under load.
                    await openBrokerCardByName(page, 'Charles Schwab');

                    // Click edit button to open BrokerModal
                    const editBtn = page.getByTestId('broker-edit-button');
                    await expect(editBtn).toBeVisible({timeout: 10_000});
                    await editBtn.click();
                    await expect(page.getByTestId('broker-modal')).toBeVisible({timeout: 5_000});

                    // Click on broker icon to open AssetPickerModal
                    const iconTrigger = page.getByTestId('broker-icon-trigger');
                    await expect(iconTrigger).toBeVisible({timeout: 5_000});
                    await iconTrigger.click();
                    const pickerModal = page.getByTestId('asset-picker-modal');
                    await expect(pickerModal).toBeVisible({timeout: 5_000});
                    // The files and their previews are the shot's settle's to wait for (its requests, its images); their
                    // order is the seed's.
                    await screenshot(page, viewport, lang, theme, 'media', 'asset-picker-modal');
                    // Close the picker and the broker modal; the next combination starts from a new load
                    await page.keyboard.press('Escape');
                    await page.keyboard.press('Escape');
                }
            }
        });

        test('file upload with pending files', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/files');
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await page.waitForTimeout(300);
                    await setLanguage(page, lang);
                    await page.getByTestId('files-tab-static').click();
                    await page.waitForTimeout(300);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Open upload area
                    await page.getByTestId('upload-button').click();
                    await expect(page.getByTestId('file-uploader')).toBeVisible({timeout: 3000});
                    await page.waitForTimeout(300);

                    await screenshot(page, viewport, lang, theme, 'media', 'file-uploader-empty');
                }
            }
        });
    });

    test.describe('FX', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        test('FX list page', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await goToFxPage(page);
                await selectOneYearDateRange(page);
                await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                await freezeAnimations(page);
                // Wait for charts (canvas) to render
                await page.waitForTimeout(2000);
                await screenshot(page, viewport, lang, theme, 'fx', 'list');
            });
        });

        test('FX list table', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Switch to table view: the button sets the view (it does not flip it), and publishes no state — the table,
                    // drawn only in the table view, is the end state.
                    const tableBtn = page.getByTestId('view-mode-list');
                    await expect(tableBtn).toBeVisible({timeout: 10_000});
                    await tableBtn.click();
                    await expect(page.getByTestId('fx-page').getByTestId('dt-header-pair'), 'the table view is on').toBeVisible({timeout: 10_000});
                    await screenshot(page, viewport, lang, theme, 'fx', 'list-table');
                }
            }
        });

        test('FX list filtered', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Apply currency filter (EUR)
                    const filterSelect = page.getByTestId('fx-currency-filter').first();
                    if (await appears(filterSelect, 2000)) {
                        await filterSelect.locator('[role="combobox"]').click();
                        await page.waitForTimeout(300);
                        const option = page.locator('[role="listbox"] button').filter({hasText: 'EUR'}).first();
                        if (await appears(option, 1000)) {
                            await option.click();
                            await page.waitForTimeout(1500); // Wait for charts to re-render
                        }
                    }
                    await screenshot(page, viewport, lang, theme, 'fx', 'list-filtered');
                }
            }
        });

        test('Add pair - direct routes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openAddPairModal(page);
                    const modal = page.getByTestId('fx-add-pair-modal');
                    const selects = modal.locator('[role="combobox"]');
                    await expect(selects.first()).toBeVisible({timeout: 3000});

                    // Select USD as base (not excluded — EUR is excluded because EUR-USD exists)
                    await selects.first().click();
                    await page.waitForTimeout(300);
                    const searchInput1 = modal.locator('input[type="text"]').first();
                    if (await searchInput1.isVisible({timeout: 500}).catch(() => false)) {
                        await searchInput1.fill('USD');
                        await page.waitForTimeout(400);
                    }
                    const usdOption = page.locator('[role="listbox"] button').filter({hasText: 'USD'}).first();
                    await expect(usdOption).toBeVisible({timeout: 2000});
                    await usdOption.click();
                    await page.waitForTimeout(500);

                    // Select CHF as quote (not excluded — FED provides USD→CHF direct)
                    await selects.nth(1).click();
                    await page.waitForTimeout(300);
                    const searchInput2 = modal.locator('input[type="text"]').first();
                    if (await searchInput2.isVisible({timeout: 500}).catch(() => false)) {
                        await searchInput2.fill('CHF');
                        await page.waitForTimeout(400);
                    }
                    const chfOption = page.locator('[role="listbox"] button').filter({hasText: 'CHF'}).first();
                    await expect(chfOption).toBeVisible({timeout: 2000});
                    await chfOption.click();

                    // Wait for route discovery to complete (loading spinner → route-select div)
                    const routeSelect = modal.locator('[data-testid="fx-route-select"]');
                    await routeSelect.waitFor({state: 'visible', timeout: 10_000});

                    // Open route picker to show discovered routes
                    const addRouteBtn = routeSelect
                        .locator('button')
                        .filter({hasText: /add|aggiungi|ajouter|añadir/i})
                        .first();
                    await addRouteBtn.waitFor({state: 'visible', timeout: 5000});
                    await addRouteBtn.click();

                    // Scroll modal body to bottom so picker content is in view
                    await modal.locator('.overflow-y-auto').evaluate((el) => (el.scrollTop = el.scrollHeight));

                    // Wait for direct routes section to render
                    await modal.locator('[data-testid="fx-route-direct-section"]').waitFor({state: 'visible', timeout: 5000});
                    await page.waitForTimeout(500); // Extra settle time for provider icons

                    await screenshot(page, viewport, lang, theme, 'fx', 'add-pair-routes');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                }
            }
        });

        test('Add pair - chain', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openAddPairModal(page);
                    const modal = page.getByTestId('fx-add-pair-modal');
                    const selects = modal.locator('[role="combobox"]');
                    await expect(selects.first()).toBeVisible({timeout: 3000});

                    // Select NOK as base (not excluded)
                    await selects.first().click();
                    await page.waitForTimeout(300);
                    const searchInput1 = modal.locator('input[type="text"]').first();
                    if (await searchInput1.isVisible({timeout: 500}).catch(() => false)) {
                        await searchInput1.fill('NOK');
                        await page.waitForTimeout(400);
                    }
                    const nokOption = page.locator('[role="listbox"] button').filter({hasText: 'NOK'}).first();
                    await expect(nokOption).toBeVisible({timeout: 2000});
                    await nokOption.click();
                    await page.waitForTimeout(500);

                    // Select CHF as quote (not excluded — chain route: ECB NOK→EUR + ECB EUR→CHF)
                    await selects.nth(1).click();
                    await page.waitForTimeout(300);
                    const searchInput2 = modal.locator('input[type="text"]').first();
                    if (await searchInput2.isVisible({timeout: 500}).catch(() => false)) {
                        await searchInput2.fill('CHF');
                        await page.waitForTimeout(400);
                    }
                    const chfOption = page.locator('[role="listbox"] button').filter({hasText: 'CHF'}).first();
                    await expect(chfOption).toBeVisible({timeout: 2000});
                    await chfOption.click();

                    // Wait for route discovery to complete (loading spinner → route-select div)
                    const routeSelect = modal.locator('[data-testid="fx-route-select"]');
                    await routeSelect.waitFor({state: 'visible', timeout: 10_000});

                    // Open route picker to show discovered chain routes
                    const addRouteBtn = routeSelect
                        .locator('button')
                        .filter({hasText: /add|aggiungi|ajouter|añadir/i})
                        .first();
                    await addRouteBtn.waitFor({state: 'visible', timeout: 5000});
                    await addRouteBtn.click();
                    await page.waitForTimeout(500); // Let Svelte render the picker

                    // Scroll modal body to bottom so picker content is in view
                    await modal.locator('.overflow-y-auto').evaluate((el) => (el.scrollTop = el.scrollHeight));

                    // Wait for chain routes section to render
                    const chainSection = modal.locator('[data-testid^="fx-route-chain-section"]').first();
                    await chainSection.waitFor({state: 'visible', timeout: 5000});

                    // The first chain group opens by itself only when the pair has no direct route (FxProviderSelect): a toggle,
                    // so its state is asked and it is opened only when closed. NOK/CHF has one — the SNB's, which quotes NOK
                    // (galleryOfflineData.ts) — so the group comes folded and is opened here. On its chevron, at the header's left
                    // edge: the header also holds a Tooltip (the chain warning's icon), which a click on it would pin instead.
                    const chainToggle = chainSection.getByTestId(/^fx-route-chain-toggle-\d+$/);
                    if ((await chainToggle.getAttribute('data-expanded')) !== 'true') {
                        const toggleBox = await chainToggle.boundingBox();
                        if (!toggleBox) throw new Error('the chain group toggle has no box');
                        await chainToggle.click({position: {x: 5, y: Math.round(toggleBox.height / 2)}});
                    }
                    await expect(chainToggle).toHaveAttribute('data-expanded', 'true');

                    // Click the first chain route item to add it — this shows the 2-step route in the selected panel. By the
                    // route's own test id: `fx-route-chain-` alone also names the group's toggle, which the click folded again.
                    // And on its "+", at the row's left edge — the button's 10 px padding plus half the 12 px icon: a click lands
                    // on an element's centre, which on a phone's narrow row is a provider badge. A badge is a Tooltip, and a
                    // mouse click on one pins it and stops there (Tooltip.svelte `toggle`): the route would never be added.
                    const selectedRoutes = modal.getByTestId('fx-route-selected');
                    const selectedBefore = await selectedRoutes.count();
                    const firstChainRoute = chainSection.getByTestId(/^fx-route-chain-\d+step-/).first();
                    await expect(firstChainRoute).toBeVisible();
                    const routeBox = await firstChainRoute.boundingBox();
                    if (!routeBox) throw new Error('the first chain route has no box');
                    await firstChainRoute.click({position: {x: 16, y: Math.round(routeBox.height / 2)}});
                    await expect(selectedRoutes, 'the chain route joins the selected routes').toHaveCount(selectedBefore + 1);

                    // Frame the routes block at the top of the modal body: the chain route just added — the selected list sits
                    // above the picker, and a route joins it at its end — the direct SNB route at the head of the picker, and the
                    // chain group opened under it. Scrolled to its bottom, the body would show the end of the picker instead.
                    await modal.getByTestId('fx-tour-providers').evaluate((block) => {
                        let body = block.parentElement;
                        while (body && getComputedStyle(body).overflowY !== 'auto') body = body.parentElement;
                        if (!body) throw new Error('the routes block sits in no scrolling body');
                        body.scrollTop += block.getBoundingClientRect().top - body.getBoundingClientRect().top - 8;
                    });
                    await expect(selectedRoutes.last(), 'the chain route just added is out of the frame').toBeInViewport({ratio: 1});
                    await expect(modal.getByTestId('fx-route-direct-SNB'), 'the direct SNB route is out of the frame').toBeInViewport({ratio: 1});
                    await expect(chainToggle, 'the opened chain group is out of the frame').toBeInViewport({ratio: 1});
                    // Then the pointer off the rows — they moved under it — and no tooltip over the shot, pinned or hovered.
                    await parkPointer(page);
                    await page.waitForTimeout(500); // Extra settle time for provider icons

                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole dialog, its body unscrolled.
                    if (viewport === 'desktop') await fitScreenToDialog(page, modal, `desktop/${lang}/${theme}/fx/add-pair-chain`);
                    await screenshot(page, viewport, lang, theme, 'fx', 'add-pair-chain');
                    await restoreTallScreen(page);
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                }
            }
        });

        test('Sync All modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Click sync all button
                    const syncBtn = page.getByTestId('fx-sync-all-button');
                    if (await appears(syncBtn, 2000)) {
                        await syncBtn.click();
                        // Wait for sync modal to appear and show progress
                        await page.waitForTimeout(1500);
                        await screenshot(page, viewport, lang, theme, 'fx', 'sync-progress');
                        // Close modal
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(200);
                    }
                }
            }
        });

        test('Detail page chart', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await goToFxDetailPage(page, 'EUR-USD');
                await selectOneYearDateRange(page);
                await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                await freezeAnimations(page);
                // Wait for ECharts canvas to render
                await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                await page.waitForTimeout(2000);
                await screenshot(page, viewport, lang, theme, 'fx', 'detail-chart');
            });
        });

        test('Detail signals overlay', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxDetailPage(page, 'EUR-USD');
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for chart canvas
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1500);

                    // Toggle signals panel
                    const signalsToggle = page.getByTestId('fx-detail-signals-toggle');
                    if (await appears(signalsToggle, 2000)) {
                        await signalsToggle.click();
                        await page.waitForTimeout(500);
                        // Scroll down to make signals panel content visible
                        const signalsPanel = page.getByTestId('fx-detail-signals-panel');
                        if (await appears(signalsPanel, 2000)) {
                            await signalsPanel.scrollIntoViewIfNeeded();
                            await page.waitForTimeout(300);
                        }
                    }
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole chart under the signals.
                    if (viewport === 'desktop') await extendScreenToBlock(page, page.getByTestId('fx-detail-chart'), `desktop/${lang}/${theme}/fx/detail-signals`);
                    await screenshot(page, viewport, lang, theme, 'fx', 'detail-signals');
                    await restoreTallScreen(page);
                }
            }
        });

        test('Detail measures panel', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxDetailPage(page, 'EUR-USD');
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for chart canvas
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1500);

                    // Toggle measures panel
                    const measuresToggle = page.getByTestId('fx-detail-measures-toggle');
                    if (await appears(measuresToggle, 2000)) {
                        await measuresToggle.click();
                        await page.waitForTimeout(500);
                    }
                    await screenshot(page, viewport, lang, theme, 'fx', 'detail-measures');
                }
            }
        });

        test('Detail data editor', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxDetailPage(page, 'EUR-USD');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for chart canvas
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    // Click edit button to open data editor
                    const editBtn = page.getByTestId('fx-detail-edit-btn');
                    if (await appears(editBtn, 2000)) {
                        await editBtn.click();
                        await page.waitForTimeout(500);
                        // Scroll to editor panel for full view
                        const editorPanel = page.getByTestId('fx-detail-editor-panel');
                        if (await appears(editorPanel, 2000)) {
                            await editorPanel.scrollIntoViewIfNeeded();
                            await page.waitForTimeout(300);
                        }
                    }
                    await screenshot(page, viewport, lang, theme, 'fx', 'detail-editor');
                }
            }
        });

        test('Detail CSV import modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxDetailPage(page, 'EUR-USD');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for chart
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    // Open data editor first
                    const editBtn = page.getByTestId('fx-detail-edit-btn');
                    await editBtn.scrollIntoViewIfNeeded();
                    await expect(editBtn).toBeVisible({timeout: 3000});
                    await editBtn.click();
                    await page.waitForTimeout(800);

                    // Scroll to editor panel to make Import CSV button visible
                    const editorPanel = page.getByTestId('fx-detail-editor-panel');
                    await editorPanel.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(300);

                    // Click Import CSV button
                    const importBtn = page.getByTestId('fx-data-import-btn');
                    await importBtn.scrollIntoViewIfNeeded();
                    await expect(importBtn).toBeVisible({timeout: 3000});
                    await importBtn.click();
                    const importModal = page.getByTestId('data-import-modal');
                    await expect(importModal).toBeVisible({timeout: 3000});
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'fx', 'detail-csv-import');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('Chart settings modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await page.waitForTimeout(1500);

                    // Click chart settings button (scroll to it first)
                    const settingsBtn = page.getByTestId('fx-chart-settings-button');
                    await settingsBtn.scrollIntoViewIfNeeded();
                    await expect(settingsBtn).toBeVisible({timeout: 3000});
                    await settingsBtn.click();
                    const settingsModal = page.getByTestId('chart-settings-modal');
                    await expect(settingsModal).toBeVisible({timeout: 3000});
                    await page.waitForTimeout(300);
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts).
                    if (viewport === 'desktop') await fitScreenToDialog(page, settingsModal, `desktop/${lang}/${theme}/fx/chart-settings`);
                    await screenshot(page, viewport, lang, theme, 'fx', 'chart-settings');
                    await restoreTallScreen(page);
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('Provider config modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToFxDetailPage(page, 'EUR-USD');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await page.waitForTimeout(1000);

                    // Click provider button (scroll to it first)
                    const providerBtn = page.getByTestId('fx-detail-provider-btn');
                    await providerBtn.scrollIntoViewIfNeeded();
                    await expect(providerBtn).toBeVisible({timeout: 3000});
                    await providerBtn.click();
                    // Wait for the inner modal (FxPairAddModal in editMode)
                    const addPairModal = page.getByTestId('fx-add-pair-modal');
                    await expect(addPairModal).toBeVisible({timeout: 5000});
                    await page.waitForTimeout(2000); // Extra time for provider icons and route loading
                    await screenshot(page, viewport, lang, theme, 'fx', 'provider-config');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });
    });

    test.describe('Assets', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        // Gallery target: Apple Inc. — has 30 days of price history from db populate. Its exact display name: the detail shots
        // find its card by its id, read by this name (openGalleryAsset).
        const GALLERY_ASSET = 'Apple Inc.';

        test('Asset list page', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                const polled = galleryOfflineGuard(page).pricedPolls;
                await goToAssetsPage(page);
                await selectOneYearDateRange(page);
                await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                // The live prices are not part of the list's data-busy: wait for this load's, drawn on the cards.
                await expectOfflinePricesDrawn(page, polled, lang);
                await freezeAnimations(page);
                await page.waitForTimeout(1500);
                await screenshot(page, viewport, lang, theme, 'assets', 'list');
            });
        });

        test('Asset list table', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    const polled = galleryOfflineGuard(page).pricedPolls;
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await expectOfflinePricesDrawn(page, polled, lang);
                    await freezeAnimations(page);

                    // Switch to table view: the button sets the view (it does not flip it), and publishes no state — the table's
                    // own panel, drawn only in the table view, is the end state.
                    const tableBtn = page.getByTestId('view-mode-list');
                    await expect(tableBtn).toBeVisible({timeout: 10_000});
                    await tableBtn.click();
                    await expect(page.getByTestId('assets-table-panel-own'), 'the table view is on').toBeVisible({timeout: 10_000});
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts).
                    if (viewport === 'desktop') await extendScreenToBlock(page, page.getByTestId('assets-table-panel-own'), `desktop/${lang}/${theme}/assets/list-table`);
                    await screenshot(page, viewport, lang, theme, 'assets', 'list-table');
                    await restoreTallScreen(page);
                }
            }
        });

        test('Asset list filtered', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // A card the search removes: the barrier that the list has applied it (below).
            const outsideTheSearch = await assetIdByName(page, GALLERY_ASSET);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    const polled = galleryOfflineGuard(page).pricedPolls;
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    // Before the search, while every card stands still: the ETFs it keeps show the fixture's prices.
                    await expectOfflinePricesDrawn(page, polled, lang);
                    await freezeAnimations(page);

                    // Type search text. The list applies it 300 ms after the typing (handleSearchInput), and its data-busy does
                    // not cover that wait: the barrier is Apple Inc.'s card — its name has no «ETF» — there before the typing,
                    // and gone after it.
                    const searchInput = page.getByTestId('assets-search-input');
                    await expect(searchInput).toBeVisible({timeout: 10_000});
                    const removedCard = page.getByTestId(`asset-card-${outsideTheSearch}`);
                    await expect(removedCard, `${GALLERY_ASSET} is on the list before the search`).toBeVisible({timeout: 10_000});
                    await searchInput.fill('ETF');
                    await expect(searchInput).toHaveValue('ETF');
                    await expect(removedCard, `the search has applied: ${GALLERY_ASSET} has left the list`).toHaveCount(0, {timeout: 10_000});
                    await screenshot(page, viewport, lang, theme, 'assets', 'list-filtered');
                }
            }
        });

        test('Asset detail chart', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    // Screenshot 1: line chart (default), drawn — the shot's settle waits for it to stand still.
                    const detailChart = page.getByTestId('asset-detail-chart');
                    await waitForChart(detailChart, 30_000);
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts), for this shot and the candlestick's.
                    if (viewport === 'desktop') await extendScreenToBlock(page, detailChart, `desktop/${lang}/${theme}/assets/detail-chart`);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-chart');
                    await restoreTallScreen(page);

                    // Screenshot 2: candlestick chart. The chart offers it on a price history with OHLC, which the seed gives Apple.
                    await switchAssetChartType(detailChart, 'candlestick');
                    await freezeAnimations(page);
                    if (viewport === 'desktop') await extendScreenToBlock(page, detailChart, `desktop/${lang}/${theme}/assets/detail-chart-candlestick`);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-chart-candlestick');
                    await restoreTallScreen(page);
                    // Back to the line chart: a page-local state, which the next combination's load resets as well.
                    await switchAssetChartType(detailChart, 'line');
                }
            }
        });

        /** The mark switchAssetChartType leaves on the chart's drawings before a switch: the one the switch replaces must go. */
        const BEFORE_SWITCH = 'data-gallery-before-switch';

        /**
         * Where the asset chart draws as `type` (PriceChartFull): the candles in CandlestickChart's drawing (`candlestick-chart`),
         * the line in the chart's other drawing — the only other element of the chart that counts its renders (attachChartReady).
         */
        function assetChartDrawing(type: 'line' | 'candlestick'): string {
            return type === 'candlestick' ? '[data-testid="candlestick-chart"][data-chart-renders]' : '[data-chart-renders]:not([data-testid="candlestick-chart"])';
        }

        /**
         * Switch the asset chart to `type` and return once ECharts has drawn it. PriceChartFull draws each type in a drawing of
         * its own (`{#if chartType === 'line'} … {:else} <CandlestickChart> …`): a switch replaces the drawing, and the new one
         * comes with its own ECharts instance and its own render counter, from 0 (attachChartReady). A counter read across the
         * switch compared two drawings — the candles' 3 never passed the line's 6. So every drawing of the chart is marked before
         * the click; after it the new type's drawing is the one without the mark, and it must have drawn (`data-chart-ready`),
         * and the old type's, marked, must be gone. The type must really change: the chart draws the other one before the click.
         */
        async function switchAssetChartType(detailChart: Locator, type: 'line' | 'candlestick'): Promise<void> {
            const from = type === 'candlestick' ? 'line' : 'candlestick';
            const button = detailChart.getByTestId(`chart-type-${type}`);
            await expect(button, `the chart offers the ${type} type`).toBeVisible({timeout: 10_000});
            await expect(detailChart.locator(assetChartDrawing(from)), `the chart draws as ${from} before the switch to ${type}`).toHaveCount(1);
            await detailChart.locator('[data-chart-renders]').evaluateAll((drawings, mark) => {
                for (const drawing of drawings) drawing.setAttribute(mark, '');
            }, BEFORE_SWITCH);
            await button.click();
            const drawn = detailChart.locator(`${assetChartDrawing(type)}:not([${BEFORE_SWITCH}])`);
            await expect(drawn, `the chart never redrew as ${type}: no drawing of its own replaced the ${from} one`).toHaveCount(1, {timeout: 15_000});
            await expect(drawn, `the chart never redrew as ${type}`).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
            await expect(detailChart.locator(`${assetChartDrawing(from)}[${BEFORE_SWITCH}]`), `the ${from} drawing the switch to ${type} replaces is still on the page`).toHaveCount(0);
        }

        /**
         * Open the Signals panel above the chart — a toggle that publishes its state (`aria-expanded`): clicked only when folded,
         * its end state asserted — and return it once its pickers are on it: they come with the signal catalogue, after the panel.
         */
        async function openSignalsPanel(page: Page): Promise<Locator> {
            const toggle = page.getByTestId('asset-detail-signals-toggle');
            await expect(toggle).toBeVisible({timeout: 15_000});
            if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
            await expect(toggle).toHaveAttribute('aria-expanded', 'true');
            const panel = page.getByTestId('asset-detail-signals-panel');
            await expect(panel).toBeVisible();
            await expect(panel.getByTestId('signals-indicator-select-button'), 'the signal catalogue has loaded').toBeVisible({timeout: 15_000});
            return panel;
        }

        // The comparison asset of the rolling-return shot: a benchmark quoted in Apple's own currency (USD), so its
        // rolling return needs no FX conversion, and seeded over the same dates as Apple (populate_mock_data.py).
        const ROLLING_RETURN_PEER = 'S&P 500';

        /** The id of the asset named exactly `displayName`: found by its name, never by its position. */
        async function assetIdByName(page: Page, displayName: string): Promise<number> {
            const response = await page.request.get(`/api/v1/assets/query?search=${encodeURIComponent(displayName)}`);
            expect(response.ok(), `GET /api/v1/assets/query?search=${displayName} answered HTTP ${response.status()}`).toBe(true);
            const match = ((await response.json()) as Array<{id: number; display_name: string}>).find((asset) => asset.display_name === displayName);
            if (!match) throw new Error(`Asset "${displayName}" not found. Check populate_mock_data.py seeding.`);
            return match.id;
        }

        /**
         * Open the detail page of the asset named exactly `displayName` from the asset list the page is on: the gallery's form of
         * navigateToAssetByName (assets-helpers.ts), which asks with instant probes and clicks whichever card comes first.
         *
         * The card clicked is the asset's own (`asset-card-<id>`, the id read from the API), on the list as it loaded — no
         * search. The detail page's ‹ n/N › follows the list the user left (AssetBrowseNav, source `list`), and the list applies
         * a search 300 ms after the typing (`handleSearchInput`), outside its `data-busy`: a click before the search had applied
         * left from the whole list, «1/16» in the header, and one after it from the single hit, with no arrows at all. The header
         * changed height, and everything under it moved (plan 56, class F). From the whole list the header carries, in every run,
         * the arrows the detail page's documentation describes.
         *
         * Ends on the asset's page loaded (`data-busy` false) and its arrows decided (`asset-browse`: ready, following the list):
         * they no longer come in after the rest of the page has drawn. Returns the asset's id.
         */
        async function openGalleryAsset(page: Page, displayName: string): Promise<number> {
            const assetId = await assetIdByName(page, displayName);
            // Settled, the list has published the order the detail page follows (AssetBrowseOrder).
            await waitForSettled(page.getByTestId('assets-page'), 20_000);
            const card = page.getByTestId(`asset-card-${assetId}`);
            await expect(card, `${displayName} has its card on the asset list`).toBeVisible({timeout: 15_000});
            await card.click();
            await expect(page, `the card opened ${displayName}'s page`).toHaveURL(new RegExp(`/assets/${assetId}(?:[?#]|$)`), {timeout: 15_000});
            const detail = page.getByTestId('asset-detail-page');
            await expect(detail).toBeVisible({timeout: 20_000});
            await expect(detail, `${displayName}'s page has loaded`).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
            const browse = page.getByTestId('asset-browse');
            await expect(browse, 'the ‹ n/N › arrows are decided').not.toHaveAttribute('data-state', 'pending', {timeout: 15_000});
            await expect(browse, 'the arrows follow the list the page was opened from').toHaveAttribute('data-source', 'list');
            await expect(browse, 'the arrows are shown: the list holds more than this asset').toHaveAttribute('data-state', 'ready');
            return assetId;
        }

        /**
         * How many values the asset chart draws for its series named `name`, 0 when it draws none. Read from the
         * ECharts instance PriceChartFull publishes as `__lfChart` on the element that carries data-chart-ready.
         * An overlay series spans every date of the chart, with null where it has no value: only values count.
         */
        async function drawnSeriesPoints(chart: Locator, name: string): Promise<number> {
            return chart
                .locator('[data-chart-ready]')
                .first()
                .evaluate((host, seriesName) => {
                    type LfChart = {getOption: () => {series?: Array<{name?: unknown; data?: unknown}>}};
                    const data = (host as unknown as {__lfChart?: LfChart}).__lfChart?.getOption().series?.find((candidate) => candidate?.name === seriesName)?.data;
                    return Array.isArray(data) ? data.filter((value) => value !== null && value !== undefined).length : 0;
                }, name);
        }

        test('Asset detail rolling return - all languages and themes', async ({page}, testInfo) => {
            // Eight combos, each loading the detail page and reading the rolling return after every step: above the
            // default budget under load.
            test.setTimeout(360_000); // 6 minutes
            const viewport = getViewport(testInfo);
            const peerId = await assetIdByName(page, ROLLING_RETURN_PEER);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await resetChartSettings(page); // no comparison and the default window: each step below is a real change
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await openGalleryAsset(page, GALLERY_ASSET);

                    // Page range 1W, strictly; it persists in the session. A 1Y window needs a full year of prices
                    // before the first day it draws, and the seeded history starts a week before the first mock
                    // deposit (populate_mock_data.py, _seed_market_start_date: 2025-09-23). Over a 1Y range almost
                    // every point lacks its reference and the chart is partial; over the last week none does.
                    const week = page.getByTestId('date-preset-1w');
                    await expect(week).toBeVisible({timeout: 10_000});
                    if ((await week.getAttribute('data-active')) !== 'true') await week.click();
                    await expect(week).toHaveAttribute('data-active', 'true');

                    // The primary mode and the window are toggles: each is switched only when it is not on already.
                    const detail = page.getByTestId('asset-detail-page');
                    const chart = detail.getByTestId('asset-detail-chart');
                    const rollingReturn = chart.getByTestId('asset-chart-primary-calendar-return');
                    await expect(rollingReturn).toBeVisible({timeout: 15_000});
                    if ((await rollingReturn.getAttribute('aria-pressed')) !== 'true') await rollingReturn.click();
                    await expect(rollingReturn).toHaveAttribute('aria-pressed', 'true');
                    await expect(chart).toHaveAttribute('data-primary-mode', 'calendar-return');
                    const oneYear = chart.getByTestId('asset-calendar-window-controls').getByTestId('asset-calendar-window-1y');
                    await expect(oneYear).toBeVisible();
                    if ((await oneYear.getAttribute('aria-pressed')) !== 'true') await oneYear.click();
                    await expect(oneYear).toHaveAttribute('aria-pressed', 'true');
                    await expect(chart).toHaveAttribute('data-window-days', '365');

                    // One comparison asset, added the way a user adds it: Signals, Comparison, asset comparison, then
                    // the asset in the new card. In this mode the panel offers comparisons only.
                    const signalsToggle = detail.getByTestId('asset-detail-signals-toggle');
                    if ((await signalsToggle.getAttribute('aria-expanded')) !== 'true') await signalsToggle.click();
                    await expect(signalsToggle).toHaveAttribute('aria-expanded', 'true');
                    const signalsPanel = detail.getByTestId('asset-detail-signals-panel');
                    // The Comparison picker renders once the signal catalog has loaded.
                    const comparisonPicker = signalsPanel.getByTestId('signals-comparison-select-button');
                    await expect(comparisonPicker).toBeVisible({timeout: 15_000});
                    const cards = signalsPanel.locator('[data-testid^="signal-card-"]');
                    await expect(cards, 'a signal survived resetChartSettings()').toHaveCount(0);
                    await comparisonPicker.click();
                    await signalsPanel.getByTestId('signal-tree-option-asset-comparison').click();
                    const card = signalsPanel.locator('[data-testid^="signal-card-"][data-signal-type="asset-comparison"]');
                    await expect(card).toHaveCount(1);
                    const signalId = (await card.getAttribute('data-testid'))?.slice('signal-card-'.length);
                    if (!signalId) throw new Error('the new comparison card carries no signal id');
                    const assetPicker = card.getByTestId(`signal-param-${signalId}-assetId-select`);
                    const assetTrigger = assetPicker.getByTestId(`signal-param-${signalId}-assetId-select-trigger`);
                    await optionsClosed(page); // search-select-option-* names a kind of row: no other list may be open
                    await assetTrigger.click();
                    await expect(assetTrigger).toHaveAttribute('aria-expanded', 'true');
                    // Narrowed by name, as a user would: the row is then at the top of the list.
                    const assetSearch = assetPicker.getByTestId(`signal-param-${signalId}-assetId-select-search`);
                    await assetSearch.fill(ROLLING_RETURN_PEER);
                    await expect(assetSearch).toHaveValue(ROLLING_RETURN_PEER);
                    await assetPicker.getByTestId(`search-select-option-${peerId}`).click();
                    await expect(assetTrigger).toHaveAttribute('aria-expanded', 'false');
                    await optionsClosed(page);

                    // Loaded, in the order that gives each check its meaning: the comparison is listed ready only once
                    // its own answer is in, then the main series is ready and the page idle — and only then are the
                    // states that must not be on screen asked about.
                    await expect(chart, `${ROLLING_RETURN_PEER} has no ready rolling return`).toHaveAttribute('data-calendar-comparison-ready', String(peerId), {timeout: 30_000});
                    await expect(chart).toHaveAttribute('data-series-state', 'ready', {timeout: 30_000});
                    await expect(detail).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
                    for (const state of ['partial', 'unavailable', 'error'] as const) await expect(chart).toHaveAttribute(`data-calendar-comparison-${state}`, '');
                    for (const state of ['loading', 'partial', 'unavailable', 'error'] as const) await expect(chart.getByTestId(`asset-calendar-return-${state}`)).toBeHidden();
                    // Drawn: the chart has painted, and the comparison line has points.
                    await waitForChart(chart);
                    await expect.poll(() => drawnSeriesPoints(chart, ROLLING_RETURN_PEER), {message: `the chart draws no ${ROLLING_RETURN_PEER} line`, timeout: 10_000}).toBeGreaterThan(0);

                    // Framed from the top of the page, the chart 8 px under the screen's edge — or as near as the page's end allows,
                    // the same in every run: the bare centring it replaces came from wherever the clicks above had left the page,
                    // so the header was back over the frame when the centring scrolled up, and gone when it scrolled down.
                    await frameTarget(page, chart, `${viewport}/${lang}/${theme}/assets/detail-chart-rolling-return`);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-chart-rolling-return');
                }
            }
        });

        test('Asset detail signals', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);

                    // The Signals panel open, with its pickers
                    await openSignalsPanel(page);
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole chart under the signals.
                    if (viewport === 'desktop') await extendScreenToBlock(page, page.getByTestId('asset-detail-chart'), `desktop/${lang}/${theme}/assets/detail-signals`);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals');
                    await restoreTallScreen(page);
                }
            }
        });

        test('Asset detail signals EMA - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);

                    // Open signals panel and add EMA indicator via the grouped SignalTreeSelect
                    await openSignalsPanel(page);

                    await selectIndicatorFromTree(page, 'trend', 'ema', `${viewport}/${lang}/${theme}/assets/detail-signals-ema`);
                    await waitForSignalCardsSettled(page);
                    // Scroll the chart into center of viewport; the shot's settle waits for the overlay's redraw to stand still
                    await page.getByTestId('asset-detail-chart').evaluate((el) => el.scrollIntoView({block: 'center'}));
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-ema');
                }
            }
        });

        test('Asset detail signals RSI - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);

                    await openSignalsPanel(page);

                    await selectIndicatorFromTree(page, 'momentum', 'rsi', `${viewport}/${lang}/${theme}/assets/detail-signals-rsi`);
                    await waitForSignalCardsSettled(page);
                    // Scroll the chart into center of viewport (not just into view)
                    await page.getByTestId('asset-detail-chart').evaluate((el) => el.scrollIntoView({block: 'center'}));
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-rsi');
                }
            }
        });

        test('Asset detail signals MACD - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);

                    await openSignalsPanel(page);

                    await selectIndicatorFromTree(page, 'momentum', 'macd', `${viewport}/${lang}/${theme}/assets/detail-signals-macd`);
                    await waitForSignalCardsSettled(page);
                    // Scroll the chart into center of viewport
                    await page.getByTestId('asset-detail-chart').evaluate((el) => el.scrollIntoView({block: 'center'}));
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-macd');
                }
            }
        });

        test('Asset detail signals Bollinger - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);

                    await openSignalsPanel(page);

                    await selectIndicatorFromTree(page, 'volatility', 'bollinger', `${viewport}/${lang}/${theme}/assets/detail-signals-bollinger`);
                    await waitForSignalCardsSettled(page);
                    await page.getByTestId('asset-detail-chart').evaluate((el) => el.scrollIntoView({block: 'center'}));
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-bollinger');
                }
            }
        });

        test('Asset detail signals tree select open - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);

                    const shot = `${viewport}/${lang}/${theme}/assets/detail-signals-tree`;
                    const signalsPanel = await openSignalsPanel(page);

                    // Open the grouped indicator dropdown: family groups with count badges +
                    // search box. The first family (trend) opens expanded on open — the shot
                    // shows both an expanded family with options and the collapsed others.
                    // TreeSelect places the dropdown once, from its root's box at the click (updatePosition), and moves it on a
                    // scroll or a resize only: opened while the page above still moved, it hung 4 px off its trigger in one run
                    // and not in the other. So it is opened on a settled page, let stand still, and asserted where TreeSelect
                    // puts it — 4 px under its root, or above it — before the shot: a misplaced one fails with both boxes.
                    const indicatorSelect = signalsPanel.getByTestId('signals-indicator-select');
                    const selectButton = signalsPanel.getByTestId('signals-indicator-select-button');
                    await selectButton.scrollIntoViewIfNeeded();
                    await settledToOpen(page, indicatorSelect, shot);
                    await selectButton.click();
                    await expect(selectButton, 'the indicator dropdown is open').toHaveAttribute('aria-expanded', 'true');
                    const treeId = await selectButton.getAttribute('aria-controls');
                    if (!treeId) throw new Error(`${shot}: the indicator select names no dropdown (aria-controls)`);
                    const tree = page.locator(`[id="${treeId}"]`);
                    await expect(tree).toBeVisible();
                    const trendGroup = tree.getByTestId('signal-tree-group-trend');
                    await expect(trendGroup).toBeVisible({timeout: 3_000});
                    await expect(trendGroup).toHaveAttribute('aria-expanded', 'true', {timeout: 3_000});
                    await expect(tree.getByTestId('signal-tree-option-sma')).toBeVisible({timeout: 3_000});
                    await boxStill(tree, `${shot}: the open dropdown`);
                    await expectDropdownAt(indicatorSelect, tree, DROPDOWN_GAP, shot);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-tree');
                    // Close the dropdown without selecting; the next combination starts from a new load
                    await page.keyboard.press('Escape');
                }
            }
        });

        test('Asset detail signals drawdown - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);

                    await openSignalsPanel(page);

                    // Underwater Drawdown card with its Full history toggle (risk family)
                    await selectIndicatorFromTree(page, 'risk', 'risk-drawdown', `${viewport}/${lang}/${theme}/assets/detail-signals-drawdown`);
                    await waitForSignalCardsSettled(page, 45_000); // full-history load is heavier
                    const fullHistoryParam = page.getByTestId('signal-param-full_history');
                    await expect(fullHistoryParam).toBeVisible({timeout: 5_000});
                    await fullHistoryParam.scrollIntoViewIfNeeded();
                    await freezeAnimations(page);
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole chart under the card.
                    if (viewport === 'desktop') await extendScreenToBlock(page, page.getByTestId('asset-detail-chart'), `desktop/${lang}/${theme}/assets/detail-signals-drawdown`);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-drawdown');
                    await restoreTallScreen(page);
                }
            }
        });

        test('Asset chart settings modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await page.waitForTimeout(1000);

                    // Global-scope chart settings from the Assets list toolbar (live preview)
                    const settingsBtn = page.getByTestId('assets-chart-settings-button');
                    await settingsBtn.scrollIntoViewIfNeeded();
                    await expect(settingsBtn).toBeVisible({timeout: 3_000});
                    await settingsBtn.click();
                    const settingsModal = page.getByTestId('chart-settings-modal');
                    await expect(settingsModal).toBeVisible({timeout: 5_000});
                    // Wait for the live preview chart to paint
                    await settingsModal
                        .locator('canvas')
                        .first()
                        .waitFor({state: 'visible', timeout: 8_000})
                        .catch(() => {});
                    await page.waitForTimeout(500);
                    await freezeAnimations(page);
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts).
                    if (viewport === 'desktop') await fitScreenToDialog(page, settingsModal, `desktop/${lang}/${theme}/assets/chart-settings`);
                    await screenshot(page, viewport, lang, theme, 'assets', 'chart-settings');
                    await restoreTallScreen(page);
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('Asset detail event popover - all languages and themes', async ({page}, testInfo) => {
            // Mocked chart + bounded hover sweep × 8 combos — above the default budget under load.
            test.setTimeout(360_000); // 6 minutes
            const viewport = getViewport(testInfo);

            // The chart canvas gives markers no DOM handle, so make the geometry known:
            // mock the bulk price query with a gentle linear ramp and a single DIVIDEND at
            // the exact mid date → the marker sits at the grid's centre, and a small hover
            // sweep around the canvas centre hits it deterministically.
            const today = new Date();
            const dayMs = 24 * 60 * 60 * 1000;
            const fmt = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
            const days = 240; // ~8 months of daily points — comfortably "daily" resolution
            const dates: string[] = [];
            for (let i = days - 1; i >= 0; i--) dates.push(fmt(new Date(today.getTime() - i * dayMs)));
            const midDate = dates[Math.floor(dates.length / 2)];
            // What the price-query route saw and answered, one entry per request: the asset ids
            // ("+events" where include_events was asked) and how many events the mock returned.
            // Read back only by the diagnostics below, when the event marker cannot be shown.
            const priceQueries: Array<{assets: string[]; eventsReturned: number}> = [];
            await page.route('**/api/v1/assets/prices/query', async (route) => {
                // The assets LIST also bulk-queries prices (per-card sparklines) before we
                // reach the detail page — answer every requested item, not just Apple's.
                // postDataJSON throws on an empty/non-JSON body; an unhandled throw leaves the
                // request pending forever and the page stuck at data-busy — fall back to [].
                let postData: Array<{asset_id?: number; target_currency?: string; include_events?: boolean}> = [];
                try {
                    postData = route.request().postDataJSON() ?? [];
                } catch {
                    postData = [];
                }
                const items = postData.map((item) => {
                    const currency = item?.target_currency ?? 'USD';
                    return {
                        asset_id: item?.asset_id ?? 0,
                        prices: dates.map((d, i) => ({date: d, close: (100 + i * 0.2).toFixed(4), currency})),
                        events: item?.include_events ? [{date: midDate, type: 'DIVIDEND', value: {code: currency, amount: '2.5000'}, notes: 'Gallery demo dividend', id: 1, is_auto: false}] : [],
                        errors: [],
                        signals: [],
                    };
                });
                priceQueries.push({assets: postData.map((item) => `${item?.asset_id ?? '?'}${item?.include_events ? '+events' : ''}`), eventsReturned: items.reduce((total, item) => total + item.events.length, 0)});
                await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({items})});
            });

            // What the price chart behind `canvas` draws, read through the `__lfChart` handle
            // PriceChartFull exposes for E2E tooling — and, with `showTip`, the first event marker's
            // tooltip driven directly instead of hovered. It reports instead of returning silently.
            type LfChart = {getOption: () => {series?: Array<{name?: unknown; data?: unknown}>; dataZoom?: Array<{start?: unknown; end?: unknown}>}; dispatchAction: (action: {type: string; seriesIndex: number; dataIndex: number}) => void};
            type ChartReading = {chartFound: boolean; series: string[]; eventPoints: number; firstEvent: string | null; zoom: string | null; tipDispatched: boolean};
            const inspectEventChart = (canvas: Locator, showTip = false): Promise<ChartReading> =>
                canvas.evaluate((el, dispatch): ChartReading => {
                    let node: Element | null = el;
                    let chart: LfChart | null = null;
                    while (node && !chart) {
                        chart = (node as unknown as {__lfChart?: LfChart}).__lfChart ?? null;
                        node = node.parentElement;
                    }
                    if (!chart) return {chartFound: false, series: [], eventPoints: 0, firstEvent: null, zoom: null, tipDispatched: false};
                    const option = chart.getOption();
                    const series = (option.series ?? []).map((s) => ({name: String(s?.name ?? ''), data: Array.isArray(s?.data) ? (s.data as unknown[]) : []}));
                    const eventSeries = series.filter((s) => s.name.startsWith('Events: '));
                    const tipIndex = series.findIndex((s) => s.name.startsWith('Events: ') && s.data.length > 0);
                    if (dispatch && tipIndex >= 0) chart.dispatchAction({type: 'showTip', seriesIndex: tipIndex, dataIndex: 0});
                    const first = (tipIndex >= 0 ? series[tipIndex].data[0] : undefined) as {value?: unknown[]; marker?: {value?: unknown}; bucketValue?: unknown} | undefined;
                    const zoom = option.dataZoom?.[0];
                    return {
                        chartFound: true,
                        series: series.map((s) => `${s.name} [${s.data.length}]`),
                        eventPoints: eventSeries.reduce((total, s) => total + s.data.length, 0),
                        firstEvent: first ? `${String(first.value?.[0])} value=${String(first.marker?.value)} bucketValue=${String(first.bucketValue)}` : null,
                        zoom: zoom ? `${String(zoom.start)}–${String(zoom.end)}%` : null,
                        tipDispatched: dispatch && tipIndex >= 0,
                    };
                }, showTip);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    const comboQueries = priceQueries.length; // this combo's slice of the route log starts here
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);

                    await openGalleryAsset(page, GALLERY_ASSET);
                    // The dividend sits ~120 days back, outside the 3-month session default, so the range must really be «All».
                    await selectMaxDateRange(page);
                    await waitForSettled(page.getByTestId('asset-detail-page'));

                    const chartCard = page.getByTestId('asset-detail-chart');
                    const canvas = chartCard.locator('canvas').first();
                    await expect(canvas).toBeVisible({timeout: 8_000});
                    // A red here must say why: what the chart draws, which preset is active, and
                    // what the price-query route was asked and answered during this combo.
                    const diagnose = async (what: string): Promise<string> => {
                        const chart = await inspectEventChart(canvas).catch((error: unknown) => `unreadable: ${(error as Error).message}`);
                        const activePresets = await page.locator('[data-testid^="date-preset-"][data-active="true"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-testid')));
                        const comboLog = priceQueries.slice(comboQueries);
                        // Events answered for this page's asset but absent from the chart point at the page, not at the mock.
                        const assetId = /\/assets\/(\d+)/.exec(page.url())?.[1];
                        const answered = comboLog.filter((query) => query.assets.includes(`${assetId}+events`)).reduce((total, query) => total + query.eventsReturned, 0);
                        const hint = answered > 0 && typeof chart !== 'string' && chart.eventPoints === 0 ? `  hint: the route answered ${answered} event(s) for asset ${assetId}, yet the chart draws none — the page dropped or filtered them` : '';
                        return [`detail-events ${lang}/${theme}: ${what}.`, `  page: ${page.url()}`, `  chart: ${JSON.stringify(chart)}`, `  active preset: ${activePresets.join(', ') || 'none'}`, `  price queries this combo: ${JSON.stringify(comboLog)}`, hint].filter(Boolean).join('\n');
                    };
                    // data-busy covers the price fetch, not the events-only request a price-cache hit
                    // still sends, so wait for the marker itself: an "Events: …" series with a point.
                    try {
                        await expect.poll(async () => (await inspectEventChart(canvas).catch(() => null))?.eventPoints ?? 0, {timeout: 15_000}).toBeGreaterThan(0);
                    } catch {
                        throw new Error(await diagnose('the chart drew no event marker within 15 s'));
                    }

                    await chartCard.evaluate((el) => el.scrollIntoView({block: 'center'}));
                    await page.waitForTimeout(500);
                    const box = await canvas.boundingBox();
                    if (!box) throw new Error('detail-events: chart canvas has no bounding box');

                    // Sweep a small spiral around the canvas centre until the event tooltip
                    // (item trigger on the scatter marker) appears. In headless CI the hover
                    // never lands on the marker — so after the sweep, drive ECharts directly:
                    // showTip on the scatter point instead of trusting the mouse.
                    const tooltip = chartCard.getByText('💰');
                    for (const dy of [0, -20, 20, -40, 40]) {
                        for (let dx = -80; dx <= 80; dx += 10) {
                            await page.mouse.move(box.x + box.width / 2 + dx, box.y + box.height / 2 + dy);
                            await page.waitForTimeout(80);
                            if (await tooltip.isVisible().catch(() => false)) break;
                        }
                        if (await tooltip.isVisible().catch(() => false)) break;
                    }
                    if (!(await tooltip.isVisible().catch(() => false))) {
                        // Deterministic fallback: showTip the first point of the "Events: …" scatter
                        // series (the mocked dividend) — and fail loudly when there is none to drive.
                        const reading = await inspectEventChart(canvas, true).catch(() => null);
                        if (!reading?.tipDispatched) throw new Error(await diagnose('the hover sweep missed and the showTip fallback found no event point to drive'));
                    }
                    try {
                        await expect(tooltip).toBeVisible({timeout: 2_000});
                    } catch (error) {
                        throw new Error(`${await diagnose('no 💰 tooltip after the hover sweep and the showTip fallback')}\n${(error as Error).message}`);
                    }
                    await freezeAnimations(page);
                    // The pointer stays still: the tooltip is the shot's subject, and ECharts takes it away when the pointer
                    // moves off the marker — or moves at all, after the showTip fallback.
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-events', {keepPointer: true});
                    // Move away to dismiss the tooltip for the next iteration
                    await page.mouse.move(box.x + 5, box.y + box.height - 5);
                    await page.waitForTimeout(150);
                }
            }
        });

        test('Asset detail measures', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    const detailChart = page.getByTestId('asset-detail-chart');
                    await waitForChart(detailChart, 30_000);

                    // Screenshot 1: the measures panel open (empty). Its toggle publishes no state: the panel is shown only while
                    // it is open, so the panel says whether a click is needed, and that it took.
                    const measuresToggle = page.getByTestId('asset-detail-measures-toggle');
                    const measuresPanel = page.getByTestId('asset-detail-measures-panel');
                    await expect(measuresToggle).toBeVisible({timeout: 15_000});
                    if (!(await measuresPanel.isVisible())) await measuresToggle.click();
                    await expect(measuresPanel, 'the measures panel is open').toBeVisible();
                    // The desktop keeps its scroll into view: the same frame in every run. On a phone it moved only when the chart
                    // was out of view, from wherever the toggle's click had left the page, and the header followed that last scroll
                    // — es/light at y 491 with the header in one run, at 416 without it in the other (plan 56). There the chart is
                    // framed from the top of the page, 8 px under the screen's edge, or as near as the page's end allows.
                    if (viewport === 'desktop') await detailChart.scrollIntoViewIfNeeded();
                    else await frameTarget(page, detailChart, `${viewport}/${lang}/${theme}/assets/detail-measures`);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-measures');

                    // Screenshot 2: panel with a measurement added (full date range)
                    const addMeasureBtn = page.getByTestId('asset-detail-add-measure-btn');
                    await expect(addMeasureBtn, 'the chart has the two points a measure needs').toBeEnabled({timeout: 10_000});
                    await addMeasureBtn.click();
                    await expect(measuresPanel.locator('tr[data-row-id="main"]'), "the asset's measure is listed").toBeVisible({timeout: 10_000});
                    if (viewport === 'desktop') {
                        await detailChart.scrollIntoViewIfNeeded();
                        await freezeAnimations(page);
                        // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts).
                        await extendScreenToBlock(page, page.getByTestId('asset-detail-measures-section'), `desktop/${lang}/${theme}/assets/detail-measures-active`);
                    } else {
                        await freezeAnimations(page);
                        // PHONE — framed as the first shot, once the measure is listed: the click on Add scrolled the page again.
                        await frameTarget(page, detailChart, `${viewport}/${lang}/${theme}/assets/detail-measures-active`);
                    }
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-measures-active');
                    await restoreTallScreen(page);
                }
            }
        });

        test('Asset detail classification', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);

                    // The classification (metadata) panel open. Its toggle publishes no aria-expanded: the panel is rendered only
                    // while it is open, so the panel says whether a click is needed, and that it took.
                    const metadataToggle = page.getByTestId('asset-detail-metadata-toggle');
                    const metadataPanel = page.getByTestId('asset-detail-metadata-panel');
                    await expect(metadataToggle).toBeVisible({timeout: 15_000});
                    if (!(await metadataPanel.isVisible())) await metadataToggle.click();
                    await expect(metadataPanel, 'the classification panel is open').toBeVisible();
                    // Its map and pie come with the classification, after the panel: drawn, every one (Apple has both).
                    await chartsDrawn(metadataPanel, 'the classification panel');
                    // Framed from the top of the page, the panel 8 px under the screen's edge — or as near as the page's end
                    // allows: the bare scroll into view it replaces depended on where the page stood, and on the charts' arrival
                    // (plan 56, class B).
                    await frameTarget(page, metadataPanel, `${viewport}/${lang}/${theme}/assets/detail-classification`);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-classification');
                }
            }
        });

        test('Asset detail data editor', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openGalleryAsset(page, GALLERY_ASSET);

                    // The data editor open. Its button publishes no state: the panel is rendered only while the editor is open.
                    const editDataBtn = page.getByTestId('asset-detail-editdata-btn');
                    const editorPanel = page.getByTestId('asset-detail-editor-panel');
                    await expect(editDataBtn).toBeVisible({timeout: 15_000});
                    if (!(await editorPanel.isVisible())) await editDataBtn.click();
                    await expect(editorPanel, 'the data editor is open').toBeVisible();
                    // Framed from the top of the page, the panel 8 px under the screen's edge — or as near as the page's end allows.
                    await frameTarget(page, editorPanel, `${viewport}/${lang}/${theme}/assets/detail-editor`);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-editor');
                }
            }
        });

        test('Asset create modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Open create modal
                    await page.getByTestId('assets-add-button').click();
                    await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});
                    // The search providers' chips come with the catalogue, after the form: a fit measured before them
                    // left their row (32 px) hidden in the dialog's body.
                    const createModal = page.getByTestId('asset-modal');
                    await expect(createModal.locator('[data-testid^="asset-search-provider-"]').first(), 'the search providers never arrived').toBeVisible({timeout: 15_000});
                    await imagesSettled(createModal);
                    // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the body is the form's box.
                    if (viewport === 'desktop') await fitScreenToDialog(page, page.getByTestId('asset-modal'), `desktop/${lang}/${theme}/assets/create-modal`, {body: page.getByTestId('asset-modal-form').locator('..')});
                    await screenshot(page, viewport, lang, theme, 'assets', 'create-modal');
                    await restoreTallScreen(page);
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        // The ETF family of the type menu: each specific type and the composite icon it previews, the ETF tag
        // with a content pastille (D52). Mirrors PNG_MAP in src/lib/utils/assetTypes.ts — change both together.
        const ETF_COMPOSITE_ICONS = [
            ['ETF_STOCK', 'etf-stock'],
            ['ETF_BOND', 'etf-bond'],
            ['ETF_COMMODITY', 'etf-commodity'],
            ['ETF_REAL_ESTATE', 'etf-real-estate'],
            ['ETF_CRYPTO', 'etf-crypto'],
            ['ETF_MONETARY', 'etf-liquidity'],
        ] as const;

        test('Asset type picker open - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await page.getByTestId('assets-add-button').click();
                    const modal = page.getByTestId('asset-modal');
                    await expect(modal.getByTestId('asset-modal-form')).toHaveAttribute('data-snapshot-ready', 'true', {timeout: 5_000});
                    // The menu is placed from where its trigger is at the moment it opens, so the form must have
                    // stopped moving first: the modal's intro, and the provider badges Search Online draws once the
                    // providers are in, which push the Type field down.
                    await expect(modal.getByTestId(/^asset-search-provider-/), 'Search Online never listed its providers').not.toHaveCount(0, {timeout: 10_000});
                    await waitForMotionSettled(modal, 'the asset modal');

                    // Rows are looked up inside the field: the menu renders within it, and asset-type-tree-* names a
                    // kind of row. A group is a toggle that opens by itself only when the value is in it, and a new
                    // asset is a STOCK: ask for its state, click only when it is closed.
                    const field = modal.getByTestId('asset-modal-type');
                    const trigger = field.getByTestId('asset-modal-type-button');
                    await trigger.click();
                    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
                    const etfFamily = field.getByTestId('asset-type-tree-group-ETF');
                    await expect(etfFamily).toBeVisible();
                    if ((await etfFamily.getAttribute('aria-expanded')) !== 'true') await etfFamily.click();
                    await expect(etfFamily).toHaveAttribute('aria-expanded', 'true');
                    await expect(field.getByTestId('asset-type-tree-option-ETF')).toBeVisible();
                    for (const [type, icon] of ETF_COMPOSITE_ICONS) {
                        const preview = field.getByTestId(`asset-type-tree-option-${type}`).locator(`img[src="/icons/asset-types/${icon}.png"]`);
                        await expect(preview, `${type} does not preview its composite icon`).toBeVisible();
                        await expect.poll(() => preview.evaluate((img) => (img as HTMLImageElement).complete && (img as HTMLImageElement).naturalWidth > 0), {message: `${icon}.png never loaded`, timeout: 5_000}).toBe(true);
                    }
                    await screenshot(page, viewport, lang, theme, 'assets', 'type-picker-open');

                    // Closed from its own search box, which stops the Escape at the menu. The next combo reloads.
                    await trigger.locator('input').press('Escape');
                    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
                }
            }
        });

        // The Provider Data Comparison a new asset meets after a Search Online pick (user/assets/create-edit.en.md). The
        // search and the provider are answered by routes registered here, after the offline guard; nothing is created.
        // galleryProviderCompare.ts says what is answered, and why.
        test('Asset create provider compare - all languages and themes', async ({page}, testInfo) => {
            // 8 combinations of about 10 s each: the Assets page, the search, two answered probes, the shot.
            test.setTimeout(300_000);
            const viewport = getViewport(testInfo);
            const mock = await mockProviderCompare(page);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    const probesBefore = mock.probes.length;
                    const dialog = await openProviderCompare(page, waitForMotionSettled);
                    // This pick's connection test and its read of the details, both answered by the mock.
                    expect(mock.probes.slice(probesBefore).sort(), 'the pick did not probe the provider as expected').toEqual(['current_price+history', 'metadata']);
                    // DESKTOP — coordinator's decision, provisional: the simulation shot's rule (see 'risk what-if simulation on
                    // the dashboard' and «Screens taller than the desktop's» in galleryRiskLab.ts). The dialog's body is capped at
                    // 60% of the screen and its three rows are taller than that: the shot gets a screen tall enough for the body to
                    // stop scrolling, width (1280) and scale unchanged, measured and logged (📐) every combination. The mobile
                    // project keeps its phone, the body scrolled to the identifier and Type rows. Reverting the decision is
                    // deleting this line.
                    if (viewport === 'desktop') await fitScreenToCompareDialog(page, dialog, `desktop/${lang}/${theme}/assets/create-provider-compare`, waitForMotionSettled);
                    await settleProviderCompareShot(page, dialog, waitForMotionSettled);
                    await screenshot(page, viewport, lang, theme, 'assets', 'create-provider-compare');
                    // The project's screen again, before anything else: the next combination's asset form opens on 720 px.
                    await restoreCompareScreen(page);
                    // Both dialogs cancelled, the form discarded: nothing is created.
                    await closeProviderCompare(page);
                }
            }
            expect(mock.problems, 'the mocked search or probe met a request it does not answer').toEqual([]);
        });

        test('Asset distribution editors - sector and geographic', async ({page}, testInfo) => {
            // Tesla is populated with both distributions summing to exactly 100%
            // (sector: Consumer Discretionary 70 / Energy 30 — geographic: USA 50 / CHN 25 / DEU 25),
            // so both editors render filled rows plus the green 100% total badge.
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);

                    // Search for Tesla directly: navigateToAssetByName races the filter
                    // debounce (waits data-busy=false, which is already false pre-refilter),
                    // so instead wait until the first card actually shows the search hit.
                    const searchInput = page.getByTestId('assets-search-input');
                    await expect(searchInput).toBeVisible({timeout: 10_000});
                    await searchInput.fill('Tesla');
                    const teslaCard = page.locator('[data-testid^="asset-card-"]').first();
                    await expect(teslaCard).toContainText('Tesla', {timeout: 10_000});
                    await teslaCard.click();
                    await page.waitForSelector('[data-testid="asset-detail-page"][data-busy="false"]', {timeout: 20_000});
                    await expect(page.getByTestId('asset-detail-header')).toBeVisible({timeout: 10_000});

                    // Open the edit modal — the button stays disabled until asset info
                    // and classification have loaded, so waiting for enabled is the gate.
                    const editBtn = page.getByTestId('asset-detail-edit-btn');
                    await expect(editBtn).toBeEnabled({timeout: 10_000});
                    await editBtn.click();
                    await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5_000});

                    // Expand More Info (Identifiers + Classification area)
                    const moreInfo = page.getByTestId('asset-modal-more-info');
                    if ((await moreInfo.getAttribute('data-expanded')) !== 'true') {
                        await moreInfo.click();
                    }

                    await expect(page.getByTestId('distribution-editor-sector')).toBeVisible({timeout: 5_000});
                    await expect(page.getByTestId('distribution-editor-geographic')).toBeVisible({timeout: 5_000});
                    // Populated distributions sum to 100% → both totals are in the valid state (data-state, not a colour)
                    const sectorTotal = page.getByTestId('distribution-total-sector');
                    const geoTotal = page.getByTestId('distribution-total-geographic');
                    await expect(sectorTotal).toHaveAttribute('data-state', 'valid', {timeout: 5_000});
                    await expect(geoTotal).toHaveAttribute('data-state', 'valid', {timeout: 5_000});
                    await freezeAnimations(page);

                    await sectorTotal.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(200);
                    await screenshot(page, viewport, lang, theme, 'assets', 'distribution-editor-sector');

                    await page.getByTestId('distribution-editor-geographic').scrollIntoViewIfNeeded();
                    await page.waitForTimeout(200);
                    await screenshot(page, viewport, lang, theme, 'assets', 'distribution-editor-geographic');

                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('Asset create modal from import wizard - all languages and themes', async ({page}, testInfo) => {
            // Heavier than the default 3-min budget: full import wizard + CSV parse × 4 langs × 2 themes.
            test.setTimeout(300_000); // 5 minutes
            // Opens AssetModal from ImportWizard step4 — pre-filled with extracted ticker/ISIN/name
            // Uses generic_simple.csv which has UNETF (unresolved asset)
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                await setBrowserLocale(page, lang);
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    // Open wizard from transactions import button
                    await page.getByTestId('tx-import-button').click();
                    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});

                    // Skip step 1, advance to step 2
                    await waitForSettled(page.getByTestId('import-wizard-step1'));
                    await page.getByTestId('import-wizard-next').click();
                    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 8_000});
                    await waitForSettled(page.getByTestId('import-wizard-step2'), 30_000);

                    // Select and parse generic_simple.csv (has UNETF - unresolved asset), then on to step 4: its notices
                    // confirmed when the parse raised some — the response says, not a probe. Ends on step 4 settled.
                    const parsed = await analyseWizardSample(page);
                    await continueToReview(page, parsed);

                    // The resolve section defaults to expanded when there are unresolved assets.
                    // Just find the AssetSelect directly — it's inside the resolve section.
                    // Use the [role="combobox"] inside the asset-select element.
                    const assetSelect = page.getByTestId('asset-select').first();
                    if (await appears(assetSelect, 5_000)) {
                        // Open the search dropdown by clicking the combobox trigger
                        const combobox = assetSelect.locator('[role="combobox"], input[type="text"]').first();
                        if (await appears(combobox, 1_000)) {
                            await combobox.click();
                        } else {
                            await assetSelect.click();
                        }
                        await page.waitForTimeout(400);

                        // Click the "Create new" option in the dropdown
                        const createNewBtn = page.getByTestId('search-select-create-new');
                        if (await appears(createNewBtn, 2_000)) {
                            await createNewBtn.click();
                            // AssetModal opens pre-filled with extracted ticker/ISIN/name
                            const assetModal = page.getByTestId('asset-modal-form');
                            if (await appears(assetModal, 5_000)) {
                                await waitForNetworkSettled(page);
                                await page.waitForTimeout(500);
                                await freezeAnimations(page);
                                await screenshot(page, viewport, lang, theme, 'assets', 'create-wizard-modal');
                                await page.keyboard.press('Escape');
                                await page.waitForTimeout(200);
                                // Close any confirm dialog
                                const confirmClose = page.getByTestId('confirm-modal-confirm');
                                if (await confirmClose.isVisible({timeout: 500}).catch(() => false)) {
                                    await confirmClose.click();
                                    await page.waitForTimeout(200);
                                }
                            }
                        }
                    }

                    // Close all wizard/bulk modals
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });
    });

    /**
     * Inventory group 4: the risk lab — the Correlation tab of the Assets page — and the Dashboard's What if…?
     * simulation. Everything runs as the admin, read-only: the lab's selection and benchmark, and the Dashboard's open
     * What if…? tools, live in the browser's storage and are written there before every load
     * (fixtures/galleryRiskLab.ts); the live-price poll and every sync are aborted. Two shots edit a real answer where
     * the gallery's clean data cannot show the state: the partial-results notice and the replay that leaves an asset
     * out — galleryRiskLab.ts says which fields, and why.
     *
     * Every shot keeps its project's screen — 1280×720 on the desktop — but, on the desktop only, the simulation and the
     * four Dashboard Risk blocks after this group (coordinator's decision, provisional): their pages want the whole box or
     * block in one image, and none fits 720 px — the Simulation box is about 1,100 px high (1090 measured). Each of those
     * shots takes a screen as tall as its box or block plus the frame's margins, at the same width and scale; the mobile
     * project keeps its phone.
     */
    test.describe('Risk Analysis', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        /** The simulation's run: fewer paths than the default 8192, for speed — 2048 still draw a smooth cone — and a fixed seed. */
        const SIMULATION_PATHS = 2048;
        const SIMULATION_SEED = 123456;
        /** The space the simulation's frame leaves above the box — and, on the desktop's fitted screen, below it. */
        const SIMULATION_FRAME_MARGIN = 8;

        /**
         * The last steps before a shot: the pointer parked where nothing reacts to it and no tooltip left, every image of
         * the framed region loaded, nothing in it still animating or moving, no toast over the page.
         */
        async function settleShot(page: Page, region: Locator, what: string): Promise<void> {
            await parkPointer(page);
            await imagesSettled(region);
            await waitForMotionSettled(region, what);
            await waitForStillness(region, what);
            await expectNoToast(page);
        }

        test('risk lab correlation, loss table and risk/return - all languages and themes', async ({page}, testInfo) => {
            // Eight combinations, each a fresh load of the lab: the eligibility engine, three risk waves over a year of
            // prices (the matrix's, L1°'s, and L3°'s with the S&P 500 comparison), the assets' metadata and two charts.
            // About 15 s a combination on a quiet lane; risk answers slow down under load.
            test.setTimeout(360_000); // 6 minutes
            const viewport = getViewport(testInfo);
            const ids = await resolveLabIds(page);
            const selection = labSelection(ids);
            const guard = await guardReadOnly(page);
            await seedLabStorage(page, ids.userId, {selection, benchmark: ids.sp500});
            await chooseLabYear(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await openLab(page, selection);
                await freezeAnimations(page);
                const panel = page.getByTestId('asset-global-risk-panel');

                // The matrix: drawn over the selection, its grouping metadata in — the sector and area orders, and the
                // badge rows above the matrix, appear only once the assets' metadata is read — and both rankings on the page.
                // The two loans are near-identical by construction (populate_mock_data.py, `correlation_plan`: 0.93), so they
                // rank among the most alike on any populate day; no other pair is required — a pair's value depends on the
                // selection's joint calendar — and with the seed's pairs the offsetting list may show its empty state.
                const correlation = panel.getByTestId('risk-correlation-section');
                const heatmap = correlation.getByTestId('risk-correlation-heatmap');
                await waitForChart(heatmap, 30_000);
                await expect.poll(async () => idSet(await heatmap.getAttribute('data-asset-order')), {message: 'the matrix does not draw the seeded selection'}).toEqual(selection);
                await expect(correlation.getByTestId('risk-correlation-ordering-similarity')).toHaveAttribute('aria-pressed', 'true');
                await expect(correlation.getByTestId('risk-correlation-ordering-sector'), 'the assets metadata never reached the matrix').toBeVisible({timeout: 15_000});
                await expect(correlation.getByTestId('risk-correlation-ordering-region')).toBeVisible();
                await expect(correlation.getByTestId('risk-correlation-groups')).toBeVisible();
                await expect(correlation.getByTestId('risk-correlation-pairs-correlated').getByTestId(pairTestId(ids.milano, ids.roma)), 'the two loans are not ranked among the most alike').toBeVisible();
                await expect(correlation.getByTestId('risk-correlation-pairs-offsetting')).toBeVisible();

                // How much did each of these hurt?: one row per asset, the bad day, the bad month and the worst fall
                // measured for every one, and the fall's duration under it.
                const loss = panel.getByTestId('risk-asset-set-loss');
                const lossTable = loss.getByTestId('risk-asset-set-l1-table');
                await expect(lossTable).toHaveAttribute('data-row-count', String(selection.length), {timeout: 30_000});
                await expect(loss.getByTestId('risk-asset-set-l1-loading')).toHaveCount(0);
                for (const column of ['badDay', 'badMonth', 'worstFall'] as const) {
                    await expect(lossTable.locator(`[data-testid="risk-asset-set-l1-${column}"][data-measured="true"]`), `${column} is not measured for every asset`).toHaveCount(selection.length);
                }
                await expect(lossTable.getByTestId('risk-asset-set-l1-worstFall-days')).not.toHaveCount(0);

                // What did each of these pay for its risk?: the S&P 500 confirmed and its comparison back whole, the table
                // opened by its tinted row, the period line, and the chart with its diamond and the line through it.
                const paid = panel.getByTestId('risk-asset-set-paid');
                const benchmark = paid.getByTestId('risk-asset-set-benchmark-control');
                await expect(benchmark).toHaveAttribute('data-benchmark-state', 'set', {timeout: 20_000});
                await expect(benchmark).toHaveAttribute('data-benchmark-id', String(ids.sp500));
                await expect(paid.getByTestId('risk-asset-set-l3'), 'the S&P 500 comparison did not come back whole').toHaveAttribute('data-benchmark', 'true', {timeout: 30_000});
                await expect(paid.getByTestId('risk-asset-set-l3-loading')).toHaveCount(0);
                const paidTable = paid.getByTestId('risk-asset-set-l3-table');
                await expect(paidTable).toHaveAttribute('data-reference-count', '1');
                await expect(paidTable.locator(`[data-testid="risk-asset-set-l3-ref-name"][data-reference="benchmark"][data-asset-id="${ids.sp500}"]`)).toBeVisible();
                await expect(paid.getByTestId('risk-asset-set-l3-period')).toBeVisible();
                const scatter = paid.getByTestId('risk-asset-set-l3-scatter');
                await waitForChart(scatter, 30_000);
                await expect(scatter).toHaveAttribute('data-dropped-count', '0');
                await expect(paid.getByTestId('risk-asset-set-l3-scatter-line')).toHaveAttribute('data-anchor', 'benchmark');
                await expectLabClean(page, selection);

                // Each frame comes down from the top of the page, so the header has slid out of every shot.
                await frameFromTop(page, correlation);
                await settleShot(page, correlation, 'the correlation section');
                await screenshot(page, viewport, lang, theme, 'risk', 'lab-correlation');

                await frameFromTop(page, loss);
                await settleShot(page, loss, 'the loss table');
                await screenshot(page, viewport, lang, theme, 'risk', 'lab-hurt-table');

                // The section from its title when it fits on the screen, otherwise from the table's benchmark row.
                await frameBlock(page, {first: paid, last: scatter, fallback: paidTable});
                // DESKTOP — the tall-screen rule (coordinator, C4; galleryTallShots.ts): the whole chart and its notes.
                if (viewport === 'desktop') await extendScreenToBlock(page, paid.getByTestId('risk-asset-set-l3-risk-return'), `desktop/${lang}/${theme}/risk/lab-risk-return`);
                await settleShot(page, paid, 'the risk/return section');
                await screenshot(page, viewport, lang, theme, 'risk', 'lab-risk-return');
                await restoreTallScreen(page);

                await scrollBackToHeader(page);
            });
            expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started').toEqual([]);
        });

        test('risk lab asset and benchmark pickers - all languages and themes', async ({page}, testInfo) => {
            // Eight combinations, each a fresh load of the lab with every wave in before a picker opens. About 12 s a
            // combination on a quiet lane.
            test.setTimeout(300_000); // 5 minutes
            const viewport = getViewport(testInfo);
            const ids = await resolveLabIds(page);
            const selection = labSelection(ids);
            const guard = await guardReadOnly(page);
            await seedLabStorage(page, ids.userId, {selection, benchmark: ids.sp500});
            await chooseLabYear(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await openLab(page, selection);
                await freezeAnimations(page);
                const panel = page.getByTestId('asset-global-risk-panel');
                const paid = panel.getByTestId('risk-asset-set-paid');
                const benchmark = paid.getByTestId('risk-asset-set-benchmark-control');
                await expect(benchmark).toHaveAttribute('data-benchmark-state', 'set', {timeout: 20_000});
                await expect(benchmark).toHaveAttribute('data-benchmark-id', String(ids.sp500));
                await expect(paid.getByTestId('risk-asset-set-l3'), 'the S&P 500 comparison did not come back whole').toHaveAttribute('data-benchmark', 'true', {timeout: 30_000});
                await expectLabClean(page, selection);

                // The "+", open over the selection card: two rows ticked, so Add counts them — never pressed — and the
                // assets the engine rules out for the period listed apart, read-only, each with its reason. NVIDIA and the
                // KRW stock are among them: the seed gives them no quote, and the gallery's offline guard writes none.
                const card = panel.getByTestId('risk-asset-set-controls');
                await frameFromTop(page, card);
                const add = page.getByTestId('risk-asset-add-panel');
                await expect(add, 'the + opens closed on every load').toHaveCount(0);
                await card.getByTestId('risk-asset-add-button').click();
                await expect(add).toBeVisible();
                await expect(add.getByTestId('risk-asset-add-search')).toBeVisible();
                await expect(add.getByTestId('risk-asset-add-filters')).toBeVisible();
                for (const assetId of [ids.microsoft, ids.tesla]) {
                    const row = add.getByTestId(`risk-asset-add-option-${assetId}`);
                    await row.click();
                    await expect(row, `the + must let asset ${assetId} be ticked`).toHaveAttribute('aria-selected', 'true');
                }
                await expect(add.getByTestId('risk-asset-add-confirm')).toBeEnabled();
                const blocked = add.getByTestId('risk-asset-add-blocked');
                for (const assetId of [ids.nvidia, ids.krw]) {
                    const row = blocked.getByTestId(`risk-asset-add-option-${assetId}`);
                    await expect(row).toHaveAttribute('data-level', 'ineligible');
                    await expect(row, `asset ${assetId} is listed apart without a reason`).toHaveAttribute('data-reasons', /\S/);
                }
                // The list scrolls inside the panel: the ticked rows and the start of the read-only part share its view.
                await expect(add.getByTestId(`risk-asset-add-option-${ids.tesla}`)).toBeInViewport();
                await expect(blocked.getByTestId(/^risk-asset-add-option-\d+$/).first()).toBeInViewport();
                await waitForStillness(add, 'the + panel');
                await settleShot(page, card, 'the selection card');
                await screenshot(page, viewport, lang, theme, 'risk', 'lab-asset-picker');
                await page.keyboard.press('Escape');
                await expect(add).toHaveCount(0);
                await expect(panel.getByTestId('risk-selected-count'), 'the ticked rows were added').toHaveAttribute('data-selected', String(selection.length));

                // The benchmark picker, open at the top of «What did each of these pay for its risk?» on the current
                // benchmark, its list scrolled to the read-only part at its bottom: the assets that cannot be measured over
                // the period, each with its reason. Only the list scrolls — the panel is placed in the viewport and
                // follows its trigger — so it is scrolled from the list that holds that part: its header at the top of
                // what the list shows, the first entries under it (the phone); where the whole part fits, the list
                // stops at its end, as before (the desktop).
                await frameFromTop(page, paid);
                const trigger = paid.getByTestId('risk-asset-set-benchmark-trigger');
                const picker = page.getByTestId('risk-asset-set-benchmark-panel');
                await expect(picker, 'the benchmark picker opens closed on every load').toHaveCount(0);
                await trigger.click();
                await expect(trigger).toHaveAttribute('aria-expanded', 'true');
                await expect(picker).toBeVisible();
                await expect(picker.getByTestId('risk-asset-set-benchmark-search')).toBeVisible();
                await expect(picker.getByTestId(`search-select-option-${ids.sp500}`), 'the picker does not open on the current benchmark').toHaveAttribute('aria-selected', 'true');
                const unusable = picker.getByTestId('risk-asset-set-benchmark-blocked');
                for (const assetId of [ids.nvidia, ids.krw]) {
                    const row = unusable.getByTestId(`search-select-option-${assetId}`);
                    await expect(row).toHaveAttribute('data-level', 'ineligible');
                    await expect(row, `asset ${assetId} is listed apart without a reason`).toHaveAttribute('data-reasons', /\S/);
                }
                await revealListSection(unusable);
                await waitForStillness(picker, 'the benchmark picker');
                await expect(unusable.getByTestId(/^search-select-option-\d+$/).first(), 'the first unusable asset is not on screen').toBeInViewport();
                await settleShot(page, picker, 'the benchmark picker');
                await screenshot(page, viewport, lang, theme, 'risk', 'lab-benchmark-picker');
                await page.keyboard.press('Escape');
                await expect(picker).toHaveCount(0);
                await optionsClosed(page);
                await expect(benchmark, 'another benchmark was chosen').toHaveAttribute('data-benchmark-id', String(ids.sp500));

                await scrollBackToHeader(page);
            });
            expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started').toEqual([]);
        });

        test('risk lab partial results notice (injected stale price) - all languages and themes', async ({page}, testInfo) => {
            // Eight combinations, each a fresh load of the lab whose three base waves and two eligibility answers are fetched
            // and edited on their way.
            test.setTimeout(300_000); // 5 minutes
            const viewport = getViewport(testInfo);
            const ids = await resolveLabIds(page);
            const selection = labSelection(ids);
            const guard = await guardReadOnly(page);
            // No benchmark: L3° measures without a comparison, so the notice counts exactly five measurements.
            await seedLabStorage(page, ids.userId, {selection, benchmark: null});
            // INJECTED (galleryRiskLab.ts, injectStalePrice): RE Loan Roma's price 12 days old on every base wave, and the
            // matrix's own answer not back; the eligibility answers about Roma carry the matching stale-end verdict
            // (warning, so Roma stays analysed). The gallery's prices are all fresh, so no real answer carries any of them.
            const injection = await injectStalePrice(page, {id: ids.roma, name: LAB_ASSET_NAMES.roma});
            await chooseLabYear(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                const editedBefore = injection.edited;
                const verdictsBefore = injection.verdictsEdited;
                await openLab(page, selection);
                await freezeAnimations(page);
                const panel = page.getByTestId('asset-global-risk-panel');
                // Both levels have their tables, so every result the notice reads is in; and this load's three base waves
                // (the matrix's, L1°'s, L3°'s) all went through the edit.
                await expect(panel.getByTestId('risk-asset-set-l1-table')).toHaveAttribute('data-row-count', String(selection.length), {timeout: 30_000});
                await expect(panel.getByTestId('risk-asset-set-l3-table')).toHaveAttribute('data-row-count', String(selection.length), {timeout: 30_000});
                await expect.poll(() => injection.edited - editedBefore + injection.problems.length, {message: 'the lab asked fewer than three base waves', timeout: 30_000}).toBeGreaterThanOrEqual(3);
                // Both eligibility answers of this load name Roma: the catalogue's, behind the chips, and the selection's.
                await expect.poll(() => injection.verdictsEdited - verdictsBefore + injection.problems.length, {message: "the lab's eligibility answers about RE Loan Roma were not both edited", timeout: 30_000}).toBeGreaterThanOrEqual(2);
                expect(injection.problems, 'an answer went through unedited').toEqual([]);

                // The chips agree with the notice: Roma's is the amber one, stale at the end, and still analysed (openLab:
                // five selected, none parked); the other four keep their clean, real verdicts.
                const roma = panel.getByTestId(`risk-selected-asset-${ids.roma}`);
                await expect(roma).toHaveAttribute('data-level', 'warning');
                await expect(roma).toHaveAttribute('data-reasons', 'stale_at_end');
                await expect(roma).toHaveAttribute('data-variant', 'warning');
                for (const assetId of selection.filter((id) => id !== ids.roma)) {
                    await expect(panel.getByTestId(`risk-selected-asset-${assetId}`), `asset ${assetId} is not clean over the year: the gallery data went stale`).toHaveAttribute('data-level', 'eligible');
                }

                // The notice: amber, one cause — the stale price — and the five partial measurements of the two levels.
                const notice = panel.getByTestId('risk-partial-notice');
                await expect(notice).toBeVisible();
                await expect(notice).toHaveAttribute('data-tone', 'warning');
                await expect(notice.getByTestId('risk-partial-reasons')).toHaveAttribute('data-count', '1');
                await expect(notice.getByTestId('risk-partial-measurements')).toHaveAttribute('data-count', '5');
                // Above it the banner, folded as every load opens it; under it the matrix's own banner, naming the measurement
                // that did not come back, and why. No other section banner, and no period offer, in the shot: the selection's
                // eligibility answer keeps the engine's suggestion, which over a year of fresh prices is none.
                const banner = panel.getByTestId('data-quality-banner');
                await expect(banner).toBeVisible();
                await expect(banner.getByTestId('data-quality-toggle')).toHaveAttribute('aria-expanded', 'false');
                const correlation = panel.getByTestId('risk-correlation-section');
                const alert = correlation.getByTestId('risk-correlation-section-alert');
                await expect(alert).toBeVisible();
                await expect(alert.getByTestId('risk-correlation-section-health')).toHaveAttribute('data-count', '1');
                await expect(alert.getByTestId('risk-correlation-section-error')).toHaveAttribute('data-code', 'insufficient_history');
                await expect(correlation.getByTestId('risk-correlation-empty')).toBeVisible();
                for (const section of ['risk-asset-set-loss', 'risk-asset-set-paid']) await expect(panel.getByTestId(`${section}-alert`)).toHaveCount(0);
                await expect(panel.getByTestId('risk-fit-period-banner')).toHaveCount(0);

                const card = panel.getByTestId('risk-asset-set-controls');
                await frameFromTop(page, card);
                await settleShot(page, card, 'the selection card');
                await expect(alert, 'the matrix banner falls outside the shot').toBeInViewport();
                await screenshot(page, viewport, lang, theme, 'risk', 'lab-notice');

                await scrollBackToHeader(page);
            });
            expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started').toEqual([]);
        });

        test('risk lab historical replay with a left-out asset (injected) - all languages and themes', async ({page}, testInfo) => {
            // Eight combinations, each a fresh load of the lab, then a replay over a year of prices run and edited on its way.
            test.setTimeout(360_000); // 6 minutes
            const viewport = getViewport(testInfo);
            const ids = await resolveLabIds(page);
            const selection = labSelection(ids);
            const guard = await guardReadOnly(page);
            await seedLabStorage(page, ids.userId, {selection, benchmark: null});
            // INJECTED (galleryRiskLab.ts, injectReplayLeftOut): RE Loan Roma left out of the replay, first quoted 60 days
            // into the window, with the common period that brings it back. Every asset of the seed starts on the same day,
            // so a real window covers all of them or none: it never leaves one out while replaying the others.
            const injection = await injectReplayLeftOut(page, {id: ids.roma, name: LAB_ASSET_NAMES.roma});
            await chooseLabYear(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await openLab(page, selection);
                await freezeAnimations(page);
                await expectLabClean(page, selection);
                const panel = page.getByTestId('asset-global-risk-panel');

                // What if…? is born closed on every load: opened from its title, the end state asserted.
                const section = panel.getByTestId('risk-replay-section');
                await expect(section).toHaveAttribute('data-open', 'false');
                await section.getByTestId('risk-replay-section-toggle').click();
                await expect(section).toHaveAttribute('data-open', 'true');
                const replay = section.getByTestId('risk-replay');
                const run = replay.getByTestId('risk-replay-run');
                await expect(run).toBeEnabled();

                // Run replay over the page's period: the replay follows it until its own dates are touched.
                const editedBefore = injection.edited;
                await run.click();
                await expect.poll(() => injection.edited - editedBefore + injection.problems.length, {message: 'the replay was never asked', timeout: 60_000}).toBeGreaterThanOrEqual(1);
                expect(injection.problems, 'the replay went through unedited').toEqual([]);
                const suggested = injection.suggested;
                if (!suggested) throw new Error('the edited replay offers no common period');

                // The box of what was left out first: one badge under its reason, and the common-period button — shown,
                // never pressed: it would run a second replay. Then the table of the assets replayed, without the one left out.
                const box = replay.getByTestId('risk-replay-excluded');
                await expect(box).toBeVisible({timeout: 30_000});
                await expect(box).toHaveAttribute('data-count', '1');
                await expect(box).toHaveAttribute('data-treatment', 'omitted_from_replay');
                await expect(box.locator(`[data-testid="risk-replay-excluded-group"][data-reason="starts_after_window_start"] [data-testid="risk-replay-excluded-asset"][data-asset-id="${ids.roma}"]`)).toBeVisible();
                const offer = box.getByTestId('risk-replay-suggested');
                await expect(offer).toHaveAttribute('data-start', suggested.start);
                await expect(offer).toHaveAttribute('data-end', suggested.end);
                await expect(offer).toHaveAttribute('data-recovers', '1');
                await expect(offer).toBeEnabled();
                const tornado = replay.getByTestId('risk-replay-tornado');
                await expect(tornado.getByTestId('risk-replay-tornado-row')).toHaveCount(selection.length - 1);
                await expect(tornado.locator(`[data-testid="risk-replay-tornado-row"][data-row-key="asset:${ids.roma}"]`)).toHaveCount(0);
                await expect(run).toBeEnabled();
                await expect(section.getByTestId('risk-replay-section-health'), 'the section does not mark the replay partial').toBeVisible();

                // The section from its title when it fits on the screen, otherwise from the box of what was left out.
                await frameBlock(page, {first: section, last: tornado, fallback: box});
                await settleShot(page, section, 'the replay');
                await screenshot(page, viewport, lang, theme, 'risk', 'lab-replay');

                await scrollBackToHeader(page);
            });
            expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started').toEqual([]);
        });

        test('risk what-if simulation on the dashboard - all languages and themes', async ({page}, testInfo) => {
            // The heaviest scenario of the group: eight live dashboard loads, each the risk tab's base wave over a year of
            // the admin's portfolio, then a 2048-path bootstrap over a 365-day horizon.
            test.setTimeout(480_000); // 8 minutes
            const viewport = getViewport(testInfo);
            // The project's own screen: the desktop shot below grows from it, never shrinks under it.
            const projectScreen = page.viewportSize();
            if (!projectScreen) throw new Error('the page has no viewport');
            const guard = await guardReadOnly(page);
            await forgetWhatIfTools(page, await currentUserId(page));
            await navigateTo(page, '/dashboard');
            await selectOneYearPreset(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                // The live report, not the snapshot: the risk tab measures the gallery DB's own portfolio.
                await navigateTo(page, '/dashboard');
                await page.getByTestId('dashboard-tab-risk').click();
                await expect(page.getByTestId('dashboard-risk-tab')).toBeVisible({timeout: 15_000});
                await freezeAnimations(page);
                const levels = page.getByTestId('risk-levels-panel');
                await expect(levels).toHaveAttribute('data-catalog', 'ready', {timeout: 30_000});
                await expect(levels).toHaveAttribute('data-busy', 'false', {timeout: 60_000});

                // What if…? is born closed, and with no tool open (the init script forgets the ones left open): opened from
                // its title, then the simulation added the way a user adds it.
                const whatIf = levels.getByTestId('risk-level-4');
                await expect(whatIf).toHaveAttribute('data-open', 'false');
                await whatIf.getByTestId('risk-level-4-toggle').click();
                await expect(whatIf).toHaveAttribute('data-open', 'true');
                await expect(whatIf.getByTestId('risk-l4-tools')).toBeVisible();
                const box = whatIf.getByTestId('risk-l4-simulation');
                await expect(box, 'a What if…? tool came back open').toHaveCount(0);
                await whatIf.getByTestId('risk-l4-add-simulation').click();
                await expect(box).toBeVisible();
                await expect(box.locator('[data-testid="risk-beta-banner"][data-scope="simulation"]')).toBeVisible();
                await expect(box.getByTestId('risk-l4-model-warning')).toBeVisible();

                // The five modes, the recommended one chosen; a 365-day horizon, the paths and the seed fixed, so every
                // combination draws the same answer.
                const simulation = box.getByTestId('risk-simulation');
                await expect(simulation.getByTestId('risk-simulation-mode')).toHaveCount(5);
                await expect(simulation.locator('[data-testid="risk-simulation-mode"][data-mode-id="block_bootstrap"]')).toHaveAttribute('data-selected', 'true');
                await expect(simulation.getByTestId('risk-simulation-horizon')).toHaveValue('365');
                const paths = simulation.getByTestId('risk-simulation-paths');
                await paths.fill(String(SIMULATION_PATHS));
                await expect(paths).toHaveValue(String(SIMULATION_PATHS));
                const seed = simulation.getByTestId('risk-simulation-seed');
                await seed.fill(String(SIMULATION_SEED));
                await expect(seed).toHaveValue(String(SIMULATION_SEED));
                const run = simulation.getByTestId('risk-simulation-run');
                await expect(run).toBeEnabled();
                await run.click();

                // A result: the terminal figures, the cone drawn (its LineChart has no test id of its own: it is the one
                // chart under the simulation root), and what the simulation assumed.
                await expect(simulation.getByTestId('risk-simulation-terminal')).toBeVisible({timeout: 120_000});
                await expect(run).toBeEnabled({timeout: 30_000});
                await waitForChart(simulation, 30_000);
                await expect(box.getByTestId('risk-l4-provenance')).toBeVisible();

                // From the top of the step: the box's own header, then the beta notice and the model warning above the modes.
                //
                // DESKTOP — coordinator's decision. The page (user/dashboard/risk.md, risk/whatif-simulation) wants the whole
                // Simulation box in one image: the beta notice and the model warning, the five modes with Reshuffled history
                // recommended, and after Simulate the cone with the terminal figures and «What this simulation assumed». With a
                // result the box is about 1,100 px high (1090 measured), which no 720 px screen holds, so this shot gets a screen
                // exactly as tall as the box plus the frame's margins — measured every combination, because the box's sentences
                // wrap differently in each language, and logged (📐). The width (1280) and the scale stay the desktop project's,
                // so the image sits beside the other desktop shots. The four Dashboard Risk blocks follow the same rule. The
                // mobile project keeps its phone: the top of the step, with its beta notice.
                if (viewport === 'desktop') {
                    const fit = await fitViewportToBlock(page, box, SIMULATION_FRAME_MARGIN, projectScreen.height);
                    console.log(`  📐 desktop/${lang}/${theme}: Simulation box ${fit.blockHeight} px → screen ${projectScreen.width}×${fit.viewportHeight}`);
                }
                await frameFromTop(page, box, SIMULATION_FRAME_MARGIN);
                await settleShot(page, box, 'the simulation');
                await expect(box.locator('[data-testid="risk-beta-banner"][data-scope="simulation"]'), 'the beta notice falls outside the shot').toBeInViewport({ratio: 1});
                if (viewport === 'desktop') {
                    await expect(box, 'the Simulation box is not whole in the shot').toBeInViewport({ratio: 1});
                    await expect(box.getByTestId('risk-l4-provenance'), '«What this simulation assumed» falls outside the shot').toBeInViewport({ratio: 1});
                }
                await screenshot(page, viewport, lang, theme, 'risk', 'whatif-simulation');

                await scrollBackToHeader(page);
            });
            expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started').toEqual([]);
        });
    });

    /**
     * The Dashboard's Risk tab (user/dashboard/risk.md), `dashboard` category: one shot per block — How much can it hurt?,
     * Am I as diversified as I think?, Am I being paid for this risk? (compared with the MSCI World Index) and What if…?
     * after a crisis replay. The tab measures the gallery database's own portfolio, the admin's — every broker it owns —
     * over the Dashboard's 1Y period: live answers, never the frozen report of the other Dashboard shots, whose broker ids
     * are not the database's. Everything runs as the admin, read-only: the benchmark and the What if…? tools left open live
     * in the browser's storage, written there before every load and removed at the end; the live-price poll and every sync
     * are aborted (guardReadOnly). One shot edits what the page receives, where the gallery's year of prices cannot show
     * the state: the crisis replay — fixtures/galleryRiskDashboard.ts says what, and why.
     *
     * Each block is framed from its top. On the desktop it then gets a screen as tall as the whole block plus the frame's
     * margins, width (1280) and scale unchanged, and the whole block is asserted in the shot (fitScreenToRiskBlock): the
     * simulation shot's rule, extended to these four blocks — the exception is the simulation and the four Dashboard Risk
     * blocks, desktop only (coordinator's decision, provisional). The mobile project keeps its phone: a block taller than
     * it shows its top part. Each shot asserts in frame the parts the page names first, and logs where every part lies
     * (🖼️ ✓ whole · ◐ partly · ✗ out · – not drawn).
     */
    test.describe('Dashboard Risk', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        /** The space the frame leaves above a block — and, on the desktop's fitted screen, below it: the simulation shot's. */
        const RISK_FRAME_MARGIN = 8;

        /**
         * Load the Dashboard on its Risk tab and end on every answer the four levels read being in: the period, the
         * capability catalogue and both base waves, the report the money lines are read from, and the benchmark picker's
         * asset list and verdicts — so every name the levels print has been read, and nothing redraws for a late one.
         */
        async function openRiskTab(page: Page): Promise<Locator> {
            // The live report, not the snapshot: the risk tab measures the gallery DB's own portfolio.
            await navigateTo(page, '/dashboard');
            await expect(page.getByTestId('date-preset-1y'), 'the Dashboard opened on another period than 1Y').toHaveAttribute('data-active', 'true', {timeout: 15_000});
            await page.getByTestId('dashboard-tab-risk').click();
            await expect(page.getByTestId('dashboard-risk-tab')).toBeVisible({timeout: 15_000});
            await freezeAnimations(page);
            const levels = page.getByTestId('risk-levels-panel');
            await expect(levels).toHaveAttribute('data-catalog', 'ready', {timeout: 30_000});
            await expect(levels).toHaveAttribute('data-busy', 'false', {timeout: 60_000});
            await waitForSettled(page.getByTestId('dashboard-page'), 30_000);
            await expect(levels.getByTestId('risk-l3-benchmark-select-control'), "the benchmark picker never had the asset list and the engine's verdicts").toHaveAttribute('data-eligibility', 'ready', {timeout: 30_000});
            return levels;
        }

        /**
         * The last steps before a shot: the pointer parked where nothing reacts to it and no tooltip left, every image of
         * the block loaded, every chart's pixels still and no figure counting up, nothing animating or moving, no toast.
         */
        async function settleRiskShot(page: Page, region: Locator, what: string): Promise<void> {
            await parkPointer(page);
            await imagesSettled(region);
            await canvasStill(region, what);
            await textStill(region, what);
            await waitForMotionSettled(region, what);
            await waitForStillness(region, what);
            await expectNoToast(page);
        }

        /** Log where each part of the shot lies on the screen: what the image holds, beyond what the test asserts in frame. */
        async function logFrame(page: Page, shot: string, parts: Readonly<Record<string, Locator>>): Promise<void> {
            console.log(`  🖼️  ${shot}: ${await framedParts(page, parts)}`);
        }

        /**
         * DESKTOP — the simulation shot's rule, extended to the four Risk blocks (coordinator's decision, provisional; see the
         * comment in 'risk what-if simulation on the dashboard'): the page wants the whole block in one image, and none fits
         * the desktop project's 720 px. Called once the block is framed and settled — every verdict, chart and answer in it
         * drawn and still — it measures the block, gives the screen its height plus the frame's margins (never under 720;
         * width and scale unchanged), logs it (📐), frames the block again, settles it again — a resize may redraw a chart,
         * which the settle waits out (canvasStill reads the pixels and the render counters) — and asserts the whole block in
         * the shot. One call per test: reverting the decision is deleting those four calls.
         */
        async function fitScreenToRiskBlock(page: Page, block: Locator, shot: string, what: string): Promise<void> {
            const fit = await fitViewportToBlock(page, block, RISK_FRAME_MARGIN, 720);
            console.log(`  📐 ${shot}: Risk block ${fit.blockHeight} px → screen ${page.viewportSize()?.width}×${fit.viewportHeight}`);
            await frameFromTop(page, block, RISK_FRAME_MARGIN);
            await settleRiskShot(page, block, what);
            await expect(block, `${what}: the block is not whole in the shot`).toBeInViewport({ratio: 1});
        }

        test('dashboard risk how much can it hurt - all languages and themes', async ({page}, testInfo) => {
            // Eight combinations, each a fresh Dashboard load with the risk tab's two base waves over a year of the admin's
            // portfolio and the benchmark picker's verdicts. About 15 s a combination on a quiet lane; risk answers slow down
            // under load. On the desktop each combination settles twice: to measure the block, then on its fitted screen.
            test.setTimeout(360_000); // 6 minutes
            const viewport = getViewport(testInfo);
            const guard = await guardReadOnly(page);
            // No benchmark: L3 asks no comparison, which this shot does not show.
            await seedDashboardBenchmark(page, await currentUserId(page), null);
            await navigateTo(page, '/dashboard');
            await selectOneYearPreset(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                const levels = await openRiskTab(page);
                const level = levels.getByTestId('risk-level-1');
                await expect(level.getByTestId('risk-l1-loading')).toHaveCount(0);
                await expect(level.getByTestId('risk-level-1-alert'), 'a measurement of How much can it hurt? did not come back').toHaveCount(0);

                // The cards, from A bad day to The worst fall, each with its amount — the loss applied to the net worth, so the
                // Dashboard's report reached the tab — and the detail lines the page names: the worst day actually seen under A
                // bad day; the fall's duration, the rise it needs, the drawdown at risk and the average beyond it under The
                // worst fall.
                const cards = level.getByTestId('risk-l1-cards');
                for (const row of ['day', 'month', 'worst'] as const) {
                    await expect(cards.getByTestId(`risk-l1-card-${row}-caption`), `the ${row} card has no amount: the Dashboard's net worth never reached the tab`).toHaveText(/\d/, {timeout: 20_000});
                }
                for (const line of ['risk-l1-worst-realization', 'risk-l1-duration-worst', 'risk-l1-recovery-worst', 'risk-l1-drawdown-at-risk', 'risk-l1-conditional-drawdown-at-risk']) {
                    await expect(cards.getByTestId(line), `the detail line ${line} is not drawn`).toBeVisible();
                }
                await expect(cards.locator('[data-columns]'), 'the card grid has not measured its columns').toHaveAttribute('data-columns', /^\d+$/);

                // Time spent below the peak, drawn, with its ulcer index; the distribution of daily returns, with its VaR threshold.
                const underwater = level.getByTestId('risk-l1-underwater');
                const underwaterChart = underwater.getByTestId('risk-l1-underwater-chart');
                await waitForChart(underwaterChart, 30_000);
                await expect(underwater.getByTestId('risk-l1-ulcer')).toBeVisible();
                const histogram = level.getByTestId('risk-l1-histogram');
                await expect(histogram.getByTestId('risk-l1-histogram-bars')).toHaveAttribute('data-bin-count', /^[1-9]\d*$/);
                await expect(histogram.getByTestId('risk-l1-histogram-cut'), 'the distribution of daily returns has no VaR threshold').toBeVisible();

                // «Currently down from the peak» is drawn only while the portfolio stands below its last high: a fact of the
                // day's prices, not of the page. It comes from the answer the chart above is drawn from, already in, so its
                // presence is read, not awaited; drawn, it carries its amount and its peak's date. The log says which it was.
                const current = cards.getByTestId('risk-l1-card-current');
                if ((await current.count()) > 0) {
                    await expect(current.getByTestId('risk-l1-card-current-caption'), 'the current fall has no amount').toHaveText(/\d/);
                    await expect(current.getByTestId('risk-l1-current-since')).toBeVisible();
                }

                // From the top of the block: its title and the first card in frame on every screen.
                await frameFromTop(page, level, RISK_FRAME_MARGIN);
                await settleRiskShot(page, level, 'How much can it hurt?');
                // DESKTOP — the simulation shot's rule (coordinator's decision, see its comment): a screen as tall as the whole block.
                if (viewport === 'desktop') await fitScreenToRiskBlock(page, level, `desktop/${lang}/${theme}/dashboard/risk-hurt`, 'How much can it hurt?');
                for (const part of [level.getByTestId('risk-level-1-title'), cards.getByTestId('risk-l1-card-day')]) await expect(part, 'the top of the block falls outside the shot').toBeInViewport({ratio: 1});
                await logFrame(page, `${viewport}/${lang}/${theme}/dashboard/risk-hurt`, {
                    cards,
                    'currently down': current,
                    'below the peak': underwaterChart,
                    'ulcer index': underwater.getByTestId('risk-l1-ulcer'),
                    distribution: histogram.getByTestId('risk-l1-histogram-bars'),
                    'VaR threshold': histogram.getByTestId('risk-l1-histogram-cut'),
                });
                await screenshot(page, viewport, lang, theme, 'dashboard', 'risk-hurt');

                await scrollBackToHeader(page);
            });
            expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started').toEqual([]);
        });

        test('dashboard risk diversification - all languages and themes', async ({page}, testInfo) => {
            // Eight combinations, each a fresh Dashboard load with the two base waves and the picker's verdicts, the matrix
            // drawn, then a second of stillness for the cards' count-up. About 15 s a combination on a quiet lane. On the
            // desktop each combination settles twice: to measure the block, then on its fitted screen.
            test.setTimeout(360_000); // 6 minutes
            const viewport = getViewport(testInfo);
            const guard = await guardReadOnly(page);
            // No benchmark: L3 asks no comparison, which this shot does not show.
            await seedDashboardBenchmark(page, await currentUserId(page), null);
            await navigateTo(page, '/dashboard');
            await selectOneYearPreset(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                const levels = await openRiskTab(page);
                const level = levels.getByTestId('risk-level-2');
                await expect(level.getByTestId('risk-l2-loading')).toHaveCount(0);
                await expect(level.getByTestId('risk-level-2-alert'), 'a measurement of Am I as diversified as I think? did not come back').toHaveCount(0);

                // The lead, written only when one holding carries at least 5 points more of the risk than of the money
                // (levelHelpers.ts, leadDivergence) — on the seeded portfolio, the crypto. Then the three cards, laid out once
                // measured, and the line on what the level does not cover.
                const lead = level.getByTestId('risk-level-2-lead');
                await expect(lead, 'no holding stands out: the lead sentence the page shows is not written').toBeVisible();
                const metrics = level.getByTestId('risk-l2-metrics');
                for (const card of ['effective-assets', 'diversification-ratio', 'uncovered']) await expect(metrics.getByTestId(`risk-l2-card-${card}`)).toBeVisible();
                await expect(metrics, 'the card grid has not measured its columns').toHaveAttribute('data-columns', /^\d+$/);
                await expect(level.getByTestId('risk-l2-uncovered')).toBeVisible();

                // The holdings, each with its weight, its share of the risk and its two-sided bar.
                const holdings = level.getByTestId('risk-l2-rows');
                const rows = holdings.locator('[data-testid^="risk-l2-row-"]');
                await expect.poll(() => rows.count(), {message: 'the list of holdings is empty'}).toBeGreaterThan(1);
                const rowCount = await rows.count();
                for (const part of ['weight', 'contribution', 'divergence-bar']) await expect(holdings.locator(`[data-testid^="risk-l2-${part}-"]`), `a holding has no ${part}`).toHaveCount(rowCount);

                // Which of these are the same bet?: the matrix drawn over the holdings, and its two lists of pairs.
                const matrix = level.getByTestId('risk-l2-correlation');
                await waitForChart(matrix, 30_000);
                const heatmap = matrix.getByTestId('risk-correlation-heatmap');
                await expect.poll(async () => idSet(await heatmap.getAttribute('data-asset-order')).length, {message: 'the matrix draws fewer than two holdings'}).toBeGreaterThan(1);
                await expect(matrix.getByTestId('risk-correlation-pairs-correlated')).toBeVisible();
                await expect(matrix.getByTestId('risk-correlation-pairs-offsetting')).toBeVisible();

                // From the top of the block: its title, the lead and the three cards in frame on every screen.
                await frameFromTop(page, level, RISK_FRAME_MARGIN);
                await settleRiskShot(page, level, 'Am I as diversified as I think?');
                // DESKTOP — the simulation shot's rule (coordinator's decision, see its comment): a screen as tall as the whole block.
                if (viewport === 'desktop') await fitScreenToRiskBlock(page, level, `desktop/${lang}/${theme}/dashboard/risk-diversification`, 'Am I as diversified as I think?');
                for (const part of [level.getByTestId('risk-level-2-title'), lead, metrics]) await expect(part, 'the top of the block falls outside the shot').toBeInViewport({ratio: 1});
                await logFrame(page, `${viewport}/${lang}/${theme}/dashboard/risk-diversification`, {
                    cards: metrics,
                    holdings,
                    matrix: heatmap,
                    pairs: matrix.getByTestId('risk-correlation-pairs'),
                });
                await screenshot(page, viewport, lang, theme, 'dashboard', 'risk-diversification');

                await scrollBackToHeader(page);
            });
            expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started').toEqual([]);
        });

        test('dashboard risk being paid against a benchmark - all languages and themes', async ({page}, testInfo) => {
            // Eight combinations, each a fresh Dashboard load with the two base waves and the picker's verdicts, then the MSCI
            // World comparison, asked once the picker confirms the stored choice. About 20 s a combination on a quiet lane. On
            // the desktop each combination settles twice: to measure the block, then on its fitted screen.
            test.setTimeout(420_000); // 7 minutes
            const viewport = getViewport(testInfo);
            const guard = await guardReadOnly(page);
            const userId = await currentUserId(page);
            const benchmarkId = await assetIdNamed(page, DASHBOARD_BENCHMARK_NAME);
            // «Compared with»: the MSCI World Index, chosen in the browser before every load — never in the database.
            await seedDashboardBenchmark(page, userId, benchmarkId);
            await navigateTo(page, '/dashboard');
            await selectOneYearPreset(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                const levels = await openRiskTab(page);
                const level = levels.getByTestId('risk-level-3');
                await expect(level.getByTestId('risk-l3-loading')).toHaveCount(0);

                // The choice confirmed — the index is priced over the whole period, so the engine lets it be measured — and
                // its comparison back: nobody holds the index, so the table adds its row under the Portfolio's.
                const benchmark = level.getByTestId('risk-l3-benchmark');
                await expect(benchmark).toHaveAttribute('data-benchmark-state', 'set', {timeout: 20_000});
                await expect(benchmark).toHaveAttribute('data-benchmark-id', String(benchmarkId));
                const table = level.getByTestId('risk-l3-table');
                await expect(table, 'the MSCI World comparison did not come back').toHaveAttribute('data-reference-count', '2', {timeout: 60_000});
                const portfolioRow = table.locator('[data-testid="risk-l3-row-ref-name"][data-reference="portfolio"]');
                const benchmarkRow = table.locator(`[data-testid="risk-l3-row-ref-name"][data-reference="benchmark"][data-asset-id="${benchmarkId}"]`);
                await expect(portfolioRow).toBeVisible();
                await expect(benchmarkRow).toBeVisible();
                // The table opens on them, in that order: nobody sorted it.
                await expect
                    .poll(() => table.locator('[data-testid="risk-l3-row-ref-name"], [data-testid="risk-l3-row-name"]').evaluateAll((cells) => cells.slice(0, 2).map((cell) => cell.getAttribute('data-reference'))), {
                        message: 'the table does not open on the Portfolio and the benchmark',
                    })
                    .toEqual(['portfolio', 'benchmark']);
                // Beta and correlation, the comparison's own columns, measured for the portfolio.
                for (const column of ['beta', 'correlation']) await expect(table.locator(`[data-testid="risk-l3-row-ref-${column}"][data-measured="true"]`), `the portfolio's ${column} is not measured`).toHaveCount(1);
                await expect(level.getByTestId('risk-level-3-alert'), 'a measurement of Am I being paid for this risk? did not come back').toHaveCount(0);

                // The chart: every dot placed — the holdings', the portfolio's, the benchmark's diamond — and the dashed line
                // drawn through the benchmark, as the note under the chart says.
                const scatter = level.getByTestId('risk-l3-scatter');
                await waitForChart(scatter, 30_000);
                await expect(scatter).toHaveAttribute('data-dropped-count', '0');
                const lineNote = level.getByTestId('risk-l3-scatter-line');
                await expect(lineNote).toHaveAttribute('data-anchor', 'benchmark');

                // From the top of the block: its title, «Compared with» and the table's first two rows in frame on every screen.
                await frameFromTop(page, level, RISK_FRAME_MARGIN);
                await settleRiskShot(page, level, 'Am I being paid for this risk?');
                // DESKTOP — the simulation shot's rule (coordinator's decision, see its comment): a screen as tall as the whole block.
                if (viewport === 'desktop') await fitScreenToRiskBlock(page, level, `desktop/${lang}/${theme}/dashboard/risk-paid`, 'Am I being paid for this risk?');
                for (const part of [level.getByTestId('risk-level-3-title'), benchmark, portfolioRow, benchmarkRow]) await expect(part, 'the top of the block falls outside the shot').toBeInViewport({ratio: 1});
                await logFrame(page, `${viewport}/${lang}/${theme}/dashboard/risk-paid`, {table, chart: scatter, 'line note': lineNote});
                await screenshot(page, viewport, lang, theme, 'dashboard', 'risk-paid');

                await scrollBackToHeader(page);
            });
            await forgetDashboardRiskMemory(page, userId);
            expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started').toEqual([]);
        });

        test('dashboard risk what-if crisis replay (injected window) - all languages and themes', async ({page}, testInfo) => {
            // Eight combinations, each a fresh Dashboard load with the two base waves and the picker's verdicts, then What
            // if…? opened (the scenario catalogue) and one replay; the first replay also asks the portfolio's deepest fall.
            // About 20 s a combination on a quiet lane. On the desktop each combination settles twice: to measure the block,
            // then on its fitted screen.
            test.setTimeout(480_000); // 8 minutes
            const viewport = getViewport(testInfo);
            const guard = await guardReadOnly(page);
            const userId = await currentUserId(page);
            await forgetWhatIfTools(page, userId);
            // No benchmark: L3 asks no comparison, which this shot does not show.
            await seedDashboardBenchmark(page, userId, null);
            const crisis = await historicalReplayPreset(page, CRISIS_PRESET_ID);
            // INJECTED (galleryRiskDashboard.ts, injectCrisisReplay): the Global Financial Crisis's replay, asked over the
            // crisis's own dates, is answered with the engine's own answer over the portfolio's deepest fall in the page's
            // period. The gallery's prices cover about the last year: replayed for real, the crisis leaves every holding out.
            const injection = await injectCrisisReplay(page, crisis);
            await navigateTo(page, '/dashboard');
            await selectOneYearPreset(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                const levels = await openRiskTab(page);

                // What if…? is born closed, and with no tool open (the init script forgets the ones left open): opened from its
                // title, then the replay added the way a user adds it, the Add: buttons left for the other two tools.
                const whatIf = levels.getByTestId('risk-level-4');
                await expect(whatIf).toHaveAttribute('data-open', 'false');
                await whatIf.getByTestId('risk-level-4-toggle').click();
                await expect(whatIf).toHaveAttribute('data-open', 'true');
                const tools = whatIf.getByTestId('risk-l4-tools');
                await expect(tools).toBeVisible();
                const box = whatIf.getByTestId('risk-l4-replay');
                await expect(box, 'a What if…? tool came back open').toHaveCount(0);
                await tools.getByTestId('risk-l4-add-replay').click();
                await expect(box).toBeVisible();
                await expect(tools.getByTestId('risk-l4-add-replay')).toHaveCount(0);
                for (const tool of ['shock', 'simulation']) await expect(tools.getByTestId(`risk-l4-add-${tool}`)).toBeVisible();

                // The crisis chosen in Preset — it sets the period to the crisis's dates, which the compact fields print as
                // they are — then Run replay. The answer is the engine's over the deepest fall; the request it answers proves
                // the box asked the crisis's own dates.
                const replay = box.getByTestId('risk-replay');
                await chooseReplayPreset(replay, crisis.id);
                const period = replay.getByTestId('risk-replay-period');
                await expect(period.getByTestId('date-range-input-start'), "the crisis did not set the period's start").toHaveValue(crisis.start);
                await expect(period.getByTestId('date-range-input-end'), "the crisis did not set the period's end").toHaveValue(crisis.end);
                const run = replay.getByTestId('risk-replay-run');
                await expect(run).toBeEnabled();
                const editedBefore = injection.edited;
                await run.click();
                await expect.poll(() => injection.edited - editedBefore + injection.problems.length, {message: "the box never asked the crisis's replay: the preset did not set its dates", timeout: 120_000}).toBeGreaterThanOrEqual(1);
                expect(injection.problems, 'the crisis replay was not answered over the deepest fall').toEqual([]);
                const fall = injection.fall;
                if (!fall || injection.total === null) throw new Error('the edited replay names no fall or no total');
                console.log(`  🧪 ${viewport}/${lang}/${theme}/dashboard/risk-whatif: ${crisis.start}…${crisis.end} answered over the deepest fall ${fall.start}…${fall.end} (total ${(injection.total * 100).toFixed(2)}%, ${injection.rows} rows)`);

                // The answer on screen: the total sentence, and one row per holding replayed with what it did to the whole.
                const total = replay.getByTestId('risk-replay-total');
                await expect(total).toBeVisible({timeout: 30_000});
                await expect(run).toBeEnabled({timeout: 30_000});
                await expect(replay.getByTestId('risk-replay-nothing')).toHaveCount(0);
                const tornado = replay.getByTestId('risk-replay-tornado');
                await expect(tornado.getByTestId('risk-replay-tornado-row')).toHaveCount(injection.rows);
                await expect(tornado.getByTestId('risk-replay-tornado-contribution')).toHaveCount(injection.rows);

                // From the top of the block: its title, the Add: buttons, the crisis, its period and the total sentence in frame
                // on every screen; on the desktop, the table's first row as well.
                await frameFromTop(page, whatIf, RISK_FRAME_MARGIN);
                await settleRiskShot(page, whatIf, 'What if…?');
                // DESKTOP — the simulation shot's rule (coordinator's decision, see its comment): a screen as tall as the whole block.
                if (viewport === 'desktop') await fitScreenToRiskBlock(page, whatIf, `desktop/${lang}/${theme}/dashboard/risk-whatif`, 'What if…?');
                const framed = [whatIf.getByTestId('risk-level-4-title'), tools, replay.getByTestId('risk-replay-preset'), period, total];
                if (viewport === 'desktop') framed.push(tornado.getByTestId('risk-replay-tornado-row').first());
                for (const part of framed) await expect(part, 'a part the page names falls outside the shot').toBeInViewport({ratio: 1});
                await logFrame(page, `${viewport}/${lang}/${theme}/dashboard/risk-whatif`, {
                    notice: whatIf.getByTestId('risk-level-4-alert'),
                    'left out': replay.getByTestId('risk-replay-excluded'),
                    total,
                    table: tornado,
                });
                await screenshot(page, viewport, lang, theme, 'dashboard', 'risk-whatif');

                await scrollBackToHeader(page);
            });
            await forgetDashboardRiskMemory(page, userId);
            expect(guard.syncs, 'a sync, a metadata refresh or a provider probe was started').toEqual([]);
        });
    });
});
