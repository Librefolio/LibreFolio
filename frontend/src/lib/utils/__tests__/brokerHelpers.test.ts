/**
 * Unit tests for brokerHelpers — sync candidate resolution + raw HTML helper.
 *
 * Authoritative priority:
 *   1. icon_url
 *   2. portal_url/favicon.ico
 *   3. default_import_plugin icon
 *   4. caller/UI fallback (system briefcase icon)
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

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

    describe('getBrokerIconCandidates', () => {
        it('keeps favicon before plugin icon when cache is populated', async () => {
            listPluginsMock.mockResolvedValueOnce([{code: 'broker_generic_csv', icon_url: '/plugins/generic.svg'}]);
            const {ensurePluginIconsLoaded, getBrokerIconCandidates} = await loadHelpers();
            await ensurePluginIconsLoaded();

            expect(
                getBrokerIconCandidates({
                    portal_url: 'https://www.recrowd.com/login',
                    default_import_plugin: 'broker_generic_csv',
                }),
            ).toEqual(['https://www.recrowd.com/favicon.ico', '/plugins/generic.svg']);
        });
    });

    describe('getBrokerIconHtml', () => {
        it('returns visible briefcase fallback when broker has no candidates', async () => {
            const {getBrokerIconHtml} = await loadHelpers();
            const html = getBrokerIconHtml(null, {width: 18, height: 18});

            expect(html).toContain('display:inline-flex');
            expect(html).toContain('<svg');
        });

        it('encodes remaining candidates into chained img html', async () => {
            listPluginsMock.mockResolvedValueOnce([{code: 'broker_generic_csv', icon_url: '/plugins/generic.svg'}]);
            const {ensurePluginIconsLoaded, getBrokerIconImgHtml} = await loadHelpers();
            await ensurePluginIconsLoaded();

            const html = getBrokerIconImgHtml(
                {
                    portal_url: 'https://www.recrowd.com/login',
                    default_import_plugin: 'broker_generic_csv',
                },
                {width: 16, height: 16},
            );

            expect(html).toContain('src="https://www.recrowd.com/favicon.ico"');
            expect(html).toContain('/plugins/generic.svg');
            expect(html).toContain('data-fallbacks=');
        });
    });
});
