<!--
  BackupListStub — test-only stand-in for BackupList (Vitest + jsdom).

  `InstanceBlockedPage.test.ts` asks where the block page puts the list of the kept backups and whether it turns the
  restore off, not what the list does: that is `BackupList.test.ts`. The real list would read the backup API at mount.
  The stub renders one element with a testid of its own, carrying the `allowRestore` it was given.
-->
<script lang="ts">
    let {allowRestore = true}: {allowRestore?: boolean} = $props();
</script>

<div data-testid="backup-list-stub" data-allow-restore={String(allowRestore)}></div>
