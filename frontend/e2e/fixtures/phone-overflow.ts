/**
 * The sideways-overflow measure of a phone page or window (81 U22), shared by `layout/phone-no-hscroll.spec.ts` and the
 * gallery's phone shots, so the two read one criterion.
 *
 * Criterion. Page: how far `documentElement.scrollWidth` goes past `clientWidth`. A window (`scope` = the selector of its
 * panel, `.modal-content`): how far the panel ends past the viewport, or its content past its own width. In both, the
 * boxes that end past the edge are listed — outermost first, a child of an offender is not repeated — except those inside
 * a container that scrolls or clips by design (`overflow-x: auto | scroll | hidden | clip`: the `.table-wrapper` of a
 * DataTable, a chip row, a code block), anything `position: fixed` (popups, tooltips, toasts) and boxes with no size.
 * The rule is the CSS property, not a list of names.
 */
import {appendFileSync, mkdirSync} from 'node:fs';
import {dirname} from 'node:path';
import type {Page} from '@playwright/test';

export interface SidewaysOverflow {
    /** The width of the screen the measure was taken on. */
    viewport: number;
    /** The worst overflow, in pixels: the page's, the window's, or the farthest box's. 0 = fits. */
    over: number;
    /** The outermost boxes past the edge, widest overflow first (at most 8). */
    offenders: Array<{name: string; over: number}>;
}

/** Measure the page, or — with `scope` — the first element matching it (a window's panel). */
export async function measureSidewaysOverflow(page: Page, scope?: string): Promise<SidewaysOverflow> {
    return page.evaluate((scopeSelector) => {
        const viewport = document.documentElement.clientWidth;
        const root: Element = scopeSelector ? (document.querySelector(scopeSelector) ?? document.body) : document.body;
        const rootRect = root.getBoundingClientRect();
        // The edge the boxes are compared with: the screen for a page, the panel's own right edge for a window.
        const limit = scopeSelector ? Math.min(rootRect.right, viewport) : viewport;
        const clips = (style: CSSStyleDeclaration) => ['auto', 'scroll', 'hidden', 'clip'].includes(style.overflowX);
        const nameOf = (el: Element) => {
            const id = el.getAttribute('data-testid');
            if (id) return id;
            const cls = (el.getAttribute('class') ?? '').trim().split(/\s+/).slice(0, 2).join('.');
            return `${el.tagName.toLowerCase()}${cls ? `.${cls}` : ''}`;
        };
        /** True when the element is inside a clipping/scrolling ancestor below the root, or is itself fixed. */
        const exempt = (el: Element) => {
            for (let node: Element | null = el; node && node !== root.parentElement; node = node.parentElement) {
                const style = getComputedStyle(node);
                if (style.position === 'fixed') return true;
                if (node !== el && node !== root && clips(style)) return true;
            }
            return false;
        };
        const past = new Map<Element, number>();
        for (const el of root.querySelectorAll('*')) {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            const over = Math.round(rect.right - limit);
            if (over > 1 && !exempt(el)) past.set(el, over);
        }
        const offenders = [...past.entries()]
            .filter(([el]) => !(el.parentElement && past.has(el.parentElement)))
            .map(([el, over]) => ({name: nameOf(el), over}))
            .sort((a, b) => b.over - a.over)
            .slice(0, 8);
        const pageOver = scopeSelector ? 0 : Math.max(0, document.documentElement.scrollWidth - viewport);
        const panelOver = scopeSelector ? Math.max(0, Math.round(rootRect.right - viewport), Math.round(-rootRect.left), (root as HTMLElement).scrollWidth - (root as HTMLElement).clientWidth) : 0;
        const over = Math.max(pageOver, panelOver, ...offenders.map((offender) => offender.over), 0);
        return {viewport, over, offenders};
    }, scope ?? null);
}

/** The panel of the window that is open, as the measure's scope. */
export const OPEN_WINDOW = '[role="dialog"] .modal-content';

/**
 * The gallery's phone shots: measure the page and, when a window is open, the window (a window is `position: fixed`, so the
 * page's own measure skips what is inside it). An overflow is appended, one JSON line, to `file`, and said in the log; it
 * never throws, so a gallery run is not stopped by a defect that was already there. The report is what the run leaves behind.
 */
export async function collectPhoneOverflow(page: Page, shot: string, file: string): Promise<void> {
    const results: Array<{what: string; result: SidewaysOverflow}> = [{what: 'page', result: await measureSidewaysOverflow(page)}];
    if ((await page.locator(OPEN_WINDOW).count()) > 0) results.push({what: 'window', result: await measureSidewaysOverflow(page, OPEN_WINDOW)});
    for (const {what, result} of results) {
        if (result.over <= 1) continue;
        mkdirSync(dirname(file), {recursive: true});
        appendFileSync(file, `${JSON.stringify({shot, what, viewport: result.viewport, over: result.over, offenders: result.offenders})}\n`);
        console.log(`  ⚠️ ${shot}: the ${what} scrolls sideways, ${result.over}px past ${result.viewport}px (${result.offenders.map((offender) => offender.name).join(', ') || 'no box named'})`);
    }
}
