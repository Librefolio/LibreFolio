import {describe, it, expect} from 'vitest';
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
