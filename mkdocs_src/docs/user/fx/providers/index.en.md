# 🔌 FX Providers

LibreFolio downloads exchange rates from central banks — free, and without an API key. A currency
pair can have several sources in priority order: if the first one fails during a sync, the next
one takes over.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ecb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.ecb.europa.eu/favicon-32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="ECB favicon">
            <span class="card-title" style="margin: 0;">European Central Bank (ECB)</span>
        </div>
        <span class="card-desc">Daily reference exchange rates from the ECB, base currency EUR.</span>
    </a>
    <a href="fed/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://fred.stlouisfed.org/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="FED favicon">
            <span class="card-title" style="margin: 0;">Federal Reserve (FED)</span>
        </div>
        <span class="card-desc">FRED database exchange rates, base currency USD.</span>
    </a>
    <a href="boe/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="BOE favicon">
            <span class="card-title" style="margin: 0;">Bank of England (BOE)</span>
        </div>
        <span class="card-desc">Daily reference rates from the BOE, base currency GBP.</span>
    </a>
    <a href="snb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://data.snb.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="SNB favicon">
            <span class="card-title" style="margin: 0;">Swiss National Bank (SNB)</span>
        </div>
        <span class="card-desc">Stable monthly average Swiss Franc rates from the SNB, base currency CHF.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
     <div style="display: flex; align-items: center; gap: 0.75rem;">
     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
     <span class="card-title" style="margin: 0;">Request New Plugin</span>
     </div>
     <span class="card-desc">Your exchange rate source is missing? Request a new plugin or contribute code!</span>
    </a>
    </div>

## 📊 Provider Comparison

Each central bank quotes other currencies against its own, the **base currency**.

| <span style="min-width: 320px;">Provider</span> | Base Currency | <span style="min-width: 220px;">Update Frequency</span> | Good for |
|:---|:---:|:---|:---|
| <img src="https://www.ecb.europa.eu/favicon-32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **ECB** (European Central Bank) | EUR 🇪🇺 | Daily, around 16:00 CET on ECB working days | Euro pairs and the main world currencies |
| <img src="https://fred.stlouisfed.org/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **FED** (Federal Reserve FRED) | USD 🇺🇸 | Daily, on US business days | US-dollar pairs |
| <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOE** (Bank of England) | GBP 🇬🇧 | Daily, on UK business days | Sterling pairs |
| <img src="https://data.snb.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **SNB** (Swiss National Bank) | CHF 🇨🇭 | Monthly averages, one value per month | Swiss-franc pairs, when a monthly rate is enough |

## 🎯 How Routing & Fallback Works

1. 🛤️ **Direct route**: one central bank quotes the pair — e.g. EUR/USD from the ECB.
2. 🔀 **Chain route**: no bank quotes the pair, so LibreFolio combines steps — e.g. RON/USD as
   RON → EUR → USD, both steps from the ECB. A chain gets a rate only on days when every step has
   one.
3. 🔄 **Fallback**: with several routes, a sync tries them in priority order and uses the first
   one that works.
4. ✍️ **Manual**: no route for your pair? Save it without a provider and enter the rates yourself
   in the [Data Editor](../detail/data-editor.md).

You choose the routes when you [add a pair](../add-pair.md), and change them later with the
pair's [Providers](../detail/provider.md) button.

!!! warning "SNB: one rate per month"

    The SNB publishes monthly averages, dated the 1st of each month. A pair that uses it gets one
    rate per month, and a chain through the SNB has rates only on those days.

## 🔗 Related

- 🛠️ **For developers: [FX Providers](../../../developer/backend/fx/providers/index.md)** — APIs, series and quotation formats
