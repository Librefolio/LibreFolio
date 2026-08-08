<!--
  FixFlaggedStep.svelte — import wizard step "Correggi le righe segnalate".

  Shows the rows the plugin booked but could not fully understand and lets the user settle
  each one before anything is compared against the database: a trade it could not read
  (`blocker`, red) or a charge it could not attach to an instrument (`warning`, amber).

  Why this is a step and not a banner in the review table: the duplicate check compares
  type, date, amount and asset. A purchase the plugin could only record as a cash
  withdrawal — because the file gave it no quantity and no instrument — is compared
  against cash withdrawals, so a real duplicate can be missed or an imaginary one
  invented. Correcting after the comparison cannot repair that; correcting before it can.

  Settled rows stay in the list, recoloured and badged, and remain editable: a decision
  the user cannot see is a decision they cannot revise.

  The step auto-skips when there is nothing flagged (see `stepIsActive` in the wizard).
-->
<script lang="ts">
    import {t} from 'svelte-i18n';
    import {AlertTriangle, Check, CheckCircle, ChevronDown, ChevronRight, Hand, RotateCcw, Wrench} from 'lucide-svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import SearchSelect from '$lib/components/ui/select/SearchSelect.svelte';
    import TransactionTypeSearchSelect from '$lib/components/transactions/shared/TransactionTypeSearchSelect.svelte';
    import BrimEvidenceTable from './BrimEvidenceTable.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {getTypeRule, type TransactionTypeCode} from '$lib/stores/transactions/transactionTypeStore';
    import {translateFieldName} from '$lib/utils/transactions/resolveValidationMessage';
    import {decimalArrowStep, normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';
    import type {BrimEvidence} from '$lib/types';
    import type {SelectOption} from '$lib/components/ui/select/types';

    interface FlaggedTodo {
        field: string;
        severity: 'blocker' | 'warning';
        reasonCode: string;
        message: string;
        evidence?: BrimEvidence[];
    }

    /** How the user settled a row. `null` = still waiting for them. */
    export type FixDecision = 'corrected' | 'kept' | null;

    interface FlaggedRow {
        index: number;
        /**
         * The transaction as it stands. Deliberately untyped: the generated `TXCreateItem`
         * models several fields as `T | T[]` (a FastAPI union artefact), and this component
         * only ever reads three of them.
         */
        tx: Record<string, unknown>;
        todos: FlaggedTodo[];
        decision: FixDecision;
    }

    /** An instrument the analysis already recognised in these files. */
    export interface AnalysisAsset {
        /** Value written into `asset_id` — the wizard's placeholder id for this instrument. */
        id: number;
        label: string;
        detail: string;
    }

    export interface FixPatch {
        type?: string;
        asset_id?: number | null;
        quantity?: string;
    }

    interface Props {
        rows: FlaggedRow[];
        /**
         * Instruments identified during the analysis. The asset of a flagged row is almost
         * always one of these — the file named it on another line. Searching the whole
         * database first would be asking the user to find what the import already found.
         */
        analysisAssets: AnalysisAsset[];
        expanded: Set<number>;
        ontoggle: (index: number) => void;
        onapply: (index: number, patch: FixPatch) => void;
        onaccept: (index: number) => void;
        /** Settle every still-pending row as "keep the plugin's reading". */
        onacceptall: () => void;
        /**
         * The instrument is in neither list: ask the wizard to open the asset creation
         * modal, seeded with what the file says about this row.
         */
        oncreateasset: (index: number) => void;
        /**
         * Assets created through `oncreateasset`, keyed by row index. The wizard owns the
         * creation modal, so the id comes back this way instead of through the draft.
         */
        createdAssets?: Record<number, number>;
        /** Put a row back the way the plugin read it, decision and edits discarded. */
        onreset: (index: number) => void;
        /** Same for every row already settled. */
        onresetall: () => void;
        /** Open the source file of a flagged row at the given 1-based line. */
        ongotosource?: (index: number, rowNumbers: number[]) => void;
    }

    let {rows, analysisAssets, expanded, ontoggle, onapply, onaccept, onacceptall, onreset, onresetall, oncreateasset, createdAssets = {}, ongotosource}: Props = $props();

    const DB_SEARCH = '__db__';
    /** Explicit "this belongs to no instrument" — see `assetOptionsFor`. */
    const NO_ASSET = '__none__';

    let pendingRows = $derived(rows.filter((r) => r.decision === null));
    let settledRows = $derived(rows.filter((r) => r.decision !== null));

    /**
     * A blocker todo carries the same `reason_code`/`message` pair as a notice, so the
     * localised wording lives at the same key namespace with the plugin string as the
     * fallback — the plugin author's language is better than a bare code.
     */
    function todoMessage(todo: FlaggedTodo | undefined): string {
        if (!todo) return '';
        const key = `importWizard.brimNotice.${todo.reasonCode}`;
        const translated = $t(key);
        return translated === key ? todo.message : translated;
    }

    /** Per-row draft edits, keyed by merged-tx index. */
    let drafts = $state<Record<number, FixPatch>>({});
    /** Rows where the user asked for the full database instead of the analysis list. */
    let dbSearchRows = $state<Set<number>>(new Set());

    function txType(row: FlaggedRow): string {
        return typeof row.tx.type === 'string' ? row.tx.type : '';
    }

    function txAssetId(row: FlaggedRow): number | null {
        return typeof row.tx.asset_id === 'number' ? row.tx.asset_id : null;
    }

    function txQuantity(row: FlaggedRow): string {
        const q = row.tx.quantity;
        return typeof q === 'string' || typeof q === 'number' ? String(q) : '';
    }

    function draftFor(row: FlaggedRow): FixPatch {
        return drafts[row.index] ?? {type: txType(row), asset_id: txAssetId(row), quantity: txQuantity(row)};
    }

    function setDraft(index: number, patch: FixPatch) {
        drafts = {...drafts, [index]: {...draftFor(rows.find((r) => r.index === index)!), ...patch}};
    }

    let assetOptions = $derived<SelectOption[]>([
        ...analysisAssets.map((a) => ({
            value: String(a.id),
            label: a.label,
            searchText: a.detail,
        })),
        {value: DB_SEARCH, label: $t('importWizard.fixStep.assetFromDb')},
    ]);

    /**
     * A fee or a tax may legitimately belong to no instrument — an account charge is the
     * bank's, not a security's. Without an explicit way to say so, "leave it empty" and
     * "I have not answered yet" look identical, and the row can never be settled.
     */
    function assetOptionsFor(row: FlaggedRow): SelectOption[] {
        const rule = getTypeRule(draftFor(row).type ?? '');
        if (rule.assetField === 'required') return assetOptions;
        return [{value: NO_ASSET, label: $t('importWizard.fixStep.assetNone')}, ...assetOptions];
    }

    /**
     * Assets the user created from this step arrive as real database ids, so they land in
     * the database picker rather than the analysis list. Applied once per row: re-applying
     * would fight with any later change the user makes to the same field.
     */
    let appliedCreated = new Set<number>();
    $effect(() => {
        for (const [key, assetId] of Object.entries(createdAssets)) {
            const index = Number(key);
            if (appliedCreated.has(index)) continue;
            appliedCreated.add(index);
            const row = rows.find((r) => r.index === index);
            if (!row) continue;
            dbSearchRows = new Set(dbSearchRows).add(index);
            setDraft(index, {asset_id: assetId});
        }
    });

    /** Rows where the user explicitly answered "no instrument" — see `assetOptionsFor`. */
    let noAssetRows = $state<Set<number>>(new Set());

    function assetSelectValue(row: FlaggedRow): string {
        if (dbSearchRows.has(row.index)) return DB_SEARCH;
        const id = draftFor(row).asset_id;
        if (id == null) return noAssetRows.has(row.index) ? NO_ASSET : '';
        return analysisAssets.some((a) => a.id === id) ? String(id) : DB_SEARCH;
    }

    function onAssetOptionPicked(row: FlaggedRow, value: string) {
        const db = new Set(dbSearchRows);
        const none = new Set(noAssetRows);
        db.delete(row.index);
        none.delete(row.index);
        if (value === DB_SEARCH) db.add(row.index);
        if (value === NO_ASSET) none.add(row.index);
        dbSearchRows = db;
        noAssetRows = none;
        setDraft(row.index, {asset_id: value === DB_SEARCH || value === NO_ASSET ? null : Number(value)});
    }

    /**
     * A draft is applicable only if it is coherent: an instrument operation needs an
     * instrument and a non-zero quantity. Letting a half-corrected row through would
     * just move the same ambiguity one step later.
     */
    function draftIsValid(row: FlaggedRow): boolean {
        const d = draftFor(row);
        const type = d.type ?? '';
        if (!type) return false;
        const rule = getTypeRule(type);
        if (rule.assetField === 'required' && d.asset_id == null) return false;
        if (rule.quantityMode === 'required') {
            const q = Number(normalizeDecimalInput(String(d.quantity ?? '')));
            if (!Number.isFinite(q) || q === 0) return false;
        }
        // Answering "no instrument" on a row flagged for its missing instrument is a real
        // correction even though it changes no field — it is the answer to the question.
        if (noAssetRows.has(row.index) && txAssetId(row) === null) return true;
        return type !== txType(row) || (d.asset_id ?? null) !== txAssetId(row) || String(d.quantity ?? '') !== txQuantity(row);
    }

    function apply(row: FlaggedRow) {
        const d = draftFor(row);
        onapply(row.index, {type: d.type, asset_id: d.asset_id, quantity: normalizeDecimalInput(String(d.quantity ?? ''))});
        drafts = Object.fromEntries(Object.entries(drafts).filter(([k]) => Number(k) !== row.index));
    }

    function clearLocalState(index: number) {
        drafts = Object.fromEntries(Object.entries(drafts).filter(([k]) => Number(k) !== index));
        dbSearchRows = new Set([...dbSearchRows].filter((i) => i !== index));
        noAssetRows = new Set([...noAssetRows].filter((i) => i !== index));
        appliedCreated.delete(index);
    }

    function reset(row: FlaggedRow) {
        clearLocalState(row.index);
        onreset(row.index);
    }

    function resetAll() {
        for (const row of resettableRows) clearLocalState(row.index);
        onresetall();
    }

    /** A row is resettable once it has been settled, or once it carries unsaved edits. */
    let resettableRows = $derived(rows.filter((r) => r.decision !== null));
    function rowIsResettable(row: FlaggedRow): boolean {
        return row.decision !== null || drafts[row.index] !== undefined;
    }

    /**
     * Not every flagged row is broken. A trade the plugin could not read at all is red;
     * a charge it could not attach to an instrument is amber — real, usable, and only
     * worth a look. Painting them alike would teach the user to skim past both.
     */
    function rowIsBlocking(row: FlaggedRow): boolean {
        return row.todos.some((td) => td.severity === 'blocker');
    }

    /**
     * Cash out cannot become a dividend and cash in cannot become a purchase. Offering the
     * full type list invites a correction that contradicts the amount the bank actually
     * moved — the one number in the row we know to be right.
     */
    const CASH_OUT_TYPES = ['WITHDRAWAL', 'BUY', 'FEE', 'TAX'] as TransactionTypeCode[];
    const CASH_IN_TYPES = ['DEPOSIT', 'SELL', 'DIVIDEND', 'INTEREST'] as TransactionTypeCode[];
    const CHARGE_TYPES = ['FEE', 'TAX'] as TransactionTypeCode[];

    function plausibleTypes(row: FlaggedRow): ReadonlyArray<TransactionTypeCode> | undefined {
        const booked = txType(row);
        const base = booked === 'WITHDRAWAL' ? CASH_OUT_TYPES : booked === 'DEPOSIT' ? CASH_IN_TYPES : booked === 'FEE' || booked === 'TAX' ? CHARGE_TYPES : undefined;
        if (!base) return undefined;
        // The row's own type always stays selectable, or the picker would open on a value
        // it does not list and read as empty.
        const draftType = (draftFor(row).type ?? booked) as TransactionTypeCode;
        return base.includes(draftType) ? base : [...base, draftType];
    }

    /**
     * Two different questions, so two lists. "Is this withdrawal really a purchase?" needs
     * the file row and a type; "which bond was this fee charged on?" needs only an asset.
     * Mixed together the user re-reads the premise on every row.
     */
    let rowGroups = $derived(
        [
            {id: 'trades', title: 'importWizard.fixStep.groupTrades', hint: 'importWizard.fixStep.groupTradesHint', items: rows.filter(rowIsBlocking)},
            {id: 'charges', title: 'importWizard.fixStep.groupCharges', hint: 'importWizard.fixStep.groupChargesHint', items: rows.filter((r) => !rowIsBlocking(r))},
        ].filter((g) => g.items.length > 0),
    );

    function rowShellClass(row: FlaggedRow): string {
        if (row.decision === 'corrected') return 'border-emerald-300 bg-emerald-50/50 dark:border-emerald-800 dark:bg-emerald-900/10';
        if (row.decision === 'kept') return 'border-slate-300 bg-slate-50 dark:border-slate-600 dark:bg-slate-800/60';
        if (!rowIsBlocking(row)) return 'border-amber-200 bg-white dark:border-amber-800 dark:bg-slate-800';
        return 'border-red-200 bg-white dark:border-red-800 dark:bg-slate-800';
    }
</script>

<div class="space-y-4">
    <InfoBanner variant="info" message={$t('importWizard.fixStep.intro')} />

    {#if rows.length === 0}
        <div class="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300" data-testid="fix-step-empty">
            <CheckCircle size={16} />
            {$t('importWizard.fixStep.allDoneDetail', {values: {n: 0}})}
        </div>
    {:else}
        <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div class="flex flex-wrap items-center gap-3">
                {#if pendingRows.length > 0}
                    <span class="flex items-center gap-1.5 font-medium text-red-700 dark:text-red-300">
                        <AlertTriangle size={14} />
                        {$t('importWizard.fixStep.pending', {values: {n: pendingRows.length}})}
                    </span>
                {:else}
                    <span class="flex items-center gap-1.5 font-medium text-emerald-700 dark:text-emerald-300">
                        <CheckCircle size={14} />
                        {$t('importWizard.fixStep.allDone')}
                    </span>
                {/if}
                {#if settledRows.length > 0}
                    <span class="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                        <Check size={13} />
                        {$t('importWizard.fixStep.settled', {values: {n: settledRows.length}})}
                    </span>
                {/if}
            </div>
            <div class="flex flex-wrap items-center gap-2">
                {#if resettableRows.length > 0}
                    <button
                        type="button"
                        class="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-slate-600 dark:bg-slate-800 dark:text-gray-300 dark:hover:bg-slate-700"
                        onclick={resetAll}
                        title={$t('importWizard.fixStep.resetAllHint')}
                        data-testid="fix-step-reset-all"
                    >
                        <RotateCcw size={13} />
                        {$t('importWizard.fixStep.resetAll', {values: {n: resettableRows.length}})}
                    </button>
                {/if}
                {#if pendingRows.length > 0}
                    <button
                        type="button"
                        class="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-slate-600 dark:bg-slate-800 dark:text-gray-200 dark:hover:bg-slate-700"
                        onclick={onacceptall}
                        title={$t('importWizard.fixStep.acceptAllHint')}
                        data-testid="fix-step-accept-all"
                    >
                        <Hand size={13} />
                        {$t('importWizard.fixStep.acceptAll', {values: {n: pendingRows.length}})}
                    </button>
                {/if}
            </div>
        </div>

        <div class="space-y-4" data-testid="fix-step-rows">
            {#each rowGroups as group (group.id)}
                <section data-testid="fix-step-group" data-group={group.id}>
                    {#if rowGroups.length > 1}
                        <h4 class="text-sm font-semibold text-gray-800 dark:text-gray-100">{$t(group.title)}</h4>
                        <p class="mb-2 mt-0.5 text-xs text-gray-500 dark:text-gray-400">{$t(group.hint)}</p>
                    {/if}
                    <ul class="space-y-3">
                        {#each group.items as row (row.index)}
                            {@const isOpen = expanded.has(row.index)}
                            {@const draft = draftFor(row)}
                            {@const rule = getTypeRule(draft.type ?? '')}
                            {@const usesDbSearch = assetSelectValue(row) === DB_SEARCH}
                            <li class="rounded-lg border {rowShellClass(row)}" data-testid="fix-step-row" data-decision={row.decision ?? 'pending'} data-severity={rowIsBlocking(row) ? 'blocker' : 'warning'}>
                                <button type="button" class="flex w-full items-start gap-2 px-3 py-2 text-left" onclick={() => ontoggle(row.index)} data-testid="fix-step-row-toggle">
                                    {#if isOpen}
                                        <ChevronDown size={14} class="mt-0.5 shrink-0 text-gray-400" />
                                    {:else}
                                        <ChevronRight size={14} class="mt-0.5 shrink-0 text-gray-400" />
                                    {/if}
                                    {#if row.decision === 'corrected'}
                                        <Check size={14} class="mt-0.5 shrink-0 text-emerald-600" />
                                    {:else if row.decision === 'kept'}
                                        <Hand size={14} class="mt-0.5 shrink-0 text-slate-500" />
                                    {:else if rowIsBlocking(row)}
                                        <Wrench size={14} class="mt-0.5 shrink-0 text-red-500" />
                                    {:else}
                                        <AlertTriangle size={14} class="mt-0.5 shrink-0 text-amber-500" />
                                    {/if}
                                    <span class="min-w-0 flex-1">
                                        <span class="font-mono text-xs text-gray-400 dark:text-gray-500">#{row.index + 1}</span>
                                        <span class="ml-1.5 text-sm {row.decision ? 'text-gray-600 dark:text-gray-300' : rowIsBlocking(row) ? 'text-red-800 dark:text-red-300' : 'text-amber-800 dark:text-amber-300'}">{todoMessage(row.todos[0])}</span>
                                        {#if row.todos.length > 0 && !row.decision}
                                            <span class="ml-1.5 text-xs {rowIsBlocking(row) ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'}">({row.todos.map((td) => translateFieldName(td.field, $t)).join(', ')})</span>
                                        {/if}
                                    </span>
                                    {#if row.decision}
                                        <span
                                            class="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium {row.decision === 'corrected' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200' : 'bg-slate-200 text-slate-700 dark:bg-slate-600 dark:text-slate-100'}"
                                            data-testid="fix-step-row-badge"
                                        >
                                            {row.decision === 'corrected' ? $t('importWizard.fixStep.badgeCorrected') : $t('importWizard.fixStep.badgeKept')}
                                        </span>
                                    {/if}
                                </button>

                                {#if isOpen}
                                    <div class="space-y-3 border-t px-3 py-3 {row.decision ? 'border-gray-200 dark:border-slate-700' : 'border-red-100 dark:border-red-900/50'}">
                                        {#each row.todos as todo}
                                            {#each todo.evidence ?? [] as ev}
                                                <BrimEvidenceTable evidence={ev} tone={row.decision ? 'warning' : rowIsBlocking(row) ? 'blocker' : 'warning'} onGotoRow={ongotosource ? (lines) => ongotosource(row.index, lines) : undefined} />
                                            {/each}
                                        {/each}

                                        <div class="grid gap-3 {rule.quantityMode === 'forbidden' ? 'sm:grid-cols-2' : 'sm:grid-cols-3'}">
                                            <div class="flex flex-col gap-1 text-xs text-gray-600 dark:text-gray-300">
                                                <span>{$t('transactions.fields.type')}</span>
                                                <TransactionTypeSearchSelect value={(draft.type ?? 'BUY') as TransactionTypeCode} types={plausibleTypes(row)} compact testid="fix-step-type" onchange={(v) => setDraft(row.index, {type: v})} />
                                            </div>

                                            <div class="flex flex-col gap-1 text-xs text-gray-600 dark:text-gray-300">
                                                <span>{$t('transactions.fields.asset_id')}</span>
                                                <SearchSelect
                                                    value={assetSelectValue(row)}
                                                    options={assetOptionsFor(row)}
                                                    placeholder={$t('importWizard.fixStep.assetPlaceholder')}
                                                    disabled={rule.assetField === 'forbidden'}
                                                    compact
                                                    inlineSearch
                                                    testId="fix-step-asset"
                                                    onchange={(v) => onAssetOptionPicked(row, v)}
                                                >
                                                    <!-- Label only, in both slots: the default rendering prints the raw option
                                                         value (`__db__`, a placeholder id) as the main line. Whether an instrument
                                                         already matches one in your archive is deliberately not shown here — that
                                                         is decided in the asset step, further on. -->
                                                    {#snippet item(option)}
                                                        <span class="block min-w-0 truncate">{option.label}</span>
                                                    {/snippet}
                                                    {#snippet selectedItem(option)}
                                                        <span class="block min-w-0 truncate">{option.label}</span>
                                                    {/snippet}
                                                </SearchSelect>
                                                {#if usesDbSearch}
                                                    <AssetSelect
                                                        value={draft.asset_id ?? null}
                                                        compact
                                                        disabled={rule.assetField === 'forbidden'}
                                                        testid="fix-step-asset-db"
                                                        createLabel={$t('importWizard.fixStep.assetCreate')}
                                                        onCreateNew={() => oncreateasset(row.index)}
                                                        onchange={(v) => setDraft(row.index, {asset_id: v})}
                                                    />
                                                {/if}
                                            </div>

                                            <!-- A fee or a tax has no quantity at all; a greyed-out box only invites
                                                 the user to wonder what they were meant to put in it. -->
                                            {#if rule.quantityMode !== 'forbidden'}
                                                <label class="flex flex-col gap-1 text-xs text-gray-600 dark:text-gray-300">
                                                    {$t('transactions.fields.quantity')}
                                                    <input
                                                        type="text"
                                                        inputmode="decimal"
                                                        autocomplete="off"
                                                        class="rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900 dark:text-gray-100"
                                                        value={draft.quantity ?? ''}
                                                        oninput={(e) => setDraft(row.index, {quantity: (e.currentTarget as HTMLInputElement).value})}
                                                        onkeydown={(e) => {
                                                            const stepped = decimalArrowStep(e, String(draft.quantity ?? ''));
                                                            if (stepped !== null) setDraft(row.index, {quantity: stepped});
                                                        }}
                                                        onblur={(e) => setDraft(row.index, {quantity: normalizeDecimalInput((e.currentTarget as HTMLInputElement).value)})}
                                                        data-testid="fix-step-quantity"
                                                    />
                                                </label>
                                            {/if}
                                        </div>

                                        <div class="flex flex-wrap items-center justify-end gap-2">
                                            {#if rowIsResettable(row)}
                                                <button
                                                    type="button"
                                                    class="mr-auto inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-700"
                                                    onclick={() => reset(row)}
                                                    title={$t('importWizard.fixStep.resetHint')}
                                                    data-testid="fix-step-reset"
                                                >
                                                    <RotateCcw size={13} />
                                                    {$t('importWizard.fixStep.reset')}
                                                </button>
                                            {/if}
                                            <button type="button" class="rounded-lg px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-700" onclick={() => onaccept(row.index)} data-testid="fix-step-accept">
                                                {$t('importWizard.fixStep.acceptAsIs')}
                                            </button>
                                            <button type="button" class="rounded-lg bg-libre-green px-3 py-1.5 text-xs text-white hover:bg-libre-green/90 disabled:cursor-not-allowed disabled:opacity-50" disabled={!draftIsValid(row)} onclick={() => apply(row)} data-testid="fix-step-apply">
                                                {row.decision === 'corrected' ? $t('importWizard.fixStep.applyAgain') : $t('importWizard.fixStep.apply')}
                                            </button>
                                        </div>
                                        <p class="text-right text-[11px] text-gray-400 dark:text-gray-500">{$t('importWizard.fixStep.acceptAsIsHint')}</p>
                                    </div>
                                {/if}
                            </li>
                        {/each}
                    </ul>
                </section>
            {/each}
        </div>
    {/if}
</div>
