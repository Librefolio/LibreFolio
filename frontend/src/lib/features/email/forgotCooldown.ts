/**
 * «Forgot password» by email: the wait before the next request (lot UA1, developer's decision 09/11/2026).
 *
 * The server sends at most one reset email every 5 minutes per account and drops the rest in silence, so the form
 * waits that long after an accepted request before it lets the user ask again. The wait is the same whether an account
 * matched or not: it never tells the accounts apart. The deadline is kept in `sessionStorage`, so a reload of the page
 * keeps it; storage that cannot be used (a private window, blocked site data) only loses that, never the form.
 */

/**
 * Seconds between two requests: the server's `RESET_EMAIL_MIN_INTERVAL` (5 minutes, in
 * `backend/app/services/email/flows.py`). Kept here rather than read from `GET /system/instance`: change both together.
 */
export const FORGOT_RESEND_WAIT_S = 5 * 60;

/** The `sessionStorage` key holding the deadline, in epoch milliseconds. */
export const FORGOT_COOLDOWN_KEY = 'librefolio.forgotPassword.nextRequestAt';

/** The deadline still in force, in epoch milliseconds; `null` when there is none, it has passed, or it cannot be read. */
export function readForgotCooldown(now: number = Date.now()): number | null {
    try {
        const stored = Number(sessionStorage.getItem(FORGOT_COOLDOWN_KEY));
        // A deadline further than the wait itself was not written by this code (or the clock moved back): ignored.
        if (!Number.isFinite(stored) || stored <= now || stored > now + FORGOT_RESEND_WAIT_S * 1000) return null;
        return stored;
    } catch {
        return null;
    }
}

/** Start the wait from `now`; returns the deadline, also when it could not be stored. */
export function startForgotCooldown(now: number = Date.now()): number {
    const deadline = now + FORGOT_RESEND_WAIT_S * 1000;
    try {
        sessionStorage.setItem(FORGOT_COOLDOWN_KEY, String(deadline));
    } catch {
        // Not stored: the wait holds until the page is reloaded.
    }
    return deadline;
}

/** Whole seconds left until `deadline`, never below 0. */
export function secondsLeft(deadline: number, now: number = Date.now()): number {
    return Math.max(0, Math.ceil((deadline - now) / 1000));
}

/** `m:ss`, the same in every language. */
export function formatWait(seconds: number): string {
    const whole = Math.max(0, Math.floor(seconds));
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
}
