/**
 * The parameters each backend signal's last answer was computed with (`normalized_params`), by signal instance.
 *
 * A control that says a value the backend chose for the request — the reader's risk-free rate (RN-21) — says the one
 * of the answer the chart draws, never the one a field holds now: between a change and the next answer, the two differ,
 * and the line must stay true (the consultant, 17/11/2026, as in RN-18b). `SignalResultState.apply` records every
 * answer it accepts, on every page that draws signals, so no page has to.
 */
import {SvelteMap} from 'svelte/reactivity';

import type {SignalInstanceResult} from './resultMapper';

const answered = new SvelteMap<string, Readonly<Record<string, unknown>>>();

/** Record the parameters of the backend answers just accepted, by the instance each one serves. */
export function recordAnsweredParams(results: readonly SignalInstanceResult[]): void {
    for (const item of results) {
        const params = item.result?.normalized_params;
        if (item.source === 'backend' && params && typeof params === 'object') answered.set(item.config.id, params as Record<string, unknown>);
    }
}

/** A parameter of the last answer for one instance, or undefined before any answer. */
export function answeredParam(instanceId: string, key: string): unknown {
    return answered.get(instanceId)?.[key];
}
