/**
 * preFloorDate — the warning for a transaction dated before 1 January 1900 (D-P4, W5-10).
 *
 * Pure helpers, no DOM. The backend still refuses such a date at save; the frontend warns and asks for one
 * confirmation. Dates are `YYYY-MM-DD` text compared as text, so the boundary is exact: 1899-12-31 is before the
 * floor, 1900-01-01 is not. A blank or unreadable date is never "before" (the required-field check owns that case).
 *
 * The last block proves the wording of the import review's todo exists in the four languages and carries the date
 * (the key is `importWizard.brimNotice.date_before_1900`, resolved by `resolveBrimTodoMessage` like any BRIM todo).
 * It reads the catalogue sources and checks the date placeholder, never the sentence.
 */
import {describe, expect, it} from 'vitest';
import {isBeforeDateFloor, isPreFloorDateTodo, PRE_FLOOR_DATE_LIMIT, PRE_FLOOR_DATE_REASON, preFloorDates, preFloorEntries, withPreFloorDateTodo} from './preFloorDate';
import {resolveBrimTodoMessage} from './resolveBrimNotice';
import type {ImportTodo} from './txPayloadHelpers';
import enImport from '$lib/i18n/importWizard/en.json';
import itImport from '$lib/i18n/importWizard/it.json';
import frImport from '$lib/i18n/importWizard/fr.json';
import esImport from '$lib/i18n/importWizard/es.json';

describe('constants', () => {
    it('the limit is the first day the backend accepts, and the reason code is the one the catalogue words', () => {
        expect(PRE_FLOOR_DATE_LIMIT).toBe('1900-01-01');
        expect(PRE_FLOOR_DATE_REASON).toBe('date_before_1900');
    });
});

describe('isBeforeDateFloor', () => {
    it.each([
        ['1899-12-31', true],
        ['1850-05-01', true],
        ['1024-03-10', true],
        ['0001-01-01', true],
        ['1900-01-01', false],
        ['1900-01-02', false],
        ['2024-03-10', false],
        ['9999-12-31', false],
        ['1899-12-31T10:00:00', true],
        ['1899-12-31T23:59:59Z', true],
        ['1900-01-01T00:00:00', false],
        ['2024-03-10T08:30:00', false],
    ])('%s -> %s', (date, expected) => {
        expect(isBeforeDateFloor(date)).toBe(expected);
    });

    it.each([
        ['empty', ''],
        ['null', null],
        ['undefined', undefined],
        ['not a date', 'abc'],
        ['a short year', '850-05-01'],
        ['a slash date', '1850/05/01'],
        ['a day-first date', '01-05-1850'],
        ['spaces', '  '],
    ])('a %s is not before the floor (the required-field check owns it)', (_label, date) => {
        expect(isBeforeDateFloor(date as string | null | undefined)).toBe(false);
    });
});

describe('preFloorDates', () => {
    it('keeps only the dates before 1900', () => {
        expect(preFloorDates(['2024-03-10', '1850-05-01', '1900-01-01', '1899-12-31'])).toEqual(['1850-05-01', '1899-12-31']);
    });

    it('is distinct and sorted oldest first, whatever the order and the repeats', () => {
        expect(preFloorDates(['1899-12-31', '1024-03-10', '1899-12-31', '1500-01-01', '1024-03-10'])).toEqual(['1024-03-10', '1500-01-01', '1899-12-31']);
    });

    it('drops the time part, so the same day at two hours is one entry', () => {
        expect(preFloorDates(['1850-05-01T08:00:00', '1850-05-01', '1850-05-01T23:59:59'])).toEqual(['1850-05-01']);
    });

    it('skips blank, null, undefined and unreadable entries', () => {
        expect(preFloorDates(['', null, undefined, 'abc', '1850-05-01'])).toEqual(['1850-05-01']);
    });

    it('is empty for an empty list, and for a list with nothing before 1900', () => {
        expect(preFloorDates([])).toEqual([]);
        expect(preFloorDates(['1900-01-01', '2024-03-10'])).toEqual([]);
    });

    it('does not change the list it is given', () => {
        const list = ['1899-12-31', '1024-03-10'];
        preFloorDates(list);
        expect(list).toEqual(['1899-12-31', '1024-03-10']);
    });
});

describe('isPreFloorDateTodo', () => {
    it('is true for a todo on date with the reason code', () => {
        expect(isPreFloorDateTodo({field: 'date', reasonCode: PRE_FLOOR_DATE_REASON})).toBe(true);
    });

    it.each([
        ['another field with the code', {field: 'quantity', reasonCode: PRE_FLOOR_DATE_REASON}],
        ['the date field with another code', {field: 'date', reasonCode: 'possible_split'}],
        ['the date field with no code', {field: 'date'}],
    ])('is false for %s', (_label, todo) => {
        expect(isPreFloorDateTodo(todo)).toBe(false);
    });
});

describe('withPreFloorDateTodo', () => {
    const plugin: ImportTodo = {field: 'quantity', severity: 'warning', reasonCode: 'corporate_action', message: 'plugin wording', context: {n: 1}};

    it('adds one warning todo on date, with the reason code and the date in its context, for a date before 1900', () => {
        const result = withPreFloorDateTodo([], '1850-05-01');
        expect(result).toHaveLength(1);
        expect(result[0]).toMatchObject({field: 'date', severity: 'warning', reasonCode: PRE_FLOOR_DATE_REASON, context: {date: '1850-05-01'}});
        expect(isPreFloorDateTodo(result[0])).toBe(true);
    });

    it('keeps the todos the plugin gave, in order, and adds the new one after them', () => {
        const result = withPreFloorDateTodo([plugin], '1850-05-01');
        expect(result).toHaveLength(2);
        expect(result[0]).toBe(plugin);
        expect(result[1].reasonCode).toBe(PRE_FLOOR_DATE_REASON);
    });

    it('puts the day alone in the context, without the time part', () => {
        expect(withPreFloorDateTodo([], '1850-05-01T10:00:00')[0].context).toEqual({date: '1850-05-01'});
    });

    it('never adds a second one: a row that already carries it is returned as it is', () => {
        const once = withPreFloorDateTodo([plugin], '1850-05-01');
        const twice = withPreFloorDateTodo(once, '1850-05-01');
        expect(twice).toBe(once);
        expect(twice.filter(isPreFloorDateTodo)).toHaveLength(1);
    });

    it.each([
        ['1900-01-01', '1900-01-01'],
        ['a normal date', '2024-03-10'],
        ['blank', ''],
        ['null', null],
        ['undefined', undefined],
        ['unreadable', 'abc'],
    ])('adds nothing for %s and returns the very same list', (_label, date) => {
        const list = [plugin];
        expect(withPreFloorDateTodo(list, date as string | null | undefined)).toBe(list);
    });

    it('does not change the list it is given', () => {
        const list = [plugin];
        withPreFloorDateTodo(list, '1850-05-01');
        expect(list).toEqual([plugin]);
    });
});

describe('preFloorEntries', () => {
    const op = (tempId: string, date: string, pairedWith?: string) => ({tempId, pairedWith, fields: {date}});
    const label = (tempId: string) => `#${tempId}`;

    it('lists the rows dated before 1900, in the grid order, with their label and date', () => {
        const entries = preFloorEntries([op('a', '2024-03-10'), op('b', '1850-05-01'), op('c', '1900-01-01'), op('d', '1899-12-31')], label);
        expect(entries).toEqual([
            {tempId: 'b', rowId: 'b', rowNumber: '#b', date: '1850-05-01'},
            {tempId: 'd', rowId: 'd', rowNumber: '#d', date: '1899-12-31'},
        ]);
    });

    it('is empty when no row is before 1900, and when there are no rows', () => {
        expect(preFloorEntries([op('a', '2024-03-10'), op('b', '1900-01-01'), op('c', '')], label)).toEqual([]);
        expect(preFloorEntries([], label)).toEqual([]);
    });

    it('lists the two legs of a pair once each by their own date, both leading to the pair (rowId is the partner)', () => {
        const entries = preFloorEntries([op('from', '1850-05-01', 'to'), op('to', '2024-03-11', 'from')], label);
        expect(entries).toEqual([{tempId: 'from', rowId: 'to', rowNumber: '#from', date: '1850-05-01'}]);
        const both = preFloorEntries([op('from', '1850-05-01', 'to'), op('to', '1850-05-02', 'from')], label);
        expect(both.map((entry) => entry.tempId)).toEqual(['from', 'to']);
        expect(both.map((entry) => entry.date)).toEqual(['1850-05-01', '1850-05-02']);
    });

    it('drops the time part of the date it reports', () => {
        expect(preFloorEntries([op('a', '1850-05-01T10:00:00')], label)[0].date).toBe('1850-05-01');
    });

    it('asks the label for every listed row, and only for those', () => {
        const asked: string[] = [];
        preFloorEntries([op('a', '2024-03-10'), op('b', '1850-05-01')], (tempId) => (asked.push(tempId), tempId));
        expect(asked).toEqual(['b']);
    });
});

describe('the wording of the import todo, in the four languages', () => {
    /** A translator over a catalogue source: walks the dotted key, replaces `{name}` from the values, echoes the key on a miss. */
    function translatorOf(catalogue: unknown) {
        return (key: string, options?: {values?: Record<string, unknown>}): string => {
            let node: unknown = catalogue;
            for (const part of key.split('.')) node = (node as Record<string, unknown> | undefined)?.[part];
            if (typeof node !== 'string') return key;
            return node.replace(/\{(\w+)\}/g, (_m, name) => String(options?.values?.[name] ?? `{${name}}`));
        };
    }

    // The todo's own message is English; swapped for a marker so a hit on the catalogue cannot be mistaken for the fallback.
    const todo = {...withPreFloorDateTodo([], '1850-05-01')[0], message: 'PLUGIN-FALLBACK'};

    it.each([
        ['en', enImport],
        ['it', itImport],
        ['fr', frImport],
        ['es', esImport],
    ])('%s has a wording that is not the plugin message and carries the date', (_lang, catalogue) => {
        const message = resolveBrimTodoMessage(todo, translatorOf(catalogue));
        expect(message, 'the key exists: not the fallback to the todo message').not.toBe(todo.message);
        expect(message).not.toContain('importWizard.brimNotice');
        expect(message, 'the date placeholder was filled').toContain('1850-05-01');
        expect(message).not.toMatch(/\{date\}/);
    });

    it('the four languages word it differently (not one language copied four times)', () => {
        const texts = [enImport, itImport, frImport, esImport].map((catalogue) => resolveBrimTodoMessage(todo, translatorOf(catalogue)));
        expect(new Set(texts).size).toBe(4);
    });
});
