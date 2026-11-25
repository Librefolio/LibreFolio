/**
 * The broker's operating profile (P2 of project 67, contract §7): the panel's draft ↔ the document the API stores.
 *
 * The panel edits text fields — a fee rate in percent, an empty maximum for «none», a step as typed — and this module turns
 * them into the document of `backend/app/schemas/broker_profile.py` and back, exactly (`exactDecimal`: 0.19 % is
 * `"0.0019"`). One rule per currency (M21); the conversion mode and the tax regime are the broker's. The draft keeps every
 * group, shown or not: a panel that hides the sale fee or the regime hands them back untouched (P2, fact 8).
 *
 * The ids of the document are local labels (D3): `mode:<currency>`, `fee:<currency>:buy|sell`. A fee whose every amount is
 * zero is left out (an absent fee is zero); the cap is always written, `none` when the maximum is empty.
 *
 * No calculation: the checks are the shape refusals the backend makes (D4), said before sending.
 */
import {canonicalInput, compareDecimal, decimalSign, fractionToPercent, isWholeDecimal, percentToFraction} from '$lib/utils/core/exactDecimal';

export type ProfileGroup = 'orderMode' | 'buyFee' | 'sellFee' | 'conversion' | 'taxRegime';
export const PROFILE_GROUPS: readonly ProfileGroup[] = ['orderMode', 'buyFee', 'sellFee', 'conversion', 'taxRegime'];

export type ConversionMode = 'manual' | 'automatic';
/**
 * What a Broker with no conversion said does (TL-6 of project 67, the developer's choice of 23/11: «per tutti, prima di
 * essere specificato»): it converts by itself when the orders execute. The backend reads the same (`broker_profile.py`);
 * the panel marks it «default», and every planner fallback reads it from here.
 */
export const DEFAULT_CONVERSION_MODE: ConversionMode = 'automatic';
export type TaxRegime = 'administered' | 'declarative';
export type OrderKind = 'whole_quantity' | 'monetary_amount';

// -- the stored document (contract §7) -------------------------------------------------------------

export interface ProfileMoney {
    amount: string;
    currency: string;
}

export type ProfileCapability = {kind: 'whole_quantity'; capability_id: string; quantity_unit: 'asset_unit'; quantity_step: string} | {kind: 'monetary_amount'; capability_id: string; order_amount_step: ProfileMoney};

export interface ProfileFee {
    fee_schedule_id: string;
    capability_id: string;
    side: 'buy' | 'sell';
    fixed_fee?: ProfileMoney | null;
    rate?: string;
    variable_floor?: ProfileMoney | null;
    variable_cap?: {kind: 'none'} | {kind: 'amount'; amount: ProfileMoney};
}

export interface ProfileRow {
    currency: string;
    capability: ProfileCapability;
    fees?: ProfileFee[];
}

export interface OperatingProfileDocument {
    profile_version: 1;
    order_modes?: ProfileRow[];
    conversion_mode?: ConversionMode;
    tax_regime?: TaxRegime | null;
}

/** The regime a profile means: an absent one is `declarative` (M6, M18), the backend's `effective_tax_regime`, written once here. */
export function effectiveTaxRegime(profile: OperatingProfileDocument | null | undefined): TaxRegime {
    return profile?.tax_regime ?? 'declarative';
}

// -- the panel's draft -------------------------------------------------------------------------------

/** One fee as the panel shows it: every field a text; an empty field is zero, an empty maximum is «none». */
export interface FeeDraft {
    minimum: string;
    ratePercent: string;
    maximum: string;
    fixed: string;
}

export interface RuleDraft {
    /** A key of the panel's own, stable while the currency changes. */
    key: string;
    currency: string;
    orderKind: OrderKind;
    step: string;
    buy: FeeDraft;
    sell: FeeDraft;
    /** The sale fee is the purchase fee (the box «same as the purchase»). */
    sellSameAsBuy: boolean;
}

export interface ProfileDraft {
    rules: RuleDraft[];
    /** `null`: not chosen; the document leaves the key out (the backend reads `automatic`, `DEFAULT_CONVERSION_MODE`). */
    conversionMode: ConversionMode | null;
    /** `null`: not chosen; the document leaves the key out (it reads `declarative`, M6, M18). */
    taxRegime: TaxRegime | null;
}

let ruleCounter = 0;

const emptyFee = (): FeeDraft => ({minimum: '', ratePercent: '', maximum: '', fixed: ''});

/** A new rule for `currency`: whole units by one, no fee, the sale fee the purchase's. */
export function newRule(currency = ''): RuleDraft {
    ruleCounter += 1;
    return {key: `rule-${ruleCounter}`, currency, orderKind: 'whole_quantity', step: '1', buy: emptyFee(), sell: emptyFee(), sellSameAsBuy: true};
}

function feeDraft(fee: ProfileFee | undefined): FeeDraft {
    if (!fee) return emptyFee();
    const cap = fee.variable_cap?.kind === 'amount' ? fee.variable_cap.amount.amount : '';
    return {
        minimum: fee.variable_floor?.amount ?? '',
        ratePercent: fee.rate && decimalSign(fee.rate) !== 0 ? (fractionToPercent(fee.rate) ?? fee.rate) : '',
        maximum: cap,
        fixed: fee.fixed_fee?.amount ?? '',
    };
}

/** The canonical value of an amount field, or `null` for an empty or zero one. */
function amount(text: string): string | null {
    const value = canonicalInput(text);
    return value === null || decimalSign(value) === 0 ? null : value;
}

function sameFee(a: FeeDraft, b: FeeDraft): boolean {
    return JSON.stringify(feeValues(a)) === JSON.stringify(feeValues(b));
}

function feeValues(fee: FeeDraft): (string | null)[] {
    return [amount(fee.minimum), amount(fee.ratePercent), canonicalInput(fee.maximum), amount(fee.fixed)];
}

/** The panel's draft of a stored profile; an empty draft for `null`. */
export function toDraft(document: OperatingProfileDocument | null | undefined): ProfileDraft {
    const rules = (document?.order_modes ?? []).map((row): RuleDraft => {
        const buy = feeDraft(row.fees?.find((fee) => fee.side === 'buy'));
        const sell = feeDraft(row.fees?.find((fee) => fee.side === 'sell'));
        const step = row.capability.kind === 'whole_quantity' ? row.capability.quantity_step : row.capability.order_amount_step.amount;
        return {...newRule(row.currency), orderKind: row.capability.kind, step, buy, sell, sellSameAsBuy: sameFee(buy, sell)};
    });
    return {rules, conversionMode: document?.conversion_mode ?? null, taxRegime: document?.tax_regime ?? null};
}

function documentFee(fee: FeeDraft, currency: string, side: 'buy' | 'sell'): ProfileFee | null {
    const minimum = amount(fee.minimum);
    const rate = amount(fee.ratePercent);
    const maximum = canonicalInput(fee.maximum);
    const fixed = amount(fee.fixed);
    if (minimum === null && rate === null && maximum === null && fixed === null) return null;
    const capabilityId = `mode:${currency}`;
    return {
        fee_schedule_id: `fee:${currency}:${side}`,
        capability_id: capabilityId,
        side,
        ...(fixed === null ? {} : {fixed_fee: {amount: fixed, currency}}),
        ...(rate === null ? {} : {rate: percentToFraction(rate) as string}),
        ...(minimum === null ? {} : {variable_floor: {amount: minimum, currency}}),
        variable_cap: maximum === null ? {kind: 'none'} : {kind: 'amount', amount: {amount: maximum, currency}},
    };
}

function documentRow(rule: RuleDraft): ProfileRow {
    const currency = rule.currency;
    const capabilityId = `mode:${currency}`;
    const step = canonicalInput(rule.step) ?? rule.step;
    const capability: ProfileCapability = rule.orderKind === 'whole_quantity' ? {kind: 'whole_quantity', capability_id: capabilityId, quantity_unit: 'asset_unit', quantity_step: step} : {kind: 'monetary_amount', capability_id: capabilityId, order_amount_step: {amount: step, currency}};
    const fees = [documentFee(rule.buy, currency, 'buy'), documentFee(rule.sellSameAsBuy ? rule.buy : rule.sell, currency, 'sell')].filter((fee): fee is ProfileFee => fee !== null);
    return {currency, capability, fees};
}

/**
 * The document a draft saves, or `null` when the panel says nothing the backend's defaults do not say already: no rule, no
 * regime, and the conversion absent or the default (`automatic`, TL-6). The backend serves `conversion_mode` always, so a
 * saved profile cleared of its rules goes back to «no profile», not to a document that only repeats the default; «Converti
 * tu» is saved, even alone.
 */
export function fromDraft(draft: ProfileDraft): OperatingProfileDocument | null {
    if (draft.rules.length === 0 && draft.taxRegime === null && (draft.conversionMode === null || draft.conversionMode === DEFAULT_CONVERSION_MODE)) return null;
    return {
        profile_version: 1,
        order_modes: draft.rules.map(documentRow),
        ...(draft.conversionMode === null ? {} : {conversion_mode: draft.conversionMode}),
        ...(draft.taxRegime === null ? {} : {tax_regime: draft.taxRegime}),
    };
}

/** Same values, same document: the panel's «changed?» compares what would be saved. */
export function draftsEqual(a: ProfileDraft, b: ProfileDraft): boolean {
    return JSON.stringify(fromDraft(a)) === JSON.stringify(fromDraft(b));
}

export type ProfileProblemKey = 'currencyMissing' | 'notANumber' | 'stepNotPositive' | 'stepNotWhole' | 'feeNegative';
export type ProfileField = 'currency' | 'step' | `${'buy' | 'sell'}.${keyof FeeDraft}`;

export interface ProfileProblem {
    ruleKey: string;
    field: ProfileField;
    key: ProfileProblemKey;
}

/** The backend's shape refusals (D4), said before sending: one per field, in the rule's order. */
export function profileProblems(draft: ProfileDraft): ProfileProblem[] {
    const problems: ProfileProblem[] = [];
    for (const rule of draft.rules) {
        const add = (field: ProfileField, key: ProfileProblemKey) => problems.push({ruleKey: rule.key, field, key});
        if (!/^[A-Z]{3}$/.test(rule.currency)) add('currency', 'currencyMissing');
        const step = canonicalInput(rule.step);
        if (step === null) add('step', 'notANumber');
        else if (decimalSign(step) !== 1) add('step', 'stepNotPositive');
        else if (rule.orderKind === 'whole_quantity' && !isWholeDecimal(step)) add('step', 'stepNotWhole');
        const sides: ('buy' | 'sell')[] = rule.sellSameAsBuy ? ['buy'] : ['buy', 'sell'];
        for (const side of sides) {
            for (const name of ['minimum', 'ratePercent', 'maximum', 'fixed'] as const) {
                const text = rule[side][name];
                if (text.trim() === '') continue;
                const value = canonicalInput(text);
                if (value === null) add(`${side}.${name}`, 'notANumber');
                else if (compareDecimal(value, '0') === -1) add(`${side}.${name}`, 'feeNegative');
            }
        }
    }
    return problems;
}

/** «Copy the rules from another currency» (M21): a new rule for `currency` with the rules of `fromKey`; never a second rule for a currency. */
export function copyRules(draft: ProfileDraft, fromKey: string, currency: string): boolean {
    const source = draft.rules.find((rule) => rule.key === fromKey);
    if (!source || draft.rules.some((rule) => rule.currency === currency)) return false;
    draft.rules.push({...newRule(currency), orderKind: source.orderKind, step: source.step, buy: {...source.buy}, sell: {...source.sell}, sellSameAsBuy: source.sellSameAsBuy});
    return true;
}
