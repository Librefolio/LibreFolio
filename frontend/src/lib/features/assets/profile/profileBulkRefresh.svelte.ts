/**
 * profileBulkRefresh.svelte.ts — the state of the «Profilo» section of the assets' sync window (87, A5): which of the
 * assets handed over have enrichers, and how their one refresh goes. It outlives the window's content: closing the window
 * leaves the read going, and opening it again finds it where it is.
 *
 * - `status`: `idle`, `loading` (who has enrichers), `ready`, `unknown` (that read failed);
 * - `run`: `idle`, `running`, `done` (with `results`), `serverRunning` (the wait ended first), `failed`.
 */
import {zodiosApi} from '$lib/api';
import {refreshProfiles} from './profileRefresh';
import type {ProfileRefreshResult} from './profileStore';

type Translate = (key: string, values?: Record<string, string | number>) => string;

/** The assets asked per `GET /assets`: its ids travel in the address. */
const ASSETS_PER_REQUEST = 100;

export function createProfileBulkRefresh() {
    let status = $state<'idle' | 'loading' | 'ready' | 'unknown'>('idle');
    let withEnrichers = $state<number[]>([]);
    let run = $state<'idle' | 'running' | 'done' | 'serverRunning' | 'failed'>('idle');
    let results = $state<ProfileRefreshResult[]>([]);
    let generation = 0;

    /** The window opened on these assets: find those with enrichers. A read under way is left alone, and shown. */
    async function open(assetIds: number[]): Promise<void> {
        if (run === 'running') return;
        const mine = ++generation;
        run = 'idle';
        results = [];
        status = 'loading';
        const ids = [...new Set(assetIds)];
        const found: number[] = [];
        try {
            for (let from = 0; from < ids.length; from += ASSETS_PER_REQUEST) {
                const rows = await zodiosApi.read_assets_bulk_api_v1_assets_get({queries: {asset_ids: ids.slice(from, from + ASSETS_PER_REQUEST)}});
                if (mine !== generation) return;
                for (const row of rows) {
                    const config = (row.enrichers as {config?: Record<string, unknown>} | null | undefined)?.config;
                    if (config && Object.keys(config).length) found.push(row.asset_id);
                }
            }
            withEnrichers = found;
            status = 'ready';
        } catch {
            if (mine === generation) status = 'unknown';
        }
    }

    async function start(translate: Translate): Promise<void> {
        if (run === 'running' || status !== 'ready' || !withEnrichers.length) return;
        run = 'running';
        results = [];
        const answer = await refreshProfiles([...withEnrichers], translate);
        if (answer.kind === 'done') results = answer.results;
        run = answer.kind === 'done' ? 'done' : answer.kind === 'running' ? 'serverRunning' : 'failed';
    }

    return {
        get status() {
            return status;
        },
        get assetIds() {
            return withEnrichers;
        },
        get run() {
            return run;
        },
        get results() {
            return results;
        },
        open,
        start,
    };
}

export type ProfileBulkRefresh = ReturnType<typeof createProfileBulkRefresh>;
