import {goto} from '$app/navigation';
import {onboardingApi} from '$lib/features/onboarding/onboardingApi';
import {
    ASSET_GUIDE_STEP_IDS,
    BROKER_GUIDE_STEP_IDS,
    CORE_TOUR_STEP_IDS,
    firstGuideStep,
    FX_GUIDE_STEP_IDS,
    guideSteps,
    IMPORT_GUIDE_STEP_IDS,
    isStepManagedFlow,
    type ContextualOnboardingFlow,
    type GuideStepId,
    type GuidedOnboardingFlow,
    type ImportGuideStepId,
} from '$lib/features/onboarding/onboardingGuideCatalog';
import {registerClientSessionReset} from '$lib/stores/app/clientSession';
import {onboarding} from '$lib/stores/app/onboarding.svelte';
import {isOnboardingProgressDue, isOnboardingStepProgressDue, type OnboardingApi, type OnboardingProgressItem} from '$lib/types/onboarding';

export {ASSET_GUIDE_STEP_IDS, BROKER_GUIDE_STEP_IDS, CORE_TOUR_STEP_IDS, FX_GUIDE_STEP_IDS, IMPORT_GUIDE_STEP_IDS};
export const INTRO_TOUR_STEP_IDS = CORE_TOUR_STEP_IDS;
export type IntroTourStepId = (typeof CORE_TOUR_STEP_IDS)[number];
export type {GuideStepId, ImportGuideStepId};

export interface ActiveOnboardingGuide {
    flow: GuidedOnboardingFlow;
    version: number;
    stepId: GuideStepId;
    mode: 'automatic' | 'replay';
    returnTo?: string;
    progress?: {
        current: number;
        total: number;
    };
}

interface QueuedContextualGuide {
    flow: ContextualOnboardingFlow;
    stepId?: GuideStepId;
}

interface OnboardingGuideDependencies {
    controller?: typeof onboarding;
    api?: OnboardingApi;
    navigate?: typeof goto;
}

function safeReturnTo(value: string | null | undefined): string | undefined {
    if (!value || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) {
        return undefined;
    }
    return value;
}

export function createOnboardingGuide(dependencies: OnboardingGuideDependencies = {}) {
    const controller = dependencies.controller ?? onboarding;
    const api = dependencies.api ?? onboardingApi;
    const navigate = dependencies.navigate ?? goto;

    let active = $state<ActiveOnboardingGuide | null>(null);
    let actionPending = $state(false);
    let error = $state<string | null>(null);
    let queuedGuides = $state<QueuedContextualGuide[]>([]);
    let introAttempted = false;
    let actionSequence = 0;
    let activeGeneration = 0;

    function replaceActive(next: ActiveOnboardingGuide | null): void {
        active = next;
        activeGeneration += 1;
    }

    function flowProgress(flow: GuidedOnboardingFlow): OnboardingProgressItem | null {
        return controller.findFlow(flow);
    }

    function stepIsDue(flow: GuidedOnboardingFlow, stepId: GuideStepId): boolean {
        return isOnboardingStepProgressDue(controller.findStep(flow, stepId));
    }

    function activate(flow: ActiveOnboardingGuide['flow'], version: number, stepId: GuideStepId, mode: ActiveOnboardingGuide['mode'], returnTo?: string, progress?: {current: number; total: number}, remainingStepIds?: GuideStepId[]): boolean {
        const normalizedReturnTo = safeReturnTo(returnTo);
        if (!controller.startReplay(flow, version, stepId, normalizedReturnTo, remainingStepIds, mode)) {
            error = 'onboarding.errors.replayStart';
            return false;
        }
        replaceActive({
            flow,
            version,
            stepId,
            mode,
            ...(normalizedReturnTo ? {returnTo: normalizedReturnTo} : {}),
            ...(progress ? {progress} : {}),
        });
        error = null;
        return true;
    }

    function maybeStartIntro(returnTo?: string): boolean {
        if (active) return active.flow === 'intro_tour';
        if (introAttempted) return false;
        const progress = flowProgress('intro_tour');
        if (!progress) return false;

        let replay = controller.resumeReplay('intro_tour', progress.current_version, CORE_TOUR_STEP_IDS, CORE_TOUR_STEP_IDS[0]);
        if (replay?.mode !== 'replay' && !isOnboardingProgressDue(progress)) {
            controller.clearReplay('intro_tour', progress.current_version);
            replay = null;
        }
        if (replay) {
            const resumedReturnTo = safeReturnTo(replay.returnTo ?? returnTo);
            introAttempted = true;
            replaceActive({
                flow: 'intro_tour',
                version: replay.version,
                stepId: replay.stepId as IntroTourStepId,
                mode: replay.mode ?? (isOnboardingProgressDue(progress) ? 'automatic' : 'replay'),
                ...(resumedReturnTo ? {returnTo: resumedReturnTo} : {}),
            });
            return true;
        }
        if (!isOnboardingProgressDue(progress)) return false;

        introAttempted = true;
        return activate('intro_tour', progress.current_version, CORE_TOUR_STEP_IDS[0], 'automatic', returnTo);
    }

    function startIntroReplay(returnTo?: string): boolean {
        const progress = flowProgress('intro_tour');
        if (!progress) return false;
        introAttempted = true;
        return activate('intro_tour', progress.current_version, CORE_TOUR_STEP_IDS[0], 'replay', returnTo);
    }

    function prepareIntroReplay(): boolean {
        const progress = flowProgress('intro_tour');
        if (!progress) return false;
        introAttempted = false;
        return controller.startReplay('intro_tour', progress.current_version, CORE_TOUR_STEP_IDS[0], undefined, undefined, 'replay');
    }

    function maybeStartContextual(flow: ContextualOnboardingFlow, requestedStepId?: GuideStepId): boolean {
        if (active) {
            if (active.flow === flow && (!requestedStepId || active.stepId === requestedStepId)) return true;
            queueContextual(flow, requestedStepId);
            return false;
        }
        const progress = flowProgress(flow);
        if (!progress) return false;
        const steps = guideSteps(flow);
        let replay = controller.resumeReplay(flow, progress.current_version, steps, steps[0]);
        if (isStepManagedFlow(flow)) {
            const replaySteps = (replay?.remainingStepIds ?? (replay ? [replay.stepId] : [])) as GuideStepId[];
            const explicitReplay = replay?.mode === 'replay';
            const stepId = explicitReplay ? (requestedStepId ? (replaySteps.includes(requestedStepId) ? requestedStepId : undefined) : steps.find((candidate) => replaySteps.includes(candidate))) : (requestedStepId ?? steps.find((candidate) => stepIsDue(flow, candidate)));
            if (!stepId) {
                if (replay && !explicitReplay) controller.clearReplay(flow, progress.current_version);
                return false;
            }
            const replayingStep = explicitReplay && replaySteps.includes(stepId);
            if (!stepIsDue(flow, stepId) && !replayingStep) return false;
            const mode: ActiveOnboardingGuide['mode'] = explicitReplay ? 'replay' : 'automatic';
            replaceActive({
                flow,
                version: progress.current_version,
                stepId,
                mode,
            });
            if (!controller.startReplay(flow, progress.current_version, stepId, undefined, replayingStep ? replaySteps : [stepId], mode)) {
                replaceActive(null);
                error = 'onboarding.errors.replayStart';
                return false;
            }
            error = null;
            return true;
        }
        if (replay?.mode !== 'replay' && !isOnboardingProgressDue(progress)) {
            controller.clearReplay(flow, progress.current_version);
            replay = null;
        }
        if (replay) {
            replaceActive({
                flow,
                version: replay.version,
                stepId: replay.stepId as GuideStepId,
                mode: replay.mode ?? (isOnboardingProgressDue(progress) ? 'automatic' : 'replay'),
            });
            error = null;
            return true;
        }
        if (!isOnboardingProgressDue(progress)) return false;
        return activate(flow, progress.current_version, steps[0], 'automatic');
    }

    function queueContextual(flow: ContextualOnboardingFlow, stepId?: GuideStepId): void {
        if (!queuedGuides.some((queued) => queued.flow === flow && queued.stepId === stepId)) {
            queuedGuides = [...queuedGuides, {flow, ...(stepId ? {stepId} : {})}];
        }
    }

    function maybeStartQueued(expectedFlow?: ContextualOnboardingFlow, expectedStepId?: GuideStepId): boolean {
        if (active || queuedGuides.length === 0) return false;
        const index = expectedFlow ? queuedGuides.findIndex((queued) => queued.flow === expectedFlow && (!expectedStepId || queued.stepId === expectedStepId)) : 0;
        if (index < 0) return false;
        const queued = queuedGuides[index];
        const started = maybeStartContextual(queued.flow, queued.stepId);
        if (started || flowProgress(queued.flow)) {
            queuedGuides = queuedGuides.filter((_, queuedIndex) => queuedIndex !== index);
        }
        return started;
    }

    function clearQueued(flow?: ContextualOnboardingFlow, stepId?: GuideStepId): void {
        if (!flow) {
            if (queuedGuides.length > 0) queuedGuides = [];
            return;
        }
        if (queuedGuides.some((queued) => queued.flow === flow && (!stepId || queued.stepId === stepId))) {
            queuedGuides = queuedGuides.filter((queued) => queued.flow !== flow || (stepId && queued.stepId !== stepId));
        }
    }

    function startImportAt(stepId: ImportGuideStepId, stepProgress?: {current: number; total: number}): boolean {
        if (active && active.flow !== 'import_guide') return false;
        const flowState = flowProgress('import_guide');
        if (!flowState) return false;
        const replay = controller.resumeReplay('import_guide', flowState.current_version, IMPORT_GUIDE_STEP_IDS, IMPORT_GUIDE_STEP_IDS[0]);
        const replaySteps = replay?.remainingStepIds ?? (replay ? [replay.stepId] : []);
        if (replay?.mode === 'replay' && !replaySteps.includes(stepId)) return false;
        const replayingStep = replay?.mode === 'replay' && replaySteps.includes(stepId);
        if (!stepIsDue('import_guide', stepId) && !replayingStep) {
            if (replay?.mode !== 'replay') controller.clearReplay('import_guide', flowState.current_version);
            return false;
        }
        const mode: ActiveOnboardingGuide['mode'] = replayingStep && replay?.mode === 'replay' ? 'replay' : 'automatic';
        return activate('import_guide', flowState.current_version, stepId, mode, undefined, stepProgress, (replayingStep ? replaySteps : [stepId]) as GuideStepId[]);
    }

    function armReplay(flow: GuidedOnboardingFlow): boolean {
        const progress = flowProgress(flow);
        if (!progress) {
            error = 'onboarding.errors.progressUnavailable';
            return false;
        }
        const steps = guideSteps(flow);
        const started = controller.startReplay(flow, progress.current_version, firstGuideStep(flow), undefined, isStepManagedFlow(flow) ? [...steps] : undefined, 'replay');
        error = started ? null : 'onboarding.errors.replayStart';
        return started;
    }

    function startImportReplay(): boolean {
        return armReplay('import_guide');
    }

    function setStep(stepId: GuideStepId, progress?: {current: number; total: number}): void {
        if (!active) return;
        if (isStepManagedFlow(active.flow) && active.stepId !== stepId) return;
        const stepChanged = active.stepId !== stepId;
        const progressChanged = progress && (active.progress?.current !== progress.current || active.progress?.total !== progress.total);
        if (!stepChanged && !progressChanged) return;
        replaceActive({...active, stepId, ...(progress ? {progress} : {})});
        if (stepChanged) controller.updateReplayStep(stepId);
        error = null;
    }

    function nextIntro(): void {
        if (active?.flow !== 'intro_tour') return;
        next();
    }

    function previousIntro(): void {
        if (active?.flow !== 'intro_tour') return;
        previous();
    }

    function next(): void {
        if (!active) return;
        if (isStepManagedFlow(active.flow)) return;
        const steps = guideSteps(active.flow);
        const index = steps.indexOf(active.stepId);
        if (index < 0 || index >= steps.length - 1) return;
        setStep(steps[index + 1]);
    }

    function previous(): void {
        if (!active) return;
        if (isStepManagedFlow(active.flow)) return;
        const steps = guideSteps(active.flow);
        const index = steps.indexOf(active.stepId);
        if (index <= 0) return;
        setStep(steps[index - 1]);
    }

    function dismissHost(options: {restartAtFirst?: boolean} = {}): void {
        if (!active) return;
        actionSequence += 1;
        if (options.restartAtFirst && !isStepManagedFlow(active.flow)) {
            controller.updateReplayStep(firstGuideStep(active.flow));
        }
        replaceActive(null);
        actionPending = false;
        error = null;
    }

    function suspend(options: {resetImport?: boolean} = {}): void {
        dismissHost({restartAtFirst: options.resetImport});
    }

    function consumeReplayStep(finishing: ActiveOnboardingGuide): void {
        const remaining = (controller.replay?.remainingStepIds ?? [finishing.stepId]).filter((stepId) => stepId !== finishing.stepId);
        if (remaining.length === 0) {
            controller.clearReplay(finishing.flow, finishing.version);
            return;
        }
        controller.startReplay(finishing.flow, finishing.version, remaining[0], finishing.returnTo, remaining, 'replay');
    }

    function isStillActive(candidate: ActiveOnboardingGuide): boolean {
        return active?.flow === candidate.flow && active.stepId === candidate.stepId && active.version === candidate.version;
    }

    function ownsActivation(candidate: ActiveOnboardingGuide, generation: number, operation: number): boolean {
        const replay = controller.replay;
        return operation === actionSequence && generation === activeGeneration && isStillActive(candidate) && replay?.flow === candidate.flow && replay.version === candidate.version && replay.stepId === candidate.stepId;
    }

    async function finish(): Promise<string | undefined> {
        if (!active || actionPending) return undefined;
        const finishing = active;
        const generation = activeGeneration;
        if (finishing.mode === 'replay') {
            if (isStepManagedFlow(finishing.flow)) {
                consumeReplayStep(finishing);
            } else {
                controller.clearReplay(finishing.flow, finishing.version);
            }
            replaceActive(null);
            error = null;
            return finishing.returnTo;
        }
        const progress = flowProgress(finishing.flow);
        if (!progress) {
            error = 'onboarding.errors.progressUnavailable';
            return undefined;
        }
        const operation = ++actionSequence;
        actionPending = true;
        error = null;
        try {
            const completed = isStepManagedFlow(finishing.flow) ? await controller.completeStep(api, finishing.flow, finishing.stepId, progress.current_version) : await controller.complete(api, finishing.flow, progress.current_version);
            if (!completed) return undefined;
            if (!ownsActivation(finishing, generation, operation)) return finishing.returnTo;
            controller.clearReplay(finishing.flow, finishing.version);
            replaceActive(null);
            return finishing.returnTo;
        } catch (actionError) {
            if (operation === actionSequence && isStillActive(finishing)) error = 'onboarding.errors.complete';
            return undefined;
        } finally {
            if (operation === actionSequence) actionPending = false;
        }
    }

    async function skip(): Promise<boolean> {
        if (!active || actionPending) return false;
        const skipping = active;
        const generation = activeGeneration;
        if (skipping.mode === 'replay') {
            if (isStepManagedFlow(skipping.flow)) {
                consumeReplayStep(skipping);
            } else {
                controller.clearReplay(skipping.flow, skipping.version);
            }
            replaceActive(null);
            error = null;
            return true;
        }
        const progress = flowProgress(skipping.flow);
        if (!progress) {
            error = 'onboarding.errors.progressUnavailable';
            return false;
        }
        const operation = ++actionSequence;
        actionPending = true;
        error = null;
        try {
            const skipped = isStepManagedFlow(skipping.flow) ? await controller.skipStep(api, skipping.flow, skipping.stepId, progress.current_version) : await controller.skip(api, skipping.flow, progress.current_version);
            if (!skipped) return false;
            if (!ownsActivation(skipping, generation, operation)) return true;
            controller.clearReplay(skipping.flow, skipping.version);
            replaceActive(null);
            return true;
        } catch (actionError) {
            if (operation === actionSequence && isStillActive(skipping)) error = 'onboarding.errors.skip';
            return false;
        } finally {
            if (operation === actionSequence) actionPending = false;
        }
    }

    async function exit(): Promise<boolean> {
        return skip();
    }

    async function navigateAfterFinish(returnTo?: string): Promise<void> {
        await navigate(safeReturnTo(returnTo) ?? '/dashboard');
    }

    function reset(): void {
        actionSequence += 1;
        replaceActive(null);
        actionPending = false;
        error = null;
        introAttempted = false;
        queuedGuides = [];
    }

    return {
        get active() {
            return active;
        },
        get actionPending() {
            return actionPending;
        },
        get error() {
            return error;
        },
        get queuedFlow() {
            return queuedGuides[0]?.flow ?? null;
        },
        get queuedFlows() {
            return queuedGuides.map((queued) => queued.flow);
        },
        get queuedGuides() {
            return queuedGuides;
        },
        maybeStartIntro,
        startIntroReplay,
        prepareIntroReplay,
        maybeStartContextual,
        queueContextual,
        maybeStartQueued,
        clearQueued,
        armReplay,
        startImportAt,
        startImportReplay,
        setStep,
        next,
        previous,
        nextIntro,
        previousIntro,
        dismissHost,
        suspend,
        finish,
        exit,
        skip,
        navigateAfterFinish,
        reset,
    };
}

export const onboardingGuide = createOnboardingGuide();

registerClientSessionReset('onboardingGuide', () => onboardingGuide.reset());
