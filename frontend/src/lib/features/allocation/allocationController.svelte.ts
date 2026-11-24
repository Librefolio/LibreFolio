/**
 * The controller of the «Allocazione» tab (lane 80, F2): asks `POST /portfolio/allocation`, keeps the last answer, and
 * remembers the user's filters per page.
 *
 * - **One answer at a time.** Each `load` takes a sequence number; an answer that comes back after a newer ask is dropped,
 *   so a quick run of clicks never leaves the screen on an old question. The previous answer stays on screen while the next
 *   one is on its way (and after a failure, with `failed` set): the tab never blanks.
 * - **Filters per page.** The Dashboard and every broker keep their own (`allocation-filters:dashboard`,
 *   `allocation-filters:broker:<id>`, a user-scoped key). What was stored is read once, defensively (`parseFilters`); a
 *   change is written at once. First opening: the whole portfolio.
 * - **No page state of its own.** What the tab asks (scope, dimension, filters) is the caller's: the caller decides when to
 *   ask, under the page's busy tracking (`pageBusy`), and passes the ask to `load`.
 *
 * It computes nothing: every amount and share is the backend's.
 *
 * @module features/allocation/allocationController
 */
import {zodiosApi} from '$lib/api';
import {getUserStorage, setUserStorage} from '$lib/utils/storage';
import {emptyFilters, parseFilters, serializeFilters, type AllocationFilters} from './allocationFilters';
import {buildAllocationQuery, DEFAULT_ALLOCATION_DIMENSION, normalizeAllocation, type AllocationAsk, type AllocationDimension, type AllocationQuery, type AllocationResponse, type RawAllocationResponse} from './allocationQuery';

export interface AllocationControllerDeps {
    fetch: (body: AllocationQuery) => Promise<RawAllocationResponse>;
    read: (key: string) => string;
    write: (key: string, value: string) => void;
}

const defaultDeps: AllocationControllerDeps = {
    fetch: (body) => zodiosApi.get_portfolio_allocation_api_v1_portfolio_allocation_post(body),
    read: (key) => getUserStorage(key, ''),
    write: (key, value) => setUserStorage(key, value),
};

export class AllocationController {
    /** The last answer; `null` until the first one lands. */
    response = $state.raw<AllocationResponse | null>(null);
    /** A request is on its way. */
    loading = $state(false);
    /** The last request failed (the previous answer, if any, is still the one shown). */
    failed = $state(false);
    filters = $state.raw<AllocationFilters>(emptyFilters());
    dimension = $state<AllocationDimension>(DEFAULT_ALLOCATION_DIMENSION);
    /** «Now» (the base's slices) or «History» (the selection's history in steps, asked with the same answer). */
    mode = $state<'now' | 'history'>('now');

    readonly #storageKey: string;
    readonly #deps: AllocationControllerDeps;
    #sequence = 0;
    #disposed = false;

    constructor(storageKey: string, deps: Partial<AllocationControllerDeps> = {}) {
        this.#storageKey = storageKey;
        this.#deps = {...defaultDeps, ...deps};
        this.filters = parseFilters(this.#deps.read(storageKey));
    }

    /** The user changed the choices: kept for this page, and the caller asks again. */
    setFilters(next: AllocationFilters): void {
        this.filters = next;
        this.#deps.write(this.#storageKey, serializeFilters(next));
    }

    /** «Rimuovi filtri»: back to the whole portfolio. */
    resetFilters(): void {
        this.setFilters(emptyFilters());
    }

    setDimension(next: AllocationDimension): void {
        this.dimension = next;
    }

    setMode(next: 'now' | 'history'): void {
        this.mode = next;
    }

    /** Asks the backend. Resolves when this ask is answered, failed or dropped; never rejects. */
    async load(ask: AllocationAsk): Promise<void> {
        if (this.#disposed) return;
        const sequence = ++this.#sequence;
        this.loading = true;
        this.failed = false;
        try {
            const answer = await this.#deps.fetch(buildAllocationQuery(ask));
            if (this.#disposed || sequence !== this.#sequence) return;
            this.response = normalizeAllocation(answer);
        } catch {
            if (this.#disposed || sequence !== this.#sequence) return;
            this.failed = true;
        } finally {
            if (!this.#disposed && sequence === this.#sequence) this.loading = false;
        }
    }

    /** The tab is gone: a late answer is dropped. */
    dispose(): void {
        this.#disposed = true;
        this.#sequence += 1;
    }
}

export function createAllocationController(storageKey: string, deps: Partial<AllocationControllerDeps> = {}): AllocationController {
    return new AllocationController(storageKey, deps);
}
