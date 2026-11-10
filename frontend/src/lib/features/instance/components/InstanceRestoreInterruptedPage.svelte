<!--
  The page of an instance that serves no data until its administrator acts: the state of its restore cannot be read
  (B-33, `reason` `restore_state`: LibreFolio cannot tell which data it holds, the administrator chooses with
  `./dev.py backup pending --recover previous`) or the owner of the restored data has no account yet (H5-3, `reason`
  `owner_assignment`: `./dev.py backup pending --recover owner`). Every API route but a few answers 423
  `instance_restore_interrupted`. The page says so on the login's animated background and offers the help of whoever can
  act (FB-27): the recovery is a command on the server, so on a self-hosted instance the administrator solves it alone
  and the page links the guide of the recovery; on a managed instance the customer cannot, and the page links the
  instance's support address with the state's code, the instance's address, the version and the date in the message
  (D7), or, without a usable address, says to contact whoever provides the service. A self-hosted instance also links
  its support address when it has one. It asks the instance every `pollMs` whether it serves the data again, and
  reloads once it does.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {ExternalLink, LifeBuoy, TriangleAlert} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {currentLanguage} from '$lib/stores/app/language';
    import AnimatedBackground from '$lib/components/ui/AnimatedBackground.svelte';
    import {reportHref, supportChannel} from '$lib/features/support/supportChannel';
    import {APP_VERSION} from '$lib/version';
    import {buildCheckReport} from '../checkSupportReport';
    import {instanceConfig} from '../instanceConfig.svelte';
    import {selfHostedConfirmed} from '$lib/features/instance/profile';

    interface Props {
        /** What the retry button and the end of the state do; reloads the page by default. */
        onretry?: () => void;
        /** Whether the instance still serves no data, `GET /system/instance`; injectable for tests. */
        fetchInterrupted?: () => Promise<boolean | undefined>;
        /** How often the instance is asked, in milliseconds. */
        pollMs?: number;
        /** The instance's support address (`LIBREFOLIO_SUPPORT_URL`); `instanceConfig.config.support_url` by default. */
        supportUrl?: string | null;
        /** Why the instance serves no data (`restore_interrupted_reason` of `GET /system/instance`); null or absent reads as `restore_state`. */
        reason?: 'restore_state' | 'owner_assignment' | null;
        /** Whether the administrator is whoever runs the server (a self-hosted instance, confirmed by the server): the recovery is theirs. */
        selfHosted?: boolean;
    }

    let {onretry = () => window.location.reload(), fetchInterrupted = defaultFetchInterrupted, pollMs = 30_000, supportUrl = configuredSupportUrl(), reason = null, selfHosted = selfHostedConfirmed()}: Props = $props();

    /** The generated type of a nullable string with a description also admits an array (a quirk of the client
     *  generator, as in `AssetSearchAutocomplete`); the response's validator accepts only a string or null. */
    function configuredSupportUrl(): string | null {
        const configured = instanceConfig.config.support_url;
        return typeof configured === 'string' ? configured : null;
    }

    // D7: the instance's support, when it names a usable one (checked again, no GitHub fallback): a mailto or a page
    const support = $derived(supportChannel(supportUrl, {githubFallback: false}));
    const supportHref = $derived(support ? reportHref(support, buildCheckReport({checkId: 'platform.restore_interrupted', severity: 'error', instanceAddress: window.location.origin, appVersion: APP_VERSION, date: new Date()})) : null);

    const ownerAssignment = $derived(reason === 'owner_assignment');

    /** The page of the recovery, in the interface language (the docs' rule: English at the root): the CLI's section for an
     *  unreadable state. The owner's account (`owner_assignment`) has no guide: no «Guide» button there. */
    const docsHref = $derived(`/mkdocs/${$currentLanguage && $currentLanguage !== 'en' ? `${$currentLanguage}/` : ''}admin/cli_backup/#backup-pending-unreadable`);

    async function defaultFetchInterrupted(): Promise<boolean | undefined> {
        return (await zodiosApi.get_instance_config_api_v1_system_instance_get()).restore_interrupted;
    }

    onMount(() => {
        let stopped = false;
        const timer = setInterval(async () => {
            let interrupted: boolean | undefined;
            try {
                interrupted = await fetchInterrupted();
            } catch {
                // Not answered: the administrator may be restarting the server; ask again at the next round
                return;
            }
            if (interrupted === false && !stopped) {
                stopped = true;
                clearInterval(timer);
                onretry();
            }
        }, pollMs);
        return () => {
            stopped = true;
            clearInterval(timer);
        };
    });
</script>

<div class="relative flex min-h-screen items-center justify-center p-4" data-testid="instance-restore-interrupted">
    <!-- The login's background, the same component: the customer meets the page they know -->
    <AnimatedBackground />
    <div class="w-full max-w-lg rounded-2xl border border-lf-subtle bg-lf-card p-6 shadow-xl">
        <section class="flex items-start gap-3" role="alert">
            <TriangleAlert class="mt-0.5 h-6 w-6 shrink-0 text-lf-warning" aria-hidden="true" />
            <div>
                <h1 class="text-xl font-semibold text-lf-primary">{$_(ownerAssignment ? 'instance.restoreInterrupted.ownerTitle' : 'instance.restoreInterrupted.title')}</h1>
                <p class="mt-2 text-sm text-lf-secondary" data-testid="instance-restore-interrupted-message">{$_(ownerAssignment ? 'instance.restoreInterrupted.ownerMessage' : 'instance.restoreInterrupted.message')}</p>
            </div>
        </section>
        <p class="mt-3 rounded-lg border border-lf-warning-line bg-lf-warning-soft px-3 py-2 text-sm text-lf-warning-on-soft" data-testid="instance-restore-interrupted-admin">{$_(ownerAssignment ? 'instance.restoreInterrupted.ownerAdminHint' : 'instance.restoreInterrupted.adminHint')}</p>
        <p class="mt-3 text-xs text-lf-muted" data-testid="instance-restore-interrupted-auto">{$_('instance.restoreInterrupted.autoReload')}</p>
        {#if !supportHref && !selfHosted}
            <p class="mt-3 text-sm text-lf-secondary" data-testid="instance-restore-interrupted-support-missing">{$_('instance.restoreInterrupted.supportMissing')}</p>
        {/if}
        <div class="mt-5 flex flex-wrap items-center justify-end gap-2">
            {#if selfHosted && !ownerAssignment}
                <a href={docsHref} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-lf-link hover:bg-lf-hover hover:underline" data-testid="instance-restore-interrupted-docs">
                    {$_('instance.restoreInterrupted.docs')}
                    <ExternalLink class="h-4 w-4" aria-hidden="true" />
                </a>
            {/if}
            {#if supportHref}
                <a
                    href={supportHref}
                    target={support?.kind === 'page' ? '_blank' : undefined}
                    rel={support?.kind === 'page' ? 'noopener noreferrer' : undefined}
                    class="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-lf-link hover:bg-lf-hover hover:underline"
                    data-testid="instance-restore-interrupted-support"
                >
                    {$_('instance.restoreInterrupted.support')}
                    <LifeBuoy class="h-4 w-4" aria-hidden="true" />
                </a>
            {/if}
            <button type="button" class="rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover" onclick={() => onretry()} data-testid="instance-restore-interrupted-retry">
                {$_('instance.awaitingRestore.retry')}
            </button>
        </div>
    </div>
</div>
