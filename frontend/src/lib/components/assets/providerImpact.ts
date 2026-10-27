/**
 * What changing or removing an asset's provider would delete, asked of the server before it is done (lot X5-1: C-65a, W-B2, X-R69).
 *
 * «Change the provider or its parameters» and «remove the provider» follow one rule: the modal tells how many prices and
 * provider-generated events go and how many transactions lose the link to a deleted event (they are kept), and on confirm
 * both proceed. The numbers come from the dry run `POST /assets/provider/impact`, which writes nothing. This module asks,
 * decides whether there is anything to say, and words the numbers; the dialog itself is `AssetModal.svelte`'s.
 *
 * The dry run is advice, never a gate: when it fails, or finds nothing to lose, the save goes on without a dialog and the
 * server judges the real call. A change the server will refuse (a SPLIT with adjustments without a purchase cost) is also
 * left to that call, which says the refusal inline (`currencyChangeErrors.ts`).
 *
 * @module components/assets/providerImpact
 */

import {zodiosApi} from '$lib/api';
import type {buildProviderAssignItem} from './assetPayload';

export type ProviderImpactKind = 'regenerate' | 'switch' | 'remove';

export interface ProviderImpact {
    kind: ProviderImpactKind;
    pricesDeleted: number;
    eventsDeleted: number;
    transactionsUnlinked: number;
}

export type ProviderChange = {action: 'assign'; item: ReturnType<typeof buildProviderAssignItem>} | {action: 'remove'};

type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

const KIND_OF_REASON: Readonly<Record<string, ProviderImpactKind>> = {
    params_changed: 'regenerate',
    provider_changed: 'switch',
    provider_removed: 'remove',
};

function asRecord(value: unknown): Record<string, unknown> | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function count(value: unknown): number {
    const n = Number(value);
    return Number.isFinite(n) && n > 0 ? n : 0;
}

/**
 * The dry run for one asset, as the dialog needs it; null when there is nothing to tell: nothing is lost, the real call
 * will be refused (it says so itself), or the request failed. Never throws.
 */
export async function loadProviderImpact(assetId: number, change: ProviderChange): Promise<ProviderImpact | null> {
    const body = change.action === 'assign' ? {assignments: [change.item], removals: []} : {assignments: [], removals: [assetId]};
    let answer: unknown;
    try {
        answer = await zodiosApi.provider_change_impact_api_v1_assets_provider_impact_post(body as never);
    } catch (error) {
        console.warn('Could not measure what the provider change deletes; the save goes on without the count:', error);
        return null;
    }
    const results = asRecord(answer)?.results;
    const found = (Array.isArray(results) ? results : []).map(asRecord).find((item) => item !== null && item.asset_id === assetId && item.action === change.action);
    if (!found) return null;
    const kind = typeof found.reason === 'string' ? KIND_OF_REASON[found.reason] : undefined;
    if (!kind) return null;
    if (Array.isArray(found.blocking_splits) && found.blocking_splits.length > 0) return null;
    const impact: ProviderImpact = {kind, pricesDeleted: count(found.prices_deleted), eventsDeleted: count(found.events_deleted), transactionsUnlinked: count(found.transactions_unlinked)};
    return impact.pricesDeleted + impact.eventsDeleted + impact.transactionsUnlinked > 0 ? impact : null;
}

/** The values of a dialog's message: `what` goes (prices, events), `unlinked` is the sentence about the transactions, or empty. */
export function impactValues(impact: ProviderImpact, t: Translate, locale: string): {what: string; unlinked: string} {
    const parts: string[] = [];
    if (impact.pricesDeleted > 0) parts.push(t('assets.modal.providerImpact.pricesPart', {values: {n: impact.pricesDeleted}}));
    if (impact.eventsDeleted > 0) parts.push(t('assets.modal.providerImpact.eventsPart', {values: {n: impact.eventsDeleted}}));
    return {
        what: new Intl.ListFormat(locale, {style: 'long', type: 'conjunction'}).format(parts),
        unlinked: impact.transactionsUnlinked > 0 ? t('assets.modal.providerImpact.unlinkedSentence', {values: {n: impact.transactionsUnlinked}}) : '',
    };
}

/** The catalogue keys and the test id of each kind's dialog: every key a whole literal, for the i18n audit. */
export const IMPACT_DIALOG: Readonly<Record<ProviderImpactKind, {title: string; message: string; confirm: string; testId: string}>> = {
    regenerate: {
        title: 'assets.modal.providerImpact.regenerateTitle',
        message: 'assets.modal.providerImpact.regenerateMessage',
        confirm: 'assets.modal.providerImpact.regenerateConfirm',
        testId: 'asset-scheduled-regen-confirm',
    },
    switch: {
        title: 'assets.modal.providerImpact.switchTitle',
        message: 'assets.modal.providerImpact.switchMessage',
        confirm: 'assets.modal.providerImpact.switchConfirm',
        testId: 'asset-parametric-switch-confirm',
    },
    remove: {
        title: 'assets.modal.providerImpact.removeTitle',
        message: 'assets.modal.providerImpact.removeMessage',
        confirm: 'assets.modal.providerImpact.removeConfirm',
        testId: 'asset-provider-remove-confirm',
    },
};
