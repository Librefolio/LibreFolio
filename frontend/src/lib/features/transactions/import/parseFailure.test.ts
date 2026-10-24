/**
 * parseFailure — what the import wizard shows when the server refuses a parse or a preview, in the UI language
 * (workstream W, wave 5, lot W5-5 — backlog C-70b; Vitest, node, pure).
 *
 * Until now the API answered a failed parse with `400 {detail: "Parse error: …"}` (or the parse guard's sentence), and the
 * wizard showed that English to every user. Now the `detail` is an object the wizard translates:
 *
 *   - `{code: 'parse_failed', message, plugin_code, plugin_name, reason: {code, message, context}}` — the parse failed, in
 *     the plugin's own code (`BRIMParseError`) or at the parse guard (`BRIMRefusal`). The frame is
 *     `importWizard.parseFailed` with `{plugin_name, reason}`; the plugin is named as the plugin select names it
 *     (`brimPluginName`: `brimPlugins.<code>.name`, else the API's `plugin_name`, else the code) and the reason is what the
 *     refusal resolver shows (`importWizard.parseRefusal.<code>` with the context, else the plugin's English sentence made a
 *     sentence). A failure with no reason at all — no code and an empty message — is one sentence of its own,
 *     `importWizard.parseFailedNoReason`, not the frame around nothing.
 *   - `{code: 'preview_unsupported' | 'preview_unreadable', message}` — a file preview failed:
 *     `importWizard.previewFailed.<code>`, or the English `message` when the catalogue has no such key.
 *   - anything else — a string `detail`, a validation array, a network error — is `extractErrorMessage(error, …)`, as before.
 *
 * `resolveParseFailureMessage(error, t)` is the pure helper that makes that choice, in `parseFailure.ts` beside
 * `defaultPluginCheck.ts`. Each branch is tested through a fake `t` that answers only the keys a test teaches it (an
 * unknown key comes back as itself, as svelte-i18n answers a missing key), so the lookups are asserted by key and by values,
 * never by catalogue wording. The last block is a plain test of the four source catalogues: the four keys the helper reads
 * exist in English, Italian, French and Spanish, and the frame carries both placeholders. Red until `parseFailure.ts` exists
 * (the file fails on its import) and until the keys are in the four catalogues.
 */

import {describe, expect, it, vi} from 'vitest';
import {extractErrorMessage} from '$lib/utils/trySave';
import en from '$lib/i18n/importWizard/en.json';
import it_ from '$lib/i18n/importWizard/it.json';
import fr from '$lib/i18n/importWizard/fr.json';
import es from '$lib/i18n/importWizard/es.json';
import {resolveGapFixFailureMessage, resolveParseFailureMessage} from './parseFailure';

/** Fake `$t`: a known key interpolates `{token}`s from its values; an unknown key comes back as itself, as svelte-i18n answers a missing key. */
function makeT(known: Record<string, string> = {}) {
    return vi.fn((key: string, opts?: {values?: Record<string, unknown>}): string => {
        const template = known[key];
        if (template === undefined) return key;
        const values = opts?.values ?? {};
        return template.replace(/\{(\w+)\}/g, (token, name: string) => (values[name] !== undefined ? String(values[name]) : token));
    });
}

/** The error axios throws for an HTTP failure: the API's body under `response.data`. */
function apiError(detail: unknown, status = 400): unknown {
    return Object.assign(new Error(`Request failed with status code ${status}`), {response: {status, statusText: 'Bad Request', data: {detail}}});
}

const FRAME_KEY = 'importWizard.parseFailed';
const NO_REASON_KEY = 'importWizard.parseFailedNoReason';
const FRAME_TEMPLATE = 'The {plugin_name} plugin failed: {reason}';
const NO_REASON_TEMPLATE = 'The file could not be read, and the plugin gave no reason.';

/** A `parse_failed` detail as the API builds it (lot W5-5): the parts a test changes are the arguments. */
function parseFailed(reason: {code: string | null; message: string | null; context?: Record<string, unknown>}, plugin: {plugin_code?: string; plugin_name?: string | null} = {}) {
    return {
        code: 'parse_failed',
        message: "Plugin 'Owned Parser' cannot parse file 'a.csv': the English diagnostic text",
        plugin_code: plugin.plugin_code ?? 'owned_parser',
        plugin_name: plugin.plugin_name === undefined ? 'Owned Parser' : plugin.plugin_name,
        reason: {code: reason.code, message: reason.message, context: reason.context ?? {}},
    };
}

describe('resolveParseFailureMessage — a parse that failed (parse_failed)', () => {
    it('is the importWizard.parseFailed frame, the plugin named by its catalogue name and the reason by its refusal key with the context', () => {
        const t = makeT({
            [FRAME_KEY]: FRAME_TEMPLATE,
            'brimPlugins.owned_parser.name': 'Localised Parser',
            'importWizard.parseRefusal.missing_columns': 'Columns {columns} are missing ({count}).',
        });
        const error = apiError(parseFailed({code: 'missing_columns', message: "required column 'date' not found in the CSV header", context: {columns: 'date', count: 1}}));

        expect(resolveParseFailureMessage(error, t)).toBe('The Localised Parser plugin failed: Columns date are missing (1).');

        expect(t).toHaveBeenCalledWith(FRAME_KEY, {values: {plugin_name: 'Localised Parser', reason: 'Columns date are missing (1).'}});
        expect(t).toHaveBeenCalledWith('importWizard.parseRefusal.missing_columns', {values: {columns: 'date', count: 1}});
    });

    it("names the plugin by the API's plugin_name when the catalogue has no name for its code, and by the code when there is no name either", () => {
        const known = {[FRAME_KEY]: FRAME_TEMPLATE, 'importWizard.parseRefusal.some_code': 'a coded reason'};

        expect(resolveParseFailureMessage(apiError(parseFailed({code: 'some_code', message: 'x'}, {plugin_name: 'Name From The API'})), makeT(known))).toBe('The Name From The API plugin failed: a coded reason');
        expect(resolveParseFailureMessage(apiError(parseFailed({code: 'some_code', message: 'x'}, {plugin_code: 'broker_unnamed', plugin_name: null})), makeT(known))).toBe('The broker_unnamed plugin failed: a coded reason');
    });

    it("shows the plugin's English sentence as a sentence when the reason has a code the catalogue does not know", () => {
        const t = makeT({[FRAME_KEY]: FRAME_TEMPLATE});

        const message = resolveParseFailureMessage(apiError(parseFailed({code: 'unknown_code', message: "required column 'date' not found in the CSV header"})), t);

        expect(message).toBe("The Owned Parser plugin failed: Required column 'date' not found in the CSV header.");
        expect(t, 'the lookup of the refusal is by key, with the context').toHaveBeenCalledWith('importWizard.parseRefusal.unknown_code', {values: {}});
    });

    it("shows the plugin's English sentence as a sentence when the reason has no code (a BRIMParseError that gave none)", () => {
        const t = makeT({[FRAME_KEY]: FRAME_TEMPLATE});

        expect(resolveParseFailureMessage(apiError(parseFailed({code: null, message: 'Directa header row not found'})), t)).toBe('The Owned Parser plugin failed: Directa header row not found.');
        expect(t, 'no code, no refusal lookup').not.toHaveBeenCalledWith(expect.stringContaining('importWizard.parseRefusal.'), expect.anything());
    });

    it("names a plugin that the reason's context gives by plugin_code in the UI language (the refusal resolver's own rule)", () => {
        const t = makeT({
            [FRAME_KEY]: FRAME_TEMPLATE,
            'importWizard.parseRefusal.csv_only': 'The {plugin_name} plugin reads only .csv files.',
            'brimPlugins.broker_generic_csv.name': 'Generic CSV (localised)',
        });
        const error = apiError(parseFailed({code: 'csv_only', message: 'the Generic CSV reads only .csv files', context: {plugin_code: 'broker_generic_csv'}}, {plugin_code: 'broker_generic_csv', plugin_name: 'Generic CSV'}));

        expect(resolveParseFailureMessage(error, t)).toBe('The Generic CSV (localised) plugin failed: The Generic CSV (localised) plugin reads only .csv files.');
    });

    it('is importWizard.parseFailedNoReason on its own when the reason has no code and no message, never the frame around nothing', () => {
        for (const message of ['', null, '   ']) {
            const t = makeT({[FRAME_KEY]: FRAME_TEMPLATE, [NO_REASON_KEY]: NO_REASON_TEMPLATE});

            const shown = resolveParseFailureMessage(apiError(parseFailed({code: null, message})), t);

            expect(shown, `message ${JSON.stringify(message)}`).toBe(NO_REASON_TEMPLATE);
            expect(t).toHaveBeenCalledWith(NO_REASON_KEY, expect.anything());
            expect(t, 'the frame is not used').not.toHaveBeenCalledWith(FRAME_KEY, expect.anything());
        }
    });

    it('keeps the frame when the message is empty but the code has a translation: the code is a reason', () => {
        const t = makeT({[FRAME_KEY]: FRAME_TEMPLATE, [NO_REASON_KEY]: NO_REASON_TEMPLATE, 'importWizard.parseRefusal.no_header_row': 'The file has no header row.'});

        expect(resolveParseFailureMessage(apiError(parseFailed({code: 'no_header_row', message: ''})), t)).toBe('The Owned Parser plugin failed: The file has no header row.');
    });

    it('does not show the English diagnostic message of the object when it can translate', () => {
        const t = makeT({[FRAME_KEY]: FRAME_TEMPLATE, 'importWizard.parseRefusal.some_code': 'translated'});
        const detail = parseFailed({code: 'some_code', message: 'english reason'});

        expect(resolveParseFailureMessage(apiError(detail), t)).not.toContain(detail.message);
    });
});

describe('resolveParseFailureMessage — a preview that failed', () => {
    it.each(['preview_unsupported', 'preview_unreadable'])('%s is importWizard.previewFailed.<code>', (code) => {
        const t = makeT({[`importWizard.previewFailed.${code}`]: `translated ${code}`});

        expect(resolveParseFailureMessage(apiError({code, message: 'English text of the API'}), t)).toBe(`translated ${code}`);
        expect(t).toHaveBeenCalledWith(`importWizard.previewFailed.${code}`, expect.anything());
    });

    it.each(['preview_unsupported', 'preview_unreadable'])('%s falls back to the English message of the detail when the catalogue has no such key', (code) => {
        const t = makeT();

        expect(resolveParseFailureMessage(apiError({code, message: 'English text of the API'}), t)).toBe('English text of the API');
    });
});

describe('resolveParseFailureMessage — any other error is extractErrorMessage, as before', () => {
    const t = makeT({[FRAME_KEY]: FRAME_TEMPLATE, [NO_REASON_KEY]: NO_REASON_TEMPLATE});

    it('returns a string detail as it is (an unknown plugin: 400, "Plugin not found: …")', () => {
        const error = apiError('Plugin not found: broker_nobody');

        expect(resolveParseFailureMessage(error, t)).toBe('Plugin not found: broker_nobody');
        expect(resolveParseFailureMessage(error, t)).toBe(extractErrorMessage(error));
    });

    it.each([
        ['an object detail of another code, with a message', apiError({code: 'something_else', message: 'Something else happened'})],
        ['a validation array', apiError([{loc: ['body', 'plugin_code'], msg: 'field required', type: 'value_error.missing'}], 422)],
        ['a 404 string', apiError('File not found', 404)],
        ['a plain Error (no response: the network)', new Error('Network Error')],
        ['an HTTP failure with no detail', Object.assign(new Error('boom'), {response: {status: 502, statusText: 'Bad Gateway', data: {}}})],
    ])('%s is exactly extractErrorMessage(error)', (_label, error) => {
        expect(resolveParseFailureMessage(error, t)).toBe(extractErrorMessage(error));
    });

    it('never asks the catalogue for a frame it does not use', () => {
        const probe = makeT();

        resolveParseFailureMessage(apiError('Plugin not found: broker_nobody'), probe);

        expect(probe).not.toHaveBeenCalledWith(FRAME_KEY, expect.anything());
        expect(probe).not.toHaveBeenCalledWith(NO_REASON_KEY, expect.anything());
    });
});

describe('importWizard catalogues — the keys the failure message reads, in the four languages', () => {
    const catalogues = {en, it: it_, fr, es} as Record<string, {importWizard: Record<string, any>}>;

    it.each(Object.keys(catalogues))('%s has parseFailed with both placeholders, and the three other texts', (language) => {
        const wizard = catalogues[language].importWizard;

        expect(typeof wizard.parseFailed, `${language}: importWizard.parseFailed`).toBe('string');
        expect(wizard.parseFailed, `${language}: the plugin's name goes in the frame`).toContain('{plugin_name}');
        expect(wizard.parseFailed, `${language}: the reason goes in the frame`).toContain('{reason}');
        for (const [label, text] of [
            ['parseFailedNoReason', wizard.parseFailedNoReason],
            ['previewFailed.preview_unsupported', wizard.previewFailed?.preview_unsupported],
            ['previewFailed.preview_unreadable', wizard.previewFailed?.preview_unreadable],
        ] as const) {
            expect(typeof text, `${language}: importWizard.${label}`).toBe('string');
            expect((text as string).trim(), `${language}: importWizard.${label} is not empty`).not.toBe('');
        }
    });

    it('keeps the two preview texts apart in every language: unsupported is not unreadable', () => {
        for (const [language, {importWizard: wizard}] of Object.entries(catalogues)) {
            expect(wizard.previewFailed?.preview_unsupported, language).not.toBe(wizard.previewFailed?.preview_unreadable);
        }
    });
});

/*
 * resolveGapFixFailureMessage — the gap-fix's own 409 (lot W5-6, E-21 / W-B80). `POST /gap-fix` refuses a broker whose
 * ledger it cannot read with `409 {detail: {code: 'ledger_unreadable', message, reason, params}}`: `message` is the English
 * sentence, `reason` says which refusal it is (`currency_codes`: codes that are not ISO 4217, params `{codes, more}`;
 * `values`: values that are not a number, params `{count}`) and `params` fill the translation
 * `importWizard.reportSet.gapFix.ledgerUnreadable.<reason>`. The helper lives in `parseFailure.ts` beside
 * `resolveParseFailureMessage`; red until it is exported (every call is "not a function").
 */

const LEDGER_KEY_PREFIX = 'importWizard.reportSet.gapFix.ledgerUnreadable';
const LEDGER_ENGLISH = "LibreFolio's balances of this broker cannot be compared with the bank: its transactions hold currency codes that are not ISO 4217 codes: 'EURO' (EUR). Correct them first.";

function ledgerUnreadable(reason: unknown, params: unknown, message: unknown = LEDGER_ENGLISH): unknown {
    return apiError({code: 'ledger_unreadable', message, reason, params}, 409);
}

describe('resolveGapFixFailureMessage — the 409 ledger_unreadable of the gap-fix', () => {
    it('currency_codes: the translation of importWizard.reportSet.gapFix.ledgerUnreadable.currency_codes, the params as its values', () => {
        const params = {codes: "'EURO' (EUR)", more: 0};
        const t = makeT({[`${LEDGER_KEY_PREFIX}.currency_codes`]: 'Currency codes to correct first: {codes} (+{more}).'});

        expect(resolveGapFixFailureMessage(ledgerUnreadable('currency_codes', params), t)).toBe("Currency codes to correct first: 'EURO' (EUR) (+0).");

        expect(t).toHaveBeenCalledWith(`${LEDGER_KEY_PREFIX}.currency_codes`, {values: params});
    });

    it('values: the translation of importWizard.reportSet.gapFix.ledgerUnreadable.values, with the count', () => {
        const params = {count: 3};
        const t = makeT({[`${LEDGER_KEY_PREFIX}.values`]: '{count} transactions hold a value that is not a number.'});

        expect(resolveGapFixFailureMessage(ledgerUnreadable('values', params), t)).toBe('3 transactions hold a value that is not a number.');

        expect(t).toHaveBeenCalledWith(`${LEDGER_KEY_PREFIX}.values`, {values: params});
    });

    it.each([
        ['currency_codes', {codes: "'EURO' (EUR)", more: 0}],
        ['values', {count: 3}],
        ['a reason this build does not know', {anything: 1}],
    ])('%s: no translation in the catalogue gives the English message of the API, never the key', (reason, params) => {
        const t = makeT();
        const knownReason = reason === 'a reason this build does not know' ? 'something_new' : reason;

        const shown = resolveGapFixFailureMessage(ledgerUnreadable(knownReason, params), t);

        expect(shown).toBe(LEDGER_ENGLISH);
        expect(shown).not.toContain(LEDGER_KEY_PREFIX);
    });

    it.each([
        ['no reason', undefined],
        ['a reason that is not text', 42],
    ])('%s: the English message of the API, without asking the catalogue for a key built from nothing', (_label, reason) => {
        const t = makeT();

        expect(resolveGapFixFailureMessage(ledgerUnreadable(reason, {count: 1}), t)).toBe(LEDGER_ENGLISH);

        expect(t).not.toHaveBeenCalledWith(expect.stringContaining('undefined'), expect.anything());
    });

    it('params the API left out are handed on as an empty object, not as undefined', () => {
        const t = makeT({[`${LEDGER_KEY_PREFIX}.values`]: 'values {count}'});

        resolveGapFixFailureMessage(ledgerUnreadable('values', undefined), t);

        expect(t).toHaveBeenCalledWith(`${LEDGER_KEY_PREFIX}.values`, {values: {}});
    });
});

describe('resolveGapFixFailureMessage — any other error is extractErrorMessage, as before', () => {
    const t = makeT({[`${LEDGER_KEY_PREFIX}.values`]: 'translated', [`${LEDGER_KEY_PREFIX}.currency_codes`]: 'translated'});

    it.each([
        ['another 409 code of the set', apiError({code: 'set_incomplete', message: 'The set is incomplete', reason: 'values', params: {count: 1}}, 409)],
        ['a string detail', apiError('Plugin not found: broker_nobody', 404)],
        ['a validation array', apiError([{loc: ['body', 'broker_id'], msg: 'field required', type: 'missing'}], 422)],
        ['a network error', new Error('Network Error')],
        ['not an error at all', 'boom'],
        ['null', null],
        ['an HTTP failure with no detail', Object.assign(new Error('boom'), {response: {status: 502, statusText: 'Bad Gateway', data: {}}})],
    ])('%s is exactly extractErrorMessage(error)', (_label, error) => {
        expect(resolveGapFixFailureMessage(error, t)).toBe(extractErrorMessage(error));
    });

    it('hands the fallback on to extractErrorMessage', () => {
        const error = new Error('Network Error');

        expect(resolveGapFixFailureMessage(error, t, 'The gap-fix failed')).toBe(extractErrorMessage(error, 'The gap-fix failed'));
    });

    it("a parse_failed detail is not this helper's business: extractErrorMessage, with no frame asked of the catalogue", () => {
        const probe = makeT();
        const error = apiError(parseFailed({code: 'missing_columns', message: 'x'}));

        expect(resolveGapFixFailureMessage(error, probe)).toBe(extractErrorMessage(error));
        expect(probe).not.toHaveBeenCalledWith(FRAME_KEY, expect.anything());
    });
});

describe('importWizard catalogues — the gap-fix ledgerUnreadable texts, in the four languages', () => {
    const catalogues = {en, it: it_, fr, es} as Record<string, {importWizard: Record<string, any>}>;
    //: The placeholder names each reason's texts must carry (the keys of `params`).
    const PLACEHOLDERS: Record<string, string[]> = {currency_codes: ['codes', 'more'], values: ['count']};

    it.each(Object.keys(catalogues))('%s has a non-empty text for each reason, with the placeholders of its params', (language) => {
        const texts = catalogues[language].importWizard.reportSet?.gapFix?.ledgerUnreadable;

        for (const [reason, names] of Object.entries(PLACEHOLDERS)) {
            const text = texts?.[reason];
            expect(typeof text, `${language}: importWizard.reportSet.gapFix.ledgerUnreadable.${reason}`).toBe('string');
            expect((text as string).trim(), `${language}: ${reason} is not empty`).not.toBe('');
            for (const name of names) {
                expect(text as string, `${language}: ${reason} uses {${name}}`).toMatch(new RegExp(`\\{${name}[,}]`));
            }
        }
    });
});
