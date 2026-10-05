/**
 * Reads the FX rates LibreFolio stores for the pairs the scenario needs (R9.4),
 * so an «Auto» pair never waits on an explicit copy. Like `AddedAssetFacts` it
 * calls no provider and fills only a rate still waiting for its first read;
 * `refreshPlan` reads copied rates again just before the calculation.
 */
import {SvelteSet} from 'svelte/reactivity';
import {applyAwaitingFxRates, newCopyRecord, rateAwaitsRead} from './copies';
import type {PlannerDraft} from './draft.svelte';
import {loadCopyScope, selectableIds} from './scope';
import {SourceLoad, type SourceLoadError} from './sourceLoad.svelte';

const SCOPE_ERROR: SourceLoadError = {key: 'tools.pacAllocator.planner.copy.scopeError', fallback: 'The Broker list could not be loaded. Nothing was copied.'};

/** What a read learned, kept per draft so it survives leaving and re-entering the step. */
interface FxMemory {
    /** Pairs read at least once: the step does not read them again on its own. */
    attempted: SvelteSet<string>;
    /** Pairs read with no stored rate. */
    missed: SvelteSet<string>;
    /** Pairs that could not be read: LibreFolio reads only for a user who owns a Broker. */
    ownerless: SvelteSet<string>;
}

const memories = new WeakMap<PlannerDraft, FxMemory>();

function memoryOf(draft: PlannerDraft): FxMemory {
    let memory = memories.get(draft);
    if (!memory) {
        memory = {attempted: new SvelteSet(), missed: new SvelteSet(), ownerless: new SvelteSet()};
        memories.set(draft, memory);
    }
    return memory;
}

function awaits(draft: PlannerDraft, pair: string): boolean {
    const fx = draft.fx(pair);
    return !fx || rateAwaitsRead(fx);
}

export class FxRateReader {
    readonly load = new SourceLoad();
    /** Pairs waiting for the running read. */
    waiting = $state<string[]>([]);
    busy = $state(false);
    error = $state<SourceLoadError | null>(null);

    #sequence = 0;
    /** Pairs of the last failed read, for «Retry». */
    #failed = $state<string[]>([]);

    isReading(pair: string): boolean {
        return this.busy && this.waiting.includes(pair);
    }

    notStored(draft: PlannerDraft, pair: string): boolean {
        return memoryOf(draft).missed.has(pair);
    }

    ownerless(draft: PlannerDraft, pair: string): boolean {
        return memoryOf(draft).ownerless.has(pair);
    }

    /** Needed pairs never read in this session and still waiting for a rate. */
    pending(draft: PlannerDraft): string[] {
        const memory = memoryOf(draft);
        return draft.requiredPairs.filter((pair) => !memory.attempted.has(pair) && awaits(draft, pair));
    }

    /**
     * A newer call supersedes an older one and carries its pairs too; the pairs
     * are taken only after the Broker scope is known, so none is lost in between.
     */
    async read(draft: PlannerDraft, pairs: readonly string[], accountGeneration: number): Promise<void> {
        if (pairs.length === 0) return;
        const memory = memoryOf(draft);
        const sequence = ++this.#sequence;
        this.waiting = [...new Set([...this.waiting, ...pairs])];
        for (const pair of pairs) {
            memory.missed.delete(pair);
            memory.ownerless.delete(pair);
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
        const needed = new Set(draft.requiredPairs);
        const wanted = this.waiting.filter((pair) => needed.has(pair) && awaits(draft, pair));
        if (wanted.length === 0 || !/^[A-Z]{3}$/.test(draft.data.valuationCurrency)) {
            this.#finish(null, []);
            return;
        }
        if (owners.length === 0) {
            for (const pair of wanted) {
                memory.ownerless.add(pair);
                memory.attempted.add(pair);
            }
            this.#finish(null, []);
            return;
        }
        draft.refreshAsOf();
        const source = await this.load.load(
            {asOf: draft.data.asOf, targetCurrency: draft.data.valuationCurrency, sections: ['fx_quotes'], brokerIds: owners, assetIds: [], fxPairs: wanted},
            accountGeneration,
        );
        if (sequence !== this.#sequence) return;
        if (!source) {
            if (this.load.status === 'error') this.#finish(this.load.error, wanted);
            else this.#finish(null, []);
            return;
        }
        const outcome = applyAwaitingFxRates(draft, source, newCopyRecord(draft, 'fx', source), wanted);
        for (const pair of outcome.missing) memory.missed.add(pair);
        for (const pair of wanted) memory.attempted.add(pair);
        this.#finish(null, []);
    }

    /** Reads again the pairs of the last failed read. */
    retry(draft: PlannerDraft, accountGeneration: number): void {
        const pairs = [...this.#failed];
        this.#failed = [];
        void this.read(draft, pairs, accountGeneration);
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

    #finish(error: SourceLoadError | null, failed: readonly string[]): void {
        this.#failed = error ? [...failed] : [];
        this.busy = false;
        this.waiting = [];
        this.error = error;
    }
}
