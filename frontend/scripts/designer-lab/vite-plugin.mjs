/**
 * Designer Lab — Vite plugin (see `design-designerLab.md` §3–§4).
 *
 * - Serves `virtual:lf-color-catalog`, the catalogue of `scan-colors.mjs`, when the Lab is enabled. The catalogue is
 *   built lazily, on the first import, so a build or dev server that never opens the Lab never scans.
 * - Under `vite dev`, forgets the catalogue when a scanned source changes, so the next load of the Lab is current.
 * - In a build where the Lab is disabled (release), fails the build when any emitted file carries the Lab's marker:
 *   the guard behind the `if (__LF_DESIGNER_LAB__)` branches that Rollup is expected to drop.
 */

import {FRONTEND_DIR, LAB_DIRS, scanColors} from './scan-colors.mjs';

export const VIRTUAL_ID = 'virtual:lf-color-catalog';
const RESOLVED_ID = '\0' + VIRTUAL_ID;
/** The test ids of the catalogue alone, for the element picker that runs in the app tabs (`testidIndex`). */
export const TESTID_INDEX_ID = 'virtual:lf-testid-index';
const RESOLVED_INDEX_ID = '\0' + TESTID_INDEX_ID;

/**
 * The picker's test-id index: the static ids, and the prefixes of the templated ones, longest first.
 * @param {{testids: Record<string, unknown>, testid_prefixes: [string, ...unknown[]][]}} catalog
 * @returns {{statics: string[], prefixes: string[]}}
 */
export function testidIndex(catalog) {
    const prefixes = [...new Set(catalog.testid_prefixes.map((p) => p[0]))];
    return {statics: Object.keys(catalog.testids).sort(), prefixes: prefixes.sort((a, b) => b.length - a.length || a.localeCompare(b))};
}

/** A string every Lab runtime module contains (storage key, channel, style id); a release build must not. */
export const LAB_MARKER = 'lf-designer-lab';

/**
 * Whether this build carries the Lab: debug builds (`VITE_DEBUG=true`, `--mode development`) and `vite dev`. The
 * environment variable `LF_DESIGNER_LAB=0|1` overrides it (`0` gives a debug build without the Lab, for A/B checks).
 * @param {{mode: string, command: string, env?: Record<string, string | undefined>}} ctx
 */
export function designerLabEnabled({mode, command, env = process.env}) {
    if (env.LF_DESIGNER_LAB === '0') return false;
    if (env.LF_DESIGNER_LAB === '1') return true;
    return env.VITE_DEBUG === 'true' || mode === 'development' || command === 'serve';
}

/**
 * The names of the emitted files that contain the marker.
 * @param {Record<string, {type: 'chunk', code: string} | {type: 'asset', source: string | Uint8Array}>} bundle
 * @param {string} [marker]
 * @returns {string[]}
 */
export function filesWithMarker(bundle, marker = LAB_MARKER) {
    const hits = [];
    for (const [name, out] of Object.entries(bundle)) {
        const text = out.type === 'chunk' ? out.code : typeof out.source === 'string' ? out.source : Buffer.from(out.source).toString('utf8');
        if (text.includes(marker)) hits.push(name);
    }
    return hits.sort();
}

/**
 * @param {{enabled: boolean, appVersion?: string | (() => string)}} opts  `appVersion` may be a getter: it is read only
 *   when the catalogue is built.
 * @returns {import('vite').Plugin}
 */
export function designerLabPlugin({enabled, appVersion = 'unknown'}) {
    /** @type {ReturnType<typeof scanColors> | null} */
    let catalog = null;
    return {
        name: 'lf-designer-lab',
        resolveId(id) {
            return id === VIRTUAL_ID ? RESOLVED_ID : id === TESTID_INDEX_ID ? RESOLVED_INDEX_ID : null;
        },
        load(id) {
            const name = id === RESOLVED_ID ? VIRTUAL_ID : id === RESOLVED_INDEX_ID ? TESTID_INDEX_ID : null;
            if (!name) return null;
            if (!enabled) this.error(`${name} was imported by a build without the Designer Lab (release): it must only be reached through an \`if (__LF_DESIGNER_LAB__)\` branch.`);
            catalog ??= scanColors({appVersion: typeof appVersion === 'function' ? appVersion() : appVersion});
            // JSON.parse of a string literal is cheaper to evaluate than an object literal of this size.
            return `export default JSON.parse(${JSON.stringify(JSON.stringify(name === VIRTUAL_ID ? catalog : testidIndex(catalog)))});`;
        },
        configureServer(server) {
            if (!enabled) return;
            const src = FRONTEND_DIR + '/src/';
            server.watcher.on('change', (file) => {
                const rel = file.startsWith(src) ? 'src/' + file.slice(src.length) : null;
                if (!rel || LAB_DIRS.some((dir) => rel.startsWith(dir)) || !/\.(svelte|ts|js|css)$/.test(rel)) return;
                catalog = null;
                for (const resolved of [RESOLVED_ID, RESOLVED_INDEX_ID]) {
                    const mod = server.moduleGraph.getModuleById(resolved);
                    if (mod) server.moduleGraph.invalidateModule(mod);
                }
                server.ws.send({type: 'custom', event: 'lf-designer-lab:catalog-stale', data: {file: rel}});
            });
        },
        generateBundle(_options, bundle) {
            if (enabled) return;
            const hits = filesWithMarker(/** @type {any} */ (bundle));
            if (hits.length) this.error(`Designer Lab code reached a build without the Lab (marker "${LAB_MARKER}" in ${hits.join(', ')}). Every import of $lib/dev/designer-lab must sit inside an \`if (__LF_DESIGNER_LAB__)\` branch.`);
        },
    };
}
