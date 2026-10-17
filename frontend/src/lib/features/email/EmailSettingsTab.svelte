<!--
  Settings › Administration › Email, for administrators (workstream E, lots E2 and E3): the state of the instance's email, the
  configuration checks worth a word, the hourly budget, a test email to one's own address, and the base of the emailed
  links checked from this browser (developer decision 45).

  The SMTP configuration itself never reaches the browser (F04): `GET /email/status` gives the state, the problem and
  the variable at fault, the checks (an i18n key and its parameters), the budget and the links' base. Colours are roles
  only (theme-roles skill): every class is a whole literal in `emailText.ts` or here.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {Mail, RefreshCw, Send} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {fetchEmailStatus, issueProbeNonce, readTestFailure, sendTestEmail, type EmailCheck, type EmailStatus, type EmailTestFailure} from './emailApi';
    import {probeEmailLinks, type LinksProbeState} from './emailLinks';
    import {LINKS_PROBE_CLASSES, LINKS_PROBE_KEYS, linksProbeWarns, minutesUntil, NOTICE_CLASSES, OUTCOME_CLASSES, problemKey, STATE_BADGE_CLASSES, STATE_LABEL_KEYS, testFailureMessage} from './emailText';

    let status = $state<EmailStatus | null>(null);
    let loading = $state(true);
    let loadFailed = $state(false);
    let sending = $state(false);
    /** The last test's outcome; its text is rendered from it, so it follows a change of language. */
    let outcome = $state<{kind: 'sent'} | {kind: 'failed'; failure: EmailTestFailure} | null>(null);

    /** The checks worth a line: not `ok`, and not `email.smtp`, whose problem the state already explains. */
    const notices = $derived((status?.checks ?? []).filter((check: EmailCheck) => check.severity !== 'ok' && check.check_id !== 'email.smtp'));
    /** A request in flight: the status, or the test email. */
    const busy = $derived(loading || sending);

    /** Only the latest read writes: an older answer never replaces a newer one, nor ends its `loading`. */
    let loadGeneration = 0;

    /** The base of the emailed links, when emails with a link can go out: the address the browser checks. */
    const linksBase = $derived(status?.state === 'ready' && status.links.ready ? status.links.base : null);
    /** The check of `linksBase` from this browser: null until there is a base to check. */
    let linksProbe = $state<LinksProbeState | null>(null);
    /** The base checked last: a new read of the state (after a test email) does not check the same base again. */
    let probedBase: string | null = null;
    /** Only the latest check writes: «Check again», a new base or leaving the tab drops an older one. */
    let probeGeneration = 0;

    async function checkLinks(base: string): Promise<void> {
        const generation = ++probeGeneration;
        probedBase = base;
        linksProbe = 'checking';
        const outcome = await probeEmailLinks(base, {pageProtocol: window.location.protocol, issueNonce: issueProbeNonce});
        if (generation !== probeGeneration) return;
        linksProbe = outcome;
        notify({name: 'email.links.checked', detail: {outcome}});
    }

    function checkLinksAgain(): void {
        if (linksBase !== null) void checkLinks(linksBase);
    }

    $effect(() => {
        const base = linksBase;
        if (base === null) {
            probedBase = null;
            linksProbe = null;
            return;
        }
        if (base !== probedBase) void checkLinks(base);
        return () => {
            probeGeneration++;
        };
    });

    async function load(): Promise<void> {
        const generation = ++loadGeneration;
        loading = true;
        try {
            const next = await fetchEmailStatus();
            if (generation !== loadGeneration) return;
            status = next;
            loadFailed = false;
        } catch {
            if (generation === loadGeneration) loadFailed = true;
        } finally {
            if (generation === loadGeneration) loading = false;
        }
    }

    async function sendTest(): Promise<void> {
        if (busy) return;
        sending = true;
        outcome = null;
        try {
            const result = await sendTestEmail();
            outcome = {kind: 'sent'};
            notify({name: 'email.test.sent', detail: {language: result.language}});
        } catch (error) {
            const failure = readTestFailure(error);
            outcome = {kind: 'failed', failure};
            notify({name: 'email.test.failed', detail: {...failure}});
        } finally {
            sending = false;
        }
        await load();
    }

    onMount(() => {
        void load();
    });
</script>

<section class="space-y-6 text-lf-primary" data-testid="email-tab" data-busy={busy ? 'true' : 'false'} aria-busy={busy}>
    <header class="flex items-start justify-between gap-4">
        <div class="space-y-1">
            <h2 class="flex items-center gap-2 text-lg font-semibold">
                <Mail class="h-5 w-5 text-lf-link" aria-hidden="true" />
                {$_('email.tab.title')}
            </h2>
            <p class="text-sm text-lf-secondary">{$_('email.tab.intro')}</p>
        </div>
        <DocsLink path="admin/email/" label={$_('common.documentation')} icon="book" size={18} testId="email-docs" />
    </header>

    {#if loadFailed}
        <p class={NOTICE_CLASSES.error} role="alert" data-testid="email-load-error">{$_('email.loadError')}</p>
    {/if}
    {#if status}
        <div class="space-y-3 rounded-lg border border-lf-subtle bg-lf-card p-4" data-testid="email-state" data-state={status.state}>
            <span class={STATE_BADGE_CLASSES[status.state]} data-testid="email-state-badge">{$_(STATE_LABEL_KEYS[status.state])}</span>
            {#if status.state === 'off'}
                <p class="text-sm text-lf-secondary" data-testid="email-off-explanation">{$_('email.off.explanation')}</p>
            {:else if status.state === 'invalid'}
                <p class="text-sm font-medium text-lf-danger" data-testid="email-problem" data-problem={status.problem ?? ''} data-variable={status.variable ?? ''}>
                    {$_(problemKey(status.problem), {values: {variable: status.variable ?? ''}})}
                </p>
                <p class="text-sm text-lf-secondary">{$_('email.invalid.explanation')}</p>
            {:else if status.budget}
                {#if status.budget.remaining > 0}
                    <p class="text-sm text-lf-secondary" data-testid="email-budget" data-remaining={status.budget.remaining} data-max={status.budget.max_per_hour}>
                        {$_('email.budget.remaining', {values: {remaining: status.budget.remaining, max: status.budget.max_per_hour}})}
                    </p>
                {:else}
                    <p class="text-sm text-lf-warning" data-testid="email-budget" data-remaining="0" data-max={status.budget.max_per_hour}>
                        {$_('email.budget.spent', {values: {max: status.budget.max_per_hour, minutes: minutesUntil(status.budget.retry_after_seconds)}})}
                    </p>
                {/if}
            {/if}
        </div>

        {#if notices.length > 0}
            <ul class="space-y-2" data-testid="email-checks">
                {#each notices as check (check.check_id)}
                    <li class={NOTICE_CLASSES[check.severity === 'ok' ? 'info' : check.severity]} data-testid="email-check" data-check-id={check.check_id} data-severity={check.severity}>
                        {$_(check.i18n_key, {values: check.detail})}
                    </li>
                {/each}
            </ul>
        {/if}

        {#if linksBase !== null}
            <div class="space-y-2" data-testid="email-links" data-base={linksBase} data-busy={linksProbe === 'checking' ? 'true' : 'false'} aria-busy={linksProbe === 'checking'}>
                <p class="text-sm text-lf-secondary" data-testid="email-links-base">{$_('email.links.base', {values: {base: linksBase}})}</p>
                {#if linksProbe !== null}
                    <p class={LINKS_PROBE_CLASSES[linksProbe]} aria-live="polite" data-testid="email-links-probe" data-outcome={linksProbe}>
                        {$_(LINKS_PROBE_KEYS[linksProbe])}
                    </p>
                {/if}
                {#if linksProbeWarns(linksProbe)}
                    <button type="button" class="inline-flex items-center gap-1.5 rounded-md border border-lf-input bg-lf-card px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover" onclick={checkLinksAgain} data-testid="email-links-recheck">
                        <RefreshCw class="h-4 w-4" aria-hidden="true" />
                        {$_('email.links.recheck')}
                    </button>
                {/if}
            </div>
        {/if}

        {#if status.state === 'ready'}
            <div class="space-y-3 rounded-lg border border-lf-subtle bg-lf-panel p-4" data-testid="email-test">
                <p class="text-sm text-lf-secondary">{$_('email.test.hint')}</p>
                <button
                    type="button"
                    class="inline-flex items-center gap-2 rounded-lg bg-lf-action px-4 py-2 text-sm font-semibold text-lf-on-action transition-colors hover:bg-lf-action-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={busy}
                    onclick={sendTest}
                    data-testid="email-test-button"
                >
                    <Send class="h-4 w-4" aria-hidden="true" />
                    {sending ? $_('email.test.sending') : $_('email.test.button')}
                </button>
            </div>
        {/if}

        {#if outcome}
            <p class={OUTCOME_CLASSES[outcome.kind]} role={outcome.kind === 'sent' ? 'status' : 'alert'} data-testid="email-test-outcome" data-outcome={outcome.kind}>
                {outcome.kind === 'sent' ? $_('email.test.sent') : testFailureMessage($_, outcome.failure)}
            </p>
        {/if}
    {/if}
</section>
