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

nuova sezione card:
Sì, concordo: le card attuali sono **troppo piatte**. Il grafico sotto è molto più ricco e professionale; le KPI sembrano ancora “placeholder”.

Problemi che vedo dallo screen:

```text
1. Le 3 card hanno gerarchia quasi identica.
2. La terza card schiaccia troppe metriche in una riga.
3. MWRR ora è ambiguo: cumulativo o annualizzato?
4. Mancano help icon/wiki link.
5. Non è chiaro quali metriche sono snapshot e quali sono di periodo.
6. Su mobile la sublabel lunga diventerà illeggibile.
```

Io ripenserei la sezione come **“Portfolio overview”**, non semplici card.

***

# Proposta A — 3 card evolute, compatta e solida

È la più semplice da implementare e resta vicina alla UI attuale.

```text
┌────────────────────────────┬────────────────────────────┬────────────────────────────┐
│ PATRIMONIO NETTO       [?] │ RISULTATO PERIODO      [?] │ RENDIMENTI PERIODO     [?] │
│                            │                            │                            │
│ EUR 33.391,52              │ +EUR 6.011,23              │ ROI                         │
│                            │ +21,95%                    │ 21,95%                      │
│ ┌──────────┬─────────────┐ │                            │                            │
│ │ Cash     │ EUR 631,85  │ │ vs inizio periodo          │ ┌──────────┬─────────────┐ │
│ │ Market   │ EUR 32.759  │ │ NAV iniziale: EUR 27.380   │ │ TWRR     │ 27,11%      │ │
│ │ Book     │ EUR 27.380  │ │                            │ │ MWRR cum │ 35,13%      │ │
│ └──────────┴─────────────┘ │                            │ │ MWRR ann │ 24,74%      │ │
│ Snapshot a fine periodo    │ Period based               │ └──────────┴─────────────┘ │
└────────────────────────────┴────────────────────────────┴────────────────────────────┘
```

## Perché funziona

* La prima card è chiaramente **snapshot**.
* La seconda è chiaramente **risultato del periodo**.
* La terza separa bene:
  * ROI
  * TWRR
  * MWRR cumulativo
  * MWRR annualizzato
* Le help icon `[?]` possono rimandare alle wiki.

## Mobile

```text
┌────────────────────────────┐
│ PATRIMONIO NETTO       [?] │
│ EUR 33.391,52              │
│ Cash  EUR 631,85           │
│ Market EUR 32.759          │
│ Book EUR 27.380            │
└────────────────────────────┘

┌────────────────────────────┐
│ RISULTATO PERIODO      [?] │
│ +EUR 6.011,23              │
│ +21,95%                    │
│ vs inizio periodo          │
└────────────────────────────┘

┌────────────────────────────┐
│ RENDIMENTI PERIODO     [?] │
│ ROI        21,95%          │
│ TWRR       27,11%          │
│ MWRR cum   35,13%          │
│ MWRR ann   24,74%          │
└────────────────────────────┘
```

Questa è la proposta più pragmatica.

***

# Proposta B — Hero card + metric matrix

Più impattante. Io la preferisco se vuoi dare alla dashboard un look più “pro”.

```text
┌──────────────────────────────────────────────┬──────────────────────────────────────────────┐
│ PATRIMONIO NETTO                         [?] │ PERFORMANCE PERIODO                      [?] │
│                                              │                                              │
│ EUR 33.391,52                                │ +EUR 6.011,23                              │
│                                              │ +21,95%                                    │
│ ┌──────────────┬──────────────┬────────────┐ │                                              │
│ │ Cash         │ Market       │ Book       │ │ ┌────────────┬────────────┬───────────────┐ │
│ │ EUR 631,85   │ EUR 32.759   │ EUR 27.380 │ │ │ ROI        │ TWRR       │ MWRR cum      │ │
│ └──────────────┴──────────────┴────────────┘ │ │ 21,95%     │ 27,11%     │ 35,13%        │ │
│ Snapshot a 21/06/2026                        │ └────────────┴────────────┴───────────────┘ │
│                                              │ MWRR annualizzato: 24,74%              [?] │
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

## Variante con piccola barra visuale

```text
┌──────────────────────────────────────────────┐
│ PATRIMONIO NETTO                         [?] │
│ EUR 33.391,52                                │
│                                              │
│ Book Value    ████████████████████░░░        │
│ Market Value  ████████████████████████       │
│ Cash          ▏ EUR 631,85                   │
└──────────────────────────────────────────────┘
```

## Perché funziona

* `Net Worth` diventa davvero protagonista.
* La performance non è nascosta in una sublabel.
* MWRR annualizzato è visibile ma secondario.
* Molto leggibile desktop.
* Mobile diventa due blocchi larghi, non tre card piccole.

***

# Proposta C — Scoreboard finanziaria

Più “trading/investment dashboard”, molto d’impatto.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ PORTFOLIO OVERVIEW                                                           │
│                                                                              │
│  NAV                      PERIOD GAIN                 RETURN METRICS          │
│  EUR 33.391,52             +EUR 6.011,23               ROI       21,95%       │
│  Cash EUR 631,85           +21,95%                     TWRR      27,11%       │
│                                                        MWRR cum  35,13%       │
│  Book EUR 27.380           From 2025-02-11             MWRR ann  24,74%       │
│  Market EUR 32.759         To   2026-06-21                                      │
│                                                                              │
│  [ ? NAV ]                [ ? Gain/Loss ]              [ ? ROI/TWRR/MWRR ]    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Perché funziona

* Una sola “super card”.
* Meno bordi, meno frammentazione.
* Ottima per desktop.
* Sembra una dashboard vera.

## Contro

* Su mobile va ripensata bene.
* Più lavoro CSS/responsive.

Mobile:

```text
┌────────────────────────────┐
│ PORTFOLIO OVERVIEW         │
│                            │
│ NAV                        │
│ EUR 33.391,52              │
│ Cash EUR 631,85            │
│ Book EUR 27.380            │
│ Market EUR 32.759          │
│                            │
│ PERIOD GAIN                │
│ +EUR 6.011,23              │
│ +21,95%                    │
│                            │
│ RETURN METRICS             │
│ ROI       21,95%           │
│ TWRR      27,11%           │
│ MWRR cum  35,13%           │
│ MWRR ann  24,74%           │
└────────────────────────────┘
```

***

# Proposta D — Card con “primary metric + metric chips”

È un buon compromesso estetico.

```text
┌────────────────────────────┬────────────────────────────┬────────────────────────────┐
│ NET WORTH              [?] │ PERIOD RESULT          [?] │ RETURNS                [?] │
│                            │                            │                            │
│ EUR 33.391,52              │ +EUR 6.011,23              │ 21,95%                     │
│                            │ +21,95%                    │ ROI                        │
│                            │                            │                            │
│ [ Cash 631,85 ]            │ [ From 2025-02-11 ]        │ [ TWRR 27,11% ]            │
│ [ Market 32.759 ]          │ [ To 2026-06-21 ]          │ [ MWRR cum 35,13% ]        │
│ [ Book 27.380 ]            │                            │ [ MWRR ann 24,74% ]        │
└────────────────────────────┴────────────────────────────┴────────────────────────────┘
```

## Visualmente

Chips con colore leggero:

```text
Cash        gray/blue
Market      green/emerald
Book        slate
TWRR        blue
MWRR cum    emerald
MWRR ann    amber/gray
```

## Perché funziona

* Mantiene 3 card.
* Più leggibile.
* Molto mobile-friendly.
* La terza card non ha più una sublabel infinita.

***

# Proposta E — Performance card separata in 4 mini-metriche

Qui la terza card cambia completamente.

```text
┌────────────────────────────┬────────────────────────────┬────────────────────────────┐
│ NET WORTH                  │ GAIN / LOSS                │ PERFORMANCE                │
│ EUR 33.391,52              │ +EUR 6.011,23              │                            │
│ Cash EUR 631,85            │ +21,95%                    │ ┌───────┬───────┐          │
│                            │                            │ │ ROI   │ TWRR  │          │
│                            │                            │ │21.95% │27.11% │          │
│                            │                            │ ├───────┼───────┤          │
│                            │                            │ │MWRR C │MWRR A │          │
│                            │                            │ │35.13% │24.74% │          │
│                            │                            │ └───────┴───────┘          │
└────────────────────────────┴────────────────────────────┴────────────────────────────┘
```

## Mobile

```text
┌────────────────────────────┐
│ PERFORMANCE            [?] │
│                            │
│ ┌──────────┬─────────────┐ │
│ │ ROI      │ 21,95%      │ │
│ │ TWRR     │ 27,11%      │ │
│ │ MWRR cum │ 35,13%      │ │
│ │ MWRR ann │ 24,74%      │ │
│ └──────────┴─────────────┘ │
└────────────────────────────┘
```

Questa è molto chiara per la parte metriche.

***

# Help icon / wiki link

Metterei icone piccole accanto alle label, non ai valori.

Esempio:

```text
RETURNS [?]
ROI [?]   TWRR [?]   MWRR cum [?]   MWRR ann [?]
```

Oppure più pulito:

```text
PERFORMANCE [?]
```

Clic sul `?` apre pagina generale performance metrics.

Dentro ogni chip puoi avere tooltip:

```text
ROI         [?]
TWRR        [?]
MWRR cum    [?]
MWRR ann    [?]
```

Io farei:

## Desktop

```text
PERFORMANCE [?]
```

e nei tooltip interni:

```text
ROI       ⓘ
TWRR      ⓘ
MWRR cum  ⓘ
MWRR ann  ⓘ
```

## Mobile

Solo una help icon principale, per non affollare.

***

# Link wiki suggeriti

```text
NAV / Net Worth
→ /financial-theory/.../net-asset-value/

Gain/Loss / ROI
→ /financial-theory/.../roi/

TWRR
→ /financial-theory/.../twrr/

MWRR cumulativo / annualizzato
→ /financial-theory/.../mwrr/
```

Nota: se manca la pagina NAV, puoi far puntare Net Worth alla pagina glossary/portfolio valuation.

***

# Naming UI che proporrei

Evita:

```text
Weighted ROI
```

È ambiguo.

Meglio:

```text
Performance
```

o:

```text
Period Returns
```

Se vuoi restare italiano:

```text
Rendimenti periodo
```

La card dovrebbe essere:

```text
RETURNS
ROI
TWRR
MWRR cumulative
MWRR annualized
```

Non:

```text
Weighted ROI
```

Perché ROI, TWRR e MWRR sono tre metriche diverse; chiamare la card “Weighted ROI” e poi metterci TWRR/MWRR sotto confonde.

***

# La mia scelta consigliata

Io sceglierei **Proposta D** ora.

È la più equilibrata:

```text
- non stravolge layout
- migliora tanto la leggibilità
- funziona bene mobile
- mette MWRR cumulativo/annualizzato in modo chiaro
- facile da implementare su KpiCard esistente
```

Target finale:

```text
┌────────────────────────────┬────────────────────────────┬────────────────────────────┐
│ NET WORTH              [?] │ PERIOD RESULT          [?] │ RETURNS                [?] │
│ EUR 33.391,52              │ +EUR 6.011,23              │ ROI 21,95%                 │
│                            │ +21,95%                    │                            │
│ [ Cash 631,85 ]            │ [ From 2025-02-11 ]        │ [ TWRR 27,11% ]            │
│ [ Market 32.759 ]          │ [ To 2026-06-21 ]          │ [ MWRR cum 35,13% ]        │
│ [ Book 27.380 ]            │                            │ [ MWRR ann 24,74% ]        │
└────────────────────────────┴────────────────────────────┴────────────────────────────┘
```

Poi, se vuoi una dashboard più premium, più avanti si può passare alla **Proposta B** con hero card.

---

Sì, mix **A + D** è la strada giusta: manteniamo le 3 card, ma le rendiamo più dense, leggibili e “dashboard-grade”.

Io farei questa struttura:

```text
1. Net Worth / Snapshot
2. P&L / Period Result
3. Returns / Performance Metrics
```

***

# Metriche risk: si applicano al portafoglio?

Sì, **si possono applicare al portafoglio intero**, usando la serie dei rendimenti giornalieri del NAV.

Esempio:

```text
portfolio_daily_return(d) = NAV(d) / NAV(d-1) - 1
```

Da lì puoi calcolare:

```text
Volatilità
Sharpe
Sortino
Max Drawdown
```

Però io **non le metterei ora nelle 3 card principali**, perché:

* richiedono NAV giornaliero affidabile;
* hanno bisogno di policy su dati mancanti/stale;
* Sharpe richiede risk-free rate;
* Sortino richiede definire downside threshold;
* possono confondere se l’utente non le conosce.

Le metterei dopo in una sezione:

```text
Risk Metrics
```

oppure come seconda riga compatta sotto le KPI.

***

# Proposta finale card — mix A + D

## Desktop

```text
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ NET WORTH                [?] │ PERIOD P&L               [?] │ RETURNS                  [?] │
│                              │                              │                              │
│ EUR 33.391,52                │ +EUR 6.011,23                │ ROI                          │
│                              │ +21,95%                      │ 21,95%                       │
│                              │                              │                              │
│ [ Cash      EUR 631,85  ]    │ [ Unreal.  +EUR 5.852 ]      │ [ TWRR cum   27,11% ]        │
│ [ Market    EUR 32.759 ]     │ [ Realized  —         ]      │ [ MWRR cum   35,13% ]        │
│ [ Book      EUR 27.380 ]     │ [ Income    +EUR xxx  ]      │ [ MWRR ann   24,74% ]        │
│                              │                              │                              │
│ Snapshot at period end       │ From start to end            │ Period-based returns         │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

***

# Se alcune metriche P\&L non esistono ancora

All’inizio puoi fare una versione compatta:

```text
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ NET WORTH                [?] │ PERIOD P&L               [?] │ RETURNS                  [?] │
│ EUR 33.391,52                │ +EUR 6.011,23                │ ROI 21,95%                   │
│                              │ +21,95%                      │                              │
│ [ Cash   EUR 631,85 ]        │ [ NAV start EUR 27.380 ]     │ [ TWRR cum 27,11% ]          │
│ [ Market EUR 32.759 ]        │ [ NAV end   EUR 33.391 ]     │ [ MWRR cum 35,13% ]          │
│ [ Book   EUR 27.380 ]        │ [ Net flows EUR xxx ]        │ [ MWRR ann 24,74% ]          │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

Poi più avanti, quando hai realised P\&L, income, fees/taxes ben calcolati, sostituisci.

***

# Mobile

Su mobile le card devono diventare leggibili, non semplicemente impilate con testo troncato.

```text
┌──────────────────────────────┐
│ NET WORTH                [?] │
│ EUR 33.391,52                │
│                              │
│ Cash        EUR 631,85       │
│ Market      EUR 32.759       │
│ Book Value  EUR 27.380       │
│ Snapshot at period end       │
└──────────────────────────────┘

┌──────────────────────────────┐
│ PERIOD P&L               [?] │
│ +EUR 6.011,23                │
│ +21,95%                      │
│                              │
│ NAV start   EUR 27.380       │
│ NAV end     EUR 33.391       │
│ Net flows   EUR xxx          │
└──────────────────────────────┘

┌──────────────────────────────┐
│ RETURNS                  [?] │
│ ROI        21,95%            │
│ TWRR cum   27,11%            │
│ MWRR cum   35,13%            │
│ MWRR ann   24,74%            │
└──────────────────────────────┘
```

***

# Cosa metterei davvero nelle 3 card ora

## Card 1 — Net Worth

Snapshot alla fine del periodo.

```text
Main:
NAV / Net Worth

Chips:
Cash
Market Value
Book Value
```

Possibile anche:

```text
Unrealized P&L
```

se vuoi evidenziare subito la distanza tra NAV e book value.

```text
[ Unrealized +EUR 5.852 ]
```

***

## Card 2 — Period P\&L

Questa card deve raccontare i soldi reali guadagnati nel periodo.

Formula concettuale:

```text
period_pnl = NAV_end - NAV_start - net_external_flows
```

Dove:

```text
net_external_flows = depositi - prelievi nello scope selezionato
```

Questa è diversa dal semplice:

```text
NAV_end - NAV_start
```

perché depura depositi/prelievi.

Chips iniziali:

```text
NAV start
NAV end
Net flows
```

Future chips:

```text
Realized P&L
Unrealized P&L
Income
Fees/Taxes
```

***

## Card 3 — Returns

Questa diventa una mini tabella metriche.

```text
ROI
TWRR cumulative
MWRR cumulative
MWRR annualized
```

Non chiamerei più la card:

```text
Weighted ROI
```

La chiamerei:

```text
Returns
```

oppure in italiano:

```text
Rendimenti
```

***

# ASCII più rifinito

```text
┌────────────────────────────────────────────────────────────────────────────────────┐
│ KPI ROW                                                                            │
├──────────────────────────────┬──────────────────────────────┬──────────────────────┤
│ NET WORTH                (?) │ PERIOD P&L               (?) │ RETURNS          (?) │
│                              │                              │                      │
│ EUR 33.391,52                │ +EUR 6.011,23                │ ROI                  │
│                              │ +21,95%                      │ 21,95%               │
│                              │                              │                      │
│  Cash        EUR 631,85      │  NAV start   EUR 27.380      │  TWRR cum   27,11%   │
│  Market      EUR 32.759      │  NAV end     EUR 33.391      │  MWRR cum   35,13%   │
│  Book value  EUR 27.380      │  Net flows   EUR 0,00        │  MWRR ann   24,74%   │
│                              │                              │                      │
│ Snapshot at end date         │ Cash-flow adjusted           │ Period metrics       │
└──────────────────────────────┴──────────────────────────────┴──────────────────────┘
```

***

# Variante con P\&L breakdown futuro

Quando avremo più dati:

```text
┌──────────────────────────────┐
│ PERIOD P&L               (?) │
│ +EUR 6.011,23                │
│ +21,95%                      │
│                              │
│  Unrealized   +EUR 5.852     │
│  Realized     +EUR 120       │
│  Income       +EUR 58        │
│  Fees/Taxes   -EUR 19        │
│                              │
│ Cash-flow adjusted           │
└──────────────────────────────┘
```

Questa è molto bella, ma la farei solo quando i dati sono solidi.

***

# Dove mettere Sharpe / Sortino / Drawdown / Volatility

Non nelle 3 card principali ora.

Proposta futura: una riga sotto, più piccola.

```text
┌────────────────────────────────────────────────────────────────────────────────────┐
│ RISK METRICS                                                                       │
│                                                                                    │
│ [ Max Drawdown  -8,4% (?) ] [ Volatility  12,1% (?) ] [ Sharpe  0,84 (?) ]         │
│ [ Sortino       1,12 (?) ]                                                         │
└────────────────────────────────────────────────────────────────────────────────────┘
```

Oppure dentro la card Returns, come sezione collapsible:

```text
RETURNS
ROI        21,95%
TWRR cum   27,11%
MWRR cum   35,13%
MWRR ann   24,74%

Risk metrics
Max DD     — 
Volatility —
Sharpe     —
Sortino    —
```

Per ora metterei placeholder? No. Meglio no.

***

# Help icon / libro

Io userei una piccola icona help vicino ai titoli e alle metriche specifiche.

```text
NET WORTH        [?]
PERIOD P&L       [?]
RETURNS          [?]

ROI              [?]
TWRR cum         [?]
MWRR cum         [?]
MWRR ann         [?]
```

Se troppe icone disturbano:

* una icona nel titolo card;
* tooltip interno con righe cliccabili.

Esempio:

```text
RETURNS [?]

click [?] apre menu:
┌──────────────────────────────┐
│ ROI                📖        │
│ TWRR cumulativo    📖        │
│ MWRR cumulativo    📖        │
│ MWRR annualizzato  📖        │
└──────────────────────────────┘
```

Per mobile, farei solo help card-level.

***

# Link wiki

Suggerimento:

```text
Net Worth / NAV
→ /financial-theory/.../nav/

Period P&L / ROI
→ /financial-theory/.../roi/

TWRR
→ /financial-theory/.../twrr/

MWRR cumulative / annualized
→ /financial-theory/.../mwrr/
```

Se non esiste NAV, linka alla pagina valuation/portfolio value.

***

# Metriche che aggiungerei ora o presto

## Ora

```text
Cash
Market Value
Book Value
Unrealized P&L
Period P&L
Net flows
ROI
TWRR cumulative
MWRR cumulative
MWRR annualized
```

## Dopo

```text
Realized P&L
Income
Fees/Taxes
Max Drawdown
Volatility
Sharpe
Sortino
Benchmark excess return
Cash ratio
```

***

# Nota su P\&L e Gain/Loss

Io cambierei label:

```text
Gain / Loss
```

in:

```text
Period P&L
```

Perché “Gain/Loss” può sembrare lifetime o posizione aperta.

`Period P&L` invece dice chiaramente:

```text
risultato della finestra selezionata
```

***

# Decisione consigliata

Implementerei questo adesso:

```text
Card 1: Net Worth
- NAV
- Cash
- Market Value
- Book Value

Card 2: Period P&L
- P&L assoluto
- P&L %
- NAV start
- NAV end
- Net flows

Card 3: Returns
- ROI
- TWRR cumulative
- MWRR cumulative
- MWRR annualized
```

E rimanderei:

```text
Sharpe
Sortino
Max Drawdown
Volatility
```

a una riga successiva o a uno step futuro dedicato.


---

Sintesi con metriche:

Sì, **P\&L e ROI sono diverse**.

## 1. P\&L vs ROI

### P\&L

Il **P\&L** è un valore monetario.

Risponde a:

```text
Quanti euro ho guadagnato o perso nel periodo?
```

Formula concettuale:

```text
period_pnl = NAV_end - NAV_start - net_external_flows
```

Dove:

```text
net_external_flows = depositi - prelievi nel periodo
```

Esempio:

```text
NAV inizio: 27.000 €
Depositi nel periodo: +1.000 €
NAV fine: 33.000 €

P&L = 33.000 - 27.000 - 1.000 = +5.000 €
```

Quindi il P\&L è:

```text
+5.000 €
```

***

### ROI

Il **ROI** è una percentuale.

Risponde a:

```text
Quanto ho reso rispetto al capitale investito?
```

Esempio semplificato:

```text
P&L = +5.000 €
capitale di riferimento = 27.000 €

ROI ≈ 5.000 / 27.000 = 18,5%
```

Quindi:

```text
P&L = soldi guadagnati
ROI = rendimento percentuale
```

Sono collegati, ma non sono la stessa cosa.

***

# 2. Cosa intendevo con `Book`

`Book` = **Book Value** = valore contabile.

Formula:

```text
book_value = open_cost_basis + cash + in_transit_book_value
```

Nel tuo caso, semplificando:

```text
Book Value = costo di carico delle posizioni aperte + liquidità
```

Serve a confrontare:

```text
NAV = valore di mercato
Book Value = valore contabile/costo
```

La differenza è:

```text
unrealized_gain_loss = NAV - Book Value
```

Esempio:

```text
Book Value: 27.380 €
NAV:        33.391 €
Differenza: +6.011 €
```

Quindi `Book` è utile nella prima card perché spiega da dove arriva il NAV.

***

# 3. Cosa intendevo con `Income`

`Income` sarebbero:

```text
dividendi
interessi
cedole
```

Quindi una parte del P\&L non dovuta alla rivalutazione degli asset, ma a flussi interni positivi.

Esempio:

```text
P&L periodo: +6.000 €

di cui:
- rivalutazione asset: +5.700 €
- dividendi/interessi/cedole: +350 €
- fee/tasse: -50 €
```

Però qui hai ragione: **se oggi non abbiamo già il breakdown pulito, meglio non metterlo**.

Quindi per ora eviterei:

```text
Income
Realized P&L
Fees/Taxes
```

Finché non siamo sicuri dei calcoli.

***

# 4. Card P\&L: versione più chiara

Per ora la seconda card la farei così:

```text
┌──────────────────────────────┐
│ PERIOD P&L               (?) │
│                              │
│ +EUR 6.011,23                │
│ +21,95%                      │
│                              │
│  NAV start   EUR 27.380      │
│  NAV end     EUR 33.391      │
│  Net flows   EUR 0,00        │
│                              │
│ Cash-flow adjusted result    │
└──────────────────────────────┘
```

Così racconta chiaramente:

```text
quanto valevo all’inizio
quanto valgo alla fine
quanti soldi ho aggiunto/tolto
quanto ho guadagnato davvero
```

***

# 5. Barra orizzontale: sì, la userei nella Net Worth card

La barra è utile soprattutto nella prima card, per visualizzare:

```text
Book Value vs NAV
```

ASCII:

```text
┌──────────────────────────────┐
│ NET WORTH                (?) │
│                              │
│ EUR 33.391,52                │
│                              │
│ Book Value                   │
│ ████████████████████░░░░░    │
│ EUR 27.380                   │
│                              │
│ NAV                          │
│ ████████████████████████     │
│ EUR 33.391                   │
│                              │
│ Cash        EUR 631,85       │
│ Market      EUR 32.759       │
└──────────────────────────────┘
```

Oppure più compatta:

```text
┌──────────────────────────────┐
│ NET WORTH                (?) │
│ EUR 33.391,52                │
│                              │
│ Book  ███████████████░░░     │
│ NAV   ██████████████████     │
│                              │
│ Cash EUR 631,85              │
│ Unrealized +EUR 6.011        │
└──────────────────────────────┘
```

Questa è bella perché fa capire subito:

```text
quanto del NAV è sopra il costo contabile
```

***

# 6. Proposta aggiornata delle 3 card

## Desktop

```text
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ NET WORTH                (?) │ PERIOD P&L               (?) │ RETURNS                  (?) │
│                              │                              │                              │
│ EUR 33.391,52                │ +EUR 6.011,23                │ ROI                          │
│                              │ +21,95%                      │ 21,95%                       │
│ Book  ███████████████░░░     │                              │                              │
│ NAV   ██████████████████     │  NAV start   EUR 27.380      │  TWRR cum   27,11%           │
│                              │  NAV end     EUR 33.391      │  MWRR cum   35,13%           │
│ Cash        EUR 631,85       │  Net flows   EUR 0,00        │  MWRR ann   24,74%           │
│ Unrealized +EUR 6.011        │                              │                              │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

***

## Mobile

```text
┌──────────────────────────────┐
│ NET WORTH                (?) │
│ EUR 33.391,52                │
│                              │
│ Book  ███████████████░░░     │
│ NAV   ██████████████████     │
│                              │
│ Cash        EUR 631,85       │
│ Unrealized +EUR 6.011        │
└──────────────────────────────┘

┌──────────────────────────────┐
│ PERIOD P&L               (?) │
│ +EUR 6.011,23                │
│ +21,95%                      │
│                              │
│ NAV start   EUR 27.380       │
│ NAV end     EUR 33.391       │
│ Net flows   EUR 0,00         │
└──────────────────────────────┘

┌──────────────────────────────┐
│ RETURNS                  (?) │
│ ROI        21,95%            │
│ TWRR cum   27,11%            │
│ MWRR cum   35,13%            │
│ MWRR ann   24,74%            │
└──────────────────────────────┘
```

***

# 7. Metriche che metterei ora

## Net Worth

```text
NAV
Cash
Market Value
Book Value
Unrealized P&L
```

Ma nella UI mostrerei magari solo:

```text
NAV
Cash
Unrealized P&L
bar Book vs NAV
```

`Market Value` può stare nel tooltip.

***

## Period P\&L

```text
P&L assoluto
P&L %
NAV start
NAV end
Net external flows
```

Questa è chiara e calcolabile.

***

## Returns

```text
ROI
TWRR cumulative
MWRR cumulative
MWRR annualized
```

***

# 8. Eviterei per ora

Per ora non metterei:

```text
Income
Realized P&L
Fees/Taxes
Sharpe
Sortino
Volatility
Max Drawdown
```

Motivo:

```text
o non sono ancora implementati,
o richiedono spiegazioni/policy dedicate.
```

***

# 9. Etichette consigliate

In inglese:

```text
Net Worth
Period P&L
Returns
```

In italiano:

```text
Patrimonio Netto
P&L Periodo
Rendimenti
```

Oppure più user-friendly:

```text
Risultato periodo
```

al posto di `P&L Periodo`.

Io userei:

```text
Period P&L
```

in inglese, perché è standard.

***

# 10. Sintesi decisionale

Per ora disegnerei le card così:

```text
Card 1: Net Worth
- NAV grande
- barra Book vs NAV
- Cash
- Unrealized P&L

Card 2: Period P&L
- P&L assoluto
- P&L %
- NAV start
- NAV end
- Net flows

Card 3: Returns
- ROI
- TWRR cum
- MWRR cum
- MWRR ann
```

Questa versione è solida, bella, mobile-friendly e non introduce metriche non ancora mature.



Sì, corretto.

## P\&L % vs ROI

Se il **P\&L %** lo calcoliamo come:

```text
P&L % = period_pnl / capitale di riferimento
```

allora rischia di sovrapporsi molto al ROI.

Per evitare confusione, nella card **Period P\&L** io toglierei il P\&L %.  
Lasciamo lì solo il valore monetario e i driver:

```text
P&L €
NAV start
NAV end
Net flows
```

La percentuale la lasciamo nella card **Returns**, dove ha senso confrontare:

```text
ROI
TWRR cumulativo
MWRR cumulativo
MWRR annualizzato
```

***

# ASCII aggiornata

## Desktop

```text
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ NET WORTH                (?) │ PERIOD P&L               (?) │ RETURNS                  (?) │
│                              │                              │                              │
│ EUR 33.391,52                │ +EUR 6.011,23                │ ROI                          │
│                              │                              │ 21,95%                       │
│ Book Value                   │ NAV start                    │                              │
│ EUR 27.380                   │ EUR 27.380                   │ TWRR cum        27,11%        │
│ ███████████████░░░░░         │                              │ MWRR cum        35,13%        │
│                              │ NAV end                      │ MWRR ann        24,74%        │
│ Net Asset Value              │ EUR 33.391                   │                              │
│ EUR 33.391                   │                              │                              │
│ ████████████████████         │ Net flows                    │                              │
│                              │ EUR 0,00                     │                              │
│ Cash          EUR 631,85     │                              │                              │
│ Unrealized    +EUR 6.011     │ Cash-flow adjusted result    │ Period-based returns         │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

***

## Variante più compatta desktop

```text
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ NET WORTH                (?) │ PERIOD P&L               (?) │ RETURNS                  (?) │
│ EUR 33.391,52                │ +EUR 6.011,23                │ ROI  21,95%                  │
│                              │                              │                              │
│ Book  EUR 27.380             │ NAV start  EUR 27.380        │ TWRR cum   27,11%            │
│       ███████████████░░░     │ NAV end    EUR 33.391        │ MWRR cum   35,13%            │
│ NAV   EUR 33.391             │ Net flows  EUR 0,00          │ MWRR ann   24,74%            │
│       ██████████████████     │                              │                              │
│ Cash  EUR 631,85             │ Adjusted for cash flows      │ Period metrics              │
│ UGL   +EUR 6.011             │                              │                              │
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

Questa è quella che preferisco.

***

## Mobile

```text
┌──────────────────────────────┐
│ NET WORTH                (?) │
│ EUR 33.391,52                │
│                              │
│ Book  EUR 27.380             │
│       ███████████████░░░     │
│ NAV   EUR 33.391             │
│       ██████████████████     │
│                              │
│ Cash  EUR 631,85             │
│ UGL   +EUR 6.011             │
└──────────────────────────────┘

┌──────────────────────────────┐
│ PERIOD P&L               (?) │
│ +EUR 6.011,23                │
│                              │
│ NAV start  EUR 27.380        │
│ NAV end    EUR 33.391        │
│ Net flows  EUR 0,00          │
│                              │
│ Adjusted for cash flows      │
└──────────────────────────────┘

┌──────────────────────────────┐
│ RETURNS                  (?) │
│ ROI        21,95%            │
│ TWRR cum   27,11%            │
│ MWRR cum   35,13%            │
│ MWRR ann   24,74%            │
└──────────────────────────────┘
```

***

# Help icon / docs

Dato che le pagine `NAV`, `Book Value`, `P&L` non esistono ancora, per ora farei così:

```text
(?) su Net Worth → tooltip locale, niente link wiki per ora
(?) su Period P&L → tooltip locale, niente link wiki per ora
(?) su Returns → link alla pagina performance metrics / ROI-TWRR-MWRR se già esiste
```

Poi quando scriviamo le pagine dedicate, aggiorniamo i link.

***

# Decisione proposta

Per ora implementerei:

```text
Card 1: Net Worth
- NAV
- Book Value con barra e numero
- NAV con barra e numero
- Cash
- Unrealized Gain/Loss

Card 2: Period P&L
- P&L monetario
- NAV start
- NAV end
- Net flows
- niente percentuale

Card 3: Returns
- ROI
- TWRR cumulative
- MWRR cumulative
- MWRR annualized
```

Così evitiamo duplicazioni tra `P&L %` e `ROI`.
