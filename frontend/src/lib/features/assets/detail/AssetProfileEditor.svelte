<!--
  AssetProfileEditor — «Modifica i dati» of the «Profilo» tab (plan 68, E9b2): the profile window in `save` mode over the
  asset page.

  Closed, it reads nothing. Opened, it reads what the window needs — the catalogue, the profile of today («Adesso») and
  the enrichers' names (the window names a source by them) — then mounts the window. «Salva Tutto» writes the profile
  alone (`PATCH /assets`); once it is done the asset's profile memory is forgotten, the window closes and the page is
  told (`onsaved`: it reads the tab again). A read that fails closes the window with the tab's own message.

  Pattern: Svelte 5 Runes.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {zodiosApi} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {todayIso} from '$lib/utils/dateOnly';
    import ProfileEditModal from '$lib/features/assets/profile/ProfileEditModal.svelte';
    import {invalidateAssetProfile, loadProfileCatalogue, readAssetProfile, type ProfileVoice} from '$lib/features/assets/profile/profileStore';
    import {currentFromRead} from '$lib/features/assets/profile/assetProfileDraft';
    import type {CurrentVoice} from '$lib/features/assets/profile/profileEditState';

    interface Props {
        open?: boolean;
        assetId: number;
        /** The asset's name, in the window's title. */
        assetName: string;
        zIndex?: number;
        /** The profile was saved: the page reads the tab again. */
        onsaved?: () => void;
    }

    let {open = $bindable(false), assetId, assetName, zIndex = 60, onsaved}: Props = $props();

    let catalogue = $state<ProfileVoice[]>([]);
    let current = $state<Record<string, CurrentVoice>>({});
    let sourceNames = $state<Record<string, string>>({});
    /** The opening whose reads are in: the window mounts only then. An older opening that answers late is dropped. */
    let ready = $state(false);
    let opening = 0;

    $effect(() => {
        if (!open) {
            ready = false;
            return;
        }
        const id = assetId;
        untrack(() => {
            const mine = ++opening;
            ready = false;
            Promise.all([loadProfileCatalogue(), readAssetProfile(id, {start: todayIso()}), zodiosApi.list_enrichers_api_v1_assets_enrichers_get()]).then(
                ([voices, read, enrichers]) => {
                    if (mine !== opening || !open) return;
                    catalogue = voices ?? [];
                    current = read.kind === 'found' ? currentFromRead(read.voices) : {};
                    sourceNames = Object.fromEntries(((enrichers as {enrichers?: Array<{code: string; name: string}>} | undefined)?.enrichers ?? []).map((info) => [info.code, info.name]));
                    ready = true;
                },
                () => {
                    if (mine !== opening) return;
                    open = false;
                    toasts.error($t('assets.profile.tab.loadFailed'));
                },
            );
        });
    });

    function saved(): void {
        invalidateAssetProfile(assetId);
        open = false;
        onsaved?.();
    }
</script>

{#if open && ready}
    <ProfileEditModal bind:open {assetName} mode="save" {assetId} {catalogue} {current} {sourceNames} {zIndex} onsaved={saved} oncancel={() => (open = false)} />
{/if}
