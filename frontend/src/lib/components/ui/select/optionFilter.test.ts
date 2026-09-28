import {existsSync, readdirSync, readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {beforeAll, describe, it, expect} from 'vitest';
import {filterOptions, firstSelectable, isSelectable, lastSelectable, stepSelectable} from './optionFilter';
import type {SelectOption} from './types';

const header = (value: string, label: string): SelectOption => ({value, label, header: true});
const opt = (value: string, label: string, searchText?: string): SelectOption => ({value, label, searchText});

/** The shape the import picker builds: two titled sections over one flat list. */
const sectioned: SelectOption[] = [header('__s:import', 'In questo import'), opt('import:-1', 'BTP 17-11-28', 'IT0005425753'), opt('import:-2', 'ETF MSCI World', 'IE00B4L5Y983'), header('__s:db', 'In archivio'), opt('db:41', 'BTP Italia 2030', 'IT0005094088')];

describe('filterOptions', () => {
    it('returns everything, titles included, on an empty query', () => {
        expect(filterOptions(sectioned, '')).toHaveLength(5);
    });

    it('drops the title of a section the query emptied', () => {
        const out = filterOptions(sectioned, 'MSCI');
        expect(out.map((o) => o.value)).toEqual(['__s:import', 'import:-2']);
    });

    it('keeps a title that still leads something', () => {
        const out = filterOptions(sectioned, 'BTP');
        expect(out.filter((o) => o.header).map((o) => o.value)).toEqual(['__s:import', '__s:db']);
    });

    it('leaves nothing at all when no section survives', () => {
        expect(filterOptions(sectioned, 'zzz')).toEqual([]);
    });

    it('drops a trailing title', () => {
        const out = filterOptions([header('__s:a', 'A'), opt('a1', 'Alpha'), header('__s:b', 'B')], '');
        expect(out.map((o) => o.value)).toEqual(['__s:a', 'a1']);
    });

    it('drops the first of two adjacent titles', () => {
        const out = filterOptions([header('__s:a', 'A'), header('__s:b', 'B'), opt('b1', 'Beta')], '');
        expect(out.map((o) => o.value)).toEqual(['__s:b', 'b1']);
    });

    it('matches on searchText, so an ISIN finds a security named otherwise', () => {
        expect(filterOptions(sectioned, 'IT0005425753').map((o) => o.value)).toEqual(['__s:import', 'import:-1']);
    });

    it('ignores case and surrounding spaces', () => {
        expect(filterOptions(sectioned, '  msci  ').map((o) => o.value)).toEqual(['__s:import', 'import:-2']);
    });
});

describe('keyboard traversal', () => {
    it('does not consider a title selectable', () => {
        expect(isSelectable(sectioned[0])).toBe(false);
        expect(isSelectable(sectioned[1])).toBe(true);
    });

    it('does not consider a disabled row selectable', () => {
        expect(isSelectable({value: 'x', label: 'X', disabled: true})).toBe(false);
    });

    it('starts below the first title, not on it', () => {
        expect(firstSelectable(sectioned)).toBe(1);
    });

    it('has no landing place in a list of titles alone', () => {
        expect(firstSelectable([header('__s:a', 'A')])).toBe(-1);
    });

    it('finds the last landing place, stepping back over a trailing title', () => {
        // `sectioned` ends on `db:41` at index 4, so the last selectable is 4, not the empty tail.
        expect(lastSelectable(sectioned)).toBe(4);
    });

    it('has no last landing place in a list of titles alone', () => {
        expect(lastSelectable([header('__s:a', 'A')])).toBe(-1);
    });

    it('steps over the title between two sections', () => {
        expect(stepSelectable(sectioned, 2, 1)).toBe(4);
    });

    it('steps back over it too', () => {
        expect(stepSelectable(sectioned, 4, -1)).toBe(2);
    });

    it('stays put at the end rather than wrapping', () => {
        expect(stepSelectable(sectioned, 4, 1)).toBe(4);
        expect(stepSelectable(sectioned, 1, -1)).toBe(1);
    });
});

describe('icon matching', () => {
    const withIcon = (value: string, label: string, icon: string): SelectOption => ({value, label, icon});

    it('does not let a query match an icon path', () => {
        // Every asset-type icon is `/icons/asset-types/<name>.png`, so a path-matching filter
        // returned the whole list for any query that appears in it — which is most short ones.
        const list = [withIcon('1', 'Alfa', '/icons/asset-types/bond.png'), withIcon('2', 'Beta', '/icons/asset-types/etf.png')];
        expect(filterOptions(list, 's')).toHaveLength(0);
        expect(filterOptions(list, 'icons')).toHaveLength(0);
        expect(filterOptions(list, 'png')).toHaveLength(0);
    });

    it('still matches a flag emoji, which is the symbol itself', () => {
        const list = [withIcon('EUR', 'Euro', '🇪🇺'), withIcon('USD', 'Dollar', '🇺🇸')];
        expect(filterOptions(list, '🇪🇺').map((o) => o.value)).toEqual(['EUR']);
    });

    it('leaves the label the deciding field for a one-letter query', () => {
        const list = [withIcon('1', 'Alfa', '/icons/asset-types/bond.png'), withIcon('2', 'Beta', '/icons/asset-types/etf.png')];
        expect(filterOptions(list, 'a').map((o) => o.value)).toEqual(['1', '2']);
        expect(filterOptions(list, 'al').map((o) => o.value)).toEqual(['1']);
    });
});

const HERE = path.dirname(fileURLToPath(import.meta.url));
/** `select` → `ui` → `components` → `lib` → `src` → `frontend` → the repository root */
const REPO_DIR = path.resolve(HERE, '..', '..', '..', '..', '..', '..');
const BRIM_PROVIDERS_DIR = path.join(REPO_DIR, 'backend', 'app', 'services', 'brim_providers');

/** The escapes a plugin string may plausibly contain; any other one stops the scrape. */
const PYTHON_ESCAPES: Record<string, string> = {'\\': '\\', "'": "'", '"': '"', n: '\n', t: '\t'};

/**
 * What `def <property>(self) -> str:` returns, provided it returns string literals: one, several
 * adjacent ones (Python concatenates them), or a parenthesised run across lines. Anything else —
 * an f-string, a name, a call, a `+` — throws rather than returning part of the string, because a
 * truncated description is a plugin that silently stops matching.
 */
function returnedLiteral(source: string, property: string, file: string): string {
    const where = `${file}, ${property}`;
    const defs = [...source.matchAll(new RegExp(`^[ \\t]*def ${property}\\(self\\)(?:\\s*->\\s*str)?\\s*:`, 'gm'))];
    if (defs.length !== 1) throw new Error(`${where}: expected exactly one definition, found ${defs.length}`);
    const bodyStart = defs[0].index! + defs[0][0].length;
    const returnPattern = /^[ \t]*return\b/gm;
    returnPattern.lastIndex = bodyStart;
    const ret = returnPattern.exec(source);
    if (!ret || /^[ \t]*(?:def |class |@)/m.test(source.slice(bodyStart, ret.index))) throw new Error(`${where}: no return statement in the property body`);

    let i = ret.index + ret[0].length;
    const skipBlanks = (acrossLines: boolean) => {
        while (source[i] === ' ' || source[i] === '\t' || (acrossLines && (source[i] === '\n' || source[i] === '\r'))) i++;
    };
    skipBlanks(false);
    const parenthesised = source[i] === '(';
    if (parenthesised) i++;
    const parts: string[] = [];
    for (;;) {
        skipBlanks(parenthesised);
        const quote = source[i];
        if (quote !== '"' && quote !== "'") break;
        if (source.startsWith(quote.repeat(3), i)) throw new Error(`${where}: a triple-quoted string; extend this scrape before relying on it`);
        let text = '';
        for (i++; source[i] !== quote; i++) {
            if (i >= source.length || source[i] === '\n') throw new Error(`${where}: unterminated string literal`);
            if (source[i] === '\\') {
                i++;
                const escaped = PYTHON_ESCAPES[source[i]];
                if (escaped === undefined) throw new Error(`${where}: unsupported escape \\${source[i]}`);
                text += escaped;
            } else {
                text += source[i];
            }
        }
        i++;
        parts.push(text);
    }
    if (parenthesised) {
        skipBlanks(true);
        if (source[i] !== ')') throw new Error(`${where}: the parenthesised return holds more than string literals`);
        i++;
        skipBlanks(false);
    }
    if (parts.length === 0) throw new Error(`${where}: the return is not a string literal`);
    if (i < source.length && source[i] !== '\n' && source[i] !== '\r' && source[i] !== '#') throw new Error(`${where}: the return goes on past its string literals, so reading the literals alone would truncate it`);
    return parts.join('');
}

/**
 * The import plugins as ImportPluginSelect turns them into options (`value: code`, `label: name`,
 * `searchText: description`), in the backend's discovery order. `icon_url` is left out: every
 * plugin's is a URL, and the icon rule never matches a URL.
 */
function readImportPluginOptions(): SelectOption[] {
    if (!existsSync(BRIM_PROVIDERS_DIR)) throw new Error(`${BRIM_PROVIDERS_DIR} does not exist: this test reads the plugin sources as text, so a move must stop it rather than let it scrape nothing`);
    // provider_registry.py imports `sorted(glob('*.py'))`, and that registration order is the order
    // /brokers/import/plugins serves. On these ASCII names `sort()` agrees with Python's `sorted()`.
    const files = readdirSync(BRIM_PROVIDERS_DIR)
        .filter((name) => /^broker_\w+\.py$/.test(name))
        .sort();
    return files.map((file) => {
        const source = readFileSync(path.join(BRIM_PROVIDERS_DIR, file), 'utf-8');
        return {value: returnedLiteral(source, 'provider_code', file), label: returnedLiteral(source, 'provider_name', file), searchText: returnedLiteral(source, 'description', file)};
    });
}

/**
 * R13 / decision D-K5: a query's survivors are ordered by how they matched, so the row the
 * highlight lands on — the one Enter picks — is the best match, not the first in source order:
 *
 *   0  value or label starts with the query
 *   1  a word inside value or label starts with it (a word starts after any non-alphanumeric)
 *   2  value or label contains it anywhere
 *   3  only searchText, or the icon rule, matched
 *
 * Stable within a rank, applied section by section, titles never moved. The match set and the
 * title rule stay exactly as they were: only the order changes. Wherever it can, a list below is
 * written in the reverse of its expected order, so that source order alone cannot pass.
 */
describe('ranking', () => {
    const values = (list: readonly SelectOption[]) => list.map((o) => o.value);

    it('orders a prefix match, then a word start, then a substring, then a searchText-only match', () => {
        const list = [opt('p3', 'Alpha', 'reads any csv export'), opt('p2', 'Bravocsv'), opt('p1', 'Charlie CSV'), opt('p0', 'CSV Delta')];
        expect(values(filterOptions(list, 'csv'))).toEqual(['p0', 'p1', 'p2', 'p3']);
        // The same trimming and case folding as the match itself.
        expect(values(filterOptions(list, '  CSV  '))).toEqual(['p0', 'p1', 'p2', 'p3']);
    });

    it('ranks on the value exactly as on the label', () => {
        const list = [opt('misc', 'Misc', 'csv'), opt('xcsv', 'Foxtrot'), opt('broker_csv', 'Golf'), opt('csv_raw', 'Hotel')];
        expect(values(filterOptions(list, 'csv'))).toEqual(['csv_raw', 'broker_csv', 'xcsv', 'misc']);
    });

    it('takes the better rank when value and label disagree', () => {
        // `broker_zulu` is a word start by its value but a prefix by its label: the prefix counts.
        const list = [opt('x', 'Big Zulu'), opt('broker_zulu', 'Zulu Exchange')];
        expect(values(filterOptions(list, 'zulu'))).toEqual(['broker_zulu', 'x']);
    });

    it('starts a word after any non-alphanumeric character, and never after a letter or a digit', () => {
        // `_` is here on purpose: a regex `\b` counts it as a word character, and would sink
        // `raw_csv` to a plain substring match.
        const list = [opt('mid', 'Xcsvx'), opt('digit', 'Form2csv'), opt('space', 'Generic CSV'), opt('underscore', 'raw_csv'), opt('dash', 'semi-csv'), opt('slash', 'text/csv'), opt('dot', 'export.csv'), opt('paren', 'Export (CSV)')];
        expect(values(filterOptions(list, 'csv'))).toEqual(['space', 'underscore', 'dash', 'slash', 'dot', 'paren', 'mid', 'digit']);
    });

    it('looks at every word, not only where the query first appears', () => {
        // The first `csv` in 'Xcsv then csv' is mid-word; the second starts a word, which is enough.
        const list = [opt('first', 'Xcsv'), opt('later', 'Xcsv then csv')];
        expect(values(filterOptions(list, 'csv'))).toEqual(['later', 'first']);
    });

    it('ranks an icon-only match with the searchText-only ones, below every label match', () => {
        // A label carrying the flag is synthetic: it gives the icon match something to lose to.
        const list: SelectOption[] = [
            {value: 'EU', label: 'Europe', icon: '🇪🇺'},
            {value: 'EZ', label: 'Eurozone 🇪🇺'},
        ];
        expect(values(filterOptions(list, '🇪🇺'))).toEqual(['EZ', 'EU']);
    });

    it('keeps source order within a rank, and leaves the caller’s array as it was', () => {
        const list = [opt('a', 'Zone', 'euro area'), opt('b', 'Euro Stoxx'), opt('c', 'Mid', 'euro'), opt('d', 'Eurozone'), opt('e', 'Last', 'euro')];
        const before = values(list);
        expect(values(filterOptions(list, 'euro'))).toEqual(['b', 'd', 'a', 'c', 'e']);
        expect(values(list), 'the ranking must sort a copy: `options` is a prop its owner still renders').toEqual(before);
    });

    it('ranks within each section and never moves a title', () => {
        // `2c` is the best match of the whole list, and still may not climb above section one.
        const list = [header('__s:one', 'One'), opt('1a', 'Alpha', 'csv notes'), opt('1b', 'CSV One'), header('__s:two', 'Two'), opt('2a', 'Beta', 'csv'), opt('2b', 'Two CSV'), opt('2c', 'CSV Two')];
        expect(values(filterOptions(list, 'csv'))).toEqual(['__s:one', '1b', '1a', '__s:two', '2c', '2b', '2a']);
    });

    it('treats the rows ahead of the first title as a section of their own', () => {
        const list = [opt('0a', 'Alpha', 'csv'), opt('0b', 'CSV Zero'), header('__s:one', 'One'), opt('1a', 'Beta', 'csv'), opt('1b', 'CSV One')];
        expect(values(filterOptions(list, 'csv'))).toEqual(['0b', '0a', '__s:one', '1b', '1a']);
    });

    it('still drops the titles of the sections a query empties, around one it keeps', () => {
        // A regression guard, green before the ranking too: sections one and three lose every row
        // — two titles in a row, then a title last — while section two keeps two ranked rows.
        const list = [header('__s:one', 'One'), opt('1a', 'Alpha'), header('__s:two', 'Two'), opt('2a', 'CSV Two'), opt('2b', 'Beta', 'csv'), header('__s:three', 'Three'), opt('3a', 'Gamma')];
        expect(values(filterOptions(list, 'csv'))).toEqual(['__s:two', '2a', '2b']);
    });

    it('leaves an empty or blank query in source order', () => {
        const list = [opt('p3', 'Alpha', 'reads any csv export'), header('__s:x', 'X'), opt('p2', 'Bravocsv'), opt('p1', 'Charlie CSV')];
        expect(values(filterOptions(list, ''))).toEqual(values(list));
        expect(values(filterOptions(list, '   '))).toEqual(values(list));
    });

    /**
     * The same rule on the list R13 was reported against, built by *reading* the plugin sources: a
     * hand-copied list would test a snapshot, while the sources are what the API serves. Loaded in
     * `beforeAll`, so a scrape that breaks fails these tests and leaves every other one alone.
     */
    describe('on the real import-plugin list (R13)', () => {
        let plugins: SelectOption[] = [];

        /** The fields the ranking reads: a match here ranks, a match only in the description does not. */
        const inValueOrLabel = (o: SelectOption, q: string) => o.value.toLowerCase().includes(q) || o.label.toLowerCase().includes(q);
        /** The match rule the ranking must leave as it was. */
        const bySubstring = (o: SelectOption, q: string) => inValueOrLabel(o, q) || (o.searchText ?? '').toLowerCase().includes(q);

        /** Every value/label match above every description-only one, and those still in backend order. */
        function expectValueOrLabelMatchesFirst(out: SelectOption[], q: string): void {
            const valueOrLabel = values(out.filter((o) => inValueOrLabel(o, q)));
            expect(values(out.slice(0, valueOrLabel.length)), `"${q}": every value/label match must rank above every description-only one`).toEqual(valueOrLabel);
            const descriptionOnly = values(plugins.filter((o) => bySubstring(o, q) && !inValueOrLabel(o, q)));
            expect(values(out.slice(valueOrLabel.length)), `"${q}": the description-only matches must keep the backend order`).toEqual(descriptionOnly);
        }

        beforeAll(() => {
            plugins = readImportPluginOptions();
            // Every assertion below reads this scrape, so one that read too little would let them
            // all pass while checking nothing. A floor and anchors, not a count: plugins get added.
            expect(plugins.length, 'fewer than 25 plugins scraped from backend/app/services/brim_providers: the file filter or the parser no longer matches the sources').toBeGreaterThanOrEqual(25);
            expect(values(plugins), 'broker_generic_csv, the plugin R13 is about, was not scraped').toContain('broker_generic_csv');
            expect(values(plugins.filter((o) => o.value.trim() === '' || o.label.trim() === '')), 'plugins scraped with an empty code or name').toEqual([]);
            expect(new Set(values(plugins)).size, 'duplicate plugin codes: the scrape read something that is not a plugin').toBe(plugins.length);
        });

        it('puts Generic CSV first for "CSV", and still returns every plugin a substring search finds', () => {
            // The shape of R13 must still be in the data, or this test proves nothing: a plugin that
            // matches "CSV" only through its description comes before Generic CSV in backend order.
            const genericAt = values(plugins).indexOf('broker_generic_csv');
            expect(
                plugins.slice(0, genericAt).some((o) => bySubstring(o, 'csv') && !inValueOrLabel(o, 'csv')),
                'no description-only CSV match precedes Generic CSV any more: source order alone would pass this test',
            ).toBe(true);

            const out = filterOptions(plugins, 'CSV');
            expect(out[0]?.value, 'the row the highlight lands on, and Enter picks').toBe('broker_generic_csv');
            const expected = plugins.filter((o) => bySubstring(o, 'csv'));
            expect(out).toHaveLength(expected.length);
            expect(new Set(values(out))).toEqual(new Set(values(expected)));
            expectValueOrLabelMatchesFirst(out, 'csv');
        });

        it('finds Generic CSV alone for "generic"', () => {
            expect(values(filterOptions(plugins, 'generic'))).toEqual(['broker_generic_csv']);
        });

        it('lists the code and name matches for "crypto" ahead of the description-only ones', () => {
            const out = filterOptions(plugins, 'crypto');
            // Both kinds must be present, or "ahead of" orders nothing.
            expect(values(out.filter((o) => inValueOrLabel(o, 'crypto')))).toContain('broker_cryptocom');
            expect(
                out.some((o) => !inValueOrLabel(o, 'crypto')),
                'no plugin matches "crypto" through its description alone',
            ).toBe(true);
            expect(new Set(values(out))).toEqual(new Set(values(plugins.filter((o) => bySubstring(o, 'crypto')))));
            expectValueOrLabelMatchesFirst(out, 'crypto');
        });
    });
});
