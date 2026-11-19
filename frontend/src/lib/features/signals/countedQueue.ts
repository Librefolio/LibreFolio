/**
 * countedQueue — loads that run one at a time, each counted from the moment it is asked (project 76, FB-7e).
 *
 * The FX list asks the comparison series of its cards one load at a time, so a load finds in the cache what the one
 * before it brought, and says busy (`data-busy`) while a load is counted. A load asked as not counted (the silent reload
 * after a price catch-up) runs in the same line without making the page busy. A counted load is counted from its call,
 * not from its start: queued behind a silent one, the page says busy for the whole wait (FB-7e; the settings save and its
 * preview start such loads).
 */

export interface CountedQueue {
    /** Run `task` after the loads asked before it; `counted` loads are counted from now until `task` ends. */
    run(task: () => Promise<void>, counted: boolean): Promise<void>;
}

/** A queue that reports each counted load's start (+1, at the call) and end (−1) to `count`. */
export function countedQueue(count: (delta: 1 | -1) => void): CountedQueue {
    let line: Promise<void> = Promise.resolve();
    return {
        run(task, counted) {
            if (counted) count(1);
            const run = line.then(task);
            // The line goes on after a failure: the next load is not held by an earlier one that failed
            line = run.catch(() => undefined);
            return counted ? run.finally(() => count(-1)) : run;
        },
    };
}
