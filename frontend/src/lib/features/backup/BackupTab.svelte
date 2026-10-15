<!--
  Settings › Backup (administrators only): the body of the tab.

  Today the backup card alone; the restore card joins it with the restore flow.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import BackupDownloadCard from './BackupDownloadCard.svelte';
</script>

<div class="space-y-6 text-lf-primary" data-testid="backup-tab">
    <p class="text-sm text-lf-secondary">{$_('backup.intro')}</p>
    <BackupDownloadCard />
</div>
