/**
 * Shared "hold the arrow key" accelerator.
 *
 * Stepping one unit at a time is fine for a nudge and useless for a journey: walking
 * a quantity from 30 to 3000, or a date back twenty years, is not something a user
 * should have to do 2970 keypresses at a time. Holding the key therefore makes the
 * step grow — but only after the current step has had a fair run, so the small
 * adjustment that is the common case is never stolen by the acceleration.
 *
 * The ladder itself is the caller's business: a number climbs by powers of ten, a
 * date climbs day → month → year. What is shared is the bookkeeping — which input
 * holds the key, in which direction, and for how long.
 */

/** Repeats one rung of the ladder serves before the next one may take over. */
export const HOLD_REPEATS_BEFORE_ESCALATION = 15;

/**
 * One key-hold run. Instantiate once per concern (numbers, dates) — two inputs cannot
 * hold a key at the same time, so a single tracker per concern is enough.
 */
export class ArrowHold {
    private target: EventTarget | null = null;
    private direction = 0;
    private repeats = 0;

    /**
     * Where the caller is on its own ladder. Meaningless to this class, which only
     * carries it across repeats so the call site can stay a plain function.
     */
    level = 0;

    /** Forgets the run, so the next press starts again at the bottom of the ladder. */
    reset(): void {
        this.target = null;
        this.direction = 0;
        this.repeats = 0;
        this.level = 0;
    }

    /**
     * Registers this keypress. Returns `true` when it starts a new run — a first press,
     * a different input, or a change of direction — in which case the caller must
     * re-seed {@link level}. Reversing direction restarts on purpose: the user has
     * overshot and is coming back for a small correction, not for more speed.
     */
    begin(event: KeyboardEvent, direction: number): boolean {
        if (!event.repeat || event.target !== this.target || direction !== this.direction) {
            this.target = event.target;
            this.direction = direction;
            this.repeats = 0;
            return true;
        }
        this.repeats += 1;
        return false;
    }

    /** Whether the current rung has served its quota and the caller may climb. */
    get ready(): boolean {
        return this.repeats >= HOLD_REPEATS_BEFORE_ESCALATION;
    }

    /** Call after climbing a rung, so the new one gets a full quota of its own. */
    escalated(): void {
        this.repeats = 0;
    }
}
