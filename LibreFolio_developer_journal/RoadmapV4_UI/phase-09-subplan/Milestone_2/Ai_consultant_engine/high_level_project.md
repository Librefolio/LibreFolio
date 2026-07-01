# LibreFolio — Architettura AI Portfolio Export MVP

## 1. Obiettivo

Realizzare una prima versione frontend-only di esportazione dati verso un AI advisor esterno.

L’utente deve poter copiare negli appunti:

```text
1. Full AI Prompt
2. Portfolio Data Only
```

Il caso d’uso principale è:

```text
supportare l’utente durante il PAC mensile long-term
```

Non è un sistema di trading automatico, né un consulente finanziario integrato.  
L’AI esterna riceve un dossier strutturato e produce una valutazione neutrale.

***

## 2. Principi architetturali

### 2.1 Frontend-only per MVP

Per questa prima versione:

```text
backend = fonte dati già disponibili
frontend = composizione prompt + calcolo segnali tecnici
```

Motivi:

```text
- i dati portfolio arrivano già dalle API esistenti
- gli indicatori tecnici sui prezzi esistono già lato frontend
- non serve introdurre endpoint AI/MCP ora
- il sistema deve essere sperimentale, rapido ed evolvibile
```

Eventuali campi non disponibili oggi non vanno inventati.

Regola:

```text
se un dato non esiste → omettere
se un dato è parzialmente disponibile → indicare limitation/data_quality
```

***

### 2.2 Backend authoritative, frontend renderer

Il frontend può:

```text
- comporre testo
- formattare dati
- campionare serie tecniche
- calcolare indicatori tecnici già supportati
- rilevare eventi tecnici/cross
```

Il frontend non deve calcolare:

```text
NAV
P&L core
cost basis
WAC
cash pools
performance portfolio
contribution monetaria
```

Questi restano responsabilità backend.

***

### 2.3 Lingua

Il prompt e le chiavi dati principali possono essere in inglese perché gli LLM interpretano meglio istruzioni tecniche in inglese.

La lingua della risposta va indicata alla fine:

```text
Please provide your answer in: Italian.
```

La lingua target deriva dalla lingua impostata nel frontend.

***

## 3. Output previsti

## 3.1 Full AI Prompt

Contiene:

```text
- istruzioni per l’AI
- metodologia di calcolo
- dati portfolio
- dati tecnici
- richiesta di analisi
- lingua di risposta
```

Formato:

```text
Markdown + YAML + tabelle Markdown per serie tecniche
```

***

## 3.2 Portfolio Data Only

Contiene solo dati strutturati, senza istruzioni estese.

Formato:

```text
Markdown + YAML
```

Serve per utenti che vogliono costruire un proprio prompt manualmente.

***

## 4. Struttura file consigliata

Proposta modulare:

```text
frontend/src/lib/features/ai-export/
├── types.ts
├── aiExportBuilder.ts
├── aiPromptRenderer.ts
├── aiDataRenderer.ts
├── aiExportClipboard.ts
├── technical/
│   ├── technicalExportBuilder.ts
│   ├── signalCrossDetection.ts
│   ├── technicalSampling.ts
│   └── technicalEvents.ts
└── templates/
    ├── promptTemplate.ts
    └── languageMap.ts
```

Responsabilità:

```text
types.ts
  Definizione tipi interni AiPortfolioExport.

aiExportBuilder.ts
  Converte report/stores frontend in AiPortfolioExport.

aiPromptRenderer.ts
  Produce il Full AI Prompt Markdown.

aiDataRenderer.ts
  Produce Data Only Export.

aiExportClipboard.ts
  Gestisce copia clipboard + feedback UI.

technicalExportBuilder.ts
  Costruisce snapshot tecnico, serie tecniche, eventi.

signalCrossDetection.ts
  Funzioni generiche per rilevare incroci tra serie.

technicalSampling.ts
  Campionamento serie: ultimi giorni daily + storico weekly.

technicalEvents.ts
  Mappa cross generici in eventi semantici.

promptTemplate.ts
  Template testuale inglese.

languageMap.ts
  Mappa locale frontend → lingua risposta.
```

***

## 5. Modello dati interno

Tipo concettuale:

```ts
AiPortfolioExport
```

Sezioni previste:

```text
metadata
methodology
portfolio_snapshot
current_allocation
positions
broker_summary
technical_context
data_quality
```

Solo campi realmente disponibili oggi.

***

## 6. Esempio struttura dati

```yaml
metadata:
  generated_at: "2026-07-01T10:34:00+02:00"
  base_currency: EUR
  selected_range:
    from: "2026-04-01"
    to: "2026-07-01"
  response_language: Italian
  export_purpose: "monthly PAC long-term allocation support"

methodology:
  portfolio_style: "long_term_monthly_accumulation"
  valuation_policy:
    primary: "market_price"
    fallback: "last_visible_buy_price"
    missing_policy: "flag_or_omit"
  wac_policy:
    used_for:
      - "cost_basis"
      - "unrealized_pnl"
      - "realized_pnl"
    not_used_as_price: true
  technical_indicators_policy:
    purpose: "descriptive_context_only"
    not_trading_signals: true
```

***

## 7. Portfolio snapshot

Il frontend deve esportare solo i dati già disponibili dal report.

Esempio:

```yaml
portfolio_snapshot:
  nav: 124500.00
  market_value: 110000.00
  cash: 14500.00
  book_value: 103000.00
  deposited_capital: 98000.00
  total_pnl: 26500.00
  unrealized_pnl: 7000.00
```

Se alcuni campi non sono presenti:

```text
omettere il campo
```

***

## 8. Allocazione corrente

Includere più livelli, se disponibili:

```yaml
current_allocation:
  by_asset:
    - name: "VWCE"
      symbol: "VWCE"
      currency: EUR
      asset_type: ETF
      allocation_percent: 18.2

  by_asset_type:
    ETF: 63.4
    Bond: 28.8
    Cash: 0.2

  by_currency:
    EUR: 74.0
    USD: 24.0

  by_broker:
    Directa: 68.2
    Recrowd: 22.1
```

Questa sezione è centrale per il PAC mensile.

***

## 9. Positions

Preferire dati per posizione, quando disponibili:

```text
position = broker + asset
```

Esempio:

```yaml
positions:
  - broker: Directa
    name: "VWCE"
    symbol: "VWCE"
    asset_type: ETF
    currency: EUR
    quantity: 100
    market_value: 11420.00
    nav_weight_percent: 18.2
    valuation_source: MARKET_PRICE
    wac: 102.50
    cost_basis: 10250.00
    unrealized_pnl: 1170.00
    unrealized_pnl_percent: 11.41
```

***

## 10. Broker summary

Utile ma sintetico.

Includere solo se derivabile con dati disponibili.

```yaml
broker_summary:
  - broker: Directa
    nav_weight_percent: 68.2
    cash: 1200.00
    main_exposure: "ETF / listed assets"

  - broker: Recrowd
    nav_weight_percent: 22.1
    cash: 300.00
    main_exposure: "Crowdfunding / income assets"
```

Non serve esportare una serie storica giornaliera per broker nell’MVP.

***

# 11. Technical context

## 11.1 Scopo

Il contesto tecnico serve per aiutare l’AI a valutare il momento del PAC mensile.

Non deve trasformare l’analisi in trading.

Il prompt deve dichiarare:

```text
Technical indicators are descriptive context only.
Do not treat them as deterministic buy/sell signals.
```

***

## 11.2 Asset inclusi

Includere solo asset con price history reale sufficiente.

Escludere o marcare come unavailable:

```text
- asset manuali
- crowdfund senza prezzi di mercato
- asset valutati solo via last_buy_price fallback
- asset con dati insufficienti
```

Esempio:

```yaml
technical_context_unavailable:
  - asset: "EX ALBERGO VELA"
    reason: "No reliable market price history; valuation uses fallback price."
```

***

## 11.3 Finestra tecnica

Default:

```text
technical_window = 3M
```

Motivo:

```text
- utile per PAC mensile
- meno rumoroso di 1M
- più attuale di 6M/1Y
```

La serie tecnica deve avere:

```text
- ultimi 7 punti validi daily
- punti precedenti campionati weekly dentro la finestra 3M
```

***

## 11.4 Serie percentuale normalizzata

Per confrontare asset con prezzi unitari diversi, includere:

```text
normalized_return_pct
```

Regola:

```text
0% = prezzo base a inizio finestra tecnica 3M
```

Formalmente:

```text
normalized_return_pct(t) =
  close(t) / base_price - 1
```

Dove:

```text
base_price = prezzo valido a technical_window_start
```

Se non esiste prezzo a inizio finestra:

```text
base_price = primo prezzo valido dopo technical_window_start
technical_window_complete = false
```

Mai usare `0` per dati mancanti.

Usare:

```text
null / NaN / —
```

***

## 11.5 Esempio metadata tecnica

```yaml
technical_metadata:
  asset: "CHIP"
  technical_window: "3M"
  technical_window_start: "2026-04-01"
  normalized_return_base_date: "2026-04-01"
  normalized_return_base_price: 145.20
  technical_window_complete: true
```

Asset con storico incompleto:

```yaml
technical_metadata:
  asset: "NEWETF"
  technical_window: "3M"
  technical_window_start: "2026-04-01"
  first_available_price_date: "2026-05-15"
  normalized_return_base_date: "2026-05-15"
  normalized_return_base_price: 100.00
  technical_window_complete: false
  normalized_return_base_reason: "first_available_price_after_window_start"
  comparability_note: "Return series starts later than other assets; compare with caution."
```

***

## 11.6 Serie tecnica in Markdown table

Per ogni asset tecnico incluso:

```markdown
### Technical series — CHIP

| Date | Close | Return from 3M base % | RSI14 | MACD Hist | EMA20 | EMA50 | EMA200 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-06-25 | 168.20 | 15.84 | 59.1 | 0.08 | 166.90 | 163.80 | 142.10 |
| 2026-06-26 | 169.10 | 16.46 | 60.3 | 0.10 | 167.30 | 164.10 | 142.35 |
| 2026-07-01 | 173.40 | 19.42 | 64.2 | 0.18 | 170.10 | 165.40 | 142.80 |
```

La tabella contiene sia:

```text
close assoluto
return percentuale comparabile
indicatori tecnici
```

***

# 12. Cross detection generico

Serve una funzione generica che lavori su:

```text
serie vs serie
serie vs soglia numerica
```

## 12.1 Definizione

Date due serie temporali:

```text
A(t)
B(t)
```

definire:

```text
delta(t) = A(t) - B(t)
```

Cross above:

```text
delta(t-1) <= 0
delta(t) > 0
```

Cross below:

```text
delta(t-1) >= 0
delta(t) < 0
```

Con tolleranza:

```text
epsilon
```

Se:

```text
abs(delta) <= epsilon
```

allora delta è considerato zero.

***

## 12.2 Input concettuale

```ts
type TimeSeriesPoint = {
  date: string;
  value: number | null;
};

type CrossDetectionOptions = {
  epsilon?: number;
  minGapDays?: number;
  includeTouch?: boolean;
  direction?: 'both' | 'above' | 'below';
  labelA?: string;
  labelB?: string;
};
```

Firma concettuale:

```ts
detectCrosses(
  seriesA: TimeSeriesPoint[],
  seriesBOrThreshold: TimeSeriesPoint[] | number,
  options?: CrossDetectionOptions
): CrossEvent[]
```

***

## 12.3 Output concettuale

```ts
type CrossEvent = {
  date: string;
  event: 'CROSSED_ABOVE' | 'CROSSED_BELOW';
  seriesA: string;
  seriesB: string;
  previousDate: string;
  previousA: number;
  previousB: number;
  currentA: number;
  currentB: number;
  previousDelta: number;
  currentDelta: number;
};
```

***

## 12.4 Regole su null/NaN

La funzione deve:

```text
- ignorare punti null/NaN
- non generare cross nel passaggio null → valore
- richiedere due punti validi consecutivi
- allineare le serie per data
```

***

## 12.5 Eventi derivabili

La stessa funzione può generare:

```text
close vs EMA20
close vs EMA50
close vs EMA200
EMA20 vs EMA50
MACD vs signal
MACD histogram vs 0
RSI14 vs 70
RSI14 vs 30
```

Esempio YAML:

```yaml
technical_events:
  - asset: "CHIP"
    date: "2026-06-18"
    event: "PRICE_CROSSED_ABOVE_EMA20"
    details:
      close: 169.20
      ema20: 168.90
      return_from_3m_base_pct: 16.53

  - asset: "VWCE"
    date: "2026-06-10"
    event: "MACD_HISTOGRAM_TURNED_POSITIVE"
```

Gli eventi sono opzionali e derivati.

La fonte primaria resta:

```text
snapshot tecnico + serie tecnica
```

***

# 13. Prompt full — struttura

Il Full AI Prompt deve essere in inglese.

Esempio struttura:

````markdown
# LibreFolio Portfolio AI Export

You are a neutral financial analysis assistant.

The portfolio is managed with a long-term monthly accumulation strategy.
The goal is to support the user's next monthly PAC allocation decision.

Do not provide deterministic buy/sell instructions.
Do not treat technical indicators as trading signals.
Use technical indicators only as descriptive context.

If you have web access, research the assets, sectors, or themes that appear most relevant, concentrated, volatile, or technically hot.
Clearly separate conclusions based on the provided portfolio data from conclusions based on web research.
If you do not have web access, state it and rely only on the provided data.

## Methodology

```yaml
...
````

## Portfolio Data

```yaml
...
```

## Technical Series

...

## Requested Analysis

Please:

1. Summarize the portfolio.
2. Evaluate current allocation and concentration.
3. Identify underweight and overweight areas.
4. Give neutral monthly PAC allocation scenarios.
5. Use technical context only as supporting evidence.
6. Highlight data quality limitations.
7. Ask clarifying questions before suggesting strong actions.

Please provide your answer in: Italian.

````

---

# 14. Richiesta web research

Il prompt deve includere una richiesta condizionale:

```text
If you have web access, research relevant assets/sectors.
If you do not have web access, state it and do not invent external context.
````

Scopo:

```text
motiva eventuali asset “caldi” con contesto recente
senza forzare allucinazioni
```

***

# 15. Azioni UI MVP

Aggiungere due azioni:

```text
Copy full AI prompt
Copy portfolio data only
```

Posizione consigliata:

```text
dashboard action menu / overflow menu vicino alle azioni principali
```

Feedback:

```text
Copied to clipboard
Copy failed
```

***

# 16. Data only export

Esempio:

````markdown
# LibreFolio Portfolio Data Export

```yaml
metadata:
  generated_at: "2026-07-01T10:34:00+02:00"
  base_currency: EUR
  response_language: Italian

portfolio_snapshot:
  ...

current_allocation:
  ...

positions:
  ...

technical_context:
  ...
````

````

Nessuna checklist lunga.

---

# 17. Validazioni e edge case

Da verificare:

```text
- portfolio senza asset
- portfolio solo cash
- asset senza price history
- asset con storico inferiore a 3M
- indicatori non calcolabili per dati insufficienti
- prompt troppo lungo
- clipboard non disponibile
- browser senza permesso clipboard
- lingua frontend diversa da italiano
````

***

# 18. Definition of Done

La feature è pronta quando:

```text
- esistono due azioni: full prompt e data only
- output è Markdown + YAML
- prompt full contiene istruzioni inglesi e lingua risposta finale
- dati inesistenti non vengono inventati
- technical series usa 3M come base comparabile
- ultimi 7 punti sono daily
- storico precedente è campionato weekly
- valori mancanti sono null/—, non zero
- cross detection è generica
- eventi tecnici sono YAML
- asset senza price history vengono esclusi o marcati unavailable
- svelte-check pulito
- i18n audit pulito se vengono aggiunte label UI
```

***

# 19. Sintesi finale

Architettura MVP:

```text
Frontend AI Export Generator
  prende dati portfolio già disponibili
  calcola segnali tecnici frontend-side
  costruisce AiPortfolioExport
  renderizza:
    - Full AI Prompt
    - Data Only
  copia negli appunti
```

Formato:

```text
Markdown + YAML
```

Serie tecniche:

```text
Markdown tables
Close assoluto + Return % normalizzato da 3M
```

Eventi tecnici:

```text
YAML
```

Prompt:

```text
inglese
risposta nella lingua frontend
```

Obiettivo prodotto:

```text
aiutare l’utente long-term a ragionare sul PAC mensile,
non generare segnali di trading deterministici
```
