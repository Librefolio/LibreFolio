/**
 * The reads of comparison targets the settings preview of a card asks for (lot Z-29d, reduced).
 *
 * A sampled card draws a comparison on its own buckets, so its target has to be read «like the card» (`sample_like`,
 * `utils/reducedPriceQuery.ts`). The page does that for the comparisons a card has saved; one the user has just picked in
 * the card's settings is not read yet, and the preview would not draw it until the save. The preview asks for it from
 * inside its rendering, where no state may be written, so the loader runs the read afterwards (a microtask), once per
 * key — card, target, range and `max_points` —, and never again for a key whose read failed: a refused or broken read
 * would otherwise be asked again on every render.
 *
 * Pure: the read itself is the caller's.
 *
 * @module utils/targetSampleLoader
 */

/** What one read is for. */
export interface TargetSampleRequest {
    cardId: number;
    targetId: number;
    start: string;
    end: string;
    /** The `max_points` of the card's plot: another width may ask another step. */
    maxPoints: number;
}

/** The key a read is run once for. */
export function targetSampleKey(request: TargetSampleRequest): string {
    return `${request.cardId}|${request.targetId}|${request.start}|${request.end}|${request.maxPoints}`;
}

export class TargetSampleLoader {
    private readonly asked = new Set<string>();

    /**
     * @param read reads the target sampled like the card and puts it where the preview reads it.
     * @param failed told once of a read that failed (the page logs it); the key is not tried again.
     */
    constructor(
        private readonly read: (request: TargetSampleRequest) => Promise<void>,
        private readonly failed: (request: TargetSampleRequest, error: unknown) => void = () => undefined,
    ) {}

    /** Ask for the read of `request`, unless it was asked already: it runs once the caller has returned. */
    want(request: TargetSampleRequest): void {
        const key = targetSampleKey(request);
        if (this.asked.has(key)) return;
        this.asked.add(key);
        queueMicrotask(() => {
            this.read(request).catch((error: unknown) => this.failed(request, error));
        });
    }

    /** Forget every key: the next ask reads again (prices changed, the settings closed). */
    reset(): void {
        this.asked.clear();
    }
}
