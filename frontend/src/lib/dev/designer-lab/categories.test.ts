// @vitest-environment jsdom
/**
 * Designer Lab — the chart categories the engine answers for (`engine/categories.ts`, contract C1–C4 with DV).
 *
 * Every chart reads the colour of an asset type, a sector or a bucket through `categoryColor` of
 * `lib/theme/chartCategories.ts`, which in a debug build first asks the Lab (C3). The engine holds the `category`
 * changes of the applied state and answers by key, never by value: a theme's own change beats one for both themes, the
 * two buckets answer for both kinds, and a key is compared as DV compares it (case, spaces and underscores ignored).
 * The answer is what a canvas reads — `#rrggbb` when opaque, `rgba()` when translucent — resolved at each ask, so a
 * `var()` follows the page.
 *
 * Two things are held against DV's real module rather than against a copy: the key rule (`categoryKey` is DV's own
 * `lookupKey`, the function itself; and every variant DV's `categoryColor` reads as a key of its tables must be read the
 * same way here, and only those), and the hook itself (the real `categoryColor` returns the engine's answer only when
 * `__LF_DESIGNER_LAB__` is on). The keys and the table colours are read from that module at run time; every colour a
 * change writes is made up by the test.
 *
 * jsdom: `resolveTarget` reads variables with `getComputedStyle(<html>)`, and jsdom answers the custom properties set
 * on `<html>`.
 */

import {afterEach, describe, expect, it, vi} from 'vitest';
import {CATEGORY_BUCKETS, CATEGORY_KEYS, categoryColor as chartCategoryColor, lookupKey, type CategoryKind} from '$lib/theme/chartCategories';
import {categoryColor, categoryKey, categoryTargetKey, setCategoryChanges} from './engine/categories';
import {changeId} from './store';
import type {LabChange, Scope} from './types';

/** A `category` change as the Lab stores it. */
function category(target: string, scope: Scope, to: string): LabChange {
    const fields = {layer: 'category' as const, target, scope, from: '', to};
    return {...fields, id: changeId(fields)};
}

const html = () => document.documentElement;

/** Made-up colours, none of them a table value (checked where it matters). */
const RED = '#a11b2c';
const BLUE = '#1b2ca1';
const GREEN = '#2ca11b';

afterEach(() => {
    setCategoryChanges([]);
    html().removeAttribute('style');
    vi.unstubAllGlobals();
});

describe('categoryKey and categoryTargetKey', () => {
    it('is DV’s own `lookupKey` (TD-1), the function itself: no copy of the rule left to drift from the tables it keys', () => {
        expect(categoryKey, 'the engine keys its edits with the very function DV keys its tables with').toBe(lookupKey);
    });

    it('compares a key without its case, spaces and underscores, as DV does — a hyphen still counts', () => {
        for (const variant of ['Health Care', 'health care', 'HEALTH_CARE', 'HealthCare', 'healthcare', ' Health  Care ', 'Health\tCare']) expect(categoryKey(variant), variant).toBe('HEALTHCARE');
        expect(categoryKey('Health-Care')).toBe('HEALTH-CARE');
    });

    it('gives the lookup key of a category target, and null for any other target', () => {
        expect(categoryTargetKey('sector:Health Care')).toBe('sector:HEALTHCARE');
        expect(categoryTargetKey('type:real_estate')).toBe('type:REALESTATE');
        expect(categoryTargetKey('bucket:Liquidity')).toBe('bucket:LIQUIDITY');
        for (const target of ['--lf-surface-card', '#1b2ca1', 'region:Europe', 'type:', 'sector', 'TYPE:ETF', ' type:ETF']) expect(categoryTargetKey(target), target).toBeNull();
    });
});

describe('setCategoryChanges and categoryColor — what the engine answers', () => {
    it('answers a change for one theme in that theme only, and for its own kind only', () => {
        setCategoryChanges([category('type:AAA', 'light', RED)]);
        expect(categoryColor('type', 'AAA', false)).toBe(RED);
        expect(categoryColor('type', 'AAA', true)).toBeUndefined();
        expect(categoryColor('sector', 'AAA', false)).toBeUndefined();

        setCategoryChanges([category('sector:Zed', 'dark', RED)]);
        expect(categoryColor('sector', 'Zed', true)).toBe(RED);
        expect(categoryColor('sector', 'Zed', false)).toBeUndefined();
        expect(categoryColor('type', 'Zed', true), 'the same key of the other kind is another category').toBeUndefined();
    });

    it('answers a change for both themes in both', () => {
        setCategoryChanges([category('type:AAA', 'both', RED)]);
        expect(categoryColor('type', 'AAA', false)).toBe(RED);
        expect(categoryColor('type', 'AAA', true)).toBe(RED);
    });

    it.each([
        ['the change for both first', [category('type:AAA', 'both', RED), category('type:AAA', 'light', BLUE), category('type:AAA', 'dark', GREEN)]],
        ['the theme changes first', [category('type:AAA', 'dark', GREEN), category('type:AAA', 'light', BLUE), category('type:AAA', 'both', RED)]],
    ])('gives a theme’s own change precedence over one for both themes, %s', (_order, changes) => {
        setCategoryChanges(changes);
        expect(categoryColor('type', 'AAA', false)).toBe(BLUE);
        expect(categoryColor('type', 'AAA', true)).toBe(GREEN);
    });

    it('keeps the change for both where a theme has none of its own', () => {
        setCategoryChanges([category('sector:Zed', 'light', BLUE), category('sector:Zed', 'both', RED)]);
        expect(categoryColor('sector', 'Zed', false)).toBe(BLUE);
        expect(categoryColor('sector', 'Zed', true)).toBe(RED);
    });

    it('answers the two buckets for both kinds', () => {
        setCategoryChanges([category('bucket:Liquidity', 'both', RED), category('bucket:Unknown', 'dark', BLUE)]);
        for (const kind of ['type', 'sector'] as const) {
            expect(categoryColor(kind, 'Liquidity', false), kind).toBe(RED);
            expect(categoryColor(kind, 'LIQUIDITY', true), kind).toBe(RED);
            expect(categoryColor(kind, 'unknown', true), kind).toBe(BLUE);
            expect(categoryColor(kind, 'Unknown', false), `${kind}: a dark change`).toBeUndefined();
        }
    });

    it('finds a key whatever its case, spaces and underscores, on both sides', () => {
        setCategoryChanges([category('sector:Health Care', 'both', RED)]);
        for (const asked of ['Health Care', 'health care', 'HEALTH_CARE', 'HealthCare']) expect(categoryColor('sector', asked, false), asked).toBe(RED);
        expect(categoryColor('type', 'Health Care', false), 'another kind').toBeUndefined();

        setCategoryChanges([category('sector:HEALTH_CARE', 'both', BLUE)]);
        expect(categoryColor('sector', 'Health Care', true)).toBe(BLUE);
    });

    it('answers an opaque colour as a canvas reads it: `#rrggbb`, lower case', () => {
        for (const [to, expected] of [
            ['#A11B2C', '#a11b2c'],
            ['#abc', '#aabbcc'],
            ['rgb(161 27 44)', '#a11b2c'],
            ['color-mix(in oklab, #a11b2c 100%, transparent)', '#a11b2c'],
        ]) {
            setCategoryChanges([category('type:AAA', 'both', to)]);
            expect(categoryColor('type', 'AAA', false), to).toBe(expected);
        }
    });

    it('answers a translucent colour as `rgba()`, a translucent mix included', () => {
        setCategoryChanges([category('type:AAA', 'light', '#ff00aa80'), category('type:AAA', 'dark', 'color-mix(in oklab, #ff0000 40%, transparent)')]);
        // 0x80 is 128/255: 0.502 at three decimals.
        expect(categoryColor('type', 'AAA', false)).toBe('rgba(255, 0, 170, 0.502)');
        expect(categoryColor('type', 'AAA', true)).toBe('rgba(255, 0, 0, 0.4)');
    });

    it('resolves a `var()` from <html> at each ask, so an edit of the variable reaches the next draw', () => {
        html().style.setProperty('--lf-test-category', '#102030');
        // The premise: jsdom answers a custom property set on <html>.
        expect(getComputedStyle(html()).getPropertyValue('--lf-test-category').trim()).toBe('#102030');
        setCategoryChanges([category('type:AAA', 'light', 'var(--lf-test-category)'), category('type:AAA', 'dark', 'color-mix(in oklab, var(--lf-test-category) 50%, transparent)')]);
        expect(categoryColor('type', 'AAA', false)).toBe('#102030');
        expect(categoryColor('type', 'AAA', true)).toBe('rgba(16, 32, 48, 0.5)');

        html().style.setProperty('--lf-test-category', '#405060');
        expect(categoryColor('type', 'AAA', false)).toBe('#405060');

        html().style.removeProperty('--lf-test-category');
        expect(categoryColor('type', 'AAA', false), 'the variable is gone').toBeUndefined();
        expect(categoryColor('type', 'AAA', true), 'the variable is gone').toBeUndefined();
    });

    it('answers nothing for a value that does not resolve: an undefined variable, a word', () => {
        setCategoryChanges([category('type:AAA', 'light', 'var(--lf-test-undefined)'), category('type:AAA', 'dark', 'nonsense')]);
        expect(categoryColor('type', 'AAA', false)).toBeUndefined();
        expect(categoryColor('type', 'AAA', true)).toBeUndefined();
    });

    it('answers nothing without changes, and nothing once they are cleared', () => {
        expect(categoryColor('type', 'AAA', false)).toBeUndefined();
        setCategoryChanges([category('type:AAA', 'both', RED)]);
        expect(categoryColor('type', 'AAA', false), 'barrier: the change answered').toBe(RED);
        expect(setCategoryChanges([])).toBe(0);
        expect(categoryColor('type', 'AAA', false)).toBeUndefined();
        expect(categoryColor('type', 'AAA', true)).toBeUndefined();
    });

    it('counts the changes that name a category, and ignores every other change', () => {
        const others: LabChange[] = [
            {id: 'css-var:--lf-x@both', layer: 'css-var', target: '--lf-x', scope: 'both', from: '', to: RED},
            {id: 'chart-color:#a11b2c@both', layer: 'chart-color', target: '#a11b2c', scope: 'both', from: '#a11b2c', to: BLUE, alphaVariants: true},
            // A `category` change whose target names no category: never applied, never counted.
            category('region:Europe', 'both', GREEN),
        ];
        const count = setCategoryChanges([category('type:AAA', 'light', RED), category('type:AAA', 'dark', BLUE), ...others, category('bucket:Unknown', 'both', GREEN)]);
        expect(count).toBe(3);
        expect(categoryColor('type', 'Unknown', false)).toBe(GREEN);
        expect(categoryColor('type', 'Europe', false)).toBeUndefined();
        expect(categoryColor('sector', 'Europe', false)).toBeUndefined();
    });
});

// The keys, both kinds with the buckets, as DV's tables hold them.
const KINDS: readonly CategoryKind[] = ['type', 'sector'];
const keysOf = (kind: CategoryKind) => [...CATEGORY_KEYS[kind], ...CATEGORY_BUCKETS];
const targetOf = (kind: CategoryKind, key: string) => (CATEGORY_BUCKETS.includes(key) ? `bucket:${key}` : `${kind}:${key}`);

/** Ways of writing a key: the ones DV's lookup reads as the key, and some it must not. */
const VARIANTS: readonly ((key: string) => string)[] = [
    (k) => k,
    (k) => k.toLowerCase(),
    (k) => k.toUpperCase(),
    (k) => k.replace(/ /g, '_'),
    (k) => k.replace(/ /g, '_').toUpperCase(),
    (k) => k.replace(/_/g, ' '),
    (k) => k.replace(/_/g, ' ').toLowerCase(),
    (k) => k.replace(/[ _]/g, ''),
    (k) => k.replace(/[ _]/g, '\t'),
    (k) => ` ${k}  `,
    (k) => k.split('').join('_'),
    (k) => k.replace(/[ _]/g, '-'),
    (k) => `${k}-`,
    (k) => `${k}.`,
    (k) => `${k}S`,
];

describe('the key rule, held to DV’s real `categoryColor`', () => {
    it('reads as the same key exactly the variants DV reads as that key', () => {
        // DV is the oracle: a variant is its key when the real function gives it the key's colours in both themes. That
        // tells keys apart only where the key's pair is its own, and is not the pair DV falls back to for a key outside
        // its tables (the unclassified one): any misspelling would read as that key.
        const pair = (kind: CategoryKind, key: string) => `${chartCategoryColor(kind, key, false)}|${chartCategoryColor(kind, key, true)}`;
        const mismatches: string[] = [];
        let decided = 0;
        let same = 0;
        for (const kind of KINDS) {
            const pairs = keysOf(kind).map((key) => pair(kind, key));
            const fallback = pair(kind, '<no such category>');
            const decisive = keysOf(kind).filter((key) => pair(kind, key) !== fallback && pairs.filter((p) => p === pair(kind, key)).length === 1);
            expect(decisive.length, `${kind}: keys with colours of their own`).toBeGreaterThan(0);
            for (const key of decisive) {
                setCategoryChanges([category(targetOf(kind, key), 'both', RED)]);
                for (const variant of VARIANTS.map((v) => v(key))) {
                    const dvSame = pair(kind, variant) === pair(kind, key);
                    const keySame = categoryKey(variant) === categoryKey(key);
                    const answered = categoryColor(kind, variant, false) === RED && categoryColor(kind, variant, true) === RED;
                    decided++;
                    if (dvSame) same++;
                    if (keySame !== dvSame || answered !== dvSame) mismatches.push(`${kind} ${JSON.stringify(key)} as ${JSON.stringify(variant)}: DV ${dvSame ? 'same' : 'other'}, categoryKey ${keySame ? 'same' : 'other'}, engine ${answered ? 'answers' : 'silent'}`);
                }
            }
        }
        expect(mismatches).toEqual([]);
        // The oracle saw both answers: some variants are the key, some are not.
        expect(same).toBeGreaterThan(0);
        expect(same).toBeLessThan(decided);
    });

    it('answers every bucket of DV’s tables for both kinds, and no table key for the other kind', () => {
        for (const bucket of CATEGORY_BUCKETS) {
            setCategoryChanges([category(`bucket:${bucket}`, 'both', RED)]);
            for (const kind of KINDS) expect(categoryColor(kind, bucket, false), `${kind} ${bucket}`).toBe(RED);
        }
        for (const kind of KINDS) {
            const other: CategoryKind = kind === 'type' ? 'sector' : 'type';
            // A key of one table only: written in both tables (`OTHER`, `Other`), it is two categories.
            const key = CATEGORY_KEYS[kind].find((k) => !CATEGORY_KEYS[other].some((o) => categoryKey(o) === categoryKey(k)));
            expect(key, `${kind}: a key of its own`).toBeDefined();
            setCategoryChanges([category(`${kind}:${key}`, 'both', RED)]);
            expect(categoryColor(kind, key as string, true)).toBe(RED);
            expect(categoryColor(other, key as string, true)).toBeUndefined();
        }
    });
});

describe('C3 end to end — the real `categoryColor` asks the engine', () => {
    const KEY = CATEGORY_KEYS.type[0];
    /** The table's colours of the key, read before any hook is published. */
    const TABLE = {light: chartCategoryColor('type', KEY, false), dark: chartCategoryColor('type', KEY, true)};

    /** Publish the engine as the Lab client does (`window.__lfDesignerLab`), with `__LF_DESIGNER_LAB__` as given. */
    function publish(flag: boolean | undefined) {
        vi.stubGlobal('__LF_DESIGNER_LAB__', flag);
        vi.stubGlobal('__lfDesignerLab', {categoryColor});
    }

    it('returns the edited colour only in a debug build, and the table’s colour otherwise', () => {
        // The premise: the edit is not already the table's colour.
        expect(TABLE.light.toLowerCase()).not.toBe(RED);
        setCategoryChanges([category(`type:${KEY}`, 'light', RED)]);

        publish(true);
        expect(chartCategoryColor('type', KEY, false)).toBe(RED);
        expect(chartCategoryColor('type', KEY.toLowerCase(), false), 'the key as another caller writes it').toBe(RED);
        expect(chartCategoryColor('type', KEY, true), 'a light change leaves the dark theme to the table').toBe(TABLE.dark);

        publish(false);
        expect(chartCategoryColor('type', KEY, false)).toBe(TABLE.light);

        publish(undefined);
        expect(chartCategoryColor('type', KEY, false)).toBe(TABLE.light);
    });

    it('returns the table’s colour once the engine holds no change', () => {
        setCategoryChanges([category(`type:${KEY}`, 'both', RED)]);
        publish(true);
        expect(chartCategoryColor('type', KEY, true), 'barrier: the edit is read').toBe(RED);
        setCategoryChanges([]);
        expect(chartCategoryColor('type', KEY, true)).toBe(TABLE.dark);
        expect(chartCategoryColor('type', KEY, false)).toBe(TABLE.light);
    });

    it('hands a bucket’s edit to both kinds, and a translucent edit as `rgba()`', () => {
        const bucket = CATEGORY_BUCKETS[0];
        const tableLight = Object.fromEntries(KINDS.map((kind) => [kind, chartCategoryColor(kind, bucket, false)]));
        setCategoryChanges([category(`bucket:${bucket}`, 'dark', '#ff00aa80')]);
        publish(true);
        for (const kind of KINDS) {
            expect(chartCategoryColor(kind, bucket, true), kind).toBe('rgba(255, 0, 170, 0.502)');
            expect(chartCategoryColor(kind, bucket, false), `${kind}: a dark change leaves the light theme to the table`).toBe(tableLight[kind]);
        }
    });
});
