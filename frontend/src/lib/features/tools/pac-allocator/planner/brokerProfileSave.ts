/**
 * «Save to the broker profile» (P3 of project 67, M10, D18, N4): the scenario's modes go back to the account.
 *
 * The planner never writes the profile blind. It re-reads the broker (`GET /brokers/{id}`), merges into the profile read
 * **only the currencies of the scenario** and the conversion mode (D18), lists what that changes, currency by currency
 * («EUR: updated · USD: new»), and writes (`PATCH /brokers/{id}`, the key `operating_profile` alone) only after the user
 * confirms that list (N4). The other currencies of the profile and its tax regime stay as they were; for the sale fees, see
 * the next paragraph.
 *
 * The sale fee of a currency the scenario changes. The planner shows and sends the purchase side only (`DraftMode`). A
 * stored rule whose sale fee is «same as the purchase» keeps that relation, so its sale fee follows the new purchase
 * fee; any other stored sale fee is kept as it is. A currency the profile does not have yet starts with the panel's
 * default for a new currency, «same as the purchase» (M21).
 *
 * `planProfileSave` is pure; `readStoredProfile` and `writeStoredProfile` are the two calls.
 */
import {zodiosApi} from '$lib/api';
import {DEFAULT_CONVERSION_MODE, fromDraft, newRule, toDraft, type ConversionMode, type OperatingProfileDocument, type ProfileDraft, type RuleDraft} from '$lib/features/brokers/profile/brokerOperatingProfile';
import {profileDraftOf} from './brokerProfileAdapter';
import type {DraftMode} from './draft.svelte';

export type ProfileSaveChange = {kind: 'currency'; currency: string; change: 'created' | 'updated'} | {kind: 'conversion'; mode: ConversionMode};

/** Where «Save to the broker profile» stands, as its banner shows it (`ProfileSaveConfirm.svelte`). */
export type ProfileSavePhase = 'reading' | 'confirm' | 'writing' | 'readFailed' | 'refused' | 'writeFailed' | 'saved';

export interface ProfileSavePlan {
    /** What the save changes, in the scenario's order; empty when the profile already says it all. */
    changes: ProfileSaveChange[];
    /** The whole document to write: the profile read, with the scenario's currencies and conversion merged in. */
    document: OperatingProfileDocument | null;
}

/** One rule as the document writes it: the comparison of «changed?» is on what would be saved. */
function rowOf(rule: RuleDraft): string {
    return JSON.stringify(fromDraft({rules: [rule], conversionMode: null, taxRegime: null})?.order_modes?.[0] ?? null);
}

/** The stored rule with the scenario's order type, increment and purchase fee; the sale side as the module comment says. */
function mergedRule(stored: RuleDraft, scenario: RuleDraft): RuleDraft {
    return {...stored, orderKind: scenario.orderKind, step: scenario.step, buy: {...scenario.buy}};
}

/** D18 and N4: the profile read, with the scenario's currencies and conversion mode merged in, and the list of changes. */
export function planProfileSave(stored: OperatingProfileDocument | null, modes: readonly DraftMode[], conversionMode: ConversionMode): ProfileSavePlan {
    const merged: ProfileDraft = toDraft(stored);
    const changes: ProfileSaveChange[] = [];
    for (const rule of profileDraftOf(modes, conversionMode).rules) {
        if (rule.currency === '') continue;
        const index = merged.rules.findIndex((item) => item.currency === rule.currency);
        if (index < 0) {
            merged.rules.push({...newRule(rule.currency), orderKind: rule.orderKind, step: rule.step, buy: {...rule.buy}, sellSameAsBuy: true});
            changes.push({kind: 'currency', currency: rule.currency, change: 'created'});
            continue;
        }
        const next = mergedRule(merged.rules[index], rule);
        if (rowOf(next) !== rowOf(merged.rules[index])) changes.push({kind: 'currency', currency: rule.currency, change: 'updated'});
        merged.rules[index] = next;
    }
    if ((merged.conversionMode ?? DEFAULT_CONVERSION_MODE) !== conversionMode) changes.push({kind: 'conversion', mode: conversionMode});
    merged.conversionMode = conversionMode;
    return {changes, document: fromDraft(merged)};
}

/** The broker's profile as stored now; throws when the broker cannot be read. */
export async function readStoredProfile(brokerId: number): Promise<OperatingProfileDocument | null> {
    const broker = (await zodiosApi.get_broker_api_v1_brokers__broker_id__get({params: {broker_id: brokerId}})) as {operating_profile?: OperatingProfileDocument | null};
    return broker.operating_profile ?? null;
}

export type ProfileWriteOutcome = {ok: true} | {ok: false; error: string | null};

/** Writes the whole document (D5: the key `operating_profile` alone, every other field of the broker untouched). */
export async function writeStoredProfile(brokerId: number, document: OperatingProfileDocument | null): Promise<ProfileWriteOutcome> {
    const response = await zodiosApi.update_broker_api_v1_brokers__broker_id__patch({operating_profile: document as never}, {params: {broker_id: brokerId}});
    const result = response.results[0];
    if (result?.success) return {ok: true};
    // A refusal carries one message, or a list of them (as the broker window reads it): the first is shown.
    const error = Array.isArray(result?.error) ? (result.error[0] ?? null) : (result?.error ?? null);
    return {ok: false, error};
}
