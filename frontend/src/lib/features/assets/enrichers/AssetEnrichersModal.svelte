<!--
  AssetEnrichersModal — the «Arricchitori dell'asset» window (plan 68, E7b2), opened only from the asset window (E8),
  for a new asset and for one that exists: it hands the list back (`onapply`) and the asset window saves it with the
  asset. The decisions are `enrichersEditState.ts`'s; this component keeps the DOM, the searches and the tests.

  - The asset, its type and its identifiers on top; a line on what enrichers do.
  - «Arricchitori scelti»: the enrichers in their order (drag, or arrows on the phone), each a row that opens
    (`EnricherChosenRow`). A binding to an enricher the instance does not serve stays in its place, drawn off.
  - «Non in elenco»: the others of the catalogue with their reason, «+» to add the ones that can be.
  - «Configura» on a not configured enricher opens its settings over the window (`PluginSettingsModal`, family
    `enricher`); once saved the row is usable.

  `search` and `test` default to the API; a caller (a test, the screenshots) may pass its own. «Riconosci» is the asset
  window's: it hands over what it found (`recognitions`), the codes it is still asking (`searching`), its line (`line`,
  on top of the window) and its proposal. A window opened «to adopt» (`adopt`: an asset with no enrichers, or a new one
  whose list the user has not applied yet) takes the proposal into its draft while the user has not touched the list
  (ENR-1, R2); after a touch, what is found later waits in «Non in elenco».

  «Cerca online» sits on top, under the asset's box (ENR-3, `EnricherOnlineSearch`): a result's «+» puts its binding at
  the end of the list, the row closed. At «Usa questi arricchitori» the identifiers those results carry are handed back
  for the asset's empty columns (R7, `suggestedIdentifiers`): the asset window shows them as suggested rows.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {untrack} from 'svelte';
    import {ChevronDown, ChevronUp, LoaderCircle, Plus} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import PluginSettingsModal from '$lib/features/plugin-settings/PluginSettingsModal.svelte';
    import {fetchPluginEntry, type PluginSettingsEntry} from '$lib/features/plugin-settings/pluginSettingsApi';
    import {assetTypeBadgeClass} from '$lib/utils/assetTypes';
    import type {ProfileVoice} from '$lib/features/assets/profile/profileStore';
    import {IDENTIFIER_TYPES} from '$lib/utils/assetTypes';
    import EnricherChosenRow from './EnricherChosenRow.svelte';
    import EnricherOnlineSearch from './EnricherOnlineSearch.svelte';
    import type {EnricherSearchEvent, EnricherSearchOutcome, EnricherSearchRequest} from './enricherSearchStream';
    import EnricherTile from './EnricherTile.svelte';
    import {searchEnricher, testEnricher, type SearchCall, type TestCall} from './enricherCalls';
    import {
        addEnricher,
        addFromSearch,
        adoptProposal,
        chosenRows,
        draftFrom,
        draftIssues,
        otherRows,
        removeEnricher,
        reorder,
        resultConfig,
        setBinding,
        suggestedIdentifiers,
        topicsOf,
        type ChosenRow,
        type EnricherBinding,
        type EnricherInfo,
        type EnricherReadState,
        type EnricherRecognition,
        type EnrichersContext,
        type EnrichersDraft,
        type OtherRow,
        type RecognitionLine,
        type SearchHit,
    } from './enrichersEditState';

    interface Props {
        open?: boolean;
        /** The asset as the asset window knows it: name, type, the identifiers known (type → value). */
        asset: {name: string; assetType: string; identifiers: Record<string, string>};
        /** The list the window opens with (`enrichers.config`, or what «Riconosci» proposed). */
        config: Record<string, EnricherBinding>;
        /** The asset's `enrichers.state`: the last read of each (empty for an asset not created yet). Not named `state`:
         *  Svelte would read the `$state` rune as that prop's store. */
        readState?: Record<string, EnricherReadState>;
        /** `GET /assets/enrichers`. */
        catalogue: EnricherInfo[];
        /** `GET /assets/profile/catalogue`: what each voice is about (its topic). */
        profileCatalogue: Pick<ProfileVoice, 'key' | 'topic'>[];
        recognitions?: Record<string, EnricherRecognition>;
        searching?: string[];
        /** «Riconosci»'s proposal: the found ones that enter by themselves, in the default order. */
        proposal?: Record<string, EnricherBinding>;
        /** Read at each opening: the window takes the proposal into its draft until the user touches the list (R2). */
        adopt?: boolean;
        /** The line of «Riconosci» on top of the window; null: nothing to say yet. */
        line?: RecognitionLine | null;
        /** The asset's price assignment, shown in the asset's box (ENR-2, «PREZZI»): the provider's name and identifier. */
        price?: {name: string; identifier: string} | null;
        /** The tickers a found one may enter by: the price assignment's symbol (ENR-2, R6). */
        trustedTickers?: string[];
        zIndex?: number;
        /** The list chosen, and the identifiers the search's results carry for the asset's empty columns (R7). */
        onapply: (config: Record<string, EnricherBinding>, extras?: {identifiers: Record<string, string>}) => void;
        oncancel?: () => void;
        search?: SearchCall;
        test?: TestCall;
        /** «Cerca online»'s call (a test passes its own). */
        searchOnline?: (request: EnricherSearchRequest, options: {onEvent: (event: EnricherSearchEvent) => void; signal?: AbortSignal}) => Promise<EnricherSearchOutcome>;
        /** The settings of an enricher as the caller may see them; null when it may not (no «Configura», as for the price
         *  providers, N3). */
        loadSettings?: (code: string) => Promise<PluginSettingsEntry | null>;
    }

    let {
        open = $bindable(false),
        asset,
        config,
        readState = {},
        catalogue,
        profileCatalogue,
        recognitions = {},
        searching = [],
        proposal = {},
        adopt = false,
        line = null,
        price = null,
        trustedTickers = [],
        zIndex = 70,
        onapply,
        oncancel,
        search = searchEnricher,
        test = testEnricher,
        searchOnline = undefined,
        loadSettings = (code) => fetchPluginEntry('enricher', code),
    }: Props = $props();

    // A not configured enricher becomes usable once its settings are saved here
    let configuredNow = $state<Set<string>>(new Set());
    // «Configura» only for an enricher whose settings the caller may see, asked once per code
    let settingsVisible = $state<Set<string>>(new Set());
    const settingsAsked = new Set<string>();
    $effect(() => {
        for (const info of catalogue) {
            if (info.configured !== false || settingsAsked.has(info.code)) continue;
            settingsAsked.add(info.code);
            loadSettings(info.code).then(
                (entry) => {
                    if (entry) settingsVisible = new Set(settingsVisible).add(info.code);
                },
                () => {
                    // Not known: no «Configura». A test or a search still says the enricher is not configured.
                },
            );
        }
    });

    let liveCatalogue = $derived(catalogue.map((info) => (configuredNow.has(info.code) ? {...info, configured: true, missing_settings: []} : info)));

    let draft = $state<EnrichersDraft>(untrack(() => draftFrom(config)));
    /** The user changed the list (an order, a removal, an addition, a binding): the proposal no longer enters it. */
    let touched = $state(false);
    let adopting = $state(untrack(() => adopt));
    let expanded = $state<string | null>(null);
    let othersOpen = $state(true);
    let configuring = $state<EnricherInfo | null>(null);

    let wasOpen = untrack(() => open);
    $effect(() => {
        const isOpen = open;
        untrack(() => {
            if (isOpen && !wasOpen) {
                draft = draftFrom(config);
                touched = false;
                adopting = adopt;
                fromSearch = new Set();
                expanded = null;
            }
            wasOpen = isOpen;
        });
    });

    // «Riconosci»'s proposal enters the list while the user has not touched it (R2)
    $effect(() => {
        const next = proposal;
        if (!open) return;
        untrack(() => {
            if (adopting && !touched) draft = adoptProposal(draft, next);
        });
    });

    /** The codes added from «Cerca online»: their identifiers are proposed for the asset's empty columns (R7). */
    let fromSearch = $state<Set<string>>(new Set());

    function addSearchHit(code: string, hit: SearchHit): void {
        change(addFromSearch(draft, code, hit.binding));
        fromSearch = new Set(fromSearch).add(code);
    }

    /** A change of the user's: from now on the list is theirs. */
    function change(next: EnrichersDraft): void {
        draft = next;
        touched = true;
    }

    let context = $derived<EnrichersContext>({catalogue: liveCatalogue, assetType: asset.assetType, state: readState, recognitions, searching, trustedTickers});
    let chosen = $derived(chosenRows(draft, context));
    let others = $derived(otherRows(draft, context));
    let issues = $derived(draftIssues(draft, context));
    let valid = $derived(Object.keys(issues).length === 0);

    function topics(fills: string[]): {labels: string[]; codes: string[]; more: number} {
        const found = topicsOf(fills, profileCatalogue);
        return {codes: found.topics, labels: found.topics.map((topic) => $t(`assets.profile.topics.${topic}`)), more: found.more};
    }

    function otherReason(row: OtherRow): string {
        if (row.reason === 'new') return '';
        if (row.reason === 'found' && row.tickerOnly) return $t('assets.enrichers.reasons.foundByTicker', {values: {ticker: row.recognition?.identifier ?? ''}});
        if (row.reason === 'found') return $t('assets.enrichers.reasons.found');
        if (row.reason === 'removed') return $t('assets.enrichers.reasons.removed');
        if (row.reason === 'not_found') {
            const identifier = row.recognition?.identifier ?? '';
            return $t('assets.enrichers.reasons.not_found', {values: {type: row.recognition?.identifier_type ?? '', identifier}});
        }
        return $t(`assets.enrichers.reasons.${row.reason}`);
    }

    function close(): void {
        open = false;
        oncancel?.();
    }

    function apply(): void {
        if (!valid) return;
        onapply(resultConfig(draft), {identifiers: suggestedIdentifiers(draft, fromSearch, asset.identifiers, IDENTIFIER_TYPES)});
        open = false;
    }

    function add(row: OtherRow): void {
        change(addEnricher(draft, row.code, row.recognition, {accepted: row.info.accepted_identifier_types, identifiers: asset.identifiers}));
        // The row opens only when it still needs a hand: no identifier, or one «Riconosci» found nothing with (R3)
        if (!draft.bindings[row.code]?.identifier || row.recognition?.status === 'not_found') expanded = row.code;
    }

    let lineNames = $derived(line ? line.found.map((code) => liveCatalogue.find((info) => info.code === code)?.name ?? code).join(', ') : '');
    /** The found ones not in the list: they wait in «Non in elenco», with «+». */
    let foundOutside = $derived(line ? line.found.filter((code) => !draft.order.includes(code)).length : 0);

    function lineText(current: RecognitionLine): string {
        if (current.state === 'running') return $t('assets.enrichers.line.running', {values: {answered: current.answered, asked: current.asked}});
        if (current.state === 'found') {
            const hint = foundOutside ? $t('assets.enrichers.line.foundOutside') : adopting ? $t('assets.enrichers.line.foundAdopted') : '';
            return [$t('assets.enrichers.line.found', {values: {count: current.found.length, names: lineNames}}), hint].filter(Boolean).join(' ');
        }
        return $t(`assets.enrichers.line.${current.state}`);
    }
</script>

<ModalBase {open} maxWidth="lg" allowOverflow={true} onRequestClose={close} {zIndex} testId="enrichers-modal" labelledBy="enrichers-title">
    <div class="flex flex-col max-h-[90vh] text-lf-primary">
        <header class="px-4 sm:px-6 py-4 border-b border-lf-subtle">
            <h2 id="enrichers-title" class="text-lg font-semibold text-lf-primary">{$t('assets.enrichers.title')}</h2>
        </header>

        <div class="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-4">
            <div class="rounded-lg border border-lf-subtle bg-lf-panel px-3 py-2.5" data-testid="enrichers-asset">
                <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-sm font-semibold text-lf-primary">{asset.name}</span>
                    <span class="px-1.5 py-0.5 text-[10px] font-medium rounded {assetTypeBadgeClass(asset.assetType)}" data-testid="enrichers-asset-type" data-type={asset.assetType}>{$t(`assets.types.${asset.assetType}`)}</span>
                </div>
                {#if Object.keys(asset.identifiers).length || price}
                    <div class="mt-1.5 flex flex-wrap gap-1.5">
                        {#each Object.entries(asset.identifiers) as [type, value] (type)}
                            <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-lf-subtle bg-lf-card text-[11px] font-mono text-lf-secondary">
                                <span class="text-lf-muted">{type}</span>{value}
                            </span>
                        {/each}
                        {#if price}
                            <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-lf-subtle bg-lf-card text-[11px] text-lf-secondary" data-testid="enrichers-asset-price">
                                <span class="text-lf-muted uppercase">{$t('assets.enrichers.price')}</span>{price.name} · <span class="font-mono">{price.identifier}</span>
                            </span>
                        {/if}
                    </div>
                {/if}
            </div>

            <EnricherOnlineSearch catalogue={liveCatalogue} assetType={asset.assetType} {draft} assetIdentifiers={asset.identifiers} assetName={asset.name} onadd={addSearchHit} {...searchOnline ? {search: searchOnline} : {}} />

            {#if line}
                <div data-testid="enrichers-recognition" data-state={line.state} data-answered={line.answered} data-asked={line.asked}>
                    <InfoBanner variant={line.state === 'refused' || line.state === 'error' ? 'warning' : line.state === 'found' ? 'success' : 'info'}>
                        <span class="inline-flex items-center gap-1.5">
                            {#if line.state === 'running'}<LoaderCircle size={12} class="animate-spin shrink-0" aria-hidden="true" />{/if}
                            <span>{lineText(line)}</span>
                        </span>
                    </InfoBanner>
                </div>
            {/if}

            <InfoBanner variant="info" message={$t('assets.enrichers.intro')} />

            <section>
                <h3 class="text-[11px] font-semibold tracking-wide uppercase text-lf-muted mb-2">{$t('assets.enrichers.chosen')}</h3>
                {#if chosen.length}
                    <OrderableList
                        items={chosen}
                        keyFn={(row: ChosenRow) => row.code}
                        onReorder={(rows: ChosenRow[]) =>
                            change(
                                reorder(
                                    draft,
                                    rows.map((row) => row.code),
                                ),
                            )}
                        itemTone={(row: ChosenRow) => (row.issue ? 'error' : expanded === row.code ? 'selected' : row.availability === 'not_configured' ? 'warning' : 'default')}
                    >
                        {#snippet children({item})}
                            <EnricherChosenRow
                                row={item}
                                topics={topics(item.fills)}
                                expanded={expanded === item.code}
                                {search}
                                {test}
                                canConfigure={settingsVisible.has(item.code)}
                                ontoggle={() => (expanded = expanded === item.code ? null : item.code)}
                                onremove={() => {
                                    change(removeEnricher(draft, item.code));
                                    if (expanded === item.code) expanded = null;
                                }}
                                onbinding={(binding) => change(setBinding(draft, item.code, binding))}
                                onconfigure={() => (configuring = item.info)}
                            />
                        {/snippet}
                    </OrderableList>
                {:else}
                    <p class="text-xs text-lf-muted" data-testid="enrichers-none-chosen">{$t('assets.enrichers.noneChosen')}</p>
                {/if}
            </section>

            {#if others.length}
                <section>
                    <button
                        type="button"
                        class="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-dashed border-lf-success-line bg-lf-success-soft text-lf-success-on-soft hover:bg-lf-hover"
                        aria-expanded={othersOpen}
                        onclick={() => (othersOpen = !othersOpen)}
                        data-testid="enrichers-others-toggle"
                    >
                        {#if othersOpen}<ChevronUp size={14} aria-hidden="true" />{:else}<ChevronDown size={14} aria-hidden="true" />{/if}
                        {othersOpen ? $t('assets.enrichers.hideOthers') : $t('assets.enrichers.showOthers', {values: {count: others.length}})}
                    </button>
                    {#if othersOpen}
                        <div class="mt-2 rounded-lg border border-lf-subtle bg-lf-panel p-3 space-y-2" data-testid="enrichers-others">
                            <h3 class="text-[11px] font-semibold tracking-wide uppercase text-lf-muted">{$t('assets.enrichers.others')}</h3>
                            {#each others as row (row.code)}
                                {@const found = topics(row.fills)}
                                <div class="flex items-start gap-2 rounded-md border border-lf-subtle bg-lf-card px-2.5 py-2" data-testid="enricher-other-{row.code}" data-reason={row.reason} data-ticker-only={row.tickerOnly ? 'true' : undefined}>
                                    <EnricherTile code={row.code} name={row.info.name} icon={row.info.icon ?? null} muted={!row.canAdd} />
                                    <div class="flex-1 min-w-0">
                                        <div class="flex items-center gap-1.5 flex-wrap">
                                            <span class="text-sm font-medium {row.canAdd ? 'text-lf-primary' : 'text-lf-muted'}">{row.info.name}</span>
                                            {#if row.binding?.identifier_type ?? row.info.accepted_identifier_types[0]}
                                                <span class="px-1.5 py-0.5 rounded bg-lf-neutral text-[10px] font-mono text-lf-secondary">{row.binding?.identifier_type ?? row.info.accepted_identifier_types[0]}</span>
                                            {/if}
                                        </div>
                                        {#if row.reason === 'found' && row.recognition?.name}
                                            <p class="text-xs text-lf-secondary truncate" data-testid="enricher-other-name-{row.code}">{row.recognition.name}</p>
                                        {:else if row.binding?.identifier && row.reason !== 'found'}
                                            <p class="text-xs text-lf-secondary truncate">{row.binding.identifier}</p>
                                        {/if}
                                        <p class="text-[11px] {row.tickerOnly ? 'text-lf-warning' : 'text-lf-muted'}">
                                            {[otherReason(row), found.labels.join(', ')].filter(Boolean).join(' · ')}
                                        </p>
                                    </div>
                                    {#if row.reason === 'not_configured' && settingsVisible.has(row.code)}
                                        <button type="button" class="shrink-0 px-2 py-1 text-xs font-medium rounded-md border border-lf-input bg-lf-card text-lf-link hover:bg-lf-hover" onclick={() => (configuring = row.info)} data-testid="enricher-configure-{row.code}">
                                            {$t('assets.enrichers.configure')}
                                        </button>
                                    {:else if row.canAdd}
                                        <button type="button" class="shrink-0 p-1 rounded text-lf-muted hover:text-lf-link hover:bg-lf-hover" title={$t('assets.enrichers.add')} aria-label={$t('assets.enrichers.add')} onclick={() => add(row)} data-testid="enricher-add-{row.code}">
                                            <Plus size={16} />
                                        </button>
                                    {/if}
                                </div>
                            {/each}
                            <p class="text-[11px] text-lf-muted">{$t('assets.enrichers.othersHelp')}</p>
                        </div>
                    {/if}
                </section>
            {/if}
        </div>

        <footer class="px-4 sm:px-6 py-3 border-t border-lf-subtle bg-lf-panel flex justify-end gap-2">
            <button type="button" class="px-4 py-2 text-sm font-medium rounded-lg border border-lf-subtle bg-lf-card text-lf-secondary hover:bg-lf-hover" onclick={close} data-testid="enrichers-cancel">
                {$t('common.cancel')}
            </button>
            <button type="button" class="px-4 py-2 text-sm font-medium rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed" disabled={!valid} onclick={apply} data-testid="enrichers-apply">
                {$t('assets.enrichers.apply')}
            </button>
        </footer>
    </div>
</ModalBase>

{#if configuring}
    {@const plugin = configuring}
    <PluginSettingsModal
        open={true}
        family="enricher"
        pluginCode={plugin.code}
        pluginName={plugin.name}
        zIndex={zIndex + 10}
        onClose={() => (configuring = null)}
        onSaved={(fresh) => {
            if (fresh.configured) configuredNow = new Set(configuredNow).add(plugin.code);
        }}
    />
{/if}
