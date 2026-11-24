/**
 * The scenario preview (F3a of project 67, step 8; N1, contract §11): the numbers the screen shows before the calculation
 * come from the backend.
 *
 * The service's `preview` operation reads the same request as `plan` (`buildRequest(…, {operation: 'preview'})`, which lets
 * a draft still being typed through) and answers the total, today's value and weight of every target entry, and the λ of
 * the three fidelity levels. This class only reads and forwards: no figure is computed here (the table «maximum acceptable
 * cost» is the page's own, `acceptableCost.ts`, from these numbers: R1-F (b) of project 67). It
 *   - calls once, `PREVIEW_DELAY_MS` after the last change (`schedule`), with the latest draft. The shell schedules on the
 *     draft's `previewFingerprint`, which leaves out the target fidelity: no number of the answer depends on it, so a level
 *     chosen or a figure typed for «Custom» asks nothing, and the request carries a fixed fidelity (`wireFidelity`);
 *   - while it waits, keeps the previous numbers, `stale`; an answer that lands while a newer change is still to be sent
 *     (queued, or in its pause) leaves it waiting: its numbers are already stale;
 *   - never sends while a call is on its way (one batch per user: a second call would be refused): a change made
 *     meanwhile waits for it, then the latest draft is sent once, so answers always come in order;
 *   - on a failure drops the numbers and keeps the reason: the first issue's code of an answer that cannot count,
 *     `incomplete` for a draft the request cannot carry yet, `unavailable` for the network, the tool error's code;
 *   - waits while a calculation runs (`blocked`): the Tools API admits one batch per user (`queue_full`, 429) and frees it
 *     only when the job ends on the server, not when the client stops waiting. So a calculation waits for the preview in
 *     flight (`busy`, `settled()`) instead of aborting it;
 *   - turns the euros typed for «Custom» (`setCustomEuros`) into the draft's λ on the total of a current answer: at once
 *     when the numbers on screen are current, else when the next answer lands, while the draft's choice is still «Custom»
 *     (§7.3: the draft keeps λ, a new total gives the euros back). The conversion lives here, not in the step, so a figure
 *     typed while the numbers are stale is converted on the fresh total even if the user leaves the step meanwhile.
 */
import {runTool} from '../../client';
import {assertToolAccount} from '../../contracts';
import {lambdaFromReferenceAmount, type FidelityLevelWeights} from './acceptableCost';
import type {PlannerDraft} from './draft.svelte';
import type {PlannerProfile} from './profile';
import {buildRequest, type PreviewLimitProblem} from './request';
import type {PlannerDescriptor} from './run.svelte';
import type {PlannerExactMoney, PlannerExactNumber} from './types';

/** The pause after the last change before the preview is asked. */
export const PREVIEW_DELAY_MS = 600;

/** An exact number and an exact amount of the wire, as the result views read them. */
export type PreviewNumber = PlannerExactNumber;
export type PreviewMoney = PlannerExactMoney;

/** The fields of a ready preview the planner reads (`RebalancerPreviewReadyResult`, `PacPreviewReadyResult`). */
export interface PreviewReady {
    operation: 'preview';
    result_state: 'preview_ready';
    availability: 'ready';
    valuation_currency: string;
    total: PreviewMoney;
    issues: {code: string}[];
    /** The limits' cross checks the plan would refuse, each on its target entry: the Targets step says them (R1-E). */
    limit_problems: PreviewLimitProblem[];
    /** Every target entry today, and «other cash» (the cash outside the entries, G5-2 of project 67). */
    items?: ({kind: 'asset'; asset_id: string; value: PreviewMoney; weight: PreviewNumber} | {kind: 'cash'; broker_id: string; currency: string; value: PreviewMoney; weight: PreviewNumber} | {kind: 'other_cash'; value: PreviewMoney; weight: PreviewNumber})[];
    /** The Rebalancer's: the λ of the three fidelity levels, the columns of the table «maximum acceptable cost». */
    fidelity_level_weights?: FidelityLevelWeights;
}

/** What one call answers: the service's result, or the Tools API's error for the item. */
export type PreviewAnswer = {kind: 'answer'; result: Record<string, unknown>} | {kind: 'tool_error'; code: string};

export interface PreviewDeps {
    call: (request: Record<string, unknown>, signal: AbortSignal) => Promise<PreviewAnswer>;
    /** True while a calculation runs: the preview waits. */
    blocked: () => boolean;
}

/** The real call, through the Tools API of the profile's Tool; an answer for another account session is dropped. */
export function toolPreviewCall(descriptor: () => PlannerDescriptor, profile: PlannerProfile, accountGeneration: () => number): PreviewDeps['call'] {
    let sequence = 0;
    return async (request, signal) => {
        const generation = accountGeneration();
        const item = await runTool(profile.toolCode, profile.contractVersion, {descriptor: descriptor(), correlationId: `${profile.correlationPrefix}-preview-${++sequence}`, parameters: request as never, signal});
        assertToolAccount(generation);
        if (item.status === 'success') return {kind: 'answer', result: item.result as unknown as Record<string, unknown>};
        return {kind: 'tool_error', code: item.error.code};
    };
}

export class PlannerPreview {
    state = $state<'idle' | 'waiting' | 'ready' | 'error'>('idle');
    /** The last good answer; `null` before the first one and after a failure. Raw: replaced whole. */
    numbers = $state.raw<PreviewReady | null>(null);
    /** Why there are no numbers (see the module notes); `null` when there are. */
    reason = $state<string | null>(null);
    /** The numbers on screen belong to an earlier draft: the next answer is on its way. */
    readonly stale = $derived(this.state === 'waiting' && this.numbers !== null);
    /** A preview call is on its way to the server. */
    busy = $state(false);

    #deps: PreviewDeps;
    #draft: PlannerDraft | null = null;
    #timer: ReturnType<typeof setTimeout> | null = null;
    #controller: AbortController | null = null;
    #sequence = 0;
    #customEuros: string | null = null;
    #inFlight: Promise<void> | null = null;
    /** A change arrived while a call was on its way: send the latest draft when it lands. */
    #queued = false;

    constructor(deps: PreviewDeps) {
        this.#deps = deps;
    }

    /** The draft changed: ask again after the pause, keeping the numbers on screen (stale) meanwhile. */
    schedule(draft: PlannerDraft): void {
        this.#draft = draft;
        this.state = 'waiting';
        this.#arm();
    }

    /**
     * «Custom»: the euros typed on the reference row become the draft's λ on the total of a current answer — now, when the
     * numbers on screen are current, else when the next answer lands. An empty text withdraws euros still waiting.
     */
    setCustomEuros(draft: PlannerDraft, euros: string): void {
        this.#draft = draft;
        this.#customEuros = euros.trim() === '' ? null : euros;
        if (this.state === 'ready' && this.numbers !== null) this.#convert(draft, this.numbers);
    }

    get customEuros(): string | null {
        return this.#customEuros;
    }

    /** Resolves once no preview call is on its way: a calculation waits for it (one batch per user). Never rejects. */
    settled(): Promise<void> {
        return this.#inFlight ?? Promise.resolve();
    }

    /** A newer draft is still to be sent: queued behind the call on its way, or in its pause after the last change. */
    get #pending(): boolean {
        return this.#queued || this.#timer !== null;
    }

    #arm(): void {
        if (this.#timer !== null) clearTimeout(this.#timer);
        this.#timer = setTimeout(() => this.#fire(), PREVIEW_DELAY_MS);
    }

    #fire(): void {
        // Called by the queue too: a pause armed meanwhile would send the same draft a second time.
        if (this.#timer !== null) clearTimeout(this.#timer);
        this.#timer = null;
        const draft = this.#draft;
        if (!draft) return;
        // A calculation is running: try again after the pause, without losing the change.
        if (this.#deps.blocked()) {
            this.#arm();
            return;
        }
        // One batch per user: never a second call while one runs; the latest draft goes when it lands.
        if (this.#inFlight !== null) {
            this.#queued = true;
            return;
        }
        const sequence = ++this.#sequence;
        const built = buildRequest(draft, new Date(), {operation: 'preview'});
        if (!built.ok) {
            this.#fail('incomplete');
            return;
        }
        const controller = new AbortController();
        this.#controller = controller;
        this.busy = true;
        const flight = this.#deps.call(built.built.request as unknown as Record<string, unknown>, controller.signal).then(
            (answer) => {
                if (sequence === this.#sequence) this.#apply(answer);
            },
            () => {
                if (sequence === this.#sequence && !controller.signal.aborted) this.#fail('unavailable');
            },
        );
        const settled = flight.finally(() => {
            if (this.#inFlight !== settled) return;
            this.#inFlight = null;
            this.busy = false;
            if (this.#queued) {
                this.#queued = false;
                this.#fire();
            }
        });
        this.#inFlight = settled;
    }

    #apply(answer: PreviewAnswer): void {
        this.#controller = null;
        if (answer.kind === 'tool_error') {
            this.#fail(answer.code);
            return;
        }
        const result = answer.result;
        if (result.result_state !== 'preview_ready') {
            const issues = (result.issues as {code: string}[] | undefined) ?? [];
            this.#fail(issues[0]?.code ?? String(result.result_state ?? 'unavailable'));
            return;
        }
        const ready = result as unknown as PreviewReady;
        this.numbers = ready;
        this.reason = null;
        // A newer draft waits to be sent: these numbers are already stale.
        this.state = this.#pending ? 'waiting' : 'ready';
        // Euros typed while the numbers were stale: converted on this answer's total, the latest draft's.
        if (this.state === 'ready' && this.#draft !== null) this.#convert(this.#draft, ready);
    }

    /**
     * The euros waiting become the draft's λ on `ready`'s total, only while its choice is still «Custom» (the user may have
     * picked a level meanwhile). A λ the plan's request cannot carry is not written: the step keeps «Custom» without one.
     */
    #convert(draft: PlannerDraft, ready: PreviewReady): void {
        const euros = this.#customEuros;
        if (euros === null) return;
        this.#customEuros = null;
        if (draft.data.fidelity.kind !== 'custom') return;
        const lambda = lambdaFromReferenceAmount(ready.total, euros) ?? '';
        if (draft.data.fidelity.lambda !== lambda) draft.data.fidelity = {kind: 'custom', lambda};
    }

    #fail(reason: string): void {
        this.numbers = null;
        this.reason = reason;
        this.state = this.#pending ? 'waiting' : 'error';
    }

    dispose(): void {
        this.#sequence += 1;
        this.#queued = false;
        if (this.#timer !== null) clearTimeout(this.#timer);
        this.#timer = null;
        this.#controller?.abort();
        this.#controller = null;
    }
}
