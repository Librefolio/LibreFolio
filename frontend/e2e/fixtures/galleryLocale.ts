/**
 * The browser locale of a gallery shot: an Italian shot is taken by an Italian browser.
 *
 * The UI language and the browser locale are two settings. The header's selector sets the first; the second is the
 * browser's own. Since M-18 the app writes every figure in the interface locale (`uiLocale()`,
 * `frontend/src/lib/stores/app/uiLocale.ts`): the interface language, plus the region of `navigator.language` only when
 * it speaks that language and names one — otherwise British English for English, the bare language for the others.
 *
 * The locale this file sets is not `navigator.language`. It is the one `Intl` and `toLocaleString()` fall back on when
 * given none, and the Accept-Language of the requests; through it all, the gallery's headless Chromium answers
 * `navigator.language` with en-US (measured on Chromium 149 under macOS in Italian, with LANG C, it_IT and en_GB). So
 * the English shots are American («Oct 12, 2026»), and the others take their bare language, which writes as it-IT, fr-FR
 * and es-ES do. Pinning the browser locale still covers whatever formats without one — a library, the browser's own
 * controls — and keeps each shot independent of the machine's own locale.
 *
 * ## Set at runtime, not as a context option
 *
 * Playwright's `locale` is fixed when the context is created, and a gallery test walks the four languages inside one
 * page. In Chromium that option is `Emulation.setLocaleOverride`; sent from the test's own CDP session, the same command
 * switches the locale of the running page — desktop and phone alike, kept across reloads and navigations.
 *
 * The trap: Chromium takes one override at a time and refuses a second session's («Another locale override is already
 * in effect»), and @playwright/test gives every context `locale: 'en-US'`, so its own session holds one from the start.
 * The gallery's describe therefore yields no locale at all —
 *
 *     test.use({locale: async ({}, use) => use(undefined)});
 *
 * — since `test.use({locale: undefined})` falls back to that very default. Then nothing pins en-US but the gallery: its
 * beforeEach sets it before the first load, whatever the locale of the machine.
 *
 * ## Before the page is drawn
 *
 * What a page has drawn keeps the browser locale it was drawn under: the override takes effect at once, yet nothing on
 * screen is formatted again for it. A switch of the interface language redraws the figures written through `uiLocale()`,
 * not necessarily the rest, and a client-side route keeps the document. Only a new document, a load or a reload, is drawn
 * whole under the new locale. So the locale of a shot is set before its page is loaded: first thing in every language
 * loop of the gallery, or in the test such a loop generates.
 *
 * The stamp makes that checkable instead of hoped for. {@link stampDocumentLocale} has every document record the locale
 * it began under; {@link expectDrawnUnder} reads it at the shot. A forgotten switch point is a red naming its shot, not
 * an en-US number in an Italian picture.
 */

import type {CDPSession} from '@playwright/test';
import {expect, type Page} from './playwright';
import type {Language} from './test-users';

/** The browser locale of each gallery language. */
export const GALLERY_LOCALES: Record<Language, string> = {en: 'en-US', it: 'it-IT', fr: 'fr-FR', es: 'es-ES'};

/** Where a document keeps the locale it began under: a property of `window` no code of the app's could own. */
const STAMP = '__lfDocumentLocale';

/** The page's own CDP session, opened on first use, and the locale it set last. */
const sessions = new WeakMap<Page, {cdp: Promise<CDPSession>; locale: string | null}>();

/**
 * The browser in `lang`'s locale — its number and date formats, and the Accept-Language of its requests. What the page
 * has drawn stays as it was drawn: only a document loaded from now on is drawn whole under the new locale. A no-op when
 * the locale is already `lang`'s.
 */
export async function setBrowserLocale(page: Page, lang: Language): Promise<void> {
    const locale = GALLERY_LOCALES[lang];
    let held = sessions.get(page);
    if (!held) {
        held = {cdp: page.context().newCDPSession(page), locale: null};
        sessions.set(page, held);
    }
    if (held.locale === locale) return;
    try {
        await (await held.cdp).send('Emulation.setLocaleOverride', {locale});
    } catch (error) {
        const reason = error instanceof Error ? error.message : String(error);
        throw new Error(
            `The browser locale ${locale} was refused: ${reason}. It is set from the test's own CDP session (Chromium only), and Chromium refuses it while the context holds a locale of its own — ` +
                "@playwright/test gives every context 'en-US'. The describe must yield none: test.use({locale: async ({}, use) => use(undefined)}); test.use({locale: undefined}) keeps the default.",
        );
    }
    await page.setExtraHTTPHeaders({'Accept-Language': `${locale},${lang};q=0.9`});
    held.locale = locale;
}

/**
 * Every document the page loads from now on records the locale it began under — before its own scripts run, so before
 * anything is formatted. Registered before the first load.
 */
export async function stampDocumentLocale(page: Page): Promise<void> {
    await page.addInitScript((key) => {
        (window as unknown as Record<string, string>)[key] = new Intl.NumberFormat().resolvedOptions().locale;
    }, STAMP);
}

/**
 * The document on screen began under `lang`'s browser locale, or the shot fails: a page drawn under another locale keeps
 * its numbers and dates, whatever language its labels speak by now. A document without a stamp fails too — nothing says
 * what it was drawn under.
 */
export async function expectDrawnUnder(page: Page, lang: Language): Promise<void> {
    const expected = GALLERY_LOCALES[lang];
    const drawnUnder = await page.evaluate((key) => {
        const stamp = (window as unknown as Record<string, unknown>)[key];
        return typeof stamp === 'string' ? stamp : null;
    }, STAMP);
    const message =
        drawnUnder === null
            ? `the page of this ${lang} shot carries no locale stamp, so nothing says it was drawn under ${expected}: stampDocumentLocale() must be registered before the first load`
            : `the page of this ${lang} shot was drawn under ${drawnUnder}, not ${expected}: set the browser locale before loading the page of a ${lang} shot`;
    expect(drawnUnder, message).toBe(expected);
}
