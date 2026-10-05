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
import {formatExactPricePlain, formatPlannerMoneyPlain, formatPlannerPercentUnits, formatPlannerPlainDecimal, formatPlannerPricePlain, formatPlannerQuantity, type CurrencyDigits} from '../format';
import type {PacExactPrice, PacOrderRow, PacResolvedOrderRoute} from '../types';

export type Translator = typeof t extends Readable<infer Formatter> ? Formatter : never;

const KEY = 'tools.pacAllocator.planner.result.text';

export function instructionText(order: PacOrderRow, translate: Translator, digits: CurrencyDigits): string {
    const instruction = order.instruction;
    if (instruction.kind === 'whole_quantity') {
        return translate(`${KEY}.buyUnits`, {default: 'buy {quantity} units', values: {quantity: formatPlannerQuantity(instruction.quantity)}});
    }
    return translate(`${KEY}.buyAmount`, {default: 'buy for {amount}', values: {amount: formatPlannerMoneyPlain(instruction.amount.amount, instruction.amount.currency, {digits})}});
}

/** The order step is a Broker parameter, not wealth. */
export function instructionStepText(order: PacOrderRow, translate: Translator, digits: CurrencyDigits): string {
    const instruction = order.instruction;
    if (instruction.kind === 'whole_quantity') {
        return translate(`${KEY}.stepUnits`, {default: 'step {step} units', values: {step: formatPlannerPlainDecimal(instruction.quantity_step)}});
    }
    return translate(`${KEY}.stepAmount`, {default: 'step {step}', values: {step: formatPlannerPricePlain(instruction.order_amount_step.amount, instruction.order_amount_step.currency, digits)}});
}

/** A market price, with its quote base when it is not one unit. */
export function priceText(price: PacExactPrice, translate: Translator, digits: CurrencyDigits): string {
    const text = formatExactPricePlain(price, digits);
    if (compareDecimal(price.quote_base_quantity, '1') === 0) return text;
    return translate(`${KEY}.pricePer`, {default: '{price} per {quantity} units', values: {price: text, quantity: formatPlannerPlainDecimal(price.quote_base_quantity)}});
}

type RouteMinimum = PacResolvedOrderRoute['required_minimum'];
type RouteCap = PacResolvedOrderRoute['cap'];

/** A route minimum: wealth by default until R7 decides otherwise. */
export function routeMinimumText(minimum: RouteMinimum, translate: Translator, digits: CurrencyDigits): string {
    if (minimum.kind === 'none') return translate(`${KEY}.none`, {default: 'none'});
    if (minimum.kind === 'whole_quantity') return translate(`${KEY}.units`, {default: '{quantity} units', values: {quantity: formatPlannerQuantity(minimum.quantity)}});
    return formatPlannerMoneyPlain(minimum.amount.amount, minimum.amount.currency, {digits});
}

export function routeCapText(cap: RouteCap, translate: Translator, digits: CurrencyDigits): string {
    if (cap.kind === 'none') return translate('tools.pacAllocator.planner.route.capNone', {default: 'no limit'});
    if (cap.kind === 'quantity') return translate(`${KEY}.units`, {default: '{quantity} units', values: {quantity: formatPlannerQuantity(cap.quantity)}});
    return formatPlannerMoneyPlain(cap.amount.amount, cap.amount.currency, {digits});
}

/** A request rate (fraction) as an exact percentage: `0.00125` → `0.125%`. Public. */
export function ratePercentText(fraction: string): string {
    const percent = fractionToPercent(fraction);
    return formatPlannerPercentUnits(percent, percent === null ? 2 : Math.min(6, Math.max(2, decimalScale(percent))));
}
