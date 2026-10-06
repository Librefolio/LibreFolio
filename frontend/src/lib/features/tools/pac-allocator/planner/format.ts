/**
 * The only privacy adapter of the PAC planner (C7).
 *
 * Every amount, quantity, price, rate and percentage the planner renders goes
 * through this file, so a change of J's privacy API touches one place. Rules
 * (C0 delta §7, decision c): wealth — amounts and quantities — is `personal`
 * and masked when privacy is on; market prices, FX rates and percentages are
 * `public`. The sign and the `≈` marker stay outside the mask. Exact values
 * stay strings; `Number()` appears only at this display boundary.
 *
 * R14: an amount the backend computed is shown at the minor unit of its
 * currency, rounded exactly from its decimal or ratio; `≈` marks a value the
 * rounding changed. Prices, typed values and posted flows keep their digits.
 */
import {formatCurrencyAmountHtml, formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import {formatDateTime} from '$lib/utils/core/formatDateTime';
import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
import {formatPercent} from '$lib/utils/core/formatPercent';
import {maskable, type AmountSensitivity} from '$lib/utils/privacy/maskable';
import {canonicalDecimal, decimalEqualsRatio, decimalScale, roundDecimal, roundRatio} from './decimal';
import {defaultAsOf} from './defaults';
import type {PacExactMoney, PacExactNumber, PacExactPrice, PacObjectiveUnit} from './types';

export type CurrencyDigits = (currencyCode: string) => number;

const EMPTY = '—';
const MAX_DISPLAY_FRACTION = 20;
/** Fraction digits of a solver number that is not money (a count bound). */
const SOLVER_COUNT_DIGITS = 2;

/** CLDR fraction digits, used for draft values before the backend catalog exists. */
export function cldrCurrencyDigits(currencyCode: string): number {
    try {
        return new Intl.NumberFormat('en', {style: 'currency', currency: currencyCode}).resolvedOptions().maximumFractionDigits ?? 2;
    } catch {
        return 2;
    }
}

/** The smallest CLDR amount of a currency (`0.01`), used as the arrow step of money inputs. */
export function cldrCurrencyStep(currencyCode: string): string {
    const places = cldrCurrencyDigits(currencyCode);
    return places <= 0 ? '1' : '0.' + '0'.repeat(places - 1) + '1';
}

/** Fraction digits published by the backend catalog (`minor_unit`, e.g. `0.01`). */
export function catalogCurrencyDigits(currencies: readonly {currency: string; minor_unit: string}[]): CurrencyDigits {
    const digits = new Map(currencies.map((item) => [item.currency, decimalScale(item.minor_unit)]));
    return (currencyCode) => digits.get(currencyCode) ?? cldrCurrencyDigits(currencyCode);
}

/** Whether the backend display projection of an exact ratio equals the ratio. */
function isExactProjection(value: Extract<PacExactNumber, {kind: 'exact_ratio'}>): boolean {
    const shown = canonicalDecimal(value.display_decimal);
    return shown !== null && decimalEqualsRatio(shown, value.numerator, value.denominator);
}

/** Decimal text to show for an exact backend number, and whether it is approximate. */
export function exactDisplay(value: PacExactNumber): {text: string; approx: boolean} {
    if (value.kind === 'finite_decimal') return {text: value.value, approx: false};
    return {text: value.display_decimal, approx: !isExactProjection(value)};
}

/** R14: an exact backend amount rounded to `places` fraction digits, and whether the rounding changed it. */
export function exactMoneyDisplay(value: PacExactNumber, places: number): {text: string; approx: boolean} {
    if (value.kind === 'finite_decimal') {
        const canonical = canonicalDecimal(value.value);
        const rounded = canonical === null ? null : roundDecimal(canonical, places);
        return rounded === null ? {text: value.value, approx: false} : {text: rounded, approx: rounded !== canonical};
    }
    const rounded = roundRatio(value.numerator, value.denominator, places);
    if (rounded !== null) return {text: rounded, approx: !decimalEqualsRatio(rounded, value.numerator, value.denominator)};
    return {text: roundDecimal(value.display_decimal, places) ?? value.display_decimal, approx: true};
}

interface MoneyOptions {
    digits?: CurrencyDigits;
    signed?: boolean;
    approx?: boolean;
    sensitivity?: AmountSensitivity;
    /** R14: round a raw amount to the minor unit of its currency; `≈` when the rounding changes it. */
    minorUnit?: boolean;
}

function moneyArgs(amount: string, currencyCode: string, options: MoneyOptions) {
    const canonical = canonicalDecimal(amount);
    if (canonical === null) return null;
    const minFraction = (options.digits ?? cldrCurrencyDigits)(currencyCode);
    const shown = options.minorUnit ? (roundDecimal(canonical, minFraction) ?? canonical) : canonical;
    const maxFraction = Math.min(MAX_DISPLAY_FRACTION, Math.max(minFraction, decimalScale(shown)));
    return {
        value: Number(shown),
        approx: (options.approx ?? false) || shown !== canonical,
        opts: {minFraction, maxFraction, showSign: options.signed ?? false, sensitivity: options.sensitivity ?? ('personal' as const)},
    };
}

/** An amount in its native currency. Personal unless told otherwise. */
export function formatPlannerMoneyPlain(amount: string | null | undefined, currencyCode: string, options: MoneyOptions = {}): string {
    if (amount === null || amount === undefined) return EMPTY;
    const args = moneyArgs(amount, currencyCode, options);
    if (!args) return EMPTY;
    const text = formatCurrencyAmountPlain(args.value, currencyCode, args.opts);
    return args.approx ? '≈' + text : text;
}

export function formatPlannerMoneyHtml(amount: string | null | undefined, currencyCode: string, options: MoneyOptions = {}): string {
    if (amount === null || amount === undefined) return EMPTY;
    const args = moneyArgs(amount, currencyCode, options);
    if (!args) return EMPTY;
    const html = formatCurrencyAmountHtml(args.value, currencyCode, args.opts);
    return args.approx ? '≈' + html : html;
}

/** An amount the backend computed, at the minor unit of its currency (R14). */
export function formatExactMoneyPlain(money: PacExactMoney, options: MoneyOptions = {}): string {
    const shown = exactMoneyDisplay(money.value, (options.digits ?? cldrCurrencyDigits)(money.currency));
    return formatPlannerMoneyPlain(shown.text, money.currency, {...options, minorUnit: false, approx: shown.approx});
}

export function formatExactMoneyHtml(money: PacExactMoney, options: MoneyOptions = {}): string {
    const shown = exactMoneyDisplay(money.value, (options.digits ?? cldrCurrencyDigits)(money.currency));
    return formatPlannerMoneyHtml(shown.text, money.currency, {...options, minorUnit: false, approx: shown.approx});
}

/** A market price: public by definition (decision c). */
export function formatPlannerPricePlain(amount: string | null | undefined, currencyCode: string, digits?: CurrencyDigits): string {
    return formatPlannerMoneyPlain(amount, currencyCode, {digits, sensitivity: 'public'});
}

export function formatPlannerPriceHtml(amount: string | null | undefined, currencyCode: string, digits?: CurrencyDigits): string {
    return formatPlannerMoneyHtml(amount, currencyCode, {digits, sensitivity: 'public'});
}

export function formatExactPricePlain(price: PacExactPrice, digits?: CurrencyDigits): string {
    const shown = exactDisplay(price.value);
    return formatPlannerMoneyPlain(shown.text, price.currency, {digits, approx: shown.approx, sensitivity: 'public'});
}

/** A quantity of an Asset: wealth, so personal (D5′). Unit labels stay outside. */
export function formatPlannerQuantity(quantity: string | null | undefined, options: {approx?: boolean} = {}): string {
    if (quantity === null || quantity === undefined) return EMPTY;
    const canonical = canonicalDecimal(quantity);
    if (canonical === null) return EMPTY;
    const text = maskable(formatDecimalForDisplay(canonical, {maxFrac: MAX_DISPLAY_FRACTION}), 'personal');
    return options.approx ? '≈' + text : text;
}

export function formatExactQuantity(value: PacExactNumber): string {
    const shown = exactDisplay(value);
    return formatPlannerQuantity(shown.text, {approx: shown.approx});
}

/** A scenario parameter that is not wealth (step, priority, count): shown as typed. */
export function formatPlannerPlainDecimal(value: string | null | undefined): string {
    if (value === null || value === undefined) return EMPTY;
    const canonical = canonicalDecimal(value);
    return canonical === null ? EMPTY : maskable(formatDecimalForDisplay(canonical, {maxFrac: MAX_DISPLAY_FRACTION}), 'public');
}

/** An FX rate: public. */
export function formatPlannerFxRate(rate: string | null | undefined, options: {approx?: boolean} = {}): string {
    if (rate === null || rate === undefined) return EMPTY;
    const canonical = canonicalDecimal(rate);
    if (canonical === null) return EMPTY;
    const text = maskable(formatDecimalForDisplay(canonical, {maxFrac: MAX_DISPLAY_FRACTION}), 'public');
    return options.approx ? '≈' + text : text;
}

export function formatExactFxRate(value: PacExactNumber): string {
    const shown = exactDisplay(value);
    return formatPlannerFxRate(shown.text, {approx: shown.approx});
}

/** A fraction (0.6) shown as a percentage (60.00%): public. */
export function formatPlannerPercent(fraction: string | null | undefined, options: {digits?: number; signed?: boolean; approx?: boolean} = {}): string {
    if (fraction === null || fraction === undefined) return EMPTY;
    const canonical = canonicalDecimal(fraction);
    if (canonical === null) return EMPTY;
    const text = maskable(formatPercent(Number(canonical), {scale: 100, signed: options.signed ?? false, digits: options.digits ?? 2}), 'public');
    return options.approx ? '≈' + text : text;
}

/** A percentage already expressed in percent units (the draft inputs and their control total). */
export function formatPlannerPercentUnits(percent: string | null | undefined, digits = 2): string {
    if (percent === null || percent === undefined) return EMPTY;
    const canonical = canonicalDecimal(percent);
    return canonical === null ? EMPTY : maskable(formatPercent(Number(canonical), {scale: 1, signed: false, digits}), 'public');
}

/**
 * R10.8: a weight is shown to `digits` decimals with no «≈». An exact ratio such as 1/3 has no finite
 * decimal, so the mark sat on most weights and only said that two decimals are a rounding.
 * Quantities and rates keep it; an amount carries it only when the rounding to the minor unit of its
 * currency changed it (R14). Amendments of the C0 rule, recorded in the plan.
 */
export function formatExactPercent(value: PacExactNumber, digits = 2): string {
    return formatPlannerPercent(exactDisplay(value).text, {digits});
}

/** L2 distance in squared valuation money: personal, unit outside the mask (`≈••• EUR²`). R14: two decimals, `≈` when the rounding changes it. */
export function formatPlannerL2(value: PacExactNumber, currencyCode: string): string {
    const shown = exactMoneyDisplay(value, SOLVER_COUNT_DIGITS);
    const canonical = canonicalDecimal(shown.text);
    if (canonical === null) return EMPTY;
    const digits = maskable(Number(canonical).toLocaleString(undefined, {maximumFractionDigits: SOLVER_COUNT_DIGITS}), 'personal');
    return [(shown.approx ? '≈' : '') + digits, currencyCode + '²'].join(' ');
}

/** An objective or solver value, formatted by its declared unit. */
export function formatObjectiveValue(value: PacExactNumber, unit: PacObjectiveUnit, digits?: CurrencyDigits): string {
    if (unit.kind === 'valuation_money') return formatExactMoneyPlain({value, currency: unit.currency_code}, {digits});
    if (unit.kind === 'valuation_money_squared') return formatPlannerL2(value, unit.currency_code);
    const shown = exactDisplay(value);
    return formatPlannerFxRate(shown.text, {approx: shown.approx});
}

/**
 * A raw solver number (primal, dual, gap) carrying the stage unit. R14: money at the minor unit of its
 * currency, a count to two decimals; `≈` when the rounding changes the reported float.
 */
export function formatSolverNumber(value: string | null | undefined, unit: PacObjectiveUnit, digits?: CurrencyDigits): string {
    if (value === null || value === undefined) return EMPTY;
    if (unit.kind === 'valuation_money') return formatPlannerMoneyPlain(value, unit.currency_code, {digits, minorUnit: true});
    if (unit.kind === 'valuation_money_squared') return formatPlannerL2({kind: 'finite_decimal', value}, unit.currency_code);
    const canonical = canonicalDecimal(value);
    if (canonical === null) return EMPTY;
    const rounded = roundDecimal(canonical, SOLVER_COUNT_DIGITS) ?? canonical;
    return formatPlannerFxRate(rounded, {approx: rounded !== canonical});
}

/** A calendar date (`YYYY-MM-DD`) in the user's locale, with no timezone shift. Public. */
export function formatPlannerDate(value: string | null | undefined, locale?: string | null): string {
    if (!value) return EMPTY;
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!match) return value;
    return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])).toLocaleDateString(locale ?? undefined, {year: 'numeric', month: '2-digit', day: '2-digit'});
}

/** When a fact was copied or entered. Public. */
export function formatPlannerTimestamp(value: string | null | undefined, locale?: string | null): string {
    if (!value) return EMPTY;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : formatDateTime(parsed, locale ?? undefined);
}

/**
 * When copied data refers to, for a copy badge: data of today shows the date and time the copy ran; data of an
 * earlier day, or a copy with no readable time, shows only its date. Public.
 */
export function formatCopyStamp(asOf: string | null | undefined, capturedAt: string | null | undefined, locale?: string | null, now: Date = new Date()): string {
    if (!asOf) return EMPTY;
    const captured = capturedAt ? new Date(capturedAt) : null;
    if (captured === null || Number.isNaN(captured.getTime()) || asOf < defaultAsOf(now)) return formatPlannerDate(asOf, locale);
    return captured.toLocaleString(locale ?? undefined, {year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'});
}
