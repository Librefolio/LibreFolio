<script lang="ts">
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import {CheckCircle2, Compass, RotateCcw, X} from 'lucide-svelte';
    import {appBootstrap} from '$lib/features/onboarding/appBootstrap.svelte';
    import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {onboarding} from '$lib/stores/app/onboarding.svelte';
    import type {OnboardingFlow, OnboardingProgressItem} from '$lib/types/onboarding';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';

    let busyFlow = $state<OnboardingFlow | 'all' | null>(null);
    let error = $state<string | null>(null);
    let replayRevision = $state(0);

    const stepTitleKeys: Record<string, string> = {
        'transaction.bulk.workspace': 'onboarding.transactionBulkGuide.steps.workspace.title',
        'transaction.bulk.validation': 'onboarding.transactionBulkGuide.steps.validation.title',
        'transaction.bulk.selection': 'onboarding.transactionBulkGuide.steps.selection.title',
        'transaction.bulk.save': 'onboarding.transactionBulkGuide.steps.save.title',
        'import.upload': 'onboarding.importGuide.steps.upload.title',
        'import.select': 'onboarding.importGuide.steps.select.title',
        'import.analyze': 'onboarding.importGuide.steps.analyze.title',
        'import.assets': 'onboarding.importGuide.steps.assets.title',
        'import.fix': 'onboarding.importGuide.steps.fix.title',
        'import.duplicates': 'onboarding.importGuide.steps.duplicates.title',
        'import.review': 'onboarding.importGuide.steps.review.title',
        'import.gapFix': 'onboarding.importGuide.steps.gapFix.title',
        'import.bulk': 'onboarding.importGuide.steps.bulk.title',
    };

    let flows = $derived(onboarding.progress?.flows ?? []);
    let flowGroups = $derived([
        {key: 'setup', items: flows.filter((item) => item.flow === 'welcome')},
        {key: 'core', items: flows.filter((item) => item.flow === 'intro_tour')},
        {
            key: 'transactions',
            items: flows.filter((item) => ['transactions_page_guide', 'transaction_create_guide', 'transaction_bulk_guide', 'import_guide'].includes(item.flow)),
        },
        {key: 'broker', items: flows.filter((item) => ['broker_page_guide', 'broker_guide', 'broker_detail_guide'].includes(item.flow))},
        {key: 'fx', items: flows.filter((item) => ['fx_page_guide', 'fx_guide', 'fx_detail_guide'].includes(item.flow))},
        {key: 'asset', items: flows.filter((item) => ['asset_page_guide', 'asset_guide', 'asset_detail_guide'].includes(item.flow))},
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
                if (!onboarding.startReplay('welcome', item.current_version, 'welcome', undefined, undefined, 'replay')) {
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
        return $_('onboarding.settings.armedAtNextTrigger', {
            values: {flow: $_(`onboarding.flows.${item.flow}`)},
        });
    }

    function replayActionLabel(item: OnboardingProgressItem): string {
        if (!['welcome', 'intro_tour'].includes(item.flow)) {
            return $_('onboarding.settings.replayNextTrigger');
        }
        return $_('onboarding.settings.replay');
    }

    function completedCount(items: OnboardingProgressItem[]): number {
        return items.filter((item) => item.status === 'completed' && !item.update_available).length;
    }

    function completedStepCount(item: OnboardingProgressItem): number {
        return item.steps?.filter((step) => step.status !== 'pending' && !step.update_available).length ?? 0;
    }

    async function replayAll(): Promise<void> {
        busyFlow = 'all';
        error = null;
        const started: Array<{flow: OnboardingFlow; version: number}> = [];
        try {
            for (const item of flows) {
                const startedReplay = item.flow === 'intro_tour' ? onboardingGuide.prepareIntroReplay() : item.flow === 'welcome' ? onboarding.startReplay(item.flow, item.current_version, 'welcome', undefined, undefined, 'replay') : onboardingGuide.armReplay(item.flow);
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

<section class="rounded-2xl border border-lf-subtle bg-lf-card p-4 text-lf-primary" data-testid="onboarding-replay-section" data-busy={busyFlow ? 'true' : 'false'} aria-busy={busyFlow !== null} use:guideAnchor={'onboarding.settings'}>
    <div class="flex flex-col gap-3 border-b border-lf-subtle pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div class="flex gap-3">
            <Compass class="mt-0.5 shrink-0 text-lf-link" size={20} />
            <div>
                <h4 class="font-semibold text-lf-primary">
                    {$_('onboarding.settings.title')}
                </h4>
                <p class="mt-1 text-sm text-lf-muted">
                    {$_('onboarding.settings.description')}
                </p>
            </div>
        </div>
        <button
            type="button"
            class="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-lf-input px-3 py-2 text-sm font-medium text-lf-secondary hover:bg-lf-hover disabled:opacity-50"
            disabled={busyFlow !== null || flows.length === 0}
            onclick={replayAll}
            data-testid="onboarding-replay-all"
        >
            <RotateCcw size={15} />
            {$_('onboarding.settings.replayAll')}
        </button>
    </div>

    {#if error}
        <div class="mt-4 rounded-lg border border-lf-danger-line bg-lf-danger-soft px-3 py-2 text-sm text-lf-danger-on-soft" role="alert" data-testid="onboarding-replay-error">
            {error}
        </div>
    {/if}

    {#if onboarding.state === 'error' && flows.length === 0}
        <div class="mt-4 flex items-center justify-between gap-3" data-testid="onboarding-replay-load-error">
            <span class="text-sm text-lf-secondary">
                {onboarding.error ?? $_('onboarding.errors.loadDescription')}
            </span>
            <button type="button" class="rounded-lg bg-lf-action px-3 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50" disabled={busyFlow !== null} onclick={retryLoad} data-testid="onboarding-replay-retry">
                {$_('common.retry')}
            </button>
        </div>
    {:else}
        <div class="mt-2 space-y-5">
            {#each flowGroups as group (group.key)}
                <details class="rounded-xl border border-lf-subtle px-3" open={group.key === 'setup' || group.key === 'core'} data-testid={`onboarding-group-${group.key}`}>
                    <summary class="flex cursor-pointer items-center justify-between gap-3 py-3">
                        <span id={`onboarding-group-${group.key}`} class="text-xs font-semibold uppercase tracking-wide text-lf-muted">
                            {$_(`onboarding.settings.groups.${group.key}`)}
                        </span>
                        <span class="text-xs text-lf-muted" data-testid={`onboarding-group-${group.key}-progress`}>
                            {$_('onboarding.settings.groupProgress', {
                                values: {
                                    completed: completedCount(group.items),
                                    total: group.items.length,
                                },
                            })}
                        </span>
                    </summary>
                    <div class="divide-y divide-lf-subtle border-t border-lf-subtle">
                        {#each group.items as item (item.flow)}
                            {@const armed = replayIsArmed(item)}
                            <div class="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between" data-testid={`onboarding-flow-${item.flow}`} data-status={item.status} data-version={item.version} data-current-version={item.current_version}>
                                <div>
                                    <div class="flex flex-wrap items-center gap-2">
                                        <span class="font-medium text-lf-primary">
                                            {$_(`onboarding.flows.${item.flow}`)}
                                        </span>
                                        <span class="rounded-full bg-lf-panel px-2 py-0.5 text-xs text-lf-secondary" data-testid={`onboarding-flow-${item.flow}-status`}>
                                            {$_(`onboarding.status.${item.status}`)}
                                        </span>
                                        {#if item.update_available}
                                            <span class="rounded-full bg-lf-warning-soft px-2 py-0.5 text-xs font-medium text-lf-warning-on-soft" data-testid={`onboarding-flow-${item.flow}-update`}>
                                                {$_('onboarding.settings.updateAvailable')}
                                            </span>
                                        {/if}
                                    </div>
                                    {#if armed}
                                        <p class="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-lf-success-soft px-2.5 py-1.5 text-sm font-medium text-lf-success-on-soft" data-testid={`onboarding-flow-${item.flow}-armed`}>
                                            <CheckCircle2 size={15} />
                                            {armedText(item)}
                                        </p>
                                    {/if}
                                    <p class="mt-1 text-xs text-lf-muted">
                                        {$_('onboarding.settings.version', {
                                            values: {
                                                seen: item.version,
                                                current: item.current_version,
                                            },
                                        })}
                                    </p>
                                    {#if item.steps?.length}
                                        <details class="mt-2 text-xs text-lf-muted" data-testid={`onboarding-flow-${item.flow}-steps`}>
                                            <summary class="cursor-pointer font-medium">
                                                {$_('onboarding.settings.groupProgress', {
                                                    values: {
                                                        completed: completedStepCount(item),
                                                        total: item.steps.length,
                                                    },
                                                })}
                                            </summary>
                                            <ul class="mt-2 space-y-1.5 border-l border-lf-subtle pl-3">
                                                {#each item.steps as step (step.step_id)}
                                                    <li class="flex items-center justify-between gap-3" data-testid={`onboarding-step-${item.flow}-${step.step_id}`}>
                                                        <span>{$_(stepTitleKeys[step.step_id] ?? step.step_id)}</span>
                                                        <span class="rounded-full bg-lf-panel px-2 py-0.5">
                                                            {$_(`onboarding.status.${step.status}`)}
                                                        </span>
                                                    </li>
                                                {/each}
                                            </ul>
                                        </details>
                                    {/if}
                                </div>
                                <button
                                    type="button"
                                    class="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-lf-input px-3 py-2 text-sm font-medium text-lf-secondary hover:bg-lf-hover disabled:opacity-50"
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
                </details>
            {/each}
        </div>
    {/if}
</section>
