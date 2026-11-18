/**
 * profileAutoAsk — the life of the automatic «Chiedi» in the asset window (plan 68, E8b), as `enricherRecognition` is
 * the life of «Riconosci».
 *
 * - One question per (type, list) (`autoAskKey`): the same is never asked twice; a new one drops the answer of the old,
 *   late ones too, and those of a session that ended.
 * - The answer is handed over once (`onanswer`), when it is the current question's; the asset window merges it
 *   (`mergeAutoFills`).
 * - A 429 (the per-user limit of the probes, C0) is a state with its wait, never retried; another failure a state too.
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

export function createProfileAutoAsk(ask: (request: AutoAskRequest) => Promise<AskAnswer>, onanswer: (answer: AskAnswer) => void) {
    let sequence = 0;
    let key: string | null = null;
    let status = $state<AutoAskStatus>('idle');
    let retryAfter = $state<number | null>(null);

    /** Ask, when the question is new; true when it started. */
    function start(request: AutoAskRequest): boolean {
        const next = autoAskKey(request);
        if (next === key) return false;
        key = next;
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
                if (wait !== undefined) {
                    status = 'refused';
                    retryAfter = wait;
                } else {
                    status = 'error';
                }
            },
        );
        return true;
    }

    /** Stop and forget: the answer in flight is dropped. */
    function cancel() {
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
