<!--
  The page of an instance its hosting panel is restoring (H-62): every API route but a few answers 423
  `instance_awaiting_restore` until the panel ends the mode, so the app cannot start. The page says so on the login's
  animated background, asks the instance every `pollMs` whether the mode ended, and reloads once it has.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {DatabaseBackup} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import AnimatedBackground from '$lib/components/ui/AnimatedBackground.svelte';

    interface Props {
        /** What the retry button and the end of the mode do; reloads the page by default. */
        onretry?: () => void;
        /** The instance's mode, `GET /system/instance`; injectable for tests. */
        fetchMode?: () => Promise<string | undefined>;
        /** How often the mode is asked, in milliseconds. */
        pollMs?: number;
    }

    let {onretry = () => window.location.reload(), fetchMode = defaultFetchMode, pollMs = 30_000}: Props = $props();

    async function defaultFetchMode(): Promise<string | undefined> {
        // `mode` is read loosely: an older server does not send it
        const config = (await zodiosApi.get_instance_config_api_v1_system_instance_get()) as {mode?: string};
        return config.mode;
    }

    onMount(() => {
        let stopped = false;
        const timer = setInterval(async () => {
            let mode: string | undefined;
            try {
                mode = await fetchMode();
            } catch {
                // Not answered: the restore may be restarting the server; ask again at the next round
                return;
            }
            if (mode === 'normal' && !stopped) {
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

<div class="relative flex min-h-screen items-center justify-center p-4" data-testid="instance-awaiting-restore">
    <!-- The login's background, the same component: the customer meets the page they know -->
    <AnimatedBackground />
    <div class="w-full max-w-lg rounded-2xl border border-lf-subtle bg-lf-card p-6 shadow-xl">
        <section class="flex items-start gap-3" role="status">
            <DatabaseBackup class="mt-0.5 h-6 w-6 shrink-0 text-lf-info" aria-hidden="true" />
            <div>
                <h1 class="text-xl font-semibold text-lf-primary">{$_('instance.awaitingRestore.title')}</h1>
                <p class="mt-2 text-sm text-lf-secondary" data-testid="instance-awaiting-restore-message">{$_('instance.awaitingRestore.message')}</p>
            </div>
        </section>
        <p class="mt-3 text-xs text-lf-muted" data-testid="instance-awaiting-restore-auto">{$_('instance.awaitingRestore.autoReload')}</p>
        <div class="mt-5 flex justify-end">
            <button type="button" class="rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover" onclick={() => onretry()} data-testid="instance-awaiting-restore-retry">
                {$_('instance.awaitingRestore.retry')}
            </button>
        </div>
    </div>
</div>
