/**
 * urlFilters — unit tests
 *
 * The deep-linking contract of every `DataTable` in the app: a filter state has
 * to survive a round trip through the address bar. `parseUrlFilters` reads it
 * back, `buildUrlFilters` writes it out, and the pair is only useful if they
 * agree — a disagreement means a shared link opens on a different table than the
 * one the sender was looking at.
 *
 * That is why the centre of this file is a **round trip** rather than a list of
 * outputs: asserting that `parse` returns a particular object only pins today's
 * shape, while asserting that `build(parse(x))` is `x` pins the property the
 * feature exists for. The per-branch tests around it exist for the cases where
 * the round trip is *deliberately* lossy, and each says why.
 *
 * These four functions are pure — no DOM, no store, no network — so they are
 * unit tests. Reaching the same ground through Playwright would mean loading a
 * page per URL shape and reading state that is never rendered.
 */
import {describe, expect, it, vi} from 'vitest';
import {buildUrlFilters, cleanUrlParams, hasActiveFilters, parseUrlFilters, type UrlFilterConfig} from '../urlFilters';
import type {FilterValue} from '$lib/components/table/types';

const COLUMNS: UrlFilterConfig[] = [
    {urlKey: 'filename', type: 'text'},
    {urlKey: 'broker', type: 'enum'},
    {urlKey: 'size', type: 'size'},
    {urlKey: 'uploaded', type: 'date'},
];

function parse(query: string, columns: UrlFilterConfig[] = COLUMNS) {
    return parseUrlFilters(new URLSearchParams(query), columns);
}

/** The round trip, as a string: parse a query and write it back out. */
function roundTrip(query: string, columns: UrlFilterConfig[] = COLUMNS): string {
    return buildUrlFilters(parse(query, columns), columns).toString();
}

describe('parseUrlFilters', () => {
    it('ignores keys no column declares', () => {
        const filters = parse('filename=report&unknown=x');
        expect([...filters.keys()]).toEqual(['filename']);
    });

    it('ignores a declared key with an empty value', () => {
        expect(parse('filename=&broker=').size).toBe(0);
    });

    describe('text', () => {
        it('defaults to contains when no mode is appended', () => {
            expect(parse('filename=report').get('filename')).toEqual({type: 'text', value: 'report', matchMode: 'contains'});
        });

        it.each(['startsWith', 'endsWith', 'equals', 'contains'] as const)('reads the %s mode off the suffix', (mode) => {
            expect(parse(`filename=report:${mode}`).get('filename')).toEqual({type: 'text', value: 'report', matchMode: mode});
        });

        it('keeps a colon that is not a known mode as part of the value', () => {
            expect(parse('filename=a:b').get('filename')).toEqual({type: 'text', value: 'a:b', matchMode: 'contains'});
        });

        it('splits on the *last* colon, so a value may itself contain one', () => {
            expect(parse('filename=a:b:equals').get('filename')).toEqual({type: 'text', value: 'a:b', matchMode: 'equals'});
        });

        it('treats a leading colon as part of the value, not as an empty mode', () => {
            // `lastIndexOf(':') > 0` — at index 0 there is no value to keep.
            expect(parse('filename=:equals').get('filename')).toEqual({type: 'text', value: ':equals', matchMode: 'contains'});
        });
    });

    describe('enum', () => {
        it('splits on commas', () => {
            expect(parse('broker=1,2,3').get('broker')).toEqual({type: 'enum', selected: ['1', '2', '3']});
        });

        it('drops blank entries left by stray commas', () => {
            expect(parse('broker=1,,2').get('broker')).toEqual({type: 'enum', selected: ['1', '2']});
        });

        it('produces no filter when every entry is blank', () => {
            expect(parse('broker=,,').has('broker')).toBe(false);
        });
    });

    describe('size', () => {
        it('reads both bounds', () => {
            expect(parse('size=1000-50000').get('size')).toEqual({type: 'size', minBytes: 1000, maxBytes: 50000});
        });

        it('reads a lower bound alone', () => {
            expect(parse('size=1000-').get('size')).toEqual({type: 'size', minBytes: 1000, maxBytes: undefined});
        });

        it('reads an upper bound alone', () => {
            expect(parse('size=-50000').get('size')).toEqual({type: 'size', minBytes: undefined, maxBytes: 50000});
        });

        it('produces no filter when neither bound is a number', () => {
            expect(parse('size=abc-def').has('size')).toBe(false);
        });

        it('keeps the bound that parses when the other does not', () => {
            expect(parse('size=abc-500').get('size')).toEqual({type: 'size', minBytes: undefined, maxBytes: 500});
        });
    });

    describe('date', () => {
        it('reads both ends', () => {
            expect(parse('uploaded=2024-01-01,2024-12-31').get('uploaded')).toEqual({type: 'date', from: '2024-01-01', to: '2024-12-31'});
        });

        it('reads an open-ended range in either direction', () => {
            expect(parse('uploaded=2024-01-01,').get('uploaded')).toEqual({type: 'date', from: '2024-01-01', to: undefined});
            expect(parse('uploaded=,2024-12-31').get('uploaded')).toEqual({type: 'date', from: undefined, to: '2024-12-31'});
        });

        it('produces no filter when both ends are empty', () => {
            expect(parse('uploaded=,').has('uploaded')).toBe(false);
        });
    });
});

describe('buildUrlFilters', () => {
    it('skips a column the caller did not declare', () => {
        const filters = new Map<string, FilterValue>([['ghost', {type: 'text', value: 'x', matchMode: 'contains'}]]);
        expect(buildUrlFilters(filters, COLUMNS).toString()).toBe('');
    });

    it('tolerates a map entry whose value is missing', () => {
        // The type forbids it; a caller holding a stale map does not. The guard
        // is one line, so proving it holds costs one line too.
        const filters = new Map<string, FilterValue>([
            ['filename', undefined as unknown as FilterValue],
            ['broker', {type: 'enum', selected: ['1']}],
        ]);
        expect(buildUrlFilters(filters, COLUMNS).toString()).toBe('broker=1');
    });

    it('translates a column id into its url key when the two differ', () => {
        const filters = new Map<string, FilterValue>([['name', {type: 'text', value: 'report', matchMode: 'contains'}]]);
        const params = buildUrlFilters(filters, COLUMNS, new Map([['name', 'filename']]));
        expect(params.get('filename')).toBe('report');
    });

    it('omits the mode suffix when it is the default', () => {
        const filters = new Map<string, FilterValue>([['filename', {type: 'text', value: 'r', matchMode: 'contains'}]]);
        expect(buildUrlFilters(filters, COLUMNS).get('filename')).toBe('r');
    });

    it('writes the mode suffix when it is not the default', () => {
        const filters = new Map<string, FilterValue>([['filename', {type: 'text', value: 'r', matchMode: 'equals'}]]);
        expect(buildUrlFilters(filters, COLUMNS).get('filename')).toBe('r:equals');
    });

    it.each([
        ['an empty text value', 'filename', {type: 'text', value: '', matchMode: 'contains'}],
        ['an empty selection', 'broker', {type: 'enum', selected: []}],
        ['a size with neither bound', 'size', {type: 'size'}],
        ['a date with neither end', 'uploaded', {type: 'date'}],
    ] as const)('writes nothing for %s', (_label, key, value) => {
        const filters = new Map<string, FilterValue>([[key, value as FilterValue]]);
        expect(buildUrlFilters(filters, COLUMNS).has(key)).toBe(false);
    });

    it('writes a half-open size range with the missing side blank', () => {
        const lower = new Map<string, FilterValue>([['size', {type: 'size', minBytes: 100}]]);
        const upper = new Map<string, FilterValue>([['size', {type: 'size', maxBytes: 900}]]);
        expect(buildUrlFilters(lower, COLUMNS).get('size')).toBe('100-');
        expect(buildUrlFilters(upper, COLUMNS).get('size')).toBe('-900');
    });

    it('writes a half-open date range with the missing end blank', () => {
        const from = new Map<string, FilterValue>([['uploaded', {type: 'date', from: '2024-01-01'}]]);
        const to = new Map<string, FilterValue>([['uploaded', {type: 'date', to: '2024-12-31'}]]);
        expect(buildUrlFilters(from, COLUMNS).get('uploaded')).toBe('2024-01-01,');
        expect(buildUrlFilters(to, COLUMNS).get('uploaded')).toBe(',2024-12-31');
    });
});

describe('the round trip', () => {
    // Each of these is a URL a user could have shared. Writing back what was read
    // must produce the same link, or the two halves disagree about what a filter is.
    it.each(['filename=report', 'filename=report%3Aequals', 'broker=1%2C2', 'size=1000-50000', 'size=1000-', 'size=-50000', 'uploaded=2024-01-01%2C2024-12-31', 'uploaded=2024-01-01%2C', 'uploaded=%2C2024-12-31', 'filename=report&broker=1%2C2&size=1000-'])('survives %s', (query) => {
        expect(new URLSearchParams(roundTrip(query)).toString()).toBe(new URLSearchParams(query).toString());
    });

    it('is deliberately lossy where the grammar is ambiguous', () => {
        // A literal value ending in a mode name cannot be distinguished from the
        // suffix that means that mode — the separator is the same character. The
        // parse wins, and the rebuilt link says what the parse understood.
        expect(roundTrip('filename=a%3Aequals')).toBe('filename=a%3Aequals');
        expect(parse('filename=a:equals').get('filename')).toEqual({type: 'text', value: 'a', matchMode: 'equals'});
    });
});

describe('hasActiveFilters', () => {
    it('is false for an empty map', () => {
        expect(hasActiveFilters(new Map())).toBe(false);
    });

    it('ignores a map entry whose value is missing', () => {
        const filters = new Map<string, FilterValue>([['k', undefined as unknown as FilterValue]]);
        expect(hasActiveFilters(filters)).toBe(false);
    });

    it.each([
        ['text', {type: 'text', value: 'x', matchMode: 'contains'}],
        ['enum', {type: 'enum', selected: ['1']}],
        ['size (min only)', {type: 'size', minBytes: 1}],
        ['size (max only)', {type: 'size', maxBytes: 1}],
        ['date (from only)', {type: 'date', from: '2024-01-01'}],
        ['date (to only)', {type: 'date', to: '2024-01-01'}],
    ] as const)('is true for an active %s filter', (_label, value) => {
        expect(hasActiveFilters(new Map([['k', value as FilterValue]]))).toBe(true);
    });

    it.each([
        ['text', {type: 'text', value: '', matchMode: 'contains'}],
        ['enum', {type: 'enum', selected: []}],
        ['size', {type: 'size'}],
        ['date', {type: 'date'}],
    ] as const)('is false for an empty %s filter', (_label, value) => {
        expect(hasActiveFilters(new Map([['k', value as FilterValue]]))).toBe(false);
    });

    it('is true when any one entry is active among empty ones', () => {
        const filters = new Map<string, FilterValue>([
            ['a', {type: 'text', value: '', matchMode: 'contains'}],
            ['b', {type: 'enum', selected: ['1']}],
        ]);
        expect(hasActiveFilters(filters)).toBe(true);
    });
});

describe('cleanUrlParams', () => {
    const valid = new Set(['filename', 'broker']);

    it('keeps declared keys that carry a value', () => {
        expect(cleanUrlParams(new URLSearchParams('filename=a&broker=1'), valid).toString()).toBe(new URLSearchParams('filename=a&broker=1').toString());
    });

    it('drops undeclared keys and empty values alike', () => {
        expect(cleanUrlParams(new URLSearchParams('filename=a&ghost=b&broker='), valid).toString()).toBe('filename=a');
    });

    it('leaves the input untouched', () => {
        const original = new URLSearchParams('filename=a&ghost=b');
        cleanUrlParams(original, valid);
        expect(original.toString()).toBe(new URLSearchParams('filename=a&ghost=b').toString());
    });
});

describe('a malformed value does not take the page down', () => {
    it('reports the key it could not read and keeps the others', () => {
        // The `catch` guards one key, not the loop. Forcing it needs a value whose
        // own methods throw — `split` is called on every enum and size value.
        const hostile = new URLSearchParams('broker=1&filename=ok');
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const original = String.prototype.split;
        try {
            // eslint-disable-next-line no-extend-native
            String.prototype.split = function (this: string, ...args: unknown[]) {
                if (this === '1') throw new Error('hostile');
                return original.apply(this, args as never);
            } as typeof String.prototype.split;
            const filters = parseUrlFilters(hostile, COLUMNS);
            expect(filters.has('broker')).toBe(false);
            expect(filters.get('filename')).toEqual({type: 'text', value: 'ok', matchMode: 'contains'});
            expect(warn).toHaveBeenCalled();
        } finally {
            String.prototype.split = original;
            warn.mockRestore();
        }
    });
});
