/**
 * txCommitApi.ts — Centralized wrapper for transaction commit/validate API calls.
 *
 * Provides a uniform interface for all transaction batch operations:
 * - Always uses `trySave` internally (unified error extraction, never throws)
 * - Normalizes the response into `CommitResult`
 * - Filters internal `extra_forbidden` errors (FE bugs — logged, not shown)
 * - Default `toast: false` — callers handle errors inline
 *
 * @module utils/txCommitApi
 */

import {zodiosApi} from '$lib/api';
import {trySave, extractValidationIssues} from '$lib/utils/trySave';
import type {TrySaveOptions} from '$lib/utils/trySave';

// =============================================================================
//  Types
// =============================================================================

/** Validation issue from the backend (normalized shape). */
export interface TxValidationIssue {
    operation?: string;
    index?: number;
    ref_id?: number | null;
    error: string;
    code?: string;
    params?: Record<string, unknown>;
    loc?: string;
}

/** Unified result from commitTransactions / validateTransactions. */
export interface CommitResult {
    /** True if the batch was committed successfully. */
    committed: boolean;
    /** Validation/business-rule issues (empty if committed=true). */
    issues: TxValidationIssue[];
    /** Per-operation results (IDs created, etc.) — only on successful commit. */
    results?: Array<{ids?: number[]; operation?: string; index?: number; status?: string}>;
    /** Set only on network/HTTP error (trySave returned status='error'). */
    networkError?: string;
    /** Raw response body for callers that need extra fields. */
    rawResponse: unknown;
}

export interface CommitOptions {
    /** Fallback error message (i18n-translated string). Default: 'Save failed'. */
    fallback?: string;
    /** Show toast on network error? Default: false. */
    toast?: boolean;
}

// =============================================================================
//  Implementation
// =============================================================================

/**
 * Call POST /transactions/commit with unified error handling.
 *
 * - Uses `trySave` internally (never throws)
 * - On network error → `CommitResult.networkError` is set, `committed=false`
 * - On `committed=false` from backend → issues are extracted and normalized
 * - Filters `extra_forbidden` issues (internal FE bugs — logged to console)
 */
export async function commitTransactions(payload: Record<string, unknown>, opts?: CommitOptions): Promise<CommitResult> {
    const trySaveOpts: TrySaveOptions = {
        fallback: opts?.fallback ?? 'Save failed',
        toast: opts?.toast ?? false,
    };

    const result = await trySave(() => zodiosApi.commit_transactions_api_v1_transactions_commit_post(payload as never), trySaveOpts);

    if (result.status === 'error') {
        // Network / HTTP error — try to extract validation issues from 422
        const extracted = extractValidationIssues(result.error);
        const issues: TxValidationIssue[] = extracted.map((iss) => ({
            error: iss.msg,
            code: iss.code,
            params: iss.params,
            loc: iss.loc,
        }));
        return {
            committed: false,
            issues,
            networkError: result.message,
            rawResponse: null,
        };
    }

    // Success HTTP — parse response
    const resp = result.data as {committed?: boolean; issues?: TxValidationIssue[]; results?: CommitResult['results']};
    const rawIssues = resp.issues ?? [];

    // Filter extra_forbidden errors (FE bugs) — log and hide from user
    const internalErrors = rawIssues.filter((i) => i.code === 'extra_forbidden');
    if (internalErrors.length > 0) {
        // eslint-disable-next-line no-console
        console.error('[commitTransactions] Internal extra_forbidden errors (FE bug):', internalErrors);
    }
    const userIssues = rawIssues.filter((i) => i.code !== 'extra_forbidden');

    return {
        committed: resp.committed ?? false,
        issues: userIssues,
        results: resp.results,
        rawResponse: resp,
    };
}

/**
 * Call POST /transactions/validate with unified error handling.
 *
 * Same contract as `commitTransactions` but hits the validate endpoint
 * (dry-run, never persists). Used for real-time validation feedback.
 */
export async function validateTransactions(payload: Record<string, unknown>, opts?: CommitOptions): Promise<CommitResult> {
    const trySaveOpts: TrySaveOptions = {
        fallback: opts?.fallback ?? 'Validation failed',
        toast: opts?.toast ?? false,
    };

    const result = await trySave(() => zodiosApi.validate_transactions_api_v1_transactions_validate_post(payload as never), trySaveOpts);

    if (result.status === 'error') {
        const extracted = extractValidationIssues(result.error);
        const issues: TxValidationIssue[] = extracted.map((iss) => ({
            error: iss.msg,
            code: iss.code,
            params: iss.params,
            loc: iss.loc,
        }));
        return {
            committed: false,
            issues,
            networkError: result.message,
            rawResponse: null,
        };
    }

    const resp = result.data as {committed?: boolean; issues?: TxValidationIssue[]};
    return {
        committed: resp.committed ?? true,
        issues: resp.issues ?? [],
        rawResponse: resp,
    };
}
