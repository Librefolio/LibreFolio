/**
 * chargesDeleteFlow — «Delete» on rows that may be parents with linked charges, before the Bulk (project 66, F6; shared
 * in F7-d). The Transactions page and the broker's Transactions tab both use it, each with its own
 * `TxChargesActionModal` bound to `panel`, `counts`, `choose` and `cancel`. Which rows the user may delete is the page's
 * filter, applied before `start`.
 *
 *   - `start(rows)`: without a parent among them, the Bulk opens at once on the delete. Otherwise the parents' charges
 *     are read (`parent_ids`) and added to the store, so the Bulk resolves them even when the list does not show them
 *     (filters, dates); a parent whose charges are not all selected opens the panel V1 and waits for the choice. A failed
 *     read calls `onReadFailed` and opens nothing.
 *   - `choose(choice)`: the panel closes and the Bulk opens on `deleteIntent` — with `chargeIds`, the charges chosen with
 *     their parent, so «Restore» on the parent in the Bulk takes them back.
 *   - `cancel()`: the panel closes, nothing opens.
 */
import {zodiosApi} from '$lib/api';
import {deletePlan, deleteIntent, type DeletePlanEntry} from './chargeLinkRules';
import {txStoreAddExtras} from './txStore.svelte';
import type {TXReadItem} from './types';
import type {WorkspaceIntent} from './bulk/TransactionBulkModal.svelte';

export interface ChargesDeleteFlowDeps {
    /** Open the Bulk on this intent. */
    openBulk: (intent: WorkspaceIntent) => void;
    /** The charges could not be read: the page tells the user (nothing opens). */
    onReadFailed: () => void;
}

/** The open panel: the ids the user chose to delete, and the parents whose charges are not all among them. */
export interface ChargesDeletePanel {
    ids: number[];
    plan: DeletePlanEntry[];
}

export interface ChargesDeleteFlow {
    readonly panel: ChargesDeletePanel | null;
    /** The panel's numbers, from the same intent the Bulk receives: a mixed selection counts right. */
    readonly counts: {keep: number; all: number} | undefined;
    start(rows: TXReadItem[]): Promise<void>;
    choose(choice: 'keep' | 'all'): void;
    cancel(): void;
}

export function createChargesDeleteFlow({openBulk, onReadFailed}: ChargesDeleteFlowDeps): ChargesDeleteFlow {
    let panel = $state<ChargesDeletePanel | null>(null);

    async function start(rows: TXReadItem[]): Promise<void> {
        const ids = rows.map((r) => r.id);
        const parents = rows.filter((r) => (r.charges_count ?? 0) > 0);
        if (parents.length === 0) {
            openBulk({action: 'delete', txIds: ids});
            return;
        }
        let charges: TXReadItem[];
        try {
            charges = ((await zodiosApi.query_transactions_api_v1_transactions_get({queries: {parent_ids: parents.map((p) => p.id)}} as never)) ?? []) as TXReadItem[];
        } catch {
            onReadFailed();
            return;
        }
        const byParent = new Map<number, TXReadItem[]>();
        for (const c of charges) {
            const parentId = c.parent_transaction_id ?? 0;
            if (parentId <= 0) continue;
            const list = byParent.get(parentId);
            if (list) list.push(c);
            else byParent.set(parentId, [c]);
        }
        txStoreAddExtras(charges);
        const plan = deletePlan(rows, byParent);
        if (plan.length === 0) {
            openBulk({action: 'delete', txIds: ids});
            return;
        }
        panel = {ids, plan};
    }

    function choose(choice: 'keep' | 'all'): void {
        const pending = panel;
        panel = null;
        if (!pending) return;
        openBulk({action: 'delete', ...deleteIntent(pending.ids, pending.plan, choice)});
    }

    function cancel(): void {
        panel = null;
    }

    return {
        get panel() {
            return panel;
        },
        get counts() {
            if (!panel) return undefined;
            return {keep: deleteIntent(panel.ids, panel.plan, 'keep').unlinkIds.length, all: deleteIntent(panel.ids, panel.plan, 'all').txIds.length};
        },
        start,
        choose,
        cancel,
    };
}
