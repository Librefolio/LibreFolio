/**
 * The words of an order mode (order type, increment, purchase fee) and of a funding source, shared
 * by the Broker card, the Broker editor and the Routing step, so they never describe one differently.
 *
 * Keys stay literal in this file: `dev.py i18n audit` resolves only same-file string literals.
 */
import {canonicalInput, decimalScale, decimalSign} from './decimal';
import type {DraftMode, ModeKind} from './draft.svelte';
import {formatPlannerPercentUnits, formatPlannerPlainDecimal, formatPlannerPricePlain} from './format';
import {MODE_KIND_FALLBACKS} from './labels';

/** The `$t` store value, narrowed to what the planner passes. */
export type PlannerTranslate = (key: string, options?: {default?: string; values?: Record<string, string | number>}) => string;

export function modeKindText(tr: PlannerTranslate, kind: ModeKind): string {
    return tr(`tools.pacAllocator.planner.modeKinds.${kind}`, {default: MODE_KIND_FALLBACKS[kind]});
}

/** The unit of a minimum or cap on a route: shares for a quantity mode, the currency for an amount mode. */
export function modeUnitText(tr: PlannerTranslate, mode: DraftMode): string {
    return mode.kind === 'whole_quantity' ? tr('tools.pacAllocator.planner.units.shares', {default: 'units'}) : mode.currency;
}

/** «1 unit», «0.001 units» or «€0.01»: every proposed order is a multiple of it. */
export function modeIncrementText(tr: PlannerTranslate, mode: DraftMode): string {
    if (mode.kind === 'monetary_amount') return formatPlannerPricePlain(mode.step, mode.currency);
    const canonical = canonicalInput(mode.step);
    return tr('tools.pacAllocator.planner.brokers.stepUnits', {
        default: '{count, plural, one {{step} unit} other {{step} units}}',
        values: {step: formatPlannerPlainDecimal(canonical ?? mode.step), count: canonical === null ? 0 : Number(canonical)},
    });
}

/** What a source of liquidity is for a Broker: its own cash, another account's cash, or a contribution. */
export function fundingSourceHelp(tr: PlannerTranslate, kind: 'local' | 'account' | 'contribution', name: string, currency: string): string {
    return tr('tools.pacAllocator.planner.brokers.fundingChipHelp', {
        default:
            '{kind, select, local {The cash already on {name} in {currency}: the plan uses it here, with no transfer.} account {The cash of {name} in {currency}: you allowed it to pay for purchases on this Broker.} other {The contribution {name}: you allowed it to pay for purchases on this Broker.}}',
        values: {kind, name: name || '—', currency},
    });
}

/** Empty counts as zero; a value that is not a number is not zero, so it stays visible. */
function isZero(text: string): boolean {
    const canonical = canonicalInput(text);
    return canonical === null ? text.trim() === '' : decimalSign(canonical) === 0;
}

/**
 * The BUY fee of a mode as the Broker would print it: «none», «€1.00», «0.19% (min €2.95, max €18.00)»
 * or both joined by «+». The fee is 0 when nothing is bought, otherwise fixed + clamp(rate × amount,
 * min, max): min and max bound only the percentage, so they follow it.
 */
export function modeFeeText(tr: PlannerTranslate, mode: DraftMode): string {
    const hasCap = mode.cap.trim() !== '';
    if (isZero(mode.fixedFee) && isZero(mode.ratePercent) && isZero(mode.floor) && !hasCap) {
        return tr('tools.pacAllocator.planner.brokers.feeZero', {default: 'none'});
    }
    const parts: string[] = [];
    if (!isZero(mode.fixedFee)) parts.push(formatPlannerPricePlain(canonicalInput(mode.fixedFee) ?? mode.fixedFee, mode.currency));
    if (!isZero(mode.ratePercent) || !isZero(mode.floor) || hasCap) {
        const rate = canonicalInput(mode.ratePercent) ?? '0';
        const bounds: string[] = [];
        if (!isZero(mode.floor)) bounds.push(tr('tools.pacAllocator.planner.brokers.feeMin', {default: 'min {amount}', values: {amount: formatPlannerPricePlain(canonicalInput(mode.floor) ?? mode.floor, mode.currency)}}));
        if (hasCap) bounds.push(tr('tools.pacAllocator.planner.brokers.feeMax', {default: 'max {amount}', values: {amount: formatPlannerPricePlain(canonicalInput(mode.cap) ?? mode.cap, mode.currency)}}));
        const percent = formatPlannerPercentUnits(rate, Math.max(2, Math.min(6, decimalScale(rate))));
        parts.push(bounds.length === 0 ? percent : `${percent} (${bounds.join(', ')})`);
    }
    return parts.join(' + ');
}
