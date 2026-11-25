/**
 * The step's title row (TL-3 of project 67, the developer's testlist of 21/11): the shell draws the step's title, and a step
 * may put one piece of its own on the same row, on the right (the Targets step puts its columns button there). The shell
 * provides the holder; the step sets its snippet while it is mounted and clears it when it goes.
 */
import {getContext, setContext, type Snippet} from 'svelte';

/** The context key; a test mounts a step inside a holder of its own with it. */
export const STEP_TITLE_CONTEXT = Symbol('planner-step-title');

export class StepTitleSlot {
    /** The step's piece for the title row, or null: the title alone. */
    action = $state<Snippet | null>(null);

    /**
     * Who holds the row, outside the reactive graph: a release compares with it, never with `action`, because an effect's
     * teardown may read a state that a write of the same tick has not reached yet (measured on the test of the guard).
     */
    #holder: Snippet | null = null;

    /** Called by a step while it is mounted: puts `snippet` on the row, and returns what takes it away again. */
    hold(snippet: Snippet): () => void {
        this.#holder = snippet;
        this.action = snippet;
        return () => {
            // The next step may already have put its own piece: only this step's piece goes.
            if (this.#holder !== snippet) return;
            this.#holder = null;
            this.action = null;
        };
    }
}

/** Called by the shell, while it is created: the steps below it put their piece on its title row. */
export function provideStepTitleSlot(): StepTitleSlot {
    const slot = new StepTitleSlot();
    setContext(STEP_TITLE_CONTEXT, slot);
    return slot;
}

/** The shell's title row, read while a step is created; null outside a shell (a step mounted alone draws the piece itself). */
export function stepTitleSlot(): StepTitleSlot | null {
    try {
        return getContext<StepTitleSlot | undefined>(STEP_TITLE_CONTEXT) ?? null;
    } catch {
        return null;
    }
}
