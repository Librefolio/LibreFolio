// @vitest-environment jsdom
//
// The docblock above is load-bearing: under the repository's default `node` environment there is no
// `document` to mount into, and the icon chain's `$effect` would never run. `assertEffectsRun()` in
// `freshModules()` fails loudly if it is ever removed.
/**
 * BrokerIcon — which <img> it draws, and which URL a `load` / `error` event belongs to.
 *
 * The icon chain (`brokerIconChain.svelte.ts`) picks the URL; BrokerIcon draws it in a keyed <img>, so
 * every time the chain moves to another URL a new <img> replaces the old one. Two contracts follow:
 *
 * - an <img> with a `src` is a request, in the page or not. With the plugin list already cached, the
 *   icon of the plugin made for the broker is known before the first render: the portal's favicon (a
 *   request to a third party) must never be drawn ahead of it.
 * - Svelte attaches `onload` / `onerror` with `addEventListener` and never removes them from an <img>
 *   that leaves the page (`$.event` tears down only body, window, document and media elements). A
 *   request still in flight when its <img> was swapped out therefore reports to the chain after the
 *   swap — and that event is about the URL of the <img> that raised it, not about the URL on screen.
 *
 * jsdom loads no images, so every outcome is driven by dispatching `load` / `error` on the <img>
 * elements themselves — including on an <img> that is no longer in the page, which is the browser's
 * late answer.
 *
 * Every case loads fresh modules (`vi.resetModules()` + dynamic imports), so the module-level plugin
 * cache of brokerHelpers starts empty in each. `svelte`, the rune harness, brokerHelpers and the
 * component are imported after the same reset, so they share one Svelte runtime and one cache — which
 * is also why the component is mounted with that runtime's own `mount` and not with `render` from
 * `$test/component`: `@testing-library/svelte` is loaded once per file and may hold another runtime.
 *
 * Two modules BrokerIcon imports are replaced, and neither is under test:
 * - `lucide-svelte`, by an inert `Briefcase`. Its barrel loads every icon of the library — some 1,900
 *   modules — and the fresh modules make every case load it again: with it, each case spent its whole
 *   5 s budget on the import. What the cases look at is the briefcase's container,
 *   `broker-icon-fallback`, which is BrokerIcon's own markup and stays real.
 * - the broker store, which BrokerIcon asks for a broker's icon fields only when it is given none: never
 *   with these props, as the cases check. Its real module would bring the lucide barrel back, through
 *   the role helpers.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const {ensureBrokerIconFieldsLoadedMock, listPluginsMock} = vi.hoisted(() => ({
    ensureBrokerIconFieldsLoadedMock: vi.fn(),
    listPluginsMock: vi.fn(),
}));

vi.mock('$lib/api', () => ({
    zodiosApi: {
        list_plugins_api_v1_brokers_import_plugins_get: listPluginsMock,
    },
}));

vi.mock('$lib/stores/reference/brokerStore', () => ({
    ensureBrokerIconFieldsLoaded: ensureBrokerIconFieldsLoadedMock,
}));

// A Svelte 5 component is a function of (anchor, props): this one draws nothing.
vi.mock('lucide-svelte', () => ({
    Briefcase: () => {},
}));

/** A plugin made for one broker, ranked as the backend ranks those (100). */
const DEDICATED = {code: 'broker_directa', icon_url: '/plugins/directa.svg', detection_priority: 100};
/** The generic CSV, ranked 0 by the backend: a generic fallback. */
const GENERIC = {code: 'broker_generic_csv', icon_url: '/plugins/generic.svg', detection_priority: 0};
/** The list `GET /brokers/import/plugins` answers in these tests. */
const PLUGINS = [DEDICATED, GENERIC];

const PORTAL = 'https://www.recrowd.com/login';
const FAVICON = 'https://www.recrowd.com/favicon.ico';

/** A broker with a portal and a plugin made for it, and no custom icon: the plugin icon, then the favicon. */
const PROPS = {portalUrl: PORTAL, pluginCode: DEDICATED.code};

const IMAGE = '[data-testid="broker-icon-img"]';
const BRIEFCASE = '[data-testid="broker-icon-fallback"]';

/** Fresh modules — an empty plugin cache — with the component, the cache and the harness on one Svelte runtime. */
async function freshModules() {
    vi.resetModules();
    const {flushSync, mount, unmount} = await import('svelte');
    const {assertEffectsRun} = await import('$test/runes.svelte');
    const {ensurePluginIconsLoaded, getPluginIconUrl} = await import('$lib/utils/broker/brokerHelpers');
    const BrokerIcon = (await import('./BrokerIcon.svelte')).default;
    assertEffectsRun();
    return {flushSync, mount, unmount, ensurePluginIconsLoaded, getPluginIconUrl, BrokerIcon};
}

type Modules = Awaited<ReturnType<typeof freshModules>>;

/** Fresh modules with the plugin list already loaded: BrokerIcon finds the plugin in the cache. */
async function modulesWithPluginsLoaded(): Promise<Modules> {
    const modules = await freshModules();
    listPluginsMock.mockResolvedValueOnce(PLUGINS);
    await modules.ensurePluginIconsLoaded();
    expect(modules.getPluginIconUrl(DEDICATED.code), 'precondition: the plugin icons are cached').toBe(DEDICATED.icon_url);
    return modules;
}

/** Fresh modules whose plugin list stays in flight until `land()` answers it. */
async function modulesWithPluginsInFlight(): Promise<{modules: Modules; land: () => Promise<void>}> {
    const modules = await freshModules();
    let answer!: (plugins: typeof PLUGINS) => void;
    listPluginsMock.mockReturnValueOnce(
        new Promise<typeof PLUGINS>((resolve) => {
            answer = resolve;
        }),
    );
    const land = async () => {
        // The load BrokerIcon started: asked after it, so the chain's own continuation runs first.
        const loaded = modules.ensurePluginIconsLoaded();
        answer(PLUGINS);
        await loaded;
        modules.flushSync();
    };
    return {modules, land};
}

/** What a case mounted, observed and attached, undone after it — last first. */
const teardowns: Array<() => unknown> = [];

/** A container owned by this case, in the page. */
function newTarget(): HTMLElement {
    const target = document.createElement('div');
    document.body.append(target);
    teardowns.push(() => target.remove());
    return target;
}

/** Mount BrokerIcon into `target`. Its effects have not run yet when this returns: `flushSync()` runs them. */
function mountIcon(modules: Modules, target: HTMLElement): void {
    const component = modules.mount(modules.BrokerIcon, {target, props: PROPS});
    teardowns.push(() => modules.unmount(component));
}

/** The `src` of every BrokerIcon <img> in `target`, in page order. */
function srcsOnScreen(target: HTMLElement): Array<string | null> {
    return [...target.querySelectorAll(IMAGE)].map((image) => image.getAttribute('src'));
}

/** The one <img> on screen. */
function theImage(target: HTMLElement): HTMLImageElement {
    const images = [...target.querySelectorAll<HTMLImageElement>(IMAGE)];
    expect(images, 'BrokerIcon draws one <img> at a time').toHaveLength(1);
    return images[0];
}

/** The briefcase BrokerIcon shows until an image has loaded, or null. */
function briefcase(target: HTMLElement): Element | null {
    return target.querySelector(BRIEFCASE);
}

/**
 * Every BrokerIcon <img> that has been in `target`, by its `src`: one entry per element and src, in the
 * order first seen.
 *
 * `sample()` reads the page as it is — called right after `mount()`, it sees the first render before
 * any effect has run — and drains a MutationObserver, which also sees what the page no longer shows: an
 * <img> swapped out between two samples is in a record's `removedNodes`, still carrying its src, and a
 * src changed in place is in an `attributes` record's `oldValue`.
 */
function watchImages(target: HTMLElement): {sample: () => string[]} {
    const seen: Array<{image: Element; src: string}> = [];
    const note = (image: Element, src: string | null) => {
        if (src !== null && !seen.some((entry) => entry.image === image && entry.src === src)) seen.push({image, src});
    };
    const visit = (node: Node) => {
        if (!(node instanceof Element)) return;
        if (node.matches(IMAGE)) note(node, node.getAttribute('src'));
        for (const image of node.querySelectorAll(IMAGE)) note(image, image.getAttribute('src'));
    };
    // Records handed to the callback are not returned again by `takeRecords()`: keep both.
    const delivered: MutationRecord[] = [];
    const observer = new MutationObserver((records) => delivered.push(...records));
    observer.observe(target, {childList: true, subtree: true, attributes: true, attributeFilter: ['src'], attributeOldValue: true});
    teardowns.push(() => observer.disconnect());
    return {
        sample() {
            for (const record of [...delivered.splice(0), ...observer.takeRecords()]) {
                if (record.type === 'attributes' && record.target instanceof Element && record.target.matches(IMAGE)) note(record.target, record.oldValue);
                record.addedNodes.forEach(visit);
                record.removedNodes.forEach(visit);
            }
            visit(target);
            return seen.map((entry) => entry.src);
        },
    };
}

/**
 * BrokerIcon mounted while the plugin list is in flight: it draws the favicon; the list lands and the
 * plugin icon takes its place in a new <img>. Returns the favicon <img> — out of the page, still listened to.
 */
async function swappedFromFaviconToPluginIcon(): Promise<{modules: Modules; target: HTMLElement; faviconImage: HTMLImageElement}> {
    const {modules, land} = await modulesWithPluginsInFlight();
    const target = newTarget();
    mountIcon(modules, target);
    modules.flushSync();
    expect(listPluginsMock, 'BrokerIcon asked for the plugin list itself').toHaveBeenCalledTimes(1);
    const faviconImage = theImage(target);
    expect(faviconImage.getAttribute('src'), 'while the plugin list is in flight, the favicon is drawn').toBe(FAVICON);

    await land();

    expect(srcsOnScreen(target), "the list landed: the plugin icon took the favicon's place").toEqual([DEDICATED.icon_url]);
    expect(faviconImage.isConnected, 'the favicon <img> left the page').toBe(false);
    expect(briefcase(target), 'the plugin icon has not loaded yet: the briefcase is shown').not.toBeNull();
    expectBrokerStoreNotAsked();
    return {modules, target, faviconImage};
}

/** With its icon fields given as props, BrokerIcon has nothing to ask the broker store. */
function expectBrokerStoreNotAsked(): void {
    expect(ensureBrokerIconFieldsLoadedMock, 'BrokerIcon was given the icon fields: it never asks the broker store for them').not.toHaveBeenCalled();
}

beforeEach(() => {
    listPluginsMock.mockReset();
    ensureBrokerIconFieldsLoadedMock.mockReset();
});

afterEach(async () => {
    while (teardowns.length > 0) await teardowns.pop()?.();
});

describe('BrokerIcon — the <img> it draws, and the URL an <img> event belongs to', () => {
    it('plugin list cached, dedicated plugin and portal: the first and only <img> is the plugin icon, the favicon is never drawn', async () => {
        const modules = await modulesWithPluginsLoaded();
        const target = newTarget();
        const images = watchImages(target);

        mountIcon(modules, target);
        const drawnAtMount = srcsOnScreen(target);
        images.sample();
        modules.flushSync();
        const everDrawn = images.sample();
        expectBrokerStoreNotAsked();

        expect.soft(drawnAtMount, 'right after mount, before any effect has run: the plugin icon is cached, so the favicon must not be drawn first').not.toContain(FAVICON);
        expect(everDrawn, 'every <img> BrokerIcon put in the page, by src: the plugin icon is the first and only one, no request goes to the portal favicon').toEqual([DEDICATED.icon_url]);
        expect(srcsOnScreen(target), 'the <img> on screen once the effects have run').toEqual([DEDICATED.icon_url]);
    });

    it('plugin list in flight, dedicated plugin and portal: a late error from the swapped-out favicon <img> leaves the plugin icon on screen', async () => {
        const {modules, target, faviconImage} = await swappedFromFaviconToPluginIcon();

        faviconImage.dispatchEvent(new Event('error'));
        modules.flushSync();

        expect(srcsOnScreen(target), 'the error came from the favicon <img>, out of the page: it fails the favicon, and the plugin icon stays the one on screen').toEqual([DEDICATED.icon_url]);

        theImage(target).dispatchEvent(new Event('load'));
        modules.flushSync();
        expect(briefcase(target), 'the plugin icon loaded: the briefcase is gone').toBeNull();
    });

    it('plugin list in flight, dedicated plugin and portal: a late load from the swapped-out favicon <img> keeps the briefcase until the plugin icon loads', async () => {
        const {modules, target, faviconImage} = await swappedFromFaviconToPluginIcon();

        faviconImage.dispatchEvent(new Event('load'));
        modules.flushSync();

        expect(srcsOnScreen(target), 'the plugin icon is still the one on screen').toEqual([DEDICATED.icon_url]);
        expect(briefcase(target), 'the load came from the favicon <img>, out of the page: the plugin icon on screen has not loaded, so the briefcase stays').not.toBeNull();

        theImage(target).dispatchEvent(new Event('load'));
        modules.flushSync();
        expect(briefcase(target), 'the plugin icon loaded: the briefcase is gone').toBeNull();
    });
});
