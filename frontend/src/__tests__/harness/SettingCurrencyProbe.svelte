<!--
  SettingCurrencyProbe — test-only stand-in for SettingCurrency.svelte (Vitest + jsdom).

  The real SettingCurrency embeds CurrencySearchSelect, which loads currencies and FX
  routes from the network on mount (`ensureCurrenciesLoaded`/`ensureFxRoutesLoaded`).
  That makes any component that renders SettingCurrency non-local unless every one of
  those data stores is mocked too — a lot of incidental setup for specs whose actual
  subject is the *caller* (WelcomeForm/WelcomePage), not currency search UX.

  This probe keeps only what those callers actually rely on: a bindable `value`, the
  `label`/`hint`/`isLocked` props, and a stable `testId` so a spec can locate and
  drive it exactly like it would the real control — via a plain text input rather
  than a searchable dropdown.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    interface Props {
        value?: string;
        label?: string;
        hint?: string;
        isLocked?: boolean;
        testId?: string;
        embedded?: boolean;
    }

    let {value = $bindable(''), label = '', hint = '', isLocked = false, testId = 'setting-currency-probe', embedded = false}: Props = $props();
</script>

<div data-testid={testId} data-embedded={embedded ? 'true' : 'false'} data-locked={isLocked ? 'true' : 'false'}>
    <label for={`${testId}-input`}>{label}</label>
    {#if hint}
        <p data-testid={`${testId}-hint`}>{hint}</p>
    {/if}
    <input id={`${testId}-input`} data-testid={`${testId}-input`} {value} disabled={isLocked} oninput={(event) => (value = (event.target as HTMLInputElement).value)} />
</div>
