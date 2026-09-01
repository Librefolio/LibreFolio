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
    import {AlertTriangle, Check, CheckCircle, ChevronDown, ChevronRight, Hand, Lightbulb, Plus, RotateCcw, Scissors, Wrench, X} from 'lucide-svelte';
    import ImportAssetPicker, {type PickedAsset} from './ImportAssetPicker.svelte';
    import TransactionTypeSearchSelect from '$lib/components/transactions/shared/TransactionTypeSearchSelect.svelte';
    import BrimEvidenceTable from './BrimEvidenceTable.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {getTransactionTypeIconUrl, getTypeRule, type TransactionTypeCode} from '$lib/stores/transactions/transactionTypeStore';
    import SearchSelect from '$lib/components/ui/select/SearchSelect.svelte';
    import {translateFieldName} from '$lib/utils/transactions/resolveValidationMessage';
    import {decimalArrowStep, normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {splitRowCharges, type ChargeDraft, type ChargeKind} from '$lib/utils/transactions/splitRowCharges';
    import type {BrimEvidence} from '$lib/types';

    interface FlaggedTodo {
        field: string;
        severity: 'blocker' | 'warning';
        reasonCode: string;
        message: string;
        evidence?: BrimEvidence[];
        context?: Record<string, unknown>;
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
        /** The archived asset this instrument is already bound to, if any. */
        archiveId?: number | null;
    }

    export interface FixPatch {
        type?: string;
        asset_id?: number | null;
        quantity?: string;
        /**
         * Carve the row's amount into the operation itself plus one leg per charge that
         * came with it. Every number is an absolute value in the row's own currency: the
         * wizard gives the trade the row's direction and every charge the opposite one, so
         * a split can never move money the bank did not move.
         */
        split?: {main: string; legs: {type: TransactionTypeCode; amount: string; description: string}[]};
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
        /**
         * Settle every still-pending row as "keep the plugin's reading". Scoped to the
         * given rows when asked: the panels ask three different questions, and answering
         * "the plugin was right about the fees" is not answering for the trades as well.
         */
        onacceptall: (indices?: number[]) => void;
        /**
         * The instrument is in neither list: ask the wizard to open the asset creation
         * modal, seeded with what the file says about this row and with the text the user
         * had typed while searching — that text is usually the name they want.
         */
        oncreateasset: (index: number, query: string) => void;
        /**
         * Assets created through `oncreateasset`, keyed by row index. The wizard owns the
         * creation modal, so the id comes back this way instead of through the draft.
         */
        createdAssets?: Record<number, number>;
        /** Put a row back the way the plugin read it, decision and edits discarded. */
        onreset: (index: number) => void;
        /** Same for every row already settled, optionally only within one panel. */
        onresetall: (indices?: number[]) => void;
        /**
         * The user is editing a row they had already settled. The decision has to lapse the
         * moment a field changes: a badge saying "kept as read" over a form that no longer
         * shows the plugin's reading is a claim the screen itself contradicts.
         */
        onreopen: (index: number) => void;
        /** Open the source file of a flagged row at the given 1-based line. */
        ongotosource?: (index: number, rowNumbers: number[]) => void;
    }

    let {rows, analysisAssets, expanded, ontoggle, onapply, onaccept, onacceptall, onreset, onresetall, onreopen, oncreateasset, createdAssets = {}, ongotosource}: Props = $props();

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

    /**
     * What the user answered in the asset field, keyed by row index.
     *
     * The draft alone cannot say it: `asset_id: null` is both "belongs to no instrument" — a
     * legitimate answer for a bank charge — and "not answered yet". Keeping the discriminated
     * answer here is what removes the two parallel sets this step used to need.
     */
    let assetPicks = $state<Record<number, PickedAsset>>({});

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
        const row = rows.find((r) => r.index === index)!;
        drafts = {...drafts, [index]: {...draftFor(row), ...patch}};
        if (row.decision !== null) onreopen(index);
    }

    /**
     * A fee or a tax may legitimately belong to no instrument — an account charge is the
     * bank's, not a security's. Without an explicit way to say so, "leave it empty" and
     * "I have not answered yet" look identical, and the row can never be settled.
     */
    function noneLabelFor(row: FlaggedRow): string | undefined {
        return getTypeRule(draftFor(row).type ?? '').assetField === 'required' ? undefined : $t('importWizard.fixStep.assetNone');
    }

    /**
     * Assets the user created from this step arrive as real database ids. Applied once per
     * row: re-applying would fight with any later change the user makes to the same field.
     */
    let appliedCreated = new Set<number>();
    $effect(() => {
        for (const [key, assetId] of Object.entries(createdAssets)) {
            const index = Number(key);
            if (appliedCreated.has(index)) continue;
            appliedCreated.add(index);
            const row = rows.find((r) => r.index === index);
            if (!row) continue;
            assetPicks = {...assetPicks, [index]: {kind: 'asset', id: assetId}};
            setDraft(index, {asset_id: assetId});
        }
    });

    function assetPickFor(row: FlaggedRow): PickedAsset {
        const pick = assetPicks[row.index];
        if (pick !== undefined) return pick;
        const id = draftFor(row).asset_id;
        return id == null ? null : {kind: 'asset', id};
    }

    function onAssetPicked(row: FlaggedRow, pick: PickedAsset) {
        assetPicks = {...assetPicks, [row.index]: pick};
        setDraft(row.index, {asset_id: pick?.kind === 'asset' ? pick.id : null});
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
        // Splitting is a correction in itself: it changes no field of the row, it divides
        // its amount, so it must be applicable even when everything else is untouched.
        if (splitApplies(row)) {
            const preview = splitPreview(row);
            if (preview?.touched) return preview.valid;
        }
        // Answering "no instrument" on a row flagged for its missing instrument is a real
        // correction even though it changes no field — it is the answer to the question.
        if (assetPicks[row.index]?.kind === 'none' && txAssetId(row) === null) return true;
        return type !== txType(row) || (d.asset_id ?? null) !== txAssetId(row) || String(d.quantity ?? '') !== txQuantity(row);
    }

    function apply(row: FlaggedRow) {
        const d = draftFor(row);
        const preview = splitApplies(row) ? splitPreview(row) : null;
        onapply(row.index, {
            type: d.type,
            asset_id: d.asset_id,
            quantity: normalizeDecimalInput(String(d.quantity ?? '')),
            split: preview?.valid
                ? {
                      main: preview.main,
                      legs: preview.charges.map((c) => ({type: chargeTxType(c.kind), amount: c.amount, description: splitLegDescription(row, c.kind)})),
                  }
                : undefined,
        });
        drafts = Object.fromEntries(Object.entries(drafts).filter(([k]) => Number(k) !== row.index));
    }

    function clearLocalState(index: number) {
        drafts = Object.fromEntries(Object.entries(drafts).filter(([k]) => Number(k) !== index));
        splitDrafts = Object.fromEntries(Object.entries(splitDrafts).filter(([k]) => Number(k) !== index));
        assetPicks = Object.fromEntries(Object.entries(assetPicks).filter(([k]) => Number(k) !== index));
        appliedCreated.delete(index);
    }

    function reset(row: FlaggedRow) {
        clearLocalState(row.index);
        onreset(row.index);
    }

    /**
     * "Keep as read" is a statement about the plugin's reading, so it has to discard the edits
     * the user was drafting — otherwise the row settles under a label the open form denies, and
     * the draft comes back the next time it is expanded.
     */
    function accept(row: FlaggedRow) {
        clearLocalState(row.index);
        onaccept(row.index);
    }

    function resetAll(scope?: FlaggedRow[]) {
        const target = scope ?? resettableRows;
        for (const row of target) clearLocalState(row.index);
        onresetall(scope ? target.map((r) => r.index) : undefined);
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

    // =========================================================================
    //  Splitting one row into a trade plus its charges
    // =========================================================================

    /**
     * A statement line is one number for something that happened in several pieces: on a
     * purchase the debit bundles price, accrued interest and commissions; on a sale the
     * credit is already net of what was withheld. The file separates none of it, so the
     * user names the pieces they can read off their contract note and the trade leg is
     * whatever is left.
     */
    let splitDrafts = $state<Record<number, ChargeDraft[]>>({});

    /** The kinds offered, in the order a contract note usually lists them. */
    const CHARGE_KINDS: ChargeKind[] = ['fee', 'tax', 'accrued'];

    /**
     * Accrued interest is a cost, but not a cost *of the security*: it is repaid by the
     * first gross coupon, so folding it into the price would overstate the cost basis for
     * good. `FEE` is the only type that both leaves the FIFO lots alone and still counts
     * against the position — and `INTEREST` is not an option anyway, since it requires
     * money coming in and here it went out.
     */
    function chargeTxType(kind: ChargeKind): TransactionTypeCode {
        return (kind === 'tax' ? 'TAX' : 'FEE') as TransactionTypeCode;
    }

    function splitTodo(row: FlaggedRow): FlaggedTodo | undefined {
        return row.todos.find((td) => (td.context as {split_hint?: string} | undefined)?.split_hint !== undefined);
    }

    /**
     * Only a trade has a price to separate from its charges. A dividend or a coupon is the
     * whole amount by definition, and a row the user has not typed yet has nothing to split
     * either — so the zone appears the moment the row becomes a purchase or a sale, whether
     * the plugin read it that way or the user just said so.
     */
    function splitApplies(row: FlaggedRow): boolean {
        if (splitTodo(row) === undefined) return false;
        const type = (draftFor(row).type ?? txType(row) ?? '') as string;
        return type === 'BUY' || type === 'SELL';
    }

    function splitLines(row: FlaggedRow): ChargeDraft[] {
        return splitDrafts[row.index] ?? [{kind: 'fee', amount: ''}];
    }

    function setSplitLines(row: FlaggedRow, lines: ChargeDraft[]) {
        splitDrafts = {...splitDrafts, [row.index]: lines};
        if (row.decision !== null) onreopen(row.index);
    }

    function updateSplitLine(row: FlaggedRow, at: number, patch: Partial<ChargeDraft>) {
        setSplitLines(
            row,
            splitLines(row).map((line, k) => (k === at ? {...line, ...patch} : line)),
        );
    }

    function addSplitLine(row: FlaggedRow) {
        const lines = splitLines(row);
        if (lines.length >= CHARGE_KINDS.length) return;
        const used = new Set(lines.map((l) => l.kind));
        setSplitLines(row, [...lines, {kind: CHARGE_KINDS.find((k) => !used.has(k)) ?? 'fee', amount: ''}]);
    }

    /**
     * The kinds still on offer for one line: the ones nobody has taken, plus its own. A
     * charge listed twice would be two answers to the same question, and the second would
     * silently overwrite nothing — it would just add up.
     */
    function kindOptions(row: FlaggedRow, current: ChargeKind) {
        const taken = new Set(splitLines(row).map((l) => l.kind));
        return CHARGE_KINDS.filter((k) => k === current || !taken.has(k)).map((k) => ({
            value: k,
            label: $t(`importWizard.fixStep.splitKind.${k}`),
            searchText: `${k} ${$t(`importWizard.fixStep.splitKind.${k}`)}`,
            icon: getTransactionTypeIconUrl(chargeTxType(k)),
        }));
    }

    function removeSplitLine(row: FlaggedRow, at: number) {
        const lines = splitLines(row).filter((_, k) => k !== at);
        setSplitLines(row, lines.length > 0 ? lines : [{kind: 'fee', amount: ''}]);
    }

    function rowCash(row: FlaggedRow): {amount: number; code: string} | null {
        const cash = row.tx.cash as {amount?: string | number; code?: string} | null | undefined;
        if (!cash || cash.amount === undefined) return null;
        const amount = Number(cash.amount);
        if (!Number.isFinite(amount)) return null;
        return {amount, code: String(cash.code ?? '')};
    }

    function splitPreview(row: FlaggedRow) {
        const cash = rowCash(row);
        if (!cash) return null;
        const split = splitRowCharges(String(cash.amount), cash.amount < 0 ? 'out' : 'in', splitLines(row));
        return split && {...split, code: cash.code, outgoing: cash.amount < 0};
    }

    function splitLegDescription(row: FlaggedRow, kind: ChargeKind): string {
        const base = typeof row.tx.description === 'string' ? row.tx.description : '';
        const suffix = $t(`importWizard.fixStep.splitKind.${kind}`);
        return `${base ? `${base} — ` : ''}${suffix}`.slice(0, 500);
    }

    /**
     * Compact money for a panel that shows several amounts at once: the shared formatter
     * appends flag and ISO code, which at this density reads as noise around the digits.
     * The currency is stated once, by the row itself.
     */
    function money(amount: string, code: string, negative: boolean): string {
        const n = Number(amount);
        if (!Number.isFinite(n)) return '—';
        const decimals = Math.min(8, Math.max(2, amount.split('.')[1]?.length ?? 0));
        const text = Math.abs(n).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: decimals});
        const symbol = getCurrencyInfo(code)?.symbol || code;
        return `${negative ? '−' : ''}${text} ${symbol}`;
    }

    /**
     * The comparison the plugin measured, when it made one. Withheld on a sale: the
     * proceeds have no reason to resemble the face value, and putting the two side by side
     * would invite the user to read a gap that means nothing.
     */
    function splitFacts(row: FlaggedRow): {nominal: string; nominalRow: number | null} | null {
        const ctx = splitTodo(row)?.context;
        if (ctx?.compare_nominal !== true) return null;
        const nominal = ctx?.nominale;
        if (typeof nominal !== 'string' && typeof nominal !== 'number') return null;
        const rowNum = ctx?.nominale_row;
        return {nominal: String(nominal), nominalRow: typeof rowNum === 'number' ? rowNum : null};
    }

    /** What the plugin could learn about this row from the rest of the file. */
    function splitHints(row: FlaggedRow): string[] {
        const hints = splitTodo(row)?.context?.split_suggestions;
        return Array.isArray(hints) ? hints.filter((h): h is string => typeof h === 'string') : [];
    }

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
     * One colour per question. Painting all three amber was the same as not grouping them:
     * the eye reads the tint before it reads the heading, so a uniform tint says "one pile"
     * however many headings sit in it.
     */
    const GROUP_TONE: Record<string, {section: string; heading: string; row: string}> = {
        trades: {
            section: 'border-rose-200 bg-rose-50/50 dark:border-rose-900/60 dark:bg-rose-950/20',
            heading: 'text-rose-900 dark:text-rose-200',
            row: 'border-rose-200 bg-white dark:border-rose-900/70 dark:bg-slate-800',
        },
        splits: {
            section: 'border-amber-200 bg-amber-50/50 dark:border-amber-900/60 dark:bg-amber-950/20',
            heading: 'text-amber-900 dark:text-amber-200',
            row: 'border-amber-200 bg-white dark:border-amber-900/70 dark:bg-slate-800',
        },
        charges: {
            section: 'border-sky-200 bg-sky-50/50 dark:border-sky-900/60 dark:bg-sky-950/20',
            heading: 'text-sky-900 dark:text-sky-200',
            row: 'border-sky-200 bg-white dark:border-sky-900/70 dark:bg-slate-800',
        },
    };

    /** Panels the user has folded away. Open by default: a fold hiding pending work is a trap. */
    let collapsedGroups = $state<Set<string>>(new Set());

    function toggleGroup(id: string) {
        const next = new Set(collapsedGroups);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        collapsedGroups = next;
    }

    /**
     * Three different questions, so three panels. "Is this withdrawal really a purchase?"
     * needs the file row and a type; "what is inside this amount?" needs the contract note;
     * "which bond was this fee charged on?" needs only an asset. Mixed together the user
     * re-reads the premise on every row.
     */
    let rowGroups = $derived(
        [
            {id: 'trades', title: 'importWizard.fixStep.groupTrades', hint: 'importWizard.fixStep.groupTradesHint', items: rows.filter(rowIsBlocking)},
            {id: 'splits', title: 'importWizard.fixStep.groupSplits', hint: 'importWizard.fixStep.groupSplitsHint', items: rows.filter((r) => !rowIsBlocking(r) && splitTodo(r) !== undefined)},
            {id: 'charges', title: 'importWizard.fixStep.groupCharges', hint: 'importWizard.fixStep.groupChargesHint', items: rows.filter((r) => !rowIsBlocking(r) && splitTodo(r) === undefined)},
        ].filter((g) => g.items.length > 0),
    );

    function rowShellClass(row: FlaggedRow, groupId: string): string {
        if (row.decision === 'corrected') return 'border-emerald-300 bg-emerald-50/50 dark:border-emerald-800 dark:bg-emerald-900/10';
        if (row.decision === 'kept') return 'border-slate-300 bg-slate-50 dark:border-slate-600 dark:bg-slate-800/60';
        return GROUP_TONE[groupId]?.row ?? 'border-amber-200 bg-white dark:border-amber-800 dark:bg-slate-800';
    }
</script>

<div class="space-y-4">
    <InfoBanner variant="info" message={$t('importWizard.fixStep.intro')} />

    <InfoBanner variant="warning">
        {$t('importWizard.fixStep.reportIssueHint')}
        <a href="https://github.com/Librefolio/LibreFolio/issues/new" target="_blank" rel="noopener noreferrer" class="font-medium underline underline-offset-2 hover:opacity-80" data-testid="fix-step-report-issue-link">{$t('importWizard.fixStep.reportIssueLink')}</a>
    </InfoBanner>

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
                        onclick={() => resetAll()}
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
                        onclick={() => onacceptall()}
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
                {@const tone = GROUP_TONE[group.id]}
                {@const folded = collapsedGroups.has(group.id)}
                {@const groupPending = group.items.filter((r) => r.decision === null)}
                {@const groupSettled = group.items.filter((r) => r.decision !== null)}
                <section class="rounded-xl border {tone.section} px-3 py-2.5" data-testid="fix-step-group" data-group={group.id}>
                    <div class="flex flex-wrap items-start justify-between gap-2">
                        <button type="button" class="flex min-w-0 flex-1 items-start gap-1.5 text-left" onclick={() => toggleGroup(group.id)} data-testid="fix-step-group-toggle">
                            {#if folded}
                                <ChevronRight size={15} class="mt-0.5 shrink-0 {tone.heading}" />
                            {:else}
                                <ChevronDown size={15} class="mt-0.5 shrink-0 {tone.heading}" />
                            {/if}
                            <span class="min-w-0">
                                <span class="text-sm font-semibold {tone.heading}">{$t(group.title)}</span>
                                <span class="ml-1.5 rounded-full bg-white/70 px-1.5 py-0.5 text-[11px] font-medium {tone.heading} dark:bg-slate-900/50">{group.items.length}</span>
                                <span class="mt-0.5 block text-xs text-gray-600 dark:text-gray-300">{$t(group.hint)}</span>
                            </span>
                        </button>
                        <!-- The same two verbs as the toolbar, scoped to this panel: with three
                             questions on screen, "keep all" without a subject is a decision the
                             user cannot check before making it. -->
                        <div class="flex shrink-0 flex-wrap items-center gap-1.5">
                            {#if groupSettled.length > 0}
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white/80 px-2 py-1 text-[11px] font-medium text-gray-600 hover:bg-white dark:border-slate-600 dark:bg-slate-800/70 dark:text-gray-300 dark:hover:bg-slate-700"
                                    onclick={() => resetAll(groupSettled)}
                                    title={$t('importWizard.fixStep.resetAllHint')}
                                    data-testid="fix-step-group-reset-all"
                                >
                                    <RotateCcw size={12} />
                                    {$t('importWizard.fixStep.resetAll', {values: {n: groupSettled.length}})}
                                </button>
                            {/if}
                            {#if groupPending.length > 0}
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white/80 px-2 py-1 text-[11px] font-medium text-gray-700 hover:bg-white dark:border-slate-600 dark:bg-slate-800/70 dark:text-gray-200 dark:hover:bg-slate-700"
                                    onclick={() => onacceptall(groupPending.map((r) => r.index))}
                                    title={$t('importWizard.fixStep.acceptAllHint')}
                                    data-testid="fix-step-group-accept-all"
                                >
                                    <Hand size={12} />
                                    {$t('importWizard.fixStep.acceptAll', {values: {n: groupPending.length}})}
                                </button>
                            {/if}
                        </div>
                    </div>
                    <ul class="mt-2.5 space-y-3" class:hidden={folded}>
                        {#each group.items as row (row.index)}
                            {@const isOpen = expanded.has(row.index)}
                            {@const draft = draftFor(row)}
                            {@const rule = getTypeRule(draft.type ?? '')}
                            <li class="rounded-lg border {rowShellClass(row, group.id)}" data-testid="fix-step-row" data-decision={row.decision ?? 'pending'} data-severity={rowIsBlocking(row) ? 'blocker' : 'warning'}>
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

                                        <!-- One amount, several events inside it. The plugin will not guess the
                                             breakdown, but the user has it on their contract note: they name the
                                             charges they can read and the trade leg is the remainder, so the legs
                                             always add back up to what the bank moved. -->
                                        {#if splitApplies(row)}
                                            {@const preview = splitPreview(row)}
                                            {@const facts = splitFacts(row)}
                                            {@const hints = splitHints(row)}
                                            {@const lines = splitLines(row)}
                                            {@const negative = (rowCash(row)?.amount ?? 0) < 0}
                                            {#if preview}
                                                <div class="rounded-lg border border-amber-300 bg-white px-3 py-2.5 dark:border-amber-700 dark:bg-slate-900/60" data-testid="fix-step-split">
                                                    <p class="flex items-center gap-1.5 text-xs font-semibold text-amber-900 dark:text-amber-200">
                                                        <Scissors size={13} />
                                                        {$t('importWizard.fixStep.splitTitle')}
                                                    </p>

                                                    <!-- The two numbers the question is about, side by side. The prose
                                                         above says the same thing, and prose is what the user skims:
                                                         seeing 46.603,73 against 50.000,00 is what makes the gap
                                                         obvious, and where the second number came from is half the
                                                         answer to "how do you know". -->
                                                    <dl class="mt-1.5 flex flex-wrap gap-x-6 gap-y-1 text-[11px]">
                                                        <div>
                                                            <dt class="text-gray-500 dark:text-gray-400">{$t('importWizard.fixStep.splitRowAmountLabel')}</dt>
                                                            <dd class="font-mono text-sm text-gray-800 dark:text-gray-100">{money(preview.total, preview.code, negative)}</dd>
                                                        </div>
                                                        {#if facts}
                                                            <div>
                                                                <dt class="text-gray-500 dark:text-gray-400">
                                                                    {$t('importWizard.fixStep.splitNominalLabel')}
                                                                    {#if facts.nominalRow !== null}
                                                                        {#if ongotosource}
                                                                            <button
                                                                                type="button"
                                                                                class="underline decoration-dotted underline-offset-2 hover:text-amber-700 dark:hover:text-amber-300"
                                                                                onclick={() => ongotosource(row.index, [facts.nominalRow as number])}
                                                                                data-testid="fix-step-split-nominal-source"
                                                                            >
                                                                                {$t('importWizard.fixStep.splitNominalSource', {values: {row: facts.nominalRow}})}
                                                                            </button>
                                                                        {:else}
                                                                            <span>{$t('importWizard.fixStep.splitNominalSource', {values: {row: facts.nominalRow}})}</span>
                                                                        {/if}
                                                                    {/if}
                                                                </dt>
                                                                <dd class="font-mono text-sm text-gray-800 dark:text-gray-100">{money(facts.nominal, preview.code, false)}</dd>
                                                            </div>
                                                        {/if}
                                                    </dl>
                                                    {#if facts}
                                                        <p class="mt-1 text-[11px] text-gray-500 dark:text-gray-400">{$t('importWizard.fixStep.splitNominalHint')}</p>
                                                    {/if}

                                                    <!-- What the rest of the file says about this row. The user is being
                                                         asked for numbers they have to go and find; these narrow down
                                                         which ones, and one of them prevents a real mistake — a charge
                                                         the file already books on its own must not be extracted twice. -->
                                                    {#if hints.length > 0}
                                                        <ul class="mt-2 space-y-1 border-t border-amber-200/70 pt-2 text-[11px] text-gray-600 dark:border-amber-800/70 dark:text-gray-300" data-testid="fix-step-split-hints">
                                                            {#each hints as hint}
                                                                <li class="flex items-start gap-1.5">
                                                                    <Lightbulb size={12} class="mt-0.5 shrink-0 text-amber-500" />
                                                                    <span>{hint}</span>
                                                                </li>
                                                            {/each}
                                                        </ul>
                                                    {/if}

                                                    <div class="mt-2 border-t border-amber-200/70 pt-2 dark:border-amber-800/70">
                                                        <p class="text-[11px] font-medium text-gray-600 dark:text-gray-300">{$t('importWizard.fixStep.splitLegsLabel')}</p>
                                                        <p class="text-[11px] text-gray-500 dark:text-gray-400">{$t('importWizard.fixStep.splitLegsHint')}</p>
                                                        <div class="mt-1.5 space-y-1.5">
                                                            {#each lines as line, k}
                                                                <div class="flex items-center gap-2" data-testid="fix-step-split-line">
                                                                    <!-- The icon is the transaction that will be created, the label the
                                                                         nature the user recognises: accrued interest books as a fee, so it
                                                                         wears the fee's icon and its own name. -->
                                                                    <div class="w-44 shrink-0" data-testid="fix-step-split-kind">
                                                                        <SearchSelect value={line.kind} options={kindOptions(row, line.kind)} compact onchange={(v) => updateSplitLine(row, k, {kind: v as ChargeKind})}>
                                                                            {#snippet selectedItem(option)}
                                                                                <div class="flex min-w-0 items-center gap-2">
                                                                                    <img src={option.icon} alt="" class="h-4 w-4 shrink-0 object-contain" />
                                                                                    <span class="truncate text-sm text-gray-900 dark:text-gray-100">{option.label}</span>
                                                                                </div>
                                                                            {/snippet}
                                                                            {#snippet item(option)}
                                                                                <div class="flex min-w-0 items-center gap-2">
                                                                                    <img src={option.icon} alt="" class="h-4 w-4 shrink-0 object-contain" />
                                                                                    <span class="truncate text-sm">{option.label}</span>
                                                                                </div>
                                                                            {/snippet}
                                                                        </SearchSelect>
                                                                    </div>
                                                                    <input
                                                                        type="text"
                                                                        inputmode="decimal"
                                                                        autocomplete="off"
                                                                        class="w-32 rounded-lg border bg-white px-2 py-1.5 text-sm dark:bg-slate-900 dark:text-gray-100 {preview.touched && !preview.valid ? 'border-red-400 dark:border-red-500' : 'border-gray-300 dark:border-slate-600'}"
                                                                        placeholder="0,00"
                                                                        value={line.amount}
                                                                        oninput={(e) => updateSplitLine(row, k, {amount: (e.currentTarget as HTMLInputElement).value})}
                                                                        onkeydown={(e) => {
                                                                            const stepped = decimalArrowStep(e, line.amount);
                                                                            if (stepped !== null) updateSplitLine(row, k, {amount: stepped});
                                                                        }}
                                                                        onblur={(e) => updateSplitLine(row, k, {amount: normalizeDecimalInput((e.currentTarget as HTMLInputElement).value)})}
                                                                        data-testid="fix-step-split-amount"
                                                                    />
                                                                    {#if lines.length > 1}
                                                                        <button
                                                                            type="button"
                                                                            class="rounded-md p-1 text-gray-400 hover:bg-amber-100 hover:text-gray-700 dark:hover:bg-amber-900/30 dark:hover:text-gray-200"
                                                                            title={$t('importWizard.fixStep.splitRemoveLine')}
                                                                            onclick={() => removeSplitLine(row, k)}
                                                                            data-testid="fix-step-split-remove"
                                                                        >
                                                                            <X size={13} />
                                                                        </button>
                                                                    {/if}
                                                                </div>
                                                            {/each}
                                                        </div>
                                                        {#if lines.length < CHARGE_KINDS.length}
                                                            <button type="button" class="mt-1.5 flex items-center gap-1 text-[11px] font-medium text-amber-800 hover:underline dark:text-amber-300" onclick={() => addSplitLine(row)} data-testid="fix-step-split-add">
                                                                <Plus size={12} />
                                                                {$t('importWizard.fixStep.splitAddLine')}
                                                            </button>
                                                        {/if}
                                                    </div>

                                                    {#if preview.valid}
                                                        <dl class="mt-2 space-y-0.5 border-t border-amber-200/70 pt-2 text-xs dark:border-amber-800/70" data-testid="fix-step-split-preview">
                                                            <div class="flex items-center justify-between gap-3">
                                                                <dt class="flex min-w-0 items-center gap-1.5 text-gray-600 dark:text-gray-300">
                                                                    <img src={getTransactionTypeIconUrl((draft.type ?? txType(row) ?? 'BUY') as TransactionTypeCode)} alt="" class="h-4 w-4 shrink-0 object-contain" />
                                                                    {$t(`transactions.types.${draft.type ?? txType(row)}`)}
                                                                </dt>
                                                                <dd class="font-mono text-gray-800 dark:text-gray-100" data-testid="fix-step-split-main">{money(preview.main, preview.code, negative)}</dd>
                                                            </div>
                                                            {#each preview.charges as charge}
                                                                <div class="flex items-center justify-between gap-3">
                                                                    <dt class="flex min-w-0 items-center gap-1.5 text-gray-600 dark:text-gray-300">
                                                                        <img src={getTransactionTypeIconUrl(chargeTxType(charge.kind))} alt="" class="h-4 w-4 shrink-0 object-contain" />
                                                                        {$t(`importWizard.fixStep.splitKind.${charge.kind}`)} · {$t(`transactions.types.${chargeTxType(charge.kind)}`)}
                                                                    </dt>
                                                                    <dd class="font-mono text-gray-800 dark:text-gray-100" data-testid="fix-step-split-charge">{money(charge.amount, preview.code, true)}</dd>
                                                                </div>
                                                            {/each}
                                                            <div class="flex items-center justify-between gap-3 border-t border-amber-200 pt-0.5 text-emerald-700 dark:border-amber-800 dark:text-emerald-300">
                                                                <dt class="flex items-center gap-1"><Check size={12} />{$t('importWizard.fixStep.splitTotalLabel')}</dt>
                                                                <dd class="font-mono">{money(preview.total, preview.code, negative)}</dd>
                                                            </div>
                                                        </dl>
                                                    {:else if preview.touched}
                                                        <p class="mt-2 text-xs text-red-600 dark:text-red-400" data-testid="fix-step-split-error">
                                                            {preview.error === 'exceeds' ? $t('importWizard.fixStep.splitErrorExceeds', {values: {total: money(preview.total, preview.code, false)}}) : $t('importWizard.fixStep.splitErrorNonpositive')}
                                                        </p>
                                                    {/if}
                                                </div>
                                            {/if}
                                        {/if}

                                        <div class="grid gap-3 {rule.quantityMode === 'forbidden' ? 'sm:grid-cols-2' : 'sm:grid-cols-3'}">
                                            <div class="flex flex-col gap-1 text-xs text-gray-600 dark:text-gray-300">
                                                <span>{$t('transactions.fields.type')}</span>
                                                <TransactionTypeSearchSelect value={(draft.type ?? 'BUY') as TransactionTypeCode} types={plausibleTypes(row)} compact testid="fix-step-type" onchange={(v) => setDraft(row.index, {type: v})} />
                                            </div>

                                            <div class="flex flex-col gap-1 text-xs text-gray-600 dark:text-gray-300">
                                                <span>{$t('transactions.fields.asset_id')}</span>
                                                <ImportAssetPicker
                                                    value={assetPickFor(row)}
                                                    importAssets={analysisAssets}
                                                    noneLabel={noneLabelFor(row)}
                                                    placeholder={$t('importWizard.fixStep.assetPlaceholder')}
                                                    disabled={rule.assetField === 'forbidden'}
                                                    compact
                                                    testid="fix-step-asset"
                                                    onchange={(v) => onAssetPicked(row, v)}
                                                    oncreate={(query) => oncreateasset(row.index, query)}
                                                />
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
                                            <button type="button" class="rounded-lg px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-700" onclick={() => accept(row)} data-testid="fix-step-accept">
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
