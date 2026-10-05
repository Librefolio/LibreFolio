import type {z} from 'zod';

import {schemas} from '$lib/api';
import {riskMetadata, singleValue} from '$lib/risk/riskTypes';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import type {RiskResultWarning} from '../warningSentence';

/**
 * Pure reading of the L4 payloads.
 *
 * Everything here is a *read*: nothing fetches, nothing holds state, nothing
 * renders. The three rungs of L4 differ in what they ask the server, but they
 * all have to answer the same two questions about what came back — "what does
 * it say" and "what can the reader do about it" — and those answers are worth
 * testing without a browser.
 */

type RiskErrorShape = z.infer<typeof schemas.RiskError>;

type ScenarioCatalog = {items?: unknown[]; geography_groups?: {id: string}[] | null} | null | undefined;

export interface ScenarioOption {
    value: string;
    label: string;
    /** Defaults the preset carries, already flattened to scalars. */
    start?: string;
    end?: string;
}

/** One bar of the tornado: a label, a signed return, and the money it costs. */
export interface TornadoRow {
    key: string;
    /** Asset id when the row is an asset, so the caller can name it. */
    assetId?: number;
    /** Bucket id when the row is a configured bucket. */
    bucketId?: string;
    /** Signed fraction: negative is a loss. */
    value: number;
    /** Signed amount in the scope currency, when the payload carried one. */
    amount: number | null;
    /** How much of the scope this row speaks for, when known. */
    weight: number | null;
}

function localized(value: unknown, language: string): string {
    if (typeof value === 'string') return value;
    if (!value || typeof value !== 'object') return '';
    const map = value as Record<string, unknown>;
    const candidate = map[language] ?? map[language.split('-')[0]] ?? map.en ?? Object.values(map)[0];
    return typeof candidate === 'string' ? candidate : '';
}

function scalar(value: unknown): string | undefined {
    if (typeof value === 'string') return value;
    if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
    return undefined;
}

/**
 * Presets of one kind, as options.
 *
 * Parsed with `safeParse` per entry rather than for the catalogue as a whole:
 * the catalogue holds both kinds in one list, so a strict parse of the list
 * would reject every scenario because of the ones that are simply not this kind.
 */
export function replayOptions(catalog: ScenarioCatalog, language: string): ScenarioOption[] {
    return (catalog?.items ?? []).flatMap((entry) => {
        const parsed = schemas.RiskHistoricalReplayScenario.safeParse((entry as {scenario?: unknown})?.scenario);
        if (!parsed.success) return [];
        const scenario = parsed.data;
        return [
            {
                value: scenario.id,
                label: localized(scenario.name, language) || scenario.id,
                start: scalar(scenario.defaults?.start),
                end: scalar(scenario.defaults?.end),
            },
        ];
    });
}

export function shockOptions(catalog: ScenarioCatalog, language: string): ScenarioOption[] {
    return (catalog?.items ?? []).flatMap((entry) => {
        const parsed = schemas.RiskHypotheticalShockScenario.safeParse((entry as {scenario?: unknown})?.scenario);
        if (!parsed.success) return [];
        return [{value: parsed.data.id, label: localized(parsed.data.name, language) || parsed.data.id}];
    });
}

/** The defaults behind a preset id: the dimension it shocks, and by how much. */
export function shockScenario(catalog: ScenarioCatalog, id: string): {dimension: string; bucketShocks: Record<string, number>} | null {
    for (const entry of catalog?.items ?? []) {
        const parsed = schemas.RiskHypotheticalShockScenario.safeParse((entry as {scenario?: unknown})?.scenario);
        if (!parsed.success || parsed.data.id !== id) continue;
        const shocks: Record<string, number> = {};
        for (const [bucket, value] of Object.entries(parsed.data.defaults?.bucket_shocks ?? {})) {
            const numeric = typeof value === 'number' ? value : Number(value);
            if (Number.isFinite(numeric)) shocks[bucket] = numeric;
        }
        return {dimension: String(parsed.data.defaults?.dimension ?? 'asset_class'), bucketShocks: shocks};
    }
    return null;
}

function toNumber(value: unknown): number | null {
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    if (typeof value === 'string' && value.trim() !== '') {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
}

/**
 * The bars of the tornado, worst first.
 *
 * Prefers the **configured buckets** when the scenario had a dimension, because
 * that is the shape of the question the reader asked ("what if equities fall
 * 20%"), and falls back to per-asset impacts for a replay, where there is no
 * dimension and every holding simply lived through the period.
 *
 * Ordering is signed and not by magnitude: a tornado sorted on `Math.abs` would
 * interleave gains among losses and destroy the one property the shape exists
 * for, which is that the eye travels down the damage.
 */
export function tornadoRows(output: unknown): TornadoRow[] {
    if (!output || typeof output !== 'object') return [];
    const stress = output as {impacts?: unknown[]; configured_buckets?: unknown[]; dimension?: unknown};
    const buckets = Array.isArray(stress.configured_buckets) ? stress.configured_buckets : [];
    const rows: TornadoRow[] = [];

    if (stress.dimension && buckets.length > 0) {
        for (const raw of buckets) {
            const bucket = raw as Record<string, unknown>;
            const bucketId = typeof bucket.bucket_id === 'string' ? bucket.bucket_id : '';
            if (!bucketId) continue;
            // The contribution is what this bucket did to the portfolio; the bare
            // shock is what the reader typed. Showing the second as if it were the
            // first would make a 1%-weight bucket look as damaging as a 60% one.
            const value = toNumber(bucket.contribution_return);
            if (value === null) continue;
            rows.push({key: `bucket:${bucketId}`, bucketId, value, amount: null, weight: toNumber(bucket.asset_exposure_total)});
        }
    } else {
        for (const raw of Array.isArray(stress.impacts) ? stress.impacts : []) {
            const impact = raw as Record<string, unknown>;
            const assetId = toNumber(impact.asset_id);
            if (assetId === null) continue;
            const value = toNumber(impact.contribution_return) ?? toNumber(impact.shock_return);
            if (value === null) continue;
            rows.push({key: `asset:${assetId}`, assetId, value, amount: toNumber(impact.impact_amount), weight: toNumber(impact.weight)});
        }
    }

    return rows.sort((left, right) => left.value - right.value);
}

/**
 * The one error a caller can reason about, whichever shape the wire used.
 *
 * `generated.ts:7662` types the field as `RiskError | Array<RiskError | null>`
 * while the Zod validator at `:14415` only ever admits the single object — the
 * backend declares `Optional[RiskError]` (`schemas/risk.py:1045`). The array
 * branch is therefore unreachable today, but casting it away would leave a lie
 * behind if the contract ever widens for real. Normalising costs one line.
 */
function firstError(error: RiskAnalyticResult['error']): RiskErrorShape | null {
    if (!error) return null;
    if (Array.isArray(error)) return error.find((entry): entry is RiskErrorShape => Boolean(entry)) ?? null;
    return error;
}

/**
 * The warnings the replay block shows itself, beside the number it qualifies (D372).
 *
 * The section around the block lists every analytic's warnings as its reasons. These two would
 * then be read twice, and the first time far from the figure, so the mounts hand the section
 * {@link replaySectionView} instead of the raw result.
 */
export const REPLAY_BLOCK_WARNING_CODES: readonly string[] = ['historical_replay_assets_excluded', 'historical_replay_mostly_excluded'];

/**
 * The order the block lists the reasons in: the order of `RiskHistoricalReplayExclusionReason`
 * (`schemas/risk.py`), with the reader's own exclusion last. A reason this list does not know
 * comes after the known ones, in the order it arrived.
 */
export const REPLAY_EXCLUSION_REASON_ORDER: readonly string[] = ['no_prices_in_window', 'starts_after_window_start', 'stale_at_window_start', 'stale_at_window_end', 'missing_fx', 'manual_exclusion'];

/** One asset the replay left out, with its share of the value when the scope has weights. */
export interface ReplayExcludedAsset {
    assetId: number;
    weight: number | null;
}

export interface ReplayExclusionGroup {
    reason: string;
    assets: ReplayExcludedAsset[];
}

/**
 * What the replay left out, grouped by why.
 *
 * `treatment` is what the figures did with them: on a portfolio the excluded weight is carried as
 * cash at zero return, on a selection without weights the assets are omitted. It is `null` when
 * nothing was replayed at all, because then no figure treated them in any way.
 */
export interface ReplayExclusions {
    groups: ReplayExclusionGroup[];
    count: number;
    weightTotal: number | null;
    treatment: 'zero_return_residual' | 'omitted_from_replay' | null;
}

/** The part of the window that brings back the assets its edges excluded, as the backend verified it. */
export interface ReplaySuggestion {
    start: string;
    end: string;
    recovers: number[];
}

type ListedExclusion = ReplayExcludedAsset & {reason: string};

function replayAudit(result: RiskAnalyticResult | null | undefined) {
    return singleValue(riskMetadata(result)?.historical_replay_audit);
}

/**
 * The details of a replay that had nothing left to run, or `null`.
 *
 * `stress.py::_historical` answers `insufficient_history` when every asset is excluded, and lists
 * them in `details.excluded_asset_ids`. The same code without that list is another refusal (a
 * window with no observations at all), and stays an error the section discloses.
 */
function nothingLeftDetails(result: RiskAnalyticResult | null | undefined): Record<string, unknown> | null {
    if (!result || result.status !== 'unavailable') return null;
    const error = firstError(result.error);
    if (!error || error.code !== 'insufficient_history') return null;
    const details = (error.details ?? {}) as Record<string, unknown>;
    return Array.isArray(details.excluded_asset_ids) && details.excluded_asset_ids.length > 0 ? details : null;
}

/** Whether the replay excluded every asset, so there was nothing left to replay. */
export function replayNothingLeft(result: RiskAnalyticResult | null | undefined): boolean {
    return nothingLeftDetails(result) !== null;
}

function reasonRank(reason: string): number {
    const index = REPLAY_EXCLUSION_REASON_ORDER.indexOf(reason);
    return index === -1 ? REPLAY_EXCLUSION_REASON_ORDER.length : index;
}

/** Heaviest first, unweighted last, then by id. */
function byWeightThenId(left: ReplayExcludedAsset, right: ReplayExcludedAsset): number {
    if (left.weight !== right.weight) {
        if (left.weight === null) return 1;
        if (right.weight === null) return -1;
        return right.weight - left.weight;
    }
    return left.assetId - right.assetId;
}

function groupByReason(items: readonly ListedExclusion[]): ReplayExclusionGroup[] {
    const groups = new Map<string, ReplayExcludedAsset[]>();
    for (const {reason, assetId, weight} of items) {
        const assets = groups.get(reason) ?? [];
        assets.push({assetId, weight});
        groups.set(reason, assets);
    }
    // A Map keeps arrival order and the sort is stable, so the unknown reasons keep theirs.
    return [...groups.entries()].sort(([left], [right]) => reasonRank(left) - reasonRank(right)).map(([reason, assets]) => ({reason, assets: assets.sort(byWeightThenId)}));
}

function listedExclusion(raw: unknown): ListedExclusion | null {
    if (!raw || typeof raw !== 'object') return null;
    const entry = raw as Record<string, unknown>;
    const assetId = toNumber(entry.asset_id);
    if (assetId === null) return null;
    return {assetId, reason: typeof entry.reason === 'string' && entry.reason !== '' ? entry.reason : 'unknown', weight: toNumber(entry.weight)};
}

/**
 * The assets the replay left out, by reason, or `null` when it left none out.
 *
 * Read from the audit when the replay ran. When nothing was left to run there is no audit, and
 * the error's details carry the same list; an older answer with only the ids gives one group
 * whose reason is unknown.
 */
export function replayExclusions(result: RiskAnalyticResult | null | undefined): ReplayExclusions | null {
    const audit = replayAudit(result);
    const audited = audit?.excluded_assets ?? [];
    if (audited.length > 0) {
        const items = audited.map((item) => ({assetId: item.asset_id, reason: item.reason ?? 'manual_exclusion', weight: toNumber(item.weight)}));
        const treatment = audited.some((item) => item.treatment === 'omitted_from_replay') ? 'omitted_from_replay' : audited.some((item) => item.treatment === 'zero_return_residual') ? 'zero_return_residual' : null;
        const weighted = items.some((item) => item.weight !== null);
        return {groups: groupByReason(items), count: items.length, weightTotal: weighted ? toNumber(audit?.excluded_weight_total) : null, treatment};
    }
    const details = nothingLeftDetails(result);
    if (!details) return null;
    const listed = (Array.isArray(details.excluded_assets) ? details.excluded_assets : []).map(listedExclusion).filter((item): item is ListedExclusion => item !== null);
    if (listed.length > 0) {
        const weights = listed.flatMap((item) => (item.weight === null ? [] : [item.weight]));
        return {groups: groupByReason(listed), count: listed.length, weightTotal: weights.length > 0 ? weights.reduce((sum, weight) => sum + weight, 0) : null, treatment: null};
    }
    const ids = (details.excluded_asset_ids as unknown[]).map(toNumber).filter((id): id is number => id !== null);
    if (ids.length === 0) return null;
    return {groups: groupByReason(ids.map((assetId) => ({assetId, reason: 'unknown', weight: null}))), count: ids.length, weightTotal: null, treatment: null};
}

function suggestionFrom(range: unknown, recovers: unknown): ReplaySuggestion | null {
    if (!range || typeof range !== 'object') return null;
    const {start, end} = range as {start?: unknown; end?: unknown};
    if (typeof start !== 'string' || start === '') return null;
    const ids = (Array.isArray(recovers) ? recovers : []).map(toNumber).filter((id): id is number => id !== null);
    if (ids.length === 0) return null;
    return {start, end: typeof end === 'string' && end !== '' ? end : start, recovers: ids};
}

/** The common period the backend proposes, from the audit or from a replay with nothing left; `null` without one. */
export function replaySuggestion(result: RiskAnalyticResult | null | undefined): ReplaySuggestion | null {
    const audit = replayAudit(result);
    const audited = suggestionFrom(audit?.suggested_range, audit?.suggested_range_recovers);
    if (audited) return audited;
    const details = nothingLeftDetails(result);
    return details ? suggestionFrom(details.suggested_range, details.suggested_range_recovers) : null;
}

/** The strong warning: the replay describes only part of the portfolio. */
export function replayCoverageWarning(result: RiskAnalyticResult | null | undefined): RiskResultWarning | null {
    return result?.warnings?.find((warning) => warning?.code === 'historical_replay_mostly_excluded') ?? null;
}

/**
 * The replay result as its section should read it: without the warnings the block shows, and
 * without the error of a replay that had nothing left, which the block explains itself.
 *
 * Status and metadata stay, so the section's status line still says the replay was partial or
 * unavailable. A new object: the controller's result is never touched.
 */
export function replaySectionView(result: RiskAnalyticResult | null | undefined): RiskAnalyticResult | null {
    if (!result) return null;
    const view: RiskAnalyticResult = {...result};
    if (result.warnings) view.warnings = result.warnings.filter((warning) => !REPLAY_BLOCK_WARNING_CODES.includes(warning?.code ?? ''));
    if (replayNothingLeft(result)) view.error = null;
    return view;
}

/** A replay date as the block writes it, e.g. «15 ott 2008». UTC, so the day never shifts. */
export function formatReplayDate(iso: string, language: string): string {
    return new Intl.DateTimeFormat(language, {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'}).format(new Date(`${iso}T00:00:00Z`));
}

/** A share of the value, with one decimal: «12,0%». */
export function formatReplayShare(fraction: number, language: string): string {
    return new Intl.NumberFormat(language, {style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1}).format(fraction);
}
