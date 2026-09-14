<script lang="ts">
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_, locale} from '$lib/i18n';
    import OnboardingCoachmark from './OnboardingCoachmark.svelte';
    import OnboardingIntroScene from './OnboardingIntroScene.svelte';
    import {onboardingGuide, type GuideStepId} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {guideSteps, isCheckpointFlow, isStepManagedFlow, type GuideHighlightMode, type GuidePanelPlacement, type GuidePointerMode, type GuideScrollPolicy} from '$lib/features/onboarding/onboardingGuideCatalog';
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
        pointer?: GuidePointerMode;
        highlight?: GuideHighlightMode;
        backdrop?: boolean;
        panelPlacement?: GuidePanelPlacement;
        mobilePanelPlacement?: GuidePanelPlacement;
        scrollPolicy?: GuideScrollPolicy;
    }

    let {currentPath = '', onrequestsidebar = () => {}}: Props = $props();

    const corePresentation = {
        pointer: 'cursor',
        highlight: 'pulse',
        backdrop: true,
        panelPlacement: 'right',
        scrollPolicy: 'nearest-if-hidden',
    } as const;

    const importPresentation = {
        pointer: 'cursor',
        panelPlacement: 'top',
        scrollPolicy: 'none',
    } as const;

    const areaPresentation = {
        highlight: 'pulse',
    } as const;

    const steps: Partial<Record<GuideStepId, StepPresentation>> = {
        'intro.dashboard': {
            ...corePresentation,
            anchorId: 'nav.dashboard',
            titleKey: 'onboarding.tour.steps.dashboard.title',
            descriptionKey: 'onboarding.tour.steps.dashboard.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.navigation': {
            ...corePresentation,
            anchorId: 'nav.toggle.desktop',
            titleKey: 'onboarding.tour.steps.navigation.title',
            descriptionKey: 'onboarding.tour.steps.navigation.description',
            route: '/dashboard',
            allowedModalDepth: 0,
        },
        'intro.transactions_nav': {
            ...corePresentation,
            anchorId: 'nav.transactions',
            titleKey: 'onboarding.tour.steps.transactionsNav.title',
            descriptionKey: 'onboarding.tour.steps.transactionsNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.brokers_nav': {
            ...corePresentation,
            anchorId: 'nav.brokers',
            titleKey: 'onboarding.tour.steps.brokersNav.title',
            descriptionKey: 'onboarding.tour.steps.brokersNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.fx_nav': {
            ...corePresentation,
            mobilePanelPlacement: 'bottom',
            anchorId: 'nav.fx',
            titleKey: 'onboarding.tour.steps.fxNav.title',
            descriptionKey: 'onboarding.tour.steps.fxNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.assets_nav': {
            ...corePresentation,
            anchorId: 'nav.assets',
            titleKey: 'onboarding.tour.steps.assetsNav.title',
            descriptionKey: 'onboarding.tour.steps.assetsNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.tools_nav': {
            ...corePresentation,
            anchorId: 'nav.tools',
            titleKey: 'onboarding.tour.steps.toolsNav.title',
            descriptionKey: 'onboarding.tour.steps.toolsNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'intro.settings_nav': {
            ...corePresentation,
            mobilePanelPlacement: 'top',
            anchorId: 'nav.settings',
            titleKey: 'onboarding.tour.steps.settingsNav.title',
            descriptionKey: 'onboarding.tour.steps.settingsNav.description',
            route: '/dashboard',
            openSidebar: true,
            allowedModalDepth: 0,
        },
        'transactions.page.overview': {
            ...areaPresentation,
            anchorId: 'transactions.page.overview',
            titleKey: 'onboarding.transactionsPageGuide.steps.overview.title',
            descriptionKey: 'onboarding.transactionsPageGuide.steps.overview.description',
            hostRoute: '/transactions',
            allowedModalDepth: 0,
            panelPlacement: 'bottom',
        },
        'transactions.page.add': {
            anchorId: 'transactions.page.add',
            titleKey: 'onboarding.transactionsPageGuide.steps.add.title',
            descriptionKey: 'onboarding.transactionsPageGuide.steps.add.description',
            hostRoute: '/transactions',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'transactions.page.import': {
            anchorId: 'transactions.page.import',
            titleKey: 'onboarding.transactionsPageGuide.steps.import.title',
            descriptionKey: 'onboarding.transactionsPageGuide.steps.import.description',
            hostRoute: '/transactions',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'transactions.page.columns': {
            ...areaPresentation,
            anchorId: 'transactions.page.columns',
            titleKey: 'onboarding.transactionsPageGuide.steps.columns.title',
            descriptionKey: 'onboarding.transactionsPageGuide.steps.columns.description',
            hostRoute: '/transactions',
            allowedModalDepth: 0,
        },
        'transaction.create.basics': {
            ...areaPresentation,
            anchorId: 'transaction.create.basics',
            titleKey: 'onboarding.transactionCreateGuide.steps.basics.title',
            descriptionKey: 'onboarding.transactionCreateGuide.steps.basics.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'transaction.create.amounts': {
            ...areaPresentation,
            anchorId: 'transaction.create.amounts',
            titleKey: 'onboarding.transactionCreateGuide.steps.amounts.title',
            descriptionKey: 'onboarding.transactionCreateGuide.steps.amounts.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'transaction.create.details': {
            ...areaPresentation,
            anchorId: 'transaction.create.details',
            titleKey: 'onboarding.transactionCreateGuide.steps.details.title',
            descriptionKey: 'onboarding.transactionCreateGuide.steps.details.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'transaction.create.save': {
            anchorId: 'transaction.create.save',
            titleKey: 'onboarding.transactionCreateGuide.steps.save.title',
            descriptionKey: 'onboarding.transactionCreateGuide.steps.save.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
            pointer: 'cursor',
        },
        'transaction.bulk.workspace': {
            ...areaPresentation,
            anchorId: 'transaction.bulk.workspace',
            titleKey: 'onboarding.transactionBulkGuide.steps.workspace.title',
            descriptionKey: 'onboarding.transactionBulkGuide.steps.workspace.description',
            hostRoute: '/transactions',
            allowedModalDepth: 1,
        },
        'transaction.bulk.validation': {
            ...areaPresentation,
            anchorId: 'transaction.bulk.validation',
            titleKey: 'onboarding.transactionBulkGuide.steps.validation.title',
            descriptionKey: 'onboarding.transactionBulkGuide.steps.validation.description',
            hostRoute: '/transactions',
            allowedModalDepth: 1,
        },
        'transaction.bulk.selection': {
            ...areaPresentation,
            anchorId: 'transaction.bulk.selection',
            titleKey: 'onboarding.transactionBulkGuide.steps.selection.title',
            descriptionKey: 'onboarding.transactionBulkGuide.steps.selection.description',
            hostRoute: '/transactions',
            allowedModalDepth: 1,
        },
        'transaction.bulk.save': {
            anchorId: 'transaction.bulk.save',
            titleKey: 'onboarding.transactionBulkGuide.steps.save.title',
            descriptionKey: 'onboarding.transactionBulkGuide.steps.save.description',
            hostRoute: '/transactions',
            allowedModalDepth: 1,
            pointer: 'cursor',
            panelPlacement: 'top',
        },
        'broker.page.overview': {
            ...areaPresentation,
            anchorId: 'broker.page.overview',
            titleKey: 'onboarding.brokerPageGuide.steps.overview.title',
            descriptionKey: 'onboarding.brokerPageGuide.steps.overview.description',
            hostRoute: '/brokers',
            allowedModalDepth: 0,
        },
        'broker.page.currency': {
            ...areaPresentation,
            anchorId: 'broker.page.currency',
            titleKey: 'onboarding.brokerPageGuide.steps.currency.title',
            descriptionKey: 'onboarding.brokerPageGuide.steps.currency.description',
            hostRoute: '/brokers',
            allowedModalDepth: 0,
        },
        'broker.page.views': {
            ...areaPresentation,
            anchorId: 'broker.page.views',
            titleKey: 'onboarding.brokerPageGuide.steps.views.title',
            descriptionKey: 'onboarding.brokerPageGuide.steps.views.description',
            hostRoute: '/brokers',
            allowedModalDepth: 0,
            scrollPolicy: 'none',
        },
        'broker.page.add': {
            anchorId: 'broker.page.add',
            titleKey: 'onboarding.brokerPageGuide.steps.add.title',
            descriptionKey: 'onboarding.brokerPageGuide.steps.add.description',
            hostRoute: '/brokers',
            allowedModalDepth: 0,
            pointer: 'cursor',
            scrollPolicy: 'nearest-if-hidden',
        },
        'broker.overview': {
            ...areaPresentation,
            anchorId: 'broker.modal',
            titleKey: 'onboarding.brokerGuide.steps.overview.title',
            descriptionKey: 'onboarding.brokerGuide.steps.overview.description',
            hostRoute: '/brokers',
            allowedModalDepth: 1,
        },
        'broker.plugin': {
            ...areaPresentation,
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
            pointer: 'cursor',
        },
        'broker.detail.header': {
            ...areaPresentation,
            anchorId: 'broker.detail.header',
            titleKey: 'onboarding.brokerDetailGuide.steps.header.title',
            descriptionKey: 'onboarding.brokerDetailGuide.steps.header.description',
            hostRoute: '/brokers/',
            allowedModalDepth: 0,
        },
        'broker.detail.overview': {
            anchorId: 'broker.detail.overview',
            titleKey: 'onboarding.brokerDetailGuide.steps.overview.title',
            descriptionKey: 'onboarding.brokerDetailGuide.steps.overview.description',
            hostRoute: '/brokers/',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'broker.detail.positions': {
            anchorId: 'broker.detail.positions',
            titleKey: 'onboarding.brokerDetailGuide.steps.positions.title',
            descriptionKey: 'onboarding.brokerDetailGuide.steps.positions.description',
            hostRoute: '/brokers/',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'broker.detail.transactions': {
            anchorId: 'broker.detail.transactions',
            titleKey: 'onboarding.brokerDetailGuide.steps.transactions.title',
            descriptionKey: 'onboarding.brokerDetailGuide.steps.transactions.description',
            hostRoute: '/brokers/',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'broker.detail.info': {
            anchorId: 'broker.detail.info',
            titleKey: 'onboarding.brokerDetailGuide.steps.info.title',
            descriptionKey: 'onboarding.brokerDetailGuide.steps.info.description',
            hostRoute: '/brokers/',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'fx.page.overview': {
            ...areaPresentation,
            anchorId: 'fx.page.overview',
            titleKey: 'onboarding.fxPageGuide.steps.overview.title',
            descriptionKey: 'onboarding.fxPageGuide.steps.overview.description',
            hostRoute: '/fx',
            allowedModalDepth: 0,
        },
        'fx.page.filters': {
            ...areaPresentation,
            anchorId: 'fx.page.filters',
            titleKey: 'onboarding.fxPageGuide.steps.filters.title',
            descriptionKey: 'onboarding.fxPageGuide.steps.filters.description',
            hostRoute: '/fx',
            allowedModalDepth: 0,
        },
        'fx.page.sync': {
            anchorId: 'fx.page.sync',
            titleKey: 'onboarding.fxPageGuide.steps.sync.title',
            descriptionKey: 'onboarding.fxPageGuide.steps.sync.description',
            hostRoute: '/fx',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'fx.page.add': {
            anchorId: 'fx.page.add',
            titleKey: 'onboarding.fxPageGuide.steps.add.title',
            descriptionKey: 'onboarding.fxPageGuide.steps.add.description',
            hostRoute: '/fx',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'fx.currencies': {
            ...areaPresentation,
            anchorId: 'fx.currencies',
            titleKey: 'onboarding.fxGuide.steps.currencies.title',
            descriptionKey: 'onboarding.fxGuide.steps.currencies.description',
            hostRoute: '/fx',
            allowedModalDepth: 1,
        },
        'fx.providers': {
            ...areaPresentation,
            anchorId: 'fx.providers',
            titleKey: 'onboarding.fxGuide.steps.providers.title',
            descriptionKey: 'onboarding.fxGuide.steps.providers.description',
            hostRoute: '/fx',
            allowedModalDepth: 1,
        },
        'fx.detail.header': {
            ...areaPresentation,
            anchorId: 'fx.detail.header',
            titleKey: 'onboarding.fxDetailGuide.steps.header.title',
            descriptionKey: 'onboarding.fxDetailGuide.steps.header.description',
            hostRoute: '/fx/',
            allowedModalDepth: 0,
        },
        'fx.detail.provider': {
            anchorId: 'fx.detail.provider',
            titleKey: 'onboarding.fxDetailGuide.steps.provider.title',
            descriptionKey: 'onboarding.fxDetailGuide.steps.provider.description',
            hostRoute: '/fx/',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'fx.detail.chart': {
            ...areaPresentation,
            anchorId: 'fx.detail.chart',
            titleKey: 'onboarding.fxDetailGuide.steps.chart.title',
            descriptionKey: 'onboarding.fxDetailGuide.steps.chart.description',
            hostRoute: '/fx/',
            allowedModalDepth: 0,
        },
        'fx.detail.editor': {
            anchorId: 'fx.detail.editor',
            titleKey: 'onboarding.fxDetailGuide.steps.editor.title',
            descriptionKey: 'onboarding.fxDetailGuide.steps.editor.description',
            hostRoute: '/fx/',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'asset.page.overview': {
            ...areaPresentation,
            anchorId: 'asset.page.overview',
            titleKey: 'onboarding.assetPageGuide.steps.overview.title',
            descriptionKey: 'onboarding.assetPageGuide.steps.overview.description',
            hostRoute: '/assets',
            allowedModalDepth: 0,
        },
        'asset.page.filters': {
            ...areaPresentation,
            anchorId: 'asset.page.filters',
            titleKey: 'onboarding.assetPageGuide.steps.filters.title',
            descriptionKey: 'onboarding.assetPageGuide.steps.filters.description',
            hostRoute: '/assets',
            allowedModalDepth: 0,
        },
        'asset.page.sync': {
            anchorId: 'asset.page.sync',
            titleKey: 'onboarding.assetPageGuide.steps.sync.title',
            descriptionKey: 'onboarding.assetPageGuide.steps.sync.description',
            hostRoute: '/assets',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'asset.page.add': {
            anchorId: 'asset.page.add',
            titleKey: 'onboarding.assetPageGuide.steps.add.title',
            descriptionKey: 'onboarding.assetPageGuide.steps.add.description',
            hostRoute: '/assets',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'asset.search': {
            ...areaPresentation,
            anchorId: 'asset.search',
            titleKey: 'onboarding.assetGuide.steps.search.title',
            descriptionKey: 'onboarding.assetGuide.steps.search.description',
            hostRoute: '/assets',
            allowedModalDepth: 1,
        },
        'asset.identity': {
            ...areaPresentation,
            anchorId: 'asset.identity',
            titleKey: 'onboarding.assetGuide.steps.identity.title',
            descriptionKey: 'onboarding.assetGuide.steps.identity.description',
            hostRoute: '/assets',
            allowedModalDepth: 1,
        },
        'asset.provider': {
            ...areaPresentation,
            anchorId: 'asset.provider',
            titleKey: 'onboarding.assetGuide.steps.provider.title',
            descriptionKey: 'onboarding.assetGuide.steps.provider.description',
            hostRoute: '/assets',
            allowedModalDepth: 1,
        },
        'asset.detail.header': {
            ...areaPresentation,
            anchorId: 'asset.detail.header',
            titleKey: 'onboarding.assetDetailGuide.steps.header.title',
            descriptionKey: 'onboarding.assetDetailGuide.steps.header.description',
            hostRoute: '/assets/',
            allowedModalDepth: 0,
        },
        'asset.detail.chart': {
            ...areaPresentation,
            anchorId: 'asset.detail.chart',
            titleKey: 'onboarding.assetDetailGuide.steps.chart.title',
            descriptionKey: 'onboarding.assetDetailGuide.steps.chart.description',
            hostRoute: '/assets/',
            allowedModalDepth: 0,
        },
        'asset.detail.editor': {
            anchorId: 'asset.detail.editor',
            titleKey: 'onboarding.assetDetailGuide.steps.editor.title',
            descriptionKey: 'onboarding.assetDetailGuide.steps.editor.description',
            hostRoute: '/assets/',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'asset.detail.metadata': {
            anchorId: 'asset.detail.metadata',
            titleKey: 'onboarding.assetDetailGuide.steps.metadata.title',
            descriptionKey: 'onboarding.assetDetailGuide.steps.metadata.description',
            hostRoute: '/assets/',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'asset.detail.risk': {
            anchorId: 'asset.detail.risk',
            titleKey: 'onboarding.assetDetailGuide.steps.risk.title',
            descriptionKey: 'onboarding.assetDetailGuide.steps.risk.description',
            hostRoute: '/assets/',
            allowedModalDepth: 0,
            pointer: 'cursor',
        },
        'import.upload': {
            ...importPresentation,
            anchorId: 'import.action.upload',
            titleKey: 'onboarding.importGuide.steps.upload.title',
            descriptionKey: 'onboarding.importGuide.steps.upload.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.select': {
            ...importPresentation,
            anchorId: 'import.action.select',
            titleKey: 'onboarding.importGuide.steps.select.title',
            descriptionKey: 'onboarding.importGuide.steps.select.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.analyze': {
            ...importPresentation,
            anchorId: 'import.action.analyze',
            titleKey: 'onboarding.importGuide.steps.analyze.title',
            descriptionKey: 'onboarding.importGuide.steps.analyze.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.assets': {
            ...importPresentation,
            anchorId: 'import.action.assets',
            titleKey: 'onboarding.importGuide.steps.assets.title',
            descriptionKey: 'onboarding.importGuide.steps.assets.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.fix': {
            ...importPresentation,
            anchorId: 'import.action.fix',
            titleKey: 'onboarding.importGuide.steps.fix.title',
            descriptionKey: 'onboarding.importGuide.steps.fix.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.duplicates': {
            ...importPresentation,
            anchorId: 'import.action.duplicates',
            titleKey: 'onboarding.importGuide.steps.duplicates.title',
            descriptionKey: 'onboarding.importGuide.steps.duplicates.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.review': {
            ...importPresentation,
            anchorId: 'import.action.review',
            titleKey: 'onboarding.importGuide.steps.review.title',
            descriptionKey: 'onboarding.importGuide.steps.review.description',
            hostRoute: '/transactions',
            allowedModalDepth: 2,
        },
        'import.bulk': {
            ...importPresentation,
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
    let lastStep = $derived(active ? isStepManagedFlow(active.flow) || stepIndex === activeSteps.length - 1 : false);
    let checkpoint = $derived(active?.flow === 'transaction_bulk_guide' || (active ? isCheckpointFlow(active.flow) : false));
    let showNext = $derived(active?.flow !== 'import_guide' || active?.stepId === 'import.bulk');
    let progressCurrent = $derived(active?.progress?.current ?? Math.max(stepIndex + 1, 1));
    let progressTotal = $derived(active?.progress?.total ?? activeSteps.length);
    let pointer = $derived(step?.pointer ?? 'none');
    let highlight = $derived(step?.highlight ?? 'none');
    let backdrop = $derived(step?.backdrop ?? false);
    let panelPlacement = $derived(mobile ? (step?.mobilePanelPlacement ?? step?.panelPlacement ?? 'auto') : (step?.panelPlacement ?? 'auto'));
    let scrollPolicy = $derived(step?.scrollPolicy ?? 'nearest-if-hidden');
    let actionHint = $derived(active?.flow === 'intro_tour' ? '' : active?.flow === 'import_guide' ? translate('onboarding.guide.useWizardAction') : pointer === 'cursor' ? translate('onboarding.guide.exploreThenContinue') : '');
    let advanceOnTarget = $derived(active?.flow !== 'intro_tour' && pointer === 'cursor');
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

    function matchesHostRoute(expected: string, actual: string): boolean {
        const pathname = actual.split('?')[0];
        return expected.endsWith('/') ? pathname.startsWith(expected) : pathname === expected;
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
        if (current && presentation?.hostRoute && !matchesHostRoute(presentation.hostRoute, currentPath)) {
            onboardingGuide.dismissHost({restartAtFirst: true});
            queueMicrotask(() => onboardingGuide.maybeStartQueued());
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

    async function handleTargetActivate() {
        if (!active || active.flow === 'intro_tour' || onboardingGuide.actionPending) return;
        if (isStepManagedFlow(active.flow)) {
            await onboardingGuide.finish();
            return;
        }
        if (lastStep) {
            await handleNext();
        } else {
            onboardingGuide.next();
        }
    }
</script>

{#if active?.stepId === 'intro.scene'}
    <OnboardingIntroScene open={true} busy={onboardingGuide.actionPending} error={onboardingGuide.error ? translate(onboardingGuide.error) : null} {closeLabel} onstart={() => onboardingGuide.next()} onclose={handleExit} />
{:else if active && step}
    <OnboardingCoachmark
        open={true}
        {suspended}
        {anchor}
        stepId={active.stepId}
        {pointer}
        {highlight}
        {backdrop}
        {panelPlacement}
        {scrollPolicy}
        {advanceOnTarget}
        title={translate(step.titleKey)}
        description={translate(step.descriptionKey)}
        {actionHint}
        progressLabel={checkpoint ? '' : translateValues('onboarding.tour.progress', {current: progressCurrent, total: progressTotal})}
        backLabel={translate('onboarding.actions.back')}
        nextLabel={checkpoint ? translate('onboarding.actions.gotIt') : lastStep || active.stepId === 'import.bulk' ? translate('onboarding.actions.finish') : translate('onboarding.actions.next')}
        showNextArrow={!checkpoint}
        {closeLabel}
        busyLabel={translate('onboarding.guide.waiting')}
        error={onboardingGuide.error ? translate(onboardingGuide.error) : null}
        showBack={!checkpoint && active.flow !== 'import_guide'}
        backDisabled={stepIndex <= 0}
        {showNext}
        showSkip={false}
        showClose={true}
        busy={onboardingGuide.actionPending}
        onback={() => onboardingGuide.previous()}
        onnext={handleNext}
        onclose={handleExit}
        ontargetactivate={handleTargetActivate}
    />
{/if}
