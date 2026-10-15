/**
 * Designer Lab — the element picker: point at an element of the app, read where its colours come from, specialise one.
 *
 * The Lab asks for a pick through localStorage (`lf-designer-lab/pick`); the app tab lays a transparent veil over the
 * page (`lf-lab-pick-veil`), and the click on an element is answered with its colours and the declarations proved to
 * set them. The Lab lists them in its «Element» tab, each with the kind of its source (`data-kind`), and «Specialise
 * here» writes an `element` change: a rule in the cascade layer `lf-designer-lab`, scoped by a selector built from the
 * nearest test id and the element's place below it — every instance of that component element changes, nothing else.
 * Its export carries an anchor (route, test ids, selector, matches, candidate places in the code) and never any text
 * of the page. Esc cancels a pick; Alt+Shift+D starts one from an app tab, but only in a browser where the Lab has
 * been opened (the neutral spec proves the converse).
 *
 * The elements are the app's own and exist whatever the data: the date header of the transactions table, which
 * DataTable styles, and the subtitle of the transactions page (a Tailwind text colour, overridden by `app.css` in the
 * dark theme). Where to click is computed at run time: a point of the element where the element itself is on top.
 *
 * How DataTable writes the header colour — a literal in its `th` rule, a `:root` token that rule reads (R-3), a role
 * utility — is not this spec's subject, and it moves. The date-header test reads it from the facts the app tab reported
 * (`picker/describe.ts`), applies the documented classification rules to the proved winner, and holds the Lab's
 * «Element» tab (`pickView.ts`) and its export to them: two modules checked against each other, whatever the code says
 * today.
 *
 * Nothing is written server-side: TEST_USER only reads, the theme toggle and the Lab keep their state in this
 * context's localStorage, and the context dies with the test.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {
    chooseTheme,
    computedStyle,
    CROSS_TAB,
    dateColumnHeader,
    DESKTOP_ONLY,
    downloadExport,
    expectChanges,
    labPicking,
    labStats,
    openLab,
    openTransactions,
    pickedFacts,
    pickedProperty,
    pickVeil,
    pointOnItself,
    textPaletteClassOf,
    transactionsSubtitle,
    waitForLabClient,
    type PickedDeclarationFacts,
} from './lab-helpers';

test.setTimeout(60_000);

/** A colour no element of the app uses, so the effect of a specialisation cannot be mistaken for the app's own. */
const FRESH = '#ff00aa';
const FRESH_RGB = 'rgb(255, 0, 170)';
const SOURCE_KINDS = ['var', 'tailwind-class', 'rule-literal', 'inline', 'attribute', 'current-color', 'chart', 'unknown'];
/** The component that renders the transactions table and styles its header cells. */
const DATA_TABLE = 'lib/components/table/DataTable.svelte';
/** The candidates that bind a colour where the code sets it; a `testid` candidate only says where the component is. */
const BINDING_CANDIDATES = ['matched-rule', 'class-use', 'var-use'];

/** The variable a declared value reads first (`var(--x, #fff)` → `--x`), or null when it reads none. */
function varReadBy(value: string): string | null {
    return /var\(\s*(--[\w-]+)/.exec(value)?.[1] ?? null;
}

/**
 * The source kind of a winning stylesheet rule by the rules the developer page documents («Source kinds», `classify()`),
 * applied here on the app tab's facts, independently of `pickView.ts`: a rule in Tailwind's cascade layer `utilities` —
 * or a dotted layer name ending in it — is a `tailwind-class`; any other rule is a `var` when its value reads a
 * variable, a `rule-literal` when it writes the colour.
 */
function kindOfRule(winner: PickedDeclarationFacts): 'tailwind-class' | 'var' | 'rule-literal' {
    if (winner.layer !== null && /(^|\.)utilities$/.test(winner.layer)) return 'tailwind-class';
    return varReadBy(winner.value) ? 'var' : 'rule-literal';
}

/** How many elements of the app tab `selector` takes. */
async function countIn(page: Page, selector: string): Promise<number> {
    return page.evaluate((sel) => document.querySelectorAll(sel).length, selector);
}

/**
 * The elements of the page that show `colour`, split by whether `selector` reaches them — the element itself or one
 * of its ancestors, since a text colour is inherited. `outside` names each stray element by tag and nearest test id.
 */
async function colourCensus(page: Page, selector: string, colour: string): Promise<{targets: number; targetsWith: number; outside: string[]}> {
    return page.evaluate(
        ({sel, value}) => {
            const targets = Array.from(document.querySelectorAll(sel));
            const reached = (el: Element) => targets.some((target) => target.contains(el));
            const name = (el: Element) => `${el.tagName.toLowerCase()} in ${el.closest('[data-testid]')?.getAttribute('data-testid') ?? 'body'}`;
            return {
                targets: targets.length,
                targetsWith: targets.filter((target) => getComputedStyle(target).color === value).length,
                outside: Array.from(document.body.querySelectorAll('*'))
                    .filter((el) => !reached(el) && getComputedStyle(el).color === value)
                    .map(name),
            };
        },
        {sel: selector, value: colour},
    );
}

test.describe('Designer Lab — the element picker', () => {
    test.beforeEach(async ({}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', DESKTOP_ONLY);
    });

    test('a pick from the Lab lists the sources; «Specialise here» changes one component element only; the export is anchored and carries no page text', async ({page, context}) => {
        await login(page, TEST_USER);
        await openTransactions(page);
        await chooseTheme(page, 'light');
        const header = dateColumnHeader(page);
        await expect(header).toBeVisible();
        const original = await computedStyle(header);
        const lab = await openLab(context);

        // The Lab asks; the app tab lays its veil; the click lands on the header cell itself.
        const point = await pointOnItself(header);
        await lab.getByTestId('lab-pick').click();
        await expect(lab.getByTestId('lab-pick-cancel')).toBeVisible();
        await expect(pickVeil(page)).toBeVisible(CROSS_TAB);
        expect(await labPicking(page)).toBe(true);
        await page.mouse.click(point.x, point.y);

        const picked = lab.getByTestId('lab-picked');
        await expect(picked, 'the app tab answers with the element').toBeVisible({timeout: 15_000});
        await expect(picked).toHaveAttribute('data-route', '/transactions');
        await expect(picked).toHaveAttribute('data-theme', 'light');
        await expect(lab.getByTestId('lab-tab-element')).toHaveAttribute('aria-current', 'true');
        await expect(lab.getByTestId('lab-pick'), 'the pick is over in the Lab').toBeVisible();
        await expect(pickVeil(page), 'and in the app tab').toHaveCount(0);
        expect(await labPicking(page)).toBe(false);
        // Where it is, said with test ids: the column header's own (a templated id) first, then the table's.
        await expect(lab.getByTestId('lab-picked-testids')).toContainText('dt-header-');
        await expect(lab.getByTestId('lab-picked-testids')).toContainText('tx-table');
        const ownSelector = ((await lab.getByTestId('lab-picked-selector').textContent()) ?? '').trim();
        await expect(lab.getByTestId('lab-picked-matches'), 'the element selector takes what the app tab counted').toHaveAttribute('data-matches', String(await countIn(page, ownSelector)));

        // Every colour listed says where it comes from.
        const kinds = await lab.getByTestId('lab-picked-property').evaluateAll((items) => items.map((item) => item.getAttribute('data-kind')));
        expect(kinds.length, 'the Element tab lists the colours of the element').toBeGreaterThan(0);
        for (const kind of kinds) expect(SOURCE_KINDS).toContain(kind);
        // The text colour: what the app tab proved sets it, read from its facts, and the kind the rules give for that
        // winner. The Element tab must agree — and when the winner reads a variable, its chain starts there.
        const facts = await pickedFacts(page);
        expect(facts, 'the facts in the pick channel are those of this pick').toMatchObject({route: '/transactions', theme: 'light'});
        const winner = facts.properties.find((p) => p.property === 'color')?.declarations.find((d) => d.wins);
        if (!winner) throw new Error(`the app tab must prove the declaration that sets the header's text colour: no \`color\` winner among its facts (${facts.properties.map((p) => p.property).join(', ')})`);
        expect(winner.origin, 'the header text colour is set by a stylesheet rule: the component, a token it reads, or a utility on the cell').toBe('rule');
        const sourceKind = kindOfRule(winner);
        const readVar = varReadBy(winner.value);
        const colour = pickedProperty(lab, 'color');
        await expect(colour, `the Element tab classifies \`${winner.selector} { color: ${winner.value} }\` (layer ${winner.layer ?? 'none'}) as the rules do`).toHaveAttribute('data-kind', sourceKind);
        const shownKind = await colour.getAttribute('data-kind');
        if (readVar) await expect(colour.getByTestId('lab-picked-var').first(), 'the variable chain starts with the variable the winner reads').toHaveText(readVar);
        else await expect(colour.getByTestId('lab-picked-var'), 'a winner that reads no variable has no variable chain').toHaveCount(0);

        // «Specialise here»: the component selector, and how many elements of the app tab it takes.
        const selector = ((await colour.getByTestId('lab-picked-specialise-selector').textContent()) ?? '').trim();
        expect(selector, 'a component selector starts at the nearest test id').toMatch(/^\[data-testid/);
        const matches = await countIn(page, selector);
        expect(matches).toBeGreaterThan(0);
        await expect(colour.getByTestId('lab-picked-specialise-matches')).toHaveAttribute('data-matches', String(matches));

        const fresh = await colourCensus(page, selector, FRESH_RGB);
        expect(fresh.targetsWith + fresh.outside.length, 'precondition: nothing on the page shows the new colour yet').toBe(0);
        // The control set: elements outside the component element that show the same colour now.
        const control = await page.evaluateHandle(
            ({sel, value}) => {
                const targets = Array.from(document.querySelectorAll(sel));
                return Array.from(document.body.querySelectorAll('*')).filter((el) => !targets.some((target) => target.contains(el)) && getComputedStyle(el).color === value);
            },
            {sel: selector, value: original},
        );
        expect(await control.evaluate((els) => els.length), `precondition: elements outside the component element show ${original} too, so that a specialisation travelling with the colour would show — on the transactions page of TEST_USER's populate_mock_data rows`).toBeGreaterThan(0);

        await colour.getByTestId('lab-picked-specialise').click();
        const editor = lab.getByTestId('lab-editor');
        await expect(editor).toHaveAttribute('data-layer', 'element');
        await expect(editor).toHaveAttribute('data-property', 'color');
        await expect(editor).toHaveAttribute('data-target', selector);
        await expect(lab.getByTestId('lab-editor-matches'), 'the editor counts the elements it changes').toHaveAttribute('data-matches', String(matches));
        await lab.getByTestId('lab-editor-to').fill(FRESH);
        await expect(lab.getByTestId('lab-editor-to')).toHaveValue(FRESH);
        await lab.getByTestId('lab-editor-apply').click();
        await expectChanges(lab, 1);

        // Every element the selector takes changes, and nothing outside it.
        await expect.poll(async () => (await labStats(page))?.elementRules ?? 0, {...CROSS_TAB, message: 'the specialisation reaches the app tab'}).toBe(1);
        await expect.poll(async () => (await colourCensus(page, selector, FRESH_RGB)).targetsWith, {...CROSS_TAB, message: 'every element of the component takes the new colour'}).toBe(matches);
        const after = await colourCensus(page, selector, FRESH_RGB);
        expect(after.targets).toBe(matches);
        expect(after.outside, 'the specialisation reaches nothing outside its component element').toEqual([]);
        const controlAfter = await control.evaluate((els) => els.filter((el) => el.isConnected).map((el) => getComputedStyle(el).color));
        expect(controlAfter.length, 'the control elements are still on the page').toBeGreaterThan(0);
        expect([...new Set(controlAfter)], `every control element still shows ${original}`).toEqual([original]);
        await control.dispose();

        // The export: one `element` change with its anchor, and no text of the page.
        const {text, doc} = await downloadExport(lab);
        expect(doc.schema).toBe('lf-designer-lab/1');
        expect(doc.changes).toHaveLength(1);
        const [change] = doc.changes;
        expect(change).toMatchObject({id: `element:color@light~${selector}`, layer: 'element', scope: 'light', property: 'color', target: selector, from: original, to: FRESH});
        const anchor = change.anchor;
        if (!anchor) throw new Error('an element change must carry its anchor');
        expect(anchor).toMatchObject({route: '/transactions', theme: 'light', selector, breadth: 'component', matches, property: 'color', computed: original});
        expect(anchor.testids[0], 'the nearest test id first, as the code writes it').toMatch(/^dt-header-/);
        expect(anchor.testids).toContain('tx-table');
        // The source the export names is the one the Element tab showed, and the winner the app tab proved.
        expect(anchor.source, 'the anchor names the source the Element tab showed: its kind, the winning rule, the variable it reads').toMatchObject({kind: shownKind, selector: winner.selector, var: readVar});
        const where = anchor.candidates.map((c) => `${c.file}:${c.line} ${c.why}`).join(', ');
        expect(
            anchor.candidates.some((c) => BINDING_CANDIDATES.includes(c.why) && c.file.endsWith(DATA_TABLE)),
            `DataTable styles its header whatever the kind: a place in ${DATA_TABLE} that binds the colour (${BINDING_CANDIDATES.join(', ')}) is a candidate — test-id places do not count. Candidates: ${where}`,
        ).toBe(true);
        expect(change.occurrences).toEqual(anchor.candidates.map((c) => ({file: c.file, line: c.line, raw: c.needle, why: c.why})));
        const texts = await page.getByTestId('tx-table').evaluate((table) => [
            ...new Set(
                Array.from(table.querySelectorAll('th, td'))
                    .map((cell) => (cell.textContent ?? '').replace(/\s+/g, ' ').trim())
                    .filter((t) => t.length >= 6 && /\p{L}/u.test(t)),
            ),
        ]);
        expect(texts.length, 'the table shows labels and cells to look for').toBeGreaterThan(0);
        expect(
            texts.filter((t) => text.includes(t)),
            'the export carries no text of the page',
        ).toEqual([]);
    });

    test('Esc cancels a pick; Alt+Shift+D starts one in an app tab that was open when the Lab was opened', async ({page, context}) => {
        await login(page, TEST_USER);
        await openTransactions(page);
        await chooseTheme(page, 'light');
        const lab = await openLab(context);

        await lab.getByTestId('lab-pick').click();
        await expect(pickVeil(page)).toBeVisible(CROSS_TAB);
        await page.keyboard.press('Escape');
        await expect(lab.getByTestId('lab-pick'), 'the Lab hears the cancel').toBeVisible(CROSS_TAB);
        await expect(lab.getByTestId('lab-pick-cancel')).toHaveCount(0);
        await expect(lab.getByTestId('lab-status')).toHaveAttribute('data-kind', 'warn');
        await expect(pickVeil(page)).toHaveCount(0);
        expect(await labPicking(page)).toBe(false);

        // The app tab learnt that the Lab was opened from the `storage` event, which arrived before the pick request it
        // has just answered: its shortcut is installed.
        const subtitle = transactionsSubtitle(page);
        const {className, variable} = await textPaletteClassOf(subtitle);
        const point = await pointOnItself(subtitle);
        await page.keyboard.press('Alt+Shift+KeyD');
        await expect(pickVeil(page)).toBeVisible(CROSS_TAB);
        expect(await labPicking(page)).toBe(true);
        await page.mouse.click(point.x, point.y);

        const picked = lab.getByTestId('lab-picked');
        await expect(picked, 'a pick started in the app tab reaches the Lab').toBeVisible({timeout: 15_000});
        await expect(picked).toHaveAttribute('data-theme', 'light');
        await expect(pickVeil(page)).toHaveCount(0);
        const colour = pickedProperty(lab, 'color');
        await expect(colour, `${className} is a Tailwind utility`).toHaveAttribute('data-kind', 'tailwind-class');
        await expect(colour.getByTestId('lab-picked-class')).toHaveText(className);
        await expect(colour.getByTestId('lab-picked-var').first(), 'the variable the utility reads comes first').toHaveText(variable);
        await expect(colour.getByTestId('lab-picked-dark-override')).toHaveCount(0);
        await expect(colour.getByTestId('lab-picked-specialise-selector'), 'a specialisation keeps the class its rule names').toContainText(`p.${className}`);
    });

    test('a dark-theme pick of a text-gray-500 element shows the variable of the app.css override', async ({page, context}) => {
        // The Lab first: the app tab then loads in a browser that has seen the Lab, and installs the shortcut as it starts.
        const lab = await openLab(context);
        await login(page, TEST_USER);
        await openTransactions(page);
        await waitForLabClient(page);
        await chooseTheme(page, 'dark');
        const subtitle = transactionsSubtitle(page);
        await expect(subtitle, 'precondition: the subtitle is a text-gray-500 element, which app.css overrides in the dark theme').toHaveClass(/(^|\s)text-gray-500(\s|$)/);

        const point = await pointOnItself(subtitle);
        await page.keyboard.press('Alt+Shift+KeyD');
        await expect(pickVeil(page)).toBeVisible(CROSS_TAB);
        await page.mouse.click(point.x, point.y);

        const picked = lab.getByTestId('lab-picked');
        await expect(picked, 'the element was picked in the dark theme').toHaveAttribute('data-theme', 'dark', {timeout: 15_000});
        await expect(lab.getByTestId('lab-scope'), 'the Lab edits the theme the element was picked in').toHaveValue('dark');
        const colour = pickedProperty(lab, 'color');
        await expect(colour, 'the !important override of app.css wins over the utility, and reads a variable').toHaveAttribute('data-kind', 'var');
        await expect(colour.getByTestId('lab-picked-dark-override')).toBeVisible();
        await expect(colour.getByTestId('lab-picked-var').first()).toHaveText(/^--[\w-]+$/);
    });
});
