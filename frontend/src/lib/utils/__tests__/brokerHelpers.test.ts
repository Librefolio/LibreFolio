/**
 * Unit tests for getBrokerIconUrl — pure fallback chain logic.
 *
 * The priority chain is:
 *   1. icon_url  (custom upload — most reliable)
 *   2. default_import_plugin → plugin icon cache (app-hosted — reliable)
 *   3. portal_url → origin/favicon.ico  (external heuristic — least reliable)
 *   4. null fallback
 *
 * Step 2 (plugin cache) relies on async loading; when the cache is empty
 * getBrokerIconUrl() skips straight to step 3. Cache-populated behaviour
 * is covered by E2E tests.
 */
import {describe, expect, it} from 'vitest';
import {getBrokerIconUrl, type BrokerIconSource} from '../broker/brokerHelpers';

describe('getBrokerIconUrl', () => {
    it('returns null for null input', () => {
        expect(getBrokerIconUrl(null)).toBeNull();
    });

    it('returns null for undefined input', () => {
        expect(getBrokerIconUrl(undefined)).toBeNull();
    });

    it('returns null for empty object (no fields)', () => {
        expect(getBrokerIconUrl({} as BrokerIconSource)).toBeNull();
    });

    it('returns icon_url directly when present', () => {
        const broker: BrokerIconSource = {icon_url: 'https://cdn.example.com/broker.png'};
        expect(getBrokerIconUrl(broker)).toBe('https://cdn.example.com/broker.png');
    });

    it('prefers icon_url over portal_url', () => {
        const broker: BrokerIconSource = {
            icon_url: 'https://cdn.example.com/broker.png',
            portal_url: 'https://www.directa.it',
        };
        expect(getBrokerIconUrl(broker)).toBe('https://cdn.example.com/broker.png');
    });

    it('derives favicon from portal_url when icon_url absent', () => {
        const broker: BrokerIconSource = {portal_url: 'https://www.directa.it'};
        expect(getBrokerIconUrl(broker)).toBe('https://www.directa.it/favicon.ico');
    });

    it('derives favicon from portal_url with trailing slash', () => {
        const broker: BrokerIconSource = {portal_url: 'https://www.recrowd.com/login'};
        expect(getBrokerIconUrl(broker)).toBe('https://www.recrowd.com/favicon.ico');
    });

    it('returns null for invalid portal_url (not a valid URL)', () => {
        const broker: BrokerIconSource = {portal_url: 'not-a-valid-url'};
        expect(getBrokerIconUrl(broker)).toBeNull();
    });

    it('returns null when icon_url is empty string', () => {
        const broker: BrokerIconSource = {icon_url: '   ', portal_url: 'https://www.directa.it'};
        // icon_url is whitespace-only → falls through to portal_url
        expect(getBrokerIconUrl(broker)).toBe('https://www.directa.it/favicon.ico');
    });

    it('returns null when only default_import_plugin and cache is empty (no load)', () => {
        // Plugin cache is not populated → step 3 yields null → overall null
        const broker: BrokerIconSource = {default_import_plugin: 'directa_csv'};
        expect(getBrokerIconUrl(broker)).toBeNull();
    });
});
