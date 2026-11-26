/**
 * chargesUnlinkFlow — «Unlink the charges» from a table's selection bar (project 66, TL-9), sibling of `chargesLinkFlow`.
 * The Transactions page and the broker's Transactions tab both use it, each with its own
 * `TxChargesActionModal mode="unlink"` bound to `open`, `charges`, `unlinking`, `confirm` and `cancel`, and its `action` in
 * the selection bar. The Bulk has its own «Unlink», which saves nothing until «Save all» (`unlinkSelectedCharges`).
 *
 *   - `action`: `unlink-charges`. It takes the selected rows `isUnlinkable` says (a saved parent, a broker the user edits)
 *     and shows their number; without one it is hidden, and it is never off. A selected parent brings none of its charges.
 *     The type rules are not needed, so they are never asked for (the broker's page opens without them).
 *   - Its click fixes those rows and opens the panel: the panel and the commit are about the rows the user saw.
 *   - `confirm()`: one commit (`unlinkCommit`). Committed → the panel closes, `tx.charges.unlinked` is sent (the rows show
 *     the outcome: no toast) and `onUnlinked` runs (the page empties its selection and reloads). Refused → a toast with the
 *     reasons, the panel stays open. While it saves, a second `confirm()` does nothing and `cancel()` does not close.
 *   - `cancel()`: the panel closes, nothing is saved.
 */
import {fromStore} from 'svelte/store';
import {Unlink} from 'lucide-svelte';
import {_} from '$lib/i18n';
import {notify} from '$lib/stores/app/notify.svelte';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {canEditBroker} from '$lib/stores/reference/brokerStore';
import type {BulkAction} from '$lib/components/table/types';
import {commitTransactions} from './txCommitApi';
import {commitRefusalMessage} from './commitRefusal';
import {isUnlinkable, unlinkCommit} from './chargeLinkRules';
import {storeIssueContext} from './chargesLinkFlow.svelte';
import type {ResolverContext} from './resolveValidationMessage';
import type {TXReadItem} from './types';

export interface ChargesUnlinkFlowDeps {
    /** The charges were unlinked: the page empties its selection and reloads. */
    onUnlinked: () => Promise<void>;
    /** What a refusal's reasons name (brokers, assets). Absent: the broker and asset stores. */
    issueContext?: () => ResolverContext;
}

export interface ChargesUnlinkFlow {
    /** The panel is open. */
    readonly open: boolean;
    /** The charges fixed at the click. */
    readonly charges: TXReadItem[];
    /** The commit is in flight. */
    readonly unlinking: boolean;
    /** The selection bar's entry. */
    readonly action: BulkAction<TXReadItem>;
    confirm(): Promise<void>;
    cancel(): void;
}

export function createChargesUnlinkFlow({onUnlinked, issueContext}: ChargesUnlinkFlowDeps): ChargesUnlinkFlow {
    const translate = fromStore(_);
    const t = (key: string, fallback: string): string => translate.current(key) || fallback;
    const takes = (row: TXReadItem): boolean => isUnlinkable(row, (brokerId) => canEditBroker(brokerId));

    let charges = $state.raw<TXReadItem[]>([]);
    let open = $state(false);
    let unlinking = $state(false);

    const action: BulkAction<TXReadItem> = {
        id: 'unlink-charges',
        icon: Unlink,
        label: () => t('transactions.bulk.unlinkSelected', 'Unlink the charges'),
        shortLabel: () => t('transactions.form.charges.unlink', 'Unlink'),
        appliesTo: takes,
        pointless: (rows) => !rows.some(takes),
        onClick: (rows) => {
            charges = rows.filter(takes);
            open = charges.length > 0;
        },
    };

    async function confirm(): Promise<void> {
        if (!open || unlinking) return;
        const failed = t('transactions.chargesUnlink.failed', 'Unlinking the charges failed');
        unlinking = true;
        try {
            const result = await commitTransactions(unlinkCommit(charges), {fallback: failed});
            if (result.committed) {
                open = false;
                notify({name: 'tx.charges.unlinked', detail: {charges: charges.map((c) => c.id)}});
                await onUnlinked();
            } else {
                toasts.error(commitRefusalMessage(result, failed, translate.current, (issueContext ?? storeIssueContext)()));
            }
        } finally {
            unlinking = false;
        }
    }

    return {
        get open() {
            return open;
        },
        get charges() {
            return charges;
        },
        get unlinking() {
            return unlinking;
        },
        action,
        confirm,
        cancel: () => {
            if (!unlinking) open = false;
        },
    };
}
