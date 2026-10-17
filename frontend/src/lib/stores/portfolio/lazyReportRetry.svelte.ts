/**
 * lazyReportRetry — how often a page asks again for a lazily-loaded report section after a failure (Y-24).
 *
 * The Dashboard and a broker's page load the P&L candles and the positions contribution only when a view shows them:
 * an `$effect` of `GrowthChart` or `PositionsPanel` calls the page's loader while the section is missing and not
 * loading. When the report fails the section stays missing and the loading flag falls back to false, so that effect
 * ran again at once: the page asked for the same failing report again and again, without a pause.
 *
 * One retry per section bounds it. After a failure, a scope (the request's brokers, period and currency) may be asked
 * again 2, 4 and 8 seconds later, then not any more until the scope changes or the user presses Refresh (`reset()`).
 * `canAsk` is a reactive read: an effect that calls it runs again when a retry falls due, so the waiting loader asks by
 * itself, with no timer of its own. No clock is read: whether a retry is due comes only from the timer.
 *
 * The loader records the outcome (`failed` or `succeeded`) before it lets its loading flag go, so the effect woken by
 * that flag already sees the failure.
 *
 * @module stores/portfolio/lazyReportRetry
 */

/** The waits before the automatic retries after a failure; after the last one, none. */
export const LAZY_REPORT_RETRY_DELAYS_MS: readonly number[] = [2_000, 4_000, 8_000];

export interface LazyReportRetry {
    /** Whether a request for `scope` may go now. A reactive read: an `$effect` that calls it runs again when a retry falls due, and after `reset()`. */
    canAsk(scope: string): boolean;
    /** A request for `scope` failed. */
    failed(scope: string): void;
    /** A request answered: the failures are forgotten. */
    succeeded(scope: string): void;
    /** Refresh: forget every failure, cancel the pending timer, wake the readers. */
    reset(): void;
    /** The page is gone: cancel the pending timer; no reader is woken afterwards. */
    dispose(): void;
}

export function createLazyReportRetry(delaysMs: readonly number[] = LAZY_REPORT_RETRY_DELAYS_MS): LazyReportRetry {
    // The readers depend on this tick only: it moves when a retry falls due and on reset().
    let version = $state(0);
    let scope: string | null = null;
    let failures = 0;
    let due = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;

    function cancel(): void {
        if (timer !== null) clearTimeout(timer);
        timer = null;
    }

    function forget(): void {
        cancel();
        scope = null;
        failures = 0;
        due = false;
    }

    return {
        canAsk(asked) {
            void version;
            if (scope !== asked || failures === 0) return true;
            return due;
        },
        failed(asked) {
            if (scope !== asked) {
                forget();
                scope = asked;
            }
            failures += 1;
            due = false;
            cancel();
            if (disposed || failures > delaysMs.length) return;
            timer = setTimeout(
                () => {
                    timer = null;
                    due = true;
                    if (!disposed) version += 1;
                },
                delaysMs[failures - 1],
            );
        },
        succeeded() {
            forget();
        },
        reset() {
            forget();
            if (!disposed) version += 1;
        },
        dispose() {
            disposed = true;
            cancel();
        },
    };
}
