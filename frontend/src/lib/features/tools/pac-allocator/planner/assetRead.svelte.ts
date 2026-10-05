/**
 * Reads what LibreFolio stores about Assets added from the database (R5.5,
 * R6.2): the latest stored price and the composition, so neither waits on an
 * explicit copy. It calls no provider and fills only what is still empty and
 * was never copied; `refreshPlan` reads copied prices again just before the
 * calculation. The cards show the outcome, so there is no copy banner.
 */
import {SvelteMap, SvelteSet} from 'svelte/reactivity';
import {applyAddedAssetClassifications, applyAddedAssetPrices, domainAssetKey, exposuresAwaitRead, lackingDimensions, newCopyRecord, priceAwaitsRead} from './copies';
import type {DraftAsset, ExposureDimension, PlannerDraft} from './draft.svelte';
import {loadCopyScope, selectableIds} from './scope';
import {SourceLoad, type SourceLoadError} from './sourceLoad.svelte';

const SCOPE_ERROR: SourceLoadError = {key: 'tools.pacAllocator.planner.copy.scopeError', fallback: 'The Broker list could not be loaded. Nothing was copied.'};

/** What a read learned, kept per draft so it survives leaving and re-entering the step. */
interface ReadMemory {
    /** Asset ids read successfully at least once: the step does not read them again on its own. */
    attempted: SvelteSet<number>;
    /** Asset ids read with no usable stored price. */
    missedPrice: SvelteSet<number>;
    /** For each Asset id read, the dimensions LibreFolio holds no classification for. */
    lacking: SvelteMap<number, ExposureDimension[]>;
}

const memories = new WeakMap<PlannerDraft, ReadMemory>();

function memoryOf(draft: PlannerDraft): ReadMemory {
    let memory = memories.get(draft);
    if (!memory) {
        memory = {attempted: new SvelteSet(), missedPrice: new SvelteSet(), lacking: new SvelteMap()};
        memories.set(draft, memory);
    }
    return memory;
}

/** A copied Asset with a price or a composition the read may still fill. */
export function needsRead(asset: DraftAsset | undefined): boolean {
    return asset !== undefined && (priceAwaitsRead(asset) || exposuresAwaitRead(asset));
}

export class AddedAssetFacts {
    readonly load = new SourceLoad();
    /** Asset ids waiting for the running read. */
    waiting = $state<number[]>([]);
    busy = $state(false);
    error = $state<SourceLoadError | null>(null);

    #sequence = 0;
    /** Asset ids of the last failed read, for «Retry». */
    #failed = $state<number[]>([]);

    isReading(assetId: number | null): boolean {
        return assetId !== null && this.busy && this.waiting.includes(assetId);
    }

    notStored(draft: PlannerDraft, assetId: number | null): boolean {
        return assetId !== null && memoryOf(draft).missedPrice.has(assetId);
    }

    /** The dimensions LibreFolio lacked for this Asset at its last read; empty when never read. */
    lackingOf(draft: PlannerDraft, assetId: number | null): readonly ExposureDimension[] {
        return assetId === null ? [] : (memoryOf(draft).lacking.get(assetId) ?? []);
    }

    /** Copied Assets never read in this session that still have something to fill. */
    pending(draft: PlannerDraft): number[] {
        const memory = memoryOf(draft);
        return draft.data.assets.filter((asset) => asset.sourceAssetId !== null && !memory.attempted.has(asset.sourceAssetId) && needsRead(asset)).map((asset) => asset.sourceAssetId as number);
    }

    /**
     * A newer call supersedes an older one and carries its ids too; the ids are
     * taken only after the Broker scope is known, so none is lost in between.
     */
    async read(draft: PlannerDraft, assetIds: readonly number[], accountGeneration: number): Promise<void> {
        if (assetIds.length === 0) return;
        const memory = memoryOf(draft);
        const sequence = ++this.#sequence;
        this.waiting = [...new Set([...this.waiting, ...assetIds])];
        for (const id of assetIds) {
            memory.missedPrice.delete(id);
            memory.lacking.delete(id);
        }
        this.busy = true;
        this.error = null;
        let owners: number[];
        try {
            owners = selectableIds(await loadCopyScope());
        } catch {
            if (sequence === this.#sequence) this.#finish(SCOPE_ERROR, this.waiting);
            return;
        }
        if (sequence !== this.#sequence) return;
        const ids = this.waiting.filter((id) => needsRead(draft.asset(domainAssetKey(id))));
        if (ids.length === 0 || owners.length === 0 || !/^[A-Z]{3}$/.test(draft.data.valuationCurrency)) {
            this.#finish(null, []);
            return;
        }
        const awaiting = (test: (asset: DraftAsset) => boolean) =>
            ids.filter((id) => {
                const asset = draft.asset(domainAssetKey(id));
                return asset !== undefined && test(asset);
            });
        const priceIds = awaiting(priceAwaitsRead);
        const classIds = awaiting(exposuresAwaitRead);
        draft.refreshAsOf();
        const source = await this.load.load(
            {asOf: draft.data.asOf, targetCurrency: draft.data.valuationCurrency, sections: ['assets', 'prices', 'classifications'], brokerIds: owners, assetIds: ids, fxPairs: []},
            accountGeneration,
        );
        if (sequence !== this.#sequence) return;
        if (!source) {
            if (this.load.status === 'error') this.#finish(this.load.error, ids);
            else this.#finish(null, []);
            return;
        }
        applyAddedAssetPrices(draft, source, newCopyRecord(draft, 'prices', source), priceIds);
        applyAddedAssetClassifications(draft, source, newCopyRecord(draft, 'classifications', source), classIds);
        for (const id of priceIds) {
            if (draft.asset(domainAssetKey(id))?.price === null) memory.missedPrice.add(id);
        }
        for (const [id, dimensions] of lackingDimensions(source, classIds)) memory.lacking.set(id, dimensions);
        for (const id of ids) memory.attempted.add(id);
        this.#finish(null, []);
    }

    /** Reads again the Assets of the last failed read. */
    retry(draft: PlannerDraft, accountGeneration: number): void {
        const ids = [...this.#failed];
        this.#failed = [];
        void this.read(draft, ids, accountGeneration);
    }

    get canRetry(): boolean {
        return this.error !== null && this.#failed.length > 0;
    }

    stop(): void {
        this.#sequence += 1;
        this.load.stop();
        this.#finish(null, []);
    }

    dismiss(): void {
        this.error = null;
        this.#failed = [];
    }

    #finish(error: SourceLoadError | null, failed: readonly number[]): void {
        this.#failed = error ? [...failed] : [];
        this.busy = false;
        this.waiting = [];
        this.error = error;
    }
}
