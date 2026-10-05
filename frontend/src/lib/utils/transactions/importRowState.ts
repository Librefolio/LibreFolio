/**
 * Pure per-row state predicates for the import wizard's review step (Step 4).
 *
 * Extracted from `ImportWizardModal.svelte`: deciding whether a parsed row predates its
 * broker's opening date, or still points at an unresolved fake asset, is input→output
 * logic that the component was reaching only through the full wizard. The component keeps
 * one-line wrappers that inject its `parseResults`, `brokers` and `assetResolutions`.
 */
import {isFakeAssetId} from '$lib/utils/brim/isFakeAssetId';
import {duplicateStatusAllowsAutoSelect} from './importDedup';
import type {AssetResolution, MergedTx} from './importTypes';

/** The minimum a parse result must expose to map a row back to its broker (and to its broker history). */
export interface RowBrokerSource {
    fileId: string;
    brokerId: number;
    /** The parse response; a report set's carries `history_start` (H0). */
    response?: {history_start?: unknown} | null;
}

/** The minimum a broker must expose for the opening-date cutoff. */
export interface BrokerOpening {
    id: number;
    opened_at?: string | null;
}

/** The broker a row's source file was parsed against, or null if the file is unknown. */
export function brokerIdForTx(mt: MergedTx, parseResults: RowBrokerSource[]): number | null {
    return parseResults.find((r) => r.fileId === mt.sourceFileId)?.brokerId ?? null;
}

/** Broker id + opening date for a row, or null when either the broker or its opening date is unknown. */
export function beforeOpeningInfo(mt: MergedTx, parseResults: RowBrokerSource[], brokers: BrokerOpening[]): {brokerId: number; openedAt: string} | null {
    const brokerId = brokerIdForTx(mt, parseResults);
    if (brokerId === null) return null;
    const openedAt = brokers.find((b) => b.id === brokerId)?.opened_at ?? null;
    if (!openedAt) return null;
    return {brokerId, openedAt};
}

/**
 * Whether a row is dated strictly before its broker opened. Strict `<`: a tx dated exactly
 * on the opening day (e.g. patrimonio opening seeds) is importable; only strictly-earlier
 * movements are flagged before-opening.
 */
export function isBeforeOpening(mt: MergedTx, parseResults: RowBrokerSource[], brokers: BrokerOpening[]): boolean {
    const info = beforeOpeningInfo(mt, parseResults, brokers);
    const txDate = mt.tx.date ? String(mt.tx.date) : '';
    return info !== null && txDate !== '' && txDate < info.openedAt;
}

/** The first day of the broker history LibreFolio already holds (H0), from the parse of the row's file; null when unknown. */
export function historyStartFor(mt: MergedTx, parseResults: RowBrokerSource[]): string | null {
    const start = parseResults.find((r) => r.fileId === mt.sourceFileId)?.response?.history_start;
    return typeof start === 'string' && start !== '' ? start.slice(0, 10) : null;
}

/**
 * Whether a row predates the broker history LibreFolio already holds (a report set's H0).
 * Strict `<`: a row dated on H0 is inside the history, and the duplicate check judges it.
 * Earlier rows are already represented — by the earlier imports, or on a first import by the
 * opening correction — so the review hides them and never imports them.
 */
export function isBeforeHistory(mt: MergedTx, parseResults: RowBrokerSource[]): boolean {
    const start = historyStartFor(mt, parseResults);
    const txDate = mt.tx.date ? String(mt.tx.date).slice(0, 10) : '';
    return start !== null && txDate !== '' && txDate < start;
}

/** True unless the row's asset is an unresolved fake mapping (no bound real asset yet). */
export function isRowAssetResolved(t: MergedTx, assetResolutions: AssetResolution[]): boolean {
    if (typeof t.tx.asset_id === 'number' && isFakeAssetId(t.tx.asset_id)) {
        return assetResolutions.find((r) => r.fakeAssetId === t.tx.asset_id)?.resolvedAssetId != null;
    }
    return true;
}

/**
 * Whether the wizard's re-check pass may (re-)select a row for import (W7):
 * not already selected, not before its broker's opening, its fake asset
 * resolved, and its duplicate verdict allowing it.
 *
 * This single predicate is the whole gate `reselectImportableRows()` applies,
 * and it runs from TWO triggers — `recheckOpenings` (broker-opening fixed) and
 * `resolveAsset`/`clearResolution` (asset assigned) — because either fix alone
 * may leave the other gate closed: a row that is before-opening AND unresolved
 * stays deselected when the broker is fixed first, and only becomes importable
 * when the asset lands. Extracted so that two-trigger contract is testable
 * without mounting the wizard.
 */
export function shouldAutoSelectOnRecheck(t: MergedTx, parseResults: RowBrokerSource[], brokers: BrokerOpening[], assetResolutions: AssetResolution[]): boolean {
    return !t.selected && !isBeforeOpening(t, parseResults, brokers) && !isBeforeHistory(t, parseResults) && isRowAssetResolved(t, assetResolutions) && duplicateStatusAllowsAutoSelect(t.duplicateStatus);
}
