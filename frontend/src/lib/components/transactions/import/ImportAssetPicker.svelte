<!--
  ImportAssetPicker.svelte — one field to name the instrument a row belongs to.

  Replaces a pair of selects in which the first list mixed **things** (the instruments this import
  found) with a **place to go look** ("assets already catalogued"), and in which creating a new
  asset sat two levels down — reachable only by failing twice, first in the import list, then in
  the archive one.

  The root defect was that we asked the user to choose a *provenance* when they only wanted to
  name a *thing*. Provenance — fake ids for this import, real ids for the archive — is our own
  bookkeeping, and after the unification step it is not even a real distinction: most import
  instruments are already bound to an archived asset, so the two sets overlap.

  So: one list, sections instead of modes.
    · the section title answers "why is this here" without the user having to choose it;
    · the import section comes first because it is right nearly always — the rows being corrected
      came from those very files;
    · an instrument already bound to the archive appears **once**, under the import section, with
      the "in archive" badge. Listing it twice would be a trap: same security, two rows, and no
      way to tell which one behaves;
    · creating is the sticky footer, always visible, carrying the text just typed — the natural
      end of a search that found nothing, rather than something to discover.

  The value is a discriminated selection rather than `number | null`, because "no instrument"
  (a broker fee belongs to nobody) and "not answered yet" are different answers that a bare null
  cannot tell apart — an ambiguity the caller previously had to patch with a parallel set.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {t} from 'svelte-i18n';
    import SearchSelect from '$lib/components/ui/select/SearchSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import {ensureAssetsLoaded, getAllAssets, assetStoreVersion, type AssetInfo} from '$lib/stores/reference/assetStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';

    /** One instrument this import found, already unified across files. */
    export interface ImportAssetItem {
        id: number;
        label: string;
        /** Codes carried by the group, shown under the name and searchable. */
        detail?: string;
        /** The group is bound to an archived asset: it must not appear twice. */
        archiveId?: number | null;
    }

    /**
     * What the user picked. `none` is an answer, `null` is the absence of one — a broker fee that
     * belongs to no security is settled, an untouched row is not.
     */
    export type PickedAsset = {kind: 'asset'; id: number} | {kind: 'none'} | null;

    interface Props {
        value: PickedAsset;
        /** The instruments this import found. Shown first, and pre-selected by search. */
        importAssets: ImportAssetItem[];
        /**
         * Wording for the explicit "belongs to no instrument" answer (fees, taxes).
         *
         * Its presence is what enables the row: offering the answer without wording it is a state
         * that should not be expressible, so there is no separate flag to disagree with it.
         */
        noneLabel?: string;
        placeholder?: string;
        disabled?: boolean;
        compact?: boolean;
        testid?: string;
        onchange: (value: PickedAsset) => void;
        /** The user wants a security nothing knows about yet; the query is what they typed. */
        oncreate?: (query: string) => void;
    }

    let {value, importAssets, noneLabel, placeholder, disabled = false, compact = false, testid = 'import-asset-picker', onchange, oncreate}: Props = $props();

    const NONE = '__none__';
    const SECTION_IMPORT = '__section:import';
    const SECTION_ARCHIVE = '__section:archive';

    let loading = $state(true);

    onMount(async () => {
        await ensureAssetsLoaded();
        loading = false;
    });

    /** Archive assets already represented by an import entry — hidden from the archive section. */
    let boundArchiveIds = $derived(new Set(importAssets.map((a) => a.archiveId).filter((id): id is number => typeof id === 'number')));

    let archiveAssets = $derived.by<AssetInfo[]>(() => {
        // Subscribe to the version counter so the list re-derives on cache mutation.
        void $assetStoreVersion;
        const all = getAllAssets().filter((a) => !boundArchiveIds.has(a.id));
        // Inactive assets stay selectable: imports are retroactive, and final coupons, redemptions
        // and loyalty premiums land on matured — hence deactivated — securities.
        return [...all].sort((a, b) => (a.active !== b.active ? (a.active ? -1 : 1) : a.display_name.localeCompare(b.display_name)));
    });

    let options = $derived.by<SelectOption[]>(() => {
        const out: SelectOption[] = [];
        if (noneLabel) out.push({value: NONE, label: noneLabel, data: {source: 'none'}});
        if (importAssets.length > 0) {
            out.push({value: SECTION_IMPORT, label: $t('importWizard.assetPicker.sectionImport'), header: true});
            for (const item of importAssets) {
                out.push({
                    value: `import:${item.id}`,
                    label: item.label,
                    searchText: item.detail,
                    badge: typeof item.archiveId === 'number' ? $t('importWizard.assetUnify.fromDb') : undefined,
                    badgeClass: 'bg-gray-200 text-gray-700 dark:bg-slate-600 dark:text-gray-200',
                    data: {source: 'import', item},
                });
            }
        }
        if (archiveAssets.length > 0) {
            out.push({value: SECTION_ARCHIVE, label: $t('importWizard.assetPicker.sectionArchive'), header: true});
            for (const asset of archiveAssets) {
                out.push({
                    value: `db:${asset.id}`,
                    // `identifier_other` holds alternate codes — the non-tradeable "CUM" ISIN of an
                    // Italian BTP among them — and omitting it made those codes unsearchable.
                    // Currency and asset type stay out: they are shared by hundreds of rows, so a
                    // query that prefixes one (`eur`) would match the entire archive.
                    searchText: [asset.identifier_isin, asset.identifier_ticker, ...(asset.identifier_other ?? [])].filter(Boolean).join(' '),
                    label: asset.display_name,
                    icon: asset.icon_url || (asset.asset_type ? getAssetTypeIconUrl(asset.asset_type) : undefined),
                    data: {source: 'db', asset},
                });
            }
        }
        return out;
    });

    /**
     * Which row is selected.
     *
     * An id can be an import instrument or an archived asset, and the two spaces do not collide
     * today — but leaning on that would make a future id scheme silently mis-select. Membership in
     * the import list is the honest test.
     *
     * A bound archive id resolves to *its group*: that archive row is hidden by the dedup, so
     * matching it literally would leave the field looking unanswered right after an answer.
     */
    let selectedValue = $derived.by(() => {
        if (value === null) return '';
        if (value.kind === 'none') return NONE;
        if (importAssets.some((a) => a.id === value.id)) return `import:${value.id}`;
        const bound = importAssets.find((a) => a.archiveId === value.id);
        return bound ? `import:${bound.id}` : `db:${value.id}`;
    });

    function handleChange(raw: string) {
        if (raw === '') return onchange(null);
        if (raw === NONE) return onchange({kind: 'none'});
        const [, id] = raw.split(':');
        onchange({kind: 'asset', id: Number(id)});
    }

    function hideOnError(e: Event) {
        const img = e.currentTarget as HTMLImageElement | null;
        if (img) img.style.display = 'none';
    }

    interface OptionData {
        source: 'import' | 'db' | 'none';
        item?: ImportAssetItem;
        asset?: AssetInfo;
    }

    /** Safe cast helper — avoids `as` in Svelte 5 templates. */
    function payload(data: unknown): OptionData {
        return (data ?? {source: 'none'}) as OptionData;
    }
</script>

<div data-testid={testid}>
    <SearchSelect
        value={selectedValue}
        {options}
        {disabled}
        {loading}
        {compact}
        placeholder={placeholder ?? $t('common.select')}
        inlineSearch={true}
        maxVisibleItems={10}
        createLabel={oncreate ? $t('importWizard.assetPicker.create') : ''}
        createLabelFor={(query) => $t('importWizard.assetPicker.createNamed', {values: {name: query}})}
        onCreateNew={oncreate}
        onchange={handleChange}
        testId="{testid}-select"
    >
        {#snippet selectedItem(option)}
            {@const d = payload(option.data)}
            <div class="flex min-w-0 items-center gap-2">
                {#if option.icon}
                    <img src={option.icon} alt="" class="h-5 w-5 shrink-0 rounded-sm object-contain" onerror={hideOnError} />
                {/if}
                <span class="truncate text-sm text-gray-900 dark:text-gray-100">{option.label}</span>
                {#if d.source === 'import' && typeof d.item?.archiveId === 'number'}
                    <span class="shrink-0 rounded bg-gray-200 px-1.5 py-0.5 text-[10px] font-medium text-gray-700 dark:bg-slate-600 dark:text-gray-200">{$t('importWizard.assetUnify.fromDb')}</span>
                {/if}
                {#if d.asset?.active === false}
                    <span class="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-slate-700 dark:text-gray-400">{$t('assets.edit.status.inactive')}</span>
                {/if}
            </div>
        {/snippet}
        {#snippet item(option)}
            {@const d = payload(option.data)}
            <div class="flex min-w-0 items-center gap-2">
                {#if option.icon}
                    <img src={option.icon} alt="" class="h-4 w-4 shrink-0 rounded-sm object-contain" onerror={hideOnError} />
                {/if}
                <span class="min-w-0 flex-1">
                    <span class="block truncate text-sm {d.asset?.active === false ? 'opacity-60' : ''}">{option.label}</span>
                    {#if option.searchText}
                        <span class="block truncate font-mono text-[10px] text-gray-500 dark:text-gray-400">{option.searchText}</span>
                    {/if}
                </span>
                {#if option.badge}
                    <span class="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium {option.badgeClass}">{option.badge}</span>
                {/if}
                {#if d.asset?.active === false}
                    <span class="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-slate-700 dark:text-gray-400">{$t('assets.edit.status.inactive')}</span>
                {/if}
                {#if d.asset?.currency}
                    {@const ci = getCurrencyInfo(d.asset.currency)}
                    <span class="shrink-0 font-mono text-[10px] opacity-60">
                        {#if ci.flag_emoji}<span class="emoji-flag">{ci.flag_emoji}</span>{/if}
                        {d.asset.currency}
                    </span>
                {/if}
            </div>
        {/snippet}
    </SearchSelect>
</div>
