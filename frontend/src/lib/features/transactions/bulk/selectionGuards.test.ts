/**
 * selectionGuards — which rows of a selection the user may edit (FB-17).
 *
 * The Transactions page and the broker page's Transactions tab open the bulk workspace from a selection; both ask
 * `guardEditableRows` first, so a row on a broker the user can only read is left out with a word, and a selection
 * with nothing left to edit opens nothing. The contract, in four lines:
 *
 *   - `splitEditableRows` splits a selection in `editable` and `skipped`, each in the order the rows came in;
 *   - some rows left out and some kept → one `warning` carrying how many were left out (`{n}`);
 *   - nothing kept (all rows read-only, or an empty selection) → one `error`, and `null` instead of a list;
 *   - everything kept → no message at all.
 *
 * Nothing here reads translated text: the translator is a stub that returns the key, so the assertions name the
 * catalogue key and the `{n}` the message is asked for, which is what a real catalogue gets.
 */
import {describe, expect, it, vi} from 'vitest';
import {guardEditableRows, splitEditableRows, type SelectionNotify, type SelectionTranslate} from './selectionGuards';

type Row = {id: number; label: string};

const row = (id: number): Row => ({id, label: `row-${id}`});

/** The translator as a stub: the key, and the values it was asked with, are the whole message. */
function stubTranslate(): {t: SelectionTranslate; calls: Array<{key: string; values?: Record<string, unknown>}>} {
    const calls: Array<{key: string; values?: Record<string, unknown>}> = [];
    const t: SelectionTranslate = (key, options) => {
        calls.push({key, values: options?.values});
        return `<${key}>`;
    };
    return {t, calls};
}

function stubNotify(): {notify: SelectionNotify; warning: ReturnType<typeof vi.fn>; error: ReturnType<typeof vi.fn>} {
    const warning = vi.fn();
    const error = vi.fn();
    return {notify: {warning, error}, warning, error};
}

/** Rows 1, 3 and 5 are editable; any other id is on a broker the user only reads. */
const editableIds = new Set([1, 3, 5]);
const canEdit = (id: number) => editableIds.has(id);

describe('splitEditableRows', () => {
    it('splits the selection into editable and skipped, each in the order the rows came in', () => {
        const rows = [row(6), row(5), row(2), row(1), row(4), row(3)];

        const {editable, skipped} = splitEditableRows(rows, canEdit);

        expect(editable.map((r) => r.id)).toEqual([5, 1, 3]);
        expect(skipped.map((r) => r.id)).toEqual([6, 2, 4]);
    });

    it('hands back the very rows it was given, not copies', () => {
        const rows = [row(1), row(2)];

        const {editable, skipped} = splitEditableRows(rows, canEdit);

        expect(editable[0]).toBe(rows[0]);
        expect(skipped[0]).toBe(rows[1]);
    });

    it('asks the predicate with the row id, once per row', () => {
        const predicate = vi.fn((id: number) => id === 1);

        splitEditableRows([row(1), row(2), row(3)], predicate);

        expect(predicate.mock.calls.map(([id]) => id)).toEqual([1, 2, 3]);
    });

    it('leaves both lists empty for an empty selection', () => {
        expect(splitEditableRows([], canEdit)).toEqual({editable: [], skipped: []});
    });

    it('does not touch the selection it was given', () => {
        const rows = [row(2), row(1)];

        splitEditableRows(rows, canEdit);

        expect(rows.map((r) => r.id)).toEqual([2, 1]);
    });
});

describe('guardEditableRows', () => {
    it('some rows editable, some not: returns the editable ones in order and raises one warning counting the rows left out', () => {
        const {notify, warning, error} = stubNotify();
        const {t, calls} = stubTranslate();

        const result = guardEditableRows([row(1), row(2), row(3), row(4)], canEdit, notify, t);

        expect(result?.map((r) => r.id)).toEqual([1, 3]);
        expect(warning).toHaveBeenCalledTimes(1);
        expect(warning).toHaveBeenCalledWith('<transactions.bulk.skippedViewerOnly>');
        expect(calls).toEqual([{key: 'transactions.bulk.skippedViewerOnly', values: {n: 2}}]);
        expect(error).not.toHaveBeenCalled();
    });

    it('counts every row left out in the warning, not only the first', () => {
        const {notify} = stubNotify();
        const {t, calls} = stubTranslate();

        guardEditableRows([row(1), row(2), row(4), row(6), row(8)], canEdit, notify, t);

        expect(calls.find((c) => c.key === 'transactions.bulk.skippedViewerOnly')?.values).toEqual({n: 4});
    });

    it('a single editable row among read-only ones is enough: it is returned, with the warning', () => {
        const {notify, warning, error} = stubNotify();
        const {t, calls} = stubTranslate();

        const result = guardEditableRows([row(2), row(1), row(4)], canEdit, notify, t);

        expect(result?.map((r) => r.id)).toEqual([1]);
        expect(calls).toEqual([{key: 'transactions.bulk.skippedViewerOnly', values: {n: 2}}]);
        expect(warning).toHaveBeenCalledTimes(1);
        expect(error).not.toHaveBeenCalled();
    });

    it('a single editable row on its own is returned and says nothing', () => {
        const {notify, warning, error} = stubNotify();
        const {t} = stubTranslate();

        const result = guardEditableRows([row(3)], canEdit, notify, t);

        expect(result?.map((r) => r.id)).toEqual([3]);
        expect(warning).not.toHaveBeenCalled();
        expect(error).not.toHaveBeenCalled();
    });

    it('every row editable: returns them all and says nothing', () => {
        const {notify, warning, error} = stubNotify();
        const {t, calls} = stubTranslate();

        const result = guardEditableRows([row(5), row(1), row(3)], canEdit, notify, t);

        expect(result?.map((r) => r.id)).toEqual([5, 1, 3]);
        expect(warning).not.toHaveBeenCalled();
        expect(error).not.toHaveBeenCalled();
        expect(calls).toEqual([]);
    });

    it('no row editable: returns null and raises one error, with no warning', () => {
        const {notify, warning, error} = stubNotify();
        const {t, calls} = stubTranslate();

        const result = guardEditableRows([row(2), row(4)], canEdit, notify, t);

        expect(result).toBeNull();
        expect(error).toHaveBeenCalledTimes(1);
        expect(error).toHaveBeenCalledWith('<transactions.bulk.allViewerOnly>');
        expect(calls.map((c) => c.key)).toEqual(['transactions.bulk.allViewerOnly']);
        expect(warning).not.toHaveBeenCalled();
    });

    it('empty selection: returns null and raises the error, never a warning', () => {
        const {notify, warning, error} = stubNotify();
        const {t} = stubTranslate();

        const result = guardEditableRows([], canEdit, notify, t);

        expect(result).toBeNull();
        expect(error).toHaveBeenCalledTimes(1);
        expect(warning).not.toHaveBeenCalled();
    });

    it('a single read-only row is the all-read-only case, not the some-left-out case', () => {
        const {notify, warning, error} = stubNotify();
        const {t} = stubTranslate();

        expect(guardEditableRows([row(2)], canEdit, notify, t)).toBeNull();
        expect(error).toHaveBeenCalledTimes(1);
        expect(warning).not.toHaveBeenCalled();
    });

    it('is a pure filter: the selection it was given keeps its rows and order', () => {
        const rows = [row(2), row(1), row(3)];
        const {notify} = stubNotify();
        const {t} = stubTranslate();

        guardEditableRows(rows, canEdit, notify, t);

        expect(rows.map((r) => r.id)).toEqual([2, 1, 3]);
    });
});
