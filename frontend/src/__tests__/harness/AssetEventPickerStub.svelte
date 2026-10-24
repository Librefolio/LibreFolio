<!--
  AssetEventPickerStub — test-only stand-in for AssetEventPicker (Vitest + jsdom).

  The real picker fetches the asset's events through the API and draws a fixed-position dropdown whose
  geometry jsdom cannot give it. What a caller needs to prove is the picker's CONTRACT with its host: the props it
  is handed (`assetId`, `txDate`, `value`) and the answer it gives (`onChange(eventId | null)`). The stub publishes
  the props as data attributes and answers with two buttons: one picks the event `PICKED_EVENT_ID`, one clears.

  Lives under `src/__tests__/`, excluded from coverage by `vitest.config.ts`.
-->
<script lang="ts">
    interface Props {
        assetId: number;
        txDate: string;
        value: number | null;
        disabled?: boolean;
        onChange: (eventId: number | null) => void;
    }

    let {assetId, txDate, value, disabled = false, onChange}: Props = $props();

    /** The event the "pick" button answers with: a host test expects to see this id come back. */
    const PICKED_EVENT_ID = 555;
</script>

<div data-testid="event-picker-stub" data-asset-id={assetId} data-tx-date={txDate} data-value={value === null ? '' : value} data-disabled={disabled}>
    <button type="button" data-testid="event-picker-stub-pick" onclick={() => onChange(PICKED_EVENT_ID)}>pick</button>
    <button type="button" data-testid="event-picker-stub-clear" onclick={() => onChange(null)}>clear</button>
</div>
