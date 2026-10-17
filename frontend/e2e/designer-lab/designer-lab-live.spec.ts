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
 * colour class: a palette class today, a colour-role utility once workstream T migrates the page), the login card a
 * visitor who is not logged in gets at `/` (a colour-role utility of workstream T), the date header of the transactions
 * table (a colour the stylesheets write as a literal — in DataTable's `th` rule once, in the `:root` token that rule
 * reads since R-3), the dashboard's growth chart. Which colour to change is read from them at run time, never written
 * down: a designer will change these colours, and the tests must keep following them. A colour class is followed to
 * what the Lab edits for it (`colourSourceOf`): a palette class to its variable, a role utility to the role its rule
 * reads in the page's CSSOM, through the chip of its `@theme inline` alias. Where the code writes a colour is not written
 * down either: the export is held to the verifier the Lab ships, which finds each occurrence in today's code.
 *
 * The editor's opacity slider (A, `lab-editor-a`) is held to the same effect in the other tab. On an opaque role — the
 * login card's background — it writes the colour with an alpha, in whichever notation; on a variable the sources write
 * at an opacity, `color-mix(in <space>, <base> <p>%, transparent)`, it moves the share and keeps the base, and a `var()`
 * base stays a reference, which the app tab proves by following it. That variable is read from the catalogue the Lab
 * lists, never named here, and colours are compared as the app tab paints them (`paintedColours`), not as texts.
 *
 * Nothing is written server-side: TEST_USER only reads, the visitor never signs in, the theme toggle and the Lab keep
 * their state in this context's localStorage, and the context dies with the test.
 *
 * The chart categories (contracts C1–C4 with DV) are edited by key: every chart asks `categoryColor(kind, key, dark)` when
 * it draws, the Lab's engine answers for the category it changed, and the charts that read categories or roles rebuild
 * their option on `lf:chart-colors-change` (C4) — which the engine also fires for an L1 edit of a role. The allocation pie
 * of the dashboard is read through the same hook as the growth chart, its values never written down: the «Categories»
 * tab lists them. The signal itself is counted in the app tab: one each for an L1 edit, a literal inside a role's
 * definition, and a reset.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {
    ALLOCATION_PIE,
    applyChange,
    categoryValues,
    CHART_COLORS_EVENT,
    chartColourValues,
    chooseTheme,
    colourSourceOf,
    computedStyle,
    CROSS_TAB,
    dateColumnHeader,
    describeColour,
    DESKTOP_ONLY,
    downloadExport,
    editLightTheme,
    expectChanges,
    expectPainted,
    hexKeyOf,
    IDLE_STATS,
    labActive,
    labStats,
    listedKeys,
    LOGIN_CARD,
    newColourFor,
    opaqueHexOf,
    opaqueKeysOf,
    openDashboard,
    openDashboardGrowthChart,
    openEditor,
    openLab,
    openSignIn,
    openTransactions,
    paintedColours,
    placesInComponent,
    rootValueOf,
    sameColour,
    setSlider,
    showAllocationNow,
    sourceLines,
    transactionsSubtitle,
    transparentMixOf,
    verifyExport,
    waitForLabClient,
    type CategoryValue,
    type TransparentMix,
} from './lab-helpers';

test.setTimeout(60_000);

/** New colours no element of the app uses, so the effect of a change cannot be mistaken for the app's own colours. */
const PINK = '#ff00aa';
const PINK_RGB = 'rgb(255, 0, 170)';
const BLUE = '#00aaff';
const BLUE_RGB = 'rgb(0, 170, 255)';
const GREEN = '#00ff00';
const GREEN_RGB = 'rgb(0, 255, 0)';
/** The new colours a colour-role test may apply, in order: the first the role has in neither theme. */
const NEW_COLOURS = [
    {hex: PINK, rgb: PINK_RGB},
    {hex: BLUE, rgb: BLUE_RGB},
    {hex: GREEN, rgb: GREEN_RGB},
];
const GROWTH_CHART = '[data-testid="growth-chart"]';
/** A base the editor keeps as a reference: `var(--x)`, without a fallback. */
const VAR_BASE = /^var\(\s*(--[\w-]+)\s*\)$/;

/**
 * A root variable the sources write at an opacity, read from the catalogue the Lab lists: those the «Variables» tab
 * finds for `transparent`, each opened in the editor, whose source value in the edited theme (`lab-editor-from`) is a mix
 * in the role tokens' form (`transparentMixOf`). One whose base is a `var()` first — the case where keeping the base
 * matters — else any. Fails, naming every value it read, when the catalogue has none.
 */
async function translucentVariable(lab: Page): Promise<{name: string; from: string; mix: TransparentMix}> {
    await lab.getByTestId('lab-tab-vars').click();
    const search = lab.getByTestId('lab-search');
    await search.fill('transparent');
    await expect(search).toHaveValue('transparent');
    const prefix = 'lab-item-var-';
    const items = lab.locator(`[data-testid^="${prefix}"]`);
    await expect(items, 'the «Variables» tab must list a variable whose definition mentions transparent: the role tokens write a colour at an opacity as color-mix(in <space>, <base> <p>%, transparent)').not.toHaveCount(0);
    const names = await items.evaluateAll((nodes, start) => nodes.map((node) => (node.getAttribute('data-testid') ?? '').slice(start.length)), prefix);
    const editor = lab.getByTestId('lab-editor');
    const read: string[] = [];
    const mixes: {name: string; from: string; mix: TransparentMix}[] = [];
    for (const name of names) {
        await lab.getByTestId(`${prefix}${name}`).click();
        await expect(editor).toHaveAttribute('data-target', name);
        const from = ((await lab.getByTestId('lab-editor-from').textContent()) ?? '').trim();
        read.push(`${name} = ${from}`);
        const mix = transparentMixOf(from);
        if (mix) mixes.push({name, from, mix});
    }
    const found = mixes.find((m) => VAR_BASE.test(m.mix.base)) ?? mixes[0];
    if (!found)
        throw new Error(
            `no root variable of the catalogue is a colour at an opacity in the edited theme: none of those the «Variables» tab finds for transparent has a source value color-mix(in <space>, <base> <p>%, transparent), the form of the role tokens (lib/theme/tokens.css). Source values read: ${read.join('; ')}`,
        );
    return found;
}

/**
 * The one file of the chart categories (contracts C1–C2 with DV): every chart reads a category colour through it, one
 * literal per line, so the Lab exports a category edit as that file and that line.
 */
const CATEGORY_TABLES_FILE = 'src/lib/theme/chartCategories.ts';

/** The roles the charts read through `chartRoles` (`ChartRole`, lib/theme/roleColors.ts): their names, never their values. */
const CHART_ROLES = ['--lf-surface-card', '--lf-surface-panel', '--lf-text-primary', '--lf-text-secondary', '--lf-text-on-inverse', '--lf-danger', '--lf-info'];

/** The app tab's window, with what the C4 test leaves on it: its count of chart-colours signals, and its no-reload mark. */
type C4Window = Window & {__e2eLabC4?: number; __e2eLabNoReload?: boolean};

/** An asset type to edit, with its light value as the canvas writes it, and whether a sector shares that value. */
interface TypeToEdit {
    category: CategoryValue & {light: string};
    key: string;
    sharedWith: 'the sector pie' | 'a sector of the tables' | 'no sector';
}

/**
 * The asset type to edit: one whose light value the type pie draws, read from the «Categories» tab — never named here,
 * DV tunes the tables. Its value must be its own among what the type pie can draw (the types and the two buckets), so
 * that «the old value is gone» speaks of it alone. Preferred: a type whose value a sector also has on the sector pie,
 * then one a sector has in the tables — the cases where an edit by value would leak into the sectors. `lightKey` maps a
 * category's target to its light value as the canvas writes it. Fails, naming the assumption, when the pie draws none.
 */
function typeToEdit(categories: CategoryValue[], lightKey: Map<string, string | null>, typePie: string[], sectorPie: string[]): TypeToEdit {
    const drawable = categories.filter((c) => c.kind === 'type' || c.kind === 'bucket');
    const candidates = categories
        .filter((c): c is CategoryValue & {light: string} => c.kind === 'type' && c.light !== null)
        .map((category) => ({category, key: lightKey.get(category.target) ?? null}))
        .filter((c): c is {category: CategoryValue & {light: string}; key: string} => c.key !== null && typePie.includes(c.key))
        .filter((c) => !drawable.some((other) => other.target !== c.category.target && lightKey.get(other.target) === c.key));
    const sectorHas = (key: string) => categories.some((c) => c.kind === 'sector' && lightKey.get(c.target) === key);
    const onScreen = candidates.find((c) => sectorHas(c.key) && sectorPie.includes(c.key));
    if (onScreen) return {...onScreen, sharedWith: 'the sector pie'};
    const inTables = candidates.find((c) => sectorHas(c.key));
    if (inTables) return {...inTables, sharedWith: 'a sector of the tables'};
    const [any] = candidates;
    if (any) return {...any, sharedWith: 'no sector'};
    const types = categories.filter((c) => c.kind === 'type').map((c) => `${c.key} ${c.light ?? '—'}`);
    throw new Error(`no colour of the type pie is the light value of an asset type the «Categories» tab lists, a value of its own among the types and buckets: the pie must draw each family in categoryColor('type', family, false) (C1). Pie: ${typePie.join(', ')}; types: ${types.join(', ')}`);
}

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

    test('category: one asset type changes in the charts of another tab, by key', async ({page, context}, testInfo) => {
        await login(page, TEST_USER);
        await openDashboard(page);
        await waitForLabClient(page);
        await chooseTheme(page, 'light');
        // Both pies before any change, colours by value as the canvas writes them. The sector pie first: the edit is made
        // with the type pie on screen, and the sector pie is drawn again only after it.
        await showAllocationNow(page, 'sector');
        const sectorBefore = await chartColourValues(page, ALLOCATION_PIE);
        expect(sectorBefore.length, 'the sector pie has colours in its option').toBeGreaterThan(0);
        await showAllocationNow(page, 'type');
        const typeBefore = await chartColourValues(page, ALLOCATION_PIE);
        expect(typeBefore.length, 'the type pie has colours in its option').toBeGreaterThan(0);

        const lab = await openLab(context);
        await editLightTheme(lab);
        // The values of the tables, as the Lab lists them, in the form the canvas writes them: compared with the pies.
        const categories = await categoryValues(lab);
        const lightKeys = await opaqueKeysOf(
            page,
            categories.map((c) => c.light ?? ''),
        );
        const darkKeys = await opaqueKeysOf(
            page,
            categories.map((c) => c.dark ?? ''),
        );
        const lightKey = new Map(categories.map((c, i) => [c.target, lightKeys[i]]));
        const chosen = typeToEdit(categories, lightKey, typeBefore, sectorBefore);
        const {target, light} = chosen.category;
        // A colour no category has, in either theme, and neither pie draws: nothing on screen can be mistaken for it.
        const taken = new Set([...typeBefore, ...sectorBefore, ...lightKeys, ...darkKeys]);
        const fresh = NEW_COLOURS.find((c) => !taken.has(c.hex));
        if (!fresh) throw new Error(`no new colour left: ${NEW_COLOURS.map((c) => c.hex).join(', ')} are all drawn by a pie or written in the category tables`);
        testInfo.annotations.push({type: 'category', description: `${target}: ${light} → ${fresh.hex}; its value shared with ${chosen.sharedWith}`});

        // The editor opens on the category: its value in the edited theme, what an edit reaches, the lines it is written at.
        await openEditor(lab, {tab: 'categories', search: chosen.category.key, item: `lab-item-category-${target}`, layer: 'category', target});
        await expect(lab.getByTestId('lab-editor-from'), `the editor starts from the light value of ${target}`).toHaveText(light);
        await expect(lab.getByTestId('lab-editor-category-reach'), 'the editor says an edit reaches this category only').toBeVisible();
        await expect(lab.getByTestId('lab-editor-category-lines'), 'the editor lists the lines the tables write the category at').toBeVisible();
        await applyChange(lab, {tab: 'categories', search: chosen.category.key, item: `lab-item-category-${target}`, layer: 'category', target, to: fresh.hex});

        // The pie on screen redraws (C4) with the new colour for the type, and only for it.
        const typeAfter = [...typeBefore.filter((c) => c !== chosen.key), fresh.hex].sort();
        await expect.poll(() => chartColourValues(page, ALLOCATION_PIE), {...CROSS_TAB, message: `${target} turns ${fresh.hex} in the type pie: ${chosen.key} gone, every other colour as it was`}).toEqual(typeAfter);
        await expect.poll(() => labActive(page)).toBe(true);
        await expect.poll(() => labStats(page)).toMatchObject({categoryOverrides: 1, varOverrides: 0, elementRules: 0});

        // By key, not by value: the sector pie, drawn with the change on, keeps every colour it had — a sector whose
        // value is the one the type had included.
        await showAllocationNow(page, 'sector');
        await expect
            .poll(() => chartColourValues(page, ALLOCATION_PIE), {
                message: chosen.sharedWith === 'the sector pie' ? `by key: the sector pie keeps ${chosen.key}, the value ${target} shares with a sector, and every other colour` : 'by key: the sector pie keeps every colour',
            })
            .toEqual(sectorBefore);

        // The export names the category and the one line the tables write its light value at.
        const {text, doc} = await downloadExport(lab);
        expect(doc.schema).toBe('lf-designer-lab/1');
        expect(doc.changes.map((c) => [c.id, c.layer, c.scope, c.target, c.to])).toEqual([[`category:${target}@light`, 'category', 'light', target, fresh.hex]]);
        const [change] = doc.changes;
        expect(change.category, 'the export names the category by its kind and its key').toEqual({kind: 'type', key: chosen.category.key});
        expect(
            change.occurrences.map((o) => o.file),
            `one occurrence: the light line of ${target} in the tables (C2: one literal per line)`,
        ).toEqual([CATEGORY_TABLES_FILE]);
        const [occurrence] = change.occurrences;
        expect((occurrence.raw ?? '').toLowerCase(), `the occurrence is the value the table writes for ${target}`).toBe(light.toLowerCase());
        const lines = await sourceLines(occurrence.file);
        expect((lines?.[occurrence.line - 1] ?? '').toLowerCase(), `${occurrence.file}:${occurrence.line} writes ${light} on disk`).toContain(light.toLowerCase());
        const verified = await verifyExport(text, testInfo.outputPath('designer-lab-changes.json'));
        const report = verified.report;
        if (!report) throw new Error(`verify-export.mjs printed no JSON report (exit ${verified.status}): ${verified.stderr}`);
        expect(report.totals.changes, 'the verifier read the one change').toBe(1);
        expect(
            report.changes.flatMap((c) => c.missing.map((m) => `${c.id} ${m.file}:${m.line} ${m.raw ?? ''}`)),
            'the line the export lists still writes the value',
        ).toEqual([]);
        expect(report.totals.missing).toBe(0);
        expect(verified.status, `verify-export.mjs exits 0 when nothing is missing: ${verified.stderr}`).toBe(0);
        expect(report.totals.ok, 'positive control: the verifier found the occurrence in place').toBeGreaterThan(0);

        // Back on the type pie, the change still on: mounted again, it draws the new colour from its first pass. Then reset
        // all: the pie on screen redraws with its own colours, without a reload.
        await showAllocationNow(page, 'type');
        await expect.poll(() => chartColourValues(page, ALLOCATION_PIE), {...CROSS_TAB, message: `the type pie, mounted again, draws ${target} in ${fresh.hex}`}).toEqual(typeAfter);
        await lab.getByTestId('lab-reset-all').click();
        await expectChanges(lab, 0);
        await expect.poll(() => chartColourValues(page, ALLOCATION_PIE), {...CROSS_TAB, message: 'reset: the type pie draws its own colours again'}).toEqual(typeBefore);
        await expect.poll(() => labActive(page), CROSS_TAB).toBe(false);
        await expect.poll(() => labStats(page)).toEqual(IDLE_STATS);
    });

    test("C4: an L1 edit, a literal inside a role's definition and a reset each reach the other tab as one chart-colours signal", async ({page, context}) => {
        await login(page, TEST_USER);
        await openDashboard(page);
        await waitForLabClient(page);
        await chooseTheme(page, 'light');
        // The signal the charts rebuild their option on (C4), counted in the app tab from here on, and a mark on its window:
        // a reload would wipe both. Read as state, never as an edge.
        await page.evaluate((event) => {
            const w = window as C4Window;
            w.__e2eLabC4 = 0;
            w.__e2eLabNoReload = true;
            document.addEventListener(event, () => {
                w.__e2eLabC4 = (w.__e2eLabC4 ?? 0) + 1;
            });
        }, CHART_COLORS_EVENT);
        const signals = () => page.evaluate(() => (window as C4Window).__e2eLabC4 ?? null);
        const notReloaded = () => page.evaluate(() => (window as C4Window).__e2eLabNoReload === true);
        /** The colour key of a variable as `<html>` of the app tab computes it: its value, as the canvas parses it. */
        const rootKeyOf = async (variable: string) => (await opaqueKeysOf(page, [await rootValueOf(page, variable)]))[0];

        const lab = await openLab(context);
        await editLightTheme(lab);
        // B: a role the charts read through chartRoles whose light value is a literal of the stylesheets — the value of its
        // definition in tokens.css, which the Lab lists — compared as colour keys. Read before any change.
        const sheetKeys = await listedKeys(lab, 'sheets');
        const roleValues = await Promise.all(CHART_ROLES.map(async (name) => ({name, value: await rootValueOf(page, name), key: await rootKeyOf(name)})));
        const roleB = roleValues.find((r): r is {name: string; value: string; key: string} => r.key !== null && !/^color-mix\(/i.test(r.value) && sheetKeys.includes(r.key));
        if (!roleB) throw new Error(`no role the charts read has a light value the «Stylesheets» tab lists: the definitions of the roles in tokens.css must write their light values as literals. Values on <html>: ${roleValues.map((r) => `${r.name} = ${r.value || '(empty)'}`).join('; ')}`);

        // A: any colour role but B — C4 follows the layer, not the variable — one the charts do not read preferred, so that
        // its edit stays clear of B. The palette lists each role utility under its @theme inline alias, and the chip edits
        // the role it names (data-target).
        await lab.getByTestId('lab-tab-palette').click();
        const search = lab.getByTestId('lab-search');
        await search.fill('');
        await expect(search).toHaveValue('');
        const chipPrefix = 'lab-item-var-';
        const roleChips = lab.locator(`[data-testid^="${chipPrefix}"][data-target^="--lf-"]`);
        await expect(roleChips, 'the palette lists the colour-role utilities of workstream T, each chip editing its role').not.toHaveCount(0);
        const chips = (await roleChips.evaluateAll((nodes, start) => nodes.map((node) => ({chipVar: (node.getAttribute('data-testid') ?? '').slice(start.length), target: node.getAttribute('data-target') ?? ''})), chipPrefix)).filter((c) => c.target !== roleB.name);
        const roleA = chips.find((c) => !CHART_ROLES.includes(c.target)) ?? chips[0];
        if (!roleA) throw new Error(`the palette lists no role chip but the one of ${roleB.name}`);
        const freshA = await newColourFor(page, roleA.target, NEW_COLOURS);
        await applyChange(lab, {tab: 'palette', search: roleA.chipVar, item: `${chipPrefix}${roleA.chipVar}`, layer: 'css-var', target: roleA.target, to: freshA.hex});
        await expect.poll(signals, {...CROSS_TAB, message: `the L1 edit of ${roleA.target} reaches the app tab as one chart-colours signal`}).toBe(1);
        await expect.poll(() => labStats(page)).toMatchObject({varOverrides: 1, categoryOverrides: 0, elementRules: 0});
        expect(await rootKeyOf(roleB.name), `the edit of ${roleA.target} leaves ${roleB.name} as it was: the literal step reads it`).toBe(roleB.key);

        // The literal B's definition writes: the stylesheet pass rewrites a variable's definition, so the charts are told.
        const freshB = await newColourFor(
            page,
            roleB.name,
            NEW_COLOURS.filter((c) => c.hex !== freshA.hex),
        );
        await applyChange(lab, {tab: 'sheets', search: roleB.key, item: `lab-item-value-css-literal-${roleB.key}`, layer: 'css-literal', target: roleB.key, to: freshB.hex});
        await expect.poll(async () => ({value: await rootKeyOf(roleB.name), signals: await signals()}), {...CROSS_TAB, message: `${roleB.name} on <html> of the app tab turns ${freshB.hex}, with one more chart-colours signal`}).toEqual({value: freshB.hex, signals: 2});

        // Reset all: the variable and the definition go back, in one pass and one signal.
        await lab.getByTestId('lab-reset-all').click();
        await expectChanges(lab, 0);
        await expect.poll(async () => ({value: await rootKeyOf(roleB.name), signals: await signals()}), {...CROSS_TAB, message: `reset: ${roleB.name} is ${roleB.key} again, with one more chart-colours signal`}).toEqual({value: roleB.key, signals: 3});
        expect(await notReloaded(), 'the app tab followed the Lab in place: no reload').toBe(true);
        await expect.poll(() => labActive(page), CROSS_TAB).toBe(false);
        await expect.poll(() => labStats(page)).toEqual(IDLE_STATS);
    });

    test('L1: a colour role recolours an element of another tab, through the chip of its utility', async ({page, context}, testInfo) => {
        const card = await openSignIn(page);
        await waitForLabClient(page);
        await chooseTheme(page, 'light');
        // The card's background class, followed to what the Lab edits for it: the role its rule reads in the CSSOM.
        const source = await colourSourceOf(card, 'bg');
        expect(source.role, `${source.className} must be a colour-role utility: the login card reads the roles of workstream T`).toBe(true);
        expect(source.target, `${source.className} reads a role`).toMatch(/^--lf-/);
        const original = await computedStyle(card, 'background-color');
        // A colour the role has in neither theme, read from the page: T changes the values of the roles.
        const fresh = await newColourFor(page, source.target, NEW_COLOURS, [original]);

        const lab = await openLab(context);
        await editLightTheme(lab);
        // The palette lists the utility under its alias, and the chip edits the role: either name finds it.
        await lab.getByTestId('lab-tab-palette').click();
        const search = lab.getByTestId('lab-search');
        const chip = lab.getByTestId(`lab-item-var-${source.chipVar}`);
        for (const name of [source.target, source.chipVar]) {
            await search.fill(name);
            await expect(search).toHaveValue(name);
            await expect(chip, `searching ${name} finds the chip of ${source.className}`).toBeVisible();
        }
        await expect(chip, `the chip of ${source.chipVar} edits the role the alias stands for`).toHaveAttribute('data-target', source.target);
        await applyChange(lab, {tab: 'palette', search: source.chipVar, item: `lab-item-var-${source.chipVar}`, layer: 'css-var', target: source.target, to: fresh.hex});

        await expect(card, `${source.className} reads ${source.target}: the app tab follows the Lab`).toHaveCSS('background-color', fresh.rgb, CROSS_TAB);
        await expect.poll(() => labActive(page)).toBe(true);
        await expect.poll(() => labStats(page)).toMatchObject({varOverrides: 1, elementRules: 0});

        // The export names the role and finds its utilities in the code: each occurrence carries the class to look for,
        // since the line names neither the role nor a palette shade.
        const {text, doc} = await downloadExport(lab);
        expect(doc.schema).toBe('lf-designer-lab/1');
        expect(doc.changes.map((c) => [c.id, c.layer, c.scope, c.target, c.to])).toEqual([[`css-var:${source.target}@light`, 'css-var', 'light', source.target, fresh.hex]]);
        const [change] = doc.changes;
        expect(Object.keys(change.impact?.classes ?? {}), `the impact lists the utilities that read ${source.target}`).toContain(source.className);
        expect(change.occurrences.length, `the export lists where the code writes the utilities of ${source.target}`).toBeGreaterThan(0);
        expect(
            change.occurrences.filter((o) => !o.raw).map((o) => `${o.file}:${o.line}`),
            'every occurrence of a role names the class to find on its line',
        ).toEqual([]);
        const classUses = change.occurrences.filter((o) => o.raw === source.className);
        const inCard = await placesInComponent(classUses, source.className, LOGIN_CARD);
        expect(inCard.length, `an occurrence of ${source.className} in the component of ${LOGIN_CARD} — read from disk: the line writes the class, the file the test id. Occurrences of the class: ${classUses.map((o) => `${o.file}:${o.line}`).join(', ') || 'none'}`).toBeGreaterThan(0);
        const definitions = change.definitions ?? [];
        expect(definitions.length, `the export says where the sources define ${source.target}`).toBeGreaterThan(0);
        expect(
            definitions.filter((d) => !/(^|\/)tokens\.css$/.test(d.file)).map((d) => `${d.file}:${d.line}`),
            'a role is defined in the token file of workstream T only',
        ).toEqual([]);
        const verified = await verifyExport(text, testInfo.outputPath('designer-lab-changes.json'));
        const report = verified.report;
        if (!report) throw new Error(`verify-export.mjs printed no JSON report (exit ${verified.status}): ${verified.stderr}`);
        expect(
            report.changes.flatMap((c) => c.missing.map((m) => `${c.id} ${m.file}:${m.line} ${m.raw ?? ''}`)),
            'every occurrence the export lists is still written in the code',
        ).toEqual([]);
        expect(report.totals.missing).toBe(0);
        expect(
            report.changes.flatMap((c) => c.definitions.filter((d) => d.status !== 'ok').map((d) => `${d.file}:${d.line} ${d.status}`)),
            `the definitions of ${source.target} are where the export says`,
        ).toEqual([]);
        expect(verified.status, `verify-export.mjs exits 0 when nothing is missing: ${verified.stderr}`).toBe(0);
        expect(report.totals.ok, 'positive control: the verifier found occurrences in place').toBeGreaterThan(0);

        await lab.getByTestId('lab-reset-all').click();
        await expectChanges(lab, 0);
        await expect(card, 'reset: the card shows its own background again').toHaveCSS('background-color', original, CROSS_TAB);
        await expect.poll(() => labActive(page), CROSS_TAB).toBe(false);
        await expect.poll(() => labStats(page)).toEqual(IDLE_STATS);
    });

    test('A: the opacity of a colour role reaches another tab', async ({page, context}) => {
        const card = await openSignIn(page);
        await waitForLabClient(page);
        await chooseTheme(page, 'light');
        // The card's background class, followed to the role its rule reads; its colour, as the page paints it.
        const source = await colourSourceOf(card, 'bg');
        expect(source.role, `${source.className} must be a colour-role utility: the login card reads the roles of workstream T`).toBe(true);
        const original = await computedStyle(card, 'background-color');
        const [shown] = await paintedColours(page, [original]);
        if (!shown || shown.alpha !== 1) throw new Error(`the login card's background must be opaque, so that half of its opacity shows: it is ${original}`);

        const lab = await openLab(context);
        await editLightTheme(lab);
        await openEditor(lab, {tab: 'palette', search: source.chipVar, item: `lab-item-var-${source.chipVar}`, layer: 'css-var', target: source.target});
        await expect(lab.getByTestId(`lab-item-var-${source.chipVar}`), `the chip of ${source.chipVar} edits the role`).toHaveAttribute('data-target', source.target);
        const to = lab.getByTestId('lab-editor-to');
        const opacity = lab.getByTestId('lab-editor-a');
        // The editor starts from the role's value in the light theme: opaque, and the colour the card shows.
        await expect(opacity, 'the editor shows the opacity of the role').toBeVisible();
        await expect(opacity, 'an opaque colour: A at 1').toHaveValue('1');
        const start = await to.inputValue();
        const [startColour] = await paintedColours(page, [start]);
        expect(startColour !== null && sameColour(startColour, shown), `the editor starts from the colour the card shows: ${start} paints ${startColour ? describeColour(startColour) : 'nothing'}, the card ${describeColour(shown)}`).toBe(true);

        // Half the opacity: the same colour with an alpha, in whichever notation the editor writes it.
        const half = {r: shown.r, g: shown.g, b: shown.b, alpha: 0.5};
        await setSlider(opacity, 0.5);
        await expect(to, 'A rewrites the value').not.toHaveValue(start);
        const written = await to.inputValue();
        const [writtenColour] = await paintedColours(page, [written]);
        expect(writtenColour !== null && sameColour(writtenColour, half), `${written} is the colour of the card at half opacity, ${describeColour(half)}: it paints ${writtenColour ? describeColour(writtenColour) : 'nothing'}`).toBe(true);
        const apply = lab.getByTestId('lab-editor-apply');
        await expect(apply).toBeEnabled();
        await apply.click();
        await expectChanges(lab, 1);

        await expectPainted(page, () => computedStyle(card, 'background-color'), half, `${source.className} reads ${source.target}: the card shows its own colour at half opacity`);
        await expect.poll(() => labActive(page)).toBe(true);
        await expect.poll(() => labStats(page)).toMatchObject({varOverrides: 1, elementRules: 0});

        // The export carries the value as the editor wrote it, from the value it started from.
        const {doc} = await downloadExport(lab);
        expect(doc.changes.map((c) => [c.id, c.layer, c.scope, c.target, c.from, c.to])).toEqual([[`css-var:${source.target}@light`, 'css-var', 'light', source.target, start, written]]);

        await lab.getByTestId('lab-reset-all').click();
        await expectChanges(lab, 0);
        await expect(card, 'reset: the card shows its own background again').toHaveCSS('background-color', original, CROSS_TAB);
        await expect.poll(() => labActive(page), CROSS_TAB).toBe(false);
        await expect.poll(() => labStats(page)).toEqual(IDLE_STATS);
    });

    test('A on a translucent mix keeps its base', async ({page, context}) => {
        await openSignIn(page);
        await waitForLabClient(page);
        await chooseTheme(page, 'light');
        const lab = await openLab(context);
        await editLightTheme(lab);
        const {name, from, mix} = await translucentVariable(lab);
        const baseVar = VAR_BASE.exec(mix.base)?.[1] ?? null;
        // A share the source does not already have: 25%, or 50% when it says 25%.
        const share = mix.percent === 25 ? 0.5 : 0.25;
        const moved = `color-mix(in ${mix.space}, ${mix.base} ${share * 100}%, transparent)`;

        // The app tab before any change: the variable on <html>, its base as the page paints it, and the base at its share.
        const originalValue = await rootValueOf(page, name);
        const [base] = await paintedColours(page, [mix.base]);
        if (!base || base.alpha === 0) throw new Error(`the base of ${name}, ${mix.base}, must be a colour the app tab paints: it computes to ${base?.css ?? 'nothing'}`);
        await expectPainted(page, async () => `var(${name})`, {...base, alpha: (mix.percent / 100) * base.alpha}, `positive control: before any change, an element painted with ${name} shows ${mix.base} at ${mix.percent}%`);

        // The editor reads the mix: its source text, its share on A, Apply enabled.
        await openEditor(lab, {tab: 'vars', search: name, item: `lab-item-var-${name}`, layer: 'css-var', target: name});
        const to = lab.getByTestId('lab-editor-to');
        const opacity = lab.getByTestId('lab-editor-a');
        await expect(lab.getByTestId('lab-editor-from'), 'the editor shows the source definition').toHaveText(from);
        await expect(to, 'and starts from it').toHaveValue(from);
        await expect(opacity, 'the editor reads the mix: its share on the A slider').toBeVisible();
        await expect.poll(async () => Math.abs(Number(await opacity.inputValue()) - mix.percent / 100), {message: `A reads the share of the mix, ${mix.percent}%, to its step of 1%`}).toBeLessThanOrEqual(0.005 + 1e-9);
        await expect(lab.getByTestId('lab-editor-invalid'), 'the mix is a value the editor knows').toHaveCount(0);
        const apply = lab.getByTestId('lab-editor-apply');
        await expect(apply, 'the mix applies as it is').toBeEnabled();

        // A moves the share in place: the same space, the same base — a var() still one.
        await setSlider(opacity, share);
        await expect(to, `the mix at ${share * 100}%, its space and its base unchanged`).toHaveValue(moved);
        await apply.click();
        await expectChanges(lab, 1);

        // <html> of the app tab computes the mix at the new share. The browser substitutes a var() base when it computes a
        // custom property, so the base is compared as a colour.
        await expect
            .poll(
                async () => {
                    const value = await rootValueOf(page, name);
                    return {value, mix: transparentMixOf(value)};
                },
                {...CROSS_TAB, message: `${name} on <html> of the app tab: the mix at ${share * 100}%`},
            )
            .toMatchObject({mix: {space: mix.space, percent: share * 100}});
        const computed = transparentMixOf(await rootValueOf(page, name));
        if (!computed) throw new Error(`${name} on <html> of the app tab stopped being a mix: ${await rootValueOf(page, name)}`);
        const [computedBase] = await paintedColours(page, [computed.base]);
        expect(computedBase !== null && sameColour(computedBase, base), `the same base: ${computed.base} on <html> paints ${computedBase ? describeColour(computedBase) : 'nothing'}, ${mix.base} paints ${describeColour(base)}`).toBe(true);
        await expectPainted(page, async () => `var(${name})`, {...base, alpha: share * base.alpha}, `an element painted with ${name} shows ${mix.base} at ${share * 100}%`);
        await expect.poll(() => labActive(page)).toBe(true);
        await expect.poll(() => labStats(page)).toMatchObject({varOverrides: 1, elementRules: 0});

        if (baseVar) {
            // The base stays a reference in the app tab too: given another value on <html>, the mix follows it.
            const fresh = await newColourFor(page, baseVar, NEW_COLOURS);
            const [freshColour] = await paintedColours(page, [fresh.hex]);
            if (!freshColour) throw new Error(`the app tab must paint ${fresh.hex}`);
            await page.evaluate(({variable, value}) => document.documentElement.style.setProperty(variable, value), {variable: baseVar, value: fresh.hex});
            try {
                await expectPainted(page, async () => `var(${name})`, {...freshColour, alpha: share * freshColour.alpha}, `${name} reads ${baseVar}: with ${baseVar} at ${fresh.hex}, the mix follows`);
            } finally {
                await page.evaluate((variable) => document.documentElement.style.removeProperty(variable), baseVar);
            }
            await expectPainted(page, async () => `var(${name})`, {...base, alpha: share * base.alpha}, `${baseVar} restored: the mix shows ${mix.base} again`);
        }

        await lab.getByTestId('lab-reset-all').click();
        await expectChanges(lab, 0);
        await expect.poll(() => rootValueOf(page, name), {...CROSS_TAB, message: `reset: ${name} on <html> is its own value again`}).toBe(originalValue);
        await expect.poll(() => labActive(page), CROSS_TAB).toBe(false);
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
            const source = await colourSourceOf(subtitle, 'text');
            expect(await computedStyle(subtitle), 'precondition: the new colour is not the subtitle colour').not.toBe(PINK_RGB);

            const lab = await openLab(context);
            await editLightTheme(lab);
            await applyChange(lab, {tab: 'palette', search: source.chipVar, item: `lab-item-var-${source.chipVar}`, layer: 'css-var', target: source.target, to: PINK});

            await expect(subtitle, `${source.className} reads ${source.target}: the app tab follows the Lab`).toHaveCSS('color', PINK_RGB, CROSS_TAB);
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

            await expect(header, `the stylesheets write ${key}, which the DataTable header shows: the app tab follows the Lab`).toHaveCSS('color', BLUE_RGB, CROSS_TAB);
            await expect.poll(() => labActive(page)).toBe(true);
            await expect.poll(async () => (await labStats(page))?.cssRules ?? 0, {message: 'declarations rewritten in the app tab'}).toBeGreaterThan(0);
        });

        test('suspend shows the original colours, resume brings the changes back', async ({page, context}) => {
            const subtitle = transactionsSubtitle(page);
            const source = await colourSourceOf(subtitle, 'text');
            const original = await computedStyle(subtitle);

            const lab = await openLab(context);
            await editLightTheme(lab);
            await applyChange(lab, {tab: 'palette', search: source.chipVar, item: `lab-item-var-${source.chipVar}`, layer: 'css-var', target: source.target, to: PINK});
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

        test('export JSON, reset all, import back: the same changes on the same elements', async ({page, context}, testInfo) => {
            const subtitle = transactionsSubtitle(page);
            const header = dateColumnHeader(page);
            const source = await colourSourceOf(subtitle, 'text');
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
            await applyChange(lab, {tab: 'palette', search: source.chipVar, item: `lab-item-var-${source.chipVar}`, layer: 'css-var', target: source.target, to: PINK});
            await applyChange(lab, {tab: 'sheets', search: key, item: `lab-item-value-css-literal-${key}`, layer: 'css-literal', target: key, to: BLUE});
            await applyChange(lab, {tab: 'charts', search: chartKey, item: `lab-item-value-chart-color-${chartKey}`, layer: 'chart-color', target: chartKey, to: GREEN});
            await expect(subtitle).toHaveCSS('color', PINK_RGB, CROSS_TAB);
            await expect(header).toHaveCSS('color', BLUE_RGB, CROSS_TAB);

            const {text, doc} = await downloadExport(lab);
            expect(doc.schema).toBe('lf-designer-lab/1');
            expect(doc.catalog_hash).toBe(await lab.getByTestId('designer-lab').getAttribute('data-catalog-hash'));
            expect(doc.changes.map((c) => [c.id, c.layer, c.scope, c.target, c.to])).toEqual([
                [`css-var:${source.target}@light`, 'css-var', 'light', source.target, PINK],
                [`css-literal:${key}@light`, 'css-literal', 'light', key, BLUE],
                [`chart-color:${chartKey}@light`, 'chart-color', 'light', chartKey, GREEN],
            ]);
            const [varChange, literalChange, chartChange] = doc.changes;
            expect(varChange.impact?.uses, 'a variable change says how many uses it reaches').toBeGreaterThan(0);
            // Where the stylesheets write the colour is the code's business, and it moves — DataTable's own `th` rule
            // once, a `:root` token since R-3. So the export is held to what an agent does with it: each occurrence is a
            // literal of the changed colour (an alpha variant counts), placed at a file and a line…
            expect(literalChange.occurrences.length, `the export lists where the stylesheets write ${key}`).toBeGreaterThan(0);
            const raws = literalChange.occurrences.map((o) => o.raw ?? '');
            const rawKeys = await opaqueKeysOf(page, raws);
            const placed = (o: {file: string; line: number}) => typeof o.file === 'string' && o.file !== '' && Number.isInteger(o.line) && o.line > 0;
            const strays = literalChange.occurrences.map((o, i) => ({at: `${o.file}:${o.line}`, raw: o.raw, key: rawKeys[i], placed: placed(o)})).filter((o) => !o.placed || o.key !== key);
            expect(strays, `every occurrence has a file, a line and a raw colour that is ${key}, alpha aside`).toEqual([]);
            expect(chartChange.occurrences.length).toBeGreaterThan(0);
            // …and the verifier the Lab ships finds every occurrence the export lists still written in today's code.
            // Not its `catalog_hash_match`: a developer editing `src` during a run changes the hash, not the export.
            const verified = await verifyExport(text, testInfo.outputPath('designer-lab-changes.json'));
            const report = verified.report;
            if (!report) throw new Error(`verify-export.mjs printed no JSON report (exit ${verified.status}): ${verified.stderr}`);
            expect(report.totals.changes, 'the verifier read the three changes').toBe(3);
            expect(
                report.changes.flatMap((c) => c.missing.map((m) => `${c.id} ${m.file}:${m.line} ${m.raw ?? ''}`)),
                'every occurrence the export lists is still written in the code',
            ).toEqual([]);
            expect(report.totals.missing).toBe(0);
            expect(verified.status, `verify-export.mjs exits 0 when nothing is missing: ${verified.stderr}`).toBe(0);
            expect(report.totals.ok, 'positive control: the verifier found occurrences in place').toBeGreaterThan(0);

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
