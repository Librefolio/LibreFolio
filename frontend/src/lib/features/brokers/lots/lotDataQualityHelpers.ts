/**
 * Pure helpers extracted from LotDataQualityBanner.svelte.
 *
 * The banner collapses the backend's one-issue-per-lot stream into one row per
 * code, each listing the affected lots as chips. An issue without a lot cannot
 * become a chip, so it keeps a message line of its own inside its code's row,
 * with its own amount, day or pair (J-53). The grouping, de-duplication,
 * per-day disambiguation index and severity ordering are pure functions of the
 * issues and the visible-lot date map — lifted here so they can be unit tested
 * without mounting the banner or a live i18n runtime.
 *
 * The human-facing lot label is injected as a `labelForDate` callback so this
 * module never imports i18n; the component passes a closure over `$_`. The CSS
 * class maps, the icon components and the i18n header text stay in the component.
 *
 * A FAILED analysis (J-12, N81 option A) adds two helpers: `partitionLotIssues`
 * sends the issues that broke the FIFO replay to the failure notice and keeps the
 * rest for the banner; `buildFailureRows` turns the blocking ones into the
 * notice's rows (broker name, day, the transaction to fix). The quantity
 * formatter is injected for the same reason as `labelForDate`.
 *
 * @module brokers/lots/lotDataQualityHelpers
 */

import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {resolveBrokerName} from './lotChartShared';

/** The three severities a data-quality issue can carry. */
export type IssueSeverity = 'error' | 'warning' | 'info';

/** A clickable affected-lot chip: the lot id plus its rendered label. */
export interface LotChip {
    lotId: number;
    label: string;
}

/** One message line of a group: its catalogue key and the params it is formatted with. */
export interface IssueMessage {
    /** Unique within its group and stable for the same issues: the banner's `{#each}` key. */
    key: string;
    messageKey: string;
    params: Record<string, string | number | boolean | null | undefined>;
}

/**
 * One issue category after grouping: its message lines and the lots it touches. The lines are, in first-occurrence
 * order, one for the code's issues on a lot (the first one's params; the lots are the chips) and one per distinct issue
 * without a lot (J-53). Never empty.
 */
export interface IssueGroup {
    code: string;
    severity: IssueSeverity;
    messages: IssueMessage[];
    lots: LotChip[];
}

/** The structural subset of a data-quality issue this module reads. */
interface DataQualityIssueLike {
    code: string;
    severity: IssueSeverity;
    message_i18n_key: string;
    message_params?: Record<string, string | number | boolean | null | undefined>;
}

/** Sort rank per severity; errors first, info last. Exhaustive over IssueSeverity. */
const severityOrder: Record<IssueSeverity, number> = {error: 0, warning: 1, info: 2};

/**
 * Resolve a raw `message_params.lot_id` (which the DTO types loosely) into a
 * number: a number passes through, a string is parsed, anything else is `NaN`
 * (and rejected downstream by the finiteness check).
 */
export function resolveLotId(raw: unknown): number {
    return typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw) : NaN;
}

/**
 * The banner's overall severity: error if any error group, else warning if any
 * warning group, else info. Drives the container styling and the header icon.
 */
export function groupedSeverity(errorCount: number, warningCount: number): IssueSeverity {
    if (errorCount > 0) return 'error';
    if (warningCount > 0) return 'warning';
    return 'info';
}

/**
 * Group issues by code, resolving each issue's `lot_id` into a chip against the
 * visible-lot date map. Only lots present in `lotDates` (and not already added)
 * become chips. Within a group the chips are ordered by opening date then id,
 * and lots sharing an opening day get a `#index` suffix so they are
 * distinguishable. Groups come out ordered by severity.
 *
 * The issues of a code on a lot (a finite `lot_id`, visible or not) share one message line, the first one's. An issue
 * without a lot (`lot_id` null, absent or not a number) has no chip to show where it applies, so its own params are the
 * only place its amount, day or pair is said: it gets a line of its own, and the same key with the same params gives
 * one line (J-53: an orphan income or cost pool per line, never only the first).
 *
 * `labelForDate(iso)` supplies the localized base label for a lot's opening date.
 */
export function buildIssueGroups(issues: readonly DataQualityIssueLike[], lotDates: ReadonlyMap<number, string>, labelForDate: (iso: string) => string): IssueGroup[] {
    const byCode = new Map<string, {code: string; severity: IssueSeverity; messages: IssueMessage[]; lotIds: number[]; hasLotLine: boolean; lotlessSeen: Set<string>}>();
    for (const issue of issues) {
        let group = byCode.get(issue.code);
        if (!group) {
            group = {code: issue.code, severity: issue.severity, messages: [], lotIds: [], hasLotLine: false, lotlessSeen: new Set()};
            byCode.set(issue.code, group);
        }
        const params = issue.message_params ?? {};
        const lotId = resolveLotId(params.lot_id);
        if (Number.isFinite(lotId)) {
            if (!group.hasLotLine) {
                group.hasLotLine = true;
                group.messages.push({key: `${group.code}:lots`, messageKey: issue.message_i18n_key, params});
            }
            if (lotDates.has(lotId) && !group.lotIds.includes(lotId)) group.lotIds.push(lotId);
            continue;
        }
        const identity = messageIdentity(issue.message_i18n_key, params);
        if (group.lotlessSeen.has(identity)) continue;
        group.lotlessSeen.add(identity);
        group.messages.push({key: `${group.code}:${group.messages.length}`, messageKey: issue.message_i18n_key, params});
    }

    const result: IssueGroup[] = [];
    for (const group of byCode.values()) {
        // Every id here passed `lotDates.has(lotId)` above, so the `?? ''` fallback is a
        // provably-unreachable guard (its right arm cannot execute) — kept for type-safety.
        const entries = group.lotIds.map((id) => ({id, iso: lotDates.get(id) ?? ''})).sort((left, right) => left.iso.localeCompare(right.iso) || left.id - right.id);

        const perDate = new Map<string, number>();
        for (const entry of entries) {
            perDate.set(entry.iso, (perDate.get(entry.iso) ?? 0) + 1);
        }

        const seen = new Map<string, number>();
        const lots: LotChip[] = entries.map((entry) => {
            const base = labelForDate(entry.iso);
            // perDate was just filled for every entry.iso, so `?? 1` is another unreachable guard.
            const total = perDate.get(entry.iso) ?? 1;
            const index = (seen.get(entry.iso) ?? 0) + 1;
            seen.set(entry.iso, index);
            return {lotId: entry.id, label: total > 1 ? `${base} #${index}` : base};
        });

        result.push({code: group.code, severity: group.severity, messages: group.messages, lots});
    }

    return result.sort((left, right) => severityOrder[left.severity] - severityOrder[right.severity]);
}

/** The same message key with the same params, whatever their order: two such lines would say the same thing. */
function messageIdentity(messageKey: string, params: Record<string, string | number | boolean | null | undefined>): string {
    return JSON.stringify([
        messageKey,
        Object.keys(params)
            .sort()
            .map((name) => [name, params[name] ?? null]),
    ]);
}

type IssueParams = Record<string, string | number | boolean | null | undefined>;

/**
 * Split the issues of an analysis between the failure notice and the banner.
 *
 * Only a FAILED analysis has a failure to explain. There, an issue goes to the notice when the backend flagged it
 * `fails_analysis: true` (its code is one of `_QUANTITATIVE_FAILURE_CODES`): the flag decides, so the frontend keeps no
 * copy of that list. Every other issue stays in the banner. Both lists keep the input order.
 */
export function partitionLotIssues<T extends DataQualityIssueLike>(issues: readonly T[], failed: boolean): {failure: T[]; banner: T[]} {
    const failure: T[] = [];
    const banner: T[] = [];
    for (const issue of issues) {
        if (failed && issue.message_params?.fails_analysis === true) failure.push(issue);
        else banner.push(issue);
    }
    return {failure, banner};
}

/** One row of the failure notice: what failed, where, when, and the transaction to fix. */
export interface FailureRow {
    /** `${code}:${transactionId ?? 'none'}`: one row per (code, transaction). */
    key: string;
    code: string;
    /** The row to open in the transactions page; null when the issue names none. */
    transactionId: number | null;
    /** The ISO day of that row; null when the issue does not carry a bare `YYYY-MM-DD`. */
    transactionDate: string | null;
    brokerName: string;
    messageKey: string;
    messageParams: IssueParams;
}

/** A positive safe integer, given as a number or as a string of digits; anything else is no id. */
function positiveId(raw: unknown): number | null {
    const value = typeof raw === 'number' ? raw : typeof raw === 'string' && /^\d+$/.test(raw) ? Number(raw) : Number.NaN;
    return Number.isSafeInteger(value) && value > 0 ? value : null;
}

/** A bare ISO day, as sent; anything else is no day. */
function isoDay(raw: unknown): string | null {
    return typeof raw === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : null;
}

/** Ascending, with null after every value. Days are ISO strings, so their order is the strings' order. */
function compareNullLast<T extends string | number>(left: T | null, right: T | null): number {
    if (left === right) return 0;
    if (left === null) return 1;
    if (right === null) return -1;
    return left < right ? -1 : 1;
}

/**
 * The rows of the failure notice, from the blocking issues of a FAILED analysis.
 *
 * - The transaction comes from `transaction_id` only: `related_transaction_id` may name a partner leg the user cannot
 *   see, so it is never offered.
 * - The broker is named from the panel's broker list (`resolveBrokerName`, with its defaults), not by its id: a
 *   broker the list lacks falls back to `#<id>`, and an issue without one to `—`.
 * - `missing_quantity`, a quantity of the lots, is written by `formatQuantity` (the lots' formatter, masked under
 *   privacy); the other params go to the catalogue as sent. The issues read are left unchanged.
 * - One row per (code, transaction): the first occurrence wins. Rows come by day (undated last), then transaction id
 *   (none last), then code: the replay breaks at its first wrong row.
 */
export function buildFailureRows(issues: readonly DataQualityIssueLike[], brokers: ReadonlyArray<BrokerLike>, formatQuantity: (raw: unknown) => string): FailureRow[] {
    const rows = new Map<string, FailureRow>();
    for (const issue of issues) {
        const params: IssueParams = issue.message_params ?? {};
        const transactionId = positiveId(params.transaction_id);
        const key = `${issue.code}:${transactionId ?? 'none'}`;
        if (rows.has(key)) continue;
        const messageParams: IssueParams = {...params};
        if (messageParams.missing_quantity != null) messageParams.missing_quantity = formatQuantity(messageParams.missing_quantity);
        rows.set(key, {
            key,
            code: issue.code,
            transactionId,
            transactionDate: isoDay(params.transaction_date),
            brokerName: resolveBrokerName(positiveId(params.broker_id), brokers),
            messageKey: issue.message_i18n_key,
            messageParams,
        });
    }
    return [...rows.values()].sort((left, right) => compareNullLast(left.transactionDate, right.transactionDate) || compareNullLast(left.transactionId, right.transactionId) || compareNullLast(left.code, right.code));
}
