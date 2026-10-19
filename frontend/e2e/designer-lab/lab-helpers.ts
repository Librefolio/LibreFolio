/**
 * Designer Lab E2E helpers: the Lab in one page, the app in another page of the same browser context.
 *
 * The Lab is a debug-only page (`/designer-lab`) and the test server always serves a debug build, so it is there in
 * every E2E run. Its state lives in the context's localStorage and reaches the other pages of the same origin through
 * the `storage` event: two pages of one Playwright context are two tabs of one browser, which is exactly the flow the
 * Lab is built for. Nothing here touches the server: what the Lab writes dies with the test's context.
 *
 * The app tab publishes `window.__lfDesignerLab` (`active`, `picking`, `stats`, `chartColors`, `categoryColor`) from the
 * client every page of a debug build loads; every wait below reads that state, a computed style or a test id — never
 * the clock. `categoryColor` is the hook every chart category asks when it draws (contract C3 with DV): the specs never
 * call it, they read what the charts drew with it.
 *
 * Which code writes a colour is not the specs' business: workstreams move colours between rules, tokens and utilities.
 * The specs read it at run time — from the page, from the facts the picker reports, from the catalogue the Lab lists —
 * and hold the export to the verifier the Lab ships (`verify-export.mjs`), never to a file name written down here. A
 * colour class is followed the same way (`colourSourceOf`): a Tailwind palette class reads its palette variable, a
 * colour-role utility of workstream T reads the role its rule names in the page's CSSOM, and the values of both are
 * read from the page, never written down — T changes them. Where a notation would get in the way — a colour at an
 * opacity is `#rrggbbaa`, `oklch(… / a)` or a `color-mix()` in the editor, `rgba(…)` or `oklab(…)` in a computed
 * style — colours are compared as the page paints them (`paintedColours`).
 */

import {execFileSync} from 'node:child_process';
import {readFile, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {expect, type BrowserContext, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';

export const DESKTOP_ONLY = 'Desktop only: the Designer Lab is a desktop tool, the Lab and the app side by side in two tabs';

/**
 * The deadline of an effect one tab waits for from the other: the write crosses tabs as a `storage` event and, the
 * first time, the receiving tab loads the engine or picker chunk before it can act. Longer than the 3 s localhost
 * default for that reason; a deadline, never a delay — the assertion returns as soon as the effect is there.
 */
export const CROSS_TAB = {timeout: 10_000};

/** The keys the Lab keeps in localStorage: the state, the picker's messages, the browser that has seen the Lab. */
export const LAB_KEY_PREFIX = 'lf-designer-lab';

/** The picker's channel: the last `start`, `cancel` or `result` message between the Lab and the app tabs (`pick.ts`). */
export const PICK_KEY = `${LAB_KEY_PREFIX}/pick`;

/** The style and SVG nodes the engines inject while a state is active; an idle client injects none of them. */
export const LAB_NODE_IDS = ['lf-designer-lab-vars', 'lf-designer-lab-elements', 'lf-designer-lab-layer-order', 'lf-designer-lab-cvd-style', 'lf-designer-lab-cvd-svg'];

export const IDLE_STATS = {cssRules: 0, chartInstances: 0, varOverrides: 0, elementRules: 0, categoryOverrides: 0};

interface LabStats {
    cssRules: number;
    chartInstances: number;
    varOverrides: number;
    elementRules: number;
    /** The `category` changes the engine answers `categoryColor` with. */
    categoryOverrides: number;
}

interface LabHook {
    active: () => boolean;
    picking: () => boolean;
    stats: () => LabStats;
    chartColors: (selector: string) => Promise<string[]>;
    categoryColor: (kind: 'type' | 'sector', key: string, dark: boolean) => string | undefined;
}

type LabWindow = Window & {__lfDesignerLab?: LabHook};

/** The subset of the `lf-designer-lab/1` export the specs read. */
interface LabExportChange {
    id: string;
    layer: string;
    scope: string;
    target: string;
    from: string;
    to: string;
    property?: string;
    /** `css-var`: the editor's figures, and the Tailwind classes that read the variable — a role's utilities included. */
    impact?: {uses: number; files: number; classes?: Record<string, number>};
    /** `css-var`: where the sources define the variable. */
    definitions?: {file: string; line: number; selector: string | null; theme: string | null; value: string}[];
    /** `category`: the chart category the change colours, as its table writes it; the occurrences are its lines. */
    category?: {kind: string; key: string};
    occurrences: {file: string; line: number; raw?: string; selector?: string | null; why?: string}[];
    anchor?: {
        route: string;
        theme: string;
        testids: string[];
        css_path: string;
        selector: string;
        breadth: string;
        matches: number;
        property: string;
        computed: string;
        source: {kind: string; selector: string | null; var: string | null; class: string | null};
        candidates: {file: string; line: number; why: string; needle: string}[];
    };
}

interface LabExport {
    schema: string;
    catalog_hash: string;
    changes: LabExportChange[];
}

/** A declaration the app tab proved, or tried, for one colour of the picked element: the subset of `PickedDeclaration` the specs read. */
export interface PickedDeclarationFacts {
    origin: 'rule' | 'inline' | 'attribute';
    /** The rule's selector, null for an inline style or an attribute. */
    selector: string | null;
    /** The declared text, as written before any Lab change. */
    value: string;
    /** The cascade layer (`utilities`, dotted when nested), `''` for an anonymous one, null when unlayered. */
    layer: string | null;
    important: boolean;
    /** Proved to set the computed value: the winner, listed first. */
    wins: boolean;
}

/** What the app tab reports about the element picked (`PickedElement`): facts only, before the Lab resolves them. */
export interface PickedElementFacts {
    route: string;
    theme: 'light' | 'dark';
    testids: string[];
    /** `depth` 0: the colour is set on the element itself; n: on its n-th ancestor (inherited, or a background seen through). */
    properties: {property: string; computed: string; depth: number; declarations: PickedDeclarationFacts[]}[];
}

/**
 * The report of `verify-export.mjs --json` (`lf-designer-lab-verify/1`): the subset the specs read. `catalog_hash_match`
 * is left out on purpose: a developer editing `src` during a run changes the hash, not what the export lists.
 */
export interface VerifyReport {
    totals: {changes: number; ok: number; missing: number};
    changes: {id: string; missing: {file: string; line: number; raw?: string}[]; definitions: {file: string; line: number; status: string; value_now?: string}[]}[];
}

/** The verifier the Lab ships next to its scanner, resolved from this file: Playwright's working directory does not matter. */
const VERIFY_EXPORT_SCRIPT = fileURLToPath(new URL('../../scripts/designer-lab/verify-export.mjs', import.meta.url));

/** `frontend/`, resolved from this file: the paths of an export are relative to it (`src/lib/…`). Ends with a separator. */
const FRONTEND_DIR = fileURLToPath(new URL('../../', import.meta.url));

/** The theme toggle's end state, read back from `<html>`: act only when the app is not already there. */
export async function chooseTheme(page: Page, theme: 'light' | 'dark'): Promise<void> {
    const current = () => page.evaluate(() => (document.documentElement.classList.contains('dark') ? 'dark' : 'light'));
    // The toggle keeps the choice in this context's localStorage only, never in the user's settings.
    if ((await current()) !== theme) await page.getByTestId('theme-toggle').click();
    await expect.poll(current, {message: `the app did not switch to the ${theme} theme`}).toBe(theme);
}

/** The transactions page, loaded: its busy flag is down and the table is on screen. */
export async function openTransactions(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await expect(page.getByTestId('tx-table')).toBeVisible({timeout: 20_000});
}

/** The root of the transactions page: it sets the text colour its children inherit, through whichever utility or rule its code uses today, whatever the data. */
export function transactionsPageRoot(page: Page): Locator {
    return page.getByTestId('transactions-page');
}

/** The subtitle under the transactions page's title: a `<p>` coloured by a Tailwind text utility, whatever the data. */
export function transactionsSubtitle(page: Page): Locator {
    return page.getByTestId('transactions-page-overview-guide-target').locator('p');
}

/** The header cell of the date column of the transactions table: DataTable styles it, through whichever rule, token or utility its code uses today. */
export function dateColumnHeader(page: Page): Locator {
    return page.getByTestId('tx-table').getByTestId('dt-header-date');
}

/** The test id of the login card, the root of `LoginCard.svelte`, which a visitor who is not logged in gets at `/`. */
export const LOGIN_CARD = 'login-modal';

/**
 * `/` for a visitor who is not logged in (a fresh context has no session), loaded: the page asks GET /auth/me before
 * it shows the login card, so the first paint gets the budget auth.spec.ts gives it. Returns the card.
 */
export async function openSignIn(page: Page): Promise<Locator> {
    await page.goto('/');
    const card = page.getByTestId(LOGIN_CARD);
    await expect(card, 'a visitor who is not logged in gets the login card at /').toBeVisible({timeout: 20_000});
    return card;
}

/** The dashboard, loaded, with the growth chart drawn: `data-chart-ready` flips once ECharts has really drawn. */
export async function openDashboardGrowthChart(page: Page): Promise<Locator> {
    await navigateTo(page, '/dashboard');
    await waitForSettled(page.getByTestId('dashboard-page'), 30_000);
    const chart = page.getByTestId('growth-chart');
    await expect(chart.locator('[data-chart-ready]'), 'the growth chart must draw: TEST_USER has a portfolio history in populate_mock_data').toHaveAttribute('data-chart-ready', 'true', {timeout: 20_000});
    return chart;
}

/**
 * The pie of the dashboard's «Allocation» panel in its «now» view, as a selector `document.querySelector` takes: the
 * panel keeps its history chart mounted (hidden) beside it, so the pie is the drawn chart that is not the history.
 */
export const ALLOCATION_PIE = '[data-testid="allocation-panel"] [data-chart-ready]:not([data-testid="allocation-history-chart"])';

/** The dashboard, loaded: its busy flag is down. `/dashboard` opens on its overview, the tab of the «Allocation» panel. */
export async function openDashboard(page: Page): Promise<void> {
    await navigateTo(page, '/dashboard');
    await waitForSettled(page.getByTestId('dashboard-page'), 30_000);
}

/**
 * Show the «now» view of the «Allocation» panel on `tab` and return its pie once drawn. The view and the tab persist per
 * user in this context's storage: each is clicked only when it is not already selected, and its end state asserted.
 * Each tab mounts a pie of its own, so the pie that reports itself drawn after the switch is the tab's.
 */
export async function showAllocationNow(page: Page, tab: 'type' | 'sector'): Promise<Locator> {
    const panel = page.getByTestId('allocation-panel');
    await expect(panel, 'the dashboard overview shows the «Allocation» panel').toBeVisible({timeout: 20_000});
    for (const button of [panel.getByTestId('allocation-view-now'), panel.getByTestId(`allocation-tab-${tab}`)]) {
        if ((await button.getAttribute('aria-pressed')) !== 'true') await button.click();
        await expect(button).toHaveAttribute('aria-pressed', 'true');
    }
    const pie = page.locator(ALLOCATION_PIE);
    await expect(pie, `the ${tab} pie must draw: TEST_USER holds positions in populate_mock_data`).toHaveAttribute('data-chart-ready', 'true', {timeout: 20_000});
    return pie;
}

/**
 * Open the Lab in a new page of `context`. Its root renders only in a debug build: a release build answers the URL
 * with the SPA shell, and the route's `load()` throws its 404 instead.
 */
export async function openLab(context: BrowserContext): Promise<Page> {
    const lab = await context.newPage();
    // «Reset all» asks for a confirmation: the designer says yes.
    lab.on('dialog', (dialog) => void dialog.accept());
    await lab.goto('/designer-lab');
    const root = lab.getByTestId('designer-lab');
    await expect(root, 'the test server must serve a debug build (dev.py server --test builds one): /designer-lab rendered no Lab').toBeVisible({timeout: 30_000});
    await expect(root).toHaveAttribute('data-catalog-hash', /^sha256:[0-9a-f]{64}$/);
    // The Lab marks this browser as one where it has been opened when it mounts: from then on the app tabs install
    // the Alt+Shift+D shortcut.
    await expect.poll(() => lab.evaluate(() => localStorage.getItem('lf-designer-lab/seen'))).not.toBeNull();
    return lab;
}

/** Edit the light theme: the app tabs are put in the light theme, and a one-theme change says which theme it is for. */
export async function editLightTheme(lab: Page): Promise<void> {
    await lab.getByTestId('lab-scope').selectOption('light');
    await expect(lab.getByTestId('lab-scope')).toHaveValue('light');
}

/** The number of changes the Lab holds, as its root publishes it. */
export async function expectChanges(lab: Page, count: number): Promise<void> {
    await expect(lab.getByTestId('designer-lab')).toHaveAttribute('data-changes', String(count));
}

/** The tabs of the Lab that list catalogue items the editor opens on: `categories` lists the chart categories, by key. */
export type ItemTab = 'palette' | 'vars' | 'sheets' | 'charts' | 'categories';

/**
 * Open the editor on one catalogue item: open the tab, narrow the list with the search, click the item. Returns the
 * editor once it shows that item — its layer and its target.
 */
export async function openEditor(lab: Page, opts: {tab: ItemTab; search: string; item: string; layer: string; target: string}): Promise<Locator> {
    await lab.getByTestId(`lab-tab-${opts.tab}`).click();
    await lab.getByTestId('lab-search').fill(opts.search);
    await expect(lab.getByTestId('lab-search')).toHaveValue(opts.search);
    const item = lab.getByTestId(opts.item);
    await expect(item, `the Lab must list ${opts.item}: the catalogue is built from the colours of the app's sources`).toBeVisible();
    await item.click();
    const editor = lab.getByTestId('lab-editor');
    await expect(editor).toHaveAttribute('data-layer', opts.layer);
    await expect(editor).toHaveAttribute('data-target', opts.target);
    return editor;
}

/**
 * Change one catalogue item to `to` through the editor: open the tab, narrow the list with the search, open the item,
 * type the new colour and apply. Returns once the Lab holds one more change.
 */
export async function applyChange(lab: Page, opts: {tab: ItemTab; search: string; item: string; layer: string; target: string; to: string}): Promise<void> {
    const before = Number(await lab.getByTestId('designer-lab').getAttribute('data-changes'));
    await openEditor(lab, opts);
    await lab.getByTestId('lab-editor-to').fill(opts.to);
    await expect(lab.getByTestId('lab-editor-to')).toHaveValue(opts.to);
    await lab.getByTestId('lab-editor-apply').click();
    await expectChanges(lab, before + 1);
}

/**
 * Move a slider of the editor to `value`, as a drag that ends there. Playwright's `fill()` refuses a range input, and a
 * real drag lands wherever the thumb's pixels put it; so the value is set in the page and the events a drag fires are
 * dispatched, `input` then `change`, bubbling — Svelte 5 listens for `input` at the root, by delegation. Returns once
 * the slider shows the value: a value off its step or its range would be snapped by the browser, and fails here.
 */
export async function setSlider(slider: Locator, value: number): Promise<void> {
    await expect(slider).toHaveAttribute('type', 'range');
    await slider.evaluate((el, next) => {
        if (!(el instanceof HTMLInputElement)) throw new Error(`a slider is an <input type="range">, not a <${el.tagName.toLowerCase()}>`);
        el.value = String(next);
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
    }, value);
    await expect(slider).toHaveValue(String(value));
}

/**
 * The colour keys a value tab of the Lab lists, all of them (the search cleared), most used first. Which values the
 * sources write is the catalogue's business, not the specs': they pick from this list at run time.
 */
export async function listedKeys(lab: Page, tab: 'sheets' | 'charts'): Promise<string[]> {
    const prefix = `lab-item-value-${tab === 'sheets' ? 'css-literal' : 'chart-color'}-`;
    await lab.getByTestId(`lab-tab-${tab}`).click();
    await lab.getByTestId('lab-search').fill('');
    await expect(lab.getByTestId('lab-search')).toHaveValue('');
    const items = lab.locator(`[data-testid^="${prefix}"]`);
    await expect(items, `the ${tab} tab lists the catalogue's colours`).not.toHaveCount(0);
    return items.evaluateAll((nodes, start) => nodes.map((node) => (node.getAttribute('data-testid') ?? '').slice(start.length)), prefix);
}

/** A chart category as the Lab's «Categories» tab lists it: its target, and the value its table writes in each theme. */
export interface CategoryValue {
    /** `type:ETF`, `sector:Health Care`, `bucket:Liquidity`: the target of a `category` change. */
    target: string;
    kind: string;
    /** As the table writes it (`ETF`, `Health Care`). */
    key: string;
    /** The values as the table writes them (`#1D5BD8`), null where it writes none. */
    light: string | null;
    dark: string | null;
}

/**
 * Every chart category the «Categories» tab lists (the search cleared), with its values read from the row's text, where
 * the Lab shows them as `<light> · <dark>` (`—` for a missing one). Which values the tables hold is DV's business and
 * T's, never the specs': they pick from this list at run time.
 */
export async function categoryValues(lab: Page): Promise<CategoryValue[]> {
    const tab = lab.getByTestId('lab-tab-categories');
    await tab.click();
    await expect(tab).toHaveAttribute('aria-current', 'true');
    const search = lab.getByTestId('lab-search');
    await search.fill('');
    await expect(search).toHaveValue('');
    const prefix = 'lab-item-category-';
    const rows = lab.locator(`[data-testid^="${prefix}"]`);
    await expect(rows, 'the «Categories» tab lists the chart categories of the catalogue: the tables of lib/theme/chartCategories.ts').not.toHaveCount(0);
    const read = await rows.evaluateAll((nodes, start) => nodes.map((node) => ({target: (node.getAttribute('data-testid') ?? '').slice(start.length), text: node.textContent ?? ''})), prefix);
    return read.map(({target, text}) => {
        const values = /(#[0-9a-f]{3,8}|—)\s*·\s*(#[0-9a-f]{3,8}|—)\s*$/i.exec(text.trim());
        if (!values) throw new Error(`the row of ${target} must end with its light and dark values, «#… · #…»: it reads «${text.trim()}»`);
        const colon = target.indexOf(':');
        return {target, kind: target.slice(0, colon), key: target.slice(colon + 1), light: values[1] === '—' ? null : values[1], dark: values[2] === '—' ? null : values[2]};
    });
}

/** The client of a debug build has started in this page: `start()` publishes its hook. */
export async function waitForLabClient(page: Page): Promise<void> {
    await expect
        .poll(() => page.evaluate(() => typeof (window as LabWindow).__lfDesignerLab === 'object'), {
            message: 'the Lab client must start in every page: the test server serves a debug build (dev.py server --test builds one)',
            timeout: 15_000,
        })
        .toBe(true);
}

export async function labActive(page: Page): Promise<boolean> {
    return page.evaluate(() => (window as LabWindow).__lfDesignerLab?.active() ?? false);
}

export async function labPicking(page: Page): Promise<boolean> {
    return page.evaluate(() => (window as LabWindow).__lfDesignerLab?.picking() ?? false);
}

export async function labStats(page: Page): Promise<LabStats | null> {
    return page.evaluate(() => (window as LabWindow).__lfDesignerLab?.stats() ?? null);
}

/**
 * The distinct colours of the ECharts option inside the first element matching `selector`, by value: each one as the
 * canvas serialises it (`#rrggbb` when opaque, `rgba(…)` otherwise), so `#fff` and `#ffffff` are one colour. A string
 * the canvas refuses stays as written. Sorted.
 */
export async function chartColourValues(page: Page, selector: string): Promise<string[]> {
    return page.evaluate(async (sel) => {
        const colours = (await (window as LabWindow).__lfDesignerLab?.chartColors(sel)) ?? [];
        const probe = document.createElement('canvas').getContext('2d');
        const valueOf = (colour: string): string => {
            if (!probe) return colour;
            // Two different starting values: a colour the canvas refuses leaves each in place, a valid one replaces both.
            probe.fillStyle = '#000000';
            probe.fillStyle = colour;
            const first = String(probe.fillStyle);
            probe.fillStyle = '#ffffff';
            probe.fillStyle = colour;
            return first === String(probe.fillStyle) ? first : colour;
        };
        return [...new Set(colours.map(valueOf))].sort();
    }, selector);
}

/**
 * The event that tells the charts their colours changed while the theme did not (contract C4 with DV, `onChartColorsChange`
 * of `lib/theme/themeMode.ts`): a chart that hears it rebuilds its whole option, its roles and categories read again.
 */
export const CHART_COLORS_EVENT = 'lf:chart-colors-change';

/** The computed value of a CSS property of the element `locator` resolves to. */
export async function computedStyle(locator: Locator, property = 'color'): Promise<string> {
    return locator.evaluate((el, name) => getComputedStyle(el).getPropertyValue(name).trim(), property);
}

/**
 * What `variable` resolves to as a colour in each theme, as the app page computes it: on a probe inside a `.light` and
 * a `.dark` subtree — the subtrees `tokens.css` defines the colour roles on too — appended, read and removed within one
 * task, so the page never paints it. A variable no theme block redefines reads the same in both.
 */
export async function themeValuesOf(page: Page, variable: string): Promise<{light: string; dark: string}> {
    return page.evaluate((name) => {
        const read = (theme: 'light' | 'dark'): string => {
            const host = document.createElement('div');
            host.className = theme;
            const probe = host.appendChild(document.createElement('div'));
            probe.style.setProperty('color', `var(${name})`);
            document.body.appendChild(host);
            try {
                return getComputedStyle(probe).color;
            } finally {
                host.remove();
            }
        };
        return {light: read('light'), dark: read('dark')};
    }, variable);
}

/** A colour a test applies: as the editor takes it, and as `getComputedStyle` gives it back. */
export interface NewColour {
    hex: string;
    rgb: string;
}

/**
 * The first of `colours` that `variable` has in neither theme (`themeValuesOf`) and that none of `alsoAvoid` is: a
 * change to it then shows whichever theme is on screen. The values are read, never written down: workstream T changes
 * them. Fails, naming the values, when every candidate is taken.
 */
export async function newColourFor(page: Page, variable: string, colours: NewColour[], alsoAvoid: string[] = []): Promise<NewColour> {
    const themes = await themeValuesOf(page, variable);
    const taken = new Set([themes.light, themes.dark, ...alsoAvoid]);
    const colour = colours.find((c) => !taken.has(c.rgb));
    if (!colour) throw new Error(`no new colour left for ${variable}: it is ${themes.light} in light and ${themes.dark} in dark, also avoided ${alsoAvoid.join(', ') || 'nothing'}; candidates ${colours.map((c) => c.rgb).join(', ')}`);
    return colour;
}

/** `rgb(100, 116, 139)` → `#64748b`: the catalogue key of an opaque sRGB colour, or null for any other form. */
export function opaqueHexOf(color: string): string | null {
    const m = /^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)$/.exec(color.trim());
    if (!m || (m[4] !== undefined && Number(m[4]) !== 1)) return null;
    return `#${[m[1], m[2], m[3]].map((v) => Number(v).toString(16).padStart(2, '0')).join('')}`;
}

/** `#RRGGBB` → `#rrggbb`: the catalogue key of an opaque colour as the canvas writes it, or null for any other form. */
export function hexKeyOf(color: string): string | null {
    return /^#[0-9a-f]{6}$/i.test(color.trim()) ? color.trim().toLowerCase() : null;
}

/** `rgba(100, 116, 139, 0.3)` → `#64748b`: the key of an sRGB colour as the canvas writes it, its alpha set aside; null for any other form. */
function rgbKeyOf(color: string): string | null {
    const m = /^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)$/.exec(color.trim());
    return m ? `#${[m[1], m[2], m[3]].map((v) => Number(v).toString(16).padStart(2, '0')).join('')}` : null;
}

/**
 * The catalogue key of each colour text with its alpha set aside (`#64748B`, `#64748b80`, `rgb(100 116 139 / 30%)` →
 * `#64748b`), as the browser of `page` parses it — the CSS parser of reference, not the Lab's: a canvas serialises a
 * colour it accepts as `#rrggbb` or `rgba(…)`. Null for a text the canvas refuses, or a colour it keeps outside sRGB.
 */
export async function opaqueKeysOf(page: Page, colours: string[]): Promise<(string | null)[]> {
    const serialised = await page.evaluate((list) => {
        const probe = document.createElement('canvas').getContext('2d');
        return list.map((colour) => {
            if (!probe) return null;
            // Two different starting values: a colour the canvas refuses leaves each in place, a valid one replaces both.
            probe.fillStyle = '#000000';
            probe.fillStyle = colour;
            const first = String(probe.fillStyle);
            probe.fillStyle = '#ffffff';
            probe.fillStyle = colour;
            return first === String(probe.fillStyle) ? first : null;
        });
    }, colours);
    return serialised.map((value) => (value === null ? null : (hexKeyOf(value) ?? rgbKeyOf(value))));
}

/** A colour as the page paints it: sRGB channels 0–255, alpha 0–1. */
export interface Painted {
    r: number;
    g: number;
    b: number;
    alpha: number;
}

/**
 * Each CSS colour value as the app page paints it, whatever its notation: set on a probe element — so a `var()` resolves
 * against the page's variables and a `color-mix()` is computed — then its computed colour painted on one pixel of a
 * canvas and read back as sRGB bytes. `#fbf8f180`, `rgba(251, 248, 241, 0.5)` and the `oklab(… / 0.5)` a browser
 * computes for a mix then compare as the colours they are, which their texts do not: the editor writes `#rrggbbaa` or
 * `oklch(… / a)` for a colour at an opacity, and a computed style serialises each form its own way. `css` is the
 * probe's computed colour, for messages. Null for a value CSS refuses, or a computed colour the canvas refuses. Each
 * probe is a fresh element without transitions, appended and removed within one task: the page never paints it.
 */
export async function paintedColours(page: Page, values: string[]): Promise<((Painted & {css: string}) | null)[]> {
    return page.evaluate((list) => {
        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;
        const ctx = canvas.getContext('2d', {willReadFrequently: true});
        return list.map((value) => {
            if (!ctx) return null;
            const probe = document.createElement('div');
            probe.style.setProperty('transition', 'none');
            probe.style.setProperty('background-color', value);
            // A text CSS refuses leaves the declaration empty.
            if (!probe.style.getPropertyValue('background-color')) return null;
            document.body.appendChild(probe);
            const css = getComputedStyle(probe).backgroundColor;
            probe.remove();
            // Two different starting values: a colour the canvas refuses leaves each in place, a valid one replaces both.
            ctx.fillStyle = '#000000';
            ctx.fillStyle = css;
            const first = String(ctx.fillStyle);
            ctx.fillStyle = '#ffffff';
            ctx.fillStyle = css;
            if (first !== String(ctx.fillStyle)) return null;
            ctx.clearRect(0, 0, 1, 1);
            ctx.fillRect(0, 0, 1, 1);
            const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
            return {r, g, b, alpha: a / 255, css};
        });
    }, values);
}

/**
 * Whether two painted colours are one colour. The alpha within 0.01: an 8-bit alpha moves in steps of 0.004. The
 * channels within what painting costs: a canvas stores a pixel premultiplied in 8 bits, so the channels of a translucent
 * pixel come back up to 255 / (2 × its alpha byte) off — 1 at alpha 0.5, 2 at 0.25, 5 at 0.12 — plus 2 for a colour the
 * browser computed in another space (a mix, in `oklab`) and the rounding of its serialisation. Two fully transparent
 * pixels are one colour.
 */
export function sameColour(a: Painted, b: Painted): boolean {
    if (Math.abs(a.alpha - b.alpha) > 0.01) return false;
    const alphaByte = Math.round(Math.min(a.alpha, b.alpha) * 255);
    if (alphaByte === 0) return true;
    const slack = Math.ceil(255 / (2 * alphaByte)) + 2;
    return [a.r - b.r, a.g - b.g, a.b - b.b].every((d) => Math.abs(d) <= slack);
}

/** A painted colour in a message: `rgba(r, g, b, a)`, the alpha to three decimals. */
export function describeColour(colour: Painted): string {
    return `rgba(${colour.r}, ${colour.g}, ${colour.b}, ${Math.round(colour.alpha * 1000) / 1000})`;
}

/**
 * Wait until the CSS colour `read` returns paints as `expected` (`sameColour`), polled to the deadline — across tabs by
 * default, since the Lab's write reaches an app tab as a `storage` event. Fails with the last value read, as computed
 * and as painted.
 */
export async function expectPainted(page: Page, read: () => Promise<string>, expected: Painted, message: string, options: {timeout: number} = CROSS_TAB): Promise<void> {
    const wanted = describeColour(expected);
    await expect
        .poll(
            async () => {
                const value = await read();
                const [painted] = await paintedColours(page, [value]);
                if (!painted) return `${value}, a value the page does not paint`;
                return sameColour(painted, expected) ? wanted : `${value}, computed ${painted.css}, painted ${describeColour(painted)}`;
            },
            {...options, message},
        )
        .toBe(wanted);
}

/** A colour at an opacity in the form the role tokens write it, `color-mix(in <space>, <base> <p>%, transparent)`. */
export interface TransparentMix {
    /** The interpolation space as the Lab writes it back: lower case, single spaces (`oklab`, `oklch longer hue`). */
    space: string;
    /** The base as written: a colour, or `var(--x)`. */
    base: string;
    /** The share of the base, 0–100: the opacity the mix gives it. */
    percent: number;
}

/**
 * The parts of a value written in the role tokens' form for a colour at an opacity — `color-mix(in <space>, <base>
 * <p>%, transparent)`, the base first and its share after it — read here independently of the Lab's own parser
 * (`colorValue.ts`), so that a spec checks the Lab instead of repeating it. Null for any other text: the other orders and
 * notations of a mix with `transparent` included, since a spec that needs a mix states which form it reads.
 */
export function transparentMixOf(text: string): TransparentMix | null {
    const m = /^color-mix\(\s*in\s+([a-z][a-z0-9-]*(?:\s+(?:shorter|longer|increasing|decreasing)\s+hue)?)\s*,\s*(\S[\s\S]*?)\s+(\d+(?:\.\d+)?)%\s*,\s*transparent\s*\)$/i.exec(text.trim());
    if (!m || /^transparent$/i.test(m[2].trim())) return null;
    return {space: m[1].toLowerCase().replace(/\s+/g, ' '), base: m[2].trim(), percent: Number(m[3])};
}

/**
 * The computed value of a custom property on `<html>` of `page`, trimmed. A browser substitutes the `var()`s a custom
 * property reads when it computes it: a mix over `var(--x)` comes back with the value of `--x` in its place.
 */
export async function rootValueOf(page: Page, variable: string): Promise<string> {
    return page.evaluate((name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim(), variable);
}

/** The colour property a utility prefix sets: the one its rule declares. */
const PREFIX_PROPERTY = {text: 'color', bg: 'background-color', border: 'border-color'} as const;

/** A Tailwind utility prefix that sets a colour: `text-…`, `bg-…`, `border-…`. */
export type ColourPrefix = keyof typeof PREFIX_PROPERTY;

/**
 * What sets one colour of an element, as the Lab's palette edits it: a Tailwind palette class, or a colour-role utility
 * of workstream T (`--color-lf-card: var(--lf-surface-card)` in `@theme inline` gives `bg-lf-card`).
 */
export interface ColourSource {
    /** The class on the element: `text-gray-500`, `bg-lf-card`. */
    className: string;
    /**
     * The variable the palette tab lists the class under, so its chip is `lab-item-var-<chipVar>`: the palette variable
     * (`--color-gray-500`), or the role's `@theme inline` alias (`--color-lf-card`), which no stylesheet defines at runtime.
     */
    chipVar: string;
    /** The variable the chip edits, the one the class reads at runtime: the palette variable itself, or the role (`--lf-surface-card`). */
    target: string;
    /** A colour role: the chip keeps its alias's test id and edits `target`. */
    role: boolean;
    /** A role utility's rule, as the app page's CSSOM serialises its selector (`.bg-lf-card`); null for a palette class, whose CSSOM is not read. */
    selector: string | null;
}

/**
 * The colour source of an element for one utility prefix (`text`, `bg`, `border`), read from its classes — colour classes
 * are the Lab's subject, so here an element is described by them on purpose:
 *
 * - a palette class (`text-gray-500`) reads its palette variable: chip and target are `--color-gray-500`;
 * - a role utility (`text-lf-muted`) is listed under its alias (`--color-lf-muted`) and reads the role its rule names:
 *   read at run time in the app page's CSSOM — the rule whose selector is the utility, in whatever layer, `@media` or
 *   `@supports` holds it, declaring `var(--lf-…)` — never written down, since workstream T moves the roles.
 *
 * Fails with a message naming the missing assumption: no colour class for the prefix, a palette class and a role
 * utility together (an element migrates whole), two role utilities, no rule for the utility, or a rule that reads no role.
 */
export async function colourSourceOf(locator: Locator, prefix: ColourPrefix): Promise<ColourSource> {
    const classes = ((await locator.getAttribute('class')) ?? '').split(/\s+/).filter(Boolean);
    const property = PREFIX_PROPERTY[prefix];
    const palette = classes.find((c) => new RegExp(`^${prefix}-(?!lf-)[a-z]+-\\d{2,3}$`).test(c));
    const roles = classes.filter((c) => new RegExp(`^${prefix}-lf-[a-z0-9]+(?:-[a-z0-9]+)*$`).test(c));
    const listed = classes.join(' ');
    if (palette && roles.length) throw new Error(`the element mixes a palette class (${palette}) and a role utility (${roles.join(', ')}) for its ${property}: its classes do not say which one sets it (classes: ${listed})`);
    if (palette) {
        const variable = `--color-${palette.slice(prefix.length + 1)}`;
        return {className: palette, chipVar: variable, target: variable, role: false, selector: null};
    }
    if (roles.length > 1) throw new Error(`the element carries several role utilities for its ${property} (${roles.join(', ')}): its classes do not say which one sets it`);
    const [className] = roles;
    if (!className) throw new Error(`the element carries no ${prefix} colour class: neither a Tailwind palette class (${prefix}-<family>-<shade>) nor a colour-role utility (${prefix}-lf-<name>) (classes: ${listed})`);

    const found = await locator.evaluate(
        (el, {cls, prop}) => {
            // The selector as Tailwind writes the class (`:` and `/` escaped) and the CSSOM serialises it.
            const wanted = `.${CSS.escape(cls)}`;
            const hits: {selector: string; value: string; layer: string | null}[] = [];
            let rules = 0;
            let unreadable = 0;
            const walk = (list: CSSRuleList, layer: string | null, nested: boolean): void => {
                for (const rule of Array.from(list)) {
                    rules++;
                    if (rule instanceof CSSStyleRule) {
                        // A rule nested in a style rule stands for a longer selector than its own text.
                        if (!nested && rule.selectorText === wanted) hits.push({selector: rule.selectorText, value: rule.style.getPropertyValue(prop).trim(), layer});
                        if (rule.cssRules?.length) walk(rule.cssRules, layer, true);
                    } else if (rule instanceof CSSMediaRule) {
                        if (window.matchMedia(rule.media.mediaText).matches) walk(rule.cssRules, layer, nested);
                    } else if (rule instanceof CSSSupportsRule) {
                        if (CSS.supports(rule.conditionText)) walk(rule.cssRules, layer, nested);
                    } else if (rule instanceof CSSLayerBlockRule) {
                        walk(rule.cssRules, layer ? `${layer}.${rule.name}` : rule.name, nested);
                    } else if (rule instanceof CSSGroupingRule && rule.constructor.name !== 'CSSStartingStyleRule') {
                        walk(rule.cssRules, layer, nested);
                    }
                }
            };
            for (const sheet of Array.from(el.ownerDocument.styleSheets)) {
                let list: CSSRuleList;
                try {
                    list = sheet.cssRules;
                } catch {
                    unreadable++;
                    continue;
                }
                walk(list, null, false);
            }
            return {wanted, hits, rules, unreadable};
        },
        {cls: className, prop: property},
    );
    const declaring = found.hits.filter((h) => h.value !== '');
    const described = declaring.map((h) => `${property}: ${h.value}${h.layer === null ? '' : ` in @layer ${h.layer}`}`).join('; ');
    if (!declaring.length)
        throw new Error(
            `${className} is a colour-role utility, but no rule ${found.wanted} of the app page declares ${property} (${found.hits.length} rules with that selector among ${found.rules} walked, ${found.unreadable} stylesheets unreadable): Tailwind did not generate it, or wrote it under another selector`,
        );
    const named = [...new Set(declaring.map((h) => /^var\(\s*(--lf-[\w-]+)\s*\)$/.exec(h.value)?.[1] ?? null))];
    const [target] = named;
    if (named.length !== 1 || !target) throw new Error(`the rule ${found.wanted} must read one colour role, var(--lf-…), for ${property}; it declares ${described}: the @theme inline alias of ${className} no longer stands for a role`);
    return {className, chipVar: `--color-${className.slice(prefix.length + 1)}`, target, role: true, selector: found.wanted};
}

/**
 * A point of `target` where the element itself is on top — not one of its children, not an overlay — in viewport
 * coordinates, after scrolling it into view. Taken before a pick starts: the veil then covers the whole page.
 */
export async function pointOnItself(target: Locator): Promise<{x: number; y: number}> {
    await target.scrollIntoViewIfNeeded();
    const point = await target.evaluate((el) => {
        const r = el.getBoundingClientRect();
        const onTop = (x: number, y: number) => x >= 0 && y >= 0 && x < window.innerWidth && y < window.innerHeight && document.elementFromPoint(x, y) === el;
        const cx = r.left + r.width / 2;
        const cy = r.top + r.height / 2;
        if (onTop(cx, cy)) return {x: cx, y: cy};
        for (let y = Math.ceil(r.top) + 1; y < r.bottom - 1; y += 2) {
            for (let x = Math.ceil(r.left) + 1; x < r.right - 1; x += 2) if (onTop(x, y)) return {x, y};
        }
        return null;
    });
    if (!point) throw new Error('no point of the element is the element itself: its children or an overlay cover all of it');
    return point;
}

/** The veil the picker lays over an app tab while it waits for a click. */
export function pickVeil(page: Page): Locator {
    return page.getByTestId('lf-lab-pick-veil');
}

/** One colour property of the picked element, as the Lab's «Element» tab lists it. */
export function pickedProperty(lab: Page, property: string): Locator {
    return lab.locator(`[data-testid="lab-picked-property"][data-property="${property}"]`);
}

/**
 * The facts the app tab reported for the element picked last: the `result` message it wrote in this context's
 * localStorage (`lf-designer-lab/pick`), as `picker/describe.ts` produced them — before the Lab's `pickView.ts` resolves
 * anything against its catalogue. A state, not an edge: the message stays there until the next pick message.
 */
export async function pickedFacts(page: Page): Promise<PickedElementFacts> {
    const raw = await page.evaluate((key) => localStorage.getItem(key), PICK_KEY);
    const message = raw ? (JSON.parse(raw) as {op?: string; element?: PickedElementFacts}) : null;
    if (message?.op !== 'result' || !message.element) throw new Error(`the app tab must leave its pick result in ${PICK_KEY}, found ${raw === null ? 'nothing' : raw.slice(0, 200)}`);
    return message.element;
}

/** Click «JSON» and read the file the Lab downloads. */
export async function downloadExport(lab: Page): Promise<{text: string; doc: LabExport}> {
    const [download] = await Promise.all([lab.waitForEvent('download'), lab.getByTestId('lab-export-json').click()]);
    expect(download.suggestedFilename()).toBe('designer-lab-changes.json');
    const text = await readFile(await download.path(), 'utf8');
    return {text, doc: JSON.parse(text) as LabExport};
}

/**
 * Check an export against the code as it is now, with the verifier the Lab ships: `text` is written to `file` (a path
 * the test owns, e.g. `testInfo.outputPath(…)`) and `verify-export.mjs <file> --json` runs under the Node that runs the
 * tests. It rescans the catalogue itself, about two seconds, synchronously: the `timeout` is the only deadline that can
 * stop it. Exit 0: nothing missing; 1: an occurrence missing, or a specialisation lost; 2: bad input. The status, the
 * parsed report (null when it printed none) and stderr come back whatever the exit.
 */
export async function verifyExport(text: string, file: string): Promise<{status: number | null; report: VerifyReport | null; stderr: string}> {
    await writeFile(file, text, 'utf8');
    let status: number | null = 0;
    let stdout = '';
    let stderr = '';
    try {
        stdout = execFileSync(process.execPath, [VERIFY_EXPORT_SCRIPT, file, '--json'], {encoding: 'utf8', timeout: 30_000, maxBuffer: 16 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe']});
    } catch (error) {
        // A non-zero exit throws, with what the process printed attached; a timeout or a failed spawn has no status.
        const failed = error as {status?: number | null; signal?: string | null; stdout?: string; stderr?: string; message?: string};
        status = failed.status ?? null;
        stdout = failed.stdout ?? '';
        stderr = [failed.stderr, failed.signal ? `killed by ${failed.signal}` : '', status === null ? failed.message : ''].filter(Boolean).join(' · ');
    }
    let report: VerifyReport | null = null;
    try {
        report = JSON.parse(stdout) as VerifyReport;
    } catch {
        report = null;
    }
    return {status, report, stderr};
}

/**
 * The lines of a source file an export names (`src/lib/…`, relative to `frontend/`), read from disk as the code is now;
 * null when the file is not there, or when the path leaves `frontend/` — an export is input.
 */
export async function sourceLines(file: string): Promise<string[] | null> {
    const full = resolve(FRONTEND_DIR, file);
    if (!full.startsWith(FRONTEND_DIR)) return null;
    try {
        return (await readFile(full, 'utf8')).split('\n');
    } catch {
        return null;
    }
}

/** Whether source lines write the test id `testid` as a string: `data-testid="…"`, a `testid` prop, a script constant. */
export function writesTestid(lines: string[], testid: string): boolean {
    const literal = testid.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const quoted = new RegExp(`["'\`]${literal}["'\`]`);
    return lines.some((line) => quoted.test(line));
}

/**
 * The places, among `places` (occurrences or candidates of an export), that are in the component of an element, read
 * from disk as the code is now: the line holds `needle`, and the file writes the element's test id. As `file:line`.
 */
export async function placesInComponent(places: {file: string; line: number}[], needle: string, testid: string): Promise<string[]> {
    const found: string[] = [];
    for (const place of places) {
        const lines = await sourceLines(place.file);
        if (lines && (lines[place.line - 1] ?? '').includes(needle) && writesTestid(lines, testid)) found.push(`${place.file}:${place.line}`);
    }
    return found;
}
