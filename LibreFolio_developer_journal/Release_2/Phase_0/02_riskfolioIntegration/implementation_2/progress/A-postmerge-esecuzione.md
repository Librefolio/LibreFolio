# A — Asset Global · piano vivo post-merge (Release 2)

> **Segue** [`A-esecuzione.md`](./A-esecuzione.md) (round 3, fasi 1–2, chiuso in `032b86959`).
> **Mandato**: A — *livelli di confronto per-asset di Asset Global*.
> **Coordinator**: sessione `c8328a01-f208-4ade-a352-0486d1f14de2` (Release 2 backlog analysis).
> **Baseline**: `f1047f766` ✅ verificata con `git rev-parse` · 23/09/2026 10:36:51 CEST · albero pulito.
> **Approvazione**: piano approvato dal developer il 23/09/2026, test list T1/T2 compresa.
> **Lane**: suite `6153` · `/tmp/librefolio-r2-a` — copia di prod `6163` · `/tmp/librefolio-r2-a-prodcopy`.
> **Credenziali della copia**: fornite dal developer, **deliberatamente non registrate qui**.

---

## Esecuzione — stato dei passi

| # | passo | stato |
|---:|---|---|
| 1 | piano nel journal, link incrociato | ✅ 23/09 |
| 2 | T1 + T2 scritti e provati **rossi** su `{{days}}` | ✅ 23/09 |
| 3 | R1 via `dev.py i18n update` | ✅ 23/09 |
| 4 | T1 + T2 **verdi** · `api sync` · `front check` | ✅ 23/09 |
| 5 | D3 guida review numeri (qui) + D1 doc utente (`docs-writer`) | ✅ 23/09 |
| 6 | copia di prod dalla snapshot → server `6163` per il developer | ✅ 23/09 — **acceso, in attesa della review** |
| 7 | handoff, `FROZEN` su albero e processi, dichiarati separati | ✅ 23/09 — albero `FROZEN` · server `6163` **acceso di proposito** per la review |
| 8 | correzione post-commit: la regola della finestra (pagina + piano), un solo commit | ✅ 24/09 |

> **Note implementazione (passo 1)**: il piano approvato è riportato sotto senza modifiche di
> sostanza; le decisioni arrivate durante la pianificazione (snapshot, perimetro F/J, R2-128 a F)
> sono già integrate. Ordine dei passi 2–3 esplicitato: la rete si scrive **prima** della
> riparazione, altrimenti il suo verde non prova niente (regola del round 3, fase 1).

> **Note implementazione (passo 2)**: scritti da `test-author`, eseguiti da me.
> - `frontend/src/lib/components/risk/assetSetI18n.test.ts` — ambiente node, 8 test. Compila ogni
>   foglia di `risk.assetSet.**` e dei cinque `risk.analytics.assetSet*` nelle 4 lingue con
>   `getMessageFormatter` di svelte-i18n (il percorso del runtime; `intl-messageformat` è solo
>   transitiva). **Controllo positivo**: `"lasted {{days}} d"` deve risultare malformato e
>   `"lasted {days} d"` compilare. Parità degli argomenti fra lingue letta **dall'AST**, non da
>   regex (le regex leggevano i rami interni dei plurali: 21 falsi positivi nel §9.6 del foglio 09).
> - `frontend/src/lib/components/risk/AssetSetLossComparisonSection.test.ts` — jsdom, 10 test,
>   nelle 4 lingue: la sotto-riga della peggior discesa contiene le **cifre** della durata, e
>   nessun avviso `[svelte-i18n]` durante il render. Barriera di presenza su `data-measured="true"`.
> - **Rosso provato da me**:
>   `npx vitest run src/lib/components/risk/assetSetI18n.test.ts src/lib/components/risk/AssetSetLossComparisonSection.test.ts`
>   → **`Test Files 2 failed (2)` · `Tests 12 failed | 6 passed (18)`** — 2 path, 2 file.
>   Il messaggio dice cosa non va senza aprire file:
>   *«asset 7: the sub-line reads "lasted {{days}} d" — the 438 days in the payload never reached
>   the screen»* · *«en: risk.assetSet.levels.l1.lastedDays → MALFORMED_ARGUMENT»*.
> - Lo specialista ha provato anche la mutazione della barriera (payload respinto da zod → 9 rossi
>   alla barriera, invece di 4 verdi vacui) e la riparazione simulata in memoria (18/18).

> **⚠️ Fuori pista — il mio briefing allo specialista contraddiceva un invariante scritto da me.**
> Gli avevo detto che un payload respinto da zod *«non produce righe»*. **Falso, e per una regola
> mia**: `assetSetLevels.ts` costruisce le righe dalla **selezione** e lascia vuote le celle —
> *«un asset selezionato ha sempre una riga»* è il docstring che ho scritto io in fase 2. Con la
> mia premessa, la barriera sarebbe stata messa sulla riga, che esiste anche su un payload
> respinto: **il test «nessun avviso» sarebbe stato verde senza formattare niente.** Lo
> specialista ha messo la barriera su `data-measured="true"`, e l'ha provata con una mutazione.

> **📌 Due misure dello specialista che valgono oltre questo caso**:
> - `getMessageFormatter` **lancia** su un messaggio malformato; è `$_()` a ingoiarlo — lo cattura,
>   emette `console.warn` (mai `console.error`) e restituisce il modello grezzo. **E `$_()` compila
>   solo se riceve valori**: una chiave rotta usata senza valori non logga niente.
> - Il parametro `locale` di `getMessageFormatter` **viene ignorato** (cache per solo messaggio).
>   Per questo T1 passa dal catalogo di ciascuna lingua, non dalla locale.
> - Il metodo di `L4Replay.test.ts` (confrontare il testo col `$_()` della stessa chiave) **qui
>   sarebbe verde oggi**: entrambi i lati restituiscono lo stesso modello grezzo.

> **⚠️ Fuori pista (dello specialista, rimediato)**: ha lasciato sei log
> `/tmp/libreFolio_assetset_i18n_*.log`. Rimossi da me.

> **Note implementazione (passo 3)**:
> ```bash
> PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n update \
>   "risk.assetSet.levels.l1.lastedDays" \
>   --en "lasted {days} d" --it "durata {days} g" --fr "durée {days} j" --es "duró {days} d"
> ```
> **Controllo dimensionale**: `git diff --numstat` → **4 file, `1 1` ciascuno**; il solo contenuto
> cambiato è la riga di `lastedDays`; `grep -c '{{'` → **0** in tutte e quattro le lingue. Lo
> strumento non ha riformattato nulla.
> **La rete diventa verde**: stesso comando del passo 2 → **`Test Files 2 passed (2)` ·
> `Tests 18 passed (18)`**. Rosso prima, verde dopo: le due misure, non una.

> **Note implementazione (passo 4)**:
> - `api sync` → client `generated.ts` rigenerato alle **23/09 16:20** (era del 22/09 12:33, un
>   artefatto ignorato da git che non viaggia col fast-forward). `git status` senza generati.
> - `front check` misurato alle **23/09 16:20:46** col client delle 16:20 → **`svelte-check found 3
>   errors and 41 warnings in 4 files`**: i tre ereditati (`TransactionFormModal.test.ts:787,819`,
>   `ToolExecutionMetrics.svelte:44`), **zero in un file risk**. I due test nuovi stanno in `src/`,
>   quindi **questa volta i loro tipi sono stati controllati** (lo specialista non poteva farlo).
> - `prettier --check` sui 4 cataloghi e i 2 test nuovi: pulito.
> - Le mie tre suite unit insieme:
>   `npx vitest run src/lib/components/risk/assetSetLevels.test.ts src/lib/components/risk/assetSetI18n.test.ts src/lib/components/risk/AssetSetLossComparisonSection.test.ts`
>   → **`Test Files 3 passed (3)` · `Tests 48 passed (48)`** (30 + 8 + 10).

> **📌 Registrazione dei due test nuovi — la scrive il coordinator, io la dichiaro**:
> | file | ambiente | vicino già registrato | azione proposta |
> |---|---|---|---|
> | `src/lib/components/risk/assetSetI18n.test.ts` | node | `assetSetLevels.test.ts` (`_frontend_utility.py:73`) | `front-utility core-unit` |
> | `src/lib/components/risk/AssetSetLossComparisonSection.test.ts` | jsdom | `L4Replay.test.ts` (`_frontend_portfolio.py:155`) | `front-portfolio risk-levels-component` |
> ⚠️ Lo specialista suggeriva `front_component_unit` per il jsdom: **il vicino reale sta altrove**.

> **🔴 Reperto fuori perimetro — il cancello privacy non lo esegue nessuno.** `check-orphans` sulla
> baseline trova **7 orfani**: i miei due (attesi) e **cinque di J**, tutti arrivati col merge
> privacy del 22/09 (`b66e93003` e seguenti): `privacyStore.test.ts`, `privacyStoreSsr.test.ts`,
> `currencyFormat.test.ts`, `maskable.test.ts` e **`moneyRenderSites.test.ts`** — cioè proprio il
> cancello che *«testa la premessa della regola»* privacy. Esiste, è verde se lo lanci a mano (l'ho
> fatto il 22/09), e **nessuna azione di `dev.py test` lo lancia**. È la forma R2-19 esatta:
> *un artefatto che esiste, scambiato per un artefatto usato*. → coordinator (runner) e J.

---

## D3 — Guida alla review dei numeri sulla copia di prod

> **Per chi guarda**: il developer, sui suoi 15 asset, su `http://localhost:6163`, in italiano.
> **Cosa non contiene, di proposito**: nessun numero atteso. Ogni cifra di questa pagina integra
> sulla finestra (Ⓕ): una cifra citata qui sarebbe falsa domani. Contiene **cosa guardare**, **cosa
> è vero per costruzione** (e quindi verificabile a occhio) e **cosa sarebbe un difetto**.
> ⚠️ Il server della copia fa girare lo **scheduler** come in prod: i prezzi di oggi si aggiornano
> mentre guardi, quindi due sguardi a distanza possono dare cifre diverse (Ⓓ). È il comportamento
> di prod, non un difetto.

**Dove**: Asset → tab **Correlazione**. Le quattro sezioni, in ordine: matrice · *«Quanto ha fatto
male ciascuno?»* · *«Quanto ha pagato ciascuno per il suo rischio?»* · replay (chiuso).

| # | cosa fare | cosa devi vedere | 🔴 è un difetto se… |
|---:|---|---|---|
| 0 | **R1**: guarda la colonna *Peggior discesa* | sotto ogni cifra, «durata **N** g» con un numero | compare `{days}`, `{{days}}` o la sola «durata  g» · la console mostra `MALFORMED_ARGUMENT` |
| 1 | scegli 2-3 asset **quotati** di lunga storia e apri i **dettagli di calcolo** della sezione — mostrano **osservazioni** e **copertura**, non le date. Poi aggiungi un asset **quotato** con storia più corta | le osservazioni **cambiano** e con loro le cifre degli **altri**: di norma **scendono**, perché la finestra comincia più tardi (e la copertura scende sotto il 100 %); possono **salire** se il nuovo asset ha prezzi anche nel weekend e gli altri no — il calendario diventa giornaliero e il risultato «parziale» (riga 9) | le cifre degli altri cambiano **ma osservazioni e copertura no** |
| 1b | aggiungi un **crowdfunding** (asset senza prezzi) | viene **escluso**: riga di trattini, la sezione dichiara che un asset è stato escluso, **le osservazioni non cambiano** e nemmeno le cifre degli altri | le cifre degli altri cambiano · l'asset sparisce senza avviso |
| 2 | *Risalita al massimo* contro *Sotto il massimo*, stessa riga | vale `\|x\| / (1 − \|x\|)`: −20 % → +25 %, −50 % → +100 %, **a meno dell'arrotondamento a un decimale** | l'identità non torna — è vera **per costruzione** (`backend/app/services/risk/metrics.py:392`, entrambe dallo stesso `current_drawdown`) |
| 3 | volatilità in tabella contro il punto sullo scatter (tooltip) | lo stesso numero | differiscono — la tabella legge la cifra dello scatter |
| 4 | il benchmark scelto nella Dashboard, **non** selezionato qui | compaiono *Beta* e *Correlazione*, e sullo scatter il rombo del benchmark porta il **nome** dell'asset | non compaiono · compaiono **quando il benchmark è fra i selezionati** (allora devono sparire, con la nota) · il rombo è etichettato `#numero` |
| 5 | una cella senza dato | `—` e, sotto la tabella, *«Un trattino significa che la misura non è stata possibile per quell'asset su questa finestra — non significa zero.»* | un `—` senza la nota, o uno `0` al posto del `—` |
| 6 | restringi il periodo a **~2 settimane** | la peggior discesa resta misurata (le bastano 2 osservazioni); *Giornata storta*, *Mese storto* e tutta la sezione rischio/rendimento **dichiarano** perché mancano (ne servono 20) | le sezioni restano vuote **senza** dire perché |
| 7 | tutta la pagina | nessun euro, nessuna classifica, nessun colore che distingua un asset dall'altro, **nessuna retta** sullo scatter — e la nota sotto lo scatter **non parla di una retta** | uno qualunque dei cinque |
| 8 | la volatilità dello stesso asset qui e nello scatter della Dashboard | **può differire** | ❌ **non è un difetto**: tre pagine, tre preparazioni (Ⓔ). Confronta le **osservazioni** nei dettagli: differiscono anche quelle. ⚠️ Confronta solo cifre **per asset**: le cifre di **portafoglio** della Dashboard sono sotto la riserva **F2** (sotto) |
| 9 | le sezioni, sui tuoi dati | alcune selezioni rispondono **«parziale»**: la sezione mostra in ambra lo stato (*«Parziale»*) e la nota del backend *«Risk result uses incomplete or carried-forward source data.»* — **in inglese in ogni lingua**, perché è testo del backend mostrato così com'è. **Due meccanismi**, entrambi via `CARRIED_FORWARD` (`backend/app/schemas/portfolio.py:244-245`) → `partial` (`backend/app/services/risk/service.py:803`): ① un asset **non quotato** in un giorno in cui un altro lo è (es. il BTP nei weekend, accanto a un ETF justETF) entra col suo ultimo prezzo; ② il **punto di partenza** stesso è riportato — se il giorno prima dell'intervallo un asset non ha quotazione (es. un intervallo che comincia di lunedì), perché la baseline si conta fra i punti riportati (`series_preparation.py:311-313`). ⚠️ **I dettagli di calcolo non mostrano i punti riportati**: solo osservazioni, copertura, fattore di annualizzazione e base di rendimento | una sezione parziale **senza** stato né nota |

🔑 **La riga 1 è quella che produrrà il primo dubbio.** La finestra comune segue **tre regole**
(`backend/app/services/series_preparation.py`):
1. **comincia** il primo giorno in cui **ogni** asset selezionato può essere **valutato** nella valuta
   del tab — prezzo **e** cambio: un cambio mancante ritarda l'inizio come un prezzo mancante. È
   l'**unico** uso dell'intersezione di `:237-239`, che lavora su prezzi già convertiti. Se tutti
   hanno storia prima dell'intervallo, è il **giorno prima** dell'intervallo (i prezzi si caricano da
   lì: `backend/app/services/risk/service.py:514-517`);
2. da lì conta **ogni data in cui almeno un asset è quotato** — l'**unione** delle quotazioni fresche
   (`:236`; fresca = `backward_fill_info.days_back == 0`, `_price_is_fresh`, `:123-125`);
3. un asset **non quotato** quel giorno entra col suo **ultimo prezzo** (`:287` tiene le date in cui
   ogni asset ha un valore, anche riportato). Il suo rendimento quel giorno è **zero se è nella valuta
   del tab**; se è in un'altra valuta è la **variazione del cambio**, perché il prezzo riportato viene
   convertito al cambio del suo giorno (`backend/app/services/asset_sources/price_query.py:403-407`) —
   zero solo se è riportato anche il cambio, come nel weekend. Il risultato diventa `partial` (riga 9).

Per questo aggiungere un asset con storia più corta cambia le cifre degli altri: la finestra comincia
più tardi. È il prezzo della clausola ⓪ (punti confrontabili sullo stesso grafico) e non ha un rimedio
che non rompa quella. Una cifra che cambia quando aggiungi un asset **è corretta se le osservazioni
sono cambiate**, ed è per questo che la guida chiede di guardare le osservazioni **prima** della cifra.
➕ **Con un benchmark attivo** il benchmark entra nella finestra delle due sezioni di confronto
(`backend/app/services/risk/service.py:171`, `comparison_dependency_asset_ids`): un benchmark con
storia più corta ne sposta l'inizio per *«Quanto ha fatto male ciascuno?»* e *«Quanto ha pagato
ciascuno?»*, **non** per la matrice né per il replay. Quindi le osservazioni delle due sezioni di
confronto possono essere **meno** di quelle della matrice sopra: non è un difetto.

### Riserve aperte — owner **Risk**, candidati e non verdetti

> Ricevute dal coordinator il 23/09, da verificare col developer nel **tempo ②**. Questa guida le
> **nomina** e dice **dove possono comparire**; **nessuna riga sopra trae una conclusione che
> dipenda da esse**. Le mappe «dove» sono misurate nel codice e, per F2, sui dati della copia.

| | candidato | può comparire su Asset Global? | dove sì |
|---|---|---|---|
| **C2** | l'orizzonte del bootstrap è forse contato in **osservazioni**, non in giorni (`backend/app/services/risk_plugins/simulation.py:403`) | ❌ **no**: la simulazione non è annunciata per `asset_set` (`supported_scopes` = `ASSET, PORTFOLIO`) | Dashboard, Broker Detail, Asset Detail — il gradino *Simulazione* del L4 |
| **F2** | gli asset **senza serie di prezzo** diventano **liquidità allo 0 %** (`backend/app/services/risk/service.py`, ramo `PORTFOLIO` dei pesi utilizzabili) | ❌ **no**: senza pesi non c'è liquidità in cui confluire; l'asset viene **escluso** con avviso — **misurato sulla copia** (riga 1b) | le cifre **di portafoglio** di Dashboard e Broker Detail (i 4 crowdfunding pesano il 30,5 %, dato del coordinator) |

⚠️ **Ma la stessa domanda di C2 tocca una colonna mia, e la dichiaro invece di tacerla.**
*Mese storto* è `asset_set_var` con `horizon_days = 21`, e il plugin conta quei 21 come
**osservazioni consecutive della griglia congiunta** (`backend/app/services/risk_plugins/asset_set_var.py:83`,
`horizon_observations = observations − horizon_days + 1`). È l'intento dichiarato anche per il L1 di
portafoglio (`MONTHLY_VAR_HORIZON_DAYS`, *«Horizon, in observations»*): su una griglia di giorni di
borsa 21 osservazioni sono circa un mese di calendario. **Quanti giorni di calendario siano davvero
dipende dalla griglia, cioè dalla selezione** — e dal 24/09 è **misurabile**:
- **con un ETF justETF nella selezione** la griglia è **giornaliera di calendario** — justETF registra
  sabato e domenica con la chiusura del venerdì (misura del coordinator sulla snapshot: 14 448 righe,
  il 100 %), e quelle righe contano fresche (regola 2) — quindi *Mese storto* = **21 giorni di
  calendario = 3 settimane**;
- l'asset `8` (BTP, `borsa_italiana`, nessuna riga nel weekend) **da solo** gira su giorni di borsa,
  ≈ 1 mese — **e solo se** non c'è un benchmark justETF, perché l'insieme preparato include gli asset di
  confronto (`backend/app/services/risk/service.py:170-171`);
- il *Mese storto* **di portafoglio** (Dashboard, Broker Detail) resta 3 settimane **in ogni caso**:
  legge la TWRR della storia del report (`backend/app/services/risk/service.py:932-941`), che ha **un
  punto per ogni giorno di calendario** — `portfolio_engine.py:870-871` (`while current <= self.date_to`,
  uno stato per giorno; i giorni fermi riusano lo stato precedente, `:874-911`) e
  `portfolio_service.py:1305-1425` (`get_history`, *«Return daily portfolio value series»*, taglia
  sull'intervallo senza campionare).

Quindi l'etichetta dipende **anche dall'unità dell'orizzonte** (osservazioni o giorni), non solo da come
si contano le righe del weekend. **Nessun verdetto**: è la domanda di C2, owner Risk, tempo ②.
L'etichetta non si cambia finché quella non è risolta.
➕ **La stessa domanda tocca anche *Giornata storta* e la volatilità**: su una griglia giornaliera il
5 % peggiore dei giorni e la dispersione includono i giorni **riportati a rendimento zero** (regola 3).
Stessa riserva, stesso owner, nessun verdetto.

> 📌 **Misura datata, istantanea e non costante** (Ⓕ): 23/09/2026, copia di prod su `6163`, finestra
> **richiesta** `2024-01-01 → 2026-09-22` (995 giorni). Selezione `[1, 3, 8]` → **574 osservazioni** su
> uno span **osservato** di **574 giorni**, dalla baseline `2025-02-25` (prima quotazione del BTP): **una
> osservazione per giorno di calendario**, f = 365,0. La copertura 574/995 = 0,577 **non** ha per
> denominatore lo span richiesto per definizione: è `osservazioni / date dell'intervallo con almeno una
> quotazione fresca, esclusa la baseline` (`series_preparation.py:344-345`), che qui vale 995 solo perché
> un ETF justETF quota ogni giorno di calendario.
> Con `[1, 3, 8, 12]` (12 = crowdfunding senza prezzi) → **574**, `12` escluso con `missing_price`,
> avviso `assets_excluded`.
> **Causa del `partial` su `[1, 3, 8]`**: il BTP non ha righe nel weekend e viene riportato in avanti
> (176 volte, misura del coordinator sulla snapshot) → `CARRIED_FORWARD` → `partial` (riga 9). La
> selezione `[1, 2, 3, 4]`, tutti justETF, risponde `ok`. Non è un difetto di A: owner Risk, tempo ②.

> **⚠️ Fuori pista (mio, nella guida stessa)**: la prima stesura della riga 6 diceva *«restringi a
> ~1 mese»*. Un mese sono ~21 sedute, cioè **più** delle 20 osservazioni minime dei quattro
> plugin: la prova avrebbe mostrato tutto pieno e il developer avrebbe concluso che la
> dichiarazione dello stato misto non funziona. **Una guida di verifica con la soglia sbagliata
> produce un falso negativo con l'aria di una misura.** Corretta a ~2 settimane. E la citazione
> della nota sotto la tabella era una parafrasi fra virgolette: ora è il testo esatto del catalogo.

> **⚠️ Fuori pista (mio, nella guida, trovato scrivendo le riserve)**: la prima stesura della riga
> 1 diceva *«aggiungi l'asset più giovane: la finestra si restringe»*, e *«apri i dettagli
> (finestra, osservazioni)»*. **Due premesse false insieme.** I dettagli mostrano un conteggio, non
> le date (lo aveva trovato lo specialista doc). E sui dati del developer l'asset «più giovane»
> potrebbe essere un **crowdfunding senza prezzi**, che non restringe niente: viene escluso — misurato
> ora, osservazioni invariate. Il developer avrebbe letto la riga 1 come smentita **dal prodotto**,
> quando era smentita **dalla guida**. Ora distingue asset quotato (1) e senza prezzi (1b).

---

## Passo 5 — D1 doc utente + un difetto nuovo, trovato scrivendola

> **Note implementazione (D1)**, `docs-writer`, solo `.en.md`, verificato da me contro il codice:
> - `mkdocs_src/docs/user/assets/correlation.en.md` — **pagina nuova** (196 righe) sul tab
>   Correlazione: selezione, le quattro sezioni coi titoli reali, e la parte *«leggere i numeri»*
>   (finestra per intersezione, trattini, stato misto, preparazioni diverse fra pagine). Nessuna
>   cifra dipendente dalla finestra, nessuno screenshot (la gallery non è rigenerata).
>   ⚠️ **Rettificato 24/09**: «finestra per intersezione» era la mia premessa sbagliata — l'intersezione
>   fissa solo l'**inizio** della finestra; le date misurate sono l'**unione** delle quotazioni fresche,
>   con gli asset non quotati riportati al loro ultimo prezzo. La pagina è corretta nel commit successivo
>   (passo 8).
> - `user/assets/index.en.md` — la frase di F (§9.1) sul controllo Abs/%, **riformulata da me**
>   perché la proposta ometteva un fatto misurato: il controllo è visibile e premibile **anche sul
>   tab Correlazione** (`+page.svelte:1439-1443`, la guardia è `viewMode`, non il tab) e **non è
>   salvato** (`$state` puro, `:222`); più la voce *🧪 Correlation Tab* nelle Features.
> - `mkdocs.yml` — **una riga aggiunta** (`:758`), fra *Create & Edit* e *Asset Detail*:
>   `          - Correlation: user/assets/correlation.md`. File condiviso: solo aggiunta.
> - `mkdocs build` strict: exit 0 · `check-links`: 80 validi (+3 ancore rotte già in eccezione,
>   non mie; 9 risolti a runtime) · **nessun `translate-stamp`**: `index.en.md` ha ora debito di
>   traduzione vero, e uno stamp lo nasconderebbe.

> **🔴 Fuori pista — quattro premesse del mio briefing allo specialista erano false.**
> 1. *«la finestra è mostrata nei dettagli di ogni sezione»* — mostrano **osservazioni**, non date.
> 2. *«tutte le cifre usano le date che condividono gli asset selezionati»* — **incompleto per due
>    motivi**. ① Quando si applica un benchmark, `service.py:171` lo **prepara insieme** alla selezione
>    (`comparison_dependency_asset_ids`), quindi un benchmark giovane **restringe anche** la finestra
>    dei miei due livelli; matrice e replay non lo includono. ② *(aggiunto 24/09, trovato da Risk)* le
>    date misurate **non sono condivise**: sono l'**unione** delle quotazioni fresche
>    (`series_preparation.py:236`), e chi quel giorno non è quotato entra col suo ultimo prezzo (`:287`);
>    l'intersezione (`:237-239`) fissa solo l'inizio. **Il motivo ① smentisce il docstring che ho
>    scritto io** in `AssetSetComparisonLevels.svelte:19-27` (*«un punto di quest'onda e una cella
>    della matrice sono misurati sulle stesse date»*). Vero senza benchmark, falso con.
>    → Il file è **congelato per me** finché R2-128 è aperto (F ci scrive una riga). **Non lo tocco:
>    lo segnalo** al coordinator; lo correggo io quando il vincolo decade, o F nella sua riga.
> 3. *«mai il tetto di 100»* — si apre a 100 se ne possiedi ≥100 o ne avevi lasciati 100. Il
>    garantito è: **mai sui primi cento della lista**.
> 4. il benchmark è condiviso anche con **Broker Detail**, non solo con la Dashboard.

> **🔴 Difetto nuovo, mio, trovato dallo specialista: la nota sotto lo scatter di L3° descriveva
> una retta che il grafico non può disegnare.**
> Usavo `risk.levels.l3.scatter.note` (di **Risk**, scritta per il L3 di portafoglio), che apre con
> *«Sopra la retta significa pagato meglio per il rischio preso»*. Sulla Dashboard è vero: la retta
> c'è. **Sulla mia pagina la retta è impossibile per costruzione** — e la frase rimetteva **a
> parole** esattamente il giudizio che la forma del payload rende inesprimibile. Tutti i cancelli
> verdi: chiave presente, ICU valido, referenziata. È la mia fase 2 (`032b86959`).
> - **Rete prima**: in `assetSetI18n.test.ts` un blocco *«L3° never describes a line it cannot
>   draw»* che legge **dal sorgente del componente** quale chiave rende la nota (così segue il
>   componente se cambia chiave), con **controllo positivo** (la nota di portafoglio deve essere
>   riconosciuta) e parole di retta nelle 4 lingue. **Rosso provato**: `Test Files 1 failed (1)` ·
>   `1 failed | 10 passed (11)`, con le quattro frasi stampate.
> - **Riparazione**: chiave **nuova e mia**, `risk.assetSet.levels.l3.scatterNote`, via
>   `dev.py i18n add`, che tiene la sola parte vera (*atteso ≠ vissuto*) e toglie la retta; il
>   componente la usa. La chiave di Risk **resta viva** (`L3RiskAdjusted.svelte:173`), non toccata.
> - **Verde**: `npx vitest run src/lib/components/risk/assetSetI18n.test.ts src/lib/components/risk/AssetSetLossComparisonSection.test.ts src/lib/components/risk/assetSetLevels.test.ts`
>   → **`Test Files 3 passed (3)` · `Tests 51 passed (51)`**.
> - **Dimensione**: `+3/−2` per catalogo, atteso `+2/−1`. **La riga in più è la virgola JSON** su
>   `noBenchmark`, che era l'ultima chiave del blocco — provato: tolti prefisso e virgola, le due
>   righe coincidono. `i18n audit`: **3404 complete, 0 incomplete**.
>
> 🔑 **La forma**: *riusare una stringa di un'altra superficie è riusare le sue premesse.* La
> chiave era giusta dove è nata e falsa dove l'ho portata, e nessun controllo di presenza o di
> sintassi può vederlo: serve un controllo sul **contenuto**, legato alla **pagina**.

> **Segnalati, non miei** (dallo specialista, da girare): «Per nome» nell'ordine della matrice
> ordina per **ID**, non alfabetico · heatmap e lista coppie usano **colori invertiti** (−1 rosso /
> +1 blu contro coppie positive rosse) · il rombo del benchmark sullo scatter è etichettato `#id`
> · il messaggio di blocco del replay offre *«un sostituto»* che su questo tab non esiste ·
> `financial-theory/…/correlation.en.md` contraddice il codice su due punti · il tab misura nella
> valuta **di istanza**, non in quella dell'utente · la selezione ricordata è **per browser**, non
> per utente.
>
> ⚠️ Una di queste è **mia**: l'etichetta `#id` del rombo viene da `buildAssetSetBenchmarkPoint`,
> che risolve il nome da `assetLabels` — la mappa della **selezione**, che per costruzione **non
> contiene** il benchmark. **Riparata** (sotto).

> **🔴 Difetto nuovo, mio — il rombo del benchmark era `#id` su ogni grafico, e il test era verde
> su uno stato impossibile.** `selectionLabels` (guscio, `AssetSetRiskPanel.svelte:138-146`) scorre
> solo `selectedAssetIds`; il benchmark, per regola del validator, **non è mai** fra i selezionati;
> quindi `label()` ricadeva **sempre** su `#id`. E il test del mio helper usava una `LABELS` che
> **conteneva** l'id 41 del benchmark: verde su una mappa che la produzione non può costruire.
> - **Rete prima**: *«names the reference through the resolver when the selection map cannot»* —
>   **rosso provato**: `expected '#41' to be 'MSCI ACWI'` (`Test Files 1 failed (1)`).
> - **Riparazione**: `buildAssetSetBenchmarkPoint` accetta un `resolveName` **opzionale** (i chiamanti
>   esistenti non cambiano); `AssetSetRiskReturnSection` gli passa lo store asset, come fa il L3 di
>   portafoglio (`RiskLevelsPanel`, `benchmarkName`), leggendo `$assetStoreVersion`. Il file
>   congelato (`AssetSetComparisonLevels.svelte`) **non è toccato**.
> - ⚠️ **Limite dichiarato**: il nome sta nel canvas ECharts, e `ScatterChart` (di **I**) non lo
>   espone nel DOM — **nessun test di componente può vederlo senza toccare un file di I**. La rete è
>   sul contratto dell'helper; il chiamante è coperto dai tipi (`front check`) e dall'occhio del
>   developer (riga 4 della guida D3).

**Verifica finale del passo 5**, 23/09 16:51:26, client delle 16:20:
- `npx vitest run src/lib/components/risk/assetSetLevels.test.ts src/lib/components/risk/assetSetI18n.test.ts src/lib/components/risk/AssetSetLossComparisonSection.test.ts`
  → **`Test Files 3 passed (3)` · `Tests 53 passed (53)`**
- `front check` → **3 errori / 4 file, gli stessi 3, zero in un file risk**
- `prettier --check` su tutti i file toccati: pulito · `i18n audit`: 3404 complete, 0 incomplete

---

## Passo 6 — la copia di prod, e la prova d'uso sui dati veri

> **Note implementazione (passo 6)**:
> - Copia creata **dalla snapshot** del coordinator, mai dal main checkout:
>   `004_release_1_2_0_schema`, marcatore assente, scrivibile. **Rinfrescata** subito prima di
>   accendere il server (la precedente, con il mio `list`, è in `…prodcopy.prev-20260923-165222`):
>   il developer deve trovare i suoi dati, non le mie prove.
> - `dev.py user --test-db list` con `LIBREFOLIO_TEST_DATA_DIR` → 1 utente. **Provato che ha letto
>   la copia e non il DB di default del worktree**: quello (`backend/data/test/sqlite/app.db`, 12 KB,
>   il mio Fuori pista 6 del round 3) contiene la sola tabella `alembic_version` e non può
>   contenere utenti. Letta direttamente, la copia ha 1 utente e **15 asset**, `journal_mode=wal`.
> - Server: `dev.py server --test --port 6163 --data-dir /tmp/librefolio-r2-a-prodcopy` →
>   **HTTP 200 dopo ~90 s**, il log dichiara `db_path /private/tmp/librefolio-r2-a-prodcopy/…`
>   *«15 tables (schema up to date)»*, nessun rate-limit dei provider.
> - Il build servito (`frontend/build/…/SpJMWftP.js`) contiene `lasted {days} d` **e** la nota
>   nuova dello scatter, e **nessuna** occorrenza di `lasted {{days}} d`.
>
> **Prova d'uso end-to-end**, sonda nella cartella di sessione (password da variabile d'ambiente,
> mai stampata né registrata; stampa forme e stati, **nessuna cifra** — Ⓕ):
> ```
> login                                  HTTP 200
> assets                                 HTTP 200, 15 visibili
> risk/query (5 codici, 1 richiesta)     HTTP 200
>   asset_set_kpi / var 1g / var 21g / drawdown / risk_return    tutti ok, 4 righe ciascuno
>   asset_set_drawdown                   durate intere ✅  ← il dato che R1 ora rende
>   asset_set_risk_return                chiavi oltre items: []   ← clausola ①, in produzione
> ```
>
> **⚠️ Fuori pista (della mia sonda)**: il primo giro ha dato `422` due volte. **Non era il
> prodotto**: indovinavo la rotta degli asset (`/assets` invece di `/assets/query`), e il secondo
> `422` era la cascata — zero asset → `asset_ids: []` → rifiutato dallo schema. Una sonda che sbaglia
> la domanda risponde con un errore che ha la forma di un difetto; l'ho letta nel backend prima di
> concluderne qualunque cosa.
>
> 📌 **Ciò che non ho potuto guardare io**: la pagina resa. Non ho un browser pilotabile in questa
> sessione. La prova sopra dice che il **dato** arriva e che il **build** contiene il testo giusto;
> che la sotto-riga si veda nel posto giusto lo dice solo l'occhio del developer (guida D3, riga 0).

---

> **Stato**: piano, nessuna riga di codice. **Baseline verificata**: `f1047f766`, pulita,
> 23/09 10:36:51 CEST. Porte `6153`/`6163` libere, `/tmp/librefolio-r2-a*` assenti (reboot).
> **Perimetro di A dalla tabella nuova**: *livelli di confronto per-asset di Asset Global*.

---

## 0. Tre rettifiche ai fogli 08/09 — prima di tutto, perché cambiano cosa va fatto

### 0.1 🔴 «`risk-lab` mai eseguito» (09 §2.1, 08 §8.8) — **falso, e provato dal repo**

| revisione | cosa registra il mio piano vivo (tracciato) |
|---|---|
| `daa03c0f2` · 21/09 19:23 | `front-portfolio risk-lab` ✅ **6/6** — «da non eseguibile a verde» |
| `032b86959` · 21/09 21:57 | `front-portfolio risk-lab` ✅ **11/11 (erano 6)** |
| `032b86959` → `f1047f766` | spec **byte-identico**: `git diff --stat` vuoto, 2057 righe entrambi |

**Vero è solo**: *mai eseguito sull'albero integrato* (dopo D/I/J). L'istruzione del developer —
*farlo girare prima di aggiornarlo* — resta giusta. **La premessa «rimasto super indietro» no**.

**Previsione statica** (etichetta: *previsione, non misura*): zero testid scomparsi — i 15
«mancanti» di una sonda letterale sono tutti **composti da template** (`{testId}-health`,
`risk-bulk-{action}`, `risk-correlation-ordering-{mode}`, `{testId}-toggle/-body`); nessuna
asserzione dipende dal banner beta tolto da E né dalla privacy (default off, D3). Atteso verde.

### 0.2 🔴 §9.2 ha misurato **il formatter sbagliato** per questa pagina

§9.2 dice: *la maschera copre il valore, non il canale* → `€` e `.currency-symbol` reggono.
Vero per `currencyFormat.ts:41-47`. **Ma su Asset Global quel formatter non rende denaro.**

L'unico sito di denaro della pagina è `L4Replay`, che importa `formatCurrencyAmount` da
`riskAnalysisHelpers.ts` — e **J lo ha reso asimmetrico apposta**, e lo ha pinnato:

> `riskAnalysisHelpers.test.ts` — *«drops the currency marker too, unlike the shared currency
> formatter»* — **eseguito ora: `Test Files 1 passed (1)`**. Sotto privacy ritorna `•••` nudo.

| # | asserzione | privacy OFF | privacy ON |
|---|---|:---:|:---:|
| 1 | `MONEY_PATTERN` (valore) | ✅ | 🔴 cieca |
| 2 | `'€'` | ✅ (lo emette `Intl`) | 🔴 **cieca** — il formatter scarta il marcatore |
| 3 | `.currency-symbol` | 🔴 **cieca sempre** su questo percorso | 🔴 cieca |

La 3 la emette **solo** `formatCurrencyAmountHtml` (`currencyFormat.ts:68,87`): è un guardiano
contro *un altro* formatter che comparisse qui, non contro questo. → **Su questa pagina la §1.6
originale («passa misurando nulla», sotto privacy) era giusta; la rettifica no.** È il §3.5 del
registro: ragionamento corretto sul pezzo che non decide.

### 0.3 Minore — R1 punta a `:163`, il sorgente è `:138`

`:163` è il frame a runtime della console; nel sorgente la chiamata è
`AssetSetLossComparisonSection.svelte:138`. File invariato da `032b86959`.

---

## 1. Perimetro

| | file |
|---|---|
| ✅ **miei** | `AssetSetComparisonLevels.svelte` · `AssetSetLossComparisonSection.svelte` · `AssetSetRiskReturnSection.svelte` · `assetSetLevels.ts` + `.test.ts` · chiavi `risk.assetSet.levels.*` e `risk.analytics.assetSet*` |
| 🔴 **di F** dalla tabella nuova | `AssetSetRiskPanel.svelte` (monta i miei livelli) · `AssetSetCorrelationSection` · `AssetSetReplaySection` · `risk-lab.spec.ts` (*«a fine review»*) |
| 🔴 **di Risk** | `riskAnalysisHelpers.ts` (porta il mio flag `includeAssetSetLevels`) · `riskPanelController` (porta `assetSetBenchmarkId`) · `levels/*` |
| 🔴 **di J** | `utils/privacy/maskable.ts` e l'asimmetria di `formatCurrencyAmount` |
| 🔴 **di I** | `ScatterChart` / `scatterChartHelpers` (li consumo) |

⚠️ **Storia**: nel round 3 `risk-lab.spec.ts` e il guscio erano miei (per il coordinatore Risk).
La tabella nuova li dà a F. **Adotto la tabella nuova** e non tocco quei file senza assegnazione.

---

## 2. Difetti di mia competenza

### R1 🔴 `lastedDays` — il solo con causa esatta, ed è mio

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n update \
  "risk.assetSet.levels.l1.lastedDays" \
  --en "lasted {days} d" --it "durata {days} g" --fr "durée {days} j" --es "duró {days} d"
```

Solo le graffe; abbreviazione invariata (sub-riga compatta di tabella). Gemella singolare
`risk.levels.l1.durationDays` usa già `{days}`: **la mia era l'unica rotta** (conferma §9.6).
**Verifica**: `git diff --stat` = 4 file, `+1/−1` ciascuno · T1 + T2 sotto · a schermo sulla copia di prod.

> **⚠️ Fuori pista (mio, da registrare)**: il valore l'ho scritto **a mano, in un letterale
> Python** che generava il JSON. `{{` è l'escape di `{` nelle f-string — **ma quella non era
> una f-string**, e l'escape è finito nel catalogo verbatim. **Nessuno dei miei cancelli parsa
> ICU**: `i18n audit` misura presenza · `front check` tipi · E2E asseriva `data-measured`, non il
> testo · vitest copriva gli helper. Quattro verdi, una chiave che non rende nulla.

### §1.6 / §9.2 — cancello euro: **misura consegnata, riparazione di J poi di F**

✅ **Deciso 23/09** (developer, via coordinator): per la regola *«la privacy nasconde il numero, non
la valuta; se la nasconde è un errore»*, l'asimmetria di `formatCurrencyAmount` è **un difetto → J**
(unico scrittore di quelle righe e del pin a `riskAnalysisHelpers.test.ts:387`). Il pin privacy sul
cancello va a **F**, **dopo** J, perché la riparazione di J cambia l'output a privacy accesa.
La mia tabella 0.2 è l'input per entrambi. **Nel mio piano non resta nulla da scrivere.**

Suggerimento per F, se utile: con privacy ON e la regola intatta `L4Replay:147` ritorna `''`
**prima** del formatter; con la regola rotta ritorna il segnaposto. Quindi *«nessun segnaposto nel
pannello»* prende la regressione anche sotto maschera, qualunque forma J scelga per il segnaposto.

### §1.7 / §2.3 — `panelTitle`: **di F, non mia**

Introdotta da F in `f2ad97dd4` (18/09, verificato). Io l'ho resa orfana smontando il monolite
(`daa03c0f2`), ma la chiave e la sua gestione di fine round sono di F. **Nessuna azione mia**, e per
decisione del developer non si cancella ora. (Nessuna **mia** chiave viva è dichiarata morta.)

### §2.6 — deriva di commenti: le mie due sono **in file di F**

**Nei miei 4 file: zero** (`service.py:170`, `riskStore:131`, `correlationHelpers.ts:28` esatte).
Le due derive che segnalo sono **citazioni scritte da me/S5 in file ora di F**:
`AssetSetRiskPanel:42` (`:874` → ora `:879`) · `AssetSetReplaySection:31` (`service.py:840` → ora `:873`).

⚠️ **Non sono quelle della §2.6 del foglio 09** (`L4Replay:47`, `L4Shock:46` → famiglia Risk): la
correzione del coordinator risponde a una coppia che non ho citato. Le mie due vanno **a F**.

---

## 3. Sviluppi concordati da proseguire

| # | voce | stato | nota |
|---|---|---|---|
| **D1** | **Doc utente dei livelli** — nel DoD della mia fase 2 | 🔴 **mai consegnata** | nessuna pagina utente sul tab correlazione. `docs-writer`, solo `.en.md`. Pagina e nav **condivise con F** |
| ~~D2~~ | ~~R2-128 — sync FX sul laboratorio~~ | ➡️ **passato a F** (coordinator, 23/09) | era sulla mia fase 2 e l'ho lasciato cadere; ora è del proprietario del guscio. **Tolto dal mio piano** |
| **D3** | **Guida alla review dei numeri** (08 §8.1: *«i dubbi sono in risk, li rivedremo»*) | da fare | vedi §4 |
| **D4** | **Test list UI** → al developer, niente `test-author` | da fare | vedi §5 |

---

## 4. D3 — cosa il developer vedrà sui **suoi** dati, e come leggerlo

🔑 **La finestra comune comincia dove tutti gli asset hanno un prezzo** — l'intersezione di
`series_preparation.py:237-239` fissa solo questo inizio — **e da lì conta ogni data in cui almeno un
asset è quotato** (unione delle quotazioni fresche, `:236`); chi quel giorno non è quotato entra col
suo ultimo prezzo (`:287`). È il prezzo della clausola ⓪ (punti commensurabili).
⚠️ **Rettificato 24/09**: la stesura approvata diceva *«il calendario congiunto è un'intersezione: ogni
cifra è misurata sulle date che tutti condividono»* — premessa mia, sbagliata, trovata da Risk. La
guida operativa è la **D3** sopra; questa tabella resta come testo del piano approvato. Conseguenze
visibili:

| osservazione | difetto? |
|---|---|
| aggiungo un asset giovane e la «peggior discesa» di Apple **cambia** | ❌ no, **se** la finestra dichiarata nei metadati è cambiata · 🔴 sì se non è cambiata |
| la volatilità di un asset differisce fra Asset Global, Dashboard e Asset Detail | ❌ no: tre preparazioni (Ⓔ) — confrontare `n_observations` nei metadati |
| un solo livello pieno e quattro buchi su finestra corta | ❌ no se la sezione **dichiara** `insufficient_history` · 🔴 sì se tace |
| trattino `—` in cella | ❌ no se c'è la nota sotto la tabella · 🔴 sì senza |
| «Risalita al massimo» ≠ `|sotto il massimo| / (1 − |sotto il massimo|)` | 🔴 **sì** — vero per costruzione (−20 % → +25 %) |
| volatilità in tabella ≠ ascissa del punto sullo scatter | 🔴 **sì** — la tabella legge la cifra dello scatter |
| un euro, una classifica, un colore fra asset, una retta sullo scatter | 🔴 **sì** |

---

## 5. D4 — test list (la sottopongo, non la scrivo senza ok)

| # | dove | cosa | chi |
|---|---|---|---|
| **T1** | nuovo vitest, mio perimetro | compila ogni `risk.assetSet.**` nelle 4 lingue con `intl-messageformat` (10.7.18, già installato) · **controllo positivo**: una stringa `{{x}}` deve lanciare | A · catalogo al coordinator |
| **T2** | nuovo vitest jsdom, come `L4Replay.test.ts` | monta `AssetSetLossComparisonSection`: la sub-riga dei giorni contiene il numero, **zero** errori `[svelte-i18n]` in console | A |
| **T3** | `risk-lab.spec.ts` | listener console: fallire su qualunque `[svelte-i18n]` durante i test del laboratorio | **F** |
| **T4** | `risk-lab.spec.ts` | pin privacy off + variante privacy on con «nessun segnaposto» (§2) — **dopo J** | **F** |
| **T5** | `risk-lab.spec.ts` | **prima** di tutto: eseguirlo sull'albero integrato (istruzione del developer) | **F** |

📌 **Proposta fuori perimetro**: l'audit globale dovrebbe parsare ICU (08 R1 lo chiede) → è
`scripts/` → coordinator. T1 lo copre **solo** per il mio namespace.

---

## 6. Previsione dei conflitti

| con | superficie | forma | mitigazione |
|---|---|---|---|
| **F** | guscio, replay, `risk-lab.spec.ts`, pagina doc + nav | 🔴 la più ampia: i miei livelli vivono dentro il suo guscio | non tocco i suoi file; T3–T5 e le due derive gli arrivano come input |
| **Risk** | `riskAnalysisHelpers`, `riskPanelController` | semantica: un refactor di `buildBaseAnalytics` spegne i miei livelli | nessuna mia modifica prevista; `risk-lab` (T5) è la rete |
| **J** | asimmetria di `formatCurrencyAmount` | 🔴 **J la ripara** (decisione 23/09): cambia l'output a privacy accesa | nessuna sovrapposizione con i miei file; i miei livelli non hanno denaro. Blocca T4 di F |
| **I** | `capitalMarketLine` gated su `role==='portfolio'` | semantica: la mia garanzia «nessuna retta» | **già protetta** da I: `scatterChartHelpers.test.ts:120` *«is absent without a portfolio point»* |
| **K** | `assetTypes.ts`, select | nessuna sui miei file | — |
| tutti | `i18n/*.json` | R1 è una **modifica** di valore, 1 riga per file | via `dev.py i18n update`; dichiarata nell'handoff |
| coordinator | catalogo runner | T1/T2 sono file nuovi | li dichiaro, registra lui |

---

## 7. Lane e dati

- **Suite** `6153` · `/tmp/librefolio-r2-a` — solo `dev.py test`.
- **Copia di prod** `6163` · `/tmp/librefolio-r2-a-prodcopy` — server, verifiche, review.

✅ **Risolto 23/09** (developer, via coordinator): **non leggo mai il main checkout.** Il coordinator
ha creato una snapshot in sola lettura, `/tmp/librefolio-r2-prod-snapshot` (`004`, senza marcatore,
`a-w`). La copia si crea e si rinfresca **da lì**, con la procedura ricevuta (test snapshot + assenza
marcatore → sposta la vecchia in `.prev-…` → `cp -R` → `chmod -R u+w` → deve stampare
`004_release_1_2_0_schema`). **Se la snapshot manca, non la ricreo: la chiedo.**

- **Credenziali**: fornite dal developer, **non registrate nel journal né nel piano** (segreto).
- **`dev.py user` non ha `--data-dir`**: si mira con `LIBREFOLIO_TEST_DATA_DIR=<copia>` +
  `--test-db`, **e il `list` va sempre prima del `reset`** — è la sola prova di stare mirando alla
  copia (la stessa trappola del mio Fuori pista 6: una variabile sbagliata viene ignorata in silenzio).
- **Mai la snapshot come `--data-dir`**: il server si ferma con *readonly database*, ed è voluto.

⚠️ *«La lane di suite è quella che conoscevi»* — non per me (era `6170` · `r3-a`); il coordinator
concorda che la proprietà che conta regge lo stesso (il percorso `-prodcopy` è nuovo per tutti).

---

## 8. Passi ordinati

| # | passo | verifica |
|---:|---|---|
| 1 | scrivere questo piano in `implementation_2/progress/A-postmerge-esecuzione.md`, con link incrociato ad `A-esecuzione.md` | file tracciabile, nessun codice |
| 2 | R1 via `dev.py i18n update` | `git diff --stat` 4×(+1/−1) · `i18n audit` invariato |
| 3 | T1 + T2 (se approvati) | `npx vitest run <2 path>` ⇒ **`Test Files 2`**; T1 **rosso** su `{{days}}` prima di R1, verde dopo |
| 4 | `front check` | gli stessi 3, zero risk — **con l'ora di `generated.ts` accanto** |
| 5 | D3 guida + D1 doc (`docs-writer`) | `mkdocs build` strict + `check-links` |
| 6 | copia di prod **dalla snapshot** → `list` utente → server `6163` | l'utente vede «durata N g», **0** `MALFORMED_ARGUMENT` in console (il developer guarda; io non ho un browser pilotabile) |
| 7 | handoff: file, i18n condiviso, voce CHANGELOG proposta, file test nuovi per il catalogo | `6153`/`6163` libere · **`FROZEN`** |

**Proposta CHANGELOG** (la scrive il coordinator): *🐛 Fixed — Asset Global: la sotto-riga «durata
N giorni» della peggior discesa non veniva resa (sintassi di traduzione errata).*

---

## Handoff — 23/09/2026

### Due affermazioni `FROZEN`, non una (§3.9 del foglio 09)

| | stato |
|---|---|
| **albero** | `FROZEN` — nessuna modifica dopo questo handoff senza nuovo via |
| **processi** | 🟢 **server acceso di proposito** su `6163` (`dev.py server --test --port 6163 --data-dir /tmp/librefolio-r2-a-prodcopy`) perché il developer ci faccia la review. **Resta mio**: lo spengo e provo la porta libera quando il developer ha finito. Porta di suite `6153`: libera, nessuna suite lanciata |

### Il delta

| file | tipo | nota |
|---|---|---|
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | 🔴 **condiviso** | `lastedDays` corretta (valore) · `risk.assetSet.levels.l3.scatterNote` **aggiunta** · `+3/−2` per file: la riga in più è la virgola JSON su `noBenchmark` |
| `frontend/src/lib/components/risk/AssetSetRiskReturnSection.svelte` | mio | nota dello scatter senza retta · nome del benchmark dallo store |
| `frontend/src/lib/components/risk/assetSetLevels.ts` (+ `.test.ts`) | mio | `resolveName` opzionale · 2 test nuovi |
| `frontend/src/lib/components/risk/assetSetI18n.test.ts` | 🆕 **da registrare** | node → proposta `front-utility core-unit` (vicino: `assetSetLevels.test.ts`) |
| `frontend/src/lib/components/risk/AssetSetLossComparisonSection.test.ts` | 🆕 **da registrare** | jsdom → proposta `front-portfolio risk-levels-component` (vicino: `L4Replay.test.ts`) |
| `mkdocs_src/docs/user/assets/correlation.en.md` | 🆕 doc | pagina del tab Correlazione, solo EN |
| `mkdocs_src/docs/user/assets/index.en.md` | doc | frase Abs/% + voce Features |
| `mkdocs_src/mkdocs.yml` | 🔴 **condiviso** | **una** riga aggiunta a `:758` |
| `…/progress/A-postmerge-esecuzione.md` · `A-esecuzione.md` | journal | piano vivo nuovo · link in avanti nel vecchio |

**Intatti, verificato**: `AssetSetComparisonLevels.svelte` (congelato per R2-128), guscio e replay di F,
`risk-lab.spec.ts`, `riskAnalysisHelpers.ts`, `ScatterChart`, `maskable.ts`, `scripts/test_runner/`,
`CHANGELOG.md`, `backend/alembic/`.

### Proposte di `CHANGELOG` (le scrive il coordinator)

- 🐛 **Fixed** — Asset Global: la sotto-riga «durata N giorni» della peggior discesa non veniva resa (sintassi di traduzione errata).
- 🐛 **Fixed** — Asset Global: la nota sotto lo scatter rischio/rendimento descriveva una retta che su questa pagina non viene mai disegnata.
- 🐛 **Fixed** — Asset Global: il punto del benchmark sullo scatter mostrava un numero al posto del nome.
- 📚 **Docs** — nuova pagina utente del tab Correlazione di Asset Global.

### Aperti, non miei

| a | cosa |
|---|---|
| **J** | l'asimmetria di `formatCurrencyAmount` (decisa difetto) — **poi** F per il pin privacy |
| **F** | due citazioni derivate nei suoi file (`AssetSetRiskPanel:42` → `:879`, `AssetSetReplaySection:31` → `service.py:873`) · «Per nome» ordina per ID · colori invertiti heatmap/lista coppie · replay che offre un sostituto inesistente |
| **coordinator / J** | 🔴 **5 test privacy orfani**: `check-orphans` → nessuna azione di `dev.py test` lancia `moneyRenderSites.test.ts` né gli altri quattro di J |
| **io, quando R2-128 si chiude** | il docstring di `AssetSetComparisonLevels.svelte:19-27` è falso **con benchmark attivo** (lo si prepara insieme alla selezione). File congelato: non toccato |
| **developer** | tab misurato nella valuta **di istanza**, selezione ricordata **per browser**: intenzionale? |
| **Risk** (previsione di conflitto) | se **C2** si risolve ridefinendo `horizon_days` come giorni di calendario **anche nei VaR** (e non solo in `simulation.py`), cambia significato *Mese storto* nel mio L1° **e** *Mese storto* nel L1 di portafoglio: entrambi contano 21 **osservazioni** per intento dichiarato. Una correzione locale alla simulazione non tocca nessuno dei due |

> **Note implementazione (riserve C2/F2, 23/09)**: ricevute dal coordinator come informazione. La
> guida D3 le **nomina** in una sezione propria con la mappa «dove possono comparire», misurata nel
> codice e — per F2 — sui dati della copia (`[1, 3, 8]` contro `[1, 3, 8, 12]`: il crowdfunding
> viene escluso, osservazioni invariate). Rilette tutte le righe della guida contro le due riserve:
> **la riga 1 dipendeva da F2** (un crowdfunding non restringe niente) ed è stata spezzata in 1/1b;
> la riga 8 porta ora l'avvertenza di confrontare solo cifre per asset. Nessun'altra riga trae
> conclusioni da C2 o F2.

---

## Passo 8 — correzione post-commit: la regola della finestra · ✅ 24/09/2026

> **Baseline**: `f7bf5a85d` (checkpoint committato: `e0364c535` → `e2327e9a3` → `f7bf5a85d`, 9+3+2
> file), albero pulito. Scongelato **solo** per questo commit: la pagina utente e questo piano.

> **Note implementazione**:
> - **La premessa corretta**: *«ogni cifra è misurata sulle date che tutti gli asset condividono
>   (intersezione)»* — mia, sbagliata, trovata da Risk. Le tre regole vere sono nella guida D3
>   (paragrafo 🔑). Corretti: la guida (righe 1 e 9, regole), il blocco *Mese storto* con la misura
>   datata, le note storiche del passo 5 (marcate *«Rettificato 24/09»*, non cancellate) e il §4 del
>   piano approvato.
> - **La serie di portafoglio**: al posto dell'etichetta «misura del coordinator», citazioni di codice
>   verificate da me — `portfolio_engine.py:870-871` (uno stato per giorno di calendario), `:874-911`
>   (giorno fermo che riusa lo stato, chiuso da `continue` a `:911`), `portfolio_service.py:1305-1425`
>   (`get_history`, *«Return daily portfolio value series»*), `risk/service.py:932-941`.
> - **Pagina** `correlation.en.md`, con `docs-writer`, solo EN: le tre regole nella sezione *One Shared
>   Window* (titolo e ancora invariati; tenuto il vero di `:287`), e le frasi che le contraddicevano a
>   `:90`, `:99`, `:138`, `:150-156`, `:161-165`, `:177`, `:189`. *Bad month* non afferma più un mese: 21
>   osservazioni consecutive, circa un mese di giorni di borsa, tre settimane quando il calendario conta
>   ogni giorno — senza verdetto. `mkdocs build` strict ✅ · `check-links` 80 validi ✅ · nessuno stamp.
> - **Precisata anche la copertura** nella misura datata: il denominatore non è lo span richiesto ma le
>   date dell'intervallo con almeno una quotazione fresca, esclusa la baseline (`series_preparation.py:344-345`);
>   coincide con i 995 giorni solo perché un ETF justETF quota ogni giorno.
> - **Rilanciati da me**, non riportati: `mkdocs build` strict → exit 0, zero righe `WARNING`/`ERROR`;
>   `check-links` → exit 0, **80** validi (+3 ancore già in eccezione, non su questa pagina).

> **🔴 Fuori pista — la regola che ho passato allo specialista era di nuovo imprecisa, in due punti.**
> Venuta dal coordinator e riletta da me senza verificarla fino in fondo:
> 1. *«il punto riportato compare nei dettagli»* — **non su questo tab**: i dettagli di calcolo mostrano
>    solo osservazioni, copertura, fattore di annualizzazione e base (`RiskLevelSection.svelte:183-211`).
>    I conteggi dei punti riportati li mostra solo il pannello legacy.
> 2. *«rendimento zero»* — **solo per gli asset nella valuta del tab**: il prezzo riportato viene
>    convertito al cambio del suo giorno (`price_query.py:403-407`), quindi per un asset in altra valuta
>    il rendimento del giorno riportato è la variazione del cambio.
> E una precisazione alla regola 1: *«ha un prezzo»* è *«può essere valutato»* (conta anche il cambio),
> e con storia precedente l'inizio è il giorno prima dell'intervallo (`risk/service.py:514-517`).
> **Tutte e tre verificate nel codice da me** prima di correggere la guida, che le conteneva già.

> **📌 Reperti dello specialista, da girare (fuori dal mio perimetro)**:
> - 🔴 **«Parziale» anche quando tutti gli asset sono quotati negli stessi giorni**: la baseline si conta
>   fra i punti riportati (`series_preparation.py:311-313`, senza la guardia `index > 0` che c'è per le
>   quotazioni fresche), quindi un intervallo il cui giorno precedente non ha quotazioni — per esempio
>   uno che comincia di lunedì — rende parziale ogni sezione. → Risk.
> - un **inizio tardivo** non si vede a schermo: gli avvisi `baseline_inside_requested_range` e
>   `short_history:<id>` (`:281-284`) non hanno consumatore frontend; lo tradisce solo la copertura. → Risk.
> - la pagina di teoria `financial-theory/…/data-quality.en.md:52,60` descrive ancora l'intersezione
>   («one holding with a gap shortens the window for everyone»). → owner della teoria.
> - il docstring di `AssetSetComparisonLevels.svelte:19-26` (già registrato, file congelato per R2-128).

---

## Chiusura — allineamento 09/10/2026 (scritta da Risk)

Le voci passate a Risk qui sopra, sul codice di `3cceb4f90`:
- la baseline fra i punti riportati: ✅ la guardia c'è (`backend/app/services/series_preparation.py`);
- l'**inizio tardivo** che non si vede: ⏳ **aperto**, nessun lettore di `baseline_inside_requested_range` e
  `short_history` nel frontend → README della cartella, aperti;
- l'intersezione in `data-quality.en.md`: ✅ la pagina ora dice che un buco dentro la storia non accorcia niente;
- il docstring di `AssetSetComparisonLevels.svelte`: ✅ descrive le richieste separate del laboratorio e perché restano
  commensurabili.
