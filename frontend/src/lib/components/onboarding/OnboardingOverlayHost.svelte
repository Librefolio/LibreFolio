<script lang="ts">
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_, locale} from '$lib/i18n';
    import OnboardingCoachmark from './OnboardingCoachmark.svelte';
    import OnboardingIntroScene from './OnboardingIntroScene.svelte';
    import {onboardingGuide, type GuideStepId} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {guideSteps, ONBOARDING_GUIDE_CATALOG} from '$lib/features/onboarding/onboardingGuideCatalog';
    import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';

    interface Props {
        currentPath?: string;
        onrequestsidebar?: (open: boolean) => void;
    }

    interface StepPresentation {
        anchorId: string;
        titleKey: string;
        descriptionKey: string;
        route?: string;
        hostRoute?: string;
        openSidebar?: boolean;
        allowedModalDepth: number;
    }

    let {currentPath = '', onrequestsidebar = () => {}}: Props = $props();

    const steps: Partial<Record<GuideStepId, StepPresentation>> = {
        'intro.dashboard': {
            anchorId: 'page.dashboard',
            titleKey: 'onboarding.tour.steps.dashboard.title',
            descriptionKey: 'onboarding.tour.steps.dashboard.description',
            route: '/dashboard',
            allowedModalDepth: 0,
        },
        'intro.navigation': {
            anchorId: 'nav.toggle.desktop',
            titleKey: 'onboarding.tour.steps.navigation.title',
            descriptionKey: 'onboarding.tour.steps.navigation.description',
            route: '/dashboard',
            allowedModalDepth: 0,
        },
        'intro.transactions_nav': {
            anchorId: 'nav.transactions',
            titleKey: 'onboarding.tour.steps.transactionsNav.title',
            descriptionKey: 'onboarding.tour.steps.transactionsNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.brokers_nav': {
            anchorId: 'nav.brokers',
            titleKey: 'onboarding.tour.steps.brokersNav.title',
            descriptionKey: 'onboarding.tour.steps.brokersNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.fx_nav': {
            anchorId: 'nav.fx',
            titleKey: 'onboarding.tour.steps.fxNav.title',
            descriptionKey: 'onboarding.tour.steps.fxNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.assets_nav': {
            anchorId: 'nav.assets',
            titleKey: 'onboarding.tour.steps.assetsNav.title',
            descriptionKey: 'onboarding.tour.steps.assetsNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.tools_nav': {
            anchorId: 'nav.tools',
            titleKey: 'onboarding.tour.steps.toolsNav.title',
            descriptionKey: 'onboarding.tour.steps.toolsNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.settings_nav': {
            anchorId: 'nav.settings',
            titleKey: 'onboarding.tour.steps.settingsNav.title',
            descriptionKey: 'onboarding.tour.steps.settingsNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'broker.overview': {
            anchorId: 'broker.modal',
            titleKey: 'onboarding.brokerGuide.steps.overview.title',
            descriptionKey: 'onboarding.brokerGuide.steps.overview.description',
            hostRoute: '/brokers',
            allowedModalDepth: 1,
        },
        'broker.plugin': {
            anchorId: 'broker.plugin',
            titleKey: 'onboarding.brokerGuide.steps.plugin.title',
            descriptionKey: 'onboarding.brokerGuide.steps.plugin.description',
            hostRoute: '/brokers',
            allowedModalDepth: 1,
        },
        'broker.icon': {
            anchorId: 'broker.icon',
            titleKey: 'onboarding.brokerGuide.steps.icon.title',
            descriptionKey: 'onboarding.brokerGuide.steps.icon.description',
            hostRoute: '/brokers',
            allowedModalDepth: 1,
        },
        'fx.currencies': {
            anchorId: 'fx.currencies',
            titleKey: 'onboarding.fxGuide.steps.currencies.title',
            descriptionKey: 'onboarding.fxGuide.steps.currencies.description',
            hostRoute: '/fx',
            allowedModalDepth: 1,
        },
        'fx.providers': {
            anchorId: 'fx.providers',
            titleKey: 'onboarding.fxGuide.steps.providers.title',
            descriptionKey: 'onboarding.fxGuide.steps.providers.description',
            hostRoute: '/fx',
            allowedModalDepth: 1,
        },
        'asset.search': {
            anchorId: 'asset.search',
            titleKey: 'onboarding.assetGuide.steps.search.title',
            descriptionKey: 'onboarding.assetGuide.steps.search.description',
            hostRoute: '/assets',
            allowedModalDepth: 1,
        },
        'asset.identity': {
            anchorId: 'asset.identity',
            titleKey: 'onboarding.assetGuide.steps.identity.title',
            descriptionKey: 'onboarding.assetGuide.steps.identity.description',
            hostRoute: '/assets',
            allowedModalDepth: 1,
        },
        'asset.provider': {
            anchorId: 'asset.provider',
            titleKey: 'onboarding.assetGuide.steps.provider.title',
            descriptionKey: 'onboarding.assetGuide.steps.provider.description',
            hostRoute: '/assets',
            allowedModalDepth: 1,
        },
        'import.upload': {
            anchorId: 'import.action.upload',
            titleKey: 'onboarding.importGuide.steps.upload.title',
            descriptionKey: 'onboarding.importGuide.steps.upload.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.select': {
            anchorId: 'import.action.select',
            titleKey: 'onboarding.importGuide.steps.select.title',
            descriptionKey: 'onboarding.importGuide.steps.select.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.analyze': {
            anchorId: 'import.action.analyze',
            titleKey: 'onboarding.importGuide.steps.analyze.title',
            descriptionKey: 'onboarding.importGuide.steps.analyze.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.assets': {
            anchorId: 'import.action.assets',
            titleKey: 'onboarding.importGuide.steps.assets.title',
            descriptionKey: 'onboarding.importGuide.steps.assets.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.fix': {
            anchorId: 'import.action.fix',
            titleKey: 'onboarding.importGuide.steps.fix.title',
            descriptionKey: 'onboarding.importGuide.steps.fix.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.duplicates': {
            anchorId: 'import.action.duplicates',
            titleKey: 'onboarding.importGuide.steps.duplicates.title',
            descriptionKey: 'onboarding.importGuide.steps.duplicates.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.review': {
            anchorId: 'import.action.review',
            titleKey: 'onboarding.importGuide.steps.review.title',
            descriptionKey: 'onboarding.importGuide.steps.review.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.bulk': {
            anchorId: 'import.bulk.save-all',
            titleKey: 'onboarding.importGuide.steps.bulk.title',
            descriptionKey: 'onboarding.importGuide.steps.bulk.description',
            hostRoute: '/transactions',
            allowedModalDepth: 1,
        },
    };

    let modalDepth = $state(0);
    let mobile = $state(false);
    let activeLocale = $derived($locale);
    let active = $derived(onboardingGuide.active);
    let step = $derived(active ? steps[active.stepId] : null);
    let activeSteps = $derived(active ? guideSteps(active.flow).filter((stepId) => stepId !== 'intro.scene') : []);
    let anchor = $derived.by(() => {
        void activeLocale;
        void guideAnchors.revision;
        if (active?.stepId === 'intro.navigation') {
            return guideAnchors.get(mobile ? 'nav.toggle.mobile' : 'nav.toggle.desktop');
        }
        return step ? guideAnchors.get(step.anchorId) : null;
    });
    let suspended = $derived(step != null && modalDepth > step.allowedModalDepth);
    let stepIndex = $derived(active ? (activeSteps as readonly GuideStepId[]).indexOf(active.stepId) : -1);
    let lastStep = $derived(stepIndex === activeSteps.length - 1);
    let showNext = $derived(active?.flow !== 'import_guide' || active?.stepId === 'import.bulk');
    let presentation = $derived(active ? ONBOARDING_GUIDE_CATALOG[active.flow].presentation : 'pointer');
    let progressCurrent = $derived(active?.progress?.current ?? Math.max(stepIndex + 1, 1));
    let progressTotal = $derived(active?.progress?.total ?? activeSteps.length);
    let actionHint = $derived(active?.flow === 'import_guide' ? translate('onboarding.guide.useWizardAction') : presentation === 'pointer' ? translate('onboarding.guide.exploreThenContinue') : '');
    let closeLabel = $derived(translate(active?.mode === 'automatic' ? 'onboarding.actions.skipCurrentTour' : 'onboarding.actions.exitTour'));

    function translate(key: string): string {
        void activeLocale;
        return $_(key);
    }

    function translateValues(key: string, values: Record<string, string | number>): string {
        void activeLocale;
        return $_(key, {values});
    }

    function updateModalDepth() {
        modalDepth = Number(document.body.dataset.modalScrollLockCount || '0');
    }

    onMount(() => {
        updateModalDepth();
        const media = window.matchMedia('(max-width: 1023px)');
        const updateMobile = () => (mobile = media.matches);
        updateMobile();
        media.addEventListener('change', updateMobile);
        const observer = new MutationObserver(updateModalDepth);
        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ['data-modal-scroll-lock-count'],
        });
        return () => {
            observer.disconnect();
            media.removeEventListener('change', updateMobile);
        };
    });

    $effect(() => {
        const current = active;
        const presentation = step;
        if (current?.stepId === 'intro.scene') {
            onrequestsidebar(false);
            if (currentPath !== '/dashboard') void goto('/dashboard');
            return;
        }
        if (current && presentation?.hostRoute && currentPath.split('?')[0] !== presentation.hostRoute) {
            onboardingGuide.dismissHost({restartAtFirst: true});
            return;
        }
        if (!current || !presentation || current.flow !== 'intro_tour') return;
        onrequestsidebar(presentation.openSidebar === true);
        if (presentation.route && currentPath !== presentation.route) {
            void goto(presentation.route);
        }
    });

    async function handleNext() {
        if (!active) return;
        if (!lastStep) {
            onboardingGuide.next();
            return;
        }
        const finishingFlow = active.flow;
        const returnTo = await onboardingGuide.finish();
        if (!onboardingGuide.error) {
            onrequestsidebar(false);
            if (finishingFlow === 'intro_tour') {
                await onboardingGuide.navigateAfterFinish(returnTo);
            }
        }
    }

    async function handleExit() {
        if (!active) return;
        const exiting = active;
        if (await onboardingGuide.exit()) {
            onrequestsidebar(false);
            if (exiting.flow === 'intro_tour') {
                await onboardingGuide.navigateAfterFinish(exiting.returnTo);
            }
        }
    }
</script>

{#if active?.stepId === 'intro.scene'}
    <OnboardingIntroScene open={true} busy={onboardingGuide.actionPending} error={onboardingGuide.error ? translate(onboardingGuide.error) : null} {closeLabel} onstart={() => onboardingGuide.next()} onclose={handleExit} />
{:else if active && step}
    <OnboardingCoachmark
        open={!suspended}
        {anchor}
        stepId={active.stepId}
        {presentation}
        title={translate(step.titleKey)}
        description={translate(step.descriptionKey)}
        {actionHint}
        progressLabel={translateValues('onboarding.tour.progress', {current: progressCurrent, total: progressTotal})}
        backLabel={translate('onboarding.actions.back')}
        nextLabel={lastStep || active.stepId === 'import.bulk' ? translate('onboarding.actions.finish') : translate('onboarding.actions.next')}
        {closeLabel}
        busyLabel={translate('onboarding.guide.waiting')}
        error={onboardingGuide.error ? translate(onboardingGuide.error) : null}
        showBack={active.flow !== 'import_guide'}
        backDisabled={stepIndex <= 0}
        {showNext}
        showSkip={false}
        showClose={true}
        busy={onboardingGuide.actionPending}
        onback={() => onboardingGuide.previous()}
        onnext={handleNext}
        onclose={handleExit}
    />
{/if}
