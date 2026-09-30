/**
 * fx-flag-font.spec.ts — K step 12b: which font actually draws a flag, read from the browser.
 *
 * The developer's decision (plan step 12, section b): ONE global font rule for flag characters, the
 * regional indicators U+1F1E6–1F1FF. The face is `'LF Flags'` (`static/lf-flags.css`) and it leads
 * the app's stacks. On Apple devices it resolves to the system Apple Color Emoji through `local()`;
 * elsewhere it downloads the one self-hosted Noto subset holding the flags
 * (`/fonts/noto-color-emoji/noto-color-emoji.0.woff2`). Every other emoji stays the system's, and no
 * emoji font may come before the text font — Inter, or the monospace font — for digits, '#', '*'.
 *
 * A stylesheet can say all that while the page draws something else, so this spec asks the browser.
 * The Chrome DevTools Protocol's `CSS.getPlatformFontsForNode` reports, for the text of a node, the
 * fonts that actually drew its glyphs: `{familyName, isCustomFont, glyphCount}`. A font loaded from
 * a URL reports the family written inside the file ('Noto Color Emoji'), not its @font-face name.
 *
 * Host-aware. Whether this host has Apple Color Emoji is itself read through CDP (a probe span set
 * in 'Apple Color Emoji'), not guessed from the user agent: the Desktop Chrome descriptor claims
 * Windows. On an Apple host the flags must be Apple Color Emoji's and nothing may be fetched from
 * the Noto directory; on any other host they must be 'Noto Color Emoji' and only the flags subset
 * may be fetched.
 *
 *   R1 (red before the fix, Apple host) Transactions cash cell: the flag is drawn by Apple Color
 *      Emoji. Before the fix, TransactionsTable puts 'Noto Color Emoji' first, so even a Mac downloads it.
 *      On an Apple host the flag looks the same through 'LF Flags' (`local()`) and through plain system
 *      fallback, so R1 also requires the document to declare the 'LF Flags' face and the flags to have
 *      engaged it (`document.fonts`, status "loaded").
 *   R2 (red before the fix, Apple host) Transactions, dashboard and FX show flags, and nothing is
 *      requested from /fonts/noto-color-emoji/: no subset, no generated stylesheet.
 *   R3 (red before the fix, Apple host) /offline.html: #lang-flag is drawn by Apple Color Emoji, through
 *      the page's own 'LF Flags' face.
 *   R4 (red before the fix) digits, '#', '*' inside `.emoji-flag` are drawn by the text font: before
 *      the fix that stack leads with the emoji families.
 *   C1 (control) a probe face identical to 'LF Flags' but without a matching local source — the
 *      Windows path — draws the flag with the self-hosted Noto subset and never digits, '#', '*'.
 *   C2 (control) digits beside a currency flag, and a flag sharing one text run with digits, are drawn
 *      by the text font (Inter where installed, the system-ui fallback otherwise) under the app's own
 *      html stack and its `font-mono`.
 *   C3 (premise) the target face, reached only through a stack by rendering a flag, loads and resolves
 *      on this host the way the contract expects — on an Apple host through local(), with no download —
 *      and the test records which of `local('Apple Color Emoji')` and `local('AppleColorEmoji')` Chrome
 *      matches here. R1–R3 can only turn green after the fix if this holds.
 *
 * No clock waits. A read comes after the page's own readiness signal (`data-busy="false"`), the node
 * showing its flag, and `document.fonts` settling to "loaded" after a forced layout, so every face the
 * text needs has been asked for. Reads are never polled towards the expected answer: a face still
 * loading draws with the fallback for a moment, and a poll would take that moment for the verdict.
 *
 * Owned data: R1, R2 and C2 create a broker (unique name) and two DEPOSITs through the API — EUR 🇪🇺
 * and USD 🇺🇸 — open `/transactions?broker_id=<own>`, and delete both rows and the broker at the end.
 * Nothing is located by position; the only `.first()` calls sit on collections already filtered to
 * flags, as presence barriers. Desktop Chromium only (CDP).
 *
 * Key hooks: transactions-page [data-busy], tx-cash-cell-{id} (`.emoji-flag`, `.currency-amount`
 * inside it are the subject, from `formatCurrencyAmountHtml`), dashboard-page [data-busy],
 * dashboard-cash-balances, fx-page [data-busy], fx-card-{slug}, offline.html #lang-flag.
 */

import type {CDPSession} from '@playwright/test';
import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;
const TEST_PORT = process.env.TEST_PORT || '6041';
const UI_TIMEOUT = 15_000;
const FONT_TIMEOUT = 10_000;

const NOTO_DIR = '/fonts/noto-color-emoji/';
const FLAGS_SUBSET = `${NOTO_DIR}noto-color-emoji.0.woff2`;
const APPLE = 'Apple Color Emoji';
const NOTO = 'Noto Color Emoji';
const FLAG_FACE = 'LF Flags';
/** The stacks the contract keeps right after 'LF Flags': html / --font-sans / .emoji-flag, and --font-mono (Tailwind's). */
const TEXT_STACK = 'Inter, system-ui, sans-serif';
const MONO_STACK = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";
const EU = '🇪🇺';
const A_FLAG = /\p{Regional_Indicator}{2}/u;
const ONLY_A_FLAG = /^\p{Regional_Indicator}{2}$/u;
/** A same-origin document this spec writes itself, fulfilled by a route: it never reaches the backend. */
const PROBE_PATH = '/__lf-flag-font-probe__.html';

type PlatformFont = {familyName: string; postScriptName?: string; isCustomFont: boolean; glyphCount: number};
type Host = {apple: boolean; probe: PlatformFont[]};
type Owned = {suffix: string; brokerIds: number[]};
type OwnRow = {id: number; currency: 'EUR' | 'USD'; flag: string};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type CommitResult = {operation: string; index?: number; ids?: number[]; status?: string};
type CommitBody = {committed: boolean; issues?: unknown[]; results?: CommitResult[]};

// ---------------------------------------------------------------------------
// Reading fonts through CDP
// ---------------------------------------------------------------------------

const describeFonts = (fonts: PlatformFont[]): string => fonts.map((f) => `${f.familyName} (${f.isCustomFont ? 'custom' : 'platform'}${f.postScriptName ? `, ${f.postScriptName}` : ''}) ×${f.glyphCount}`).join(' + ') || '(none)';
const familiesOf = (fonts: PlatformFont[]): string[] => [...new Set(fonts.map((f) => f.familyName))].sort();
const isEmojiFamily = (family: string): boolean => /emoji|segoe ui symbol/i.test(family);
const glyphsOf = (fonts: PlatformFont[]): number => fonts.reduce((sum, f) => sum + f.glyphCount, 0);
const emojiGlyphsOf = (fonts: PlatformFont[]): number => glyphsOf(fonts.filter((f) => isEmojiFamily(f.familyName)));
const distinct = (paths: string[]): string[] => [...new Set(paths)].sort();

let probeSeq = 0;

/** What CDP saw, kept in the report and printed by the list reporter. */
function record(label: string, fonts: PlatformFont[]): void {
    const line = `${label}: ${describeFonts(fonts)}`;
    base.info().annotations.push({type: 'cdp-fonts', description: line});
    console.log(`[cdp-fonts] ${line}`);
}

async function openCdp(page: Page): Promise<CDPSession> {
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('DOM.enable');
    await cdp.send('CSS.enable');
    return cdp;
}

/** Every face the laid-out document asked for has loaded, and the next frames re-laid the text out with it. */
async function settleFonts(page: Page): Promise<void> {
    await expect
        .poll(
            () =>
                page.evaluate(async () => {
                    // Lay out now, so any face the text needs has been requested before `ready` is read.
                    void document.body.getBoundingClientRect();
                    await document.fonts.ready;
                    await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
                    return document.fonts.status;
                }),
            {message: 'document.fonts settles to "loaded" after a forced layout', timeout: FONT_TIMEOUT},
        )
        .toBe('loaded');
}

/**
 * The fonts that drew the text of `target`, read once the fonts have settled. The retry only covers
 * the node being re-rendered between tagging and reading, never the answer.
 */
async function fontsOf(page: Page, cdp: CDPSession, target: Locator, label: string, prepare?: () => Promise<Locator>): Promise<PlatformFont[]> {
    let fonts: PlatformFont[] = [];
    await expect(async () => {
        const node = prepare ? await prepare() : target;
        await settleFonts(page);
        const token = `lf-cdp-${++probeSeq}`;
        await node.evaluate((el, t) => {
            el.setAttribute('data-lf-cdp', t);
            void el.getBoundingClientRect();
        }, token);
        const {root} = await cdp.send('DOM.getDocument', {depth: 0});
        const {nodeId} = await cdp.send('DOM.querySelector', {nodeId: root.nodeId, selector: `[data-lf-cdp="${token}"]`});
        if (!nodeId) throw new Error(`${label}: the node was re-rendered before CDP could read it`);
        ({fonts} = await cdp.send('CSS.getPlatformFontsForNode', {nodeId}));
        if (fonts.length === 0) throw new Error(`${label}: CDP reports no font, the text is not laid out yet`);
    }, `read the fonts of ${label}`).toPass({timeout: FONT_TIMEOUT * 2});
    record(label, fonts);
    return fonts;
}

/** Append probe markup to the current document, off screen but laid out; it inherits the page's stacks. */
async function inject(page: Page, html: string): Promise<Locator> {
    const id = `lf-font-probe-${++probeSeq}`;
    await page.evaluate(
        ({boxId, markup}) => {
            const box = document.createElement('div');
            box.id = boxId;
            box.setAttribute('aria-hidden', 'true');
            box.style.cssText = 'position:absolute;left:-10000px;top:0;white-space:nowrap;font-size:16px';
            box.innerHTML = markup;
            document.body.appendChild(box);
        },
        {boxId: id, markup: html},
    );
    return page.locator(`#${id}`);
}

/** Does this host have Apple Color Emoji? Asked of the fonts, not of the user agent. */
async function detectHost(page: Page, cdp: CDPSession): Promise<Host> {
    const box = await inject(page, `<span data-k="apple" style="font-family:'${APPLE}'">${EU}</span>`);
    const probe = await fontsOf(page, cdp, box.locator('[data-k="apple"]'), `host probe, font-family '${APPLE}'`);
    await box.evaluate((el) => el.remove());
    const apple = probe.some((f) => f.familyName === APPLE && !f.isCustomFont);
    base.info().annotations.push({type: 'host', description: apple ? 'Apple Color Emoji available: the Apple path' : 'no Apple Color Emoji: the Noto path'});
    return {apple, probe};
}

/** Every request this page makes under /fonts/noto-color-emoji/, armed before the first navigation. */
function recordNotoRequests(page: Page): string[] {
    const seen: string[] = [];
    page.context().on('request', (request) => {
        const {pathname} = new URL(request.url());
        if (pathname.startsWith(NOTO_DIR)) seen.push(pathname);
    });
    return seen;
}

/**
 * The status of every 'LF Flags' face the document declares. On an Apple host the flags look the same
 * through the face (`local()`) and through plain system fallback — CDP reports Apple Color Emoji as a
 * platform font both ways — so this is what proves the global rule is wired and was engaged.
 */
async function flagFaceStatuses(page: Page): Promise<string[]> {
    return page.evaluate((family) => [...document.fonts].filter((face) => face.family.replace(/["']/g, '') === family).map((face) => face.status), FLAG_FACE);
}

async function openProbePage(page: Page, style: string, body: string): Promise<void> {
    const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>LF flag font probe</title><style>${style}</style></head><body style="font-size:16px">${body}</body></html>`;
    await page.route(
        (url) => url.pathname === PROBE_PATH,
        (route) => route.fulfill({status: 200, contentType: 'text/html; charset=utf-8', body: html}),
    );
    await page.goto(PROBE_PATH);
}

// ---------------------------------------------------------------------------
// Owned data (API)
// ---------------------------------------------------------------------------

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** One broker and two DEPOSITs with flagged currencies; the broker id is recorded before anything can fail. */
async function createOwnRows(page: Page, owned: Owned): Promise<{brokerId: number; rows: OwnRow[]}> {
    const name = `FLAG ${owned.suffix}`;
    const created = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01'}]}), 'create the owned broker');
    const brokerId = created.results.find((item) => item.name === name && item.success)?.broker_id;
    if (typeof brokerId !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(created)}`);
    owned.brokerIds.push(brokerId);

    const currencies = [
        {currency: 'EUR', flag: '🇪🇺'},
        {currency: 'USD', flag: '🇺🇸'},
    ] as const;
    const body = await jsonFrom<CommitBody>(
        await page.request.post(COMMIT_PATH, {
            data: {creates: currencies.map((c) => ({broker_id: brokerId, type: 'DEPOSIT', date: '2024-01-02', cash: {code: c.currency, amount: '1234.5'}, description: `FLAG ${c.currency} ${owned.suffix}`}))},
        }),
        'commit the owned deposits',
    );
    expect(body.committed, `owned deposits rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const rows = currencies.map((c, index) => {
        const id = body.results?.find((result) => result.operation === 'create' && result.index === index && result.status === 'success')?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`Owned ${c.currency} deposit got no id: ${JSON.stringify(body.results)}`);
        return {id, currency: c.currency, flag: c.flag};
    });
    return {brokerId, rows};
}

/** Delete every row on the owned brokers, then the brokers: scoped to ids this test created. */
async function cleanupOwned(page: Page, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    const transactionIds: number[] = [];
    for (const brokerId of owned.brokerIds) {
        await attempt(`list the rows of broker ${brokerId}`, async () => {
            const rows = await jsonFrom<Array<{id: number}>>(await page.request.get(`${API}/transactions`, {params: {broker_id: brokerId}}), `list the rows of owned broker ${brokerId}`);
            transactionIds.push(...rows.map((row) => row.id));
        });
    }
    if (transactionIds.length > 0) {
        await attempt(`transactions ${transactionIds.join(', ')}`, async () => {
            const result = await jsonFrom<CommitBody>(await page.request.post(COMMIT_PATH, {data: {creates: [], updates: [], deletes: transactionIds}}), 'delete owned rows');
            expect(result.committed, JSON.stringify(result.issues ?? [])).toBe(true);
        });
    }
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete owned broker');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use, testInfo) => {
        const baseURL = testInfo.project.use.baseURL;
        if (!baseURL || new URL(baseURL).port !== TEST_PORT || !['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname)) {
            throw new Error(`Flag font checks write owned rows and may only use the shared local test backend on port ${TEST_PORT}`);
        }
        const owned: Owned = {suffix: `f${testInfo.workerIndex}-${uniqueSuffix()}`, brokerIds: []};
        try {
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

// ---------------------------------------------------------------------------
// The surfaces
// ---------------------------------------------------------------------------

function cashCell(page: Page, id: number): Locator {
    return page.getByTestId('transactions-page').getByTestId(`tx-cash-cell-${id}`);
}

/** Open the transactions page on the owned broker only; ends with every owned cash cell showing its flag. */
async function openOwnTransactions(page: Page, brokerId: number, rows: OwnRow[]): Promise<void> {
    await navigateTo(page, `/transactions?broker_id=${brokerId}`);
    const txPage = page.getByTestId('transactions-page');
    await expect(txPage).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(txPage, 20_000);
    for (const row of rows) await expect(cashCell(page, row.id).locator('.emoji-flag'), `the ${row.currency} cash cell shows its flag`).toHaveText(row.flag, {timeout: UI_TIMEOUT});
}

/** The text of `target`, cloned beside it (same classes, same inherited style) but set in `stack`: the reference for the text font. */
async function cloneInStack(page: Page, target: Locator, stack: string): Promise<Locator> {
    const id = `lf-font-ref-${++probeSeq}`;
    await target.evaluate(
        (el, {refId, fontStack}) => {
            const clone = el.cloneNode(true) as HTMLElement;
            clone.id = refId;
            clone.removeAttribute('data-lf-cdp');
            clone.style.fontFamily = fontStack;
            el.after(clone);
        },
        {refId: id, fontStack: stack},
    );
    return page.locator(`#${id}`);
}

// ---------------------------------------------------------------------------
// The checks
// ---------------------------------------------------------------------------

test.describe('flag font — which font draws a flag, read through CDP (K step 12b)', () => {
    test.skip(({browserName, isMobile}) => browserName !== 'chromium' || isMobile, 'CSS.getPlatformFontsForNode is a Chromium DevTools call: desktop Chromium only');
    test.describe.configure({timeout: 90_000});

    test('R1 transactions cash cell: the flag is drawn by Apple Color Emoji on an Apple host, by the Noto flags elsewhere', async ({page, owned}) => {
        await login(page, TEST_USER);
        const {brokerId, rows} = await createOwnRows(page, owned);
        await openOwnTransactions(page, brokerId, rows);
        const cdp = await openCdp(page);
        const host = await detectHost(page, cdp);
        const expected = host.apple ? APPLE : NOTO;

        for (const row of rows) {
            const fonts = await fontsOf(page, cdp, cashCell(page, row.id).locator('.emoji-flag'), `tx-cash-cell-${row.id} .emoji-flag, ${row.currency} ${row.flag}`);
            expect.soft(familiesOf(fonts), `${row.currency} ${row.flag} in its cash cell is drawn by ${expected} and nothing else. CDP: ${describeFonts(fonts)}`).toEqual([expected]);
            expect.soft(glyphsOf(fonts), `${row.currency} ${row.flag} is one flag glyph, not two letters. CDP: ${describeFonts(fonts)}`).toBe(1);
        }
        expect.soft(await flagFaceStatuses(page), `the app declares the '${FLAG_FACE}' face once, and the flags on screen engaged it`).toEqual(['loaded']);
    });

    test('R2 an Apple host fetches nothing from the Noto directory while transactions, dashboard and FX show flags', async ({page, owned}) => {
        const noto = recordNotoRequests(page);
        await login(page, TEST_USER);
        const {brokerId, rows} = await createOwnRows(page, owned);

        await openOwnTransactions(page, brokerId, rows);
        await settleFonts(page);

        await navigateTo(page, '/dashboard');
        const dashboard = page.getByTestId('dashboard-page');
        await waitForSettled(dashboard, 30_000);
        // Presence barrier: filtered to flags, any one proves the page drew them.
        await expect(dashboard.getByTestId('dashboard-cash-balances').locator('.emoji-flag').filter({hasText: A_FLAG}).first(), 'presence: the dashboard cash balances show a currency flag').toBeVisible({timeout: UI_TIMEOUT});
        await settleFonts(page);

        await navigateTo(page, '/fx');
        const fx = page.getByTestId('fx-page');
        await waitForSettled(fx, 30_000);
        await expect(fx.locator('[data-testid^="fx-card-"] .emoji-flag').filter({hasText: A_FLAG}).first(), 'presence: an FX card shows a currency flag').toBeVisible({timeout: UI_TIMEOUT});
        await settleFonts(page);

        const cdp = await openCdp(page);
        const host = await detectHost(page, cdp);
        const subsets = distinct(noto.filter((path) => path.endsWith('.woff2')));
        const stylesheets = distinct(noto.filter((path) => !path.endsWith('.woff2')));
        base.info().annotations.push({type: 'noto-requests', description: JSON.stringify(distinct(noto))});
        console.log(`[noto-requests] ${JSON.stringify(distinct(noto))}`);

        if (host.apple) {
            expect.soft(subsets, 'Apple host: no Noto subset is downloaded, the flags are Apple Color Emoji (local)').toEqual([]);
        } else {
            expect
                .soft(
                    subsets.filter((path) => path !== FLAGS_SUBSET),
                    'only the flags subset may be downloaded',
                )
                .toEqual([]);
        }
        expect.soft(stylesheets, 'no page requests the generated Noto stylesheet: the flags come from /lf-flags.css').toEqual([]);
    });

    test('R3 /offline.html: #lang-flag is drawn by Apple Color Emoji on an Apple host, by the Noto flags elsewhere', async ({page}) => {
        const noto = recordNotoRequests(page);
        // Offline for real: the page polls the health endpoint and reloads itself as soon as it answers.
        await page.route(
            (url) => url.pathname === `${API}/system/health`,
            (route) => route.abort(),
        );
        await page.goto('/offline.html');
        const flag = page.locator('#lang-flag');
        await expect(flag, 'the offline page shows its language flag').toHaveText(ONLY_A_FLAG, {timeout: UI_TIMEOUT});

        const cdp = await openCdp(page);
        const host = await detectHost(page, cdp);
        const expected = host.apple ? APPLE : NOTO;
        const fonts = await fontsOf(page, cdp, flag, `offline.html #lang-flag ${await flag.textContent()}`);

        expect.soft(familiesOf(fonts), `#lang-flag is drawn by ${expected} and nothing else. CDP: ${describeFonts(fonts)}`).toEqual([expected]);
        expect.soft(glyphsOf(fonts), `#lang-flag is one flag glyph. CDP: ${describeFonts(fonts)}`).toBe(1);
        expect.soft(await flagFaceStatuses(page), `offline.html declares the '${FLAG_FACE}' face once, and #lang-flag engaged it`).toEqual(['loaded']);
        if (host.apple) expect.soft(distinct(noto), 'Apple host: the offline page fetches nothing from the Noto directory').toEqual([]);
    });

    test('R4 digits, # and * inside .emoji-flag are drawn by the text font, never by an emoji font', async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/dashboard');
        await waitForSettled(page.getByTestId('dashboard-page'), 30_000);
        const cdp = await openCdp(page);
        const box = await inject(page, `<span class="emoji-flag" data-k="text">12#*</span> <span class="emoji-flag" data-k="mixed">${EU} 12#*</span> <span data-k="ref" style="font-family:${TEXT_STACK}">12#*</span>`);

        const ref = await fontsOf(page, cdp, box.locator('[data-k="ref"]'), `reference 12#* in ${TEXT_STACK}`);
        const text = await fontsOf(page, cdp, box.locator('[data-k="text"]'), '.emoji-flag 12#*');
        const mixed = await fontsOf(page, cdp, box.locator('[data-k="mixed"]'), `.emoji-flag ${EU} 12#*`);

        expect
            .soft(
                text.filter((f) => isEmojiFamily(f.familyName)),
                `no emoji font draws digits, # or * in .emoji-flag. CDP: ${describeFonts(text)}`,
            )
            .toEqual([]);
        expect.soft(familiesOf(text), `.emoji-flag draws 12#* with the text font (${describeFonts(ref)})`).toEqual(familiesOf(ref));
        expect.soft(emojiGlyphsOf(mixed), `in one run, an emoji font draws the flag and nothing else. CDP: ${describeFonts(mixed)}`).toBe(1);
    });

    test('C1 control: the LF Flags face without a local match draws the flag with the self-hosted Noto subset, and never digits, # or *', async ({page}) => {
        const noto = recordNotoRequests(page);
        const probe = "'LF Flags Probe'";
        await openProbePage(
            page,
            `@font-face {font-family: ${probe}; src: local('No Such Font LF'), url('${FLAGS_SUBSET}') format('woff2'); unicode-range: U+1F1E6-1F1FF;}`,
            [
                `<p><span data-k="sans-flag" style="font-family:${probe}, Inter">${EU}</span></p>`,
                `<p><span data-k="sans-text" style="font-family:${probe}, Inter">12#*</span></p>`,
                `<p><span data-k="sans-mixed" style="font-family:${probe}, Inter">${EU} 12#*</span></p>`,
                `<p><span data-k="sans-ref" style="font-family:Inter">12#*</span></p>`,
                `<div style="font-family:${probe}, ui-monospace, monospace">`,
                `<p><span data-k="mono-flag">${EU}</span></p><p><span data-k="mono-text">12#*</span></p><p><span data-k="mono-mixed">${EU} 12#*</span></p>`,
                `</div>`,
                `<p><span data-k="mono-ref" style="font-family:ui-monospace, monospace">12#*</span></p>`,
            ].join(''),
        );
        const loaded = await page.evaluate(async (flag) => {
            try {
                return (await document.fonts.load('16px "LF Flags Probe"', flag)).map((face) => face.status);
            } catch (error) {
                return [`load failed: ${String(error)}`];
            }
        }, EU);
        expect(loaded, 'the probe face loads for the flag from its url source').toEqual(['loaded']);
        const cdp = await openCdp(page);
        const at = (key: string) => page.locator(`[data-k="${key}"]`);

        for (const kind of ['sans', 'mono'] as const) {
            const flag = await fontsOf(page, cdp, at(`${kind}-flag`), `${kind} probe ${EU}`);
            const ref = await fontsOf(page, cdp, at(`${kind}-ref`), `${kind} reference 12#*`);
            const text = await fontsOf(page, cdp, at(`${kind}-text`), `${kind} probe 12#*`);
            const mixed = await fontsOf(page, cdp, at(`${kind}-mixed`), `${kind} probe ${EU} 12#*`);

            expect
                .soft(
                    flag.map((f) => ({family: f.familyName, custom: f.isCustomFont, glyphs: f.glyphCount})),
                    `${kind}: the flag comes from the url source, the self-hosted Noto flags. CDP: ${describeFonts(flag)}`,
                )
                .toEqual([{family: NOTO, custom: true, glyphs: 1}]);
            expect
                .soft(
                    text.filter((f) => isEmojiFamily(f.familyName)),
                    `${kind}: no emoji font draws 12#*. CDP: ${describeFonts(text)}`,
                )
                .toEqual([]);
            expect.soft(familiesOf(text), `${kind}: 12#* is drawn by the text font (${describeFonts(ref)})`).toEqual(familiesOf(ref));
            expect.soft(emojiGlyphsOf(mixed), `${kind}: in one run, the flag face draws the flag and nothing else. CDP: ${describeFonts(mixed)}`).toBe(1);
            expect.soft(familiesOf(mixed.filter((f) => !isEmojiFamily(f.familyName))), `${kind}: the rest of the run is the text font`).toEqual(familiesOf(ref));
        }
        expect.soft(distinct(noto), 'the url source fetched the flags subset and nothing else').toEqual([FLAGS_SUBSET]);
    });

    test('C2 control: digits beside a currency flag are drawn by the text font under the app stacks, never by an emoji font', async ({page, owned}) => {
        await login(page, TEST_USER);
        const {brokerId, rows} = await createOwnRows(page, owned);
        await openOwnTransactions(page, brokerId, rows);
        const cdp = await openCdp(page);

        // The amount the app renders beside the flag, against a clone of it set in the text stack.
        for (const row of rows) {
            // The original amount only: the reference clone below carries the same classes.
            const amount = cashCell(page, row.id).locator('.currency-amount:not([id^="lf-font-ref-"])');
            await expect(amount, `the ${row.currency} amount is rendered`).toHaveText(/\d/);
            const digits = await fontsOf(page, cdp, amount, `tx-cash-cell-${row.id} .currency-amount (${row.currency})`);
            let reference: Locator | null = null;
            const ref = await fontsOf(page, cdp, amount, `reference: the same amount in ${TEXT_STACK}`, async () => {
                await reference?.evaluate((el) => el.remove());
                reference = await cloneInStack(page, amount, TEXT_STACK);
                return reference;
            });
            expect
                .soft(
                    digits.filter((f) => isEmojiFamily(f.familyName)),
                    `${row.currency}: no emoji font draws the amount. CDP: ${describeFonts(digits)}`,
                )
                .toEqual([]);
            expect.soft(familiesOf(digits), `${row.currency}: the amount is drawn by the text font (${describeFonts(ref)})`).toEqual(familiesOf(ref));
        }

        // One run mixing a flag and digits under the app's own stacks: html (inherited) and Tailwind's font-mono.
        const box = await inject(
            page,
            [
                `<span data-k="html-text">12#*</span> <span data-k="html-mixed">${EU} 12#*</span> <span data-k="html-ref" style="font-family:${TEXT_STACK}">12#*</span>`,
                `<span class="font-mono" data-k="mono-text">12#*</span> <span class="font-mono" data-k="mono-mixed">${EU} 12#*</span> <span data-k="mono-ref" style="font-family:${MONO_STACK}">12#*</span>`,
            ].join(' '),
        );
        for (const kind of ['html', 'mono'] as const) {
            const ref = await fontsOf(page, cdp, box.locator(`[data-k="${kind}-ref"]`), `${kind} reference 12#*`);
            const text = await fontsOf(page, cdp, box.locator(`[data-k="${kind}-text"]`), `${kind} stack 12#*`);
            const mixed = await fontsOf(page, cdp, box.locator(`[data-k="${kind}-mixed"]`), `${kind} stack ${EU} 12#*`);

            expect
                .soft(
                    text.filter((f) => isEmojiFamily(f.familyName)),
                    `${kind}: no emoji font draws 12#*. CDP: ${describeFonts(text)}`,
                )
                .toEqual([]);
            expect.soft(familiesOf(text), `${kind}: 12#* is drawn by the text font (${describeFonts(ref)})`).toEqual(familiesOf(ref));
            expect.soft(emojiGlyphsOf(mixed), `${kind}: in one run, an emoji font draws the flag and nothing else. CDP: ${describeFonts(mixed)}`).toBe(1);
        }
    });

    test('C3 premise: the target face resolves on this host as the contract expects, and which local() names match', async ({page}) => {
        const noto = recordNotoRequests(page);
        const range = 'unicode-range: U+1F1E6-1F1FF;';
        await openProbePage(
            page,
            [
                `@font-face {font-family: 'LF Premise Target'; src: local('Apple Color Emoji'), local('AppleColorEmoji'), local('Noto Color Emoji'), local('NotoColorEmoji'), url('${FLAGS_SUBSET}') format('woff2'); ${range}}`,
                `@font-face {font-family: 'LF Premise Full Name'; src: local('Apple Color Emoji'); ${range}}`,
                `@font-face {font-family: 'LF Premise PostScript'; src: local('AppleColorEmoji'); ${range}}`,
            ].join('\n'),
            `<span data-k="target" style="font-family:'LF Premise Target', ${TEXT_STACK}">${EU}</span>`,
        );
        const statusOf = (families: string[], load: boolean) =>
            page.evaluate(
                async ({names, explicit}) => {
                    const out: Record<string, string> = {};
                    for (const face of document.fonts) {
                        const family = face.family.replace(/["']/g, '');
                        if (!names.includes(family)) continue;
                        if (explicit) await face.load().catch(() => undefined);
                        out[family] = face.status;
                    }
                    return out;
                },
                {names: families, explicit: load},
            );

        // The target, reached the way the app reaches it: only through a stack, only by rendering a flag.
        const cdp = await openCdp(page);
        const host = await detectHost(page, cdp);
        const target = await fontsOf(page, cdp, page.locator('[data-k="target"]'), `target face ${EU}, through the stack`);
        const rendered = await statusOf(['LF Premise Target'], false);
        // Then each Apple name on its own, loaded explicitly: which one does Chrome match on this host?
        const names = await statusOf(['LF Premise Full Name', 'LF Premise PostScript'], true);
        const statuses = {...rendered, ...names};
        base.info().annotations.push({type: 'local-names', description: JSON.stringify(statuses)});
        console.log(`[local-names] ${JSON.stringify(statuses)}`);

        expect(rendered, 'rendering a flag through the stack alone loads the target face').toEqual({'LF Premise Target': 'loaded'});
        if (host.apple) {
            expect.soft(familiesOf(target), `Apple host: the target face resolves to ${APPLE}. CDP: ${describeFonts(target)}`).toEqual([APPLE]);
            expect.soft(distinct(noto), 'Apple host: the target face downloads nothing').toEqual([]);
            expect.soft([names['LF Premise Full Name'], names['LF Premise PostScript']], "Apple host: local('Apple Color Emoji') or local('AppleColorEmoji') matches").toContain('loaded');
        } else {
            expect.soft(familiesOf(target), `the target face resolves to ${NOTO}. CDP: ${describeFonts(target)}`).toEqual([NOTO]);
        }
    });
});
