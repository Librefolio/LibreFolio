<!--
  TransactionFormModal.svelte — Single-row CRUD modal for transactions.

  Modes:
  - 'create'   → blank form, POST /transactions/commit with 1 item in creates
  - 'edit'     → pre-filled from initialRow (id immutable, type/broker locked),
                 POST /transactions/commit with 1 TXUpdateItem in updates
  - 'duplicate'→ pre-filled, id stripped, link_uuid regenerated, date=today,
                 commits as 'create'
  - 'view'     → readonly display (Save button hidden)

  Field gating per type comes from `transactionTypeRules.ts` (UI hint only —
  authoritative validation is server-side via POST /transactions/validate).

  Sections:
   • Required: type, broker, date, asset (gated), quantity, cash
   • Optional (collapsible): tags, description
   • Advanced (collapsible): asset_event_id, cost_basis_override, link_uuid (RO),
                             pair-partner chip (clickable → stack-modal)
   • Read-only footer (edit/view): id, created_at, updated_at

  Dual-form mode (R6-B.1–B.3):
   • When pairLayout !== null, shows a dual-transaction form
   • FX: shared date+broker, two CompactCashCells (Da/A)
   • Transfer Asset: shared date+asset+qty, two broker selects (Da/A)
   • Transfer Cash: shared date+cash, two broker selects (Da/A)

  Validate scheduler: 1 row → always under threshold → debounce + idle ON.
  On commit rolled_back=true → banner persistent, modal stays open.

  Pattern: Svelte 5 runes, ModalBase shell, savewithretry for HTTP errors,
  data-testid everywhere.
-->
<script lang="ts">
    import {onDestroy, untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {X, ArrowRight, ArrowDown, Check, Pencil, Save} from 'lucide-svelte';
    import {getRoleIcon, getRoleIconColor} from '$lib/utils/brokerRoleHelpers';

    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import BrokerSearchSelect from '$lib/components/ui/select/BrokerSearchSelect.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import SingleDatePicker from '$lib/components/ui/SingleDatePicker.svelte';
    import TagInput from '$lib/components/ui/TagInput.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import CompactCashCell from '$lib/components/ui/CompactCashCell.svelte';
    import TransactionTypeSearchSelect from './TransactionTypeSearchSelect.svelte';
    import BrokerModal from '$lib/components/brokers/BrokerModal.svelte';
    import AssetModal from '$lib/components/assets/AssetModal.svelte';

    import {zodiosApi} from '$lib/api';
    import {ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {ensureAssetsLoaded, getAssetInfo, getAllAssets, refreshAllAssets} from '$lib/stores/assetStore';
    import {ensureBrokersLoaded, getAllBrokers, getEditableBrokers, brokerStoreVersion, refreshAllBrokers, getBrokerInfo, getBrokerRole, type BrokerInfo} from '$lib/stores/brokerStore';
    import {type TransactionTypeCode, type PairFormLayout, getTransactionTypeIconUrl, getTypeRule, getPairFormLayout, isDraftReadyForValidation, ensureTypesLoaded, getSwapGroup, typesVersion} from '$lib/stores/transactionTypeStore';
    import {createValidateScheduler} from '$lib/utils/useValidateScheduler.svelte';
    import {saveWithRetry, extractErrorMessage, extractValidationIssues} from '$lib/utils/saveWithRetry';
    import {resolveIssueMessage, type ResolverContext} from '$lib/utils/resolveValidationMessage';
    import {generateUUID} from '$lib/utils/uuid';
    import {formatDecimalForDisplay} from '$lib/utils/formatDecimal';
    import {
        buildCreatePayload,
        buildUpdateDiff,
        diffDualItem,
        type TxFields,
        type TxOriginal,
    } from '$lib/utils/txPayloadHelpers';

    // =========================================================================
    // Types (mirror schemas/transactions.py — kept local to avoid pulling Zod)
    // =========================================================================

    export interface TXReadItem {
        id: number;
        broker_id: number;
        asset_id?: number | null;
        type: string;
        date: string;
        quantity: string;
        cash?: {code: string; amount: string} | null;
        related_transaction_id?: number | null;
        partner_broker_id?: number | null;
        tags?: string[] | null;
        description?: string | null;
        cost_basis_override?: string | null;
        asset_event_id?: number | null;
        created_at?: string;
        updated_at?: string;
    }

    interface ValidationIssue {
        operation: 'create' | 'update' | 'delete';
        index: number;
        ref_id?: number | null;
        error: string;
        code?: string | null;
        params?: Record<string, any> | null;
        field?: string | null;
        /** Pydantic loc path (e.g. "body.creates.0.broker_id"). */
        loc?: string;
    }

    type Mode = 'create' | 'edit' | 'duplicate' | 'view';

    interface Props {
        open: boolean;
        mode: Mode;
        initialRow?: TXReadItem | null;
        /** When opened from the wizard: pre-select this broker. */
        forcedBroker?: number | null;
        /** Bugfix-5 §A4: when `false`, the Save button does NOT call the
         *  bulk endpoint — instead it invokes `onPushDraft` with the
         *  collected create-shaped payload, so the parent (BulkModal) can
         *  apply the change to its in-flight grid. Default `true` (commit). */
        commitOnSave?: boolean;
        /** Bugfix-5 §A4: when `true`, override the default immutability of
         *  `type`/`broker` in `mode='edit'` (deep-edit single row from the
         *  BulkModal). Default `false`. */
        unlockImmutable?: boolean;
        /** Bugfix-5 §U20: client-side tag suggestions for the autocomplete.
         *  Caller is expected to aggregate from the loaded transactions
         *  (no dedicated backend endpoint). */
        availableTags?: string[];
        /** Z-index override — needed when the form is mounted as a stacked
         *  modal on top of another (e.g. BulkModal → FormModal). */
        zIndex?: number;
        /** C1-fix: pre-injected partner row so the dual form can be populated
         *  without fetching from the API. Used when opening from BulkModal. */
        injectedPartnerRow?: TXReadItem | null;
        onClose: () => void;
        onCommitted?: (resp: {transaction_id?: number | null}) => void;
        /** Called instead of committing when `commitOnSave=false`. Receives
         *  the same payload shape as `collectCreate()` (which is also valid
         *  as an update payload because all fields are present). */
        onPushDraft?: (payload: Record<string, unknown>) => void;
        /** Called when the user clicks "Edit" in view mode to switch to edit. */
        onSwitchToEdit?: () => void;
        /** Bug3-fix: when false, the edit pencil button is hidden in view mode
         *  (user lacks EDITOR access on the broker). Default true. */
        canEdit?: boolean;
        /** Bug15-fix: monotonic key that forces re-init when the modal is
         *  re-opened without `open` transitioning through `false`. */
        openKey?: number;
        /** Context-aware validation: when set, the FormModal sends the entire
         *  bulk payload (from this callback) merged with its own row to /validate,
         *  so the balance walk sees all in-flight changes. */
        getBulkContext?: () => {creates: Record<string, unknown>[]; updates: Record<string, unknown>[]; deletes: number[]};
    }

    let {open, mode, initialRow = null, forcedBroker = null, commitOnSave = true, unlockImmutable = false, availableTags = [], zIndex = 50, injectedPartnerRow = null, onClose, onCommitted, onPushDraft, onSwitchToEdit, canEdit = true, openKey = 0, getBulkContext}: Props = $props();

    // =========================================================================
    // Form state
    // =========================================================================

    interface FormDraft {
        broker_id: number;
        asset_id: number | null;
        type: TransactionTypeCode;
        date: string;
        quantity: string;
        cash: {code: string; amount: string} | null;
        tags: string[];
        description: string;
        asset_event_id: number | null;
        cost_basis_override: string;
        link_uuid: string | null;
    }

    /** Dual-form "To" side state — only used when pairLayout !== null. */
    interface DualDraftTo {
        /** For transfer_asset / transfer_cash: the "To" broker. */
        broker_id: number;
        /** For fx: the "To" cash (different currency). */
        cash: {code: string; amount: string} | null;
        /** "To" side date — may differ from "From" side (e.g. wire transfer arrival). */
        date: string;
    }

    function todayIso(): string {
        return new Date().toISOString().slice(0, 10);
    }

    function emptyDraft(): FormDraft {
        const brokers = getEditableBrokers();
        // Bugfix-2 §C9: only auto-pick a broker if exactly one is available;
        // otherwise leave the field empty (0 = unset sentinel) so the user
        // is forced to choose consciously.
        const defaultBroker = forcedBroker ?? (brokers.length === 1 ? brokers[0].id : 0);
        return {
            broker_id: defaultBroker,
            asset_id: null,
            type: 'BUY',
            date: todayIso(),
            quantity: '0',
            cash: null,
            tags: [],
            description: '',
            asset_event_id: null,
            cost_basis_override: '',
            link_uuid: null,
        };
    }

    function emptyDualTo(): DualDraftTo {
        return {broker_id: 0, cash: null, date: todayIso()};
    }

    function fromTx(tx: TXReadItem, opts: {regenerateLink?: boolean; resetDate?: boolean} = {}): FormDraft {
        const txRule = getTypeRule(tx.type);
        // Auto-sign: show positive values for auto-negated types
        // Also normalize paired types (transfer_asset, transfer_cash) — the dual
        // form always displays absolute values; sign is determined by From/To sides.
        let qty = tx.quantity;
        if (Number(qty) < 0 && (txRule.quantityRule === 'negative' || txRule.pairFormLayout != null)) {
            qty = String(Math.abs(Number(qty)));
        }
        let cash = tx.cash ? {code: tx.cash.code, amount: tx.cash.amount} : null;
        if (cash && txRule.cashSign === 'negative' && Number(cash.amount) < 0) {
            cash = {code: cash.code, amount: String(Math.abs(Number(cash.amount)))};
        }
        return {
            broker_id: tx.broker_id,
            asset_id: tx.asset_id ?? null,
            type: tx.type as TransactionTypeCode,
            date: opts.resetDate ? todayIso() : tx.date,
            quantity: qty,
            cash,
            tags: [...(tx.tags ?? [])],
            description: tx.description ?? '',
            asset_event_id: tx.asset_event_id ?? null,
            cost_basis_override: tx.cost_basis_override ?? '',
            link_uuid: opts.regenerateLink ? generateUUID() : null,
        };
    }

    // Single source-of-truth state (computed from props in $effect, never read inside the same effect).
    let draft = $state<FormDraft>(emptyDraft());
    /** Dual-form "To" side — populated when pairLayout !== null. */
    let dualTo = $state<DualDraftTo>(emptyDualTo());
    /** The partner TXReadItem when editing a paired transaction. */
    let partnerRow = $state<TXReadItem | null>(null);
    /** Loading state for the partner fetch. */
    let loadingPartner = $state(false);
    let issues = $state<ValidationIssue[]>([]);
    let formError = $state<string | null>(null);
    let commitFailed = $state(false);
    let committing = $state(false);
    /** Anti-bounce: track last commit draft key + timestamp to prevent duplicate network requests. */
    let lastCommitDraftKey = $state('');
    let lastCommitAt = $state(0);
    const COMMIT_ANTI_BOUNCE_MS = 10000;
    let optionalOpen = $state(false);
    let advancedOpen = $state(false);
    /** Snapshot of `draft` at modal-open time, used to detect unsaved
     *  changes (Bugfix-3 §C11). */
    let initialDraftKey = $state('');
    let confirmCloseOpen = $state(false);
    /** Bug5-fix: broker_id of partner that the user cannot access.
     *  When set, the "To" side shows a locked placeholder instead of empty. */
    let inaccessiblePartnerBrokerId = $state<number | null>(null);
    /** User-facing display string for `draft.quantity`. Decoupled from the
     *  authoritative payload so the user can type freely (e.g. "0.0000")
     *  without us reformatting mid-keystroke (Bugfix-4 §U18). The display
     *  is reseeded from `draft.quantity` whenever the draft itself is reset
     *  (modal open, type change reset). */
    let qtyDisplay = $state('');

    // Reset draft on open; broker store must be loaded first.
    $effect(() => {
        if (!open) return;
        // Bug15-fix: track openKey to force re-init even when `open` doesn't toggle.
        void openKey;
        // Read props inside `untrack` — we only want to recompute when `open` flips,
        // not on every initialRow/mode mutation that may be irrelevant.
        const m = mode;
        const row = initialRow;
        untrack(() => {
            issues = [];
            formError = null;
            commitFailed = false;
            optionalOpen = false;
            advancedOpen = false;
            confirmCloseOpen = false;
            inaccessiblePartnerBrokerId = null;
            partnerRow = null;
            loadingPartner = false;
            dualTo = emptyDualTo();
            if (m === 'create') {
                // C1-fix: when initialRow is present (e.g. editing a 'new' draft
                // from BulkModal), populate from it instead of starting blank.
                if (row) {
                    draft = fromTx(row, {resetDate: false});
                    // Injected partner for paired drafts
                    const injected = injectedPartnerRow;
                    if (injected) {
                        partnerRow = injected;
                        const layout = getPairFormLayout(row.type);
                        if (layout) {
                            applyPartnerToDualTo(row, injected, layout);
                        }
                    }
                } else {
                    draft = emptyDraft();
                }
            } else if (m === 'duplicate' && row) {
                draft = fromTx(row, {regenerateLink: row.related_transaction_id != null, resetDate: true});
            } else if ((m === 'edit' || m === 'view') && row) {
                draft = fromTx(row);
                // C1-fix: if a partner was injected (from BulkModal), use it
                // directly instead of fetching from the API.
                const injected = injectedPartnerRow;
                if (injected) {
                    partnerRow = injected;
                    const layout = getPairFormLayout(row.type);
                    if (layout) {
                        applyPartnerToDualTo(row, injected, layout);
                    }
                } else if (row.related_transaction_id != null && row.related_transaction_id > 0) {
                    // If the row has a linked partner and its type has a pairFormLayout,
                    // fetch the partner for dual-form editing.
                    const layout = getPairFormLayout(row.type);

                    // Bug13-fix: pre-populate dualTo synchronously from partner_broker_id
                    // so the template shows the correct state immediately (lock/name),
                    // BEFORE fetchPartner resolves. Don't gate on `layout` because
                    // getPairFormLayout may return null if types haven't loaded yet.
                    const pBid = row.partner_broker_id;
                    if (pBid != null) {
                        dualTo = {broker_id: pBid, cash: null, date: ''};
                        // If the user has no role on the partner broker, mark it inaccessible now
                        if (getBrokerRole(pBid) == null) {
                            inaccessiblePartnerBrokerId = pBid;
                        }
                    }

                    if (layout) {
                        loadingPartner = true;
                        fetchPartner(row);
                    } else {
                        // Types not loaded yet — defer fetchPartner to when types arrive.
                        // The $derived pairLayout will re-trigger via $typesVersion,
                        // but we need to also trigger fetchPartner. Schedule it.
                        loadingPartner = true;
                        void ensureTypesLoaded().then(() => {
                            const l = getPairFormLayout(row.type);
                            if (l) fetchPartner(row);
                            else loadingPartner = false;
                        });
                    }
                } else if (row.related_transaction_id === -1) {
                    // C1-fix: sentinel -1 means "paired but new/no DB id" —
                    // partner should have been injected above. If not, the dual
                    // form will still show (from pairLayout) but partner fields empty.
                    const layout = getPairFormLayout(row.type);
                    void layout; // dual form will activate via pairLayout derived
                }
            } else {
                draft = emptyDraft();
            }
            lastTypeForReset = draft.type;
            initialDraftKey = JSON.stringify(draft) + JSON.stringify(dualTo);
            qtyDisplay = formatDecimalForDisplay(draft.quantity);
        });
        // Async hydration (brokers + currencies + asset cache for the picked asset).
        void (async () => {
            await Promise.all([ensureBrokersLoaded(), ensureCurrenciesLoaded($currentLanguage), ensureAssetsLoaded(), ensureTypesLoaded()]);
            // After brokers loaded, backfill broker_id only if a single broker is
            // available (Bugfix-2 §C9) — otherwise leave it 0 so the user must
            // pick. `forcedBroker` (from the wizard's "Create new") still wins.
            untrack(() => {
                if (mode === 'create' && draft.broker_id === 0) {
                    if (forcedBroker != null) {
                        draft = {...draft, broker_id: forcedBroker};
                    } else {
                        const all = getAllBrokers();
                        if (all.length === 1) draft = {...draft, broker_id: all[0].id};
                    }
                }
                // Refresh the unsaved-changes baseline now that any auto-set
                // broker_id is in place — otherwise the user would be asked
                // to confirm "discard" on a broker we ourselves just picked.
                initialDraftKey = JSON.stringify(draft) + JSON.stringify(dualTo);
            });
        })();
    });

    // =========================================================================
    // Dual-form: partner fetch for edit mode
    // =========================================================================

    async function fetchPartner(row: TXReadItem) {
        if (!row.related_transaction_id) return;
        try {
            const results = await zodiosApi.query_transactions_api_v1_transactions_get({
                queries: {ids: [row.related_transaction_id], limit: 1},
            }) as unknown as TXReadItem[];
            if (results.length > 0) {
                const partner = results[0];
                partnerRow = partner;
                // Bug13-fix: clear pre-set inaccessible flag — partner IS accessible
                inaccessiblePartnerBrokerId = null;
                const layout = getPairFormLayout(row.type);
                if (layout) {
                    applyPartnerToDualTo(row, partner, layout);
                }
            } else {
                // Bug5-fix: partner not accessible — use partner_broker_id to
                // show a placeholder in the dual form "To" side.
                const pBid = row.partner_broker_id;
                if (pBid != null) {
                    const layout = getPairFormLayout(row.type);
                    if (layout && layout !== 'fx') {
                        dualTo = {broker_id: pBid, cash: null, date: row.date};
                    }
                    inaccessiblePartnerBrokerId = pBid;
                }
            }
        } catch (e) {
            console.error('[TransactionFormModal] Failed to fetch partner', e);
        } finally {
            loadingPartner = false;
        }
    }

    /** C1-fix: apply partner data to the dual-form "To" side. Shared by
     *  both `fetchPartner` (API) and injectedPartnerRow (BulkModal). */
    function applyPartnerToDualTo(row: TXReadItem, partner: TXReadItem, layout: PairFormLayout) {
        if (layout === 'fx') {
            const myAmount = Number(row.cash?.amount ?? 0);
            const partnerAmount = Number(partner.cash?.amount ?? 0);
            if (myAmount > 0 && partnerAmount < 0) {
                draft = fromTx(partner);
                dualTo = {
                    broker_id: partner.broker_id,
                    cash: row.cash ? {code: row.cash.code, amount: String(Math.abs(Number(row.cash.amount)))} : null,
                    date: row.date,
                };
            } else {
                dualTo = {
                    broker_id: partner.broker_id,
                    cash: partner.cash ? {code: partner.cash.code, amount: String(Math.abs(Number(partner.cash.amount)))} : null,
                    date: partner.date,
                };
            }
        } else if (layout === 'transfer_asset') {
            const myQty = Number(row.quantity);
            if (myQty > 0) {
                draft = fromTx(partner);
                dualTo = {broker_id: row.broker_id, cash: null, date: row.date};
            } else {
                dualTo = {broker_id: partner.broker_id, cash: null, date: partner.date};
            }
            // Dual form always shows absolute qty — sign is determined by From/To sides
            if (Number(draft.quantity) < 0) {
                draft = {...draft, quantity: String(Math.abs(Number(draft.quantity)))};
            }
            qtyDisplay = formatDecimalForDisplay(draft.quantity);
        } else if (layout === 'transfer_cash') {
            const myAmount = Number(row.cash?.amount ?? 0);
            const fromRow = myAmount < 0 ? row : partner;
            const toRow = myAmount < 0 ? partner : row;
            draft = fromTx(fromRow);
            if (draft.cash && Number(draft.cash.amount) < 0) {
                draft = {...draft, cash: {code: draft.cash.code, amount: String(Math.abs(Number(draft.cash.amount)))}};
            }
            dualTo = {broker_id: toRow.broker_id, cash: null, date: toRow.date};
            qtyDisplay = formatDecimalForDisplay(draft.quantity);
        }
        // B1-fix: if the pair has mismatched description, concatenate with explanatory note
        const rowDesc = row.description ?? '';
        const partnerDesc = partner.description ?? '';
        if (rowDesc !== partnerDesc) {
            const parts: string[] = [];
            if (rowDesc) parts.push(rowDesc);
            if (partnerDesc) parts.push(partnerDesc);
            draft = {...draft, description: parts.join(' | ') + ' [auto-merged: pair had mismatched descriptions]'};
        }
        // B1-fix: if the pair has mismatched tags, union them
        const rowTags = row.tags ?? [];
        const partnerTags = partner.tags ?? [];
        if (JSON.stringify([...rowTags].sort()) !== JSON.stringify([...partnerTags].sort())) {
            const merged = [...new Set([...rowTags, ...partnerTags])].sort();
            draft = {...draft, tags: merged};
        }
        initialDraftKey = JSON.stringify(draft) + JSON.stringify(dualTo);
    }

    /** Detect unsaved changes vs. the snapshot taken at modal-open. */
    function hasUnsavedChanges(): boolean {
        if (isReadonly) return false;
        return (JSON.stringify(draft) + JSON.stringify(dualTo)) !== initialDraftKey;
    }

    function requestClose() {
        if (committing) return;
        if (hasUnsavedChanges()) {
            confirmCloseOpen = true;
            return;
        }
        onClose();
    }

    function confirmDiscardAndClose() {
        confirmCloseOpen = false;
        onClose();
    }

    // -------------------------------------------------------------------------
    // Type-rule enforcement: when `draft.type` changes the rules for
    // `asset/cash/quantity` may change too. Any value that becomes
    // *forbidden* must be cleared from the draft (otherwise the UI hides it
    // but the backend still receives the stale value — see Bugfix-1 §C3).
    // -------------------------------------------------------------------------
    let lastTypeForReset = $state<TransactionTypeCode>('BUY');
    $effect(() => {
        if (!open || isReadonly) return;
        const t = draft.type;
        if (t === lastTypeForReset) return;
        lastTypeForReset = t;
        const r = getTypeRule(t);
        untrack(() => {
            const next = {...draft};
            if (r.assetField === 'forbidden' && next.asset_id != null) next.asset_id = null;
            if (r.cashField === 'forbidden' && next.cash != null) next.cash = null;
            if (r.quantityMode === 'forbidden') {
                next.quantity = '0';
                qtyDisplay = '0';
            }
            // Clear linked event when no longer applicable.
            if (!r.eventLinkable && next.asset_event_id != null) next.asset_event_id = null;
            // Clear cost basis when not a TRANSFER (only meaningful there).
            if (t !== 'TRANSFER' && next.cost_basis_override) next.cost_basis_override = '';
            draft = next;
            // Reset dualTo when switching to/from dual mode
            const newLayout = getPairFormLayout(t);
            if (!newLayout) {
                dualTo = emptyDualTo();
                partnerRow = null;
            }
        });
    });

    // =========================================================================
    // Brokers (reactive view of brokerStore)
    // =========================================================================

    let brokers = $derived.by<BrokerInfo[]>(() => {
        void $brokerStoreVersion;
        return getEditableBrokers();
    });

    // =========================================================================
    // Type rule + derived UI state
    // =========================================================================

    let rule = $derived.by(() => {
        void $typesVersion; // re-derive when server type rules load
        return getTypeRule(draft.type);
    });
    /** Dual-form layout — null for standard single form.
     *  W32 fix: dual mode ONLY when the type requires a link (TRANSFER,
     *  FX_CONVERSION) OR when editing an existing linked pair. Types like
     *  DEPOSIT/WITHDRAWAL have pair_form_layout set but requires_link=false
     *  → they stay in single form by default. */
    let pairLayout = $derived.by<PairFormLayout | null>(() => {
        void $typesVersion; // Bug9-fix: re-derive when server type rules load
        const r = getTypeRule(draft.type);
        // Types that ALWAYS require a pair → auto dual
        if (r.requiresPair) return r.pairFormLayout;
        // When editing an existing linked pair → use the layout
        if (initialRow?.related_transaction_id != null) {
            return getPairFormLayout(initialRow.type);
        }
        return null;
    });
    /** Auto-sign: user enters positive, backend expects negative. */
    let autoNegateQty = $derived(rule.quantityRule === 'negative');
    let autoNegateCash = $derived(rule.cashSign === 'negative');
    let isReadonly = $derived(mode === 'view');
    // Bugfix-5 §A4: `unlockImmutable=true` (deep-edit from BulkModal) overrides
    // the default immutability so the user can change `type`/`broker` on an
    // existing draft. `view` mode always wins (everything stays readonly).
    let typeImmutable = $derived((mode === 'edit' || mode === 'view') && !unlockImmutable);
    /** H6: when editing a DB row (unlockImmutable=true), restrict the type
     *  dropdown to the swap group of the original type. For create/duplicate,
     *  show all standalone types (no restriction). */
    let allowedTypes = $derived.by<TransactionTypeCode[] | undefined>(() => {
        // In edit mode with unlockImmutable (deep-edit from BulkModal),
        // restrict to swap group of the original type.
        if (mode === 'edit' && unlockImmutable && initialRow) {
            return getSwapGroup(initialRow.type as TransactionTypeCode);
        }
        // No restriction for create/duplicate
        return undefined;
    });
    let brokerImmutable = $derived(((mode === 'edit' || mode === 'view') && !unlockImmutable) || forcedBroker != null);
    let canShowAssetEvent = $derived(rule.eventLinkable && draft.asset_id != null);

    /** H4-fix: true when all required fields for the current type are filled.
     *  Gates the auto-validate scheduler and the Apply/Save button. */
    let isFormComplete = $derived.by(() => {
        void $typesVersion; // re-derive when server type rules load
        return isDraftReadyForValidation(draft);
    });

    // cost_basis_override is meaningful only for the receiver of a TRANSFER pair.
    // Single-form mode rarely creates TRANSFER (uses wizard), so we expose the
    // field whenever type=TRANSFER and let the backend enforce semantics.
    let showCostBasisField = $derived(draft.type === 'TRANSFER');

    // Pair partner chip (only when editing an existing linked tx — non-dual mode).
    let pairPartnerId = $derived(pairLayout ? null : (initialRow?.related_transaction_id ?? null));

    // =========================================================================
    // Dual-form title
    // =========================================================================

    let dualTitle = $derived.by(() => {
        if (!pairLayout) return '';
        switch (pairLayout) {
            case 'fx': return $t('transactions.form.fxTitle');
            case 'transfer_asset': return $t('transactions.form.transferAssetTitle');
            case 'transfer_cash': return $t('transactions.form.transferCashTitle');
            default: return '';
        }
    });

    // =========================================================================
    // Dual-form validation helpers
    // =========================================================================

    /** Client-side validation error for the dual form (shown in the form, not from backend). */
    let dualValidationError = $derived.by<string | null>(() => {
        if (!pairLayout) return null;
        if (pairLayout === 'fx') {
            const fromCode = draft.cash?.code ?? '';
            const toCode = dualTo.cash?.code ?? '';
            if (fromCode && toCode && fromCode === toCode) {
                return $t('transactions.form.sameCurrencyError');
            }
        } else {
            // transfer_asset / transfer_cash: brokers must differ
            if (draft.broker_id && dualTo.broker_id && draft.broker_id === dualTo.broker_id) {
                return $t('transactions.form.sameBrokerError');
            }
        }
        return null;
    });

    // =========================================================================
    // Validate scheduler — debounced/manual/idle, always enabled (1 row).
    // =========================================================================

    const scheduler = createValidateScheduler({
        // Auto-fire only when the draft is "ready" — i.e. all required fields
        // for its type are populated (Bugfix-2 §C5). Manual ⚡ Validate now
        // always fires regardless.
        enabled: () => !isReadonly && isDraftReadyForValidation(draft),
        draftKey: () => lastDraftKey,
        validateFn: async () => {
            if (isReadonly) return {issuesCount: 0};
            if (pairLayout) {
                // Dual mode: validate both sides
                const dualPayload = mode === 'edit'
                    ? {updates: collectDualUpdates()}
                    : {creates: collectDualCreates()};
                // Merge bulk context if available
                let payload: Record<string, unknown>;
                if (getBulkContext) {
                    const ctx = getBulkContext();
                    const mergedCreates = [...(ctx.creates || []), ...(dualPayload.creates || [] as Record<string, unknown>[])];
                    const mergedUpdates = [...(ctx.updates || []), ...(dualPayload.updates || [] as Record<string, unknown>[])];
                    payload = {};
                    if (mergedCreates.length > 0) payload.creates = mergedCreates;
                    if (mergedUpdates.length > 0) payload.updates = mergedUpdates;
                    if (ctx.deletes?.length > 0) payload.deletes = ctx.deletes;
                } else {
                    payload = dualPayload;
                }
                const sentKey = lastDraftKey;
                try {
                    const res = (await zodiosApi.validate_transactions_api_v1_transactions_validate_post(payload as never)) as {committed?: boolean; issues?: ValidationIssue[]};
                    // W42: deduplicate issues by code (both halves produce the same error)
                    issues = deduplicateIssues(res?.issues ?? []);
                    lastValidatedDraftKey = sentKey;
                    issuesDismissed = false;
                    return {issuesCount: issues.length};
                } catch (e) {
                    const extracted = extractValidationIssues(e);
                    if (extracted.length > 0) {
                        issues = deduplicateIssues(extracted.map((iss) => ({
                            operation: (mode === 'edit' ? 'update' : 'create') as 'create' | 'update',
                            index: 0,
                            error: iss.msg,
                            code: iss.code,
                            params: iss.params,
                            loc: iss.loc,
                        })));
                    } else {
                        const msg = extractErrorMessage(e, $t('transactions.form.saveFailed'));
                        issues = [{operation: mode === 'edit' ? 'update' : 'create', index: 0, error: msg}];
                    }
                    lastValidatedDraftKey = sentKey;
                    issuesDismissed = false;
                    return {issuesCount: issues.length};
                }
            }
            const myPayload = mode === 'edit' ? {updates: [collectUpdate()]} : {creates: [collectCreate()]};
            // Context-aware validation: merge bulk context if available
            let payload: Record<string, unknown>;
            let myOperation: 'create' | 'update' = mode === 'edit' ? 'update' : 'create';
            let myIndex: number;
            if (getBulkContext) {
                const ctx = getBulkContext();
                const mergedCreates = [...(ctx.creates || []), ...(myPayload.creates || [] as Record<string, unknown>[])];
                const mergedUpdates = [...(ctx.updates || []), ...(myPayload.updates || [] as Record<string, unknown>[])];
                payload = {};
                if (mergedCreates.length > 0) payload.creates = mergedCreates;
                if (mergedUpdates.length > 0) payload.updates = mergedUpdates;
                if (ctx.deletes?.length > 0) payload.deletes = ctx.deletes;
                // My row is the last item in creates or updates
                myIndex = myOperation === 'create' ? mergedCreates.length - 1 : mergedUpdates.length - 1;
            } else {
                payload = myPayload;
                myIndex = 0;
            }
            const sentKey = lastDraftKey;
            try {
                const res = (await zodiosApi.validate_transactions_api_v1_transactions_validate_post(payload as never)) as {committed?: boolean; issues?: ValidationIssue[]};
                // Filter: show only issues for my row (or global balance issues with index=-1)
                const allIssues = res?.issues ?? [];
                issues = getBulkContext
                    ? allIssues.filter((i) => (i.operation === myOperation && i.index === myIndex) || i.index === -1)
                    : allIssues;
                lastValidatedDraftKey = sentKey;
                issuesDismissed = false;
                return {issuesCount: issues.length};
            } catch (e) {
                // 422 safety net — should rarely fire now that /validate uses List[dict].
                const extracted = extractValidationIssues(e);
                if (extracted.length > 0) {
                    issues = extracted.map((iss) => ({
                        operation: (mode === 'edit' ? 'update' : 'create') as 'create' | 'update',
                        index: 0,
                        error: iss.msg,
                        code: iss.code,
                        params: iss.params,
                        loc: iss.loc,
                    }));
                } else {
                    const msg = extractErrorMessage(e, $t('transactions.form.saveFailed'));
                    issues = [{operation: mode === 'edit' ? 'update' : 'create', index: 0, error: msg}];
                }
                lastValidatedDraftKey = sentKey;
                issuesDismissed = false;
                return {issuesCount: issues.length};
            }
        },
    });

    onDestroy(() => scheduler.dispose());

    // Trigger 'change' on every meaningful draft mutation.
    let lastDraftKey = $state('');
    /** Bugfix-4 §U16: track validate freshness for the green/warning banner UX. */
    let lastValidatedDraftKey = $state('');
    let issuesDismissed = $state(false);
    let isFreshlyValid = $derived(!isReadonly && scheduler.state.lastValidatedAt != null && issues.length === 0 && lastValidatedDraftKey === lastDraftKey && lastDraftKey !== '');
    let showIssuesBanner = $derived(issues.length > 0 && !issuesDismissed);
    let fieldIssues = $derived(issues.filter((i) => i.index >= 0));
    let balanceIssues = $derived(issues.filter((i) => i.index < 0));

    /** Context for resolving validation issue codes into translated messages. */
    let resolverCtx: ResolverContext = $derived({
        brokers: brokers as unknown as Array<{id: number; name: string}>,
        assets: getAllAssets() as unknown as Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null}>,
        getBrokerIconUrl: (brokerId: number) => {
            const b = brokers.find((br) => br.id === brokerId);
            if (!b) return null;
            if (b.icon_url?.trim()) return b.icon_url;
            if (b.portal_url?.trim()) {
                try { return new URL(b.portal_url).origin + '/favicon.ico'; } catch { /* skip */ }
            }
            return null;
        },
    });
    $effect(() => {
        if (!open || isReadonly) return;
        const key = JSON.stringify(draft) + JSON.stringify(dualTo);
        if (key === lastDraftKey) return;
        lastDraftKey = key;
        commitFailed = false;
        scheduler.trigger('change');
    });

    // -------------------------------------------------------------------------
    // UI helpers (SimpleSelect options for Type, autocomplete name suffix)
    // -------------------------------------------------------------------------

    /** Random suffix used as the `name` attribute on numeric inputs to
     *  defeat browser autofill heuristics (Bugfix-1 §U7). Stable per modal
     *  open. */
    const autocompleteNonce = $derived(Math.random().toString(36).slice(2, 10));

    /** Show the Advanced disclosure only if at least one of its sub-fields
     *  is meaningful for the current type/state (Bugfix-1 §U6). */
    let showAdvancedSection = $derived(!pairLayout && ((rule.eventLinkable && draft.asset_id != null) || draft.type === 'TRANSFER' || pairPartnerId != null || (mode === 'edit' && draft.link_uuid != null)));

    /** BrokerSearchSelect expects `BrokerSelectItem[]`; the brokerStore's
     *  `BrokerInfo` is structurally compatible (id/name/icon_url present)
     *  but TS can't widen via the prop attribute. We cast in script. */
    let brokersForSelect = $derived(brokers as unknown as Array<{id: number; name: string; icon_url?: string | null}>);
    /** W37: Filtered broker lists for dual form — prevent same broker on both sides. */
    let brokersForFrom = $derived(pairLayout && pairLayout !== 'fx'
        ? brokersForSelect.filter((b) => b.id !== dualTo.broker_id || !dualTo.broker_id)
        : brokersForSelect);
    let brokersForTo = $derived(pairLayout && pairLayout !== 'fx'
        ? brokersForSelect.filter((b) => b.id !== draft.broker_id || !draft.broker_id)
        : brokersForSelect);
    let brokerIdValue = $derived<number | null>(draft.broker_id || null);
    let brokerToIdValue = $derived<number | null>(dualTo.broker_id || null);

    // =========================================================================
    // Sanitizers
    // =========================================================================

    function collectCreate(): Record<string, unknown> {
        return buildCreatePayload(draftToTxFields(), rule);
    }

    function collectUpdate(): Record<string, unknown> {
        if (!initialRow) return {};
        const origRule = getTypeRule(initialRow.type as TransactionTypeCode);
        return buildUpdateDiff(draftToTxFields(), initialRow as unknown as TxOriginal, rule, origRule);
    }

    /** Convert the form draft to the shared TxFields interface. */
    function draftToTxFields(): TxFields {
        return {
            type: draft.type,
            broker_id: draft.broker_id,
            date: draft.date,
            quantity: draft.quantity,
            asset_id: draft.asset_id,
            cash: draft.cash,
            tags: draft.tags,
            description: draft.description,
            cost_basis_override: draft.cost_basis_override,
            asset_event_id: draft.asset_event_id,
            link_uuid: draft.link_uuid,
        };
    }

    // =========================================================================
    // Dual-form collect helpers
    // =========================================================================

    /**
     * Build 2 TXCreateItem payloads for dual-form mode.
     * Shared link_uuid connects them as a pair.
     */
    function collectDualCreates(): Record<string, unknown>[] {
        // Bug14-fix: reuse existing link_uuid in edit mode so BulkModal can
        // match the hidden partner draft; only generate a new UUID for create.
        const linkUuid = draft.link_uuid || generateUUID();
        const sharedTags = draft.tags.length > 0 ? draft.tags : undefined;
        const sharedDesc = draft.description.trim() || undefined;

        if (pairLayout === 'fx') {
            // FX_CONVERSION: both sides qty=0, different currencies
            const fromCashAmt = draft.cash?.amount ? String(-Math.abs(Number(draft.cash.amount))) : '0';
            const toCashAmt = dualTo.cash?.amount ? String(Math.abs(Number(dualTo.cash.amount))) : '0';
            const fromItem: Record<string, unknown> = {
                broker_id: draft.broker_id,
                type: 'FX_CONVERSION',
                date: draft.date,
                quantity: '0',
                cash: {code: draft.cash?.code ?? '', amount: fromCashAmt},
                link_uuid: linkUuid,
            };
            const toItem: Record<string, unknown> = {
                broker_id: draft.broker_id,
                type: 'FX_CONVERSION',
                date: dualTo.date || draft.date,
                quantity: '0',
                cash: {code: dualTo.cash?.code ?? '', amount: toCashAmt},
                link_uuid: linkUuid,
            };
            if (sharedTags) { fromItem.tags = sharedTags; toItem.tags = sharedTags; }
            if (sharedDesc) { fromItem.description = sharedDesc; toItem.description = sharedDesc; }
            return [fromItem, toItem];
        }

        if (pairLayout === 'transfer_asset') {
            // TRANSFER: from = negative qty, to = positive qty
            const absQty = String(Math.abs(Number(draft.quantity)));
            const fromItem: Record<string, unknown> = {
                broker_id: draft.broker_id,
                type: 'TRANSFER',
                date: draft.date,
                quantity: String(-Math.abs(Number(draft.quantity))),
                link_uuid: linkUuid,
            };
            const toItem: Record<string, unknown> = {
                broker_id: dualTo.broker_id,
                type: 'TRANSFER',
                date: dualTo.date || draft.date,
                quantity: absQty,
                link_uuid: linkUuid,
            };
            if (draft.asset_id != null) { fromItem.asset_id = draft.asset_id; toItem.asset_id = draft.asset_id; }
            if (draft.cost_basis_override.trim()) toItem.cost_basis_override = draft.cost_basis_override.trim();
            if (sharedTags) { fromItem.tags = sharedTags; toItem.tags = sharedTags; }
            if (sharedDesc) { fromItem.description = sharedDesc; toItem.description = sharedDesc; }
            return [fromItem, toItem];
        }

        if (pairLayout === 'transfer_cash') {
            // CASH_TRANSFER pair: from (negative cash) + to (positive cash)
            const absAmount = draft.cash?.amount ? String(Math.abs(Number(draft.cash.amount))) : '0';
            const cashCode = draft.cash?.code ?? '';
            const fromItem: Record<string, unknown> = {
                broker_id: draft.broker_id,
                type: 'CASH_TRANSFER',
                date: draft.date,
                quantity: '0',
                cash: {code: cashCode, amount: String(-Math.abs(Number(absAmount)))},
                link_uuid: linkUuid,
            };
            const toItem: Record<string, unknown> = {
                broker_id: dualTo.broker_id,
                type: 'CASH_TRANSFER',
                date: dualTo.date || draft.date,
                quantity: '0',
                cash: {code: cashCode, amount: absAmount},
                link_uuid: linkUuid,
            };
            if (sharedTags) { fromItem.tags = sharedTags; toItem.tags = sharedTags; }
            if (sharedDesc) { fromItem.description = sharedDesc; toItem.description = sharedDesc; }
            return [fromItem, toItem];
        }

        // Fallback — should not happen
        return [collectCreate()];
    }

    /**
     * Build 2 TXUpdateItem payloads for dual-form edit mode.
     * Only include PATCHABLE fields that actually changed vs the original.
     */
    function collectDualUpdates(): Record<string, unknown>[] {
        if (!initialRow || !partnerRow) return [];
        const items = collectDualCreates();

        // Determine which original row maps to which item (From=items[0], To=items[1])
        let fromOrig: TXReadItem = initialRow;
        let toOrig: TXReadItem = partnerRow;
        if (pairLayout === 'fx') {
            if (Number(initialRow.cash?.amount ?? 0) > 0) {
                fromOrig = partnerRow; toOrig = initialRow;
            }
        } else if (pairLayout === 'transfer_asset') {
            if (Number(initialRow.quantity) > 0) {
                fromOrig = partnerRow; toOrig = initialRow;
            }
        } else if (pairLayout === 'transfer_cash') {
            if (Number(initialRow.cash?.amount ?? 0) >= 0) {
                fromOrig = partnerRow; toOrig = initialRow;
            }
        }

        const allItems = [
            diffDualItem(items[0], fromOrig as unknown as TxOriginal),
            diffDualItem(items[1], toOrig as unknown as TxOriginal),
        ];
        // Only include items that have actual changes (more than just `id`)
        return allItems.filter((item) => Object.keys(item).length > 1);
    }

    // =========================================================================
    // Commit
    // =========================================================================

    async function commit() {
        if (isReadonly || committing) return;
        // Client-side dual validation
        if (pairLayout && dualValidationError) {
            formError = dualValidationError;
            return;
        }
        // Bugfix-5 §A4: when wired from the BulkModal, "Apply" pushes the draft
        // back to the parent grid instead of committing to the backend.
        if (!commitOnSave) {
            if (pairLayout) {
                // Dual mode: emit full pair payload so BulkModal can create
                // both the visible draft and the hidden partner draft.
                const items = collectDualCreates();
                const payload: Record<string, unknown> = {
                    _dual: true,
                    _items: items,
                    _partnerBrokerId: dualTo.broker_id,
                    _partnerCash: dualTo.cash,
                    _partnerDate: dualTo.date,
                };
                // Also carry the "from" side fields for applyFormPayload
                Object.assign(payload, items[0]);
                onPushDraft?.(payload);
            } else {
                const payload = collectCreate();
                onPushDraft?.(payload);
            }
            onClose();
            return;
        }
        committing = true;
        formError = null;
        commitFailed = false;
        // Anti-bounce: if draft unchanged and < 10s since last commit attempt, skip.
        const currentKey = lastDraftKey;
        if (currentKey === lastCommitDraftKey && Date.now() - lastCommitAt < COMMIT_ANTI_BOUNCE_MS) {
            committing = false;
            return;
        }
        try {
            if (pairLayout) {
                // Dual-form commit — create or update 2 linked transactions
                if (mode === 'edit' && partnerRow) {
                    const payload = {updates: collectDualUpdates()};
                    const result = await saveWithRetry(() => zodiosApi.commit_transactions_api_v1_transactions_commit_post(payload as never), {fallback: $t('transactions.form.saveFailed'), toast: false});
                    if (result.status === 'error') { formError = result.message; return; }
                    const resp = result.data as {committed?: boolean; issues?: ValidationIssue[]; results?: Array<{id?: number}>};
                    if (!resp.committed) { issues = resp.issues ?? []; issuesDismissed = false; commitFailed = true; return; }
                    onCommitted?.({transaction_id: resp.results?.[0]?.id ?? null});
                    onClose();
                } else {
                    const payload = {creates: collectDualCreates()};
                    const result = await saveWithRetry(() => zodiosApi.commit_transactions_api_v1_transactions_commit_post(payload as never), {fallback: $t('transactions.form.saveFailed'), toast: false});
                    if (result.status === 'error') { formError = result.message; return; }
                    const resp = result.data as {committed?: boolean; issues?: ValidationIssue[]; results?: Array<{id?: number | null}>};
                    if (!resp.committed) { issues = resp.issues ?? []; issuesDismissed = false; commitFailed = true; return; }
                    onCommitted?.({transaction_id: resp.results?.[0]?.id ?? null});
                    onClose();
                }
            } else if (mode === 'edit') {
                const payload = {updates: [collectUpdate()]};
                const result = await saveWithRetry(() => zodiosApi.commit_transactions_api_v1_transactions_commit_post(payload as never), {fallback: $t('transactions.form.saveFailed'), toast: false});
                if (result.status === 'error') {
                    formError = result.message;
                    return;
                }
                const resp = result.data as {committed?: boolean; issues?: ValidationIssue[]; results?: Array<{id?: number}>};
                if (!resp.committed) {
                    issues = resp.issues ?? [];
                    issuesDismissed = false;
                    commitFailed = true;
                    return;
                }
                onCommitted?.({transaction_id: resp.results?.[0]?.id ?? null});
                onClose();
            } else {
                // create / duplicate
                const payload = {creates: [collectCreate()]};
                const result = await saveWithRetry(() => zodiosApi.commit_transactions_api_v1_transactions_commit_post(payload as never), {fallback: $t('transactions.form.saveFailed'), toast: false});
                if (result.status === 'error') {
                    formError = result.message;
                    return;
                }
                const resp = result.data as {committed?: boolean; issues?: ValidationIssue[]; results?: Array<{id?: number | null}>};
                if (!resp.committed) {
                    issues = resp.issues ?? [];
                    issuesDismissed = false;
                    commitFailed = true;
                    return;
                }
                onCommitted?.({transaction_id: resp.results?.[0]?.id ?? null});
                onClose();
            }
        } finally {
            committing = false;
            lastCommitDraftKey = currentKey;
            lastCommitAt = Date.now();
        }
    }

    // =========================================================================
    // Field handlers
    // =========================================================================

    function setType(v: string) {
        draft = {...draft, type: v as TransactionTypeCode};
    }
    function setBroker(v: number) {
        draft = {...draft, broker_id: v};
    }
    function setBrokerTo(v: number) {
        dualTo = {...dualTo, broker_id: v};
    }
    function setDate(v: string) {
        draft = {...draft, date: v};
    }
    function setAsset(v: number | null) {
        draft = {...draft, asset_id: v};
        // If the new asset has a known native currency, seed cash code when empty.
        if (v != null && draft.cash == null) {
            const a = getAssetInfo(v);
            if (a?.currency) draft = {...draft, cash: {code: a.currency, amount: ''}};
        }
    }
    function setQuantity(v: string) {
        draft = {...draft, quantity: v};
    }
    function setCash(v: {code: string; amount: string} | null) {
        draft = {...draft, cash: v};
    }
    function setCashTo(v: {code: string; amount: string} | null) {
        dualTo = {...dualTo, cash: v};
    }
    /** W36: Swap Da↔A sides in dual form. */
    function swapDualSides() {
        if (!pairLayout) return;
        // Always swap dates
        const tmpDate = draft.date;
        if (pairLayout === 'fx') {
            // Swap cash (currencies)
            const tmpCash = draft.cash;
            draft = {...draft, cash: dualTo.cash, date: dualTo.date};
            dualTo = {...dualTo, cash: tmpCash, date: tmpDate};
        } else {
            // transfer_asset / transfer_cash: swap brokers
            const tmpBroker = draft.broker_id;
            draft = {...draft, broker_id: dualTo.broker_id, date: dualTo.date};
            dualTo = {...dualTo, broker_id: tmpBroker, date: tmpDate};
        }
    }
    function addTag(raw: string) {
        const v = raw.trim();
        if (!v) return;
        if (draft.tags.includes(v)) return;
        draft = {...draft, tags: [...draft.tags, v]};
    }
    function unlinkEvent() {
        draft = {...draft, asset_event_id: null};
    }

    function onQuantityInput(e: Event) {
        const v = (e.currentTarget as HTMLInputElement).value;
        qtyDisplay = v; // preserve raw user input mid-typing
        setQuantity(v);
    }
    function onDescriptionInput(e: Event) {
        draft = {...draft, description: (e.currentTarget as HTMLTextAreaElement).value};
    }
    function onAssetEventInput(e: Event) {
        const v = (e.currentTarget as HTMLInputElement).value;
        draft = {...draft, asset_event_id: v === '' ? null : Number(v)};
    }
    function onCostBasisInput(e: Event) {
        draft = {...draft, cost_basis_override: (e.currentTarget as HTMLInputElement).value};
    }


    // =========================================================================
    // Quantity / cash sign hints
    // =========================================================================
    // Sign hints — unified for both quantity and cash fields
    // =========================================================================

    /** Label suffix for a sign rule: (+), (−), (≠0), or empty. */
    function signLabel(sign: import('$lib/stores/transactionTypeStore').SignRule): string {
        switch (sign) {
            case 'positive': return '(+)';
            case 'negative': return '(−)';
            case 'nonzero': return '(≠0)';
            default: return '';
        }
    }

    /** Hint text below the field explaining the sign constraint. */
    function signHintText(sign: import('$lib/stores/transactionTypeStore').SignRule): string {
        switch (sign) {
            case 'positive': return $t('transactions.form.hintSignPositive');
            case 'negative': return $t('transactions.form.hintSignNegative');
            case 'zero': return $t('transactions.form.hintSignZero');
            case 'nonzero': return $t('transactions.form.hintSignNonzero');
            default: return '';
        }
    }

    let qtyHint = $derived(signHintText(rule.quantityRule));
    let qtyLabel = $derived(signLabel(rule.quantityRule));
    let cashHint = $derived(signHintText(rule.cashSign));
    let cashLabel = $derived(signLabel(rule.cashSign));

    // =========================================================================
    // W39: Inline broker / asset creation modals
    // =========================================================================
    let createBrokerOpen = $state(false);
    let createAssetOpen = $state(false);

    function handleBrokerCreated(e: CustomEvent<{id: number}>) {
        // BrokerModal dispatches 'created' with {id} + already merges into brokerStore
        draft = {...draft, broker_id: e.detail.id};
        createBrokerOpen = false;
    }
    function handleAssetCreated(assetId: number) {
        draft = {...draft, asset_id: assetId};
        createAssetOpen = false;
    }

    // =========================================================================
    // Validate-state chip text
    // =========================================================================

    /** W42: Deduplicate validation issues by `code` — in dual mode both halves
     *  can produce the same error code, showing it once is enough. */
    function deduplicateIssues(raw: ValidationIssue[]): ValidationIssue[] {
        const seen = new Set<string>();
        return raw.filter((iss) => {
            const key = iss.code ?? iss.error;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    // Bugfix-4 §U16: validate chip removed in favor of the green/warning
    // banners (single source of truth). The footer now shows only an inline
    // "Validating…" indicator while a request is in flight (see template).

</script>

<ModalBase {open} maxWidth="3xl" onRequestClose={requestClose} testId="tx-form-modal" allowOverflow={true} {zIndex}>
    <div class="flex flex-col max-h-[90vh] min-h-[50vh]" data-testid="tx-form-modal-root">
        <!-- ============================================================= -->
        <!-- Header -->
        <!-- ============================================================= -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-gray-100 dark:border-slate-700 shrink-0">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100" data-testid="tx-form-title">
                {#if pairLayout}
                    {#if pairLayout === 'fx'}💱{:else if pairLayout === 'transfer_asset'}📦{:else}🏦{/if}
                    {#if mode === 'edit'}
                        ✎ {dualTitle}
                        {#if initialRow?.id != null && initialRow?.related_transaction_id != null && initialRow.related_transaction_id > 0}
                            #{initialRow.id} ↔ #{initialRow.related_transaction_id}
                        {:else if initialRow?.id != null}
                            #{initialRow.id}
                        {:else}
                            (new pair)
                        {/if}
                    {:else if mode === 'view'}
                        👁 {dualTitle}
                        {#if initialRow?.id != null && initialRow?.related_transaction_id != null && initialRow.related_transaction_id > 0}
                            #{initialRow.id} ↔ #{initialRow.related_transaction_id}
                        {:else if initialRow?.id != null}
                            #{initialRow.id}
                        {/if}
                    {:else}{dualTitle}{/if}
                {:else if mode === 'create'}
                    ➕ {$t('transactions.form.titleCreate')}
                {:else if mode === 'duplicate'}
                    📋 {$t('transactions.form.titleDuplicate')}
                {:else if mode === 'edit'}
                    ✎ {$t('transactions.form.titleEdit')} #{initialRow?.id}
                {:else}
                    👁 {$t('transactions.form.titleView')} #{initialRow?.id}
                {/if}
            </h2>
            <div class="flex items-center gap-1">
                {#if isReadonly && onSwitchToEdit && canEdit}
                    <button class="p-2 text-gray-400 hover:text-libre-green hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors" onclick={onSwitchToEdit} data-testid="tx-form-switch-edit" aria-label="Edit" title={$t('transactions.form.titleEdit') || 'Edit'}>
                        <Pencil size={18} />
                    </button>
                {/if}
                <button class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors" onclick={requestClose} data-testid="tx-form-close" aria-label="Close">
                    <X size={20} />
                </button>
            </div>
        </div>

        <!-- ============================================================= -->
        <!-- Body (scrollable) -->
        <!-- ============================================================= -->
        <div class="overflow-y-auto flex-1 min-h-0 px-5 py-4 space-y-4" data-testid="tx-form-body">
            <!-- Inline banners: red ⛔ for commit failure, green ✓ for valid,
                 yellow for validate issues. Both error types show categorized lists. -->
            {#if formError}
                <InfoBanner variant="error" dismissible ondismiss={() => (formError = null)}>
                    <p class="font-semibold mb-1" data-testid="tx-form-error">⛔ {$t('transactions.form.rolledBackTitle')}</p>
                    <p>{formError}</p>
                </InfoBanner>
            {:else if commitFailed && issues.length > 0}
                <InfoBanner variant="error" dismissible ondismiss={() => (commitFailed = false)}>
                    <p class="font-semibold mb-1" data-testid="tx-form-error">⛔ {$t('transactions.form.rolledBackTitle')}</p>
                    {#if fieldIssues.length > 0}
                        <p class="font-semibold text-sm mt-2 mb-1">{$t('transactions.validate.issuesHeader')}</p>
                        <ul class="list-disc list-inside space-y-0.5 text-sm" data-testid="tx-form-issues">
                            {#each fieldIssues as issue}
                                <li data-testid="tx-form-issue">{resolveIssueMessage(issue, $t, resolverCtx)}</li>
                            {/each}
                        </ul>
                    {/if}
                    {#if balanceIssues.length > 0}
                        <p class="font-semibold text-sm mt-2 mb-1">{$t('transactions.validate.balanceIssuesHeader')}</p>
                        <ul class="list-disc list-inside space-y-0.5 text-sm">
                            {#each balanceIssues as issue}
                                <li>{@html resolveIssueMessage(issue, $t, resolverCtx)}</li>
                            {/each}
                        </ul>
                    {/if}
                </InfoBanner>
            {:else if dualValidationError}
                <InfoBanner variant="warning">
                    <p data-testid="tx-form-dual-error">⚠ {dualValidationError}</p>
                </InfoBanner>
            {:else if showIssuesBanner}
                <InfoBanner variant="warning" dismissible ondismiss={() => (issuesDismissed = true)}>
                    {#if fieldIssues.length > 0}
                        <p class="font-semibold text-sm mb-1.5" data-testid="tx-form-issues-header">{getBulkContext ? $t('transactions.validate.contextualIssuesHeader') : $t('transactions.validate.issuesHeader')}</p>
                        <ul class="list-disc list-inside space-y-0.5 text-sm" data-testid="tx-form-issues">
                            {#each fieldIssues as issue}
                                <li data-testid="tx-form-issue">{resolveIssueMessage(issue, $t, resolverCtx)}</li>
                            {/each}
                        </ul>
                    {/if}
                    {#if balanceIssues.length > 0}
                        <p class="font-semibold text-sm {fieldIssues.length > 0 ? 'mt-2' : ''} mb-1.5">{$t('transactions.validate.balanceIssuesHeader')}</p>
                        <ul class="list-disc list-inside space-y-0.5 text-sm">
                            {#each balanceIssues as issue}
                                <li>{@html resolveIssueMessage(issue, $t, resolverCtx)}</li>
                            {/each}
                        </ul>
                    {/if}
                </InfoBanner>
            {/if}

            <!-- Loading partner indicator (dual-form edit) -->
            {#if loadingPartner}
                <InfoBanner variant="info">
                    <p class="text-sm">{$t('transactions.form.loadingPartner')}</p>
                </InfoBanner>
            {/if}

            <!-- ============================================================= -->
            <!-- DUAL FORM — FX / Transfer Asset / Transfer Cash -->
            <!-- ============================================================= -->
            {#if pairLayout}
                <fieldset class="border border-gray-200 dark:border-slate-700 rounded-lg p-4" data-testid="tx-form-required">
                    <legend class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 px-1">{$t('transactions.form.sectionRequired')}</legend>

                    <!-- Type (date is now inside Da/A panels) -->
                    <div class="text-sm">
                        <!-- Type: editable in create dual mode (W41), readonly in edit/view -->
                        <div class="flex flex-col gap-1" data-testid="tx-form-type-wrap">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.type')}</span>
                            {#if typeImmutable}
                                <div class="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-gray-200" data-testid="tx-form-type-readonly">
                                    <img src={getTransactionTypeIconUrl(draft.type)} alt="" class="w-6 h-6 object-contain shrink-0" onerror={(e) => { const el = e.currentTarget; if (el instanceof HTMLImageElement) el.style.display = 'none'; }} />
                                    <span class="font-medium">{dualTitle}</span>
                                </div>
                            {:else}
                                <TransactionTypeSearchSelect value={draft.type} onchange={(v) => setType(v)} disabled={isReadonly} types={allowedTypes} testid="tx-form-type" />
                            {/if}
                        </div>
                    </div>

                    <!-- FX: shared broker -->
                    {#if pairLayout === 'fx'}
                        <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-broker-wrap">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</span>
                            {#if brokerImmutable}
                                {@const b = brokers.find((br) => br.id === draft.broker_id)}
                                <div class="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-gray-200" data-testid="tx-form-broker-readonly">
                                    <BrokerIcon iconUrl={b?.icon_url ?? null} portalUrl={b?.portal_url ?? null} pluginCode={b?.default_import_plugin ?? null} altText={b?.name ?? ''} size="sm" />
                                    <span class="font-medium">{b?.name ?? `#${draft.broker_id}`}</span>
                                </div>
                            {:else}
                                <BrokerSearchSelect brokers={brokersForSelect} value={brokerIdValue} onchange={(id) => setBroker(id ?? 0)} />
                            {/if}
                        </div>
                    {/if}

                    <!-- Transfer Asset: shared asset + quantity -->
                    {#if pairLayout === 'transfer_asset'}
                        <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-asset-wrap">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.asset')} *</span>
                            <AssetSelect bind:value={draft.asset_id} disabled={isReadonly} onchange={setAsset} testid="tx-form-asset" createLabel={isReadonly ? undefined : ($t('assets.create') || 'New asset')} onCreateNew={isReadonly ? undefined : (() => (createAssetOpen = true))} />
                        </div>
                        <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-quantity-wrap">
                            <span class="text-xs text-gray-500 dark:text-gray-400">
                                {$t('transactions.table.quantity')} <span class="text-amber-500">(+)</span>
                            </span>
                            <input
                                type="number"
                                step="any"
                                inputmode="decimal"
                                autocomplete="off"
                                spellcheck="false"
                                name="qty-{autocompleteNonce}"
                                class="qty-input w-full px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg text-right font-mono tabular-nums disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-libre-green/30"
                                value={qtyDisplay}
                                disabled={isReadonly}
                                oninput={onQuantityInput}
                                onblur={() => (qtyDisplay = formatDecimalForDisplay(draft.quantity))}
                                data-testid="tx-form-quantity"
                            />
                        </div>
                    {/if}

                    <!-- Transfer Cash: shared cash -->
                    {#if pairLayout === 'transfer_cash'}
                        <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-cash-wrap">
                            <span class="text-xs text-gray-500 dark:text-gray-400">
                                {$t('transactions.table.cash')} *
                            </span>
                            <CompactCashCell value={draft.cash} onChange={setCash} signHint="positive" disabled={isReadonly} testid="tx-form-cash" defaultCode="EUR" />
                        </div>
                    {/if}

                    <!-- ============================================================= -->
                    <!-- Da / A split section -->
                    <!-- ============================================================= -->
                    <div class="mt-4 grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-3 items-start overflow-hidden" data-testid="tx-form-dual-split">
                        <!-- DA (From) -->
                        <div class="border border-gray-200 dark:border-slate-700 rounded-lg p-3 min-w-0" data-testid="tx-form-dual-from">
                            <div class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.form.from')}</div>
                            <!-- Date (from side) -->
                            <div class="flex flex-col gap-1 mb-2">
                                <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.date')}</span>
                                {#if isReadonly}
                                    <div class="px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-gray-200">{draft.date || '—'}</div>
                                {:else}
                                    <SingleDatePicker bind:value={draft.date} label="" inputStyle={true} onchange={(d) => setDate(d)} />
                                {/if}
                            </div>
                            {#if pairLayout === 'fx'}
                                <CompactCashCell value={draft.cash} onChange={setCash} signHint="positive" disabled={isReadonly} testid="tx-form-cash-from" defaultCode="EUR" />
                            {:else}
                                <!-- transfer_asset / transfer_cash: broker from -->
                                <div class="flex flex-col gap-1">
                                    <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</span>
                                    <BrokerSearchSelect brokers={brokersForFrom} value={brokerIdValue} onchange={(id) => setBroker(id ?? 0)} disabled={isReadonly} />
                                </div>
                            {/if}
                        </div>

                        <!-- Arrow (clickable to swap Da↔A) -->
                        <button type="button" class="hidden sm:flex items-center justify-center text-gray-400 dark:text-gray-500 hover:text-libre-green dark:hover:text-libre-green self-center p-1 rounded-full hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors" onclick={swapDualSides} title={$t('transactions.form.swapSides') || 'Swap sides'} data-testid="tx-form-dual-swap" disabled={isReadonly}>
                            <ArrowRight size={20} />
                        </button>
                        <button type="button" class="flex sm:hidden items-center justify-center text-gray-400 dark:text-gray-500 hover:text-libre-green dark:hover:text-libre-green p-1 rounded-full hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors" onclick={swapDualSides} title={$t('transactions.form.swapSides') || 'Swap sides'} data-testid="tx-form-dual-swap-mobile" disabled={isReadonly}>
                            <ArrowDown size={20} />
                        </button>

                        <!-- A (To) -->
                        <div class="border border-gray-200 dark:border-slate-700 rounded-lg p-3 min-w-0" data-testid="tx-form-dual-to">
                            <div class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">{$t('transactions.form.to')}</div>
                            <!-- Date (to side) — hidden when partner is inaccessible (role=null or not in store) -->
                            {#if inaccessiblePartnerBrokerId != null || (isReadonly && !partnerRow && dualTo.broker_id > 0 && getBrokerRole(dualTo.broker_id) == null)}
                                <!-- partner inaccessible — hide date -->
                            {:else}
                            <div class="flex flex-col gap-1 mb-2">
                                <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.date')}</span>
                                {#if isReadonly}
                                    <div class="px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-gray-200">{dualTo.date || '—'}</div>
                                {:else}
                                    <SingleDatePicker bind:value={dualTo.date} label="" inputStyle={true} onchange={(d) => { dualTo = {...dualTo, date: d}; }} />
                                {/if}
                            </div>
                            {/if}
                            {#if pairLayout === 'fx'}
                                <CompactCashCell value={dualTo.cash} onChange={setCashTo} signHint="positive" disabled={isReadonly} testid="tx-form-cash-to" defaultCode="USD" />
                            {:else}
                                <!-- transfer_asset / transfer_cash: broker to -->
                                <div class="flex flex-col gap-1">
                                    {#if inaccessiblePartnerBrokerId == null}
                                        <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</span>
                                    {/if}
                                    {#if inaccessiblePartnerBrokerId != null}
                                        {@const pInfo = getBrokerInfo(inaccessiblePartnerBrokerId)}
                                        {@const RoleIconC = getRoleIcon(null)}
                                        <div class="flex flex-col gap-1.5 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400" data-testid="tx-form-partner-locked">
                                            <div class="flex items-center gap-1.5">
                                                {#if pInfo?.icon_url || pInfo?.portal_url || pInfo?.default_import_plugin}
                                                    <BrokerIcon iconUrl={pInfo.icon_url} portalUrl={pInfo.portal_url} pluginCode={pInfo.default_import_plugin} altText={pInfo.name ?? ''} size="sm" />
                                                {/if}
                                                <strong>{pInfo?.name ?? `#${inaccessiblePartnerBrokerId}`}</strong>
                                                <RoleIconC size={14} class="{getRoleIconColor(null)} shrink-0" />
                                            </div>
                                            <span class="text-xs leading-relaxed">{$t('transactions.access.partnerNotAccessible')}</span>
                                        </div>
                                    {:else if isReadonly}
                                        <!-- Bug10/13-fix: in view mode show static broker info -->
                                        {@const toInfo = getBrokerInfo(dualTo.broker_id)}
                                        {@const toRole = toInfo ? getBrokerRole(dualTo.broker_id) : null}
                                        <div class="flex {toRole == null && toInfo ? 'flex-col gap-1.5' : 'items-center gap-2'} px-3 py-2 {toRole == null && toInfo ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-600 dark:text-red-400' : 'bg-gray-50 dark:bg-slate-800 border-gray-200 dark:border-slate-700 text-gray-700 dark:text-gray-200'} border rounded-lg text-sm" data-testid="tx-form-broker-to-readonly">
                                            {#if toInfo && toRole != null}
                                                <!-- Accessible broker (OWNER/EDITOR/VIEWER) -->
                                                {@const RoleIcon = getRoleIcon(toRole)}
                                                <BrokerIcon iconUrl={toInfo.icon_url} portalUrl={toInfo.portal_url} pluginCode={toInfo.default_import_plugin} altText={toInfo.name} size="sm" />
                                                <span class="font-medium">{toInfo.name}</span>
                                                <RoleIcon size={14} class="{getRoleIconColor(toRole)} shrink-0" />
                                            {:else if toInfo && toRole == null}
                                                <!-- Broker in store but role=null (hidden/admin) — show lock -->
                                                {@const LockIcon = getRoleIcon(null)}
                                                {@const lockColor = getRoleIconColor(null)}
                                                <div class="flex items-center gap-1.5">
                                                    {#if toInfo.icon_url || toInfo.portal_url || toInfo.default_import_plugin}
                                                        <BrokerIcon iconUrl={toInfo.icon_url} portalUrl={toInfo.portal_url} pluginCode={toInfo.default_import_plugin} altText={toInfo.name ?? ''} size="sm" />
                                                    {/if}
                                                    <strong>{toInfo.name}</strong>
                                                    <LockIcon size={14} class="{lockColor} shrink-0" />
                                                </div>
                                                <span class="text-xs leading-relaxed">{$t('transactions.access.partnerNotAccessible')}</span>
                                            {:else if dualTo.broker_id > 0}
                                                <!-- Broker not in store at all -->
                                                {@const LockIcon2 = getRoleIcon(null)}
                                                {@const lockColor2 = getRoleIconColor(null)}
                                                <LockIcon2 size={14} class="{lockColor2} shrink-0" />
                                                <span class="text-gray-500 dark:text-gray-400">#{dualTo.broker_id} — {$t('transactions.access.partnerNotAccessible')}</span>
                                            {:else}
                                                <span class="text-gray-400">—</span>
                                            {/if}
                                        </div>
                                    {:else}
                                        <BrokerSearchSelect brokers={brokersForTo} value={brokerToIdValue} onchange={(id) => setBrokerTo(id ?? 0)} disabled={isReadonly} />
                                    {/if}
                                </div>
                            {/if}
                        </div>
                    </div>

                    <!-- Cost basis override for transfer_asset -->
                    {#if pairLayout === 'transfer_asset'}
                        <div class="mt-3 flex flex-col gap-1">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.form.costBasis')}</span>
                            <input
                                type="number"
                                step="any"
                                inputmode="decimal"
                                autocomplete="off"
                                name="cb-{autocompleteNonce}"
                                class="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-libre-green/30 text-sm"
                                placeholder="auto"
                                value={draft.cost_basis_override}
                                disabled={isReadonly}
                                oninput={onCostBasisInput}
                                data-testid="tx-form-cost-basis"
                            />
                        </div>
                    {/if}
                </fieldset>

            <!-- ============================================================= -->
            <!-- STANDARD SINGLE FORM (unchanged) -->
            <!-- ============================================================= -->
            {:else}
                <!-- Required section -->
                <fieldset class="border border-gray-200 dark:border-slate-700 rounded-lg p-4" data-testid="tx-form-required">
                    <legend class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 px-1">{$t('transactions.form.sectionRequired')}</legend>

                    <!-- Reordered to match table column order (Bugfix-1 §U5):
                         Date → Type → Quantity → Cash → Asset → Broker.
                         Bugfix-5 §U21: Date+Type are kept in a 2-col mini-grid
                         even on mobile (always-on, never wraps to 1-col); Qty/Cash
                         get their own sub-grid that collapses to a single
                         full-width Cash row when the type forces quantity=0. -->
                    <div class="grid grid-cols-2 gap-3 text-sm">
                        <!-- Date -->
                        <div class="flex flex-col gap-1" data-testid="tx-form-date-wrap">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.date')}</span>
                            {#if isReadonly}
                                <div class="px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-gray-200" data-testid="tx-form-date-readonly">{draft.date || '—'}</div>
                            {:else}
                                <SingleDatePicker bind:value={draft.date} label="" inputStyle={true} onchange={(d) => setDate(d)} />
                            {/if}
                        </div>

                        <!-- Type -->
                        <div class="flex flex-col gap-1" data-testid="tx-form-type-wrap">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.type')}</span>
                            {#if typeImmutable}
                                <!-- Bugfix-4 §U17 + Bugfix-5 §U22: render the
                                     readonly type as a plain inline [icon] [name]
                                     row matching the table cell rendering — icon
                                     enlarged (w-6 h-6) so it stays legible
                                     alongside the other selectors. -->
                                <div class="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-gray-200" data-testid="tx-form-type-readonly">
                                    <img src={getTransactionTypeIconUrl(draft.type)} alt="" class="w-6 h-6 object-contain shrink-0" onerror={(e) => { const el = e.currentTarget; if (el instanceof HTMLImageElement) el.style.display = 'none'; }} />
                                    <span class="font-medium">{$t(`transactions.types.${draft.type}`) || draft.type}</span>
                                </div>
                            {:else}
                                <TransactionTypeSearchSelect value={draft.type} onchange={(v) => setType(v)} disabled={isReadonly} types={allowedTypes} testid="tx-form-type" />
                            {/if}
                        </div>
                    </div>

                    <!-- Quantity + Cash sub-grid.
                         Symmetric visibility: forbidden fields disappear entirely,
                         the remaining field takes full width (col-span-2). -->
                    <div class="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                        {#if rule.quantityMode !== 'forbidden' && rule.cashField !== 'forbidden'}
                            <!-- Both visible: 2-col layout -->
                            <div class="flex flex-col gap-1" data-testid="tx-form-quantity-wrap">
                                <span class="text-xs text-gray-500 dark:text-gray-400">
                                    {$t('transactions.table.quantity')}{#if qtyLabel} <span class="text-amber-500">{qtyLabel}</span>{/if}
                                </span>
                                <input
                                    type="number"
                                    step="any"
                                    inputmode="decimal"
                                    autocomplete="off"
                                    spellcheck="false"
                                    name="qty-{autocompleteNonce}"
                                    class="qty-input w-full px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg text-right font-mono tabular-nums disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-libre-green/30"
                                    value={qtyDisplay}
                                    disabled={isReadonly}
                                    oninput={onQuantityInput}
                                    onblur={() => (qtyDisplay = formatDecimalForDisplay(draft.quantity))}
                                    data-testid="tx-form-quantity"
                                />
                                {#if qtyHint}
                                    <span class="text-[10px] text-gray-400">{qtyHint}</span>
                                {/if}
                            </div>
                            <div class="flex flex-col gap-1" data-testid="tx-form-cash-wrap">
                                <span class="text-xs text-gray-500 dark:text-gray-400">
                                    {$t('transactions.table.cash')}{rule.cashField === 'required' ? ' *' : ''}{#if cashLabel} <span class="text-amber-500">{cashLabel}</span>{/if}
                                </span>
                                <CompactCashCell value={draft.cash} onChange={setCash} signHint={rule.cashSign} disabled={isReadonly} testid="tx-form-cash" defaultCode={(draft.asset_id != null && getAssetInfo(draft.asset_id)?.currency) || 'EUR'} originalCurrency={draft.asset_id != null ? getAssetInfo(draft.asset_id)?.currency : undefined} />
                                {#if cashHint}
                                    <span class="text-[10px] text-gray-400">{cashHint}</span>
                                {/if}
                            </div>
                        {:else if rule.quantityMode !== 'forbidden'}
                            <!-- Only quantity visible (cash forbidden) → full width -->
                            <div class="flex flex-col gap-1 col-span-2" data-testid="tx-form-quantity-wrap">
                                <span class="text-xs text-gray-500 dark:text-gray-400">
                                    {$t('transactions.table.quantity')}{#if qtyLabel} <span class="text-amber-500">{qtyLabel}</span>{/if}
                                </span>
                                <input
                                    type="number"
                                    step="any"
                                    inputmode="decimal"
                                    autocomplete="off"
                                    spellcheck="false"
                                    name="qty-{autocompleteNonce}"
                                    class="qty-input w-full px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg text-right font-mono tabular-nums disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-libre-green/30"
                                    value={qtyDisplay}
                                    disabled={isReadonly}
                                    oninput={onQuantityInput}
                                    onblur={() => (qtyDisplay = formatDecimalForDisplay(draft.quantity))}
                                    data-testid="tx-form-quantity"
                                />
                                {#if qtyHint}
                                    <span class="text-[10px] text-gray-400">{qtyHint}</span>
                                {/if}
                            </div>
                        {:else if rule.cashField !== 'forbidden'}
                            <!-- Only cash visible (quantity forbidden) → full width -->
                            <div class="flex flex-col gap-1 col-span-2" data-testid="tx-form-cash-wrap">
                                <span class="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
                                    {$t('transactions.table.cash')}{rule.cashField === 'required' ? ' *' : ''}{#if cashLabel} <span class="text-amber-500">{cashLabel}</span>{/if}
                                    <span class="text-[10px] text-gray-400 italic" data-testid="tx-form-quantity-locked">· {$t('transactions.form.hintSignZero')}</span>
                                </span>
                                <CompactCashCell value={draft.cash} onChange={setCash} signHint={rule.cashSign} disabled={isReadonly} testid="tx-form-cash" defaultCode={(draft.asset_id != null && getAssetInfo(draft.asset_id)?.currency) || 'EUR'} originalCurrency={draft.asset_id != null ? getAssetInfo(draft.asset_id)?.currency : undefined} />
                                {#if cashHint}
                                    <span class="text-[10px] text-gray-400">{cashHint}</span>
                                {/if}
                            </div>
                        {/if}
                        <!-- Both forbidden: nothing rendered (no current type uses this) -->
                    </div>

                    <!-- Asset (full width) -->
                    {#if rule.assetField !== 'forbidden'}
                        <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-asset-wrap">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.asset')}{rule.assetField === 'required' ? ' *' : ''}{#if rule.assetField === 'optional'} <span class="text-gray-400 italic">({$t('common.optional')})</span>{/if}</span>
                            <AssetSelect bind:value={draft.asset_id} disabled={isReadonly} onchange={setAsset} testid="tx-form-asset" createLabel={isReadonly ? undefined : ($t('assets.create') || 'New asset')} onCreateNew={isReadonly ? undefined : (() => (createAssetOpen = true))} />
                        </div>
                    {/if}

                    <!-- Broker (full width, last) -->
                    <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-broker-wrap">
                        <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.broker')}</span>
                        {#if brokerImmutable}
                            {@const b = brokers.find((br) => br.id === draft.broker_id)}
                            <!-- Bugfix-4 §U19: readonly broker also shows the icon
                                 (parity with the editable BrokerSearchSelect). -->
                            <div class="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-gray-200" data-testid="tx-form-broker-readonly">
                                <BrokerIcon iconUrl={b?.icon_url ?? null} portalUrl={b?.portal_url ?? null} pluginCode={b?.default_import_plugin ?? null} altText={b?.name ?? ''} size="sm" />
                                <span class="font-medium">{b?.name ?? `#${draft.broker_id}`}</span>
                            </div>
                        {:else}
                            <BrokerSearchSelect brokers={brokersForSelect} value={brokerIdValue} onchange={(id) => setBroker(id ?? 0)} createLabel={$t('common.createNew') || 'Create new'} onCreateNew={() => (createBrokerOpen = true)} />
                        {/if}
                    </div>
                </fieldset>
            {/if}

            <!-- Optional disclosure -->
            {#if !isReadonly || draft.tags.length > 0 || draft.description.trim()}
                <details class="border border-gray-200 dark:border-slate-700 rounded-lg" bind:open={optionalOpen}>
                    <summary class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 px-4 py-3 cursor-pointer select-none" data-testid="tx-form-optional-toggle">{$t('transactions.form.sectionOptional')}</summary>
                    <div class="px-4 pb-4 space-y-3 text-sm">
                        <!-- Tags -->
                        <div class="flex flex-col gap-1">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.form.tags')}</span>
                            <TagInput
                                value={draft.tags}
                                availableTags={availableTags}
                                placeholder={$t('transactions.form.tagsPlaceholder')}
                                disabled={isReadonly}
                                onchange={(v) => { draft = {...draft, tags: v}; }}
                            />
                        </div>

                        <!-- Description -->
                        <label class="flex flex-col gap-1">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.form.description')}</span>
                            <textarea autocomplete="off" class="px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg resize-y min-h-[60px] disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-libre-green/30" rows="2" bind:value={draft.description} disabled={isReadonly} oninput={onDescriptionInput} data-testid="tx-form-description" maxlength="500"></textarea>
                        </label>
                    </div>
                </details>
            {/if}

            <!-- Advanced disclosure (Bugfix-1 §U6: gated) — hidden in dual mode -->
            {#if showAdvancedSection}
                <details class="border border-gray-200 dark:border-slate-700 rounded-lg" bind:open={advancedOpen}>
                    <summary class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 px-4 py-3 cursor-pointer select-none" data-testid="tx-form-advanced-toggle">{$t('transactions.form.sectionAdvanced')}</summary>
                    <div class="px-4 pb-4 space-y-3 text-sm">
                        <!-- Asset event link -->
                        {#if canShowAssetEvent}
                            <div class="flex items-center gap-2">
                                <span class="text-xs text-gray-500 dark:text-gray-400 w-32 shrink-0">{$t('transactions.form.assetEvent')}</span>
                                <input type="number" autocomplete="off" name="event-{autocompleteNonce}" class="flex-1 px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg disabled:opacity-60" placeholder="event id" value={draft.asset_event_id ?? ''} disabled={isReadonly} oninput={onAssetEventInput} data-testid="tx-form-asset-event" />
                                {#if draft.asset_event_id != null && !isReadonly}
                                    <button type="button" class="text-xs text-gray-500 hover:text-red-500" onclick={unlinkEvent} data-testid="tx-form-asset-event-unlink">{$t('transactions.form.unlink')}</button>
                                {/if}
                            </div>
                        {/if}

                        <!-- Cost basis override (TRANSFER only) -->
                        {#if showCostBasisField}
                            <label class="flex items-center gap-2">
                                <span class="text-xs text-gray-500 dark:text-gray-400 w-32 shrink-0">{$t('transactions.form.costBasis')}</span>
                                <input type="number" step="any" inputmode="decimal" autocomplete="off" name="cb-{autocompleteNonce}" class="flex-1 px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg disabled:opacity-60" placeholder="auto" value={draft.cost_basis_override} disabled={isReadonly} oninput={onCostBasisInput} data-testid="tx-form-cost-basis" />
                            </label>
                        {/if}

                        <!-- link_uuid (readonly) -->
                        {#if draft.link_uuid}
                            <div class="flex items-center gap-2">
                                <span class="text-xs text-gray-500 dark:text-gray-400 w-32 shrink-0">{$t('transactions.form.linkUuid')}</span>
                                <code class="text-[10px] font-mono text-gray-500 dark:text-gray-400 truncate" data-testid="tx-form-link-uuid">{draft.link_uuid}</code>
                            </div>
                        {/if}

                        <!-- Pair partner chip -->
                        {#if pairPartnerId}
                            <div class="flex items-center gap-2">
                                <span class="text-xs text-gray-500 dark:text-gray-400 w-32 shrink-0">{$t('transactions.form.pairPartner')}</span>
                                <button type="button" class="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-900/50" data-testid="tx-form-pair-partner">
                                    #{pairPartnerId}
                                </button>
                            </div>
                        {/if}
                    </div>
                </details>
            {/if}

            <!-- Read-only footer (edit/view) -->
            {#if (mode === 'edit' || mode === 'view') && initialRow}
                <div class="text-[10px] text-gray-400 dark:text-gray-500 border-t border-gray-100 dark:border-slate-800 pt-3" data-testid="tx-form-readonly-footer">
                    ID #{initialRow.id}
                    {#if partnerRow}+ #{partnerRow.id}{/if}
                    {#if initialRow.created_at}· {$t('common.created')} {initialRow.created_at}{/if}
                    {#if initialRow.updated_at}· {$t('common.updated')} {initialRow.updated_at}{/if}
                </div>
            {/if}
        </div>

        <!-- ============================================================= -->
        <!-- Footer -->
        <!-- ============================================================= -->
        <div class="flex items-center justify-between gap-2 px-5 py-3 border-t border-gray-100 dark:border-slate-700 shrink-0 text-xs">
            <div class="flex items-center gap-2 flex-wrap">
                {#if !isReadonly}
                    <button type="button" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={() => scheduler.trigger('manual')} data-testid="tx-form-validate-now" title={$t('transactions.validate.now')}>
                        ⚡ <span class="hidden sm:inline">{$t('transactions.validate.now')}</span>
                    </button>
                {/if}
                {#if scheduler.state.isValidating}
                    <span class="text-[11px] text-gray-500 dark:text-gray-400">{$t('transactions.validate.validating')}</span>
                {:else if isFreshlyValid}
                    <span class="text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-1" data-testid="tx-form-valid-inline">
                        <Check size={14} /> {$t('transactions.validate.ok')}
                    </span>
                {/if}
            </div>
            <div class="flex items-center gap-2">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 inline-flex items-center gap-1.5" onclick={requestClose} data-testid="tx-form-cancel" title={isReadonly ? $t('common.close') || 'Close' : $t('common.cancel')}><X size={15} /> <span class="hidden sm:inline">{isReadonly ? $t('common.close') || 'Close' : $t('common.cancel')}</span></button>
                {#if !isReadonly}
                    <button type="button" class="px-4 py-2 text-sm rounded-lg text-white bg-libre-green hover:bg-libre-green/90 disabled:opacity-50 inline-flex items-center gap-1.5" disabled={committing || loadingPartner || !!dualValidationError || (!commitOnSave && !isFormComplete)} onclick={commit} data-testid="tx-form-save" title={committing ? ($t('common.saving')) : (!commitOnSave ? ($t('transactions.form.apply')) : ($t('common.save')))}>
                        {#if committing}
                            <span class="hidden sm:inline">{$t('common.saving')}</span>
                        {:else if !commitOnSave}
                            <Check size={16} /> <span class="hidden sm:inline">{$t('transactions.form.apply')}</span>
                        {:else}
                            <Save size={15} /> <span class="hidden sm:inline">{$t('common.save')}</span>
                        {/if}
                    </button>
                {/if}
            </div>
        </div>
    </div>
</ModalBase>

<!-- Bugfix-3 §C11: confirm dialog when closing with unsaved changes. -->
<ConfirmModal
    open={confirmCloseOpen}
    title={$t('common.discardChanges') || 'Discard changes?'}
    message={$t('common.discardChangesMessage')}
    confirmText={$t('common.discard') || $t('common.confirm')}
    cancelText={$t('common.cancel')}
    warning
    onConfirm={confirmDiscardAndClose}
    onCancel={() => (confirmCloseOpen = false)}
    zIndex={70}
/>

<!-- W39: Inline broker creation modal. BrokerModal is Svelte 4 (event dispatcher). -->
<BrokerModal isOpen={createBrokerOpen} mode="create" zIndex={zIndex + 10} on:created={handleBrokerCreated} on:close={() => (createBrokerOpen = false)} />

<!-- W39: Inline asset creation modal. AssetModal is Svelte 5 (runes). -->
<AssetModal bind:open={createAssetOpen} zIndex={zIndex + 10} oncreated={handleAssetCreated} onclose={() => (createAssetOpen = false)} />

<style>
    /* Bugfix-5 walkthrough #6: numeric inputs (quantity, cost basis) — hide
       the browser spinner controls so the field reads cleaner alongside the
       hint text and matches the CompactCashCell amount input. */
    :global(.qty-input)::-webkit-outer-spin-button,
    :global(.qty-input)::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    :global(.qty-input) {
        -moz-appearance: textfield;
        appearance: textfield;
    }
</style>

