<script lang="ts">
    import {tick, untrack} from 'svelte';
    import {get} from 'svelte/store';
    import {Brain, LoaderCircle} from 'lucide-svelte';

    import {currentLanguage} from '$lib/stores/app/language';
    import {getFixedDropdownPosition} from '$lib/utils/layout/dropdownPosition';

    import AiExportOptionsPanel from './AiExportOptionsPanel.svelte';
    import {loadAiExportMemory, saveAiExportMemory, type AiExportMemoryKey} from './aiExportMemory';
    import type {AiExportCatalogCompatibilityResult} from './catalog/compatibility';
    import type {AiExportDetailLevel, AiExportRenderMode, AiExportTask, AiExportTaskDefinition} from './catalog/shared';
    import {getAiExportMenuTriggerBehavior, normalizeAiExportUserNotes, type AiExportHiddenAnalysisTasks, type AiExportOptionsPanelCallbackMetadata, type AiExportOptionsPanelLabels, type AiExportOptionsSelection} from './aiExportOptions';
    import type {AiExportPromptStats} from './templates/promptRenderer';
    import {aiExportResponseLanguageFromLocale} from './ui';

    export interface AiExportMenuV2Labels {
        readonly triggerLabel: string;
        readonly loadingLabel: string;
        readonly panelLabel: string;
        readonly options: AiExportOptionsPanelLabels;
    }

    interface Props {
        domainTaskDefinitions: readonly AiExportTaskDefinition[];
        compatibility: AiExportCatalogCompatibilityResult;
        memoryKey: AiExportMemoryKey;
        defaultTask: AiExportTask;
        defaultDetailLevel: AiExportDetailLevel;
        defaultRenderMode: AiExportRenderMode;
        defaultUserNotes?: string;
        hiddenAnalysisTasks?: AiExportHiddenAnalysisTasks;
        lastStats?: AiExportPromptStats;
        lastStatsFingerprint?: string;
        disabled?: boolean;
        loading?: boolean;
        labels: AiExportMenuV2Labels;
        align?: 'start' | 'end';
        showLabel?: boolean;
        onexport: (options: AiExportOptionsSelection) => void | Promise<void>;
    }

    interface AiExportPanelSession {
        readonly id: number;
        readonly memoryKey: AiExportMemoryKey;
        readonly onexport: (options: AiExportOptionsSelection, metadata: AiExportOptionsPanelCallbackMetadata) => void;
        readonly ondraftchange: (options: AiExportOptionsSelection, metadata: AiExportOptionsPanelCallbackMetadata) => void;
    }

    let {domainTaskDefinitions, compatibility, memoryKey, defaultTask, defaultDetailLevel, defaultRenderMode, defaultUserNotes = '', hiddenAnalysisTasks = [], lastStats, lastStatsFingerprint, disabled = false, loading = false, labels, align = 'end', showLabel = true, onexport}: Props = $props();

    const componentId = $props.id();
    const panelId = `${componentId}-panel`;
    const PANEL_FOCUSABLE_SELECTOR = ['a[href]', 'button:not([disabled])', 'input:not([disabled]):not([type="hidden"])', 'select:not([disabled])', 'textarea:not([disabled])', '[tabindex]:not([tabindex="-1"])'].join(',');

    let open = $state(false);
    let activeMemoryKey = $state<AiExportMemoryKey>(untrack(() => memoryKey));
    let panelSession = $state<AiExportPanelSession | null>(null);
    let panelSessionSequence = 0;
    let triggerEl = $state<HTMLButtonElement | null>(null);
    let panelEl = $state<HTMLDivElement | null>(null);
    let position = $state({left: 8, top: 8});
    let responseLanguage = $derived(aiExportResponseLanguageFromLocale($currentLanguage));
    let triggerBehavior = $derived(getAiExportMenuTriggerBehavior(disabled, loading));
    let draft = $state<AiExportOptionsSelection>(
        untrack(() =>
            loadAiExportMemory({
                memoryKey: activeMemoryKey,
                defaults: {
                    task: defaultTask,
                    detailLevel: defaultDetailLevel,
                    renderMode: defaultRenderMode,
                    userNotes: defaultUserNotes,
                },
                responseLanguage: aiExportResponseLanguageFromLocale(get(currentLanguage)),
                taskDefinitions: domainTaskDefinitions,
                hiddenAnalysisTasks,
            }),
        ),
    );

    function portalToBody(node: HTMLElement) {
        document.body.appendChild(node);
        return {
            destroy() {
                if (node.parentNode === document.body) node.remove();
            },
        };
    }

    function eventTargetsElement(event: Event, element: HTMLElement | null): boolean {
        return element !== null && event.composedPath().includes(element);
    }

    function eventTargetsOwnedSelectPortal(event: Event): boolean {
        if (!panelEl || !(event.target instanceof Element)) return false;
        const dropdown = event.target.closest('[data-simpleselect-dropdown]');
        if (!dropdown?.id) return false;
        return Array.from(panelEl.querySelectorAll<HTMLElement>('[aria-controls]')).some((control) => control.getAttribute('aria-controls') === dropdown.id);
    }

    function eventTargetsOwnedExpandedCombobox(event: KeyboardEvent): boolean {
        if (!panelEl) return false;
        const eventPath = event.composedPath();
        return Array.from(panelEl.querySelectorAll<HTMLElement>('[role="combobox"][aria-expanded="true"]')).some((control) => eventPath.includes(control));
    }

    function focusFirstPanelControl() {
        const target = panelEl?.querySelector<HTMLElement>('[data-testid="ai-export-v2-task-select-button"]') ?? panelEl?.querySelector<HTMLElement>(PANEL_FOCUSABLE_SELECTOR);
        (target ?? panelEl)?.focus();
    }

    function loadDraft(key: AiExportMemoryKey): AiExportOptionsSelection {
        return loadAiExportMemory({
            memoryKey: key,
            defaults: {
                task: defaultTask,
                detailLevel: defaultDetailLevel,
                renderMode: defaultRenderMode,
                userNotes: defaultUserNotes,
            },
            responseLanguage,
            taskDefinitions: domainTaskDefinitions,
            hiddenAnalysisTasks,
        });
    }

    function normalizeExportOptions(options: AiExportOptionsSelection): AiExportOptionsSelection {
        return {
            ...options,
            responseLanguage,
            userNotes: normalizeAiExportUserNotes(options.renderMode, options.userNotes),
            webResearch: false,
        };
    }

    function persistDraft(key: AiExportMemoryKey, sessionId: number, options: AiExportOptionsSelection, metadata: AiExportOptionsPanelCallbackMetadata): AiExportOptionsSelection {
        const normalized = normalizeExportOptions(options);
        const storedDraft = {
            ...normalized,
            userNotes: metadata.userNotesDraft,
        };
        if (key === activeMemoryKey && key === memoryKey && panelSession?.id === sessionId) {
            draft = storedDraft;
        }
        saveAiExportMemory({
            memoryKey: key,
            options: normalized,
            userNotesDraft: metadata.userNotesDraft,
            taskDefinitions: domainTaskDefinitions,
            hiddenAnalysisTasks,
        });
        return normalized;
    }

    function createPanelSession(key: AiExportMemoryKey): AiExportPanelSession {
        const id = ++panelSessionSequence;
        return {
            id,
            memoryKey: key,
            ondraftchange: (options, metadata) => {
                persistDraft(key, id, options, metadata);
            },
            onexport: (options, metadata) => {
                const committedOptions = persistDraft(key, id, options, metadata);
                if (panelSession?.id !== id || key !== activeMemoryKey || key !== memoryKey) return;
                closeMenu(true);
                void onexport(committedOptions);
            },
        };
    }

    async function reposition() {
        await tick();
        if (!open) return;
        position = getFixedDropdownPosition(triggerEl, panelEl, align);
    }

    async function openMenu() {
        if (!triggerBehavior.canToggle) return;
        draft = loadDraft(activeMemoryKey);
        panelSession = createPanelSession(activeMemoryKey);
        open = true;
        await reposition();
        focusFirstPanelControl();
    }

    function closeMenu(restoreTriggerFocus: boolean) {
        if (!open) return;
        open = false;
        panelSession = null;
        if (restoreTriggerFocus) triggerEl?.focus();
    }

    function toggleMenu() {
        if (!triggerBehavior.canToggle) return;
        if (open) closeMenu(true);
        else void openMenu();
    }

    $effect(() => {
        const nextMemoryKey = memoryKey;
        if (nextMemoryKey === activeMemoryKey) return;

        closeMenu(false);
        activeMemoryKey = nextMemoryKey;
        draft = loadDraft(nextMemoryKey);
    });

    $effect(() => {
        if (!open) return;

        const handlePointerDown = (event: PointerEvent) => {
            if (eventTargetsElement(event, triggerEl) || eventTargetsElement(event, panelEl) || eventTargetsOwnedSelectPortal(event)) return;
            closeMenu(false);
        };
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key !== 'Escape') return;
            if (eventTargetsOwnedExpandedCombobox(event)) return;
            event.preventDefault();
            event.stopPropagation();
            closeMenu(true);
        };

        document.addEventListener('pointerdown', handlePointerDown, true);
        document.addEventListener('keydown', handleKeyDown, true);
        return () => {
            document.removeEventListener('pointerdown', handlePointerDown, true);
            document.removeEventListener('keydown', handleKeyDown, true);
        };
    });

    $effect(() => {
        if (!open) return;

        const handleViewportChange = () => void reposition();
        window.addEventListener('resize', handleViewportChange);
        window.addEventListener('scroll', handleViewportChange, true);

        const observer =
            typeof ResizeObserver !== 'undefined' && panelEl
                ? new ResizeObserver(() => {
                      void reposition();
                  })
                : undefined;
        if (panelEl) observer?.observe(panelEl);

        return () => {
            window.removeEventListener('resize', handleViewportChange);
            window.removeEventListener('scroll', handleViewportChange, true);
            observer?.disconnect();
        };
    });
</script>

<button
    bind:this={triggerEl}
    type="button"
    disabled={triggerBehavior.nativeDisabled}
    aria-busy={triggerBehavior.ariaBusy}
    aria-expanded={open}
    aria-controls={panelId}
    aria-haspopup="dialog"
    aria-label={loading ? labels.loadingLabel : labels.triggerLabel}
    class="flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-700 dark:text-gray-300 dark:hover:bg-slate-600 dark:focus-visible:ring-offset-slate-800 {loading
        ? 'cursor-wait'
        : ''}"
    title={loading ? labels.loadingLabel : labels.triggerLabel}
    onclick={toggleMenu}
    data-testid="ai-export-v2-button"
>
    {#if loading}
        <LoaderCircle size={14} class="animate-spin" aria-hidden="true" />
    {:else}
        <Brain size={14} aria-hidden="true" />
    {/if}
    {#if showLabel}
        <span>{loading ? labels.loadingLabel : labels.triggerLabel}</span>
    {/if}
</button>

{#if open && panelSession}
    <div
        use:portalToBody
        bind:this={panelEl}
        id={panelId}
        role="dialog"
        aria-label={labels.panelLabel}
        tabindex="-1"
        class="fixed z-[9000] max-h-[calc(100vh-1rem)] w-[30rem] max-w-[calc(100vw-1rem)] overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-xl outline-none dark:border-slate-600 dark:bg-slate-800"
        style:left={`${position.left}px`}
        style:top={`${position.top}px`}
        data-testid="ai-export-v2-menu-panel"
        data-ai-export-panel-portal
    >
        <AiExportOptionsPanel
            {domainTaskDefinitions}
            {compatibility}
            initialTask={draft.task}
            initialDetailLevel={draft.detailLevel}
            initialRenderMode={draft.renderMode}
            {hiddenAnalysisTasks}
            {responseLanguage}
            initialUserNotes={draft.userNotes}
            {lastStats}
            {lastStatsFingerprint}
            {disabled}
            {loading}
            labels={labels.options}
            onexport={panelSession.onexport}
            ondraftchange={panelSession.ondraftchange}
        />
    </div>
{/if}
