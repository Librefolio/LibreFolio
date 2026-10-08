// @vitest-environment jsdom
/**
 * RiskResultFrame — component test (Vitest + jsdom).
 *
 * The frame is the legacy card `RiskAnalysisPanel` mounts once per analytic on
 * the Asset Detail page. It used to word each warning by its *code* —
 * `$t('risk.warnings.<code>')`, called **without values** — and that goes wrong
 * in two ways, each pinned below:
 *
 *   1. **Raw ICU on screen.** svelte-i18n returns the message source untouched
 *      when it is given no values (`if (!values) return message`), so a key whose
 *      name equals the warning code *and* whose sentence has arguments printed
 *      its braces: `hypothetical_metadata_other_fallback` rendered
 *      `{names}: {dimension, select, …}`.
 *   2. **The generic sentence instead of the real one.** A code with no
 *      code-equal key — `assets_excluded`, whose keys are
 *      `assets_excluded_<reason>` — fell back to `risk.states.warning`, although
 *      the backend had sent the exact key and the names it needs.
 *
 * The contract the frame follows now: each warning reads
 * `warningSentence(warning, $t)` — its own `message_i18n_key` formatted with its
 * `message_params`, else the backend `message` — and only an empty answer falls
 * back to the generic sentence. Errors keep their code-based wording, pinned
 * unchanged near the bottom; the last block pins the one refinement D379 adds to
 * it — a `resource_limit` refusal worded by the remedy its details name. Beyond
 * the named cases, one property runs over the
 * whole catalogue: every `risk.warnings` sentence with arguments is worded through
 * its key once its values arrive, and shows the backend sentence when they do not —
 * never a brace, never a key. The list and the values come from
 * `$test/riskWarningCatalogue`, read off `en.json` at test time.
 *
 * **How a sentence is asserted without writing one down.** Expected sentences
 * are resolved from the shipped catalogue through the same `$_` formatter the
 * component uses, with the same values (the pattern of `L4Replay.test.ts`), so no
 * English is pinned here. The harness case guards the ways that could go vacuous:
 * a key missing from the catalogue (svelte-i18n echoes the id back, and so would
 * the component), and outcomes that happen to read alike (the formatted, the
 * backend and the generic sentence must all differ, or "which branch rendered"
 * has no answer).
 *
 * Left elsewhere: the helper's own rules (a missing value, no translator, a blank
 * sentence) in `levels/levelHelpers.test.ts`; the page itself in the Playwright
 * net `portfolio/risk-asset-detail.spec.ts`.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';

import {render, screen, setupI18n} from '$test/component';
import {CODE_EQUAL_ICU_WARNING_KEYS, icuWarningKeys, plausibleParams, type WarningParams} from '$test/riskWarningCatalogue';
import {_} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import RiskResultFrame from './RiskResultFrame.svelte';

type Warning = NonNullable<RiskAnalyticResult['warnings']>[number];

const TEST_ID = 'risk-stress-section';
const GENERIC_KEY = 'risk.states.warning';

const FALLBACK_KEY = 'risk.warnings.hypothetical_metadata_other_fallback';
const FALLBACK_PARAMS: WarningParams = {names: 'Synthetic Holding A', dimension: 'sector', count: 1};
const FALLBACK_MESSAGE = 'Sector or geography metadata was unavailable; the asset was treated as Other at 100%.';

const EXCLUDED_KEY = 'risk.warnings.assets_excluded_missing_price';
const EXCLUDED_PARAMS: WarningParams = {count: 2, names: 'Synthetic Holding B, Synthetic Holding C'};
const EXCLUDED_MESSAGE = 'One or more scope assets were excluded from risk calculations.';

const MOSTLY_EXCLUDED_KEY = 'risk.warnings.historical_replay_mostly_excluded';
const MOSTLY_EXCLUDED_PARAMS: WarningParams = {covered: 0.37};
const MOSTLY_EXCLUDED_MESSAGE = 'Historical replay describes only 37% of the portfolio: the rest is excluded.';

const UNKEYED_MESSAGE = 'A synthetic notice the backend sent without a key.';

/** A key no catalogue ships: svelte-i18n answers it with the id itself. */
const ABSENT_KEY = 'risk.warnings.synthetic_key_added_after_this_build';
const ABSENT_KEY_MESSAGE = 'A synthetic notice whose key this build does not ship.';

/** One warning of each kind the frame has to word. */
const WARNING = {
    /** Code-equal key with ICU arguments: the raw-ICU case. */
    fallback: {code: 'hypothetical_metadata_other_fallback', message: FALLBACK_MESSAGE, degrades_result: false, message_i18n_key: FALLBACK_KEY, message_params: FALLBACK_PARAMS},
    /** No code-equal key: the reason lives in the key alone. The generic-sentence case. */
    excluded: {code: 'assets_excluded', message: EXCLUDED_MESSAGE, message_i18n_key: EXCLUDED_KEY, message_params: EXCLUDED_PARAMS},
    /** Code-equal key whose argument is formatted as a number (`{covered, number, percent}`). */
    mostlyExcluded: {code: 'historical_replay_mostly_excluded', message: MOSTLY_EXCLUDED_MESSAGE, message_i18n_key: MOSTLY_EXCLUDED_KEY, message_params: MOSTLY_EXCLUDED_PARAMS},
    unkeyed: {code: 'synthetic_unkeyed_notice', message: UNKEYED_MESSAGE},
    absentKey: {code: 'synthetic_code_added_later', message: ABSENT_KEY_MESSAGE, message_i18n_key: ABSENT_KEY, message_params: {names: 'Synthetic Holding D', count: 1}},
    /** Neither a key nor a readable sentence: the only case left for the generic one. */
    blank: {code: 'synthetic_blank_notice', message: '   '},
} satisfies Record<string, Warning>;

function stressResult(warnings: Warning[]): RiskAnalyticResult {
    return {
        instance_id: 'single-stress',
        analytic_code: 'stress',
        status: 'partial',
        output: {kind: 'stress', method: 'hypothetical', dimension: 'sector', portfolio_return: -0.05, impacts: []},
        warnings,
    };
}

/** Whitespace around a line comes from the template, not from the message. */
function normalize(text: string): string {
    return text.replace(/\s+/g, ' ').trim();
}

/** A catalogue sentence formatted as the component formats it: `$_`, with the warning's values. */
function resolve(key: string, values?: WarningParams): string {
    return normalize(get(_)(key, values === undefined ? undefined : {values}));
}

/** The catalogue leaf behind a dotted key, read from `en.json` on disk. */
function enLeaf(key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), en);
}

function renderFrame(result: RiskAnalyticResult): void {
    render(RiskResultFrame, {props: {title: 'Synthetic frame title', testId: TEST_ID, result}});
}

/**
 * The rendered warning lines, one per warning.
 *
 * The line count is a barrier, and not a count this file borrowed: the fixture
 * is the whole collection. Without it a frame that rendered no line — or one
 * line for everything — would fail, or pass, for a reason that has nothing to do
 * with the wording. The partial badge proves the result was taken at all.
 */
function warningLines(expected: number): string[] {
    expect(screen.getByTestId(`${TEST_ID}-partial`), 'the frame did not take the result as partial: it may not have rendered it at all').toBeVisible();
    const lines = Array.from(screen.getByTestId(`${TEST_ID}-warnings`).children, (line) => normalize(line.textContent ?? ''));
    expect(lines, 'the frame did not render one line per warning').toHaveLength(expected);
    return lines;
}

beforeAll(async () => {
    await setupI18n();
});

describe('RiskResultFrame — the harness itself', () => {
    it('resolves every keyed sentence, and no two outcomes read alike', () => {
        expect(typeof enLeaf(GENERIC_KEY), `${GENERIC_KEY} is missing from en.json`).toBe('string');
        const generic = resolve(GENERIC_KEY);
        expect(generic, `${GENERIC_KEY} does not resolve: the catalogue is not loaded`).not.toBe(GENERIC_KEY);

        for (const {key, values, message, carries} of [
            {key: FALLBACK_KEY, values: FALLBACK_PARAMS, message: FALLBACK_MESSAGE, carries: String(FALLBACK_PARAMS.names)},
            {key: EXCLUDED_KEY, values: EXCLUDED_PARAMS, message: EXCLUDED_MESSAGE, carries: String(EXCLUDED_PARAMS.names)},
            {key: MOSTLY_EXCLUDED_KEY, values: MOSTLY_EXCLUDED_PARAMS, message: MOSTLY_EXCLUDED_MESSAGE, carries: '37'},
        ]) {
            expect(typeof enLeaf(key), `${key} is missing from en.json`).toBe('string');
            const sentence = resolve(key, values);
            expect(sentence, `${key} does not resolve through svelte-i18n`).not.toBe(key);
            expect(sentence, `${key} still carries ICU braces once formatted with its values`).not.toContain('{');
            expect(sentence, `${key} does not show "${carries}": its values never reached the formatter`).toContain(carries);
            expect(sentence, `${key} formats to the backend sentence: the rendered branch could not be told`).not.toBe(message);
            expect(sentence, `${key} formats to the generic sentence: the rendered branch could not be told`).not.toBe(generic);
        }

        // Defect 1's premise: called without values, the raw source comes back.
        for (const key of [FALLBACK_KEY, MOSTLY_EXCLUDED_KEY]) {
            expect(get(_)(key), `svelte-i18n now formats ${key} called without values: the raw-ICU case pinned here could not occur`).toContain('{');
        }
        expect(get(_)(ABSENT_KEY), `${ABSENT_KEY} exists after all: its fallback case would not be exercised`).toBe(ABSENT_KEY);
        for (const message of [UNKEYED_MESSAGE, ABSENT_KEY_MESSAGE]) {
            expect(message, 'a backend sentence reads like the generic one: the rendered branch could not be told').not.toBe(generic);
        }
    });
});

describe('RiskResultFrame — each warning speaks through its own key', () => {
    it('formats a keyed warning with the names and dimension it carries, instead of printing its ICU source', () => {
        renderFrame(stressResult([WARNING.fallback]));
        expect(warningLines(1)).toEqual([resolve(FALLBACK_KEY, FALLBACK_PARAMS)]);
    });

    it('words an assets_excluded warning through its reason key, instead of the generic sentence', () => {
        renderFrame(stressResult([WARNING.excluded]));
        expect(warningLines(1)).toEqual([resolve(EXCLUDED_KEY, EXCLUDED_PARAMS)]);
    });

    it('formats a numeric argument — the share the replay still covers — instead of printing its ICU source', () => {
        renderFrame(stressResult([WARNING.mostlyExcluded]));
        expect(warningLines(1)).toEqual([resolve(MOSTLY_EXCLUDED_KEY, MOSTLY_EXCLUDED_PARAMS)]);
    });

    it('shows the backend sentence for a warning that carries no key', () => {
        renderFrame(stressResult([WARNING.unkeyed]));
        expect(warningLines(1)).toEqual([UNKEYED_MESSAGE]);
    });

    it('shows the backend sentence for a key this build does not ship, never the key', () => {
        renderFrame(stressResult([WARNING.absentKey]));
        expect(warningLines(1)).toEqual([ABSENT_KEY_MESSAGE]);
    });

    it('keeps the generic sentence for a warning with neither a key nor a readable sentence, instead of an empty line', () => {
        renderFrame(stressResult([WARNING.blank]));
        expect(warningLines(1)).toEqual([resolve(GENERIC_KEY)]);
    });

    it('leaves no ICU brace and no raw key anywhere once every kind is listed together', () => {
        renderFrame(stressResult([WARNING.fallback, WARNING.excluded, WARNING.mostlyExcluded, WARNING.unkeyed, WARNING.absentKey]));
        const lines = warningLines(5);
        const block = normalize(screen.getByTestId(`${TEST_ID}-warnings`).textContent ?? '');

        expect(block, 'a warning printed ICU braces: a sentence was formatted without its values').not.toContain('{');
        expect(block, 'a warning printed a raw catalogue key').not.toMatch(/risk\.(warnings|states)\./);
        expect(lines).toEqual([resolve(FALLBACK_KEY, FALLBACK_PARAMS), resolve(EXCLUDED_KEY, EXCLUDED_PARAMS), resolve(MOSTLY_EXCLUDED_KEY, MOSTLY_EXCLUDED_PARAMS), UNKEYED_MESSAGE, ABSENT_KEY_MESSAGE]);
    });

    // The general property, over the whole catalogue — the list and the values come
    // from `$test/riskWarningCatalogue`, shared with the helper's own cases. Each
    // warning's code is set to its key's own name: the worst case for a lookup by
    // code, which finds the sentence and prints its source.
    function scannedKeys(): string[] {
        const keys = icuWarningKeys();
        // Never an empty list: a frame with no lines has no brace to find either.
        expect(keys.length, 'no risk.warnings sentence with arguments was found: the scan reads the wrong node').toBeGreaterThan(0);
        for (const key of CODE_EQUAL_ICU_WARNING_KEYS) {
            expect(keys, `${key} is missing from the scanned list`).toContain(key);
        }
        return keys;
    }

    function catalogueWarning(key: string, index: number, params: WarningParams): Warning {
        return {code: key.replace('risk.warnings.', ''), message: `Synthetic backend sentence number ${index + 1}.`, message_i18n_key: key, message_params: params};
    }

    it('words every sentence with arguments through its own key once its values arrive — never a brace, never a key', () => {
        const keys = scannedKeys();
        const expected = keys.map((key) => resolve(key, plausibleParams(key)));
        expected.forEach((sentence, index) => {
            // The harness first: incomplete values would make even a correct frame fall back.
            expect(sentence, `the values built for ${keys[index]} do not complete its sentence`).not.toContain('{');
        });

        renderFrame(stressResult(keys.map((key, index) => catalogueWarning(key, index, plausibleParams(key)))));
        const lines = warningLines(keys.length);
        const block = normalize(screen.getByTestId(`${TEST_ID}-warnings`).textContent ?? '');

        expect(block, 'a sentence given its values still printed ICU braces').not.toContain('{');
        expect(block, 'a sentence given its values printed a raw key').not.toMatch(/risk\.(warnings|states)\./);
        expect(lines).toEqual(expected);
    });

    it('shows the backend sentence, never a brace or a key, for every sentence with arguments that arrives without its values', () => {
        const warnings = scannedKeys().map((key, index) => catalogueWarning(key, index, {}));

        // svelte-i18n logs every failed format; the log is the premise, not the subject.
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        try {
            renderFrame(stressResult(warnings));
            const lines = warningLines(warnings.length);
            const block = normalize(screen.getByTestId(`${TEST_ID}-warnings`).textContent ?? '');

            expect(block, 'a sentence without its values printed ICU braces').not.toContain('{');
            expect(block, 'a sentence without its values printed its key').not.toMatch(/risk\.(warnings|states)\./);
            expect(lines).toEqual(warnings.map((item) => item.message));
        } finally {
            warn.mockRestore();
        }
    });
});

describe('RiskResultFrame — the error branch is still worded by its code', () => {
    const BACKEND_ERROR_MESSAGE = 'A synthetic backend error sentence.';

    it('words a known error code through risk.errors.<code>, not through the backend sentence', () => {
        const key = 'risk.errors.incompatible_scope';
        expect(typeof enLeaf(key), `${key} is missing from en.json`).toBe('string');
        const expected = resolve(key);
        expect(expected, `${key} does not resolve`).not.toBe(key);
        expect(expected, `${key} reads like the state fallback: the two branches could not be told`).not.toBe(resolve('risk.states.unavailable'));

        renderFrame({instance_id: 'single-stress', analytic_code: 'stress', status: 'unavailable', error: {code: 'incompatible_scope', message: BACKEND_ERROR_MESSAGE}});

        const text = normalize(screen.getByTestId(`${TEST_ID}-unavailable`).textContent ?? '');
        expect(text).toBe(expected);
        expect(text).not.toContain(BACKEND_ERROR_MESSAGE);
        expect(screen.queryByTestId(`${TEST_ID}-warnings`), 'a result without warnings grew a warnings block').toBeNull();
    });

    it.each([
        {status: 'failed', error: {code: 'synthetic_error_code', message: BACKEND_ERROR_MESSAGE}, fallbackKey: 'risk.states.failed'},
        {status: 'unavailable', error: undefined, fallbackKey: 'risk.states.unavailable'},
    ] as const)('falls back to $fallbackKey when the $status result has no worded code', ({status, error, fallbackKey}) => {
        expect(typeof enLeaf(fallbackKey), `${fallbackKey} is missing from en.json`).toBe('string');
        expect(get(_)('risk.errors.synthetic_error_code'), 'the synthetic error code gained a sentence: the fallback would not be exercised').toBe('risk.errors.synthetic_error_code');
        const expected = resolve(fallbackKey);
        expect(expected, `${fallbackKey} does not resolve`).not.toBe(fallbackKey);

        // Cast on purpose: an error code outside the generated enum is exactly the
        // case the fallback exists for, and the enum type cannot express it.
        renderFrame({instance_id: 'single-stress', analytic_code: 'stress', status, ...(error === undefined ? {} : {error})} as unknown as RiskAnalyticResult);

        const text = normalize(screen.getByTestId(`${TEST_ID}-${status}`).textContent ?? '');
        expect(text).toBe(expected);
        expect(text).not.toContain('risk.errors.');
    });
});

/**
 * D379: a `resource_limit` refusal is worded by the remedy its details name.
 *
 * The backend's refusal for size now says which setting brings the run back within reach —
 * `details = {metric, actual, limit, remedy}` — and the frame words
 * `errorDisplayCode(singleValue(result.error))`: the remedy's own sentence,
 * `risk.errors.resource_limit_<remedy>`, when this build knows the remedy; the generic
 * `risk.errors.resource_limit` when it does not — never a key, and never the state sentence a key
 * built from an unknown remedy would fall to. Written red first: until the frame reads the
 * details, a refusal naming its remedy is worded with the generic sentence. The helper's own
 * rules live in `levels/levelHelpers.test.ts`; this block pins what reaches the reader of Asset
 * Detail's simulation frame.
 */
describe('RiskResultFrame — a resource_limit refusal is worded by the remedy it names', () => {
    const SIMULATION_TEST_ID = 'risk-simulation-section';
    const GENERIC_LIMIT_KEY = 'risk.errors.resource_limit';
    const PERIOD_KEY = 'risk.errors.resource_limit_period';
    const UNAVAILABLE_KEY = 'risk.states.unavailable';
    const FUTURE_REMEDY = 'future_remedy';
    const REFUSAL_MESSAGE = 'A synthetic backend refusal sentence.';
    /** The details `simulation.py::_resource_limit` sends for a history longer than the engine carries. */
    const PERIOD_DETAILS = {metric: 'observations', actual: 5001, limit: 5000, remedy: 'period'};

    type Refusal = {code: 'resource_limit'; message: string; details: Record<string, unknown>};

    /** A refusal for size as the backend sends it, carrying `details` as given. */
    function refusal(details: Record<string, unknown>): Refusal {
        return {code: 'resource_limit', message: REFUSAL_MESSAGE, details};
    }

    /** The error line of the simulation frame for an unavailable result carrying `error`, as the reader sees it. */
    function refusalLine(error: RiskAnalyticResult['error']): string {
        render(RiskResultFrame, {props: {title: 'Synthetic frame title', testId: SIMULATION_TEST_ID, result: {instance_id: 'single-simulation', analytic_code: 'simulation', status: 'unavailable', error}}});
        return normalize(screen.getByTestId(`${SIMULATION_TEST_ID}-unavailable`).textContent ?? '');
    }

    it('resolves the generic sentence and the period remedy’s own: two sentences, neither of them the state fallback', () => {
        expect(typeof enLeaf(GENERIC_LIMIT_KEY), `${GENERIC_LIMIT_KEY} is missing from en.json`).toBe('string');
        const generic = resolve(GENERIC_LIMIT_KEY);
        expect(generic, `${GENERIC_LIMIT_KEY} does not resolve: the catalogue is not loaded`).not.toBe(GENERIC_LIMIT_KEY);
        expect(generic, `${GENERIC_LIMIT_KEY} reads like ${UNAVAILABLE_KEY}: the two fallbacks could not be told`).not.toBe(resolve(UNAVAILABLE_KEY));

        expect(typeof enLeaf(PERIOD_KEY), `${PERIOD_KEY} is missing from en.json: a refusal naming the period remedy has no sentence to be worded by`).toBe('string');
        const period = resolve(PERIOD_KEY);
        expect(period, `${PERIOD_KEY} does not resolve through svelte-i18n`).not.toBe(PERIOD_KEY);
        expect(period, `${PERIOD_KEY} reads like ${GENERIC_LIMIT_KEY}: which sentence rendered could not be told`).not.toBe(generic);
        expect(period, `${PERIOD_KEY} reads like ${UNAVAILABLE_KEY}: which sentence rendered could not be told`).not.toBe(resolve(UNAVAILABLE_KEY));
    });

    // The error is read through `singleValue`, like the code before it: the generated client
    // types it as a value or a list, and a refusal that arrives wrapped keeps its remedy too.
    it.each([
        {form: 'as it arrives', wrap: (error: Refusal): RiskAnalyticResult['error'] => error},
        {form: 'wrapped in a list', wrap: (error: Refusal): RiskAnalyticResult['error'] => [error]},
    ])('words a refusal naming the period remedy by that remedy’s sentence, not the generic one — the error $form', ({wrap}) => {
        const generic = resolve(GENERIC_LIMIT_KEY);
        expect(generic, `${GENERIC_LIMIT_KEY} does not resolve: the comparison below would prove nothing`).not.toBe(GENERIC_LIMIT_KEY);

        const line = refusalLine(wrap(refusal(PERIOD_DETAILS)));

        expect(line, 'the refusal is worded with the generic resource_limit sentence: the remedy its details name never reached the reader').not.toBe(generic);
        expect(line, 'a raw catalogue key reached the screen').not.toMatch(/risk\.(errors|states)\./);
        expect(line, 'the backend sentence reached the screen').not.toContain(REFUSAL_MESSAGE);
        // What it must read instead, from the shipped catalogue: guarded, so a missing key cannot pass on its own echo.
        expect(typeof enLeaf(PERIOD_KEY), `${PERIOD_KEY} is missing from en.json`).toBe('string');
        expect(line).toBe(resolve(PERIOD_KEY));
    });

    it('keeps the generic resource_limit sentence for a remedy this build does not know — never the state fallback, never a key', () => {
        const generic = resolve(GENERIC_LIMIT_KEY);
        const unknownRemedyKey = `risk.errors.resource_limit_${FUTURE_REMEDY}`;
        expect(generic, `${GENERIC_LIMIT_KEY} does not resolve`).not.toBe(GENERIC_LIMIT_KEY);
        // The fallback is really exercised: the unknown remedy has no sentence of its own…
        expect(get(_)(unknownRemedyKey), `${unknownRemedyKey} gained a sentence: the fallback would not be exercised`).toBe(unknownRemedyKey);
        // …and the generic sentence can be told from the state one, where a key built from that remedy would fall.
        expect(generic, `${GENERIC_LIMIT_KEY} reads like ${UNAVAILABLE_KEY}: the two fallbacks could not be told`).not.toBe(resolve(UNAVAILABLE_KEY));

        const line = refusalLine(refusal({...PERIOD_DETAILS, remedy: FUTURE_REMEDY}));

        expect(line).toBe(generic);
        expect(line, 'a raw catalogue key reached the screen').not.toMatch(/risk\.(errors|states)\./);
        expect(line, 'the backend sentence reached the screen').not.toContain(REFUSAL_MESSAGE);
    });
});
