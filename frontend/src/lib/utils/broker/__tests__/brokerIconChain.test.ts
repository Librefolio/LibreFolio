// @vitest-environment jsdom
//
// The docblock above is load-bearing, not decoration. Under the repository's default `node`
// environment a `.svelte.ts` compiles but its `$effect` never runs: the chain would never read the
// plugin cache, and every case below that expects the favicon first would pass for the wrong reason.
// `assertEffectsRun()` in `freshModules()` fails loudly if it is ever removed.
/**
 * brokerIconChain — the reactive icon chain behind BrokerIcon and BrokerBadge walks its candidates in
 * the order `getBrokerIconCandidates` lists them: the broker's custom icon, the icon of a plugin made
 * for the broker, the portal's favicon, the icon of a generic fallback plugin (detection_priority below
 * 50, the generic CSV, whose icon is the same for every broker), and then nothing — `currentDisplayUrl`
 * null, where the caller draws its briefcase.
 *
 * The chain is walked as the component walks it: `currentDisplayUrl` is what the <img> shows, and
 * `handleError()` is what the <img> calls when that URL fails to load.
 *
 * The plugin's icon and kind reach the chain on two paths, and both are covered: the plugin list is
 * already loaded when the chain is created (a cache hit), or it is not, and the chain asks for it and
 * re-orders itself when it lands.
 *
 * Every case loads fresh modules (`vi.resetModules()` + dynamic imports), so the module-level plugin
 * cache of brokerHelpers starts empty in each; `svelte` and the rune harness are imported after the
 * same reset as the chain, so all three share one Svelte runtime.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {BrokerIconSource} from '../brokerHelpers';
import type {BrokerIconChain} from '../brokerIconChain.svelte';

const {listPluginsMock} = vi.hoisted(() => ({
    listPluginsMock: vi.fn(),
}));

vi.mock('$lib/api', () => ({
    zodiosApi: {
        list_plugins_api_v1_brokers_import_plugins_get: listPluginsMock,
    },
}));

/** A plugin made for one broker, ranked as the backend ranks those (100). */
const DEDICATED = {code: 'broker_directa', icon_url: '/plugins/directa.svg', detection_priority: 100};
/** The generic CSV, ranked 0 by the backend: a generic fallback. */
const GENERIC = {code: 'broker_generic_csv', icon_url: '/plugins/generic.svg', detection_priority: 0};
/** The list `GET /brokers/import/plugins` answers in these tests. */
const PLUGINS = [DEDICATED, GENERIC];

const CUSTOM_ICON = 'https://cdn.example.com/broker.png';
const PORTAL = 'https://www.recrowd.com/login';
const FAVICON = 'https://www.recrowd.com/favicon.ico';

/** Fresh modules — an empty plugin cache — with the chain and the rune harness on one Svelte runtime. */
async function freshModules() {
    vi.resetModules();
    const {flushSync} = await import('svelte');
    const {assertEffectsRun, effectRoot, recordReads} = await import('$test/runes.svelte');
    const {ensurePluginIconsLoaded, getPluginIconUrl} = await import('../brokerHelpers');
    const {createBrokerIconChain} = await import('../brokerIconChain.svelte');
    assertEffectsRun();
    return {flushSync, effectRoot, recordReads, ensurePluginIconsLoaded, getPluginIconUrl, createBrokerIconChain};
}

type Modules = Awaited<ReturnType<typeof freshModules>>;

/** Teardowns of the effect roots a case created, run after it. */
const stops: Array<() => void> = [];

/** Create a chain for `broker` inside an effect root, as a component would, and run its effects once. */
function mountChain(modules: Modules, broker: BrokerIconSource): BrokerIconChain {
    const {value: chain, stop} = modules.effectRoot(() => modules.createBrokerIconChain(() => broker));
    stops.push(stop);
    modules.flushSync();
    return chain;
}

/** Every URL the chain shows, in order: each is shown and fails to load, until the briefcase is left. */
function walkChain(modules: Modules, chain: BrokerIconChain): string[] {
    const shown: string[] = [];
    // Bounded: a chain that stopped advancing repeats its URL in the result instead of hanging the run.
    for (let step = 0; step < 6 && chain.currentDisplayUrl !== null; step++) {
        shown.push(chain.currentDisplayUrl);
        chain.handleError();
        modules.flushSync();
    }
    return shown;
}

/** Fresh modules with the plugin list already loaded: the chain finds the plugin in the cache. */
async function modulesWithPluginsLoaded(): Promise<Modules> {
    const modules = await freshModules();
    listPluginsMock.mockResolvedValueOnce(PLUGINS);
    await modules.ensurePluginIconsLoaded();
    expect(modules.getPluginIconUrl(GENERIC.code), 'precondition: the plugin icons are cached').toBe(GENERIC.icon_url);
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
        // The load the chain started: asked after it, so the chain's own continuation runs first.
        const loaded = modules.ensurePluginIconsLoaded();
        answer(PLUGINS);
        await loaded;
        modules.flushSync();
    };
    return {modules, land};
}

beforeEach(() => {
    listPluginsMock.mockReset();
});

afterEach(() => {
    while (stops.length > 0) stops.pop()?.();
});

describe('createBrokerIconChain — custom, plugin made for the broker, portal favicon, generic fallback plugin', () => {
    it('plugin list loaded, dedicated plugin and portal: the plugin icon, then the favicon, then the briefcase', async () => {
        const modules = await modulesWithPluginsLoaded();

        const chain = mountChain(modules, {portal_url: PORTAL, default_import_plugin: DEDICATED.code});

        expect(walkChain(modules, chain)).toEqual([DEDICATED.icon_url, FAVICON]);
        expect(listPluginsMock, 'a cache hit asks for nothing more').toHaveBeenCalledTimes(1);
    });

    it('plugin list loaded, generic fallback plugin and portal: the favicon, then the plugin icon, then the briefcase', async () => {
        const modules = await modulesWithPluginsLoaded();

        const chain = mountChain(modules, {portal_url: PORTAL, default_import_plugin: GENERIC.code});

        expect(walkChain(modules, chain)).toEqual([FAVICON, GENERIC.icon_url]);
    });

    it('plugin list loaded: the custom icon comes first, whatever kind of plugin follows it', async () => {
        const modules = await modulesWithPluginsLoaded();

        const dedicated = mountChain(modules, {icon_url: CUSTOM_ICON, portal_url: PORTAL, default_import_plugin: DEDICATED.code});
        const generic = mountChain(modules, {icon_url: CUSTOM_ICON, portal_url: PORTAL, default_import_plugin: GENERIC.code});

        expect(walkChain(modules, dedicated), 'dedicated plugin').toEqual([CUSTOM_ICON, DEDICATED.icon_url, FAVICON]);
        expect(walkChain(modules, generic), 'generic fallback plugin').toEqual([CUSTOM_ICON, FAVICON, GENERIC.icon_url]);
    });

    it('plugin list not loaded yet, dedicated plugin: the favicon until the list lands, then the plugin icon takes its place', async () => {
        const {modules, land} = await modulesWithPluginsInFlight();

        const chain = mountChain(modules, {portal_url: PORTAL, default_import_plugin: DEDICATED.code});
        expect(listPluginsMock, 'the chain asked for the plugin list itself').toHaveBeenCalledTimes(1);
        const shown = modules.recordReads(() => chain.currentDisplayUrl);
        stops.push(shown.stop);
        expect(shown.values, 'while the list is in flight').toEqual([FAVICON]);

        await land();

        expect(shown.values, 'the dedicated plugin icon replaces the favicon on screen').toEqual([FAVICON, DEDICATED.icon_url]);
        expect(walkChain(modules, chain)).toEqual([DEDICATED.icon_url, FAVICON]);
    });

    it('plugin list not loaded yet, generic fallback plugin: the favicon stays on screen when the list lands, the plugin icon becomes its fallback', async () => {
        const {modules, land} = await modulesWithPluginsInFlight();

        const chain = mountChain(modules, {portal_url: PORTAL, default_import_plugin: GENERIC.code});
        expect(listPluginsMock, 'the chain asked for the plugin list itself').toHaveBeenCalledTimes(1);
        const shown = modules.recordReads(() => chain.currentDisplayUrl);
        stops.push(shown.stop);
        expect(shown.values, 'while the list is in flight').toEqual([FAVICON]);

        await land();

        expect(modules.getPluginIconUrl(GENERIC.code), 'presence barrier: the list has landed').toBe(GENERIC.icon_url);
        expect(shown.values, 'the favicon was never displaced').toEqual([FAVICON]);
        expect(walkChain(modules, chain), 'the plugin icon arrived, after the favicon').toEqual([FAVICON, GENERIC.icon_url]);
    });
});
