// @vitest-environment jsdom
/**
 * State-machine wiring, not a pretend layout engine. Header, HelpMenu,
 * LanguageSelector, ThemeToggle and the document-scroll helper are real.
 * Only browser measurements, observers, animation-frame delivery and the
 * `:focus-visible` verdict the focus pin reads (ownFocusVisible) are owned.
 * Real sticky/transform/reduced-motion geometry, and the focus kind Chrome
 * gives a real click and a real Tab, live in header-scroll.spec.ts.
 *
 * The menu dot of N69b (an administrator's security attention) is the last
 * describe. The checks' store it reads is a fake for the whole file, idle and
 * empty unless a case says otherwise (see `securityStore` below).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import type {ComponentProps} from 'svelte';
import {flushSync, tick} from 'svelte';
import {addMessages} from 'svelte-i18n';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import Header from './Header.svelte';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
import {get} from 'svelte/store';
import {connectionSecurity, refreshConnectionSecurity, resetConnectionSecurity, type LocationLike} from '$lib/stores/app/connectionSecurityStore';
import type {ConnectionLevel, ServerView} from '$lib/utils/security/connectionSecurity';
import {auth} from '$lib/stores/app/auth';
import {zodiosApi} from '$lib/api';
import {_ as formatMessage} from '$lib/i18n';

/** A finding of the Security tab, as the store lists it (`securityFindings.ts`). */
interface FakeFinding {
    id: string;
    severity: 'error' | 'warning' | 'info';
    messageKey: string;
    params: Record<string, string | number>;
    source: 'server' | 'browser';
}

/**
 * The checks' store (`$lib/features/settings/security/securityChecks.svelte`), faked over a `$state` box (`reactiveBox`)
 * so the header re-renders when a case lands an answer — the real one is a module singleton nothing can reset between
 * cases. One source of truth, the answer's attention findings: `findings`, `attentionCount` (errors and warnings) and
 * `attentionSeverity` (error, else warning, else null) derive from it as the real store derives them, empty and `null`
 * before the answer. `ensureLoaded` and `reload` are spies that never answer (a case lands the answer itself), so «the
 * header never asks» is a counted call; `ensureLoaded` reads the status and, from idle, starts a request, as the real one.
 */
const securityStore = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const state = reactiveBox<{status: 'idle' | 'loading' | 'ready' | 'error'; answered: boolean; attention: FakeFinding[]}>({status: 'idle', answered: false, attention: []});
    const ensureLoaded = vi
        .fn((): Promise<void> => {
            if (state.status === 'idle' || state.status === 'error') state.status = 'loading';
            return Promise.resolve();
        })
        .mockName('securityChecks.ensureLoaded');
    const reload = vi
        .fn((): Promise<void> => {
            state.status = 'loading';
            return Promise.resolve();
        })
        .mockName('securityChecks.reload');
    const counted = (): FakeFinding[] => (state.answered ? state.attention.filter((finding) => finding.severity === 'error' || finding.severity === 'warning') : []);
    const store = {
        get status() {
            return state.status;
        },
        get checks(): never[] {
            return [];
        },
        get answered() {
            return state.answered;
        },
        get findings(): {attention: FakeFinding[]; passed: FakeFinding[]} {
            return {attention: state.answered ? state.attention : [], passed: []};
        },
        get attentionCount(): number {
            return counted().length;
        },
        get attentionSeverity(): 'error' | 'warning' | null {
            const found = counted();
            if (found.some((finding) => finding.severity === 'error')) return 'error';
            return found.length > 0 ? 'warning' : null;
        },
        ensureLoaded,
        reload,
    };
    return {state, ensureLoaded, reload, store};
});

vi.mock('$lib/features/settings/security/securityChecks.svelte', () => ({securityChecks: securityStore.store}));

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

type FocusKind = 'keyboard' | 'pointer' | 'unsupported';

/**
 * Owns the browser's verdict on `:focus-visible`, which decides the focus pin. jsdom computes it with a heuristic that
 * reads the last mouse or keyboard event its window recorded — a `fireEvent.click` of an earlier test in this file
 * included — so, left to jsdom, the same `focus()` is visible or not depending on test order. The kind is stated
 * instead: `keyboard`, the focused element matches (a focus by Tab); `pointer`, nothing matches (the focus Chrome
 * leaves on a clicked button); `unsupported`, the selector throws, as in an engine that cannot parse it. Every other
 * selector reaches jsdom unchanged, and afterEach's `vi.restoreAllMocks()` hands `matches` back. Call it once per test;
 * `kind` may change mid-test, and `asked` lists every element the question was put to.
 */
function ownFocusVisible(kind: FocusKind): {kind: FocusKind; asked: Element[]} {
    const jsdomMatches = Element.prototype.matches;
    if (vi.isMockFunction(jsdomMatches)) throw new Error(':focus-visible is already owned in this test: change its `kind` instead');
    const verdict = {kind, asked: [] as Element[]};
    vi.spyOn(Element.prototype, 'matches').mockImplementation(function (this: Element, selectors: string) {
        if (selectors !== ':focus-visible') return jsdomMatches.call(this, selectors);
        verdict.asked.push(this);
        if (verdict.kind === 'unsupported') throw new DOMException(`'${selectors}' is not a valid selector`, 'SyntaxError');
        return verdict.kind === 'keyboard' && this === document.activeElement;
    });
    return verdict;
}

beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => {
    guideAnchors.clear();
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
    guideAnchors.clear();
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
    it.each(['sidebarOpen', 'keepVisible', 'guideActive'] as const)('pins on %s and establishes a fresh baseline on release', async (prop) => {
        const mounted = await mount();
        await scrollTo(108);
        expectState('hidden');
        await mounted.rerender({[prop]: true});
        expectState('pinned');
        if (prop === 'sidebarOpen') expect(header()).toHaveAttribute('data-sidebar-open', 'true');
        if (prop === 'guideActive') expect(header()).toHaveAttribute('data-guide-active', 'true');
        await scrollTo(200);
        expectState('pinned');
        await mounted.rerender({[prop]: false});
        expectState('visible');
        if (prop === 'guideActive') expect(header()).toHaveAttribute('data-guide-active', 'false');
        await scrollTo(207);
        expectState('visible');
        await scrollTo(208);
        expectState('hidden');
    });

    it('guideActive publishes data-guide-active even while unpinned, and pins through a downward scroll that would otherwise hide the header', async () => {
        const mounted = await mount({guideActive: false});
        expect(header()).toHaveAttribute('data-guide-active', 'false');

        await mounted.rerender({guideActive: true});
        expect(header()).toHaveAttribute('data-guide-active', 'true');
        expectState('pinned');

        // A downward scroll that would normally cross both hide thresholds must
        // still leave the header pinned, not hidden, while the guide is active.
        await scrollTo(108);
        expectState('pinned');
        await scrollTo(200);
        expectState('pinned');

        await mounted.rerender({guideActive: false});
        expect(header()).toHaveAttribute('data-guide-active', 'false');
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

    it('registers the mobile menu toggle as the responsive onboarding anchor and removes it on unmount', async () => {
        const mounted = await mount();
        const toggle = within(header()).getByTestId('mobile-menu-toggle');

        expect(guideAnchors.get('nav.toggle.mobile')).toBe(toggle);
        expect(guideAnchors.get('nav.toggle.desktop')).toBeNull();

        mounted.unmount();

        expect(guideAnchors.get('nav.toggle.mobile')).toBeNull();
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

    it('keeps keyboard focus pinned across controls, then releases only after focus leaves the header', async () => {
        // The focus a Tab gives, stated rather than left to jsdom's order-dependent heuristic (ownFocusVisible).
        ownFocusVisible('keyboard');
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

    it('does not pin on a focus the browser does not show (a mouse click), so the header still hides', async () => {
        const focusVisible = ownFocusVisible('pointer');
        await mount();
        const controls = within(header());
        const theme = controls.getByTestId('theme-toggle');
        theme.focus();
        await tick();
        expect(theme).toHaveFocus();
        // Presence barrier: the header put the question and was told no, so the missing pin is its answer and not a
        // focus it never saw.
        expect(focusVisible.asked).toContain(theme);
        expectState('visible');
        await scrollTo(108);
        expectState('hidden');
        // A move inside the header goes through the focus recheck, which applies the same rule.
        const help = controls.getByTestId('help-menu-button');
        help.focus();
        expect(frames.size, 'the move queued the focus recheck').toBe(1);
        await deliverFrames();
        expect(help).toHaveFocus();
        expectState('hidden');
        // The sibling control: the same wiring pins as soon as the browser shows the focus.
        focusVisible.kind = 'keyboard';
        theme.focus();
        await tick();
        expectState('pinned');
    });

    it('keeps the old rule where the engine cannot read :focus-visible: any focus inside the header pins it', async () => {
        const focusVisible = ownFocusVisible('unsupported');
        await mount();
        await scrollTo(108);
        expectState('hidden');
        const controls = within(header());
        const theme = controls.getByTestId('theme-toggle');
        theme.focus();
        await tick();
        // Presence barrier: the header put the question and the engine threw, so the pin is the fallback's.
        expect(focusVisible.asked).toContain(theme);
        expectState('pinned');
        await scrollTo(200);
        expectState('pinned');
        // The focus recheck after a move inside the header falls back the same way.
        controls.getByTestId('help-menu-button').focus();
        await deliverFrames();
        expectState('pinned');
        outside.focus();
        await deliverFrames();
        expect(outside).toHaveFocus();
        expectState('visible');
        await scrollTo(208);
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

/**
 * The menu dot — plan 36 (§2.2). On a phone the sidebar, and with it the connection-security line, hides behind the
 * burger; when the level is `insecure` the header says so on the burger itself: `mobile-menu-security-dot`, inside
 * `mobile-menu-toggle`. Secure and local draw nothing.
 *
 * The store is the real one, primed as a page load leaves it (`refreshConnectionSecurity` with an injected location
 * and server answer, `force`), and its level is a premise checked before the header is read: an absent dot means
 * something only once the store is known to hold a level that draws none. The header never asks the server itself
 * (the sidebar's line does), so nothing here reaches the network. Written RED-FIRST against the stubs of plan 36.
 */
describe('Header menu security dot (plan 36)', () => {
    async function primeConnection(location: LocationLike, answer: ServerView): Promise<void> {
        resetConnectionSecurity();
        await refreshConnectionSecurity({location, fetchServerView: () => Promise.resolve(answer), force: true});
    }

    /** The dot, looked for inside the burger only. */
    function menuDot(): HTMLElement | null {
        return within(within(header()).getByTestId('mobile-menu-toggle')).queryByTestId('mobile-menu-security-dot');
    }

    beforeEach(() => {
        resetConnectionSecurity();
    });
    afterEach(() => {
        resetConnectionSecurity();
    });

    it('insecure: the dot sits inside the menu toggle', async () => {
        await primeConnection({protocol: 'http:', hostname: 'lf.example'}, {clientClass: 'public', cookieSecure: false});
        expect(get(connectionSecurity).level, 'premise: the store holds insecure').toBe('insecure');

        await mount();

        expect(menuDot(), 'an insecure connection marks the burger').not.toBeNull();
    });

    const NO_DOT: Array<{name: string; level: ConnectionLevel; location: LocationLike; answer: ServerView}> = [
        {name: 'secure, http on localhost', level: 'secure', location: {protocol: 'http:', hostname: 'localhost'}, answer: {clientClass: 'loopback', cookieSecure: false}},
        {name: 'secure, https', level: 'secure', location: {protocol: 'https:', hostname: 'lf.example'}, answer: {clientClass: 'public', cookieSecure: true}},
        {name: 'local, a .lan name', level: 'local', location: {protocol: 'http:', hostname: 'lf.lan'}, answer: {clientClass: 'lan', cookieSecure: false}},
        {name: 'local, a public name the server sees from a LAN', level: 'local', location: {protocol: 'http:', hostname: 'lf.example'}, answer: {clientClass: 'lan', cookieSecure: false}},
    ];

    it.each(NO_DOT.map((testCase): [string, (typeof NO_DOT)[number]] => [testCase.name, testCase]))('%s: no dot', async (_name, {level, location, answer}) => {
        await primeConnection(location, answer);
        expect(get(connectionSecurity).level, `premise: the store holds ${level}`).toBe(level);

        await mount();

        expect(within(header()).getByTestId('mobile-menu-toggle'), 'presence barrier: the burger is drawn').toBeInTheDocument();
        expect(screen.queryByTestId('mobile-menu-security-dot'), `${level} draws no dot`).toBeNull();
    });

    it('follows the store after mount: on while only the browser has spoken (insecure), off once the server reports a LAN client', async () => {
        // Created up front, so the answer can be given whenever the store gets round to asking.
        let answer: (view: ServerView) => void = () => undefined;
        const serverView = new Promise<ServerView>((resolve) => {
            answer = resolve;
        });
        resetConnectionSecurity();
        const refreshing = refreshConnectionSecurity({location: {protocol: 'http:', hostname: 'lf.example'}, fetchServerView: () => serverView, force: true});
        await vi.waitFor(() => expect(get(connectionSecurity), 'premise: alone, the browser calls a public name over http insecure').toMatchObject({level: 'insecure', serverChecked: false}));

        await mount();
        expect(menuDot(), 'while the server is asked, the browser’s verdict marks the burger').not.toBeNull();

        answer({clientClass: 'lan', cookieSecure: false});
        await refreshing;
        await tick();

        expect(get(connectionSecurity), 'premise: a LAN client makes the public name uncertain').toMatchObject({level: 'local', reason: 'uncertain', serverChecked: true});
        expect(screen.queryByTestId('mobile-menu-security-dot'), 'the dot leaves with the insecure level').toBeNull();
    });
});

/**
 * The menu dot, N69b (N69 point 1; the developer's answers D1 a, D2 a, D3 a). On a phone the sidebar's connection line —
 * which now carries an administrator's security attention — hides behind the burger, so the burger says it too:
 *   - `mobile-menu-security-dot` is drawn while the connection is insecure (plan 36) or while an administrator
 *     (`$auth.user?.is_superuser === true`) has attention (`securityChecks.attentionCount > 0`); one dot either way;
 *   - it carries `data-severity`: `error` when the connection is insecure or the administrator's `attentionSeverity` is
 *     `error`, else `warning`;
 *   - absent for anybody else on a secure or local connection, and for an administrator with nothing to see;
 *   - the burger's `aria-label` appends the attention text, «… — ‹attention text›», after whatever it says today (the
 *     English «Toggle menu», and «— ‹insecure label›» when insecure), the attention text being
 *     `$_('connectionSecurity.attention', {values: {count}})`;
 *   - the header only reads the store (`attentionCount`, `attentionSeverity`) and `$auth`: it never calls
 *     `ensureLoaded()` — the sidebar's line, always mounted in the app shell, loads it.
 *
 * The doubles: the fake store at the top of the file, its answer landed by hand (`storeAnswers`); the user signed in
 * through the auth store's own seam, `auth.checkAuth()` against a spied `GET /auth/me`; the connection primed as the
 * plan-36 cases prime it. The attention key is given the test's own ICU plural (`addMessages`, English is the cases'
 * locale), so the label reads `⟦key·branch·count⟧`: the key, the plural branch and the count passed, never a
 * translation. Today's part of the label is read from the burger before the attention lands, never written here.
 */
describe('Header menu dot: an administrator’s security attention (N69b)', () => {
    const ATTENTION_KEY = 'connectionSecurity.attention';
    const ATTENTION_MESSAGE = `{count, plural, one {⟦${ATTENTION_KEY}·one·#⟧} other {⟦${ATTENTION_KEY}·other·#⟧}}`;
    /** The first characters of any attention text: a label without them says nothing about the checks. */
    const ATTENTION_MARK = `⟦${ATTENTION_KEY}`;
    /** What the burger's label already puts before «insecure». */
    const SEPARATOR = ' — ';
    const SECURE_LOCATION: LocationLike = {protocol: 'https:', hostname: 'lf.example'};
    const SECURE_ANSWER: ServerView = {clientClass: 'public', cookieSecure: true};
    const INSECURE_LOCATION: LocationLike = {protocol: 'http:', hostname: 'lf.example'};
    const INSECURE_ANSWER: ServerView = {clientClass: 'public', cookieSecure: false};

    const finding = (id: string, severity: FakeFinding['severity']): FakeFinding => ({id, severity, messageKey: `test.${id}`, params: {}, source: 'server'});
    /** Two warnings and an info: 2, warning. */
    const WARNINGS = [finding('platform.jwt_secret', 'warning'), finding('accounts.login_limit', 'warning'), finding('platform.log_level', 'info')];
    /** An error, a warning and an info: 2, error. */
    const WITH_ERROR = [finding('platform.instance_key', 'error'), finding('email.smtp_encryption', 'warning'), finding('email.links', 'info')];
    /** Infos only: listed in the tab, counted nowhere. */
    const INFOS_ONLY = [finding('platform.log_level', 'info'), finding('email.links', 'info')];

    /** `GET /auth/me` as the spy sees it: the generated client's types are too deep for `vi.spyOn` to instantiate. */
    type MeOperation = () => Promise<unknown>;
    let me: MockInstance<MeOperation>;

    /** The attention text for `count`, as the test's own message renders it. */
    function attentionText(count: number): string {
        return `⟦${ATTENTION_KEY}·${count === 1 ? 'one' : 'other'}·${count}⟧`;
    }

    /** The insecure level's label, as the header's own `$_` gives it. */
    function insecureLabel(): string {
        return get(formatMessage)('connectionSecurity.level.insecure');
    }

    async function primeConnection(location: LocationLike, answer: ServerView, level: ConnectionLevel): Promise<void> {
        resetConnectionSecurity();
        await refreshConnectionSecurity({location, fetchServerView: () => Promise.resolve(answer), force: true});
        expect(get(connectionSecurity).level, `premise: the store holds ${level}`).toBe(level);
    }

    /** Signs a user in through the auth store's own seam: `checkAuth()` against the spied `GET /auth/me`. */
    async function signInAs(isSuperuser: boolean): Promise<void> {
        const user = {id: isSuperuser ? 691 : 692, username: isSuperuser ? 'n69b-admin' : 'n69b-member', email: 'n69b@example.com', is_active: true, is_superuser: isSuperuser, created_at: '2026-10-20T00:00:00Z'};
        me.mockResolvedValueOnce({user});
        expect(await auth.checkAuth(), 'premise: the auth store signed the user in').toBe('authenticated');
        expect(get(auth).user?.is_superuser, 'premise: the signed-in user is the one this case needs').toBe(isSuperuser);
        await tick();
    }

    /** The checks' answer lands in the store, as the sidebar's `ensureLoaded()` lands it. */
    async function storeAnswers(attention: FakeFinding[]): Promise<void> {
        securityStore.state.attention = attention;
        securityStore.state.answered = true;
        securityStore.state.status = 'ready';
        flushSync();
        await tick();
    }

    function resetSecurityStore(): void {
        securityStore.state.status = 'idle';
        securityStore.state.answered = false;
        securityStore.state.attention = [];
        securityStore.ensureLoaded.mockClear();
        securityStore.reload.mockClear();
    }

    function burger(): HTMLElement {
        return within(header()).getByTestId('mobile-menu-toggle');
    }

    /** The dots inside the burger: one, or none. */
    function burgerDots(): HTMLElement[] {
        return within(burger()).queryAllByTestId('mobile-menu-security-dot');
    }

    function burgerLabel(): string {
        return burger().getAttribute('aria-label') ?? '';
    }

    function expectNeverAsked(when: string): void {
        expect(securityStore.ensureLoaded, `${when}: the header only reads the store, the sidebar’s line loads it`).not.toHaveBeenCalled();
        expect(securityStore.reload, `${when}: nor forces a read`).not.toHaveBeenCalled();
    }

    beforeAll(() => {
        addMessages('en', {[ATTENTION_KEY]: ATTENTION_MESSAGE});
        expect(get(formatMessage)(ATTENTION_KEY, {values: {count: 2}}), 'premise: the attention key renders the test’s own marker').toBe(attentionText(2));
    });
    beforeEach(() => {
        auth.reset();
        resetConnectionSecurity();
        resetSecurityStore();
        // Restored by the file's afterEach (`vi.restoreAllMocks()`).
        me = vi.spyOn(zodiosApi as unknown as {get_me_api_v1_auth_me_get: MeOperation}, 'get_me_api_v1_auth_me_get');
    });
    afterEach(() => {
        auth.reset();
        resetConnectionSecurity();
        resetSecurityStore();
    });

    const ATTENTION_CASES: Array<[label: string, attention: FakeFinding[], count: number, severity: 'error' | 'warning']> = [
        ['warnings', WARNINGS, 2, 'warning'],
        ['an error among the warnings', WITH_ERROR, 2, 'error'],
    ];

    // red until N69b
    it.each(ATTENTION_CASES)('an administrator with %s, on a secure connection: the dot and its severity, the count appended to the label — and the header never asks the store', async (_label, attention, count, severity) => {
        await signInAs(true);
        await primeConnection(SECURE_LOCATION, SECURE_ANSWER, 'secure');
        await mount();
        const todaysLabel = burgerLabel();
        expect(todaysLabel, 'premise: the burger has a name').not.toBe('');
        expect(burgerDots(), 'idle, before the checks are in: nothing to mark').toHaveLength(0);
        expectNeverAsked('idle at mount');

        await storeAnswers(INFOS_ONLY);
        expect(burgerDots(), 'infos only: nothing for the administrator to see').toHaveLength(0);
        expect(burgerLabel(), 'infos only: the label as today').toBe(todaysLabel);

        await storeAnswers(attention);

        const dots = burgerDots();
        expect(dots, 'the administrator’s attention marks the burger').toHaveLength(1);
        expect(dots[0], 'the dot says how serious').toHaveAttribute('data-severity', severity);
        expect(dots[0], 'the dot is decoration: the count is in the name').toHaveAttribute('aria-hidden', 'true');
        expect(burgerLabel(), 'the count is appended to the name, as «insecure» is').toBe(`${todaysLabel}${SEPARATOR}${attentionText(count)}`);
        expectNeverAsked('after the answer');
    });

    // red until N69b
    it('a member on an insecure connection: today’s dot, now with data-severity="error", and nothing about the checks in the label', async () => {
        await signInAs(false);
        await primeConnection(INSECURE_LOCATION, INSECURE_ANSWER, 'insecure');

        await mount();

        const dots = burgerDots();
        expect(dots, 'one dot: the insecure connection’s').toHaveLength(1);
        expect(dots[0], 'an insecure connection is an error').toHaveAttribute('data-severity', 'error');
        expect(burgerLabel(), 'the insecure level is in the name, as today').toContain(`${SEPARATOR}${insecureLabel()}`);
        expect(burgerLabel(), 'a member is told nothing about the checks').not.toContain(ATTENTION_MARK);
        expectNeverAsked('a member');
    });

    // red until N69b
    it('an administrator with warnings on an insecure connection: one dot, error wins; the label carries the level, then the count', async () => {
        await signInAs(true);
        await primeConnection(INSECURE_LOCATION, INSECURE_ANSWER, 'insecure');
        await mount();
        const todaysLabel = burgerLabel();
        expect(todaysLabel, 'premise: today’s name carries the insecure level').toContain(`${SEPARATOR}${insecureLabel()}`);

        await storeAnswers(WARNINGS);

        expect(burgerLabel(), 'the count is appended after the level').toBe(`${todaysLabel}${SEPARATOR}${attentionText(2)}`);
        const dots = burgerDots();
        expect(dots, 'one dot, not one per reason').toHaveLength(1);
        expect(dots[0], 'the most severe wins: the insecure connection is an error, the checks only warn').toHaveAttribute('data-severity', 'error');
        expectNeverAsked('after the answer');
    });

    // red until N69b
    it('a member, the store holding an administrator’s warnings, on a secure connection: no dot, nothing in the label — until an administrator signs in (the control)', async () => {
        await signInAs(false);
        await primeConnection(SECURE_LOCATION, SECURE_ANSWER, 'secure');
        await storeAnswers(WARNINGS);
        expect(securityStore.store.attentionCount, 'premise: the store holds two warnings, left by an administrator earlier in this runtime').toBe(2);

        await mount();

        expect(burger(), 'presence barrier: the burger is drawn').toBeInTheDocument();
        expect(burgerDots(), 'a member is never marked for the checks').toHaveLength(0);
        const membersLabel = burgerLabel();
        expect(membersLabel, 'a member is told nothing about the checks').not.toContain(ATTENTION_MARK);

        // The negative's control: the same header, the same store, an administrator.
        await signInAs(true);

        const dots = burgerDots();
        expect(dots, 'control: the same store marks an administrator’s burger').toHaveLength(1);
        expect(dots[0]).toHaveAttribute('data-severity', 'warning');
        expect(burgerLabel(), 'control: and names the count').toBe(`${membersLabel}${SEPARATOR}${attentionText(2)}`);
        expectNeverAsked('member then administrator');
    });
});
