<!--
  Settings › Administration › Backup (administrators only): the body of the tab.

  The backup card, the backups the instance keeps (lot FB-24), then the restore card (lot B5b).
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import BackupDownloadCard from './BackupDownloadCard.svelte';
    import BackupsSection from './BackupsSection.svelte';
    import RestoreCard from './RestoreCard.svelte';
</script>

<div class="space-y-6 text-lf-primary" data-testid="backup-tab">
    <p class="text-sm text-lf-secondary">{$_('backup.intro')}</p>
    <BackupDownloadCard />
    <BackupsSection />
    <RestoreCard />
</div>
