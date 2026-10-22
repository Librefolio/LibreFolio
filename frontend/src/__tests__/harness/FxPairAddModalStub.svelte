<!--
  FxPairAddModalStub — test-only stand-in for FxPairAddModal (Vitest + jsdom).

  `RiskPanelHeader.test.ts` asks which pair the panel opens the add-pair dialog on, and what the panel does once the dialog
  reports back, not what the dialog does: that is the dialog's own business. The real one would also load the currency
  graph and the provider routes through the API at mount. The stub keeps the props the panels pass — `open` (bindable),
  `initialBase`, `initialQuote`, `oncreated`, `onsynced`, `onclose` — and publishes what it was given as data attributes:
  `data-open`, `data-base` and `data-quote`. Its three buttons are the dialog's three ways of reporting back: created,
  synced, closed.

  It renders whether or not it is open, as the real dialog's own element does not decide whether a panel mounts it: a
  test reads `data-open`, and an absent stub reads as closed.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    import type {FxPairCreatedDetail, FxPairSyncCompleteDetail} from '$lib/services/fxCreationSync';

    interface Props {
        open?: boolean;
        initialBase?: string;
        initialQuote?: string;
        oncreated?: (detail: FxPairCreatedDetail) => void | Promise<void>;
        onsynced?: (detail: FxPairSyncCompleteDetail) => void | Promise<void>;
        onclose?: () => void;
    }

    let {open = $bindable(false), initialBase = '', initialQuote = '', oncreated, onsynced, onclose}: Props = $props();

    /** The smallest detail a creation reports: the pair as the dialog was opened on it. */
    function created(): FxPairCreatedDetail {
        return {base: initialBase, quote: initialQuote, hasRealProvider: true, slug: `${initialBase}-${initialQuote}`, autoSyncStarted: true};
    }

    function reportCreated(): void {
        void oncreated?.(created());
    }

    function reportSynced(): void {
        const detail = created();
        void onsynced?.({...detail, pairs: [detail.slug], start: '2026-01-01', end: '2026-06-30', sessionGeneration: 0, outcome: 'ok', results: [], missingPairs: []});
    }

    function close(): void {
        open = false;
        onclose?.();
    }
</script>

<div data-testid="fx-pair-add-modal-stub" data-open={open ? 'true' : 'false'} data-base={initialBase} data-quote={initialQuote}>
    <button type="button" aria-label="fx-pair-add-modal-stub-created" data-testid="fx-pair-add-modal-stub-created" onclick={reportCreated}></button>
    <button type="button" aria-label="fx-pair-add-modal-stub-synced" data-testid="fx-pair-add-modal-stub-synced" onclick={reportSynced}></button>
    <button type="button" aria-label="fx-pair-add-modal-stub-close" data-testid="fx-pair-add-modal-stub-close" onclick={close}></button>
</div>
