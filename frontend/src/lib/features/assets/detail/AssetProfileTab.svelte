<!--
  AssetProfileTab — the «Profilo» tab of the asset page (plan 68, E3+E4): the classification, the description, the key
  figures and the details of one asset, for the period chosen at the top of the page (I16).

  - It reads through the profile memory (`profileStore`): the catalogue once, the asset's profile per period. «Tutti» reads
    from the profile's first day (`start: 'min'`). A new period, or a new `refreshKey` (the page bumps it after anything
    that writes the profile, having called `invalidateAssetProfile`), reads again; an older answer that arrives late is
    dropped.
  - It publishes its loading (`data-busy`, `aria-busy`) and its outcome (`data-status`: loading, ready, failed, missing).
  - What goes where comes from the catalogue (`profileTabState`); the parts are `ProfileClassification`,
    `ProfileKeyFigureCard`, `ProfileDetails` and, last, «Ultime variazioni» (`ProfileChangesPanel`, E6a): a «Dimentica»
    there reads the tab again.
  - Seams: `onedit` («Modifica i dati»: the page opens `AssetProfileEditor`, the profile window in save mode, E9b2),
    `onhistory` (the history of a voice, E6: the clock of a card, a detail row, and since E6b2 the clocks beside the
    countries, the sectors and «Descrizione»). Without them, no button.
  - The asset's enrichers (E6c, `enrichers`: how many, and the last read). With some, «Aggiorna» beside «Modifica i dati»
    (`onrefresh`: the page reads them again and saves, I13; only the icon on a phone; its hint says the last read): it is
    busy (`data-state="running"`) until the page is done, and never on the next asset. With none, on top, the box
    «Nessun arricchitore configurato» and its «Configura» (`onconfigure`: the page opens the asset window with the
    enrichers' window on top). Not known yet (`null`): neither.

  Pattern: Svelte 5 Runes, Tailwind CSS 4, colour roles only.
-->
<script lang="ts">
    import {Layers, Pencil, RefreshCw} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {ensureCountriesLoaded, getCountryInfo} from '$lib/stores/reference/countryStore';
    import ProfileChangesPanel from '$lib/features/assets/profile/ProfileChangesPanel.svelte';
    import ProfileClassification from '$lib/features/assets/profile/ProfileClassification.svelte';
    import ProfileDetails from '$lib/features/assets/profile/ProfileDetails.svelte';
    import ProfileHistoryClock from '$lib/features/assets/profile/ProfileHistoryClock.svelte';
    import ProfileKeyFigureCard from '$lib/features/assets/profile/ProfileKeyFigureCard.svelte';
    import {loadProfileCatalogue, readAssetProfile, type ProfileVoice, type ProfileVoices} from '$lib/features/assets/profile/profileStore';
    import {detailGroups, formatProfileDay, formatProfileValue, keyFigureCards, periodLabel, profileCell, profileReadRange, staleSince, type PagePeriod, type ProfileCell, type ProfileFormatContext} from '$lib/features/assets/profile/profileTabState';

    interface Props {
        assetId: number;
        /** The period chosen at the top of the page. */
        period: PagePeriod;
        /** The asset's identifiers, shown with the identity. */
        isin: string | null;
        ticker: string | null;
        /** The asset's other identifiers (CUSIP, FIGI…), shown with the identity. */
        otherIdentifiers?: [string, string][];
        /** The free identifiers (type `OTHER`), shown as chips in one row. */
        softIdentifiers?: string[];
        /** Bumped by the page after anything that writes the profile: the tab reads again. */
        refreshKey?: number;
        /** «Modifica i dati» (E8); without it, no button. */
        onedit?: () => void;
        /** The history of a voice (E6); without it, no clock and no clickable row. */
        onhistory?: (key: string) => void;
        /** The asset's enrichers (E6c): how many are bound, and the day of the last read (`null`: never). `null`: not known yet. */
        enrichers?: {count: number; lastRead: string | null} | null;
        /** «Aggiorna» (E6c): the page reads the enrichers again; the button is busy until it resolves. */
        onrefresh?: () => Promise<unknown>;
        /** «Configura» of the box without enrichers (E6c). */
        onconfigure?: () => void;
    }

    let {assetId, period, isin, ticker, otherIdentifiers = [], softIdentifiers = [], refreshKey = 0, onedit, onhistory, enrichers = null, onrefresh, onconfigure}: Props = $props();

    /** The asset whose «Aggiorna» is running: the button is busy for that asset only, never for the next one. */
    let refreshingFor = $state<number | null>(null);
    const refreshing = $derived(refreshingFor !== null && refreshingFor === assetId);

    async function refresh(): Promise<void> {
        if (!onrefresh || refreshing) return;
        const id = assetId;
        refreshingFor = id;
        try {
            await onrefresh();
        } finally {
            if (refreshingFor === id) refreshingFor = null;
        }
    }

    type Status = 'loading' | 'ready' | 'failed' | 'missing';
    let status = $state<Status>('loading');
    let catalogue = $state<ProfileVoice[]>([]);
    let voices = $state<ProfileVoices>({});
    /** The read whose answer the tab still waits for: an older one that arrives later is dropped. */
    let latest = 0;
    /** Bumped after a «Dimentica» of the changes panel: the tab reads again (the memory is already forgotten). */
    let forgotten = $state(0);

    $effect(() => {
        const id = assetId;
        const range = profileReadRange({start: period.start, end: period.end, all: period.all});
        void refreshKey;
        void forgotten;
        const mine = ++latest;
        status = 'loading';
        Promise.all([loadProfileCatalogue(), readAssetProfile(id, range)]).then(
            ([loaded, read]) => {
                if (mine !== latest) return;
                catalogue = loaded;
                voices = read.kind === 'found' ? read.voices : {};
                status = read.kind === 'found' ? 'ready' : 'missing';
            },
            () => {
                if (mine === latest) status = 'failed';
            },
        );
    });

    /** Bumped when the countries' names arrive: the details write a country by its name. */
    let countriesVersion = $state(0);
    $effect(() => {
        void ensureCountriesLoaded($currentLanguage).then(() => (countriesVersion += 1));
    });

    const context: ProfileFormatContext = $derived.by(() => {
        void countriesVersion;
        const translate = $t;
        return {translate: (key: string) => translate(key), locale: uiLocale(), countryName: (iso3: string) => getCountryInfo(iso3).name};
    });

    const refreshHint = $derived(enrichers?.lastRead ? $t('assets.profile.refresh.hint', {values: {date: formatProfileDay(enrichers.lastRead, uiLocale())}}) : $t('assets.profile.refresh.hintNever'));

    const cards = $derived(keyFigureCards(catalogue, voices));
    const voicesByKey = $derived(Object.fromEntries(catalogue.map((voice) => [voice.key, voice])));
    const groups = $derived(detailGroups(catalogue, voices));
    const description = $derived.by((): ProfileCell | null => {
        const voice = catalogue.find((entry) => entry.key === 'description');
        return voice ? profileCell(voice, voices[voice.key]) : null;
    });
    /** The text of every cell with a value, by key. */
    const texts = $derived.by(() => {
        const result: Record<string, string> = {};
        for (const cell of [...cards, ...groups.flatMap((group) => group.cells)]) {
            if (cell.state !== 'value') continue;
            const text = formatProfileValue(cell.voice, cell.step?.value, context);
            // A fiscal year's figure names its year beside it (BI-PROF)
            const period = periodLabel(cell, (year) => $t('assets.profile.tab.fiscalYear', {values: {year}}));
            result[cell.key] = period && text ? `${text} (${period})` : text;
        }
        return result;
    });
    /** «Confermato il …, non aggiornato» of every stale cell, by key (D1d). */
    const staleTexts = $derived.by(() => {
        const result: Record<string, string> = {};
        for (const cell of [...cards, ...groups.flatMap((group) => group.cells)]) {
            const day = staleSince(cell);
            if (day) result[cell.key] = $t('assets.profile.tab.staleConfirmed', {values: {date: formatProfileDay(day, context.locale)}});
        }
        return result;
    });
</script>

<div class="flex flex-col gap-4 text-lf-primary" data-testid="asset-profile-tab" data-status={status} data-busy={status === 'loading' ? 'true' : 'false'} aria-busy={status === 'loading'}>
    {#if status === 'failed' || status === 'missing'}
        <div class="rounded-xl border border-lf-warning-line bg-lf-warning-soft p-4 text-sm text-lf-warning-on-soft" role="status" data-testid="asset-profile-message">
            {status === 'failed' ? $t('assets.profile.tab.loadFailed') : $t('assets.profile.tab.missing')}
        </div>
    {:else}
        {#if enrichers?.count === 0 && onconfigure}
            <section class="flex flex-col gap-3 rounded-xl border border-lf-subtle bg-lf-card p-4 shadow-sm shadow-lf-shadow-card sm:flex-row sm:items-center" data-testid="asset-profile-no-enrichers">
                <span class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-lf-panel text-lf-muted" aria-hidden="true"><Layers size={18} /></span>
                <div class="min-w-0 flex-1 text-sm">
                    <p class="font-semibold text-lf-primary">{$t('risk.assetDetail.profileNoEnrichers')}</p>
                    <p class="text-lf-secondary">{$t('assets.profile.tab.noEnrichersText')}</p>
                </div>
                <button
                    type="button"
                    class="inline-flex shrink-0 items-center justify-center gap-1.5 rounded-lg bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-lf-focus"
                    title={$t('assets.profile.tab.configureHint')}
                    data-testid="asset-profile-configure"
                    onclick={() => onconfigure?.()}
                >
                    <Layers size={14} />
                    {$t('assets.enrichers.configure')}
                </button>
            </section>
        {/if}
        <section class="rounded-xl border border-lf-subtle bg-lf-card p-4 shadow-sm shadow-lf-shadow-card">
            <ProfileClassification {voices} {onhistory} />
        </section>

        <section class="rounded-xl border border-lf-subtle bg-lf-card p-4 shadow-sm shadow-lf-shadow-card" data-testid="asset-profile-description" data-state={description?.state ?? 'unavailable'}>
            <div class="mb-2 flex items-start justify-between gap-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-lf-muted">{$t('assets.profile.voices.description')}</h3>
                {#if onhistory && description && description.state !== 'unavailable'}<ProfileHistoryClock voiceKey="description" testId="asset-profile-description-history" {onhistory} />{/if}
            </div>
            {#if description?.state === 'value'}
                <p class="whitespace-pre-wrap text-sm leading-relaxed text-lf-secondary">{String(description.step?.value ?? '')}</p>
            {:else}
                <p class="text-sm italic text-lf-muted">{$t('assets.profile.tab.notAvailable')}</p>
            {/if}
        </section>

        <section class="flex flex-col gap-3" data-testid="asset-profile-key-figures">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-lf-muted">{$t('assets.profile.tab.data')}</h3>
                <div class="flex items-center gap-2">
                    {#if onrefresh && enrichers && enrichers.count > 0}
                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 rounded-lg border border-lf-subtle bg-lf-card px-2.5 py-1 text-xs text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus disabled:cursor-wait disabled:opacity-60"
                            aria-label={`${$t('assets.profile.refresh.button')} · ${refreshHint}`}
                            title={refreshHint}
                            disabled={refreshing}
                            aria-busy={refreshing}
                            data-state={refreshing ? 'running' : 'idle'}
                            data-last-read={enrichers.lastRead ?? ''}
                            data-testid="asset-profile-refresh"
                            onclick={() => void refresh()}
                        >
                            <RefreshCw size={13} class={refreshing ? 'animate-spin' : ''} />
                            <span class="hidden sm:inline">{$t('assets.profile.refresh.button')}</span>
                        </button>
                    {/if}
                    {#if onedit}
                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 rounded-lg border border-lf-subtle bg-lf-card px-2.5 py-1 text-xs text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus"
                            data-testid="asset-profile-edit"
                            onclick={() => onedit?.()}
                        >
                            <Pencil size={13} />
                            {$t('assets.profile.tab.editData')}
                        </button>
                    {/if}
                </div>
            </div>
            <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {#each cards as card (card.key)}
                    <ProfileKeyFigureCard {card} text={texts[card.key] ?? ''} staleText={staleTexts[card.key]} {onhistory} />
                {/each}
            </div>
        </section>

        <section class="rounded-xl border border-lf-subtle bg-lf-card p-4 shadow-sm shadow-lf-shadow-card">
            <h3 class="mb-3 text-xs font-semibold uppercase tracking-wide text-lf-muted">{$t('assets.profile.tab.details')}</h3>
            <ProfileDetails {groups} {texts} {staleTexts} {isin} {ticker} {otherIdentifiers} {softIdentifiers} {onhistory} />
        </section>
    {/if}
    {#if status !== 'failed'}
        <ProfileChangesPanel {assetId} voices={voicesByKey} {refreshKey} onchanged={() => (forgotten += 1)} />
    {/if}
</div>
