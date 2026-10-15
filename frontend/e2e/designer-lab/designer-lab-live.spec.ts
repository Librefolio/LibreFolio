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
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {
    applyChange,
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
    transactionsSubtitle,
    transparentMixOf,
    verifyExport,
    waitForLabClient,
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
