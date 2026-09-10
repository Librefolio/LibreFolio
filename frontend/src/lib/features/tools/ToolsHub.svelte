<script lang="ts">
    import {onMount} from 'svelte';
    import {afterNavigate} from '$app/navigation';
    import {AlertTriangle, ArrowRight, LoaderCircle, RefreshCw, Wrench} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {fetchToolCatalog} from './client';
    import {
        getToolAccountState,
        observeToolAccount,
        type ToolAccountState,
        type ToolClientError,
        type ToolDescriptor,
        type VerifiedToolCatalog,
    } from './contracts';
    import {resolveToolRenderer, type ToolRendererResolution} from './registry';
    import {
        toolDescription,
        toolDocumentationPath,
        toolErrorMessage,
        toolIcon,
        toolName,
        toolRoute,
        toolViewError,
        unavailableMessage,
    } from './presentation';

    interface HubEntry {
        descriptor: ToolDescriptor;
        resolution: ToolRendererResolution;
    }

    let account = $state.raw<ToolAccountState>(getToolAccountState());
    // Branded catalogue/descriptor identity must not be replaced by reactive proxies.
    let catalog = $state.raw<VerifiedToolCatalog | null>(null);
    let entries = $state.raw<readonly HubEntry[]>([]);
    let error = $state.raw<ToolClientError | null>(null);
    let loading = $state(true);
    let heading = $state<HTMLHeadingElement | undefined>(undefined);
    let alive = false;
    let sequence = 0;
    let controller: AbortController | null = null;

    const frontendUnavailable = $derived(entries.filter((entry) => entry.resolution.status === 'unavailable').length);
    const errorCopy = $derived(error ? toolErrorMessage(error) : null);
    const state = $derived(
        loading ? 'loading' : !account.authenticated ? 'anonymous' : error ? 'error' : !catalog ? 'idle'
            : catalog.unavailable.length || frontendUnavailable ? 'degraded' : entries.length ? 'ready' : 'empty',
    );

    afterNavigate(() => heading?.focus({preventScroll: true}));

    function current(requestSequence: number, generation: number, request: AbortController): boolean {
        const session = getToolAccountState();
        return alive && sequence === requestSequence && !request.signal.aborted
            && session.authenticated && session.generation === generation;
    }

    async function loadCatalog(): Promise<void> {
        if (!alive || !account.authenticated || controller) return;
        const generation = account.generation;
        const requestSequence = ++sequence;
        const request = new AbortController();
        controller = request;
        loading = true;
        error = null;
        catalog = null;
        entries = [];
        try {
            const loaded = await fetchToolCatalog({signal: request.signal});
            if (!current(requestSequence, generation, request)) return;
            const nextEntries = loaded.items.map((descriptor): HubEntry => ({
                descriptor,
                resolution: resolveToolRenderer(loaded, descriptor.tool_code),
            }));
            catalog = loaded;
            entries = nextEntries;
            const incompatible = nextEntries.filter((entry) => entry.resolution.status === 'unavailable').length;
            const degraded = loaded.unavailable.length > 0 || incompatible > 0;
            notify({
                name: degraded ? 'tool.catalog.degraded' : 'tool.catalog.loaded',
                detail: {loaded: loaded.items.length, unavailable: loaded.unavailable.length, incompatible},
                toast: degraded ? {
                    variant: 'warning',
                    message: $t('tools.catalog.degradedToast', {
                        default: 'Tools loaded with unavailable entries or interfaces. See the catalogue for details.',
                    }),
                } : undefined,
            });
        } catch (caught) {
            if (!current(requestSequence, generation, request)) return;
            error = toolViewError(caught);
            catalog = null;
            entries = [];
            const message = toolErrorMessage(error);
            notify({
                name: 'tool.catalog.failed',
                detail: {code: error.code, kind: error.kind, issueCount: error.issueCount},
                toast: {variant: 'error', message: $t(message.key, {default: message.fallback})},
            });
        } finally {
            if (alive && sequence === requestSequence && controller === request) {
                controller = null;
                loading = false;
            }
        }
    }

    onMount(() => {
        alive = true;
        const unobserve = observeToolAccount((next) => {
            sequence += 1;
            controller?.abort();
            controller = null;
            account = next;
            catalog = null;
            entries = [];
            error = null;
            loading = next.authenticated;
            if (next.authenticated) void loadCatalog();
        });
        return () => {
            alive = false;
            sequence += 1;
            controller?.abort();
            controller = null;
            unobserve();
            catalog = null;
            entries = [];
        };
    });
</script>

<section class="min-w-0 space-y-6" data-testid="tools-hub" data-state={state} data-busy={loading ? 'true' : 'false'} aria-busy={loading}>
    <header class="flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0">
            <h1 bind:this={heading} tabindex="-1" class="flex items-center gap-2 text-2xl font-bold text-gray-900 outline-none dark:text-gray-100">
                <Wrench size={24} aria-hidden="true" class="shrink-0 text-libre-green dark:text-green-400" />
                {$t('tools.title', {default: 'Tools'})}
            </h1>
            <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {$t('tools.subtitle', {default: 'Independent calculations. No portfolio changes are written.'})}
            </p>
        </div>
        <button
            type="button"
            onclick={() => loadCatalog()}
            disabled={loading || !account.authenticated}
            class="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 dark:focus-visible:outline-green-400"
            data-testid="tools-hub-refresh"
        >
            <RefreshCw size={16} aria-hidden="true" />
            {$t('common.refresh')}
        </button>
    </header>

    {#if loading}
        <div class="flex items-center gap-2 rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" role="status" data-testid="tools-catalog-loading">
            <LoaderCircle size={20} class="animate-spin motion-reduce:animate-none" aria-hidden="true" />
            {$t('common.loading')}
        </div>
    {:else if !account.authenticated}
        <p class="text-sm text-gray-600 dark:text-gray-400" role="status" data-testid="tools-auth-required">
            {$t('tools.authRequired', {default: 'Sign in to use tools.'})}
        </p>
    {:else if error && errorCopy}
        <div class="space-y-3 rounded-xl border border-red-200 bg-red-50 p-5 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="tools-catalog-error" data-error-code={error.code}>
            <h2 class="font-semibold">{$t('common.error')}</h2>
            <p class="text-sm">{$t(errorCopy.key, {default: errorCopy.fallback})}</p>
            <button type="button" onclick={() => loadCatalog()} class="rounded-lg border border-current px-3 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2" data-testid="tools-catalog-retry">
                {$t('common.retry')}
            </button>
        </div>
    {:else if catalog}
        {#if catalog.unavailable.length > 0 || frontendUnavailable > 0}
            <aside class="space-y-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" role="status" data-testid="tools-catalog-degraded">
                <AlertTriangle size={18} aria-hidden="true" />
                {#if catalog.unavailable.length > 0}
                    <p>{$t('tools.catalog.degraded', {default: 'Unavailable backend entries: {count}.', values: {count: catalog.unavailable.length}})}</p>
                {/if}
                {#if frontendUnavailable > 0}
                    <p>{$t('tools.catalog.uiUnavailable', {default: 'Interfaces unavailable in this build: {count}.', values: {count: frontendUnavailable}})}</p>
                {/if}
                <p>{$t('tools.catalog.diagnosticsHint', {default: 'Read-only diagnostics are available in Settings → About → Plugin diagnostics.'})}</p>
            </aside>
        {/if}

        {#if entries.length === 0}
            <div class="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800" role="status" data-testid="tools-catalog-empty">
                <h2 class="font-semibold text-gray-900 dark:text-gray-100">
                    {$t('tools.catalog.emptyTitle', {default: 'No tools available'})}
                </h2>
                <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
                    {$t('tools.catalog.emptyDescription', {default: 'No healthy tools were returned by this catalogue. Reload after a tool is installed or repaired.'})}
                </p>
            </div>
        {:else}
            <ul class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="tools-catalog-cards">
                {#each entries as entry (entry.descriptor.tool_code)}
                    {@const descriptor = entry.descriptor}
                    {@const Icon = toolIcon(descriptor.icon_key)}
                    {@const documentation = toolDocumentationPath(descriptor)}
                    <li class="flex min-w-0 flex-col gap-4 rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800" data-testid={`tool-card-${descriptor.tool_code}`}>
                        <div class="flex items-start gap-3">
                            <Icon size={22} class="shrink-0 text-libre-green dark:text-green-400" aria-hidden="true" />
                            <div class="min-w-0">
                                <h2 class="break-words font-semibold text-gray-900 dark:text-gray-100">{toolName(descriptor, $t)}</h2>
                                <p class="mt-2 break-words text-sm text-gray-600 dark:text-gray-400">{toolDescription(descriptor, $t)}</p>
                            </div>
                        </div>
                        <p class="break-words text-xs text-gray-500 dark:text-gray-400">
                            {$t('tools.contractVersion', {default: 'Contract'})}: {descriptor.contract_version}
                        </p>
                        {#if entry.resolution.status === 'unavailable'}
                            {@const message = unavailableMessage(entry.resolution.reason)}
                            <p class="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-200" data-testid="tool-interface-unavailable" data-reason={entry.resolution.reason}>
                                {$t(message.key, {default: message.fallback})}
                            </p>
                        {/if}
                        <div class="mt-auto flex flex-wrap items-center justify-between gap-3">
                            {#if entry.resolution.status === 'ready'}
                                <a href={toolRoute(descriptor)} class="inline-flex items-center gap-2 rounded-lg bg-libre-green px-3 py-2 text-sm font-medium text-white hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green dark:focus-visible:outline-green-400" data-testid="tool-open">
                                    {$t('tools.open', {default: 'Open tool'})}
                                    <ArrowRight size={16} aria-hidden="true" />
                                </a>
                            {:else}
                                <button type="button" disabled class="cursor-not-allowed rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-500 dark:bg-gray-700 dark:text-gray-400" data-testid="tool-open">
                                    {$t('tools.open', {default: 'Open tool'})}
                                </button>
                            {/if}
                            {#if documentation}
                                <span class="inline-flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                                    {$t('common.documentation')}
                                    <DocsLink path={documentation} label={$t('common.documentation')} icon="book" size={18} testId={`tool-docs-${descriptor.tool_code}`} />
                                </span>
                            {:else}
                                <span class="text-xs text-gray-500 dark:text-gray-400" data-testid="tool-docs-unavailable">
                                    {$t('tools.documentationUnavailable', {default: 'Documentation link unavailable'})}
                                </span>
                            {/if}
                        </div>
                    </li>
                {/each}
            </ul>
        {/if}

        {#if catalog.unavailable.length > 0}
            <section class="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800" data-testid="tools-unavailable-entries">
                <h2 class="font-semibold text-gray-900 dark:text-gray-100">{$t('tools.catalog.unavailableEntries', {default: 'Unavailable backend entries'})}</h2>
                <ul class="mt-3 space-y-2 text-sm text-gray-600 dark:text-gray-400">
                    {#each catalog.unavailable as unavailable}
                        <li class="flex flex-wrap items-center justify-between gap-2" data-testid="tool-unavailable-entry">
                            <span class="break-words">{unavailable.tool_code ?? $t('tools.catalog.unknownTool', {default: 'Unidentified tool'})}</span>
                            <span>{$t('tools.status.unavailable', {default: 'Unavailable'})}</span>
                        </li>
                    {/each}
                </ul>
            </section>
        {/if}
    {/if}
</section>
