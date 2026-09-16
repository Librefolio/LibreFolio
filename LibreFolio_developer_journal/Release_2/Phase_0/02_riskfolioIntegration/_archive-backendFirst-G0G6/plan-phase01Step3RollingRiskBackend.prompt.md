# Step 3 — Rolling Risk Backend (P3-P4)

**Stato**: ✅ COMPLETATO — 27 Luglio 2026; Gate G3 chiuso.

← Step precedente:
[`plan-phase01Step2CanonicalSeriesMetadata.prompt.md`](./plan-phase01Step2CanonicalSeriesMetadata.prompt.md)

← Master:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)

→ Step successivo:
[`plan-phase01Step4MultiAssetRiskBackend.prompt.md`](./plan-phase01Step4MultiAssetRiskBackend.prompt.md)

## 1. Obiettivo

Aggiungere cinque metriche rolling asset-scoped al framework `SignalPlugin`, con
matematica backend, catalogo schema-driven e serie comparison preparata.

## 2. Task

### 3.1 — Contratto segnali

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

- aggiungere `SignalCategory.RISK`;
- dichiarare una dependency `comparison_asset_id`;
- estendere execution context con serie comparison pronta;
- mantenere compatibilità plugin esistenti.

> **Note implementazione**: aggiunta `SignalCategory.RISK`; il contratto
> `SignalInputRequirements` ora dichiara in modo esplicito
> `uses_prepared_asset_series` e l'eventuale parametro
> `comparison_asset_param`. `SignalExecutionContext` dispone degli slot tipizzati
> `primary_asset_series`/`comparison_asset_series` e del fattore di
> annualizzazione osservato. `SignalResult` può esporre la coppia
> `RiskResultMetadata` + `DataQualityReport`; aggiunti stati espliciti per serie
> preparata mancante e finestre matematicamente indefinite. Il registry rifiuta
> una dependency comparison che non corrisponde a un parametro dichiarato.
> Test contratto: 81 schema + 15 registry passati.

### 3.2 — Orchestrazione comparison asset

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

`SignalService` resta DB-free:

1. adapter Asset legge il piano;
2. carica primary+comparison in bulk;
3. utility Step 2 converte e allinea;
4. context riceve la serie;
5. plugin calcola.

> **Note implementazione**: `AssetSourceManager` legge dal piano gli asset di
> confronto, include primary e dependency nello stesso caricamento bulk, applica
> conversione FX e `prepare_asset_series_set()` una sola volta per dipendenza,
> quindi passa a `SignalService` un bundle tipizzato. Il service resta DB/FX-free
> e inietta serie primary/comparison, fattore osservato, metadata risk e qualità.
> Il confronto con lo stesso asset riusa la serie primaria. Verificati: una sola
> query prezzi, valuta target, FX carried-forward, comparison mancante e same-asset.

> **⚠️ Fuori pista**: il calendario canonico omette i giorni senza nuove quote;
> la coverage generica dei segnali lo tratterebbe erroneamente come gap giornaliero.
> Solo la selezione interna usa quindi cadenza `IRREGULAR`; i metadata finanziari
> restano correttamente `DAILY`.
>
> **Note semantica metadata**: `RiskResultMetadata.analyzed_range`,
> `n_observations`, `calendar_days` e `annualization_factor` descrivono lo stesso
> campione preparato realmente consumato dal rolling, incluso il warm-up. Il range
> visibile resta nel contesto segnale e nel trimming dell'output; non viene usato
> per dichiarare un fattore di annualizzazione diverso da quello del campione.

### 3.3 — Plugin price-only

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

- underwater drawdown;
- rolling volatility;
- rolling compounded return.

> **Note implementazione**: aggiunto il modulo puro e riusabile
> `services/risk/metrics.py` e i plugin `RISK_DRAWDOWN`,
> `RISK_ROLLING_VOLATILITY`, `RISK_ROLLING_RETURN`. Le formule consumano prezzi
> e rendimenti canonici target-currency; sample variance usa `ddof=1`.

> **⚠️ Fuori pista**: `SignalUnit.PERCENTAGE` usa storicamente punti percentuali
> (PPO/ROC/NATR), mentre il contratto matematico produce decimali. La conversione
> `×100` è stata confinata al boundary di output dei plugin; le primitive pure
> restano decimali.

### 3.4 — Rolling Sharpe

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Parametro `risk_free_annual_rate`, default 0. Conversione:
`(1+rf)^(1/365)-1`.

> **Note implementazione**: `RISK_ROLLING_SHARPE` usa media del rendimento
> eccedente, deviazione standard campionaria e `sqrt(A)`. Il risk-free annuo è
> convertito con `expm1(log1p(rf)/365)`. Finestre a varianza nulla non inventano
> valori: tutte nulle → `UNAVAILABLE/UNDEFINED_METRIC`; solo alcune →
> `PARTIAL/PARTIAL_UNDEFINED_METRIC` con warning esplicito.

### 3.5 — Rolling beta

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Solo asset reale variabile. Formula `cov/var`; benchmark a varianza nulla →
`UNAVAILABLE`.

> **Note implementazione**: `RISK_ROLLING_BETA` dichiara
> `comparison_asset_id` come parametro obbligatorio e semantic control
> `comparison_asset`. Primaria e confronto sono convertite e derivate sullo stesso
> calendario congiunto; beta usa covarianza/varianza campionarie. Benchmark flat →
> indisponibilità di dominio, mai zero/infinito. Fixture con serie 2× conferma
> beta 2; same-asset conferma beta 1.

### 3.6 — Catalog/API/OpenAPI

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Catalogo espone categoria, params, output e semantic widget asset picker.
Rigenerazione client solo al gate backend.

> **Note implementazione**: registry e catalogo Asset espongono 22 plugin
> (17 tecnici legacy + 5 risk), mentre il catalogo FX resta invariato a 9.
> Rigenerato il client OpenAPI; mapper e selettore supportano categoria `risk` e
> semantic control `comparison_asset`. Il picker riusa la cache degli asset
> persistiti e `SearchSelect`; i parametri obbligatori mancanti non generano
> richieste invalide. Aggiunte traduzioni EN/IT/FR/ES guidate dalle chiavi backend.
> Verificati 73 test backend, 143 unit frontend, type-check/build, audit i18n e un
> E2E funzionale desktop che renderizza i cinque plugin e invia beta solo dopo la
> selezione dell'asset reale.
>
> **⚠️ Fuori pista**: `AssetSearchAutocomplete` cerca candidati esterni e non
> restituisce un ID asset persistito; non può quindi soddisfare
> `comparison_asset_id`. È stato riusato il pattern `assetStore` + `SearchSelect`,
> senza introdurre un secondo catalogo o calcoli frontend.

## 3. Formule

- volatility: sample stdev × `sqrt(A)`;
- drawdown: `W/max(W)-1`;
- rolling return: prodotto rendimenti semplici della finestra;
- Sharpe: `mean(excess)/stdev×sqrt(A)`;
- beta: `cov(primary, benchmark)/var(benchmark)`.

## 4. Test

- fixture manuali;
- window/warmup boundaries;
- short/flat/gapped series;
- risk-free 0 e non-zero;
- comparison uguale/valuta diversa;
- benchmark zero variance;
- catalog/registry/service/bulk API;
- no DB access nei plugin;
- non-regressione plugin esistenti.

## 5. Gate G3

- 5 plugin auto-discovered;
- output/status/warnings corretti;
- RISK nel catalogo;
- beta riceve serie pronta;
- client sync pulito;
- nessuna matematica frontend.

## 6. Rischi/fallback

- dependency troppo generica → campo dedicato comparison asset;
- beta ritarda → consegnare 3 price-only, Sharpe, poi beta, senza aprire UI prima del gate;
- schema mapper non supporta asset ref → estensione generica metadata-driven.

## 7. Progress rule

Dopo ogni task aggiornare stato/data/note/fuori-pista qui e nel master.
