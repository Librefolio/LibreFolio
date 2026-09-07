# AI Export — Riferimento funzionale compatto

**Data fotografia**: 28 luglio 2026
**Scopo**: review funzionale; il codice corrente è la source of truth.
**Catalogo**: 19 task × 3 livelli = 57 profili.

## 1. Modello mentale

```text
Pagina LibreFolio
  → contesto finanziario + opzioni UI
  → POST /api/v1/ai-export/snapshot
  → snapshot backend tipizzato/versionato
  → renderer frontend sicuro
  → testo copiato negli appunti
  → nessuna chiamata LLM fatta da LibreFolio
```

Il backend possiede:

- calcoli finanziari;
- FIFO runtime;
- prezzi/FX;
- segnali e annotazioni;
- selezione compact;
- sampling;
- coverage, semantics e provenance;
- applicabilità e accesso broker.

Il frontend possiede:

- label e descrizioni localizzate;
- scelta Snapshot/analisi;
- istruzioni per il modello;
- response contract;
- lingua risposta;
- note utente;
- serializzazione YAML/Markdown;
- clipboard e memoria UI.

## 2. Pagine, scope e voci visibili

| Pagina | Scope request | Memoria | Voci visibili |
|---|---|---|---|
| Dashboard | Portfolio + filtro broker attivo | `portfolio` | Data Snapshot + 7 analisi Portfolio |
| Broker Detail | singolo broker accessibile | `broker:{id}` | Data Snapshot + 4 analisi Broker |
| Asset Detail | singolo asset; broker scope opzionale | `asset:{id}` | Data Snapshot + Trend + Position + Drawdown |
| FX Detail | coppia base/quote; broker scope opzionale | `fx:{canonical_slug}` | Data Snapshot + Trend + Conversion Timing |

### 2.1 Data Snapshot non è un superset

Data Snapshot usa un task reale in modalità `data_only`:

| Pagina | Task backend usato |
|---|---|
| Dashboard | `portfolio_description` |
| Broker | `broker_review` |
| Asset | `asset_snapshot` |
| FX | `fx_trend_review` |

Conseguenza: Snapshot esporta i dati previsti da quel profilo, non ogni dato
possibile del dominio.

Esempi:

- Dashboard Snapshot non include le righe FIFO per-lot: serve
  `portfolio_fifo_lot_review`;
- Broker Snapshot può includere il riepilogo FIFO aggregato, ma non richiede
  `fifo_lots`;
- Asset Snapshot non equivale a Position Review;
- FX Snapshot non include `exposure_links`.

### 2.2 Task presenti nel catalogo ma nascosti nella pagina

- Asset: `asset_snapshot` è nascosto come analisi perché già usato da Data
  Snapshot; `asset_pac_timing_context` è nascosto per decisione prodotto.
- FX: `fx_exposure_impact` è nascosto per decisione prodotto.

Restano profili backend validi e versionati.

## 3. Parametri

### 3.1 Parametri inviati al backend

| Parametro | Effetto |
|---|---|
| `domain` | `portfolio`, `broker`, `asset`, `fx` |
| `task` | task reale allow-listed |
| `detail_level` | `compact`, `standard`, `full` |
| `date_range` | intervallo finanziario: performance, contributi, redditi, prezzi/ritorni selezionati |
| `technical_window` | intervallo tecnico indipendente; termina sempre a `snapshot_as_of` |
| `target_currency` | valuta di valorizzazione/export |
| `broker_ids` | filtro Portfolio/Asset/FX, se esplicito |
| `broker_id` | Broker Detail |
| `asset_id` | Asset Detail |
| `base_currency`, `quote_currency` | FX Detail |

`user_id` non arriva mai dal browser: deriva dall'autenticazione.

### 3.2 Parametri frontend

| Parametro | Comportamento |
|---|---|
| Analisi | Snapshot sintetico oppure task reale |
| Detail | default `standard` |
| Finestra tecnica | default `3M`; `6M`, `1Y`, oppure Custom |
| Custom | numero positivo + unità `giorni/settimane/mesi/anni` |
| Note | solo analisi che le supportano; mai esportate in Snapshot |
| Lingua | sempre derivata dalla lingua UI |
| Render mode | Snapshot → `data_only`; analisi → `full_prompt` |
| Web research | sempre `false`; controllo non esposto |

Il Custom replica il DateRangePicker:

- il badge **Personalizzato** diventa esso stesso editor;
- input numerico inline;
- unità tramite `SimpleSelect` LibreFolio;
- unità corta localizzata: D/G/J, W/S, M, Y/A;
- nessun `<select>` nativo.

UI: `1..999`; il frontend converte la durata in date esatte prima della request.
Mesi/anni usano sottrazione di calendario con clamp del giorno
(`31 marzo - 1 mese = 28/29 febbraio`).

## 4. Detail level e finestra tecnica

### 4.1 Overlay condivisi

| Livello | Entità | Serie | Eventi max |
|---|---|---|---:|
| Compact | aggregati completi + selezione task-specifica | nessuna | 10 |
| Standard | tutte le entità/contribution applicabili | 7 daily recenti + max 8 weekly precedenti | 40 |
| Full | tutte le entità/contribution applicabili | 7 daily recenti + weekly sull'intera finestra tecnica | 120 |

Sempre:

- eventi deduplicati;
- precisione applicata dopo sampling;
- nessun top-N implicito in Standard/Full.

### 4.2 Cosa cambia scegliendo 3M/6M/1Y/Custom

La finestra tecnica:

- cambia il periodo osservabile per segnali, stati e annotazioni;
- cambia il numero di weekly esportati in Full;
- può cambiare gli eventi tecnici disponibili entro il limite;
- può cambiare coverage e disponibilità degli indicatori;
- estende anche il calculation range necessario al warm-up;
- non modifica `date_range`, P&L, contributi, redditi o normalized return
  finanziario.

Il calculation range può iniziare prima della finestra tecnica per fornire il
warm-up richiesto da EMA200 e indicatori simili; i valori visibili vengono poi
tagliati alla finestra richiesta.

### 4.3 Interazione detail × finestra

| Caso | Effetto della finestra |
|---|---|
| Compact con tecnica | niente serie, ma cambiano calcolo/stato latest e possibili eventi |
| Standard con tecnica | calcolo più ampio; output resta limitato a max 15 punti per serie |
| Full con tecnica | output cresce con i weekly dell'intera finestra |
| Technical depth `NONE` | nessun effetto sui dati esportati; la finestra resta solo nei metadata |

Task/detail dove la finestra è inerte:

- Portfolio FIFO: Compact, Standard, Full;
- Portfolio Performance Attribution: Compact;
- Portfolio Income Review: Compact;
- Portfolio Description: Compact;
- Broker Cost Efficiency: Compact;
- Broker FIFO: Compact.

La UI oggi mostra comunque il controllo: possibile punto di feedback
`mostrare sempre` vs `disabilitare/nascondere quando inerte`.

### 4.4 La finestra FIFO non è quella tecnica

I lotti chiusi recenti usano sempre:

```text
snapshot_as_of - 3 mesi di calendario
```

Questo cutoff FIFO non cambia selezionando 6M, 1Y o Custom.

## 5. Come viene composto il testo copiato

### 5.1 Analisi (`full_prompt`)

Ordine esatto:

1. `## Task Instructions`
   - regole anti prompt-injection condivise;
   - objective specifico;
   - step numerati specifici.
2. `## Response Contract`
   - ID/versione;
   - sezioni obbligatorie in ordine.
3. `## Snapshot Data`
   - YAML tipizzato.
4. `## Domain Notes and Descriptions`
   - solo se presenti.
5. `## Optional User Notes`
   - solo se ammesse e non vuote.
6. `## Response Language`
   - lingua derivata dalla UI.

### 5.2 Data Snapshot (`data_only`)

Contiene soltanto:

1. Snapshot Data;
2. eventuali Domain Notes.

Non contiene:

- istruzioni;
- response contract;
- note utente;
- riga della lingua;
- web research.

### 5.3 Confine di sicurezza

- nomi asset/broker, descrizioni e note sono dati, non istruzioni;
- YAML deterministico;
- fence Markdown dimensionate per non essere chiuse da testo avversariale;
- valori non finiti rifiutati;
- technical data dichiarata descrittiva, non segnale buy/sell;
- mismatch task/profile/contract → fail closed, nessun fallback.

Le istruzioni e i titoli del contract sono in inglese; la lingua richiesta per
la risposta segue EN/IT/FR/ES dell'interfaccia.

## 6. Bundle tecnici e parametri

I task non scelgono indicatori arbitrari: riusano bundle statici allow-listed.

### 6.1 Asset / Portfolio / Broker

| Bundle | Indicatori |
|---|---|
| Compact | EMA(20/50/200, offset 0), RSI(14, 30/70), MACD(12/26/9), Bollinger(20, 2), NATR(14), MFI(14, 20/80; volume richiesto) |
| Standard | Compact + ADX(14), Donchian(20), StochRSI(14, D=3, 20/80), OBV(volume richiesto); output sampled |
| Full | EMA20/50/200, SMA50/200, KAMA20, Aroon25, ADX14, Donchian20, RSI14, MACD12/26/9, PPO12/26/9, ROC20, StochRSI14/3, CCI20, Bollinger20/2, ATR14, NATR14, MFI14, OBV |

Annotazioni core:

- prezzo/EMA20;
- EMA20/50;
- EMA50/200;
- RSI 30/70;
- MACD/signal e histogram/0;
- MFI 20/80;
- prezzo/Bollinger lower/middle/upper.

Standard/Full aggiungono:

- ADX/25;
- StochRSI K/D e 20/80;
- prezzo/Donchian lower/middle/upper.

### 6.2 FX

| Bundle | Indicatori |
|---|---|
| Compact | EMA20/50/200, RSI14 30/70, PPO12/26/9, Bollinger20/2 |
| Standard | Compact + ROC20, StochRSI14/3, KAMA20; output sampled |
| Full | EMA20/50/200, SMA50/200, KAMA20, RSI14, MACD12/26/9, PPO12/26/9, ROC20, StochRSI14/3, Bollinger20/2 |

Annotazioni core:

- rate/EMA20;
- EMA20/50;
- EMA50/200;
- RSI 30/70;
- PPO/signal e histogram/0;
- rate/Bollinger lower/middle/upper.

Standard/Full aggiungono ROC/0 e StochRSI K/D + 20/80.

Un nuovo Signal Plugin non entra automaticamente nell'AI Export: serve modifica
esplicita del bundle/contratto.

## 7. Dashboard / Portfolio

### Data Snapshot

- task sottostante: `portfolio_description`;
- dati: summary, posizioni, allocazioni, cash context; contribution/tecnica
  secondo profilo/detail;
- Compact: 10 maggiori NAV;
- tecnica C/S/F: Ø / standard summary / sampled standard;
- nessun prompt.

### Recurring Investment Plan — `pac_planning`

- focus: scenari PAC neutrali, vincoli, capitale aggiuntivo e trade-off;
- dati richiesti: summary, posizioni, contribution, unallocated/other effects,
  allocazioni, cash, coverage/semantics;
- Compact: 6 maggiori NAV + 6 minori posizioni non-zero;
- tecnica C/S/F: latest breadth / standard summary / full;
- note sì; web supportato dal contratto ma UI off;
- risposta:
  `Portfolio Summary → Allocation and Concentration → Areas That May Deserve
  Additional Capital → Technical Context → Two or Three PAC Scenarios →
  Assumptions/Missing Information → Optional Web Context`.

### Portfolio Rebalancing — `rebalancing`

- focus: confronto allocazione attuale vs target fornito dall'utente;
- non inventa target o tolleranze;
- Compact: 12 maggiori NAV;
- tecnica: latest breadth / standard summary / full;
- risposta:
  `Current Facts → Target/Tolerance Inputs → Measured Gaps → Rebalancing
  Pathways → Cash-Flow-Only → Costs/Tax Caveats → Assumptions → Optional Web`.

### Performance Attribution — `performance_attribution`

- richiede dati nel selected range;
- separa contributori positivi/negativi, realized/unrealized, income/costi/tax;
- Compact: 5 migliori + 5 peggiori `period_pnl_amount`;
- tecnica: Ø / latest states / sampled standard;
- risposta:
  `Absolute Result → Positive → Negative → Realized vs Unrealized →
  Income/Costs/Taxes → TWRR/MWRR/ROI → Cash Flow Effect`.

### Portfolio Income Review — `income_review`

- focus: redditi e concentrazione nel selected range;
- Compact: 10 maggiori `period_income_amount`;
- tecnica: Ø / latest states / sampled standard;
- risposta:
  `Income Summary → Contributors → Concentration → Fees/Taxes/Net Cash Flow →
  Reinvestment/Spending → Data Gaps → Neutral Options`.

### Portfolio FIFO Lot Review — `portfolio_fifo_lot_review`

- scope: filtro broker attivo Dashboard;
- tutti i lotti aperti/parziali + chiusi negli ultimi 3 mesi;
- Compact: 7 open/partial per residual cost + 3 closed recenti, backfill a 10;
- Standard/Full: tutte le righe eleggibili;
- tecnica: Ø / Ø / Ø;
- risposta:
  `Scope/Eligibility → Open/Partial Table → Recently Closed Table →
  Residual Cost/Value → Realized/Unrealized/Net → Concentration Asset/Broker →
  Income/Fees/Taxes → Limits/Questions`.

### Technical Breadth — `technical_breadth`

- no note utente;
- aggregati calcolati sull'intero universo tecnico eleggibile;
- Compact: 10 eventi recenti pesati NAV;
- tecnica: breadth only / standard / full;
- risposta:
  `Coverage → Long-Term Breadth → Short/Medium Breadth → Momentum →
  Volatility → Recent Events → Universe Limits`.

### Portfolio Description — `portfolio_description`

- descrizione fattuale e neutrale;
- Compact: 10 maggiori NAV;
- tecnica: Ø / standard summary / sampled standard;
- risposta:
  `Snapshot → Allocation/Diversification → Concentration → Performance/Cash
  Flow → Technical Context → Data Quality/Coverage → Assumptions/Questions`.

## 8. Broker Detail

### Data Snapshot

- task: `broker_review` in `data_only`;
- scope singolo broker;
- Compact: 10 maggiori NAV;
- tecnica: breadth / standard / full;
- non include obbligatoriamente le righe FIFO per-lot.

### Broker Review — `broker_review`

- holdings, cash, capital, performance, income, costi, attività;
- Compact: 10 maggiori NAV;
- tecnica: breadth / standard / full;
- risposta:
  `Broker Snapshot → Holdings/Cash → Performance/Contributions →
  Concentration → Costs/Taxes/Income → FIFO/Activity → Coverage → Questions`.

### Broker Cost Efficiency — `broker_cost_efficiency`

- fee e tax separate, rapporti solo con denominatori disponibili;
- Compact: 10 maggiori `abs(period_fees_taxes_amount)`;
- tecnica: Ø / latest states / sampled standard;
- risposta:
  `Cost Snapshot → Fees/Taxes by Source → Concentration → Relative to Activity
  and Assets → Income Offset → Data Gaps → Neutral Options`.

### Broker Concentration Context — `broker_concentration_context`

- concentrazione posizioni, asset type, settore, geografia, valute, cash;
- Compact: 10 maggiori NAV;
- tecnica: breadth / standard / full;
- risposta:
  `Broker Snapshot → Position Concentration → Dimension Concentration →
  Cash → Technical Breadth → Coverage/Selection → Diversification Questions`.

### Broker FIFO Lot Review — `broker_fifo_lot_review`

- stesso contratto righe FIFO condiviso, limitato al broker;
- Compact 7+3; Standard/Full tutte le righe eleggibili;
- tecnica: Ø / latest states / sampled standard;
- response contract v1;
- risposta:
  `Scope/Eligibility → Open/Partial Table → Recently Closed Table →
  Residual Cost/Value → Realized/Unrealized → Lot Age/Concentration →
  Income/Fees/Taxes → Limits/Questions`.

## 9. Asset Detail

### Data Snapshot

- task: `asset_snapshot` data-only;
- identity obbligatoria; market/tecnica/eventi se disponibili;
- non equivale a Position Review;
- tecnica: latest states / standard / full.

### Asset Trend Analysis — `asset_trend_analysis`

- focus: trend long/medium/short, momentum, volatilità, drawdown, eventi;
- tecnica: latest trend/momentum/volatility / standard with series / full;
- risposta:
  `Snapshot Facts → Long-Term → Short/Medium → Momentum →
  Volatility/Drawdown → Recent Events → Optional Web → Assumptions/Limits`.

### Position Review — `position_review`

- applicabile solo con quantità aperta positiva nello scope;
- dati: posizione corrente; market, lot summary e valuation fallback se presenti;
- tecnica: latest states / standard / full;
- web non supportato;
- risposta:
  `Position → Cost Basis/Valuation → Realized/Unrealized → FIFO →
  Income/Fees/Taxes → Portfolio Role/Concentration → Risks/Limits/Questions`.

### Drawdown and Recovery — `drawdown_recovery`

- richiede almeno 2 osservazioni e un massimo precedente misurabile;
- tecnica: latest drawdown context / standard with recovery events / full;
- risposta:
  `Snapshot → Peak-to-Trough → Recovery Progress → Trend/Momentum →
  Volatility/Events → Historical Episodes → Optional Web →
  Assumptions/Limits`.

### Nascosto: Asset PAC Timing Context

- profilo valido ma non mostrato;
- tecnica: latest neutral context / standard with sampling / full;
- chiede scenari temporali neutrali, non timing deterministico.

## 10. FX Detail

### Data Snapshot

- task: `fx_trend_review` data-only;
- identity + current rate obbligatori;
- sampled rates/extrema/volatility/return/tecnica se disponibili;
- non include exposure links.

### FX Trend Review — `fx_trend_review`

- direzione quote-per-base esplicita;
- tecnica: latest rate/states / standard / full;
- risposta:
  `Snapshot → Direction/Magnitude → Trend State → Momentum/Volatility →
  Recent Events → Optional Web → Assumptions/Limits`.

### FX Conversion Timing Context — `fx_conversion_timing_context`

- scenari di conversione condizionali, nessun point forecast;
- tecnica: latest trend/volatility / standard with sampling / full;
- risposta:
  `Snapshot → Current Rate Context → Trend/Momentum →
  Volatility/Drawdown → Neutral Timing Scenarios → Optional Web →
  Assumptions/Limits`.

### Nascosto: FX Exposure Impact

- richiede cash o posizione collegabile;
- linkage: cash currency, trading currency, valuation currency;
- non è look-through exposure;
- tecnica: latest exposure/states / standard / full.

## 11. FIFO per-lot

Ogni riga esporta:

- asset id/nome/simbolo;
- opening broker id/nome;
- opening date e closing date;
- LONG/SHORT;
- open/partial/closed;
- opening unit price;
- quantità original/open/realized;
- original cost e residual cost basis;
- proceeds;
- open value;
- realized/unrealized/total/net P&L;
- income, fees, taxes;
- value source;
- state tags.

Non esporta:

- `lot_id`;
- `opening_transaction_id`;
- custody history;
- event history;
- value/return/price timeline;
- andamento giornaliero del lotto.

Gli asset ormai chiusi vengono scoperti anche dallo storico transazioni, non
soltanto dalle holdings correnti.

## 12. Versioning, errori e privacy

- catalog schema v1;
- snapshot schema v1;
- profile version v1;
- 57 lookup esatti, nessun default server;
- tutti i response contract sono v1;
- frontend e backend devono concordare su task/detail/profile/contract/support flags.

Errori tipizzati:

| HTTP | Codice |
|---:|---|
| 403 | `broker_access_denied` |
| 404 | `entity_not_found` |
| 409 | `task_not_applicable` |
| 422 | `unsupported_profile` / validazione request |
| 503 | `snapshot_source_failure` |

Clipboard:

- `ClipboardItem(Promise<Blob>)` quando disponibile;
- fallback `writeText`/`execCommand`;
- stesso prompt V2, nessun fallback legacy.

Il testo può contenere dati finanziari sensibili; LibreFolio lo copia soltanto e
non lo invia.

## 13. Memoria e dimensione export

Memoria browser-local per utente/contesto:

- task;
- detail;
- render mode;
- note raw;
- finestra tecnica.

La lingua non viene fidata dalla memoria: viene ricalcolata dalla UI. Le note
restano memorizzate passando a Snapshot, ma vengono rimosse strutturalmente
dall'export.

Dimensione:

- backend: caratteri JSON canonico + stima `chars_div_4_v1`;
- frontend: caratteri prompt finale UTF-16 + `ceil(chars/4)`;
- warning da 8.000 token;
- large da 16.000;
- nessun troncamento automatico.

## 14. Punti per feedback strutturato

1. Data Snapshot deve restare task-specifico o diventare un superset del dominio?
2. Finestra tecnica: mostrarla sempre o disabilitarla quando il profilo è `NONE`?
3. Standard con 1Y/Custom deve restare limitato a 7 daily + 8 weekly?
4. Full deve davvero crescere con tutti i weekly della finestra?
5. Il cutoff FIFO recenti deve restare fisso 3 mesi o diventare parametro separato?
6. `asset_pac_timing_context` e `fx_exposure_impact` devono restare nascosti?
7. Web research: eliminare definitivamente plumbing/section oppure riesporre il controllo?
8. I prompt devono mantenere istruzioni/heading inglesi con sola risposta localizzata?
9. La finestra tecnica deve essere ricordata per pagina, come ora, o per task?
10. Data Snapshot Broker/Dashboard deve includere anche le righe FIFO per-lot?

## Source files

- `backend/app/schemas/ai_export.py`
- `backend/app/services/ai_export/models.py`
- `backend/app/services/ai_export/profiles/`
- `backend/app/services/ai_export/assemblers/`
- `backend/app/services/ai_export/technical.py`
- `frontend/src/lib/features/ai-export/`
- `frontend/src/routes/(app)/dashboard/+page.svelte`
- `frontend/src/routes/(app)/brokers/[id]/+page.svelte`
- `frontend/src/routes/(app)/assets/[id]/+page.svelte`
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte`
