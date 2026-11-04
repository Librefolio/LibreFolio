/**
 * commitRefusal.ts — what the user reads when a commit started outside the workspace is refused.
 *
 * The Transactions page commits a Split pair or a Promote pair at once (`commitTransactions`, which shows
 * no toast of its own). A refusal used to reach only the console (W-B39): this composes the error toast
 * instead, the action's title and then each distinct reason, translated as the form and bulk banners
 * translate them (`resolveIssueMessage`).
 *
 * @module features/transactions/commitRefusal
 */

import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {resolveIssueMessage, type ResolverContext} from './resolveValidationMessage';
import type {CommitResult} from './txCommitApi';

type Translate = (key: string, opts?: {values?: Record<string, any>}) => string;

/**
 * The message of the error toast for a refused commit: `title`, then one line per distinct reason.
 *
 * The reasons are the issues resolved by `resolveIssueMessage` (HTML, every input escaped), in their
 * order and without repeats; with no issue, the network error, if any and other than the title (the
 * page's fallback message is the title itself); with neither, the title alone.
 * The toast keeps the line breaks (`whitespace-pre-line`) and sanitises the HTML.
 */
export function commitRefusalMessage(result: Pick<CommitResult, 'issues' | 'networkError'>, title: string, t: Translate, ctx?: ResolverContext): string {
    const reasons = [...new Set(result.issues.map((issue) => resolveIssueMessage(issue, t, ctx)))];
    if (reasons.length === 0 && result.networkError && result.networkError !== title) reasons.push(escapeHtml(result.networkError));
    const head = escapeHtml(title);
    return reasons.length === 0 ? head : `${head}\n${reasons.map((reason) => `• ${reason}`).join('\n')}`;
}
