<!--
  ProfileChangesPanel — «Ultime variazioni», the last panel of the «Profilo» tab (plan 68, E6a; round 40: folded and
  closed). Opened, it reads one page of the asset's latest changes (`changes: {}`: a volatile voice only with the rows
  written by hand and the reading that replaces one) and shows them in `ProfileChangesTable`.

  - It reads only while open, and never the voices (`keys: []`); it publishes `data-open`, `data-status` and `data-busy`.
  - «Dimentica» sends back the `as_of` of the read that showed the rows: a row written after it is never forgotten by
    this page. Then it tells the tab (`onchanged`: the cards read again) and reads its page again; a page left empty
    falls back to the one before. A refusal of the server (`newer`, `not_found`) reads again too, and says so.
  - The source names are the enrichers' declared ones (`profileSources`).

  Pattern: Svelte 5 Runes, colour roles only.
-->
<script lang="ts">
    import {ChevronDown, ChevronRight} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import ProfileChangesTable from './ProfileChangesTable.svelte';
    import type {ProfileChange} from './profileChanges';
    import {loadEnricherNames} from './profileSources';
    import {forgetProfileRows, readAssetProfile, type ProfileVoice} from './profileStore';

    interface Props {
        assetId: number;
        /** The catalogue's voices, by key. */
        voices: Record<string, ProfileVoice>;
        /** Bumped by the tab when the profile changed elsewhere: an open panel reads again. */
        refreshKey?: number;
        /** «Dimentica» changed the profile: the tab reads its cards again. */
        onchanged?: () => void;
    }

    let {assetId, voices, refreshKey = 0, onchanged}: Props = $props();

    type Status = 'idle' | 'loading' | 'ready' | 'failed';
    let open = $state(false);
    let status = $state<Status>('idle');
    let page = $state(0);
    let rows = $state<ProfileChange[]>([]);
    let total = $state(0);
    /** The `as_of` of the read the table shows: «Dimentica» sends it back. */
    let asOf = $state('');
    let sourceNames = $state<Record<string, string>>({});
    /** Bumped to read the same page again (after a forget). */
    let again = $state(0);
    /** The read whose answer the panel still waits for: an older one that arrives later is dropped. */
    let latest = 0;

    function today(): string {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    }

    $effect(() => {
        if (!open) return;
        void loadEnricherNames().then((names) => (sourceNames = names));
    });

    $effect(() => {
        if (!open) return;
        const id = assetId;
        const asked = page;
        void refreshKey;
        void again;
        const mine = ++latest;
        status = 'loading';
        readAssetProfile(id, {start: today()}, {keys: [], changes: {page: asked}}).then(
            (read) => {
                if (mine !== latest) return;
                if (read.kind !== 'found') {
                    rows = [];
                    total = 0;
                    asOf = read.asOf;
                    status = 'ready';
                    return;
                }
                const changes = read.changes;
                // A forget emptied the last page: the page before (never below the first)
                if (changes && changes.items.length === 0 && asked > 0) {
                    page = asked - 1;
                    return;
                }
                rows = changes?.items ?? [];
                total = changes?.total ?? 0;
                asOf = read.asOf;
                status = 'ready';
            },
            () => {
                if (mine === latest) status = 'failed';
            },
        );
    });

    async function forget(ids: number[]): Promise<void> {
        try {
            const outcome = await forgetProfileRows(assetId, ids, asOf);
            if (outcome.kind === 'forgotten') {
                notify({name: 'asset.profile.changes.forgotten', detail: {asset_id: assetId, deleted: outcome.deleted}, toast: {variant: 'success', message: $t('assets.profile.changes.forgotten', {values: {count: outcome.deleted}})}});
            } else {
                notify({name: 'asset.profile.changes.refused', detail: {asset_id: assetId, reason: outcome.kind, update_ids: outcome.updateIds}, toast: {variant: 'warning', message: $t(outcome.kind === 'newer' ? 'assets.profile.changes.newer' : 'assets.profile.changes.notFound')}});
            }
        } catch {
            notify({name: 'asset.profile.changes.forgetFailed', detail: {asset_id: assetId}, toast: {variant: 'error', message: $t('assets.profile.changes.forgetFailed')}});
        }
        // Whatever the answer, the profile may have changed: the cards and this page read again
        onchanged?.();
        again += 1;
    }
</script>

<section class="rounded-xl border border-lf-subtle bg-lf-card shadow-sm shadow-lf-shadow-card" data-testid="profile-changes-panel" data-open={open ? 'true' : 'false'} data-status={status} data-busy={status === 'loading' ? 'true' : 'false'} aria-busy={status === 'loading'}>
    <button type="button" class="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-medium text-lf-primary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus" data-testid="profile-changes-toggle" aria-expanded={open} onclick={() => (open = !open)}>
        {#if open}<ChevronDown size={16} />{:else}<ChevronRight size={16} />{/if}
        {$t('assets.profile.changes.title')}
    </button>
    {#if open}
        <div class="border-t border-lf-subtle px-4 py-3">
            {#if status === 'failed'}
                <p class="text-sm text-lf-warning-on-soft" role="status" data-testid="profile-changes-failed">{$t('assets.profile.changes.loadFailed')}</p>
            {:else}
                <ProfileChangesTable {rows} {voices} {total} {page} {sourceNames} showVoice busy={status === 'loading'} storageKey="profileChangesPanel" onforget={forget} onpage={(next) => (page = next)} />
            {/if}
        </div>
    {/if}
</section>
