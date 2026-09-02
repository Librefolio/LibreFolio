# Phase 0 — AI Export Migration Equivalence Report

**Stato**: ✅ COMPLETATO
**Data**: 26 luglio 2026

← [Piano implementativo](plan-phase00AiExportBackendSnapshotImplementation.prompt.md)
← [Contratto task/profile](contract-phase00AiExportTaskProfiles.md)

## 1. Scopo della verifica

Questo report separa tre concetti che non devono essere confusi:

1. **migration parity**: una capacità legacy aveva un equivalente diretto verificabile;
2. **deliberate difference**: il nuovo sistema corregge o restringe intenzionalmente la
   semantica legacy;
3. **greenfield conformance**: la capacità non esisteva nel legacy e viene verificata
   contro il nuovo contratto, non contro una falsa parità.

La parità riguarda dati e semantiche applicabili. Non richiede di conservare:

- il calcolo finanziario o tecnico nel browser;
- la struttura interna dei vecchi builder TypeScript;
- il vecchio formato prompt;
- i detail level legacy `summary/full`;
- il catalogo Portfolio riusato impropriamente nella pagina Broker.

## 2. Equivalenza catalogo e render mode

### 2.1 Portfolio

| Legacy | Nuovo task | Render mode equivalente | Classificazione |
|---|---|---|---|
| `snapshot` | `portfolio_description` | `data_only` | migration parity |
| `pac_planning` | `pac_planning` | `full_prompt` | migration parity |
| `rebalancing` | `rebalancing` | `full_prompt` | migration parity |
| `market_trend` | `technical_breadth` | `full_prompt` | migration parity evolutiva |
| `income_review` | `income_review` | `full_prompt` | migration parity |
| `describe_portfolio` | `portfolio_description` | `full_prompt` | migration parity evolutiva |

`performance_attribution` è greenfield.

### 2.2 Asset

| Legacy | Nuovo task | Render mode equivalente | Classificazione |
|---|---|---|---|
| `asset_snapshot` | `asset_snapshot` | `data_only` | migration parity |
| `asset_classify` | `asset_trend_analysis` | `full_prompt` | migration parity evolutiva |

Sono greenfield:

- `position_review`;
- `asset_pac_timing_context`;
- `drawdown_recovery`.

### 2.3 FX

| Legacy | Nuovo task | Render mode equivalente | Classificazione |
|---|---|---|---|
| `fx_snapshot` | `fx_trend_review` | `data_only` | migration parity |
| `fx_trend` | `fx_trend_review` | `full_prompt` | migration parity evolutiva |

Sono greenfield:

- `fx_exposure_impact`;
- `fx_conversion_timing_context`.

### 2.4 Broker

Il legacy non aveva task Broker. La pagina Broker eseguiva il catalogo Portfolio con un
filtro `brokerIds=[broker.id]`.

I fatti finanziari condivisi restano confrontabili nello stesso scope, ma i quattro task:

- `broker_review`;
- `broker_cost_efficiency`;
- `broker_concentration_context`;
- `broker_fifo_lot_review`;

sono greenfield e usano contratti Broker dedicati.

### 2.5 Estensione FIFO post-cutover

Sono greenfield anche:

- `portfolio_fifo_lot_review`;
- le righe per-lot sintetiche di `broker_fifo_lot_review`;
- il filtro condiviso: tutti i lotti aperti/parziali più quelli chiusi nei tre
  mesi di calendario precedenti;
- la selezione compact 7 aperti/parziali + 3 chiusi recenti con backfill.

Non esiste parità legacy perché il vecchio export non possedeva righe FIFO.

## 3. Detail level e cardinalità

I detail level `compact`, `standard` e `full` sono greenfield:

- `compact` applica soltanto il limite e la selection rule dichiarati dal profilo;
- `standard` conserva tutte le posizioni;
- `full` conserva tutte le entità e aggiunge contribution/profondità;
- nessun livello applica top-N impliciti;
- il render mode `data_only/full_prompt` è indipendente dal profilo backend.

Non esiste quindi una parità uno-a-uno valida con il vecchio `summary/full`.

## 4. Evidenze di parità

### 4.1 Fixture congelate

La baseline legacy è preservata in:

- `backend/test_scripts/fixtures/ai_export/legacy_semantics/prompt_compatibility.v1.json`;
- `backend/test_scripts/fixtures/ai_export/legacy_semantics/normalized_return.v1.json`;
- `backend/test_scripts/fixtures/ai_export/legacy_semantics/sampling.v1.json`;
- `backend/test_scripts/fixtures/ai_export/legacy_semantics/technical_events.v1.json`.

Le fixture distinguono esplicitamente `migration-parity` e
`known-legacy-discrepancy`.

### 4.2 Semantiche tecniche mantenute

Sono coperte come parità:

- cross prezzo/EMA20;
- cross EMA20/EMA50;
- ingresso/uscita RSI overbought e oversold;
- cambio di segno dell'istogramma MACD;
- asset giovane con finestra tecnica incompleta;
- sampling observed-only senza punti sintetici.

### 4.3 Contratti greenfield

La conformità greenfield è coperta da:

- resolver statico: 19 task × 3 detail = 57 profili;
- schemi discriminati per Portfolio, Asset, FX e Broker;
- applicability e problemi typed;
- fixture/API per tutti i domini;
- catalog handshake frontend fail-closed;
- 19 instruction template e 19 response contract;
- serializer YAML/Markdown avversariale;
- client, clipboard, stats e menu V2.

## 5. Differenze deliberate approvate

| Area | Legacy | Nuovo sistema |
|---|---|---|
| Sorgente dati | builder e calcoli frontend | snapshot backend tipizzato |
| Normalized return con gap iniziale | poteva usare il prezzo pre-window | primo osservato on-or-after |
| Punto base | il sampling poteva rimuovere lo 0% | base, primo e ultimo sempre preservati |
| Valuation fallback | riferimento BUY frontend | `MARKET_PRICE → LAST_BUY_PRICE → LAST_SEED_COST → MISSING` |
| Seed | non distinto | broker-scoped, split-adjusted, zero-cost |
| Tecnica | EMA/RSI/MACD frontend curati localmente | plugin backend allow-listed con warm-up reale |
| Signal semantics | duplicate/implicite nel frontend | semantic ID e descrizioni plugin-owned |
| Broker | Portfolio filtrato | dominio e task Broker dedicati |
| FX exposure | assente | cash/posizioni collegabili, senza promessa look-through |
| Note/provenance | campi legacy poco distinti | fonte dichiarata o campo escluso |
| Import timestamp | deduzione non autorevole possibile | `last_import_at` non esportato |
| Errori | flow UI generico | 403/404/409/422/503 typed e fail-closed |
| Prompt | formato monolitico legacy | istruzioni, contratto, dati, note e lingua separati |

Queste differenze non sono regressioni di parità: correggono ambiguità note oppure
implementano decisioni architetturali esplicite.

## 6. Evidenza di hard cutover

| Superficie | Dominio V2 | Contesto request |
|---|---|---|
| Dashboard | Portfolio | broker filter, range, target currency |
| Broker Detail | Broker | broker ID, range, target currency |
| Asset Detail | Asset | asset ID, range, display/target currency |
| FX Detail | FX | coppia canonica, range, target currency |

Le quattro route:

- usano `AiExportMenuV2`;
- caricano il catalogo backend e falliscono chiuso;
- invocano esclusivamente `copyAiExportV2`;
- non hanno feature flag o fallback runtime;
- conservano nel frontend soltanto task UX, lingua, note, render mode e prompt.

I vecchi file restano temporaneamente nel repository soltanto per il cleanup H1; non
sono più importati dalle superfici production.

## 7. Verifiche residue

Il cutover funzionale e il contratto sono chiusi. Restano nel gate finale I2:

- E2E mirati delle quattro superfici e multi-user Broker;
- review manuale desktop/mobile di menu, clipboard, privacy, dark mode e messaggi;
- verifica browser reale del percorso Clipboard/Safari.

Queste verifiche non cambiano la matrice di equivalenza; possono soltanto rilevare
regressioni d'integrazione o UX.
