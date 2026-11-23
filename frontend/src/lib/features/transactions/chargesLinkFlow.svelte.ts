/**
 * chargesLinkFlow — «Link the charges» from a table's selection bar (project 66, F6; shared in TL-5). The Transactions
 * page and the broker's Transactions tab both use it, each with its own `TxChargesActionModal mode="link"` bound to
 * `open`, `parent`, `charges`, `linking`, `confirm` and `cancel`, and its `action` in the selection bar.
 *
 *   - `state`: `linkSelection` on the rows the page has selected (`selection()`): hidden, off with its reason, or one
 *     parent with the charges to link. The type rules are read here (`ensureTypesLoaded`) once two rows are selected:
 *     the broker's tab does not load them otherwise, and without them every row would have no charge role and the
 *     action would stay hidden. Not before: the broker's page opens without them (the Bulk's cold path).
 *   - `action`: the bar's entry (`link-charges`): hidden when the selection is not one parent with charges, off with
 *     the reason when a rule refuses it, otherwise it opens the panel.
 *   - `confirm()`: saves the links in one commit (`linkCommit`). Committed → the panel closes, `tx.charges.linked` is
 *     sent (the parent's badge shows the outcome: no toast) and `onLinked` runs (the page empties its selection and
 *     reloads). Refused → a toast with the reasons, the panel stays open.
 *   - `cancel()`: the panel closes, nothing is saved.
 */
import {fromStore} from 'svelte/store';
import {Link2} from 'lucide-svelte';
import {_} from '$lib/i18n';
import {notify} from '$lib/stores/app/notify.svelte';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {canEditBroker, getAllBrokers} from '$lib/stores/reference/brokerStore';
import {getAllAssets} from '$lib/stores/reference/assetStore';
import {getBrokerIconHtmlById} from '$lib/utils/broker/brokerHelpers';
import type {BulkAction} from '$lib/components/table/types';
import {commitTransactions} from './txCommitApi';
import {commitRefusalMessage} from './commitRefusal';
import {linkCommit, linkSelection, txRowRef, type LinkSelection} from './chargeLinkRules';
import {ensureTypesLoaded, getTypeRule, typesVersion} from './transactionTypeStore';
import type {ResolverContext} from './resolveValidationMessage';
import type {TXReadItem} from './types';

export interface ChargesLinkFlowDeps {
    /** The rows selected in the page's table. */
    selection: () => TXReadItem[];
    /** The links were saved: the page empties its selection and reloads. */
    onLinked: () => Promise<void>;
    /** What a refusal's reasons name (brokers, assets). Absent: the broker and asset stores, as the Bulk reads them. */
    issueContext?: () => ResolverContext;
}

export interface ChargesLinkFlow {
    readonly state: LinkSelection;
    /** The panel is open on a selection that can be linked. */
    readonly open: boolean;
    readonly parent: TXReadItem | null;
    readonly charges: TXReadItem[];
    /** The commit is in flight. */
    readonly linking: boolean;
    /** The selection bar's entry. */
    readonly action: BulkAction<TXReadItem>;
    confirm(): Promise<void>;
    cancel(): void;
}

/** The refusal's context from the reference stores (the broker's tab: `PortfolioView` loads both). */
function storeIssueContext(): ResolverContext {
    const brokers = getAllBrokers() as unknown as Array<{id: number; name: string}>;
    return {
        brokers,
        assets: getAllAssets() as unknown as Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null}>,
        getBrokerIconHtml: (brokerId: number) => getBrokerIconHtmlById(brokerId, brokers as never, {width: 16, height: 16, style: 'display:inline-block;vertical-align:middle;margin-right:2px;border-radius:2px'}),
    };
}

export function createChargesLinkFlow({selection, onLinked, issueContext}: ChargesLinkFlowDeps): ChargesLinkFlow {
    const types = fromStore(typesVersion);
    const translate = fromStore(_);
    // The rules are asked for once a selection could be linked (two rows at least; fewer is hidden anyway), not when the
    // page opens: the broker's page keeps its cold path, the Bulk opening on an empty types cache (brokers-detail, 6b).
    // A failure is logged by the store; the action then stays hidden, as for any row without a charge role.
    $effect(() => {
        if (selection().length >= 2) void ensureTypesLoaded().catch(() => undefined);
    });

    const t = (key: string, fallback: string, values?: Record<string, string | number>): string => translate.current(key, values ? {values} : undefined) || fallback;

    const state = $derived.by<LinkSelection>(() => {
        void types.current;
        return linkSelection(selection(), {roleOf: (type) => getTypeRule(type).chargeRole, canEdit: (brokerId) => canEditBroker(brokerId)});
    });
    const hint = $derived(state.kind === 'disabled' ? t(`transactions.chargesLink.reason.${state.reason}`, state.reason, {type: t(`transactions.types.${state.params.type}`, state.params.type), ref: txRowRef(state.params.id, null, translate.current)}) : '');
    let panelOpen = $state(false);
    let linking = $state(false);

    const action: BulkAction<TXReadItem> = {
        id: 'link-charges',
        icon: Link2,
        label: () => t('transactions.chargesLink.action', 'Link the charges'),
        shortLabel: () => t('transactions.chargesLink.actionShort', 'Link'),
        pointless: () => state.kind === 'hidden',
        blocked: () => (state.kind === 'disabled' ? {hint, reason: state.reason} : null),
        onClick: () => {
            panelOpen = true;
        },
    };

    async function confirm(): Promise<void> {
        if (state.kind !== 'ok') return;
        const {parent, charges} = state;
        const failed = t('transactions.chargesLink.failed', 'Linking the charges failed');
        linking = true;
        try {
            const result = await commitTransactions(linkCommit(parent, charges), {fallback: failed});
            if (result.committed) {
                panelOpen = false;
                notify({name: 'tx.charges.linked', detail: {parent: parent.id, charges: charges.map((c) => c.id)}});
                await onLinked();
            } else {
                toasts.error(commitRefusalMessage(result, failed, translate.current, (issueContext ?? storeIssueContext)()));
            }
        } finally {
            linking = false;
        }
    }

    return {
        get state() {
            return state;
        },
        get open() {
            return panelOpen && state.kind === 'ok';
        },
        get parent() {
            return state.kind === 'ok' ? state.parent : null;
        },
        get charges() {
            return state.kind === 'ok' ? state.charges : [];
        },
        get linking() {
            return linking;
        },
        action,
        confirm,
        cancel: () => {
            panelOpen = false;
        },
    };
}
