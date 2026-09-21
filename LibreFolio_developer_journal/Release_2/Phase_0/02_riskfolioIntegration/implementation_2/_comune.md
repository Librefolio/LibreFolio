# Vincoli comuni a tutte le superfici della fase 2

> Incluso per riferimento in ogni briefing S1–S5. **Il coordinatore è l'unico che scrive qui.**

## Corsie

| | mandato | porta | cartella dati |
|---|---|---|---|
| S1 | L1 | `6153` | `/tmp/librefolio-r2-s1` |
| S2 | L2 | `6154` | `/tmp/librefolio-r2-s2` |
| S3 | L3 | `6155` | `/tmp/librefolio-r2-s3` |
| S4 | L4 | `6156` | `/tmp/librefolio-r2-s4` |
| S5 | Asset Global | `6157` | `/tmp/librefolio-r2-s5` |

⚠️ **Il coordinatore usa `6150` con la cartella dati predefinita.** Nessuno la tocchi.

## Scrittori unici delle superfici condivise

| superficie | chi scrive | gli altri |
|---|---|---|
| `levels/RiskLevelsPanel.svelte` | round 2: **S1** → round 3: **A**, sole aggiunte | chiedono ad A |
| `levels/levelHelpers.ts` | **S1** | chiedono a S1 |
| `i18n/*.json` | ciascuno **solo** nel proprio namespace | il coordinatore verifica l'unione |
| `scripts/test_runner/*` | ~~**T3**~~ → **il coordinatore** | i mandati **dichiarano** i file nuovi nell'handoff, non li registrano |
| `frontend/e2e/portfolio/*.spec.ts` | ~~**T3**~~ → round 3: **A** su `risk-lab.spec.ts` | gli altri passano dal coordinatore |
| `ui/display/ScatterChart.svelte` | round 3: **A**, sole aggiunte | mai un default cambiato |
| `implementation_2/PRIMITIVE.md` | **F2** (chiuso) | lo leggono tutti |

> 🔴 **21 Set — `T3` non esiste più.** Si è svuotata durante la fase 2: ogni superficie ha
> scritto i propri spec e `check-orphans` dà zero orfani. **Una riga che nomina un mandato
> mai aperto non è vuota, è falsa** — e si legge come un divieto, perché un divieto non ha
> bisogno di un titolare vivo per sembrare valido. Dettaglio in `REGISTRO.md §2`.

## I quattro vincoli misurati

**① `api sync` dopo ogni aggiornamento di baseline**, forma canonica:
```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync
```
`generated.ts` **e** `openapi.json` sono entrambi in `.gitignore`: non viaggiano col merge.

**② Niente `toFixed` nuovi.** Esiste `utils/core/formatPercent`. I 16 (o 26, secondo il perimetro)
esistenti sono di **T4**, non tuoi.

**③ I `DocsLink` sono rotti in due modi** — percorso inesistente **e** forma `.md#ancora` invece
che directory. 🔄 **Aggiornato 18 Set: il debito è di chi possiede il file**, non di T2 — non si
possono mettere link corretti accanto a link sbagliati senza che la card si contraddica. T2 tiene
solo quelli in file di nessuno, più il cancello. **Percorso verificato**:
`financial-theory/technical-analysis/risk-metrics/<slug>/` — prefisso completo, **senza `.md`**,
**con lo slash finale**. ⚠️ `dev.py:1238` salta i `path={espressione}`: **apri il link nel
browser**, il cancello non ti copre.

**④ Gli avvisi in inglese sono 17 messaggi in prosa del backend**, non traduzioni mancanti.
Sono di **T1**. Non incorporarli come testo definitivo.

## I tre vincoli della fase 2

**Nati ciascuno da un mandato, durante la fase, e validi per tutti e cinque.**

**Ⓐ Dichiara la finestra** *(di S2)*. Nessun numero del mock è citabile come fatto — e la ragione
è più stretta di «il giorno scorre»: **due finestre diverse dello stesso giorno danno numeri
diversi**. Prova: F1 e S2 hanno popolato **lo stesso giorno** e divergono del **9 %** su
`effective_number_of_assets` (16,47 contro 15,00), perché hanno interrogato intervalli diversi.
**La finestra è una scelta della pagina, non un dato** → si scrive accanto al numero.

**Ⓑ Un vuoto consegnato va dichiarato** *(dal caso della heatmap)*. Guardare **non distingue**
*«vuoto perché rotto»* da *«vuoto perché il dato è quello»*: la matrice di S2 ha **0 coppie su 21
sopra 0,3**, e non è un guasto. Se la tua superficie esce povera, **dillo sulla pagina e nel piano
vivo** — non lasciarla sembrare un difetto, e non riempirla con valori fabbricati.

**Ⓒ Un cancello che non esercita gli stati raggiungibili solo con un'azione misura la pigrizia del
test, non il prodotto** *(di S5)*: *«il mio test scansiona senza cliccare, e gli euro stanno dietro
un click»*. Prima di dichiarare coperta una superficie, chiediti **quali stati richiedono un click
per esistere**.

> 🔑 **E la forma d'errore che li unisce** *(R2-19, nove occorrenze, cinque in fase 2 e tutte mie)*:
> **verificare che un artefatto esista e concluderne che è usato.** Le chiavi i18n c'erano davvero
> — nessuno le legge. La pagina docs esiste davvero — il link non la raggiunge. La formulazione
> migliore è di S4, su un errore suo: ***«era un'inferenza travestita da misura»***.
> **L'unico controllo che non può essere interrogato male è dimensionale**: `git show :file | wc -l`
> contro `wc -l file` — non cerca niente, quindi non può tacere su niente.

**Ⓓ Misurare i dati e guardare l'app nella stessa corsia sono attività incompatibili.**
Aprire la pagina asset nel browser fa aggiornare i prezzi correnti, e
`asset_sources/price_store.py:190` **riscrive il `close` di oggi** in `price_history`
allargando `high` per coprirlo (`open`, `low` e `volume` restano del generatore). Nella
corsia di S5 questo ha portato Apple `264,57 → 335,65 → 335,6` e Bitcoin
`25.890 → 80.942 → 80.917`: **cambia a ogni visita**, quindi una corsia guardata due volte
non è uguale nemmeno a sé stessa.

🔑 **Cancello obbligatorio prima di ogni misura numerica** — rilevatore **v2 di S5**, che misura
**l'arco** invece del conteggio:

```sql
SELECT ROUND((julianday(MAX(fetched_at)) - julianday(MIN(fetched_at))) * 86400, 1) FROM price_history;
```

| corsia | arco |
|---|---:|
| ripopolata | **0,1 s** |
| contaminata | **5 885 s** |

**Tre ordini di grandezza separano un atto da due, e non c'è soglia da tarare.**

> **Il conteggio chiedeva *«quanti istanti distinti?»* — una proprietà dell'orologio.
> L'arco chiede *«quanto tempo separa la prima scrittura dall'ultima?»* — una proprietà dell'atto.**

🔴 **v1 (conteggio delle raffiche al secondo) è RITIRATO: falso-positivo sulla corsia pulita.**
2 615 righe non entrano in un'etichetta di secondo — o meglio, **ci entrano solo per fortuna**:
misurate due corsie appena ripopolate, una dà **1 raffica** (2 615 righe in 0,13 s, cadute dentro
la stessa etichetta) e l'altra ne dà **2** (`18:45:52` → 1 331 · `18:45:53` → 1 284). **Il verdetto
di v1 su una corsia sana è sorteggiato dal punto in cui il popolamento attraversa il secondo.**

> ⚠️ **Ed è il verso peggiore per un cancello che autorizza a guardare**: un falso positivo su ciò
> che deve **dare il via** costa più di un falso negativo su ciò che deve fermare, **perché si
> impara a ignorarlo**.

🔴 **Il rilevatore di N è ritirato anche come conferma, e la sua premessa era falsa.**
Diceva *«il generatore scrive 13-16 cifre significative, il negozio prezzi esattamente due»*. **Il
log del negozio prezzi la smentisce riga per riga**: `10936.84931506849315068493154` (26 decimali),
`335.715` e `363.565` (3), `7635.1` (1). **`price_store` non arrotonda: ricopia ciò che il provider
gli dà.** Quindi il suo tasso d'errore **è sorteggiato dai dati che ispeziona** — **13 → 12 → 10 su
una raffica che è sempre di 14 righe**.

> **Un rilevatore il cui tasso di errore è sorteggiato dai dati che ispeziona può provare la
> presenza, mai l'assenza — e non può mai dire «solo N righe sono state toccate».**

### 🔴 La contaminazione finisce con la connessione, non con l'osservatore

Non basta smettere di guardare. Misurato da S5 **prima di uccidere il processo**, con lo scheduler
provato spento (`"Scheduler disabled via LIBREFOLIO_NO_SCHEDULER"`):

```
POST /api/v1/assets/prices/current  ×8, da porte effimere tutte diverse
18:44:15.902Z  "processing 14 fresh provider quote(s) … (existing rows today: 14)"
18:44:15.907Z  "commit OK (14 row(s) written/updated)"
allo spegnimento:  2 connessioni ESTABLISHED
```

**Ha scritto un minuto dopo l'ordine di spegnere.** Una scheda del browser lasciata aperta continua
a riscrivere: **l'atto che scrive non è la decisione di guardare, è la connessione che resta
aperta.** → **Spegnere il server non è igiene: è il rimedio.**

### 🔴 E guardare non riscrive soltanto: **crea storia dove non ce n'era**

Prima dello sguardo, 8 asset su 17 avevano **zero** prezzi. Dopo, **7 ne hanno esattamente
uno, quello di oggi**.

> **Un prezzo è peggio di zero.** Zero → l'asset è **visibilmente assente** dalla matrice, e
> *una riga mancante è il dato*. Uno → **ha storia**, entra nel calcolo, e **una sola
> osservazione ha varianza nulla** → correlazione degenere. **L'assenza è diventata una
> presenza, in silenzio.**

✅ **Forma operativa, di S5**: **ripopola → misura → guarda → butta la corsia.** Non
«rimisura dopo»: dopo è troppo tardi, perché la misura di prima **è già stata usata per
decidere**.

> ⚠️ Un unico punto anomalo condiviso ha portato una correlazione a **0,96** dove il DB
> pulito legge **0,22** — e **decade con la finestra esattamente come un artefatto di coda**,
> che è un'altra cosa.

**Ⓔ Prima di confrontare due numeri, verifica che siano prodotti dalla stessa cosa — e con
la stessa preparazione.** Una sonda che reimplementa la pipeline **non è una seconda misura
del prodotto: è una misura della sonda**. E `historical_kpi` (asset / `historical`, **258**
osservazioni) contro `comparison` (portfolio / `current_composition`, **360**) sono **due
preparazioni**: l'identità di manuale `beta = ρ·σₚ/σ_b` sbaglia del **19,49 %** fra due
numeri **entrambi corretti**, e **le due analitiche dichiarano la stessa `analyzed_range`**.
L'unico campo che le distingue è `n_observations`, **che nessuna card mostra**.

**Ⓕ Nessun numero che integri sulla finestra entra in un commento, una didascalia o
un'asserzione.** L'RNG è seminato per *(asset, data)* (`populate_mock_data.py:2162`): **un
prezzo a una data è stabile per sempre, è la finestra che scorre.** Quindi un prezzo o un
rendimento giornaliero si possono citare; **un beta, un DR, una correlazione, un
`cash_weight` no** — si derivano dalla fixture che il test inietta, o si rimanda al piano
vivo, che porta corsia, finestra e data.

> 🔑 Formulazione di S3: **un commento può affermare ciò che è vero per costruzione, e deve
> rimandare per ciò che è vero per misurazione.**

**Ⓖ Qualunque selettore `services risk-*` svuota la corsia.** Non solo `risk-all`: anche
`services risk-simulation` fa `db create-clean`. **Il sintomo non assomiglia alla causa** — una
sonda che muore con `sqlalchemy.exc.NoResultFound` cercando `e2e_test_user`, cioè **una sonda che
sembra rotta**. Misurato da S4 dopo una corsa di `test-author` nella sua corsia.

> ✅ **Ordine obbligatorio**: `api risk` **prima** di qualunque `services risk-*`, oppure
> `db populate --force` in mezzo. **Sbagliarlo fallisce sempre, non spesso.**

**Ⓗ Un'etichetta falsa sopravvive a una verifica corretta.** S4 ha consegnato a `test-author` una
fixture **ricostruita** etichettandola *«real measured»*. Lo specialista **ha trovato
l'incoerenza aritmetica** (`×3,386` contro `×3,33`) **e ha poi firmato quella riga come
"measured on the running backend"**, perché la verifica interroga **il numero** e non **la sua
provenienza**.

> 🔑 **Quando consegni un numero a un altro mandato, l'etichetta è parte del dato.** Se è
> ricostruito, dillo: chi lo riceve controllerà l'aritmetica, non l'origine.

⚠️ **E i letterali di una fixture non sono costanti.** Fra due popolazioni dello stesso giorno:
`fattore 29,90 → 27,46`, `n 93 → 96`. **I verdetti invece non si muovono.** Una fixture di
letterali va commentata come *«istantanea, non costante»*, altrimenti il prossimo che li
"aggiorna" credendoli stabili **scrive un rosso dal nulla**.

## Definizione di finito

**Il coordinatore guarda la tua superficie nel browser, in italiano, prima che tu chiuda.**
Non «i test passano».

## Processo

- **Analisi prima del codice.** Nessuna riga prima della revisione.
- **Non fidarti del briefing.** Nella fase 1 cinque numeri del coordinatore o di F2 sono
  risultati sbagliati, ciascuno trovato dall'altro. Una divergenza segnalata è un'informazione.
- **Lo stage è l'ultimo atto, e lo dichiari tu** con `FROZEN`. Nella fase 1 la finestra fra
  «stagio» e «l'agente finisce» si è riaperta **sei volte**.
- **Il controllo che non mente** è dimensionale: `git show :file | wc -l` contro `wc -l file`.
  Non cerca una stringa, quindi non può tacere su un'altra.
- **Aggiorna il piano vivo dopo ogni passo**, in `implementation_2/progress/SN-esecuzione.md`,
  e **nominalo a ogni handoff**: nel round 1 gli otto `*-esecuzione.md` sono stati gli unici file
  a esistere solo sul disco, perché il piano si aggiorna *dopo* il passo e nessun checkpoint
  automatico lo contiene mai.

---

## I vincoli del round 3

### Ⓘ — `front check` non ha mai controllato uno spec, e il cancello di fase lo ignorava

**Trovato da A il 21 Set**, per mano del suo specialista: `./dev.py front check` esegue
`svelte-check --tsconfig ./tsconfig.json`, e **quel tsconfig ha `"exclude": ["e2e/**/*"]`**.

> 🔑 ***«La risposta giusta a una domanda che quello strumento non sta ascoltando.»***
> Il cancello *«non deve aggiungere un quarto errore»* non poteva dire niente su uno spec,
> perché lo spec non è nel suo perimetro — e passava, verde, esattamente come se lo avesse
> controllato.

✅ **Chiunque tocchi un file sotto `frontend/e2e/` aggiunge al proprio cancello:**

```bash
npx tsc -p tsconfig.e2e.json --noEmit
```

⚠️ Sulla baseline `f829cd76b` ci sono **76 errori preesistenti** (`onboarding-tour`, `tools/*`) e
**0 in tutto `e2e/portfolio/`**. Il cancello è quindi *«zero in `e2e/portfolio/`»*, non «zero».

### Ⓙ — il cancello `front check` non è «verde», ed è così per costruzione

La baseline eredita **3 errori** da `dev_release2`, verificati **byte-identici** e con **zero file
`risk`** coinvolti:

```
ToolExecutionMetrics.svelte:44:55
TransactionFormModal.test.ts:787:48  ·  :819:48
```

✅ **Il cancello è: «gli stessi 3, e nessuno in un file risk».**

> **Un cancello che non si può passare va ridefinito con la sua misura, non ignorato** —
> altrimenti il primo rosso vero si legge come quello ereditato.

### Ⓚ — un worktree fresco non compila il frontend, e una corsia sana e una malata danno lo stesso verde

**Riprodotto da A e dal coordinatore indipendentemente**, 21 Set. Su una corsia nuova:

```
❌ Download failed and no cached version exists   (mathjax)
❌ Resource cache incomplete - aborting frontend build
```

**Due cause sovrapposte:**

| | causa | chi ripara |
|---|---|---|
| **SSL** | il `certifi` del venv condiviso non verifica il CDN — `curl -I` → **200**, `urlopen` dentro il venv → `CERTIFICATE_VERIFY_FAILED` | 🔴 **developer**, a corsie ferme |
| **politica** | `scripts/update_js_cache.py` rende **hard failure** un asset con `vendor_dir_key: "mkdocs"`, e con quello **aborta il build dell'applicazione** — benché `grep mathjax frontend/` dia **zero** | **C**, round 3 |

🔑 **E l'aggravante è di metodo**: la corsia del coordinatore gira **perché ha una cache del
18 Set**, non perché sia sana. **Una corsia sana e una malata producono lo stesso verde, e il
verde della prima non significa niente.**

📌 **Ripristino autorizzato solo con provenienza verificata**: il manifesto porta
`current_hash` e `size`, e la copia vale solo se **entrambi combaciano** con la fonte canonica
(`300480069078` · `1 173 007`, confermato contro il `Content-Length` del CDN). Un ripristino di
cache con hash verificato **non è un aggiramento**; `pip install --upgrade certifi` lo sarebbe,
perché tocca il venv di **tutte** le corsie.

### Ⓛ — la cartella dati si passa solo con `--data-dir`

**Trovato da A il 21 Set.** `LIBREFOLIO_DATA_DIR` **non è il meccanismo**: il server la ignora e
usa `backend/data/test/`.

> 🔑 **Non «uno strumento risponde alla domanda che gli si fa», ma uno strumento che risponde
> correttamente alla domanda giusta, su un soggetto che non ha dichiarato.** I numeri erano
> esatti e venivano dal database sbagliato — e niente nella risposta lo diceva.

⚠️ Non produce contaminazione tracciata (`backend/data/**` è ignorato), **ma fa misurare la
corsia sbagliata**, che è peggio: una contaminazione si vede, una misura fuori soggetto no.

### Ⓜ — il grafo Alembic non è unito da Git, e nessun cancello lo guarda

Il merge `f829cd76b` ha prodotto **due teste** — `003_asset_benchmark_flag_and_taxonomy` e
`003_user_onboarding_progress`, entrambe con `down_revision = "5b1333fa6b07"`.

> **File diversi, stesso genitore: un conflitto semantico senza conflitto testuale.**
> Git ha unito i file **senza unire il grafo**.

✅ **Dopo ogni aggiornamento di baseline che porti migrazioni, prima di qualunque altra cosa:**

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run alembic -c backend/alembic.ini heads
```

**Una sola riga, o il grafo è biforcato.** ⚠️ Un DB **già esistente** continua a funzionare su
una delle due teste: **solo chi ne crea uno nuovo incontra il muro**. Le corsie che girano,
girano **per anzianità, non per salute**.

🔴 **E il cancello della riparazione ha tre livelli, di cui il terzo è quello che nessuno
penserebbe di fare**: ① `heads` dà una testa · ② un DB fresco si crea · ③ **un DB stampato sulla
testa preesistente fa `upgrade head`** — *il percorso delle installazioni rilasciate, l'unico che
prova che un utente che aggiorna non si rompe*.

### Ⓝ — `front check` è strutturalmente cieco sul contratto del payload di rischio

**Trovato da P il 21 Set**, verificando la riga «zero modifiche frontend» del contratto di A.
Regge — **ma il corollario conta più della riga**:

```ts
okOutput(): Record<string, unknown>
finite(value: unknown)
```

> 🔴 **I tipi del payload di rischio sono cancellati alla frontiera.** Nessun `null`, nessun
> tipo generato allargato può produrre un errore di compilazione. **Un verde di `front check`
> non è una prova che il contratto del payload regga.**

🔑 **È la forma Ⓘ un piano più sotto**: là il cancello non guardava gli spec per esclusione di
`tsconfig`; qui guarda il file giusto e **non può vedere la classe di difetto che conta**,
perché il tipo è stato cancellato prima.

✅ Il cancello vero lato consumatore è il **validatore Zod** del client generato.
⚠️ E la devWiki registra già che per `RiskMatrixCell.value` **tipo emesso e validatore emesso
divergono** — quindi nemmeno quello è un cancello unico.

**Conseguenza operativa**: chi cambia un contratto di rischio prova il cambiamento con un test
del **payload**, non con `front check`. Il verde di `front check` resta necessario e **non è
mai sufficiente** su questa superficie.

### Ⓞ — il rifiuto per storia insufficiente arriva PRIMA del plugin

`RiskService._available_observations` rifiuta prima che la guardia del plugin venga raggiunta.

```
historical_kpi     available=0 required=20 -> insufficient_history
drawdown_summary   available=0 required= 2 -> insufficient_history
asset_risk_return  available=0 required=20 -> insufficient_history
```

⚠️ **Aggiungere uno scope alla tupla di un plugin non basta**: senza passare questo cancello si
ottiene un'analitica **`unavailable` al 100 %** — *lo stesso fallimento con un nome nuovo*.
Chi allarga uno scope **lo prova end-to-end**, non leggendo `supported_scopes`.
