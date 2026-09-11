<script lang="ts">
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import {CheckCircle2, Compass, RotateCcw, X} from 'lucide-svelte';
    import {appBootstrap} from '$lib/features/onboarding/appBootstrap.svelte';
    import {IMPORT_GUIDE_STEP_IDS, INTRO_TOUR_STEP_IDS, onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {onboarding} from '$lib/stores/app/onboarding.svelte';
    import type {OnboardingFlow, OnboardingProgressItem} from '$lib/types/onboarding';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';

    let busyFlow = $state<OnboardingFlow | 'all' | null>(null);
    let error = $state<string | null>(null);
    let replayRevision = $state(0);

    let flows = $derived(onboarding.progress?.flows ?? []);
    let flowGroups = $derived([
        {key: 'setup', items: flows.filter((item) => item.flow === 'welcome')},
        {key: 'core', items: flows.filter((item) => item.flow === 'intro_tour')},
        {key: 'contextual', items: flows.filter((item) => !['welcome', 'intro_tour'].includes(item.flow))},
    ]);

    function replayIsArmed(item: OnboardingProgressItem): boolean {
        void replayRevision;
        return onboarding.hasReplay(item.flow, item.current_version);
    }

    function fail(message?: string | null) {
        error = message ?? onboarding.replayStorageError ?? $_('onboarding.errors.replayStart');
    }

    async function replayFlow(item: OnboardingProgressItem): Promise<void> {
        busyFlow = item.flow;
        error = null;
        try {
            if (item.flow === 'welcome') {
                if (!onboarding.startReplay('welcome', item.current_version, 'welcome')) {
                    fail();
                    return;
                }
                replayRevision += 1;
                await goto('/welcome');
                return;
            }
            if (item.flow === 'intro_tour') {
                if (!onboardingGuide.startIntroReplay()) {
                    fail(onboardingGuide.error);
                    return;
                }
                replayRevision += 1;
                await goto('/dashboard');
                return;
            }
            if (!onboardingGuide.armReplay(item.flow)) {
                fail(onboardingGuide.error);
                return;
            }
            replayRevision += 1;
            notify({
                name: 'onboarding.replay.armed',
                detail: {flow: item.flow, version: item.current_version},
                toast: {
                    variant: 'success',
                    message: $_('onboarding.settings.armedToast', {
                        values: {flow: $_(`onboarding.flows.${item.flow}`)},
                    }),
                },
            });
        } catch (replayError) {
            fail(replayError instanceof Error ? replayError.message : $_('onboarding.errors.replayStart'));
        } finally {
            busyFlow = null;
        }
    }

    function cancelReplay(item: OnboardingProgressItem): void {
        onboarding.clearReplay(item.flow, item.current_version);
        replayRevision += 1;
        notify({
            name: 'onboarding.replay.cancelled',
            detail: {flow: item.flow, version: item.current_version},
        });
    }

    function armedText(item: OnboardingProgressItem): string {
        return $_(`onboarding.settings.armed.${item.flow}`);
    }

    function replayActionLabel(item: OnboardingProgressItem): string {
        if (item.flow === 'import_guide') return $_('onboarding.settings.replayOnNextImport');
        if (['broker_guide', 'fx_guide', 'asset_guide'].includes(item.flow)) {
            return $_(`onboarding.settings.replayAtNextTrigger.${item.flow}`);
        }
        return $_('onboarding.settings.replay');
    }

    async function replayAll(): Promise<void> {
        busyFlow = 'all';
        error = null;
        const started: Array<{flow: OnboardingFlow; version: number}> = [];
        try {
            for (const item of flows) {
                const stepId = item.flow === 'welcome' ? 'welcome' : item.flow === 'intro_tour' ? INTRO_TOUR_STEP_IDS[0] : item.flow === 'import_guide' ? IMPORT_GUIDE_STEP_IDS[0] : item.flow === 'broker_guide' ? 'broker.overview' : item.flow === 'fx_guide' ? 'fx.currencies' : 'asset.search';
                const startedReplay = item.flow === 'intro_tour' ? onboardingGuide.prepareIntroReplay() : item.flow === 'welcome' ? onboarding.startReplay(item.flow, item.current_version, stepId) : onboardingGuide.armReplay(item.flow);
                if (!startedReplay) {
                    throw new Error(onboarding.replayStorageError ?? $_('onboarding.errors.replayStart'));
                }

                started.push({flow: item.flow, version: item.current_version});
            }
            replayRevision += 1;
            await goto('/welcome');
        } catch (replayError) {
            for (const item of started) {
                onboarding.clearReplay(item.flow, item.version);
            }
            replayRevision += 1;
            fail(replayError instanceof Error ? replayError.message : $_('onboarding.errors.replayStart'));
        } finally {
            busyFlow = null;
        }
    }

    async function retryLoad() {
        busyFlow = 'all';
        error = null;
        await appBootstrap.load(true);
        busyFlow = null;
    }
</script>

<section class="rounded-2xl border border-gray-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800" data-testid="onboarding-replay-section" data-busy={busyFlow ? 'true' : 'false'} aria-busy={busyFlow !== null} use:guideAnchor={'onboarding.settings'}>
    <div class="flex flex-col gap-3 border-b border-gray-200 pb-4 dark:border-slate-700 sm:flex-row sm:items-start sm:justify-between">
        <div class="flex gap-3">
            <Compass class="mt-0.5 shrink-0 text-libre-green dark:text-emerald-300" size={20} />
            <div>
                <h4 class="font-semibold text-gray-900 dark:text-gray-100">
                    {$_('onboarding.settings.title')}
                </h4>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    {$_('onboarding.settings.description')}
                </p>
            </div>
        </div>
        <button
            type="button"
            class="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700"
            disabled={busyFlow !== null || flows.length === 0}
            onclick={replayAll}
            data-testid="onboarding-replay-all"
        >
            <RotateCcw size={15} />
            {$_('onboarding.settings.replayAll')}
        </button>
    </div>

    {#if error}
        <div class="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="onboarding-replay-error">
            {error}
        </div>
    {/if}

    {#if onboarding.state === 'error' && flows.length === 0}
        <div class="mt-4 flex items-center justify-between gap-3" data-testid="onboarding-replay-load-error">
            <span class="text-sm text-gray-600 dark:text-gray-300">
                {onboarding.error ?? $_('onboarding.errors.loadDescription')}
            </span>
            <button type="button" class="rounded-lg bg-libre-green px-3 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={busyFlow !== null} onclick={retryLoad} data-testid="onboarding-replay-retry">
                {$_('common.retry')}
            </button>
        </div>
    {:else}
        <div class="mt-2 space-y-5">
            {#each flowGroups as group (group.key)}
                <section aria-labelledby={`onboarding-group-${group.key}`}>
                    <h5 id={`onboarding-group-${group.key}`} class="pt-2 text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                        {$_(`onboarding.settings.groups.${group.key}`)}
                    </h5>
                    <div class="divide-y divide-gray-100 dark:divide-slate-700">
                        {#each group.items as item (item.flow)}
                            {@const armed = replayIsArmed(item)}
                            <div class="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between" data-testid={`onboarding-flow-${item.flow}`} data-status={item.status} data-version={item.version} data-current-version={item.current_version}>
                                <div>
                                    <div class="flex flex-wrap items-center gap-2">
                                        <span class="font-medium text-gray-800 dark:text-gray-100">
                                            {$_(`onboarding.flows.${item.flow}`)}
                                        </span>
                                        <span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-slate-700 dark:text-gray-300" data-testid={`onboarding-flow-${item.flow}-status`}>
                                            {$_(`onboarding.status.${item.status}`)}
                                        </span>
                                        {#if item.update_available}
                                            <span class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200" data-testid={`onboarding-flow-${item.flow}-update`}>
                                                {$_('onboarding.settings.updateAvailable')}
                                            </span>
                                        {/if}
                                    </div>
                                    {#if armed}
                                        <p class="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-emerald-100 px-2.5 py-1.5 text-sm font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200" data-testid={`onboarding-flow-${item.flow}-armed`}>
                                            <CheckCircle2 size={15} />
                                            {armedText(item)}
                                        </p>
                                    {/if}
                                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                        {$_('onboarding.settings.version', {
                                            values: {
                                                seen: item.version,
                                                current: item.current_version,
                                            },
                                        })}
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    class="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700"
                                    disabled={busyFlow !== null}
                                    onclick={() => (armed ? cancelReplay(item) : replayFlow(item))}
                                    data-testid={`onboarding-replay-${item.flow}`}
                                >
                                    {#if armed}<X size={14} />{/if}
                                    {armed ? $_('onboarding.settings.cancelArmed') : replayActionLabel(item)}
                                </button>
                            </div>
                        {/each}
                    </div>
                </section>
            {/each}
        </div>
    {/if}
</section>
