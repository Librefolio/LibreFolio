/**
 * Designer Lab — live preview: what the Lab changes in its own tab shows at once in an app tab of the same browser.
 *
 * The Lab keeps its changes in localStorage and every other tab of the origin applies them on the `storage` event: L1
 * overrides a CSS variable on `<html>`, L2 rewrites a colour in the stylesheets, L3 maps a colour in the ECharts
 * options, and the colour-vision simulation filters the whole page. Each test opens the app in its page and the Lab
 * in a second page of the same context, makes the change in the Lab through its editor and reads the effect in the
 * app — a computed style, the chart option through the debug hook `window.__lfDesignerLab` — then undoes it: suspend
 * and resume, reset all, import of the exported file.
 *
 * The elements are the app's own and exist whatever the data: the subtitle of the transactions page (a Tailwind
 * colour class, so a palette variable), the date header of the transactions table (DataTable's `th` rule, a
 * stylesheet literal), the dashboard's growth chart. Which colour to change is read from them at run time, never
 * written down: a designer will change these colours, and the tests must keep following them.
 *
 * Nothing is written server-side: TEST_USER only reads, the theme toggle and the Lab keep their state in this
 * context's localStorage, and the context dies with the test.
 */
import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {
    applyChange,
    chartColourValues,
    chooseTheme,
    computedStyle,
    CROSS_TAB,
    dateColumnHeader,
    DESKTOP_ONLY,
    downloadExport,
    editLightTheme,
    expectChanges,
    hexKeyOf,
    IDLE_STATS,
    labActive,
    labStats,
    listedKeys,
    opaqueHexOf,
    openDashboardGrowthChart,
    openLab,
    openTransactions,
    textPaletteClassOf,
    transactionsSubtitle,
} from './lab-helpers';

test.setTimeout(60_000);

/** New colours no element of the app uses, so the effect of a change cannot be mistaken for the app's own colours. */
const PINK = '#ff00aa';
const PINK_RGB = 'rgb(255, 0, 170)';
const BLUE = '#00aaff';
const BLUE_RGB = 'rgb(0, 170, 255)';
const GREEN = '#00ff00';
const GROWTH_CHART = '[data-testid="growth-chart"]';

test.describe('Designer Lab — live preview in another tab', () => {
    test.beforeEach(async ({}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', DESKTOP_ONLY);
    });

    test('the Lab page loads the colour catalogue of the build', async ({page}) => {
        await page.goto('/designer-lab');
        const root = page.getByTestId('designer-lab');
        await expect(root, 'the test server must serve a debug build (dev.py server --test builds one): /designer-lab rendered no Lab').toBeVisible({timeout: 30_000});
        await expect(root).toHaveAttribute('data-catalog-hash', /^sha256:[0-9a-f]{64}$/);
        await expect(root).toHaveAttribute('data-changes', '0');
        await expect(page.getByTestId('lab-reset-all'), 'nothing to reset in a fresh browser').toBeDisabled();

        for (const layer of ['css-literal', 'chart-color']) {
            await expect(page.getByTestId(`lab-overview-layer-${layer}`).locator('strong'), `the overview counts the ${layer} colours written in the app's sources`).toHaveText(/^[1-9]\d*$/);
        }
        const lists = {palette: 'lab-item-var---color-', sheets: 'lab-item-value-css-literal-', charts: 'lab-item-value-chart-color-'};
        for (const [tab, prefix] of Object.entries(lists)) {
            await page.getByTestId(`lab-tab-${tab}`).click();
            await expect(page.locator(`[data-testid^="${prefix}"]`), `the ${tab} tab lists the catalogue's colours`).not.toHaveCount(0);
        }
        await page.getByTestId('lab-tab-element').click();
        await expect(page.getByTestId('lab-picked-none'), 'no element picked yet').toBeVisible();
    });

    test('L3: a chart colour reaches the charts of another tab, and reset all gives them back', async ({page, context}) => {
        await login(page, TEST_USER);
        await chooseTheme(page, 'light');
        await openDashboardGrowthChart(page);
        // Colours by value throughout: the engine writes its own canvas form, and an option may spell one colour twice
        // (`#fff`, `#ffffff`); what the designer sees is the value.
        const before = await chartColourValues(page, GROWTH_CHART);
        expect(before.length, 'the growth chart has colours in its option').toBeGreaterThan(0);
        expect(before, 'precondition: the new colour is not one of the chart').not.toContain(GREEN);

        const lab = await openLab(context);
        await editLightTheme(lab);
        // A colour this chart draws that the catalogue lists as a chart colour: read from both, not written down.
        const listed = await listedKeys(lab, 'charts');
        const key = before.map(hexKeyOf).find((k): k is string => k !== null && listed.includes(k));
        if (!key) throw new Error(`no colour of the growth chart is a chart colour of the catalogue — chart: ${before.join(', ')}`);

        await applyChange(lab, {tab: 'charts', search: key, item: `lab-item-value-chart-color-${key}`, layer: 'chart-color', target: key, to: GREEN});
        await expect.poll(() => chartColourValues(page, GROWTH_CHART), {...CROSS_TAB, message: `${key} of the growth chart becomes ${GREEN}`}).toContain(GREEN);
        await expect.poll(async () => (await chartColourValues(page, GROWTH_CHART)).includes(key), {...CROSS_TAB, message: `no ${key} is left in the growth chart`}).toBe(false);
        await expect.poll(() => labActive(page)).toBe(true);
        await expect.poll(async () => (await labStats(page))?.chartInstances ?? 0, {message: 'the chart on screen was patched in place'}).toBeGreaterThan(0);

        await lab.getByTestId('lab-reset-all').click();
        await expectChanges(lab, 0);
        await expect.poll(() => labActive(page), CROSS_TAB).toBe(false);
        await expect.poll(() => chartColourValues(page, GROWTH_CHART), {...CROSS_TAB, message: 'the chart gets its own colours back'}).toEqual(before);
        await expect.poll(() => labStats(page)).toEqual(IDLE_STATS);
    });

    test.describe('on the transactions page', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_USER);
            await openTransactions(page);
            await chooseTheme(page, 'light');
        });

        test('L1: a palette variable recolours an element of another tab', async ({page, context}) => {
            const subtitle = transactionsSubtitle(page);
            const {className, variable} = await textPaletteClassOf(subtitle);
            expect(await computedStyle(subtitle), 'precondition: the new colour is not the subtitle colour').not.toBe(PINK_RGB);

            const lab = await openLab(context);
            await editLightTheme(lab);
            await applyChange(lab, {tab: 'palette', search: variable, item: `lab-item-var-${variable}`, layer: 'css-var', target: variable, to: PINK});

            await expect(subtitle, `${className} reads ${variable}: the app tab follows the Lab`).toHaveCSS('color', PINK_RGB, CROSS_TAB);
            await expect.poll(() => labActive(page)).toBe(true);
            await expect.poll(() => labStats(page)).toMatchObject({varOverrides: 1, elementRules: 0});
        });

        test('L2: a stylesheet colour recolours an element of another tab', async ({page, context}) => {
            const header = dateColumnHeader(page);
            const original = await computedStyle(header);
            const key = opaqueHexOf(original);
            if (!key) throw new Error(`the DataTable header must be coloured by an opaque sRGB stylesheet literal, it shows ${original}`);

            const lab = await openLab(context);
            await editLightTheme(lab);
            await applyChange(lab, {tab: 'sheets', search: key, item: `lab-item-value-css-literal-${key}`, layer: 'css-literal', target: key, to: BLUE});

            await expect(header, `DataTable's th rule writes ${key}: the app tab follows the Lab`).toHaveCSS('color', BLUE_RGB, CROSS_TAB);
            await expect.poll(() => labActive(page)).toBe(true);
            await expect.poll(async () => (await labStats(page))?.cssRules ?? 0, {message: 'declarations rewritten in the app tab'}).toBeGreaterThan(0);
        });

        test('suspend shows the original colours, resume brings the changes back', async ({page, context}) => {
            const subtitle = transactionsSubtitle(page);
            const {variable} = await textPaletteClassOf(subtitle);
            const original = await computedStyle(subtitle);

            const lab = await openLab(context);
            await editLightTheme(lab);
            await applyChange(lab, {tab: 'palette', search: variable, item: `lab-item-var-${variable}`, layer: 'css-var', target: variable, to: PINK});
            await expect(subtitle).toHaveCSS('color', PINK_RGB, CROSS_TAB);

            const suspend = lab.getByTestId('lab-suspend');
            await expect(suspend).toHaveAttribute('aria-pressed', 'false');
            await suspend.click();
            await expect(suspend).toHaveAttribute('aria-pressed', 'true');
            await expect(subtitle, 'suspended: the app shows its own colour').toHaveCSS('color', original, CROSS_TAB);
            await expect.poll(() => labActive(page)).toBe(false);
            await expectChanges(lab, 1);

            await suspend.click();
            await expect(suspend).toHaveAttribute('aria-pressed', 'false');
            await expect(subtitle, 'resumed: the change is back').toHaveCSS('color', PINK_RGB, CROSS_TAB);
            await expect.poll(() => labActive(page)).toBe(true);
        });

        test('the colour-vision simulation filters another tab', async ({page, context}) => {
            const filter = () => page.evaluate(() => getComputedStyle(document.documentElement).filter);
            expect(await filter()).toBe('none');

            const lab = await openLab(context);
            await lab.getByTestId('lab-cvd').selectOption('deuteranopia');
            await expect.poll(filter, {...CROSS_TAB, message: 'an SVG filter on <html> of the app tab'}).toContain('url(');
            await expect.poll(() => labActive(page)).toBe(true);

            await lab.getByTestId('lab-cvd').selectOption('none');
            await expect.poll(filter, CROSS_TAB).toBe('none');
            await expect.poll(() => labActive(page)).toBe(false);
        });

        test('export JSON, reset all, import back: the same changes on the same elements', async ({page, context}) => {
            const subtitle = transactionsSubtitle(page);
            const header = dateColumnHeader(page);
            const {variable} = await textPaletteClassOf(subtitle);
            const subtitleOriginal = await computedStyle(subtitle);
            const headerOriginal = await computedStyle(header);
            const key = opaqueHexOf(headerOriginal);
            if (!key) throw new Error(`the DataTable header must be coloured by an opaque sRGB stylesheet literal, it shows ${headerOriginal}`);

            const lab = await openLab(context);
            await editLightTheme(lab);
            // One change per layer. The chart colour is any colour the catalogue lists as one, read at run time: which
            // values the chart sources write is not this test's subject, and they move.
            const chartKey = (await listedKeys(lab, 'charts')).find((k) => k !== key);
            if (!chartKey) throw new Error(`the catalogue must list a chart colour other than ${key}`);
            await applyChange(lab, {tab: 'palette', search: variable, item: `lab-item-var-${variable}`, layer: 'css-var', target: variable, to: PINK});
            await applyChange(lab, {tab: 'sheets', search: key, item: `lab-item-value-css-literal-${key}`, layer: 'css-literal', target: key, to: BLUE});
            await applyChange(lab, {tab: 'charts', search: chartKey, item: `lab-item-value-chart-color-${chartKey}`, layer: 'chart-color', target: chartKey, to: GREEN});
            await expect(subtitle).toHaveCSS('color', PINK_RGB, CROSS_TAB);
            await expect(header).toHaveCSS('color', BLUE_RGB, CROSS_TAB);

            const {text, doc} = await downloadExport(lab);
            expect(doc.schema).toBe('lf-designer-lab/1');
            expect(doc.catalog_hash).toBe(await lab.getByTestId('designer-lab').getAttribute('data-catalog-hash'));
            expect(doc.changes.map((c) => [c.id, c.layer, c.scope, c.target, c.to])).toEqual([
                [`css-var:${variable}@light`, 'css-var', 'light', variable, PINK],
                [`css-literal:${key}@light`, 'css-literal', 'light', key, BLUE],
                [`chart-color:${chartKey}@light`, 'chart-color', 'light', chartKey, GREEN],
            ]);
            const [varChange, literalChange, chartChange] = doc.changes;
            expect(varChange.impact?.uses, 'a variable change says how many uses it reaches').toBeGreaterThan(0);
            expect(
                literalChange.occurrences.some((o) => o.file.endsWith('lib/components/table/DataTable.svelte')),
                'the occurrences of a stylesheet colour name the files that write it, DataTable.svelte among them',
            ).toBe(true);
            expect(chartChange.occurrences.length).toBeGreaterThan(0);

            await lab.getByTestId('lab-reset-all').click();
            await expectChanges(lab, 0);
            await expect.poll(() => labActive(page), CROSS_TAB).toBe(false);
            await expect.poll(() => labStats(page)).toEqual(IDLE_STATS);
            await expect(subtitle, 'reset: the app shows its own colours again').toHaveCSS('color', subtitleOriginal);
            await expect(header).toHaveCSS('color', headerOriginal);

            await lab.getByTestId('lab-import-input').setInputFiles({name: 'designer-lab-changes.json', mimeType: 'application/json', buffer: Buffer.from(text)});
            await expectChanges(lab, 3);
            await expect(lab.getByTestId('lab-status'), 'the import is accepted').toHaveAttribute('data-kind', /^(ok|warn)$/);
            await expect(subtitle, 'imported: the same changes again').toHaveCSS('color', PINK_RGB, CROSS_TAB);
            await expect(header).toHaveCSS('color', BLUE_RGB, CROSS_TAB);
            await expect.poll(() => labActive(page)).toBe(true);
        });
    });
});
