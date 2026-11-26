/**
 * «Copy cell» and «Copy row» of a table's row menu (85 BTN-0, the developer's choice of 24/11/2026): what a finger
 * copies instead of selecting text, since a long press on a row opens the menu and never the selection handles.
 *
 * The text is exactly what the screen shows, read from the DOM and never from the data: a value the privacy mode
 * masks (`€•••`) stays masked, a formatted number keeps its format (the privacy mode masks in the text, never with CSS
 * alone). A text the screen does not show is left out — an element hidden by CSS (a word hidden below a breakpoint), a
 * screen-reader-only text (`.sr-only`), an `aria-hidden` subtree. A field gives its value (a select its chosen option);
 * a password never. Whitespace collapses to one space, so a cell never breaks the tab-separated row it is part of.
 */

const NOT_ON_SCREEN = '.sr-only, [aria-hidden="true"]';

/** The inputs whose value is text the screen shows. A password is never copied, a checkbox or a range has no text. */
const TEXT_INPUT_TYPES = new Set(['', 'text', 'number', 'search', 'email', 'url', 'tel', 'date', 'time', 'datetime-local', 'month', 'week']);

function shownOnScreen(element: Element): boolean {
    if (element.matches(NOT_ON_SCREEN)) return false;
    // `checkVisibility` is the browser's own answer (display, content-visibility, visibility); jsdom has none.
    if (typeof element.checkVisibility === 'function') return element.checkVisibility({visibilityProperty: true});
    return true;
}

/** A field shows its value, not its markup: an input its text, a select its chosen option, never the other options. */
function fieldText(element: Element): string | null {
    if (element instanceof HTMLInputElement) return TEXT_INPUT_TYPES.has(element.type) ? element.value : '';
    if (element instanceof HTMLTextAreaElement) return element.value;
    if (element instanceof HTMLSelectElement) {
        return Array.from(element.selectedOptions)
            .map((option) => option.text)
            .join(' ');
    }
    return null;
}

function collect(node: Node, parts: string[]): void {
    for (const child of Array.from(node.childNodes)) {
        if (child.nodeType === Node.TEXT_NODE) {
            parts.push(child.textContent ?? '');
            continue;
        }
        if (!(child instanceof Element) || !shownOnScreen(child)) continue;
        const field = fieldText(child);
        if (field !== null) {
            parts.push(` ${field} `);
            continue;
        }
        collect(child, parts);
    }
}

/** The text of `cell` as it reads on screen, on one line. */
export function cellScreenText(cell: Element): string {
    const parts: string[] = [];
    collect(cell, parts);
    return parts.join('').replace(/\s+/g, ' ').trim();
}

/** The data cells of `row` as they read on screen, separated by tabs: a paste into a spreadsheet fills one row. */
export function rowScreenText(row: Element, dataCellSelector = 'td.td-data'): string {
    return Array.from(row.querySelectorAll(dataCellSelector))
        .map((cell) => cellScreenText(cell))
        .join('\t');
}
