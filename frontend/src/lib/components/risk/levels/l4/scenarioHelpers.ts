import type {z} from 'zod';

import {schemas} from '$lib/api';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

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

/**
 * The two things a failed replay lets the reader do next.
 *
 * `stress.py:458` refuses the whole replay as soon as one holding has no usable
 * history in the period, and says so by name: *"Asset N requires a manual proxy
 * or explicit exclusion"*. That is not a dead end, it is a **question** — and
 * the answer is a choice the reader has to make, because a proxy is an opinion
 * about what a missing asset would have done, not a measurement of it.
 */
export interface ReplayBlocker {
    assetId: number;
    /** Why the series was unusable, verbatim from the server. */
    reason: string;
    /** True when the *proxy* is the thing without history, not the original. */
    proxyAtFault: boolean;
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
 * What a failed replay is asking for, when it is asking for something.
 *
 * Returns `null` for every other failure: a timeout, a busy worker or an
 * unprepared series are not questions the reader can answer, and offering a
 * "fix it" button for them would be a lie about who is in control.
 */ export function replayBlocker(result: RiskAnalyticResult | null | undefined): ReplayBlocker | null {
    if (!result || (result.status !== 'unavailable' && result.status !== 'failed')) return null;
    const error = firstError(result.error);
    if (!error) return null;
    if (error.code !== 'insufficient_history' && error.code !== 'invalid_parameters') return null;
    const details = (error.details ?? {}) as Record<string, unknown>;
    const assetId = toNumber(details.asset_id);
    if (assetId === null) return null;
    const source = toNumber(details.return_source_asset_id);
    return {
        assetId,
        reason: typeof details.reason === 'string' ? details.reason : 'insufficient_history',
        proxyAtFault: source !== null && source !== assetId,
    };
}
