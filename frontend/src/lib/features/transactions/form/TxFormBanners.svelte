<!--
  TxFormBanners — the inline banners of the form: commit failure, validation result, issues, partner loading.

  Cut from TransactionFormModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {resolveIssueMessage, type ResolverContext} from '$lib/features/transactions/resolveValidationMessage';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';
    import type {ValidationIssue} from './txFormTypes';

    interface Props {
        getBulkContext: (() => {creates: Record<string, unknown>[]; updates: Record<string, unknown>[]; deletes: number[]}) | undefined;
        commitFailed: boolean;
        formError: string | null;
        issues: ValidationIssue[];
        issuesDismissed: boolean;
        loadingPartner: boolean;
        balanceIssues: ValidationIssue[];
        dualValidationError: string | null;
        fieldIssues: ValidationIssue[];
        resolverCtx: ResolverContext;
        showIssuesBanner: boolean;
        handleSyncFx: () => Promise<void>;
    }

    let {getBulkContext, commitFailed = $bindable(), formError = $bindable(), issues, issuesDismissed = $bindable(), loadingPartner, balanceIssues, dualValidationError, fieldIssues, resolverCtx, showIssuesBanner, handleSyncFx}: Props = $props();
</script>

<!-- Inline banners: red ⛔ for commit failure, green ✓ for valid,
     yellow for validate issues. Both error types show categorized lists. -->
{#if formError}
    <InfoBanner variant="error" dismissible ondismiss={() => (formError = null)}>
        <p class="font-semibold mb-1" data-testid="tx-form-error">⛔ {$t('common.saveCancelled')}</p>
        <p>{formError}</p>
    </InfoBanner>
{:else if commitFailed && issues.length > 0}
    <InfoBanner variant="error" dismissible ondismiss={() => (commitFailed = false)}>
        <p class="font-semibold mb-1" data-testid="tx-form-error">⛔ {$t('common.saveCancelled')}</p>
        {#if fieldIssues.length > 0}
            <p class="font-semibold text-sm mt-2 mb-1">{$t('transactions.validate.issuesHeader')}</p>
            <ul class="list-disc list-inside space-y-0.5 text-sm" data-testid="tx-form-issues">
                {#each fieldIssues as issue}
                    <li data-testid="tx-form-issue" data-code={issue.code}>{@html sanitizeHtml(resolveIssueMessage(issue, $t, resolverCtx))}</li>
                {/each}
            </ul>
        {/if}
        {#if balanceIssues.length > 0}
            <p class="font-semibold text-sm mt-2 mb-1">{$t('transactions.validate.balanceIssuesHeader')}</p>
            <ul class="list-disc list-inside space-y-0.5 text-sm" data-testid="tx-form-balance-issues">
                {#each balanceIssues as issue}
                    <li data-testid="tx-form-balance-issue" data-code={issue.code}>{@html sanitizeHtml(resolveIssueMessage(issue, $t, resolverCtx))}</li>
                {/each}
            </ul>
        {/if}
    </InfoBanner>
{:else if dualValidationError}
    <InfoBanner variant="warning">
        <p data-testid="tx-form-dual-error">⚠ {dualValidationError}</p>
    </InfoBanner>
{:else if showIssuesBanner}
    <InfoBanner variant="warning" dismissible ondismiss={() => (issuesDismissed = true)}>
        {#if fieldIssues.length > 0}
            <p class="font-semibold text-sm mb-1.5" data-testid="tx-form-issues-header">{getBulkContext ? $t('transactions.validate.contextualIssuesHeader') : $t('transactions.validate.issuesHeader')}</p>
            <ul class="list-disc list-inside space-y-0.5 text-sm" data-testid="tx-form-issues">
                {#each fieldIssues as issue}
                    {#if issue.code === 'wacFxUnavailable'}
                        <li data-testid="tx-form-issue" data-code={issue.code} class="flex flex-wrap items-center gap-1.5">
                            <span>{$t('transactions.errors.wacFxUnavailable')}</span>
                            <button
                                type="button"
                                class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded
                                    bg-lf-selected text-lf-link hover:bg-lf-checked/20
                                    transition-colors"
                                onclick={handleSyncFx}
                                data-testid="tx-form-sync-fx-link"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                                    ><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" /><path d="M21 3v5h-5" /><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" /><path d="M8 16H3v5" /></svg
                                >
                                {$t('transactions.errors.wacFxUnavailableSyncLink')}
                            </button>
                            <span>{$t('transactions.errors.wacFxUnavailableOrManual')}</span>
                        </li>
                    {:else}
                        <li data-testid="tx-form-issue" data-code={issue.code}>{@html sanitizeHtml(resolveIssueMessage(issue, $t, resolverCtx))}</li>
                    {/if}
                {/each}
            </ul>
        {/if}
        {#if balanceIssues.length > 0}
            <p class="font-semibold text-sm {fieldIssues.length > 0 ? 'mt-2' : ''} mb-1.5">{$t('transactions.validate.balanceIssuesHeader')}</p>
            <ul class="list-disc list-inside space-y-0.5 text-sm" data-testid="tx-form-balance-issues">
                {#each balanceIssues as issue}
                    <li data-testid="tx-form-balance-issue" data-code={issue.code}>{@html sanitizeHtml(resolveIssueMessage(issue, $t, resolverCtx))}</li>
                {/each}
            </ul>
        {/if}
    </InfoBanner>
{/if}

<!-- Loading partner indicator (dual-form edit) -->
{#if loadingPartner}
    <InfoBanner variant="info">
        <p class="text-sm">{$t('transactions.form.loadingPartner')}</p>
    </InfoBanner>
{/if}
