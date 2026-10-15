/**
 * Designer Lab — the Vite plugin (`scripts/designer-lab/vite-plugin.mjs`) and the switch that decides whether a build
 * carries the Lab.
 *
 * The plugin serves the catalogue (`virtual:lf-color-catalog`) and the picker's test-id index
 * (`virtual:lf-testid-index`) when the Lab is enabled, builds the catalogue lazily and once, forgets it when a scanned
 * source changes under `vite dev`, and fails a release build that imports a virtual module or emits a file carrying
 * the Lab's marker. The scanner is mocked with a synthetic catalogue: the real scan has tests of its own
 * (`scanColors.test.ts`), and here only what the plugin does with a catalogue is the subject. Hooks are called the way
 * Rollup calls them, with a context whose `error` throws.
 */

import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';

const scan = vi.hoisted(() => {
    const catalog: import('./types').ColorCatalog = {
        meta: {schema: 'lf-color-catalog/1', app_version: 'test', generated_at: '2026-10-14T19:00:00.000Z', hash: 'sha256:abc', scan_ms: 1, parity: {files: 2}, layers: {'css-literal': 1}, excluded: ['src/lib/dev/designer-lab/', 'src/routes/designer-lab/']},
        files: ['src/lib/components/A.svelte', 'src/lib/components/B.svelte'],
        css_vars: [],
        palette: [],
        // A snippet with everything a JS string literal must escape: quotes, a backslash, `</script>`, U+2028.
        literals: [{id: 0, file: 0, line: 1, col: 1, raw: '#64748b', kind: 'hex', key: '#64748b', alpha: 1, zone: 'svelte-style', theme: 'both', layer: 'css-literal', preview: true, snippet: 'content: "\\"</script>\u2028\'";'}],
        by_value: {'#64748b': [0]},
        testids: {'tx-table': [[1, 3, 'attr']], 'b-id': [[0, 2, 'prop']], 'a-id': [[0, 1, 'attr']]},
        testid_prefixes: [
            ['filter-row-', 0, 4, 'attr'],
            ['tab-', 1, 6, 'attr'],
            ['row-', 1, 5, 'prop'],
            ['row-', 0, 7, 'attr'],
            ['ab-', 0, 8, 'attr'],
        ],
    };
    return {catalog, scanColors: vi.fn((_opts?: {appVersion?: string}) => catalog)};
});

vi.mock('../../../../scripts/designer-lab/scan-colors.mjs', async (importOriginal) => ({
    ...(await importOriginal<typeof import('../../../../scripts/designer-lab/scan-colors.mjs')>()),
    scanColors: scan.scanColors,
}));

import {FRONTEND_DIR} from '../../../../scripts/designer-lab/scan-colors.mjs';
import {designerLabEnabled, designerLabPlugin, filesWithMarker, LAB_MARKER, TESTID_INDEX_ID, testidIndex, VIRTUAL_ID} from '../../../../scripts/designer-lab/vite-plugin.mjs';

/** Rollup's plugin context, as far as the plugin uses it: `error` throws, as Rollup's does. */
interface Context {
    error: (message: string) => never;
}

interface FakeServer {
    watcher: {on: (event: string, handler: (file: string) => void) => void};
    moduleGraph: {getModuleById: (id: string) => {id: string} | undefined; invalidateModule: (mod: {id: string}) => void};
    ws: {send: (payload: unknown) => void};
}

/** The hooks the plugin defines, as plain functions (Vite types them as hooks that may be objects). */
interface Hooks {
    name: string;
    resolveId: (id: string) => string | null;
    load: (this: Context, id: string) => string | null;
    configureServer: (server: FakeServer) => void;
    generateBundle: (this: Context, options: unknown, bundle: Record<string, unknown>) => void;
}

const pluginOf = (opts: {enabled: boolean; appVersion?: string | (() => string)}) => designerLabPlugin(opts) as unknown as Hooks;

const RESOLVED = `\0${VIRTUAL_ID}`;
const RESOLVED_INDEX = `\0${TESTID_INDEX_ID}`;

function context(): Context & {error: Mock<(message: string) => never>} {
    return {
        error: vi.fn((message: string): never => {
            throw new Error(message);
        }),
    };
}

/** Evaluate the module text the plugin serves, as the bundler would, and return its default export. */
function evaluate(code: string | null): unknown {
    expect(code).toMatch(/^export default JSON\.parse\(".*"\);$/s);
    return new Function((code as string).replace(/^export default /, 'return '))();
}

function fakeServer() {
    const handlers: ((file: string) => void)[] = [];
    const server = {
        watcher: {on: vi.fn((event: string, handler: (file: string) => void) => void (event === 'change' && handlers.push(handler)))},
        moduleGraph: {getModuleById: vi.fn((id: string): {id: string} | undefined => ({id})), invalidateModule: vi.fn()},
        ws: {send: vi.fn()},
    };
    return {server, change: (file: string) => handlers.forEach((handler) => handler(file))};
}

beforeEach(() => {
    scan.scanColors.mockClear();
});

afterEach(() => {
    vi.unstubAllEnvs();
});

describe('designerLabEnabled', () => {
    it('is off in a release build', () => {
        expect(designerLabEnabled({mode: 'production', command: 'build', env: {}})).toBe(false);
    });

    it('is on in a debug build, a development build and the dev server', () => {
        expect(designerLabEnabled({mode: 'production', command: 'build', env: {VITE_DEBUG: 'true'}})).toBe(true);
        expect(designerLabEnabled({mode: 'development', command: 'build', env: {}})).toBe(true);
        expect(designerLabEnabled({mode: 'production', command: 'serve', env: {}})).toBe(true);
    });

    it('reads VITE_DEBUG as the literal `true` only', () => {
        expect(designerLabEnabled({mode: 'production', command: 'build', env: {VITE_DEBUG: 'false'}})).toBe(false);
        expect(designerLabEnabled({mode: 'production', command: 'build', env: {VITE_DEBUG: '1'}})).toBe(false);
    });

    it('lets LF_DESIGNER_LAB=0|1 override everything else, and nothing else override it', () => {
        expect(designerLabEnabled({mode: 'development', command: 'serve', env: {LF_DESIGNER_LAB: '0', VITE_DEBUG: 'true'}})).toBe(false);
        expect(designerLabEnabled({mode: 'production', command: 'build', env: {LF_DESIGNER_LAB: '1'}})).toBe(true);
        expect(designerLabEnabled({mode: 'production', command: 'build', env: {LF_DESIGNER_LAB: 'true'}})).toBe(false);
        expect(designerLabEnabled({mode: 'development', command: 'build', env: {LF_DESIGNER_LAB: ''}})).toBe(true);
    });

    it('reads the process environment by default', () => {
        vi.stubEnv('LF_DESIGNER_LAB', '1');
        expect(designerLabEnabled({mode: 'production', command: 'build'})).toBe(true);
        vi.stubEnv('LF_DESIGNER_LAB', '0');
        expect(designerLabEnabled({mode: 'development', command: 'serve'})).toBe(false);
    });
});

describe('filesWithMarker', () => {
    const bundle = {
        'z-client.js': {type: 'chunk' as const, code: 'const KEY = "lf-designer-lab/v1";'},
        'app.js': {type: 'chunk' as const, code: 'export const x = 1;'},
        'm-styles.css': {type: 'asset' as const, source: '#lf-designer-lab-vars { }'},
        'catalog.bin': {type: 'asset' as const, source: new TextEncoder().encode('{"schema":"lf-designer-lab/1"}')},
        'image.bin': {type: 'asset' as const, source: new Uint8Array([0x89, 0x50, 0x4e, 0x47])},
    };

    it('names the chunks and assets — text or bytes — that carry the marker, sorted', () => {
        expect(LAB_MARKER).toBe('lf-designer-lab');
        expect(filesWithMarker(bundle)).toEqual(['catalog.bin', 'm-styles.css', 'z-client.js']);
    });

    it('looks for another marker when given one, and finds nothing in a clean bundle', () => {
        expect(filesWithMarker(bundle, 'lf-designer-lab/v1')).toEqual(['z-client.js']);
        expect(filesWithMarker({'app.js': bundle['app.js'], 'image.bin': bundle['image.bin']})).toEqual([]);
    });
});

describe('testidIndex', () => {
    it('lists the static ids sorted, and each prefix once, longest first', () => {
        expect(testidIndex(scan.catalog)).toEqual({statics: ['a-id', 'b-id', 'tx-table'], prefixes: ['filter-row-', 'row-', 'tab-', 'ab-']});
    });
});

describe('designerLabPlugin — virtual modules', () => {
    it('resolves the two virtual ids, and nothing else', () => {
        const plugin = pluginOf({enabled: true});
        expect(plugin.name).toBe('lf-designer-lab');
        expect(plugin.resolveId(VIRTUAL_ID)).toBe(RESOLVED);
        expect(plugin.resolveId(TESTID_INDEX_ID)).toBe(RESOLVED_INDEX);
        expect(plugin.resolveId('$lib/dev/designer-lab/client')).toBeNull();
        expect(plugin.resolveId(RESOLVED)).toBeNull();
        // Resolved in a release build too: `load` is where the build fails, with a message that says why.
        expect(pluginOf({enabled: false}).resolveId(VIRTUAL_ID)).toBe(RESOLVED);
    });

    it('serves the catalogue as `JSON.parse` of a string literal that gives the catalogue back', () => {
        const plugin = pluginOf({enabled: true, appVersion: '1.2.0'});
        expect(evaluate(plugin.load.call(context(), RESOLVED))).toEqual(scan.catalog);
    });

    it('serves the picker’s index from the same catalogue', () => {
        const plugin = pluginOf({enabled: true});
        expect(evaluate(plugin.load.call(context(), RESOLVED_INDEX))).toEqual(testidIndex(scan.catalog));
    });

    it('scans on the first load only, reading the app version then', () => {
        const appVersion = vi.fn(() => '1.2.0+150f2716');
        const plugin = pluginOf({enabled: true, appVersion});
        plugin.resolveId(VIRTUAL_ID);
        expect(scan.scanColors).not.toHaveBeenCalled();
        expect(appVersion).not.toHaveBeenCalled();

        plugin.load.call(context(), RESOLVED);
        plugin.load.call(context(), RESOLVED_INDEX);
        plugin.load.call(context(), RESOLVED);
        expect(scan.scanColors).toHaveBeenCalledOnce();
        expect(scan.scanColors).toHaveBeenCalledWith({appVersion: '1.2.0+150f2716'});
        expect(appVersion).toHaveBeenCalledOnce();

        pluginOf({enabled: true}).load.call(context(), RESOLVED);
        expect(scan.scanColors).toHaveBeenLastCalledWith({appVersion: 'unknown'});
    });

    it('loads nothing it does not own', () => {
        const ctx = context();
        expect(pluginOf({enabled: true}).load.call(ctx, '/src/app.css')).toBeNull();
        expect(pluginOf({enabled: false}).load.call(ctx, '/src/app.css')).toBeNull();
        expect(ctx.error).not.toHaveBeenCalled();
        expect(scan.scanColors).not.toHaveBeenCalled();
    });

    it('fails a build without the Lab that imports either virtual module, before any scan', () => {
        const plugin = pluginOf({enabled: false});
        for (const [id, name] of [
            [RESOLVED, VIRTUAL_ID],
            [RESOLVED_INDEX, TESTID_INDEX_ID],
        ]) {
            const ctx = context();
            expect(() => plugin.load.call(ctx, id)).toThrow(`${name} was imported by a build without the Designer Lab`);
            expect(ctx.error).toHaveBeenCalledOnce();
            expect(ctx.error.mock.calls[0][0]).toContain('if (__LF_DESIGNER_LAB__)');
        }
        expect(scan.scanColors).not.toHaveBeenCalled();
    });
});

describe('designerLabPlugin — release guard', () => {
    const dirty = {'app.js': {type: 'chunk', code: 'ok'}, 'nodes/17.js': {type: 'chunk', code: 'localStorage.getItem("lf-designer-lab/v1")'}, 'lab.css': {type: 'asset', source: '.lf-designer-lab{}'}};
    const clean = {'app.js': {type: 'chunk', code: 'ok'}, 'logo.png': {type: 'asset', source: new Uint8Array([1, 2, 3])}};

    it('fails a build without the Lab whose output carries the marker, naming the files', () => {
        const ctx = context();
        expect(() => pluginOf({enabled: false}).generateBundle.call(ctx, {}, dirty)).toThrow('marker "lf-designer-lab" in lab.css, nodes/17.js');
        expect(ctx.error).toHaveBeenCalledOnce();
    });

    it('passes a clean build without the Lab, and does not check a build with it', () => {
        const ctx = context();
        pluginOf({enabled: false}).generateBundle.call(ctx, {}, clean);
        pluginOf({enabled: true}).generateBundle.call(ctx, {}, dirty);
        expect(ctx.error).not.toHaveBeenCalled();
    });
});

describe('designerLabPlugin — dev server', () => {
    it('forgets the catalogue when a scanned source changes, invalidates both modules and tells the Lab page', () => {
        const plugin = pluginOf({enabled: true});
        const {server, change} = fakeServer();
        plugin.configureServer(server);
        expect(server.watcher.on).toHaveBeenCalledWith('change', expect.any(Function));

        plugin.load.call(context(), RESOLVED);
        expect(scan.scanColors).toHaveBeenCalledOnce();

        change(`${FRONTEND_DIR}/src/lib/components/table/DataTable.svelte`);
        expect(server.moduleGraph.invalidateModule.mock.calls.map(([mod]) => mod.id)).toEqual([RESOLVED, RESOLVED_INDEX]);
        expect(server.ws.send).toHaveBeenCalledWith({type: 'custom', event: 'lf-designer-lab:catalog-stale', data: {file: 'src/lib/components/table/DataTable.svelte'}});

        plugin.load.call(context(), RESOLVED);
        expect(scan.scanColors).toHaveBeenCalledTimes(2);
    });

    it('ignores the Lab’s own sources, files that are not sources, and anything outside src', () => {
        const plugin = pluginOf({enabled: true});
        const {server, change} = fakeServer();
        plugin.configureServer(server);
        plugin.load.call(context(), RESOLVED);

        change(`${FRONTEND_DIR}/src/lib/dev/designer-lab/store.ts`);
        change(`${FRONTEND_DIR}/src/routes/designer-lab/+page.svelte`);
        change(`${FRONTEND_DIR}/src/lib/i18n/en.json`);
        change(`${FRONTEND_DIR}/scripts/designer-lab/scan-colors.mjs`);
        change('/elsewhere/src/app.css');

        expect(server.ws.send).not.toHaveBeenCalled();
        expect(server.moduleGraph.invalidateModule).not.toHaveBeenCalled();
        plugin.load.call(context(), RESOLVED);
        expect(scan.scanColors).toHaveBeenCalledOnce();
    });

    it('still tells the Lab page when the modules were never loaded', () => {
        const plugin = pluginOf({enabled: true});
        const {server, change} = fakeServer();
        server.moduleGraph.getModuleById.mockReturnValue(undefined);
        plugin.configureServer(server);
        change(`${FRONTEND_DIR}/src/app.css`);
        expect(server.moduleGraph.invalidateModule).not.toHaveBeenCalled();
        expect(server.ws.send).toHaveBeenCalledOnce();
    });

    it('does not watch anything in a build without the Lab', () => {
        const {server} = fakeServer();
        pluginOf({enabled: false}).configureServer(server);
        expect(server.watcher.on).not.toHaveBeenCalled();
    });
});
