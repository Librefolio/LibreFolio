import {describe, it, expect} from 'vitest';
import type {BrimNotice} from '$lib/types';
import * as resolveBrimNotice from './resolveBrimNotice';
import {resolveBrimNoticeMessage} from './resolveBrimNotice';

/** Fake `$t`: known keys interpolate {tokens} from values; unknown keys echo the key. */
function makeT(known: Record<string, string> = {}) {
    return (key: string, opts?: {values?: Record<string, any>}): string => {
        const tpl = known[key];
        if (tpl === undefined) return key;
        const values = opts?.values ?? {};
        return tpl.replace(/\{(\w+)\}/g, (_m, k) => (values[k] !== undefined ? String(values[k]) : `{${k}}`));
    };
}

const notice = (partial: Partial<BrimNotice>): BrimNotice => ({code: null, message: '', context: null, ...partial}) as unknown as BrimNotice;

describe('resolveBrimNoticeMessage', () => {
    it('returns the plugin message verbatim when the notice has no code', () => {
        const t = makeT({'importWizard.brimNotice.X': 'never used'});
        expect(resolveBrimNoticeMessage(notice({message: 'raw plugin text'}), t)).toBe('raw plugin text');
    });

    it('translates a known code and interpolates its context', () => {
        const t = makeT({'importWizard.brimNotice.SKIPPED': 'Skipped {n} rows'});
        const msg = resolveBrimNoticeMessage(notice({code: 'SKIPPED', message: 'fallback', context: {n: 3}}), t);
        expect(msg).toBe('Skipped 3 rows');
    });

    it('aliases row_count into the conventional {n} placeholder', () => {
        const t = makeT({'importWizard.brimNotice.SKIPPED': 'Skipped {n} rows'});
        const msg = resolveBrimNoticeMessage(notice({code: 'SKIPPED', message: 'fallback', context: {row_count: 7}}), t);
        expect(msg).toBe('Skipped 7 rows');
    });

    it('does not override an explicit {n} with row_count', () => {
        const t = makeT({'importWizard.brimNotice.SKIPPED': '{n}'});
        const msg = resolveBrimNoticeMessage(notice({code: 'SKIPPED', message: 'fallback', context: {n: 1, row_count: 99}}), t);
        expect(msg).toBe('1');
    });

    it('ignores a non-numeric row_count', () => {
        const t = makeT({'importWizard.brimNotice.SKIPPED': 'n={n}'});
        const msg = resolveBrimNoticeMessage(notice({code: 'SKIPPED', message: 'fallback', context: {row_count: 'many'}}), t);
        // row_count is not a number → {n} stays unresolved
        expect(msg).toBe('n={n}');
    });

    it('falls back to the plugin message when the code has no translation key', () => {
        const t = makeT();
        expect(resolveBrimNoticeMessage(notice({code: 'UNKNOWN_CODE', message: 'plugin default'}), t)).toBe('plugin default');
    });

    it('tolerates a null context bag', () => {
        const t = makeT({'importWizard.brimNotice.OK': 'all good'});
        expect(resolveBrimNoticeMessage(notice({code: 'OK', message: 'fallback', context: null}), t)).toBe('all good');
    });
});

/**
 * ─── resolveBrimTodoMessage: the wording of a BRIM field todo ───────────────────────────────────
 *
 * A field todo (`BRIMFieldTodo`, an `ImportTodo` once in the editor) carries the same pair as a
 * notice: a stable `reason_code` and the plugin's own `message`, written in the language of the
 * parsed file, plus a `context` of i18n params. Decision A of the i18n audit (S18-S19, 08/10/2026):
 * one rule for the todos, with the notices' contract —
 *   - key    `importWizard.brimNotice.<reasonCode>`
 *   - values `todo.context`
 *   - miss, or an empty code → the plugin's own `message`, never the raw key.
 * The bulk editor's three surfaces and ParseDetailModal read it. Written red first, against a module
 * that does not export it yet.
 */

/** The todo fields the rule reads, as decision A names them: declared here, so the cases compile before the export exists. */
type BrimTodoLike = {reasonCode: string; message: string; context?: Record<string, unknown> | null};
type TranslateFn = ReturnType<typeof makeT>;

/**
 * `resolveBrimTodoMessage`, called through the module. Until the export exists every case below fails
 * here, on the assertion that names what is missing, rather than on a `TypeError` thrown before any
 * assertion ran — and the notice cases above keep running.
 */
function resolveBrimTodoMessage(todo: BrimTodoLike, t: TranslateFn): string {
    const rule = (resolveBrimNotice as unknown as Record<string, unknown>).resolveBrimTodoMessage;
    expect(typeof rule, 'resolveBrimNotice exports no resolveBrimTodoMessage(): a field todo has no rule from its reason code to a wording').toBe('function');
    return (rule as (todo: BrimTodoLike, t: TranslateFn) => string)(todo, t);
}

/** `makeT`, also recording every lookup: the key, and the values it came with. */
function recordingT(known: Record<string, string> = {}) {
    const asked: Array<{key: string; values?: Record<string, any>}> = [];
    const translate = makeT(known);
    const t: TranslateFn = (key, opts) => {
        asked.push({key, values: opts?.values});
        return translate(key, opts);
    };
    return {t, asked};
}

describe('resolveBrimTodoMessage — the wording of a BRIM field todo', () => {
    it('translates a reason code that has a key, interpolating its context', () => {
        const t = makeT({'importWizard.brimNotice.probe_worded': 'Enter the cost of {ticker} on row {row}'});
        const todo = {reasonCode: 'probe_worded', message: 'Messaggio del plugin, nella lingua del file', context: {ticker: 'ACME', row: 7}};
        expect(resolveBrimTodoMessage(todo, t)).toBe('Enter the cost of ACME on row 7');
    });

    it('translates a key without placeholders for a todo with no context, absent or null — corporate_action as the generic CSV emits it', () => {
        const t = makeT({'importWizard.brimNotice.corporate_action': 'Catalogue wording, in the UI language'});
        const plugin = 'Missing inherited per-unit cost basis (WAC). Enter the cost per single unit (not the total) to import.';
        expect(resolveBrimTodoMessage({reasonCode: 'corporate_action', message: plugin}, t)).toBe('Catalogue wording, in the UI language');
        expect(resolveBrimTodoMessage({reasonCode: 'corporate_action', message: plugin, context: null}, t)).toBe('Catalogue wording, in the UI language');
    });

    it("keeps the plugin's message, in the language of the file, when the code has no key — never the raw key", () => {
        const t = makeT({'importWizard.brimNotice.another_code': 'never used'});
        const todo = {reasonCode: 'degiro_probe_unworded', message: 'Bericht van de plugin, in de taal van het bestand', context: {n: 2}};
        expect(resolveBrimTodoMessage(todo, t), "the plugin's message, never importWizard.brimNotice.degiro_probe_unworded").toBe('Bericht van de plugin, in de taal van het bestand');
    });

    it("keeps the plugin's message for an empty reason code, never the entry of the bare namespace", () => {
        const t = makeT({'importWizard.brimNotice.': 'never used'});
        expect(resolveBrimTodoMessage({reasonCode: '', message: 'raw plugin text'}, t)).toBe('raw plugin text');
    });

    it('looks the code up at importWizard.brimNotice.<reasonCode>, with the context as its values', () => {
        const context = {old_ticker: 'CCIV', new_ticker: 'LCID'};
        // The gap-fix todos are worded at another key (importWizard.reportSet.gapFix.todo.<code>) before they reach the editor.
        const {t, asked} = recordingT({'importWizard.reportSet.gapFix.todo.probe_namespace': 'the gap-fix namespace', 'importWizard.brimNotice.probe_namespace': 'the notices namespace'});
        expect(resolveBrimTodoMessage({reasonCode: 'probe_namespace', message: 'plugin wording', context}, t)).toBe('the notices namespace');
        const lookup = asked.find((call) => call.key === 'importWizard.brimNotice.probe_namespace');
        expect(lookup, `the keys looked up: ${JSON.stringify(asked.map((call) => call.key))}`).toBeDefined();
        expect(lookup?.values, 'the context reaches the lookup as its values').toEqual(expect.objectContaining(context));
    });
});
