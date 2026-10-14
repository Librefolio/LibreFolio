# N — piano di esecuzione

| | |
|---|---|
| Mandato | [`../N-backend-acquisizioni.md`](../N-backend-acquisizioni.md) (sola lettura) |
| Branch | `e-alfy-risk-n-backend-acquisizioni` |
| Baseline | `cc33120ebfbc61efe4c6178218ff8d64dd4adf47` ✅ verificata |
| Lane | porta `6248` · data dir `backend/data/test-risk-n` |
| Coordinatore | sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca` |
| Consegna | contratto **K8** → **E** *e* **I** (esteso, D-N9) |

---

## Decisioni ratificate dal coordinatore

| # | Esito |
|---|---|
| **D-N1** | `acquired.py` in **`math` puro** — mai NumPy: A fa M6 nello stesso vicinato |
| **D-N2** | **`api sync` non è di N**. N esegue `api schema`; il client TS lo rigenera chi ha `node_modules`. DoD §12 corretta dal coordinatore |
| **D-N3** | Chiedere ad A la riga in `RISK_SERVICE_TEST_PATHS`; nel frattempo test di plugin in `test_risk_analytics.py` |
| **D-N4** | Identità con AI Export **condizionata** + tolleranza. **D77 va corretta** |
| **D-N5** | Campi **piatti** → N **non tocca `__all__`** → attrito zero con A e C |
| **D-N6** | `WR` porta la data; ties = **prima occorrenza** |
| **D-N7** | α **parametro**, default `0,05` |
| **D-N8** | **`test_risk_analytics.py` è di N**. Regola nuova: chi apre per primo un file di test backend lo dichiara |
| **D-N9** | **K8 esteso a I** |

Regola di segno ratificata:

> **Drawdown e rendimenti negativi · dispersioni non-negative.**

---

## Passi

- [x] 1. Analisi di implementazione — ✅ 18 Set 2026
  > **Note implementazione**: verificate sul codice tutte le affermazioni del brief.
  > Confermate: `diversification` 0 occorrenze, `worst_*` 0, `herfindahl` solo AI Export,
  > `RiskKpiOutput` `:638-647` con `max_drawdown` `le=0` a `:644`,
  > `RiskContributionOutput` `:673-680`, `__all__` `:1067-1126`, 1 126 e 661 righe.
  > **Fuori pista**: otto presupposti del brief falsificati (F1-F8). I tre bloccanti:
  > l'identità con AI Export non vale in generale (granularità `(broker, asset)` contro
  > `asset`, `quantize(0.01)` contro float pieni, asset esclusi dentro `cash_weight`);
  > `api sync` ineseguibile senza `node_modules`; `services risk-all` non fa discovery.
  > Più tre trappole di correttezza lette dal sorgente riskfolio, mai nominate prima:
  > `CDaR` è Rockafellar-Uryasev e non una media, `T` contro `T+1` dentro la stessa
  > famiglia, il `n−1` di `UCI` non è Bessel.

- [x] 2. Piano vivo — ✅ 18 Set 2026
  > **Note implementazione**: questo file, creato dopo l'autorizzazione del coordinatore.

- [x] 3. Contratto K8 → E e I — ✅ 18 Set 2026
  > **Note implementazione**: nomi, segni, unità, cassa, data di `WR`, invarianza del DR,
  > vincolo «NEA e DR insieme». Comunicato al coordinatore, che lo materializza in
  > `contracts/K8.md` e lo relaya.
  > **⚠️ Fuori pista — nona scoperta, non prevista da nessun documento**: il progetto ha
  > **già due convenzioni di segno opposte** in due output che **E ricompone nello stesso
  > livello L1**. `RiskVarCvarOutput.value_at_risk` è `Field(..., ge=0)` — magnitudine
  > **positiva** (`:823-824`, e `metrics.py:621` calcola `max(-value, 0.0)`), mentre
  > `RiskKpiOutput.max_drawdown` è `le=0`. Nessuno dei due è sbagliato — ogni oggetto è
  > coerente con sé, che è esattamente la regola. Ma il brief §5 chiede `WR` «accanto al
  > VaR per contrasto»: a schermo E metterà `−0,0385` accanto a `+0,0312` per due
  > grandezze che sono entrambe perdite. Messo in K8 come avvertenza esplicita.

- [x] 4. `acquired.py` — ✅ 18 Set 2026
  > **Note implementazione**: nuovo modulo `backend/app/services/risk/acquired.py`,
  > 8 funzioni pubbliche, `math` puro, zero NumPy, zero import di riskfolio.
  > Consuma `DrawdownSummary.drawdowns` già prodotto da `summarize_drawdown` →
  > nessuna passata in più e **`metrics.py` mai toccato**. Le tre trappole sono
  > codificate in struttura, non in commento: `_tail_without_baseline()` per
  > `DaR`/`CDaR`, serie intera per `UCI`, forma Rockafellar-Uryasev per `CDaR`.
  > **⚠️ Fuori pista — undicesima scoperta, sul mio stesso codice**: avevo messo un
  > pavimento a zero su `worst_realization`. **`riskfolio.WR` non ce l'ha**: su una
  > finestra tutta in guadagno restituisce un valore negativo, cioè «il giorno peggiore
  > è stato un guadagno». Il pavimento avrebbe accoppiato un valore `0,0` con una data
  > che punta a un giorno in utile — una bugia silenziosa. Rimosso: la funzione pura dice
  > il vero, l'adattamento al vincolo `le=0` è del plugin. Rimossi anche tre pavimenti
  > `min(…, 0.0)` inutili su misure già ≤ 0 per costruzione: un ramo che non scatta mai
  > è peso che il lettore futuro deve ri-dimostrare.
  > **Fuori pista — quarta trappola di riskfolio**: dentro la **stessa** libreria,
  > `MDD_Rel`/`UCI_Rel` accumulano `DD = (peak−i)/peak` **positivo**, mentre
  > `DaR_Rel`/`CDaR_Rel` accumulano `-(peak−i)/peak` **negativo** e negano alla fine.
  > Irrilevante per noi solo perché normalizzo in ingresso, ma spiega perché copiare
  > una funzione riskfolio «per analogia» con un'altra sia pericoloso.

- [x] 5. Test di matematica pura — ✅ 18 Set 2026
  > **Note implementazione**: **21 test**, nel file `test_risk_analytics.py`.
  > Oracolo riskfolio 7.0.1 **per valore** su tutte e cinque le misure: accordo a
  > **≤ 1 ULP** (`1,110e-16`). Serie deterministica **aritmetica** (`sin`/`cos`), non
  > seeded-random: `random.gauss` è stabile oggi ma è un dettaglio di CPython.
  > Ogni trappola ha il suo test che **fallisce se qualcuno la reintroduce**:
  > `CDaR` contro la media ingenua, denominatore `T` contro `T+1`, `UCI` contro `/(T−1)`,
  > `_Rel` contro `_Abs`. Segno asserito **un campo per volta**, così un'inversione
  > applicata a metà non può nascondersi dentro un'asserzione aggregata.
  > **⚠️ Fuori pista — il kickoff è smentito su un punto**: mi era stato detto che «A ha
  > già verificato che `summarize_drawdown.max == -MDD_Rel` **esattamente**».
  > **Non è esatto.** Su due serie indipendenti la differenza è di **1 ULP**
  > (`-0,64572671320363` contro `-0,6457267132036301`), perché `wealth_index` e
  > `np.cumprod` accumulano gli stessi prodotti in ordine diverso. Non è un errore
  > numerico — è un'uguaglianza che **non si può asserire con `==`**. Chiunque scriva
  > quel test come uguaglianza stretta lo vede rosso e, non sapendo perché, rischia di
  > «aggiustare» il codice invece della tolleranza. Riportato al coordinatore per A,
  > non aggiustato da me. Il mio test usa `pytest.approx(abs=1e-12)` e lo **documenta**.
  > **Fuori pista — dipendenza da A rimossa**: il piano prevedeva un file nuovo
  > `test_risk_acquired.py` e una richiesta ad A di registrarlo in
  > `RISK_SERVICE_TEST_PATHS`. Ma un file non registrato **non viene eseguito mentre la
  > suite resta verde** (F4). Invece di dipendere da un altro mandato per non essere
  > silenziosamente saltato, ho messo tutto in `test_risk_analytics.py`, **già registrato
  > e già mio** (D-N8). La richiesta ad A decade.

- [x] 6. Campi di schema — ✅ 18 Set 2026
  > **Note implementazione**: 6 campi su `RiskKpiOutput`, 2 su `RiskContributionOutput`,
  > tutti `Optional` con default `None`. Nessun campo esistente toccato nel nome, tipo,
  > unità o segno: `RiskKpiOutput(volatility=…, max_drawdown=…, max_drawdown_duration_days=…)`
  > continua a costruire e i campi nuovi valgono `None`. **`__all__` non toccato** (D-N5).
  > Aggiunto un `model_validator` che impone `max_drawdown ≤ CDaR ≤ DaR`, sul modello del
  > `validate_tail_ordering` già presente su `RiskVarCvarOutput` con il segno rovesciato:
  > i due valori sono entrambi negativi e entrambi plausibili da soli, **solo l'ordine**
  > distingue il quantile dalla sua media condizionale, e nessun vincolo di intervallo
  > può vedere uno scambio di assegnazione.
  > **Fuori pista — zero debito i18n**: `drawdown_confidence_level` riusa
  > `risk.params.confidenceLevel`, chiave **già esistente e tradotta** in en/it/fr/es
  > (verificato). Il namespace `risk` è di E: non gli chiedo chiavi nuove.

- [x] 7. `historical_kpi.py` — ✅ 18 Set 2026
  > **Note implementazione**: riusa il `DrawdownSummary` già calcolato alla riga ~69 →
  > **nessuna passata in più** sulla storia. `_dates` non era più scartato: serve per la
  > data di `WR`. `algorithm_version` 2.0.0 → **2.1.0**.
  > Caso degenere gestito: finestra tutta in guadagno → `worst_realization` e la sua data
  > vanno a `None` con un `RiskWarning(code="worst_realization_undefined")`, invece di
  > dichiarare una perdita mai avvenuta.

- [x] 8. `risk_contribution.py` — ✅ 18 Set 2026
  > **Note implementazione**: `covariance_matrix(rows)` sollevata da argomento inline a
  > locale per riusarne la diagonale. `algorithm_version` 1.0.0 → **1.1.0**.
  > **⚠️ Fuori pista — decisione numerica non prevista dal brief**:
  > `risk_contributions_from_covariance` **annualizza internamente**, quindi
  > `summary.portfolio_volatility` è annualizzata. Il rapporto di diversificazione è
  > invariante all'annualizzazione **solo se numeratore e denominatore concordano**: usare
  > la diagonale grezza contro una volatilità annualizzata l'avrebbe sbagliato di un
  > fattore `√af` ≈ **15,9**, cioè un DR di `1,31` stampato come `0,082`. Passo la matrice
  > annualizzata esplicitamente invece di dividere la volatilità per `√af`: nessuna
  > operazione inversa, e il lettore vede i due lati alla stessa scala.
  > Pesi **non rinormalizzati** → semantica di cassa identica ad AI Export (F6).

- [x] 9. Test di comportamento dei plugin — ✅ 18 Set 2026
  > **Note implementazione**: delegati a `test-author` come impone il mandato, con lane,
  > file unico e divieto di toccare il sorgente. **8 test**, `45 → 53` nel file.
  > Nessun difetto trovato nel mio sorgente. Il test che conta è il settimo: stessi due
  > asset, pesi scalati esattamente di ½ → NEA `1,923…` contro `7,692…` (fattore 4) e DR
  > `1,3071384803161736` **identico all'ultima cifra**. Se il plugin rinormalizzasse,
  > entrambe le righe leggerebbero `1,923…` e il test andrebbe rosso: non è vacuo.

- [x] 10. Gate — ✅ 18 Set 2026
  > **Note implementazione**: vedi tabella Evidenza. `lint` pulito, `format` idempotente,
  > `risk-all` **163 passed**, `schemas risk` **14 passed**, `api schema` rigenerato con
  > tutti e 8 i campi nell'OpenAPI. **F4 verificata sul serio**: 53 nomi unici di
  > `test_risk_analytics.py` risultano eseguiti *dentro* `risk-all`, di cui **29 miei** —
  > non mi sono fidato del colore.
  > **⚠️ Fuori pista — `api risk` NON eseguibile, e riguarda tutta la campagna**: vedi
  > sotto. Infrastruttura, non prodotto.
  > **⚠️ Fuori pista — `./dev.py format` sporca 7 file non miei**: vedi sotto.

- [x] 11. Gate `api risk` sbloccato + verifica end-to-end su dati reali — ✅ 18 Set 2026
  > **Note implementazione**: il coordinatore ha riparato il bootstrap (cache mathjax
  > completa + `node_modules`). Il server **parte**, i test **collezionano**: prima
  > `8 passed, 2 failed` per DB non popolato, poi — seminati i fixture nella *mia* data
  > dir (5612 record) — **10 passed in 10,16s**.
  >
  > **⚠️ Fuori pista — «10 passed» valeva meno di quanto sembrasse**. Ho letto le
  > asserzioni di `test_risk_query_runs_all_analytics_against_populated_test_database`:
  > verifica `status ok/partial` e `output is not None`, più controlli mirati su
  > VaR/ottimizzazione/stress/simulazione. **Nessuna riga tocca i miei otto campi.** Il
  > verde provava che i plugin non esplodono, non che i valori escano sani. Ho quindi
  > sondato l'API direttamente (`/tmp/libreFolio_n_e2e_fields.py`) — ed è lì che è uscita
  > la 14ª scoperta.
  >
  > **14ª — NEA supera il numero di posizioni, su dati reali.** Misurato sul portafoglio
  > seminato: `NEA = 11,4394` con **2** sole posizioni. Provenienza esatta
  > (`/tmp/libreFolio_n_nea_probe.py`): pesi `0,24919719587288608` e `0,15911534301518165`,
  > `Σw = 0,40831253888806773`, `cash_weight = 0,5916874611119323`, somma **1,0** precisa,
  > `Σw² = 0,08741693481374846` → `1/Σw² = 11,4394`. Rinormalizzando ai soli investiti
  > direbbe `1,9072`, cioè `≤ n`.
  >
  > **Non è un difetto**: `1/Σw²` è limitato da `n` *solo* se i pesi sommano a 1, e i
  > pesi di rischio non lo fanno — la cassa sta nel denominatore senza mai essere un
  > termine. È il prezzo, ratificato, dell'accordo con AI Export. Lo schema impone solo
  > `gt=0`, quindi **nessun vincolo è violato e nulla diventa mai rosso**.
  >
  > Ma era invisibile: 29 test unitari (pesi normalizzati), 163 di `risk-all` e 10 di
  > `api risk` non la vedevano. Aggiunto
  > `test_effective_number_of_assets_may_exceed_the_number_of_positions`, che **nomina**
  > la proprietà e fissa la forma reale. Rinormalizzare, o mettere un tetto a `n`, ora
  > fa cadere due asserzioni invece di cambiare in silenzio una decisione ratificata.
  > `risk-all` **163 → 164 passed**.

- [x] 12. Caso degenere — verifica su suggerimento del coordinatore — ✅ 18 Set 2026
  > **Note implementazione**: il coordinatore ha girato il difetto di A (serie costante →
  > barra d'istogramma larga 100 punti, perché NumPy imbottisce di ±0,5 un campione a
  > range nullo) segnalando che le mie misure hanno **lo stesso profilo di rischio**.
  > Risposta empirica, non ragionata: sondate sette finestre degeneri attraverso il
  > *plugin* (`/tmp/libreFolio_n_degenerate2.py`).
  >
  > **Il meccanismo di A non si trasferisce**: non faccio binning, quindi non esiste un
  > range nullo da imbottire. **Nessuna anomalia** su piatta, costante positiva, costante
  > negativa, monotona-poi-piatta, due punti identici, alternante minima. Ordinamento,
  > segno e confine a zero reggono ovunque.
  >
  > **⚠️ Fuori pista — la prima sonda era sbagliata, non il codice.** Il primo tentativo
  > passava i *rendimenti* a `maximum_drawdown`/`ulcer_index`, che consumano invece la
  > **serie di drawdown baseline-inclusive**, e confrontava `WR` senza negare la
  > magnitudine di riskfolio. Produsse dodici «anomalie» tutte false. Lezione speculare a
  > quella del mandato: **anche la propria sonda è un'ipotesi**. Ho letto le firme reali
  > prima di riportare qualunque cosa — nessun falso allarme è uscito da qui.
  >
  > **Guadagno collaterale**: la colonna riskfolio di quella sonda sbagliata era comunque
  > un oracolo valido, e il plugin riproduce esattamente i suoi valori sulla serie
  > costante negativa — `MDD −0,07725530557208005` e `UCI 0,04916919913152908`.
  >
  > **Scoperto un confine non asserito**: il guard del plugin è `worst > 0`, **strettamente**
  > maggiore. Una finestra piatta conserva quindi `0,0` **con la data** (vero: il giorno
  > peggiore non ha perso, e `0` è rappresentabile sotto `le=0`), mentre una tutta in
  > guadagno degrada a `None`. Rilassarlo a `>= 0` farebbe riportare `None` su una finestra
  > piatta, **in contraddizione con `max_drawdown = 0,0` sullo stesso oggetto** — e il test
  > esistente, che copre solo il ramo tutti-guadagni, resterebbe verde.
  >
  > Aggiunti `test_worst_realization_keeps_a_flat_window_and_drops_only_a_winning_one` e
  > `test_acquired_drawdown_family_collapses_on_a_monotonic_decline` (dove quantile,
  > media condizionale e massimo **devono** coincidere, perché nessuna osservazione sta
  > fuori dalla coda: il posto più economico per prendere un'inversione di segno o un
  > off-by-one nell'indice). `risk-all` **164 → 166 passed**.
  >
  > **`T=1` solleva `ValueError: sample variance requires at least two observations`** —
  > da `metrics.py`, che **non ho toccato** (`git diff --name-only` non lo elenca). La
  > finestra a osservazione singola era già non supportata prima di me: pre-esistente,
  > non introdotto, non mio da correggere.

---

## Evidenza

| Comando | Esito |
|---|---|
| `git rev-parse HEAD` | `cc33120e…` ✅ baseline |
| oracolo riskfolio 7.0.1, 2 serie × 5 misure | accordo **≤ 1 ULP** (`1,110e-16`) |
| `pytest test_risk_analytics.py -k "<misure acquisite>"` | **21 passed**, 24 deselected, 0,47 s |
| `pytest test_risk_analytics.py` (dopo `test-author`) | **53 passed** (era 45; originale 24) |
| `dev.py lint` | **All checks passed!** |
| `dev.py format` | idempotente: **530 files left unchanged** |
| `dev.py test … services risk-all` (prima di P11) | **163 passed in 29,29s** |
| `dev.py test --test-port 6248 --data-dir backend/data/test-risk-n services risk-all` | **166 passed in 28,45s** (finale) |
| `dev.py test --test-port 6248 --data-dir backend/data/test-risk-n schemas risk` | **14 passed in 0,15s** |
| `dev.py api schema` | OpenAPI rigenerato, **8/8 campi nuovi presenti** |
| `dev.py test … db populate --force` (mia data dir) | **5612 record** seminati |
| `dev.py test --test-port 6248 --data-dir backend/data/test-risk-n api risk` | **10 passed in 10,16s** ✅ |
| sonda end-to-end sui campi acquisiti (dati reali) | **8/8 presenti**, invarianti di segno e ordinamento reggono |
| `lsof -nP -iTCP:6248 -sTCP:LISTEN` | **LIBERA** |

### Valori misurati end-to-end sul portafoglio seminato

| Campo | Valore | Nota |
|---|---|---|
| `worst_realization` | `−0,0032605285193822997` | data `2026-08-31` |
| `drawdown_at_risk` | `0,0` | al 95 %: oltre il 5 % dei giorni è a un picco |
| `conditional_drawdown_at_risk` | `−0,0008000799902596155` | |
| `ulcer_index` | `0,0002864109184842319` | `≥ 0` per costruzione |
| `drawdown_confidence_level` | `0,95` | default |
| `effective_number_of_assets` | `11,439431068254814` | **su 2 posizioni** → 14ª scoperta |
| `diversification_ratio` | `1,3871156441489803` | `≥ 1` ✅ |
| `max_drawdown ≤ CDaR ≤ DaR ≤ 0` | `−0,00326 ≤ −0,00080 ≤ 0 ≤ 0` | ordinamento verificato su dati reali |

`algorithm_version` osservate attraverso l'API: `historical_kpi` **2.1.0**,
`risk_contribution` **1.1.0**.

**Non eseguito**: `services all`, `all-backend`, coverage. Il raggio d'impatto è però
coperto: gli **unici** consumatori di `RiskKpiOutput`/`RiskContributionOutput` nel
repo sono `historical_kpi.py`, `risk_contribution.py`, `test_risk_schemas.py`,
`test_risk_service.py`, `test_risk_registry.py`, `test_risk_analytics.py` — tutti
dentro `risk-all` o `schemas risk`.

### Deriva misurata delle trappole, sulla serie di test

| Trappola | Corretto | Sbagliato | Deriva |
|---|---|---|---|
| `CDaR` media ingenua | `−0,6333273658` | `−0,6332470028` | **0,013 %** |
| `UCI` con `/(T−1)` | `0,4190087283` | `0,4192883471` | **0,067 %** |
| `DaR` con `T+1` | `−0,6272197808` | `−0,6272197808` | **0 % — identico** |
| `_Rel` contro `_Abs` (MDD) | `0,6457` | `1,0196` | 58 % |

> La riga che conta è la terza: su questa serie **`DaR` non cambia** fra `T` e `T+1`,
> mentre il denominatore `α·T` di `CDaR` sì. Un test di `DaR` verde **non protegge**
> `CDaR`. È la ragione per cui la lunghezza è asserita sulla misura condizionale.

---

## Due impedimenti che non sono miei e riguardano tutti

### 1. `api <qualsiasi>` non è eseguibile in un worktree backend

> ✅ **RISOLTO dal coordinatore il 18 Set 2026.** La causa era una classificazione:
> `node_modules` e la cache mathjax erano stati assegnati ai soli mandati frontend, ma
> `server --test` **ricostruisce il frontend**, quindi servono anche a N, C, H e A. In
> più il `.cache_manifest.json` era **parziale** — il download fallito aveva lasciato la
> directory esistente ma senza `mathjax/tex-mml-chtml.js`, così `test -d vendor` dava
> vero su una cache incompleta: un falso positivo. Riparato su C, H e N. Dopo la
> riparazione il gate gira: **10 passed**. Resta come lezione di diagnosi — il referto
> qui sotto è ciò che ha permesso di distinguere un guasto d'ambiente da un rosso di
> prodotto.

```
dev.py test --test-port 6248 --data-dir backend/data/test-risk-n api risk
→ ❌ Shared backend exited during startup (code 1)
```

Il runner scarta lo stderr del server (`_server.py:269-270`, `DEVNULL` senza `verbose`),
quindi il messaggio è muto. Replicando a mano il suo comando esatto
(`dev.py server --test --no-reload --no-scheduler --workers 1`):

```
❌ Failed to download https://cdn.jsdelivr.net/npm/mathjax@3/…
   <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] … Missing Authority Key Identifier>
❌ Resource cache incomplete — the build would ship without these: mathjax
📦 Frontend was last built in unknown mode, rebuilding in debug mode...
❌ Resource cache incomplete - aborting frontend build
❌ Frontend build failed. Server not started.
```

**`server --test` ricostruisce il frontend**, che pretende la cache statica, il cui
download fallisce per TLS e non ha copia locale in un worktree fresco. Il fallimento
è **prima della collection** di pytest: nessun test è fallito, nessun test è girato.
Server mai avviato, porta `6248` libera, nessun dato toccato.

Non ho installato nulla, non ho disattivato il controllo, non ho ritentato con un
aggiramento. Ma la conseguenza va oltre me: **ogni mandato backend il cui cancello
includa una categoria `api` incontrerà lo stesso muro** — A, C e H come me. O il
cancello `api` esce dalla definizione di finito dei mandati backend, oppure serve una
decisione del coordinatore sulla cache statica.

### 2. `./dev.py format` sporca sette file che non sono di nessuno

La baseline `cc33120e` **non è black-pulita**. Un singolo `dev.py format` ha
riformattato, oltre ai miei due file, questi sette che non ho mai aperto:

| File | Righe | Natura |
|---|---|---|
| `backend/app/config.py` | 50 | cosmetica |
| `backend/test_scripts/test_api/test_brokers_api.py` | 8 | cosmetica |
| `backend/app/api/v1/system.py` | 6 | un `if` ricompattato |
| `backend/test_scripts/test_services/test_scheduler_leader.py` | 3 | righe vuote |
| `backend/test_scripts/test_services/test_scheduler_loop.py` | 2 | righe vuote |
| `backend/app/schemas/prices.py` | 2 | righe vuote |
| `backend/app/schemas/common.py` | 1 | riga vuota |

Verificate a mano: **zero cambiamenti semantici**, solo spaziatura e un
accorpamento di riga. **Non posso revertirle** — `git checkout -- …` è fuori dalle mie
regole. Restano nel working tree **non staged** e vanno **escluse dal checkpoint**.
Chiunque degli undici esegua `format` le raccoglie: conviene una passata unica di
igiene sulla baseline, decisa dal coordinatore, non undici diff che se le contendono.

---

## Contratti

| # | Verso | Stato |
|---|---|---|
| K8 | E, I | **consegnato** al coordinatore 18 Set 2026 |
| *inverso* | da A | richiesto: firma e semantica di `summarize_drawdown` invarianti dopo M6 |
| *catalogo* | da A | **decaduto** — nessun file nuovo, uso `test_risk_analytics.py` già registrato |
| *segnalazione* | per A | `summarize_drawdown.max == -MDD_Rel` **non è bit-esatto** (1 ULP): l'affermazione di esattezza nel kickoff è falsa, il valore è corretto |
