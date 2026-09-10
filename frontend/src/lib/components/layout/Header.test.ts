// @vitest-environment jsdom
/**
 * State-machine wiring, not a pretend layout engine. Header, HelpMenu,
 * LanguageSelector, ThemeToggle and the document-scroll helper are real.
 * Only browser measurements, observers and animation-frame delivery are owned.
 * Real sticky/transform/reduced-motion geometry lives in header-scroll.spec.ts.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {tick} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import Header from './Header.svelte';

let scrollY: number;
let measuredHeight: number;
let nextFrame: number;
let frames: Map<number, FrameRequestCallback>;
let resizeObservers: ControlledResizeObserver[];
let mutationObservers: ControlledMutationObserver[];
let restoreDescriptors: Array<() => void>;
let previousModalCount: string | null;
let outside: HTMLButtonElement;

class ControlledResizeObserver implements ResizeObserver {
    readonly targets = new Set<Element>();
    readonly disconnect = vi.fn(() => this.targets.clear());
    constructor(readonly callback: ResizeObserverCallback) {
        resizeObservers.push(this);
    }
    observe(target: Element) {
        this.targets.add(target);
    }
    unobserve(target: Element) {
        this.targets.delete(target);
    }
    deliver() {
        this.callback([], this);
    }
}

class ControlledMutationObserver implements MutationObserver {
    readonly targets = new Map<Node, MutationObserverInit>();
    readonly disconnect = vi.fn(() => this.targets.clear());
    constructor(readonly callback: MutationCallback) {
        mutationObservers.push(this);
    }
    observe(target: Node, options: MutationObserverInit) {
        this.targets.set(target, options);
    }
    takeRecords(): MutationRecord[] {
        return [];
    }
    deliver() {
        this.callback([], this);
    }
}

function ownProperty(target: object, name: string, descriptor: PropertyDescriptor) {
    const previous = Object.getOwnPropertyDescriptor(target, name);
    Object.defineProperty(target, name, {configurable: true, ...descriptor});
    restoreDescriptors.push(() => {
        if (previous) Object.defineProperty(target, name, previous);
        else Reflect.deleteProperty(target, name);
    });
}

function header() {
    return screen.getByTestId('app-header');
}

function expectState(state: 'visible' | 'hidden' | 'pinned') {
    expect(header()).toHaveAttribute('data-scroll-state', state);
}

async function deliverFrames() {
    // Deliver the queued browser turn, not an arbitrary amount of elapsed time.
    // A newly scheduled frame is left pending for the next explicit delivery.
    const queued = [...frames.entries()];
    for (const [id, callback] of queued) {
        if (!frames.delete(id)) continue;
        callback(0);
    }
    await tick();
}

async function scrollTo(y: number, target: Window | Document | HTMLElement = window) {
    scrollY = y;
    target.dispatchEvent(new Event('scroll'));
    await deliverFrames();
}

async function mount(props: ComponentProps<typeof Header> = {}) {
    const result = render(Header, props);
    await tick();
    expect(header()).toBeInTheDocument();
    return result;
}

function ownResizeObserver() {
    const observer = resizeObservers.find((entry) => entry.targets.has(header()));
    if (!observer) throw new Error('Header did not observe its own size');
    return observer;
}

function ownModalObserver() {
    const observer = mutationObservers.find((entry) => entry.targets.get(document.body)?.attributeFilter?.includes('data-modal-scroll-lock-count'));
    if (!observer) throw new Error('Header did not observe the body modal-lock counter');
    return observer;
}

async function setModalCount(count: number) {
    document.body.setAttribute('data-modal-scroll-lock-count', String(count));
    ownModalObserver().deliver();
    await tick();
}

beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => {
    scrollY = 100;
    measuredHeight = 64;
    nextFrame = 0;
    frames = new Map();
    resizeObservers = [];
    mutationObservers = [];
    restoreDescriptors = [];
    previousModalCount = document.body.getAttribute('data-modal-scroll-lock-count');
    document.body.removeAttribute('data-modal-scroll-lock-count');
    ownProperty(window, 'scrollY', {get: () => scrollY});
    ownProperty(window, 'innerHeight', {value: 800});
    ownProperty(document, 'scrollingElement', {get: () => document.documentElement});
    ownProperty(document.documentElement, 'scrollHeight', {value: 3000});
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
        const id = ++nextFrame;
        frames.set(id, callback);
        return id;
    });
    vi.stubGlobal('cancelAnimationFrame', (id: number) => frames.delete(id));
    vi.stubGlobal('ResizeObserver', ControlledResizeObserver);
    vi.stubGlobal('MutationObserver', ControlledMutationObserver);
    vi.stubGlobal('localStorage', {getItem: () => null, setItem: vi.fn(), removeItem: vi.fn()});
    const originalRect = HTMLElement.prototype.getBoundingClientRect;
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
        if (this.getAttribute('data-testid') !== 'app-header') return originalRect.call(this);
        return {x: 0, y: 0, top: 0, left: 0, right: 1000, bottom: measuredHeight, width: 1000, height: measuredHeight, toJSON: () => ({})};
    });
    outside = document.createElement('button');
    outside.dataset.testid = 'review-header-outside';
    document.body.append(outside);
});
afterEach(() => {
    cleanup();
    outside.remove();
    if (previousModalCount === null) document.body.removeAttribute('data-modal-scroll-lock-count');
    else document.body.setAttribute('data-modal-scroll-lock-count', previousModalCount);
    for (const restore of restoreDescriptors.reverse()) restore();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe('Header document scroll thresholds', () => {
    it('accumulates small downward deltas to 8px and upward deltas to 4px', async () => {
        await mount();
        expectState('visible');
        for (const y of [102, 105, 107]) {
            await scrollTo(y);
            expectState('visible');
        }
        await scrollTo(108);
        expectState('hidden');
        await scrollTo(106);
        expectState('hidden');
        await scrollTo(105);
        expectState('hidden');
        await scrollTo(104);
        expectState('visible');
    });

    it('resets accumulated intent when direction reverses', async () => {
        await mount();
        await scrollTo(107);
        await scrollTo(106);
        await scrollTo(107);
        expectState('visible');
        await scrollTo(114);
        expectState('hidden');
        await scrollTo(112);
        await scrollTo(113);
        await scrollTo(111);
        expectState('hidden');
        await scrollTo(109);
        expectState('visible');
    });

    it('keeps the inclusive header-height top zone visible and restarts accumulation on leaving it', async () => {
        scrollY = 0;
        await mount();
        await scrollTo(64);
        expectState('visible');
        await scrollTo(65);
        await scrollTo(71);
        expectState('visible');
        await scrollTo(72);
        expectState('hidden');
        await scrollTo(64);
        expectState('visible');
    });

    it('rounds a fractional measured height upward for the top-zone boundary', async () => {
        scrollY = 0;
        measuredHeight = 64.2;
        await mount();
        await scrollTo(65);
        expectState('visible');
        await scrollTo(73);
        expectState('hidden');
    });

    it('clamps rubber-band overscroll so returning from the bottom is not a false upward gesture', async () => {
        scrollY = 2190;
        await mount();
        await scrollTo(2300); // Actual maximum is 3000 - 800 = 2200.
        expectState('hidden');
        await scrollTo(2200);
        expectState('hidden');
        await scrollTo(2197);
        expectState('hidden');
        await scrollTo(2196);
        expectState('visible');
        await scrollTo(-100);
        expectState('visible');
        await scrollTo(0);
        expectState('visible');
    });

    it('coalesces window events, accepts document scroll, and ignores native nested scroll', async () => {
        await mount();
        const nested = document.createElement('div');
        outside.append(nested);
        scrollY = 108;
        nested.dispatchEvent(new Event('scroll'));
        expect(frames.size).toBe(0);
        expectState('visible');

        window.dispatchEvent(new Event('scroll'));
        window.dispatchEvent(new Event('scroll'));
        expect(frames.size).toBe(1);
        await deliverFrames();
        expectState('hidden');

        scrollY = 104;
        // Browser document scroll bubbles to window; element scroll does not.
        document.dispatchEvent(new Event('scroll', {bubbles: true}));
        await deliverFrames();
        expectState('visible');
    });
});

describe('Header visibility pins', () => {
    it.each(['sidebarOpen', 'keepVisible'] as const)('pins on %s and establishes a fresh baseline on release', async (prop) => {
        const mounted = await mount();
        await scrollTo(108);
        expectState('hidden');
        await mounted.rerender({[prop]: true});
        expectState('pinned');
        if (prop === 'sidebarOpen') expect(header()).toHaveAttribute('data-sidebar-open', 'true');
        await scrollTo(200);
        expectState('pinned');
        await mounted.rerender({[prop]: false});
        expectState('visible');
        await scrollTo(207);
        expectState('visible');
        await scrollTo(208);
        expectState('hidden');
    });

    it('delegates the sidebar toggle rather than claiming a controlled prop changed', async () => {
        const onToggleSidebar = vi.fn();
        const mounted = await mount({onToggleSidebar});
        await fireEvent.click(within(header()).getByTestId('mobile-menu-toggle'));
        expect(onToggleSidebar).toHaveBeenCalledTimes(1);
        expect(header()).toHaveAttribute('data-sidebar-open', 'false');
        await mounted.rerender({sidebarOpen: true});
        expect(header()).toHaveAttribute('data-sidebar-open', 'true');
        expectState('pinned');
    });

    it.each([
        {button: 'help-menu-button', panel: 'help-menu-panel', attribute: 'data-help-menu-open'},
        {button: 'language-selector-button', panel: 'language-selector-panel', attribute: 'data-language-menu-open'},
    ])('pins while $panel is open and releases after closing', async ({button, panel, attribute}) => {
        await mount();
        await scrollTo(108);
        expectState('hidden');
        // fireEvent intentionally does not focus: menu callbacks, not the
        // independent focus pin, are the subject here.
        await fireEvent.click(within(header()).getByTestId(button));
        expect(screen.getByTestId(panel)).toBeVisible();
        expect(header()).toHaveAttribute(attribute, 'true');
        expect(header()).toHaveAttribute('data-menu-open', 'true');
        expectState('pinned');
        await scrollTo(200);
        expectState('pinned');
        await fireEvent.click(within(header()).getByTestId(button));
        expect(screen.queryByTestId(panel)).toBeNull();
        expect(header()).toHaveAttribute(attribute, 'false');
        expect(header()).toHaveAttribute('data-menu-open', 'false');
        expectState('visible');
        await scrollTo(208);
        expectState('hidden');
    });

    it('releases LanguageSelector on Escape and HelpMenu on an outside click', async () => {
        await mount();
        await fireEvent.click(within(header()).getByTestId('language-selector-button'));
        expect(screen.getByTestId('language-selector-panel')).toBeVisible();
        expectState('pinned');
        await fireEvent.keyDown(document, {key: 'Escape'});
        expect(screen.queryByTestId('language-selector-panel')).toBeNull();
        expectState('visible');
        await fireEvent.click(within(header()).getByTestId('help-menu-button'));
        expect(screen.getByTestId('help-menu-panel')).toBeVisible();
        await fireEvent.click(outside);
        expect(screen.queryByTestId('help-menu-panel')).toBeNull();
        expectState('visible');
    });

    it('keeps focus pinned across controls, then releases only after focus leaves the header', async () => {
        await mount();
        const controls = within(header());
        controls.getByTestId('theme-toggle').focus();
        await tick();
        expectState('pinned');
        await scrollTo(180);
        expectState('pinned');
        controls.getByTestId('help-menu-button').focus();
        await deliverFrames();
        expectState('pinned');
        outside.focus();
        await deliverFrames();
        expect(outside).toHaveFocus();
        expectState('visible');
        await scrollTo(188);
        expectState('hidden');
    });

    it('reads pre-existing modal locks and retains the pin until the last modal closes', async () => {
        document.body.setAttribute('data-modal-scroll-lock-count', '2');
        await mount();
        expect(ownModalObserver().targets.get(document.body)).toEqual({
            attributes: true,
            attributeFilter: ['data-modal-scroll-lock-count'],
        });
        expectState('pinned');
        expect(header()).toHaveAttribute('data-modal-open', 'true');
        await scrollTo(180);
        await setModalCount(1);
        expectState('pinned');
        await setModalCount(0);
        expectState('visible');
        expect(header()).toHaveAttribute('data-modal-open', 'false');
        await scrollTo(188);
        expectState('hidden');
        await setModalCount(1);
        expectState('pinned');
    });

    it('does not release one pin while another still applies', async () => {
        const mounted = await mount({sidebarOpen: true});
        await setModalCount(1);
        await mounted.rerender({sidebarOpen: false});
        expectState('pinned');
        expect(header()).toHaveAttribute('data-sidebar-open', 'false');
        expect(header()).toHaveAttribute('data-modal-open', 'true');
        await setModalCount(0);
        expectState('visible');
    });
});

describe('Header navigation, resizing and teardown', () => {
    it('resets pending scroll intent on route change and starts from the current document offset', async () => {
        const mounted = await mount({routeKey: '/review/first'});
        await scrollTo(108);
        expectState('hidden');
        scrollY = 150;
        window.dispatchEvent(new Event('scroll'));
        expect(frames.size).toBe(1);
        await mounted.rerender({routeKey: '/review/second?tab=owned'});
        expect(frames.size).toBe(0);
        expectState('visible');
        await scrollTo(157);
        expectState('visible');
        await scrollTo(158);
        expectState('hidden');
    });

    it('uses a newly observed height and resets even when a resize reports the same height', async () => {
        await mount();
        const observer = ownResizeObserver();
        await scrollTo(108);
        expectState('hidden');
        measuredHeight = 120;
        observer.deliver();
        await tick();
        expectState('visible');
        await scrollTo(120);
        expectState('visible');
        await scrollTo(128);
        expectState('hidden');
        observer.deliver();
        await tick();
        expectState('visible');
    });

    it('resets on window resize even without a header ResizeObserver notification', async () => {
        await mount();
        await scrollTo(108);
        expectState('hidden');
        window.dispatchEvent(new Event('resize'));
        await tick();
        expectState('visible');
        await scrollTo(115);
        expectState('visible');
        await scrollTo(116);
        expectState('hidden');
    });

    it('removes its listeners, disconnects observers and cancels both pending frame kinds on unmount', async () => {
        const addWindow = vi.spyOn(window, 'addEventListener');
        const removeWindow = vi.spyOn(window, 'removeEventListener');
        const addDocument = vi.spyOn(document, 'addEventListener');
        const removeDocument = vi.spyOn(document, 'removeEventListener');
        const mounted = await mount();
        const resize = ownResizeObserver();
        const modal = ownModalObserver();
        within(header()).getByTestId('theme-toggle').focus();
        await tick();
        outside.focus(); // Queues a focus recheck.
        window.dispatchEvent(new Event('scroll')); // Queues a scroll frame.
        expect(frames.size).toBe(2);
        mounted.unmount();
        expect(screen.queryByTestId('app-header')).toBeNull();
        expect(resize.disconnect).toHaveBeenCalledTimes(1);
        expect(modal.disconnect).toHaveBeenCalledTimes(1);
        expect(frames.size).toBe(0);
        for (const type of ['scroll', 'resize']) {
            const registration = addWindow.mock.calls.find(([eventType]) => eventType === type);
            expect(registration).toBeDefined();
            expect(removeWindow).toHaveBeenCalledWith(type, registration?.[1]);
        }
        for (const type of ['focusin', 'focusout']) {
            const registration = addDocument.mock.calls.find(([eventType]) => eventType === type);
            expect(registration).toBeDefined();
            expect(removeDocument).toHaveBeenCalledWith(type, registration?.[1], true);
        }
        window.dispatchEvent(new Event('scroll'));
        window.dispatchEvent(new Event('resize'));
        outside.focus();
        await tick();
        expect(frames.size).toBe(0);
    });
});
