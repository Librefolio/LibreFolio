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
 *     button's with `getBoundingClientRect()`, and moves the scroller's own `scrollLeft` — never the page — by exactly
 *     what is hidden: `scrollLeft -= scroller.left − tab.left` when the tab starts left of the scroller,
 *     `scrollLeft += tab.right − scroller.right` when it ends right of it, nothing when it is inside;
 *   - without it the markup is exactly today's — no scroller, the tablist is the root — and nothing ever scrolls: the
 *     five other places that draw a TabBar keep their bar.
 *
 * jsdom lays nothing out, so the layout is a model this file owns (`G15Geometry`): the scroller's box and the place
 * of each tab in the row. A tab's box slides left as the scroller scrolls right, as in a browser, so a reveal that
 * runs twice lands where one would: a red names wrong arithmetic, not a stale mock. Animation frames and resize
 * notifications are owned too — a frame is delivered, a resize announced, only when a case says so. Overflow on the
 * real page, in a real language, is the E2E's (`e2e/settings.spec.ts`, «G-15»).
 *
 * Red today: TabBar has no `scrollable` prop, never draws `tab-bar-scroller`, and every case that needs the scroller
 * fails on its absence. The two guards — today's markup without the prop, nothing scrolled without it — are green
 * now and must stay green.
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
 * `scrollLeft` 0 the first three are inside, four ends 80 px past the right edge and five lies wholly past it.
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

    describe('the active tab is kept whole in view (a 300 px scroller over 480 px of tabs, modelled)', () => {
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

        it('on mount, as ?tab= opens the page: an active tab 80 px past the right edge (280–380 in 0–300) brings scrollLeft from 0 to 80', async () => {
            await mountBar({activeTab: 'four', scrollable: true});
            const scroller = scrollerOf();

            expect(scroller.scrollLeft, 'the hidden 80 px, and no more').toBe(80);
            expect(edges('four'), 'whole in view, flush with the right edge').toEqual({left: 200, right: 300});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        it('when activeTab changes to a tab 80 px past the right edge (280–380 in 0–300): scrollLeft grows by exactly 80', async () => {
            const {rerender} = await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller.scrollLeft, 'precondition: an active tab already inside moved nothing').toBe(0);
            expect(edges('four'), 'precondition: tab four ends 80 px past the scroller').toEqual({left: 280, right: 380});

            await rerender({activeTab: 'four'});
            await g15DeliverFrames();

            expect(scroller.scrollLeft, 'the hidden 80 px, and no more').toBe(80);
            expect(edges('four'), 'whole in view, flush with the right edge').toEqual({left: 200, right: 300});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        it('when activeTab changes to a tab already inside (120–240 at scrollLeft 40): scrollLeft stays 40', async () => {
            const {rerender} = await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            // The user scrolled the bar a little.
            scroller.scrollLeft = 40;
            expect(edges('three'), 'precondition: tab three lies inside the scroller').toEqual({left: 120, right: 240});

            await rerender({activeTab: 'three'});
            await g15DeliverFrames();

            expect(screen.getByTestId(g15TestId('three'))).toHaveAttribute('aria-selected', 'true');
            expect(scroller.scrollLeft, 'a tab already whole in view moves nothing').toBe(40);
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        it('when activeTab changes to a tab 50 px past the left edge (−50–40 at scrollLeft 120): scrollLeft comes back to 70', async () => {
            const {rerender} = await mountBar({activeTab: 'four', scrollable: true});
            const scroller = scrollerOf();
            // The bar is scrolled right, as after the last tabs were opened.
            scroller.scrollLeft = 120;
            expect(edges('two'), 'precondition: tab two starts 50 px before the scroller').toEqual({left: -50, right: 40});

            await rerender({activeTab: 'two'});
            await g15DeliverFrames();

            expect(scroller.scrollLeft, 'back by the hidden 50 px, and no more').toBe(70);
            expect(edges('two'), 'whole in view, flush with the left edge').toEqual({left: 0, right: 90});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        it('on a click, the user picking a tab wholly past the right edge (380–480 in 0–300): scrollLeft goes to 180', async () => {
            await mountBar({activeTab: 'one', scrollable: true});
            const scroller = scrollerOf();
            expect(edges('five'), 'precondition: tab five lies wholly past the scroller').toEqual({left: 380, right: 480});

            await fireEvent.click(screen.getByTestId(g15TestId('five')));
            await g15DeliverFrames();

            expect(screen.getByTestId(g15TestId('five'))).toHaveAttribute('aria-selected', 'true');
            expect(scroller.scrollLeft, 'the hidden 180 px, and no more').toBe(180);
            expect(edges('five'), 'whole in view, flush with the right edge').toEqual({left: 200, right: 300});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        it('when the scroller is resized (300 → 250 px) and the active tab (160–280) now ends 30 px past it: scrollLeft goes to 30', async () => {
            await mountBar({activeTab: 'three', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller.scrollLeft, 'precondition: tab three fits a 300 px scroller').toBe(0);

            // The window narrowed.
            geometry.scroller.width = 250;
            expect(g15Resized(scroller), 'a ResizeObserver watches the scroller').toBeGreaterThan(0);
            await g15DeliverFrames();

            expect(scroller.scrollLeft, 'the hidden 30 px, and no more').toBe(30);
            expect(edges('three'), 'whole in view, flush with the right edge').toEqual({left: 130, right: 250});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });

        it('when the labels change (a language switch) and the active tab grows to 160–340: scrollLeft goes to 40', async () => {
            const {rerender} = await mountBar({activeTab: 'three', scrollable: true});
            const scroller = scrollerOf();
            expect(scroller.scrollLeft, 'precondition: tab three (160–280) fits a 300 px scroller').toBe(0);

            // Another language's longer labels: tab three grows by 60 px, and the tabs after it move along.
            geometry.tabs.three.width += 60;
            geometry.tabs.four.offset += 60;
            geometry.tabs.five.offset += 60;
            await rerender({tabs: G15_TABS.map((tab) => ({...tab, label: `${tab.label} (longer)`}))});
            await g15DeliverFrames();

            expect(within(screen.getByTestId(g15TestId('three'))).getByText('Label three (longer)'), 'presence: the new label is drawn').toBeInTheDocument();
            expect(scroller.scrollLeft, 'the hidden 40 px, and no more').toBe(40);
            expect(edges('three'), 'whole in view, flush with the right edge').toEqual({left: 120, right: 300});
            expect(pageScrolls, 'the page is never scrolled').toEqual([]);
        });
    });
});
