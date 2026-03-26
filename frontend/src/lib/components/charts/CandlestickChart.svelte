<!-- CandlestickChart — STUB.
     TODO Phase 6 (Assets): Implement for OHLC data. Not applicable to daily FX close rates.
     OHLC candlestick chart for asset price history (yfinance, JustETF). -->
<script lang="ts">
    interface Props {
        height?: string;
    }

    let {height = '300px'}: Props = $props();
</script>
<div class="flex items-center justify-center bg-gray-50 dark:bg-slate-800 rounded-lg border border-dashed border-gray-300 dark:border-slate-600" style="height: {height};">
    <p class="text-gray-400 dark:text-slate-500 text-sm">CandlestickChart — Phase 6 (Assets)</p>
</div>
