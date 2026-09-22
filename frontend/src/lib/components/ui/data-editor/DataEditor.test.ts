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
 * What is deliberately left to the E2E suite: the date cell's embedded
 * SingleDatePicker (handleDateChange). CSV import is exercised here through a
 * tiny caller-supplied snippet because the dated-vs-identified dispatch is pure
 * component state and needs no browser or backend.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {render, screen, fireEvent, setupI18n, waitFor, within} from '$test/component';
import DataEditor from './DataEditor.svelte';
import type {ColumnDef, DataRow} from './DataEditorTypes';
import CsvEditor from './CsvEditor.svelte';
import type {CsvColumnDef, ParsedRow} from './CsvEditor.svelte';
import DistributionDataImportModal from '$lib/components/assets/DistributionDataImportModal.svelte';
import DistributionEditor from '$lib/components/ui/input/DistributionEditor.svelte';
import DataEditorImportHarness from '$test/harness/DataEditorImportHarness.svelte';

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

async function parsedCsv(value: string, columns: CsvColumnDef[] = CSV_COLUMNS) {
    const onvalidchange = vi.fn();
    render(CsvEditor, {columns, value, onvalidchange});
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
