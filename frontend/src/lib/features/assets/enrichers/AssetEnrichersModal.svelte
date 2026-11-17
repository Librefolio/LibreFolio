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
  window's: it hands over what it found (`recognitions`) and the codes it is still asking (`searching`).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {untrack} from 'svelte';
    import {ChevronDown, ChevronUp, Plus} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import PluginSettingsModal from '$lib/features/plugin-settings/PluginSettingsModal.svelte';
    import {fetchPluginEntry, type PluginSettingsEntry} from '$lib/features/plugin-settings/pluginSettingsApi';
    import {assetTypeBadgeClass} from '$lib/utils/assetTypes';
    import type {ProfileVoice} from '$lib/features/assets/profile/profileStore';
    import EnricherChosenRow from './EnricherChosenRow.svelte';
    import EnricherTile from './EnricherTile.svelte';
    import {searchEnricher, testEnricher, type SearchCall, type TestCall} from './enricherCalls';
    import {
        addEnricher,
        chosenRows,
        draftFrom,
        draftIssues,
        otherRows,
        removeEnricher,
        reorder,
        resultConfig,
        setBinding,
        topicsOf,
        type ChosenRow,
        type EnricherBinding,
        type EnricherInfo,
        type EnricherReadState,
        type EnricherRecognition,
        type EnrichersContext,
        type EnrichersDraft,
        type OtherRow,
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
        zIndex?: number;
        onapply: (config: Record<string, EnricherBinding>) => void;
        oncancel?: () => void;
        search?: SearchCall;
        test?: TestCall;
        /** The settings of an enricher as the caller may see them; null when it may not (no «Configura», as for the price
         *  providers, N3). */
        loadSettings?: (code: string) => Promise<PluginSettingsEntry | null>;
    }

    let {open = $bindable(false), asset, config, readState = {}, catalogue, profileCatalogue, recognitions = {}, searching = [], zIndex = 70, onapply, oncancel, search = searchEnricher, test = testEnricher, loadSettings = (code) => fetchPluginEntry('enricher', code)}: Props = $props();

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
    let expanded = $state<string | null>(null);
    let othersOpen = $state(true);
    let configuring = $state<EnricherInfo | null>(null);

    let wasOpen = untrack(() => open);
    $effect(() => {
        const isOpen = open;
        untrack(() => {
            if (isOpen && !wasOpen) {
                draft = draftFrom(config);
                expanded = null;
            }
            wasOpen = isOpen;
        });
    });

    let context = $derived<EnrichersContext>({catalogue: liveCatalogue, assetType: asset.assetType, state: readState, recognitions, searching});
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
        if (row.reason === 'found') return row.recognition?.name ?? $t('assets.enrichers.reasons.found');
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
        onapply(resultConfig(draft));
        open = false;
    }

    function add(row: OtherRow): void {
        draft = addEnricher(draft, row.code, row.recognition, row.info.accepted_identifier_types[0] ?? '');
        if (!draft.bindings[row.code]?.identifier) expanded = row.code;
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
                {#if Object.keys(asset.identifiers).length}
                    <div class="mt-1.5 flex flex-wrap gap-1.5">
                        {#each Object.entries(asset.identifiers) as [type, value] (type)}
                            <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-lf-subtle bg-lf-card text-[11px] font-mono text-lf-secondary">
                                <span class="text-lf-muted">{type}</span>{value}
                            </span>
                        {/each}
                    </div>
                {/if}
            </div>

            <InfoBanner variant="info" message={$t('assets.enrichers.intro')} />

            <section>
                <h3 class="text-[11px] font-semibold tracking-wide uppercase text-lf-muted mb-2">{$t('assets.enrichers.chosen')}</h3>
                {#if chosen.length}
                    <OrderableList
                        items={chosen}
                        keyFn={(row: ChosenRow) => row.code}
                        onReorder={(rows: ChosenRow[]) =>
                            (draft = reorder(
                                draft,
                                rows.map((row) => row.code),
                            ))}
                        itemTone={(row: ChosenRow) => (row.issue ? 'error' : row.availability === 'not_configured' ? 'warning' : 'default')}
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
                                    draft = removeEnricher(draft, item.code);
                                    if (expanded === item.code) expanded = null;
                                }}
                                onbinding={(binding) => (draft = setBinding(draft, item.code, binding))}
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
                                <div class="flex items-start gap-2 rounded-md border border-lf-subtle bg-lf-card px-2.5 py-2" data-testid="enricher-other-{row.code}" data-reason={row.reason}>
                                    <EnricherTile code={row.code} name={row.info.name} icon={row.info.icon ?? null} muted={!row.canAdd} />
                                    <div class="flex-1 min-w-0">
                                        <div class="flex items-center gap-1.5 flex-wrap">
                                            <span class="text-sm font-medium {row.canAdd ? 'text-lf-primary' : 'text-lf-muted'}">{row.info.name}</span>
                                            {#if row.binding?.identifier_type ?? row.info.accepted_identifier_types[0]}
                                                <span class="px-1.5 py-0.5 rounded bg-lf-neutral text-[10px] font-mono text-lf-secondary">{row.binding?.identifier_type ?? row.info.accepted_identifier_types[0]}</span>
                                            {/if}
                                        </div>
                                        {#if row.binding?.identifier && row.reason !== 'found'}
                                            <p class="text-xs text-lf-secondary truncate">{row.binding.identifier}</p>
                                        {/if}
                                        <p class="text-[11px] text-lf-muted">
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
