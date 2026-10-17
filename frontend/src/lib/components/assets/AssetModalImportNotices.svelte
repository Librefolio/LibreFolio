<!--
  AssetModalImportNotices — the broker-import advisories of the asset being created (AssetModal, wizard create
  context): one amber banner per kind, purely informational.
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import type {GroupedNotice} from './assetFormState';

    interface Props {
        /** Advisories grouped by kind (`groupImportNotices`). */
        groups: GroupedNotice[];
    }

    let {groups}: Props = $props();
</script>

<div class="space-y-2" data-testid="asset-import-notices">
    {#each groups as group (group.kind)}
        {@const _key = `assets.modal.importNotices.kind.${group.kind}`}
        {@const _label = $t(_key)}
        <div class="rounded-lg border border-lf-warning-line bg-lf-warning-soft px-3 py-2.5 space-y-1.5" data-testid="asset-import-notice">
            <div class="flex items-center gap-2 text-xs font-semibold text-lf-warning-on-soft">
                <span aria-hidden="true">⚠️</span>
                <span>{_label === _key ? $t('assets.modal.importNotices.kind.generic') : _label}</span>
            </div>
            <ul class="list-disc list-inside space-y-0.5 text-xs text-lf-warning-on-soft">
                {#each group.reasons as reason}
                    <li>{reason}</li>
                {/each}
            </ul>
            <p class="text-[11px] text-lf-warning-on-soft/80">{$t('assets.modal.importNotices.intro')}</p>
        </div>
    {/each}
</div>
