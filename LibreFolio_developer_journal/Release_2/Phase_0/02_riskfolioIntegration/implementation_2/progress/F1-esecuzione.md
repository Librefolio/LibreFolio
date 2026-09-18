# F1 — Dati di prova · piano vivo

| | |
|---|---|
| Mandato | **F1 — Dati di prova** (round 2, fase 1) |
| Worktree | `e-alfy-miniature-train` |
| Baseline | `2ec19b8f0644eeab3d1b96efa52e6c183a8f807f` ✅ verificata |
| Corsia | porta **6151** · data dir **`/tmp/librefolio-r2-f1`** |
| Coordinatore | sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca` |

> Aggiornato **dopo ogni passo**, non alla fine.

---

## Passo 1 — Misurare il collasso ✅ 2026-09-18

**Comando**

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6151 --data-dir /tmp/librefolio-r2-f1 db populate --force --clean
```

→ `✅ Total records: 5612` · `1549 price history` — **le misure del 18 settembre si riproducono esattamente**.

**Prezzi per asset** (`sqlite3 app.db`)

| id | asset | tipo | punti | primo | ultimo |
|---:|---|---|---:|---|---|
| 6, 7 | Bitcoin, Ethereum | CRYPTO | 373 | 2025-09-11 | 2026-09-18 |
| 1, 2, 3 | Apple, Microsoft, Tesla | STOCK | 267 | 2025-09-11 | 2026-09-18 |
| **4** | **RE Loan Milano** | CROWDFUND | **1** | **2026-08-29** | 2026-08-29 |
| **5** | **RE Loan Roma** | CROWDFUND | **1** | **2026-09-03** | 2026-09-03 |
| 8-17 | NVIDIA, ETF, **S&P 500**, **MSCI World**, BTP×2, Gold, iShares, KRW | — | **0** | — | — |

`is_benchmark = 0` su **tutti e 17**.

**Sonda sull'intersezione reale** (`/tmp/librefolio_f1_probe2.py`, sola lettura, via
`AssetSourceManager.get_prices_bulk` + `prepare_asset_series_set`)

```
n_observations  = 15
baseline_date   = 2026-09-03
effective_range = 2026-09-04 → 2026-09-18
serie attive    = [1, 2, 3, 4, 5, 6, 7]
unusable        = [(17, MISSING_PRICE)]
```

> **Note implementazione**: la previsione dell'analisi è **confermata alla lettera**.
> `baseline_date = 2026-09-03` è **esattamente** l'unico punto prezzo di `RE Loan Roma` (= `today − 15`),
> e da lì discendono 16 date meno la baseline = **15 osservazioni**.
> Non sono «i quattro asset senza storia»: **è un asset solo**, e il secondo prestito (`2026-08-29`,
> `today − 20`) non arriva nemmeno a vincolare perché il primo è più recente.

### ⚠️ Fuori pista 1 — due mie previsioni smentite dalla misura

1. **Avevo previsto che i prestiti e il benchmark andassero generati "feriali", o non avrebbero aggiunto nulla.**
   **Falso.** Il resolver riporta in avanti su **ogni giorno solare**: gli asset azionari hanno
   367 punti di cui **104 nel fine settimana**, pur avendo 267 righe in `price_history`.
   La scelta feriale/solare è quindi **libera**: i buchi vengono riempiti a valle.
2. **Avevo previsto che `Test KRW Stock` finisse fra gli `unusable` con ragione `MISSING_FX`.**
   **Falso**: la ragione misurata è **`MISSING_PRICE`**. Avendo *zero* righe di prezzo, il controllo sui prezzi
   scatta prima di quello sul cambio. Lo scenario «missing FX pair» che il commento del popolatore dichiara
   è esercitato altrove (WAC/portafoglio), **non** nella preparazione delle serie di rischio.
   La conclusione operativa non cambia — **non si tocca** — ma la ragione che avevo scritto era sbagliata.

### 🔴 Fuori pista 2 — un secondo vincolo che nessuno aveva nominato: la copertura FX

La sonda ha mostrato 6 errori per ogni asset in USD:

```
No FX rate found for EUR/USD on or before 2025-09-17 … (fino al 2025-09-22)
```

Misurato su `fx_rates`: **259 tassi per coppia, dal 2025-09-23 al 2026-09-18** (feriali).
I prezzi partono dal **2025-09-11**, i cambi dal **2025-09-23**: **12 giorni di scarto**.

Conteggio dei punti **realmente convertiti in EUR**:

| asset | punti totali | **in EUR** | primo EUR |
|---|---:|---:|---|
| 1, 2, 3, 6, 7 (USD) | 367 | **361** | **2025-09-23** |
| 4, 5 (EUR nativi) | 21 / 16 | 21 / 16 | 2026-08-29 / 2026-09-03 |

> **Conseguenza**: il tetto raggiungibile non è 373 ma **361 date → 360 osservazioni**, fissato dalla
> disponibilità dei cambi, non dai prezzi. **Resta molto sopra le 250 richieste**, quindi riparare i
> prestiti è sufficiente e non devo toccare gli FX. Ma se il criterio fosse stato «≥ 365», i prezzi da soli
> non sarebbero bastati e il difetto sarebbe stato attribuito al generatore di prezzi invece che ai cambi.

---

## Passo 2 — Confermare l'esclusione di KRW ✅ 2026-09-18

Misurato nella stessa sonda: `unusable = [(17, MISSING_PRICE)]`, e `serie attive = [1,2,3,4,5,6,7]`.

> **Note implementazione**: `Test KRW Stock` **non vincola** l'intersezione: è già fuori da `active`.
> Confermata l'asimmetria descritta nell'analisi — **0 punti → escluso e innocuo; 1 punto → attivo e vincolante**.
> È la ragione per cui la tabella del kickoff, che segna 🔴 quattro righe uguali, descrive tre situazioni diverse.

---

## Passo 3 — Serie piena per i due prestiti ✅ (2026-09-18)

> **Note implementazione**: quattro voci aggiunte a `price_configs` in
> `populate_price_history`, due per i prestiti. Terminano al valore nominale che il
> vecchio punto singolo portava (10 000 / 5 000 EUR), così la semantica «vale il
> nominale oggi» resta. Rimosso il blocco `loan_price_points`, ora superato.
> `_ANNUAL_VOL["CROWDFUND"]` portata da `0.00` a `0.04`.

> **⚠️ Fuori pista**: `"CROWDFUND": 0.00` era **codice morto** — la chiave non era mai
> letta, perché i prestiti non comparivano in `price_configs`. Lasciarla a zero avrebbe
> prodotto rendimenti giornalieri identici → varianza nulla → covarianza singolare →
> beta e correlazione indefiniti **su un asset posseduto**: esattamente lo stato che
> questo mandato esiste per rimuovere. È una modifica deliberata a una costante
> esistente e va dichiarata, non sepolta.

## Passo 4 — Serie per i due indici ✅ (2026-09-18)

> **Note implementazione**: `S&P 500` (#10) e `MSCI World Index` (#11) esistevano già
> come asset ma avevano **zero prezzi**. Aggiunta `_ANNUAL_VOL["INDEX"] = 0.15`.

## Passo 5 — `is_benchmark` ✅ (2026-09-18)

> **Note implementazione**: nel ciclo di `populate_assets`,
> `if asset.asset_type == AssetType.INDEX: asset.is_benchmark = True`. Rispecchia la
> regola della migrazione `003` invece di inventarne una seconda. Il 0-su-17 misurato
> non è «il popolatore ignora il flag»: è un artefatto di **ordine** — la `UPDATE` di
> `003` gira a DB vuoto, prima che gli asset esistano.

## Passo 6 — Rimisura ✅ (2026-09-18)

| | prima | dopo |
|---|---:|---:|
| `n_observations` | **15** | **360** |
| `baseline_date` | 2026-09-03 (RE Loan Roma) | 2025-09-23 (inizio FX) |
| righe `price_history` | 1 549 | **2 615** |
| record totali | 5 612 | **6 679** |
| asset con prezzi | 7 | **9** |
| `is_benchmark=1` | 0 su 17 | **2** (#10, #11) |

Il nuovo limite è il tetto FX misurato al passo 2, **alla singola unità**.

## Passo 7 — Il beta sullo schermo ✅ (2026-09-18)

> **Note implementazione**: sonda `/tmp/librefolio_f1_beta.py`, che esegue
> `ComparisonAnalytic` e `RiskContributionAnalytic` sui dati veri della corsia.
> Il benchmark si unisce alla serie preparata (`attive = [1,2,3,4,5,6,7,11]`)
> **senza restringere la finestra**: 360 osservazioni prima e dopo.

> **⚠️ Fuori pista — il criterio 3 preso alla lettera è un cancello che non prova
> nulla.** Il primo beta usciva così:
>
> ```
> beta = 0,02329969380111363   correlation = 0,014719450436334615
> ```
>
> Un numero, su 360 osservazioni, zero warning: il criterio 5 risultava soddisfatto.
> Ma ogni asset è generato con rumore **indipendente**: il mercato finto non ha un
> fattore comune, quindi un «indice mondiale» è scorrelato dal portafoglio che
> dovrebbe indicizzare. Un benchmark solo di nome — e i mandati di superficie
> avrebbero costruito una card che mostra sempre ~0,02 senza poter distinguere il
> dato dal difetto. Stessa famiglia di `effective_number_of_assets` che promette un
> conteggio: due cose coerenti ciascuna con sé, contraddittorie appena le si nomina.
>
> Correzione: seconda passata che costruisce gli indici come **miscela dei fattori
> giornalieri azionari** più un piccolo rumore di tracking, poi inclinata per
> atterrare sul prezzo finale — l'inclinazione sposta il livello, non la forma,
> quindi il co-movimento sopravvive.
>
> **Raggio d'azione nullo sui dati esistenti**: gli indici non sono posseduti (nessuna
> transazione), quindi non entrano in nessun valore di portafoglio. Solo l'analitica
> `comparison` li legge.

| | prima | dopo |
|---|---:|---:|
| `beta` | 0,0232996938 | **0,8842536997** |
| `correlation` | 0,0147194504 | **0,5202729245** |
| `information_ratio` | 0,5495498747 | 1,2683683187 |

`risk_contribution` sugli stessi dati: `effective_number_of_assets = 5,2631578947`
(Σw² = 0,19 → 1/0,19, coerente coi pesi passati) e
`diversification_ratio = 2,2807405707`. Nessun `insufficient_history`.


## Passo 8 — I cancelli ✅ (2026-09-18)

Ordine obbligato rispettato: `services risk-all` ricrea un DB pulito e cancella le
fixture, e il runner non ripopola.

| # | comando | esito |
|---|---|---|
| 1 | `test --test-port 6151 --data-dir /tmp/librefolio-r2-f1 services risk-all` | **400 passed** in 55,12s |
| 2 | `… db populate --force --clean` | **6 679 record** |
| 3 | `… api risk` | **1 failed, 9 passed** → dopo correzione **10 passed** in 9,55s |

Statici, solo sul file modificato (la baseline non è black-pulita e una `format`
globale si contenderebbe la spaziatura con gli altri mandati):
`ruff check` → *All checks passed* · `black --check` → *1 file would be left unchanged*.

> **⚠️ Fuori pista — la terza previsione mia falsificata, e la più cara.**
>
> Il rosso è `test_portfolio_optimization_supports_all_scopes_and_strategies`
> (`test_risk_api.py:540`):
>
> ```
> AssertionError: None
> assert 'partial' in {'unavailable'}
> ```
>
> Il caso è `({"kind": "portfolio"}, "min_risk", {"unavailable"})`: il test
> **pretendeva che l'ottimizzazione dell'intero portafoglio fosse indisponibile**, e
> con la storia allungata riesce — `error` è `None`, cioè non è un guasto: è il
> difetto che smette di esserci.
>
> La mia analisi aveva cercato apposta «i test che dipendono dai numeri attuali» e
> aveva dichiarato questa riga *tollerante per progetto*. Avevo letto i due casi
> tolleranti (`{"ok","partial"}`) e non il terzo, che inchioda `unavailable` esatto.
> **Il costo che mi era stato chiesto di trovare in anticipo l'ho trovato dal rosso.**
>
> **Correzione scelta, e perché non la minima.** Ribaltare l'attesa a `{"ok","partial"}`
> sarebbe stato meccanico, ma avrebbe **cancellato in silenzio la copertura del ramo
> `unavailable`** — lo stesso «cancello che non prova nulla» che questo mandato ha già
> nominato due volte. Il caso è invece ripuntato su uno scope **progettato** per non
> avere storia: `asset_set [17]`, `Test KRW Stock`, zero prezzi per scelta
> (`populate_mock_data.py:849`). Il ramo resta coperto, e in più il test ora
> **dipende** da quello scenario voluto: va rosso anche se qualcuno lo «ripara».
>
> ⚠️ **`test_risk_api.py` non è fra i file che il mandato mi assegna.** L'ho toccato
> perché il rosso è conseguenza diretta e necessaria del mio cambiamento e il cancello
> restava bloccato. Va ratificato o riassegnato dal coordinatore.

> **Guardia di regressione — proposta, non fatta.** Un'asserzione diretta («ogni asset
> posseduto ≥ 250 punti, ≥ 1 benchmark con serie, KRW ancora escluso») non ha una casa
> registrata che le somigli: `test_db_referential_integrity.py` verifica vincoli e si
> costruisce i propri dati, e un file nuovo richiede la registrazione nel runner, che
> è condiviso. Esiste già una guardia **indiretta**: i due casi `{"ok","partial"}` di
> `test_risk_api.py` tornano rossi se la storia ricollassa. Indiretta, però, e non
> etichettata.

## Passo 9 — Il sintomo originale, riprodotto sull'API ✅ (2026-09-18)

La sonda del passo 7 girava **al livello del plugin**, con pesi costruiti a mano. Il
sintomo che il coordinatore aveva misurato il 18 settembre era però una **risposta
HTTP**. Riprodotto con `httpx.ASGITransport` sul router vero, corsia `6151`.

> **⚠️ Fuori pista — due imprecisioni nel kickoff.** `comparison` **non è una
> modalità**: le modalità sono `historical` e `current_composition`, e `comparison` è
> un `analytic_code`. E `current_composition` esige
> `composition_policy="current_buy_and_hold"`, altrimenti è `422`. Il comando citato
> nel kickoff, preso alla lettera, non parte.

**Prima** (kickoff): `{"code":"insufficient_history","details":{"observations":15,"required":20}}`

**Dopo**, `HTTP 200` su entrambe le analitiche, `error = None`, nessun
`insufficient_history`:

| analitica | modalità | status | valori |
|---|---|---|---|
| `risk_contribution` | `current_composition` | `partial` | NEA 16,4686196839 · DR 1,9857170031 · vol 0,0483397669 · `cash_weight` 0,5088738900 |
| `comparison` | `current_composition` | `partial` | **beta 0,2279865428** · corr 0,6709581314 · 357 oss. |
| `comparison` | `historical` | `partial` | **beta −0,0035102924** · corr −0,0096685265 · 350 oss. |

Criteri 1-4: **soddisfatti**. Criterio 5: il beta è un numero in entrambe le
modalità — ma in una sola delle due **significa qualcosa**.

## Passo 10 — 🔴 Un difetto diverso dal mio, isolato e NON corretto

Le due modalità hanno **gli stessi dati, lo stesso benchmark, lo stesso intervallo** e
danno correlazione `0,671` contro `−0,010`. Il benchmark funziona: il problema è
**come `historical` costruisce la serie del portafoglio**.

Misurato sul DB della corsia — ed è la forma delle transazioni a dirlo:

| tipo | n | da | a |
|---|---:|---|---|
| **BUY** | **15** | **2026-07-30** | **2026-09-14** |
| DEPOSIT | 18 | 2025-09-30 | 2026-09-16 |
| *(asset NULL, cassa)* | 31 | 2025-09-30 | 2026-09-17 |

**Tutti i quindici acquisti stanno nelle ultime sette settimane.** Per l'**87%** della
finestra di 350 giorni il portafoglio era quasi interamente cassa che accumulava
versamenti: i suoi «rendimenti» storici sono salti da flusso di cassa, non movimenti
di mercato. Ecco perché la correlazione con un indice azionario collassa a zero.

> **Perché non lo correggo.** È la stessa famiglia del difetto che mi è stato
> assegnato — le analitiche vedono una finestra in gran parte vuota — ma è **un'altra
> grandezza**: là era la storia dei *prezzi*, qui la storia dei *possessi*. E il raggio
> d'azione non è confrontabile: allungare le date d'acquisto muove lotti FIFO, valori
> di portafoglio, la dashboard e le schermate della galleria, cioè **numeri già
> pubblicati**. La regola ricevuta è esplicita: davanti a un valore già pubblicato che
> cambierebbe, fermarsi e riportare.
>
> C'è poi una seconda metà che **non è mia per perimetro**: se un versamento debba
> essere neutralizzato nella serie dei rendimenti è una questione di
> `backend/app/services/risk/`, che non posso toccare.
>
> **Da instradare dal coordinatore**, non da assorbire qui.
