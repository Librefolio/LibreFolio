/**
 * enricherRecognition — the life of «Riconosci» in the asset window (plan 68, E8a), as `providerProbeState` is the
 * life of the price provider's probe.
 *
 * - **When it starts** (PROF, rounds 18 and 21): at creation, as soon as the form holds a strong identifier: a whole ISIN
 *   (the only strong type the asset form has; one being typed asks nothing, each question counting on the limit). For
 *   an asset that exists (ENR-1, R1), when its enrichers' window opens: the fields are not being typed, so any
 *   identifier a covering enricher accepts is enough (`acceptedTypes`).
 *   The question is the asset's type, every identifier known and the price provider (first at equal degree); the same
 *   question is never asked twice, a new one aborts the old and drops its answers, late ones too.
 * - **What it keeps**: every enricher's answer by code, as it arrives (the enrichers' window shows them, and «searching»
 *   while it runs), and the `default_order` of `done`.
 * - **What it proposes**: the found ones in the default order, each bound to the identifier it was found by; not one
 *   found only by a ticker (R2: it may be another listing, the user adds it after reading its name).
 * - **No work in the background** (round 28): `cancel` (the asset created, the window closed) drops what is in flight.
 * - A 429 (the per-user limit of the probes, C0) is a wait, not an end (PROF, E8c): the state is `refused` with its
 *   wait (`retryAfter`, a minute when the answer names none), and the same question is asked again by itself once the
 *   wait is over; the user starts nothing. `cancel` and a new question end the wait. A failure is a state (`error`).
 *
 * @module features/assets/enrichers/enricherRecognition
 */
import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
import {entersAlone, type EnricherBinding, type EnricherRecognition} from './enrichersEditState';
import {recognizeEnrichers, type RecognizeEvent, type RecognizeRequest} from './recognizeStream';

/** What the asset window knows: its type, its identifiers (type → value), its price provider. */
export interface RecognitionInput {
    assetType: string;
    identifiers: Record<string, string>;
    priceProviderCode: string | null;
    /**
     * An asset that exists (ENR-1): the identifier types the covering enrichers accept. One of them is enough to ask;
     * absent at creation, where a whole ISIN is needed.
     */
    acceptedTypes?: string[];
}

export type RecognitionStatus = 'idle' | 'running' | 'done' | 'refused' | 'error';

/** The shape of an ISIN: country, nine characters, a check digit. One being typed is not one yet. */
const ISIN_SHAPE = /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/;

function requestOf(input: RecognitionInput): RecognizeRequest | null {
    const identifiers = Object.fromEntries(Object.entries(input.identifiers).filter(([, value]) => value.trim() !== ''));
    if (!input.assetType) return null;
    const askable = input.acceptedTypes ? input.acceptedTypes.some((type) => type in identifiers) : ISIN_SHAPE.test(identifiers.ISIN ?? '');
    if (!askable) return null;
    return {asset_type: input.assetType, identifiers, price_provider_code: input.priceProviderCode || null};
}

function keyOf(request: RecognizeRequest): string {
    const identifiers = Object.entries(request.identifiers).sort(([a], [b]) => a.localeCompare(b));
    return JSON.stringify([request.asset_type, identifiers, request.price_provider_code ?? null]);
}

/** The wait when a refusal for too many requests names none: the limiter's window, a minute. */
const DEFAULT_RETRY_SECONDS = 60;

export function createEnricherRecognitionState() {
    let sequence = 0;
    let key: string | null = null;
    let controller: AbortController | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let status = $state<RecognitionStatus>('idle');
    let recognitions = $state<Record<string, EnricherRecognition>>({});
    let defaultOrder = $state<string[]>([]);
    let retryAfter = $state<number | null>(null);

    function drop() {
        sequence += 1;
        if (retryTimer !== null) clearTimeout(retryTimer);
        retryTimer = null;
        controller?.abort();
        controller = null;
        recognitions = {};
        defaultOrder = [];
        retryAfter = null;
    }

    /** Ask `request`, the current question: its answers replace whatever an earlier asking of it left. */
    function ask(request: RecognizeRequest) {
        drop();
        status = 'running';
        const mine = sequence;
        const session = getClientSessionGeneration();
        const current = () => mine === sequence && isClientSessionCurrent(session);
        controller = new AbortController();
        const onEvent = (event: RecognizeEvent) => {
            if (!current()) return;
            if (event.event === 'enricher_result') {
                const {event: _kind, ...answer} = event;
                recognitions = {...recognitions, [answer.code]: answer as EnricherRecognition};
            } else if (event.event === 'done') {
                defaultOrder = event.default_order;
            }
        };
        recognizeEnrichers(request, {onEvent, signal: controller.signal}).then(
            (outcome) => {
                if (!current()) return;
                if (outcome.kind === 'refused') {
                    status = 'refused';
                    retryAfter = outcome.retryAfter;
                    // The same question again once the wait is over: the user starts nothing (PROF, E8c)
                    retryTimer = setTimeout(
                        () => {
                            retryTimer = null;
                            if (current()) ask(request);
                        },
                        (outcome.retryAfter ?? DEFAULT_RETRY_SECONDS) * 1000,
                    );
                } else if (outcome.kind === 'done') {
                    status = 'done';
                }
            },
            () => {
                if (current()) status = 'error';
            },
        );
    }

    /** Ask, when the form holds a strong identifier and the question is new; true when a question started. */
    function start(input: RecognitionInput): boolean {
        const request = requestOf(input);
        if (request === null) return false;
        const next = keyOf(request);
        if (next === key) return false;
        key = next;
        ask(request);
        return true;
    }

    /** Stop and forget: the answers in flight are dropped (the asset created, the window closed). */
    function cancel() {
        drop();
        key = null;
        status = 'idle';
    }

    return {
        start,
        cancel,
        /** The input holds something to ask with: «Riconosci» would start on it. */
        canRecognize: (input: RecognitionInput) => requestOf(input) !== null,
        get status() {
            return status;
        },
        get recognitions() {
            return recognitions;
        },
        get retryAfter() {
            return retryAfter;
        },
        /** The found enrichers in the default order, each bound to the identifier it was found by. */
        get proposal(): Record<string, EnricherBinding> {
            const order = defaultOrder.length ? defaultOrder : Object.keys(recognitions);
            const proposal: Record<string, EnricherBinding> = {};
            for (const code of order) {
                const answer = recognitions[code];
                if (entersAlone(answer)) proposal[code] = {identifier_type: answer.identifier_type, identifier: answer.identifier};
            }
            return proposal;
        },
    };
}

export type EnricherRecognitionState = ReturnType<typeof createEnricherRecognitionState>;
