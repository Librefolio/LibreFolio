<!--
  FileSetBadges.svelte — the report-set badges of one BRIM file in FilesTable (the files page and the
  broker's import files): combined · stale · usedInCombined · set · incomplete (design §5).

  The badges are computed by `fileSetBadges` (importReportSets.ts); this component only shows them.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {formatIsoDay, type FileSetBadge} from '$lib/utils/transactions/importReportSets';

    interface Props {
        badges: FileSetBadge[];
    }

    let {badges}: Props = $props();

    const STYLE: Record<FileSetBadge['kind'], string> = {
        combined: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200',
        stale: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200',
        usedInCombined: 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-gray-200',
        set: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200',
        incomplete: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
    };

    function roleName(role: string): string {
        const key = `importWizard.reportSet.roleName.${role}`;
        const translated = $t(key);
        return translated === key ? role : translated;
    }

    function label(badge: FileSetBadge): string {
        switch (badge.kind) {
            case 'combined':
                return $t('importWizard.reportSet.badge.combined');
            case 'stale':
                return $t('importWizard.reportSet.badge.stale');
            case 'usedInCombined':
                return $t('importWizard.reportSet.badge.usedInCombined');
            case 'set':
                return $t('importWizard.reportSet.badge.set', {values: {date: formatIsoDay(badge.uploadedAt)}});
            case 'incomplete':
                return $t('importWizard.reportSet.badge.incomplete');
        }
    }

    function tooltip(badge: FileSetBadge): string {
        switch (badge.kind) {
            case 'combined': {
                const built = $t('importWizard.reportSet.badge.combinedTooltip', {values: {names: (badge.names ?? []).join(', ')}});
                if (!badge.deleted || badge.deleted.length === 0) return built;
                return `${built} · ${$t('importWizard.reportSet.badge.combinedDeleted', {values: {names: badge.deleted.join(', ')}})}`;
            }
            case 'stale':
                return $t('importWizard.reportSet.badge.staleTooltip');
            case 'usedInCombined':
                return $t('importWizard.reportSet.badge.usedInCombinedTooltip');
            case 'set':
                return $t('importWizard.reportSet.badge.setTooltip');
            case 'incomplete':
                return $t('importWizard.reportSet.badge.incompleteTooltip', {values: {roles: (badge.roles ?? []).map(roleName).join(', ')}});
        }
    }
</script>

<span class="flex flex-wrap gap-1">
    {#each badges as badge (badge.kind)}
        <span class="whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium {STYLE[badge.kind]}" title={tooltip(badge)} data-testid="file-set-badge" data-kind={badge.kind}>{label(badge)}</span>
    {/each}
</span>
