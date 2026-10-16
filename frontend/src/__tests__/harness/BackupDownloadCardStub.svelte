<!--
  BackupDownloadCardStub — test-only stand-in for BackupDownloadCard (Vitest + jsdom).

  `InstanceBlockedPage.test.ts` asks where the block page puts the backup card, and whether it mounts it at all, not
  what the card does: that is `BackupDownloadCard.test.ts`. The real card would also resume at mount, through the backup
  API, a job this tab followed before. The stub renders one element with a testid of its own, and nothing else.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<div data-testid="backup-download-card-stub"></div>
