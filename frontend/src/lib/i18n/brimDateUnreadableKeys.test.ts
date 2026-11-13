// @vitest-environment node
/**
 * importWizard.brimNotice.date_unreadable / date_unreadable_more — the notices of the generic CSV for dates it cannot read (FB-18b; Vitest, node).
 *
 * Why. The generic CSV plugin no longer reports an unreadable date as a plain English string: it sends a `BRIMNotice` with the stable code
 * `date_unreadable` (context `{row, value, order}`, `order` one of the six values of the `date_order` setting) and, past the first 20 rows, ONE
 * `date_unreadable_more` (context `{n}`). The wording is looked up by `resolveBrimNoticeMessage` under `importWizard.brimNotice.<code>`; a missing
 * key silently falls back to the plugin's English message, and the catalogue build fills a missing it, fr or es entry from English — so a forgotten
 * key would never show. This file reads the SOURCES, `lib/features/transactions/import/i18n/<lang>.json`, directly, never the generated catalogue.
 *
 * Contract (structure and behaviour, never the words, which are the translators').
 *   - both keys exist, non-empty, in the four sources, nested `importWizard` → `brimNotice` → code like the other notices; it, fr and es differ from
 *     the English text (a copy of English is an untranslated key);
 *   - `date_unreadable` carries `{row}` and `{value}` and an ICU `select` on `order` with the six options `day_first`, `month_first`,
 *     `day_first_short`, `month_first_short`, `year_first_short`, `year_first` (no `other`-only shortcut: every option is named);
 *   - `date_unreadable_more` is an ICU plural on `n`, and one and many read differently;
 *   - through `resolveBrimNoticeMessage` with the real catalogue in en and it: the sentence holds the row and the date as written, is not the notice's
 *     raw message, leaves no placeholder behind, and the six orders give six different sentences; the `_more` notice reads differently for n = 1 and 5.
 *
 * Control. The reader is proven on a key that exists today (`importWizard.brimNotice.corporate_action`): found, non-empty, in the four languages; an
 * invented key is reported missing; the formatter tells a plural's one from many and a select's options apart.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action `core-unit`).
 */
import {readFileSync} from 'node:fs';
import {getMessageFormatter} from 'svelte-i18n';
import {describe, expect, it} from 'vitest';
import type {BrimNotice} from '$lib/types';
import {resolveBrimNoticeMessage} from '$lib/features/transactions/resolveBrimNotice';

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
type Lang = (typeof LANGUAGES)[number];
const TRANSLATIONS: readonly Lang[] = ['it', 'fr', 'es'];
const PREFIX = 'importWizard.brimNotice.';
const NEW_KEYS = ['date_unreadable', 'date_unreadable_more'] as const;
const ORDERS = ['day_first', 'month_first', 'day_first_short', 'month_first_short', 'year_first_short', 'year_first'] as const;

/** `lib/features/transactions/import/i18n/<lang>.json`, read from disk, never through the generated catalogue (which fills gaps from English). */
function importWizardSource(lang: Lang): unknown {
    return JSON.parse(readFileSync(new URL(`../features/transactions/import/i18n/${lang}.json`, import.meta.url), 'utf8'));
}

/** The value at a dotted key of a nested source; `undefined` when any step is missing or not an object. */
function valueAt(source: unknown, key: string): unknown {
    let current: unknown = source;
    for (const step of key.split('.')) {
        if (typeof current !== 'object' || current === null || !Object.hasOwn(current, step)) return undefined;
        current = (current as Record<string, unknown>)[step];
    }
    return current;
}

/** The text of `importWizard.brimNotice.<name>` in one language's source, or `undefined`. */
function noticeText(lang: Lang, name: string): string | undefined {
    const value = valueAt(importWizardSource(lang), PREFIX + name);
    return typeof value === 'string' ? value : undefined;
}

/** `message` formatted by the runtime's own formatter for `lang`. */
function render(message: string, lang: Lang, values: Record<string, string | number>): string {
    return String(getMessageFormatter(message, lang).format(values));
}

/** A `$t` over the real source of one language: walks the dotted key, formats with ICU, echoes the key on a miss (what the runtime does). */
function translatorOf(lang: Lang) {
    return (key: string, opts?: {values?: Record<string, any>}): string => {
        const text = noticeText(lang, key.slice(PREFIX.length));
        if (!key.startsWith(PREFIX) || text === undefined) return key;
        return render(text, lang, opts?.values ?? {});
    };
}

/** The raw message the plugin sends, marked so that a hit on the catalogue cannot be mistaken for the fallback. */
const RAW = 'RAW-PLUGIN-ENGLISH-MESSAGE';
const notice = (code: string, context: Record<string, unknown>): BrimNotice => ({severity: 'warning', code, message: RAW, evidence: [], context}) as unknown as BrimNotice;

describe('importWizard.brimNotice — unreadable dates of the generic CSV, in the four languages (FB-18b)', () => {
    it('Control: the reader finds corporate_action in the four sources, an invented key is reported missing, the formatter tells plural and select apart', () => {
        for (const lang of LANGUAGES) expect(noticeText(lang, 'corporate_action')?.trim().length ?? 0, `Control: corporate_action is a non-empty string in ${lang}.json`).toBeGreaterThan(0);
        expect(noticeText('en', 'noSuchKey'), 'Control: an invented key is reported missing').toBeUndefined();
        const plural = '{n, plural, one {# thing} other {# things}}';
        expect(render(plural, 'en', {n: 1}), 'Control: one').toBe('1 thing');
        expect(render(plural, 'en', {n: 5}), 'Control: many').toBe('5 things');
        const select = '{order, select, a {A} b {B} other {O}}';
        expect([render(select, 'en', {order: 'a'}), render(select, 'en', {order: 'b'})], 'Control: a select picks its option').toEqual(['A', 'B']);
    });

    for (const lang of LANGUAGES) {
        describe(lang, () => {
            it.each(NEW_KEYS)('%s exists and is not empty', (name) => {
                expect(noticeText(lang, name)?.trim().length ?? 0, `${PREFIX}${name} in importWizard/${lang}.json`).toBeGreaterThan(0);
            });

            it('date_unreadable carries {row}, {value} and an ICU select on order that names all six options', () => {
                const message = noticeText(lang, 'date_unreadable') ?? '';
                expect(message, `date_unreadable (${lang}) has {row}`).toContain('{row}');
                expect(message, `date_unreadable (${lang}) has {value}`).toContain('{value}');
                expect(message, `date_unreadable (${lang}) is an ICU select on order`).toMatch(/\{order\s*,\s*select\s*,/);
                for (const order of ORDERS) expect(message, `date_unreadable (${lang}) names the option ${order}`).toMatch(new RegExp(`(^|[\\s{,])${order}\\s*\\{`));
            });

            it('date_unreadable_more is a plural on n: one and many read differently', () => {
                const message = noticeText(lang, 'date_unreadable_more') ?? '';
                expect(message, `date_unreadable_more (${lang}) is an ICU plural on n`).toMatch(/\{n\s*,\s*plural\s*,/);
                const wording = (n: number) => render(message, lang, {n}).replaceAll(String(n), '#');
                expect(wording(1), `date_unreadable_more (${lang}): the singular reads like the plural`).not.toBe(wording(5));
            });
        });
    }

    for (const lang of TRANSLATIONS) {
        it(`${lang}: the two texts differ from the English ones (a copy of English is an untranslated key)`, () => {
            for (const name of NEW_KEYS) {
                const text = noticeText(lang, name);
                expect(text, `${name} exists in ${lang}`).toBeDefined();
                expect(text, `${name} in ${lang} is the English text`).not.toBe(noticeText('en', name));
            }
        });
    }
});

describe('resolveBrimNoticeMessage over the real catalogue — date_unreadable and date_unreadable_more (FB-18b)', () => {
    for (const lang of ['en', 'it'] as const) {
        describe(lang, () => {
            const t = translatorOf(lang);
            const dateNotice = (order: string) => notice('date_unreadable', {row: 4, value: '25/12/26', order});

            it('a date_unreadable notice resolves to a sentence with the row and the date, not the raw message, no placeholder left', () => {
                const text = resolveBrimNoticeMessage(dateNotice('month_first_short'), t);
                expect(text, 'not the raw message of the notice').not.toBe(RAW);
                expect(text, 'the row').toContain('4');
                expect(text, 'the date as written').toContain('25/12/26');
                expect(text, 'no placeholder left behind').not.toMatch(/[{}]/);
            });

            it.each(ORDERS)('%s resolves too: row, date, no placeholder', (order) => {
                const text = resolveBrimNoticeMessage(dateNotice(order), t);
                expect(text).not.toBe(RAW);
                expect(text).toContain('4');
                expect(text).toContain('25/12/26');
                expect(text).not.toMatch(/[{}]/);
            });

            it('the six orders give six different sentences (each names its own format)', () => {
                const texts = ORDERS.map((order) => resolveBrimNoticeMessage(dateNotice(order), t));
                expect(new Set(texts).size, `six orders, six sentences in ${lang}: ${JSON.stringify(texts)}`).toBe(ORDERS.length);
            });

            it('date_unreadable_more resolves with its count, singular and plural read differently, no placeholder left', () => {
                const one = resolveBrimNoticeMessage(notice('date_unreadable_more', {n: 1}), t);
                const many = resolveBrimNoticeMessage(notice('date_unreadable_more', {n: 5}), t);
                for (const text of [one, many]) {
                    expect(text, 'not the raw message of the notice').not.toBe(RAW);
                    expect(text, 'no placeholder left behind').not.toMatch(/[{}]/);
                }
                expect(one).toContain('1');
                expect(many).toContain('5');
                expect(one.replaceAll('1', '#'), 'the singular reads like the plural').not.toBe(many.replaceAll('5', '#'));
            });
        });
    }
});
