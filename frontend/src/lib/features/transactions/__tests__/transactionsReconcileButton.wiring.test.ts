/**
 * N68 wiring (lot X5-3): the Transactions page opens the event-reconciliation modal, read from its source.
 *
 * After a currency change deletes an asset's events, the transactions that were linked to them have no event. The page now
 * has a button among its actions, `data-testid="tx-reconcile-events-button"`, that opens `EventReconciliationModal`
 * (`$lib/features/transactions/EventReconciliationModal.svelte`); when the modal links something (`onlinked`) the page
 * reloads its data, so the rows show the new links. The modal itself is `EventReconciliationModal.test.ts`'s and the whole
 * flow is `e2e/transactions/tx-event-reconciliation.spec.ts`'s.
 *
 * Mounting the page loads a dozen endpoints and stores, so, like `fxDetailRollingReturn.wiring.test.ts` (whose helpers are
 * copied below, the file being its own), the adoption is proven from the source with its comments blanked: a floor, not a
 * proof. The button's behaviour (it really opens the modal) is pinned by the E2E.
 *
 * Expected. Red before the cure: the page imports nothing of the sort, renders no such button and no such modal.
 * Registered in `scripts/test_runner/_frontend_utility.py` (Vitest list of `front_utility_unit`, action `core-unit`).
 */
import {describe, expect, it} from 'vitest';
import {readFileSync} from 'node:fs';

const PAGE = new URL('../../../../routes/(app)/transactions/+page.svelte', import.meta.url);

// ---------------------------------------------------------------------------
// Helpers (own copies of the ones in fxDetailRollingReturn.wiring.test.ts)
// ---------------------------------------------------------------------------

/** A source with its comments blanked, the way the gate blanks them: a name in a comment is no code. `//` after `:` stays (`https://`). */
function withoutComments(source: string): string {
    const blank = (text: string, pattern: RegExp): string => text.replace(pattern, (found) => found.replace(/[^\n]/g, ' '));
    return blank(blank(blank(source, /<!--[\s\S]*?-->/g), /\/\*[\s\S]*?\*\//g), /(?<![:\\])\/\/[^\n]*/g);
}

/**
 * Whether `code` calls `name(` as itself: not a longer name, not a method of something (`other.name(`), but a spread of
 * its result is a call (`...name(`): a single `.` before the name is member access, three are a spread.
 */
const callsFunction = (code: string, name: string): boolean => new RegExp(`(?<![\\w$])(?<!(?<!\\.)\\.)${name}\\s*\\(`).test(code);

/** Every import statement of `code`: whether it is `import type`, its clause (default and/or braces) and its module. */
function importStatements(code: string): Array<{typeOnly: boolean; clause: string; source: string}> {
    return [...code.matchAll(/import\s+(type\s+)?([^;'"]*?)\s*\bfrom\s*['"]([^'"]+)['"]/g)].map(([, typeOnly, clause, source]) => ({typeOnly: Boolean(typeOnly), clause, source}));
}

/** Whether `code` imports `name` as a value from the module `from`: a named specifier (`{name}`, `{name as other}`), not a `type` one. */
function importsNamedValue(code: string, name: string, from: string): boolean {
    return importStatements(code).some(({typeOnly, clause, source}) => {
        if (typeOnly || source !== from) return false;
        const braces = clause.match(/\{([^}]*)\}/)?.[1] ?? '';
        return braces.split(',').some((specifier) => !/^\s*type\s/.test(specifier) && specifier.trim().split(/\s+as\s+/)[0] === name);
    });
}

/** Whether `code` imports the default export of the module `from` under `name` (`import Name from '…'`, `import Name, {type X} from '…'`), not as a type. */
function importsDefault(code: string, name: string, from: string): boolean {
    return importStatements(code).some(({typeOnly, clause, source}) => !typeOnly && source === from && clause.split(/[,{]/)[0].trim() === name);
}

/** The opening tags `<name …>` of `markup`: their attribute text, with `{…}` expressions skipped whole (a `>` inside one does not end the tag). */
function openingTags(markup: string, name: string): string[] {
    const tags: string[] = [];
    const start = new RegExp(`<${name}(?![\\w$.-])`, 'g');
    for (let found = start.exec(markup); found; found = start.exec(markup)) {
        let depth = 0;
        let quote: string | null = null;
        let end = -1;
        for (let index = found.index + found[0].length; index < markup.length; index++) {
            const char = markup[index];
            if (quote) {
                if (char === quote) quote = null;
            } else if (depth > 0) {
                if (char === '{') depth++;
                else if (char === '}') depth--;
            } else if (char === '"' || char === "'") quote = char;
            else if (char === '{') depth++;
            else if (char === '>') {
                end = index;
                break;
            }
        }
        if (end >= 0) tags.push(markup.slice(found.index + found[0].length, end));
    }
    return tags;
}

/** Whether a tag's attribute text sets `idPrefix` to the literal `prefix`: `idPrefix="fx"`, `idPrefix='fx'` or `idPrefix={'fx'}`. */
const setsIdPrefix = (attributes: string, prefix: string): boolean => new RegExp(`(?<![\\w$-])idPrefix\\s*=\\s*(?:"${prefix}"|'${prefix}'|\\{\\s*['"]${prefix}['"]\\s*\\})`).test(attributes);

/** The text between the parentheses of each call `name(…)` in `code`, parentheses matched. */
function callArguments(code: string, name: string): string[] {
    const calls: string[] = [];
    const start = new RegExp(`(?<![\\w$])(?<!(?<!\\.)\\.)${name}\\s*\\(`, 'g');
    for (let found = start.exec(code); found; found = start.exec(code)) {
        let depth = 1;
        for (let index = found.index + found[0].length; index < code.length; index++) {
            if (code[index] === '(') depth++;
            else if (code[index] === ')' && --depth === 0) {
                calls.push(code.slice(found.index + found[0].length, index));
                break;
            }
        }
    }
    return calls;
}

// ---------------------------------------------------------------------------
// The form: what keeps the page from offering the reconciliation
// ---------------------------------------------------------------------------

const MODAL = {name: 'EventReconciliationModal', from: '$lib/features/transactions/EventReconciliationModal.svelte'} as const;
const BUTTON_ID = 'tx-reconcile-events-button';

/** The value of the attribute `name` in a tag's attribute text: the quoted literal, or the `{…}` expression, braces matched; null when absent. */
function attributeValue(attributes: string, name: string): string | null {
    const start = new RegExp(`(?<![\\w$-])${name}\\s*=\\s*`).exec(attributes);
    if (!start) return null;
    const rest = attributes.slice(start.index + start[0].length);
    if (rest[0] === '"' || rest[0] === "'") return rest.slice(1, rest.indexOf(rest[0], 1));
    if (rest[0] !== '{') return null;
    let depth = 0;
    for (let index = 0; index < rest.length; index++) {
        if (rest[index] === '{') depth++;
        else if (rest[index] === '}' && --depth === 0) return rest.slice(1, index);
    }
    return null;
}

/** What keeps the page from the button that opens the modal: the button, its click, and the state the click sets. */
function buttonProblems(source: string): string[] {
    const code = withoutComments(source);
    const problems: string[] = [];
    const buttons = openingTags(code, 'button').filter((attributes) => attributeValue(attributes, 'data-testid') === BUTTON_ID);
    if (buttons.length === 0) problems.push(`no <button data-testid="${BUTTON_ID}"> among the page actions`);
    else if (!buttons.some((attributes) => attributeValue(attributes, 'onclick') !== null)) problems.push(`<button data-testid="${BUTTON_ID}"> has no onclick: it opens nothing`);
    return problems;
}

/** Whether an `onlinked` expression reloads the page data: it calls `reload(`/`loadMainRows(` itself, or is the name of a handler whose body does. */
function reloadsPage(code: string, expression: string): boolean {
    const reloads = (text: string): boolean => callsFunction(text, 'reload') || callsFunction(text, 'loadMainRows');
    if (reloads(expression)) return true;
    const name = /^\s*([A-Za-z_$][\w$]*)\s*$/.exec(expression)?.[1];
    if (!name) return false;
    const definition = new RegExp(`(?:function\\s+${name}\\b|(?:const|let)\\s+${name}\\s*=)`).exec(code);
    return definition ? reloads(code.slice(definition.index, definition.index + 1200)) : false;
}

/** What keeps the page from rendering the modal, opened by its own state, and reloading its data when something is linked. */
function modalProblems(source: string): string[] {
    const code = withoutComments(source);
    const problems: string[] = [];
    if (!importsDefault(code, MODAL.name, MODAL.from)) problems.push(`${MODAL.name} is not imported as a value from ${MODAL.from}`);
    const tags = openingTags(code, MODAL.name);
    if (tags.length === 0) {
        problems.push(`<${MODAL.name} is never rendered`);
        return problems;
    }
    if (!tags.some((attributes) => /(?<![\w$-])(?:bind:)?open\b/.test(attributes))) problems.push(`<${MODAL.name} is rendered without an open state (bind:open or open=…): nothing opens it`);
    const reload = tags.map((attributes) => attributeValue(attributes, 'onlinked')).filter((value): value is string => value !== null);
    if (reload.length === 0) problems.push(`<${MODAL.name} has no onlinked: the rows keep showing the links they had`);
    else if (!reload.some((expression) => reloadsPage(code, expression))) problems.push(`<${MODAL.name} onlinked does not reload the page data (reload( / loadMainRows( is never called in it)`);
    return problems;
}

/** The button and the modal must share ONE state: the name the button's click assigns is the one the modal opens on. */
function sharedStateProblems(source: string): string[] {
    const code = withoutComments(source);
    const button = openingTags(code, 'button').find((attributes) => attributeValue(attributes, 'data-testid') === BUTTON_ID);
    const click = button ? attributeValue(button, 'onclick') : null;
    const modal = openingTags(code, MODAL.name)[0];
    if (!click || !modal) return [];
    const assigned = /(?<![\w$.])([A-Za-z_$][\w$]*)\s*=\s*true\b/.exec(click)?.[1];
    if (!assigned) return []; // the click may call a function that sets it: the E2E proves the opening
    const bound = /(?<![\w$-])(?:bind:)?open\s*=\s*\{\s*([A-Za-z_$][\w$]*)\s*\}/.exec(modal)?.[1];
    return bound === assigned ? [] : [`the button sets ${assigned} but the modal opens on ${bound ?? 'no named state'}`];
}

const listed = (what: string, problems: readonly string[]): string => ['', `The Transactions page ${what} (N68). ${problems.length} finding(s):`, '', ...problems, ''].join('\n  ');

describe('N68 wiring, read from the Transactions page’s source', () => {
    const source = readFileSync(PAGE, 'utf8');

    it('has the reconcile button among its actions, with a click handler', () => {
        const problems = buttonProblems(source);

        expect(problems, listed(`does not offer the reconciliation: add <button data-testid="${BUTTON_ID}" onclick=…> next to the import and add buttons`, problems)).toEqual([]);
    });

    it('renders EventReconciliationModal on a state of its own and reloads the page data when it links something', () => {
        const problems = modalProblems(source);

        expect(problems, listed('does not render the reconciliation modal or does not reload after it: import EventReconciliationModal and render it with bind:open and onlinked={() => … reload(…)}', problems)).toEqual([]);
    });

    it('opens the modal with the state the button sets', () => {
        const problems = sharedStateProblems(source);

        expect(problems, listed('has a button and a modal that do not share their open state', problems)).toEqual([]);
    });

    describe('the form reads what it claims (controls)', () => {
        const WIRED = [
            "import EventReconciliationModal from '$lib/features/transactions/EventReconciliationModal.svelte';",
            'let reconcileOpen = $state(false);',
            '<button class="x" data-testid="tx-reconcile-events-button" onclick={() => (reconcileOpen = true)}>',
            "<EventReconciliationModal bind:open={reconcileOpen} onlinked={() => void pageBusy.track('tx-reload', () => reload({soft: true}))} />",
        ].join('\n');

        it('pass a page that does all of it', () => {
            expect(buttonProblems(WIRED)).toEqual([]);
            expect(modalProblems(WIRED)).toEqual([]);
            expect(sharedStateProblems(WIRED)).toEqual([]);
        });

        it('fail a page without the button, or with a button that has no click', () => {
            expect(buttonProblems(WIRED.replace('data-testid="tx-reconcile-events-button"', 'data-testid="other"'))).toEqual([`no <button data-testid="${BUTTON_ID}"> among the page actions`]);
            expect(buttonProblems(WIRED.replace(' onclick={() => (reconcileOpen = true)}', ''))).toEqual([`<button data-testid="${BUTTON_ID}"> has no onclick: it opens nothing`]);
        });

        it('fail a type-only import, a modal never rendered, one without onlinked and one whose onlinked does not reload', () => {
            expect(modalProblems(WIRED.replace('import EventReconciliationModal', 'import type EventReconciliationModal'))).toEqual([`${MODAL.name} is not imported as a value from ${MODAL.from}`]);
            expect(
                modalProblems(
                    WIRED.split('\n')
                        .filter((line) => !line.startsWith('<EventReconciliationModal'))
                        .join('\n'),
                ),
            ).toEqual([`<${MODAL.name} is never rendered`]);
            expect(modalProblems(WIRED.replace(/ onlinked=\{.*\} \/>/, ' />'))).toEqual([`<${MODAL.name} has no onlinked: the rows keep showing the links they had`]);
            expect(modalProblems(WIRED.replace(/onlinked=\{.*\} \/>/, 'onlinked={() => console.log(1)} />'))).toEqual([`<${MODAL.name} onlinked does not reload the page data (reload( / loadMainRows( is never called in it)`]);
        });

        it('accept an onlinked that names a handler whose body reloads, and fail one whose body does not', () => {
            const named = WIRED.replace(/onlinked=\{.*\} \/>/, 'onlinked={onEventsLinked} />');
            expect(modalProblems(`${named}\nasync function onEventsLinked() {\n  await reload({soft: true});\n}`)).toEqual([]);
            expect(modalProblems(`${named}\nasync function onEventsLinked() {\n  toasts.info('x');\n}`)).toEqual([`<${MODAL.name} onlinked does not reload the page data (reload( / loadMainRows( is never called in it)`]);
        });

        it('fail a button and a modal on two different states', () => {
            expect(sharedStateProblems(WIRED.replace('bind:open={reconcileOpen}', 'bind:open={otherOpen}'))).toEqual(['the button sets reconcileOpen but the modal opens on otherOpen']);
        });

        it('ignore a name that only a comment holds', () => {
            const commented = WIRED.replace('<EventReconciliationModal', '<!-- <EventReconciliationModal --> <div').replace('<button class="x" data-testid="tx-reconcile-events-button"', '<!-- <button data-testid="tx-reconcile-events-button" --> <button class="y"');
            expect(buttonProblems(commented)).toEqual([`no <button data-testid="${BUTTON_ID}"> among the page actions`]);
        });
    });
});
