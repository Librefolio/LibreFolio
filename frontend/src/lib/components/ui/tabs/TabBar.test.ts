// @vitest-environment jsdom
/**
 * TabBar — label visibility and accessible names (Vitest + jsdom).
 *
 * K step 13, item 7. The asset detail page hands PageToolbar two tabs with no `icon`, and
 * PageToolbar passes `showLabels={false}` below its `labelHideTabs` threshold (370 px of bar).
 * TabBar then hides every label unconditionally, so on a phone the two tabs render as empty
 * buttons: nothing to see. The approved fix has three parts. The icons belong to the page and
 * are asserted by the E2E (`e2e/assets/asset-mobile-layout.spec.ts`); the other two live in
 * TabBar and are pinned here, with a guard:
 *
 *   1. TabBar never hides the label of a tab that has no icon — whichever switch asked for it,
 *      `showLabels={false}` or `hideLabelOnMobile`;
 *   2. when it does hide a label, the button carries `aria-label={tab.label}`;
 *   3. (guard) while labels are shown, the visible text names the tab and no `aria-label` is added.
 *
 * Every button already carries `title={tab.label}`, which browsers fall back on for a name when
 * the content has none: the name is implicit today, not missing. The contract asked for is the
 * explicit `aria-label`.
 *
 * Why the assertions read a class and an attribute. jsdom loads no Tailwind, so `hidden` and
 * `sm:inline` compute to nothing and `toBeVisible()` would be true for every label: the class
 * token IS the rendering contract that can be observed here. For the same reason the computed
 * accessible name is useless in jsdom — the "hidden" label still contributes its text — so
 * the `aria-label` attribute is asserted directly. The real name, in a real layout, is
 * asserted by the E2E.
 *
 * Every label is a value this file passes in as a prop, never a translated string.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {cleanup, fireEvent, render, screen, within} from '$test/component';
import {ChartLine, Shield} from 'lucide-svelte';
import TabBar, {type TabItem} from './TabBar.svelte';

const PLAIN_LABEL = 'Plain label';
const ICON_LABEL = 'Icon label';
const SECOND_ICON_LABEL = 'Second icon label';

/** A mixed bar: one tab without an icon, two with. Mixed on purpose — the rule is per tab. */
const TABS: TabItem[] = [
    {id: 'plain', label: PLAIN_LABEL, testId: 'tab-plain'},
    {id: 'iconic', label: ICON_LABEL, icon: Shield, testId: 'tab-iconic'},
    {id: 'iconic-2', label: SECOND_ICON_LABEL, icon: ChartLine, testId: 'tab-iconic-2'},
];

function setup(props: {showLabels?: boolean; hideLabelOnMobile?: boolean} = {}) {
    render(TabBar, {tabs: TABS, activeTab: 'plain', ...props});
    const tab = (testId: string) => screen.getByTestId(testId);
    /** The label span of a tab, found by the text this file gave it — never by a class. */
    const label = (testId: string, text: string) => within(tab(testId)).getByText(text);
    return {tab, label};
}

describe('TabBar — label visibility and accessible names', () => {
    describe('showLabels={false} (PageToolbar below labelHideTabs)', () => {
        it('keeps the label of a tab without an icon: an icon-less tab is never left empty', () => {
            const {tab, label} = setup({showLabels: false});

            // Precondition: this tab really has nothing else to show.
            expect(tab('tab-plain').querySelector('svg'), 'precondition: the plain tab renders no icon').toBeNull();
            expect(label('tab-plain', PLAIN_LABEL), 'a tab without an icon must keep its label visible — hiding it leaves an empty button').not.toHaveClass('hidden');
        });

        it('hides the label of a tab with an icon and names the button with aria-label', () => {
            const {tab, label} = setup({showLabels: false});

            for (const [testId, text] of [
                ['tab-iconic', ICON_LABEL],
                ['tab-iconic-2', SECOND_ICON_LABEL],
            ] as const) {
                // Presence barrier: the icon is what stays on screen once the label goes.
                expect(tab(testId).querySelector('svg'), `precondition: ${testId} renders its icon`).not.toBeNull();
                expect(label(testId, text), `${testId}: the icon carries the tab, so the label may go`).toHaveClass('hidden');
                expect(tab(testId), `${testId}: a hidden label must be replaced by aria-label={tab.label}`).toHaveAttribute('aria-label', text);
            }
        });
    });

    describe('labels shown', () => {
        it.each([
            ['showLabels={true}', {showLabels: true}],
            ['showLabels undefined (default)', {}],
        ] as const)('%s: every label is visible and the visible text names the tab — no aria-label', (_mode, props) => {
            const {tab, label} = setup(props);

            for (const [testId, text] of [
                ['tab-plain', PLAIN_LABEL],
                ['tab-iconic', ICON_LABEL],
                ['tab-iconic-2', SECOND_ICON_LABEL],
            ] as const) {
                expect(label(testId, text), `${testId}: label shown`).not.toHaveClass('hidden');
                expect(tab(testId), `${testId}: the visible label already names the tab`).not.toHaveAttribute('aria-label');
            }
        });
    });

    describe('hideLabelOnMobile (viewport-driven, no showLabels)', () => {
        it('keeps `hidden sm:inline` on the label of a tab with an icon', () => {
            const {label} = setup({hideLabelOnMobile: true});

            const iconLabel = label('tab-iconic', ICON_LABEL);
            expect(iconLabel).toHaveClass('hidden');
            expect(iconLabel).toHaveClass('sm:inline');
        });

        it('does not hide the label of a tab without an icon (the rule is "never", not "only for showLabels")', () => {
            const {label} = setup({hideLabelOnMobile: true});

            expect(label('tab-plain', PLAIN_LABEL), 'below sm an icon-less tab would be an empty button').not.toHaveClass('hidden');
        });
    });
});

/*
 * G-15 (workstream A, release 1.3) — the Settings tab bar clips its last tab.
 *
 * `routes/(app)/settings/+page.svelte` draws TabBar inside a card with `overflow-hidden`. From `sm` up the tabs keep
 * their natural width (`flex-1 sm:flex-none`) and the row does not scroll, so an administrator's seventh tab, `email`,
 * runs past the card at 1280 px in Spanish (and between 640 and ~1200 px in the other languages): only `?tab=` or the
 * keyboard reach it. The approved cure is an opt-in prop, `scrollable` (default false), which the Settings page passes:
 *
 *   - with it, the tablist row — `role="tablist"`, the same buttons — is wrapped in a sideways scroll container,
 *     `<div data-testid="tab-bar-scroller" class="overflow-x-auto …">`, and the row is `min-w-full w-max`: as wide as
 *     its tabs, never narrower than the scroller, so `sm:ml-auto` still pushes the right-hand group when there is room;
 *   - the active tab is kept whole in view — when it changes, when the scroller is resized, when the labels change (a
 *     language switch). In a `requestAnimationFrame` after the change the bar reads the scroller's box and the active
 *     button's with `getBoundingClientRect()`, and moves the scroller's own `scrollLeft` — never the page. G-15 moved it
 *     by exactly what is hidden: `scrollLeft -= scroller.left − tab.left` when the tab starts left of the scroller,
 *     `scrollLeft += tab.right − scroller.right` when it ends right of it, nothing when it is inside; point 33, below,
 *     adds the fade's 24 px;
 *   - without it the markup is exactly today's — no scroller, the tablist is the root — and nothing ever scrolls: the
 *     five other places that draw a TabBar keep their bar.
 *
 * jsdom lays nothing out, so the layout is a model this file owns (`G15Geometry`): the scroller's box and the place
 * of each tab in the row. A tab's box slides left as the scroller scrolls right, as in a browser, so a reveal that
 * runs twice lands where one would: a red names wrong arithmetic, not a stale mock. Animation frames and resize
 * notifications are owned too — a frame is delivered, a resize announced, only when a case says so. Overflow on the
 * real page, in a real language, is the E2E's (`e2e/settings.spec.ts`, «G-15»).
 *
 * Red until G-15: TabBar had no `scrollable` prop, never drew `tab-bar-scroller`, and every case that needs the
 * scroller failed on its absence. The two guards — today's markup without the prop, nothing scrolled without it — were
 * green then and must stay green.
 *
 * A8b, the designer's point 33 (the colour coordinator, 17/10): a tab the user picks, or the bar reveals — on mount
 * too — must not lie under an active fade: `data-fade`, below, a 1.5rem mask (`mask-…-from-[calc(100%-1.5rem)]`) on
 * each side that hides tabs. «Exactly what is hidden» became «what is hidden, and the fade's 24 px». With `M` the
 * fade's width (1.5 × the root font size, as the mask: 24 px at jsdom's 16 px, which these cases keep — how the size is
 * read is not pinned), the tab's edges in the row's own coordinates (`tabStart`, `tabEnd`: its box from the scroller's
 * left edge, plus `scrollLeft`) and `maxScroll = scrollWidth − clientWidth`, a window `[target, target + clientWidth]`
 * shows the tab clear of the fades when `tabStart ≥ target + (target > 1 ? M : 0)` and
 * `tabEnd ≤ target + clientWidth − (target < maxScroll − 1 ? M : 0)`: at an end of the row no fade is drawn, so no
 * margin is owed. If the current `scrollLeft` already shows it so, nothing moves — the user's scroll stands. Otherwise a
 * tab too far left brings `target = max(0, tabStart − M)`, one too far right
 * `target = min(maxScroll, tabEnd + M − clientWidth)` — unless that target would hide the tab's start under the left
 * fade: then the start wins, `target = max(0, tabStart − M)`, and a tab wider than the window less its fades shows its
 * start and loses its end. In the layout below the mount on tab three moves too: its last 4 px lie under the right
 * fade, so the bar opens at 4. Red until A8b (point 33): every case whose reveal now ends elsewhere. A reveal that stops
 * at an end of the row, or a tab already clear of the fades, moves as before: green, and they stay green.
 */
const G15_IDS = ['one', 'two', 'three', 'four', 'five'] as const;
type G15Id = (typeof G15_IDS)[number];

const g15TestId = (id: G15Id): string => `tab-${id}`;

/** Five tabs, labelled by this file: never a translated string. */
const G15_TABS: TabItem[] = G15_IDS.map((id) => ({id, label: `Label ${id}`, testId: g15TestId(id)}));

/** Any height: the reveal is horizontal. */
const G15_TAB_HEIGHT_PX = 48;

/** The layout a browser would compute, which jsdom does not. */
interface G15Geometry {
    /** The scroller's box in the viewport, px. */
    scroller: {left: number; width: number};
    /** Where each tab sits in the row, px from the row's start, and how wide it is. */
    tabs: Record<G15Id, {offset: number; width: number}>;
}

/**
 * A 300 px scroller over 480 px of tabs — one 0–70 · two 70–160 · three 160–280 · four 280–380 · five 380–480 — so at
 * `scrollLeft` 0 the first three are inside, four ends 80 px past the right edge and five lies wholly past it. The right
 * fade covers 276–300 there: three is whole in view, but its last 4 px lie under it.
 */
function g15Layout(): G15Geometry {
    return {
        scroller: {left: 0, width: 300},
        tabs: {
            one: {offset: 0, width: 70},
            two: {offset: 70, width: 90},
            three: {offset: 160, width: 120},
            four: {offset: 280, width: 100},
            five: {offset: 380, width: 100},
        },
    };
}

let geometry: G15Geometry;
let frames: Map<number, FrameRequestCallback>;
let nextFrame: number;
let resizeObservers: G15ResizeObserver[];
/** Every attempt to scroll the page itself: the bar may move its own scroller, and nothing else. */
let pageScrolls: string[];

function g15Box(left: number, right: number): DOMRect {
    return {x: left, y: 0, left, right, top: 0, bottom: G15_TAB_HEIGHT_PX, width: right - left, height: G15_TAB_HEIGHT_PX, toJSON: () => ({})} as DOMRect;
}

/** The row is as wide as its tabs (`w-max`) and never narrower than the scroller (`min-w-full`). */
function g15RowWidth(): number {
    return Math.max(geometry.scroller.width, ...G15_IDS.map((id) => geometry.tabs[id].offset + geometry.tabs[id].width));
}

/** The box a browser would report for `element`; null for an element the model does not lay out. */
function g15Rect(element: Element): DOMRect | null {
    const {scroller, tabs} = geometry;
    const testId = element.getAttribute('data-testid');
    if (testId === 'tab-bar-scroller') return g15Box(scroller.left, scroller.left + scroller.width);
    // The row and its tabs slide left by what the scroller has scrolled: that is what scrolling is.
    const scrolled = element.closest<HTMLElement>('[data-testid="tab-bar-scroller"]')?.scrollLeft ?? 0;
    const rowLeft = scroller.left - scrolled;
    if (element.getAttribute('role') === 'tablist') return g15Box(rowLeft, rowLeft + g15RowWidth());
    const id = G15_IDS.find((candidate) => g15TestId(candidate) === testId);
    return id ? g15Box(rowLeft + tabs[id].offset, rowLeft + tabs[id].offset + tabs[id].width) : null;
}

class G15ResizeObserver implements ResizeObserver {
    readonly targets = new Set<Element>();
    constructor(readonly callback: ResizeObserverCallback) {
        resizeObservers.push(this);
    }
    observe(target: Element) {
        this.targets.add(target);
    }
    unobserve(target: Element) {
        this.targets.delete(target);
    }
    disconnect() {
        this.targets.clear();
    }
}

/** Announces a resize of `target` to every observer watching it, as a browser would; returns how many were watching. */
function g15Resized(target: Element): number {
    const watching = resizeObservers.filter((observer) => observer.targets.has(target));
    const contentRect = target.getBoundingClientRect();
    const size = [{inlineSize: contentRect.width, blockSize: contentRect.height}];
    for (const observer of watching) {
        observer.callback([{target, contentRect, borderBoxSize: size, contentBoxSize: size, devicePixelContentBoxSize: size} as unknown as ResizeObserverEntry], observer);
    }
    return watching.length;
}

/** Delivers the queued animation frames, then those they queue in turn: a bounded number of browser turns, no clock. */
async function g15DeliverFrames(turns = 4): Promise<void> {
    for (let turn = 0; turn < turns; turn += 1) {
        await tick();
        if (frames.size === 0) return;
        for (const [id, callback] of [...frames.entries()]) {
            if (frames.delete(id)) callback(performance.now());
        }
    }
    await tick();
}

describe('TabBar — scrollable (G-15: the Settings tab bar clips its last tab)', () => {
    beforeEach(() => {
        geometry = g15Layout();
        frames = new Map();
        nextFrame = 0;
        resizeObservers = [];
        pageScrolls = [];
        vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
            const id = ++nextFrame;
            frames.set(id, callback);
            return id;
        });
        vi.stubGlobal('cancelAnimationFrame', (id: number) => {
            frames.delete(id);
        });
        vi.stubGlobal('ResizeObserver', G15ResizeObserver);
        const originalRect = Element.prototype.getBoundingClientRect;
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
            return g15Rect(this) ?? originalRect.call(this);
        });
        // The scroller's widths agree with its boxes, for a bar that checks there is anything to scroll.
        const originalClientWidth = Object.getOwnPropertyDescriptor(Element.prototype, 'clientWidth')?.get;
        const originalScrollWidth = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollWidth')?.get;
        vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockImplementation(function (this: HTMLElement) {
            return this.getAttribute('data-testid') === 'tab-bar-scroller' ? geometry.scroller.width : (originalClientWidth?.call(this) ?? 0);
        });
        vi.spyOn(HTMLElement.prototype, 'scrollWidth', 'get').mockImplementation(function (this: HTMLElement) {
            return this.getAttribute('data-testid') === 'tab-bar-scroller' ? g15RowWidth() : (originalScrollWidth?.call(this) ?? 0);
        });
        vi.spyOn(Element.prototype, 'scrollIntoView').mockImplementation(function (this: Element) {
            pageScrolls.push(`scrollIntoView() on ${this.getAttribute('data-testid') ?? this.tagName}`);
        });
        vi.spyOn(window, 'scrollTo').mockImplementation(() => {
            pageScrolls.push('window.scrollTo()');
        });
        vi.spyOn(window, 'scrollBy').mockImplementation(() => {
            pageScrolls.push('window.scrollBy()');
        });
    });

    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    async function mountBar(props: {activeTab: G15Id; scrollable?: boolean}) {
        const result = render(TabBar, {tabs: G15_TABS, ...props});
        await g15DeliverFrames();
        return result;
    }

    /** The scroller: present, or the case is red on its absence — which is why every red below is red today. */
    function scrollerOf(): HTMLElement {
        const scroller = screen.queryByTestId('tab-bar-scroller');
        expect(scroller, 'TabBar with `scrollable` wraps its row in [data-testid="tab-bar-scroller"]').not.toBeNull();
        return scroller as HTMLElement;
    }

    /** A tab's edges as the bar reads them: through the model. */
    function edges(id: G15Id): {left: number; right: number} {
        const {left, right} = screen.getByTestId(g15TestId(id)).getBoundingClientRect();
        return {left, right};
    }

    /** The user scrolls the bar, as a browser delivers it: the position moves, then `scroll` fires on the scroller. */
    async function userScrollsTo(scroller: HTMLElement, left: number): Promise<void> {
        scroller.scrollLeft = left;
        await fireEvent.scroll(scroller);
        await g15DeliverFrames();
    }

    describe('markup', () => {
        it('without `scrollable` (the default): no scroller, and the tablist is the root, as today — the other TabBars keep their markup', async () => {
            const {container} = await mountBar({activeTab: 'one'});
            const tablist = screen.getByRole('tablist');

            expect(screen.queryByTestId('tab-bar-scroller'), 'no scroller unless it is asked for').toBeNull();
            expect(container.childElementCount, 'TabBar draws one root element').toBe(1);
            expect(container.firstElementChild, 'the tablist is the root').toBe(tablist);
            // jsdom loads no Tailwind: the class tokens are the layout contract observable here.
            for (const token of ['overflow-x-auto', 'w-max', 'min-w-full']) {
                expect(tablist, `the tablist does not take the scrolling layout (${token})`).not.toHaveClass(token);
            }
            for (const id of G15_IDS) {
                expect(screen.getByTestId(g15TestId(id)).parentElement, `${g15TestId(id)} is a child of the tablist`).toBe(tablist);
            }
        });

        it('with `scrollable`: [data-testid="tab-bar-scroller"] scrolls sideways and wraps the tablist, which keeps every tab', async () => {
            const {container} = await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            const tablist = screen.getByRole('tablist');

            expect(container.childElementCount, 'TabBar draws one root element').toBe(1);
            expect(container.firstElementChild, 'the scroller is the root').toBe(scroller);
            expect(tablist.parentElement, "the tablist is the scroller's own child: the row is what scrolls").toBe(scroller);
            // jsdom loads no Tailwind: the class tokens are the layout contract observable here; the E2E measures the real one.
            expect(scroller, 'the scroller scrolls sideways').toHaveClass('overflow-x-auto');
            expect(tablist, 'the row is as wide as its tabs').toHaveClass('w-max');
            expect(tablist, 'and never narrower than the scroller, so ml-auto still pushes the right-hand group').toHaveClass('min-w-full');
            for (const id of G15_IDS) {
                const tab = screen.getByTestId(g15TestId(id));
                expect(tab.parentElement, `${g15TestId(id)} is still a child of the tablist`).toBe(tablist);
                expect(tab).toHaveAttribute('role', 'tab');
            }
            expect(screen.getByTestId(g15TestId('one')), 'the active tab is still the selected one').toHaveAttribute('aria-selected', 'true');
        });
    });

    describe('the active tab is kept whole in view, clear of the fade (a 300 px scroller over 480 px of tabs, modelled)', () => {
        it('without `scrollable`, a tab past the edge scrolls nothing: not the bar, not its container, not the page', async () => {
            const {container, rerender} = await mountBar({activeTab: 'one'});
            const tablist = screen.getByRole('tablist');

            await rerender({activeTab: 'five'});
            await g15DeliverFrames();

            // Presence first: the change did land, so the absence below is about scrolling.
            expect(screen.getByTestId(g15TestId('five'))).toHaveAttribute('aria-selected', 'true');
            expect(tablist.scrollLeft, 'the bar is not scrolled').toBe(0);
            expect(container.scrollLeft, 'its container is not scrolled').toBe(0);
            expect(pageScrolls, 'the page is not scrolled').toEqual([]);
        });

        // red until A8b (point 33)
        it("on mount, as ?tab= opens the page: an active tab 80 px past the right edge (280–380 in 0–300) brings scrollLeft from 0 to 104 — the hidden 80 px and the fade's 24 px", async () => {
            await mountBar({activeTab: 'four', scrollable: true});
            const scroller = scrollerOf();

            expect(scroller.scrollLeft, "the hidden 80 px and the fade's 24 px: 380 + 24 − 300").toBe(104);
            expect(edges('four'), 'whole in view, ending where the right fade begins (276 of 300)').toEqual({left: 176, right: 276});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        // red until A8b (point 33)
        it("when activeTab changes to a tab 80 px past the right edge (280–380 in 0–300): scrollLeft grows by 104 — the hidden 80 px and the fade's 24 px", async () => {
            const {rerender} = await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller.scrollLeft, 'precondition: an active tab already inside, and clear of the fade, moved nothing').toBe(0);
            expect(edges('four'), 'precondition: tab four ends 80 px past the scroller').toEqual({left: 280, right: 380});

            await rerender({activeTab: 'four'});
            await g15DeliverFrames();

            expect(scroller.scrollLeft, "the hidden 80 px and the fade's 24 px: 380 + 24 − 300").toBe(104);
            expect(edges('four'), 'whole in view, ending where the right fade begins (276 of 300)').toEqual({left: 176, right: 276});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        it('when activeTab changes to a tab already inside and clear of both fades (120–240 at scrollLeft 40; the fades cover 0–24 and 276–300): scrollLeft stays 40', async () => {
            const {rerender} = await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            // The user scrolled the bar a little.
            scroller.scrollLeft = 40;
            expect(edges('three'), 'precondition: tab three lies inside the scroller, clear of both fades').toEqual({left: 120, right: 240});

            await rerender({activeTab: 'three'});
            await g15DeliverFrames();

            expect(screen.getByTestId(g15TestId('three'))).toHaveAttribute('aria-selected', 'true');
            expect(scroller.scrollLeft, 'a tab already whole in view and clear of the fades moves nothing').toBe(40);
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        // red until A8b (point 33)
        it("when activeTab changes to a tab 50 px past the left edge (−50–40 at scrollLeft 120): scrollLeft comes back to 46 — the hidden 50 px and the fade's 24 px", async () => {
            const {rerender} = await mountBar({activeTab: 'four', scrollable: true});
            const scroller = scrollerOf();
            // The bar is scrolled right, as after the last tabs were opened.
            scroller.scrollLeft = 120;
            expect(edges('two'), 'precondition: tab two starts 50 px before the scroller').toEqual({left: -50, right: 40});

            await rerender({activeTab: 'two'});
            await g15DeliverFrames();

            expect(scroller.scrollLeft, "back by the hidden 50 px and the fade's 24 px: 70 − 24").toBe(46);
            expect(edges('two'), 'whole in view, starting where the left fade ends (24)').toEqual({left: 24, right: 114});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        it("on a click, the user picking a tab wholly past the right edge (380–480 in 0–300): scrollLeft goes to 180, the end of the row — where no fade is drawn, so the fade's 24 px are not added", async () => {
            await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(edges('five'), 'precondition: tab five lies wholly past the scroller').toEqual({left: 380, right: 480});

            await fireEvent.click(screen.getByTestId(g15TestId('five')));
            await g15DeliverFrames();

            expect(screen.getByTestId(g15TestId('five'))).toHaveAttribute('aria-selected', 'true');
            expect(scroller.scrollLeft, 'the hidden 180 px: the end of the row, which the reveal never passes').toBe(180);
            expect(edges('five'), 'whole in view, flush with the right edge: nothing lies past it, so no fade covers it').toEqual({left: 200, right: 300});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        // red until A8b (point 33)
        it("when the scroller is resized (300 → 250 px) and the active tab (160–280) now ends 26 px past it: scrollLeft goes to 54 — the hidden part and the fade's 24 px", async () => {
            await mountBar({activeTab: 'three', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller.scrollLeft, 'precondition: tab three is in view — its last 4 px lay under the right fade (276–300), so the mount moved the bar 4 px').toBe(4);

            // The window narrowed.
            geometry.scroller.width = 250;
            expect(g15Resized(scroller), 'a ResizeObserver watches the scroller').toBeGreaterThan(0);
            await g15DeliverFrames();

            expect(scroller.scrollLeft, "the hidden part and the fade's 24 px: 280 + 24 − 250").toBe(54);
            expect(edges('three'), 'whole in view, ending where the right fade begins (226 of 250)').toEqual({left: 106, right: 226});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        // red until A8b (point 33)
        it("when the labels change (a language switch) and the active tab grows to 160–340: scrollLeft goes to 64 — the hidden part and the fade's 24 px", async () => {
            const {rerender} = await mountBar({activeTab: 'three', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller.scrollLeft, 'precondition: tab three (160–280) is in view — its last 4 px lay under the right fade (276–300), so the mount moved the bar 4 px').toBe(4);

            // Another language's longer labels: tab three grows by 60 px, and the tabs after it move along.
            geometry.tabs.three.width += 60;
            geometry.tabs.four.offset += 60;
            geometry.tabs.five.offset += 60;
            await rerender({tabs: G15_TABS.map((tab) => ({...tab, label: `${tab.label} (longer)`}))});
            await g15DeliverFrames();

            expect(within(screen.getByTestId(g15TestId('three'))).getByText('Label three (longer)'), 'presence: the new label is drawn').toBeInTheDocument();
            expect(scroller.scrollLeft, "the hidden part and the fade's 24 px: 340 + 24 − 300").toBe(64);
            expect(edges('three'), 'whole in view, ending where the right fade begins (276 of 300)').toEqual({left: 96, right: 276});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        // Point 33's margin, pinned on its own: owed where a fade is drawn, and only there.

        // red until A8b (point 33)
        it('on a click, a tab whole in view but ending under the right fade, with tabs past it (three, 160–280 in 0–300; the fade covers 276–300): scrollLeft goes to 4, just clear of the fade', async () => {
            await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(edges('three'), 'precondition: tab three is whole in view, its end 20 px from the right edge').toEqual({left: 160, right: 280});
            expect(scroller, 'precondition: the right fade is on — tabs four and five lie past the edge').toHaveAttribute('data-fade', 'end');

            await fireEvent.click(screen.getByTestId(g15TestId('three')));
            await g15DeliverFrames();

            expect(screen.getByTestId(g15TestId('three'))).toHaveAttribute('aria-selected', 'true');
            expect(scroller.scrollLeft, 'just enough to clear the fade: 280 + 24 − 300').toBe(4);
            expect(edges('three'), 'ends where the right fade begins (276 of 300)').toEqual({left: 156, right: 276});
            expect(scroller, 'the bar left its start, so the left fade is on too — 0–24, far from the tab').toHaveAttribute('data-fade', 'both');
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        // Guard — green today, and it stays green: at the end of the row no fade is drawn, so no margin is owed there.
        it('on a click, at the end of the row (scrollLeft 180 of 180): the last tab (380–480), flush with the right edge where no fade is drawn, moves nothing', async () => {
            await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            await userScrollsTo(scroller, 180);
            expect(scroller.scrollLeft, 'precondition: the user scrolled the bar to its end (480 − 300)').toBe(180);
            expect(scroller, 'precondition: nothing lies past the right edge, so no fade is drawn there').toHaveAttribute('data-fade', 'start');
            expect(edges('five'), 'precondition: tab five is whole in view, flush with the right edge').toEqual({left: 200, right: 300});

            await fireEvent.click(screen.getByTestId(g15TestId('five')));
            await g15DeliverFrames();

            expect(screen.getByTestId(g15TestId('five'))).toHaveAttribute('aria-selected', 'true');
            expect(scroller.scrollLeft, 'no fade on the right, no margin: the bar stays — and never runs past its end').toBe(180);
            expect(edges('five'), 'still flush with the right edge').toEqual({left: 200, right: 300});
            expect(scroller, 'still no fade on the right').toHaveAttribute('data-fade', 'start');
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        // red until A8b (point 33)
        it('on a click, a tab wider than the window less its fades (three, 100–380: 280 px in 0–300): the start wins — scrollLeft goes to 76, the tab starts where the left fade ends and loses its end', async () => {
            // A layout of its own: the same 480 px of tabs, tab three 280 px wide.
            geometry.tabs = {
                one: {offset: 0, width: 50},
                two: {offset: 50, width: 50},
                three: {offset: 100, width: 280},
                four: {offset: 380, width: 50},
                five: {offset: 430, width: 50},
            };
            await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller.scrollLeft, 'precondition: an active tab already inside, and clear of the fade, moved nothing').toBe(0);
            expect(edges('three'), 'precondition: tab three ends 80 px past the right edge').toEqual({left: 100, right: 380});

            await fireEvent.click(screen.getByTestId(g15TestId('three')));
            await g15DeliverFrames();

            expect(screen.getByTestId(g15TestId('three'))).toHaveAttribute('aria-selected', 'true');
            // Clearing the right fade (380 + 24 − 300 = 104) would put the start under the left one (100 < 104 + 24).
            expect(scroller.scrollLeft, 'the start wins: 100 − 24').toBe(76);
            expect(edges('three'), 'starts where the left fade ends (24); its end runs past the right edge (304 of 300)').toEqual({left: 24, right: 304});
            expect(scroller, 'tabs hidden on both sides').toHaveAttribute('data-fade', 'both');
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });
    });

    /*
     * A8b (workstream A, release 1.3; decision P13 a, the designer's point 33) — the edge fade of a scrollable bar.
     *
     * In French and Spanish an administrator's Settings bar overflows. G-15 made it scroll, but nothing yet tells the user
     * that more tabs wait past an edge. The approved cure, with `scrollable` only:
     *
     *   - the scroller, [data-testid="tab-bar-scroller"], publishes `data-fade` — `none | start | end | both` — naming the
     *     sides where the row hides something, read from its own metrics with one pixel of tolerance for rounding:
     *     `start` while `scrollLeft > 1`, `end` while `scrollLeft + clientWidth < scrollWidth − 1`;
     *   - it is recomputed on the scroller's `scroll` event; when the ResizeObserver reports the scroller or the row
     *     resized; after a change of the active tab or of the labels, once `revealActiveTab` has scrolled (in that frame
     *     or right after); and once after mount;
     *   - the fade itself is a CSS mask on the scroller, on the named sides and on no other: Tailwind 4.1's `mask-l-…` for
     *     the start, `mask-r-…` for the end. No colour: a mask fades whatever lies behind it, in every theme;
     *   - without `scrollable` nothing changes: no `data-fade` anywhere.
     *
     * The layout is the G-15 model above, a 300 px scroller over 480 px of tabs unless a case says otherwise. Like jsdom,
     * the model fires no `scroll` when the bar moves its own `scrollLeft`: a case that changes the tab or the labels
     * therefore proves the bar recomputes after its reveal, not that a browser would have told it to a frame later. A
     * user's scroll is modelled as a browser delivers it: the position moves, then `scroll` fires on the scroller. jsdom
     * loads no Tailwind, so the mask is read from the class tokens — the family (`mask-l-`, `mask-r-`), never the exact
     * utility or its size.
     *
     * Red until A8b: TabBar published no `data-fade` and drew no mask. The guard without `scrollable` was green and must
     * stay green. Point 33 (the G-15 note above) then moved every reveal that ended under a fade: the cases here that go
     * through one are red until A8b (point 33). The two that opened on tab three now open in a 320 px scroller — at 300
     * the mount itself moves the bar 4 px off the fade, and `data-fade` would read `both` before and after the change it
     * is there to follow.
     */
    describe('the edge fade (A8b, P13 a): data-fade names the sides where the bar hides tabs', () => {
        type Fade = 'none' | 'start' | 'end' | 'both';

        /** The sides the scroller masks. jsdom loads no Tailwind, so the class token is what can be observed: its family. */
        function maskedSides(scroller: HTMLElement): {start: boolean; end: boolean} {
            const classes = scroller.getAttribute('class') ?? '';
            return {start: /\bmask-l-/.test(classes), end: /\bmask-r-/.test(classes)};
        }

        /** The sides a value of `data-fade` names. */
        function namedSides(fade: Fade): {start: boolean; end: boolean} {
            return {start: fade === 'start' || fade === 'both', end: fade === 'end' || fade === 'both'};
        }

        /** Whatever carries `data-fade` inside `container`: its test id, or its tag. */
        function fadeCarriers(container: Element): string[] {
            return Array.from(container.querySelectorAll('[data-fade]'), (element) => element.getAttribute('data-testid') ?? element.tagName);
        }

        // Guard — green today, and it stays green: without `scrollable` the bar is today's.
        it('without `scrollable` (the default): no data-fade anywhere — once mounted, after a change of tab, after a change of labels', async () => {
            const {container, rerender} = await mountBar({activeTab: 'one'});

            expect(screen.getByRole('tablist'), 'presence: the bar is drawn').toBeInTheDocument();
            expect(fadeCarriers(container), 'once mounted').toEqual([]);

            await rerender({activeTab: 'five'});
            await g15DeliverFrames();
            expect(screen.getByTestId(g15TestId('five')), 'presence: the change of tab landed').toHaveAttribute('aria-selected', 'true');
            expect(fadeCarriers(container), 'after a change of tab').toEqual([]);

            await rerender({tabs: G15_TABS.map((tab) => ({...tab, label: `${tab.label} (longer)`}))});
            await g15DeliverFrames();
            expect(within(screen.getByTestId(g15TestId('five'))).getByText('Label five (longer)'), 'presence: the new labels are drawn').toBeInTheDocument();
            expect(fadeCarriers(container), 'after a change of labels').toEqual([]);
        });

        // red until A8b
        it.each([
            ['the tabs fit (a 500 px scroller over 480 px of tabs)', 'none', 500],
            ['a 1 px overflow (479 px over 480 px) is rounding, not a hidden tab', 'none', 479],
            ['the tabs overflow (300 px over 480 px) and the bar sits at scrollLeft 0', 'end', 300],
        ] as const)('once mounted, %s: data-fade="%s", on the scroller and nowhere else', async (_situation, fade, scrollerWidth) => {
            geometry.scroller.width = scrollerWidth;
            const {container} = await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller.scrollLeft, 'precondition: the active tab (0–70) is inside, nothing scrolled').toBe(0);

            expect(scroller, 'the sides where the row hides a tab').toHaveAttribute('data-fade', fade);
            expect(fadeCarriers(container), 'the scroller carries it, and nothing else — not the tablist, not a tab').toEqual(['tab-bar-scroller']);
        });

        // red until A8b
        it.each([
            ['the middle (scrollLeft 90 of 180)', 'both', 90],
            ['the end (scrollLeft 180: 180 + 300 = 480)', 'start', 180],
            ['1 px from the start — rounding, not a hidden tab', 'end', 1],
            ['1 px from the end (179 + 300 = 479) — rounding, not a hidden tab', 'start', 179],
        ] as const)('scrolled by the user to %s: data-fade="%s"', async (_where, fade, left) => {
            await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();

            await userScrollsTo(scroller, left);

            expect(scroller.scrollLeft, 'precondition: the bar stands where the user put it').toBe(left);
            expect(scroller, 'the sides where the row hides a tab').toHaveAttribute('data-fade', fade);
        });

        // red until A8b
        it("a scroll event moves it, both ways — end → start → both → end — and the scroll stays the user's: the bar does not snap back to its active tab", async () => {
            await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller, 'precondition: at scrollLeft 0, tabs hidden past the right edge').toHaveAttribute('data-fade', 'end');

            for (const [left, fade] of [
                [180, 'start'],
                [90, 'both'],
                [0, 'end'],
            ] as const) {
                await userScrollsTo(scroller, left);
                expect(scroller.scrollLeft, `scrolled to ${left}: the user's scroll stands, the active tab is not brought back`).toBe(left);
                expect(scroller, `scrolled to ${left}`).toHaveAttribute('data-fade', fade);
            }
        });

        // red until A8b
        it('a resize of the scroller moves it: narrowed from 500 to 300 px over 480 px of tabs, none → end; widened back, end → none', async () => {
            geometry.scroller.width = 500;
            await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller, 'precondition: 480 px of tabs fit in 500').toHaveAttribute('data-fade', 'none');

            // The window narrowed.
            geometry.scroller.width = 300;
            expect(g15Resized(scroller), 'a ResizeObserver watches the scroller').toBeGreaterThan(0);
            await g15DeliverFrames();
            expect(scroller.scrollLeft, 'precondition: the active tab (0–70) is still inside, nothing scrolled').toBe(0);
            expect(scroller, '480 px of tabs in 300: hidden past the right edge').toHaveAttribute('data-fade', 'end');

            // And widened again.
            geometry.scroller.width = 500;
            g15Resized(scroller);
            await g15DeliverFrames();
            expect(scroller, '480 px of tabs in 500: nothing hidden').toHaveAttribute('data-fade', 'none');
        });

        // red until A8b
        it('a resize of the row moves it: in a 500 px scroller the last label grows by 60 px (a web font arriving late), none → end', async () => {
            geometry.scroller.width = 500;
            await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller, 'precondition: 480 px of tabs fit in 500').toHaveAttribute('data-fade', 'none');

            // The scroller keeps its size; the row grows to 540 px.
            geometry.tabs.five.width += 60;
            expect(g15Resized(screen.getByRole('tablist')), 'a ResizeObserver watches the row').toBeGreaterThan(0);
            await g15DeliverFrames();

            expect(scroller, '540 px of tabs in 500: hidden past the right edge').toHaveAttribute('data-fade', 'end');
        });

        // red until A8b (point 33)
        it("a resize that makes the bar reveal its active tab (320 → 250 px; tab three, 160–280, brought in at scrollLeft 54 — the hidden part and the fade's 24 px): end → both, read after the reveal", async () => {
            // 320 px, not 300: tab three ends 40 px before the edge, clear of the fade, so the bar opens at 0 and reads `end`.
            geometry.scroller.width = 320;
            await mountBar({activeTab: 'three', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller.scrollLeft, 'precondition: tab three (160–280) is whole in view and clear of the fade (296–320): nothing scrolled').toBe(0);
            expect(scroller, 'precondition: at scrollLeft 0, tabs hidden past the right edge').toHaveAttribute('data-fade', 'end');

            geometry.scroller.width = 250;
            g15Resized(scroller);
            await g15DeliverFrames();

            expect(scroller.scrollLeft, 'precondition: the reveal brought tab three whole into view, clear of the fade: 280 + 24 − 250').toBe(54);
            expect(scroller, '54 px hidden before the left edge, 176 past the right one').toHaveAttribute('data-fade', 'both');
        });

        // red until A8b (point 33)
        it("once mounted on a tab past the edge (?tab= opening tab four, 280–380 in 0–300): data-fade follows the reveal to scrollLeft 104 — the hidden 80 px and the fade's 24 px — both", async () => {
            await mountBar({activeTab: 'four', scrollable: true});
            const scroller = scrollerOf();

            expect(scroller.scrollLeft, 'precondition: the reveal ran').toBe(104);
            expect(scroller, '104 px hidden before the left edge, 76 past the right one').toHaveAttribute('data-fade', 'both');
        });

        // red until A8b (point 33): one → four, whose reveal now ends 24 px further (80 → 104). The two others stop at an end of the row, where no fade is drawn: unchanged.
        it.each([
            ['one', 'four', 104, 'both'],
            ['one', 'five', 180, 'start'],
            ['five', 'one', 0, 'end'],
        ] as const)('when activeTab changes from %s to %s, off-screen: the reveal ends at scrollLeft %s and data-fade="%s" matches it', async (from, to, left, fade) => {
            const {rerender} = await mountBar({activeTab: from, scrollable: true});
            const scroller = scrollerOf();

            await rerender({activeTab: to});
            await g15DeliverFrames();

            expect(screen.getByTestId(g15TestId(to)), 'presence: the change of tab landed').toHaveAttribute('aria-selected', 'true');
            expect(scroller.scrollLeft, 'precondition: the reveal brought the tab whole into view').toBe(left);
            expect(scroller, `scrollLeft ${left} of 180`).toHaveAttribute('data-fade', fade);
        });

        // red until A8b (point 33)
        it("when the labels change (a language switch) and the active tab grows to 160–340 in a 320 px scroller: the reveal ends at scrollLeft 44 — the hidden part and the fade's 24 px — and data-fade follows, end → both", async () => {
            // 320 px, not 300, as in the resize case above: the bar must open at 0 for data-fade to have somewhere to go.
            geometry.scroller.width = 320;
            const {rerender} = await mountBar({activeTab: 'three', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller.scrollLeft, 'precondition: tab three (160–280) is whole in view and clear of the fade (296–320): nothing scrolled').toBe(0);
            expect(scroller, 'precondition: at scrollLeft 0, tabs hidden past the right edge').toHaveAttribute('data-fade', 'end');

            // Another language's longer labels: tab three grows by 60 px, the tabs after it move along, the row is 540 px.
            geometry.tabs.three.width += 60;
            geometry.tabs.four.offset += 60;
            geometry.tabs.five.offset += 60;
            await rerender({tabs: G15_TABS.map((tab) => ({...tab, label: `${tab.label} (longer)`}))});
            await g15DeliverFrames();

            expect(within(screen.getByTestId(g15TestId('three'))).getByText('Label three (longer)'), 'presence: the new label is drawn').toBeInTheDocument();
            expect(scroller.scrollLeft, 'precondition: the reveal brought tab three whole into view, clear of the fade: 340 + 24 − 320').toBe(44);
            expect(scroller, '44 px hidden before the left edge, 176 past the right one').toHaveAttribute('data-fade', 'both');
        });

        // red until A8b
        it('when the labels change and the row now fits (a shorter language, 300 px of tabs in 300): end → none, recomputed though nothing scrolled', async () => {
            const {rerender} = await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller, 'precondition: 480 px of tabs in 300, hidden past the right edge').toHaveAttribute('data-fade', 'end');

            // A shorter language: 50 + 60 + 80 + 60 + 50 = 300 px of tabs. No resize is announced: the change of labels alone must do.
            geometry.tabs = {
                one: {offset: 0, width: 50},
                two: {offset: 50, width: 60},
                three: {offset: 110, width: 80},
                four: {offset: 190, width: 60},
                five: {offset: 250, width: 50},
            };
            await rerender({tabs: G15_TABS.map((tab) => ({...tab, label: tab.id}))});
            await g15DeliverFrames();

            expect(within(screen.getByTestId(g15TestId('one'))).getByText('one'), 'presence: the new label is drawn').toBeInTheDocument();
            expect(scroller.scrollLeft, 'precondition: the active tab was already inside, nothing scrolled').toBe(0);
            expect(scroller, '300 px of tabs in 300: nothing hidden').toHaveAttribute('data-fade', 'none');
        });

        // red until A8b
        it('the mask sits on the sides data-fade names and on no other — mask-l-… for the start, mask-r-… for the end — and brings no colour', async () => {
            geometry.scroller.width = 500;
            const {container} = await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            const tokens = (): string[] => Array.from(scroller.classList).sort();
            expect(scroller, 'precondition: 480 px of tabs fit in 500').toHaveAttribute('data-fade', 'none');
            const unfaded = tokens();

            /** One state of the walk: the attribute is reached first, then the mask is read against it. */
            const expectMaskFor = (fade: Fade): void => {
                expect(scroller, `precondition: the bar reached "${fade}"`).toHaveAttribute('data-fade', fade);
                expect(maskedSides(scroller), `"${fade}": a mask-l-… token iff the start is named, a mask-r-… token iff the end is`).toEqual(namedSides(fade));
                const now = tokens();
                const changed = [...unfaded.filter((token) => !now.includes(token)), ...now.filter((token) => !unfaded.includes(token))];
                expect(
                    changed.filter((token) => !token.includes('mask')),
                    `"${fade}": the fade changes mask utilities and nothing else — no colour class`,
                ).toEqual([]);
                expect(scroller.getAttribute('style') ?? '', `"${fade}": no inline colour on the scroller`).not.toMatch(/colou?r|#|rgba?\(|hsla?\(|oklch\(/i);
                expect(container.childElementCount, `"${fade}": no overlay beside the scroller`).toBe(1);
                expect(scroller.childElementCount, `"${fade}": nor inside it — the fade is the scroller's own mask over its tablist`).toBe(1);
            };

            expectMaskFor('none');

            geometry.scroller.width = 300;
            g15Resized(scroller);
            await g15DeliverFrames();
            expectMaskFor('end');

            await userScrollsTo(scroller, 90);
            expectMaskFor('both');

            await userScrollsTo(scroller, 180);
            expectMaskFor('start');

            await userScrollsTo(scroller, 0);
            geometry.scroller.width = 500;
            g15Resized(scroller);
            await g15DeliverFrames();
            expectMaskFor('none');
            expect(tokens(), 'back to "none": the scroller wears the classes it started with').toEqual(unfaded);
        });
    });
});

/*
 * A8b (badge hook) — a tab's badge publishes a test hook.
 *
 * The Settings bar now carries badges that count — the Administration group shows the sum of its members', the
 * Security tab the checks that ask for attention — and the tests of that page must read one without a class or a
 * position. Contract: when a tab's `badge` is a number > 0, the badge element inside that tab's button carries
 * `data-testid="tab-badge"` and `data-badge="<the number>"`, its visible text staying the number; no badge (undefined,
 * null, 0) → no `tab-badge` element in that button. `tab-badge` names a kind, not an instance: a hook is always reached
 * through its own tab's button, never by an index.
 *
 * `null` is not exercised: `TabItem.badge` is `number | undefined`, and the Settings page always passes a number (0 for
 * none) — a null would need a cast to reach the bar.
 *
 * Red until A8b (badge hook): the badge is a bare <span> with neither attribute. The absence case is red as well, on its
 * presence barrier — in a bar that draws no hook at all, «none here» would hold for the wrong reason.
 */
describe('TabBar — the badge hook (A8b): data-testid="tab-badge" and data-badge, inside its own tab', () => {
    /** Four tabs, labelled and counted by this file: badges 3 and 12, one at 0, one without. */
    const BADGE_TABS: TabItem[] = [
        {id: 'alerts', label: 'Alerts', badge: 3, testId: 'tab-alerts'},
        {id: 'quiet', label: 'Quiet', badge: 0, testId: 'tab-quiet'},
        {id: 'plain', label: 'Plain', testId: 'tab-plain'},
        {id: 'queue', label: 'Queue', badge: 12, testId: 'tab-queue'},
    ];

    /** The hook inside the button of `tabTestId`, reached through that button; null when it holds none. */
    function badgeIn(tabTestId: string): HTMLElement | null {
        return within(screen.getByTestId(tabTestId)).queryByTestId('tab-badge');
    }

    // red until A8b (badge hook)
    it('badge 3: the badge inside that tab button carries data-testid="tab-badge" and data-badge="3", and still reads 3', () => {
        render(TabBar, {tabs: BADGE_TABS, activeTab: 'quiet'});

        const badge = badgeIn('tab-alerts');
        expect(badge, 'a tab with badge 3 holds [data-testid="tab-badge"] inside its own button').not.toBeNull();
        expect(badge, 'the number, for a test to read').toHaveAttribute('data-badge', '3');
        expect(badge, 'and the visible text stays the number').toHaveTextContent(/^3$/);
    });

    // red until A8b (badge hook) — on its presence barrier
    it('badge 0, and no badge at all: no tab-badge inside those buttons — beside a tab whose badge 3 has its hook', () => {
        render(TabBar, {tabs: BADGE_TABS, activeTab: 'quiet'});

        // Presence first: this bar draws hooks, so each absence below is about its own tab.
        expect(badgeIn('tab-alerts'), 'presence barrier: the badged tab beside them carries its hook').not.toBeNull();
        for (const [testId, why] of [
            ['tab-quiet', 'badge 0'],
            ['tab-plain', 'no badge (undefined)'],
        ] as const) {
            expect(badgeIn(testId), `${why}: no [data-testid="tab-badge"] inside ${testId}`).toBeNull();
        }
    });

    // red until A8b (badge hook)
    it('two badges, 3 and 12: each hook is reached through its own tab button and carries its own number — every hook in the bar belongs to a badged tab', () => {
        render(TabBar, {tabs: BADGE_TABS, activeTab: 'quiet'});

        for (const [testId, count] of [
            ['tab-alerts', '3'],
            ['tab-queue', '12'],
        ] as const) {
            const badge = badgeIn(testId);
            expect(badge, `${testId}: the hook sits inside its own button`).not.toBeNull();
            expect(badge, `${testId}: its own number, not a neighbour's`).toHaveAttribute('data-badge', count);
            expect(badge, `${testId}: the visible text stays the number`).toHaveTextContent(new RegExp(`^${count}$`));
        }
        // Every hook in the bar, traced to the tab that holds it — by ownership, not by order.
        const owners = screen.queryAllByTestId('tab-badge').map((badge) => badge.closest('[role="tab"]')?.getAttribute('data-testid'));
        expect(owners.sort(), 'one hook per badged tab, none in the others').toEqual(['tab-alerts', 'tab-queue']);
    });
});
