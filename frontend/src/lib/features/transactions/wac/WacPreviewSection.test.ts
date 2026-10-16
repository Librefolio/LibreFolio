// @vitest-environment jsdom
/**
 * WacPreviewSection — the qualifying-transactions table under the global privacy toggle.
 * Component test (Vitest + jsdom), workstream J (privacy), checkpoint C6.
 *
 * The rule, developer decision D5′-c: a UNIT value — a price, a WAC, a unit cost — is `public`
 * and always visible; a TOTAL — a cash amount, a value, a P&L — is `personal` and masked while
 * privacy is on. Every money cell of this table is a unit value: the unit cost of each
 * qualifying transaction — for a cross-currency row both the original amount and the converted
 * one — and the running WAC after it. A unit value is not patrimony without a quantity, and the
 * quantity beside it is the quantity of a transaction, which D5′ leaves visible (quantities are
 * masked only beside a price in positions and lots). So with privacy on, every cell of the
 * table must still read exactly as it reads with privacy off: digits and currency.
 *
 * How the two tests tell a regression apart:
 *   - a unit value left `personal` in a component that re-renders on the toggle fails the first
 *     test at its first toggle (off → on) and the second at mount;
 *   - a unit value left `personal` in a component that does NOT re-render on the toggle would
 *     pass the first test vacuously — the cells simply keep their mount-time text — and that is
 *     what the second test is for: mounted with privacy already on, a masked site renders
 *     masked whatever its reactivity.
 * There is no personal amount in this table to serve as an in-component positive control, so
 * every step checks two layer controls before the table, and a red names its layer: the flag
 * really moved (`isPrivacyEnabled()`), and a fresh personal call to the very formatter the cells
 * use masks. The quantity of each row is a third, always-visible control: it proves the row is
 * rendered and read in the right column, so a "digits present" assertion cannot pass on the
 * wrong cell.
 *
 * Selection. The table by its `{testid}-qualifying-table` handle; a row by the transaction id
 * its first cell prints — data this spec owns, never a position among the rows; a cell by the
 * column order of the template (#, type, date, quantity, unit cost, effect, WAC). The cells
 * publish no handle of their own, so every read first checks the header and the row still have
 * exactly those seven columns: a column added or moved fails with a message instead of reading
 * a neighbour. Nothing here reads translated text: headers are counted, never read.
 *
 * Expectations. The clear text of every cell comes from the formatter the template calls, with
 * the template's own options, computed with privacy off — `toLocaleString(undefined, …)`
 * follows the host locale, so a frozen literal would turn a de-DE runner red — and each one is
 * checked once against the digits put in. Masked strings are literals: a placeholder has no
 * locale.
 *
 * Storage. The shared `$app/environment` mock reports `browser: false`, so the privacy store
 * keeps the flag in memory and never touches `localStorage`; the component's own storage read
 * (the Total/Per-unit toggle) is try/catch-guarded and does not reach the table.
 *
 * The interface language (M-18 CP3a, last block). The quantity of each qualifying transaction is
 * the backend's exact decimal string, shown through `formatDecimalForDisplay` — exact digits, cut at
 * the eighth, trailing zeros dropped — but with a dot and no grouping in every language. The cure
 * writes the same digits in the interface locale (`formatExactDecimal`): `1.234.567,12345678` in an
 * Italian UI, and in an English one `1,234,567.12345678`, grouped from a thousand on — the new
 * contract of English. The expected text is Intl's output for the interface locale, handed
 * `formatDecimalForDisplay`'s digits as a string; no localized literal is typed. jsdom's browser is
 * en-US: an English UI is written en-US, an Italian one bare `it`. The unit cost of the same rows
 * already follows the interface language (the shared currency formatter, CP2): when the language is
 * switched in place it is the in-component control that the switch reached the table, so a red
 * after it is the quantity's own. The quantities below 1000 of the privacy cases read the same
 * before and after the cure.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {waitLocale} from 'svelte-i18n';

// The only request this graph makes is the currency catalogue (the currency store behind the
// formatter, and the currency chip of the cost-basis input). It is answered here so every money
// cell carries a real symbol and flag, as in the app. Every other method is inert.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') {
                    return vi.fn(async () => ({
                        items: [
                            {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
                            {code: 'USD', name: 'US Dollar', symbol: '$', flag_emoji: '🇺🇸', country_codes: ['US'], country_names: ['United States']},
                        ],
                    }));
                }
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {fireEvent, render, screen, setupI18n} from '$test/component';
import {currentLanguage} from '$lib/stores/app/language';
import {isPrivacyEnabled, setPrivacyEnabled, togglePrivacy} from '$lib/stores/app/privacyStore.svelte';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
import {formatCurrencyAmountPlain, type CurrencyAmountFormatOptions} from '$lib/utils/currency/currencyFormat';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import WacPreviewSection from './WacPreviewSection.svelte';

const P = PRIVACY_PLACEHOLDER;
const TESTID = 'c6-wac';

/** A same-currency BUY: unit cost and running WAC both in EUR, no conversion. */
const SAME_CURRENCY = {
    tx_id: 7101,
    type: 'BUY',
    date: '2026-01-15',
    quantity: '12.5',
    unit_cost: '98.76',
    currency: 'EUR',
    effect: 'add',
    running_wac: '98.76',
    fx_info: null,
};

/** A cross-currency BUY: paid 123.45 USD per unit, converted at 0.91 to the EUR the WAC is kept in. */
const CROSS_CURRENCY = {
    tx_id: 7102,
    type: 'BUY',
    date: '2026-02-20',
    quantity: '7.25',
    unit_cost: '112.34',
    currency: 'EUR',
    effect: 'add',
    running_wac: '103.7451',
    original_unit_cost: '123.45',
    original_currency: 'USD',
    fx_rate_used: '0.91',
    // One day back: an FX conversion (the 💱 badge renders), not a stale one (no banner).
    fx_info: {fx_rate_date: '2026-02-19', fx_days_back: 1},
};

const ROWS = [SAME_CURRENCY, CROSS_CURRENCY] as const;

/** The column order of the qualifying table, as the template writes it. */
const COLUMNS = ['id', 'type', 'date', 'quantity', 'unitCost', 'effect', 'wac'] as const;
type Column = (typeof COLUMNS)[number];

/** The cells under test, per row: the always-visible control and the two unit-value columns. */
interface RowCells {
    quantity: string;
    unitCost: string;
    wac: string;
}

/** Filled in `beforeAll`, once the currency cache is loaded, with privacy off. */
let clearCells: Record<number, RowCells> = {};
let personalClear = '';
const PERSONAL_AMOUNT = 4321.5;

/** Text as a reader sees it: whitespace runs collapsed, template indentation trimmed. */
function norm(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** The formatter the template calls, with its options, in the clear. */
function plain(amount: string, code: string, opts: CurrencyAmountFormatOptions): string {
    return norm(formatCurrencyAmountPlain(parseFloat(amount), code, {...opts, sensitivity: 'public'}));
}

/** A fresh `externalResult`, as TransactionFormModal passes it after a validate. */
function externalResult() {
    return {
        wac: {code: 'EUR', amount: '103.7451'},
        qualifying_txs: ROWS.map((row) => structuredClone(row)),
        missing_pairs: [],
    };
}

function mount(result: ReturnType<typeof externalResult> = externalResult()): void {
    // `value` already equals the result's WAC, so the auto-fill effect has nothing to push.
    render(WacPreviewSection, {value: {...result.wac}, onChange: vi.fn(), mode: 'auto', testid: TESTID, externalResult: result});
}

function table(): HTMLElement {
    return screen.getByTestId(`${TESTID}-qualifying-table`);
}

/** Open the qualifying table and assert it is open: the expand control is a toggle, so it is clicked only when the table is closed. */
async function openQualifyingTable(rows: ReadonlyArray<{tx_id: number}> = ROWS): Promise<void> {
    // Barrier: the expand control exists only once the external result has been adopted.
    const expand = await screen.findByTestId(`${TESTID}-show-qualifying`);
    if (!screen.queryByTestId(`${TESTID}-qualifying-table`)) await fireEvent.click(expand);
    expect(table(), 'the qualifying table is open').toBeInTheDocument();
    for (const row of rows) rowOf(row.tx_id);
}

/** The one body row whose first cell prints `txId`. */
function rowOf(txId: number): HTMLTableRowElement {
    const headers = table().querySelectorAll('thead th').length;
    if (headers !== COLUMNS.length) throw new Error(`the qualifying table has ${headers} columns, this spec maps ${COLUMNS.length}: re-read the template`);
    const matches = [...table().querySelectorAll<HTMLTableRowElement>('tbody tr')].filter((tr) => norm(tr.cells[COLUMNS.indexOf('id')]?.textContent) === String(txId));
    if (matches.length !== 1) throw new Error(`${matches.length} qualifying rows print tx #${txId}, expected exactly one`);
    if (matches[0].cells.length !== COLUMNS.length) throw new Error(`the row of tx #${txId} has ${matches[0].cells.length} cells for ${COLUMNS.length} columns`);
    return matches[0];
}

function cellText(txId: number, column: Column): string {
    return norm(rowOf(txId).cells[COLUMNS.indexOf(column)].textContent);
}

/** Every cell under test, keyed by transaction id: one object, so a red diff shows them all at once. */
function observedCells(): Record<number, RowCells> {
    return Object.fromEntries(ROWS.map((row) => [row.tx_id, {quantity: cellText(row.tx_id, 'quantity'), unitCost: cellText(row.tx_id, 'unitCost'), wac: cellText(row.tx_id, 'wac')}]));
}

/**
 * Flip the flag through the store's own toggle — the call the header's PrivacyToggle makes —
 * then flush: synchronously, and once more through the microtask the app itself waits on.
 */
async function togglePrivacyInPlace(): Promise<void> {
    togglePrivacy();
    flushSync();
    await tick();
}

/**
 * The table reads exactly as with privacy off, whatever the flag says. Controls first, so a red
 * names its layer; then the always-visible quantities; then the subject.
 */
function expectUnitValuesPublic(step: string, privacyOn: boolean): void {
    expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(privacyOn);
    expect(norm(formatCurrencyAmountPlain(PERSONAL_AMOUNT, 'EUR')), `${step} — control: a personal amount through the same formatter`).toBe(privacyOn ? `${P} € 🇪🇺 EUR` : personalClear);

    for (const row of ROWS) {
        expect(cellText(row.tx_id, 'quantity'), `${step} — control: the quantity of tx #${row.tx_id} stays visible`).toBe(clearCells[row.tx_id].quantity);
    }

    // The subject: unit cost (original → converted, or plain) and running WAC, every row at once.
    expect(observedCells(), `${step} — unit cost and running WAC are unit values, public under D5′-c: digits and currency as with privacy off`).toEqual(clearCells);
    expect(norm(table().textContent), `${step} — no placeholder anywhere in the qualifying table`).not.toContain(P);
}

beforeAll(async () => {
    await setupI18n();
    await ensureCurrenciesLoaded('en');
    // Control: the cache is really populated, so every money cell carries the symbol and flag.
    expect(getCurrencyInfo('USD').symbol).toBe('$');

    setPrivacyEnabled(false);
    personalClear = norm(formatCurrencyAmountPlain(PERSONAL_AMOUNT, 'EUR'));
    clearCells = {
        [SAME_CURRENCY.tx_id]: {
            quantity: norm(formatDecimalForDisplay(SAME_CURRENCY.quantity)),
            unitCost: plain(SAME_CURRENCY.unit_cost, 'EUR', {maxFraction: 2}),
            wac: plain(SAME_CURRENCY.running_wac, 'EUR', {maxFraction: 4}),
        },
        [CROSS_CURRENCY.tx_id]: {
            quantity: norm(formatDecimalForDisplay(CROSS_CURRENCY.quantity)),
            unitCost: `${plain(CROSS_CURRENCY.original_unit_cost, 'USD', {maxFraction: 2})} → ${plain(CROSS_CURRENCY.unit_cost, 'EUR', {maxFraction: 2})}`,
            wac: plain(CROSS_CURRENCY.running_wac, 'EUR', {maxFraction: 4}),
        },
    };

    // The clear expectations are the formatters' own output, so check once that they carry the
    // digits and currencies put in: a formatter masking unconditionally would otherwise make
    // "reads as with privacy off" compare the placeholder with itself.
    const digits = (text: string): string => text.replace(/\D/g, '');
    expect(digits(personalClear)).toBe('432150');
    expect(digits(clearCells[SAME_CURRENCY.tx_id].quantity)).toBe('125');
    expect(digits(clearCells[SAME_CURRENCY.tx_id].unitCost)).toBe('9876');
    expect(digits(clearCells[SAME_CURRENCY.tx_id].wac)).toBe('9876');
    expect(digits(clearCells[CROSS_CURRENCY.tx_id].quantity)).toBe('725');
    expect(digits(clearCells[CROSS_CURRENCY.tx_id].unitCost)).toBe('1234511234');
    expect(digits(clearCells[CROSS_CURRENCY.tx_id].wac)).toBe('1037451');
    expect(clearCells[CROSS_CURRENCY.tx_id].unitCost).toMatch(/USD → .*EUR$/);
    for (const cells of Object.values(clearCells)) expect(Object.values(cells).join(' ')).not.toContain(P);
});

afterEach(() => {
    // The flag is module-level state shared by every test in this file: a leftover `true`
    // would mount the next table masked.
    setPrivacyEnabled(false);
});

describe('WacPreviewSection — qualifying table: unit cost and running WAC are public (D5′-c)', () => {
    it('mounted in the clear: keeps every unit cost (original → converted) and running WAC in the clear when privacy turns on in place, and after it turns off', async () => {
        mount();
        await openQualifyingTable();
        expectUnitValuesPublic('mount, privacy off', false);

        await togglePrivacyInPlace();
        expectUnitValuesPublic('off → on', true);

        await togglePrivacyInPlace();
        expectUnitValuesPublic('on → off', false);
    });

    it('mounted with privacy already on: shows every unit cost and running WAC from the first render, and still after privacy turns off', async () => {
        setPrivacyEnabled(true);
        flushSync();
        mount();
        await openQualifyingTable();
        expectUnitValuesPublic('mount, privacy on', true);

        await togglePrivacyInPlace();
        expectUnitValuesPublic('on → off', false);
    });
});

// ---------------------------------------------------------------------------
// M-18 CP3a — the quantity column in the interface language
// ---------------------------------------------------------------------------

/**
 * What Intl writes for the plain decimal `text` in `locale`, with exactly its own fraction digits. Intl is handed
 * the string, which Intl.NumberFormat v3 reads as an exact decimal: no double in between.
 */
function intlExact(locale: string, text: string): string {
    const fractionDigits = text.split('.')[1]?.length ?? 0;
    return new Intl.NumberFormat(locale, {minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits}).format(text as Intl.StringNumericLiteral);
}

describe('WacPreviewSection — qualifying table: the quantity column in the interface language (M-18 CP3a)', () => {
    type UiLanguage = 'en' | 'it';
    /** The interface locale of each language: jsdom's browser is en-US. */
    const LOCALE_OF: Readonly<Record<UiLanguage, string>> = {en: 'en-US', it: 'it'};

    /** Quantities as the backend sends them: thousands with a ninth fraction digit the table cuts, a small fraction, trailing zeros. */
    const DECIMAL_ROWS = [
        {...SAME_CURRENCY, tx_id: 7201, quantity: '1234567.123456789'},
        {...SAME_CURRENCY, tx_id: 7202, quantity: '0.00012345'},
        {...SAME_CURRENCY, tx_id: 7203, quantity: '6.000000'},
    ];

    function decimalResult(): ReturnType<typeof externalResult> {
        return {wac: {code: 'EUR', amount: SAME_CURRENCY.running_wac}, qualifying_txs: DECIMAL_ROWS.map((row) => structuredClone(row)), missing_pairs: []};
    }

    /** The quantity column as `locale` writes it: formatDecimalForDisplay's digits (the template's cut at eight), handed to Intl as a string. */
    function quantitiesIn(locale: string): Record<number, string> {
        return Object.fromEntries(DECIMAL_ROWS.map((row) => [row.tx_id, norm(intlExact(locale, formatDecimalForDisplay(row.quantity)))]));
    }

    function observedQuantities(): Record<number, string> {
        return Object.fromEntries(DECIMAL_ROWS.map((row) => [row.tx_id, cellText(row.tx_id, 'quantity')]));
    }

    /** Change the UI language as LanguageSelector does, flush, and check the interface locale it gives. */
    async function uiLanguage(lang: UiLanguage): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        flushSync();
        await tick();
        expect(uiLocale(), `control: a ${lang} UI on jsdom's en-US browser is written ${LOCALE_OF[lang]}`).toBe(LOCALE_OF[lang]);
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it('Italian UI: every quantity in Italian notation — formatDecimalForDisplay’s digits, cut at the eighth, never rounded', async () => {
        await uiLanguage('it');
        expect(formatDecimalForDisplay(DECIMAL_ROWS[0].quantity), 'control: the template cuts at the eighth digit, it does not round').toBe('1234567.12345678');
        const italian = quantitiesIn('it');
        expect(italian[7201], 'control: Italian writes the quantity otherwise than English').not.toBe(quantitiesIn('en-US')[7201]);
        expect(italian[7201].replace(/\D/g, ''), 'control: and keeps its digits').toBe('123456712345678');

        mount(decimalResult());
        await openQualifyingTable(DECIMAL_ROWS);

        expect(observedQuantities()).toEqual(italian);
    });

    it('follows a language switch in place: English (en-US, grouped from 1,000 on — the new contract) → Italian → English', async () => {
        await uiLanguage('en');
        mount(decimalResult());
        await openQualifyingTable(DECIMAL_ROWS);
        const unitCost = () => cellText(DECIMAL_ROWS[0].tx_id, 'unitCost');
        const unitCostEnglish = plain(SAME_CURRENCY.unit_cost, 'EUR', {maxFraction: 2});
        expect(unitCost(), 'control: the unit cost, written by the shared formatter in the English UI').toBe(unitCostEnglish);

        expect(observedQuantities(), 'English UI: en-US notation').toEqual(quantitiesIn('en-US'));

        await uiLanguage('it');
        const unitCostItalian = plain(SAME_CURRENCY.unit_cost, 'EUR', {maxFraction: 2});
        expect(unitCostItalian, 'control: Italian writes the unit cost otherwise').not.toBe(unitCostEnglish);
        expect(unitCost(), 'control: the unit cost followed the switch, so the table was redrawn').toBe(unitCostItalian);

        expect(observedQuantities(), 'switched to Italian in place').toEqual(quantitiesIn('it'));

        await uiLanguage('en');
        expect(unitCost(), 'control: the unit cost came back to English').toBe(unitCostEnglish);

        expect(observedQuantities(), 'back to English in place').toEqual(quantitiesIn('en-US'));
    });
});
