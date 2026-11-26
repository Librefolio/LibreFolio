/**
 * profileStore.ts — the small memory of the asset profile (plan 68, E1): what the «Profilo» tab, its cards, the changes
 * panel and the profile windows read, shared so one page asks the server once per question.
 *
 * - The catalogue (`GET /assets/profile/catalogue`) is asked once per session; `profileVoice(key)` answers a voice of
 *   it once loaded. A failed load is not kept.
 * - A read (`POST /assets/profile/query`) is remembered per request: asset, range, voices and changes. A read that fails
 *   is not kept. `invalidateAssetProfile(id)` forgets one asset's reads — call it after anything that writes the
 *   profile (`PATCH /assets` with `profile`, «Aggiorna»); «Dimentica» calls it itself.
 * - «Dimentica» (`DELETE /assets/profile`) sends the `as_of` of the read the page shows: the server refuses, whole, rows
 *   written after it (409 `PROFILE_UPDATES_NEWER`) or not of that asset (404 `PROFILE_UPDATES_NOT_FOUND`). Those two
 *   are typed results, never a throw, so the page can say «reload» and read again.
 * - «Aggiorna» (`POST /assets/profile/refresh`, E6c) reads the asset's enrichers again and saves what changed; the
 *   asset's reads are forgotten either way. «Riallinea i profili» (87, A5) asks it for many assets in one call.
 *
 * Plain module, no runes: nothing here is reactive; a component keeps what it reads in its own state.
 */
import {schemas, zodiosApi} from '$lib/api';
import type {z} from 'zod';

/** One voice of the catalogue: its key, shape, sign, unit, groups and choices. */
export type ProfileVoice = z.infer<typeof schemas.FAProfileVoice>;
/** The range of a read: two days, one day (`end` absent), or `start: 'min'` for «Tutti». */
export type ProfileDateRange = {start: string; end?: string | null} | {start: 'min'; end: string};
/** Which changes a read adds: the panel (`key` absent or null) or the history of one voice, a page of twenty. */
export interface ProfileChangesQuery {
    key?: string | null;
    page?: number;
}
/** One step of a voice: from `date` to `through`, its value and source. */
export type ProfileStep = z.infer<typeof schemas.FAProfileStepPoint>;
/** The steps of every voice read, by key. */
export type ProfileVoices = Record<string, ProfileStep[]>;
/** A page of changes. */
export type ProfileChangesPage = z.infer<typeof schemas.FAProfileChangesPage>;

/** A read of one asset: its steps and changes, or the asset no longer exists (deleted by someone else). */
export type AssetProfileRead = {kind: 'found'; asOf: string; voices: ProfileVoices; changes: ProfileChangesPage | null} | {kind: 'missing'; asOf: string};

/** What «Dimentica» did: the rows are gone, or the server refused them all (`newer`: reload the page; `not_found`). */
/** «Aggiorna» for one asset: the voices written and how each enricher's read went (E6c). */
export type ProfileRefreshResult = z.infer<typeof schemas.FAProfileRefreshResult>;

export type ProfileForgetOutcome = {kind: 'forgotten'; deleted: number} | {kind: 'newer' | 'not_found'; updateIds: number[]};

export interface ProfileReadOptions {
    /** The voices to read; absent: every voice; `[]`: none (only the changes). */
    keys?: string[];
    changes?: ProfileChangesQuery;
}

let catalogue: Promise<ProfileVoice[]> | null = null;
let voicesByKey = new Map<string, ProfileVoice>();
/** asset id → request key → the read in flight or done. */
const reads = new Map<number, Map<string, Promise<AssetProfileRead>>>();

/** The catalogue of the profile, asked once per session. */
export function loadProfileCatalogue(): Promise<ProfileVoice[]> {
    if (catalogue === null) {
        catalogue = zodiosApi.profile_catalogue_api_v1_assets_profile_catalogue_get().then(
            (response) => {
                voicesByKey = new Map(response.voices.map((voice) => [voice.key, voice]));
                return response.voices;
            },
            (error: unknown) => {
                catalogue = null;
                throw error;
            },
        );
    }
    return catalogue;
}

/** A voice of the loaded catalogue; `undefined` before the first load or for a key it does not list. */
export function profileVoice(key: string): ProfileVoice | undefined {
    return voicesByKey.get(key);
}

function requestKey(range: ProfileDateRange, options: ProfileReadOptions): string {
    return JSON.stringify([range.start, range.end ?? null, options.keys ?? null, options.changes ? [options.changes.key ?? null, options.changes.page ?? 0] : null]);
}

/** The profile of one asset in `range`: remembered per request until the asset is invalidated. */
export function readAssetProfile(assetId: number, range: ProfileDateRange, options: ProfileReadOptions = {}): Promise<AssetProfileRead> {
    const key = requestKey(range, options);
    let byRequest = reads.get(assetId);
    if (!byRequest) {
        byRequest = new Map();
        reads.set(assetId, byRequest);
    }
    const remembered = byRequest.get(key);
    if (remembered) return remembered;
    const item = {asset_id: assetId, date_range: range, ...(options.keys !== undefined ? {keys: options.keys} : {}), ...(options.changes !== undefined ? {changes: options.changes} : {})};
    const read = zodiosApi.query_profile_api_v1_assets_profile_query_post([item]).then(
        (response): AssetProfileRead => {
            const result = response.items[0];
            if (!result || result.error) return {kind: 'missing', asOf: response.as_of};
            return {kind: 'found', asOf: response.as_of, voices: (result.voices ?? {}) as ProfileVoices, changes: (result.changes ?? null) as ProfileChangesPage | null};
        },
        (error: unknown) => {
            if (reads.get(assetId)?.get(key) === read) reads.get(assetId)?.delete(key);
            throw error;
        },
    );
    byRequest.set(key, read);
    return read;
}

/** Forget the remembered reads of one asset: call after anything that writes its profile. */
export function invalidateAssetProfile(assetId: number): void {
    reads.delete(assetId);
}

/** Forget everything: the catalogue and every read (sign-out, tests). */
export function clearProfileMemory(): void {
    catalogue = null;
    voicesByKey = new Map();
    reads.clear();
}

const REFUSALS: Record<string, 'newer' | 'not_found'> = {PROFILE_UPDATES_NEWER: 'newer', PROFILE_UPDATES_NOT_FOUND: 'not_found'};

function refusal(error: unknown): ProfileForgetOutcome | null {
    const response = (error as {response?: {status?: unknown; data?: unknown}} | null | undefined)?.response;
    const detail = (response?.data as {detail?: unknown} | null | undefined)?.detail;
    if (!detail || typeof detail !== 'object') return null;
    const fields = detail as {error_code?: unknown; update_ids?: unknown};
    const kind = typeof fields.error_code === 'string' ? REFUSALS[fields.error_code] : undefined;
    if (!kind) return null;
    const updateIds = Array.isArray(fields.update_ids) ? fields.update_ids.filter((id): id is number => typeof id === 'number') : [];
    return {kind, updateIds};
}

/**
 * «Dimentica»: delete those rows of one asset, as if the changes had never been made. `asOf` is the `as_of` of the read
 * the page shows. The asset's reads are forgotten whatever the server answers: the page reads again.
 */
export async function forgetProfileRows(assetId: number, updateIds: number[], asOf: string): Promise<ProfileForgetOutcome> {
    try {
        const response = await zodiosApi.forget_profile_api_v1_assets_profile_delete([{asset_id: assetId, update_ids: updateIds, as_of: asOf}]);
        return {kind: 'forgotten', deleted: response.total_deleted};
    } catch (error) {
        const refused = refusal(error);
        if (refused === null) throw error;
        return refused;
    } finally {
        invalidateAssetProfile(assetId);
    }
}

/**
 * «Aggiorna» (E6c): read the asset's enrichers again and save what changed, as the weekly read does. The asset's reads are
 * forgotten whatever the server answers: the tab reads again. An error is thrown as it came.
 */
export async function refreshAssetProfile(assetId: number): Promise<ProfileRefreshResult> {
    try {
        const response = await zodiosApi.refresh_profile_api_v1_assets_profile_refresh_post([assetId]);
        const result = response.results.find((item) => item.asset_id === assetId);
        return result ?? {asset_id: assetId, written: [], outcomes: [], error: 'missing', enrichers_read: 0};
    } finally {
        invalidateAssetProfile(assetId);
    }
}

/**
 * How long «Riallinea i profili» waits for its one answer. A source is read slowly, about one call a second, so many assets
 * take minutes. Never split into smaller calls: a source that refused for too many requests stops for the rest of its
 * own call only, and the next call would ask it again.
 */
export const PROFILE_BULK_REFRESH_TIMEOUT_MS = 15 * 60_000;

/** «Riallinea i profili» (87, A5): as `refreshAssetProfile`, for many assets in one call, one result per asset asked. */
export async function refreshAssetProfiles(assetIds: number[]): Promise<ProfileRefreshResult[]> {
    try {
        const response = await zodiosApi.refresh_profile_api_v1_assets_profile_refresh_post(assetIds, {timeout: PROFILE_BULK_REFRESH_TIMEOUT_MS});
        const byId = new Map(response.results.map((item) => [item.asset_id, item]));
        return assetIds.map((id) => byId.get(id) ?? {asset_id: id, written: [], outcomes: [], error: 'missing', enrichers_read: 0});
    } finally {
        for (const id of assetIds) invalidateAssetProfile(id);
    }
}
