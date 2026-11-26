<!--
  ProfileHistoryModal — «Storia del dato» of one voice of the asset profile (plan 68, E6b; round 38, the mock's shots
  13 and 14). It opens from a key figure card's clock or a detail row of the «Profilo» tab.

  - On top, for a voice whose value is a number, the big chart of the voice from its first day (`start: 'min'`): the
    zoom left for later in round 24. A point per step, in its source's colour; under it the legend of the sources.
  - Under it, the same table as «Ultime variazioni» (`ProfileChangesTable`), with every row of this voice
    (`changes: {key}`), twenty a page, without the «Dato» column, and the same «Dimentica».
  - «Dimentica» sends back the `as_of` of the changes read, tells the page (`onchanged`: the tab reads again) and reads
    the window again. To write a new value, the footer points at «Modifica i dati».

  It publishes `data-voice`, `data-status` (`loading`, `ready`, `failed`) and `data-busy`.

  Pattern: Svelte 5 Runes, ModalBase, colour roles only.
-->
<script lang="ts">
    import {X} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import ProfileChangesTable from './ProfileChangesTable.svelte';
    import ProfileHistoryChart from './ProfileHistoryChart.svelte';
    import type {ProfileChange} from './profileChanges';
    import {forgetChanges} from './profileForget';
    import {historyCharted, historyPoints, type HistoryPoint} from './profileHistory';
    import {loadProfileSources, profileSourceName, type ProfileSource} from './profileSources';
    import {loadProfileCatalogue, profileVoice, readAssetProfile, type ProfileVoice} from './profileStore';
    import {formatProfileDay, formatProfileValue} from './profileTabState';

    interface Props {
        open?: boolean;
        assetId: number;
        assetName: string;
        /** The voice whose history the window shows; null: closed. */
        voiceKey: string | null;
        /** Bumped by the page when the profile changed elsewhere: an open window reads again. */
        refreshKey?: number;
        /** «Dimentica» changed the profile: the page reads its tab again. */
        onchanged?: () => void;
        onclose?: () => void;
        zIndex?: number;
    }

    let {open = $bindable(false), assetId, assetName, voiceKey, refreshKey = 0, onchanged, onclose, zIndex = 60}: Props = $props();

    type Status = 'loading' | 'ready' | 'failed';
    let status = $state<Status>('loading');
    let voices = $state<Record<string, ProfileVoice>>({});
    let points = $state<HistoryPoint[]>([]);
    let rows = $state<ProfileChange[]>([]);
    let total = $state(0);
    let page = $state(0);
    /** The `as_of` of the changes read: «Dimentica» sends it back. */
    let asOf = $state('');
    let sources = $state<Record<string, ProfileSource>>({});
    /** Bumped to read again (after a forget). */
    let again = $state(0);
    let latest = 0;

    const voice = $derived(voiceKey ? voices[voiceKey] : undefined);
    /** A text's two values need more room than a figure's (87, A3); the catalogue is in memory before the window opens. */
    const width = $derived(((voiceKey ? profileVoice(voiceKey) : undefined) ?? voice)?.shape === 'text' ? '6xl' : '4xl');
    const charted = $derived(voice ? historyCharted(voice) : false);

    function today(): string {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    }

    // A new voice opens on its first page
    $effect(() => {
        void voiceKey;
        page = 0;
    });

    $effect(() => {
        if (!open || !voiceKey) return;
        const id = assetId;
        const key = voiceKey;
        const asked = page;
        void refreshKey;
        void again;
        const mine = ++latest;
        status = 'loading';
        void loadProfileSources().then((known) => (sources = known));
        Promise.all([loadProfileCatalogue(), readAssetProfile(id, {start: 'min', end: today()}, {keys: [key]}), readAssetProfile(id, {start: today()}, {keys: [], changes: {key, page: asked}})]).then(
            ([catalogue, steps, changes]) => {
                if (mine !== latest) return;
                voices = Object.fromEntries(catalogue.map((entry) => [entry.key, entry]));
                const found = catalogue.find((entry) => entry.key === key);
                points = found && steps.kind === 'found' && historyCharted(found) ? historyPoints(found, steps.voices[key] ?? []) : [];
                const page_ = changes.kind === 'found' ? changes.changes : null;
                if (page_ && page_.items.length === 0 && asked > 0) {
                    page = asked - 1;
                    return;
                }
                rows = page_?.items ?? [];
                total = page_?.total ?? 0;
                asOf = changes.asOf;
                status = 'ready';
            },
            () => {
                if (mine === latest) status = 'failed';
            },
        );
    });

    function sourceName(code: string): string {
        if (code === 'user') return $t('assets.profile.history.byHand');
        return profileSourceName(code, (key) => $t(key), sources);
    }

    /** The sources the chart shows, once each, in the order they come: the legend. */
    const legend = $derived.by(() => {
        const seen = new Map<string, boolean>();
        for (const point of points) if (point.marked && point.value !== null && !seen.has(point.source)) seen.set(point.source, point.byHand);
        return [...seen.entries()].map(([source, byHand]) => ({source, byHand, name: sourceName(source)}));
    });

    /** A stored value as the profile writes it: an amount with its currency, a percentage as a percentage. */
    function formatValue(stored: unknown): string {
        if (!voice) return String(stored ?? '');
        return formatProfileValue(voice, stored, {translate: (key) => $t(key), locale: uiLocale(), countryName: (iso3) => iso3});
    }

    async function forget(ids: number[]): Promise<void> {
        await forgetChanges(assetId, ids, asOf, (key, values) => $t(key, {values}));
        onchanged?.();
        again += 1;
    }

    function close(): void {
        open = false;
        onclose?.();
    }
</script>

<ModalBase {open} maxWidth={width} onRequestClose={close} {zIndex} testId="profile-history-modal" labelledBy="profile-history-title">
    <div class="flex max-h-[90vh] flex-col text-lf-primary" data-testid="profile-history" data-voice={voiceKey ?? ''} data-status={status} data-busy={status === 'loading' ? 'true' : 'false'} aria-busy={status === 'loading'}>
        <header class="flex items-center justify-between gap-3 border-b border-lf-subtle px-4 py-4 sm:px-6">
            <h2 id="profile-history-title" class="min-w-0 truncate text-lg font-semibold text-lf-primary">
                {voiceKey ? $t(`assets.profile.voices.${voiceKey}`) : ''}
                <span class="text-sm font-normal text-lf-muted">· {assetName}</span>
            </h2>
            <button type="button" class="rounded p-1 text-lf-muted hover:bg-lf-hover hover:text-lf-primary focus-visible:outline-2 focus-visible:outline-lf-focus" aria-label={$t('common.close')} data-testid="profile-history-x" onclick={close}>
                <X size={18} />
            </button>
        </header>

        <div class="flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-6">
            {#if status === 'failed'}
                <p class="text-sm text-lf-warning-on-soft" role="status" data-testid="profile-history-failed">{$t('assets.profile.history.loadFailed')}</p>
            {:else}
                {#if charted && points.length}
                    <section class="rounded-xl border border-lf-subtle bg-lf-card p-3">
                        <ProfileHistoryChart {points} {formatValue} formatDay={(iso) => formatProfileDay(iso, uiLocale())} {sourceName} />
                        <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-lf-muted" data-testid="profile-history-legend">
                            {#each legend as entry (entry.source)}
                                <span class="inline-flex items-center gap-1" data-source={entry.source}>
                                    <span class="inline-block h-2 w-2 rounded-full {entry.byHand ? 'bg-lf-info' : 'bg-lf-focus'}" aria-hidden="true"></span>
                                    {entry.name}
                                </span>
                            {/each}
                            {#if voice?.shape === 'percentage'}<span>{$t('assets.profile.history.valuesInPercent')}</span>{/if}
                        </div>
                    </section>
                {/if}
                <ProfileChangesTable {rows} {voices} {total} {page} {sources} busy={status === 'loading'} storageKey="profileHistoryModal" onforget={forget} onpage={(next) => (page = next)} />
            {/if}
        </div>

        <footer class="flex flex-wrap items-center justify-between gap-2 border-t border-lf-subtle bg-lf-panel px-4 py-3 sm:px-6">
            <span class="text-xs text-lf-muted">{$t('assets.profile.history.writeHint', {values: {action: $t('assets.profile.tab.editData')}})}</span>
            <button type="button" class="ml-auto rounded-lg border border-lf-subtle bg-lf-card px-4 py-2 text-sm font-medium text-lf-secondary hover:bg-lf-hover" data-testid="profile-history-close" onclick={close}>
                {$t('common.close')}
            </button>
        </footer>
    </div>
</ModalBase>
