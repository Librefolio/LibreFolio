// @vitest-environment jsdom
/**
 * CurrencyAmount — one amount through the D8 formatter, followed live (Vitest + jsdom).
 *
 * The component is the R20 fix. A legacy-mode template compiles a call inside an expression to
 * `$.untrack(() => …)`, so `{@html formatCurrencyAmountHtml(…)}` written in a legacy component
 * never sees the privacy flag the formatter reads through `maskable`: the amount keeps the
 * state it had at mount. Legacy parents (BrokerCard, broker detail) now render money through
 * this runes child instead. Its contract is small and exact, and each part has a test:
 *   - it renders exactly the markup `formatCurrencyAmountHtml(amount, code, options)` returns
 *     in the same state — no wrapper element, no reformatting;
 *   - under a legacy parent it follows the privacy toggle both ways, and on every toggle after
 *     the first;
 *   - it passes `options` through (`showSign` keeps `+` outside the mask, decision D8);
 *   - a new amount from the parent re-renders it, and the flag is still followed afterwards.
 *
 * The parent is `$test/harness/CurrencyAmountLegacyHost.svelte`, legacy by construction. It
 * also renders the same call inline, and that copy is the control for the premise: it must keep
 * its mount-time markup while the child follows. Without it, a green toggle test could not tell
 * "the runes child tracked the flag" from "something re-rendered the whole host".
 *
 * Every toggle step checks two controls before the subject: `isPrivacyEnabled()` (the flag
 * moved) and a fresh formatter call (the formatter follows it). Expected markup is always the
 * formatter's own output in the current state — the host locale decides the separators — and
 * the digits of the clear amount are checked once against the value put in.
 *
 * Comparison. Svelte leaves empty comment anchors around `{@html}` and component boundaries;
 * they are not content, so they are stripped before `innerHTML` is compared. Nothing else is.
 *
 * Storage. The shared `$app/environment` mock reports `browser: false`, so `setPrivacyEnabled`
 * moves the in-memory rune and never touches `localStorage`. Nothing here reads translated
 * text; the component renders none.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';

// The currency catalogue is the only request in this graph, answered so the markup carries a
// real symbol and flag — every optional part the formatter can emit. Everything else is inert.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') {
                    return vi.fn(async () => ({
                        items: [{code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []}],
                    }));
                }
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {render, screen} from '$test/component';
import CurrencyAmountLegacyHost from '$test/harness/CurrencyAmountLegacyHost.svelte';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {formatCurrencyAmountHtml, type CurrencyAmountFormatOptions} from '$lib/utils/currency/currencyFormat';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';

const P = PRIVACY_PLACEHOLDER;
const CODE = 'EUR';
const AMOUNT = 12345.67;
/** A second amount, different in every digit, for the prop-change test. */
const OTHER_AMOUNT = 890.12;

/** `.currency-amount` text of the formatter's output for AMOUNT with privacy off; set in `beforeAll`. */
let clearText = '';

const child = () => screen.getByTestId('legacy-host-child');
const inline = () => screen.getByTestId('legacy-host-inline');

/** The markup under `el` as content: Svelte's comment anchors are removed, nothing else is. */
function markupOf(el: Element): string {
    const clone = el.cloneNode(true) as Element;
    const walker = document.createTreeWalker(clone, NodeFilter.SHOW_COMMENT);
    const anchors: Node[] = [];
    while (walker.nextNode()) anchors.push(walker.currentNode);
    for (const anchor of anchors) anchor.parentNode?.removeChild(anchor);
    return clone.innerHTML;
}

/** The `.currency-amount` text inside a piece of formatter markup. */
function amountTextOf(html: string): string {
    const host = document.createElement('span');
    host.innerHTML = html;
    const [amount, ...extra] = [...host.querySelectorAll('.currency-amount')];
    if (!amount || extra.length > 0) throw new Error('expected exactly one .currency-amount');
    return amount.textContent ?? '';
}

/** Set the flag, then flush: synchronously, and once more through the microtask the app itself waits on. */
async function setPrivacy(value: boolean): Promise<void> {
    setPrivacyEnabled(value);
    flushSync();
    await tick();
}

/**
 * One toggle step: the flag is where the step says, the formatter follows it, the child renders
 * exactly the formatter's markup in that state — and the legacy parent's inline copy has not
 * moved from its mount-time markup.
 */
function expectStep(step: string, masked: boolean, inlineAtMount: string): void {
    expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(masked);
    const now = formatCurrencyAmountHtml(AMOUNT, CODE);
    expect(amountTextOf(now), `${step} — control: a fresh formatter call`).toBe(masked ? P : clearText);

    expect(markupOf(child()), `${step} — the child renders the formatter's markup in this state`).toBe(now);
    expect(markupOf(inline()), `${step} — premise: the legacy parent's inline call keeps its mount-time markup`).toBe(inlineAtMount);
}

beforeAll(async () => {
    await ensureCurrenciesLoaded('en');
    // Control: the cache is populated, so the markup carries symbol and flag, not the bare-code fallback.
    expect(getCurrencyInfo(CODE).symbol).toBe('€');

    setPrivacyEnabled(false);
    clearText = amountTextOf(formatCurrencyAmountHtml(AMOUNT, CODE));
    // The expectations are the formatter's own output, so check once that the clear one carries
    // the digits put in: a formatter masking unconditionally would otherwise make every "clear"
    // step compare the placeholder with itself.
    expect(clearText.replace(/\D/g, '')).toBe('1234567');
});

afterEach(() => {
    // The flag is module-level state shared by every test in this file: a leftover `true`
    // would mount the next host masked.
    setPrivacyEnabled(false);
});

describe('CurrencyAmount — one amount through the formatter, followed live (R20)', () => {
    it('renders exactly the markup formatCurrencyAmountHtml returns for the same inputs, and nothing around it', () => {
        render(CurrencyAmountLegacyHost, {amount: AMOUNT, code: CODE});

        const expected = formatCurrencyAmountHtml(AMOUNT, CODE);
        expect(markupOf(child())).toBe(expected);
        // Control: the expectation is the full formatter output — amount, symbol, flag and code.
        for (const part of ['.currency-amount', '.currency-symbol', '.emoji-flag', '.currency-code']) {
            expect(child().querySelectorAll(part), `${part} rendered once`).toHaveLength(1);
        }
        expect(amountTextOf(expected)).toBe(clearText);
    });

    it('under a legacy parent, mounted in the clear: masks when privacy turns on and unmasks when it turns off', async () => {
        render(CurrencyAmountLegacyHost, {amount: AMOUNT, code: CODE});
        const inlineAtMount = markupOf(inline());
        expectStep('mount, privacy off', false, inlineAtMount);

        await setPrivacy(true);
        expectStep('off → on', true, inlineAtMount);

        await setPrivacy(false);
        expectStep('on → off', false, inlineAtMount);
    });

    it('under a legacy parent, mounted masked: unmasks when privacy turns off', async () => {
        await setPrivacy(true);
        render(CurrencyAmountLegacyHost, {amount: AMOUNT, code: CODE});
        const inlineAtMount = markupOf(inline());
        expectStep('mount, privacy on', true, inlineAtMount);

        await setPrivacy(false);
        expectStep('on → off', false, inlineAtMount);
    });

    it('under a legacy parent, follows every toggle of two more round trips (on/off/on/off), not only the first', async () => {
        render(CurrencyAmountLegacyHost, {amount: AMOUNT, code: CODE});
        const inlineAtMount = markupOf(inline());
        expectStep('mount, privacy off', false, inlineAtMount);

        for (const round of [1, 2]) {
            await setPrivacy(true);
            expectStep(`round ${round}: off → on`, true, inlineAtMount);
            await setPrivacy(false);
            expectStep(`round ${round}: on → off`, false, inlineAtMount);
        }
    });

    it('passes options through: showSign puts + in front of the amount, outside the mask', async () => {
        const options: CurrencyAmountFormatOptions = {showSign: true};
        render(CurrencyAmountLegacyHost, {amount: AMOUNT, code: CODE, options});

        // Control: the option changes the formatter's output, so matching it is evidence it was passed.
        expect(formatCurrencyAmountHtml(AMOUNT, CODE, options)).not.toBe(formatCurrencyAmountHtml(AMOUNT, CODE));
        expect(markupOf(child()), 'clear').toBe(formatCurrencyAmountHtml(AMOUNT, CODE, options));
        expect(child().querySelector('.currency-amount')?.textContent).toBe(`+${clearText}`);

        await setPrivacy(true);
        expect(isPrivacyEnabled(), 'control: the flag').toBe(true);
        expect(markupOf(child()), 'masked').toBe(formatCurrencyAmountHtml(AMOUNT, CODE, options));
        // D8: the sign stays outside the substitution.
        expect(child().querySelector('.currency-amount')?.textContent).toBe(`+${P}`);
    });

    it('renders a new amount when the parent passes one, and keeps following the flag after it', async () => {
        const {rerender} = render(CurrencyAmountLegacyHost, {amount: AMOUNT, code: CODE});
        expect(markupOf(child()), 'before').toBe(formatCurrencyAmountHtml(AMOUNT, CODE));

        rerender({amount: OTHER_AMOUNT});
        const next = formatCurrencyAmountHtml(OTHER_AMOUNT, CODE);
        // Control: the two amounts render differently, so a stale child cannot pass as updated.
        expect(amountTextOf(next)).not.toBe(clearText);
        expect(markupOf(child()), 'after the prop change').toBe(next);

        await setPrivacy(true);
        expect(isPrivacyEnabled(), 'control: the flag').toBe(true);
        expect(markupOf(child()), 'masked after the prop change').toBe(formatCurrencyAmountHtml(OTHER_AMOUNT, CODE));
        await setPrivacy(false);
        expect(markupOf(child()), 'clear again').toBe(next);
    });
});
