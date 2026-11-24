/**
 * The Rebalancer's part of the request (F3a of project 67, step 11; contract 2.0.0 §5.2, §5.4).
 *
 * `buildRequest` writes one request for both Tools; under the Rebalancer's profile it takes from here what only the
 * Rebalancer sends:
 *   - `holdings`: the user's positions (custody, share, planning quantity); a copied position whose planning quantity the
 *     user changed travels with a manual provenance, one still equal to its copy with the copy's;
 *   - the Brokers that only hold positions (not among the scenario's Brokers): their identity and no order mode, so they
 *     can hold and cannot buy (Q-F3a-5b, the consultant's (a); `capabilities` and `fee_schedules` default to empty);
 *   - the cash entries of the targets (`kind: cash`: weight, minimum, maximum);
 *   - the target fidelity (a level, `custom` with the λ the draft keeps, `target_first`).
 * No funding route (the normalizer generates deposits and transfers) and no `tax` section before F3b. No calculation: every
 * value is a typed text sent as exact decimal.
 */
import {canonicalInput, decimalSign, percentToFraction} from '$lib/utils/core/exactDecimal';
import {positionIsCopied, type CopyRef, type DraftFidelity, type DraftPosition, type PlannerDraft} from './draft.svelte';
import {wireLimit} from './limits';
import type {PlannerStep} from './types';

type Copied = (stamp: CopyRef, step: PlannerStep, entityKey: string) => string;
type Manual = (entityKey: string, suffix: string, label: string, enteredAt: string, step: PlannerStep) => string;

/** A planning quantity the request can carry: a number from zero. */
export function positionQuantityValid(position: DraftPosition): boolean {
    const value = canonicalInput(position.quantity);
    return value !== null && decimalSign(value) !== -1;
}

/** The positions the request carries: those of an Asset still in the scenario (the Review counts the same). */
export function requestPositions(draft: PlannerDraft): DraftPosition[] {
    return draft.data.positions.filter((position) => draft.asset(position.assetKey) !== undefined);
}

/** The positions as the request's holdings. */
export function rebalancerHoldings(draft: PlannerDraft, copied: Copied, manual: Manual) {
    return requestPositions(draft).map((position) => ({
        holding_id: position.key,
        asset_id: position.assetKey,
        broker_id: position.brokerKey,
        custody_quantity: canonicalInput(position.custody) as string,
        economic_share: canonicalInput(position.ownershipShare) as string,
        planning_quantity: canonicalInput(position.quantity) as string,
        quantity_unit: 'asset_unit' as const,
        provenance_id: positionIsCopied(position) ? copied(position.stamp, 'assets', position.key) : manual(position.key, '/quantity', 'manual position quantity', position.enteredAt, 'assets'),
    }));
}

/** The Brokers that hold a position and are not among the scenario's Brokers: identity only, no order mode. */
export function positionOnlyBrokers(draft: PlannerDraft, copied: Copied) {
    const seen = new Set(draft.data.brokers.map((broker) => broker.key));
    const brokers = [];
    for (const position of draft.data.positions) {
        if (seen.has(position.brokerKey) || draft.asset(position.assetKey) === undefined) continue;
        seen.add(position.brokerKey);
        brokers.push({
            broker_id: position.brokerKey,
            identity: {kind: 'domain_broker' as const, source_broker_id: String(position.sourceBrokerId), name: position.brokerName.trim().slice(0, 128), active: true},
            provenance_id: copied(position.stamp, 'brokers', position.brokerKey),
            conversion_mode: 'manual' as const,
        });
    }
    return brokers;
}

/** The cash entries of the targets: a weight (an empty field is 0) and, each optional, a minimum and a maximum. */
export function cashTargetEntries(draft: PlannerDraft) {
    const data = draft.data;
    return data.cashEntries.map((entry) => {
        const weight = data.targets[entry.key]?.trim() ? data.targets[entry.key] : '0';
        const minimum = wireLimit(data.limits[entry.key]?.minimum, data.valuationCurrency);
        const maximum = wireLimit(data.limits[entry.key]?.maximum, data.valuationCurrency);
        return {
            kind: 'cash' as const,
            broker_id: entry.brokerKey,
            currency: entry.currency,
            weight: percentToFraction(canonicalInput(weight) as string) as string,
            ...(minimum ? {minimum} : {}),
            ...(maximum ? {maximum} : {}),
        };
    });
}

/**
 * The target fidelity on the wire. The preview always sends «Balanced»: no number it answers depends on the fidelity, and
 * the page keys it without the fidelity (R1-F (b) of project 67), so a λ it would refuse can never leave it unanswered.
 * The plan sends the draft's.
 */
export function wireFidelity(fidelity: DraftFidelity, preview = false) {
    if (preview) return {kind: 'level' as const, level: 'balanced' as const};
    if (fidelity.kind === 'custom') return {kind: 'custom' as const, lambda: canonicalInput(fidelity.lambda) as string};
    return fidelity.kind === 'level' ? {kind: 'level' as const, level: fidelity.level} : {kind: 'target_first' as const};
}
