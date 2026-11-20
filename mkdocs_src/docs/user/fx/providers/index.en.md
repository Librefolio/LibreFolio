# 🔌 FX Providers

LibreFolio downloads exchange rates from central banks, for free. Most need no API key; Banxico and the
Bank of Korea ask for a free one, which an administrator sets in the plugin settings. A currency
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
    <a href="bdi/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="../../../static/icons/fx/bdi.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="BDI favicon">
            <span class="card-title" style="margin: 0;">Banca d'Italia (BDI)</span>
        </div>
        <span class="card-desc">About 150 currencies against EUR: almost every currency in the world in one step to the euro.</span>
    </a>
    <a href="bcb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.bcb.gov.br/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="BCB favicon">
            <span class="card-title" style="margin: 0;">Banco Central do Brasil (BCB)</span>
        </div>
        <span class="card-desc">About 150 currencies against USD, and the Brazilian real, from the PTAX closing bulletin.</span>
    </a>
    <a href="norges/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.norges-bank.no/Static/Favicons/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="NORGES favicon">
            <span class="card-title" style="margin: 0;">Norges Bank (NORGES)</span>
        </div>
        <span class="card-desc">About 35 currencies against NOK, among them BDT, PKR, VND and MMK.</span>
    </a>
    <a href="nbu/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://bank.gov.ua/frontend/icon/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="NBU favicon">
            <span class="card-title" style="margin: 0;">National Bank of Ukraine (NBU)</span>
        </div>
        <span class="card-desc">Official rates of about 40 currencies against UAH, among them KZT, GEL, AZN and EGP.</span>
    </a>
    <a href="boc/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.bankofcanada.ca/wp-content/themes/ews-build-2024/img/favicon/favicon-32x32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="BOC favicon">
            <span class="card-title" style="margin: 0;">Bank of Canada (BOC)</span>
        </div>
        <span class="card-desc">Daily averages of about 24 currencies against CAD, among them PEN, from 2017.</span>
    </a>
    <a href="banxico/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.banxico.org.mx/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="BANXICO favicon">
            <span class="card-title" style="margin: 0;">Banco de México (BANXICO)</span>
        </div>
        <span class="card-desc">The official US dollar FIX against MXN from 1991, and EUR, JPY, GBP, CNY and the SDR. Needs a free API token.</span>
    </a>
    <a href="cnb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.cnb.cz/export/system/modules/org.opencms.apollo/resources/img/favicon_120.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CNB favicon">
            <span class="card-title" style="margin: 0;">Czech National Bank (CNB)</span>
        </div>
        <span class="card-desc">The CNB fixing of 30 currencies against CZK, from 1991.</span>
    </a>
    <a href="sarb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.resbank.co.za/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="SARB favicon">
            <span class="card-title" style="margin: 0;">South African Reserve Bank (SARB)</span>
        </div>
        <span class="card-desc">25 currencies against ZAR from 2010, among them BWP, KES, MWK, MZN and ZMW.</span>
    </a>
    <a href="bok/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://ecos.bok.or.kr/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="BOK favicon">
            <span class="card-title" style="margin: 0;">Bank of Korea (BOK)</span>
        </div>
        <span class="card-desc">43 currencies against KRW, among them TWD, KZT, MNT, VND, PKR and BDT. Needs a free API key.</span>
    </a>
    <a href="bcrp/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://estadisticas.bcrp.gob.pe/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="BCRP favicon">
            <span class="card-title" style="margin: 0;">Banco Central de Reserva del Perú (BCRP)</span>
        </div>
        <span class="card-desc">The interbank rate of the US dollar against PEN, from 1997.</span>
    </a>
    <a href="trm/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.superfinanciera.gov.co/info/superfinancierav8/web/portal/img/favicon.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="TRM favicon">
            <span class="card-title" style="margin: 0;">TRM Colombia (TRM)</span>
        </div>
        <span class="card-desc">Colombia's official dollar rate against COP, a value for every day, from 1991.</span>
    </a>
    <a href="cbc/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://cpx.cbc.gov.tw/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CBC favicon">
            <span class="card-title" style="margin: 0;">Central Bank of the Republic of China (Taiwan) (CBC)</span>
        </div>
        <span class="card-desc">The interbank closing rate of the US dollar against TWD, the same day, from 2008.</span>
    </a>
    <a href="cbn/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.cbn.gov.ng/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CBN favicon">
            <span class="card-title" style="margin: 0;">Central Bank of Nigeria (CBN)</span>
        </div>
        <span class="card-desc">The central rate of 12 currencies against NGN, among them the West African CFA franc, from 2001.</span>
    </a>
    <a href="cbk/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.centralbank.go.ke/wp-content/uploads/2016/09/NewLogoCBK-150x150.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CBK favicon">
            <span class="card-title" style="margin: 0;">Central Bank of Kenya (CBK)</span>
        </div>
        <span class="card-desc">21 currencies against KES, among them UGX, TZS, RWF and BIF, from 2004.</span>
    </a>
    <a href="rbi/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.rbi.org.in/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="RBI favicon">
            <span class="card-title" style="margin: 0;">Reserve Bank of India (RBI)</span>
        </div>
        <span class="card-desc">The FBIL reference rate of 7 currencies against INR, from 1998, with a gap from 2018 to 2022.</span>
    </a>
    <a href="bog/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.bog.gov.gh/wp-content/uploads/2020/08/logo-150x150.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="BOG favicon">
            <span class="card-title" style="margin: 0;">Bank of Ghana (BOG)</span>
        </div>
        <span class="card-desc">The interbank mid rate of 17 currencies against GHS, among them NGN, XOF, GMD and SLE, from 2020.</span>
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
| <img src="../../../static/icons/fx/bdi.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BDI** (Banca d'Italia) | EUR 🇪🇺 | Daily, on Italian business days | Almost any currency to the euro in one step |
| <img src="https://www.bcb.gov.br/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BCB** (Banco Central do Brasil) | USD 🇺🇸 | Daily, on Brazilian business days | Almost any currency to the US dollar, and BRL |
| <img src="https://www.norges-bank.no/Static/Favicons/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **NORGES** (Norges Bank) | NOK 🇳🇴 | Daily, around 16:00 CET on Norwegian business days | Asian currencies the ECB does not publish (BDT, PKR, VND, MMK) |
| <img src="https://bank.gov.ua/frontend/icon/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **NBU** (National Bank of Ukraine) | UAH 🇺🇦 | Every day, weekends included (each rate valid from the day after it is set) | Central Asia, the Caucasus, Eastern Europe, North Africa |
| <img src="https://www.bankofcanada.ca/wp-content/themes/ews-build-2024/img/favicon/favicon-32x32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOC** (Bank of Canada) | CAD 🇨🇦 | Daily, by 16:30 ET on Canadian business days | Canadian-dollar pairs, a second source for the Americas (PEN) |
| <img src="https://www.banxico.org.mx/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BANXICO** (Banco de México) | MXN 🇲🇽 | Daily, the FIX at 12:00 Mexico City time on Mexican banking days | The official dollar rate of Mexico (needs a free token) |
| <img src="https://www.cnb.cz/export/system/modules/org.opencms.apollo/resources/img/favicon_120.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CNB** (Czech National Bank) | CZK 🇨🇿 | Daily, around 14:30 on Czech working days | Koruna pairs, a long history from 1991 |
| <img src="https://www.resbank.co.za/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **SARB** (South African Reserve Bank) | ZAR 🇿🇦 | Daily, after 10:30 SAST on South African business days | Southern and eastern Africa (BWP, MWK, MZN, ZMW) |
| <img src="https://ecos.bok.or.kr/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOK** (Bank of Korea) | KRW 🇰🇷 | Daily, on Korean business days | Asia and the Middle East to the won (needs a free key) |
| <img src="https://estadisticas.bcrp.gob.pe/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BCRP** (Banco Central de Reserva del Perú) | PEN 🇵🇪 | Peruvian business days, published one to three days late | The official dollar rate of Peru |
| <img src="https://www.superfinanciera.gov.co/info/superfinancierav8/web/portal/img/favicon.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **TRM** (TRM Colombia) | COP 🇨🇴 | Every Colombian banking day, the day before it is valid; a value for every day | The official dollar rate of Colombia |
| <img src="https://cpx.cbc.gov.tw/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CBC** (Central Bank of the Republic of China (Taiwan)) | TWD 🇹🇼 | Every Taiwanese business day, between 16:00 and 17:00 Taiwan time | The Taiwan dollar on the same day |
| <img src="https://www.cbn.gov.ng/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CBN** (Central Bank of Nigeria) | NGN 🇳🇬 | Nigerian business days | The official naira rate |
| <img src="https://www.centralbank.go.ke/wp-content/uploads/2016/09/NewLogoCBK-150x150.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CBK** (Central Bank of Kenya) | KES 🇰🇪 | Kenyan business days | East Africa (UGX, TZS, RWF, BIF) |
| <img src="https://www.rbi.org.in/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **RBI** (Reserve Bank of India) | INR 🇮🇳 | Mumbai business days, around 13:30 India time | The rupee's reference rate (FBIL) |
| <img src="https://www.bog.gov.gh/wp-content/uploads/2020/08/logo-150x150.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOG** (Bank of Ghana) | GHS 🇬🇭 | Ghanaian business days | West Africa (NGN, XOF, GMD, SLE) |

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
