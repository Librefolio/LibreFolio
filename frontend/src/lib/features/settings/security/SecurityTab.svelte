<!--
  The «Security» tab of the admin settings (lot A8b): the configuration checks of the instance
  (`GET /security/checks`) and the browser's own, most severe first, with a link where a setting of the app fixes
  them; the passed checks folded below. Colours are roles only, after the state convention of `STATUS_TONES`, written
  here: a tint per severity (`bg-lf-X-soft text-lf-X-on-soft border-lf-X-line`), a neutral chip for the count of the
  passed ones. Each row whose check has a page in the administrator's guide (`checkGuides.ts`, workstream H) carries a
  «Guide» button to it (N69d); a check the map lacks has none.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {AlertCircle, AlertTriangle, CheckCircle2, Info, RefreshCw} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {checkGuidePath} from '$lib/features/instance/checkGuides';
    import {securityChecks, type SecurityChecksStore} from './securityChecks.svelte';
    import type {FindingSeverity} from './securityFindings';

    interface Props {
        /** The state to show: the shared one, which the badge reads too, unless a test hands its own. */
        checks?: SecurityChecksStore;
    }

    let {checks = securityChecks}: Props = $props();

    const FINDING_CLASSES: Record<FindingSeverity, string> = {
        error: 'flex items-start gap-3 rounded-lg border border-lf-danger-line bg-lf-danger-soft px-4 py-3 text-sm text-lf-danger-on-soft',
        warning: 'flex items-start gap-3 rounded-lg border border-lf-warning-line bg-lf-warning-soft px-4 py-3 text-sm text-lf-warning-on-soft',
        info: 'flex items-start gap-3 rounded-lg border border-lf-info-line bg-lf-info-soft px-4 py-3 text-sm text-lf-info-on-soft',
    };

    const ICON_CLASSES: Record<FindingSeverity, string> = {
        error: 'mt-0.5 h-4 w-4 shrink-0 text-lf-danger',
        warning: 'mt-0.5 h-4 w-4 shrink-0 text-lf-warning',
        info: 'mt-0.5 h-4 w-4 shrink-0 text-lf-info',
    };

    const ICONS = {error: AlertCircle, warning: AlertTriangle, info: Info};

    /** Whole keys, so the i18n audit sees each one. */
    const SEVERITY_LABEL_KEYS: Record<FindingSeverity, string> = {
        error: 'settings.securityTab.severity.error',
        warning: 'settings.securityTab.severity.warning',
        info: 'settings.securityTab.severity.info',
    };

    const findings = $derived(checks.findings);
    const loading = $derived(checks.status === 'loading');

    onMount(() => {
        void checks.ensureLoaded();
    });
</script>

{#snippet guide(checkId: string)}
    {@const path = checkGuidePath(checkId)}
    {#if path}
        <span class="shrink-0 [&_button]:text-inherit">
            <DocsLink icon="book" label={$_('settings.securityTab.guide')} labelDisplay="visible" {path} size={14} testId="security-guide" />
        </span>
    {/if}
{/snippet}

<div class="space-y-6 text-lf-primary" data-testid="security-tab" data-status={checks.status} data-busy={loading} aria-busy={loading}>
    <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
            <h2 class="text-lg font-semibold text-lf-primary">{$_('settings.securityTab.title')}</h2>
            <p class="mt-1 text-sm text-lf-muted">{$_('settings.securityTab.description')}</p>
        </div>
        <button
            type="button"
            class="inline-flex shrink-0 items-center gap-2 rounded-lg border border-lf-input px-3 py-2 text-sm font-medium text-lf-secondary hover:bg-lf-hover disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="security-refresh"
            disabled={loading}
            onclick={() => void checks.reload()}
        >
            <RefreshCw class={loading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} aria-hidden="true" />
            {$_('settings.securityTab.refresh')}
        </button>
    </div>

    {#if checks.status === 'error'}
        <div class={FINDING_CLASSES.error} role="alert" data-testid="security-load-error">
            <AlertCircle class={ICON_CLASSES.error} aria-hidden="true" />
            <p class="flex-1">{$_('settings.securityTab.loadError')}</p>
            <button type="button" class="shrink-0 font-medium underline" data-testid="security-retry" onclick={() => void checks.reload()}>
                {$_('settings.securityTab.retry')}
            </button>
        </div>
    {/if}

    {#if !checks.answered}
        {#if loading || checks.status === 'idle'}
            <div class="space-y-2" data-testid="security-loading" aria-busy="true">
                <div class="h-12 animate-pulse rounded-lg bg-lf-neutral"></div>
                <div class="h-12 animate-pulse rounded-lg bg-lf-neutral"></div>
            </div>
        {/if}
    {:else}
        {#if findings.attention.length > 0}
            <ul class="space-y-2">
                {#each findings.attention as finding (finding.id)}
                    {@const Icon = ICONS[finding.severity]}
                    <li class={FINDING_CLASSES[finding.severity]} data-testid="security-finding" data-check-id={finding.id} data-severity={finding.severity}>
                        <Icon class={ICON_CLASSES[finding.severity]} aria-hidden="true" />
                        <p class="flex-1">
                            <span class="sr-only">{$_(SEVERITY_LABEL_KEYS[finding.severity])}:</span>
                            {$_(finding.messageKey, {values: finding.params})}
                            {#if finding.action}
                                <a href={finding.action.href} class="ml-1 font-medium underline" data-testid="security-finding-action">{$_(finding.action.labelKey)}</a>
                            {/if}
                        </p>
                        {@render guide(finding.id)}
                    </li>
                {/each}
            </ul>
        {:else}
            <div class="flex items-start gap-3 rounded-lg border border-lf-success-line bg-lf-success-soft px-4 py-3 text-sm text-lf-success-on-soft" data-testid="security-all-clear">
                <CheckCircle2 class="mt-0.5 h-4 w-4 shrink-0 text-lf-success" aria-hidden="true" />
                <p class="flex-1">{$_('settings.securityTab.allClear')}</p>
            </div>
        {/if}

        {#if findings.passed.length > 0}
            <details class="rounded-lg border border-lf-subtle" data-testid="security-passed">
                <summary class="flex cursor-pointer items-center gap-2 px-4 py-3 text-sm font-medium text-lf-secondary">
                    <span class="rounded-full bg-lf-neutral px-2 py-0.5 text-xs text-lf-secondary">{findings.passed.length}</span>
                    {$_('settings.securityTab.passed', {values: {count: findings.passed.length}})}
                </summary>
                <ul class="space-y-1 border-t border-lf-subtle px-4 py-3 text-sm text-lf-muted">
                    {#each findings.passed as finding (finding.id)}
                        <li class="flex items-start gap-2" data-testid="security-passed-check" data-check-id={finding.id}>
                            <CheckCircle2 class="mt-0.5 h-4 w-4 shrink-0 text-lf-success" aria-hidden="true" />
                            <span class="flex-1">{$_(finding.messageKey, {values: finding.params})}</span>
                            {@render guide(finding.id)}
                        </li>
                    {/each}
                </ul>
            </details>
        {/if}
    {/if}
</div>
