/**
 * Bounded parallelism for browser-issued requests.
 *
 * ## Why a limit at all
 *
 * Firing every request at once is not free. A browser will not open unlimited connections
 * to one host, so the extra requests queue *inside* the browser — invisible to us, and in
 * an order we do not control. Worse, they compete with the requests the rest of the app
 * still needs (prices, FX, navigation). Saturating the pool to shave a second off an
 * import makes the whole page feel broken while it runs.
 *
 * ## The limit we cannot read
 *
 * There is **no web API that exposes the per-host connection cap**. `navigator.connection`
 * describes link quality on Chromium only, never counts; `navigator.hardwareConcurrency`
 * counts CPU cores, which is a different thing entirely. The cap is a browser internal:
 * HTTP/1.1 clients settle on **6 per host** by long-standing convention, while HTTP/2
 * multiplexes over one connection and the practical ceiling is far higher.
 *
 * So the number here is a **heuristic, not a measurement**, and it is deliberately built
 * on the pessimistic case: assume HTTP/1.1, leave one slot free so the rest of the app can
 * still talk to the server while an import runs, and never exceed the number of cores —
 * on a dual-core machine, six parses in flight only means six of them taking turns.
 */

/** Long-standing browser convention for HTTP/1.1. Not readable at runtime — see above. */
export const HTTP1_PER_HOST_LIMIT = 6;

/** Used when `navigator.hardwareConcurrency` is unavailable, as on older Safari. */
export const DEFAULT_CONCURRENCY = 4;

/**
 * How many requests to keep in flight at once.
 *
 * One slot is always left free: an import that starves the rest of the application of
 * connections looks like a freeze, and a user cannot tell the difference between "busy"
 * and "broken".
 */
export function requestConcurrency(): number {
    const cores = typeof navigator !== 'undefined' ? navigator.hardwareConcurrency : undefined;
    const byCores = typeof cores === 'number' && cores > 0 ? cores : DEFAULT_CONCURRENCY;
    return Math.max(2, Math.min(HTTP1_PER_HOST_LIMIT - 1, byCores));
}

export interface ConcurrencyOptions {
    /** Maximum tasks in flight. Defaults to {@link requestConcurrency}. */
    limit?: number;
    /**
     * Consulted before each task starts. Returning `true` stops the run: tasks already in
     * flight are awaited (they cannot be unsent), none new are started.
     */
    shouldStop?: () => boolean;
}

/**
 * Run `task` over `items` with at most `limit` in flight, **preserving order**.
 *
 * Order matters more than it looks: callers index their own state by position, so a
 * runner that returned results as they completed would scramble it. Results are written
 * into a pre-sized array by index, so completion order is irrelevant to the caller.
 *
 * A task that rejects does not cancel the others — the rejection surfaces once the whole
 * run settles. Callers that must not lose the other results should catch inside `task`,
 * which is what both import loops do: a file that fails to parse is a row marked in error,
 * not an aborted import.
 */
export async function mapWithConcurrency<T, R>(items: readonly T[], task: (item: T, index: number) => Promise<R>, options: ConcurrencyOptions = {}): Promise<Array<R | undefined>> {
    const {limit = requestConcurrency(), shouldStop} = options;
    const results: Array<R | undefined> = new Array(items.length);
    if (items.length === 0) return results;

    let next = 0;
    const workers = Math.max(1, Math.min(limit, items.length));

    async function pump(): Promise<void> {
        for (;;) {
            if (shouldStop?.()) return;
            const index = next++;
            if (index >= items.length) return;
            results[index] = await task(items[index], index);
        }
    }

    await Promise.all(Array.from({length: workers}, () => pump()));
    return results;
}
