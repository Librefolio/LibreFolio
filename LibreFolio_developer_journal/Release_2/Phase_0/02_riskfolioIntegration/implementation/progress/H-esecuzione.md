# H — piano di esecuzione

| | |
|---|---|
| Mandato | [`../H-backend-montecarlo.md`](../H-backend-montecarlo.md) — **sola lettura** |
| Branch | `e-alfy-h-monte-carlo` |
| Baseline | `cc33120ebfbc61efe4c6178218ff8d64dd4adf47` — verificata, coincide |
| Lane | porta `6247` · data dir `backend/data/test-risk-h` |
| Coordinatore | sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca` |
| Autorizzazione | ricevuta 17 Set 2026 — **implementazione approvata tranne GJR-GARCH** |

---

## Decisioni che governano questa esecuzione

| # | Esito |
|---|---|
| **H-Q1** | 🔴 **NO.** `arch` non si promuove, **GJR-GARCH esce dalla v1** → `TODO_FUTURI.md`. Promuovere `arch` tocca l'ambiente Python **condiviso da tutte le lane attive**: è lavoro del developer a lane congelate, non di un mandato |
| **H-Q2** | univariato sull'aggregato — *decaduta con H-Q1* |
| **H-Q3** | ✅ registrare la decisione **F6**: NumPy diventa campionatore di produzione |
| **H-Q4** | ✅ `process` × `regime`, due assi |
| **H-Q5** | ✅ i preset cavalcano il bootstrap |
| **H-Q6** | ✅ **ammorbidire l'ipotesi**: il testo dice ciò che il preset fa davvero |
| **H-Q7** | ✅ troncare e dichiarare a schermo |
| **H-Q8** | ✅ `lib/risk/**` è di **E** — fuori dall'ambito di H |
| **H-Q9** | ✅ regola `__all__` estesa a quattro scrittori |
| **H-Q10** | ✅ `TODO_FUTURI.md:277` lo corregge il coordinatore |
| **F7** | ✅ **H consegna K6, E costruisce il selettore** |

---

## Passi

- [x] 0. Creare questo file — ✅ 17 Set 2026
  > **Note implementazione**: creato prima di qualunque modifica al codice, come
  > punto di ripristino. Il brief resta intonso.

- [x] 1. K6 al coordinatore — ✅ 17 Set 2026
  > **Note implementazione**: inviato appena la forma è stata stabile, senza
  > aspettare l'implementazione completa, come richiesto.

- [x] 2. Schemi — ✅ 17 Set 2026
  > **Note implementazione**: `RiskSimulationProcess.BLOCK_BOOTSTRAP`; nuovo
  > `RiskSimulationRegime`; `RiskSimulationDriftEstimator.EMPIRICAL_RESAMPLED`;
  > `RiskSimulationCovarianceEstimator.NOT_ESTIMATED_JOINT_RESAMPLING` — perché
  > dire `sample_log_returns` per un bootstrap sarebbe una bugia nei metadati.
  > `RiskSimulationOutput` espone `regime`, `block_length_days`,
  > `regime_declared_days`, `regime_applied_days`, con un validatore che **rende
  > impossibile** non dichiarare l'ipotesi applicata. `__all__` a quattro
  > scrittori: aggiunta una sola riga in ordine alfabetico.

- [x] 3. Contratto di motore — ✅ 17 Set 2026
  > **Note implementazione**: `annual_drifts`/`annual_covariance` diventano
  > opzionali e sono **rifiutati** sotto bootstrap; `historical_returns` +
  > `historical_digest` + `bootstrap_seed` + `block_length_days` sono rifiutati
  > sotto GBM. La chiave di cache esclude la matrice e usa il digest (115×), e
  > il worker **ricalcola** il digest: una chiave non può sopravvivere ai dati
  > che dichiara. Budget `MAX_HISTORY_CELLS = 250_000` = il caso peggiore
  > misurato (100 asset × 2 500 osservazioni = 2,26 MB pickle).

- [x] 4. Campionatore block bootstrap — ✅ 17 Set 2026
  > **Note implementazione**: nuovo `quant/resampling.py`, NumPy puro, nessun
  > import QuantLib. Moving block circolare, ricampionamento **congiunto** di
  > righe intere. Gli origini dei blocchi sono estratti **tutti in una volta**
  > prima del chunking: la riproducibilità non dipende da come il lavoro viene
  > affettato per la memoria. Lavoro in spazio log → la crescita cumulata è una
  > `cumsum` e `1 + r` non può diventare negativo.

- [x] 5. Bootstrap default, GBM conservato — ✅ 17 Set 2026
  > **Note implementazione**: default di `process` invertito. Compatibilità
  > all'indietro per deduzione esplicita: chi nomina `qmc`, `random_seed` o
  > `sobol_start_index` chiede senza ambiguità il motore parametrico, perché
  > quei campi non hanno senso per un ricampionatore. Chi non nomina nulla
  > prende il nuovo default. `algorithm_version` → `3.0.0-bootstrap-…`: la
  > distribuzione cambia, le voci di cache vecchie non devono sopravvivere.

- [x] 6. Preset di regime con ipotesi onesta — ✅ 17 Set 2026
  > **Note implementazione**: `calm` scala la dispersione a 0,7; `crisis` a 2,5
  > con deriva −20% annua per 426 giorni; `shock_recovery` sovrappone una deriva
  > deterministica di −35% su 61 giorni e poi lascia riprendere la storia vera.
  > Troncamento a orizzonte corto **dichiarato** via `regime_applied_days`.

- [x] 7. ~~GJR-GARCH~~ → **fuori dalla v1** (H-Q1), voce in `TODO_FUTURI.md` — ✅ 17 Set 2026
  > **Note implementazione**: sezione «Livello 2 — GJR-GARCH: perché è uscito
  > dalla v1» scritta con le **misure**, non con l'argomento: le tre righe di
  > introspezione su QuantLib 1.43 sono riportate integralmente, perché il
  > presupposto del brief («nativo QuantLib, calibrabile dalla sola serie
  > prezzi») era falso e chi riaprirà il tema deve vederne la prova, non la mia
  > conclusione. Registrata anche la precondizione: `arch` promossa a dipendenza
  > **diretta** nel `Pipfile`. Appoggiarsi alla transitiva di `riskfolio-lib`
  > sarebbe stato peggio che rinviare: il giorno in cui quella dipendenza cade,
  > il GARCH sparirebbe **senza che nulla fallisca in modo visibile**.
  > Aggiunta, su richiesta del coordinatore, la sezione «Preset di crisi — la
  > forma preferita per il seguito» (ricampionamento condizionato dal decile
  > peggiore) con la sua condizione vincolante: se la storia non è abbastanza
  > severa **si dichiara, non si fabbrica**.
  > **Righe altrui non toccate**: la riga `:277` della tabella è del
  > coordinatore; il mio testo è una sezione nuova, inserita più in basso.

- [x] 8. i18n `risk.simulation.*` × 4 lingue — ✅ 17 Set 2026
  > **Note implementazione**: aggiunto `risk.simulation.mode.*` (label +
  > **hypothesis** per bootstrap/calm/crisis/shock/gbm, più `recommended` e
  > `advanced`) e `risk.simulation.regimeTruncated`. Il testo dell'ipotesi è
  > **contratto K6, non decorazione**: sta accanto alla scelta, non in un
  > tooltip. Scritto solo dentro `risk.simulation.*`; nessun riordino, nessuna
  > riformattazione — un round-trip `json.dumps(indent=2, ensure_ascii=False)`
  > è stato verificato **byte-identico** sui quattro file *prima* di scrivere,
  > così il diff è un solo hunk per lingua.
  > **⚠️ Fuori pista minore**: tolti gli hint di controllo da `process` e
  > `regime` nello schema. Sotto il nuovo selettore **nessuno dei due è un
  > controllo utente** — l'utente sceglie una *modalità*, che li determina
  > entrambi. Lasciare `x-i18n-key: risk.params.regime` avrebbe per giunta
  > lasciato un riferimento pendente a una chiave mai scritta.

- [x] 9. Test + `api sync` — ✅ 17 Set 2026
  > **Note implementazione**: 14 test nuovi scritti da `test-author` in
  > `test_risk_simulation.py` (15 preesistenti → **29**), diff `+666/-0`: i
  > quindici vecchi sono **byte per byte intatti**. Il test portante è la
  > riproducibilità a seme fissato: senza di quello ogni altro test del file
  > sarebbe flaky per costruzione, perché il bootstrap introduce un
  > campionamento casuale che prima non c'era. Aggiunto anche il test che la
  > riproducibilità **non dipenda dal chunking** — gli origini dei blocchi sono
  > estratti prima che il lavoro venga affettato, e ora c'è un rosso che lo
  > difende.
  > `api sync`: eseguita la **sola metà Python**, l'export OpenAPI, verificando
  > che la superficie nuova ci sia tutta (`RiskSimulationRegime`, i quattro
  > campi di disclosure, `metadata.bootstrap_seed`, i due estimatori nuovi). La
  > metà TypeScript richiede `node_modules`, assente per disegno in questo
  > worktree: **non installo**, la rigenerazione di `generated.ts` (gitignorato)
  > resta a chi ha la lane frontend.

- [x] 10. Gate di integrazione — ✅ 17 Set 2026
  > **Note implementazione**: quattro selettori verdi, uno alla volta nella
  > lane. `lint` pulito dopo aver spezzato due validatori troppo complessi.
  > Porta 6247 libera, `git diff --check` pulito, nessun artefatto generato fra
  > i file non tracciati.

---

## Fuori pista del tratto finale

- **18 Set — ⚠️ freeze rotto deliberatamente: avevo costruito io una trappola
  per E.** Le chiavi i18n che avevo scritto erano `mode.bootstrap`,
  `mode.crisis`, `mode.shock`; i valori enum sono `block_bootstrap`,
  `prolonged_crisis`, `shock_recovery`. Un `mode[regime]` ingenuo — cioè il
  modo naturale di scrivere quel selettore — sarebbe fallito su **3 voci su 5**,
  e sarebbe fallito *silenziosamente*, rendendo la chiave grezza al posto
  dell'ipotesi. Cioè proprio la riga che il contratto dichiara non
  decorativa. Chiavi rinominate ai valori enum **esatti**, così E risolve con
  `regime === 'none' ? mode[process] : mode[regime]` senza tabella di mappatura.
  Nessun consumatore esisteva ancora: costo zero adesso, un ciclo di debug
  altrui fra un'ora. Verificato: parità sulle 4 lingue, `i18n audit`
  2774/2774 completi e 0 chiavi backend mancanti, suite 29 passed, porta libera.

- **17 Set — il default sul contratto *interno* era una trappola.** Avevo dato
  a `SimulationEngineRequest.process` un default `block_bootstrap`. Tredici
  test preesistenti sono diventati rossi: costruivano un payload parametrico
  senza nominare il processo, e finivano nella fisica sbagliata.
  La correzione non è stata cambiare il default ma **toglierlo**: i due
  contratti portano dati diversi, quindi un default lascia costruire per
  sbaglio una forma ed evolverla sotto la fisica dell'altra. Entrambi i siti
  di produzione dichiaravano già il processo; il campo obbligatorio serve solo
  a far fallire **rumorosamente** chi non lo dichiara. I quattro siti nei test
  ora dichiarano `process="gbm"`, e così dicono che cosa stanno testando.

- **17 Set — ⚠️ il test legacy aveva ragione e io torto.** La mia regola di
  compatibilità mandava `{"sampling":"mc","paths":N,"seed":S}` sul bootstrap.
  Verificato che i params **non sono persistiti** da nessuna parte: l'alias
  legacy è input d'API, non configurazione salvata. Il che rende la regola
  *più* netta, non meno: chi manda quei nomi è un client vecchio, che renderà
  il risultato con le **etichette vecchie** — una riga di ipotesi fissa che
  descrive un processo lognormale. Rispondergli con percorsi ricampionati
  metterebbe numeri onesti sotto una didascalia che li descrive male. Ora
  qualunque alias legacy identifica GBM, e il test preesistente torna verde
  **perché il comportamento è diventato giusto**, non perché l'ho piegato.

- **17 Set — ⚠️ `./dev.py format` formatta l'albero intero.** Ha riformattato
  **7 file estranei** con drift preesistente (`api/v1/system.py`, `config.py`,
  `schemas/common.py`, `schemas/prices.py`, e tre file di test). Riportati al
  contenuto di HEAD con `git show HEAD:<path> > <path>` — scrittura di file,
  nessun comando git proibito. **Segnalato al coordinatore**: chiunque in
  questa campagna esegua `format` si trascina quei 7 file nel proprio
  checkpoint senza accorgersene. Da qui in avanti ho formattato con `black`
  sui soli file miei.

- **17 Set — ⚠️ tre dei miei numeri erano sbagliati, e il terzo era un difetto
  di contratto.** `test-author` ha misurato e corretto:
  1. la correlazione `0.9012` era della **mia** storia sintetica, non una
     proprietà del codice. La proprietà vera è più forte: i tre regimi
     concordano **all'ultimo ulp** (deviazione massima 5,6e-16). Il test ora
     asserisce l'invarianza a 1e-9 e confronta la correlazione simulata con
     quella della **storia in ingresso**, che è ciò che la didascalia promette.
  2. i rapporti di dispersione sono esatti — **0,7 e 2,5 a precisione di
     macchina** — sulla deviazione standard dei log-rendimenti terminali,
     perché il regime scala il log uniformemente. Sul volatility di portafoglio
     restano approssimati (0,6926 / 2,3897). Il test asserisce entrambi, e
     annota che l'esattezza vale solo finché l'orizzonte non supera la finestra
     della crisi.
  3. **lo shock non cala del 35%: moltiplica per 0,65.** Verificato esatto a
     2,2e-16. Ciò che l'utente legge è `0,65 × (1 + la deriva della sua storia
     a 61 giorni) − 1`: −33,94% su una storia, −35,22% su un'altra. Il fattore
     è esatto, **la didascalia no**. Ho corretto il testo nelle quattro lingue:
     «un calo del 35% **applicato alla tua storia** in 2 mesi». È esattamente
     il tipo di scarto fra didascalia e numero che questa campagna esiste per
     togliere, ed è emerso da un test, non da una rilettura.

---

## Evidenza

| Comando | Esito |
|---|---|
| `git rev-parse HEAD` | `cc33120e…` = baseline ✅ |
| `… test --test-port 6247 --data-dir backend/data/test-risk-h services risk-simulation` | **29 passed in 9.20s** ✅ (era 15) |
| `… services risk-workers` | **11 passed in 14.53s** ✅ |
| `… services quantlib-runtime` | **2 passed in 0.08s** ✅ |
| `… services risk-all` | **148 passed in 31.53s** ✅ (dopo il refactor dei validatori) |
| `dev.py lint` | `All checks passed!` ✅ |
| `black` sui soli file miei | `11 files left unchanged` ✅ |
| `scripts/list_api_endpoints.py --openapi-file` | superficie nuova completa ✅ |
| `lsof -nP -iTCP:6247 -sTCP:LISTEN` | vuoto ✅ |
| `git diff --check` | pulito ✅ |
| non tracciati | solo `resampling.py` e questo piano ✅ |

La suite è stata eseguita **tre volte di fila** da `test-author` con conteggio
identico (29/29/29): la riproducibilità a seme fissato non è un'affermazione,
è stata ripetuta.

### Misure eseguite in analisi (sola introspezione, nessuna scrittura)

**QuantLib 1.43 — il presupposto del brief era falso**

```text
hasattr(ql, 'Garch11')                            -> False
GJRGARCHModel.calibrate(CalibrationHelperVector, OptimizationMethod, EndCriteria, ...)
issubclass(GJRGARCHProcess, ql.StochasticProcess1D) -> False   factors() -> 2
```

**Chiave di cache — perché serve il digest**

```text
json.dumps(matrice)   99,2 ms   (5,41 MB)     100 asset × 2 500 oss
sha256(stringa json)   2,6 ms
TOTALE oggi          101,8 ms   per chiamata
sha256(arr.tobytes)    0,9 ms   <- digest       guadagno 115x
```

Il punto non è il 2% su una simulazione fredda: **anche il cache *hit* paga 101,8 ms**
solo per scoprire di non dover calcolare nulla.

---

## Contratti

| # | Verso | Stato |
|---|---|---|
| K6 v2 | E (via coordinatore) | 📝 **stabile** — consegnato e relayato a E |

---

## Fuori pista

- **17 Set — ⚠️ RITRATTAZIONE: il guadagno `INVALID_COVARIANCE` che avevo promesso
  non esiste come guadagno utente.** Il coordinatore ha chiesto la prova, non
  l'argomento: la prova dice che avevo torto io. Misurato sul codice vero, il
  percorso parametrico **non** solleva su dati storici reali — la covarianza
  campionaria è PSD per costruzione:

  | Caso degenere | GBM | bootstrap |
  |---|---|---|
  | serie duplicate (collinearità perfetta) | ok | ok |
  | asset a volatilità zero | ok | ok |
  | più asset che osservazioni | ok | ok |
  | matrice non-PSD costruita a mano | **ValueError** | **non esprimibile** |

  Solo l'ultima riga solleva, e nessun percorso di produzione la costruisce. Il
  bootstrap rende l'errore **strutturalmente** impossibile invece che
  **improbabile** — che è una proprietà d'ingegneria reale, non un beneficio che
  l'utente possa notare. **Non va nel CHANGELOG**: sarebbe esattamente la
  rivendicazione decorativa che questa campagna esiste per togliere.
- **17 Set — difetto vero trovato mentre cercavo quello falso.** Il plugin
  mappava **qualunque** `ValueError` remoto su `INVALID_COVARIANCE`. Sotto
  bootstrap un digest non corrispondente sarebbe arrivato all'utente come
  «covarianza non valida», mandandolo a cercare una matrice mai costruita. Ora
  il codice d'errore dipende dal motore: `DATA_UNAVAILABLE` per il bootstrap,
  `INVALID_COVARIANCE` solo dove una covarianza esiste davvero.
- **17 Set — la riga «correlazioni → 0,9» del brief non era realizzabile** con
  una trasformazione scalare, ed è caduta. Misurato: la correlazione terminale
  resta **0,9012 identica** sotto `none`, `calm` e `crisis`, perché scalare la
  dispersione lascia la correlazione di Pearson invariata. Il testo dell'ipotesi
  ora dichiara proprio questo.
- **17 Set — il presupposto «GJR-GARCH nativo QuantLib, calibrabile dalla sola
  serie prezzi» era falso.** QuantLib espone solo engine di *option pricing*;
  `ql.Garch11`, l'unica classe che calibra per MLE da una serie di rendimenti,
  non è nei binding Python. L'obiezione con cui il piano rinviava il livello 5
  («richiede dati di opzioni») si applicava **identica** al livello 2.
- **17 Set — `arch 8.0.0` è installato ma assente dal `Pipfile`**: transitiva di
  `riskfolio-lib`. Appoggiarcisi è fragilità silenziosa; promuoverla tocca
  l'ambiente condiviso da tutte le lane. Decisione del coordinatore: nessuna
  delle due, si rinvia.
- **17 Set — due buchi nella mappa del coordinatore**, poi corretti da lui:
  `schemas/risk.py` aveva un quarto scrittore non dichiarato (H) e `lib/risk/**`
  non risultava assegnato a nessuno (è di E).
- **17 Set — tre file condivisi toccati fuori dalla mia lista**, tutti in modo
  additivo di una riga, per non riusare `random_seed` come fa il difetto
  archiviato: `risk/base.py` (campo `bootstrap_seed` sul dataclass),
  `risk/service.py` (una riga di assemblaggio metadati), `schemas/risk.py:487`
  (`RiskResultMetadata.bootstrap_seed`, regione non contesa).
