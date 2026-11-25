/**
 * The planner's order modes ↔ the broker's operating profile (P3 of project 67).
 *
 * The only place where the planner knows the shape of the shared panel (`features/brokers/profile`): a planner mode is a
 * currency, an order kind, a step and the **purchase** fee, in the draft's own text fields (`DraftMode`); the panel's
 * rule carries the sale fee too, which the planner neither shows nor sends. Pure: no calculation, only fields moved
 * across. The panel writes an empty fee field for zero, the planner `'0'` (`DEFAULT_FEE`); the cap stays empty for «none»
 * on both sides.
 */
import {DEFAULT_CONVERSION_MODE, toDraft, type ConversionMode, type OperatingProfileDocument, type ProfileDraft, type RuleDraft} from '$lib/features/brokers/profile/brokerOperatingProfile';
import {DEFAULT_FEE} from './defaults';
import type {DraftMode} from './draft.svelte';

function orZero(text: string, zero: string): string {
    return text.trim() === '' ? zero : text;
}

/** A panel rule as a planner mode: its purchase fee, with the planner's zero for an empty field. */
function modeFromRule(rule: RuleDraft, key: string): DraftMode {
    return {
        key,
        currency: rule.currency,
        kind: rule.orderKind,
        step: rule.step,
        fixedFee: orZero(rule.buy.fixed, DEFAULT_FEE.fixed),
        ratePercent: orZero(rule.buy.ratePercent, DEFAULT_FEE.ratePercent),
        floor: orZero(rule.buy.minimum, DEFAULT_FEE.floor),
        cap: rule.buy.maximum,
    };
}

/**
 * The modes of a stored profile, one per rule, keys from `nextKey`; `null` when the profile has no order mode (D11: the
 * planner then gives its default modes, as without a profile).
 */
export function modesFromProfile(profile: OperatingProfileDocument | null, nextKey: () => string): DraftMode[] | null {
    const rules = toDraft(profile).rules;
    return rules.length === 0 ? null : rules.map((rule) => modeFromRule(rule, nextKey()));
}

/**
 * The panel's draft of a Broker's modes: one rule per mode, keyed by the mode's own key so the way back keeps it (the
 * request's capability ids and the issues' routing read it). The sale side is empty and «same as the purchase»: the
 * planner neither shows nor sends it; the regime is not chosen.
 */
export function profileDraftOf(modes: readonly DraftMode[], conversionMode: ConversionMode): ProfileDraft {
    return {
        rules: modes.map(
            (mode): RuleDraft => ({
                key: mode.key,
                currency: mode.currency,
                orderKind: mode.kind,
                step: mode.step,
                buy: {minimum: mode.floor, ratePercent: mode.ratePercent, maximum: mode.cap, fixed: mode.fixedFee},
                sell: {minimum: '', ratePercent: '', maximum: '', fixed: ''},
                sellSameAsBuy: true,
            }),
        ),
        conversionMode,
        taxRegime: null,
    };
}

/**
 * The key of the mode a rule becomes: a rule that came from a mode keeps that mode's key; a rule added in the panel takes
 * a new one from `nextKey` once, and keeps it at every later edit.
 */
export function modeKeys(knownKeys: Iterable<string>, nextKey: () => string): (ruleKey: string) => string {
    const known = new Set(knownKeys);
    const added = new Map<string, string>();
    return (ruleKey) => {
        if (known.has(ruleKey)) return ruleKey;
        let key = added.get(ruleKey);
        if (key === undefined) {
            key = nextKey();
            added.set(ruleKey, key);
        }
        return key;
    };
}

/** The modes of a panel draft; the conversion mode the panel leaves unchosen is the planner's default, `manual`. */
export function modesOf(draft: ProfileDraft, keyFor: (ruleKey: string) => string): {modes: DraftMode[]; conversionMode: ConversionMode} {
    return {
        modes: draft.rules.map((rule) => modeFromRule(rule, keyFor(rule.key))),
        conversionMode: draft.conversionMode ?? DEFAULT_CONVERSION_MODE,
    };
}
