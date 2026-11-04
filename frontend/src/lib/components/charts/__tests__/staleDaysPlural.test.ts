/**
 * T-ST — the days of a stale price read as a real plural, and the badge's abbreviation is the language's own.
 *
 * `chart.tooltip.stale` had `{days}` and a «(s)» («day(s)», «giorno/i», «jour(s)», «día(s)»). It is now an ICU plural per language, and
 * `chart.tooltip.staleBadge` is the short form of the visible `⚠️ Nd` badge: «d» in English and Spanish, «g» in Italian, «j» in French.
 */
import {get} from 'svelte/store';
import {beforeAll, describe, expect, it} from 'vitest';
import {_ as translate, waitLocale} from 'svelte-i18n';
import {setupI18n} from '$test/component';
import {currentLanguage} from '$lib/stores/app/language';

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;

async function inLanguage<T>(lang: (typeof LANGUAGES)[number], read: () => T): Promise<T> {
    await waitLocale(lang);
    currentLanguage.set(lang);
    await waitLocale(lang);
    return read();
}

beforeAll(async () => {
    await setupI18n();
});

describe('chart.tooltip.stale', () => {
    it.each(LANGUAGES)('%s: one day and several days read differently, and neither keeps the «(s)» of the old text', async (lang) => {
        const [one, many] = await inLanguage(lang, () => [get(translate)('chart.tooltip.stale', {values: {days: 1}}), get(translate)('chart.tooltip.stale', {values: {days: 3}})]);
        expect(one).not.toBe('chart.tooltip.stale');
        expect(one, 'a singular and a plural').not.toBe(many);
        for (const text of [one, many]) expect(text, 'no «(s)» and no «/i»').not.toMatch(/\(s\)|\/i\b|\(es\)/);
        expect(one).toContain('1');
        expect(many).toContain('3');
    });
});

describe('chart.tooltip.staleBadge', () => {
    it.each([
        ['en', '5d'],
        ['it', '5g'],
        ['fr', '5j'],
        ['es', '5d'],
    ] as const)('%s: the abbreviation of the days is the language’s own', async (lang, expected) => {
        const text = await inLanguage(lang, () => get(translate)('chart.tooltip.staleBadge', {values: {days: 5}}));
        expect(text).toBe(expected);
    });
});
