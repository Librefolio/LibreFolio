<!--
  AssetSelect.svelte — Reusable asset picker backed by `assetStore`.

  Wraps `SearchSelect` with options derived from the global asset cache.
  The cache is loaded lazily (`ensureAssetsLoaded()` is called on mount), so
  the component is self-sufficient — callers just bind a `value: number | null`.

  Each option shows: [type icon] display_name [(currency)]; inactive assets remain
  selectable but are sorted last and marked with an "inactive" badge (P3/A1).

  Pattern: Svelte 5 runes, dark mode via Tailwind, `data-testid` for E2E.

  Used by: TransactionStagingModal, TransferPromoteModal, future BRIM staging.
  Migrate other asset_id pickers (e.g. DistributionEditor) to use this when convenient.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import SearchSelect from './SearchSelect.svelte';
    import type {SelectOption} from './types';
    import {ensureAssetsLoaded, getAllAssets, assetStoreVersion, type AssetInfo} from '$lib/stores/reference/assetStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

    interface Props {
        /** Currently selected asset id (null = none). */
        value: number | null;
        /** Disable the select. */
        disabled?: boolean;
        /** Optional filter applied on top of the cache (e.g. only same currency). */
        filter?: (a: AssetInfo) => boolean;
        /** Placeholder when no value is selected. */
        placeholder?: string;
        /** Test id for E2E targeting. */
        testid?: string;
        /** Compact trigger padding (matches standard inputs). */
        compact?: boolean;
        /** Label for the "Create new" footer button (e.g. "+ New asset"). */
        createLabel?: string;
        /** Callback when user clicks the "Create new" footer. */
        onCreateNew?: () => void;
        /** Change callback (number | null). */
        onchange?: (value: number | null) => void;
        /** Prioritized items shown at the top of the list with a badge (e.g. BRIM candidates). */
        suggestedIds?: Array<{id: number; badge: string; badgeClass?: string; badgeTooltip?: string}>;
        /**
         * Split the list into labelled, ordered sections (K3).
         *
         * Each asset joins the **first** section whose `match` accepts it, so the
         * array order is the screen order and overlapping predicates are resolved
         * rather than duplicated. A section that ends up empty prints no title:
         * `SearchSelect` already drops a header whose section is emptied by the
         * search, and an always-empty one would be a promise the list never keeps.
         *
         * Leave it undefined for a flat list — that is still the right answer for
         * pickers where every asset is equally plausible.
         */
        sections?: Array<{key: string; label: string; match: (a: AssetInfo) => boolean}>;
        /** Title for the assets no section claimed. Omit to leave them untitled. */
        restLabel?: string;
        /** Dropdown side. 'auto' flips it above the trigger when there is no room below. */
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        /** Minimum dropdown width in px, for triggers narrower than their content. */
        dropdownMinWidth?: number;
        /** Called when the asset cache fails to load, so the caller can say so in its own layout. */
        onLoadError?: () => void;
    }

    let {value = $bindable(null), disabled = false, filter, placeholder, testid = 'asset-select', compact = false, createLabel, onCreateNew, onchange, suggestedIds, sections, restLabel, dropdownPosition, dropdownMinWidth, onLoadError}: Props = $props();

    let loading = $state(true);

    onMount(async () => {
        try {
            await ensureAssetsLoaded();
        } catch {
            // Without this the rejection escaped and `loading` was never cleared, so a
            // failed cache load left the select spinning forever with no way to report it.
            onLoadError?.();
        } finally {
            loading = false;
        }
    });

    /** Build SearchSelect options from the asset store cache. */
    let options = $derived.by<SelectOption[]>(() => {
        // Subscribe to version counter so the list re-derives on cache mutation.
        void $assetStoreVersion;
        const all = getAllAssets();
        const filtered = filter ? all.filter(filter) : all;
        // Sort: active first, then by display_name.
        filtered.sort((a, b) => {
            if (a.active !== b.active) return a.active ? -1 : 1;
            return a.display_name.localeCompare(b.display_name);
        });
        const baseOptions = filtered.map<SelectOption>((a) => ({
            value: String(a.id),
            label: a.display_name,
            // P3/A6: `identifier_other` holds alternate codes (e.g. the non-tradeable
            // "CUM" ISIN of an Italian BTP). Omitting it made those codes unsearchable
            // even though they were stored on the asset.
            //
            // Currency and asset type are deliberately *not* here. They are properties
            // shared by hundreds of rows, so any query that is a prefix of one — `eur`,
            // `bon`, `etf` — matched the whole list, and the search looked as if it only
            // began working from the fourth letter. An identifier names an instrument;
            // a currency describes it.
            searchText: [a.identifier_isin, a.identifier_ticker, ...(a.identifier_other ?? [])].filter(Boolean).join(' '),
            // P3/A1: inactive assets stay selectable — imports are retroactive by nature,
            // and final coupons, redemptions and loyalty premiums land on matured
            // (hence deactivated) securities. Selecting one does NOT reactivate it.
            icon: a.icon_url || (a.asset_type ? getAssetTypeIconUrl(a.asset_type) : undefined),
            data: a,
        }));
        if (!suggestedIds || suggestedIds.length === 0) return sectioned(baseOptions);
        // Pin suggested items at the top with a badge.
        const suggestedSet = new Map(suggestedIds.map((s) => [String(s.id), s]));
        const suggested: SelectOption[] = [];
        const rest: SelectOption[] = [];
        for (const opt of baseOptions) {
            const hint = suggestedSet.get(opt.value);
            if (hint) {
                suggested.push({...opt, badge: hint.badge, badgeClass: hint.badgeClass, badgeTooltip: hint.badgeTooltip});
            } else {
                rest.push(opt);
            }
        }
        // Sections are structure, badges are decoration: when both are given the
        // sections decide the order and the badges simply travel with their option.
        return sections && sections.length > 0 ? sectioned([...suggested, ...rest]) : [...suggested, ...rest];
    });

    /**
     * Group options under section titles, preserving the order of `sections`.
     * Returns the input untouched when no sections are configured.
     */
    function sectioned(opts: SelectOption[]): SelectOption[] {
        if (!sections || sections.length === 0) return opts;
        const buckets = new Map<string, SelectOption[]>(sections.map((section) => [section.key, []]));
        const unclaimed: SelectOption[] = [];
        for (const opt of opts) {
            const asset = asAsset(opt.data);
            const section = asset ? sections.find((candidate) => candidate.match(asset)) : undefined;
            if (section) buckets.get(section.key)!.push(opt);
            else unclaimed.push(opt);
        }
        const out: SelectOption[] = [];
        for (const section of sections) {
            const members = buckets.get(section.key)!;
            if (members.length === 0) continue;
            out.push({value: `__section:${section.key}`, label: section.label, header: true});
            out.push(...members);
        }
        if (unclaimed.length > 0) {
            // Only title the remainder when something above it was titled, otherwise
            // the list would carry a single heading over the whole of itself.
            if (restLabel && out.length > 0) out.push({value: '__section:__rest', label: restLabel, header: true});
            out.push(...unclaimed);
        }
        return out;
    }

    let stringValue = $derived(value == null ? '' : String(value));

    function handleChange(v: string) {
        const next = v === '' ? null : Number(v);
        value = next;
        onchange?.(next);
    }

    function hideOnError(e: Event) {
        const img = e.currentTarget as HTMLImageElement | null;
        if (img) img.style.display = 'none';
    }

    /** Safe cast helper — avoids `as` in Svelte 5 templates. */
    function asAsset(data: unknown): AssetInfo | undefined {
        return data as AssetInfo | undefined;
    }
</script>

<!-- The test id lives on SearchSelect (via `testId` below), not here: carrying it on
     both would render two nested elements with the same `data-testid`, and every
     exact resolution of it fails Playwright's strict mode. This wrapper stays for
     layout only. -->
<div>
    <SearchSelect value={stringValue} {options} {disabled} {loading} placeholder={placeholder ?? $t('common.select')} {compact} inlineSearch={true} {dropdownPosition} {dropdownMinWidth} testId={testid} {createLabel} {onCreateNew} onchange={handleChange}>
        {#snippet selectedItem(option)}
            {@const a = asAsset(option.data)}
            <div class="flex items-center gap-2 min-w-0">
                {#if option.icon}
                    <span class="shrink-0 w-7 h-7 flex items-center justify-center bg-libre-green/10 dark:bg-libre-green/20 rounded overflow-hidden">
                        <img src={option.icon} alt="" class="w-5 h-5 object-contain" onerror={hideOnError} />
                    </span>
                {/if}
                <div class="min-w-0 flex-1">
                    <div class="font-medium text-gray-900 dark:text-gray-100 truncate text-sm flex items-center gap-1.5">
                        <span class="truncate">{a?.identifier_ticker || option.label}</span>
                        {#if a?.active === false}
                            <span data-testid="asset-select-selected-inactive-badge" class="shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-gray-400">
                                {$t('assets.edit.status.inactive')}
                            </span>
                        {/if}
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {option.label}{#if a?.currency}{@const ci = getCurrencyInfo(a.currency)} ·
                            <span class="inline-flex items-center gap-0.5"
                                >{#if ci.symbol && ci.symbol !== a.currency}<span>{ci.symbol}</span>{/if}{#if ci.flag_emoji}<span class="emoji-flag">{ci.flag_emoji}</span>{/if}<span>{a.currency}</span></span
                            >{/if}
                    </div>
                </div>
            </div>
        {/snippet}
        {#snippet item(option)}
            {@const a = asAsset(option.data)}
            <div class="flex items-center gap-2 min-w-0">
                {#if option.icon}
                    <img src={option.icon} alt="" class="w-4 h-4 rounded-sm object-contain shrink-0" onerror={hideOnError} />
                {/if}
                <span class="truncate text-sm {a?.active === false ? 'opacity-60' : ''}">{a?.identifier_ticker ? `${a.identifier_ticker} · ${option.label}` : option.label}</span>
                {#if a?.active === false}
                    <span data-testid="asset-select-inactive-badge" class="shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-gray-400">
                        {$t('assets.edit.status.inactive')}
                    </span>
                {/if}
                {#if option.badge}
                    {#if option.badgeTooltip}
                        <Tooltip text={option.badgeTooltip} position="left" maxWidth="220px">
                            <span class="shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium cursor-help {option.badgeClass || 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-300'}">
                                {option.badge}
                            </span>
                        </Tooltip>
                    {:else}
                        <span class="shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium {option.badgeClass || 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-300'}">
                            {option.badge}
                        </span>
                    {/if}
                {/if}
                {#if a?.currency}
                    {@const ci = getCurrencyInfo(a.currency)}
                    <span class="ml-auto text-[10px] font-mono opacity-60 shrink-0 inline-flex items-center gap-0.5">
                        {#if ci.symbol && ci.symbol !== a.currency}{ci.symbol}{/if}
                        {#if ci.flag_emoji}<span class="emoji-flag">{ci.flag_emoji}</span>{/if}
                        {a.currency}
                    </span>
                {/if}
            </div>
        {/snippet}
    </SearchSelect>
</div>
