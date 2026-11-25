<!--
  EnricherOnlineSearch — «Cerca online» on top of the enrichers' window (ENR-3, decision 1, R9-R13). It has the look of
  the asset search (title, «Suggerimenti», field, pills, rows) but searches the enrichers, one per source:

  - **Suggerimenti**: the asset's name, ISIN and ticker; a touch puts it in the field and searches (P-34: ESMA's ISIN
    with one touch, never typed again).
  - **Pills** (R10): the enrichers that cover the type and are not chosen, switches that start on; one without a search
    says which identifiers it answers («solo ISIN»). A line names the chosen ones, not searched.
  - It searches only when the user types (a pause of ~400 ms, at least 2 characters) or touches a suggestion: one
    question to `GET /assets/enrichers/search`, one probe on the per-user limit.
  - **Rows** (R11): a binding ready to add, with «+»; the «+» hands it to the window (`onadd`), the search stays open
    with its text, the enricher's rows and pill go. A result naming an ISIN different from the asset's or a chosen
    one's says so, and its «+» asks to confirm (R13).
  - An ISIN added asks, once, the enrichers without a search that accept it (R12: ESMA), with the same route; their
    rows say where the ISIN came from.

  Pure decisions in `enrichersEditState.ts`; the stream in `enricherSearchStream.ts` (`search` may be given by a test).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {onDestroy} from 'svelte';
    import {Check, ExternalLink, LoaderCircle, Plus, Search, TriangleAlert} from 'lucide-svelte';
    import EnricherTile from './EnricherTile.svelte';
    import {addFromSearch, isinFollowUp, searchExcluded, searchPills, searchRows, type EnricherInfo, type EnrichersDraft, type SearchAnswer, type SearchHit, type SearchRow} from './enrichersEditState';
    import {searchEnrichersOnline, type EnricherSearchEvent, type EnricherSearchOutcome, type EnricherSearchRequest} from './enricherSearchStream';

    type SearchCallOnline = (request: EnricherSearchRequest, options: {onEvent: (event: EnricherSearchEvent) => void; signal?: AbortSignal}) => Promise<EnricherSearchOutcome>;

    interface Props {
        catalogue: EnricherInfo[];
        assetType: string;
        /** The window's list: what is chosen leaves the pills and the rows. */
        draft: EnrichersDraft;
        /** The asset's identifiers (type → value): the suggestions, and the ISIN results must agree with (R13). */
        assetIdentifiers: Record<string, string>;
        assetName: string;
        onadd: (code: string, hit: SearchHit) => void;
        search?: SearchCallOnline;
    }

    let {catalogue, assetType, draft, assetIdentifiers, assetName, onadd, search = searchEnrichersOnline}: Props = $props();

    const DEBOUNCE_MS = 400;
    const MIN_CHARS = 2;

    let query = $state('');
    let off = $state<Set<string>>(new Set());
    let status = $state<'idle' | 'searching' | 'done' | 'refused' | 'error'>('idle');
    let answers = $state<SearchAnswer[]>([]);
    let asked = $state('');
    /** The questions an added ISIN asked (R12), with the enricher whose result carried it. */
    let followUps = $state<{isin: string; origin: string; answers: SearchAnswer[]}[]>([]);
    const isinsAsked = new Set<string>();
    let confirming = $state<string | null>(null);
    let lastAdded = $state<{code: string; position: number} | null>(null);

    let timer: ReturnType<typeof setTimeout> | null = null;
    let controller: AbortController | null = null;
    const followControllers: AbortController[] = [];
    onDestroy(() => {
        if (timer !== null) clearTimeout(timer);
        controller?.abort();
        followControllers.forEach((each) => each.abort());
    });

    let pills = $derived(searchPills(draft, catalogue, assetType, off));
    let excluded = $derived(searchExcluded(draft, catalogue, assetType));
    let rows = $derived(searchRows(answers, draft, assetIdentifiers));
    let followRows = $derived(followUps.map((follow) => ({...follow, rows: searchRows(follow.answers, draft, assetIdentifiers)})));
    let suggestions = $derived([assetName.trim(), assetIdentifiers.ISIN?.trim(), assetIdentifiers.TICKER?.trim()].filter((value, index, all): value is string => !!value && value.length >= MIN_CHARS && all.indexOf(value) === index));
    /** What an enricher said that is not a result: no results, ISIN only, a refusal, a failure. */
    let notes = $derived(answers.filter((answer) => !draft.order.includes(answer.code) && (answer.status !== 'ok' || answer.results.length === 0)));

    function nameOf(code: string): string {
        return catalogue.find((info) => info.code === code)?.name ?? code;
    }

    function run(text: string): void {
        const q = text.trim();
        controller?.abort();
        confirming = null;
        if (q.length < MIN_CHARS) {
            status = 'idle';
            answers = [];
            asked = '';
            return;
        }
        const codes = pills.filter((pill) => pill.on).map((pill) => pill.code);
        if (!codes.length) {
            status = 'idle';
            answers = [];
            return;
        }
        const mine = new AbortController();
        controller = mine;
        status = 'searching';
        answers = [];
        asked = q;
        search(
            {q, codes, assetType},
            {
                signal: mine.signal,
                onEvent: (event) => {
                    if (controller !== mine || event.event !== 'enricher_results') return;
                    answers = [...answers.filter((answer) => answer.code !== event.code), event as SearchAnswer];
                },
            },
        ).then(
            (outcome) => {
                if (controller !== mine || outcome.kind === 'aborted') return;
                status = outcome.kind === 'refused' ? 'refused' : 'done';
            },
            () => {
                if (controller === mine) status = 'error';
            },
        );
    }

    function schedule(): void {
        if (timer !== null) clearTimeout(timer);
        timer = setTimeout(() => {
            timer = null;
            run(query);
        }, DEBOUNCE_MS);
    }

    function suggest(value: string): void {
        if (timer !== null) clearTimeout(timer);
        query = value;
        run(value);
    }

    function toggle(code: string): void {
        const next = new Set(off);
        if (next.has(code)) next.delete(code);
        else next.add(code);
        off = next;
        if (query.trim().length >= MIN_CHARS) schedule();
    }

    /** Each row with a stable key: its enricher and its place among that enricher's results, so a key does not move
     *  when another enricher's rows go. */
    function keyed(list: SearchRow[], origin = ''): {row: SearchRow; key: string}[] {
        const seen: Record<string, number> = {};
        return list.map((row) => {
            const index = seen[row.code] ?? 0;
            seen[row.code] = index + 1;
            return {row, key: `${origin}${row.code}-${index}`};
        });
    }

    function add(row: SearchRow, key: string): void {
        if (row.conflict && confirming !== key) {
            confirming = key;
            return;
        }
        confirming = null;
        const after = addFromSearch(draft, row.code, row.hit.binding);
        onadd(row.code, row.hit);
        lastAdded = {code: row.code, position: after.order.length};
        const follow = isinFollowUp(row.hit.binding, after, catalogue, assetType, isinsAsked);
        if (follow) ask(follow.isin, follow.codes, row.code);
    }

    /** R12: the ISIN of a result added, asked once to the enrichers without a search. */
    function ask(isin: string, codes: string[], origin: string): void {
        isinsAsked.add(isin);
        const mine = new AbortController();
        followControllers.push(mine);
        followUps = [...followUps, {isin, origin, answers: []}];
        search(
            {q: isin, codes, assetType},
            {
                signal: mine.signal,
                onEvent: (event) => {
                    if (event.event !== 'enricher_results') return;
                    followUps = followUps.map((follow) => (follow.isin === isin ? {...follow, answers: [...follow.answers.filter((answer) => answer.code !== event.code), event as SearchAnswer]} : follow));
                },
            },
        ).catch(() => {
            // A failed follow-up adds no row: the user can still type the ISIN
        });
    }

    function noteText(answer: SearchAnswer): string {
        const name = nameOf(answer.code);
        if (answer.status === 'ok') return $t('assets.enrichers.search.none', {values: {name, q: asked}});
        if (answer.status === 'identifier_only') return $t('assets.enrichers.search.identifierHint', {values: {name, types: answer.accepted_identifier_types.join(', ')}});
        if (answer.status === 'rate_limited') return $t('assets.enrichers.search.refusedOne', {values: {name}});
        return $t('assets.enrichers.search.failedOne', {values: {name}});
    }

    function originText(row: SearchRow, followOrigin: string | null): string {
        if (followOrigin) return $t('assets.enrichers.search.withIsinOf', {values: {name: nameOf(followOrigin)}});
        const answer = answers.find((each) => each.code === row.code);
        return answer?.via === 'recognize' ? $t('assets.enrichers.search.withIsinTyped') : '';
    }
</script>

{#snippet resultRow(row: SearchRow, key: string, followOrigin: string | null)}
    {@const info = catalogue.find((each) => each.code === row.code)}
    {@const details = [row.hit.binding.identifier, row.hit.asset_type ? $t(`assets.types.${row.hit.asset_type}`) : '', row.hit.market ?? '', originText(row, followOrigin)].filter(Boolean)}
    <li class="flex items-center gap-2 px-2.5 py-2 bg-lf-card" data-testid="enrichers-search-row-{key}" data-code={row.code} data-conflict={row.conflict ? 'true' : undefined}>
        <div class="flex-1 min-w-0">
            <p class="text-sm text-lf-primary truncate">{row.hit.name}</p>
            <p class="text-[11px] text-lf-muted flex items-center gap-1 min-w-0">
                <span class="truncate font-mono">{details.join(' · ')}</span>
            </p>
            <p class="text-[11px] text-lf-secondary flex items-center gap-1">
                <EnricherTile code={row.code} name={info?.name ?? row.code} icon={info?.icon ?? null} />
                <span class="truncate">{info?.name ?? row.code}</span>
            </p>
            {#if row.conflict}
                <p class="text-[11px] text-lf-warning flex items-center gap-1" data-testid="enrichers-search-conflict-{key}">
                    <TriangleAlert size={11} aria-hidden="true" />
                    {$t('assets.enrichers.search.conflict', {values: {whose: row.conflict.against === 'asset' ? $t('assets.enrichers.search.whoseAsset') : nameOf(row.conflict.against), isin: row.conflict.isin}})}
                </p>
            {/if}
        </div>
        {#if row.hit.page_url}
            <a class="shrink-0 p-1 rounded text-lf-muted hover:text-lf-secondary hover:bg-lf-hover" href={row.hit.page_url} target="_blank" rel="noopener noreferrer" title={$t('assets.enrichers.openPage')} aria-label={$t('assets.enrichers.openPage')}>
                <ExternalLink size={14} />
            </a>
        {/if}
        {#if confirming === key}
            <button type="button" class="shrink-0 px-2 h-8 text-xs font-medium rounded-md border border-lf-warning-line bg-lf-warning-soft text-lf-warning-on-soft hover:bg-lf-hover" onclick={() => add(row, key)} data-testid="enrichers-search-confirm-{key}">
                {$t('assets.enrichers.search.confirmAdd')}
            </button>
        {:else}
            <button
                type="button"
                class="shrink-0 inline-flex items-center justify-center w-8 h-8 rounded-md border border-lf-input bg-lf-card text-lf-link hover:bg-lf-hover"
                title={$t('assets.enrichers.add')}
                aria-label={$t('assets.enrichers.add')}
                onclick={() => add(row, key)}
                data-testid="enrichers-search-add-{key}"
            >
                <Plus size={16} />
            </button>
        {/if}
    </li>
{/snippet}

<section class="rounded-lg border border-lf-subtle bg-lf-panel p-3 space-y-2" data-testid="enrichers-search" data-status={status} data-busy={status === 'searching' ? 'true' : 'false'} aria-busy={status === 'searching'}>
    <h3 class="text-[11px] font-semibold tracking-wide uppercase text-lf-muted flex items-center gap-1.5"><Search size={12} aria-hidden="true" />{$t('assets.enrichers.search.title')}</h3>

    {#if suggestions.length}
        <div class="flex flex-wrap items-center gap-1.5 text-xs">
            <span class="text-lf-muted">{$t('assets.enrichers.search.suggestions')}</span>
            {#each suggestions as value, index (value)}
                <button type="button" class="px-2 py-0.5 rounded-full border border-lf-subtle bg-lf-card text-lf-secondary hover:bg-lf-hover max-w-full truncate" onclick={() => suggest(value)} data-testid="enrichers-search-suggestion-{index}" data-value={value}>
                    {value}
                </button>
            {/each}
        </div>
    {/if}

    <div class="relative">
        <Search size={14} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-lf-muted" aria-hidden="true" />
        <input
            type="text"
            class="w-full pl-8 pr-8 py-1.5 text-sm rounded-md border border-lf-input bg-lf-field text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:border-lf-focus"
            placeholder={$t('assets.enrichers.search.placeholder')}
            aria-label={$t('assets.enrichers.search.title')}
            bind:value={query}
            oninput={schedule}
            data-testid="enrichers-search-input"
        />
        {#if status === 'searching'}
            <LoaderCircle size={14} class="absolute right-2.5 top-1/2 -translate-y-1/2 animate-spin text-lf-muted" aria-hidden="true" />
        {/if}
    </div>

    {#if pills.length}
        <div class="flex flex-wrap items-center gap-1.5 text-xs">
            <span class="text-lf-muted">{$t('assets.enrichers.search.pills')}</span>
            {#each pills as pill (pill.code)}
                <button
                    type="button"
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border {pill.on ? 'border-lf-success-line bg-lf-success-soft text-lf-success-on-soft' : 'border-lf-subtle bg-lf-card text-lf-muted line-through'}"
                    aria-pressed={pill.on}
                    onclick={() => toggle(pill.code)}
                    data-testid="enrichers-search-pill-{pill.code}"
                    data-on={pill.on ? 'true' : 'false'}
                    data-identifier-only={pill.identifierOnly ? 'true' : undefined}
                >
                    {pill.info.name}
                    {#if pill.identifierOnly}<span class="text-[10px] opacity-80">{$t('assets.enrichers.search.identifierOnly', {values: {types: pill.info.accepted_identifier_types.join(', ')}})}</span>{/if}
                </button>
            {/each}
        </div>
    {/if}
    {#if excluded.length}
        <p class="text-[11px] text-lf-muted" data-testid="enrichers-search-excluded">{$t('assets.enrichers.search.excluded', {values: {names: excluded.map((info) => info.name).join(', ')}})}</p>
    {/if}

    {#if status === 'refused'}
        <p class="text-xs text-lf-warning" data-testid="enrichers-search-refused">{$t('assets.enrichers.search.refused')}</p>
    {:else if status === 'error'}
        <p class="text-xs text-lf-danger" data-testid="enrichers-search-failed">{$t('assets.enrichers.search.failed')}</p>
    {/if}

    {#if rows.length || followRows.some((follow) => follow.rows.length)}
        <ul class="rounded-md border border-lf-subtle divide-y divide-lf-subtle overflow-hidden" data-testid="enrichers-search-results">
            {#each followRows as follow (follow.isin)}
                {#each keyed(follow.rows, `isin-${follow.isin}-`) as entry (entry.key)}
                    {@render resultRow(entry.row, entry.key, follow.origin)}
                {/each}
            {/each}
            {#each keyed(rows) as entry (entry.key)}
                {@render resultRow(entry.row, entry.key, null)}
            {/each}
        </ul>
    {/if}

    {#each notes as answer (answer.code)}
        <p class="text-[11px] text-lf-muted" data-testid="enrichers-search-note-{answer.code}" data-status={answer.status}>{noteText(answer)}</p>
    {/each}

    {#if lastAdded && draft.order.includes(lastAdded.code)}
        <p class="text-xs text-lf-success flex items-center gap-1" data-testid="enrichers-search-added" data-code={lastAdded.code}>
            <Check size={12} aria-hidden="true" />{$t('assets.enrichers.search.added', {values: {name: nameOf(lastAdded.code), n: lastAdded.position}})}
        </p>
    {/if}
</section>
