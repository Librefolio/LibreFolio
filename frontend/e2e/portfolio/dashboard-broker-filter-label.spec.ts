/**
 * The dashboard's broker filter keeps a long broker name inside its bar — K step 15, item (b) (02/10).
 *
 * Written RED-FIRST, before the fix. In the stacked tiers of the dashboard's PageToolbar (`dashboard-controls`) the
 * currency select (`w-28`) and the broker trigger (`broker-filter-trigger`, dashboard/+page.svelte) share one row. The
 * trigger is `whitespace-nowrap` and nothing lets it shrink, and its label is user data: "All brokers" by default, but
 * with exactly one broker selected (out of several) that broker's name, up to 100 characters. Measured on 02/10 on a
 * 254 px bar, a 320 px phone without a scrollbar gutter: "Interactive Brokers" (19 characters) sticks out of the bar
 * by +6.2 px, "Interactive Brokers Ireland Ltd" (31) by +71.1 px, and still by +1.1 px on a 324 px bar. The card is
 * `overflow-hidden`: the user sees a button cut off mid-name, its arrow gone. The cure the developer approved: the
 * trigger shrinks and truncates its label with an ellipsis only when there is no room; the whole name stays in the DOM,
 * so the accessible name does not change.
 *
 * The contract, one test per width, so that a red never hides another:
 *   1. at the app's floor, a 320 px layout, the trigger, and the part of its label nothing inside it clips, stay inside
 *      the bar card within 1 px on both sides; the page does not scroll sideways; the label is still the whole name, in
 *      the DOM and in the accessible name, and what is visible of it stays inside the trigger;
 *   2. at 2560 px, the oneRow tier with room to spare, the whole name is shown and nothing clips it, on arrival and again
 *      after a trip to the 320 px layout (a truncation that never lets go is a defect too).
 * Not at 1280 px: there the bar is 927–942 px wide, the stackFilters tier, where the currency + broker row is capped at
 * the date picker's two-row width (390 px). A 45-character name has no room in it, and the cure must truncate it there.
 *
 * The scrollbar gutter. app.css reserves the vertical scrollbar's thickness on <html> (`scrollbar-gutter: stable`).
 * With classic scrollbars (the developer's Mac with a mouse) that is 15 px, headless too, so a 320 px viewport is a
 * 305 px layout, below the app's floor; overlay scrollbars (a Mac with a trackpad only, the mobile project) reserve
 * nothing. So the gutter g is measured once the dashboard has loaded and settled, like the toolbar sweep does it:
 * window.innerWidth − the width of <html>'s box, 0–30 px or the precondition fails. Not innerWidth − clientWidth:
 * headless, clientWidth counts the hidden gutter as room and reads the whole window. The narrow viewport is then
 * 320 + ⌈g⌉ (335 on the developer's Mac, 320 with overlay scrollbars): the layout is 320 px and the bar 254 px on every
 * host, the bar the 02/10 numbers were measured on. The messages say what the viewport, g and the bar were. The page
 * check compares every box with the right edge of <html>'s box, the layout's, for the same reason.
 *
 * Settling, without a sleep. After a resize the bar goes through ResizeObserver callbacks, Svelte's flush, frame
 * re-fits, the date picker's 100 ms resize debounce and, across 1024 px, the content column's 300 ms margin transition.
 * A width is measured once two readings, each taken after two rendering updates and 250 ms apart, are ready and
 * identical. Ready: the viewport is that wide, `window.__lfLayouts.dashboard` reports the expected tier with a width
 * equal to the filter row's content box, no CSS transition runs on the card, inside it or on an ancestor, and the fonts
 * are loaded.
 *
 * Positive controls. "Inside the bar", "no sideways scroll" and "nothing clips the name" are absences, so each reader is
 * first shown a presence, once the real reading is taken: a box hung 200 px past the card comes back past it; a 24 px
 * box whose unclipped text runs past the card comes back with its text past it (a trigger that shrinks without clipping
 * its label would look like that); a box hung g/2 + 4 px past the layout's right edge, outside the bar, comes back as
 * page overflow, by name (behind a gutter it still ends inside the window, where clientWidth sees nothing); and a 60 px
 * truncated twin of the label comes back clipped, by name. Each probe is a last child of the card (or of <body>), and
 * is gone before any assertion.
 *
 * Waiting for the scoped report. A selection reloads the report after a 2 s debounce, and nothing on the page says a
 * reload is pending: `data-busy` stays false meanwhile. Its request is the only witness, and a certain one: the report
 * cache lives in the page, and this document has never asked for this scope.
 *
 * Ownership. The broker is this test's: created for TEST_USER over the API with a long unique name, selected through the
 * panel (a toggle held in component state, nothing persisted), and deleted by id at the end whatever happens, once the
 * page has left the dashboard. Without `force`: it never held a transaction, and a plain delete refuses to take one a
 * neighbour may have written to it. It holds nothing, so no total moves under a neighbour, and no existing row is
 * borrowed. Seeded broker icon and portal URLs point at the internet: refused.
 *
 * Registered as `./dev.py test front-portfolio broker-filter-label` (desktop project, the runner default).
 */
import {expect, test as base, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const REPORT_PATH = `${API}/portfolio/report`;
/** The PageToolbar under test (dashboard/+page.svelte): its `layoutDebugName`, `testId` and `filterRowTestId`. */
const LAYOUT_NAME = 'dashboard';
const CARD_ID = 'dashboard-controls';
const ROW_ID = 'dashboard-filter-bar';
const TRIGGER_ID = 'broker-filter-trigger';
/**
 * The app's floor: a 320 px phone's layout. The narrow viewport is this plus the scrollbar gutter measured at load,
 * so the bar is 254 px on every host.
 */
const NARROW_LAYOUT_PX = 320;
/** A classic scrollbar is 15–17 px thick: a wider gap between the window and <html> is not a gutter. */
const MAX_GUTTER_PX = 30;
/** The oneRow tier with room to spare (a 2207–2222 px bar): nothing beside the trigger squeezes it here. */
const WIDE_VW = 2560;
const VIEWPORT_HEIGHT_PX = 900;
/** Layout boxes are fractional: up to 1 px past an edge is rounding, more is a control out of its bar. */
const TOLERANCE_PX = 1;
/**
 * A realistic account name. Its first 31 characters, "Interactive Brokers Ireland Ltd", alone stuck out of the 254 px bar
 * by +71.1 px on 02/10; with the unique suffix the whole name is 57–61 characters.
 */
const BROKER_NAME_BASE = 'Interactive Brokers Ireland Ltd - Pension Account';
const MIN_NAME_CHARS = 45;
/** Two identical readings at least this far apart: the date picker's 100 ms resize debounce fires in between. */
const SETTLE_INTERVAL_MS = 250;
const SETTLE_TIMEOUT_MS = 15_000;
/** How many page-overflow culprits a message names. */
const MAX_NAMED = 3;
/** Positive control of the bar check: a box hung this far past the card. */
const PROBE_BOX_ID = 'broker-label-probe-box';
const PROBE_BOX_PAST_PX = 200;
/** Positive control of the visible-label check: a 24 px box whose unclipped text runs far past the card. */
const PROBE_TEXT_ID = 'broker-label-probe-text';
const PROBE_TEXT = 'W'.repeat(80);
/** Positive control of the clip check: a truncated twin of the label, this wide. */
const PROBE_CLIP_ID = 'broker-label-probe-clip';
const PROBE_CLIP_WIDTH_PX = 60;
/** Positive control of the page check: a box hung half the gutter plus this past the layout's right edge. */
const PAGE_PROBE_ID = 'broker-label-probe-page';
const PAGE_PROBE_PAST_PX = 4;

type Tier = 'oneRow' | 'denseRow' | 'stackFilters' | 'oneColumn';

/** The broker this test created, by id: deleted at the end whatever happened. */
interface Owned {
    brokerIds: number[];
}

interface OwnedBroker {
    id: number;
    name: string;
}

/** The dashboard, scoped to the owned broker alone, and the narrow viewport this host needs for a 320 px layout. */
interface Scoped {
    broker: OwnedBroker;
    /** The scrollbar gutter measured at load. */
    gutter: number;
    /** NARROW_LAYOUT_PX + ⌈gutter⌉. */
    narrowVw: number;
}

interface Edges {
    left: number;
    right: number;
}

interface LayoutArgs {
    name: string;
    cardId: string;
    rowId: string;
    triggerId: string;
    vw: number;
    tier: Tier;
}

/** One settle round's view of the bar. Crosses `page.evaluate`, so plain data only. */
interface LayoutReading {
    /** Every reason the bar is not worth measuring yet. Empty when it is. */
    notReady: string[];
    /** Tier, observed width, scroll state and quarter-pixel boxes of the card, the row, the trigger and its contents. */
    signature: string;
    tier: string;
    /** window.innerWidth when the reading was taken. */
    viewport: number;
    /** `window.__lfLayouts.dashboard.width`: the ResizeObserver content width the thresholds are compared with. */
    barWidth: number;
    /** window.innerWidth − the width of <html>'s box: the scrollbar gutter the layout reserves. */
    gutter: number;
}

interface Clipper {
    name: string;
    box: Edges;
    scrollWidth: number;
    clientWidth: number;
    /** Inside the subject, or the subject itself: clipping there is the cure's truncation, not the bar cutting it off. */
    insideSubject: boolean;
}

interface SubjectReading {
    card: Edges;
    box: Edges & {width: number; height: number};
    /** The subject's text, whitespace collapsed. */
    text: string;
    /** Where its text runs are laid out, clipped or not; null when it renders no text. */
    textBox: Edges | null;
    /** Every element from the text up to the card, card included, that clips horizontally. */
    clippers: Clipper[];
}

interface Culprit {
    label: string;
    over: number;
}

interface PageReading {
    /** The right of <html>'s box: the layout's edge. A reserved scrollbar gutter is not room. */
    edge: number;
    gutter: number;
    /** How far the furthest box or text run reaches past the edge, px; negative: that far inside. */
    overflow: number;
    /** The outermost boxes and text runs past the edge, furthest first. */
    culprits: Culprit[];
    /** Boxes and text runs compared with the edge. */
    measured: number;
}

interface Spill {
    /** How far the box starts left of the frame's left edge, px; negative: that far inside it. */
    left: number;
    /** How far the box ends right of the frame's right edge, px; negative: that far inside it. */
    right: number;
    over: number;
}

interface BarVerdict {
    box: Spill;
    /** The visible part of the label against the card; null when nothing of it is visible. */
    label: Spill | null;
    /** The furthest of the two past the card, px. */
    over: number;
}

interface Probe {
    id: string;
    /** The element it hangs from, by data-testid, or null for <body>. */
    parentId: string | null;
    css: string;
    text: string;
}

// =============================================================================
// Reading the page
// =============================================================================

/** Runs inside the page: serialised by `page.evaluate`, so it references nothing outside itself. */
async function readLayoutInPage({name, cardId, rowId, triggerId, vw, tier}: LayoutArgs): Promise<LayoutReading> {
    // Two real rendering updates: ResizeObserver notifications are delivered inside one, so after the second whatever
    // the previous round changed has been observed and reacted to.
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

    const notReady: string[] = [];
    const layout = (window as unknown as {__lfLayouts?: Record<string, {layoutMode?: unknown; width?: unknown} | undefined>}).__lfLayouts?.[name];
    const card = document.querySelector<HTMLElement>(`[data-testid="${cardId}"]`);
    const row = document.querySelector<HTMLElement>(`[data-testid="${rowId}"]`);
    const trigger = document.querySelector<HTMLElement>(`[data-testid="${triggerId}"]`);
    const html = document.documentElement.getBoundingClientRect();
    const gutter = window.innerWidth - html.width;
    if (!layout) notReady.push(`window.__lfLayouts.${name} is not registered`);
    if (!card) notReady.push(`[data-testid="${cardId}"] is not in the page`);
    if (!row) notReady.push(`[data-testid="${rowId}"] is not in the page`);
    if (!trigger) notReady.push(`[data-testid="${triggerId}"] is not in the page`);
    if (!layout || !card || !row || !trigger) return {notReady, signature: '', tier: '?', viewport: window.innerWidth, barWidth: Number.NaN, gutter};

    if (window.innerWidth !== vw) notReady.push(`the viewport is ${window.innerWidth} px wide, not ${vw}`);
    if (document.fonts.status !== 'loaded') notReady.push('fonts are still loading');
    const mode = String(layout.layoutMode);
    if (mode !== tier) notReady.push(`the bar is in the ${mode} tier, not ${tier}`);
    const rowStyle = getComputedStyle(row);
    const rowContent = row.getBoundingClientRect().width - parseFloat(rowStyle.paddingLeft) - parseFloat(rowStyle.paddingRight) - parseFloat(rowStyle.borderLeftWidth) - parseFloat(rowStyle.borderRightWidth);
    const barWidth = Number(layout.width);
    if (!(Math.abs(barWidth - rowContent) <= 0.5)) notReady.push(`the ResizeObserver still reports ${barWidth.toFixed(2)} px for a ${rowContent.toFixed(2)} px row`);
    // A CSS transition on the card, inside it or on an ancestor (the content column's margin animates for 300 ms across
    // 1024 px) is geometry still on its way.
    let transitions = 0;
    for (const animation of document.getAnimations()) {
        if (animation.playState !== 'running' || !(animation instanceof CSSTransition)) continue;
        const target = animation.effect instanceof KeyframeEffect ? animation.effect.target : null;
        if (target && (target === card || card.contains(target) || target.contains(card))) transitions++;
    }
    if (transitions > 0) notReady.push(`${transitions} CSS transition(s) still running on the bar or an ancestor`);

    const quarter = (box: {left: number; right: number; top: number; bottom: number}): string => [box.left, box.right, box.top, box.bottom].map((value) => Math.round(value * 4)).join(',');
    const contents = document.createRange();
    contents.selectNodeContents(trigger);
    const boxes = [card, row, trigger].map((element) => quarter(element.getBoundingClientRect()));
    return {
        notReady,
        signature: [mode, barWidth.toFixed(2), quarter(html), window.scrollX, document.documentElement.scrollWidth, ...boxes, quarter(contents.getBoundingClientRect())].join('|'),
        tier: mode,
        viewport: window.innerWidth,
        barWidth,
        gutter,
    };
}

/** Runs inside the page: serialised by `page.evaluate`, so it references nothing outside itself. */
function readSubjectInPage({cardId, subjectId}: {cardId: string; subjectId: string}): SubjectReading {
    const card = document.querySelector<HTMLElement>(`[data-testid="${cardId}"]`);
    const subject = document.querySelector<HTMLElement>(`[data-testid="${subjectId}"]`);
    if (!card) throw new Error(`[data-testid="${cardId}"] is not in the page`);
    if (!subject || !card.contains(subject)) throw new Error(`[data-testid="${subjectId}"] is not inside [data-testid="${cardId}"]`);
    const name = (element: Element): string => {
        const own = element.getAttribute('data-testid');
        if (own) return own;
        const classes = Array.from(element.classList)
            .filter((token) => /^[a-z][a-z0-9-]*$/i.test(token))
            .slice(0, 3);
        return [element.tagName.toLowerCase(), ...classes].join('.');
    };

    const runs: Text[] = [];
    const walker = document.createTreeWalker(subject, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) if (node.textContent?.trim()) runs.push(node as Text);
    const range = document.createRange();
    const clippers = new Map<Element, Clipper>();
    let textBox: Edges | null = null;
    for (const run of runs) {
        range.selectNodeContents(run);
        const box = range.getBoundingClientRect();
        if (box.width > 0) textBox = textBox ? {left: Math.min(textBox.left, box.left), right: Math.max(textBox.right, box.right)} : {left: box.left, right: box.right};
        // Every box between the text and the card that clips horizontally. Overflow does not apply to an inline box.
        for (let element = run.parentElement; element; element = element.parentElement) {
            const style = getComputedStyle(element);
            if (!clippers.has(element) && style.display !== 'inline' && style.display !== 'contents' && ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowX)) {
                const own = element.getBoundingClientRect();
                clippers.set(element, {name: name(element), box: {left: own.left, right: own.right}, scrollWidth: element.scrollWidth, clientWidth: element.clientWidth, insideSubject: subject.contains(element)});
            }
            if (element === card) break;
        }
    }
    const box = subject.getBoundingClientRect();
    const cardBox = card.getBoundingClientRect();
    return {
        card: {left: cardBox.left, right: cardBox.right},
        box: {left: box.left, right: box.right, width: box.width, height: box.height},
        text: runs
            .map((run) => run.textContent ?? '')
            .join(' ')
            .replace(/\s+/g, ' ')
            .trim(),
        textBox,
        clippers: [...clippers.values()],
    };
}

/**
 * Runs inside the page: serialised by `page.evaluate`, so it references nothing outside itself.
 *
 * The page's right edge is the layout's, the right of <html>'s box. Every box and text run of the page, visible or not
 * (a hidden box widens the page all the same), is compared with it, except popups, anything fixed, empty boxes and the
 * content of scrolling or clipping containers, which cannot widen the page past the container itself.
 */
function readPageInPage({tolerance}: {tolerance: number}): PageReading {
    const html = document.documentElement.getBoundingClientRect();
    const edge = html.right;
    const POPUP = '[role="listbox"], [role="dialog"], [role="tooltip"], [role="menu"]';
    const CLIPPING = ['auto', 'scroll', 'hidden', 'clip'];
    const range = document.createRange();
    const culprits: Culprit[] = [];
    let overflow = Number.NEGATIVE_INFINITY;
    let measured = 0;
    const describe = (element: Element): string => {
        const own = element.getAttribute('data-testid');
        if (own) return own;
        const owner = element.parentElement?.closest('[data-testid]')?.getAttribute('data-testid');
        const classes = Array.from(element.classList)
            .filter((token) => /^[a-z][a-z0-9-]*$/i.test(token))
            .slice(0, 3);
        return `${owner ? `${owner} › ` : ''}${[element.tagName.toLowerCase(), ...classes].join('.')}`;
    };
    /** Says whether the box reaches past the edge, and names it unless an ancestor past the edge already is. */
    const past = (box: DOMRect, insideCulprit: boolean, label: () => string): boolean => {
        measured++;
        const by = box.right - edge;
        overflow = Math.max(overflow, by);
        if (by <= tolerance) return false;
        if (!insideCulprit) culprits.push({label: label(), over: by});
        return true;
    };
    const scan = (element: Element, insideCulprit: boolean): void => {
        if (element.matches(POPUP)) return;
        const style = getComputedStyle(element);
        if (style.display === 'none' || style.position === 'fixed') return;
        const box = element.getBoundingClientRect();
        let culprit = insideCulprit;
        if (style.display !== 'contents' && box.width > 0 && box.height > 0) culprit = past(box, insideCulprit, () => describe(element));
        if (element instanceof SVGElement || CLIPPING.includes(style.overflowX)) return;
        for (const node of Array.from(element.childNodes)) {
            if (node instanceof Element) {
                scan(node, culprit);
            } else if (node.nodeType === Node.TEXT_NODE && node.textContent?.trim()) {
                range.selectNodeContents(node);
                const textBox = range.getBoundingClientRect();
                if (textBox.width > 0 && textBox.height > 0) past(textBox, culprit, () => `${describe(element)} › text "${(node.textContent ?? '').trim().slice(0, 24)}"`);
            }
        }
    };
    for (const child of Array.from(document.body.children)) scan(child, false);
    culprits.sort((a, b) => b.over - a.over);
    return {edge, gutter: window.innerWidth - html.width, overflow, culprits, measured};
}

function readSubject(page: Page, subjectId: string): Promise<SubjectReading> {
    return page.evaluate(readSubjectInPage, {cardId: CARD_ID, subjectId});
}

function readPage(page: Page): Promise<PageReading> {
    return page.evaluate(readPageInPage, {tolerance: TOLERANCE_PX});
}

/**
 * The scrollbar gutter, read once the page has loaded and settled, like the toolbar sweep reads it: <html>'s box is the
 * layout's width, gutter or not, headless or headed; clientWidth is not (headless it reads the whole window).
 */
async function measureGutter(page: Page): Promise<number> {
    const gutter = await page.evaluate(() => window.innerWidth - document.documentElement.getBoundingClientRect().width);
    expect(gutter >= 0 && gutter <= MAX_GUTTER_PX, `precondition: the scrollbar gutter (window.innerWidth − the width of <html>) is 0–${MAX_GUTTER_PX} px, measured ${gutter} px`).toBe(true);
    return gutter;
}

/** Resize, then read until two readings, 250 ms apart and each after two rendering updates, are ready and identical. */
async function settleAt(page: Page, vw: number, tier: Tier): Promise<LayoutReading> {
    await page.setViewportSize({width: vw, height: VIEWPORT_HEIGHT_PX});
    const args: LayoutArgs = {name: LAYOUT_NAME, cardId: CARD_ID, rowId: ROW_ID, triggerId: TRIGGER_ID, vw, tier};
    const seen: {last?: LayoutReading; settled?: LayoutReading} = {};
    await expect
        .poll(
            async () => {
                const reading = await page.evaluate(readLayoutInPage, args);
                const last = seen.last;
                seen.last = reading;
                if (reading.notReady.length > 0) return reading.notReady.join('; ');
                if (!last || last.notReady.length > 0 || last.signature !== reading.signature) return 'ready, not yet identical in two readings';
                seen.settled = reading;
                return 'settled';
            },
            {message: `the dashboard bar settles at vw ${vw} in the ${tier} tier`, timeout: SETTLE_TIMEOUT_MS, intervals: [SETTLE_INTERVAL_MS]},
        )
        .toBe('settled');
    if (!seen.settled) throw new Error(`vw ${vw}: the poll resolved without a settled reading`);
    return seen.settled;
}

// =============================================================================
// Judging a reading
// =============================================================================

function spill(box: Edges, frame: Edges): Spill {
    const left = frame.left - box.left;
    const right = box.right - frame.right;
    return {left, right, over: Math.max(left, right)};
}

/** What the user can see of the label: its text, cut by whatever clips it inside the subject itself. */
function visibleLabel(reading: SubjectReading): Edges | null {
    if (!reading.textBox) return null;
    let {left, right} = reading.textBox;
    for (const clipper of reading.clippers) {
        if (!clipper.insideSubject) continue;
        left = Math.max(left, clipper.box.left);
        right = Math.min(right, clipper.box.right);
    }
    return right > left ? {left, right} : null;
}

/** How far the subject, or the part of its label left visible, reaches past the bar card. */
function barVerdict(reading: SubjectReading): BarVerdict {
    const box = spill(reading.box, reading.card);
    const visible = visibleLabel(reading);
    const label = visible ? spill(visible, reading.card) : null;
    return {box, label, over: Math.max(box.over, label ? label.over : Number.NEGATIVE_INFINITY)};
}

/**
 * Everything that hides part of the label: its own box, any clipping box up to the card that its text runs past, and,
 * inside the subject, any clipping box whose content overflows it. That last rule catches an ellipsis even if the text's
 * laid-out extent were reported cut. It stays inside the subject because there the content is the label, while a
 * card's scrollWidth counts every control of the bar.
 */
function clipFindings(reading: SubjectReading): string[] {
    if (!reading.textBox) return ['the subject renders no text'];
    const findings: string[] = [];
    const own = spill(reading.textBox, reading.box);
    if (own.over > TOLERANCE_PX) findings.push(`the label runs out of its own box (${describeSpill(own)})`);
    for (const clipper of reading.clippers) {
        const cut = spill(reading.textBox, clipper.box);
        if (cut.over > TOLERANCE_PX) findings.push(`${clipper.name} hides part of the label (${describeSpill(cut)})`);
        if (clipper.insideSubject && clipper.scrollWidth > clipper.clientWidth + TOLERANCE_PX) findings.push(`${clipper.name} clips its content: scrollWidth ${clipper.scrollWidth} > clientWidth ${clipper.clientWidth}`);
    }
    return findings;
}

function px(value: number): string {
    return Number.isFinite(value) ? value.toFixed(1) : '?';
}

function signed(value: number): string {
    return Number.isFinite(value) ? `${value > 0 ? '+' : ''}${value.toFixed(1)}` : '?';
}

/** Positive: past the edge; negative: that far inside it. */
function describeSpill(value: Spill): string {
    return `${signed(value.left)} px past the left edge, ${signed(value.right)} px past the right edge`;
}

function describePage(reading: PageReading): string {
    const named = reading.culprits.slice(0, MAX_NAMED).map((culprit) => `${culprit.label} +${px(culprit.over)}`);
    return `furthest ${signed(reading.overflow)} px past the layout's right edge at ${px(reading.edge)} (scrollbar gutter ${px(reading.gutter)} px, ${reading.measured} boxes and text runs compared); outermost: ${named.join(', ') || 'none'}`;
}

function describeBarVerdict(layout: LayoutReading, reading: SubjectReading, verdict: BarVerdict): string {
    const label = verdict.label ? `its visible label ${describeSpill(verdict.label)}` : 'no visible label';
    return `viewport ${layout.viewport} px (${NARROW_LAYOUT_PX} + scrollbar gutter g ${px(layout.gutter)} px, a ${px(layout.viewport - layout.gutter)} px layout), bar ${px(layout.barWidth)} px (${layout.tier}): the broker trigger reaches ${signed(verdict.over)} px past the bar card [data-testid="${CARD_ID}"] — its box ${describeSpill(verdict.box)}; ${label}. The trigger is ${px(reading.box.width)} px wide for "${reading.text}" (${reading.text.length} characters)`;
}

/** The whole name, unclipped, in a trigger inside its bar. */
function expectShownWhole(layout: LayoutReading, reading: SubjectReading, broker: OwnedBroker, when: string): void {
    const where = `vw ${WIDE_VW}, bar ${px(layout.barWidth)} px (${layout.tier}), ${when}`;
    expect(reading.text, `${where}: the label is the whole name`).toBe(broker.name);
    const labelWidth = reading.textBox ? reading.textBox.right - reading.textBox.left : Number.NaN;
    expect(clipFindings(reading), `${where}: nothing clips the name (trigger ${px(reading.box.width)} px wide, label ${px(labelWidth)} px)`).toEqual([]);
    const box = spill(reading.box, reading.card);
    expect(box.over, `${where}: the trigger is inside the bar card (${describeSpill(box)})`).toBeLessThanOrEqual(TOLERANCE_PX);
}

// =============================================================================
// Positive controls
// =============================================================================

/** Hangs a probe for the duration of one reading, and removes it whatever happens. */
async function withProbe<T>(page: Page, probe: Probe, read: () => Promise<T>): Promise<T> {
    await page.evaluate(({id, parentId, css, text}) => {
        const parent = parentId === null ? document.body : document.querySelector(`[data-testid="${parentId}"]`);
        if (!parent) throw new Error(`[data-testid="${parentId}"] is not in the page`);
        const element = document.createElement('div');
        element.dataset.testid = id;
        element.style.cssText = css;
        element.textContent = text;
        parent.append(element);
    }, probe);
    try {
        return await read();
    } finally {
        await page.evaluate((id) => document.querySelector(`[data-testid="${id}"]`)?.remove(), probe.id);
    }
}

/**
 * The bar check is an absence: its reader must first see a spill. A box hung past the card must come back past it, and a
 * box that fits but whose unclipped text runs past the card must come back with its text past it. Both hang from the card,
 * which clips them as it clips the trigger.
 */
async function proveTheBarReaderSeesSpills(page: Page): Promise<void> {
    const hung = barVerdict(await withProbe(page, {id: PROBE_BOX_ID, parentId: CARD_ID, css: `width: calc(100% + ${PROBE_BOX_PAST_PX}px); height: 2px;`, text: ''}, () => readSubject(page, PROBE_BOX_ID)));
    expect(hung.over, `positive control: a box hung ${PROBE_BOX_PAST_PX} px past [data-testid="${CARD_ID}"] is read past it (${describeSpill(hung.box)})`).toBeGreaterThan(PROBE_BOX_PAST_PX - 5);

    const spilling = barVerdict(await withProbe(page, {id: PROBE_TEXT_ID, parentId: CARD_ID, css: 'width: 24px; height: 16px; white-space: nowrap; font-size: 12px;', text: PROBE_TEXT}, () => readSubject(page, PROBE_TEXT_ID)));
    expect(spilling.box.over, `positive control: the 24 px box itself fits in the bar (${describeSpill(spilling.box)})`).toBeLessThanOrEqual(TOLERANCE_PX);
    expect(spilling.label?.over ?? Number.NaN, `positive control: its unclipped text, running past the bar, is read past it (${spilling.label ? describeSpill(spilling.label) : 'no visible text read'})`).toBeGreaterThan(100);
}

/**
 * The page check is an absence too. A box hung half the gutter plus 4 px past the layout's right edge, outside the bar,
 * must come back as page overflow, by name: behind a classic scrollbar's gutter it still ends inside the window, the
 * overflow headless Chromium's clientWidth does not see; with no gutter it is simply past the window.
 */
async function proveThePageReaderSeesOverflow(page: Page, gutter: number): Promise<void> {
    const pastPx = gutter / 2 + PAGE_PROBE_PAST_PX;
    const reading = await withProbe(page, {id: PAGE_PROBE_ID, parentId: null, css: `position: absolute; top: 0; right: ${-pastPx}px; width: 20px; height: 2px;`, text: ''}, () => readPage(page));
    const probe = reading.culprits.find((culprit) => culprit.label === PAGE_PROBE_ID);
    expect(probe, `positive control: a box hung ${px(pastPx)} px past the layout's right edge (scrollbar gutter ${px(gutter)} px) is page overflow, by name (${describePage(reading)})`).toBeDefined();
    expect(probe?.over, 'positive control: by as far as it was hung').toBeCloseTo(pastPx, 0);
}

/** "Nothing clips the name" is an absence: a truncated twin of the label, hung from the card, must come back clipped, by name. */
async function proveTheClipReaderSeesTruncation(page: Page, name: string): Promise<void> {
    const twin = await withProbe(page, {id: PROBE_CLIP_ID, parentId: CARD_ID, css: `width: ${PROBE_CLIP_WIDTH_PX}px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: 12px;`, text: name}, () => readSubject(page, PROBE_CLIP_ID));
    const findings = clipFindings(twin);
    expect(
        findings.some((finding) => finding.startsWith(PROBE_CLIP_ID)),
        `positive control: a ${PROBE_CLIP_WIDTH_PX} px truncated twin of the label is reported clipped, by name (${JSON.stringify(findings)})`,
    ).toBe(true);
}

// =============================================================================
// The broker, the page, the cleanup
// =============================================================================

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

async function jsonFrom(response: HttpResponse, purpose: string): Promise<unknown> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    return response.json();
}

/** The dashboard's reload for exactly this broker: the one request that carries `broker_ids: [id]`. */
function isScopedReport(request: Request, brokerId: number): boolean {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== REPORT_PATH) return false;
    const ids = (request.postDataJSON() as {broker_ids?: unknown} | null)?.broker_ids;
    return Array.isArray(ids) && ids.length === 1 && ids[0] === brokerId;
}

/** A broker of TEST_USER's own, with a long unique name. Its id is recorded for cleanup before it is checked. */
async function createOwnedBroker(page: Page, owned: Owned): Promise<OwnedBroker> {
    const item = {name: `${BROKER_NAME_BASE} ${uniqueSuffix()}`};
    expect(item.name.length, `the broker name is long enough to stick out of any phone's bar: "${item.name}"`).toBeGreaterThanOrEqual(MIN_NAME_CHARS);
    schemas.BRCreateItem.parse(item);
    const created = schemas.BRBulkCreateResponse.parse(await jsonFrom(await page.request.post(`${API}/brokers`, {data: [item]}), 'create the owned broker'));
    const row = created.results.find((result) => result.name === item.name);
    if (typeof row?.broker_id === 'number') owned.brokerIds.push(row.broker_id);
    if (!row?.success || typeof row.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(created)}`);
    // The id goes to the run log, so the cleanup can be checked against the database afterwards.
    console.log(`owned broker #${row.broker_id} created: "${item.name}"`);
    return {id: row.broker_id, name: item.name};
}

/**
 * Deletes what the test created, by the ids it recorded. Routes and the dashboard go first, so no debounced reload
 * reads the broker while it goes; `page.request` shares the browser's session. No `force`: the broker never held a
 * transaction, and a plain delete refuses to take one a neighbour may have written to it.
 */
async function releaseOwned(page: Page, owned: Owned): Promise<void> {
    if (owned.brokerIds.length === 0) return;
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<unknown>): Promise<void> => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    await attempt('detach routes', () => page.unrouteAll({behavior: 'ignoreErrors'}));
    await attempt('leave the dashboard', () => page.goto('about:blank'));
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const deleted = schemas.BRBulkDeleteResponse.parse(await jsonFrom(await page.request.delete(`${API}/brokers?ids=${brokerId}`), 'delete the owned broker'));
            expect(deleted.results.find((result) => result.id === brokerId)?.success, `broker ${brokerId} deleted: ${JSON.stringify(deleted)}`).toBe(true);
            console.log(`owned broker #${brokerId} deleted`);
        });
    }
    expect(failures, 'every cleanup step is scoped to the broker this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use) => {
        const owned: Owned = {brokerIds: []};
        try {
            await use(owned);
        } finally {
            await releaseOwned(page, owned);
        }
    },
});

// Login, a full dashboard load, a 2 s debounced reload, up to three settled widths and the cleanup share the budget.
test.setTimeout(120_000);

async function keepOffline(page: Page, origin: string): Promise<void> {
    // Seeded broker icon and portal URLs point at the internet: refused, the icons fall back to their fixed-size placeholders.
    await page.route(
        (url) => (url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== origin,
        (route) => route.abort('blockedbyclient'),
    );
}

/**
 * Signs in as TEST_USER, creates the broker, opens the dashboard at WIDE_VW, measures the scrollbar gutter once it has
 * loaded and settled, and selects that broker alone through the panel. Ends once the report scoped to it is in and the
 * page has settled, with the trigger naming the broker.
 */
async function openDashboardScopedToOwnedBroker(page: Page, baseURL: string | undefined, owned: Owned): Promise<Scoped> {
    if (!baseURL) throw new Error('This spec needs the runner-provided baseURL');
    await keepOffline(page, new URL(baseURL).origin);
    await login(page, TEST_USER);
    const broker = await createOwnedBroker(page, owned);

    await page.setViewportSize({width: WIDE_VW, height: VIEWPORT_HEIGHT_PX});
    await navigateTo(page, '/dashboard');
    const dashboard = page.getByTestId('dashboard-page');
    await waitForSettled(dashboard, 30_000);
    const gutter = await measureGutter(page);

    const trigger = page.getByTestId(TRIGGER_ID);
    await trigger.click();
    const item = page.getByTestId(`broker-filter-item-${broker.id}`);
    await expect(item, 'precondition: the filter panel lists the broker this test created').toBeVisible({timeout: 5_000});
    // Armed before the click: the reload is the only witness that the selection reached the page (see the header). It is
    // awaited below; the empty catch only keeps a failure in between from also surfacing as an unhandled rejection.
    const reload = page.waitForResponse((response) => isScopedReport(response.request(), broker.id), {timeout: 20_000});
    void reload.catch(() => undefined);
    await item.click();
    // The item is a toggle: the end state is asserted, not assumed. The label names a broker only when it is the one selected out of several.
    await expect(trigger, 'precondition: the filter is scoped to this broker alone').toHaveAccessibleName(broker.name);
    await trigger.click();
    await expect(item, 'the filter panel closed').toBeHidden();
    const response = await reload;
    expect(response.ok(), `the report scoped to broker ${broker.id} answered HTTP ${response.status()}`).toBe(true);
    await waitForSettled(dashboard, 30_000);
    await expect(trigger, 'precondition: once its report is in, the trigger names this broker').toHaveAccessibleName(broker.name);
    // The pointer is parked in the top-left corner, off the bar: a control moving under a still pointer would start hover transitions.
    await page.mouse.move(1, 1);
    return {broker, gutter, narrowVw: NARROW_LAYOUT_PX + Math.ceil(gutter)};
}

// =============================================================================
// The tests
// =============================================================================

test.describe('Dashboard broker filter: a long broker name stays inside its bar (K step 15, item b)', () => {
    test(`layout ${NARROW_LAYOUT_PX} px (viewport ${NARROW_LAYOUT_PX} + scrollbar gutter): the trigger and its visible label stay inside the bar card, the page does not scroll sideways, the name stays whole`, async ({page, baseURL, owned}) => {
        const {broker, narrowVw} = await openDashboardScopedToOwnedBroker(page, baseURL, owned);
        const trigger = page.getByTestId(TRIGGER_ID);

        const layout = await settleAt(page, narrowVw, 'oneColumn');
        const reading = await readSubject(page, TRIGGER_ID);
        const pageReading = await readPage(page);
        const where = `viewport ${narrowVw} px (${NARROW_LAYOUT_PX} + g ${px(layout.gutter)} px), bar ${px(layout.barWidth)} px`;

        // With the readings taken, each absence below is first shown a presence.
        await proveTheBarReaderSeesSpills(page);
        await proveThePageReaderSeesOverflow(page, pageReading.gutter);

        // The cure truncates on screen only: the whole name stays in the DOM, and so in the accessible name.
        expect(reading.text, `${where}: the label is still the whole name in the DOM`).toBe(broker.name);
        await expect(trigger, `${where}: and in the accessible name`).toHaveAccessibleName(broker.name);
        const visible = visibleLabel(reading);
        expect(visible, `${where}: the trigger shows part of its label`).not.toBeNull();
        if (visible) {
            const inTrigger = spill(visible, reading.box);
            expect(inTrigger.over, `${where}: what is visible of the label stays inside its trigger (${describeSpill(inTrigger)})`).toBeLessThanOrEqual(TOLERANCE_PX);
        }
        expect.soft(pageReading.overflow, `${where}: the page does not scroll sideways — ${describePage(pageReading)}`).toBeLessThanOrEqual(TOLERANCE_PX);

        const verdict = barVerdict(reading);
        expect(verdict.over, describeBarVerdict(layout, reading, verdict)).toBeLessThanOrEqual(TOLERANCE_PX);
    });

    test(`vw ${WIDE_VW} (oneRow, room to spare): the whole name is shown unclipped, on arrival and after a trip to the ${NARROW_LAYOUT_PX} px layout`, async ({page, baseURL, owned}) => {
        const {broker, narrowVw} = await openDashboardScopedToOwnedBroker(page, baseURL, owned);
        const trigger = page.getByTestId(TRIGGER_ID);

        const arrival = await settleAt(page, WIDE_VW, 'oneRow');
        const shown = await readSubject(page, TRIGGER_ID);
        await proveTheClipReaderSeesTruncation(page, broker.name);
        expectShownWhole(arrival, shown, broker, 'on arrival');
        await expect(trigger, `vw ${WIDE_VW}, on arrival: the accessible name is the whole name`).toHaveAccessibleName(broker.name);

        await settleAt(page, narrowVw, 'oneColumn');
        const back = await settleAt(page, WIDE_VW, 'oneRow');
        const shownAgain = await readSubject(page, TRIGGER_ID);
        const trip = `after a trip to the ${NARROW_LAYOUT_PX} px layout (viewport ${narrowVw} px)`;
        expectShownWhole(back, shownAgain, broker, trip);
        await expect(trigger, `vw ${WIDE_VW}, ${trip}: the accessible name is still the whole name`).toHaveAccessibleName(broker.name);
    });
});
