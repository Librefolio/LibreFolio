<!--
  RestoreKeptModalStub — test-only stand-in for RestoreKeptModal (Vitest + jsdom).

  `BackupList.test.ts` asks whether «Restore» on a row opens the modal for that backup, and whether closing it removes it,
  not what the modal does: that is `RestoreKeptModal.test.ts`. The real modal would read the state of the restore through
  the backup API as it mounts. The stub shows the backup it was given and offers its `onClose`.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    interface Props {
        jobId: string;
        createdAt: string;
        onClose: () => void;
    }

    let {jobId, createdAt, onClose}: Props = $props();
</script>

<div data-testid="restore-kept-modal-stub" data-job-id={jobId} data-created-at={createdAt}>
    <button type="button" data-testid="restore-kept-modal-stub-close" onclick={onClose}>close</button>
</div>
