/**
 * profileAutoAsk — the life of the automatic «Chiedi» in the asset window (plan 68, E8b), as `enricherRecognition` is
 * the life of «Riconosci».
 *
 * - One question per (type, list) (`autoAskKey`): the same is never asked twice; a new one drops the answer of the old,
 *   late ones too, and those of a session that ended.
 * - The answer is handed over once (`onanswer`), when it is the current question's; the asset window merges it
 *   (`mergeAutoFills`).
 * - A 429 (the per-user limit of the probes, C0) is a wait, not an end (PROF, E8c): `refused` with its wait (a minute
 *   when the answer names none), then the same question again by itself; `cancel` and a new question end the wait.
 *   Another failure is a state.
 * - `cancel` (the asset created, the window closed) drops what is in flight: no work in the background (round 28).
 *
 * @module features/assets/profile/profileAutoAsk
 */
import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
import {autoAskKey, type AutoAskRequest} from './assetProfileDraft';
import type {AskAnswer} from './profileEditState';

export type AutoAskStatus = 'idle' | 'running' | 'done' | 'refused' | 'error';

/** The wait of a refusal for too many requests, in seconds; null when the answer is not one. */
function refusedWait(error: unknown): number | null | undefined {
    const response = (error as {response?: {status?: unknown; data?: unknown}} | null | undefined)?.response;
    if (response?.status !== 429) return undefined;
    const wait = (response.data as {detail?: {retry_after?: unknown}} | null | undefined)?.detail?.retry_after;
    return typeof wait === 'number' ? wait : null;
}

/** The wait when a refusal for too many requests names none: the limiter's window, a minute. */
const DEFAULT_RETRY_SECONDS = 60;

export function createProfileAutoAsk(ask: (request: AutoAskRequest) => Promise<AskAnswer>, onanswer: (answer: AskAnswer) => void) {
    let sequence = 0;
    let key: string | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let status = $state<AutoAskStatus>('idle');
    let retryAfter = $state<number | null>(null);

    function stopWaiting() {
        if (retryTimer !== null) clearTimeout(retryTimer);
        retryTimer = null;
    }

    /** Ask `request`, the current question. */
    function run(request: AutoAskRequest) {
        stopWaiting();
        const mine = ++sequence;
        const session = getClientSessionGeneration();
        const current = () => mine === sequence && isClientSessionCurrent(session);
        status = 'running';
        retryAfter = null;
        ask(request).then(
            (answer) => {
                if (!current()) return;
                status = 'done';
                onanswer(answer);
            },
            (error: unknown) => {
                if (!current()) return;
                const wait = refusedWait(error);
                if (wait === undefined) {
                    status = 'error';
                    return;
                }
                status = 'refused';
                retryAfter = wait;
                // The same question again once the wait is over: the user starts nothing (PROF, E8c)
                retryTimer = setTimeout(
                    () => {
                        retryTimer = null;
                        if (current()) run(request);
                    },
                    (wait ?? DEFAULT_RETRY_SECONDS) * 1000,
                );
            },
        );
    }

    /** Ask, when the question is new; true when it started. */
    function start(request: AutoAskRequest): boolean {
        const next = autoAskKey(request);
        if (next === key) return false;
        key = next;
        run(request);
        return true;
    }

    /** Stop and forget: the answer in flight is dropped. */
    function cancel() {
        stopWaiting();
        sequence += 1;
        key = null;
        status = 'idle';
        retryAfter = null;
    }

    return {
        start,
        cancel,
        get status() {
            return status;
        },
        get retryAfter() {
            return retryAfter;
        },
    };
}

export type ProfileAutoAsk = ReturnType<typeof createProfileAutoAsk>;
