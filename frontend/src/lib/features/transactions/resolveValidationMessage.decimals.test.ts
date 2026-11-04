// @vitest-environment node
/**
 * C-97a (GitHub issue #43) — a value refused for its decimal places reads «field: why», in the user's language
 * (Vitest, node).
 *
 * The contract (the developer's decisions, 16/10; D5 the coordinator's, 16/10 17:05). `POST /transactions/validate` and
 * `/commit` refuse a quantity with more than 10 decimal places, a cash amount with more than 6 and a manual cost basis —
 * a per-unit price (D5) — with more than 12, with the issue
 * `{code: 'decimalPlacesExceeded', params: {max}, field}`, and any of them past 15 significant digits with
 * `{code: 'significantDigitsExceeded', params: {max: 15}, field}`; `field` is `quantity`, `cash.amount` or
 * `cost_basis_override`. The catalogue gains `transactions.errors.decimalPlacesExceeded` (EN «At most {max} decimal
 * places», IT «Al massimo {max} decimali», FR «Au maximum {max} décimales», ES «Como máximo {max} decimales») and
 * `transactions.errors.significantDigitsExceeded` (EN «At most {max} significant digits», IT «Al massimo {max} cifre
 * significative», FR «Au maximum {max} chiffres significatifs», ES «Como máximo {max} cifras significativas»). For these
 * two codes `resolveIssueMessage` puts the translated field label in front, `transactions.fields.<field, dots as
 * underscores>`: `{code: 'decimalPlacesExceeded', params: {max: 10}, field: 'quantity'}` reads «Quantity: At most 10
 * decimal places», `{…, params: {max: 12}, field: 'cost_basis_override'}` «Cost basis override: At most 12 decimal places».
 *
 * Two halves, a red for each:
 * - the resolver, the catalogue faked as the resolver's own tests fake it (`resolveValidationMessage.test.ts`): today a
 *   custom code's text comes back as it is, so «At most 10 decimal places» comes back without its label;
 * - the catalogue, the app's own: svelte-i18n with the `<lang>.json` Vitest's global setup builds from the sources,
 *   the language switched in place as the language selector does. Today neither key exists, so the resolver falls back
 *   to the backend's English `error`, behind the label.
 * Guards, green today and after: `costBasisRequired`, an existing code sent with a field, keeps its own text without
 * the label — the label goes in front of the two new codes only.
 *
 * The texts are asserted on purpose: the translation is the subject here. English is pinned whole, as the contract
 * writes it; in Italian the error texts are the contract's, and the field labels are read from the catalogue, where
 * they already live — with controls that they exist and differ from the English ones.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action
 * `core-unit`), next to `resolveValidationMessage.test.ts`.
 *
 * R13-SEC2 (W-B58, E's security review of 17/10; the limits of the coordinator's decision N63). A third code of a value
 * over its column's limit: past the digits the column keeps before the decimal point, the batch answers
 * `{code: 'integerDigitsExceeded', params: {max}, field}` — `max` 15 for a quantity and a cash amount, 12 for a per-unit
 * cost basis. The catalogue gains `transactions.errors.integerDigitsExceeded` (EN «At most {max} digits before the
 * decimal point», IT «Al massimo {max} cifre prima della virgola», FR «Au maximum {max} chiffres avant la virgule», ES
 * «Como máximo {max} cifras en la parte entera»), and the code joins `FIELD_PREFIXED_CODES`: the label goes in front,
 * «Quantity: At most 15 digits before the decimal point», «Cost basis override: At most 12 digits before the decimal
 * point». The same two halves, reds today: the resolver with the faked catalogue (today the text comes back without its
 * label), and the app's catalogue in English and Italian (today the key is missing, and the backend's English `error`
 * comes back behind the label); the French and Spanish texts of the catalogue too.
 *
 * R13-SEC7-3 (E's R13-SEC7, night decision N74), as D-P4 lot L3 revised it. The batch checks a row's date at write against
 * one bound, `date ≤ tomorrow` (the server's): the floor of 1900-01-01 is gone (the frontend asks one confirmation before
 * a date before 1900 instead), and a date past the ceiling is refused with `{code: 'dateOutOfRange', params: {max},
 * field: 'date'}` (an ISO date; NO `min`). The catalogue text `transactions.errors.dateOutOfRange` is ceiling-only: it
 * uses `{max}` and no `{min}` in any language (`dateOutOfRangeCatalogue.test.ts` reads the four sources), and the code
 * stays in `FIELD_PREFIXED_CODES`: the label of `transactions.fields.date` goes in front (read from the catalogue: EN
 * «Date», IT «Data», FR «Date», ES «Fecha»). The resolver is checked with a faked catalogue (the exact text is the
 * fake's), and against the app's catalogue in every language by what the contract fixes and not by the sentence: the
 * label in front, the ceiling date in the text, and nothing of a floor or of a missing `{min}` (reds today: the text
 * still asks for `{min}`, which the issue no longer carries).
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';
import {init, waitLocale} from 'svelte-i18n';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {resolveIssueMessage, type ResolvableIssue} from './resolveValidationMessage';

/** The translate function the resolver takes: the app passes its own (`$_`, svelte-i18n). */
type Translate = Parameters<typeof resolveIssueMessage>[1];
type Language = 'en' | 'it';
type DecimalCode = 'decimalPlacesExceeded' | 'significantDigitsExceeded';
type DecimalField = 'quantity' | 'cash.amount' | 'cost_basis_override';

const CODES: DecimalCode[] = ['decimalPlacesExceeded', 'significantDigitsExceeded'];
const FIELDS: DecimalField[] = ['quantity', 'cash.amount', 'cost_basis_override'];

/** The `max` the backend sends: 10 decimals for a quantity, 6 for a cash amount, 12 for a per-unit cost basis (D5), 15 digits for any. */
function maxOf(code: DecimalCode, field: DecimalField): number {
    if (code === 'significantDigitsExceeded') return 15;
    if (field === 'quantity') return 10;
    return field === 'cash.amount' ? 6 : 12;
}

/** Every code on every field, with its `max`. */
const CASES = CODES.flatMap((code) => FIELDS.map((field) => ({code, field, max: maxOf(code, field)})));

/** The contract's texts of the two codes, `{max}` filled in. */
const TEXT: Record<Language, Record<DecimalCode, (max: number) => string>> = {
    en: {decimalPlacesExceeded: (max) => `At most ${max} decimal places`, significantDigitsExceeded: (max) => `At most ${max} significant digits`},
    it: {decimalPlacesExceeded: (max) => `Al massimo ${max} decimali`, significantDigitsExceeded: (max) => `Al massimo ${max} cifre significative`},
};

/** The English field labels the contract names. */
const EN_LABEL: Record<DecimalField, string> = {quantity: 'Quantity', 'cash.amount': 'Cash amount', cost_basis_override: 'Cost basis override'};

/** The catalogue key of a field label, as `translateFieldName` reads it: the dots of the field become underscores. */
const labelKey = (field: DecimalField): string => `transactions.fields.${field.replace(/\./g, '_')}`;

/** The issue `check_decimal_limits` writes on a create: its English `error` names the field. */
function decimalIssue(code: DecimalCode, field: DecimalField): ResolvableIssue {
    const max = maxOf(code, field);
    const what = code === 'decimalPlacesExceeded' ? 'decimal places' : 'significant digits';
    return {operation: 'create', code, params: {max}, field, error: `${field} has more than ${max} ${what}`};
}

/** The issue the batch writes on a received TRANSFER created without a cost basis (`batch_costs.py`). */
const COST_BASIS_REQUIRED: ResolvableIssue = {operation: 'create', code: 'costBasisRequired', params: {type: 'TRANSFER'}, field: 'cost_basis_override', error: 'TRANSFER with qty>0 requires cost_basis_override'};

/**
 * A stand-in for svelte-i18n's `$t`, as in `resolveValidationMessage.test.ts`: a missing key resolves to the key itself
 * (the resolver's «not found» signal), a known one fills its `{placeholder}` tokens from `opts.values`.
 */
function makeT(known: Record<string, string>): Translate {
    return (key, opts) => {
        const template = known[key];
        if (template === undefined) return key;
        const values = opts?.values ?? {};
        return template.replace(/\{(\w+)\}/g, (token, name) => (values[name] !== undefined ? String(values[name]) : token));
    };
}

describe('C-97a — the resolver puts the field label in front of the two decimal codes (catalogue faked)', () => {
    const t = makeT({
        'transactions.errors.decimalPlacesExceeded': 'At most {max} decimal places',
        'transactions.errors.significantDigitsExceeded': 'At most {max} significant digits',
        'transactions.errors.costBasisRequired': '{type} with a positive quantity needs a cost basis',
        'transactions.types.TRANSFER': 'Transfer',
        [labelKey('quantity')]: EN_LABEL.quantity,
        [labelKey('cash.amount')]: EN_LABEL['cash.amount'],
        [labelKey('cost_basis_override')]: EN_LABEL.cost_basis_override,
    });

    it.each(CASES)('$code on $field reads «label: text», max $max', ({code, field, max}) => {
        expect(resolveIssueMessage(decimalIssue(code, field), t)).toBe(`${EN_LABEL[field]}: ${TEXT.en[code](max)}`);
    });

    it('guard: costBasisRequired sent with a field keeps its own text, without the label', () => {
        expect(resolveIssueMessage(COST_BASIS_REQUIRED, t)).toBe('Transfer with a positive quantity needs a cost basis');
    });
});

describe('C-97a — the app catalogue: «label: text» in English and in Italian', () => {
    /** Switches the UI language as LanguageSelector does, and answers the app's translate function in it. */
    async function speak(lang: Language): Promise<Translate> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        return get(_);
    }

    beforeAll(async () => {
        init({fallbackLocale: 'en', initialLocale: 'en'});
        await waitLocale('en');
    });

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await speak('en');
    });

    it.each(CASES)('English: $code on $field reads «label: At most $max …»', async ({code, field, max}) => {
        const t = await speak('en');
        expect(t(labelKey(field)), 'control: the catalogue labels the field as the contract names it').toBe(EN_LABEL[field]);

        expect(resolveIssueMessage(decimalIssue(code, field), t)).toBe(`${EN_LABEL[field]}: ${TEXT.en[code](max)}`);
    });

    it.each(CASES)('Italian: $code on $field reads «etichetta: Al massimo $max …»', async ({code, field, max}) => {
        const t = await speak('it');
        const label = t(labelKey(field));
        expect(label, 'control: the field has a label in the catalogue').not.toBe(labelKey(field));
        expect(label, 'control: the language switched, the Italian label is not the English one').not.toBe(EN_LABEL[field]);

        expect(resolveIssueMessage(decimalIssue(code, field), t)).toBe(`${label}: ${TEXT.it[code](max)}`);
    });

    it.each(['en', 'it'] as const)('guard, %s: costBasisRequired keeps the text of the catalogue, without the label', async (lang) => {
        const t = await speak(lang);
        const key = 'transactions.errors.costBasisRequired';
        const type = t('transactions.types.TRANSFER');
        expect(t(key), 'control: the code has a text in the catalogue').not.toBe(key);
        expect(type, 'control: the type has a name in the catalogue').not.toBe('transactions.types.TRANSFER');

        expect(resolveIssueMessage(COST_BASIS_REQUIRED, t)).toBe(t(key, {values: {type}}));
    });
});

// ---------------------------------------------------------------------------------------------------------------------
// R13-SEC2 — integerDigitsExceeded (decision N63: 15 for a quantity and a cash amount, 12 for a per-unit cost basis)
// ---------------------------------------------------------------------------------------------------------------------

type Speech = 'en' | 'it' | 'fr' | 'es';

/** The `max` the backend sends with `integerDigitsExceeded`: `max_integer_digits` of the field's column (N63). */
const INTEGER_MAX: Record<DecimalField, number> = {quantity: 15, 'cash.amount': 15, cost_basis_override: 12};

/** Every field with its integer `max`. */
const INTEGER_CASES = FIELDS.map((field) => ({field, max: INTEGER_MAX[field]}));

/** The contract's texts of `transactions.errors.integerDigitsExceeded`, `{max}` filled in. */
const INTEGER_TEXT: Record<Speech, (max: number) => string> = {
    en: (max) => `At most ${max} digits before the decimal point`,
    it: (max) => `Al massimo ${max} cifre prima della virgola`,
    fr: (max) => `Au maximum ${max} chiffres avant la virgule`,
    es: (max) => `Como máximo ${max} cifras en la parte entera`,
};

/** The C-97a text of `decimalPlacesExceeded` with max 10, per language: proves the language switched (that key exists). */
const DECIMALS_10: Record<Speech, string> = {
    en: 'At most 10 decimal places',
    it: 'Al massimo 10 decimali',
    fr: 'Au maximum 10 décimales',
    es: 'Como máximo 10 decimales',
};

/** The issue `check_decimal_limits` writes past the integer digits: its English `error` names the field, and differs from the catalogue's text. */
function integerIssue(field: DecimalField): ResolvableIssue {
    const max = INTEGER_MAX[field];
    return {operation: 'create', code: 'integerDigitsExceeded', params: {max}, field, error: `${field} has more than ${max} integer digits`};
}

describe('R13-SEC2 — the resolver puts the field label in front of integerDigitsExceeded (catalogue faked)', () => {
    const t = makeT({
        'transactions.errors.integerDigitsExceeded': 'At most {max} digits before the decimal point',
        [labelKey('quantity')]: EN_LABEL.quantity,
        [labelKey('cash.amount')]: EN_LABEL['cash.amount'],
        [labelKey('cost_basis_override')]: EN_LABEL.cost_basis_override,
    });

    // Red today: integerDigitsExceeded is not in FIELD_PREFIXED_CODES, so its text comes back without the label.
    it.each(INTEGER_CASES)('integerDigitsExceeded on $field reads «label: At most $max digits before the decimal point»', ({field, max}) => {
        expect(resolveIssueMessage(integerIssue(field), t)).toBe(`${EN_LABEL[field]}: ${INTEGER_TEXT.en(max)}`);
    });
});

describe('R13-SEC2 — the app catalogue: integerDigitsExceeded reads «label: text» in every language', () => {
    /** Switches the UI language as LanguageSelector does, and answers the app's translate function in it. */
    async function speak(lang: Speech): Promise<Translate> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        return get(_);
    }

    beforeAll(async () => {
        init({fallbackLocale: 'en', initialLocale: 'en'});
        await waitLocale('en');
    });

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await speak('en');
    });

    // Red today: the key is missing, so the backend's English `error` comes back behind the label.
    it.each(INTEGER_CASES)('English: integerDigitsExceeded on $field reads «label: At most $max digits before the decimal point»', async ({field, max}) => {
        const t = await speak('en');
        expect(t(labelKey(field)), 'control: the catalogue labels the field as the contract names it').toBe(EN_LABEL[field]);

        expect(resolveIssueMessage(integerIssue(field), t)).toBe(`${EN_LABEL[field]}: ${INTEGER_TEXT.en(max)}`);
    });

    // Red today: as in English.
    it.each(INTEGER_CASES)('Italian: integerDigitsExceeded on $field reads «etichetta: Al massimo $max cifre prima della virgola»', async ({field, max}) => {
        const t = await speak('it');
        const label = t(labelKey(field));
        expect(label, 'control: the field has a label in the catalogue').not.toBe(labelKey(field));
        expect(label, 'control: the language switched, the Italian label is not the English one').not.toBe(EN_LABEL[field]);

        expect(resolveIssueMessage(integerIssue(field), t)).toBe(`${label}: ${INTEGER_TEXT.it(max)}`);
    });

    // Red today: the key is missing in French and Spanish too.
    it.each(['fr', 'es'] as const)('%s: integerDigitsExceeded reads «label: text» on every field', async (lang) => {
        const t = await speak(lang);
        expect(t('transactions.errors.decimalPlacesExceeded', {values: {max: 10}}), 'control: the language switched (a C-97a text of the catalogue)').toBe(DECIMALS_10[lang]);

        for (const {field, max} of INTEGER_CASES) {
            const label = t(labelKey(field));
            expect(label, `control: ${field} has a label in the catalogue`).not.toBe(labelKey(field));
            expect(resolveIssueMessage(integerIssue(field), t), `${lang}, ${field}`).toBe(`${label}: ${INTEGER_TEXT[lang](max)}`);
        }
    });
});

// ---------------------------------------------------------------------------------------------------------------------
// R13-SEC7-3 — dateOutOfRange (night decision N74, revised by D-P4 lot L3: date ≤ tomorrow, the server's; no floor)
// ---------------------------------------------------------------------------------------------------------------------

/** The ceiling the issue carries, and the first day of the old floor: the text must show the first and never the second. */
const DATE_CEILING = '2026-10-20';
const OLD_FLOOR = '1900-01-01';

/** The issue the batch's date stage writes on a create dated past the ceiling: `params` is `{max}` alone; its English `error` differs from the catalogue's text. */
const DATE_ISSUE: ResolvableIssue = {operation: 'create', code: 'dateOutOfRange', params: {max: DATE_CEILING}, field: 'date', error: `date 2026-10-25 is after ${DATE_CEILING}`};

/** `transactions.fields.date` as the catalogue reads it (`src/lib/i18n/transactions/<lang>.json`), checked by a control in each test. */
const DATE_LABEL: Record<Speech, string> = {en: 'Date', it: 'Data', fr: 'Date', es: 'Fecha'};

describe('R13-SEC7-3 — the resolver puts the field label in front of dateOutOfRange (catalogue faked)', () => {
    const t = makeT({
        'transactions.errors.dateOutOfRange': 'On or before {max}',
        'transactions.fields.date': DATE_LABEL.en,
    });

    // Guard (green today and after): the resolver maps the code with `params: {max}` to the key, label in front. The text is the fake's.
    it('dateOutOfRange on date with params {max} reads «Date: <the key filled with max>»', () => {
        expect(resolveIssueMessage(DATE_ISSUE, t)).toBe(`${DATE_LABEL.en}: On or before ${DATE_CEILING}`);
    });
});

describe('R13-SEC7-3 — the app catalogue: dateOutOfRange reads «label: text» in every language', () => {
    /** Switches the UI language as LanguageSelector does, and answers the app's translate function in it. */
    async function speak(lang: Speech): Promise<Translate> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        return get(_);
    }

    beforeAll(async () => {
        init({fallbackLocale: 'en', initialLocale: 'en'});
        await waitLocale('en');
    });

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await speak('en');
    });

    /** What the contract fixes of the resolved message in `lang`, whatever the sentence: the date label in front, the ceiling date, no floor, no unfilled `{min}`. */
    async function expectCeilingMessage(lang: Speech): Promise<void> {
        const t = await speak(lang);
        expect(t('transactions.errors.decimalPlacesExceeded', {values: {max: 10}}), 'control: the language switched (a C-97a text of the catalogue)').toBe(DECIMALS_10[lang]);
        expect(t('transactions.fields.date'), 'control: the catalogue labels the date field').toBe(DATE_LABEL[lang]);

        const message = resolveIssueMessage(DATE_ISSUE, t);

        expect(message.startsWith(`${DATE_LABEL[lang]}: `), `${lang}: the label of the date field leads the message`).toBe(true);
        expect(message, `${lang}: the text shows the ceiling the issue carries`).toContain(DATE_CEILING);
        expect(message, `${lang}: no trace of the old floor`).not.toContain(OLD_FLOOR);
        expect(message, `${lang}: the text is the catalogue's, not the backend's English fallback`).not.toBe(`${DATE_LABEL[lang]}: ${DATE_ISSUE.error}`);
        expect(message, `${lang}: no placeholder is left unfilled`).not.toMatch(/[{}]/);
    }

    // Red today: the catalogue text asks for `{min}`, which the issue no longer carries, so it cannot be filled.
    it.each(['en', 'it', 'fr', 'es'] as const)('%s: dateOutOfRange reads «label: text» with the ceiling and no floor', async (lang) => {
        await expectCeilingMessage(lang);
    });
});
