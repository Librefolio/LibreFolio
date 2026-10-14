/**
 * Designer Lab E2E helpers: the Lab in one page, the app in another page of the same browser context.
 *
 * The Lab is a debug-only page (`/designer-lab`) and the test server always serves a debug build, so it is there in
 * every E2E run. Its state lives in the context's localStorage and reaches the other pages of the same origin through
 * the `storage` event: two pages of one Playwright context are two tabs of one browser, which is exactly the flow the
 * Lab is built for. Nothing here touches the server: what the Lab writes dies with the test's context.
 *
 * The app tab publishes `window.__lfDesignerLab` (`active`, `picking`, `stats`, `chartColors`) from the client every
 * page of a debug build loads; every wait below reads that state, a computed style or a test id — never the clock.
 */

import {readFile} from 'node:fs/promises';
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

/** The style and SVG nodes the engines inject while a state is active; an idle client injects none of them. */
export const LAB_NODE_IDS = ['lf-designer-lab-vars', 'lf-designer-lab-elements', 'lf-designer-lab-layer-order', 'lf-designer-lab-cvd-style', 'lf-designer-lab-cvd-svg'];

export const IDLE_STATS = {cssRules: 0, chartInstances: 0, varOverrides: 0, elementRules: 0};

interface LabStats {
    cssRules: number;
    chartInstances: number;
    varOverrides: number;
    elementRules: number;
}

interface LabHook {
    active: () => boolean;
    picking: () => boolean;
    stats: () => LabStats;
    chartColors: (selector: string) => Promise<string[]>;
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
    impact?: {uses: number; files: number};
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

/** The subtitle under the transactions page's title: a `<p>` coloured by a Tailwind text utility, whatever the data. */
export function transactionsSubtitle(page: Page): Locator {
    return page.getByTestId('transactions-page-overview-guide-target').locator('p');
}

/** The header cell of the date column of the transactions table: DataTable colours it in its own `th` rule. */
export function dateColumnHeader(page: Page): Locator {
    return page.getByTestId('tx-table').getByTestId('dt-header-date');
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

/**
 * Change one catalogue item to `to` through the editor: open the tab, narrow the list with the search, open the item,
 * type the new colour and apply. Returns once the Lab holds one more change.
 */
export async function applyChange(lab: Page, opts: {tab: 'palette' | 'vars' | 'sheets' | 'charts'; search: string; item: string; layer: string; target: string; to: string}): Promise<void> {
    const before = Number(await lab.getByTestId('designer-lab').getAttribute('data-changes'));
    await lab.getByTestId(`lab-tab-${opts.tab}`).click();
    await lab.getByTestId('lab-search').fill(opts.search);
    await expect(lab.getByTestId('lab-search')).toHaveValue(opts.search);
    const item = lab.getByTestId(opts.item);
    await expect(item, `the Lab must list ${opts.item}: the catalogue is built from the colours of the app's sources`).toBeVisible();
    await item.click();
    const editor = lab.getByTestId('lab-editor');
    await expect(editor).toHaveAttribute('data-layer', opts.layer);
    await expect(editor).toHaveAttribute('data-target', opts.target);
    await lab.getByTestId('lab-editor-to').fill(opts.to);
    await expect(lab.getByTestId('lab-editor-to')).toHaveValue(opts.to);
    await lab.getByTestId('lab-editor-apply').click();
    await expectChanges(lab, before + 1);
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

/** The computed value of a CSS property of the element `locator` resolves to. */
export async function computedStyle(locator: Locator, property = 'color'): Promise<string> {
    return locator.evaluate((el, name) => getComputedStyle(el).getPropertyValue(name).trim(), property);
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

/**
 * The Tailwind palette variable the text-colour class of an element reads (`text-gray-500` → `--color-gray-500`), with
 * that class. Colour classes are the Lab's subject, so here an element is described by them on purpose.
 */
export async function textPaletteClassOf(locator: Locator): Promise<{className: string; variable: string}> {
    const classes = ((await locator.getAttribute('class')) ?? '').split(/\s+/);
    const className = classes.find((c) => /^text-[a-z]+-\d{2,3}$/.test(c));
    if (!className) throw new Error(`the element carries no Tailwind text colour class (classes: ${classes.join(' ')})`);
    return {className, variable: `--color-${className.slice('text-'.length)}`};
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

/** Click «JSON» and read the file the Lab downloads. */
export async function downloadExport(lab: Page): Promise<{text: string; doc: LabExport}> {
    const [download] = await Promise.all([lab.waitForEvent('download'), lab.getByTestId('lab-export-json').click()]);
    expect(download.suggestedFilename()).toBe('designer-lab-changes.json');
    const text = await readFile(await download.path(), 'utf8');
    return {text, doc: JSON.parse(text) as LabExport};
}
