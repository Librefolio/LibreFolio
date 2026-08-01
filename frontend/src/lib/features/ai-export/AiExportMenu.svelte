<script lang="ts">
    import {tick, untrack} from 'svelte';
    import {get} from 'svelte/store';
    import {Brain, LoaderCircle} from 'lucide-svelte';

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

    let {domain, compatibility, memoryKey, defaultSelectionId, disabled = false, labels, align = 'end', showLabel = true, onprepare, oncopied, onerror}: Props = $props();

    const componentId = $props.id();
    const panelId = `${componentId}-panel`;
    let open = $state(false);
    let loading = $state(false);
    let triggerEl = $state<HTMLButtonElement | null>(null);
    let panelEl = $state<HTMLDivElement | null>(null);
    let position = $state({left: 8, top: 8});
    let activeMemoryKey = $state<AiExportMemoryKey>(untrack(() => memoryKey));
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
    let copyAnywayFingerprint = $state<string | undefined>(memory.copyAnywayFingerprint);
    let pending = $state<PreparedAiExport | undefined>(undefined);
    let catalogSignature = $state('');

    function portalToBody(node: HTMLElement) {
        document.body.appendChild(node);
        return {
            destroy() {
                if (node.parentNode === document.body) node.remove();
            },
        };
    }

    function loadDraft(key: AiExportMemoryKey) {
        const loaded = loadAiExportMemory({memoryKey: key, domain, compatibility, responseLanguage, defaultSelectionId});
        draft = loaded.options;
        copyAnywayFingerprint = loaded.copyAnywayFingerprint;
        pending = undefined;
    }

    function saveDraft(options: AiExportOptionsSelection, overrideFingerprint = copyAnywayFingerprint) {
        const normalized = {...options, responseLanguage};
        if (!areAiExportOptionsEqual(draft, normalized)) draft = normalized;
        copyAnywayFingerprint = overrideFingerprint;
        saveAiExportMemory({memoryKey: activeMemoryKey, options: normalized, copyAnywayFingerprint});
    }

    function handleDraftChange(options: AiExportOptionsSelection) {
        saveDraft(options);
        if (pending && pending.optionsFingerprint !== aiExportOptionsFingerprint(options)) pending = undefined;
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
        open = false;
        pending = undefined;
        triggerEl?.focus();
    }

    async function copyPrepared(result: PreparedAiExport, rememberOverride: boolean) {
        await writePreparedAiExport(result);
        saveDraft(result.options, rememberOverride ? result.optionsFingerprint : copyAnywayFingerprint);
        oncopied(result);
        closeMenu();
    }

    async function prepare(options: AiExportOptionsSelection) {
        if (loading) return;
        loading = true;
        pending = undefined;
        saveDraft(options);
        try {
            const result = await onprepare({...options, responseLanguage});
            pending = result;
            const severity = estimateAiExportTokenSeverity(result.stats.finalPrompt.estimatedTokens);
            if (severity === 'normal' || copyAnywayFingerprint === result.optionsFingerprint) await copyPrepared(result, false);
        } catch (error) {
            onerror(error);
        } finally {
            loading = false;
        }
    }

    async function copyAnyway() {
        if (!pending || loading) return;
        loading = true;
        try {
            await copyPrepared(pending, true);
        } catch (error) {
            onerror(error);
        } finally {
            loading = false;
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
        <AiExportOptionsPanel
            {domain}
            {compatibility}
            initialOptions={draft}
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
    </div>
{/if}
