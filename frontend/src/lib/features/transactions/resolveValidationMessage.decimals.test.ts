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
