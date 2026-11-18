<!--
  AssetProfileTab — the «Profilo» tab of the asset page (plan 68, E3+E4): the classification, the description, the key
  figures and the details of one asset, for the period chosen at the top of the page (I16).

  - It reads through the profile memory (`profileStore`): the catalogue once, the asset's profile per period. «Tutti» reads
    from the profile's first day (`start: 'min'`). A new period, or a new `refreshKey` (the page bumps it after anything
    that writes the profile, having called `invalidateAssetProfile`), reads again; an older answer that arrives late is
    dropped.
  - It publishes its loading (`data-busy`, `aria-busy`) and its outcome (`data-status`: loading, ready, failed, missing).
  - What goes where comes from the catalogue (`profileTabState`); the parts are `ProfileClassification`,
    `ProfileKeyFigureCard` and `ProfileDetails`.
  - Seams for the lots after it: `onedit` («Modifica i dati», E8), `onhistory` (the history of a voice, E6). Without
    them, no button.

  Not mounted by the page yet: the page's wiring comes with lane 70 in dev (coordinator, 17/11/2026).

  Pattern: Svelte 5 Runes, Tailwind CSS 4, colour roles only.
-->
<script lang="ts">
    import {Pencil} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {ensureCountriesLoaded, getCountryInfo} from '$lib/stores/reference/countryStore';
    import ProfileClassification from '$lib/features/assets/profile/ProfileClassification.svelte';
    import ProfileDetails from '$lib/features/assets/profile/ProfileDetails.svelte';
    import ProfileKeyFigureCard from '$lib/features/assets/profile/ProfileKeyFigureCard.svelte';
    import {loadProfileCatalogue, readAssetProfile, type ProfileVoice, type ProfileVoices} from '$lib/features/assets/profile/profileStore';
    import {detailGroups, formatProfileValue, keyFigureCards, profileCell, profileReadRange, type PagePeriod, type ProfileCell, type ProfileFormatContext} from '$lib/features/assets/profile/profileTabState';

    interface Props {
        assetId: number;
        /** The period chosen at the top of the page. */
        period: PagePeriod;
        /** The asset's identifiers, shown with the identity. */
        isin: string | null;
        ticker: string | null;
        /** The asset's other identifiers (CUSIP, FIGI…), shown with the identity. */
        otherIdentifiers?: [string, string][];
        /** Bumped by the page after anything that writes the profile: the tab reads again. */
        refreshKey?: number;
        /** «Modifica i dati» (E8); without it, no button. */
        onedit?: () => void;
        /** The history of a voice (E6); without it, no clock and no clickable row. */
        onhistory?: (key: string) => void;
    }

    let {assetId, period, isin, ticker, otherIdentifiers = [], refreshKey = 0, onedit, onhistory}: Props = $props();

    type Status = 'loading' | 'ready' | 'failed' | 'missing';
    let status = $state<Status>('loading');
    let catalogue = $state<ProfileVoice[]>([]);
    let voices = $state<ProfileVoices>({});
    /** The read whose answer the tab still waits for: an older one that arrives later is dropped. */
    let latest = 0;

    $effect(() => {
        const id = assetId;
        const range = profileReadRange({start: period.start, end: period.end, all: period.all});
        void refreshKey;
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

    const cards = $derived(keyFigureCards(catalogue, voices));
    const groups = $derived(detailGroups(catalogue, voices));
    const description = $derived.by((): ProfileCell | null => {
        const voice = catalogue.find((entry) => entry.key === 'description');
        return voice ? profileCell(voice, voices[voice.key]) : null;
    });
    /** The text of every cell with a value, by key. */
    const texts = $derived.by(() => {
        const result: Record<string, string> = {};
        for (const cell of [...cards, ...groups.flatMap((group) => group.cells)]) {
            if (cell.state === 'value') result[cell.key] = formatProfileValue(cell.voice, cell.step?.value, context);
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
        <section class="rounded-xl border border-lf-subtle bg-lf-card p-4 shadow-sm shadow-lf-shadow-card">
            <ProfileClassification {voices} />
        </section>

        <section class="rounded-xl border border-lf-subtle bg-lf-card p-4 shadow-sm shadow-lf-shadow-card" data-testid="asset-profile-description" data-state={description?.state ?? 'unavailable'}>
            <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-lf-muted">{$t('assets.profile.voices.description')}</h3>
            {#if description?.state === 'value'}
                <p class="whitespace-pre-wrap text-sm leading-relaxed text-lf-secondary">{String(description.step?.value ?? '')}</p>
            {:else}
                <p class="text-sm italic text-lf-muted">{$t('assets.profile.tab.notAvailable')}</p>
            {/if}
        </section>

        <section class="flex flex-col gap-3" data-testid="asset-profile-key-figures">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-lf-muted">{$t('assets.profile.tab.data')}</h3>
                {#if onedit}
                    <button type="button" class="inline-flex items-center gap-1.5 rounded-lg border border-lf-subtle bg-lf-card px-2.5 py-1 text-xs text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus" data-testid="asset-profile-edit" onclick={() => onedit?.()}>
                        <Pencil size={13} />
                        {$t('assets.profile.tab.editData')}
                    </button>
                {/if}
            </div>
            <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {#each cards as card (card.key)}
                    <ProfileKeyFigureCard {card} text={texts[card.key] ?? ''} {onhistory} />
                {/each}
            </div>
        </section>

        <section class="rounded-xl border border-lf-subtle bg-lf-card p-4 shadow-sm shadow-lf-shadow-card">
            <h3 class="mb-3 text-xs font-semibold uppercase tracking-wide text-lf-muted">{$t('assets.profile.tab.details')}</h3>
            <ProfileDetails {groups} {texts} {isin} {ticker} {otherIdentifiers} {onhistory} />
        </section>
    {/if}
</div>
