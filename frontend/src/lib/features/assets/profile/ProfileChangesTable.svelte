<!--
  ProfileChangesTable — the one table of the changes of the asset profile (plan 68, E6a; round 38): the «Ultime
  variazioni» panel shows the latest changes of every voice, the «Storia del dato» window every row of one voice. The
  table never reads: its host owns the read, the page and the `as_of` «Dimentica» sends back.

  - Columns: «Quando» (the day of the row), «Dato» (`showVoice`, the panel only), «Cosa è cambiato» (`profileChanges`,
    its kind on `data-kind`), «Chi» (the author of a value written by hand, or the source).
  - «Dimentica» of one row (its menu) and of the rows chosen asks first: the change leaves the history and does not come
    back. On confirm, `onforget(ids)`. The rows chosen are the table's selection panel (77 SEL-D): the bar at the top,
    «Dimentica» with the number of rows it takes, the dock when the top leaves the view.
  - The server pages by twenty: the pager is the table's balloon (`DataTablePagination` on the server's total, under the
    actions in the dock), its range on `profile-changes-pager` (`data-from`, `data-to`, `data-total`); it asks the host
    for another page (`onpage`).

  Pattern: Svelte 5 Runes, DataTable, colour roles only.
-->
<script lang="ts">
    import {Trash2} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {currentLanguage} from '$lib/stores/app/language';
    import {ensureCountriesLoaded, getCountryInfo} from '$lib/stores/reference/countryStore';
    import {type BulkAction, type ColumnDef, ConfirmModal, DataTable, type RowAction} from '$lib/components/table';
    import DataTablePagination from '$lib/components/table/DataTablePagination.svelte';
    import ProfileChangeWhat from './ProfileChangeWhat.svelte';
    import ProfileChangeWho from './ProfileChangeWho.svelte';
    import {changeSentence, text, type ProfileChange} from './profileChanges';
    import {profileSourceName} from './profileSources';
    import type {ProfileVoice} from './profileStore';
    import {formatProfileDay, formatProfileValue, type ProfileFormatContext} from './profileTabState';

    /** The server's page of changes (`CHANGES_PAGE_SIZE`). */
    const PAGE_SIZE = 20;

    interface Props {
        rows: ProfileChange[];
        /** The catalogue's voices, by key. */
        voices: Record<string, ProfileVoice>;
        /** How many changes there are in all, and the page shown (0 first). */
        total: number;
        page: number;
        /** The enrichers' declared names, by code. */
        sourceNames?: Record<string, string>;
        /** The «Dato» column: the panel shows it, the window of one voice does not. */
        showVoice?: boolean;
        /** A read of the host is under way. */
        busy?: boolean;
        /** The table's own preferences (column widths): one key per host. */
        storageKey: string;
        onforget: (ids: number[]) => Promise<void>;
        onpage: (page: number) => void;
    }

    let {rows, voices, total, page, sourceNames = {}, showVoice = false, busy = false, storageKey, onforget, onpage}: Props = $props();

    /** Bumped when the countries' names arrive: a map's sentence names its countries. */
    let countriesVersion = $state(0);
    $effect(() => {
        void ensureCountriesLoaded($currentLanguage).then(() => (countriesVersion += 1));
    });

    const context: ProfileFormatContext = $derived.by(() => {
        void countriesVersion;
        const translate = $t;
        return {translate: (key: string) => translate(key), locale: uiLocale(), countryName: (iso3: string) => getCountryInfo(iso3).name};
    });

    function sourceName(code: string): string {
        return profileSourceName(code, (key) => $t(key), sourceNames);
    }

    function sentence(change: ProfileChange) {
        const format = context;
        return changeSentence(change, voices[change.key], {
            translate: (key, values) => $t(key, {values}),
            format: (voice, value) => formatProfileValue(voice, value, format),
            day: (iso) => formatProfileDay(iso, format.locale),
            source: sourceName,
        });
    }

    function author(change: ProfileChange): string {
        // The sentence says «before the profile»; the «Chi» cell says who: the system (81 U26a).
        if (change.source === 'legacy') return $t('assets.profile.changes.who.system');
        if (change.source !== 'user') return sourceName(change.source);
        return text(change.user_name) ?? $t('assets.profile.changes.who.deletedUser');
    }

    /** A phone (below 640 px): one column, the sentence over the day, the voice and who wrote it (the mock's shot 14). */
    let compact = $state(false);
    $effect(() => {
        if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
        const query = window.matchMedia('(max-width: 639px)');
        compact = query.matches;
        const follow = (event: MediaQueryListEvent) => (compact = event.matches);
        query.addEventListener('change', follow);
        return () => query.removeEventListener('change', follow);
    });

    function whatCell(row: ProfileChange) {
        const detail = compact ? {when: formatProfileDay(row.read_on, context.locale), voice: showVoice ? $t(`assets.profile.voices.${row.key}`) : undefined, source: row.source, name: author(row), avatarUrl: text(row.user_avatar_url)} : null;
        return {type: 'custom' as const, component: ProfileChangeWhat, props: {...sentence(row), changeId: row.id, compact: detail}};
    }

    const columns: ColumnDef<ProfileChange>[] = $derived.by(() => {
        const what: ColumnDef<ProfileChange> = {id: 'what', header: () => $t('assets.profile.changes.columns.what'), type: 'text', sortable: false, filterable: false, minWidth: 220, cell: whatCell};
        if (compact) return [what];
        const list: ColumnDef<ProfileChange>[] = [{id: 'when', header: () => $t('assets.profile.changes.columns.when'), type: 'text', sortable: false, filterable: false, width: 110, cell: (row) => formatProfileDay(row.read_on, context.locale)}];
        if (showVoice) {
            list.push({id: 'voice', header: () => $t('assets.profile.changes.columns.voice'), type: 'text', sortable: false, filterable: false, width: 150, cell: (row) => $t(`assets.profile.voices.${row.key}`)});
        }
        list.push(what, {
            id: 'who',
            header: () => $t('assets.profile.changes.columns.who'),
            type: 'text',
            sortable: false,
            filterable: false,
            width: 160,
            cell: (row) => ({type: 'custom', component: ProfileChangeWho, props: {changeId: row.id, source: row.source, name: author(row), avatarUrl: text(row.user_avatar_url)}}),
        });
        return list;
    });

    /** The ids the confirmation is asking about; null when it is closed. */
    let asking = $state<number[] | null>(null);
    let forgetting = $state(false);
    /** Bumped after a forget: the table is drawn again, its selection empty. */
    let drawn = $state(0);

    const rowActions: RowAction<ProfileChange>[] = $derived([
        {
            id: 'forget',
            icon: Trash2,
            label: () => $t('assets.profile.changes.forget'),
            variant: 'danger',
            testid: (row: ProfileChange) => `profile-change-forget-${row.id}`,
            onClick: (row: ProfileChange) => {
                asking = [row.id];
            },
        },
    ]);
    /** The selection panel's action: «Dimentica» on the rows chosen, with their number (77 SEL-D). */
    const bulkActions: BulkAction<ProfileChange>[] = [
        {
            id: 'forget',
            icon: Trash2,
            variant: 'danger',
            label: () => $t('assets.profile.changes.forget'),
            onClick: (chosen) => {
                asking = chosen.map((row) => row.id);
            },
        },
    ];

    // Another page: the rows chosen on this one are dropped, so «Dimentica» never reaches rows no longer shown
    let shownPage = -1;
    $effect(() => {
        const current = page;
        if (shownPage !== -1 && current !== shownPage) drawn += 1;
        shownPage = current;
    });

    async function confirm(): Promise<void> {
        const ids = asking ?? [];
        asking = null;
        if (!ids.length) return;
        forgetting = true;
        try {
            await onforget(ids);
        } finally {
            forgetting = false;
            drawn += 1;
        }
    }

    const from = $derived(total === 0 ? 0 : page * PAGE_SIZE + 1);
    const to = $derived(Math.min(total, page * PAGE_SIZE + rows.length));
    const last = $derived(Math.max(0, Math.ceil(total / PAGE_SIZE) - 1));
</script>

<div class="flex flex-col gap-2 text-lf-primary" data-testid="profile-changes-table" data-busy={busy || forgetting ? 'true' : 'false'} aria-busy={busy || forgetting}>
    {#snippet pager(docked: boolean)}
        <!-- The table's balloon on the server's pages; its range on stable handles. -->
        <div class="contents" data-testid="profile-changes-pager" data-from={from} data-to={to} data-total={total} data-page={page}>
            <DataTablePagination pageIndex={page} pageSize={PAGE_SIZE} totalItems={total} pageSizeOptions={[PAGE_SIZE]} {docked} onPageChange={(next) => !busy && onpage(next)} onPageSizeChange={() => {}} />
        </div>
    {/snippet}
    {#key drawn}
        <DataTable
            data={rows}
            {columns}
            getRowId={(row) => String(row.id)}
            {storageKey}
            selectionMode="multi"
            {rowActions}
            {bulkActions}
            selectionPanel={true}
            pager={total > 0 ? pager : undefined}
            enableSorting={false}
            enableColumnFilters={false}
            enableColumnVisibility={false}
            enablePagination={false}
            isLoading={busy}
            emptyMessage={$t('assets.profile.changes.empty')}
        />
    {/key}
</div>

<ConfirmModal
    open={asking !== null}
    title={$t('assets.profile.changes.confirmTitle')}
    message={$t('assets.profile.changes.confirmMessage', {values: {count: asking?.length ?? 0}})}
    confirmText={$t('assets.profile.changes.forgetSelected', {values: {count: asking?.length ?? 0}})}
    danger
    testId="profile-changes-confirm"
    onConfirm={confirm}
    onCancel={() => (asking = null)}
/>
