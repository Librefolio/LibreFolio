<script lang="ts">
    import {getAllContexts, onMount, tick, untrack} from 'svelte';
    import {get} from 'svelte/store';
    import {afterNavigate} from '$app/navigation';
    import {AlertTriangle, ArrowLeft, LoaderCircle, RefreshCw} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {fetchToolCatalog} from './client';
    import {
        ToolClientError,
        getToolAccountState,
        observeToolAccount,
        type ToolAccountState,
        type ToolDescriptor,
        type VerifiedToolCatalog,
    } from './contracts';
    import {
        resolveToolRenderer,
        type ToolRendererBinding,
        type ToolRendererMount,
    } from './registry';
    import {
        toolDescription,
        toolDocumentationPath,
        toolErrorMessage,
        toolName,
        toolViewError,
        unavailableMessage,
        type ToolUnavailableReason,
    } from './presentation';

    let {toolCode}: {toolCode: string} = $props();

    type HostPhase = 'catalog_loading' | 'component_loading' | 'ready' | 'unavailable' | 'error' | 'anonymous';
    const context = getAllContexts<Map<unknown, unknown>>();
    let account = $state.raw<ToolAccountState>(getToolAccountState());
    let catalog = $state.raw<VerifiedToolCatalog | null>(null);
    let descriptor = $state.raw<ToolDescriptor | null>(null);
    let binding = $state.raw<ToolRendererBinding | null>(null);
    let unavailable = $state<ToolUnavailableReason | null>(null);
    let error = $state.raw<ToolClientError | null>(null);
    let cleanupError = $state.raw<ToolClientError | null>(null);
    let phase = $state<HostPhase>('catalog_loading');
    let errorStage = $state<'catalog' | 'component'>('catalog');
    let confirmReload = $state(false);
    let mounted = $state(false);
    let heading = $state<HTMLHeadingElement | undefined>(undefined);
    let rendererTarget = $state<HTMLDivElement | undefined>(undefined);
    let alive = false;
    let sequence = 0;
    let controller: AbortController | null = null;
    let activeMount: {handle: ToolRendererMount; generation: number; sequence: number} | null = null;

    const busy = $derived(phase === 'catalog_loading' || phase === 'component_loading');
    const documentation = $derived(descriptor ? toolDocumentationPath(descriptor) : null);
    const errorCopy = $derived(error ? toolErrorMessage(error) : null);
    const unavailableCopy = $derived(unavailable ? unavailableMessage(unavailable) : null);
    const cleanupCopy = $derived(cleanupError ? toolErrorMessage(cleanupError) : null);

    afterNavigate(() => heading?.focus({preventScroll: true}));

    function current(requestSequence: number, code: string, generation: number, request: AbortController): boolean {
        const session = getToolAccountState();
        return alive && requestSequence === sequence && code === toolCode && !request.signal.aborted
            && session.authenticated && session.generation === generation;
    }

    function reportFailure(failure: ToolClientError, name = 'tool.host.failed'): void {
        const message = toolErrorMessage(failure);
        notify({
            name,
            detail: {code: failure.code, kind: failure.kind, issueCount: failure.issueCount},
            toast: {variant: 'error', message: $t(message.key, {default: message.fallback})},
        });
    }

    async function disposeMount(handle: ToolRendererMount, generation: number, ownerSequence: number): Promise<void> {
        try {
            await handle.unmount();
        } catch (caught) {
            const failure = toolViewError(caught);
            if (alive && sequence === ownerSequence && getToolAccountState().generation === generation) cleanupError = failure;
            // The registry already emitted the expected cleanup event and host-supplied toast.
            if (failure.code !== 'renderer_unmount_failed') reportFailure(failure, 'tool.host.cleanup.failed');
        }
    }

    function releaseRenderer(): void {
        const previous = activeMount;
        activeMount = null;
        if (previous) void disposeMount(previous.handle, previous.generation, previous.sequence);
    }

    function invalidate(): void {
        sequence += 1;
        controller?.abort();
        controller = null;
        releaseRenderer();
        catalog = null;
        descriptor = null;
        binding = null;
        unavailable = null;
        error = null;
        cleanupError = null;
        confirmReload = false;
    }

    async function loadTool(code: string, generation: number, reuse?: ToolRendererBinding): Promise<void> {
        const session = getToolAccountState();
        if (!alive || !session.authenticated || session.generation !== generation) return;
        const requestSequence = ++sequence;
        controller?.abort();
        const request = new AbortController();
        controller = request;
        releaseRenderer();
        confirmReload = false;
        error = null;
        unavailable = null;
        errorStage = reuse ? 'component' : 'catalog';
        phase = reuse ? 'component_loading' : 'catalog_loading';
        if (!reuse) {
            catalog = null;
            descriptor = null;
            binding = null;
        }
        try {
            const loadedCatalog = reuse ? catalog : await fetchToolCatalog({signal: request.signal});
            if (!current(requestSequence, code, generation, request)) return;
            if (!loadedCatalog) throw new ToolClientError('compatibility', 'catalog_unverified');
            catalog = loadedCatalog;
            descriptor = loadedCatalog.items.find((item) => item.tool_code === code) ?? null;
            let selected: ToolRendererBinding;
            if (reuse) {
                selected = reuse;
            } else {
                const resolution = resolveToolRenderer(loadedCatalog, code);
                if (resolution.status === 'unavailable') {
                    unavailable = resolution.reason;
                    phase = 'unavailable';
                    const message = unavailableMessage(resolution.reason);
                    notify({
                        name: 'tool.host.unavailable',
                        detail: {code: resolution.reason, unavailable: loadedCatalog.unavailable.length},
                        toast: {variant: 'warning', message: $t(message.key, {default: message.fallback})},
                    });
                    return;
                }
                selected = resolution.binding;
            }
            descriptor = selected.descriptor;
            binding = selected;
            phase = 'component_loading';
            errorStage = 'component';
            const renderer = await selected.load({signal: request.signal});
            if (!current(requestSequence, code, generation, request)) return;
            await tick();
            if (!current(requestSequence, code, generation, request)) return;
            if (!rendererTarget) throw new ToolClientError('renderer', 'renderer_mount_failed');
            const handle = renderer.mount(rendererTarget, {
                context,
                cleanupFailureToast: () => ({
                    variant: 'error',
                    message: get(t)('tools.errors.cleanup', {default: 'The tool view was removed, but its cleanup reported an error.'}),
                }),
            });
            if (!current(requestSequence, code, generation, request)) {
                void disposeMount(handle, generation, requestSequence);
                return;
            }
            activeMount = {handle, generation, sequence: requestSequence};
            phase = 'ready';
            const degraded = loadedCatalog.unavailable.length > 0;
            notify({
                name: degraded ? 'tool.host.degraded' : 'tool.host.loaded',
                detail: {unavailable: loadedCatalog.unavailable.length},
                toast: degraded ? {
                    variant: 'warning',
                    message: $t('tools.catalog.degradedToast', {
                        default: 'Tools loaded with unavailable entries or interfaces. See the catalogue for details.',
                    }),
                } : undefined,
            });
        } catch (caught) {
            if (!current(requestSequence, code, generation, request)) return;
            releaseRenderer();
            error = toolViewError(caught);
            if (error.kind === 'authentication') {
                catalog = null;
                descriptor = null;
                binding = null;
            }
            phase = 'error';
            reportFailure(error);
        } finally {
            if (sequence === requestSequence && controller === request) controller = null;
        }
    }

    function requestReload(): void {
        if (busy || !account.authenticated) return;
        if (activeMount) confirmReload = true;
        else void loadTool(toolCode, account.generation);
    }

    function acceptReload(): void {
        if (busy) return;
        confirmReload = false;
        void loadTool(toolCode, account.generation);
    }

    function retry(): void {
        if (busy) return;
        void loadTool(toolCode, account.generation, errorStage === 'component' ? binding ?? undefined : undefined);
    }

    onMount(() => {
        alive = true;
        const unobserve = observeToolAccount((next) => {
            invalidate();
            account = next;
            phase = next.authenticated ? 'catalog_loading' : 'anonymous';
        });
        mounted = true;
        return () => {
            alive = false;
            mounted = false;
            unobserve();
            invalidate();
        };
    });

    $effect(() => {
        const ready = mounted;
        const code = toolCode;
        const {generation, authenticated} = account;
        if (!ready) return;
        untrack(() => {
            if (authenticated) void loadTool(code, generation);
            else phase = 'anonymous';
        });
    });
</script>

<section class="min-w-0 space-y-5" data-testid="tool-host" data-state={phase} data-busy={busy ? 'true' : 'false'} aria-busy={busy}>
    <header class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
            <a href="/tools" aria-label={`${$t('common.back')} · ${$t('tools.title', {default: 'Tools'})}`} class="inline-flex items-center gap-2 rounded text-sm font-medium text-libre-green focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green dark:text-green-400 dark:focus-visible:outline-green-400" data-testid="tool-back">
                <ArrowLeft size={18} aria-hidden="true" />
                {$t('tools.title', {default: 'Tools'})}
            </a>
            <button type="button" onclick={requestReload} disabled={busy || !account.authenticated} class="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 dark:focus-visible:outline-green-400" data-testid="tool-host-refresh">
                <RefreshCw size={16} aria-hidden="true" />
                {$t('common.refresh')}
            </button>
        </div>
        <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="min-w-0">
                <h1 bind:this={heading} tabindex="-1" class="break-words text-2xl font-bold text-gray-900 outline-none dark:text-gray-100">
                    {descriptor ? toolName(descriptor, $t) : $t('tools.title', {default: 'Tools'})}
                </h1>
                {#if descriptor}
                    <p class="mt-2 break-words text-sm text-gray-600 dark:text-gray-400">{toolDescription(descriptor, $t)}</p>
                    <p class="mt-2 break-words text-xs text-gray-500 dark:text-gray-400">
                        {$t('tools.contractVersion', {default: 'Contract'})}: {descriptor.contract_version}
                        · {$t('tools.implementationVersion', {default: 'Implementation'})}: {descriptor.implementation_version}
                    </p>
                {:else}
                    <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">{$t('tools.subtitle', {default: 'Independent calculations. No portfolio changes are written.'})}</p>
                {/if}
            </div>
            {#if documentation}
                <span class="inline-flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
                    {$t('common.documentation')}
                    <DocsLink path={documentation} label={$t('common.documentation')} icon="book" size={20} testId="tool-host-docs" />
                </span>
            {:else if descriptor}
                <span class="text-xs text-gray-500 dark:text-gray-400" data-testid="tool-docs-unavailable">
                    {$t('tools.documentationUnavailable', {default: 'Documentation link unavailable'})}
                </span>
            {/if}
        </div>
    </header>

    {#if cleanupError && cleanupCopy}
        <p class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="tool-cleanup-error" data-error-code={cleanupError.code}>
            {$t(cleanupCopy.key, {default: cleanupCopy.fallback})}
        </p>
    {/if}

    {#if catalog && catalog.unavailable.length > 0}
        <aside class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" role="status" data-testid="tool-host-degraded">
            {$t('tools.catalog.degraded', {default: 'Unavailable backend entries: {count}.', values: {count: catalog.unavailable.length}})}
        </aside>
    {/if}

    {#if phase === 'anonymous'}
        <p class="text-sm text-gray-600 dark:text-gray-400" role="status" data-testid="tools-auth-required">
            {$t('tools.authRequired', {default: 'Sign in to use tools.'})}
        </p>
    {:else if phase === 'error' && error && errorCopy}
        <div class="space-y-3 rounded-xl border border-red-200 bg-red-50 p-5 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="tool-host-error" data-error-code={error.code}>
            <h2 class="font-semibold">{$t('common.error')}</h2>
            <p class="text-sm">{$t(errorCopy.key, {default: errorCopy.fallback})}</p>
            <button type="button" onclick={retry} class="rounded-lg border border-current px-3 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2" data-testid={errorStage === 'component' && binding ? 'tool-retry-interface' : 'tool-retry-catalog'}>
                {$t('common.retry')}
            </button>
        </div>
    {:else if phase === 'unavailable' && unavailable && unavailableCopy}
        <div class="space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200" role="status" data-testid="tool-host-unavailable" data-reason={unavailable}>
            <h2 class="flex items-center gap-2 font-semibold">
                <AlertTriangle size={20} aria-hidden="true" />
                {$t('tools.status.unavailable', {default: 'Unavailable'})}
            </h2>
            <p class="text-sm">{$t(unavailableCopy.key, {default: unavailableCopy.fallback})}</p>
        </div>
    {:else if busy}
        <div class="flex items-center gap-2 rounded-xl border border-gray-200 bg-white p-5 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" role="status" data-testid={phase === 'catalog_loading' ? 'tool-host-catalog-loading' : 'tool-host-component-loading'}>
            <LoaderCircle size={20} class="animate-spin motion-reduce:animate-none" aria-hidden="true" />
            {phase === 'component_loading' ? $t('tools.host.loadingInterface', {default: 'Loading tool interface…'}) : $t('common.loading')}
        </div>
    {/if}

    {#key account.generation}
        {#key toolCode}
            {#if binding && (phase === 'component_loading' || phase === 'ready')}
                <div bind:this={rendererTarget} class="min-w-0" data-testid="tool-host-renderer" data-busy={phase === 'component_loading' ? 'true' : 'false'} aria-busy={phase === 'component_loading'}></div>
            {/if}
        {/key}
    {/key}
</section>

<ConfirmModal
    open={confirmReload}
    title={$t('tools.host.reloadTitle', {default: 'Reload tool?'})}
    message={$t('tools.host.reloadWarning', {default: 'Reloading replaces this tool interface and discards its current draft. Continue?'})}
    confirmText={$t('common.refresh')}
    cancelText={$t('common.continueEditing')}
    warning
    onConfirm={acceptReload}
    onCancel={() => { confirmReload = false; }}
    testId="tool-host-reload-confirm"
/>
