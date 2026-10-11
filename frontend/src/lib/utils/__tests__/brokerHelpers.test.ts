/**
 * Unit tests for brokerHelpers — sync candidate resolution + raw HTML helper.
 *
 * Authoritative priority (custom > plugin > portal favicon > briefcase, generic fallback plugins after
 * the favicon):
 *   1. icon_url — the broker's custom icon
 *   2. default_import_plugin icon, when the plugin is made for a broker
 *   3. portal_url/favicon.ico
 *   4. default_import_plugin icon, when the plugin is a generic fallback — `detection_priority` below
 *      50 (`isFallbackPlugin`, `$lib/utils/brim/pluginKind`): the generic CSV's icon is the same for
 *      every broker, so the portal's own favicon says more
 *   5. caller/UI fallback (system briefcase icon)
 *
 * Plugin icons and kinds come from `GET /brokers/import/plugins` (mocked below), loaded by
 * `ensurePluginIconsLoaded()`; until then no plugin icon is a candidate. Every test starts from a fresh
 * module (`vi.resetModules()`), so a loaded list is never carried over from a neighbour.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import type {BrokerIconSource} from '../broker/brokerHelpers';

const {listPluginsMock} = vi.hoisted(() => ({
    listPluginsMock: vi.fn(),
}));

vi.mock('$lib/api', () => ({
    zodiosApi: {
        list_plugins_api_v1_brokers_import_plugins_get: listPluginsMock,
    },
}));

async function loadHelpers() {
    return import('../broker/brokerHelpers');
}

/** A plugin made for one broker, ranked as the backend ranks those (100). */
const DEDICATED = {code: 'broker_directa', icon_url: '/plugins/directa.svg', detection_priority: 100};
/** The generic CSV, ranked 0 by the backend: a generic fallback. */
const GENERIC = {code: 'broker_generic_csv', icon_url: '/plugins/generic.svg', detection_priority: 0};
/** A plugin listed without a priority: made for a broker, the backend default (100). */
const UNRANKED = {code: 'broker_unranked', icon_url: '/plugins/unranked.svg'};
/** Either side of the limit (50): 49 is still a generic fallback, 50 no longer is. */
const AT_49 = {code: 'broker_priority_49', icon_url: '/plugins/priority-49.svg', detection_priority: 49};
const AT_50 = {code: 'broker_priority_50', icon_url: '/plugins/priority-50.svg', detection_priority: 50};
/** The list `GET /brokers/import/plugins` answers in these tests. */
const PLUGINS = [DEDICATED, GENERIC, UNRANKED, AT_49, AT_50];

const CUSTOM_ICON = 'https://cdn.example.com/broker.png';
const PORTAL = 'https://www.recrowd.com/login';
const FAVICON = 'https://www.recrowd.com/favicon.ico';

/** Fresh helpers with `PLUGINS` loaded — the state every page reaches once the plugin list is in. */
async function loadHelpersWithPlugins() {
    listPluginsMock.mockResolvedValueOnce(PLUGINS);
    const helpers = await loadHelpers();
    await helpers.ensurePluginIconsLoaded();
    expect(listPluginsMock, 'precondition: the plugin list was asked for once').toHaveBeenCalledTimes(1);
    expect(helpers.getPluginIconUrl(GENERIC.code), 'precondition: the plugin icons are cached').toBe(GENERIC.icon_url);
    return helpers;
}

describe('brokerHelpers', () => {
    beforeEach(() => {
        vi.resetModules();
        listPluginsMock.mockReset();
    });

    describe('getBrokerIconUrl', () => {
        it('returns null for null input', async () => {
            const {getBrokerIconUrl} = await loadHelpers();
            expect(getBrokerIconUrl(null)).toBeNull();
        });

        it('returns null for undefined input', async () => {
            const {getBrokerIconUrl} = await loadHelpers();
            expect(getBrokerIconUrl(undefined)).toBeNull();
        });

        it('returns null for empty object (no fields)', async () => {
            const {getBrokerIconUrl} = await loadHelpers();
            expect(getBrokerIconUrl({})).toBeNull();
        });

        it('returns icon_url directly when present', async () => {
            const {getBrokerIconUrl} = await loadHelpers();
            expect(getBrokerIconUrl({icon_url: 'https://cdn.example.com/broker.png'})).toBe('https://cdn.example.com/broker.png');
        });

        it('prefers icon_url over portal_url', async () => {
            const {getBrokerIconUrl} = await loadHelpers();
            expect(
                getBrokerIconUrl({
                    icon_url: 'https://cdn.example.com/broker.png',
                    portal_url: 'https://www.directa.it',
                }),
            ).toBe('https://cdn.example.com/broker.png');
        });

        it('derives favicon from portal_url when icon_url absent', async () => {
            const {getBrokerIconUrl} = await loadHelpers();
            expect(getBrokerIconUrl({portal_url: 'https://www.directa.it'})).toBe('https://www.directa.it/favicon.ico');
        });

        it('derives favicon from nested portal_url path', async () => {
            const {getBrokerIconUrl} = await loadHelpers();
            expect(getBrokerIconUrl({portal_url: 'https://www.recrowd.com/login'})).toBe('https://www.recrowd.com/favicon.ico');
        });

        it('returns null for invalid portal_url', async () => {
            const {getBrokerIconUrl} = await loadHelpers();
            expect(getBrokerIconUrl({portal_url: 'not-a-valid-url'})).toBeNull();
        });

        it('falls through to favicon when icon_url is blank', async () => {
            const {getBrokerIconUrl} = await loadHelpers();
            expect(getBrokerIconUrl({icon_url: '   ', portal_url: 'https://www.directa.it'})).toBe('https://www.directa.it/favicon.ico');
        });

        it('returns null when only default_import_plugin and cache is empty', async () => {
            const {getBrokerIconUrl} = await loadHelpers();
            expect(getBrokerIconUrl({default_import_plugin: 'broker_generic_csv'})).toBeNull();
        });
    });

    describe('getBrokerIconCandidates — custom, plugin made for the broker, portal favicon, generic fallback plugin', () => {
        const cases: Array<{name: string; broker: BrokerIconSource; expected: string[]}> = [
            {
                name: '(i) custom icon, dedicated plugin and portal → custom, plugin, favicon',
                broker: {icon_url: CUSTOM_ICON, portal_url: PORTAL, default_import_plugin: DEDICATED.code},
                expected: [CUSTOM_ICON, DEDICATED.icon_url, FAVICON],
            },
            {
                name: '(ii) dedicated plugin and portal → plugin, favicon',
                broker: {portal_url: PORTAL, default_import_plugin: DEDICATED.code},
                expected: [DEDICATED.icon_url, FAVICON],
            },
            {
                name: '(iii) generic fallback plugin (detection_priority 0) and portal → favicon, plugin',
                broker: {portal_url: PORTAL, default_import_plugin: GENERIC.code},
                expected: [FAVICON, GENERIC.icon_url],
            },
            {
                name: '(iv) generic fallback plugin alone → plugin',
                broker: {default_import_plugin: GENERIC.code},
                expected: [GENERIC.icon_url],
            },
            {
                name: '(v) portal alone → favicon',
                broker: {portal_url: PORTAL},
                expected: [FAVICON],
            },
            {
                name: 'custom icon, generic fallback plugin and portal → custom, favicon, plugin',
                broker: {icon_url: CUSTOM_ICON, portal_url: PORTAL, default_import_plugin: GENERIC.code},
                expected: [CUSTOM_ICON, FAVICON, GENERIC.icon_url],
            },
            {
                name: 'a plugin listed without a priority is made for a broker → plugin, favicon',
                broker: {portal_url: PORTAL, default_import_plugin: UNRANKED.code},
                expected: [UNRANKED.icon_url, FAVICON],
            },
            {
                name: 'detection_priority 49, below the limit → favicon, plugin',
                broker: {portal_url: PORTAL, default_import_plugin: AT_49.code},
                expected: [FAVICON, AT_49.icon_url],
            },
            {
                name: 'detection_priority 50, at the limit → plugin, favicon',
                broker: {portal_url: PORTAL, default_import_plugin: AT_50.code},
                expected: [AT_50.icon_url, FAVICON],
            },
        ];

        // A loop rather than `it.each`: `$name` titles are cut at 40 characters, and the order is the title.
        for (const {name, broker, expected} of cases) {
            it(name, async () => {
                const {getBrokerIconCandidates} = await loadHelpersWithPlugins();

                expect(getBrokerIconCandidates(broker)).toEqual(expected);
            });
        }

        it('(vi) before the plugin list is loaded no plugin icon is a candidate — the same brokers get theirs once it is', async () => {
            listPluginsMock.mockResolvedValueOnce(PLUGINS);
            const {ensurePluginIconsLoaded, getBrokerIconCandidates} = await loadHelpers();
            const dedicated = {portal_url: PORTAL, default_import_plugin: DEDICATED.code};
            const generic = {portal_url: PORTAL, default_import_plugin: GENERIC.code};

            expect(getBrokerIconCandidates(dedicated), 'dedicated plugin, list not loaded').toEqual([FAVICON]);
            expect(getBrokerIconCandidates(generic), 'generic plugin, list not loaded').toEqual([FAVICON]);
            expect(getBrokerIconCandidates({default_import_plugin: DEDICATED.code}), 'plugin alone, list not loaded').toEqual([]);
            expect(listPluginsMock, 'the sync lookup never loads the plugin list itself').not.toHaveBeenCalled();

            await ensurePluginIconsLoaded();

            expect(getBrokerIconCandidates(dedicated), 'presence control: once loaded, the dedicated plugin leads').toEqual([DEDICATED.icon_url, FAVICON]);
            expect(getBrokerIconCandidates(generic), 'presence control: once loaded, the generic plugin follows the favicon').toEqual([FAVICON, GENERIC.icon_url]);
        });
    });

    describe('isFallbackPluginCode', () => {
        it('is false until the plugin list is loaded — even for the generic CSV — and true for it after', async () => {
            listPluginsMock.mockResolvedValueOnce(PLUGINS);
            const {ensurePluginIconsLoaded, isFallbackPluginCode} = await loadHelpers();

            expect(isFallbackPluginCode(GENERIC.code), 'list not loaded').toBe(false);

            await ensurePluginIconsLoaded();

            expect(isFallbackPluginCode(GENERIC.code), 'list loaded').toBe(true);
        });

        const cases: Array<{code: string | null | undefined; expected: boolean; why: string}> = [
            {code: GENERIC.code, expected: true, why: 'detection_priority 0'},
            {code: AT_49.code, expected: true, why: 'detection_priority 49, below the limit'},
            {code: AT_50.code, expected: false, why: 'detection_priority 50, at the limit'},
            {code: DEDICATED.code, expected: false, why: 'detection_priority 100'},
            {code: UNRANKED.code, expected: false, why: 'listed without a priority: the default, 100'},
            {code: 'broker_not_listed', expected: false, why: 'not in the list'},
            {code: `  ${GENERIC.code}  `, expected: true, why: 'padded with blanks: trimmed, as getPluginIconUrl trims'},
            {code: '   ', expected: false, why: 'blank'},
            {code: null, expected: false, why: 'null'},
            {code: undefined, expected: false, why: 'undefined'},
        ];

        for (const {code, expected, why} of cases) {
            it(`${JSON.stringify(code) ?? 'undefined'} → ${expected} (${why})`, async () => {
                const {isFallbackPluginCode} = await loadHelpersWithPlugins();

                expect(isFallbackPluginCode(code)).toBe(expected);
            });
        }
    });

    describe('the helpers built on the candidates keep their order', () => {
        it('getBrokerIconUrl: a dedicated plugin’s icon before the favicon, the favicon before a generic plugin’s icon', async () => {
            const {getBrokerIconUrl} = await loadHelpersWithPlugins();

            expect(getBrokerIconUrl({portal_url: PORTAL, default_import_plugin: DEDICATED.code})).toBe(DEDICATED.icon_url);
            expect(getBrokerIconUrl({portal_url: PORTAL, default_import_plugin: GENERIC.code})).toBe(FAVICON);
        });

        it('getBrokerIconCandidatesById / getBrokerIconUrlById: the same order from a list and from a map', async () => {
            const {getBrokerIconCandidatesById, getBrokerIconUrlById} = await loadHelpersWithPlugins();
            const list = [
                {id: 7, name: 'Dedicated', portal_url: PORTAL, default_import_plugin: DEDICATED.code},
                {id: 8, name: 'Generic', portal_url: PORTAL, default_import_plugin: GENERIC.code},
            ];
            const byId = new Map(list.map((broker) => [broker.id, broker]));

            for (const [label, brokers] of [
                ['list', list],
                ['map', byId],
            ] as const) {
                expect(getBrokerIconCandidatesById(7, brokers), `${label}: dedicated plugin`).toEqual([DEDICATED.icon_url, FAVICON]);
                expect(getBrokerIconCandidatesById(8, brokers), `${label}: generic plugin`).toEqual([FAVICON, GENERIC.icon_url]);
                expect(getBrokerIconUrlById(7, brokers), `${label}: dedicated plugin`).toBe(DEDICATED.icon_url);
                expect(getBrokerIconUrlById(8, brokers), `${label}: generic plugin`).toBe(FAVICON);
            }
        });
    });

    describe('getBrokerIconHtml', () => {
        it('returns visible briefcase fallback when broker has no candidates', async () => {
            const {getBrokerIconHtml} = await loadHelpers();
            const html = getBrokerIconHtml(null, {width: 18, height: 18});

            expect(html).toContain('display:inline-flex');
            expect(html).toContain('<svg');
        });

        it('encodes remaining candidates into chained img html: src is the first candidate, data-fallbacks the rest in order', async () => {
            const {getBrokerIconHtml, getBrokerIconImgHtml} = await loadHelpersWithPlugins();

            const generic = getBrokerIconImgHtml({portal_url: PORTAL, default_import_plugin: GENERIC.code}, {width: 16, height: 16});
            expect(generic, 'generic fallback plugin: the favicon is tried first').toContain(`src="${FAVICON}"`);
            expect(generic, 'generic fallback plugin: its icon is the fallback').toContain(`data-fallbacks="${escapeHtml(JSON.stringify([GENERIC.icon_url]))}"`);

            const dedicated = getBrokerIconImgHtml({portal_url: PORTAL, default_import_plugin: DEDICATED.code}, {width: 16, height: 16});
            expect(dedicated, 'dedicated plugin: its icon is tried first').toContain(`src="${DEDICATED.icon_url}"`);
            expect(dedicated, 'dedicated plugin: the favicon is the fallback').toContain(`data-fallbacks="${escapeHtml(JSON.stringify([FAVICON]))}"`);

            const withBriefcase = getBrokerIconHtml({portal_url: PORTAL, default_import_plugin: DEDICATED.code});
            expect(withBriefcase, 'the briefcase variant chains the same img').toContain(`src="${DEDICATED.icon_url}"`);
            expect(withBriefcase).toContain(`data-fallbacks="${escapeHtml(JSON.stringify([FAVICON]))}"`);
        });
    });
});
