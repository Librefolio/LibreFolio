/**
 * One explicit read of the domain snapshot for a copy dialog (B2, Q-C0-6).
 *
 * The dialog previews exactly the snapshot it will apply. A newer read
 * replaces an older one; a stopped or superseded read is dropped.
 */
import {ToolClientError} from '../../contracts';
import {toolErrorMessage} from '../../presentation';
import {fetchPlannerSource, isPlannerSourceError, isStoppedWait, type PlannerSource, type SourceQuery} from './source';

export interface SourceLoadError {
    key: string;
    fallback: string;
}

const REFUSALS: Record<string, SourceLoadError> = {
    broker_forbidden: {key: 'tools.pacAllocator.planner.source.errors.brokerForbidden', fallback: 'The Portfolio API refused a Broker (403): only Brokers you own can be copied.'},
    asset_not_found: {key: 'tools.pacAllocator.planner.source.errors.assetNotFound', fallback: 'The Portfolio API did not find an Asset (404). Nothing was copied.'},
};

export class SourceLoad {
    status = $state<'idle' | 'loading' | 'ready' | 'error'>('idle');
    data = $state<PlannerSource | null>(null);
    error = $state<SourceLoadError | null>(null);

    #controller: AbortController | null = null;
    #sequence = 0;

    async load(query: SourceQuery, accountGeneration: number): Promise<PlannerSource | null> {
        this.#controller?.abort();
        const sequence = ++this.#sequence;
        const controller = new AbortController();
        this.#controller = controller;
        this.status = 'loading';
        this.error = null;
        this.data = null;
        try {
            const data = await fetchPlannerSource(query, accountGeneration, controller.signal);
            if (sequence !== this.#sequence) return null;
            this.data = data;
            this.status = 'ready';
            return data;
        } catch (caught) {
            if (sequence !== this.#sequence) return null;
            if (isStoppedWait(caught)) {
                this.status = 'idle';
                return null;
            }
            this.status = 'error';
            if (isPlannerSourceError(caught)) this.error = REFUSALS[caught.code];
            else this.error = toolErrorMessage(caught instanceof ToolClientError ? caught : new ToolClientError('internal', 'unexpected_ui_error'));
            return null;
        } finally {
            if (sequence === this.#sequence) this.#controller = null;
        }
    }

    stop(): void {
        this.#sequence += 1;
        this.#controller?.abort();
        this.#controller = null;
        if (this.status === 'loading') this.status = 'idle';
    }
}
