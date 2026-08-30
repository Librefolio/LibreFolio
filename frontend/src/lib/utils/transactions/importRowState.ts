/**
 * Pure per-row state predicates for the import wizard's review step (Step 4).
 *
 * Extracted from `ImportWizardModal.svelte`: deciding whether a parsed row predates its
 * broker's opening date, or still points at an unresolved fake asset, is input→output
 * logic that the component was reaching only through the full wizard. The component keeps
 * one-line wrappers that inject its `parseResults`, `brokers` and `assetResolutions`.
 */
import {isFakeAssetId} from '$lib/utils/brim/isFakeAssetId';
import type {AssetResolution, MergedTx} from './importTypes';

/** The minimum a parse result must expose to map a row back to its broker. */
export interface RowBrokerSource {
    fileId: string;
    brokerId: number;
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

/** True unless the row's asset is an unresolved fake mapping (no bound real asset yet). */
export function isRowAssetResolved(t: MergedTx, assetResolutions: AssetResolution[]): boolean {
    if (typeof t.tx.asset_id === 'number' && isFakeAssetId(t.tx.asset_id)) {
        return assetResolutions.find((r) => r.fakeAssetId === t.tx.asset_id)?.resolvedAssetId != null;
    }
    return true;
}
