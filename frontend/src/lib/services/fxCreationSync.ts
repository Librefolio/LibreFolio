import {get} from 'svelte/store';
import {zodiosApi} from '$lib/api';
import {_} from '$lib/i18n';
import {isClientSessionCurrent} from '$lib/stores/app/clientSession';
import {notify} from '$lib/stores/app/notify.svelte';
import {getFxStore} from '$lib/stores/fxStoreRegistry';
import {invalidateFxRoutes} from '$lib/stores/reference/fxRoutesStore';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {formatSyncDetail, fxPairHtml} from '$lib/utils/providerHelpers';
import {buildFxSyncToast, type SyncToastResult} from '$lib/utils/sync/syncToastHelpers';
import {extractErrorMessage} from '$lib/utils/trySave';

type FxSyncResponse = Awaited<ReturnType<typeof zodiosApi.sync_rates_api_v1_fx_currencies_sync_post>>;
type FxSyncResult = FxSyncResponse['results'][number];

export interface FxPairCreatedDetail {
    readonly base: string;
    readonly quote: string;
    readonly hasRealProvider: boolean;
    readonly slug: string;
    readonly autoSyncStarted: boolean;
}

export interface FxPairSyncCompleteDetail extends FxPairCreatedDetail {
    readonly pairs: readonly string[];
    readonly start: string;
    readonly end: string;
    readonly sessionGeneration: number;
    readonly outcome: 'ok' | 'partial' | 'failed' | 'skipped' | 'transport-error';
    readonly results: readonly FxSyncResult[];
    readonly missingPairs: readonly string[];
}

export interface FxPairCreationContext {
    readonly detail: FxPairCreatedDetail;
    readonly pairs: readonly string[];
    readonly start: string;
    readonly end: string;
    readonly sessionGeneration: number;
    readonly editMode?: boolean;
    readonly oncreated?: (detail: FxPairCreatedDetail) => void | Promise<void>;
    readonly onsynced?: (detail: FxPairSyncCompleteDetail) => void | Promise<void>;
    readonly onclose?: () => void;
}

type FxCreationSyncListener = (detail: FxPairSyncCompleteDetail) => void | Promise<void>;
const completionListeners = new Set<FxCreationSyncListener>();

export function subscribeFxCreationSyncCompleted(listener: FxCreationSyncListener): () => void {
    completionListeners.add(listener);
    return () => completionListeners.delete(listener);
}

function joinedText(value: string | null | (string | null)[] | undefined): string {
    return Array.isArray(value) ? value.filter((part): part is string => part !== null).join('; ') : (value ?? '');
}

function formatResult(result: FxSyncResult | undefined, slug: string): SyncToastResult {
    const tr = get(_);
    const normalized = result
        ? {
              ...result,
              provider_used: joinedText(result.provider_used),
              message: escapeHtml(joinedText(result.message) || result.errors?.join('; ') || ''),
              detail: (result.detail ?? [])
                  .flatMap((leg) => (Array.isArray(leg) ? leg : leg ? [leg] : []))
                  .map((leg) => ({
                      provider: escapeHtml(leg.provider),
                      leg: escapeHtml(leg.leg),
                      dates_available: leg.dates_available ?? 0,
                      error: escapeHtml(joinedText(leg.error)),
                  })),
          }
        : {status: 'failed', message: escapeHtml(tr('prices.sync.noResponse'))};
    return buildFxSyncToast(normalized, slug, tr, undefined, formatSyncDetail, {outerFlags: true, linkToDetail: true});
}

/**
 * Finish a committed configuration without retaining the modal's reactive draft.
 * Browser-lifetime only: closing the modal is supported, closing the tab is not.
 */
export async function finishFxPairCreation(context: FxPairCreationContext): Promise<void> {
    const {sessionGeneration, start, end, oncreated, onsynced, onclose, editMode = false} = context;
    const detail = Object.freeze({...context.detail, autoSyncStarted: !editMode && context.detail.hasRealProvider && !!start && !!end && context.detail.autoSyncStarted});
    const pairs = Object.freeze([...new Set([detail.slug, ...context.pairs])]);
    const current = () => isClientSessionCurrent(sessionGeneration);
    if (typeof window === 'undefined' || !current()) return;

    const callbackErrors: Array<{phase: 'creation' | 'close' | 'completion'; message: string}> = [];
    const recordCallbackError = (phase: 'creation' | 'close' | 'completion', error: unknown) => {
        callbackErrors.push({phase, message: extractErrorMessage(error, get(_)('common.error'))});
    };
    // Attach rejection handling immediately, even if sync finishes much later.
    let creationRefresh: Promise<void>;
    try {
        creationRefresh = Promise.resolve(oncreated?.(detail)).catch((error: unknown) => recordCallbackError('creation', error));
    } catch (error) {
        recordCallbackError('creation', error);
        creationRefresh = Promise.resolve();
    }
    if (!current()) return;
    try {
        onclose?.();
    } catch (error) {
        recordCallbackError('close', error);
    }
    if (!current()) return;
    invalidateFxRoutes();
    notify({name: editMode ? 'fx.pair.updated' : 'fx.pair.created', detail: {...detail, pairs, sessionGeneration}});

    const refreshFailureMessage = () => {
        const tr = get(_);
        return `${tr('common.refresh')} — ${callbackErrors.map(({message}) => escapeHtml(message)).join('; ')}`;
    };
    if (editMode || !detail.autoSyncStarted) {
        if (!editMode) {
            const tr = get(_);
            notify({
                name: 'fx.pair.creation-completed',
                detail: {...detail, pairs, sessionGeneration},
                toast: {variant: 'success', message: `${tr('common.created')}:\n${fxPairHtml(detail.slug, {outerFlags: true, linkToDetail: true})}`},
            });
        }
        await creationRefresh;
        if (current() && callbackErrors.length > 0) {
            notify({
                name: 'fx.pair.refresh-failed',
                detail: {...detail, pairs, sessionGeneration, configurationSaved: true, callbackErrors},
                toast: {variant: 'warning', message: `${fxPairHtml(detail.slug, {outerFlags: true, linkToDetail: true})}\n${refreshFailureMessage()}`},
            });
        }
        return;
    }

    let response: FxSyncResponse | undefined;
    let transportError: string | undefined;
    try {
        response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({pairs: [...pairs], start, end});
    } catch (error) {
        transportError = extractErrorMessage(error, get(_)('prices.sync.failedDefault'));
    }
    if (!current()) return;
    for (const slug of pairs) getFxStore(slug).invalidateAll();
    // A pre-sync refresh must settle before the final invalidation/refetch.
    await creationRefresh;
    if (!current()) return;
    for (const slug of pairs) getFxStore(slug).invalidateAll();

    const results = response?.results ?? [];
    const requestedResults = pairs.map((slug) => results.find((result) => result.pair === slug));
    const missingPairs = pairs.filter((_, index) => !requestedResults[index]);
    const operationErrors = response?.errors ?? [];
    const outcome: FxPairSyncCompleteDetail['outcome'] = transportError
        ? 'transport-error'
        : missingPairs.length > 0 || operationErrors.length > 0 || requestedResults.some((result) => result?.status === 'failed')
          ? 'failed'
          : requestedResults.every((result) => result?.status === 'skipped')
            ? 'skipped'
            : requestedResults.some((result) => result?.status !== 'ok')
              ? 'partial'
              : 'ok';
    const completion: FxPairSyncCompleteDetail = {...detail, pairs, start, end, sessionGeneration, outcome, results, missingPairs};
    const listenerResults = await Promise.allSettled(
        [...completionListeners].map((listener) => {
            if (!current()) return Promise.resolve();
            try {
                return Promise.resolve(listener(completion));
            } catch (error) {
                return Promise.reject(error);
            }
        }),
    );
    for (const result of listenerResults) {
        if (result.status === 'rejected') recordCallbackError('completion', result.reason);
    }
    if (!current()) return;
    try {
        await onsynced?.(completion);
    } catch (error) {
        recordCallbackError('completion', error);
    }
    if (!current()) return;

    const formatted = requestedResults.map((result, index) => formatResult(result, pairs[index]));
    let variant: SyncToastResult['variant'] = outcome === 'ok' ? 'success' : outcome === 'skipped' ? 'info' : outcome === 'partial' ? 'warning' : 'error';
    let message = formatted.map((item) => item.message).join('\n\n');
    if (transportError) {
        message = buildFxSyncToast({status: 'failed', message: escapeHtml(transportError)}, detail.slug, get(_), undefined, undefined, {outerFlags: true, linkToDetail: true}).message;
    } else if (operationErrors.length > 0) {
        message += `\n${operationErrors.map(escapeHtml).join('; ')}`;
    }
    if (callbackErrors.length > 0) {
        if (variant === 'success' || variant === 'info') variant = 'warning';
        message += `\n${refreshFailureMessage()}`;
    }
    notify({
        name: 'fx.pair.creation-sync-completed',
        detail: {...completion, configurationSaved: true, callbackErrors, ...(transportError ? {transportError} : {}), operationErrors},
        toast: {variant, message},
    });
}
