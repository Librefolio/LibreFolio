<!--
  A currency identifier in the project's form, `symbol flag code` (`€ 🇪🇺 EUR`), through the shared
  formatter: the flag keeps its emoji font, and it is drawn again once the currency catalogue loads.
-->
<script lang="ts">
    import {currentLanguage} from '$lib/stores/app/language';
    import {currencyStoreVersion, ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';
    import {formatCurrencyCodeHtml} from '$lib/utils/currency/currencyFormat';

    interface Props {
        code: string;
        testid?: string;
    }

    let {code, testid}: Props = $props();

    // Idempotent; until the catalogue arrives, or if it fails, the bare code is shown.
    $effect(() => {
        ensureCurrenciesLoaded($currentLanguage).catch(() => undefined);
    });

    const html = $derived.by(() => {
        void $currencyStoreVersion;
        return formatCurrencyCodeHtml(code);
    });
</script>

<span class="whitespace-nowrap" data-testid={testid} data-currency={code}>{@html sanitizeHtml(html)}</span>
