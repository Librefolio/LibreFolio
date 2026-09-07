/**
 * The pure builders behind the import wizard's N-way "compare" modal, lifted out of
 * `ImportWizardModal.svelte`.
 *
 * These turn a transaction — freshly parsed (`TransactionCreateItem`) or already in the
 * database (`TXReadItem`) — into the neutral `CmpSource` the column builder reads, and
 * render the type cell's HTML. They read only their arguments, so they can be unit-tested
 * without mounting the wizard; the label the type cell shows is passed in by the caller
 * (which owns the `$t` i18n store), keeping this module free of the Svelte runtime.
 *
 * `escHtml` escapes only `& < >` on purpose — it matches the historical inline behaviour
 * and must not be swapped for the stronger 5-char `escapeHtml`, or the rendered markup
 * (and any snapshot of it) would change.
 */
import type {TransactionCreateItem} from '$lib/types';
import type {TXReadItem} from '$lib/components/transactions/types';

/** The neutral shape both a parsed row and a DB row collapse to before cell-building. */
export interface CmpSource {
    date: string;
    type: string;
    cashAmount: number | null;
    cashCode: string | null;
    brokerId: number | null;
    assetId: number | null;
    description: string;
}

/** Escape only `& < >` (three chars) — deliberately weaker than the shared `escapeHtml`. */
export function escHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/**
 * The compare grid's "type" cell: the transaction-type icon plus its already-translated
 * label. `label` is passed in (the caller resolves it via `$t`) so this stays pure.
 */
export function compareTypeCellHtml(type: string, label: string): string {
    const slug = type.toLowerCase().replace(/_/g, '-');
    return `<span class="inline-flex items-center gap-1.5"><img src="/icons/transactions/${slug}.png" alt="" style="width:1.15rem;height:1.15rem" class="shrink-0 object-contain" onerror="this.style.display='none'"/><span>${escHtml(label)}</span></span>`;
}

/** Collapse a freshly-parsed transaction into a `CmpSource`, unwrapping array-wrapped fields. */
export function cmpSourceFromTx(tx: TransactionCreateItem, fallbackBrokerId: number | null = null): CmpSource {
    const rawCash = tx.cash ? (Array.isArray(tx.cash) ? tx.cash[0] : tx.cash) : null;
    const cash = rawCash && typeof rawCash === 'object' ? (rawCash as {code: string; amount: string}) : null;
    const assetIdRaw = Array.isArray(tx.asset_id) ? tx.asset_id[0] : tx.asset_id;
    return {
        date: tx.date ? String(tx.date) : '',
        type: tx.type ? String(tx.type) : '',
        cashAmount: cash && cash.amount != null ? Number(cash.amount) : null,
        cashCode: cash ? cash.code : null,
        brokerId: typeof tx.broker_id === 'number' ? tx.broker_id : fallbackBrokerId,
        assetId: typeof assetIdRaw === 'number' ? assetIdRaw : null,
        description: String(tx.description ?? ''),
    };
}

/** Collapse an existing DB transaction into a `CmpSource`. */
export function cmpSourceFromExisting(tx: TXReadItem): CmpSource {
    return {
        date: tx.date ? String(tx.date) : '',
        type: tx.type ? String(tx.type) : '',
        cashAmount: tx.cash && tx.cash.amount != null ? Number(tx.cash.amount) : null,
        cashCode: tx.cash ? tx.cash.code : null,
        brokerId: typeof tx.broker_id === 'number' ? tx.broker_id : null,
        assetId: typeof tx.asset_id === 'number' ? tx.asset_id : null,
        description: String(tx.description ?? ''),
    };
}
