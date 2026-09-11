import {goto} from '$app/navigation';
import {onboardingApi} from '$lib/features/onboarding/onboardingApi';
import {ASSET_GUIDE_STEP_IDS, BROKER_GUIDE_STEP_IDS, CORE_TOUR_STEP_IDS, firstGuideStep, FX_GUIDE_STEP_IDS, guideSteps, IMPORT_GUIDE_STEP_IDS, type GuideStepId, type GuidedOnboardingFlow, type ImportGuideStepId} from '$lib/features/onboarding/onboardingGuideCatalog';
import {registerClientSessionReset} from '$lib/stores/app/clientSession';
import {onboarding} from '$lib/stores/app/onboarding.svelte';
import {isOnboardingProgressDue, type OnboardingApi, type OnboardingProgressItem} from '$lib/types/onboarding';

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
    let introAttempted = false;

    function flowProgress(flow: GuidedOnboardingFlow): OnboardingProgressItem | null {
        return controller.findFlow(flow);
    }

    function activate(flow: ActiveOnboardingGuide['flow'], version: number, stepId: GuideStepId, mode: ActiveOnboardingGuide['mode'], returnTo?: string, progress?: {current: number; total: number}): boolean {
        const normalizedReturnTo = safeReturnTo(returnTo);
        if (!controller.startReplay(flow, version, stepId, normalizedReturnTo)) {
            error = 'onboarding.errors.replayStart';
            return false;
        }
        active = {
            flow,
            version,
            stepId,
            mode,
            ...(normalizedReturnTo ? {returnTo: normalizedReturnTo} : {}),
            ...(progress ? {progress} : {}),
        };
        error = null;
        return true;
    }

    function maybeStartIntro(returnTo?: string): boolean {
        if (active) return active.flow === 'intro_tour';
        if (introAttempted) return false;
        const progress = flowProgress('intro_tour');
        if (!progress) return false;

        const replay = controller.resumeReplay('intro_tour', progress.current_version, CORE_TOUR_STEP_IDS, CORE_TOUR_STEP_IDS[0]);
        if (replay) {
            const resumedReturnTo = safeReturnTo(replay.returnTo ?? returnTo);
            introAttempted = true;
            active = {
                flow: 'intro_tour',
                version: replay.version,
                stepId: replay.stepId as IntroTourStepId,
                mode: isOnboardingProgressDue(progress) ? 'automatic' : 'replay',
                ...(resumedReturnTo ? {returnTo: resumedReturnTo} : {}),
            };
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
        return controller.startReplay('intro_tour', progress.current_version, CORE_TOUR_STEP_IDS[0]);
    }

    function maybeStartContextual(flow: Extract<GuidedOnboardingFlow, 'broker_guide' | 'fx_guide' | 'asset_guide'>): boolean {
        if (active) return active.flow === flow;
        const progress = flowProgress(flow);
        if (!progress) return false;
        const steps = guideSteps(flow);
        const replay = controller.resumeReplay(flow, progress.current_version, steps, steps[0]);
        if (replay) {
            active = {
                flow,
                version: replay.version,
                stepId: replay.stepId as GuideStepId,
                mode: isOnboardingProgressDue(progress) ? 'automatic' : 'replay',
            };
            error = null;
            return true;
        }
        if (!isOnboardingProgressDue(progress)) return false;
        return activate(flow, progress.current_version, steps[0], 'automatic');
    }

    function startImportAt(stepId: ImportGuideStepId, stepProgress?: {current: number; total: number}): boolean {
        if (active && active.flow !== 'import_guide') return false;
        const flowState = flowProgress('import_guide');
        if (!flowState) return false;
        const hasReplay = controller.hasReplay('import_guide', flowState.current_version);
        if (!isOnboardingProgressDue(flowState) && !hasReplay) return false;
        return activate('import_guide', flowState.current_version, stepId, isOnboardingProgressDue(flowState) ? 'automatic' : 'replay', undefined, stepProgress);
    }

    function armReplay(flow: GuidedOnboardingFlow): boolean {
        const progress = flowProgress(flow);
        if (!progress) {
            error = 'onboarding.errors.progressUnavailable';
            return false;
        }
        const started = controller.startReplay(flow, progress.current_version, firstGuideStep(flow));
        error = started ? null : 'onboarding.errors.replayStart';
        return started;
    }

    function startImportReplay(): boolean {
        return armReplay('import_guide');
    }

    function setStep(stepId: GuideStepId, progress?: {current: number; total: number}): void {
        if (!active) return;
        const stepChanged = active.stepId !== stepId;
        const progressChanged = progress && (active.progress?.current !== progress.current || active.progress?.total !== progress.total);
        if (!stepChanged && !progressChanged) return;
        active = {...active, stepId, ...(progress ? {progress} : {})};
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
        const steps = guideSteps(active.flow);
        const index = steps.indexOf(active.stepId);
        if (index < 0 || index >= steps.length - 1) return;
        setStep(steps[index + 1]);
    }

    function previous(): void {
        if (!active) return;
        const steps = guideSteps(active.flow);
        const index = steps.indexOf(active.stepId);
        if (index <= 0) return;
        setStep(steps[index - 1]);
    }

    function dismissHost(options: {restartAtFirst?: boolean} = {}): void {
        if (!active) return;
        if (options.restartAtFirst) {
            controller.updateReplayStep(firstGuideStep(active.flow));
        }
        active = null;
        actionPending = false;
        error = null;
    }

    function suspend(options: {resetImport?: boolean} = {}): void {
        dismissHost({restartAtFirst: options.resetImport});
    }

    async function finish(): Promise<string | undefined> {
        if (!active || actionPending) return undefined;
        const finishing = active;
        if (finishing.mode === 'replay') {
            controller.clearReplay(finishing.flow, finishing.version);
            active = null;
            error = null;
            return finishing.returnTo;
        }
        const progress = flowProgress(finishing.flow);
        if (!progress) {
            error = 'onboarding.errors.progressUnavailable';
            return undefined;
        }
        actionPending = true;
        error = null;
        try {
            const completed = await controller.complete(api, finishing.flow, progress.current_version);
            if (!completed) return undefined;
            controller.clearReplay(finishing.flow, finishing.version);
            active = null;
            return finishing.returnTo;
        } catch (actionError) {
            error = 'onboarding.errors.complete';
            return undefined;
        } finally {
            actionPending = false;
        }
    }

    async function skip(): Promise<boolean> {
        if (!active || actionPending) return false;
        const skipping = active;
        if (skipping.mode === 'replay') {
            controller.clearReplay(skipping.flow, skipping.version);
            active = null;
            error = null;
            return true;
        }
        const progress = flowProgress(skipping.flow);
        if (!progress) {
            error = 'onboarding.errors.progressUnavailable';
            return false;
        }
        actionPending = true;
        error = null;
        try {
            const skipped = await controller.skip(api, skipping.flow, progress.current_version);
            if (!skipped) return false;
            controller.clearReplay(skipping.flow, skipping.version);
            active = null;
            return true;
        } catch (actionError) {
            error = 'onboarding.errors.skip';
            return false;
        } finally {
            actionPending = false;
        }
    }

    async function exit(): Promise<boolean> {
        return skip();
    }

    async function navigateAfterFinish(returnTo?: string): Promise<void> {
        await navigate(safeReturnTo(returnTo) ?? '/dashboard');
    }

    function reset(): void {
        active = null;
        actionPending = false;
        error = null;
        introAttempted = false;
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
        maybeStartIntro,
        startIntroReplay,
        prepareIntroReplay,
        maybeStartContextual,
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
