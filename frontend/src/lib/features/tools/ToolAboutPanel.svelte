<script lang="ts">
    import {onMount, untrack} from 'svelte';
    import {AlertTriangle, ChevronDown, LoaderCircle, RefreshCw, Wrench} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {fetchToolCatalog, fetchToolDiagnostics} from './client';
    import {
        getToolAccountState,
        observeToolAccount,
        type ToolAccountState,
        type ToolClientError,
        type ToolDescriptor,
        type ToolDiagnosticsResponse,
        type VerifiedToolCatalog,
    } from './contracts';
    import {resolveToolRenderer, type ToolRendererResolution} from './registry';
    import {
        toolDescription,
        toolDocumentationPath,
        toolErrorMessage,
        toolName,
        toolViewError,
        unavailableMessage,
    } from './presentation';
    import ToolDiagnosticsPanel from './ToolDiagnosticsPanel.svelte';

    let {active = false}: {active?: boolean} = $props();

    interface CatalogEntry {
        descriptor: ToolDescriptor;
        resolution: ToolRendererResolution;
    }

    let account = $state.raw<ToolAccountState>(getToolAccountState());
    let catalog = $state.raw<VerifiedToolCatalog | null>(null);
    let entries = $state.raw<readonly CatalogEntry[]>([]);
    let catalogError = $state.raw<ToolClientError | null>(null);
    let diagnostics = $state.raw<ToolDiagnosticsResponse | null>(null);
    let diagnosticsError = $state.raw<ToolClientError | null>(null);
    let catalogLoading = $state(false);
    let diagnosticsLoading = $state(false);
    let diagnosticsOpen = $state(false);
    let mounted = $state(false);
    let alive = false;
    let catalogSequence = 0;
    let diagnosticsSequence = 0;
    let catalogController: AbortController | null = null;
    let diagnosticsController: AbortController | null = null;

    const catalogPending = $derived(active && account.authenticated && (catalogLoading || (!catalog && !catalogError)));
    const busy = $derived(active && account.authenticated && (catalogPending || diagnosticsLoading));
    const incompatibleCount = $derived(entries.filter((entry) => entry.resolution.status === 'unavailable').length);
    const catalogErrorCopy = $derived(catalogError ? toolErrorMessage(catalogError) : null);
    const diagnosticsDegraded = $derived(diagnosticsOpen && diagnostics !== null
        && (diagnostics.failures.length > 0 || !diagnostics.pool.available || diagnostics.pool.degraded_lanes > 0));
    const state = $derived(
        !active ? 'inactive' : !account.authenticated ? 'anonymous' : busy ? 'loading' : catalogError ? 'error'
            : (diagnosticsError && diagnosticsOpen) || diagnosticsDegraded ? 'degraded' : !catalog ? 'idle'
                : catalog.unavailable.length || incompatibleCount ? 'degraded' : entries.length ? 'ready' : 'empty',
    );

    function sessionCurrent(generation: number, request: AbortController): boolean {
        const session = getToolAccountState();
        return alive && active && !request.signal.aborted && session.authenticated && session.generation === generation;
    }

    function clearDiagnostics(): void {
        diagnosticsSequence += 1;
        diagnosticsController?.abort();
        diagnosticsController = null;
        diagnostics = null;
        diagnosticsError = null;
        diagnosticsLoading = false;
    }

    function clearSnapshots(): void {
        catalogSequence += 1;
        catalogController?.abort();
        catalogController = null;
        catalog = null;
        entries = [];
        catalogError = null;
        catalogLoading = false;
        clearDiagnostics();
        diagnosticsOpen = false;
    }

    function reportReadFailure(failure: ToolClientError, name: string): void {
        const message = toolErrorMessage(failure);
        notify({
            name,
            detail: {code: failure.code, kind: failure.kind, issueCount: failure.issueCount},
            toast: {variant: 'error', message: $t(message.key, {default: message.fallback})},
        });
    }

    async function refreshCatalog(): Promise<void> {
        const session = getToolAccountState();
        if (!alive || !active || !session.authenticated || catalogController) return;
        const generation = session.generation;
        const requestSequence = ++catalogSequence;
        const request = new AbortController();
        catalogController = request;
        catalogLoading = true;
        catalogError = null;
        catalog = null;
        entries = [];
        try {
            const loaded = await fetchToolCatalog({signal: request.signal});
            if (catalogSequence !== requestSequence || !sessionCurrent(generation, request)) return;
            const nextEntries = loaded.items.map((descriptor): CatalogEntry => ({
                descriptor,
                resolution: resolveToolRenderer(loaded, descriptor.tool_code),
            }));
            catalog = loaded;
            entries = nextEntries;
            const incompatible = nextEntries.filter((entry) => entry.resolution.status === 'unavailable').length;
            const degraded = loaded.unavailable.length > 0 || incompatible > 0;
            notify({
                name: degraded ? 'tool.about.catalog.degraded' : 'tool.about.catalog.loaded',
                detail: {loaded: loaded.items.length, unavailable: loaded.unavailable.length, incompatible},
                toast: degraded ? {
                    variant: 'warning',
                    message: $t('tools.catalog.degradedToast', {
                        default: 'Tools loaded with unavailable entries or interfaces. See the catalogue for details.',
                    }),
                } : undefined,
            });
        } catch (caught) {
            if (catalogSequence !== requestSequence || !sessionCurrent(generation, request)) return;
            const failure = toolViewError(caught);
            if (failure.kind === 'authentication') {
                clearSnapshots();
                diagnosticsError = failure;
            }
            catalog = null;
            entries = [];
            catalogError = failure;
            reportReadFailure(catalogError, 'tool.about.catalog.failed');
        } finally {
            if (catalogSequence === requestSequence && catalogController === request) {
                catalogController = null;
                catalogLoading = false;
            }
        }
    }

    async function refreshDiagnostics(): Promise<void> {
        const session = getToolAccountState();
        if (!alive || !active || !diagnosticsOpen || !session.authenticated || diagnosticsController) return;
        const generation = session.generation;
        const requestSequence = ++diagnosticsSequence;
        const request = new AbortController();
        diagnosticsController = request;
        diagnosticsLoading = true;
        diagnosticsError = null;
        diagnostics = null;
        try {
            const snapshot = await fetchToolDiagnostics({signal: request.signal});
            if (diagnosticsSequence !== requestSequence || !diagnosticsOpen || !sessionCurrent(generation, request)) return;
            diagnostics = snapshot;
            const degraded = snapshot.failures.length > 0 || !snapshot.pool.available || snapshot.pool.degraded_lanes > 0;
            notify({
                name: degraded ? 'tool.diagnostics.degraded' : 'tool.diagnostics.loaded',
                detail: {
                    scope: snapshot.scope,
                    loaded: snapshot.loaded.length,
                    failures: snapshot.failures.length,
                    degradedLanes: snapshot.pool.degraded_lanes,
                    poolAvailable: snapshot.pool.available,
                },
                toast: degraded ? {
                    variant: 'warning',
                    message: $t('tools.diagnostics.degraded', {
                        default: 'Discovery failures or reduced execution capacity were reported. Other tools may remain available.',
                    }),
                } : undefined,
            });
        } catch (caught) {
            if (diagnosticsSequence !== requestSequence || !diagnosticsOpen || !sessionCurrent(generation, request)) return;
            const failure = toolViewError(caught);
            if (failure.kind === 'authentication') {
                clearSnapshots();
                catalogError = failure;
            }
            diagnostics = null;
            diagnosticsError = failure;
            reportReadFailure(diagnosticsError, 'tool.diagnostics.failed');
        } finally {
            if (diagnosticsSequence === requestSequence && diagnosticsController === request) {
                diagnosticsController = null;
                diagnosticsLoading = false;
            }
        }
    }

    function toggleDiagnostics(event: Event & {currentTarget: HTMLDetailsElement}): void {
        const open = event.currentTarget.open;
        if (open === diagnosticsOpen) return;
        diagnosticsOpen = open;
        if (diagnosticsOpen) void refreshDiagnostics();
        else clearDiagnostics();
    }

    onMount(() => {
        alive = true;
        const unobserve = observeToolAccount((next) => {
            clearSnapshots();
            account = next;
        });
        mounted = true;
        return () => {
            alive = false;
            mounted = false;
            unobserve();
            clearSnapshots();
        };
    });

    $effect(() => {
        const ready = mounted;
        const visible = active;
        const {generation, authenticated} = account;
        if (!ready) return;
        untrack(() => {
            clearSnapshots();
            if (visible && authenticated && getToolAccountState().generation === generation) void refreshCatalog();
        });
    });
</script>

<section class="mt-4 min-w-0 space-y-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800" data-testid="tool-about-panel" data-state={state} data-busy={busy ? 'true' : 'false'} aria-busy={busy}>
    <header class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
            <h4 class="flex items-center gap-2 font-semibold text-gray-900 dark:text-gray-100">
                <Wrench size={18} aria-hidden="true" class="shrink-0 text-libre-green dark:text-green-400" />
                {$t('tools.title', {default: 'Tools'})}
            </h4>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {$t('tools.about.readOnly', {default: 'Read-only catalogue and diagnostics. No calculations, probes or repairs are run.'})}
            </p>
        </div>
        <button type="button" onclick={() => refreshCatalog()} disabled={!active || !account.authenticated || catalogPending} class="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700 dark:focus-visible:outline-green-400" data-testid="tool-about-refresh">
            <RefreshCw size={15} aria-hidden="true" />
            {$t('common.refresh')}
        </button>
    </header>

    {#if !active}
        <p class="text-sm text-gray-500 dark:text-gray-400" role="status" data-testid="tool-about-inactive">
            {$t('tools.about.inactive', {default: 'Open Plugin diagnostics to load tool metadata.'})}
        </p>
    {:else if !account.authenticated}
        <p class="text-sm text-gray-500 dark:text-gray-400" role="status" data-testid="tools-auth-required">{$t('tools.authRequired', {default: 'Sign in to use tools.'})}</p>
    {:else}
        {#if catalogPending}
            <p class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300" role="status" data-testid="tool-about-catalog-loading">
                <LoaderCircle size={18} class="animate-spin motion-reduce:animate-none" aria-hidden="true" />
                {$t('common.loading')}
            </p>
        {:else if catalogError && catalogErrorCopy}
            <div class="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="tool-about-catalog-error" data-error-code={catalogError.code}>
                <p>{$t(catalogErrorCopy.key, {default: catalogErrorCopy.fallback})}</p>
                <button type="button" onclick={() => refreshCatalog()} class="rounded border border-current px-3 py-1.5 focus-visible:outline-2 focus-visible:outline-offset-2" data-testid="tool-about-catalog-retry">{$t('common.retry')}</button>
            </div>
        {:else if catalog}
            {#if catalog.unavailable.length > 0 || incompatibleCount > 0}
                <aside class="space-y-1 rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-200" role="status" data-testid="tool-about-degraded">
                    <AlertTriangle size={16} aria-hidden="true" />
                    {#if catalog.unavailable.length > 0}
                        <p>{$t('tools.catalog.degraded', {default: 'Unavailable backend entries: {count}.', values: {count: catalog.unavailable.length}})}</p>
                    {/if}
                    {#if incompatibleCount > 0}
                        <p>{$t('tools.catalog.uiUnavailable', {default: 'Interfaces unavailable in this build: {count}.', values: {count: incompatibleCount}})}</p>
                    {/if}
                </aside>
            {/if}
            {#if entries.length === 0}
                <p class="text-sm text-gray-500 dark:text-gray-400" role="status" data-testid="tool-about-catalog-empty">{$t('tools.catalog.emptyTitle', {default: 'No tools available'})}</p>
            {:else}
                <ul class="space-y-3" data-testid="tool-about-catalog">
                    {#each entries as entry (entry.descriptor.tool_code)}
                        {@const item = entry.descriptor}
                        {@const documentation = toolDocumentationPath(item)}
                        <li class="min-w-0 rounded-lg border border-gray-200 p-3 dark:border-gray-700" data-testid={`tool-about-entry-${item.tool_code}`}>
                            <div class="flex flex-wrap items-start justify-between gap-2">
                                <div class="min-w-0">
                                    <h5 class="break-words text-sm font-semibold text-gray-900 dark:text-gray-100">{toolName(item, $t)}</h5>
                                    <p class="mt-1 break-words text-xs text-gray-600 dark:text-gray-400">{toolDescription(item, $t)}</p>
                                </div>
                                {#if documentation}
                                    <DocsLink path={documentation} label={$t('common.documentation')} icon="book" size={18} testId={`tool-about-docs-${item.tool_code}`} />
                                {:else}
                                    <span class="text-xs text-gray-500 dark:text-gray-400" data-testid="tool-docs-unavailable">{$t('tools.documentationUnavailable', {default: 'Documentation link unavailable'})}</span>
                                {/if}
                            </div>
                            <p class="mt-2 break-words text-xs text-gray-500 dark:text-gray-400">
                                <code>{item.tool_code}</code> · {$t('tools.contractVersion', {default: 'Contract'})}: {item.contract_version}
                                · {$t('tools.implementationVersion', {default: 'Implementation'})}: {item.implementation_version}
                            </p>
                            {#if entry.resolution.status === 'ready'}
                                <p class="mt-2 text-xs text-green-800 dark:text-green-300" data-testid="tool-about-ui-compatible">
                                    {$t('tools.about.interfaceRegistered', {default: 'Compatible interface registered in this build.'})}
                                </p>
                            {:else}
                                {@const message = unavailableMessage(entry.resolution.reason)}
                                <p class="mt-2 text-xs text-amber-800 dark:text-amber-300" data-testid="tool-about-ui-unavailable" data-reason={entry.resolution.reason}>
                                    {$t(message.key, {default: message.fallback})}
                                </p>
                            {/if}
                        </li>
                    {/each}
                </ul>
            {/if}
            {#if catalog.unavailable.length > 0}
                <div class="text-xs text-gray-600 dark:text-gray-400" data-testid="tool-about-unavailable-entries">
                    <p class="font-medium">{$t('tools.catalog.unavailableEntries', {default: 'Unavailable backend entries'})}</p>
                    <ul class="mt-1 space-y-1">
                        {#each catalog.unavailable as item}
                            <li class="break-words">{item.tool_code ?? $t('tools.catalog.unknownTool', {default: 'Unidentified tool'})}</li>
                        {/each}
                    </ul>
                </div>
            {/if}
        {/if}

        <details open={diagnosticsOpen} ontoggle={toggleDiagnostics} class="border-t border-gray-200 pt-3 dark:border-gray-700" data-testid="tool-about-diagnostics">
            <summary class="flex cursor-pointer list-none items-center justify-between gap-2 rounded text-sm font-medium text-gray-800 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-libre-green dark:text-gray-200 dark:focus-visible:outline-green-400" data-testid="tool-about-diagnostics-toggle">
                {$t('tools.diagnostics.title', {default: 'Tool diagnostics'})}
                <ChevronDown size={16} aria-hidden="true" class={`shrink-0 transition-transform ${diagnosticsOpen ? 'rotate-180' : ''}`} />
            </summary>
            {#if diagnosticsOpen}
                <ToolDiagnosticsPanel snapshot={diagnostics} loading={diagnosticsLoading} error={diagnosticsError} onRefresh={() => refreshDiagnostics()} />
            {/if}
        </details>
    {/if}
</section>
