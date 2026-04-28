<!--
  TransactionFormModal.svelte — Single-row CRUD modal for transactions.

  Modes:
  - 'create'   → blank form, POST /transactions/bulk with 1 item
  - 'edit'     → pre-filled from initialRow (id immutable, type/broker locked),
                 PATCH /transactions/bulk with 1 TXUpdateItem
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

  Validate scheduler: 1 row → always under threshold → debounce + idle ON.
  On commit rolled_back=true → banner persistent, modal stays open.

  Pattern: Svelte 5 runes, ModalBase shell, savewithretry for HTTP errors,
  data-testid everywhere.
-->
<script lang="ts">
    import {onDestroy, untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {X} from 'lucide-svelte';

    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import BrokerSearchSelect from '$lib/components/ui/select/BrokerSearchSelect.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import SingleDatePicker from '$lib/components/ui/SingleDatePicker.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import CompactCashCell from '$lib/components/ui/CompactCashCell.svelte';
    import TransactionTypeSearchSelect from './TransactionTypeSearchSelect.svelte';

    import {zodiosApi} from '$lib/api';
    import {ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {ensureAssetsLoaded, getAssetInfo} from '$lib/stores/assetStore';
    import {ensureBrokersLoaded, getAllBrokers, brokerStoreVersion, type BrokerInfo} from '$lib/stores/brokerStore';
    import {type TransactionTypeCode, getTransactionTypeIconUrl} from '$lib/utils/transactionTypes';
    import {getTypeRule, isDraftReadyForValidation} from '$lib/utils/transactionTypeRules';
    import {createValidateScheduler} from '$lib/utils/useValidateScheduler.svelte';
    import {saveWithRetry, extractErrorMessage} from '$lib/utils/saveWithRetry';
    import {generateUUID} from '$lib/utils/uuid';
    import {formatDecimalForDisplay} from '$lib/utils/formatDecimal';

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
    }

    type Mode = 'create' | 'edit' | 'duplicate' | 'view';

    interface Props {
        open: boolean;
        mode: Mode;
        initialRow?: TXReadItem | null;
        /** When opened from the wizard: pre-select this broker. */
        forcedBroker?: number | null;
        onClose: () => void;
        onCommitted?: (resp: {transaction_id?: number | null}) => void;
    }

    let {open, mode, initialRow = null, forcedBroker = null, onClose, onCommitted}: Props = $props();

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

    function todayIso(): string {
        return new Date().toISOString().slice(0, 10);
    }

    function emptyDraft(): FormDraft {
        const brokers = getAllBrokers();
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

    function fromTx(tx: TXReadItem, opts: {regenerateLink?: boolean; resetDate?: boolean} = {}): FormDraft {
        return {
            broker_id: tx.broker_id,
            asset_id: tx.asset_id ?? null,
            type: tx.type as TransactionTypeCode,
            date: opts.resetDate ? todayIso() : tx.date,
            quantity: tx.quantity,
            cash: tx.cash ? {code: tx.cash.code, amount: tx.cash.amount} : null,
            tags: [...(tx.tags ?? [])],
            description: tx.description ?? '',
            asset_event_id: tx.asset_event_id ?? null,
            cost_basis_override: tx.cost_basis_override ?? '',
            link_uuid: opts.regenerateLink ? generateUUID() : null,
        };
    }

    // Single source-of-truth state (computed from props in $effect, never read inside the same effect).
    let draft = $state<FormDraft>(emptyDraft());
    let issues = $state<ValidationIssue[]>([]);
    let formError = $state<string | null>(null);
    let committing = $state(false);
    let optionalOpen = $state(false);
    let advancedOpen = $state(false);
    /** Snapshot of `draft` at modal-open time, used to detect unsaved
     *  changes (Bugfix-3 §C11). */
    let initialDraftKey = $state('');
    let confirmCloseOpen = $state(false);
    /** User-facing display string for `draft.quantity`. Decoupled from the
     *  authoritative payload so the user can type freely (e.g. "0.0000")
     *  without us reformatting mid-keystroke (Bugfix-4 §U18). The display
     *  is reseeded from `draft.quantity` whenever the draft itself is reset
     *  (modal open, type change reset). */
    let qtyDisplay = $state('');

    // Reset draft on open; broker store must be loaded first.
    $effect(() => {
        if (!open) return;
        // Read props inside `untrack` — we only want to recompute when `open` flips,
        // not on every initialRow/mode mutation that may be irrelevant.
        const m = mode;
        const row = initialRow;
        untrack(() => {
            issues = [];
            formError = null;
            optionalOpen = false;
            advancedOpen = false;
            confirmCloseOpen = false;
            if (m === 'create') {
                draft = emptyDraft();
            } else if (m === 'duplicate' && row) {
                draft = fromTx(row, {regenerateLink: row.related_transaction_id != null, resetDate: true});
            } else if ((m === 'edit' || m === 'view') && row) {
                draft = fromTx(row);
            } else {
                draft = emptyDraft();
            }
            lastTypeForReset = draft.type;
            initialDraftKey = JSON.stringify(draft);
            qtyDisplay = formatDecimalForDisplay(draft.quantity);
        });
        // Async hydration (brokers + currencies + asset cache for the picked asset).
        void (async () => {
            await Promise.all([ensureBrokersLoaded(), ensureCurrenciesLoaded($currentLanguage), ensureAssetsLoaded()]);
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
                initialDraftKey = JSON.stringify(draft);
            });
        })();
    });

    /** Detect unsaved changes vs. the snapshot taken at modal-open. */
    function hasUnsavedChanges(): boolean {
        if (isReadonly) return false;
        return JSON.stringify(draft) !== initialDraftKey;
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
            if (r.quantityRule === 'zero') {
                next.quantity = '0';
                qtyDisplay = '0';
            }
            // Clear linked event when no longer applicable.
            if (!r.eventLinkable && next.asset_event_id != null) next.asset_event_id = null;
            // Clear cost basis when not a TRANSFER (only meaningful there).
            if (t !== 'TRANSFER' && next.cost_basis_override) next.cost_basis_override = '';
            draft = next;
        });
    });

    // =========================================================================
    // Brokers (reactive view of brokerStore)
    // =========================================================================

    let brokers = $derived.by<BrokerInfo[]>(() => {
        void $brokerStoreVersion;
        return getAllBrokers();
    });

    // =========================================================================
    // Type rule + derived UI state
    // =========================================================================

    let rule = $derived(getTypeRule(draft.type));
    let isReadonly = $derived(mode === 'view');
    let typeImmutable = $derived(mode === 'edit' || mode === 'view');
    let brokerImmutable = $derived(mode === 'edit' || mode === 'view' || forcedBroker != null);
    let canShowAssetEvent = $derived(rule.eventLinkable && draft.asset_id != null);

    // cost_basis_override is meaningful only for the receiver of a TRANSFER pair.
    // Single-form mode rarely creates TRANSFER (uses wizard), so we expose the
    // field whenever type=TRANSFER and let the backend enforce semantics.
    let showCostBasisField = $derived(draft.type === 'TRANSFER');

    // Pair partner chip (only when editing an existing linked tx).
    let pairPartnerId = $derived(initialRow?.related_transaction_id ?? null);

    // =========================================================================
    // Validate scheduler — debounced/manual/idle, always enabled (1 row).
    // =========================================================================

    const scheduler = createValidateScheduler({
        // Auto-fire only when the draft is "ready" — i.e. all required fields
        // for its type are populated (Bugfix-2 §C5). Manual ⚡ Validate now
        // always fires regardless.
        enabled: () => !isReadonly && isDraftReadyForValidation(draft),
        validateFn: async () => {
            if (isReadonly) return {issuesCount: 0};
            const payload = mode === 'edit' ? {updates: [collectUpdate()]} : {creates: [collectCreate()]};
            const sentKey = lastDraftKey;
            try {
                const res = (await zodiosApi.validate_transactions_api_v1_transactions_validate_post(payload as never)) as {issues?: ValidationIssue[]};
                issues = res?.issues ?? [];
                lastValidatedDraftKey = sentKey;
                issuesDismissed = false;
                return {issuesCount: issues.length};
            } catch (e) {
                // Pydantic 422 → readable per-field summary; otherwise fall back to message.
                const msg = extractErrorMessage(e, $t('transactions.form.saveFailed'));
                issues = [{operation: mode === 'edit' ? 'update' : 'create', index: 0, error: msg}];
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
    $effect(() => {
        if (!open || isReadonly) return;
        const key = JSON.stringify(draft);
        if (key === lastDraftKey) return;
        lastDraftKey = key;
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
    let showAdvancedSection = $derived((rule.eventLinkable && draft.asset_id != null) || draft.type === 'TRANSFER' || pairPartnerId != null || (mode === 'edit' && draft.link_uuid != null));

    /** BrokerSearchSelect expects `BrokerSelectItem[]`; the brokerStore's
     *  `BrokerInfo` is structurally compatible (id/name/icon_url present)
     *  but TS can't widen via the prop attribute. We cast in script. */
    let brokersForSelect = $derived(brokers as unknown as Array<{id: number; name: string; icon_url?: string | null}>);
    let brokerIdValue = $derived<number | null>(draft.broker_id || null);

    // =========================================================================
    // Sanitizers
    // =========================================================================

    function collectCreate(): Record<string, unknown> {
        const out: Record<string, unknown> = {
            broker_id: draft.broker_id,
            type: draft.type,
            date: draft.date,
            quantity: draft.quantity,
        };
        if (draft.asset_id != null && rule.assetField !== 'forbidden') out.asset_id = draft.asset_id;
        if (draft.cash && rule.cashField !== 'forbidden') out.cash = draft.cash;
        if (draft.tags.length > 0) out.tags = draft.tags;
        if (draft.description.trim()) out.description = draft.description.trim();
        if (draft.asset_event_id != null && rule.eventLinkable) out.asset_event_id = draft.asset_event_id;
        if (draft.cost_basis_override.trim() && showCostBasisField) out.cost_basis_override = draft.cost_basis_override.trim();
        if (draft.link_uuid && rule.requiresPair) out.link_uuid = draft.link_uuid;
        return out;
    }

    function collectUpdate(): Record<string, unknown> {
        const out: Record<string, unknown> = {id: initialRow?.id};
        if (!initialRow) return out;
        if (draft.date !== initialRow.date) out.date = draft.date;
        if (draft.quantity !== initialRow.quantity) out.quantity = draft.quantity;
        const origCash = JSON.stringify(initialRow.cash ?? null);
        const newCash = JSON.stringify(draft.cash ?? null);
        if (origCash !== newCash) out.cash = draft.cash ?? null;
        const origTags = JSON.stringify(initialRow.tags ?? []);
        const newTags = JSON.stringify(draft.tags);
        if (origTags !== newTags) out.tags = draft.tags;
        if ((initialRow.description ?? '') !== draft.description) out.description = draft.description || null;
        if ((initialRow.cost_basis_override ?? '') !== draft.cost_basis_override) {
            out.cost_basis_override = draft.cost_basis_override || null;
        }
        // asset_event_id sentinel: 0 = unlink
        const origEvent = initialRow.asset_event_id ?? null;
        const newEvent = draft.asset_event_id;
        if (origEvent !== newEvent) {
            out.asset_event_id = newEvent ?? 0;
        }
        return out;
    }

    // =========================================================================
    // Commit
    // =========================================================================

    async function commit() {
        if (isReadonly || committing) return;
        committing = true;
        formError = null;
        try {
            if (mode === 'edit') {
                const result = await saveWithRetry(() => zodiosApi.update_transactions_bulk_api_v1_transactions_bulk_patch([collectUpdate()] as never), {fallback: $t('transactions.form.saveFailed'), toast: false});
                if (result.status === 'error') {
                    formError = result.message;
                    return;
                }
                const resp = result.data as {rolled_back?: boolean; errors?: string[]; results?: Array<{id: number}>};
                if (resp.rolled_back) {
                    formError = (resp.errors?.[0] ?? $t('transactions.form.rolledBack')) as string;
                    return;
                }
                onCommitted?.({transaction_id: resp.results?.[0]?.id ?? null});
                onClose();
            } else {
                // create / duplicate
                const result = await saveWithRetry(() => zodiosApi.create_transactions_bulk_api_v1_transactions_bulk_post([collectCreate()] as never), {fallback: $t('transactions.form.saveFailed'), toast: false});
                if (result.status === 'error') {
                    formError = result.message;
                    return;
                }
                const resp = result.data as {rolled_back?: boolean; errors?: string[]; results?: Array<{transaction_id?: number | null}>};
                if (resp.rolled_back) {
                    formError = (resp.errors?.[0] ?? $t('transactions.form.rolledBack')) as string;
                    return;
                }
                onCommitted?.({transaction_id: resp.results?.[0]?.transaction_id ?? null});
                onClose();
            }
        } finally {
            committing = false;
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
    function addTag(raw: string) {
        const v = raw.trim();
        if (!v) return;
        if (draft.tags.includes(v)) return;
        draft = {...draft, tags: [...draft.tags, v]};
    }
    function removeTag(idx: number) {
        const next = [...draft.tags];
        next.splice(idx, 1);
        draft = {...draft, tags: next};
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

    // Tag input local buffer.
    let tagInputBuffer = $state('');
    function handleTagKey(e: KeyboardEvent) {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            addTag(tagInputBuffer);
            tagInputBuffer = '';
        }
    }

    // =========================================================================
    // Quantity / cash sign hints
    // =========================================================================

    let qtyHint = $derived.by(() => {
        switch (rule.quantityRule) {
            case 'positive':
                return $t('transactions.form.hintQtyPositive');
            case 'negative':
                return $t('transactions.form.hintQtyNegative');
            case 'zero':
                return $t('transactions.form.hintQtyZero');
            case 'nonzero':
                return $t('transactions.form.hintQtyNonzero');
            default:
                return '';
        }
    });

    // =========================================================================
    // Validate-state chip text
    // =========================================================================

    // Bugfix-4 §U16: validate chip removed in favor of the green/warning
    // banners (single source of truth). The footer now shows only an inline
    // "Validating…" indicator while a request is in flight (see template).

</script>

<ModalBase {open} maxWidth="3xl" onRequestClose={requestClose} testId="tx-form-modal" allowOverflow={true}>
    <div class="flex flex-col max-h-[90vh] min-h-[50vh]" data-testid="tx-form-modal-root">
        <!-- ============================================================= -->
        <!-- Header -->
        <!-- ============================================================= -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-gray-100 dark:border-slate-700 shrink-0">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100" data-testid="tx-form-title">
                {#if mode === 'create'}
                    ➕ {$t('transactions.form.titleCreate')}
                {:else if mode === 'duplicate'}
                    📋 {$t('transactions.form.titleDuplicate')}
                {:else if mode === 'edit'}
                    ✎ {$t('transactions.form.titleEdit')} #{initialRow?.id}
                {:else}
                    👁 {$t('transactions.form.titleView')} #{initialRow?.id}
                {/if}
            </h2>
            <button class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors" onclick={requestClose} data-testid="tx-form-close" aria-label="Close">
                <X size={20} />
            </button>
        </div>

        <!-- ============================================================= -->
        <!-- Body (scrollable) -->
        <!-- ============================================================= -->
        <div class="overflow-y-auto flex-1 min-h-0 px-5 py-4 space-y-4" data-testid="tx-form-body">
            <!-- Inline banners (Bugfix-4 §U16: green ✓ when validate is fresh
                 and clean; warning with × dismiss when there are issues). -->
            {#if formError}
                <InfoBanner variant="error">
                    <p class="font-semibold mb-1" data-testid="tx-form-error">⛔ {$t('transactions.form.rolledBackTitle')}</p>
                    <p>{formError}</p>
                </InfoBanner>
            {:else if isFreshlyValid}
                <InfoBanner variant="success">
                    <p data-testid="tx-form-valid">✓ {$t('transactions.validate.ok')}</p>
                </InfoBanner>
            {:else if showIssuesBanner}
                <InfoBanner variant="warning" dismissible ondismiss={() => (issuesDismissed = true)}>
                    <ul class="space-y-0.5" data-testid="tx-form-issues">
                        {#each issues as issue}
                            <li data-testid="tx-form-issue">{issue.error}</li>
                        {/each}
                    </ul>
                </InfoBanner>
            {/if}

            <!-- Required section -->
            <fieldset class="border border-gray-200 dark:border-slate-700 rounded-lg p-4" data-testid="tx-form-required">
                <legend class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 px-1">{$t('transactions.form.sectionRequired')}</legend>

                <!-- Reordered to match table column order (Bugfix-1 §U5):
                     Date → Type → Quantity → Cash → Asset → Broker -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                    <!-- Date -->
                    <div class="flex flex-col gap-1" data-testid="tx-form-date-wrap">
                        <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.date')}</span>
                        {#if isReadonly}
                            <div class="px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-gray-200" data-testid="tx-form-date-readonly">{draft.date || '—'}</div>
                        {:else}
                            <SingleDatePicker bind:value={draft.date} label="" onchange={(d) => setDate(d)} />
                        {/if}
                    </div>

                    <!-- Type -->
                    <div class="flex flex-col gap-1" data-testid="tx-form-type-wrap">
                        <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.type')}</span>
                        {#if typeImmutable}
                            <!-- Bugfix-4 §U17: render the readonly type as a
                                 plain inline [icon] [name] row matching the
                                 height of other selectors — no big rectangle
                                 around a tiny badge. -->
                            <div class="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-gray-200" data-testid="tx-form-type-readonly">
                                <img src={getTransactionTypeIconUrl(draft.type)} alt="" class="w-5 h-5 object-contain shrink-0" onerror={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')} />
                                <span class="font-medium">{$t(`transactions.types.${draft.type}`) || draft.type}</span>
                            </div>
                        {:else}
                            <TransactionTypeSearchSelect value={draft.type} onchange={(v) => setType(v)} disabled={isReadonly} testid="tx-form-type" />
                        {/if}
                    </div>

                    <!-- Quantity -->
                    {#if rule.quantityRule !== 'zero'}
                        <div class="flex flex-col gap-1" data-testid="tx-form-quantity-wrap">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.quantity')}</span>
                            <input
                                type="text"
                                inputmode="decimal"
                                autocomplete="off"
                                spellcheck="false"
                                name="qty-{autocompleteNonce}"
                                class="px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg text-right font-mono tabular-nums disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-libre-green/30"
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
                    {:else}
                        <div class="flex flex-col gap-1 opacity-60" data-testid="tx-form-quantity-locked">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.quantity')}</span>
                            <div class="px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-right text-gray-400 text-xs">0 ({$t('transactions.form.hintQtyZero')})</div>
                        </div>
                    {/if}

                    <!-- Cash -->
                    {#if rule.cashField !== 'forbidden'}
                        <div class="flex flex-col gap-1" data-testid="tx-form-cash-wrap">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.cash')}{rule.cashField === 'required' ? ' *' : ''}</span>
                            <CompactCashCell value={draft.cash} onChange={setCash} signHint={rule.cashSign} disabled={isReadonly} testid="tx-form-cash" defaultCode={(draft.asset_id != null && getAssetInfo(draft.asset_id)?.currency) || 'EUR'} />
                        </div>
                    {:else}
                        <div class="flex flex-col gap-1 opacity-60" data-testid="tx-form-cash-locked">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.cash')}</span>
                            <div class="px-3 py-2 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-gray-400 text-xs">— ({$t('transactions.types.' + draft.type)} doesn't use cash)</div>
                        </div>
                    {/if}
                </div>

                <!-- Asset (full width) -->
                {#if rule.assetField !== 'forbidden'}
                    <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-asset-wrap">
                        <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.table.asset')}{rule.assetField === 'required' ? ' *' : ''}</span>
                        <AssetSelect bind:value={draft.asset_id} disabled={isReadonly} onchange={setAsset} testid="tx-form-asset" />
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
                        <BrokerSearchSelect brokers={brokersForSelect} value={brokerIdValue} onchange={(id) => setBroker(id ?? 0)} />
                    {/if}
                </div>
            </fieldset>

            <!-- Optional disclosure -->
            {#if !isReadonly || draft.tags.length > 0 || draft.description.trim()}
                <details class="border border-gray-200 dark:border-slate-700 rounded-lg" bind:open={optionalOpen}>
                    <summary class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 px-4 py-3 cursor-pointer select-none" data-testid="tx-form-optional-toggle">{$t('transactions.form.sectionOptional')}</summary>
                    <div class="px-4 pb-4 space-y-3 text-sm">
                        <!-- Tags -->
                        <div class="flex flex-col gap-1">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.form.tags')}</span>
                            <div class="flex flex-wrap items-center gap-1.5 px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg min-h-[38px]" data-testid="tx-form-tags">
                                {#each draft.tags as tag, i}
                                    <span class="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded bg-gray-100 dark:bg-slate-700">
                                        {tag}
                                        {#if !isReadonly}
                                            <button type="button" class="text-gray-400 hover:text-red-500" aria-label="remove tag" onclick={() => removeTag(i)} data-testid={`tx-form-tag-remove-${i}`}>×</button>
                                        {/if}
                                    </span>
                                {/each}
                                {#if !isReadonly}
                                    <input type="text" autocomplete="off" class="flex-1 min-w-[5rem] bg-transparent text-xs outline-none" placeholder={$t('transactions.form.tagsPlaceholder')} bind:value={tagInputBuffer} onkeydown={handleTagKey} data-testid="tx-form-tag-input" />
                                {/if}
                            </div>
                        </div>

                        <!-- Description -->
                        <label class="flex flex-col gap-1">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('transactions.form.description')}</span>
                            <textarea autocomplete="off" class="px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg resize-y min-h-[60px] disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-libre-green/30" rows="2" bind:value={draft.description} disabled={isReadonly} oninput={onDescriptionInput} data-testid="tx-form-description" maxlength="500"></textarea>
                        </label>
                    </div>
                </details>
            {/if}

            <!-- Advanced disclosure (Bugfix-1 §U6: gated) -->
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
                                <input type="text" inputmode="decimal" autocomplete="off" name="cb-{autocompleteNonce}" class="flex-1 px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg disabled:opacity-60" placeholder="auto" value={draft.cost_basis_override} disabled={isReadonly} oninput={onCostBasisInput} data-testid="tx-form-cost-basis" />
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
                    {#if initialRow.created_at}· {$t('common.created')} {initialRow.created_at}{/if}
                    {#if initialRow.updated_at}· {$t('common.updated')} {initialRow.updated_at}{/if}
                </div>
            {/if}
        </div>

        <!-- ============================================================= -->
        <!-- Footer -->
        <!-- ============================================================= -->
        <div class="flex items-center justify-between gap-2 px-5 py-3 border-t border-gray-100 dark:border-slate-700 shrink-0">
            <!-- Bugfix-4 §U16: drop the chip — the green/warning banner above
                 already conveys validate state. Show only "Validating…" while
                 a request is in flight. -->
            <span class="text-[11px] text-gray-500 dark:text-gray-400">
                {#if scheduler.state.isValidating}{$t('transactions.validate.validating')}{/if}
            </span>
            <div class="flex items-center gap-2">
                {#if !isReadonly}
                    <button type="button" class="px-3 py-2 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700" onclick={() => scheduler.trigger('manual')} data-testid="tx-form-validate-now">⚡ {$t('transactions.validate.now')}</button>
                {/if}
                <button type="button" class="px-4 py-2 text-sm rounded-lg text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600" onclick={requestClose} data-testid="tx-form-cancel">{isReadonly ? $t('common.close') || 'Close' : $t('common.cancel')}</button>
                {#if !isReadonly}
                    <button type="button" class="px-4 py-2 text-sm rounded-lg text-white bg-libre-green hover:bg-libre-green/90 disabled:opacity-50" disabled={committing} onclick={commit} data-testid="tx-form-save">
                        {committing ? $t('common.saving') : $t('common.save')}
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












