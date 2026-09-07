/**
 * DataTable — pure logic, extracted from `DataTable.svelte`.
 *
 * Half the application is a DataTable, and the decisions that make it behave —
 * which rows a filter keeps, how a typed cell sorts, what min/max a slider spans,
 * which enum options a popover offers — used to live inside `$derived.by` blocks
 * and `{@const}` template expressions. Reached only through a mounted component,
 * their many branches (seven filter modes, eleven cell shapes, the empty-cell
 * ordering rule) were exercised by accident or through pages that are most of the
 * work to set up.
 *
 * Here each is a plain function of its inputs: the row(s), the column def and the
 * filter/sort request. The `.svelte` delegates to them unchanged, so the contract
 * is identical — but every branch is now reachable with a literal, not a fixture.
 *
 * Nothing here reads component state: the caller passes the dataset explicitly
 * (`boundaryData` for the min/max computations, `data` for the option sets), which
 * is exactly what the template did before.
 */
import type {CellContent, ColumnDef, EnumOption, FilterValue} from './types';

/**
 * The value a typed cell sorts and filters *by*, which is not always what it
 * renders. A badge sorts by its text, not its colour; a size cell by its byte
 * count, not "1.2 MB"; a date cell by the instant, not its printed form; an html
 * cell by the text left once the tags are stripped. Plain (non-typed) cells and
 * any shape without a discriminant `type` are returned as-is.
 */
export function extractRawValue(cell: CellContent): unknown {
    if (typeof cell !== 'object' || cell === null) return cell;
    if (!('type' in cell)) return cell;

    switch (cell.type) {
        case 'icon-text':
            return cell.text;
        case 'badge':
            return cell.text;
        case 'date':
            return new Date(cell.value);
        case 'size':
            return cell.bytes;
        case 'link':
            return cell.text;
        case 'editable-number':
            return cell.value;
        case 'editable-text':
            return cell.value;
        case 'editable-select':
            return cell.value;
        case 'editable-checkbox':
            return cell.value;
        case 'html':
            // Strip HTML tags for sorting
            return cell.html.replace(/<[^>]*>/g, '');
        default:
            return String(cell);
    }
}

/**
 * Does `row` pass the active `filterValue` for `column`? One predicate, seven
 * modes. `null` is not a value here: for text/number/size the string/number
 * coercions do the work, and an empty enum/multi-enum/currency selection means
 * "no restriction" (returns true), never "match nothing".
 *
 * The raw value is read through `getValue ?? cell` and, for a typed cell, kept as
 * its `String(...)` form — the per-mode branches then re-extract what they need
 * (bytes for size, the inner date for date). This mirrors the original inline
 * predicate exactly; it deliberately does NOT route through `extractRawValue`,
 * which is the *sort* path.
 */
export function matchesColumnFilter<T>(column: ColumnDef<T>, row: T, filterValue: FilterValue): boolean {
    const getValue = column.getValue ?? column.cell;
    const cellValue = getValue(row);
    const rawValue = typeof cellValue === 'object' && cellValue !== null && 'type' in cellValue ? String(cellValue) : cellValue;

    if (filterValue.type === 'text') {
        const str = String(rawValue).toLowerCase();
        const search = filterValue.value.toLowerCase();
        switch (filterValue.matchMode) {
            case 'contains':
                return str.includes(search);
            case 'startsWith':
                return str.startsWith(search);
            case 'endsWith':
                return str.endsWith(search);
            case 'equals':
                return str === search;
        }
    } else if (filterValue.type === 'number') {
        const num = Number(rawValue);
        if (filterValue.min !== undefined && num < filterValue.min) return false;
        if (filterValue.max !== undefined && num > filterValue.max) return false;
        return true;
    } else if (filterValue.type === 'size') {
        // Size filter - rawValue should be bytes (from SizeCell)
        const bytes = typeof rawValue === 'object' && rawValue !== null && 'type' in rawValue && (rawValue as unknown as {type: string}).type === 'size' ? (rawValue as unknown as {bytes: number}).bytes : Number(rawValue);
        if (filterValue.minBytes !== undefined && bytes < filterValue.minBytes) return false;
        if (filterValue.maxBytes !== undefined && bytes > filterValue.maxBytes) return false;
        return true;
    } else if (filterValue.type === 'date') {
        const dateStr = typeof rawValue === 'object' && rawValue !== null && 'type' in rawValue && (rawValue as unknown as {type: string}).type === 'date' ? String((rawValue as unknown as {value: Date | string}).value) : String(rawValue);
        const date = new Date(dateStr);
        if (filterValue.from && date < new Date(filterValue.from)) return false;
        if (filterValue.to && date > new Date(filterValue.to)) return false;
        return true;
    } else if (filterValue.type === 'enum') {
        return filterValue.selected.includes(String(rawValue));
    } else if (filterValue.type === 'multi-enum') {
        if (filterValue.selected.length === 0) return true;
        const rowVals = column.getMultiValue ? column.getMultiValue(row) : Array.isArray(rawValue) ? (rawValue as unknown[]).map((v) => String(v)) : String(rawValue ?? '').split(',');
        return filterValue.selected.some((sel) => rowVals.includes(sel));
    } else if (filterValue.type === 'currency-stack') {
        if (filterValue.items.length === 0) return true;
        const cv = column.getCurrencyValue ? column.getCurrencyValue(row) : null;
        if (!cv) return false;
        return filterValue.items.some((it) => it.code === cv.code && (it.min === undefined || cv.amount >= it.min) && (it.max === undefined || cv.amount <= it.max));
    }
    return true;
}

/**
 * Comparator for two rows on `column`, honouring `direction`. Typed cells are
 * reduced through `extractRawValue` first; then:
 *   - a missing value (null / undefined / '') always sorts *last*, in both
 *     directions, and is returned before the direction flip so it cannot be
 *     dragged to the top by a descending sort;
 *   - two numbers compare by magnitude, two Dates by instant, everything else
 *     by `localeCompare` on its string form.
 */
export function compareRowsByColumn<T>(column: ColumnDef<T>, a: T, b: T, direction: 'asc' | 'desc'): number {
    // A column may define its own ordering, and when it does that ordering *is*
    // the answer: `sortFn` receives the rows themselves, so it can rank by
    // something the rendered cell does not show. The import wizard's Status
    // column uses it to sort by triage priority — "before opening" first, then
    // unresolved, then the duplicate grades — and until this line existed the
    // option was declared in `ColumnDef`, set by that caller, and read by
    // nobody: clicking the header sorted the statuses *alphabetically*, which
    // buries the rows that need attention in the middle of the list.
    if (column.sortFn) {
        const custom = column.sortFn(a, b);
        return direction === 'asc' ? custom : -custom;
    }

    const getValue = column.getValue ?? column.cell;
    const aVal = getValue(a);
    const bVal = getValue(b);

    // Extract raw value if it's a CellContent object
    const aRaw = typeof aVal === 'object' && aVal !== null && 'type' in aVal ? extractRawValue(aVal as CellContent) : aVal;
    const bRaw = typeof bVal === 'object' && bVal !== null && 'type' in bVal ? extractRawValue(bVal as CellContent) : bVal;

    let comparison = 0;
    // A missing value is not a value: it sorts last whichever way the column
    // points. Falling through to the string branch turned `null` into the
    // literal "null" and handed it to localeCompare, so in descending order
    // empty cells outranked the largest number — and *where* they landed
    // depended on the spelling of the placeholder, since 'null' and
    // 'undefined' sort after digits while '' sorts before everything.
    // Returned directly, because the direction flip below must not move them.
    const aEmpty = aRaw === null || aRaw === undefined || aRaw === '';
    const bEmpty = bRaw === null || bRaw === undefined || bRaw === '';
    if (aEmpty || bEmpty) {
        if (aEmpty && bEmpty) return 0;
        return aEmpty ? 1 : -1;
    }

    if (typeof aRaw === 'number' && typeof bRaw === 'number') {
        comparison = aRaw - bRaw;
    } else if (aRaw instanceof Date && bRaw instanceof Date) {
        comparison = aRaw.getTime() - bRaw.getTime();
    } else {
        comparison = String(aRaw).localeCompare(String(bRaw));
    }

    return direction === 'asc' ? comparison : -comparison;
}

/**
 * Min/max across `rows` for a number or size column, used to seed a range
 * slider. Size cells contribute their `bytes`; everything else is coerced with
 * `Number` (via `extractRawValue` for typed cells). Non-numeric and infinite
 * values are skipped. The result is always a usable interval: empty columns
 * collapse to `{0, 1}`, and a single distinct value is widened by one so the
 * slider never has zero span.
 */
export function getColumnMinMax<T>(column: ColumnDef<T>, rows: T[]): {min: number; max: number} {
    let min = Infinity;
    let max = -Infinity;

    for (const row of rows) {
        const getValue = column.getValue ?? column.cell;
        const cellValue = getValue(row);
        let numValue: number;

        if (typeof cellValue === 'object' && cellValue !== null && 'type' in cellValue) {
            const typed = cellValue as unknown as {type: string; bytes?: number};
            if (typed.type === 'size' && typeof typed.bytes === 'number') {
                numValue = typed.bytes;
            } else {
                numValue = Number(extractRawValue(cellValue as CellContent));
            }
        } else {
            numValue = Number(cellValue);
        }

        if (!isNaN(numValue) && isFinite(numValue)) {
            min = Math.min(min, numValue);
            max = Math.max(max, numValue);
        }
    }

    // If no valid values, use sensible defaults
    if (min === Infinity) min = 0;
    if (max === -Infinity) max = min + 1;

    // Ensure min < max
    if (min >= max) max = min + 1;

    return {min, max};
}

/**
 * Option set for a `multi-enum` column derived from `rows` (used when the column
 * declares no static `enumOptions` — tags and other open sets). Alphabetically
 * sorted; blank and nullish values are dropped.
 */
export function getMultiEnumOptions<T>(column: ColumnDef<T>, rows: T[]): EnumOption[] {
    const all = new Set<string>();
    for (const row of rows) {
        const vals = column.getMultiValue ? column.getMultiValue(row) : [];
        for (const v of vals) if (v != null && v !== '') all.add(String(v));
    }
    return [...all].sort((a, b) => a.localeCompare(b)).map((v) => ({value: v, label: v}));
}

/**
 * Enrich a column's declared `enumOptions` for a multi-enum column with per-value
 * counts from `rows`. An empty option list is returned untouched (no counting).
 */
export function getMultiEnumOptionsWithCounts<T>(column: ColumnDef<T>, rows: T[]): EnumOption[] {
    const opts = column.enumOptions ?? [];
    if (opts.length === 0) return opts;
    const counts = new Map<string, number>();
    for (const row of rows) {
        const vals = column.getMultiValue ? column.getMultiValue(row) : [];
        for (const v of vals) counts.set(v, (counts.get(v) ?? 0) + 1);
    }
    return opts.map((o) => ({...o, count: counts.get(o.value) ?? 0}));
}

/**
 * Enrich a column's declared `enumOptions` (single-select enum) with the count of
 * rows carrying each value. An empty option list is returned untouched.
 */
export function getEnumOptionsWithCounts<T>(column: ColumnDef<T>, rows: T[]): EnumOption[] {
    const opts = column.enumOptions ?? [];
    if (opts.length === 0) return opts;
    const counts = new Map<string, number>();
    for (const row of rows) {
        const v = column.getValue ? String(column.getValue(row) ?? '') : '';
        counts.set(v, (counts.get(v) ?? 0) + 1);
    }
    return opts.map((o) => ({...o, count: counts.get(o.value) ?? 0}));
}

/**
 * Distinct currency codes present in `rows` for a `currency-stack` column, sorted.
 * A column with no `getCurrencyValue` accessor yields nothing.
 */
export function getCurrencyOptions<T>(column: ColumnDef<T>, rows: T[]): string[] {
    if (!column.getCurrencyValue) return [];
    const all = new Set<string>();
    for (const row of rows) {
        const cv = column.getCurrencyValue(row);
        if (cv?.code) all.add(cv.code);
    }
    return [...all].sort();
}

/**
 * Per-currency min/max amount across `rows` for a `currency-stack` column, so the
 * popover can offer a relevant range editor per currency instead of one global
 * range spanning mixed currencies. Rows without a code or a finite amount are
 * skipped; each single-row currency is widened by one so its slider stays usable.
 */
export function getCurrencyMinMaxByCode<T>(column: ColumnDef<T>, rows: T[]): Map<string, {min: number; max: number}> {
    const out = new Map<string, {min: number; max: number}>();
    if (!column.getCurrencyValue) return out;
    for (const row of rows) {
        const cv = column.getCurrencyValue(row);
        if (!cv || !cv.code || !Number.isFinite(cv.amount)) continue;
        const cur = out.get(cv.code);
        if (!cur) {
            out.set(cv.code, {min: cv.amount, max: cv.amount});
        } else {
            if (cv.amount < cur.min) cur.min = cv.amount;
            if (cv.amount > cur.max) cur.max = cv.amount;
        }
    }
    // Defensive: ensure min < max so the slider remains usable on single-row currencies.
    for (const v of out.values()) {
        if (v.min >= v.max) v.max = v.min + 1;
    }
    return out;
}

/** Labels the `relative` date format needs, injected so this stays free of the i18n store. */
export interface RelativeDateLabels {
    today: string;
    yesterday: string;
}

const DEFAULT_RELATIVE_LABELS: RelativeDateLabels = {today: 'Today', yesterday: 'Yesterday'};

/**
 * Render a date cell's value for display. `time`, `datetime` and the default
 * fall through to the platform locale formatters; `relative` is the only branch
 * with real logic — today, yesterday, "Nd ago" under a week, then the full date.
 * The two relative words are passed in (the component supplies the translated
 * ones) so this function needs no i18n store.
 */
export function formatCellDate(value: Date | string, format?: string, labels: RelativeDateLabels = DEFAULT_RELATIVE_LABELS): string {
    const date = value instanceof Date ? value : new Date(value);
    if (format === 'time') {
        return date.toLocaleTimeString();
    } else if (format === 'datetime') {
        return date.toLocaleString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    } else if (format === 'relative') {
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        if (days === 0) return labels.today;
        if (days === 1) return labels.yesterday;
        if (days < 7) return `${days}d ago`;
        return date.toLocaleDateString();
    }
    return date.toLocaleDateString(undefined, {year: 'numeric', month: 'short', day: 'numeric'});
}
