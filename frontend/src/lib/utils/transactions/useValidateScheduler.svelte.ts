/**
 * useValidateScheduler — debounced + idle + manual server-validate trigger.
 *
 * Centralizes the scheduling logic shared by `TransactionFormModal` (1 row),
 * `TransactionBulkModal` (N rows).
 *
 * Three triggers, all routed to a single `validateFn`:
 * - `'change'`: debounced 1 s, used on every editable-field mutation.
 * - `'manual'`: fires immediately, used by the toolbar `⚡ Validate now` button.
 * - `'idle'`:   auto-fires after 60 s without any `change` (NOT reset by manual).
 *
 * The `enabled` predicate is checked at every dispatch; when it returns false
 * (e.g. row count > 50 in bulk modal), `change` and `idle` are no-ops. Manual
 * trigger is ALWAYS honored.
 *
 * Filename uses the `.svelte.ts` extension to opt-in to runes outside a
 * component (Svelte 5 convention for stateful utilities).
 *
 * @module utils/useValidateScheduler
 */

export type ValidateReason = 'change' | 'manual' | 'idle';

export interface ValidateSchedulerOptions {
    /** Predicate guarding `change` + `idle` auto-triggers. Manual ignores it. */
    enabled: () => boolean;
    /** Async validate function (typically calls POST /transactions/validate). */
    validateFn: (reason: ValidateReason) => Promise<{issuesCount: number}>;
    /** Returns a key representing the current draft state. When unchanged, anti-bounce kicks in. */
    draftKey?: () => string;
    /** Debounce window after a `change` trigger. Default 1000 ms. */
    debounceMs?: number;
    /** Idle window before auto-firing without changes. Default 60 000 ms. */
    idleMs?: number;
    /** Anti-bounce window: skip re-validate if draft unchanged within this window. Default 10 000 ms. */
    antiBounceMs?: number;
}

export interface ValidateSchedulerState {
    /** True while a validate request is in-flight. */
    isValidating: boolean;
    /**
     * True while a `change` trigger is waiting out its debounce window.
     *
     * Without this the scheduler looks settled for `debounceMs` after an edit,
     * while what is on screen is still the *previous* verdict. Both the toolbar
     * hint and `data-busy` read `isPending || isValidating`, so "the numbers are
     * being recomputed" covers the queued window too.
     */
    isPending: boolean;
    /**
     * Monotonic count of *completed* validate runs.
     *
     * `isPending`/`isValidating` answer "is it working now?", which a reader can
     * miss entirely by arriving late. A counter answers "has it worked since I
     * looked?", which cannot be missed: read it before acting, wait for it to
     * grow after. Same shape as `data-chart-renders`.
     */
    validateRuns: number;
    /** Wall-clock ms of the last successful validate response. `null` until the first call. */
    lastValidatedAt: number | null;
    /** Issue count from the last response. `null` until the first call. */
    issuesCount: number | null;
    /** True when the predicate disabled auto-triggers (UI hint). */
    autoDisabled: boolean;
}

export interface ValidateScheduler {
    /** Reactive state — read-only from callers; updated internally. */
    readonly state: ValidateSchedulerState;
    /** Request a validate run. Auto-triggers respect `enabled`; manual ignores it. */
    trigger: (reason: ValidateReason) => void;
    /** Stop pending timers and prevent further runs. */
    dispose: () => void;
}

export function createValidateScheduler(opts: ValidateSchedulerOptions): ValidateScheduler {
    const debounceMs = opts.debounceMs ?? 500;
    const idleMs = opts.idleMs ?? 60000;
    const antiBounceMs = opts.antiBounceMs ?? 10000;

    const state = $state<ValidateSchedulerState>({
        isValidating: false,
        isPending: false,
        validateRuns: 0,
        lastValidatedAt: null,
        issuesCount: null,
        autoDisabled: !opts.enabled(),
    });

    let debounceTimer: ReturnType<typeof setTimeout> | null = null;
    let idleTimer: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;
    /** Monotonic seq# — late responses with stale seq are dropped. */
    let runSeq = 0;
    /** Draft key at the time of the last completed validate call. */
    let lastValidatedDraftKey: string | null = null;

    function clearDebounce() {
        if (debounceTimer != null) {
            clearTimeout(debounceTimer);
            debounceTimer = null;
        }
        state.isPending = false;
    }
    function clearIdle() {
        if (idleTimer != null) {
            clearTimeout(idleTimer);
            idleTimer = null;
        }
    }
    function rearmIdle() {
        clearIdle();
        if (disposed) return;
        if (!opts.enabled()) return;
        idleTimer = setTimeout(() => {
            void runValidate('idle');
        }, idleMs);
    }

    async function runValidate(reason: ValidateReason) {
        if (disposed) return;
        // W3-fix: re-check enabled() at execution time (debounce timer may fire
        // after predicate flipped — e.g. paired form where partner isn't ready yet).
        if (reason !== 'manual' && !opts.enabled()) return;
        // Anti-bounce: if draft hasn't changed since last validate and we're within the window, skip.
        // Manual triggers bypass anti-bounce (user explicitly requested, or post-sync needs fresh data).
        if (reason !== 'manual' && opts.draftKey) {
            const currentKey = opts.draftKey();
            if (currentKey === lastValidatedDraftKey && state.lastValidatedAt != null && Date.now() - state.lastValidatedAt < antiBounceMs) {
                return;
            }
        }
        const seq = ++runSeq;
        // Sample the draft key BEFORE the round-trip: it identifies the state
        // this run actually validated. Reading it again after the `await` would
        // credit the run with whatever the user typed while the server was
        // thinking — and the anti-bounce below would then skip the run that was
        // supposed to check those very edits, leaving a stale verdict on screen
        // with nothing queued. Slow server ⇒ the last edit silently loses its
        // validation. `validateFn` already samples its own key this way.
        const sentKey = opts.draftKey ? opts.draftKey() : null;
        state.isValidating = true;
        try {
            const res = await opts.validateFn(reason);
            if (seq !== runSeq || disposed) return; // stale response or disposed
            state.lastValidatedAt = Date.now();
            state.issuesCount = res.issuesCount;
            lastValidatedDraftKey = sentKey;
        } catch {
            if (seq !== runSeq || disposed) return;
            // Leave previous lastValidatedAt/issuesCount as-is; caller surfaces banner.
            lastValidatedDraftKey = sentKey;
        } finally {
            if (seq === runSeq && !disposed) {
                state.isValidating = false;
                state.validateRuns += 1;
            }
        }
    }

    function trigger(reason: ValidateReason) {
        if (disposed) return;
        // Refresh autoDisabled view on every dispatch (cheap).
        state.autoDisabled = !opts.enabled();

        if (reason === 'manual') {
            clearDebounce();
            // Manual does NOT reset the idle timer — per plan: idle resets only on real change.
            void runValidate('manual');
            return;
        }

        if (reason === 'change') {
            if (!opts.enabled()) {
                // Auto path disabled — clear any pending timers, await manual click.
                clearDebounce();
                clearIdle();
                return;
            }
            clearDebounce();
            state.isPending = true;
            debounceTimer = setTimeout(() => {
                debounceTimer = null;
                state.isPending = false;
                void runValidate('change');
            }, debounceMs);
            // Reset idle timer ONLY on a real change.
            rearmIdle();
            return;
        }

        // reason === 'idle' (internal call from setTimeout) — predicate already
        // checked at rearm but verify again (predicate may have flipped).
        if (!opts.enabled()) return;
        void runValidate('idle');
    }

    // Initial idle arm if predicate currently allows it.
    rearmIdle();

    function dispose() {
        disposed = true;
        clearDebounce();
        clearIdle();
    }

    return {state, trigger, dispose};
}
