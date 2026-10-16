/**
 * Pure helpers extracted from LotDataQualityBanner.svelte.
 *
 * The banner collapses the backend's one-issue-per-lot stream into one row per
 * code, each listing the affected lots as chips. The grouping, de-duplication,
 * per-day disambiguation index and severity ordering are pure functions of the
 * issues and the visible-lot date map — lifted here so they can be unit tested
 * without mounting the banner or a live i18n runtime.
 *
 * The human-facing lot label is injected as a `labelForDate` callback so this
 * module never imports i18n; the component passes a closure over `$_`. The CSS
 * class maps, the icon components and the i18n header text stay in the component.
 *
 * @module brokers/lots/lotDataQualityHelpers
 */

/** The three severities a data-quality issue can carry. */
export type IssueSeverity = 'error' | 'warning' | 'info';

/** A clickable affected-lot chip: the lot id plus its rendered label. */
export interface LotChip {
    lotId: number;
    label: string;
}

/** One issue category after grouping: its message and the lots it touches. */
export interface IssueGroup {
    code: string;
    severity: IssueSeverity;
    messageKey: string;
    messageParams: Record<string, string | number | boolean | null | undefined>;
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
 * `labelForDate(iso)` supplies the localized base label for a lot's opening date.
 */
export function buildIssueGroups(issues: readonly DataQualityIssueLike[], lotDates: ReadonlyMap<number, string>, labelForDate: (iso: string) => string): IssueGroup[] {
    const byCode = new Map<string, {code: string; severity: IssueSeverity; messageKey: string; messageParams: Record<string, string | number | boolean | null | undefined>; lotIds: number[]}>();
    for (const issue of issues) {
        let group = byCode.get(issue.code);
        if (!group) {
            group = {code: issue.code, severity: issue.severity, messageKey: issue.message_i18n_key, messageParams: issue.message_params ?? {}, lotIds: []};
            byCode.set(issue.code, group);
        }
        const lotId = resolveLotId(issue.message_params?.lot_id);
        if (Number.isFinite(lotId) && lotDates.has(lotId) && !group.lotIds.includes(lotId)) {
            group.lotIds.push(lotId);
        }
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

        result.push({code: group.code, severity: group.severity, messageKey: group.messageKey, messageParams: group.messageParams, lots});
    }

    return result.sort((left, right) => severityOrder[left.severity] - severityOrder[right.severity]);
}
