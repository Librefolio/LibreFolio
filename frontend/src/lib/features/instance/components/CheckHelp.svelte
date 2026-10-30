<!--
  The help next to a check (FB-27): who can solve it decides what the user is offered (`checkGuides.json`).
  - `guide`: the administrator solves it alone → the «Guide» button to the section of the administrator's guide.
  - `support`: whoever hosts the instance solves it → «Contact support», a link to the instance's support address
    (`LIBREFOLIO_SUPPORT_URL`) with the check's code, its severity, the instance's address, the version and the date in
    the message (`buildCheckReport`; never a personal datum or a secret). Without a usable address there is no link, and
    a line tells the user to contact whoever provides the service; never a public GitHub issue. A check that passed has
    nothing to report, so it shows no support control.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {LifeBuoy} from 'lucide-svelte';
    import {APP_VERSION} from '$lib/version';
    import {reportHref, supportChannel} from '$lib/features/support/supportChannel';
    import {checkHelp} from '../checkGuides';
    import {buildCheckReport, type CheckReportSeverity} from '../checkSupportReport';
    import {instanceConfig} from '../instanceConfig.svelte';

    interface Props {
        checkId: string;
        severity: CheckReportSeverity;
        /** The check passed: a guide still serves it, the support has nothing to receive. */
        passed?: boolean;
        /** The instance's support address; `instanceConfig.config.support_url` by default. */
        supportUrl?: string | null;
    }

    let {checkId, severity, passed = false, supportUrl = configuredSupportUrl()}: Props = $props();

    /** The generated type of a nullable string with a description also admits an array (a quirk of the client generator). */
    function configuredSupportUrl(): string | null {
        const configured = instanceConfig.config.support_url;
        return typeof configured === 'string' ? configured : null;
    }

    const help = $derived(checkHelp(checkId));
    const channel = $derived(supportChannel(supportUrl, {githubFallback: false}));
    const href = $derived(channel ? reportHref(channel, buildCheckReport({checkId, severity, instanceAddress: window.location.origin, appVersion: APP_VERSION, date: new Date()})) : null);
</script>

{#if help?.kind === 'guide'}
    <span class="shrink-0 [&_button]:text-inherit">
        <DocsLink icon="book" label={$_('settings.securityTab.guide')} labelDisplay="visible" path={help.path} size={14} testId="security-guide" />
    </span>
{:else if help?.kind === 'support' && !passed}
    {#if channel && href}
        <a {href} target={channel.kind === 'page' ? '_blank' : undefined} rel={channel.kind === 'page' ? 'noopener noreferrer' : undefined} class="inline-flex shrink-0 items-center gap-1.5 text-sm font-medium text-inherit underline" data-testid="check-support">
            <LifeBuoy class="h-3.5 w-3.5" aria-hidden="true" />
            {$_('settings.securityTab.support')}
        </a>
    {:else}
        <span class="shrink-0 text-sm" data-testid="check-support-missing">{$_('settings.securityTab.supportMissing')}</span>
    {/if}
{/if}
