# Step 2 — Canonical Series & Metadata (P1-P2)

**Stato**: ✅ COMPLETATO — 27 Luglio 2026. Gate G2 verde.

← Step precedente:
[`plan-phase01Step1QuantFoundation.prompt.md`](./plan-phase01Step1QuantFoundation.prompt.md)

← Master:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)

→ Step successivo:
[`plan-phase01Step3RollingRiskBackend.prompt.md`](./plan-phase01Step3RollingRiskBackend.prompt.md)

## 1. Obiettivo

Creare un'unica pipeline service-layer per prezzi convertiti, rendimenti,
calendario, annualizzazione, provenance e qualità. Riutilizzarla nei segnali senza
cambiare i loro output.

## 2. Decisione di placement

Default:

- `backend/app/services/series_preparation.py` per utility domain-neutral;
- `backend/app/schemas/risk.py` per DTO risk;
- helper ROI esistente esteso in modo backward-compatible;
- nessuna tabella/migrazione.

Il nome finale può adattarsi al codice, ma `SignalService` non deve dipendere da un
modulo semanticamente risk-only.

## 3. Task

### 2.1 — Freeze regressivo SignalService

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Congelare plan, coverage, point selection, availability, warmup e output dei plugin
esistenti prima dell'estrazione.

> **Note implementazione**: riallineati i test catalogo alle chiavi JSON legacy
> effettive e congelata la baseline completa: SignalService, core, close-only, OHLC,
> volume, matrice uniforme dei 17 plugin e integrazione AssetSource sono verdi.

> **⚠️ Fuori pista**: tre test storici cercavano sottostringhe (`color`) o
> pretendevano `UNAVAILABLE` per plugin che il contratto corrente dichiara
> `ALLOW_PARTIAL_CONTIGUOUS`. Le aspettative sono state rese coerenti con la matrice
> autoritativa, verificando che venga usato l'ultimo segmento contiguo senza compattare
> le date.

### 2.2 — Estrazione utility comune

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Estrarre helper puri; lasciare a `SignalService` validazione/orchestrazione/error
isolation. Nessun plugin accede a DB, prezzi o FX.

> **Note implementazione**: estratti i primitivi data/cadenza in
> `series_preparation.py` e coverage, selezione, availability, warning e slicing in
> `signal_series_preparation.py`. `SignalService` conserva solo pianificazione,
> invocazione plugin, validazione output ed error isolation. Tutte le suite segnali
> congelate al task 2.1 restano verdi.

> **⚠️ Fuori pista**: l'estrazione è stata separata in core comune + adapter segnali.
> Riutilizzare direttamente la coverage segnali nel rischio sarebbe errato: un prezzo
> esatto con FX backward-filled ha `backward_fill_info` non nullo, ma resta una nuova
> quotazione valida per il calendario congiunto. Le due semantiche condividono i
> primitivi, non la classificazione di freshness.

### 2.3 — Asset valuation/return series

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Pipeline:

```text
prezzo nativo
  -> FX alla data
  -> prezzo target con provenance
  -> calendario valorizzato
  -> rendimento semplice
```

Conservare:

- valuation/effective price date;
- prezzo/valuta nativi;
- FX rate/date;
- prezzo target;
- carry prezzo/FX;
- source/warnings.

> **Note implementazione**: aggiunti DTO strict in `schemas/risk.py` e preparazione
> pura da `FAPriceQueryResult` già convertiti da `AssetSourceManager`. Ogni punto
> conserva prezzo/valuta nativi, prezzo target, fattore/data FX, effective price date,
> carry separati, source provider e warning. `FAPricePoint` espone additivamente
> `source_plugin_key`, preservato anche nel backward-fill e nella conversione.

> **⚠️ Fuori pista**: `AssetSourceManager` mantiene il punto nativo quando FX fallisce;
> la preparazione richiede quindi `target_currency` esplicita e rifiuta quei punti,
> evitando serie a valuta mista.

### 2.4 — Joint calendar

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

- almeno un nuovo prezzo → giorno incluso;
- altri asset → ultimo prezzo;
- nessun nuovo prezzo → giorno escluso;
- nessun prezzo precedente → asset escluso;
- rendimento sempre derivato dal prezzo valorizzato.

> **Note implementazione**: calendario unico costruito dall'unione delle date con
> almeno una quotazione reale; baseline precedente separata; prezzi degli altri asset
> valorizzati sulla stessa data; giorni senza update esclusi; date con conversione
> incompleta escluse per tutte le serie. I rendimenti hanno calendario identico e sono
> sempre derivati da valutazioni target-currency consecutive.

> **⚠️ Fuori pista**: un prezzo nativo carried-forward può avere rendimento target
> non nullo se l'FX cambia. Lo zero è garantito solo quando la valutazione convertita
> resta invariata. Un prezzo esatto con FX stale resta invece una nuova quotazione
> (`days_back=0`) e non viene escluso.

### 2.5 — TWRR periodale e annualizzazione

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Esporre HPR/compound non arrotondato riusando il calcolo ROI corrente; evitare il
rapporto tra cumulative API quantizzate.

Calcolare `A=N_included×365/D_calendar`.

> **Note implementazione**: `calculate_twrr_period_series()` espone HPR, wealth index
> e cumulata non arrotondati; le API storiche delegano allo stesso calcolo e mantengono
> la quantizzazione a sei decimali. Annualizzazione osservata calcolata da baseline,
> ultimo rendimento e numero di osservazioni incluse.

### 2.6 — Data quality e metadata

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Estendere `DataQualityReport` solo per qualità sorgente. Aggiungere
`RiskResultMetadata` per contesto e esclusioni specifiche.

> **Note implementazione**: `DataQualityReport` ora espone contatori/asset/pair
> carried-forward, FX irrisolti, date di valutazione incomplete e asset inutilizzabili.
> `data_quality_status` è derivato con precedenza `partial > carried_forward > ok`,
> quindi i producer legacy non possono dichiarare `ok` insieme a errori esistenti.
> `RiskResultMetadata` resta separato e valida range, valuta, frequenza giornaliera,
> annualizzazione, mode/policy, return basis, algoritmo, timestamp e seed.

### 2.7 — Fingerprint FX

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Creare fingerprint content-derived riusabile dalle cache risk costose; nessuna
invalidazione manuale.

> **Note implementazione**: SHA-256 stabile sulle tuple FX realmente consumate
> (`pair`, valuation date, rate date, rate), indipendente dall'ordine asset e sensibile
> a qualunque variazione del contenuto.

## 4. Test obbligatori

- joint calendar equity/crypto;
- carry prezzo e FX;
- conversione prima del rendimento;
- asset senza prezzo;
- min observations;
- observed annualization;
- cash-flow neutrality TWRR;
- serializzazione `extra="forbid"`;
- parità completa plugin esistenti.

## 5. Gate G2

- utility condivisa realmente usata;
- 17 plugin senza regressioni;
- DTO/provenance/quality testati;
- nessuna migrazione;
- P3/P5 possono consumare la stessa preparazione.

> **Note implementazione**: Gate G2 chiuso con schema suite completa, regressione
> SignalService + matrice 17 plugin + AssetSource signal path, 7 test matematici della
> preparazione, 282 test ROI/FIFO/portfolio, ROI utilities, Portfolio Engine e
> AssetSource. Client OpenAPI rigenerato; `svelte-check` verde; nessuna migrazione DB.

## 6. Rischi/fallback

- estrazione troppo invasiva → spostare helper via import senza riscrivere orchestration;
- HPR non esposto → estendere helper ROI, non reimplementare TWRR;
- FX missing → risultato parziale/errore di dominio coerente, mai default silenzioso.

## 7. Progress rule

Dopo ogni task aggiornare stato/data/note/fuori-pista qui e nel master.
