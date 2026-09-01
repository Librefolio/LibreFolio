<!--
  ChangelogModal — F12 (round 4): opens from the version label in the sidebar.

  - One foldable panel per release; only the most recent starts open.
  - `###` sections and `####` sub-sections are foldable (click the header).
  - Chip index of all versions: clicking a chip unfolds AND scrolls to it.
  - Search descends into the folds: matching branches auto-open while typing.
  - Expand-all / collapse-all buttons.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {marked} from 'marked';
    import {tick} from 'svelte';
    import {ChevronDown, ChevronsDownUp, ChevronsUpDown, ExternalLink, RefreshCw, Search} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {CHANGELOG_REMOTE_URL, changelogChapters, type ChangelogChapter, type ChangelogSection} from '$lib/features/changelog/changelog';
    import {auth} from '$lib/stores/app/auth';
    import {zodiosApi} from '$lib/api';
    import {checkForNewerRelease, type NewerRelease} from '$lib/features/update-check/updateCheck';
    import {updateAvailable} from '$lib/features/update-check/updateCheckStore.svelte';

    interface Props {
        open: boolean;
        onClose: () => void;
        /** Running app version (for the update check). */
        currentVersion?: string;
    }

    let {open, onClose, currentVersion = ''}: Props = $props();

    /** Fold state per chapter / section ("ci:si") / subsection ("ci:si:ssi").
     *  Newest chapter starts open; everything else folded. */
    let openChapters = $state<Record<number, boolean>>({0: true});
    let openSections = $state<Record<string, boolean>>({});
    let query = $state('');

    // Reset to defaults every time the modal opens.
    $effect(() => {
        if (open) {
            openChapters = {0: true};
            openSections = {};
            query = '';
        }
    });

    /** Normalized needle — search is case-insensitive and ignores padding. */
    let needle = $derived(query.trim().toLowerCase());

    function chapterMatches(chapter: ChangelogChapter, q: string): boolean {
        const hay = `${chapter.version}\n${chapter.date}\n${chapter.body}`.toLowerCase();
        return hay.includes(q);
    }

    function sectionMatches(section: ChangelogSection, q: string): boolean {
        const hay = `${section.title ?? ''}\n${section.body}\n${section.subsections.map((s) => `${s.title}\n${s.body}`).join('\n')}`.toLowerCase();
        return hay.includes(q);
    }

    /** Effective fold state: while searching, matching branches force-open. */
    function isChapterOpen(i: number, chapter: ChangelogChapter): boolean {
        if (needle && chapterMatches(chapter, needle)) return true;
        return !!openChapters[i];
    }

    function isSectionOpen(ci: number, si: number, section: ChangelogSection): boolean {
        if (needle && sectionMatches(section, needle)) return true;
        return !!openSections[`${ci}:${si}`];
    }

    function isSubsectionOpen(ci: number, si: number, ssi: number, title: string, body: string): boolean {
        if (needle && `${title}\n${body}`.toLowerCase().includes(needle)) return true;
        return !!openSections[`${ci}:${si}:${ssi}`];
    }

    function setAll(openIt: boolean) {
        const chapters: Record<number, boolean> = {};
        const sections: Record<string, boolean> = {};
        changelogChapters.forEach((c, ci) => {
            chapters[ci] = openIt;
            c.sections.forEach((s, si) => {
                sections[`${ci}:${si}`] = openIt;
                s.subsections.forEach((_sub, ssi) => {
                    sections[`${ci}:${si}:${ssi}`] = openIt;
                });
            });
        });
        openChapters = chapters;
        openSections = sections;
    }

    async function jumpTo(i: number) {
        openChapters = {...openChapters, [i]: true};
        await tick();
        document.querySelector(`[data-testid="changelog-chapter-${i}"]`)?.scrollIntoView({block: 'start'});
    }

    function renderMarkdown(body: string): string {
        return marked.parse(body, {async: false}) as string;
    }

    /** Escape the needle for use in a RegExp. */
    function escapeRegExp(s: string): string {
        return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Render markdown AND highlight needle occurrences in the visible text.
     * The marked output is trusted (bundled changelog); the highlight runs on
     * the HTML string with a needle-escaped regex, wrapping matches in <mark>.
     * Tags/attributes are skipped via a simple tag-boundary split.
     */
    function renderHighlighted(body: string): string {
        let html = renderMarkdown(body);
        if (!needle) return html;
        const re = new RegExp(`(${escapeRegExp(needle)})`, 'gi');
        return html
            .split(/(<[^>]+>)/) // tags pass through untouched
            .map((chunk) => (chunk.startsWith('<') ? chunk : chunk.replace(re, '<mark class="changelog-hit-mark">$1</mark>')))
            .join('');
    }

    /** Highlight helper: matched titles get a marker class while searching. */
    function hitClass(text: string): string {
        return needle && text.toLowerCase().includes(needle) ? 'bg-amber-100 dark:bg-amber-900/40 rounded px-0.5' : '';
    }

    // =========================================================================
    // Search results (round 5): clickable option list under the input — click
    // opens the branch and scrolls to it. Capped, most-specific first.
    // =========================================================================
    interface SearchHit {
        key: string;
        label: string;
        /** Testid of the toggle button to scroll to. */
        target: string;
        ci: number;
        si?: number;
        ssi?: number;
    }

    let searchHits = $derived.by((): SearchHit[] => {
        if (!needle) return [];
        const hits: SearchHit[] = [];
        changelogChapters.forEach((chapter, ci) => {
            chapter.sections.forEach((section, si) => {
                // Title match OR body-only match (round 5 follow-up): a bullet deep
                // inside a section is still a clickable "go there" hit.
                const titleHit = section.title?.toLowerCase().includes(needle) ?? false;
                const bodyHit = section.body.toLowerCase().includes(needle);
                if (section.title && (titleHit || bodyHit)) {
                    hits.push({key: `s-${ci}-${si}`, label: `${section.title} — v${chapter.version}`, target: `changelog-section-toggle-${ci}-${si}`, ci, si});
                }
                section.subsections.forEach((sub, ssi) => {
                    if (sub.title.toLowerCase().includes(needle) || sub.body.toLowerCase().includes(needle)) {
                        hits.push({key: `sub-${ci}-${si}-${ssi}`, label: `${sub.title} — v${chapter.version}`, target: `changelog-subsection-toggle-${ci}-${si}-${ssi}`, ci, si, ssi});
                    }
                });
            });
        });
        return hits.slice(0, 8);
    });

    async function jumpToHit(hit: SearchHit) {
        openChapters = {...openChapters, [hit.ci]: true};
        const next = {...openSections};
        if (hit.si !== undefined) next[`${hit.ci}:${hit.si}`] = true;
        if (hit.ssi !== undefined) next[`${hit.ci}:${hit.si}:${hit.ssi}`] = true;
        openSections = next;
        await tick();
        document.querySelector(`[data-testid="${hit.target}"]`)?.scrollIntoView({block: 'center'});
    }

    // =========================================================================
    // Update check (round 5): manual probe from the modal header — same
    // checkForNewerRelease the login flow uses (never duplicated). Admins get
    // the update modal; non-admins get a hint with the admin list as badges.
    // =========================================================================
    type CheckState = 'idle' | 'checking' | 'up-to-date' | 'newer' | 'ask-admin';
    let checkState = $state<CheckState>('idle');
    let admins = $state<string[]>([]);
    const isAdmin = $derived($auth.user?.is_superuser === true);

    async function handleCheckNow() {
        if (checkState === 'checking') return;
        checkState = 'checking';
        try {
            const release: NewerRelease | null = currentVersion ? await checkForNewerRelease(currentVersion) : null;
            if (!release) {
                checkState = 'up-to-date';
                return;
            }
            if (isAdmin) {
                // Admin: the real modal takes over from here.
                updateAvailable.show(release);
                checkState = 'newer';
            } else {
                // Non-admin: point at the administrators who can act on it.
                checkState = 'ask-admin';
                const res = await zodiosApi.search_users_endpoint_api_v1_users_search_get({queries: {q: '', admins: true}});
                admins = ((res as {items?: Array<{username: string}>}).items ?? []).map((u) => u.username);
            }
        } catch {
            checkState = 'idle';
        }
    }
</script>

<ModalBase {open} onRequestClose={onClose} maxWidth="4xl" testId="changelog-modal">
    <div class="bg-white dark:bg-slate-800 rounded-xl flex flex-col max-h-[85vh]">
        <!-- Header -->
        <div class="flex items-center justify-between gap-3 p-4 border-b border-gray-200 dark:border-slate-700 shrink-0">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 shrink-0">{$_('changelog.title')}</h2>
            <!-- Search descends into the folds -->
            <div class="relative flex-1 max-w-xs">
                <Search size={14} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                <input
                    type="text"
                    bind:value={query}
                    placeholder={$_('changelog.searchPlaceholder')}
                    class="w-full pl-8 pr-2 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-libre-green"
                    data-testid="changelog-search"
                />
            </div>
            <div class="flex items-center gap-1 shrink-0">
                <!-- Update check (F14): same checkForNewerRelease as the login flow -->
                <button
                    type="button"
                    class="inline-flex items-center gap-1 px-2 py-1.5 text-xs font-medium rounded-lg border border-gray-200 dark:border-slate-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
                    onclick={handleCheckNow}
                    disabled={checkState === 'checking'}
                    title={$_('changelog.checkNow')}
                    data-testid="changelog-check-update"
                >
                    <RefreshCw size={13} class={checkState === 'checking' ? 'animate-spin' : ''} />
                    {$_('changelog.checkNow')}
                </button>
                <button type="button" class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors" title={$_('changelog.expandAll')} onclick={() => setAll(true)} data-testid="changelog-expand-all">
                    <ChevronsUpDown size={15} />
                </button>
                <button type="button" class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors" title={$_('changelog.collapseAll')} onclick={() => setAll(false)} data-testid="changelog-collapse-all">
                    <ChevronsDownUp size={15} />
                </button>
                <a href={CHANGELOG_REMOTE_URL} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 text-xs font-medium text-libre-green dark:text-green-400 hover:underline ml-1" data-testid="changelog-remote-link">
                    <ExternalLink size={13} />
                    {$_('changelog.viewRemote')}
                </a>
            </div>
        </div>

        <!-- Search results (clickable) + update-check outcome -->
        {#if searchHits.length > 0}
            <div class="flex flex-wrap items-center gap-1.5 px-4 py-2 border-b border-gray-100 dark:border-slate-700 shrink-0" data-testid="changelog-search-results">
                <span class="text-[11px] text-gray-400 dark:text-gray-500">{$_('changelog.searchResults')}</span>
                {#each searchHits as hit (hit.key)}
                    <button type="button" class="px-2 py-0.5 text-[11px] font-medium rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors" onclick={() => jumpToHit(hit)} data-testid="changelog-hit-{hit.key}">
                        {hit.label}
                    </button>
                {/each}
            </div>
        {/if}
        {#if checkState === 'up-to-date'}
            <div class="px-4 py-2 border-b border-gray-100 dark:border-slate-700 shrink-0 text-xs text-emerald-600 dark:text-emerald-400" data-testid="changelog-up-to-date">
                ✓ {$_('changelog.upToDate')}
            </div>
        {:else if checkState === 'ask-admin'}
            <div class="flex flex-wrap items-center gap-1.5 px-4 py-2 border-b border-amber-100 dark:border-amber-900/40 bg-amber-50/50 dark:bg-amber-900/10 shrink-0 text-xs text-amber-700 dark:text-amber-300" data-testid="changelog-ask-admin">
                <span>{$_('changelog.askAdmin')}</span>
                {#each admins as name (name)}
                    <span class="px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/40 font-medium" data-testid="changelog-admin-badge">{name}</span>
                {/each}
            </div>
        {/if}

        {#if changelogChapters.length === 0}
            <p class="p-6 text-sm text-gray-500 dark:text-gray-400" data-testid="changelog-empty">{$_('changelog.empty')}</p>
        {:else}
            <!-- Version index -->
            <div class="flex gap-1.5 overflow-x-auto px-4 py-2 border-b border-gray-100 dark:border-slate-700 shrink-0" data-testid="changelog-index">
                {#each changelogChapters as chapter, i (chapter.version + chapter.date)}
                    <button
                        type="button"
                        class="px-2.5 py-1 text-xs font-mono font-medium rounded-full whitespace-nowrap transition-colors {isChapterOpen(i, chapter) ? 'bg-libre-green text-white' : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
                        onclick={() => jumpTo(i)}
                        data-testid="changelog-index-{i}"
                    >
                        v{chapter.version}
                    </button>
                {/each}
            </div>

            <!-- Chapters -->
            <div class="flex-1 overflow-y-auto p-4 space-y-3" data-testid="changelog-chapters">
                {#each changelogChapters as chapter, ci (chapter.version + chapter.date)}
                    <section class="rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden" data-testid="changelog-chapter-{ci}">
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 px-3 py-2 text-left bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                            onclick={() => (openChapters = {...openChapters, [ci]: !openChapters[ci]})}
                            aria-expanded={isChapterOpen(ci, chapter)}
                            data-testid="changelog-chapter-toggle-{ci}"
                        >
                            <ChevronDown size={14} class="shrink-0 text-gray-400 transition-transform {isChapterOpen(ci, chapter) ? 'rotate-180' : ''}" />
                            <span class="text-sm font-semibold text-libre-green dark:text-green-400 {hitClass(chapter.version)}">v{chapter.version}</span>
                            {#if chapter.date}
                                <span class="text-xs text-gray-400 dark:text-gray-500">{chapter.date}</span>
                            {/if}
                        </button>
                        {#if isChapterOpen(ci, chapter)}
                            <div class="px-3 py-2 space-y-1">
                                {#each chapter.sections as section, si}
                                    {#if section.title === null}
                                        <!-- intro block before the first ### — always visible -->
                                        <div class="changelog-body text-sm text-gray-700 dark:text-gray-300 leading-relaxed py-1" data-testid="changelog-intro-{ci}">
                                            {@html renderHighlighted(section.body)}
                                        </div>
                                        {#each section.subsections as sub, ssi}
                                            <!-- #### before any ### — render at section level -->
                                            {@render subBlock(ci, si, ssi, sub.title, sub.body)}
                                        {/each}
                                    {:else}
                                        <div class="rounded-md" data-testid="changelog-section-{ci}-{si}">
                                            <button
                                                type="button"
                                                class="flex w-full items-center gap-1.5 px-1.5 py-1 text-left rounded hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
                                                onclick={() => (openSections = {...openSections, [`${ci}:${si}`]: !openSections[`${ci}:${si}`]})}
                                                aria-expanded={isSectionOpen(ci, si, section)}
                                                data-testid="changelog-section-toggle-{ci}-{si}"
                                            >
                                                <ChevronDown size={12} class="shrink-0 text-gray-400 transition-transform {isSectionOpen(ci, si, section) ? 'rotate-180' : ''}" />
                                                <span class="text-[13px] font-medium text-gray-700 dark:text-gray-200 {hitClass(section.title ?? '')}">{section.title}</span>
                                            </button>
                                            {#if isSectionOpen(ci, si, section)}
                                                <div class="pl-6 pr-1 py-1 space-y-1">
                                                    {#if section.body.trim().length > 0}
                                                        <div class="changelog-body text-sm text-gray-700 dark:text-gray-300 leading-relaxed" data-testid="changelog-section-body-{ci}-{si}">
                                                            {@html renderHighlighted(section.body)}
                                                        </div>
                                                    {/if}
                                                    {#each section.subsections as sub, ssi}
                                                        {@render subBlock(ci, si, ssi, sub.title, sub.body)}
                                                    {/each}
                                                </div>
                                            {/if}
                                        </div>
                                    {/if}
                                {/each}
                            </div>
                        {/if}
                    </section>
                {/each}
            </div>
        {/if}
    </div>
</ModalBase>

<!-- #### subsection block -->
{#snippet subBlock(ci: number, si: number, ssi: number, title: string, body: string)}
    <div class="rounded-md" data-testid="changelog-subsection-{ci}-{si}-{ssi}">
        <button
            type="button"
            class="flex w-full items-center gap-1.5 px-1.5 py-1 text-left rounded hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
            onclick={() => (openSections = {...openSections, [`${ci}:${si}:${ssi}`]: !openSections[`${ci}:${si}:${ssi}`]})}
            aria-expanded={isSubsectionOpen(ci, si, ssi, title, body)}
            data-testid="changelog-subsection-toggle-{ci}-{si}-{ssi}"
        >
            <ChevronDown size={11} class="shrink-0 text-gray-400 transition-transform {isSubsectionOpen(ci, si, ssi, title, body) ? 'rotate-180' : ''}" />
            <span class="text-xs font-medium text-gray-600 dark:text-gray-300 {hitClass(title)}">{title}</span>
        </button>
        {#if isSubsectionOpen(ci, si, ssi, title, body)}
            <div class="changelog-body pl-7 pr-1 py-1 text-sm text-gray-700 dark:text-gray-300 leading-relaxed" data-testid="changelog-subsection-body-{ci}-{si}-{ssi}">
                {@html renderHighlighted(body)}
            </div>
        {/if}
    </div>
{/snippet}

<style>
    /* Minimal markdown typography for the bundled changelog (trusted content —
       the file ships with the app build). */
    .changelog-body :global(h3),
    .changelog-body :global(h4) {
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0.5rem 0 0.2rem;
        color: inherit;
    }

    .changelog-body :global(ul) {
        list-style: disc;
        padding-left: 1.25rem;
        margin: 0.4rem 0;
    }

    .changelog-body :global(li) {
        margin: 0.2rem 0;
    }

    .changelog-body :global(p) {
        margin: 0.4rem 0;
    }

    .changelog-body :global(a) {
        color: #1a4031;
        text-decoration: underline;
    }

    :global(html.dark) .changelog-body :global(a) {
        color: #4ade80;
    }

    .changelog-body :global(code) {
        font-size: 0.8em;
        background: rgba(0, 0, 0, 0.05);
        padding: 0.1em 0.3em;
        border-radius: 0.25rem;
    }

    :global(html.dark) .changelog-body :global(code) {
        background: rgba(255, 255, 255, 0.08);
    }

    .changelog-body :global(blockquote) {
        border-left: 3px solid #d1d5db;
        padding-left: 0.75rem;
        margin: 0.5rem 0;
        color: #6b7280;
    }

    /* Search hits inside the rendered markdown (round 5) */
    .changelog-body :global(.changelog-hit-mark) {
        background: #fef08a;
        color: inherit;
        border-radius: 0.2em;
        padding: 0 0.1em;
    }

    :global(html.dark) .changelog-body :global(.changelog-hit-mark) {
        background: rgba(234, 179, 8, 0.35);
    }
</style>
