<!--
  ChangelogModal — F12 (round 4): opens from the version label in the sidebar.

  - One foldable panel per release; only the most recent starts open.
  - `###` sections and `####` sub-sections are foldable (click the header).
  - Chip index of all versions: clicking a chip unfolds AND scrolls to it.
  - Search descends into the folds: matching branches auto-open while typing.
  - Expand-all / collapse-all buttons.
  - Chapters in the interface language, chapter by chapter: an English chapter
    in a translated interface carries a discreet "not translated yet" pill.
-->
<script lang="ts">
    import {_, locale} from '$lib/i18n';
    import {marked} from 'marked';
    import {onDestroy, tick} from 'svelte';
    import {ChevronDown, ChevronsDownUp, ChevronsUpDown, ExternalLink, RefreshCw, Search} from 'lucide-svelte';
    import AskAdminModal from '$lib/features/update-check/AskAdminModal.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {CHANGELOG_REMOTE_URL, baseLanguage, localizedChangelog, type ChangelogChapter, type ChangelogSection, type DisplayedChapter} from '$lib/features/changelog/changelog';
    import {auth} from '$lib/stores/app/auth';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {zodiosApi} from '$lib/api';
    import {checkForUpdates, type UpdateCheckResult} from '$lib/features/update-check/updateCheck';
    import {selfHostedConfirmed} from '$lib/features/instance/profile';
    import {updateAvailable} from '$lib/features/update-check/updateCheckStore.svelte';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';

    interface Props {
        open: boolean;
        onClose: () => void;
        /** Version displayed by the caller; checks resolve the running backend version. */
        currentVersion?: string;
    }

    let {open, onClose, currentVersion = ''}: Props = $props();

    /** The interface language: a chapter shown in another language carries a discreet pill. */
    const uiLanguage = $derived(baseLanguage($locale));
    /** The last load, kept for the language it was for (a failed load holds the English fallback). */
    let loaded = $state<{language: string; chapters: DisplayedChapter[]} | null>(null);
    /** Chapters in the interface language, chapter by chapter; undefined while its translation loads. */
    const ready: DisplayedChapter[] | undefined = $derived(localizedChangelog.peek(uiLanguage) ?? (loaded?.language === uiLanguage ? loaded.chapters : undefined));
    const chapters = $derived(ready ?? []);
    const loading = $derived(ready === undefined);

    // The first time the modal opens in a language, fetch its translation (a lazy chunk).
    $effect(() => {
        if (!open) return;
        const language = uiLanguage;
        if (localizedChangelog.peek(language)) return;
        let live = true;
        localizedChangelog.load(language).then((result) => {
            if (live) loaded = {language, chapters: result};
        });
        return () => {
            live = false;
        };
    });

    /** Fold state per chapter / section ("ci:si") / subsection ("ci:si:ssi").
     *  Newest chapter starts open; everything else folded. */
    let openChapters = $state<Record<number, boolean>>({0: true});
    let openSections = $state<Record<string, boolean>>({});
    let query = $state('');

    // Reset to defaults every time the modal opens.
    $effect(() => {
        checkGeneration++;
        checkState = 'idle';
        lastCheck = null;
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
        const chapterFolds: Record<number, boolean> = {};
        const sectionFolds: Record<string, boolean> = {};
        chapters.forEach((c, ci) => {
            chapterFolds[ci] = openIt;
            c.sections.forEach((s, si) => {
                sectionFolds[`${ci}:${si}`] = openIt;
                s.subsections.forEach((_sub, ssi) => {
                    sectionFolds[`${ci}:${si}:${ssi}`] = openIt;
                });
            });
        });
        openChapters = chapterFolds;
        openSections = sectionFolds;
    }

    async function jumpTo(i: number) {
        openChapters = {...openChapters, [i]: true};
        await tick();
        document.querySelector(`[data-testid="changelog-chapter-${i}"]`)?.scrollIntoView({block: 'start'});
    }

    /** marked output per body: bodies never change while the app runs, and a search re-renders every open one on each keystroke. */
    const markdownByBody = new Map<string, string>();

    function renderMarkdown(body: string): string {
        let html = markdownByBody.get(body);
        if (html === undefined) {
            html = marked.parse(body, {async: false}) as string;
            markdownByBody.set(body, html);
        }
        return html;
    }

    /** Escape the needle for use in a RegExp. */
    function escapeRegExp(s: string): string {
        return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Render markdown AND highlight needle occurrences in the visible text.
     * The highlight runs on the HTML string with a needle-escaped regex,
     * wrapping matches in <mark>; tags/attributes are skipped via a simple
     * tag-boundary split. Every sink passes the result through sanitizeHtml:
     * the translated chapters come from an LLM pipeline, and one path serves
     * every language.
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

    /**
     * Highlight helper: while searching, a matched title takes the mark roles (Q7), any other title its resting text
     * colour `idle`. Both sit in one ternary: Tailwind orders two text utilities of one element by name, not by their
     * place in the class string (skill `theme-roles`, rule 8).
     */
    function hitClass(text: string, idle: string): string {
        return needle && text.toLowerCase().includes(needle) ? 'bg-lf-mark text-lf-on-mark inset-ring inset-ring-lf-mark-line rounded px-0.5' : idle;
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
        chapters.forEach((chapter, ci) => {
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
    // Manual probe uses the same release selection and image gate as login.
    // Only explicit checks bypass the cache and prompt dismissal. Admins get
    // the update modal; non-admins get a hint with the admin list as badges.
    // =========================================================================
    type CheckState = 'idle' | 'checking' | 'newer' | 'ask-admin';
    let checkState = $state<CheckState>('idle');
    let lastCheck = $state<UpdateCheckResult | null>(null);
    let checkedVersion = $state('');
    let checkGeneration = 0;
    let admins = $state<Array<{username: string; email: string | null}>>([]);
    const isAdmin = $derived($auth.user?.is_superuser === true);

    onDestroy(() => {
        checkGeneration++;
    });

    function checkMessage(result: UpdateCheckResult): string {
        if (result.status === 'up-to-date') return $_('changelog.upToDate');
        if (result.status === 'no-release') return $_('changelog.noStableRelease');
        if (result.status === 'image-pending') return $_('changelog.imagePending');
        if (result.status === 'error') {
            return $_(result.reason?.startsWith('image-') ? 'changelog.imageCheckFailed' : 'changelog.checkFailed');
        }
        return $_('updateCheck.title');
    }

    function reportCheck(result: UpdateCheckResult) {
        const message = result.status === 'up-to-date' && result.latest ? `${checkMessage(result)}\n${$_('changelog.detectedRemoteVersion', {values: {version: result.latest.tag ?? result.latest.version}})}` : checkMessage(result);
        notify({
            name: 'app.update.checked',
            detail: {status: result.status, source: result.source, checkedAt: result.checkedAt, currentVersion: checkedVersion, reportedVersion: currentVersion, remoteVersion: result.latest?.version ?? null, remoteTag: result.latest?.tag ?? null, reason: result.reason},
            toast:
                result.status === 'up-to-date'
                    ? {variant: 'success', message: escapeHtml(message)}
                    : result.status === 'error'
                      ? {variant: 'error', message: escapeHtml(message)}
                      : result.status === 'image-pending' || result.status === 'no-release'
                        ? {variant: 'warning', message: escapeHtml(message)}
                        : undefined,
        });
    }

    async function handleCheckNow() {
        if (checkState === 'checking') return;
        const generation = ++checkGeneration;
        checkState = 'checking';
        lastCheck = null;
        checkedVersion = '';
        try {
            const info = await zodiosApi.get_system_info_api_v1_system_info_get();
            if (generation !== checkGeneration || !open) return;
            checkedVersion = info.app_version;
            const result = await checkForUpdates(checkedVersion, {force: true, ignoreDismissed: true});
            if (generation !== checkGeneration || !open) return;
            lastCheck = result;
            reportCheck(result);
            if (result.status !== 'update-available' || !result.latest) {
                checkState = 'idle';
                return;
            }
            if (isAdmin) {
                // Admin: the real modal takes over from here, at once and above this one.
                updateAvailable.show(result.latest, {requested: true});
                checkState = 'newer';
            } else {
                // Non-admin: open the ask-admin modal listing the administrators.
                const res = await zodiosApi.search_users_endpoint_api_v1_users_search_get({queries: {q: '', admins: true}});
                if (generation !== checkGeneration || !open) return;
                admins = ((res as {items?: Array<{username: string; email?: string | null}>}).items ?? []).map((u) => ({username: u.username, email: u.email ?? null}));
                checkState = 'ask-admin';
            }
        } catch {
            if (generation !== checkGeneration || !open) return;
            checkState = 'idle';
            if (lastCheck?.status === 'update-available') {
                notify({name: 'app.update.admin-lookup-failed', toast: {variant: 'error', message: $_('changelog.adminLookupFailed')}});
                return;
            }
            lastCheck = {status: 'error', latest: null, source: 'none', checkedAt: null, reason: 'check-failed'};
            reportCheck(lastCheck);
        }
    }
</script>

<ModalBase {open} onRequestClose={onClose} maxWidth="4xl" testId="changelog-modal">
    <div class="bg-lf-card text-lf-primary rounded-xl flex flex-col max-h-[85vh]">
        <!-- Header rows:
             - Row 1 (always): title + expand/collapse + GitHub link.
             - Row 2: search (left) + update-check (right). On ≥sm everything merges
               into one line; on mobile the two rows stay distinct. -->
        <div class="flex flex-wrap items-center gap-x-3 gap-y-2 p-4 border-b border-lf-subtle shrink-0">
            <!-- Row 1 -->
            <h2 class="text-lg font-semibold text-lf-primary shrink-0 order-1">{$_('changelog.title')}</h2>
            <div class="flex items-center gap-1 shrink-0 order-2 sm:order-2 ml-auto">
                <button type="button" class="p-1.5 rounded-lg text-lf-muted hover:text-lf-secondary hover:bg-lf-hover transition-colors" title={$_('changelog.expandAll')} onclick={() => setAll(true)} data-testid="changelog-expand-all">
                    <ChevronsUpDown size={15} />
                </button>
                <button type="button" class="p-1.5 rounded-lg text-lf-muted hover:text-lf-secondary hover:bg-lf-hover transition-colors" title={$_('changelog.collapseAll')} onclick={() => setAll(false)} data-testid="changelog-collapse-all">
                    <ChevronsDownUp size={15} />
                </button>
                <a href={CHANGELOG_REMOTE_URL} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 text-xs font-medium text-lf-link hover:underline ml-1" data-testid="changelog-remote-link">
                    <ExternalLink size={13} />
                    <span class="hidden sm:inline">{$_('changelog.viewRemote')}</span>
                </a>
            </div>
            <!-- Row 2: search (left) + update check (right). Full-width row on mobile. -->
            <div class="relative flex-1 min-w-32 max-w-xs order-3 sm:order-3">
                <Search size={14} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-lf-muted pointer-events-none" />
                <input
                    type="text"
                    bind:value={query}
                    placeholder={$_('changelog.searchPlaceholder')}
                    class="w-full pl-8 pr-2 py-1.5 text-xs rounded-lg border border-lf-input hover:border-lf-input-hover bg-lf-field text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:border-lf-focus focus:ring-1 focus:ring-lf-focus"
                    data-testid="changelog-search"
                />
            </div>
            <div class="flex items-center gap-1 shrink-0 order-4 sm:order-4 ml-auto sm:ml-0">
                <!-- Update check (F14): force a fresh result, retaining the login flow's gates. Only once the server said
                     self-hosted: a managed instance is updated by its operator (F05, workstream A), and nothing shows
                     before the answer or after a failed request. -->
                {#if selfHostedConfirmed()}
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 px-2 py-1.5 text-xs font-medium rounded-lg border border-lf-subtle text-lf-secondary hover:bg-lf-hover transition-colors disabled:opacity-50"
                        onclick={handleCheckNow}
                        disabled={checkState === 'checking'}
                        title={$_('changelog.checkNow')}
                        data-testid="changelog-check-update"
                    >
                        <RefreshCw size={13} class={checkState === 'checking' ? 'animate-spin' : ''} />
                        <span class="hidden sm:inline">{$_('changelog.checkNow')}</span>
                    </button>
                {/if}
            </div>
        </div>

        <!-- Search results (clickable) + update-check outcome -->
        {#if searchHits.length > 0}
            <div class="flex flex-wrap items-center gap-1.5 px-4 py-2 border-b border-lf-subtle shrink-0" data-testid="changelog-search-results">
                <span class="text-[11px] text-lf-muted">{$_('changelog.searchResults')}</span>
                {#each searchHits as hit (hit.key)}
                    <button type="button" class="px-2 py-0.5 text-[11px] font-medium rounded-full bg-lf-info-soft text-lf-info-on-soft hover:bg-lf-info-line transition-colors" onclick={() => jumpToHit(hit)} data-testid="changelog-hit-{hit.key}">
                        {hit.label}
                    </button>
                {/each}
            </div>
        {/if}
        {#if checkState === 'ask-admin'}
            <!-- Non-admin + newer release: the AskAdminModal lists the admins. -->
            <AskAdminModal open={true} {admins} onClose={() => (checkState = 'idle')} />
        {/if}

        {#if loading}
            <p class="p-6 text-sm text-lf-muted" data-testid="changelog-loading" aria-busy="true">{$_('common.loading')}</p>
        {:else if chapters.length === 0}
            <p class="p-6 text-sm text-lf-muted" data-testid="changelog-empty">{$_('changelog.empty')}</p>
        {:else}
            <!-- Version index -->
            <div class="flex gap-1.5 overflow-x-auto px-4 py-2 border-b border-lf-subtle shrink-0" data-testid="changelog-index">
                {#each chapters as chapter, i (chapter.version + chapter.date)}
                    <button
                        type="button"
                        class="px-2.5 py-1 text-xs font-mono font-medium rounded-full whitespace-nowrap transition-colors {isChapterOpen(i, chapter) ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-panel text-lf-secondary hover:bg-lf-neutral'}"
                        onclick={() => jumpTo(i)}
                        data-testid="changelog-index-{i}"
                    >
                        v{chapter.version}
                    </button>
                {/each}
            </div>

            <!-- Chapters -->
            <div class="flex-1 overflow-y-auto p-4 space-y-3" data-testid="changelog-chapters">
                {#each chapters as chapter, ci (chapter.version + chapter.date)}
                    <section class="rounded-lg border border-lf-subtle overflow-hidden" data-testid="changelog-chapter-{ci}" data-version={chapter.version} lang={chapter.lang}>
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 px-3 py-2 text-left bg-lf-panel hover:bg-lf-neutral transition-colors"
                            onclick={() => (openChapters = {...openChapters, [ci]: !openChapters[ci]})}
                            aria-expanded={isChapterOpen(ci, chapter)}
                            data-testid="changelog-chapter-toggle-{ci}"
                        >
                            <ChevronDown size={14} class="shrink-0 text-lf-muted transition-transform {isChapterOpen(ci, chapter) ? 'rotate-180' : ''}" />
                            <span class="text-sm font-semibold {hitClass(chapter.version, 'text-lf-link')}">v{chapter.version}</span>
                            {#if chapter.date}
                                <span class="text-xs text-lf-muted">{chapter.date}</span>
                            {/if}
                            {#if chapter.lang !== uiLanguage}
                                <!-- An English chapter in a translated interface: its translation is not out yet. -->
                                <span class="rounded-full border border-lf-subtle px-1.5 text-[10px] font-medium leading-4 text-lf-muted" lang={uiLanguage} data-testid="changelog-not-translated-{ci}">{$_('changelog.notTranslated')}</span>
                            {/if}
                        </button>
                        {#if isChapterOpen(ci, chapter)}
                            <div class="px-3 py-2 space-y-1">
                                {#each chapter.sections as section, si}
                                    {#if section.title === null}
                                        <!-- intro block before the first ### — always visible -->
                                        <div class="changelog-body text-sm text-lf-secondary leading-relaxed py-1" data-testid="changelog-intro-{ci}">
                                            {@html sanitizeHtml(renderHighlighted(section.body))}
                                        </div>
                                        {#each section.subsections as sub, ssi}
                                            <!-- #### before any ### — render at section level -->
                                            {@render subBlock(ci, si, ssi, sub.title, sub.body)}
                                        {/each}
                                    {:else}
                                        <div class="rounded-md" data-testid="changelog-section-{ci}-{si}">
                                            <button
                                                type="button"
                                                class="flex w-full items-center gap-1.5 px-1.5 py-1 text-left rounded hover:bg-lf-hover transition-colors"
                                                onclick={() => (openSections = {...openSections, [`${ci}:${si}`]: !openSections[`${ci}:${si}`]})}
                                                aria-expanded={isSectionOpen(ci, si, section)}
                                                data-testid="changelog-section-toggle-{ci}-{si}"
                                            >
                                                <ChevronDown size={12} class="shrink-0 text-lf-muted transition-transform {isSectionOpen(ci, si, section) ? 'rotate-180' : ''}" />
                                                <span class="text-[13px] font-medium {hitClass(section.title ?? '', 'text-lf-secondary')}">{section.title}</span>
                                            </button>
                                            {#if isSectionOpen(ci, si, section)}
                                                <div class="pl-6 pr-1 py-1 space-y-1">
                                                    {#if section.body.trim().length > 0}
                                                        <div class="changelog-body text-sm text-lf-secondary leading-relaxed" data-testid="changelog-section-body-{ci}-{si}">
                                                            {@html sanitizeHtml(renderHighlighted(section.body))}
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
            class="flex w-full items-center gap-1.5 px-1.5 py-1 text-left rounded hover:bg-lf-hover transition-colors"
            onclick={() => (openSections = {...openSections, [`${ci}:${si}:${ssi}`]: !openSections[`${ci}:${si}:${ssi}`]})}
            aria-expanded={isSubsectionOpen(ci, si, ssi, title, body)}
            data-testid="changelog-subsection-toggle-{ci}-{si}-{ssi}"
        >
            <ChevronDown size={11} class="shrink-0 text-lf-muted transition-transform {isSubsectionOpen(ci, si, ssi, title, body) ? 'rotate-180' : ''}" />
            <span class="text-xs font-medium {hitClass(title, 'text-lf-secondary')}">{title}</span>
        </button>
        {#if isSubsectionOpen(ci, si, ssi, title, body)}
            <div class="changelog-body pl-7 pr-1 py-1 text-sm text-lf-secondary leading-relaxed" data-testid="changelog-subsection-body-{ci}-{si}-{ssi}">
                {@html sanitizeHtml(renderHighlighted(body))}
            </div>
        {/if}
    </div>
{/snippet}

<style>
    /* Minimal markdown typography for the bundled changelog (the files ship
       with the app build; every sink sanitises their HTML). */
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
        color: var(--lf-link);
        text-decoration: underline;
    }

    .changelog-body :global(code) {
        font-size: 0.8em;
        background: var(--lf-surface-panel);
        border: 1px solid var(--lf-border-subtle);
        color: var(--lf-text-primary);
        padding: 0.1em 0.3em;
        border-radius: 0.25rem;
    }

    .changelog-body :global(blockquote) {
        border-left: 3px solid var(--lf-border-subtle);
        padding-left: 0.75rem;
        margin: 0.5rem 0;
        color: var(--lf-text-muted);
    }

    /* Search hits inside the rendered markdown (round 5), on the mark roles (Q7). The edge is an inset shadow, so a
       hit never moves the text around it. */
    .changelog-body :global(.changelog-hit-mark) {
        background: var(--lf-mark-bg);
        color: var(--lf-mark-text);
        box-shadow: inset 0 0 0 1px var(--lf-mark-line);
        border-radius: 0.2em;
        padding: 0 0.1em;
    }
</style>
