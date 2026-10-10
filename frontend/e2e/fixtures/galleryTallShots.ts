/**
 * Gallery — screens taller than the desktop's 720 px, for the shots whose subject the screen cuts: the coordinator's rule,
 * approved by the developer (commit C4). The shots and the reason for each are the release pipeline's
 * (runs/b5_tall_worklist.json, lista_scatti_alti.md). The seven shots that took the rule first keep their own helpers
 * (galleryRiskLab.ts `fitViewportToBlock`, galleryPac.ts, galleryProviderCompare.ts).
 *
 * Desktop only: the mobile project keeps its phone. Its screen is the emulated device's, which `setViewportSize` would
 * overwrite, so every helper here refuses a touch screen.
 *
 * ## Three ways
 *
 * - **A block** ({@link extendScreenToBlock}): today's framing stays, scroll included, and the screen grows down to the
 *   block's end plus the frame's margin, `max(720, ceil(bottom) + 8)`, the bottom read on the screen. Some blocks follow the
 *   screen — the holdings map is 65% of it tall (ExposureTreemap.svelte), the performance chart scrolls inside 70% of it
 *   (PerformanceChart.svelte) — so the block is measured again after every resize, until the screen holds it with the margin:
 *   the screen at which the block, grown with it, ends 8 px above the bottom edge.
 * - **A dialog** ({@link fitScreenToDialog}): its body is capped at a share of the screen — ModalBase's box at 90%, a
 *   dialog's own column at 80, 85 or 90%, AssetModal's body at 70% — so a taller screen lets it stop scrolling. The shares are
 *   read on the page, off every capped box from the body up to the dialog's box, and the screen becomes the height at which
 *   none of them holds the body back. A box capped in pixels does not follow the screen: the fit says so, and fails. What the
 *   body hides is its content in flow — the height it takes when nothing holds it — not its scroll range: BrokerForm's sticky
 *   footer hangs 16 px out of the flow (`-mb-4`), so that body always scrolls 16 px, with nothing in them.
 * - **A whole page** ({@link PAGE_BLOCK}): the page's body taken as the block, so the screen is as tall as the page. Not
 *   Playwright's `fullPage`: that capture keeps the screen and paints the rest of the page under it, and the sidebar — fixed,
 *   one screen tall — stops at 720 px with the page bare below it (seen on `brokers/list`, run b5_c4_1).
 *
 * The screen the page had is remembered: {@link restoreTallScreen} puts it back right after the shot when the test goes on —
 * other shots, other combinations — and does nothing when nothing grew it.
 *
 * ## The header
 *
 * Header.svelte resets itself on every `resize` — visible again, its scroll baseline where the page stands
 * (`syncScrollContext`) — and slides away only after 8 px of scrolling down (`HIDE_SCROLL_THRESHOLD`). So after every resize
 * the header is put back as it was: when it was hidden, the page goes up {@link HEADER_STEP} px and, a rendered frame later,
 * back down to the same scroll — the header sees a scroll down and slides away, and the frame keeps its place. An open
 * dialog pins the header (`modalScrollLockCount`): there is nothing to put back.
 *
 * ## After a resize
 *
 * A chart may redraw (its container's ResizeObserver, a `resize` listener), and content that came into view may load its
 * images. Every fit ends on the subject's images loaded, its charts' pixels and render counters still ({@link chartsStill}),
 * nothing animating and nothing moving, the pointer parked with no tooltip — then on the whole subject asserted in the shot,
 * and one line in the run's log (📐).
 */

import {expect, type Locator, type Page} from './playwright';
import {waitForStillness} from './galleryReportSets';
import {imagesSettled, parkPointer} from './galleryRiskLab';

/** The whole page, as a block for {@link extendScreenToBlock}: the screen becomes as tall as the page. */
export const PAGE_BLOCK = 'body';

/** The space left between the subject's end and the screen's bottom edge. */
const FRAME_MARGIN = 8;

/** How far the page goes up and back to hide the header again: past Header.svelte's 8 px `HIDE_SCROLL_THRESHOLD`. */
const HEADER_STEP = 16;

/** Resizes a block fit may take: one for a block that does not follow the screen, a few more for one that does. */
const MAX_BLOCK_FITS = 6;

/** Resizes a dialog fit may take: one when every cap is a share of the screen, a second for content that follows it. */
const MAX_DIALOG_FITS = 3;

/** How long the page may take to handle a resize and the header to settle again, on a busy lane. */
const RESIZE_TIMEOUT = 10_000;

/** The marks a dialog fit leaves on the box that scrolls and on the dialog's box, so the page can name them again. */
const TALL_BODY = 'data-gallery-tall-body';
const TALL_BOX = 'data-gallery-tall-box';

type Screen = {width: number; height: number};

/** The screen each page had before a fit grew it: what {@link restoreTallScreen} puts back. */
const screensBefore = new WeakMap<Page, Screen>();

function currentScreen(page: Page): Screen {
    const screen = page.viewportSize();
    if (!screen) throw new Error('the page has no viewport');
    return screen;
}

/** The project's screen, remembered on the first fit: a later fit grows from it, never from a screen already grown. */
function rememberScreen(page: Page): Screen {
    const own = screensBefore.get(page) ?? currentScreen(page);
    screensBefore.set(page, own);
    return own;
}

/** The mobile project emulates its phone's screen with the device: `setViewportSize` would overwrite it. */
async function refuseOnPhone(page: Page): Promise<void> {
    if (await page.evaluate(() => navigator.maxTouchPoints > 0)) throw new Error('a taller screen was asked on a touch screen: the rule is for the desktop project only');
}

/** Two animation frames rendered in the page: a scroll made before is dispatched, and every frame callback it scheduled has run. */
async function renderedFrames(page: Page): Promise<void> {
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
}

/** The header's `data-scroll-state` — visible, hidden or pinned — or null on a page without one. */
async function headerState(page: Page): Promise<string | null> {
    const header = page.getByTestId('app-header');
    if ((await header.count()) === 0) return null;
    return header.getAttribute('data-scroll-state');
}

/**
 * Resize the screen and end once the page has handled it: its `resize` dispatched — the app's listeners, added at mount,
 * run before the one armed here — and its layout at the new height.
 */
async function resizeScreen(page: Page, size: Screen): Promise<void> {
    const screen = currentScreen(page);
    if (screen.width === size.width && screen.height === size.height) return;
    await page.evaluate(() => {
        const flag = window as unknown as {__galleryTallResized?: boolean};
        flag.__galleryTallResized = false;
        window.addEventListener(
            'resize',
            () => {
                flag.__galleryTallResized = true;
            },
            {once: true},
        );
    });
    await page.setViewportSize(size);
    await expect
        .poll(() => page.evaluate(() => ((window as unknown as {__galleryTallResized?: boolean}).__galleryTallResized === true ? window.innerHeight : -1)), {
            message: 'the page never handled the screen resize',
            timeout: RESIZE_TIMEOUT,
        })
        .toBe(size.height);
}

/**
 * Put the header back as it was before a resize: hidden again when it was hidden — the page goes up {@link HEADER_STEP} px
 * and, a rendered frame later, down to `scrollY` again, the scroll down the header waits for to slide away. Visible or
 * pinned, the resize left it so. Ends on the page at `scrollY`.
 */
async function restoreHeader(page: Page, before: string | null, scrollY: number): Promise<void> {
    if (before !== 'hidden') return;
    const header = page.getByTestId('app-header');
    if ((await header.getAttribute('data-scroll-state')) !== 'hidden') {
        await page.evaluate((top) => window.scrollTo({top, behavior: 'instant'}), Math.max(0, scrollY - HEADER_STEP));
        await renderedFrames(page);
        await page.evaluate((top) => window.scrollTo({top, behavior: 'instant'}), scrollY);
    }
    await expect(header, 'the header did not slide away again after the resize').toHaveAttribute('data-scroll-state', 'hidden', {timeout: RESIZE_TIMEOUT});
    await expect.poll(() => header.evaluate((element) => element.getBoundingClientRect().bottom), {message: 'the header is still sliding away', timeout: RESIZE_TIMEOUT}).toBeLessThanOrEqual(1);
    await expect.poll(() => page.evaluate(() => Math.round(window.scrollY)), {message: 'the page did not come back to its scroll', timeout: RESIZE_TIMEOUT}).toBe(Math.round(scrollY));
}

/** Resize the screen and keep the frame: the scroll the page had, and its header as it was. */
async function resizeKeepingFrame(page: Page, size: Screen): Promise<void> {
    const before = await headerState(page);
    await resizeScreen(page, size);
    // The page keeps its scroll: a fit never grows the screen past the end of the page, and a smaller screen scrolls further.
    await restoreHeader(page, before, await page.evaluate(() => window.scrollY));
}

/** Nothing in `scope` is running a Web Animation: the spec's `waitForMotionSettled`, which this module cannot import. */
async function animationsSettled(scope: Locator, what: string): Promise<void> {
    await expect.poll(() => scope.evaluate((root) => root.getAnimations({subtree: true}).filter((animation) => animation.playState === 'running').length), {message: `${what} is still animating`, timeout: 5_000}).toBe(0);
}

/**
 * The charts in `scope` have stopped drawing: their pixels and their render counters (`data-chart-renders`, chartReady.ts) are
 * the same twice running — galleryRiskDashboard.ts `canvasStill`, for canvases the page may not read too. The holdings map
 * draws the brokers' logos, pictures from other sites, and a canvas that holds one is closed to reading (`toDataURL` throws):
 * its size stands for it, and its render counter tells when ECharts drew it again.
 */
async function chartsStill(scope: Locator, what: string): Promise<void> {
    let previous: string | null = null;
    await expect
        .poll(
            async () => {
                const now = await scope.evaluate((root) => {
                    const canvases = Array.from(root.querySelectorAll('canvas'));
                    let hash = 0;
                    for (const canvas of canvases) {
                        let pixels = `${canvas.width}x${canvas.height}`;
                        if (canvas.width > 0 && canvas.height > 0) {
                            try {
                                pixels = canvas.toDataURL();
                            } catch {
                                // A picture from another site is drawn in it: its size stands for its pixels.
                            }
                        }
                        for (let index = 0; index < pixels.length; index += 1) hash = (Math.imul(hash, 31) + pixels.charCodeAt(index)) | 0;
                    }
                    const passes = Array.from(root.querySelectorAll('[data-chart-renders]'), (chart) => chart.getAttribute('data-chart-renders') ?? '').join(',');
                    return `${canvases.length}:${hash}:${passes}`;
                });
                const still = now === previous;
                previous = now;
                return still;
            },
            {message: `${what} is still drawing`, timeout: 15_000, intervals: [150, 250]},
        )
        .toBe(true);
}

/** What a resize can change in the subject: images that came into view, charts redrawn, anything still moving. */
async function settleAfterResize(page: Page, subject: Locator, what: string): Promise<void> {
    await imagesSettled(subject);
    await chartsStill(subject, what);
    await animationsSettled(subject, what);
    await waitForStillness(subject, what);
    // The subject may have moved under the pointer: parked again, where nothing reacts to it, and no tooltip left.
    await parkPointer(page);
}

/** Take the marks of an earlier dialog fit off the page. */
async function clearMarks(page: Page): Promise<void> {
    await page.evaluate(
        (marks) => {
            for (const mark of marks) for (const element of Array.from(document.querySelectorAll(`[${mark}]`))) element.removeAttribute(mark);
        },
        [TALL_BODY, TALL_BOX],
    );
}

// ---------------------------------------------------------------------------
// A block
// ---------------------------------------------------------------------------

/**
 * DESKTOP ONLY — the tall-screen rule (coordinator's decision, approved by the developer). Keep today's framing — the page
 * stays where the test scrolled it — and grow the screen down to `block`'s end plus the frame's margin, `max(720,
 * ceil(bottom) + 8)` with the bottom read on the screen, width and scale unchanged; never past the end of the page, which
 * would pull the frame up. `footer`, a bar that sticks to the screen's bottom edge over the page (the PAC wizard's Back and
 * Continue), is made room for under the block. Measured with the block standing still, every combination — its sentences
 * wrap differently in each language — and again after each resize: a block that follows the screen gets the screen that holds
 * it grown, one whose height grows as fast as the screen fails here instead of being cut. Ends on the header as it was, the
 * block settled again (a resize may redraw a chart), asserted whole in the shot and clear of the footer, and logged (📐) under
 * `shot`. {@link restoreTallScreen} puts the project's screen back when the test goes on.
 */
export async function extendScreenToBlock(page: Page, block: Locator, shot: string, options: {footer?: Locator} = {}): Promise<void> {
    await refuseOnPhone(page);
    const own = rememberScreen(page);
    await expect(block, `${shot}: the block is not on the page`).toBeVisible();
    await waitForStillness(block, `${shot}: the block`);
    // The screen the block asks for, on the screen it is on now.
    const need = async (): Promise<number> => {
        const reserve = options.footer ? Math.ceil((await options.footer.boundingBox())?.height ?? 0) : 0;
        const {bottom, pageEnd} = await block.evaluate((element) => ({bottom: element.getBoundingClientRect().bottom, pageEnd: document.documentElement.scrollHeight - window.scrollY}));
        return Math.max(own.height, Math.min(Math.ceil(bottom) + FRAME_MARGIN + reserve, Math.max(Math.ceil(bottom), Math.floor(pageEnd))));
    };
    let height = currentScreen(page).height;
    let wanted = await need();
    let previous: {height: number; wanted: number} | null = null;
    for (let fits = 0; ; fits += 1) {
        // Held, and to the pixel (or by the project's own screen): done.
        if (wanted <= height && (wanted >= height - 1 || height === own.height)) break;
        if (fits === MAX_BLOCK_FITS) throw new Error(`${shot}: no screen holds the block after ${MAX_BLOCK_FITS} resizes (it asks ${wanted} px on a ${height} px screen)`);
        let next = wanted;
        if (wanted > height && previous && previous.height !== height) {
            // Still cut, and it grew with the screen: the screen at which the block, grown at the same rate, ends at the margin.
            const rate = (wanted - previous.wanted) / (height - previous.height);
            if (rate >= 1) throw new Error(`${shot}: the block grows as fast as the screen (${rate.toFixed(2)} px a px): no screen holds it`);
            next = Math.max(wanted, Math.ceil(height + (wanted - height) / (1 - rate)));
        }
        previous = {height, wanted};
        await resizeKeepingFrame(page, {width: own.width, height: next});
        await waitForStillness(block, `${shot}: the block`);
        height = next;
        wanted = await need();
    }
    await settleAfterResize(page, block, `${shot}: the block`);
    await expect(block, `${shot}: the block is not whole in the shot`).toBeInViewport({ratio: 1});
    if (options.footer) {
        const blockBox = await block.boundingBox();
        const footerBox = await options.footer.boundingBox();
        if (!blockBox || !footerBox) throw new Error(`${shot}: the block or the footer has no box`);
        expect(footerBox.y, `${shot}: the footer covers the end of the block`).toBeGreaterThanOrEqual(blockBox.y + blockBox.height - 0.5);
    }
    const blockHeight = Math.ceil((await block.boundingBox())?.height ?? 0);
    const screen = currentScreen(page);
    console.log(`  📐 ${shot}: block ${blockHeight} px → screen ${screen.width}×${screen.height}`);
}

// ---------------------------------------------------------------------------
// A dialog
// ---------------------------------------------------------------------------

interface DialogMeasure {
    /**
     * The body's content in flow hidden below its fold: the height it takes when nothing holds it, less the height it shows.
     * Not `scrollHeight − clientHeight`, which also counts a box hanging out of the flow — BrokerForm's sticky footer, whose
     * `-mb-4` collapses through its padding-less wrapper: the wrapper's box runs 16 px past the content, the body scrolls to
     * them, and they hide nothing.
     */
    hidden: number;
    /** The body's scroll range, `scrollHeight − clientHeight`: `hidden` plus whatever hangs out of the flow. */
    overflow: number;
    scrollHeight: number;
    /** What a failed fit reports: the body's sizes and its children's place in it. */
    evidence: string;
    /** Every box from the body up to the dialog's box that carries a max-height: its cap and its height now, in layout px. */
    caps: Array<{cap: number; height: number}>;
    /** The dialog's box sits in a fixed backdrop, which centres it on the screen. */
    overlay: boolean;
    boxBottom: number;
    boxHeight: number;
    screenHeight: number;
}

/**
 * Read the dialog on the page. On the first reading the body — `given`, else the scroll box inside the dialog with the most
 * content hidden — and the dialog's box — the body's ancestor that sits in a fixed backdrop (ModalBase's content), else the
 * dialog element itself — are marked ({@link TALL_BODY}, {@link TALL_BOX}), so every later reading, and the locators the fit
 * returns, name the same two. Heights are layout heights, which a dialog's entrance scale does not change.
 */
async function measureDialog(dialog: Locator, body: Locator | undefined): Promise<DialogMeasure> {
    const bodyHandle = body ? await body.elementHandle() : null;
    try {
        return await dialog.evaluate(
            (root, {bodyMark, boxMark, given}) => {
                let scroller = document.querySelector<HTMLElement>(`[${bodyMark}]`) ?? (given as HTMLElement | null);
                if (!scroller) {
                    let most = 0;
                    for (const candidate of [root, ...Array.from(root.querySelectorAll('*'))]) {
                        if (!(candidate instanceof HTMLElement) || candidate.getClientRects().length === 0) continue;
                        const overflowY = getComputedStyle(candidate).overflowY;
                        const hidden = candidate.scrollHeight - candidate.clientHeight;
                        if ((overflowY === 'auto' || overflowY === 'scroll') && hidden > most) {
                            most = hidden;
                            scroller = candidate;
                        }
                    }
                }
                // A dialog with nothing to scroll is measured from itself: no cap holds anything back.
                const start = scroller ?? (root as HTMLElement);
                let box = document.querySelector<HTMLElement>(`[${boxMark}]`);
                if (!box) {
                    let node: HTMLElement = start;
                    while (node.parentElement && node.parentElement !== document.body && getComputedStyle(node.parentElement).position !== 'fixed') node = node.parentElement;
                    const inBackdrop = node.parentElement !== null && node.parentElement !== document.body;
                    box = inBackdrop ? node : (root as HTMLElement);
                    start.setAttribute(bodyMark, '');
                    box.setAttribute(boxMark, '');
                }
                const overlay = box.parentElement !== null && getComputedStyle(box.parentElement).position === 'fixed';
                const caps: Array<{cap: number; height: number}> = [];
                for (let node: HTMLElement | null = start; node; node = node === box ? null : node.parentElement) {
                    const maxHeight = getComputedStyle(node).maxHeight;
                    if (maxHeight.endsWith('px')) caps.push({cap: parseFloat(maxHeight), height: node.offsetHeight});
                }
                // The content in flow: the height the body takes when nothing holds it — its own height and caps lifted for one
                // synchronous layout, put back before anything is painted. Margins that collapse through a box (BrokerForm's
                // footer, `-mb-4`, through its padding-less wrapper) are counted as the layout counts them.
                const shown = start.getBoundingClientRect().height;
                const inline = start.getAttribute('style');
                const scrolled = start.scrollTop;
                start.style.setProperty('flex', 'none', 'important');
                start.style.setProperty('height', 'auto', 'important');
                start.style.setProperty('max-height', 'none', 'important');
                const natural = start.getBoundingClientRect().height;
                if (inline === null) start.removeAttribute('style');
                else start.setAttribute('style', inline);
                // Lifted, the body had nothing to scroll: the scroll the test gave it is put back too.
                start.scrollTop = scrolled;
                const contentTop = start.getBoundingClientRect().top + start.clientTop - start.scrollTop;
                // Evidence for a fit that cannot finish: the body's children and theirs, top to bottom, as `name:top-bottom`.
                const place = (element: Element): string => {
                    const rect = element.getBoundingClientRect();
                    const sticky = getComputedStyle(element).position === 'sticky' ? '(sticky)' : '';
                    return `${element.getAttribute('data-testid') ?? element.tagName.toLowerCase()}${sticky}:${Math.round(rect.top - contentTop)}-${Math.round(rect.bottom - contentTop)}`;
                };
                const layout = Array.from(start.children, (child) => `${place(child)} [${Array.from(child.children, place).join(' ')}]`).join(' ');
                return {
                    hidden: Math.max(0, Math.round(natural - shown)),
                    overflow: start.scrollHeight - start.clientHeight,
                    scrollHeight: start.scrollHeight,
                    evidence: `body ${Math.round(shown)} of ${Math.round(natural)} px shown, ${start.clientHeight}/${start.scrollHeight} px scrolled, scrollTop ${Math.round(start.scrollTop)}, children ${layout}`,
                    caps,
                    overlay,
                    boxBottom: box.getBoundingClientRect().bottom,
                    boxHeight: box.offsetHeight,
                    screenHeight: window.innerHeight,
                };
            },
            {bodyMark: TALL_BODY, boxMark: TALL_BOX, given: bodyHandle},
        );
    } finally {
        await bodyHandle?.dispose();
    }
}

/**
 * The screen at which the body shows all its content: every capped box, grown by the content the body hides, within its cap —
 * a share of the screen, `cap / screen` now — and, for a dialog that is not centred in a backdrop, its end on the screen.
 */
function dialogTarget(measure: DialogMeasure, own: Screen): number {
    // Heights are whole pixels and the content's end may not be: one more keeps a fraction of a pixel from staying hidden.
    const grown = measure.hidden + 1;
    let height = Math.max(own.height, measure.screenHeight);
    for (const {cap, height: now} of measure.caps) height = Math.max(height, Math.ceil(((now + grown) * measure.screenHeight) / cap));
    if (!measure.overlay) height = Math.max(height, Math.ceil(measure.boxBottom + grown + FRAME_MARGIN));
    return height;
}

/**
 * DESKTOP ONLY — the tall-screen rule (coordinator's decision, approved by the developer), for a dialog whose body scrolls:
 * galleryProviderCompare.ts `fitScreenToCompareDialog`, generalised. `dialog` is the dialog's element — its backdrop
 * (ModalBase puts the test id there), its column or its body; `body`, when given, is the box that scrolls, found otherwise as
 * the one inside `dialog` with the most content hidden. The screen becomes the height at which no capped box holds the body
 * back ({@link dialogTarget}), width and scale unchanged — measured with the dialog standing still, every combination, and
 * again after each resize: a cap in pixels does not follow the screen, and the fit fails naming it instead of shooting a body
 * that still hides its content. Ends on the body showing all its content in flow, the dialog settled again, its box asserted
 * whole in the shot, and logged (📐) under `shot` — with the scroll left by a box hanging out of the flow, when there is one.
 * Returns the dialog's box — ModalBase's content: the title, the body and the buttons — valid until the next fit or the
 * restore. {@link restoreTallScreen} puts the project's screen back.
 */
export async function fitScreenToDialog(page: Page, dialog: Locator, shot: string, options: {body?: Locator} = {}): Promise<Locator> {
    await refuseOnPhone(page);
    const own = rememberScreen(page);
    await expect(dialog, `${shot}: the dialog is not on the page`).toBeVisible();
    await clearMarks(page);
    await animationsSettled(dialog, `${shot}: the dialog`);
    await measureDialog(dialog, options.body);
    const box = page.locator(`[${TALL_BOX}]`);
    await waitForStillness(box, `${shot}: the dialog`);
    let measure = await measureDialog(dialog, options.body);
    for (let fits = 0; measure.hidden > 0; fits += 1) {
        if (fits === MAX_DIALOG_FITS) throw new Error(`${shot}: the dialog's body still hides ${measure.hidden} px after ${MAX_DIALOG_FITS} resizes (${measure.evidence})`);
        const target = dialogTarget(measure, own);
        if (target <= measure.screenHeight)
            throw new Error(
                `${shot}: the dialog's body hides ${measure.hidden} px and no box between it and the dialog's box is capped by the screen: a taller screen shows nothing more (caps, height/cap: ${measure.caps.map(({cap, height}) => `${height}/${Math.round(cap)}`).join(', ')}; ${measure.evidence})`,
            );
        const before = measure;
        await resizeKeepingFrame(page, {width: own.width, height: target});
        await waitForStillness(box, `${shot}: the dialog`);
        measure = await measureDialog(dialog, options.body);
        // A cap that held the body back and stayed put while the screen changed is a cap in pixels: no screen lifts it.
        const stuck = measure.caps.find(({cap, height}, index) => before.caps[index] !== undefined && Math.round(before.caps[index].cap) === Math.round(cap) && height >= cap - 1);
        if (stuck && measure.hidden > 0) throw new Error(`${shot}: the dialog's body is held at ${Math.round(stuck.cap)} px, a cap in pixels: no screen shows the ${measure.hidden} px it hides`);
    }
    await settleAfterResize(page, box, `${shot}: the dialog`);
    measure = await measureDialog(dialog, options.body);
    expect(measure.hidden, `${shot}: the dialog's body hides its content on the fitted screen`).toBe(0);
    await expect(box, `${shot}: the dialog is not whole in the shot`).toBeInViewport({ratio: 1});
    const screen = currentScreen(page);
    const hanging = measure.overflow > 0 ? ` (${measure.overflow} px hanging out of the flow still scroll)` : '';
    console.log(`  📐 ${shot}: dialog ${measure.boxHeight} px, body ${measure.scrollHeight} px${hanging} → screen ${screen.width}×${screen.height}`);
    return box;
}

// ---------------------------------------------------------------------------
// Back to the project's screen
// ---------------------------------------------------------------------------

/**
 * Put back the screen the page had before the first fit, with the header as it was and the page where it stands, and take a
 * dialog fit's marks off the page. A no-op when nothing grew the screen — the mobile project, a shot that keeps 720 px, the
 * rule reverted — so a test calls it right after a shot that may have been tall, before anything else: the next shot, or the
 * next combination's load, is a 720 px one.
 */
export async function restoreTallScreen(page: Page): Promise<void> {
    const own = screensBefore.get(page);
    if (!own) return;
    screensBefore.delete(page);
    await clearMarks(page);
    await resizeKeepingFrame(page, own);
}
