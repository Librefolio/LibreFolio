# Piano UI: Dashboard Home

Questo documento contiene il wireframe ASCII per la vista generale della Dashboard Home, che aggrega i dati di più broker e mostra l'andamento complessivo del portafoglio.

## Wireframe Generale

Consente di filtrare per uno o più broker tramite un pannello a comparsa (popover a checklist, identico ai filtri della pagina Assets) e scegliere il range temporale desiderato.

```text
+-------------------------------------------------------------------------------------------------+
|  LibreFolio                                                                  [Avatar] Username  |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   DASHBOARD HOME                                                                                |
|   [ Range: 1W | 1M | ... | Custom ]  [ Filtra Broker (3) v ]                   [↻ Sincronizza]  |
|                                                                                                 |
|   +--------------------------+  +--------------------------+  +--------------------------+      |
|   | NET WORTH COMPLESSIVO    |  | GAIN/LOSS DI PORTAFOGLIO |  | ROI PESATO (PMC/WAC)     |      |
|   | EUR 124.500,00           |  | +EUR 14.250,32  (+12,9%) |  | +11,45%                  |      |
|   | [Dettaglio per valuta]   |  | [Dettaglio per broker]   |  | TWRR: 12,1%  | MWRR: 11,2% |      |
|   +--------------------------+  +--------------------------+  +--------------------------+      |
|                                                                                                 |
|   +------------------------------------------------+  +--------------------------------------+  |
|   | ANDAMENTO DEL PORTAFOGLIO (GROWTH)  [EUR | % ] |  | ALLOCAZIONE PATRIMONIALE             |  |
|   |                                                |  | [Tipo Asset] [Settore] [Geografica]  |  |
|   |  EUR (o Percentuale se vista %)                |  |                                      |  |
|   |  150k +                                 ..**   |  |         _.._   [■] ETF     (45%)     |  |
|   |       |                             ..**       |  |       .'    '. [■] AZIONI  (30%)     |  |
|   |  100k |                         ..** - - -     |  |      /  (•)   \ [■] CRYPTO  (15%)     |  |
|   |       |                     ..**               |  |     |   NAV   | [■] LIQUID. (10%)     |  |
|   |   50k |                 ..**                   |  |      \       /                       |  |
|   |       |             ..**                       |  |       '.__..'                        |  |
|   |     0 +---*---*---*---*---*---*---*---*---*--->|  |  ( ) MAPPA DEL MONDO                 |  |
|   |         Gen Feb Mar Apr Mag Giu Lug Ago Set    |  |  Mappa a calore basata sul paese     |  |
|   |         [■] Valore NAV / MWRR                  |  |  dell'asset, con 'Unknown' separato  |  |
|   |         [- -] Capitale Invest. / TWRR          |  |                                      |  |
|   |         [....] Liquidità / ROI Semplice        |  |                                      |  |
|   +------------------------------------------------+  +--------------------------------------+  |
|                                                                                                 |
|   +-----------------------------------------+  +---------------------------------------------+  |
|   | LE TUE POSIZIONI (ASSET)                |  | ULTIME TRANSAZIONI                          |  |
|   | Asset         Prezzo   Valore     Gain  |  | Data  Tipo   Asset   Broker   Importo       |  |
|   | [Ic] AAPL     $291     $1.200     +67%  |  | 09-06 BUY    AAPL    IBKR     € -250,00     |  |
|   | [Ic] VWCE     €114     €5.400     +12%  |  |                               +1 AAPL       |  |
|   |                                         |  | 08-06 DEP    --      Directa  € +1.000,00   |  |
|   | Vedi Tutti ->                           |  | Vedi Tutte ->                               |  |
|   +-----------------------------------------+  +---------------------------------------------+  |
|   *In modalità Mobile, il blocco "Transazioni" scivolerà automaticamente sotto agli "Asset"*    |
+-------------------------------------------------------------------------------------------------+
```

---

## Requisiti Dati Frontend

Per renderizzare questa schermata, il frontend necessita delle seguenti funzionalità:

### Funzionalità Esistenti (da riutilizzare o integrare):
* **Componente `DateRangePicker`**: Esiste (usato in `assets/` e `forex/`).
* **Filtro Multi-selettore Broker**: Esiste concettualmente (popover a checklist simile a quello degli asset), va applicato al contesto Broker.
* **Componente `<TransactionsTable>`**: Esiste ed è completo, va montato in fondo alla pagina passando la prop per nascondere paginazione/filtri avanzati (solo modalità "Ultime righe").

### Funzionalità da Sviluppare (Frontend State Management):
* **`portfolioStore.ts`**: Store globale di caching (Svelte Store) che trattiene l'ultimo JSON di `summary` e `history` per evitare che la navigazione tra le pagine della dashboard e dei broker continui a innescare il ricalcolo backend. Include metodi per invalidare la cache (su CRUD transazioni) e il refresh forzato tramite il pulsante `[↻ Sincronizza]`.

### Funzionalità da Sviluppare (Backend & API):
* **`GET /api/v1/portfolio/summary`**: Endpoint che restituisce (filtrando per `broker_id` opzionali):
  * KPI totali: `net_worth`, `total_gain_loss` (assoluto e %), `cash_total`.
  * Metriche ROI: `twrr_percent` e `mwrr_percent`.
  * Dati aggregati per le 3 allocazioni: `allocation_by_type`, `allocation_by_sector`, `allocation_by_geography`.
  * **Breakdown per Broker (Opzionale)**: Supporta il query parameter `?include_breakdown=true` (default `false`). Se attivo, include un array `by_broker: [{broker_id, net_worth, ...}]` per fornire agilmente i saldi alla pagina "Global Brokers" senza fare chiamate multiple, eseguendo i calcoli N+1 in memoria (super-veloce) dopo un solo fetch I/O.
* **`GET /api/v1/portfolio/history`**: Endpoint che restituisce (filtrando per `broker_id` opzionali e `date_range`):
  * Serie storica aggregata giornaliera: `date`, `cash_value`, `invested_value`, `nav_value` (per la vista EUR).
  * Serie storica percentuale: `twrr`, `mwrr`, `roi` (per la vista % attivabile dal toggle `[EUR | %]`).

*Nota*: le formule matematiche core (TWRR, MWRR) dovranno essere calcolate in backend (all'interno di `roi_utils.py` orchestrato da `portfolio_service.py`) per garantire consistenza dei dati.


---
## 1. Riassunto high-level / ASCII art per documentazione piano

````markdown
# Dashboard KPI Cards — High-Level UI Plan

## Obiettivo

Ripensare la riga delle 3 KPI card della dashboard portfolio per renderla più chiara, d’impatto e leggibile sia desktop sia mobile.

La struttura target resta a 3 blocchi principali:

1. `Net Worth`
2. `Period P&L`
3. `Returns`

Le card devono distinguere chiaramente:

- valori snapshot a fine periodo;
- risultato monetario del periodo;
- metriche percentuali di rendimento.

---

## Decisioni principali

### 1. Net Worth

La card `Net Worth` rappresenta uno snapshot alla fine della finestra selezionata.

Deve mostrare:

- NAV / Net Worth come valore principale;
- Book Value con numero e barra;
- NAV con numero e barra;
- Cash;
- Unrealized Gain/Loss.

Il confronto visuale Book Value vs NAV deve aiutare l’utente a capire rapidamente se il portafoglio è sopra o sotto il costo contabile.

Desktop layout:

```text
┌──────────────────────────────┐
│ NET WORTH                (?) │
│ EUR 33.391,52                │
│                              │
│ Book Value      EUR 27.380   │
│ ███████████████░░░           │
│                              │
│ Net Asset Value EUR 33.391   │
│ ██████████████████           │
│                              │
│ Cash            EUR 631,85   │
│ UGL             +EUR 6.011   │
└──────────────────────────────┘
````

Mobile layout:

```text
┌──────────────────────────────┐
│ NET WORTH                (?) │
│ EUR 33.391,52                │
│                              │
│ Book Value      EUR 27.380   │
│ ███████████████░░░           │
│                              │
│ Net Asset Value EUR 33.391   │
│ ██████████████████           │
│                              │
│ Cash            EUR 631,85   │
│ UGL             +EUR 6.011   │
└──────────────────────────────┘
```

Note:

* I valori monetari devono usare il formatter/helper currency già presente nel frontend, incluse emoji/bandiere valuta dove previsto dallo standard del progetto.
* La `(?)` deve linkare alla futura pagina wiki `Net Worth / NAV`.

***

### 2. Period P\&L

La card `Period P&L` rappresenta il risultato monetario della finestra selezionata.

Deve mostrare:

* P\&L monetario come valore principale;
* NAV start;
* NAV end;
* Net flows.

Non deve mostrare una percentuale P\&L separata, perché rischia di sovrapporsi semanticamente al ROI.

Formula concettuale:

```text
period_pnl = nav_end - nav_start - net_external_flows
```

Desktop/mobile layout:

```text
┌──────────────────────────────┐
│ PERIOD P&L               (?) │
│ +EUR 6.011,23                │
│                              │
│ NAV start       EUR 27.380   │
│ NAV end         EUR 33.391   │
│ Net flows       EUR 0,00     │
│                              │
│ Cash-flow adjusted result    │
└──────────────────────────────┘
```

Note:

* Il P\&L è monetario.
* Il ROI resta nella card `Returns`.
* La `(?)` deve linkare alla futura pagina wiki `Period P&L`.

***

### 3. Returns

La card `Returns` rappresenta le metriche percentuali del periodo selezionato.

Deve mostrare:

* ROI;
* TWRR cumulativo;
* MWRR cumulativo;
* MWRR annualizzato.

Il grafico `%` usa metriche cumulative:

```text
TWRR cumulative
MWRR cumulative
ROI
```

La card può mostrare anche `MWRR annualized`, ma deve essere chiaramente etichettato.

Desktop/mobile layout:

```text
┌──────────────────────────────┐
│ RETURNS                  (?) │
│ ROI              21,95%      │
│ TWRR cum         27,11%      │
│ MWRR cum         35,13%      │
│ MWRR ann         24,74%      │
│                              │
│ Period-based returns         │
└──────────────────────────────┘
```

Note:

* `MWRR` senza specifica non è abbastanza chiaro.
* Usare label esplicite:
  * `MWRR cum`
  * `MWRR ann`
* La `(?)` deve linkare alla pagina wiki MWRR/TWRR/ROI o performance metrics.

***

## Layout complessivo desktop

```text
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ NET WORTH                (?) │ PERIOD P&L               (?) │ RETURNS                  (?) │
│ EUR 33.391,52                │ +EUR 6.011,23                │ ROI              21,95%      │
│                              │                              │                              │
│ Book Value      EUR 27.380   │ NAV start       EUR 27.380   │ TWRR cum         27,11%      │
│ ███████████████░░░           │ NAV end         EUR 33.391   │ MWRR cum         35,13%      │
│                              │ Net flows       EUR 0,00     │ MWRR ann         24,74%      │
│ Net Asset Value EUR 33.391   │                              │                              │
│ ██████████████████           │ Cash-flow adjusted result    │ Period-based returns         │
│                              │                              │                              │
│ Cash            EUR 631,85   │                              │                              │
│ UGL             +EUR 6.011   │                              │                              │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

***

## Layout complessivo mobile

```text
┌──────────────────────────────┐
│ NET WORTH                (?) │
│ EUR 33.391,52                │
│ Book Value      EUR 27.380   │
│ ███████████████░░░           │
│ Net Asset Value EUR 33.391   │
│ ██████████████████           │
│ Cash            EUR 631,85   │
│ UGL             +EUR 6.011   │
└──────────────────────────────┘

┌──────────────────────────────┐
│ PERIOD P&L               (?) │
│ +EUR 6.011,23                │
│ NAV start       EUR 27.380   │
│ NAV end         EUR 33.391   │
│ Net flows       EUR 0,00     │
│ Cash-flow adjusted result    │
└──────────────────────────────┘

┌──────────────────────────────┐
│ RETURNS                  (?) │
│ ROI              21,95%      │
│ TWRR cum         27,11%      │
│ MWRR cum         35,13%      │
│ MWRR ann         24,74%      │
│ Period-based returns         │
└──────────────────────────────┘
```

***

## Metriche escluse per ora

Non implementare ora nella riga KPI:

* Sharpe;
* Sortino;
* Max Drawdown;
* Volatilità;
* Realized P\&L;
* Income;
* Fees/Taxes.

Sono metriche utili, ma richiedono un progetto dedicato e policy di calcolo/documentazione.


---

Sì. Alla luce dell’analisi, per ora farei **Step A solido**:

* fix `period_nav_start = 0` se `date_from` è prima del primo evento;
* card `Period P&L` semplice ma corretta;
* niente breakdown avanzato finché non aggiungiamo `income`, `fees_taxes`, `unrealized_delta`, `realized_gain_loss`;
* UI già pronta visivamente per evolvere dopo.

***

# ASCII art aggiornata — KPI cards high-level

```text
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ NET WORTH                (?) │ PERIOD P&L               (?) │ RETURNS                  (?) │
│                              │                              │                              │
│ EUR 32.596,13                │ +EUR 5.215,84                │ ROI              19,05%      │
│                              │                              │                              │
│ Net Asset Value EUR 32.596   │ Start NAV       EUR 0,00     │ TWRR cumulative  24,08%      │
│ ██████████████████           │ Net flows       +EUR 27.380  │ MWRR cumulative  30,38%      │
│                              │                              │ MWRR annualized  21,51%      │
│ Book Value      EUR 27.781   │ Cash-flow adjusted result    │                              │
│ ███████████████░░░           │                              │ Period-based returns         │
│                              │                              │                              │
│ Cash            EUR 631,85   │                              │                              │
│ Unrealized G/L  +EUR 4.814   │                              │                              │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

## Mobile

```text
┌──────────────────────────────┐
│ NET WORTH                (?) │
│ EUR 32.596,13                │
│                              │
│ Net Asset Value EUR 32.596   │
│ ██████████████████           │
│ Book Value      EUR 27.781   │
│ ███████████████░░░           │
│                              │
│ Cash            EUR 631,85   │
│ Unrealized G/L  +EUR 4.814   │
└──────────────────────────────┘

┌──────────────────────────────┐
│ PERIOD P&L               (?) │
│ +EUR 5.215,84                │
│                              │
│ Start NAV       EUR 0,00     │
│ Net flows       +EUR 27.380  │
│                              │
│ Cash-flow adjusted result    │
└──────────────────────────────┘

┌──────────────────────────────┐
│ RETURNS                  (?) │
│ ROI              19,05%      │
│ TWRR cumulative  24,08%      │
│ MWRR cumulative  30,38%      │
│ MWRR annualized  21,51%      │
│                              │
│ Period-based returns         │
└──────────────────────────────┘
```


Sì, sono d’accordo: **barre anche nella card Period P\&L**. A quel punto le card 2 e 3 hanno una grammatica visiva coerente:

* **Period P\&L**: barre per contributori monetari al risultato.
* **Returns**: barre per confronto tra metriche percentuali.
* **Fees & Taxes**: valore negativo, barra rossa.

L’unica attenzione: nella card P\&L le barre devono rappresentare la **contribuzione al P\&L**, non una progress bar rispetto al NAV.

***

## ASCII art aggiornato — con barre P\&L

```text
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ NET WORTH                (?) │ PERIOD P&L               (?) │ RETURNS                  (?) │
│ EUR 33.395,52                │ +EUR 5.064,30                │                              │
│                              │                              │ ROI              21,97%      │
│ Net Asset Value EUR 33.395   │ Unrealized Δ    +EUR 4.620   │ ███████████░░░               │
│ ██████████████████           │ ██████████████████           │                              │
│                              │                              │ TWRR cumulative  27,13%      │
│ Book Value      EUR 27.781   │ Income          +EUR 580     │ █████████████░               │
│ ███████████████░░░           │ ██░░░░░░░░░░░░░░░             │                              │
│                              │                              │ MWRR cumulative  35,15%      │
│ Cash            EUR 631,85   │ Fees & Taxes    -EUR 136     │ ██████████████████           │
│ Unrealized G/L  +EUR 5.614   │ ███                          │                              │
│                              │                              │ MWRR annualized  24,76%      │
│                              │ Other result    +EUR 0       │ ████████████░░               │
│                              │ ░░░                          │                              │
│                              │                              │ Period-based returns         │
│                              │ Start NAV       EUR 0,00     │                              │
│                              │ Net flows       +EUR 28.331  │                              │
│                              │ Cash-flow adjusted result    │                              │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

***

## Variante mobile

```text
┌──────────────────────────────┐
│ PERIOD P&L               (?) │
│ +EUR 5.064,30                │
│                              │
│ Unrealized Δ    +EUR 4.620   │
│ ██████████████████           │
│                              │
│ Income          +EUR 580     │
│ ██░░░░░░░░░░░░░░░             │
│                              │
│ Fees & Taxes    -EUR 136     │
│ ███                          │
│                              │
│ Other result    +EUR 0       │
│ ░░░                          │
│                              │
│ Start NAV       EUR 0,00     │
│ Net flows       +EUR 28.331  │
│ Cash-flow adjusted result    │
└──────────────────────────────┘
```

***

## Regole barre Period P\&L

Le barre della card P\&L devono essere normalizzate sul massimo contributore assoluto:

```text
max_abs_pnl_component =
    max(
        abs(period_unrealized_gain_loss_delta),
        abs(period_income),
        abs(period_fees_taxes),
        abs(period_other_result)
    )
```

Poi:

```text
bar_width = abs(component_value) / max_abs_pnl_component
```

Colori:

```text
valori positivi  → green
valori negativi  → red / rose
zero / null      → slate / gray
```

Per `Fees & Taxes`:

```text
DTO: period_fees_taxes = valore positivo del costo
UI: mostra -period_fees_taxes
Barra: rossa
```

Quindi se il backend dà:

```text
period_fees_taxes = EUR 136
```

la UI mostra:

```text
Fees & Taxes    -EUR 136
```

## 1. High level plan / ASCII art

````markdown
# Dashboard KPI Cards — Final Target

## Obiettivo

Rifinire le 3 KPI card della dashboard portfolio:

1. `Patrimonio Netto`
2. `P&L Periodo`
3. `Rendimenti`

La sezione deve essere leggibile, non ansiogena, e coerente con la nuova architettura portfolio.

---

## Card 1 — Patrimonio Netto

La card `Patrimonio Netto` mostra lo snapshot a fine periodo.

Deve contenere:

- NAV / Patrimonio netto come valore principale;
- barra NAV;
- marker/tooltip sul NAV iniziale, senza mostrare NAV iniziale come riga principale;
- Valore Contabile;
- Liquidità;
- G/L non realizzato.

```text
┌──────────────────────────────┐
│ PATRIMONIO NETTO         (?) │
│          33.400,52 € 🇪🇺 EUR │
│                              │
│ Valore Netto (NAV)           │
│ 33.400,52 € 🇪🇺 EUR          │
│ ██████████████████           │
│        ▲                     │
│ tooltip: NAV iniziale        │
│ 19.811,22 € 🇪🇺 EUR          │
│                              │
│ Valore Contabile             │
│ 27.781,31 € 🇪🇺 EUR          │
│ ███████████████░░░           │
│                              │
│ Liquidità                    │
│ 631,85 € 🇪🇺 EUR             │
│                              │
│ G/L non realizzato           │
│ +5.619,21 € 🇪🇺 EUR          │
│                              │
│ Snapshot a fine periodo      │
└──────────────────────────────┘
````

***

## Card 2 — P\&L Periodo

La card `P&L Periodo` mostra il risultato monetario della finestra selezionata.

Il valore principale è:

```text
period_pnl = nav_end - nav_start - net_external_flows
```

La card deve mostrare una scomposizione del risultato, non NAV end.

Componenti:

* Variazione non realizzata;
* Dividendi e interessi;
* Costi e tasse;
* Altro risultato;
* Movimenti capitale separati dai contributori P\&L.

`Movimenti capitale` rappresenta depositi meno prelievi nel periodo. Non è P\&L.

```text
┌──────────────────────────────┐
│ P&L PERIODO              (?) │
│          +5.069,30 € 🇪🇺 EUR │
│                              │
│ Variazione non realizzata    │
│ +4.908,76 € 🇪🇺 EUR          │
│ ██████████████████           │
│                              │
│ Dividendi e interessi        │
│ +160,32 € 🇪🇺 EUR            │
│ ██░░░░░░░░░░░░░░             │
│                              │
│ Costi e tasse                │
│ -50,48 € 🇪🇺 EUR             │
│ ██░░░░░░░░░░░░░░             │
│                              │
│ Altro risultato              │
│ +50,70 € 🇪🇺 EUR             │
│ ░░░░░░░░░░░░░░               │
│                              │
│ ───────────────────────────  │
│ Movimenti capitale           │
│ +8.520,00 € 🇪🇺 EUR          │
│                              │
│ Risultato corretto per flussi│
└──────────────────────────────┘
```

### Regole negative

Se il P\&L o una componente è negativa:

```text
valore negativo → rosso
barra negativa → rossa
larghezza barra = abs(value) / max_abs_component
```

Esempio:

```text
│ P&L PERIODO              (?) │
│          -7.000,00 € 🇪🇺 EUR │
│                              │
│ Variazione non realizzata    │
│ -6.500,00 € 🇪🇺 EUR          │
│ ██████████████████           │  ← rossa
```

***

## Card 3 — Rendimenti

La card `Rendimenti` mostra le metriche percentuali del periodo.

La metrica headline sarà:

```text
Effetto timing = MWRR cumulativo - TWRR cumulativo
```

Unità:

```text
pp = punti percentuali
```

Interpretazione:

* positivo: timing/importo dei flussi ha migliorato il rendimento rispetto alla strategia pura;
* negativo: timing/importo dei flussi lo ha peggiorato.

Sotto la headline, mostrare:

* ROI;
* TWRR cumulativo;
* MWRR cumulativo;
* MWRR annualizzato.

```text
┌──────────────────────────────┐
│ RENDIMENTI               (?) │
│                              │
│ Effetto timing               │
│ +8,04 pp                     │
│ ████████████░░░              │
│                              │
│ ROI                          │
│ 21,99%                       │
│ █████████░░░░░░              │
│                              │
│ TWRR cumulativo              │
│ 27,14%                       │
│ ███████████░░░               │
│                              │
│ MWRR cumulativo              │
│ 35,18%                       │
│ ████████████████             │
│                              │
│ MWRR annualizzato            │
│ 24,78%                       │
│ ██████████░░░░               │
│                              │
│ Rendimenti del periodo       │
└──────────────────────────────┘
```

Se `Effetto timing` è negativo:

```text
│ Effetto timing               │
│ -4,20 pp                     │
│ ███████░░░░░░░               │  ← rossa
```

***

## Tooltip richiesti

Usare il tooltip custom del progetto sulle label tecniche.

### P\&L Periodo

```text
Variazione non realizzata:
Variazione del guadagno/perdita latente sulle posizioni ancora aperte.

Dividendi e interessi:
Proventi incassati nel periodo da dividendi, interessi o cedole.

Costi e tasse:
Commissioni e imposte registrate come transazioni separate.

Altro risultato:
Residuo del P&L: vendite, costi incorporati, arrotondamenti o aggiustamenti.

Movimenti capitale:
Depositi meno prelievi nel periodo. Non sono P&L.
```

### Rendimenti

```text
Effetto timing:
Differenza tra MWRR cumulativo e TWRR cumulativo. Mostra quanto timing e importo dei flussi hanno inciso sul rendimento.

ROI:
Rendimento semplice del periodo.

TWRR cumulativo:
Rendimento della strategia, neutralizzando depositi e prelievi.

MWRR cumulativo:
Rendimento money-weighted del periodo, considerando importi e timing dei flussi.

MWRR annualizzato:
Tasso annuo equivalente del rendimento money-weighted.
```

***

## Metriche escluse per ora

Non implementare in questa fase:

* realized gain/loss esplicito;
* risk metrics;
* Sharpe;
* Sortino;
* Max Drawdown;
* Volatilità;
* cache frontend/backend.

````


---

Ottimizzazione vista di asset e transazioni nella dashboard:

Sì, ha senso. Ridefinirei così:

```text
Fase A = quick win / rischio basso
  → adattamento RecentTransactionsPanel

Fase B = blocco asset completo
  → nuovo PositionsPanel
  → shared cells
  → DTO holdings
  → treemap esposizione
  → engine contribution
  → tabella/mappa contributo
```

Questa divisione è più coerente perché il widget asset, se lo tocchiamo, conviene farlo **bene una volta sola**, senza passare da una versione “solo esposizione” che poi va riaperta subito.

***

# Disegno aggiornato roadmap

```text
+==============================================================================================+
| DASHBOARD BOTTOM                                                                              |
+==============================================================================================+

FASE A — Recent Transactions compact
------------------------------------------------
Obiettivo:
  sistemare widget esistente, senza toccare engine asset.

Output:
  +--------------------------------------+
  | ULTIME TRANSAZIONI                   |
  +--------------------------------------+
  | Data | Tipo | Asset | Broker | Qty | Amount |
  |--------------------------------------|
  | 15 giu | Tassa       | —       | directa | —        | -13,18 €  |
  | 15 giu | Commissione | —       | directa | —        |  -1,50 €  |
  | 15 giu | Vendita     | iShares | directa | -12 EXXY | +384,84 € |
  | 08 giu | Acquisto    | Amundi  | directa | +6 CHIP  | -673,56 € |
  |                                                  Vedi tutte → |
  +--------------------------------------+

Scelte:
  - riusa/evolve RecentTransactionsPanel
  - Qty colonna separata
  - Qty neutra, senza rosso/verde
  - Amount = solo cash leg
  - no actions inline
  - no context menu home
  - mobile resta tabella scrollabile
  - desktop double click → view
  - mobile long press → view diretto
```

***

# Fase A — dettaglio transazioni

## Prima

```text
Amount
-673,56 EUR
+6.00 CHIP   ← sub-row colorata sotto amount
```

## Dopo

```text
Qty          Amount
+6 CHIP      -673,56 €
```

Regola:

```text
Qty = quantità asset
Amount = movimento cash
```

Esempi:

```text
BUY:
  Qty    = +6 CHIP
  Amount = -673,56 €

SELL:
  Qty    = -12 EXXY
  Amount = +384,84 €

FEE/TAX/DEPOSIT/WITHDRAWAL:
  Qty    = —
  Amount = cash amount
```

Motivo:

```text
Qty colorata dentro Amount confonde:
  sembra P&L / performance
  invece è solo asset leg
```

***

# Fase B — blocco asset completo

Qui facciamo tutto insieme.

```text
FASE B — Positions Widget + Asset-Level Contribution
----------------------------------------------------
Obiettivo:
  creare il nuovo componente "Le tue posizioni" completo,
  con esposizione + contributo, tabella + mappa.

Output finale:
  +--------------------------------------------------------------+
  | LE TUE POSIZIONI                                             |
  | [ Esposizione | Contributo ]                    [Tabella|Mappa] |
  +--------------------------------------------------------------+
  |                                                              |
  |  vista variabile secondo toggle                              |
  |                                                              |
  | Vedi tutte →                                                 |
  +--------------------------------------------------------------+
```

***

# Fase B — lavoro backend

## 1. Estensione `PortfolioHolding`

Serve comunque per Esposizione.

Aggiungere:

```text
broker_id
broker_name
nav_weight_percent
```

Motivo:

```text
broker_id/broker_name → tabella + treemap Broker → Asset Type → Asset
nav_weight_percent    → calcolo backend, frontend presentation-only
```

Formula:

```text
nav_weight_percent = current_value / NAV × 100
```

***

## 2. Nuovo endpoint/dati Contribution

Creare nuovo DTO tipo:

```text
AssetPeriodContribution:
  asset_id
  asset_name
  asset_ticker
  asset_type
  broker_id
  broker_name
  period_unrealized_delta
  period_realized_gain_loss
  period_income
  period_fees_taxes
  period_pnl
  period_pnl_percent?   ← opzionale / delicato
  data_quality_flags?
  is_fully_sold
```

Formula:

```text
asset_period_pnl =
    period_unrealized_delta
  + period_realized_gain_loss
  + period_income
  - period_fees_taxes
```

Dove:

```text
period_unrealized_delta =
    unrealized_pnl_end
  - unrealized_pnl_start
```

```text
unrealized_pnl(date) =
    qty(date) × price(date)
  - qty(date) × wac(date)
```

Accumulatori:

```text
per_realized[(broker_id, asset_id)]
per_income[(broker_id, asset_id)]
per_fees_taxes[(broker_id, asset_id)]
unallocated_fees_taxes[broker_id]
unallocated_income[broker_id]
```

Fee/tax:

```text
if tx.asset_id:
  attribuisci all’asset
else:
  bucket Portfolio / Non allocato
```

Niente euristiche.

***

# Fase B — shared cells

Prima di fare la tabella nuova, estrarre/centralizzare:

```text
AssetIdentityCell
AssetTypeBadge
BrokerBadge
MoneyCell
PercentCell
PnlCell
```

Obiettivo:

```text
coerenza con AssetTable e Transactions
senza forzare riuso della tabella Asset full
```

***

# Fase B — vista 1: Esposizione / Tabella

Domanda:

```text
Cosa possiedo ora?
```

```text
+------------------------------------------------------------------------------------------------+
| LE TUE POSIZIONI                               [ Esposizione | Contributo ] [ Tabella | Mappa ] |
+------------------------------------------------------------------------------------------------+
| Asset                                      Tipo        Broker        Valore       Peso   P&L lat.|
|------------------------------------------------------------------------------------------------|
| 🇪🇺👑 VWCE                                  ETF         Directa      €12.450     18,2%   +€840   |
| 🇪🇺 iShares Commodity Swap                  ETF         Directa       €4.820      7,1%   -€180   |
| 🏠 EX ALBERGO VELA                          Crowdfund   Recrowd       €3.000      4,4%      —    |
| 🇺🇸 Apple Inc.                              Stock       Directa       €2.650      3,9%   +€310   |
| 💶 Cash EUR                                 Cash        Directa       €1.920      2,8%      —    |
|                                                                                                |
|                                                                            Vedi tutte →        |
+------------------------------------------------------------------------------------------------+
```

Label corretta:

```text
P&L latente / Unrealized P&L
```

Non:

```text
P&L totale
```

Perché `gain_loss` corrente è:

```text
current_value - WAC × qty
```

quindi esclude:

```text
realized storico
dividendi/interessi storici
fee/tasse storiche
```

***

# Fase B — vista 2: Esposizione / Mappa

Domanda:

```text
Dove pesa il patrimonio?
```

```text
+------------------------------------------------------------------------------------------------+
| LE TUE POSIZIONI                               [ Esposizione | Contributo ] [ Tabella | Mappa ] |
+------------------------------------------------------------------------------------------------+
|                                                                                                |
| Area = valore posizione / NAV                         Colore = P&L latente %                   |
| Gerarchia = Broker → Asset Type → Asset                                                        |
|                                                                                                |
| +-------------------------------- Directa --------------------------------+ +---- Recrowd ----+ |
| | +---------------- ETF ----------------+ +--------- Stock -----------+   | | +-- Crowdfund -+| |
| | |              VWCE                  | |        Apple Inc.         |   | | | EX ALBERGO   || |
| | |            €12.450                 | |         €2.650            |   | | | €3.000      || |
| | |             18,2% NAV              | |          3,9% NAV         |   | | | — P&L       || |
| | +------------------------------------+ +---------------------------+   | | +-------------+| |
| | +------------- ETF ------------------+ +---------- Cash -----------+   | |                 |
| | | iShares Commodity                  | | Cash EUR                  |   | |                 |
| | | €4.820                             | | €1.920                    |   | |                 |
| | | -€180 lat.                         | | —                         |   | |                 |
| | +------------------------------------+ +---------------------------+   | |                 |
| +------------------------------------------------------------------------------+-------------+ |
|                                                                                                |
|                                                                            Vedi tutte →        |
+------------------------------------------------------------------------------------------------+
```

Tooltip:

```text
VWCE
Broker: Directa
Tipo: ETF
Valore: €12.450
Peso NAV: 18,2%
P&L latente: +€840 / +7,2%
```

***

# Fase B — vista 3: Contributo / Tabella

Domanda:

```text
Chi ha mosso il risultato nel periodo?
```

```text
+------------------------------------------------------------------------------------------------+
| LE TUE POSIZIONI                               [ Esposizione | Contributo ] [ Tabella | Mappa ] |
+------------------------------------------------------------------------------------------------+
| Asset                                      Tipo        Broker      P&L periodo       Impatto    |
|------------------------------------------------------------------------------------------------|
| 🇪🇺👑 VWCE                                  ETF         Directa        +€840          Gain #1    |
| 🇺🇸 Apple Inc.                              Stock       Directa        +€310          Gain #2    |
| 🏠 EX ALBERGO VELA                          Crowdfund   Recrowd        +€126          Gain #3    |
| 🇪🇺 iShares Commodity Swap                  ETF         Directa        -€180          Loss #1    |
| Portfolio / Non allocato                    —           Directa         -€30          Costi      |
|                                                                                                |
|                                                                            Vedi tutte →        |
+------------------------------------------------------------------------------------------------+
```

Per ora eviterei o renderei opzionale:

```text
Var. %
```

Motivo:

```text
period_pnl_percent è semanticamente delicata con buy/sell intra-periodo
```

Se la mettiamo:

```text
deve essere nullable
deve avere tooltip molto chiaro
```

***

# Fase B — vista 4: Contributo / Mappa doppia

Domanda:

```text
I gain e le loss da chi arrivano?
```

```text
+------------------------------------------------------------------------------------------------+
| LE TUE POSIZIONI                               [ Esposizione | Contributo ] [ Tabella | Mappa ] |
+------------------------------------------------------------------------------------------------+
|                                                                                                |
| P&L DEL PERIODO PER ASSET                                                                       |
| Area = |P&L periodo|        Scala condivisa: 100% = max(gain totali, loss totali)               |
|                                                                                                |
| +------------------------------------- GUADAGNI ----------------------------------------------+ |
| | Totale gain: +€1.260                                                                          | |
| | +--------------------------- Directa / ETF ---------------------------+ +--- Directa/Stock-+ | |
| | |                              VWCE                                 | | Apple Inc.        | | |
| | |                            +€840                                  | | +€310             | | |
| | +-------------------------------------------------------------------+ +-------------------+ | |
| | +------------------------- Recrowd / Crowdfund ---------------------+                       | |
| | | EX ALBERGO VELA +€126                                             |                       | |
| | +-------------------------------------------------------------------+                       | |
| +------------------------------------------------------------------------------------------------+
|                                                                                                |
| +-------------------------------------- PERDITE ----------------------------------------------+ |
| | Totale loss: -€320                                                                            | |
| | +--------------------------- Directa / ETF ---------------------------+ +--- Portfolio ----+ | |
| | |                    iShares Commodity Swap                          | | Non allocato     | | |
| | |                          -€180                                    | | -€30             | | |
| | +-------------------------------------------------------------------+ +------------------+ | |
| | +----------------------------- Binance / Crypto --------------------+                       | |
| | | Bitcoin -€90                                                       |                       | |
| | +-------------------------------------------------------------------+                       | |
| +------------------------------------------------------------------------------------------------+
|                                                                                                |
|                                                                            Vedi tutte →        |
+------------------------------------------------------------------------------------------------+
```

Scaling:

```text
gross_gains = Σ max(asset_period_pnl, 0)
gross_losses = Σ abs(min(asset_period_pnl, 0))
scale_max = max(gross_gains, gross_losses)
```

```text
gain_area = asset_period_pnl / scale_max
loss_area = abs(asset_period_pnl) / scale_max
```

Se:

```text
gross_gains = 1260
gross_losses = 320
```

allora:

```text
area totale gain = 100%
area totale loss = 25,4%
```

***

# Nuova sequenza implementativa

## Fase A — solo transazioni

```text
A1. Analizzare RecentTransactionsPanel attuale
A2. Separare Qty da Amount
A3. Rendere Qty neutra
A4. Tenere mobile scrollabile
A5. Aggiungere interazioni:
    - desktop double-click → view
    - mobile long-press → view diretto
A6. i18n se servono nuove label
A7. test/svelte-check
```

Output:

```text
widget transazioni pulito
nessun impatto su engine
rischio basso
```

***

## Fase B — asset completo

```text
B1. Backend holdings DTO
    - broker_id
    - broker_name
    - nav_weight_percent

B2. Backend contribution
    - AssetPeriodContribution DTO
    - get_positions_contribution()
    - endpoint/API or include in report
    - accumulatori per asset/broker
    - unallocated bucket

B3. api sync

B4. Shared cells
    - AssetIdentityCell
    - AssetTypeBadge
    - BrokerBadge
    - MoneyCell
    - PercentCell
    - PnlCell

B5. PositionsPanel nuovo
    - toggle Esposizione | Contributo
    - toggle Tabella | Mappa

B6. Esposizione views
    - tabella
    - treemap

B7. Contributo views
    - tabella
    - doppia treemap gain/loss

B8. i18n + cleanup
    - EN/IT/FR/ES
    - rimuovere HoldingsPanel se non più usato
    - i18n audit
```

***

# Perché questa divisione è migliore

Prima divisione:

```text
Phase A = Esposizione + Transactions
Phase B = Contributo
```

rischiava:

```text
toccare PositionsPanel due volte
fare UI asset provvisoria
rifare toggle/layout dopo poco
```

Nuova divisione:

```text
Fase A = transactions only
Fase B = asset completo
```

è più pulita:

```text
- transazioni è quick win isolato
- asset diventa un blocco coerente
- engine contribution e UI nascono insieme
- evitiamo placeholder e funzioni nascoste
```

***

# Decisione finale aggiornata

```text
FASE A
  RecentTransactionsPanel compact/home
  Qty separata
  Amount pulito
  interazioni home

FASE B
  PositionsPanel completo
  Esposizione + Contributo
  Tabella + Mappa
  backend DTO + contribution engine
  shared cells
```

Secondo me questa è la divisione migliore: meno refactor intermedi, più coerenza architetturale.

