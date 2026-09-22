/**
 * currencyFormat under global privacy — what is replaced, and what survives.
 *
 * The formatter is the channel: every table cell, tooltip and title attribute
 * that shows money goes through it, so the substitution decided here is the one
 * the user sees everywhere. Four properties matter:
 *
 *  1. the currency identity survives — symbol, flag and code are not secrets,
 *     and dropping them would leave a column of bare bullets;
 *  2. the **magnitude** does not, in any form: two amounts four orders of
 *     magnitude apart produce one identical string (clause 2.2.2), and the
 *     placeholder's width never tracks the value;
 *  3. the **sign** does survive, on purpose — decision D8. Masking it was
 *     implemented first, on the argument that `+`/`-` publishes whether the
 *     holder is up or down; the objection was put to the product owner and
 *     rejected in favour of readability. `+•••` / `-•••` is therefore the
 *     contract, not a leak to be quietly fixed here. What it costs is not left
 *     to be rediscovered: the residual disclosure is pinned by "discloses
 *     whether a signed amount is zero" below;
 *  4. `formatCurrencyCodeHtml` has no amount to hide and is untouched.
 *
 * Note the deliberate asymmetry with `riskAnalysisHelpers.formatCurrencyAmount`
 * and `LotComparisonChart.formatAxisCurrency`, which replace the whole `Intl`
 * string and so return a bare `•••` with no prefix. D8 governs this module, not
 * those; the difference is documented at both ends and is not to be harmonised.
 *
 * Because the sign is now outside the substitution, an assertion that the
 * prefix is present is no longer evidence that anything was masked —
 * `toContain('+')` is green against a completely unmasked string. Every such
 * assertion below is therefore paired, against the *same* value, with one that
 * the locale-formatted amount is absent.
 *
 * Locale: `toLocaleString(undefined, …)` follows the host process, so the
 * expected amount is built with the same call rather than frozen as
 * `1,234.50` — a literal would turn a de-DE runner into a red. What is pinned
 * is the composition (which parts, in which order, with which separators),
 * which is what this module is responsible for. The *masked* expectations are
 * exact strings, because a placeholder has no locale.
 *
 * `getCurrencyInfo` reaches a session cache that is empty in a unit run (it
 * would fall back to `symbol === code`, `flag === '🏳️'`, and both are dropped
 * by the formatter), so it is stubbed per test — the same `vi.spyOn` on the
 * module namespace that syncToastHelpers.test.ts uses.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import * as currencyStore from '$lib/stores/reference/currencyStore';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';

import {formatCurrencyAmountHtml, formatCurrencyAmountPlain, formatCurrencyCodeHtml} from './currencyFormat';

const AMOUNT = 1234.5;

/** USD carries a real symbol and a real flag: every optional part is present. */
const USD: currencyStore.CurrencyInfo = {code: 'USD', name: 'US Dollar', symbol: '$', flag_emoji: '🇺🇸', country_codes: ['US'], country_names: ['United States']};
/** A code whose symbol *is* the code and whose flag is the placeholder one: both get dropped. */
const XAU: currencyStore.CurrencyInfo = {code: 'XAU', name: 'Gold', symbol: 'XAU', flag_emoji: '🏳️', country_codes: [], country_names: []};

const CURRENCIES: Record<string, currencyStore.CurrencyInfo> = {USD, XAU};

/** The amount exactly as the formatter renders it on this host's locale. */
function localAmount(value: number, fraction = 2): string {
    return Math.abs(value).toLocaleString(undefined, {minimumFractionDigits: fraction, maximumFractionDigits: fraction});
}

beforeEach(() => {
    setPrivacyEnabled(false);
    vi.spyOn(currencyStore, 'getCurrencyInfo').mockImplementation((code: string) => CURRENCIES[code] ?? {code, name: code, symbol: code, flag_emoji: '🏳️', country_codes: [], country_names: []});
});

afterEach(() => {
    // The store is module level and shared with every other suite in the run:
    // a leftover `true` here would mask the unmasked expectations elsewhere.
    setPrivacyEnabled(false);
    vi.restoreAllMocks();
});

describe('formatCurrencyAmountPlain — the currency survives, the magnitude does not', () => {
    it('keeps symbol, flag and code around the placeholder', () => {
        // Control: the same call with privacy off, which shows the four parts in
        // the order the masked assertion expects and the real amount in place.
        expect(formatCurrencyAmountPlain(AMOUNT, 'USD')).toBe(`${localAmount(AMOUNT)} $ 🇺🇸 USD`);

        setPrivacyEnabled(true);
        expect(formatCurrencyAmountPlain(AMOUNT, 'USD')).toBe(`${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
    });

    it('leaves nothing of the amount in the masked output', () => {
        setPrivacyEnabled(true);
        const masked = formatCurrencyAmountPlain(AMOUNT, 'USD');

        expect(masked).not.toContain(localAmount(AMOUNT));
        expect(masked).not.toMatch(/\d/);

        // The same check, on the same call, with the flag off: it can see the
        // amount when the amount is there. Without this the two lines above
        // would pass just as well against an empty string, or against a stub
        // that returned the suffix only.
        setPrivacyEnabled(false);
        expect(formatCurrencyAmountPlain(AMOUNT, 'USD')).toContain(localAmount(AMOUNT));
    });

    it('drops the parts the currency does not have, masked or not', () => {
        // XAU has no real symbol and only the placeholder flag, so the output is
        // amount + code. Masking must not resurrect the dropped parts.
        expect(formatCurrencyAmountPlain(AMOUNT, 'XAU')).toBe(`${localAmount(AMOUNT)} XAU`);

        setPrivacyEnabled(true);
        expect(formatCurrencyAmountPlain(AMOUNT, 'XAU')).toBe(`${PRIVACY_PLACEHOLDER} XAU`);
    });

    it('gives two very different magnitudes the same masked string', () => {
        // Control: unmasked, these differ — and by length, not just content.
        const smallClear = formatCurrencyAmountPlain(1_000, 'USD');
        const largeClear = formatCurrencyAmountPlain(9_999_999, 'USD');
        expect(smallClear).not.toBe(largeClear);
        expect(smallClear.length).not.toBe(largeClear.length);

        setPrivacyEnabled(true);
        expect(formatCurrencyAmountPlain(1_000, 'USD')).toBe(formatCurrencyAmountPlain(9_999_999, 'USD'));
        expect(formatCurrencyAmountPlain(1_000, 'USD')).toBe(`${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
    });
});

describe('formatCurrencyAmountPlain — the sign survives the mask, the magnitude does not (D8)', () => {
    it('keeps the + and takes the digits out from behind it', () => {
        // Control: `showSign: true` is genuinely in effect on this call — the
        // masked assertion below is worthless if the option was being ignored.
        expect(formatCurrencyAmountPlain(AMOUNT, 'USD', {showSign: true})).toBe(`+${localAmount(AMOUNT)} $ 🇺🇸 USD`);

        setPrivacyEnabled(true);
        const masked = formatCurrencyAmountPlain(AMOUNT, 'USD', {showSign: true});

        expect(masked).toBe(`+${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
        // The prefix assertion on its own is green whether or not masking
        // happened, so it is paired here against the same string: the `+` is
        // present *and* what it used to be attached to is gone.
        expect(masked).toContain('+');
        expect(masked).not.toContain(localAmount(AMOUNT));
        expect(masked).not.toMatch(/\d/);
    });

    it('renders a gain and a loss differently once masked — the direction is disclosed', () => {
        // This is the property D8 reversed: the two sides used to collapse to
        // one string. Pinning the new shape exactly is what makes a silent
        // re-masking of the sign show up here as a red.
        expect(formatCurrencyAmountPlain(AMOUNT, 'USD', {showSign: true})).not.toBe(formatCurrencyAmountPlain(-AMOUNT, 'USD', {showSign: true}));

        setPrivacyEnabled(true);
        const gain = formatCurrencyAmountPlain(AMOUNT, 'USD', {showSign: true});
        const loss = formatCurrencyAmountPlain(-AMOUNT, 'USD', {showSign: true});

        expect(gain).toBe(`+${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
        expect(loss).toBe(`-${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
        expect(gain).not.toBe(loss);

        // Paired on both: the sign is the entire difference, the magnitude is
        // absent from each — not merely absent from their comparison.
        expect(gain).not.toContain(localAmount(AMOUNT));
        expect(loss).not.toContain(localAmount(AMOUNT));
    });

    it('keeps the minus even when no sign was requested', () => {
        // `showSign` only governs the `+`; a negative amount always carries its
        // `-`, so an unsigned call on a negative value is a second, independent
        // path to a prefix — and under D8 it survives on that path too.
        expect(formatCurrencyAmountPlain(-AMOUNT, 'USD')).toBe(`-${localAmount(AMOUNT)} $ 🇺🇸 USD`);

        setPrivacyEnabled(true);
        const masked = formatCurrencyAmountPlain(-AMOUNT, 'USD');

        expect(masked).toBe(`-${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
        expect(masked).toContain('-');
        expect(masked).not.toContain(localAmount(AMOUNT));
        expect(masked).not.toMatch(/\d/);
    });

    it('gives two magnitudes of the same sign the identical masked string', () => {
        // Clause 2.2.2 survives D8: the sign came back out of the substitution,
        // the magnitude did not follow it out. Four orders of magnitude apart,
        // same sign ⇒ one string.
        const smallClear = formatCurrencyAmountPlain(1_000, 'USD', {showSign: true});
        const largeClear = formatCurrencyAmountPlain(9_999_999, 'USD', {showSign: true});
        expect(smallClear).not.toBe(largeClear);
        expect(smallClear.length).not.toBe(largeClear.length);

        setPrivacyEnabled(true);
        const small = formatCurrencyAmountPlain(1_000, 'USD', {showSign: true});
        const large = formatCurrencyAmountPlain(9_999_999, 'USD', {showSign: true});

        expect(small).toBe(large);
        expect(small).toBe(`+${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
        // And on the negative side, where the prefix differs but must still be
        // the only thing that differs.
        expect(formatCurrencyAmountPlain(-1_000, 'USD', {showSign: true})).toBe(formatCurrencyAmountPlain(-9_999_999, 'USD', {showSign: true}));
        expect(formatCurrencyAmountPlain(-1_000, 'USD', {showSign: true})).toBe(`-${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
    });

    it('discloses whether a signed amount is zero — a known, accepted consequence of D8', () => {
        // Deliberate, not an oversight, and pinned so it cannot be reversed in
        // silence. Six call sites pass `showSign: value !== 0` — UnifiedLotsTable,
        // LotCustodyModal, LotGanttChart, OtherPeriodEffectsTable,
        // ContributionTable, ExposureTable — so in those columns the prefix is
        // present exactly when the amount is non-zero. A fully masked column
        // therefore still reveals which rows carry a value: `sign(amount)` has
        // three states, not two.
        //
        // This test exists so that if someone later removes the disclosure, the
        // change is visible rather than silent — a privacy improvement made
        // behind D8's back is still a reversal of a decision with an owner.
        setPrivacyEnabled(true);
        const zero = formatCurrencyAmountPlain(0, 'USD', {showSign: true});
        const gain = formatCurrencyAmountPlain(AMOUNT, 'USD', {showSign: true});
        const loss = formatCurrencyAmountPlain(-AMOUNT, 'USD', {showSign: true});

        expect(zero).toBe(`${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
        expect(gain).toBe(`+${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
        expect(loss).toBe(`-${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);

        // Paired, as everywhere above: what the three shapes disclose is the
        // sign, and the magnitude is gone from all of them.
        for (const out of [zero, gain, loss]) expect(out).not.toMatch(/\d/);
    });
});

describe('formatCurrencyAmountHtml', () => {
    const suffix = '<span class="currency-symbol">$</span> <span class="emoji-flag">🇺🇸</span> <span class="currency-code">USD</span>';

    it('keeps the currency-amount wrapper around the placeholder', () => {
        // Control: the wrapper and suffix as they are without privacy.
        expect(formatCurrencyAmountHtml(AMOUNT, 'USD')).toBe(`<span class="currency-amount">${localAmount(AMOUNT)}</span> ${suffix}`);

        setPrivacyEnabled(true);
        const masked = formatCurrencyAmountHtml(AMOUNT, 'USD');

        expect(masked).toBe(`<span class="currency-amount">${PRIVACY_PLACEHOLDER}</span> ${suffix}`);
        // The wrapper is what the stylesheet and the cell renderer key on, so
        // its survival is asserted on its own and not only via the whole string.
        expect(masked).toContain(`<span class="currency-amount">${PRIVACY_PLACEHOLDER}</span>`);
    });

    it('masks the amount without disturbing the markup around it', () => {
        setPrivacyEnabled(true);
        const masked = formatCurrencyAmountHtml(AMOUNT, 'USD', {showSign: true});

        expect(masked).toContain(suffix);
        expect(masked).not.toContain(localAmount(AMOUNT));
        // D8 puts the prefix *inside* the amount wrapper, glued to the
        // placeholder — not loose between the spans, where the stylesheet that
        // colours the amount green or red would not reach it. Asserting the
        // wrapper's whole content is what distinguishes the two placements;
        // a bare `toContain('+')` would accept either, and would also accept a
        // string that was never masked at all, which is why the magnitude
        // check above is on the same value.
        expect(masked).toContain(`<span class="currency-amount">+${PRIVACY_PLACEHOLDER}</span>`);
        expect(masked).toBe(`<span class="currency-amount">+${PRIVACY_PLACEHOLDER}</span> ${suffix}`);

        // The negative takes the same route through the same wrapper.
        const maskedLoss = formatCurrencyAmountHtml(-AMOUNT, 'USD', {showSign: true});
        expect(maskedLoss).toBe(`<span class="currency-amount">-${PRIVACY_PLACEHOLDER}</span> ${suffix}`);
        expect(maskedLoss).not.toContain(localAmount(AMOUNT));

        setPrivacyEnabled(false);
        const clear = formatCurrencyAmountHtml(AMOUNT, 'USD', {showSign: true});
        expect(clear).toContain(suffix);
        expect(clear).toContain(localAmount(AMOUNT));
        expect(clear).toContain(`<span class="currency-amount">+${localAmount(AMOUNT)}</span>`);
    });
});

describe('sensitivity: public', () => {
    it('renders the real amount with privacy on', () => {
        setPrivacyEnabled(true);
        expect(isPrivacyEnabled()).toBe(true);

        const plain = formatCurrencyAmountPlain(AMOUNT, 'USD', {sensitivity: 'public'});
        const html = formatCurrencyAmountHtml(AMOUNT, 'USD', {sensitivity: 'public'});

        expect(plain).toBe(`${localAmount(AMOUNT)} $ 🇺🇸 USD`);
        expect(html).toContain(`<span class="currency-amount">${localAmount(AMOUNT)}</span>`);

        // Positive control for the flag itself: with privacy in this exact
        // state, an unclassified amount *is* masked. Otherwise "public was not
        // masked" would also hold on a run where the flag never turned on.
        expect(formatCurrencyAmountPlain(AMOUNT, 'USD')).toBe(`${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
    });

    it('keeps the sign of a public amount', () => {
        setPrivacyEnabled(true);

        expect(formatCurrencyAmountPlain(AMOUNT, 'USD', {showSign: true, sensitivity: 'public'})).toBe(`+${localAmount(AMOUNT)} $ 🇺🇸 USD`);
        expect(formatCurrencyAmountPlain(-AMOUNT, 'USD', {sensitivity: 'public'})).toBe(`-${localAmount(AMOUNT)} $ 🇺🇸 USD`);
    });

    it('is the only opt-out: an explicit personal is masked like an omitted one', () => {
        setPrivacyEnabled(true);

        expect(formatCurrencyAmountPlain(AMOUNT, 'USD', {sensitivity: 'personal'})).toBe(`${PRIVACY_PLACEHOLDER} $ 🇺🇸 USD`);
        expect(formatCurrencyAmountPlain(AMOUNT, 'USD', {sensitivity: 'personal'})).toBe(formatCurrencyAmountPlain(AMOUNT, 'USD'));
    });
});

describe('formatCurrencyCodeHtml', () => {
    it('is identical with privacy on and off', () => {
        const usdClear = formatCurrencyCodeHtml('USD');
        const xauClear = formatCurrencyCodeHtml('XAU');

        setPrivacyEnabled(true);
        expect(formatCurrencyCodeHtml('USD')).toBe(usdClear);
        expect(formatCurrencyCodeHtml('XAU')).toBe(xauClear);
    });

    it('still renders the parts it always rendered', () => {
        // Without this the equality above would hold just as well between two
        // empty strings: the point is that there is something to be unaffected.
        setPrivacyEnabled(true);
        const html = formatCurrencyCodeHtml('USD');

        expect(html).toBe('<span class="currency-symbol">$</span> <span class="emoji-flag">🇺🇸</span> <span class="currency-code">USD</span>');
        expect(html).not.toContain(PRIVACY_PLACEHOLDER);
    });
});
