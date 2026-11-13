import {pageBusy, type BusyToken} from '$lib/stores/app/pageBusy.svelte';

/**
 * The quiet period between the last click on the broker filter and the reload it asks for (anti-bounce for rapid
 * clicks). For all of it the page is busy: the Refresh button spins and `data-busy` holds, so the totals still on
 * screen are not mistaken for the new scope's (K-18). One token spans the wait; the reload takes its own before the
 * wait's is returned, so the page is never idle in between.
 */
export function createScopeReloadDebounce(options: {delayMs: number; waitLabel: string; reloadLabel: string; reload: () => Promise<unknown>}) {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let waiting: BusyToken | null = null;

    function endWait() {
        if (waiting !== null) pageBusy.end(waiting);
        waiting = null;
    }

    return {
        schedule() {
            if (timer !== null) clearTimeout(timer);
            if (waiting === null) waiting = pageBusy.begin(options.waitLabel);
            timer = setTimeout(() => {
                timer = null;
                void pageBusy.track(options.reloadLabel, options.reload);
                endWait();
            }, options.delayMs);
        },
        /** The page is left: no reload fires, and no token stays behind. */
        dispose() {
            if (timer !== null) clearTimeout(timer);
            timer = null;
            endWait();
        },
    };
}
