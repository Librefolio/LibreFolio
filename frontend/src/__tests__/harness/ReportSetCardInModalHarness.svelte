<!--
  ReportSetCardInModalHarness — test-only host for a ReportSetCard inside the import wizard's modal (Vitest + jsdom).

  ImportWizardModal is one ModalBase (`maxWidth="6xl"`, `closeOnBackdropClick`, the default transitions) whose
  `onRequestClose` is `handleClose`: with work in progress, that opens the «discard the import?» confirmation.
  Step 2 renders a ReportSetCard for each report set inside it, and nothing between the two handles a key. The
  harness keeps that structure and nothing more:

    - ModalBase with the wizard's props, `onRequestClose` passed straight through, so a spec reads the request
      itself rather than a confirmation it would have to mount;
    - the real ReportSetCard, with every prop the spec hands it, as the wizard passes them.

  The modal's id is the harness's own (`report-set-escape-modal`); the card publishes its own.
  Lives under `src/__tests__/`, which `vitest.config.ts` excludes from coverage.
-->
<script lang="ts">
    import type {ComponentProps} from 'svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ReportSetCard from '$lib/components/transactions/import/ReportSetCard.svelte';

    interface Props {
        onRequestClose?: () => void;
        /** Every prop of the card. */
        card: ComponentProps<typeof ReportSetCard>;
    }

    let {onRequestClose = () => {}, card}: Props = $props();
</script>

<ModalBase open={true} maxWidth="6xl" {onRequestClose} testId="report-set-escape-modal" closeOnBackdropClick={true}>
    <ReportSetCard {...card} />
</ModalBase>
