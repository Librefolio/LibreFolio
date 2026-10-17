// @vitest-environment jsdom
/**
 * CurrencySearchSelect — a stored currency value that is no ISO 4217 code (lot E-19b1, workstream E, item 3).
 *
 * Before E-18 the lenient rule stored a currency as given, so a row can hold `978` or `EURO`. The picker finds no such
 * option among the ISO currencies and today shows its placeholder: the stored value vanishes from the field, and the
 * user cannot tell what is stored nor what to choose instead. E-19b1 shows the stored value, with a hint.
 *
 * The contract under test, with `value` bound to `978` (not among the fixtures) once the currencies are loaded:
 *   - CNI-01: the field shows `978`, not the placeholder (read on the trigger, as `SearchSelect.test.ts` reads the
 *     selected display);
 *   - CNI-02: an element `data-testid="currency-non-iso-hint"` is shown; with the answer
 *     `{canonical: false, suggestion: 'EUR', candidates: ['EUR']}` it carries `data-suggestion="EUR"` and its text
 *     contains `978` and `EUR`;
 *   - CNI-03: `suggestCurrency` is called once, with `978`, and not again when the picker renders again with the same
 *     value;
 *   - CNI-04: an ambiguous answer (`{suggestion: null, candidates: ['VED', 'VES']}`): the hint shows, its text contains
 *     `VED` and `VES`, and it has no `data-suggestion` value (absent or empty);
 *   - CNI-05: an unknown answer (`{suggestion: null, candidates: []}`): the hint shows, and its text contains `978`;
 *   - CNI-06: `suggestCurrency` rejects: the hint shows as in CNI-05, and no rejection goes unhandled;
 *   - CNI-07: choosing `USD` from the list sets the value to `USD`, and the hint disappears;
 *   - CNI-08: the stored value is not a choice: an option of value `978`, if listed, is disabled;
 *   - CNI-09: the hint's texts are the keys `common.nonIsoCurrency.suggestion|candidates|unknown`, messages of the four
 *     catalogues naming `{value}`, `{suggestion}` and `{candidates}` (read from the contract's keys and parameters);
 *   - GUARDS (green today): the value `EUR` and an empty value give no hint and no call of `suggestCurrency`.
 *
 * The texts are never asserted on: only the parameters this file controls (`978`, `EUR`, `VED`, `VES`) are looked for
 * in them. A visual state is read on `data-*`, never on a class.
 *
 * `$lib/stores/reference/currencyStore` is mocked as `CurrencySearchSelect.test.ts` mocks it — `ensureCurrenciesLoaded`,
 * and `getAllCurrencies` answering EUR and USD — plus the new export `suggestCurrency(value)`, a `vi.fn` each case
 * answers (the backend's `GET /utilities/currencies/suggest`, through the store). The component imports only what this
 * mock defines.
 *
 * Red today (marked `// red until E-19b1`): the picker shows its placeholder for `978`, renders no hint and never asks
 * `suggestCurrency`; and the catalogues hold no `common.nonIsoCurrency` key.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick, type ComponentProps} from 'svelte';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import CurrencySearchSelect from './CurrencySearchSelect.svelte';

/** What `suggestCurrency(value)` resolves to: the answer of `GET /utilities/currencies/suggest`. */
type Suggestion = {canonical: boolean; suggestion: string | null; candidates: string[]};

const {ensureCurrenciesLoadedMock, suggestCurrencyMock} = vi.hoisted(() => ({
    ensureCurrenciesLoadedMock: vi.fn<() => Promise<void>>(),
    suggestCurrencyMock: vi.fn<(value: string) => Promise<Suggestion>>(),
}));

vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: ensureCurrenciesLoadedMock,
    getAllCurrencies: () => [
        {
            code: 'EUR',
            name: 'Euro fixture',
            symbol: '€',
            flag_emoji: '🇪🇺',
            country_codes: ['EU'],
            country_names: ['Fixture Europe'],
        },
        {
            code: 'USD',
            name: 'Dollar fixture',
            symbol: '$',
            flag_emoji: '🇺🇸',
            country_codes: ['US'],
            country_names: ['Fixture United States'],
        },
    ],
    suggestCurrency: suggestCurrencyMock,
}));

// --- Fixtures ---------------------------------------------------------------------------------------------------------

const HINT = 'currency-non-iso-hint';
const TEST_ID = 'stored-currency';
/** The stored value: a numeric code the lenient rule kept as given. Not among the fixtures. */
const STORED = '978';
/** A placeholder this file passes in, so that "not the placeholder" asserts on a prop, never on a translation. */
const PLACEHOLDER = 'placeholder-of-the-cni-fixture';

const SUGGESTS_EUR: Suggestion = {canonical: false, suggestion: 'EUR', candidates: ['EUR']};
const AMBIGUOUS: Suggestion = {canonical: false, suggestion: null, candidates: ['VED', 'VES']};
const UNKNOWN: Suggestion = {canonical: false, suggestion: null, candidates: []};

// --- Helpers ----------------------------------------------------------------------------------------------------------

function mount(value: string, props: Partial<ComponentProps<typeof CurrencySearchSelect>> = {}) {
    const onchange = vi.fn();
    const utils = render(CurrencySearchSelect, {value, testId: TEST_ID, placeholder: PLACEHOLDER, onchange, ...props});
    return {onchange, ...utils};
}

/** The field: SearchSelect's trigger, which shows the selected value (or the placeholder). */
function trigger(): HTMLElement {
    return screen.getByTestId(`${TEST_ID}-trigger`);
}

/** The hint, once it is on screen and `check` holds of it. Looked up again at every attempt: a new state may draw a new element. */
async function shownHint(check: (hint: HTMLElement) => void = () => {}): Promise<HTMLElement> {
    return waitFor(() => {
        const hint = screen.getByTestId(HINT);
        expect(hint).toBeVisible();
        check(hint);
        return hint;
    });
}

/** No hint the user can see: none in the document, or a hidden one. */
function expectNoHint(): void {
    const hint = screen.queryByTestId(HINT);
    if (hint !== null) expect(hint).not.toBeVisible();
}

/** The suggestion the hint publishes, `''` when it publishes none (the attribute absent or empty). */
function suggestionOf(hint: HTMLElement): string {
    return hint.getAttribute('data-suggestion') ?? '';
}

/** Let the effects and promise callbacks already queued run: Svelte's tick, the microtasks behind it, a tick again. */
async function settle(): Promise<void> {
    await tick();
    await Promise.resolve();
    await tick();
}

/** `suggestCurrency` was asked for the stored value, and its answer has been delivered to the component. */
async function answered(): Promise<void> {
    await waitFor(() => expect(suggestCurrencyMock).toHaveBeenCalledWith(STORED));
    await suggestCurrencyMock.mock.results[0].value;
    await settle();
}

/**
 * One turn of the event loop. Node reports a rejection nobody handled once the microtasks drain at the end of the
 * current task, before the next timer callback runs: this is an ordering point, not a bet on how long anything takes.
 */
async function oneEventLoopTurn(): Promise<void> {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
}

/** The open dropdown panel, scoped to this instance: the closing barrier of `SearchSelect.test.ts`. */
function dropdown(): HTMLElement {
    return screen.getByRole('listbox').parentElement as HTMLElement;
}

/** Opens the list and returns its panel once the currencies are drawn in it (USD is the presence barrier). */
async function openList(): Promise<HTMLElement> {
    await fireEvent.click(trigger());
    await waitFor(() => expect(screen.queryByRole('listbox')).not.toBeNull());
    const panel = dropdown();
    await within(panel).findByTestId('search-select-option-USD');
    return panel;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    ensureCurrenciesLoadedMock.mockReset();
    ensureCurrenciesLoadedMock.mockResolvedValue();
    suggestCurrencyMock.mockReset();
    suggestCurrencyMock.mockResolvedValue(SUGGESTS_EUR);
});

// =====================================================================================================================
describe('CurrencySearchSelect — a stored value that is no ISO 4217 code', () => {
    // red until E-19b1
    it('CNI-01: the field shows the stored value 978, not the placeholder', async () => {
        mount(STORED);

        await waitFor(() => expect(trigger()).toHaveTextContent(STORED));
        expect(trigger()).not.toHaveTextContent(PLACEHOLDER);
    });

    // red until E-19b1
    it('CNI-02: the hint is shown, carries data-suggestion="EUR", and its text names 978 and EUR', async () => {
        mount(STORED);

        const hint = await shownHint((shown) => expect(shown).toHaveAttribute('data-suggestion', 'EUR'));
        expect(hint).toHaveTextContent(STORED);
        expect(hint).toHaveTextContent('EUR');
    });

    // red until E-19b1
    it('CNI-03: suggestCurrency is asked once, with 978, and not again when the picker renders again with the same value', async () => {
        const {rerender} = mount(STORED);
        await shownHint((shown) => expect(shown).toHaveAttribute('data-suggestion', 'EUR'));
        expect(suggestCurrencyMock).toHaveBeenCalledExactlyOnceWith(STORED);

        await rerender({value: STORED, disabled: true});
        // The barrier: the new render is on screen (SearchSelect publishes data-disabled on its trigger).
        await waitFor(() => expect(trigger()).toHaveAttribute('data-disabled', 'true'));
        await settle();

        expect(suggestCurrencyMock).toHaveBeenCalledTimes(1);
    });

    // red until E-19b1
    it('CNI-04: an ambiguous value: the hint names VED and VES, and carries no data-suggestion value', async () => {
        suggestCurrencyMock.mockResolvedValue(AMBIGUOUS);
        mount(STORED);

        const hint = await shownHint((shown) => {
            expect(shown).toHaveTextContent('VED');
            expect(shown).toHaveTextContent('VES');
        });
        expect(suggestionOf(hint), 'no suggestion when two codes are possible').toBe('');
    });

    // red until E-19b1
    it('CNI-05: a value that stands for no code: the hint is shown and names 978', async () => {
        suggestCurrencyMock.mockResolvedValue(UNKNOWN);
        mount(STORED);
        await answered();

        const hint = await shownHint((shown) => expect(shown).toHaveTextContent(STORED));
        expect(suggestionOf(hint), 'no suggestion when no code is possible').toBe('');
    });

    // red until E-19b1
    it('CNI-06: suggestCurrency rejects: the hint is shown as for an unknown value, and no rejection goes unhandled', async () => {
        const unhandled: unknown[] = [];
        const record = (reason: unknown) => {
            unhandled.push(reason);
        };
        process.on('unhandledRejection', record);
        try {
            suggestCurrencyMock.mockRejectedValue(new Error('the suggestion failed (fixture)'));
            mount(STORED);
            await waitFor(() => expect(suggestCurrencyMock).toHaveBeenCalledWith(STORED));
            await oneEventLoopTurn();

            const hint = await shownHint((shown) => expect(shown).toHaveTextContent(STORED));
            expect(suggestionOf(hint), 'no suggestion when the answer failed').toBe('');
            expect(unhandled, 'the failure of suggestCurrency must be handled by the picker').toEqual([]);
        } finally {
            process.off('unhandledRejection', record);
        }
    });

    // red until E-19b1
    it('CNI-07: choosing USD from the list sets the value to USD, and the hint disappears', async () => {
        const {onchange} = mount(STORED);
        await shownHint();

        const panel = await openList();
        await fireEvent.click(within(panel).getByTestId('search-select-option-USD'));

        expect(onchange).toHaveBeenCalledExactlyOnceWith('USD');
        await waitFor(() => expect(trigger()).toHaveTextContent('USD'));
        await waitFor(() => expectNoHint());
        expect(suggestCurrencyMock, 'USD is an ISO code of the list: nothing to ask').not.toHaveBeenCalledWith('USD');
    });

    // red until E-19b1 (its precondition, CNI-01, is)
    it('CNI-08: the stored value is no choice: an option of value 978, if listed, is disabled, by pointer and by keyboard', async () => {
        const {onchange} = mount(STORED);
        await waitFor(() => expect(trigger()).toHaveTextContent(STORED));

        const panel = await openList();
        // Not a probe: the list is drawn (USD is in it), so an option 978 is listed now or never.
        const stored = within(panel).queryByTestId(`search-select-option-${STORED}`);
        if (stored !== null) {
            expect(stored).toBeDisabled();
            await fireEvent.click(stored);
            expect(onchange).not.toHaveBeenCalled();
            expect(screen.queryByRole('listbox'), 'a refused choice leaves the list open').not.toBeNull();
        }

        const search = screen.getByTestId(`${TEST_ID}-search`);
        await fireEvent.input(search, {target: {value: STORED}});
        await fireEvent.keyDown(search, {key: 'Enter'});
        expect(onchange, 'Enter on the stored value chooses nothing').not.toHaveBeenCalledWith(STORED);
    });
});

// =====================================================================================================================
describe('CurrencySearchSelect — values that need no hint', () => {
    it('GUARD (green today) CNI-G1: the value EUR, an ISO code of the list: no hint, and suggestCurrency is never asked', async () => {
        mount('EUR');
        // The barrier: EUR is drawn on the trigger only once the currencies are loaded.
        await waitFor(() => expect(trigger()).toHaveTextContent('EUR'));
        await settle();

        expectNoHint();
        expect(suggestCurrencyMock).not.toHaveBeenCalled();
    });

    it('GUARD (green today) CNI-G2: an empty value: no hint, and suggestCurrency is never asked', async () => {
        mount('');
        // The barrier: the list is drawn, so the currencies are loaded.
        await openList();
        await settle();

        expectNoHint();
        expect(suggestCurrencyMock).not.toHaveBeenCalled();
    });
});

// =====================================================================================================================
const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

/** The node at a dotted path of a catalogue, or undefined. */
function messageOf(catalogue: unknown, key: string): unknown {
    let node = catalogue;
    for (const part of key.split('.')) node = node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined;
    return node;
}

/** The ICU arguments a message names: `value` for «{value} is not an ISO code». */
function placeholdersOf(message: string): string[] {
    return [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();
}

/** Each text of the hint, and the parameters it must name: those the cases above look for in the hint. */
const HINT_TEXTS: Array<[string, string[]]> = [
    ['common.nonIsoCurrency.suggestion', ['suggestion', 'value']],
    ['common.nonIsoCurrency.candidates', ['candidates']],
    ['common.nonIsoCurrency.unknown', ['value']],
];

describe('the texts of the hint', () => {
    // red until E-19b1
    it.each(HINT_TEXTS)('CNI-09: %s is a message of the four catalogues, naming %j, the same placeholders in each', (key, required) => {
        const english = messageOf(en, key);
        expect(typeof english, `en: ${key} is not a message of the catalogue`).toBe('string');
        const named = placeholdersOf(english as string);
        expect(named, `en: ${key} must name ${required.join(', ')}`).toEqual(expect.arrayContaining(required));

        for (const [language, catalogue] of Object.entries(CATALOGUES)) {
            const message = messageOf(catalogue, key);
            expect(typeof message, `${language}: ${key} is not a message of the catalogue`).toBe('string');
            expect(placeholdersOf(message as string), `${language}: ${key} names other placeholders than in en`).toEqual(named);
        }
    });
});
