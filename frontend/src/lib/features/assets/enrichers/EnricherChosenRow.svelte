<!--
  EnricherChosenRow — one enricher of the list in the «Arricchitori dell'asset» window (plan 68, E7b2).

  Closed: the enricher, the identifier type it reads, the name it found (or the identifier), what it fills (topics),
  its last read and outcome, its priority («#1»); drawn off when the instance does not serve it or it is not
  configured («Configura»). Open (the pencil): «Cerca su …» inside that enricher, the identifier type and identifier,
  the plugin's parameters, «Testa Configurazione». An enricher that accepts one identifier type only shows it as a
  fixed badge, not a choice (R4). A binding «Riconosci» found nothing with says so, to correct or search (R3). The row publishes its state (`data-position`, `data-availability`,
  `data-last-read`, `data-issue`) for the tests.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Check, ExternalLink, LoaderCircle, Pencil, RefreshCw, Search, Settings, Trash2, TriangleAlert} from 'lucide-svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import EnricherParamsForm from './EnricherParamsForm.svelte';
    import EnricherTile from './EnricherTile.svelte';
    import {bindingFromResult, withParams, type ChosenRow, type EnricherBinding} from './enrichersEditState';
    import {refusalOutcome, testOutcome, type EnricherSearchResult, type SearchCall, type TestCall, type TestOutcome} from './enricherCalls';

    interface Props {
        row: ChosenRow;
        /** The topics it fills, already in words, and how many more. */
        topics: {labels: string[]; codes: string[]; more: number};
        expanded: boolean;
        search: SearchCall;
        test: TestCall;
        /** The caller may see the enricher's settings: «Configura» on a not configured one. */
        canConfigure?: boolean;
        ontoggle: () => void;
        onremove: () => void;
        onbinding: (binding: EnricherBinding) => void;
        onconfigure: () => void;
    }

    let {row, topics, expanded, search, test, canConfigure = false, ontoggle, onremove, onbinding, onconfigure}: Props = $props();

    let usable = $derived(row.availability === 'ok');
    let name = $derived(row.info?.name ?? row.code);
    /** The one type the enricher reads, when it accepts one only and the binding is on it (or has none yet): no choice (R4). */
    let fixedType = $derived.by(() => {
        const accepted = row.info?.accepted_identifier_types ?? [];
        return accepted.length === 1 && (!row.binding.identifier_type || row.binding.identifier_type === accepted[0]) ? accepted[0] : null;
    });
    let typeOptions = $derived([...new Set([...(row.info?.accepted_identifier_types ?? []), row.binding.identifier_type].filter(Boolean))].map((type) => ({value: type, label: type})));
    let params = $derived(Object.fromEntries(Object.entries(row.binding).filter(([key]) => key !== 'identifier_type' && key !== 'identifier')));

    // «Cerca su …»: the answer of an older query is dropped
    let query = $state('');
    let searching = $state(false);
    /** A refused search: too many, not configured, turned off, or a failure. */
    let searchRefused = $state<TestOutcome['status'] | null>(null);
    let results = $state<EnricherSearchResult[] | null>(null);
    let searchToken = 0;

    async function runSearch(): Promise<void> {
        const text = query.trim();
        if (!text) return;
        const token = ++searchToken;
        searching = true;
        searchRefused = null;
        try {
            const found = await search(row.code, text);
            if (token === searchToken) results = found;
        } catch (error) {
            if (token === searchToken) {
                results = null;
                searchRefused = refusalOutcome(error).status;
            }
        } finally {
            if (token === searchToken) searching = false;
        }
    }

    function pick(result: EnricherSearchResult): void {
        onbinding(bindingFromResult(row.binding, result.binding));
        tested = null;
    }

    // «Testa Configurazione»
    let testing = $state(false);
    let tested = $state<TestOutcome | null>(null);

    async function runTest(): Promise<void> {
        testing = true;
        tested = null;
        try {
            tested = testOutcome(await test(row.code, row.binding));
        } catch (error) {
            tested = refusalOutcome(error);
        } finally {
            testing = false;
        }
    }

    function setBinding(patch: Partial<EnricherBinding>): void {
        onbinding({...row.binding, ...patch});
        tested = null;
    }

    function lastReadText(): string {
        const last = row.lastRead;
        if (!last) return '';
        const day = formatDay(last.day);
        if (last.status === 'ok') return $t('assets.enrichers.lastReadOk', {values: {day}});
        if (last.status === 'not_found') return $t('assets.enrichers.lastReadNotFound', {values: {day}});
        return $t('assets.enrichers.lastReadError', {values: {day}});
    }

    const TEST_KEYS: Record<string, string> = {
        not_found: 'assets.enrichers.testNotFound',
        conflict: 'assets.enrichers.testConflict',
        error: 'assets.enrichers.testError',
        rate_limited: 'assets.enrichers.testRateLimited',
        off: 'assets.enrichers.testOff',
        not_configured: 'assets.enrichers.testNotConfigured',
    };
</script>

<div class="w-full min-w-0 text-lf-primary" data-testid="enricher-row-{row.code}" data-position={row.position} data-availability={row.availability} data-last-read={row.lastRead?.status} data-issue={row.issue ?? undefined} data-expanded={expanded ? 'true' : 'false'}>
    <div class="flex items-start gap-2">
        <EnricherTile code={row.code} {name} icon={row.info?.icon ?? null} muted={!usable} />
        <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 flex-wrap">
                <span class="text-sm font-semibold {usable ? 'text-lf-primary' : 'text-lf-muted'}">{name}</span>
                {#if row.binding.identifier_type}
                    <span class="px-1.5 py-0.5 rounded bg-lf-neutral text-[10px] font-mono text-lf-secondary">{row.binding.identifier_type}</span>
                {/if}
                {#if row.availability === 'off'}
                    <span class="text-[11px] text-lf-muted italic">{$t('assets.enrichers.off')}</span>
                {:else if row.availability === 'not_configured'}
                    <span class="px-1.5 py-0.5 rounded-full bg-lf-warning-soft text-[10px] font-semibold text-lf-warning-on-soft">{$t('assets.enrichers.notConfigured')}</span>
                {/if}
            </div>
            <p class="text-xs text-lf-secondary truncate">{row.foundName ?? row.binding.identifier}</p>
            <p class="text-[11px] text-lf-muted truncate">
                <span data-testid="enricher-topics-{row.code}" data-topics={topics.codes.join(',')} data-more={topics.more}>{topics.labels.join(', ')}{topics.more ? ` ${$t('assets.enrichers.moreTopics', {values: {count: topics.more}})}` : ''}</span>
            </p>
            {#if row.lastRead}
                <p class="text-[11px] {row.lastRead.status === 'ok' ? 'text-lf-muted' : 'text-lf-warning'}" data-testid="enricher-last-read-{row.code}">{lastReadText()}</p>
            {/if}
            {#if row.notFoundWith}
                <p class="mt-0.5 text-[11px] text-lf-warning flex items-center gap-1" data-testid="enricher-not-found-with-{row.code}">
                    <TriangleAlert size={11} aria-hidden="true" />
                    {$t('assets.enrichers.notFoundWith', {values: {type: row.notFoundWith.identifier_type, identifier: row.notFoundWith.identifier}})}
                </p>
            {/if}
            {#if row.conflictWith}
                <p class="mt-0.5 text-[11px] text-lf-warning flex items-center gap-1" data-testid="enricher-conflict-with-{row.code}">
                    <TriangleAlert size={11} aria-hidden="true" />
                    {$t('assets.enrichers.conflictWith', {
                        values: {
                            named: Object.entries(row.conflictWith)
                                .map(([type, value]) => `${type} ${value}`)
                                .join(', '),
                        },
                    })}
                </p>
            {/if}
            {#if row.issue}
                <p class="mt-0.5 text-[11px] text-lf-danger flex items-center gap-1">
                    <TriangleAlert size={11} aria-hidden="true" />
                    {$t(row.issue === 'no_identifier' ? 'assets.enrichers.issueNoIdentifier' : 'assets.enrichers.issueTypeNotAccepted')}
                </p>
            {/if}
        </div>
        <div class="flex items-center gap-1 shrink-0">
            {#if row.availability === 'not_configured' && canConfigure}
                <button type="button" class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md border border-lf-input bg-lf-card text-lf-link hover:bg-lf-hover" onclick={onconfigure} data-testid="enricher-configure-{row.code}">
                    <Settings size={12} aria-hidden="true" />
                    {$t('assets.enrichers.configure')}
                </button>
            {/if}
            {#if row.availability !== 'off'}
                <button type="button" class="p-1 rounded text-lf-muted hover:text-lf-secondary hover:bg-lf-hover" title={$t('assets.enrichers.edit')} aria-label={$t('assets.enrichers.edit')} aria-expanded={expanded} onclick={ontoggle} data-testid="enricher-edit-{row.code}">
                    <Pencil size={14} />
                </button>
            {/if}
            {#if row.pageUrl}
                <a class="p-1 rounded text-lf-muted hover:text-lf-secondary hover:bg-lf-hover" href={row.pageUrl} target="_blank" rel="noopener noreferrer" title={$t('assets.enrichers.openPage')} aria-label={$t('assets.enrichers.openPage')}>
                    <ExternalLink size={14} />
                </a>
            {/if}
            <span class="px-1.5 py-0.5 rounded bg-lf-success-soft text-[10px] font-bold text-lf-success-on-soft">{$t('assets.enrichers.position', {values: {n: row.position}})}</span>
            <button type="button" class="p-1 rounded text-lf-muted hover:text-lf-danger hover:bg-lf-hover" title={$t('assets.enrichers.remove')} aria-label={$t('assets.enrichers.remove')} onclick={onremove} data-testid="enricher-remove-{row.code}">
                <Trash2 size={14} />
            </button>
        </div>
    </div>

    {#if expanded}
        <div class="mt-3 pt-3 border-t border-lf-subtle space-y-3" data-testid="enricher-editor-{row.code}" data-busy={searching || testing ? 'true' : 'false'}>
            {#if row.info?.supports_search && usable}
                <div>
                    <label class="block text-xs text-lf-secondary mb-1" for="enricher-search-{row.code}">{$t('assets.enrichers.searchIn', {values: {name}})}</label>
                    <div class="relative">
                        <Search size={14} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-lf-muted" aria-hidden="true" />
                        <input
                            id="enricher-search-{row.code}"
                            type="text"
                            class="w-full pl-8 pr-2 py-1.5 text-sm rounded-md border border-lf-input bg-lf-field text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:border-lf-focus"
                            placeholder={$t('assets.enrichers.searchPlaceholder')}
                            bind:value={query}
                            onkeydown={(event) => {
                                if (event.key === 'Enter') {
                                    event.preventDefault();
                                    void runSearch();
                                }
                            }}
                            data-testid="enricher-search-{row.code}"
                        />
                    </div>
                    {#if searching}
                        <p class="mt-1 text-xs text-lf-muted flex items-center gap-1"><LoaderCircle size={12} class="animate-spin" aria-hidden="true" />{$t('assets.enrichers.searching')}</p>
                    {:else if searchRefused}
                        <p class="mt-1 text-xs text-lf-danger" data-testid="enricher-search-refused-{row.code}" data-status={searchRefused}>
                            {$t(searchRefused === 'error' ? 'assets.enrichers.searchFailed' : TEST_KEYS[searchRefused])}
                        </p>
                    {:else if results && results.length === 0}
                        <p class="mt-1 text-xs text-lf-muted" data-testid="enricher-results-empty-{row.code}">{$t('assets.enrichers.searchNone')}</p>
                    {:else if results}
                        <ul class="mt-1 rounded-md border border-lf-subtle divide-y divide-lf-subtle overflow-hidden">
                            {#each results as result, index (index)}
                                <li>
                                    <button type="button" class="w-full flex items-center justify-between gap-2 px-2 py-1.5 text-left text-xs bg-lf-panel hover:bg-lf-hover" onclick={() => pick(result)} data-testid="enricher-result-{row.code}-{index}">
                                        <span class="text-lf-primary truncate">{result.name}</span>
                                        <span class="font-mono text-[10px] text-lf-muted shrink-0">{result.binding.identifier}</span>
                                    </button>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </div>
            {/if}

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                    <span class="block text-xs text-lf-secondary mb-1">{$t('assets.enrichers.identifierType')}</span>
                    {#if fixedType}
                        <div class="flex items-center gap-1.5 min-h-[34px]" data-testid="enricher-type-fixed-{row.code}" data-type={fixedType}>
                            <span class="px-1.5 py-0.5 rounded bg-lf-neutral text-xs font-mono font-semibold text-lf-primary">{fixedType}</span>
                            <span class="text-[11px] text-lf-muted">{$t('assets.enrichers.onlyType', {values: {name}})}</span>
                        </div>
                    {:else}
                        <SimpleSelect value={row.binding.identifier_type} options={typeOptions} testId="enricher-type-{row.code}" optionTestId={(option) => `enricher-type-${row.code}-option-${option.value}`} onchange={(value) => setBinding({identifier_type: value})} />
                    {/if}
                </div>
                <label class="block">
                    <span class="block text-xs text-lf-secondary mb-1">{$t('assets.enrichers.identifier')}</span>
                    <!-- Committed at every key (E7c): «Usa questi arricchitori» clicked right after typing finds the window valid,
                         no click lost; trimmed once the field lets the focus go -->
                    <input
                        type="text"
                        class="w-full px-2 py-1.5 text-sm font-mono rounded-md border border-lf-input bg-lf-field text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:border-lf-focus"
                        value={row.binding.identifier}
                        oninput={(event) => setBinding({identifier: event.currentTarget.value})}
                        onchange={(event) => setBinding({identifier: event.currentTarget.value.trim()})}
                        data-testid="enricher-identifier-{row.code}"
                    />
                </label>
            </div>

            {#if row.info?.params_schema?.length}
                <EnricherParamsForm code={row.code} schema={row.info.params_schema} values={params} onchange={(next) => onbinding(withParams(row.binding, next))} />
            {/if}

            <div class="flex flex-wrap items-center gap-2">
                <button
                    type="button"
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md border border-lf-input bg-lf-card text-lf-primary hover:bg-lf-hover disabled:opacity-50"
                    disabled={testing || !row.binding.identifier}
                    onclick={runTest}
                    data-testid="enricher-test-{row.code}"
                >
                    {#if testing}<LoaderCircle size={12} class="animate-spin" aria-hidden="true" />{:else}<RefreshCw size={12} aria-hidden="true" />{/if}
                    {testing ? $t('assets.enrichers.testing') : $t('assets.enrichers.test')}
                </button>
            </div>
            {#if row.info?.supports_search}
                <p class="text-[11px] text-lf-muted">{$t('assets.enrichers.resultHint')}</p>
            {/if}

            {#if tested}
                <div
                    class="flex items-start gap-1.5 px-2.5 py-2 rounded-md border text-xs {tested.status === 'found' ? 'bg-lf-success-soft border-lf-success-line text-lf-success-on-soft' : 'bg-lf-warning-soft border-lf-warning-line text-lf-warning-on-soft'}"
                    data-testid="enricher-test-result-{row.code}"
                    data-status={tested.status}
                >
                    {#if tested.status === 'found'}
                        <Check size={13} class="mt-0.5 shrink-0" aria-hidden="true" />
                        <span>
                            {$t('assets.enrichers.testFound', {values: {name: tested.name ?? row.binding.identifier}})}
                            {#if topics.labels.length}
                                {$t('assets.enrichers.testFills', {values: {topics: topics.labels.join(', ')}})}
                            {/if}
                        </span>
                    {:else}
                        <TriangleAlert size={13} class="mt-0.5 shrink-0" aria-hidden="true" />
                        <span>{$t(TEST_KEYS[tested.status])}</span>
                    {/if}
                </div>
            {/if}
        </div>
    {/if}
</div>
