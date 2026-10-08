/**
 * Gallery, inventory group 5 — onboarding: the first-run Welcome page, a step of the Core tour, a
 * contextual guide on the FX page, and the Onboarding category of Preferences.
 *
 * ## Accounts
 *
 * Onboarding is persisted per user, and the canonical E2E users have completed every flow
 * (populate_mock_data `_grandfather_onboarding_for_test_users`), so the first three shots each run as
 * a disposable account: signed up by the test (`registerGalleryAccount`: `demo_` and a random token,
 * a name the sidebar shows), deleted by its afterEach with everything it owns, failure or not
 * (`cleanupGalleryAccount`).
 *
 * One account per test, not one per combination, so the eight variants of a shot show the same
 * account. That holds because what changes from one combination to the next lives in the browser:
 *
 * - The language and the theme a page is drawn in: `librefolio-locale` and `librefolio-theme` in
 *   localStorage, read at boot by i18n and by app.html's theme script ({@link seedLanguageAndTheme})
 *   and applied by the next full load. Only a sign-in applies the account's own settings, and each
 *   test signs in once, before its first shot.
 * - A guide's position, kept per account in localStorage (onboarding.svelte.ts): walked once to its
 *   step, the Core tour and the FX page guide resume on that step after every full load — the
 *   product's own contract, which every combination asserts ({@link expectGuideStep}). Their Welcome
 *   is confirmed once, before the walk, so nothing on the server sets the language again afterwards.
 *
 * One thing is the account's: the Welcome form is pre-filled from its settings, so before each load
 * of it the account's language is set to the combination's ({@link setAccountLanguage}, the
 * account's own row). That test never confirms Welcome, which stays due on every load.
 *
 * The fourth shot runs as the admin and only reads: the category is a view of the Preferences tab,
 * and Replay and Replay all are never pressed (each arms a replay).
 *
 * ## Third parties
 *
 * The gallery-wide offline guard (galleryReportSets.ts, `guardGalleryOffline`) keeps every page of
 * these tests from reaching a provider, or GitHub. The FX page asks for the exchange-rate provider
 * catalogue on every load (currencyGraphStore.ts) — which the backend answers by asking ECB and SNB
 * over the network — and the guard answers it from its fixture; the grid of cards draws nothing from
 * it (only the table's provider badges do). Any sync is aborted, and fails the test at its end.
 */

import {expect, type APIRequestContext, type Locator, type Page} from './playwright';
import {frameFromTop, parkPointer} from './galleryRiskLab';
import type {Language} from './test-users';

export type Theme = 'light' | 'dark';

/** The id every guide target names in `aria-describedby` while its step is on screen (OnboardingCoachmark.svelte). */
const DESCRIPTION_ID = 'onboarding-coachmark-description';

// ---------------------------------------------------------------------------
// Language and theme
// ---------------------------------------------------------------------------

/** Write the language and the theme the next full load draws the page in. `page` must be on the app's origin. */
export async function seedLanguageAndTheme(page: Page, lang: Language, theme: Theme): Promise<void> {
    await page.evaluate(
        ([locale, look]) => {
            localStorage.setItem('librefolio-locale', locale);
            localStorage.setItem('librefolio-theme', look);
        },
        [lang, theme] as [string, string],
    );
}

/** The page speaks `lang`, its dictionary is in, and it is drawn in `theme` — the class app.html's theme script sets on `<html>`. */
export async function expectLanguageAndTheme(page: Page, lang: Language, theme: Theme): Promise<void> {
    const html = page.locator('html');
    await expect(html).toHaveAttribute('lang', lang, {timeout: 15_000});
    await expect(html).toHaveAttribute('data-i18n-ready', 'true', {timeout: 15_000});
    await expect(html, `the page is not drawn in the ${theme} theme`).toHaveClass(new RegExp(`(^|\\s)${theme}(\\s|$)`));
}

// ---------------------------------------------------------------------------
// The Welcome page
// ---------------------------------------------------------------------------

/** What the Welcome form is pre-filled from: the account's own settings (`UserSettingsRead`), reduced to what is read here. */
export type WelcomeDefaults = {language: string; base_currency: string};

/**
 * Set the signed-in account's language — its own settings row, through the browser's session — and
 * return its settings as the server now holds them: what the Welcome form is pre-filled with.
 */
export async function setAccountLanguage(api: APIRequestContext, lang: Language): Promise<WelcomeDefaults> {
    const response = await api.put('/api/v1/settings/user', {data: {language: lang}});
    expect(response.ok(), `set the account's language to ${lang}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const settings = (await response.json()) as WelcomeDefaults;
    expect(settings.language, 'the server holds the language the form is pre-filled with').toBe(lang);
    expect(settings.base_currency, 'the account has a default currency to pre-fill').toMatch(/^[A-Z]{3}$/);
    return settings;
}

/**
 * The Welcome page from its end. A screen that holds the whole page does not move; on one that
 * does not, the top gives way: the picture, both fields and both actions — what the shot is about —
 * are wholly in the shot either way, or this fails.
 */
export async function frameWelcome(page: Page): Promise<void> {
    await page.evaluate(() => window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'}));
    for (const testId of ['welcome-avatar-preview', 'welcome-language', 'welcome-currency', 'welcome-skip', 'welcome-continue']) {
        await expect(page.getByTestId(testId), `${testId} is not wholly in the shot`).toBeInViewport({ratio: 1});
    }
}

// ---------------------------------------------------------------------------
// Guides
// ---------------------------------------------------------------------------

/** A guide step as the overlay presents it (OnboardingOverlayHost.svelte) and the element its anchor is on. */
export type GuideStep = {stepId: string; target: string; pointer: 'none' | 'cursor'; highlight: 'none' | 'pulse'; backdrop: boolean};

/** The Core tour's step on the Exchange rates destination: the page dimmed around it, a pulse and the cursor on it. */
export const CORE_TOUR_FX_STEP: GuideStep = {stepId: 'intro.fx_nav', target: 'nav-fx', pointer: 'cursor', highlight: 'pulse', backdrop: true};

/** The FX page guide's first step, an area: the page's title. */
export const FX_PAGE_OVERVIEW_STEP: GuideStep = {stepId: 'fx.page.overview', target: 'fx-page-overview-guide-target', pointer: 'none', highlight: 'pulse', backdrop: false};

/** Its second, an area over real controls: the currency filters. Never `fx.page.sync`, whose target starts a sync. */
export const FX_PAGE_FILTERS_STEP: GuideStep = {stepId: 'fx.page.filters', target: 'fx-page-filters', pointer: 'none', highlight: 'pulse', backdrop: false};

/** The Core tour in catalogue order (onboardingGuideCatalog.ts, CORE_TOUR_STEP_IDS), from its first step after the intro to Exchange rates. */
const CORE_TOUR_TO_FX = ['intro.navigation', 'intro.dashboard', 'intro.transactions_nav', 'intro.brokers_nav', 'intro.fx_nav'] as const;

type GuideSample = {
    coachmarks: number;
    stepId: string | null;
    guideState: string | null;
    geometryState: string | null;
    hidden: string | null;
    pointer: string | null;
    highlight: string | null;
    pointerShown: boolean;
    highlightShown: boolean;
    spotlight: boolean;
    described: string[];
};

/**
 * One atomic reading of the overlay — its published state, what it draws, and every element other
 * than its panel that names the coachmark description — taken in a single evaluate, so "step X,
 * anchored, still, describing only Y" holds at one instant instead of being assembled from reads
 * taken at different moments (the reading of onboarding-guides.spec.ts, with what it draws added).
 */
async function sampleGuide(page: Page): Promise<GuideSample | {unreadable: string}> {
    try {
        return await page.evaluate((descriptionId) => {
            const coachmarks = Array.from(document.querySelectorAll<HTMLElement>('[data-testid="onboarding-coachmark"]'));
            const coachmark = coachmarks.length === 1 ? coachmarks[0] : null;
            const draws = (testId: string) => (coachmark ? coachmark.querySelector(`[data-testid="${testId}"]`) !== null : false);
            const described = Array.from(document.querySelectorAll<HTMLElement>(`[aria-describedby="${descriptionId}"]`))
                .filter((element) => element.dataset.testid !== 'onboarding-coachmark-panel')
                .map((element) => element.dataset.testid ?? `<${element.tagName.toLowerCase()} without data-testid>`);
            return {
                coachmarks: coachmarks.length,
                stepId: coachmark?.dataset.stepId ?? null,
                guideState: coachmark?.dataset.guideState ?? null,
                geometryState: coachmark?.dataset.geometryState ?? null,
                hidden: coachmark?.getAttribute('aria-hidden') ?? null,
                pointer: coachmark?.dataset.pointer ?? null,
                highlight: coachmark?.dataset.highlight ?? null,
                pointerShown: draws('onboarding-coachmark-pointer'),
                highlightShown: draws('onboarding-coachmark-highlight'),
                spotlight: draws('onboarding-spotlight-top'),
                described,
            };
        }, DESCRIPTION_ID);
    } catch (error) {
        // A navigation can replace the execution context between two readings: "not on screen yet".
        return {unreadable: String(error)};
    }
}

/**
 * `step` is on screen: one coachmark, on that step, anchored on a still target, drawing what the step
 * draws, its target the one element described — visible, in the viewport — and its message panel
 * wholly in the viewport. Returns the panel.
 */
export async function expectGuideStep(page: Page, step: GuideStep, timeout = 15_000): Promise<Locator> {
    await expect
        .poll(() => sampleGuide(page), {timeout, message: `the guide never showed ${step.stepId} anchored on a still ${step.target}`})
        .toEqual({
            coachmarks: 1,
            stepId: step.stepId,
            guideState: 'anchored',
            geometryState: 'stable',
            hidden: 'false',
            pointer: step.pointer,
            highlight: step.highlight,
            pointerShown: step.pointer === 'cursor',
            highlightShown: step.highlight === 'pulse',
            spotlight: step.backdrop,
            described: [step.target],
        });
    await expect(page.getByTestId(step.target), `${step.stepId} points at a target the user can see`).toBeInViewport();
    const panel = page.getByTestId('onboarding-coachmark-panel');
    await expect(panel, `the message panel of ${step.stepId} is not wholly on screen`).toBeInViewport({ratio: 1});
    return panel;
}

/**
 * From the intro scene that follows Welcome: Start, then Next, one step at a time — each step
 * reached before the next press — up to the Exchange rates destination, where it ends anchored.
 */
export async function walkCoreTourToFx(page: Page): Promise<void> {
    const scene = page.getByTestId('onboarding-intro-scene');
    await expect(scene).toHaveAttribute('data-state', 'intro-scene', {timeout: 10_000});
    await page.getByTestId('onboarding-intro-start').click();
    await expect(scene).toHaveCount(0);
    const coachmark = page.getByTestId('onboarding-coachmark');
    for (const [index, stepId] of CORE_TOUR_TO_FX.entries()) {
        if (index > 0) await page.getByTestId('onboarding-coachmark-next').click();
        await expect(coachmark, `the tour did not reach ${stepId}`).toHaveAttribute('data-step-id', stepId, {timeout: 10_000});
    }
    await expectGuideStep(page, CORE_TOUR_FX_STEP);
}

/**
 * Keep the message panel at full strength for the shot. It turns translucent 3 s after its step is
 * shown and comes back under the pointer (OnboardingCoachmark.svelte, `data-subdued`). The pointer
 * first leaves it — the panel keeps 16 px from every edge of the screen, the pointer rests on one —
 * and the fade is awaited, so the hover is proved to be what holds it solid, not a shot taken early.
 * Then the pointer rests in the middle of its top padding, where no control is.
 */
export async function holdPanelAtFullStrength(page: Page): Promise<Locator> {
    const panel = page.getByTestId('onboarding-coachmark-panel');
    await parkPointer(page);
    await expect(panel, 'the message panel never turned translucent').toHaveAttribute('data-subdued', 'true', {timeout: 10_000});
    const box = await panel.boundingBox();
    if (!box) throw new Error('the message panel has no box');
    await panel.hover({position: {x: Math.round(box.width / 2), y: 6}});
    await expect(panel, 'the message panel did not come back to full strength under the pointer').toHaveAttribute('data-subdued', 'false');
    return panel;
}

// ---------------------------------------------------------------------------
// Pages
// ---------------------------------------------------------------------------

/**
 * Every chart in `scope` has finished drawing (`data-chart-ready`, chartReady.ts), and there is at
 * least one: a page whose cards have nothing to draw is not the page the shot documents.
 */
export async function chartsDrawn(scope: Locator, what: string, timeout = 30_000): Promise<void> {
    await expect
        .poll(
            () =>
                scope.evaluate((root) => {
                    const charts = Array.from(root.querySelectorAll('[data-chart-ready]'));
                    if (charts.length === 0) return 'no chart';
                    const drawing = charts.filter((chart) => chart.getAttribute('data-chart-ready') !== 'true').length;
                    return drawing === 0 ? 'drawn' : `${drawing} of ${charts.length} still drawing`;
                }),
            {message: `${what}: a chart is still drawing, or none has anything to draw (the lane's rates may not cover the page's period: re-populate it)`, timeout},
        )
        .toBe('drawn');
}

/**
 * Narrow Preferences to its Onboarding category, through the control each layout offers
 * (SettingsLayout.svelte): the sidebar on a desktop, the category dropdown on a phone. Every load
 * opens on All. The end state is read on the sidebar's button, which publishes the one selection
 * both layouts share and stays in the DOM on a phone, where the dropdown closes on the choice.
 */
export async function chooseOnboardingCategory(page: Page, viewport: 'desktop' | 'mobile'): Promise<void> {
    const all = page.getByTestId('settings-category-all');
    const onboarding = page.getByTestId('settings-category-onboarding');
    await expect(all, 'Preferences opens on All').toHaveAttribute('aria-pressed', 'true');
    await expect(onboarding).toHaveAttribute('aria-pressed', 'false');
    if (viewport === 'mobile') {
        const option = page.getByTestId('settings-mobile-category-onboarding');
        await page.getByTestId('settings-mobile-category-trigger').click();
        await expect(option).toBeVisible();
        await expect(option).toHaveAttribute('aria-pressed', 'false');
        await option.click();
        await expect(option, 'the dropdown closes on the choice').toHaveCount(0);
    } else {
        await onboarding.click();
    }
    await expect(onboarding, 'the Onboarding category is the one selected').toHaveAttribute('aria-pressed', 'true');
    await expect(all).toHaveAttribute('aria-pressed', 'false');
}

/** The areas of the Onboarding category, in order (OnboardingReplaySection.svelte): the first two open on every load. */
const OPEN_GROUPS = ['setup', 'core'] as const;
const FOLDED_GROUPS = ['transactions', 'broker', 'fx', 'asset'] as const;

/**
 * The Onboarding category as every load opens it, settled: only its section on the page, the flows
 * loaded and nothing running (Replay all enabled), the first two areas open on their flow — each with
 * its status, its version line and its Replay action — the other four folded, no replay armed (a
 * fresh browser holds none, and none is armed here), no error. Returns the section.
 */
export async function expectOnboardingCategory(page: Page): Promise<Locator> {
    const section = page.getByTestId('onboarding-replay-section');
    await expect(section).toBeVisible({timeout: 15_000});
    await expect(section).toHaveAttribute('data-busy', 'false');
    await expect(section.getByTestId('onboarding-replay-all'), 'Replay all is enabled once the flows are in and nothing runs').toBeEnabled({timeout: 15_000});
    for (const field of ['preference-language', 'preference-currency', 'preference-theme']) {
        await expect(page.getByTestId(field), `${field} is not part of the Onboarding category`).toHaveCount(0);
    }
    for (const group of OPEN_GROUPS) await expect(section.getByTestId(`onboarding-group-${group}`)).toHaveAttribute('open', '');
    for (const group of FOLDED_GROUPS) {
        const folded = section.getByTestId(`onboarding-group-${group}`);
        await expect(folded).toBeVisible();
        await expect(folded).not.toHaveAttribute('open');
    }
    for (const flow of ['welcome', 'intro_tour']) {
        const row = section.getByTestId(`onboarding-flow-${flow}`);
        await expect(row).toBeVisible();
        await expect(row).toHaveAttribute('data-status', /^(pending|completed|skipped)$/);
        await expect(row).toHaveAttribute('data-version', /^\d+$/);
        await expect(row).toHaveAttribute('data-current-version', /^\d+$/);
        await expect(row.getByTestId(`onboarding-flow-${flow}-status`)).toBeVisible();
        await expect(row.getByTestId(`onboarding-replay-${flow}`)).toBeEnabled();
    }
    await expect(section.locator('[data-testid$="-armed"]'), 'a replay is armed in this browser').toHaveCount(0);
    await expect(section.getByTestId('onboarding-replay-error')).toHaveCount(0);
    await expect(section.getByTestId('onboarding-replay-load-error')).toHaveCount(0);
    return section;
}

/**
 * Frame the Onboarding category for its shot, and prove the frame holds what the shot documents: Replay all and the
 * Welcome setup row whole, and a second area — the Core tour's — at least by its top. A desktop shows all of it from
 * the top of the page. A phone does not: the tab bar, the category dropdown and the Preferences heading stack above
 * the card, and with Setup open the Core tour's area falls below the fold in the longer languages (in Spanish it is
 * out of the frame entirely). So on a phone the page is scrolled until the card's own header — its title and Replay
 * all — stands at the top of the screen: what stood above it leaves the frame, the app header slides away as on any
 * scroll down, and the Core tour's area comes in with its header. Nothing is opened: the areas stay as every load
 * opens them. A phone's frame is left scrolled down: {@link scrollBackToHeader} (galleryRiskLab.ts) brings back the
 * header's language and theme controls.
 */
export async function frameOnboardingCategory(page: Page, viewport: 'desktop' | 'mobile'): Promise<void> {
    const section = page.getByTestId('onboarding-replay-section');
    const core = section.getByTestId('onboarding-group-core');
    if (viewport === 'mobile') await frameFromTop(page, section);
    await expect(section.getByTestId('onboarding-replay-all')).toBeInViewport({ratio: 1});
    await expect(section.getByTestId('onboarding-flow-welcome')).toBeInViewport({ratio: 1});
    await expect(core, 'the Core tour area is out of the frame: the shot shows one area').toBeInViewport();
    // Its header carries the area's progress, on the summary's one row: whole on screen, the row is.
    if (viewport === 'mobile') await expect(core.getByTestId('onboarding-group-core-progress'), "the Core tour area's header is cut by the frame").toBeInViewport({ratio: 1});
}
