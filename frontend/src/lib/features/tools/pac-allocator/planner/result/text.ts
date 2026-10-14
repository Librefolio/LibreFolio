/**
 * Sentences of the result screens (C10–C13, D12).
 *
 * Wording only: every figure is a backend field or a request field passed
 * through the privacy adapter. Quantities, amounts, route caps and minimums
 * are wealth (`personal`); prices and steps are public.
 */
import type {Readable} from 'svelte/store';
import type {t} from '$lib/i18n';
import {compareDecimal, decimalScale, fractionToPercent} from '../decimal';
import {exactQuantityCount, formatExactPricePlain, formatExactQuantity, formatPlannerMoneyPlain, formatPlannerPercentUnits, formatPlannerPlainDecimal, formatPlannerPricePlain, formatPlannerQuantity, plannerPlainDecimalCount, plannerQuantityCount, type CurrencyDigits} from '../format';
import type {PacExactPrice, PacOrderRow, PacResolvedOrderRoute} from '../types';

export type Translator = typeof t extends Readable<infer Formatter> ? Formatter : never;

const KEY = 'tools.pacAllocator.planner.result.text';
const DETAIL_KEY = 'tools.pacAllocator.planner.result.detail';

export function instructionText(order: PacOrderRow, translate: Translator, digits: CurrencyDigits): string {
    const instruction = order.instruction;
    if (instruction.kind === 'whole_quantity') {
        return translate(`${KEY}.buyUnits`, {default: 'buy {quantity} {count, plural, one {unit} other {units}}', values: {quantity: formatPlannerQuantity(instruction.quantity), count: plannerQuantityCount(instruction.quantity)}});
    }
    return translate(`${KEY}.buyAmount`, {default: 'buy for {amount}', values: {amount: formatPlannerMoneyPlain(instruction.amount.amount, instruction.amount.currency, {digits})}});
}

/** The order step is a Broker parameter, not wealth. */
export function instructionStepText(order: PacOrderRow, translate: Translator, digits: CurrencyDigits): string {
    const instruction = order.instruction;
    if (instruction.kind === 'whole_quantity') {
        return translate(`${KEY}.stepUnits`, {default: 'step {step} {count, plural, one {unit} other {units}}', values: {step: formatPlannerPlainDecimal(instruction.quantity_step), count: plannerPlainDecimalCount(instruction.quantity_step)}});
    }
    return translate(`${KEY}.stepAmount`, {default: 'step {step}', values: {step: formatPlannerPricePlain(instruction.order_amount_step.amount, instruction.order_amount_step.currency, digits)}});
}

/** A market price, with its quote base when it is not one unit. */
export function priceText(price: PacExactPrice, translate: Translator, digits: CurrencyDigits): string {
    const text = formatExactPricePlain(price, digits);
    if (compareDecimal(price.quote_base_quantity, '1') === 0) return text;
    return translate(`${KEY}.pricePer`, {default: '{price} per {quantity} {count, plural, one {unit} other {units}}', values: {price: text, quantity: formatPlannerPlainDecimal(price.quote_base_quantity), count: plannerPlainDecimalCount(price.quote_base_quantity)}});
}

/** The economic quantity of an order: wealth, so masked with privacy on. */
export function economicQuantityText(quantity: PacOrderRow['economic_quantity'], translate: Translator): string {
    const values = {quantity: formatExactQuantity(quantity.value), count: exactQuantityCount(quantity.value)};
    if (quantity.kind === 'exact') return translate(`${DETAIL_KEY}.quantityExact`, {default: '{quantity} {count, plural, one {unit} other {units}} (exact)', values});
    return translate(`${DETAIL_KEY}.quantityEstimated`, {default: '{quantity} {count, plural, one {unit} other {units}} (estimated)', values});
}

type RouteMinimum = PacResolvedOrderRoute['required_minimum'];
type RouteCap = PacResolvedOrderRoute['cap'];

function unitsText(quantity: string, translate: Translator): string {
    return translate(`${KEY}.units`, {default: '{quantity} {count, plural, one {unit} other {units}}', values: {quantity: formatPlannerQuantity(quantity), count: plannerQuantityCount(quantity)}});
}

/** A route minimum or cap is wealth, like the order it bounds: masked with privacy on. */
export function routeMinimumText(minimum: RouteMinimum, translate: Translator, digits: CurrencyDigits): string {
    if (minimum.kind === 'none') return translate(`${KEY}.none`, {default: 'none'});
    if (minimum.kind === 'whole_quantity') return unitsText(minimum.quantity, translate);
    return formatPlannerMoneyPlain(minimum.amount.amount, minimum.amount.currency, {digits});
}

export function routeCapText(cap: RouteCap, translate: Translator, digits: CurrencyDigits): string {
    if (cap.kind === 'none') return translate('tools.pacAllocator.planner.route.capNone', {default: 'no limit'});
    if (cap.kind === 'quantity') return unitsText(cap.quantity, translate);
    return formatPlannerMoneyPlain(cap.amount.amount, cap.amount.currency, {digits});
}

/** A request rate (fraction) as an exact percentage: `0.00125` → `0.125%`. Public. */
export function ratePercentText(fraction: string): string {
    const percent = fractionToPercent(fraction);
    return formatPlannerPercentUnits(percent, percent === null ? 2 : Math.min(6, Math.max(2, decimalScale(percent))));
}
