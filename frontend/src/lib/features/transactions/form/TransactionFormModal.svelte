<!--
  TransactionFormModal.svelte — Single-row CRUD modal for transactions.

  Modes:
  - 'create'   → blank form, POST /transactions/commit with 1 item in creates
  - 'edit'     → pre-filled from items[0] (id immutable, type/broker locked),
                   POST /transactions/commit with 1 TXUpdateItem in updates
  - 'view'     → readonly display (Save button hidden)

  With commitOnSave=false, Apply only emits the local draft to BulkModal;
  the parent owns batch validation and commit.

  Field gating per type comes from `transactionTypeStore.ts` (UI hint only —
  authoritative validation is server-side via POST /transactions/validate).

  Sections:
   • Required: type, broker, date, asset (gated), quantity, cash
   • Optional (collapsible): tags, description, asset_event_id,
     cost_basis_override, link_uuid (RO), pair-partner chip
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
    import {todayIso} from '$lib/utils/dateOnly';
    import {onDestroy, untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {X, ArrowRight, ArrowDown, Check, Pencil, Save, Info} from 'lucide-svelte';
    import {getRoleIcon, getRoleIconColor} from '$lib/utils/broker/brokerRoleHelpers';
    import {getBrokerIconHtmlById} from '$lib/utils/broker/brokerHelpers';

    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import BrokerSearchSelect from '$lib/components/ui/select/BrokerSearchSelect.svelte';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import TagInput from '$lib/components/ui/input/TagInput.svelte';
    import ExactQuantityInput from '$lib/components/ui/input/ExactQuantityInput.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import CompactCashCell from '$lib/features/transactions/form/CompactCashCell.svelte';
    import FxSyncModal from '$lib/components/fx/FxSyncModal.svelte';
    import TransactionTypeSearchSelect from '../TransactionTypeSearchSelect.svelte';
    import WacPreviewSection from '../wac/WacPreviewSection.svelte';
    import AssetEventPicker from '../events/AssetEventPicker.svelte';
    import EventCreateMiniModal from '../events/EventCreateMiniModal.svelte';
    import BrokerModal from '$lib/features/brokers/BrokerModal.svelte';
    import AssetModal from '$lib/components/assets/AssetModal.svelte';

    import {zodiosApi} from '$lib/api';
    import {ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
    import {ensureAssetsLoaded, getAssetInfo, getAllAssets, refreshAllAssets} from '$lib/stores/reference/assetStore';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {ensureBrokersLoaded, getEditableBrokers, brokerStoreVersion, refreshAllBrokers, getBrokerInfo, getBrokerRole, type BrokerInfo} from '$lib/stores/reference/brokerStore';
    import {type TransactionTypeCode, type PairFormLayout, getTransactionTypeIconUrl, getTypeRule, getPairFormLayout, isDraftReadyForValidation, ensureTypesLoaded, getSwapGroup, typesVersion} from '$lib/features/transactions/transactionTypeStore';
    import {createValidateScheduler} from '$lib/features/transactions/useValidateScheduler.svelte';
    import {commitTransactions, validateTransactions} from '$lib/features/transactions/txCommitApi';
    import {resolveIssueMessage, type ResolverContext} from '$lib/features/transactions/resolveValidationMessage';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';
    import {generateUUID} from '$lib/utils/core/uuid';
    import {computeSignHint} from '$lib/features/transactions/form/signHintColor';
    import {deduplicateIssues, signLabel, signHintKey} from '$lib/features/transactions/form/txFormFields';
    import {isBulkBalanceIssue} from '$lib/features/transactions/bulk/bulkDisplay';
    import {applySign, buildCreatePayload, buildUpdateDiff, diffDualItem, buildDualCreatePayloads, exactDecimalSign, upgradeAutoToDetail, type TxFields, type TxOriginal, type TxDualSide, type PairFormLayout as PayloadPairLayout} from '$lib/features/transactions/txPayloadHelpers';
    import {exceedsSignificantDigits, REAL_SIGNIFICANT_DIGITS} from '$lib/utils/core/parseDecimalInput';
    import {lookupFxRate, type FxDataPoint} from '$lib/stores/fxStoreRegistry';
    import {computeFxConversionInfo, buildFxTooltipData, buildFxTooltipHtml} from '$lib/utils/currency/fxConversionHelper';
    import type {TXReadItem} from '../types';
    import {type FormModalItems, isInaccessible} from '../resolveFormItems';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {formatFixed} from '$lib/utils/core/formatFixed';
    import type {DualDraftTo, FormDraft, TxFormWacResult, ValidationIssue} from './txFormTypes';
    import TxFormBanners from './TxFormBanners.svelte';
    import TxFormPairSection from './TxFormPairSection.svelte';
    import TxFormSingleSection from './TxFormSingleSection.svelte';
    import TxFormOptionalSection from './TxFormOptionalSection.svelte';

    // =========================================================================
    // Types
    // =========================================================================

    type Mode = 'create' | 'edit' | 'view';

    interface Props {
        open: boolean;
        mode: Mode;
        /** Unified items input: [main] | [main, partner] | [main, InaccessiblePartner] | null.
         *  Replaces the old `initialRow` + `injectedPartnerRow` pair.
         *  Built by resolveFormItemsForView / resolveFormItemsFromOps. */
        items?: FormModalItems | null;
        /** When opened from the wizard: pre-select this broker. */
        forcedBroker?: number | null;
        /** Soft default (unlike forcedBroker, does NOT lock the field) — e.g. when
         *  opened from a broker-scoped page: pre-populate but let the user change it. */
        defaultBrokerId?: number | null;
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
        /** V5: WAC result getter — when non-null, WacPreviewSection uses external
         *  mode (no own fetch). Provided by BulkModal's single source of truth. */
        getWacResult?: ((tempId: string) => TxFormWacResult | null) | null;
        /** V5: The tempId of the op currently being edited in the BulkModal. */
        editingTempId?: string | null;
        /** Set of TX IDs from the current batch (uncommitted). Passed to WacPreviewSection for pending markers. */
        pendingTxIds?: Set<number> | null;
        /** When true, the optional section (description, tags, etc.) is expanded when the modal opens. Default false. */
        initialOptionalOpen?: boolean;
    }

    let {
        open,
        mode,
        items = null,
        forcedBroker = null,
        defaultBrokerId = null,
        commitOnSave = true,
        unlockImmutable = false,
        availableTags = [],
        zIndex = 50,
        onClose,
        onCommitted,
        onPushDraft,
        onSwitchToEdit,
        canEdit = true,
        openKey = 0,
        getBulkContext,
        getWacResult = null,
        editingTempId = null,
        pendingTxIds = null,
        initialOptionalOpen = false,
    }: Props = $props();

    let guideObservedOpen = false;

    function releaseCreateGuideHost(): void {
        if (onboardingGuide.active?.flow === 'transaction_create_guide') {
            onboardingGuide.dismissHost({restartAtFirst: true});
        }
        onboardingGuide.clearQueued('transaction_create_guide');
        guideObservedOpen = false;
    }

    $effect(() => {
        const isOpen = open && mode === 'create';
        if (isOpen && !guideObservedOpen) {
            guideObservedOpen = true;
            onboardingGuide.maybeStartContextual('transaction_create_guide');
            return;
        }
        if (!isOpen && guideObservedOpen) {
            releaseCreateGuideHost();
        }
    });

    // Internal derived: main row from items[0], partner info from items[1]
    let mainRow = $derived(items?.[0] ?? null);
    /** Extract injected partner TXReadItem from items[1] (when not inaccessible). */
    let _injectedPartner = $derived.by<TXReadItem | null>(() => {
        const second = items?.[1];
        if (!second) return null;
        return isInaccessible(second) ? null : second;
    });
    /** Extract inaccessible partner info from items[1] (when present). */
    let _inaccessibleFromItems = $derived.by<{broker_id: number} | null>(() => {
        const second = items?.[1];
        if (!second) return null;
        return isInaccessible(second) ? second : null;
    });

    /** V5: External WAC result from BulkModal (single source of truth). */
    /** Phase D: local WAC result from FormModal's own validate response (standalone mode). */
    let formWacResult = $state<TxFormWacResult | null>(null);
    let externalWacResult = $derived((getWacResult && editingTempId ? getWacResult(editingTempId) : null) ?? formWacResult);
    /** Derive available currencies from qualifying TXs for the currency chip */
    let wacAvailableCurrencies = $derived.by(() => {
        const qtxs = externalWacResult?.qualifying_txs ?? [];
        const codes = [...new Set(qtxs.map((q) => (q.original_currency ?? q.currency) as string | null).filter(Boolean))] as string[];
        // Always include asset currency as fallback
        const assetCcy = draft?.cash?.code ?? 'EUR';
        if (!codes.includes(assetCcy)) codes.push(assetCcy);
        return codes;
    });

    // =========================================================================
    // Form state
    // =========================================================================

    function emptyDraft(): FormDraft {
        const brokers = getEditableBrokers();
        // Bugfix-2 §C9: only auto-pick a broker if exactly one is available;
        // otherwise leave the field empty (0 = unset sentinel) so the user
        // is forced to choose consciously. defaultBrokerId (soft, editable) wins
        // over that heuristic but not over forcedBroker (hard-locked).
        const defaultBroker = forcedBroker ?? defaultBrokerId ?? (brokers.length === 1 ? brokers[0].id : 0);
        return {
            broker_id: defaultBroker,
            asset_id: null,
            type: 'BUY',
            date: todayIso(),
            // Empty on purpose (T1-b): a pre-filled "0" forces the user to
            // cursor around it just to type decimals. Validation already
            // rejects empty/zero until a real quantity is typed.
            quantity: '',
            cash: null,
            tags: [],
            description: '',
            asset_event_id: null,
            cost_basis_override: null,
            link_uuid: null,
        };
    }

    function emptyDualTo(): DualDraftTo {
        return {broker_id: 0, cash: null, date: todayIso()};
    }

    function fromTx(tx: TXReadItem, opts: {regenerateLink?: boolean} = {}): FormDraft {
        const txRule = getTypeRule(tx.type);
        // Auto-sign: show positive values for auto-negated types
        // Also normalize paired types (transfer_asset, transfer_cash) — the dual
        // form always displays absolute values; sign is determined by From/To sides.
        let qty = tx.quantity;
        if (txRule.quantityRule === 'negative' || txRule.pairFormLayout != null) {
            qty = applySign(qty, 'positive');
        }
        let cash = tx.cash ? {code: tx.cash.code, amount: tx.cash.amount} : null;
        // Paired cash editors show magnitudes; the collector signs the two legs.
        if (cash && (txRule.cashSign === 'negative' || (txRule.requiresPair && mode !== 'view'))) {
            cash = {code: cash.code, amount: applySign(cash.amount, 'positive')};
        }
        return {
            broker_id: tx.broker_id,
            asset_id: tx.asset_id ?? null,
            type: tx.type as TransactionTypeCode,
            // T3: the date is always preserved — duplicating is how users fix a
            // misclassified historical row, and resetting to today destroyed
            // exactly the field they needed to keep.
            date: tx.date,
            quantity: qty,
            cash,
            tags: [...(tx.tags ?? [])],
            description: tx.description ?? '',
            asset_event_id: tx.asset_event_id ?? null,
            cost_basis_override: (() => {
                const cbo = tx.cost_basis_override;
                if (!cbo) return null;
                if (typeof cbo === 'object' && cbo !== null) return {code: String((cbo as any).code ?? ''), amount: String((cbo as any).amount ?? '')};
                // Legacy string "42.50" (no currency) → use TX cash code as fallback
                const s = String(cbo).trim();
                if (!s) return null;
                const parts = s.split(/\s+/);
                if (parts.length >= 2) return {amount: parts[0], code: parts[1]};
                return {amount: parts[0], code: tx.cash?.code ?? ''};
            })(),
            link_uuid: opts.regenerateLink ? generateUUID() : null,
        };
    }

    // Single source-of-truth state (computed from props in $effect, never read inside the same effect).
    let draft = $state<FormDraft>(emptyDraft());
    /** Dual-form "To" side — populated when pairLayout !== null. */
    let dualTo = $state<DualDraftTo>(emptyDualTo());
    /** Cost basis mode tracking for BulkModal propagation. */
    let costBasisMode = $state<'auto' | 'manual'>('auto');
    /** Currency hint for WAC calculation — null = backend decides (last acquisition) */
    let wacCurrencyHint = $state<string | null>(null);
    /** In auto mode, display the WAC result value (not the sentinel {code, amount:"0"}) */
    let displayedCostBasis = $derived(costBasisMode === 'auto' && externalWacResult?.wac ? externalWacResult.wac : costBasisMode === 'auto' && wacCurrencyHint ? {code: wacCurrencyHint, amount: ''} : draft.cost_basis_override);
    // Phase D + G5: clear local WAC result on any mode change (manual: stop showing; auto: force re-fetch)
    $effect(() => {
        void costBasisMode; // track
        formWacResult = null;
    });
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
    let optionalOpen = $state(untrack(() => initialOptionalOpen));
    /** Snapshot of `draft` at modal-open time, used to detect unsaved
     *  changes (Bugfix-3 §C11). */
    let initialDraftKey = $state('');
    let confirmCloseOpen = $state(false);
    /** Bug5-fix: broker_id of partner that the user cannot access.
     *  When set, the "To" side shows a locked placeholder instead of empty. */
    let inaccessiblePartnerBrokerId = $state<number | null>(null);
    /** ExactQuantityInput owns the locale-specific edit buffer; the draft stays normalized. */
    let quantityInputValid = $state(true);
    /** V-37: each date picker's verdict on its typed text. A refused text never reaches the draft, so the draft
     *  alone cannot tell that the field on screen shows another date. Not reset on open: the picker is the source
     *  of truth for its own text, and reports it on mount, on every change, and once more if it unmounts refusing. */
    let dateMainValid = $state(true);
    let dateToValid = $state(true);

    // Reset draft on open; broker store must be loaded first.
    $effect(() => {
        if (!open) return;
        // Bug15-fix: track openKey to force re-init even when `open` doesn't toggle.
        void openKey;
        // Read props — the $effect depends on open, openKey, mode, items.
        const m = mode;
        const row = items?.[0] ?? null;
        untrack(() => {
            // Extract partner info from items[1]
            const injected = _injectedPartner;
            const inaccessFromItems = _inaccessibleFromItems;

            issues = [];
            formError = null;
            commitFailed = false;
            optionalOpen = initialOptionalOpen;
            confirmCloseOpen = false;
            inaccessiblePartnerBrokerId = inaccessFromItems?.broker_id ?? null;
            partnerRow = null;
            loadingPartner = false;
            quantityInputValid = true;
            formWacResult = null;
            wacCurrencyHint = null;
            dualTo = emptyDualTo();
            if (m === 'create') {
                // C1-fix: when items[0] is present (e.g. editing a 'new' draft
                // from BulkModal), populate from it instead of starting blank.
                if (row) {
                    draft = fromTx(row);
                    // Injected partner for paired drafts
                    if (injected) {
                        partnerRow = injected;
                        const layout = getPairFormLayout(row.type);
                        if (layout) {
                            applyPartnerToDualTo(row, injected, layout);
                        }
                        // Derive costBasisMode from receiver's state
                        if (layout === 'transfer_asset' && (injected as any).cost_basis_mode === 'manual') {
                            costBasisMode = 'manual';
                        } else {
                            costBasisMode = 'auto';
                        }
                        // Restore receiver's cost_basis_override into draft so WacPreviewSection.value is correct
                        if (dualTo.cost_basis_override) {
                            draft = {...draft, cost_basis_override: dualTo.cost_basis_override};
                            // Recover WAC currency hint from the stored sentinel override
                            if (costBasisMode === 'auto' && dualTo.cost_basis_override.code && String(dualTo.cost_basis_override.amount) === '0') {
                                wacCurrencyHint = dualTo.cost_basis_override.code;
                            }
                        }
                    } else {
                        // Solo op (no partner) — use explicit mode from BulkModal when available
                        costBasisMode = row.cost_basis_mode === 'manual' || row.cost_basis_mode === 'auto' ? row.cost_basis_mode : 'auto';
                        // Recover WAC currency hint from stored sentinel override
                        const cbo = row.cost_basis_override;
                        if (costBasisMode === 'auto' && cbo && typeof cbo === 'object' && cbo.code && String(cbo.amount) === '0') {
                            wacCurrencyHint = cbo.code;
                        }
                    }
                } else {
                    draft = emptyDraft();
                    costBasisMode = 'auto';
                }
            } else if ((m === 'edit' || m === 'view') && row) {
                draft = fromTx(row);
                // Use injected partner directly instead of fetching from the API.
                if (injected) {
                    partnerRow = injected;
                    const layout = getPairFormLayout(row.type);
                    if (layout) {
                        applyPartnerToDualTo(row, injected, layout);
                    }
                    // Derive costBasisMode from receiver's state
                    if (layout === 'transfer_asset') {
                        costBasisMode = (injected as any).cost_basis_mode === 'manual' ? 'manual' : 'auto';
                    } else {
                        costBasisMode = row.cost_basis_mode === 'manual' || row.cost_basis_mode === 'auto' ? row.cost_basis_mode : 'auto';
                    }
                    // Restore receiver's cost_basis_override into draft for WacPreviewSection
                    if (dualTo.cost_basis_override) {
                        draft = {...draft, cost_basis_override: dualTo.cost_basis_override};
                        // Recover WAC currency hint from stored sentinel override
                        if (costBasisMode === 'auto' && dualTo.cost_basis_override.code && String(dualTo.cost_basis_override.amount) === '0') {
                            wacCurrencyHint = dualTo.cost_basis_override.code;
                        }
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
                    // Use explicit mode if available (BulkModal); fallback to override heuristic for DB rows
                    costBasisMode = row.cost_basis_mode === 'manual' || row.cost_basis_mode === 'auto' ? row.cost_basis_mode : draft.cost_basis_override ? 'manual' : 'auto';

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
                    costBasisMode = row.cost_basis_mode === 'manual' || row.cost_basis_mode === 'auto' ? row.cost_basis_mode : 'auto';
                } else {
                    // Standalone edit (no partner) — use explicit mode from BulkModal when available
                    costBasisMode = row.cost_basis_mode === 'manual' || row.cost_basis_mode === 'auto' ? row.cost_basis_mode : 'auto';
                }
            } else {
                draft = emptyDraft();
                costBasisMode = 'auto';
            }
            lastTypeForReset = draft.type;
            initialDraftKey = JSON.stringify(draft) + JSON.stringify(dualTo);
        });
        // Async hydration (brokers + currencies + asset cache for the picked asset).
        void (async () => {
            await Promise.all([ensureBrokersLoaded(), ensureCurrenciesLoaded($currentLanguage), ensureAssetsLoaded(), ensureTypesLoaded()]);
            // After brokers loaded, backfill broker_id only if a single broker is
            // available (Bugfix-2 §C9) — otherwise leave it 0 so the user must
            // pick. `forcedBroker` (locked) and `defaultBrokerId` (soft) still win.
            untrack(() => {
                if (mode === 'create' && draft.broker_id === 0) {
                    if (forcedBroker != null) {
                        draft = {...draft, broker_id: forcedBroker};
                    } else if (defaultBrokerId != null) {
                        draft = {...draft, broker_id: defaultBrokerId};
                    } else {
                        const all = getEditableBrokers();
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
            const results = (await zodiosApi.query_transactions_api_v1_transactions_get({
                queries: {ids: [row.related_transaction_id], limit: 1},
            })) as unknown as TXReadItem[];
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
     *  both `fetchPartner` (API) and items[1] injection. */
    function applyPartnerToDualTo(row: TXReadItem, partner: TXReadItem, layout: PairFormLayout) {
        if (layout === 'fx') {
            const myAmount = Number(row.cash?.amount ?? 0);
            const partnerAmount = Number(partner.cash?.amount ?? 0);
            if (myAmount > 0 && partnerAmount < 0) {
                draft = fromTx(partner);
                dualTo = {
                    broker_id: partner.broker_id,
                    cash: row.cash ? {code: row.cash.code, amount: applySign(row.cash.amount, 'positive')} : null,
                    date: row.date,
                };
            } else {
                dualTo = {
                    broker_id: partner.broker_id,
                    cash: partner.cash ? {code: partner.cash.code, amount: applySign(partner.cash.amount, 'positive')} : null,
                    date: partner.date,
                };
            }
        } else if (layout === 'transfer_asset') {
            const myQtySign = exactDecimalSign(row.quantity) ?? 0;
            if (myQtySign > 0) {
                // row is receiver (qty>0), partner is sender (qty<0)
                draft = fromTx(partner);
                dualTo = {broker_id: row.broker_id, cash: null, date: row.date, cost_basis_override: row.cost_basis_override ? (typeof row.cost_basis_override === 'object' ? (row.cost_basis_override as {code: string; amount: string}) : null) : null};
            } else {
                // row is sender (qty<0), partner is receiver (qty>0)
                dualTo = {broker_id: partner.broker_id, cash: null, date: partner.date, cost_basis_override: partner.cost_basis_override ? (typeof partner.cost_basis_override === 'object' ? (partner.cost_basis_override as {code: string; amount: string}) : null) : null};
            }
            // Sender draft must have empty cost_basis_override
            draft = {...draft, cost_basis_override: null};
            // Dual form always shows absolute qty — sign is determined by From/To sides
            draft = {...draft, quantity: applySign(draft.quantity, 'positive')};
        } else if (layout === 'transfer_cash') {
            const myAmount = Number(row.cash?.amount ?? 0);
            const fromRow = myAmount < 0 ? row : partner;
            const toRow = myAmount < 0 ? partner : row;
            draft = fromTx(fromRow);
            if (draft.cash) {
                draft = {...draft, cash: {code: draft.cash.code, amount: applySign(draft.cash.amount, 'positive')}};
            }
            dualTo = {broker_id: toRow.broker_id, cash: null, date: toRow.date};
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
        return JSON.stringify(draft) + JSON.stringify(dualTo) !== initialDraftKey;
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
            }
            // Clear linked event when no longer applicable.
            if (!r.eventLinkable && next.asset_event_id != null) next.asset_event_id = null;
            // Clear cost basis when not a TRANSFER (only meaningful there).
            if (t !== 'TRANSFER' && next.cost_basis_override) next.cost_basis_override = null;
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
        if (mainRow?.related_transaction_id != null) {
            return getPairFormLayout(mainRow.type);
        }
        return null;
    });
    /** FX has one broker, including presets, late hydration and type switches.
     *  Keep the stored partner untouched in view mode so historical facts stay visible. */
    let effectiveDualTo = $derived<DualDraftTo>(pairLayout === 'fx' && mode !== 'view' ? {...dualTo, broker_id: draft.broker_id} : dualTo);
    /** Auto-sign: user enters positive, backend expects negative cash. */
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
        if (mode === 'edit' && unlockImmutable && mainRow) {
            return getSwapGroup(mainRow.type as TransactionTypeCode);
        }
        // No restriction for create/duplicate
        return undefined;
    });
    /** #58: a saved transaction keeps its asset and its broker(s): the update the backend accepts has neither `asset_id`
     *  nor `broker_id`, so a change shown in the grid was never sent. A new row (`create`) still picks them; a stored
     *  one in `edit` shows them, in the grid's deep-edit too (`unlockImmutable` frees the type only). */
    let rowSaved = $derived(mode === 'edit' || mode === 'view');
    let brokerImmutable = $derived(rowSaved || forcedBroker != null);
    let canShowAssetEvent = $derived(rule.eventLinkable && draft.asset_id != null && draft.date !== '');

    /** H4-fix: true when all required fields for the current type are filled.
     *  Gates the auto-validate scheduler, the ⚡ Validate button, and the Apply/Save button.
     *  In paired mode also requires the partner side fields (broker, cash for FX). */
    let isFormComplete = $derived.by(() => {
        void $typesVersion; // re-derive when server type rules load
        if (!draft.date || !isDraftReadyForValidation(draft)) return false;
        // Paired mode: partner side must also be populated
        if (pairLayout != null) {
            if (!effectiveDualTo.broker_id || effectiveDualTo.broker_id <= 0 || !effectiveDualTo.date) return false;
            if (pairLayout === 'fx') {
                return [draft.cash, effectiveDualTo.cash].every((cash) => {
                    if (!cash?.code.trim() || !cash.amount.trim()) return false;
                    const amount = Number(cash.amount);
                    return Number.isFinite(amount) && amount !== 0;
                });
            }
        }
        return true;
    });

    // cost_basis_override is meaningful only for units coming in: the receiver of a TRANSFER pair, or an ADJUSTMENT with
    // a positive quantity. An ADJUSTMENT taking units out has no value (N78-1): it only lowers the quantity.
    let showCostBasisField = $derived(draft.type === 'TRANSFER' || (draft.type === 'ADJUSTMENT' && (exactDecimalSign(draft.quantity) ?? 0) > 0));

    // Pair partner chip (only when editing an existing linked tx — non-dual mode).
    let pairPartnerId = $derived(pairLayout ? null : (mainRow?.related_transaction_id ?? null));

    // =========================================================================
    // FX Implied Rate — market rate lookup for FX conversion form
    // =========================================================================

    let fxMarketPoint = $state<FxDataPoint | null | undefined>(undefined);
    let fxLookupKey = $state('');

    $effect(() => {
        if (pairLayout !== 'fx') {
            fxMarketPoint = undefined;
            return;
        }
        const fromCode = draft.cash?.code;
        const toCode = dualTo.cash?.code;
        const fromDate = draft.date;
        if (!fromCode || !toCode || fromCode === toCode || !fromDate) {
            fxMarketPoint = undefined;
            return;
        }
        const key = `${fromCode}-${toCode}-${fromDate}`;
        if (key === fxLookupKey) return;
        fxLookupKey = key;
        fxMarketPoint = undefined;
        lookupFxRate(fromCode, toCode, fromDate).then((result) => {
            if (`${fromCode}-${toCode}-${fromDate}` === fxLookupKey) {
                fxMarketPoint = result;
            }
        });
    });

    // =========================================================================
    // Dual-form title
    // =========================================================================

    let dualTitle = $derived.by(() => {
        if (!pairLayout) return '';
        switch (pairLayout) {
            case 'fx':
                return $t('transactions.form.fxTitle');
            case 'transfer_asset':
                return $t('transactions.form.transferAssetTitle');
            case 'transfer_cash':
                return $t('transactions.form.transferCashTitle');
            default:
                return '';
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

    // Cash sign validation — paired mode uses 'positive' (user enters positive, flip negates FROM).
    // Single mode uses the type's cashSign rule.
    let effectiveCashRule = $derived(pairLayout != null ? 'positive' : rule.cashSign);
    let cashSignResult = $derived(computeSignHint(parseFloat(draft.cash?.amount ?? '0'), effectiveCashRule));
    let cashToSignViolation = $derived(pairLayout === 'fx' && computeSignHint(parseFloat(dualTo.cash?.amount ?? '0'), 'positive').bad);

    // Block submit for an invalid exact quantity (syntax, digit budget — 15 integer, 10 decimals, 15 significant —
    // range or sign) and for the legacy cash-sign checks.
    let hasSignViolation = $derived((rule.quantityMode !== 'forbidden' && !quantityInputValid) || cashSignResult.bad || cashToSignViolation);

    // B-48: a cash amount past the significant digits the backend keeps. The quantity's own budget is in its validity.
    let cashOverSignificant = $derived(exceedsSignificantDigits(draft.cash?.amount, REAL_SIGNIFICANT_DIGITS));
    let cashToOverSignificant = $derived(pairLayout === 'fx' && exceedsSignificantDigits(dualTo.cash?.amount, REAL_SIGNIFICANT_DIGITS));

    /** A date picker shows a date it refused: the draft still holds the previous one. */
    let hasDateError = $derived(!dateMainValid || !dateToValid);
    /**
     * V-37: the errors the form sees on its own — a quantity or cash sign it refuses, two sides that must differ, a
     * typed date the picker refused, a cash amount past the significant digits (B-48). While any is on screen the server is not asked: the payload would carry the
     * sign-corrected quantity or the previous date, and its verdict would be about a draft that is not the one shown.
     * So no automatic run, no manual one, no «valid» and no Apply. Declared before the scheduler, whose constructor
     * already reads `enabled`.
     */
    let hasLocalErrors = $derived(hasSignViolation || !!dualValidationError || hasDateError || cashOverSignificant || cashToOverSignificant);

    // =========================================================================
    // Validate scheduler — debounced/manual/idle, always enabled (1 row).
    // =========================================================================

    const scheduler = createValidateScheduler({
        // Auto-fire only when the form is fully complete (both sides for paired) and holds
        // no error of its own (V-37). The manual dispatch ignores `enabled`: «Validate now»
        // checks `hasLocalErrors` itself, in `validateNow`.
        enabled: () => !isReadonly && isFormComplete && !hasLocalErrors,
        draftKey: () => lastDraftKey,
        validateFn: async () => {
            if (isReadonly) return {issuesCount: 0};

            // Build my payload
            const myPayload: Record<string, unknown> = pairLayout ? (mode === 'edit' ? {updates: collectDualUpdates()} : {creates: collectDualCreates()}) : mode === 'edit' ? {updates: [collectUpdate()]} : {creates: [collectCreate()]};

            // Context-aware: merge bulk context if available
            let payload: Record<string, unknown>;
            let myOperation: 'create' | 'update' = mode === 'edit' ? 'update' : 'create';
            let myIndex: number;
            if (getBulkContext) {
                const ctx = getBulkContext();
                const mergedCreates = [...(ctx.creates || []), ...((myPayload.creates as Record<string, unknown>[]) || [])];
                const mergedUpdates = [...(ctx.updates || []), ...((myPayload.updates as Record<string, unknown>[]) || [])];
                payload = {};
                if (mergedCreates.length > 0) payload.creates = mergedCreates;
                if (mergedUpdates.length > 0) payload.updates = mergedUpdates;
                if (ctx.deletes?.length > 0) payload.deletes = ctx.deletes;
                myIndex = myOperation === 'create' ? mergedCreates.length - 1 : mergedUpdates.length - 1;
            } else {
                payload = myPayload;
                myIndex = 0;
            }

            upgradeAutoToDetail(payload);
            const sentKey = lastDraftKey;
            const result = await validateTransactions(payload, {fallback: $t('transactions.form.saveFailed')});
            // Superseded response: the draft moved on while the server was
            // thinking, so this verdict is about a state that no longer exists.
            // The change that moved the key already armed a newer run.
            if (lastDraftKey !== sentKey) return {issuesCount: issues.length};

            if (result.networkError) {
                issues = [{operation: myOperation, index: 0, error: result.networkError}];
            } else if (pairLayout) {
                // W42: deduplicate issues by code (both halves produce the same error)
                issues = deduplicateIssues(result.issues as unknown as ValidationIssue[]);
            } else {
                // Filter: show only issues for my row (or global with index=-1)
                const allIssues = result.issues as unknown as ValidationIssue[];
                issues = getBulkContext ? allIssues.filter((i) => (i.operation === myOperation && i.index === myIndex) || i.index === -1) : allIssues;
            }
            lastValidatedDraftKey = sentKey;
            issuesDismissed = false;

            // Phase D: extract wac_results from validate response
            if (costBasisMode === 'auto') {
                const rawResp = result.rawResponse as Record<string, unknown> | null;
                const rawWacResults = (rawResp?.wac_results as Array<Record<string, unknown>> | null | undefined) ?? null;
                if (rawWacResults && rawWacResults.length > 0) {
                    // Find my WAC result — for paired creates the receiver (toItem) is at myIndex+1
                    // The backend returns WAC only for items with cost_basis_mode, so find the first match
                    const myWr = rawWacResults.find((wr) => wr.operation === myOperation) ?? null;
                    if (myWr) {
                        formWacResult = {
                            wac: (myWr.wac as {code: string; amount: string} | null) ?? null,
                            qualifying_txs: (myWr.wac_qualifying_txs as Array<Record<string, any>>) ?? [],
                            missing_pairs: (myWr.wac_missing_pairs as string[]) ?? [],
                        };
                        // Sync currency hint from backend response (first calc or when null)
                        if (!wacCurrencyHint && formWacResult.wac?.code) {
                            wacCurrencyHint = formWacResult.wac.code;
                        }
                    } else {
                        formWacResult = null;
                    }
                } else {
                    formWacResult = null;
                }
            }

            return {issuesCount: issues.length};
        },
    });

    onDestroy(() => {
        scheduler.dispose();
        if (guideObservedOpen) releaseCreateGuideHost();
    });

    // Trigger 'change' on every meaningful draft mutation.
    let lastDraftKey = $state('');
    /** Bugfix-4 §U16: track validate freshness for the green/warning banner UX. */
    let lastValidatedDraftKey = $state('');
    let issuesDismissed = $state(false);
    let isFreshlyValid = $derived(!isReadonly && !hasLocalErrors && scheduler.state.lastValidatedAt != null && issues.length === 0 && lastValidatedDraftKey === lastDraftKey && lastDraftKey !== '');
    let showIssuesBanner = $derived(issues.length > 0 && !issuesDismissed);
    let fieldIssues = $derived(issues.filter((i) => i.index >= 0 && !isBulkBalanceIssue(i)));
    let balanceIssues = $derived(issues.filter((i) => i.index < 0 || isBulkBalanceIssue(i)));
    let hasWacFxIssues = $derived(issues.some((i) => i.code === 'wacFxUnavailable'));
    let showFxSyncModal = $state(false);
    let fxSyncPairs = $state<string[]>([]);
    let fxSyncDateStart = $state('');
    let fxSyncDateEnd = $state('');

    /** Context for resolving validation issue codes into translated messages. */
    let resolverCtx: ResolverContext = $derived({
        brokers: brokers as unknown as Array<{id: number; name: string}>,
        assets: getAllAssets() as unknown as Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null}>,
        getBrokerIconHtml: (brokerId: number) =>
            getBrokerIconHtmlById(brokerId, brokers as any[], {
                width: 16,
                height: 16,
                style: 'display:inline-block;vertical-align:middle;margin-right:2px;border-radius:2px',
            }),
    });
    $effect(() => {
        if (!open || isReadonly) return;
        const key = JSON.stringify(draft) + JSON.stringify(effectiveDualTo) + (wacCurrencyHint ?? '') + `:${$typesVersion}`;
        if (key === lastDraftKey) return;
        lastDraftKey = key;
        commitFailed = false;
        scheduler.trigger('change');
    });
    // V-37: when the form's own errors clear, ask the scheduler again. The change that cleared them can reach it
    // while they still stand — the quantity input and the date picker report their validity after the draft
    // moves — and the scheduler drops a change it is not enabled for. Either order ends in one debounced run.
    let hadLocalErrors = false;
    $effect(() => {
        const blocked = hasLocalErrors;
        if (hadLocalErrors && !blocked && open && !isReadonly) scheduler.trigger('change');
        hadLocalErrors = blocked;
    });

    // -------------------------------------------------------------------------
    // UI helpers (SimpleSelect options for Type, autocomplete name suffix)
    // -------------------------------------------------------------------------

    /** Random suffix used as the `name` attribute on numeric inputs to
     *  defeat browser autofill heuristics (Bugfix-1 §U7). Stable per modal
     *  open. */
    const autocompleteNonce = $derived(Math.random().toString(36).slice(2, 10));
    let quantityInputId = $derived(`tx-form-quantity-${autocompleteNonce}`);
    let quantityHintId = $derived(`tx-form-quantity-hint-${autocompleteNonce}`);

    /** BrokerSearchSelect expects `BrokerSelectItem[]`; the brokerStore's
     *  `BrokerInfo` is structurally compatible (id/name/icon_url present)
     *  but TS can't widen via the prop attribute. We cast in script. */
    let brokersForSelect = $derived(brokers as unknown as Array<{id: number; name: string; icon_url?: string | null}>);
    /** W37: Filtered broker lists for dual form — prevent same broker on both sides. */
    let brokersForFrom = $derived(pairLayout && pairLayout !== 'fx' ? brokersForSelect.filter((b) => b.id !== dualTo.broker_id || !dualTo.broker_id) : brokersForSelect);
    let brokersForTo = $derived(pairLayout && pairLayout !== 'fx' ? brokersForSelect.filter((b) => b.id !== draft.broker_id || !draft.broker_id) : brokersForSelect);
    let brokerIdValue = $derived<number | null>(draft.broker_id || null);
    let brokerToIdValue = $derived<number | null>(dualTo.broker_id || null);

    // =========================================================================
    // Sanitizers
    // =========================================================================

    function collectCreate(): Record<string, unknown> {
        return buildCreatePayload(draftToTxFields(), rule);
    }

    function collectUpdate(): Record<string, unknown> {
        if (!mainRow) return {};
        const origRule = getTypeRule(mainRow.type as TransactionTypeCode);
        return buildUpdateDiff(draftToTxFields(), mainRow as unknown as TxOriginal, rule, origRule);
    }

    /** Convert the form draft to the shared TxFields interface. */
    function draftToTxFields(): TxFields {
        // Normalize cost_basis_override: treat empty amount as null
        const cbo = draft.cost_basis_override?.amount?.trim() ? draft.cost_basis_override : null;
        // In auto mode, use wacCurrencyHint as currency override (amount=0 sentinel)
        const cbOverride = costBasisMode === 'auto' ? (wacCurrencyHint ? {code: wacCurrencyHint, amount: '0'} : null) : cbo;
        return {
            type: draft.type,
            broker_id: draft.broker_id,
            date: draft.date,
            quantity: draft.quantity,
            asset_id: draft.asset_id,
            cash: draft.cash,
            tags: draft.tags,
            description: draft.description,
            cost_basis_override: cbOverride,
            cost_basis_mode: costBasisMode,
            asset_event_id: draft.asset_event_id,
            link_uuid: draft.link_uuid,
        };
    }

    /** Handle WAC currency chip change — re-trigger validate without switching to manual */
    function onWacCurrencyChange(code: string) {
        wacCurrencyHint = code;
        formWacResult = null; // clear stale result to show placeholder while recalculating
        // Re-trigger validate to recompute WAC in new currency
        scheduler.trigger('change');
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
        if (!pairLayout) return [collectCreate()];

        const toSide: TxDualSide = {
            broker_id: effectiveDualTo.broker_id,
            date: effectiveDualTo.date,
            cash: effectiveDualTo.cash,
            quantity: effectiveDualTo.quantity,
            cost_basis_override: effectiveDualTo.cost_basis_override,
        };
        return buildDualCreatePayloads(pairLayout as PayloadPairLayout, draftToTxFields(), toSide, linkUuid);
    }

    /**
     * Build 2 TXUpdateItem payloads for dual-form edit mode.
     * Only include PATCHABLE fields that actually changed vs the original.
     */
    function collectDualUpdates(): Record<string, unknown>[] {
        if (!mainRow || !partnerRow) return [];
        const items = collectDualCreates();

        // Determine which original row maps to which item (From=items[0], To=items[1])
        let fromOrig: TXReadItem = mainRow;
        let toOrig: TXReadItem = partnerRow;
        if (pairLayout === 'fx') {
            if (Number(mainRow.cash?.amount ?? 0) > 0) {
                fromOrig = partnerRow;
                toOrig = mainRow;
            }
        } else if (pairLayout === 'transfer_asset') {
            if ((exactDecimalSign(mainRow.quantity) ?? 0) > 0) {
                fromOrig = partnerRow;
                toOrig = mainRow;
            }
        } else if (pairLayout === 'transfer_cash') {
            if (Number(mainRow.cash?.amount ?? 0) >= 0) {
                fromOrig = partnerRow;
                toOrig = mainRow;
            }
        }

        const allItems = [diffDualItem(items[0], fromOrig as unknown as TxOriginal, null), diffDualItem(items[1], toOrig as unknown as TxOriginal, costBasisMode)];
        // Only include items that have actual changes (more than just `id`)
        return allItems.filter((item) => Object.keys(item).length > 1);
    }

    // =========================================================================
    // Local errors (V-37): «Validate now» and the first field to fix
    // =========================================================================

    /** The scrollable form body, searched by `focusFirstLocalError`. */
    let formBodyEl = $state<HTMLDivElement | undefined>(undefined);

    /**
     * Moves the focus to the first field, in screen order, that holds one of the form's own errors. Each selector
     * matches what that control publishes — the date picker's `data-invalid` root, the quantity input's test id — or,
     * for the cells that publish nothing, the test id this form gives them. `querySelector` on the list returns the
     * first match in document order, whatever the layout (single, pair, FX).
     */
    function focusFirstLocalError() {
        if (!formBodyEl) return;
        const selectors: string[] = [];
        if (hasDateError) selectors.push('[data-invalid="true"] input[type="text"]');
        if (rule.quantityMode !== 'forbidden' && !quantityInputValid) selectors.push('input[data-testid="tx-form-quantity"]');
        if (cashSignResult.bad || cashOverSignificant) selectors.push('input[data-testid="tx-form-cash-amount"]', 'input[data-testid="tx-form-cash-from-amount"]');
        if (cashToSignViolation || cashToOverSignificant) selectors.push('input[data-testid="tx-form-cash-to-amount"]');
        if (dualValidationError) selectors.push(pairLayout === 'fx' ? '[data-testid="tx-form-cash-to"] [role="combobox"]' : '[data-testid="tx-form-dual-to"] [role="combobox"]');
        if (selectors.length === 0) return;
        formBodyEl.querySelector<HTMLElement>(selectors.join(', '))?.focus();
    }

    /** «Validate now» asks the server, unless the form holds an error of its own: then it leads to that field. */
    function validateNow() {
        if (hasLocalErrors) {
            focusFirstLocalError();
            return;
        }
        scheduler.trigger('manual');
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
        // V-37: Apply is disabled while the form holds an error of its own; this guard
        // covers a click that lands before the button repaints.
        if (hasLocalErrors) {
            focusFirstLocalError();
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
                    _partnerBrokerId: effectiveDualTo.broker_id,
                    _partnerCash: effectiveDualTo.cash,
                    _partnerDate: effectiveDualTo.date,
                    _cost_basis_mode: costBasisMode,
                    _wac_currency_hint: wacCurrencyHint,
                };
                // Also carry the "from" side fields for applyFormPayload
                Object.assign(payload, items[0]);
                onPushDraft?.(payload);
            } else {
                const payload = collectCreate();
                (payload as any)._cost_basis_mode = costBasisMode;
                (payload as any)._wac_currency_hint = wacCurrencyHint;
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
            // Build payload based on mode + pairLayout
            const payload: Record<string, unknown> = pairLayout ? (mode === 'edit' && partnerRow ? {updates: collectDualUpdates()} : {creates: collectDualCreates()}) : mode === 'edit' ? {updates: [collectUpdate()]} : {creates: [collectCreate()]};

            const result = await commitTransactions(payload, {fallback: $t('transactions.form.saveFailed')});
            if (result.networkError) {
                formError = result.networkError;
                return;
            }
            if (!result.committed) {
                issues = result.issues as unknown as ValidationIssue[];
                issuesDismissed = false;
                commitFailed = true;
                return;
            }
            onCommitted?.({transaction_id: result.results?.[0]?.ids?.[0] ?? null});
            onClose();
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
    function setDateTo(v: string) {
        dualTo = {...dualTo, date: v};
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
        const tmpDate = draft.date;
        if (pairLayout === 'fx') {
            // FX shares a broker, not necessarily a settlement date.
            const tmpCash = draft.cash;
            draft = {...draft, cash: dualTo.cash, date: dualTo.date};
            dualTo = {...dualTo, cash: tmpCash, date: tmpDate};
        } else {
            // transfer_asset / transfer_cash: swap brokers and dates
            const tmpBroker = draft.broker_id;
            draft = {...draft, broker_id: dualTo.broker_id, date: dualTo.date};
            dualTo = {...dualTo, broker_id: tmpBroker, date: tmpDate};
        }
    }
    function addTag(raw: string) {
        const v = raw.trim();
        if (!v) return;
        if ((draft.tags ?? []).includes(v)) return;
        draft = {...draft, tags: [...(draft.tags ?? []), v]};
    }
    function onQuantityValidityChange(state: {valid: boolean}) {
        quantityInputValid = state.valid;
    }
    function onDateMainValidityChange(state: {valid: boolean}) {
        dateMainValid = state.valid;
    }
    function onDateToValidityChange(state: {valid: boolean}) {
        dateToValid = state.valid;
    }
    function onDescriptionInput(e: Event) {
        draft = {...draft, description: (e.currentTarget as HTMLTextAreaElement).value};
    }
    function onCostBasisChange(next: {code: string; amount: string} | null) {
        draft = {...draft, cost_basis_override: next};
    }

    // =========================================================================
    // Sync FX (WAC FX unavailable recovery)
    // =========================================================================

    async function handleSyncFx() {
        // Collect pairs and dates from wacFxUnavailable issues (pair_details has dates)
        const pairs: string[] = [];
        const allDates: string[] = [];
        for (const issue of issues) {
            if (issue.code === 'wacFxUnavailable' && issue.params) {
                if (issue.params.pairs) {
                    for (const p of issue.params.pairs) {
                        if (!pairs.includes(p)) pairs.push(p);
                    }
                }
                if (issue.params.pair_details) {
                    for (const pd of issue.params.pair_details as Array<{pair: string; dates: string[]}>) {
                        allDates.push(...(pd.dates ?? []));
                    }
                }
            }
        }
        if (pairs.length === 0) return;
        // Convert "USD/EUR" → "EUR-USD" (alphabetical slug format for sync API)
        fxSyncPairs = pairs.map((p) => {
            const [a, b] = p.split('/');
            return [a, b].sort().join('-');
        });
        // Use min/max dates from backend (covers all needed dates), fallback to draft.date
        const sortedDates = allDates.length > 0 ? allDates.sort() : [draft.date];
        fxSyncDateStart = sortedDates[0] ?? draft.date;
        fxSyncDateEnd = sortedDates[sortedDates.length - 1] ?? draft.date;
        showFxSyncModal = true;
    }

    // =========================================================================
    // Quantity / cash sign hints
    // =========================================================================
    // Sign hints — unified for both quantity and cash fields
    // =========================================================================

    /** Label suffix for a sign rule: (+), (−), (≠0), or empty. */
    /** Hint text below the field explaining the sign constraint. */
    function signHintText(sign: import('$lib/features/transactions/transactionTypeStore').SignRule): string {
        const key = signHintKey(sign);
        return key ? $t(key) : '';
    }

    let qtyHint = $derived(signHintText(rule.quantityRule));
    let qtyLabel = $derived(signLabel(rule.quantityRule));
    let cashHint = $derived(signHintText(rule.cashSign));
    let cashLabel = $derived(signLabel(rule.cashSign));

    // The quantity editor classifies sign from the exact string. Negative backend
    // rules are auto-flipped, so their user-facing entry rule is positive.
    let effectiveQtyRule = $derived(pairLayout != null ? 'positive' : rule.quantityRule);
    let quantityInputSignRule = $derived.by<'positive' | 'nonzero' | 'zero' | 'any'>(() => {
        if (effectiveQtyRule === 'positive' || effectiveQtyRule === 'negative') return 'positive';
        if (effectiveQtyRule === 'nonzero' || effectiveQtyRule === 'zero') return effectiveQtyRule;
        return 'any';
    });

    // The cash sign checks and `hasSignViolation` live above the validate scheduler, with
    // `hasLocalErrors`: the scheduler's constructor already reads them.

    // =========================================================================
    // W39: Inline broker / asset creation modals
    // =========================================================================
    let createBrokerOpen = $state(false);
    let createAssetOpen = $state(false);
    let createEventOpen = $state(false);

    function handleBrokerCreated(d: {id: number}) {
        // BrokerModal merges into brokerStore; just set the draft field
        draft = {...draft, broker_id: d.id};
        createBrokerOpen = false;
    }
    function handleAssetCreated(assetId: number) {
        draft = {...draft, asset_id: assetId};
        createAssetOpen = false;
        // Show info toast: remind user to sync prices after completing transactions
        const info = getAssetInfo(assetId);
        const name = info?.display_name || `#${assetId}`;
        toasts.info(`ℹ️ ${name} — ${$t('transactions.toast.assetCreatedHint')}`);
    }

    // =========================================================================
    // Validate-state chip text
    // =========================================================================

    /** W42: Deduplicate validation issues by `code` — in dual mode both halves
     *  can produce the same error code, showing it once is enough. */
    // Bugfix-4 §U16: validate chip removed in favor of the green/warning
    // banners (single source of truth). The footer now shows only an inline
    // "Validating…" indicator while a request is in flight (see template).
</script>

<ModalBase {open} maxWidth="3xl" onRequestClose={requestClose} testId="tx-form-modal" allowOverflow={true} {zIndex}>
    <div class="flex flex-col max-h-[90vh] min-h-[50vh]" data-testid="tx-form-modal-root" data-busy={scheduler.state.isPending || scheduler.state.isValidating || committing || loadingPartner} data-validate-runs={scheduler.state.validateRuns}>
        <!-- ============================================================= -->
        <!-- Header -->
        <!-- ============================================================= -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-lf-subtle shrink-0">
            <h2 class="text-lg font-semibold text-lf-primary" data-testid="tx-form-title">
                {#if pairLayout}
                    {#if pairLayout === 'fx'}💱{:else if pairLayout === 'transfer_asset'}📦{:else}🏦{/if}
                    {#if mode === 'edit'}
                        ✎ {dualTitle}
                        {#if mainRow?.id != null && mainRow?.related_transaction_id != null && mainRow.related_transaction_id > 0}
                            #{mainRow.id} ↔ #{mainRow.related_transaction_id}
                        {:else if mainRow?.id != null}
                            #{mainRow.id}
                        {:else}
                            (new pair)
                        {/if}
                    {:else if mode === 'view'}
                        👁 {dualTitle}
                        {#if mainRow?.id != null && mainRow?.related_transaction_id != null && mainRow.related_transaction_id > 0}
                            #{mainRow.id} ↔ #{mainRow.related_transaction_id}
                        {:else if mainRow?.id != null}
                            #{mainRow.id}
                        {/if}
                    {:else}{dualTitle}{/if}
                {:else if mode === 'create'}
                    ➕ {$t('transactions.form.titleCreate')}
                {:else if mode === 'edit'}
                    ✎ {$t('transactions.form.titleEdit')} #{mainRow?.id}
                {:else}
                    👁 {$t('transactions.form.titleView')} #{mainRow?.id}
                {/if}
            </h2>
            <div class="flex items-center gap-1">
                {#if isReadonly && onSwitchToEdit && canEdit}
                    <button class="p-2 text-lf-muted hover:text-lf-link hover:bg-lf-hover rounded-lg transition-colors" onclick={onSwitchToEdit} data-testid="tx-form-switch-edit" aria-label="Edit" title={$t('transactions.form.titleEdit') || 'Edit'}>
                        <Pencil size={18} />
                    </button>
                {/if}
                <button class="p-2 text-lf-muted hover:text-lf-secondary hover:bg-lf-hover rounded-lg transition-colors" onclick={requestClose} data-testid="tx-form-close" aria-label="Close">
                    <X size={20} />
                </button>
            </div>
        </div>

        <!-- ============================================================= -->
        <!-- Body (scrollable) -->
        <!-- ============================================================= -->
        <div class="overflow-y-auto flex-1 min-h-0 px-5 py-4 space-y-4" data-testid="tx-form-body" data-guide-scroll-root bind:this={formBodyEl}>
            <TxFormBanners {getBulkContext} bind:commitFailed bind:formError {issues} bind:issuesDismissed {loadingPartner} {balanceIssues} {dualValidationError} {fieldIssues} {resolverCtx} {showIssuesBanner} {handleSyncFx} />

            <!-- ============================================================= -->
            <!-- DUAL FORM — FX / Transfer Asset / Transfer Cash -->
            <!-- ============================================================= -->
            {#if pairLayout}
                <TxFormPairSection
                    {open}
                    {openKey}
                    {pendingTxIds}
                    bind:costBasisMode
                    bind:createAssetOpen
                    bind:createBrokerOpen
                    bind:draft
                    {dualTo}
                    {fxMarketPoint}
                    {inaccessiblePartnerBrokerId}
                    {partnerRow}
                    {wacCurrencyHint}
                    {allowedTypes}
                    {autocompleteNonce}
                    {brokerIdValue}
                    {rowSaved}
                    {brokerImmutable}
                    {brokerToIdValue}
                    {brokers}
                    {brokersForFrom}
                    {brokersForSelect}
                    {brokersForTo}
                    {displayedCostBasis}
                    {effectiveDualTo}
                    {externalWacResult}
                    {isReadonly}
                    {pairLayout}
                    {quantityInputId}
                    {quantityInputSignRule}
                    {typeImmutable}
                    {wacAvailableCurrencies}
                    {handleSyncFx}
                    {onCostBasisChange}
                    {onDateMainValidityChange}
                    {onDateToValidityChange}
                    {onQuantityValidityChange}
                    {onWacCurrencyChange}
                    {setAsset}
                    {setBroker}
                    {setBrokerTo}
                    {setCash}
                    {setCashTo}
                    {setDate}
                    {setDateTo}
                    {setQuantity}
                    {setType}
                    {swapDualSides}
                />

                <!-- ============================================================= -->
                <!-- STANDARD SINGLE FORM (unchanged) -->
                <!-- ============================================================= -->
            {:else}
                <TxFormSingleSection
                    {open}
                    {openKey}
                    {pendingTxIds}
                    bind:costBasisMode
                    bind:createAssetOpen
                    bind:createBrokerOpen
                    bind:draft
                    {wacCurrencyHint}
                    {allowedTypes}
                    {autocompleteNonce}
                    {brokerIdValue}
                    {rowSaved}
                    {brokerImmutable}
                    {brokers}
                    {brokersForSelect}
                    {cashHint}
                    {cashLabel}
                    {displayedCostBasis}
                    {externalWacResult}
                    {isReadonly}
                    {pairLayout}
                    {qtyHint}
                    {qtyLabel}
                    {quantityHintId}
                    {quantityInputId}
                    {quantityInputSignRule}
                    {rule}
                    {showCostBasisField}
                    {typeImmutable}
                    {wacAvailableCurrencies}
                    {handleSyncFx}
                    {onCostBasisChange}
                    {onDateMainValidityChange}
                    {onQuantityValidityChange}
                    {onWacCurrencyChange}
                    {setAsset}
                    {setBroker}
                    {setCash}
                    {setDate}
                    {setQuantity}
                    {setType}
                />
            {/if}

            <!-- Cost basis override — TRANSFER single-form (editing existing linked pair, non-dual) -->
            {#if !pairLayout && showCostBasisField && draft.type !== 'ADJUSTMENT'}
                <div class="mt-3" data-testid="tx-form-cost-basis-inline">
                    <WacPreviewSection
                        value={displayedCostBasis}
                        onChange={onCostBasisChange}
                        mode={costBasisMode}
                        defaultCode={draft.cash?.code ?? 'EUR'}
                        disabled={isReadonly}
                        hideTable={isReadonly}
                        testid="tx-form-cost-basis"
                        senderBrokerId={draft.broker_id}
                        assetId={draft.asset_id}
                        txDate={draft.date}
                        onModeChange={(m) => (costBasisMode = m)}
                        externalResult={externalWacResult}
                        {pendingTxIds}
                        wacCurrency={wacCurrencyHint}
                        onCurrencyChange={onWacCurrencyChange}
                        availableCurrencies={wacAvailableCurrencies}
                        onOpenFxSync={handleSyncFx}
                        quantity={draft.quantity}
                    />
                </div>
            {/if}

            <!-- Optional disclosure -->
            {#if !isReadonly || (draft.tags && draft.tags.length > 0) || (draft.description ?? '').trim() || draft.asset_event_id != null || draft.link_uuid != null || pairPartnerId != null}
                <TxFormOptionalSection {availableTags} bind:createEventOpen bind:draft bind:optionalOpen {canShowAssetEvent} {isReadonly} {pairPartnerId} {onDescriptionInput} />
            {/if}

            <!-- Read-only footer (edit/view) -->
            {#if (mode === 'edit' || mode === 'view') && mainRow}
                <div class="text-[10px] text-lf-muted border-t border-lf-subtle pt-3" data-testid="tx-form-readonly-footer">
                    ID #{mainRow.id}
                    {#if partnerRow}+ #{partnerRow.id}{/if}
                    {#if mainRow.created_at}· {$t('common.created')} {mainRow.created_at}{/if}
                    {#if mainRow.updated_at}· {$t('common.updated')} {mainRow.updated_at}{/if}
                </div>
            {/if}
        </div>

        <!-- ============================================================= -->
        <!-- Footer -->
        <!-- ============================================================= -->
        <div class="flex items-center justify-between gap-2 px-5 py-3 border-t border-lf-subtle shrink-0 text-xs">
            <div class="flex items-center gap-2 flex-wrap">
                {#if !isReadonly}
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-lf-secondary hover:bg-lf-hover disabled:opacity-40 disabled:cursor-not-allowed"
                        disabled={!isFormComplete}
                        onclick={validateNow}
                        data-testid="tx-form-validate-now"
                        title={$t('transactions.validate.now')}
                    >
                        ⚡ <span class="hidden sm:inline">{$t('transactions.validate.now')}</span>
                    </button>
                {/if}
                {#if scheduler.state.isValidating || scheduler.state.isPending}
                    <span class="text-[11px] text-lf-muted">{$t('transactions.validate.validating')}</span>
                {:else if isFreshlyValid}
                    <span class="text-lf-success text-xs flex items-center gap-1" data-testid="tx-form-valid-inline">
                        <Check size={14} />
                        {$t('transactions.validate.ok')}
                    </span>
                {/if}
            </div>
            <div class="flex items-center gap-2">
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary bg-lf-panel hover:bg-lf-neutral inline-flex items-center gap-1.5" onclick={requestClose} data-testid="tx-form-cancel" title={isReadonly ? $t('common.close') || 'Close' : $t('common.cancel')}
                    ><X size={15} /> <span class="hidden sm:inline">{isReadonly ? $t('common.close') || 'Close' : $t('common.cancel')}</span></button
                >
                {#if !isReadonly}
                    <button
                        type="button"
                        class="px-4 py-2 text-sm rounded-lg text-lf-on-action bg-lf-action hover:bg-lf-action-hover disabled:opacity-50 inline-flex items-center gap-1.5"
                        disabled={committing || loadingPartner || hasLocalErrors || (!commitOnSave && !isFormComplete)}
                        onclick={commit}
                        data-testid="tx-form-save"
                        use:guideAnchor={'transaction.create.save'}
                        title={committing ? $t('common.saving') : !commitOnSave ? $t('common.apply') : $t('common.save')}
                    >
                        {#if committing}
                            <span class="hidden sm:inline">{$t('common.saving')}</span>
                        {:else if !commitOnSave}
                            <Check size={16} /> <span class="hidden sm:inline">{$t('common.apply')}</span>
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

<!-- W39: Inline broker creation modal. -->
<BrokerModal isOpen={createBrokerOpen} mode="create" zIndex={zIndex + 10} oncreated={(d) => handleBrokerCreated(d)} onclose={() => (createBrokerOpen = false)} />

<!-- W39: Inline asset creation modal. AssetModal is Svelte 5 (runes). -->
<AssetModal bind:open={createAssetOpen} zIndex={zIndex + 10} oncreated={handleAssetCreated} onclose={() => (createAssetOpen = false)} />

<!-- Inline event creation mini-modal -->
{#if draft.asset_id != null}
    <EventCreateMiniModal
        open={createEventOpen}
        assetId={draft.asset_id}
        assetName={getAssetInfo(draft.asset_id)?.display_name || ''}
        assetCurrency={getAssetInfo(draft.asset_id)?.currency || 'USD'}
        defaultDate={draft.date}
        suggestedAmount={draft.cash?.amount || ''}
        defaultEventType={draft.type}
        zIndex={zIndex + 10}
        oncreated={(eventId) => {
            draft = {...draft, asset_event_id: eventId};
            createEventOpen = false;
        }}
        onclose={() => (createEventOpen = false)}
    />
{/if}

<!-- FxSyncModal for WAC missing pairs -->
{#if showFxSyncModal}
    <FxSyncModal
        bind:open={showFxSyncModal}
        dateStart={fxSyncDateStart}
        dateEnd={fxSyncDateEnd}
        pairs={fxSyncPairs}
        zIndex={zIndex + 10}
        onsynced={() => {
            if (!hasLocalErrors) scheduler.trigger('manual');
        }}
        onclose={() => {
            showFxSyncModal = false;
        }}
    />
{/if}

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

    /* Duplicate-compare highlight: soft amber background + smooth entrance.
       Starts transparent → peaks bright yellow → settles to a light tint.
       animation-fill-mode: forwards keeps the resting state after the animation. */
</style>
