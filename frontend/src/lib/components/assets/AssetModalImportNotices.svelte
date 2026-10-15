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
        <div class="rounded-lg border border-amber-300 dark:border-amber-700/60 bg-amber-50 dark:bg-amber-900/20 px-3 py-2.5 space-y-1.5" data-testid="asset-import-notice">
            <div class="flex items-center gap-2 text-xs font-semibold text-amber-800 dark:text-amber-300">
                <span aria-hidden="true">⚠️</span>
                <span>{_label === _key ? $t('assets.modal.importNotices.kind.generic') : _label}</span>
            </div>
            <ul class="list-disc list-inside space-y-0.5 text-xs text-amber-700 dark:text-amber-200/90">
                {#each group.reasons as reason}
                    <li>{reason}</li>
                {/each}
            </ul>
            <p class="text-[11px] text-amber-600 dark:text-amber-300/70">{$t('assets.modal.importNotices.intro')}</p>
        </div>
    {/each}
</div>
