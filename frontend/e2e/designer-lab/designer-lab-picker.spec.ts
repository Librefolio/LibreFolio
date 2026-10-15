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
 * DataTable styles, the subtitle of the transactions page (a Tailwind text colour, overridden by `app.css` in the
 * dark theme), and the login card a visitor who is not logged in gets at `/`, whose background is a colour-role utility
 * of workstream T (`bg-lf-*`, read from its classes and the page's CSSOM by `colourSourceOf`). Where to click is
 * computed at run time: a point of the element where the element itself is on top.
 *
 * How DataTable writes the header colour — a literal in its `th` rule, a `:root` token that rule reads (R-3), a role
 * utility — is not this spec's subject, and it moves. The date-header test reads it from the facts the app tab reported
 * (`picker/describe.ts`), applies the documented classification rules to the proved winner, and holds the Lab's
 * «Element» tab (`pickView.ts`) and its export to them: two modules checked against each other, whatever the code says
 * today. The login-card test holds them to a role: the winner is the utility's rule, which reads the role; «Edit the
 * source» edits the role, not the alias no stylesheet defines; and the anchor finds the class in the card's component.
 *
 * Nothing is written server-side: TEST_USER only reads, the visitor never signs in, the theme toggle and the Lab keep
 * their state in this context's localStorage, and the context dies with the test.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {
    chooseTheme,
    colourSourceOf,
    computedStyle,
    CROSS_TAB,
    dateColumnHeader,
    DESKTOP_ONLY,
    downloadExport,
    expectChanges,
    IDLE_STATS,
    labActive,
    labPicking,
    labStats,
    LOGIN_CARD,
    newColourFor,
    openLab,
    openSignIn,
    openTransactions,
    pickedFacts,
    pickedProperty,
    pickVeil,
    placesInComponent,
    pointOnItself,
    sourceLines,
    transactionsSubtitle,
    verifyExport,
    waitForLabClient,
    type PickedDeclarationFacts,
} from './lab-helpers';

test.setTimeout(60_000);

/** A colour no element of the app uses, so the effect of a specialisation cannot be mistaken for the app's own. */
const FRESH = '#ff00aa';
const FRESH_RGB = 'rgb(255, 0, 170)';
/** The new colours a colour-role test may apply, in order: the first the role has in neither theme. */
const NEW_COLOURS = [
    {hex: FRESH, rgb: FRESH_RGB},
    {hex: '#00aaff', rgb: 'rgb(0, 170, 255)'},
];
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

    test('a colour-role utility: the pick reads the role, «Edit the source» edits it, the filter shows its chip, the anchor finds the class in its component', async ({page, context}, testInfo) => {
        const card = await openSignIn(page);
        await waitForLabClient(page);
        await chooseTheme(page, 'light');
        // The card's background class and the role its rule reads in the page's CSSOM: what the picker must find.
        const source = await colourSourceOf(card, 'bg');
        expect(source.role, `${source.className} must be a colour-role utility: the login card reads the roles of workstream T`).toBe(true);
        expect(source.target, `${source.className} reads a role`).toMatch(/^--lf-/);
        const original = await computedStyle(card, 'background-color');
        // A colour the role has in neither theme, read from the page: T changes the values of the roles.
        const fresh = await newColourFor(page, source.target, NEW_COLOURS, [original]);
        const lab = await openLab(context);

        // The Lab asks; the app tab lays its veil; the click lands on the card itself — its border, around its children.
        const point = await pointOnItself(card);
        await lab.getByTestId('lab-pick').click();
        await expect(lab.getByTestId('lab-pick-cancel')).toBeVisible();
        await expect(pickVeil(page)).toBeVisible(CROSS_TAB);
        await page.mouse.click(point.x, point.y);

        const picked = lab.getByTestId('lab-picked');
        await expect(picked, 'the app tab answers with the element').toBeVisible({timeout: 15_000});
        await expect(picked).toHaveAttribute('data-route', '/');
        await expect(picked).toHaveAttribute('data-theme', 'light');
        await expect(lab.getByTestId('lab-scope'), 'the Lab edits the theme the element was picked in').toHaveValue('light');
        await expect(pickVeil(page), 'the pick is over in the app tab').toHaveCount(0);

        // What the app tab proved: the card's own background, set by the utility's rule, which reads the role.
        const facts = await pickedFacts(page);
        expect(facts, 'the facts in the pick channel are those of this pick').toMatchObject({route: '/', theme: 'light'});
        expect(facts.testids[0], "the nearest test id is the card's own").toBe(LOGIN_CARD);
        const background = facts.properties.find((p) => p.property === 'background-color');
        if (!background) throw new Error(`the app tab must report the card's background: no \`background-color\` among its facts (${facts.properties.map((p) => p.property).join(', ')})`);
        expect(background.depth, 'the pick landed on the card itself: the background is its own, not one seen through').toBe(0);
        const winner = background.declarations.find((d) => d.wins);
        if (!winner) throw new Error(`the app tab must prove the declaration that sets the card's background: no winner among ${background.declarations.map((d) => d.selector ?? d.origin).join(', ') || 'no candidate'}`);
        expect(winner, `the rule of ${source.className} the page's CSSOM holds sets the card's background`).toMatchObject({origin: 'rule', selector: source.selector});
        expect(varReadBy(winner.value), `${winner.selector} { background-color: ${winner.value} } reads the role`).toBe(source.target);
        const kind = kindOfRule(winner);
        expect(kind, `${winner.selector} is in the layer ${winner.layer ?? 'none'}: a Tailwind utility`).toBe('tailwind-class');
        const colour = pickedProperty(lab, 'background-color');
        await expect(colour, `the Element tab classifies \`${winner.selector} { background-color: ${winner.value} }\` (layer ${winner.layer ?? 'none'}) as the rules do`).toHaveAttribute('data-kind', kind);
        await expect(colour.getByTestId('lab-picked-class')).toHaveText(source.className);
        await expect(colour.getByTestId('lab-picked-var').first(), 'the chain starts at the role the utility reads, not at its alias').toHaveText(source.target);

        // The «picked» filter keeps the card's colours: fewer chips, the role's among them, under its alias.
        await lab.getByTestId('lab-tab-palette').click();
        const search = lab.getByTestId('lab-search');
        await search.fill('');
        await expect(search).toHaveValue('');
        const chips = lab.locator('[data-testid^="lab-item-var-"]');
        await expect(chips, 'the palette tab lists the catalogue').not.toHaveCount(0);
        const unfiltered = await chips.count();
        const filter = lab.getByTestId('lab-filter-picked');
        await filter.check();
        await expect(filter).toBeChecked();
        await expect.poll(() => chips.count(), {message: "the filter keeps only the picked element's colours"}).toBeLessThan(unfiltered);
        const chip = lab.getByTestId(`lab-item-var-${source.chipVar}`);
        await expect(chip, `the filter shows the chip of ${source.className}, under its alias ${source.chipVar}`).toBeVisible();
        await expect(chip, 'the chip edits the role').toHaveAttribute('data-target', source.target);

        // «Edit the source» edits the role — the alias has no rule at runtime — with the pick as the change's anchor.
        await lab.getByTestId('lab-tab-element').click();
        await colour.getByTestId('lab-picked-edit').click();
        const editor = lab.getByTestId('lab-editor');
        await expect(editor).toHaveAttribute('data-layer', 'css-var');
        await expect(editor).toHaveAttribute('data-target', source.target);
        await lab.getByTestId('lab-editor-to').fill(fresh.hex);
        await expect(lab.getByTestId('lab-editor-to')).toHaveValue(fresh.hex);
        await lab.getByTestId('lab-editor-apply').click();
        await expectChanges(lab, 1);
        await expect(card, `${source.target} changes, and the card with it`).toHaveCSS('background-color', fresh.rgb, CROSS_TAB);
        await expect.poll(() => labStats(page)).toMatchObject({varOverrides: 1, elementRules: 0});

        // The export: the role, anchored on the card, with the class where the code writes it.
        const {text, doc} = await downloadExport(lab);
        expect(doc.schema).toBe('lf-designer-lab/1');
        expect(doc.changes.map((c) => [c.id, c.layer, c.scope, c.target, c.to])).toEqual([[`css-var:${source.target}@light`, 'css-var', 'light', source.target, fresh.hex]]);
        const [change] = doc.changes;
        const anchor = change.anchor;
        if (!anchor) throw new Error('a change opened from the Element tab must carry its anchor');
        expect(anchor).toMatchObject({route: '/', theme: 'light', property: 'background-color', computed: original});
        expect(anchor.testids[0], 'the nearest test id first, as the code writes it').toBe(LOGIN_CARD);
        expect(anchor.source, 'the anchor names the source the Element tab showed: the utility, its rule, the role').toMatchObject({kind, selector: winner.selector, var: source.target, class: source.className});
        const where = anchor.candidates.map((c) => `${c.file}:${c.line} ${c.why} ${c.needle}`).join(', ');
        const classUses = anchor.candidates.filter((c) => c.why === 'class-use' && c.needle === source.className);
        expect(classUses.length, `the uses of ${source.className} are found through the role: a class-use candidate. Candidates: ${where}`).toBeGreaterThan(0);
        // Each is a line of today's code that writes the class, read from disk; one is in the card's component.
        for (const c of classUses) {
            const lines = await sourceLines(c.file);
            expect(lines, `${c.file} exists in the repository`).not.toBeNull();
            expect(lines?.[c.line - 1] ?? '', `${c.file}:${c.line} writes ${source.className}`).toContain(source.className);
        }
        const inCard = await placesInComponent(classUses, source.className, LOGIN_CARD);
        expect(inCard.length, `a class-use candidate in the component that writes ${LOGIN_CARD}. Candidates: ${where}`).toBeGreaterThan(0);
        const verified = await verifyExport(text, testInfo.outputPath('designer-lab-changes.json'));
        const report = verified.report;
        if (!report) throw new Error(`verify-export.mjs printed no JSON report (exit ${verified.status}): ${verified.stderr}`);
        expect(
            report.changes.flatMap((c) => c.missing.map((m) => `${c.id} ${m.file}:${m.line} ${m.raw ?? ''}`)),
            'every occurrence the export lists is still written in the code',
        ).toEqual([]);
        expect(verified.status, `verify-export.mjs exits 0 when nothing is missing: ${verified.stderr}`).toBe(0);
        expect(report.totals.ok, 'positive control: the verifier found occurrences in place').toBeGreaterThan(0);
        // No text of the page: the card's phrases — words of the interface, never a token of the code — appear nowhere.
        const phrases = await card.evaluate((root) => [
            ...new Set(
                Array.from(root.querySelectorAll('*'))
                    .map((el) =>
                        Array.from(el.childNodes)
                            .filter((node) => node.nodeType === Node.TEXT_NODE)
                            .map((node) => node.textContent ?? '')
                            .join(' ')
                            .replace(/\s+/g, ' ')
                            .trim(),
                    )
                    .filter((t) => /\p{L}/u.test(t) && t.includes(' ')),
            ),
        ]);
        expect(phrases.length, 'the card shows phrases to look for').toBeGreaterThan(0);
        expect(
            phrases.filter((t) => text.includes(t)),
            'the export carries no text of the page',
        ).toEqual([]);

        await lab.getByTestId('lab-reset-all').click();
        await expectChanges(lab, 0);
        await expect(card, 'reset: the card shows its own background again').toHaveCSS('background-color', original, CROSS_TAB);
        await expect.poll(() => labActive(page), CROSS_TAB).toBe(false);
        await expect.poll(() => labStats(page)).toEqual(IDLE_STATS);
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
        const source = await colourSourceOf(subtitle, 'text');
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
        await expect(colour, `${source.className} is a Tailwind utility`).toHaveAttribute('data-kind', 'tailwind-class');
        await expect(colour.getByTestId('lab-picked-class')).toHaveText(source.className);
        await expect(colour.getByTestId('lab-picked-var').first(), 'the variable the utility reads comes first').toHaveText(source.target);
        await expect(colour.getByTestId('lab-picked-dark-override')).toHaveCount(0);
        await expect(colour.getByTestId('lab-picked-specialise-selector'), 'a specialisation keeps the class its rule names').toContainText(`p.${source.className}`);
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
