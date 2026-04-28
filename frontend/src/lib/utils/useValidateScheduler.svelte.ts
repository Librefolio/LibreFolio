/**
 * useValidateScheduler — debounced + idle + manual server-validate trigger.
 *
 * Centralizes the scheduling logic shared by `TransactionFormModal` (1 row),
 * `TransactionBulkModal` (N rows), and `PromotePairWizardModal` (Step 3).
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
    /** Debounce window after a `change` trigger. Default 1000 ms. */
    debounceMs?: number;
    /** Idle window before auto-firing without changes. Default 60 000 ms. */
    idleMs?: number;
}

export interface ValidateSchedulerState {
    /** True while a validate request is in-flight. */
    isValidating: boolean;
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
    const debounceMs = opts.debounceMs ?? 1000;
    const idleMs = opts.idleMs ?? 60000;

    const state = $state<ValidateSchedulerState>({
        isValidating: false,
        lastValidatedAt: null,
        issuesCount: null,
        autoDisabled: !opts.enabled(),
    });

    let debounceTimer: ReturnType<typeof setTimeout> | null = null;
    let idleTimer: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;
    /** Monotonic seq# — late responses with stale seq are dropped. */
    let runSeq = 0;

    function clearDebounce() {
        if (debounceTimer != null) {
            clearTimeout(debounceTimer);
            debounceTimer = null;
        }
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
        const seq = ++runSeq;
        state.isValidating = true;
        try {
            const res = await opts.validateFn(reason);
            if (seq !== runSeq || disposed) return; // stale response or disposed
            state.lastValidatedAt = Date.now();
            state.issuesCount = res.issuesCount;
        } catch {
            if (seq !== runSeq || disposed) return;
            // Leave previous lastValidatedAt/issuesCount as-is; caller surfaces banner.
        } finally {
            if (seq === runSeq && !disposed) {
                state.isValidating = false;
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
            debounceTimer = setTimeout(() => {
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

