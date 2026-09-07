<script lang="ts">
    import {onDestroy, tick, untrack} from 'svelte';
    import {get} from 'svelte/store';
    import {Brain, LoaderCircle} from 'lucide-svelte';

    import {clientSessionUserId, getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent} from '$lib/stores/app/clientSession';
    import {currentLanguage} from '$lib/stores/app/language';
    import {getFixedDropdownPosition} from '$lib/utils/layout/dropdownPosition';

    import AiExportOptionsPanel from './AiExportOptionsPanel.svelte';
    import {writePreparedAiExport, type PreparedAiExport} from './aiExportClipboard';
    import {loadAiExportMemory, saveAiExportMemory, type AiExportMemoryKey} from './aiExportMemory';
    import {aiExportOptionsFingerprint, areAiExportOptionsEqual, estimateAiExportTokenSeverity, type AiExportOptionsPanelLabels, type AiExportOptionsSelection} from './aiExportOptions';
    import type {AiExportCatalogCompatibilityResult} from './catalog/compatibility';
    import type {AiExportDomain, AiExportSelectionId} from './catalog/shared';
    import {aiExportResponseLanguageFromLocale} from './ui';

    export interface AiExportMenuLabels {
        readonly triggerLabel: string;
        readonly panelLabel: string;
        readonly options: AiExportOptionsPanelLabels;
    }

    interface Props {
        domain: AiExportDomain;
        compatibility: AiExportCatalogCompatibilityResult;
        memoryKey: AiExportMemoryKey;
        defaultSelectionId: AiExportSelectionId;
        disabled?: boolean;
        labels: AiExportMenuLabels;
        align?: 'start' | 'end';
        showLabel?: boolean;
        onprepare: (options: AiExportOptionsSelection) => Promise<PreparedAiExport>;
        oncopied: (result: PreparedAiExport) => void;
        onerror: (error: unknown) => void;
    }

    interface PreparationContext {
        readonly contextEpoch: number;
        readonly operationId: number;
        readonly sessionGeneration: number;
        readonly sessionUserId: string | null;
        readonly memoryKey: AiExportMemoryKey;
        readonly optionsFingerprint: string;
    }

    let {domain, compatibility, memoryKey, defaultSelectionId, disabled = false, labels, align = 'end', showLabel = true, onprepare, oncopied, onerror}: Props = $props();

    const componentId = $props.id();
    const panelId = `${componentId}-panel`;
    let open = $state(false);
    let loading = $state(false);
    let triggerEl = $state<HTMLButtonElement | null>(null);
    let panelEl = $state<HTMLDivElement | null>(null);
    let position = $state({left: 8, top: 8});
    let activeMemoryKey = $state<AiExportMemoryKey>(untrack(() => memoryKey));
    let activeSessionUserId = $state<string | null>(untrack(getClientSessionUserId));
    let responseLanguage = $derived(aiExportResponseLanguageFromLocale($currentLanguage));
    let memory = $state(
        untrack(() =>
            loadAiExportMemory({
                memoryKey: activeMemoryKey,
                domain,
                compatibility,
                responseLanguage: aiExportResponseLanguageFromLocale(get(currentLanguage)),
                defaultSelectionId,
            }),
        ),
    );
    let draft = $state<AiExportOptionsSelection>(memory.options);
    let draftUserNotes = $state(memory.userNotesDraft);
    let copyAnywayFingerprint = $state<string | undefined>(memory.copyAnywayFingerprint);
    let pending = $state<PreparedAiExport | undefined>(undefined);
    let pendingContext = $state<PreparationContext | undefined>(undefined);
    let catalogSignature = $state('');
    let draftRevision = $state(0);
    let contextEpoch = 0;
    let nextOperationId = 0;
    let activeOperationId: number | undefined;

    function portalToBody(node: HTMLElement) {
        document.body.appendChild(node);
        return {
            destroy() {
                if (node.parentNode === document.body) node.remove();
            },
        };
    }

    function loadDraft(key: AiExportMemoryKey) {
        contextEpoch += 1;
        activeOperationId = undefined;
        loading = false;
        const loaded = loadAiExportMemory({memoryKey: key, domain, compatibility, responseLanguage, defaultSelectionId});
        draft = loaded.options;
        draftUserNotes = loaded.userNotesDraft;
        copyAnywayFingerprint = loaded.copyAnywayFingerprint;
        pending = undefined;
        pendingContext = undefined;
        draftRevision += 1;
    }

    function saveDraft(options: AiExportOptionsSelection, overrideFingerprint = copyAnywayFingerprint, notesDraft = draftUserNotes) {
        const normalized = {...options, responseLanguage};
        if (!areAiExportOptionsEqual(draft, normalized)) draft = normalized;
        draftUserNotes = notesDraft;
        copyAnywayFingerprint = overrideFingerprint;
        if (getClientSessionUserId() !== activeSessionUserId) return;
        saveAiExportMemory({memoryKey: activeMemoryKey, options: normalized, userNotesDraft: notesDraft, copyAnywayFingerprint});
    }

    function handleDraftChange(options: AiExportOptionsSelection, notesDraft: string) {
        saveDraft(options, copyAnywayFingerprint, notesDraft);
        if (pendingContext && pendingContext.optionsFingerprint !== aiExportOptionsFingerprint(options)) {
            contextEpoch += 1;
            activeOperationId = undefined;
            loading = false;
            pending = undefined;
            pendingContext = undefined;
        }
    }

    async function reposition() {
        await tick();
        if (open) position = getFixedDropdownPosition(triggerEl, panelEl, align);
    }

    async function openMenu() {
        if (disabled || loading) return;
        loadDraft(activeMemoryKey);
        open = true;
        await reposition();
        panelEl?.querySelector<HTMLElement>('[data-testid="ai-export-selection-button"]')?.focus();
    }

    function closeMenu() {
        contextEpoch += 1;
        activeOperationId = undefined;
        loading = false;
        open = false;
        pending = undefined;
        pendingContext = undefined;
        triggerEl?.focus();
    }

    function capturePreparationContext(options: AiExportOptionsSelection): PreparationContext {
        const operationId = ++nextOperationId;
        activeOperationId = operationId;
        return {
            contextEpoch,
            operationId,
            sessionGeneration: getClientSessionGeneration(),
            sessionUserId: activeSessionUserId,
            memoryKey: activeMemoryKey,
            optionsFingerprint: aiExportOptionsFingerprint(options),
        };
    }

    function isPreparationContextCurrent(context: PreparationContext): boolean {
        return (
            context.contextEpoch === contextEpoch &&
            context.operationId === activeOperationId &&
            isClientSessionCurrent(context.sessionGeneration) &&
            activeSessionUserId === context.sessionUserId &&
            activeMemoryKey === context.memoryKey &&
            aiExportOptionsFingerprint(draft) === context.optionsFingerprint
        );
    }

    async function copyPrepared(result: PreparedAiExport, rememberOverride: boolean, context: PreparationContext) {
        if (!isPreparationContextCurrent(context)) return;
        await writePreparedAiExport(result);
        if (!isPreparationContextCurrent(context)) return;
        saveDraft(result.options, rememberOverride ? result.optionsFingerprint : copyAnywayFingerprint);
        oncopied(result);
        closeMenu();
    }

    async function prepare(options: AiExportOptionsSelection) {
        if (loading) return;
        loading = true;
        pending = undefined;
        pendingContext = undefined;
        saveDraft(options);
        const context = capturePreparationContext({...options, responseLanguage});
        pendingContext = context;
        try {
            const result = await onprepare({...options, responseLanguage});
            if (!isPreparationContextCurrent(context)) return;
            pending = result;
            const severity = estimateAiExportTokenSeverity(result.stats.finalPrompt.estimatedTokens);
            if (severity === 'normal' || copyAnywayFingerprint === result.optionsFingerprint) await copyPrepared(result, false, context);
        } catch (error) {
            if (isPreparationContextCurrent(context)) onerror(error);
            if (context.operationId === activeOperationId) pendingContext = undefined;
        } finally {
            if (context.operationId === activeOperationId) {
                loading = false;
                if (pendingContext?.operationId !== context.operationId) activeOperationId = undefined;
            }
        }
    }

    async function copyAnyway() {
        if (!pending || !pendingContext || loading) return;
        const context = pendingContext;
        if (!isPreparationContextCurrent(context)) return;
        loading = true;
        try {
            await copyPrepared(pending, true, context);
        } catch (error) {
            if (isPreparationContextCurrent(context)) onerror(error);
        } finally {
            if (context.operationId === activeOperationId) loading = false;
        }
    }

    $effect(() => {
        const key = memoryKey;
        if (key !== activeMemoryKey) {
            activeMemoryKey = key;
            if (open) closeMenu();
            loadDraft(key);
        }
    });

    onDestroy(() => {
        contextEpoch += 1;
        activeOperationId = undefined;
    });

    $effect(() => {
        const userId = $clientSessionUserId;
        if (userId !== activeSessionUserId) {
            activeSessionUserId = userId;
            loadDraft(activeMemoryKey);
        }
    });

    $effect(() => {
        const signature = compatibility.selections.map((selection) => `${selection.kind}:${selection.id}:${selection.version}`).join('|');
        if (signature !== catalogSignature) {
            catalogSignature = signature;
            loadDraft(activeMemoryKey);
        }
    });

    $effect(() => {
        if (!open) return;
        const pointer = (event: PointerEvent) => {
            const path = event.composedPath();
            const portal = event.target instanceof Element ? event.target.closest('[data-simpleselect-dropdown]') : null;
            if (!(triggerEl && path.includes(triggerEl)) && !(panelEl && path.includes(panelEl)) && !portal) closeMenu();
        };
        const keyboard = (event: KeyboardEvent) => {
            if (event.key === 'Escape') closeMenu();
        };
        document.addEventListener('pointerdown', pointer, true);
        document.addEventListener('keydown', keyboard, true);
        return () => {
            document.removeEventListener('pointerdown', pointer, true);
            document.removeEventListener('keydown', keyboard, true);
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
    disabled={disabled || loading}
    aria-busy={loading}
    aria-expanded={open}
    aria-controls={panelId}
    aria-haspopup="dialog"
    aria-label={labels.triggerLabel}
    class="flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-700 dark:text-gray-300 dark:hover:bg-slate-600"
    onclick={() => (open ? closeMenu() : void openMenu())}
    data-testid="ai-export-button"
>
    {#if loading}<LoaderCircle size={14} class="animate-spin" />{:else}<Brain size={14} />{/if}
    {#if showLabel}<span>{labels.triggerLabel}</span>{/if}
</button>

{#if open}
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
        data-testid="ai-export-menu-panel"
    >
        {#key draftRevision}
            <AiExportOptionsPanel
                {domain}
                {compatibility}
                initialOptions={draft}
                initialUserNotes={draftUserNotes}
                {responseLanguage}
                {pending}
                {disabled}
                {loading}
                labels={labels.options}
                locale={$currentLanguage}
                onprepare={(options) => void prepare(options)}
                oncopyanyway={() => void copyAnyway()}
                onusecompact={(options) => void prepare(options)}
                ondraftchange={handleDraftChange}
            />
        {/key}
    </div>
{/if}
