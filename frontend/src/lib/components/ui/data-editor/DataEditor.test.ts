// @vitest-environment jsdom
/**
 * DataEditor — component test (Vitest + jsdom).
 *
 * DataEditor is the status-tracking layer over a DataTable: every row carries a
 * status (original / edited / deleted / appended), and the ONE thing the editor
 * promises its parent is `onchange(dirtyRows)` — the rows whose status is no
 * longer 'original'. So these tests never read a colour or a counter label; they
 * drive a toolbar button, a cell, or a row-action menu item, and assert the
 * *payload the parent receives*. That payload is the contract.
 *
 * The date cell's embedded SingleDatePicker is opened here only to read which days
 * a new row may take and to pick one (I-11d); the picker's own behaviour belongs to
 * SingleDatePicker.test.ts. CSV import is exercised here through a
 * tiny caller-supplied snippet because the dated-vs-identified dispatch is pure
 * component state and needs no browser or backend.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {get} from 'svelte/store';
import {addMessages, waitLocale} from 'svelte-i18n';
import {render, screen, fireEvent, setupI18n, waitFor, within} from '$test/component';
import {_ as translate} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import DataEditor from './DataEditor.svelte';
import type {ColumnDef, DataRow} from './DataEditorTypes';
import CsvEditor from './CsvEditor.svelte';
import type {CsvColumnDef, CsvIdentityDef, ParsedRow} from './CsvEditor.svelte';
import DataImportModal from './DataImportModal.svelte';
import DistributionDataImportModal from '$lib/components/assets/DistributionDataImportModal.svelte';
import DistributionEditor from '$lib/components/ui/input/DistributionEditor.svelte';
import EventDataImportModal, {unescapeFormulaText} from '$lib/components/assets/EventDataImportModal.svelte';
import PriceDataImportModal from '$lib/components/assets/PriceDataImportModal.svelte';
import DataEditorImportHarness from '$test/harness/DataEditorImportHarness.svelte';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

const referenceData = vi.hoisted(() => ({
    countries: [{iso2: 'IT', iso3: 'ITA', name: 'Italia', flag_emoji: '🇮🇹'}],
    // 'SyntheticUntranslatedSector' has no `sectors.SyntheticUntranslatedSector`
    // entry in en.json (nor any other locale) and never will: it exists only to
    // exercise the missing-translation fallback deterministically, decoupled from
    // whatever real sector keys do or don't have a translation on a given day.
    sectorKeys: ['Technology', 'Financials', 'Corporate Bonds', 'Government Bonds', 'SyntheticUntranslatedSector'],
}));

vi.mock('$lib/stores/reference/countryStore', () => ({
    ensureCountriesLoaded: vi.fn(async () => {}),
    getAllCountries: vi.fn(() => referenceData.countries),
}));

vi.mock('$lib/stores/reference/sectorStore', () => ({
    ensureSectorsLoaded: vi.fn(async () => {}),
    getSectorKeys: vi.fn(() => referenceData.sectorKeys),
    getSectorEmoji: vi.fn(() => '🏷️'),
}));

const COLS: ColumnDef[] = [{key: 'rate', label: 'Rate', type: 'number', editable: true, required: false, step: 0.5}];

/** A row in its loaded 'original' state unless overridden. rowId = date, as price rows use. */
function row(date: string, rate: number | null = 1, extra: Partial<DataRow> = {}): DataRow {
    return {rowId: date, date, status: 'original', originalStatus: 'original', values: {rate}, selected: false, ...extra};
}

function mount(rows: DataRow[] = []) {
    const onchange = vi.fn();
    const {container} = render(DataEditor, {props: {columns: COLS, rows, onchange}});
    return {onchange, container};
}

/** The last dirty-row set the editor pushed to its parent. */
function lastDirty(onchange: ReturnType<typeof vi.fn>): DataRow[] {
    return onchange.mock.calls.at(-1)?.[0] as DataRow[];
}

/** The editable number <input> of one specific row, scoped by the row's data-row-id. */
function rateInput(container: HTMLElement, rowId: string): HTMLInputElement {
    const el = container.querySelector<HTMLInputElement>(`tr[data-row-id="${rowId}"] input.cell-editable-number`);
    if (!el) throw new Error(`no editable rate input for row ${rowId}`);
    return el;
}

/** Open a row's action menu and click one action by its stable id (delete / revert).
 *  The menu is opened via the row's right-click affordance rather than the ⋮ button:
 *  both open the identical ContextMenu, but the ⋮ path positions against an anchor via
 *  requestAnimationFrame, which jsdom does not drive — the right-click path is anchorless
 *  and renders immediately. The action handler under test is the same either way. */
async function runRowAction(rowId: string, actionId: 'delete' | 'revert') {
    const tr = screen.getByTestId('data-editor-root').querySelector<HTMLElement>(`tr[data-row-id="${rowId}"]`);
    if (!tr) throw new Error(`no row ${rowId}`);
    await fireEvent.contextMenu(tr, {clientX: 10, clientY: 10});
    await fireEvent.click(await screen.findByTestId(`context-menu-action-${actionId}`));
}

beforeAll(async () => {
    await setupI18n();
});

describe('DataEditor — adding a row publishes it as an appended dirty row', () => {
    it('on an empty editor, the new row carries today and status appended', async () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-06-14T12:00:00Z'));
        try {
            const {onchange} = mount([]);
            await fireEvent.click(screen.getByTestId('fx-data-add-row-btn'));
            const dirty = lastDirty(onchange);
            expect(dirty).toHaveLength(1);
            expect(dirty[0].status).toBe('appended');
            expect(dirty[0].date).toBe('2024-06-14');
        } finally {
            vi.useRealTimers();
        }
    });

    it('with existing rows, the new date is the day after the latest', async () => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-06-14T12:00:00Z'));
        try {
            const {onchange} = mount([row('2024-06-10'), row('2024-06-11')]);
            await fireEvent.click(screen.getByTestId('fx-data-add-row-btn'));
            const appended = lastDirty(onchange).find((r) => r.status === 'appended');
            expect(appended?.date).toBe('2024-06-12');
        } finally {
            vi.useRealTimers();
        }
    });

    it('never proposes a future date: it caps at today and steps back to a free day', async () => {
        // The latest row IS today, so "the day after" would be tomorrow — forbidden. The editor
        // caps at today, finds it taken, and walks back to the first free day (yesterday).
        vi.useFakeTimers();
        vi.setSystemTime(new Date('2024-06-14T12:00:00Z'));
        try {
            const {onchange} = mount([row('2024-06-14')]);
            await fireEvent.click(screen.getByTestId('fx-data-add-row-btn'));
            const appended = lastDirty(onchange).find((r) => r.status === 'appended');
            expect(appended?.date).toBe('2024-06-13');
        } finally {
            vi.useRealTimers();
        }
    });
});

describe('DataEditor — editing a cell flips the row to edited, and back', () => {
    it('a changed value publishes the row as edited with the new number', async () => {
        const {onchange, container} = mount([row('2024-06-10', 1.1)]);
        await fireEvent.input(rateInput(container, '2024-06-10'), {target: {value: '2.5'}});
        await waitFor(() => expect(onchange).toHaveBeenCalled());
        const dirty = lastDirty(onchange);
        expect(dirty).toHaveLength(1);
        expect(dirty[0].status).toBe('edited');
        expect(dirty[0].values.rate).toBe(2.5);
    });

    it('editing a value back to its original clears the dirty flag', async () => {
        const {onchange, container} = mount([row('2024-06-10', 1.1)]);
        const input = rateInput(container, '2024-06-10');
        await fireEvent.input(input, {target: {value: '2.5'}});
        await waitFor(() => expect(lastDirty(onchange)).toHaveLength(1));
        await fireEvent.input(input, {target: {value: '1.1'}});
        // Restoring the original value returns the row to 'original', so nothing is dirty.
        await waitFor(() => expect(lastDirty(onchange)).toHaveLength(0));
    });
});

describe('DataEditor — the delete / revert lifecycle through the row menu', () => {
    it('deleting an original row publishes it as deleted', async () => {
        const {onchange} = mount([row('2024-06-10')]);
        await runRowAction('2024-06-10', 'delete');
        const dirty = lastDirty(onchange);
        expect(dirty).toHaveLength(1);
        expect(dirty[0].status).toBe('deleted');
    });

    it('reverting a deleted original row restores it and clears the dirty set', async () => {
        const {onchange} = mount([row('2024-06-10')]);
        await runRowAction('2024-06-10', 'delete');
        await waitFor(() => expect(lastDirty(onchange)).toHaveLength(1));
        await runRowAction('2024-06-10', 'revert');
        await waitFor(() => expect(lastDirty(onchange)).toHaveLength(0));
    });

    it('reverting an appended row removes it entirely', async () => {
        const appended = row('2024-06-20', 1, {status: 'appended', originalStatus: 'appended'});
        const {onchange} = mount([row('2024-06-10'), appended]);
        await runRowAction('2024-06-20', 'revert');
        // The appended row is dropped, not merely reset — so it is gone from the table…
        await waitFor(() => expect(screen.queryByTestId('row-actions-2024-06-20')).toBeNull());
        // …and the last emission contains no appended row.
        expect(lastDirty(onchange).some((r) => r.date === '2024-06-20')).toBe(false);
    });
});

describe('DataEditor — bulk-selecting rows and deleting them in one action', () => {
    it('checking two rows then hitting bulk-delete publishes both as deleted', async () => {
        const {onchange, container} = mount([row('2024-06-10'), row('2024-06-11'), row('2024-06-12')]);
        // Selecting rows is a DataTable concern surfaced back through onSelectionChange; the
        // bulk-delete affordance only appears once something is selected.
        await fireEvent.click(container.querySelector<HTMLElement>('[data-testid="dt-row-checkbox-2024-06-10"]')!);
        await fireEvent.click(container.querySelector<HTMLElement>('[data-testid="dt-row-checkbox-2024-06-11"]')!);
        const bulkDelete = await screen.findByTestId('data-editor-bulk-delete');
        await fireEvent.click(bulkDelete);
        await waitFor(() => expect(onchange).toHaveBeenCalled());
        const dirty = lastDirty(onchange);
        expect(dirty.map((r) => r.date).sort()).toEqual(['2024-06-10', '2024-06-11']);
        expect(dirty.every((r) => r.status === 'deleted')).toBe(true);
    });
});

describe('DataEditor — the stale toggle hides backfilled rows without emitting', () => {
    it('flipping the toggle drops stale rows from the table but publishes nothing', async () => {
        const {onchange, container} = mount([row('2024-06-10'), row('2024-06-01', 1, {staleDays: 5})]);
        // The stale row is present, and the toggle only appears because a stale row exists.
        expect(container.querySelector('tr[data-row-id="2024-06-01"]')).not.toBeNull();
        const toggle = within(screen.getByTestId('data-editor-stale-toggle')).getByRole('switch');
        await fireEvent.click(toggle);
        await waitFor(() => expect(container.querySelector('tr[data-row-id="2024-06-01"]')).toBeNull());
        expect(container.querySelector('tr[data-row-id="2024-06-10"]')).not.toBeNull(); // fresh row stays
        expect(onchange).not.toHaveBeenCalled(); // a view filter is not an edit
    });
});

const CSV_COLUMNS: CsvColumnDef[] = [
    {key: 'note', label: 'note', type: 'string', required: true},
    {key: 'amount', label: 'amount', type: 'number', required: true},
];

async function parsedCsv(value: string, columns: CsvColumnDef[] = CSV_COLUMNS, identity?: CsvIdentityDef) {
    const onvalidchange = vi.fn();
    render(CsvEditor, {columns, identity, value, onvalidchange});
    await waitFor(() => expect(onvalidchange).toHaveBeenCalled());
    return onvalidchange.mock.calls.at(-1) as [ParsedRow[], number, boolean];
}

describe('CsvEditor — resilient CSV and complete finite numbers', () => {
    it('accepts a BOM and RFC-style quoted delimiters and escaped quotes', async () => {
        const [rows, errors, duplicates] = await parsedCsv('\uFEFFdate;note;amount\n2024-01-02;"ACME; ""Class A""";"1,25"');

        expect(errors).toBe(0);
        expect(duplicates).toBe(false);
        expect(rows).toEqual([
            {
                kind: 'dated',
                date: '2024-01-02',
                values: {note: 'ACME; "Class A"', amount: 1.25},
                lineNumber: 2,
            },
        ]);
    });

    it('accepts a literal quote embedded in an unquoted legacy field, while still parsing a properly quoted field', async () => {
        // B3-adjacent CsvEditor gap: a bare `"` that is not opening a quoted field
        // (e.g. a size marker like 3") must be kept as literal text in the legacy,
        // unquoted style this column already supported — the new RFC4180 handling
        // must not regress it. The second row proves proper quoting still works
        // side by side with the legacy row in the same paste.
        const [rows, errors] = await parsedCsv('date;note;amount\n2024-03-01;3" pipe;12\n2024-03-02;"quoted; note";7');

        expect(errors).toBe(0);
        expect(rows).toEqual([
            {kind: 'dated', date: '2024-03-01', values: {note: '3" pipe', amount: 12}, lineNumber: 2},
            {kind: 'dated', date: '2024-03-02', values: {note: 'quoted; note', amount: 7}, lineNumber: 3},
        ]);
    });

    it.each(['12tail', 'Infinity', 'NaN', '1e309'])('rejects a non-finite or partially parsed number: %s', async (raw) => {
        const [rows, errors] = await parsedCsv(`date;note;amount\n2024-01-02;ok;${raw}`);

        expect(rows).toEqual([]);
        expect(errors).toBe(1);
    });

    it('keeps the legacy dated identity when no explicit identity is supplied', async () => {
        const [rows, errors] = await parsedCsv('date;note;amount\n2024-02-29;legacy;2');

        expect(errors).toBe(0);
        expect(rows).toEqual([
            {
                kind: 'dated',
                date: '2024-02-29',
                values: {note: 'legacy', amount: 2},
                lineNumber: 2,
            },
        ]);
    });

    it('emits a canonical non-date identity when one is supplied', async () => {
        const onvalidchange = vi.fn();
        render(CsvEditor, {
            columns: [{key: 'amount', label: 'amount', type: 'number', required: true}],
            identity: {
                key: 'name',
                label: 'name',
                parse: (raw: string) => (raw.trim().toLowerCase() === 'alpha' ? 'ALPHA' : null),
            },
            value: 'name;amount\n Alpha ;10',
            onvalidchange,
        });
        await waitFor(() => expect(onvalidchange).toHaveBeenCalled());

        expect(onvalidchange.mock.calls.at(-1)?.[0]).toEqual([{kind: 'identified', identity: 'ALPHA', values: {amount: 10}, lineNumber: 2}]);
    });
});

function distributionModal(
    resolveName: (raw: string) => string | null = (raw) =>
        new Map([
            ['A', 'A'],
            ['B', 'B'],
            ['C', 'C'],
        ]).get(raw.trim().toUpperCase()) ?? null,
) {
    const onimport = vi.fn();
    render(DistributionDataImportModal, {open: true, title: 'fixture title', resolveName, onimport});
    return {onimport};
}

async function enterDistributionCsv(csv: string) {
    const input = await screen.findByTestId('csv-editor-input');
    await fireEvent.input(input, {target: {value: csv}});
    const confirm = screen.getByTestId('data-import-confirm');
    return confirm;
}

async function expectImportValidation(confirm: HTMLElement, expected: {validRows: number; errors: number; duplicates?: boolean; domainError?: boolean}) {
    await waitFor(() => {
        expect(confirm).toHaveAttribute('data-valid-rows', String(expected.validRows));
        expect(confirm).toHaveAttribute('data-error-count', String(expected.errors));
        expect(confirm).toHaveAttribute('data-has-duplicates', String(expected.duplicates ?? false));
        expect(confirm).toHaveAttribute('data-domain-error', String(expected.domainError ?? false));
    });
}

describe('DistributionDataImportModal — atomic percentage contract', () => {
    it('opens the distribution CSV documentation in an isolated tab', async () => {
        const open = vi.spyOn(window, 'open').mockReturnValue(null);
        try {
            distributionModal();

            const header = screen.getByTestId('data-import-modal-header');
            const docsButton = within(header).getByTestId('distribution-import-docs');
            await fireEvent.click(docsButton);

            expect(open).toHaveBeenCalledWith('/mkdocs/user/assets/create-edit/#importing-a-distribution-csv', '_blank', 'noopener');
        } finally {
            open.mockRestore();
        }
    });

    it('the pristine header-only state never reports the domain total error', async () => {
        // Regression guard: before the fix, `validateRows` ran unconditionally over
        // whatever rows existed — including the empty array present right after
        // open, before the user has typed a single data row past the pre-seeded
        // header — and reported "Weights must total 100 (current total: 0)" on a
        // modal nobody had touched yet. It is now guarded by `validRows.length > 0`.
        distributionModal();
        const confirm = await screen.findByTestId('data-import-confirm');

        await waitFor(() => {
            expect(confirm).toHaveAttribute('data-valid-rows', '0');
            expect(confirm).toHaveAttribute('data-domain-error', 'false');
        });
        expect(screen.queryByTestId('csv-domain-error')).not.toBeInTheDocument();
        expect(confirm).toBeDisabled();
    });

    it('blocks the whole import when any otherwise-surplus row is invalid', async () => {
        distributionModal();
        const confirm = await enterDistributionCsv('name,weight\nA,60\nB,40\nunknown,5');

        await expectImportValidation(confirm, {validRows: 2, errors: 1});
        expect(confirm).toBeDisabled();
    });

    it('blocks duplicate canonical identities even when the remaining rows total 100', async () => {
        distributionModal();
        const confirm = await enterDistributionCsv('name,weight\nA,0\n a ,0\nC,100');

        await expectImportValidation(confirm, {validRows: 1, errors: 0, duplicates: true});
        expect(
            screen
                .getByText(/duplicate names/)
                .textContent?.replace(/^•\s*/, '')
                .trim(),
        ).toBe('duplicate names');
        expect(confirm).toBeDisabled();
    });

    it.each(['-0.01', '100.01'])('rejects a weight outside the closed 0..100 range: %s', async (weight) => {
        distributionModal();
        const confirm = await enterDistributionCsv(`name,weight\nA,${weight}\nC,100`);

        await expectImportValidation(confirm, {validRows: 1, errors: 1});
        expect(confirm).toBeDisabled();
    });

    it('accepts both weight boundaries', async () => {
        distributionModal();
        const confirm = await enterDistributionCsv('name,weight\nA,0\nB,100');

        await waitFor(() => expect(confirm).toBeEnabled());
    });

    it('rejects totals at and beyond the 0.005 tolerance boundary', async () => {
        distributionModal();
        const input = await screen.findByTestId('csv-editor-input');
        const confirm = screen.getByTestId('data-import-confirm');

        // |total - 100| = 0.01, clearly outside the tolerance
        await fireEvent.input(input, {target: {value: 'name,weight\nA,33.33\nB,66.66'}});
        await expectImportValidation(confirm, {validRows: 2, errors: 0, domainError: true});
        expect(confirm).toBeDisabled();

        // The decimal total is exactly 99.995: the strict "< 0.005" contract rejects the boundary itself
        await fireEvent.input(input, {target: {value: 'name,weight\nA,30.002\nB,69.993'}});
        await expectImportValidation(confirm, {validRows: 2, errors: 0, domainError: true});
        expect(confirm).toBeDisabled();
    });

    it('accepts a total within the 0.005 tolerance without balancing and divides percentages exactly once', async () => {
        const {onimport} = distributionModal();
        const confirm = await enterDistributionCsv('name,weight\nA,33.33\nB,66.667');

        // |total - 100| = 0.003 < 0.005: inside the tolerance, so import is enabled even though
        // the raw weights sum to 99.997, not 100
        await waitFor(() => expect(confirm).toBeEnabled());
        await fireEvent.click(confirm);

        // no balancing: each imported value is the raw weight divided by 100 exactly once, left
        // summing to 0.99997 — never rescaled so the reported total is exactly 1
        expect(onimport).toHaveBeenCalledWith({A: 33.33 / 100, B: 66.667 / 100});
    });
});

async function importThroughDistributionEditor(kind: 'sector' | 'geographic', identity: string) {
    const onchange = vi.fn();
    render(DistributionEditor, {kind, value: {}, onchange});
    await fireEvent.click(screen.getByTestId(`distribution-import-${kind}`));
    const confirm = await enterDistributionCsv(`name,weight\n${identity},100`);
    return {confirm, onchange};
}

describe('DistributionEditor — exact reference-name resolution', () => {
    it.each([' it ', 'iTa', ' ITALIA '])('accepts an exact ISO2, ISO3, or current country name after case and trim normalization: %s', async (identity) => {
        const {confirm, onchange} = await importThroughDistributionEditor('geographic', identity);

        await waitFor(() => expect(confirm).toBeEnabled());
        await fireEvent.click(confirm);
        expect(onchange).toHaveBeenCalledWith({ITA: 1});
    });

    it('does not fuzzy-match a country name', async () => {
        const {confirm, onchange} = await importThroughDistributionEditor('geographic', 'Ital');

        // The unmatched row remains a row-level error. With zero valid rows,
        // cross-row total validation stays suppressed: reporting a 0% total here
        // would duplicate the real error with a misleading domain error.
        await expectImportValidation(confirm, {validRows: 0, errors: 1});
        expect(screen.queryByTestId('csv-domain-error')).not.toBeInTheDocument();
        expect(confirm).toBeDisabled();
        expect(onchange).not.toHaveBeenCalled();
    });

    it.each([
        [' technology ', 'Technology'],
        [' TECNOLOGIA ', 'Technology'],
        ['Obbligazioni societarie', 'Corporate Bonds'],
        ['Titoli di Stato', 'Government Bonds'],
        ['Finanziari', 'Financials'],
    ])('accepts an exact sector key or current Italian label after case and trim normalization: %s', async (identity, canonical) => {
        await setupI18n('it');
        try {
            const {confirm, onchange} = await importThroughDistributionEditor('sector', identity);
            await waitFor(() => expect(confirm).toBeEnabled());
            await fireEvent.click(confirm);
            expect(onchange).toHaveBeenCalledWith({[canonical]: 1});
        } finally {
            await setupI18n('en');
        }
    });

    it('does not fuzzy-match a sector', async () => {
        const {confirm, onchange} = await importThroughDistributionEditor('sector', 'Tech');

        // Same zero-valid-row contract as geographic import: preserve the
        // row-level rejection without inventing a cross-row total failure.
        await expectImportValidation(confirm, {validRows: 0, errors: 1});
        expect(screen.queryByTestId('csv-domain-error')).not.toBeInTheDocument();
        expect(confirm).toBeDisabled();
        expect(onchange).not.toHaveBeenCalled();
    });

    it('falls back to the canonical sector key, never the raw sectors.<key> path, when a translation is missing', async () => {
        // Same defect shape as the country/currency selects: a missing i18n entry
        // must degrade to the plain identifier a user already recognizes (the
        // sector key itself), never to the untranslated lookup path string.
        const onchange = vi.fn();
        render(DistributionEditor, {kind: 'sector', value: {}, onchange});
        await fireEvent.click(screen.getByTestId('distribution-add-sector'));

        const trigger = await screen.findByRole('combobox');
        await fireEvent.click(trigger);
        const option = await screen.findByTestId('search-select-option-SyntheticUntranslatedSector');

        // The dropdown option itself must show the bare key, not `sectors.` + key.
        expect(option.textContent ?? '').not.toContain('sectors.SyntheticUntranslatedSector');
        expect(option.textContent ?? '').toContain('SyntheticUntranslatedSector');

        await fireEvent.click(option);

        // And so must the trigger, once this becomes the row's selected value.
        await waitFor(() => expect(trigger.textContent ?? '').toContain('SyntheticUntranslatedSector'));
        expect(trigger.textContent ?? '').not.toContain('sectors.SyntheticUntranslatedSector');
    });
});

describe('DataEditor — dated import compatibility', () => {
    it('merges dated rows and ignores identified rows that belong to another editor', async () => {
        const onchange = vi.fn();
        const importedRows: ParsedRow[] = [
            {kind: 'identified', identity: 'Technology', values: {rate: 99}, lineNumber: 2},
            {kind: 'dated', date: '2024-06-10', values: {rate: 2}, lineNumber: 3},
            {kind: 'dated', date: '2024-06-11', values: {rate: 3}, lineNumber: 4},
        ];
        render(DataEditorImportHarness, {
            columns: COLS,
            rows: [row('2024-06-10', 1)],
            importedRows,
            onchange,
        });

        await fireEvent.click(screen.getByTestId('fx-data-import-btn'));
        await fireEvent.click(await screen.findByTestId('data-editor-test-import'));
        const dirty = lastDirty(onchange);

        expect(
            dirty.map((entry) => ({
                rowId: entry.rowId,
                status: entry.status,
                rate: entry.values.rate,
            })),
        ).toEqual([
            {rowId: '2024-06-10', status: 'edited', rate: 2},
            {rowId: '2024-06-11', status: 'appended', rate: 3},
        ]);
    });
});

describe('DataEditor — an event import matches on date and type (importMatchKeys)', () => {
    // A price has one row per date; an asset event does not: one date can carry a DIVIDEND and an
    // INTEREST, two rows with two DB ids. The events editor therefore asks DataEditor to match an
    // imported row on its date *and* its type (`importMatchKeys={['type']}`). Before that prop
    // existed, an import merged into the first row of the date, whatever its type: it rewrote an
    // event of another type, collapsed two imported events into one, and gave up on the whole date
    // whenever that first row was a readonly provider event. With no keys the match stays date-only:
    // the price and FX editors rely on it (guarded here and by the compatibility test above).
    // The rows mirror what `eventsToEventRows` loads: the rowId is the DB id, never the date.
    const D = '2026-03-02';
    const D2 = '2026-03-09';
    const EVENT_COLS: ColumnDef[] = [
        {
            key: 'type',
            label: 'Type',
            type: 'enum',
            editable: true,
            required: true,
            enumOptions: [
                {value: 'DIVIDEND', label: 'Dividend'},
                {value: 'INTEREST', label: 'Interest'},
                {value: 'SPLIT', label: 'Split'},
            ],
        },
        {key: 'amount', label: 'Amount', type: 'number', editable: true, required: true, step: 0.01},
        {key: 'notes', label: 'Notes', type: 'string', editable: true, required: false},
    ];

    function eventRow(rowId: string, date: string, type: string, amount: number, extra: Partial<DataRow> = {}): DataRow {
        return {rowId, date, status: 'original', originalStatus: 'original', values: {type, amount, notes: null}, selected: false, ...extra};
    }

    function importedEvent(date: string, type: string, amount: number, lineNumber = 2): ParsedRow {
        return {kind: 'dated', date, values: {type, amount}, lineNumber};
    }

    /** Render the editor over `rows`, open its import modal and run each batch as one import, in
     *  order. Returns the last dirty set the parent received and the row ids the table renders. */
    async function runImports(rows: DataRow[], batches: ParsedRow[][], importMatchKeys?: string[]) {
        const onchange = vi.fn();
        const {container} = render(DataEditorImportHarness, {columns: EVENT_COLS, rows, importBatches: batches, importMatchKeys, onchange});
        await fireEvent.click(screen.getByTestId('fx-data-import-btn'));
        for (let n = 1; n <= batches.length; n++) {
            await fireEvent.click(await screen.findByTestId(`data-editor-test-import-batch-${n}`));
        }
        const renderedIds = [...container.querySelectorAll('tr[data-row-id]')].map((tr) => tr.getAttribute('data-row-id'));
        return {dirty: lastDirty(onchange) ?? [], renderedIds};
    }

    /** What the save path reads from a dirty row. */
    const saved = (r: DataRow) => ({rowId: r.rowId, status: r.status, date: r.date, type: r.values.type, amount: r.values.amount});
    /** Same, without the rowId — for appended rows, whose id is checked on its own. */
    const savedNew = (r: DataRow) => ({status: r.status, date: r.date, type: r.values.type, amount: r.values.amount});
    const byType = (a: DataRow, b: DataRow) => String(a.values.type).localeCompare(String(b.values.type));

    it('an import of another type on an existing date appends a new event and leaves the existing one untouched', async () => {
        // Before the fix: matched on the date alone, so event 101 became an INTEREST of 2 — its
        // DIVIDEND gone from the editor, and on save a second event created beside the old one.
        const {dirty, renderedIds} = await runImports([eventRow('101', D, 'DIVIDEND', 1)], [[importedEvent(D, 'INTEREST', 2)]], ['type']);

        expect(dirty.map(savedNew)).toEqual([{status: 'appended', date: D, type: 'INTEREST', amount: 2}]);
        expect(dirty[0].rowId).not.toBe('101');
        expect(renderedIds).toContain('101');
        expect(renderedIds).toContain(dirty[0].rowId);
    });

    it('an import of the same type on an existing date edits that event in place', async () => {
        const {dirty} = await runImports([eventRow('101', D, 'DIVIDEND', 1)], [[importedEvent(D, 'DIVIDEND', 3)]], ['type']);

        expect(dirty.map(saved)).toEqual([{rowId: '101', status: 'edited', date: D, type: 'DIVIDEND', amount: 3}]);
    });

    it('a readonly event listed first does not hide an editable event of the same date and type', async () => {
        // Before the fix: the first row of the date was the readonly one, so the import was dropped.
        const rows = [eventRow('201', D, 'DIVIDEND', 1, {readonly: true}), eventRow('202', D, 'DIVIDEND', 2)];
        const {dirty} = await runImports(rows, [[importedEvent(D, 'DIVIDEND', 5)]], ['type']);

        expect(dirty.map(saved)).toEqual([{rowId: '202', status: 'edited', date: D, type: 'DIVIDEND', amount: 5}]);
    });

    it('a readonly event of another type does not swallow the imported event', async () => {
        // Before the fix: the date matched the readonly row and the imported DIVIDEND was dropped.
        const {dirty} = await runImports([eventRow('301', D, 'INTEREST', 1, {readonly: true})], [[importedEvent(D, 'DIVIDEND', 4)]], ['type']);

        expect(dirty.map(savedNew)).toEqual([{status: 'appended', date: D, type: 'DIVIDEND', amount: 4}]);
        expect(dirty[0].rowId).not.toBe('301');
    });

    it('a readonly event of the same type still refuses the import (readonly stays readonly)', async () => {
        const {dirty} = await runImports([eventRow('301', D, 'DIVIDEND', 1, {readonly: true})], [[importedEvent(D, 'DIVIDEND', 4)]], ['type']);

        expect(dirty).toEqual([]);
    });

    it('two events imported together on one new date stay two rows with distinct ids', async () => {
        // Before the fix: the first became an appended row whose rowId was the date, and the second
        // matched it by date and merged into it — one INTEREST row, the DIVIDEND lost.
        const {dirty, renderedIds} = await runImports([eventRow('101', D, 'DIVIDEND', 1)], [[importedEvent(D2, 'DIVIDEND', 4, 2), importedEvent(D2, 'INTEREST', 6, 3)]], ['type']);

        expect([...dirty].sort(byType).map(savedNew)).toEqual([
            {status: 'appended', date: D2, type: 'DIVIDEND', amount: 4},
            {status: 'appended', date: D2, type: 'INTEREST', amount: 6},
        ]);
        const ids = dirty.map((r) => r.rowId);
        // The contract names the scheme: the date itself, then `date#2`, `date#3`…
        expect([...ids].sort()).toEqual([D2, `${D2}#2`]);
        for (const id of ids) expect(renderedIds).toContain(id);
    });

    it('successive imports on one new date: a new type appends a second row, a known type merges into its own row', async () => {
        // Before the fix: every batch merged into the single appended row of the date.
        const batches = [[importedEvent(D2, 'DIVIDEND', 4)], [importedEvent(D2, 'INTEREST', 6)], [importedEvent(D2, 'DIVIDEND', 7)]];
        const {dirty, renderedIds} = await runImports([eventRow('101', D, 'DIVIDEND', 1)], batches, ['type']);

        expect([...dirty].sort(byType).map(savedNew)).toEqual([
            {status: 'appended', date: D2, type: 'DIVIDEND', amount: 7},
            {status: 'appended', date: D2, type: 'INTEREST', amount: 6},
        ]);
        const ids = dirty.map((r) => r.rowId);
        expect([...ids].sort()).toEqual([D2, `${D2}#2`]);
        for (const id of ids) expect(renderedIds).toContain(id);
    });

    it('without importMatchKeys the match stays date-only', async () => {
        const {dirty} = await runImports([eventRow('101', D, 'DIVIDEND', 1)], [[importedEvent(D, 'INTEREST', 2)]]);

        expect(dirty.map(saved)).toEqual([{rowId: '101', status: 'edited', date: D, type: 'INTEREST', amount: 2}]);
    });

    describe('the date picker of a new row (I-11d)', () => {
        // A new row's date is picked in a SingleDatePicker whose calendar refuses every date another row holds —
        // the row's own date excepted —, and `handleDateChange` refuses those dates a second time. For prices and
        // FX rates, one row per date, that is the rule. For events it is not: one date holds a DIVIDEND and an
        // INTEREST, yet a new DIVIDEND could not be moved to a day holding only an INTEREST. The contract, with
        // `importMatchKeys`: a new row is refused only the dates of the other rows whose values for those keys
        // equal its own, and its own date stays open; with no keys, every other row's date, as today.
        //
        // Read through the rendered calendar — a day is `calendar-day`, named by its `data-iso`, and disabled when
        // refused — and through the dirty rows the parent receives once a day is picked. FREE_DAY, a day no row
        // holds, is the control that the calendar refuses by rule and not because every day is closed.
        //
        // Red today: the new DIVIDEND's calendar refuses DAY_2, which holds only an INTEREST, and the row cannot
        // move there.

        /** Holds the original DIVIDEND — with rate rows, simply another row. */
        const DAY_1 = '2024-03-04';
        /** Holds the original INTEREST — with rate rows, simply another row. */
        const DAY_2 = '2024-03-11';
        /** The new row's day, and its rowId, as for a row added by the + button. */
        const NEW_DAY = '2024-03-18';
        /** No row holds it. */
        const FREE_DAY = '2024-03-25';
        const NEW: Partial<DataRow> = {status: 'appended', originalStatus: 'appended'};

        /** An original DIVIDEND, an original INTEREST and a new DIVIDEND, each on its own day. */
        const eventRows = (): DataRow[] => [eventRow('101', DAY_1, 'DIVIDEND', 1), eventRow('102', DAY_2, 'INTEREST', 2), eventRow(NEW_DAY, NEW_DAY, 'DIVIDEND', 3, NEW)];

        function mountEvents(rows: DataRow[], importMatchKeys?: string[]) {
            const onchange = vi.fn();
            const {container} = render(DataEditor, {props: {columns: EVENT_COLS, rows, importMatchKeys, onchange}});
            return {onchange, container};
        }

        /**
         * The open calendar of row `rowId` — only a new row's date cell holds a picker. The picker's state is
         * read before its button is clicked: the button toggles, and a blind click would close an open calendar.
         */
        async function calendarOf(container: HTMLElement, rowId: string): Promise<HTMLElement> {
            const cell = container.querySelector<HTMLElement>(`tr[data-row-id="${rowId}"] td[data-column-id="date"]`);
            if (!cell) throw new Error(`no date cell in row ${rowId}`);
            const picker = within(cell).getByTestId('single-date-picker-root');
            if (picker.getAttribute('data-open') !== 'true') await fireEvent.click(within(picker).getByTestId('single-date-picker-calendar-button'));
            expect(picker, `the calendar of row ${rowId} is open`).toHaveAttribute('data-open', 'true');
            return within(picker).getByTestId('single-date-picker-popover');
        }

        function dayOf(calendar: HTMLElement, iso: string): HTMLButtonElement {
            const day = calendar.querySelector<HTMLButtonElement>(`[data-testid="calendar-day"][data-iso="${iso}"]`);
            if (!day) throw new Error(`the calendar shows no ${iso}`);
            return day;
        }

        /** Whether the calendar of row `rowId` refuses each of the four days. */
        async function refusedDays(container: HTMLElement, rowId: string): Promise<Record<string, boolean>> {
            const calendar = await calendarOf(container, rowId);
            return Object.fromEntries([DAY_1, DAY_2, NEW_DAY, FREE_DAY].map((iso) => [iso, dayOf(calendar, iso).disabled]));
        }

        /** Click the day `iso` in the calendar of row `rowId`, as a user picks it. */
        async function pickDay(container: HTMLElement, rowId: string, iso: string): Promise<void> {
            await fireEvent.click(dayOf(await calendarOf(container, rowId), iso));
        }

        /** Every dirty set the parent received, each row by its status and date. */
        const emitted = (onchange: ReturnType<typeof vi.fn>) => onchange.mock.calls.map(([dirty]) => (dirty as DataRow[]).map((r) => ({status: r.status, date: r.date})));

        it('the calendar of a new DIVIDEND refuses the day of another DIVIDEND, not the day of an INTEREST, nor its own', async () => {
            const {container} = mountEvents(eventRows(), ['type']);

            expect(await refusedDays(container, NEW_DAY)).toEqual({[DAY_1]: true, [DAY_2]: false, [NEW_DAY]: false, [FREE_DAY]: false});
        });

        it('a new DIVIDEND picked onto the day of an INTEREST moves there: still new, and handed to the parent on that day', async () => {
            const {onchange, container} = mountEvents(eventRows(), ['type']);

            await pickDay(container, NEW_DAY, DAY_2);

            expect((lastDirty(onchange) ?? []).map(savedNew)).toEqual([{status: 'appended', date: DAY_2, type: 'DIVIDEND', amount: 3}]);
        });

        it('a new DIVIDEND picked onto the day of another DIVIDEND stays where it is, while a free day takes it (guard)', async () => {
            const {onchange, container} = mountEvents(eventRows(), ['type']);

            await pickDay(container, NEW_DAY, DAY_1);
            expect(onchange, 'the refused pick changed nothing').not.toHaveBeenCalled();

            await pickDay(container, NEW_DAY, FREE_DAY);
            expect(emitted(onchange), 'control: the same row does move, to a day no row holds').toEqual([[{status: 'appended', date: FREE_DAY}]]);
        });

        it.each([
            {setup: 'rate rows, as for prices and FX', mountRows: () => mount([row(DAY_1, 1), row(DAY_2, 2), row(NEW_DAY, 3, NEW)])},
            {setup: 'the event rows', mountRows: () => mountEvents(eventRows())},
        ])('without importMatchKeys ($setup) every other row’s day stays refused, and a pick onto one changes nothing (guard)', async ({mountRows}) => {
            const {onchange, container} = mountRows();

            expect(await refusedDays(container, NEW_DAY)).toEqual({[DAY_1]: true, [DAY_2]: true, [NEW_DAY]: false, [FREE_DAY]: false});

            await pickDay(container, NEW_DAY, DAY_2);
            expect(onchange, 'the refused pick changed nothing').not.toHaveBeenCalled();

            await pickDay(container, NEW_DAY, FREE_DAY);
            expect(emitted(onchange), 'control: the same row does move, to a day no row holds').toEqual([[{status: 'appended', date: FREE_DAY}]]);
        });
    });
});

/** The events import modal, open, with a spy on what it hands on. */
function eventImportModal() {
    const onimport = vi.fn();
    render(EventDataImportModal, {open: true, onimport});
    return {onimport};
}

/** The rows handed to `onimport` by its single call. */
function importedRows(onimport: ReturnType<typeof vi.fn>): ParsedRow[] {
    expect(onimport).toHaveBeenCalledTimes(1);
    return onimport.mock.calls[0][0] as ParsedRow[];
}

describe('EventDataImportModal — a file written by the events export imports back', () => {
    // `GET /api/v1/backup/asset/{id}/events?format=csv` (backend/app/api/v1/backup.py) writes this
    // header — `;`-separated, CRLF line ends, the amount in a column named `value`, among columns the
    // modal does not know. The modal requires `amount`; the column definition carries `value` as an
    // alias, looked up only when the `amount` label itself is absent.
    const EXPORT_HEADER = 'date;type;value;currency;source;provider_assignment_id;notes;created_at;updated_at';

    it('accepts the export header verbatim and reads the amount from `value`', async () => {
        // Before the fix: "Missing required columns: amount", so every data row waits on the header.
        const {onimport} = eventImportModal();
        // `enterDistributionCsv` is modal-agnostic: it fills `csv-editor-input`, returns `data-import-confirm`.
        const confirm = await enterDistributionCsv(`${EXPORT_HEADER}\r\n2026-03-15;DIVIDEND;0.37;USD;MANUAL;;e2e-note;2026-03-15T10:00:00;2026-03-15T10:00:00`);

        await expectImportValidation(confirm, {validRows: 1, errors: 0});
        expect(confirm).toBeEnabled();
        await fireEvent.click(confirm);

        const rows = importedRows(onimport);
        expect(rows).toHaveLength(1);
        expect(rows[0]).toMatchObject({kind: 'dated', date: '2026-03-15', values: {type: 'DIVIDEND', amount: 0.37, currency: 'USD', notes: 'e2e-note'}});
    });

    it.each([
        ['after', 'date;type;amount;value;notes', '2026-03-16;DIVIDEND;1.5;9.99;n'],
        ['before', 'date;type;value;amount;notes', '2026-03-16;DIVIDEND;9.99;1.5;n'],
    ])('with both columns present the `amount` label wins over its alias (`value` %s `amount`)', async (_where, header, line) => {
        const {onimport} = eventImportModal();
        const confirm = await enterDistributionCsv(`${header}\n${line}`);

        await expectImportValidation(confirm, {validRows: 1, errors: 0});
        await fireEvent.click(confirm);

        const rows = importedRows(onimport);
        expect(rows).toHaveLength(1);
        expect(rows[0]).toMatchObject({kind: 'dated', date: '2026-03-16', values: {type: 'DIVIDEND', amount: 1.5}});
    });
});

// =====================================================================================================================
// B-39 — a formula-like text, escaped by the export, imports back as it was written (written red first)
// =====================================================================================================================

/*
 * The series export writes a text a spreadsheet would run as a formula (one starting with `=`, `+`, `-`, `@`, a tab or
 * a CR, after any apostrophes; a plain number never) with one more leading `'`. The events import drops exactly one
 * again: the module script of EventDataImportModal.svelte exports `unescapeFormulaText(raw)`, and the modal's `notes`
 * column parses with it (CsvEditor calls a string column's `parse` only for a non-empty, trimmed cell).
 *
 * Red today: the modal exports no `unescapeFormulaText`. Vite reads a missing export of a module it transforms as
 * `undefined`, so each case of the function fails on its own call and the rest of this file runs as before; the
 * modal's case is red because the `notes` column hands the apostrophe on.
 */

/** As the export writes it, then as the import must read it: exactly one leading apostrophe dropped. */
const ONE_APOSTROPHE_DROPPED: Array<[string, string]> = [
    ["'=1+1", '=1+1'],
    ["'@x", '@x'],
    ["'-2+3", '-2+3'],
    ["'+cmd", '+cmd'],
    ["''=x", "'=x"],
    ["'''@y", "''@y"],
    ["'\t=1", '\t=1'],
    ["'\r=1", '\r=1'],
];

/** Texts the import leaves as they are: no apostrophe stands before a formula character. */
const UNCHANGED: Array<[string, string]> = [
    ['an apostrophe before a letter', "'hello"],
    ['a formula with no apostrophe to drop', '=1'],
    ['a plain number, which the export never escapes', '-1.5'],
    ['an equals sign inside the text', 'a = b'],
    ['two apostrophes and nothing after them', "''"],
];

/** The originals the export escapes, each written with one more leading apostrophe (its Python: `"'" + text`). */
const ESCAPED_BY_THE_EXPORT: Array<[string, string]> = [
    ['a formula', '=1+1'],
    ['an at sign', '@x'],
    ['a minus that starts no number', '-2+3'],
    ['a plus', '+cmd'],
    ['a formula behind one apostrophe', "'=x"],
    ['an at sign behind two apostrophes', "''@y"],
    ['a tab', '\t=1'],
    ['a carriage return', '\r=1'],
];

describe('B-39 — unescapeFormulaText: the events import drops the one apostrophe the export added', () => {
    it.each(ONE_APOSTROPHE_DROPPED)('%j → %j: one apostrophe dropped', (exported, expected) => {
        expect(unescapeFormulaText(exported)).toBe(expected);
    });

    it.each(UNCHANGED)('%s (%j): unchanged', (_what, text) => {
        expect(unescapeFormulaText(text)).toBe(text);
    });

    it.each(ESCAPED_BY_THE_EXPORT)('the round trip of %s (%j): exported with one more apostrophe, imported as the original', (_what, original) => {
        expect(unescapeFormulaText(`'${original}`), 'export, then import').toBe(original);
    });
});

describe('B-39 — EventDataImportModal: the notes column drops the apostrophe the export added', () => {
    it('a note the export escaped imports back as it was written; a note it left alone stays as it is', async () => {
        const {onimport} = eventImportModal();
        // The header the events export writes (the case above), and three notes as it writes them.
        const csv = [
            'date;type;value;currency;source;provider_assignment_id;notes;created_at;updated_at',
            "2026-03-15;DIVIDEND;0.37;USD;MANUAL;;'=1+1;2026-03-15T10:00:00;2026-03-15T10:00:00",
            "2026-03-16;DIVIDEND;0.38;USD;MANUAL;;''@y;2026-03-16T10:00:00;2026-03-16T10:00:00",
            "2026-03-17;DIVIDEND;0.39;USD;MANUAL;;'hello;2026-03-17T10:00:00;2026-03-17T10:00:00",
        ].join('\r\n');
        const confirm = await enterDistributionCsv(csv);

        await expectImportValidation(confirm, {validRows: 3, errors: 0});
        await fireEvent.click(confirm);

        expect(importedRows(onimport)).toMatchObject([
            {kind: 'dated', date: '2026-03-15', values: {notes: '=1+1'}},
            {kind: 'dated', date: '2026-03-16', values: {notes: "'@y"}},
            {kind: 'dated', date: '2026-03-17', values: {notes: "'hello"}},
        ]);
    });
});

describe('CSV import — two lines are duplicates only when their date and every matchKey value agree (I-11a)', () => {
    // CsvEditor flags as duplicates — and leaves out of the import — every line that shares its date with another,
    // whatever else the two lines say. For prices and FX rates, one row per date, that is the rule. For asset events
    // it is not: a DIVIDEND and a SPLIT of one day were both dropped (the data editor's page states it as a limit).
    // The contract: a column marked `matchKey` (CsvColumnDef) belongs to a line's identity, and two lines are
    // duplicates only when their date — or identity value, in an identity editor — and the value of every matchKey
    // column are equal. The events modal marks its `type`; prices, FX rates and distributions mark nothing, and
    // keep one line per date.
    //
    // Read from what the editor and the modal publish — the rows handed on, the error count, the duplicate flag —,
    // never from the message, whose wording of the key is free.
    //
    // Red today: the flag is ignored, so two lines that differ only in a matchKey column are duplicates, and the
    // events modal drops a DIVIDEND and a SPLIT of one day.

    const DAY = '2024-01-02';
    const OTHER_DAY = '2024-01-09';

    /** `tag` belongs to a line's identity, `amount` does not. */
    const TAG_KEY: CsvColumnDef[] = [
        {key: 'tag', label: 'tag', type: 'string', required: true, matchKey: true},
        {key: 'amount', label: 'amount', type: 'number', required: true},
    ];
    /** Two matchKey columns: a line's identity takes both. */
    const TAG_AND_CURRENCY_KEYS: CsvColumnDef[] = [
        {key: 'tag', label: 'tag', type: 'string', required: true, matchKey: true},
        {key: 'currency', label: 'currency', type: 'string', required: true, matchKey: true},
        {key: 'amount', label: 'amount', type: 'number', required: true},
    ];

    it.each([
        {
            editor: 'a dated editor, one matchKey column',
            columns: TAG_KEY,
            identity: undefined,
            csv: `date;tag;amount\n${DAY};A;1\n${DAY};B;2`,
            expected: [
                {kind: 'dated', date: DAY, values: {tag: 'A', amount: 1}, lineNumber: 2},
                {kind: 'dated', date: DAY, values: {tag: 'B', amount: 2}, lineNumber: 3},
            ],
        },
        {
            editor: 'a dated editor, two matchKey columns, the second one differing',
            columns: TAG_AND_CURRENCY_KEYS,
            identity: undefined,
            csv: `date;tag;currency;amount\n${DAY};A;USD;1\n${DAY};A;EUR;2`,
            expected: [
                {kind: 'dated', date: DAY, values: {tag: 'A', currency: 'USD', amount: 1}, lineNumber: 2},
                {kind: 'dated', date: DAY, values: {tag: 'A', currency: 'EUR', amount: 2}, lineNumber: 3},
            ],
        },
        {
            editor: 'an identity editor, one matchKey column',
            columns: TAG_KEY,
            identity: {key: 'name', label: 'name'},
            csv: 'name;tag;amount\nalpha;A;1\nalpha;B;2',
            expected: [
                {kind: 'identified', identity: 'alpha', values: {tag: 'A', amount: 1}, lineNumber: 2},
                {kind: 'identified', identity: 'alpha', values: {tag: 'B', amount: 2}, lineNumber: 3},
            ],
        },
    ])('$editor: two lines that differ in a matchKey value are both kept', async ({columns, identity, csv, expected}) => {
        const [rows, errors, duplicates] = await parsedCsv(csv, columns, identity);

        expect({rows, errors, duplicates}).toEqual({rows: expected, errors: 0, duplicates: false});
    });

    it.each([
        {
            lines: 'the same matchKey value, another amount',
            columns: TAG_KEY,
            csv: `date;tag;amount\n${DAY};A;1\n${DAY};A;2\n${OTHER_DAY};A;3`,
            kept: {kind: 'dated', date: OTHER_DAY, values: {tag: 'A', amount: 3}, lineNumber: 4},
        },
        {
            lines: 'no matchKey column, another value in a required string column',
            columns: CSV_COLUMNS,
            csv: `date;note;amount\n${DAY};x;1\n${DAY};y;2\n${OTHER_DAY};x;3`,
            kept: {kind: 'dated', date: OTHER_DAY, values: {note: 'x', amount: 3}, lineNumber: 4},
        },
    ])('two lines of one date with $lines are still duplicates, both left out (guard)', async ({columns, csv, kept}) => {
        const [rows, errors, duplicates] = await parsedCsv(csv, columns);

        // The line of the other day is the control: duplicates leave out their own lines, not the whole paste.
        expect({rows, errors, duplicates}).toEqual({rows: [kept], errors: 0, duplicates: true});
    });

    it('the events modal keeps a DIVIDEND and a SPLIT of one day, and hands both on with their types', async () => {
        const {onimport} = eventImportModal();
        const confirm = await enterDistributionCsv(`date;type;amount\n${DAY};DIVIDEND;0.37\n${DAY};SPLIT;2`);

        await expectImportValidation(confirm, {validRows: 2, errors: 0, duplicates: false});
        await fireEvent.click(confirm);

        expect(importedRows(onimport)).toMatchObject([
            {kind: 'dated', date: DAY, values: {type: 'DIVIDEND', amount: 0.37}},
            {kind: 'dated', date: DAY, values: {type: 'SPLIT', amount: 2}},
        ]);
    });

    it('the events modal still leaves out two DIVIDENDs of one day (guard)', async () => {
        const {onimport} = eventImportModal();
        const confirm = await enterDistributionCsv(`date;type;amount\n${DAY};DIVIDEND;0.37\n${DAY};DIVIDEND;0.41\n${OTHER_DAY};DIVIDEND;0.39`);

        await expectImportValidation(confirm, {validRows: 1, errors: 0, duplicates: true});
        await fireEvent.click(confirm);

        expect(importedRows(onimport), 'only the line of the other day is handed on').toMatchObject([{kind: 'dated', date: OTHER_DAY, values: {type: 'DIVIDEND', amount: 0.39}}]);
    });

    it('the prices modal still leaves out two lines of one day in two currencies: the rule is matchKey, not any required string column (guard)', async () => {
        const onimport = vi.fn();
        render(PriceDataImportModal, {open: true, onimport});
        const confirm = await enterDistributionCsv(`date;currency;close\n${DAY};USD;145.5\n${DAY};EUR;133.2\n${OTHER_DAY};USD;146.1`);

        await expectImportValidation(confirm, {validRows: 1, errors: 0, duplicates: true});
        await fireEvent.click(confirm);

        expect(importedRows(onimport), 'only the line of the other day is handed on').toMatchObject([{kind: 'dated', date: OTHER_DAY, values: {currency: 'USD', close: 146.1}}]);
    });
});

describe('DataEditor — a value rendered into an html cell stays text (K step 13, item 0)', () => {
    // Four branches of the column builder hand DataTable an `html` cell — rendered with `{@html}` —
    // built around the row's own value: a readonly row of a string column, of an enum column whose
    // value matches no option (the fallback label), of a currency column, and every column of a
    // readonly editor. Rows are readonly when they are auto/provider events, and asset events belong
    // to global assets: a note written as markup would run for every user who opens the asset. So
    // these cases read the rendered cell rather than the payload the parent receives — the rendered
    // cell is where the defect is.
    const PAYLOAD = '<img src=x onerror="window.__k13=1">';
    const KIND_OPTIONS = [
        {value: 'DIVIDEND', label: 'Dividend', emoji: '💰'},
        {value: 'SPLIT', label: 'Split', emoji: '✂️'},
    ];
    const NOTES: ColumnDef = {key: 'notes', label: 'Notes', type: 'string', editable: true, required: false};
    const KIND: ColumnDef = {key: 'kind', label: 'Kind', type: 'enum', editable: true, required: true, enumOptions: KIND_OPTIONS};
    const CURRENCY: ColumnDef = {key: 'currency', label: 'Currency', type: 'currency', editable: true, required: false};

    // `ordinary` carries an ampersand where the column takes free text: it must come out as `&`, never
    // as `&amp;` — the control that would catch an escape applied twice.
    const PATHS = [
        {path: '(a) a readonly row of a string column', column: NOTES, readonlyEditor: false, readonlyRow: true, ordinary: 'Paid & reinvested'},
        {path: '(b) an enum column, value outside the options', column: KIND, readonlyEditor: false, readonlyRow: true, ordinary: 'LEGACY_KIND'},
        {path: '(c) a readonly row of a currency column', column: CURRENCY, readonlyEditor: false, readonlyRow: true, ordinary: 'EUR'},
        {path: '(d) a string column of a readonly editor', column: NOTES, readonlyEditor: true, readonlyRow: false, ordinary: 'Paid & reinvested'},
    ];

    interface CellSetup {
        readonlyEditor?: boolean;
        readonlyRow?: boolean;
        readonlyReason?: string;
    }

    /** DataTable marks the header, not the cell: the header's position names the cell of a row. */
    function cellOf(container: HTMLElement, rowId: string, columnId: string): Element {
        const header = container.querySelector(`th[data-testid="dt-header-${columnId}"]`);
        const tr = container.querySelector(`tr[data-row-id="${rowId}"]`);
        if (!header?.parentElement || !tr) throw new Error(`no ${columnId} header, or no row ${rowId}`);
        const cell = tr.children[[...header.parentElement.children].indexOf(header)];
        if (cell?.tagName !== 'TD') throw new Error(`no ${columnId} cell in row ${rowId}`);
        return cell;
    }

    async function renderCell(column: ColumnDef, value: string, {readonlyEditor = false, readonlyRow = false, readonlyReason}: CellSetup = {}): Promise<Element> {
        const rows: DataRow[] = [{rowId: 'k13', date: '2026-01-05', status: 'original', originalStatus: 'original', values: {[column.key]: value}, selected: false, readonly: readonlyRow, readonlyReason}];
        const {container} = render(DataEditor, {props: {columns: [column], rows, readonly: readonlyEditor, onchange: vi.fn()}});
        return waitFor(() => cellOf(container, 'k13', column.key));
    }

    const handlerAttributes = (root: Element): string[] =>
        [...root.querySelectorAll('*')].flatMap((el) =>
            el
                .getAttributeNames()
                .filter((name) => name.toLowerCase().startsWith('on'))
                .map((name) => `<${el.tagName.toLowerCase()} ${name}>`),
        );

    it.each(PATHS)('$path: a value made of markup is shown as text', async ({column, readonlyEditor, readonlyRow}) => {
        const cell = await renderCell(column, PAYLOAD, {readonlyEditor, readonlyRow});
        expect.soft(cell.querySelectorAll('img').length, 'the value must not become an <img>').toBe(0);
        expect.soft(handlerAttributes(cell), 'the value must not add a handler').toEqual([]);
        expect.soft(cell.textContent?.trim(), 'the cell must show the value as the characters it is made of').toBe(PAYLOAD);
    });

    it.each(PATHS)('$path: an ordinary value is shown unchanged (control)', async ({column, readonlyEditor, readonlyRow, ordinary}) => {
        // Also the proof that `cellOf` finds the cell the cases above read.
        const cell = await renderCell(column, ordinary, {readonlyEditor, readonlyRow});
        expect(cell.textContent?.trim()).toBe(ordinary);
    });

    it('an enum value matching an option shows its emoji and label, and the lock badge stays markup (control)', async () => {
        const cell = await renderCell(KIND, 'DIVIDEND', {readonlyRow: true, readonlyReason: 'Auto-generated by provider'});
        expect(cell.textContent).toContain('💰 Dividend');
        expect([...cell.querySelectorAll('span')].some((span) => span.textContent === '🔒')).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// The marker locale — shared by the describes below that ask whether a label comes from the catalogue
// ---------------------------------------------------------------------------
// A private-use language where every key of the English catalogue, and each key a cure adds, reads as a
// marker of itself (`⟦common.status⟧`, or `⟦key n=3⟧` for a message given values): a label the component
// takes from the catalogue reads its marker, a literal written in the component reads as itself. That asks
// whether the code uses the key, never what a language says; whether the four catalogues have the key is
// asked of the JSON files (`catalogueGaps`). Each describe that switches to it puts English back after
// every test.

/** A private-use language (BCP 47 reserves qaa–qtz): Intl accepts it, and it is none of the app's catalogues. */
const MARKER_LOCALE = 'qaa';
/** The four shipped catalogues, by language. */
const SHIPPED_CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

/** How a label reads in the marker locale: `⟦key⟧`, or `⟦key n=3⟧` for a message given values. */
const marked = (key: string, values: Record<string, string | number> = {}): string => `⟦${[key, ...Object.entries(values).map(([name, value]) => `${name}=${value}`)].join(' ')}⟧`;

/** The value behind a dotted key of a catalogue, if any. */
const leafOf = (catalogue: unknown, key: string): unknown => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);

/** Every dotted key of a catalogue that holds a string. */
function stringKeysOf(node: unknown, prefix = ''): string[] {
    if (typeof node === 'string') return [prefix];
    if (node === null || typeof node !== 'object') return [];
    return Object.entries(node).flatMap(([part, child]) => stringKeysOf(child, prefix ? `${prefix}.${part}` : part));
}

/** Each of `keys` that some catalogue has no string for, with those catalogues: `{}` when all four have all of them. */
function catalogueGaps(keys: readonly string[]): Record<string, string[]> {
    const gaps = keys.map((key) => [key, Object.entries(SHIPPED_CATALOGUES).flatMap(([lang, catalogue]) => (typeof leafOf(catalogue, key) === 'string' ? [] : [lang]))] as const);
    return Object.fromEntries(gaps.filter(([, langs]) => langs.length > 0));
}

/** Switch svelte-i18n to the marker locale: every key of the English catalogue reads as its marker, and so does every key of `added` — a key the cure adds, with the names of its values. */
async function useMarkerLocale(added: Record<string, readonly string[]>): Promise<void> {
    const messages: Record<string, string> = Object.fromEntries(stringKeysOf(en).map((key) => [key, marked(key)]));
    for (const [key, names] of Object.entries(added)) messages[key] = marked(key, Object.fromEntries(names.map((name) => [name, `{${name}}`])));
    addMessages(MARKER_LOCALE, messages);
    await setupI18n(MARKER_LOCALE);
}

describe('DataEditor — the status column is labelled from the catalogues (P, item 8)', () => {
    // The status column (hidden until the column menu shows it) is English written in the code: the
    // header 'Status', the filter options 'Original', 'Edited', 'Deleted' and 'New', and a badge that
    // reads 'New' for an appended row and the capitalised status otherwise — the same English in
    // Italian, French and Spanish. The contract: the header is `common.status`, and a status reads
    // `dataEditor.status.<status>` on its badge and on its filter option alike, so the two always say
    // the same thing.
    //
    // Observed without reading a language. The editor is mounted in a marker locale, where every key
    // of the English catalogue, and each key the cure adds, reads as a marker of itself
    // (`⟦common.status⟧`): a label the component takes from the catalogue reads its marker, a literal
    // written in the component reads as itself. That asks whether the code uses the key; whether the
    // four catalogues have it is asked of the JSON files, in the first case. The control: the add-row
    // button, already `common.addRow`, reads its marker — or the locale never switched, and nothing
    // here means anything.
    //
    // Red today: header and menu read 'Status'; badges and options 'Original', 'Edited', 'Deleted' and
    // 'New'; no catalogue has `dataEditor.status`.

    const STATUSES = ['original', 'edited', 'deleted', 'appended'] as const;
    type Status = (typeof STATUSES)[number];
    const statusKey = (status: Status): string => `dataEditor.status.${status}`;
    /** One row per status, each on its own date — its rowId, as for prices. */
    const ROW_OF: Record<Status, string> = {original: '2024-06-10', edited: '2024-06-11', deleted: '2024-06-12', appended: '2024-06-13'};

    beforeEach(async () => {
        await useMarkerLocale(Object.fromEntries(STATUSES.map((status) => [statusKey(status), []])));
    });

    afterEach(async () => {
        await setupI18n('en');
    });

    /** Mount one row per status, and check that the marker locale is live. */
    function mountStatuses(): HTMLElement {
        const {container} = mount(STATUSES.map((status) => row(ROW_OF[status], 1, {status, originalStatus: status === 'appended' ? 'appended' : 'original'})));
        expect(screen.getByTestId('fx-data-add-row-btn'), 'control: a label the editor already takes from the catalogue reads its marker').toHaveTextContent(marked('common.addRow'));
        return container;
    }

    /**
     * Show the status column, hidden by default, from the column menu, and return the name the menu
     * gives it. The column's state is read before the click: DataTable remembers the choice wherever
     * there is a localStorage (this jsdom has none), and a blind click would hide a column on screen.
     */
    async function showStatusColumn(): Promise<string> {
        await fireEvent.click(screen.getByTestId('column-visibility-toggle'));
        const item = await screen.findByTestId('column-visibility-item-status');
        const menuName = item.textContent?.trim() ?? '';
        if (!screen.queryByTestId('dt-header-status')) await fireEvent.click(item);
        await screen.findByTestId('dt-header-status');
        await fireEvent.click(screen.getByTestId('column-visibility-toggle'));
        expect(screen.queryByTestId('column-visibility-dropdown'), 'the column menu closes again').toBeNull();
        return menuName;
    }

    /** The text of a row's cell in one column. DataTable marks the header, not the cell: the header's position names it. */
    function cellText(container: HTMLElement, columnId: string, rowId: string): string {
        const header = container.querySelector(`th[data-testid="dt-header-${columnId}"]`);
        const tr = container.querySelector(`tr[data-row-id="${rowId}"]`);
        if (!header?.parentElement || !tr) throw new Error(`no ${columnId} header, or no row ${rowId}`);
        const cell = tr.children[[...header.parentElement.children].indexOf(header)];
        if (cell?.tagName !== 'TD') throw new Error(`no ${columnId} cell in row ${rowId}`);
        return cell.textContent?.trim() ?? '';
    }

    it('the four catalogues have every label of the column', () => {
        expect(catalogueGaps(['common.status', ...STATUSES.map(statusKey)]), 'key → the catalogues with no string for it').toEqual({});
    });

    it('names the column common.status, in the table header and in the column menu', async () => {
        mountStatuses();
        const menu = await showStatusColumn();
        const header = screen.getByTestId('dt-header-status').textContent?.trim();

        expect({header, menu}).toEqual({header: marked('common.status'), menu: marked('common.status')});
    });

    it('labels each status dataEditor.status.<status>, on its badge and on its filter option alike', async () => {
        const container = mountStatuses();
        await showStatusColumn();
        const badges = Object.fromEntries(STATUSES.map((status) => [status, cellText(container, 'status', ROW_OF[status])]));
        await fireEvent.click(screen.getByTestId('col-filter-trigger-status'));
        const filter = await screen.findByTestId('column-filter');
        // An option reads its label, then how many rows hold that status.
        const options = Object.fromEntries(STATUSES.map((status) => [status, within(filter).getByTestId(`filter-enum-option-${status}`).textContent?.trim()]));

        const said = Object.fromEntries(STATUSES.map((status) => [status, {badge: badges[status], option: options[status]}]));
        expect(said).toEqual(Object.fromEntries(STATUSES.map((status) => [status, {badge: marked(statusKey(status)), option: expect.stringContaining(marked(statusKey(status)))}])));
    });
});

describe('DataEditor — the toolbar counters and the stale-rows switch are labelled from the catalogues (P-15, W part)', () => {
    // The toolbar counts the rows the user has changed in English written in the code — «2 modified»,
    // «1 deleted», «3 new» — and names the switch that hides the stale rows «Hide 2 stale rows», then
    // «Show 2 stale rows»: the same English in Italian, French and Spanish, and read aloud by a screen
    // reader. The contract: each counter reads `dataEditor.counter.<status>` (edited, deleted, appended)
    // with `n` its number of rows; the switch is named `dataEditor.staleHide` while the stale rows show and
    // `dataEditor.staleShow` once they are hidden — today's ternary — with `n` the number of stale rows.
    //
    // Read in the marker locale (above); control: the add-row button, already `common.addRow`, reads its
    // marker. The counters have no handle of their own, so they are looked for among the texts the editor
    // writes outside its grid, element by element: a red lists what the toolbar says instead.
    //
    // Red today: the counters read «2 modified», «1 deleted», «3 new»; the switch «Hide 2 stale rows», then
    // «Show 2 stale rows»; no catalogue has the five keys.

    const COUNTERS = [
        {status: 'edited', key: 'dataEditor.counter.edited', n: 2},
        {status: 'deleted', key: 'dataEditor.counter.deleted', n: 1},
        {status: 'appended', key: 'dataEditor.counter.appended', n: 3},
    ] as const;
    const STALE_SHOW = 'dataEditor.staleShow';
    const STALE_HIDE = 'dataEditor.staleHide';
    /** The keys the cure adds, each given `n`. */
    const ADDED_KEYS = [...COUNTERS.map(({key}) => key), STALE_SHOW, STALE_HIDE];

    const squash = (text: string): string => text.replace(/\s+/g, ' ').trim();

    beforeEach(async () => {
        await useMarkerLocale(Object.fromEntries(ADDED_KEYS.map((key) => [key, ['n']])));
    });

    afterEach(async () => {
        await setupI18n('en');
    });

    /** Mount `rows`, and check that the marker locale is live. */
    function mountMarked(rows: DataRow[]): HTMLElement {
        const {container} = mount(rows);
        expect(screen.getByTestId('fx-data-add-row-btn'), 'control: a label the editor already takes from the catalogue reads its marker').toHaveTextContent(marked('common.addRow'));
        return container;
    }

    /**
     * One original row, then as many rows in each status as its counter will say: 2 edited, 1 deleted,
     * 3 appended — three different numbers, so a counter handed another one's count is caught. Each row on
     * its own day, its rowId, as for prices.
     */
    function countedRows(): DataRow[] {
        let day = 0;
        const nextDay = (): string => `2024-06-${String(++day).padStart(2, '0')}`;
        return [row(nextDay()), ...COUNTERS.flatMap(({status, n}) => Array.from({length: n}, () => row(nextDay(), 1, {status, originalStatus: status === 'appended' ? 'appended' : 'original'})))];
    }

    /** What the editor writes outside its grid — its toolbar —, element by element: each element's own text. */
    function textsOutsideGrid(): string[] {
        return [...screen.getByTestId('data-editor-root').querySelectorAll('*')]
            .filter((element) => element.closest('table') === null)
            .map((element) => squash([...element.childNodes].map((node) => (node.nodeType === Node.TEXT_NODE ? (node.textContent ?? '') : '')).join('')))
            .filter((text) => text !== '');
    }

    it('the four catalogues have the five new labels', () => {
        expect(catalogueGaps(ADDED_KEYS), 'key → the catalogues with no string for it').toEqual({});
    });

    it('each counter reads dataEditor.counter.<status>, its n the number of rows in that status', () => {
        mountMarked(countedRows());

        expect(textsOutsideGrid(), 'what the editor writes outside its grid').toEqual(expect.arrayContaining(COUNTERS.map(({key, n}) => marked(key, {n}))));
    });

    it('the stale-rows switch is named dataEditor.staleHide while they show, dataEditor.staleShow once they are hidden, its n the number of stale rows', async () => {
        const container = mountMarked([row('2024-06-10'), row('2024-06-01', 1, {staleDays: 5}), row('2024-06-02', 1, {staleDays: 3})]);
        const toggle = within(screen.getByTestId('data-editor-stale-toggle')).getByRole('switch');
        expect(toggle, 'premise: the stale rows show').toHaveAttribute('aria-checked', 'false');
        const whileShown = toggle.getAttribute('aria-label');

        await fireEvent.click(toggle);
        await waitFor(() => expect(container.querySelector('tr[data-row-id="2024-06-01"]'), 'premise: the click hid the stale rows').toBeNull());
        expect(toggle).toHaveAttribute('aria-checked', 'true');
        const whileHidden = toggle.getAttribute('aria-label');

        expect({whileShown, whileHidden}).toEqual({whileShown: marked(STALE_HIDE, {n: 2}), whileHidden: marked(STALE_SHOW, {n: 2})});
    });
});

describe('DataImportModal — the help and close buttons are named from the catalogues (W-B8)', () => {
    // The import modal's header names its two icon buttons in English written in the code: aria-label
    // «Help» on the help toggle — whose title is already `csvImport.helpTitle` — and «Close» on ✕, the same
    // English to a screen reader in Italian, French and Spanish. The contract: the help button is named
    // `csvImport.helpTitle`, like its title, and the close button `common.close`; both keys exist.
    //
    // Read in the marker locale (above), on the events import modal: it gives help content and no header
    // action, so its header holds exactly these two buttons. The help button is the one titled with the
    // marker of `csvImport.helpTitle` — which is also the control that the locale is live —, and the close
    // button is the other one, proved by what a click on it does.
    //
    // Red today: «Help» and «Close».

    beforeEach(async () => {
        await useMarkerLocale({});
    });

    afterEach(async () => {
        await setupI18n('en');
    });

    it('the help button is named csvImport.helpTitle, the close button common.close', async () => {
        const onclose = vi.fn();
        render(EventDataImportModal, {open: true, onclose});
        const buttons = within(await screen.findByTestId('data-import-modal-header')).getAllByRole('button');
        expect(buttons, 'premise: the header holds the help button and the close button').toHaveLength(2);
        const help = buttons.find((button) => button.getAttribute('title') === marked('csvImport.helpTitle'));
        if (!help) throw new Error(`control: no header button is titled ${marked('csvImport.helpTitle')}: the help button lost its title, or the marker locale is not live (titles: ${JSON.stringify(buttons.map((button) => button.getAttribute('title')))})`);
        const close = buttons.find((button) => button !== help);
        if (!close) throw new Error('premise: the header holds a second button besides the help button');
        const said = {help: help.getAttribute('aria-label'), close: close.getAttribute('aria-label')};

        await fireEvent.click(close);
        expect(onclose, 'premise: the other header button closes the modal').toHaveBeenCalledTimes(1);

        expect(said).toEqual({help: marked('csvImport.helpTitle'), close: marked('common.close')});
    });
});

describe('DataImportModal — the footer Cancel and the discard confirmation are named by test id (X-R9)', () => {
    // The footer's Cancel button has no test id, and neither has the confirmation the modal raises before it throws
    // away what the user typed: a spec reaches them only through their translated text, a selector the project
    // forbids. The contract: Cancel is `data-import-cancel`; the discard confirmation — a ConfirmModal, which puts
    // its `testId` on its header — is `data-import-discard-confirm`. What they do does not change: a clean modal
    // closes at once; one holding typed data asks first, from Cancel as from ✕ (`data-import-modal-close`, already
    // named), and the confirmation's confirm closes it.
    //
    // Red today: neither test id exists.

    /** The generic import modal, open on two columns, with a spy on its close. */
    function importModal() {
        const onclose = vi.fn();
        render(DataImportModal, {open: true, columns: CSV_COLUMNS, onclose});
        return {onclose};
    }

    it('on a clean modal, data-import-cancel closes it at once, asking nothing', async () => {
        const {onclose} = importModal();
        expect(await screen.findByTestId('data-import-modal'), 'premise: the modal is open').toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('data-import-cancel'));

        expect(onclose).toHaveBeenCalledTimes(1);
        await waitFor(() => expect(screen.queryByTestId('data-import-modal')).toBeNull());
        expect(screen.queryByTestId('confirm-modal-message'), 'no confirmation was raised').toBeNull();
    });

    it.each(['data-import-cancel', 'data-import-modal-close'])('on a modal holding typed data, %s asks first, in data-import-discard-confirm, whose confirm closes it', async (closeButton) => {
        const {onclose} = importModal();
        const confirm = await enterDistributionCsv('date;note;amount\n2024-01-02;typed;1');
        await expectImportValidation(confirm, {validRows: 1, errors: 0}); // premise: the typed line reached the modal

        await fireEvent.click(screen.getByTestId(closeButton));

        expect(await screen.findByTestId('confirm-modal-message'), 'premise: a confirmation is on screen').toBeInTheDocument();
        expect(screen.queryByTestId('data-import-discard-confirm'), 'the confirmation on screen is data-import-discard-confirm').not.toBeNull();
        expect(onclose, 'nothing is thrown away before the user confirms').not.toHaveBeenCalled();
        expect(screen.getByTestId('data-import-modal'), 'the import modal stays open behind it').toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        expect(onclose).toHaveBeenCalledTimes(1);
        await waitFor(() => expect(screen.queryByTestId('data-import-modal')).toBeNull());
    });
});

/**
 * M-17, M-18 CP2 — the date column and the numbers in the interface language.
 *
 * Every figure follows the UI language (the developer's rule of 2026-10-12), and the words around it come
 * from the catalogue. The date column was written in a fixed language: the weekday beside each date
 * (`toLocaleDateString('en-US', {weekday: 'short'})`, M-17), its header (`'Date'`) and the stale marker's
 * title (`"N days stale"`); and the number of a readonly row in an editable number column went through
 * `toLocaleString(undefined, …)`, the browser's notation. The cure: the weekday and the number in
 * `uiLocale()`, the header `common.date`, the title `chart.tooltip.stale` with `days` = N. No key is added:
 * the four catalogues have both.
 *
 * The visible `⚠️ Nd` badge is out of this lot — its «d» is English, backlog T-ST — and is never read.
 *
 * Expectations. The weekday and the number are Intl's output for the interface locale with the component's
 * options, never typed; the header is read from the shipped catalogue; the title is produced by the app's
 * own formatter — `$_('chart.tooltip.stale', {values: {days}})`, once the language's catalogue is loaded —
 * never copied from the message, which may change. jsdom's browser is en-US, so the English UI keeps
 * en-US. A cell is found by its header's position, as DataTable marks the header and not the cell.
 *
 * Language. `currentLanguage.set`, as LanguageSelector does (it also moves svelte-i18n), put back after
 * each test.
 */
describe('DataEditor — the date column and the numbers in the interface language (M-17, M-18 CP2)', () => {
    type UiLanguage = 'en' | 'it';
    /** The interface locale of each language: jsdom's browser is en-US. */
    const LOCALE_OF: Record<UiLanguage, string> = {en: 'en-US', it: 'it'};
    const CATALOGUES = {en, it: itCatalogue};

    /** A Monday, on a fresh row. */
    const MONDAY = '2026-01-05';
    /** A readonly row of the editable `rate` column, carrying RATE. */
    const READONLY = '2026-01-06';
    /** Thousands and four decimals: every separator of a notation shows. */
    const RATE = 12345.6789;
    /** A row five days behind its source. */
    const STALE = '2026-01-02';
    const STALE_DAYS = 5;

    /** The weekday of `iso` as Intl writes it for `lang`, with the component's options. */
    const weekdayIn = (lang: UiLanguage, iso = MONDAY): string => new Date(iso + 'T00:00:00Z').toLocaleDateString(LOCALE_OF[lang], {weekday: 'short', timeZone: 'UTC'});
    /** RATE as Intl writes it for `lang`, with the component's options. */
    const rateIn = (lang: UiLanguage): string => RATE.toLocaleString(LOCALE_OF[lang], {maximumFractionDigits: 4});
    const squash = (text: string | null | undefined): string => (text ?? '').replace(/\s+/g, ' ').trim();

    /** DataTable marks the header, not the cell: the header's position names the cell of a row. */
    function cellOf(container: HTMLElement, rowId: string, columnId: string): Element {
        const header = container.querySelector(`th[data-testid="dt-header-${columnId}"]`);
        const tr = container.querySelector(`tr[data-row-id="${rowId}"]`);
        if (!header?.parentElement || !tr) throw new Error(`no ${columnId} header, or no row ${rowId}`);
        const cell = tr.children[[...header.parentElement.children].indexOf(header)];
        if (cell?.tagName !== 'TD') throw new Error(`no ${columnId} cell in row ${rowId}`);
        return cell;
    }

    /** A fresh Monday, a readonly row and a stale row; resolves once the three rows are drawn. */
    async function mountRows(): Promise<HTMLElement> {
        const {container} = mount([row(MONDAY, 1), row(READONLY, RATE, {readonly: true}), row(STALE, 1, {staleDays: STALE_DAYS})]);
        await waitFor(() => [MONDAY, READONLY, STALE].forEach((rowId) => cellOf(container, rowId, 'date')));
        return container;
    }

    /** Change the UI language as LanguageSelector does; the catalogue is loaded before the next step. */
    async function uiLanguage(lang: UiLanguage): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        await tick();
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it('English UI on an en-US browser (control): the weekday, the number and the header as today', async () => {
        await uiLanguage('en');
        const container = await mountRows();

        expect(squash(cellOf(container, MONDAY, 'date').textContent)).toBe(`${MONDAY} ${weekdayIn('en')}`);
        expect(squash(cellOf(container, READONLY, 'rate').textContent)).toBe(rateIn('en'));
        expect(screen.getByTestId('dt-header-date').textContent?.trim()).toBe(CATALOGUES.en.common.date);
    });

    it('Italian UI: the weekday beside each date in Italian', async () => {
        await uiLanguage('it');
        expect(weekdayIn('it'), 'control: the Italian weekday differs from the English one').not.toBe(weekdayIn('en'));
        const container = await mountRows();

        expect(squash(cellOf(container, MONDAY, 'date').textContent)).toBe(`${MONDAY} ${weekdayIn('it')}`);
    });

    it('Italian UI: a readonly row writes its number in Italian notation', async () => {
        await uiLanguage('it');
        expect(rateIn('it'), 'control: the Italian notation differs from the English one').not.toBe(rateIn('en'));
        const container = await mountRows();

        expect(squash(cellOf(container, READONLY, 'rate').textContent)).toBe(rateIn('it'));
    });

    it('Italian UI: the date column is headed common.date', async () => {
        await uiLanguage('it');
        expect(CATALOGUES.it.common.date, 'control: the Italian header differs from the English one').not.toBe(CATALOGUES.en.common.date);
        await mountRows();

        expect(screen.getByTestId('dt-header-date').textContent?.trim()).toBe(CATALOGUES.it.common.date);
    });

    it.each(['en', 'it'] as const)('the stale marker’s title is chart.tooltip.stale of the UI language, its days the row’s (%s)', async (lang) => {
        await uiLanguage(lang);
        const expected = get(translate)('chart.tooltip.stale', {values: {days: STALE_DAYS}});
        expect(expected, 'control: the formatter found the message in the catalogue').not.toBe('chart.tooltip.stale');
        expect(expected, 'control: the formatter filled in the days').toContain(String(STALE_DAYS));
        const container = await mountRows();

        const titled = [...cellOf(container, STALE, 'date').querySelectorAll('[title]')];
        expect(titled, 'the stale row’s date cell carries one titled marker').toHaveLength(1);
        expect(titled[0].getAttribute('title')).toBe(expected);
    });
});
