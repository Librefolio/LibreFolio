import {afterEach, describe, expect, it, vi} from 'vitest';
import {checkMessageValues, PUBLIC_URL_EXAMPLE_FALLBACK, publicUrlExample} from './publicUrlExample';

describe('publicUrlExample: the address the administrator uses now, as the value to set', () => {
    it.each([
        ['https://librefolio.stargazer-orfe.ts.net', 'https://librefolio.stargazer-orfe.ts.net'],
        ['http://192.168.1.20:6040', 'http://192.168.1.20:6040'],
        ['http://localhost:6040', 'http://localhost:6040'],
    ])('%s stands for itself', (origin, expected) => {
        expect(publicUrlExample(origin)).toBe(expected);
    });

    it.each([['null'], ['file://'], [''], ['chrome-extension://abc'], ['https://user:pw@host'], ['https://host/path']])('%s cannot stand for a public address: the fallback', (origin) => {
        expect(publicUrlExample(origin === 'null' ? null : origin)).toBe(PUBLIC_URL_EXAMPLE_FALLBACK);
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('reads the page address when none is given', () => {
        vi.stubGlobal('window', {location: {origin: 'https://librefolio.example.org'}});
        expect(publicUrlExample()).toBe('https://librefolio.example.org');
    });
});

describe('checkMessageValues: the example only for the two LIBREFOLIO_PUBLIC_URL texts', () => {
    it.each(['email.checks.links.missing', 'email.checks.links.invalid'])('%s gets its example, and keeps its own values', (key) => {
        expect(checkMessageValues(key, {a: 1})).toEqual({a: 1, example: publicUrlExample()});
    });

    it.each(['email.checks.links.ok', 'email.checks.smtp.invalid', 'instance.checks.instanceKey.unusable'])('%s is left as it is', (key) => {
        const params = {variable: 'X'};
        expect(checkMessageValues(key, params)).toBe(params);
    });
});
