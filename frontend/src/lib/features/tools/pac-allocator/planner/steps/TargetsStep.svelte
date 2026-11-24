<script lang="ts">
    import {PieChart, Plus, Scale, Trash2} from 'lucide-svelte';
    import type {Snippet} from 'svelte';
    import {MediaQuery} from 'svelte/reactivity';
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {BulkAction, ColumnDef, FooterCellContent, RowAction} from '$lib/components/table/types';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {canonicalInput, compareDecimal, decimalSign, rebalanceControlPercentages, remainingControlPercentage, sumControlPercentages} from '$lib/utils/core/exactDecimal';
    import type {PlannerDraft, TargetRow} from '../draft.svelte';
    import {formatExactMoneyPlain, formatExactPercent, formatPlannerPercentUnits} from '../format';
    import type {PlannerPreview} from '../preview.svelte';
    import {chartPercent, exactSign} from '../result/model';
    import {formatLimitSum, limitSum, type LimitSum} from '../limitSums';
    import {BUTTON_SECONDARY, HINT, NOTICE} from '../ui';
    import AssetNameCell from '../shared/AssetNameCell.svelte';
    import CashEntryIcon from '../shared/CashEntryIcon.svelte';
    import CashEntryNameCell from '../shared/CashEntryNameCell.svelte';
    import PlannerDialog from '../shared/PlannerDialog.svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import TargetInputCell from '../shared/TargetInputCell.svelte';
    import LimitInputCell from '../shared/LimitInputCell.svelte';
    import LimitProblems from '../shared/LimitProblems.svelte';
    import TableColumns from '../shared/TableColumns.svelte';
    import {withHelpCues} from '../shared/columnHelp';
    import DistributionDialog from './DistributionDialog.svelte';
    import {STATUS_TONES} from '$lib/theme/toneClasses';
    import {domId, getPlannerProfile, storageKey, testId} from '../profile';
    import {stepTitleSlot} from '../shell/stepTitle.svelte';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();
    /** The shell's title row (TL-3 of project 67): the columns button goes there, on the right; null when mounted alone. */
    const titleSlot = stepTitleSlot();

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
        /** The scenario preview (F3a of project 67, step 9a): the total, «Now» and the limits note's figure; none before 9a's shell. */
        preview?: PlannerPreview | null;
    }

    let {draft, accountGeneration, preview = null}: Props = $props();

    // -- The preview's figures (N1: the backend's, never counted here) --------------------------------------------------
    const numbers = $derived(preview?.numbers ?? null);
    /** The total of the plan, the user's money: masked in privacy mode. */
    const totalText = $derived(numbers ? formatExactMoneyPlain(numbers.total) : null);
    const stale = $derived(preview?.stale ?? false);
    /** «Now» (U5): a Tool that works on positions shows each row's weight today. */
    const showNow = $derived(profile.positions);

    const KEY = 'tools.pacAllocator.planner.targets';
    type TotalState = 'balanced' | 'excess' | 'missing' | 'unknown';
    /** Colours of the Asset distribution editor: green at 100%, red above, amber below. */
    const BAR_CLASS: Record<TotalState, string> = STATUS_TONES.pacTargetBar;
    const TOTAL_CLASS: Record<TotalState, string> = STATUS_TONES.pacTargetTotal;

    /**
     * A row of the table: an Asset or a cash entry (F3a of project 67). The cash without an entry of its own (the backend's
     * `other_cash`) is counted by the plan, never shown here (TL-2 of project 67, the developer's testlist of 21/11).
     */
    type TableRow = TargetRow;
    const R = 'tools.portfolioRebalancer.planner.targets';

    let copying = $state(false);
    let addingCash = $state(false);
    let tableRef: DataTable<TableRow> | undefined = $state(undefined);
    /** The rows ticked in the table, as it reports them (77 SEL-D3). */
    let tickedKeys = $state<string[]>([]);

    /** A row with a target of its own: an Asset, or a cash entry where the Tool gives cash a target (`full`). */
    function targetable(row: TableRow): boolean {
        return row.kind === 'asset' || (row.kind === 'cash' && profile.cashEntries === 'full');
    }
    const rows = $derived<TableRow[]>(draft.targetRows);
    /** The rows whose targets the balancing reads and writes, in table order. */
    const editable = $derived(draft.targetRows.filter(targetable));

    const copyDisabled = $derived(!/^[A-Z]{3}$/.test(draft.data.valuationCurrency) || !draft.data.assets.some((asset) => asset.sourceAssetId !== null));
    const total = $derived(draft.targetTotal);
    const remaining = $derived(draft.targetRemaining);
    const totalState = $derived.by((): TotalState => {
        const sign = remaining === null ? null : decimalSign(remaining);
        if (sign === 0) return 'balanced';
        if (sign === -1) return 'excess';
        if (sign === 1) return 'missing';
        return 'unknown';
    });
    const excess = $derived(remaining === null ? null : remainingControlPercentage(remaining, '0'));

    // -- The summary row under the table (TL-4 of project 67, the developer's testlist of 21/11) -------------------------
    // «Metterei in fondo alla tabella una riga di summary»: the targets together, the minimums together, the maximums
    // together. The minimums turn red on the backend's verdict only (`limit_problems`), so the row and the box never
    // disagree: a PAC cash entry's trapped cash honours its minimum, and the sum may pass the total while the plan accepts it.
    const minimumSum = $derived(limitSum(draft, 'minimum', numbers?.total ?? null));
    const maximumSum = $derived(limitSum(draft, 'maximum', numbers?.total ?? null));
    const minimumsOver = $derived((numbers?.limit_problems ?? []).some((problem) => problem.code === 'allocation.bounds_min_sum_exceeds_reference'));
    /** A preview is on its way while limits are typed: the check of the minimums is coming (the sign the developer missed). */
    const checkingLimits = $derived(preview?.state === 'waiting' && (minimumSum.kind !== 'none' || maximumSum.kind !== 'none'));

    function sumLine(side: 'minimum' | 'maximum', sum: LimitSum, over: boolean): string {
        if (sum.kind === 'none') return '';
        const label = side === 'minimum' ? $t(`${KEY}.limitMinimum`, {default: 'min'}) : $t(`${KEY}.limitMaximum`, {default: 'max'});
        const figure = sum.kind === 'sum' ? formatLimitSum(sum.value, draft.data.valuationCurrency) : '—';
        const tone = over ? 'font-semibold text-lf-danger' : 'text-lf-secondary';
        return `<span class="tabular-nums ${tone}" data-testid="${testId(`targets-limits-sum-${side}`, profile)}" data-over="${over ? 'true' : 'false'}"><span class="font-normal text-lf-muted">${escapeHtml(label)}</span> ${escapeHtml(figure)}</span>`;
    }

    /**
     * The cash without an entry of its own, today (P-24, the developer's answer of 24/11): it has no row (TL-2), so «Now»
     * adds up to less than 100%, and the summary row says the rest — under «Now», or under the names while that column is
     * hidden (a phone). The backend's weight, shown as «Now» shows its own.
     */
    const otherCashText = $derived.by((): string | null => {
        if (!showNow) return null;
        const item = numbers?.items?.find((candidate) => candidate.kind === 'other_cash');
        return item && exactSign(item.weight) === 1 ? formatExactPercent(item.weight, 1) : null;
    });

    const totalClass = $derived(TOTAL_CLASS[totalState]);
    const footerCells = $derived.by((): Record<string, FooterCellContent> => {
        const otherCash =
            otherCashText === null
                ? ''
                : `<span class="block whitespace-normal text-xs font-normal ${stale ? 'text-lf-muted' : 'text-lf-secondary'}" data-testid="${testId('targets-now-other-cash', profile)}">${escapeHtml($t('tools.portfolioRebalancer.planner.targets.nowOtherCash', {values: {weight: otherCashText}}))}</span>`;
        const cells: Record<string, FooterCellContent> = {
            asset: {type: 'html', html: `<span class="font-medium text-lf-muted">${escapeHtml($t(`${KEY}.total`, {default: 'Total'}))}</span>${nowColumnHidden ? otherCash : ''}`},
            target: {type: 'html', html: `<span class="font-mono font-medium ${totalClass}" data-testid="${testId('targets-total', profile)}">${escapeHtml(total === null ? '—' : formatPlannerPercentUnits(total))}</span>`},
        };
        if (otherCash !== '' && !nowColumnHidden) cells.now = {type: 'html', html: otherCash};
        const lines = [sumLine('minimum', minimumSum, minimumsOver), sumLine('maximum', maximumSum, false)].filter((line) => line !== '');
        if (checkingLimits) lines.push(`<span class="font-normal text-lf-muted" role="status" data-testid="${testId('targets-limits-checking', profile)}">${escapeHtml($t(`${KEY}.limitsChecking`, {default: 'Checking the limits…'}))}</span>`);
        // The table's cells keep one line and cut the rest: these wrap, at a space first, inside a long figure on a phone.
        if (lines.length > 0) cells.limits = {type: 'html', html: `<div class="flex flex-col items-end gap-0.5 whitespace-normal text-right text-xs [overflow-wrap:anywhere]" data-testid="${testId('targets-limits-sum', profile)}">${lines.join('')}</div>`};
        return cells;
    });
    /**
     * The scale of the bars, in percent: the widest target, and in a Tool with «Now» the widest weight today too, so both bars
     * of a row are drawn on one scale (TL-2). Drawing only.
     */
    const maxWeight = $derived(Math.max(1, ...editable.map((row) => percentNumber(draft.data.targets[row.key])), ...(showNow ? rows.map((row) => chartPercent(nowItem(row)?.weight) ?? 0) : [])));

    function rowLabel(row: TableRow): string {
        if (row.kind === 'asset') return [row.asset.ticker, row.asset.name].filter((part) => part.trim() !== '').join(' ');
        return $t(`${R}.cashEntry`, {values: {broker: draft.broker(row.entry.brokerKey)?.name || '—', currency: row.entry.currency}});
    }

    /** Bar length only: a picture of the target, never a value that is sent. */
    function percentNumber(value: string | undefined): number {
        const canonical = canonicalInput(value ?? '');
        const number = canonical === null ? 0 : Number(canonical);
        return Number.isFinite(number) ? Math.max(0, number) : 0;
    }

    /** A bar's width, in percent of the column: its value on the bars' scale. */
    function barWidth(percent: number): string {
        return `${Math.min(100, Math.max(0, (percent / maxWeight) * 100)).toFixed(2)}%`;
    }

    /**
     * «Distribution»: the target as a bar, coloured by the total's state. In a Tool with «Now» (the Rebalancer, TL-2) two bars on
     * one scale, the grey weight today above the target, as the result's tables pair theirs; muted while the preview is stale.
     */
    function barHtml(row: TableRow): string {
        if (!targetable(row)) return '';
        const key = escapeHtml(row.key);
        const width = barWidth(percentNumber(draft.data.targets[row.key]));
        if (!showNow) {
            return `<div data-testid="${testId('target-bar', profile)}" data-asset-key="${key}" data-width="${width}" aria-hidden="true" class="h-3 overflow-hidden rounded-full bg-lf-neutral"><div class="h-full rounded-full transition-all ${escapeHtml(BAR_CLASS[totalState])}" style="width: ${width}"></div></div>`;
        }
        const today = chartPercent(nowItem(row)?.weight);
        const nowWidth = barWidth(today ?? 0);
        return (
            `<div class="flex w-full flex-col gap-1" aria-hidden="true">` +
            `<div data-testid="${testId('target-bar-now', profile)}" data-asset-key="${key}" data-width="${nowWidth}" data-known="${today === null ? 'false' : 'true'}" class="h-2 overflow-hidden rounded-full bg-lf-neutral"><div class="h-full rounded-full bg-lf-secondary transition-all${stale ? ' opacity-50' : ''}" style="width: ${nowWidth}"></div></div>` +
            `<div data-testid="${testId('target-bar', profile)}" data-asset-key="${key}" data-width="${width}" class="h-2 overflow-hidden rounded-full bg-lf-neutral"><div class="h-full rounded-full transition-all ${escapeHtml(BAR_CLASS[totalState])}" style="width: ${width}"></div></div>` +
            `</div>`
        );
    }

    /** Gives this row what is missing, or takes away the excess, within 0–100. */
    function balance(row: TableRow): void {
        if (remaining === null || !targetable(row)) return;
        const next = sumControlPercentages([canonicalInput(draft.data.targets[row.key] ?? '') ?? '0', remaining]);
        if (next === null) return;
        if ((compareDecimal(next, '0') ?? 0) < 0) draft.data.targets[row.key] = '0';
        else if ((compareDecimal(next, '100') ?? 0) > 0) draft.data.targets[row.key] = '100';
        else draft.data.targets[row.key] = next;
    }

    /** Targets in row order; an empty field counts as 0, text that is not a number stops the balancing. */
    const controlValues = $derived(editable.map((row) => ((draft.data.targets[row.key] ?? '').trim() === '' ? '0' : canonicalInput(draft.data.targets[row.key]))));
    /** The positions, among the rows the balancing reads, of the given rows (a row without a target has none). */
    function indicesOf(rows: readonly TableRow[]): number[] {
        const keys = new Set(rows.map((row) => row.key));
        return editable.flatMap((row, index) => (keys.has(row.key) ? [index] : []));
    }

    /** Rescales the chosen rows, keeping their ratios, so the total is exactly 100% (equal parts if they are all 0). */
    function rebalanced(indices: readonly number[]): string[] | null {
        if (totalState === 'balanced' || controlValues.some((value) => value === null)) return null;
        return rebalanceControlPercentages(controlValues as string[], indices);
    }

    /** Whether the rows left out of `indices` stay below 100 %, so the chosen ones have something to share. */
    function hasRoom(indices: readonly number[]): boolean {
        const chosen = new Set(indices);
        const others = sumControlPercentages(controlValues.flatMap((value, index) => (chosen.has(index) || value === null ? [] : [value])));
        return others !== null && (compareDecimal(others, '100') ?? 1) < 0;
    }

    const canBalanceAll = $derived(editable.length > 0 && rebalanced(editable.map((_, index) => index)) !== null);

    function applyBalance(indices: readonly number[]): void {
        const next = rebalanced(indices);
        if (next === null) return;
        for (const index of indices) draft.data.targets[editable[index].key] = next[index];
    }

    /**
     * The selection bar's action (77 SEL-D3): the ticked rows that have a target, with their number. At a total of 100 %
     * there is nothing to balance, so it is not offered (Q-SEL-17); it is off, saying why, when a target is not a number
     * or when the rows left out already exceed 100 % on their own, so the ticked ones have no room.
     */
    const bulkActions = $derived.by((): BulkAction<TableRow>[] => [
        {
            id: 'balance-selected',
            icon: Scale,
            label: () => $t(`${KEY}.balanceSelected`, {default: 'Balance the selected rows to 100%'}),
            appliesTo: (row) => targetable(row),
            pointless: () => totalState === 'balanced',
            blocked: (picked) => {
                if (controlValues.some((value) => value === null || decimalSign(value) === -1)) return {hint: () => $t(`${KEY}.balanceNotNumber`), reason: 'not-a-number'};
                // The rows left out at 100 % or more leave the ticked ones no room: at exactly 100 the balancing would only empty them.
                if (!hasRoom(indicesOf(picked)) || rebalanced(indicesOf(picked)) === null) return {hint: () => $t(`${KEY}.balanceNoRoom`), reason: 'no-room'};
                return null;
            },
            onClick: (picked) => {
                applyBalance(indicesOf(picked));
                tableRef?.clearSelection();
            },
        },
    ]);

    // On a phone (the table's own 768 px breakpoint) the columns are fluid down to a floor each, and the decorative bar is hidden by
    // default: asset, target, and the pinned columns have to fit a card some 300 px wide (Y-9). The bar stays one click away in «Columns».
    // With the «Limits» column (F2 of project 67) the phone also drops the selection and Action columns, as the mockup does: «Balance to
    // 100%» opens from the row's menu on a long press (`enableContextMenu`, as on the Review step, P3), «Balance all» stays in the toolbar.
    const phone = new MediaQuery('max-width: 768px');

    // -- The head's buttons (TL-3 of project 67, the developer's testlist of 21/11) --------------------------------------
    // Their explanation is the button's own tooltip, after the pointer rests on it, and its description for a screen
    // reader: no «?» beside them. When the head is too narrow they are icons only, and the tooltip carries the name too.
    /** The last pointer over the head's buttons was a finger: a tap acts at once, so no tooltip opens over the dialog. */
    let touchPointer = false;
    function notePointer(event: PointerEvent): void {
        touchPointer = event.pointerType === 'touch';
    }
    /**
     * Whether a button's tooltip may open now: never for a finger; and not for a focus the button got back without the
     * keyboard (a dialog closed with the mouse gives it back), unless the pointer rests on it.
     */
    function tipAllowed(trigger: HTMLElement): boolean {
        if (touchPointer) return false;
        const focused = trigger.contains(document.activeElement);
        return !focused || trigger.matches(':hover') || trigger.querySelector(':focus-visible') !== null;
    }
    /**
     * A button's word: hidden below this width of the head, where the three words do not fit one line. Measured on 24/11
     * (TL-3), the row with every word on one line, both Tools: EN 520 px, ES 556, IT 583, FR 600; 41 px more with the rows
     * ticked (FR 640 = 40rem). 42rem leaves a margin for the fonts of other systems.
     */
    const WORD = '@max-[42rem]:hidden';
    /** The button's word is out of view (the head's compact form): only then the name alone says something. */
    function wordHidden(trigger: HTMLElement): boolean {
        const word = trigger.querySelector('[data-word]');
        return !word || word.getClientRects().length === 0;
    }
    /** The tooltip of a button with an explanation: its name, then what it does. */
    function tipHtml(name: string, help: string): string {
        return `<strong>${escapeHtml(name)}</strong><br>${escapeHtml(help)}`;
    }
    const copyName = $derived($t(`${KEY}.copyDistribution`, {default: 'Copy current distribution'}));
    const copyHelp = $derived(
        $t(`${KEY}.copyHelp`, {
            default:
                'Reads how much each of these Assets weighs today in the Brokers you tick, counting only these Assets and not the cash, and brings the ratios to 100%. Assets entered by hand get 0. You see the weights before using them, and a target you changed is replaced only after you confirm.',
        }),
    );
    const addCashName = $derived($t(`${R}.addCash`));
    const addCashHelp = $derived(profile.text === 'rebalancer' ? $t(`${R}.addCashHelp`) : $t(`${KEY}.addCashHelp`));
    const balanceAllName = $derived($t(`${KEY}.balanceAll`, {default: 'Balance all'}));
    const COPY_HELP_ID = domId('distribution-open-help', profile);
    const ADD_CASH_HELP_ID = domId('cash-entry-add-help', profile);
    /** The percent line of the limits note: one name per Tool for the figure (TL-3), with it once the preview has it. */
    const limitsPercent = $derived.by(() => {
        const base = profile.text === 'rebalancer' ? R : KEY;
        return totalText !== null ? $t(`${base}.limitsGuide.percentTotal`, {values: {total: totalText}}) : $t(`${base}.limitsGuide.percent`);
    });

    // The columns button on the shell's title row, while this step is on screen and has a table (TL-3).
    $effect(() => {
        if (!titleSlot || draft.data.assets.length === 0) return;
        return titleSlot.hold(columnsButton);
    });

    /** The name cell: an Asset's icon and name, or a cash row's icon (M3) and name. */
    /**
     * «Now» under the name (G5-1 of project 67, mockup screen 5 on a phone): only while the «Now» column is hidden, as it is
     * by default on a phone; «Columns» brings the column back and the line goes.
     */
    const nowColumnHidden = $derived(showNow && (tableRef as DataTable<TableRow> | undefined)?.getColumnsForVisibility().find((column) => column.id === 'now')?.visible === false);

    function nowLine(row: TableRow): {text: string; key: string; stale: boolean} | null {
        if (!nowColumnHidden) return null;
        const weight = nowText(row);
        return weight === '' ? null : {text: $t('tools.portfolioRebalancer.planner.targets.nowLine', {values: {weight}}), key: row.key, stale};
    }

    function nameCell(row: TableRow) {
        const now = nowLine(row);
        if (row.kind === 'asset') return {type: 'custom' as const, component: AssetNameCell, props: {label: rowLabel(row), iconUrl: row.asset.iconUrl, assetType: row.asset.assetClass ? row.asset.assetClass.toUpperCase() : null, now}};
        return {type: 'custom' as const, component: CashEntryNameCell, props: {broker: draft.broker(row.entry.brokerKey), currency: row.entry.currency, now}};
    }

    /** A row's item in the preview: its value and weight today; none without a preview. */
    function nowItem(row: TableRow) {
        return row.kind === 'asset' ? numbers?.items?.find((candidate) => candidate.kind === 'asset' && candidate.asset_id === row.key) : numbers?.items?.find((candidate) => candidate.kind === 'cash' && candidate.broker_id === row.entry.brokerKey && candidate.currency === row.entry.currency);
    }

    /** Today's weight of a row, as the preview gives it; empty without a preview. */
    function nowText(row: TableRow): string {
        const item = nowItem(row);
        return item ? formatExactPercent(item.weight, 1) : '';
    }

    function nowHtml(row: TableRow): string {
        const text = nowText(row);
        return `<span class="font-mono ${stale ? 'text-lf-muted' : 'text-lf-secondary'}" data-testid="${testId('target-now', profile)}" data-asset-key="${escapeHtml(row.key)}">${escapeHtml(text)}</span>`;
    }

    /** A PAC cash row has limits only (F3a step 14, U8): no target, a dash in its place. */
    function noTargetHtml(): string {
        return '<span class="text-lf-muted" aria-hidden="true">—</span>';
    }

    const columns = $derived.by((): ColumnDef<TableRow>[] =>
        withHelpCues<TableRow>([
            {
                id: 'asset',
                // «Voce» in both Tools (G6): the PAC's targets list cash rows too since step 14.
                header: () => $t('tools.portfolioRebalancer.planner.targets.entry'),
                type: 'text',
                sortable: false,
                filterable: false,
                minWidth: phone.current ? 80 : 160,
                getValue: (row) => rowLabel(row),
                cell: (row) => nameCell(row),
            },
            {
                id: 'bar',
                header: () => $t(`${KEY}.shape`, {default: 'Distribution'}),
                type: 'custom',
                sortable: false,
                filterable: false,
                width: 200,
                minWidth: 100,
                hiddenByDefault: phone.current,
                cell: (row) => ({type: 'html', html: barHtml(row)}),
            },
            // «Now» right after the bars and before the target: today's weight next to the target's (TL-2).
            ...(showNow
                ? [
                      {
                          id: 'now',
                          header: () => $t('tools.portfolioRebalancer.planner.targets.now'),
                          headerTooltip: () => $t('tools.portfolioRebalancer.planner.targets.nowHelp'),
                          type: 'custom' as const,
                          sortable: false,
                          filterable: false,
                          align: 'right' as const,
                          width: 80,
                          minWidth: 64,
                          hiddenByDefault: phone.current,
                          cell: (row: TableRow) => ({type: 'html' as const, html: nowHtml(row)}),
                      },
                  ]
                : []),
            {
                id: 'target',
                header: () => $t(`${KEY}.target`, {default: 'Target %'}),
                headerTooltip: () => (profile.text === 'rebalancer' ? $t('tools.portfolioRebalancer.planner.targets.wire') : $t(`${KEY}.wire`, {default: 'The share of the cash the plan can invest that goes to this Asset, in percent. Decimals are allowed.'})),
                type: 'custom',
                sortable: false,
                filterable: false,
                align: 'right',
                width: phone.current ? 96 : 140,
                minWidth: phone.current ? 84 : 128,
                cell: (row) => (targetable(row) ? {type: 'custom', component: TargetInputCell, props: {draft, assetKey: row.key, label: rowLabel(row)}} : {type: 'html', html: noTargetHtml()}),
            },
            {
                // F2 of project 67 (M1, M17): minimum and maximum of the final value; the total a percentage refers to is named, not computed.
                id: 'limits',
                header: () => $t(`${KEY}.limits`, {default: 'Limits'}),
                headerTooltip: () =>
                    profile.text === 'rebalancer'
                        ? $t('tools.portfolioRebalancer.planner.targets.limitsHelp')
                        : $t(`${KEY}.limitsHelp`, {
                              default: "Minimum and maximum of this Asset's value at the end of the plan. Write an amount in the valuation currency (500) or a percentage of the plan's total (35%): the total is the cash the plan can invest. Empty field = no limit.",
                          }),
                type: 'custom',
                sortable: false,
                filterable: false,
                align: 'right',
                width: phone.current ? 96 : 184,
                minWidth: phone.current ? 92 : 176,
                // TL-4: an Asset's minimum alone above the base of the last preview is red at once; a cash entry's trapped cash counts too.
                cell: (row) => ({type: 'custom', component: LimitInputCell, props: {draft, assetKey: row.key, label: rowLabel(row), total: row.kind === 'asset' ? () => numbers?.total ?? null : undefined}}),
            },
        ]),
    );

    const rowActions = $derived.by((): RowAction<TableRow>[] => [
        {
            id: 'balance',
            icon: Scale,
            label: () => $t(`${KEY}.balance`, {default: 'Balance to 100%'}),
            onClick: (row) => balance(row),
            // At 100 % there is nothing to balance: not offered (77 SEL-M, Q-SEL-17). A field that is not a number counts 0 in
            // the total and here alike, so nothing blocks it.
            visible: (row) => targetable(row) && totalState !== 'balanced',
            testid: testId('target-balance', profile),
        },
        {
            id: 'remove-cash',
            icon: Trash2,
            label: () => $t(`${R}.removeCash`),
            onClick: (row) => draft.removeCashEntry(row.key),
            visible: (row) => row.kind === 'cash',
            testid: testId('cash-entry-remove', profile),
        },
    ]);

    function addCash(brokerKey: string, currency: string): void {
        draft.addCashEntry(brokerKey, currency);
        addingCash = false;
    }
</script>

<!-- The step's head (77 SEL-D3): the intro, the table's selection bar, the step's own buttons, and the preview's reason
     below them. The table draws it and hands it the bar, as the sections of SEL-D2 do; with no Asset it is drawn here with
     an empty bar. -->
{#snippet head(bar: Snippet)}
    <!-- The step keeps 12 px between its head and the table. Drawn by the table with the panel (a desktop), the head sits in
         the panel's top slot, 8 px above the rows: 4 px more. On a phone the table has no ticks and no panel: all 12. The head
         is its own container (TL-3): the buttons' words go when it is narrow, on a phone too, where there is no panel. -->
    <div class="@container {bar === noBar ? '' : phone.current ? 'pb-3' : 'pb-1'}">
        <div class="flex flex-wrap items-center gap-2">
            <p class="text-sm text-lf-secondary" data-testid={testId('targets-intro', profile)}>
                {#if profile.text === 'rebalancer'}
                    {totalText !== null ? $t('tools.portfolioRebalancer.planner.targets.introTotal', {values: {total: totalText}}) : $t('tools.portfolioRebalancer.planner.targets.intro')}
                {:else}
                    {$t(`${KEY}.intro`, {default: 'How to split among the Assets the cash the plan can invest, in percent.'})}
                {/if}
            </p>
            <div class="ml-auto flex flex-wrap items-center justify-end gap-1.5" onpointerover={notePointer} onpointerdown={notePointer} data-testid={testId('targets-buttons', profile)}>
                {@render bar()}
                {#if draft.data.assets.length > 0}
                    <Tooltip text={balanceAllName} interactiveChild openOnFocus showIf={(trigger) => wordHidden(trigger) && tipAllowed(trigger)}>
                        <button
                            type="button"
                            class={BUTTON_SECONDARY}
                            disabled={!canBalanceAll}
                            aria-label={balanceAllName}
                            data-testid={testId('targets-balance-all', profile)}
                            onclick={(event) => {
                                // The click acts; it does not pin the tooltip.
                                event.stopPropagation();
                                applyBalance(editable.map((_, index) => index));
                            }}
                        >
                            <Scale class="h-4 w-4" aria-hidden="true" />
                            <span class={WORD} data-word>{balanceAllName}</span>
                        </button>
                    </Tooltip>
                {/if}
                <Tooltip html={tipHtml(copyName, copyHelp)} maxWidth="320px" interactiveChild openOnFocus showIf={tipAllowed}>
                    <button
                        type="button"
                        class={BUTTON_SECONDARY}
                        disabled={copyDisabled}
                        aria-label={copyName}
                        aria-describedby={COPY_HELP_ID}
                        data-testid={testId('distribution-open', profile)}
                        onclick={(event) => {
                            event.stopPropagation();
                            copying = true;
                        }}
                    >
                        <PieChart class="h-4 w-4" aria-hidden="true" />
                        <span class={WORD} data-word>{copyName}</span>
                    </button>
                </Tooltip>
                <span id={COPY_HELP_ID} hidden>{copyHelp}</span>
                {#if profile.cashEntries !== 'none'}
                    <Tooltip html={tipHtml(addCashName, addCashHelp)} maxWidth="320px" interactiveChild openOnFocus showIf={tipAllowed}>
                        <button
                            type="button"
                            class={BUTTON_SECONDARY}
                            aria-label={addCashName}
                            aria-describedby={ADD_CASH_HELP_ID}
                            data-testid={testId('cash-entry-add', profile)}
                            onclick={(event) => {
                                event.stopPropagation();
                                addingCash = true;
                            }}
                        >
                            <Plus class="h-4 w-4" aria-hidden="true" />
                            <span class={WORD} data-word>{addCashName}</span>
                        </button>
                    </Tooltip>
                    <span id={ADD_CASH_HELP_ID} hidden>{addCashHelp}</span>
                {/if}
                {#if !titleSlot && draft.data.assets.length > 0}
                    {@render columnsButton()}
                {/if}
            </div>
        </div>

        {#if preview?.state === 'error' && preview.reason}
            <p class="{HINT} mt-3" role="status" data-testid={testId('targets-preview-reason', profile)} data-reason={preview.reason}>
                {preview.reason === 'incomplete' ? $t(`${KEY}.previewIncomplete`) : preview.reason === 'unavailable' ? $t(`${KEY}.previewUnavailable`) : $t(`tools.pacAllocator.planner.issues.${preview.reason}`, {default: $t(`${KEY}.previewUnavailable`)})}
            </p>
        {/if}

        {#if draft.data.assets.length > 0}
            <!-- The limits note above the table (TL-3): on a phone it is read before the rows, not after them. -->
            <div class="{NOTICE.info} mt-3" data-testid={testId('targets-limits-note', profile)}>
                <p class="font-medium">{$t(`${KEY}.limitsGuide.title`)}</p>
                <ul class="mt-1 list-disc space-y-0.5 pl-5">
                    <li>{$t(`${KEY}.limitsGuide.end`)}</li>
                    <li>{$t(`${KEY}.limitsGuide.amount`)}</li>
                    <li data-testid={testId('targets-limits-percent', profile)}>{limitsPercent}</li>
                    <li>{$t(`${KEY}.limitsGuide.empty`)}</li>
                </ul>
            </div>
        {/if}
    </div>
{/snippet}

<!-- The columns button: on the shell's title row (TL-3), or in the head when the step is mounted alone. -->
{#snippet columnsButton()}
    <TableColumns table={tableRef} testid={testId('targets-columns', profile)} />
{/snippet}

{#snippet noBar()}{/snippet}

<div class="space-y-3" data-testid={testId('targets', profile)} data-preview={preview?.state ?? 'none'} data-stale={stale ? 'true' : 'false'}>
    {#if draft.data.assets.length === 0}
        {@render head(noBar)}
        <p class={NOTICE.info} data-testid={testId('targets-empty', profile)}>{$t('tools.pacAllocator.planner.problems.noAssets', {default: 'Add at least one Asset.'})}</p>
    {:else}
        <div data-testid={testId('targets-table', profile)}>
            <DataTable
                bind:this={tableRef}
                data={rows}
                {columns}
                getRowId={(row) => row.key}
                onSelectionChange={(keys) => (tickedKeys = keys)}
                storageKey={storageKey('targets', profile)}
                enableSorting={false}
                enablePagination={false}
                enableSelection={!phone.current}
                selectionMode={phone.current ? 'none' : 'multi'}
                {bulkActions}
                selectionPanel={true}
                selectionHead={head}
                enableColumnVisibility
                enableColumnFilters={false}
                enableColumnResize
                enableContextMenu={phone.current}
                enableActions={!phone.current}
                {rowActions}
                actionsColumnWidth={phone.current ? '44px' : '64px'}
                tableLayout="auto"
                {footerCells}
            />
        </div>

        <div class="flex flex-wrap items-center justify-end gap-1.5 pt-1 text-xs font-medium" data-testid={testId('targets-control', profile)} data-balanced={totalState === 'balanced' ? 'true' : 'false'} data-state={totalState}>
            <!-- TL-4: the label and the figure moved to the table's summary row; the state and its help stay here. -->
            {#if totalState === 'balanced'}
                <span class="text-lf-success" aria-hidden="true">✅</span>
            {:else if totalState === 'excess' && excess !== null}
                <span class="text-lf-danger">⚠ {$t(`${KEY}.excess`, {default: '+{value} in excess', values: {value: formatPlannerPercentUnits(excess)}})}</span>
            {:else if totalState === 'missing' && remaining !== null}
                <span class="text-lf-warning">⚠ {$t(`${KEY}.remaining`, {default: '{value} missing', values: {value: formatPlannerPercentUnits(remaining)}})}</span>
            {/if}
            <HelpTip
                label={$t(`${KEY}.total`, {default: 'Total'})}
                help={profile.text === 'rebalancer'
                    ? $t('tools.portfolioRebalancer.planner.targets.totalHelp')
                    : $t(`${KEY}.totalHelp`, {
                          default:
                              'The targets split among the Assets the cash the plan can invest, contributions included: to calculate, they must add up to exactly 100%. «Balance all» rescales every target keeping their ratios (equal parts if they are all 0). Tick some rows to rescale only those, with «Balance the selected rows to 100%». «Balance to 100%» on a row gives that Asset what is missing, or takes away the excess.',
                      })}
                testid={testId('targets-total-help', profile)}
            />
        </div>

        <LimitProblems {draft} previewProblems={numbers?.limit_problems ?? []} total={numbers?.total ?? null} />
    {/if}
</div>

{#if copying}
    <DistributionDialog {draft} {accountGeneration} onclose={() => (copying = false)} />
{/if}
{#if addingCash}
    <PlannerDialog open title={$t(`${R}.addCash`)} testid={testId('cash-entry-dialog', profile)} onclose={() => (addingCash = false)}>
        {#if draft.cashEntryChoices.length === 0}
            <p class={NOTICE.info} data-testid={testId('cash-entry-none', profile)}>{$t(`${R}.addCashNone`)}</p>
        {:else}
            <ul class="grid gap-2 sm:grid-cols-2">
                {#each draft.cashEntryChoices as choice (choice.brokerKey + choice.currency)}
                    {@const broker = draft.broker(choice.brokerKey)}
                    <li>
                        <button type="button" class="{BUTTON_SECONDARY} w-full justify-start" data-testid={testId('cash-entry-choice', profile)} data-broker-key={choice.brokerKey} data-currency={choice.currency} onclick={() => addCash(choice.brokerKey, choice.currency)}>
                            <CashEntryIcon {broker} currency={choice.currency} size={24} />
                            <span class="min-w-0 truncate">{$t(`${R}.cashEntry`, {values: {broker: broker?.name || '—', currency: choice.currency}})}</span>
                        </button>
                    </li>
                {/each}
            </ul>
        {/if}
    </PlannerDialog>
{/if}
